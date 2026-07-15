import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/apply_wave64_openslr31_speaker_identity_tracking.py"
)
SPEC = importlib.util.spec_from_file_location(
    "apply_wave64_openslr31_speaker_identity_tracking", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def report_payload():
    return {
        "item_id": "ITEM-W64-027",
        "tracker_id": "TRK-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
        "row_complete": False,
        "blockers": [
            {"classification": "Blocked_Voice_Dialogue_Production_Proof_Missing"},
            {"classification": MODULE.SUPERSEDED_BLOCKER},
        ],
        "evidence": [],
    }


class OpenSLR31SpeakerTrackingTests(unittest.TestCase):
    def test_report_removes_only_superseded_threshold_blocker(self):
        result = MODULE.update_report_payload(report_payload())
        classifications = [entry.get("classification") for entry in result["blockers"]]
        self.assertNotIn(MODULE.SUPERSEDED_BLOCKER, classifications)
        self.assertIn("Blocked_Voice_Dialogue_Production_Proof_Missing", classifications)
        self.assertTrue(result["validation"]["openslr31_speaker_disjoint_validation_pass"])
        self.assertTrue(result["validation"]["licensed_human_voice_chain_identity_verified"])
        self.assertFalse(result["acceptance_gates"]["production_review_authority_pass"])
        self.assertFalse(result["row_complete"])

    def test_report_update_is_idempotent(self):
        once = MODULE.update_report_payload(report_payload())
        twice = MODULE.update_report_payload(once)
        matches = [entry for entry in twice["evidence"] if entry.get("path") == MODULE.EVIDENCE_REL]
        self.assertEqual(len(matches), 1)
        self.assertEqual(twice["runtime"]["openslr31_speaker_validation_execution_count"], 1)

    def test_report_rejects_status_drift(self):
        payload = report_payload()
        payload["status"] = "Completed"
        with self.assertRaisesRegex(ValueError, "status drift"):
            MODULE.update_report_payload(payload)

    def test_append_unique_does_not_duplicate(self):
        self.assertEqual(MODULE.append_unique("a; b", "b", "; "), "a; b")
        self.assertEqual(MODULE.append_unique("a; b", "c", "; "), "a; b; c")

    def test_csv_update_preserves_status_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "items.csv"
            fields = ["Item_ID", "Status", "Evidence_Required", "Coverage_Audit_Status", "Notes"]
            rows = [
                {
                    "Item_ID": spec["item_id"],
                    "Status": spec["status"],
                    "Evidence_Required": "existing.json",
                    "Coverage_Audit_Status": "existing",
                    "Notes": "existing note",
                }
                for spec in MODULE.ROW_SPECS.values()
            ]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            specs = {
                key: {**value, "Item_ID": value["item_id"]}
                for key, value in MODULE.ROW_SPECS.items()
            }
            MODULE.update_csv(path, "Item_ID", "Evidence_Required", specs, True)
            MODULE.update_csv(path, "Item_ID", "Evidence_Required", specs, True)
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count(MODULE.EVIDENCE_REL), 3)
            self.assertEqual(content.count(MODULE.NOTE), 3)


if __name__ == "__main__":
    unittest.main()
