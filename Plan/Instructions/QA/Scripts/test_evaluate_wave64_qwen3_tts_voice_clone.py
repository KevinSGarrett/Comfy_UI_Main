from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "evaluate_wave64_qwen3_tts_voice_clone.py"
SPEC = importlib.util.spec_from_file_location("qwen_clone_eval", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenVoiceCloneEvaluationTests(unittest.TestCase):
    def test_classification_preserves_production_boundary(self) -> None:
        gates = {"technical_audio_pass": True, "candidate_asr_pass": True, "chain_specific_speaker_identity_pass": True}
        self.assertEqual("PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED", MODULE.classify(gates))
        gates["chain_specific_speaker_identity_pass"] = False
        self.assertEqual("FAIL_QWEN3_CLONE_SPEAKER_IDENTITY", MODULE.classify(gates))

    def test_prosody_measurement_does_not_infer_semantic_controls(self) -> None:
        rate = 24000
        t = np.arange(rate * 2, dtype=np.float32) / rate
        audio = (0.1 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)
        result = MODULE.measure_prosody(audio, rate, 8)
        self.assertAlmostEqual(180.0, result["pitch_median_hz"], delta=3.0)
        self.assertFalse(result["delivery_style_inferred"])
        self.assertFalse(result["intensity_class_inferred"])
        self.assertFalse(result["emotion_class_inferred"])

    def test_lineage_rejects_production_authorized_reference(self) -> None:
        manifest = {
            "classification": "QWEN3_TTS_BASE_ICL_CLONE_GENERATED_AUTOMATED_QA_PENDING",
            "candidate_id": MODULE.EXPECTED_CANDIDATE_ID,
            "engine": {"repository": MODULE.EXPECTED_ENGINE, "revision": MODULE.EXPECTED_REVISION},
            "request": {"text": MODULE.EXPECTED_TEXT, "seed": 12401, "clone_mode": "icl", "x_vector_only_mode": False},
            "reference": {"sha256": MODULE.EXPECTED_REFERENCE_SHA256, "transcript": MODULE.EXPECTED_REFERENCE_TEXT, "production_authorized": True},
            "output": {},
            "boundaries": {"automated_qa_complete": False, "production_ready": False},
        }
        with self.assertRaises(MODULE.EvaluationError):
            MODULE.verify_lineage(manifest, Path("missing.wav"), "0" * 64)


if __name__ == "__main__":
    unittest.main()
