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
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_INSIGHTFACE_106_EYE_ROUTE_EVAL_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_insightface_106_eye_routes" / RUN_STAMP
PANEL_DIR = RUNTIME_DIR / "review_panels"
MASK_DIR = RUNTIME_DIR / "route_masks"
MODEL_ROOT = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "insightface_models"

REGION = "mf70_eyes_full"
MIN_MEAN_IOU = 0.85
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def abs_path(path_text: str | Path) -> Path:
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


def load_mask(path_text: str | Path) -> np.ndarray:
    return (np.array(Image.open(abs_path(path_text)).convert("L")) > 0).astype(np.uint8)


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask > 0).astype(np.uint8) * 255).save(path)


def kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


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
        "false_positive_ratio_vs_gold": round(fp / gold_count, 6) if gold_count else 0.0,
        "false_negative_ratio_vs_gold": round(fn / gold_count, 6) if gold_count else 0.0,
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(items),
        "mean_iou": round(sum(float(item["iou"]) for item in items) / len(items), 6),
        "mean_dice": round(sum(float(item["dice"]) for item in items) / len(items), 6),
        "mean_false_positive_ratio_vs_gold": round(sum(float(item["false_positive_ratio_vs_gold"]) for item in items) / len(items), 6),
        "mean_false_negative_ratio_vs_gold": round(sum(float(item["false_negative_ratio_vs_gold"]) for item in items) / len(items), 6),
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
        - 0.25 * max(0.0, float(summary["mean_false_negative_ratio_vs_gold"]) - MAX_FALSE_NEGATIVE_RATIO_VS_GOLD)
    )


def collect_records() -> tuple[list[dict[str, Any]], dict[str, Any], Path]:
    lapa_path = latest("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json")
    evidence = load_json(lapa_path)
    staged = {str(item["stem"]): item for item in evidence.get("staged_inputs", [])}
    records: list[dict[str, Any]] = []
    for rec in evidence.get("comparison_records", []):
        if rec.get("region") != REGION:
            continue
        item = dict(rec)
        item["stem"] = str(rec.get("stem", rec.get("sample_key", rec.get("sample_id"))))
        records.append(item)
    return records, staged, lapa_path


def choose_primary_face(faces: list[Any]) -> Any | None:
    if not faces:
        return None
    return max(
        faces,
        key=lambda face: float(face.get("det_score", 0.0))
        * max(1.0, float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))),
    )


def scale_points(points: np.ndarray, source_shape: tuple[int, int], target_shape: tuple[int, int]) -> np.ndarray:
    source_h, source_w = source_shape
    target_h, target_w = target_shape
    scaled = points.astype(np.float32).copy()
    scaled[:, 0] *= target_w / source_w
    scaled[:, 1] *= target_h / source_h
    return scaled


def hull_from_points(points: np.ndarray, shape: tuple[int, int], dilate: int) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    if len(points) >= 3:
        clipped = points.copy()
        clipped[:, 0] = np.clip(clipped[:, 0], 0, shape[1] - 1)
        clipped[:, 1] = np.clip(clipped[:, 1], 0, shape[0] - 1)
        cv2.fillConvexPoly(mask, cv2.convexHull(np.rint(clipped).astype(np.int32)), 1)
    elif len(points) > 0:
        for x, y in np.rint(points).astype(np.int32):
            cv2.circle(mask, (int(x), int(y)), max(1, dilate + 1), 1, -1)
    if dilate:
        mask = cv2.dilate(mask, kernel(dilate), iterations=1)
    return mask


