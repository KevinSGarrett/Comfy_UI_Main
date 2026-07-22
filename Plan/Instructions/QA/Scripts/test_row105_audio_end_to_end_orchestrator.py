from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/orchestrate_wave64_audio_end_to_end.py"
SPEC = importlib.util.spec_from_file_location("orchestrate_wave64_audio_end_to_end", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def fixture_run() -> dict:
    return MOD.compile_run(
        ROOT,
        request={"fixture": "row105", "video_sha256": MOD.stable_hash("video")},
        is_synthetic=True,
        admissions=MOD.accepted_fixture_dependencies(),
    )


def test_live_dependencies_hold_all_execution() -> None:
    run = MOD.compile_run(ROOT, request={"mode": "live"}, is_synthetic=False)
    assert run["decision"]["status"] == "blocked"
    assert "ROW105_DEPENDENCIES_NOT_ACCEPTED" in run["decision"]["blocker_codes"]
    assert all(stage["state"] == "pending" for stage in run["stages"])


def test_dag_is_content_addressed_and_root_only_is_ready() -> None:
    first = fixture_run()
    second = fixture_run()
    assert first == second
    assert first["run_id"].startswith("audio-run-")
    assert first["stages"][0]["state"] == "ready"
    assert all(stage["state"] == "pending" for stage in first["stages"][1:])


def test_out_of_order_stage_is_rejected() -> None:
    with pytest.raises(MOD.AudioOrchestratorError, match="stage_not_ready"):
        MOD.complete_stage(ROOT, fixture_run(), "publication", MOD.stable_hash("publication"))


def test_completed_stage_same_output_is_idempotent_and_different_output_is_rejected() -> None:
    run = MOD.complete_stage(ROOT, fixture_run(), "normalize_inputs", MOD.stable_hash("normalized"))
    assert MOD.complete_stage(ROOT, run, "normalize_inputs", MOD.stable_hash("normalized")) == run
    with pytest.raises(MOD.AudioOrchestratorError, match="immutable_passed_stage_output"):
        MOD.complete_stage(ROOT, run, "normalize_inputs", MOD.stable_hash("different"))


def test_crash_resume_preserves_passed_stage_and_readies_successors() -> None:
    proof = MOD.synthetic_crash_resume_fixture(ROOT)
    assert proof["idempotent_replay_identical"] is True
    resumed = proof["resumed"]
    states = {stage["stage_id"]: stage["state"] for stage in resumed["stages"]}
    assert states["normalize_inputs"] == "pass"
    assert states["audio_intelligence"] == "ready"
    assert states["visual_event_intelligence"] == "ready"
    assert len(resumed["event_log"]) == 1


def test_retry_budget_allows_one_retry_then_fails_closed() -> None:
    run = MOD.fail_stage(ROOT, fixture_run(), "normalize_inputs", "TRANSIENT_FAILURE", retryable=True)
    assert run["stages"][0]["state"] == "ready"
    run = MOD.fail_stage(ROOT, run, "normalize_inputs", "TRANSIENT_FAILURE", retryable=True)
    assert run["stages"][0]["state"] == "failed"
    assert run["decision"]["publication_allowed"] is False


def test_cost_budget_rejects_overrun_without_mutation() -> None:
    run = fixture_run()
    with pytest.raises(MOD.AudioOrchestratorError, match="cost_budget_exceeded"):
        MOD.complete_stage(ROOT, run, "normalize_inputs", MOD.stable_hash("normalized"), cost_usd=2.0)


def test_full_synthetic_dag_never_grants_publication() -> None:
    run = fixture_run()
    for stage in run["stages"]:
        run = MOD.complete_stage(ROOT, run, stage["stage_id"], MOD.stable_hash(f"output:{stage['stage_id']}"), cost_usd=0.01)
    assert run["decision"]["status"] == "complete"
    assert run["decision"]["row105_acceptance"] == "fixture_only"
    assert run["decision"]["publication_allowed"] is False
    assert run["decision"]["runtime_completion"] is False


def test_tampered_event_chain_is_rejected() -> None:
    run = MOD.complete_stage(ROOT, fixture_run(), "normalize_inputs", MOD.stable_hash("normalized"))
    mutated = deepcopy(run)
    mutated["event_log"][0]["payload_sha256"] = "a" * 64
    mutated.pop("receipt_sha256")
    mutated = MOD._seal(mutated)
    with pytest.raises(MOD.AudioOrchestratorError, match="event_hash_mismatch"):
        MOD.validate_run(ROOT, mutated)


def test_hold_packet_is_truthful_and_contains_resume_proof() -> None:
    packet = MOD.build_hold_packet(ROOT)
    assert packet["row_complete"] is False
    assert packet["publication_authority"] is False
    assert packet["decision"]["row105_acceptance"] == "held"
    assert packet["fixture_proof"]["idempotent_replay_identical"] is True
