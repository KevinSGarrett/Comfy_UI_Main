#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T221500-0500"
TIMESTAMP = "2026-07-07T22:15:00-05:00"
MASK_TYPE_ID = "mf70_mouth_lips"
TRACKER_ID = "TRK-W70-0018"
ITEM_ID = "ITEM-W70-0018"
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
OLD_MASK = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_mouth_lips_20260707T193000-0500/"
    "wave70_mf70_mouth_lips_mask.png"
)
OLD_OVERLAY = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_mouth_lips_20260707T193000-0500/"
    "wave70_mf70_mouth_lips_overlay.png"
)
BOUNDARY_PROTOCOL = "Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md"


LANDMARKS = {
    "left_corner": [310, 451],
    "right_corner": [438, 452],
    "upper_left_outer": [327, 443],
    "upper_left_peak": [358, 439],
    "upper_cupid_center": [389, 449],
    "upper_right_peak": [417, 441],
    "upper_right_outer": [452, 452],
    "inner_left": [323, 455],
    "inner_center_left": [361, 457],
    "inner_center_right": [402, 459],
    "inner_right": [433, 457],
    "lower_left_outer": [319, 461],
    "lower_left_mid": [350, 473],
    "lower_center": [388, 479],
    "lower_right_mid": [423, 472],
    "lower_right_outer": [449, 461],
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
    bbox_raw = mask.point(lambda v: 255 if v > 8 else 0).getbbox()
    bbox = None
    if bbox_raw:
        left, top, right, bottom = bbox_raw
        bbox = {"x_min": left, "y_min": top, "x_max": right - 1, "y_max": bottom - 1}
    return {
        "white_pixel_count": sum(hist[250:]),
        "nonblack_pixel_count": nonblack,
        "coverage_percent": round(nonblack * 100.0 / total, 4),
        "bbox_pixels": bbox,
    }


def upper_lip_polygon() -> list[tuple[int, int]]:
    return [
        tuple(LANDMARKS["left_corner"]),
        tuple(LANDMARKS["upper_left_outer"]),
        tuple(LANDMARKS["upper_left_peak"]),
        tuple(LANDMARKS["upper_cupid_center"]),
        tuple(LANDMARKS["upper_right_peak"]),
        tuple(LANDMARKS["upper_right_outer"]),
        tuple(LANDMARKS["right_corner"]),
        tuple(LANDMARKS["inner_right"]),
        tuple(LANDMARKS["inner_center_right"]),
        tuple(LANDMARKS["inner_center_left"]),
        tuple(LANDMARKS["inner_left"]),
    ]


def lower_lip_polygon() -> list[tuple[int, int]]:
    return [
        tuple(LANDMARKS["left_corner"]),
        tuple(LANDMARKS["inner_left"]),
        tuple(LANDMARKS["inner_center_left"]),
        tuple(LANDMARKS["inner_center_right"]),
        tuple(LANDMARKS["inner_right"]),
        tuple(LANDMARKS["right_corner"]),
        tuple(LANDMARKS["lower_right_outer"]),
        tuple(LANDMARKS["lower_right_mid"]),
        tuple(LANDMARKS["lower_center"]),
        tuple(LANDMARKS["lower_left_mid"]),
        tuple(LANDMARKS["lower_left_outer"]),
    ]


def inner_mouth_polygon() -> list[tuple[int, int]]:
    return [
        tuple(LANDMARKS["inner_left"]),
        tuple(LANDMARKS["inner_center_left"]),
        tuple(LANDMARKS["inner_center_right"]),
        tuple(LANDMARKS["inner_right"]),
        (430, 463),
        (398, 466),
        (360, 464),
        (321, 459),
    ]


def make_mask(size: tuple[int, int]) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(upper_lip_polygon(), fill=255)
    draw.polygon(lower_lip_polygon(), fill=255)
    draw.polygon(inner_mouth_polygon(), fill=0)
    # Hard guardrails keep this single-source candidate local to the visible lip surfaces.
    draw.rectangle((0, 0, width, 436), fill=0)
    draw.rectangle((0, 484, width, height), fill=0)
    draw.rectangle((0, 0, 300, height), fill=0)
    draw.rectangle((456, 0, width, height), fill=0)
    return mask.filter(ImageFilter.GaussianBlur(radius=0.55))


def boundary_layer(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "inner_mouth_teeth":
        draw.polygon([(319, 453), (360, 454), (402, 456), (437, 454), (430, 466), (388, 468), (344, 464)], fill=255)
    elif region_id == "philtrum":
        draw.polygon([(350, 430), (424, 430), (438, 452), (315, 452)], fill=255)
    elif region_id == "nose":
        draw.polygon([(384, 326), (403, 326), (408, 360), (416, 393), (424, 419), (415, 431), (394, 436), (371, 431), (360, 419), (366, 394), (377, 360)], fill=255)
        draw.ellipse((356, 407, 385, 435), fill=255)
        draw.ellipse((401, 407, 427, 435), fill=255)
    elif region_id == "chin_lower_skin":
        draw.polygon([(310, 482), (454, 482), (486, 550), (278, 550)], fill=255)
    elif region_id == "left_cheek_skin":
        draw.polygon([(232, 404), (307, 430), (306, 490), (236, 512)], fill=255)
    elif region_id == "right_cheek_skin":
        draw.polygon([(456, 420), (536, 390), (540, 520), (456, 490)], fill=255)
    elif region_id == "mouth_lips_target_candidate":
        draw.polygon(upper_lip_polygon(), fill=255)
        draw.polygon(lower_lip_polygon(), fill=255)
        draw.polygon(inner_mouth_polygon(), fill=0)
    else:
        raise ValueError(f"unknown boundary region: {region_id}")
    return mask.filter(ImageFilter.GaussianBlur(radius=0.5))


def pixel_count(mask: Image.Image) -> int:
    hist = mask.point(lambda v: 255 if v > 8 else 0).histogram()
    return sum(hist[1:])


def intersection_count(a: Image.Image, b: Image.Image) -> int:
    aa = a.point(lambda v: 255 if v > 8 else 0)
    bb = b.point(lambda v: 255 if v > 8 else 0)
    return sum(1 for av, bv in zip(aa.getdata(), bb.getdata()) if av and bv)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (0, 255, 128, 0))
    fill.putalpha(mask.point(lambda v: min(150, int(v * 0.58))))
    edges = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 8 else 0)
    outline = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
    outline.putalpha(edges)
    draw = ImageDraw.Draw(outline)
    for x, y in LANDMARKS.values():
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 60, 60, 230))
    return Image.alpha_composite(Image.alpha_composite(rgba, fill), outline)


