from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RECONCILIATION = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_model_selection_reconciliation.json"
RECOVERY = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_asset_recovery_package.json"


def test_missing_required_assets_and_unresolved_presets_block_activation() -> None:
    data = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    assert len(data["missing_nonzero_unique_assets"]) == 9
    assert len(data["missing_zero_weight_unique_assets"]) == 14
    assert len(data["present_unique_assets"]) == 10
    assert data["quarantine_recovery_package"] == RECOVERY.relative_to(ROOT).as_posix()
    assert data["quarantine_recovered_nonzero_unique_assets"] == data["missing_nonzero_unique_assets"]
    assert "sams/sam_vit_b_01ec64.pth" in data["missing_nonzero_unique_assets"]
    assert "ultralytics/bbox/hand_yolov8n.pt" in data["missing_nonzero_unique_assets"]
    assert data["unresolved_presets"][0]["preset"] == "PLUS FACE (portraits)"
    promoted_loras = json.loads((ROOT / "Plan/10_REGISTRIES/wave64_wave42_lora_promoted_storage_package.json").read_text(encoding="utf-8"))
    wet = next(item for item in promoted_loras["files"] if item["asset_id"] == "wet_makeup_runny_mascara_sdxl")
    assert wet["path"].removeprefix("/workspace/ComfyUI/models/") in data["present_unique_assets"]
    assert data["authority"]["loader_widget_extraction"] is True
    assert data["authority"]["complete_required_quarantine_asset_set"] is True
    for field in ("complete_required_asset_set", "exact_preset_binding", "all_present_asset_identity", "object_info_compatibility", "workflow_execution", "activation", "promotion"):
        assert data["authority"][field] is False


def test_recovered_required_assets_are_hash_verified_but_inactive() -> None:
    data = json.loads(RECOVERY.read_text(encoding="utf-8"))
    files = data["files"]
    assert data["status"] == "QUARANTINE_STORAGE_HASH_VERIFIED_NOT_ACTIVATED"
    assert data["file_count"] == len(files) == 9
    assert data["total_bytes"] == sum(item["bytes"] for item in files) == 4_224_495_032
    assert len({item["relative_path"] for item in files}) == 9
    assert all(len(item["sha256"]) == 64 for item in files)
    assert data["destination"]["loader_visible"] is False
    assert data["transfer"]["runpod_authorized_key_removed"] is True
    assert data["transfer"]["ec2_private_key_removed"] is True
    assert data["authority"]["complete_required_quarantine_asset_set"] is True
    assert data["authority"]["source_to_destination_hash_equality"] is True
    for field in ("live_runtime_presence", "complete_provider_and_permission_identity", "dependency_compatibility", "object_info_compatibility", "model_load", "workflow_execution", "quality", "activation", "promotion"):
        assert data["authority"][field] is False
