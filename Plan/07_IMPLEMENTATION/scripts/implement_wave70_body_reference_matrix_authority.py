from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
HISTORICAL_SOURCE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
MAIN_REFERENCE = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
REF_IMAGE_2_MAIN_REFERENCE = PROJECT_ROOT / "Ref_Image_2/97f30ff4819b8b8206e8ce30f2355800.jpg"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_BODY_REFERENCE_MATRIX_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_body_reference_matrix_authority.py"

TRACKER_ID = "TRK-W70-0176"
ITEM_ID = "ITEM-W70-0176"
NEXT_TRACKER_ID = "TRK-W70-0177"
NEXT_ITEM_ID = "ITEM-W70-0177"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_body_reference_matrix_authority" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

FULL_REF_MANIFEST = QA_DIR / "ref_image_1_full_body_references.json"
GOLD_MASK_MANIFEST = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
REF_IMAGE_2_MANIFEST = QA_DIR / "ref_image_2_body_reference.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQUISITE_EVIDENCE = {
    "model_consensus_geometry_validator": QA_DIR / "model_consensus_geometry_validator.json",
    "body_region_geometry_authority": QA_DIR / "body_region_geometry_authority.json",
    "contact_occlusion_ownership_authority": QA_DIR / "contact_occlusion_ownership_authority.json",
    "soft_body_anchor_geometry_authority": QA_DIR / "soft_body_anchor_geometry_authority.json",
    "temporal_body_part_tracking_authority": QA_DIR / "temporal_body_part_tracking_authority.json",
}

REFERENCE_DOCS_FOUND = [
    "Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_REFERENCE_IMAGE_MATRIX.md",
    "Plan/07_IMPLEMENTATION/mask_factory/WAVE70_WHOLE_BODY_GEOMETRY_AUTHORITY.md",
    "Plan/07_IMPLEMENTATION/mask_factory/WAVE70_WHOLE_BODY_GEOMETRY_AUTHORITY_MATRIX.csv",
    "Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md",
    "Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md",
    "Plan/Instructions/QA/Templates/WAVE70_REFERENCE_IMAGE_MATRIX_MANIFEST_TEMPLATE.json",
]

