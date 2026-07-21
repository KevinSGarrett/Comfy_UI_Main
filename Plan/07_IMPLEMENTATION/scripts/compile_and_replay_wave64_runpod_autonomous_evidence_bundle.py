#!/usr/bin/env python3
"""Compile, replay, and plan—but never execute—W64-AQA evidence promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_qa_decision.schema.json"
BUNDLE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_evidence_bundle.schema.json"
PROMOTION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_promotion_transaction.schema.json"
ZERO_HASH = "0" * 64
REQUIRED_RECORD_TYPES = {"candidate", "workflow", "runtime_receipt", "correction_state", "cost_receipt"}


class EvidenceBundleError(ValueError):
    """Raised when evidence cannot be compiled or replayed without ambiguity."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceBundleError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceBundleError(f"JSON root must be an object: {path}")
    return value


def _safe_relative(path: str) -> bool:
    if "\\" in path:
        return False
    pure = PurePosixPath(path)
    return not pure.is_absolute() and all(part not in {"", ".", ".."} for part in pure.parts) and pure.as_posix() == path


def _validate_contract_and_decision(contract: dict[str, Any], decision: dict[str, Any]) -> None:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1":
        raise EvidenceBundleError("unsupported contract schema_version")
    try:
        jsonschema.Draft7Validator(_load_json(DECISION_SCHEMA_PATH)).validate(decision)
    except jsonschema.ValidationError as exc:
        raise EvidenceBundleError(f"decision schema validation failed: {exc.message}") from exc
    if decision["job_id"] != contract.get("job_id"):
        raise EvidenceBundleError("decision job_id does not match contract")
    if decision["modality"] != contract.get("modality"):
        raise EvidenceBundleError("decision modality does not match contract")
    if decision["lineage"]["quality_contract_sha256"] != contract.get("contract_id"):
        raise EvidenceBundleError("decision lineage does not bind the contract_id")
    if decision.get("promotion_claimed") is not False:
        raise EvidenceBundleError("decision must not claim promotion")


def replay_decision(contract: dict[str, Any], decision: dict[str, Any]) -> str:
    _validate_contract_and_decision(contract, decision)
    applicable = [entry for entry in decision["measurements"] if entry["applicable"]]
    hard_gates_pass = bool(applicable) and all(entry["passed"] for entry in applicable)
    required_roles = set(contract["quality_profile"]["required_approval_roles"])
    valid_approvals = {
        entry["role_id"] for entry in decision["reviewers"]
        if entry["product_authority"] and entry["response_valid"] and entry["state"] == "QUALIFIED"
    }
    approvals_pass = required_roles.issubset(valid_approvals)
    attempt = decision["attempt_state"]
    ceilings = attempt["ceilings"]
    exhausted = (
        attempt["defect_attempt"] >= ceilings["per_defect"]
        or attempt["total_generation_attempt"] >= ceilings["total_generation"]
        or attempt["consecutive_no_progress"] >= ceilings["no_progress"]
    )
    workflow_patch = decision.get("workflow_patch")
    workflow_ready = workflow_patch is None or all(
        workflow_patch.get(key) is True
        for key in ("static_validation_passed", "sandbox_validation_passed", "regression_passed")
    )
    if not approvals_pass or not workflow_ready:
        return "BLOCKED"
    if hard_gates_pass and not decision["blocking_defects"]:
        return "PASS"
    if exhausted:
        return "BLOCKED"
    return "REPAIR"


