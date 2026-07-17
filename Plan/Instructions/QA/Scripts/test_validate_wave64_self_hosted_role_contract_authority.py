from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_self_hosted_role_contract_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_self_hosted_roles", SCRIPT)
assert SPEC and SPEC.loader
AUTHORITY = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = AUTHORITY; SPEC.loader.exec_module(AUTHORITY)


def fixture(): return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_REGISTRY)
def validate(candidate=None): return AUTHORITY.validate_all(ROOT, candidate or fixture(), AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_SCHEMA))


def test_fixture_passes_without_activation():
    result = validate()
    assert result["classification"] == "WAVE64_SELF_HOSTED_ROLE_CONTRACT_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [201, 202, 203, 204]
    assert result["bounded_role_count"] == 8
    assert result["model_serving_active"] is False
    assert result["role_activation_allowed"] is False
    assert result["production_selection_allowed"] is False


def test_source_hash_drift_fails_closed():
    candidate = fixture(); candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.RoleContractError, match="bound_hash_mismatch:role_card_schema"): validate(candidate)


def test_source_path_escape_fails_closed():
    candidate = fixture(); candidate["source_authorities"][0]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.RoleContractError, match="bound_path_not_relative:role_card_schema"): validate(candidate)


def test_source_names_are_unique():
    candidate = fixture(); candidate["source_authorities"][5]["name"] = "role_card_schema"
    with pytest.raises(AUTHORITY.RoleContractError, match="duplicate_source_authority_name"): validate(candidate)


def test_exact_eight_role_taxonomy_is_required():
    candidate = fixture(); candidate["roles"][0]["role_id"] = "summarizer"
    with pytest.raises(AUTHORITY.RoleContractError, match="role_exact_set_mismatch"): validate(candidate)


@pytest.mark.parametrize("field", ["activated", "direct_execution_authority", "promotion_authority"])
def test_role_cannot_gain_runtime_or_final_authority(field):
    candidate = fixture(); candidate["roles"][0][field] = True
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_role_cannot_bind_unqualified_stack():
    candidate = fixture(); candidate["roles"][0]["stack_ref"] = "stack_unproven"
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_every_role_abstains_or_escalates():
    assert all(role["uncertainty_policy"] == "abstain_or_escalate" for role in fixture()["roles"])


def test_retrieval_requires_all_eight_source_classes():
    candidate = fixture(); candidate["retrieval_contract"]["source_classes"][0] = "evidence"
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_retrieval_requires_immutable_citations():
    candidate = fixture(); candidate["retrieval_contract"]["required_citation_fields"] = ["immutable_id", "revision", "path"]
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_retrieval_cannot_invent_runtime_bundle():
    candidate = fixture(); candidate["retrieval_contract"]["retrieval_bundle_ref"] = "bundle_unproven"
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_stale_missing_and_conflicting_evidence_surface_explicitly():
    contract = fixture()["retrieval_contract"]
    assert contract["stale_evidence_action"] == "surface_and_abstain"
    assert contract["missing_evidence_action"] == "surface_and_abstain"
    assert contract["conflicting_evidence_action"] == "surface_and_escalate"


def test_proposal_requires_all_ten_structured_fields():
    candidate = fixture(); candidate["proposal_contract"]["required_fields"][0] = "confidence"
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_unsupported_ids_and_authority_bypass_reject():
    proposal = fixture()["proposal_contract"]
    assert proposal["unsupported_id_action"] == "reject"
    assert proposal["authority_bypass_action"] == "reject"


def test_fixture_abstains_without_qualified_stack():
    assert fixture()["proposal_contract"]["fixture_decision"] == "abstain_missing_qualified_stack"


def test_qualification_requires_exact_stack_fields():
    candidate = fixture(); candidate["qualification_gate"]["required_stack_fields"][0] = "runtime"
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_qualification_cannot_invent_stack():
    candidate = fixture(); candidate["qualification_gate"]["qualified_stack_refs"] = ["stack_unproven"]
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


@pytest.mark.parametrize("field", ["shadow_mode_allowed", "production_mode_allowed", "health_probe_run", "benchmark_run"])
def test_deferred_gate_forbids_execution_claims(field):
    candidate = fixture(); candidate["qualification_gate"][field] = True
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_false_completion_boundary_is_rejected():
    candidate = fixture(); candidate["boundaries"]["production_role_activated"] = True
    with pytest.raises(AUTHORITY.RoleContractError, match="schema_validation_failed"): validate(candidate)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    evidence = AUTHORITY.build_evidence(ROOT, validate(), AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa, tracker = tmp_path / "qa.json", tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence); AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert not any(evidence["boundaries"].values())
