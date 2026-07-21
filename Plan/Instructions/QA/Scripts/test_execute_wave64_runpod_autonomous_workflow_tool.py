from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_workflow_tool.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_workflow_receipt_shadow.py"
INPUT_KINDS = ("workflow", "object_info", "contract", "model_inventory")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path: Path) -> tuple[dict, dict[str, dict], dict[str, bytes]]:
    output = tmp_path / "shadow"
    load(PRODUCER_PATH, "w64_workflow_tool_fixture_producer").produce(
        output, "a" * 40, "2026-07-21T23:20:00Z"
    )
    job_id = "W64-AQA-JOB-workflow-receipt-shadow"
    parsed: dict[str, dict] = {}
    raw: dict[str, bytes] = {}
    for kind in INPUT_KINDS:
        path = output / "jobs" / job_id / "inputs" / f"{kind}.json"
        raw[kind] = path.read_bytes()
        parsed[kind] = json.loads(raw[kind])
    bundle = json.loads((output / "input_receipt_bundle.json").read_text(encoding="utf-8"))
    return bundle, parsed, raw


def request(contract: dict, *, action: str, target: str, role: str, mode: str = "shadow_qualification", parameters=None) -> dict:
    return {
        "schema_version": "wave64.aqa.tool_gateway_request.v1",
        "request_id": f"W64-AQA-TOOL-{action}-test",
        "job_id": contract["job_id"],
        "actor_role_id": role,
        "authority_binding_sha256": contract["contract_id"],
        "execution_mode": mode,
        "action_type": action,
        "target": target,
        "parameters": {} if parameters is None else parameters,
    }


@pytest.mark.parametrize(("action", "target", "role"), [
    ("workflow_inspect", "workflow.graph", "W64-AQA-ROLE-WORKFLOW-ENGINEER"),
    ("validator_run", "validate.workflow.v1", "W64-AQA-ROLE-DETERMINISTIC"),
])
def test_exact_logical_actions_execute_receipt_bound_static_validation(
    tmp_path: Path, action: str, target: str, role: str,
) -> None:
    module = load(EXECUTOR_PATH, f"w64_workflow_tool_{action}")
    gateway = load(GATEWAY_PATH, f"w64_workflow_gateway_{action}")
    bundle, parsed, raw = fixture(tmp_path)
    tool_request = request(parsed["contract"], action=action, target=target, role=role)
    receipt = module.execute_workflow_tool(
        tool_request, gateway.evaluate_request(tool_request), bundle, parsed, raw
    )
    assert receipt["disposition"] == "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_TOOL"
    assert receipt["workflow_validation_disposition"] == "PASS_STATIC_VALIDATION"
    assert receipt["input_binding_disposition"] == "PASS_EXECUTOR_RECEIPT_BOUND"
    assert receipt["findings_count"] == 0
    assert receipt["execution_performed"] is True
    assert receipt["sandbox_execution_performed"] is False
    assert receipt["content_exposed"] is False
    assert receipt["target_write_performed"] is False
    assert receipt["network_used"] is False
    assert set(receipt["validation_result"]["input_executor_receipt_ids"]) == set(INPUT_KINDS)


