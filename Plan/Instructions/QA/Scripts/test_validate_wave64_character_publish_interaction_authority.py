from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_character_publish_interaction_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_character_publish_interaction_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def registry():
    return VALIDATOR.load_json(ROOT / VALIDATOR.DEFAULT_REGISTRY)


def schema():
    return VALIDATOR.load_json(ROOT / VALIDATOR.DEFAULT_SCHEMA)


def validate(candidate):
    return VALIDATOR.validate_all(ROOT, candidate, schema())


def test_live_registry_passes_all_five_staged_authority_rows():
    result = validate(registry())
    assert result["classification"] == "WAVE64_CHARACTER_PUBLISH_INTERACTION_SLICE_PASS"
    assert result["rows_covered"] == [159, 160, 161, 162, 163]
    assert result["adapter_card_count"] == 5
    assert result["publication_non_pass_domain_count"] == 7
    assert result["owned_resource_count"] == 10
    assert result["runtime_completion_claimed"] is False
    assert result["production_publication_allowed"] is False


def test_source_compilation_contract_hash_is_immutable():
    candidate = registry()
    candidate["source_compilation_contract"]["sha256"] = "0" * 64
    with pytest.raises(VALIDATOR.AuthorityError, match="source_compilation_contract_hash_mismatch"):
        validate(candidate)


def test_source_compilation_path_must_remain_project_bounded():
    candidate = registry()
    candidate["source_compilation_contract"]["path"] = "C:/outside/fixture.json"
    with pytest.raises(VALIDATOR.AuthorityError, match="source_compilation_path_must_be_bounded_relative"):
        validate(candidate)


def test_adapter_role_set_cannot_be_incomplete_or_duplicated():
    candidate = registry()
    candidate["adapter_cards"][-1]["adapter_role"] = "video"
    candidate["adapter_cards"][-1]["modality"] = "video"
    with pytest.raises(VALIDATOR.AuthorityError, match="adapter_role_set_incomplete_or_duplicate"):
        validate(candidate)


def test_adapter_cannot_bind_different_character_revision():
    candidate = registry()
    candidate["adapter_cards"][0]["character_revision"] = "r999"
    with pytest.raises(VALIDATOR.AuthorityError, match="adapter_character_revision_mismatch"):
        validate(candidate)


def test_synthetic_adapter_cannot_claim_runtime_calibration_pass():
    candidate = registry()
    candidate["adapter_cards"][0]["calibration_status"] = "passed"
    with pytest.raises(VALIDATOR.AuthorityError, match="synthetic_adapter_cannot_claim_calibration_pass"):
        validate(candidate)


def test_adapter_requires_explicit_prohibited_pairings():
    candidate = registry()
    candidate["adapter_cards"][0]["prohibited_pairings"] = []
    with pytest.raises(VALIDATOR.AuthorityError, match="schema_validation_failed"):
        validate(candidate)


def test_publication_revision_hash_must_match_source_character():
    candidate = registry()
    candidate["publication_gate"]["immutable_revision_sha256"] = "0" * 64
    with pytest.raises(VALIDATOR.AuthorityError, match="publication_immutable_revision_hash_mismatch"):
        validate(candidate)


def test_publication_domains_must_be_exact_and_complete():
    candidate = registry()
    candidate["publication_gate"]["required_domains"][-1] = "duplicate_domain"
    with pytest.raises(VALIDATOR.AuthorityError, match="publication_required_domain_set_mismatch"):
        validate(candidate)


def test_synthetic_gate_cannot_convert_all_domains_to_pass():
    candidate = registry()
    for result in candidate["publication_gate"]["domain_results"]:
        result["status"] = "pass"
        result["evidence_ids"] = [f"evidence://synthetic/{result['domain']}"]
    with pytest.raises(VALIDATOR.AuthorityError, match="synthetic_publication_gate_requires_real_blocker"):
        validate(candidate)


def test_scene_compiler_must_preserve_all_five_modalities():
    candidate = registry()
    candidate["scene_compilation"]["output_modalities"].remove("mask")
    with pytest.raises(VALIDATOR.AuthorityError, match="schema_validation_failed"):
        validate(candidate)


def test_scene_timebase_must_be_forward():
    candidate = registry()
    candidate["scene_compilation"]["timebase"]["end_frame"] = 0
    candidate["scene_compilation"]["timebase"]["start_frame"] = 1
    with pytest.raises(VALIDATOR.AuthorityError, match="scene_timebase_invalid"):
        validate(candidate)


