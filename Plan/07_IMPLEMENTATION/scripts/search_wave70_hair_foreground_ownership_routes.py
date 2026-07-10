#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
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
EVIDENCE_ID = f"W70_MF70_HAIR_FOREGROUND_OWNERSHIP_ROUTE_SEARCH_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_hair_foreground_ownership_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGION = "mf70_hair"
ANCHOR_REGIONS = (
    "mf70_face_skin",
    "mf70_nose",
    "mf70_eyes_full",
    "mf70_eyebrows",
    "mf70_lips_top",
    "mf70_lips_bottom",
    "mf70_teeth_mouth_area",
)

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


def load_mask(path_text: str | None, shape: tuple[int, int] | None = None) -> np.ndarray:
    if not path_text:
        if shape is None:
            raise ValueError("shape required for empty mask")
        return np.zeros(shape, dtype=np.uint8)
    image = Image.open(abs_path(path_text)).convert("L")
    mask = (np.array(image) > 0).astype(np.uint8)
    if shape is not None and mask.shape != shape:
        mask = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return mask


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


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
        "false_positive_ratio_vs_pred": round(false_positive / pred_count, 6) if pred_count else None,
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
        - 0.20 * max(0.0, float(summary["mean_false_negative_ratio_vs_gold"]) - MAX_FALSE_NEGATIVE_RATIO_VS_GOLD)
    )


def bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def largest_component(mask: np.ndarray) -> np.ndarray:
    labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    largest = max(range(1, labels_count), key=lambda idx: stats[idx, cv2.CC_STAT_AREA])
    return (labels == largest).astype(np.uint8)


def bbox_window(mask: np.ndarray, expand_x: float, expand_top: float, expand_bottom: float) -> np.ndarray:
    box = bbox(largest_component(mask))
    out = np.zeros_like(mask, dtype=np.uint8)
    if box is None:
        return out
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    nx1 = max(0, int(round(x1 - width * expand_x)))
    nx2 = min(mask.shape[1], int(round(x2 + width * expand_x)))
    ny1 = max(0, int(round(y1 - height * expand_top)))
    ny2 = min(mask.shape[0], int(round(y2 + height * expand_bottom)))
    out[ny1:ny2, nx1:nx2] = 1
    return out


def component_filter(
    hair: np.ndarray,
    anchor: np.ndarray,
    *,
    contact_radius: int,
    min_contact_ratio: float,
    max_anchor_distance_ratio: float,
    max_border_touch_ratio: float | None,
    window: np.ndarray | None = None,
    split_radius: int = 0,
) -> np.ndarray:
    source = hair.astype(np.uint8)
    if split_radius > 0:
        eroded = cv2.erode(source, kernel(split_radius))
        labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(eroded, 8)
        if labels_count > 1:
            split = np.zeros_like(source)
            for idx in range(1, labels_count):
                comp_seed = labels == idx
                grown = cv2.dilate(comp_seed.astype(np.uint8), kernel(split_radius))
                split[np.logical_and(grown > 0, source > 0)] = idx
            source = (split > 0).astype(np.uint8)

    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(source, 8)
    if labels_count <= 1:
        return source if window is None else (source & window)

    anchor_owner = largest_component(anchor)
    owner_box = bbox(anchor_owner)
    if owner_box is None:
        return np.zeros_like(source, dtype=np.uint8)
    ax1, ay1, ax2, ay2 = owner_box
    owner_w = max(1, ax2 - ax1)
    owner_h = max(1, ay2 - ay1)
    anchor_zone = cv2.dilate(anchor_owner, kernel(contact_radius))
    out = np.zeros_like(source, dtype=np.uint8)

    for idx in range(1, labels_count):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area <= 0:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        cx, cy = centroids[idx]
        component = labels == idx
        if window is not None and not np.logical_and(component, window > 0).any():
            continue
        contact = int(np.logical_and(component, anchor_zone > 0).sum())
        contact_ratio = contact / area
        dx = max(ax1 - cx, 0, cx - ax2) / owner_w
        dy = max(ay1 - cy, 0, cy - ay2) / owner_h
        distance_ratio = (dx * dx + dy * dy) ** 0.5
        border_pixels = 0
        if x == 0:
            border_pixels += h
        if y == 0:
            border_pixels += w
        if x + w >= source.shape[1]:
            border_pixels += h
        if y + h >= source.shape[0]:
            border_pixels += w
        border_touch_ratio = border_pixels / max(1, area)
        if contact_ratio < min_contact_ratio:
            continue
        if distance_ratio > max_anchor_distance_ratio:
            continue
        if max_border_touch_ratio is not None and border_touch_ratio > max_border_touch_ratio and contact_ratio < 0.02:
            continue
        out[component] = 1
    return out if window is None else (out & window)


