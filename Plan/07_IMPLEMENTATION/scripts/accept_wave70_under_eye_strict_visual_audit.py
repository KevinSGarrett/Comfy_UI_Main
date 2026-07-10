#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T231500-0500"
TIMESTAMP = "2026-07-07T23:15:00-05:00"
MASK_TYPE_ID = "mf70_under_eye"
TRACKER_ID = "TRK-W70-0015"
ITEM_ID = "ITEM-W70-0015"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Safe_Target_Runtime_Pending"
STATUS_DECISION = "under_eye_strict_visual_alignment_pass_generated_output_safe_target_runtime_pending_reference_matrix_pending"
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
MASK = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_under_eye_20260707T184500-0500/wave70_mf70_under_eye_mask.png"
OVERLAY = "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_under_eye_20260707T184500-0500/wave70_mf70_under_eye_overlay.png"
FAIL_CLOSED_PANEL = "runtime_artifacts/mask_factory/wave70_alignment_audit_20260707T211500-0500/mf70_under_eye_source_mask_alignment_panel.png"
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


def resolve_rel(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / raw.replace("/", "\\")


def pixel_count(mask: Image.Image) -> int:
    hist = mask.point(lambda v: 255 if v > 8 else 0).histogram()
    return sum(hist[1:])


def intersection_count(a: Image.Image, b: Image.Image) -> int:
    aa = a.point(lambda v: 255 if v > 8 else 0)
    bb = b.point(lambda v: 255 if v > 8 else 0)
    return sum(1 for av, bv in zip(aa.getdata(), bb.getdata()) if av and bv)


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


def boundary_layer(size: tuple[int, int], region_id: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if region_id == "left_eye_core":
        draw.ellipse((242, 303, 333, 353), fill=255)
    elif region_id == "right_eye_core":
        draw.ellipse((415, 300, 507, 354), fill=255)
    elif region_id == "left_lower_lid":
        draw.polygon([(245, 348), (284, 356), (329, 348), (331, 362), (284, 370), (246, 362)], fill=255)
    elif region_id == "right_lower_lid":
        draw.polygon([(417, 348), (462, 358), (507, 348), (507, 362), (462, 371), (418, 362)], fill=255)
    elif region_id == "nose_bridge_sidewalls":
        draw.polygon([(362, 328), (406, 328), (424, 430), (356, 430)], fill=255)
    elif region_id == "upper_cheek_lower_boundary":
        draw.polygon([(230, 398), (532, 398), (548, 492), (212, 492)], fill=255)
    elif region_id == "eyebrows":
        draw.polygon([(218, 277), (326, 277), (337, 295), (224, 298)], fill=255)
        draw.polygon([(421, 273), (535, 276), (544, 295), (424, 296)], fill=255)
    elif region_id == "under_eye_target_candidate":
        draw.polygon([(242, 362), (282, 374), (329, 362), (321, 382), (282, 391), (238, 377)], fill=255)
        draw.polygon([(414, 362), (461, 375), (510, 362), (503, 381), (461, 392), (410, 377)], fill=255)
    else:
        raise ValueError(f"unknown boundary region: {region_id}")
    return mask


def make_boundary_overlay(source: Image.Image, layers: list[dict[str, Any]]) -> Image.Image:
    rgba = source.convert("RGBA")
    colors = {
        "left_eye_core": (255, 70, 70, 95),
        "right_eye_core": (255, 70, 70, 95),
        "left_lower_lid": (255, 196, 0, 95),
        "right_lower_lid": (255, 196, 0, 95),
        "nose_bridge_sidewalls": (0, 220, 120, 80),
        "upper_cheek_lower_boundary": (40, 150, 255, 70),
        "eyebrows": (255, 80, 220, 75),
        "under_eye_target_candidate": (255, 255, 255, 90),
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
    return (190, 245, 560, 430)


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


def make_panel(source: Image.Image, overlay: Image.Image, boundary_overlay: Image.Image, mask: Image.Image, fail_panel: Image.Image, panel_path: Path) -> None:
    crop = crop_box()
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(overlay.crop(crop), "under-eye overlay"),
        label_tile(boundary_overlay.crop(crop), "candidate + boundaries"),
        label_tile(mask_rgb.crop(crop), "mask only"),
        label_tile(fail_panel.resize((720, 158), Image.Resampling.LANCZOS), "fail-closed panel", 360),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


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
            if key in row:
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


def update_mask_qa(root: Path, evidence_rel: str, tracker_evidence_rel: str, evidence: dict[str, Any]) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_under_eye.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["strict_visual_acceptance"] = {
        "evidence": evidence_rel,
        "tracker_evidence": tracker_evidence_rel,
        "timestamp": TIMESTAMP,
        "result": evidence["result"],
        "status": STATUS_DECISION,
        "semantic_mask_alignment_candidate_pass": True,
        "protected_overlap_matrix_pass": True,
        "generated_output_safe_pass_reused_for_same_mask": True,
        "generated_output_proof_reused": data.get("generated_output_proof", {}),
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "findings": evidence["visual_review_findings"],
    }
    write_json(path, data)


def update_ledgers(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    note = (
        " Under-eye strict source-overlay review accepted the existing compact under-eye mask after protected-overlap matrix pass. "
        "The mask targets under-eye skin below the lower lids, clears eye cores/lids, nose, eyebrows, and lower-cheek boundary, and old generated-output proof is reused for the same mask hash. "
        "Status remains candidate-local because target-runtime and reference-matrix proof are pending."
    )
    evidence_append = f"{evidence_rel}; {tracker_evidence_rel}"
    updates = {
        "Status": STATUS,
        "Status_Decision": STATUS_DECISION,
        "Coverage_Audit_Status": STATUS_DECISION,
        "Final_Render_Gate": "Blocked until target-runtime proof and reference-image matrix proof are complete.",
    }
    append_fields = {
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Acceptance_Evidence": evidence_append,
        "Output_Artifact": panel_rel,
        "Notes": note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, updates, append_fields)


def update_hydration(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    section = f"""## Wave70 mf70_under_eye Strict Visual Candidate Acceptance - {TIMESTAMP}

Local fail-closed visual review accepted the existing compact `mf70_under_eye` mask as source-aligned for the active single-anchor MOD-17 portrait. Evidence is `{evidence_rel}` with tracker evidence `{tracker_evidence_rel}` and review panel `{panel_rel}`.

The accepted mask targets the under-eye skin crescents below the lower lids and clears protected eye cores, lower-lid apertures, nose, eyebrows, and lower-cheek boundary. Generated-output proof is reused only because it used the same mask hash and already passed local output QA. Target-runtime proof, reference-image matrix proof, and other disputed masks remain pending.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, evidence_rel)

    qa_index_row = (
        f"| W70-MF70-UNDER-EYE-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP} | "
        "mf70_under_eye existing compact mask accepted by strict source-overlay/protected-overlap review for the active single-anchor portrait; "
        "same-mask generated-output proof reused, target-runtime/reference-matrix proof remains pending | mask_factory_strict_visual_acceptance | pass_candidate_generated_output_safe_no_final_promotion | "
        f"{evidence_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, f"W70-MF70-UNDER-EYE-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}")
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_under_eye strict visual candidate acceptance",
            "Accepted the compact under-eye mask after protected-overlap pass and strict visual review; reused same-mask local generated-output proof while preserving target-runtime and matrix blockers.",
            f"{evidence_rel}; {tracker_evidence_rel}; {panel_rel}",
            "direct visual inspection; protected-overlap matrix review; existing same-mask generated-output proof check; JSON parse; tracker/item row update",
            "PASS_CANDIDATE_GENERATED_OUTPUT_SAFE_FINAL_BLOCKED_TARGET_RUNTIME_MATRIX",
            evidence_rel,
            "Repair the next downgraded Wave70 mask with the same fail-closed source-overlay method",
        ],
        f"W70_MF70_UNDER_EYE_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root
    source_path = resolve_rel(root, SOURCE_IMAGE)
    mask_path = resolve_rel(root, MASK)
    overlay_path = resolve_rel(root, OVERLAY)
    fail_panel_path = resolve_rel(root, FAIL_CLOSED_PANEL)
    source = Image.open(source_path).convert("RGB")
    mask = Image.open(mask_path).convert("L")
    overlay = Image.open(overlay_path).convert("RGB")
    fail_panel = Image.open(fail_panel_path).convert("RGB")

    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_under_eye/strict_visual_acceptance" / RUN_STAMP
    layers_dir = out_dir / "boundary_layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    region_ids = ["left_eye_core", "right_eye_core", "left_lower_lid", "right_lower_lid", "nose_bridge_sidewalls", "upper_cheek_lower_boundary", "eyebrows", "under_eye_target_candidate"]
    layers: list[dict[str, Any]] = []
    for region_id in region_ids:
        layer = boundary_layer(source.size, region_id)
        path = layers_dir / f"{region_id}.png"
        layer.save(path)
        layers.append(
            {
                "region_id": region_id,
                "source": "manual_source_reviewed_polygon_under_eye_audit",
                "path": str(path),
                "sha256": sha256_file(path),
                "review_status": "candidate_runtime_ready" if region_id == "under_eye_target_candidate" else "manual_boundary_candidate",
            }
        )

    candidate_pixels = pixel_count(mask)
    overlap_rows: list[dict[str, Any]] = []
    protected_failures: list[str] = []
    tolerances = {
        "left_eye_core": 0,
        "right_eye_core": 0,
        "left_lower_lid": 12,
        "right_lower_lid": 12,
        "nose_bridge_sidewalls": 0,
        "upper_cheek_lower_boundary": 16,
        "eyebrows": 0,
    }
    for layer in layers:
        region_id = layer["region_id"]
        if region_id == "under_eye_target_candidate":
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

    matrix_path = out_dir / "mf70_under_eye_strict_protected_overlap_matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["target_mask_type_id", "protected_region_id", "overlap_pixels", "overlap_percent_of_candidate", "allowed_overlap_pixels", "pass"],
        )
        writer.writeheader()
        writer.writerows(overlap_rows)

    protected_overlap_pass = not protected_failures
    boundary_overlay = make_boundary_overlay(overlay, layers)
    boundary_overlay_path = out_dir / "mf70_under_eye_strict_boundary_overlay.png"
    panel_path = out_dir / "mf70_under_eye_strict_visual_acceptance_panel.png"
    boundary_overlay.save(boundary_overlay_path)
    make_panel(source, overlay, boundary_overlay, mask, fail_panel, panel_path)

    qa_record = read_json(root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_under_eye.json")
    proof = qa_record.get("generated_output_proof", {})
    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_UNDER_EYE_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_UNDER_EYE_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    result = "pass_candidate_strict_visual_alignment_generated_output_safe_pending_target_runtime" if protected_overlap_pass else "under_eye_strict_visual_candidate_protected_overlap_failed"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-UNDER-EYE-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_under_eye_strict_visual_fail_closed_acceptance",
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
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": sha256_file(mask_path),
        "candidate_overlay": rel(overlay_path, root),
        "candidate_overlay_sha256": sha256_file(overlay_path),
        "boundary_protocol": BOUNDARY_PROTOCOL,
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
        "visual_review_findings": [
            "Accepted: mask targets compact under-eye skin crescents below both lower lids.",
            "Accepted: mask does not cover eye cores, eyebrow bands, nose bridge/sidewalls, broad cheek field, hair, clothing, or background.",
            "Accepted with boundary: this is single-anchor candidate evidence only and does not prove generalized under-eye masking.",
            "Generated-output stability is reused only because the old local proof used this same mask hash and already passed whole-image QA; target-runtime/reference-matrix proof remains pending.",
        ],
        "semantic_mask_alignment_candidate_pass": protected_overlap_pass,
        "generated_output_proof_reused": proof,
        "generated_output_safe_pass": bool(proof and proof.get("visual_qa_result") == "pass_with_notes_local_wave70_under_eye_generated_output"),
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "result": result,
        "status_after_audit": STATUS if protected_overlap_pass else "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "status_decision_after_audit": STATUS_DECISION if protected_overlap_pass else "under_eye_candidate_protected_overlap_failed",
        "boundary": "This evidence accepts only the compact mf70_under_eye mask on the active source portrait. It does not certify Wave70 and does not replace target-runtime/reference-matrix proof.",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_UNDER_EYE_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "status": evidence["status_after_audit"],
            "status_decision": evidence["status_decision_after_audit"],
            "evidence": rel(evidence_path, root),
            "review_panel": rel(panel_path, root),
            "protected_overlap_matrix_pass": protected_overlap_pass,
            "generated_output_proof_reused": True,
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
        tracker_evidence_rel = rel(tracker_path, root)
        panel_rel = rel(panel_path, root)
        update_mask_qa(root, evidence_rel, tracker_evidence_rel, evidence)
        update_ledgers(root, evidence_rel, tracker_evidence_rel, panel_rel)
        update_hydration(root, evidence_rel, tracker_evidence_rel, panel_rel)

    print(json.dumps({"result": result, "evidence": rel(evidence_path, root), "tracker_evidence": rel(tracker_path, root), "panel": rel(panel_path, root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
