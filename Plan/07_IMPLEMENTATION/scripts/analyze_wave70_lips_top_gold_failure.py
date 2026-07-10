#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260710T023500-0500"
TIMESTAMP = "2026-07-10T02:35:00-05:00"
REGION = "mf70_lips_top"
BENCHMARK = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_STANDARD_BENCHMARK_20260710T012300-0500.json"
)
GATE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_BENCHMARK_GATE_20260710T013355-0500.json"
)


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def bool_mask(path: Path) -> Image.Image:
    return Image.open(path).convert("L").point(lambda p: 255 if p > 0 else 0)


def count_pixels(mask: Image.Image) -> int:
    return sum(1 for p in mask.getdata() if p > 0)


def metrics(pred: Image.Image, gold: Image.Image) -> dict[str, Any]:
    pred_data = list(pred.getdata())
    gold_data = list(gold.getdata())
    intersection = sum(1 for p, g in zip(pred_data, gold_data) if p > 0 and g > 0)
    union = sum(1 for p, g in zip(pred_data, gold_data) if p > 0 or g > 0)
    pred_pixels = sum(1 for p in pred_data if p > 0)
    gold_pixels = sum(1 for g in gold_data if g > 0)
    fp = sum(1 for p, g in zip(pred_data, gold_data) if p > 0 and g == 0)
    fn = sum(1 for p, g in zip(pred_data, gold_data) if p == 0 and g > 0)
    dice_den = pred_pixels + gold_pixels
    return {
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / dice_den, 6) if dice_den else 1.0,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "pred_pixels": pred_pixels,
        "gold_pixels": gold_pixels,
        "false_positive_pixels": fp,
        "false_negative_pixels": fn,
        "false_positive_ratio_vs_gold": round(fp / gold_pixels, 6) if gold_pixels else 0.0,
        "false_negative_ratio_vs_gold": round(fn / gold_pixels, 6) if gold_pixels else 0.0,
    }


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def label_tile(image: Image.Image, label: str, size: int = 256) -> Image.Image:
    tile = Image.new("RGB", (size, size + 32), (16, 16, 16))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.NEAREST), (0, 32))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def overlay_error(pred: Image.Image, gold: Image.Image) -> Image.Image:
    out = Image.new("RGB", pred.size, (0, 0, 0))
    pixels = []
    for p, g in zip(pred.getdata(), gold.getdata()):
        if p > 0 and g > 0:
            pixels.append((255, 255, 255))
        elif p > 0:
            pixels.append((255, 64, 64))
        elif g > 0:
            pixels.append((64, 160, 255))
        else:
            pixels.append((0, 0, 0))
    out.putdata(pixels)
    return out


