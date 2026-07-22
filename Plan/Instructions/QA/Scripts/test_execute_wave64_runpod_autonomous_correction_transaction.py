from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_correction_transaction.py"
CORRECTION_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py"
CANDIDATE_ROOT = ROOT / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_CANDIDATE_STAGING_20260721T232803Z"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seal(module, value: dict) -> dict:
    value["receipt_id"] = "0" * 64
    value["receipt_id"] = hashlib.sha256(module.canonical_bytes(value)).hexdigest()
    return value


def fixture(tmp_path: Path, *, score: float = 0.55):
    module = load(EXECUTOR_PATH, "w64_correction_transaction_fixture")
    correction = load(CORRECTION_PATH, "w64_correction_transaction_state")
    candidate = json.loads((CANDIDATE_ROOT / "receipts/candidate_write.receipt.json").read_text(encoding="utf-8"))
    contract = json.loads((CANDIDATE_ROOT / "jobs/W64-AQA-JOB-workflow-receipt-shadow/inputs/contract.json").read_text(encoding="utf-8"))
    state = correction.initialize_state(
        contract, candidate["job_id"], candidate["base_workflow_sha256"], 0.6,
        {"graph_validity": 1.0, "output_contract": 1.0},
    )
    measurement = seal(module, {
        "schema_version": "wave64.aqa.correction_measurement_receipt.v1", "receipt_id": "0" * 64,
        "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
        "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
        "hard_gates_pass": True, "candidate_total_score": score,
        "candidate_protected_scores": {"graph_validity": 1.0, "output_contract": 1.0},
        "deterministic": True, "runtime_measurement_performed": False,
        "disposition": "PASS_SYNTHETIC_DETERMINISTIC_MEASUREMENT_ONLY",
    })
    sandbox = seal(module, {
        "schema_version": "wave64.aqa.correction_sandbox_receipt.v1", "receipt_id": "0" * 64,
        "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
        "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
        "candidate_staging_receipt_id": candidate["receipt_id"], "static_validation_passed": True,
        "synthetic_fixture_only": True, "comfyui_execution_performed": False,
        "model_inference_performed": False, "network_used": False,
        "disposition": "PASS_SYNTHETIC_SANDBOX_FIXTURE_ONLY",
    })
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    paths = []
    for name, value in (("candidate", candidate), ("measurement", measurement), ("sandbox", sandbox)):
        path = evidence_dir / f"{name}.json"
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(path)
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    attempt = {
        "schema_version": "wave64.aqa.correction_attempt.v1", "attempt_id": "W64-AQA-REPAIR-receipt-bound-1",
        "job_id": candidate["job_id"], "contract_id": candidate["authority_binding_sha256"],
        "parent_artifact_sha256": candidate["base_workflow_sha256"],
        "candidate_artifact_sha256": candidate["candidate_workflow_sha256"],
        "defect_id": "workflow_cfg", "generation_consumed": False, "hard_gates_pass": True,
        "candidate_total_score": score,
        "candidate_protected_scores": {"graph_validity": 1.0, "output_contract": 1.0},
        "evidence_sha256": hashes,
    }
    journal = tmp_path / "journal"
    journal.mkdir()
    return module, state, attempt, contract, candidate, measurement, sandbox, hashes, journal


def test_receipt_bound_nonimproving_candidate_reverts_without_runtime_claim(tmp_path: Path) -> None:
    module, state, attempt, contract, candidate, measurement, sandbox, hashes, journal = fixture(tmp_path)
    receipt = module.execute_transaction(
        state, attempt, contract, candidate, measurement, sandbox, hashes, journal
    )
    assert receipt["transition_disposition"] == "REVERT_CANDIDATE_CONTINUE"
    assert receipt["state_publish_status"] == "CREATED_IMMUTABLE"
    assert receipt["comfyui_execution_performed"] is False
    assert receipt["runtime_measurement_performed"] is False
    assert receipt["promotion_authorized"] is False
    saved = json.loads((journal / "0001.state.json").read_text(encoding="utf-8"))
    assert saved["accepted_artifact_sha256"] == state["accepted_artifact_sha256"]


def test_crash_after_state_resumes_exactly_and_completed_replay_is_idempotent(tmp_path: Path) -> None:
    module, state, attempt, contract, candidate, measurement, sandbox, hashes, journal = fixture(tmp_path)
    with pytest.raises(module.CorrectionTransactionError, match="INJECTED_CRASH"):
        module.execute_transaction(
            state, attempt, contract, candidate, measurement, sandbox, hashes, journal,
            inject_crash_after_state=True,
        )
    assert (journal / "0001.state.json").is_file()
    assert not (journal / "0001.receipt.json").exists()
    resumed = module.execute_transaction(
        state, attempt, contract, candidate, measurement, sandbox, hashes, journal
    )
    assert resumed["state_publish_status"] == "REUSED_EXACT_AFTER_REPLAY"
    replayed = module.execute_transaction(
        state, attempt, contract, candidate, measurement, sandbox, hashes, journal
    )
    assert replayed == resumed


def test_improving_fixture_can_retain_but_never_promote_or_claim_comfyui(tmp_path: Path) -> None:
    module, state, attempt, contract, candidate, measurement, sandbox, hashes, journal = fixture(tmp_path, score=0.7)
    receipt = module.execute_transaction(
        state, attempt, contract, candidate, measurement, sandbox, hashes, journal
    )
    assert receipt["transition_disposition"] == "RETAIN_CANDIDATE_EXIT_REPAIR_LOOP"
    assert receipt["promotion_authorized"] is False
    assert receipt["comfyui_execution_performed"] is False


def test_receipt_tampering_evidence_mismatch_and_policy_weakening_fail_closed(tmp_path: Path) -> None:
    module, state, attempt, contract, candidate, measurement, sandbox, hashes, journal = fixture(tmp_path)
    tampered = copy.deepcopy(measurement)
    tampered["candidate_total_score"] = 0.9
    with pytest.raises(module.CorrectionTransactionError, match="self-hash"):
        module.execute_transaction(state, attempt, contract, candidate, tampered, sandbox, hashes, journal)
    wrong_hashes = list(hashes)
    wrong_hashes[0] = "f" * 64
    with pytest.raises(module.CorrectionTransactionError, match="do not bind"):
        module.execute_transaction(state, attempt, contract, candidate, measurement, sandbox, wrong_hashes, journal)
    policy = module._load_json(module.POLICY_PATH)
    policy["promotion_allowed"] = True
    with pytest.raises(module.CorrectionTransactionError, match="changed or weakened"):
        module.execute_transaction(
            state, attempt, contract, candidate, measurement, sandbox, hashes, journal, policy=policy
        )
