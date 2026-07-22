from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_import_canary_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_import_canary_admission.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_import_canary_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_import_admission", SCRIPT)
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


def test_gpu_authority_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["authority"]["gpu_or_lease_poll"] = True
    assert "import canary admission exceeds import-only authority" in MODULE.validate(admission)


def test_import_set_drift_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["imports"].pop()
    assert "import canary module set mismatch" in MODULE.validate(admission)


def test_environment_receipt_drift_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["environment"]["receipt_sha256"] = "0" * 64
    assert "import canary environment receipt binding mismatch" in MODULE.validate(admission)
