from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

EVIDENCE = QA_DIR / "project_control_autonomy.json"
STAMPED_EVIDENCE = QA_DIR / f"PROJECT_CONTROL_AUTONOMY_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"PROJECT_CONTROL_AUTONOMY_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

TRACKER_ID = "TRK-W64-002"
ITEM_ID = "ITEM-W64-002"

CONTROL_SOURCES = {
    "operating_manual": {
        "path": PLAN_ROOT / "00_PROJECT_CONTROL/AI_PROJECT_MANAGER_OPERATING_MANUAL.md",
        "tokens": [
            "Build the ultimate modular hyper-realism generation system",
            "Use QA gates as blockers",
            "Every result must be reproducible from manifests",
            "Do not claim runtime proof unless actual outputs exist",
        ],
    },
    "autonomous_master_manual": {
        "path": PLAN_ROOT / "Instructions/AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md",
        "tokens": [
            "Do not mark any item complete without proof",
            "Do not drift from the selected wave or active task",
            "Do not loop on the same failed fix",
            "Do not start the EC2 GPU instance unless the selected task requires GPU/runtime proof",
            "Record the evidence chain",
        ],
    },
    "decision_recovery_protocol": {
        "path": PLAN_ROOT / "Instructions/AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL.md",
        "tokens": [
            "diagnose, record evidence, recover safely",
            "Classify the failure",
            "Update pursuing goal",
            "Update tracker/issue log",
        ],
    },
    "no_loop_no_drift": {
        "path": PLAN_ROOT / "Instructions/NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md",
        "tokens": [
            "Progress exists only when",
            "Loop detection rules",
            "Drift detection rules",
            "Proof of forward movement",
        ],
    },
    "done_gate": {
        "path": PLAN_ROOT / "Instructions/COMPLETION_DEFINITION_AND_DONE_GATE.md",
        "tokens": [
            "Only Level 7 equals complete",
            "Universal done gate",
            "Gold-standard mask dependency gate",
            "Missing or not-yet-validated manual gold masks block only",
        ],
    },
    "session_start_rehydration": {
        "path": HYDRATION_DIR / "SESSION_START_REHYDRATION_CHECKLIST.md",
        "tokens": [
            "Read the latest resume file first",
            "Read active state files",
            "Inspect Items and Tracker",
            "Decide the next highest-value task",
        ],
    },
    "tracker_update_protocol": {
        "path": HYDRATION_DIR / "TRACKER_UPDATE_PROTOCOL.md",
        "tokens": [
            "Update the tracker whenever Codex",
            "Do not use `complete` unless done certification exists",
            "Every tracker update that claims progress must include at least one evidence path",
        ],
    },
    "itemized_list_update_protocol": {
        "path": HYDRATION_DIR / "ITEMIZED_LIST_UPDATE_PROTOCOL.md",
        "tokens": [
            "Update itemized list records whenever Codex creates or changes",
            "must point to the concrete evidence file or folder",
            "must not say an item is fully complete unless",
        ],
    },
    "gold_mask_dependency_gate": {
        "path": PLAN_ROOT / "Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md",
        "tokens": [
            "scoped dependency gate",
            "Work That May Continue",
            "Do not consume guarded in-progress folders",
            "Continue unrelated non-mask work",
        ],
    },
}

