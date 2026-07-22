from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_audio_full_system_certification.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_audio_full_system_certification", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def genuine_gates():
    gates = MOD.synthetic_gates()
    for gate in gates.values():
        gate["is_synthetic"] = False
    return gates


def videos():
    return [MOD.stable_hash(f"video:{index}") for index in range(3)]


def test_current_dependency_matrix_is_exact_45_and_fail_closed():
    dependencies = MOD.inspect_all_dependencies(ROOT)
    assert len(dependencies) == 45
    assert [item["tracker_id"] for item in dependencies] == list(MOD.REQUIRED_TRACKERS)
    assert not all(item["accepted"] for item in dependencies)


def test_current_matrix_detects_held_row101_and_ambiguous_rows():
    by_id = {item["tracker_id"]: item for item in MOD.inspect_all_dependencies(ROOT)}
    assert by_id["TRK-W64-101"]["disposition"] == "held"
    for tracker in ("TRK-W64-086", "TRK-W64-087", "TRK-W64-088"):
        assert by_id[tracker]["disposition"] == "ambiguous"
        assert len(by_id[tracker]["candidate_paths"]) > 1


def test_single_current_delta_requires_boolean_complete_and_pass_status(tmp_path: Path):
    tracker = "TRK-W64-067"
    path = tmp_path / f"{tracker}_TEST_CURRENT_DELTA.json"
    path.write_text(json.dumps({"tracker_id": tracker, "row_complete": True, "status": "HOLD_NOT_ACCEPTED"}))
    result = MOD.inspect_dependency(tmp_path, tracker)
    assert result["disposition"] == "held"
    path.write_text(json.dumps({"tracker_id": tracker, "row_complete": True, "status": "PASS_ACCEPTED"}))
    assert MOD.inspect_dependency(tmp_path, tracker)["accepted"] is True


def test_invalid_tracker_binding_rejected_as_invalid(tmp_path: Path):
    tracker = "TRK-W64-067"
    (tmp_path / f"{tracker}_TEST_CURRENT_DELTA.json").write_text(json.dumps({"tracker_id": "TRK-W64-999", "row_complete": True, "status": "PASS"}))
    assert MOD.inspect_dependency(tmp_path, tracker)["disposition"] == "invalid"


def test_complete_genuine_packet_can_pass_mechanically():
    report = MOD.evaluate(ROOT, gates=genuine_gates(), video_hashes=videos(), is_synthetic=False, dependencies=MOD.synthetic_dependencies())
    assert report["decision"]["certification_authority"] is True
    assert report["decision"]["product_completion"] is True


def test_synthetic_packet_never_certifies():
    report = MOD.evaluate(ROOT, gates=MOD.synthetic_gates(), video_hashes=videos(), is_synthetic=True, dependencies=MOD.synthetic_dependencies())
    assert report["decision"]["certification_authority"] is False
    assert "SYNTHETIC_CERTIFICATION_FORBIDDEN" in report["decision"]["blocker_codes"]


@pytest.mark.parametrize("gate_name", MOD.REQUIRED_GATES)
def test_each_missing_production_gate_blocks(gate_name: str):
    gates = genuine_gates()
    gates[gate_name] = MOD.empty_gate()
    report = MOD.evaluate(ROOT, gates=gates, video_hashes=videos(), is_synthetic=False, dependencies=MOD.synthetic_dependencies())
    assert report["decision"]["certification_authority"] is False
    assert f"PRODUCTION_GATE_{gate_name.upper()}_NOT_ACCEPTED" in report["decision"]["blocker_codes"]


def test_single_held_dependency_blocks():
    dependencies = MOD.synthetic_dependencies()
    dependencies[10] = {**dependencies[10], "accepted": False, "disposition": "held", "row_complete": False, "status": "HOLD"}
    report = MOD.evaluate(ROOT, gates=genuine_gates(), video_hashes=videos(), is_synthetic=False, dependencies=dependencies)
    assert report["decision"]["certification_authority"] is False
    assert "TRK_W64_077_HELD" in report["decision"]["blocker_codes"]


def test_three_unique_genuine_videos_required():
    for values in ([MOD.stable_hash("one")], [MOD.stable_hash("same")] * 3):
        report = MOD.evaluate(ROOT, gates=genuine_gates(), video_hashes=values, is_synthetic=False, dependencies=MOD.synthetic_dependencies())
        assert "GENUINE_VIDEO_COVERAGE_INSUFFICIENT" in report["decision"]["blocker_codes"]


def test_gate_set_must_be_exact():
    gates = genuine_gates()
    gates.pop("rights")
    with pytest.raises(MOD.CertificationError, match="production_gate_set_mismatch"):
        MOD.evaluate(ROOT, gates=gates, video_hashes=videos(), is_synthetic=False, dependencies=MOD.synthetic_dependencies())


def test_dependency_order_must_be_exact():
    dependencies = MOD.synthetic_dependencies()
    dependencies.reverse()
    with pytest.raises(MOD.CertificationError, match="dependency_set_or_order_mismatch"):
        MOD.evaluate(ROOT, gates=genuine_gates(), video_hashes=videos(), is_synthetic=False, dependencies=dependencies)


def test_report_tampering_rejected():
    report = MOD.evaluate(ROOT, gates=genuine_gates(), video_hashes=videos(), is_synthetic=False, dependencies=MOD.synthetic_dependencies())
    report["genuine_video_sha256s"][0] = MOD.stable_hash("tampered")
    with pytest.raises(MOD.CertificationError, match="report_sha256_mismatch"):
        MOD.validate_report(ROOT, report)


def test_live_evidence_truthfully_holds():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["live_hold_report"]["decision"]["certification_authority"] is False
    assert evidence["decision"]["row112_acceptance"] == "held"
