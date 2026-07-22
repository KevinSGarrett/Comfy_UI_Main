from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_animatediff_sdxl_v10_beta_promoted_storage_package.json"


def test_exact_s3_mirror_record_and_visual_block_are_retained() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    registry_path = ROOT / package["source_registry"]["path"]
    assert hashlib.sha256(registry_path.read_bytes()).hexdigest() == package["source_registry"]["sha256_at_acceptance"]
    records = [json.loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    record = next(item for item in records if item.get("record_id") == package["source_registry"]["record_id"])
    file_entry = package["files"][0]
    assert record["source"] == package["provider"] == "aws_s3_existing_mirror"
    assert record["source_url"] == package["source_url"]
    assert record["source_model_version_id"] == package["source_model_version_id"]
    assert record["file_size_bytes"] == package["total_bytes"] == file_entry["bytes"] == 950143538
    assert record["sha256"] == file_entry["sha256"] == "fa4950a062e892fca50d4c441fcd6130d1ad68a621a0404d155be17580072978"
    assert record["qa_status"] == "technical_runtime_pass_visual_temporal_fail"
    assert package["retained_runtime_evidence"]["disposition"] == "TECHNICAL_RUNTIME_PASS_VISUAL_TEMPORAL_FAIL"
    assert "frame_7_severe_color_corruption" in package["retained_runtime_evidence"]["blocking_findings"]
    for evidence in ("technical", "visual"):
        assert (ROOT / package["retained_runtime_evidence"][evidence]).is_file()
    assert package["authority"]["storage_identity"] is True
    assert package["authority"]["versioned_s3_mirror_binding"] is True
    for field in (
        "original_publisher_identity",
        "original_publisher_hash_binding",
        "license_metadata_binding",
        "license_acceptance",
        "dependency_bundle",
        "model_load",
        "generation_quality",
        "visual_temporal_promotion",
        "operational_activation",
        "product_promotion",
    ):
        assert package["authority"][field] is False
