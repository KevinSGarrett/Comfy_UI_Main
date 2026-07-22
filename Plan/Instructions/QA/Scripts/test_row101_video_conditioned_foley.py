from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_video_conditioned_foley.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_video_conditioned_foley", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def accepted_dependencies():
    return {tracker: True for tracker in MOD.DEPENDENCIES}


def evaluate_fixture(**overrides):
    packet = MOD.fixture_packet()
    packet.update(overrides)
    return MOD.evaluate(ROOT, dependencies=accepted_dependencies(), **packet)


def test_dependency_state_is_exact_and_currently_held():
    state = MOD.dependency_state(ROOT)
    assert tuple(state) == MOD.DEPENDENCIES
    assert not any(state.values())


def test_synthetic_fixture_never_has_production_authority():
    report = evaluate_fixture()
    assert report["decision"]["candidate_authority"] is True
    assert report["decision"]["production_authority"] is False
    assert "SYNTHETIC_PRODUCTION_AUTHORITY_FORBIDDEN" in report["decision"]["blocker_codes"]


def test_genuine_fully_bound_packet_can_mechanically_pass():
    report = evaluate_fixture(is_synthetic=False)
    assert report["decision"]["production_authority"] is True


@pytest.mark.parametrize("tracker", MOD.DEPENDENCIES)
def test_each_dependency_holds_production(tracker):
    dependencies = accepted_dependencies()
    dependencies[tracker] = False
    packet = MOD.fixture_packet(synthetic=False)
    report = MOD.evaluate(ROOT, dependencies=dependencies, **packet)
    assert f"{tracker.replace('-', '_')}_HELD" in report["decision"]["blocker_codes"]


def test_unqualified_engine_blocks():
    packet = MOD.fixture_packet(synthetic=False)
    packet["engine"]["qualified"] = False
    report = MOD.evaluate(ROOT, dependencies=accepted_dependencies(), **packet)
    assert "ENGINE_NOT_INDEPENDENTLY_QUALIFIED" in report["decision"]["blocker_codes"]


def test_unregistered_engine_blocks():
    packet = MOD.fixture_packet(synthetic=False)
    packet["engine"]["family"] = "unknown"
    with pytest.raises(Exception):
        MOD.evaluate(ROOT, dependencies=accepted_dependencies(), **packet)


def test_missing_runtime_blocks():
    report = evaluate_fixture(is_synthetic=False, runtime_evidence_sha256=None)
    assert "GENUINE_RUNTIME_EVIDENCE_ABSENT" in report["decision"]["blocker_codes"]


def test_anchor_cannot_be_silently_overwritten():
    decisions = [{"anchor_id": "contact-001", "action": "overwrite", "explicit": False}]
    with pytest.raises(Exception):
        evaluate_fixture(is_synthetic=False, anchor_decisions=decisions)


@pytest.mark.parametrize("onset,coverage", [(50.1, 0.95), (12.0, 0.79)])
def test_anchor_alignment_thresholds_fail_closed(onset, coverage):
    alignments = [{"anchor_id": "contact-001", "onset_error_ms": onset, "coverage": coverage}]
    report = evaluate_fixture(is_synthetic=False, alignments=alignments)
    assert "ANCHOR_contact-001_ALIGNMENT_FAILED" in report["decision"]["blocker_codes"]


def test_every_anchor_requires_explicit_decision_and_alignment():
    with pytest.raises(MOD.FoleyDecisionError, match="anchor_coverage_mismatch"):
        evaluate_fixture(anchor_decisions=[])


def test_duplicate_anchor_ids_rejected():
    packet = MOD.fixture_packet()
    packet["anchors"].append(dict(packet["anchors"][0]))
    with pytest.raises(MOD.FoleyDecisionError, match="duplicate_anchor_id"):
        MOD.evaluate(ROOT, dependencies=accepted_dependencies(), **packet)


def test_invalid_anchor_sample_range_rejected():
    packet = MOD.fixture_packet()
    packet["anchors"][0]["end_sample"] = packet["anchors"][0]["start_sample"]
    with pytest.raises(MOD.FoleyDecisionError, match="invalid_anchor_sample_range"):
        MOD.evaluate(ROOT, dependencies=accepted_dependencies(), **packet)


def test_report_tamper_rejected():
    report = evaluate_fixture()
    report["candidate_sha256"] = MOD.stable_hash("tampered")
    with pytest.raises(MOD.FoleyDecisionError, match="report_sha256_mismatch"):
        MOD.validate_report(ROOT, report)
