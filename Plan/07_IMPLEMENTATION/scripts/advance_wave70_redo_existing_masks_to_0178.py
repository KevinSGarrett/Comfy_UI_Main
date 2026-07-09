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

TRACKER_ID = "TRK-W70-0177"
ITEM_ID = "ITEM-W70-0177"
NEXT_TRACKER_ID = "TRK-W70-0178"
NEXT_ITEM_ID = "ITEM-W70-0178"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

REDO_EVIDENCE = QA_DIR / "redo_existing_body_hand_contact_masks.json"
GEOMETRY_GATE = QA_DIR / "W70_MASK_GEOMETRY_HARD_GATE_POST_REDO_EXISTING_BODY_HAND_CONTACT_REF_IMAGES_1_2_20260708T153727-0500.json"
PROMOTION_GATE = QA_DIR / "W70_MASK_PROMOTION_HARD_GATE_POST_REDO_EXISTING_BODY_HAND_CONTACT_REF_IMAGES_1_2_20260708T153727-0500.json"
ADVANCE_EVIDENCE = QA_DIR / f"W70_REDO_EXISTING_BODY_HAND_CONTACT_ADVANCE_TO_0178_{STAMP}.json"


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    redo = read_json(REDO_EVIDENCE)
    analysis = redo.get("redo_existing_body_hand_contact_analysis") or {}
    context = analysis.get("body_reference_context") or {}
    whole_body = redo.get("whole_body_geometry_authority") or {}
    geometry = gate_summary(GEOMETRY_GATE)
    promotion = gate_summary(PROMOTION_GATE)

    require(geometry == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected geometry gate: {geometry}")
    require(promotion == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected promotion gate: {promotion}")
    require(redo.get("qa_decision") == "blocked_exact_local_canonical_body_geometry_unavailable_ref_images_1_2_context_available", "Unexpected 0177 QA decision")
    require(analysis.get("canonical_body_geometry_available") is False, "Canonical body geometry unexpectedly available")
    require(analysis.get("body_reference_context_available") is True, "Body reference context is not available")
    require(whole_body.get("result") == "blocked", "Whole-body geometry authority is not blocked")
    require(whole_body.get("body_reference_context_available") is True, "Whole-body authority does not acknowledge Ref_Image_1+2 context")
    require(whole_body.get("body_reference_matrix_pass") is False, "Body reference matrix unexpectedly passed")
    require(context.get("combined_full_or_near_full_reference_count") == 9, f"Unexpected full/near-full ref count: {context.get('combined_full_or_near_full_reference_count')}")
    require(context.get("combined_gold_mask_count") == 78, f"Unexpected gold mask count: {context.get('combined_gold_mask_count')}")

    payload = {
        "schema_version": "1.0",
        "created_iso": ISO_TS,
        "task": f"Advance from already-recorded {TRACKER_ID} / {ITEM_ID} redo-existing-masks blocker to {NEXT_TRACKER_ID} / {NEXT_ITEM_ID}.",
        "source_evidence": {
            "path": rel(REDO_EVIDENCE),
            "evidence_id": redo.get("evidence_id"),
            "qa_decision": redo.get("qa_decision"),
            "promotion_decision": redo.get("promotion_decision"),
        },
        "verified_reference_context": {
            "body_reference_context_available": analysis.get("body_reference_context_available"),
            "combined_full_or_near_full_reference_count": context.get("combined_full_or_near_full_reference_count"),
            "combined_gold_mask_count": context.get("combined_gold_mask_count"),
            "ref_image_1_full_or_near_full_reference_count": context.get("ref_image_1_full_or_near_full_reference_count"),
            "ref_image_2_full_body_reference_count": context.get("ref_image_2_full_body_reference_count"),
            "ref_image_1_limited_reference_policy": context.get("ref_image_1_limited_reference_policy"),
        },
        "verified_blocker": {
            "canonical_body_geometry_available": analysis.get("canonical_body_geometry_available"),
            "whole_body_geometry_authority_pass": analysis.get("whole_body_geometry_authority_pass"),
            "body_reference_matrix_pass": analysis.get("body_reference_matrix_pass"),
            "reason": whole_body.get("blocked_reason"),
        },
        "gates": {
            "geometry": {"path": rel(GEOMETRY_GATE), **geometry},
            "promotion": {"path": rel(PROMOTION_GATE), **promotion},
        },
        "decision": "advance_to_0178_redo_existing_masks_blocker_already_recorded_ref_images_1_2_gates_pass",
        "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
    }
    ADVANCE_EVIDENCE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    evidence_paths = [
        rel(ADVANCE_EVIDENCE),
        rel(REDO_EVIDENCE),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Verified `{TRACKER_ID}` / `{ITEM_ID}` redo-existing body/hand/contact/support/soft-body masks already has a current Ref_Image_1+Ref_Image_2 fail-closed blocker.

The blocker records `9` combined full/near-full references and `78` combined gold masks, with `Ref_Image_1/Full/New folder` still treated as knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof.

No mask was promoted: canonical body geometry remains unavailable, the body reference matrix is context-available but not passed, and whole-body geometry authority remains blocked. Existing body/hand/contact/support/soft-body masks therefore remain untrusted rather than redrawn from guessed geometry.

Post-0177 gates remain valid: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}

Next exact local action: work `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` whole-body authority integration into Wave70 promotion and scheduled QA gates."""

    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - 0177 Redo Existing Masks Verified Blocked",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0177 Redo Existing Masks Verified Blocked",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0177 Redo Existing Masks Verified Blocked",
            "NEXT_ACTION.md": "Immediate Next Action - Work TRK-W70-0178 Whole Body Geometry Promotion Integration",
            "QA_EVIDENCE_INDEX.md": "Wave70 0177 Redo Existing Masks Advance Evidence",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0177 redo-existing masks verified blocked",
                "Verified Ref_Image_1+2 redo-existing-masks blocker and gates are current; advanced hydration to 0178.",
                "; ".join(evidence_paths),
                "redo_existing_body_hand_contact_masks.json inspection; geometry/promotion gate JSON summaries",
                "REDO_EXISTING_BODY_HAND_CONTACT_REF_IMAGES_1_2_BLOCKER_ADVANCE_TO_0178",
                rel(ADVANCE_EVIDENCE),
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID}.",
            ]
        )
    print(json.dumps({"evidence": rel(ADVANCE_EVIDENCE), "hydration_updates": updates, "next": payload["next"]}, indent=2))


if __name__ == "__main__":
    main()
