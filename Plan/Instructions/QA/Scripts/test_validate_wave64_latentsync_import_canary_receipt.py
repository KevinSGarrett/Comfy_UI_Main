from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_import_canary_receipt.py"
RECEIPT = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_1_6_IMPORT_CANARY_20260722T091000Z/remote_import_canary.receipt.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_import_canary_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_import_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_receipt() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_real_receipt_is_valid() -> None:
    assert MODULE.validate(load_receipt(), RECEIPT) == []


def test_schema_accepts_real_receipt() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(load_receipt())


def test_module_origin_drift_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["imports"][0]["origin"] = "/tmp/escape.py"
    assert "module origin outside admitted roots: antlr4" in MODULE.validate(receipt, RECEIPT)


def test_decord_binary_drift_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["decord_binary"]["sha256"] = "0" * 64
    assert "decord imported binary identity mismatch" in MODULE.validate(receipt, RECEIPT)


def test_runtime_claim_drift_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["runtime_claims"]["model_constructed"] = True
    assert "LatentSync import receipt authority claims mismatch" in MODULE.validate(receipt, RECEIPT)
