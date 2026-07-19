from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/select_wave64_audio_repetition_diversity.py"
SPEC = importlib.util.spec_from_file_location("select_wave64_audio_repetition_diversity", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {"TRK-W64-074", "TRK-W64-080", "TRK-W64-081"}
    for tracker_id in ("TRK-W64-074", "TRK-W64-080", "TRK-W64-081"):
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
    assert payload["decision"]["row082_acceptance"] == "held"
    assert "ROW082_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_cooldown_blocks_identical_asset_reuse():
    record = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    blocked = next(item for item in record["candidates"] if item["candidate_id"] == "cand_reuse_blocked")
    ok = next(item for item in record["candidates"] if item["candidate_id"] == "cand_alt_ok")
    assert blocked["eligible"] is False
    assert "COOLDOWN_ACTIVE" in blocked["hard_exclusions"]
    assert ok["eligible"] is True
    assert record["decision"]["route"] == "select"
    assert record["decision"]["selected_candidate_id"] == "cand_alt_ok"
    assert record["selection_history_sha256"]
    assert record["resulting_history_sha256"]
    assert record["selection_history_sha256"] != record["resulting_history_sha256"]


def test_near_duplicate_penalty_rotates_to_distinct_candidate():
    record = MOD.extract_fixture_record(ROOT, "near_duplicate_penalty_rotates")
    assert record["decision"]["route"] == "select"
    assert record["decision"]["selected_candidate_id"] == "cand_distinct_rotate"
    hot = next(item for item in record["candidates"] if item["candidate_id"] == "cand_near_dup_hot")
    assert any(p["code"] == "near_duplicate_recent_use" for p in hot["penalties"])
    assert hot["total_score"] < hot["base_score"]


def test_foot_alternation_preserves_expected_side():
    record = MOD.extract_fixture_record(ROOT, "foot_alternation_preserves_order")
    wrong = next(item for item in record["candidates"] if item["candidate_id"] == "cand_right_wrong")
    expected = next(
        item for item in record["candidates"] if item["candidate_id"] == "cand_left_expected"
    )
    assert wrong["eligible"] is False
    assert "ALTERNATION_VIOLATION" in wrong["hard_exclusions"]
    assert expected["eligible"] is True
    assert record["decision"]["selected_candidate_id"] == "cand_left_expected"


def test_missing_history_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "missing_history_fails_closed")
    only = record["candidates"][0]
    assert only["eligible"] is False
    assert "MISSING_SELECTION_HISTORY" in only["hard_exclusions"]
    assert record["decision"]["route"] == "abstain"
    assert record["decision"]["selected_candidate_id"] is None


def test_out_of_bound_transform_rejected():
    record = MOD.extract_fixture_record(ROOT, "out_of_bound_transform_rejected")
    bad = next(item for item in record["candidates"] if item["candidate_id"] == "cand_transform_bad")
    ok = next(item for item in record["candidates"] if item["candidate_id"] == "cand_transform_ok")
    assert bad["eligible"] is False
    assert "TRANSFORM_OUT_OF_BOUNDS" in bad["hard_exclusions"]
    assert ok["eligible"] is True
    assert record["decision"]["selected_candidate_id"] == "cand_transform_ok"


def test_fixture_records_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    second = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    assert first == second
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False


def test_semantic_validator_rejects_eligible_with_hard_exclusion():
    record = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    mutated = deepcopy(record)
    mutated["candidates"][0]["hard_exclusions"] = ["COOLDOWN_ACTIVE"]
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.RepetitionDiversityError, match="eligible_with_hard_exclusions"):
        MOD.validate_selection_semantics(mutated)


def test_semantic_validator_rejects_duplicate_rank():
    record = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    mutated = deepcopy(record)
    mutated["candidates"][1]["rank"] = 1
    mutated["receipt_sha256"] = "c" * 64
    with pytest.raises(MOD.RepetitionDiversityError, match="duplicate_rank"):
        MOD.validate_selection_semantics(mutated)


def test_schema_rejects_missing_history_binding_field():
    record = MOD.extract_fixture_record(ROOT, "cooldown_blocks_identical_reuse")
    mutated = deepcopy(record)
    del mutated["selection_history_sha256"]
    with pytest.raises(Exception):
        MOD.validate_selection_record(ROOT, mutated)
