import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/prepare_wave64_aqa_hf_snapshot_manifest.py"
SPEC = importlib.util.spec_from_file_location("hf_admission_builder", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_metadata() -> dict:
    payload = b"config"
    git_digest = hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()
    return {
        "id": "publisher/model-fp8",
        "sha": "a" * 40,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {
                "rfilename": "model.safetensors",
                "size": 10,
                "lfs": {"sha256": "b" * 64},
            },
            {"rfilename": "config.json", "size": len(payload), "blobId": git_digest},
        ],
    }


def test_build_manifest_emits_established_storage_admission_contract() -> None:
    manifest = MODULE.build_manifest(
        fixture_metadata(),
        "a" * 40,
        "W64-AQA-PKG-TEST",
        "/workspace/w64_aqa/models/test/revision",
        1024,
    )
    assert manifest["schema_version"] == "wave64.aqa.model_install_admission.v1"
    assert manifest["storage"]["weight_bytes"] == 10
    assert manifest["files"][0]["path"] == "config.json"
    assert manifest["files"][1]["identity_kind"] == "sha256"
    assert manifest["authority"]["forbidden"][:4] == [
        "model_load",
        "inference",
        "gpu_probe",
        "lease_poll",
    ]


def test_build_manifest_fails_closed_on_revision_drift() -> None:
    with pytest.raises(ValueError, match="upstream revision changed"):
        MODULE.build_manifest(fixture_metadata(), "c" * 40, "package", "/workspace/model", 1)
