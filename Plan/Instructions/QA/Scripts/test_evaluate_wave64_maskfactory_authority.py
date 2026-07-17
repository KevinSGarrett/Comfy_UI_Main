from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_maskfactory_authority.py"


@pytest.fixture(scope="module")
def authority():
    spec = importlib.util.spec_from_file_location("evaluate_wave64_maskfactory_authority_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("authority evaluator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def examples(authority):
    return copy.deepcopy(authority.CORE.build_examples())


def fixture_decision_inputs(authority):
    records = examples(authority)
    request = records["maskfactory_bridge_request_v2.example.json"]
    result = records["maskfactory_bridge_result_v2.example.json"]
    policy = records["maskfactory_promotion_gate_policy_v2.example.json"]
    observations = {
        criterion["criterion_id"]: {
            "observed": 0.0 if criterion["comparator"] == "lte" else 0,
            "evidence_ref": authority.CORE.ref(
                "criterion_evidence", f"{criterion['criterion_id']}_fixture", "7"
            ),
        }
        for criterion in policy["criteria"]
    }
    decision_evidence = [authority.CORE.ref("authority_decision_evidence", "fixture_decision", "5")]
    return request, result, policy, observations, decision_evidence


def fixture_invalidation_state(authority, event):
    transition = event["target_transitions"][0]
    affected = {
        "target_kind": transition["target_kind"],
        "target_id": transition["target_id"],
        "target_sha256": transition["target_sha256"],
        "scope_sha256": transition["scope_sha256"],
        "authority_state": transition["previous_authority_state"],
        "certificate_status": transition["previous_certificate_status"],
        "cache_state": "fresh",
        "dependent_pass_ids": ["dependent_pass_001"],
        "branch_id": "branch_affected",
    }
    unrelated = {
        "target_kind": "artifact",
        "target_id": "unrelated_artifact_001",
        "target_sha256": "4" * 64,
        "scope_sha256": "5" * 64,
        "authority_state": "qa_passed_noncertified",
        "certificate_status": "none",
        "cache_state": "fresh",
        "dependent_pass_ids": ["unrelated_pass_001"],
        "branch_id": "branch_unrelated",
    }
    return {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_authority_runtime_state",
        "targets": [affected, unrelated],
        "tombstones": [],
        "unrelated_branch_ids": ["branch_unrelated"],
        "applied_event_refs": [],
        "runtime_completion_claimed": False,
    }


def test_frozen_crosswalk_is_complete_and_human_anchor_optional(authority):
    report = authority.validate_authority_crosswalks()
    assert report["classification"] == "MASKFACTORY_AUTHORITY_CROSSWALK_FROZEN"
    assert report["access_mode_authority_matrix_count"] == 15
    assert report["human_anchor_required_for_core"] is False


@pytest.mark.parametrize("field", ["access_modes", "authority_states", "issuer_kinds", "claim_classes"])
def test_unknown_or_missing_vocabulary_fails_closed(authority, field):
    crosswalk = authority.strict_json(authority.AUTHORITY_CROSSWALK_PATH)
    crosswalk[field] = [*crosswalk[field], "invented_value"]
    with pytest.raises(ValueError, match="vocabulary drift"):
        authority.validate_authority_crosswalks(authority_crosswalk=crosswalk)


def test_access_mode_or_state_alone_never_promotes(authority):
    crosswalk = authority.strict_json(authority.AUTHORITY_CROSSWALK_PATH)
    crosswalk["matrix"][0]["promotion_eligible_by_state_alone"] = True
    with pytest.raises(ValueError, match="cannot authorize promotion"):
        authority.validate_authority_crosswalks(authority_crosswalk=crosswalk)


def test_operational_certificate_never_becomes_accuracy_or_training_gold(authority):
    crosswalk = authority.strict_json(authority.AUTHORITY_CROSSWALK_PATH)
    crosswalk["operational_claim_firewall"]["counts_as_training_gold"] = True
    with pytest.raises(ValueError, match="firewall"):
        authority.validate_authority_crosswalks(authority_crosswalk=crosswalk)


def test_legacy_strings_and_live_dial_are_non_authoritative(authority):
    legacy = authority.strict_json(authority.LEGACY_CROSSWALK_PATH)
    legacy["live_qa_dial_can_mutate_core_decision"] = True
    with pytest.raises(ValueError, match="legacy string or live QA"):
        authority.validate_authority_crosswalks(legacy_crosswalk=legacy)


def test_fixture_result_without_certificate_validates_nonproduction_only(authority):
    result = examples(authority)["maskfactory_bridge_result_v2.example.json"]
    report = authority.verify_result_certificate(result, None, production_required=False)
    assert report["certificate_present"] is False
    assert report["production_authority_verified"] is False
    with pytest.raises(ValueError, match="fixture|production"):
        authority.verify_result_certificate(result, None, production_required=True)


def test_certificate_presence_must_match_certified_result(authority):
    records = examples(authority)
    with pytest.raises(ValueError):
        authority.verify_result_certificate(
            records["maskfactory_bridge_result_v2.example.json"],
            records["maskfactory_operational_certificate_v2.example.json"],
            production_required=False,
        )


def test_fixture_decision_recomputes_policy_but_remains_diagnostic(authority):
    request, result, policy, observations, decision_evidence = fixture_decision_inputs(authority)
    decision = authority.derive_authority_decision(
        request,
        result,
        policy,
        observations,
        decision_evidence_refs=decision_evidence,
    )
    assert decision["decision"] == "diagnostic_only"
    assert decision["eligible_for_intended_use"] is False
    assert decision["fixture_only"] is True
    assert all(item["status"] == "pass" for item in decision["criterion_evaluations"])
    assert decision["observed_authority"]["authority_state"] == "draft"


def test_policy_observations_must_exactly_cover_unique_signed_criteria(authority):
    request, result, policy, observations, decision_evidence = fixture_decision_inputs(authority)
    observations.pop(next(iter(observations)))
    with pytest.raises(ValueError, match="exactly cover"):
        authority.derive_authority_decision(
            request,
            result,
            policy,
            observations,
            decision_evidence_refs=decision_evidence,
        )


def test_criterion_status_is_derived_not_caller_supplied(authority):
    request, result, policy, observations, decision_evidence = fixture_decision_inputs(authority)
    criterion_id = policy["criteria"][0]["criterion_id"]
    observations[criterion_id]["observed"] = 999.0
    decision = authority.derive_authority_decision(
        request,
        result,
        policy,
        observations,
        decision_evidence_refs=decision_evidence,
    )
    status = {item["criterion_id"]: item["status"] for item in decision["criterion_evaluations"]}
    assert status[criterion_id] == "fail"
    assert decision["eligible_for_intended_use"] is False


def test_fixture_cannot_request_promotion_or_become_eligible(authority):
    request, result, policy, observations, decision_evidence = fixture_decision_inputs(authority)
    request["intended_use"] = "promotion_bound"
    request["production_promotion_requested"] = True
    with pytest.raises(ValueError):
        authority.derive_authority_decision(
            request,
            result,
            policy,
            observations,
            decision_evidence_refs=decision_evidence,
        )


def test_invalidation_demotes_only_exact_target_and_writes_tombstone(authority):
    event = examples(authority)["maskfactory_invalidation_event_v2.example.json"]
    state = fixture_invalidation_state(authority, event)
    unrelated_before = copy.deepcopy(state["targets"][1])
    updated = authority.apply_invalidation_event(state, event)
    assert updated["targets"][0]["authority_state"] == event["target_transitions"][0]["new_authority_state"]
    assert updated["targets"][0]["cache_state"] == "tombstoned"
    assert updated["targets"][1] == unrelated_before
    assert len(updated["tombstones"]) == 1
    assert updated["tombstones"][0]["reason"] == event["reason"]
    assert state["tombstones"] == []


def test_invalidation_replay_is_idempotent(authority):
    event = examples(authority)["maskfactory_invalidation_event_v2.example.json"]
    state = fixture_invalidation_state(authority, event)
    once = authority.apply_invalidation_event(state, event)
    twice = authority.apply_invalidation_event(once, event)
    assert twice == once


@pytest.mark.parametrize("field", ["target_sha256", "scope_sha256", "authority_state", "certificate_status"])
def test_invalidation_predecessor_binding_mismatch_fails_closed(authority, field):
    event = examples(authority)["maskfactory_invalidation_event_v2.example.json"]
    state = fixture_invalidation_state(authority, event)
    state["targets"][0][field] = "0" * 64 if field.endswith("sha256") else "invalid"
    with pytest.raises(ValueError, match="predecessor mismatch"):
        authority.apply_invalidation_event(state, event)


def test_invalidation_cannot_target_unknown_or_duplicate_state(authority):
    event = examples(authority)["maskfactory_invalidation_event_v2.example.json"]
    state = fixture_invalidation_state(authority, event)
    state["targets"][0]["target_id"] = "different_target"
    with pytest.raises(ValueError, match="absent"):
        authority.apply_invalidation_event(state, event)
    state = fixture_invalidation_state(authority, event)
    state["targets"].append(copy.deepcopy(state["targets"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        authority.apply_invalidation_event(state, event)

