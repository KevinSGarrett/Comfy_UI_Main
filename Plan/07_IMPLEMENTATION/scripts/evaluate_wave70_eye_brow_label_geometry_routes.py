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
EVIDENCE_ID = f"W70_EYE_BROW_LABEL_GEOMETRY_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_eye_brow_label_geometry_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGIONS = ("mf70_eyes_full", "mf70_eyebrows")

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


def load_mask(path_text: str, shape: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(abs_path(path_text)).convert("L")
    mask = (np.array(image) > 0).astype(np.uint8)
    if shape is not None and mask.shape != shape:
        mask = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return mask


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def kernel(width: int, height: int, ellipse: bool = True) -> np.ndarray:
    shape = cv2.MORPH_ELLIPSE if ellipse else cv2.MORPH_RECT
    return cv2.getStructuringElement(shape, (max(1, width), max(1, height)))


def keep_largest(mask: np.ndarray, count: int = 2) -> np.ndarray:
    labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    ids = list(range(1, labels_count))
    ids.sort(key=lambda idx: stats[idx, cv2.CC_STAT_AREA], reverse=True)
    return np.isin(labels, ids[:count]).astype(np.uint8)


def component_boxes(mask: np.ndarray, count: int = 2) -> list[tuple[int, int, int, int]]:
    labels_count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    ids = list(range(1, labels_count))
    ids.sort(key=lambda idx: stats[idx, cv2.CC_STAT_AREA], reverse=True)
    boxes = []
    for idx in ids[:count]:
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        boxes.append((x, y, x + w, y + h))
    return boxes


def box_expand(mask: np.ndarray, x_factor: float, y_factor: float, mode: str) -> np.ndarray:
    out = np.zeros_like(mask, dtype=np.uint8)
    for x1, y1, x2, y2 in component_boxes(mask, 2):
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        nx1 = max(0, int(round(x1 - w * x_factor)))
        nx2 = min(mask.shape[1], int(round(x2 + w * x_factor)))
        ny1 = max(0, int(round(y1 - h * y_factor)))
        ny2 = min(mask.shape[0], int(round(y2 + h * y_factor)))
        if mode == "rect":
            out[ny1:ny2, nx1:nx2] = 1
        else:
            center = ((nx1 + nx2) // 2, (ny1 + ny2) // 2)
            axes = (max(1, (nx2 - nx1) // 2), max(1, (ny2 - ny1) // 2))
            cv2.ellipse(out, center, axes, 0, 0, 360, 1, -1)
    return out


def shifted(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask.astype(np.uint8), matrix, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_NEAREST)


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


def score(summary: dict[str, Any]) -> float:
    return (
        float(summary["mean_iou"])
        - 0.25 * max(0.0, float(summary["mean_false_positive_ratio_vs_gold"]) - MAX_FALSE_POSITIVE_RATIO_VS_GOLD)
        - 0.25 * max(0.0, float(summary["mean_false_negative_ratio_vs_gold"]) - MAX_FALSE_NEGATIVE_RATIO_VS_GOLD)
    )


Route = Callable[[np.ndarray], np.ndarray]


def make_routes(region: str) -> dict[str, Route]:
    routes: dict[str, Route] = {"identity": lambda mask: mask}
    if region == "mf70_eyes_full":
        for w in (3, 5, 7, 9, 11, 13):
            for h in (1, 3, 5):
                routes[f"anisotropic_dilate_w{w}_h{h}"] = (
                    lambda mask, w=w, h=h: keep_largest(cv2.dilate(mask, kernel(w, h), iterations=1), 2)
                )
        for xf in (0.15, 0.25, 0.35, 0.50, 0.70):
            for yf in (0.05, 0.15, 0.25, 0.40):
                for mode in ("ellipse", "rect"):
                    routes[f"box_{mode}_x{xf}_y{yf}"] = (
                        lambda mask, xf=xf, yf=yf, mode=mode: box_expand(keep_largest(mask, 2), xf, yf, mode)
                    )
        for dx in (-2, 0, 2):
            for dy in (-2, -1, 1, 2):
                routes[f"shift_dx{dx}_dy{dy}_dilate_w7_h3"] = (
                    lambda mask, dx=dx, dy=dy: keep_largest(cv2.dilate(shifted(mask, dx, dy), kernel(7, 3)), 2)
                )
    else:
        for w in (3, 5, 7, 9):
            for h in (1, 3):
                routes[f"anisotropic_dilate_w{w}_h{h}"] = (
                    lambda mask, w=w, h=h: keep_largest(cv2.dilate(mask, kernel(w, h), iterations=1), 2)
                )
                routes[f"anisotropic_open_w{w}_h{h}"] = (
                    lambda mask, w=w, h=h: keep_largest(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel(w, h)), 2)
                )
        for xf in (0.05, 0.10, 0.18, 0.25, 0.35):
            for yf in (0.00, 0.08, 0.15, 0.25):
                for mode in ("ellipse", "rect"):
                    routes[f"box_{mode}_x{xf}_y{yf}"] = (
                        lambda mask, xf=xf, yf=yf, mode=mode: box_expand(keep_largest(mask, 2), xf, yf, mode)
                    )
        for dy in (-3, -2, -1, 1):
            routes[f"shift_dy{dy}_keep_largest_2"] = lambda mask, dy=dy: keep_largest(shifted(mask, 0, dy), 2)
    return routes


def collect_records() -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    celeba_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dataset, path in (("CelebAMask-HQ", celeba_path), ("LaPa", lapa_path)):
        evidence = load_json(path)
        for record in evidence.get("comparison_records", []):
            region = str(record["region"])
            if region in REGIONS:
                item = dict(record)
                item["dataset"] = dataset
                item["sample_key"] = str(record.get("sample_id", record.get("stem", record.get("sample_index"))))
                item["source_evidence"] = rel(path)
                out[region].append(item)
    return out, {"celeba": rel(celeba_path), "lapa": rel(lapa_path)}


def evaluate(records_by_region: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    region_results: list[dict[str, Any]] = []
    best_samples: list[dict[str, Any]] = []
    for region in REGIONS:
        records = records_by_region[region]
        route_records = []
        sample_metrics_by_route: dict[str, list[dict[str, Any]]] = {}
        for route_name, route in make_routes(region).items():
            sample_metrics = []
            for record in records:
                gold = load_mask(str(record["gold_comparison_mask"]))
                pred = load_mask(str(record["pred_comparison_mask"]), gold.shape)
                routed = route(pred).astype(np.uint8)
                sample_metrics.append(
                    {
                        "dataset": record["dataset"],
                        "sample_key": record["sample_key"],
                        "metrics": metrics(gold, routed),
                    }
                )
            summary = summarize([item["metrics"] for item in sample_metrics])
            passed, failed = pass_gate(summary)
            route_records.append(
                {
                    "route": route_name,
                    "summary": summary,
                    "pass_gate": passed,
                    "failed_reasons": failed,
                    "score": round(score(summary), 6),
                }
            )
            sample_metrics_by_route[route_name] = sample_metrics
        route_records.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
        best = route_records[0]
        region_results.append(
            {
                "region": region,
                "sample_count": len(records),
                "best_route": best["route"],
                "best_summary": best["summary"],
                "best_pass_gate": best["pass_gate"],
                "best_failed_reasons": best["failed_reasons"],
                "top_routes": route_records[:10],
                "decision": (
                    "eye_brow_label_geometry_candidate_found_no_promotion"
                    if best["pass_gate"]
                    else "eye_brow_label_geometry_routes_blocked_stronger_route_required"
                ),
            }
        )
        best_samples.extend({"region": region, "best_route": best["route"], **item} for item in sample_metrics_by_route[best["route"]])
    return region_results, best_samples


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
    out = np.zeros((*mask.shape, 3), dtype=np.uint8)
    out[mask > 0] = color
    return Image.fromarray(out)


def error_rgb(gold: np.ndarray, pred: np.ndarray) -> Image.Image:
    out = np.zeros((*gold.shape, 3), dtype=np.uint8) + 22
    out[np.logical_and(gold > 0, pred > 0)] = (245, 245, 245)
    out[np.logical_and(gold == 0, pred > 0)] = (230, 45, 45)
    out[np.logical_and(gold > 0, pred == 0)] = (40, 130, 240)
    return Image.fromarray(out)


def make_panels(records_by_region: dict[str, list[dict[str, Any]]], region_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels = []
    for region_result in region_results:
        region = region_result["region"]
        route_name = region_result["best_route"]
        route = make_routes(region)[route_name]
        records = records_by_region[region]
        chunks = [records[:4], records[4:8], records[8:]]
        for panel_index, chunk in enumerate([item for item in chunks if item], 1):
            cells: list[Image.Image] = []
            for record in chunk:
                gold = load_mask(str(record["gold_comparison_mask"]))
                pred = load_mask(str(record["pred_comparison_mask"]), gold.shape)
                routed = route(pred).astype(np.uint8)
                routed_path = MASK_DIR / f"{region}_{record['dataset']}_{record['sample_key']}_{route_name}.png"
                save_mask(routed, routed_path)
                cells.extend(
                    [
                        tile(mask_rgb(gold, (0, 210, 220)), f"{region} gold", f"{record['dataset']} {record['sample_key']}"),
                        tile(mask_rgb(pred, (255, 210, 0)), "baseline pred", f"IoU {metrics(gold, pred)['iou']}"),
                        tile(mask_rgb(routed, (20, 210, 80)), f"best {route_name}"[:30], f"IoU {metrics(gold, routed)['iou']}"),
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
            panel_path = PANEL_DIR / f"{region}_{route_name}_panel_{panel_index}.png"
            panel.save(panel_path)
            panels.append(
                {
                    "region": region,
                    "best_route": route_name,
                    "panel_index": panel_index,
                    "panel_path": rel(panel_path),
                    "panel_sha256": sha256(panel_path),
                }
            )
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    records_by_region, source_evidence = collect_records()
    region_results, best_samples = evaluate(records_by_region)
    panels = make_panels(records_by_region, region_results)
    candidates = [item["region"] for item in region_results if item["best_pass_gate"]]
    blocked = [item["region"] for item in region_results if not item["best_pass_gate"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_eyes_full and mf70_eyebrows label-aware geometry route evaluation against combined CelebAMask-HQ and LaPa gold masks",
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
        "route_family": "component-wise anisotropic dilation, bbox ellipse/rect expansion, small shifts, and two-component retention for eye/brow labels",
        "region_results": region_results,
        "candidate_regions": candidates,
        "blocked_regions": blocked,
        "best_sample_metrics": best_samples,
        "review_panels": panels,
        "result": (
            "eye_brow_label_geometry_candidates_found_no_promotion"
            if candidates
            else "eye_brow_label_geometry_routes_blocked_stronger_route_required"
        ),
        "next_required_action": (
            "Candidate regions require target-specific source-overlay review only. Blocked regions require stronger landmark/model "
            "geometry or dataset-policy separation before target-portrait proof."
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
                "candidate_regions": candidates,
                "blocked_regions": blocked,
                "region_results": [
                    {
                        "region": item["region"],
                        "best_route": item["best_route"],
                        "best_summary": item["best_summary"],
                        "best_pass_gate": item["best_pass_gate"],
                    }
                    for item in region_results
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
