from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_ipadapter_plus_sdxl_promoted_storage_package.json"


def test_exact_adapter_hash_and_encoder_pair_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    encoder = json.loads((ROOT / package["paired_encoder_package"]["path"]).read_text(encoding="utf-8"))
    file_entry = package["files"][0]
    assert source["repository"] == package["repository"] == encoder["repository"] == "h94/IP-Adapter"
    assert source["revision"] == package["revision"] == encoder["revision"] == "018e402774aeeddd60609b4ecdb7e298259dc729"
    assert source["license_metadata"] == package["license_metadata"] == encoder["license_metadata"] == "apache-2.0"
    assert source["file"]["path"] == file_entry["provider_path"]
    assert source["file"]["bytes"] == package["total_bytes"] == file_entry["bytes"] == 847517512
    assert source["file"]["lfs_sha256"] == file_entry["sha256"] == "3f5062b8400c94b7159665b21ba5c62acdcd7682262743d7f2aefedef00e6581"
    assert package["authority"]["paired_encoder_storage_identity"] is True
    for field in ("license_acceptance", "dependency_code", "model_load", "reference_conditioning_quality", "operational_activation", "workflow_promotion", "product_promotion"):
        assert package["authority"][field] is False
