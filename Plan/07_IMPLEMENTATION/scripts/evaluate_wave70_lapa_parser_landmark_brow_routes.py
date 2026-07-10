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
EVIDENCE_ID = f"W70_LAPA_PARSER_LANDMARK_BROW_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_lapa_parser_landmark_brow_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGION = "mf70_eyebrows"
MIN_MEAN_IOU = 0.85
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15

LEFT_BROW = list(range(33, 42))
RIGHT_BROW = list(range(42, 51))
BROW_GROUPS = [LEFT_BROW, RIGHT_BROW]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def abs_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def load_mask(path_text: str, shape: tuple[int, int] | None = None) -> np.ndarray:
    mask = (np.array(Image.open(abs_path(path_text)).convert("L")) > 0).astype(np.uint8)
    if shape is not None and mask.shape != shape:
        mask = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return mask


def read_lapa_points(landmark_path: Path, width: int, height: int, target_shape: tuple[int, int]) -> np.ndarray:
    lines = landmark_path.read_text(encoding="utf-8").strip().splitlines()
    count = int(lines[0].strip())
    if count < 106:
        raise ValueError(f"Expected at least 106 LaPa landmarks in {landmark_path}, found {count}")
    target_h, target_w = target_shape
    sx = target_w / width
    sy = target_h / height
    points = []
    for line in lines[1:107]:
        x_text, y_text = line.strip().split()[:2]
        points.append((int(round(float(x_text) * sx)), int(round(float(y_text) * sy))))
    return np.array(points, dtype=np.int32)


