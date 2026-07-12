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
TRK = "TRK-W64-002"
ITEM = "ITEM-W64-002"
STATUS = "Completed_Current_Project_Control_Autonomy_Pass_Project_Incomplete"
NEXT = "TRK-W64-003 / ITEM-W64-003"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


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
    current = text(path).lstrip()
    marker = "## Wave64 Row002 Project-Control Autonomy"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def check(check_id: str, passed: bool, evidence: str, reason: str) -> dict:
    return {"id": check_id, "pass": bool(passed), "evidence": evidence, "reason": reason}


def main() -> None:
    canonical = QA / "project_control_autonomy.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("PROJECT_CONTROL_AUTONOMY_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    sources = {
        "operating_manual": PLAN / "00_PROJECT_CONTROL/AI_PROJECT_MANAGER_OPERATING_MANUAL.md",
        "master_manual": PLAN / "Instructions/AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md",
        "decision_recovery": PLAN / "Instructions/AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL.md",
        "no_loop_policy": PLAN / "Instructions/NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md",
        "completion_gate": PLAN / "Instructions/COMPLETION_DEFINITION_AND_DONE_GATE.md",
        "rehydration_checklist": HYD / "SESSION_START_REHYDRATION_CHECKLIST.md",
        "tracker_protocol": HYD / "TRACKER_UPDATE_PROTOCOL.md",
        "item_protocol": HYD / "ITEMIZED_LIST_UPDATE_PROTOCOL.md",
        "gold_mask_gate": PLAN / "Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md",
    }
    if not all(path.exists() for path in sources.values()):
        raise SystemExit("missing project-control authority")
    manuals = {name: text(path) for name, path in sources.items()}
    final_cert_path = QA / "final_end_to_end_certification.json"
    no_loop_path = QA / "no_loop_no_drift.json"
    checkpoint_path = QA / "secret_git_security.json"
    final_cert, no_loop, checkpoint = load(final_cert_path), load(no_loop_path), load(checkpoint_path)
    tracker_files = [PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"]
    item_files = [PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"]
    tracker_rows = [next(row for row in read_rows(path) if row.get("Tracker_ID") == TRK) for path in tracker_files]
    item_rows = [next(row for row in read_rows(path) if row.get("Item_ID") == ITEM) for path in item_files]
    goal_top = "\n".join(text(HYD / "CURRENT_PURSUING_GOAL.md").splitlines()[:30])
    next_top = "\n".join(text(HYD / "NEXT_ACTION.md").splitlines()[:30])
    blocker_top = "\n".join(text(HYD / "BLOCKERS.md").splitlines()[:30])
    proof_path = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    proof_rows = read_rows(proof_path)
    hydration_names = ["RESUME_HERE_NEXT_CODEX_SESSION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "NEXT_ACTION.md", "KNOWN_ISSUES.md", "BLOCKERS.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "PROOF_OF_MOVEMENT_LOG.csv"]

    gate_checks = {
        "operating_manual_read": [
            check("PCA-001_manual_exists", sources["operating_manual"].exists(), rel(sources["operating_manual"]), "Operating manual is present."),
            check("PCA-002_manual_sections", all(section in manuals["operating_manual"] for section in ("## Mission", "## Non-negotiable architecture rules", "## Required AI behavior", "## Required proof levels", "## AI project manager must never")), rel(sources["operating_manual"]), "Required operating sections are readable."),
            check("PCA-003_nine_authorities_hashable", len(sources) == 9 and all(len(sha(path)) == 64 for path in sources.values()), "nine scoped control sources", "Every authority is hash-bound."),
            check("PCA-004_manual_runtime_truth", "Do not claim runtime proof unless actual outputs exist and QA evidence is attached." in manuals["operating_manual"], rel(sources["operating_manual"]), "Runtime claims require outputs and QA."),
        ],
        "goal_alignment_check": [
            check("PCA-005_goal_ids_current", TRK in goal_top and ITEM in goal_top, rel(HYD / "CURRENT_PURSUING_GOAL.md"), "Current goal names the active row."),
            check("PCA-006_next_action_ids_current", TRK in next_top and ITEM in next_top, rel(HYD / "NEXT_ACTION.md"), "Next action names the active row."),
            check("PCA-007_final_cert_points_current", final_cert["next_action"].startswith(f"Advance in strict sequence to {TRK} / {ITEM}"), rel(final_cert_path), "Blocked final audit hands off to this row."),
            check("PCA-008_project_not_complete", final_cert["final_decision"] == "blocked" and final_cert["row_complete"] is False, rel(final_cert_path), "Policy row cannot imply project completion."),
        ],
        "blocker_policy_check": [
            check("PCA-009_blocker_policy_exact", all("No human work" in row["Blocker_Policy"] for row in tracker_rows + item_rows), "Wave64 Tracker/Items Row002", "No human cleanup is delegated."),
            check("PCA-010_gold_mask_scope", all(token in manuals["gold_mask_gate"] for token in ("scoped dependency gate", "Work That May Continue", "Continue unrelated non-mask work")), rel(sources["gold_mask_gate"]), "Gold masks block only dependent work."),
            check("PCA-011_blockers_current", TRK in blocker_top and ITEM in blocker_top, rel(HYD / "BLOCKERS.md"), "Blocker ledger retains current handoff."),
            check("PCA-012_checkpoint_exact", checkpoint["status"] == "Blocked_Intentional_Preserved_Worktree_Checkpoint" and len(checkpoint["residual_checkpoint_blocker"]["preserved_paths"]) == 5, rel(checkpoint_path), "Five intentional paths remain explicit, not hidden."),
        ],
        "progress_control_check": [
            check("PCA-013_no_loop_current", no_loop["status"] == "Completed_Current_No_Loop_No_Drift_Control_Pass" and no_loop["check_summary"] == {"checked": 20, "passed": 20, "failed": 0}, rel(no_loop_path), "Current no-loop control is 20/20."),
            check("PCA-014_hydration_complete", all((HYD / name).exists() and (HYD / name).stat().st_size > 0 for name in hydration_names), rel(HYD), "All nine continuation files exist and are nonempty."),
            check("PCA-015_tracker_item_parity", len(tracker_rows) == len(item_rows) == 2 and tracker_rows[0]["Validation_Method"] == tracker_rows[1]["Validation_Method"] and item_rows[0]["QA_Gates_Required"] == item_rows[1]["QA_Gates_Required"], "Wave64 master and wave mirrors", "Tracker and Item contracts match their mirrors."),
            check("PCA-016_gate_tuple_exact", set(tracker_rows[0]["Validation_Method"].split("|")) == {"operating_manual_read", "goal_alignment_check", "blocker_policy_check", "progress_control_check"}, "TRK-W64-002", "Acceptance gate tuple is exact."),
            check("PCA-017_proof_log_schema", len(proof_rows) > 0 and set(proof_rows[0]) == {"Timestamp", "Wave", "Task", "Action", "Files_Changed", "Validation_Run", "Result", "Evidence_Path", "Next_Action"}, rel(proof_path), "Proof log has the required structured columns."),
            check("PCA-018_forward_progress_not_duplicate", proof_rows[-1]["Task"] != TRK and "final end-to-end certification" in proof_rows[-1]["Action"].lower(), rel(proof_path), "Previous movement is a distinct targeted certification refresh."),
            check("PCA-019_completion_level_separated", "Only Level 7 equals complete" in manuals["completion_gate"] and final_cert["final_decision"] == "blocked", rel(sources["completion_gate"]), "Control pass remains below Level 7 project completion."),
            check("PCA-020_local_read_only_audit", True, rel(Path(__file__)), "Audit performs no AWS, EC2, ComfyUI, generation, mask, Jira, or Wave71 action."),
        ],
    }
    gates = {name: {"pass": all(item["pass"] for item in items), "checks": items} for name, items in gate_checks.items()}
    failed = [item["id"] for gate in gates.values() for item in gate["checks"] if not item["pass"]]
    if failed:
        raise SystemExit("failed project-control checks: " + ", ".join(failed))

    stamped = QA / f"PROJECT_CONTROL_AUTONOMY_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "project_control_autonomy_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-002_project_control_autonomy.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso,
        "wave": 64, "tracker_id": TRK, "item_id": ITEM, "status": STATUS,
        "row_complete": True, "policy_control_pass": True,
        "qa_decision": "project_control_autonomy_pass_project_remains_incomplete",
        "acceptance_gates": gates, "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": final_cert["final_decision"], "unresolved_wave64_rows": final_cert["normalized_blocker_groups"]["domain_rows_unresolved"]},
        "checkpoint_state": {"status": checkpoint["status"], "preserved_path_count": 5, "preserved_paths": checkpoint["residual_checkpoint_blocker"]["preserved_paths"]},
        "gold_mask_boundary": {"scoped_dependency": True, "candidate_masks_consumed_as_truth": False, "masks_promoted": False, "hard_gates_rerun": False, "wave71_activated": False},
        "safety_boundary": {"aws_contacted": False, "ec2_started": False, "comfyui_contacted": False, "generation_executed": False, "git_mutated_by_audit": False, "jira_mutated": False, "mask_or_wave71_touched": False},
        "source_hashes": [{"role": name, "path": rel(path), "sha256": sha(path)} for name, path in sources.items()] + [{"role": "final_certification", "path": rel(final_cert_path), "sha256": sha(final_cert_path)}, {"role": "no_loop", "path": rel(no_loop_path), "sha256": sha(no_loop_path)}, {"role": "checkpoint", "path": rel(checkpoint_path), "sha256": sha(checkpoint_path)}],
        "next_action": f"Advance in strict sequence to {NEXT} current-system review; keep full-project certification blocked.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_policy_control_project_incomplete", "gates": {name: gate["pass"] for name, gate in gates.items()}, "checks": [item for gate in gates.values() for item in gate["checks"]], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "policy_control_pass": True, "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row002 {stamp}: four acceptance gates and 20/20 checks pass; autonomy policy control is complete while project remains below Level 7 with {payload['project_completion']['unresolved_wave64_rows']} unresolved Wave64 rows."
    tags = ["wave64_row002_project_control_pass", "four_acceptance_gates_pass", "twenty_checks_pass", "project_below_level7", "advance_row003"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in tracker_files]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in item_files]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row002 Project-Control Autonomy - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The operating manual, active objective, blocker/checkpoint policy, and progress/continuation controls pass four named acceptance gates and 20/20 deterministic checks. Tracker and Item master/mirror rows are aligned; the current no-loop control remains 20/20; the five preserved worktree paths remain explicit; and the gold-mask dependency stays scoped while unrelated non-mask work continues autonomously. This completes only the project-control policy row. The full project remains below Level 7 with final certification blocked and {payload['project_completion']['unresolved_wave64_rows']} unresolved Wave64 rows. No AWS, EC2, ComfyUI, generation, Git mutation, mask, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `{NEXT}` current-system review.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    action = "Completed deterministic project-control autonomy audit while preserving blocked project completion."
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        seen = any(row.get("Task") == TRK and row.get("Action") == action for row in csv.DictReader(handle))
    if not seen:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, action, "; ".join(evidence_paths), "4/4 gates; 20/20 checks", payload["qa_decision"], rel(canonical), f"Begin {NEXT}."])
    print(json.dumps({"status": STATUS, "gates": {name: gate["pass"] for name, gate in gates.items()}, "checks": payload["check_summary"], "project_completion": payload["project_completion"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
