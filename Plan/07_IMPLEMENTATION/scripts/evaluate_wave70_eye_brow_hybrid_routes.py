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
EVIDENCE_ID = f"W70_EYE_BROW_HYBRID_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_eye_brow_hybrid_routes" / RUN_STAMP
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


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def pts(face_landmarks: Any, indices: list[int], width: int, height: int) -> np.ndarray:
    return np.array([[int(round(face_landmarks[i].x * width)), int(round(face_landmarks[i].y * height))] for i in indices], dtype=np.int32)


def mp_poly(face_landmarks: Any, groups: list[list[int]], width: int, height: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        cv2.fillPoly(mask, [pts(face_landmarks, group, width, height)], 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def mp_hull(face_landmarks: Any, groups: list[list[int]], width: int, height: int, dilate: int = 0) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        cv2.fillConvexPoly(mask, cv2.convexHull(pts(face_landmarks, group, width, height)), 1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def mp_stroke(face_landmarks: Any, groups: list[list[int]], width: int, height: int, thickness: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for group in groups:
        p = pts(face_landmarks, group, width, height)
        for a, b in zip(p[:-1], p[1:]):
            cv2.line(mask, tuple(a), tuple(b), 1, thickness=thickness, lineType=cv2.LINE_AA)
    return (mask > 0).astype(np.uint8)


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
        "mean_iou": round(sum(float(v["iou"]) for v in values) / len(values), 6),
        "mean_dice": round(sum(float(v["dice"]) for v in values) / len(values), 6),
        "mean_false_positive_ratio_vs_gold": round(sum(float(v["false_positive_ratio_vs_gold"] or 0.0) for v in values) / len(values), 6),
        "mean_false_negative_ratio_vs_gold": round(sum(float(v["false_negative_ratio_vs_gold"] or 0.0) for v in values) / len(values), 6),
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
    return float(summary["mean_iou"]) - 0.25 * max(0, float(summary["mean_false_positive_ratio_vs_gold"]) - 0.15) - 0.25 * max(0, float(summary["mean_false_negative_ratio_vs_gold"]) - 0.15)


def collect() -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, str]]:
    celeba = latest("W70_FACIAL_GOLD_STANDARD_BENCHMARK_*.json")
    lapa = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    staged: dict[str, dict[str, Any]] = {}
    for dataset, path in (("CelebAMask-HQ", celeba), ("LaPa", lapa)):
        evidence = load_json(path)
        for item in evidence.get("staged_inputs", []):
            sample_key = str(item.get("sample_id", item.get("stem", item.get("sample_index"))))
            staged[f"{dataset}:{sample_key}"] = item
        for rec in evidence.get("comparison_records", []):
            if rec["region"] in REGIONS:
                item = dict(rec)
                item["dataset"] = dataset
                item["sample_key"] = str(rec.get("sample_id", rec.get("stem", rec.get("sample_index"))))
                records[item["region"]].append(item)
    return records, staged, {"celeba": rel(celeba), "lapa": rel(lapa)}


def run_landmarks(staged: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)
    out = {}
    for key, record in staged.items():
        path = abs_path(str(record["staged_image"]))
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        out[key] = {"image": rel(path), "width": bgr.shape[1], "height": bgr.shape[0], "landmarks": result.face_landmarks[0] if result.face_landmarks else None, "face_found": bool(result.face_landmarks)}
    return out


Route = Callable[[np.ndarray, Any, int, int], np.ndarray]


def make_routes(region: str) -> dict[str, Route]:
    routes: dict[str, Route] = {}
    if region == "mf70_eyes_full":
        for pd in range(0, 5):
            for md in range(0, 3):
                routes[f"union_parser_d{pd}_mp_poly_d{md}"] = (
                    lambda parser, lm, w, h, pd=pd, md=md: np.maximum(cv2.dilate(parser, kernel(pd)) if pd else parser, mp_poly(lm, [LEFT_EYE, RIGHT_EYE], w, h, md))
                )
                routes[f"intersect_parser_d{pd}_mp_poly_d{md}"] = (
                    lambda parser, lm, w, h, pd=pd, md=md: (cv2.dilate(parser, kernel(pd)) if pd else parser) & mp_poly(lm, [LEFT_EYE, RIGHT_EYE], w, h, md)
                )
        for pd in range(1, 8):
            routes[f"parser_dilate_{pd}_clip_mp_hull_d1"] = (
                lambda parser, lm, w, h, pd=pd: cv2.dilate(parser, kernel(pd)) & mp_hull(lm, [LEFT_EYE, RIGHT_EYE], w, h, 1)
            )
    else:
        for pd in range(0, 4):
            for thickness in (2, 4, 6, 8):
                routes[f"union_parser_d{pd}_mp_stroke_t{thickness}"] = (
                    lambda parser, lm, w, h, pd=pd, thickness=thickness: np.maximum(cv2.dilate(parser, kernel(pd)) if pd else parser, mp_stroke(lm, [LEFT_BROW, RIGHT_BROW], w, h, thickness))
                )
                routes[f"intersect_parser_d{pd}_mp_hull_d1"] = (
                    lambda parser, lm, w, h, pd=pd: (cv2.dilate(parser, kernel(pd)) if pd else parser) & mp_hull(lm, [LEFT_BROW, RIGHT_BROW], w, h, 1)
                )
        routes["parser_identity"] = lambda parser, lm, w, h: parser
    return routes


def evaluate(records: dict[str, list[dict[str, Any]]], lm_data: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    region_results = []
    best_samples = []
    for region in REGIONS:
        route_records = []
        by_route_samples = {}
        for route_name, route in make_routes(region).items():
            sample_metrics = []
            for rec in records[region]:
                key = f"{rec['dataset']}:{rec['sample_key']}"
                gold = load_mask(str(rec["gold_comparison_mask"]))
                parser = load_mask(str(rec["pred_comparison_mask"]), gold.shape)
                ld = lm_data[key]
                if not ld["face_found"]:
                    pred = np.zeros_like(gold)
                else:
                    pred = route(parser, ld["landmarks"], int(ld["width"]), int(ld["height"]))
                    if pred.shape != gold.shape:
                        pred = cv2.resize(pred, (gold.shape[1], gold.shape[0]), interpolation=cv2.INTER_NEAREST)
                sample_metrics.append({"dataset": rec["dataset"], "sample_key": rec["sample_key"], "metrics": metrics(gold, pred)})
            summary = summarize([m["metrics"] for m in sample_metrics])
            passed, failed = pass_gate(summary)
            route_records.append({"route": route_name, "summary": summary, "pass_gate": passed, "failed_reasons": failed, "score": round(score(summary), 6)})
            by_route_samples[route_name] = sample_metrics
        route_records.sort(key=lambda x: (x["pass_gate"], x["score"]), reverse=True)
        best = route_records[0]
        region_results.append({"region": region, "best_route": best["route"], "best_summary": best["summary"], "best_pass_gate": best["pass_gate"], "best_failed_reasons": best["failed_reasons"], "top_routes": route_records[:10], "decision": "hybrid_eye_brow_candidate_found_no_promotion" if best["pass_gate"] else "hybrid_eye_brow_routes_blocked_stronger_route_required"})
        best_samples.extend({"region": region, "best_route": best["route"], **m} for m in by_route_samples[best["route"]])
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


def make_panels(records: dict[str, list[dict[str, Any]]], results: list[dict[str, Any]], lm_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels = []
    for result in results:
        region = result["region"]
        route_name = result["best_route"]
        route = make_routes(region)[route_name]
        chunks = [records[region][:4], records[region][4:8], records[region][8:]]
        for idx, chunk in enumerate([c for c in chunks if c], 1):
            cells = []
            for rec in chunk:
                key = f"{rec['dataset']}:{rec['sample_key']}"
                gold = load_mask(str(rec["gold_comparison_mask"]))
                parser = load_mask(str(rec["pred_comparison_mask"]), gold.shape)
                ld = lm_data[key]
                pred = np.zeros_like(gold) if not ld["face_found"] else route(parser, ld["landmarks"], int(ld["width"]), int(ld["height"]))
                if pred.shape != gold.shape:
                    pred = cv2.resize(pred, (gold.shape[1], gold.shape[0]), interpolation=cv2.INTER_NEAREST)
                save_path = MASK_DIR / f"{region}_{rec['dataset']}_{rec['sample_key']}_{route_name}.png"
                save_path.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray((pred > 0).astype(np.uint8) * 255).save(save_path)
                cells.extend([
                    tile(mask_rgb(gold, (0, 210, 220)), f"{region} gold", f"{rec['dataset']} {rec['sample_key']}"),
                    tile(mask_rgb(parser, (255, 210, 0)), "parser pred", f"IoU {metrics(gold, parser)['iou']}"),
                    tile(mask_rgb(pred, (20, 210, 80)), f"hybrid {route_name}"[:30], f"IoU {metrics(gold, pred)['iou']}"),
                    tile(error_rgb(gold, pred), "hybrid error", "red FP / blue FN"),
                ])
            panel = Image.new("RGB", (4 * 190, ((len(cells) + 3) // 4) * 238), "white")
            for i, cell in enumerate(cells):
                panel.paste(cell, ((i % 4) * 190, (i // 4) * 238))
            panel_path = PANEL_DIR / f"{region}_{route_name}_panel_{idx}.png"
            panel.save(panel_path)
            panels.append({"region": region, "best_route": route_name, "panel_index": idx, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return panels


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)
    records, staged, sources = collect()
    lm_data = run_landmarks(staged)
    results, best_samples = evaluate(records, lm_data)
    panels = make_panels(records, results, lm_data)
    candidates = [r["region"] for r in results if r["best_pass_gate"]]
    blocked = [r["region"] for r in results if not r["best_pass_gate"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "parser plus MediaPipe hybrid eye/brow route evaluation against combined CelebAMask-HQ and LaPa gold masks",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": sources,
        "mediapipe_model": rel(MODEL_PATH),
        "mediapipe_model_sha256": sha256(MODEL_PATH),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "min_sample_count": MIN_SAMPLE_COUNT,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "route_family": "parser masks combined with MediaPipe eye polygons/hulls and brow strokes/hulls by union/intersection/clipped dilation",
        "region_results": results,
        "candidate_regions": candidates,
        "blocked_regions": blocked,
        "best_sample_metrics": best_samples,
        "review_panels": panels,
        "result": "hybrid_eye_brow_candidates_found_no_promotion" if candidates else "hybrid_eye_brow_routes_blocked_stronger_route_required",
        "next_required_action": "Use candidate regions only for target-specific source-overlay review; blocked regions require another model/policy route before target proof.",
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "result": evidence["result"], "candidate_regions": candidates, "blocked_regions": blocked, "region_results": [{"region": r["region"], "best_route": r["best_route"], "best_summary": r["best_summary"], "best_pass_gate": r["best_pass_gate"]} for r in results]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
