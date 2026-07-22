from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_python_environment_build_receipt.py"
RECEIPT = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_1_6_ENVIRONMENT_BUILD_20260722T090000Z/remote_environment_build.receipt.json"
LOCK = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_runtime_wheels_v2.toml"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_python_environment_build_receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_environment_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        json.loads(RECEIPT.read_text(encoding="utf-8")),
        tomllib.loads(LOCK.read_text(encoding="utf-8")),
    )


def test_real_receipt_is_valid() -> None:
    receipt, lock = load_inputs()
    assert MODULE.validate(receipt, RECEIPT, lock, LOCK) == []


def test_schema_accepts_real_receipt() -> None:
    receipt, _ = load_inputs()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(receipt)


def test_distribution_drift_fails_closed() -> None:
    receipt, lock = load_inputs()
    receipt = copy.deepcopy(receipt)
    next(item for item in receipt["distributions"] if item["name"] == "decord")["version"] = "0"
    assert "installed distribution manifest does not exactly match lock" in MODULE.validate(
        receipt, RECEIPT, lock, LOCK
    )


def test_tree_drift_fails_closed() -> None:
    receipt, lock = load_inputs()
    receipt = copy.deepcopy(receipt)
    receipt["environment_tree"]["sha256"] = "0" * 64
    assert "LatentSync environment tree digest mismatch" in MODULE.validate(
        receipt, RECEIPT, lock, LOCK
    )


def test_runtime_claim_fails_closed() -> None:
    receipt, lock = load_inputs()
    receipt = copy.deepcopy(receipt)
    receipt["runtime_claims"]["package_imported"] = True
    assert "environment build receipt contains a false runtime claim" in MODULE.validate(
        receipt, RECEIPT, lock, LOCK
    )
