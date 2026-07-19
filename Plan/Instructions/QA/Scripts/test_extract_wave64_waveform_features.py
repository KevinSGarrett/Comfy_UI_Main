from __future__ import annotations

import importlib.util
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


def test_row070_admission_fails_closed_on_current_hold_delta():
    admission = MOD.evaluate_row070_admission(ROOT)
    assert admission["dependency_satisfied"] is False
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" in admission["blocker_codes"]
    assert admission["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["feature_pipeline_revision"] == MOD.FEATURE_PIPELINE_REVISION
    assert set(payload["required_features"]) == set(MOD.REQUIRED_FEATURES)
    assert payload["fixture_calibration"]["fixture_count"] == 5


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


def test_stereo_anticorrelated_fixture_reports_negative_correlation():
    record = MOD.extract_fixture_record(ROOT, "stereo_anticorrelated")
    assert record["features"]["channel_correlation"] == pytest.approx(-1.0, abs=1e-6)


def test_impulse_fixture_sets_high_crest_and_no_library_authority():
    record = MOD.extract_fixture_record(ROOT, "impulse")
    assert record["features"]["crest_factor"] > 10.0
    assert record["decision"]["library_authority"] is False


def test_method_provenance_covers_required_feature_set():
    assert set(MOD.METHOD_PROVENANCE) == set(MOD.REQUIRED_FEATURES)
    for binding in MOD.METHOD_PROVENANCE.values():
        assert binding["method_id"]
        assert binding["unit"]
        assert binding["window"]


def test_schema_rejects_incomplete_feature_set():
    record = MOD.extract_fixture_record(ROOT, "silence")
    del record["features"]["rms"]
    with pytest.raises(MOD.WaveformFeatureError, match="schema_validation_failed"):
        MOD.validate_feature_record(ROOT, record)
