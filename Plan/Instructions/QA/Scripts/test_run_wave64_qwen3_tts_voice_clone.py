from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_wave64_qwen3_tts_voice_clone.py"
SPEC = importlib.util.spec_from_file_location("qwen_voice_clone", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenVoiceCloneRunnerTests(unittest.TestCase):
    def test_candidate_paths_are_seed_specific_and_clone_specific(self) -> None:
        wav, manifest = MODULE.candidate_paths(Path("out"), 12401)
        self.assertEqual("qwen3_tts_base_icl_clone_seed12401.wav", wav.name)
        self.assertEqual("qwen3_tts_base_icl_clone_seed12401.manifest.json", manifest.name)

    def test_reference_verification_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reference = Path(temporary) / "reference.wav"
            reference.write_bytes(b"not-the-authorized-reference")
            with self.assertRaisesRegex(MODULE.CloneError, "SHA-256 mismatch"):
                MODULE.verify_reference(reference)

    def test_model_verification_requires_exact_base_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(MODULE.CloneError, "size mismatch"):
                MODULE.verify_files(Path(temporary))

    def test_contract_keeps_reference_and_target_text_distinct(self) -> None:
        self.assertNotEqual(MODULE.REFERENCE_TRANSCRIPT, MODULE.TARGET_TEXT)
        self.assertFalse(MODULE.GENERATION["max_new_tokens"] > 512)

    def test_runtime_version_drift_fails_closed(self) -> None:
        self.assertEqual(
            MODULE.EXPECTED_RUNTIME_PACKAGES,
            MODULE.validate_runtime_versions(dict(MODULE.EXPECTED_RUNTIME_PACKAGES)),
        )
        with self.assertRaisesRegex(MODULE.CloneError, "runtime identity drift"):
            MODULE.validate_runtime_versions({"torch": "2.11.0+cu128", "torchaudio": "2.10.0"})


if __name__ == "__main__":
    unittest.main()
