#!/usr/bin/env python3
"""Stage one receipt-bound typed workflow candidate by immutable copy-on-write."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
VALIDATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py"
PUBLISHER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
REQUEST_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_candidate_staging_receipt.schema.json"
GATEWAY_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json"
STAGER_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_candidate_stager_policy.json"
PATCH_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_patch_policy.json"
ZERO_HASH = "0" * 64
INPUT_NAMES = ("workflow", "object_info", "contract", "model_inventory")


class CandidateStagingError(ValueError):
    """Raised when a candidate cannot be staged without weakening isolation."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateStagingError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateStagingError(f"JSON root must be an object: {path}")
    return value


def _load_component(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CandidateStagingError(f"cannot load required component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _is_reparse(value: os.stat_result) -> bool:
    attributes = int(getattr(value, "st_file_attributes", 0))
    flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(value.st_mode) or bool(attributes & flag)


def _validate_policy(policy: dict[str, Any]) -> None:
    exact = {
        "schema_version": "wave64.aqa.workflow_candidate_stager_policy.v1",
        "qualified_action": "candidate_write",
        "execution_modes": ["shadow_qualification"],
        "roles": ["W64-AQA-ROLE-CONTROLLER", "W64-AQA-ROLE-DETERMINISTIC"],
        "target_template": "jobs/{job_id}/candidates/workflow.candidate.json",
        "parameters_required_empty": True,
        "input_receipt_bundle_required": True,
        "typed_patch_required": True,
        "copy_on_write_required": True,
        "immutable_candidate_required": True,
        "base_input_write_allowed": False,
        "overwrite_allowed": False,
        "comfyui_execution_allowed": False,
        "model_inference_allowed": False,
        "network_allowed": False,
        "production_mode_allowed": False,
        "max_total_input_bytes": 16777216,
        "max_patch_bytes": 65536,
        "max_candidate_bytes": 16777216,
        "max_elapsed_ms": 5000,
        "all_other_targets": "UNQUALIFIED_DENY",
    }
    if any(policy.get(key) != value for key, value in exact.items()):
        raise CandidateStagingError("candidate stager policy changed or weakened")


def _resolve_plain_path(root: Path, relative: str, *, must_exist: bool) -> Path:
    root_stat = os.lstat(root)
    if _is_reparse(root_stat) or not stat.S_ISDIR(root_stat.st_mode):
        raise CandidateStagingError("SANDBOX_ROOT_NOT_PLAIN_DIRECTORY")
    canonical_root = root.resolve(strict=True)
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise CandidateStagingError("UNSAFE_SANDBOX_RELATIVE_PATH")
    current = canonical_root
    parts = pure.parts if must_exist else pure.parts[:-1]
    for part in parts:
        current = current / part
        try:
            current_stat = os.lstat(current)
        except OSError as exc:
            raise CandidateStagingError("SANDBOX_PATH_COMPONENT_MISSING") from exc
        if _is_reparse(current_stat):
            raise CandidateStagingError("SYMLINK_OR_REPARSE_POINT_DENIED")
        if current != canonical_root / pure and not stat.S_ISDIR(current_stat.st_mode):
            raise CandidateStagingError("SANDBOX_PARENT_NOT_DIRECTORY")
    target = canonical_root.joinpath(*pure.parts)
    try:
        target.parent.resolve(strict=True).relative_to(canonical_root)
    except (OSError, ValueError) as exc:
        raise CandidateStagingError("SANDBOX_TARGET_ESCAPED_ROOT") from exc
    if must_exist:
        target_stat = os.lstat(target)
        if _is_reparse(target_stat) or not stat.S_ISREG(target_stat.st_mode):
            raise CandidateStagingError("SANDBOX_INPUT_NOT_PLAIN_FILE")
    elif target.exists() or target.is_symlink():
        raise CandidateStagingError("CANDIDATE_TARGET_ALREADY_EXISTS")
    return target


def _read_bound_input(root: Path, relative: str) -> tuple[dict[str, Any], bytes, Path]:
    path = _resolve_plain_path(root, relative, must_exist=True)
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateStagingError(f"cannot read bound input {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateStagingError(f"bound input must be an object: {relative}")
    return value, raw, path


def stage_candidate(
    request: dict[str, Any],
    decision: dict[str, Any],
    sandbox_root: Path,
    *,
    gateway_policy: dict[str, Any] | None = None,
    stager_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    gateway_policy = gateway_policy or _load_json(GATEWAY_POLICY_PATH)
    stager_policy = stager_policy or _load_json(STAGER_POLICY_PATH)
    _validate_policy(stager_policy)
    try:
        jsonschema.Draft7Validator(_load_json(REQUEST_SCHEMA_PATH)).validate(request)
        jsonschema.Draft7Validator(_load_json(DECISION_SCHEMA_PATH)).validate(decision)
    except jsonschema.ValidationError as exc:
        raise CandidateStagingError(f"gateway input schema invalid: {exc.message}") from exc
    gateway = _load_component(GATEWAY_PATH, "w64_gateway_for_candidate_stager")
    expected_decision = gateway.evaluate_request(request, gateway_policy)
    if decision != expected_decision:
        raise CandidateStagingError("DECISION_RECOMPUTE_MISMATCH")
    if decision["admission_disposition"] != "ADMIT_FOR_SEPARATE_EXECUTOR":
        raise CandidateStagingError("DECISION_NOT_ADMITTED")
    if request["action_type"] != "candidate_write":
        raise CandidateStagingError("ACTION_NOT_QUALIFIED_BY_CANDIDATE_STAGER")
    if request["execution_mode"] not in stager_policy["execution_modes"]:
        raise CandidateStagingError("EXECUTION_MODE_NOT_QUALIFIED_BY_CANDIDATE_STAGER")
    if request["actor_role_id"] not in stager_policy["roles"]:
        raise CandidateStagingError("ROLE_NOT_QUALIFIED_BY_CANDIDATE_STAGER")
    if request["parameters"] != {}:
        raise CandidateStagingError("CANDIDATE_WRITE_PARAMETERS_MUST_BE_EMPTY")
    expected_target = stager_policy["target_template"].format(job_id=request["job_id"])
    if request["target"] != expected_target or decision["normalized_target"] != expected_target:
        raise CandidateStagingError("CANDIDATE_TARGET_NOT_QUALIFIED")

    job_id = request["job_id"]
    parsed: dict[str, dict[str, Any]] = {}
    raw: dict[str, bytes] = {}
    source_paths: dict[str, Path] = {}
    for name in INPUT_NAMES:
        parsed[name], raw[name], source_paths[name] = _read_bound_input(
            sandbox_root, f"jobs/{job_id}/inputs/{name}.json"
        )
    bundle, bundle_raw, _ = _read_bound_input(
        sandbox_root, f"jobs/{job_id}/inputs/input_receipt_bundle.json"
    )
    patch, patch_raw, _ = _read_bound_input(
        sandbox_root, f"jobs/{job_id}/proposals/workflow.patch.json"
    )
    if sum(len(value) for value in raw.values()) + len(bundle_raw) > stager_policy["max_total_input_bytes"]:
        raise CandidateStagingError("CANDIDATE_STAGER_TOTAL_INPUT_LIMIT_EXCEEDED")
    if len(patch_raw) > stager_policy["max_patch_bytes"]:
        raise CandidateStagingError("CANDIDATE_STAGER_PATCH_LIMIT_EXCEEDED")
    if parsed["contract"].get("job_id") != job_id:
        raise CandidateStagingError("REQUEST_JOB_CONTRACT_MISMATCH")
    if parsed["contract"].get("contract_id") != request["authority_binding_sha256"]:
        raise CandidateStagingError("REQUEST_AUTHORITY_CONTRACT_MISMATCH")

    validator = _load_component(VALIDATOR_PATH, "w64_validator_for_candidate_stager")
    validation = validator.validate_workflow(
        parsed["workflow"], parsed["object_info"], parsed["contract"],
        parsed["model_inventory"], patch=patch, input_receipt_bundle=bundle,
        input_raw_bytes=raw,
    )
    if validation["disposition"] != "PASS_STATIC_VALIDATION":
        raise CandidateStagingError("TYPED_PATCH_STATIC_VALIDATION_FAILED")
    if validation["patch_disposition"] != "TYPED_PATCH_ACCEPTED_FOR_SANDBOX":
        raise CandidateStagingError("TYPED_PATCH_NOT_ACCEPTED_FOR_SANDBOX")
    if validation["input_binding_disposition"] != "PASS_EXECUTOR_RECEIPT_BOUND":
        raise CandidateStagingError("TYPED_PATCH_INPUTS_NOT_RECEIPT_BOUND")
    patch_findings: list[dict[str, Any]] = []
    patch_policy = _load_json(PATCH_POLICY_PATH)
    candidate, accepted = validator._apply_patch(
        parsed["workflow"], patch, patch_policy,
        set(parsed["model_inventory"]["eligible_model_names"]), patch_findings,
    )
    if not accepted or patch_findings:
        raise CandidateStagingError("TYPED_PATCH_APPLICATION_DIVERGED")
    if validator.content_hash(candidate) != validation["candidate_workflow_sha256"]:
        raise CandidateStagingError("CANDIDATE_HASH_DIVERGED_FROM_VALIDATION")
    rendered = json.dumps(candidate, indent=2, sort_keys=True) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    if len(rendered_bytes) > stager_policy["max_candidate_bytes"]:
        raise CandidateStagingError("CANDIDATE_STAGER_OUTPUT_LIMIT_EXCEEDED")
    if source_paths["workflow"].read_bytes() != raw["workflow"]:
        raise CandidateStagingError("BASE_WORKFLOW_CHANGED_BEFORE_PUBLISH")
    if (time.monotonic() - started) * 1000 > stager_policy["max_elapsed_ms"]:
        raise CandidateStagingError("CANDIDATE_STAGER_TIME_LIMIT_EXCEEDED")
    destination = _resolve_plain_path(sandbox_root, expected_target, must_exist=False)
    publisher = _load_component(PUBLISHER_PATH, "w64_candidate_immutable_publisher")
    publisher._publish_immutable(destination, rendered)
    if source_paths["workflow"].read_bytes() != raw["workflow"]:
        destination.unlink(missing_ok=False)
        raise CandidateStagingError("BASE_WORKFLOW_CHANGED_DURING_PUBLISH")

    receipt = {
        "schema_version": "wave64.aqa.workflow_candidate_staging_receipt.v1",
        "receipt_id": ZERO_HASH,
        "request_id": request["request_id"],
        "decision_id": decision["decision_id"],
        "job_id": job_id,
        "actor_role_id": request["actor_role_id"],
        "authority_binding_sha256": request["authority_binding_sha256"],
        "gateway_policy_sha256": hashlib.sha256(canonical_bytes(gateway_policy)).hexdigest(),
        "stager_policy_sha256": hashlib.sha256(canonical_bytes(stager_policy)).hexdigest(),
        "patch_sha256": hashlib.sha256(canonical_bytes(patch)).hexdigest(),
        "base_workflow_sha256": validation["base_workflow_sha256"],
        "candidate_workflow_sha256": validation["candidate_workflow_sha256"],
        "candidate_file_sha256": hashlib.sha256(rendered_bytes).hexdigest(),
        "workflow_validation_id": validation["validation_id"],
        "input_receipt_bundle_id": bundle["bundle_id"],
        "normalized_target": expected_target,
        "execution_performed": True,
        "candidate_write_performed": True,
        "base_input_write_performed": False,
        "overwrite_performed": False,
        "comfyui_execution_performed": False,
        "model_inference_performed": False,
        "network_used": False,
        "copy_on_write_verified": True,
        "disposition": "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGED",
        "reason_codes": [
            "ADMITTED_DECISION_RECOMPUTED",
            "FOUR_INPUT_RECEIPTS_VERIFIED",
            "TYPED_PATCH_STATIC_VALIDATION_PASS",
            "IMMUTABLE_COPY_ON_WRITE_PUBLISHED",
            "BASE_INPUT_UNCHANGED",
        ],
    }
    receipt["receipt_id"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    jsonschema.Draft7Validator(_load_json(RECEIPT_SCHEMA_PATH)).validate(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("decision", type=Path)
    parser.add_argument("sandbox_root", type=Path)
    parser.add_argument("--gateway-policy", type=Path, default=GATEWAY_POLICY_PATH)
    parser.add_argument("--stager-policy", type=Path, default=STAGER_POLICY_PATH)
    parser.add_argument("--receipt-output", type=Path)
    args = parser.parse_args()
    try:
        receipt = stage_candidate(
            _load_json(args.request), _load_json(args.decision), args.sandbox_root,
            gateway_policy=_load_json(args.gateway_policy),
            stager_policy=_load_json(args.stager_policy),
        )
        rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.receipt_output:
            publisher = _load_component(PUBLISHER_PATH, "w64_candidate_receipt_publisher")
            publisher._publish_immutable(args.receipt_output, rendered)
        else:
            sys.stdout.write(rendered)
    except (CandidateStagingError, jsonschema.ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
