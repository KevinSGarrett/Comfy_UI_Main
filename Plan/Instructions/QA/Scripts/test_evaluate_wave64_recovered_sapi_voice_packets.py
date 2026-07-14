#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_recovered_sapi_voice_packets.py"
SPEC = importlib.util.spec_from_file_location("row027_recovered_sapi", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredSapiVoicePacketTests(unittest.TestCase):
    def line(self) -> dict:
        return {
            "line_id": "L001",
            "character_id": "C01",
            "voice_profile_id": "voice_C01_placeholder",
            "text": "Test line.",
            "start_seconds": 1.2,
            "end_seconds": 4.2,
            "emotion": "focused",
            "selected_sapi_voice": {"name": "Diagnostic Voice"},
            "voice_profile_rights_status": "private_personal_use_pre_authorized",
            "recovered_wav_path": Path("C:/Comfy_UI_Main/test.wav"),
        }

    def test_profile_is_explicitly_diagnostic(self) -> None:
        profile = MODULE.build_profile(self.line(), "a" * 64)
        self.assertFalse(profile["production_grade"])
        self.assertEqual(profile["status"], "diagnostic_placeholder_profile")
        self.assertIn("not a production", profile["boundary"])

    def test_contract_preserves_original_timing_and_marks_intensity_unverified(self) -> None:
        contract = MODULE.build_contract(self.line())
        line = contract["lines"][0]
        self.assertEqual((line["start_time"], line["end_time"]), (1.2, 4.2))
        self.assertEqual(line["intensity"], "unverified_diagnostic_unknown")
        self.assertTrue(line["sync_required"])

    def test_missing_proof_set_is_exact(self) -> None:
        self.assertEqual(
            set(MODULE.MISSING_PROOF_FILES),
            {
                "asr_proof.json", "speaker_proof.json", "emotion_proof.json",
                "playback_review_proof.json", "production_runtime_proof.json",
                "production_proof_bundle.json",
            },
        )

    def test_expected_outcomes_preserve_l002_timing_failure(self) -> None:
        self.assertEqual(MODULE.EXPECTED_LINES["L001"]["overall_status"], "BLOCKED")
        self.assertEqual(MODULE.EXPECTED_LINES["L002"]["dialogue_timing_status"], "FAIL")
        self.assertEqual(MODULE.EXPECTED_LINES["L002"]["overall_status"], "FAIL")

    def test_wav_duration_reads_pcm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(b"\0\0" * 80)
            self.assertEqual(MODULE.wav_duration(path), 0.01)


if __name__ == "__main__":
    unittest.main()