def brow_hull(points: np.ndarray, shape: tuple[int, int], dilate: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in BROW_GROUPS:
        cv2.fillConvexPoly(mask, cv2.convexHull(points[group]), 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def brow_stroke(points: np.ndarray, shape: tuple[int, int], thickness: int, y_shift: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in BROW_GROUPS:
        p = points[group].copy()
        p[:, 1] += y_shift
        for a, b in zip(p[:-1], p[1:]):
            cv2.line(mask, tuple(a), tuple(b), 1, thickness=thickness, lineType=cv2.LINE_AA)
    return (mask > 0).astype(np.uint8)


def brow_band(points: np.ndarray, shape: tuple[int, int], up: int, down: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in BROW_GROUPS:
        p = points[group]
        upper = p.copy()
        lower = p.copy()
        upper[:, 1] -= up
        lower[:, 1] += down
        cv2.fillPoly(mask, [np.vstack([upper, lower[::-1]])], 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def keep_largest(mask: np.ndarray, count: int = 2) -> np.ndarray:
    labels_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if labels_count <= 1:
        return mask
    component_ids = list(range(1, labels_count))
    component_ids.sort(key=lambda idx: stats[idx, cv2.CC_STAT_AREA], reverse=True)
    keep = set(component_ids[:count])
    return np.isin(labels, list(keep)).astype(np.uint8)


def metrics(gold: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    g = gold > 0
    p = pred > 0
    gold_count = int(g.sum())
    pred_count = int(p.sum())
    inter = int(np.logical_and(g, p).sum())
    union = int(np.logical_or(g, p).sum())
    fp = int(np.logical_and(~g, p).sum())
    fn = int(np.logical_and(g, ~p).sum())
    return {
        "gold_pixels": gold_count,
        "pred_pixels": pred_count,
        "intersection_pixels": inter,
        "union_pixels": union,
        "false_positive_pixels": fp,
        "false_negative_pixels": fn,
        "iou": round(inter / union, 6) if union else 1.0,
        "dice": round((2 * inter) / (gold_count + pred_count), 6) if (gold_count + pred_count) else 1.0,
        "false_positive_ratio_vs_gold": round(fp / gold_count, 6) if gold_count else None,
        "false_negative_ratio_vs_gold": round(fn / gold_count, 6) if gold_count else None,
    }


def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "mean_iou": round(sum(float(item["iou"]) for item in values) / len(values), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in values) / len(values), 6),
        "mean_false_positive_ratio_vs_gold": round(sum(float(item["false_positive_ratio_vs_gold"] or 0.0) for item in values) / len(values), 6),
        "mean_false_negative_ratio_vs_gold": round(sum(float(item["false_negative_ratio_vs_gold"] or 0.0) for item in values) / len(values), 6),
    }


def pass_gate(summary: dict[str, Any]) -> tuple[bool, list[str]]:
    failed = []
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


Route = Callable[[np.ndarray, np.ndarray, tuple[int, int]], np.ndarray]


def make_routes() -> dict[str, Route]:
    routes: dict[str, Route] = {}
    routes["parser_identity"] = lambda parser, points, shape: parser
    for erode_radius in range(1, 5):
        routes[f"parser_erode_r{erode_radius}"] = lambda parser, points, shape, erode_radius=erode_radius: cv2.erode(parser, kernel(erode_radius), iterations=1)
    for dilate_radius in range(1, 4):
        routes[f"parser_dilate_r{dilate_radius}"] = lambda parser, points, shape, dilate_radius=dilate_radius: cv2.dilate(parser, kernel(dilate_radius), iterations=1)
    for d in range(0, 5):
        routes[f"intersect_parser_brow_hull_d{d}"] = lambda parser, points, shape, d=d: parser & brow_hull(points, shape, d)
        routes[f"union_parser_brow_hull_d{d}"] = lambda parser, points, shape, d=d: np.maximum(parser, brow_hull(points, shape, d))
    for thickness in range(2, 18, 2):
        for y_shift in (-3, -2, -1, 0, 1, 2, 3):
            routes[f"intersect_parser_stroke_t{thickness}_y{y_shift}"] = (
                lambda parser, points, shape, thickness=thickness, y_shift=y_shift: parser & brow_stroke(points, shape, thickness, y_shift)
            )
            routes[f"union_parser_stroke_t{thickness}_y{y_shift}"] = (
                lambda parser, points, shape, thickness=thickness, y_shift=y_shift: np.maximum(parser, brow_stroke(points, shape, thickness, y_shift))
            )
    for up in range(1, 16, 2):
        for down in range(1, 10, 2):
            for d in range(0, 3):
                routes[f"intersect_parser_band_u{up}_d{down}_r{d}"] = (
                    lambda parser, points, shape, up=up, down=down, d=d: parser & brow_band(points, shape, up, down, d)
                )
                routes[f"union_parser_band_u{up}_d{down}_r{d}"] = (
                    lambda parser, points, shape, up=up, down=down, d=d: np.maximum(parser, brow_band(points, shape, up, down, d))
                )
    for count in (1, 2, 3):
        routes[f"parser_keep_largest_{count}"] = lambda parser, points, shape, count=count: keep_largest(parser, count)
    return routes


def collect() -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    evidence = load_json(lapa_path)
    staged = {str(item["stem"]): item for item in evidence.get("staged_inputs", [])}
    records = []
    for rec in evidence.get("comparison_records", []):
        if rec.get("region") == REGION:
            item = dict(rec)
            item["stem"] = str(rec.get("stem", rec.get("sample_key", rec.get("sample_id"))))
            records.append(item)
    return records, staged, rel(lapa_path)


def evaluate(records: list[dict[str, Any]], staged: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    route_results = []
    by_route_samples = {}
    for route_name, route in make_routes().items():
        sample_metrics = []
        for rec in records:
            stem = str(rec["stem"])
            staged_record = staged[stem]
            gold = load_mask(str(rec["gold_comparison_mask"]))
            parser = load_mask(str(rec["pred_comparison_mask"]), gold.shape)
            source_image = Image.open(abs_path(str(staged_record["source_image"])))
            points = read_lapa_points(abs_path(str(staged_record["source_landmark"])), source_image.width, source_image.height, gold.shape)
            pred = route(parser, points, gold.shape).astype(np.uint8)
            sample_metrics.append({"stem": stem, "metrics": metrics(gold, pred)})
        summary = summarize([item["metrics"] for item in sample_metrics])
        passed, failed = pass_gate(summary)
        route_results.append({"route": route_name, "summary": summary, "pass_gate": passed, "failed_reasons": failed, "score": round(score(summary), 6)})
        by_route_samples[route_name] = sample_metrics
    route_results.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
    best = route_results[0]
    best_samples = [{"best_route": best["route"], **item} for item in by_route_samples[best["route"]]]
    return route_results, best_samples


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


def make_panels(records: list[dict[str, Any]], staged: dict[str, Any], best_route: str) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    route = make_routes()[best_route]
    chunks = [records[:4], records[4:]]
    panels = []
    for panel_index, chunk in enumerate([chunk for chunk in chunks if chunk], 1):
        cells = []
        for rec in chunk:
            stem = str(rec["stem"])
            staged_record = staged[stem]
            gold = load_mask(str(rec["gold_comparison_mask"]))
            parser = load_mask(str(rec["pred_comparison_mask"]), gold.shape)
            source_image = Image.open(abs_path(str(staged_record["source_image"])))
            points = read_lapa_points(abs_path(str(staged_record["source_landmark"])), source_image.width, source_image.height, gold.shape)
            pred = route(parser, points, gold.shape).astype(np.uint8)
            save_path = MASK_DIR / f"{REGION}_{stem}_{best_route}.png"
            Image.fromarray((pred > 0).astype(np.uint8) * 255).save(save_path)
            cells.extend(
                [
                    tile(mask_rgb(gold, (0, 210, 220)), "LaPa gold brows", stem),
                    tile(mask_rgb(parser, (255, 210, 0)), "parser brows", f"IoU {metrics(gold, parser)['iou']}"),
                    tile(mask_rgb(pred, (20, 210, 80)), best_route[:30], f"IoU {metrics(gold, pred)['iou']}"),
                    tile(error_rgb(gold, pred), "route error", "red FP / blue FN"),
                ]
            )
        panel = Image.new("RGB", (4 * 190, ((len(cells) + 3) // 4) * 238), "white")
        for index, cell in enumerate(cells):
            panel.paste(cell, ((index % 4) * 190, (index // 4) * 238))
        panel_path = PANEL_DIR / f"{REGION}_{best_route}_panel_{panel_index}.png"
        panel.save(panel_path)
        panels.append({"region": REGION, "best_route": best_route, "panel_index": panel_index, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    records, staged, source_evidence = collect()
    route_results, best_samples = evaluate(records, staged)
    best = route_results[0]
    panels = make_panels(records, staged, best["route"])
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "LaPa parser plus supplied-landmark route evaluation for mf70_eyebrows",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": source_evidence,
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": "LaPa supplied brow landmarks combined with BiSeNet parser masks by union/intersection/strokes/bands/hulls",
        "region_result": {
            "region": REGION,
            "best_route": best["route"],
            "best_summary": best["summary"],
            "best_pass_gate": best["pass_gate"],
            "best_failed_reasons": best["failed_reasons"],
            "top_routes": route_results[:12],
            "decision": "lapa_parser_landmark_brow_candidate_found_no_promotion" if best["pass_gate"] else "lapa_parser_landmark_brow_routes_blocked_policy_or_stronger_parser_required",
        },
        "best_sample_metrics": best_samples,
        "review_panels": panels,
        "result": "lapa_parser_landmark_brow_candidate_found_no_promotion" if best["pass_gate"] else "lapa_parser_landmark_brow_routes_blocked_policy_or_stronger_parser_required",
        "next_required_action": "If blocked, stop treating brows as a landmark-only problem and move to semantic parser/policy repair.",
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": rel(evidence_path), "tracker": rel(tracker_path), "result": evidence["result"], "best_route": best["route"], "best_summary": best["summary"], "best_pass_gate": best["pass_gate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