def collect_records() -> tuple[list[dict[str, Any]], dict[str, str]]:
    celeba_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    source_evidence = {"celeba": rel(celeba_path), "lapa": rel(lapa_path)}
    for dataset, path in (("CelebAMask-HQ", celeba_path), ("LaPa", lapa_path)):
        evidence = load_json(path)
        for record in evidence.get("comparison_records", []):
            sample_key = str(record.get("sample_id", record.get("stem", record.get("sample_index"))))
            key = (dataset, sample_key)
            grouped.setdefault(key, {"dataset": dataset, "sample_key": sample_key, "regions": {}, "source_evidence": rel(path)})
            grouped[key]["regions"][str(record["region"])] = record
    return [sample for sample in grouped.values() if REGION in sample["regions"]], source_evidence


def anchor_mask(sample: dict[str, Any], shape: tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=np.uint8)
    for region in ANCHOR_REGIONS:
        record = sample["regions"].get(region)
        if record:
            out = np.maximum(out, load_mask(str(record["pred_comparison_mask"]), shape))
    return out


Route = Callable[[np.ndarray, np.ndarray], np.ndarray]


def make_routes() -> dict[str, Route]:
    routes: dict[str, Route] = {}
    for expand_x in (0.35, 0.45, 0.55):
        for expand_top in (0.45, 0.6, 0.85):
            for expand_bottom in (0.25, 0.45):
                for contact_radius in (8, 16, 32):
                    for contact_ratio in (0.0, 0.005, 0.02):
                        for distance_ratio in (1.1, 1.6, 2.1):
                            name = (
                                f"owner_x{expand_x}_t{expand_top}_b{expand_bottom}"
                                f"_r{contact_radius}_c{contact_ratio}_d{distance_ratio}"
                            )
                            routes[name] = (
                                lambda hair, anchor, expand_x=expand_x, expand_top=expand_top,
                                expand_bottom=expand_bottom, contact_radius=contact_radius,
                                contact_ratio=contact_ratio, distance_ratio=distance_ratio:
                                component_filter(
                                    hair,
                                    anchor,
                                    contact_radius=contact_radius,
                                    min_contact_ratio=contact_ratio,
                                    max_anchor_distance_ratio=distance_ratio,
                                    max_border_touch_ratio=0.01,
                                    window=bbox_window(anchor, expand_x, expand_top, expand_bottom),
                                )
                            )
    for split_radius in (2, 4):
        for contact_radius in (8, 16):
            for contact_ratio in (0.005, 0.02):
                name = f"erode_split{split_radius}_owner_r{contact_radius}_c{contact_ratio}"
                routes[name] = (
                    lambda hair, anchor, split_radius=split_radius, contact_radius=contact_radius, contact_ratio=contact_ratio:
                    component_filter(
                        hair,
                        anchor,
                        contact_radius=contact_radius,
                        min_contact_ratio=contact_ratio,
                        max_anchor_distance_ratio=1.8,
                        max_border_touch_ratio=0.01,
                        split_radius=split_radius,
                    )
                )
    return routes


def prepare_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for sample in samples:
        hair_record = sample["regions"][REGION]
        gold = load_mask(str(hair_record["gold_comparison_mask"]))
        hair = load_mask(str(hair_record["pred_comparison_mask"]), gold.shape)
        anchor = anchor_mask(sample, gold.shape)
        prepared.append(
            {
                "dataset": sample["dataset"],
                "sample_key": sample["sample_key"],
                "gold": gold,
                "hair": hair,
                "anchor": anchor,
            }
        )
    return prepared


