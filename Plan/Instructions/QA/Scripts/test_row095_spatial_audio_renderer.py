from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_spatial_audio_renderer.py"
SPEC = importlib.util.spec_from_file_location(
    "compile_wave64_spatial_audio_renderer", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependencies_fail_closed_on_current_hold_deltas():
    row088 = MOD.evaluate_row088_admission(ROOT)
    row091 = MOD.evaluate_row091_admission(ROOT)
    row093 = MOD.evaluate_row093_admission(ROOT)
    assert row088["dependency_satisfied"] is False
    assert row091["dependency_satisfied"] is False
    assert row093["dependency_satisfied"] is False
    assert "ROW088_DEPENDENCY_NOT_ACCEPTED" in row088["blocker_codes"]
    assert "ROW091_DEPENDENCY_NOT_ACCEPTED" in row091["blocker_codes"]
    assert "ROW093_DEPENDENCY_NOT_ACCEPTED" in row093["blocker_codes"]


def test_production_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_production_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["production_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row095_acceptance"] == "held"
    assert "ROW088_ROW091_ROW093_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "EVENT_DRIVEN_PRODUCTION_RENDERER_ABSENT" in payload["blocker_codes"]
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["registry_revision"] == MOD.REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert payload["adversarial_schema_probe"]["false_open_count"] == 0
    assert payload["planning_schema_boundary"]["planning_schema_remains_non_authority"] is True


def test_moving_source_fixture_is_deterministic_and_schema_valid():
    first = MOD.extract_fixture_manifest(ROOT, "moving_source_trajectory_pass")
    second = MOD.extract_fixture_manifest(ROOT, "moving_source_trajectory_pass")
    assert first == second
    assert first["validation"]["decision"] == "pass"
    assert first["validation"]["trajectory_pass"] is True
    assert first["production_authority"] is False
    assert first["is_synthetic"] is True
    assert first["sources"][0]["trajectory"][0]["azimuth_deg"] < 0
    assert first["sources"][0]["trajectory"][1]["azimuth_deg"] > 0


def test_occlusion_offscreen_fixture_marks_continuity_gates():
    record = MOD.extract_fixture_manifest(ROOT, "time_varying_occlusion_offscreen")
    end = record["sources"][0]["trajectory"][1]
    assert end["offscreen"] is True
    assert end["visibility"] == "offscreen"
    assert end["occlusion_amount"] > 0.5
    assert record["validation"]["offscreen_continuity_pass"] is True
    assert record["validation"]["occlusion_pass"] is True


def test_reject_wet_source_and_unknown_room_remain_blocked():
    reject = MOD.extract_fixture_manifest(ROOT, "reject_wet_source_blocked")
    unknown = MOD.extract_fixture_manifest(ROOT, "unknown_room_blocked")
    assert reject["sources"][0]["wet_source_policy"] == "reject"
    assert reject["validation"]["decision"] == "blocked"
    assert "WET_SOURCE_REJECT_POLICY" in reject["decision"]["blocker_codes"]
    assert unknown["room"]["authority"] == "unknown"
    assert unknown["validation"]["decision"] == "blocked"
    assert "UNKNOWN_ROOM_AUTHORITY" in unknown["decision"]["blocker_codes"]


def test_gate_failure_fixture_blocks_phase_loudness_clipping():
    record = MOD.extract_fixture_manifest(ROOT, "gate_failure_blocked")
    assert record["validation"]["phase_pass"] is False
    assert record["validation"]["loudness_pass"] is False
    assert record["validation"]["clipping_pass"] is False
    assert record["validation"]["decision"] == "blocked"


def test_seven_planning_false_open_cases_are_rejected():
    cases = MOD.adversarial_false_open_cases(ROOT)
    assert len(cases) == 7
    assert all(case["false_open"] is False for case in cases)
    assert all(case["schema_accepted"] is False for case in cases)


def test_schema_rejects_production_authority_true_on_synthetic():
    record = MOD.extract_fixture_manifest(ROOT, "moving_source_trajectory_pass")
    mutated = deepcopy(record)
    mutated["production_authority"] = True
    mutated["is_synthetic"] = False
    mutated["decision"].update(
        {
            "status": "accepted",
            "row095_acceptance": "accepted",
            "product_completion": True,
            "runtime_completion": True,
            "promotion_eligible": False,
        }
    )
    with pytest.raises(
        MOD.SpatialAudioRendererError,
        match="production_authority_forbidden|schema_validation_failed:production_authority",
    ):
        MOD.validate_manifest(ROOT, mutated)


def test_schema_rejects_pass_with_false_gates():
    record = MOD.extract_fixture_manifest(ROOT, "moving_source_trajectory_pass")
    mutated = deepcopy(record)
    mutated["validation"]["phase_pass"] = False
    with pytest.raises(MOD.SpatialAudioRendererError, match="schema_validation_failed"):
        MOD.validate_manifest(ROOT, mutated)
