from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "finalize_wave64_speech_rows134_137_147.py"
SPEC = importlib.util.spec_from_file_location("wave64_speech_rows134_137_147_finalizer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechRows134137147FinalizerTests(unittest.TestCase):
    def test_row_statuses_are_fail_closed(self) -> None:
        self.assertEqual({"134", "137", "147"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(status.startswith("Blocked_") for status in MODULE.ROW_STATUS.values()))

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Item_ID", "Status", "Coverage_Audit_Status", "Evidence_Path", "Notes"]
            rows = [
                {"Item_ID": f"ITEM-W64-{number}", "Status": "Planned", "Coverage_Audit_Status": "planned", "Evidence_Path": "old", "Notes": "old"}
                for number in (134, 137, 147)
            ]
            rows.append({"Item_ID": "ITEM-W64-999", "Status": "UserOwned", "Coverage_Audit_Status": "keep", "Evidence_Path": "keep", "Notes": "keep"})
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
            destination = root / "durable.bin"
            source.write_bytes(b"source")
            destination.write_bytes(b"conflict")
            with self.assertRaises(MODULE.FinalizationError):
                MODULE.copy_exact(source, destination)

    def test_validate_packet_rejects_manifest_binding_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in MODULE.ARTIFACT_NAMES[:3]:
                (root / name).write_text("{}", encoding="utf-8")
            manifest = {
                "classification": MODULE.EXPECTED_CLASSIFICATION,
                "outputs": {
                    name: MODULE.binding(root / name) for name in MODULE.ARTIFACT_NAMES[:3]
                },
            }
            (root / MODULE.ARTIFACT_NAMES[3]).write_text(json.dumps(manifest), encoding="utf-8")
            evaluation = {
                "classification": MODULE.EXPECTED_CLASSIFICATION,
                "manifest_binding": {"sha256": "0" * 64},
            }
            (root / MODULE.ARTIFACT_NAMES[4]).write_text(json.dumps(evaluation), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.FinalizationError, "does not bind"):
                MODULE.validate_packet(root)

    def test_validate_packet_rejects_false_promotion_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in MODULE.ARTIFACT_NAMES[:3]:
                (root / name).write_text("{}", encoding="utf-8")
            manifest = {
                "classification": MODULE.EXPECTED_CLASSIFICATION,
                "outputs": {
                    name: MODULE.binding(root / name) for name in MODULE.ARTIFACT_NAMES[:3]
                },
            }
            manifest_path = root / MODULE.ARTIFACT_NAMES[3]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            gates = {
                "source_hashes_verified_pass": True,
                "ownership_timeline_technical_pass": True,
                "lipsync_admission_refusal_pass": True,
                "benchmark_partition_disjoint_pass": True,
                "benchmark_media_hashes_verified_pass": True,
                "independent_diarization_pass": False,
                "visual_active_speaker_ownership_pass": False,
                "lipsync_correction_executed": False,
                "benchmark_full_coverage_pass": False,
                "production_authority_pass": True,
            }
            evaluation = {
                "classification": MODULE.EXPECTED_CLASSIFICATION,
                "manifest_binding": MODULE.binding(manifest_path),
                "gates": gates,
                "row_results": {number: {"row_complete": False} for number in MODULE.ROW_STATUS},
                "boundaries": {
                    key: False for key in (
                        "media_regenerated", "media_mutated", "video_read_or_written",
                        "subjective_review_fabricated", "production_promotion_claimed",
                        "content_based_suppression", "aws_or_ec2_used", "mask_or_wave71_touched",
                    )
                },
            }
            (root / MODULE.ARTIFACT_NAMES[4]).write_text(json.dumps(evaluation), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.FinalizationError, "not fail-closed"):
                MODULE.validate_packet(root)


if __name__ == "__main__":
    unittest.main()
