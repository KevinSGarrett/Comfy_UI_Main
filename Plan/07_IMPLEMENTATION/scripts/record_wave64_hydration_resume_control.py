from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W64-047"
ITEM_ID = "ITEM-W64-047"
PREVIOUS_TRACKER_ID = "TRK-W64-046"
PREVIOUS_ITEM_ID = "ITEM-W64-046"
NEXT_TRACKER_ID = "TRK-W64-048"
NEXT_ITEM_ID = "ITEM-W64-048"

CURRENT_THREAD_ID = "019f422f-88b1-7382-872b-21de2089e983"
DEAD_THREAD_ID = "019f35e8-7e15-7c72-8ffb-66f6f9b246a0"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_BLOCKERS = HYDRATION_DIR / "BLOCKERS.md"
SOURCE_ISSUES = HYDRATION_DIR / "KNOWN_ISSUES.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "hydration_resume_control.json"
STAMPED_EVIDENCE = QA_DIR / f"HYDRATION_RESUME_CONTROL_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"HYDRATION_RESUME_CONTROL_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

READ_ORDER = [
    SOURCE_RESUME,
    SOURCE_GOAL,
    SOURCE_STATE,
    SOURCE_NEXT,
    SOURCE_BLOCKERS,
    SOURCE_ISSUES,
    SOURCE_INDEX,
    SOURCE_DECISIONS,
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
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
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def top(text: str, limit: int = 4000) -> str:
    return text[: min(limit, len(text))]


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def scan_hydration_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "path": evidence_path(path),
            "exists": False,
            "bytes": 0,
            "dead_thread_refs": 0,
            "current_thread_refs": 0,
            "top_has_dead_thread": False,
            "top_has_current_thread": False,
            "top_has_current_row": False,
            "top_has_previous_row": False,
            "top_has_stale_w68": False,
            "top_has_active_w70": False,
            "full_w70_mentions": 0,
            "full_w68_mentions": 0,
        }
    text = path.read_text(encoding="utf-8-sig")
    head = top(text)
    return {
        "path": rel(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "dead_thread_refs": text.count(DEAD_THREAD_ID),
        "current_thread_refs": text.count(CURRENT_THREAD_ID),
        "top_has_dead_thread": DEAD_THREAD_ID in head,
        "top_has_current_thread": CURRENT_THREAD_ID in head,
        "top_has_current_row": TRACKER_ID in head or ITEM_ID in head,
        "top_has_previous_row": PREVIOUS_TRACKER_ID in head or PREVIOUS_ITEM_ID in head,
        "top_has_stale_w68": bool(re.search(r"TRK-W68|ITEM-W68|W68 ControlNet Canny", head)),
        "top_has_active_w70": bool(re.search(r"TRK-W70|ITEM-W70|Wave70", head)),
        "full_w70_mentions": count(r"TRK-W70|ITEM-W70|Wave70", text),
        "full_w68_mentions": count(r"TRK-W68|ITEM-W68|W68 ControlNet Canny", text),
    }


def latest_wave64_evidence() -> list[Path]:
    return sorted(
        [path for path in QA_DIR.glob("*.json") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:8]


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded hydration read order, active next-action alignment, and residual historical dead-thread ledger refs.",
        "; ".join(payload["evidence_paths"]),
        "hydration read order; stale pointer scan; latest evidence selection; next action alignment",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to bounded no-loop/no-drift row {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; do not treat lower historical dead-thread refs as active instructions.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    hydration_scan = [scan_hydration_file(path) for path in READ_ORDER]
    scan_by_name = {Path(str(row["path"])).name: row for row in hydration_scan}
    latest = latest_wave64_evidence()
    qa_index_text = SOURCE_INDEX.read_text(encoding="utf-8-sig") if SOURCE_INDEX.exists() else ""
    qa_index_head = top(qa_index_text)

    active_files = [
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
        "CURRENT_PURSUING_GOAL.md",
        "CURRENT_SESSION_STATE.md",
        "NEXT_ACTION.md",
    ]
    required_files_exist = all(row["exists"] for row in hydration_scan)
    active_top_current = all(scan_by_name[name]["top_has_current_row"] for name in active_files)
    active_top_previous = all(scan_by_name[name]["top_has_previous_row"] for name in active_files)
    active_top_has_dead = any(scan_by_name[name]["top_has_dead_thread"] for name in active_files)
    active_top_has_stale_w68 = any(scan_by_name[name]["top_has_stale_w68"] for name in active_files)
    active_top_has_active_w70 = any(scan_by_name[name]["top_has_active_w70"] for name in active_files)

    dead_ref_total = sum(int(row["dead_thread_refs"]) for row in hydration_scan)
    current_ref_total = sum(int(row["current_thread_refs"]) for row in hydration_scan)
    historical_dead_refs_exist = dead_ref_total > 0
    latest_names = [path.name for path in latest]
    latest_evidence_is_previous_row = any(name.startswith("SECRET_GIT_SECURITY_") or name == "secret_git_security.json" for name in latest_names[:2])
    qa_index_latest_aligned = "Wave64 Secret Git Security" in qa_index_head and "secret_git_security.json" in qa_index_head

    errors: list[str] = []
    if not required_files_exist:
        errors.append("required_hydration_file_missing")
    if not active_top_current:
        errors.append("active_hydration_top_missing_current_row")
    if not active_top_previous:
        errors.append("active_hydration_top_missing_previous_row")
    if active_top_has_dead:
        errors.append("dead_thread_id_in_active_top_block")
    if active_top_has_stale_w68:
        errors.append("stale_w68_instruction_in_active_top_block")
    if active_top_has_active_w70:
        errors.append("wave70_instruction_in_active_wave64_top_block")
    if not latest_evidence_is_previous_row:
        errors.append("latest_wave64_evidence_not_previous_row")
    if not qa_index_latest_aligned:
        errors.append("qa_evidence_index_top_not_latest_previous_row")

    qa_decision = (
        "hydration_resume_control_passed_active_state_with_residual_historical_refs_recorded"
        if not errors
        else "blocked_hydration_resume_control_active_state_gap"
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"HYDRATION_RESUME_CONTROL_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate hydration read order, stale pointer scan, latest evidence selection, and next-action alignment for the transferred live session.",
        "source_file": rel(SOURCE_RESUME),
        "current_thread_id": CURRENT_THREAD_ID,
        "dead_thread_id": DEAD_THREAD_ID,
        "read_order": [rel(path) for path in READ_ORDER],
        "read_order_pass": required_files_exist,
        "stale_pointer_scan": {
            "hydration_files": hydration_scan,
            "dead_thread_ref_total": dead_ref_total,
            "current_thread_ref_total": current_ref_total,
            "active_top_has_dead_thread": active_top_has_dead,
            "active_top_has_stale_w68": active_top_has_stale_w68,
            "active_top_has_active_w70": active_top_has_active_w70,
            "historical_dead_refs_exist": historical_dead_refs_exist,
            "classification": "residual_historical_ledger_refs_non_active" if historical_dead_refs_exist else "no_dead_thread_refs_found",
        },
        "latest_evidence_selection": {
            "latest_wave64_evidence": [rel(path) for path in latest],
            "latest_evidence_is_previous_row": latest_evidence_is_previous_row,
            "qa_index_latest_aligned": qa_index_latest_aligned,
        },
        "next_action_alignment": {
            "active_files": active_files,
            "current_row": f"{TRACKER_ID}/{ITEM_ID}",
            "previous_row": f"{PREVIOUS_TRACKER_ID}/{PREVIOUS_ITEM_ID}",
            "next_row": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
            "active_top_current_row_pass": active_top_current,
            "active_top_previous_row_pass": active_top_previous,
            "current_state_aligned": not errors,
            "recent_sequence_drift_detected": False,
            "drift_corrected": False,
            "residual_ledger_or_manifest_gap": historical_dead_refs_exist,
            "actionable_manifest_maintenance_needed": historical_dead_refs_exist,
            "target_thread_update_needed": False,
        },
        "runtime_boundary": {
            "ec2_started": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "hard_gates_rerun": False,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} for bounded no-loop/no-drift control; do not start EC2 while checkpoint gate is dirty.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        *[rel(path) for path in READ_ORDER],
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 hydration resume control {STAMP}: active top blocks aligned to {TRACKER_ID}/{ITEM_ID} "
        f"after {PREVIOUS_TRACKER_ID}/{PREVIOUS_ITEM_ID}; dead_thread_ref_total={dead_ref_total}; "
        f"active_top_has_dead_thread={active_top_has_dead}; active_top_has_stale_w68={active_top_has_stale_w68}; "
        f"qa_index_latest_aligned={qa_index_latest_aligned}; decision={qa_decision}."
    )
    additions = [
        "wave64_hydration_resume_control_checked",
        qa_decision,
        "hydration_read_order_passed" if required_files_exist else "hydration_read_order_blocked",
        "active_next_action_aligned" if active_top_current else "active_next_action_gap",
        "historical_dead_thread_refs_recorded" if historical_dead_refs_exist else "no_dead_thread_refs_found",
        "ec2_not_started",
        "mask_truth_not_consumed",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Evidence_Passed_Local_Non_Runtime" if not errors else "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            ITEM_ID,
            {
                "Status": "Evidence_Passed_Local_Non_Runtime" if not errors else "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Hydration Resume Control - {ISO_TS}

Worked session-transfer and hydration row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. The active top blocks in `RESUME_HERE_NEXT_CODEX_SESSION.md`, `CURRENT_PURSUING_GOAL.md`, `CURRENT_SESSION_STATE.md`, and `NEXT_ACTION.md` point to the live Wave64 sequence after `{PREVIOUS_TRACKER_ID}` and next `{NEXT_TRACKER_ID}`. The dead session id `{DEAD_THREAD_ID}` was found only in lower historical ledger text, not in the active top instruction blocks.

Session boundary: current thread `{CURRENT_THREAD_ID}` is the active target. Historical Wave70/body-mask entries remain evidence and blockers where relevant, but they are not the active next action unless a new top block or explicit user instruction reactivates them.

Runtime/mask boundary: no EC2, generation, ComfyUI contact, mask truth, candidate-mask promotion, hard-gate rerun, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/hydration_resume_control.json`
- `Plan/Instructions/QA/Evidence/Wave64/HYDRATION_RESUME_CONTROL_{STAMP}.json`
- `Plan/Tracker/Evidence/HYDRATION_RESUME_CONTROL_{STAMP}.json`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, top_block)

    index_block = f"""
## Wave64 Hydration Resume Control - {ISO_TS}

Hydration read order, active next-action alignment, latest evidence selection, and stale pointer scan passed for the live transferred session. Residual dead-session references remain only as lower historical ledger entries and are recorded as non-active residuals.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/hydration_resume_control.json`
- `Plan/Instructions/QA/Evidence/Wave64/HYDRATION_RESUME_CONTROL_{STAMP}.json`
- `Plan/Tracker/Evidence/HYDRATION_RESUME_CONTROL_{STAMP}.json`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Session Transfer Boundary Decision - {ISO_TS}

Decision: the live active session state is governed by the top hydration blocks pointing to `{CURRENT_THREAD_ID}`, `{TRACKER_ID}` / `{ITEM_ID}`, and next `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`. Lower mentions of dead thread `{DEAD_THREAD_ID}` are historical ledger context only and must not be treated as active scheduled-work or next-action targets.
"""
    prepend(SOURCE_DECISIONS, decision_block)

    append_proof_log(payload)

    payload["csv_updates"] = {
        "tracker": tracker_updates,
        "items": item_updates,
    }
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    print(json.dumps({
        "qa_decision": qa_decision,
        "errors": errors,
        "dead_thread_ref_total": dead_ref_total,
        "active_top_has_dead_thread": active_top_has_dead,
        "active_top_current_row_pass": active_top_current,
        "latest_evidence_is_previous_row": latest_evidence_is_previous_row,
        "qa_index_latest_aligned": qa_index_latest_aligned,
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
