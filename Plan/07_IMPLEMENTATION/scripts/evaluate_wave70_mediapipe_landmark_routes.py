#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260710T034800-0500"
TIMESTAMP = "2026-07-10T03:48:00-05:00"
BENCHMARK = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_STANDARD_BENCHMARK_20260710T012300-0500.json"
)
FACE_LANDMARKER_MODEL = Path(
    "runtime_artifacts/mask_factory/mediapipe_models/face_landmarker_float16_latest.task"
)
TARGET_REGIONS = [
    "mf70_eyebrows",
    "mf70_lips_top",
    "mf70_lips_bottom",
    "mf70_lips_combined",
]
THRESHOLDS = {
    "mean_iou": 0.85,
    "mean_false_positive_ratio_vs_gold": 0.15,
    "mean_false_negative_ratio_vs_gold": 0.15,
}

UPPER_LIP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78]
LOWER_LIP = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78]
LIPS_ALL = sorted(set(UPPER_LIP + LOWER_LIP))
LEFT_BROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_mask(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(path)
    return ((image > 0).astype(np.uint8)) * 255


def metrics(pred: np.ndarray, gold: np.ndarray) -> dict[str, Any]:
    p = pred > 0
    g = gold > 0
    intersection = int(np.logical_and(p, g).sum())
    union = int(np.logical_or(p, g).sum())
    pred_pixels = int(p.sum())
    gold_pixels = int(g.sum())
    fp = int(np.logical_and(p, ~g).sum())
    fn = int(np.logical_and(~p, g).sum())
    dice_den = pred_pixels + gold_pixels
    return {
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / dice_den, 6) if dice_den else 1.0,
        "pred_pixels": pred_pixels,
        "gold_pixels": gold_pixels,
        "false_positive_ratio_vs_gold": round(fp / gold_pixels, 6) if gold_pixels else 0.0,
        "false_negative_ratio_vs_gold": round(fn / gold_pixels, 6) if gold_pixels else 0.0,
    }


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def summarize(sample_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mean_iou": mean([m["iou"] for m in sample_metrics]),
        "mean_dice": mean([m["dice"] for m in sample_metrics]),
        "mean_false_positive_ratio_vs_gold": mean([m["false_positive_ratio_vs_gold"] for m in sample_metrics]),
        "mean_false_negative_ratio_vs_gold": mean([m["false_negative_ratio_vs_gold"] for m in sample_metrics]),
        "sample_count": len(sample_metrics),
    }


def passes(summary: dict[str, Any]) -> bool:
    return (
        summary["mean_iou"] >= THRESHOLDS["mean_iou"]
        and summary["mean_false_positive_ratio_vs_gold"] <= THRESHOLDS["mean_false_positive_ratio_vs_gold"]
        and summary["mean_false_negative_ratio_vs_gold"] <= THRESHOLDS["mean_false_negative_ratio_vs_gold"]
    )


def landmark_points(face_landmarks: Any, indices: list[int], width: int, height: int) -> np.ndarray:
    points = []
    for index in indices:
        lm = face_landmarks[index]
        points.append([int(round(lm.x * width)), int(round(lm.y * height))])
    return np.array(points, dtype=np.int32)


def polygon_mask(face_landmarks: Any, indices: list[int], width: int, height: int, dilate: int = 0) -> np.ndarray:
    points = landmark_points(face_landmarks, indices, width, height)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)
    if dilate:
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1, dilate * 2 + 1)))
    return mask


def stroke_mask(face_landmarks: Any, index_groups: list[list[int]], width: int, height: int, thickness: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for indices in index_groups:
        points = landmark_points(face_landmarks, indices, width, height)
        for a, b in zip(points[:-1], points[1:]):
            cv2.line(mask, tuple(a), tuple(b), 255, thickness=thickness, lineType=cv2.LINE_AA)
    return ((mask > 0).astype(np.uint8)) * 255


def region_mask(face_landmarks: Any, region: str, width: int, height: int, param: int) -> np.ndarray:
    if region == "mf70_lips_top":
        return polygon_mask(face_landmarks, UPPER_LIP, width, height, param)
    if region == "mf70_lips_bottom":
        return polygon_mask(face_landmarks, LOWER_LIP, width, height, param)
    if region == "mf70_lips_combined":
        return polygon_mask(face_landmarks, LIPS_ALL, width, height, param)
    if region == "mf70_eyebrows":
        return stroke_mask(face_landmarks, [LEFT_BROW, RIGHT_BROW], width, height, thickness=max(1, param))
    raise ValueError(region)


def label_tile(image: Image.Image, label: str, size: int = 220) -> Image.Image:
    tile = Image.new("RGB", (size, size + 30), (16, 16, 16))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.NEAREST), (0, 30))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    draw.text((6, 7), label, fill=(245, 245, 245), font=font)
    return tile


def error_image(pred: np.ndarray, gold: np.ndarray) -> Image.Image:
    p = pred > 0
    g = gold > 0
    out = np.zeros((*pred.shape, 3), dtype=np.uint8)
    out[np.logical_and(p, g)] = (255, 255, 255)
    out[np.logical_and(p, ~g)] = (255, 64, 64)
    out[np.logical_and(~p, g)] = (64, 160, 255)
    return Image.fromarray(out, mode="RGB")