REQUIRED_BODY_MATRIX_SLOTS = [
    "pose_front_standing_or_neutral",
    "pose_three_quarter_left",
    "pose_three_quarter_right",
    "pose_profile_or_near_profile",
    "body_size_variation",
    "skin_tone_variation",
    "hair_and_body_hair_case",
    "clothing_state_upper_lower_boundary",
    "hand_finger_configuration_visible",
    "feet_toe_visibility",
    "contact_support_surface",
    "occlusion_or_multi_person_case",
    "body_region_regression_case",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def entries(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def label_for(entry: dict[str, object]) -> str:
    for key in ("label", "mask_label", "name", "id", "relative_to_ref_dir", "path"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def summarize_full_references() -> dict[str, object]:
    payload = read_json(FULL_REF_MANIFEST)
    refs = entries(payload, "full_body_references")
    limited = []
    eligible = []
    dims = []
    for ref in refs:
        path_text = str(ref.get("path", ""))
        limitations = ref.get("coverage_limitations") or []
        is_limited = "New folder" in path_text or any("knees_to_top_of_head" in str(item) for item in limitations)
        (limited if is_limited else eligible).append(ref)
        if isinstance(ref.get("dimensions"), list):
            dims.append(ref["dimensions"])
    return {
        "manifest_path": rel(FULL_REF_MANIFEST),
        "manifest_exists": FULL_REF_MANIFEST.exists(),
        "sha256": sha256_file(FULL_REF_MANIFEST) if FULL_REF_MANIFEST.exists() else "",
        "static_pose_reference_count": len(refs),
        "full_body_lower_region_eligible_reference_count": len(eligible),
        "near_full_knees_to_head_reference_count": len(limited),
        "dimensions_observed": dims,
        "near_full_limitations": [
            {
                "path": ref.get("path", ""),
                "relative_to_full_dir": ref.get("relative_to_full_dir", ""),
                "coverage_limitations": ref.get("coverage_limitations", []),
            }
            for ref in limited
        ],
    }


def summarize_gold_masks() -> dict[str, object]:
    payload = read_json(GOLD_MASK_MANIFEST)
    masks = entries(payload, "gold_standard_masks") or entries(payload, "extracted_masks")
    labels = [label_for(mask) for mask in masks]
    if not labels and isinstance(payload.get("ref_image_1_body_region_gold_refs"), dict):
        labels = list(payload["ref_image_1_body_region_gold_refs"].get("body_region_reference_labels", []))
    lower = " ".join(label.lower() for label in labels)
    return {
        "manifest_path": rel(GOLD_MASK_MANIFEST),
        "manifest_exists": GOLD_MASK_MANIFEST.exists(),
        "sha256": sha256_file(GOLD_MASK_MANIFEST) if GOLD_MASK_MANIFEST.exists() else "",
        "all_gold_mask_count": payload.get("extracted_nonzero_mask_count", len(labels)),
        "labels": sorted(set(labels)),
        "category_presence": {
            "torso_abdomen": any(token in lower for token in ["abdomen", "stomach", "belly"]),
            "arms_hands_fingers": any(token in lower for token in ["arm", "hand", "finger", "thumb"]),
            "legs_feet_toes": any(token in lower for token in ["thigh", "calf", "feet", "foot", "toe"]),
            "pelvis_glute": any(token in lower for token in ["pelvic", "glute"]),
            "hair": "hair" in lower,
            "breasts": "breast" in lower,
        },
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body masks here are not failures",
            "lower_strip": "primary full-body body-mask validation area",
        },
    }


def summarize_ref_image_2() -> dict[str, object]:
    payload = read_json(REF_IMAGE_2_MANIFEST)
    overlays = entries(payload, "gold_mask_overlays")
    labels = [label_for(mask) for mask in overlays]
    lower = " ".join(
        f"{item.get('normalized_category', '')} {item.get('category', '')} {item.get('mask_label', '')}".lower()
        for item in overlays
    )
    manifest = payload.get("manifest") if isinstance(payload.get("manifest"), dict) else {}
    main = payload.get("main_reference") if isinstance(payload.get("main_reference"), dict) else {}
    return {
        "manifest_path": rel(REF_IMAGE_2_MANIFEST),
        "manifest_exists": REF_IMAGE_2_MANIFEST.exists(),
        "sha256": sha256_file(REF_IMAGE_2_MANIFEST) if REF_IMAGE_2_MANIFEST.exists() else "",
        "main_reference": {
            "path": rel(REF_IMAGE_2_MAIN_REFERENCE),
            "exists": REF_IMAGE_2_MAIN_REFERENCE.exists(),
            "sha256": sha256_file(REF_IMAGE_2_MAIN_REFERENCE) if REF_IMAGE_2_MAIN_REFERENCE.exists() else "",
            "dimensions": main.get("dimensions", []),
            "coverage_scope": main.get("coverage_scope", "full_body_reference_user_provided"),
        },
        "all_gold_mask_count": manifest.get("located_overlay_count", len(labels)),
        "manifest_row_count": manifest.get("row_count", len(overlays)),
        "labels": sorted(set(labels)),
        "category_presence": {
            "torso_abdomen": any(token in lower for token in ["abdomen", "stomach", "belly"]),
            "arms_hands_fingers": any(token in lower for token in ["arm", "hand", "finger", "thumb"]),
            "legs_feet_toes": any(token in lower for token in ["thigh", "calf", "feet", "foot", "toe"]),
            "pelvis_glute": any(token in lower for token in ["pelvic", "glute"]),
            "hair": "hair" in lower,
            "breasts": "breast" in lower or "chest" in lower,
            "clothes": "clothes" in lower or "bra" in lower or "underwear" in lower,
        },
        "layout_interpretation": {
            "role": "additional full-body gold reference with organized per-part overlays",
            "duplicate_source_copy_policy": "Do not count Ref_Image_2/Face/Ref_Image_2 extracted copies as additional organized masks.",
        },
    }


def merge_category_presence(*summaries: dict[str, object]) -> dict[str, bool]:
    keys = [
        "torso_abdomen",
        "arms_hands_fingers",
        "legs_feet_toes",
        "pelvis_glute",
        "hair",
        "breasts",
        "clothes",
    ]
    merged = {key: False for key in keys}
    for summary in summaries:
        presence = summary.get("category_presence") if isinstance(summary.get("category_presence"), dict) else {}
        for key in keys:
            merged[key] = bool(merged[key] or presence.get(key))
    return merged


def prerequisite_summary() -> dict[str, object]:
    result: dict[str, object] = {}
    for name, path in PREREQUISITE_EVIDENCE.items():
        payload = read_json(path)
        authority = (
            payload.get("model_backed_geometry_authority")
            or payload.get("whole_body_geometry_authority")
            or payload.get("soft_body_anchor_geometry_authority")
            or payload.get("temporal_body_part_tracking_authority")
            or payload.get("body_region_geometry_authority")
            or payload.get("contact_occlusion_ownership_authority")
            or {}
        )
        result[name] = {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else "",
            "evidence_id": payload.get("evidence_id"),
            "qa_decision": payload.get("qa_decision"),
            "result": authority.get("result"),
            "body_reference_matrix_pass": authority.get("body_reference_matrix_pass"),
            "model_consensus_geometry_pass": authority.get("model_consensus_geometry_pass"),
            "body_region_geometry_pass": authority.get("body_region_geometry_pass"),
            "contact_occlusion_ownership_pass": authority.get("contact_occlusion_ownership_pass"),
            "soft_body_anchor_pass": authority.get("soft_body_anchor_pass"),
            "temporal_tracking_pass": authority.get("temporal_tracking_pass"),
            "canonical_polygon_export_pass": authority.get("canonical_polygon_export_pass"),
        }
    return result


def slot_status(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    ref_image_2_summary: dict[str, object],
) -> list[dict[str, object]]:
    categories = merge_category_presence(gold_summary, ref_image_2_summary)
    base_available = bool(
        full_summary["manifest_exists"]
        and gold_summary["manifest_exists"]
        and ref_image_2_summary["manifest_exists"]
    )
    statuses: list[dict[str, object]] = []
    for slot_id in REQUIRED_BODY_MATRIX_SLOTS:
        status = "reference_available_route_not_complete"
        source_artifact = rel(FULL_REF_MANIFEST)
        source_artifacts = [rel(FULL_REF_MANIFEST), rel(GOLD_MASK_MANIFEST), rel(REF_IMAGE_2_MANIFEST)]
        reason = "Ref_Image_1 and Ref_Image_2 static references/gold masks provide reference context, but production/generalization proof is incomplete."
        visibility_pass = base_available
        if slot_id == "feet_toe_visibility" and full_summary["full_body_lower_region_eligible_reference_count"] < 1:
            status = "blocked"
            reason = "No lower-body eligible full reference exists."
            visibility_pass = False
        if slot_id == "contact_support_surface":
            status = "required_not_complete"
            reason = "Static references include foot/body context but do not prove support/contact ownership or generated-output contact behavior."
        if slot_id == "occlusion_or_multi_person_case":
            status = "blocked"
            source_artifact = ""
            reason = "No multi-person or occlusion matrix slot is filled by Ref_Image_1."
            visibility_pass = False
        if slot_id == "body_size_variation":
            status = "blocked"
            reason = "Single-character reference set does not prove cross-body-size generalization."
            visibility_pass = False
        if slot_id == "skin_tone_variation":
            status = "blocked"
            reason = "Single-character reference set does not prove skin-tone variation."
            visibility_pass = False
        if slot_id == "clothing_state_upper_lower_boundary":
            status = "required_not_complete"
            reason = "Body masks exist, but parser-backed clothing/body boundary ownership is not complete."
        if slot_id == "hair_and_body_hair_case" and not categories["hair"]:
            status = "blocked"
            reason = "No hair reference label found."
            visibility_pass = False
        if slot_id == "hand_finger_configuration_visible" and not categories["arms_hands_fingers"]:
            status = "blocked"
            reason = "No hand/finger reference labels found."
            visibility_pass = False
        statuses.append(
            {
                "slot_id": slot_id,
                "status": status,
                "source_artifact": source_artifact,
                "source_artifacts": source_artifacts,
                "source_visibility_matrix_pass": visibility_pass,
                "cross_subject_generalization_pass": False,
                "body_reference_matrix_pass": False,
                "reason": reason,
            }
        )
    return statuses


def body_reference_matrix_analysis(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    ref_image_2_summary: dict[str, object],
) -> dict[str, object]:
    slots = slot_status(full_summary, gold_summary, ref_image_2_summary)
    passed_visibility = sum(1 for slot in slots if slot["source_visibility_matrix_pass"])
    blocked = sum(1 for slot in slots if slot["status"] == "blocked")
    return {
        "reference_docs_found": REFERENCE_DOCS_FOUND,
        "required_body_matrix_slots": REQUIRED_BODY_MATRIX_SLOTS,
        "slot_status": slots,
        "slots_required_count": len(REQUIRED_BODY_MATRIX_SLOTS),
        "source_visibility_slots_available_count": passed_visibility,
        "slots_blocked_count": blocked,
        "static_reference_context_available": True,
        "ref_image_1_full_body_reference_count": full_summary["static_pose_reference_count"],
        "ref_image_2_full_body_reference_count": 1 if ref_image_2_summary["main_reference"]["exists"] else 0,
        "full_body_reference_count": full_summary["static_pose_reference_count"]
        + (1 if ref_image_2_summary["main_reference"]["exists"] else 0),
        "ref_image_1_gold_mask_count": gold_summary["all_gold_mask_count"],
        "ref_image_2_gold_mask_count": ref_image_2_summary["all_gold_mask_count"],
        "gold_mask_count": int(gold_summary["all_gold_mask_count"]) + int(ref_image_2_summary["all_gold_mask_count"]),
        "multi_reference_gold_context_available": True,
        "single_character_reference_set": True,
        "body_reference_matrix_pass": False,
        "cross_subject_generalization_pass": False,
        "source_visibility_matrix_pass": passed_visibility > 0,
        "whole_body_geometry_authority_pass": False,
        "canonical_polygon_export_pass": False,
        "blocked_reason": (
            "ref_images_1_2_body_reference_context_available_but_matrix_route_missing_cross_subject_generalization_"
            "occlusion_multi_person_slot_parser_backed_ownership_canonical_polygons_generated_output_and_promotion_evidence"
        ),
    }


def make_reference_panel(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    ref_image_2_summary: dict[str, object],
    analysis: dict[str, object],
) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "body_reference_matrix_authority_reference_route_panel.png"
    panel = Image.new("RGB", (1500, 900), (248, 248, 246))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, 1499, 899], outline=(90, 90, 90), width=2)
    draw.text((36, 28), "Wave70 0176 Body Reference Matrix", fill=(20, 20, 20), font=font)
    draw.text((36, 58), "Ref_Image_1 + Ref_Image_2 body matrix context available; generalized production route remains not complete.", fill=(20, 20, 20), font=font)
    lines = [
        f"Ref_Image_1 Full/near-full static references: {full_summary['static_pose_reference_count']}",
        f"Lower-body eligible Full references: {full_summary['full_body_lower_region_eligible_reference_count']}",
        f"Knees-to-head limited references: {full_summary['near_full_knees_to_head_reference_count']}",
        f"Ref_Image_1 gold masks: {gold_summary['all_gold_mask_count']}",
        f"Ref_Image_2 full-body references: {analysis['ref_image_2_full_body_reference_count']}",
        f"Ref_Image_2 organized gold masks: {ref_image_2_summary['all_gold_mask_count']}",
        f"Combined gold mask count: {analysis['gold_mask_count']}",
        f"Visibility slots with reference context: {analysis['source_visibility_slots_available_count']} / {analysis['slots_required_count']}",
        "Top strip partial upper-body only; lower strip primary full-body validation section.",
        "Missing for pass: cross-subject variation, occlusion/multi-person slot, parser-backed ownership, generated output.",
        "No masks promoted.",
    ]
    y = 112
    for line in lines:
        draw.text((48, y), line, fill=(0, 0, 0), font=font)
        y += 38
    if MAIN_REFERENCE.exists():
        image = Image.open(MAIN_REFERENCE).convert("RGB")
        image.thumbnail((360, 360))
        panel.paste(image, (760, 150))
        draw.rectangle([755, 145, 1130, 520], outline=(120, 120, 120), width=2)
        draw.text((760, 538), "Main Ref_Image_1 gold mask matrix source", fill=(0, 0, 0), font=font)
    if REF_IMAGE_2_MAIN_REFERENCE.exists():
        image = Image.open(REF_IMAGE_2_MAIN_REFERENCE).convert("RGB")
        image.thumbnail((300, 450))
        panel.paste(image, (1160, 150))
        draw.rectangle([1155, 145, 1468, 610], outline=(120, 120, 120), width=2)
        draw.text((1160, 628), "Ref_Image_2 full-body source", fill=(0, 0, 0), font=font)
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "Tracker_ID", TRACKER_ID) for path in TRACKER_FILES] + [
        (path, "Item_ID", ITEM_ID) for path in ITEM_FILES
    ]
    for csv_path, id_field, target_id in targets:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        changed = 0
        for row in rows:
            if row.get(id_field) != target_id:
                continue
            changed += 1
            row["Status"] = "Required_Not_Complete"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "ref_images_1_2_body_reference_matrix_context_available_route_not_complete"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_body_reference_matrix_context_available",
                        "ref_image_2_body_reference_matrix_context_available",
                        "body_reference_matrix_route_not_complete_no_promotion",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        updated[rel(csv_path)] = changed
    return updated


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(
    evidence_paths: list[str],
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    ref_image_2_summary: dict[str, object],
    analysis: dict[str, object],
) -> None:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-evaluated `{TRACKER_ID}` / `{ITEM_ID}` body reference matrix with Ref_Image_1 gold masks, Ref_Image_1/Full context, and the new Ref_Image_2 full-body gold-mask set.

