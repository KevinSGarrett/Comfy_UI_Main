from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_python_environment_admission.py"
ADMISSION_PATH = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_asr_17b_dependency_environment_admission.json"
LOCK_PATH = ROOT / "Plan/10_REGISTRIES/Locks/wave64_qwen3_asr_0_0_6_py312_cu124.pylock.toml"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_python_environment_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_python_environment_admission", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(ADMISSION_PATH.read_text(encoding="utf-8")),
        tomllib.loads(LOCK_PATH.read_text(encoding="utf-8")),
    )


def test_real_admission_and_lock_are_valid() -> None:
    admission, lock = load_inputs()
    assert MODULE.validate(admission, lock, LOCK_PATH) == []


def test_schema_accepts_real_admission() -> None:
    admission, _ = load_inputs()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(admission)


def test_unexpected_wheel_host_fails_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    lock["packages"][0]["wheels"][0]["url"] = "https://example.invalid/package.whl"
    errors = MODULE.validate(admission, lock, LOCK_PATH)
    assert "dependency wheel host allowlist mismatch" in errors


def test_runtime_authority_fails_closed() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["authority"]["model_load"] = True
    assert "dependency build admission exceeds non-runtime authority" in MODULE.validate(
        admission, lock, LOCK_PATH
    )


def test_key_package_version_mismatch_fails_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    next(package for package in lock["packages"] if package["name"] == "transformers")["version"] = "0"
    assert "transformers: required version mismatch" in MODULE.validate(admission, lock, LOCK_PATH)
