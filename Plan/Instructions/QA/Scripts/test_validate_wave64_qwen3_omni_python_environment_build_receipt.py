from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_qwen3_omni_python_environment_build_receipt.py"
RECEIPT = ROOT / "Plan/Tracker/Evidence/W64_AQA_QWEN3_OMNI_ENVIRONMENT_BUILD_20260722T024800Z/remote_environment_build.receipt.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_python_environment_build_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_qwen3_omni_environment_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_receipt() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_real_receipt_and_schema_are_valid() -> None:
    receipt = load_receipt()
    assert MODULE.validate(receipt, RECEIPT) == []
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        receipt
    )


def test_runtime_claim_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["runtime_claims"]["model_library_imported"] = True
    assert "environment build receipt contains a false runtime claim" in MODULE.validate(
        receipt, RECEIPT
    )


def test_key_version_and_decord_fail_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    next(item for item in receipt["distributions"] if item["name"] == "torchvision")[
        "version"
    ] = "0"
    receipt["distributions"][0]["name"] = "decord"
    errors = MODULE.validate(receipt, RECEIPT)
    assert "torchvision: installed version mismatch" in errors
    assert "incompatible Decord distribution is installed" in errors


def test_active_environment_change_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["active_environment"]["metadata_signature_after"] = "0" * 64
    assert "active Python environment changed" in MODULE.validate(receipt, RECEIPT)
