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
TRK, ITEM = "TRK-W64-005", "ITEM-W64-005"
STATUS = "Completed_Local_First_Runtime_Strategy_Contract_Pass_Project_Incomplete"
GATES = ["local_preflight", "low_vram_policy", "ec2_final_proof_boundary", "no_false_equivalence"]


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


def normalize_row_note(path: Path, key: str, expected: str, prefix: str, note: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames or [], list(reader)
    for row in rows:
        if row.get(key) != expected or "Notes" not in fields:
            continue
        entries = [entry.strip() for entry in row.get("Notes", "").split(";") if entry.strip()]
        entries = [entry for entry in entries if not entry.startswith(prefix) and not entry.startswith("verified local static pass, bounded --lowvram")]
        entries.append(note)
        row["Notes"] = "; ".join(entries)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row005 Local-First Runtime Validation Strategy"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "local_first_runtime_strategy.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("LOCAL_FIRST_RUNTIME_STRATEGY_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    strategy_path = PLAN / "02_TARGET_ARCHITECTURE/LOCAL_FIRST_RUNTIME_VALIDATION_STRATEGY.md"
    contract_path = PLAN / "10_REGISTRIES/local_first_runtime_validation_contract.json"
    architecture_path = PLAN / "10_REGISTRIES/end_to_end_architecture_boundary_registry.json"
    preflight_path = PLAN / "Instructions/QA/Evidence/Runtime_Readiness/W64_LOCAL_COMFY_DEV_PREFLIGHT_SDXL_LOW_RISK_20260708T232400-0500.json"
    dryrun_path = PLAN / "Instructions/QA/Evidence/Runtime_Readiness/W64_LOCAL_COMFY_DEV_START_DRY_RUN_LOWVRAM_20260708T232500-0500.json"
    full_ready_path = PLAN / "Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_DEV_PREFLIGHT_FULL_READY_20260706T204500-0500.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    authority_path = PLAN / "Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md"
    strategy = strategy_path.read_text(encoding="utf-8-sig")
    contract, architecture = load(contract_path), load(architecture_path)
    preflight, dryrun, full_ready, queue = load(preflight_path), load(dryrun_path), load(full_ready_path), load(queue_path)
    authority = authority_path.read_text(encoding="utf-8-sig")
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    policy = architecture["local_runtime_validation_policy"]
    lanes = queue["lanes"]
    checks = {
        "LFR-001_row005_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "LFR-002_strategy_primary_rule": "Do as much validation locally as possible before EC2 is started" in strategy,
        "LFR-003_strategy_machine_contract_link": rel(contract_path) in strategy,
        "LFR-004_strategy_equivalence_matrix": all(token in strategy for token in ("Local static preflight", "Local object-info", "Local low-VRAM smoke", "Target-runtime proof")),
        "LFR-005_strategy_low_vram_and_ec2_sections": "## Low-VRAM execution policy" in strategy and "## EC2 final-proof boundary" in strategy,
        "LFR-006_contract_schema_identity": contract["schema_version"] == "1.0" and contract["contract_id"] == "wave64_local_first_runtime_validation" and contract["tracker_id"] == TRK and contract["item_id"] == ITEM,
        "LFR-007_gate_order_exact": contract["checks_required"] == GATES and list(contract["checks"]) == GATES,
        "LFR-008_preflight_local_only": preflight["local_only"] is True and preflight["ec2_started"] is False and preflight["generation_executed"] is False,
        "LFR-009_preflight_static_pass": preflight["static_validation"]["qa_status"] == "pass" and preflight["static_validation"]["defect_count"] == 0 and preflight["failed_check_count"] == 0,
        "LFR-010_preflight_no_false_equivalence": preflight["local_dev_replaces_ec2_final_proof"] is False and preflight["ec2_final_proof_still_required"] is True,
        "LFR-011_dryrun_operation_and_scope": dryrun["operation"] == "start_local_comfyui_dev" and dryrun["local_only"] is True and dryrun["execute"] is False,
        "LFR-012_dryrun_low_vram_command": dryrun["low_vram_args_enabled"] is True and "--lowvram" in dryrun["command"] and dryrun["host"] == "127.0.0.1",
        "LFR-013_dryrun_gpu_recorded": dryrun["local_gpu"]["nvidia_smi_found"] is True and dryrun["local_gpu"]["memory_total_mib"] == 8151,
        "LFR-014_dryrun_no_external_or_runtime": all(dryrun[key] is False for key in ("aws_contacted", "github_api_contacted", "civitai_contacted", "ec2_started", "generation_executed")),
        "LFR-015_full_ready_scope_consistent": full_ready["local_only"] is True and full_ready["failed_check_count"] == 0 and full_ready["local_dev_replaces_ec2_final_proof"] is False and full_ready["ec2_final_proof_still_required"] is True,
        "LFR-016_architecture_anti_equivalence": policy["local_runtime_evidence_equates_target_runtime"] is False and policy["local_smoke_implies_final_certification"] is False and policy["failed_local_static_validation_allows_ec2_bypass"] is False,
        "LFR-017_ec2_non_authority_and_stopped": architecture["boundaries"]["ec2"]["planning_authority"] is False and architecture["boundaries"]["ec2"]["required_terminal_state"] == "stopped" and "EC2 workspace is runtime/cache state only" in authority,
        "LFR-018_queue_current_ten_lanes_bounded": len(lanes) == 10 and len({lane["lane_id"] for lane in lanes}) == 10 and all(lane.get("required_next_runtime_gate") and lane.get("promotion_rule") for lane in lanes),
        "LFR-019_queue_manifest_denies_live_action": queue["runtime_boundary"]["ec2_start_allowed_by_queue_file"] is False and queue["runtime_boundary"]["generation_allowed_by_queue_file"] is False,
        "LFR-020_contract_grants_no_action_or_completion": all(contract[key] is False for key in ("runtime_action_allowed", "ec2_start_allowed", "generation_allowed", "promotion_allowed", "full_project_completion_implied")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed local-first-runtime invariants: " + ", ".join(failed))
    groups = {
        "local_preflight": [name for name in checks if name.startswith(("LFR-001", "LFR-002", "LFR-003", "LFR-008", "LFR-009", "LFR-015"))],
        "low_vram_policy": [name for name in checks if name.startswith(("LFR-004", "LFR-005", "LFR-011", "LFR-012", "LFR-013", "LFR-014"))],
        "ec2_final_proof_boundary": [name for name in checks if name.startswith(("LFR-006", "LFR-007", "LFR-017", "LFR-018", "LFR-019"))],
        "no_false_equivalence": [name for name in checks if name.startswith(("LFR-010", "LFR-016", "LFR-020"))],
    }
    stamped = QA / f"LOCAL_FIRST_RUNTIME_STRATEGY_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "local_first_runtime_strategy_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-005_local_first_runtime_strategy.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": True, "qa_decision": "local_first_runtime_contract_pass_project_incomplete",
        "validation_gates": {gate: {"pass": True, "checks": groups[gate]} for gate in GATES},
        "local_preflight": {"lane_id": preflight["lane_id"], "result": preflight["result"], "failed_check_count": 0, "local_only": True},
        "low_vram_policy": {"gpu": dryrun["local_gpu"], "host": dryrun["host"], "execute": False, "low_vram_args_enabled": True},
        "equivalence_boundary": {"local_dev_replaces_ec2_final_proof": False, "ec2_final_proof_still_required": True, "local_smoke_implies_final_certification": False},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"aws_contacted": False, "ec2_started": False, "generation_executed": False, "runtime_promoted": False, "queue_modified": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (strategy_path, contract_path, architecture_path, preflight_path, dryrun_path, full_ready_path, queue_path, authority_path)],
        "next_action": "Proceed in strict sequence to TRK-W64-006 / ITEM-W64-006 repo/EC2/S3 architecture; keep EC2 stopped and live/runtime gates fail-closed.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_policy_scope_only", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "local_preflight": payload["local_preflight"], "low_vram_policy": payload["low_vram_policy"], "equivalence_boundary": payload["equivalence_boundary"], "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})
    note_prefix = f"Wave64 Row005 {stamp}: implemented four-gate local-first contract"
    note = f"{note_prefix}, verified local static pass, bounded --lowvram dry-run on 8151 MiB GPU, EC2 final-proof boundary, no false equivalence, and 20/20 checks."
    tags = ["wave64_row005_local_first_contract_pass", "low_vram_policy_bound", "ec2_final_proof_preserved", "no_false_equivalence", "row006_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    for path in tracker_paths:
        normalize_row_note(path, "Tracker_ID", TRK, note_prefix, note)
    for path in item_paths:
        normalize_row_note(path, "Item_ID", ITEM, note_prefix, note)
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in tracker_paths]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row005 Local-First Runtime Validation Strategy - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. A canonical four-gate contract now binds local preflight, low-VRAM command policy, the EC2 final-proof boundary, and explicit no-false-equivalence rules. The audit verified zero-failure local static evidence, a non-executing localhost `--lowvram` plan on the recorded 8,151 MiB GPU, current ten-lane bounded queue controls, EC2 non-authority/stopped-state policy, and 20/20 checks. Local evidence remains local-scope only and does not become target-runtime, promotion, release, or project-completion proof. No AWS, EC2, generation, queue mutation, mask, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-006 / ITEM-W64-006` repo/EC2/S3 architecture.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Implemented and audited local-first runtime and evidence-equivalence controls.", "; ".join(evidence_paths), "20/20 checks; low-VRAM dry-run; EC2 boundary preserved", payload["qa_decision"], rel(canonical), "Proceed to TRK-W64-006 / ITEM-W64-006."])
    print(json.dumps({"status": STATUS, "gates": {gate: True for gate in GATES}, "checks": payload["check_summary"], "preflight": payload["local_preflight"], "low_vram": payload["low_vram_policy"], "equivalence": payload["equivalence_boundary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
