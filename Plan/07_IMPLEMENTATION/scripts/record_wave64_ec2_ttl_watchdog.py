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

TRACKER_ID = "TRK-W64-042"
ITEM_ID = "ITEM-W64-042"
NEXT_TRACKER_ID = "TRK-W64-043"
NEXT_ITEM_ID = "ITEM-W64-043"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
RUNTIME_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"

AUTH_GATE = max(RUNTIME_DIR.glob("W64_AWS_AUTH_GATE_EC2_TTL_WATCHDOG_*.json"), key=lambda path: path.stat().st_mtime)
EMERGENCY_STOP = max(RUNTIME_DIR.glob("W64_EC2_EMERGENCY_STOP_SCHEDULE_DRY_RUN_*.json"), key=lambda path: path.stat().st_mtime)
WATCHDOG = max(RUNTIME_DIR.glob("W64_EC2_INSTANCE_WATCHDOG_DRY_RUN_*.json"), key=lambda path: path.stat().st_mtime)

SOURCE_EMERGENCY_STOP = PLAN_ROOT / "Instructions/Operations/Scripts/New-EC2EmergencyStopSchedule.ps1"
SOURCE_WATCHDOG = PLAN_ROOT / "Instructions/Operations/Scripts/Start-EC2InstanceStopWatchdog.ps1"
SOURCE_AUTH_GATE = PLAN_ROOT / "Instructions/Operations/Scripts/Test-AwsAuthGate.ps1"
SOURCE_RUNBOOK = PLAN_ROOT / "Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md"

