from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "prepare_wave64_qwen3_tts_base_acquisition.py"
SPEC = importlib.util.spec_from_file_location("qwen_base_preparation", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenBaseAcquisitionPreparationTests(unittest.TestCase):
    def test_exact_file_set_is_complete_and_unique(self) -> None:
        self.assertEqual(11, len(MODULE.SOURCE_FILES))
        self.assertEqual(11, len({digest for _, digest in MODULE.SOURCE_FILES.values()}))
        self.assertEqual(4_544_170_364, sum(size for size, _ in MODULE.SOURCE_FILES.values()))

    def test_nested_tokenizer_file_preserves_target_subdirectory(self) -> None:
        size, digest = MODULE.SOURCE_FILES["speech_tokenizer/config.json"]
        request = MODULE.build_request("speech_tokenizer/config.json", size, digest)
        self.assertEqual("audio/tts/qwen3_tts_1_7b_base/speech_tokenizer", request["asset"]["target_subdir"])
        self.assertEqual("config.json", request["asset"]["filename"])
        self.assertEqual("speech_tokenizer/config.json", request["source"]["filename"])

    def test_request_preserves_license_and_suppression_boundaries(self) -> None:
        size, digest = MODULE.SOURCE_FILES["model.safetensors"]
        request = MODULE.build_request("model.safetensors", size, digest)
        self.assertEqual(MODULE.REVISION, request["source"]["revision"])
        self.assertEqual("apache-2.0", request["policy"]["license_id"])
        self.assertFalse(request["policy"]["content_based_suppression"])
        self.assertFalse(request["policy"]["allow_browser_fallback"])


if __name__ == "__main__":
    unittest.main()
