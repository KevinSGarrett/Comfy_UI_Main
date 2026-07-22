from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RECONCILIATION = ROOT / "Plan/10_REGISTRIES/wave64_wave42_quarantine_node_type_reconciliation.json"


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
    for field in ("object_info_compatibility", "dependency_install", "custom_node_import", "workflow_execution", "activation", "promotion"):
        assert data["authority"][field] is False
