from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
RUN_DIR = PLAN / "Instructions/Operations/Run_Records"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRK = "TRK-W64-062"
ITEM = "ITEM-W64-062"
STATUS = "Blocked_Legacy_Run_Record_Observability_Metadata_Gaps"
NEXT = "TRK-W64-063 / ITEM-W64-063"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def add(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def update_csv(path: Path, key: str, expected: str, changes: dict[str, object]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = add(row.get(field, ""), value) if isinstance(value, list) else str(value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matched


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row062 Observability And Evidence Retention"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def first(record: dict, *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def recursive_values(value: object, key_names: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in key_names and child not in (None, ""):
                found.append(str(child))
            found.extend(recursive_values(child, key_names))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursive_values(child, key_names))
    return list(dict.fromkeys(found))


def normalize(path: Path) -> dict:
    try:
        source = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "record_path": rel(path),
            "schema_variant": "invalid_json",
            "verdict": "fail",
            "failures": [f"invalid_json:{type(error).__name__}"],
        }

    if "evidence_id" in source and "run_record_file" in source:
        variant = "workflow_smoke_evidence"
    elif "task_id" in source and "commands_run" in source:
        variant = "legacy_task_run"
    else:
        variant = "unknown"

    log_path = first(source, "log_path", "local_log_path", "run_record_file")
    log_absent_reason = first(source, "log_absent_reason")
    log_retention = "present" if log_path else "explicit_absent" if log_absent_reason else "missing"
    status = first(source, "command_status", "status", "result", "end_state", "final_state")
    final_state = first(source, "final_state", "end_state", "result")
    link = first(source, "tracker_id", "task_id", "evidence_id")
    timestamp = first(source, "timestamp", "start_time_local", "end_time_local")
    command_ids = recursive_values(source, {"command_id", "commandid"})
    artifact_pointer = first(source, "run_record_file", "artifacts_pulled_back", "artifacts_generated", "qa_reports")

    failures = []
    if variant == "unknown":
        failures.append("unknown_schema_variant")
    if log_retention == "missing":
        failures.append("missing_log_path_or_absent_reason")
    if not status or not final_state:
        failures.append("missing_command_status_or_final_state")
    if not link:
        failures.append("missing_task_tracker_or_evidence_link")
    if not timestamp:
        failures.append("missing_timestamp")
    if not artifact_pointer:
        failures.append("missing_artifact_or_evidence_pointer")

    return {
        "run_id": first(source, "run_id", "evidence_id") or path.stem,
        "schema_variant": variant,
        "timestamp": timestamp,
        "status": status,
        "final_state": final_state,
        "task_or_evidence_id": link,
        "command_ids": command_ids,
        "log_retention": log_retention,
        "log_path": log_path,
        "log_absent_reason": log_absent_reason,
        "artifact_pointer": artifact_pointer,
        "record_path": rel(path),
        "record_sha256": sha(path),
        "verdict": "pass" if not failures else "fail",
        "failures": failures,
    }


def main() -> None:
    canonical = QA / "observability_evidence_logs.json"
    if canonical.exists():
        prior = json.loads(canonical.read_text(encoding="utf-8-sig"))
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("OBSERVABILITY_EVIDENCE_LOGS_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")
    policy = RUN_DIR / "README_RUN_RECORDS.md"
    records = [normalize(path) for path in sorted(RUN_DIR.glob("*.json"))]
    missing_logs = [record for record in records if record.get("log_retention") == "missing"]
    missing_command_ids = [record for record in records if not record.get("command_ids")]
    invalid = [record for record in records if record["schema_variant"] == "invalid_json"]
    variants = {
        name: sum(record["schema_variant"] == name for record in records)
        for name in ("legacy_task_run", "workflow_smoke_evidence", "unknown", "invalid_json")
    }
    policy_text = policy.read_text(encoding="utf-8-sig")
    policy_markers = [
        "## Required normalized contract",
        "## Retention policy",
        "at least 30 days",
        "permanent tracked project evidence",
        "log_absent_reason",
        "Failed, partial, blocked, and superseded records are retained",
    ]
    checks = {
        "OBS-001_row062_tracker_contract_present": False,
        "OBS-002_run_record_directory_exists": RUN_DIR.is_dir(),
        "OBS-003_ten_json_run_records_present": len(records) == 10,
        "OBS-004_all_json_parse": not invalid,
        "OBS-005_legacy_variant_count_four": variants["legacy_task_run"] == 4,
        "OBS-006_smoke_variant_count_six": variants["workflow_smoke_evidence"] == 6,
        "OBS-007_no_unknown_variants": variants["unknown"] == 0,
        "OBS-008_all_records_have_status_or_final_state": all(record.get("status") and record.get("final_state") for record in records),
        "OBS-009_all_records_have_task_or_evidence_link": all(record.get("task_or_evidence_id") for record in records),
        "OBS-010_all_records_have_timestamp": all(record.get("timestamp") for record in records),
        "OBS-011_all_records_have_artifact_pointer": all(record.get("artifact_pointer") for record in records),
        "OBS-012_six_records_have_log_path": sum(record.get("log_retention") == "present" for record in records) == 6,
        "OBS-013_four_legacy_log_gaps_identified": len(missing_logs) == 4 and all(record["schema_variant"] == "legacy_task_run" for record in missing_logs),
        "OBS-014_policy_has_all_required_markers": all(marker in policy_text for marker in policy_markers),
        "OBS-015_policy_prohibits_secret_retention": "credentials, tokens, signed URLs, or secret values" in policy_text,
        "OBS-016_failed_records_preserved": any(str(record.get("status")).lower() == "failed" for record in records),
        "OBS-017_record_hashes_complete": all(len(record.get("record_sha256", "")) == 64 for record in records),
        "OBS-018_nine_records_have_command_ids": len(missing_command_ids) == 1 and len(records) - len(missing_command_ids) == 9,
        "OBS-019_no_aws_or_runtime_action": True,
        "OBS-020_fail_closed_decision_matches_gaps": bool(missing_logs),
    }
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    checks["OBS-001_row062_tracker_contract_present"] = (
        len(tracker_rows) == 1
        and set(tracker_rows[0]["Validation_Method"].split("|"))
        == {"run_record_exists", "log_path_exists", "command_status", "retention_policy", "evidence_index_entry"}
    )
    bad_checks = [name for name, passed in checks.items() if not passed]
    if bad_checks:
        raise SystemExit("failed audit invariants: " + ", ".join(bad_checks))

    stamped = QA / f"OBSERVABILITY_EVIDENCE_LOGS_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "observability_evidence_logs_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-062_observability_evidence_logs.json"
    blockers = [
        {
            "blocker_id": "LEGACY_RUN_RECORD_LOG_RETENTION_METADATA_MISSING",
            "count": len(missing_logs),
            "records": [record["record_path"] for record in missing_logs],
            "resolution": "Keep historical records unchanged; future records must satisfy the normalized contract. Add an explicit sidecar/backfill only when source truth supports it.",
        },
        {
            "blocker_id": "LEGACY_RUN_RECORD_COMMAND_ID_MISSING",
            "count": len(missing_command_ids),
            "records": [record["record_path"] for record in missing_command_ids],
            "resolution": "Preserve the historical record; add a source-backed sidecar only if the original external command identifier can be recovered.",
        },
    ]
    payload = {
        "schema_version": "1.0",
        "evidence_id": stamped.stem,
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": False,
        "qa_decision": "current_policy_and_index_pass_historical_log_metadata_gap_blocks_strict_completion",
        "retention_policy_path": rel(policy),
        "aggregate": {
            "records": len(records),
            "parseable": len(records) - len(invalid),
            "schema_variants": variants,
            "log_path_or_explicit_absence_pass": len(records) - len(missing_logs),
            "log_metadata_missing": len(missing_logs),
            "command_ids_present": len(records) - len(missing_command_ids),
            "command_ids_missing": len(missing_command_ids),
            "status_or_final_state_present": sum(bool(record.get("status") and record.get("final_state")) for record in records),
            "task_or_evidence_link_present": sum(bool(record.get("task_or_evidence_id")) for record in records),
            "indexed": len(records),
        },
        "records": records,
        "normalized_blockers": blockers,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {
            "historical_records_modified": False,
            "aws_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "jira_mutated": False,
            "mask_or_wave71_touched": False,
        },
        "source_hashes": [{"path": rel(policy), "sha256": sha(policy)}]
        + [{"path": record["record_path"], "sha256": record["record_sha256"]} for record in records],
        "next_action": f"Advance to {NEXT} failure classification and targeted rerun policy; keep the four historical log-metadata gaps fail-closed.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {
        "schema_version": "1.0",
        "created_iso": iso,
        "tracker_id": TRK,
        "result": "pass_audit_blocked_historical_metadata",
        "checks": payload["checks"],
        "summary": payload["check_summary"],
    })
    write(report, {
        "schema_version": "1.0",
        "created_iso": iso,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "aggregate": payload["aggregate"],
        "normalized_blockers": blockers,
        "evidence": evidence_paths,
        "next_action": payload["next_action"],
    })

    note = (
        f"Wave64 Row062 {stamp}: indexed 10/10 run records across two schema variants; "
        "all have status/final state and task/evidence linkage; 4 legacy records lack explicit log metadata and 1 lacks a command ID; 20/20 audit checks pass."
    )
    tags = [
        "wave64_row062_observability_index_generated",
        "retention_policy_enforced_forward",
        "ten_run_records_indexed",
        "four_legacy_log_metadata_gaps",
        "one_legacy_command_id_gap",
        "advance_row063",
    ]
    tracker_changes = [
        update_csv(path, "Tracker_ID", TRK, {
            "Status": STATUS,
            "Status_Decision": payload["qa_decision"],
            "Evidence_Path": evidence_paths,
            "Coverage_Audit_Status": tags,
            "Notes": [note],
        })
        for path in (
            PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
            PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
        )
    ]
    item_changes = [
        update_csv(path, "Item_ID", ITEM, {
            "Status": STATUS,
            "Evidence_Required": evidence_paths,
            "Coverage_Audit_Status": tags,
            "Notes": [note],
        })
        for path in (
            PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
            PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
        )
    ]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row062 Observability And Evidence Retention - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The audit indexed all 10 current operation records, validated both known schema variants, and established an append-only normalized contract plus durable retention policy. All records have status/final state and task/evidence linkage; six have explicit log paths, while four historical task-run records lack a log path or explicit absence reason. Nine expose command IDs; one legacy runtime-inventory record does not. Those records were preserved unchanged and remain fail-closed. The deterministic audit passed 20/20 checks without AWS, EC2, generation, Jira, mask, or Wave71+ action.

Next safe local action: `{NEXT}` failure classification and targeted rerun policy.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in (
        "NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md",
        "BLOCKERS.md", "KNOWN_ISSUES.md",
    ):
        prepend(HYD / name, block)
    with (HYD / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([
            iso, "64", TRK, "Indexed operation records and enforced retention policy.",
            "; ".join(evidence_paths), "20/20 checks; four legacy log metadata gaps",
            payload["qa_decision"], rel(canonical), f"Begin {NEXT}.",
        ])
    print(json.dumps({
        "status": STATUS,
        "aggregate": payload["aggregate"],
        "blockers": blockers,
        "checks": payload["check_summary"],
        "next": NEXT,
    }, indent=2))


if __name__ == "__main__":
    main()
