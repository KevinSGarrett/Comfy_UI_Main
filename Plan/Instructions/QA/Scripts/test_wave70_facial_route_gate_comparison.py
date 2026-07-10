from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compare_wave70_facial_route_gates.py"
spec = importlib.util.spec_from_file_location("facial_compare", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def gate(tmp_path: Path, name: str, ids: list[str], passed: list[str], eye_iou: float | None) -> dict:
    benchmark = tmp_path / f"{name}-benchmark.json"
    benchmark.write_text(json.dumps({"sample_results": [{"sample_id": value} for value in ids]}), encoding="utf-8")
    return {
        "benchmark_evidence": str(benchmark),
        "passed_classes": passed,
        "blocked_classes": [value for value in ("eye", "hair") if value not in passed],
        "class_gate_records": [
            {"class_name": "eye", "aggregate_iou": eye_iou, "gate_pass": "eye" in passed},
            {"class_name": "hair", "aggregate_iou": 0.95, "gate_pass": "hair" in passed},
        ],
    }


def test_controlled_comparison_accepts_more_passes_without_regression(tmp_path: Path) -> None:
    result = module.compare(
        gate(tmp_path, "old", ["0", "1", "2"], ["hair"], 0.5),
        gate(tmp_path, "new", ["0", "1", "2"], ["eye", "hair"], 0.9),
    )
    assert result["candidate_route_improved"] is True
    assert result["pass_count_delta"] == 1
    assert result["newly_passed_classes"] == ["eye"]


def test_controlled_comparison_rejects_sample_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="controlled_sample_ids_mismatch"):
        module.compare(
            gate(tmp_path, "old", ["0", "1", "2"], ["hair"], 0.5),
            gate(tmp_path, "new", ["3", "4", "5"], ["eye", "hair"], 0.9),
        )


def test_controlled_comparison_rejects_pass_regression(tmp_path: Path) -> None:
    result = module.compare(
        gate(tmp_path, "old", ["0", "1", "2"], ["hair"], 0.5),
        gate(tmp_path, "new", ["0", "1", "2"], ["eye"], 0.9),
    )
    assert result["candidate_route_improved"] is False
    assert result["previously_passing_classes_regressed"] == ["hair"]


def test_controlled_comparison_classifies_improved_full_pass(tmp_path: Path) -> None:
    result = module.compare(
        gate(tmp_path, "old", ["0", "1", "2"], ["hair"], 0.5),
        gate(tmp_path, "new", ["0", "1", "2"], ["eye", "hair"], 0.9),
    )
    assert result["candidate_route_fully_passed"] is True
    assert result["classification"] == "FACIAL_NATIVE_SCALE_ROUTE_IMPROVED_FULL_GATE_PASS"


def test_controlled_comparison_all_null_iou_is_explicit(tmp_path: Path) -> None:
    baseline = gate(tmp_path, "old", ["0", "1", "2"], ["hair"], None)
    candidate = gate(tmp_path, "new", ["0", "1", "2"], ["eye", "hair"], None)
    baseline["class_gate_records"][1]["aggregate_iou"] = None
    candidate["class_gate_records"][1]["aggregate_iou"] = None
    result = module.compare(baseline, candidate)
    assert result["mean_comparable_iou_delta"] is None
    assert result["comparable_iou_class_count"] == 0


def test_controlled_comparison_rejects_pass_list_record_mismatch(tmp_path: Path) -> None:
    candidate = gate(tmp_path, "new", ["0", "1", "2"], ["eye", "hair"], 0.9)
    candidate["passed_classes"] = ["hair"]
    with pytest.raises(ValueError, match="candidate_passed_classes_inconsistent"):
        module.compare(gate(tmp_path, "old", ["0", "1", "2"], ["hair"], 0.5), candidate)
