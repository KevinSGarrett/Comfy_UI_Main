#!/usr/bin/env python3
"""Compile scoped role certificates and suspend authority on any material drift."""

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
REPORT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_report.schema.json"
CERTIFICATE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_certificate.schema.json"
DRIFT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_role_drift_decision.schema.json"
ZERO_HASH = "0" * 64
REQUIRED_CATEGORIES = {"known_good", "known_bad", "borderline", "adversarial", "refusal", "identity", "temporal", "audio_mask", "workflow"}


class QualificationError(ValueError):
    """Raised when qualification evidence is malformed or non-replayable."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"JSON root must be an object: {path}")
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationError(f"invalid date-time: {value}") from exc
    if parsed.tzinfo is None:
        raise QualificationError("date-time must include a timezone")
    return parsed.astimezone(timezone.utc)


def compile_certificate(report: dict[str, Any]) -> dict[str, Any]:
    try:
        jsonschema.Draft7Validator(_load_json(REPORT_SCHEMA_PATH), format_checker=jsonschema.FormatChecker()).validate(report)
    except jsonschema.ValidationError as exc:
        raise QualificationError(f"qualification report schema failed: {exc.message}") from exc
    if _parse_time(report["expires_at"]) <= _parse_time(report["issued_at"]):
        raise QualificationError("qualification expiration must follow issuance")
    categories = {fixture["category"] for fixture in report["fixtures"]}
    run_count = false_accepts = false_rejects = invalid_schema = refusal_total = refusal_correct = 0
    repeatable = 0
    for fixture in report["fixtures"]:
        outcomes = set()
        for run in fixture["runs"]:
            run_count += 1
            outcomes.add((run["disposition"], run["schema_valid"]))
            invalid_schema += int(not run["schema_valid"])
            expected, observed = fixture["expected_disposition"], run["disposition"]
            if expected in {"FAIL", "REFUSE"} and observed == "PASS":
                false_accepts += 1
            if expected == "PASS" and observed != "PASS":
                false_rejects += 1
            if expected == "REFUSE":
                refusal_total += 1
                refusal_correct += int(observed == "REFUSE")
        repeatable += int(len(outcomes) == 1)
    fixture_count = len(report["fixtures"])
    metrics = {
        "fixture_count": fixture_count,
        "run_count": run_count,
        "false_accept_rate": false_accepts / run_count,
        "false_reject_rate": false_rejects / run_count,
        "invalid_schema_rate": invalid_schema / run_count,
        "repeatability_rate": repeatable / fixture_count,
        "refusal_correctness_rate": refusal_correct / refusal_total if refusal_total else 0.0,
    }
    capacity = report["capacity"]
    capacity_pass = (
        capacity["passed"]
        and capacity["peak_vram_gb"] <= capacity["max_vram_gb"]
        and capacity["peak_ram_gb"] <= capacity["max_ram_gb"]
        and capacity["p95_latency_seconds"] <= capacity["max_latency_seconds"]
    )
    thresholds = report["thresholds"]
    reasons: set[str] = set()
    if categories != REQUIRED_CATEGORIES:
        reasons.add("REQUIRED_FIXTURE_COVERAGE_INCOMPLETE")
    if not capacity_pass:
        reasons.add("CAPACITY_OR_LATENCY_QUALIFICATION_FAILED")
    if metrics["false_accept_rate"] > thresholds["max_false_accept_rate"]:
        reasons.add("FALSE_ACCEPT_RATE_EXCEEDED")
    if metrics["false_reject_rate"] > thresholds["max_false_reject_rate"]:
        reasons.add("FALSE_REJECT_RATE_EXCEEDED")
    if metrics["invalid_schema_rate"] > thresholds["max_invalid_schema_rate"]:
        reasons.add("STRUCTURED_OUTPUT_RELIABILITY_FAILED")
    if metrics["repeatability_rate"] < thresholds["min_repeatability_rate"]:
        reasons.add("REPEATABILITY_FAILED")
    if metrics["refusal_correctness_rate"] < thresholds["min_refusal_correctness_rate"]:
        reasons.add("REFUSAL_CORRECTNESS_FAILED")
    qualified = not reasons
    if qualified:
        reasons.add("EXACT_SCOPE_CAPACITY_QUALITY_AND_RELIABILITY_QUALIFIED")
    certificate = {
        "schema_version": "wave64.aqa.role_qualification_certificate.v1",
        "certificate_id": ZERO_HASH,
        "report_sha256": content_hash(report),
        "role_id": report["role_id"], "model_id": report["model_id"],
        "checkpoint_sha256": report["checkpoint_sha256"], "runtime_digest": report["runtime_digest"],
        "prompt_sha256": report["prompt_sha256"], "corpus_sha256": report["corpus_sha256"],
        "issued_at": report["issued_at"], "expires_at": report["expires_at"],
        "scope": report["scope"], "thresholds": thresholds, "metrics": metrics,
        "coverage_categories": sorted(categories),
        "qualification_disposition": "QUALIFIED_FOR_DECLARED_SCOPE" if qualified else "FAILED_QUALIFICATION",
        "operational_authority_granted": qualified,
        "reason_codes": sorted(reasons),
    }
    certificate["certificate_id"] = hashlib.sha256(canonical_bytes(certificate)).hexdigest()
    jsonschema.Draft7Validator(_load_json(CERTIFICATE_SCHEMA_PATH)).validate(certificate)
    return certificate


def evaluate_drift(
    baseline: dict[str, Any], current_report: dict[str, Any], evaluated_at: str,
) -> dict[str, Any]:
    try:
        jsonschema.Draft7Validator(_load_json(CERTIFICATE_SCHEMA_PATH)).validate(baseline)
    except jsonschema.ValidationError as exc:
        raise QualificationError(f"baseline certificate schema failed: {exc.message}") from exc
    current = compile_certificate(current_report)
    when = _parse_time(evaluated_at)
    reasons: set[str] = set()
    disposition = "ACTIVE_SCOPE_UNCHANGED"
    if baseline["qualification_disposition"] != "QUALIFIED_FOR_DECLARED_SCOPE":
        disposition, reasons = "SUSPEND_BASELINE_NOT_QUALIFIED", {"BASELINE_CERTIFICATE_NOT_QUALIFIED"}
    elif when >= _parse_time(baseline["expires_at"]):
        disposition, reasons = "SUSPEND_EXPIRED", {"BASELINE_CERTIFICATE_EXPIRED"}
    else:
        fingerprint_fields = ("role_id", "model_id", "checkpoint_sha256", "runtime_digest", "prompt_sha256", "corpus_sha256")
        if any(current[field] != baseline[field] for field in fingerprint_fields):
            disposition, reasons = "SUSPEND_FINGERPRINT_DRIFT", {"MODEL_RUNTIME_PROMPT_OR_CORPUS_FINGERPRINT_CHANGED"}
        elif current["scope"] != baseline["scope"]:
            disposition, reasons = "SUSPEND_SCOPE_DRIFT", {"QUALIFIED_SCOPE_CHANGED"}
        else:
            tolerance = baseline["thresholds"]["max_behavior_metric_delta"]
            worse = (
                current["qualification_disposition"] != "QUALIFIED_FOR_DECLARED_SCOPE"
                or current["metrics"]["false_accept_rate"] - baseline["metrics"]["false_accept_rate"] > tolerance
                or current["metrics"]["false_reject_rate"] - baseline["metrics"]["false_reject_rate"] > tolerance
                or current["metrics"]["invalid_schema_rate"] - baseline["metrics"]["invalid_schema_rate"] > tolerance
                or baseline["metrics"]["repeatability_rate"] - current["metrics"]["repeatability_rate"] > tolerance
                or baseline["metrics"]["refusal_correctness_rate"] - current["metrics"]["refusal_correctness_rate"] > tolerance
            )
            if worse:
                disposition, reasons = "SUSPEND_BEHAVIOR_DRIFT", {"BEHAVIOR_OR_RELIABILITY_DRIFT_EXCEEDED"}
            else:
                reasons.add("FINGERPRINT_SCOPE_CAPACITY_AND_BEHAVIOR_UNCHANGED")
    decision = {
        "schema_version": "wave64.aqa.role_drift_decision.v1", "decision_id": ZERO_HASH,
        "baseline_certificate_id": baseline["certificate_id"],
        "current_certificate_id": current["certificate_id"], "evaluated_at": evaluated_at,
        "disposition": disposition, "scope_operational": disposition == "ACTIVE_SCOPE_UNCHANGED",
        "reason_codes": sorted(reasons),
    }
    decision["decision_id"] = hashlib.sha256(canonical_bytes(decision)).hexdigest()
    jsonschema.Draft7Validator(_load_json(DRIFT_SCHEMA_PATH), format_checker=jsonschema.FormatChecker()).validate(decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("report", type=Path)
    drift_parser = subparsers.add_parser("drift")
    drift_parser.add_argument("baseline", type=Path)
    drift_parser.add_argument("current_report", type=Path)
    drift_parser.add_argument("evaluated_at")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "compile":
            result = compile_certificate(_load_json(args.report))
        else:
            result = evaluate_drift(_load_json(args.baseline), _load_json(args.current_report), args.evaluated_at)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise QualificationError("output already exists; qualification evidence is immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (QualificationError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
