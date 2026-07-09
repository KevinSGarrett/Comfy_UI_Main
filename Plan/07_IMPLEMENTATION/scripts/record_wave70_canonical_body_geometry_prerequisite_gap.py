from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"

BODY_MATRIX = QA_DIR / "body_reference_matrix.json"
REF1_FULL = QA_DIR / "ref_image_1_full_body_references.json"
REF1_GOLD = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
REF2_BODY = QA_DIR / "ref_image_2_body_reference.json"
TERMINAL_BLOCKER = QA_DIR / "W70_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_TERMINAL_BLOCKER_20260708T183948-0500.json"

GEOMETRY_GATE = QA_DIR / "W70_MASK_GEOMETRY_HARD_GATE_POST_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_REF_IMAGES_1_2_20260708T154144-0500.json"
PROMOTION_GATE = QA_DIR / "W70_MASK_PROMOTION_HARD_GATE_POST_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_REF_IMAGES_1_2_20260708T154144-0500.json"

EVIDENCE_NAME = f"W70_CANONICAL_BODY_GEOMETRY_PREREQUISITE_GAP_{STAMP}.json"
EVIDENCE = QA_DIR / EVIDENCE_NAME
CANONICAL_EVIDENCE = QA_DIR / "canonical_body_geometry_prerequisite_gap.json"
TRACKER_COPY = TRACKER_EVIDENCE_DIR / EVIDENCE_NAME
TRACKER_CANONICAL_COPY = TRACKER_EVIDENCE_DIR / "canonical_body_geometry_prerequisite_gap.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def gate_summary(path: Path) -> dict[str, int]:
    payload = read_json(path)
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def slot_summary(slots: list[dict[str, object]]) -> dict[str, object]:
    by_status: dict[str, int] = {}
    blocked_slots: list[dict[str, str]] = []
    route_not_complete_slots: list[dict[str, str]] = []
    for slot in slots:
        status = str(slot.get("status", ""))
        by_status[status] = by_status.get(status, 0) + 1
        record = {
            "slot_id": str(slot.get("slot_id", "")),
            "status": status,
            "reason": str(slot.get("reason", "")),
        }
        if status == "blocked":
            blocked_slots.append(record)
        elif status in {"reference_available_route_not_complete", "required_not_complete"}:
            route_not_complete_slots.append(record)
    return {
        "by_status": by_status,
        "blocked_slots": blocked_slots,
        "route_not_complete_slots": route_not_complete_slots,
    }


