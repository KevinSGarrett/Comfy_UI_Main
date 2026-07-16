from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "finalize_wave64_speech_rows135_136_138.py"
SPEC = importlib.util.spec_from_file_location("speech_alignment_spatial_finalizer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechAlignmentSpatialFinalizerTests(unittest.TestCase):
    def test_row_statuses_are_fail_closed(self) -> None:
        self.assertEqual({"135", "136", "138"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(status.startswith("Blocked_") for status in MODULE.ROW_STATUS.values()))

    def test_evaluation_accepts_only_bounded_runtime(self) -> None:
        gates = {
            key: True for key in (
                "runtime_manifest_lineage_pass", "source_nonmutation_pass", "word_grapheme_alignment_runtime_pass",
                "viseme_fixture_runtime_pass", "spatial_decode_pass", "spatial_duration_pass",
                "spatial_channel_motion_pass", "spatial_clipping_pass", "spatial_intelligibility_pass",
                "spatial_speaker_identity_pass",
            )
        }
        gates.update({
            "phoneme_authority_pass": False,
            "viseme_production_input_pass": False,
            "independent_playback_review_pass": False,
            "production_scene_authority_pass": False,
        })
        value = {
            "classification": MODULE.EXPECTED_CLASSIFICATION,
            "gates": gates,
            "row_results": {number: {"row_complete": False} for number in MODULE.ROW_STATUS},
            "boundaries": {
                "true_phoneme_authority_complete": False,
                "mandated_row135_asset_set_complete": False,
                "independent_playback_review_complete": False,
                "production_scene_authority_complete": False,
                "production_ready": False,
            },
        }
        MODULE.validate_evaluation(value)
        value["gates"]["phoneme_authority_pass"] = True
        with self.assertRaises(MODULE.FinalizationError):
            MODULE.validate_evaluation(value)

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Item_ID", "Status", "Coverage_Audit_Status", "Evidence_Path", "Notes"]
            rows = [{"Item_ID": f"ITEM-W64-{number}", "Status": "Planned", "Coverage_Audit_Status": "planned", "Evidence_Path": "old", "Notes": "old"} for number in (135, 136, 138)]
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


if __name__ == "__main__":
    unittest.main()
