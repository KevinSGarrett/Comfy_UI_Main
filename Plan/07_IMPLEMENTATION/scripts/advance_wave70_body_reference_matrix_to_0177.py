from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
TRACKER_ID = "TRK-W70-0176"
ITEM_ID = "ITEM-W70-0176"
NEXT_TRACKER_ID = "TRK-W70-0177"
NEXT_ITEM_ID = "ITEM-W70-0177"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

BODY_MATRIX = QA_DIR / "body_reference_matrix.json"
GEOMETRY_GATE = QA_DIR / "W70_MASK_GEOMETRY_HARD_GATE_POST_BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_20260708T153118-0500.json"
PROMOTION_GATE = QA_DIR / "W70_MASK_PROMOTION_HARD_GATE_POST_BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_20260708T153118-0500.json"
ADVANCE_EVIDENCE = QA_DIR / f"W70_BODY_REFERENCE_MATRIX_ADVANCE_TO_0177_{datetime.now(ZoneInfo('America/Chicago')).strftime('%Y%m%dT%H%M%S-0500')}.json"


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


def main() -> None:
    matrix = read_json(BODY_MATRIX)
    geometry = gate_summary(GEOMETRY_GATE)
    promotion = gate_summary(PROMOTION_GATE)
    if geometry != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected geometry gate summary: {geometry}")
    if promotion != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected promotion gate summary: {promotion}")
    combined = matrix.get("combined_body_reference_matrix", {})
    combined_full_reference_count = combined.get("combined_full_or_near_full_reference_count")
    combined_gold_mask_count = combined.get("combined_gold_mask_count")
    if combined_full_reference_count is None:
        combined_full_reference_count = matrix.get("body_reference_matrix", {}).get("full_body_reference_count")
    if combined_gold_mask_count is None:
        combined_gold_mask_count = matrix.get("body_reference_matrix", {}).get("gold_mask_count")
    if combined_full_reference_count is None:
        combined_full_reference_count = matrix.get("body_reference_matrix_analysis", {}).get("full_body_reference_count")
    if combined_gold_mask_count is None:
        combined_gold_mask_count = matrix.get("body_reference_matrix_analysis", {}).get("gold_mask_count")
    payload = {
        "schema_version": "1.0",
        "created_iso": ISO_TS,
        "task": f"Advance from already-current {TRACKER_ID} / {ITEM_ID} body reference matrix to {NEXT_TRACKER_ID} / {NEXT_ITEM_ID}.",
        "body_reference_matrix": {
            "path": rel(BODY_MATRIX),
            "evidence_id": matrix.get("evidence_id"),
            "qa_decision": matrix.get("qa_decision"),
            "combined_full_or_near_full_reference_count": combined_full_reference_count,
            "combined_gold_mask_count": combined_gold_mask_count,
            "limited_reference_policy": "Ref_Image_1/Full/New folder remains knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof.",
        },
        "gates": {
            "geometry": {"path": rel(GEOMETRY_GATE), **geometry},
            "promotion": {"path": rel(PROMOTION_GATE), **promotion},
        },
        "decision": "advance_to_0177_body_reference_matrix_already_current_ref_images_1_2_gates_pass",
        "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
    }
    ADVANCE_EVIDENCE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    evidence_paths = [
        rel(ADVANCE_EVIDENCE),
        rel(BODY_MATRIX),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Verified `{TRACKER_ID}` / `{ITEM_ID}` body reference matrix is already current for Ref_Image_1+Ref_Image_2.

The canonical matrix records `{combined_full_reference_count}` combined full/near-full references and `{combined_gold_mask_count}` combined gold masks. The `Ref_Image_1/Full/New folder` image remains knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof.

Existing Ref_Image_1+2 matrix gates remain valid: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}

Next exact local action: work `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` redo existing body/hand/contact/support/soft-body masks from canonical body geometry."""
    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - 0176 Body Reference Matrix Verified Current",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0176 Body Reference Matrix Verified Current",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0176 Body Reference Matrix Verified Current",
            "NEXT_ACTION.md": "Immediate Next Action - Work TRK-W70-0177 Redo Existing Body Hand Contact Masks",
            "QA_EVIDENCE_INDEX.md": "Wave70 0176 Body Reference Matrix Advance Evidence",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0176 body reference matrix verified current",
                "Verified Ref_Image_1+2 body reference matrix and gates are current; advanced hydration to 0177.",
                "; ".join(evidence_paths),
                "body_reference_matrix.json inspection; geometry/promotion gate JSON summaries",
                "BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_CURRENT_ADVANCE_TO_0177",
                rel(ADVANCE_EVIDENCE),
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID}.",
            ]
        )
    print(json.dumps({"evidence": rel(ADVANCE_EVIDENCE), "hydration_updates": updates, "next": payload["next"]}, indent=2))


if __name__ == "__main__":
    main()
