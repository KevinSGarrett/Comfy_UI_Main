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
EVIDENCE_ID = f"W70_MF70_TEETH_MOUTH_AREA_ANISOTROPIC_ROUTE_SEARCH_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_teeth_mouth_area_anisotropic_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "best_route_masks"

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


def kernel(width: int, height: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (width, height))


def shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    if dx == 0 and dy == 0:
        return mask
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask.astype(np.uint8), matrix, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_NEAREST, borderValue=0)


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


def score(summary: dict[str, Any]) -> float:
    fp_excess = max(0.0, float(summary["mean_false_positive_ratio_vs_gold"]) - MAX_FALSE_POSITIVE_RATIO_VS_GOLD)
    fn_excess = max(0.0, float(summary["mean_false_negative_ratio_vs_gold"]) - MAX_FALSE_NEGATIVE_RATIO_VS_GOLD)
    return float(summary["mean_iou"]) - 0.25 * fp_excess - 0.25 * fn_excess


def route_specs() -> dict[str, Callable[[np.ndarray], np.ndarray]]:
    routes: dict[str, Callable[[np.ndarray], np.ndarray]] = {"identity": lambda mask: mask}
    widths = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    heights = [1, 3, 5, 7, 9, 11]
    for w in widths:
        for h in heights:
            if w == 1 and h == 1:
                continue
            routes[f"dilate_w{w}_h{h}"] = lambda mask, w=w, h=h: cv2.dilate(mask, kernel(w, h), iterations=1)
            routes[f"close_w{w}_h{h}"] = lambda mask, w=w, h=h: cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel(w, h))
    for ew in [1, 3, 5, 7, 9]:
        for eh in [1, 3, 5]:
            for dw in [5, 7, 9, 11, 13, 15, 17, 19]:
                for dh in [3, 5, 7, 9, 11]:
                    if ew == 1 and eh == 1 and dw == 1 and dh == 1:
                        continue
                    name = f"erode_w{ew}_h{eh}_dilate_w{dw}_h{dh}"
                    routes[name] = (
                        lambda mask, ew=ew, eh=eh, dw=dw, dh=dh: cv2.dilate(
                            cv2.erode(mask, kernel(ew, eh), iterations=1),
                            kernel(dw, dh),
                            iterations=1,
                        )
                    )
    base_route_items = list(routes.items())
    for route_name, route in base_route_items:
        for dx in [-2, -1, 1, 2]:
            routes[f"{route_name}_shiftx{dx}"] = lambda mask, route=route, dx=dx: shift_mask(route(mask), dx, 0)
        for dy in [-2, -1, 1, 2]:
            routes[f"{route_name}_shifty{dy}"] = lambda mask, route=route, dy=dy: shift_mask(route(mask), 0, dy)
    return routes


def collect_records() -> tuple[list[dict[str, Any]], dict[str, str]]:
    source_paths = {
        "celeba": latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json"),
        "lapa": latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json"),
    }
    records: list[dict[str, Any]] = []
    for dataset, path in (("CelebAMask-HQ", source_paths["celeba"]), ("LaPa", source_paths["lapa"])):
        payload = load_json(path)
        for record in payload.get("comparison_records", []):
            if record.get("region") != REGION:
                continue
            item = dict(record)
            item["dataset"] = dataset
            item["source_evidence"] = rel(path)
            item["sample_key"] = str(record.get("sample_id", record.get("stem", record.get("sample_index", "sample"))))
            records.append(item)
    return records, {key: rel(path) for key, path in source_paths.items()}


def evaluate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    route_summaries: list[dict[str, Any]] = []
    route_sample_metrics: dict[str, list[dict[str, Any]]] = {}
    masks = [
        {
            "dataset": record["dataset"],
            "sample_key": record["sample_key"],
            "source_evidence": record["source_evidence"],
            "gold": load_mask(str(record["gold_comparison_mask"])),
            "pred": load_mask(str(record["pred_comparison_mask"])),
        }
        for record in records
    ]
    for route_name, transform in route_specs().items():
        samples: list[dict[str, Any]] = []
        by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in masks:
            routed = (transform(item["pred"]) > 0).astype(np.uint8)
            metric = metrics(item["gold"], routed)
            sample = {
                "dataset": item["dataset"],
                "sample_key": item["sample_key"],
                "source_evidence": item["source_evidence"],
                "metrics": metric,
            }
            samples.append(sample)
            by_dataset[item["dataset"]].append(metric)
        summary = summarize([item["metrics"] for item in samples])
        pass_gate, failed = gate(summary)
        dataset_summaries: dict[str, Any] = {}
        for dataset, values in sorted(by_dataset.items()):
            dataset_summary = summarize(values)
            dataset_pass, dataset_failed = gate(dataset_summary)
            dataset_summaries[dataset] = {
                "summary": dataset_summary,
                "pass_gate": dataset_pass,
                "failed_reasons": dataset_failed,
            }
        route_summaries.append(
            {
                "route": route_name,
                "summary": summary,
                "pass_gate": pass_gate,
                "failed_reasons": failed,
                "score": round(score(summary), 6),
                "dataset_summaries": dataset_summaries,
            }
        )
        route_sample_metrics[route_name] = samples
    route_summaries.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
    return route_summaries, route_sample_metrics


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