def main() -> None:
    matrix = read_json(BODY_MATRIX)
    ref1_full = read_json(REF1_FULL)
    ref1_gold = read_json(REF1_GOLD)
    ref2_body = read_json(REF2_BODY)
    terminal = read_json(TERMINAL_BLOCKER)
    analysis = matrix.get("body_reference_matrix_analysis") or {}
    slots = analysis.get("slot_status") or []
    geometry = gate_summary(GEOMETRY_GATE)
    promotion = gate_summary(PROMOTION_GATE)

    require(analysis.get("slots_required_count") == 13, "Unexpected required body matrix slot count")
    require(analysis.get("source_visibility_slots_available_count") == 10, "Unexpected visible body matrix slot count")
    require(analysis.get("slots_blocked_count") == 3, "Unexpected blocked body matrix slot count")
    require(analysis.get("full_body_reference_count") == 9, "Unexpected full/near-full reference count")
    require(analysis.get("gold_mask_count") == 78, "Unexpected combined gold mask count")
    require(analysis.get("body_reference_matrix_pass") is False, "Body reference matrix unexpectedly passed")
    require(analysis.get("whole_body_geometry_authority_pass") is False, "Whole-body authority unexpectedly passed")
    require(terminal.get("decision") == "wave70_terminal_blocker_recorded_wave71_deferred_no_activation", "Terminal blocker evidence is not current")
    require(geometry == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected geometry gate: {geometry}")
    require(promotion == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected promotion gate: {promotion}")

    slot_state = slot_summary(slots)
    required_reference_package = [
        {
            "requirement_id": "front_full_body_with_feet_visible",
            "priority": "already_partially_satisfied",
            "needed": "Keep at least one clean front full-body source with head through feet visible and matching masks.",
            "current_status": "covered by Ref_Image_1 and Ref_Image_2 context, but not enough for canonical pass without model-backed geometry.",
        },
        {
            "requirement_id": "left_side_or_left_profile_full_body",
            "priority": "required_next",
            "needed": "Full body left-side or near-profile view with feet, hands, torso, pelvis, calves, and hair visible where possible, plus organized masks.",
            "current_status": "not proven as a distinct side/profile canonical slot.",
        },
        {
            "requirement_id": "right_side_or_right_profile_full_body",
            "priority": "required_next",
            "needed": "Full body right-side or near-profile view with feet, hands, torso, pelvis, calves, and hair visible where possible, plus organized masks.",
            "current_status": "not proven as a distinct side/profile canonical slot.",
        },
        {
            "requirement_id": "back_full_body",
            "priority": "required_next",
            "needed": "Back-view full body source and masks for hair/back/shoulders/arms/glutes/thighs/calves/feet boundaries.",
            "current_status": "missing; back geometry cannot be inferred from front references.",
        },
        {
            "requirement_id": "three_quarter_left_and_right",
            "priority": "high",
            "needed": "3/4 left and 3/4 right full-body views to validate side transitions, limb overlap, and protected neighbors.",
            "current_status": "static context exists but cross-angle canonical evidence is not passed.",
        },
        {
            "requirement_id": "occlusion_contact_support_case",
            "priority": "required_next",
            "needed": "One or more full-body cases with hands crossing body, limb-over-limb, body on support surface, or object/contact boundary, with owner/contact masks.",
            "current_status": "blocked; current matrix does not prove contact/support ownership.",
        },
        {
            "requirement_id": "multi_person_or_owner_separation_case",
            "priority": "required_for_generalization",
            "needed": "At least one multi-person or clear foreground/background owner-separation case with masks if multi-character/contact masks are in scope.",
            "current_status": "blocked; no occlusion or multi-person slot is filled.",
        },
        {
            "requirement_id": "model_backed_geometry_stack",
            "priority": "required_before_promotion",
            "needed": "Local pose, hand, human parsing, promptable refinement, contact ownership, canonical polygon export, and coordinate transform evidence.",
            "current_status": "blocked locally; static gold overlays are calibration evidence, not canonical polygon authority.",
        },
    ]

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_BODY_GEOMETRY_PREREQUISITE_GAP_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record exact Wave70 canonical whole-body geometry prerequisite gap after Ref_Image_1 and Ref_Image_2 ingestion.",
        "source_evidence": {
            "body_reference_matrix": {
                "path": rel(BODY_MATRIX),
                "evidence_id": matrix.get("evidence_id"),
                "qa_decision": matrix.get("qa_decision"),
            },
            "ref_image_1_full_body_references": {
                "path": rel(REF1_FULL),
                "evidence_id": ref1_full.get("evidence_id"),
                "count": len(ref1_full.get("full_body_references") or []),
            },
            "ref_image_1_gold_masks": {
                "path": rel(REF1_GOLD),
                "evidence_id": ref1_gold.get("evidence_id"),
                "extracted_nonzero_mask_count": ref1_gold.get("extracted_nonzero_mask_count"),
            },
            "ref_image_2_body_reference": {
                "path": rel(REF2_BODY),
                "evidence_id": ref2_body.get("evidence_id"),
                "manifest_row_count": (ref2_body.get("manifest") or {}).get("row_count"),
                "located_overlay_count": (ref2_body.get("manifest") or {}).get("located_overlay_count"),
            },
            "wave70_terminal_blocker": {
                "path": rel(TERMINAL_BLOCKER),
                "decision": terminal.get("decision"),
            },
        },
        "provided_reference_context": {
            "combined_full_or_near_full_reference_count": analysis.get("full_body_reference_count"),
            "combined_gold_mask_count": analysis.get("gold_mask_count"),
            "source_visibility_slots_available_count": analysis.get("source_visibility_slots_available_count"),
            "ref_image_1_limited_reference_policy": "Ref_Image_1/Full/New folder/8ead94ca6f2884fb1ae671fee89e8126.jpg is knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof.",
            "main_reference_layout_note": "Ref_Image_1 main composite has partial 1/3-body images in the top section and full body-part mask panels in the lower section; the top section is not expected to contain all body-part masks.",
            "gold_overlays_are_calibration_not_authority": True,
        },
        "matrix_gap_summary": {
            "required_body_matrix_slots": analysis.get("required_body_matrix_slots"),
            "slots_required_count": analysis.get("slots_required_count"),
            "slots_blocked_count": analysis.get("slots_blocked_count"),
            "source_visibility_matrix_pass": analysis.get("source_visibility_matrix_pass"),
            "body_reference_matrix_pass": analysis.get("body_reference_matrix_pass"),
            "cross_subject_generalization_pass": analysis.get("cross_subject_generalization_pass"),
            "whole_body_geometry_authority_pass": analysis.get("whole_body_geometry_authority_pass"),
            "canonical_polygon_export_pass": analysis.get("canonical_polygon_export_pass"),
            **slot_state,
        },
        "required_reference_package": required_reference_package,
        "promotion_policy": {
            "masks_changed": [],
            "masks_promoted": [],
            "completion_allowed": False,
            "next_allowed_state": "Keep Wave70 fail-closed until canonical whole-body geometry prerequisites are acquired or integrated and hard gates pass.",
        },
        "gates": {
            "geometry": {"path": rel(GEOMETRY_GATE), **geometry},
            "promotion": {"path": rel(PROMOTION_GATE), **promotion},
        },
        "qa_decision": "canonical_body_geometry_prerequisite_gap_recorded_ref_images_1_2_context_available_no_promotion",
        "next_step": "Acquire or integrate side, back, contact/occlusion, and model-backed canonical body geometry prerequisites before any body/hand/contact/support/soft-body promotion or Wave71+ activation.",
    }

    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_COPY, payload)
    write_json(TRACKER_CANONICAL_COPY, payload)

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_COPY),
        rel(BODY_MATRIX),
        rel(TERMINAL_BLOCKER),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Recorded the canonical whole-body geometry prerequisite gap after Ref_Image_1+Ref_Image_2 ingestion.

