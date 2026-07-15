import importlib.util
import json
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_chatterbox_dialogue.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_chatterbox_dialogue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_wav(path: Path, frames: int = 24000, sample_rate: int = 24000) -> None:
    samples = array("h", [1000] * frames)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


class RunWave64ChatterboxDialogueTests(unittest.TestCase):
    def args(self, base: Path, prompt: Path) -> SimpleNamespace:
        return SimpleNamespace(
            model_dir=str(base / "model"),
            prompt_wav=str(prompt),
            prompt_wav_sha256=MODULE.EXPECTED_REFERENCE_SHA256,
            prompt_transcript=MODULE.EXPECTED_REFERENCE_TRANSCRIPT,
            output_dir=str(base / "output"),
            run_id="test",
            text=MODULE.EXPECTED_TEXT,
            output_name="candidate.wav",
            character_id="C01",
            line_id="L001",
            style_emotion="focused",
            style_intensity="controlled",
            contract_start=1.2,
            contract_end=4.2,
            max_duration_delta=MODULE.EXPECTED_MAX_DURATION_DELTA,
            exaggeration=MODULE.EXPECTED_EXAGGERATION,
            cfg_weight=MODULE.EXPECTED_CFG_WEIGHT,
            temperature=MODULE.EXPECTED_TEMPERATURE,
            repetition_penalty=MODULE.EXPECTED_REPETITION_PENALTY,
            min_p=MODULE.EXPECTED_MIN_P,
            top_p=MODULE.EXPECTED_TOP_P,
            candidate_ordinal=1,
            seed=MODULE.EXPECTED_SEED,
            reference_speaker_name="Chris Goringe",
            reference_source_page="source",
            reference_license="Public Domain Mark 1.0",
            reference_license_reference="license",
        )

    def fixture(self, base: Path):
        model = base / "model"
        model.mkdir()
        payloads = {
            "ve.safetensors": b"ve",
            "t3_cfg.safetensors": b"t3",
            "s3gen.safetensors": b"s3",
            "tokenizer.json": b"tokenizer",
            "conds.pt": b"conds",
        }
        hashes = {}
        for name, data in payloads.items():
            path = model / name
            path.write_bytes(data)
            hashes[name] = MODULE.sha256(path)
        prompt = base / "reference.wav"
        write_wav(prompt)
        return prompt, hashes

    def test_hash_model_payloads_requires_every_exact_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            _, hashes = self.fixture(base)
            with mock.patch.dict(MODULE.EXPECTED_MODEL_HASHES, hashes, clear=True):
                rows = MODULE.hash_model_payloads(base / "model")
            self.assertEqual(len(rows), 5)
            (base / "model" / "conds.pt").write_bytes(b"changed")
            with mock.patch.dict(MODULE.EXPECTED_MODEL_HASHES, hashes, clear=True):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    MODULE.hash_model_payloads(base / "model")

    def test_validate_inputs_accepts_only_approved_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            with mock.patch.object(MODULE, "EXPECTED_REFERENCE_SHA256", MODULE.sha256(prompt)):
                args.prompt_wav_sha256 = MODULE.sha256(prompt)
                model, actual_prompt, output = MODULE.validate_inputs(args)
            self.assertEqual(model, (base / "model").resolve())
            self.assertEqual(actual_prompt, prompt.resolve())
            self.assertEqual(output, (base / "output").resolve())

    def test_validate_inputs_rejects_text_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            args.text = "Different text."
            with self.assertRaisesRegex(ValueError, "reference-speaker WAV"):
                MODULE.validate_inputs(args)
            with mock.patch.object(MODULE, "EXPECTED_REFERENCE_SHA256", MODULE.sha256(prompt)):
                args.prompt_wav_sha256 = MODULE.sha256(prompt)
                with self.assertRaisesRegex(ValueError, "dialogue text"):
                    MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_control_tuning(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            args.exaggeration = 0.61
            with mock.patch.object(MODULE, "EXPECTED_REFERENCE_SHA256", MODULE.sha256(prompt)):
                args.prompt_wav_sha256 = MODULE.sha256(prompt)
                with self.assertRaisesRegex(ValueError, "exaggeration"):
                    MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_second_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            args.candidate_ordinal = 2
            with mock.patch.object(MODULE, "EXPECTED_REFERENCE_SHA256", MODULE.sha256(prompt)):
                args.prompt_wav_sha256 = MODULE.sha256(prompt)
                with self.assertRaisesRegex(ValueError, "exactly one candidate"):
                    MODULE.validate_inputs(args)

    def test_validate_inputs_rejects_timing_contract_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            args.contract_end = 4.3
            with mock.patch.object(MODULE, "EXPECTED_REFERENCE_SHA256", MODULE.sha256(prompt)):
                args.prompt_wav_sha256 = MODULE.sha256(prompt)
                with self.assertRaisesRegex(ValueError, "3.0-second"):
                    MODULE.validate_inputs(args)

    def test_runtime_identity_requires_sm120_compatible_override(self):
        versions = {
            name: "1" for name in MODULE.RUNTIME_DISTRIBUTIONS
        }
        versions.update(
            {
                "chatterbox-tts": "0.1.7",
                "torch": "2.11.0+cu128",
                "torchaudio": "2.11.0+cu128",
                "transformers": "5.2.0",
            }
        )
        with mock.patch.object(MODULE.metadata, "version", side_effect=versions.__getitem__):
            self.assertEqual(MODULE.runtime_package_identity()["torch"], "2.11.0+cu128")
        versions["torch"] = "2.6.0+cu124"
        with mock.patch.object(MODULE.metadata, "version", side_effect=versions.__getitem__):
            with self.assertRaisesRegex(ValueError, "RTX 5060"):
                MODULE.runtime_package_identity()

    def test_inspect_pcm_reports_exact_duration(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audio.wav"
            write_wav(path, frames=72000)
            pcm = MODULE.inspect_pcm(path)
            self.assertEqual(pcm["duration_seconds"], 3.0)
            self.assertEqual(pcm["sample_rate_hz"], 24000)

    def test_normalize_watermark_score_accepts_scalar_item(self):
        value = mock.Mock()
        value.item.return_value = 1.0
        self.assertEqual(MODULE.normalize_watermark_score(value), 1.0)

    def test_constants_preserve_one_candidate_contract(self):
        self.assertEqual(MODULE.EXPECTED_TEXT, "We hold the frame steady and move on the beat.")
        self.assertEqual(MODULE.EXPECTED_DURATION_SECONDS, 3.0)
        self.assertEqual(MODULE.EXPECTED_SEED, 64032)
        self.assertEqual(MODULE.MODEL_REVISION, "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18")

    def test_control_contract_hash_changes_on_any_control_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            prompt, _ = self.fixture(base)
            args = self.args(base, prompt)
            contract, first_hash = MODULE.control_contract(args)
            self.assertFalse(contract["same_control_path_retry_allowed"])
            args.cfg_weight = 0.31
            _, second_hash = MODULE.control_contract(args)
            self.assertNotEqual(first_hash, second_hash)


if __name__ == "__main__":
    unittest.main()
