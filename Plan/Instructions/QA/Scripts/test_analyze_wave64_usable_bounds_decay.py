from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/analyze_wave64_usable_bounds_decay.py"
SPEC = importlib.util.spec_from_file_location("analyze_wave64_usable_bounds_decay", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row071_accepted_and_row072_runtime_unlocked_for_probe_gate():
    row071 = MOD.evaluate_row071_admission(ROOT)
    row072 = MOD.evaluate_row072_admission(ROOT)
    assert row071["dependency_satisfied"] is True
    assert row071["row_complete"] is True
    assert row072["dependency_satisfied"] is True
    assert row072["admission_mode"] == "runtime_unlocked"
    assert row072["row_complete"] is False
    assert row072["row072_acceptance"] == "held"
    assert row072["proof_tier"] == "RUNTIME_PASS_BOUNDED"


def test_library_mode_emits_deps_unlocked_hold_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row073_acceptance"] == "held"
    assert "ROW071_AND_ROW072_DEPENDENCIES_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["status"] == "HOLD_LIBRARY_RUNTIME_AND_STRATA_ABSENT_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["analysis_pipeline_revision"] == MOD.ANALYSIS_PIPELINE_REVISION
    assert payload["thresholds"]["suggestion_only"] is True
    assert payload["thresholds"]["destructive_trim_allowed"] is False
    assert payload["fixture_calibration"]["fixture_count"] == 5


def test_library_mode_with_probe_runtime_marks_probe_hold():
    retained = {
        "coverage_complete": False,
        "limit": 25,
        "counts": {"records_processed": 25, "bounds_pass": 20, "bounds_blocked": 5},
        "blocker_histogram": {"BOUNDS_EXTRACTION_FAILED": 5},
        "records_path": "runtime_artifacts/usable_bounds/row073_index_retained_20260720/records.jsonl",
        "progress_path": "runtime_artifacts/usable_bounds/row073_index_retained_20260720/progress.json",
        "receipt_path": "runtime_artifacts/usable_bounds/row073_index_retained_20260720/retained_index_bounds_receipt.json",
        "status": "RUNTIME_PASS_BOUNDED_PROBE_LIMIT",
        "row075_contention_policy": "limited_probe_only_while_row075_full_reconcile_owns_pcm_io",
    }
    payload = MOD.build_library_blocker_packet(ROOT, retained_runtime=retained)
    assert payload["status"] == "HOLD_LIBRARY_PROBE_PASS_FULL_RECONCILE_DEFERRED_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["runtime_completion_claimed"] is False
    assert payload["accepted_index_retained_bounds_runtime"]["present"] is True
    assert payload["accepted_index_retained_bounds_runtime"]["limit"] == 25
    assert payload["decision"]["product_completion"] is False


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "padded_tone")
    second = MOD.extract_fixture_record(ROOT, "padded_tone")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["suggestion_only"] is True
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["source_before_sha256"] == first["source_after_sha256"]
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["measurements"]["leading_silence_samples"] >= 700
    assert first["measurements"]["trailing_silence_samples"] >= 700
    assert first["measurements"]["usable_start_sample"] < first["measurements"]["usable_end_sample"]
    assert first["measurements"]["onset_preservation_ok"] is True
    assert first["measurements"]["tail_preservation_ok"] is True


def test_silence_fixture_reports_full_silence_bounds():
    record = MOD.extract_fixture_record(ROOT, "silence")
    assert record["measurements"]["leading_silence_samples"] == record["frame_count"]
    assert record["measurements"]["usable_start_sample"] == 0
    assert record["measurements"]["usable_end_sample"] == 0


def test_impulse_decay_fixture_preserves_natural_tail():
    record = MOD.extract_fixture_record(ROOT, "impulse_decay")
    assert record["measurements"]["attack_seconds"] == pytest.approx(0.0, abs=1e-9)
    assert record["measurements"]["natural_decay_end_sample"] > record["measurements"]["usable_start_sample"]
    assert record["measurements"]["tail_preservation_ok"] is True


def test_gradual_attack_fixture_reports_nonzero_attack():
    record = MOD.extract_fixture_record(ROOT, "gradual_attack")
    assert record["measurements"]["attack_seconds"] > 0.01
    assert record["measurements"]["onset_preservation_ok"] is True


def test_method_provenance_covers_required_measurement_set():
    required = {
        "leading_silence",
        "trailing_silence",
        "usable_bounds",
        "attack",
        "sustain",
        "release",
        "noise_only_tail",
        "natural_decay",
    }
    assert set(MOD.METHOD_PROVENANCE) == required
    for binding in MOD.METHOD_PROVENANCE.values():
        assert binding["method_id"]
        assert binding["unit"]
        assert binding["window"]


def test_schema_rejects_missing_usable_bounds():
    record = MOD.extract_fixture_record(ROOT, "noisy_tail")
    del record["measurements"]["usable_start_sample"]
    with pytest.raises(MOD.UsableBoundsDecayError, match="schema_validation_failed"):
        MOD.validate_analysis_record(ROOT, record)


def test_compact_bounds_pass_withholds_library_authority():
    compact = MOD.build_compact_bounds_record(
        relative_path="demo/a.wav",
        extension=".wav",
        role="evaluation",
        event_type="evaluation_reference",
        asset_id="index:demo/a.wav",
        feature_status="pass",
        measurements={
            "leading_silence_samples": 10,
            "trailing_silence_samples": 10,
            "usable_start_sample": 10,
            "usable_end_sample": 100,
            "attack_seconds": 0.01,
            "sustain_seconds": 0.02,
            "release_seconds": 0.03,
            "noise_only_tail": False,
            "natural_decay_end_sample": 100,
            "onset_preservation_ok": True,
            "tail_preservation_ok": True,
        },
        source_sha256="a" * 64,
        canonical_pcm_sha256="b" * 64,
        sample_rate_hz=48000,
        channels=2,
        frame_count=200,
        pcm_sha_verified=True,
        source_immutable=True,
        analysis_truncated=False,
        blocker_code=None,
        blocker_codes=[],
    )
    assert compact["bounds_status"] == "pass"
    assert compact["technical_bounds_pass"] is True
    assert compact["library_authority"] is False
    assert compact["suggestion_only"] is True
    assert compact["blocker_codes"] == ["LIBRARY_AUTHORITY_NOT_GRANTED"]
