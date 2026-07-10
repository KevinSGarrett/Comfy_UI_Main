from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/gate_wave70_facial_originals_benchmark.py"
spec = importlib.util.spec_from_file_location("facial_gate", SCRIPT)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def result(name: str, tp: int, fp: int, fn: int, category: str) -> dict:
    return {
        "class_name": name,
        "metrics": {"tp": tp, "fp": fp, "fn": fn, "empty_category": category},
        "protected_neighbor_leakage": 0.0,
    }


def samples(entries: list[list[dict]]) -> list[dict]:
    return [
        {"sample_id": str(index), "status": "ok", "evaluation": {"classes": classes}}
        for index, classes in enumerate(entries)
    ]


def test_aggregate_passes_good_nonempty_class() -> None:
    records = gate.aggregate_classes(samples([[result("skin", 90, 5, 5, "gold_nonempty_pred_nonempty")]] * 3))
    assert records[0]["gate_pass"] is True
    assert records[0]["aggregate_iou"] == 270 / 300


def test_aggregate_fails_empty_gold_false_positive() -> None:
    records = gate.aggregate_classes(samples([
        [result("hat", 0, 0, 0, "gold_empty_pred_empty")],
        [result("hat", 0, 2, 0, "gold_empty_pred_nonempty")],
        [result("hat", 0, 0, 0, "gold_empty_pred_empty")],
    ]))
    assert records[0]["gold_empty_all_samples"] is True
    assert records[0]["aggregate_iou"] is None
    assert records[0]["failed_reasons"] == ["gold_empty_false_positive_pixels_present"]


def test_aggregate_fails_insufficient_samples() -> None:
    records = gate.aggregate_classes(samples([[result("hair", 100, 0, 0, "gold_nonempty_pred_nonempty")]] * 2))
    assert records[0]["gate_pass"] is False
    assert "sample_count_below_3" in records[0]["failed_reasons"]
