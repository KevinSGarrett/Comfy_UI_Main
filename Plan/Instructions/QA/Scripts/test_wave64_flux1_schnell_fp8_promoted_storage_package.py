from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_flux1_schnell_fp8_promoted_storage_package.json"


def test_exact_provider_revision_lfs_hash_and_nonpromotion_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    file_entry = package["files"][0]
    assert source["repository"] == package["repository"] == "Comfy-Org/flux1-schnell"
    assert source["revision"] == package["revision"] == "7d679837b018bfeb28eca55734b335efcd0e7100"
    assert source["license_metadata"] == package["license_metadata"] == "apache-2.0"
    assert source["file"]["path"] == file_entry["path"]
    assert source["file"]["bytes"] == package["total_bytes"] == file_entry["bytes"] == 17236328572
    assert source["file"]["lfs_sha256"] == file_entry["sha256"] == "ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72"
    lanes = json.loads((ROOT / package["workflow_reference"]["path"]).read_text(encoding="utf-8"))
    serialized = json.dumps(lanes)
    assert package["workflow_reference"]["lane_id"] in serialized
    assert package["workflow_reference"]["promotion_status"] in serialized
    assert package["authority"]["storage_identity"] is True
    for field in ("license_acceptance", "execution_bundle", "model_load", "generation_quality", "operational_activation", "workflow_promotion", "product_promotion"):
        assert package["authority"][field] is False
