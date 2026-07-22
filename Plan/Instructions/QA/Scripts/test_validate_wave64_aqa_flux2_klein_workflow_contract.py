from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_workflow_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_flux2_workflow_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.CONTRACT_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["contract_id"] = module.content_id(candidate)
    return candidate


def test_static_contract_binds_official_and_selected_workflows() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_contract(ROOT, candidate)
    assert candidate["official_template"]["sha256"] == "237b436e577cdd2a97527766637e87af162b4c14fb293c9c269b470b7a2d0166"
    assert candidate["compatibility_decision"]["official_template_directly_executable_for_selected_stack"] is False
    assert candidate["authority"]["static_workflow_contract"] is True
    assert candidate["authority"]["runtime_smoke"] is False


def test_unselected_base_model_cannot_enter_api_candidate_contract() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["compatibility_decision"]["base_branch_removed"] = False
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_contract(ROOT, candidate, verify_local_environment=False)


def test_required_node_source_coverage_cannot_shrink() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["comfyui_checkout"]["source_bindings"][0]["node_types"].remove("SaveImage")
    candidate = resign(module, candidate)
    with pytest.raises(module.WorkflowContractError, match="coverage drift"):
        module.validate_contract(ROOT, candidate, verify_local_environment=False)


def test_runtime_authority_cannot_be_self_granted() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["authority"]["runtime_smoke"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_contract(ROOT, candidate, verify_local_environment=False)
