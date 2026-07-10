#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageFilter


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
BENCHMARK_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_STANDARD_BENCHMARK_20260710T012300-0500.json"
)
GATE_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_BENCHMARK_GATE_20260710T013355-0500.json"
)
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MF70_NECK_GOLD_FAILURE_DIAGNOSTIC_{RUN_STAMP}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pixel_bits(image: Image.Image) -> list[int]:
    return [1 if value else 0 for value in image.convert("L").getdata()]


def metrics(gold: Image.Image, pred: Image.Image) -> dict[str, Any]:
    gold_bits = pixel_bits(gold)
    pred_bits = pixel_bits(pred)
    gold_count = sum(gold_bits)
    pred_count = sum(pred_bits)
    intersection = sum(1 for g, p in zip(gold_bits, pred_bits) if g and p)
    union = sum(1 for g, p in zip(gold_bits, pred_bits) if g or p)
    false_positive = sum(1 for g, p in zip(gold_bits, pred_bits) if not g and p)
    false_negative = sum(1 for g, p in zip(gold_bits, pred_bits) if g and not p)
    return {
        "gold_pixels": gold_count,
        "pred_pixels": pred_count,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "false_positive_pixels": false_positive,
        "false_negative_pixels": false_negative,
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / (gold_count + pred_count), 6) if gold_count + pred_count else 1.0,
        "false_positive_ratio_vs_gold": round(false_positive / gold_count, 6) if gold_count else None,
        "false_negative_ratio_vs_gold": round(false_negative / gold_count, 6) if gold_count else None,
    }


def mean_metric(records: list[dict[str, Any]], key: str) -> float:
    return round(sum(float(record[key] or 0.0) for record in records) / len(records), 6)


def load_neck_records() -> list[dict[str, Any]]:
    benchmark = json.loads(BENCHMARK_EVIDENCE.read_text(encoding="utf-8"))
    return [record for record in benchmark["comparison_records"] if record["region"] == "mf70_neck"]


def run_dilation_sweep(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sweep: list[dict[str, Any]] = []
    for radius in [0, 1, 2, 3, 4, 5, 7, 9, 11]:
        sample_metrics: list[dict[str, Any]] = []
        for record in records:
            gold = Image.open(PROJECT_ROOT / record["gold_comparison_mask"]).convert("L")
            pred = Image.open(PROJECT_ROOT / record["pred_comparison_mask"]).convert("L")
            if radius:
                pred = pred.filter(ImageFilter.MaxFilter(radius * 2 + 1)).point(lambda value: 255 if value else 0)
            sample_metric = metrics(gold, pred)
            sample_metric["sample_id"] = record["sample_id"]
            sample_metrics.append(sample_metric)
        sweep.append(
            {
                "radius": radius,
                "mean_iou": mean_metric(sample_metrics, "iou"),
                "mean_dice": mean_metric(sample_metrics, "dice"),
                "mean_false_positive_ratio_vs_gold": mean_metric(sample_metrics, "false_positive_ratio_vs_gold"),
                "mean_false_negative_ratio_vs_gold": mean_metric(sample_metrics, "false_negative_ratio_vs_gold"),
                "sample_metrics": sample_metrics,
            }
        )
    return sweep


def main() -> int:
    neck_records = load_neck_records()
    gate = json.loads(GATE_EVIDENCE.read_text(encoding="utf-8"))
    sweep = run_dilation_sweep(neck_records)
    best_by_iou = max(sweep, key=lambda record: record["mean_iou"])
    original = next(record for record in sweep if record["radius"] == 0)

    per_sample = []
    for record in neck_records:
        gold_path = PROJECT_ROOT / record["gold_comparison_mask"]
        pred_path = PROJECT_ROOT / record["pred_comparison_mask"]
        gold = Image.open(gold_path).convert("L")
        pred = Image.open(pred_path).convert("L")
        per_sample.append(
            {
                "sample_id": record["sample_id"],
                "gold_mask": record["gold_comparison_mask"],
                "pred_mask": record["pred_comparison_mask"],
                "gold_bbox": gold.getbbox(),
                "pred_bbox": pred.getbbox(),
                "metrics": record["metrics"],
            }
        )

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local mf70_neck gold benchmark failure diagnostic and simple repair experiment",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "benchmark_evidence": rel(BENCHMARK_EVIDENCE),
        "benchmark_sha256": sha256(BENCHMARK_EVIDENCE),
        "gate_evidence": rel(GATE_EVIDENCE),
        "gate_sha256": sha256(GATE_EVIDENCE),
        "gate_result": gate["result"],
        "per_sample_neck_records": per_sample,
        "dilation_sweep": sweep,
        "best_simple_dilation_by_iou": best_by_iou,
        "original_metrics": original,
        "diagnostic_result": "mf70_neck_blocked_simple_expansion_not_sufficient",
        "finding": (
            "The weakest sample is 18000, where the parser neck mask is much narrower than the gold neck mask. "
            "A small dilation improves mean IoU from 0.726100 to 0.745391 but remains below the 0.85 gate, "
            "while larger dilation increases false positives and degrades mean IoU. The repair cannot be a broad expansion only."
        ),
        "next_required_action": (
            "Build a neck-specific parser/postprocess candidate that uses neighboring face/skin/hair/clothing boundaries and gold-mask "
            "error panels, then rerun the gold benchmark/gate. Keep mf70_neck unpromoted."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "diagnostic_result": evidence["diagnostic_result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
