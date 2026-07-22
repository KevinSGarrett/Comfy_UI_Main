from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_dependency_lock.py"
EVIDENCE_PATH = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_1_6_DEPENDENCY_LOCK_20260722T074216Z.json"
LOCK_PATH = ROOT / "Plan/10_REGISTRIES/Locks/wave64_latentsync_1_6_py311_cu121.pylock.toml"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_dependency_lock_evidence.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_dependency_lock", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")),
        tomllib.loads(LOCK_PATH.read_text(encoding="utf-8")),
    )


def test_real_evidence_and_lock_are_valid() -> None:
    evidence, lock = load_inputs()
    assert MODULE.validate(evidence, lock, LOCK_PATH) == []


def test_schema_accepts_real_evidence() -> None:
    evidence, _ = load_inputs()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(evidence)


def test_unexpected_artifact_host_fails_closed() -> None:
    evidence, lock = load_inputs()
    lock = copy.deepcopy(lock)
    lock["packages"][0]["wheels"][0]["url"] = "https://example.invalid/package.whl"
    assert "dependency artifact host allowlist mismatch" in MODULE.validate(
        evidence, lock, LOCK_PATH
    )


def test_source_only_hash_mismatch_fails_closed() -> None:
    evidence, lock = load_inputs()
    lock = copy.deepcopy(lock)
    package = next(item for item in lock["packages"] if item["name"] == "insightface")
    package["sdist"]["hashes"]["sha256"] = "0" * 64
    assert "source-only package set or hash mismatch" in MODULE.validate(
        evidence, lock, LOCK_PATH
    )


def test_runtime_install_authority_fails_closed() -> None:
    evidence, lock = load_inputs()
    evidence = copy.deepcopy(evidence)
    evidence["source_wheel_gate"]["runtime_install_admitted"] = True
    assert "source-wheel gate must block runtime install" in MODULE.validate(
        evidence, lock, LOCK_PATH
    )


def test_runtime_claim_fails_closed() -> None:
    evidence, lock = load_inputs()
    evidence = copy.deepcopy(evidence)
    evidence["execution_claims"]["model_loaded"] = True
    assert "lock evidence exceeds non-execution authority" in MODULE.validate(
        evidence, lock, LOCK_PATH
    )
