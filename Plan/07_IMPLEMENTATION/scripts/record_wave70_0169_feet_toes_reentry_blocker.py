from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_0169_feet_toes_reentry_blocker" / STAMP

SUPERVISOR_CORRECTION = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Milestone_Progress_Audit/TWO_HOUR_SUPERVISOR_ROUTE_LOOP_CORRECTION_20260708T185529-0500.json"
FEET_TOES_AUTHORITY = QA_DIR / "feet_toes_authority.json"
BODY_REFERENCE_MATRIX = QA_DIR / "body_reference_matrix.json"
REF1_FULL = QA_DIR / "ref_image_1_full_body_references.json"
REF1_GOLD = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
REF2_BODY = QA_DIR / "ref_image_2_body_reference.json"
AVAILABLE_ROUTE_ALIGNMENT = QA_DIR / "available_route_runtime_validation_alignment.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

EVIDENCE = QA_DIR / f"W70_0169_FEET_TOES_REENTRY_BLOCKER_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "feet_toes_reentry_blocker.json"
PANEL = RUNTIME_DIR / "feet_toes_reentry_blocker_panel.png"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def ref1_full_summary() -> dict[str, object]:
    payload = read_json(REF1_FULL)
    refs = payload.get("full_body_references") or []
    eligible = []
    excluded = []
    for ref in refs:
        limitations = ref.get("coverage_limitations") or []
        if "user_corrected_not_full_body" in limitations:
            excluded.append(ref)
        else:
            eligible.append(ref)
    return {
        "path": rel(REF1_FULL),
        "evidence_id": payload.get("evidence_id"),
        "all_ref_image_1_full_folder_count": len(refs),
        "feet_toes_eligible_count": len(eligible),
        "feet_toes_excluded_count": len(excluded),
        "excluded_references": [
            {
                "path": item.get("path", ""),
                "coverage_scope": item.get("coverage_scope", ""),
                "coverage_limitations": item.get("coverage_limitations", []),
            }
            for item in excluded
        ],
    }


def ref1_foot_gold_summary() -> dict[str, object]:
    payload = read_json(REF1_GOLD)
    masks = []
    for item in payload.get("extracted_masks") or []:
        label = str(item.get("label", "")).lower()
        if any(token in label for token in ("feet", "foot", "toe")):
            masks.append(
                {
                    "label": item.get("label", ""),
                    "binary_mask_path": item.get("binary_mask_path", ""),
                    "red_overlay_pixel_count": item.get("red_overlay_pixel_count", 0),
                }
            )
    return {
        "path": rel(REF1_GOLD),
        "evidence_id": payload.get("evidence_id"),
        "foot_toe_gold_mask_count": len(masks),
        "foot_toe_gold_masks": masks,
    }


def ref2_foot_gold_summary() -> dict[str, object]:
    payload = read_json(REF2_BODY)
    overlays = []
    for item in payload.get("gold_mask_overlays") or []:
        path_text = str(item.get("path", "")).lower()
        if any(token in path_text for token in ("feet", "foot", "toe")):
            overlays.append({"path": item.get("path", ""), "overlay_exists": item.get("overlay_exists")})
    return {
        "path": rel(REF2_BODY),
        "evidence_id": payload.get("evidence_id"),
        "manifest_row_count": (payload.get("manifest") or {}).get("row_count"),
        "foot_toe_overlay_count": len(overlays),
        "foot_toe_overlays": overlays,
    }


def body_matrix_summary() -> dict[str, object]:
    payload = read_json(BODY_REFERENCE_MATRIX)
    analysis = payload.get("body_reference_matrix_analysis") or {}
    return {
        "path": rel(BODY_REFERENCE_MATRIX),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "source_visibility_matrix_pass": analysis.get("source_visibility_matrix_pass"),
        "body_reference_matrix_pass": analysis.get("body_reference_matrix_pass"),
        "whole_body_geometry_authority_pass": analysis.get("whole_body_geometry_authority_pass"),
        "canonical_polygon_export_pass": analysis.get("canonical_polygon_export_pass"),
        "combined_full_or_near_full_reference_count": analysis.get("full_body_reference_count"),
        "combined_gold_mask_count": analysis.get("gold_mask_count"),
        "blocked_reason": analysis.get("blocked_reason"),
    }


