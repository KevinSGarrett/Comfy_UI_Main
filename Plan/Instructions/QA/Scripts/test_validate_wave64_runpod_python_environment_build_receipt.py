from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_python_environment_build_receipt.py"
RECEIPT_PATH = ROOT / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_ENVIRONMENT_BUILD_20260722T010500Z/remote_environment_build.receipt.json"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_python_environment_build_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_python_environment_build_receipt", SCRIPT_PATH)
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


def test_runtime_claim_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["runtime_claims"]["model_library_imported"] = True
    assert "environment build receipt contains a false runtime claim" in MODULE.validate(
        receipt, RECEIPT_PATH
    )


def test_key_distribution_mismatch_fails_closed() -> None:
    receipt = copy.deepcopy(load_receipt())
    next(item for item in receipt["distributions"] if item["name"].lower() == "qwen-asr")[
        "version"
    ] = "0"
    assert "qwen-asr: installed version mismatch" in MODULE.validate(receipt, RECEIPT_PATH)


def test_verification_correction_cannot_change_bytes() -> None:
    receipt = copy.deepcopy(load_receipt())
    receipt["verification_command_correction"]["installed_bytes_changed_by_correction"] = True
    assert "verification correction cannot mutate installed bytes" in MODULE.validate(
        receipt, RECEIPT_PATH
    )
