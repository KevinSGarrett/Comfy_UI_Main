from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows140_142_144.py"
SPEC = importlib.util.spec_from_file_location("wave64_rows140_142_144_finalizer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def bound(path: Path) -> dict:
    return {"path": str(path), "sha256": MODULE.sha256_file(path), "bytes": path.stat().st_size}


def valid_manifest(root: Path) -> dict:
    records = {}
    for name in ("a.wav", "b.wav", "mix.wav", "matrix.json", "decisions.json", "probe.bin", "ledger.json"):
        path = root / name
        path.write_bytes(f"fixture:{name}\n".encode("ascii"))
        records[name] = bound(path)
    return {
        "classification": MODULE.EXPECTED_CLASSIFICATION,
        "source_hashes_unchanged": True,
        "row_complete": False,
        "overlap_artifacts": {"a": records["a.wav"], "b": records["b.wav"], "mix": records["mix.wav"]},
        "overlap": {"gates": {
            "source_ownership_from_isolated_stems_pass": True,
            "overlap_interval_present_pass": True,
            "priority_duck_pass": True,
            "spatial_separation_pass": True,
            "sample_sum_integrity_pass": True,
            "technical_clipping_pass": True,
            "independent_diarization_pass": False,
            "independent_overlap_intelligibility_pass": False,
            "human_playback_review_pass": False,
            "production_authority_pass": False,
        }},
        "adversarial_matrix": {
            "known_fixture_detection_pass": True,
            "known_fixture_detection_rate": 1.0,
            "full_required_category_coverage_pass": False,
            "candidate_media_mutated": False,
            "binding": records["matrix.json"],
        },
        "promotion_control": {
            "all_current_candidates_refused_pass": True,
            "production_promotion_performed": False,
            "binding": records["decisions.json"],
            "synthetic_non_media_control_probe": {
                "atomic_write_pass": True,
                "idempotent_replay_pass": True,
                "revocation_invalidation_pass": True,
                "rollback_pass": True,
                "production_candidate": False,
                "media_promotion_performed": False,
                "probe_artifact": records["probe.bin"],
                "ledger": records["ledger.json"],
            },
        },
        "boundaries": {
            "candidate_regenerated": False,
            "candidate_media_mutated": False,
            "human_review_fabricated": False,
            "production_promotion_performed": False,
            "ec2_started": False,
            "s3_mutated": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
            "content_based_suppression": False,
        },
    }


class FinalizeWave64SpeechRows140142144Tests(unittest.TestCase):
    def test_manifest_validation_accepts_control_pass_and_blocked_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = MODULE.validate_manifest(valid_manifest(Path(temporary)))
            self.assertEqual(7, len(paths))

    def test_manifest_rejects_false_production_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = valid_manifest(Path(temporary))
            manifest["promotion_control"]["production_promotion_performed"] = True
            with self.assertRaisesRegex(MODULE.FinalizationError, "promotion boundary"):
                MODULE.validate_manifest(manifest)

    def test_update_rows_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Item_ID", "Status", "Coverage_Audit_Status", "Evidence_Path", "Status_Decision", "Notes"]
            rows = [{name: "old" for name in fields} | {"Item_ID": f"ITEM-W64-{number}"} for number in (140, 142, 144)]
            rows.append({name: "keep" for name in fields} | {"Item_ID": "ITEM-W64-999", "Status": "UserOwned"})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            first = path.read_bytes()
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            self.assertEqual(first, path.read_bytes())
            with path.open("r", encoding="utf-8", newline="") as handle:
                updated = list(csv.DictReader(handle))
            self.assertEqual("UserOwned", updated[-1]["Status"])
            self.assertTrue(all(updated[index]["Status"].startswith("Blocked_") for index in range(3)))

    def test_copy_exact_rejects_existing_hash_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            target = root / "target.bin"
            source.write_bytes(b"source")
            target.write_bytes(b"target")
            with self.assertRaisesRegex(MODULE.FinalizationError, "hash conflict"):
                MODULE.copy_exact(source, target)


if __name__ == "__main__":
    unittest.main()
