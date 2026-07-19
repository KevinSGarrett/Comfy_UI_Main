from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_generated_sound_qa.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_generated_sound_qa", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_including_held_or_absent_row102():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-071",
        "TRK-W64-072",
        "TRK-W64-075",
        "TRK-W64-076",
        "TRK-W64-079",
        "TRK-W64-083",
        "TRK-W64-102",
    }
    for tracker_id in admissions:
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False
        assert admission["row_complete"] is False
        assert admission["blocker_codes"]
    row102_codes = set(admissions["TRK-W64-102"]["blocker_codes"])
    assert row102_codes & {
        "TRK_W64_102_DELTA_ABSENT",
        "TRK_W64_102_DEPENDENCY_NOT_ACCEPTED",
    }
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row103_acceptance"] == "held"
    assert "ROW103_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_GENERATED_SOUND_QA_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 9
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_clean_multi_signal_accept_is_deterministic_fixture_only():
    first = MOD.extract_fixture_record(ROOT, "clean_multi_signal_accept")
    second = MOD.extract_fixture_record(ROOT, "clean_multi_signal_accept")
    assert first == second
    assert first["decision"]["route"] == "accept_candidate"
    assert first["decision"]["status"] == "pass"
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["decision"]["row103_acceptance"] == "fixture_only"
    assert all(result["status"] == "pass" for result in first["gate_results"].values())


def test_semantic_mismatch_rejected():
    record = MOD.extract_fixture_record(ROOT, "semantic_mismatch_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "SEMANTIC_MISMATCH" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["semantic_qa"]["status"] == "fail"


def test_extra_event_rejected():
    record = MOD.extract_fixture_record(ROOT, "extra_event_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "EXTRA_EVENTS" in record["decision"]["blocker_codes"]


def test_timing_defect_rejected():
    record = MOD.extract_fixture_record(ROOT, "timing_defect_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "ONSET_OFFSET_EXCEEDED" in record["decision"]["blocker_codes"]
    assert "ENDPOINT_DRIFT_EXCEEDED" in record["decision"]["blocker_codes"]


def test_technical_defect_rejected():
    record = MOD.extract_fixture_record(ROOT, "technical_defect_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "CLIPPING" in record["decision"]["blocker_codes"]
    assert "TRUE_PEAK_EXCEEDED" in record["decision"]["blocker_codes"]
    assert "SPECTRAL_DEFECT" in record["decision"]["blocker_codes"]


def test_unsuitable_acoustics_rejected():
    record = MOD.extract_fixture_record(ROOT, "unsuitable_acoustics_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "UNSUITABLE_ACOUSTICS" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["acoustic_qa"]["status"] == "fail"


def test_near_duplicate_rejected():
    record = MOD.extract_fixture_record(ROOT, "near_duplicate_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "NEAR_DUPLICATE" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["dedup"]["status"] == "fail"


def test_single_metric_cannot_grant_authority():
    record = MOD.extract_fixture_record(ROOT, "single_metric_cannot_grant_authority")
    assert record["decision"]["route"] == "reject_candidate"
    assert "SINGLE_METRIC_AUTHORITY_DENIED" in record["decision"]["blocker_codes"]
    assert record["signals"]["model_metric_score"] >= 0.99
    assert record["signals"]["semantic_score"] < 0.78


def test_failed_candidate_immutable_negative_evidence():
    record = MOD.extract_fixture_record(
        ROOT, "failed_candidate_immutable_negative_evidence"
    )
    assert record["decision"]["route"] == "reject_candidate"
    assert "NEGATIVE_EVIDENCE_REWRITE_BLOCKED" in record["decision"]["blocker_codes"]
    assert record["negative_evidence"]["immutable"] is True
    assert record["negative_evidence"]["retained"] is True
    assert record["negative_evidence"]["rewrite_blocked"] is True
    assert "CLIPPING" in record["negative_evidence"]["prior_failure_codes"]


def test_semantic_validator_rejects_accept_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "semantic_mismatch_rejected")
    mutated = deepcopy(record)
    mutated["decision"]["route"] = "accept_candidate"
    mutated["decision"]["status"] = "pass"
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.GeneratedSoundQAError, match="failed_gates_cannot_accept"):
        MOD.validate_evaluation_semantics(mutated)


def test_schema_rejects_missing_negative_evidence_field():
    record = MOD.extract_fixture_record(ROOT, "clean_multi_signal_accept")
    mutated = deepcopy(record)
    del mutated["negative_evidence"]
    with pytest.raises(Exception):
        MOD.validate_evaluation_record(ROOT, mutated)
