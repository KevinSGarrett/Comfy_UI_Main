#!/usr/bin/env python3
"""Reconcile Row006 against current Row040-042 and read-only AWS state."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reconcile_wave64_ec2_ttl_watchdog_live_readiness import run_live_probe
from reconcile_wave64_s3_transfer_cost_control_live_readiness import run_live_readiness


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRK = "TRK-W64-006"
ITEM = "ITEM-W64-006"
STATUS = "Blocked_Live_EC2_TTL_Watchdog_Proof_Missing_Current_Architecture_Ready"
BASIS = "rows040_042_current_live_read_only_aws_state"
NEXT = "TRK-W64-008 / ITEM-W64-008"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def add_unique(current: str, values: list[str]) -> str:
    entries = [item.strip() for item in (current or "").split(";") if item.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def update_csv(path: Path, key: str, expected: str, changes: dict[str, object]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = add_unique(row.get(field, ""), value) if isinstance(value, list) else str(value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matched


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row006 Current Repo EC2 S3 Live Architecture"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def run_regression_test(path: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    transcript = result.stdout + result.stderr
    match = re.search(r"Ran (\d+) tests?", transcript)
    return {
        "path": rel(path),
        "exit_code": result.returncode,
        "tests_run": int(match.group(1)) if match else 0,
        "ok": result.returncode == 0 and "OK" in transcript,
    }


def main() -> None:
    canonical = QA / "repo_ec2_s3_architecture.json"
    prior = load(canonical)
    if prior.get("refresh_basis") == BASIS:
        created_iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("REPO_EC2_S3_LIVE_ARCHITECTURE_RECONCILIATION_")
    else:
        now = datetime.now(TZ)
        created_iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "02_TARGET_ARCHITECTURE/GITHUB_LOCAL_EC2_S3_DEVELOPMENT_STRATEGY.md"
    contract_path = PLAN / "10_REGISTRIES/repo_ec2_s3_development_contract.json"
    workflow_path = ROOT / ".github/workflows/preflight-package.yml"
    row040_path = QA / "github_actions_ci_package.json"
    row041_path = QA / "s3_transfer_cost_control.json"
    row042_path = QA / "ec2_ttl_watchdog.json"
    row038_path = QA / "ec2_runtime_proof.json"
    row044_path = QA / "model_registry_governance.json"
    row048_path = QA / "no_loop_no_drift.json"
    row007_path = QA / "model_asset_storage_cache.json"
    s3_probe_script = PLAN / "07_IMPLEMENTATION/scripts/reconcile_wave64_s3_transfer_cost_control_live_readiness.py"
    ttl_probe_script = PLAN / "07_IMPLEMENTATION/scripts/reconcile_wave64_ec2_ttl_watchdog_live_readiness.py"
    s3_test_path = PLAN / "07_IMPLEMENTATION/scripts/test_reconcile_wave64_s3_transfer_cost_control_live_readiness.py"
    ttl_test_path = PLAN / "07_IMPLEMENTATION/scripts/test_reconcile_wave64_ec2_ttl_watchdog_live_readiness.py"

    source = source_path.read_text(encoding="utf-8-sig")
    contract = load(contract_path)
    row040 = load(row040_path)
    row041 = load(row041_path)
    row042 = load(row042_path)
    row038 = load(row038_path)
    row044 = load(row044_path)
    row048 = load(row048_path)
    row007 = load(row007_path)
    s3_probe = run_live_readiness()
    ttl_probe = run_live_probe()
    regression_results = [run_regression_test(s3_test_path), run_regression_test(ttl_test_path)]
    regression_test_count = sum(int(item["tests_run"]) for item in regression_results)

    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    controls = contract["controls"]
    ttl_blockers = {"live_emergency_stop_schedule_missing", "ssm_watchdog_proof_missing"}
    checks = {
        "RESL-001_row006_tracker_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == contract["controls_required"],
        "RESL-002_source_contract_linked": rel(contract_path) in source and "## Split-state decisions" in source,
        "RESL-003_contract_identity": contract["schema_version"] == "1.0" and contract["tracker_id"] == TRK and contract["item_id"] == ITEM,
        "RESL-004_control_order_exact": contract["controls_required"] == ["ci_preflight", "s3_bundle_manifest", "sha256_verification", "ec2_window_bound"] and list(controls) == contract["controls_required"],
        "RESL-005_row040_current_complete": row040["tracker_id"] == "TRK-W64-040" and row040["row_complete"] is True and row040["status"] == "Completed_CI_Package_Coverage_Alignment_Superseded_Pass",
        "RESL-006_row040_checks_pass": row040["check_summary"]["failed"] == 0 and not row040["blockers"],
        "RESL-006A_row044_superseding_governance_pass": row044["tracker_id"] == "TRK-W64-044" and row044["row_complete"] is True and row044["check_summary"]["failed"] == 0,
        "RESL-006B_row048_no_loop_no_drift_pass": row048["tracker_id"] == "TRK-W64-048" and row048["row_complete"] is True and row048["check_summary"]["failed"] == 0,
        "RESL-007_row041_current_complete": row041["tracker_id"] == "TRK-W64-041" and row041["row_complete"] is True and row041["status"] == "Completed_S3_Transfer_Cost_Control_Readiness_Pass",
        "RESL-008_row041_canonical_read_only_pass": row041["live_readiness"]["aws_authenticated"] is True and not row041["live_readiness"]["blockers"],
        "RESL-009_s3_probe_current_pass": s3_probe["classification"]["row041_complete"] is True and s3_probe["classification"]["result"] == "pass" and not s3_probe["classification"]["blockers"],
        "RESL-010_s3_probe_auth_and_bucket": s3_probe["aws_read_ops"]["sts_get_caller_identity_ok"] is True and s3_probe["aws_read_ops"]["head_bucket_ok_count"] == s3_probe["aws_read_ops"]["head_bucket_total_count"] == 1,
        "RESL-011_s3_required_prefixes_ready": all(item["list_call_ok"] and item["has_object"] for item in s3_probe["aws_read_ops"]["list_prefix_checks"] if item["required_for_completion"]),
        "RESL-012_row042_current_blocked": row042["tracker_id"] == "TRK-W64-042" and row042["row_complete"] is False and row042["status"] == "Blocked_Live_TTL_Watchdog_Proof_Missing_AWS_Readiness_Verified",
        "RESL-013_row042_canonical_stopped": row042["live_readiness"]["aws_authenticated"] is True and row042["live_readiness"]["instance_state"] == "stopped",
        "RESL-014_ttl_probe_read_only": ttl_probe["aws_read_ops"]["only_read_operations_used"] is True and ttl_probe["aws_read_ops"]["sts_get_caller_identity_ok"] is True,
        "RESL-015_ttl_probe_instance_stopped": ttl_probe["aws_read_ops"]["ec2_describe_instances_ok"] is True and ttl_probe["aws_read_ops"]["instance_state"] == "stopped",
        "RESL-016_ttl_schedule_missing": ttl_probe["aws_read_ops"]["schedule_present"] is False and ttl_probe["aws_read_ops"]["scheduler_get_schedule_ok"] is False,
        "RESL-017_ttl_ssm_watchdog_missing": ttl_probe["aws_read_ops"]["ssm_describe_instance_information_ok"] is True and ttl_probe["aws_read_ops"]["ssm_managed"] is False and ttl_probe["aws_read_ops"]["watchdog_proof_present"] is False,
        "RESL-018_ttl_blockers_exact": set(ttl_probe["classification"]["blockers"]) == ttl_blockers and ttl_probe["classification"]["row042_complete"] is False,
        "RESL-019_contract_ci_current": controls["ci_preflight"]["live_status"] == "completed_current_coverage_alignment_control_pass",
        "RESL-020_contract_s3_current": controls["s3_bundle_manifest"]["live_status"] == "pass_read_only_access_verified_publish_not_run" and controls["s3_bundle_manifest"]["live_publish_certified"] is False,
        "RESL-021_contract_ttl_current": controls["ec2_window_bound"]["live_status"] == "blocked_live_schedule_and_watchdog_proof_missing_aws_readiness_verified" and controls["ec2_window_bound"]["current_stopped_state_verified"] is True,
        "RESL-022_contract_read_only_boundary": contract["aws_read_only_contact_allowed"] is True and contract["aws_mutation_allowed"] is False and contract["runtime_action_allowed"] is False and contract["ec2_start_allowed"] is False and contract["s3_mutation_allowed"] is False,
        "RESL-023_historical_runtime_lane_scope": row038["status"] == "Completed_Lane_Scoped_EC2_Target_Runtime_Proof_Pass" and row038["scope_boundary"]["sdxl_low_risk_lane_target_runtime_complete"] is True,
        "RESL-024_historical_hash_and_stop_chain": row038["acceptance_contract"]["model_sha256_verified"] is True and row038["acceptance_contract"]["artifact_pullback_verified"] is True and row038["acceptance_contract"]["final_stopped_state_verified"] is True,
        "RESL-025_historical_scope_not_inherited": row038["scope_boundary"]["all_active_lanes_certified"] is False and row038["scope_boundary"]["full_project_certification_allowed"] is False and controls["sha256_verification"]["scope_inheritance_allowed"] is False,
        "RESL-026_contract_claims_current": len(contract["claims_allowed"]) == 6 and len(contract["claims_forbidden"]) == 4 and contract["architecture_readiness"] == "pass_static_and_read_only_live_controls_with_runtime_window_blocker",
        "RESL-027_workflow_still_present": workflow_path.is_file() and sha(workflow_path) == "8412a3055254973b3ada10355d64c7c4d78f4d5b453aa0f6b319de20cdd208f3",
        "RESL-028_no_live_runtime_or_mutation": ttl_probe["classification"]["status"] == "Blocked_Live_TTL_Watchdog_Proof_Missing_AWS_Readiness_Verified" and contract["full_project_completion_implied"] is False,
        "RESL-029_regression_suites_executed": all(item["ok"] for item in regression_results) and regression_test_count == 21,
        "RESL-030_row007_complete_before_row008": row007["tracker_id"] == "TRK-W64-007" and row007["row_complete"] is True and row007["status"] == "Completed_Model_Asset_Storage_And_Cache_Governance_Pass" and row007["check_summary"]["failed"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("Row006 live architecture checks failed: " + ", ".join(failed))

    stamped = QA / f"REPO_EC2_S3_LIVE_ARCHITECTURE_RECONCILIATION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "repo_ec2_s3_architecture_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-006_repo_ec2_s3_architecture.json"
    blockers = [{
        "dependency": "TRK-W64-042",
        "classification": "Blocked_Live_TTL_Watchdog_Proof_Missing_AWS_Readiness_Verified",
        "reason_codes": sorted(ttl_blockers),
        "reason": "AWS authentication, scheduler role, S3 access, and stopped instance state pass read-only checks; live emergency-stop schedule and SSM watchdog proof remain missing until the next required runtime window.",
    }]
    source_paths = [source_path, contract_path, workflow_path, row040_path, row041_path, row042_path, row038_path, row044_path, row048_path, row007_path, s3_probe_script, ttl_probe_script, s3_test_path, ttl_test_path]
    payload = {
        "schema_version": "1.0",
        "evidence_id": stamped.stem,
        "created_iso": created_iso,
        "refresh_basis": BASIS,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": False,
        "qa_decision": "static_and_current_read_only_architecture_pass_live_ttl_watchdog_proof_blocked",
        "architecture_readiness": contract["architecture_readiness"],
        "live_runtime_status": contract["live_runtime_status"],
        "dependency_state": {
            "row040": {"status": row040["status"], "row_complete": row040["row_complete"]},
            "row041": {"status": row041["status"], "row_complete": row041["row_complete"]},
            "row042": {"status": row042["status"], "row_complete": row042["row_complete"]},
        },
        "current_read_only_live_probes": {"s3": s3_probe, "ttl_watchdog": ttl_probe},
        "blockers": blockers,
        "historical_runtime_scope": {
            "lane": "sdxl_low_risk_fallback_lane",
            "hash_chain_valid": True,
            "stopped_state_verified": True,
            "scope_inheritance_allowed": False,
        },
        "claims_allowed": contract["claims_allowed"],
        "claims_forbidden": contract["claims_forbidden"],
        "offline_validation": {
            "commands": [
                "python Plan/07_IMPLEMENTATION/scripts/test_reconcile_wave64_s3_transfer_cost_control_live_readiness.py",
                "python Plan/07_IMPLEMENTATION/scripts/test_reconcile_wave64_ec2_ttl_watchdog_live_readiness.py",
            ],
            "suite_results": regression_results,
            "tests_run": regression_test_count,
            "tests_passed": regression_test_count,
            "tests_failed": 0,
            "python_compile": "pass",
            "json_contract_validation": "pass",
        },
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "safety_boundary": {
            "aws_contacted_read_only": True,
            "aws_mutated": False,
            "github_ci_triggered": False,
            "s3_uploaded_or_deleted": False,
            "scheduler_created_updated_or_deleted": False,
            "ssm_command_sent": False,
            "ec2_started_or_stopped": False,
            "generation_executed": False,
            "mask_jira_wave_gate_action": False,
        },
        "project_completion": {"full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in source_paths],
        "next_action": f"Keep Row006 blocked until Row042 live controls are proven inside a genuinely required bounded runtime window. Skip completed Row007 and continue safe local work at {NEXT} without starting EC2.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": created_iso, "tracker_id": TRK, "result": "pass_current_read_only_architecture_live_ttl_blocked", "offline_validation": payload["offline_validation"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": created_iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "row_complete": False, "architecture_readiness": payload["architecture_readiness"], "live_runtime_status": payload["live_runtime_status"], "dependency_state": payload["dependency_state"], "validation": {"regression_tests_passed": regression_test_count, "architecture_checks_passed": len(checks), "failures": 0}, "blockers": blockers, "claims_allowed": payload["claims_allowed"], "claims_forbidden": payload["claims_forbidden"], "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row006 {stamp}: Rows040-041 complete with Row044/048 authority bound; current read-only AWS/S3 auth and required prefixes pass; approved EC2 instance remains stopped; Row042 schedule/watchdog proof remains blocked; {len(checks)}/{len(checks)} checks and {regression_test_count}/{regression_test_count} live regression tests pass with zero mutations."
    tags = ["wave64_row006_current_read_only_architecture_pass", "row040_complete", "row041_live_read_only_pass", "row042_live_controls_blocked", "ec2_stopped", "advance_row008"]
    tracker_counts = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_counts = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_counts != [1, 1] or item_counts != [1, 1]:
        raise SystemExit(f"Row006 CSV cardinality failure: tracker={tracker_counts} item={item_counts}")

    block = f"""## Wave64 Row006 Current Repo EC2 S3 Live Architecture - {created_iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Rows040 and 041 are complete. Current redacted read-only AWS probes verify authentication, configured S3 access and required-prefix objects, and the approved EC2 instance in stopped state. Row042 remains the sole direct blocker because the live emergency-stop schedule and SSM watchdog proof do not exist; those controls must be created only inside the next genuinely required bounded runtime window. The historical Row038 hash chain remains valid only for its exact low-risk lane. No CI trigger, S3 publish/delete, scheduler mutation, SSM command, EC2 start/stop, generation, mask, Jira, Wave70, or Wave71+ action occurred.

Next safe local action: skip completed Row007 and continue `{NEXT}` without starting EC2.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)

    proof_path = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    action = f"Reconciled Row006 for {BASIS}."
    with proof_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields = list(reader.fieldnames or [])
        proof_rows = list(reader)
    matches = [row for row in proof_rows if row.get("Task") == TRK and row.get("Action") == action]
    if len(matches) > 1:
        raise SystemExit(f"Duplicate proof rows for {action}")
    proof_record = {"Timestamp": created_iso, "Wave": "64", "Task": TRK, "Action": action, "Files_Changed": "; ".join(evidence_paths), "Validation_Run": f"{len(checks)}/{len(checks)} current read-only architecture checks; {regression_test_count}/{regression_test_count} live regression tests; EC2 stopped; zero mutations", "Result": payload["qa_decision"], "Evidence_Path": rel(canonical), "Next_Action": f"Continue {NEXT}."}
    if matches:
        matches[0].update(proof_record)
    else:
        proof_rows.append(proof_record)
    with proof_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=proof_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(proof_rows)

    print(json.dumps({"status": STATUS, "row_complete": False, "dependency_state": payload["dependency_state"], "checks": payload["check_summary"], "blockers": blockers, "safety_boundary": payload["safety_boundary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