def test_gateway_decision_tampering_is_rejected(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_workflow_tool_tampered_decision")
    gateway = load(GATEWAY_PATH, "w64_workflow_gateway_tampered_decision")
    bundle, parsed, raw = fixture(tmp_path)
    tool_request = request(
        parsed["contract"], action="workflow_inspect", target="workflow.graph",
        role="W64-AQA-ROLE-WORKFLOW-ENGINEER",
    )
    decision = gateway.evaluate_request(tool_request)
    decision["actor_role_id"] = "W64-AQA-ROLE-CONTROLLER"
    with pytest.raises(module.WorkflowToolExecutorError, match="DECISION_RECOMPUTE_MISMATCH"):
        module.execute_workflow_tool(tool_request, decision, bundle, parsed, raw)


def test_other_validator_targets_and_production_mode_remain_unqualified(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_workflow_tool_scope")
    gateway = load(GATEWAY_PATH, "w64_workflow_gateway_scope")
    bundle, parsed, raw = fixture(tmp_path)
    other_target = request(
        parsed["contract"], action="validator_run", target="measure.image.v1",
        role="W64-AQA-ROLE-DETERMINISTIC",
    )
    assert gateway.evaluate_request(other_target)["admission_disposition"] == "ADMIT_FOR_SEPARATE_EXECUTOR"
    with pytest.raises(module.WorkflowToolExecutorError, match="LOGICAL_TARGET_NOT_QUALIFIED"):
        module.execute_workflow_tool(
            other_target, gateway.evaluate_request(other_target), bundle, parsed, raw
        )
    production = request(
        parsed["contract"], action="validator_run", target="validate.workflow.v1",
        role="W64-AQA-ROLE-DETERMINISTIC", mode="production_release",
    )
    assert gateway.evaluate_request(production)["admission_disposition"] == "ADMIT_FOR_SEPARATE_EXECUTOR"
    with pytest.raises(module.WorkflowToolExecutorError, match="EXECUTION_MODE_NOT_QUALIFIED"):
        module.execute_workflow_tool(
            production, gateway.evaluate_request(production), bundle, parsed, raw
        )


def test_nonempty_parameters_wrong_role_and_contract_authority_fail_closed(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_workflow_tool_bindings")
    gateway = load(GATEWAY_PATH, "w64_workflow_gateway_bindings")
    bundle, parsed, raw = fixture(tmp_path)
    with_parameters = request(
        parsed["contract"], action="workflow_inspect", target="workflow.graph",
        role="W64-AQA-ROLE-WORKFLOW-ENGINEER", parameters={"safe": True},
    )
    with pytest.raises(module.WorkflowToolExecutorError, match="PARAMETERS_MUST_BE_EMPTY"):
        module.execute_workflow_tool(
            with_parameters, gateway.evaluate_request(with_parameters), bundle, parsed, raw
        )
    wrong_role = request(
        parsed["contract"], action="workflow_inspect", target="workflow.graph",
        role="W64-AQA-ROLE-DETERMINISTIC",
    )
    assert gateway.evaluate_request(wrong_role)["admission_disposition"] == "DENY"
    with pytest.raises(module.WorkflowToolExecutorError, match="DECISION_NOT_ADMITTED"):
        module.execute_workflow_tool(
            wrong_role, gateway.evaluate_request(wrong_role), bundle, parsed, raw
        )
    wrong_authority = request(
        parsed["contract"], action="validator_run", target="validate.workflow.v1",
        role="W64-AQA-ROLE-DETERMINISTIC",
    )
    wrong_authority["authority_binding_sha256"] = "f" * 64
    with pytest.raises(module.WorkflowToolExecutorError, match="REQUEST_AUTHORITY_CONTRACT_MISMATCH"):
        module.execute_workflow_tool(
            wrong_authority, gateway.evaluate_request(wrong_authority), bundle, parsed, raw
        )


def test_policy_expansion_weakening_and_elapsed_limit_fail_closed(tmp_path: Path, monkeypatch) -> None:
    module = load(EXECUTOR_PATH, "w64_workflow_tool_policy")
    gateway = load(GATEWAY_PATH, "w64_workflow_gateway_policy")
    bundle, parsed, raw = fixture(tmp_path)
    tool_request = request(
        parsed["contract"], action="validator_run", target="validate.workflow.v1",
        role="W64-AQA-ROLE-DETERMINISTIC",
    )
    decision = gateway.evaluate_request(tool_request)
    base = json.loads(module.EXECUTOR_POLICY_PATH.read_text(encoding="utf-8"))
    expanded = copy.deepcopy(base)
    expanded["qualified_actions"]["shadow_generation_submit"] = {
        "logical_target": "comfyui.prompt", "roles": ["W64-AQA-ROLE-CONTROLLER"]
    }
    with pytest.raises(module.WorkflowToolExecutorError, match="action set changed"):
        module.execute_workflow_tool(
            tool_request, decision, bundle, parsed, raw, executor_policy=expanded
        )
    weakened = copy.deepcopy(base)
    weakened["network_allowed"] = True
    with pytest.raises(module.WorkflowToolExecutorError, match="weakens"):
        module.execute_workflow_tool(
            tool_request, decision, bundle, parsed, raw, executor_policy=weakened
        )
    ticks = iter([0.0, 6.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    with pytest.raises(module.WorkflowToolExecutorError, match="TIME_LIMIT"):
        module.execute_workflow_tool(tool_request, decision, bundle, parsed, raw)
