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
