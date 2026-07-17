from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_video_adapter_authority.py"
SPEC = importlib.util.spec_from_file_location("wave64_video_adapter_authority", SCRIPT)
assert SPEC and SPEC.loader
AUTHORITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTHORITY
SPEC.loader.exec_module(AUTHORITY)


def fixture():
    return AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_REGISTRY)


def validate(candidate=None):
    return AUTHORITY.validate_all(ROOT, candidate or fixture(), AUTHORITY.load_json(ROOT / AUTHORITY.DEFAULT_SCHEMA))


def test_live_fixture_is_blocked_and_non_mutating():
    result = validate()
    assert result["classification"] == "WAVE64_VIDEO_ADAPTER_AUTHORITY_SLICE_PASS"
    assert result["rows_covered"] == [185, 186, 187, 188]
    assert result["runtime_execution_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["segment_count"] == 2
    assert result["temporal_check_count"] == 7


def test_parent_image_evidence_is_hash_bound():
    candidate = fixture()
    candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="bound_hash_mismatch:image_dag_evidence"):
        validate(candidate)


def test_bound_path_cannot_escape_project():
    candidate = fixture()
    candidate["source_authorities"][1]["path"] = "../outside.json"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="bound_path_not_relative:keyframe_authority_schema"):
        validate(candidate)


def test_source_authorities_require_unique_names():
    candidate = fixture()
    candidate["source_authorities"][5]["name"] = "video_span_repair_schema"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="duplicate_source_authority_name"):
        validate(candidate)


def test_keyframe_requires_exact_input_contracts():
    candidate = fixture()
    candidate["keyframe_adapter"]["required_input_contracts"][0] = "camera"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_keyframe_cannot_invent_artifact():
    candidate = fixture()
    candidate["keyframe_adapter"]["source_image_artifact_ref"] = "artifact_unproven"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_keyframe_cannot_invent_certificate():
    candidate = fixture()
    candidate["keyframe_adapter"]["keyframe_certificate_ref"] = "certificate_unproven"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_keyframe_request_is_not_emitted():
    candidate = fixture()
    candidate["keyframe_adapter"]["request_emitted"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_keyframe_preserves_shot_instance_authority():
    assert fixture()["keyframe_adapter"]["shot_instance_authority_preserved"] is True
    assert fixture()["keyframe_adapter"]["incompatible_keyframe_rejected"] is True


def test_segment_route_requires_exact_two_segment_plan():
    candidate = fixture()
    candidate["segment_route_plan"]["segments"][0]["segment_id"] = "wrong"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="segment_route_exact_set_mismatch"):
        validate(candidate)


def test_segment_overlap_is_exact():
    candidate = fixture()
    candidate["segment_route_plan"]["segments"][0]["overlap_next_frames"] = 7
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="segment_overlap_contract_mismatch"):
        validate(candidate)


def test_segment_cannot_select_uncertified_bundle():
    candidate = fixture()
    candidate["segment_route_plan"]["segments"][0]["selected_bundle_ref"] = "bundle_unproven"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_segment_candidate_cannot_be_eligible():
    candidate = fixture()
    candidate["segment_route_plan"]["segments"][0]["evaluated_candidates"][0]["eligible"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_segment_has_temporal_and_resource_contracts():
    segment = fixture()["segment_route_plan"]["segments"][0]
    assert "identity_continuity" in segment["temporal_constraints"]
    assert segment["resource_envelope"]["max_attempts"] == 2


def test_route_silent_substitution_is_forbidden():
    candidate = fixture()
    candidate["segment_route_plan"]["silent_substitution_allowed"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_cross_engine_transfer_is_decoded_only():
    bridge = fixture()["decoded_handoff"]
    assert bridge["transfer_type"] == "decoded_frames_only"
    assert bridge["latent_transfer_allowed"] is False


def test_decoded_bridge_cannot_claim_bundles():
    candidate = fixture()
    candidate["decoded_handoff"]["source_bundle_ref"] = "bundle_unproven"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_decoded_bridge_cannot_claim_certificate():
    candidate = fixture()
    candidate["decoded_handoff"]["certificate_ref"] = "certificate_unproven"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_span_repair_targets_only_failed_frames():
    result = validate()
    assert result["repair_target_frame_count"] == 24
    assert fixture()["span_repair_plan"]["full_clip_rerender"] is False


def test_span_repair_preserves_accepted_spans():
    candidate = fixture()
    candidate["span_repair_plan"]["immutable_accepted_spans"][0]["end_frame"] = 24
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="span_repair_accepted_span_mismatch"):
        validate(candidate)


def test_span_repair_cannot_execute_without_authority():
    candidate = fixture()
    candidate["span_repair_plan"]["repair_executed"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_span_repair_cannot_invent_masks():
    candidate = fixture()
    candidate["span_repair_plan"]["write_mask_refs"] = ["mask_unproven"]
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_span_repair_attempt_budget_is_bounded():
    candidate = fixture()
    candidate["span_repair_plan"]["max_attempts"] = 3
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_temporal_gate_requires_exact_check_set():
    candidate = fixture()
    candidate["temporal_promotion_gate"]["checks"][0]["check_id"] = "duration"
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="temporal_check_exact_set_mismatch"):
        validate(candidate)


def test_temporal_gate_clock_is_exact():
    clock = fixture()["temporal_promotion_gate"]["expected_clock"]
    assert clock == {"frame_count": 72, "fps_numerator": 24, "fps_denominator": 1, "duration_seconds": 3.0}


def test_temporal_gate_cannot_claim_playback_evidence():
    candidate = fixture()
    candidate["temporal_promotion_gate"]["checks"][5]["evidence_refs"] = ["playback_unproven"]
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_temporal_gate_cannot_claim_promotion():
    candidate = fixture()
    candidate["temporal_promotion_gate"]["promotion_allowed"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_false_completion_boundary_is_rejected():
    candidate = fixture()
    candidate["boundaries"]["candidate_video_created"] = True
    with pytest.raises(AUTHORITY.VideoAdapterAuthorityError, match="schema_validation_failed:video_adapter_authority"):
        validate(candidate)


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    evidence = AUTHORITY.build_evidence(ROOT, validate(), AUTHORITY.DEFAULT_REGISTRY, AUTHORITY.DEFAULT_SCHEMA)
    qa, tracker = tmp_path / "qa.json", tmp_path / "tracker.json"
    AUTHORITY.write_json(qa, evidence)
    AUTHORITY.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert not any(evidence["boundaries"].values())
