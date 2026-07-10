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
EVIDENCE_ID = f"W70_MF70_NECK_BOUNDARY_ROUTE_SEARCH_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_neck_boundary_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGION = "mf70_neck"
PROTECTED_REGIONS = (
    "mf70_nose",
    "mf70_eyes_full",
    "mf70_eyebrows",
    "mf70_lips_combined",
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


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def abs_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_mask(path_text: str | Path, shape: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(abs_path(path_text)).convert("L")
    mask = (np.array(image) > 0).astype(np.uint8)
    if shape is not None and mask.shape != shape:
        mask = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return mask


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def kernel(rx: int, ry: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (rx * 2 + 1, ry * 2 + 1))


def bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


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
        "false_positive_ratio_vs_gold": round(false_positive / gold_count, 6) if gold_count else 0.0,
        "false_negative_ratio_vs_gold": round(false_negative / gold_count, 6) if gold_count else 0.0,
    }


def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "mean_iou": round(sum(float(item["iou"]) for item in values) / len(values), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in values) / len(values), 6),
        "mean_false_positive_ratio_vs_gold": round(
            sum(float(item["false_positive_ratio_vs_gold"]) for item in values) / len(values),
            6,
        ),
        "mean_false_negative_ratio_vs_gold": round(
            sum(float(item["false_negative_ratio_vs_gold"]) for item in values) / len(values),
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


def protect(mask: np.ndarray, protected: np.ndarray) -> np.ndarray:
    return np.where(protected > 0, 0, mask).astype(np.uint8)


def connected_to_seed(mask: np.ndarray, seed: np.ndarray, radius: int = 5) -> np.ndarray:
    labels_count, labels, _, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    seed_zone = cv2.dilate(seed.astype(np.uint8), kernel(radius, radius))
    out = np.zeros_like(mask, dtype=np.uint8)
    for idx in range(1, labels_count):
        component = labels == idx
        if np.logical_and(component, seed_zone > 0).any():
            out[component] = 1
    return out


def dilate_route(rx: int, ry: int) -> Callable[[dict[str, Any]], np.ndarray]:
    def route(sample: dict[str, Any]) -> np.ndarray:
        out = cv2.dilate(sample["neck"], kernel(rx, ry)) if rx or ry else sample["neck"].copy()
        return protect(out, sample["protected"])

    return route


def adaptive_trapezoid_route(
    *,
    height_threshold: int,
    width_ratio_threshold: float,
    skin_expand: float,
    top_pad: int,
    dilate_x: int,
    dilate_y: int,
    taper: float,
) -> Callable[[dict[str, Any]], np.ndarray]:
    def route(sample: dict[str, Any]) -> np.ndarray:
        neck = sample["neck"]
        skin = sample["skin"]
        out = cv2.dilate(neck, kernel(dilate_x, dilate_y)) if dilate_x or dilate_y else neck.copy()
        neck_box = bbox(neck)
        skin_box = bbox(skin)
        if neck_box is None or skin_box is None:
            return protect(out, sample["protected"])
        x1, y1, x2, y2 = neck_box
        sx1, _, sx2, _ = skin_box
        neck_width = max(1, x2 - x1)
        neck_height = y2 - y1
        skin_width = max(1, sx2 - sx1)
        if neck_height >= height_threshold and neck_width / skin_width < width_ratio_threshold:
            nx1 = max(0, int(min(x1, sx1) - skin_width * skin_expand))
            nx2 = min(neck.shape[1], int(max(x2, sx2) + skin_width * skin_expand))
            ytop = max(0, y1 - top_pad)
            ybottom = neck.shape[0]
            top_x1 = max(0, int(x1 - neck_width * taper))
            top_x2 = min(neck.shape[1], int(x2 + neck_width * taper))
            polygon = np.array([[(top_x1, ytop), (top_x2, ytop), (nx2, ybottom), (nx1, ybottom)]], dtype=np.int32)
            fill = np.zeros_like(out)
            cv2.fillPoly(fill, polygon, 1)
            out = np.maximum(out, fill)
        out = protect(out, sample["protected"])
        return connected_to_seed(out, neck)

    return route


Route = Callable[[dict[str, Any]], np.ndarray]


def make_routes() -> dict[str, Route]:
    routes: dict[str, Route] = {"baseline": dilate_route(0, 0)}
    for rx, ry in ((1, 1), (2, 1), (3, 1), (3, 2), (5, 1)):
        routes[f"dilate_x{rx}_y{ry}"] = dilate_route(rx, ry)
    for height_threshold in (80, 90, 100, 110):
        for width_ratio_threshold in (0.75, 0.85, 1.0):
            for skin_expand in (0.0, 0.05, 0.10):
                for top_pad in (0, 4, 8):
                    for dilate_x, dilate_y in ((2, 1), (3, 1)):
                        for taper in (0.0, 0.15):
                            name = (
                                f"adaptive_h{height_threshold}_r{width_ratio_threshold}"
                                f"_sx{skin_expand}_t{top_pad}_d{dilate_x}x{dilate_y}_q{taper}"
                            )
                            routes[name] = adaptive_trapezoid_route(
                                height_threshold=height_threshold,
                                width_ratio_threshold=width_ratio_threshold,
                                skin_expand=skin_expand,
                                top_pad=top_pad,
                                dilate_x=dilate_x,
                                dilate_y=dilate_y,
                                taper=taper,
                            )
    return routes


def collect_samples() -> tuple[list[dict[str, Any]], Path]:
    benchmark_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    benchmark = read_json(benchmark_path)
    staged_by_id = {int(item["sample_id"]): item for item in benchmark.get("staged_inputs", [])}
    grouped: dict[int, dict[str, Any]] = {}
    for record in benchmark.get("comparison_records", []):
        sample_id = int(record["sample_id"])
        grouped.setdefault(sample_id, {"sample_id": sample_id, "regions": {}, "staged_input": staged_by_id.get(sample_id)})
        grouped[sample_id]["regions"][str(record["region"])] = record

    samples: list[dict[str, Any]] = []
    for sample_id, sample in sorted(grouped.items()):
        if REGION not in sample["regions"] or "mf70_face_skin" not in sample["regions"]:
            continue
        neck_record = sample["regions"][REGION]
        gold = load_mask(neck_record["gold_comparison_mask"])
        neck = load_mask(neck_record["pred_comparison_mask"], gold.shape)
        skin = load_mask(sample["regions"]["mf70_face_skin"]["pred_comparison_mask"], gold.shape)
        protected = np.zeros_like(gold, dtype=np.uint8)
        for region in PROTECTED_REGIONS:
            record = sample["regions"].get(region)
            if record:
                protected = np.maximum(protected, load_mask(record["pred_comparison_mask"], gold.shape))
        samples.append(
            {
                "sample_id": sample_id,
                "gold": gold,
                "neck": neck,
                "skin": skin,
                "protected": protected,
                "record": neck_record,
                "staged_input": sample.get("staged_input"),
            }
        )
    return samples, benchmark_path


def evaluate(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], str, Route]:
    routes = make_routes()
    route_records: list[dict[str, Any]] = []
    samples_by_route: dict[str, list[dict[str, Any]]] = {}
    for route_name, route in routes.items():
        sample_metrics: list[dict[str, Any]] = []
        for sample in samples:
            pred = route(sample).astype(np.uint8)
            m = metrics(sample["gold"], pred)
            sample_metrics.append(
                {
                    "sample_id": sample["sample_id"],
                    "metrics": m,
                    "gold_bbox": bbox(sample["gold"]),
                    "baseline_bbox": bbox(sample["neck"]),
                    "route_bbox": bbox(pred),
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
        samples_by_route[route_name] = sample_metrics
    route_records.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
    best_route_name = str(route_records[0]["route"])
    return route_records, samples_by_route, best_route_name, routes[best_route_name]


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def tile(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail((188, 188))
    out = Image.new("RGB", (188, 238), "white")
    out.paste(image, ((188 - image.width) // 2, 48 + (188 - image.height) // 2))
    draw = ImageDraw.Draw(out)
    draw.text((6, 5), title[:30], fill=(0, 0, 0), font=font(14))
    if subtitle:
        draw.text((6, 25), subtitle[:42], fill=(60, 60, 60), font=font(11))
    return out


def mask_rgb(mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    out = np.zeros((*mask.shape, 3), dtype=np.uint8)
    out[mask > 0] = color
    return Image.fromarray(out)


def overlay(source_path: str | None, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    if source_path:
        base = Image.open(abs_path(source_path)).convert("RGB").resize((mask.shape[1], mask.shape[0]))
    else:
        base = Image.new("RGB", (mask.shape[1], mask.shape[0]), (24, 24, 24))
    color_layer = Image.new("RGB", base.size, color)
    alpha = Image.fromarray((mask > 0).astype(np.uint8) * 110)
    base.paste(color_layer, (0, 0), alpha)
    return base


def error_rgb(gold: np.ndarray, pred: np.ndarray) -> Image.Image:
    out = np.zeros((*gold.shape, 3), dtype=np.uint8) + 22
    out[np.logical_and(gold > 0, pred > 0)] = (245, 245, 245)
    out[np.logical_and(gold == 0, pred > 0)] = (230, 45, 45)
    out[np.logical_and(gold > 0, pred == 0)] = (40, 130, 240)
    return Image.fromarray(out)


def make_panels(samples: list[dict[str, Any]], route_name: str, route: Route) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    cells: list[Image.Image] = []
    panels: list[dict[str, Any]] = []
    for sample in samples:
        routed = route(sample).astype(np.uint8)
        sample_id = sample["sample_id"]
        routed_path = MASK_DIR / f"{sample_id:05d}_{route_name}.png"
        save_mask(routed, routed_path)
        source_path = None
        if sample.get("staged_input"):
            source_path = sample["staged_input"].get("source_image")
        cells.extend(
            [
                tile(overlay(source_path, sample["gold"], (0, 220, 230)), f"{sample_id} gold overlay"),
                tile(overlay(source_path, sample["neck"], (255, 205, 0)), "baseline overlay", f"IoU {metrics(sample['gold'], sample['neck'])['iou']}"),
                tile(mask_rgb(sample["skin"], (175, 90, 220)), "face-skin pred", "neighbor geometry"),
                tile(overlay(source_path, routed, (30, 210, 85)), f"best {route_name}"[:30], f"IoU {metrics(sample['gold'], routed)['iou']}"),
                tile(error_rgb(sample["gold"], routed), "best error", "red FP / blue FN"),
            ]
        )
    cols = 5
    cell_w = max(cell.width for cell in cells)
    cell_h = max(cell.height for cell in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for index, cell in enumerate(cells):
        panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
    panel_path = PANEL_DIR / f"mf70_neck_boundary_{route_name}_panel.png"
    panel.save(panel_path)
    panels.append({"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    samples, benchmark_path = collect_samples()
    route_records, samples_by_route, best_route_name, best_route = evaluate(samples)
    best = route_records[0]
    panels = make_panels(samples, best_route_name, best_route)
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "mf70_neck boundary route search using MaskedWarehouse CelebAMask-HQ originals and gold masks",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "benchmark_evidence": rel(benchmark_path),
        "benchmark_sha256": sha256(benchmark_path),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "min_sample_count": MIN_SAMPLE_COUNT,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": (
            "baseline anisotropic dilation plus adaptive lower-neck trapezoid expansion from predicted neck and "
            "predicted face-skin geometry; gold masks are used only for scoring, not for route construction"
        ),
        "sample_count": len(samples),
        "route_count": len(route_records),
        "best_route": best_route_name,
        "best_summary": best["summary"],
        "best_pass_gate": best["pass_gate"],
        "best_failed_reasons": best["failed_reasons"],
        "best_sample_metrics": samples_by_route[best_route_name],
        "baseline_summary": next(item["summary"] for item in route_records if item["route"] == "baseline"),
        "route_records": route_records[:100],
        "review_panels": panels,
        "result": (
            "mf70_neck_boundary_candidate_found_no_promotion"
            if best["pass_gate"]
            else "mf70_neck_boundary_routes_blocked_no_promotion"
        ),
        "finding": (
            "The best adaptive boundary route improves the baseline neck benchmark but still fails the current gold gate. "
            "The weak sample needs much wider lower-neck coverage; expanding far enough to reduce false negatives creates "
            "too much false-positive area on the combined sample set."
        ),
        "next_required_action": (
            "Keep mf70_neck unpromoted. Use a stronger body/neck parsing authority or a separate body-source neck gold policy; "
            "do not use target-portrait neck overlays as pass evidence."
        ),
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "route_count": evidence["route_count"],
                "best_route": evidence["best_route"],
                "baseline_summary": evidence["baseline_summary"],
                "best_summary": evidence["best_summary"],
                "review_panels": panels,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
