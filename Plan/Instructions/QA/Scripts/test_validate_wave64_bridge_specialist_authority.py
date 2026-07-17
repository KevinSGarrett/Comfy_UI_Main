from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_bridge_specialist_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_bridge_specialist_authority", SCRIPT)
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


def source(candidate=None):
    candidate = candidate or fixture()
    return AUTHORITY.load_source_route(ROOT, candidate["source_route_evidence"])


def test_live_authority_is_blocked_contract_compilation_only():
    result = validate()
    assert result["classification"] == "WAVE64_BRIDGE_SPECIALIST_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [169, 170, 171, 172, 173]
    assert result["runtime_scope"] == "blocked_contract_compilation_only"
    assert result["runtime_execution_allowed"] is False
    assert result["production_bridge_certified"] is False
    assert result["first_pass_candidate_count"] == 4
    assert result["downstream_bridge_need_count"] == 5
    assert result["bridge_transfer_object_count"] == 2
    assert result["bridge_transform_count"] == 1
    assert result["conditioning_translation_count"] == 9
    assert result["qualification_metric_count"] == 6
    assert result["specialist_catalog_count"] == 11
    assert result["blocked_specialist_contract_count"] == 11


def test_source_route_hash_is_immutable():
    candidate = fixture()
    candidate["source_route_evidence"]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="source_route_hash_mismatch"):
        validate(candidate)


def test_source_route_path_cannot_escape_project():
    candidate = fixture()
    candidate["source_route_evidence"]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="source_route_path_not_bounded_relative"):
        validate(candidate)


def test_intent_classifier_requires_exact_objective_dimensions():
    candidate = fixture()
    candidate["intent_classification"]["objective_dimensions"].remove("downstream_specialists")
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="intent_objective_dimension_set_mismatch"):
        validate(candidate)


def test_intent_candidates_must_match_source_route_candidates():
    candidate = fixture()
    candidate["intent_classification"]["candidate_stack_ids"].pop()
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="intent_candidate_stack_set_mismatch"):
        validate(candidate)


def test_first_pass_stack_cannot_be_hardcoded_or_selected():
    candidate = fixture()
    candidate["intent_classification"]["selected_first_pass_stack_id"] = candidate["intent_classification"]["candidate_stack_ids"][0]
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="selected_first_pass_stack_id"):
        validate(candidate)


def test_flux_is_one_candidate_not_the_classifier_default():
    classification = fixture()["intent_classification"]
    assert classification["selected_first_pass_stack_id"] is None
    assert len(classification["candidate_stack_ids"]) > 1
    assert sum("flux" in stack_id for stack_id in classification["candidate_stack_ids"]) == 1


def test_bridge_stacks_must_come_from_source_route():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["target_execution_stack_id"] = "unknown_stack"
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="bridge_stack_not_evaluated"):
        validate(candidate)


def test_bridge_requires_decoded_image_and_metadata_manifest():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["transfer_objects"].pop()
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="decoded_bridge_required_transfer_missing"):
        validate(candidate)


def test_cross_family_latent_transfer_is_rejected():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["transfer_objects"][0]["transfer_type"] = "cross_family_latent"
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:decoded_bridge_contract.*cross_family_latent"):
        validate(candidate)


def test_all_forbidden_transfer_classes_remain_declared():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["forbidden_transfer_objects"].remove("adapter_weight")
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:decoded_bridge_contract:forbidden_transfer_objects"):
        validate(candidate)


def test_bridge_metadata_payload_is_hash_bound():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["transfer_objects"][1]["media_metadata"]["payload"]["color_space"] = "display_p3"
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="bridge_metadata_hash_mismatch"):
        validate(candidate)


def test_bridge_transform_parameters_are_hash_bound():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["transform_chain"][0]["operations"][0]["parameters"]["scale_x"] = 2
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="bridge_transform_parameters_hash_mismatch"):
        validate(candidate)


