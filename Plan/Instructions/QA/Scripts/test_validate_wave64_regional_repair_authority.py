from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_regional_repair_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_regional_repair_authority", SCRIPT)
assert SPEC and SPEC.loader
AUTHORITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTHORITY
SPEC.loader.exec_module(AUTHORITY)


def fixture():
    return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_REGISTRY)


def fixture_schema():
    return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_SCHEMA)


def validate(candidate=None):
    return AUTHORITY.validate_all(ROOT, candidate or fixture(), fixture_schema())


def test_live_fixture_is_blocked_and_parent_preserving():
    result = validate()
    assert result["classification"] == "WAVE64_REGIONAL_REPAIR_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [174, 175, 176]
    assert result["runtime_scope"] == "blocked_contract_validation_only"
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["accepted_parent_immutable"] is True
    assert result["protected_scope_count"] == 3
    assert result["repair_changed_variable_count"] == 1
    assert result["remaining_attempt_budget"] == 1
    assert result["reintegration_gate_count"] == 13


def test_source_hash_is_immutable():
    candidate = fixture()
    candidate["source_bridge_evidence"]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="source_hash_mismatch"):
        validate(candidate)


def test_source_path_cannot_escape_project():
    candidate = fixture()
    candidate["source_bridge_evidence"]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="source_path_not_bounded_relative"):
        validate(candidate)


def test_regional_contract_must_bind_accepted_parent():
    candidate = fixture()
    candidate["regional_edit_contract"]["parent_artifact_id"] = "different_parent"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="regional_parent_binding_mismatch"):
        validate(candidate)


def test_regional_execution_cannot_be_enabled():
    candidate = fixture()
    candidate["regional_edit_contract"]["execution_allowed"] = True
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_accepted_parent_cannot_be_mutable():
    candidate = fixture()
    candidate["accepted_parent"]["immutable"] = False
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_regional_denoise_bounds_cannot_invert():
    candidate = fixture()
    candidate["regional_edit_contract"]["denoise_bounds"]["minimum"] = 0.8
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="regional_denoise_bounds_inverted"):
        validate(candidate)


def test_transform_parameters_are_hash_bound():
    candidate = fixture()
    candidate["regional_edit_contract"]["transform"]["parameters"]["scale_x"] = 2.0
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="regional_transform_parameters_hash_mismatch"):
        validate(candidate)


def test_invertible_transform_requires_roundtrip_evidence():
    candidate = fixture()
    candidate["regional_edit_contract"]["transform"]["roundtrip_evidence_id"] = ""
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_unvalidated_mask_binding_cannot_be_claimed():
    candidate = fixture()
    candidate["regional_edit_contract"]["target"]["mask_binding_id"] = "draft_mask"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_mode_b_cannot_become_truth_or_write_gold():
    candidate = fixture()
    candidate["regional_edit_contract"]["mask_authority"]["mode_b_draft_only"] = False
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)
    candidate = fixture()
    candidate["regional_edit_contract"]["mask_authority"]["writes_gold"] = True
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_repair_hypothesis_validates_against_adopted_schema():
    result = validate()
    assert result["repair_changed_variable_count"] == 1


def test_repair_must_bind_to_failed_defect():
    candidate = fixture()
    candidate["repair_hypothesis"]["defect_codes"] = ["UNRELATED_DEFECT"]
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="repair_hypothesis_not_bound_to_failed_defect"):
        validate(candidate)


def test_repair_must_materially_change_prior_variables():
    candidate = fixture()
    candidate["repair_hypothesis"]["changed_variables"] = ["seed"]
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="repair_hypothesis_repeats_prior_variables"):
        validate(candidate)


def test_seed_only_repair_is_forbidden():
    candidate = fixture()
    candidate["prior_failed_attempt"]["changed_variables"] = ["scheduler"]
    candidate["repair_hypothesis"]["changed_variables"] = ["seed"]
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="seed_only_repair_forbidden"):
        validate(candidate)


def test_repair_attempt_budget_is_bounded():
    candidate = fixture()
    candidate["repair_hypothesis"]["remaining_attempt_budget"] = 3
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="repair_attempt_budget_unbounded"):
        validate(candidate)


def test_localized_scope_is_hash_bound():
    candidate = fixture()
    candidate["repair_hypothesis"]["localized_scope_sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="repair_localized_scope_hash_mismatch"):
        validate(candidate)


def test_reintegration_requires_complete_exact_gate_set():
    candidate = fixture()
    candidate["reintegration_gate"]["required_gates"][0] = "wrong_gate"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="reintegration_required_gate_set_mismatch"):
        validate(candidate)


def test_reintegration_results_must_be_complete_and_unique():
    candidate = fixture()
    candidate["reintegration_gate"]["gate_results"][0]["gate"] = "protected_regions"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="reintegration_gate_results_incomplete_or_duplicate"):
        validate(candidate)


def test_reintegration_cannot_claim_unrun_qa():
    candidate = fixture()
    candidate["reintegration_gate"]["gate_results"][0]["status"] = "pass"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_reintegration_cannot_claim_candidate_or_promotion():
    candidate = fixture()
    candidate["reintegration_gate"]["candidate_artifact_id"] = "candidate_fixture"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)
    candidate = fixture()
    candidate["reintegration_gate"]["promotion_transaction_id"] = "promotion_fixture"
    with pytest.raises(AUTHORITY.RegionalRepairAuthorityError, match="schema_validation_failed:regional_repair_authority"):
        validate(candidate)


def test_evidence_outputs_are_exact_compact_mirrors(tmp_path):
    result = validate()
    evidence = AUTHORITY.build_evidence(ROOT, result, AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa = tmp_path / "qa.json"
    tracker = tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence)
    AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert evidence["worker_dispatch"]["fallback"] == "bounded_codex_implementation_and_deterministic_validation"
    assert not any(evidence["boundaries"].values())
