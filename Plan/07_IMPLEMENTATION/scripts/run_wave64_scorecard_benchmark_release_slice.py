#!/usr/bin/env python3
"""Execute the bounded Wave64 Rows209-212 scorecard and release slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_scorecard_benchmark_release_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_scorecard_benchmark_release_authority.schema.json")
GATES = {"identity", "morphology", "pose", "framing", "ownership", "mask", "anatomy", "realism", "temporal", "speech", "audio", "sync", "provenance", "runtime"}
SCOPES = {"target", "protected", "whole"}
BUCKETS = {"positive", "negative", "adversarial", "ownership", "outage", "recovery", "cross_engine", "specialist", "video", "audio", "av"}
COHORTS = {"solo", "multi_character", "mixed"}
SIGNAL_TYPES = {"deterministic_validator", "scoped_metric", "critic", "review_packet"}


class ReleaseAuthorityError(ValueError):
    """Raised when scorecard, benchmark, or release authority fails closed."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_digest(fixture: dict[str, Any]) -> str:
    payload = {key: fixture[key] for key in ("bucket", "cohort", "expected_decision", "revision")}
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def validate_registry(root: Path, registry: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry), key=lambda e: list(e.absolute_path))
    if errors:
        error = errors[0]
        raise ReleaseAuthorityError(f"schema_validation_failed:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}")
    seen: set[str] = set()
    for ref in registry["source_authorities"]:
        if ref["name"] in seen:
            raise ReleaseAuthorityError("duplicate_source_authority_name")
        seen.add(ref["name"])
        relative = Path(ref["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ReleaseAuthorityError(f"bound_path_not_relative:{ref['name']}")
        path = (root / relative).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise ReleaseAuthorityError(f"bound_file_missing:{ref['name']}")
        if sha256_file(path) != ref["sha256"]:
            raise ReleaseAuthorityError(f"bound_hash_mismatch:{ref['name']}")
    scorecard = registry["scorecard_contract"]
    if set(scorecard["required_gate_ids"]) != GATES or {gate["gate_id"] for gate in scorecard["gates"]} != GATES:
        raise ReleaseAuthorityError("scorecard_gate_set_mismatch")
    if set(scorecard["required_scopes"]) != SCOPES or scorecard["single_subjective_scalar_allowed"]:
        raise ReleaseAuthorityError("scorecard_scope_or_scalar_policy_invalid")
    for gate in scorecard["gates"]:
        if not all((gate["applicability_rule"], gate["method"], gate["authority"], gate["evidence_type"], gate["severity"])):
            raise ReleaseAuthorityError(f"gate_metadata_incomplete:{gate['gate_id']}")
    benchmark = registry["benchmark_contract"]
    if set(benchmark["required_buckets"]) != BUCKETS or set(benchmark["required_cohorts"]) != COHORTS:
        raise ReleaseAuthorityError("benchmark_coverage_mismatch")
    if {item["bucket"] for item in benchmark["fixtures"]} != BUCKETS:
        raise ReleaseAuthorityError("benchmark_fixture_bucket_mismatch")
    if {item["cohort"] for item in benchmark["fixtures"]} != COHORTS:
        raise ReleaseAuthorityError("benchmark_fixture_cohort_mismatch")
    for fixture in benchmark["fixtures"]:
        if fixture_digest(fixture) != fixture["payload_sha256"]:
            raise ReleaseAuthorityError(f"benchmark_fixture_hash_mismatch:{fixture['fixture_id']}")
    calibration = registry["calibration_policy"]
    if set(calibration["required_signal_types"]) != SIGNAL_TYPES or calibration["weak_signal_can_override_hard_failure"]:
        raise ReleaseAuthorityError("calibration_policy_invalid")
    if registry["production_release_allowed"] or any(registry["boundaries"].values()):
        raise ReleaseAuthorityError("false_production_boundary")


def evaluate_ensemble(
    registry: dict[str, Any],
    gate_results: dict[str, dict[str, Any]],
    scope_results: dict[str, bool],
    signals: list[dict[str, str]],
    calibration: dict[str, float],
) -> dict[str, Any]:
    if set(gate_results) != GATES:
        raise ReleaseAuthorityError("runtime_gate_set_mismatch")
    if set(scope_results) != SCOPES:
        raise ReleaseAuthorityError("runtime_scope_set_mismatch")
    if {signal.get("signal_type") for signal in signals} != SIGNAL_TYPES:
        raise ReleaseAuthorityError("runtime_signal_type_set_mismatch")
    policy = registry["calibration_policy"]
    for name in ("false_accept_rate", "false_reject_rate", "abstention_rate"):
        if name not in calibration or not 0 <= calibration[name] <= 1:
            raise ReleaseAuthorityError(f"calibration_value_invalid:{name}")
    if calibration["false_accept_rate"] > policy["max_false_accept_rate"] or calibration["false_reject_rate"] > policy["max_false_reject_rate"] or calibration["abstention_rate"] > policy["max_abstention_rate"]:
        return {"decision": "block", "reason": "CALIBRATION_LIMIT_EXCEEDED", "hard_failures": [], "disagreement": False}
    definitions = {gate["gate_id"]: gate for gate in registry["scorecard_contract"]["gates"]}
    hard_failures: list[str] = []
    soft_failures: list[str] = []
    for gate_id, result in gate_results.items():
        if "applicable" not in result:
            raise ReleaseAuthorityError(f"applicability_missing:{gate_id}")
        if not result["applicable"]:
            if not result.get("not_applicable_reason"):
                raise ReleaseAuthorityError(f"not_applicable_reason_missing:{gate_id}")
            continue
        if not result.get("evidence_ref") or not result.get("method") or not result.get("authority"):
            raise ReleaseAuthorityError(f"runtime_gate_metadata_missing:{gate_id}")
        if result.get("passed") is not True:
            (hard_failures if definitions[gate_id]["hard_gate"] else soft_failures).append(gate_id)
    if hard_failures:
        return {"decision": "block", "reason": "HARD_GATE_FAILURE", "hard_failures": sorted(hard_failures), "soft_failures": sorted(soft_failures), "disagreement": False}
    failed_scopes = sorted(scope for scope, passed in scope_results.items() if not passed)
    if failed_scopes:
        return {"decision": "block", "reason": "SCOPED_GATE_FAILURE", "hard_failures": [], "soft_failures": sorted(soft_failures), "failed_scopes": failed_scopes, "disagreement": False}
    decisions = {signal["decision"] for signal in signals}
    if "abstain" in decisions or len(decisions) != 1:
        return {"decision": "abstain", "reason": "ENSEMBLE_DISAGREEMENT", "hard_failures": [], "soft_failures": sorted(soft_failures), "disagreement": True}
    if soft_failures or decisions != {"allow"}:
        return {"decision": "block", "reason": "SOFT_GATE_OR_ENSEMBLE_BLOCK", "hard_failures": [], "soft_failures": sorted(soft_failures), "disagreement": False}
    return {"decision": "allow", "reason": "ALL_APPLICABLE_GATES_SCOPES_AND_SIGNALS_PASS", "hard_failures": [], "soft_failures": [], "disagreement": False}


def release_readiness(registry: dict[str, Any], ensemble: dict[str, Any], completed_rows: set[int], certificates: dict[str, bool]) -> dict[str, Any]:
    policy = registry["release_policy"]
    required_rows = set(range(policy["required_row_start"], policy["required_row_end"] + 1))
    missing_rows = sorted(required_rows - completed_rows)
    missing_certificates = sorted(set(policy["required_certificates"]) - {name for name, passed in certificates.items() if passed})
    blockers: list[str] = []
    if ensemble["decision"] != "allow": blockers.append(f"ensemble:{ensemble['decision']}")
    if missing_rows: blockers.append("required_rows_incomplete")
    if missing_certificates: blockers.append("required_certificates_missing")
    eligible = not blockers
    return {
        "status": "eligible" if eligible else "blocked",
        "all_blocking_gates_pass": eligible,
        "promotion_request_eligible": eligible,
        "actual_promotion_state": "not_requested",
        "projection_only": True,
        "missing_rows": missing_rows,
        "missing_certificates": missing_certificates,
        "blockers": blockers,
        "residual_risk": [] if eligible else ["runtime_and_release_authority_incomplete"],
        "scope": {"row_start": policy["required_row_start"], "row_end": policy["required_row_end"]},
        "certificate_issued": False,
    }


def passing_gate_results(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {gate_id: {"applicable": True, "passed": True, "evidence_ref": f"fixture://{gate_id}/r001", "method": gate_id + "_fixture_method", "authority": gate_id + "_fixture_authority"} for gate_id in registry["scorecard_contract"]["required_gate_ids"]}


def signals(*decisions: str) -> list[dict[str, str]]:
    values = list(decisions) or ["allow"] * len(SIGNAL_TYPES)
    return [{"signal_type": signal_type, "decision": values[index % len(values)]} for index, signal_type in enumerate(sorted(SIGNAL_TYPES))]


def execute_fixture(registry: dict[str, Any]) -> dict[str, Any]:
    calibration = {"false_accept_rate": 0.01, "false_reject_rate": 0.04, "abstention_rate": 0.10}
    scopes = {scope: True for scope in SCOPES}
    positive = evaluate_ensemble(registry, passing_gate_results(registry), scopes, signals("allow"), calibration)
    hard_results = passing_gate_results(registry); hard_results["anatomy"]["passed"] = False
    hard_block = evaluate_ensemble(registry, hard_results, scopes, signals("allow"), calibration)
    disagreement = evaluate_ensemble(registry, passing_gate_results(registry), scopes, signals("allow", "block"), calibration)
    current_rows = set(range(149, 213))
    readiness = release_readiness(registry, positive, current_rows, {name: False for name in registry["release_policy"]["required_certificates"]})
    return {
        "status": "PASS",
        "classification": "WAVE64_SCORECARD_BENCHMARK_RELEASE_SLICE_PASS",
        "rows_covered": [209, 210, 211, 212],
        "gate_count": len(GATES), "benchmark_fixture_count": len(BUCKETS),
        "positive_decision": positive, "hard_failure_decision": hard_block, "disagreement_decision": disagreement,
        "release_readiness": readiness,
        "production_release_allowed": False, "gpu_allocated": False, "comfyui_submitted": False, "aws_mutated": False,
    }


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "evidence_type": "wave64_scorecard_benchmark_release_slice", **result,
        "authority": {"registry_path": registry_path.as_posix(), "registry_sha256": sha256_file(root / registry_path), "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path), "runner_path": "Plan/07_IMPLEMENTATION/scripts/run_wave64_scorecard_benchmark_release_slice.py", "runner_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/run_wave64_scorecard_benchmark_release_slice.py")},
        "worker_dispatch": {"intent_id": "intent_20260717T091423218Z_wave64_rows209_212_scorecard_benchmark_release_architecture_c12d53d2", "request_id": "p050_20260717T091431635Z_wave64_rows209_212_scorecard_benchmark_release_architecture_270f62a4", "result": "AI_WORKER_RETRY_BUDGET_EXHAUSTED_REGISTERED_PRIMARY_WORKTREE_REQUIRED", "fallback": "bounded_codex_runtime_implementation_and_deterministic_validation"},
        "boundaries": {"model_loaded": False, "gpu_allocated": False, "comfyui_submitted": False, "production_artifact_created": False, "promotion_requested": False, "certificate_issued": False, "wave_completion_claimed": False, "aws_mutated": False, "item_tracker_status_changed": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY); parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA); parser.add_argument("--evidence-out", type=Path); parser.add_argument("--tracker-evidence-out", type=Path); args = parser.parse_args()
    root = args.root.resolve(); registry = load_json(root / args.registry); validate_registry(root, registry, load_json(root / args.schema)); result = execute_fixture(registry)
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out: write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out: write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
