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
TRK, ITEM = "TRK-W64-008", "ITEM-W64-008"
STATUS = "Blocked_End_To_End_Image_Promotion_Planner_And_Local_Stages_Pass"
GATES = ["workflow_template_valid", "prompt_request_valid", "image_artifact_manifest", "promotion_gate"]


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


def normalize_row_note(path: Path, key: str, expected: str, note: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames or [], list(reader)
    for row in rows:
        if row.get(key) != expected or "Notes" not in fields:
            continue
        base = "AI-only operational row. Do not treat prose summary as completion; require structured evidence paths and pass/fail records. | Wave64 reconciliation 2026-07-09: no exact direct row evidence found; do not infer completion from rollups, mentions, Wave65 planned rows, Wave70 supporting evidence, local artifacts, or AWS artifacts without matching item/tracker id."
        row["Notes"] = f"{base}; {note}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row008 Image Pipeline Blueprint Implementation"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "image_pipeline_build.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_PIPELINE_BUILD_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")
    source_path = PLAN / "03_IMAGE_SYSTEM/IMAGE_PIPELINE_BLUEPRINT.md"
    contract_path = PLAN / "10_REGISTRIES/image_pipeline_stage_contract.json"
    compiler_path = PLAN / "07_IMPLEMENTATION/scripts/compile_orchestrator_run_plan.py"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_orchestrator_run_plan.py"
    request_example_path = PLAN / "09_EXAMPLES/wave14_orchestrator_request.example.json"
    planner_evidence_path = PLAN / "Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W69_LOCAL_PASS_PLANNER_CANNY_INPAINT_READINESS_P06_BOUND_20260707T112000-0500.json"
    active_path = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
    promotion_manifest_path = PLAN / "07_IMPLEMENTATION/manifests/generated/W69_LOCAL_IMAGE_QA_ORCHESTRATOR_PROMOTION_MANIFEST_SUPERSEDED_20260707T103500-0500.json"
    promotion_policy_path = QA / "future_lane_promotion.json"
    source, contract = source_path.read_text(encoding="utf-8-sig"), load(contract_path)
    compiler, validator = compiler_path.read_text(encoding="utf-8-sig"), validator_path.read_text(encoding="utf-8-sig")
    request_example, planner, active, manifest, promotion = (load(path) for path in (request_example_path, planner_evidence_path, active_path, promotion_manifest_path, promotion_policy_path))
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    lanes = active["lanes"]
    lane_files = []
    for lane in lanes:
        paths = [ROOT / lane[key] for key in ("workflow", "smoke_request", "runtime_requirements", "patch_points")]
        lane_files.append({"lane_id": lane["lane_id"], "paths": paths, "all_exist": all(path.is_file() for path in paths)})
    stages = {stage["stage"]: stage for stage in contract["stages"]}
    expected_passes = ["p00_preflight", "p01_base", "p03_pose_control", "p04_mask_factory", "p05_regional_detail", "p06_upscale_polish", "p99_promotion"]
    checks = {
        "IPB-001_row008_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IPB-002_source_contract_linked": rel(contract_path) in source and "## Promotion invariant" in source,
        "IPB-003_contract_schema_identity": contract["schema_version"] == "1.0" and contract["contract_id"] == "wave64_image_pipeline_stage_contract" and contract["tracker_id"] == TRK,
        "IPB-004_gate_order_exact": contract["gates_required"] == GATES,
        "IPB-005_exact_ten_active_lanes": len(lanes) == 10 and len({lane["lane_id"] for lane in lanes}) == 10,
        "IPB-006_all_lane_contract_files_exist": all(row["all_exist"] for row in lane_files),
        "IPB-007_all_lane_contract_json_parseable": all(all(isinstance(load(path), dict) for path in row["paths"]) for row in lane_files),
        "IPB-008_active_manifest_denies_runtime": active["runtime_boundaries"]["ec2_start_allowed_by_this_manifest"] is False and active["runtime_boundaries"]["generation_allowed_by_this_manifest"] is False,
        "IPB-009_compiler_stage_contract_present": all(token in compiler for token in ("p00_preflight", "p01_base", "p04_mask_factory", "p05_regional_detail", "p06_upscale_polish", "p99_promotion")),
        "IPB-010_validator_evidence_checks_present": all(token in validator for token in ("dry_run_first", "global_evidence_dependencies", "evidence_dependencies", "is required but has no evidence dependency binding yet")),
        "IPB-011_example_request_valid_shape": isinstance(request_example, dict) and bool(request_example.get("request_id")) and "image" in request_example.get("requested_modalities", []),
        "IPB-012_planner_passes_exact": planner["compiled_plan_summary"]["passes"] == expected_passes and planner["compiled_plan_summary"]["pass_count"] == 7,
        "IPB-013_planner_validation_clean": planner["validation_summary"]["status"] == "PASS" and planner["validation_summary"]["error_count"] == 0 and planner["validation_summary"]["warning_count"] == 0 and planner["validation_summary"]["checked_evidence_path_count"] == 19,
        "IPB-014_planner_local_only_no_generation": planner["local_only"] is True and planner["ec2_started"] is False and planner["comfyui_generation_executed"] is False and planner["certification_allowed"] is False,
        "IPB-015_stage_contract_exact_seven": len(stages) == 7 and set(stages) == {"base_generation", "pose_camera_control", "mask_factory", "regional_repair_detail", "contact_deformation", "upscale_final_polish", "promotion"},
        "IPB-016_mask_and_contact_fail_closed": stages["mask_factory"]["status"].startswith("blocked_") and stages["contact_deformation"]["status"].startswith("blocked_"),
        "IPB-017_artifact_manifest_partial_exact": manifest["promotion_status"] == "block_final_promotion_missing_target_runtime" and manifest["run_manifest"] is None and len(manifest["promoted_outputs"]) == 0 and manifest["gate_summary"]["target_runtime_block_count"] == 45,
        "IPB-018_contract_manifest_matches_source": contract["artifact_manifest"]["status"] == "partial_local_superseded" and contract["artifact_manifest"]["promoted_output_count"] == 0 and contract["artifact_manifest"]["target_runtime_block_count"] == 45,
        "IPB-019_promotion_policy_denies_zero_promotions": promotion["current_promotion_state"]["promotion_allowed"] is False and promotion["current_promotion_state"]["promoted_lane_count"] == 0 and contract["promotion"]["promotion_allowed"] is False,
        "IPB-020_no_runtime_mask_wave71_or_completion": all(contract[key] is False for key in ("runtime_action_allowed", "generation_allowed", "mask_promotion_allowed", "wave71_activation_allowed", "full_project_completion_implied")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed image-pipeline invariants: " + ", ".join(failed))
    groups = {
        "workflow_template_valid": [name for name in checks if name.startswith(("IPB-001", "IPB-002", "IPB-003", "IPB-004", "IPB-005", "IPB-006", "IPB-007", "IPB-008", "IPB-009", "IPB-010"))],
        "prompt_request_valid": [name for name in checks if name.startswith(("IPB-011", "IPB-012", "IPB-013", "IPB-014"))],
        "image_artifact_manifest": [name for name in checks if name.startswith(("IPB-015", "IPB-016", "IPB-017", "IPB-018"))],
        "promotion_gate": [name for name in checks if name.startswith(("IPB-019", "IPB-020"))],
    }
    stamped = QA / f"IMAGE_PIPELINE_BUILD_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_pipeline_build_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-008_image_pipeline_build.json"
    blockers = [
        "complete same-scope base-to-final runtime chain missing",
        "current image artifact manifest is local and superseded with no run manifest or promoted outputs",
        "trusted mask/body/hand/contact authority remains blocked",
        "Flux license/install/hash/runtime proof remains blocked",
        "final promotion is denied pending target-runtime and certification proof",
    ]
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": "planner_and_prompt_pass_artifact_partial_final_promotion_blocked",
        "validation_gates": {
            "workflow_template_valid": {"status": "pass_local_static", "checks": groups["workflow_template_valid"]},
            "prompt_request_valid": {"status": "pass_local_evidence_bound", "checks": groups["prompt_request_valid"]},
            "image_artifact_manifest": {"status": "partial_local_superseded", "checks": groups["image_artifact_manifest"]},
            "promotion_gate": {"status": "blocked_final_promotion_missing_target_runtime", "checks": groups["promotion_gate"]},
        },
        "stage_states": contract["stages"], "artifact_manifest": contract["artifact_manifest"], "promotion": contract["promotion"], "blockers": blockers,
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"compiler_executed": False, "validator_executed": False, "comfyui_contacted": False, "generation_executed": False, "aws_contacted": False, "ec2_started": False, "mask_consumed_or_promoted": False, "promotion_executed": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, contract_path, compiler_path, validator_path, request_example_path, planner_evidence_path, active_path, promotion_manifest_path, promotion_policy_path)],
        "next_action": "Proceed to TRK-W64-009 / ITEM-W64-009 for safe local work; do not generate, consume candidate masks as truth, or promote without a selected materially scoped runtime chain and all gates.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_static_planner_artifact_and_promotion_blocked", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "stage_states": payload["stage_states"], "artifact_manifest": payload["artifact_manifest"], "promotion": payload["promotion"], "blockers": blockers, "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})
    note_prefix = f"Wave64 Row008 {stamp}: ten lane contracts and seven-pass evidence-bound local planner validate"
    note = f"{note_prefix}, artifact manifest remains local/superseded with 45 target-runtime blocks and zero promoted outputs, final promotion remains denied, and 20/20 split-state checks pass."
    tags = ["wave64_row008_planner_prompt_pass", "image_artifact_manifest_partial", "mask_contact_stages_blocked", "final_promotion_blocked", "row009_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    for path in tracker_paths:
        normalize_row_note(path, "Tracker_ID", TRK, note)
    for path in item_paths:
        normalize_row_note(path, "Item_ID", ITEM, note)
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in tracker_paths]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row008 Image Pipeline Blueprint Implementation - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. All ten active lane contract files exist and parse, and the evidence-bound seven-pass local planner validates with zero errors/warnings and 19 evidence paths. The current image artifact manifest remains local/superseded with no run manifest, zero promoted outputs, and 45 target-runtime blocks. Mask/contact stages remain blocked by trusted-mask and geometry dependencies, Flux remains dependency-blocked, and final promotion remains denied. The split-state audit passes 20/20 checks without treating compilation as production completion. No compiler/validator execution, ComfyUI generation, AWS, EC2, mask use/promotion, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-009 / ITEM-W64-009`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Implemented current image-pipeline stage/proof contract and promotion blockers.", "; ".join(evidence_paths), "20/20 checks; planner pass; artifact partial; promotion blocked", payload["qa_decision"], rel(canonical), "Proceed to TRK-W64-009 / ITEM-W64-009."])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "lanes": len(lanes), "passes": planner["compiled_plan_summary"]["pass_count"], "artifact_manifest": payload["artifact_manifest"], "promotion": payload["promotion"], "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
