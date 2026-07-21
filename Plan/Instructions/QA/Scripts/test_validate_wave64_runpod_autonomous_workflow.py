from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("w64_aqa_workflow_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def object_info() -> dict:
    return {
        "CheckpointLoaderSimple": {
            "input": {"required": {"ckpt_name": [["base.safetensors", "other.safetensors"]]}},
            "output": ["MODEL"], "output_node": False,
        },
        "Sampler": {
            "input": {"required": {
                "model": ["MODEL"], "steps": ["INT", {"min": 1, "max": 1000}],
                "cfg": ["FLOAT", {"min": 0, "max": 100}], "text": ["STRING"],
            }},
            "output": ["IMAGE"], "output_node": False,
        },
        "SaveImage": {
            "input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING"]}},
            "output": [], "output_node": True,
        },
    }


def workflow() -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "base.safetensors"}},
        "2": {"class_type": "Sampler", "inputs": {"model": ["1", 0], "steps": 20, "cfg": 7.0, "text": "portrait"}},
        "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "jobs/output"}},
    }


def inventory() -> dict:
    return {"schema_version": "wave64.aqa.model_inventory.v1", "eligible_model_names": ["base.safetensors"]}


def contract(module, info: dict | None = None) -> dict:
    info = info or object_info()
    return {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "e" * 64,
        "modality": "workflow", "preflight_disposition": "READY_FOR_LEASE",
        "workflow_spec": {
            "object_info_sha256": module.content_hash(info),
            "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
            "sandbox_required": True, "regression_suite_id": "workflow-regression-v1",
        },
    }


def test_valid_api_workflow_is_deterministic_and_passes_without_execution() -> None:
    module = load_validator()
    first = module.validate_workflow(workflow(), object_info(), contract(module), inventory())
    second = module.validate_workflow(workflow(), object_info(), contract(module), inventory())
    assert first == second
    assert first["disposition"] == "PASS_STATIC_VALIDATION"
    assert first["input_binding_disposition"] == "UNBOUND_STATIC_TEST_ONLY"
    assert first["input_executor_receipt_ids"] == {}
    assert first["graph_summary"] == {"node_count": 3, "edge_count": 2, "output_node_count": 1, "acyclic": True}
    assert first["sandbox_execution_performed"] is False


def test_unknown_node_missing_input_bad_edge_type_and_cycle_are_rejected() -> None:
    module = load_validator()
    value = workflow()
    value["1"]["class_type"] = "UnknownLoader"
    value["2"]["inputs"].pop("steps")
    value["2"]["inputs"]["model"] = ["3", 0]
    value["3"]["inputs"]["images"] = ["2", 0]
    result = module.validate_workflow(value, object_info(), contract(module), inventory())
    codes = {item["code"] for item in result["findings"]}
    assert {"NODE_CLASS_UNAVAILABLE", "REQUIRED_INPUT_MISSING", "EDGE_OUTPUT_INDEX_INVALID", "WORKFLOW_CYCLE_DETECTED"}.issubset(codes)
    assert result["disposition"] == "FAIL_STATIC_VALIDATION"


def test_model_range_path_and_option_controls_fail_closed() -> None:
    module = load_validator()
    value = workflow()
    value["1"]["inputs"]["ckpt_name"] = "unapproved.safetensors"
    value["2"]["inputs"]["steps"] = 500
    value["3"]["inputs"]["filename_prefix"] = "../../escape"
    result = module.validate_workflow(value, object_info(), contract(module), inventory())
    codes = {item["code"] for item in result["findings"]}
    assert {"MODEL_NOT_ELIGIBLE", "LITERAL_OUTSIDE_CONTROLLER_RANGE", "PATH_LITERAL_UNSAFE"}.issubset(codes)


def patch(
    module, value: dict, *, operation: str = "replace_bounded_numeric",
    node_id: str = "2", input_name: str = "steps", old=20, new=30,
) -> dict:
    return {
        "schema_version": "wave64.aqa.workflow_patch.v1",
        "patch_id": "W64-AQA-PATCH-test-001",
        "base_workflow_sha256": module.content_hash(value),
        "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
        "operations": [{
            "operation": operation, "node_id": node_id, "input_name": input_name,
            "expected_old_value": old, "new_value": new,
        }],
    }


def test_typed_copy_on_write_patch_is_accepted_for_future_sandbox() -> None:
    module = load_validator()
    value = workflow()
    proposal = patch(module, value)
    result = module.validate_workflow(value, object_info(), contract(module), inventory(), proposal)
    assert result["patch_disposition"] == "TYPED_PATCH_ACCEPTED_FOR_SANDBOX"
    assert result["disposition"] == "PASS_STATIC_VALIDATION"
    assert result["candidate_workflow_sha256"] != result["base_workflow_sha256"]
    assert value["2"]["inputs"]["steps"] == 20
    assert result["sandbox_execution_performed"] is False


def test_model_patch_requires_both_declared_point_and_eligible_inventory() -> None:
    module = load_validator()
    value = workflow()
    proposal = patch(
        module, value, operation="replace_model", node_id="1", input_name="ckpt_name",
        old="base.safetensors", new="other.safetensors",
    )
    eligible = {"schema_version": "wave64.aqa.model_inventory.v1", "eligible_model_names": ["base.safetensors", "other.safetensors"]}
    result = module.validate_workflow(value, object_info(), contract(module), eligible, proposal)
    assert result["patch_disposition"] == "TYPED_PATCH_ACCEPTED_FOR_SANDBOX"
    assert result["disposition"] == "PASS_STATIC_VALIDATION"


@pytest.mark.parametrize("operation,input_name,old,new", [
    ("replace_bounded_numeric", "steps", 20, 500),
    ("replace_model", "text", "portrait", "unapproved.safetensors"),
    ("replace_prompt_fragment", "steps", 20, "inject"),
    ("replace_declared_literal", "text", "portrait", "bypass"),
])
def test_patch_operations_outside_exact_allowlist_are_rejected(operation: str, input_name: str, old, new) -> None:
    module = load_validator()
    value = workflow()
    proposal = patch(module, value, operation=operation, input_name=input_name, old=old, new=new)
    result = module.validate_workflow(value, object_info(), contract(module), inventory(), proposal)
    assert result["patch_disposition"] == "TYPED_PATCH_REJECTED"
    assert "PATCH_OPERATION_OUTSIDE_ALLOWLIST" in {item["code"] for item in result["findings"]}
    assert result["candidate_workflow_sha256"] == result["base_workflow_sha256"]


def test_patch_base_hash_expected_value_and_contract_bindings_are_enforced() -> None:
    module = load_validator()
    value = workflow()
    wrong_hash = patch(module, value)
    wrong_hash["base_workflow_sha256"] = "f" * 64
    result = module.validate_workflow(value, object_info(), contract(module), inventory(), wrong_hash)
    assert "PATCH_BASE_HASH_MISMATCH" in {item["code"] for item in result["findings"]}
    wrong_old = patch(module, value, old=99)
    result = module.validate_workflow(value, object_info(), contract(module), inventory(), wrong_old)
    assert "PATCH_EXPECTED_VALUE_MISMATCH" in {item["code"] for item in result["findings"]}
    held = contract(module)
    held["preflight_disposition"] = "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    with pytest.raises(module.WorkflowValidationError, match="not ready"):
        module.validate_workflow(value, object_info(), held, inventory())
    stale = contract(module)
    stale["workflow_spec"]["object_info_sha256"] = "0" * 64
    with pytest.raises(module.WorkflowValidationError, match="object_info hash"):
        module.validate_workflow(value, object_info(), stale, inventory())
