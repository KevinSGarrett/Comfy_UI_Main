import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/apply_wave64_cosyvoice2_instruct_control_tracking.py"
SPEC = importlib.util.spec_from_file_location("apply_wave64_cosyvoice2_instruct", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ApplyWave64CosyVoice2InstructControlTrackingTests(unittest.TestCase):
    def test_evidence_mirrors_are_exact_and_fail_closed(self):
        result = MODULE.verify_evidence()
        self.assertEqual(result["sha256"], MODULE.EVIDENCE_SHA256)

    def test_append_unique_is_idempotent(self):
        once = MODULE.append_unique("one", "two", "; ")
        twice = MODULE.append_unique(once, "two", "; ")
        self.assertEqual(once, twice)

    def test_report_update_preserves_blocked_status(self):
        source = ROOT / MODULE.REPORT_PATHS[1]
        payload = json.loads(source.read_text(encoding="utf-8"))
        updated = MODULE.update_report_payload(copy.deepcopy(payload))
        self.assertEqual(updated["status"], "Blocked_Voice_Dialogue_Production_Proof_Missing")
        self.assertFalse(updated["row_complete"])
        self.assertFalse(
            updated["acceptance_gates"]["cosyvoice2_instruct_candidate_exact_content_pass"]
        )
        self.assertFalse(
            updated["validation"]["cosyvoice2_instruct_same_control_retry_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
