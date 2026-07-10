#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_COMBINED_GOLD_POSTPROCESS_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_combined_gold_postprocess_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "best_route_masks"

MIN_MEAN_IOU = 0.85
MIN_SAMPLE_COUNT = 3
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15


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


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def abs_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_mask(path_text: str) -> np.ndarray:
    image = Image.open(abs_path(path_text)).convert("L")
    return (np.array(image) > 0).astype(np.uint8)


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.dilate(mask, kernel(radius), iterations=1)


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.erode(mask, kernel(radius), iterations=1)


def close(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel(radius))


def open_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel(radius))


def keep_largest(mask: np.ndarray, count: int) -> np.ndarray:
    labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    component_ids = list(range(1, labels_count))
    component_ids.sort(key=lambda idx: stats[idx, cv2.CC_STAT_AREA], reverse=True)
    keep = set(component_ids[:count])
    return np.isin(labels, list(keep)).astype(np.uint8)


def remove_border_components(mask: np.ndarray) -> np.ndarray:
    labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    height, width = mask.shape
    out = np.zeros_like(mask, dtype=np.uint8)
    for idx in range(1, labels_count):
        x = stats[idx, cv2.CC_STAT_LEFT]
        y = stats[idx, cv2.CC_STAT_TOP]
        w = stats[idx, cv2.CC_STAT_WIDTH]
        h = stats[idx, cv2.CC_STAT_HEIGHT]
        touches = x == 0 or y == 0 or x + w >= width or y + h >= height
        if not touches:
            out[labels == idx] = 1
    return out


def make_routes() -> dict[str, Callable[[np.ndarray], np.ndarray]]:
    routes: dict[str, Callable[[np.ndarray], np.ndarray]] = {"identity": lambda mask: mask}
    for radius in range(1, 9):
        routes[f"dilate_r{radius}"] = lambda mask, radius=radius: dilate(mask, radius)
    for radius in range(1, 5):
        routes[f"erode_r{radius}"] = lambda mask, radius=radius: erode(mask, radius)
        routes[f"open_r{radius}"] = lambda mask, radius=radius: open_mask(mask, radius)
        routes[f"close_r{radius}"] = lambda mask, radius=radius: close(mask, radius)
        routes[f"close_r{radius}_dilate_r1"] = lambda mask, radius=radius: dilate(close(mask, radius), 1)
        routes[f"open_r{radius}_dilate_r1"] = lambda mask, radius=radius: dilate(open_mask(mask, radius), 1)
    for count in (1, 2, 3):
        routes[f"keep_largest_{count}"] = lambda mask, count=count: keep_largest(mask, count)
        routes[f"keep_largest_{count}_dilate_r1"] = lambda mask, count=count: dilate(keep_largest(mask, count), 1)
        routes[f"remove_border_keep_largest_{count}"] = (
            lambda mask, count=count: keep_largest(remove_border_components(mask), count)
        )
    return routes


def metrics(gold: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    gold_bits = gold > 0
    pred_bits = pred > 0
    gold_count = int(gold_bits.sum())
    pred_count = int(pred_bits.sum())
    intersection = int(np.logical_and(gold_bits, pred_bits).sum())
    union = int(np.logical_or(gold_bits, pred_bits).sum())
    false_positive = int(np.logical_and(~gold_bits, pred_bits).sum())
    false_negative = int(np.logical_and(gold_bits, ~pred_bits).sum())
    dice_denominator = gold_count + pred_count
    return {
        "gold_pixels": gold_count,
        "pred_pixels": pred_count,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "false_positive_pixels": false_positive,
        "false_negative_pixels": false_negative,
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / dice_denominator, 6) if dice_denominator else 1.0,
        "false_positive_ratio_vs_gold": round(false_positive / gold_count, 6) if gold_count else None,
        "false_negative_ratio_vs_gold": round(false_negative / gold_count, 6) if gold_count else None,
    }


def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "mean_iou": round(sum(float(item["iou"]) for item in values) / len(values), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in values) / len(values), 6),
        "mean_false_positive_ratio_vs_gold": round(
            sum(float(item["false_positive_ratio_vs_gold"] or 0.0) for item in values) / len(values),
            6,
        ),
        "mean_false_negative_ratio_vs_gold": round(
            sum(float(item["false_negative_ratio_vs_gold"] or 0.0) for item in values) / len(values),
            6,
        ),
    }


