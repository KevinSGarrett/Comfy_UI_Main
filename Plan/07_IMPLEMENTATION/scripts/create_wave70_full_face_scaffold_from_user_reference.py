#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260708T001500-0500"

SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
USER_REFERENCE_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_user_geometry_reference_20260707T235800-0500"
USER_SCAFFOLD_REFERENCE = USER_REFERENCE_DIR / "user_reference_full_face_geometry_scaffold.png"
USER_SEMANTIC_REFERENCE = USER_REFERENCE_DIR / "user_reference_semantic_mask_regions.png"

RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_full_face_scaffold_from_user_reference" / RUN_STAMP
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_FULL_FACE_SCAFFOLD_FROM_USER_REFERENCE_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_FULL_FACE_SCAFFOLD_FROM_USER_REFERENCE_{RUN_STAMP}.json"
)

SCAFFOLD_LAYERS = {
    "visible_face_contour": {
        "target_rgb": (128, 0, 16),
        "threshold": 78,
        "overlay_rgb": (255, 0, 32),
        "meaning": "user red visible-face contour excluding hair mass and defining forehead, cheek, jaw, and chin envelope",
    },
    "eye_band": {
        "target_rgb": (240, 240, 0),
        "threshold": 82,
        "overlay_rgb": (255, 245, 0),
        "meaning": "user yellow bilateral eye band and bridge-level eye-plane scaffold",
    },
    "nose_guides": {
        "target_rgb": (32, 176, 64),
        "threshold": 76,
        "overlay_rgb": (0, 220, 90),
        "meaning": "user green nose axis and side guide strokes",
    },
    "mouth_lip_guides": {
        "target_rgb": (0, 160, 224),
        "threshold": 86,
        "overlay_rgb": (0, 190, 255),
        "meaning": "user cyan mouth/lip polygon and associated guide strokes",
    },
    "brow_forehead_separator": {
        "target_rgb": (240, 160, 192),
        "threshold": 78,
        "overlay_rgb": (255, 160, 210),
        "meaning": "user pink brow/forehead separator guide",
    },
}

SEMANTIC_LAYERS = {
    "semantic_visible_face_skin_region": {
        "quantized_targets": [
            (112, 80, 96),
            (128, 80, 96),
            (128, 96, 96),
            (144, 96, 96),
            (144, 96, 112),
            (160, 96, 112),
            (160, 112, 112),
            (176, 112, 112),
            (176, 128, 128),
            (176, 128, 144),
            (192, 128, 128),
            (192, 128, 144),
            (192, 144, 144),
        ],
        "quantized_threshold": 28,
        "bounds": (185, 160, 485, 565),
        "overlay_rgb": (230, 150, 170),
        "meaning": "large translucent face-skin/facial-contour region from user semantic reference",
    },
    "semantic_neck_region": {
        "quantized_targets": [
            (176, 112, 112),
            (176, 128, 128),
            (192, 128, 128),
            (192, 128, 144),
            (192, 144, 144),
            (208, 144, 160),
            (224, 144, 160),
        ],
        "quantized_threshold": 30,
        "bounds": (180, 430, 430, 768),
        "overlay_rgb": (240, 155, 175),
        "meaning": "translucent neck and lower exposed-skin region from user semantic reference",
    },
    "semantic_nose_region": {
        "quantized_targets": [
            (64, 0, 16),
            (80, 0, 16),
            (96, 0, 16),
            (96, 16, 16),
            (112, 0, 16),
            (112, 32, 32),
            (128, 16, 16),
            (128, 16, 32),
            (128, 32, 32),
            (144, 32, 32),
        ],
        "quantized_threshold": 24,
        "bounds": (300, 300, 405, 430),
        "overlay_rgb": (210, 10, 45),
        "meaning": "red nose mask region from user semantic reference",
    },
    "semantic_eye_regions": {
        "quantized_targets": [
            (0, 80, 112),
            (16, 80, 112),
            (16, 128, 176),
            (32, 96, 32),
            (32, 96, 48),
            (32, 96, 112),
            (32, 96, 128),
            (32, 128, 48),
            (32, 128, 64),
            (32, 144, 64),
            (48, 112, 48),
            (48, 112, 64),
            (48, 112, 128),
            (176, 176, 0),
            (192, 176, 0),
        ],
        "quantized_threshold": 26,
        "bounds": (260, 295, 465, 355),
        "overlay_rgb": (0, 185, 255),
        "meaning": "user semantic eye-region colors constrained to the shared eye band",
    },
    "semantic_brow_regions": {
        "quantized_targets": [
            (176, 112, 128),
            (176, 112, 144),
            (192, 128, 144),
            (208, 128, 144),
            (224, 144, 160),
        ],
        "quantized_threshold": 24,
        "bounds": (250, 260, 490, 315),
        "overlay_rgb": (255, 135, 210),
        "meaning": "pink brow regions from user semantic reference, bounded above the eye band",
    },
    "semantic_lip_regions": {
        "quantized_targets": [
            (96, 32, 80),
            (112, 48, 80),
            (112, 48, 96),
            (128, 48, 96),
            (128, 64, 96),
            (128, 64, 112),
            (128, 64, 128),
            (144, 16, 16),
            (144, 64, 112),
            (144, 64, 128),
            (144, 80, 128),
            (160, 32, 32),
            (176, 16, 16),
            (176, 48, 48),
            (192, 32, 32),
        ],
        "quantized_threshold": 26,
        "bounds": (290, 430, 410, 495),
        "overlay_rgb": (225, 35, 80),
        "meaning": "upper/lower lip regions from user semantic reference",
    },
}


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