def eye_window_mask(
    points: np.ndarray,
    kps: np.ndarray,
    shape: tuple[int, int],
    *,
    x_frac: float,
    y_frac: float,
    min_points: int,
    fallback_points: int,
    dilate: int,
) -> np.ndarray:
    left_center = kps[0]
    right_center = kps[1]
    eye_distance = max(1.0, float(np.linalg.norm(left_center - right_center)))
    out = np.zeros(shape, dtype=np.uint8)
    for center in (left_center, right_center):
        dx = max(2.0, eye_distance * x_frac)
        dy = max(1.0, eye_distance * y_frac)
        normalized = ((points[:, 0] - center[0]) / dx) ** 2 + ((points[:, 1] - center[1]) / dy) ** 2
        selected = points[normalized <= 1.0]
        if len(selected) < min_points:
            nearest = np.argsort(normalized)[:fallback_points]
            selected = points[nearest]
        out = np.maximum(out, hull_from_points(selected, shape, dilate))
    return out


def eye_ellipse_mask(
    kps: np.ndarray,
    shape: tuple[int, int],
    *,
    x_frac: float,
    y_frac: float,
    y_shift_frac: float,
    angle_from_kps: bool,
    dilate: int,
) -> np.ndarray:
    left_center = kps[0].copy()
    right_center = kps[1].copy()
    eye_delta = right_center - left_center
    eye_distance = max(1.0, float(np.linalg.norm(eye_delta)))
    angle = float(np.degrees(np.arctan2(eye_delta[1], eye_delta[0]))) if angle_from_kps else 0.0
    out = np.zeros(shape, dtype=np.uint8)
    for center in (left_center, right_center):
        center[1] += eye_distance * y_shift_frac
        axes = (
            max(1, int(round(eye_distance * x_frac))),
            max(1, int(round(eye_distance * y_frac))),
        )
        cv2.ellipse(
            out,
            tuple(np.rint(center).astype(np.int32)),
            axes,
            angle,
            0,
            360,
            1,
            -1,
            lineType=cv2.LINE_AA,
        )
    out = (out > 0).astype(np.uint8)
    if dilate:
        out = cv2.dilate(out, kernel(dilate), iterations=1)
    return out


def eye_index_hull_mask(
    points: np.ndarray,
    shape: tuple[int, int],
    *,
    left_indices: tuple[int, ...],
    right_indices: tuple[int, ...],
    dilate: int,
    erode: int,
) -> np.ndarray:
    out = np.zeros(shape, dtype=np.uint8)
    for indices in (left_indices, right_indices):
        selected = points[list(indices)]
        out = np.maximum(out, hull_from_points(selected, shape, 0))
    if dilate:
        out = cv2.dilate(out, kernel(dilate), iterations=1)
    if erode:
        out = cv2.erode(out, kernel(erode), iterations=1)
    return out


def parser_constrained_mask(
    landmark_mask: np.ndarray,
    parser_mask: np.ndarray,
    *,
    mode: str,
    parser_dilate: int,
    parser_erode: int,
) -> np.ndarray:
    parser = (parser_mask > 0).astype(np.uint8)
    if parser_dilate:
        parser = cv2.dilate(parser, kernel(parser_dilate), iterations=1)
    if parser_erode:
        parser = cv2.erode(parser, kernel(parser_erode), iterations=1)
    landmark = (landmark_mask > 0).astype(np.uint8)
    if mode == "landmark":
        return landmark
    if mode == "intersect_parser":
        return np.logical_and(landmark, parser).astype(np.uint8)
    if mode == "union_parser":
        return np.logical_or(landmark, parser).astype(np.uint8)
    if mode == "parser_only":
        return parser
    raise ValueError(f"unknown parser constraint mode: {mode}")


def anisotropic_morph(mask: np.ndarray, *, dilate_x: int = 0, dilate_y: int = 0, erode_x: int = 0, erode_y: int = 0) -> np.ndarray:
    out = (mask > 0).astype(np.uint8)
    if dilate_x or dilate_y:
        out = cv2.dilate(
            out,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1, 2 * dilate_x + 1), max(1, 2 * dilate_y + 1))),
            iterations=1,
        )
    if erode_x or erode_y:
        out = cv2.erode(
            out,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1, 2 * erode_x + 1), max(1, 2 * erode_y + 1))),
            iterations=1,
        )
    return out