def test_every_instance_requires_all_owned_resource_classes():
    candidate = registry()
    candidate["scene_compilation"]["instances"][0]["resources"] = [
        resource for resource in candidate["scene_compilation"]["instances"][0]["resources"]
        if resource["resource_type"] != "prop"
    ]
    with pytest.raises(VALIDATOR.AuthorityError, match="scene_instance_resource_type_missing"):
        validate(candidate)


def test_resource_owner_must_equal_containing_instance():
    candidate = registry()
    candidate["scene_compilation"]["instances"][0]["resources"][0]["owner_instance_id"] = "charinst_other"
    with pytest.raises(VALIDATOR.AuthorityError, match="resource_owner_mismatch"):
        validate(candidate)


def test_one_resource_cannot_have_two_ownership_claims():
    candidate = registry()
    duplicate = dict(candidate["scene_compilation"]["instances"][0]["resources"][0])
    candidate["scene_compilation"]["instances"][0]["resources"].append(duplicate)
    with pytest.raises(VALIDATOR.AuthorityError, match="resource_ambiguously_owned"):
        validate(candidate)


def test_synthetic_mask_cannot_be_upgraded_above_machine_draft():
    candidate = registry()
    mask = next(
        resource for resource in candidate["scene_compilation"]["instances"][0]["resources"]
        if resource["resource_type"] == "mask"
    )
    mask["authority"] = "approved_package"
    with pytest.raises(VALIDATOR.AuthorityError, match="synthetic_mask_authority_upgrade_forbidden"):
        validate(candidate)


def test_audio_event_requires_known_owner_and_dialogue_resource():
    candidate = registry()
    candidate["scene_compilation"]["expected_audio_events"][0]["owner_instance_id"] = "charinst_missing"
    with pytest.raises(VALIDATOR.AuthorityError, match="audio_event_owner_unknown"):
        validate(candidate)


def test_audio_event_must_fit_shot_timebase():
    candidate = registry()
    candidate["scene_compilation"]["expected_audio_events"][0]["end_frame"] = 99
    with pytest.raises(VALIDATOR.AuthorityError, match="audio_event_timing_invalid"):
        validate(candidate)


def test_interaction_plan_scope_must_match_scene_compilation():
    candidate = registry()
    candidate["interaction_plan"]["take_id"] = "take999"
    with pytest.raises(VALIDATOR.AuthorityError, match="interaction_plan_scope_mismatch"):
        validate(candidate)


def test_contact_participant_owner_must_exist():
    candidate = registry()
    candidate["interaction_plan"]["contacts"][0]["participants"][0]["owner_instance_id"] = "charinst_missing"
    with pytest.raises(VALIDATOR.AuthorityError, match="contact_owner_unknown"):
        validate(candidate)


def test_contact_region_must_be_owned_by_participant():
    candidate = registry()
    candidate["interaction_plan"]["contacts"][0]["participants"][0]["region_id"] = "unowned_region"
    with pytest.raises(VALIDATOR.AuthorityError, match="contact_region_not_owned"):
        validate(candidate)


def test_expected_deformation_must_bind_contact_participant_region():
    candidate = registry()
    candidate["interaction_plan"]["contacts"][0]["expected_deformations"][0]["region_id"] = "left_hand"
    with pytest.raises(VALIDATOR.AuthorityError, match="contact_deformation_not_bound_to_participant"):
        validate(candidate)


def test_contact_timing_must_fit_shot_timebase():
    candidate = registry()
    candidate["interaction_plan"]["contacts"][0]["end_frame"] = 99
    with pytest.raises(VALIDATOR.AuthorityError, match="contact_timing_invalid"):
        validate(candidate)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    result = validate(registry())
    evidence = VALIDATOR.build_evidence(ROOT, result, VALIDATOR.DEFAULT_REGISTRY, VALIDATOR.DEFAULT_SCHEMA)
    qa = tmp_path / "qa.json"
    tracker = tmp_path / "tracker.json"
    VALIDATOR.write_json(qa, evidence)
    VALIDATOR.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    payload = json.loads(qa.read_text(encoding="utf-8"))
    assert payload["boundaries"]["character_revision_published"] is False
    assert payload["boundaries"]["writes_gold"] is False