def font(size: int = 15) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def ensure_same_size(images: list[Image.Image]) -> None:
    sizes = {image.size for image in images}
    if len(sizes) != 1:
        raise ValueError(f"Input images must share dimensions; got {sorted(sizes)}")


def diff_mask(source_rgb: np.ndarray, reference_rgb: np.ndarray, threshold: int = 35) -> np.ndarray:
    source_i = source_rgb.astype(np.int16)
    reference_i = reference_rgb.astype(np.int16)
    return np.max(np.abs(reference_i - source_i), axis=2) > threshold


def target_color_mask(
    source_rgb: np.ndarray,
    reference_rgb: np.ndarray,
    target_rgb: tuple[int, int, int],
    threshold: int,
) -> np.ndarray:
    changed = diff_mask(source_rgb, reference_rgb)
    delta = reference_rgb.astype(np.int32) - np.array(target_rgb, dtype=np.int32)
    distance_squared = np.sum(delta * delta, axis=2)
    return changed & (distance_squared <= threshold * threshold)


def quantized_group_mask(
    source_rgb: np.ndarray,
    reference_rgb: np.ndarray,
    targets: list[tuple[int, int, int]],
    threshold: int,
    bounds: tuple[int, int, int, int] | None,
) -> np.ndarray:
    changed = diff_mask(source_rgb, reference_rgb)
    quantized = (reference_rgb // 16) * 16
    mask = np.zeros(changed.shape, dtype=bool)
    q_int = quantized.astype(np.int32)
    for target in targets:
        delta = q_int - np.array(target, dtype=np.int32)
        distance_squared = np.sum(delta * delta, axis=2)
        mask |= distance_squared <= threshold * threshold
    mask &= changed
    if bounds is not None:
        x0, y0, x1, y1 = bounds
        bounded = np.zeros_like(mask)
        bounded[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
        mask = bounded
    return mask


def stats_for_mask(mask: np.ndarray) -> dict[str, Any]:
    mask_u8 = mask.astype(np.uint8)
    pixel_count = int(mask_u8.sum())
    if pixel_count == 0:
        return {
            "pixel_count": 0,
            "coverage_percent": 0.0,
            "bbox_xyxy": None,
            "connected_component_count": 0,
            "largest_components": [],
        }
    ys, xs = np.where(mask_u8 > 0)
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
    components = []
    for component_id in range(1, component_count):
        x, y, w, h, area = stats[component_id]
        components.append(
            {
                "component_id": int(component_id),
                "bbox_xyxy": [int(x), int(y), int(x + w - 1), int(y + h - 1)],
                "area_pixels": int(area),
            }
        )
    components.sort(key=lambda item: item["area_pixels"], reverse=True)
    return {
        "pixel_count": pixel_count,
        "coverage_percent": round(pixel_count * 100.0 / mask_u8.size, 5),
        "bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        "connected_component_count": int(component_count - 1),
        "largest_components": components[:12],
    }


def save_mask(mask: np.ndarray, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)
    return rel(path)


def overlay_layers(
    base: Image.Image,
    layers: dict[str, dict[str, Any]],
    alpha: int = 165,
    line_boost: bool = False,
) -> Image.Image:
    overlay = base.convert("RGBA")
    for layer in layers.values():
        mask = layer["mask"]
        color = layer["overlay_rgb"]
        color_layer = np.zeros((base.height, base.width, 4), dtype=np.uint8)
        color_layer[mask, 0] = color[0]
        color_layer[mask, 1] = color[1]
        color_layer[mask, 2] = color[2]
        color_layer[mask, 3] = alpha
        overlay = Image.alpha_composite(overlay, Image.fromarray(color_layer, mode="RGBA"))
        if line_boost:
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour_img = np.zeros((base.height, base.width, 4), dtype=np.uint8)
            cv2.drawContours(contour_img, contours, -1, (*color, 255), 2)
            overlay = Image.alpha_composite(overlay, Image.fromarray(contour_img, mode="RGBA"))
    return overlay.convert("RGB")


def label_tile(image: Image.Image, label: str) -> Image.Image:
    tile = Image.new("RGB", (image.width, image.height + 34), (18, 18, 18))
    tile.paste(image.convert("RGB"), (0, 34))
    draw = ImageDraw.Draw(tile)
    draw.text((8, 9), label, fill=(245, 245, 245), font=font(15))
    return tile


def resize_for_panel(image: Image.Image, width: int = 384) -> Image.Image:
    height = int(round(image.height * width / image.width))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_contact_sheet(scaffold_layers: dict[str, dict[str, Any]], semantic_layers: dict[str, dict[str, Any]]) -> Image.Image:
    all_layers = {**scaffold_layers, **semantic_layers}
    cell_w, cell_h = 256, 256
    labels_h = 34
    cols = 3
    rows = int(np.ceil(len(all_layers) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + labels_h)), (0, 0, 0))
    for index, (name, layer) in enumerate(all_layers.items()):
        row, col = divmod(index, cols)
        mask = Image.fromarray((layer["mask"].astype(np.uint8) * 255), mode="L").resize((cell_w, cell_h), Image.Resampling.NEAREST)
        color = layer["overlay_rgb"]
        tile = Image.new("RGB", (cell_w, cell_h + labels_h), (18, 18, 18))
        colored = Image.new("RGB", (cell_w, cell_h), color)
        dark = Image.new("RGB", (cell_w, cell_h), (12, 12, 12))
        dark.paste(colored, mask=mask)
        tile.paste(dark, (0, labels_h))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 8), name[:38], fill=(245, 245, 245), font=font(13))
        sheet.paste(tile, (col * cell_w, row * (cell_h + labels_h)))
    return sheet


