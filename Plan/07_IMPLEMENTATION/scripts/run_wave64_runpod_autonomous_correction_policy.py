#!/usr/bin/env python3
"""Apply immutable compare-improve-or-revert transitions for W64-AQA corrections."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
ATTEMPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_correction_attempt.schema.json"
STATE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_correction_state.schema.json"
ZERO_HASH = "0" * 64
SCORE_EPSILON = 1e-9
GLOBAL_MAX_REPAIRS_PER_DEFECT = 2
GLOBAL_MAX_TOTAL_GENERATIONS = 4
GLOBAL_MAX_NO_PROGRESS = 2


class CorrectionPolicyError(ValueError):
    """Raised when a correction state or transition cannot be trusted."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorrectionPolicyError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CorrectionPolicyError(f"JSON root must be an object: {path}")
    return value


def _schema(path: Path) -> dict[str, Any]:
    return _load_json(path)


def _seal(state: dict[str, Any]) -> dict[str, Any]:
    state["state_id"] = ZERO_HASH
    state["state_id"] = hashlib.sha256(canonical_bytes(state)).hexdigest()
    jsonschema.Draft7Validator(_schema(STATE_SCHEMA_PATH)).validate(state)
    return state


def _validate_policy(contract: dict[str, Any]) -> dict[str, int]:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1":
        raise CorrectionPolicyError("unsupported contract schema_version")
    policy = contract.get("attempt_policy")
    if not isinstance(policy, dict):
        raise CorrectionPolicyError("contract lacks attempt_policy")
    expected = {
        "max_repairs_per_defect": GLOBAL_MAX_REPAIRS_PER_DEFECT,
        "max_total_generations": GLOBAL_MAX_TOTAL_GENERATIONS,
        "max_no_progress_cycles": GLOBAL_MAX_NO_PROGRESS,
    }
    parsed: dict[str, int] = {}
    for key, global_maximum in expected.items():
        value = policy.get(key)
        minimum = 1 if key == "max_total_generations" else 0
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum or value > global_maximum:
            raise CorrectionPolicyError(f"attempt policy {key} must be between {minimum} and {global_maximum}")
        parsed[key] = value
    return parsed


def initialize_state(
    contract: dict[str, Any], job_id: str, accepted_artifact_sha256: str,
    accepted_total_score: float, accepted_protected_scores: dict[str, float],
) -> dict[str, Any]:
    _validate_policy(contract)
    if not isinstance(job_id, str) or not job_id.startswith("W64-AQA-JOB-"):
        raise CorrectionPolicyError("job_id is invalid")
    if not isinstance(accepted_artifact_sha256, str) or len(accepted_artifact_sha256) != 64:
        raise CorrectionPolicyError("accepted artifact hash is invalid")
    if not isinstance(accepted_total_score, (int, float)) or not math.isfinite(float(accepted_total_score)) or not 0 <= accepted_total_score <= 1:
        raise CorrectionPolicyError("accepted total score is invalid")
    if not accepted_protected_scores or any(
        not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0 <= value <= 1
        for value in accepted_protected_scores.values()
    ):
        raise CorrectionPolicyError("accepted protected scores are invalid")
    state = {
        "schema_version": "wave64.aqa.correction_state.v1",
        "state_id": ZERO_HASH,
        "previous_state_id": None,
        "sequence": 0,
        "job_id": job_id,
        "contract_id": contract["contract_id"],
        "accepted_artifact_sha256": accepted_artifact_sha256,
        "accepted_total_score": float(accepted_total_score),
        "accepted_protected_scores": {key: float(value) for key, value in accepted_protected_scores.items()},
        "total_generation_attempts": 1,
        "repairs_by_defect": {},
        "consecutive_no_progress": 0,
        "last_attempt_id": None,
        "last_candidate_artifact_sha256": None,
        "last_evidence_sha256": [],
        "disposition": "BASELINE_ACCEPTED",
        "terminal": False,
        "promotion_authorized": False,
        "reason_codes": ["IMMUTABLE_BASELINE_CAPTURED"],
    }
    return _seal(state)


