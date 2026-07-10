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
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
MODEL_PATH = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "mediapipe_models" / "face_landmarker_float16_latest.task"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MEDIAPIPE_EYE_BROW_COMBINED_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_mediapipe_eye_brow_combined_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"

REGIONS = ("mf70_eyes_full", "mf70_eyebrows")
MIN_MEAN_IOU = 0.85
MIN_SAMPLE_COUNT = 3
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15

LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
LEFT_BROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]


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


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def points(face_landmarks: Any, indices: list[int], width: int, height: int) -> np.ndarray:
    pts = []
    for idx in indices:
        lm = face_landmarks[idx]
        pts.append([int(round(lm.x * width)), int(round(lm.y * height))])
    return np.array(pts, dtype=np.int32)


def polygon(face_landmarks: Any, groups: list[list[int]], width: int, height: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        cv2.fillPoly(mask, [points(face_landmarks, group, width, height)], 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def stroke(face_landmarks: Any, groups: list[list[int]], width: int, height: int, thickness: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        pts = points(face_landmarks, group, width, height)
        for a, b in zip(pts[:-1], pts[1:]):
            cv2.line(mask, tuple(a), tuple(b), 1, thickness=thickness, lineType=cv2.LINE_AA)
    mask = (mask > 0).astype(np.uint8)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def hull(face_landmarks: Any, groups: list[list[int]], width: int, height: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        pts = points(face_landmarks, group, width, height)
        cv2.fillConvexPoly(mask, cv2.convexHull(pts), 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


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
    fp = int(np.logical_and(~gold_bits, pred_bits).sum())
    fn = int(np.logical_and(gold_bits, ~pred_bits).sum())
    dice_den = gold_count + pred_count
    return {
        "gold_pixels": gold_count,
        "pred_pixels": pred_count,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "false_positive_pixels": fp,
        "false_negative_pixels": fn,
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / dice_den, 6) if dice_den else 1.0,
        "false_positive_ratio_vs_gold": round(fp / gold_count, 6) if gold_count else None,
        "false_negative_ratio_vs_gold": round(fn / gold_count, 6) if gold_count else None,
    }


def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "mean_iou": round(sum(float(item["iou"]) for item in values) / len(values), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in values) / len(values), 6),
        "mean_false_positive_ratio_vs_gold": round(
            sum(float(item["false_positive_ratio_vs_gold"] or 0.0) for item in values) / len(values), 6
        ),
        "mean_false_negative_ratio_vs_gold": round(
            sum(float(item["false_negative_ratio_vs_gold"] or 0.0) for item in values) / len(values), 6
        ),
    }


def pass_gate(summary: dict[str, Any]) -> tuple[bool, list[str]]:
    failed = []
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


Route = Callable[[Any, int, int], np.ndarray]


def make_routes(region: str) -> dict[str, Route]:
    routes: dict[str, Route] = {}
    if region == "mf70_eyes_full":
        for d in range(0, 8):
            routes[f"eye_polygon_d{d}"] = lambda lm, w, h, d=d: polygon(lm, [LEFT_EYE, RIGHT_EYE], w, h, d)
            routes[f"eye_hull_d{d}"] = lambda lm, w, h, d=d: hull(lm, [LEFT_EYE, RIGHT_EYE], w, h, d)
        for dy in (-2, -1, 1, 2):
            for d in (1, 2, 3, 4):
                routes[f"eye_polygon_shift_y{dy}_d{d}"] = (
                    lambda lm, w, h, dy=dy, d=d: shifted(polygon(lm, [LEFT_EYE, RIGHT_EYE], w, h, d), 0, dy)
                )
    else:
        for thickness in range(2, 18, 2):
            routes[f"brow_stroke_t{thickness}"] = (
                lambda lm, w, h, thickness=thickness: stroke(lm, [LEFT_BROW, RIGHT_BROW], w, h, thickness)
            )
            routes[f"brow_stroke_t{thickness}_d1"] = (
                lambda lm, w, h, thickness=thickness: stroke(lm, [LEFT_BROW, RIGHT_BROW], w, h, thickness, 1)
            )
        for d in range(0, 5):
            routes[f"brow_hull_d{d}"] = lambda lm, w, h, d=d: hull(lm, [LEFT_BROW, RIGHT_BROW], w, h, d)
        for dy in (-3, -2, -1, 1, 2, 3):
            for thickness in (4, 6, 8, 10):
                routes[f"brow_stroke_y{dy}_t{thickness}"] = (
                    lambda lm, w, h, dy=dy, thickness=thickness:
                    shifted(stroke(lm, [LEFT_BROW, RIGHT_BROW], w, h, thickness), 0, dy)
                )
    return routes


def collect() -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, str]]:
    celeba_path = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    staged: dict[str, dict[str, Any]] = {}
    for dataset, path in (("CelebAMask-HQ", celeba_path), ("LaPa", lapa_path)):
        evidence = load_json(path)
        for item in evidence.get("staged_inputs", []):
            sample_key = str(item.get("sample_id", item.get("stem", item.get("sample_index"))))
            if dataset == "LaPa" and "stem" not in item:
                # LaPa staged records have sample_index and stem in current evidence.
                sample_key = str(item.get("stem", item.get("sample_index")))
            staged[f"{dataset}:{sample_key}"] = item
        for record in evidence.get("comparison_records", []):
            region = str(record["region"])
            if region not in REGIONS:
                continue
            sample_key = str(record.get("sample_id", record.get("stem", record.get("sample_index"))))
            item = dict(record)
            item["dataset"] = dataset
            item["sample_key"] = sample_key
            records[region].append(item)
    return records, staged, {"celeba": rel(celeba_path), "lapa": rel(lapa_path)}


