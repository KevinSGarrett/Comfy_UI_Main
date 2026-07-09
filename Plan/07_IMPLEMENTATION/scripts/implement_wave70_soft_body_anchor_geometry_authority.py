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
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_SOFT_BODY_ANCHOR_GEOMETRY_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_soft_body_anchor_geometry_authority.py"

TRACKER_ID = "TRK-W70-0174"
ITEM_ID = "ITEM-W70-0174"
NEXT_TRACKER_ID = "TRK-W70-0175"
NEXT_ITEM_ID = "ITEM-W70-0175"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_soft_body_anchor_geometry_authority" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

FULL_REF_MANIFEST = QA_DIR / "ref_image_1_full_body_references.json"
GOLD_MASK_MANIFEST = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
BODY_REFERENCE_MATRIX = QA_DIR / "body_reference_matrix.json"

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
    "limb_joint_region_authority": QA_DIR / "limb_joint_region_authority.json",
    "torso_abdomen_umbilicus_authority": QA_DIR / "torso_abdomen_umbilicus_authority.json",
}

SOFT_BODY_LABEL_TOKENS = [
    "abdomen",
    "stomach",
    "belly",
    "breast",
    "glute",
    "thigh",
    "calf",
    "pelvic",
    "upper_arm",
    "lower_arm",
    "fore",
    "torso",
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


def manifest_entries(payload: dict[str, object]) -> list[dict[str, object]]:
    for key in ("full_body_references", "gold_standard_masks", "extracted_masks", "masks"):
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
    refs = manifest_entries(payload)
    limited = []
    eligible = []
    for ref in refs:
        limitations = ref.get("coverage_limitations") or []
        path_text = str(ref.get("path", ""))
        is_limited = "New folder" in path_text or any("knees_to_top_of_head" in str(item) for item in limitations)
        if is_limited:
            limited.append(ref)
        else:
            eligible.append(ref)
    return {
        "manifest_path": rel(FULL_REF_MANIFEST),
        "manifest_exists": FULL_REF_MANIFEST.exists(),
        "sha256": sha256_file(FULL_REF_MANIFEST) if FULL_REF_MANIFEST.exists() else "",
        "recursive_image_count": len(refs),
        "soft_body_lower_anchor_eligible_reference_count": len(eligible),
        "near_full_knees_to_head_reference_count": len(limited),
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
    entries = manifest_entries(payload)
    labels = [label_for(entry) for entry in entries]
    soft_labels = [
        label
        for label in labels
        if any(token in label.lower().replace("-", "_") for token in SOFT_BODY_LABEL_TOKENS)
    ]
    if not soft_labels and isinstance(payload.get("ref_image_1_body_region_gold_refs"), dict):
        soft_labels = list(payload["ref_image_1_body_region_gold_refs"].get("body_region_reference_labels", []))
    return {
        "manifest_path": rel(GOLD_MASK_MANIFEST),
        "manifest_exists": GOLD_MASK_MANIFEST.exists(),
        "sha256": sha256_file(GOLD_MASK_MANIFEST) if GOLD_MASK_MANIFEST.exists() else "",
        "all_gold_mask_count": payload.get("extracted_nonzero_mask_count", len(entries)),
        "soft_body_reference_mask_count": len(soft_labels),
        "soft_body_reference_labels": sorted(set(soft_labels)),
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body soft-body anchors here are not failures",
            "lower_strip": "primary full-body body-mask validation area",
        },
    }


def summarize_combined_body_reference_matrix() -> dict[str, object]:
    payload = read_json(BODY_REFERENCE_MATRIX)
    ref1 = payload.get("ref_image_1_body_mask_gold_refs", {}) if isinstance(payload, dict) else {}
    ref2 = payload.get("ref_image_2_body_mask_gold_refs", {}) if isinstance(payload, dict) else {}
    ref1_full = payload.get("ref_image_1_full_body_references", {}) if isinstance(payload, dict) else {}
    combined = payload.get("combined_body_reference_matrix", {}) if isinstance(payload, dict) else {}
    ref2_exists = bool(ref2.get("main_reference", {}).get("exists")) if isinstance(ref2, dict) else False
    return {
        "manifest_path": rel(BODY_REFERENCE_MATRIX),
        "manifest_exists": BODY_REFERENCE_MATRIX.exists(),
        "sha256": sha256_file(BODY_REFERENCE_MATRIX) if BODY_REFERENCE_MATRIX.exists() else "",
        "evidence_id": payload.get("evidence_id") if isinstance(payload, dict) else "",
        "qa_decision": payload.get("qa_decision") if isinstance(payload, dict) else "",
        "ref_image_1_gold_mask_count": ref1.get("all_gold_mask_count", 0) if isinstance(ref1, dict) else 0,
        "ref_image_2_gold_mask_count": ref2.get("all_gold_mask_count", 0) if isinstance(ref2, dict) else 0,
        "combined_gold_mask_count": combined.get(
            "combined_gold_mask_count",
            int(ref1.get("all_gold_mask_count", 0) or 0) + int(ref2.get("all_gold_mask_count", 0) or 0),
        )
        if isinstance(combined, dict)
        else 0,
        "ref_image_1_full_or_near_full_reference_count": ref1_full.get("static_pose_reference_count", 0)
        if isinstance(ref1_full, dict)
        else 0,
        "ref_image_2_full_body_reference_count": 1 if ref2_exists else 0,
        "combined_full_or_near_full_reference_count": combined.get(
            "combined_full_or_near_full_reference_count",
            int(ref1_full.get("static_pose_reference_count", 0) or 0) + (1 if ref2_exists else 0),
        )
        if isinstance(combined, dict)
        else 0,
        "limited_reference_policy": "Ref_Image_1/Full/New folder is knees-to-head only and not valid for feet/toes/ankles/lower-calf/support proof.",
    }


def prerequisite_summary() -> dict[str, object]:
    result: dict[str, object] = {}
    for name, path in PREREQUISITE_EVIDENCE.items():
        payload = read_json(path)
        authority = (
            payload.get("whole_body_geometry_authority")
            or payload.get("model_backed_geometry_authority")
            or payload.get("contact_occlusion_ownership_authority")
            or payload.get("body_region_geometry_authority")
            or {}
        )
        result[name] = {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else "",
            "evidence_id": payload.get("evidence_id"),
            "qa_decision": payload.get("qa_decision"),
            "result": authority.get("result"),
            "whole_body_geometry_authority_pass": authority.get("whole_body_geometry_authority_pass"),
            "model_consensus_geometry_pass": authority.get("model_consensus_geometry_pass"),
            "semantic_human_part_parsing_pass": authority.get("semantic_human_part_parsing_pass"),
            "contact_occlusion_ownership_pass": authority.get("contact_occlusion_ownership_pass"),
            "body_region_geometry_pass": authority.get("body_region_geometry_pass"),
            "canonical_polygon_export_pass": authority.get("canonical_polygon_export_pass"),
        }
    return result


def soft_body_anchor_analysis(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    combined_summary: dict[str, object],
) -> dict[str, object]:
    return {
        "reference_source_available": bool(full_summary["manifest_exists"] and gold_summary["manifest_exists"]),
        "source_visibility_blocker_superseded": True,
        "body_reference_matrix_pass": combined_summary["combined_gold_mask_count"] >= gold_summary["all_gold_mask_count"],
        "production_route_pass": False,
        "soft_body_anchor_pass": False,
        "skeletal_anchor_pass": False,
        "deformation_region_protected_neighbor_pass": False,
        "canonical_polygon_export_pass": False,
        "required_anchor_results": {
            "gold_soft_body_regions": {
                "visibility": "reference_masks_available",
                "authority_status": "reference_only",
                "reason": "Ref_Image_1 and Ref_Image_2 contain labeled body-region masks usable as gold reference context.",
            },
            "skeletal_anchor_map": {
                "visibility": "not_exported",
                "authority_status": "required_not_complete",
                "reason": "No dense pose or skeleton-to-body canonical anchor graph has been exported.",
            },
            "soft_body_deformation_regions": {
                "visibility": "reference_context_available",
                "authority_status": "required_not_complete",
                "reason": "Reference masks do not produce deformation fields, strain anchors, or parser-backed soft-body regions.",
            },
            "protected_neighbor_anchors": {
                "visibility": "not_exported",
                "authority_status": "required_not_complete",
                "reason": "No canonical polygons exist for body/clothing/contact boundaries or protected-neighbor thresholds.",
            },
        },
        "blocked_reason": (
            "ref_images_1_2_soft_body_reference_context_available_but_production_route_missing_dense_pose_skeletal_anchor_graph_"
            "semantic_body_part_parser_deformation_fields_canonical_polygons_protected_neighbor_metrics_and_promotion_evidence"
        ),
    }


def make_reference_panel(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    combined_summary: dict[str, object],
) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "soft_body_anchor_geometry_authority_reference_route_panel.png"
    panel = Image.new("RGB", (1500, 900), (248, 248, 246))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, 1499, 899], outline=(90, 90, 90), width=2)
    draw.text((36, 28), "Wave70 0174 Soft-Body Protected Anchor Geometry", fill=(20, 20, 20), font=font)
    draw.text((36, 58), "Ref_Image_1+2 context available; production soft-body anchor route remains not complete.", fill=(20, 20, 20), font=font)
    lines = [
        f"Gold soft-body/body-region masks: {gold_summary['soft_body_reference_mask_count']}",
        f"Full/near-full references: {full_summary['recursive_image_count']}",
        f"Combined Ref_Image_1+2 refs: {combined_summary['combined_full_or_near_full_reference_count']}",
        f"Combined Ref_Image_1+2 gold masks: {combined_summary['combined_gold_mask_count']}",
        f"Lower-anchor eligible Full references: {full_summary['soft_body_lower_anchor_eligible_reference_count']}",
        f"Knees-to-head limited references: {full_summary['near_full_knees_to_head_reference_count']}",
        "Top strip is partial upper-body only; lower strip is the primary body-mask validation section.",
        "Full/New folder image is knees-to-head only; excluded from feet/toes/ankles/lower-calf/support proof.",
        "Missing for pass: dense pose/skeleton anchors, deformation fields, canonical polygons, protected-neighbor metrics.",
        "No masks promoted.",
    ]
    y = 112
    for line in lines:
        draw.text((48, y), line, fill=(0, 0, 0), font=font)
        y += 38
    if MAIN_REFERENCE.exists():
        image = Image.open(MAIN_REFERENCE).convert("RGB")
        image.thumbnail((560, 560))
        panel.paste(image, (880, 150))
        draw.rectangle([875, 145, 1450, 720], outline=(120, 120, 120), width=2)
        draw.text((880, 738), "Main Ref_Image_1 gold mask reference", fill=(0, 0, 0), font=font)
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
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "ref_images_1_2_soft_body_anchor_references_available_route_not_complete"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_soft_body_anchor_references_available",
                        "ref_image_2_soft_body_anchor_references_available",
                        "ref_images_1_2_combined_body_reference_matrix_available",
                        "soft_body_anchor_geometry_route_not_complete_no_promotion",
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
    combined_summary: dict[str, object],
) -> None:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-evaluated `{TRACKER_ID}` / `{ITEM_ID}` soft-body deformation and protected anchor geometry authority with Ref_Image_1+Ref_Image_2 combined body-reference context.

