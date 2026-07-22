from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_runpod_qwen3_omni_30b_a3b_thinking_install_admission.json"
RECEIPT = ROOT / (
    "Plan/Tracker/Evidence/"
    "W64_AQA_QWEN3_OMNI_30B_A3B_STORAGE_INSTALL_20260722T021221Z/"
    "remote_install_receipt.json"
)


def test_receipt_exactly_binds_manifest_files_and_runtime_limits() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "wave64.aqa.model_install_receipt.v1"
    assert receipt["package_id"] == manifest["package_id"]
    assert receipt["source_revision"] == manifest["source"]["revision"]
    assert receipt["target_root"] == manifest["storage"]["target_root"]
    assert receipt["manifest_sha256"] == "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480"
    for declaration, observed in zip(manifest["files"], receipt["files"], strict=True):
        if declaration["bytes"] is not None:
            assert observed["bytes"] == declaration["bytes"]
    expected = [
        {
            "path": item["path"],
            "identity_kind": item["identity_kind"],
            "identity": item["identity"],
            "bytes": observed["bytes"],
        }
        for item, observed in zip(manifest["files"], receipt["files"], strict=True)
    ]
    assert receipt["files"] == expected
    assert sum(
        item["bytes"]
        for item in receipt["files"]
        if item["identity_kind"] == "sha256"
    ) == manifest["storage"]["weight_bytes"]
    assert receipt["runtime_claims"] == {
        "model_loaded": False,
        "inference_performed": False,
        "gpu_or_lease_polled": False,
        "role_activated": False,
        "product_authority": False,
    }
