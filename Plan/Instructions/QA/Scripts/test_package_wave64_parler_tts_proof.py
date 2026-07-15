import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = ROOT / "Plan/07_IMPLEMENTATION/scripts"
SCRIPT = SCRIPT_DIR / "package_wave64_parler_tts_proof.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_parler_tts_proof", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC.loader.exec_module(MODULE)


class PackageWave64ParlerTTSProofTests(unittest.TestCase):
    def _wav(self, path: Path, frames: int = 8000) -> None:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(b"\x01\x00" * frames)

    def test_conform_pads_to_exact_duration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "source.wav", root / "target.wav"
            self._wav(source, 8000)
            result = MODULE.conform_pcm16_mono(source, target, 1.0)
            self.assertEqual(result["padding_frames"], 8000)
            with wave.open(str(target), "rb") as handle:
                self.assertEqual(handle.getnframes(), 16000)

    def test_conform_refuses_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "source.wav", root / "target.wav"
            self._wav(source, 16001)
            with self.assertRaisesRegex(ValueError, "refuses"):
                MODULE.conform_pcm16_mono(source, target, 1.0)

    def test_normalized_tokens_fold_case_and_punctuation(self):
        self.assertEqual(MODULE.normalized_tokens("Move on the B."), ["move", "on", "the", "b"])

    def test_levenshtein_counts_one_substitution(self):
        self.assertEqual(MODULE.levenshtein(["the", "beat"], ["the", "b"]), 1)

    def test_levenshtein_handles_empty_input(self):
        self.assertEqual(MODULE.levenshtein([], ["one", "two"]), 2)


if __name__ == "__main__":
    unittest.main()