def update_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updates: dict[str, int] = {}
    targets = [(path, "TRK-W70-0169") for path in TRACKER_FILES] + [(path, "ITEM-W70-0169") for path in ITEM_FILES]
    for csv_path, target_id in targets:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        key = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        changed = 0
        for row in rows:
            if row.get(key) != target_id:
                continue
            changed += 1
            row["Status"] = "Required_Not_Complete"
            if "Status_Decision" in row and target_id.startswith("TRK-"):
                row["Status_Decision"] = "ref_images_1_2_feet_toes_reentry_exact_blocker_no_promotion"
            for field in ("Evidence_Path", "Acceptance_Evidence", "Evidence_Required", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_images_1_2_feet_toes_reentry_exact_blocker",
                        "ref_image_1_full_new_folder_excluded_from_feet_toes_proof",
                        "body_reference_matrix_not_passed_no_canonical_polygon",
                        "no_mask_promoted",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(csv_path)] = changed
    return updates


def draw_panel(summary: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1500, 820), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0169 / ITEM-W70-0169 feet-toes authority re-entry blocker",
        f"Created: {ISO_TS}",
        "Supervisor correction: stop route loop; return to foot/toe authority.",
        f"Ref_Image_1 eligible feet/toes refs: {summary['ref_image_1_full']['feet_toes_eligible_count']}",
        f"Ref_Image_1 excluded knees-to-head refs: {summary['ref_image_1_full']['feet_toes_excluded_count']}",
        f"Ref_Image_1 foot/toe gold masks: {summary['ref_image_1_gold']['foot_toe_gold_mask_count']}",
        f"Ref_Image_2 foot/toe overlays: {summary['ref_image_2']['foot_toe_overlay_count']}",
        f"Combined full/near-full refs: {summary['body_matrix']['combined_full_or_near_full_reference_count']}",
        f"Combined gold masks: {summary['body_matrix']['combined_gold_mask_count']}",
        f"Body reference matrix pass: {summary['body_matrix']['body_reference_matrix_pass']}",
        f"Whole-body authority pass: {summary['body_matrix']['whole_body_geometry_authority_pass']}",
        f"Canonical polygon export pass: {summary['body_matrix']['canonical_polygon_export_pass']}",
        "",
        "Decision: Required_Not_Complete, no mask promoted.",
        "Still missing: source-derived foot/toe parser or landmarks, support/floor contact ownership, canonical foot/toe polygons.",
    ]
    y = 30
    for idx, line in enumerate(lines):
        color = (130, 0, 0) if "missing" in line.lower() or "no mask" in line.lower() or "false" in line.lower() else (0, 0, 0)
        draw.text((30, y), line, fill=color, font=font)
        y += 34 if idx else 48
    image.save(PANEL)


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def main() -> None:
    supervisor = read_json(SUPERVISOR_CORRECTION)
    prior_feet = read_json(FEET_TOES_AUTHORITY)
    route_alignment = read_json(AVAILABLE_ROUTE_ALIGNMENT)
    summary = {
        "ref_image_1_full": ref1_full_summary(),
        "ref_image_1_gold": ref1_foot_gold_summary(),
        "ref_image_2": ref2_foot_gold_summary(),
        "body_matrix": body_matrix_summary(),
    }

    require(supervisor.get("classification") == "ADVANCING_WITH_LOOP_RISK_SEQUENCE_DRIFT_CORRECTED", "Supervisor correction not active")
    require(prior_feet.get("qa_decision") == "ref_images_1_2_full_body_feet_toes_references_available_route_not_complete", "Prior feet/toes authority is not the expected route-not-complete record")
    require(summary["ref_image_1_full"]["feet_toes_excluded_count"] >= 1, "No excluded knees-to-head reference recorded")
    require(summary["ref_image_1_gold"]["foot_toe_gold_mask_count"] >= 4, "Ref_Image_1 foot/toe gold masks are missing")
    require(summary["ref_image_2"]["foot_toe_overlay_count"] >= 4, "Ref_Image_2 foot/toe overlays are missing")
    require(summary["body_matrix"]["body_reference_matrix_pass"] is False, "Body reference matrix unexpectedly passed")

    draw_panel(summary)
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(FEET_TOES_AUTHORITY),
        rel(BODY_REFERENCE_MATRIX),
        rel(REF1_FULL),
        rel(REF1_GOLD),
        rel(REF2_BODY),
        rel(SUPERVISOR_CORRECTION),
        rel(AVAILABLE_ROUTE_ALIGNMENT),
        rel(PANEL),
    ]
    note = (
        "TRK-W70-0169 re-entry blocker after supervisor correction: Ref_Image_1+2 feet/toe references and gold masks are available; "
        "Ref_Image_1/Full/New folder remains excluded from feet/toes/ankles/lower-calf proof; body reference matrix and canonical polygon authority remain not passed; no mask promoted."
    )
    row_updates = update_rows(evidence_paths, note)
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_0169_FEET_TOES_REENTRY_BLOCKER_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Re-enter TRK-W70-0169 / ITEM-W70-0169 after supervisor correction and record exact foot/toe authority blocker.",
        "supervisor_correction": {
            "path": rel(SUPERVISOR_CORRECTION),
            "classification": supervisor.get("classification"),
            "corrected_next_action": supervisor.get("corrected_next_action"),
        },
        "source_evidence": {
            "prior_feet_toes_authority": {
                "path": rel(FEET_TOES_AUTHORITY),
                "evidence_id": prior_feet.get("evidence_id"),
                "qa_decision": prior_feet.get("qa_decision"),
            },
            "available_route_alignment": {
                "path": rel(AVAILABLE_ROUTE_ALIGNMENT),
                "evidence_id": route_alignment.get("evidence_id"),
                "qa_decision": route_alignment.get("qa_decision"),
            },
        },
        "reference_context": summary,
        "row_decision": {
            "tracker_id": "TRK-W70-0169",
            "item_id": "ITEM-W70-0169",
            "status": "Required_Not_Complete",
            "qa_decision": "ref_images_1_2_feet_toes_reentry_exact_blocker_no_promotion",
            "promotion_decision": "no_mask_promoted_no_active_input_changed_feet_toes_reentry_blocker",
            "blocker_reason": "foot_toe_gold_references_available_but_body_reference_matrix_whole_body_authority_contact_ownership_floor_support_boundary_and_canonical_polygons_not_passed",
            "masks_changed": [],
            "masks_promoted": [],
            "hard_gate_rerun_performed": False,
        },
        "artifacts": {
            "panel": rel(PANEL),
        },
        "tracker_item_updates": row_updates,
        "next_step": "Run Wave70 hard gates only after this row-level blocker, then continue active Wave70 sequence without returning to generic route-loop work.",
    }
    for path in [EVIDENCE, CANONICAL_EVIDENCE, TRACKER_EVIDENCE_DIR / EVIDENCE.name, TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, RUNTIME_DIR / "feet_toes_reentry_blocker.json"]:
        write_json(path, payload)

    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-entered `TRK-W70-0169` / `ITEM-W70-0169` after the two-hour supervisor correction and recorded an exact foot/toe authority blocker.

