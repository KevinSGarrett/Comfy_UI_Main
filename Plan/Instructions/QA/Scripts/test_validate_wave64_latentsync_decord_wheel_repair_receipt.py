from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_decord_wheel_repair_receipt.py"
RECEIPT = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_DECORD_WHEEL_REPAIR_20260722T084500Z/remote_decord_wheel_repair.receipt.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_decord_wheel_repair_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_decord_repair_receipt", SCRIPT)
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


def test_binary_drift_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["repaired_wheel"]["binary_sha256"] = "0" * 64
    assert "decord shared-library bytes changed" in MODULE.validate(receipt, RECEIPT)


def test_extra_changed_entry_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["repaired_wheel"]["changed_entries"].append("decord/libdecord.so")
    assert "decord repair exceeded the two-entry boundary" in MODULE.validate(receipt, RECEIPT)


def test_runtime_claim_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["runtime_claims"]["package_imported"] = True
    assert "decord repair receipt exceeds non-runtime authority" in MODULE.validate(receipt, RECEIPT)
