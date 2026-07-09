#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T213500-0500"
MASK_TYPE_ID = "mf70_nose"
TRACKER_ID = "TRK-W70-0017"
ITEM_ID = "ITEM-W70-0017"
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
CANDIDATE_MASK = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_20260707T212500-0500/"
    "wave70_mf70_nose_mask.png"
)
CANDIDATE_OVERLAY = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_20260707T212500-0500/"
    "wave70_mf70_nose_overlay.png"
)
CANDIDATE_EVIDENCE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_20260707T212500-0500.json"
)
BOUNDARY_PROTOCOL = "Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md"


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


def binary_mask(mask: Image.Image, threshold: int = 8) -> Image.Image:
    return mask.convert("L").point(lambda v: 255 if v > threshold else 0)


def pixel_count(mask: Image.Image) -> int:
    hist = mask.convert("L").histogram()
    return sum(hist[1:])


def intersection_count(a: Image.Image, b: Image.Image) -> int:
    ba = binary_mask(a)
    bb = binary_mask(b)
    return sum(1 for va, vb in zip(ba.getdata(), bb.getdata()) if va and vb)


def layer_mask(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "mouth_lips":
        draw.polygon([(319, 444), (351, 435), (395, 440), (438, 436), (470, 449), (451, 480), (393, 491), (338, 482)], fill=255)
    elif region_id == "upper_lip":
        draw.polygon([(326, 440), (356, 432), (392, 438), (430, 434), (466, 448), (442, 458), (393, 453), (346, 457)], fill=255)
    elif region_id == "philtrum":
        draw.polygon([(362, 427), (424, 426), (435, 449), (352, 449)], fill=255)
    elif region_id == "left_eye_canthus_lower_lid":
        draw.ellipse((242, 284, 350, 354), fill=255)
    elif region_id == "right_eye_canthus_lower_lid":
        draw.ellipse((406, 279, 518, 356), fill=255)
    elif region_id == "left_cheek":
        draw.polygon([(238, 355), (342, 352), (352, 443), (238, 493)], fill=255)
    elif region_id == "right_cheek":
        draw.polygon([(437, 350), (539, 344), (541, 504), (426, 450)], fill=255)
    elif region_id == "nose_target_candidate_boundary":
        draw.polygon([(384, 326), (404, 326), (409, 358), (417, 392), (429, 423), (420, 438), (394, 445), (364, 439), (352, 424), (362, 393), (374, 358)], fill=255)
        draw.ellipse((350, 409, 388, 446), fill=255)
        draw.ellipse((398, 408, 431, 443), fill=255)
    else:
        raise ValueError(f"unknown region_id: {region_id}")
    return mask.filter(ImageFilter.GaussianBlur(radius=0.7))


def make_boundary_overlay(source: Image.Image, layers: list[dict[str, Any]]) -> Image.Image:
    rgba = source.convert("RGBA")
    palette = {
        "mouth_lips": (255, 60, 60, 85),
        "upper_lip": (255, 120, 40, 110),
        "philtrum": (255, 210, 40, 105),
        "left_eye_canthus_lower_lid": (80, 170, 255, 100),
        "right_eye_canthus_lower_lid": (80, 170, 255, 100),
        "left_cheek": (255, 80, 200, 60),
        "right_cheek": (255, 80, 200, 60),
        "nose_target_candidate_boundary": (0, 255, 120, 80),
    }
    for layer in layers:
        mask = Image.open(layer["path"]).convert("L")
        color = Image.new("RGBA", rgba.size, palette[layer["region_id"]])
        alpha = mask.point(lambda v: min(palette[layer["region_id"]][3], int(v * (palette[layer["region_id"]][3] / 255))))
        color.putalpha(alpha)
        edge = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 220 if v > 8 else 0)
        outline = Image.new("RGBA", rgba.size, (*palette[layer["region_id"]][:3], 0))
        outline.putalpha(edge)
        rgba = Image.alpha_composite(Image.alpha_composite(rgba, color), outline)
    return rgba.convert("RGB")


def crop_box() -> tuple[int, int, int, int]:
    return (230, 260, 552, 520)