def staged_image_path(dataset: str, sample_key: str, staged: dict[str, dict[str, Any]]) -> Path:
    record = staged.get(f"{dataset}:{sample_key}")
    if record is None and dataset == "LaPa":
        for key, candidate in staged.items():
            if key.startswith("LaPa:") and str(candidate.get("stem")) == sample_key:
                record = candidate
                break
    if record is None:
        raise KeyError(f"No staged input for {dataset}:{sample_key}")
    return abs_path(str(record["staged_image"]))


def run_landmarks(staged_records: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    detector = FaceLandmarker.create_from_options(options)
    out: dict[str, dict[str, Any]] = {}
    for key, record in staged_records.items():
        image_path = abs_path(str(record["staged_image"]))
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(image_path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        out[key] = {
            "image": rel(image_path),
            "width": bgr.shape[1],
            "height": bgr.shape[0],
            "landmarks": result.face_landmarks[0] if result.face_landmarks else None,
            "face_found": bool(result.face_landmarks),
        }
    return out


def evaluate(records: dict[str, list[dict[str, Any]]], landmark_data: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    region_results = []
    best_samples = []
    for region in REGIONS:
        route_records = []
        sample_metrics_by_route = {}
        for route_name, route in make_routes(region).items():
            sample_metrics = []
            for record in records[region]:
                key = f"{record['dataset']}:{record['sample_key']}"
                lm_data = landmark_data.get(key)
                gold = load_mask(str(record["gold_comparison_mask"]))
                if not lm_data or not lm_data["face_found"]:
                    pred = np.zeros_like(gold)
                else:
                    pred = route(lm_data["landmarks"], int(lm_data["width"]), int(lm_data["height"]))
                    if pred.shape != gold.shape:
                        pred = cv2.resize(pred, (gold.shape[1], gold.shape[0]), interpolation=cv2.INTER_NEAREST)
                sample_metrics.append({"dataset": record["dataset"], "sample_key": record["sample_key"], "metrics": metrics(gold, pred)})
            summary = summarize([item["metrics"] for item in sample_metrics])
            passed, failed = pass_gate(summary)
            route_records.append({"route": route_name, "summary": summary, "pass_gate": passed, "failed_reasons": failed, "score": round(score(summary), 6)})
            sample_metrics_by_route[route_name] = sample_metrics
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
                "decision": "mediapipe_eye_brow_candidate_found_no_promotion" if best["pass_gate"] else "mediapipe_eye_brow_routes_blocked_stronger_route_required",
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


def make_panels(records: dict[str, list[dict[str, Any]]], region_results: list[dict[str, Any]], landmark_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels = []
    for region_result in region_results:
        region = region_result["region"]
        route_name = region_result["best_route"]
        route = make_routes(region)[route_name]
        chunks = [records[region][:4], records[region][4:8], records[region][8:]]
        for panel_index, chunk in enumerate([item for item in chunks if item], 1):
            cells = []
            for record in chunk:
                key = f"{record['dataset']}:{record['sample_key']}"
                lm_data = landmark_data.get(key)
                gold = load_mask(str(record["gold_comparison_mask"]))
                if not lm_data or not lm_data["face_found"]:
                    pred = np.zeros_like(gold)
                else:
                    pred = route(lm_data["landmarks"], int(lm_data["width"]), int(lm_data["height"]))
                    if pred.shape != gold.shape:
                        pred = cv2.resize(pred, (gold.shape[1], gold.shape[0]), interpolation=cv2.INTER_NEAREST)
                mask_path = MASK_DIR / f"{region}_{record['dataset']}_{record['sample_key']}_{route_name}.png"
                save_mask(pred, mask_path)
                cells.extend(
                    [
                        tile(mask_rgb(gold, (0, 210, 220)), f"{region} gold", f"{record['dataset']} {record['sample_key']}"),
                        tile(mask_rgb(pred, (20, 210, 80)), f"best {route_name}"[:30], f"IoU {metrics(gold, pred)['iou']}"),
                        tile(error_rgb(gold, pred), "best error", "red FP / blue FN"),
                    ]
                )
            cols = 3
            cell_w = max(cell.width for cell in cells)
            cell_h = max(cell.height for cell in cells)
            rows = (len(cells) + cols - 1) // cols
            panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
            for index, cell in enumerate(cells):
                panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
            panel_path = PANEL_DIR / f"{region}_{route_name}_panel_{panel_index}.png"
            panel.save(panel_path)
            panels.append({"region": region, "best_route": route_name, "panel_index": panel_index, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)
    records, staged, source_evidence = collect()
    landmark_data = run_landmarks(staged)
    region_results, best_samples = evaluate(records, landmark_data)
    panels = make_panels(records, region_results, landmark_data)
    candidates = [item["region"] for item in region_results if item["best_pass_gate"]]
    blocked = [item["region"] for item in region_results if not item["best_pass_gate"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "MediaPipe FaceLandmarker combined CelebAMask-HQ plus LaPa eye/brow route evaluation",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": source_evidence,
        "mediapipe_model": rel(MODEL_PATH),
        "mediapipe_model_sha256": sha256(MODEL_PATH),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "min_sample_count": MIN_SAMPLE_COUNT,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": "MediaPipe FaceLandmarker eye contours, brow strokes/hulls, dilation and small vertical shifts",
        "landmark_detection": {
            key: {"image": value["image"], "face_found": value["face_found"], "width": value["width"], "height": value["height"]}
            for key, value in landmark_data.items()
        },
        "region_results": region_results,
        "candidate_regions": candidates,
        "blocked_regions": blocked,
        "best_sample_metrics": best_samples,
        "review_panels": panels,
        "result": "mediapipe_eye_brow_candidates_found_no_promotion" if candidates else "mediapipe_eye_brow_routes_blocked_stronger_route_required",
        "next_required_action": "Use candidate regions only for target-specific source-overlay review; blocked regions need another model/policy route before target proof.",
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "result": evidence["result"], "candidate_regions": candidates, "blocked_regions": blocked, "region_results": [{"region": item["region"], "best_route": item["best_route"], "best_summary": item["best_summary"], "best_pass_gate": item["best_pass_gate"]} for item in region_results]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
