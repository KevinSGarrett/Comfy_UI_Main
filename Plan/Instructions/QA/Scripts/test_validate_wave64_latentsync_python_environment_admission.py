from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_python_environment_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_dependency_environment_admission.json"
LOCK = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_wheels.toml"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_python_environment_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_environment_admission", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(ADMISSION.read_text(encoding="utf-8")),
        tomllib.loads(LOCK.read_text(encoding="utf-8")),
    )


def test_real_admission_and_lock_are_valid() -> None:
    admission, lock = load_inputs()
    assert MODULE.validate(admission, lock, LOCK) == []


def test_schema_accepts_real_admission() -> None:
    admission, _ = load_inputs()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(admission)


def test_unexpected_remote_host_fails_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    package = next(item for item in lock["packages"] if item["name"] == "transformers")
    package["wheels"][0]["url"] = "https://example.invalid/package.whl"
    assert "runtime wheel host allowlist mismatch" in MODULE.validate(admission, lock, LOCK)


def test_local_wheel_drift_fails_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    package = next(item for item in lock["packages"] if item["name"] == "insightface")
    package["wheels"][0]["hashes"]["sha256"] = "0" * 64
    assert "local wheel identity set mismatch" in MODULE.validate(admission, lock, LOCK)


def test_runtime_authority_fails_closed() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["authority"]["model_load"] = True
    assert "dependency build admission exceeds non-runtime authority" in MODULE.validate(
        admission, lock, LOCK
    )


def test_global_environment_mutation_fails_closed() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["targets"]["global_python_environment_mutable"] = True
    assert "global Python environment must remain immutable" in MODULE.validate(
        admission, lock, LOCK
    )
