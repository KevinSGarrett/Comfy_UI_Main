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
TRK, ITEM = "TRK-W64-011", "ITEM-W64-011"
STATUS = "Blocked_Visual_Runtime_Composition_Mismatch"
DECISION = "camera_plan_and_composition_score_pass_crop_and_visual_runtime_blocked"
GATES = ["camera_spec_check", "crop_boundary_check", "composition_score", "visual_runtime_ready"]


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
        "| Wave64 reconciliation 2026-07-09: no exact direct row evidence found; do not infer completion from rollups, mentions, Wave65 planned rows, Wave70 supporting evidence, local artifacts, or AWS artifacts without matching item/tracker id."
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
    marker = "## Wave64 Row011 Camera Framing And Composition Strictness"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        existing = current[:next_heading].strip() if next_heading >= 0 else current.strip()
        if existing == block.strip():
            return
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(block.strip() + "\n\n" + current, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    canonical = QA / "image_camera_composition.json"
    if canonical.exists() and load(canonical).get("artifact_type") == "wave64_camera_composition_reconciliation":
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_CAMERA_COMPOSITION_RECONCILIATION_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "03_IMAGE_SYSTEM/WAVE10_IMAGE_CAMERA_PLAN_COMPILER.md"
    original_path = PLAN / "Tracker/Evidence/Wave64/image_camera_composition.json"
    original_test_path = PLAN / "Tracker/Evidence/Wave64/image_camera_composition_test_log.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAVE10_CAMERA_COMPILER_FULL_BODY_VISUAL_QA_20260711T113100-0500.json"
    w70_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_OPENPOSE_V6_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T045000-0500.json"
    w70_done_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W70_OPENPOSE_V6_FULL_BODY_MULTISEED_ROBUSTNESS_DONE_20260711T045000-0500.json"
    compiler_path = PLAN / "07_IMPLEMENTATION/scripts/compile_camera_plan.py"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_camera_plan.py"
    scorer_path = PLAN / "07_IMPLEMENTATION/scripts/score_framing_composition.py"
    profile_path = ROOT / "PromptProfiles/base_generation/wave10_camera_compiler/wave10_camera_full_body_realvisxl_seed7152026101.json"
    source = source_path.read_text(encoding="utf-8-sig")
    original, original_test, visual, w70, w70_done = map(load, (original_path, original_test_path, visual_path, w70_path, w70_done_path))
    image_path = ROOT / original["runtime"]["image"]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    gates = original["acceptance_gates"]
    disposition = original["strict_visual_disposition"]
    checks = {
        "ICC-001_row011_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "ICC-002_source_exact_binding_rule": all(token in source for token in ("exact compiled request", "cannot supersede", "Landmark presence is not proof")),
        "ICC-003_original_row_identity_exact": original["tracker_id"] == TRK and original["item_id"] == ITEM,
        "ICC-004_original_unit_tests_pass": original_test["result"] == "pass" and original_test["tests_run"] == 22 and original_test["failures"] == 0 and original_test["errors"] == 0,
        "ICC-005_camera_tools_present": all(path.is_file() for path in (compiler_path, validator_path, scorer_path, profile_path)),
        "ICC-006_compiler_recompile_exact": original["technical_checks"]["request_recompiles_to_committed_plan"] is True and original["technical_checks"]["request_and_plan_recompile_to_committed_profile"] is True,
        "ICC-007_runtime_and_bindings_pass": original["technical_pass"] is True and original["technical_checks"]["runtime_passed"] is True and original["technical_checks"]["runtime_prompt_hash_matches_package"] is True,
        "ICC-008_exactly_one_person_all_landmarks": original["dwpose"]["person_count"] == 1 and original["dwpose"]["detected_body_landmark_count"] == 18,
        "ICC-009_image_hash_and_dimensions_exact": image_path.is_file() and sha(image_path) == original["runtime"]["image_sha256"] and original["runtime"]["dimensions"] == {"width": 768, "height": 1024},
        "ICC-010_camera_spec_gate_pass": gates["camera_spec_check"] is True,
        "ICC-011_visual_contract_valid": disposition["contract_valid"] is True and not disposition["issues"],
        "ICC-012_full_body_camera_intent_pass": disposition["checks"]["eye_level_full_body_camera_intent"] is True,
        "ICC-013_head_feet_and_margins_pass": all(disposition["checks"][key] is True for key in ("head_and_hair_fully_in_frame", "both_feet_fully_in_frame", "balanced_headroom_footroom_and_side_margins")),
        "ICC-014_hands_visibility_fails": disposition["checks"]["both_hands_fully_visible_and_inspectable"] is False,
        "ICC-015_required_region_visibility_fails": disposition["checks"]["no_required_region_hidden"] is False,
        "ICC-016_crop_boundary_gate_blocked": gates["crop_boundary_check"] is False,
        "ICC-017_composition_score_preserved": gates["composition_score"] == 100,
        "ICC-018_visual_runtime_gate_blocked": gates["visual_runtime_ready"] is False and disposition["visual_pass"] is False,
        "ICC-019_w70_adjacent_lane_non_superseding": w70["lane_id"] == "sdxl_realvisxl_controlnet_openpose_lane" and w70["boundaries"]["target_runtime_proof"] is False and w70["boundaries"]["final_lane_certification"] is False,
        "ICC-020_w70_done_scope_not_wave10": w70_done["closes_local_scope_item"] is True and w70_done["closes_final_lane_work_order"] is False and w70_done["full_project_certification"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed camera composition invariants: " + ", ".join(failed))

    groups = {
        "camera_spec_check": ["ICC-001", "ICC-002", "ICC-003", "ICC-004", "ICC-010"],
        "crop_boundary_check": ["ICC-008", "ICC-009", "ICC-013", "ICC-014", "ICC-016"],
        "composition_score": ["ICC-005", "ICC-006", "ICC-007", "ICC-012", "ICC-017"],
        "visual_runtime_ready": ["ICC-011", "ICC-015", "ICC-018", "ICC-019", "ICC-020"],
    }
    stamped = QA / f"IMAGE_CAMERA_COMPOSITION_RECONCILIATION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_camera_composition_reconciliation_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-011_image_camera_composition_reconciliation.json"
    blocker = "The exact Wave10 output keeps full-body framing but both hands are partly hidden in trouser pockets instead of fully visible and inspectable."
    payload = {
        "schema_version": "1.0", "artifact_type": "wave64_camera_composition_reconciliation", "evidence_id": stamped.stem,
        "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "camera_spec_check": {"status": "pass_compiler_bound", "checks": groups["camera_spec_check"]},
            "crop_boundary_check": {"status": "blocked_required_hands_not_fully_visible", "checks": groups["crop_boundary_check"]},
            "composition_score": {"status": "pass_score_100_with_visibility_override", "score": 100, "checks": groups["composition_score"]},
            "visual_runtime_ready": {"status": "blocked_strict_visual_mismatch", "checks": groups["visual_runtime_ready"]},
        },
        "exact_blocker": blocker,
        "codex_visual_review": {
            "reviewed_existing_image_only": True, "image": rel(image_path), "image_sha256": sha(image_path),
            "findings": [
                "One adult is centered in an eye-level full-body portrait with complete hair and both shoes inside the frame.",
                "Headroom, footroom, and side margins are balanced and the image has no obvious global composition defect.",
                "Both hands are visibly inserted into trouser pockets; only partial hands/wrists are exposed, so the requested open inspectable hands are absent.",
            ],
        },
        "non_superseding_adjacent_evidence": {"path": rel(w70_path), "lane_id": w70["lane_id"], "reason": "different OpenPose lane/control workflow; local robustness only; no target-runtime or final-lane certification"},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "mask_consumed_or_promoted": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, original_path, original_test_path, visual_path, w70_path, w70_done_path, compiler_path, validator_path, scorer_path, profile_path, image_path)],
        "next_action": "Proceed to TRK-W64-012 / ITEM-W64-012 in strict sequence. Reopen Row011 only for a new Wave10-compiled, scope-bound sample with both hands fully visible; do not reuse W70 OpenPose evidence as a substitute.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(original_path), rel(original_test_path), rel(visual_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_split_state_camera_composition_blocker_preserved", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "exact_blocker": blocker, "codex_visual_review": payload["codex_visual_review"], "non_superseding_adjacent_evidence": payload["non_superseding_adjacent_evidence"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row011 {stamp}: preserved the 22-test compiler/runtime pass and score 100, confirmed by Codex visual review that both hands remain pocket-obscured, and classified W70 OpenPose full-body proof as adjacent/non-superseding; crop and visual-runtime gates remain blocked; 20/20 split-state checks pass without regeneration."
    tags = ["wave64_row011_compiler_and_score_pass", "crop_visibility_blocked", "visual_runtime_blocked", "w70_non_superseding", "row012_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row011 Camera Framing And Composition Strictness - {iso}

`{TRK}` / `{ITEM}` remains `{STATUS}`. The exact Wave10 compiler-bound request passes 22 tests, deterministic plan/profile binding, local runtime, one-person/18-landmark detection, camera intent, full-body framing, and composition score 100. Direct Codex visual review confirms both hands remain partly hidden in trouser pockets, so the required-region crop and strict visual-runtime gates fail. Later W70 OpenPose full-body robustness belongs to a different lane/control workflow and explicitly lacks target-runtime/final-lane certification; it is supportive but cannot supersede this blocker. The reconciliation audit passes 20/20 checks. No new generation, AWS, EC2, mask use/promotion, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-012 / ITEM-W64-012`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Reconciled camera compiler, framing, crop, and visual-runtime evidence.", "; ".join(evidence_paths), "22/22 unit tests retained; 20/20 reconciliation checks; crop and visual runtime blocked", DECISION, rel(canonical), "Proceed to TRK-W64-012 / ITEM-W64-012."])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
