from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compose_wave64_layered_foley_composition.py"
SPEC = importlib.util.spec_from_file_location("compose_wave64_layered_foley_composition", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-079",
        "TRK-W64-081",
        "TRK-W64-091",
        "TRK-W64-093",
    }
    # Row068 rights authority is accepted on this branch; remaining deps stay held.
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-068"]["row_complete"] is True
    for tracker_id in ("TRK-W64-079", "TRK-W64-081", "TRK-W64-091", "TRK-W64-093"):
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False
        assert admission["row_complete"] is False
        assert admission["blocker_codes"]
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row094_acceptance"] == "held"
    assert "ROW094_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_LIBRARY_LAYER_COMPOSER_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_compatible_layers_compose_is_deterministic_and_reconstructable():
    first = MOD.extract_fixture_record(ROOT, "compatible_layers_compose")
    second = MOD.extract_fixture_record(ROOT, "compatible_layers_compose")
    assert first == second
    assert first["decision"]["route"] == "compose"
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["composite"]["reconstructable"] is True
    assert first["composite"]["composite_hash"]
    assert first["gate_results"]["composite_hash"]["status"] == "pass"
    assert [item["layer_role"] for item in first["layers"]] == [
        "transient",
        "body",
        "settle",
    ]


def test_license_incompatible_layers_are_rejected():
    record = MOD.extract_fixture_record(ROOT, "license_incompatible_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "LICENSE_INCOMPATIBLE" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["license_compatibility"]["status"] == "fail"
    assert record["composite"]["composite_hash"] is None


def test_acoustic_perspective_mismatch_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "acoustic_perspective_mismatch_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "ACOUSTIC_INCOMPATIBLE" in record["decision"]["blocker_codes"]
    assert "PERSPECTIVE_MISMATCH" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["acoustic_compatibility"]["status"] == "fail"


def test_duplicate_layer_role_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "duplicate_layer_role_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "DUPLICATE_LAYER_ROLE" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["layer_justification"]["status"] == "fail"


def test_missing_expected_layer_is_blocked():
    record = MOD.extract_fixture_record(ROOT, "missing_expected_layer_blocked")
    assert record["decision"]["route"] == "blocked"
    assert "MISSING_LAYER_JUSTIFICATION" in record["decision"]["blocker_codes"]
    assert any(
        item["layer_role"] == "room"
        and "MISSING_LAYER_JUSTIFICATION" in item["reason_codes"]
        for item in record["exclusions"]
    )


def test_semantic_validator_rejects_tampered_composite_hash():
    record = MOD.extract_fixture_record(ROOT, "compatible_layers_compose")
    mutated = deepcopy(record)
    mutated["composite"]["composite_hash"] = "a" * 64
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.LayeredFoleyError, match="composite_hash_recompute_mismatch"):
        MOD.validate_composition_semantics(mutated)


def test_semantic_validator_rejects_compose_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "compatible_layers_compose")
    mutated = deepcopy(record)
    mutated["gate_results"]["license_compatibility"] = {
        "status": "fail",
        "reason_codes": ["LICENSE_INCOMPATIBLE"],
    }
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.LayeredFoleyError, match="compose_with_failed_gate"):
        MOD.validate_composition_semantics(mutated)


def test_schema_rejects_library_authority_true():
    record = MOD.extract_fixture_record(ROOT, "compatible_layers_compose")
    mutated = deepcopy(record)
    mutated["library_authority"] = True
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(Exception):
        MOD.validate_composition_receipt(ROOT, mutated)
