from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/detect_wave64_onset_transient_anchors.py"
SPEC = importlib.util.spec_from_file_location("detect_wave64_onset_transient_anchors", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def _write_retained_fixture(path: Path) -> None:
    rows = [
        {
            "relative_path": "fixture/body_pass.wav",
            "extension": ".wav",
            "role": "body",
            "event_type": "body_foley",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 120,
            "sample_rate_hz": 48000,
            "channels": 2,
            "frame_count": 4800,
            "source_sha256": "a" * 64,
            "canonical_pcm_sha256": "b" * 64,
            "asset_id": "index:fixture/body_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/body_blocked.wav",
            "extension": ".wav",
            "role": "body",
            "event_type": "body_foley",
            "onset_status": "blocked",
            "technical_onset_pass": False,
            "onset_sample": 80,
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_count": 2400,
            "source_sha256": "c" * 64,
            "canonical_pcm_sha256": "d" * 64,
            "asset_id": "index:fixture/body_blocked.wav",
            "blocker_code": "MULTI_CANDIDATE_ONSET_NO_FRAME_EXACT_CLAIM",
        },
        {
            "relative_path": "fixture/action_pass.wav",
            "extension": ".wav",
            "role": "effects",
            "event_type": "action_sfx",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 64,
            "sample_rate_hz": 44100,
            "channels": 2,
            "frame_count": 4410,
            "source_sha256": "e" * 64,
            "canonical_pcm_sha256": "f" * 64,
            "asset_id": "index:fixture/action_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/impact_pass.wav",
            "extension": ".wav",
            "role": "effects",
            "event_type": "impact",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 32,
            "sample_rate_hz": 48000,
            "channels": 2,
            "frame_count": 2000,
            "source_sha256": "1" * 64,
            "canonical_pcm_sha256": "2" * 64,
            "asset_id": "index:fixture/impact_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/clothing_pass.wav",
            "extension": ".wav",
            "role": "clothing",
            "event_type": "clothing_foley",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 16,
            "sample_rate_hz": 32000,
            "channels": 2,
            "frame_count": 3200,
            "source_sha256": "3" * 64,
            "canonical_pcm_sha256": "4" * 64,
            "asset_id": "index:fixture/clothing_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/voice_pass.wav",
            "extension": ".wav",
            "role": "voice",
            "event_type": "voice_reaction",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 200,
            "sample_rate_hz": 44100,
            "channels": 1,
            "frame_count": 44100,
            "source_sha256": "5" * 64,
            "canonical_pcm_sha256": "6" * 64,
            "asset_id": "index:fixture/voice_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/furniture_blocked.wav",
            "extension": ".wav",
            "role": "furniture",
            "event_type": "furniture_foley",
            "onset_status": "blocked",
            "technical_onset_pass": False,
            "onset_sample": 90,
            "sample_rate_hz": 44100,
            "channels": 2,
            "frame_count": 8000,
            "source_sha256": "7" * 64,
            "canonical_pcm_sha256": "8" * 64,
            "asset_id": "index:fixture/furniture_blocked.wav",
            "blocker_code": "METHOD_DISAGREEMENT",
        },
        {
            "relative_path": "fixture/eval_pass.wav",
            "extension": ".wav",
            "role": "evaluation",
            "event_type": "evaluation_reference",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 10,
            "sample_rate_hz": 16000,
            "channels": 1,
            "frame_count": 16000,
            "source_sha256": "9" * 64,
            "canonical_pcm_sha256": "0" * 64,
            "asset_id": "index:fixture/eval_pass.wav",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/effects_pass.mp3",
            "extension": ".mp3",
            "role": "effects",
            "event_type": "unclassified",
            "onset_status": "pass",
            "technical_onset_pass": True,
            "onset_sample": 48,
            "sample_rate_hz": 48000,
            "channels": 2,
            "frame_count": 48000,
            "source_sha256": "ab" * 32,
            "canonical_pcm_sha256": "cd" * 32,
            "asset_id": "index:fixture/effects_pass.mp3",
            "blocker_code": None,
        },
        {
            "relative_path": "fixture/body_blocked.mp3",
            "extension": ".mp3",
            "role": "body",
            "event_type": "body_foley",
            "onset_status": "blocked",
            "technical_onset_pass": False,
            "onset_sample": 12,
            "sample_rate_hz": 44100,
            "channels": 2,
            "frame_count": 22050,
            "source_sha256": "ef" * 32,
            "canonical_pcm_sha256": "aa" * 32,
            "asset_id": "index:fixture/body_blocked.mp3",
            "blocker_code": "MULTI_CANDIDATE_ONSET_NO_FRAME_EXACT_CLAIM",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_row070_and_row071_admission_unlocked_on_accepted_deltas():
    row070 = MOD.evaluate_row070_admission(ROOT)
    row071 = MOD.evaluate_row071_admission(ROOT)
    assert row070["dependency_satisfied"] is True
    assert row071["dependency_satisfied"] is True
    assert row070["blocker_codes"] == []
    assert row071["blocker_codes"] == []


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["dependencies_unlocked"] is True
    assert payload["status"] == (
        "HOLD_LIBRARY_RUNTIME_AND_BENCHMARK_STRATA_ABSENT_DEPS_UNLOCKED"
    )
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "ROW071_DEPENDENCY_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY" in payload["blocker_codes"]
    assert "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT" in payload["blocker_codes"]
    assert payload["detector_revision"] == MOD.DETECTOR_REVISION
    assert payload["threshold_registry_revision"] == MOD.THRESHOLD_REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_methods"]) == {
        MOD.METHOD_ENERGY_FLUX,
        MOD.METHOD_HF_ENVELOPE,
    }


def test_impulse_fixture_is_deterministic_and_within_thresholds():
    first = MOD.extract_fixture_record(ROOT, "impulse")
    second = MOD.extract_fixture_record(ROOT, "impulse")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["multi_method_agreement"]["status"] == "agree"
    assert first["decision"]["frame_exact_claim"] is True
    assert first["benchmark"]["within_registered_thresholds"] is True
    assert first["benchmark"]["sample_error"] is not None
    assert first["benchmark"]["sample_error"] <= 2
    assert len(first["method_results"]) >= 2


def test_silence_fixture_blocks_frame_exact_claim():
    record = MOD.extract_fixture_record(ROOT, "silence")
    assert record["decision"]["frame_exact_claim"] is False
    assert record["ambiguity"]["status"] == "blocked"
    assert "SILENCE_NO_FRAME_EXACT_ONSET" in record["ambiguity"]["reason_codes"] or (
        "NO_ONSET_DETECTED" in record["ambiguity"]["reason_codes"]
    )


def test_gradual_attack_requires_windowed_sync():
    record = MOD.extract_fixture_record(ROOT, "gradual_attack")
    assert record["ambiguity"]["status"] == "windowed"
    assert record["decision"]["frame_exact_claim"] is False
    assert "WINDOWED_SYNC_REQUIRED" in record["decision"]["blocker_codes"]


def test_stereo_disagree_preserves_ambiguity_or_block():
    record = MOD.extract_fixture_record(ROOT, "stereo_disagree")
    assert record["decision"]["frame_exact_claim"] is False
    assert record["ambiguity"]["status"] in {"multi_candidate", "blocked", "windowed"}
    assert record["multi_method_agreement"]["status"] in {
        "disagree",
        "insufficient_methods",
        "not_applicable",
        "agree",
    }
    if record["multi_method_agreement"]["status"] == "agree":
        assert record["ambiguity"]["status"] == "blocked"


def test_multi_hit_reports_positive_event_density():
    record = MOD.extract_fixture_record(ROOT, "multi_hit")
    assert record["event_density"] > 0
    assert record["decision"]["library_authority"] is False


def test_schema_rejects_single_method_results():
    record = MOD.extract_fixture_record(ROOT, "impulse")
    record["method_results"] = record["method_results"][:1]
    with pytest.raises(MOD.OnsetAnchorError, match="schema_validation_failed"):
        MOD.validate_anchor_record(ROOT, record)


def test_threshold_registry_revision_is_frozen():
    registry = MOD.load_threshold_registry(ROOT)
    assert registry["revision"] == MOD.THRESHOLD_REGISTRY_REVISION
    assert "impulse" in registry["event_families"]
    assert registry["event_families"]["impulse"]["max_sample_error"] == 2


def test_numpy_methods_agree_on_impulse_fixture():
    import numpy as np

    fixture = MOD.synthesize_fixture("impulse")
    left = np.asarray(fixture["channel_samples"][0], dtype=np.float32)
    right = np.asarray(fixture["channel_samples"][1], dtype=np.float32)
    mono = ((left + right) / 2.0).astype(np.float32)
    compact = MOD.detect_library_compact_from_mono(
        ROOT,
        mono=mono,
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=2,
        frame_count=fixture["frame_count"],
        asset_id="fixture:impulse",
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        relative_path="fixture/impulse.wav",
        extension=".wav",
        role="fixture",
        event_type="impulse",
        analysis_truncated=False,
    )
    assert compact["multi_method_agreement"] == "agree"
    assert compact["technical_onset_pass"] is True
    assert compact["onset_status"] == "pass"
    assert compact["library_authority"] is False
    assert abs(int(compact["onset_sample"]) - 512) <= 2


def test_library_packet_marks_reconcile_in_progress_when_retained_present():
    retained = {
        "authority": "accepted_index_retained_onset_reconcile",
        "coverage_complete": False,
        "counts": {"records_processed": 10, "records_total": 100, "onset_pass": 4},
        "receipt_path": "runtime_artifacts/onset_anchors/row072_index_retained_20260719/retained_index_onset_receipt.json",
        "records_path": "runtime_artifacts/onset_anchors/row072_index_retained_20260719/records.jsonl",
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "status": "HOLD_LIBRARY_RECONCILE_IN_PROGRESS",
    }
    payload = MOD.build_library_blocker_packet(ROOT, retained_runtime=retained)
    assert payload["decision"]["dependencies_unlocked"] is True
    assert payload["status"] == "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED"
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in payload["blocker_codes"]
    assert "FULL_LIBRARY_RECONCILE_IN_PROGRESS_TIME_BOUND" in payload["blocker_codes"]
    assert "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY" in payload["blocker_codes"]
    assert "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT" in payload["blocker_codes"]
    assert payload["row_complete"] is False
    assert payload["library_authority"] is False


def test_coverage_complete_with_unlabeled_strata_shortlist_keeps_both_blockers():
    retained_path = (
        ROOT
        / "runtime_artifacts"
        / "_pytest_row072_library_strata"
        / "coverage_complete_records.jsonl"
    )
    _write_retained_fixture(retained_path)
    try:
        strata = MOD.select_library_strata_candidates_from_retained(
            ROOT,
            retained_records_path=retained_path,
        )
    finally:
        if retained_path.is_file():
            retained_path.unlink()
        parent = retained_path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    retained = {
        "authority": "accepted_index_retained_onset_reconcile",
        "coverage_complete": True,
        "counts": {"records_processed": 39771, "records_total": 39771, "onset_pass": 6359},
        "receipt_path": "runtime_artifacts/onset_anchors/row072_index_retained_20260719/retained_index_onset_receipt.json",
        "records_path": "runtime_artifacts/onset_anchors/row072_index_retained_20260719/records.jsonl",
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
    }
    payload = MOD.build_library_blocker_packet(
        ROOT,
        retained_runtime=retained,
        strata_manifest=strata,
    )
    assert payload["status"] == (
        "HOLD_LIBRARY_THRESHOLDS_AND_BENCHMARK_STRATA_ABSENT_RECONCILE_COMPLETE"
    )
    assert payload["row_complete"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["product_completion"] is False
    assert payload["runtime_completion_claimed"] is True
    assert "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY" in payload["blocker_codes"]
    assert "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT" in payload["blocker_codes"]
    assert payload["library_benchmark_strata"]["candidates_selected"] == 10
    assert payload["library_benchmark_strata"]["truth_onset_status"] == "absent"
    assert payload["library_benchmark_strata"]["benchmark_strata_calibrated"] is False


def test_library_strata_selects_from_retained_records_without_authority():
    retained_path = (
        ROOT
        / "runtime_artifacts"
        / "_pytest_row072_library_strata"
        / "select_records.jsonl"
    )
    _write_retained_fixture(retained_path)
    try:
        strata = MOD.select_library_strata_candidates_from_retained(
            ROOT,
            retained_records_path=retained_path,
        )
        assert strata["authority"] == "candidate_shortlist_pending_truth_onsets"
        assert strata["selection_policy"] == "retained_records_only_no_pcm_decode_no_full_rescan"
        assert strata["counts"]["candidates_selected"] == 10
        assert strata["counts"]["strata_filled"] == 10
        assert strata["counts"]["truth_labeled"] == 0
        assert strata["counts"]["truth_unlabeled"] == 10
        assert strata["truth_onset_status"] == "absent"
        assert strata["decision"]["status"] == "blocked"
        assert strata["decision"]["library_authority"] is False
        assert strata["decision"]["row_complete"] is False
        assert strata["decision"]["product_completion"] is False
        assert strata["decision"]["threshold_authority_unfrozen"] is False
        assert strata["decision"]["benchmark_strata_calibrated"] is False
        assert MOD.BLOCKER_THRESHOLD_FROZEN in strata["blocker_codes"]
        assert MOD.BLOCKER_STRATA_ABSENT in strata["blocker_codes"]
        assert all(item["truth_label_status"] == "unlabeled" for item in strata["candidates"])
        assert all(item["truth_onset_sample"] is None for item in strata["candidates"])
        refs = strata["row109_synthetic_partition_references"]
        assert refs["partition_ids"] == [
            "train",
            "calibration",
            "held_out_test",
            "adversarial",
        ]
        assert refs["pcm_decode_authorized"] is False
        assert refs["library_authority"] is False
        MOD.validate_strata_manifest(ROOT, strata)
    finally:
        if retained_path.is_file():
            retained_path.unlink()
        parent = retained_path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()


def test_strata_registry_revision_is_frozen_pending_truth():
    registry = MOD.load_strata_registry(ROOT)
    assert registry["revision"] == MOD.STRATA_REGISTRY_REVISION
    assert registry["authority"] == "candidate_shortlist_pending_truth_onsets"
    assert registry["library_authority"] is False
    assert registry["row_complete"] is False
    assert registry["threshold_authority_unfrozen"] is False
    assert registry["truth_onset_status"] == "absent"
    assert len(registry["strata_targets"]) >= 8
    refs = registry["row109_synthetic_partition_references"]
    assert refs["partition_ids"] == [
        "train",
        "calibration",
        "held_out_test",
        "adversarial",
    ]
    assert refs["pcm_decode_authorized"] is False
    assert refs["library_authority"] is False


def test_row109_synthetic_partition_refs_bind_without_authority():
    refs = MOD.build_row109_synthetic_partition_references(ROOT)
    assert refs["authority"] == "synthetic_fixture_partition_references_only"
    assert refs["binding_scope"] == "synthetic_partition_ids_only"
    assert refs["partition_ids"] == list(MOD.ROW109_REQUIRED_PARTITION_IDS)
    assert refs["pcm_decode_authorized"] is False
    assert refs["threshold_authority_unfrozen"] is False
    assert refs["library_authority"] is False
    assert refs["tracker_id"] == "TRK-W64-109"
