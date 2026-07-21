#!/usr/bin/env python3
"""Statically validate ComfyUI API workflows and typed copy-on-write patch proposals."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
VALIDATION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_validation.schema.json"
PATCH_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_patch.schema.json"
PATCH_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_patch_policy.json"
TOOL_RECEIPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_executor_receipt.schema.json"
INPUT_RECEIPT_BUNDLE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_input_receipt_bundle.schema.json"
TOOL_GATEWAY_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json"
TOOL_EXECUTOR_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_executor_policy.json"
CONTRACT_COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py"
ZERO_HASH = "0" * 64
INPUT_KINDS = ("workflow", "object_info", "contract", "model_inventory")
HOST_PATH_OR_URI = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|^[a-z]:[\\/]|^\\\\|^/)")


class WorkflowValidationError(ValueError):
    """Raised when workflow validation inputs are structurally unusable."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowValidationError(f"JSON root must be an object: {path}")
    return value


def _load_json_with_raw_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorkflowValidationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowValidationError(f"JSON root must be an object: {path}")
    return value, raw


def _load_contract_compiler():
    spec = importlib.util.spec_from_file_location("w64_aqa_contract_compiler_for_workflow", CONTRACT_COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise WorkflowValidationError("cannot load immutable contract verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _self_hash(document: dict[str, Any], field: str) -> str:
    candidate = copy.deepcopy(document)
    candidate[field] = ZERO_HASH
    return content_hash(candidate)


def validate_input_receipt_bundle(
    bundle: dict[str, Any],
    raw_inputs: dict[str, bytes],
    parsed_inputs: dict[str, dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, str]:
    try:
        jsonschema.Draft7Validator(_load_json(INPUT_RECEIPT_BUNDLE_SCHEMA_PATH)).validate(bundle)
    except jsonschema.ValidationError as exc:
        raise WorkflowValidationError(f"input receipt bundle schema invalid: {exc.message}") from exc
    if bundle["bundle_id"] != _self_hash(bundle, "bundle_id"):
        raise WorkflowValidationError("input receipt bundle identity mismatch")
    if set(raw_inputs) != set(INPUT_KINDS) or set(parsed_inputs) != set(INPUT_KINDS):
        raise WorkflowValidationError("raw and parsed inputs must cover every workflow inspector input")
    raw_sha256: dict[str, str] = {}
    for kind in INPUT_KINDS:
        raw = raw_inputs[kind]
        if not isinstance(raw, bytes):
            raise WorkflowValidationError(f"{kind} raw input must be bytes")
        try:
            reparsed = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WorkflowValidationError(f"{kind} raw input is not valid JSON") from exc
        if reparsed != parsed_inputs[kind]:
            raise WorkflowValidationError(f"{kind} parsed object does not match its receipt-bound raw bytes")
        raw_sha256[kind] = hashlib.sha256(raw).hexdigest()
    if contract.get("job_id") != bundle["job_id"]:
        raise WorkflowValidationError("contract job_id does not match input receipt bundle")
    if contract.get("contract_id") != bundle["authority_binding_sha256"]:
        raise WorkflowValidationError("contract identity does not match input receipt authority binding")
    try:
        _load_contract_compiler().verify_contract(contract)
    except Exception as exc:
        raise WorkflowValidationError(f"immutable contract verification failed: {exc}") from exc

    receipt_schema = _load_json(TOOL_RECEIPT_SCHEMA_PATH)
    gateway_policy_sha256 = content_hash(_load_json(TOOL_GATEWAY_POLICY_PATH))
    executor_policy_sha256 = content_hash(_load_json(TOOL_EXECUTOR_POLICY_PATH))
    receipt_ids: dict[str, str] = {}
    for kind in INPUT_KINDS:
        receipt = bundle["receipts"][kind]
        try:
            jsonschema.Draft7Validator(receipt_schema).validate(receipt)
        except jsonschema.ValidationError as exc:
            raise WorkflowValidationError(f"{kind} executor receipt schema invalid: {exc.message}") from exc
        expected_target = f"jobs/{bundle['job_id']}/inputs/{kind}.json"
        required_values = {
            "job_id": bundle["job_id"],
            "authority_binding_sha256": bundle["authority_binding_sha256"],
            "action_type": "artifact_read",
            "normalized_target": expected_target,
            "disposition": "PASS_READ_ONLY_ARTIFACT_DIGEST",
            "execution_performed": True,
            "content_exposed": False,
            "target_write_performed": False,
            "network_used": False,
            "gateway_policy_sha256": gateway_policy_sha256,
            "executor_policy_sha256": executor_policy_sha256,
            "artifact_sha256": raw_sha256[kind],
        }
        for field, expected in required_values.items():
            if receipt.get(field) != expected:
                raise WorkflowValidationError(f"{kind} executor receipt {field} binding mismatch")
        if receipt["receipt_id"] != _self_hash(receipt, "receipt_id"):
            raise WorkflowValidationError(f"{kind} executor receipt identity mismatch")
        receipt_ids[kind] = receipt["receipt_id"]
    if len(set(receipt_ids.values())) != len(INPUT_KINDS):
        raise WorkflowValidationError("workflow inspector executor receipt IDs must be distinct")
    return receipt_ids


def _finding(code: str, detail: str, node_id: str | None = None, input_name: str | None = None) -> dict[str, Any]:
    return {"code": code, "severity": "ERROR", "node_id": node_id, "input_name": input_name, "detail": detail[:512]}


def _is_edge(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], (str, int)) and isinstance(value[1], int)


def _input_definition(node_schema: dict[str, Any], input_name: str) -> tuple[Any, bool] | None:
    inputs = node_schema.get("input", {})
    for group, required in (("required", True), ("optional", False), ("hidden", False)):
        definitions = inputs.get(group, {})
        if input_name in definitions:
            return definitions[input_name], required
    return None


def _declared_type(definition: Any) -> Any:
    return definition[0] if isinstance(definition, list) and definition else definition


def _literal_valid(value: Any, definition: Any) -> bool:
    declared = _declared_type(definition)
    if isinstance(declared, list):
        return value in declared
    if declared == "INT":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "FLOAT":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    if declared == "BOOLEAN":
        return isinstance(value, bool)
    if declared in {"STRING", "COMBO"}:
        return isinstance(value, str)
    return True


def _path_safe(value: str) -> bool:
    if HOST_PATH_OR_URI.search(value) or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _acyclic(nodes: dict[str, Any], edges: list[tuple[str, str]]) -> bool:
    indegree = {node_id: 0 for node_id in nodes}
    outgoing = {node_id: [] for node_id in nodes}
    for source, destination in edges:
        if source in nodes and destination in nodes:
            outgoing[source].append(destination)
            indegree[destination] += 1
    pending = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while pending:
        node_id = pending.pop()
        visited += 1
        for destination in outgoing[node_id]:
            indegree[destination] -= 1
            if indegree[destination] == 0:
                pending.append(destination)
    return visited == len(nodes)


def _apply_patch(
    workflow: dict[str, Any], patch: dict[str, Any], policy: dict[str, Any],
    eligible_models: set[str], findings: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    try:
        jsonschema.Draft7Validator(_load_json(PATCH_SCHEMA_PATH)).validate(patch)
    except jsonschema.ValidationError as exc:
        findings.append(_finding("PATCH_SCHEMA_INVALID", exc.message))
        return copy.deepcopy(workflow), False
    if patch["base_workflow_sha256"] != content_hash(workflow):
        findings.append(_finding("PATCH_BASE_HASH_MISMATCH", "patch is not bound to the supplied base workflow"))
        return copy.deepcopy(workflow), False
    if patch["patch_allowlist_id"] != policy["patch_allowlist_id"]:
        findings.append(_finding("PATCH_POLICY_ID_MISMATCH", "patch allowlist ID does not match the active policy"))
        return copy.deepcopy(workflow), False
    candidate = copy.deepcopy(workflow)
    accepted = True
    for operation in patch["operations"]:
        node_id, input_name = operation["node_id"], operation["input_name"]
        node = candidate.get(node_id)
        if not isinstance(node, dict) or input_name not in node.get("inputs", {}):
            findings.append(_finding("PATCH_POINT_NOT_FOUND", "declared node input does not exist", node_id, input_name))
            accepted = False
            continue
        old_value = node["inputs"][input_name]
        if old_value != operation["expected_old_value"]:
            findings.append(_finding("PATCH_EXPECTED_VALUE_MISMATCH", "current input does not match expected_old_value", node_id, input_name))
            accepted = False
            continue
        new_value, kind = operation["new_value"], operation["operation"]
        allowed = False
        if kind == "replace_bounded_numeric" and input_name in policy["bounded_numeric_inputs"]:
            bounds = policy["bounded_numeric_inputs"][input_name]
            allowed = isinstance(new_value, (int, float)) and not isinstance(new_value, bool) and math.isfinite(float(new_value)) and bounds["minimum"] <= new_value <= bounds["maximum"]
        elif kind == "replace_model" and input_name in policy["model_inputs"]:
            allowed = isinstance(new_value, str) and new_value in eligible_models
        elif kind == "replace_prompt_fragment" and input_name in policy["prompt_inputs"]:
            allowed = isinstance(new_value, str) and len(new_value) <= policy["max_prompt_characters"]
        elif kind == "replace_declared_literal" and input_name in policy["declared_literal_inputs"]:
            allowed = isinstance(new_value, (str, int, float, bool))
        if not allowed:
            findings.append(_finding("PATCH_OPERATION_OUTSIDE_ALLOWLIST", "operation, input, value, or range is not allowlisted", node_id, input_name))
            accepted = False
            continue
        node["inputs"][input_name] = new_value
    return candidate if accepted else copy.deepcopy(workflow), accepted


def validate_workflow(
    workflow: dict[str, Any], object_info: dict[str, Any], contract: dict[str, Any],
    model_inventory: dict[str, Any], patch: dict[str, Any] | None = None,
    input_receipt_bundle: dict[str, Any] | None = None,
    input_raw_bytes: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1" or contract.get("modality") != "workflow":
        raise WorkflowValidationError("workflow validation requires a W64-AQA workflow contract")
    if contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise WorkflowValidationError("contract is not ready for a lease")
    workflow_spec = contract.get("workflow_spec")
    if not isinstance(workflow_spec, dict) or workflow_spec.get("sandbox_required") is not True:
        raise WorkflowValidationError("contract lacks a sandbox-required workflow_spec")
    policy = _load_json(PATCH_POLICY_PATH)
    if workflow_spec.get("patch_allowlist_id") != policy.get("patch_allowlist_id"):
        raise WorkflowValidationError("contract patch allowlist does not match active policy")
    object_info_hash = content_hash(object_info)
    if object_info_hash != workflow_spec.get("object_info_sha256"):
        raise WorkflowValidationError("object_info hash does not match immutable contract")
    if model_inventory.get("schema_version") != "wave64.aqa.model_inventory.v1" or not isinstance(model_inventory.get("eligible_model_names"), list):
        raise WorkflowValidationError("model inventory is invalid")
    eligible_models = set(model_inventory["eligible_model_names"])
    if len(eligible_models) != len(model_inventory["eligible_model_names"]):
        raise WorkflowValidationError("model inventory contains duplicates")
    base_hash = content_hash(workflow)
    input_binding_disposition = "UNBOUND_STATIC_TEST_ONLY"
    input_executor_receipt_ids: dict[str, str] = {}
    if input_receipt_bundle is not None or input_raw_bytes is not None:
        if input_receipt_bundle is None or input_raw_bytes is None:
            raise WorkflowValidationError("receipt bundle and raw input bytes must be supplied together")
        input_executor_receipt_ids = validate_input_receipt_bundle(
            input_receipt_bundle,
            input_raw_bytes,
            {
                "workflow": workflow,
                "object_info": object_info,
                "contract": contract,
                "model_inventory": model_inventory,
            },
            contract,
        )
        input_binding_disposition = "PASS_EXECUTOR_RECEIPT_BOUND"
    findings: list[dict[str, Any]] = []
    candidate, patch_accepted = (copy.deepcopy(workflow), True)
    patch_disposition = "NOT_REQUESTED"
    if patch is not None:
        candidate, patch_accepted = _apply_patch(workflow, patch, policy, eligible_models, findings)
        patch_disposition = "TYPED_PATCH_ACCEPTED_FOR_SANDBOX" if patch_accepted else "TYPED_PATCH_REJECTED"

    if not candidate:
        findings.append(_finding("WORKFLOW_EMPTY", "workflow must contain at least one node"))
    edges: list[tuple[str, str]] = []
    output_nodes = 0
    forbidden_names = set(policy["forbidden_input_names"])
    for raw_node_id, node in candidate.items():
        node_id = str(raw_node_id)
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            findings.append(_finding("NODE_SHAPE_INVALID", "node must contain class_type and inputs objects", node_id))
            continue
        class_type, inputs = node["class_type"], node["inputs"]
        node_schema = object_info.get(class_type)
        if not isinstance(node_schema, dict):
            findings.append(_finding("NODE_CLASS_UNAVAILABLE", "class_type is absent from object_info", node_id))
            continue
        if node_schema.get("output_node") is True:
            output_nodes += 1
        required = node_schema.get("input", {}).get("required", {})
        for input_name in required:
            if input_name not in inputs:
                findings.append(_finding("REQUIRED_INPUT_MISSING", "required input is absent", node_id, input_name))
        for input_name, value in inputs.items():
            definition_entry = _input_definition(node_schema, input_name)
            if definition_entry is None:
                findings.append(_finding("INPUT_NOT_DECLARED", "input is absent from object_info schema", node_id, input_name))
                continue
            definition, _ = definition_entry
            if input_name.lower() in forbidden_names:
                findings.append(_finding("FORBIDDEN_INPUT_NAME", "input name is forbidden by security policy", node_id, input_name))
            if _is_edge(value):
                source_id, output_index = str(value[0]), value[1]
                edges.append((source_id, node_id))
                source = candidate.get(source_id)
                if not isinstance(source, dict):
                    findings.append(_finding("EDGE_SOURCE_MISSING", "edge source node does not exist", node_id, input_name))
                    continue
                source_schema = object_info.get(source.get("class_type"), {})
                outputs = source_schema.get("output", []) if isinstance(source_schema, dict) else []
                if output_index < 0 or output_index >= len(outputs):
                    findings.append(_finding("EDGE_OUTPUT_INDEX_INVALID", "edge output index is outside source outputs", node_id, input_name))
                    continue
                source_type, destination_type = outputs[output_index], _declared_type(definition)
                if isinstance(destination_type, str) and source_type not in {destination_type, "*"} and destination_type != "*":
                    findings.append(_finding("EDGE_TYPE_MISMATCH", f"source type {source_type} does not match destination type {destination_type}", node_id, input_name))
            else:
                if not _literal_valid(value, definition):
                    findings.append(_finding("LITERAL_TYPE_OR_OPTION_INVALID", "literal does not match object_info type/options", node_id, input_name))
                options = definition[1] if isinstance(definition, list) and len(definition) > 1 and isinstance(definition[1], dict) else {}
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if "min" in options and value < options["min"] or "max" in options and value > options["max"]:
                        findings.append(_finding("LITERAL_OUTSIDE_NODE_RANGE", "numeric literal is outside object_info range", node_id, input_name))
                if input_name in policy["bounded_numeric_inputs"] and isinstance(value, (int, float)) and not isinstance(value, bool):
                    bounds = policy["bounded_numeric_inputs"][input_name]
                    if value < bounds["minimum"] or value > bounds["maximum"]:
                        findings.append(_finding("LITERAL_OUTSIDE_CONTROLLER_RANGE", "numeric literal is outside controller safety range", node_id, input_name))
                if input_name in policy["model_inputs"] and (not isinstance(value, str) or value not in eligible_models):
                    findings.append(_finding("MODEL_NOT_ELIGIBLE", "model literal is absent from eligible inventory", node_id, input_name))
                if isinstance(value, str) and any(fragment in input_name.lower() for fragment in policy["path_input_fragments"]) and not _path_safe(value):
                    findings.append(_finding("PATH_LITERAL_UNSAFE", "path-like input is absolute, traversing, URI, or host-specific", node_id, input_name))
    acyclic = _acyclic(candidate, edges)
    if not acyclic:
        findings.append(_finding("WORKFLOW_CYCLE_DETECTED", "workflow graph contains a cycle"))
    if output_nodes < 1:
        findings.append(_finding("OUTPUT_NODE_MISSING", "workflow has no object_info-declared output node"))

    validation = {
        "schema_version": "wave64.aqa.workflow_validation.v1",
        "validation_id": ZERO_HASH,
        "contract_id": contract["contract_id"],
        "base_workflow_sha256": base_hash,
        "candidate_workflow_sha256": content_hash(candidate),
        "object_info_sha256": object_info_hash,
        "model_inventory_sha256": content_hash(model_inventory),
        "patch_policy_sha256": content_hash(policy),
        "input_binding_disposition": input_binding_disposition,
        "input_executor_receipt_ids": input_executor_receipt_ids,
        "graph_summary": {
            "node_count": len(candidate), "edge_count": len(edges),
            "output_node_count": output_nodes, "acyclic": acyclic,
        },
        "findings": findings,
        "patch_disposition": patch_disposition,
        "sandbox_execution_performed": False,
        "disposition": "PASS_STATIC_VALIDATION" if not findings and patch_accepted else "FAIL_STATIC_VALIDATION",
    }
    validation["validation_id"] = hashlib.sha256(canonical_bytes(validation)).hexdigest()
    jsonschema.Draft7Validator(_load_json(VALIDATION_SCHEMA_PATH)).validate(validation)
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path)
    parser.add_argument("object_info", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("model_inventory", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--input-receipt-bundle", type=Path)
    parser.add_argument("--allow-unbound-static-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.input_receipt_bundle is None and not args.allow_unbound_static_test:
            raise WorkflowValidationError(
                "CLI validation requires --input-receipt-bundle; unbound mode is test-only"
            )
        loaded = {
            "workflow": _load_json_with_raw_bytes(args.workflow),
            "object_info": _load_json_with_raw_bytes(args.object_info),
            "contract": _load_json_with_raw_bytes(args.contract),
            "model_inventory": _load_json_with_raw_bytes(args.model_inventory),
        }
        result = validate_workflow(
            loaded["workflow"][0],
            loaded["object_info"][0],
            loaded["contract"][0],
            loaded["model_inventory"][0],
            _load_json(args.patch) if args.patch else None,
            _load_json(args.input_receipt_bundle) if args.input_receipt_bundle else None,
            {kind: loaded[kind][1] for kind in INPUT_KINDS} if args.input_receipt_bundle else None,
        )
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise WorkflowValidationError("output already exists; validations are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (WorkflowValidationError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