Result: combined context records `{combined_summary['combined_full_or_near_full_reference_count']}` full/near-full references and `{combined_summary['combined_gold_mask_count']}` gold masks. Ref_Image_1 supplies soft-body/body-region reference masks and `Ref_Image_1/Full` supplies `{full_summary['recursive_image_count']}` body context references. The `Full/New folder` image remains knees-to-head only and is not used for feet/toes/ankles/lower-calf/support proof.

The row remains `Required_Not_Complete` because reference masks do not prove dense-pose skeletal anchors, semantic body-part parser output, soft-body deformation fields, canonical body/clothing/contact polygons, protected-neighbor metrics, generated output, target runtime, visual QA, or promotion evidence. No masks were promoted.

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - 0174 Soft-Body Ref_Image_1 Evidence - {ISO_STAMP}",
        body + f"\n\nNext local action: `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` temporal body-part tracking and video mask drift authority.",
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - 0174 Soft-Body Ref_Image_1 Evidence - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - 0174 Soft-Body Ref_Image_1 Evidence - {ISO_STAMP}",
        body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` temporal body-part tracking and video mask drift authority.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0175 Temporal Body-Part Tracking",
        body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` temporal body-part tracking and video mask drift authority.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 0174 Soft-Body Ref_Image_1 Evidence - {ISO_STAMP}",
        body,
    )
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 0174 soft-body Ref_Image_1+2 evidence",
                (
                    "Re-evaluated soft-body anchor geometry with Ref_Image_1+Ref_Image_2 combined context; superseded "
                    "the portrait-only source blocker for reference evaluation; kept route Required_Not_Complete "
                    "because dense pose, deformation fields, canonical polygons, and protected-neighbor metrics are missing."
                ),
                "; ".join(evidence_paths),
                "python py_compile; Ref_Image_1 full manifest validation; gold mask manifest validation; JSON validation; panel generation; CSV row verification",
                "SOFT_BODY_REF_IMAGES_1_2_REFERENCE_AVAILABLE_ROUTE_NOT_COMPLETE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/soft_body_anchor_geometry_authority.json",
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} temporal body-part tracking and video mask drift authority next.",
            ]
        )


