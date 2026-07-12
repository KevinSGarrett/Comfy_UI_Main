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
TRK, ITEM = "TRK-W64-018", "ITEM-W64-018"
STATUS = "Blocked_No_Scope_Matched_MultiSeed_MultiPrompt_Target_Runtime_Portfolio_Certification"
DECISION = "row018_contract_pass_bounded_multisample_sets_reconciled_portfolio_certification_blocked"
GATES = ["multi_seed_sample_set", "aggregate_score", "defect_rate_limit", "portfolio_certification_record"]


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
    marker = "## Wave64 Row018 Multi-Sample Image Quality Certification"
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
    canonical = QA / "image_multi_sample_certification.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_MULTI_SAMPLE_CERTIFICATION_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    scorecard_path = PLAN / "Instructions/QA/MULTIMODAL_ARTIFACT_REVIEW_SCORECARD.md"
    schema_path = PLAN / "08_SCHEMAS/image_multi_sample_certification.schema.json"
    example_path = PLAN / "09_EXAMPLES/image_multi_sample_certification.example.json"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_image_multi_sample_certification.py"
    tests_path = PLAN / "Instructions/QA/Scripts/test_image_multi_sample_certification.py"
    canny_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_CANNY_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T093800-0500.json"
    canny_done_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W70_CANNY_FULL_BODY_MULTISEED_ROBUSTNESS_DONE_20260711T093800-0500.json"
    openpose_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_OPENPOSE_V6_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T045000-0500.json"
    matrix_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json"
    local_matrix_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_REALVISXL_MULTISAMPLE_VISUAL_QA_20260707T034600-0500.json"
    row016_path = QA / "image_hyperreal_visual_review.json"
    row017_path = QA / "global_visual_review_not_local_only.json"

    scorecard = scorecard_path.read_text(encoding="utf-8-sig")
    validator = validator_path.read_text(encoding="utf-8-sig")
    schema, example, canny, canny_done, openpose, matrix, local_matrix, row016, row017 = map(load, (schema_path, example_path, canny_path, canny_done_path, openpose_path, matrix_path, local_matrix_path, row016_path, row017_path))
    example_images = [(ROOT / sample["artifact"]["path"], sample["artifact"]["sha256"]) for sample in example["multi_seed_sample_set"]]
    matrix_images = [(ROOT / sample["image_path"], sample["image_sha256"]) for sample in matrix["samples"]]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    unit = run(tests_path)
    example_validation = run(validator_path, "--input", example_path)
    checks = {
        "IMC-001_row018_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IMC-002_scorecard_binds_four_gates": all(gate in scorecard for gate in GATES) and "at least three distinct" in scorecard,
        "IMC-003_schema_requires_four_gates": set(GATES).issubset(schema["required"]),
        "IMC-004_schema_requires_three_samples": schema["properties"]["multi_seed_sample_set"]["minItems"] == 3,
        "IMC-005_validator_requires_seed_prompt_diversity": "seed and prompt diversity" in validator,
        "IMC-006_validator_checks_aggregate": "aggregate_score must match sample scores" in validator,
        "IMC-007_validator_checks_defect_rate": "defect_rate_limit must match sample defects" in validator and "zero blocking defects" in validator,
        "IMC-008_validator_checks_target_runtime": "target-runtime proof for every sample" in validator,
        "IMC-009_nine_regressions_pass": unit.returncode == 0 and "Ran 9 tests" in unit.stderr and "OK" in unit.stderr,
        "IMC-010_blocked_example_validates": example_validation.returncode == 0 and example["portfolio_certification_record"]["decision"] == "blocked",
        "IMC-011_example_hashes_exact": len(example_images) == 3 and all(path.is_file() and sha(path) == expected for path, expected in example_images),
        "IMC-012_canny_three_seed_local_pass": len(canny["records"]) == 3 and canny["strict_visual_disposition"]["all_samples_pass"] is True,
        "IMC-013_canny_not_final_portfolio": canny["boundaries"]["target_runtime_proof"] is False and canny["boundaries"]["final_lane_certification"] is False and canny_done["closes_final_lane_work_order"] is False,
        "IMC-014_openpose_has_prompt_drift": len(openpose["samples"]) == 3 and openpose["aggregate"]["footwear_color_drift_count"] == 1 and openpose["quality_decision"]["strict_footwear_color_prompt_robustness_pass"] is False,
        "IMC-015_matrix_is_three_prompt_bounded": len(matrix["samples"]) == 3 and matrix["certification_status"] == "matrix_sample_set_certified" and matrix["not_project_final_done"] is True,
        "IMC-016_matrix_hashes_exact": all(path.is_file() and sha(path) == expected for path, expected in matrix_images),
        "IMC-017_local_matrix_not_certified": local_matrix["sample_count"] == 3 and local_matrix["final_decision_allowed"] is False and local_matrix["certification_status"].startswith("not_certified"),
        "IMC-018_local_matrix_has_hand_note": any(sample["defects"] for sample in local_matrix["samples"]) and local_matrix["runtime_boundaries"]["aws_contacted"] is False,
        "IMC-019_row016_has_no_promoted_outputs": row016["certificate_reconciliation"]["current_promoted_output_count"] == 0,
        "IMC-020_row017_global_authority_incomplete": row017["row_complete"] is False and canny["boundaries"]["wave71_activated"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed multi-sample invariants: " + ", ".join(failed))

    groups = {
        "multi_seed_sample_set": ["IMC-001", "IMC-003", "IMC-004", "IMC-011", "IMC-012"],
        "aggregate_score": ["IMC-002", "IMC-006", "IMC-009", "IMC-015", "IMC-016"],
        "defect_rate_limit": ["IMC-007", "IMC-010", "IMC-014", "IMC-017", "IMC-018"],
        "portfolio_certification_record": ["IMC-005", "IMC-008", "IMC-013", "IMC-019", "IMC-020"],
    }
    stamped = QA / f"IMAGE_MULTI_SAMPLE_CERTIFICATION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_multi_sample_certification_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-018_image_multi_sample_certification.json"
    blocker = "No lane has one scope-matched set proving at least three distinct seeds, at least two prompt references, aggregate/minimum score thresholds, zero blocking-defect rate, complete target-runtime coverage, and final portfolio certification."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "multi_seed_sample_set": {"status": "partial_multiple_three_sample_sets_exist_scope_dimensions_split", "checks": groups["multi_seed_sample_set"]},
            "aggregate_score": {"status": "blocked_no_canonical_scope_matched_aggregate_across_seed_and_prompt_diversity", "checks": groups["aggregate_score"]},
            "defect_rate_limit": {"status": "partial_local_sets_report_defects_but_no_portfolio_rate_certificate", "checks": groups["defect_rate_limit"]},
            "portfolio_certification_record": {"status": "blocked_no_full_target_runtime_multi_seed_multi_prompt_portfolio_record", "checks": groups["portfolio_certification_record"]},
        },
        "exact_blocker": blocker,
        "sample_set_reconciliation": {
            "realvisxl_target_runtime_matrix": "three prompt-focused samples, bounded matrix certified, seed robustness and portfolio completion not claimed",
            "canny_local_fullbody_matrix": "three seeds pass locally, target-runtime full-body scope and portfolio certification absent",
            "openpose_local_fullbody_matrix": "three seeds pass pose scope, one of three violates footwear color prompt",
            "local_realvisxl_matrix": "three local samples pass with notes, one hand/contact ambiguity, final decision disallowed",
        },
        "test_results": {"unit_tests": {"run": 9, "passed": 9}, "contract_example_validation": "pass"},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "promotion_performed": False, "hard_gates_rerun": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (scorecard_path, schema_path, example_path, validator_path, tests_path, canny_path, canny_done_path, openpose_path, matrix_path, local_matrix_path, row016_path, row017_path, *[path for path, _ in example_images], *[path for path, _ in matrix_images])],
        "next_action": "Proceed to TRK-W64-019 / ITEM-W64-019 in strict sequence. Reopen Row018 only with one lane-scoped target-runtime set satisfying the complete multi-seed, multi-prompt, score, defect-rate, and portfolio contract.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(canny_path), rel(openpose_path), rel(matrix_path), rel(local_matrix_path), rel(row016_path), rel(row017_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": DECISION, "test_results": payload["test_results"], "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "implementation": {"required_machine_gates": GATES, "minimum_distinct_seeds": 3, "minimum_distinct_prompts": 2, "target_runtime_all_samples_required": True}, "exact_blocker": blocker, "sample_set_reconciliation": payload["sample_set_reconciliation"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row018 {stamp}: implemented the four-gate portfolio multi-sample contract, passed 9/9 regressions, reconciled RealVisXL/Canny/OpenPose sample sets, and preserved blocked state because no lane combines seed/prompt diversity, target-runtime coverage, scores, and defect limits; 20/20 checks pass."
    tags = ["wave64_row018_multisample_contract_implemented", "bounded_sample_sets_reconciled", "portfolio_certification_blocked", "target_runtime_matrix_incomplete", "row019_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row018 Multi-Sample Image Quality Certification - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The scorecard now requires one lane-scoped `multi_seed_sample_set`, `aggregate_score`, `defect_rate_limit`, and `portfolio_certification_record` with at least three distinct seeds, at least two prompts, strict score thresholds, zero blocking defects, hash-bound artifacts, and target-runtime proof for every sample. Nine regressions and 20/20 split-state checks pass. Existing RealVisXL, Canny, and OpenPose matrices remain valid within their bounded scopes but split prompt diversity, seed robustness, target-runtime coverage, or defect-free consistency across different records. No generation, AWS, EC2, promotion, hard-gate rerun, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-019 / ITEM-W64-019`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields, proof_rows = reader.fieldnames or [], list(reader)
    record = {"Timestamp": iso, "Wave": "64", "Task": TRK, "Action": "Implemented multi-sample portfolio certification contract and reconciled bounded matrices.", "Files_Changed": "; ".join(evidence_paths), "Validation_Run": "9/9 regressions; contract validation; 20/20 audit checks", "Result": DECISION, "Evidence_Path": rel(canonical), "Next_Action": "Proceed to TRK-W64-019 / ITEM-W64-019."}
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
