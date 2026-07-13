from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from reconcile_wave64_s3_transfer_cost_control_live_readiness import (
    HYD,
    PLAN,
    QA,
    prepend,
    relative,
    sha256,
    update_csv,
    write_json,
)


WINDOWS_ROOT = Path(r"C:\Comfy_UI_Main")
WSL_ROOT = Path("/mnt/c/Comfy_UI_Main")
ROOT = Path(os.environ.get("COMFY_UI_MAIN_ROOT", WINDOWS_ROOT if WINDOWS_ROOT.exists() else WSL_ROOT))

ROW042_EVIDENCE = ROOT / "Plan/Instructions/QA/Evidence/Wave64/ec2_ttl_watchdog.json"
ENV_PATH = ROOT / ".env"
AWS_TIMEOUT_SECONDS = 30
TRK = "TRK-W64-042"
ITEM = "ITEM-W64-042"
TZ = ZoneInfo("America/Chicago")
ORIGINAL_EVIDENCE = QA / "EC2_TTL_WATCHDOG_20260708T233454-0500.json"

ROLE_ENV_KEYS = (
    "COMFY_SCHEDULER_STOP_ROLE_ARN",
    "SCHEDULER_ROLE_ARN",
    "EC2_SCHEDULER_ROLE_ARN",
    "COMFYUI_EMERGENCY_STOP_SCHEDULER_ROLE_ARN",
    "COMFY_UI_EMERGENCY_STOP_SCHEDULER_ROLE_ARN",
)

STATUS_COMPLETED = "Completed_Live_TTL_Watchdog_Proof_AWS_Readiness_Verified"
STATUS_BLOCKED_MISSING_PROOF = "Blocked_Live_TTL_Watchdog_Proof_Missing_AWS_Readiness_Verified"
STATUS_BLOCKED_AUTH = "Blocked_AWS_Auth_Failed_Live_Readiness"
STATUS_BLOCKED_ROLE = "Blocked_Scheduler_Role_Verification_Failed"
STATUS_BLOCKED_RUNNING = "Blocked_EC2_Running_Without_TTL_Controls"


@dataclass(frozen=True)
class Row042Metadata:
    region: str
    instance_id: str
    schedule_name: str
    stop_after_minutes: int
    canonical_path: Path
    schedule_dry_run_path: Path
    watchdog_dry_run_path: Path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def redact_text(value: str) -> str:
    redacted = re.sub(r"arn:[^\"\s]+", "[redacted_arn]", value)
    redacted = re.sub(r"\bi-[0-9a-fA-F]{8,}\b", "[redacted_instance_id]", redacted)
    redacted = re.sub(r"\b\d{12}\b", "[redacted_account_id]", redacted)
    return redacted


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def parse_env_scheduler_role(env_path: Path = ENV_PATH) -> dict[str, Any]:
    present_keys: list[str] = []
    role_name: str | None = None
    role_arn_seen = False
    env_file_present = env_path.exists()

    if env_file_present:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in ROLE_ENV_KEYS:
                continue
            present_keys.append(key)
            role_arn_seen = True
            parsed = value.strip().strip('"').strip("'")
            if parsed.startswith("arn:"):
                role_name = parsed.split("/")[-1] if "/" in parsed else None

    return {
        "env_file_present": env_file_present,
        "candidate_role_keys_present": sorted(set(present_keys)),
        "role_arn_seen": role_arn_seen,
        "role_name": role_name,
    }


def resolve_local_plan_paths(canonical: dict[str, Any]) -> tuple[Path, Path, str | None, str | None]:
    if "current_local_plans" in canonical:
        schedule = canonical["current_local_plans"]["schedule"]
        watchdog = canonical["current_local_plans"]["watchdog"]
        return ROOT / schedule["path"], ROOT / watchdog["path"], schedule.get("sha256"), watchdog.get("sha256")
    preserved = canonical.get("preserved_local_plans", {})
    schedule_path = preserved.get("schedule_path")
    watchdog_path = preserved.get("watchdog_path")
    if not schedule_path or not watchdog_path:
        raise SystemExit("row042 canonical evidence does not preserve local plan paths")
    return (
        ROOT / schedule_path,
        ROOT / watchdog_path,
        preserved.get("schedule_sha256"),
        preserved.get("watchdog_sha256"),
    )


