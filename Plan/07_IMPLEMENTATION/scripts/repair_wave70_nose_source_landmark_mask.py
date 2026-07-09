#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T212500-0500"
MASK_TYPE_ID = "mf70_nose"
TRACKER_ID = "TRK-W70-0017"
ITEM_ID = "ITEM-W70-0017"
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
SUPERSEDING_DISPUTE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MASK_ALIGNMENT_USER_DISPUTE_GLOBAL_REVIEW_20260707T211000-0500.json"
)
FAIL_CLOSED_AUDIT = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MASK_ALIGNMENT_FAIL_CLOSED_AUDIT_20260707T211500-0500.json"
)


LANDMARKS = {
    "nose_bridge_top_left": [384, 326],
    "nose_bridge_top_right": [404, 326],
    "left_bridge_wall": [374, 358],
    "right_bridge_wall": [409, 358],
    "left_sidewall": [362, 393],
    "right_sidewall": [417, 392],
    "left_ala_outer": [352, 424],
    "right_ala_outer": [429, 423],
    "left_nostril_edge": [364, 439],
    "right_nostril_edge": [420, 438],
    "columella_base": [394, 445],
    "tip_highlight": [393, 416],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_rel(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / raw.replace("/", "\\")


def count_pixels(mask: Image.Image) -> dict[str, Any]:
    hist = mask.histogram()
    nonblack = sum(hist[1:])
    total = sum(hist)
    bbox = mask.getbbox()
    bbox_dict = None
    if bbox:
        left, top, right, bottom = bbox
        bbox_dict = {"x_min": left, "y_min": top, "x_max": right - 1, "y_max": bottom - 1}
    return {
        "white_pixel_count": sum(hist[250:]),
        "nonblack_pixel_count": nonblack,
        "coverage_percent": round(nonblack * 100.0 / total, 4),
        "bbox_pixels": bbox_dict,
    }


def nose_polygon() -> list[tuple[int, int]]:
    names = [
        "nose_bridge_top_left",
        "nose_bridge_top_right",
        "right_bridge_wall",
        "right_sidewall",
        "right_ala_outer",
        "right_nostril_edge",
        "columella_base",
        "left_nostril_edge",
        "left_ala_outer",
        "left_sidewall",
        "left_bridge_wall",
    ]
    return [tuple(LANDMARKS[name]) for name in names]


def make_mask(size: tuple[int, int]) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(nose_polygon(), fill=255)
    # Include a small nostril/ala support area but keep it above the philtrum and mouth.
    draw.ellipse((350, 409, 388, 446), fill=255)
    draw.ellipse((398, 408, 431, 443), fill=255)
    # Hard protected-neighbor guards. These intentionally clip the candidate if landmarks drift.
    draw.rectangle((0, 0, width, 314), fill=0)
    draw.rectangle((0, 450, width, height), fill=0)
    draw.rectangle((0, 0, 336, height), fill=0)
    draw.rectangle((442, 0, width, height), fill=0)
    return mask.filter(ImageFilter.GaussianBlur(radius=1.0))


def make_overlay(source: Image.Image, mask: Image.Image, color=(0, 255, 128)) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (*color, 0))
    fill.putalpha(mask.point(lambda v: min(150, int(v * 0.58))))
    edges = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 8 else 0)
    outline = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
    outline.putalpha(edges)
    draw = ImageDraw.Draw(outline)
    for point_name, (x, y) in LANDMARKS.items():
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 60, 60, 230))
    return Image.alpha_composite(Image.alpha_composite(rgba, fill), outline)


def crop_box() -> tuple[int, int, int, int]:
    return (300, 286, 474, 474)


