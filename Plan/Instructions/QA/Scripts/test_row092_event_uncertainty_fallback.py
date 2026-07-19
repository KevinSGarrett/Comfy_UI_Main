from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_event_uncertainty_fallback.py"
SPEC = importlib.util.spec_from_file_location("compile_wave64_event_uncertainty_fallback", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admission_fail_closed_on_row091_hold():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {"TRK-W64-091"}
    admission = admissions["TRK-W64-091"]
    assert admission["dependency_satisfied"] is False
    assert admission["row_complete"] is False
    assert admission["blocker_codes"]


def test_hold_packet_refuses_false_completion():
    payload = MOD.build_hold_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["production_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row092_acceptance"] == "held"
    assert "ROW092_DEPENDENCY_ROW091_NOT_ACCEPTED" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_adversarial_self_declared_certification_blocked():
    record = MOD.extract_fixture_record(
        ROOT, "adversarial_self_declared_certification_blocked"
    )
    assert record["declared_authority_ceiling"] == "certification"
    assert record["derived_authority_ceiling"] == "candidate"
    assert "SELF_DECLARED_CERTIFICATION_REJECTED" in record["fallback_reason_codes"]
    assert "NULL_OWNERSHIP" in record["fallback_reason_codes"]
    assert "UNKNOWN_MATERIAL" in record["fallback_reason_codes"]
    assert "EMPTY_EVIDENCE" in record["fallback_reason_codes"]
    assert record["decision"]["status"] == "blocked"
    assert record["fallback_route"] == "blocked"
    assert record["production_authority"] is False


def test_detector_conflict_preserves_all_votes():
    record = MOD.extract_fixture_record(ROOT, "detector_conflict_preserves_votes")
    assert record["conflict_record"]["conflict_present"] is True
    assert record["conflict_record"]["preserved_vote_count"] == 2
    assert len(record["detector_votes"]) == 2
    assert record["conflict_record"]["selected_detector_name"] == "contact_detector"
    assert "DETECTOR_CONFLICT" in record["fallback_reason_codes"]
    assert "detector_disagreement" in record["uncertainty"]["sources"]
    assert record["derived_authority_ceiling"] in {"candidate", "technical"}


def test_unknown_material_never_certifies():
    record = MOD.extract_fixture_record(ROOT, "unknown_material_routes_fallback")
    assert "UNKNOWN_MATERIAL" in record["fallback_reason_codes"]
    assert record["derived_authority_ceiling"] == "candidate"
    assert record["fallback_route"] in {"broader_retrieval", "blocked", "generated_candidate"}
    assert record["declared_authority_ceiling"] == "certification"
    assert "SELF_DECLARED_CERTIFICATION_REJECTED" in record["fallback_reason_codes"]


def test_offscreen_intentional_silence_route():
    record = MOD.extract_fixture_record(ROOT, "offscreen_event_intentional_silence")
    assert record["scene_flags"]["offscreen"] is True
    assert record["scene_flags"]["intentionally_silent"] is True
    assert "OFFSCREEN" in record["fallback_reason_codes"]
    assert "INTENTIONAL_SILENCE" in record["fallback_reason_codes"]
    assert record["fallback_route"] == "intentional_silence"
    assert record["decision"]["status"] == "intentional_silence"
    assert record["derived_authority_ceiling"] == "candidate"


def test_occluded_contact_caps_at_candidate():
    record = MOD.extract_fixture_record(ROOT, "occluded_contact_candidate_only")
    assert record["scene_flags"]["occlusion"] is True
    assert "OCCLUSION" in record["fallback_reason_codes"]
    assert "AMBIGUOUS_ONSET" in record["fallback_reason_codes"]
    assert record["derived_authority_ceiling"] == "candidate"
    assert record["decision"]["sync_class"] in {"windowed", "multi_anchor", "none"}
    assert "SELF_DECLARED_CERTIFICATION_REJECTED" in record["fallback_reason_codes"]


def test_fixture_records_are_deterministic():
    first = MOD.extract_fixture_record(
        ROOT, "adversarial_self_declared_certification_blocked"
    )
    second = MOD.extract_fixture_record(
        ROOT, "adversarial_self_declared_certification_blocked"
    )
    assert first == second
    assert first["receipt_sha256"]
    assert first["observation_sha256"]


def test_semantic_validator_rejects_missing_self_declared_rejection():
    record = MOD.extract_fixture_record(
        ROOT, "adversarial_self_declared_certification_blocked"
    )
    mutated = deepcopy(record)
    mutated["fallback_reason_codes"] = [
        code
        for code in mutated["fallback_reason_codes"]
        if code != "SELF_DECLARED_CERTIFICATION_REJECTED"
    ]
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(
        MOD.EventUncertaintyFallbackError, match="self_declared_certification_not_rejected"
    ):
        MOD.validate_decision_record(ROOT, mutated)


def test_semantic_validator_rejects_vote_drop():
    record = MOD.extract_fixture_record(ROOT, "detector_conflict_preserves_votes")
    mutated = deepcopy(record)
    mutated["detector_votes"] = mutated["detector_votes"][:1]
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(
        MOD.EventUncertaintyFallbackError, match="conflict_vote_preservation_mismatch"
    ):
        MOD.validate_decision_record(ROOT, mutated)
