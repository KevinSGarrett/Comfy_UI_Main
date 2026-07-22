from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_comfyui_modules.py"
SPEC = importlib.util.spec_from_file_location("validate_wave64_audio_comfyui_modules", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def registry():
    return MOD.load_json(ROOT / MOD.REGISTRY_PATH)


def test_exact_six_module_contract_passes():
    result = MOD.validate_registry(ROOT, registry())
    assert result["module_count"] == 6
    assert set(result["module_types"]) == MOD.REQUIRED_TYPES
    assert result["authority_boundary_valid"] is True
    assert result["runtime_active_count"] == 0


def test_dependency_admissions_are_hash_bound_and_held():
    admissions = MOD.dependency_admissions(ROOT)
    assert set(admissions) == set(MOD.DEPENDENCY_DELTAS)
    assert all(len(item["sha256"]) == 64 for item in admissions.values())
    assert not any(item["dependency_satisfied"] for item in admissions.values())


def test_evidence_truthfully_holds_runtime():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["implementation_completion_claimed"] is True
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["release_authority"] is False
    assert evidence["decision"]["row107_acceptance"] == "held"
    assert "ROW107_DEPENDENCIES_NOT_ACCEPTED" in evidence["decision"]["blocker_codes"]


def test_missing_module_rejected():
    payload = registry()
    payload["modules"].pop()
    with pytest.raises(MOD.AudioModuleValidationError, match="required_module_set_mismatch"):
        MOD.validate_registry(ROOT, payload)


def test_duplicate_module_type_rejected():
    payload = registry()
    payload["modules"][5]["module_type"] = "analysis_request"
    with pytest.raises(MOD.AudioModuleValidationError, match="required_module_set_mismatch"):
        MOD.validate_registry(ROOT, payload)


def test_duplicate_namespace_rejected():
    payload = registry()
    payload["modules"][1]["workflow_namespace"] = payload["modules"][0]["workflow_namespace"]
    with pytest.raises(MOD.AudioModuleValidationError, match="duplicate_workflow_namespace"):
        MOD.validate_registry(ROOT, payload)


def test_authority_omission_rejected():
    payload = registry()
    payload["modules"][0]["forbidden_authorities"].remove("release_or_promotion")
    with pytest.raises(MOD.AudioModuleValidationError, match="module_schema_invalid|forbidden_authority_set_incomplete"):
        MOD.validate_registry(ROOT, payload)


def test_credentials_rejected_by_schema():
    payload = registry()
    payload["modules"][0]["credentials_embedded"] = True
    with pytest.raises(MOD.AudioModuleValidationError, match="module_schema_invalid"):
        MOD.validate_registry(ROOT, payload)


def test_unqualified_active_module_rejected():
    payload = registry()
    payload["modules"][0]["runtime_active"] = True
    with pytest.raises(MOD.AudioModuleValidationError, match="unqualified_module_cannot_be_active"):
        MOD.validate_registry(ROOT, payload)


def test_runtime_qualified_module_requires_workflow_path():
    payload = deepcopy(registry())
    payload["modules"][0]["status"] = "runtime_qualified"
    with pytest.raises(MOD.AudioModuleValidationError, match="qualified_module_requires_workflow_path"):
        MOD.validate_registry(ROOT, payload)


def test_oversized_module_rejected_by_schema():
    payload = registry()
    payload["modules"][0]["maximum_node_count"] = 41
    with pytest.raises(MOD.AudioModuleValidationError, match="module_schema_invalid"):
        MOD.validate_registry(ROOT, payload)
