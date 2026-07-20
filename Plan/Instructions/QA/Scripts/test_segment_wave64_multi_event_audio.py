from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/segment_wave64_multi_event_audio.py"
SPEC = importlib.util.spec_from_file_location("segment_wave64_multi_event_audio", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row072_runtime_unlocked_and_row073_probe_unlocked_for_probe_gate():
    row072 = MOD.evaluate_row072_admission(ROOT)
    row073 = MOD.evaluate_row073_admission(ROOT)
    assert row072["dependency_satisfied"] is True
    assert row072["admission_mode"] == "runtime_unlocked"
    assert row072["row_complete"] is False
    assert row072["row072_acceptance"] == "held"
    assert row072["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert row073["dependency_satisfied"] is True
    assert row073["admission_mode"] == "probe_unlocked"
    assert row073["row_complete"] is False
    assert row073["row073_acceptance"] == "held"
    assert row073["proof_tier"] == "RUNTIME_PASS_BOUNDED"


def test_library_mode_emits_deps_unlocked_hold_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row074_acceptance"] == "held"
    assert payload["decision"]["dependencies_unlocked"] is True
    assert "ROW072_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["status"] == "HOLD_LIBRARY_RUNTIME_AND_EVENT_CALIBRATION_ABSENT_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["segmentation_pipeline_revision"] == MOD.SEGMENTATION_PIPELINE_REVISION
    assert payload["thresholds"]["source_mutation_allowed"] is False
    assert payload["boundary_convention"]["inclusive_start"] is True
    assert payload["boundary_convention"]["exclusive_end"] is True
    assert payload["fixture_calibration"]["fixture_count"] == len(MOD.FIXTURE_NAMES)


def test_library_mode_with_probe_runtime_marks_probe_hold():
    retained = {
        "coverage_complete": False,
        "limit": 25,
        "authority": "accepted_index_retained_segment_probe",
        "counts": {
            "records_processed": 25,
            "segment_pass": 20,
            "segment_blocked": 5,
            "multi_event_assets": 4,
        },
        "blocker_histogram": {"SEGMENTATION_EXTRACTION_FAILED": 5},
        "records_path": (
            "runtime_artifacts/multi_event_segmentation/"
            "row074_index_retained_20260720/records.jsonl"
        ),
        "progress_path": (
            "runtime_artifacts/multi_event_segmentation/"
            "row074_index_retained_20260720/progress.json"
        ),
        "receipt_path": (
            "runtime_artifacts/multi_event_segmentation/"
            "row074_index_retained_20260720/retained_index_segment_receipt.json"
        ),
        "status": "RUNTIME_PASS_BOUNDED_PROBE_LIMIT",
        "row075_contention_policy": "limited_probe_only_while_row075_full_reconcile_owns_pcm_io",
    }
    payload = MOD.build_library_blocker_packet(ROOT, retained_runtime=retained)
    assert payload["status"] == "HOLD_LIBRARY_PROBE_PASS_FULL_RECONCILE_DEFERRED_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["runtime_completion_claimed"] is False
    assert payload["accepted_index_retained_segment_runtime"]["present"] is True
    assert payload["accepted_index_retained_segment_runtime"]["limit"] == 25
    assert payload["decision"]["product_completion"] is False


def test_two_footsteps_fixture_detects_two_non_overlapping_events():
    first = MOD.extract_fixture_record(ROOT, "two_footsteps")
    second = MOD.extract_fixture_record(ROOT, "two_footsteps")
    assert first == second
    assert first["event_count"] == 2
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["decision"]["bit_exact_reconstruction_ok"] is True
    assert first["source_before_sha256"] == first["source_after_sha256"]
    assert first["overlap_policy"]["mode"] == "non_overlapping"
    assert first["segments"][0]["end_sample"] <= first["segments"][1]["start_sample"]
    for segment in first["segments"]:
        assert segment["parent_canonical_pcm_sha256"] == first["canonical_pcm_sha256"]
        assert segment["overlap_mode"] == "none"
        assert segment["layer_id"] is None


def test_silence_fixture_emits_zero_events():
    record = MOD.extract_fixture_record(ROOT, "silence")
    assert record["event_count"] == 0
    assert record["segments"] == []
    assert record["decision"]["bit_exact_reconstruction_ok"] is True


def test_three_impacts_fixture_event_count():
    record = MOD.extract_fixture_record(ROOT, "three_impacts")
    assert record["event_count"] == 3
    assert all(segment["event_family"] == "impact" for segment in record["segments"])


def test_layered_overlap_requires_explicit_layer_ids():
    record = MOD.extract_fixture_record(ROOT, "layered_overlap")
    assert record["event_count"] == 2
    assert record["overlap_policy"]["mode"] == "explicit_layered"
    assert record["overlap_policy"]["layered_overlap_present"] is True
    assert record["segments"][0]["end_sample"] > record["segments"][1]["start_sample"]
    assert {segment["layer_id"] for segment in record["segments"]} == {"layer_a", "layer_b"}
    assert record["decision"]["bit_exact_reconstruction_ok"] is True


def test_accidental_overlap_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "two_footsteps")
    record["segments"][1]["start_sample"] = record["segments"][0]["start_sample"] + 10
    errors = MOD.validate_segments_policy(
        record["segments"],
        frame_count=record["frame_count"],
        overlap_mode="non_overlapping",
    )
    assert any(error.startswith("accidental_overlap:") for error in errors)


def test_out_of_parent_and_duplicate_ids_fail_closed():
    record = MOD.extract_fixture_record(ROOT, "single_impact")
    bad = dict(record["segments"][0])
    bad["segment_id"] = record["segments"][0]["segment_id"]
    bad["end_sample"] = record["frame_count"] + 5
    errors = MOD.validate_segments_policy(
        [record["segments"][0], bad],
        frame_count=record["frame_count"],
        overlap_mode="non_overlapping",
    )
    assert any(error.startswith("duplicate_segment_id:") for error in errors)
    assert any(error.startswith("out_of_parent_segment:") for error in errors)


def test_bit_exact_reconstruction_matches_parent_slice():
    fixture = MOD.synthesize_fixture("breath_pair")
    segments, _policy = MOD.build_segments_for_fixture(fixture)
    assert len(segments) == 2
    for segment in segments:
        reconstructed = MOD.virtual_clip_sha256_from_parent(
            fixture["pcm_f32le"],
            channels=fixture["channels"],
            start_sample=segment["start_sample"],
            end_sample=segment["end_sample"],
        )
        assert reconstructed == segment["virtual_clip_sha256"]


def test_schema_rejects_missing_virtual_clip_hash():
    record = MOD.extract_fixture_record(ROOT, "single_impact")
    del record["segments"][0]["virtual_clip_sha256"]
    with pytest.raises(MOD.MultiEventSegmentationError, match="schema_validation_failed"):
        MOD.validate_segmentation_record(ROOT, record)


def test_layered_segment_without_layer_id_fails_closed():
    record = MOD.extract_fixture_record(ROOT, "layered_overlap")
    record["segments"][0]["layer_id"] = None
    errors = MOD.validate_segments_policy(
        record["segments"],
        frame_count=record["frame_count"],
        overlap_mode="explicit_layered",
    )
    assert any("missing_layer_id" in error for error in errors)
