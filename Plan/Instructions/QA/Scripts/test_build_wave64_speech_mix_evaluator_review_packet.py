from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_speech_mix_evaluator_review_packet.py"
SPEC = importlib.util.spec_from_file_location("wave64_speech_mix_packet", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Wave64SpeechMixEvaluatorReviewPacketTests(unittest.TestCase):
    def test_resample_channels_is_deterministic_and_preserves_channels(self) -> None:
        source = np.column_stack((np.linspace(-0.2, 0.2, 2400), np.linspace(0.2, -0.2, 2400))).astype(np.float32)
        first = MODULE.resample_channels(source, 24000, 16000)
        second = MODULE.resample_channels(source, 24000, 16000)
        self.assertEqual(first.shape, (1600, 2))
        self.assertTrue(np.array_equal(first, second))

    def test_build_stems_emits_exact_format_and_sample_sum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rate = 24000
            time = np.arange(rate * 2, dtype=np.float32) / rate
            dry = (0.1 * np.sin(2 * np.pi * 220 * time)).astype(np.float32)
            spatial = np.column_stack((dry * 0.6, dry * 0.4)).astype(np.float32)
            dry_path = root / "dry.wav"
            spatial_path = root / "spatial.wav"
            sf.write(str(dry_path), dry, rate, subtype="PCM_24")
            sf.write(str(spatial_path), spatial, rate, subtype="PCM_24")
            bindings, metadata = MODULE.build_stems(dry_path, spatial_path, root / "out")
            self.assertEqual(metadata["sample_rate_hz"], 16000)
            self.assertFalse(metadata["gain_or_normalization_applied_to_final_mix"])
            decoded = {}
            for name, binding in bindings.items():
                audio, observed_rate = sf.read(binding["path"], dtype="float32", always_2d=True)
                decoded[name] = audio
                self.assertEqual(observed_rate, 16000)
                self.assertEqual(audio.shape[1], 2)
            residual = decoded["final_mix"] - decoded["spatial_dialogue"] - decoded["ambience_bed"]
            self.assertLess(float(np.max(np.abs(residual))), 2e-6)
            self.assertFalse(np.array_equal(decoded["previous_ambience"], decoded["current_ambience"]))

    def test_manifest_source_keeps_authority_fail_closed(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"automated_metrics_are_human_review": False', text)
        self.assertIn('"human_review_fabricated": False', text)
        self.assertIn('"production_ready": False', text)
        self.assertIn('"human_review_record_present": False', text)
        self.assertIn('"row_complete": False', text)


if __name__ == "__main__":
    unittest.main()
