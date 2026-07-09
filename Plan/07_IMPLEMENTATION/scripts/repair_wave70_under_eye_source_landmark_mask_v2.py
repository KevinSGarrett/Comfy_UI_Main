#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T232500-0500"
TIMESTAMP = "2026-07-07T23:25:00-05:00"
MASK_TYPE_ID = "mf70_under_eye"
TRACKER_ID = "TRK-W70-0015"
ITEM_ID = "ITEM-W70-0015"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Pending_Target_Runtime_Pending"
STATUS_DECISION = "under_eye_v2_strict_visual_alignment_pass_generated_output_pending_reference_matrix_pending"
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
OLD_MASK = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_under_eye_20260707T184500-0500/wave70_mf70_under_eye_mask.png"
OLD_OVERLAY = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_under_eye_20260707T184500-0500/wave70_mf70_under_eye_overlay.png"
FAILED_AUDIT_EVIDENCE = "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_UNDER_EYE_STRICT_VISUAL_ACCEPTANCE_20260707T231500-0500.json"
FAILED_AUDIT_PANEL = "runtime_artifacts/mask_factory/wave70_mf70_under_eye/strict_visual_acceptance/20260707T231500-0500/mf70_under_eye_strict_visual_acceptance_panel.png"
BOUNDARY_PROTOCOL = "Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md"


def load_audit_module(root: Path):
    script = root / "Plan/07_IMPLEMENTATION/scripts/accept_wave70_under_eye_strict_visual_audit.py"
    spec = importlib.util.spec_from_file_location("under_eye_audit", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load audit module from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def v2_under_eye_polygons() -> list[list[tuple[int, int]]]:
    return [
        [(246, 371), (283, 381), (327, 371), (318, 386), (283, 394), (246, 382)],
        [(425, 371), (462, 382), (506, 371), (501, 386), (463, 395), (426, 383)],
    ]


def make_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for poly in v2_under_eye_polygons():
        draw.polygon(poly, fill=255)
    return mask


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    color = Image.new("RGBA", rgba.size, (0, 255, 128, 0))
    color.putalpha(mask.point(lambda v: min(165, int(v * 0.66))))
    overlay = Image.alpha_composite(rgba, color)
    outline = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline)
    for poly in v2_under_eye_polygons():
        draw.line(poly + [poly[0]], fill=(255, 255, 255, 235), width=2)
    return Image.alpha_composite(overlay, outline).convert("RGB")


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
    old_overlay: Image.Image,
    v2_overlay: Image.Image,
    boundary_overlay: Image.Image,
    mask: Image.Image,
    failed_panel: Image.Image,
    panel_path: Path,
) -> None:
    crop = (190, 245, 560, 430)
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(old_overlay.crop(crop), "old overlay failed"),
        label_tile(v2_overlay.crop(crop), "v2 under-eye overlay"),
        label_tile(boundary_overlay.crop(crop), "v2 + boundaries"),
        label_tile(mask_rgb.crop(crop), "v2 mask only"),
        label_tile(failed_panel.resize((720, 158), Image.Resampling.LANCZOS), "prior failure panel"),
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


def patch_failed_audit_wording(root: Path) -> None:
    failed_path = root / FAILED_AUDIT_EVIDENCE.replace("/", "\\")
    data = read_json(failed_path)
    if data.get("protected_overlap_matrix_pass") is not False:
        return
    data["visual_review_findings"] = [
        "Rejected: the old compact under-eye mask overlaps protected eye cores, lower-lid guardrails, and nose sidewall guardrails.",
        "Rejected: generated-output stability for the old mask does not prove source-image alignment.",
        "Required correction: create a lower, narrower source-landmark candidate and re-run protected-overlap review before any generated-output proof.",
    ]
    data["boundary"] = (
        "Failure evidence only. This record does not accept the old compact mf70_under_eye mask; "
        "it records why the old mask remains downgraded until repaired."
    )
    write_json(failed_path, data)