def pass_gate(summary: dict[str, Any]) -> tuple[bool, list[str]]:
    failed: list[str] = []
    if int(summary["sample_count"]) < MIN_SAMPLE_COUNT:
        failed.append(f"sample_count_below_{MIN_SAMPLE_COUNT}")
    if float(summary["mean_iou"]) < MIN_MEAN_IOU:
        failed.append(f"mean_iou_below_{MIN_MEAN_IOU}")
    if float(summary["mean_false_positive_ratio_vs_gold"]) > MAX_FALSE_POSITIVE_RATIO_VS_GOLD:
        failed.append(f"false_positive_ratio_above_{MAX_FALSE_POSITIVE_RATIO_VS_GOLD}")
    if float(summary["mean_false_negative_ratio_vs_gold"]) > MAX_FALSE_NEGATIVE_RATIO_VS_GOLD:
        failed.append(f"false_negative_ratio_above_{MAX_FALSE_NEGATIVE_RATIO_VS_GOLD}")
    return not failed, failed


def route_score(summary: dict[str, Any]) -> float:
    return (
        float(summary["mean_iou"])
        - 0.20 * max(0.0, float(summary["mean_false_positive_ratio_vs_gold"]) - MAX_FALSE_POSITIVE_RATIO_VS_GOLD)
        - 0.20 * max(0.0, float(summary["mean_false_negative_ratio_vs_gold"]) - MAX_FALSE_NEGATIVE_RATIO_VS_GOLD)
    )


def collect_records() -> tuple[list[dict[str, Any]], dict[str, str]]:
    celeba_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    records: list[dict[str, Any]] = []
    for dataset, path in (("CelebAMask-HQ", celeba_path), ("LaPa", lapa_path)):
        evidence = load_json(path)
        for record in evidence.get("comparison_records", []):
            item = dict(record)
            item["dataset"] = dataset
            item["source_evidence"] = rel(path)
            records.append(item)
    return records, {"celeba": rel(celeba_path), "lapa": rel(lapa_path)}


