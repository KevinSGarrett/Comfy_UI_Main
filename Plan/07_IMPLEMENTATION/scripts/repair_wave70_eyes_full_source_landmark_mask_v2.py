#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260709T215300-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
OUT_DIR = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_eyes_full_source_landmark_v2_{RUN_STAMP}"
)
RUNTIME_DIR = PROJECT_ROOT / (
    "runtime_artifacts/mask_factory/wave70_mf70_eyes_full_source_landmark_v2"
) / RUN_STAMP
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}.json"
)

# Image-space coordinates on the active 768x768 source.
# These are candidate aperture traces, not promoted geometry authority.
EYE_POLYGONS = {
    "viewer_left_visible_eye_aperture": [
        (286, 329),
        (296, 319),
        (313, 316),
        (330, 321),
        (340, 331),
        (328, 340),
        (309, 342),
        (292, 337),
    ],
    "viewer_right_visible_eye_aperture": [
        (397, 329),
        (407, 320),
        (426, 316),
        (445, 320),
        (459, 331),
        (448, 341),
        (426, 344),
        (407, 339),
    ],
}

PROTECTED_NEIGHBORS = {
    "viewer_left_hair_occlusion_boundary_note": (
        "viewer-left eye mask is clipped inside the visible aperture and intentionally "
        "does not extend into the curl mass over the outer eye/temple."
    ),
    "brows_and_eyelids_note": (
        "eyes_full candidate excludes eyebrow strips and most eyelid skin; eyelids remain "
        "separate child/neighbor regions."
    ),
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def draw_antialiased_mask(size: tuple[int, int]) -> Image.Image:
    scale = 4
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(mask)
    for polygon in EYE_POLYGONS.values():
        scaled = [(x * scale, y * scale) for x, y in polygon]
        draw.polygon(scaled, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.0 * scale))
    return mask.resize(size, Image.Resampling.LANCZOS)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", source.size, (0, 220, 255, 0))
    fill.putalpha(mask.point(lambda v: min(145, int(v * 0.56))))
    edge = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 12 else 0)
    outline = Image.new("RGBA", source.size, (255, 255, 0, 0))
    outline.putalpha(edge)
    return Image.alpha_composite(Image.alpha_composite(rgba, fill), outline).convert("RGB")


def make_panel(source: Image.Image, mask: Image.Image, overlay: Image.Image) -> Image.Image:
    crop = (240, 250, 500, 380)
    tile_w, tile_h = 420, 260
    tiles = []
    for title, image in (
        ("source crop", source.crop(crop)),
        ("candidate overlay", overlay.crop(crop)),
        ("mask only", Image.merge("RGB", (mask, mask, mask)).crop(crop)),
    ):
        tile = Image.new("RGB", (tile_w, tile_h), (16, 16, 16))
        resized = image.resize((tile_w, tile_h - 32), Image.Resampling.LANCZOS)
        tile.paste(resized, (0, 32))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 8), title, fill=(245, 245, 245))
        tiles.append(tile)
    panel = Image.new("RGB", (tile_w * len(tiles), tile_h), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * tile_w, 0))
    return panel


def mask_stats(mask: Image.Image) -> dict[str, Any]:
    threshold = mask.point(lambda v: 255 if v > 12 else 0)
    return {
        "bbox": threshold.getbbox(),
        "nonzero_pixels": sum(1 for value in threshold.getdata() if value > 0),
        "image_size": list(mask.size),
    }


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    mask = draw_antialiased_mask(source.size)
    overlay = make_overlay(source, mask)
    panel = make_panel(source, mask, overlay)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    mask_path = OUT_DIR / "wave70_mf70_eyes_full_source_landmark_v2_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_eyes_full_source_landmark_v2_overlay.png"
    panel_path = RUNTIME_DIR / "wave70_mf70_eyes_full_source_landmark_v2_review_panel.png"
    coordinate_manifest_path = OUT_DIR / "wave70_mf70_eyes_full_source_landmark_v2_coordinates.json"

    mask.save(mask_path)
    overlay.save(overlay_path)
    panel.save(panel_path)

    coordinate_manifest = {
        "schema_version": "1.0",
        "mask_type_id": "mf70_eyes_full",
        "source_image": rel(SOURCE_IMAGE),
        "coordinate_space": "active_source_image_pixels_768x768",
        "eye_polygons": EYE_POLYGONS,
        "protected_neighbors": PROTECTED_NEIGHBORS,
        "candidate_only": True,
        "promotion_allowed": False,
    }
    write_json(coordinate_manifest_path, coordinate_manifest)

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "task": "Create one superseding source-aware eyes_full candidate mask after user reported eye/eyebrow masks drifting into hair.",
        "supersedes_failed_candidate": "W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V1_20260709T214900-0500",
        "implementation_script": rel(Path(__file__).resolve()),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "comfyui_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "artifacts": {
            "mask": rel(mask_path),
            "mask_sha256": sha256_file(mask_path),
            "overlay": rel(overlay_path),
            "overlay_sha256": sha256_file(overlay_path),
            "review_panel": rel(panel_path),
            "review_panel_sha256": sha256_file(panel_path),
            "coordinate_manifest": rel(coordinate_manifest_path),
            "coordinate_manifest_sha256": sha256_file(coordinate_manifest_path),
        },
        "mask_stats": mask_stats(mask),
        "semantic_mask_alignment_repair_notes": [
            "Candidate narrows mf70_eyes_full from broad ovals to visible eye apertures.",
            "Viewer-left eye is deliberately clipped away from the hair occlusion boundary.",
            "Candidate excludes eyebrow and eyelid skin regions; those remain separate protected neighbors.",
            "This is one source-anchor candidate only and cannot establish matrix/generalized mask completion.",
        ],
        "qa_decision": "candidate_created_pending_strict_visual_review_and_wave70_geometry_promotion_gates",
        "promotion_decision": "not_promoted_no_active_input_changed_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "next_required_action": (
            "Perform strict source/overlay/mask-only visual QA on the review panel, then either adjust the "
            "candidate or run Wave70 geometry/promotion gates before any runtime proof."
        ),
    }
    write_json(QA_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    print(json.dumps({"result": payload["qa_decision"], "qa_evidence": rel(QA_EVIDENCE), "review_panel": rel(panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
