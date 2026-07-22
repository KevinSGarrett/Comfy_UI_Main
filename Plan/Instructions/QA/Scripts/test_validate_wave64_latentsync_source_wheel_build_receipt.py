from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_source_wheel_build_receipt.py"
RECEIPT_PATH = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_1_6_SOURCE_WHEEL_BUILD_20260722T075800Z/remote_source_wheel_build.receipt.json"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_source_wheel_build_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_source_wheel_receipt", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_receipt() -> dict:
    return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def test_real_receipt_is_valid() -> None:
    assert MODULE.validate(load_receipt(), RECEIPT_PATH) == []


def test_schema_accepts_real_receipt() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(load_receipt())


def test_wheel_hash_mismatch_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["wheels"][0]["sha256"] = "0" * 64
    assert "wheel manifest mismatch" in MODULE.validate(receipt, RECEIPT_PATH)


def test_runtime_claim_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["runtime_claims"]["model_loaded"] = True
    assert "source-wheel receipt exceeds non-runtime authority" in MODULE.validate(
        receipt, RECEIPT_PATH
    )


def test_active_environment_mutation_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["active_environment"]["metadata_signature_after"] = "0" * 64
    assert "active environment mutation detected" in MODULE.validate(receipt, RECEIPT_PATH)
