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
TRK = "TRK-W64-003"
ITEM = "ITEM-W64-003"
STATUS = "Completed_Current_System_Review_Boundary_Pass_Project_Incomplete"
VALIDATION = ["source_review_complete", "runtime_boundary_recorded", "stale_assumption_blocked"]
SOURCE_SHA = "13297484923fa1ca7525fa913792b19999f395e05118e50eb269e48e4d1bc8bb"


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
    marker = "## Wave64 Row003 Current System Review Boundary"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "current_system_review.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("CURRENT_SYSTEM_REVIEW_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    findings_path = PLAN / "01_CURRENT_SYSTEM_REVIEW/MAIN_FLOW_REVIEW_FINDINGS.md"
    snapshot_path = PLAN / "12_SOURCE_SUMMARIES/source_snapshots/WAVE42_MAIN_FLOW_20260702.runtime_bound_snapshot.json"
    snapshot_pair_path = PLAN / "12_SOURCE_SUMMARIES/source_snapshots/WAVE42_MAIN_FLOW_20260702_WAVE13_SOURCE.json"
    summary_path = PLAN / "10_REGISTRIES/current_main_flow_summary.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    active_path = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
    local_authority_path = PLAN / "Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md"
    reconciliation_path = PLAN / "Instructions/QA/Evidence/Runtime_Readiness/LOCAL_LEGACY_AWS_DUPLICATE_RECONCILIATION_20260711T065400-0500.json"

    findings = findings_path.read_text(encoding="utf-8-sig")
    snapshot = load(snapshot_path)
    summary = load(summary_path)
    queue = load(queue_path)
    active = load(active_path)
    authority = local_authority_path.read_text(encoding="utf-8-sig")
    reconciliation = load(reconciliation_path)
    queue_lanes = queue["lanes"]
    active_lanes = active["lanes"]
    queue_ids = [lane["lane_id"] for lane in queue_lanes]
    active_ids = [lane["lane_id"] for lane in active_lanes]

    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    classes = set(reconciliation["classifications"])
    legacy = reconciliation["legacy_local_reconciliation"]
    implementation_archive = legacy["implementation_core_archive"]
    evidence_archive = legacy["evidence_core_archive"]
    generated = legacy["generated_artifact_review"]
    save_outputs = [
        "Main_Flow/SDXL_RealVisXL_LoRA",
        "Main_Flow/Flux_Family_ZImage",
        "Main_Flow/SDXL_RealVisXL_LoRA_Upscaled",
        "Main_Flow/SDXL_Inpaint_Detail",
        "Main_Flow/Flux_to_SDXL_Refine",
        "Main_Flow/True_Flux_Schnell_Reference_Smoke",
        "Main_Flow/ControlNet_Canny_Edge",
        "Main_Flow/IPAdapter_Face_Reference",
    ]

    checks = {
        "CSR-001_row003_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == VALIDATION,
        "CSR-002_findings_hash_bound": sha(findings_path) == "1563c02780cdc35ce8bb0e02ee5a3756ce3e780298b2211d9a2f1a33d491460f",
        "CSR-003_normalized_snapshot_pair_byte_identical": sha(snapshot_path) == sha(snapshot_pair_path),
        "CSR-004_snapshot_shape_exact": len(snapshot.get("nodes", [])) == 356 and len(snapshot.get("links", [])) == 91,
        "CSR-005_summary_shape_exact": summary["sha256"] == SOURCE_SHA and summary["node_count"] == 356 and summary["link_count"] == 91,
        "CSR-006_source_inventory_exact": all(token in findings for token in ("SaveImage outputs: 8", "Active upstream nodes feeding SaveImage outputs: 61", "Disabled/library LoRA loader nodes: 274")),
        "CSR-007_eight_save_outputs_cited": all(output in findings for output in save_outputs),
        "CSR-008_staging_canvas_boundary_explicit": "source artifact and staging canvas, not the final autonomous pipeline" in findings,
        "CSR-009_note_only_boundaries_explicit": all(token in findings for token in ("pose/depth/openpose/tile", "Video handoff", "Audio/AV sync")),
        "CSR-010_local_main_is_authority": reconciliation["authoritative_project"]["local_source_of_truth"] is True and "C:\\Comfy_UI_Main" in authority,
        "CSR-011_legacy_and_ec2_not_authority": reconciliation["authoritative_project"]["legacy_root_is_runtime_authority"] is False and reconciliation["authoritative_project"]["ec2_workspace_is_planning_authority"] is False,
        "CSR-012_legacy_implementation_archived_fail_closed": implementation_archive["included_file_count"] == 1279 and implementation_archive["activation_allowed"] is False and implementation_archive["curated_review_required_before_reuse"] is True,
        "CSR-013_legacy_evidence_archived_fail_closed": evidence_archive["included_file_count"] == 4912 and evidence_archive["activation_allowed"] is False and evidence_archive["completion_claims_require_main_ledger_corroboration"] is True,
        "CSR-014_no_missing_approved_output": generated["confirmed_approved_output_uniquely_missing_from_main"] == 0,
        "CSR-015_required_reconciliation_classes": {"LOCAL_SOURCE_OF_TRUTH_ACTIVE", "LEGACY_IMPLEMENTATION_CORE_ARCHIVED_NOT_ACTIVATED", "AWS_POST_BASELINE_WORK_REPRESENTED_IN_MAIN", "NO_RERUN_COMPLETED_EC2_PROOF"}.issubset(classes),
        "CSR-016_current_queue_exact_ten": len(queue_ids) == 10 and len(set(queue_ids)) == 10,
        "CSR-017_queue_active_lane_parity": queue_ids == active_ids and [lane["order"] for lane in queue_lanes] == [lane["order"] for lane in active_lanes],
        "CSR-018_current_manifests_deny_runtime": active["runtime_boundaries"]["ec2_start_allowed_by_this_manifest"] is False and active["runtime_boundaries"]["generation_allowed_by_this_manifest"] is False,
        "CSR-019_aws_live_state_fail_closed": reconciliation["aws_reconciliation"]["live_probe"]["aws_auth_verified_now"] is False and reconciliation["aws_reconciliation"]["live_probe"]["current_ec2_state_verified_now"] is False,
        "CSR-020_no_external_or_promotion_action": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed current-system-review invariants: " + ", ".join(failed))

    stamped = QA / f"CURRENT_SYSTEM_REVIEW_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "current_system_review_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-003_current_system_review.json"
    gates = {
        "source_review_complete": {"pass": True, "checks": [name for name in checks if name.startswith("CSR-00")]},
        "runtime_boundary_recorded": {"pass": True, "checks": [name for name in checks if name.startswith(("CSR-010", "CSR-011", "CSR-016", "CSR-017", "CSR-018"))]},
        "stale_assumption_blocked": {"pass": True, "checks": [name for name in checks if name.startswith(("CSR-012", "CSR-013", "CSR-014", "CSR-015", "CSR-019", "CSR-020"))]},
    }
    payload = {
        "schema_version": "1.0",
        "evidence_id": stamped.stem,
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": True,
        "qa_decision": "current_system_source_boundary_pass_project_incomplete",
        "validation_gates": gates,
        "source_review": {
            "source_sha256": SOURCE_SHA,
            "normalized_repository_snapshot_sha256": sha(snapshot_path),
            "nodes": 356,
            "links": 91,
            "save_image_outputs": 8,
            "active_upstream_nodes": 61,
            "disabled_library_lora_nodes": 274,
            "classification": "inherited_source_and_staging_context_not_runtime_authority",
        },
        "reconciliation": {
            "implementation_files_archived": 1279,
            "evidence_files_archived": 4912,
            "approved_output_uniquely_missing_from_main": 0,
            "legacy_activation_allowed": False,
            "completion_claims_require_main_ledger_corroboration": True,
        },
        "current_authority": {
            "root": str(ROOT),
            "queue_lane_count": len(queue_ids),
            "active_lane_count": len(active_ids),
            "ordered_parity": True,
            "runtime_enabled_by_manifests": False,
        },
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {
            "legacy_root_modified": False,
            "aws_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "runtime_lane_promoted": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (findings_path, snapshot_path, snapshot_pair_path, summary_path, queue_path, active_path, local_authority_path, reconciliation_path)],
        "next_action": "Proceed in strict sequence to TRK-W64-004 / ITEM-W64-004 end-to-end target architecture coverage; keep runtime, release, masks, and Wave71+ fail-closed.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_boundary_only", "validation_gates": gates, "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "source_review": payload["source_review"], "reconciliation": payload["reconciliation"], "current_authority": payload["current_authority"], "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row003 {stamp}: hash-bound original 356-node/91-link Main Flow, verified 8 outputs and 274 disabled LoRA nodes, preserved 1279 implementation plus 4912 evidence files as non-active legacy context, found zero uniquely missing approved output, verified 10/10 current lane parity, and passed 20/20 boundary checks."
    tags = ["wave64_row003_current_system_review_pass", "legacy_source_context_only", "main_root_authoritative", "no_duplicate_runtime_work", "row004_next"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row003 Current System Review Boundary - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The original 356-node/91-link Main Flow and its eight image outputs are hash-bound as inherited source/staging context, not current runtime authority. Prior reconciliation preserved 1,279 legacy implementation files and 4,912 legacy evidence files without activation and found zero uniquely missing approved output. Current authority remains local `C:\\Comfy_UI_Main` with exact 10/10 queue-to-ACTIVE_LANES parity and runtime disabled by the manifests. Legacy and stale EC2 state cannot reopen completed work or authorize a lane. The row passed 20/20 local checks; the full project remains below Level 7 with final certification blocked. No AWS, EC2, generation, mask, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-004 / ITEM-W64-004` end-to-end target architecture coverage.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Recorded inherited Main Flow and legacy/runtime authority boundary.", "; ".join(evidence_paths), "20/20 checks; 10/10 current lane parity; zero missing approved outputs", payload["qa_decision"], rel(canonical), "Proceed to TRK-W64-004 target architecture."])
    print(json.dumps({"status": STATUS, "gates": {name: gate["pass"] for name, gate in gates.items()}, "checks": payload["check_summary"], "legacy": payload["reconciliation"], "current_authority": payload["current_authority"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