def _compile_records(record_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for spec in record_specs:
        if set(spec) != {"record_type", "source_path", "durable_relative_path"}:
            raise EvidenceBundleError("record spec requires exactly record_type, source_path, and durable_relative_path")
        source = Path(spec["source_path"])
        durable_path = spec["durable_relative_path"]
        if not source.is_file() or source.stat().st_size < 1:
            raise EvidenceBundleError(f"record source is missing or empty: {source}")
        if not isinstance(durable_path, str) or not _safe_relative(durable_path):
            raise EvidenceBundleError("record durable path must be normalized and relative")
        if durable_path in seen_paths:
            raise EvidenceBundleError("record durable paths must be unique")
        seen_paths.add(durable_path)
        records.append({
            "record_type": spec["record_type"],
            "content_sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
            "durable_relative_path": durable_path,
        })
    return sorted(records, key=lambda item: (item["record_type"], item["durable_relative_path"]))


def compile_bundle(
    contract: dict[str, Any], decision: dict[str, Any], record_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    replayed = replay_decision(contract, decision)
    if decision["decision"] not in {"PASS", "REPAIR", "BLOCKED"}:
        raise EvidenceBundleError("static replay does not authorize REJECT or HUMAN_EXCEPTION_REQUIRED")
    if replayed != decision["decision"]:
        raise EvidenceBundleError(f"replay mismatch: recorded={decision['decision']} replayed={replayed}")
    records = _compile_records(record_specs)
    record_types = {entry["record_type"] for entry in records}
    if not REQUIRED_RECORD_TYPES.issubset(record_types):
        raise EvidenceBundleError(f"missing required record types: {sorted(REQUIRED_RECORD_TYPES - record_types)}")
    hashes = {entry["content_sha256"] for entry in records}
    required_hashes = {
        decision["lineage"]["candidate_sha256"],
        decision["lineage"]["workflow_sha256"],
    }
    required_hashes.update(
        entry["evidence_sha256"] for entry in decision["measurements"]
        if entry.get("applicable") and entry.get("evidence_sha256") is not None
    )
    required_hashes.update(
        entry["observation_sha256"] for entry in decision["reviewers"]
        if entry.get("observation_sha256") is not None
    )
    if decision.get("runtime_receipt_sha256") is not None:
        required_hashes.add(decision["runtime_receipt_sha256"])
    if decision.get("rollback_parent_sha256") is not None:
        required_hashes.add(decision["rollback_parent_sha256"])
    missing_hashes = required_hashes - hashes
    if missing_hashes:
        raise EvidenceBundleError(f"referenced evidence hashes are missing: {sorted(missing_hashes)}")
    candidate_records = [entry for entry in records if entry["record_type"] == "candidate"]
    workflow_records = [entry for entry in records if entry["record_type"] == "workflow"]
    if len(candidate_records) != 1 or candidate_records[0]["content_sha256"] != decision["lineage"]["candidate_sha256"]:
        raise EvidenceBundleError("exactly one candidate record must match decision lineage")
    if len(workflow_records) != 1 or workflow_records[0]["content_sha256"] != decision["lineage"]["workflow_sha256"]:
        raise EvidenceBundleError("exactly one workflow record must match decision lineage")
    bundle = {
        "schema_version": "wave64.aqa.evidence_bundle.v1",
        "bundle_id": ZERO_HASH,
        "job_id": contract["job_id"],
        "contract_id": contract["contract_id"],
        "contract_content_sha256": content_hash(contract),
        "decision_sha256": content_hash(decision),
        "replayed_decision": replayed,
        "replay_disposition": "MATCH",
        "accepted_candidate_sha256": decision["lineage"]["candidate_sha256"],
        "workflow_sha256": decision["lineage"]["workflow_sha256"],
        "rollback_parent_sha256": decision.get("rollback_parent_sha256"),
        "records": records,
        "promotion_invariants": {
            "replay_match_required": True,
            "integration_authority_required": True,
            "s3_presence_is_acceptance": False,
            "git_presence_is_acceptance": False,
            "promotion_executed": False,
        },
    }
    bundle["bundle_id"] = hashlib.sha256(canonical_bytes(bundle)).hexdigest()
    jsonschema.Draft7Validator(_load_json(BUNDLE_SCHEMA_PATH)).validate(bundle)
    return bundle


def replay_bundle(
    stored_bundle: dict[str, Any], contract: dict[str, Any], decision: dict[str, Any],
    record_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        jsonschema.Draft7Validator(_load_json(BUNDLE_SCHEMA_PATH)).validate(stored_bundle)
    except jsonschema.ValidationError as exc:
        raise EvidenceBundleError(f"stored bundle schema validation failed: {exc.message}") from exc
    expected = compile_bundle(contract, decision, record_specs)
    return {
        "replay_disposition": "MATCH" if expected == stored_bundle else "MISMATCH",
        "stored_bundle_id": stored_bundle["bundle_id"],
        "recompiled_bundle_id": expected["bundle_id"],
        "replayed_decision": expected["replayed_decision"],
    }


def plan_promotion(
    bundle: dict[str, Any], bucket: str, key_prefix: str,
    integration_authority_approval_sha256: str | None,
) -> dict[str, Any]:
    try:
        jsonschema.Draft7Validator(_load_json(BUNDLE_SCHEMA_PATH)).validate(bundle)
    except jsonschema.ValidationError as exc:
        raise EvidenceBundleError(f"bundle schema validation failed: {exc.message}") from exc
    if not _safe_relative(key_prefix):
        raise EvidenceBundleError("promotion key prefix must be normalized and relative")
    base = f"{key_prefix}/{bundle['bundle_id']}"
    object_keys = sorted({f"{base}/objects/{record['content_sha256']}" for record in bundle["records"]})
    if bundle["replayed_decision"] != "PASS":
        disposition = "HELD_NON_PASS_DECISION"
    elif integration_authority_approval_sha256 is None:
        disposition = "HELD_PENDING_INTEGRATION_AUTHORITY"
    elif len(integration_authority_approval_sha256) != 64 or any(character not in "0123456789abcdef" for character in integration_authority_approval_sha256):
        raise EvidenceBundleError("integration authority approval hash is invalid")
    else:
        disposition = "READY_FOR_INTEGRATION_AUTHORITY_EXECUTION"
    transaction = {
        "schema_version": "wave64.aqa.promotion_transaction.v1",
        "transaction_id": ZERO_HASH,
        "bundle_id": bundle["bundle_id"],
        "candidate_sha256": bundle["accepted_candidate_sha256"],
        "bucket": bucket,
        "key_prefix": key_prefix,
        "bundle_manifest_key": f"{base}/bundle.json",
        "object_keys": object_keys,
        "integration_authority_approval_sha256": integration_authority_approval_sha256,
        "disposition": disposition,
        "execution_performed": False,
    }
    transaction["transaction_id"] = hashlib.sha256(canonical_bytes(transaction)).hexdigest()
    jsonschema.Draft7Validator(_load_json(PROMOTION_SCHEMA_PATH)).validate(transaction)
    return transaction


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("decision", type=Path)
    parser.add_argument("records", type=Path, help="JSON array of record specs")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        record_specs = json.loads(args.records.read_text(encoding="utf-8"))
        if not isinstance(record_specs, list):
            raise EvidenceBundleError("records JSON must be an array")
        bundle = compile_bundle(_load_json(args.contract), _load_json(args.decision), record_specs)
        rendered = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise EvidenceBundleError("output already exists; bundles are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (EvidenceBundleError, json.JSONDecodeError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
