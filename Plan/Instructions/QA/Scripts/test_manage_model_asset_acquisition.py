from __future__ import annotations

import csv
import errno
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from email.message import Message
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "manage_model_asset_acquisition.py"
SPEC = importlib.util.spec_from_file_location("model_asset_acquisition", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


QUEUE_FIELDS = [
    "queue_id", "created_at", "model_name", "model_type", "base_model", "local_path",
    "workflow_lane", "test_workflow_path", "expected_result", "priority", "status", "evidence_path",
]


def request(provider: str = "civitai") -> dict:
    source = (
        {"model_version_id": "456", "file_id": "9"}
        if provider == "civitai"
        else {
            "repo_id": "owner/repo",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "filename": "models/test.safetensors",
        }
    )
    return {
        "schema_version": "1.0",
        "request_id": "TEST-ASSET-001",
        "capability_need": "Exact test model for a bounded image lane.",
        "intended_use": "Exercise deterministic acquisition and workflow binding.",
        "provider": provider,
        "source": source,
        "asset": {
            "model_name": "Test Model",
            "model_type": "LORA",
            "base_model": "sdxl",
            "target_subdir": "loras/test",
            "filename": "test.safetensors",
        },
        "integration": {
            "workflow_lane": "test_lane",
            "compatible_engines": ["sdxl"],
            "runtime_requirements_path": "Workflows/test/runtime_requirements.json",
            "model_role": "detail_lora",
            "test_workflow_path": "Workflows/test/workflow.api.json",
            "workflow_bindings": [
                {
                    "workflow_path": "Workflows/test/workflow.api.json",
                    "node_id": "2",
                    "input_name": "lora_name",
                }
            ],
        },
        "policy": {
            "license_status": "source_terms_recorded",
            "content_based_suppression": False,
            "adult_or_nsfw_metadata_is_not_a_filter": True,
            "allow_browser_fallback": True,
        },
    }


def civitai_metadata(payload: bytes) -> dict:
    return {
        "id": 456,
        "modelId": 123,
        "name": "Version One",
        "baseModel": "SDXL 1.0",
        "trainedWords": ["test-trigger"],
        "downloadUrl": "https://civitai.com/api/download/models/456",
        "files": [
            {
                "id": 9,
                "name": "source.safetensors",
                "primary": True,
                "sizeBytes": len(payload),
                "hashes": {"SHA256": MODULE.hashlib.sha256(payload).hexdigest()},
            }
        ],
    }


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/octet-stream", status: int = 200) -> None:
        self._stream = io.BytesIO(payload)
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Disposition"] = 'attachment; filename="source.safetensors"'

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


class ModelAssetAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "Plan/Registries/Models").mkdir(parents=True)
        (self.root / "Plan/Registries/Models/model_registry.jsonl").write_text("", encoding="utf-8")
        with (self.root / "Plan/Registries/Models/model_runtime_validation_queue.csv").open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=QUEUE_FIELDS, lineterminator="\n").writeheader()
        (self.root / "Plan/10_REGISTRIES").mkdir(parents=True)
        (self.root / MODULE.CONTROL_REGISTRY).write_text(
            json.dumps({"placement_map": {"LORA": "loras"}}) + "\n",
            encoding="utf-8",
        )
        (self.root / "Workflows/test").mkdir(parents=True)
        (self.root / "Workflows/test/workflow.api.json").write_text(
            json.dumps({"2": {"class_type": "LoraLoader", "inputs": {"lora_name": "old.safetensors"}}}),
            encoding="utf-8",
        )
        (self.root / "Workflows/test/runtime_requirements.json").write_text(
            json.dumps({"schema_version": "1.0", "lane_id": "test_lane", "required_models": []}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def resolved(self, payload: bytes = b"model-bytes") -> dict:
        metadata_path = self.root / "metadata.json"
        metadata_path.write_text(json.dumps(civitai_metadata(payload)), encoding="utf-8")
        return MODULE.resolve_request(self.root, request(), metadata_path)

    def test_resolve_civitai_exact_file_and_hash(self) -> None:
        payload = b"exact-model"
        manifest = self.resolved(payload)
        self.assertEqual(manifest["source_identity"]["file_id"], "9")
        self.assertEqual(manifest["source_metadata"]["expected_sha256"], MODULE.hashlib.sha256(payload).hexdigest())
        self.assertEqual(manifest["install"]["target_path"], "models/loras/test/test.safetensors")
        self.assertFalse(manifest["security"]["content_based_suppression"])

    def test_registry_and_queue_preserve_logical_path_for_offloaded_destination(self) -> None:
        manifest = self.resolved(b"offloaded-model")
        destination = self.root.parent / "physical-offload" / "test.safetensors"
        proof = {
            "sha256": MODULE.hashlib.sha256(b"offloaded-model").hexdigest(),
            "bytes": len(b"offloaded-model"),
        }

        record_id = MODULE.upsert_registry(self.root, manifest, destination, proof)
        MODULE.upsert_runtime_queue(self.root, manifest, destination, record_id)

        registry = MODULE.read_registry(self.root / MODULE.MODEL_REGISTRY)
        self.assertEqual(registry[0]["local_path"], "models/loras/test/test.safetensors")
        with (self.root / MODULE.RUNTIME_QUEUE).open("r", encoding="utf-8-sig", newline="") as handle:
            queue = list(csv.DictReader(handle))
        self.assertEqual(queue[0]["local_path"], "models/loras/test/test.safetensors")

    def test_logical_install_path_rejects_parent_traversal(self) -> None:
        manifest = self.resolved()
        manifest["install"]["target_subdir"] = "../outside"
        with self.assertRaisesRegex(MODULE.AcquisitionError, "logical models root"):
            MODULE.logical_install_path(manifest)

    def test_civitai_discovery_preserves_nsfw_metadata_without_filtering(self) -> None:
        payload = {
            "items": [
                {
                    "id": 123,
                    "name": "Technical Asset",
                    "type": "LORA",
                    "nsfw": True,
                    "tags": ["realism"],
                    "creator": {"username": "creator"},
                    "modelVersions": [
                        {
                            "id": 456,
                            "name": "v1",
                            "baseModel": "SDXL 1.0",
                            "trainedWords": ["trigger"],
                            "files": [
                                {
                                    "id": 9,
                                    "name": "asset.safetensors",
                                    "type": "Model",
                                    "primary": True,
                                    "metadata": {"format": "SafeTensor", "size": "full", "fp": "fp16"},
                                    "hashes": {"SHA256": "A" * 64},
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        with mock.patch.object(MODULE, "fetch_json", return_value=payload):
            result = MODULE.discover_civitai("realism", "LORA", 20, "sdxl")
        self.assertEqual(result["candidate_count"], 1)
        self.assertTrue(result["candidates"][0]["nsfw_metadata"])
        self.assertFalse(result["content_based_suppression"])
        self.assertFalse(result["adult_or_nsfw_metadata_used_as_filter"])
        self.assertEqual(result["candidates"][0]["files"][0]["file_id"], "9")

    def test_ambiguous_civitai_file_fails_closed(self) -> None:
        value = request()
        value["source"].pop("file_id")
        metadata = civitai_metadata(b"a")
        metadata["files"].append({"id": 10, "name": "other.safetensors", "primary": True, "hashes": {}})
        path = self.root / "metadata.json"
        path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.AcquisitionError, "Expected one exact Civitai file"):
            MODULE.resolve_request(self.root, value, path)

    def test_content_suppression_or_unknown_license_fails_closed(self) -> None:
        value = request()
        value["policy"]["content_based_suppression"] = True
        with self.assertRaisesRegex(MODULE.AcquisitionError, "content_based_suppression"):
            MODULE.require_request(value)
        value = request()
        value["policy"]["license_status"] = "unknown_blocked"
        with self.assertRaisesRegex(MODULE.AcquisitionError, "License/access"):
            MODULE.require_request(value)

    def test_huggingface_resolution_pins_revision(self) -> None:
        value = request("huggingface")
        value["source"]["sha256"] = "a" * 64
        manifest = MODULE.resolve_request(self.root, value)
        self.assertIn(value["source"]["revision"], manifest["source_metadata"]["download_url"])
        self.assertEqual(manifest["source_metadata"]["expected_sha256"], "a" * 64)

    def test_text_tokenizer_assets_are_allowed(self) -> None:
        self.assertIn(".txt", MODULE.SAFE_EXTENSIONS)

    def test_api_download_then_wire_register_and_queue_is_idempotent(self) -> None:
        payload = b"verified-model-payload"
        manifest = self.resolved(payload)
        with mock.patch.object(MODULE, "open_url", return_value=FakeResponse(payload)):
            candidate = MODULE.download_to_staging(self.root, manifest)
        result = MODULE.finalize(self.root, manifest, candidate, True, "http://127.0.0.1:9/object_info")
        self.assertEqual(result["classification"], "MODEL_ASSET_INSTALLED_REGISTERED_AND_QUEUED")
        self.assertFalse(result["production_ready"])
        target = self.root / "models/loras/test/test.safetensors"
        self.assertEqual(target.read_bytes(), payload)
        workflow = json.loads((self.root / "Workflows/test/workflow.api.json").read_text(encoding="utf-8"))
        self.assertEqual(workflow["2"]["inputs"]["lora_name"], "test.safetensors")
        requirements = json.loads((self.root / "Workflows/test/runtime_requirements.json").read_text(encoding="utf-8"))
        self.assertEqual(requirements["required_models"][0]["sha256"], MODULE.hashlib.sha256(payload).hexdigest())

        second = self.root / "second.safetensors"
        second.write_bytes(payload)
        second_result = MODULE.finalize(self.root, manifest, second, True, "http://127.0.0.1:9/object_info")
        self.assertTrue(second_result["duplicate_bytes_reused"])
        records = MODULE.read_registry(self.root / MODULE.MODEL_REGISTRY)
        self.assertEqual(len(records), 1)
        with (self.root / MODULE.RUNTIME_QUEUE).open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 1)

    def test_hash_mismatch_prevents_install(self) -> None:
        manifest = self.resolved(b"expected")
        candidate = self.root / "wrong.safetensors"
        candidate.write_bytes(b"wrong")
        with self.assertRaisesRegex(MODULE.AcquisitionError, "Expected SHA256"):
            MODULE.install_candidate(self.root, manifest, candidate)
        self.assertFalse((self.root / "models/loras/test/test.safetensors").exists())

    def test_complete_staging_part_is_reused_without_network(self) -> None:
        payload = b"complete-staging-payload"
        manifest = self.resolved(payload)
        partial = (
            self.root
            / "Models_Staging"
            / manifest["provider"]
            / "downloads"
            / manifest["manifest_id"]
            / f"{manifest['install']['local_filename']}.part"
        )
        partial.parent.mkdir(parents=True)
        partial.write_bytes(payload)
        with mock.patch.object(MODULE, "open_url") as network:
            candidate = MODULE.download_to_staging(self.root, manifest)
        network.assert_not_called()
        self.assertEqual(partial, candidate)
        self.assertEqual("resumed_complete_staging_file", manifest["acquisition_method"])

    def test_cross_volume_install_copies_verifies_and_renames(self) -> None:
        payload = b"cross-volume-payload"
        manifest = self.resolved(payload)
        candidate = self.root / "staging" / "test.safetensors"
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(payload)
        original_replace = MODULE.os.replace

        def replace_with_cross_volume(source, destination):
            if Path(source) == candidate:
                error = OSError(errno.EXDEV, "cross-device link")
                error.winerror = 17
                raise error
            return original_replace(source, destination)

        with mock.patch.object(MODULE.os, "replace", side_effect=replace_with_cross_volume):
            destination, proof, _ = MODULE.install_candidate(self.root, manifest, candidate)
        self.assertFalse(candidate.exists())
        self.assertEqual(payload, destination.read_bytes())
        self.assertEqual(MODULE.hashlib.sha256(payload).hexdigest(), proof["sha256"])

    def test_html_download_requires_browser(self) -> None:
        manifest = self.resolved(b"expected")
        with mock.patch.object(MODULE, "open_url", return_value=FakeResponse(b"<html>login</html>", "text/html")):
            with self.assertRaises(MODULE.AcquisitionError) as caught:
                MODULE.download_to_staging(self.root, manifest)
        self.assertEqual(caught.exception.classification, "BROWSER_DOWNLOAD_REQUIRED")

    def test_acquire_automatically_routes_api_auth_failure_to_background_browser(self) -> None:
        manifest = self.resolved(b"browser-fallback")
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        browser_result = {
            "classification": "BACKGROUND_BROWSER_DOWNLOAD_INSTALLED_REGISTERED_AND_QUEUED",
            "secret_values_reported": False,
        }
        argv = [
            "manage_model_asset_acquisition.py",
            "--project-root",
            str(self.root),
            "acquire",
            "--manifest",
            str(manifest_path),
            "--wire",
        ]
        with (
            mock.patch.object(MODULE.sys, "argv", argv),
            mock.patch.object(
                MODULE,
                "download_to_staging",
                side_effect=MODULE.AcquisitionError("BROWSER_DOWNLOAD_REQUIRED", "login required"),
            ),
            mock.patch.object(MODULE, "run_background_browser_fallback", return_value=browser_result) as fallback,
            redirect_stdout(io.StringIO()),
        ):
            return_code = MODULE.run()
        self.assertEqual(return_code, 0)
        fallback.assert_called_once_with(
            self.root.resolve(),
            manifest_path.resolve(),
            True,
            MODULE.DEFAULT_OBJECT_INFO,
        )

    def test_background_browser_subprocess_command_never_contains_secret(self) -> None:
        worker = self.root / "Plan/07_IMPLEMENTATION/scripts/run_background_browser_asset_download.py"
        worker.parent.mkdir(parents=True)
        worker.write_text("# worker\n", encoding="utf-8")
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text("{}\n", encoding="utf-8")
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"classification": "BACKGROUND_BROWSER_DOWNLOAD_HASH_VERIFIED"}),
            stderr="",
        )
        with (
            mock.patch.dict(os.environ, {"CIVITAI_API_KEY": "secret-api-value", "CIVITAI_SESSION_COOKIE": "secret-session-value"}),
            mock.patch.object(MODULE.subprocess, "run", return_value=completed) as launched,
        ):
            result = MODULE.run_background_browser_fallback(
                self.root,
                manifest_path,
                True,
                MODULE.DEFAULT_OBJECT_INFO,
            )
        command = launched.call_args.args[0]
        serialized_command = json.dumps(command)
        self.assertNotIn("secret-api-value", serialized_command)
        self.assertNotIn("secret-session-value", serialized_command)
        self.assertIn("--install", command)
        self.assertIn("--wire", command)
        self.assertEqual(result["classification"], "BACKGROUND_BROWSER_DOWNLOAD_HASH_VERIFIED")

    def test_civitai_401_retries_once_with_ephemeral_query_token(self) -> None:
        payload = b"query-token-download"
        manifest = self.resolved(payload)
        old = os.environ.get("CIVITAI_API_KEY")
        os.environ["CIVITAI_API_KEY"] = "secret-query-token"
        unauthorized = urllib.error.HTTPError(
            manifest["source_metadata"]["download_url"],
            401,
            "Unauthorized",
            Message(),
            None,
        )
        try:
            with mock.patch.object(MODULE, "open_url", side_effect=[unauthorized, FakeResponse(payload)]) as opened:
                candidate = MODULE.download_to_staging(self.root, manifest)
            self.assertEqual(candidate.read_bytes(), payload)
            self.assertTrue(manifest["ephemeral_token_query_retry_used"])
            second_request = opened.call_args_list[1].args[0]
            self.assertIn("token=secret-query-token", second_request.full_url)
            self.assertNotIn("secret-query-token", json.dumps(manifest))
        finally:
            if old is None:
                os.environ.pop("CIVITAI_API_KEY", None)
            else:
                os.environ["CIVITAI_API_KEY"] = old

    def test_existing_exact_hash_is_reused_before_network_and_preserved(self) -> None:
        payload = b"already-present-model"
        manifest = self.resolved(payload)
        existing = self.root / "ComfyUI/models/loras/test/test.safetensors"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(payload)
        with mock.patch.object(MODULE, "open_url") as network:
            candidate = MODULE.download_to_staging(self.root, manifest)
        network.assert_not_called()
        self.assertEqual(candidate, existing.resolve())
        result = MODULE.finalize(self.root, manifest, candidate, True, "http://127.0.0.1:9/object_info")
        self.assertEqual(result["acquisition_method"], "local_exact_hash_reuse")
        self.assertTrue(result["duplicate_bytes_reused"])
        self.assertTrue(existing.is_file())
        self.assertEqual((self.root / "models/loras/test/test.safetensors").read_bytes(), payload)

    def test_legacy_main_model_root_is_checked_before_network(self) -> None:
        payload = b"legacy-main-model"
        manifest = self.resolved(payload)
        legacy = self.root / "legacy-models"
        existing = legacy / "loras/test/test.safetensors"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(payload)
        with (
            mock.patch.object(MODULE, "LEGACY_MODEL_ROOTS", (legacy,)),
            mock.patch.object(MODULE, "open_url") as network,
        ):
            candidate = MODULE.download_to_staging(self.root, manifest)
        network.assert_not_called()
        self.assertEqual(existing.resolve(), candidate)

    def test_exact_huggingface_snapshot_is_checked_before_network(self) -> None:
        payload = b"cached-huggingface-file"
        value = request("huggingface")
        value["source"]["sha256"] = MODULE.hashlib.sha256(payload).hexdigest()
        value["source"]["bytes"] = len(payload)
        manifest = MODULE.resolve_request(self.root, value)
        cache = self.root / "hf-cache"
        repo_name = "models--" + value["source"]["repo_id"].replace("/", "--")
        existing = cache / repo_name / "snapshots" / value["source"]["revision"] / value["source"]["filename"]
        existing.parent.mkdir(parents=True)
        existing.write_bytes(payload)
        with (
            mock.patch.object(MODULE, "HF_CACHE_ROOT", cache),
            mock.patch.object(MODULE, "open_url") as network,
        ):
            candidate = MODULE.download_to_staging(self.root, manifest)
        network.assert_not_called()
        self.assertEqual(existing.resolve(), candidate)

    def test_concurrent_finalization_lock_fails_closed(self) -> None:
        lock = self.root / "runtime_artifacts/model_acquisition/model_registry_update.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("owned", encoding="utf-8")
        with self.assertRaises(MODULE.AcquisitionError) as caught:
            with MODULE.acquisition_update_lock(self.root):
                self.fail("lock should not be acquired")
        self.assertEqual(caught.exception.classification, "MODEL_ACQUISITION_UPDATE_LOCKED")
        self.assertTrue(lock.is_file())

    def test_browser_request_never_exports_cookie_or_token(self) -> None:
        manifest = self.resolved()
        value = MODULE.browser_request(self.root, manifest)
        serialized = json.dumps(value)
        self.assertFalse(value["browser_contract"]["export_browser_cookies"])
        self.assertFalse(value["content_based_suppression"])
        self.assertNotIn("Authorization", serialized)
        self.assertNotIn("super-secret-test-value", serialized)

    def test_placement_map_mismatch_fails_closed(self) -> None:
        value = request()
        value["asset"]["target_subdir"] = "checkpoints"
        metadata_path = self.root / "metadata.json"
        metadata_path.write_text(json.dumps(civitai_metadata(b"model")), encoding="utf-8")
        with self.assertRaises(MODULE.AcquisitionError) as caught:
            MODULE.resolve_request(self.root, value, metadata_path)
        self.assertEqual(caught.exception.classification, "MODEL_PLACEMENT_MAP_MISMATCH")

    def test_cross_host_redirect_strips_authorization(self) -> None:
        handler = MODULE.CredentialSafeRedirectHandler()
        original = MODULE.urllib.request.Request(
            "https://civitai.com/api/download/models/456",
            headers={"Authorization": "Bearer secret"},
        )
        redirected = handler.redirect_request(
            original,
            None,
            302,
            "Found",
            Message(),
            "https://cdn.example.test/model.safetensors",
        )
        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_preflight_reports_credential_presence_not_value(self) -> None:
        old = os.environ.get("CIVITAI_API_KEY")
        os.environ["CIVITAI_API_KEY"] = "super-secret-test-value"
        try:
            value = MODULE.preflight(self.root, False)
            serialized = json.dumps(value)
            self.assertTrue(value["checks"]["civitai_credential_present"])
            self.assertNotIn("super-secret-test-value", serialized)
            self.assertFalse(value["secret_values_reported"])
        finally:
            if old is None:
                os.environ.pop("CIVITAI_API_KEY", None)
            else:
                os.environ["CIVITAI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
