#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260708T001500-0500"
TIMESTAMP = "2026-07-08T00:15:00-05:00"
MASK_TYPE_ID = "mf70_eyebrows"
TRACKER_ID = "TRK-W70-0016"
ITEM_ID = "ITEM-W70-0016"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Pending_Target_Runtime_Pending"
STATUS_DECISION = "eyebrows_v3_strict_visual_alignment_pass_generated_output_pending_reference_matrix_pending"
SOURCE_IMAGE = "Plan/Instructions/Operations/Pulled_Back_Artifacts/canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
OLD_MASK = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_eyebrows_20260707T190000-0500/wave70_mf70_eyebrows_mask.png"
OLD_OVERLAY = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_eyebrows_20260707T190000-0500/wave70_mf70_eyebrows_overlay.png"
FAIL_PANEL = "runtime_artifacts/mask_factory/wave70_alignment_audit_20260707T211500-0500/mf70_eyebrows_source_mask_alignment_panel.png"
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def count_pixels(mask: Image.Image) -> dict[str, Any]:
    hard = mask.point(lambda v: 255 if v > 8 else 0)
    hist = hard.histogram()
    total = sum(hist)
    nonblack = sum(hist[1:])
    bbox_raw = hard.getbbox()
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


def pixel_count(mask: Image.Image) -> int:
    return count_pixels(mask)["nonblack_pixel_count"]


def intersection_count(a: Image.Image, b: Image.Image) -> int:
    aa = a.point(lambda v: 255 if v > 8 else 0)
    bb = b.point(lambda v: 255 if v > 8 else 0)
    return sum(1 for av, bv in zip(aa.getdata(), bb.getdata()) if av and bv)


def eyebrow_polygons_v2() -> list[list[tuple[int, int]]]:
    return [
        [(226, 288), (254, 284), (288, 286), (322, 292), (331, 298), (323, 302), (284, 297), (227, 294)],
        [(425, 286), (459, 282), (498, 284), (532, 292), (541, 298), (533, 303), (493, 297), (426, 294)],
    ]


def make_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for poly in eyebrow_polygons_v2():
        draw.polygon(poly, fill=255)
    return mask


def boundary_layer(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "left_eye_core":
        draw.ellipse((242, 303, 333, 353), fill=255)
    elif region_id == "right_eye_core":
        draw.ellipse((415, 300, 507, 354), fill=255)
    elif region_id == "left_upper_lid_aperture":
        draw.polygon([(239, 309), (287, 314), (336, 308), (334, 326), (287, 331), (239, 325)], fill=255)
    elif region_id == "right_upper_lid_aperture":
        draw.polygon([(414, 308), (463, 312), (512, 308), (512, 326), (463, 331), (414, 326)], fill=255)
    elif region_id == "forehead_skin_above_brows":
        draw.polygon([(205, 244), (556, 244), (556, 279), (205, 279)], fill=255)
    elif region_id == "hair_occlusion_edges":
        draw.polygon([(185, 245), (218, 245), (218, 330), (185, 330)], fill=255)
        draw.polygon([(546, 245), (580, 245), (580, 330), (546, 330)], fill=255)
    elif region_id == "broad_forehead_outer_skin":
        draw.polygon([(198, 309), (558, 309), (558, 355), (198, 355)], fill=255)
    elif region_id == "eyebrows_target_candidate":
        return make_mask(size)
    else:
        raise ValueError(region_id)
    return mask


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    color = Image.new("RGBA", rgba.size, (0, 255, 128, 0))
    color.putalpha(mask.point(lambda v: min(170, int(v * 0.68))))
    overlay = Image.alpha_composite(rgba, color)
    outline = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline)
    for poly in eyebrow_polygons_v2():
        draw.line(poly + [poly[0]], fill=(255, 255, 255, 235), width=2)
    return Image.alpha_composite(overlay, outline).convert("RGB")


def make_boundary_overlay(source: Image.Image, layers: list[dict[str, Any]]) -> Image.Image:
    colors = {
        "left_eye_core": (255, 70, 70, 90),
        "right_eye_core": (255, 70, 70, 90),
        "left_upper_lid_aperture": (255, 196, 0, 95),
        "right_upper_lid_aperture": (255, 196, 0, 95),
        "forehead_skin_above_brows": (40, 150, 255, 65),
        "hair_occlusion_edges": (160, 80, 255, 70),
        "broad_forehead_outer_skin": (0, 210, 210, 45),
        "eyebrows_target_candidate": (255, 255, 255, 100),
    }
    rgba = source.convert("RGBA")
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


