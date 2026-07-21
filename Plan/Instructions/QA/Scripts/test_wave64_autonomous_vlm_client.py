#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_autonomous_vlm_client.py"


def _load():
    spec = importlib.util.spec_from_file_location("wave64_autonomous_vlm_client", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class Wave64AutonomousVlmClientTests(unittest.TestCase):
    def test_default_vlm_model_is_llava_13b(self) -> None:
        self.assertEqual(MOD.DEFAULT_VLM_MODEL, "llava:13b")

    def test_resolve_base_url_prefers_wave64_vlm_url(self) -> None:
        env = {
            "WAVE64_VLM_URL": "http://127.0.0.1:11434",
            "OLLAMA_HOST": "http://9.9.9.9:1",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertEqual(MOD.resolve_base_url(), "http://127.0.0.1:11434")

    def test_resolve_base_url_falls_back_to_ollama_host_and_default(self) -> None:
        with mock.patch.dict("os.environ", {"OLLAMA_HOST": "127.0.0.1:11434"}, clear=True):
            self.assertEqual(MOD.resolve_base_url(), "http://127.0.0.1:11434")
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(MOD.resolve_base_url(), "http://127.0.0.1:11434")

    def test_resolve_vlm_model_defaults_to_llava_13b(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(MOD.resolve_vlm_model(), "llava:13b")

    def test_resolve_vlm_model_reads_env_and_explicit(self) -> None:
        with mock.patch.dict("os.environ", {"WAVE64_VLM_MODEL": "llama3.2-vision:11b"}, clear=True):
            self.assertEqual(MOD.resolve_vlm_model(), "llama3.2-vision:11b")
            self.assertEqual(MOD.resolve_vlm_model("llava:13b"), "llava:13b")

    def test_resolve_vlm_endpoint_receipt_boundaries(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "WAVE64_VLM_URL": "http://127.0.0.1:11434",
                "WAVE64_VLM_MODEL": "llava:13b",
                "WAVE64_LLM_MODEL": "qwen2.5:7b-instruct",
            },
            clear=True,
        ):
            receipt = MOD.resolve_vlm_endpoint()
        self.assertEqual(receipt["WAVE64_VLM_URL"], "http://127.0.0.1:11434")
        self.assertEqual(receipt["WAVE64_VLM_MODEL"], "llava:13b")
        self.assertFalse(receipt["product_completion_claimed"])
        self.assertTrue(receipt["row074_pcm_left_alone"])

    def test_chat_with_images_uses_resolved_vlm_model_mocked(self) -> None:
        fake = {
            "message": {"content": json.dumps({"verdict": "pass", "overall_score": 0.6})},
            "eval_count": 12,
        }
        with mock.patch.dict(
            "os.environ",
            {"WAVE64_VLM_URL": "http://vlm.test:11434", "WAVE64_VLM_MODEL": "llava:13b"},
            clear=True,
        ):
            with mock.patch.object(MOD, "_http_json", return_value=fake) as http:
                out = MOD.chat_with_images("score", ["YmFzZTY0"], timeout_s=1.0)
        self.assertEqual(out["model"], "llava:13b")
        self.assertEqual(out["base_url"], "http://vlm.test:11434")
        self.assertEqual(out["parsed_json"]["verdict"], "pass")
        self.assertFalse(out["product_completion_claimed"])
        self.assertTrue(out["row074_pcm_left_alone"])
        args, kwargs = http.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "http://vlm.test:11434/api/chat")
        self.assertEqual(args[2]["model"], "llava:13b")
        self.assertEqual(args[2]["messages"][0]["images"], ["YmFzZTY0"])


if __name__ == "__main__":
    unittest.main()
