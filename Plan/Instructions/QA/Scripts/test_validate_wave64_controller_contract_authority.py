from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_controller_contract_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_controller_contract_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def registry():
    return VALIDATOR.load_json(ROOT / VALIDATOR.DEFAULT_REGISTRY)


def schema():
    return VALIDATOR.load_json(ROOT / VALIDATOR.DEFAULT_SCHEMA)


def test_live_registry_passes_all_synthetic_contract_gates():
    result = VALIDATOR.validate_all(ROOT, registry(), schema())
    assert result["classification"] == "WAVE64_CONTROLLER_CONTRACT_SLICE_PASS"
    assert result["rows_covered"] == [149, 150, 151, 152, 153]
    assert result["reserved_row_count"] == 172
    assert result["item_id_count"] == 172
    assert result["tracker_id_count"] == 172
    assert result["runtime_completion_claimed"] is False


def test_record_type_cannot_have_multiple_component_owners():
    candidate = registry()
    candidate["component_responsibilities"][1]["owns_record_types"].append("program_charter")
    with pytest.raises(VALIDATOR.ContractValidationError, match="record_type_has_multiple_owners"):
        VALIDATOR.validate_components_and_authority(candidate)


def test_llm_or_vlm_cannot_be_final_authority():
    candidate = registry()
    candidate["component_responsibilities"].append({
        "component_id": "llm",
        "responsibility": "Synthetic negative fixture",
        "owns_record_types": ["llm_negative_fixture"],
        "forbidden_authorities": [],
    })
    candidate["decision_authority_matrix"][4]["final_authority"] = "llm"
    with pytest.raises(VALIDATOR.ContractValidationError, match="llm_vlm_or_ui_final_authority_forbidden"):
        VALIDATOR.validate_components_and_authority(candidate)


def test_component_forbidden_authority_is_enforced():
    candidate = registry()
    candidate["decision_authority_matrix"][4]["final_authority"] = "governance_authority"
    with pytest.raises(VALIDATOR.ContractValidationError, match="component_forbidden_final_authority"):
        VALIDATOR.validate_components_and_authority(candidate)


def test_namespace_overlap_fails_closed_before_sidecar_acceptance():
    candidate = registry()
    candidate["namespace_reservations"][1]["first_row"] = 220
    with pytest.raises(VALIDATOR.ContractValidationError, match="namespace_range_overlap"):
        VALIDATOR.validate_namespaces(ROOT, candidate)


def test_namespace_pattern_must_match_every_real_sidecar_id():
    candidate = registry()
    candidate["namespace_reservations"][1]["item_id_pattern"] = r"^ITEM-W64-(?P<row>[0-9]{3})$"
    with pytest.raises(VALIDATOR.ContractValidationError, match="namespace_id_pattern_mismatch"):
        VALIDATOR.validate_namespaces(ROOT, candidate)


def test_revision_parent_must_be_a_prior_immutable_revision():
    candidate = registry()
    candidate["revision_history_fixture"][1]["parent_revision_id"] = "controller-contract-r999"
    with pytest.raises(VALIDATOR.ContractValidationError, match="revision_reference_not_prior"):
        VALIDATOR.validate_revisions_and_exceptions(candidate)


def test_multiple_revision_chains_each_require_one_active_head():
    candidate = registry()
    candidate["revision_history_fixture"].append({
        "record_id": "second_contract_fixture",
        "revision_id": "second-contract-r001",
        "parent_revision_id": None,
        "supersedes_revision_id": None,
        "status": "active",
        "payload_sha256": "c" * 64,
        "evidence_refs": ["evidence://second-contract/r001"],
    })
    result = VALIDATOR.validate_revisions_and_exceptions(candidate)
    assert result["revision_count"] == 3

    candidate["revision_history_fixture"][-1]["status"] = "superseded"
    with pytest.raises(VALIDATOR.ContractValidationError, match="each_revision_chain_requires_one_active_head"):
        VALIDATOR.validate_revisions_and_exceptions(candidate)


def test_exception_cannot_waive_never_waivable_rule():
    candidate = registry()
    candidate["exception_fixture"][0]["waives_rules"] = ["llm_vlm_cannot_certify_or_promote"]
    with pytest.raises(VALIDATOR.ContractValidationError, match="exception_waives_never_waivable_rule"):
        VALIDATOR.validate_revisions_and_exceptions(candidate)


def test_exception_requires_forward_expiry():
    candidate = registry()
    candidate["exception_fixture"][0]["expires_at"] = candidate["exception_fixture"][0]["created_at"]
    with pytest.raises(VALIDATOR.ContractValidationError, match="exception_expiry_invalid"):
        VALIDATOR.validate_revisions_and_exceptions(candidate)


def test_entity_relation_cannot_dangle():
    candidate = registry()
    candidate["synthetic_entity_graph"]["relations"][0]["target_id"] = "char_missing"
    with pytest.raises(VALIDATOR.ContractValidationError, match="dangling_entity_relation"):
        VALIDATOR.validate_entity_graph(candidate)


def test_character_instance_cannot_use_reusable_definition_namespace():
    candidate = registry()
    instance = next(
        entity for entity in candidate["synthetic_entity_graph"]["entities"]
        if entity["entity_type"] == "character_instance"
    )
    instance["entity_id"] = "char_c01_duplicate_role"
    with pytest.raises(VALIDATOR.ContractValidationError, match="entity_id_pattern_mismatch"):
        VALIDATOR.validate_entity_graph(candidate)


def test_cli_evidence_outputs_are_exact_mirrors(tmp_path):
    result = VALIDATOR.validate_all(ROOT, registry(), schema())
    evidence = VALIDATOR.build_evidence(ROOT, result, VALIDATOR.DEFAULT_REGISTRY, VALIDATOR.DEFAULT_SCHEMA)
    qa_path = tmp_path / "qa.json"
    tracker_path = tmp_path / "tracker.json"
    VALIDATOR.write_json(qa_path, evidence)
    VALIDATOR.write_json(tracker_path, evidence)
    assert qa_path.read_bytes() == tracker_path.read_bytes()
    payload = json.loads(qa_path.read_text(encoding="utf-8"))
    assert payload["boundaries"]["promotion_authority_granted"] is False
    assert payload["authority"]["registry_sha256"]
