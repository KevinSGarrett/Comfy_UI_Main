from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/rank_wave64_explainable_audio_candidates.py"
SPEC = importlib.util.spec_from_file_location("rank_wave64_explainable_audio_candidates", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-072",
        "TRK-W64-076",
        "TRK-W64-079",
        "TRK-W64-080",
    }
    # Row068 rights authority is accepted on this branch; remaining deps stay held.
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-068"]["row_complete"] is True
    for tracker_id in ("TRK-W64-072", "TRK-W64-076", "TRK-W64-079", "TRK-W64-080"):
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
    assert payload["decision"]["row081_acceptance"] == "held"
    assert "ROW081_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 4
    assert set(payload["required_components"]) == set(MOD.REQUIRED_COMPONENTS)


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    second = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    assert first == second
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["decision"]["route"] == "select"
    assert first["decision"]["selected_candidate_id"] == "cand_a_best"
    assert first["candidates"][0]["rank"] == 1
    assert first["candidates"][0]["candidate_id"] == "cand_a_best"
    assert len(first["candidates"][0]["components"]) == 14
    assert first["candidates"][0]["explanation"]


def test_tie_break_is_deterministic_on_equal_scores():
    record = MOD.extract_fixture_record(ROOT, "tie_break_by_candidate_id")
    assert record["decision"]["route"] == "select"
    assert record["decision"]["selected_candidate_id"] == "cand_a_tie"
    assert record["decision"]["tie_break_outcome"]["applied"] is True
    assert record["candidates"][0]["candidate_id"] == "cand_a_tie"


def test_hard_exclusion_runs_before_weighted_ranking():
    record = MOD.extract_fixture_record(ROOT, "hard_exclude_rights")
    bad = next(item for item in record["candidates"] if item["candidate_id"] == "cand_rights_bad")
    good = next(item for item in record["candidates"] if item["candidate_id"] == "cand_rights_ok")
    assert bad["eligible"] is False
    assert "RIGHTS_INELIGIBLE" in bad["hard_exclusions"]
    assert bad["total_score"] == -1.0
    assert good["eligible"] is True
    assert record["decision"]["selected_candidate_id"] == "cand_rights_ok"


def test_missing_mandatory_feature_abstains():
    record = MOD.extract_fixture_record(ROOT, "missing_mandatory_abstain")
    assert record["decision"]["route"] == "abstain"
    assert record["decision"]["selected_candidate_id"] is None
    only = record["candidates"][0]
    assert only["eligible"] is False
    assert "MISSING_MANDATORY_FEATURE" in only["hard_exclusions"]


def test_semantic_validator_rejects_eligible_with_hard_exclusion():
    record = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    mutated = deepcopy(record)
    mutated["candidates"][0]["hard_exclusions"] = ["RIGHTS_INELIGIBLE"]
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.ExplainableRankingError, match="eligible_with_hard_exclusions"):
        MOD.validate_ranking_semantics(mutated)


def test_semantic_validator_rejects_nonexistent_selection():
    record = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    mutated = deepcopy(record)
    mutated["decision"]["selected_candidate_id"] = "does_not_exist"
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(MOD.ExplainableRankingError, match="selected_candidate_missing"):
        MOD.validate_ranking_semantics(mutated)


def test_semantic_validator_rejects_duplicate_rank():
    record = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    mutated = deepcopy(record)
    mutated["candidates"][1]["rank"] = 1
    mutated["receipt_sha256"] = "c" * 64
    with pytest.raises(MOD.ExplainableRankingError, match="duplicate_rank"):
        MOD.validate_ranking_semantics(mutated)


def test_schema_rejects_empty_candidate_explanation():
    record = MOD.extract_fixture_record(ROOT, "select_clear_winner")
    mutated = deepcopy(record)
    mutated["candidates"][0]["explanation"] = []
    with pytest.raises(Exception):
        MOD.validate_ranking_record(ROOT, mutated)
