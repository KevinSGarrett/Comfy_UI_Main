import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/apply_wave64_cv3_speaker_identity_tracking.py"
)
SPEC = importlib.util.spec_from_file_location("apply_wave64_cv3_speaker_identity_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def report_fixture():
    return {
        "item_id": "ITEM-W64-027",
        "tracker_id": "TRK-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
        "row_complete": False,
        "implementation": {},
        "validation": {},
        "acceptance_gates": {},
        "blockers": [],
        "evidence": [],
        "runtime": {},
    }


class ApplyCV3SpeakerIdentityTrackingTests(unittest.TestCase):
    def test_append_unique_is_idempotent(self):
        once = MODULE.append_unique("first", "second", "; ")
        twice = MODULE.append_unique(once, "second", "; ")
        self.assertEqual(once, twice)

    def test_update_report_preserves_status_and_adds_blocker(self):
        payload = MODULE.update_report_payload(report_fixture())
        self.assertEqual(payload["status"], "Blocked_Voice_Dialogue_Production_Proof_Missing")
        self.assertFalse(payload["row_complete"])
        self.assertTrue(
            payload["acceptance_gates"]["cv3_speaker_matched_pair_calibration_executed"]
        )
        self.assertFalse(
            payload["acceptance_gates"]["cv3_speaker_threshold_generalization_pass"]
        )
        self.assertEqual(
            [entry["classification"] for entry in payload["blockers"]],
            [MODULE.BLOCKER_CLASSIFICATION],
        )

    def test_update_report_is_idempotent(self):
        payload = MODULE.update_report_payload(report_fixture())
        payload = MODULE.update_report_payload(payload)
        self.assertEqual(
            sum(
                entry.get("classification") == MODULE.BLOCKER_CLASSIFICATION
                for entry in payload["blockers"]
            ),
            1,
        )
        self.assertEqual(
            sum(entry.get("path") == MODULE.EVIDENCE_REL for entry in payload["evidence"]),
            1,
        )

    def test_update_report_rejects_status_drift(self):
        payload = report_fixture()
        payload["status"] = "Completed"
        with self.assertRaisesRegex(ValueError, "status drift"):
            MODULE.update_report_payload(payload)


if __name__ == "__main__":
    unittest.main()