def test_invertible_transform_requires_roundtrip_evidence():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["transform_chain"][0]["operations"][0]["roundtrip_evidence_id"] = None
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="bridge_invertible_transform_missing_roundtrip_evidence"):
        validate(candidate)


def test_bridge_cannot_claim_execution_or_compatibility_certificate():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["execution_allowed"] = True
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:decoded_bridge_contract:execution_allowed"):
        validate(candidate)


def test_bridge_requires_ownership_propagation():
    candidate = fixture()
    candidate["decoded_bridge_contract"]["ownership_propagation"] = []
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="bridge_ownership_propagation_missing"):
        validate(candidate)


def test_conditioning_translation_semantics_are_complete_and_unique():
    candidate = fixture()
    candidate["conditioning_translations"].pop()
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority:conditioning_translations"):
        validate(candidate)


def test_raw_conditioning_values_cannot_be_blindly_copied():
    candidate = fixture()
    candidate["conditioning_translations"][0]["raw_value_copy_allowed"] = True
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority"):
        validate(candidate)


def test_conditioning_translation_ids_are_unique():
    candidate = fixture()
    candidate["conditioning_translations"][1]["translation_id"] = candidate["conditioning_translations"][0]["translation_id"]
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="duplicate_conditioning_translation_id"):
        validate(candidate)


def test_qualification_metrics_are_complete():
    candidate = fixture()
    candidate["qualification_gate"]["metric_results"].pop()
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority:qualification_gate.metric_results"):
        validate(candidate)


def test_qualification_cannot_claim_unmeasured_results():
    candidate = fixture()
    candidate["qualification_gate"]["metric_results"][0]["status"] = "pass"
    candidate["qualification_gate"]["metric_results"][0]["evidence_ids"] = ["fake_evidence"]
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority:qualification_gate.metric_results.0"):
        validate(candidate)


def test_qualification_cannot_issue_certificate_or_execute():
    candidate = fixture()
    candidate["qualification_gate"]["certificate_id"] = "fake_certificate"
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority"):
        validate(candidate)


def test_specialist_catalog_is_complete_and_unique():
    candidate = fixture()
    candidate["specialist_catalog"].pop()
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority:specialist_catalog"):
        validate(candidate)


def test_specialist_catalog_cannot_name_uncertified_eligible_stack():
    candidate = fixture()
    candidate["specialist_catalog"][0]["eligible_exact_stack_ids"] = ["stack_template_flux2_dev_global_v1"]
    with pytest.raises(AUTHORITY.BridgeAuthorityError, match="schema_validation_failed:bridge_specialist_authority"):
        validate(candidate)


def test_generated_specialist_contracts_are_non_executable_and_non_promotable():
    contracts = validate()["specialist_contracts"]
    assert {contract["pass_intent"] for contract in contracts} == AUTHORITY.REQUIRED_SPECIALISTS
    assert all(contract["compilation_status"] == "blocked_no_certified_bundle" for contract in contracts)
    assert all(contract["selected_execution_stack_id"] is None for contract in contracts)
    assert all(contract["attempt_plan"] == [] for contract in contracts)
    assert all(contract["promotion_policy"] == "not_promotable" for contract in contracts)
    assert all(contract["parent_artifact_ids"] == [fixture()["accepted_parent_artifact_id"]] for contract in contracts)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    result = validate()
    evidence = AUTHORITY.build_evidence(ROOT, result, AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa = tmp_path / "qa.json"
    tracker = tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence)
    AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert "specialist_contracts" not in evidence
    assert evidence["specialist_contracts_sha256"] == AUTHORITY.canonical_sha256(result["specialist_contracts"])
    assert evidence["boundaries"] == {
        "first_pass_stack_selected": False,
        "bridge_executed": False,
        "conditioning_translation_executed": False,
        "bridge_certificate_issued": False,
        "specialist_pass_executed": False,
        "model_library_gate_changed": False,
        "accepted_parent_mutated": False,
        "item_tracker_status_changed": False,
    }
