from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_animatediff_quarantine_static_admission.json"


def test_clean_pin_absent_workflow_binding_and_visual_block() -> None:
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    model = json.loads((ROOT / admission["motion_model_package"]).read_text(encoding="utf-8"))
    assert admission["custom_node"]["commit"] == "d8d163cd90b1111f6227495e3467633676fbb346"
    assert admission["custom_node"]["clean_worktree"] is True
    assert admission["custom_node"]["license_metadata"] == "Apache-2.0"
    assert all(item["animatediff_or_ade_nodes"] == 0 for item in admission["workflow_observations"])
    assert model["retained_runtime_evidence"]["disposition"] == "TECHNICAL_RUNTIME_PASS_VISUAL_TEMPORAL_FAIL"
    assert "frame_7_severe_color_corruption" in model["retained_runtime_evidence"]["blocking_findings"]
    assert admission["authority"]["custom_node_pin_identity"] is True
    for field in ("workflow_binding", "dependency_install", "custom_node_import", "object_info_binding", "model_load", "visual_temporal_quality", "activation", "workflow_promotion", "product_promotion"):
        assert admission["authority"][field] is False
