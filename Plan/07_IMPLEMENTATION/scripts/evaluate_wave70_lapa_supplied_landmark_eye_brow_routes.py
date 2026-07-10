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
EVIDENCE_ID = f"W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_lapa_supplied_landmark_eye_brow_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGIONS = ("mf70_eyes_full", "mf70_eyebrows")
MIN_MEAN_IOU = 0.85
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15

LEFT_BROW = list(range(33, 42))
RIGHT_BROW = list(range(42, 51))
LEFT_EYE = list(range(66, 75))
RIGHT_EYE = list(range(75, 84))


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


def load_mask(path_text: str) -> np.ndarray:
    return (np.array(Image.open(abs_path(path_text)).convert("L")) > 0).astype(np.uint8)


def read_lapa_points(landmark_path: Path, width: int, height: int, target_shape: tuple[int, int]) -> np.ndarray:
    lines = landmark_path.read_text(encoding="utf-8").strip().splitlines()
    count = int(lines[0].strip())
    if count < 106:
        raise ValueError(f"Expected at least 106 LaPa landmarks in {landmark_path}, found {count}")
    points = []
    target_h, target_w = target_shape
    sx = target_w / width
    sy = target_h / height
    for line in lines[1:107]:
        x_text, y_text = line.strip().split()[:2]
        points.append((int(round(float(x_text) * sx)), int(round(float(y_text) * sy))))
    return np.array(points, dtype=np.int32)


