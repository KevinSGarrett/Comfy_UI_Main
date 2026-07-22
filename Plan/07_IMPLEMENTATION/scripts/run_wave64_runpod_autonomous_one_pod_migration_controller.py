#!/usr/bin/env python3
"""Advance decision-only W64-AQA one-pod migration state without mutating RunPod."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
EVENT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_event.schema.json"
STATE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_state.schema.json"
POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_one_pod_migration_policy.json"
ZERO_HASH = "0" * 64


class MigrationError(ValueError):
    """Raised when a migration transition would violate the one-pod safety policy."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MigrationError(f"JSON root must be an object: {path}")
    return value


def _seal(state: dict[str, Any]) -> dict[str, Any]:
    state["state_id"] = ZERO_HASH
    state["state_id"] = hashlib.sha256(canonical_bytes(state)).hexdigest()
    jsonschema.Draft7Validator(_load_json(STATE_SCHEMA_PATH)).validate(state)
    return state


def initialize_state(current_pod_id: str, network_volume_id: str) -> dict[str, Any]:
    if not current_pod_id or not network_volume_id:
        raise MigrationError("current pod and network volume IDs are required")
    return _seal({
        "schema_version": "wave64.aqa.one_pod_migration_state.v1",
        "state_id": ZERO_HASH, "previous_state_id": None, "sequence": 0,
        "authoritative_pod_id": current_pod_id, "legacy_pod_id": None,
        "network_volume_id": network_volume_id, "profile_id": "preferred_2xa40",
        "candidate_pod_id": None, "candidate_hourly_usd": None, "passed_gates": [],
        "phase": "STOCK_WAIT", "current_pod_remains_authoritative": True,
        "old_pod_stop_authorized": False, "execution_performed": False,
        "last_event_id": None, "reason_codes": ["CURRENT_POD_REMAINS_AUTHORITATIVE_WHILE_STOCK_WATCH_CONTINUES"],
    })


def _validate_profile(event: dict[str, Any], policy: dict[str, Any]) -> float:
    key = "preferred_profile" if event["profile_id"] == "preferred_2xa40" else "performance_fallback_profile"
    required = policy[key]
    observed = event.get("observed_profile")
    if not isinstance(observed, dict):
        raise MigrationError("candidate creation requires an observed hardware profile")
    failures = []
    if observed["gpu_type"] != required["gpu_type"]:
        failures.append("gpu_type")
    if observed["gpu_count"] != required["gpu_count"]:
        failures.append("gpu_count")
    if observed["aggregate_vram_gb"] < required["minimum_aggregate_vram_gb"]:
        failures.append("aggregate_vram")
    if observed["ram_gb"] < required["minimum_ram_gb"]:
        failures.append("ram")
    if observed["vcpu"] < required["minimum_vcpu"]:
        failures.append("vcpu")
    if observed["hourly_usd"] > required["maximum_hourly_usd"]:
        failures.append("hourly_cost")
    if failures:
        raise MigrationError(f"candidate profile violates: {','.join(failures)}")
    if required["fallback_approval_required"] and event.get("integration_authority_approval_sha256") is None:
        raise MigrationError("performance fallback requires explicit integration-authority approval")
    return float(observed["hourly_usd"])