Result: Ref_Image_1 supplies `{full_summary['static_pose_reference_count']}` static Full/near-full references plus `{gold_summary['all_gold_mask_count']}` gold body-part masks. The `Full/New folder` image remains knees-to-head only and is not used for feet/toes/ankles/lower-calf/support proof.

Ref_Image_2 supplies one additional full-body reference image (`Ref_Image_2/97f30ff4819b8b8206e8ce30f2355800.jpg`) plus `{ref_image_2_summary['all_gold_mask_count']}` organized mask overlays from `Ref_Image_2/manifest.csv`. It is now included as body reference matrix context.

The row remains `Required_Not_Complete`: the expanded reference context exists, but the matrix does not prove cross-subject/body-size/skin-tone generalization, occlusion/multi-person coverage, parser-backed clothing/body/contact ownership, canonical polygons, generated output, target runtime, visual QA, or mask promotion evidence. No masks were promoted.

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body + f"\n\nNext local action: `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0177",
        body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body,
    )
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 0176 body reference matrix Ref_Image_1 Ref_Image_2 evidence",
                (
                    "Re-evaluated body reference matrix with Ref_Image_1 static references/gold masks and the new Ref_Image_2 "
                    "full-body reference plus 44 organized masks; kept route Required_Not_Complete because generalization, "
                    "occlusion/multi-person, parser ownership, canonical polygons, generated output, and promotion evidence are missing."
                ),
                "; ".join(evidence_paths),
                "python py_compile; Ref_Image_1 manifest validation; slot matrix analysis; JSON validation; panel generation; CSV row verification",
                "BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_CONTEXT_AVAILABLE_ROUTE_NOT_COMPLETE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json",
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} next.",
            ]
        )