def fill_poly(points: np.ndarray, groups: list[list[int]], shape: tuple[int, int], dilate: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in groups:
        cv2.fillPoly(mask, [points[group]], 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def fill_hull(points: np.ndarray, groups: list[list[int]], shape: tuple[int, int], dilate: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in groups:
        cv2.fillConvexPoly(mask, cv2.convexHull(points[group]), 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def stroke(points: np.ndarray, groups: list[list[int]], shape: tuple[int, int], thickness: int, y_shift: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in groups:
        p = points[group].copy()
        p[:, 1] += y_shift
        for a, b in zip(p[:-1], p[1:]):
            cv2.line(mask, tuple(a), tuple(b), 1, thickness=thickness, lineType=cv2.LINE_AA)
    return (mask > 0).astype(np.uint8)


def eyebrow_band(points: np.ndarray, groups: list[list[int]], shape: tuple[int, int], up: int, down: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for group in groups:
        p = points[group]
        upper = p.copy()
        lower = p.copy()
        upper[:, 1] -= up
        lower[:, 1] += down
        band = np.vstack([upper, lower[::-1]])
        cv2.fillPoly(mask, [band], 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


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


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(items),
        "mean_iou": round(sum(float(item["iou"]) for item in items) / len(items), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in items) / len(items), 6),
        "mean_false_positive_ratio_vs_gold": round(sum(float(item["false_positive_ratio_vs_gold"] or 0.0) for item in items) / len(items), 6),
        "mean_false_negative_ratio_vs_gold": round(sum(float(item["false_negative_ratio_vs_gold"] or 0.0) for item in items) / len(items), 6),
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


Route = Callable[[np.ndarray, tuple[int, int]], np.ndarray]


def make_routes(region: str) -> dict[str, Route]:
    routes: dict[str, Route] = {}
    if region == "mf70_eyes_full":
        groups = [LEFT_EYE, RIGHT_EYE]
        for d in range(0, 7):
            routes[f"eye_poly_d{d}"] = lambda points, shape, d=d: fill_poly(points, groups, shape, d)
            routes[f"eye_hull_d{d}"] = lambda points, shape, d=d: fill_hull(points, groups, shape, d)
    else:
        groups = [LEFT_BROW, RIGHT_BROW]
        for thickness in range(2, 15, 2):
            for y_shift in (-3, -2, -1, 0, 1, 2, 3):
                routes[f"brow_stroke_t{thickness}_y{y_shift}"] = (
                    lambda points, shape, thickness=thickness, y_shift=y_shift: stroke(points, groups, shape, thickness, y_shift)
                )
        for up in range(1, 13, 2):
            for down in range(1, 9, 2):
                for d in range(0, 3):
                    routes[f"brow_band_u{up}_d{down}_d{d}"] = (
                        lambda points, shape, up=up, down=down, d=d: eyebrow_band(points, groups, shape, up, down, d)
                    )
        for d in range(0, 5):
            routes[f"brow_hull_d{d}"] = lambda points, shape, d=d: fill_hull(points, groups, shape, d)
    return routes


def collect() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], str]:
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    evidence = load_json(lapa_path)
    staged = {str(item["stem"]): item for item in evidence.get("staged_inputs", [])}
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in evidence.get("comparison_records", []):
        if rec["region"] not in REGIONS:
            continue
        item = dict(rec)
        item["stem"] = str(rec.get("stem", rec.get("sample_key", rec.get("sample_id"))))
        records[item["region"]].append(item)
    return records, staged, rel(lapa_path)


def evaluate(records: dict[str, list[dict[str, Any]]], staged: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    region_results = []
    best_samples = []
    for region in REGIONS:
        route_records = []
        by_route_samples = {}
        for route_name, route in make_routes(region).items():
            sample_metrics = []
            for rec in records[region]:
                stem = str(rec["stem"])
                staged_record = staged[stem]
                gold = load_mask(str(rec["gold_comparison_mask"]))
                source_image = Image.open(abs_path(str(staged_record["source_image"])))
                landmark_path = abs_path(str(staged_record["source_landmark"]))
                points = read_lapa_points(landmark_path, source_image.width, source_image.height, gold.shape)
                pred = route(points, gold.shape)
                sample_metrics.append({"stem": stem, "metrics": metrics(gold, pred)})
            summary = summarize([item["metrics"] for item in sample_metrics])
            passed, failed = pass_gate(summary)
            route_records.append({"route": route_name, "summary": summary, "pass_gate": passed, "failed_reasons": failed, "score": round(score(summary), 6)})
            by_route_samples[route_name] = sample_metrics
        route_records.sort(key=lambda item: (item["pass_gate"], item["score"]), reverse=True)
        best = route_records[0]
        region_results.append(
            {
                "region": region,
                "best_route": best["route"],
                "best_summary": best["summary"],
                "best_pass_gate": best["pass_gate"],
                "best_failed_reasons": best["failed_reasons"],
                "top_routes": route_records[:10],
                "decision": "lapa_supplied_landmark_candidate_found_no_promotion" if best["pass_gate"] else "lapa_supplied_landmark_routes_blocked_or_policy_required",
            }
        )
        best_samples.extend({"region": region, "best_route": best["route"], **item} for item in by_route_samples[best["route"]])
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


def make_panels(records: dict[str, list[dict[str, Any]]], staged: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels = []
    for result in results:
        region = result["region"]
        route_name = result["best_route"]
        route = make_routes(region)[route_name]
        chunks = [records[region][:4], records[region][4:]]
        for panel_index, chunk in enumerate([chunk for chunk in chunks if chunk], 1):
            cells = []
            for rec in chunk:
                stem = str(rec["stem"])
                staged_record = staged[stem]
                gold = load_mask(str(rec["gold_comparison_mask"]))
                source_image = Image.open(abs_path(str(staged_record["source_image"]))).convert("RGB")
                landmark_path = abs_path(str(staged_record["source_landmark"]))
                points = read_lapa_points(landmark_path, source_image.width, source_image.height, gold.shape)
                pred = route(points, gold.shape)
                save_path = MASK_DIR / f"{region}_{stem}_{route_name}.png"
                Image.fromarray((pred > 0).astype(np.uint8) * 255).save(save_path)
                cells.extend(
                    [
                        tile(mask_rgb(gold, (0, 210, 220)), f"{region} LaPa gold", stem),
                        tile(mask_rgb(pred, (20, 210, 80)), f"{route_name}"[:30], f"IoU {metrics(gold, pred)['iou']}"),
                        tile(error_rgb(gold, pred), "route error", "red FP / blue FN"),
                    ]
                )
            panel = Image.new("RGB", (3 * 190, ((len(cells) + 2) // 3) * 238), "white")
            for index, cell in enumerate(cells):
                panel.paste(cell, ((index % 3) * 190, (index // 3) * 238))
            panel_path = PANEL_DIR / f"{region}_{route_name}_panel_{panel_index}.png"
            panel.save(panel_path)
            panels.append({"region": region, "best_route": route_name, "panel_index": panel_index, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    records, staged, source_evidence = collect()
    results, best_samples = evaluate(records, staged)
    panels = make_panels(records, staged, results)
    candidates = [result["region"] for result in results if result["best_pass_gate"]]
    blocked = [result["region"] for result in results if not result["best_pass_gate"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "LaPa supplied 106-point landmark eye/brow route evaluation against LaPa gold labels",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": source_evidence,
        "landmark_source": "MaskedWarehouse/LaPa/*/landmarks/*.txt supplied 106-point files",
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": "LaPa supplied landmarks using explicit 106-point eye/brow groups, polygons, hulls, strokes, and brow bands",
        "region_results": results,
        "candidate_regions": candidates,
        "blocked_regions": blocked,
        "best_sample_metrics": best_samples,
        "review_panels": panels,
        "result": "lapa_supplied_landmark_candidates_found_no_promotion" if candidates else "lapa_supplied_landmark_routes_blocked_or_policy_required",
        "next_required_action": "Use this as diagnostic evidence only; target portraits do not have supplied LaPa landmarks, so any promotion requires a runtime landmark/segmentation source with comparable behavior.",
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
                "candidate_regions": candidates,
                "blocked_regions": blocked,
                "region_results": [
                    {
                        "region": result["region"],
                        "best_route": result["best_route"],
                        "best_summary": result["best_summary"],
                        "best_pass_gate": result["best_pass_gate"],
                    }
                    for result in results
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
