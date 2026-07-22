from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_ipadapter_quarantine_static_admission.json"


def test_pin_assets_workflow_counts_and_fail_closed_authority() -> None:
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    node_rows = list(csv.DictReader((ROOT / "Plan/10_REGISTRIES/main_flow_node_inventory.csv").open(encoding="utf-8-sig", newline="")))
    ip_rows = [row for row in node_rows if row["node_type"] in {"IPAdapter", "IPAdapterUnifiedLoader"}]
    assert {row["cnr_version"] for row in ip_rows} == {admission["custom_node"]["commit"]}
    assert admission["custom_node"]["clean_worktree"] is True
    assert admission["custom_node"]["dependency_manifest_present"] is False
    packages = [json.loads((ROOT / path).read_text(encoding="utf-8")) for path in admission["asset_packages"]]
    assert len(packages) == 2
    assert {package["revision"] for package in packages} == {"018e402774aeeddd60609b4ecdb7e298259dc729"}
    for workflow in admission["workflows"]:
        assert workflow["ipadapter_nodes"] == workflow["unified_loaders"] + workflow["appliers"] == 50
        assert workflow["zero_weight_appliers"] == workflow["strict_gate_appliers"] == 45
        assert workflow["nonzero_weight_appliers"] == 1
    assert admission["authority"]["quarantine_integrity"] is True
    for field in ("dependency_install", "custom_node_import", "object_info_binding", "model_load", "visual_quality", "activation", "workflow_promotion", "product_promotion"):
        assert admission["authority"][field] is False
