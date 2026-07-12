from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRK, ITEM = "TRK-W64-006", "ITEM-W64-006"
STATUS = "Blocked_Live_Repo_EC2_S3_Proof_Static_Architecture_Pass"
GATES = ["ci_preflight", "s3_bundle_manifest", "sha256_verification", "ec2_window_bound"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        fields, rows = reader.fieldnames or [], list(reader)
    matched = 0
    for row in rows:
        if row.get(key) == expected:
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
    marker = "## Wave64 Row006 GitHub Local EC2 S3 Architecture"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "repo_ec2_s3_architecture.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("REPO_EC2_S3_ARCHITECTURE_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "02_TARGET_ARCHITECTURE/GITHUB_LOCAL_EC2_S3_DEVELOPMENT_STRATEGY.md"
    contract_path = PLAN / "10_REGISTRIES/repo_ec2_s3_development_contract.json"
    workflow_path = ROOT / ".github/workflows/preflight-package.yml"
    ci_path = QA / "github_actions_ci_package.json"
    s3_path = QA / "s3_transfer_cost_control.json"
    runtime_path = QA / "ec2_runtime_proof.json"
    ttl_path = QA / "ec2_ttl_watchdog.json"
    bundle_path = PLAN / "Instructions/QA/Evidence/Operations_Static_Validation/W66_EC2_DEPLOY_BUNDLE_CURRENT_ACTIVE_LANES_CONTENT_QA_20260709T014115-0500.json"
    readiness_path = PLAN / "Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READINESS_CURRENT_ACTIVE_LANES_20260709T014300-0500.json"
    source, workflow = source_path.read_text(encoding="utf-8-sig"), workflow_path.read_text(encoding="utf-8-sig")
    contract, ci, s3, runtime, ttl, bundle, readiness = (load(path) for path in (contract_path, ci_path, s3_path, runtime_path, ttl_path, bundle_path, readiness_path))
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    controls = contract["controls"]
    checks = {
        "RES-001_row006_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "RES-002_source_contract_linked": rel(contract_path) in source and "## Split-state decisions" in source,
        "RES-003_contract_schema_identity": contract["schema_version"] == "1.0" and contract["contract_id"] == "wave64_repo_ec2_s3_development_contract" and contract["tracker_id"] == TRK,
        "RES-004_control_order_exact": contract["controls_required"] == GATES and list(controls) == GATES,
        "RES-005_ci_workflow_hash_exact": sha(workflow_path) == "8412a3055254973b3ada10355d64c7c4d78f4d5b453aa0f6b319de20cdd208f3",
        "RES-006_ci_static_contract_present": all(token in workflow for token in ("Checkout without LFS payloads", "lfs: false", "Model registry coverage gate", "Build verified run package", "Build deploy bundle", "retention-days: 7")),
        "RES-007_ci_s3_upload_config_gated": workflow.count("vars.AWS_ROLE_TO_ASSUME != ''") >= 2 and workflow.count("vars.COMFY_DEPLOY_BUNDLE_S3_URI != ''") >= 2,
        "RES-008_ci_current_alignment_blocked": ci["status"] == "Blocked_Current_Model_Registry_Coverage_Alignment" and ci["ci_contract"]["live_github_ci_triggered"] is False,
        "RES-009_ci_split_state_exact": controls["ci_preflight"]["static_status"] == "pass" and controls["ci_preflight"]["live_status"] == "blocked_current_model_registry_coverage_alignment",
        "RES-010_bundle_static_pass_and_hash": bundle["result"] == "pass" and len(bundle["bundle_zip_sha256"]) == 64 and all(check["result"] == "pass" for check in bundle["checks"]),
        "RES-011_bundle_local_only_boundary": bundle["runtime_boundary"]["local_only"] is True and bundle["runtime_boundary"]["aws_contacted"] is False and bundle["runtime_boundary"]["ec2_started"] is False,
        "RES-012_s3_readiness_local_only": readiness["result"] == "ready_local_only" and readiness["local_only"] is True and readiness["aws_contacted"] is False and readiness["ec2_started"] is False,
        "RES-013_s3_live_status_blocked": s3["status"] == "Local_Ready_Only_AWS_Authentication_Expired" and controls["s3_bundle_manifest"]["live_publish_certified"] is False,
        "RES-014_runtime_lane_scoped_pass": runtime["status"] == "Completed_Lane_Scoped_EC2_Target_Runtime_Proof_Pass" and runtime["scope_boundary"]["sdxl_low_risk_lane_target_runtime_complete"] is True and runtime["scope_boundary"]["all_active_lanes_certified"] is False,
        "RES-015_runtime_hash_chain_and_stopped": runtime["acceptance_contract"]["model_sha256_verified"] is True and runtime["acceptance_contract"]["artifact_pullback_verified"] is True and runtime["acceptance_contract"]["final_stopped_state_verified"] is True,
        "RES-016_hash_scope_inheritance_denied": controls["sha256_verification"]["scope_inheritance_allowed"] is False and runtime["scope_boundary"]["full_project_certification_allowed"] is False,
        "RES-017_ttl_dry_runs_exact": ttl["current_local_plans"]["schedule"]["stop_after_minutes"] == 60 and ttl["current_local_plans"]["watchdog"]["stop_after_minutes"] == 60 and ttl["current_local_plans"]["schedule"]["execute"] is False and ttl["current_local_plans"]["watchdog"]["execute"] is False,
        "RES-018_ttl_live_status_blocked": ttl["status"] == "Blocked_AWS_Expired_Session_Live_Proof" and controls["ec2_window_bound"]["live_schedule_executed"] is False and controls["ec2_window_bound"]["live_watchdog_executed"] is False,
        "RES-019_claim_boundaries_complete": len(contract["claims_allowed"]) == 4 and len(contract["claims_forbidden"]) == 5 and contract["architecture_readiness"] == "pass_static_controls_with_live_blockers",
        "RES-020_no_external_action_or_completion": all(contract[key] is False for key in ("runtime_action_allowed", "aws_contact_allowed", "ec2_start_allowed", "s3_mutation_allowed", "full_project_completion_implied")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed repo/EC2/S3 architecture invariants: " + ", ".join(failed))
    groups = {
        "ci_preflight": [name for name in checks if name.startswith(("RES-001", "RES-002", "RES-003", "RES-004", "RES-005", "RES-006", "RES-007", "RES-008", "RES-009"))],
        "s3_bundle_manifest": [name for name in checks if name.startswith(("RES-010", "RES-011", "RES-012", "RES-013"))],
        "sha256_verification": [name for name in checks if name.startswith(("RES-014", "RES-015", "RES-016"))],
        "ec2_window_bound": [name for name in checks if name.startswith(("RES-017", "RES-018", "RES-019", "RES-020"))],
    }
    gate_states = {
        "ci_preflight": {"static_status": "pass", "live_status": "blocked_current_model_registry_coverage_alignment"},
        "s3_bundle_manifest": {"static_status": "pass_local_ready_only", "live_status": "blocked_aws_authentication_expired"},
        "sha256_verification": {"static_status": "pass_bounded_historical_lane_scope", "live_status": "not_current_live_reexecution"},
        "ec2_window_bound": {"static_status": "pass_dry_run_only", "live_status": "blocked_aws_authentication_expired"},
    }
    stamped = QA / f"REPO_EC2_S3_ARCHITECTURE_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "repo_ec2_s3_architecture_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-006_repo_ec2_s3_architecture.json"
    blockers = [
        {"dependency": "TRK-W64-040", "reason": "current CI model-registry coverage alignment remains blocked"},
        {"dependency": "TRK-W64-041", "reason": "live S3 proof remains blocked by expired AWS authentication"},
        {"dependency": "TRK-W64-042", "reason": "live TTL/watchdog enforcement remains blocked by expired AWS authentication"},
    ]
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": "static_architecture_pass_live_ci_s3_ec2_window_blocked",
        "validation_gates": {gate: {**gate_states[gate], "checks": groups[gate]} for gate in GATES},
        "architecture_readiness": contract["architecture_readiness"], "live_runtime_status": "blocked", "blockers": blockers,
        "historical_runtime_scope": {"lane": "sdxl_low_risk_fallback_lane", "hash_chain_valid": True, "stopped_state_verified": True, "scope_inheritance_allowed": False},
        "claims_allowed": contract["claims_allowed"], "claims_forbidden": contract["claims_forbidden"],
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"github_ci_triggered": False, "aws_contacted": False, "s3_mutated": False, "ec2_started": False, "generation_executed": False, "historical_evidence_mutated": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, contract_path, workflow_path, ci_path, s3_path, runtime_path, ttl_path, bundle_path, readiness_path)],
        "next_action": "Proceed to TRK-W64-007 / ITEM-W64-007 for safe local work; do not rerun CI, contact AWS/S3, or start EC2 without material source change and current live gates.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_split_state_audit_live_blocked", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "architecture_readiness": payload["architecture_readiness"], "live_runtime_status": "blocked", "blockers": blockers, "claims_allowed": payload["claims_allowed"], "claims_forbidden": payload["claims_forbidden"], "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})
    note = f"Wave64 Row006 {stamp}: static CI/package, bundle/S3 readiness, bounded historical SHA chain, and EC2-window dry-run controls pass 20/20 checks while current CI alignment and live AWS/S3/TTL proof remain blocked."
    tags = ["wave64_row006_static_architecture_pass", "live_ci_alignment_blocked", "live_s3_blocked_expired_auth", "live_ec2_window_blocked_expired_auth", "row007_next"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row006 GitHub Local EC2 S3 Architecture - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The direct split-state contract passes static CI/package architecture, local deploy-bundle/S3 readiness, the bounded historical low-risk lane SHA chain, and non-executing 60-minute EC2-window controls with 20/20 checks. It remains fail-closed for current CI alignment (`TRK-W64-040`), live S3 proof (`TRK-W64-041`), and live TTL/watchdog enforcement (`TRK-W64-042`). Historical Row038 proof remains valid only for its exact low-risk lane scope. No CI trigger, AWS/S3 contact, EC2 start, generation, mask, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-007 / ITEM-W64-007`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Implemented split-state repo/EC2/S3 architecture contract and direct blocker evidence.", "; ".join(evidence_paths), "20/20 checks; static pass; current live CI/S3/TTL blocked", payload["qa_decision"], rel(canonical), "Proceed to TRK-W64-007 / ITEM-W64-007."])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": gate_states, "checks": payload["check_summary"], "blockers": blockers, "historical_runtime_scope": payload["historical_runtime_scope"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
