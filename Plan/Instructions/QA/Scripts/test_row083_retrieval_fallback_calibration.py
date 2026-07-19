from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/calibrate_wave64_retrieval_fallback.py"
SPEC = importlib.util.spec_from_file_location("calibrate_wave64_retrieval_fallback", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {"TRK-W64-081", "TRK-W64-082"}
    for tracker_id in ("TRK-W64-081", "TRK-W64-082"):
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False
        assert admission["row_complete"] is False
        assert admission["blocker_codes"]
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row083_acceptance"] == "held"
    assert "ROW083_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 7
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)
    assert set(payload["required_routes"]) == set(MOD.REQUIRED_ROUTES)


def test_high_confidence_exact_selects_exact():
    record = MOD.extract_fixture_record(ROOT, "high_confidence_exact_selects_exact")
    assert record["decision"]["route"] == "exact_retrieval"
    assert record["decision"]["selected_candidate_id"] == "cand_exact_ok"
    chosen = next(item for item in record["candidates"] if item["candidate_id"] == "cand_exact_ok")
    assert chosen["relevance"] == "exact"
    assert chosen["eligible"] is True
    assert chosen["rank"] == 1
    assert record["calibration_revision"]
    assert record["metric_table_sha256"]


def test_below_exact_routes_to_approximate():
    record = MOD.extract_fixture_record(ROOT, "below_exact_routes_to_approximate")
    assert record["decision"]["route"] == "approximate_retrieval"
    assert record["decision"]["selected_candidate_id"] == "cand_approx_primary"
    assert record["decision"]["route"] != "exact_retrieval"


def test_low_confidence_abstains_not_silent_select():
    record = MOD.extract_fixture_record(ROOT, "low_confidence_abstains_not_silent_select")
    assert record["decision"]["route"] == "abstain"
    assert record["decision"]["selected_candidate_id"] is None
    trap = record["candidates"][0]
    assert trap["eligible"] is False
    assert "BELOW_ROUTE_THRESHOLD" in trap["hard_exclusions"]
    assert "low_confidence_cannot_silently_select" in " ".join(record["decision"]["explanation"])


def test_no_candidates_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "no_candidates_fails_closed")
    assert record["decision"]["route"] == "abstain"
    assert record["decision"]["selected_candidate_id"] is None
    assert record["candidates"] == []
    assert record["decision"]["reason"] == "no_candidates"


def test_sparse_family_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "sparse_family_fails_closed")
    assert record["decision"]["route"] == "review_escalation"
    assert record["decision"]["selected_candidate_id"] is None
    assert record["event_family_metrics"]["support_count"] < 8


def test_missing_metric_table_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "missing_metric_table_fails_closed")
    assert record["decision"]["route"] == "blocked"
    assert record["decision"]["selected_candidate_id"] is None
    assert "MISSING_METRIC_TABLE" in record["candidates"][0]["hard_exclusions"]


def test_generated_fallback_under_calibrated_band():
    record = MOD.extract_fixture_record(ROOT, "generated_fallback_under_calibrated_band")
    assert record["decision"]["route"] == "generated_fallback"
    assert record["decision"]["selected_candidate_id"] == "cand_generated"
    assert 0.55 <= record["calibrated_confidence"] < 0.65


def test_fixture_records_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "high_confidence_exact_selects_exact")
    second = MOD.extract_fixture_record(ROOT, "high_confidence_exact_selects_exact")
    assert first == second
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False


def test_semantic_validator_rejects_abstain_with_selected_candidate():
    record = MOD.extract_fixture_record(ROOT, "low_confidence_abstains_not_silent_select")
    mutated = deepcopy(record)
    mutated["decision"]["selected_candidate_id"] = "cand_silent_trap"
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.RetrievalFallbackError, match="non_select_route_must_null_selection"):
        MOD.validate_calibration_semantics(mutated)


def test_semantic_validator_rejects_exact_with_non_exact_relevance():
    record = MOD.extract_fixture_record(ROOT, "high_confidence_exact_selects_exact")
    mutated = deepcopy(record)
    mutated["candidates"][0]["relevance"] = "approximate"
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(MOD.RetrievalFallbackError, match="exact_route_requires_exact_relevance"):
        MOD.validate_calibration_semantics(mutated)


def test_schema_rejects_missing_calibration_binding_field():
    record = MOD.extract_fixture_record(ROOT, "high_confidence_exact_selects_exact")
    mutated = deepcopy(record)
    del mutated["metric_table_sha256"]
    with pytest.raises(Exception):
        MOD.validate_calibration_record(ROOT, mutated)
