#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from audit_wave70_nose_candidate_protected_overlap import (
    BOUNDARY_PROTOCOL,
    ITEM_ID,
    MASK_TYPE_ID,
    SOURCE_IMAGE,
    TRACKER_ID,
    intersection_count,
    make_boundary_overlay,
    make_panel,
    pixel_count,
    rel,
    resolve_rel,
    sha256_file,
    write_json,
)


RUN_STAMP = "20260707T214800-0500"
CANDIDATE_MASK = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_mask.png"
)
CANDIDATE_OVERLAY = (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_overlay.png"
)
CANDIDATE_EVIDENCE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_V2_20260707T214500-0500.json"
)
PRIOR_OVERLAP_AUDIT = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_NOSE_SOURCE_LANDMARK_PROTECTED_OVERLAP_AUDIT_20260707T213500-0500.json"
)


def layer_mask(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "mouth_lips":
        draw.polygon([(318, 452), (350, 442), (394, 446), (437, 443), (470, 454), (452, 484), (394, 493), (337, 484)], fill=255)
    elif region_id == "upper_lip":
        draw.polygon([(327, 445), (356, 439), (393, 444), (431, 440), (463, 452), (441, 462), (394, 458), (346, 461)], fill=255)
    elif region_id == "philtrum":
        draw.polygon([(362, 440), (425, 440), (437, 456), (350, 456)], fill=255)
    elif region_id == "left_eye_canthus_lower_lid":
        draw.ellipse((242, 284, 350, 354), fill=255)
    elif region_id == "right_eye_canthus_lower_lid":
        draw.ellipse((410, 279, 518, 356), fill=255)
    elif region_id == "left_cheek":
        draw.polygon([(236, 356), (348, 356), (346, 442), (236, 494)], fill=255)
    elif region_id == "right_cheek":
        draw.polygon([(438, 356), (542, 346), (544, 505), (438, 448)], fill=255)
    elif region_id == "nose_target_candidate_boundary":
        draw.polygon([(384, 326), (403, 326), (408, 360), (416, 393), (424, 419), (415, 431), (394, 436), (371, 431), (360, 419), (366, 394), (377, 360)], fill=255)
        draw.ellipse((356, 407, 385, 435), fill=255)
        draw.ellipse((401, 407, 427, 435), fill=255)
    else:
        raise ValueError(f"unknown region_id: {region_id}")
    return mask.filter(ImageFilter.GaussianBlur(radius=0.5))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    source_path = resolve_rel(root, SOURCE_IMAGE)
    candidate_mask_path = resolve_rel(root, CANDIDATE_MASK)
    candidate_overlay_path = resolve_rel(root, CANDIDATE_OVERLAY)
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
                "source": "manual_reviewed_polygon_v2",
                "path": str(path),
                "sha256": sha256_file(path),
                "review_status": "candidate_runtime_ready" if region_id == "nose_target_candidate_boundary" else "manual_boundary_candidate_v2",
            }
        )

    candidate_pixels = pixel_count(candidate_mask)
    overlap_rows: list[dict[str, Any]] = []
    protected_failures: list[str] = []
    for layer in layers:
        if layer["region_id"] == "nose_target_candidate_boundary":
            continue
        protected_mask = Image.open(layer["path"]).convert("L")
        overlap = intersection_count(candidate_mask, protected_mask)
        overlap_percent = round(overlap * 100.0 / candidate_pixels, 4) if candidate_pixels else 0.0
        tolerance = 0 if layer["region_id"] in {"mouth_lips", "upper_lip", "philtrum"} else 12
        passed = overlap <= tolerance
        if not passed:
            protected_failures.append(layer["region_id"])
        overlap_rows.append(
            {
                "target_mask_type_id": MASK_TYPE_ID,
                "protected_region_id": layer["region_id"],
                "overlap_pixels": overlap,
                "overlap_percent_of_candidate": overlap_percent,
                "allowed_overlap_pixels": tolerance,
                "pass": passed,
            }
        )

    matrix_path = out_dir / "mf70_nose_source_landmark_v2_protected_overlap_matrix.csv"
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

    manifest_layers = [{**layer, "path": rel(Path(layer["path"]), root)} for layer in layers]
    protected_overlap_pass = not protected_failures
    registry_path = out_dir / "BOUNDARY_REGISTRY_MANIFEST.json"
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
                "boundary_status": "candidate_registry_v2_pending_strict_visual_review",
            },
            "policy": "V2 manual source-derived candidate boundaries for local repair audit only. These are not promoted canonical boundary layers.",
            "prior_overlap_audit": PRIOR_OVERLAP_AUDIT,
        },
    )

    boundary_overlay = make_boundary_overlay(source, layers)
    combined_overlay = make_boundary_overlay(candidate_overlay, layers)
    boundary_overlay_path = out_dir / "mf70_nose_v2_candidate_boundary_overlay.png"
    panel_path = out_dir / "mf70_nose_v2_candidate_protected_overlap_panel.png"
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, candidate_overlay, boundary_overlay, combined_overlay, panel_path)

    evidence_path = root / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70" / f"W70_MF70_NOSE_SOURCE_LANDMARK_V2_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}.json"
    tracker_path = root / "Plan" / "Tracker" / "Evidence" / f"W70_MF70_NOSE_SOURCE_LANDMARK_V2_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}.json"
    result = "pass_candidate_protected_overlap_pending_strict_visual_review" if protected_overlap_pass else "fail_candidate_protected_overlap_requires_geometry_revision"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-NOSE-SOURCE-LANDMARK-V2-PROTECTED-OVERLAP-AUDIT-{RUN_STAMP}",
        "timestamp": "2026-07-07T21:48:00-05:00",
        "project_root": str(root),
        "qa_type": "wave70_mf70_nose_v2_candidate_protected_boundary_overlap_audit",
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
        "boundary_registry_manifest": rel(registry_path, root),
        "boundary_registry_manifest_sha256": sha256_file(registry_path),
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
        "boundary": "V2 candidate protected-overlap audit only. Even if overlap passes, canonical boundary layers are not promoted and mf70_nose remains failed until strict visual review/fail-closed audit accepts the candidate.",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_NOSE_SOURCE_LANDMARK_V2_PROTECTED_OVERLAP_AUDIT_{RUN_STAMP}",
            "created_at": "2026-07-07T21:48:00-05:00",
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
        },
    )
    print(
        json.dumps(
            {
                "result": result,
                "evidence": rel(evidence_path, root),
                "tracker_evidence": rel(tracker_path, root),
                "boundary_registry": rel(registry_path, root),
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
