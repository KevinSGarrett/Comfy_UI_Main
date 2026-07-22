#!/usr/bin/env python3
"""Execute a receipt-bound immutable correction transition with crash-safe replay."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_correction_transaction_policy.json"
MEASUREMENT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_correction_measurement_receipt.schema.json"
SANDBOX_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_correction_sandbox_receipt.schema.json"
TRANSACTION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_correction_transaction_receipt.schema.json"
CANDIDATE_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_workflow_candidate_staging_receipt.schema.json"
CORRECTION_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py"
PUBLISHER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
ZERO_HASH = "0" * 64


class CorrectionTransactionError(ValueError):
    """Raised when correction evidence or immutable replay cannot be trusted."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorrectionTransactionError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CorrectionTransactionError(f"JSON root must be an object: {path}")
    return value


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CorrectionTransactionError(f"cannot load component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _self_hash(value: dict[str, Any], field: str) -> str:
    candidate = copy.deepcopy(value)
    candidate[field] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(candidate)).hexdigest()


def _validate_policy(policy: dict[str, Any]) -> None:
    expected = {
        "schema_version": "wave64.aqa.correction_transaction_policy.v1",
        "execution_modes": ["shadow_qualification"],
        "candidate_staging_disposition": "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGED",
        "measurement_deterministic_required": True,
        "synthetic_sandbox_disposition": "PASS_SYNTHETIC_SANDBOX_FIXTURE_ONLY",
        "comfyui_execution_required_false": True,
        "immutable_state_publish_required": True,
        "immutable_receipt_publish_required": True,
        "resume_by_exact_replay_required": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "network_allowed": False,
        "production_mode_allowed": False,
        "promotion_allowed": False,
    }
    if any(policy.get(key) != value for key, value in expected.items()):
        raise CorrectionTransactionError("correction transaction policy changed or weakened")


def _publish_or_reuse(path: Path, rendered: str) -> str:
    if path.exists():
        if path.is_symlink() or path.read_text(encoding="utf-8") != rendered:
            raise CorrectionTransactionError("IMMUTABLE_JOURNAL_REPLAY_MISMATCH")
        return "REUSED_EXACT_AFTER_REPLAY"
    publisher = _load(PUBLISHER_PATH, "w64_correction_transaction_publisher")
    publisher._publish_immutable(path, rendered)
    return "CREATED_IMMUTABLE"


