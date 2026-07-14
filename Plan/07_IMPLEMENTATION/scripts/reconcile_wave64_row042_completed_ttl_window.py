#!/usr/bin/env python3
"""Close Row042 from one already-completed, locally preserved EC2 runtime window."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
TRK = "TRK-W64-042"
ITEM = "ITEM-W64-042"
STATUS = "Completed_Live_TTL_Watchdog_Proof_And_Final_Stop_Pass"
DECISION = "ec2_ttl_watchdog_completed_window_reconciled_existing_proof_no_rerun"
DEFAULT_SOURCES = {
    "schedule": Path("Plan/Instructions/QA/Evidence/Runtime_Readiness/W64_NORMAL_SMOKE_EMERGENCY_STOP_SCHEDULE_LIVE_2011CF98_20260713T150022-0500.json"),
    "watchdog": Path("Plan/Instructions/QA/Evidence/Runtime_Readiness/W64_NORMAL_SMOKE_INSTANCE_WATCHDOG_LIVE_2011CF98_20260713T150058-0500.json"),
    "runtime": Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_NORMAL_EC2_WORKFLOW_SMOKE_EXECUTION_2011CF98_20260713T150058-0500.json"),
    "cleanup": Path("Plan/Instructions/QA/Evidence/Runtime_Readiness/W64_NORMAL_EC2_RUNTIME_CLEANUP_2011CF98_20260713T151600-0500.json"),
    "visual_qa": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_NORMAL_EC2_WORKFLOW_SMOKE_VISUAL_QA_2011CF98_20260713T151500-0500.json"),
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def bind(path: Path, root: Path) -> dict[str, Any]:
    path = path.resolve()
    root = root.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"source outside project root: {path}") from exc
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if not path.is_file() or after.st_size < 1:
        raise ValueError(f"source missing or empty: {path}")
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"source changed while hashing: {path}")
    return {"path": relative.as_posix(), "sha256": digest.hexdigest(), "bytes": after.st_size}


def require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(label)


def normalized_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").lower()


def build_evidence(root: Path, sources: dict[str, Path], timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    resolved = {name: path.resolve() for name, path in sources.items()}
    payloads = {name: load_json(path) for name, path in resolved.items()}
    bindings = {name: bind(path, root) for name, path in resolved.items()}
    schedule = payloads["schedule"]
    watchdog = payloads["watchdog"]
    runtime = payloads["runtime"]
    cleanup = payloads["cleanup"]
    visual = payloads["visual_qa"]

    window = str(schedule.get("runtime_window_id", ""))
    require(bool(window), "schedule runtime_window_id missing")
    for name, payload in (("watchdog", watchdog), ("runtime", runtime), ("cleanup", cleanup)):
        require(payload.get("runtime_window_id") == window, f"{name} runtime window mismatch")
    require(schedule.get("tracker_id") == TRK and schedule.get("item_id") == ITEM, "schedule row identity mismatch")
    require(watchdog.get("tracker_id") == TRK and watchdog.get("item_id") == ITEM, "watchdog row identity mismatch")
    for field in ("instance_id", "region"):
        expected = schedule.get(field)
        require(bool(expected), f"schedule {field} missing")
        for name, payload in (("watchdog", watchdog), ("runtime", runtime), ("cleanup", cleanup)):
            require(payload.get(field) == expected, f"{name} {field} mismatch")

    ttl = schedule.get("stop_after_minutes")
    require(isinstance(ttl, int) and not isinstance(ttl, bool) and 1 <= ttl <= 60, "invalid schedule TTL")
    require(watchdog.get("stop_after_minutes") == ttl, "watchdog TTL mismatch")
    require(runtime.get("max_ec2_runtime_minutes") == ttl, "runtime TTL mismatch")
    require(schedule.get("operation") == "new_ec2_emergency_stop_schedule", "schedule operation mismatch")
    require(schedule.get("execute") is True and schedule.get("aws_contacted") is True, "schedule is not live proof")
    require(schedule.get("schedule_verified") is True and schedule.get("schedule_state") == "ENABLED", "schedule not verified enabled")
    require(schedule.get("action_after_completion") == "DELETE", "schedule auto-delete missing")
    require(schedule.get("result") == "emergency_stop_schedule_created_and_verified", "schedule result mismatch")
    require(not schedule.get("errors"), "schedule errors present")

    require(watchdog.get("operation") == "start_ec2_instance_stop_watchdog", "watchdog operation mismatch")
    require(watchdog.get("execute") is True and watchdog.get("aws_contacted") is True, "watchdog is not live proof")
    require(watchdog.get("command_status") == "Success", "watchdog command did not succeed")
    require(watchdog.get("stop_capability_verified") is True, "watchdog stop capability not verified")
    require(bool(watchdog.get("command_id")) and bool(watchdog.get("watchdog_pid")), "watchdog identity missing")
    require(watchdog.get("result") == "instance_stop_watchdog_started_and_capability_verified", "watchdog result mismatch")
    require(not watchdog.get("errors"), "watchdog errors present")

    require(runtime.get("mode") == "execute", "runtime was not an execute run")
    require(runtime.get("result") == "workflow_smoke_generation_complete", "runtime generation incomplete")
    require(runtime.get("execute_gates_pass") is True and not runtime.get("blocked_reasons"), "runtime execute gates failed")
    require(runtime.get("generation_executed") is True and runtime.get("ec2_started") is True, "runtime did not execute")
    require(runtime.get("command_status") == "Success", "runtime command did not succeed")
    require(runtime.get("stop_exit_code") == 0 and runtime.get("final_state") == "stopped", "runtime final stop failed")
    require(runtime.get("stop_failure_category") is None and not runtime.get("errors"), "runtime stop/errors present")
    require(runtime.get("emergency_stop_gate", {}).get("status") == "pass", "runtime schedule gate did not pass")
    require(runtime.get("instance_watchdog", {}).get("status") == "pass", "runtime watchdog gate did not pass")
    require(normalized_path(runtime.get("emergency_stop_gate", {}).get("path")).endswith(bindings["schedule"]["path"].lower()), "runtime schedule path mismatch")
    require(normalized_path(runtime.get("instance_watchdog", {}).get("path")).endswith(bindings["watchdog"]["path"].lower()), "runtime watchdog path mismatch")

    require(cleanup.get("schedule_name") == schedule.get("schedule_name"), "cleanup schedule mismatch")
    require(cleanup.get("instance_state_query_exit_code") == 0, "cleanup instance query failed")
    require(cleanup.get("instance_final_state") == "stopped", "cleanup final state not stopped")
    require(cleanup.get("schedule_delete_exit_code") == 0, "cleanup schedule deletion failed")
    require(cleanup.get("schedule_absence_verified") is True, "cleanup schedule absence unverified")
    require(cleanup.get("result") == "runtime_cleanup_verified", "cleanup result mismatch")
    require(cleanup.get("failure_category") is None, "cleanup failure present")

    require(visual.get("result") == "pass_runtime_smoke_visual_qa", "visual QA did not pass")
    require(visual.get("instance_final_state_independently_verified") == "stopped", "visual QA lacks independent stopped proof")
    require(normalized_path(visual.get("runtime_evidence")) == bindings["runtime"]["path"].lower(), "visual QA runtime binding mismatch")
    require(visual.get("integrity_boundary", {}).get("runtime_generation_complete") is True, "visual QA runtime completion missing")
    boundaries = visual.get("scope_boundary")
    require(isinstance(boundaries, list), "visual QA scope boundary missing")
    rendered_boundary = " ".join(str(item).lower() for item in boundaries)
    require("does not evaluate or promote body" in rendered_boundary, "visual QA mask boundary missing")
    require("does not activate wave71" in rendered_boundary, "visual QA Wave71 boundary missing")

    stamp = timestamp.replace("-", "").replace(":", "")
    checks = [
        "single_runtime_window_exact_match",
        "live_schedule_created_verified_enabled",
        "schedule_auto_delete_configured",
        "live_ssm_watchdog_command_success",
        "watchdog_stop_capability_verified",
        "ttl_parity_schedule_watchdog_runtime",
        "runtime_execute_gates_pass",
        "runtime_generation_complete",
        "runtime_final_state_stopped",
        "cleanup_final_state_stopped",
        "cleanup_schedule_absence_verified",
        "independent_visual_qa_stopped_state",
        "body_mask_and_wave71_boundaries_preserved",
    ]
    evidence_paths = [binding["path"] for binding in bindings.values()]
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-ROW042-COMPLETED-TTL-WINDOW-{stamp}",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": True,
        "qa_decision": DECISION,
        "runtime_window": {
            "runtime_window_id": window,
            "stop_after_minutes": ttl,
            "schedule_name": schedule.get("schedule_name"),
            "generation_executed": True,
            "schedule_verified_enabled": True,
            "watchdog_stop_capability_verified": True,
            "runtime_final_state": "stopped",
            "cleanup_final_state": "stopped",
            "schedule_absence_verified": True,
            "visual_qa_result": visual.get("result"),
        },
        "source_bindings": bindings,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "blockers": [],
        "reconciliation_execution_boundary": {
            "method": "local_file_only_no_cloud_client_or_subprocess_code_path",
            "independent_runtime_telemetry": False,
            "declared_actions": {
                "aws_contacted": False,
                "ec2_started_or_stopped": False,
                "scheduler_mutated": False,
                "ssm_command_sent": False,
                "generation_executed": False,
            },
        },
        "claim_boundary": {
            "historical_window_only": True,
            "full_project_certification": False,
            "body_mask_or_geometry_authority": False,
            "mask_promotion_authorized": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activation_authorized": False,
        },
        "evidence_paths": evidence_paths,
        "next_action": "Preserve Row042 complete and continue duplicate-checking TRK-W64-043 / ITEM-W64-043 without rerunning this EC2 window.",
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_unique(old: str, value: str) -> str:
    parts = [part.strip() for part in (old or "").split(";") if part.strip()]
    if value not in parts:
        parts.append(value)
    return "; ".join(parts)


def update_csv(path: Path, key: str, identifier: str, changes: dict[str, Any]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != identifier:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = append_unique(row.get(field, ""), value) if field in {"Evidence_Path", "Evidence_Required", "Coverage_Audit_Status", "Notes"} else value
    if matched != 1:
        raise ValueError(f"expected one {identifier} row in {path}, found {matched}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def apply_ledgers(root: Path, evidence_path: str, note: str) -> None:
    tracker_changes = {
        "Status": STATUS,
        "Status_Decision": DECISION,
        "Evidence_Path": evidence_path,
        "Coverage_Audit_Status": "row042_completed_existing_ttl_window_no_rerun",
        "Notes": note,
    }
    item_changes = {
        "Status": STATUS,
        "Evidence_Required": evidence_path,
        "Coverage_Audit_Status": "row042_completed_existing_ttl_window_no_rerun",
        "Notes": note,
    }
    for path in (
        root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", TRK, tracker_changes)
    for path in (
        root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        root / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", ITEM, item_changes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    for name, default in DEFAULT_SOURCES.items():
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, default=default)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracker-output", type=Path, required=True)
    parser.add_argument("--canonical-output", type=Path)
    parser.add_argument("--item-report", type=Path)
    parser.add_argument("--apply-ledger", action="store_true")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve()
        sources = {
            name: ((value if value.is_absolute() else root / value).resolve())
            for name, value in ((name, getattr(args, name)) for name in DEFAULT_SOURCES)
        }
        evidence = build_evidence(root, sources, args.timestamp)
        outputs = [args.output, args.tracker_output]
        if args.canonical_output:
            outputs.append(args.canonical_output)
        resolved_outputs = [(path if path.is_absolute() else root / path).resolve() for path in outputs]
        for path in resolved_outputs:
            path.relative_to(root)
            write_atomic(path, evidence)
        if args.item_report:
            report_path = (args.item_report if args.item_report.is_absolute() else root / args.item_report).resolve()
            report_path.relative_to(root)
            write_atomic(
                report_path,
                {
                    "schema_version": "1.0",
                    "created_iso": args.timestamp,
                    "tracker_id": TRK,
                    "item_id": ITEM,
                    "status": STATUS,
                    "row_complete": True,
                    "blockers": [],
                    "evidence": [path.relative_to(root).as_posix() for path in resolved_outputs] + evidence["evidence_paths"],
                    "next_action": evidence["next_action"],
                },
            )
        if args.apply_ledger:
            primary = resolved_outputs[0].relative_to(root).as_posix()
            note = "Wave64 Row042 existing-window reconciliation: one live schedule/watchdog/runtime/cleanup/visual-QA chain passes with final stopped state; no AWS or EC2 action was rerun."
            apply_ledgers(root, primary, note)
        print(json.dumps({"status": STATUS, "row_complete": True, "output": str(resolved_outputs[0])}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
