#!/usr/bin/env python3
"""Resolve independently qualified reviewer agreement without averaging or promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
OBSERVATION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_reviewer_observation.schema.json"
CERTIFICATE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_certificate.schema.json"
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_review_disagreement_decision.schema.json"
ZERO_HASH = "0" * 64
PRIMARY_ROLE = "W64-AQA-ROLE-PRIMARY-VISUAL"
JUROR_ROLE = "W64-AQA-ROLE-INDEPENDENT-JUROR"
ARBITER_ROLE = "W64-AQA-ROLE-SENIOR-ARBITER"


class DisagreementError(ValueError):
    """Raised when disagreement evidence is not independently trustworthy."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DisagreementError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DisagreementError(f"JSON root must be an object: {path}")
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DisagreementError(f"invalid evaluated_at: {value}") from exc
    if parsed.tzinfo is None:
        raise DisagreementError("evaluated_at must include timezone")
    return parsed.astimezone(timezone.utc)


def _sealed(value: dict[str, Any], field: str) -> bool:
    observed = value[field]
    candidate = dict(value)
    candidate[field] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(candidate)).hexdigest() == observed


def _validated_pair(
    observation: dict[str, Any], certificate: dict[str, Any], expected_role: str,
    contract: dict[str, Any], evaluated_at: datetime,
) -> None:
    try:
        jsonschema.Draft7Validator(_load_json(OBSERVATION_SCHEMA_PATH)).validate(observation)
        jsonschema.Draft7Validator(_load_json(CERTIFICATE_SCHEMA_PATH)).validate(certificate)
    except jsonschema.ValidationError as exc:
        raise DisagreementError(f"observation or certificate schema failed: {exc.message}") from exc
    if not _sealed(observation, "observation_id") or not _sealed(certificate, "certificate_id"):
        raise DisagreementError("observation or certificate content hash is invalid")
    if observation["role_id"] != expected_role or certificate["role_id"] != expected_role:
        raise DisagreementError(f"evidence does not bind expected role {expected_role}")
    if observation["job_id"] != contract["job_id"] or observation["contract_id"] != contract["contract_id"]:
        raise DisagreementError("observation does not bind contract and job")
    if observation["qualification_certificate_id"] != certificate["certificate_id"]:
        raise DisagreementError("observation does not bind supplied certificate")
    for field in ("model_id", "checkpoint_sha256", "runtime_digest", "prompt_sha256"):
        if observation[field] != certificate[field]:
            raise DisagreementError(f"observation/certificate {field} mismatch")
    if certificate["qualification_disposition"] != "QUALIFIED_FOR_DECLARED_SCOPE" or not certificate["operational_authority_granted"]:
        raise DisagreementError("certificate is not qualified and operational for scope")
    if evaluated_at >= _parse_time(certificate["expires_at"]):
        raise DisagreementError("certificate is expired")
    if not observation["structured_response_valid"]:
        raise DisagreementError("reviewer structured response is invalid")


