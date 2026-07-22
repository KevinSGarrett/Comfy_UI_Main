from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_decord_wheel_repair_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_decord_0_6_0_wheel_repair_admission.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_decord_wheel_repair_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_decord_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_real_admission_is_valid() -> None:
    assert MODULE.validate(load_admission()) == []


def test_schema_accepts_real_admission() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(load_admission())


def test_runtime_authority_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["authority"]["package_import"] = True
    assert "wheel repair admission exceeds non-runtime authority" in MODULE.validate(admission)


def test_extra_changed_entry_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["repair"]["allowed_changed_entries"].append("decord/libdecord.so")
    assert "wheel repair change boundary mismatch" in MODULE.validate(admission)


def test_source_hash_drift_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["source"]["sha256"] = "0" * 64
    assert "source wheel identity mismatch" in MODULE.validate(admission)
