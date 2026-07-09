#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
COMFY_INPUT = PROJECT_ROOT / "ComfyUI/input"
EVIDENCE_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_ROOT = PROJECT_ROOT / "runtime_artifacts/mask_factory"

EYE_FAMILY_MASKS = [
    "mf70_left_eye",
    "mf70_right_eye",
    "mf70_pupils_iris_sclera",
    "mf70_eyelids",
    "mf70_eyelashes",
    "mf70_eyebrows",
]

FACE_CROP = (170, 245, 560, 380)
VIEWER_LEFT_EYE_CROP = (205, 278, 360, 360)
VIEWER_RIGHT_EYE_CROP = (385, 278, 540, 360)
HAIR_OCCLUDED_VIEWER_LEFT_REVIEW_ZONE = (175, 250, 285, 375)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_font(size: int = 16) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def label_tile(image: Image.Image, label: str, width: int = 420) -> Image.Image:
    image = image.convert("RGB")
    height = max(1, round(image.height * (width / image.width)))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height + 34), (18, 18, 18))
    tile.paste(resized, (0, 34))
    draw = ImageDraw.Draw(tile)
    draw.text((8, 9), label, fill=(245, 245, 245), font=load_font(16))
    return tile


def paste_grid(tiles: list[Image.Image], cols: int, path: Path) -> None:
    rows = (len(tiles) + cols - 1) // cols
    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    panel = Image.new("RGB", (cols * width, rows * height), (0, 0, 0))
    for index, tile in enumerate(tiles):
        x = (index % cols) * width
        y = (index // cols) * height
        panel.paste(tile, (x, y))
    path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(path)


def draw_coordinate_grid(image: Image.Image, crop: tuple[int, int, int, int], step: int = 20) -> Image.Image:
    out = image.crop(crop).convert("RGB")
    draw = ImageDraw.Draw(out)
    font = load_font(11)
    x0, y0, x1, y1 = crop
    for x in range(((x0 + step - 1) // step) * step, x1 + 1, step):
        local_x = x - x0
        draw.line([(local_x, 0), (local_x, out.height)], fill=(255, 255, 0), width=1)
        draw.text((local_x + 2, 2), str(x), fill=(255, 255, 0), font=font)
    for y in range(((y0 + step - 1) // step) * step, y1 + 1, step):
        local_y = y - y0
        draw.line([(0, local_y), (out.width, local_y)], fill=(0, 255, 170), width=1)
        draw.text((2, local_y + 2), str(y), fill=(0, 255, 170), font=font)
    return out


def canny_crop(source: Image.Image, crop: tuple[int, int, int, int]) -> Image.Image:
    arr = np.array(source.crop(crop).convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    edges = cv2.Canny(gray, 40, 110)
    edge_rgb = np.zeros((edges.shape[0], edges.shape[1], 3), dtype=np.uint8)
    edge_rgb[..., 1] = edges
    base = arr.copy()
    mixed = cv2.addWeighted(base, 0.62, edge_rgb, 0.75, 0)
    return Image.fromarray(mixed)


def mask_bbox(mask: Image.Image) -> list[int] | None:
    arr = np.array(mask.convert("L"))
    ys, xs = np.where(arr > 0)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def overlay_mask(source: Image.Image, mask: Image.Image, crop: tuple[int, int, int, int], color: tuple[int, int, int]) -> Image.Image:
    base = source.convert("RGBA")
    alpha = mask.convert("L").point(lambda value: 125 if value > 8 else 0)
    fill = Image.new("RGBA", source.size, (*color, 0))
    fill.putalpha(alpha)
    return Image.alpha_composite(base, fill).convert("RGB").crop(crop)


def count_mask_in_rect(mask: Image.Image, rect: tuple[int, int, int, int]) -> int:
    return int(np.count_nonzero(np.array(mask.convert("L").crop(rect)) > 0))


def detect_haar_regions(source_path: Path) -> dict[str, Any]:
    bgr = cv2.imread(str(source_path))
    if bgr is None:
        raise RuntimeError(f"Could not read source image: {source_path}")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")
    faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(160, 160))
    eyes = eye_cascade.detectMultiScale(gray, 1.05, 4, minSize=(20, 15), maxSize=(100, 65))
    return {
        "face_boxes_xywh": [[int(v) for v in box] for box in faces],
        "eye_boxes_xywh": [[int(v) for v in box] for box in eyes],
        "detected_eye_count": int(len(eyes)),
    }


def draw_detection_panel(source: Image.Image, detections: dict[str, Any]) -> Image.Image:
    out = source.crop(FACE_CROP).convert("RGB")
    draw = ImageDraw.Draw(out)
    x0, y0, _, _ = FACE_CROP
    for x, y, w, h in detections["eye_boxes_xywh"]:
        draw.rectangle([x - x0, y - y0, x + w - x0, y + h - y0], outline=(0, 255, 0), width=4)
        draw.text((x - x0, max(0, y - y0 - 18)), "detected eye", fill=(0, 255, 0), font=load_font(14))
    hx0, hy0, hx1, hy1 = HAIR_OCCLUDED_VIEWER_LEFT_REVIEW_ZONE
    draw.rectangle([hx0 - x0, hy0 - y0, hx1 - x0, hy1 - y0], outline=(255, 200, 0), width=4)
    draw.text((hx0 - x0, hy0 - y0 - 18), "hair-occluded side: no auto pass", fill=(255, 200, 0), font=load_font(14))
    return out


def current_mask_tiles(source: Image.Image) -> tuple[list[Image.Image], list[dict[str, Any]]]:
    tiles: list[Image.Image] = []
    records: list[dict[str, Any]] = []
    colors = {
        "mf70_left_eye": (255, 30, 30),
        "mf70_right_eye": (30, 220, 255),
        "mf70_pupils_iris_sclera": (180, 80, 255),
        "mf70_eyelids": (255, 110, 30),
        "mf70_eyelashes": (255, 255, 255),
        "mf70_eyebrows": (0, 255, 80),
    }
    for mask_id in EYE_FAMILY_MASKS:
        path = COMFY_INPUT / f"wave70_{mask_id}_mask.png"
        if not path.exists():
            records.append({"mask_type_id": mask_id, "exists": False})
            continue
        mask = Image.open(path).convert("L")
        bbox = mask_bbox(mask)
        hair_hits = count_mask_in_rect(mask, HAIR_OCCLUDED_VIEWER_LEFT_REVIEW_ZONE)
        records.append(
            {
                "mask_type_id": mask_id,
                "exists": True,
                "path": rel(path),
                "sha256": sha256_file(path),
                "bbox": bbox,
                "hair_occluded_viewer_left_zone_hits": hair_hits,
                "nonzero_pixels": int(np.count_nonzero(np.array(mask) > 0)),
            }
        )
        overlay = overlay_mask(source, mask, FACE_CROP, colors[mask_id])
        tiles.append(label_tile(overlay, f"current disputed overlay: {mask_id}", width=420))
    return tiles, records


def main() -> int:
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    stamp = stamp[:-2] + ":" + stamp[-2:]
    file_stamp = stamp.replace(":", "")
    runtime_dir = RUNTIME_ROOT / f"wave70_eye_boundary_trace_template_{file_stamp}"
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    detections = detect_haar_regions(SOURCE_IMAGE)

    source_tiles = [
        label_tile(draw_coordinate_grid(source, FACE_CROP), "source crop with absolute coordinate grid", width=520),
        label_tile(draw_detection_panel(source, detections), "source-derived Haar eye detection and hair-occlusion review zone", width=520),
        label_tile(canny_crop(source, VIEWER_LEFT_EYE_CROP), "viewer-left eye/hair crop + Canny edge assist", width=520),
        label_tile(canny_crop(source, VIEWER_RIGHT_EYE_CROP), "viewer-right eye crop + Canny edge assist", width=520),
    ]
    current_tiles, mask_records = current_mask_tiles(source)

    trace_panel = runtime_dir / "wave70_eye_boundary_source_trace_template_panel.png"
    current_overlay_panel = runtime_dir / "wave70_eye_family_current_disputed_mask_overlays.png"
    paste_grid(source_tiles, 2, trace_panel)
    paste_grid(current_tiles, 2, current_overlay_panel)

    template_payload = {
        "schema_version": "1.0",
        "created_local": stamp,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "coordinate_system": "absolute source-image pixels, origin at upper-left, image size 768x768",
        "trace_regions": {
            "face_crop": list(FACE_CROP),
            "viewer_left_eye_crop": list(VIEWER_LEFT_EYE_CROP),
            "viewer_right_eye_crop": list(VIEWER_RIGHT_EYE_CROP),
            "hair_occluded_viewer_left_review_zone": list(HAIR_OCCLUDED_VIEWER_LEFT_REVIEW_ZONE),
        },
        "manual_trace_slots": {
            "viewer_left_visible_eye_aperture": [],
            "viewer_right_visible_eye_aperture": [],
            "viewer_left_visible_brow_hair": [],
            "viewer_right_visible_brow_hair": [],
            "viewer_left_lid_folds": [],
            "viewer_right_lid_folds": [],
            "viewer_left_hair_occlusion_boundary": [],
        },
        "rule": "Do not promote eye-family masks from rectangles, symmetry, or generated-output proof. Fill trace slots only after high-zoom visual inspection or a reliable source-derived landmark/segmentation method.",
    }
    template_path = runtime_dir / "wave70_eye_boundary_manual_trace_template.json"
    write_json(template_path, template_payload)

    detected_eye_count = detections["detected_eye_count"]
    result = (
        "blocked_manual_or_better_source_derived_trace_required"
        if detected_eye_count < 2
        else "diagnostic_only_two_eye_detector_regions_present_requires_visual_trace_review"
    )
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70_EYE_BOUNDARY_TRACE_TEMPLATE_{file_stamp}",
        "created_local": stamp,
        "task": "Wave70 eye-family source-boundary diagnostic after user-reported eye/brow geometry drift into hair",
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "affected_mask_type_ids": EYE_FAMILY_MASKS,
        "result": result,
        "promotion_decision": "no_eye_family_mask_promoted_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "detector": {
            "name": "OpenCV Haar frontal face + eye-tree-eyeglasses",
            "face_boxes_xywh": detections["face_boxes_xywh"],
            "eye_boxes_xywh": detections["eye_boxes_xywh"],
            "detected_eye_count": detected_eye_count,
            "decision": "not_sufficient_for_eye_family_acceptance" if detected_eye_count < 2 else "diagnostic_only_not_acceptance",
        },
        "user_dispute_response": "User is correct that current eye-family boundaries must not be accepted while visible eye/brow geometry runs into the hair mass. This evidence fails closed and creates a trace template instead of another guessed polygon.",
        "artifacts": {
            "source_trace_panel": rel(trace_panel),
            "current_disputed_mask_overlay_panel": rel(current_overlay_panel),
            "manual_trace_template": rel(template_path),
        },
        "current_mask_records": mask_records,
        "required_next_step": "Complete source-derived segmentation/landmark extraction or fill the high-zoom manual trace slots for visible eye apertures, brows, eyelids, lashes, and hair occlusion before generating any new eye-family mask.",
        "forbidden_next_step": "Do not run generated-output proof, target-runtime proof, row promotion, or hand-guessed eye polygons for these rows.",
    }

    evidence_path = EVIDENCE_DIR / f"W70_EYE_BOUNDARY_TRACE_TEMPLATE_{file_stamp}.json"
    tracker_path = TRACKER_EVIDENCE_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    shutil.copy2(evidence_path, tracker_path)
    print(json.dumps({"evidence": str(evidence_path), "tracker_evidence": str(tracker_path), "trace_panel": str(trace_panel), "overlay_panel": str(current_overlay_panel)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