def resolve_disagreement(
    contract: dict[str, Any], primary_observation: dict[str, Any], primary_certificate: dict[str, Any],
    juror_observation: dict[str, Any], juror_certificate: dict[str, Any],
    deterministic_hard_gates_pass: bool, evaluated_at: str,
    arbiter_observation: dict[str, Any] | None = None,
    arbiter_certificate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1" or contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise DisagreementError("disagreement resolution requires a ready W64-AQA contract")
    when = _parse_time(evaluated_at)
    _validated_pair(primary_observation, primary_certificate, PRIMARY_ROLE, contract, when)
    _validated_pair(juror_observation, juror_certificate, JUROR_ROLE, contract, when)
    independence = all(
        primary_certificate[field] != juror_certificate[field]
        for field in ("model_id", "checkpoint_sha256", "runtime_digest", "prompt_sha256")
    )
    reasons: set[str] = set()
    arbiter_id = None
    if not independence:
        disposition, product_decision = "BLOCKED_INDEPENDENCE", "BLOCKED"
        reasons.add("PRIMARY_AND_JUROR_INDEPENDENCE_NOT_PROVEN")
    elif not deterministic_hard_gates_pass:
        disposition, product_decision = "HARD_GATE_FAIL", "FAIL"
        reasons.add("DETERMINISTIC_HARD_GATE_FAILURE_CANNOT_BE_OVERRIDDEN")
    elif "ABSTAIN" in {primary_observation["decision"], juror_observation["decision"]}:
        disposition, product_decision = "BLOCKED_ABSTENTION", "BLOCKED"
        reasons.add("PRIMARY_OR_JUROR_ABSTAINED")
    elif primary_observation["decision"] == juror_observation["decision"]:
        if primary_observation["decision"] == "PASS":
            disposition, product_decision = "CONSENSUS_PASS", "PASS"
            reasons.add("INDEPENDENT_PRIMARY_AND_JUROR_CONSENSUS_PASS")
        else:
            disposition, product_decision = "CONSENSUS_FAIL", "FAIL"
            reasons.add("INDEPENDENT_PRIMARY_AND_JUROR_CONSENSUS_FAIL")
    else:
        if (arbiter_observation is None) != (arbiter_certificate is None):
            raise DisagreementError("arbiter observation and certificate must be supplied together")
        if arbiter_observation is None or arbiter_certificate is None:
            disposition, product_decision = "BLOCKED_ARBITRATION_REQUIRED", "BLOCKED"
            reasons.add("PRIMARY_JUROR_DISAGREEMENT_REQUIRES_QUALIFIED_ARBITER")
        else:
            _validated_pair(arbiter_observation, arbiter_certificate, ARBITER_ROLE, contract, when)
            arbiter_id = arbiter_observation["observation_id"]
            if arbiter_observation["decision"] == "ABSTAIN":
                disposition, product_decision = "BLOCKED_ARBITRATION_REQUIRED", "BLOCKED"
                reasons.add("QUALIFIED_ARBITER_ABSTAINED")
            elif arbiter_observation["decision"] == "PASS":
                disposition, product_decision = "ARBITRATED_PASS", "PASS"
                reasons.add("QUALIFIED_SENIOR_ARBITER_SELECTED_PASS")
            else:
                disposition, product_decision = "ARBITRATED_FAIL", "FAIL"
                reasons.add("QUALIFIED_SENIOR_ARBITER_SELECTED_FAIL")
    decision = {
        "schema_version": "wave64.aqa.review_disagreement_decision.v1", "decision_id": ZERO_HASH,
        "job_id": contract["job_id"], "contract_id": contract["contract_id"],
        "evaluated_at": evaluated_at, "primary_observation_id": primary_observation["observation_id"],
        "juror_observation_id": juror_observation["observation_id"], "arbiter_observation_id": arbiter_id,
        "independence_verified": independence, "deterministic_hard_gates_pass": deterministic_hard_gates_pass,
        "disposition": disposition, "product_decision": product_decision,
        "promotion_authorized": False, "reason_codes": sorted(reasons),
    }
    decision["decision_id"] = hashlib.sha256(canonical_bytes(decision)).hexdigest()
    jsonschema.Draft7Validator(_load_json(DECISION_SCHEMA_PATH), format_checker=jsonschema.FormatChecker()).validate(decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("primary_observation", type=Path)
    parser.add_argument("primary_certificate", type=Path)
    parser.add_argument("juror_observation", type=Path)
    parser.add_argument("juror_certificate", type=Path)
    parser.add_argument("hard_gates_pass", choices=["true", "false"])
    parser.add_argument("evaluated_at")
    parser.add_argument("--arbiter-observation", type=Path)
    parser.add_argument("--arbiter-certificate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = resolve_disagreement(
            _load_json(args.contract), _load_json(args.primary_observation), _load_json(args.primary_certificate),
            _load_json(args.juror_observation), _load_json(args.juror_certificate),
            args.hard_gates_pass == "true", args.evaluated_at,
            _load_json(args.arbiter_observation) if args.arbiter_observation else None,
            _load_json(args.arbiter_certificate) if args.arbiter_certificate else None,
        )
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise DisagreementError("output already exists; disagreement decisions are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (DisagreementError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
