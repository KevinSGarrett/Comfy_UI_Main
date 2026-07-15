import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/apply_wave64_cv3_emotion_tracking.py"
SPEC = importlib.util.spec_from_file_location("apply_wave64_cv3_emotion_tracking", SCRIPT)
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
        "acceptance_gates": {"candidate_emotion_verified": False},
        "blockers": [
            {
                "classification": "Blocked_Voice_Emotion_Model_Payload_Missing",
                "reason": "old",
            }
        ],
        "evidence": [],
        "runtime": {},
    }


class CV3EmotionTrackingTests(unittest.TestCase):
    def test_append_unique_is_idempotent(self):
        first = MODULE.append_unique("a", "b", "; ")
        second = MODULE.append_unique(first, "b", "; ")
        self.assertEqual(second, "a; b")

    def test_report_update_replaces_payload_blocker_without_promotion(self):
        payload = MODULE.update_report_payload(report_fixture())
        self.assertEqual(payload["blockers"][0]["classification"], MODULE.BLOCKER_CLASSIFICATION)
        self.assertTrue(payload["acceptance_gates"]["cv3_emotion_model_execution_path_verified"])
        self.assertFalse(payload["acceptance_gates"]["candidate_emotion_verified"])
        self.assertFalse(payload["row_complete"])

    def test_report_update_is_idempotent(self):
        once = MODULE.update_report_payload(report_fixture())
        twice = MODULE.update_report_payload(deepcopy(once))
        self.assertEqual(len(twice["evidence"]), 1)
        self.assertEqual(twice["runtime"]["cv3_emotion_calibration_count"], 1)

    def test_report_update_rejects_status_drift(self):
        payload = report_fixture()
        payload["status"] = "Completed"
        with self.assertRaisesRegex(ValueError, "status drift"):
            MODULE.update_report_payload(payload)


if __name__ == "__main__":
    unittest.main()