def label_tile(image: Image.Image, label: str, size: int = 360) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def make_panel(
    source: Image.Image,
    previous_overlay: Image.Image,
    repair_overlay: Image.Image,
    repair_mask: Image.Image,
    panel_path: Path,
) -> None:
    crop = crop_box()
    mask_rgb = Image.merge("RGB", (repair_mask, repair_mask, repair_mask))
    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(previous_overlay.crop(crop), "previous failed overlay"),
        label_tile(repair_overlay.crop(crop), "source-landmark repair"),
        label_tile(mask_rgb.crop(crop), "repair mask only"),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    parser.add_argument("--source-image", default=SOURCE_IMAGE)
    args = parser.parse_args()

    root = args.project_root
    source_path = resolve_rel(root, args.source_image)
    source = Image.open(source_path).convert("RGB")

    prepared_dir = root / "Plan" / "Instructions" / "Operations" / "Prepared_Input_Assets" / f"wave70_mf70_nose_source_landmark_{RUN_STAMP}"
    audit_dir = root / "runtime_artifacts" / "mask_factory" / "wave70_mf70_nose" / "source_landmark_repair"
    evidence_path = root / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70" / f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    tracker_path = root / "Plan" / "Tracker" / "Evidence" / f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    old_overlay = root / "Plan" / "Instructions" / "Operations" / "Prepared_Input_Assets" / "wave70_mf70_nose_20260707T204500-0500" / "wave70_mf70_nose_overlay.png"

    prepared_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    mask = make_mask(source.size)
    overlay = make_overlay(source, mask)

    mask_path = prepared_dir / "wave70_mf70_nose_mask.png"
    overlay_path = prepared_dir / "wave70_mf70_nose_overlay.png"
    landmark_path = audit_dir / f"mf70_nose_source_landmarks_{RUN_STAMP}.json"
    panel_path = audit_dir / f"mf70_nose_source_landmark_repair_panel_{RUN_STAMP}.png"
    mask.save(mask_path)
    overlay.save(overlay_path)
    write_json(
        landmark_path,
        {
            "schema_version": "1.0",
            "timestamp": "2026-07-07T21:25:00-05:00",
            "source_image": rel(source_path, root),
            "source_image_sha256": sha256_file(source_path),
            "landmark_source": "manual_source_specific_pixels_after_fail_closed_audit",
            "coordinate_space": {"width": source.width, "height": source.height, "origin": "top_left"},
            "landmarks": LANDMARKS,
            "protected_neighbor_guards": {
                "mouth_and_philtrum_y_min": 450,
                "eye_region_y_max": 314,
                "left_cheek_x_max": 336,
                "right_cheek_x_min": 442,
            },
            "policy": "Candidate geometry only; not a pass or certification record until strict overlay review accepts the mask.",
        },
    )
    previous = Image.open(old_overlay).convert("RGB")
    make_panel(source, previous, overlay, mask, panel_path)

    metrics = count_pixels(mask)
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-NOSE-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}",
        "timestamp": "2026-07-07T21:25:00-05:00",
        "project_root": str(root),
        "qa_type": "wave70_mf70_nose_source_specific_landmark_repair_candidate",
        "implementation_script": rel(Path(__file__).resolve(), root),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "mask_type_id": MASK_TYPE_ID,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "source_image": rel(source_path, root),
        "source_image_sha256": sha256_file(source_path),
        "superseding_user_dispute": SUPERSEDING_DISPUTE,
        "fail_closed_audit": FAIL_CLOSED_AUDIT,
        "artifacts": {
            "mask_png": rel(mask_path, root),
            "overlay_png": rel(overlay_path, root),
            "landmarks_json": rel(landmark_path, root),
            "repair_panel": rel(panel_path, root),
        },
        "hashes": {
            "mask_sha256": sha256_file(mask_path),
            "overlay_sha256": sha256_file(overlay_path),
            "landmarks_sha256": sha256_file(landmark_path),
            "repair_panel_sha256": sha256_file(panel_path),
        },
        "metrics": metrics,
        "repair_candidate": {
            "candidate_only": True,
            "semantic_mask_alignment_pass": False,
            "protected_neighbor_pass": False,
            "generated_output_safe_pass": None,
            "completion_allowed_by_mask_alignment": False,
            "status": "source_landmark_repair_candidate_pending_strict_overlay_review",
            "notes": [
                "Replaces the broad percentage-coordinate nose blob with source-specific pixel landmarks.",
                "Hard guardrails clip the mask above the mouth/philtrum and away from eye/cheek regions.",
                "No generated-output proof was run because source-overlay review must pass first.",
            ],
        },
        "result": "mf70_nose_source_landmark_repair_candidate_created_pending_strict_overlay_review",
        "next_required_action": "Visually review repair panel, rerun fail-closed audit against this candidate, and only then consider low-denoise generated-output proof.",
    }
    write_json(evidence_path, evidence)

    tracker = {
        "schema_version": "1.0",
        "tracker_evidence_id": f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
        "created_at": "2026-07-07T21:25:00-05:00",
        "project_root": str(root),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "mask_type_id": MASK_TYPE_ID,
        "source_evidence": rel(evidence_path, root),
        "status": "Mask_Alignment_Fail_Generated_Output_Safe_Target_Runtime_Pending",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "artifact": rel(panel_path, root),
        "result": "source_landmark_repair_candidate_created_without_pass_promotion",
    }
    write_json(tracker_path, tracker)

    print(
        json.dumps(
            {
                "result": evidence["result"],
                "evidence": rel(evidence_path, root),
                "tracker_evidence": rel(tracker_path, root),
                "mask": rel(mask_path, root),
                "overlay": rel(overlay_path, root),
                "panel": rel(panel_path, root),
                "coverage_percent": metrics["coverage_percent"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
