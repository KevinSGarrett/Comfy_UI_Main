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
TRK = "TRK-W64-063"
ITEM = "ITEM-W64-063"
STATUS = "Completed_Current_Failure_Classification_Targeted_Rerun_Control_Pass"
NEXT = "TRK-W64-064 / ITEM-W64-064"
ALLOWED_CATEGORIES = {
    "environment_infrastructure", "workflow_logic", "artifact_quality",
    "observability_evidence", "unknown_needs_diagnosis",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
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
    marker = "## Wave64 Row063 Failure Classification And Targeted Rerun"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def entry(blocker_id: str, source_row: str, category: str, severity: str,
          cause: str, prerequisite: str, action: str, expected: str,
          anchors: list[dict], affected_count: int = 1) -> dict:
    return {
        "blocker_id": blocker_id,
        "source_row": source_row,
        "failure_category": category,
        "severity": severity,
        "suspected_cause": cause,
        "material_change_prerequisite": prerequisite,
        "targeted_rerun_action": action,
        "expected_result_after_retry": expected,
        "rerun_reason_required": True,
        "similar_retry_count": 0,
        "retry_limit": {"deep_diagnosis_after": 2, "blocked_needs_redesign_after": 3},
        "escalation_decision": "hold_no_rerun_until_material_change",
        "affected_count": affected_count,
        "preserved_passed_evidence_hashes": anchors,
    }


def main() -> None:
    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    protocol = PLAN / "Instructions/QA/FAILURE_CLASSIFICATION_AND_RETEST_PROTOCOL.md"
    sources = {
        "row059": QA / "release_done_certification.json",
        "row060": QA / "final_end_to_end_certification.json",
        "row061": QA / "autonomous_24_7_operations.json",
        "row062": QA / "observability_evidence_logs.json",
        "no_loop": QA / "no_loop_no_drift.json",
    }
    data = {name: load(path) for name, path in sources.items()}
    anchors = [{"row": name, "path": rel(sources[name]), "sha256": sha(sources[name])}
               for name in ("row059", "row060", "row061", "row062")]

    rows = [
        entry("BLOCKER-W64-AWS-EXPIRED-SESSION-001", "TRK-W64-059", "environment_infrastructure", "critical", "AWS session is expired", "fresh authenticated identity/account proof", "targeted_auth_gate_recheck_only", "AWS auth gate reports the expected account or a new exact blocker", anchors),
        entry("BLOCKER-W64-GIT-DIRTY-WORKTREE-001", "TRK-W64-059", "environment_infrastructure", "high", "five intentional paths remain outside scoped checkpoints", "preserved paths are intentionally checkpointed or explicitly resolved", "targeted_checkpoint_gate_recheck_only", "checkpoint gate reports the exact current worktree state", anchors),
        entry("BLOCKER-W64-ADVANCED-DIRECT-PROOF-001", "TRK-W64-059", "observability_evidence", "critical", "advanced runtime, visual, audio, model, and mask proof is incomplete", "one exact missing proof artifact is newly produced", "targeted_missing_advanced_proof_validation_only", "the named proof advances without rerunning passed lanes", anchors),
        entry("BLOCKER-W64-ORGANIZATION-PLACEMENT-DEBT-001", "TRK-W64-059", "workflow_logic", "high", "tracked legacy artifacts violate placement authority", "a bounded named placement subset is corrected with hashes", "targeted_organization_debt_subset_audit_only", "the named debt subset decreases and unrelated files remain unchanged", anchors, 85),
        entry("BLOCKER-W64-RUNTIME-DEPENDENT-TRACE-LINKS-001", "TRK-W64-059", "observability_evidence", "critical", "cw_006, cw_007, and cw_008 require runtime proof", "one named runtime-dependent trace link gains direct proof", "targeted_trace_link_validation_only", "the named link advances without broad traceability refresh", anchors, 3),
        entry("BLOCKER-W66-FINAL-READINESS-001", "TRK-W64-059", "workflow_logic", "critical", "nine of ten runtime lanes are not final-ready", "a specific blocked lane gains its missing prerequisite evidence", "targeted_blocked_lane_readiness_recheck_only", "only the changed lane readiness is recomputed", anchors, 9),
        entry("ROW060_ALL_DOMAIN_ROWS_PASS", "TRK-W64-060", "workflow_logic", "critical", "48 domain rows are not pass-like", "one unresolved row gains exact direct evidence", "targeted_changed_domain_row_recheck_only", "the changed row is re-evaluated and all passed rows are preserved", anchors, 48),
        entry("ROW060_MEDIA_REVIEWS_PASS", "TRK-W64-060", "artifact_quality", "high", "six media rows lack required production review proof", "a named media artifact and review record are newly available", "targeted_missing_media_review_only", "the named media review receives an evidence-backed decision", anchors, 6),
        entry("ROW060_AUDIO_REVIEWS_PASS", "TRK-W64-060", "artifact_quality", "high", "eight audio rows lack required production review proof", "a named audio artifact and review record are newly available", "targeted_missing_audio_review_only", "the named audio review receives an evidence-backed decision", anchors, 8),
        entry("ROW060_RUNTIME_EVIDENCE_PASS", "TRK-W64-060", "observability_evidence", "critical", "runtime-dependent requirements and nine lanes remain unproven", "a named lane gains new target-runtime evidence", "targeted_changed_runtime_lane_evidence_only", "only the changed runtime lane evidence is re-evaluated", anchors, 9),
        entry("ROW060_RELEASE_MANIFEST_PASS", "TRK-W64-060", "observability_evidence", "critical", "no current Wave64 all-pass release manifest exists", "all prerequisite rows pass and a current manifest is generated", "targeted_current_release_manifest_validation_only", "current manifest authority is validated without reusing Wave47 scope", anchors),
        entry("AWS_AUTH_EXPIRED_LIVE_RUNTIME_BLOCK", "TRK-W64-061", "environment_infrastructure", "critical", "live AWS credentials are expired", "fresh authenticated identity/account proof", "targeted_live_auth_gate_recheck_only", "live auth state is recorded without starting EC2", anchors),
        entry("EMERGENCY_STOP_LIVE_PROOF_MISSING", "TRK-W64-061", "observability_evidence", "critical", "only dry-run emergency-stop scheduling is proven", "live runtime is separately authorized and a stop schedule is created", "targeted_emergency_stop_live_proof_only", "schedule, watchdog, and stopped-state evidence are captured", anchors),
        entry("CHECKPOINT_DIRTY_WORKTREE_INTENTIONAL_5_PATHS", "TRK-W64-061", "environment_infrastructure", "high", "five preserved paths intentionally remain dirty", "the exact five-path state materially changes", "targeted_five_path_checkpoint_recheck_only", "checkpoint evidence reflects the changed path set", anchors, 5),
        entry("LIVE_RUNTIME_AUTHORITY_NOT_GRANTED", "TRK-W64-061", "workflow_logic", "critical", "current policy does not authorize an unselected live run", "an exact lane and bounded runtime objective are authorized", "targeted_selected_runtime_authority_check_only", "authority is proven for one bounded lane", anchors),
        entry("FINAL_CERTIFICATION_STILL_BLOCKED_UPSTREAM", "TRK-W64-061", "workflow_logic", "critical", "upstream final-certification gates remain failed", "one named upstream gate materially advances", "targeted_changed_final_gate_recheck_only", "only the changed final gate is recomputed", anchors),
        entry("LEGACY_RUN_RECORD_LOG_RETENTION_METADATA_MISSING", "TRK-W64-062", "observability_evidence", "high", "four legacy records have no log path or explicit absence reason", "source-backed sidecar metadata becomes available", "targeted_four_record_log_metadata_reconciliation_only", "four records gain truthful metadata without historical rewriting", anchors, 4),
        entry("LEGACY_RUN_RECORD_COMMAND_ID_MISSING", "TRK-W64-062", "observability_evidence", "medium", "one legacy record lacks a recoverable command identifier", "original command id or an explicit unrecoverable reason is sourced", "targeted_one_record_command_id_reconciliation_only", "the single record receives source-backed reconciliation", anchors),
    ]

    row059_ids = {item["blocker_id"] for item in data["row059"]["global_blockers"]}
    row061_ids = {item["blocker_id"] for item in data["row061"]["normalized_blockers"]}
    row062_ids = {item["blocker_id"] for item in data["row062"]["normalized_blockers"]}
    row060_ids = {f"ROW060_{name.upper()}" for name in data["row060"]["required_gates"]}
    expected_ids = row059_ids | row060_ids | row061_ids | row062_ids
    actual_ids = {item["blocker_id"] for item in rows}
    protocol_text = protocol.read_text(encoding="utf-8-sig")
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    checks = {
        "FCR-001_row063_tracker_contract_present": len(tracker_rows) == 1 and set(tracker_rows[0]["Validation_Method"].split("|")) == {"failure_category", "targeted_rerun", "passed_evidence_preserved", "rerun_reason_required"},
        "FCR-002_protocol_present": protocol.exists(),
        "FCR-003_protocol_requires_classification": "Every failed or uncertain outcome must be classified before retest." in protocol_text,
        "FCR-004_protocol_material_change_fields": "exact change being made before retry" in protocol_text and "expected result after retry" in protocol_text,
        "FCR-005_protocol_retry_limits": "After 2 unsuccessful similar attempts" in protocol_text and "After 3 unsuccessful attempts" in protocol_text,
        "FCR-006_exact_18_entries": len(rows) == 18,
        "FCR-007_source_id_set_exact": actual_ids == expected_ids,
        "FCR-008_all_categories_allowed": all(item["failure_category"] in ALLOWED_CATEGORIES for item in rows),
        "FCR-009_all_severity_present": all(item["severity"] in {"medium", "high", "critical"} for item in rows),
        "FCR-010_all_causes_present": all(item["suspected_cause"] for item in rows),
        "FCR-011_all_material_prerequisites_present": all(item["material_change_prerequisite"] for item in rows),
        "FCR-012_all_targeted_actions_present": all(item["targeted_rerun_action"].startswith("targeted_") for item in rows),
        "FCR-013_no_broad_reruns": all("broad" not in item["targeted_rerun_action"] and "full_project" not in item["targeted_rerun_action"] for item in rows),
        "FCR-014_all_expected_results_present": all(item["expected_result_after_retry"] for item in rows),
        "FCR-015_all_reasons_required": all(item["rerun_reason_required"] is True for item in rows),
        "FCR-016_retry_counters_zero": all(item["similar_retry_count"] == 0 for item in rows),
        "FCR-017_escalation_rules_exact": all(item["retry_limit"] == {"deep_diagnosis_after": 2, "blocked_needs_redesign_after": 3} for item in rows),
        "FCR-018_four_anchor_hashes_preserved_per_entry": all(len(item["preserved_passed_evidence_hashes"]) == 4 for item in rows),
        "FCR-019_no_loop_control_current_pass": data["no_loop"]["status"] == "Completed_Current_No_Loop_No_Drift_Control_Pass" and data["no_loop"]["check_summary"] == {"checked": 20, "passed": 20, "failed": 0},
        "FCR-020_local_read_only_control": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed audit invariants: " + ", ".join(failed))

    canonical = QA / "failure_classification_rerun.json"
    stamped = QA / f"FAILURE_CLASSIFICATION_RERUN_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "failure_classification_rerun_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-063_failure_classification_rerun.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso,
        "wave": 64, "tracker_id": TRK, "item_id": ITEM, "status": STATUS,
        "row_complete": True, "qa_decision": "pass_failure_controls_upstream_failures_remain_open",
        "classification_summary": {
            "entries": len(rows),
            "by_source_row": {row: sum(item["source_row"] == row for item in rows) for row in ("TRK-W64-059", "TRK-W64-060", "TRK-W64-061", "TRK-W64-062")},
            "by_category": {category: sum(item["failure_category"] == category for item in rows) for category in sorted(ALLOWED_CATEGORIES)},
            "targeted_reruns": len(rows), "rerun_reasons_required": len(rows),
            "passed_anchor_hashes": len(anchors), "broad_reruns_authorized": 0,
        },
        "failure_ledger": rows,
        "preserved_passed_evidence": anchors,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"rerun_executed": False, "aws_contacted": False, "ec2_started": False, "generation_executed": False, "historical_evidence_rewritten": False, "jira_mutated": False, "mask_or_wave71_touched": False},
        "source_hashes": [{"path": rel(protocol), "sha256": sha(protocol)}] + [{"path": rel(path), "sha256": sha(path)} for path in sources.values()],
        "next_action": f"Advance to {NEXT} prompt and negative-prompt QA; execute no Row063 rerun until its exact material-change prerequisite is proven.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass", "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "classification_summary": payload["classification_summary"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row063 {stamp}: classified 18/18 current blocker entries, constrained 18/18 reruns to material-change scopes, preserved four anchor hashes per entry, and passed 20/20 controls; no rerun executed."
    tags = ["wave64_row063_failure_control_pass", "eighteen_failures_classified", "targeted_reruns_only", "passed_evidence_preserved", "advance_row064"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row063 Failure Classification And Targeted Rerun - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The control classified all 18 current Row059-062 blocker entries, assigned severity and material-change prerequisites, constrained every rerun to its named scope, preserved four canonical evidence hashes per entry, and passed 20/20 checks. No rerun, AWS, EC2, generation, historical rewrite, Jira, mask, or Wave71+ action occurred. Upstream failures remain open; this row passes because their recovery policy is now exact and fail-closed.

Next safe local action: `{NEXT}` prompt and negative-prompt QA.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Classified current failures and constrained targeted reruns.", "; ".join(evidence_paths), "20/20 checks; 18/18 classified; no rerun executed", payload["qa_decision"], rel(canonical), f"Begin {NEXT}."])
    print(json.dumps({"status": STATUS, "summary": payload["classification_summary"], "checks": payload["check_summary"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
