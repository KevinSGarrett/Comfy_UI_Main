#!/usr/bin/env python3
"""Produce retained receipt-bound correction crash/replay evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_correction_transaction.py"
CORRECTION_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py"
CANDIDATE_ROOT = ROOT / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_CANDIDATE_STAGING_20260721T232803Z"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def produce(output: Path, source_head: str, generated_at_utc: str) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        executor = load(EXECUTOR_PATH, "w64_retained_correction_transaction")
        correction = load(CORRECTION_PATH, "w64_retained_correction_state")
        candidate_source = CANDIDATE_ROOT / "receipts/candidate_write.receipt.json"
        candidate_path = temporary / "candidate_staging.receipt.json"
        shutil.copy2(candidate_source, candidate_path)
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        contract = json.loads((CANDIDATE_ROOT / "jobs/W64-AQA-JOB-workflow-receipt-shadow/inputs/contract.json").read_text(encoding="utf-8"))
        state = correction.initialize_state(
            contract, candidate["job_id"], candidate["base_workflow_sha256"], 0.6,
            {"graph_validity": 1.0, "output_contract": 1.0},
        )
        measurement = {
            "schema_version": "wave64.aqa.correction_measurement_receipt.v1", "receipt_id": "0" * 64,
            "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
            "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
            "hard_gates_pass": True, "candidate_total_score": 0.55,
            "candidate_protected_scores": {"graph_validity": 1.0, "output_contract": 1.0},
            "deterministic": True, "runtime_measurement_performed": False,
            "disposition": "PASS_SYNTHETIC_DETERMINISTIC_MEASUREMENT_ONLY",
        }
        measurement["receipt_id"] = hashlib.sha256(executor.canonical_bytes(measurement)).hexdigest()
        sandbox = {
            "schema_version": "wave64.aqa.correction_sandbox_receipt.v1", "receipt_id": "0" * 64,
            "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
            "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
            "candidate_staging_receipt_id": candidate["receipt_id"], "static_validation_passed": True,
            "synthetic_fixture_only": True, "comfyui_execution_performed": False,
            "model_inference_performed": False, "network_used": False,
            "disposition": "PASS_SYNTHETIC_SANDBOX_FIXTURE_ONLY",
        }
        sandbox["receipt_id"] = hashlib.sha256(executor.canonical_bytes(sandbox)).hexdigest()
        measurement_path = temporary / "measurement.receipt.json"
        sandbox_path = temporary / "sandbox.receipt.json"
        write_json(measurement_path, measurement)
        write_json(sandbox_path, sandbox)
        evidence_hashes = [
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (candidate_path, measurement_path, sandbox_path)
        ]
        attempt = {
            "schema_version": "wave64.aqa.correction_attempt.v1",
            "attempt_id": "W64-AQA-REPAIR-retained-revert-1",
            "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
            "parent_artifact_sha256": candidate["base_workflow_sha256"],
            "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
            "defect_id": "workflow_cfg", "generation_consumed": False, "hard_gates_pass": True,
            "candidate_total_score": 0.55,
            "candidate_protected_scores": {"graph_validity": 1.0, "output_contract": 1.0},
            "evidence_sha256": evidence_hashes,
        }
        write_json(temporary / "contract.json", contract)
        write_json(temporary / "baseline.state.json", state)
        write_json(temporary / "attempt.json", attempt)
        journal = temporary / "journal"
        journal.mkdir()
        crash_observed = False
        try:
            executor.execute_transaction(
                state, attempt, contract, candidate, measurement, sandbox, evidence_hashes, journal,
                inject_crash_after_state=True,
            )
        except executor.CorrectionTransactionError as exc:
            if str(exc) != "INJECTED_CRASH_AFTER_STATE_PUBLISH":
                raise
            crash_observed = True
        if not crash_observed or not (journal / "0001.state.json").is_file() or (journal / "0001.receipt.json").exists():
            raise ValueError("injected correction crash boundary was not retained exactly")
        resumed = executor.execute_transaction(
            state, attempt, contract, candidate, measurement, sandbox, evidence_hashes, journal
        )
        replayed = executor.execute_transaction(
            state, attempt, contract, candidate, measurement, sandbox, evidence_hashes, journal
        )
        if replayed != resumed:
            raise ValueError("completed correction transaction replay diverged")
        manifest = {}
        for path in sorted(temporary.rglob("*")):
            if path.is_file():
                manifest[path.relative_to(temporary).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence = {
            "schema_version": "wave64.aqa.correction_transaction_evidence.v1",
            "program_id": "W64-AQA", "evidence_id": "W64-AQA-CORRECTION-TRANSACTION-20260722T000248Z",
            "generated_at_utc": generated_at_utc, "source_head": source_head,
            "job_id": candidate["job_id"], "attempt_id": attempt["attempt_id"],
            "crash_after_state_publish_observed": crash_observed,
            "resume_state_publish_status": resumed["state_publish_status"],
            "completed_replay_exact": replayed == resumed,
            "transition_disposition": resumed["transition_disposition"],
            "accepted_parent_preserved": json.loads((journal / "0001.state.json").read_text(encoding="utf-8"))["accepted_artifact_sha256"] == state["accepted_artifact_sha256"],
            "runtime_claims": {"runpod_contacted": False, "gpu_used": False, "comfyui_execution_performed": False,
                               "runtime_measurement_performed": False, "network_used": False,
                               "overwrite_performed": False, "delete_performed": False,
                               "product_promotion_granted": False},
            "disposition": "PASS_RECEIPT_BOUND_CORRECTION_CRASH_RESUME_REVERT_FIXTURE_ONLY",
            "file_manifest_sha256": manifest,
        }
        write_json(temporary / "evidence.json", evidence)
        os.replace(temporary, output)
        return evidence
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("source_head")
    parser.add_argument("generated_at_utc")
    args = parser.parse_args()
    try:
        print(json.dumps(produce(args.output, args.source_head, args.generated_at_utc), indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
