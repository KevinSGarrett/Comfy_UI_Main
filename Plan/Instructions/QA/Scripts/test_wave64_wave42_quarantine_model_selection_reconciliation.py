from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RECONCILIATION = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_model_selection_reconciliation.json"


def test_missing_required_assets_and_unresolved_presets_block_activation() -> None:
    data = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    assert len(data["missing_nonzero_unique_assets"]) == 9
    assert len(data["missing_zero_weight_unique_assets"]) == 14
    assert len(data["present_unique_assets"]) == 10
    assert "sams/sam_vit_b_01ec64.pth" in data["missing_nonzero_unique_assets"]
    assert "ultralytics/bbox/hand_yolov8n.pt" in data["missing_nonzero_unique_assets"]
    assert data["unresolved_presets"][0]["preset"] == "PLUS FACE (portraits)"
    promoted_loras = json.loads((ROOT / "Plan/10_REGISTRIES/wave64_wave42_lora_promoted_storage_package.json").read_text(encoding="utf-8"))
    wet = next(item for item in promoted_loras["files"] if item["asset_id"] == "wet_makeup_runny_mascara_sdxl")
    assert wet["path"].removeprefix("/workspace/ComfyUI/models/") in data["present_unique_assets"]
    assert data["authority"]["loader_widget_extraction"] is True
    for field in ("complete_required_asset_set", "exact_preset_binding", "all_present_asset_identity", "object_info_compatibility", "workflow_execution", "activation", "promotion"):
        assert data["authority"][field] is False
