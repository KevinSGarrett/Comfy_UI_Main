from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_av_assembly_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_av_assembly_authority", SCRIPT)
assert SPEC and SPEC.loader
AUTHORITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTHORITY
SPEC.loader.exec_module(AUTHORITY)


def fixture():
    return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_REGISTRY)


def validate(candidate=None):
    return AUTHORITY.validate_all(ROOT, candidate or fixture(), AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_SCHEMA))


def test_live_fixture_is_fail_closed_and_complete_as_contract():
    result = validate()
    assert result["classification"] == "WAVE64_AV_ASSEMBLY_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [193, 194, 195, 196]
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["samples_per_frame"] == 2000
    assert result["certification_gate_count"] == 6


def test_source_is_hash_bound():
    candidate = fixture(); candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="bound_hash_mismatch:video_adapter_evidence"):
        validate(candidate)


def test_bound_path_cannot_escape_project():
    candidate = fixture(); candidate["source_authorities"][1]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="bound_path_not_relative:audio_adapter_evidence"):
        validate(candidate)


def test_source_names_are_unique():
    candidate = fixture(); candidate["source_authorities"][7]["name"] = "mmaudio_mux_evidence"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="duplicate_source_authority_name"):
        validate(candidate)


def test_parent_authorities_remain_runtime_blocked():
    result = validate()
    assert result["runtime_scope"].startswith("blocked_contract_validation")


def test_clock_requires_exact_timeline_field_set():
    candidate = fixture(); candidate["canonical_av_clock"]["required_timeline_fields"][0] = "dialogue"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_clock_is_exact_48000_over_24():
    candidate = fixture(); candidate["canonical_av_clock"]["samples_per_frame"] = 1999
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_clock_cannot_allow_drift():
    candidate = fixture(); candidate["canonical_av_clock"]["cumulative_drift_allowed"] = True
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_clock_must_be_monotonic():
    candidate = fixture(); candidate["canonical_av_clock"]["monotonic"] = False
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_clock_cannot_invent_timeline_manifest():
    candidate = fixture(); candidate["canonical_av_clock"]["timeline_manifest_ref"] = "timeline_unproven"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_clock_cannot_invent_execution_receipt():
    candidate = fixture(); candidate["canonical_av_clock"]["execution_receipt_ref"] = "receipt_unproven"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_requires_exact_retained_components():
    candidate = fixture(); candidate["mux_assembly_contract"]["retained_components"][0] = "metadata"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_requires_exact_reconciliation_set():
    candidate = fixture(); candidate["mux_assembly_contract"]["reconciliation_checks"][0]["check_id"] = "durations"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="mux_reconciliation_exact_set_mismatch"):
        validate(candidate)


def test_mux_cannot_claim_reconciliation_evidence():
    candidate = fixture(); candidate["mux_assembly_contract"]["reconciliation_checks"][0]["evidence_refs"] = ["unproven"]
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_cannot_bind_unaccepted_video():
    candidate = fixture(); candidate["mux_assembly_contract"]["accepted_video_ref"] = "video_unproven"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_cannot_bind_unaccepted_audio():
    candidate = fixture(); candidate["mux_assembly_contract"]["accepted_audio_ref"] = "audio_unproven"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_cannot_allow_substitution():
    candidate = fixture(); candidate["mux_assembly_contract"]["unapproved_substitution_allowed"] = True
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_mux_cannot_claim_execution_or_output():
    candidate = fixture(); candidate["mux_assembly_contract"]["assembly_executed"] = True
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_repair_requires_exact_defect_taxonomy():
    candidate = fixture(); candidate["localized_sync_repair"]["defect_classes"][0] = "event_sync"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_repair_cannot_invent_target_span():
    candidate = fixture(); candidate["localized_sync_repair"]["target_span"] = {"start_frame": 1, "end_frame": 2}
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_repair_preserves_accepted_parents():
    candidate = fixture(); candidate["localized_sync_repair"]["accepted_parents_immutable"] = False
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_repair_forbids_full_regeneration():
    candidate = fixture(); candidate["localized_sync_repair"]["full_regeneration_allowed"] = True
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_repair_requires_full_av_regression():
    candidate = fixture(); candidate["localized_sync_repair"]["complete_av_regression_required"] = False
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_certification_requires_exact_package_contents():
    candidate = fixture(); candidate["certification_package"]["required_contents"][0] = "audio"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_certification_requires_exact_gate_set():
    candidate = fixture(); candidate["certification_package"]["gate_results"][0]["gate_id"] = "technical"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="certification_gate_exact_set_mismatch"):
        validate(candidate)


def test_certification_cannot_claim_playback_evidence():
    candidate = fixture(); candidate["certification_package"]["gate_results"][5]["evidence_refs"] = ["playback_unproven"]
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_certification_cannot_invent_package_or_transaction():
    candidate = fixture(); candidate["certification_package"]["package_ref"] = "package_unproven"
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_rollback_and_revocation_are_ready_without_promotion():
    package = fixture()["certification_package"]
    assert package["rollback_ready"] is True
    assert package["revocation_ready"] is True
    assert package["certification_decision"] == "blocked"


def test_false_completion_boundary_is_rejected():
    candidate = fixture(); candidate["boundaries"]["production_certification_claimed"] = True
    with pytest.raises(AUTHORITY.AVAssemblyAuthorityError, match="schema_validation_failed:av_assembly_authority"):
        validate(candidate)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    evidence = AUTHORITY.build_evidence(ROOT, validate(), AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa, tracker = tmp_path / "qa.json", tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence); AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert not any(evidence["boundaries"].values())