Ref_Image_1+Ref_Image_2 feet/toe reference context is available: Ref_Image_1 has `{summary['ref_image_1_gold']['foot_toe_gold_mask_count']}` foot/toe gold masks, Ref_Image_2 has `{summary['ref_image_2']['foot_toe_overlay_count']}` foot/toe overlays, and the combined body matrix records `{summary['body_matrix']['combined_full_or_near_full_reference_count']}` full/near-full references plus `{summary['body_matrix']['combined_gold_mask_count']}` gold masks. `Ref_Image_1/Full/New folder` remains excluded from feet/toes/ankles/lower-calf proof because it is knees-to-head only.

The row remains `Required_Not_Complete`: body reference matrix pass is false, whole-body authority pass is false, canonical polygon export pass is false, and foot/toe contact/support ownership is not proved. No mask was changed or promoted. No hard-gate rerun was performed in this re-entry step.

Evidence:

{evidence_block}

Next exact local action: run Wave70 hard gates only after this row-level blocker, then continue active Wave70 sequence without returning to generic route-loop work."""
    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - TRK-W70-0169 Feet Toes Reentry Blocker",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - TRK-W70-0169 Feet Toes Reentry Blocker",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - TRK-W70-0169 Feet Toes Reentry Blocker",
            "NEXT_ACTION.md": "Immediate Next Action - TRK-W70-0169 Post-Blocker Gates",
            "QA_EVIDENCE_INDEX.md": "Wave70 0169 Feet Toes Reentry Blocker Evidence",
            "BLOCKERS.md": "Wave70 0169 Feet Toes Exact Blocker",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0169 feet/toes reentry blocker recorded",
                "Returned from route-loop correction to TRK-W70-0169 and recorded exact foot/toe blocker without hard-gate rerun.",
                "; ".join(evidence_paths),
                "Ref_Image_1/2 manifests; body_reference_matrix.json; supervisor correction",
                "W70_0169_FEET_TOES_REENTRY_BLOCKER_NO_PROMOTION",
                rel(EVIDENCE),
                "Run Wave70 hard gates after this row-level blocker; do not return to generic route loop.",
            ]
        )
    print(json.dumps({"evidence": rel(EVIDENCE), "panel": rel(PANEL), "hydration_updates": updates, "qa_decision": payload["row_decision"]["qa_decision"]}, indent=2))


if __name__ == "__main__":
    main()
