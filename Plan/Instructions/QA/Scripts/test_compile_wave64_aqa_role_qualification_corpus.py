from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_aqa_role_qualification_corpus.py"
SPEC = importlib.util.spec_from_file_location("compile_wave64_aqa_role_qualification_corpus", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def source():
    return MOD.load_json(ROOT / MOD.SOURCE_PATH)


def test_current_corpus_replays_with_exact_coverage_and_no_runtime_authority():
    manifest = MOD.compile_manifest(ROOT)
    assert len(manifest["cases"]) == 9
    assert set(manifest["coverage"]["categories"]) == MOD.REQUIRED_CATEGORIES
    assert len(manifest["coverage"]["modalities"]) >= 4
    assert manifest["coverage"]["calibration_count"] >= 4
    assert manifest["coverage"]["held_out_count"] >= 4
    assert manifest["authority"]["source_admission"] is True
    assert not any(value for key, value in manifest["authority"].items() if key != "source_admission")
    MOD.validate_manifest(ROOT, manifest)


def test_scope_specific_shared_media_retains_distinct_truth():
    manifest = MOD.compile_manifest(ROOT)
    image_cases = [case for case in manifest["cases"] if case["source"]["path"].endswith("contact_lower_upper_arm_reposition_seed210705_00001_.png")]
    assert {case["expected_disposition"] for case in image_cases} == {"PASS", "FAIL"}
    assert len({case["task_scope"] for case in image_cases}) == 2


def test_missing_category_duplicate_id_and_unknown_role_fail_closed():
    missing = source()
    missing["cases"] = missing["cases"][:-1]
    with pytest.raises(MOD.CorpusError, match="exactly nine"):
        MOD.compile_manifest(ROOT, missing)
    duplicate = source()
    duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
    with pytest.raises(MOD.CorpusError, match="unique"):
        MOD.compile_manifest(ROOT, duplicate)
    role = source()
    role["cases"][0]["eligible_roles"] = ["W64-AQA-ROLE-NOT-REAL"]
    with pytest.raises(MOD.CorpusError, match="unknown or empty"):
        MOD.compile_manifest(ROOT, role)


def test_partition_drift_and_path_escape_fail_closed():
    partition = source()
    for case in partition["cases"]:
        case["partition"] = "held_out"
    with pytest.raises(MOD.CorpusError, match="partitions"):
        MOD.compile_manifest(ROOT, partition)
    escaped = source()
    escaped["cases"][0]["source_path"] = "../outside.json"
    with pytest.raises(MOD.CorpusError, match="escapes"):
        MOD.compile_manifest(ROOT, escaped)


def test_manifest_tampering_is_not_replayable():
    manifest = MOD.compile_manifest(ROOT)
    tampered = copy.deepcopy(manifest)
    tampered["cases"][0]["expected_disposition"] = "REFUSE"
    with pytest.raises(MOD.CorpusError, match="does not replay"):
        MOD.validate_manifest(ROOT, tampered)
