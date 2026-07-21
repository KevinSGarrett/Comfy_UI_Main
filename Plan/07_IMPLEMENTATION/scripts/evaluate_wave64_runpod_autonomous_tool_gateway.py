#!/usr/bin/env python3
"""Produce a fail-closed, decision-only W64-AQA tool admission receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json"
POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json"
ZERO_HASH = "0" * 64

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}\b"),
}
URI_OR_HOST_PATH = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|^[a-z]:[\\/]|^\\\\)")


class GatewayError(ValueError):
    """Raised when a gateway request or policy cannot be parsed safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GatewayError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayError(f"JSON root must be an object: {path}")
    return value


def _walk(value: Any, path: str = "parameters") -> list[tuple[str, Any]]:
    entries = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            entries.extend(_walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            entries.extend(_walk(child, f"{path}[{index}]"))
    return entries


def _secret_categories(request: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    findings: set[str] = set()
    forbidden_keys = {item.lower() for item in policy["forbidden_parameter_keys"]}
    for path, value in _walk(request.get("parameters", {})):
        leaf = path.rsplit(".", 1)[-1].split("[", 1)[0].lower()
        if leaf in forbidden_keys:
            findings.add("forbidden_parameter_key")
        if isinstance(value, str):
            for category, pattern in SECRET_PATTERNS.items():
                if pattern.search(value):
                    findings.add(category)
    return sorted(findings)


def _contains_external_or_host_path(parameters: dict[str, Any]) -> bool:
    return any(
        isinstance(value, str) and URI_OR_HOST_PATH.search(value) is not None
        for _, value in _walk(parameters)
    )


def _normalize_relative_target(target: str) -> str | None:
    if "\\" in target or URI_OR_HOST_PATH.search(target):
        return None
    pure = PurePosixPath(target)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    normalized = pure.as_posix()
    return normalized if normalized == target else None


def evaluate_request(request: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or _load_json(POLICY_PATH)
    request_schema = _load_json(REQUEST_SCHEMA_PATH)
    decision_schema = _load_json(DECISION_SCHEMA_PATH)
    try:
        jsonschema.Draft7Validator(request_schema).validate(request)
    except jsonschema.ValidationError as exc:
        raise GatewayError(f"request schema validation failed: {exc.message}") from exc
    if policy.get("schema_version") != "wave64.aqa.tool_gateway_policy.v1" or policy.get("decision_only") is not True:
        raise GatewayError("policy is not a decision-only W64-AQA tool policy")

    reasons: set[str] = set()
    action_type = request["action_type"]
    action = policy.get("allowed_actions", {}).get(action_type)
    normalized_target = request["target"]
    secret_categories = _secret_categories(request, policy)
    if secret_categories:
        reasons.add("SECRET_OR_CREDENTIAL_MATERIAL_DENIED")
    if _contains_external_or_host_path(request["parameters"]):
        reasons.add("PARAMETER_URI_OR_HOST_PATH_DENIED")
    if request["authority_binding_sha256"] == ZERO_HASH:
        reasons.add("EMPTY_AUTHORITY_BINDING_DENIED")
    if action_type in policy.get("forbidden_action_types", []):
        reasons.add("EXPLICITLY_FORBIDDEN_ACTION")
    if action is None:
        reasons.add("ACTION_NOT_ALLOWLISTED")
    else:
        if request["actor_role_id"] not in action.get("roles", []):
            reasons.add("ROLE_NOT_AUTHORIZED_FOR_ACTION")
        if request["execution_mode"] == "production_release" and action.get("production_allowed") is not True:
            reasons.add("ACTION_NOT_ALLOWED_IN_PRODUCTION_MODE")
        target_kind = action.get("target_kind")
        if target_kind == "relative_path":
            normalized = _normalize_relative_target(request["target"])
            if normalized is None:
                reasons.add("INVALID_OR_UNSAFE_RELATIVE_PATH")
            else:
                normalized_target = normalized
                allowed_prefixes = [
                    prefix.format(job_id=request["job_id"])
                    for prefix in action.get("target_prefixes", [])
                ]
                if not any(normalized.startswith(prefix) and len(normalized) > len(prefix) for prefix in allowed_prefixes):
                    reasons.add("PATH_OUTSIDE_JOB_SCOPED_ALLOWLIST")
        elif target_kind == "logical_id":
            if request["target"] not in action.get("targets", []):
                reasons.add("LOGICAL_TARGET_NOT_ALLOWLISTED")
        else:
            reasons.add("INVALID_POLICY_TARGET_KIND")

    if not reasons:
        reasons.add("ADMITTED_BY_EXACT_ACTION_ROLE_TARGET_POLICY")
    disposition = "DENY" if reasons != {"ADMITTED_BY_EXACT_ACTION_ROLE_TARGET_POLICY"} else "ADMIT_FOR_SEPARATE_EXECUTOR"
    decision = {
        "schema_version": "wave64.aqa.tool_gateway_decision.v1",
        "decision_id": ZERO_HASH,
        "request_id": request["request_id"],
        "job_id": request["job_id"],
        "actor_role_id": request["actor_role_id"],
        "policy_sha256": hashlib.sha256(canonical_bytes(policy)).hexdigest(),
        "action_type": action_type,
        "normalized_target": normalized_target,
        "admission_disposition": disposition,
        "execution_performed": False,
        "reason_codes": sorted(reasons),
        "secret_scan_categories": secret_categories,
    }
    decision["decision_id"] = hashlib.sha256(canonical_bytes(decision)).hexdigest()
    jsonschema.Draft7Validator(decision_schema).validate(decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        decision = evaluate_request(_load_json(args.request), _load_json(args.policy))
        rendered = json.dumps(decision, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise GatewayError("output already exists; decisions are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (GatewayError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
