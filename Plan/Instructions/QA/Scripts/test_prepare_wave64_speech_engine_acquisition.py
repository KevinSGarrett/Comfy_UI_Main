from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts"
SCRIPT = SCRIPT_DIR / "prepare_wave64_speech_engine_acquisition.py"
SPEC = importlib.util.spec_from_file_location("speech_acquisition", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
import sys

sys.path.insert(0, str(SCRIPT_DIR))
SPEC.loader.exec_module(MODULE)


ASSET = {
    "asset_id": "test_speech_engine",
    "capability": "test speech",
    "provider": "huggingface",
    "repo_id": "owner/repo",
    "revision": "0123456789abcdef0123456789abcdef01234567",
    "license": "apache-2.0",
}


class SpeechRepositoryAcquisitionTests(unittest.TestCase):
    def test_runtime_tree_excludes_repository_documents(self) -> None:
        tree = [
            {"path": ".gitattributes", "type": "file", "size": 1},
            {"path": "README.md", "type": "file", "size": 1},
            {"path": "config.json", "type": "file", "size": 2},
            {"path": "subdir", "type": "directory", "size": 0},
        ]
        self.assertEqual(["config.json"], [item["path"] for item in MODULE.runtime_repository_files(tree)])

    def test_lfs_oid_is_exact_sha256_without_fetch(self) -> None:
        called = False

        def fetcher(_url: str):
            nonlocal called
            called = True
            return b"", {}

        value = MODULE.source_identity(
            "owner/repo",
            ASSET["revision"],
            {"path": "model.safetensors", "size": 123, "lfs": {"oid": "a" * 64}},
            fetcher,
        )
        self.assertEqual(("a" * 64, 123, "huggingface_lfs_oid_sha256"), value)
        self.assertFalse(called)

    def test_small_file_is_hashed_from_official_bytes(self) -> None:
        payload = b"{}"
        value = MODULE.source_identity(
            "owner/repo",
            ASSET["revision"],
            {"path": "config.json", "size": len(payload)},
            lambda _url: (payload, {}),
        )
        self.assertEqual(64, len(value[0]))
        self.assertEqual("downloaded_official_small_file_sha256", value[2])

    def test_request_is_fail_closed_and_preserves_subdirectory(self) -> None:
        request = MODULE.request_for_file(
            ASSET,
            {"path": "speech_tokenizer/model.safetensors"},
            "b" * 64,
            100,
        )
        self.assertEqual("audio/tts/test_speech_engine/speech_tokenizer", request["asset"]["target_subdir"])
        self.assertFalse(request["policy"]["content_based_suppression"])
        self.assertFalse(request["policy"]["allow_browser_fallback"])
        self.assertIn(ASSET["revision"], request["source"]["revision"])

    def test_prepare_bundle_writes_exact_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / MODULE.CATALOG
            catalog.parent.mkdir(parents=True)
            catalog.write_text(json.dumps({"official_asset_groups": [ASSET]}), encoding="utf-8")
            control = root / MODULE.acquisition.CONTROL_REGISTRY
            control.parent.mkdir(parents=True, exist_ok=True)
            control.write_text(json.dumps({"placement_map": {"audio_model": "audio"}}), encoding="utf-8")
            tree = [
                {"path": "config.json", "type": "file", "size": 2},
                {"path": "model.safetensors", "type": "file", "size": 100, "lfs": {"oid": "c" * 64}},
            ]
            bundle = MODULE.prepare_bundle(
                root,
                ASSET["asset_id"],
                root / "runtime_artifacts" / "bundle",
                tree_fetcher=lambda _repo, _revision: tree,
                small_file_fetcher=lambda _url: (b"{}", {}),
            )
            self.assertEqual(2, bundle["file_count"])
            self.assertEqual(102, bundle["total_bytes"])
            self.assertEqual("not_acquired", bundle["runtime_status"])
            self.assertFalse(bundle["content_based_suppression"])
            self.assertTrue((root / "runtime_artifacts" / "bundle" / "bundle.json").is_file())

    def test_acquire_bundle_uses_controller_destination_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            bundle_path = root / "bundle.json"
            bundle_path.write_text(
                json.dumps(
                    {
                        "asset_id": "engine",
                        "repo_id": "owner/repo",
                        "revision": ASSET["revision"],
                        "license": "apache-2.0",
                        "files": [{"source_path": "config.json", "manifest_path": str(manifest_path)}],
                    }
                ),
                encoding="utf-8",
            )
            result = {
                "destination_path": "models/audio/tts/engine/config.json",
                "sha256": "d" * 64,
                "bytes": 2,
                "acquisition_method": "api",
                "runtime_validation_status": "queued",
            }
            with (
                mock.patch.object(MODULE.acquisition, "download_to_staging", return_value=root / "candidate"),
                mock.patch.object(MODULE.acquisition, "finalize", return_value=result),
            ):
                value = MODULE.acquire_bundle(root, bundle_path, "http://127.0.0.1:9/object_info")
            self.assertEqual("models/audio/tts/engine/config.json", value["files"][0]["target_path"])


if __name__ == "__main__":
    unittest.main()
