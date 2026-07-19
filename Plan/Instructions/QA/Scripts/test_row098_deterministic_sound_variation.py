from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_deterministic_sound_variation.py"
SPEC = importlib.util.spec_from_file_location(
    "compile_wave64_deterministic_sound_variation", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependencies_fail_closed_except_accepted_row068():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-071",
        "TRK-W64-072",
        "TRK-W64-073",
        "TRK-W64-079",
        "TRK-W64-093",
    }
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-068"]["row_complete"] is True
    for tracker_id in (
        "TRK-W64-071",
        "TRK-W64-072",
        "TRK-W64-073",
        "TRK-W64-079",
        "TRK-W64-093",
    ):
        admission = admissions[tracker_id]
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
    assert payload["decision"]["row098_acceptance"] == "held"
    assert (
        "ROW068_ROW071_ROW072_ROW073_ROW079_ROW093_DEPENDENCIES_NOT_ACCEPTED"
        in payload["blocker_codes"]
    )
    assert "DETERMINISTIC_VARIATION_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "CANONICAL_PCM_DEDUP_INDEX_ABSENT" in payload["blocker_codes"]
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["registry_revision"] == MOD.REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 8
    assert payload["adversarial_schema_probe"]["false_open_count"] == 0
    assert payload["planning_schema_boundary"]["planning_schema_remains_non_authority"] is True
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_micro_variation_fixture_is_deterministic_and_schema_valid():
    first = MOD.extract_fixture_manifest(ROOT, "micro_variation_pass")
    second = MOD.extract_fixture_manifest(ROOT, "micro_variation_pass")
    assert first == second
    assert first["validation"]["decision"] == "pass"
    assert first["variation_tier"] == "micro_variation"
    assert first["production_authority"] is False
    assert first["is_synthetic"] is True
    assert first["source"]["original_mutated"] is False
    assert first["variant"]["canonical_pcm_duplicate"] is False
    assert all(item["deterministic"] is True for item in first["transforms"])


def test_structural_variation_fixture_preserves_identity_and_provenance():
    record = MOD.extract_fixture_manifest(ROOT, "structural_variation_pass")
    assert record["variation_tier"] == "structural_variation"
    assert record["validation"]["event_identity_pass"] is True
    assert record["validation"]["license_provenance_pass"] is True
    assert record["source"]["license_class"] == "cc_by"
    assert record["decision"]["row098_acceptance"] == "fixture_only"


def test_reject_duplicate_mutation_and_license_remain_blocked():
    duplicate = MOD.extract_fixture_manifest(ROOT, "reject_canonical_pcm_duplicate")
    mutated = MOD.extract_fixture_manifest(ROOT, "reject_original_mutation")
    license_missing = MOD.extract_fixture_manifest(
        ROOT, "reject_license_provenance_missing"
    )
    assert duplicate["variant"]["canonical_pcm_duplicate"] is True
    assert duplicate["validation"]["decision"] == "blocked"
    assert "CANONICAL_PCM_DUPLICATE" in duplicate["decision"]["blocker_codes"]
    assert mutated["source"]["original_mutated"] is True
    assert mutated["validation"]["original_immutability_pass"] is False
    assert "ORIGINAL_SOURCE_MUTATED" in mutated["decision"]["blocker_codes"]
    assert license_missing["source"]["rights_decision_sha256"] is None
    assert license_missing["validation"]["license_provenance_pass"] is False
    assert "LICENSE_PROVENANCE_MISSING" in license_missing["decision"]["blocker_codes"]


def test_semantic_bounds_and_transform_bounds_block():
    semantic = MOD.extract_fixture_manifest(ROOT, "reject_semantic_similarity_fail")
    bounds = MOD.extract_fixture_manifest(ROOT, "reject_transform_bounds_exceeded")
    assert semantic["validation"]["semantic_similarity_pass"] is False
    assert "SEMANTIC_SIMILARITY_OUT_OF_BOUNDS" in semantic["decision"]["blocker_codes"]
    assert bounds["validation"]["transform_bounds_pass"] is False
    assert "TRANSFORM_BOUNDS_EXCEEDED" in bounds["decision"]["blocker_codes"]


def test_gate_failure_fixture_blocks_all_variation_gates():
    record = MOD.extract_fixture_manifest(ROOT, "gate_failure_blocked")
    assert record["validation"]["decision"] == "blocked"
    assert record["validation"]["event_identity_pass"] is False
    assert record["validation"]["canonical_pcm_dedup_pass"] is False
    assert record["validation"]["anchor_preservation_pass"] is False
    assert "ANCHOR_PRESERVATION_FAILED" in record["decision"]["blocker_codes"]


def test_seven_false_open_cases_are_rejected():
    cases = MOD.adversarial_false_open_cases(ROOT)
    assert len(cases) == 7
    assert all(case["false_open"] is False for case in cases)
    assert all(case["schema_accepted"] is False for case in cases)


def test_schema_rejects_production_authority_true_on_synthetic():
    record = MOD.extract_fixture_manifest(ROOT, "micro_variation_pass")
    mutated = deepcopy(record)
    mutated["production_authority"] = True
    mutated["is_synthetic"] = False
    mutated["decision"].update(
        {
            "status": "accepted",
            "row098_acceptance": "accepted",
            "product_completion": True,
            "runtime_completion": True,
            "promotion_eligible": False,
        }
    )
    with pytest.raises(
        MOD.DeterministicSoundVariationError,
        match="production_authority_forbidden|schema_validation_failed:production_authority",
    ):
        MOD.validate_manifest(ROOT, mutated)


def test_semantic_validator_rejects_duplicate_pass():
    record = MOD.extract_fixture_manifest(ROOT, "reject_canonical_pcm_duplicate")
    mutated = deepcopy(record)
    mutated["validation"]["decision"] = "pass"
    mutated["validation"]["canonical_pcm_dedup_pass"] = True
    with pytest.raises(
        MOD.DeterministicSoundVariationError,
        match="canonical_pcm_duplicate_cannot_pass|schema_validation_failed",
    ):
        MOD.validate_manifest(ROOT, mutated)
