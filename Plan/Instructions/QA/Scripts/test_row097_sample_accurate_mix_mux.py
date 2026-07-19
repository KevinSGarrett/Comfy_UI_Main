from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_sample_accurate_mix_mux.py"
SPEC = importlib.util.spec_from_file_location("compile_wave64_sample_accurate_mix_mux", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-091",
        "TRK-W64-093",
        "TRK-W64-094",
        "TRK-W64-095",
        "TRK-W64-096",
    }
    for tracker_id, admission in admissions.items():
        assert admission["dependency_satisfied"] is False, tracker_id
        assert admission["row_complete"] is False, tracker_id
        assert admission["blocker_codes"], tracker_id
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row097_acceptance"] == "held"
    assert "ROW097_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_LIBRARY_MIX_MUX_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 6
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_compatible_stems_mix_mux_is_deterministic_and_reconstructable():
    first = MOD.extract_fixture_record(ROOT, "compatible_stems_mix_mux")
    second = MOD.extract_fixture_record(ROOT, "compatible_stems_mix_mux")
    assert first == second
    assert first["decision"]["route"] == "mix_mux"
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["mux"]["reconstructable"] is True
    assert first["mux"]["mux_lineage_sha256"]
    assert first["gate_results"]["mux_lineage"]["status"] == "pass"
    assert [item["stem_bus"] for item in first["stems"]] == [
        "dialogue",
        "foley",
        "ambience",
        "room",
    ]


def test_missing_expected_stem_is_blocked():
    record = MOD.extract_fixture_record(ROOT, "missing_expected_stem_blocked")
    assert record["decision"]["route"] == "blocked"
    assert "MISSING_EXPECTED_STEM" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["stem_manifest"]["status"] == "fail"
    assert record["mux"]["mux_lineage_sha256"] is None


def test_true_peak_exceedance_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "true_peak_exceedance_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "TRUE_PEAK_EXCEEDANCE" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["true_peak"]["status"] == "fail"


def test_endpoint_drift_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "endpoint_drift_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "ENDPOINT_DRIFT" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["sample_schedule"]["status"] == "fail"


def test_sample_schedule_mismatch_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "sample_schedule_mismatch_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "SAMPLE_SCHEDULE_MISMATCH" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["sample_schedule"]["status"] == "fail"


def test_duplicate_stem_bus_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "duplicate_stem_bus_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "DUPLICATE_STEM_BUS" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["stem_manifest"]["status"] == "fail"


def test_semantic_validator_rejects_tampered_mux_lineage():
    record = MOD.extract_fixture_record(ROOT, "compatible_stems_mix_mux")
    mutated = deepcopy(record)
    mutated["mux"]["mux_lineage_sha256"] = "a" * 64
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.SampleAccurateMixMuxError, match="mux_lineage_recompute_mismatch"):
        MOD.validate_mix_mux_semantics(mutated)


def test_semantic_validator_rejects_mix_mux_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "compatible_stems_mix_mux")
    mutated = deepcopy(record)
    mutated["gate_results"]["true_peak"] = {
        "status": "fail",
        "reason_codes": ["TRUE_PEAK_EXCEEDANCE"],
    }
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.SampleAccurateMixMuxError, match="mix_mux_with_failed_gate"):
        MOD.validate_mix_mux_semantics(mutated)


def test_schema_rejects_library_authority_true():
    record = MOD.extract_fixture_record(ROOT, "compatible_stems_mix_mux")
    mutated = deepcopy(record)
    mutated["library_authority"] = True
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(Exception):
        MOD.validate_mix_mux_receipt(ROOT, mutated)
