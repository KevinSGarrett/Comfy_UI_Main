from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RECONCILIATION = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_node_type_reconciliation.json"
SECURITY = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_dependency_security_reconciliation.json"


def test_all_raw_type_gaps_are_owned_and_runtime_stays_fail_closed() -> None:
    data = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    inventory_path = ROOT / data["inventory"]["path"]
    assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == data["inventory"]["sha256"]
    rows = list(csv.DictReader(inventory_path.open(encoding="utf-8-sig", newline="")))
    assert len(rows) == data["inventory"]["rows"] == 356
    assert sum(row["cnr_id"] == "comfy-core" for row in rows) == data["inventory"]["comfy_core_rows"] == 340
    gap_types = {node_type for workflow in data["raw_workflows"] for node_type in workflow["inventory_missing_type_nodes"]}
    owned_types = {node_type for types in data["static_ownership"].values() for node_type in types}
    assert gap_types == owned_types
    assert all(workflow["unique_types"] == 40 for workflow in data["raw_workflows"])
    pins = dict(data["quarantine_pins"])
    assert len(pins) == 17
    assert len(data["referenced_quarantine_repositories"]) + data["unused_quarantine_repository_count"] == len(pins)
    assert data["core_compatibility"]["inventory_version"] == "0.26.0"
    assert data["core_compatibility"]["current_pod_version"] == "0.28.0"
    assert data["authority"]["raw_type_static_ownership"] is True
    assert data["dependency_security_reconciliation"] == SECURITY.relative_to(ROOT).as_posix()
    assert data["authority"]["dependency_security_static_reconciliation"] is True
    for field in ("object_info_compatibility", "dependency_install", "custom_node_import", "workflow_execution", "activation", "promotion"):
        assert data["authority"][field] is False


def test_dependency_and_dwpose_security_gates_fail_closed() -> None:
    data = json.loads(SECURITY.read_text(encoding="utf-8"))
    repos = {item["name"]: item for item in data["repositories"]}
    assert len(repos) == 5
    assert all(item["clean"] for item in repos.values())
    assert repos["ComfyUI-Impact-Pack"]["manifest_dependency_count"] == 10
    assert repos["ComfyUI-Impact-Subpack"]["manifest_dependency_count"] == 5
    assert repos["comfyui-controlnet-aux"]["manifest_dependency_count"] == 25
    dw = data["selected_dwpreprocessor"]
    assert dw["bbox_model"]["sha256"] == "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411"
    assert dw["pose_model"]["sha256"] == "d86a0b2b59fddc0901a7076e9f59c9f8602602133ed72511c693fd11eea23d91"
    assert "non-commercial use only" in dw["implementation_notice"]
    assert dw["commercial_activation"].startswith("BLOCKED_")
    assert data["authority"]["used_repository_pins_clean"] is True
    assert data["authority"]["dependency_manifests_inventoried"] is True
    for field in ("dependency_lock_reproducible", "installer_side_effects_disabled", "hash_bound_unsafe_loader_policy", "commercial_dwpreprocessor_authority", "dependency_install", "custom_node_import", "object_info_compatibility", "workflow_execution", "activation", "promotion"):
        assert data["authority"][field] is False
