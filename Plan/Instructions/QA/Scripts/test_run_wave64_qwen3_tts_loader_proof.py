from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_wave64_qwen3_tts_loader_proof.py"
SPEC = importlib.util.spec_from_file_location("qwen_loader", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenLoaderProofTests(unittest.TestCase):
    def test_acquisition_validation_hashes_exact_file_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "models/audio/tts/qwen/config.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"{}")
            digest = MODULE.sha256_file(target)
            bundle = {
                "asset_id": "qwen3_tts_1_7b_voicedesign",
                "revision": "rev",
                "files": [{"source_path": "config.json", "sha256": digest, "bytes": 2}],
            }
            acquisition = {
                "classification": "HF_SPEECH_REPOSITORY_ACQUIRED_HASH_VERIFIED_RUNTIME_PENDING",
                "revision": "rev",
                "files": [{"source_path": "config.json", "sha256": digest, "target_path": str(target)}],
            }
            result = MODULE.validate_acquisition(root, bundle, acquisition)
            self.assertEqual(digest, result[0]["sha256"])
            self.assertEqual(
                "models/audio/tts/qwen3_tts_1_7b_voicedesign/config.json",
                result[0]["path"],
            )

    def test_acquisition_validation_rejects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "model.safetensors"
            target.write_bytes(b"wrong")
            bundle = {
                "asset_id": "qwen3_tts_1_7b_voicedesign",
                "revision": "rev",
                "files": [{"source_path": "model.safetensors", "sha256": "0" * 64, "bytes": 5}],
            }
            acquisition = {
                "classification": "HF_SPEECH_REPOSITORY_ACQUIRED_HASH_VERIFIED_RUNTIME_PENDING",
                "revision": "rev",
                "files": [{"source_path": "model.safetensors", "sha256": "0" * 64, "target_path": str(target)}],
            }
            with self.assertRaises(MODULE.LoaderProofError):
                MODULE.validate_acquisition(root, bundle, acquisition)

    def test_adapter_registry_keeps_generation_and_production_blocked(self) -> None:
        registry = MODULE.build_adapter_registry(
            [{"filename": "model.safetensors", "sha256": "a" * 64, "bytes": 1}],
            MODULE.EXPECTED_PACKAGES,
            [{"filename": "qwen.whl", "sha256": "b" * 64, "bytes": 1}],
            "proof.json",
            "c" * 64,
            {"sox_executable_available": False},
        )
        adapter = registry["adapters"][0]
        self.assertEqual("load_proven", adapter["runtime_status"])
        self.assertFalse(adapter["capabilities"]["candidate_generation_proven"])
        self.assertFalse(adapter["production_ready"])
        self.assertFalse(adapter["content_based_suppression"])


if __name__ == "__main__":
    unittest.main()