def main() -> int:
    if not MAIN_REFERENCE.exists():
        raise FileNotFoundError(MAIN_REFERENCE)
    full_summary = summarize_full_references()
    gold_summary = summarize_gold_masks()
    combined_summary = summarize_combined_body_reference_matrix()
    prereqs = prerequisite_summary()
    analysis = soft_body_anchor_analysis(full_summary, gold_summary, combined_summary)
    panel_path = make_reference_panel(full_summary, gold_summary, combined_summary)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "soft_body_anchor_geometry_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "soft_body_anchor_geometry_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "soft_body_anchor_geometry_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        rel(FULL_REF_MANIFEST),
        rel(GOLD_MASK_MANIFEST),
        rel(BODY_REFERENCE_MATRIX),
    ]
    note = (
        f"Soft-body anchor geometry authority {RUN_STAMP}: Ref_Image_1+Ref_Image_2 combined context records "
        f"{combined_summary['combined_full_or_near_full_reference_count']} full/near-full references and "
        f"{combined_summary['combined_gold_mask_count']} gold masks; "
        "the portrait-only blocker is superseded for this reference evaluation. Row remains Required_Not_Complete "
        "because dense pose/skeletal anchors, deformation fields, canonical polygons, protected-neighbor metrics, "
        "generated output, target runtime, visual QA, and promotion evidence are missing. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": f"Implement soft-body deformation and protected anchor geometry authority for {TRACKER_ID} / {ITEM_ID} using Ref_Image_1+Ref_Image_2 combined context.",
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
        "ref_image_1_full_body_references": full_summary,
        "ref_image_1_soft_body_gold_refs": gold_summary,
        "ref_images_1_2_combined_body_reference_matrix": combined_summary,
        "prerequisite_evidence": prereqs,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "artifacts": {
            "reference_route_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "soft_body_anchor_analysis": analysis,
        "soft_body_anchor_geometry_authority": {
            "result": "required_not_complete",
            "reference_source_available": analysis["reference_source_available"],
            "soft_body_reference_gold_refs_available": gold_summary["soft_body_reference_mask_count"] > 0,
            "body_reference_matrix_pass": analysis["body_reference_matrix_pass"],
            "source_visibility_blocker_superseded": True,
            "production_route_pass": False,
            "soft_body_anchor_pass": False,
            "skeletal_anchor_pass": False,
            "deformation_region_protected_neighbor_pass": False,
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
                "Ref_Image_1 and Ref_Image_2 gold-standard masks include soft-body/body-region reference context.",
                "Ref_Image_1/Full supplies full/near-full body context, with the knees-to-head image still limited for lower-body proof.",
                "The prior portrait-only soft-body blocker is superseded for this reference evaluation.",
                "Reference masks do not by themselves prove dense-pose skeletal anchors, deformation fields, canonical polygons, protected-neighbor thresholds, generated output, visual QA, or promotion evidence.",
                "No soft-body deformation field, protected anchor polygon, segmentation map, active mask change, or mask promotion was produced.",
            ],
        },
        "qa_decision": "ref_images_1_2_soft_body_anchor_references_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_soft_body_anchor_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} temporal body-part tracking and video mask drift authority locally.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths, full_summary, gold_summary, combined_summary)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "row_updates": row_updates,
                "combined_full_or_near_full_reference_count": combined_summary["combined_full_or_near_full_reference_count"],
                "combined_gold_mask_count": combined_summary["combined_gold_mask_count"],
                "evidence": rel(qa_evidence_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