HYDRATION_STATE_FILES = [
    "RESUME_HERE_NEXT_CODEX_SESSION.md",
    "CURRENT_SESSION_STATE.md",
    "CURRENT_PURSUING_GOAL.md",
    "NEXT_ACTION.md",
    "KNOWN_ISSUES.md",
    "BLOCKERS.md",
    "QA_EVIDENCE_INDEX.md",
    "RECENT_DECISIONS.md",
    "PROOF_OF_MOVEMENT_LOG.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def source_check(name: str, spec: dict[str, object]) -> dict[str, object]:
    path = spec["path"]
    assert isinstance(path, Path)
    text = read_text(path)
    tokens = [str(token) for token in spec["tokens"]]
    missing = [token for token in tokens if token not in text]
    return {
        "name": name,
        "path": rel(path) if path.exists() else str(path),
        "exists": path.exists(),
        "token_count": len(tokens),
        "missing_tokens": missing,
        "pass": path.exists() and not missing,
    }


def csv_row_exists(path: Path, key: str, value: str) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return any(row.get(key) == value for row in csv.DictReader(f))


def hydration_state() -> dict[str, object]:
    files = []
    for name in HYDRATION_STATE_FILES:
        path = HYDRATION_DIR / name
        files.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return {
        "all_required_files_exist": all(item["exists"] for item in files),
        "files": files,
    }


def top_text(path: Path, line_count: int = 40) -> str:
    text = read_text(path)
    return "\n".join(text.splitlines()[:line_count])


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


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Audited autonomous project manager operating controls for objective, no-loop, blocker, checkpoint, evidence, tracker/item, and continuation behavior.",
        "; ".join(payload["evidence_paths"]),
        "source token checks; hydration file existence; tracker/item row existence; non-mask boundary check; JSON evidence; row update",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Advance to TRK-W64-003 current system review evidence.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    source_results = [source_check(name, spec) for name, spec in CONTROL_SOURCES.items()]
    hydration = hydration_state()
    tracker_row_present = all(csv_row_exists(path, "Tracker_ID", TRACKER_ID) for path in TRACKER_FILES)
    item_row_present = all(csv_row_exists(path, "Item_ID", ITEM_ID) for path in ITEM_FILES)
    next_action_top = top_text(HYDRATION_DIR / "NEXT_ACTION.md")
    current_goal_top = top_text(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md")
    state_mentions_nonmask_boundary = "Gold-mask boundary" in next_action_top or "Gold Mask Dependency Boundary" in current_goal_top
    all_pass = (
        all(result["pass"] for result in source_results)
        and hydration["all_required_files_exist"]
        and tracker_row_present
        and item_row_present
        and state_mentions_nonmask_boundary
    )
    qa_decision = (
        "project_control_autonomy_passed_nonmask_safe"
        if all_pass
        else "blocked_project_control_autonomy_missing_control_evidence"
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"PROJECT_CONTROL_AUTONOMY_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Audit autonomous project manager controls for objective, no-loop, blocker, checkpoint, evidence, tracker/item, and continuation behavior.",
        "source_results": source_results,
        "hydration_state": hydration,
        "row_state": {
            "tracker_row_present": tracker_row_present,
            "item_row_present": item_row_present,
            "tracker_files": [rel(path) for path in TRACKER_FILES],
            "item_files": [rel(path) for path in ITEM_FILES],
        },
        "current_posture": {
            "state_mentions_nonmask_boundary": state_mentions_nonmask_boundary,
            "next_action_top": next_action_top,
            "current_goal_top": current_goal_top,
        },
        "gold_mask_dependency_boundary": {
            "manual_gold_masks_are_scoped_dependency": True,
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "qa_decision": qa_decision,
        "completion_claim": "not_complete_certified_without_done_certification",
        "next_step": "Advance to TRK-W64-003 current system review evidence if this audit passes.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
    ]
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 project control autonomy audit {STAMP}: source control protocols, hydration files, tracker/item rows, "
        f"and scoped gold-mask boundary checked. Decision={qa_decision}. No mask truth consumed, no masks promoted, "
        "no hard gates rerun, no Wave71 activation attempted."
    )
    coverage_additions = [
        "wave64_project_control_autonomy_audited",
        qa_decision,
        "allowed_nonmask_work_can_continue",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": coverage_additions,
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
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Project Control Autonomy Audit - {ISO_TS}

Worked the next explicit non-mask-safe task: `{TRACKER_ID}` / `{ITEM_ID}` autonomous project manager operating controls.

Result: checked `{len(source_results)}` control source files, hydration state files, tracker/item row presence, proof/evidence machinery, and scoped gold-mask boundary posture. Decision: `{qa_decision}`.

Gold-mask boundary: this audit did not consume candidate masks as truth, did not promote masks, did not rerun hard gates, and did not activate Wave71+. Missing manual gold masks remain scoped only to mask-dependent rows/gates.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`

Next exact local action: advance to `TRK-W64-003` current system review evidence, still staying outside mask-truth work until the user says manual masks are ready.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"""
## Wave64 Project Control Autonomy Audit - {ISO_TS}

Autonomous operating controls audited for `{TRACKER_ID}` / `{ITEM_ID}` without consuming mask truth.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
""",
    )
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "qa_decision": qa_decision,
        "source_checks": len(source_results),
        "source_checks_passed": sum(1 for result in source_results if result["pass"]),
        "hydration_files_pass": hydration["all_required_files_exist"],
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
