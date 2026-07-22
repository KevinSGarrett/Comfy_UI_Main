from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_audio_av_qa_matrix.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_audio_av_qa_matrix", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependencies_are_hash_bound_and_held():
    admissions = MOD.dependency_admissions(ROOT)
    assert set(admissions) == set(MOD.DEPENDENCY_DELTAS)
    assert all(len(item["sha256"]) == 64 for item in admissions.values())
    assert not any(item["dependency_satisfied"] for item in admissions.values())


def test_all_dimensions_pass_is_deterministic_fixture_only():
    first = MOD.evaluate(ROOT, MOD.fixture_packet("all_dimensions_pass"), is_synthetic=True)
    second = MOD.evaluate(ROOT, MOD.fixture_packet("all_dimensions_pass"), is_synthetic=True)
    assert first == second
    assert first["decision"]["route"] == "accept_fixture"
    assert first["decision"]["row106_acceptance"] == "fixture_only"
    assert first["release_authority"] is False


@pytest.mark.parametrize(
    ("name", "dimension"),
    [
        ("event_coverage_fail", "event_coverage"),
        ("false_event_fail", "false_event"),
        ("contact_offset_fail", "contact_offset"),
        ("endpoint_drift_fail", "endpoint_drift"),
        ("semantic_match_fail", "semantic_match"),
        ("room_consistency_fail", "room_consistency"),
        ("global_review_fail", "global_review"),
    ],
)
def test_each_required_dimension_fails_closed(name: str, dimension: str):
    record = MOD.evaluate(ROOT, MOD.fixture_packet(name), is_synthetic=True)
    assert record["decision"]["route"] == "reject"
    assert record["dimensions"][dimension]["status"] == "fail"


def test_technical_failure_rejected():
    record = MOD.evaluate(ROOT, MOD.fixture_packet("technical_fail"), is_synthetic=True)
    assert {"DECODE_FAILED", "CLIPPING_OR_TRUE_PEAK_FAILED"} <= set(record["decision"]["blocker_codes"])


def test_single_metric_cannot_grant_authority():
    record = MOD.evaluate(ROOT, MOD.fixture_packet("single_metric_cannot_grant_authority"), is_synthetic=True)
    assert record["dimensions"]["semantic_match"]["value"] == 0.999
    assert record["decision"]["route"] == "reject"
    assert "EVENT_COVERAGE_FAILED" in record["decision"]["blocker_codes"]


def test_component_binding_mismatch_rejected():
    record = MOD.evaluate(ROOT, MOD.fixture_packet("binding_mismatch_rejected"), is_synthetic=True)
    assert "COMPONENT_MEDIA_BINDING_MISMATCH" in record["decision"]["blocker_codes"]


def test_live_packet_holds_without_false_authority():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["release_authority"] is False
    assert evidence["decision"]["row106_acceptance"] == "held"
    assert "ROW106_DEPENDENCIES_NOT_ACCEPTED" in evidence["decision"]["blocker_codes"]


def test_receipt_tampering_rejected():
    record = MOD.evaluate(ROOT, MOD.fixture_packet("all_dimensions_pass"), is_synthetic=True)
    mutated = deepcopy(record)
    mutated["dimensions"]["semantic_match"]["value"] = 0.1
    with pytest.raises(MOD.AudioAVMatrixError, match="receipt_sha256_mismatch"):
        MOD.validate_record(ROOT, mutated)


def test_semantics_reject_accept_with_failed_dimension():
    record = MOD.evaluate(ROOT, MOD.fixture_packet("event_coverage_fail"), is_synthetic=True)
    mutated = deepcopy(record)
    mutated["decision"]["route"] = "accept_fixture"
    with pytest.raises(MOD.AudioAVMatrixError, match="failed_dimensions_cannot_accept"):
        MOD.validate_semantics(mutated)
