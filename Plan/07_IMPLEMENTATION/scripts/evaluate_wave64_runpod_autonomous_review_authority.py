#!/usr/bin/env python3
"""Evaluate exact-scope reviewer authority without granting artifact promotion."""

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
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_review_authority_decision.schema.json"
ROLE_REGISTRY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json"
ZERO_HASH = "0" * 64
TRIAGE_ROLE = "W64-AQA-ROLE-FAST-TRIAGE"


class ReviewAuthorityError(ValueError):
    """Raised when reviewer evidence cannot be evaluated safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewAuthorityError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewAuthorityError(f"JSON root must be an object: {path}")
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewAuthorityError(f"invalid evaluated_at: {value}") from exc
    if parsed.tzinfo is None:
        raise ReviewAuthorityError("evaluated_at must include timezone")
    return parsed.astimezone(timezone.utc)


def _verify_sealed(value: dict[str, Any], field: str) -> bool:
    observed = value[field]
    candidate = dict(value)
    candidate[field] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(candidate)).hexdigest() == observed


def _scope_covers(certificate: dict[str, Any], contract: dict[str, Any]) -> bool:
    scope = certificate["scope"]
    if contract["modality"] not in scope["modalities"]:
        return False
    image_spec = contract.get("image_spec", {})
    video_spec = contract.get("video_spec", {})
    audio_spec = contract.get("audio_spec", {})
    width = max(int(image_spec.get("width", 0)), int(video_spec.get("width", 0)))
    height = max(int(image_spec.get("height", 0)), int(video_spec.get("height", 0)))
    duration = max(float(video_spec.get("duration_seconds", 0)), float(audio_spec.get("duration_seconds", 0)))
    return width <= scope["max_width"] and height <= scope["max_height"] and duration <= scope["max_duration_seconds"]


def evaluate_authority(
    contract: dict[str, Any], observations: list[dict[str, Any]],
    certificates: list[dict[str, Any]], evaluated_at: str,
) -> dict[str, Any]:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1" or contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise ReviewAuthorityError("review authority requires a ready W64-AQA contract")
    when = _parse_time(evaluated_at)
    role_registry = {entry["role_id"]: entry for entry in _load_json(ROLE_REGISTRY_PATH)["roles"]}
    required = set(contract["quality_profile"]["required_approval_roles"])
    role_contract = {entry["role_id"]: entry for entry in contract["quality_profile"]["review_roles"]}
    if not required.issubset(role_contract):
        raise ReviewAuthorityError("required approval role is absent from review_roles")
    if any(not role_contract[role]["can_approve"] for role in required):
        raise ReviewAuthorityError("required approval role lacks contract approval authority")
    if TRIAGE_ROLE in required:
        raise ReviewAuthorityError("triage can never be a required approval role")
    certificates_by_id: dict[str, dict[str, Any]] = {}
    for certificate in certificates:
        try:
            jsonschema.Draft7Validator(_load_json(CERTIFICATE_SCHEMA_PATH)).validate(certificate)
        except jsonschema.ValidationError as exc:
            raise ReviewAuthorityError(f"certificate schema failed: {exc.message}") from exc
        if not _verify_sealed(certificate, "certificate_id"):
            raise ReviewAuthorityError("certificate content hash is invalid")
        if certificate["certificate_id"] in certificates_by_id:
            raise ReviewAuthorityError("duplicate certificate ID")
        certificates_by_id[certificate["certificate_id"]] = certificate
    observations_by_role: dict[str, dict[str, Any]] = {}
    triage_results: list[dict[str, Any]] = []
    for observation in observations:
        try:
            jsonschema.Draft7Validator(_load_json(OBSERVATION_SCHEMA_PATH)).validate(observation)
        except jsonschema.ValidationError as exc:
            raise ReviewAuthorityError(f"observation schema failed: {exc.message}") from exc
        if not _verify_sealed(observation, "observation_id"):
            raise ReviewAuthorityError("observation content hash is invalid")
        if observation["job_id"] != contract["job_id"] or observation["contract_id"] != contract["contract_id"]:
            raise ReviewAuthorityError("observation identity does not bind contract and job")
        role_id = observation["role_id"]
        if role_id == TRIAGE_ROLE:
            reasons = ["TRIAGE_EVIDENCE_ONLY_NEVER_PRODUCT_AUTHORITY"]
            status = "IGNORED_TRIAGE_ONLY"
            if observation["product_authority_claimed"]:
                reasons.append("TRIAGE_PRODUCT_AUTHORITY_CLAIM_DENIED")
                status = "BLOCKED"
            triage_results.append({
                "role_id": role_id, "required": False, "observation_id": observation["observation_id"],
                "certificate_id": observation["qualification_certificate_id"], "status": status,
                "reason_codes": sorted(reasons),
            })
            continue
        if role_id in observations_by_role:
            raise ReviewAuthorityError(f"duplicate observation for role {role_id}")
        observations_by_role[role_id] = observation

    role_results: list[dict[str, Any]] = []
    overall_reasons: set[str] = set()
    for role_id in sorted(required):
        observation = observations_by_role.get(role_id)
        reasons: set[str] = set()
        certificate_id = observation.get("qualification_certificate_id") if observation else None
        certificate = certificates_by_id.get(certificate_id) if certificate_id else None
        status = "BLOCKED"
        if observation is None:
            reasons.add("REQUIRED_OBSERVATION_MISSING")
        elif not observation["structured_response_valid"]:
            reasons.add("STRUCTURED_RESPONSE_INVALID")
        elif certificate is None:
            reasons.add("QUALIFICATION_CERTIFICATE_MISSING")
        else:
            if certificate["qualification_disposition"] != "QUALIFIED_FOR_DECLARED_SCOPE" or not certificate["operational_authority_granted"]:
                reasons.add("CERTIFICATE_NOT_OPERATIONAL")
            if when >= _parse_time(certificate["expires_at"]):
                reasons.add("CERTIFICATE_EXPIRED")
            fingerprint_matches = (
                certificate["role_id"] == role_id
                and certificate["model_id"] == observation["model_id"]
                and certificate["checkpoint_sha256"] == observation["checkpoint_sha256"]
                and certificate["runtime_digest"] == observation["runtime_digest"]
                and certificate["prompt_sha256"] == observation["prompt_sha256"]
            )
            if not fingerprint_matches:
                reasons.add("OBSERVATION_CERTIFICATE_FINGERPRINT_MISMATCH")
            if not _scope_covers(certificate, contract):
                reasons.add("CERTIFICATE_SCOPE_INSUFFICIENT")
            if role_id not in role_registry:
                reasons.add("ROLE_NOT_REGISTERED")
            if not reasons:
                if observation["decision"] == "PASS":
                    status, reasons = "PASS", {"QUALIFIED_REQUIRED_AUTHORITY_PASS"}
                elif observation["decision"] == "FAIL":
                    status, reasons = "FAIL", {"QUALIFIED_REQUIRED_AUTHORITY_FAIL"}
                else:
                    reasons.add("REQUIRED_AUTHORITY_ABSTAINED")
        role_results.append({
            "role_id": role_id, "required": True,
            "observation_id": observation["observation_id"] if observation else None,
            "certificate_id": certificate_id, "status": status, "reason_codes": sorted(reasons),
        })
    role_results.extend(triage_results)
    required_statuses = [entry["status"] for entry in role_results if entry["required"]]
    if any(entry["status"] == "BLOCKED" and "TRIAGE_PRODUCT_AUTHORITY_CLAIM_DENIED" in entry["reason_codes"] for entry in triage_results):
        disposition = "BLOCKED_REQUIRED_AUTHORITY"
        overall_reasons.add("TRIAGE_AUTHORITY_ESCALATION_ATTEMPT_BLOCKED")
    elif "BLOCKED" in required_statuses:
        disposition = "BLOCKED_REQUIRED_AUTHORITY"
        overall_reasons.add("ONE_OR_MORE_REQUIRED_AUTHORITIES_UNAVAILABLE_OR_INVALID")
    elif "FAIL" in required_statuses:
        disposition = "FAIL_REQUIRED_AUTHORITY"
        overall_reasons.add("ONE_OR_MORE_REQUIRED_AUTHORITIES_REJECTED")
    else:
        disposition = "PASS_REQUIRED_AUTHORITIES"
        overall_reasons.add("ALL_REQUIRED_QUALIFIED_AUTHORITIES_PASS")
    evidence_only = contract.get("promotion_disposition") == "EVIDENCE_ONLY"
    if evidence_only:
        overall_reasons.add("SHADOW_EVIDENCE_ONLY_NO_PRODUCT_PROMOTION")
    decision = {
        "schema_version": "wave64.aqa.review_authority_decision.v1", "decision_id": ZERO_HASH,
        "job_id": contract["job_id"], "contract_id": contract["contract_id"],
        "evaluated_at": evaluated_at, "required_roles": sorted(required),
        "role_results": role_results, "review_disposition": disposition,
        "evidence_only": evidence_only, "promotion_authorized": False,
        "reason_codes": sorted(overall_reasons),
    }
    decision["decision_id"] = hashlib.sha256(canonical_bytes(decision)).hexdigest()
    jsonschema.Draft7Validator(_load_json(DECISION_SCHEMA_PATH), format_checker=jsonschema.FormatChecker()).validate(decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("certificates", type=Path)
    parser.add_argument("evaluated_at")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        observations = json.loads(args.observations.read_text(encoding="utf-8"))
        certificates = json.loads(args.certificates.read_text(encoding="utf-8"))
        if not isinstance(observations, list) or not isinstance(certificates, list):
            raise ReviewAuthorityError("observations and certificates must be JSON arrays")
        result = evaluate_authority(_load_json(args.contract), observations, certificates, args.evaluated_at)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise ReviewAuthorityError("output already exists; authority decisions are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (ReviewAuthorityError, json.JSONDecodeError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