def make_boundary_overlay(source: Image.Image, layers: list[dict[str, Any]]) -> Image.Image:
    rgba = source.convert("RGBA")
    colors = {
        "inner_mouth_teeth": (255, 70, 70, 110),
        "philtrum": (255, 196, 0, 110),
        "nose": (0, 220, 120, 105),
        "chin_lower_skin": (255, 80, 220, 90),
        "left_cheek_skin": (40, 150, 255, 85),
        "right_cheek_skin": (40, 150, 255, 85),
        "mouth_lips_target_candidate": (255, 255, 255, 90),
    }
    for layer in layers:
        region_id = layer["region_id"]
        mask = Image.open(layer["path"]).convert("L")
        color = Image.new("RGBA", rgba.size, colors[region_id])
        color.putalpha(mask.point(lambda v, alpha=colors[region_id][3]: min(alpha, int(v * alpha / 255))))
        rgba = Image.alpha_composite(rgba, color)
        edges = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 220 if v > 8 else 0)
        edge = Image.new("RGBA", rgba.size, (*colors[region_id][:3], 0))
        edge.putalpha(edges)
        rgba = Image.alpha_composite(rgba, edge)
    return rgba.convert("RGB")


def crop_box() -> tuple[int, int, int, int]:
    return (270, 405, 486, 525)


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


