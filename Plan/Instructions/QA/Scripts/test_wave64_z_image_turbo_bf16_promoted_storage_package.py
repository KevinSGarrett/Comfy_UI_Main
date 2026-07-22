from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_z_image_turbo_bf16_promoted_storage_package.json"


def test_exact_mirror_hash_and_license_non_inference_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    file_entry = package["files"][0]
    assert source["repository"] == package["repository"] == "Comfy-Org/z_image_turbo"
    assert source["revision"] == package["revision"] == "d24c4cf2a0cd98a42f23467e27e3d76ee9438b8e"
    assert source["license_metadata"] is package["license_metadata"] is None
    assert source["file"]["path"] == file_entry["provider_path"]
    assert source["file"]["bytes"] == package["total_bytes"] == file_entry["bytes"] == 12309866400
    assert source["file"]["lfs_sha256"] == file_entry["sha256"] == "2407613050b809ffdff18a4ac99af83ea6b95443ecebdf80e064a79c825574a6"
    lanes = json.dumps(json.loads((ROOT / package["workflow_reference"]["path"]).read_text(encoding="utf-8")))
    assert package["workflow_reference"]["lane_id"] in lanes
    assert package["workflow_reference"]["promotion_status"] in lanes
    assert package["authority"]["storage_identity"] is True
    for field in ("original_publisher_identity", "license_metadata_binding", "license_acceptance", "execution_bundle", "model_load", "generation_quality", "operational_activation", "workflow_promotion", "product_promotion"):
        assert package["authority"][field] is False
