from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_sdxl_base_1_0_promoted_storage_package.json"


def test_exact_provider_revision_lfs_hash_and_authority_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    file_entry = package["files"][0]
    assert source["provider"] == package["provider"] == "huggingface"
    assert source["repository"] == package["repository"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert source["revision"] == package["revision"] == "462165984030d82259a11f4367a4eed129e94a7b"
    assert source["license_metadata"] == package["license_metadata"] == "openrail++"
    assert source["file"]["path"] == file_entry["path"]
    assert source["file"]["bytes"] == package["total_bytes"] == file_entry["bytes"] == 6938078334
    assert source["file"]["lfs_sha256"] == file_entry["sha256"] == "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b"
    assert (ROOT / package["historical_runtime_evidence"]["path"]).is_file()
    assert package["authority"]["storage_identity"] is True
    for field in ("license_acceptance", "dependency_bundle", "current_pod_model_load", "current_pod_generation_quality", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