def evaluate_routes(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    routes = make_routes()
    by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_region[str(record["region"])].append(record)

    region_summaries: list[dict[str, Any]] = []
    best_sample_records: list[dict[str, Any]] = []
    for region, region_records in sorted(by_region.items()):
        route_summaries: list[dict[str, Any]] = []
        route_sample_metrics: dict[str, list[dict[str, Any]]] = {}
        for route_name, transform in routes.items():
            sample_values: list[dict[str, Any]] = []
            for record in region_records:
                gold = load_mask(str(record["gold_comparison_mask"]))
                pred = load_mask(str(record["pred_comparison_mask"]))
                routed = transform(pred).astype(np.uint8)
                sample_metric = {
                    "dataset": record["dataset"],
                    "sample_id": record.get("sample_id", record.get("stem", record.get("sample_index"))),
                    "metrics": metrics(gold, routed),
                }
                sample_values.append(sample_metric)
            summary = summarize([item["metrics"] for item in sample_values])
            passed, failed = pass_gate(summary)
            route_summaries.append(
                {
                    "route": route_name,
                    "summary": summary,
                    "pass_gate": passed,
                    "failed_reasons": failed,
                    "score": round(route_score(summary), 6),
                }
            )
            route_sample_metrics[route_name] = sample_values
        route_summaries.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
        best = route_summaries[0]
        region_summaries.append(
            {
                "region": region,
                "dataset_sample_count": len(region_records),
                "best_route": best["route"],
                "best_summary": best["summary"],
                "best_pass_gate": best["pass_gate"],
                "best_failed_reasons": best["failed_reasons"],
                "top_routes": route_summaries[:8],
                "decision": (
                    "combined_gold_postprocess_route_candidate_found_not_promoted"
                    if best["pass_gate"]
                    else "combined_gold_postprocess_routes_blocked_stronger_route_required"
                ),
            }
        )
        for sample_metric in route_sample_metrics[best["route"]]:
            best_sample_records.append({"region": region, "best_route": best["route"], **sample_metric})
    return region_summaries, best_sample_records


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def tile(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail((190, 190))
    out = Image.new("RGB", (190, 238), "white")
    out.paste(image, ((190 - image.width) // 2, 48 + (190 - image.height) // 2))
    draw = ImageDraw.Draw(out)
    draw.text((6, 5), title[:30], fill=(0, 0, 0), font=font(14))
    if subtitle:
        draw.text((6, 25), subtitle[:42], fill=(60, 60, 60), font=font(11))
    return out


def mask_rgb(mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    bg = np.zeros((*mask.shape, 3), dtype=np.uint8)
    bg[mask > 0] = color
    return Image.fromarray(bg)


def error_rgb(gold: np.ndarray, pred: np.ndarray) -> Image.Image:
    out = np.zeros((*gold.shape, 3), dtype=np.uint8) + 22
    out[np.logical_and(gold > 0, pred > 0)] = (245, 245, 245)
    out[np.logical_and(gold == 0, pred > 0)] = (230, 45, 45)
    out[np.logical_and(gold > 0, pred == 0)] = (40, 130, 240)
    return Image.fromarray(out)


def make_panels(records: list[dict[str, Any]], region_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    routes = make_routes()
    by_region_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_region_record[str(record["region"])].append(record)
    panels: list[dict[str, Any]] = []
    for summary in region_summaries:
        region = summary["region"]
        route_name = summary["best_route"]
        transform = routes[route_name]
        cells: list[Image.Image] = []
        for record in by_region_record[region][:4]:
            gold = load_mask(str(record["gold_comparison_mask"]))
            pred = load_mask(str(record["pred_comparison_mask"]))
            routed = transform(pred).astype(np.uint8)
            routed_path = MASK_DIR / f"{record['dataset']}_{record.get('sample_id', record.get('stem', record.get('sample_index')))}_{region}_{route_name}.png"
            save_mask(routed, routed_path)
            m = metrics(gold, routed)
            cells.extend(
                [
                    tile(mask_rgb(gold, (0, 210, 220)), f"{region} gold", str(record["dataset"])),
                    tile(mask_rgb(pred, (255, 210, 0)), "baseline pred", f"IoU {metrics(gold, pred)['iou']}"),
                    tile(mask_rgb(routed, (20, 210, 80)), f"best {route_name}", f"IoU {m['iou']}"),
                    tile(error_rgb(gold, routed), "best error", "red FP / blue FN"),
                ]
            )
        cols = 4
        cell_w = max(cell.width for cell in cells)
        cell_h = max(cell.height for cell in cells)
        rows = (len(cells) + cols - 1) // cols
        panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
        for index, cell in enumerate(cells):
            panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
        panel_path = PANEL_DIR / f"{region}_{route_name}_combined_gold_panel.png"
        panel.save(panel_path)
        panels.append({"region": region, "best_route": route_name, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    records, source_evidence = collect_records()
    region_summaries, best_sample_metrics = evaluate_routes(records)
    panels = make_panels(records, region_summaries)
    candidates = [item for item in region_summaries if item["best_pass_gate"]]
    blocked = [item for item in region_summaries if not item["best_pass_gate"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "combined CelebAMask-HQ plus LaPa gold-mask postprocess route search for Wave70 facial regions",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": source_evidence,
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "min_sample_count": MIN_SAMPLE_COUNT,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": "identity, dilation, erosion, opening, closing, largest-component, border-component cleanup",
        "region_route_records": region_summaries,
        "best_sample_metrics": best_sample_metrics,
        "review_panels": panels,
        "candidate_regions": [item["region"] for item in candidates],
        "blocked_regions": [item["region"] for item in blocked],
        "result": (
            "combined_gold_postprocess_candidates_found_no_promotion"
            if candidates
            else "combined_gold_postprocess_routes_all_blocked_stronger_routes_required"
        ),
        "next_required_action": (
            "Only candidate regions may proceed to target-specific source-overlay review. Blocked regions need model-backed, "
            "dataset-policy, or boundary-aware repair beyond this simple postprocess route family."
        ),
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": str(evidence_path),
                "tracker": str(tracker_path),
                "result": evidence["result"],
                "candidate_regions": evidence["candidate_regions"],
                "blocked_regions": evidence["blocked_regions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