def eye_index_anisotropic_parser_union_mask(
    sample: dict[str, Any],
    *,
    left_indices: tuple[int, ...],
    right_indices: tuple[int, ...],
    landmark_erode_y: int,
    parser_dilate_y: int,
) -> np.ndarray:
    landmark = eye_index_hull_mask(
        sample["points"],
        sample["gold"].shape,
        left_indices=left_indices,
        right_indices=right_indices,
        dilate=0,
        erode=0,
    )
    landmark = anisotropic_morph(landmark, erode_y=landmark_erode_y)
    parser = anisotropic_morph(sample["pred"], dilate_y=parser_dilate_y)
    return np.logical_or(landmark, parser).astype(np.uint8)


Route = Callable[[dict[str, Any]], np.ndarray]


def make_routes() -> dict[str, Route]:
    routes: dict[str, Route] = {}
    for x_frac in (0.12, 0.15, 0.18, 0.22, 0.26, 0.30):
        for y_frac in (0.045, 0.06, 0.075, 0.09, 0.11, 0.13):
            for min_points in (4, 6, 8):
                for fallback_points in (6, 8, 10, 12):
                    for dilate in (0, 1, 2, 3):
                        name = f"eye_window_x{x_frac}_y{y_frac}_m{min_points}_f{fallback_points}_d{dilate}"
                        routes[name] = (
                            lambda sample, x_frac=x_frac, y_frac=y_frac,
                            min_points=min_points, fallback_points=fallback_points, dilate=dilate:
                            eye_window_mask(
                                sample["points"],
                                sample["kps"],
                                sample["gold"].shape,
                                x_frac=x_frac,
                                y_frac=y_frac,
                                min_points=min_points,
                                fallback_points=fallback_points,
                                dilate=dilate,
                            )
                        )
    for x_frac in (0.055, 0.07, 0.085, 0.10, 0.12, 0.14, 0.16):
        for y_frac in (0.022, 0.03, 0.038, 0.046, 0.055, 0.065, 0.075):
            for y_shift_frac in (-0.035, -0.02, -0.01, 0.0, 0.01, 0.02, 0.035):
                for angle_from_kps in (False, True):
                    for dilate in (0, 1, 2):
                        name = f"eye_ellipse_x{x_frac}_y{y_frac}_ys{y_shift_frac}_a{int(angle_from_kps)}_d{dilate}"
                        routes[name] = (
                            lambda sample, x_frac=x_frac, y_frac=y_frac,
                            y_shift_frac=y_shift_frac, angle_from_kps=angle_from_kps, dilate=dilate:
                            eye_ellipse_mask(
                                sample["kps"],
                                sample["gold"].shape,
                                x_frac=x_frac,
                                y_frac=y_frac,
                                y_shift_frac=y_shift_frac,
                                angle_from_kps=angle_from_kps,
                                dilate=dilate,
                            )
                        )
    index_groups: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {
        "eye106_all10": (tuple(range(33, 43)), tuple(range(87, 97))),
        "eye106_contour8": ((33, 35, 36, 37, 39, 40, 41, 42), (87, 89, 90, 91, 93, 94, 95, 96)),
        "eye106_inner8": ((33, 34, 36, 38, 40, 41, 42, 35), (87, 88, 90, 92, 94, 95, 96, 93)),
        "eye106_no_centers8": ((33, 35, 36, 37, 39, 40, 41, 42), (87, 89, 90, 91, 93, 94, 95, 96)),
        "eye106_core6": ((33, 34, 36, 38, 40, 42), (87, 88, 90, 92, 94, 96)),
        "eye106_upper_lower6": ((33, 36, 37, 40, 41, 42), (87, 90, 91, 94, 95, 96)),
    }
    for group_name, (left_indices, right_indices) in index_groups.items():
        for hull_dilate in (0, 1, 2, 3):
            for hull_erode in (0, 1):
                for mode in ("landmark", "intersect_parser", "union_parser"):
                    parser_dilates = (0,) if mode == "landmark" else (0, 1, 2, 3, 4, 5)
                    for parser_dilate in parser_dilates:
                        name = (
                            f"{group_name}_hd{hull_dilate}_he{hull_erode}"
                            f"_{mode}_pd{parser_dilate}"
                        )
                        routes[name] = (
                            lambda sample, left_indices=left_indices, right_indices=right_indices,
                            hull_dilate=hull_dilate, hull_erode=hull_erode, mode=mode,
                            parser_dilate=parser_dilate:
                            parser_constrained_mask(
                                eye_index_hull_mask(
                                    sample["points"],
                                    sample["gold"].shape,
                                    left_indices=left_indices,
                                    right_indices=right_indices,
                                    dilate=hull_dilate,
                                    erode=hull_erode,
                                ),
                                sample["pred"],
                                mode=mode,
                                parser_dilate=parser_dilate,
                                parser_erode=0,
                            )
                        )
    for parser_dilate in (0, 1, 2, 3, 4, 5, 6):
        name = f"parser_only_pd{parser_dilate}"
        routes[name] = (
            lambda sample, parser_dilate=parser_dilate:
            parser_constrained_mask(
                np.zeros_like(sample["pred"], dtype=np.uint8),
                sample["pred"],
                mode="parser_only",
                parser_dilate=parser_dilate,
                parser_erode=0,
            )
        )
    for group_name, (left_indices, right_indices) in {
        "eye106_all10": (tuple(range(33, 43)), tuple(range(87, 97))),
        "eye106_contour8": ((33, 35, 36, 37, 39, 40, 41, 42), (87, 89, 90, 91, 93, 94, 95, 96)),
    }.items():
        for landmark_erode_y in (0, 1, 2):
            for parser_dilate_y in (0, 1, 2, 3):
                name = f"{group_name}_anis_heY{landmark_erode_y}_union_parser_pdY{parser_dilate_y}"
                routes[name] = (
                    lambda sample, left_indices=left_indices, right_indices=right_indices,
                    landmark_erode_y=landmark_erode_y, parser_dilate_y=parser_dilate_y:
                    eye_index_anisotropic_parser_union_mask(
                        sample,
                        left_indices=left_indices,
                        right_indices=right_indices,
                        landmark_erode_y=landmark_erode_y,
                        parser_dilate_y=parser_dilate_y,
                    )
                )
    return routes


