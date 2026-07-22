from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_wave42_lora_promoted_storage_package.json"


def test_exact_lora_hashes_provider_ids_and_permission_boundaries() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence_path.read_text(encoding="utf-8"))
    by_id = {item["asset_id"]: item for item in source["assets"]}
    assert package["file_count"] == len(package["files"]) == len(by_id) == 3
    assert package["total_bytes"] == sum(item["bytes"] for item in package["files"]) == 685369060
    for item in package["files"]:
        provider = by_id[item["asset_id"]]
        assert provider["sha256"] == item["sha256"]
        assert provider["bytes"] == item["bytes"]
        assert provider["model_id"] == item["model_id"]
        assert provider["version_id"] == item["version_id"]
    assert by_id["big_areolas_sdxl"]["allow_no_credit"] is False
    assert by_id["big_areolas_sdxl"]["allow_derivatives"] is False
    assert by_id["latina_xl"]["allow_commercial_use"] == []
    assert package["authority"]["storage_identity"] is True
    for field in ("license_acceptance", "content_consent", "workflow_binding", "model_load", "visual_quality", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
