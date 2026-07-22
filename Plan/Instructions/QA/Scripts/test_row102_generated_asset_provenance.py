from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_generated_asset_provenance.py"
SPEC = importlib.util.spec_from_file_location(
    "evaluate_wave64_generated_asset_provenance", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_with_row068_accepted():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-098",
        "TRK-W64-099",
        "TRK-W64-100",
        "TRK-W64-101",
    }
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-068"]["blocker_codes"] == []
    for tracker_id in ("TRK-W64-098", "TRK-W64-099", "TRK-W64-100", "TRK-W64-101"):
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False
        assert admission["blocker_codes"]
        assert any(
            code.endswith("_DELTA_ABSENT") or code.endswith("_DEPENDENCY_NOT_ACCEPTED")
            for code in admission["blocker_codes"]
        )
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is True
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row102_acceptance"] == "held"
    assert "ROW102_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_GENERATED_ASSET_STAGING_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 10
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_clean_staged_candidate_is_deterministic_fixture_only():
    first = MOD.extract_fixture_record(ROOT, "clean_staged_candidate_accept")
    second = MOD.extract_fixture_record(ROOT, "clean_staged_candidate_accept")
    assert first == second
    assert first["decision"]["route"] == "stage_candidate"
    assert first["decision"]["status"] == "pass"
    assert first["library_authority"] is False
    assert first["selector_visible"] is False
    assert first["decision"]["product_completion"] is False
    assert first["decision"]["row102_acceptance"] == "fixture_only"
    assert first["provenance_binding"]["immutable"] is True
    assert all(result["status"] == "pass" for result in first["gate_results"].values())


def test_missing_input_hashes_rejected():
    record = MOD.extract_fixture_record(ROOT, "missing_input_hashes_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "INPUT_HASHES_MISSING" in record["decision"]["blocker_codes"]


def test_missing_prompt_hash_rejected():
    record = MOD.extract_fixture_record(ROOT, "missing_prompt_hash_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "PROMPT_HASH_MISSING" in record["decision"]["blocker_codes"]


def test_missing_engine_hashes_rejected():
    record = MOD.extract_fixture_record(ROOT, "missing_engine_hashes_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "ENGINE_MODEL_HASH_MISSING" in record["decision"]["blocker_codes"]
    assert "ENGINE_CONFIGURATION_HASH_MISSING" in record["decision"]["blocker_codes"]
    assert "ENGINE_ENVIRONMENT_HASH_MISSING" in record["decision"]["blocker_codes"]


def test_missing_seed_rejected():
    record = MOD.extract_fixture_record(ROOT, "missing_seed_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "SEED_MISSING" in record["decision"]["blocker_codes"]


def test_missing_output_hash_rejected():
    record = MOD.extract_fixture_record(ROOT, "missing_output_hash_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "OUTPUT_HASH_MISSING" in record["decision"]["blocker_codes"]
    assert "CANONICAL_PCM_HASH_MISSING" in record["decision"]["blocker_codes"]


def test_rights_blocked_rejected():
    record = MOD.extract_fixture_record(ROOT, "rights_blocked_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "RIGHTS_DECISION_NOT_PASS" in record["decision"]["blocker_codes"]


def test_selector_visible_boundary_rejected():
    record = MOD.extract_fixture_record(ROOT, "selector_visible_boundary_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "SELECTOR_VISIBLE_BEFORE_PROMOTION" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["staging_boundary"]["status"] == "fail"


def test_approved_library_path_boundary_rejected():
    record = MOD.extract_fixture_record(ROOT, "approved_library_path_boundary_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "APPROVED_LIBRARY_PATH_BEFORE_PROMOTION" in record["decision"]["blocker_codes"]


def test_content_suppression_rejected():
    record = MOD.extract_fixture_record(ROOT, "content_suppression_rejected")
    assert record["decision"]["route"] == "reject_candidate"
    assert "CONTENT_BASED_SUPPRESSION_FORBIDDEN" in record["decision"]["blocker_codes"]


def test_semantic_validator_rejects_stage_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "missing_seed_rejected")
    mutated = deepcopy(record)
    mutated["decision"]["route"] = "stage_candidate"
    mutated["decision"]["status"] = "pass"
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.GeneratedAssetProvenanceError, match="failed_gates_cannot_stage"):
        MOD.validate_decision_semantics(mutated)


def test_schema_rejects_missing_provenance_binding():
    record = MOD.extract_fixture_record(ROOT, "clean_staged_candidate_accept")
    mutated = deepcopy(record)
    del mutated["provenance_binding"]
    with pytest.raises(Exception):
        MOD.validate_decision_record(ROOT, mutated)