def execute_transaction(
    state: dict[str, Any], attempt: dict[str, Any], contract: dict[str, Any],
    candidate_receipt: dict[str, Any], measurement_receipt: dict[str, Any],
    sandbox_receipt: dict[str, Any], evidence_file_sha256: list[str], journal: Path,
    *, policy: dict[str, Any] | None = None, inject_crash_after_state: bool = False,
) -> dict[str, Any]:
    policy = policy or _load_json(POLICY_PATH)
    _validate_policy(policy)
    try:
        jsonschema.Draft7Validator(_load_json(CANDIDATE_SCHEMA_PATH)).validate(candidate_receipt)
        jsonschema.Draft7Validator(_load_json(MEASUREMENT_SCHEMA_PATH)).validate(measurement_receipt)
        jsonschema.Draft7Validator(_load_json(SANDBOX_SCHEMA_PATH)).validate(sandbox_receipt)
    except jsonschema.ValidationError as exc:
        raise CorrectionTransactionError(f"correction receipt schema invalid: {exc.message}") from exc
    for label, receipt in (
        ("candidate", candidate_receipt), ("measurement", measurement_receipt), ("sandbox", sandbox_receipt)
    ):
        if receipt["receipt_id"] != _self_hash(receipt, "receipt_id"):
            raise CorrectionTransactionError(f"{label} receipt self-hash mismatch")
    if len(evidence_file_sha256) != 3 or len(set(evidence_file_sha256)) != 3:
        raise CorrectionTransactionError("exactly three distinct evidence file hashes are required")
    if sorted(attempt["evidence_sha256"]) != sorted(evidence_file_sha256):
        raise CorrectionTransactionError("attempt evidence hashes do not bind supplied receipts")
    required_common = {
        "job_id": attempt["job_id"], "contract_id": attempt["contract_id"],
        "candidate_artifact_sha256": attempt["candidate_artifact_sha256"],
    }
    for label, receipt in (("measurement", measurement_receipt), ("sandbox", sandbox_receipt)):
        if any(receipt.get(key) != value for key, value in required_common.items()):
            raise CorrectionTransactionError(f"{label} receipt binding mismatch")
    if candidate_receipt["job_id"] != attempt["job_id"]:
        raise CorrectionTransactionError("candidate receipt job mismatch")
    if candidate_receipt["authority_binding_sha256"] != attempt["contract_id"]:
        raise CorrectionTransactionError("candidate receipt contract mismatch")
    if candidate_receipt["base_workflow_sha256"] != attempt["parent_artifact_sha256"]:
        raise CorrectionTransactionError("candidate receipt parent mismatch")
    if candidate_receipt["candidate_workflow_sha256"] != attempt["candidate_artifact_sha256"]:
        raise CorrectionTransactionError("candidate receipt artifact mismatch")
    if sandbox_receipt["candidate_staging_receipt_id"] != candidate_receipt["receipt_id"]:
        raise CorrectionTransactionError("sandbox receipt does not bind candidate staging receipt")
    if measurement_receipt["hard_gates_pass"] != attempt["hard_gates_pass"]:
        raise CorrectionTransactionError("measurement hard-gate binding mismatch")
    if measurement_receipt["candidate_total_score"] != attempt["candidate_total_score"]:
        raise CorrectionTransactionError("measurement total-score binding mismatch")
    if measurement_receipt["candidate_protected_scores"] != attempt["candidate_protected_scores"]:
        raise CorrectionTransactionError("measurement protected-score binding mismatch")

    correction = _load(CORRECTION_PATH, "w64_receipt_bound_correction_policy")
    next_state = correction.transition(state, attempt, contract)
    state_path = journal / f"{next_state['sequence']:04d}.state.json"
    rendered_state = json.dumps(next_state, indent=2, sort_keys=True) + "\n"
    state_status = _publish_or_reuse(state_path, rendered_state)
    if inject_crash_after_state:
        raise CorrectionTransactionError("INJECTED_CRASH_AFTER_STATE_PUBLISH")
    receipt_path = journal / f"{next_state['sequence']:04d}.receipt.json"
    if receipt_path.exists():
        existing_receipt = _load_json(receipt_path)
        jsonschema.Draft7Validator(_load_json(TRANSACTION_SCHEMA_PATH)).validate(existing_receipt)
        if existing_receipt["receipt_id"] != _self_hash(existing_receipt, "receipt_id"):
            raise CorrectionTransactionError("existing transaction receipt self-hash mismatch")
        if (
            existing_receipt["previous_state_id"] != state["state_id"]
            or existing_receipt["next_state_id"] != next_state["state_id"]
            or existing_receipt["attempt_id"] != attempt["attempt_id"]
        ):
            raise CorrectionTransactionError("existing transaction receipt replay mismatch")
        return existing_receipt
    receipt = {
        "schema_version": "wave64.aqa.correction_transaction_receipt.v1",
        "receipt_id": ZERO_HASH,
        "job_id": attempt["job_id"], "contract_id": attempt["contract_id"],
        "attempt_id": attempt["attempt_id"], "previous_state_id": state["state_id"],
        "next_state_id": next_state["state_id"],
        "candidate_staging_receipt_id": candidate_receipt["receipt_id"],
        "measurement_receipt_id": measurement_receipt["receipt_id"],
        "sandbox_receipt_id": sandbox_receipt["receipt_id"],
        "evidence_file_sha256": sorted(evidence_file_sha256),
        "state_publish_status": state_status,
        "transition_disposition": next_state["disposition"],
        "resume_safe": True, "comfyui_execution_performed": False,
        "runtime_measurement_performed": False, "network_used": False,
        "overwrite_performed": False, "delete_performed": False,
        "promotion_authorized": False,
        "disposition": "PASS_RECEIPT_BOUND_CORRECTION_TRANSACTION_FIXTURE_ONLY",
    }
    receipt["receipt_id"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    jsonschema.Draft7Validator(_load_json(TRANSACTION_SCHEMA_PATH)).validate(receipt)
    _publish_or_reuse(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state", "attempt", "contract", "candidate_receipt", "measurement_receipt", "sandbox_receipt"):
        parser.add_argument(name, type=Path)
    parser.add_argument("journal", type=Path)
    args = parser.parse_args()
    try:
        paths = [args.candidate_receipt, args.measurement_receipt, args.sandbox_receipt]
        receipt = execute_transaction(
            _load_json(args.state), _load_json(args.attempt), _load_json(args.contract),
            _load_json(args.candidate_receipt), _load_json(args.measurement_receipt),
            _load_json(args.sandbox_receipt),
            [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths], args.journal,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except (CorrectionTransactionError, jsonschema.ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
