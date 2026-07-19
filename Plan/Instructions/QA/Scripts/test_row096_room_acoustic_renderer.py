from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_room_acoustic_renderer.py"
SPEC = importlib.util.spec_from_file_location(
    "compile_wave64_room_acoustic_renderer", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependencies_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-076",
        "TRK-W64-088",
        "TRK-W64-089",
        "TRK-W64-095",
    }
    for tracker_id, admission in admissions.items():
        assert admission["dependency_satisfied"] is False, tracker_id
        assert admission["row_complete"] is False, tracker_id
        assert admission["blocker_codes"], tracker_id


def test_production_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_production_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["production_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row096_acceptance"] == "held"
    assert (
        "ROW076_ROW088_ROW089_ROW095_DEPENDENCIES_NOT_ACCEPTED"
        in payload["blocker_codes"]
    )
    assert "EVENT_DRIVEN_ROOM_ACOUSTIC_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "MEASURED_RIR_SELECTION_OR_SYNTHESIS_ABSENT" in payload["blocker_codes"]
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["registry_revision"] == MOD.REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert payload["adversarial_schema_probe"]["false_open_count"] == 0
    assert payload["planning_schema_boundary"]["planning_schema_remains_non_authority"] is True
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_measured_rir_fixture_is_deterministic_and_schema_valid():
    first = MOD.extract_fixture_manifest(ROOT, "measured_rir_convolution_pass")
    second = MOD.extract_fixture_manifest(ROOT, "measured_rir_convolution_pass")
    assert first == second
    assert first["validation"]["decision"] == "pass"
    assert first["validation"]["rir_pass"] is True
    assert first["validation"]["rt60_pass"] is True
    assert first["production_authority"] is False
    assert first["is_synthetic"] is True
    assert first["convolution"]["deterministic"] is True
    assert first["wet_source"]["policy"] == "dry_render"


def test_early_reflection_rt60_fixture_marks_tolerance_gates():
    record = MOD.extract_fixture_manifest(ROOT, "early_reflection_rt60_pass")
    assert record["validation"]["early_reflections_pass"] is True
    assert record["validation"]["rt60_pass"] is True
    assert record["early_reflections"]["reflection_count"] >= 4
    assert record["validation"]["rt60_error_seconds"] <= 0.05
    assert record["decision"]["row096_acceptance"] == "fixture_only"


def test_reject_wet_source_and_unknown_room_remain_blocked():
    reject = MOD.extract_fixture_manifest(ROOT, "reject_wet_source_blocked")
    unknown = MOD.extract_fixture_manifest(ROOT, "unknown_room_geometry_blocked")
    assert reject["wet_source"]["policy"] == "reject"
    assert reject["validation"]["decision"] == "blocked"
    assert reject["validation"]["wet_source_guard_pass"] is False
    assert "WET_SOURCE_REJECT_POLICY" in reject["decision"]["blocker_codes"]
    assert unknown["room"]["authority"] == "unknown"
    assert unknown["validation"]["decision"] == "blocked"
    assert unknown["validation"]["room_geometry_pass"] is False
    assert "UNKNOWN_ROOM_AUTHORITY" in unknown["decision"]["blocker_codes"]
    assert "MATERIAL_ABSORPTION_MISSING" in unknown["decision"]["blocker_codes"]


def test_gate_failure_fixture_blocks_rir_early_reflection_rt60():
    record = MOD.extract_fixture_manifest(ROOT, "gate_failure_blocked")
    assert record["validation"]["rir_pass"] is False
    assert record["validation"]["early_reflections_pass"] is False
    assert record["validation"]["rt60_pass"] is False
    assert record["validation"]["decision"] == "blocked"
    assert "RT60_TOLERANCE_FAILED" in record["decision"]["blocker_codes"]


def test_seven_false_open_cases_are_rejected():
    cases = MOD.adversarial_false_open_cases(ROOT)
    assert len(cases) == 7
    assert all(case["false_open"] is False for case in cases)
    assert all(case["schema_accepted"] is False for case in cases)


def test_schema_rejects_production_authority_true_on_synthetic():
    record = MOD.extract_fixture_manifest(ROOT, "measured_rir_convolution_pass")
    mutated = deepcopy(record)
    mutated["production_authority"] = True
    mutated["is_synthetic"] = False
    mutated["decision"].update(
        {
            "status": "accepted",
            "row096_acceptance": "accepted",
            "product_completion": True,
            "runtime_completion": True,
            "promotion_eligible": False,
        }
    )
    with pytest.raises(
        MOD.RoomAcousticRendererError,
        match="production_authority_forbidden|schema_validation_failed:production_authority",
    ):
        MOD.validate_manifest(ROOT, mutated)


def test_schema_rejects_pass_with_false_gates():
    record = MOD.extract_fixture_manifest(ROOT, "measured_rir_convolution_pass")
    mutated = deepcopy(record)
    mutated["validation"]["rt60_pass"] = False
    with pytest.raises(MOD.RoomAcousticRendererError, match="schema_validation_failed"):
        MOD.validate_manifest(ROOT, mutated)


def test_semantic_validator_rejects_wet_source_reject_pass():
    record = MOD.extract_fixture_manifest(ROOT, "reject_wet_source_blocked")
    mutated = deepcopy(record)
    mutated["validation"]["decision"] = "pass"
    mutated["validation"]["wet_source_guard_pass"] = True
    with pytest.raises(
        MOD.RoomAcousticRendererError,
        match="reject_wet_source_cannot_pass|schema_validation_failed",
    ):
        MOD.validate_manifest(ROOT, mutated)