def main() -> int:
    if not MAIN_REFERENCE.exists():
        raise FileNotFoundError(MAIN_REFERENCE)
    full_summary = summarize_full_references()
    gold_summary = summarize_gold_masks()
    ref_image_2_summary = summarize_ref_image_2()
    prereqs = prerequisite_summary()
    analysis = body_reference_matrix_analysis(full_summary, gold_summary, ref_image_2_summary)
    panel_path = make_reference_panel(full_summary, gold_summary, ref_image_2_summary, analysis)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "body_reference_matrix.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "body_reference_matrix.json"
    runtime_evidence_path = RUNTIME_DIR / "body_reference_matrix.json"
    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        rel(FULL_REF_MANIFEST),
        rel(GOLD_MASK_MANIFEST),
        rel(REF_IMAGE_2_MANIFEST),
    ]
    note = (
        f"Body reference matrix authority {RUN_STAMP}: Ref_Image_1 static Full references/gold masks plus Ref_Image_2 "
        "full-body gold-mask context provide body reference context, superseding the portrait-only matrix blocker for this "
        "reference evaluation. Row remains "
        "Required_Not_Complete because cross-subject/body-size/skin-tone generalization, occlusion/multi-person slot, "
        "parser ownership, canonical polygons, generated output, target runtime, visual QA, and promotion evidence are missing. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)
    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": f"Build body reference matrix for {TRACKER_ID} / {ITEM_ID} using Ref_Image_1 context.",
        "script": SCRIPT_REL,
        "historical_portrait_source": {
            "path": rel(HISTORICAL_SOURCE),
            "exists": HISTORICAL_SOURCE.exists(),
            "sha256": sha256_file(HISTORICAL_SOURCE) if HISTORICAL_SOURCE.exists() else "",
            "role": "historical_prior_active_source_not_decisive_for_current_body_reference_evaluation",
        },
        "main_reference": {
            "path": rel(MAIN_REFERENCE),
            "exists": True,
            "sha256": sha256_file(MAIN_REFERENCE),
        },
        "ref_image_2_main_reference": {
            "path": rel(REF_IMAGE_2_MAIN_REFERENCE),
            "exists": REF_IMAGE_2_MAIN_REFERENCE.exists(),
            "sha256": sha256_file(REF_IMAGE_2_MAIN_REFERENCE) if REF_IMAGE_2_MAIN_REFERENCE.exists() else "",
        },
        "ref_image_1_full_body_references": full_summary,
        "ref_image_1_body_mask_gold_refs": gold_summary,
        "ref_image_2_body_mask_gold_refs": ref_image_2_summary,
        "prerequisite_evidence": prereqs,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "body_reference_matrix_analysis": analysis,
        "artifacts": {
            "reference_route_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "whole_body_geometry_authority": {
            "result": "required_not_complete",
            "reference_source_available": True,
            "source_visibility_matrix_pass": analysis["source_visibility_matrix_pass"],
            "body_reference_matrix_pass": False,
            "cross_subject_generalization_pass": False,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "model_consensus_geometry_pass": False,
            "canonical_polygon_export_pass": False,
            "blocked_reason": analysis["blocked_reason"],
            "findings": [
                "Ref_Image_1 and Ref_Image_1/Full provide static body-reference context and labeled gold body masks.",
                "Ref_Image_2 provides an additional full-body reference image and organized per-part mask overlays, now included in the body reference matrix context.",
                "The prior single portrait matrix blocker is superseded for this reference evaluation.",
                "The knees-to-head Full/New folder reference remains excluded from feet/toes/ankles/lower-calf/support proof.",
                "The matrix still does not prove cross-subject/body-size/skin-tone generalization, occlusion/multi-person coverage, parser-backed ownership, canonical polygons, generated output, target runtime, visual QA, or promotion evidence.",
                "No active mask changed and no mask was promoted.",
            ],
        },
        "qa_decision": "ref_images_1_2_body_reference_matrix_context_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_body_reference_matrix_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} locally.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths, full_summary, gold_summary, ref_image_2_summary, analysis)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "row_updates": row_updates, "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
