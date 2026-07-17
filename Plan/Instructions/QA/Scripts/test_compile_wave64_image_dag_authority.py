from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_image_dag_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_image_dag_authority", SCRIPT)
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
    assert result["classification"] == "WAVE64_IMAGE_DAG_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [181, 182, 183, 184]
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["module_count"] == 8
    assert result["compiled_slice_count"] == 2
    assert result["blocked_vertical_slice_count"] == 2


def test_source_evidence_hash_is_immutable():
    candidate = fixture()
    candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="bound_hash_mismatch:maskfactory_adapter_evidence"):
        validate(candidate)


def test_bound_paths_cannot_escape_project():
    candidate = fixture()
    candidate["source_authorities"][1]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="bound_path_not_relative:workflow_module_contract_schema"):
        validate(candidate)


def test_source_authorities_require_exact_unique_set():
    candidate = fixture()
    candidate["source_authorities"][7]["name"] = "workflow_release_manifest_schema"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="duplicate_source_authority_name"):
        validate(candidate)


def test_source_maskfactory_cannot_claim_runtime_authority(monkeypatch):
    original = AUTHORITY.load_bound_file

    def altered(root, reference, label):
        path, payload = original(root, reference, label)
        if label == "maskfactory_adapter_evidence":
            payload["runtime_execution_allowed"] = True
        return path, payload

    monkeypatch.setattr(AUTHORITY, "load_bound_file", altered)
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="source_maskfactory_false_runtime_authority"):
        validate()


def test_module_library_requires_exact_eight_module_set():
    candidate = fixture()
    candidate["module_library"][0]["module_id"] = "identity"
    candidate["module_library"][0]["module_contract"]["module_id"] = "identity"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="duplicate_module_id"):
        validate(candidate)


def test_module_contract_validates_against_adopted_schema():
    candidate = fixture()
    del candidate["module_library"][0]["module_contract"]["purpose"]
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:module:composition"):
        validate(candidate)


def test_module_cannot_claim_workflow_release():
    candidate = fixture()
    candidate["module_library"][0]["workflow_release_id"] = "release_unproven"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_module_requires_stable_patch_points():
    candidate = fixture()
    candidate["module_library"][0]["stable_patch_points"] = []
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


@pytest.mark.parametrize("field", ["fixed_character_names", "hidden_paths", "orchestration_decisions"])
def test_module_forbids_embedded_character_path_or_orchestration_authority(field):
    candidate = fixture()
    candidate["module_library"][0][field] = ["forbidden"]
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_unknown_compile_intent_fails_closed():
    candidate = fixture()
    candidate["compile_requests"][0]["needed_pass_intents"][0] = "unknown"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_compiler_is_deterministic_for_both_slices():
    candidate = fixture()
    refreshed = AUTHORITY.refresh_compiled_dags(candidate)
    assert refreshed["compiled_dags"] == candidate["compiled_dags"]


def test_compile_request_character_count_matches_slice():
    candidate = fixture()
    candidate["compile_requests"][0]["character_count"] = 2
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="compile_request_character_count_mismatch:single_character"):
        validate(candidate)


def test_compiled_plan_hash_is_content_bound():
    candidate = fixture()
    candidate["compiled_dags"][0]["dag"]["compiled_plan_sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="compiled_dag_not_deterministic:single_character"):
        validate(candidate)


def test_dag_cannot_gain_an_unrequested_pass():
    candidate = fixture()
    candidate["compiled_dags"][0]["dag"]["pass_nodes"].append(candidate["compiled_dags"][0]["dag"]["pass_nodes"][0].copy())
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="compiled_dag_not_deterministic:single_character"):
        validate(candidate)


def test_intent_coverage_must_be_exact():
    candidate = fixture()
    candidate["compiled_dags"][1]["intent_coverage"][3]["intent"] = "realism"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="compile_intent_coverage_mismatch:two_character_contact"):
        validate(candidate)


def test_intent_coverage_cannot_point_to_unknown_pass():
    candidate = fixture()
    candidate["compiled_dags"][0]["intent_coverage"][0]["pass_id"] = "unknown_pass"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="compile_intent_unknown_pass:single_character"):
        validate(candidate)


def test_accepted_parent_is_immutable():
    candidate = fixture()
    candidate["compile_requests"][0]["accepted_parent"]["immutable"] = False
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_single_and_two_character_slices_are_present():
    candidate = fixture()
    assert [entry["character_count"] for entry in candidate["vertical_slices"]] == [1, 2]


def test_vertical_slice_cannot_claim_execution():
    candidate = fixture()
    candidate["vertical_slices"][0]["runtime_execution_allowed"] = True
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_vertical_slice_cannot_invent_execution_receipt():
    candidate = fixture()
    candidate["vertical_slices"][0]["execution_receipt_refs"] = ["receipt_unproven"]
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_vertical_slice_cannot_invent_candidate_artifact():
    candidate = fixture()
    candidate["vertical_slices"][1]["candidate_artifact_ref"] = "artifact_unproven"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_vertical_slice_retains_parent_and_resume_boundary():
    candidate = fixture()
    candidate["vertical_slices"][0]["resumable"] = False
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_promotion_lineage_requires_exact_eleven_bindings():
    candidate = fixture()
    candidate["reproducibility_promotion_gate"]["lineage_bindings"][0]["binding_type"] = "prompts"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="promotion_lineage_exact_set_mismatch"):
        validate(candidate)


def test_promotion_lineage_cannot_claim_unavailable_reference():
    candidate = fixture()
    candidate["reproducibility_promotion_gate"]["lineage_bindings"][0]["reference"] = "package_unproven"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_promotion_requires_target_protected_and_whole_frame_qa():
    candidate = fixture()
    candidate["reproducibility_promotion_gate"]["qa_results"][0]["scope"] = "protected"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="promotion_qa_scope_exact_set_mismatch"):
        validate(candidate)


def test_promotion_qa_cannot_claim_evidence():
    candidate = fixture()
    candidate["reproducibility_promotion_gate"]["qa_results"][0]["evidence_ids"] = ["qa_unproven"]
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_promotion_transaction_remains_absent():
    candidate = fixture()
    candidate["reproducibility_promotion_gate"]["promotion_transaction_ref"] = "promotion_unproven"
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


def test_false_completion_boundary_is_rejected():
    candidate = fixture()
    candidate["boundaries"]["visual_qa_claimed"] = True
    with pytest.raises(AUTHORITY.ImageDagAuthorityError, match="schema_validation_failed:image_dag_authority"):
        validate(candidate)


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
