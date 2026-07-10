#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


MIN_SAMPLE_COUNT = 3
MIN_IOU = 0.85
MAX_FP_VS_GOLD = 0.15
MAX_FN_VS_GOLD = 0.15
VISUAL_CLASS_LIMIT = 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aggregate_classes(sample_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in sample_results:
        if sample.get("status") != "ok":
            raise ValueError(f"sample_not_ok:{sample.get('sample_id')}")
        for result in sample.get("evaluation", {}).get("classes", []):
            buckets[str(result["class_name"])].append(result)

    records: list[dict[str, Any]] = []
    for class_name, entries in sorted(buckets.items()):
        sample_count = len(entries)
        tp = sum(int(entry["metrics"]["tp"]) for entry in entries)
        fp = sum(int(entry["metrics"]["fp"]) for entry in entries)
        fn = sum(int(entry["metrics"]["fn"]) for entry in entries)
        gold_pixels = tp + fn
        union = tp + fp + fn
        gold_empty_all = gold_pixels == 0
        iou = None if gold_empty_all else tp / union if union else 1.0
        fp_vs_gold = None if gold_empty_all else fp / gold_pixels
        fn_vs_gold = None if gold_empty_all else fn / gold_pixels
        reasons: list[str] = []
        if sample_count < MIN_SAMPLE_COUNT:
            reasons.append(f"sample_count_below_{MIN_SAMPLE_COUNT}")
        if gold_empty_all:
            if fp:
                reasons.append("gold_empty_false_positive_pixels_present")
        else:
            if iou is None or iou < MIN_IOU:
                reasons.append(f"iou_below_{MIN_IOU}")
            if fp_vs_gold is None or fp_vs_gold > MAX_FP_VS_GOLD:
                reasons.append(f"false_positive_ratio_above_{MAX_FP_VS_GOLD}")
            if fn_vs_gold is None or fn_vs_gold > MAX_FN_VS_GOLD:
                reasons.append(f"false_negative_ratio_above_{MAX_FN_VS_GOLD}")
        records.append(
            {
                "class_name": class_name,
                "sample_count": sample_count,
                "tp_sum": tp,
                "fp_sum": fp,
                "fn_sum": fn,
                "gold_pixel_sum": gold_pixels,
                "aggregate_iou": iou,
                "false_positive_ratio_vs_gold": fp_vs_gold,
                "false_negative_ratio_vs_gold": fn_vs_gold,
                "mean_protected_neighbor_leakage": sum(
                    float(entry.get("protected_neighbor_leakage", 0.0)) for entry in entries
                ) / sample_count,
                "empty_class_accounting": {
                    category: sum(entry["metrics"]["empty_category"] == category for entry in entries)
                    for category in sorted({entry["metrics"]["empty_category"] for entry in entries})
                },
                "gold_empty_all_samples": gold_empty_all,
                "gate_pass": not reasons,
                "failed_reasons": reasons,
            }
        )
    return records


def load_mask(path: Path, size: tuple[int, int]) -> Image.Image:
    if not path.is_file():
        return Image.new("L", size, 0)
    return Image.open(path).convert("L").resize(size, Image.Resampling.NEAREST)


def overlay(image: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    base = image.convert("RGB")
    tint = Image.new("RGB", base.size, color)
    alpha = mask.point(lambda value: 125 if value else 0)
    return Image.composite(tint, base, alpha)


def error_overlay(image: Image.Image, gold: Image.Image, prediction: Image.Image) -> Image.Image:
    base = image.convert("RGB")
    g = np.asarray(gold) > 0
    p = np.asarray(prediction) > 0
    false_positive = Image.fromarray(np.logical_and(p, ~g).astype("uint8") * 255)
    false_negative = Image.fromarray(np.logical_and(g, ~p).astype("uint8") * 255)
    base = overlay(base, false_positive, (230, 45, 45))
    return overlay(base, false_negative, (40, 110, 235))


def make_panel(project_root: Path, sample_results: list[dict[str, Any]], records: list[dict[str, Any]], out: Path) -> list[str]:
    candidates = [record for record in records if not record["gate_pass"] and not record["gold_empty_all_samples"]]
    candidates.sort(key=lambda record: float(record["aggregate_iou"] or 0.0))
    selected = [record["class_name"] for record in candidates[:VISUAL_CLASS_LIMIT]]
    tile = (220, 220)
    header_h = 76
    row_h = tile[1] + 42
    panel = Image.new("RGB", (tile[0] * 4, header_h + row_h * len(selected) * len(sample_results)), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((10, 8), "Facial originals-first gold benchmark: red=false positive, blue=false negative", fill="black", font=font)
    draw.text((10, 28), "Columns: original | gold overlay | prediction overlay | error overlay", fill="black", font=font)
    draw.text((10, 48), "Selected weakest nonempty classes: " + ", ".join(selected), fill="black", font=font)
    y = header_h
    gold_root = project_root / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    source_root = project_root / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img"
    for sample in sample_results:
        sample_id = str(sample["sample_id"])
        class_map = {entry["class_name"]: entry for entry in sample["evaluation"]["classes"]}
        source = Image.open(source_root / f"{sample_id}.jpg").convert("RGB").resize(tile, Image.Resampling.LANCZOS)
        for class_name in selected:
            entry = class_map[class_name]
            gold = load_mask(gold_root / f"{int(sample_id):05d}_{class_name}.png", tile)
            prediction = load_mask(Path(entry["prediction_path"]), tile)
            views = (source, overlay(source, gold, (35, 190, 90)), overlay(source, prediction, (235, 170, 25)), error_overlay(source, gold, prediction))
            for column, view in enumerate(views):
                panel.paste(view, (column * tile[0], y))
            metrics = entry["metrics"]
            draw.text((8, y + tile[1] + 8), f"ID {sample_id} | {class_name} | IoU {metrics['iou']:.3f} | leak {entry.get('protected_neighbor_leakage', 0.0):.3f}", fill="black", font=font)
            y += row_h
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate originals-first facial benchmark evidence and create visual QA.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--benchmark-evidence", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tracker-out", required=True)
    parser.add_argument("--panel-out", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    benchmark_path = Path(args.benchmark_evidence).resolve()
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if benchmark.get("status") != "pass" or benchmark.get("fail_closed_events"):
        raise ValueError("benchmark_evaluator_contract_not_pass")
    samples = benchmark.get("sample_results", [])
    records = aggregate_classes(samples)
    panel_path = Path(args.panel_out).resolve()
    selected = make_panel(project_root, samples, records, panel_path)
    blocked = [record["class_name"] for record in records if not record["gate_pass"]]
    passed = [record["class_name"] for record in records if record["gate_pass"]]
    evidence = {
        "classification": "BLOCKED_FACIAL_GOLD_BENCHMARK_METRIC_THRESHOLD_NOT_MET" if blocked else "FACIAL_GOLD_BENCHMARK_GATE_PASS",
        "benchmark_evidence": str(benchmark_path),
        "benchmark_sha256": sha256_file(benchmark_path),
        "thresholds": {
            "min_sample_count": MIN_SAMPLE_COUNT,
            "min_aggregate_iou": MIN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FP_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FN_VS_GOLD,
            "gold_empty_rule": "pass_only_when_fp_sum_is_zero",
        },
        "class_gate_records": records,
        "passed_classes": passed,
        "blocked_classes": blocked,
        "visual_qa_panel": str(panel_path),
        "visualized_classes": selected,
        "mask_promoted": False,
        "certification_authorized": False,
        "body_mask_dependency_cleared": False,
        "result": "blocked_route_repair_required" if blocked else "pass_candidate_evidence_only_no_promotion",
    }
    write_json(Path(args.out).resolve(), evidence)
    write_json(Path(args.tracker_out).resolve(), evidence)
    print(json.dumps({"result": evidence["result"], "passed": passed, "blocked": blocked, "panel": str(panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
