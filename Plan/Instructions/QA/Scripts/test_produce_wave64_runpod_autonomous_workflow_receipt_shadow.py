from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_workflow_receipt_shadow.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_workflow_receipt_shadow", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_producer_retains_four_receipts_and_bound_static_validation(tmp_path: Path) -> None:
    module = load_producer()
    output = tmp_path / "shadow"
    evidence = module.produce(output, "a" * 40, "2026-07-21T23:10:00Z")
    assert evidence["disposition"] == "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_INSPECTION_ONLY"
    assert evidence["receipt_count"] == 4
    assert evidence["input_binding_disposition"] == "PASS_EXECUTOR_RECEIPT_BOUND"
    assert evidence["validation_disposition"] == "PASS_STATIC_VALIDATION"
    assert evidence["sandbox_execution_performed"] is False
    assert not any(evidence["runtime_claims"].values())
    validation = json.loads((output / "workflow_validation.json").read_text(encoding="utf-8"))
    assert len(validation["input_executor_receipt_ids"]) == 4
    assert set(validation["input_executor_receipt_ids"]) == {
        "workflow", "object_info", "contract", "model_inventory"
    }
    assert (output / "evidence.json").is_file()


def test_producer_refuses_overwrite_and_invalid_identity_or_time(tmp_path: Path) -> None:
    module = load_producer()
    output = tmp_path / "shadow"
    module.produce(output, "a" * 40, "2026-07-21T23:10:00Z")
    with pytest.raises(module.ShadowProducerError, match="already exists"):
        module.produce(output, "a" * 40, "2026-07-21T23:10:00Z")
    with pytest.raises(module.ShadowProducerError, match="source_head"):
        module.produce(tmp_path / "bad-head", "not-a-hash", "2026-07-21T23:10:00Z")
    with pytest.raises(module.ShadowProducerError, match="observed_at"):
        module.produce(tmp_path / "bad-time", "a" * 40, "not-a-time")
