from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/verify_wave64_room_spatial_full_mix_runtime.py"
SPEC = importlib.util.spec_from_file_location("verify_wave64_room_spatial_full_mix_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RoomSpatialFullMixRuntimeTests(unittest.TestCase):
    def write_pcm(self, path: Path, frames: int = MODULE.EXPECTED_AUDIO_FRAMES) -> None:
        samples = array("h")
        for index in range(frames):
            value = int(4000 * math.sin(2 * math.pi * 220 * index / MODULE.EXPECTED_RATE))
            samples.extend((value, value))
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(MODULE.EXPECTED_RATE)
            handle.writeframes(samples.tobytes())

    def test_pcm_profile_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.wav"
            self.write_pcm(path)
            samples, metrics = MODULE.read_pcm16_stereo(path)
            self.assertEqual(MODULE.EXPECTED_AUDIO_FRAMES * 2, len(samples))
            self.assertEqual(0.0, metrics["clipping_ratio"])
            self.assertEqual(0.0, metrics["stereo_balance_delta"])

    def test_pcm_profile_rejects_wrong_rate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(16_000)
                handle.writeframes(array("h", [0, 0] * MODULE.EXPECTED_AUDIO_FRAMES).tobytes())
            with self.assertRaisesRegex(MODULE.RuntimeVerificationError, "unexpected PCM profile"):
                MODULE.read_pcm16_stereo(path)

    def test_linear_mix_fit_recovers_gain(self) -> None:
        voice = array("h", [100, 200, -300, 400] * 8)
        foley = array("h", [50, -20, 70, -40] * 8)
        ambience = array("h", [10, 30, -20, 40] * 8)
        gain = 2.5
        final_mix = array("h")
        for v, f, a in zip(voice, foley, ambience, strict=True):
            final_mix.append(round(gain * (v + 0.16 * f + 0.45 * a)))
        metrics = MODULE.fitted_linear_mix_metrics(voice, foley, ambience, final_mix)
        self.assertAlmostEqual(gain, metrics["fitted_linear_loudness_gain"], places=2)
        self.assertLess(metrics["normalized_reconstruction_rmse"], 0.01)

    def test_linear_mix_fit_rejects_shape_mismatch(self) -> None:
        with self.assertRaisesRegex(MODULE.RuntimeVerificationError, "equal length"):
            MODULE.fitted_linear_mix_metrics(array("h", [1]), array("h", [1, 2]), array("h", [1]), array("h", [1]))

    def test_binding_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.bin"
            path.write_bytes(b"fixture")
            with self.assertRaisesRegex(MODULE.RuntimeVerificationError, "SHA-256 mismatch"):
                MODULE.binding(path, "0" * 64)

    def test_classification_is_fail_closed(self) -> None:
        self.assertIn("AUTHORITY_BLOCKED", MODULE.CLASSIFICATION)
        self.assertNotIn("PRODUCTION_PASS", MODULE.CLASSIFICATION)
        self.assertEqual(48, MODULE.CORRECTED_AUDIO_FRAMES - MODULE.EXPECTED_AUDIO_FRAMES)


if __name__ == "__main__":
    unittest.main()