def transition(state: dict[str, Any], attempt: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    policy = _validate_policy(contract)
    try:
        jsonschema.Draft7Validator(_schema(STATE_SCHEMA_PATH)).validate(state)
        jsonschema.Draft7Validator(_schema(ATTEMPT_SCHEMA_PATH)).validate(attempt)
    except jsonschema.ValidationError as exc:
        raise CorrectionPolicyError(f"state or attempt schema validation failed: {exc.message}") from exc
    expected_state_id = state["state_id"]
    unsealed = dict(state)
    unsealed["state_id"] = ZERO_HASH
    if hashlib.sha256(canonical_bytes(unsealed)).hexdigest() != expected_state_id:
        raise CorrectionPolicyError("state hash chain validation failed")
    if state["terminal"]:
        raise CorrectionPolicyError("terminal correction state cannot accept another attempt")
    if state["contract_id"] != contract.get("contract_id") or attempt["contract_id"] != state["contract_id"]:
        raise CorrectionPolicyError("contract identity mismatch")
    if attempt["job_id"] != state["job_id"]:
        raise CorrectionPolicyError("job identity mismatch")
    if attempt["parent_artifact_sha256"] != state["accepted_artifact_sha256"]:
        raise CorrectionPolicyError("attempt parent does not match accepted rollback parent")
    if attempt["candidate_artifact_sha256"] == state["accepted_artifact_sha256"]:
        raise CorrectionPolicyError("candidate artifact must differ from accepted parent")
    if set(attempt["candidate_protected_scores"]) != set(state["accepted_protected_scores"]):
        raise CorrectionPolicyError("protected score categories must have exact parity")

    previous_repairs = state["repairs_by_defect"].get(attempt["defect_id"], 0)
    if previous_repairs >= policy["max_repairs_per_defect"]:
        raise CorrectionPolicyError("repair attempt submitted after per-defect ceiling")
    new_repair_count = previous_repairs + 1
    total_generations = state["total_generation_attempts"] + int(attempt["generation_consumed"])
    if total_generations > policy["max_total_generations"]:
        raise CorrectionPolicyError("generation attempt submitted after total ceiling")
    improved = attempt["candidate_total_score"] > state["accepted_total_score"] + SCORE_EPSILON
    regressions = sorted(
        key for key, baseline in state["accepted_protected_scores"].items()
        if attempt["candidate_protected_scores"][key] + SCORE_EPSILON < baseline
    )
    retain = attempt["hard_gates_pass"] and improved and not regressions
    repairs = dict(state["repairs_by_defect"])
    repairs[attempt["defect_id"]] = new_repair_count
    reasons: set[str] = set()
    if not attempt["hard_gates_pass"]:
        reasons.add("HARD_GATES_FAILED")
    if not improved:
        reasons.add("TOTAL_SCORE_DID_NOT_IMPROVE")
    if regressions:
        reasons.add("PROTECTED_CATEGORY_REGRESSION")

    if retain:
        disposition, terminal, no_progress = "RETAIN_CANDIDATE_EXIT_REPAIR_LOOP", True, 0
        accepted_hash = attempt["candidate_artifact_sha256"]
        accepted_score = float(attempt["candidate_total_score"])
        accepted_protected = {key: float(value) for key, value in attempt["candidate_protected_scores"].items()}
        reasons.add("HARD_GATES_PASS_SCORE_IMPROVED_NO_PROTECTED_REGRESSION")
    else:
        no_progress = state["consecutive_no_progress"] + 1
        exhausted_reasons = set()
        if new_repair_count >= policy["max_repairs_per_defect"]:
            exhausted_reasons.add("PER_DEFECT_REPAIR_CEILING_REACHED")
        if total_generations >= policy["max_total_generations"]:
            exhausted_reasons.add("TOTAL_GENERATION_CEILING_REACHED")
        if no_progress >= policy["max_no_progress_cycles"]:
            exhausted_reasons.add("NO_PROGRESS_CEILING_REACHED")
        terminal = bool(exhausted_reasons)
        disposition = "EXHAUSTED_BLOCKED" if terminal else "REVERT_CANDIDATE_CONTINUE"
        reasons.update(exhausted_reasons)
        reasons.add("CANDIDATE_REVERTED_TO_ACCEPTED_PARENT")
        accepted_hash = state["accepted_artifact_sha256"]
        accepted_score = state["accepted_total_score"]
        accepted_protected = state["accepted_protected_scores"]

    next_state = {
        "schema_version": "wave64.aqa.correction_state.v1",
        "state_id": ZERO_HASH,
        "previous_state_id": state["state_id"],
        "sequence": state["sequence"] + 1,
        "job_id": state["job_id"],
        "contract_id": state["contract_id"],
        "accepted_artifact_sha256": accepted_hash,
        "accepted_total_score": accepted_score,
        "accepted_protected_scores": accepted_protected,
        "total_generation_attempts": total_generations,
        "repairs_by_defect": repairs,
        "consecutive_no_progress": no_progress,
        "last_attempt_id": attempt["attempt_id"],
        "last_candidate_artifact_sha256": attempt["candidate_artifact_sha256"],
        "last_evidence_sha256": attempt["evidence_sha256"],
        "disposition": disposition,
        "terminal": terminal,
        "promotion_authorized": False,
        "reason_codes": sorted(reasons),
    }
    return _seal(next_state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("contract", type=Path)
    initialize.add_argument("job_id")
    initialize.add_argument("artifact_sha256")
    initialize.add_argument("total_score", type=float)
    initialize.add_argument("protected_scores", type=Path)
    advance = subparsers.add_parser("transition")
    advance.add_argument("state", type=Path)
    advance.add_argument("attempt", type=Path)
    advance.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "initialize":
            result = initialize_state(
                _load_json(args.contract), args.job_id, args.artifact_sha256,
                args.total_score, _load_json(args.protected_scores),
            )
        else:
            result = transition(_load_json(args.state), _load_json(args.attempt), _load_json(args.contract))
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise CorrectionPolicyError("output already exists; correction states are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (CorrectionPolicyError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
