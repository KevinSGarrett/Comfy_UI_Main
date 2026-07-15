import importlib.util
import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_parler_tts_dialogue.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_parler_tts_dialogue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunWave64ParlerTTSDialogueTests(unittest.TestCase):
    def _args(self, base: Path):
        model = base / "model"
        model.mkdir()
        weight = model / "model.safetensors"
        weight.write_bytes(b"weight")
        return SimpleNamespace(
            model_dir=str(model),
            output_dir=str(base / "output"),
            prompt="A real line.",
            description="A focused voice.",
            contract_start=1.2,
            contract_end=4.2,
            model_weight_sha256=MODULE.sha256(weight),
        )

    def test_sha256_streams_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "value.bin"
            path.write_bytes(b"exact")
            self.assertEqual(
                MODULE.sha256(path),
                "fa79d4746c21cd960a17b92db8976ddef95a7e20b590721f8e0fa7847a05e486",
            )

    def test_validate_inputs_accepts_exact_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            model, output, weight = MODULE.validate_inputs(args)
            self.assertTrue(model.is_dir())
            self.assertFalse(output.exists())
            self.assertTrue(weight.is_file())

    def test_validate_inputs_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.model_weight_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_refuses_output_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            Path(args.output_dir).mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_empty_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.prompt = " "
            with self.assertRaisesRegex(ValueError, "non-empty"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_invalid_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.contract_end = args.contract_start
            with self.assertRaisesRegex(ValueError, "exceed"):
                MODULE.validate_inputs(args)

    def test_inspect_pcm_reports_signal_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tone.wav"
            samples = array("h", [int(math.sin(index / 10) * 10000) for index in range(1600)])
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(samples.tobytes())
            result = MODULE.inspect_pcm(path)
            self.assertEqual(result["duration_seconds"], 0.1)
            self.assertLess(result["rms_dbfs"], 0)
            self.assertEqual(result["clipping_ratio"], 0)

    def test_contract_token_cap_includes_allowed_delta(self):
        self.assertEqual(MODULE.max_tokens_for_contract(1.2, 4.2, 0.35), 289)

    def test_contract_token_cap_rejects_negative_delta(self):
        with self.assertRaisesRegex(ValueError, "invalid"):
            MODULE.max_tokens_for_contract(1.2, 4.2, -0.01)

    def test_engine_identity_reads_runtime_distribution(self):
        direct_url = '{"url":"https://github.com/huggingface/parler-tts.git","vcs_info":{"commit_id":"d108732cd57788ec86bc857d99a6cabd66663d68"}}'
        distribution = SimpleNamespace(version="0.2.2", read_text=lambda name: direct_url)
        with mock.patch.object(MODULE.metadata, "distribution", return_value=distribution):
            identity = MODULE.verify_engine_identity()
        self.assertEqual(identity["version"], "0.2.2")
        self.assertEqual(identity["commit"], MODULE.EXPECTED_ENGINE_COMMIT)

    def test_engine_identity_rejects_commit_drift(self):
        direct_url = '{"url":"https://example.test/repo","vcs_info":{"commit_id":"wrong"}}'
        distribution = SimpleNamespace(version="0.2.2", read_text=lambda name: direct_url)
        with mock.patch.object(MODULE.metadata, "distribution", return_value=distribution):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                MODULE.verify_engine_identity()

    def test_engine_identity_rejects_version_drift(self):
        direct_url = '{"url":"https://github.com/huggingface/parler-tts.git","vcs_info":{"commit_id":"d108732cd57788ec86bc857d99a6cabd66663d68"}}'
        distribution = SimpleNamespace(version="0.2.3", read_text=lambda name: direct_url)
        with mock.patch.object(MODULE.metadata, "distribution", return_value=distribution):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                MODULE.verify_engine_identity()


if __name__ == "__main__":
    unittest.main()
