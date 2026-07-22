from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_model_storage_transaction.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_storage_transaction", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.TRANSACTION_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["transaction_id"] = module.content_id(candidate)
    return candidate


def test_prepared_transaction_is_exact_and_non_executable() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_transaction(ROOT, candidate)
    assert candidate["storage_gate"]["minimum_verified_free_before_bytes"] == 62068284540
    assert candidate["executable"] is False
    assert len(candidate["blockers"]) == 6


def test_wrong_target_or_hash_is_rejected() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["files"][0]["target_path"] = candidate["files"][1]["target_path"]
    candidate = resign(module, candidate)
    with pytest.raises(module.StorageTransactionError, match="file identity drift"):
        module.validate_transaction(ROOT, candidate)


def test_reserve_arithmetic_drift_is_rejected() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["storage_gate"]["minimum_verified_free_before_bytes"] += 1
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_transaction(ROOT, candidate)


def test_missing_vae_cannot_be_marked_verified_or_transaction_executable() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["files"][1]["source"]["local_bytes_verified"] = True
    candidate["files"][1]["source"]["state"] = "EXACT_LOCAL_HASH_VERIFIED"
    candidate["files"][1]["source"]["kind"] = "retained_local_file"
    candidate = resign(module, candidate)
    with pytest.raises(module.StorageTransactionError, match="falsely marked local"):
        module.validate_transaction(ROOT, candidate)
    candidate = copy.deepcopy(value(module))
    candidate["executable"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_transaction(ROOT, candidate)
