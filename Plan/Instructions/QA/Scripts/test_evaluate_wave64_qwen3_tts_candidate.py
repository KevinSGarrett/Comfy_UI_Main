from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "evaluate_wave64_qwen3_tts_candidate.py"
SPEC = importlib.util.spec_from_file_location("qwen_evaluator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenCandidateEvaluatorTests(unittest.TestCase):
    def test_classification_preserves_playback_and_authority_boundary(self) -> None:
        gates = {
            "technical_audio_pass": True,
            "dialogue_timing_pass": True,
            "candidate_asr_pass": True,
        }
        self.assertEqual(
            "PASS_QWEN3_TTS_AUTOMATED_QA_PLAYBACK_AND_AUTHORITY_PENDING",
            MODULE.classify(gates),
        )
        gates["candidate_asr_pass"] = False
        self.assertEqual("FAIL_QWEN3_TTS_DIALOGUE_INTELLIGIBILITY", MODULE.classify(gates))

    def test_audio_inspection_reports_raw_pcm_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(24_000)
                handle.writeframes((b"\x00\x10" * 24_000))
            before = MODULE.sha256_file(path)
            result = MODULE.inspect_audio(path)
            self.assertEqual(1.0, result["duration_seconds"])
            self.assertEqual(1, result["channels"])
            self.assertEqual(before, MODULE.sha256_file(path))

    def test_lineage_rejects_review_or_production_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.wav"
            candidate.write_bytes(b"RIFF-test")
            runner = root / "runner.py"
            runner.write_text("pass\n", encoding="utf-8")
            plan = root / "plan.json"
            plan.write_text(
                json.dumps({
                    "normalization": {"normalized_text": "We hold the frame steady and move on the beat."},
                    "duration": {"target_seconds": 3.0, "tolerance_seconds": 0.08},
                }),
                encoding="utf-8",
            )
            manifest = {
                "classification": "QWEN3_TTS_GENUINE_CANDIDATE_GENERATED_AUTOMATED_QA_PENDING",
                "candidate_id": "W64-QWEN3-VOICE-DESIGN-SEED-12345",
                "engine": {"repository": MODULE.EXPECTED_ENGINE, "revision": MODULE.EXPECTED_REVISION},
                "output": {"path": str(candidate), "sha256": MODULE.sha256_file(candidate)},
                "request": {"seed": 12345, "text": "We hold the frame steady and move on the beat."},
                "plan": {"sha256": MODULE.sha256_file(plan)},
                "boundaries": {
                    "automated_qa_complete": False,
                    "playback_review_complete": True,
                    "production_ready": False,
                    "rejected_candidate_rerun": False,
                },
            }
            with self.assertRaisesRegex(MODULE.EvaluationError, "review or production"):
                MODULE.verify_lineage(
                    manifest,
                    candidate,
                    MODULE.sha256_file(candidate),
                    runner,
                    MODULE.sha256_file(runner),
                    plan,
                    MODULE.sha256_file(plan),
                )


if __name__ == "__main__":
    unittest.main()
