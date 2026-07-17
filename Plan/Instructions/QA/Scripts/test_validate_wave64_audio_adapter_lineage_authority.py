from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_adapter_lineage_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_audio_adapter_lineage_authority", SCRIPT)
assert SPEC and SPEC.loader
AUTHORITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTHORITY
SPEC.loader.exec_module(AUTHORITY)


def fixture():
    return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_REGISTRY)


def validate(candidate=None):
    return AUTHORITY.validate_all(ROOT, candidate or fixture(), AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_SCHEMA))


def test_live_fixture_is_blocked_and_reuses_existing_audio():
    result = validate()
    assert result["classification"] == "WAVE64_AUDIO_ADAPTER_LINEAGE_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [189, 190, 191, 192]
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["audio_intent_binding_count"] == 9
    assert result["audio_adapter_count"] == 9
    assert result["audio_promotion_gate_count"] == 12


def test_functional_index_is_hash_bound():
    candidate = fixture(); candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="bound_hash_mismatch:functional_audio_index_registry"):
        validate(candidate)


def test_bound_path_cannot_escape_project():
    candidate = fixture(); candidate["source_authorities"][1]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="bound_path_not_relative:audio_event_graph_schema"):
        validate(candidate)


def test_source_authority_names_are_unique():
    candidate = fixture(); candidate["source_authorities"][7]["name"] = "mmaudio_mux_evidence"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="duplicate_source_authority_name"):
        validate(candidate)


def test_intent_bindings_require_exact_set():
    candidate = fixture(); candidate["shot_audio_intent_binding"]["bindings"][0]["intent_type"] = "dialogue"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="audio_intent_exact_set_mismatch"):
        validate(candidate)


def test_intent_binding_cannot_invent_authority():
    candidate = fixture(); candidate["shot_audio_intent_binding"]["bindings"][0]["authority_ref"] = "voice_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_rows067_148_are_reused_without_generation():
    binding = fixture()["shot_audio_intent_binding"]
    assert binding["rows_067_148_reused"] is True
    assert binding["duplicate_generation_allowed"] is False


def test_event_graph_cannot_be_emitted_without_bindings():
    candidate = fixture(); candidate["shot_audio_intent_binding"]["event_graph_emitted"] = True
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_adapter_library_requires_exact_nine_modules():
    candidate = fixture(); candidate["adapter_library"][0]["adapter_id"] = "mix"
    candidate["adapter_library"][0]["output_stem_id"] = "stem_speech_duplicate"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="audio_adapter_exact_set_mismatch"):
        validate(candidate)


def test_adapter_cannot_select_unproven_stack():
    candidate = fixture(); candidate["adapter_library"][0]["selected_stack_ref"] = "stack_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_adapter_cannot_claim_workflow_release():
    candidate = fixture(); candidate["adapter_library"][2]["workflow_release_ref"] = "release_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_adapter_requires_exact_package_contract_version():
    candidate = fixture(); candidate["adapter_library"][0]["package_contract_version"] = "latest"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_adapter_requires_stack_requirements():
    candidate = fixture(); candidate["adapter_library"][0]["stack_requirements"] = []
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_all_adapters_use_canonical_48k_24fps_timebase():
    candidate = fixture(); candidate["adapter_library"][0]["timebase"]["sample_rate_hz"] = 44100
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_adapter_output_stems_are_unique():
    candidate = fixture(); candidate["adapter_library"][1]["output_stem_id"] = "stem_speech"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="audio_adapter_output_stems_not_unique"):
        validate(candidate)


def test_adapter_cannot_claim_execution():
    candidate = fixture(); candidate["adapter_library"][0]["execution_allowed"] = True
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_sample_lineage_requires_exact_six_fields():
    candidate = fixture(); candidate["sample_lineage_pipeline"]["required_lineage_fields"][0] = "source_ref"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_sample_lineage_cannot_invent_manifest():
    candidate = fixture(); candidate["sample_lineage_pipeline"]["sample_span_manifest_ref"] = "manifest_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_sample_lineage_cannot_invent_receipt():
    candidate = fixture(); candidate["sample_lineage_pipeline"]["execution_receipt_ref"] = "receipt_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_every_stem_is_independently_replaceable():
    result = validate()
    assert result["replaceable_stem_count"] == 9
    assert all(x["independently_replaceable"] for x in fixture()["sample_lineage_pipeline"]["stem_replacement_policy"])


def test_stem_replacement_preserves_unaffected_stems():
    candidate = fixture(); candidate["sample_lineage_pipeline"]["stem_replacement_policy"][0]["unaffected_stems_immutable"] = False
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_replacement_set_must_match_adapter_outputs():
    candidate = fixture(); candidate["sample_lineage_pipeline"]["stem_replacement_policy"][0]["stem_id"] = "stem_unknown"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="stem_replacement_set_mismatch"):
        validate(candidate)


def test_promotion_requires_exact_twelve_gate_set():
    candidate = fixture(); candidate["promotion_revocation_gate"]["gate_results"][0]["gate_id"] = "prosody"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="audio_promotion_gate_exact_set_mismatch"):
        validate(candidate)


def test_promotion_gate_cannot_claim_playback_evidence():
    candidate = fixture(); candidate["promotion_revocation_gate"]["gate_results"][9]["evidence_refs"] = ["playback_unproven"]
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_incomplete_package_cannot_promote():
    candidate = fixture(); candidate["promotion_revocation_gate"]["complete_synchronized_package"] = True
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_local_stem_gain_cannot_hide_global_regression():
    assert fixture()["promotion_revocation_gate"]["local_stem_gain_requires_global_regression_pass"] is True


def test_promotion_transaction_remains_absent():
    candidate = fixture(); candidate["promotion_revocation_gate"]["promotion_transaction_ref"] = "promotion_unproven"
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_false_completion_boundary_is_rejected():
    candidate = fixture(); candidate["boundaries"]["subjective_review_fabricated"] = True
    with pytest.raises(AUTHORITY.AudioAdapterAuthorityError, match="schema_validation_failed:audio_adapter_lineage_authority"):
        validate(candidate)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    evidence = AUTHORITY.build_evidence(ROOT, validate(), AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa, tracker = tmp_path / "qa.json", tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence); AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert not any(evidence["boundaries"].values())
