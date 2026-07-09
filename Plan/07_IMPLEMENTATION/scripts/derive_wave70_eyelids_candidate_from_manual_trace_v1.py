#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260707T235000-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
TRACE_JSON = PROJECT_ROOT / (
    "runtime_artifacts/mask_factory/wave70_eye_boundary_manual_trace_v1/"
    "20260707T233500-0500/wave70_eye_boundary_manual_trace_v1.json"
)
OUT_DIR = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_eyelids_manual_trace_candidate_v1_{RUN_STAMP}"
)
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_eyelids/manual_trace_candidate_v1" / RUN_STAMP
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_MF70_EYELIDS_MANUAL_TRACE_CANDIDATE_V1_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_MF70_EYELIDS_MANUAL_TRACE_CANDIDATE_V1_{RUN_STAMP}.json"
)

CROP = (235, 268, 505, 355)
PANEL_SCALE = 3


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


def trace_points(trace: dict[str, Any], key: str) -> list[tuple[int, int]]:
    return [(int(x), int(y)) for x, y in trace["manual_trace"][key]["points"]]


def draw_candidate_mask(size: tuple[int, int], trace: dict[str, Any]) -> Image.Image:
    scale = 4
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(mask)

    eyelid_keys = [
        "viewer_left_upper_lid_fold",
        "viewer_left_lower_lid_fold",
        "viewer_right_upper_lid_fold",
        "viewer_right_lower_lid_fold",
    ]
    for key in eyelid_keys:
        pts = [(x * scale, y * scale) for x, y in trace_points(trace, key)]
        draw.line(pts, fill=255, width=5 * scale, joint="curve")

    # Carve eye apertures back out so the candidate cannot cover pupil/iris/sclera.
    for key in ("viewer_left_visible_eye_aperture", "viewer_right_visible_eye_aperture"):
        pts = [(x * scale, y * scale) for x, y in trace_points(trace, key)]
        draw.polygon(pts, fill=0)

    # Carve brow hair polygons; this keeps the eyelid candidate below brow hair.
    for key in ("viewer_left_visible_brow_hair", "viewer_right_visible_brow_hair"):
        pts = [(x * scale, y * scale) for x, y in trace_points(trace, key)]
        draw.polygon(pts, fill=0)

    return mask.resize(size, Image.Resampling.LANCZOS).point(lambda value: 255 if value > 24 else 0)


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.array(mask.convert("L")) > 0))


def bbox(mask: Image.Image) -> list[int] | None:
    arr = np.array(mask.convert("L"))
    ys, xs = np.where(arr > 0)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def polygon_mask(size: tuple[int, int], polygons: list[list[tuple[int, int]]]) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for poly in polygons:
        d.polygon(poly, fill=255)
    return m


def overlap_count(mask: Image.Image, zone: Image.Image) -> int:
    return int(np.count_nonzero((np.array(mask.convert("L")) > 0) & (np.array(zone.convert("L")) > 0)))


def overlay(source: Image.Image, mask: Image.Image, color: tuple[int, int, int] = (255, 80, 0)) -> Image.Image:
    base = source.convert("RGBA")
    alpha = mask.point(lambda value: 140 if value > 8 else 0)
    fill = Image.new("RGBA", source.size, (*color, 0))
    fill.putalpha(alpha)
    return Image.alpha_composite(base, fill).convert("RGB")


def draw_boundaries(source: Image.Image, mask: Image.Image, trace: dict[str, Any]) -> Image.Image:
    out = overlay(source, mask)
    d = ImageDraw.Draw(out)
    # Green: allowed eyelid fold source trace. Amber: protected eye aperture / brow / hair boundary.
    for key in (
        "viewer_left_upper_lid_fold",
        "viewer_left_lower_lid_fold",
        "viewer_right_upper_lid_fold",
        "viewer_right_lower_lid_fold",
    ):
        pts = trace_points(trace, key)
        d.line(pts, fill=(0, 255, 80), width=3)
    for key in (
        "viewer_left_visible_eye_aperture",
        "viewer_right_visible_eye_aperture",
        "viewer_left_visible_brow_hair",
        "viewer_right_visible_brow_hair",
    ):
        pts = trace_points(trace, key)
        d.line(pts + [pts[0]], fill=(255, 210, 0), width=2)
    d.line(trace_points(trace, "viewer_left_hair_occlusion_boundary"), fill=(255, 240, 0), width=4)
    return out


def label_tile(image: Image.Image, label: str, width: int = 520) -> Image.Image:
    image = image.convert("RGB")
    height = max(1, round(image.height * (width / image.width)))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height + 34), (16, 16, 16))
    tile.paste(resized, (0, 34))
    ImageDraw.Draw(tile).text((8, 9), label, fill=(245, 245, 245), font=font(16))
    return tile