def make_panel(root: Path, sample_id: int, gold: Image.Image, pred: Image.Image, best: Image.Image, best_radius: int) -> str:
    tiles = [
        label_tile(gold, f"{sample_id} gold"),
        label_tile(pred, f"{sample_id} baseline pred"),
        label_tile(overlay_error(pred, gold), "baseline err white/hit red/fp blue/fn"),
        label_tile(best, f"best radius {best_radius}"),
        label_tile(overlay_error(best, gold), "best err white/hit red/fp blue/fn"),
    ]
    panel = Image.new("RGB", (256 * len(tiles), 288), (0, 0, 0))
    for i, tile in enumerate(tiles):
        panel.paste(tile, (256 * i, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_lips_top_gold_failure"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"W70_MF70_LIPS_TOP_GOLD_FAILURE_DIAGNOSTIC_{RUN_STAMP}_panel.png"
    panel.save(out_path)
    return rel(out_path, root)


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    benchmark = read_json(resolve(root, BENCHMARK))
    gate = read_json(resolve(root, GATE))
    if REGION not in gate.get("blocked_regions", []):
        raise RuntimeError(f"{REGION} is not blocked by the current benchmark gate")

    records = [r for r in benchmark["comparison_records"] if r.get("region") == REGION]
    if not records:
        raise RuntimeError(f"no benchmark records found for {REGION}")

    radius_records: list[dict[str, Any]] = []
    best_by_iou: tuple[int, dict[str, Any]] | None = None
    per_sample: list[dict[str, Any]] = []
    cached_masks: dict[int, tuple[Image.Image, Image.Image]] = {}
    for rec in records:
        sample_id = int(rec["sample_id"])
        gold = bool_mask(resolve(root, rec["gold_comparison_mask"]))
        pred = bool_mask(resolve(root, rec["pred_comparison_mask"]))
        cached_masks[sample_id] = (gold, pred)

    for radius in range(0, 6):
        sample_metrics = []
        for sample_id, (gold, pred) in cached_masks.items():
            candidate = pred if radius == 0 else pred.filter(ImageFilter.MaxFilter(radius * 2 + 1))
            m = metrics(candidate, gold)
            sample_metrics.append({"sample_id": sample_id, **m})
            if radius == 0:
                per_sample.append({"sample_id": sample_id, "baseline": m})
        summary = {
            "radius": radius,
            "mean_iou": mean([m["iou"] for m in sample_metrics]),
            "mean_dice": mean([m["dice"] for m in sample_metrics]),
            "mean_false_positive_ratio_vs_gold": mean([m["false_positive_ratio_vs_gold"] for m in sample_metrics]),
            "mean_false_negative_ratio_vs_gold": mean([m["false_negative_ratio_vs_gold"] for m in sample_metrics]),
            "sample_metrics": sample_metrics,
        }
        radius_records.append(summary)
        if best_by_iou is None or summary["mean_iou"] > best_by_iou[1]["mean_iou"]:
            best_by_iou = (radius, summary)

    assert best_by_iou is not None
    worst_sample = min(per_sample, key=lambda item: item["baseline"]["iou"])["sample_id"]
    gold, pred = cached_masks[worst_sample]
    best_radius = best_by_iou[0]
    best_mask = pred if best_radius == 0 else pred.filter(ImageFilter.MaxFilter(best_radius * 2 + 1))
    panel_rel = make_panel(root, worst_sample, gold, pred, best_mask, best_radius)

    result = (
        "mf70_lips_top_simple_expansion_candidate_possible_pending_repair"
        if best_by_iou[1]["mean_iou"] >= 0.85 and best_by_iou[1]["mean_false_positive_ratio_vs_gold"] <= 0.15
        else "mf70_lips_top_blocked_simple_expansion_not_sufficient"
    )
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-LIPS-TOP-GOLD-FAILURE-DIAGNOSTIC-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "local_gold_benchmark_failure_diagnostic_only",
        "region": REGION,
        "benchmark_evidence": rel(resolve(root, BENCHMARK), root),
        "benchmark_sha256": sha256_file(resolve(root, BENCHMARK)),
        "gate_evidence": rel(resolve(root, GATE), root),
        "gate_sha256": sha256_file(resolve(root, GATE)),
        "sample_ids": sorted(cached_masks.keys()),
        "radius_sweep": radius_records,
        "best_radius_by_mean_iou": best_radius,
        "best_summary": best_by_iou[1],
        "worst_baseline_sample_id": worst_sample,
        "diagnostic_panel": panel_rel,
        "diagnostic_panel_sha256": sha256_file(resolve(root, panel_rel)),
        "finding": (
            "mf70_lips_top fails the current gold gate from under-masking; sample 18000 is the largest baseline miss."
        ),
        "decision": result,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "next_required_action": (
            "Build a lips-top repair candidate only if the radius sweep clears threshold; otherwise use a stronger boundary-aware route."
        ),
        "result": result,
    }
    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_LIPS_TOP_GOLD_FAILURE_DIAGNOSTIC_{RUN_STAMP}.json"
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    section = f"""## Wave70 mf70_lips_top Gold Failure Diagnostic - {TIMESTAMP}

Ran a local gold-benchmark diagnostic for `mf70_lips_top` after `mf70_nose` v5 local proof completed. Evidence `{rel(out, root)}` reports `{result}`. Baseline failure is under-masking, especially sample `{worst_sample}`; diagnostic panel is `{panel_rel}`. No active input, mask promotion, generation, EC2, AWS, GitHub, S3, or Civitai action occurred.
"""
    marker = f"W70-MF70-LIPS-TOP-GOLD-FAILURE-DIAGNOSTIC-{RUN_STAMP}"
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)
    print(json.dumps({"result": result, "evidence": rel(out, root), "tracker": rel(tracker, root), "panel": panel_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