def transition(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    policy = _load_json(POLICY_PATH)
    try:
        jsonschema.Draft7Validator(_load_json(STATE_SCHEMA_PATH)).validate(state)
        jsonschema.Draft7Validator(_load_json(EVENT_SCHEMA_PATH)).validate(event)
    except jsonschema.ValidationError as exc:
        raise MigrationError(f"state or event schema validation failed: {exc.message}") from exc
    unsealed = dict(state)
    unsealed["state_id"] = ZERO_HASH
    if hashlib.sha256(canonical_bytes(unsealed)).hexdigest() != state["state_id"]:
        raise MigrationError("migration state hash chain validation failed")
    if policy.get("decision_only") is not True:
        raise MigrationError("migration policy must remain decision-only")
    next_state = dict(state)
    next_state.update({
        "previous_state_id": state["state_id"], "sequence": state["sequence"] + 1,
        "last_event_id": event["event_id"], "execution_performed": False,
    })
    event_type = event["event_type"]
    reasons: set[str] = set()

    if event_type == "STOCK_UNAVAILABLE":
        if state["phase"] != "STOCK_WAIT" or state["candidate_pod_id"] is not None:
            raise MigrationError("stock-unavailable event is valid only while waiting without a candidate")
        reasons.add("EXACT_PROFILE_STOCK_UNAVAILABLE_CURRENT_POD_CONTINUES")
    elif event_type == "CANDIDATE_CREATED":
        if state["phase"] != "STOCK_WAIT" or state["candidate_pod_id"] is not None:
            raise MigrationError("duplicate or out-of-phase candidate creation denied")
        if not event["candidate_pod_id"]:
            raise MigrationError("candidate_pod_id is required")
        if event["queue_idle"] is not True:
            raise MigrationError("candidate creation requires an idle current ComfyUI queue")
        if event["network_volume_id"] != state["network_volume_id"]:
            raise MigrationError("candidate must bind the authoritative network volume")
        hourly = _validate_profile(event, policy)
        next_state.update({
            "profile_id": event["profile_id"], "candidate_pod_id": event["candidate_pod_id"],
            "candidate_hourly_usd": hourly, "passed_gates": [], "phase": "CANDIDATE_QUALIFYING",
            "current_pod_remains_authoritative": True, "old_pod_stop_authorized": False,
        })
        reasons.add("EXACT_CANDIDATE_ADMITTED_FOR_BOUNDED_QUALIFICATION")
    elif event_type == "QUALIFICATION_GATE":
        if state["phase"] != "CANDIDATE_QUALIFYING" or event["candidate_pod_id"] != state["candidate_pod_id"]:
            raise MigrationError("qualification gate does not bind the active candidate")
        required_gates = set(policy["required_qualification_gates"])
        if event["gate_id"] not in required_gates or event["passed"] is None or not event["evidence_sha256"]:
            raise MigrationError("qualification gate ID, disposition, and evidence are required")
        if event["passed"] is False:
            next_state.update({"phase": "ROLLBACK_REQUIRED", "old_pod_stop_authorized": False})
            reasons.add("CANDIDATE_GATE_FAILED_ROLLBACK_REQUIRED")
        else:
            passed = set(state["passed_gates"])
            passed.add(event["gate_id"])
            next_state["passed_gates"] = sorted(passed)
            if passed == required_gates:
                next_state["phase"] = "MIGRATION_READY"
                reasons.add("ALL_CANDIDATE_GATES_PASS_INTEGRATION_SWITCH_PENDING")
            else:
                reasons.add("CANDIDATE_GATE_RECORDED_QUALIFICATION_CONTINUES")
    elif event_type == "INTEGRATION_SWITCH_COMMITTED":
        if state["phase"] != "MIGRATION_READY" or event["candidate_pod_id"] != state["candidate_pod_id"]:
            raise MigrationError("integration switch requires the fully qualified active candidate")
        if event["integration_authority_approval_sha256"] is None:
            raise MigrationError("integration switch requires integration-authority approval")
        next_state.update({
            "authoritative_pod_id": state["candidate_pod_id"], "legacy_pod_id": state["authoritative_pod_id"],
            "candidate_pod_id": None, "phase": "NEW_AUTHORITATIVE",
            "current_pod_remains_authoritative": False, "old_pod_stop_authorized": True,
        })
        reasons.add("INTEGRATION_AUTHORITY_COMMITTED_SWITCH_LEGACY_STOP_MAY_BE_SEPARATELY_REQUESTED")
    elif event_type == "REQUEST_OLD_POD_STOP":
        if state["phase"] != "NEW_AUTHORITATIVE" or not state["old_pod_stop_authorized"]:
            raise MigrationError("old pod stop is forbidden before a committed integration switch")
        if event["integration_authority_approval_sha256"] is None:
            raise MigrationError("old pod stop request requires integration-authority approval")
        reasons.add("OLD_POD_STOP_ADMITTED_FOR_SEPARATE_EXECUTOR_NOT_EXECUTED")
    elif event_type == "CANDIDATE_TERMINATED":
        if state["phase"] not in {"CANDIDATE_QUALIFYING", "ROLLBACK_REQUIRED"}:
            raise MigrationError("candidate termination is valid only during qualification or rollback")
        if event["candidate_pod_id"] != state["candidate_pod_id"]:
            raise MigrationError("candidate termination does not bind the active candidate")
        next_state.update({
            "candidate_pod_id": None, "candidate_hourly_usd": None, "passed_gates": [],
            "phase": "ROLLED_BACK", "current_pod_remains_authoritative": True,
            "old_pod_stop_authorized": False,
        })
        reasons.add("CANDIDATE_TERMINATED_CURRENT_POD_RETAINED")
    else:  # pragma: no cover - schema owns this boundary
        raise MigrationError("unsupported migration event")
    next_state["reason_codes"] = sorted(reasons)
    return _seal(next_state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("current_pod_id")
    initialize.add_argument("network_volume_id")
    advance = subparsers.add_parser("transition")
    advance.add_argument("state", type=Path)
    advance.add_argument("event", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        policy = _load_json(POLICY_PATH)
        if policy.get("migration_candidates_enabled") is not True:
            raise MigrationError(
                "alternative-pod migration is retired; use current-production-pod residency"
            )
        result = initialize_state(args.current_pod_id, args.network_volume_id) if args.command == "initialize" else transition(_load_json(args.state), _load_json(args.event))
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise MigrationError("output already exists; migration states are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (MigrationError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
