#!/usr/bin/env python3
"""Execute exact receipt-bound workflow inspection or validation logical tools."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
ARTIFACT_EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
WORKFLOW_VALIDATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py"
REQUEST_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_tool_execution_receipt.schema.json"
WORKFLOW_VALIDATION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_validation.schema.json"
GATEWAY_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json"
EXECUTOR_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_tool_executor_policy.json"
ZERO_HASH = "0" * 64
INPUT_KINDS = ("workflow", "object_info", "contract", "model_inventory")


class WorkflowToolExecutorError(ValueError):
    """Raised when an exact logical workflow tool cannot execute safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowToolExecutorError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowToolExecutorError(f"JSON root must be an object: {path}")
    return value


def _load_json_with_raw(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorkflowToolExecutorError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowToolExecutorError(f"JSON root must be an object: {path}")
    return value, raw


def _load_component(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise WorkflowToolExecutorError(f"cannot load required component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _self_hash(value: dict[str, Any], field: str) -> str:
    candidate = copy.deepcopy(value)
    candidate[field] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(candidate)).hexdigest()


def _validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != "wave64.aqa.workflow_tool_executor_policy.v1":
        raise WorkflowToolExecutorError("unsupported workflow tool executor policy")
    expected_actions = {"workflow_inspect", "validator_run"}
    if set(policy.get("qualified_actions", {})) != expected_actions:
        raise WorkflowToolExecutorError("workflow tool executor action set changed")
    mandatory = {
        "parameters_required_empty": True,
        "input_receipt_bundle_required": True,
        "content_exposure_allowed": False,
        "sandbox_execution_allowed": False,
        "target_write_allowed": False,
        "network_allowed": False,
        "all_other_actions": "UNQUALIFIED_DENY",
    }
    if any(policy.get(key) != expected for key, expected in mandatory.items()):
        raise WorkflowToolExecutorError("workflow tool executor policy weakens mandatory controls")
    exact_limits = {
        "max_total_input_bytes": 16777216,
        "max_workflow_nodes": 4096,
        "max_findings": 1024,
        "max_elapsed_ms": 5000,
    }
    if any(policy.get(key) != expected for key, expected in exact_limits.items()):
        raise WorkflowToolExecutorError("workflow tool executor limits changed")
    if policy.get("execution_modes") != ["shadow_qualification"]:
        raise WorkflowToolExecutorError("workflow tool executor must remain shadow-only")


def execute_workflow_tool(
    request: dict[str, Any],
    decision: dict[str, Any],
    input_receipt_bundle: dict[str, Any],
    parsed_inputs: dict[str, dict[str, Any]],
    raw_inputs: dict[str, bytes],
    *,
    gateway_policy: dict[str, Any] | None = None,
    executor_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    gateway_policy = gateway_policy or _load_json(GATEWAY_POLICY_PATH)
    executor_policy = executor_policy or _load_json(EXECUTOR_POLICY_PATH)
    _validate_policy(executor_policy)
    try:
        jsonschema.Draft7Validator(_load_json(REQUEST_SCHEMA_PATH)).validate(request)
        jsonschema.Draft7Validator(_load_json(DECISION_SCHEMA_PATH)).validate(decision)
    except jsonschema.ValidationError as exc:
        raise WorkflowToolExecutorError(f"gateway input schema invalid: {exc.message}") from exc
    expected_decision = _load_component(GATEWAY_PATH, "w64_gateway_for_workflow_tool").evaluate_request(
        request, gateway_policy
    )
    if decision != expected_decision:
        raise WorkflowToolExecutorError("DECISION_RECOMPUTE_MISMATCH")
    if decision["admission_disposition"] != "ADMIT_FOR_SEPARATE_EXECUTOR":
        raise WorkflowToolExecutorError("DECISION_NOT_ADMITTED")
    action = executor_policy["qualified_actions"].get(request["action_type"])
    if action is None:
        raise WorkflowToolExecutorError("ACTION_NOT_QUALIFIED_BY_WORKFLOW_EXECUTOR")
    if request["target"] != action["logical_target"] or decision["normalized_target"] != request["target"]:
        raise WorkflowToolExecutorError("LOGICAL_TARGET_NOT_QUALIFIED_BY_WORKFLOW_EXECUTOR")
    if request["actor_role_id"] not in action["roles"]:
        raise WorkflowToolExecutorError("ROLE_NOT_QUALIFIED_BY_WORKFLOW_EXECUTOR")
    if request["execution_mode"] not in executor_policy["execution_modes"]:
        raise WorkflowToolExecutorError("EXECUTION_MODE_NOT_QUALIFIED_BY_WORKFLOW_EXECUTOR")
    if request["parameters"] != {}:
        raise WorkflowToolExecutorError("WORKFLOW_TOOL_PARAMETERS_MUST_BE_EMPTY")
    if set(parsed_inputs) != set(INPUT_KINDS) or set(raw_inputs) != set(INPUT_KINDS):
        raise WorkflowToolExecutorError("workflow tool inputs are incomplete")
    if sum(len(raw_inputs[kind]) for kind in INPUT_KINDS) > executor_policy["max_total_input_bytes"]:
        raise WorkflowToolExecutorError("WORKFLOW_TOOL_TOTAL_INPUT_LIMIT_EXCEEDED")
    if len(parsed_inputs["workflow"]) > executor_policy["max_workflow_nodes"]:
        raise WorkflowToolExecutorError("WORKFLOW_TOOL_NODE_LIMIT_EXCEEDED")
    if parsed_inputs["contract"].get("job_id") != request["job_id"]:
        raise WorkflowToolExecutorError("REQUEST_JOB_CONTRACT_MISMATCH")
    if parsed_inputs["contract"].get("contract_id") != request["authority_binding_sha256"]:
        raise WorkflowToolExecutorError("REQUEST_AUTHORITY_CONTRACT_MISMATCH")

    validator = _load_component(WORKFLOW_VALIDATOR_PATH, "w64_validator_for_workflow_tool")
    validation = validator.validate_workflow(
        parsed_inputs["workflow"],
        parsed_inputs["object_info"],
        parsed_inputs["contract"],
        parsed_inputs["model_inventory"],
        input_receipt_bundle=input_receipt_bundle,
        input_raw_bytes=raw_inputs,
    )
    try:
        jsonschema.Draft7Validator(_load_json(WORKFLOW_VALIDATION_SCHEMA_PATH)).validate(validation)
    except jsonschema.ValidationError as exc:
        raise WorkflowToolExecutorError(f"workflow validation output invalid: {exc.message}") from exc
    if validation["input_binding_disposition"] != "PASS_EXECUTOR_RECEIPT_BOUND":
        raise WorkflowToolExecutorError("WORKFLOW_VALIDATION_NOT_RECEIPT_BOUND")
    if validation["sandbox_execution_performed"] is not False:
        raise WorkflowToolExecutorError("WORKFLOW_VALIDATION_CLAIMED_SANDBOX_EXECUTION")
    if len(validation["findings"]) > executor_policy["max_findings"]:
        raise WorkflowToolExecutorError("WORKFLOW_TOOL_FINDINGS_LIMIT_EXCEEDED")
    if (time.monotonic() - started) * 1000 > executor_policy["max_elapsed_ms"]:
        raise WorkflowToolExecutorError("WORKFLOW_TOOL_TIME_LIMIT_EXCEEDED")
    passed = validation["disposition"] == "PASS_STATIC_VALIDATION"
    receipt = {
        "schema_version": "wave64.aqa.workflow_tool_execution_receipt.v1",
        "receipt_id": ZERO_HASH,
        "request_id": request["request_id"],
        "decision_id": decision["decision_id"],
        "job_id": request["job_id"],
        "actor_role_id": request["actor_role_id"],
        "authority_binding_sha256": request["authority_binding_sha256"],
        "gateway_policy_sha256": hashlib.sha256(canonical_bytes(gateway_policy)).hexdigest(),
        "executor_policy_sha256": hashlib.sha256(canonical_bytes(executor_policy)).hexdigest(),
        "action_type": request["action_type"],
        "logical_target": request["target"],
        "execution_performed": True,
        "content_exposed": False,
        "sandbox_execution_performed": False,
        "target_write_performed": False,
        "network_used": False,
        "input_receipt_bundle_id": input_receipt_bundle["bundle_id"],
        "workflow_validation_id": validation["validation_id"],
        "workflow_validation_disposition": validation["disposition"],
        "input_binding_disposition": validation["input_binding_disposition"],
        "findings_count": len(validation["findings"]),
        "validation_result": validation,
        "disposition": (
            "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_TOOL"
            if passed else "COMPLETED_RECEIPT_BOUND_STATIC_VALIDATION_FAIL"
        ),
        "reason_codes": [
            "ADMITTED_DECISION_RECOMPUTED",
            "EXACT_LOGICAL_ACTION_TARGET",
            "FOUR_INPUT_RECEIPTS_VERIFIED",
            "STATIC_VALIDATION_COMPLETED",
        ],
    }
    receipt["receipt_id"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    jsonschema.Draft7Validator(_load_json(RECEIPT_SCHEMA_PATH)).validate(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("decision", type=Path)
    parser.add_argument("workflow", type=Path)
    parser.add_argument("object_info", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("model_inventory", type=Path)
    parser.add_argument("input_receipt_bundle", type=Path)
    parser.add_argument("--gateway-policy", type=Path, default=GATEWAY_POLICY_PATH)
    parser.add_argument("--executor-policy", type=Path, default=EXECUTOR_POLICY_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        loaded = {
            "workflow": _load_json_with_raw(args.workflow),
            "object_info": _load_json_with_raw(args.object_info),
            "contract": _load_json_with_raw(args.contract),
            "model_inventory": _load_json_with_raw(args.model_inventory),
        }
        receipt = execute_workflow_tool(
            _load_json(args.request),
            _load_json(args.decision),
            _load_json(args.input_receipt_bundle),
            {kind: loaded[kind][0] for kind in INPUT_KINDS},
            {kind: loaded[kind][1] for kind in INPUT_KINDS},
            gateway_policy=_load_json(args.gateway_policy),
            executor_policy=_load_json(args.executor_policy),
        )
        rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.output:
            _load_component(ARTIFACT_EXECUTOR_PATH, "w64_atomic_receipt_publisher")._publish_immutable(
                args.output, rendered
            )
        else:
            sys.stdout.write(rendered)
    except (WorkflowToolExecutorError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
