from __future__ import annotations

import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_genuine_audio_review_mux_correction.py"
SPEC = importlib.util.spec_from_file_location("build_wave64_genuine_audio_review_mux_correction", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class GenuineAudioReviewMuxCorrectionTests(unittest.TestCase):
    def write_source(self, path: Path, frames: int = MODULE.SOURCE_AUDIO_FRAMES, rate: int = MODULE.EXPECTED_RATE) -> None:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(rate)
            handle.writeframes(b"\x01\x00\x01\x00" * frames)

    def test_padding_is_exact_and_source_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            output = root / "output.wav"
            self.write_source(source)
            before = MODULE.sha256_file(source)
            result = MODULE.write_padded_pcm16_stereo(source, output)
            self.assertEqual(48, result["padding_frames"])
            self.assertEqual(MODULE.TARGET_AUDIO_FRAMES, result["target_frames"])
            self.assertEqual(before, MODULE.sha256_file(source))
            with wave.open(str(output), "rb") as handle:
                self.assertEqual(MODULE.TARGET_AUDIO_FRAMES, handle.getnframes())

    def test_padding_rejects_wrong_source_rate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            self.write_source(source, rate=16_000)
            with self.assertRaisesRegex(MODULE.MuxCorrectionError, "source mix profile is invalid"):
                MODULE.write_padded_pcm16_stereo(source, root / "output.wav")

    def test_binding_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.bin"
            path.write_bytes(b"fixture")
            with self.assertRaisesRegex(MODULE.MuxCorrectionError, "SHA-256 mismatch"):
                MODULE.binding(path, "0" * 64)

    def test_correction_constants_match_one_millisecond_pad(self) -> None:
        self.assertEqual(48, MODULE.TARGET_AUDIO_FRAMES - MODULE.SOURCE_AUDIO_FRAMES)
        self.assertEqual(0.001, (MODULE.TARGET_AUDIO_FRAMES - MODULE.SOURCE_AUDIO_FRAMES) / MODULE.EXPECTED_RATE)

    def test_authoritative_duration_does_not_trust_container_average_rate(self) -> None:
        self.assertEqual(49 / 24.0, MODULE.authoritative_video_duration(49, 24.0))
        with self.assertRaises(MODULE.MuxCorrectionError):
            MODULE.authoritative_video_duration(49, 0.0)


if __name__ == "__main__":
    unittest.main()
