from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_reference_audio_variation.py"
SPEC = importlib.util.spec_from_file_location(
    "evaluate_wave64_reference_audio_variation", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_including_absent_row098_row099():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-072",
        "TRK-W64-073",
        "TRK-W64-083",
        "TRK-W64-098",
        "TRK-W64-099",
    }
    # Row068 rights authority may already be accepted; remaining prerequisites
    # must still fail closed so library variation cannot falsely complete.
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    for tracker_id in (
        "TRK-W64-072",
        "TRK-W64-073",
        "TRK-W64-083",
        "TRK-W64-098",
        "TRK-W64-099",
    ):
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False
        assert admission["row_complete"] is False
        assert admission["blocker_codes"]
    assert "TRK_W64_098_DEPENDENCY_NOT_ACCEPTED" in admissions["TRK-W64-098"][
        "blocker_codes"
    ]
    assert "TRK_W64_099_DEPENDENCY_NOT_ACCEPTED" in admissions["TRK-W64-099"][
        "blocker_codes"
    ]
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is True
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row100_acceptance"] == "held"
    assert "ROW100_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "REFERENCE_CONDITIONED_VARIATION_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "ROW098_SOUND_VARIATION_ENGINE_AUTHORITY_ABSENT" in payload["blocker_codes"]
    assert "ROW099_NEURAL_TEXT_TO_AUDIO_ROUTER_AUTHORITY_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 9
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_clean_reference_variation_accept_is_deterministic_fixture_only():
    first = MOD.extract_fixture_record(ROOT, "clean_reference_variation_accept")
    second = MOD.extract_fixture_record(ROOT, "clean_reference_variation_accept")
    assert first == second
    assert first["decision"]["route"] == "accept_candidate"
    assert first["decision"]["status"] == "pass"
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["decision"]["row100_acceptance"] == "fixture_only"
    assert first["source_pcm_sha256"] != first["candidate_pcm_sha256"]
    assert all(result["status"] == "pass" for result in first["gate_results"].values())


def test_derivative_rights_rejected():
    record = MOD.extract_fixture_record(ROOT, "derivative_rights_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "DERIVATIVE_RIGHTS_DENIED" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["source_rights"]["status"] == "fail"


def test_conditioning_strength_out_of_bounds_rejected():
    record = MOD.extract_fixture_record(
        ROOT, "conditioning_strength_out_of_bounds_rejected"
    )
    assert record["decision"]["route"] == "reject_candidate"
    assert "CONDITIONING_STRENGTH_TOO_HIGH" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["conditioning_strength"]["status"] == "fail"


def test_structure_not_preserved_rejected():
    record = MOD.extract_fixture_record(ROOT, "structure_not_preserved_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "STRUCTURE_NOT_PRESERVED" in record["decision"]["blocker_codes"]
    assert "IDENTITY_DRIFT_EXCEEDED" in record["decision"]["blocker_codes"]


def test_variation_too_weak_rejected():
    record = MOD.extract_fixture_record(ROOT, "variation_too_weak_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "VARIATION_TOO_WEAK" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["variation_measure"]["status"] == "fail"


def test_variation_too_strong_identity_drift_rejected():
    record = MOD.extract_fixture_record(
        ROOT, "variation_too_strong_identity_drift_rejected"
    )
    assert record["decision"]["route"] == "reject_candidate"
    assert "VARIATION_TOO_STRONG" in record["decision"]["blocker_codes"]
    assert "IDENTITY_DRIFT_EXCEEDED" in record["decision"]["blocker_codes"]


def test_timing_loss_rejected():
    record = MOD.extract_fixture_record(ROOT, "timing_loss_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "ONSET_TIMING_LOSS" in record["decision"]["blocker_codes"]
    assert "ENDPOINT_TIMING_LOSS" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["structure_preservation"]["status"] == "fail"


def test_unwanted_speech_rejected():
    record = MOD.extract_fixture_record(ROOT, "unwanted_speech_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "UNWANTED_SPEECH" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["unexpected_class_reject"]["status"] == "fail"


def test_unwanted_music_rejected():
    record = MOD.extract_fixture_record(ROOT, "unwanted_music_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "UNWANTED_MUSIC" in record["decision"]["blocker_codes"]


def test_semantic_validator_rejects_accept_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "derivative_rights_rejected")
    mutated = deepcopy(record)
    mutated["decision"]["route"] = "accept_candidate"
    mutated["decision"]["status"] = "pass"
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.ReferenceAudioVariationError, match="failed_gates_cannot_accept"):
        MOD.validate_evaluation_semantics(mutated)


def test_schema_rejects_missing_signals_field():
    record = MOD.extract_fixture_record(ROOT, "clean_reference_variation_accept")
    mutated = deepcopy(record)
    del mutated["signals"]
    with pytest.raises(Exception):
        MOD.validate_evaluation_record(ROOT, mutated)
