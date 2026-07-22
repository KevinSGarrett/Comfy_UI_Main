from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_wave42_object_info_admission_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("wave42_object_info_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(module):
    return json.loads((ROOT / module.CONTRACT_PATH).read_text(encoding="utf-8"))


def resign(module, value):
    value["contract_id"] = module.content_id(value)
    return value


def passing_snapshot(value):
    snapshot = {node_type: {"input": {"required": {}}} for node_type in value["required_object_info_types"]}
    for node_type, inputs in value["signature_requirements"].items():
        snapshot[node_type]["input"]["required"] = {name: ["TEST"] for name in inputs}
    return snapshot


def test_static_contract_binds_quarantine_and_retains_runtime_holds() -> None:
    module = load_module()
    value = contract(module)
    module.validate_contract(ROOT, value)
    assert len(value["quarantine"]["custom_node_pins"]) == 17
    assert len(value["required_object_info_types"]) == 39
    assert value["frontend_only_exemptions"][0]["type"] == "Note"
    assert value["authority"]["static_contract"] is True
    assert value["authority"]["object_info"] is False


def test_candidate_snapshot_passes_presence_and_signature_without_runtime_authority() -> None:
    module = load_module()
    value = contract(module)
    result = module.evaluate_object_info(value, passing_snapshot(value))
    assert result["required_types"] == 39
    assert result["object_info"] is True
    assert result["model_load"] is False
    assert result["workflow_execution"] is False


def test_missing_type_fails_closed() -> None:
    module = load_module()
    value = contract(module)
    snapshot = passing_snapshot(value)
    snapshot.pop("SAMLoader")
    with pytest.raises(module.AdmissionContractError, match="SAMLoader"):
        module.evaluate_object_info(value, snapshot)


def test_legacy_noncommercial_dwpose_fails_closed() -> None:
    module = load_module()
    value = contract(module)
    snapshot = passing_snapshot(value)
    snapshot["DWPreprocessor"] = {"input": {"required": {}}}
    with pytest.raises(module.AdmissionContractError, match="DWPreprocessor"):
        module.evaluate_object_info(value, snapshot)


def test_custom_signature_drift_fails_closed() -> None:
    module = load_module()
    value = contract(module)
    snapshot = passing_snapshot(value)
    del snapshot["Wave64CommercialDWPosePreprocessor"]["input"]["required"]["pose_estimator"]
    with pytest.raises(module.AdmissionContractError, match="pose_estimator"):
        module.evaluate_object_info(value, snapshot)


def test_runtime_authority_cannot_be_self_granted() -> None:
    module = load_module()
    value = copy.deepcopy(contract(module))
    value["authority"]["object_info"] = True
    resign(module, value)
    with pytest.raises(Exception):
        module.validate_contract(ROOT, value)