def label_tile(image: Image.Image, label: str, size: tuple[int, int]) -> Image.Image:
    width, height = size
    tile = Image.new("RGB", (width, height + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def make_panel(
    source: Image.Image,
    candidate_overlay: Image.Image,
    boundary_overlay: Image.Image,
    overlap_overlay: Image.Image,
    panel_path: Path,
) -> None:
    crop = crop_box()
    size = (340, 275)
    tiles = [
        label_tile(source.crop(crop), "source crop", size),
        label_tile(candidate_overlay.crop(crop), "candidate nose mask", size),
        label_tile(boundary_overlay.crop(crop), "canonical protected boundaries", size),
        label_tile(overlap_overlay.crop(crop), "candidate + boundaries", size),
    ]
    panel = Image.new("RGB", (len(tiles) * size[0], size[1] + 34), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * size[0], 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    parser.add_argument("--source-image", default=SOURCE_IMAGE)
    parser.add_argument("--candidate-mask", default=CANDIDATE_MASK)
    parser.add_argument("--candidate-overlay", default=CANDIDATE_OVERLAY)
    args = parser.parse_args()

    root = args.project_root
    source_path = resolve_rel(root, args.source_image)
    candidate_mask_path = resolve_rel(root, args.candidate_mask)
    candidate_overlay_path = resolve_rel(root, args.candidate_overlay)
    source = Image.open(source_path).convert("RGB")
    candidate_mask = Image.open(candidate_mask_path).convert("L")
    candidate_overlay = Image.open(candidate_overlay_path).convert("RGB")

    out_dir = root / "runtime_artifacts" / "mask_factory" / "wave70_mf70_nose" / "protected_boundary_audit" / RUN_STAMP
    layers_dir = out_dir / "boundary_layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    region_ids = [
        "mouth_lips",
        "upper_lip",
        "philtrum",
        "left_eye_canthus_lower_lid",
        "right_eye_canthus_lower_lid",
        "left_cheek",
        "right_cheek",
        "nose_target_candidate_boundary",
    ]
    layers: list[dict[str, Any]] = []
    for region_id in region_ids:
        mask = layer_mask(source.size, region_id)
        path = layers_dir / f"{region_id}.png"
        mask.save(path)
        layers.append(
            {
                "region_id": region_id,
                "source": "manual_reviewed_polygon",
                "path": str(path),
                "sha256": sha256_file(path),
                "review_status": "candidate_review_required" if region_id == "nose_target_candidate_boundary" else "manual_boundary_candidate",
            }
        )

    candidate_pixels = pixel_count(binary_mask(candidate_mask))
    overlap_rows: list[dict[str, Any]] = []
    protected_failures: list[str] = []
    for layer in layers:
        if layer["region_id"] == "nose_target_candidate_boundary":
            continue
        protected_mask = Image.open(layer["path"]).convert("L")
        overlap = intersection_count(candidate_mask, protected_mask)
        overlap_percent_of_candidate = round(overlap * 100.0 / candidate_pixels, 4) if candidate_pixels else 0.0
        tolerance = 0 if layer["region_id"] in {"mouth_lips", "upper_lip", "philtrum"} else 12
        passed = overlap <= tolerance
        if not passed:
            protected_failures.append(layer["region_id"])
        overlap_rows.append(
            {
                "target_mask_type_id": MASK_TYPE_ID,
                "protected_region_id": layer["region_id"],
                "overlap_pixels": overlap,
                "overlap_percent_of_candidate": overlap_percent_of_candidate,
                "allowed_overlap_pixels": tolerance,
                "pass": passed,
            }
        )

    matrix_path = out_dir / "mf70_nose_source_landmark_protected_overlap_matrix.csv"
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

    boundary_registry_path = out_dir / "BOUNDARY_REGISTRY_MANIFEST.json"
    # Paths in the manifest should be relative to the project root.
    manifest_layers = []
    for layer in layers:
        manifest_layers.append({**layer, "path": rel(Path(layer["path"]), root)})
    protected_overlap_pass = not protected_failures
    registry = {
        "schema_version": "1.0",
        "boundary_registry": {
            "source_image_id": "active_mod17_canny_v3_seed711570105",
            "matrix_slot_id": "single_anchor_smoke_frontal_neutral",
            "canonical_boundary_layer_pass": False,
            "boundary_layers": manifest_layers,
            "protected_overlap_matrix_path": rel(matrix_path, root),
            "protected_overlap_matrix_sha256": sha256_file(matrix_path),
            "protected_overlap_matrix_pass": protected_overlap_pass,
            "boundary_status": "candidate_registry_pending_human_or_strict_visual_review",
        },
        "policy": "Manual source-derived candidate boundaries for local repair audit only. These are not promoted canonical boundary layers.",
    }
    write_json(boundary_registry_path, registry)

    boundary_overlay = make_boundary_overlay(source, layers)
    overlap_overlay = make_boundary_overlay(candidate_overlay, layers)
    boundary_overlay_path = out_dir / "mf70_nose_candidate_boundary_overlay.png"
    panel_path = out_dir / "mf70_nose_candidate_protected_overlap_panel.png"
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, candidate_overlay, boundary_overlay, overlap_overlay, panel_path)

    evidence_path = root / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70" / f"W70_MF70_NOSE_SOURCE_LANDMARK_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}.json"
    tracker_path = root / "Plan" / "Tracker" / "Evidence" / f"W70_MF70_NOSE_SOURCE_LANDMARK_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}.json"
    result = "pass_candidate_protected_overlap_pending_strict_visual_review" if protected_overlap_pass else "fail_candidate_protected_overlap_requires_geometry_revision"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-NOSE-SOURCE-LANDMARK-PROTECTED-OVERLAP-AUDIT-{RUN_STAMP}",
        "timestamp": "2026-07-07T21:35:00-05:00",
        "project_root": str(root),
        "qa_type": "wave70_mf70_nose_candidate_protected_boundary_overlap_audit",
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
        "candidate_evidence": CANDIDATE_EVIDENCE,
        "candidate_mask": rel(candidate_mask_path, root),
        "candidate_mask_sha256": sha256_file(candidate_mask_path),
        "candidate_overlay": rel(candidate_overlay_path, root),
        "boundary_protocol": BOUNDARY_PROTOCOL,
        "boundary_registry_manifest": rel(boundary_registry_path, root),
        "boundary_registry_manifest_sha256": sha256_file(boundary_registry_path),
        "protected_overlap_matrix": rel(matrix_path, root),
        "protected_overlap_matrix_sha256": sha256_file(matrix_path),
        "boundary_overlay": rel(boundary_overlay_path, root),
        "boundary_overlay_sha256": sha256_file(boundary_overlay_path),
        "review_panel": rel(panel_path, root),
        "review_panel_sha256": sha256_file(panel_path),
        "candidate_pixels": candidate_pixels,
        "protected_overlap_rows": overlap_rows,
        "protected_overlap_failures": protected_failures,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "canonical_boundary_layer_pass": False,
        "completion_allowed_by_boundary_registry": False,
        "result": result,
        "boundary": "Candidate protected-overlap audit only. Even if overlap passes, canonical boundary layers are not promoted and mf70_nose remains failed until strict visual review/fail-closed audit accepts the candidate.",
    }
    write_json(evidence_path, evidence)
    tracker = {
        "schema_version": "1.0",
        "tracker_evidence_id": f"W70_MF70_NOSE_SOURCE_LANDMARK_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}",
        "created_at": "2026-07-07T21:35:00-05:00",
        "project_root": str(root),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "mask_type_id": MASK_TYPE_ID,
        "source_evidence": rel(evidence_path, root),
        "status": "Mask_Alignment_Fail_Generated_Output_Safe_Target_Runtime_Pending",
        "result": result,
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "canonical_boundary_layer_pass": False,
        "review_panel": rel(panel_path, root),
    }
    write_json(tracker_path, tracker)

    print(
        json.dumps(
            {
                "result": result,
                "evidence": rel(evidence_path, root),
                "tracker_evidence": rel(tracker_path, root),
                "boundary_registry": rel(boundary_registry_path, root),
                "overlap_matrix": rel(matrix_path, root),
                "panel": rel(panel_path, root),
                "protected_overlap_matrix_pass": protected_overlap_pass,
                "protected_overlap_failures": protected_failures,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
