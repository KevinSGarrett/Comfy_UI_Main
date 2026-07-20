from __future__ import annotations

import importlib.util
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
    assert payload["row_complete"] is False
    assert payload["library_authority"] is False
