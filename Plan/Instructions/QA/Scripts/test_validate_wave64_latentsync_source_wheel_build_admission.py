from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_source_wheel_build_admission.py"
ADMISSION_PATH = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_source_wheel_build_admission.json"
LOCK_PATH = ROOT / "Plan/10_REGISTRIES/Locks/wave64_latentsync_1_6_source_wheel_builder_py311.pylock.toml"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_source_wheel_build_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_source_wheel_admission", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(ADMISSION_PATH.read_text(encoding="utf-8")),
        tomllib.loads(LOCK_PATH.read_text(encoding="utf-8")),
    )


def test_real_admission_and_builder_lock_are_valid() -> None:
    admission, lock = load_inputs()
    assert MODULE.validate(admission, lock, LOCK_PATH) == []


def test_schema_accepts_real_admission() -> None:
    admission, _ = load_inputs()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(admission)


def test_source_hash_mismatch_fails_closed() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["sources"][0]["sha256"] = "0" * 64
    assert "source distribution set or hash mismatch" in MODULE.validate(admission, lock, LOCK_PATH)


def test_runtime_install_authority_fails_closed() -> None:
    admission, lock = load_inputs()
    admission = copy.deepcopy(admission)
    admission["authority"]["runtime_environment_install"] = True
    assert "source-wheel admission exceeds build authority" in MODULE.validate(
        admission, lock, LOCK_PATH
    )


def test_builder_host_mismatch_fails_closed() -> None:
    admission, lock = load_inputs()
    lock = copy.deepcopy(lock)
    lock["packages"][0]["wheels"][0]["url"] = "https://example.invalid/package.whl"
    assert "builder host allowlist mismatch" in MODULE.validate(admission, lock, LOCK_PATH)