def make_panel(
    source: Image.Image,
    user_scaffold: Image.Image,
    user_semantic: Image.Image,
    scaffold_layers: dict[str, dict[str, Any]],
    semantic_layers: dict[str, dict[str, Any]],
    panel_path: Path,
) -> None:
    scaffold_overlay = overlay_layers(source, scaffold_layers, alpha=205, line_boost=True)
    semantic_overlay = overlay_layers(source, semantic_layers, alpha=125, line_boost=True)
    contact_sheet = make_contact_sheet(scaffold_layers, semantic_layers)
    tiles = [
        label_tile(resize_for_panel(source), "clean source"),
        label_tile(resize_for_panel(user_scaffold), "user scaffold reference"),
        label_tile(resize_for_panel(scaffold_overlay), "extracted scaffold over source"),
        label_tile(resize_for_panel(user_semantic), "user semantic reference"),
        label_tile(resize_for_panel(semantic_overlay), "extracted semantic regions over source"),
        label_tile(resize_for_panel(contact_sheet, 768), "extracted layer contact sheet"),
    ]
    row1_w = sum(tile.width for tile in tiles[:3])
    row2_w = sum(tile.width for tile in tiles[3:5])
    width = max(row1_w, row2_w, tiles[5].width)
    height = max(tile.height for tile in tiles[:3]) + max(tile.height for tile in tiles[3:5]) + tiles[5].height
    panel = Image.new("RGB", (width, height), (0, 0, 0))
    x = 0
    for tile in tiles[:3]:
        panel.paste(tile, (x, 0))
        x += tile.width
    y2 = max(tile.height for tile in tiles[:3])
    x = 0
    for tile in tiles[3:5]:
        panel.paste(tile, (x, y2))
        x += tile.width
    panel.paste(tiles[5], (0, y2 + max(tile.height for tile in tiles[3:5])))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def build_layer_records(
    source_rgb: np.ndarray,
    scaffold_rgb: np.ndarray,
    semantic_rgb: np.ndarray,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    scaffold_layers: dict[str, dict[str, Any]] = {}
    for name, config in SCAFFOLD_LAYERS.items():
        mask = target_color_mask(source_rgb, scaffold_rgb, config["target_rgb"], config["threshold"])
        scaffold_layers[name] = {
            "mask": mask,
            "overlay_rgb": config["overlay_rgb"],
            "meaning": config["meaning"],
            "extraction": {
                "method": "source_reference_difference_plus_nearest_annotation_color",
                "target_rgb": list(config["target_rgb"]),
                "rgb_distance_threshold": config["threshold"],
                "changed_pixel_threshold": 35,
            },
        }
    semantic_layers: dict[str, dict[str, Any]] = {}
    for name, config in SEMANTIC_LAYERS.items():
        mask = quantized_group_mask(
            source_rgb,
            semantic_rgb,
            config["quantized_targets"],
            config["quantized_threshold"],
            config["bounds"],
        )
        semantic_layers[name] = {
            "mask": mask,
            "overlay_rgb": config["overlay_rgb"],
            "meaning": config["meaning"],
            "extraction": {
                "method": "source_reference_difference_plus_quantized_annotation_color_groups",
                "quantized_targets": [list(item) for item in config["quantized_targets"]],
                "quantized_distance_threshold": config["quantized_threshold"],
                "changed_pixel_threshold": 35,
                "bounds_xyxy": list(config["bounds"]) if config["bounds"] is not None else None,
            },
        }
    return scaffold_layers, semantic_layers


def serialize_layers(layers: dict[str, dict[str, Any]], mask_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, layer in layers.items():
        mask_path = mask_dir / f"{name}.png"
        out[name] = {
            "meaning": layer["meaning"],
            "overlay_rgb": list(layer["overlay_rgb"]),
            "mask_path": save_mask(layer["mask"], mask_path),
            "mask_sha256": sha256_file(mask_path),
            "stats": stats_for_mask(layer["mask"]),
            "extraction": layer["extraction"],
        }
    return out


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    user_scaffold = Image.open(USER_SCAFFOLD_REFERENCE).convert("RGB")
    user_semantic = Image.open(USER_SEMANTIC_REFERENCE).convert("RGB")
    ensure_same_size([source, user_scaffold, user_semantic])

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    copied_refs_dir = RUNTIME_DIR / "reference_inputs"
    copied_refs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(USER_SCAFFOLD_REFERENCE, copied_refs_dir / USER_SCAFFOLD_REFERENCE.name)
    shutil.copy2(USER_SEMANTIC_REFERENCE, copied_refs_dir / USER_SEMANTIC_REFERENCE.name)

    source_rgb = np.array(source)
    scaffold_rgb = np.array(user_scaffold)
    semantic_rgb = np.array(user_semantic)

    scaffold_layers, semantic_layers = build_layer_records(source_rgb, scaffold_rgb, semantic_rgb)
    mask_dir = RUNTIME_DIR / "masks"
    scaffold_serialized = serialize_layers(scaffold_layers, mask_dir / "scaffold")
    semantic_serialized = serialize_layers(semantic_layers, mask_dir / "semantic")

    panel_path = RUNTIME_DIR / "wave70_full_face_scaffold_from_user_reference_panel.png"
    make_panel(source, user_scaffold, user_semantic, scaffold_layers, semantic_layers, panel_path)

    manifest_path = RUNTIME_DIR / "wave70_full_face_scaffold_from_user_reference_manifest.json"
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_FULL_FACE_SCAFFOLD_FROM_USER_REFERENCE_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "task": "Extract a full visible-face scaffold from the user annotated references before deriving any more Wave70 subregion masks.",
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": list(source.size),
        },
        "user_references": {
            "full_face_geometry_scaffold": {
                "path": rel(USER_SCAFFOLD_REFERENCE),
                "sha256": sha256_file(USER_SCAFFOLD_REFERENCE),
                "dimensions": list(user_scaffold.size),
            },
            "semantic_mask_regions": {
                "path": rel(USER_SEMANTIC_REFERENCE),
                "sha256": sha256_file(USER_SEMANTIC_REFERENCE),
                "dimensions": list(user_semantic.size),
            },
        },
        "runtime_artifacts": {
            "runtime_dir": rel(RUNTIME_DIR),
            "panel": rel(panel_path),
            "manifest": rel(manifest_path),
        },
        "extraction_method": [
            "All layers are extracted from changed pixels between the clean source and user annotated reference images.",
            "Scaffold line layers use nearest-color extraction against the user drawing colors.",
            "Semantic layers use quantized changed-color groups plus bounded anatomical regions to keep face, neck, eyes, brows, nose, and lips separated.",
            "This scaffold is reference evidence only. It is not a promoted ComfyUI input mask and does not satisfy any row promotion gate by itself.",
        ],
        "scaffold_layers": scaffold_serialized,
        "semantic_layers": semantic_serialized,
        "qa_position": {
            "status": "extracted_pending_strict_visual_review",
            "promotion_decision": "no_mask_promoted_no_active_input_changed_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
            "must_not_use_as": "automatic pass mask or replacement for row-specific geometry/protected-overlap/generated-output QA",
            "next_use": "Use the visually reviewed scaffold to derive future face-detail candidate masks from the full visible-face geometry first.",
        },
        "correction_rules_applied": [
            "Visible face contour and hair occlusion must be established before eye/brow/nose/mouth subregions.",
            "Eye and brow rows must be constrained by the shared bilateral eye band instead of isolated local crop boxes.",
            "Nose rows must be constrained by the face centerline and side guides.",
            "Mouth/lip rows must be constrained by the mouth plane/lip polygon.",
            "Face/neck rows must preserve the face-neck separation visible in the semantic reference.",
        ],
    }
    write_json(manifest_path, payload)
    write_json(QA_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    print(json.dumps({"qa_evidence": rel(QA_EVIDENCE), "panel": rel(panel_path), "manifest": rel(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
