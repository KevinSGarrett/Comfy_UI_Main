from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_component_compatibility.py"
SPEC = importlib.util.spec_from_file_location("validate_wave64_audio_component_compatibility", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def registry():
    return MOD.load_json(ROOT / MOD.REGISTRY_PATH)


def test_all_component_hashes_and_unique_capabilities_validate():
    result = MOD.validate_registry(ROOT, registry())
    assert result["component_count"] == 15
    assert result["unique_capability_count"] == 15
    assert result["source_hashes_match"] is True
    assert result["maximum_authority_rank"] == MOD.AUTHORITY_RANK["technical_qa"]


def test_dispositions_preserve_direct_adapt_and_hold_boundaries():
    result = MOD.validate_registry(ROOT, registry())
    assert result["disposition_counts"] == {"reuse_direct": 1, "adapt_once": 11, "evidence_only_hold": 3}


def test_duplicate_capability_owner_rejected():
    payload = registry()
    payload["components"][1]["capability"] = payload["components"][0]["capability"]
    with pytest.raises(MOD.CompatibilityError, match="duplicate_capability_owner"):
        MOD.validate_registry(ROOT, payload)


def test_duplicate_source_path_rejected():
    payload = registry()
    payload["components"][1]["source_path"] = payload["components"][0]["source_path"]
    with pytest.raises(MOD.CompatibilityError, match="duplicate_source_path|source_identity_mismatch"):
        MOD.validate_registry(ROOT, payload)


def test_stale_source_hash_or_size_rejected():
    for field, value in (("source_sha256", "a" * 64), ("source_bytes", 1)):
        payload = registry()
        payload["components"][0][field] = value
        with pytest.raises(MOD.CompatibilityError, match="source_identity_mismatch"):
            MOD.validate_registry(ROOT, payload)


def test_adapter_requires_contract():
    payload = registry()
    payload["components"][1]["adapter_contract"] = None
    with pytest.raises(MOD.CompatibilityError, match="adapter_contract_required"):
        MOD.validate_registry(ROOT, payload)


def test_non_adapter_cannot_claim_adapter_contract():
    payload = registry()
    payload["components"][0]["adapter_contract"] = "invented"
    with pytest.raises(MOD.CompatibilityError, match="adapter_contract_forbidden_for_disposition"):
        MOD.validate_registry(ROOT, payload)


def test_legacy_production_authority_forbidden():
    payload = registry()
    payload["components"][0]["authority_ceiling"] = "production"
    with pytest.raises(MOD.CompatibilityError, match="legacy_production_authority_forbidden"):
        MOD.validate_registry(ROOT, payload)


def test_limitations_cannot_be_erased():
    payload = registry()
    payload["components"][0]["limitations"] = []
    with pytest.raises(MOD.CompatibilityError, match="component_schema_invalid|limitations_required"):
        MOD.validate_registry(ROOT, payload)


def test_completed_proof_guard_cannot_be_disabled():
    payload = registry()
    payload["components"][0]["completed_proof_guard"] = False
    with pytest.raises(MOD.CompatibilityError, match="component_schema_invalid"):
        MOD.validate_registry(ROOT, payload)


def test_dependencies_are_hash_bound_and_not_all_accepted():
    admissions = MOD.dependency_admissions(ROOT)
    assert set(admissions) == set(MOD.DEPENDENCY_DELTAS)
    assert all(len(item["sha256"]) == 64 for item in admissions.values())
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_evidence_truthfully_holds_runtime_adapters():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["validation"]["source_hashes_match"] is True
    assert "VERSIONED_RUNTIME_ADAPTERS_NOT_MATERIALIZED" in evidence["decision"]["blocker_codes"]
