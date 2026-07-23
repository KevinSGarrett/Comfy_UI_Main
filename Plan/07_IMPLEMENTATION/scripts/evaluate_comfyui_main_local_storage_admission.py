#!/usr/bin/env python3
"""Fail-closed local storage admission for the RunPod-only Comfy_UI_Main control plane."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "Plan/10_REGISTRIES/comfyui_main_local_storage_admission_policy.json"
OPERATIONS = {
    "worker_worktree",
    "source_edit_test",
    "docker_start",
    "local_model_download",
    "local_runtime_artifact_materialization",
    "local_dataset_materialization",
}


class AdmissionError(ValueError):
    """The policy is invalid or cannot be evaluated safely."""


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != "comfyui.main.local_storage_admission_policy.v1":
        raise AdmissionError("local storage policy schema version mismatch")
    thresholds = policy.get("thresholds")
    operations = policy.get("operations")
    if not isinstance(thresholds, dict) or not isinstance(operations, dict):
        raise AdmissionError("local storage policy is missing thresholds or operations")
    required_thresholds = {
        "local_control_plane_min_free_bytes",
        "worker_worktree_min_free_before_bytes",
        "worker_worktree_min_free_after_bytes",
        "worker_worktree_default_projected_write_bytes",
        "local_control_plane_max_projected_write_bytes",
    }
    if set(thresholds) != required_thresholds:
        raise AdmissionError("local storage threshold set mismatch")
    if any(not isinstance(value, int) or value < 0 for value in thresholds.values()):
        raise AdmissionError("local storage thresholds must be non-negative integers")
    if set(operations) != OPERATIONS:
        raise AdmissionError("local storage operation set mismatch")
    return policy


def evaluate(
    policy: dict[str, Any],
    operation: str,
    observed_free_bytes: int,
    expected_write_bytes: int | None = None,
) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise AdmissionError(f"unsupported local storage operation: {operation}")
    if observed_free_bytes < 0:
        raise AdmissionError("observed free bytes must be non-negative")
    thresholds = policy["thresholds"]
    rule = policy["operations"][operation]
    if rule == "DENIED_RUNPOD_ONLY":
        projected = 0 if expected_write_bytes is None else expected_write_bytes
        return {
            "schema_version": "comfyui.main.local_storage_admission.v1",
            "policy_id": policy["policy_id"],
            "operation": operation,
            "status": "DENIED",
            "classification": "COMFYUI_LOCAL_STORAGE_DENIED_RUNPOD_ONLY",
            "observed_free_bytes": observed_free_bytes,
            "expected_write_bytes": projected,
            "projected_free_after_bytes": observed_free_bytes - projected,
            "reasons": ["OPERATION_FORBIDDEN_WHILE_RUNPOD_IS_SOLE_PRODUCTION_STORAGE"],
            "authority": {"local_write": False, "deletion": False, "runpod": False},
        }
    if rule != "THRESHOLD_GATED":
        raise AdmissionError(f"unsupported local storage rule: {rule}")

    if operation == "worker_worktree":
        projected = (
            thresholds["worker_worktree_default_projected_write_bytes"]
            if expected_write_bytes is None
            else expected_write_bytes
        )
        min_before = thresholds["worker_worktree_min_free_before_bytes"]
        min_after = thresholds["worker_worktree_min_free_after_bytes"]
        reasons = []
        if observed_free_bytes < min_before:
            reasons.append("FREE_SPACE_BELOW_WORKTREE_ADMISSION_FLOOR")
        if observed_free_bytes - projected < min_after:
            reasons.append("PROJECTED_FREE_SPACE_BELOW_WORKTREE_RESERVE")
    else:
        projected = 0 if expected_write_bytes is None else expected_write_bytes
        min_before = thresholds["local_control_plane_min_free_bytes"]
        min_after = min_before
        reasons = []
        if projected > thresholds["local_control_plane_max_projected_write_bytes"]:
            reasons.append("PROJECTED_LOCAL_CONTROL_PLANE_WRITE_EXCEEDS_LIMIT")
        if observed_free_bytes - projected < min_after:
            reasons.append("PROJECTED_FREE_SPACE_BELOW_LOCAL_CONTROL_PLANE_RESERVE")

    admitted = not reasons
    return {
        "schema_version": "comfyui.main.local_storage_admission.v1",
        "policy_id": policy["policy_id"],
        "operation": operation,
        "status": "ADMITTED" if admitted else "DENIED",
        "classification": (
            "COMFYUI_LOCAL_STORAGE_ADMISSION_PASS"
            if admitted
            else "COMFYUI_LOCAL_STORAGE_CAPACITY_DENIED"
        ),
        "observed_free_bytes": observed_free_bytes,
        "expected_write_bytes": projected,
        "projected_free_after_bytes": observed_free_bytes - projected,
        "minimum_free_before_bytes": min_before,
        "minimum_free_after_bytes": min_after,
        "reasons": reasons,
        "authority": {"local_write": admitted, "deletion": False, "runpod": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--operation", required=True, choices=sorted(OPERATIONS))
    parser.add_argument("--expected-write-bytes", type=int)
    parser.add_argument("--observed-free-bytes", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    policy = load_policy(args.policy)
    observed = (
        shutil.disk_usage(policy["storage_root"]).free
        if args.observed_free_bytes is None
        else args.observed_free_bytes
    )
    result = evaluate(policy, args.operation, observed, args.expected_write_bytes)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