def make_panel(root: Path, region: str, sample_id: int, source_path: Path, gold: np.ndarray, pred: np.ndarray) -> str:
    source = Image.open(source_path).convert("RGB")
    tiles = [
        label_tile(source, f"{sample_id} source"),
        label_tile(Image.fromarray(gold), "gold"),
        label_tile(Image.fromarray(pred), "mediapipe pred"),
        label_tile(error_image(pred, gold), "err white/hit red/fp blue/fn"),
    ]
    panel = Image.new("RGB", (220 * len(tiles), 250), (0, 0, 0))
    for i, tile in enumerate(tiles):
        panel.paste(tile, (220 * i, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mediapipe_landmark_routes" / RUN_STAMP
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{region}_mediapipe_route_panel.png"
    panel.save(out_path)
    return rel(out_path, root)


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root
    benchmark = read_json(resolve(root, BENCHMARK))
    model_path = resolve(root, FACE_LANDMARKER_MODEL)
    if not model_path.exists():
        raise FileNotFoundError(f"MediaPipe FaceLandmarker model missing: {FACE_LANDMARKER_MODEL.as_posix()}")
    staged_by_sample = {int(item["sample_id"]): Path(item["staged_image"]) for item in benchmark["staged_inputs"]}

    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    face_landmarker = FaceLandmarker.create_from_options(options)
    landmark_by_sample: dict[int, Any] = {}
    image_shape_by_sample: dict[int, tuple[int, int]] = {}
    for sample_id, staged in staged_by_sample.items():
        image_path = resolve(root, staged)
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(image_path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = face_landmarker.detect(mp_image)
        if not result.face_landmarks:
            raise RuntimeError(f"MediaPipe found no face for sample {sample_id}")
        landmark_by_sample[sample_id] = result.face_landmarks[0]
        image_shape_by_sample[sample_id] = (bgr.shape[1], bgr.shape[0])

    records_out = []
    candidate_regions = []
    still_blocked = []
    for region in TARGET_REGIONS:
        region_records = [r for r in benchmark["comparison_records"] if r["region"] == region]
        best: dict[str, Any] | None = None
        params = range(1, 18, 2) if region == "mf70_eyebrows" else range(0, 8)
        for param in params:
            sample_metrics = []
            sample_preds: dict[int, np.ndarray] = {}
            for record in region_records:
                sample_id = int(record["sample_id"])
                width, height = image_shape_by_sample[sample_id]
                pred = region_mask(landmark_by_sample[sample_id], region, width, height, param)
                gold = load_mask(resolve(root, record["gold_comparison_mask"]))
                sample_metrics.append({"sample_id": sample_id, **metrics(pred, gold)})
                sample_preds[sample_id] = pred
            summary = summarize(sample_metrics)
            candidate = {"param": param, "summary": summary, "sample_metrics": sample_metrics, "sample_preds": sample_preds}
            if best is None or summary["mean_iou"] > best["summary"]["mean_iou"]:
                best = candidate
        assert best is not None
        best_pass = passes(best["summary"])
        if best_pass:
            candidate_regions.append(region)
        else:
            still_blocked.append(region)
        worst = min(best["sample_metrics"], key=lambda row: row["iou"])
        worst_record = next(r for r in region_records if int(r["sample_id"]) == int(worst["sample_id"]))
        panel = make_panel(
            root,
            region,
            int(worst["sample_id"]),
            resolve(root, staged_by_sample[int(worst["sample_id"])]),
            load_mask(resolve(root, worst_record["gold_comparison_mask"])),
            best["sample_preds"][int(worst["sample_id"])],
        )
        records_out.append(
            {
                "region": region,
                "route": "mediapipe_face_mesh_landmarks",
                "best_param": best["param"],
                "postprocess_summary": best["summary"],
                "sample_records": best["sample_metrics"],
                "passes_current_gold_gate": best_pass,
                "diagnostic_panel": panel,
                "decision": "candidate_route_found_pending_target_specific_qa" if best_pass else "blocked_mediapipe_route_not_sufficient",
            }
        )

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MEDIAPIPE-LANDMARK-ROUTE-EVAL-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "local_gold_benchmark_mediapipe_landmark_route_evaluation_only",
        "benchmark_evidence": rel(resolve(root, BENCHMARK), root),
        "benchmark_sha256": sha256_file(resolve(root, BENCHMARK)),
        "mediapipe_model": rel(model_path, root),
        "mediapipe_model_sha256": sha256_file(model_path),
        "thresholds": THRESHOLDS,
        "target_regions": TARGET_REGIONS,
        "route_records": records_out,
        "candidate_routes_found": candidate_regions,
        "still_blocked_after_mediapipe": still_blocked,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "mediapipe_landmark_routes_evaluated_no_promotion",
        "next_required_action": "Use only regions that pass the gold benchmark for target-specific candidate creation; record blockers for the rest.",
    }
    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MEDIAPIPE_LANDMARK_ROUTE_EVAL_{RUN_STAMP}.json"
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 MediaPipe Landmark Route Evaluation - {TIMESTAMP}

Evaluated local MediaPipe FaceMesh landmark routes for remaining eyebrows/lip rows against the same MaskedWarehouse gold samples. Evidence `{rel(out, root)}` reports `{evidence['result']}`. Candidate routes found: `{', '.join(candidate_regions) if candidate_regions else 'none'}`. Still blocked after MediaPipe: `{', '.join(still_blocked) if still_blocked else 'none'}`. No active input, mask promotion, generation, EC2, AWS, GitHub, S3, Civitai, row completion, or certification occurred.
"""
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)

    print(json.dumps({"result": evidence["result"], "candidate_routes_found": candidate_regions, "still_blocked_after_mediapipe": still_blocked, "evidence": rel(out, root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