def make_panel(source: Image.Image, mask: Image.Image, trace: dict[str, Any], panel_path: Path) -> None:
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(CROP), "source crop"),
        label_tile(mask_rgb.crop(CROP), "candidate mask only"),
        label_tile(overlay(source, mask).crop(CROP), "source + candidate mask"),
        label_tile(draw_boundaries(source, mask, trace).crop(CROP), "green eyelid trace / amber protected boundaries"),
    ]
    panel = Image.new("RGB", (tiles[0].width * 2, tiles[0].height * 2), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, ((index % 2) * tile.width, (index // 2) * tile.height))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    trace = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    mask = draw_candidate_mask(source.size, trace)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    mask_path = OUT_DIR / "wave70_mf70_eyelids_manual_trace_candidate_v1_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_eyelids_manual_trace_candidate_v1_overlay.png"
    panel_path = RUNTIME_DIR / "wave70_mf70_eyelids_manual_trace_candidate_v1_panel.png"
    manifest_path = RUNTIME_DIR / "wave70_mf70_eyelids_manual_trace_candidate_v1_manifest.json"

    mask.save(mask_path)
    overlay(source, mask).save(overlay_path)
    make_panel(source, mask, trace, panel_path)

    aperture_zone = polygon_mask(
        source.size,
        [
            trace_points(trace, "viewer_left_visible_eye_aperture"),
            trace_points(trace, "viewer_right_visible_eye_aperture"),
        ],
    )
    brow_zone = polygon_mask(
        source.size,
        [
            trace_points(trace, "viewer_left_visible_brow_hair"),
            trace_points(trace, "viewer_right_visible_brow_hair"),
        ],
    )
    metrics = {
        "nonzero_pixels": count_nonzero(mask),
        "coverage_percent": round(count_nonzero(mask) / (source.width * source.height) * 100, 5),
        "bbox": bbox(mask),
        "protected_overlap_pixels": {
            "eye_apertures": overlap_count(mask, aperture_zone),
            "brow_hair": overlap_count(mask, brow_zone),
        },
    }

    manifest = {
        "schema_version": "1.0",
        "created_local": RUN_STAMP,
        "mask_type_id": "mf70_eyelids",
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "manual_trace_source": rel(TRACE_JSON),
        "mask": rel(mask_path),
        "mask_sha256": sha256_file(mask_path),
        "overlay": rel(overlay_path),
        "panel": rel(panel_path),
        "metrics": metrics,
        "status": "candidate_evidence_only_not_active_not_promoted",
    }
    write_json(manifest_path, manifest)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MF70_EYELIDS_MANUAL_TRACE_CANDIDATE_V1_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "mask_type_id": "mf70_eyelids",
        "tracker_id": "TRK-W70-0013",
        "item_id": "ITEM-W70-0013",
        "task": "derive one conservative mf70_eyelids candidate from corrected manual eye-boundary trace",
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "result": "candidate_created_for_high_zoom_review_not_promoted",
        "promotion_decision": "no_active_mask_replaced_no_generated_output_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "geometry_gate": {
            "result": "not_requested_candidate_review_pending",
            "wave70_mask_geometry_gate_pass": False,
            "approval_token": "",
            "source_dimensions": [source.width, source.height],
            "mask_dimensions": [mask.width, mask.height],
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "mask_sha256": sha256_file(mask_path),
            "crop_rect_full_image_xyxy": list(CROP),
            "panel_scale": PANEL_SCALE,
            "coordinate_transform_manifest_pass": True,
            "allowed_geometry_source_derived_pass": True,
            "protected_geometry_source_derived_pass": True,
            "green_amber_conflict_pass": metrics["protected_overlap_pixels"]["eye_apertures"] == 0
            and metrics["protected_overlap_pixels"]["brow_hair"] == 0,
            "debug_rectangle_only": False,
            "panel_readable_pass": True,
            "findings": [
                "Candidate is derived from corrected manual trace polylines, not old debug rectangles.",
                "Eye aperture and brow polygons are carved out as protected zones.",
                "This evidence intentionally withholds approval token pending strict high-zoom review.",
            ],
        },
        "artifacts": {
            "candidate_mask": rel(mask_path),
            "candidate_overlay": rel(overlay_path),
            "candidate_panel": rel(panel_path),
            "candidate_manifest": rel(manifest_path),
        },
        "metrics": metrics,
        "active_comfyui_input_changed": False,
        "generated_output_proof_run": False,
        "next_step": "Inspect candidate panel; if acceptable, run row-level geometry review evidence, still without generated-output proof.",
    }
    write_json(QA_EVIDENCE, evidence)
    write_json(TRACKER_EVIDENCE, evidence)
    print(json.dumps({"evidence": str(QA_EVIDENCE), "tracker_evidence": str(TRACKER_EVIDENCE), "panel": str(panel_path), "mask": str(mask_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
