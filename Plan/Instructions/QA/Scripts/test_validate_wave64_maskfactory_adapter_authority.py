from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_maskfactory_adapter_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_maskfactory_adapter_authority", SCRIPT)
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


def test_live_fixture_is_blocked_and_non_mutating():
    result = validate()
    assert result["classification"] == "WAVE64_MASKFACTORY_ADAPTER_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [177, 178, 179, 180]
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["writes_gold"] is False
    assert result["validated_binding_count"] == 2
    assert result["normalized_binding_count"] == 2
    assert result["typed_blocker_condition_count"] == 5


def test_source_evidence_hash_is_immutable():
    candidate = fixture()
    candidate["source_regional_evidence"]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="bound_hash_mismatch:source_regional_evidence"):
        validate(candidate)


def test_bound_paths_cannot_escape_project():
    candidate = fixture()
    candidate["binding_schema"]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="bound_path_not_relative:binding_schema"):
        validate(candidate)


def test_binding_schema_hash_is_immutable():
    candidate = fixture()
    candidate["binding_schema"]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="bound_hash_mismatch:binding_schema"):
        validate(candidate)


def test_mode_a_binding_validates_against_adopted_schema():
    result = validate()
    assert result["mode_a_mask_count"] == 1


def test_mode_b_binding_validates_against_adopted_schema():
    result = validate()
    assert result["mode_b_mask_count"] == 1


def test_mode_b_cannot_escape_machine_draft():
    candidate = fixture()
    candidate["mode_b_binding"]["authority"]["truth_tier"] = "approved_package"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:mode_b_binding"):
        validate(candidate)


def test_mode_b_cannot_satisfy_promotion():
    candidate = fixture()
    candidate["mode_b_binding"]["can_satisfy_promotion_gate"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:mode_b_binding"):
        validate(candidate)


def test_mode_a_without_certificate_cannot_claim_promotion():
    candidate = fixture()
    candidate["mode_a_binding"]["can_satisfy_promotion_gate"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:mode_a_binding"):
        validate(candidate)


def test_bindings_never_write_gold():
    candidate = fixture()
    candidate["mode_a_binding"]["writes_gold"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:mode_a_binding"):
        validate(candidate)


def test_transform_parameters_are_hash_bound():
    candidate = fixture()
    candidate["mode_a_binding"]["transform_chain"][0]["parameters"]["scale_x"] = 2.0
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="binding_transform_hash_mismatch:mode_a"):
        validate(candidate)


def test_mode_b_client_does_not_submit_or_execute():
    candidate = fixture()
    candidate["mode_b_client"]["request_submitted"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_silent_fallback_is_forbidden():
    candidate = fixture()
    candidate["mode_b_client"]["silent_fallback_allowed"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_mode_b_model_and_route_remain_unverified():
    candidate = fixture()
    candidate["mode_b_client"]["champion_model_id"] = "invented_model"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_normalization_preserves_owner():
    candidate = fixture()
    candidate["normalized_bindings"][0]["owner_id"] = "wrong_owner"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="normalized_field_not_preserved:normalized_mode_a_fixture_001:owner_id"):
        validate(candidate)


def test_normalization_preserves_person_index():
    candidate = fixture()
    candidate["normalized_bindings"][0]["person_index"] = 1
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="normalized_field_not_preserved:normalized_mode_a_fixture_001:person_index"):
        validate(candidate)


def test_normalization_preserves_taxonomy_and_provider():
    candidate = fixture()
    candidate["normalized_bindings"][1]["ontology_version"] = "unknown"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="normalized_field_not_preserved:normalized_mode_b_fixture_001:ontology_version"):
        validate(candidate)
    candidate = fixture()
    candidate["normalized_bindings"][1]["provider"] = "unknown"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="normalized_field_not_preserved:normalized_mode_b_fixture_001:provider"):
        validate(candidate)


def test_normalization_preserves_transform_digest():
    candidate = fixture()
    candidate["normalized_bindings"][0]["transform_chain_sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="normalized_field_not_preserved:normalized_mode_a_fixture_001:transform_chain_sha256"):
        validate(candidate)


def test_normalized_binding_cannot_claim_promotion():
    candidate = fixture()
    candidate["normalized_bindings"][0]["promotion_ready"] = True
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_weaker_mode_b_cannot_overwrite_stronger_mode_a():
    candidate = fixture()
    candidate["arbitration"]["selected_normalized_id"] = "normalized_mode_b_fixture_001"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="weaker_authority_overwrite_attempt"):
        validate(candidate)


def test_arbitration_candidates_must_match_normalized_set():
    candidate = fixture()
    candidate["arbitration"]["candidate_ids"][1] = "unknown_candidate"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="arbitration_candidate_set_mismatch"):
        validate(candidate)


def test_derivation_preserves_exact_parent_hash_lineage():
    candidate = fixture()
    candidate["derivation"]["parent_mask_sha256s"][0] = "d" * 64
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="derivation_parent_hash_set_mismatch"):
        validate(candidate)


def test_derived_output_cannot_inflate_authority():
    candidate = fixture()
    candidate["derivation"]["output_truth_tier"] = "approved_package"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_availability_matrix_requires_exact_typed_conditions():
    candidate = fixture()
    candidate["availability_gate"]["blocker_matrix"][0]["condition"] = "unknown_condition"
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="availability_blocker_matrix_mismatch"):
        validate(candidate)


def test_dependent_blocker_cannot_block_unrelated_dag_branches():
    candidate = fixture()
    candidate["availability_gate"]["blocker_matrix"][0]["unrelated_branches_continue"] = False
    with pytest.raises(AUTHORITY.MaskFactoryAdapterAuthorityError, match="schema_validation_failed:maskfactory_adapter_authority"):
        validate(candidate)


def test_availability_gate_retains_parent_and_blocks_execution():
    gate = fixture()["availability_gate"]
    assert gate["accepted_parent_retained"] is True
    assert gate["execution_allowed"] is False
    assert gate["promotion_allowed"] is False
    assert gate["unrelated_dag_branches_allowed"] is True


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    result = validate()
    evidence = AUTHORITY.build_evidence(ROOT, result, AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa = tmp_path / "qa.json"
    tracker = tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence)
    AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert evidence["future_rows321_348_package"]["adopted"] is False
    assert not any(evidence["boundaries"].values())
