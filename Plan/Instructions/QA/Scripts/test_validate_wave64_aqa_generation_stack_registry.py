from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_generation_stack_registry.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_aqa_generation_stacks", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry(module):
    return json.loads((ROOT / module.REGISTRY_PATH).read_text(encoding="utf-8"))


def test_registry_binds_four_inactive_candidates_and_selects_smallest_exact_asset() -> None:
    module = load_module()
    selected = module.validate_registry(ROOT, registry(module))
    assert selected["stack_id"] == "W64-AQA-GEN-FLUX2-KLEIN-4B-FP8"
    assert selected["asset"]["bytes"] == 4070624520
    assert selected["execution"]["executable"] is False
    assert selected["execution"]["workflow_bound"] is True
    assert selected["current_pod_reconciliation"]["path"].endswith("current_pod_reconciliation.json")
    assert "EXACT_KLEIN_VAE_CURRENT_POD_IDENTITY_MISMATCH" in selected["blockers"]


def test_selected_stack_drift_is_rejected() -> None:
    module = load_module()
    value = registry(module)
    value["selected_stack_id"] = value["stacks"][1]["stack_id"]
    with pytest.raises(module.GenerationStackError, match="selected inactive stack"):
        module.validate_registry(ROOT, value)


def test_package_identity_drift_is_rejected() -> None:
    module = load_module()
    value = registry(module)
    value["stacks"][0]["asset"]["sha256"] = "0" * 64
    with pytest.raises(module.GenerationStackError, match="package file drift"):
        module.validate_registry(ROOT, value)


def test_schema_rejects_execution_or_broad_authority() -> None:
    module = load_module()
    value = copy.deepcopy(registry(module))
    value["stacks"][0]["execution"]["executable"] = True
    with pytest.raises(Exception):
        module.validate_registry(ROOT, value)
    value = copy.deepcopy(registry(module))
    value["authority"]["quality"] = True
    with pytest.raises(Exception):
        module.validate_registry(ROOT, value)


def test_current_pod_reconciliation_hash_drift_is_rejected() -> None:
    module = load_module()
    value = copy.deepcopy(registry(module))
    value["stacks"][0]["current_pod_reconciliation"]["sha256"] = "0" * 64
    with pytest.raises(module.GenerationStackError, match="reconciliation hash drift"):
        module.validate_registry(ROOT, value)
