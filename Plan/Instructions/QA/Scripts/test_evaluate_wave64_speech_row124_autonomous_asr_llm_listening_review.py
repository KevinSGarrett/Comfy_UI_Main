from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_speech_row124_autonomous_asr_llm_listening_review.py"
)
SPEC = importlib.util.spec_from_file_location("row124_autonomous_asr_llm_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvaluateWave64SpeechRow124AutonomousAsrLlmListeningReviewTests(unittest.TestCase):
    def test_dry_run_fails_closed_on_pacing_and_dnsmos_without_complete(self) -> None:
        packet = MODULE.build_review(ROOT, stamp="DRYRUNTESTG", write_outputs=False)
        self.assertEqual(packet["artifact_type"], "wave64_speech_row124_autonomous_asr_llm_listening_review")
        self.assertEqual(packet["status"], "AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_FAIL")
        self.assertFalse(packet["independent_playback_review_pass"])
        self.assertFalse(packet["listening_authority_granted"])
        self.assertFalse(packet["row_complete"])
        self.assertFalse(packet["product_completion_claimed"])
        self.assertFalse(packet["human_decision_fabricated"])
        self.assertFalse(packet["boundaries"]["row074_touched"])
        self.assertFalse(packet["boundaries"]["timing_waiver_granted"])
        self.assertIn("pacing_timing", packet["failing_categories"])
        self.assertEqual(packet["blocker_code"], "AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_FAIL")
        self.assertEqual(packet["candidate_sha256"], MODULE.EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(
            packet["observations"]["asr"]["normalized_wer"],
            0.0,
        )
        self.assertIn("OVRL", packet["observations"]["dnsmos"])
        self.assertTrue(packet["cross_gate_coupling"]["fake_listening_pass_rejected"])
        self.assertFalse(
            (
                ROOT
                / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/"
                "TRK-W64-124_AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_DRYRUNTESTG.json"
            ).exists()
        )

    def test_score_helpers(self) -> None:
        self.assertEqual(MODULE.score_intelligibility(0.0), 5.0)
        self.assertEqual(MODULE.score_pacing(0.30, 0.08), 0.0)
        self.assertEqual(MODULE.score_pacing(0.20, 0.08), 2.0)
        self.assertGreaterEqual(MODULE.score_identity(0.76, 0.33), 4.0)


if __name__ == "__main__":
    unittest.main()
