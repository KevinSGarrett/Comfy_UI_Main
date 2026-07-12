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
TRK = "TRK-W64-066"
ITEM = "ITEM-W64-066"
STATUS = "Completed_Current_Future_Lane_Module_Promotion_Control_Pass_No_Promotion_Executed"
GATES = ["objective_declared", "lane_queue_update", "model_registry", "run_package", "runtime_proof", "runtime_gate"]


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
    marker = "## Wave64 Row066 Future Lane And Module Promotion Rule"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "future_lane_promotion.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("FUTURE_LANE_PROMOTION_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")
    policy_path = PLAN / "10_REGISTRIES/future_lane_module_promotion_policy.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    active_path = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
    model_registry = PLAN / "Registries/Models/model_registry.jsonl"
    failure_control = QA / "failure_classification_rerun.json"
    terminal_state = QA / "realvisxl_lane_terminal_state.json"
    policy, queue, active = load(policy_path), load(queue_path), load(active_path)
    queue_lanes, active_lanes = queue["lanes"], active["lanes"]
    model_rows = []
    for line_number, line in enumerate(model_registry.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            model_rows.append(json.loads(line))
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    queue_ids = [lane["lane_id"] for lane in queue_lanes]
    active_ids = [lane["lane_id"] for lane in active_lanes]
    parity = [
        {
            "order": q["order"], "lane_id": q["lane_id"], "status": q["status"],
            "required_next_runtime_gate": q["required_next_runtime_gate"],
            "promotion_rule": q["promotion_rule"],
            "active_status_match": q["status"] == a["status"],
            "active_next_gate_match": q["required_next_runtime_gate"] == a["next_gate"],
        }
        for q, a in zip(queue_lanes, active_lanes)
    ]
    checks = {
        "FLP-001_row066_tracker_contract_present": len(tracker_rows) == 1 and set(tracker_rows[0]["Validation_Method"].split("|")) == set(GATES),
        "FLP-002_policy_schema_and_id": policy["schema_version"] == "1.0" and policy["policy_id"] == "wave64_future_lane_module_promotion_policy",
        "FLP-003_gate_order_exact": policy["required_gate_order"] == GATES,
        "FLP-004_six_gate_objects_present": list(policy["gates"]) == GATES,
        "FLP-005_gate_fields_nonempty": all(policy["gates"][gate]["required_fields"] and policy["gates"][gate]["pass_rule"] for gate in GATES),
        "FLP-006_default_decision_deny": policy["default_promotion_decision"] == "deny",
        "FLP-007_current_decision_no_request": policy["current_promotion_decision"] == "deny_no_promotion_request" and policy["current_selected_lane_id"] is None and policy["current_promotion_request_id"] is None,
        "FLP-008_promotion_not_allowed": policy["promotion_allowed"] is False,
        "FLP-009_same_scope_invariant_present": all(term in policy["same_scope_invariant"] for term in ("six gates", "promotion_request_id", "selected_lane_id")),
        "FLP-010_exact_ten_queue_lanes": len(queue_lanes) == 10 and len(set(queue_ids)) == 10,
        "FLP-011_exact_ten_active_lanes": len(active_lanes) == 10 and len(set(active_ids)) == 10,
        "FLP-012_queue_active_order_parity": queue_ids == active_ids and [lane["order"] for lane in queue_lanes] == [lane["order"] for lane in active_lanes],
        "FLP-013_queue_active_status_parity": all(row["active_status_match"] for row in parity),
        "FLP-014_queue_active_gate_parity": all(row["active_next_gate_match"] for row in parity),
        "FLP-015_all_queue_promotion_rules_present": all(lane.get("promotion_rule") and lane.get("required_next_runtime_gate") for lane in queue_lanes),
        "FLP-016_runtime_manifest_denies_execution": active["runtime_boundaries"]["ec2_start_allowed_by_this_manifest"] is False and active["runtime_boundaries"]["generation_allowed_by_this_manifest"] is False,
        "FLP-017_model_registry_exact_15_rows": len(model_rows) == 15,
        "FLP-018_change_control_fail_closed": all(policy["change_control"][key] is True for key in ("preserve_passed_evidence", "no_broad_rerun", "targeted_rerun_requires_material_change", "completed_terminal_chain_reuse_required", "single_lane_mutation_only", "historical_evidence_append_only", "promotion_request_must_supersede_explicitly")),
        "FLP-019_prior_controls_preserved": load(failure_control)["row_complete"] is True and load(terminal_state)["terminal_chain"]["no_rerun"] is True,
        "FLP-020_no_promotion_or_external_action": all(value is False for value in policy["authority_boundaries"].values()),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed promotion-control invariants: " + ", ".join(failed))

    stamped = QA / f"FUTURE_LANE_PROMOTION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "future_lane_promotion_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-066_future_lane_promotion.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso,
        "wave": 64, "tracker_id": TRK, "item_id": ITEM, "status": STATUS,
        "row_complete": True, "qa_decision": "promotion_control_pass_current_promotion_denied_no_request",
        "policy_path": rel(policy_path),
        "current_promotion_state": {"decision": policy["current_promotion_decision"], "promotion_allowed": False, "selected_lane_id": None, "promotion_request_id": None, "promoted_lane_count": 0},
        "required_gate_order": GATES,
        "queue_summary": {"queue_lane_count": len(queue_lanes), "active_lane_count": len(active_lanes), "ordered_parity": True, "runtime_enabled_by_manifests": False, "lane_ids": queue_ids},
        "lane_policy_index": parity,
        "model_registry_record_count": len(model_rows),
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"lane_selected": False, "lane_promoted": False, "queue_modified": False, "active_lanes_modified": False, "model_registry_modified": False, "runtime_executed": False, "aws_contacted": False, "ec2_started": False, "generation_executed": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (policy_path, queue_path, active_path, model_registry, failure_control, terminal_state)],
        "next_action": "Run a targeted Wave64 final end-to-end certification refresh because Rows061-066 now have direct evidence; keep release, runtime, masks, and Wave71+ fail-closed unless their exact gates pass.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_control_no_promotion", "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "current_promotion_state": payload["current_promotion_state"], "queue_summary": payload["queue_summary"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row066 {stamp}: implemented six-gate future promotion policy; verified 10/10 queue-to-active parity, {len(model_rows)} parseable model-registry records, default/current deny, zero selected or promoted lanes, and 20/20 checks."
    tags = ["wave64_row066_promotion_control_pass", "six_gate_policy_enforced", "ten_lane_parity", "current_promotion_denied", "zero_lanes_promoted", "targeted_final_cert_refresh_next"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row066 Future Lane And Module Promotion Rule - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. A machine-readable policy now requires all six gates (`objective_declared`, `lane_queue_update`, `model_registry`, `run_package`, `runtime_proof`, `runtime_gate`) to pass for the same request, lane, and scope before promotion. The audit verified exact 10/10 ordered queue-to-ACTIVE_LANES status/gate parity, parseable model-registry authority, lane-specific promotion rules, no-broad-rerun controls, and disabled runtime boundaries. The policy control passes while the current promotion decision remains `deny_no_promotion_request`: no lane was selected, modified, executed, or promoted. No AWS, EC2, generation, mask, Jira, or Wave71+ action occurred.

Next safe local action: targeted Wave64 final end-to-end certification refresh against direct Row061-066 evidence.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        already_recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not already_recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Implemented fail-closed future lane/module promotion policy.", "; ".join(evidence_paths), "20/20 checks; 10/10 parity; zero promotions", payload["qa_decision"], rel(canonical), "Refresh Wave64 final end-to-end certification."])
    print(json.dumps({"status": STATUS, "promotion": payload["current_promotion_state"], "queue": payload["queue_summary"], "model_registry_record_count": len(model_rows), "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
