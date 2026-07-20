from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/analyze_wave64_audio_reverb_dryness.py"
SPEC = importlib.util.spec_from_file_location("analyze_wave64_audio_reverb_dryness", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row071_accepted_and_row073_probe_unlocked_for_probe_gate():
    row071 = MOD.evaluate_row071_admission(ROOT)
    row073 = MOD.evaluate_row073_admission(ROOT)
    assert row071["dependency_satisfied"] is True
    assert row071["row_complete"] is True
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
    assert payload["decision"]["row076_acceptance"] == "held"
    assert "ROW071_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["status"] == "HOLD_LIBRARY_RUNTIME_AND_ROOM_CALIBRATION_ABSENT_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["analysis_pipeline_revision"] == MOD.ANALYSIS_PIPELINE_REVISION
    assert payload["thresholds"]["suggestion_only"] is True
    assert payload["thresholds"]["source_mutation_allowed"] is False
    assert payload["fixture_calibration"]["fixture_count"] == len(MOD.FIXTURE_NAMES)


def test_library_mode_with_probe_runtime_marks_probe_hold():
    retained = {
        "coverage_complete": False,
        "limit": 25,
        "counts": {"records_processed": 25, "reverb_pass": 20, "reverb_blocked": 5},
        "blocker_histogram": {"REVERB_EXTRACTION_FAILED": 5},
        "records_path": "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/records.jsonl",
        "progress_path": "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/progress.json",
        "receipt_path": (
            "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/"
            "retained_index_reverb_receipt.json"
        ),
        "status": "RUNTIME_PASS_BOUNDED_PROBE_LIMIT",
        "row075_contention_policy": "limited_probe_only_while_row075_full_reconcile_owns_pcm_io",
    }
    payload = MOD.build_library_blocker_packet(ROOT, retained_runtime=retained)
    assert payload["status"] == "HOLD_LIBRARY_PROBE_PASS_FULL_RECONCILE_DEFERRED_DEPS_UNLOCKED"
    assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    assert payload["runtime_completion_claimed"] is False
    assert payload["accepted_index_retained_reverb_runtime"]["present"] is True
    assert payload["accepted_index_retained_reverb_runtime"]["limit"] == 25
    assert payload["decision"]["product_completion"] is False


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "dry_impulse")
    second = MOD.extract_fixture_record(ROOT, "dry_impulse")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["suggestion_only"] is True
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["decision"]["double_reverb_guard_enforced"] is True
    assert first["source_before_sha256"] == first["source_after_sha256"]
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]


def test_dry_impulse_classifies_dry_and_allows_convolution():
    record = MOD.extract_fixture_record(ROOT, "dry_impulse")
    assert record["classification"] == "dry"
    assert record["wet_source_policy"] == "dry_render"
    assert record["measurements"]["additional_convolution_safe"] is True
    assert record["measurements"]["rt60_seconds"] <= MOD.THRESHOLDS["rt60_dry_max_s"]


def test_wet_exponential_tail_rejects_double_reverb():
    record = MOD.extract_fixture_record(ROOT, "wet_exponential_tail")
    assert record["classification"] == "wet"
    assert record["wet_source_policy"] == "reject"
    assert record["measurements"]["additional_convolution_safe"] is False
    assert record["decision"]["double_reverb_guard_enforced"] is True
    assert record["measurements"]["rt60_seconds"] >= MOD.THRESHOLDS["rt60_wet_min_s"]
    assert record["measurements"]["direct_to_reverberant_ratio_db"] <= MOD.THRESHOLDS["wet_drr_max_db"]


def test_wet_stereo_room_reports_stereo_imprint_and_rejects_without_rule():
    record = MOD.extract_fixture_record(ROOT, "wet_stereo_room")
    assert record["classification"] == "wet"
    assert record["wet_source_policy"] == "reject"
    assert record["measurements"]["stereo_room_imprint"]["width_score"] > 0.0
    assert record["measurements"]["compatible_room_rule_id"] is None


def test_compatible_room_passthrough_requires_explicit_rule_id():
    record = MOD.extract_fixture_record(
        ROOT,
        "wet_exponential_tail",
        compatible_room_rule_id="compatible_room_rule_fixture_v1",
    )
    assert record["classification"] == "wet"
    assert record["wet_source_policy"] == "compatible_wet_passthrough"
    assert record["measurements"]["additional_convolution_safe"] is False
    assert record["measurements"]["compatible_room_rule_id"] == "compatible_room_rule_fixture_v1"
    assert record["decision"]["double_reverb_guard_enforced"] is True


def test_ambiguous_and_noise_fixtures_limit_processing():
    ambiguous = MOD.extract_fixture_record(ROOT, "ambiguous_medium_tail")
    noise = MOD.extract_fixture_record(ROOT, "mono_noise")
    assert ambiguous["classification"] in {"ambiguous", "dry", "wet"}
    if ambiguous["classification"] == "ambiguous":
        assert ambiguous["wet_source_policy"] == "limited_processing"
        assert ambiguous["measurements"]["additional_convolution_safe"] is False
    assert noise["classification"] in {"ambiguous", "dry", "wet"}
    if noise["classification"] == "ambiguous":
        assert noise["wet_source_policy"] == "limited_processing"


def test_method_provenance_covers_required_measurement_set():
    required = {
        "direct_to_reverberant",
        "rt60",
        "early_reflections",
        "stereo_room_imprint",
        "reverb_tail",
        "double_reverb_guard",
    }
    assert set(MOD.METHOD_PROVENANCE) == required
    for binding in MOD.METHOD_PROVENANCE.values():
        assert binding["method_id"]
        assert binding["unit"]
        assert binding["window"]


def test_schema_rejects_missing_drr_measurement():
    record = MOD.extract_fixture_record(ROOT, "dry_tone_burst")
    del record["measurements"]["direct_to_reverberant_ratio_db"]
    with pytest.raises(MOD.AudioReverbDrynessError, match="schema_validation_failed"):
        MOD.validate_analysis_record(ROOT, record)
