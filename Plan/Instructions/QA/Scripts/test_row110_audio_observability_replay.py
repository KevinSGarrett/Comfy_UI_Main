from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/record_replay_wave64_audio_observability.py"
SPEC = importlib.util.spec_from_file_location("record_replay_wave64_audio_observability", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_complete_fixture_replays_deterministically():
    first = MOD.fixture_ledger(ROOT)
    second = MOD.fixture_ledger(ROOT)
    assert first == second
    assert first["recorded_projection"]["reconstructable"] is True
    assert first["decision"]["row110_acceptance"] == "fixture_only"
    assert first["decision"]["release_authority"] is False


def test_projection_contains_ranking_rejection_transform_and_qa():
    projection = MOD.fixture_ledger(ROOT)["recorded_projection"]
    assert projection["ranked_candidate_ids"] == ["candidate-a", "candidate-b"]
    assert projection["rejected_candidate_ids"] == ["candidate-b"]
    assert projection["transform_sha256s"] == [MOD.stable_hash("transform")]
    assert projection["qa_evidence_sha256s"] == [MOD.stable_hash("qa")]
    assert projection["cache_hits"] == 1


def test_event_append_is_nonmutating_and_duplicate_id_rejected():
    ledger = MOD.new_ledger("x", synthetic=True)
    appended = MOD.append_event(ledger, "e1", "stage_timing", {"duration_ms": 1})
    assert ledger["events"] == []
    assert len(appended["events"]) == 1
    with pytest.raises(MOD.AudioObservabilityError, match="duplicate_event_id"):
        MOD.append_event(appended, "e1", "stage_timing", {"duration_ms": 2})


def test_sealed_ledger_is_immutable():
    ledger = MOD.fixture_ledger(ROOT)
    with pytest.raises(MOD.AudioObservabilityError, match="sealed_ledger_is_immutable"):
        MOD.append_event(ledger, "late", "retry", {"attempt": 2})


@pytest.mark.parametrize("field", ["sequence", "previous_event_sha256", "payload_sha256", "event_sha256"])
def test_chain_tampering_rejected(field: str):
    ledger = MOD.fixture_ledger(ROOT)
    event = deepcopy(ledger["events"][1])
    event[field] = 99 if field == "sequence" else "a" * 64
    events = deepcopy(ledger["events"])
    events[1] = event
    with pytest.raises(MOD.AudioObservabilityError):
        MOD.replay(events)


def test_payload_tampering_rejected():
    events = deepcopy(MOD.fixture_ledger(ROOT)["events"])
    events[0]["payload"]["duration_ms"] = 999
    with pytest.raises(MOD.AudioObservabilityError, match="payload_sha256_mismatch"):
        MOD.replay(events)


def test_missing_required_event_type_blocks_reconstructability():
    events = [event for event in MOD.fixture_ledger(ROOT)["events"] if event["event_type"] != "qa_score"]
    ledger = MOD.new_ledger("missing-qa", synthetic=True)
    for event in events:
        ledger = MOD.append_event(ledger, event["event_id"], event["event_type"], event["payload"])
    sealed = MOD.seal_ledger(ROOT, ledger, release_authority=False)
    assert sealed["recorded_projection"]["reconstructable"] is False
    assert "MISSING_EVENT_TYPE_QA_SCORE" in sealed["decision"]["blocker_codes"]


def test_synthetic_release_authority_forbidden():
    unsealed = MOD.new_ledger("release", synthetic=True)
    for event in MOD.fixture_ledger(ROOT)["events"]:
        unsealed = MOD.append_event(unsealed, event["event_id"], event["event_type"], event["payload"])
    with pytest.raises(MOD.AudioObservabilityError, match="release_authority_requirements_unsatisfied"):
        MOD.seal_ledger(ROOT, unsealed, release_authority=True)


def test_external_blocker_prevents_release():
    unsealed = MOD.new_ledger("blocked-release", synthetic=False)
    for event in MOD.fixture_ledger(ROOT)["events"]:
        unsealed = MOD.append_event(unsealed, event["event_id"], event["event_type"], event["payload"])
    unsealed = MOD.append_event(unsealed, "blocker", "external_blocker", {"blocker_code": "MISSING_RIGHTS"})
    with pytest.raises(MOD.AudioObservabilityError, match="release_authority_requirements_unsatisfied"):
        MOD.seal_ledger(ROOT, unsealed, release_authority=True)


def test_recorded_projection_mismatch_rejected():
    ledger = MOD.fixture_ledger(ROOT)
    ledger["recorded_projection"]["cache_hits"] = 99
    ledger["ledger_sha256"] = MOD.digest({key: value for key, value in ledger.items() if key != "ledger_sha256"})
    with pytest.raises(MOD.AudioObservabilityError, match="recorded_projection_replay_mismatch"):
        MOD.validate_ledger(ROOT, ledger)


def test_ledger_digest_tampering_rejected():
    ledger = MOD.fixture_ledger(ROOT)
    ledger["ledger_sha256"] = "a" * 64
    with pytest.raises(MOD.AudioObservabilityError, match="ledger_sha256_mismatch"):
        MOD.validate_ledger(ROOT, ledger)


def test_dependencies_are_hash_bound_and_held():
    admissions = MOD.dependency_admissions(ROOT)
    assert set(admissions) == set(MOD.DEPENDENCY_DELTAS)
    assert all(len(value["sha256"]) == 64 for value in admissions.values())
    assert not any(value["dependency_satisfied"] for value in admissions.values())


def test_evidence_truthfully_holds_genuine_replay():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["fixture_replay"]["recorded_projection"]["reconstructable"] is True
    assert evidence["live_blocker_ledger"]["recorded_projection"]["external_blocker_codes"] == ["ROW110_DEPENDENCIES_NOT_ACCEPTED"]
