from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_aqa_role_qualification_execution_matrix.py"
SPEC = importlib.util.spec_from_file_location("compile_wave64_aqa_role_qualification_execution_matrix", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_all_twelve_roles_receive_all_nine_categories_and_remain_nonoperational():
    matrix = MOD.compile_matrix(ROOT)
    assert len(matrix["role_plans"]) == 12
    assert sum(len(plan["cases"]) for plan in matrix["role_plans"]) == 108
    for plan in matrix["role_plans"]:
        assert {case["category"] for case in plan["cases"]} == MOD.REQUIRED_CATEGORIES
        assert plan["coverage_complete"] is True
        assert plan["operational"] is False
    assert matrix["authority"]["execution_planning"] is True
    assert not any(value for key, value in matrix["authority"].items() if key != "execution_planning")
    MOD.validate_matrix(ROOT, matrix)


def test_in_scope_keeps_declared_outcome_and_out_of_scope_must_refuse():
    matrix = MOD.compile_matrix(ROOT)
    deterministic = next(plan for plan in matrix["role_plans"] if plan["role_id"] == "W64-AQA-ROLE-DETERMINISTIC")
    good = next(case for case in deterministic["cases"] if case["category"] == "known_good")
    bad = next(case for case in deterministic["cases"] if case["category"] == "known_bad")
    assert good["in_scope"] is True and good["expected_disposition"] == "PASS"
    assert bad["in_scope"] is False and bad["expected_disposition"] == "REFUSE"
    assert bad["task_scope"].startswith("refuse out-of-scope request:")


def test_audio_and_workflow_roles_retain_their_scoped_cases():
    matrix = MOD.compile_matrix(ROOT)
    audio = next(plan for plan in matrix["role_plans"] if plan["role_id"] == "W64-AQA-ROLE-AUDIO-SEMANTIC")
    workflow = next(plan for plan in matrix["role_plans"] if plan["role_id"] == "W64-AQA-ROLE-WORKFLOW-ENGINEER")
    assert next(case for case in audio["cases"] if case["category"] == "refusal")["in_scope"] is True
    assert next(case for case in workflow["cases"] if case["category"] == "workflow")["expected_disposition"] == "PASS"


def test_missing_role_or_unfrozen_corpus_fails_closed():
    roles = MOD.load_json(ROOT / MOD.ROLE_REGISTRY_PATH)
    roles["roles"] = roles["roles"][:-1]
    with pytest.raises(MOD.MatrixError, match="twelve"):
        MOD.compile_matrix(ROOT, roles=roles)
    corpus = MOD.load_json(ROOT / MOD.CORPUS_PATH)
    corpus["status"] = "NOT_FROZEN"
    with pytest.raises(MOD.MatrixError, match="not frozen"):
        MOD.compile_matrix(ROOT, corpus=corpus)


def test_matrix_tampering_is_not_replayable():
    matrix = MOD.compile_matrix(ROOT)
    tampered = copy.deepcopy(matrix)
    current = tampered["role_plans"][0]["cases"][0]["expected_disposition"]
    tampered["role_plans"][0]["cases"][0]["expected_disposition"] = "PASS" if current != "PASS" else "REFUSE"
    with pytest.raises(MOD.MatrixError, match="does not replay"):
        MOD.validate_matrix(ROOT, tampered)
