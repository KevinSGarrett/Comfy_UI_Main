from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_qwen3_omni_python_environment_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_omni_dependency_environment_admission.json"
LOCK = ROOT / "Plan/10_REGISTRIES/Locks/wave64_qwen3_omni_transformers_5_2_0_py312_cu124.pylock.toml"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_python_environment_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("qwen3_omni_environment_admission", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(ADMISSION.read_text(encoding="utf-8")),
        tomllib.loads(LOCK.read_text(encoding="utf-8")),
    )


def test_real_admission_lock_and_schema_are_valid() -> None:
    admission, lock = load_inputs()
    assert MODULE.validate(admission, lock, LOCK) == []
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(admission)


def test_wheel_host_and_hash_drift_fail_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    lock["packages"][0]["wheels"][0]["url"] = "https://example.invalid/a.whl"
    lock["packages"][1]["wheels"][0]["hashes"]["sha256"] = "bad"
    errors = MODULE.validate(admission, lock, LOCK)
    assert "dependency wheel host allowlist mismatch" in errors
    assert any("wheel SHA-256 missing" in error for error in errors)


def test_key_versions_and_runtime_authority_fail_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    next(item for item in lock["packages"] if item["name"] == "transformers")["version"] = "0"
    admission = copy.deepcopy(admission)
    admission["authority"]["model_load"] = True
    errors = MODULE.validate(admission, lock, LOCK)
    assert "transformers: required version mismatch" in errors
    assert "dependency build admission exceeds non-runtime authority" in errors


def test_base_python_cannot_be_reinstalled_or_substituted() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["base_python"]["install_allowed"] = True
    admission["base_python"]["sha256"] = "0" * 64
    assert "base Python reuse identity mismatch" in MODULE.validate(admission, lock, LOCK)
