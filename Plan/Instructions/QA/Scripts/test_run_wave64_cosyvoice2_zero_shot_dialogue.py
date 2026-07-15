import importlib.util
import math
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_cosyvoice2_zero_shot_dialogue.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_cosyvoice2_zero_shot_dialogue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunWave64CosyVoice2ZeroShotDialogueTests(unittest.TestCase):
    def _write_wav(self, path: Path):
        samples = array("h", [int(math.sin(index / 10) * 10000) for index in range(2400)])
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(samples.tobytes())

    def _args(self, base: Path):
        model = base / "model"
        source = base / "source"
        model.mkdir()
        source.mkdir()
        prompt = base / "prompt.wav"
        self._write_wav(prompt)
        return SimpleNamespace(
            model_dir=str(model),
            source_dir=str(source),
            prompt_wav=str(prompt),
            prompt_wav_sha256=MODULE.sha256(prompt),
            output_dir=str(base / "output"),
            prompt_transcript="Once upon a midnight",
            text="We hold the frame steady and move on the beat.",
            style_emotion="focused",
            style_intensity="controlled",
            contract_start=1.2,
            contract_end=4.2,
            max_duration_delta=0.35,
            speed=1.0,
        )

    def test_sha256_streams_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "value.bin"
            path.write_bytes(b"exact")
            self.assertEqual(
                MODULE.sha256(path),
                "fa79d4746c21cd960a17b92db8976ddef95a7e20b590721f8e0fa7847a05e486",
            )

    def test_validate_inputs_accepts_bound_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            model, source, prompt, output = MODULE.validate_inputs(args)
            self.assertTrue(model.is_dir())
            self.assertTrue(source.is_dir())
            self.assertTrue(prompt.is_file())
            self.assertFalse(output.exists())

    def test_validate_inputs_rejects_reference_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.prompt_wav_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "reference-speaker WAV SHA-256 mismatch"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_refuses_output_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            Path(args.output_dir).mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_empty_prompt_transcript(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.prompt_transcript = " "
            with self.assertRaisesRegex(ValueError, "prompt transcript"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_style_substitution_by_omission(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.style_emotion = " "
            with self.assertRaisesRegex(ValueError, "style emotion"):
                MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_speed_outside_predeclared_range(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary))
            args.speed = 1.21
            with self.assertRaisesRegex(ValueError, "predeclared"):
                MODULE.validate_inputs(args)

    def test_activate_source_path_is_first_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve()
            matcha = source / "third_party/Matcha-TTS"
            matcha.mkdir(parents=True)
            source_paths = [str(source), str(matcha)]
            original = list(sys.path)
            try:
                sys.path.extend(source_paths + source_paths)
                self.assertEqual(MODULE.activate_source_path(source), source_paths)
                self.assertEqual(sys.path[:2], source_paths)
                self.assertTrue(all(sys.path.count(path) == 1 for path in source_paths))
                MODULE.activate_source_path(source)
                self.assertTrue(all(sys.path.count(path) == 1 for path in source_paths))
            finally:
                sys.path[:] = original

    def test_activate_source_path_rejects_missing_matcha_submodule(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Matcha-TTS"):
                MODULE.activate_source_path(Path(temporary))

    def test_inspect_pcm_reports_signal_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tone.wav"
            self._write_wav(path)
            result = MODULE.inspect_pcm(path)
            self.assertEqual(result["duration_seconds"], 0.1)
            self.assertLess(result["rms_dbfs"], 0)
            self.assertEqual(result["clipping_ratio"], 0)

    def test_soundfile_compat_rejects_low_sample_rate(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "low_rate.wav"
            samples = array("h", [1000] * 800)
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(samples.tobytes())
            decoder = SimpleNamespace(read=lambda *args, **kwargs: (None, 8000))
            with mock.patch.dict(
                sys.modules,
                {
                    "soundfile": decoder,
                    "torch": SimpleNamespace(),
                    "torchaudio": SimpleNamespace(),
                },
            ):
                with self.assertRaisesRegex(ValueError, "at least 16000"):
                    MODULE.load_wav_soundfile_compat(str(path), 16000)

    def test_hash_model_payloads_requires_every_declared_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary)
            for relative in MODULE.REQUIRED_MODEL_FILES:
                path = model / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode("utf-8"))
            payloads = MODULE.hash_model_payloads(model)
            self.assertEqual(len(payloads), len(MODULE.REQUIRED_MODEL_FILES))
            (model / MODULE.REQUIRED_MODEL_FILES[-1]).unlink()
            with self.assertRaisesRegex(ValueError, "missing or empty"):
                MODULE.hash_model_payloads(model)

    def test_source_identity_rejects_cosyvoice_commit_drift(self):
        with mock.patch.object(
            MODULE,
            "git_commit",
            side_effect=["wrong", MODULE.EXPECTED_MATCHA_COMMIT],
        ):
            with self.assertRaisesRegex(ValueError, "CosyVoice source commit mismatch"):
                MODULE.verify_source_identity(Path("source"))

    def test_source_identity_accepts_exact_commits(self):
        with mock.patch.object(
            MODULE,
            "git_commit",
            side_effect=[MODULE.EXPECTED_COSYVOICE_COMMIT, MODULE.EXPECTED_MATCHA_COMMIT],
        ):
            result = MODULE.verify_source_identity(Path("source"))
        self.assertEqual(result["cosyvoice_commit"], MODULE.EXPECTED_COSYVOICE_COMMIT)
        self.assertEqual(result["matcha_tts_commit"], MODULE.EXPECTED_MATCHA_COMMIT)

    def test_runtime_package_identity_fails_closed_on_missing_distribution(self):
        with mock.patch.object(
            MODULE.metadata,
            "version",
            side_effect=MODULE.metadata.PackageNotFoundError("missing"),
        ):
            with self.assertRaisesRegex(ValueError, "required runtime distribution"):
                MODULE.runtime_package_identity()


if __name__ == "__main__":
    unittest.main()