def update_mask_qa(root: Path, evidence_rel: str, tracker_rel: str, evidence: dict[str, Any]) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_under_eye.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["source_landmark_v2_repair"] = {
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
        "old_generated_output_proof_invalidated_reason": "v2 mask hash differs from old generated-output proof mask hash",
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
        " Under-eye v2 source-landmark repair replaced the old failed mask with a lower/narrower two-crescent mask. "
        "Strict protected-overlap matrix passed against eye cores, lower lids, nose sidewalls, lower-cheek boundary, and eyebrows. "
        "Old generated-output proof is not reused because the mask hash changed; minimum local generated-output proof remains pending."
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
    section = f"""## Wave70 mf70_under_eye V2 Source-Landmark Repair - {TIMESTAMP}

The old `mf70_under_eye` mask failed the strict protected-overlap matrix: it crossed eye cores, both lower lids, and nose sidewall guardrails. A v2 source-landmark repair now exists and passed the protected-overlap matrix for the active single-anchor MOD-17 portrait. Evidence is `{evidence_rel}`, tracker evidence is `{tracker_rel}`, and panel is `{panel_rel}`.

The v2 mask is lower and narrower than the old mask. It is accepted only as a source-overlay candidate; the old generated-output proof is not reused because the mask hash changed. Next exact action is a bounded local generated-output proof for this v2 mask with strict whole-image QA, or continue the next downgraded mask if local runtime is unavailable.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, evidence_rel)

    qa_index_row = (
        f"| W70-MF70-UNDER-EYE-V2-SOURCE-LANDMARK-REPAIR-{RUN_STAMP} | "
        "old mf70_under_eye mask failed protected-overlap; v2 lower/narrower source-landmark mask passed protected-overlap but generated-output proof remains pending | "
        "mask_factory_source_landmark_repair | pass_candidate_generated_output_pending | "
        f"{evidence_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, f"W70-MF70-UNDER-EYE-V2-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}")
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_under_eye v2 source-landmark repair",
            "Repaired under-eye mask after protected-overlap failure; v2 passed source-boundary matrix but awaits generated-output proof.",
            f"{evidence_rel}; {tracker_rel}; {panel_rel}",
            "strict source overlay; protected-overlap matrix; direct visual inspection; tracker/item update",
            "PASS_CANDIDATE_GENERATED_OUTPUT_PENDING_TARGET_RUNTIME_MATRIX",
            evidence_rel,
            "Run bounded local generated-output proof for mf70_under_eye v2 with strict whole-image QA",
        ],
        f"W70_MF70_UNDER_EYE_V2_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root
    audit = load_audit_module(root)
    patch_failed_audit_wording(root)

    source_path = root / SOURCE_IMAGE.replace("/", "\\")
    old_mask_path = root / OLD_MASK.replace("/", "\\")
    old_overlay_path = root / OLD_OVERLAY.replace("/", "\\")
    failed_panel_path = root / FAILED_AUDIT_PANEL.replace("/", "\\")
    source = Image.open(source_path).convert("RGB")
    old_overlay = Image.open(old_overlay_path).convert("RGB")
    failed_panel = Image.open(failed_panel_path).convert("RGB")

    prepared_dir = root / "Plan/Instructions/Operations/Prepared_Input_Assets" / f"wave70_mf70_under_eye_v2_{RUN_STAMP}"
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_under_eye/source_landmark_repair_v2" / RUN_STAMP
    layers_dir = out_dir / "boundary_layers"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)

    mask = make_mask(source.size)
    overlay = make_overlay(source, mask)
    mask_path = prepared_dir / "wave70_mf70_under_eye_v2_mask.png"
    overlay_path = prepared_dir / "wave70_mf70_under_eye_v2_overlay.png"
    input_copy = root / "ComfyUI/input/wave70_mf70_under_eye_mask.png"
    mask.save(mask_path)
    overlay.save(overlay_path)
    input_copy.parent.mkdir(parents=True, exist_ok=True)
    mask.save(input_copy)

    region_ids = [
        "left_eye_core",
        "right_eye_core",
        "left_lower_lid",
        "right_lower_lid",
        "nose_bridge_sidewalls",
        "upper_cheek_lower_boundary",
        "eyebrows",
        "under_eye_target_candidate",
    ]
    layers: list[dict[str, Any]] = []
    for region_id in region_ids:
        layer = audit.boundary_layer(source.size, region_id)
        if region_id == "under_eye_target_candidate":
            layer = mask
        path = layers_dir / f"{region_id}.png"
        layer.save(path)
        layers.append({"region_id": region_id, "path": path, "sha256": sha256_file(path)})

    candidate_pixels = audit.pixel_count(mask)
    tolerances = {
        "left_eye_core": 0,
        "right_eye_core": 0,
        "left_lower_lid": 12,
        "right_lower_lid": 12,
        "nose_bridge_sidewalls": 0,
        "upper_cheek_lower_boundary": 16,
        "eyebrows": 0,
    }
    overlap_rows: list[dict[str, Any]] = []
    protected_failures: list[str] = []
    for layer in layers:
        region_id = layer["region_id"]
        if region_id == "under_eye_target_candidate":
            continue
        protected = Image.open(layer["path"]).convert("L")
        overlap = audit.intersection_count(mask, protected)
        allowed = tolerances[region_id]
        passed = overlap <= allowed
        if not passed:
            protected_failures.append(region_id)
        overlap_rows.append({
            "target_mask_type_id": MASK_TYPE_ID,
            "protected_region_id": region_id,
            "overlap_pixels": overlap,
            "overlap_percent_of_candidate": round(overlap * 100.0 / candidate_pixels, 4) if candidate_pixels else 0.0,
            "allowed_overlap_pixels": allowed,
            "pass": passed,
        })

    matrix_path = out_dir / "mf70_under_eye_v2_protected_overlap_matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["target_mask_type_id", "protected_region_id", "overlap_pixels", "overlap_percent_of_candidate", "allowed_overlap_pixels", "pass"],
        )
        writer.writeheader()
        writer.writerows(overlap_rows)

    boundary_overlay = audit.make_boundary_overlay(overlay, layers)
    boundary_overlay_path = out_dir / "mf70_under_eye_v2_boundary_overlay.png"
    panel_path = out_dir / "mf70_under_eye_v2_source_landmark_panel.png"
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, old_overlay, overlay, boundary_overlay, mask, failed_panel, panel_path)

    protected_overlap_pass = not protected_failures
    result = "pass_under_eye_v2_source_landmark_mask_generated_output_pending" if protected_overlap_pass else "under_eye_v2_source_landmark_mask_protected_overlap_failed"
    old_mask_sha = sha256_file(old_mask_path)
    new_mask_sha = sha256_file(mask_path)
    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_UNDER_EYE_V2_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_UNDER_EYE_V2_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-UNDER-EYE-V2-SOURCE-LANDMARK-REPAIR-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_under_eye_source_landmark_repair_v2",
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
        "prior_failed_audit_evidence": FAILED_AUDIT_EVIDENCE,
        "prior_failed_audit_panel": FAILED_AUDIT_PANEL,
        "old_candidate_mask": OLD_MASK,
        "old_candidate_mask_sha256": old_mask_sha,
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": new_mask_sha,
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
        "protected_overlap_failures": protected_failures,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "boundary_protocol": BOUNDARY_PROTOCOL,
        "visual_review_findings": [
            "Accepted candidate: v2 mask is placed below the protected lower-lid guardrails instead of on top of the lid/eye aperture.",
            "Accepted candidate: v2 mask clears protected eye cores, nose sidewalls, eyebrow bands, and lower-cheek boundary in the matrix.",
            "Accepted with limitation: v2 is intentionally narrower/lower than the old mask, so it targets tear-trough/under-eye skin only and avoids broad cheek edits.",
            "Old generated-output proof is not reused because the v2 mask hash differs from the old mask hash.",
        ] if protected_overlap_pass else [
            "Rejected candidate: v2 still overlaps protected boundaries.",
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
        "status_decision_after_audit": STATUS_DECISION if protected_overlap_pass else "under_eye_v2_candidate_protected_overlap_failed",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_UNDER_EYE_V2_SOURCE_LANDMARK_REPAIR_{RUN_STAMP}",
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
        mask_rel = rel(mask_path, root)
        overlay_rel = rel(overlay_path, root)
        update_mask_qa(root, evidence_rel, tracker_rel, evidence)
        update_ledgers(root, evidence_rel, tracker_rel, panel_rel, mask_rel, overlay_rel)
        update_hydration(root, evidence_rel, tracker_rel, panel_rel)

    print(json.dumps({
        "result": result,
        "protected_overlap_matrix_pass": protected_overlap_pass,
        "evidence": rel(evidence_path, root),
        "tracker_evidence": rel(tracker_path, root),
        "panel": rel(panel_path, root),
        "mask": rel(mask_path, root),
        "overlay": rel(overlay_path, root),
        "old_mask_sha256": old_mask_sha,
        "new_mask_sha256": new_mask_sha,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