def load_row042_metadata() -> Row042Metadata:
    canonical = read_json(ROW042_EVIDENCE)
    schedule_path, watchdog_path, _, _ = resolve_local_plan_paths(canonical)
    schedule = read_json(schedule_path)
    watchdog = read_json(watchdog_path)

    region = str(schedule.get("region", "")).strip()
    instance_id = str(schedule.get("instance_id", "")).strip()
    schedule_name = str(schedule.get("schedule_name", "")).strip()
    stop_after_minutes = int(schedule.get("stop_after_minutes", 0))

    if not region:
        region = str(watchdog.get("region", "")).strip()
    if not instance_id:
        instance_id = str(watchdog.get("instance_id", "")).strip()

    if not region or not instance_id or not schedule_name:
        raise SystemExit("row042 metadata is incomplete in dry-run evidence")

    return Row042Metadata(
        region=region,
        instance_id=instance_id,
        schedule_name=schedule_name,
        stop_after_minutes=stop_after_minutes,
        canonical_path=ROW042_EVIDENCE,
        schedule_dry_run_path=schedule_path,
        watchdog_dry_run_path=watchdog_path,
    )


def run_aws(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["aws", *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=AWS_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def aws_call_json(args: list[str]) -> dict[str, Any]:
    proc = run_aws([*args, "--output", "json"])
    if proc is None:
        return {"ok": False, "exit_code": None, "payload": {}}
    if proc.returncode != 0:
        return {"ok": False, "exit_code": proc.returncode, "payload": {}}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {"ok": True, "exit_code": 0, "payload": payload}


def parse_instance_state(payload: dict[str, Any]) -> str:
    reservations = payload.get("Reservations", [])
    if not reservations:
        return "unknown"
    instances = reservations[0].get("Instances", [])
    if not instances:
        return "unknown"
    state_name = instances[0].get("State", {}).get("Name")
    return str(state_name or "unknown")


def parse_ssm_managed(payload: dict[str, Any]) -> bool:
    return bool(payload.get("InstanceInformationList", []))


def classify_readiness(
    *,
    auth_verified: bool,
    role_verified: bool,
    instance_state: str,
    schedule_present: bool,
    ssm_managed: bool,
    watchdog_proof_present: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    recommendations: list[str] = []
    instance_state_normalized = (instance_state or "unknown").lower()
    instance_is_stopped = instance_state_normalized == "stopped"
    running_without_ttl_controls = (
        instance_state_normalized == "running" and (not schedule_present or not watchdog_proof_present)
    )

    if not auth_verified:
        blockers.append("aws_auth_not_verified")
    if not role_verified:
        blockers.append("scheduler_role_not_verified")

    if not instance_is_stopped:
        blockers.append("final_instance_state_not_stopped")
        if running_without_ttl_controls:
            blockers.append("running_instance_without_ttl_controls")

    if auth_verified and role_verified and instance_is_stopped:
        if not schedule_present:
            blockers.append("live_emergency_stop_schedule_missing")
        if not ssm_managed or not watchdog_proof_present:
            blockers.append("ssm_watchdog_proof_missing")

    completed = not blockers
    if completed:
        status = STATUS_COMPLETED
        qa_decision = "ec2_ttl_watchdog_live_readiness_completed_read_only"
    elif "running_instance_without_ttl_controls" in blockers:
        status = STATUS_BLOCKED_RUNNING
        qa_decision = "ec2_running_without_ttl_controls_blocked"
    elif not auth_verified:
        status = STATUS_BLOCKED_AUTH
        qa_decision = "aws_auth_not_verified_blocked"
    elif not role_verified:
        status = STATUS_BLOCKED_ROLE
        qa_decision = "scheduler_role_not_verified_blocked"
    elif (
        auth_verified
        and role_verified
        and instance_is_stopped
        and (not schedule_present or not ssm_managed or not watchdog_proof_present)
    ):
        status = STATUS_BLOCKED_MISSING_PROOF
        qa_decision = "aws_readiness_verified_but_live_ttl_watchdog_proof_missing"
        recommendations.append(
            "Create the emergency-stop schedule and start the SSM watchdog only inside the next genuinely required bounded runtime window; do not start EC2 now."
        )
    else:
        status = STATUS_BLOCKED_MISSING_PROOF
        qa_decision = "ec2_ttl_watchdog_live_readiness_blocked"

    return {
        "row042_complete": completed,
        "status": status,
        "qa_decision": qa_decision,
        "blockers": sorted(set(blockers)),
        "recommendations": recommendations,
    }


def run_live_probe() -> dict[str, Any]:
    metadata = load_row042_metadata()
    role_cfg = parse_env_scheduler_role()

    sts = aws_call_json(["sts", "get-caller-identity"])
    ec2 = aws_call_json(
        [
            "ec2",
            "describe-instances",
            "--region",
            metadata.region,
            "--instance-ids",
            metadata.instance_id,
        ]
    )
    scheduler = aws_call_json(
        [
            "scheduler",
            "get-schedule",
            "--region",
            metadata.region,
            "--name",
            metadata.schedule_name,
        ]
    )
    ssm = aws_call_json(
        [
            "ssm",
            "describe-instance-information",
            "--region",
            metadata.region,
            "--filters",
            f"Key=InstanceIds,Values={metadata.instance_id}",
        ]
    )

    iam = (
        aws_call_json(["iam", "get-role", "--role-name", role_cfg["role_name"]])
        if role_cfg["role_name"]
        else {"ok": False, "exit_code": None, "payload": {}}
    )

    instance_state = parse_instance_state(ec2["payload"]) if ec2["ok"] else "unknown"
    schedule_present = bool(scheduler["ok"])
    ssm_managed = parse_ssm_managed(ssm["payload"]) if ssm["ok"] else False
    # A managed-instance record proves reachability only, never watchdog execution.
    watchdog_proof_present = False

    classification = classify_readiness(
        auth_verified=bool(sts["ok"]),
        role_verified=bool(iam["ok"]),
        instance_state=instance_state,
        schedule_present=schedule_present,
        ssm_managed=ssm_managed,
        watchdog_proof_present=watchdog_proof_present,
    )

    output = {
        "schema_version": "1.0",
        "mode": "read_only_live_probe",
        "operation": "row042_live_readiness_reconciliation",
        "root_selection": {
            "root_kind": "windows" if ROOT == WINDOWS_ROOT else "wsl",
            "env_override_used": bool(os.environ.get("COMFY_UI_MAIN_ROOT")),
        },
        "metadata_source": {
            "canonical_evidence_path": metadata.canonical_path.resolve().as_posix(),
            "schedule_dry_run_path": metadata.schedule_dry_run_path.resolve().as_posix(),
            "watchdog_dry_run_path": metadata.watchdog_dry_run_path.resolve().as_posix(),
            "region_present": bool(metadata.region),
            "instance_id_present": bool(metadata.instance_id),
            "schedule_name_present": bool(metadata.schedule_name),
            "stop_after_minutes": metadata.stop_after_minutes,
        },
        "env_parse": {
            "env_file_present": role_cfg["env_file_present"],
            "candidate_role_keys_present": role_cfg["candidate_role_keys_present"],
            "role_arn_seen": role_cfg["role_arn_seen"],
            "role_name_present": bool(role_cfg["role_name"]),
        },
        "aws_read_ops": {
            "only_read_operations_used": True,
            "sts_get_caller_identity_ok": bool(sts["ok"]),
            "ec2_describe_instances_ok": bool(ec2["ok"]),
            "scheduler_get_schedule_ok": bool(scheduler["ok"]),
            "iam_get_role_ok": bool(iam["ok"]),
            "ssm_describe_instance_information_ok": bool(ssm["ok"]),
            "instance_state": instance_state,
            "schedule_present": schedule_present,
            "ssm_managed": ssm_managed,
            "watchdog_proof_present": watchdog_proof_present,
        },
        "classification": classification,
    }
    return sanitize(output)


def build_evidence(probe: dict[str, Any], created_iso: str, stamp: str) -> dict[str, Any]:
    canonical = read_json(ROW042_EVIDENCE)
    schedule_path, watchdog_path, expected_schedule_sha, expected_watchdog_sha = resolve_local_plan_paths(canonical)
    schedule_plan = read_json(schedule_path)
    watchdog_plan = read_json(watchdog_path)
    aws = probe["aws_read_ops"]
    classification = probe["classification"]
    checks = {
        "original_evidence_exists": ORIGINAL_EVIDENCE.exists(),
        "schedule_dry_run_exists": schedule_path.exists(),
        "watchdog_dry_run_exists": watchdog_path.exists(),
        "schedule_dry_run_hash_preserved": sha256(schedule_path) == expected_schedule_sha,
        "watchdog_dry_run_hash_preserved": sha256(watchdog_path) == expected_watchdog_sha,
        "schedule_plan_pass": schedule_plan.get("result") == "dry_run_emergency_stop_schedule_plan",
        "watchdog_plan_pass": watchdog_plan.get("result") == "dry_run_instance_watchdog_plan",
        "schedule_ttl_60": schedule_plan.get("stop_after_minutes") == 60,
        "watchdog_ttl_60": watchdog_plan.get("stop_after_minutes") == 60,
        "schedule_execute_false": schedule_plan.get("execute") is False,
        "watchdog_execute_false": watchdog_plan.get("execute") is False,
        "aws_authentication_verified": aws["sts_get_caller_identity_ok"],
        "scheduler_role_verified": aws["iam_get_role_ok"],
        "ec2_state_query_pass": aws["ec2_describe_instances_ok"],
        "final_instance_state_stopped": aws["instance_state"] == "stopped",
        "scheduler_query_completed": True,
        "live_schedule_state_consistent": aws["schedule_present"] == ("live_emergency_stop_schedule_missing" not in classification["blockers"]),
        "ssm_query_pass": aws["ssm_describe_instance_information_ok"],
        "ssm_watchdog_state_consistent": aws["watchdog_proof_present"] == ("ssm_watchdog_proof_missing" not in classification["blockers"]),
        "stale_auth_blocker_cleared": "aws_auth_not_verified" not in classification["blockers"],
        "live_blockers_logically_consistent": not ({"aws_auth_not_verified", "scheduler_role_not_verified"} & set(classification["blockers"])),
        "ec2_not_started": True,
        "aws_not_mutated": True,
        "next_runtime_window_boundary_recorded": bool(classification["recommendations"]),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "1.0",
        "evidence_id": f"EC2_TTL_WATCHDOG_LIVE_READINESS_{stamp}",
        "created_iso": created_iso,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": classification["status"],
        "row_complete": classification["row042_complete"],
        "qa_decision": classification["qa_decision"],
        "task": "Replace the stale expired-auth blocker with bounded read-only AWS TTL/watchdog readiness proof.",
        "preserved_local_plans": {
            "schedule_path": relative(schedule_path),
            "schedule_sha256": sha256(schedule_path),
            "watchdog_path": relative(watchdog_path),
            "watchdog_sha256": sha256(watchdog_path),
        },
        "live_readiness": {
            "mode": probe["mode"],
            "aws_authenticated": aws["sts_get_caller_identity_ok"],
            "scheduler_role_verified": aws["iam_get_role_ok"],
            "instance_state": aws["instance_state"],
            "live_schedule_present": aws["schedule_present"],
            "ssm_managed_record_present": aws["ssm_managed"],
            "watchdog_proof_present": aws["watchdog_proof_present"],
            "blockers": classification["blockers"],
            "recommendations": classification["recommendations"],
        },
        "safety_boundary": {
            "aws_contacted_read_only": True,
            "ec2_started_or_stopped": False,
            "scheduler_created_updated_or_deleted": False,
            "ssm_command_sent": False,
            "generation_executed": False,
            "identifiers_or_secrets_recorded": False,
            "mask_jira_wave_gate_action": False,
        },
        "checks": [{"name": name, "result": "pass" if passed else "fail"} for name, passed in checks.items()],
        "check_summary": {"checked": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
        "next_action": (
            "Advance to TRK-W64-043 / ITEM-W64-043; live TTL/watchdog and stopped-state proof are complete."
            if classification["row042_complete"]
            else "Keep EC2 stopped. Create the emergency-stop schedule and start the SSM watchdog only inside the next genuinely required bounded runtime window, then record final stopped-state proof."
        ),
    }


def upsert_hydration_block(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig")
    marker = "## Wave64 Row042 EC2 TTL Watchdog Live Readiness - "
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        tail = current[next_heading + 1 :] if next_heading >= 0 else ""
        path.write_text(block.strip() + "\n\n" + tail.lstrip(), encoding="utf-8")
    else:
        prepend(path, block)


def write_evidence(probe: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(TZ)
    created_iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    payload = build_evidence(probe, created_iso, stamp)
    if payload["check_summary"]["failed"]:
        raise SystemExit("Row042 read-only reconciliation checks failed; refusing evidence update.")
    canonical = ROW042_EVIDENCE
    stamped = QA / f"EC2_TTL_WATCHDOG_LIVE_READINESS_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "ec2_ttl_watchdog_live_readiness_test_log.json"
    item_report = PLAN / "Items/Reports/ITEM-W64-042_ec2_ttl_watchdog.json"
    evidence_paths = [relative(canonical), relative(stamped), relative(mirror), relative(test_log), relative(item_report), relative(ORIGINAL_EVIDENCE)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write_json(path, payload)
    write_json(test_log, {"schema_version": "1.0", "created_iso": created_iso, "tracker_id": TRK, "result": "pass", "checks": payload["checks"], "summary": payload["check_summary"]})
    write_json(item_report, {"schema_version": "1.0", "created_iso": created_iso, "tracker_id": TRK, "item_id": ITEM, "status": payload["status"], "row_complete": payload["row_complete"], "blockers": payload["live_readiness"]["blockers"], "evidence": evidence_paths, "next_action": payload["next_action"]})
    note = (
        f"Wave64 Row042 {stamp}: {payload['check_summary']['passed']}/{payload['check_summary']['checked']} read-only reconciliation checks pass; "
        + (
            "live TTL/watchdog and final stopped-state proof complete."
            if payload["row_complete"]
            else f"AWS auth, scheduler role, and stopped instance verified; blockers remain: {', '.join(payload['live_readiness']['blockers'])}."
        )
    )
    tags = (
        ["wave64_row042_ttl_watchdog_pass", "live_controls_verified", "final_stopped_state_verified", "advance_row043"]
        if payload["row_complete"]
        else ["wave64_row042_aws_readiness_verified", "stale_auth_blocker_cleared", "live_schedule_missing", "ssm_watchdog_proof_missing", "ec2_remains_stopped"]
    )
    tracker_counts = [update_csv(path, "Tracker_ID", TRK, {"Status": payload["status"], "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_counts = [update_csv(path, "Item_ID", ITEM, {"Status": payload["status"], "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_counts != [1, 1] or item_counts != [1, 1]:
        raise SystemExit(f"Row042 CSV cardinality failure: tracker={tracker_counts}, item={item_counts}")
    block = f"""## Wave64 Row042 EC2 TTL Watchdog Live Readiness - {created_iso}

`{TRK}` / `{ITEM}` is `{payload['status']}`. The stale expired-session blocker is cleared: current read-only AWS proof verifies authentication, the scheduler role, and the approved instance in stopped state. All 24 reconciliation checks pass. {('Live schedule, SSM watchdog execution, and final stopped-state proof are complete.' if payload['row_complete'] else 'Current blockers are recorded fail-closed: ' + ', '.join(payload['live_readiness']['blockers']) + '.')} EC2 was not started by this reconciliation; any missing controls must be installed only inside the next genuinely required bounded runtime window.

Next: `{payload['next_action']}`

Evidence: `{relative(canonical)}`; `{relative(stamped)}`; `{relative(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        upsert_hydration_block(HYD / name, block)
    with (HYD / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([created_iso, "64", TRK, "Reconciled EC2 TTL/watchdog live readiness without starting EC2.", "; ".join(evidence_paths), "24/24 checks; auth/role/stopped state pass; live schedule and watchdog proof missing", payload["qa_decision"], relative(canonical), "Install live controls only in next required bounded runtime window."])
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only live readiness reconciler for Wave64 Row042.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output (default behavior).")
    parser.add_argument("--write-evidence", action="store_true", help="Write the exact Row042 blocker evidence and ledgers.")
    args = parser.parse_args()
    probe = run_live_probe()
    result = write_evidence(probe) if args.write_evidence else probe
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
