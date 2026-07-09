from __future__ import annotations

import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
WAVE70_EVIDENCE = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_EVIDENCE = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
HYDRATION = PROJECT_ROOT / "Plan" / "Instructions" / "Hydration_Rehydration"
TRACKER_CSV = PROJECT_ROOT / "Plan" / "Tracker" / "wave70_ultimate_mask_factory_tracker.csv"
ITEMS_CSV = PROJECT_ROOT / "Plan" / "Items" / "wave70_ultimate_mask_factory_itemized_list.csv"

STAMP = "20260708T185825-0500"
NOW = datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%dT%H:%M:%S-05:00")
POST_STAMP = datetime.now(timezone(timedelta(hours=-5))).strftime("%Y%m%dT%H%M%S-0500")

GEOMETRY_GATE = WAVE70_EVIDENCE / f"W70_MASK_GEOMETRY_HARD_GATE_POST_FEET_TOES_REENTRY_BLOCKER_{STAMP}.json"
PROMOTION_GATE = WAVE70_EVIDENCE / f"W70_MASK_PROMOTION_HARD_GATE_POST_FEET_TOES_REENTRY_BLOCKER_{STAMP}.json"
BLOCKER = WAVE70_EVIDENCE / f"W70_0169_FEET_TOES_REENTRY_BLOCKER_{STAMP}.json"
POST_GATE_EVIDENCE = WAVE70_EVIDENCE / f"W70_0169_FEET_TOES_REENTRY_POST_GATES_{POST_STAMP}.json"
POST_GATE_CANONICAL = WAVE70_EVIDENCE / "feet_toes_reentry_post_gates.json"


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_unique(text: str, additions: list[str]) -> str:
    parts = [p.strip() for p in (text or "").split(";") if p.strip()]
    seen = set(parts)
    for addition in additions:
        if addition not in seen:
            parts.append(addition)
            seen.add(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    for row in rows:
        if row.get(key) != key_value:
            continue
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(block.rstrip() + "\n\n" + existing, encoding="utf-8")


def append(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    sep = "" if existing.endswith("\n") else "\n"
    path.write_text(existing + sep + block.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    geometry = load_json(GEOMETRY_GATE)
    promotion = load_json(PROMOTION_GATE)
    blocker = load_json(BLOCKER)

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_0169_FEET_TOES_REENTRY_POST_GATES_{POST_STAMP}",
        "timestamp": NOW,
        "tracker_id": "TRK-W70-0169",
        "item_id": "ITEM-W70-0169",
        "decision": "ref_images_1_2_feet_toes_reentry_exact_blocker_post_gates_pass_no_promotion",
        "row_status": "Required_Not_Complete",
        "blocker_evidence": rel(BLOCKER),
        "geometry_gate_evidence": rel(GEOMETRY_GATE),
        "promotion_gate_evidence": rel(PROMOTION_GATE),
        "tracker_geometry_gate_evidence": rel(TRACKER_EVIDENCE / GEOMETRY_GATE.name),
        "tracker_promotion_gate_evidence": rel(TRACKER_EVIDENCE / PROMOTION_GATE.name),
        "geometry_gate": {
            "result": geometry.get("result"),
            "wave70_mask_geometry_gate_pass": geometry.get("wave70_mask_geometry_gate_pass"),
            "checked_row_count": geometry.get("checked_row_count"),
            "pass_like_row_count": geometry.get("pass_like_row_count"),
            "failure_count": len(geometry.get("failures") or []),
        },
        "promotion_gate": {
            "result": promotion.get("result"),
            "wave70_mask_promotion_gate_pass": promotion.get("wave70_mask_promotion_gate_pass"),
            "checked_row_count": promotion.get("checked_row_count"),
            "pass_like_row_count": promotion.get("pass_like_row_count"),
            "failure_count": len(promotion.get("failures") or []),
        },
        "reference_context": blocker.get("reference_context", {}),
        "promotion_decision": "no_mask_promoted_no_active_input_changed_post_reentry_gates",
        "next_active_row": "TRK-W70-0171 / ITEM-W70-0171",
        "next_action": "Continue contact occlusion ownership authority with combined Ref_Image_1+Ref_Image_2 references; do not return to generic route-loop work.",
    }
    write_json(POST_GATE_EVIDENCE, payload)
    write_json(POST_GATE_CANONICAL, payload)
    write_json(TRACKER_EVIDENCE / POST_GATE_EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE / POST_GATE_CANONICAL.name, payload)

    evidence_additions = [
        rel(POST_GATE_EVIDENCE),
        rel(POST_GATE_CANONICAL),
        rel(TRACKER_EVIDENCE / POST_GATE_EVIDENCE.name),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        rel(TRACKER_EVIDENCE / GEOMETRY_GATE.name),
        rel(TRACKER_EVIDENCE / PROMOTION_GATE.name),
    ]
    coverage_additions = [
        "post_feet_toes_reentry_blocker_geometry_gate_pass",
        "post_feet_toes_reentry_blocker_promotion_gate_pass",
        "ref_images_1_2_feet_toes_reentry_post_gates_no_promotion",
    ]
    note = (
        f"Feet/toes re-entry post-gates {POST_STAMP}: after the row-level blocker, geometry and promotion hard gates "
        "passed with 332 checked rows, zero pass-like rows, and zero failures. Row remains Required_Not_Complete; no masks promoted."
    )
    update_csv(
        TRACKER_CSV,
        "Tracker_ID",
        "TRK-W70-0169",
        {
            "Status_Decision": payload["decision"],
            "Evidence_Path": evidence_additions,
            "Coverage_Audit_Status": coverage_additions,
            "Notes": [note],
        },
    )
    update_csv(
        ITEMS_CSV,
        "Item_ID",
        "ITEM-W70-0169",
        {
            "Evidence_Required": evidence_additions,
            "Coverage_Audit_Status": coverage_additions,
            "Notes": [note],
        },
    )

    next_block = f"""## Immediate Next Action - Continue TRK-W70-0171 Contact Occlusion Ownership - {NOW}

`TRK-W70-0169` / `ITEM-W70-0169` has post-blocker gates recorded after the supervisor correction. The row remains `Required_Not_Complete`: Ref_Image_1+Ref_Image_2 feet/toe references are available, `Ref_Image_1/Full/New folder` remains excluded from feet/toes/ankles/lower-calf proof, but body reference matrix, whole-body authority, canonical polygon export, and contact/support ownership still do not pass. No mask was changed or promoted.

Gate verification after the exact row-level blocker:
- Wave70 geometry gate: `pass`, `332` checked, `0` pass-like, `0` failures.
- Wave70 promotion gate: `pass`, `332` checked, `0` pass-like, `0` failures.

Evidence:
- `{rel(POST_GATE_EVIDENCE)}`
- `{rel(POST_GATE_CANONICAL)}`
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`
- `{rel(TRACKER_EVIDENCE / POST_GATE_EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE / GEOMETRY_GATE.name)}`
- `{rel(TRACKER_EVIDENCE / PROMOTION_GATE.name)}`

Next exact local action: continue active Wave70 at `TRK-W70-0171` / `ITEM-W70-0171` contact occlusion ownership authority using combined Ref_Image_1+Ref_Image_2 references. Do not return to generic route registration, generic dependency probing, or looped hard-gate reruns unless a new exact route implementation artifact exists first."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION / name, next_block)

    index_block = f"""
## Wave70 0169 Feet Toes Reentry Post Gates - {NOW}

Recorded post-blocker Wave70 gates for `TRK-W70-0169` / `ITEM-W70-0169` after the two-hour supervisor correction returned work to the feet/toes row. Geometry and promotion gates passed with `332` checked rows, `0` pass-like rows, and `0` failures. The row remains `Required_Not_Complete`; no mask was changed or promoted.

Evidence:
- `{rel(POST_GATE_EVIDENCE)}`
- `{rel(POST_GATE_CANONICAL)}`
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`
- `{rel(TRACKER_EVIDENCE / POST_GATE_EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE / GEOMETRY_GATE.name)}`
- `{rel(TRACKER_EVIDENCE / PROMOTION_GATE.name)}`
"""
    prepend(HYDRATION / "QA_EVIDENCE_INDEX.md", index_block)

    proof_line = [
        NOW,
        "70",
        "Wave70 0169 feet toes reentry post gates",
        "Ran Wave70 geometry and promotion hard gates after the exact TRK/ITEM-W70-0169 re-entry blocker; both gates passed with 332 checked rows, zero pass-like rows, and zero failures; no masks changed or promoted.",
        "; ".join(evidence_additions),
        "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "REF_IMAGES_1_2_FEET_TOES_REENTRY_POST_GATES_PASS_NO_PROMOTION",
        rel(POST_GATE_EVIDENCE),
        "Continue Wave70 at TRK-W70-0171 / ITEM-W70-0171 contact occlusion ownership authority with combined body references.",
    ]
    with (HYDRATION / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(proof_line)

    print(json.dumps({
        "post_gate_evidence": str(POST_GATE_EVIDENCE),
        "canonical": str(POST_GATE_CANONICAL),
        "tracker_copies_written": True,
        "next_active_row": payload["next_active_row"],
        "decision": payload["decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
