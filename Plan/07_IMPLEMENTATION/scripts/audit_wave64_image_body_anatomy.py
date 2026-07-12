from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TRK, ITEM = "TRK-W64-013", "ITEM-W64-013"
STATUS = "Blocked_Regional_Hard_Anatomy_Evidence_Missing_Contract_Gates_Implemented"
DECISION = "hard_anatomy_contract_pass_whole_image_support_regional_authority_blocked"
GATES = ["anatomy_scorecard", "hands_feet_check", "face_teeth_eye_check", "hard_reject_on_deformation"]


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
    marker = "## Wave64 Row013 Hard Anatomy And Body Proportion Review"
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
    canonical = QA / "image_body_anatomy.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_BODY_ANATOMY_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "03_IMAGE_SYSTEM/WAVE20_IMAGE_HARD_ANATOMY_REPAIR_PLAN.md"
    compiler_path = PLAN / "07_IMPLEMENTATION/scripts/compile_hard_anatomy_repair_contract.py"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_hard_anatomy_repair_contract.py"
    scorer_path = PLAN / "07_IMPLEMENTATION/scripts/score_hard_anatomy_evidence.py"
    pack_validator_path = PLAN / "07_IMPLEMENTATION/scripts/run_wave20_local_validation.py"
    schema_path = PLAN / "08_SCHEMAS/hard_anatomy_repair_contract.schema.json"
    example_path = PLAN / "09_EXAMPLES/wave20_hard_anatomy_repair_contract.example.json"
    scoring17_path = PLAN / "10_REGISTRIES/wave17_body_proportion_qa_scoring_rules.json"
    scoring20_path = PLAN / "10_REGISTRIES/wave20_hard_anatomy_qa_scoring_rules.json"
    tests_path = PLAN / "Instructions/QA/Scripts/test_hard_anatomy_contract.py"
    protocol_path = PLAN / "Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md"
    openpose_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_OPENPOSE_V6_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T045000-0500.json"
    normal_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T043500-0500.json"
    canny_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_CANNY_FULL_BODY_MULTISEED_ROBUSTNESS_QA_20260711T093800-0500.json"
    source = source_path.read_text(encoding="utf-8-sig")
    compiler = compiler_path.read_text(encoding="utf-8-sig")
    validator = validator_path.read_text(encoding="utf-8-sig")
    scorer = scorer_path.read_text(encoding="utf-8-sig")
    schema, example, scoring17, scoring20, openpose, normal, canny = map(load, (schema_path, example_path, scoring17_path, scoring20_path, openpose_path, normal_path, canny_path))
    representative = [
        (ROOT / openpose["samples"][0]["image"]["path"], openpose["samples"][0]["image"]["sha256"]),
        (ROOT / normal["samples"][0]["image"]["path"], normal["samples"][0]["image"]["sha256"]),
        (ROOT / canny["records"][0]["image"], canny["records"][0]["image_sha256"]),
    ]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    unit = run("-m", "unittest", "-v", "Plan.Instructions.QA.Scripts.test_hard_anatomy_contract")
    pack = run(pack_validator_path, "--root", PLAN)
    pack_json_match = re.search(r"JSON files checked: (\d+)", pack.stdout)
    pack_required_match = re.search(r"Required files checked: (\d+)", pack.stdout)
    pack_json_count = int(pack_json_match.group(1)) if pack_json_match else 0
    pack_required_count = int(pack_required_match.group(1)) if pack_required_match else 0
    with tempfile.TemporaryDirectory() as tmp:
        compiled_path = Path(tmp) / "compiled.json"
        compile_run = run(compiler_path, "--input", example_path, "--output", compiled_path)
        validate_run = run(validator_path, "--input", compiled_path)
        compiled = load(compiled_path) if compiled_path.exists() else {}

    checks = {
        "IBA-001_row013_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IBA-002_source_documents_four_gates": all(gate in source for gate in GATES) and "Whole-image plausibility does not certify" in source,
        "IBA-003_compiler_emits_four_gates": all(gate in compiler for gate in GATES),
        "IBA-004_validator_requires_four_gates": all(gate in validator for gate in GATES) and "promotion allowed while" in validator,
        "IBA-005_schema_requires_four_gates": set(GATES).issubset(schema["required"]),
        "IBA-006_example_fail_closed": set(GATES).issubset(example) and example["hard_reject_on_deformation"]["triggered"] is True and example["hard_reject_on_deformation"]["promotion_allowed"] is False,
        "IBA-007_scoring_registries_bind_gates": scoring17["required_hard_anatomy_contract_fields"] == GATES and scoring20["required_gate_fields"] == GATES and scoring20["numeric_score_override_allowed"] is False,
        "IBA-008_scorer_hard_override_present": all(token in scorer for token in ("required_gates_pass", "regional_checks_pass", "hard_reject_clear", "automatic_fail_flags")),
        "IBA-009_eight_regressions_pass": unit.returncode == 0 and "Ran 8 tests" in unit.stderr and "OK" in unit.stderr,
        "IBA-010_wave20_pack_validation_pass": pack.returncode == 0 and pack_json_count >= 5020 and pack_required_count == 9,
        "IBA-011_compile_and_validate_example": compile_run.returncode == 0 and validate_run.returncode == 0 and set(GATES).issubset(compiled),
        "IBA-012_compiled_example_stays_blocked": compiled["hard_reject_on_deformation"]["triggered"] is True and compiled["hard_reject_on_deformation"]["promotion_allowed"] is False,
        "IBA-013_openpose_whole_body_support": len(openpose["samples"]) == 3 and all(row["metrics"]["common_body_landmarks"] == 18 for row in openpose["samples"]),
        "IBA-014_normal_whole_body_support": len(normal["samples"]) == 3 and all(row["metrics"]["common_body_landmarks"] == 18 for row in normal["samples"]),
        "IBA-015_canny_whole_body_support": len(canny["records"]) == 3 and canny["strict_visual_disposition"]["all_samples_pass"] is True,
        "IBA-016_representative_hashes_exact": all(path.is_file() and sha(path) == expected for path, expected in representative),
        "IBA-017_fullbody_evidence_non_authoritative": openpose["boundaries"]["body_mask_or_geometry_authority"] is False and normal["boundaries"]["body_mask_or_geometry_authority"] is False and canny["boundaries"]["gold_masks_consumed"] is False,
        "IBA-018_zoomed_regions_not_proven": all(row["boundaries"]["final_lane_certification"] is False for row in (openpose, normal, canny)),
        "IBA-019_gold_geometry_dependency_preserved": "body/hand/contact validation" in protocol_path.read_text(encoding="utf-8-sig").lower() and "trusted masks" in protocol_path.read_text(encoding="utf-8-sig").lower(),
        "IBA-020_no_runtime_or_promotion_action": all(row["boundaries"]["local_only"] is True for row in (openpose, normal, canny)) and all(row["boundaries"]["wave71_activated"] is False for row in (openpose, normal, canny)),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed body-anatomy invariants: " + ", ".join(failed))

    groups = {
        "anatomy_scorecard": ["IBA-001", "IBA-002", "IBA-005", "IBA-007", "IBA-013"],
        "hands_feet_check": ["IBA-003", "IBA-006", "IBA-014", "IBA-016", "IBA-017"],
        "face_teeth_eye_check": ["IBA-009", "IBA-010", "IBA-015", "IBA-018", "IBA-019"],
        "hard_reject_on_deformation": ["IBA-004", "IBA-008", "IBA-011", "IBA-012", "IBA-020"],
    }
    stamped = QA / f"IMAGE_BODY_ANATOMY_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_body_anatomy_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-013_image_body_anatomy.json"
    blocker = "No scope-matched zoomed regional evidence proves fingers, toes, teeth, eyes, joints, limbs, and contact anatomy together; trusted body/hand/contact geometry authority remains unavailable."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "anatomy_scorecard": {"status": "partial_contract_implemented_whole_image_support_only", "checks": groups["anatomy_scorecard"]},
            "hands_feet_check": {"status": "blocked_zoomed_finger_toe_authority_missing", "checks": groups["hands_feet_check"]},
            "face_teeth_eye_check": {"status": "blocked_scope_matched_regional_evidence_missing", "checks": groups["face_teeth_eye_check"]},
            "hard_reject_on_deformation": {"status": "pass_fail_closed_implementation", "checks": groups["hard_reject_on_deformation"]},
        },
        "exact_blocker": blocker,
        "codex_visual_review": {
            "reviewed_existing_images_only": True, "images": [rel(path) for path, _ in representative],
            "findings": [
                "Representative OpenPose, Normal, and Canny images show plausible whole-body silhouettes, coherent major limbs, and in-frame hands and footwear.",
                "Hands and shoes are too small for authoritative finger, nail, toe, or sole inspection; teeth are not visible and eye detail is not scope-matched for regional certification.",
                "Whole-image visual plausibility therefore supports anatomy triage but cannot clear the new regional hard gates.",
            ],
        },
        "test_results": {"unit_tests": {"run": 8, "passed": 8}, "wave20_pack": {"json_files_checked": pack_json_count, "required_files_checked": pack_required_count, "minimum_json_files_required": 5020, "result": "pass"}},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "mask_promotion_performed": False, "hard_gates_rerun": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, compiler_path, validator_path, scorer_path, pack_validator_path, schema_path, example_path, scoring17_path, scoring20_path, tests_path, protocol_path, openpose_path, normal_path, canny_path, *[path for path, _ in representative])],
        "next_action": "Proceed to TRK-W64-014 / ITEM-W64-014 in strict sequence. Reopen Row013 only with scope-matched regional evidence and trusted geometry prerequisites; whole-image matrices must not be promoted into finger/toe/teeth/eye authority.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(openpose_path), rel(normal_path), rel(canny_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_contract_implementation_regional_authority_blocked", "commands": {"unit": [sys.executable, "-m", "unittest", "-v", "Plan.Instructions.QA.Scripts.test_hard_anatomy_contract"], "pack": [sys.executable, rel(pack_validator_path), "--root", "Plan"]}, "test_results": payload["test_results"], "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "implementation": {"four_machine_gates": GATES, "fail_closed_defaults": True, "numeric_override_forbidden": True}, "exact_blocker": blocker, "codex_visual_review": payload["codex_visual_review"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row013 {stamp}: implemented four machine hard-anatomy gates across compiler/validator/schema/example/scorers, passed 8/8 regressions and the 5020-plus-JSON Wave20 pack validator, and preserved hard rejection because W70 whole-image matrices do not prove zoomed fingers/toes/teeth/eyes/contact authority; 20/20 split-state checks pass."
    tags = ["wave64_row013_contract_gates_implemented", "hard_reject_fail_closed", "whole_image_support_only", "regional_authority_blocked", "row014_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row013 Hard Anatomy And Body Proportion Review - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The compiler, validator, schema, example, Wave17/Wave20 scoring rules, and evidence scorer now implement `anatomy_scorecard`, `hands_feet_check`, `face_teeth_eye_check`, and `hard_reject_on_deformation`. Missing regional evidence compiles blocked, numeric scores cannot override regional failure, and promotion is rejected unless every applicable region is pass-like and inspectable. Eight regressions pass, and the repaired Wave20 validator parses at least 5,020 JSON files and all 9 required files. Direct Codex review of representative OpenPose, Normal, and Canny images supports broad whole-body plausibility only; fingers, toes, teeth, detailed eyes, joints, and contact anatomy remain unproven at zoomed regional authority. The split-state audit passes 20/20 checks. No generation, AWS, EC2, mask truth consumption/promotion, hard-gate rerun, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-014 / ITEM-W64-014`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields, proof_rows = reader.fieldnames or [], list(reader)
    proof_record = {
        "Timestamp": iso, "Wave": "64", "Task": TRK,
        "Action": "Implemented fail-closed hard-anatomy gates and reconciled regional evidence.",
        "Files_Changed": "; ".join(evidence_paths),
        "Validation_Run": "8/8 regressions; 5020-plus JSON pack validation; 20/20 audit checks",
        "Result": DECISION, "Evidence_Path": rel(canonical),
        "Next_Action": "Proceed to TRK-W64-014 / ITEM-W64-014.",
    }
    matched_proof = False
    for row in proof_rows:
        if row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical):
            row.update(proof_record)
            matched_proof = True
    if not matched_proof:
        proof_rows.append(proof_record)
    with proof.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=proof_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(proof_rows)
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "tests": payload["test_results"], "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
