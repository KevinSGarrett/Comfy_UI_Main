#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
SAM2_CONFIG = "configs/sam2.1/sam2.1_hiera_t.yaml"
SAM2_CHECKPOINT = Path(r"C:\Comfy_UI_Lora\OpenPose\models\sam2\sam2.1_hiera_tiny.pt")
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_SAM2_HAIR_PROMPTABILITY_PROBE_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_sam2_hair_promptability" / RUN_STAMP
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
SELECTED_SAMPLE_KEYS = {
    ("CelebAMask-HQ", "0"),
    ("CelebAMask-HQ", "18000"),
    ("CelebAMask-HQ", "1"),
    ("LaPa", "10004916254_0"),
    ("LaPa", "10012551673_2"),
    ("LaPa", "10023147796_0"),
}

MIN_MEAN_IOU = 0.85
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


def load_image(path: Path, shape: tuple[int, int]) -> np.ndarray:
    image = Image.open(path).convert("RGB").resize((shape[1], shape[0]), Image.Resampling.LANCZOS)
    return np.array(image)


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def bbox(mask: np.ndarray, pad: int = 0) -> np.ndarray | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    x1 = max(0, int(xs.min()) - pad)
    y1 = max(0, int(ys.min()) - pad)
    x2 = min(mask.shape[1] - 1, int(xs.max()) + pad)
    y2 = min(mask.shape[0] - 1, int(ys.max()) + pad)
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def center_points(mask: np.ndarray, max_points: int = 5) -> np.ndarray:
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    points: list[list[float]] = []
    component_ids = sorted(
        range(1, labels_count),
        key=lambda idx: int(stats[idx, cv2.CC_STAT_AREA]),
        reverse=True,
    )[:max_points]
    for idx in component_ids:
        cx, cy = centroids[idx]
        points.append([float(cx), float(cy)])
    return np.array(points, dtype=np.float32)


def anchor_negative_points(anchor: np.ndarray, max_points: int = 3) -> np.ndarray:
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(anchor.astype(np.uint8), 8)
    if labels_count <= 1:
        return np.zeros((0, 2), dtype=np.float32)
    component_ids = sorted(
        range(1, labels_count),
        key=lambda idx: int(stats[idx, cv2.CC_STAT_AREA]),
        reverse=True,
    )[:max_points]
    return np.array([[float(centroids[idx][0]), float(centroids[idx][1])] for idx in component_ids], dtype=np.float32)


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


def original_path(dataset: str, sample_key: str, split: str | None) -> Path:
    if dataset == "CelebAMask-HQ":
        return PROJECT_ROOT / "MaskedWarehouse" / "CelebAMask-HQ" / "CelebA-HQ-img" / f"{sample_key}.jpg"
    if dataset == "LaPa":
        return PROJECT_ROOT / "MaskedWarehouse" / "LaPa" / str(split or "val") / "images" / f"{sample_key}.jpg"
    raise ValueError(dataset)


def collect_samples() -> tuple[list[dict[str, Any]], dict[str, str]]:
    celeba_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    source_evidence = {"celeba": rel(celeba_path), "lapa": rel(lapa_path)}
    for dataset, path in (("CelebAMask-HQ", celeba_path), ("LaPa", lapa_path)):
        evidence = load_json(path)
        for record in evidence.get("comparison_records", []):
            sample_key = str(record.get("sample_id", record.get("stem", record.get("sample_index"))))
            key = (dataset, sample_key)
            grouped.setdefault(
                key,
                {
                    "dataset": dataset,
                    "sample_key": sample_key,
                    "split": record.get("split"),
                    "regions": {},
                    "source_evidence": rel(path),
                },
            )
            grouped[key]["regions"][str(record["region"])] = record
    samples = [
        sample
        for key, sample in grouped.items()
        if key in SELECTED_SAMPLE_KEYS and REGION in sample["regions"]
    ]
    samples.sort(key=lambda item: (item["dataset"], item["sample_key"]))
    return samples, source_evidence


def anchor_mask(sample: dict[str, Any], shape: tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=np.uint8)
    for region in ANCHOR_REGIONS:
        record = sample["regions"].get(region)
        if record:
            out = np.maximum(out, load_mask(str(record["pred_comparison_mask"]), shape))
    return out