Current usable context remains `9` combined full/near-full references and `78` combined gold masks. This is enough calibration/reference context to supersede the old missing-full-body-reference blocker, but not enough to pass canonical whole-body geometry authority. Static overlays remain calibration evidence, not canonical polygon authority.

Required next evidence before body/hand/contact/support/soft-body promotion: left side/profile full body, right side/profile full body, back full body, 3/4 left and right, contact/support or occlusion cases, optional multi-person owner-separation case for multi-character/contact scope, and a local model-backed geometry stack with pose, hands, human parsing, promptable refinement, contact ownership, canonical polygons, and coordinate transforms.

Clarifications preserved: `Ref_Image_1/Full/New folder` is knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof; the top portion of the Ref_Image_1 composite contains partial 1/3-body references and is not expected to mask all body parts.

Wave70 remains fail-closed. No masks were changed or promoted. Post-0178 geometry and promotion gates remain 332 checked, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}

Next exact local action: acquire or integrate the missing canonical whole-body geometry prerequisites, then rerun body reference matrix, whole-body authority, geometry gate, and promotion gate before any Wave71+ activation."""

    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - Canonical Body Geometry Prerequisite Gap",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Canonical Body Geometry Prerequisite Gap",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Canonical Body Geometry Prerequisite Gap",
            "NEXT_ACTION.md": "Immediate Next Action - Canonical Body Geometry Prerequisites",
            "QA_EVIDENCE_INDEX.md": "Wave70 Canonical Body Geometry Prerequisite Gap Evidence",
            "BLOCKERS.md": "Wave70 Canonical Body Geometry Prerequisite Gap",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 canonical body geometry prerequisite gap recorded",
                "Converted terminal whole-body blocker into exact missing reference/model-backed geometry prerequisite ledger.",
                "; ".join(evidence_paths),
                "body_reference_matrix.json; Ref_Image_1/2 manifests; terminal blocker; geometry/promotion gate summaries",
                "CANONICAL_BODY_GEOMETRY_PREREQUISITE_GAP_NO_PROMOTION",
                rel(EVIDENCE),
                "Acquire or integrate missing side/back/contact/occlusion/model-backed canonical geometry prerequisites.",
            ]
        )

    print(json.dumps({"evidence": rel(EVIDENCE), "canonical": rel(CANONICAL_EVIDENCE), "hydration_updates": updates}, indent=2))


if __name__ == "__main__":
    main()