def detect_samples(records: list[dict[str, Any]], staged: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    app = FaceAnalysis(name="buffalo_l", root=str(MODEL_ROOT), providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    samples: list[dict[str, Any]] = []
    detection_records: list[dict[str, Any]] = []
    for rec in records:
        stem = str(rec["stem"])
        staged_record = staged[stem]
        image_path = abs_path(staged_record["source_image"])
        gold = load_mask(rec["gold_comparison_mask"])
        pred = load_mask(rec["pred_comparison_mask"])
        image = cv2.imread(str(image_path))
        if image is None:
            detection_records.append({"stem": stem, "source_image": rel(image_path), "error": "cv2_imread_failed"})
            continue
        faces = app.get(image)
        face = choose_primary_face(faces)
        detection_record = {
            "stem": stem,
            "source_image": rel(image_path),
            "face_count": len(faces),
            "selected_face_available": face is not None,
        }
        if face is None or face.get("landmark_2d_106") is None:
            detection_record["error"] = "no_face_or_no_106_landmarks"
            detection_records.append(detection_record)
            continue
        source_shape = (image.shape[0], image.shape[1])
        points = scale_points(np.asarray(face["landmark_2d_106"]), source_shape, gold.shape)
        kps = scale_points(np.asarray(face["kps"]), source_shape, gold.shape)
        detection_record.update(
            {
                "bbox": [round(float(value), 3) for value in face["bbox"].tolist()],
                "det_score": round(float(face.get("det_score", 0.0)), 6),
                "landmark_2d_106_shape": list(np.asarray(face["landmark_2d_106"]).shape),
                "kps_shape": list(np.asarray(face["kps"]).shape),
            }
        )
        detection_records.append(detection_record)
        samples.append({"stem": stem, "gold": gold, "pred": pred, "points": points, "kps": kps, "record": rec, "staged": staged_record})
    return samples, {"detections": detection_records}


def evaluate(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], str, Route]:
    routes = make_routes()
    route_records: list[dict[str, Any]] = []
    samples_by_route: dict[str, list[dict[str, Any]]] = {}
    for route_name, route in routes.items():
        sample_metrics: list[dict[str, Any]] = []
        for sample in samples:
            pred = route(sample)
            sample_metrics.append({"stem": sample["stem"], "metrics": metrics(sample["gold"], pred)})
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
    return route_records, samples_by_route, best_route_name, make_routes()[best_route_name]


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


def make_panels(samples: list[dict[str, Any]], route_name: str, route: Route) -> list[dict[str, Any]]:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []
    chunks = [samples[:4], samples[4:8]]
    for panel_index, chunk in enumerate([chunk for chunk in chunks if chunk], 1):
        cells: list[Image.Image] = []
        for sample in chunk:
            pred = route(sample)
            save_path = MASK_DIR / f"{sample['stem']}_{route_name}.png"
            save_mask(pred, save_path)
            cells.extend(
                [
                    tile(mask_rgb(sample["gold"], (0, 210, 220)), "LaPa eyes gold", sample["stem"]),
                    tile(mask_rgb(pred, (20, 210, 80)), f"{route_name}"[:30], f"IoU {metrics(sample['gold'], pred)['iou']}"),
                    tile(error_rgb(sample["gold"], pred), "route error", "red FP / blue FN"),
                ]
            )
        panel = Image.new("RGB", (3 * 190, ((len(cells) + 2) // 3) * 238), "white")
        for index, cell in enumerate(cells):
            panel.paste(cell, ((index % 3) * 190, (index // 3) * 238))
        panel_path = PANEL_DIR / f"{REGION}_{route_name}_panel_{panel_index}.png"
        panel.save(panel_path)
        panels.append({"panel_path": rel(panel_path), "panel_sha256": sha256(panel_path), "panel_index": panel_index})
    return panels


def model_files() -> list[dict[str, Any]]:
    model_dir = MODEL_ROOT / "models" / "buffalo_l"
    records = []
    for path in sorted(model_dir.glob("*.onnx")):
        records.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    records, staged, source_evidence = collect_records()
    samples, detection_evidence = detect_samples(records, staged)
    route_records, samples_by_route, best_route_name, best_route = evaluate(samples)
    best = route_records[0]
    panels = make_panels(samples, best_route_name, best_route)
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "InsightFace runtime 106-point landmark eye route evaluation against LaPa gold eye labels",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_evidence": rel(source_evidence),
        "landmark_source": "insightface buffalo_l landmark_2d_106 runtime detection",
        "model_root": rel(MODEL_ROOT),
        "model_files": model_files(),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "detection_evidence": detection_evidence,
        "sample_count": len(samples),
        "route_family": (
            "eye-center windows, ellipses, fixed InsightFace 106-index eye hulls, "
            "and parser-constrained hybrids against LaPa gold eye labels"
        ),
        "route_count": len(route_records),
        "best_route": best_route_name,
        "best_summary": best["summary"],
        "best_pass_gate": best["pass_gate"],
        "best_failed_reasons": best["failed_reasons"],
        "best_sample_metrics": samples_by_route[best_route_name],
        "route_records": route_records[:100],
        "review_panels": panels,
        "result": (
            "insightface_106_eye_candidate_found_no_promotion"
            if best["pass_gate"]
            else "insightface_106_eye_routes_blocked_no_promotion"
        ),
        "next_required_action": (
            "If candidate found, run combined-gold and target-source visual review before promotion. "
            "If blocked, inspect panels and either derive a better 106-point index map/manual high-zoom trace policy or switch rows."
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
                "sample_count": evidence["sample_count"],
                "route_count": evidence["route_count"],
                "best_route": evidence["best_route"],
                "best_summary": evidence["best_summary"],
                "best_pass_gate": evidence["best_pass_gate"],
                "review_panels": panels,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
