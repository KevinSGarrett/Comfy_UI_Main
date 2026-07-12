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
TRK, ITEM = "TRK-W64-004", "ITEM-W64-004"
STATUS = "Completed_Target_Architecture_Contract_Pass_Project_Incomplete"
GATES = ["architecture_traceability", "interface_contracts", "runtime_boundary_check", "release_gate_mapping"]


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
    marker = "## Wave64 Row004 End-to-End Target Architecture"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "target_architecture.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("TARGET_ARCHITECTURE_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    architecture_path = PLAN / "02_TARGET_ARCHITECTURE/END_TO_END_ARCHITECTURE.md"
    registry_path = PLAN / "10_REGISTRIES/end_to_end_architecture_boundary_registry.json"
    strategy_path = PLAN / "02_TARGET_ARCHITECTURE/GITHUB_LOCAL_EC2_S3_DEVELOPMENT_STRATEGY.md"
    model_path = PLAN / "Registries/Models/model_registry.jsonl"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    active_path = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
    release_engine_path = PLAN / "02_TARGET_ARCHITECTURE/WAVE34_RELEASE_GATE_DECISION_ENGINE.md"
    release_decision_path = PLAN / "11_RELEASES/WAVE34_RELEASE_GATE_DECISION.json"
    done_path = PLAN / "Instructions/QA/DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md"
    architecture = architecture_path.read_text(encoding="utf-8-sig")
    registry, queue, active, release_decision = load(registry_path), load(queue_path), load(active_path), load(release_decision_path)
    strategy = strategy_path.read_text(encoding="utf-8-sig")
    release_engine = release_engine_path.read_text(encoding="utf-8-sig")
    done = done_path.read_text(encoding="utf-8-sig")
    model_rows = [json.loads(line) for line in model_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    boundary_names = list(registry["boundaries"])
    queue_ids = [lane["lane_id"] for lane in queue["lanes"]]
    active_ids = [lane["lane_id"] for lane in active["lanes"]]
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    checks = {
        "TAR-001_row004_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "TAR-002_registry_schema_and_id": registry["schema_version"] == "1.0" and registry["registry_id"] == "end_to_end_architecture_boundary_registry",
        "TAR-003_exact_nine_authority_domains": len(boundary_names) == 9 and boundary_names == registry["authority_order"],
        "TAR-004_required_domains_present": set(boundary_names) == {"local_project", "github", "model_registry", "s3", "ec2", "workflow_lanes", "qa_evidence", "release_gate", "done_certification"},
        "TAR-005_architecture_layers_present": all(token in architecture for token in ("App / input layer", "Planner layer", "Execution layer", "Evidence layer", "QA layer")),
        "TAR-006_architecture_boundary_table_present": all(token in architecture for token in ("| Local project |", "| GitHub |", "| S3 |", "| EC2 |", "| Done certification |")),
        "TAR-007_eight_step_cross_boundary_contract": all(f"{number}." in architecture for number in range(1, 9)),
        "TAR-008_local_authority_exact": registry["boundaries"]["local_project"]["authority"] == r"C:\Comfy_UI_Main",
        "TAR-009_github_lightweight_only": "model_binaries" in registry["boundaries"]["github"]["excludes"] and "secrets" in registry["boundaries"]["github"]["excludes"],
        "TAR-010_s3_not_planning_authority": registry["boundaries"]["s3"]["planning_authority"] is False and registry["boundaries"]["s3"]["full_library_sync_allowed"] is False,
        "TAR-011_ec2_gated_non_authority": registry["boundaries"]["ec2"]["planning_authority"] is False and len(registry["boundaries"]["ec2"]["required_gates"]) == 10 and registry["boundaries"]["ec2"]["required_terminal_state"] == "stopped",
        "TAR-012_model_registry_parseable": len(model_rows) == 15 and len(registry["boundaries"]["model_registry"]["required_before_hydration"]) == 7,
        "TAR-013_git_s3_ec2_strategy_consistent": all(token in strategy for token in ("S3 canonical model store", "EC2 GPU runtime cache", "Turn EC2 on only", "Stop EC2 automatically")),
        "TAR-014_lane_authority_exact": registry["boundaries"]["workflow_lanes"]["authority"] == [rel(queue_path), rel(active_path)],
        "TAR-015_current_ten_lane_parity": len(queue_ids) == 10 and queue_ids == active_ids,
        "TAR-016_manifests_deny_runtime": active["runtime_boundaries"]["ec2_start_allowed_by_this_manifest"] is False and active["runtime_boundaries"]["generation_allowed_by_this_manifest"] is False,
        "TAR-017_qa_existence_not_pass": registry["boundaries"]["qa_evidence"]["existence_is_pass"] is False,
        "TAR-018_release_gate_fail_closed": "If any required runtime proof is missing" in release_engine and release_decision["promotion_decision"] == "release_with_runtime_boundaries",
        "TAR-019_done_certification_complete_contract": len(registry["boundaries"]["done_certification"]["required"]) == 8 and "Absolute completion requirements" in done and registry["boundaries"]["done_certification"]["scope_inheritance_allowed"] is False,
        "TAR-020_no_runtime_promotion_or_completion": registry["runtime_action_allowed_by_registry"] is False and registry["promotion_allowed_by_registry"] is False and registry["full_project_completion_implied"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed target-architecture invariants: " + ", ".join(failed))

    groups = {
        "architecture_traceability": [name for name in checks if name.startswith(("TAR-001", "TAR-002", "TAR-003", "TAR-004", "TAR-005", "TAR-006", "TAR-007"))],
        "interface_contracts": [name for name in checks if name.startswith(("TAR-008", "TAR-009", "TAR-010", "TAR-011", "TAR-012", "TAR-013", "TAR-014"))],
        "runtime_boundary_check": [name for name in checks if name.startswith(("TAR-015", "TAR-016", "TAR-017", "TAR-020"))],
        "release_gate_mapping": [name for name in checks if name.startswith(("TAR-018", "TAR-019"))],
    }
    stamped = QA / f"TARGET_ARCHITECTURE_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "target_architecture_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-004_target_architecture.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": True, "qa_decision": "target_architecture_contract_pass_project_incomplete",
        "validation_gates": {gate: {"pass": True, "checks": groups[gate]} for gate in GATES},
        "authority_domains": boundary_names,
        "current_runtime_boundary": {"queue_lanes": len(queue_ids), "active_lanes": len(active_ids), "ordered_parity": True, "runtime_enabled_by_manifests": False},
        "release_boundary": {"historical_decision": release_decision["promotion_decision"], "missing_proof_fails_closed": True, "done_certification_scope_inheritance": False},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"aws_contacted": False, "ec2_started": False, "s3_mutated": False, "github_mutated_by_audit": False, "generation_executed": False, "promotion_executed": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (architecture_path, registry_path, strategy_path, model_path, queue_path, active_path, release_engine_path, release_decision_path, done_path)],
        "next_action": "Proceed in strict sequence to TRK-W64-005 / ITEM-W64-005; keep runtime, release, masks, and Wave71+ fail-closed.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_contract_only", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "authority_domains": boundary_names, "runtime_boundary": payload["current_runtime_boundary"], "release_boundary": payload["release_boundary"], "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row004 {stamp}: implemented nine-domain architecture boundary registry and eight-step interface contract; verified 10/10 current lane parity, 15 model rows, fail-closed runtime/release/done boundaries, and 20/20 checks."
    tags = ["wave64_row004_target_architecture_pass", "nine_authority_domains", "runtime_fail_closed", "release_and_done_scope_control", "row005_next"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row004 End-to-End Target Architecture - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The target architecture now has a machine-readable nine-domain authority registry and an eight-step cross-boundary contract covering local, GitHub, model registry, S3, EC2, workflow lanes, QA evidence, release gates, and done certification. The audit verified 10/10 queue-to-ACTIVE_LANES parity, 15 parseable model records, EC2/S3 non-authority, runtime disabled by current manifests, existence-not-pass QA, and scoped fail-closed release/certification behavior with 20/20 checks. This completes the architecture contract row only; the full project remains below Level 7 and final certification stays blocked. No AWS, EC2, S3, runtime, generation, promotion, mask, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-005 / ITEM-W64-005`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Implemented and audited the end-to-end architecture authority contract.", "; ".join(evidence_paths), "20/20 checks; nine domains; 10/10 lanes; 15 model rows", payload["qa_decision"], rel(canonical), "Proceed to TRK-W64-005 / ITEM-W64-005."])
    print(json.dumps({"status": STATUS, "gates": {gate: True for gate in GATES}, "checks": payload["check_summary"], "domains": boundary_names, "runtime": payload["current_runtime_boundary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
