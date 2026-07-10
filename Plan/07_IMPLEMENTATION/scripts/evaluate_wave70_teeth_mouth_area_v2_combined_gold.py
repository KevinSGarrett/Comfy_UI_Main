from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MF70_TEETH_MOUTH_AREA_V2_COMBINED_GOLD_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_teeth_mouth_area_v2_combined_gold" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGION = "mf70_teeth_mouth_area"
MIN_MEAN_IOU = 0.85
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15
MIN_SAMPLE_COUNT = 3


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
    matches = sorted(QA_DIR.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def abs_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_mask(path_text: str) -> np.ndarray:
    return (np.array(Image.open(abs_path(path_text)).convert("L")) > 0).astype(np.uint8)


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def route_v2(mask: np.ndarray) -> np.ndarray:
    eroded = cv2.erode(mask.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 3)))
    routed = cv2.dilate(eroded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 7)))
    return (routed > 0).astype(np.uint8)


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


def gate(summary: dict[str, Any]) -> tuple[bool, list[str]]:
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


def collect_records() -> tuple[list[dict[str, Any]], dict[str, str]]:
    sources = {
        "celeba": latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json"),
        "lapa": latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json"),
    }
    records: list[dict[str, Any]] = []
    for dataset, path in (("CelebAMask-HQ", sources["celeba"]), ("LaPa", sources["lapa"])):
        payload = load_json(path)
        for record in payload.get("comparison_records", []):
            if record.get("region") != REGION:
                continue
            item = dict(record)
            item["dataset"] = dataset
            item["source_evidence"] = rel(path)
            records.append(item)
    return records, {key: rel(path) for key, path in sources.items()}


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


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


def make_panel(rows: list[dict[str, Any]]) -> dict[str, Any]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    cells: list[Image.Image] = []
    for row in rows[:8]:
        gold = row["gold"]
        pred = row["baseline"]
        routed = row["routed"]
        base_metrics = metrics(gold, pred)
        route_metrics = row["metrics"]
        cells.extend(
            [
                tile(mask_rgb(gold, (0, 210, 220)), "gold", str(row["dataset"])),
                tile(mask_rgb(pred, (255, 210, 0)), "baseline pred", f"IoU {base_metrics['iou']}"),
                tile(mask_rgb(routed, (20, 210, 80)), "v2 erode/dilate", f"IoU {route_metrics['iou']}"),
                tile(error_rgb(gold, routed), "v2 error", "red FP / blue FN"),
            ]
        )
    cols = 4
    cell_w = 190
    cell_h = 238
    panel = Image.new("RGB", (cols * cell_w, ((len(cells) + cols - 1) // cols) * cell_h), "white")
    for index, cell in enumerate(cells):
        panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
    panel_path = PANEL_DIR / f"{REGION}_v2_combined_gold_panel.png"
    panel.save(panel_path)
    return {"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)}


def sample_key(record: dict[str, Any]) -> str:
    return str(record.get("sample_id", record.get("stem", record.get("sample_index", "sample"))))


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)

    records, source_evidence = collect_records()
    if not records:
        raise RuntimeError(f"No combined gold records found for {REGION}")

    rows: list[dict[str, Any]] = []
    by_dataset_metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        gold = load_mask(str(record["gold_comparison_mask"]))
        baseline = load_mask(str(record["pred_comparison_mask"]))
        routed = route_v2(baseline)
        metric = metrics(gold, routed)
        key = sample_key(record)
        mask_path = MASK_DIR / f"{record['dataset']}_{key}_{REGION}_v2.png"
        save_mask(routed, mask_path)
        row = {
            "dataset": record["dataset"],
            "sample_key": key,
            "source_evidence": record["source_evidence"],
            "gold_comparison_mask": record["gold_comparison_mask"],
            "pred_comparison_mask": record["pred_comparison_mask"],
            "routed_mask": rel(mask_path),
            "routed_mask_sha256": sha256(mask_path),
            "metrics": metric,
            "gold": gold,
            "baseline": baseline,
            "routed": routed,
        }
        rows.append(row)
        by_dataset_metrics[str(record["dataset"])].append(metric)

    combined_summary = summarize([row["metrics"] for row in rows])
    combined_pass, combined_failed = gate(combined_summary)
    dataset_summaries: dict[str, Any] = {}
    for dataset, values in sorted(by_dataset_metrics.items()):
        summary = summarize(values)
        passed, failed = gate(summary)
        dataset_summaries[dataset] = {
            "summary": summary,
            "pass_gate": passed,
            "failed_reasons": failed,
        }

    panel = make_panel(rows)
    sample_metrics = [
        {
            "dataset": row["dataset"],
            "sample_key": row["sample_key"],
            "source_evidence": row["source_evidence"],
            "routed_mask": row["routed_mask"],
            "routed_mask_sha256": row["routed_mask_sha256"],
            "metrics": row["metrics"],
        }
        for row in rows
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "combined CelebAMask-HQ plus LaPa gold evaluation for mf70_teeth_mouth_area v2 erode/dilate route",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": REGION,
        "route": {
            "name": "teeth_mouth_area_v2_erode7x3_dilate11x7",
            "operations": [
                {"op": "erode", "kernel": "ellipse_7x3"},
                {"op": "dilate", "kernel": "ellipse_11x7"},
            ],
        },
        "source_evidence": source_evidence,
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
            "min_sample_count": MIN_SAMPLE_COUNT,
        },
        "combined_summary": combined_summary,
        "combined_pass_gate": combined_pass,
        "combined_failed_reasons": combined_failed,
        "dataset_summaries": dataset_summaries,
        "sample_metrics": sample_metrics,
        "review_panel": panel,
        "result": (
            "mf70_teeth_mouth_area_v2_combined_gold_pass_candidate_not_promoted"
            if combined_pass
            else "mf70_teeth_mouth_area_v2_combined_gold_blocked_no_promotion"
        ),
        "decision": (
            "Candidate may proceed only as unpromoted target-specific proof after strict visual QA."
            if combined_pass
            else "Do not promote or treat the v2 target proof as gold-supported; repair or policy work is still required."
        ),
        "next_required_action": (
            "If pass, keep candidate unpromoted and require target-specific strict visual/runtime proof before any active-input change. "
            "If blocked, stop using v2 as a gold-backed route and design a stronger mouth-interior boundary route."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "combined_summary": combined_summary,
                "combined_pass_gate": combined_pass,
                "dataset_summaries": dataset_summaries,
                "review_panel": panel["panel_path"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