def make_panel(source: Image.Image, old_overlay: Image.Image, candidate_overlay: Image.Image, boundary_overlay: Image.Image, mask: Image.Image, panel_path: Path) -> None:
    crop = crop_box()
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(old_overlay.crop(crop), "old disputed overlay"),
        label_tile(candidate_overlay.crop(crop), "source-landmark candidate"),
        label_tile(boundary_overlay.crop(crop), "candidate + boundaries"),
        label_tile(mask_rgb.crop(crop), "candidate mask only"),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    source_path = resolve_rel(root, SOURCE_IMAGE)
    old_mask_path = resolve_rel(root, OLD_MASK)
    old_overlay_path = resolve_rel(root, OLD_OVERLAY)
    source = Image.open(source_path).convert("RGB")
    old_overlay = Image.open(old_overlay_path).convert("RGB")

    prepared_dir = root / "Plan/Instructions/Operations/Prepared_Input_Assets" / f"wave70_mf70_mouth_lips_source_landmark_{RUN_STAMP}"
    audit_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_mouth_lips/source_landmark_repair" / RUN_STAMP
    layers_dir = audit_dir / "boundary_layers"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)

    mask = make_mask(source.size)
    overlay = make_overlay(source, mask)
    mask_path = prepared_dir / "wave70_mf70_mouth_lips_mask.png"
    overlay_path = prepared_dir / "wave70_mf70_mouth_lips_overlay.png"
    landmarks_path = audit_dir / "mf70_mouth_lips_source_landmarks.json"
    matrix_path = audit_dir / "mf70_mouth_lips_source_landmark_protected_overlap_matrix.csv"
    registry_path = audit_dir / "BOUNDARY_REGISTRY_MANIFEST.json"
    boundary_overlay_path = audit_dir / "mf70_mouth_lips_source_landmark_boundary_overlay.png"
    panel_path = audit_dir / "mf70_mouth_lips_source_landmark_repair_panel.png"
    mask.save(mask_path)
    overlay.save(overlay_path)

    region_ids = ["inner_mouth_teeth", "philtrum", "nose", "chin_lower_skin", "left_cheek_skin", "right_cheek_skin", "mouth_lips_target_candidate"]
    layers: list[dict[str, Any]] = []
    for region_id in region_ids:
        layer = boundary_layer(source.size, region_id)
        path = layers_dir / f"{region_id}.png"
        layer.save(path)
        layers.append(
            {
                "region_id": region_id,
                "source": "manual_source_reviewed_polygon_candidate",
                "path": str(path),
                "sha256": sha256_file(path),
                "review_status": "candidate_review_required" if region_id == "mouth_lips_target_candidate" else "manual_boundary_candidate",
            }
        )

    candidate_pixels = pixel_count(mask)
    overlap_rows: list[dict[str, Any]] = []
    protected_failures: list[str] = []
    tolerances = {
        "inner_mouth_teeth": 0,
        "philtrum": 0,
        "nose": 0,
        "chin_lower_skin": 8,
        "left_cheek_skin": 8,
        "right_cheek_skin": 8,
    }
    for layer in layers:
        region_id = layer["region_id"]
        if region_id == "mouth_lips_target_candidate":
            continue
        protected_mask = Image.open(layer["path"]).convert("L")
        overlap = intersection_count(mask, protected_mask)
        allowed = tolerances[region_id]
        passed = overlap <= allowed
        if not passed:
            protected_failures.append(region_id)
        overlap_rows.append(
            {
                "target_mask_type_id": MASK_TYPE_ID,
                "protected_region_id": region_id,
                "overlap_pixels": overlap,
                "overlap_percent_of_candidate": round(overlap * 100.0 / candidate_pixels, 4) if candidate_pixels else 0.0,
                "allowed_overlap_pixels": allowed,
                "pass": passed,
            }
        )

    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "target_mask_type_id",
                "protected_region_id",
                "overlap_pixels",
                "overlap_percent_of_candidate",
                "allowed_overlap_pixels",
                "pass",
            ],
        )
        writer.writeheader()
        writer.writerows(overlap_rows)

    boundary_overlay = make_boundary_overlay(overlay, layers)
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, old_overlay, overlay, boundary_overlay, mask, panel_path)

    metrics = count_pixels(mask)
    old_metrics = count_pixels(Image.open(old_mask_path).convert("L"))
    write_json(
        landmarks_path,
        {
            "schema_version": "1.0",
            "timestamp": TIMESTAMP,
            "source_image": rel(source_path, root),
            "source_image_sha256": sha256_file(source_path),
            "landmark_source": "manual_source_specific_pixels_after_user_global_mask_alignment_dispute",
            "coordinate_space": {"width": source.width, "height": source.height, "origin": "top_left"},
            "landmarks": LANDMARKS,
            "changes_from_old_mask": [
                "Removed right-side stray speckle/fragment artifacts visible in the old mask-only panel.",
                "Tightened lower boundary to visible lower-lip surface instead of broader perioral skin.",
                "Protected central inner-mouth/teeth slit and kept the candidate separate from nose, philtrum, chin, and broad cheek regions.",
            ],
        },
    )

    manifest_layers = [{**layer, "path": rel(Path(layer["path"]), root)} for layer in layers]
    protected_overlap_pass = not protected_failures
    write_json(
        registry_path,
        {
            "schema_version": "1.0",
            "boundary_registry": {
                "source_image_id": "active_mod17_canny_v3_seed711570105",
                "matrix_slot_id": "single_anchor_smoke_frontal_neutral",
                "canonical_boundary_layer_pass": False,
                "boundary_layers": manifest_layers,
                "protected_overlap_matrix_path": rel(matrix_path, root),
                "protected_overlap_matrix_sha256": sha256_file(matrix_path),
                "protected_overlap_matrix_pass": protected_overlap_pass,
                "boundary_status": "candidate_registry_pending_strict_visual_review",
            },
            "policy": "Manual source-derived candidate boundaries for local repair audit only. These are not promoted canonical boundary layers.",
        },
    )

    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    result = "mouth_lips_source_landmark_candidate_created_pending_strict_visual_review" if protected_overlap_pass else "mouth_lips_source_landmark_candidate_protected_overlap_failed"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-MOUTH-LIPS-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_mouth_lips_source_specific_landmark_repair_candidate",
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
        "old_mask": rel(old_mask_path, root),
        "old_mask_sha256": sha256_file(old_mask_path),
        "old_coverage_percent": old_metrics["coverage_percent"],
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": sha256_file(mask_path),
        "candidate_overlay": rel(overlay_path, root),
        "candidate_overlay_sha256": sha256_file(overlay_path),
        "landmarks_json": rel(landmarks_path, root),
        "landmarks_json_sha256": sha256_file(landmarks_path),
        "boundary_protocol": BOUNDARY_PROTOCOL,
        "boundary_registry_manifest": rel(registry_path, root),
        "boundary_registry_manifest_sha256": sha256_file(registry_path),
        "protected_overlap_matrix": rel(matrix_path, root),
        "protected_overlap_matrix_sha256": sha256_file(matrix_path),
        "boundary_overlay": rel(boundary_overlay_path, root),
        "boundary_overlay_sha256": sha256_file(boundary_overlay_path),
        "review_panel": rel(panel_path, root),
        "review_panel_sha256": sha256_file(panel_path),
        "candidate_metrics": metrics,
        "protected_overlap_rows": overlap_rows,
        "protected_overlap_failures": protected_failures,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "semantic_mask_alignment_pass": False,
        "generated_output_executed": False,
        "completion_allowed_by_mask_alignment": False,
        "result": result,
        "boundary": "Candidate repair only. mf70_mouth_lips remains needs-revision until strict visual review accepts the candidate and generated-output proof is rerun with this mask.",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "status": "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
            "status_decision": "mouth_lips_source_landmark_candidate_pending_strict_visual_review",
            "evidence": rel(evidence_path, root),
            "review_panel": rel(panel_path, root),
            "protected_overlap_matrix_pass": protected_overlap_pass,
            "local_only": True,
            "aws_contacted": False,
            "github_api_contacted": False,
            "civitai_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "result": result,
        },
    )
    print(json.dumps({"result": result, "evidence": rel(evidence_path, root), "tracker_evidence": rel(tracker_path, root), "panel": rel(panel_path, root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
