from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_clip_vit_h14_ipadapter_promoted_storage_package.json"


def test_exact_provider_hash_and_independent_dependency_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    file_entry = package["files"][0]
    assert source["repository"] == package["repository"] == "h94/IP-Adapter"
    assert source["revision"] == package["revision"] == "018e402774aeeddd60609b4ecdb7e298259dc729"
    assert source["license_metadata"] == package["license_metadata"] == "apache-2.0"
    assert source["file"]["path"] == file_entry["provider_path"]
    assert source["file"]["bytes"] == package["total_bytes"] == file_entry["bytes"] == 2528373448
    assert source["file"]["lfs_sha256"] == file_entry["sha256"] == "6ca9667da1ca9e0b0f75e46bb030f7e011f44f86cbfb8d5a36590fcd7507b030"
    assert package["authority"]["storage_identity"] is True
    for field in ("license_acceptance", "paired_ipadapter", "dependency_bundle", "model_load", "reference_conditioning_quality", "operational_activation", "workflow_promotion", "product_promotion"):
        assert package["authority"][field] is False
