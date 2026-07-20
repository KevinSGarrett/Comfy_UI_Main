from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
SPEC = importlib.util.spec_from_file_location("extract_wave64_waveform_features", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row070_admission_reads_accepted_library_pcm_authority():
    admission = MOD.evaluate_row070_admission(ROOT)
    assert admission["dependency_satisfied"] is True
    assert admission["blocker_codes"] == []
    assert admission["row_complete"] is True


def test_library_mode_without_retained_runtime_stays_fail_closed():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["implementation_completion_claimed"] is False
    assert payload["decision"]["product_completion"] is False
    assert payload["bs1770_methods_wired"] is True
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "BS1770_LOUDNESS_AUTHORITY_NOT_WIRED" not in payload["blocker_codes"]
    assert payload["feature_pipeline_revision"] == MOD.FEATURE_PIPELINE_REVISION
    assert set(payload["required_features"]) == set(MOD.REQUIRED_FEATURES)
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert payload["method_provenance"]["integrated_loudness"]["method_id"].startswith("bs1770_")
    assert payload["method_provenance"]["true_peak"]["method_id"].startswith("bs1770_")
    assert payload["library_authority"] is False
    assert payload["row_complete"] is False
    assert payload["decision"]["status"] == "blocked"


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "tone_1k")
    second = MOD.extract_fixture_record(ROOT, "tone_1k")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["features"]["clipping"] is False
    # 1 kHz tone at 48 kHz should place spectral mass near 1000 Hz.
    assert 800.0 <= first["features"]["spectral_centroid"] <= 1200.0
    assert first["features"]["channel_correlation"] == pytest.approx(1.0, abs=1e-6)
    assert math.isfinite(first["features"]["integrated_loudness"])
    assert math.isfinite(first["features"]["true_peak"])


def test_stereo_anticorrelated_fixture_reports_negative_correlation():
    record = MOD.extract_fixture_record(ROOT, "stereo_anticorrelated")
    assert record["features"]["channel_correlation"] == pytest.approx(-1.0, abs=1e-6)


def test_impulse_fixture_sets_high_crest_and_no_library_authority():
    record = MOD.extract_fixture_record(ROOT, "impulse")
    assert record["features"]["crest_factor"] > 10.0
    assert record["features"]["true_peak"] > -6.0
    assert record["decision"]["library_authority"] is False


def test_method_provenance_covers_required_feature_set():
    assert set(MOD.METHOD_PROVENANCE) == set(MOD.REQUIRED_FEATURES)
    for binding in MOD.METHOD_PROVENANCE.values():
        assert binding["method_id"]
        assert binding["unit"]
        assert binding["window"]
    assert MOD.bs1770_authority_wired() is True


def test_schema_rejects_incomplete_feature_set():
    record = MOD.extract_fixture_record(ROOT, "silence")
    del record["features"]["rms"]
    with pytest.raises(MOD.WaveformFeatureError, match="schema_validation_failed"):
        MOD.validate_feature_record(ROOT, record)


def test_bs1770_silence_stays_at_or_below_absolute_gate_floor():
    record = MOD.extract_fixture_record(ROOT, "silence")
    assert record["features"]["integrated_loudness"] <= MOD.BS1770_ABSOLUTE_GATE_LUFS
    assert record["features"]["true_peak"] <= MOD.SILENCE_FLOOR_DBTP


def test_leading_power_of_two_window_supports_non_pot_signals():
    # 3000 frames is not power-of-two; spectral path must truncate without mutating source hash path.
    frames = 3000
    sr = 48000
    tone = [0.25 * math.sin(2.0 * math.pi * 1000.0 * (i / sr)) for i in range(frames)]
    features, analysis = MOD.extract_features_from_channels([tone, tone], sample_rate_hz=sr)
    assert analysis["policy"] == "leading_power_of_two_truncated_capped"
    assert analysis["source_frame_count"] == frames
    assert analysis["analysis_frame_count"] == 2048
    assert math.isfinite(features["integrated_loudness"])
    assert math.isfinite(features["true_peak"])
    assert features["spectral_centroid"] >= 0.0


def test_retained_reconcile_allows_feature_extraction_failed_residuals():
    retained = {
        "coverage_complete": True,
        "counts": {
            "feature_pass": 39011,
            "feature_hold": 0,
            "exact_blockers": 760,
            "decode_pass_inputs": 39024,
            "decode_non_pass_inputs": 747,
            "records_processed": 39771,
            "records_total": 39771,
        },
        "blocker_histogram": {
            "DECODE_FAILED_CORRUPT_OR_UNREADABLE": 747,
            "FEATURE_EXTRACTION_FAILED": 13,
        },
    }
    assert MOD.retained_feature_reconcile_counts_consistent(retained) is True
    packet = MOD.build_library_blocker_packet(ROOT, retained_feature_runtime=retained)
    assert "FEATURE_RECONCILE_COUNT_MISMATCH" not in packet["blocker_codes"]
    assert packet["library_authority"] is True
    assert packet["decision"]["status"] == "pass"
    assert packet["status"] == "PASS_LIBRARY_FEATURE_AUTHORITY_ACCEPTED_NO_PRODUCT_COMPLETION"
    assert packet["decision"]["product_completion"] is False