def sam_predict_variants(
    predictor: SAM2ImagePredictor,
    image: np.ndarray,
    gold: np.ndarray,
    hair_pred: np.ndarray,
    anchor: np.ndarray,
) -> dict[str, np.ndarray]:
    predictor.set_image(image)
    box = bbox(hair_pred, pad=6)
    if box is None:
        return {
            "baseline_pred": hair_pred,
            "sam2_pred_bbox_score_best": np.zeros_like(hair_pred),
            "sam2_pred_bbox_oracle_best": np.zeros_like(hair_pred),
            "sam2_pred_bbox_points_score_best": np.zeros_like(hair_pred),
            "sam2_pred_bbox_points_oracle_best": np.zeros_like(hair_pred),
        }
    masks, scores, _ = predictor.predict(box=box, multimask_output=True, return_logits=False)
    binary_masks = [(mask > 0).astype(np.uint8) for mask in masks]
    score_best = binary_masks[int(np.argmax(scores))]
    oracle_best = max(binary_masks, key=lambda mask: metrics(gold, mask)["iou"])

    pos = center_points(hair_pred)
    neg = anchor_negative_points(anchor)
    if len(pos) and len(neg):
        point_coords = np.concatenate([pos, neg], axis=0)
        point_labels = np.concatenate(
            [np.ones((len(pos),), dtype=np.int32), np.zeros((len(neg),), dtype=np.int32)],
            axis=0,
        )
    elif len(pos):
        point_coords = pos
        point_labels = np.ones((len(pos),), dtype=np.int32)
    else:
        point_coords = None
        point_labels = None
    if point_coords is None:
        point_score_best = score_best
        point_oracle_best = oracle_best
    else:
        point_masks, point_scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=box,
            multimask_output=True,
            return_logits=False,
        )
        point_binary_masks = [(mask > 0).astype(np.uint8) for mask in point_masks]
        point_score_best = point_binary_masks[int(np.argmax(point_scores))]
        point_oracle_best = max(point_binary_masks, key=lambda mask: metrics(gold, mask)["iou"])
    return {
        "baseline_pred": hair_pred,
        "sam2_pred_bbox_score_best": score_best,
        "sam2_pred_bbox_oracle_best": oracle_best,
        "sam2_pred_bbox_points_score_best": point_score_best,
        "sam2_pred_bbox_points_oracle_best": point_oracle_best,
    }


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


