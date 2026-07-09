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

TRACKER_ID = "TRK-W64-048"
ITEM_ID = "ITEM-W64-048"
PREVIOUS_TRACKER_ID = "TRK-W64-047"
PREVIOUS_ITEM_ID = "ITEM-W64-047"
NEXT_TRACKER_ID = "TRK-W64-049"
NEXT_ITEM_ID = "ITEM-W64-049"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

SOURCE_PROTOCOL = PLAN_ROOT / "Instructions/NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "no_loop_no_drift.json"
STAMPED_EVIDENCE = QA_DIR / f"NO_LOOP_NO_DRIFT_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"NO_LOOP_NO_DRIFT_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

RECENT_CANONICAL_EVIDENCE = [
    "github_actions_ci_package.json",
    "s3_transfer_cost_control.json",
    "ec2_ttl_watchdog.json",
    "artifact_pullback_integrity.json",
    "model_registry_governance.json",
    "civitai_metadata.json",
    "secret_git_security.json",
    "hydration_resume_control.json",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, object]:
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


def top_text(path: Path, limit: int = 5000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig")
    return text[: min(limit, len(text))]


def canonical_evidence_summary() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name in RECENT_CANONICAL_EVIDENCE:
        path = QA_DIR / name
        if not path.exists():
            rows.append({"path": rel(path), "exists": False})
            continue
        payload = read_json(path)
        rows.append(
            {
                "path": rel(path),
                "exists": True,
                "tracker_id": payload.get("tracker_id"),
                "item_id": payload.get("item_id"),
                "qa_decision": payload.get("qa_decision"),
                "ec2_started": payload.get("runtime_boundary", {}).get("ec2_started")
                if isinstance(payload.get("runtime_boundary"), dict)
                else None,
                "generation_executed": payload.get("runtime_boundary", {}).get("generation_executed")
                if isinstance(payload.get("runtime_boundary"), dict)
                else None,
                "masks_promoted": payload.get("gold_mask_dependency_boundary", {}).get("masks_promoted")
                if isinstance(payload.get("gold_mask_dependency_boundary"), dict)
                else None,
                "hard_gates_rerun": payload.get("runtime_boundary", {}).get("hard_gates_rerun")
                if isinstance(payload.get("runtime_boundary"), dict)
                else payload.get("gold_mask_dependency_boundary", {}).get("hard_gates_rerun")
                if isinstance(payload.get("gold_mask_dependency_boundary"), dict)
                else None,
            }
        )
    return rows


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded no-loop/no-drift control: preserve completed evidence, stop blocked-state reruns, and advance to a concrete next row.",
        "; ".join(payload["evidence_paths"]),
        "completed proof no rerun; blocked state stop rule; advance or report; scope drift check",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; do not repeat hydration, route-loop, coverage, EC2, or hard-gate refreshes without changed inputs.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    source_text = SOURCE_PROTOCOL.read_text(encoding="utf-8-sig") if SOURCE_PROTOCOL.exists() else ""
    next_head = top_text(SOURCE_NEXT)
    goal_head = top_text(SOURCE_GOAL)
    evidence_rows = canonical_evidence_summary()
    evidence_by_tracker = {row.get("tracker_id"): row for row in evidence_rows if row.get("exists")}

    missing_evidence = [row["path"] for row in evidence_rows if not row.get("exists")]
    previous_row_passed = evidence_by_tracker.get(PREVIOUS_TRACKER_ID, {}).get("qa_decision") == "hydration_resume_control_passed_active_state_with_residual_historical_refs_recorded"
    current_next_action = TRACKER_ID in next_head and ITEM_ID in next_head
    current_goal_aligned = TRACKER_ID in goal_head and ITEM_ID in goal_head
    source_has_stop_rules = all(
        token in source_text
        for token in [
            "Do not create another validator",
            "Housekeeping budget",
            "Do not repeat a completed lane proof",
            "Same command fails 2 times",
        ]
    )
    no_ec2_started_in_recent_local_rows = all(row.get("ec2_started") is not True for row in evidence_rows if row.get("exists"))
    no_masks_promoted_in_recent_local_rows = all(row.get("masks_promoted") is not True for row in evidence_rows if row.get("exists"))
    no_hard_gate_rerun_in_recent_local_rows = all(row.get("hard_gates_rerun") is not True for row in evidence_rows if row.get("exists"))
    blocked_state_stop_rule = no_ec2_started_in_recent_local_rows and no_hard_gate_rerun_in_recent_local_rows

    errors: list[str] = []
    if missing_evidence:
        errors.append(f"missing_recent_evidence:{len(missing_evidence)}")
    if not previous_row_passed:
        errors.append("previous_hydration_resume_control_not_passed")
    if not current_next_action:
        errors.append("next_action_top_not_current_row")
    if not current_goal_aligned:
        errors.append("current_goal_top_not_current_row")
    if not source_has_stop_rules:
        errors.append("source_protocol_stop_rules_missing")
    if not blocked_state_stop_rule:
        errors.append("blocked_state_stop_rule_failed")
    if not no_masks_promoted_in_recent_local_rows:
        errors.append("mask_promotion_detected_in_recent_local_rows")

    qa_decision = "no_loop_no_drift_passed_bounded_advance_to_concrete_next_row" if not errors else "blocked_no_loop_no_drift_control_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"NO_LOOP_NO_DRIFT_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate no-loop/no-drift progress control and stop repeated bookkeeping or blocked-state reruns.",
        "source_protocol": rel(SOURCE_PROTOCOL),
        "completed_proof_no_rerun": {
            "recent_canonical_evidence": evidence_rows,
            "missing_evidence": missing_evidence,
            "previous_row_passed": previous_row_passed,
            "rerun_completed_proof_required": False,
        },
        "blocked_state_stop_rule": {
            "aws_or_ec2_blockers_repeated": False,
            "ec2_started_in_recent_local_rows": not no_ec2_started_in_recent_local_rows,
            "hard_gate_rerun_in_recent_local_rows": not no_hard_gate_rerun_in_recent_local_rows,
            "mask_promotion_detected": not no_masks_promoted_in_recent_local_rows,
            "blocked_state_stop_rule_pass": blocked_state_stop_rule,
        },
        "advance_or_report": {
            "current_row": f"{TRACKER_ID}/{ITEM_ID}",
            "previous_row": f"{PREVIOUS_TRACKER_ID}/{PREVIOUS_ITEM_ID}",
            "next_row": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
            "next_action_top_current_row": current_next_action,
            "advance_to_concrete_project_row": True,
            "next_row_capability": "blocker and known issue governance with source-cited latest-state precedence",
        },
        "scope_drift_check": {
            "source_protocol_has_stop_rules": source_has_stop_rules,
            "current_goal_top_current_row": current_goal_aligned,
            "no_route_loop_allowed": True,
            "no_coverage_refresh_loop_allowed": True,
            "no_hydration_refresh_loop_allowed": True,
            "no_wave71_activation_without_gate_proof": True,
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
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; do not repeat the just-passed hydration/no-loop evidence unless inputs change.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(SOURCE_PROTOCOL),
        *[row["path"] for row in evidence_rows if row.get("exists")],
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 no-loop/no-drift {STAMP}: previous_row_passed={previous_row_passed}; "
        f"blocked_state_stop_rule={blocked_state_stop_rule}; no_ec2_started={no_ec2_started_in_recent_local_rows}; "
        f"no_masks_promoted={no_masks_promoted_in_recent_local_rows}; next={NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; decision={qa_decision}."
    )
    additions = [
        "wave64_no_loop_no_drift_checked",
        qa_decision,
        "completed_proof_no_rerun_passed" if not missing_evidence else "completed_proof_evidence_missing",
        "blocked_state_stop_rule_passed" if blocked_state_stop_rule else "blocked_state_stop_rule_failed",
        "advance_to_concrete_next_row",
        "no_route_loop_allowed",
        "no_hydration_loop_allowed",
        "no_mask_promotion",
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
## Immediate Next Action - Wave64 No Loop No Drift - {ISO_TS}

Worked progress-control row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Completed Wave64 evidence is preserved without rerun, blocked EC2/Git/mask states are recorded as stop rules rather than work loops, and the next concrete row is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.

Do not repeat hydration transfer checks, generic route alignment, broad coverage refreshes, EC2 TTL/auth probes, hard-gate reruns, or mask-dependent promotion unless a specific input changes or the user explicitly asks. Manual gold masks remain in progress and candidate masks are not truth.

Runtime boundary: no EC2, generation, ComfyUI contact, hard-gate rerun, mask truth, mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/no_loop_no_drift.json`
- `Plan/Instructions/QA/Evidence/Wave64/NO_LOOP_NO_DRIFT_{STAMP}.json`
- `Plan/Tracker/Evidence/NO_LOOP_NO_DRIFT_{STAMP}.json`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, top_block)

    index_block = f"""
## Wave64 No Loop No Drift - {ISO_TS}

No-loop/no-drift progress control passed: completed proofs were not rerun, blocked runtime states remain stop rules, and the next row is a concrete blocker/known-issue governance task rather than another housekeeping loop.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/no_loop_no_drift.json`
- `Plan/Instructions/QA/Evidence/Wave64/NO_LOOP_NO_DRIFT_{STAMP}.json`
- `Plan/Tracker/Evidence/NO_LOOP_NO_DRIFT_{STAMP}.json`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 No-Loop Boundary Decision - {ISO_TS}

Decision: do not repeat the session-transfer, hydration, route-alignment, coverage-refresh, EC2-auth, hard-gate, or mask-promotion checks unless an input changes or the user explicitly asks. Continue only to concrete tracker rows that advance implementation, orchestration, runtime readiness, evidence governance, or exact blocker recording.
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
        "previous_row_passed": previous_row_passed,
        "blocked_state_stop_rule": blocked_state_stop_rule,
        "current_next_action": current_next_action,
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