def evaluate(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Route]:
    routes = make_routes()
    prepared_samples = prepare_samples(samples)
    route_records: list[dict[str, Any]] = []
    sample_metrics_by_route: dict[str, list[dict[str, Any]]] = {}
    for route_name, route in routes.items():
        sample_metrics: list[dict[str, Any]] = []
        for sample in prepared_samples:
            gold = sample["gold"]
            hair = sample["hair"]
            anchor = sample["anchor"]
            routed = route(hair, anchor).astype(np.uint8)
            m = metrics(gold, routed)
            sample_metrics.append({"dataset": sample["dataset"], "sample_key": sample["sample_key"], "metrics": m})
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
    best_route_name = str(route_records[0]["route"])
    return route_records, sample_metrics_by_route[best_route_name], make_panels(samples, best_route_name, routes[best_route_name]), routes[best_route_name]


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


def make_panels(samples: list[dict[str, Any]], best_route: str, route: Route) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []
    chunks = [samples[:4], samples[4:8], samples[8:]]
    for panel_index, chunk in enumerate([item for item in chunks if item]):
        cells: list[Image.Image] = []
        for sample in chunk:
            hair_record = sample["regions"][REGION]
            gold = load_mask(str(hair_record["gold_comparison_mask"]))
            hair = load_mask(str(hair_record["pred_comparison_mask"]), gold.shape)
            anchor = anchor_mask(sample, gold.shape)
            routed = route(hair, anchor).astype(np.uint8)
            routed_path = MASK_DIR / f"{sample['dataset']}_{sample['sample_key']}_{best_route}.png"
            save_mask(routed, routed_path)
            cells.extend(
                [
                    tile(mask_rgb(gold, (0, 210, 220)), "hair gold", f"{sample['dataset']} {sample['sample_key']}"),
                    tile(mask_rgb(hair, (255, 210, 0)), "baseline hair", f"IoU {metrics(gold, hair)['iou']}"),
                    tile(mask_rgb(largest_component(anchor), (210, 90, 255)), "primary anchor", "face/feature owner"),
                    tile(mask_rgb(routed, (20, 210, 80)), f"best {best_route}"[:30], f"IoU {metrics(gold, routed)['iou']}"),
                    tile(error_rgb(gold, routed), "best error", "red FP / blue FN"),
                ]
            )
        cols = 5
        cell_w = max(cell.width for cell in cells)
        cell_h = max(cell.height for cell in cells)
        rows = (len(cells) + cols - 1) // cols
        panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
        for index, cell in enumerate(cells):
            panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
        panel_path = PANEL_DIR / f"mf70_hair_foreground_ownership_{best_route}_panel_{panel_index + 1}.png"
        panel.save(panel_path)
        panels.append({"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path), "panel_index": panel_index + 1})
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    samples, source_evidence = collect_records()
    route_records, best_sample_metrics, panels, _ = evaluate(samples)
    best = route_records[0]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "mf70_hair foreground ownership route search using MaskedWarehouse CelebAMask-HQ and LaPa originals/gold masks",
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
        "route_family": (
            "foreground owner component filters with face/feature anchor contact, anchor-distance limits, "
            "border-touch suppression, anchor windows, and erode-split component recovery"
        ),
        "sample_count": len(samples),
        "route_count": len(route_records),
        "route_records": route_records[:100],
        "best_route": best["route"],
        "best_summary": best["summary"],
        "best_pass_gate": best["pass_gate"],
        "best_failed_reasons": best["failed_reasons"],
        "best_sample_metrics": best_sample_metrics,
        "review_panels": panels,
        "result": (
            "mf70_hair_foreground_ownership_candidate_found_no_promotion"
            if best["pass_gate"]
            else "mf70_hair_foreground_ownership_routes_blocked_no_promotion"
        ),
        "next_required_action": (
            "If candidate found, run strict target-source overlay review only after gold-backed review. "
            "If blocked, switch to stronger person-instance/foreground segmentation authority or explicit hair-row policy."
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
                "route_count": evidence["route_count"],
                "best_route": evidence["best_route"],
                "best_summary": evidence["best_summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
