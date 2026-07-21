from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py"


def load_policy():
    spec = importlib.util.spec_from_file_location("w64_aqa_correction_policy", POLICY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(*, repairs: int = 2, generations: int = 4, no_progress: int = 2) -> dict:
    return {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "1" * 64,
        "attempt_policy": {
            "max_repairs_per_defect": repairs,
            "max_total_generations": generations,
            "max_no_progress_cycles": no_progress,
        },
    }


def initial(module, spec: dict | None = None) -> dict:
    return module.initialize_state(
        spec or contract(), "W64-AQA-JOB-test", "a" * 64, 0.6,
        {"identity": 0.8, "composition": 0.7},
    )


def attempt(
    *, number: int = 1, score: float = 0.7, hard_pass: bool = True,
    protected: dict | None = None, defect: str = "identity", generation: bool = True,
) -> dict:
    return {
        "schema_version": "wave64.aqa.correction_attempt.v1",
        "attempt_id": f"W64-AQA-REPAIR-test-{number}",
        "job_id": "W64-AQA-JOB-test", "contract_id": "1" * 64,
        "parent_artifact_sha256": "a" * 64,
        "candidate_artifact_sha256": f"{number + 1:x}" * 64,
        "defect_id": defect, "generation_consumed": generation,
        "hard_gates_pass": hard_pass, "candidate_total_score": score,
        "candidate_protected_scores": protected or {"identity": 0.8, "composition": 0.7},
        "evidence_sha256": [f"{number + 8:x}" * 64],
    }


def test_initial_state_is_immutable_deterministic_and_has_no_promotion_authority() -> None:
    module = load_policy()
    first, second = initial(module), initial(module)
    assert first == second
    assert first["disposition"] == "BASELINE_ACCEPTED"
    assert first["total_generation_attempts"] == 1
    assert first["promotion_authorized"] is False


def test_improved_hard_gate_passing_nonregressing_candidate_is_retained() -> None:
    module = load_policy()
    result = module.transition(initial(module), attempt(), contract())
    assert result["disposition"] == "RETAIN_CANDIDATE_EXIT_REPAIR_LOOP"
    assert result["accepted_artifact_sha256"] == "2" * 64
    assert result["accepted_total_score"] == 0.7
    assert result["terminal"] is True
    assert result["promotion_authorized"] is False


@pytest.mark.parametrize("candidate,reason", [
    (attempt(hard_pass=False), "HARD_GATES_FAILED"),
    (attempt(score=0.6), "TOTAL_SCORE_DID_NOT_IMPROVE"),
    (attempt(protected={"identity": 0.79, "composition": 0.7}), "PROTECTED_CATEGORY_REGRESSION"),
])
def test_failed_nonimproving_or_regressing_candidate_reverts(candidate: dict, reason: str) -> None:
    module = load_policy()
    result = module.transition(initial(module), candidate, contract())
    assert result["disposition"] == "REVERT_CANDIDATE_CONTINUE"
    assert result["accepted_artifact_sha256"] == "a" * 64
    assert reason in result["reason_codes"]
    assert "CANDIDATE_REVERTED_TO_ACCEPTED_PARENT" in result["reason_codes"]


def test_second_consecutive_no_progress_exhausts_to_blocked_never_pass() -> None:
    module = load_policy()
    first = module.transition(initial(module), attempt(number=1, score=0.6), contract())
    second_attempt = attempt(number=2, score=0.6)
    second = module.transition(first, second_attempt, contract())
    assert second["disposition"] == "EXHAUSTED_BLOCKED"
    assert second["terminal"] is True
    assert "NO_PROGRESS_CEILING_REACHED" in second["reason_codes"]
    assert "PER_DEFECT_REPAIR_CEILING_REACHED" in second["reason_codes"]
    assert second["promotion_authorized"] is False


def test_stricter_per_defect_and_total_generation_ceilings_are_enforced() -> None:
    module = load_policy()
    strict_repair = contract(repairs=1)
    result = module.transition(initial(module, strict_repair), attempt(score=0.6), strict_repair)
    assert result["disposition"] == "EXHAUSTED_BLOCKED"
    assert "PER_DEFECT_REPAIR_CEILING_REACHED" in result["reason_codes"]
    strict_generation = contract(generations=2)
    result = module.transition(initial(module, strict_generation), attempt(score=0.6), strict_generation)
    assert "TOTAL_GENERATION_CEILING_REACHED" in result["reason_codes"]


def test_zero_no_progress_policy_blocks_first_rejected_candidate() -> None:
    module = load_policy()
    spec = contract(no_progress=0)
    result = module.transition(initial(module, spec), attempt(score=0.6), spec)
    assert result["disposition"] == "EXHAUSTED_BLOCKED"
    assert "NO_PROGRESS_CEILING_REACHED" in result["reason_codes"]


def test_parent_contract_job_protected_keys_and_terminal_state_are_enforced() -> None:
    module = load_policy()
    state = initial(module)
    wrong_parent = attempt()
    wrong_parent["parent_artifact_sha256"] = "b" * 64
    with pytest.raises(module.CorrectionPolicyError, match="rollback parent"):
        module.transition(state, wrong_parent, contract())
    wrong_keys = attempt(protected={"identity": 0.8})
    with pytest.raises(module.CorrectionPolicyError, match="exact parity"):
        module.transition(state, wrong_keys, contract())
    terminal = module.transition(state, attempt(), contract())
    with pytest.raises(module.CorrectionPolicyError, match="terminal"):
        module.transition(terminal, attempt(number=2), contract())


def test_tampered_state_same_candidate_and_policy_expansion_fail_closed() -> None:
    module = load_policy()
    state = initial(module)
    state["accepted_total_score"] = 0.1
    with pytest.raises(module.CorrectionPolicyError, match="hash chain"):
        module.transition(state, attempt(), contract())
    same = attempt()
    same["candidate_artifact_sha256"] = "a" * 64
    with pytest.raises(module.CorrectionPolicyError, match="must differ"):
        module.transition(initial(module), same, contract())
    expanded = contract(repairs=3)
    with pytest.raises(module.CorrectionPolicyError, match="between"):
        initial(module, expanded)
