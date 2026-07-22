from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_speech_full_system_certification.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_speech_full_system_certification", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def genuine_gates():
    gates = {name: MOD.synthetic_gate(name) for name in MOD.REQUIRED_GATES}
    for gate in gates.values():
        gate["is_synthetic"] = False
    return gates


def test_current_matrix_is_exact_and_fail_closed():
    dependencies = MOD.inspect_dependencies(ROOT)
    assert len(dependencies) == 35
    assert [item["tracker_id"] for item in dependencies] == list(MOD.REQUIRED_TRACKERS)
    assert not all(item["accepted"] for item in dependencies)


def test_complete_genuine_packet_can_pass_mechanically():
    report = MOD.evaluate(root=ROOT, dependencies=MOD.synthetic_dependencies(), gates=genuine_gates(), coverage=MOD.fixture_coverage(), is_synthetic=False)
    assert report["decision"]["certification_authority"] is True


def test_synthetic_packet_never_certifies():
    report = MOD.evaluate(root=ROOT, dependencies=MOD.synthetic_dependencies(), gates={name: MOD.synthetic_gate(name) for name in MOD.REQUIRED_GATES}, coverage=MOD.fixture_coverage(), is_synthetic=True)
    assert report["decision"]["certification_authority"] is False
    assert "SYNTHETIC_CERTIFICATION_FORBIDDEN" in report["decision"]["blocker_codes"]


@pytest.mark.parametrize("gate_name", MOD.REQUIRED_GATES)
def test_each_missing_gate_blocks(gate_name):
    gates = genuine_gates()
    gates[gate_name] = MOD.empty_gate()
    report = MOD.evaluate(root=ROOT, dependencies=MOD.synthetic_dependencies(), gates=gates, coverage=MOD.fixture_coverage(), is_synthetic=False)
    assert f"PRODUCTION_GATE_{gate_name.upper()}_NOT_ACCEPTED" in report["decision"]["blocker_codes"]


@pytest.mark.parametrize("coverage_name", MOD.MINIMUM_COVERAGE)
def test_each_coverage_floor_blocks(coverage_name):
    coverage = MOD.fixture_coverage()
    coverage[coverage_name] = coverage[coverage_name][:-1]
    report = MOD.evaluate(root=ROOT, dependencies=MOD.synthetic_dependencies(), gates=genuine_gates(), coverage=coverage, is_synthetic=False)
    assert f"{coverage_name.upper()}_COVERAGE_INSUFFICIENT" in report["decision"]["blocker_codes"]


def test_held_dependency_blocks():
    dependencies = MOD.synthetic_dependencies()
    dependencies[0] = {**dependencies[0], "accepted": False, "row_complete": False, "status": "HOLD"}
    report = MOD.evaluate(root=ROOT, dependencies=dependencies, gates=genuine_gates(), coverage=MOD.fixture_coverage(), is_synthetic=False)
    assert "TRK_W64_113_NOT_ACCEPTED" in report["decision"]["blocker_codes"]


def test_dependency_order_is_exact():
    dependencies = MOD.synthetic_dependencies()
    dependencies.reverse()
    with pytest.raises(MOD.CertificationError, match="dependency_set_or_order_mismatch"):
        MOD.evaluate(root=ROOT, dependencies=dependencies, gates=genuine_gates(), coverage=MOD.fixture_coverage(), is_synthetic=False)


def test_report_tampering_is_rejected():
    report = MOD.evaluate(root=ROOT, dependencies=MOD.synthetic_dependencies(), gates=genuine_gates(), coverage=MOD.fixture_coverage(), is_synthetic=False)
    report["coverage"]["engine_ids"][0] = "tampered"
    with pytest.raises(MOD.CertificationError, match="report_sha256_mismatch"):
        MOD.validate_report(ROOT, report)


def test_live_evidence_truthfully_holds():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["live_hold_report"]["decision"]["certification_authority"] is False