def make_panel(records: list[dict[str, Any]], route_name: str, transform: Callable[[np.ndarray], np.ndarray]) -> dict[str, Any]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    cells: list[Image.Image] = []
    mask_records: list[dict[str, str]] = []
    for record in records[:8]:
        gold = load_mask(str(record["gold_comparison_mask"]))
        pred = load_mask(str(record["pred_comparison_mask"]))
        routed = (transform(pred) > 0).astype(np.uint8)
        sample_key = str(record["sample_key"])
        mask_path = MASK_DIR / f"{record['dataset']}_{sample_key}_{REGION}_{route_name}.png"
        save_mask(routed, mask_path)
        mask_records.append({"dataset": record["dataset"], "sample_key": sample_key, "path": rel(mask_path), "sha256": sha256(mask_path)})
        base_metric = metrics(gold, pred)
        route_metric = metrics(gold, routed)
        cells.extend(
            [
                tile(mask_rgb(gold, (0, 210, 220)), "gold", str(record["dataset"])),
                tile(mask_rgb(pred, (255, 210, 0)), "baseline pred", f"IoU {base_metric['iou']}"),
                tile(mask_rgb(routed, (20, 210, 80)), route_name[:22], f"IoU {route_metric['iou']}"),
                tile(error_rgb(gold, routed), "route error", "red FP / blue FN"),
            ]
        )
    cols = 4
    panel = Image.new("RGB", (cols * 190, ((len(cells) + cols - 1) // cols) * 238), "white")
    for index, cell in enumerate(cells):
        panel.paste(cell, ((index % cols) * 190, (index // cols) * 238))
    panel_path = PANEL_DIR / f"{REGION}_{route_name}_panel.png"
    panel.save(panel_path)
    return {"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path), "mask_records": mask_records}


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    records, source_evidence = collect_records()
    if not records:
        raise RuntimeError(f"No records found for {REGION}")
    route_summaries, route_sample_metrics = evaluate(records)
    best = route_summaries[0]
    routes = route_specs()
    panel = make_panel(records, best["route"], routes[best["route"]])
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "combined gold anisotropic morphology and shift route search for mf70_teeth_mouth_area",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": REGION,
        "source_evidence": source_evidence,
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
            "min_sample_count": MIN_SAMPLE_COUNT,
        },
        "route_family": "identity, anisotropic dilation/closing, anisotropic erode-then-dilate, and small x/y shifts",
        "route_count": len(route_summaries),
        "best_route": best["route"],
        "best_summary": best["summary"],
        "best_pass_gate": best["pass_gate"],
        "best_failed_reasons": best["failed_reasons"],
        "best_dataset_summaries": best["dataset_summaries"],
        "top_routes": route_summaries[:20],
        "best_sample_metrics": route_sample_metrics[best["route"]],
        "review_panel": panel,
        "result": (
            "mf70_teeth_mouth_area_anisotropic_route_candidate_found_no_promotion"
            if best["pass_gate"]
            else "mf70_teeth_mouth_area_anisotropic_routes_blocked_no_promotion"
        ),
        "decision": (
            "Candidate route may proceed to target-specific strict visual/runtime proof but remains unpromoted."
            if best["pass_gate"]
            else "The tested anisotropic morphology/shift family does not repair mf70_teeth_mouth_area across combined gold evidence."
        ),
        "next_required_action": (
            "If candidate found, run target-specific source overlay and strict output proof before promotion. "
            "If blocked, use a non-morphology boundary model/policy route or switch rows."
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
                "route_count": evidence["route_count"],
                "best_route": evidence["best_route"],
                "best_summary": evidence["best_summary"],
                "best_pass_gate": evidence["best_pass_gate"],
                "best_failed_reasons": evidence["best_failed_reasons"],
                "best_dataset_summaries": evidence["best_dataset_summaries"],
                "review_panel": panel["panel_path"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