EVIDENCE = QA_DIR / "ec2_ttl_watchdog.json"
STAMPED_EVIDENCE = QA_DIR / f"EC2_TTL_WATCHDOG_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"EC2_TTL_WATCHDOG_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
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


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded EC2 TTL watchdog dry-run controls and exact live-proof blocker.",
        "; ".join(payload["evidence_paths"]),
        "AWS auth gate; EventBridge emergency stop dry-run; instance watchdog dry-run; max runtime; final stopped proof boundary",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Resolve AWS auth before any live schedule/watchdog/final-state proof; then continue {NEXT_TRACKER_ID} if appropriate.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    auth = read_json(AUTH_GATE)
    emergency = read_json(EMERGENCY_STOP)
    watchdog = read_json(WATCHDOG)

    errors: list[str] = []
    if emergency.get("result") != "dry_run_emergency_stop_schedule_plan":
        errors.append(f"emergency_stop_dry_run_unexpected:{emergency.get('result')}")
    if emergency.get("stop_after_minutes") is None or int(emergency.get("stop_after_minutes")) <= 0:
        errors.append("emergency_stop_missing_positive_ttl")
    if emergency.get("scheduler_role_arn_supplied") is not True:
        errors.append("scheduler_role_arn_not_supplied")
    if emergency.get("execute") is not False:
        errors.append("emergency_stop_executed_unexpectedly")
    if emergency.get("aws_contacted") is not False:
        errors.append("emergency_stop_contacted_aws_unexpectedly")
    if watchdog.get("result") != "dry_run_instance_watchdog_plan":
        errors.append(f"watchdog_dry_run_unexpected:{watchdog.get('result')}")
    if watchdog.get("stop_after_minutes") is None or int(watchdog.get("stop_after_minutes")) <= 0:
        errors.append("watchdog_missing_positive_ttl")
    if watchdog.get("execute") is not False:
        errors.append("watchdog_executed_unexpectedly")
    if watchdog.get("aws_contacted") is not False:
        errors.append("watchdog_contacted_aws_unexpectedly")
    if auth.get("safe_to_start_ec2") is not False:
        errors.append("auth_gate_unexpectedly_safe_to_start_ec2")
    if auth.get("secrets_printed") is not False:
        errors.append("auth_gate_printed_secret_unexpectedly")

    qa_decision = (
        "blocked_ec2_ttl_watchdog_live_proof_expired_aws_session"
        if not errors
        else "invalid_ec2_ttl_watchdog_evidence_record"
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"EC2_TTL_WATCHDOG_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate EC2 TTL watchdog and emergency stop controls without starting EC2.",
        "source_runbook": rel(SOURCE_RUNBOOK),
        "source_scripts": [
            rel(SOURCE_EMERGENCY_STOP),
            rel(SOURCE_WATCHDOG),
            rel(SOURCE_AUTH_GATE),
        ],
        "aws_auth_gate": {
            "path": evidence_path(AUTH_GATE),
            "result": auth.get("result"),
            "failure_category": auth.get("failure_category"),
            "safe_to_start_ec2": auth.get("safe_to_start_ec2"),
            "generation_allowed": auth.get("generation_allowed"),
            "secrets_printed": auth.get("secrets_printed"),
            "auth_url_recorded": auth.get("auth_url_recorded"),
        },
        "cloud_side_emergency_stop": {
            "path": evidence_path(EMERGENCY_STOP),
            "result": emergency.get("result"),
            "stop_after_minutes": emergency.get("stop_after_minutes"),
            "scheduler_role_arn_supplied": emergency.get("scheduler_role_arn_supplied"),
            "execute": emergency.get("execute"),
            "aws_contacted": emergency.get("aws_contacted"),
            "ec2_started": emergency.get("ec2_started"),
            "schedule_expression_present": bool(emergency.get("schedule_expression")),
            "action_after_completion": emergency.get("action_after_completion"),
        },
        "instance_side_watchdog": {
            "path": evidence_path(WATCHDOG),
            "result": watchdog.get("result"),
            "stop_after_minutes": watchdog.get("stop_after_minutes"),
            "execute": watchdog.get("execute"),
            "aws_contacted": watchdog.get("aws_contacted"),
            "ec2_started": watchdog.get("ec2_started"),
            "command_status": watchdog.get("command_status"),
            "allow_os_shutdown_fallback": watchdog.get("allow_os_shutdown_fallback"),
        },
        "live_runtime_boundary": {
            "max_runtime_required": True,
            "cloud_side_schedule_created": False,
            "instance_watchdog_started": False,
            "final_state_stopped_verified": False,
            "blocked_reason": "AWS auth gate is blocked_expired_session, so no live schedule, watchdog, EC2 start, or final-state query was attempted.",
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Do not start EC2. Resolve AWS auth before any live TTL/watchdog/final-state proof; continue only with non-EC2-safe portions of {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(AUTH_GATE),
        evidence_path(EMERGENCY_STOP),
        evidence_path(WATCHDOG),
        rel(SOURCE_EMERGENCY_STOP),
        rel(SOURCE_WATCHDOG),
        rel(SOURCE_AUTH_GATE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 EC2 TTL watchdog {STAMP}: emergency_stop={emergency.get('result')} "
        f"ttl={emergency.get('stop_after_minutes')} scheduler_role_supplied={emergency.get('scheduler_role_arn_supplied')}; "
        f"watchdog={watchdog.get('result')} ttl={watchdog.get('stop_after_minutes')}; "
        f"auth={auth.get('result')}/{auth.get('failure_category')}; live_final_state_stopped_verified=False; "
        f"ec2_started=False; decision={qa_decision}."
    )
    additions = [
        "wave64_ec2_ttl_watchdog_checked",
        qa_decision,
        "emergency_stop_dry_run_planned",
        "instance_watchdog_dry_run_planned",
        "max_runtime_required",
        "final_state_stopped_live_proof_blocked",
        "ec2_not_started",
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
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 EC2 TTL Watchdog - {ISO_TS}

Worked EC2-safety row `{TRACKER_ID}` / `{ITEM_ID}` without starting EC2 or contacting AWS.

Result: `{qa_decision}`. Cloud-side emergency stop dry-run result `{emergency.get('result')}` with stop_after_minutes=`{emergency.get('stop_after_minutes')}` and scheduler_role_arn_supplied=`{emergency.get('scheduler_role_arn_supplied')}`. Instance-side watchdog dry-run result `{watchdog.get('result')}` with stop_after_minutes=`{watchdog.get('stop_after_minutes')}`.

Live blocker: AWS auth gate is `{auth.get('result')}` / `{auth.get('failure_category')}`. Therefore no live EventBridge schedule, SSM watchdog command, EC2 start, generation, or final-state `stopped` verification was attempted.

Boundary: do not start EC2 until AWS auth and checkpoint gates are clean. No masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(AUTH_GATE)}`
- `{evidence_path(EMERGENCY_STOP)}`
- `{evidence_path(WATCHDOG)}`

Next exact local action: continue only non-EC2-safe portions of `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` or another non-EC2 row while AWS auth remains expired.
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
## Wave64 EC2 TTL Watchdog - {ISO_TS}

EC2 TTL/watchdog row: dry-run emergency stop and instance watchdog plans exist; live proof blocked by expired AWS auth. No EC2 start.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(AUTH_GATE)}`
- `{evidence_path(EMERGENCY_STOP)}`
- `{evidence_path(WATCHDOG)}`
""",
    )
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "stamped_evidence": str(STAMPED_EVIDENCE),
                "tracker_evidence": str(TRACKER_EVIDENCE),
                "qa_decision": qa_decision,
                "errors": errors,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