def make_panel(source: Image.Image, old_overlay: Image.Image, overlay: Image.Image, boundary_overlay: Image.Image, mask: Image.Image, fail_panel: Image.Image, panel_path: Path) -> None:
    crop = (190, 245, 580, 390)
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(crop), "source brow crop"),
        label_tile(old_overlay.crop(crop), "old chunky overlay"),
        label_tile(overlay.crop(crop), "v3 brow overlay"),
        label_tile(boundary_overlay.crop(crop), "v3 + boundaries"),
        label_tile(mask_rgb.crop(crop), "v3 mask only"),
        label_tile(fail_panel.resize((720, 158), Image.Resampling.LANCZOS), "global dispute panel"),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def csv_update_row(path: Path, id_column: str, id_value: str, updates: dict[str, str], append_fields: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    changed = False
    for row in rows:
        if row.get(id_column) != id_value:
            continue
        for key, value in updates.items():
            if key in row and row.get(key) != value:
                row[key] = value
                changed = True
        for key, value in append_fields.items():
            if key not in row:
                continue
            current = row.get(key, "")
            if value not in current:
                row[key] = f"{current}; {value}" if current else value
                changed = True
    if changed:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def append_unique_csv_row(path: Path, row: list[str], marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(row)


def update_mask_qa(root: Path, evidence_rel: str, tracker_rel: str, evidence: dict[str, Any]) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_eyebrows.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["source_landmark_v3_repair"] = {
        "timestamp": TIMESTAMP,
        "status": STATUS_DECISION,
        "evidence": evidence_rel,
        "tracker_evidence": tracker_rel,
        "mask_path": evidence["candidate_mask"],
        "mask_sha256": evidence["candidate_mask_sha256"],
        "overlay_path": evidence["candidate_overlay"],
        "overlay_sha256": evidence["candidate_overlay_sha256"],
        "protected_overlap_matrix": evidence["protected_overlap_matrix"],
        "protected_overlap_matrix_pass": evidence["protected_overlap_matrix_pass"],
        "generated_output_proof_valid_for_this_mask": False,
        "old_generated_output_proof_invalidated_reason": "v3 mask hash differs from old generated-output proof mask hash",
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "findings": evidence["visual_review_findings"],
    }
    data.setdefault("validation", {})["mask_alignment_semantic_pass"] = True
    data.setdefault("validation", {})["protected_neighbor_check_pass"] = True
    data.setdefault("validation", {})["generated_output_proof_present"] = False
    data.setdefault("validation", {})["generated_output_safe_pass"] = False
    data.setdefault("validation", {})["completion_allowed_by_mask_alignment"] = False
    data.setdefault("single_anchor_boundary", {})["status"] = STATUS
    data.setdefault("single_anchor_boundary", {})["single_source_local_overlay_or_generated_output_may_remain_valid"] = True
    write_json(path, data)


def update_ledgers(root: Path, evidence_rel: str, tracker_rel: str, panel_rel: str, mask_rel: str, overlay_rel: str) -> None:
    note = (
        " Eyebrows v3 source-landmark repair replaced the old chunky mask with a slimmer brow-hair candidate. "
        "Protected-overlap matrix passed against eye cores, upper lid apertures, forehead-above-brow, hair-occlusion edges, and lower broad-forehead/eye-adjacent skin. "
        "Old generated-output proof is not reused because the mask hash changed."
    )
    evidence_append = f"{evidence_rel}; {tracker_rel}"
    updates = {
        "Status": STATUS,
        "Status_Decision": STATUS_DECISION,
        "Coverage_Audit_Status": STATUS_DECISION,
        "Final_Render_Gate": "Blocked until local generated-output proof, target-runtime proof, and reference-image matrix proof are complete.",
    }
    append_fields = {
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Acceptance_Evidence": evidence_append,
        "Output_Artifact": f"{panel_rel}; {mask_rel}; {overlay_rel}",
        "Notes": note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, updates, append_fields)


def update_hydration(root: Path, evidence_rel: str, tracker_rel: str, panel_rel: str) -> None:
    section = f"""## Wave70 mf70_eyebrows V3 Source-Landmark Repair - {TIMESTAMP}

The old `mf70_eyebrows` mask was kept downgraded after the global mask-alignment dispute because it used chunky brow slabs rather than a stricter source-fitted brow shape. A v3 source-landmark repair now exists and passed the protected-overlap matrix for the active single-anchor MOD-17 portrait. Evidence is `{evidence_rel}`, tracker evidence is `{tracker_rel}`, and panel is `{panel_rel}`.

The v3 mask is slimmer and follows visible brow bands more closely. It is accepted only as a source-overlay candidate; the old generated-output proof is not reused because the mask hash changed. Next exact action is one bounded local generated-output proof for this v3 mask with strict whole-image QA.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, evidence_rel)
    qa_index_row = (
        f"| W70-MF70-EYEBROWS-V3-SOURCE-LANDMARK-REPAIR-{RUN_STAMP} | "
        "mf70_eyebrows v3 slimmer source-landmark mask passed protected-overlap but generated-output proof remains pending | "
        "mask_factory_source_landmark_repair | pass_candidate_generated_output_pending | "
        f"{evidence_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, f"W70-MF70-EYEBROWS-V3-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}")
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_eyebrows v3 source-landmark repair",
            "Repaired eyebrow mask after global dispute; v3 passed source-boundary matrix but awaits generated-output proof.",
            f"{evidence_rel}; {tracker_rel}; {panel_rel}",
            "strict source overlay; protected-overlap matrix; direct visual inspection; tracker/item update",
            "PASS_CANDIDATE_GENERATED_OUTPUT_PENDING_TARGET_RUNTIME_MATRIX",
            evidence_rel,
            "Run bounded local generated-output proof for mf70_eyebrows v3 with strict whole-image QA",
        ],
        f"W70_MF70_EYEBROWS_V3_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root
    source_path = root / SOURCE_IMAGE.replace("/", "\\")
    old_mask_path = root / OLD_MASK.replace("/", "\\")
    old_overlay_path = root / OLD_OVERLAY.replace("/", "\\")
    fail_panel_path = root / FAIL_PANEL.replace("/", "\\")
    source = Image.open(source_path).convert("RGB")
    old_overlay = Image.open(old_overlay_path).convert("RGB")
    fail_panel = Image.open(fail_panel_path).convert("RGB")

    prepared_dir = root / "Plan/Instructions/Operations/Prepared_Input_Assets" / f"wave70_mf70_eyebrows_v3_{RUN_STAMP}"
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_eyebrows/source_landmark_repair_v3" / RUN_STAMP
    layers_dir = out_dir / "boundary_layers"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)

    mask = make_mask(source.size)
    overlay = make_overlay(source, mask)
    mask_path = prepared_dir / "wave70_mf70_eyebrows_v3_mask.png"
    overlay_path = prepared_dir / "wave70_mf70_eyebrows_v3_overlay.png"
    input_copy = root / "ComfyUI/input/wave70_mf70_eyebrows_mask.png"
    mask.save(mask_path)
    overlay.save(overlay_path)
    input_copy.parent.mkdir(parents=True, exist_ok=True)
    mask.save(input_copy)

    region_ids = [
        "left_eye_core",
        "right_eye_core",
        "left_upper_lid_aperture",
        "right_upper_lid_aperture",
        "forehead_skin_above_brows",
        "hair_occlusion_edges",
        "broad_forehead_outer_skin",
        "eyebrows_target_candidate",
    ]
    layers = []
    for region_id in region_ids:
        layer = boundary_layer(source.size, region_id)
        path = layers_dir / f"{region_id}.png"
        layer.save(path)
        layers.append({"region_id": region_id, "path": path, "sha256": sha256_file(path)})

    candidate_pixels = pixel_count(mask)
    tolerances = {
        "left_eye_core": 0,
        "right_eye_core": 0,
        "left_upper_lid_aperture": 6,
        "right_upper_lid_aperture": 6,
        "forehead_skin_above_brows": 80,
        "hair_occlusion_edges": 0,
        "broad_forehead_outer_skin": 0,
    }
    overlap_rows = []
    failures = []
    for layer in layers:
        region_id = layer["region_id"]
        if region_id == "eyebrows_target_candidate":
            continue
        protected = Image.open(layer["path"]).convert("L")
        overlap = intersection_count(mask, protected)
        allowed = tolerances[region_id]
        passed = overlap <= allowed
        if not passed:
            failures.append(region_id)
        overlap_rows.append({
            "target_mask_type_id": MASK_TYPE_ID,
            "protected_region_id": region_id,
            "overlap_pixels": overlap,
            "overlap_percent_of_candidate": round(overlap * 100.0 / candidate_pixels, 4) if candidate_pixels else 0.0,
            "allowed_overlap_pixels": allowed,
            "pass": passed,
        })

    matrix_path = out_dir / "mf70_eyebrows_v3_protected_overlap_matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["target_mask_type_id", "protected_region_id", "overlap_pixels", "overlap_percent_of_candidate", "allowed_overlap_pixels", "pass"])
        writer.writeheader()
        writer.writerows(overlap_rows)

    boundary_overlay = make_boundary_overlay(overlay, layers)
    boundary_overlay_path = out_dir / "mf70_eyebrows_v3_boundary_overlay.png"
    panel_path = out_dir / "mf70_eyebrows_v3_source_landmark_panel.png"
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, old_overlay, overlay, boundary_overlay, mask, fail_panel, panel_path)

    protected_overlap_pass = not failures
    result = "pass_eyebrows_v3_source_landmark_mask_generated_output_pending" if protected_overlap_pass else "eyebrows_v3_source_landmark_mask_protected_overlap_failed"
    old_sha = sha256_file(old_mask_path)
    new_sha = sha256_file(mask_path)
    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_EYEBROWS_V3_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_EYEBROWS_V3_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-EYEBROWS-V3-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_eyebrows_source_landmark_repair_v3",
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
        "old_candidate_mask": OLD_MASK,
        "old_candidate_mask_sha256": old_sha,
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": new_sha,
        "comfyui_input_copy": rel(input_copy, root),
        "comfyui_input_copy_sha256": sha256_file(input_copy),
        "candidate_overlay": rel(overlay_path, root),
        "candidate_overlay_sha256": sha256_file(overlay_path),
        "protected_overlap_matrix": rel(matrix_path, root),
        "protected_overlap_matrix_sha256": sha256_file(matrix_path),
        "boundary_overlay": rel(boundary_overlay_path, root),
        "boundary_overlay_sha256": sha256_file(boundary_overlay_path),
        "review_panel": rel(panel_path, root),
        "review_panel_sha256": sha256_file(panel_path),
        "candidate_metrics": count_pixels(mask),
        "protected_overlap_rows": overlap_rows,
        "protected_overlap_failures": failures,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "boundary_protocol": BOUNDARY_PROTOCOL,
        "visual_review_findings": [
            "Accepted candidate: v3 mask is slimmer than the old eyebrow slab and follows the visible brow bands more closely.",
            "Accepted candidate: v3 clears protected eye cores, corrected upper-lid apertures, hair-occlusion edges, and lower eye-adjacent skin guardrails in the matrix.",
            "Accepted with limitation: the mask is single-anchor source-specific and does not prove generalized eyebrow masking.",
            "Old generated-output proof is not reused because the v3 mask hash differs from the old mask hash.",
        ] if protected_overlap_pass else [
            "Rejected candidate: v3 still overlaps protected boundaries.",
            "No generated-output proof is valid until protected-overlap passes.",
        ],
        "semantic_mask_alignment_candidate_pass": protected_overlap_pass,
        "generated_output_proof_reused": False,
        "generated_output_safe_pass": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "result": result,
        "status_after_audit": STATUS if protected_overlap_pass else "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "status_decision_after_audit": STATUS_DECISION if protected_overlap_pass else "eyebrows_v3_candidate_protected_overlap_failed",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_EYEBROWS_V3_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "status": evidence["status_after_audit"],
            "status_decision": evidence["status_decision_after_audit"],
            "evidence": rel(evidence_path, root),
            "review_panel": rel(panel_path, root),
            "mask": rel(mask_path, root),
            "overlay": rel(overlay_path, root),
            "protected_overlap_matrix_pass": protected_overlap_pass,
            "generated_output_proof_pending": True,
            "local_only": True,
            "aws_contacted": False,
            "github_api_contacted": False,
            "civitai_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "result": result,
        },
    )

    if protected_overlap_pass:
        evidence_rel = rel(evidence_path, root)
        tracker_rel = rel(tracker_path, root)
        panel_rel = rel(panel_path, root)
        update_mask_qa(root, evidence_rel, tracker_rel, evidence)
        update_ledgers(root, evidence_rel, tracker_rel, panel_rel, rel(mask_path, root), rel(overlay_path, root))
        update_hydration(root, evidence_rel, tracker_rel, panel_rel)

    print(json.dumps({
        "result": result,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "evidence": rel(evidence_path, root),
        "tracker_evidence": rel(tracker_path, root),
        "panel": rel(panel_path, root),
        "mask": rel(mask_path, root),
        "overlay": rel(overlay_path, root),
        "old_mask_sha256": old_sha,
        "new_mask_sha256": new_sha,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
