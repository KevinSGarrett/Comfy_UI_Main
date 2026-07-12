from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TRK, ITEM = "TRK-W64-017", "ITEM-W64-017"
STATUS = "Blocked_Canonical_Global_Review_Records_Missing_For_Historical_Localized_Changes"
DECISION = "row017_contract_pass_legacy_whole_image_support_not_canonical_global_authority"
GATES = ["whole_frame_visual_scan", "required_target_region_check", "required_non_target_region_scan", "hands_face_body_background_contact_lighting_check", "reject_on_any_global_defect"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, capture_output=True, text=True, check=False)


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
    marker = "## Wave64 Row017 Global Whole-Image Review For Localized Changes"
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
    canonical = QA / "global_visual_review_not_local_only.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("GLOBAL_VISUAL_REVIEW_NOT_LOCAL_ONLY_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    protocol_path = PLAN / "Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md"
    schema_path = PLAN / "08_SCHEMAS/global_whole_image_visual_review.schema.json"
    example_path = PLAN / "09_EXAMPLES/global_whole_image_visual_review.example.json"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_global_whole_image_visual_review.py"
    tests_path = PLAN / "Instructions/QA/Scripts/test_global_whole_image_visual_review.py"
    inpaint_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_VISUAL_QA_20260707T035000-0500.json"
    robust_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_ROBUSTNESS_VISUAL_QA_20260707T034000-0500.json"
    canny_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_CANNY_EYEONLY_VISUAL_QA_20260707T071100-0500.json"
    contact_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_WAVE25_CONTACT_SHADOW_PRESSURE_SEED210704_VISUAL_QA_20260707T124500-0500.json"
    cheeks_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_MF70_CHEEKS_SKIN_SEED210805_VISUAL_QA_20260707T154500-0500.json"
    matrix_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json"
    row016_path = QA / "image_hyperreal_visual_review.json"
    anatomy_path = QA / "image_body_anatomy.json"
    contact_authority_path = QA / "image_contact_physics.json"

    protocol = protocol_path.read_text(encoding="utf-8-sig")
    validator = validator_path.read_text(encoding="utf-8-sig")
    schema, example, inpaint, robust, canny, contact, cheeks, matrix, row016, anatomy, contact_authority = map(load, (schema_path, example_path, inpaint_path, robust_path, canny_path, contact_path, cheeks_path, matrix_path, row016_path, anatomy_path, contact_authority_path))
    output_image = ROOT / inpaint["reviewed_artifact"]["path"]
    source_image = ROOT / inpaint["source_image"]["path"]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    unit = run(tests_path)
    example_validation = run(validator_path, "--input", example_path)
    required_schema = set(schema.get("required", []))
    checks = {
        "GVR-001_row017_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "GVR-002_protocol_binds_five_gates": all(gate in protocol for gate in GATES) and "target pass never overrides" in protocol.lower(),
        "GVR-003_schema_requires_five_gates": set(GATES).issubset(required_schema),
        "GVR-004_schema_requires_pre_post_scan": set(schema["properties"]["whole_frame_visual_scan"]["allOf"][1]["required"]) == {"pre_edit_status", "post_edit_status"},
        "GVR-005_schema_requires_six_categories": set(schema["properties"]["hands_face_body_background_contact_lighting_check"]["required"]) == {"hands", "face", "body", "background", "contact", "lighting"},
        "GVR-006_validator_binds_target_name": "must match localized_change.target_region" in validator,
        "GVR-007_validator_requires_explicit_inspection": "must be explicitly inspected" in validator,
        "GVR-008_validator_rejects_any_defect": "any global defect requires fail status and rejection" in validator,
        "GVR-009_validator_blocks_target_only_pass": "pass requires whole-frame, target, and non-target gates to pass" in validator,
        "GVR-010_nine_regressions_pass": unit.returncode == 0 and "Ran 9 tests" in unit.stderr and "OK" in unit.stderr,
        "GVR-011_blocked_example_validates": example_validation.returncode == 0 and example["overall_decision"] == "blocked",
        "GVR-012_example_artifacts_hash_bound": output_image.is_file() and sha(output_image) == inpaint["reviewed_artifact"]["sha256"] and source_image.is_file() and sha(source_image) == inpaint["source_image"]["sha256"],
        "GVR-013_inpaint_local_pass_has_scope_gap": inpaint["strict_qa_result"].startswith("pass_with_notes") and inpaint["whole_image_findings"]["hands_feet_body"] == "not_visible" and "not_target_runtime_certified" in inpaint["certification_status"],
        "GVR-014_robustness_local_only": robust["overall_result"].startswith("pass_with_notes") and robust["certification_scope"] == "local_multiseed_robustness_only" and len(robust["not_certified_reasons"]) >= 1,
        "GVR-015_canny_preferred_local_not_global": "promote_as_preferred_local" in canny["decision"]["result"] and "not_visible_not_certified" in canny["strict_whole_image_checks"]["hands"],
        "GVR-016_contact_local_improvement_has_blockers": contact["qa_decision"]["promote_over_seed210701_for_final_certification"] is False and len(contact["qa_decision"]["expected_remaining_blockers"]) >= 1,
        "GVR-017_cheeks_local_not_final": cheeks["decision"]["whole_image_visual_qa_passed_with_notes"] is True and cheeks["decision"]["final_certification_allowed"] is False,
        "GVR-018_matrix_bounded_not_global": matrix["not_project_final_done"] is True and matrix["certification_status"] == "matrix_sample_set_certified",
        "GVR-019_row016_has_no_promoted_set": row016["certificate_reconciliation"]["current_promoted_output_count"] == 0 and row016["row_complete"] is False,
        "GVR-020_upstream_global_authority_incomplete": anatomy["row_complete"] is False and contact_authority["row_complete"] is False and inpaint["aws_contacted"] is False and inpaint["ec2_started"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed global-review invariants: " + ", ".join(failed))

    groups = {
        "whole_frame_visual_scan": ["GVR-001", "GVR-002", "GVR-004", "GVR-013"],
        "required_target_region_check": ["GVR-003", "GVR-006", "GVR-011", "GVR-016"],
        "required_non_target_region_scan": ["GVR-007", "GVR-009", "GVR-014", "GVR-017"],
        "hands_face_body_background_contact_lighting_check": ["GVR-005", "GVR-012", "GVR-015", "GVR-020"],
        "reject_on_any_global_defect": ["GVR-008", "GVR-010", "GVR-018", "GVR-019"],
    }
    stamped = QA / f"GLOBAL_VISUAL_REVIEW_NOT_LOCAL_ONLY_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "global_visual_review_not_local_only_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"
    blocker = "Historical localized QA records use ad hoc whole-image fields and do not consistently bind canonical pre-edit, target, non-target, post-edit, six-category coverage, and global-rejection evidence for every localized change."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "whole_frame_visual_scan": {"status": "partial_legacy_whole_image_reviews_exist_canonical_pre_post_scan_missing", "checks": groups["whole_frame_visual_scan"]},
            "required_target_region_check": {"status": "partial_target_findings_exist_canonical_binding_incomplete", "checks": groups["required_target_region_check"]},
            "required_non_target_region_scan": {"status": "blocked_not_emitted_consistently_for_historical_localized_changes", "checks": groups["required_non_target_region_scan"]},
            "hands_face_body_background_contact_lighting_check": {"status": "partial_ad_hoc_coverage_scope_gaps_remain", "checks": groups["hands_face_body_background_contact_lighting_check"]},
            "reject_on_any_global_defect": {"status": "pass_fail_closed_contract_implemented_historical_records_not_normalized", "checks": groups["reject_on_any_global_defect"]},
        },
        "exact_blocker": blocker,
        "legacy_evidence_reconciliation": {
            "representative_records_checked": [rel(path) for path in (inpaint_path, robust_path, canny_path, contact_path, cheeks_path, matrix_path)],
            "finding": "Local pass-with-notes semantics can coexist with visibility gaps, placement blockers, bounded scope, or missing final authority; none is silently normalized into a Row017 pass.",
            "new_contract_applies_to_future_or_explicitly_normalized_localized_reviews": True,
        },
        "test_results": {"unit_tests": {"run": 9, "passed": 9}, "contract_example_validation": "pass"},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "image_or_mask_promotion_performed": False, "hard_gates_rerun": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (protocol_path, schema_path, example_path, validator_path, tests_path, inpaint_path, robust_path, canny_path, contact_path, cheeks_path, matrix_path, row016_path, anatomy_path, contact_authority_path, output_image, source_image)],
        "next_action": "Proceed to TRK-W64-018 / ITEM-W64-018 in strict sequence. Reopen Row017 when localized-review producers emit the canonical contract or historical records are explicitly normalized without changing their bounded decisions.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(inpaint_path), rel(robust_path), rel(canny_path), rel(contact_path), rel(cheeks_path), rel(row016_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": DECISION, "test_results": payload["test_results"], "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "implementation": {"required_machine_gates": GATES, "pre_and_post_whole_frame_required": True, "target_only_override_forbidden": True, "global_defect_auto_reject": True}, "exact_blocker": blocker, "legacy_evidence_reconciliation": payload["legacy_evidence_reconciliation"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row017 {stamp}: implemented the five-gate global whole-image review contract, passed 9/9 regressions, reconciled six representative localized QA records, and preserved blocked state because historical records are not canonical Row017 evidence; 20/20 checks pass."
    tags = ["wave64_row017_global_review_contract_implemented", "target_only_override_forbidden", "legacy_localized_records_not_canonical", "global_defect_auto_reject", "row018_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row017 Global Whole-Image Review For Localized Changes - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The visual protocol now requires canonical pre-edit whole-frame, target-region, non-target-region, six-category coverage, post-edit whole-frame, and automatic global-defect rejection evidence. A target-only pass cannot override damage elsewhere. Nine regressions pass and the split-state audit passes 20/20 checks. Existing inpaint, Canny, contact, cheek-skin, and RealVisXL records provide useful bounded whole-image support but use ad hoc fields and retain visibility, placement, runtime, or certification boundaries; they are not rewritten into false Row017 passes. No generation, AWS, EC2, image/mask promotion, hard-gate rerun, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-018 / ITEM-W64-018`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields, proof_rows = reader.fieldnames or [], list(reader)
    record = {"Timestamp": iso, "Wave": "64", "Task": TRK, "Action": "Implemented global whole-image review contract and reconciled localized QA records.", "Files_Changed": "; ".join(evidence_paths), "Validation_Run": "9/9 regressions; contract validation; 20/20 audit checks", "Result": DECISION, "Evidence_Path": rel(canonical), "Next_Action": "Proceed to TRK-W64-018 / ITEM-W64-018."}
    matched = False
    for row in proof_rows:
        if row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical):
            row.update(record)
            matched = True
    if not matched:
        proof_rows.append(record)
    with proof.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=proof_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(proof_rows)
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "tests": payload["test_results"], "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
