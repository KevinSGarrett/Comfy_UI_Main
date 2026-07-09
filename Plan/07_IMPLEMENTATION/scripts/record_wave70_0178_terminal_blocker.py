from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W70-0178"
ITEM_ID = "ITEM-W70-0178"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
TRACKER_PATH = PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
ITEMS_PATH = PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv"
WAVE71_TRACKER_PATH = PROJECT_ROOT / "Plan/Tracker/wave71_soft_body_physics_deformation_map_system_tracker.csv"

INTEGRATION_EVIDENCE = QA_DIR / "whole_body_geometry_promotion_integration.json"
ADVANCE_0177_EVIDENCE = QA_DIR / "W70_REDO_EXISTING_BODY_HAND_CONTACT_ADVANCE_TO_0178_20260708T183724-0500.json"
TERMINAL_EVIDENCE = QA_DIR / f"W70_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_TERMINAL_BLOCKER_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


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


def tracker_number(value: str) -> int:
    match = re.search(r"-(\d+)$", value or "")
    return int(match.group(1)) if match else -1


def main() -> None:
    integration = read_json(INTEGRATION_EVIDENCE)
    integration_block = integration.get("whole_body_geometry_promotion_integration") or {}
    prereq = integration_block.get("prerequisite_gate_state") or {}
    context = prereq.get("body_reference_context") or {}
    post_gates = integration.get("post_evaluation_hard_gates") or {}
    geometry_path = PROJECT_ROOT / (post_gates.get("geometry") or {}).get("path", "")
    promotion_path = PROJECT_ROOT / (post_gates.get("promotion") or {}).get("path", "")
    geometry = gate_summary(geometry_path)
    promotion = gate_summary(promotion_path)

    tracker_rows = read_csv(TRACKER_PATH)
    item_rows = read_csv(ITEMS_PATH)
    wave71_rows = read_csv(WAVE71_TRACKER_PATH)
    max_tracker = max(tracker_rows, key=lambda row: tracker_number(row.get("Tracker_ID", "")))
    max_item = max(item_rows, key=lambda row: tracker_number(row.get("Item_ID", "")))
    wave71_statuses = sorted({row.get("Status", "") for row in wave71_rows})

    require(integration.get("qa_decision") == "blocked_exact_local_whole_body_geometry_authority_not_integrated_ref_images_1_2_context_available", "Unexpected 0178 QA decision")
    require(integration_block.get("result") == "blocked", "0178 integration is not blocked")
    require(integration_block.get("blocker_status") == "Blocked_Body_Geometry_Authority_Not_Integrated", "Unexpected 0178 blocker status")
    require(integration_block.get("completion_allowed") is False, "0178 unexpectedly allows completion")
    require(integration_block.get("fail_closed_policy_confirmed") is True, "0178 fail-closed policy not confirmed")
    require(integration_block.get("masks_changed") == [], "0178 changed masks")
    require(integration_block.get("masks_promoted") == [], "0178 promoted masks")
    require(context.get("combined_full_or_near_full_reference_count") == 9, f"Unexpected full/near-full ref count: {context.get('combined_full_or_near_full_reference_count')}")
    require(context.get("combined_gold_mask_count") == 78, f"Unexpected gold mask count: {context.get('combined_gold_mask_count')}")
    require(geometry == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected geometry gate: {geometry}")
    require(promotion == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected promotion gate: {promotion}")
    require(max_tracker.get("Tracker_ID") == TRACKER_ID, f"Unexpected final tracker row: {max_tracker.get('Tracker_ID')}")
    require(max_item.get("Item_ID") == ITEM_ID, f"Unexpected final item row: {max_item.get('Item_ID')}")
    require(wave71_statuses == ["Deferred_Required_Not_Complete"], f"Wave71 is not fully deferred: {wave71_statuses}")

    payload = {
        "schema_version": "1.0",
        "created_iso": ISO_TS,
        "task": f"Record terminal Wave70 blocker at {TRACKER_ID} / {ITEM_ID} without activating Wave71.",
        "source_evidence": {
            "path": rel(INTEGRATION_EVIDENCE),
            "evidence_id": integration.get("evidence_id"),
            "qa_decision": integration.get("qa_decision"),
            "promotion_decision": integration.get("promotion_decision"),
        },
        "verified_reference_context": {
            "combined_full_or_near_full_reference_count": context.get("combined_full_or_near_full_reference_count"),
            "combined_gold_mask_count": context.get("combined_gold_mask_count"),
            "ref_image_2_gold_mask_count": context.get("ref_image_2_gold_mask_count"),
            "ref_image_1_limited_reference_policy": context.get("ref_image_1_limited_reference_policy"),
        },
        "terminal_blocker": {
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "blocker_status": integration_block.get("blocker_status"),
            "completion_allowed": integration_block.get("completion_allowed"),
            "fail_closed_policy_confirmed": integration_block.get("fail_closed_policy_confirmed"),
            "masks_changed": integration_block.get("masks_changed"),
            "masks_promoted": integration_block.get("masks_promoted"),
            "next_allowed_state": "Do not activate Wave71+ without explicit activation-gate proof; continue acquiring or integrating canonical whole-body geometry prerequisites.",
        },
        "wave70_boundary": {
            "tracker_rows": len(tracker_rows),
            "item_rows": len(item_rows),
            "final_tracker_id": max_tracker.get("Tracker_ID"),
            "final_item_id": max_item.get("Item_ID"),
            "known_sequence_gap": "TRK-W70-0173 / ITEM-W70-0173 missing from Wave70 CSVs and already recorded as MILESTONE_SEQUENCE_LEDGER_GAP.",
        },
        "wave71_deferred_check": {
            "path": rel(WAVE71_TRACKER_PATH),
            "row_count": len(wave71_rows),
            "statuses": wave71_statuses,
        },
        "gates": {
            "geometry": {"path": rel(geometry_path), **geometry},
            "promotion": {"path": rel(promotion_path), **promotion},
        },
        "decision": "wave70_terminal_blocker_recorded_wave71_deferred_no_activation",
    }
    TERMINAL_EVIDENCE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    evidence_paths = [
        rel(TERMINAL_EVIDENCE),
        rel(INTEGRATION_EVIDENCE),
        rel(ADVANCE_0177_EVIDENCE),
        rel(geometry_path),
        rel(promotion_path),
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Verified terminal Wave70 row `{TRACKER_ID}` / `{ITEM_ID}` remains blocked exactly: whole-body geometry authority is not integrated, canonical body geometry is unavailable, and no mask was changed or promoted.

Ref_Image_1+Ref_Image_2 context is preserved in the blocker: `9` combined full/near-full references and `78` combined gold masks. The `Ref_Image_1/Full/New folder` image remains knees-to-head only and excluded from feet/toes/ankles/lower-calf/support proof.

Wave70 local boundary is `{TRACKER_ID}` / `{ITEM_ID}` with 166 tracker rows and 166 item rows; `TRK-W70-0173` / `ITEM-W70-0173` remains a recorded sequence ledger gap. Wave71 remains fully deferred with 34 rows at `Deferred_Required_Not_Complete`; no Wave71+ activation was performed.

Post-0178 gates remain valid: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}

Next exact local action: keep Wave70 fail-closed and acquire or integrate canonical whole-body geometry prerequisites before any body/hand/contact/support/soft-body promotion or Wave71+ activation."""

    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - Wave70 Terminal Blocker",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Wave70 Terminal Blocker",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Wave70 Terminal Blocker",
            "NEXT_ACTION.md": "Immediate Next Action - Wave70 Terminal Whole Body Geometry Blocker",
            "QA_EVIDENCE_INDEX.md": "Wave70 0178 Terminal Blocker Evidence",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 terminal blocker recorded",
                "Verified 0178 whole-body integration blocker, hard gates, Wave70 boundary, and Wave71 deferred state.",
                "; ".join(evidence_paths),
                "whole_body_geometry_promotion_integration.json inspection; gate JSON summaries; Wave70/Wave71 CSV checks",
                "WAVE70_TERMINAL_BLOCKER_WAVE71_DEFERRED_NO_ACTIVATION",
                rel(TERMINAL_EVIDENCE),
                "Acquire/integrate canonical whole-body geometry prerequisites before any promotion or Wave71+ activation.",
            ]
        )
    print(json.dumps({"evidence": rel(TERMINAL_EVIDENCE), "hydration_updates": updates, "decision": payload["decision"]}, indent=2))


if __name__ == "__main__":
    main()
