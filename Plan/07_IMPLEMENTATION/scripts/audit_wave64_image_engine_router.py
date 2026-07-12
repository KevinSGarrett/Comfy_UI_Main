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
TRK, ITEM = "TRK-W64-009", "ITEM-W64-009"
STATUS = "Completed_Local_Router_Contract_Pass_Current_Lanes_Fail_Closed_Target_Runtime_Not_Certified"
DECISION = "local_router_contract_pass_current_lanes_fail_closed_target_runtime_not_certified"
GATES = ["model_compatibility_matrix", "object_info_check", "registry_hash_match", "router_decision_evidence"]


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


def rewrite_csv(path: Path, key: str, expected: str, changes: dict[str, object], note: str) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames or [], list(reader)
    base = (
        "AI-only operational row. Do not treat prose summary as completion; require structured evidence paths and pass/fail records. "
        "| Wave64 reconciliation 2026-07-09: status is generated from exact direct evidence when present; skip repeat local/AWS work unless source, evidence, or downstream gate changes."
    )
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        if "Notes" in fields:
            row["Notes"] = f"{base}; {note}"
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
    marker = "## Wave64 Row009 Image Engine Router Compatibility"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "image_engine_router.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_ENGINE_ROUTER_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    validations = sorted((PLAN / "Instructions/QA/Evidence/Engine_Router").glob("W64_IMAGE_ENGINE_ROUTER_ROW009_RECONCILIATION_*.json"))
    if not validations:
        raise SystemExit("Row009 reconciliation validation is missing")
    validation_path = validations[-1]
    validation = load(validation_path)
    named = {check["name"]: check for check in validation["checks"]}

    source_path = PLAN / "03_IMAGE_SYSTEM/ENGINE_ROUTER_SPEC.md"
    router_path = PLAN / "07_IMPLEMENTATION/scripts/resolve_wave64_image_engine_route.py"
    validator_path = PLAN / "Instructions/QA/Scripts/Test-ImageEngineRouter.ps1"
    matrix_path = PLAN / "10_REGISTRIES/wave15_model_family_compatibility_matrix.json"
    rules_path = PLAN / "10_REGISTRIES/wave06_engine_router_rules.json"
    active_path = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    registry_path = PLAN / "Registries/Models/model_registry.jsonl"
    example_path = PLAN / "09_EXAMPLES/wave64_image_engine_route_matrix_forbidden_sdxl_unproven_request.example.json"
    source = source_path.read_text(encoding="utf-8-sig")
    matrix, active, queue = load(matrix_path), load(active_path), load(queue_path)
    decisions = [ROOT / value for value in validation["decisions"].values()]
    decision_payloads = [load(path) for path in decisions]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    current_hashes = {rel(path): sha(path) for path in (active_path, queue_path, registry_path, matrix_path)}

    checks = {
        "IER-001_row009_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IER-002_source_documents_machine_contract": all(token in source for token in (rel(router_path), rel(matrix_path), rel(validator_path), "fail closed")),
        "IER-003_router_and_validator_present": router_path.is_file() and validator_path.is_file(),
        "IER-004_matrix_has_six_unique_families": len(matrix) == 6 and len({row["family_id"] for row in matrix}) == 6,
        "IER-005_rules_and_matrix_parse": isinstance(load(rules_path).get("hard_rules"), list) and isinstance(matrix, list),
        "IER-006_active_lane_count_current": len(active["lanes"]) == 10,
        "IER-007_runtime_queue_count_current": len(queue["lanes"]) == 10,
        "IER-008_validator_nineteen_checks_pass": len(validation["checks"]) == 19 and all(row["result"] == "pass" for row in validation["checks"]),
        "IER-009_validator_zero_failures": validation["failure_count"] == 0 and validation["result"] == "pass_local_only",
        "IER-010_three_decisions_exist": len(decisions) == 3 and all(path.is_file() for path in decisions),
        "IER-011_three_decisions_parse": len(decision_payloads) == 3,
        "IER-012_all_current_decisions_fail_closed": all(row["result"] == "block_local_only" for row in decision_payloads),
        "IER-013_no_current_lane_selected": all(row["selected_lane_id"] is None for row in decision_payloads),
        "IER-014_blocked_suffix_rejected": named["blocked_suffix_queue_status_rejected"]["result"] == "pass",
        "IER-015_pending_requirement_rejected": named["pending_requirement_status_rejected"]["result"] == "pass",
        "IER-016_realvisxl_checkpoint_matrix_allowed": named["realvisxl_checkpoint_allowed_by_matrix"]["result"] == "pass",
        "IER-017_matrix_forbidden_same_family_rejected": named["matrix_forbidden_same_normalized_family_is_rejected"]["result"] == "pass",
        "IER-018_current_proof_hashes_exact": decision_payloads[0]["proof_sources"] == current_hashes,
        "IER-019_no_external_runtime_or_generation": validation["local_only"] is True and validation["ec2_started"] is False and validation["generation_executed"] is False,
        "IER-020_matrix_regression_example_bound": example_path.is_file() and "matrix_forbidden" in validation["requests"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed image-engine router invariants: " + ", ".join(failed))

    groups = {
        "model_compatibility_matrix": ["IER-002", "IER-004", "IER-005", "IER-016", "IER-017"],
        "object_info_check": ["IER-006", "IER-007", "IER-008", "IER-014", "IER-015"],
        "registry_hash_match": ["IER-003", "IER-010", "IER-011", "IER-018", "IER-020"],
        "router_decision_evidence": ["IER-001", "IER-009", "IER-012", "IER-013", "IER-019"],
    }
    stamped = QA / f"IMAGE_ENGINE_ROUTER_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_engine_router_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-009_image_engine_router.json"
    blockers = [
        "all current image lanes fail closed for production selection under current certification-qualified statuses",
        "target-runtime and final lane certification remain outside this local router contract proof",
        "Flux1 remains blocked on local install, hash, license, and runtime proof",
    ]
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK,
        "item_id": ITEM, "status": STATUS, "row_complete": True, "qa_decision": DECISION,
        "validation_gates": {gate: {"status": "pass_local_fail_closed", "checks": groups[gate]} for gate in GATES},
        "current_route_state": {"active_lane_count": 10, "runtime_queue_lane_count": 10, "selected_lane_count": 0, "decision_count": 3, "all_decisions_fail_closed": True},
        "blockers": blockers, "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "source_validation": rel(validation_path), "decision_evidence": [rel(path) for path in decisions],
        "safety_boundary": {"comfyui_contacted": False, "generation_executed": False, "aws_contacted": False, "ec2_started": False, "mask_consumed_or_promoted": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, router_path, validator_path, matrix_path, rules_path, active_path, queue_path, registry_path, example_path, validation_path, *decisions)],
        "next_action": "Proceed to TRK-W64-010 / ITEM-W64-010 in strict sequence; preserve the current fail-closed router decision until a lane receives materially new certification evidence.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(validation_path), *[rel(path) for path in decisions]]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_local_fail_closed", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "current_route_state": payload["current_route_state"], "blockers": blockers, "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row009 {stamp}: router rejects blocked/pending pass-prefix statuses, enforces the Wave15 family matrix, records four current source hashes, and passes 20/20 local fail-closed audit checks; current production selections remain blocked pending materially new lane certification proof."
    tags = ["wave64_row009_router_contract_pass", "matrix_policy_enforced", "qualified_status_fail_closed", "current_lane_selection_blocked", "row010_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row009 Image Engine Router Compatibility - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The router now fails closed on negative status qualifiers even when a legacy pass prefix is present. It loads and enforces the Wave15 checkpoint/LoRA compatibility matrix and records hashes for the current active lanes, runtime queue, model registry, and matrix. The three-case regression and canonical audit pass 19/19 and 20/20 checks. All current production lane selections remain blocked under current certification-qualified statuses; no silent fallback occurred. No ComfyUI generation, AWS, EC2, mask use/promotion, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-010 / ITEM-W64-010`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Hardened the image-engine router and reconciled current compatibility proof.", "; ".join(evidence_paths), "19/19 regression checks; 20/20 canonical checks; zero current selections", DECISION, rel(canonical), "Proceed to TRK-W64-010 / ITEM-W64-010."])
    print(json.dumps({"status": STATUS, "row_complete": True, "regression_checks": {"checked": 19, "passed": 19, "failed": 0}, "audit_checks": payload["check_summary"], "current_route_state": payload["current_route_state"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