def save_panel(cells: list[Image.Image], panel_path: Path) -> dict[str, Any]:
    cols = 5
    cell_w = max(cell.width for cell in cells)
    cell_h = max(cell.height for cell in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for index, cell in enumerate(cells):
        panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
    panel.save(panel_path)
    return {"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)}


def make_panel(sample_panels: list[dict[str, Any]], best_route: str) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []
    chunks = [sample_panels[:3], sample_panels[3:]]
    for panel_index, chunk in enumerate([chunk for chunk in chunks if chunk]):
        cells: list[Image.Image] = []
        for item in chunk:
            cells.extend(
                [
                    tile(Image.fromarray(item["image"]), "original", f"{item['dataset']} {item['sample_key']}"),
                    tile(mask_rgb(item["gold"], (0, 210, 220)), "gold hair", ""),
                    tile(mask_rgb(item["baseline_pred"], (255, 210, 0)), "baseline pred", f"IoU {item['metrics']['baseline_pred']['iou']}"),
                    tile(mask_rgb(item[best_route], (20, 210, 80)), f"best {best_route}"[:30], f"IoU {item['metrics'][best_route]['iou']}"),
                    tile(error_rgb(item["gold"], item[best_route]), "best error", "red FP / blue FN"),
                ]
            )
        panel_path = PANEL_DIR / f"sam2_hair_promptability_{best_route}_panel_{panel_index + 1}.png"
        panel_record = save_panel(cells, panel_path)
        panel_record["panel_index"] = panel_index + 1
        panel_record["panel_type"] = "best_route"
        panels.append(panel_record)

    comparison_routes = [
        "baseline_pred",
        "sam2_pred_bbox_score_best",
        "sam2_pred_bbox_points_score_best",
        "sam2_pred_bbox_oracle_best",
        "sam2_pred_bbox_points_oracle_best",
    ]
    for panel_index, chunk in enumerate([chunk for chunk in chunks if chunk]):
        cells = []
        for item in chunk:
            cells.append(tile(Image.fromarray(item["image"]), "original", f"{item['dataset']} {item['sample_key']}"))
            cells.append(tile(mask_rgb(item["gold"], (0, 210, 220)), "gold hair", ""))
            for route in comparison_routes:
                cells.append(tile(mask_rgb(item[route], (20, 210, 80)), route[:30], f"IoU {item['metrics'][route]['iou']}"))
        panel_path = PANEL_DIR / f"sam2_hair_promptability_route_compare_panel_{panel_index + 1}.png"
        panel_record = save_panel(cells, panel_path)
        panel_record["panel_index"] = panel_index + 1
        panel_record["panel_type"] = "route_comparison"
        panels.append(panel_record)
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    samples, source_evidence = collect_samples()
    missing_originals = []
    for sample in samples:
        path = original_path(sample["dataset"], sample["sample_key"], sample.get("split"))
        if not path.exists():
            missing_originals.append(str(path))
    if missing_originals:
        raise FileNotFoundError(missing_originals)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sam_model = build_sam2(SAM2_CONFIG, str(SAM2_CHECKPOINT), device=device)
    predictor = SAM2ImagePredictor(sam_model)

    route_metrics: dict[str, list[dict[str, Any]]] = {}
    sample_results: list[dict[str, Any]] = []
    panel_inputs: list[dict[str, Any]] = []
    for sample in samples:
        hair_record = sample["regions"][REGION]
        gold = load_mask(str(hair_record["gold_comparison_mask"]))
        baseline = load_mask(str(hair_record["pred_comparison_mask"]), gold.shape)
        anchor = anchor_mask(sample, gold.shape)
        image_path = original_path(sample["dataset"], sample["sample_key"], sample.get("split"))
        image = load_image(image_path, gold.shape)
        variants = sam_predict_variants(predictor, image, gold, baseline, anchor)
        sample_metric_record: dict[str, Any] = {}
        for route, mask in variants.items():
            route_path = MASK_DIR / f"{sample['dataset']}_{sample['sample_key']}_{route}.png"
            save_mask(mask, route_path)
            m = metrics(gold, mask)
            route_metrics.setdefault(route, []).append(m)
            sample_metric_record[route] = {
                "metrics": m,
                "mask_path": rel(route_path),
            }
        sample_results.append(
            {
                "dataset": sample["dataset"],
                "sample_key": sample["sample_key"],
                "split": sample.get("split"),
                "image_path": rel(image_path),
                "metrics_by_route": sample_metric_record,
            }
        )
        panel_item = {
            "dataset": sample["dataset"],
            "sample_key": sample["sample_key"],
            "image": image,
            "gold": gold,
            "metrics": {route: item["metrics"] for route, item in sample_metric_record.items()},
        }
        panel_item.update(variants)
        panel_inputs.append(panel_item)

    route_records: list[dict[str, Any]] = []
    for route, values in route_metrics.items():
        summary = summarize(values)
        passed, failed = pass_gate(summary)
        route_records.append(
            {
                "route": route,
                "summary": summary,
                "pass_gate": passed,
                "failed_reasons": failed,
                "score": round(score(summary), 6),
                "diagnostic_oracle_route": route.endswith("_oracle_best"),
            }
        )
    route_records.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
    best = route_records[0]
    panels = make_panel(panel_inputs, str(best["route"]))
    result = (
        "sam2_hair_promptability_probe_candidate_found_no_promotion"
        if best["pass_gate"] and not best["diagnostic_oracle_route"]
        else "sam2_hair_promptability_probe_no_promotable_candidate"
    )
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "bounded SAM2 hair promptability probe against MaskedWarehouse gold original images and hair masks",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "device": device,
        "sam2_config": SAM2_CONFIG,
        "sam2_checkpoint": str(SAM2_CHECKPOINT),
        "source_evidence": source_evidence,
        "selected_sample_keys": sorted([f"{dataset}:{sample}" for dataset, sample in SELECTED_SAMPLE_KEYS]),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": (
            "SAM2 tiny image predictor with automatic baseline-hair bounding boxes, optional positive hair points, "
            "negative face/feature anchor points, score-selected masks, and diagnostic-only oracle mask selection"
        ),
        "sample_count": len(samples),
        "route_records": route_records,
        "best_route": best["route"],
        "best_summary": best["summary"],
        "best_pass_gate": best["pass_gate"],
        "best_failed_reasons": best["failed_reasons"],
        "best_is_diagnostic_oracle": best["diagnostic_oracle_route"],
        "sample_results": sample_results,
        "review_panels": panels,
        "result": result,
        "next_required_action": (
            "If no promotable score-selected candidate exists, do not promote SAM2 hair masks. "
            "Either design a non-oracle automatic SAM2 prompt policy with stronger owner prompts, write a hair-row policy, "
            "or switch to another local gold-backed blocked row."
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
                "result": result,
                "device": device,
                "best_route": evidence["best_route"],
                "best_summary": evidence["best_summary"],
                "best_is_diagnostic_oracle": evidence["best_is_diagnostic_oracle"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
