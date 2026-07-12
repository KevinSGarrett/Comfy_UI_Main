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
TRK, ITEM = "TRK-W64-014", "ITEM-W64-014"
STATUS = "Blocked_Gold_Mask_Dependency_Missing"
DECISION = "skin_material_contract_pass_bounded_visual_support_macro_regional_promotion_blocked"
GATES = ["surface_texture_check", "lighting_consistency", "material_state_continuity", "visual_score_threshold"]


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
    marker = "## Wave64 Row014 Skin Material And Surface Hyperrealism Review"
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
    canonical = QA / "image_skin_material.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_SKIN_MATERIAL_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "03_IMAGE_SYSTEM/WAVE18_IMAGE_SKIN_MATERIAL_PASS_IMPLEMENTATION_PLAN.md"
    qa_gates_path = PLAN / "06_QA_TESTING/WAVE18_SKIN_MATERIAL_REALISM_QA_GATES.md"
    compiler_path = PLAN / "07_IMPLEMENTATION/scripts/compile_skin_material_contract.py"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_skin_material_contract.py"
    scorer_path = PLAN / "07_IMPLEMENTATION/scripts/score_skin_material_evidence.py"
    pack_path = PLAN / "07_IMPLEMENTATION/scripts/run_wave18_local_validation.py"
    contract_schema_path = PLAN / "08_SCHEMAS/skin_material_contract.schema.json"
    evidence_schema_path = PLAN / "08_SCHEMAS/skin_material_evidence.schema.json"
    qa_schema_path = PLAN / "08_SCHEMAS/skin_material_qa_goal.schema.json"
    contract_example_path = PLAN / "09_EXAMPLES/wave18_skin_material_contract.example.json"
    evidence_example_path = PLAN / "09_EXAMPLES/wave18_skin_material_evidence.example.json"
    profiles_path = PLAN / "10_REGISTRIES/wave18_skin_material_profiles.json"
    scoring_path = PLAN / "10_REGISTRIES/wave18_surface_continuity_scoring_rules.json"
    rerun_path = PLAN / "10_REGISTRIES/wave18_skin_material_rerun_policy.json"
    tests_path = PLAN / "Instructions/QA/Scripts/test_skin_material_contract.py"
    dependency_path = PLAN / "Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md"
    normal_qa_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_NORMAL_V2_SKIN_FABRIC_VISUAL_QA_20260707T074900-0500.json"
    realvis_qa_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_IMAGE_QA_VISUAL_20260706T200845-0500.json"

    source = source_path.read_text(encoding="utf-8-sig")
    qa_gates = qa_gates_path.read_text(encoding="utf-8-sig")
    compiler = compiler_path.read_text(encoding="utf-8-sig")
    validator = validator_path.read_text(encoding="utf-8-sig")
    scorer = scorer_path.read_text(encoding="utf-8-sig")
    contract_schema, evidence_schema, qa_schema = map(load, (contract_schema_path, evidence_schema_path, qa_schema_path))
    contract_example, evidence_example, scoring, rerun = map(load, (contract_example_path, evidence_example_path, scoring_path, rerun_path))
    normal, realvis = map(load, (normal_qa_path, realvis_qa_path))
    normal_image = ROOT / normal["generated_artifact"]["path"]
    realvis_image = ROOT / realvis["image_path"]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    unit = run(tests_path)
    pack = run(pack_path, "--root", PLAN)
    pack_json_match = re.search(r"JSON files checked: (\d+)", pack.stdout)
    pack_required_match = re.search(r"Required files checked: (\d+)", pack.stdout)
    pack_json_count = int(pack_json_match.group(1)) if pack_json_match else 0
    pack_required_count = int(pack_required_match.group(1)) if pack_required_match else 0
    with tempfile.TemporaryDirectory() as tmp:
        compiled_path = Path(tmp) / "compiled.json"
        score_path = Path(tmp) / "score.json"
        compile_run = run(compiler_path, "--input", contract_example_path, "--output", compiled_path)
        validate_run = run(validator_path, "--input", compiled_path)
        score_run = run(scorer_path, "--input", evidence_example_path, "--output", score_path)
        compiled = load(compiled_path) if compiled_path.exists() else {}
        blocked_score = load(score_path) if score_path.exists() else {}

    required_schema = set(evidence_schema.get("required", []))
    block_conditions = set(rerun.get("block_conditions", []))
    checks = {
        "ISM-001_row014_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "ISM-002_source_documents_four_gates": all(gate in source and gate in qa_gates for gate in GATES),
        "ISM-003_compiler_emits_gate_contract": "REQUIRED_EVIDENCE_GATES" in compiler and all(gate in compiler for gate in GATES),
        "ISM-004_validator_rejects_unknown_or_empty": "surface_profile is not registered" in validator and "target_regions must contain" in validator,
        "ISM-005_scorer_ands_four_gates": all(gate in scorer for gate in GATES) and "all(gate_results.values())" in scorer,
        "ISM-006_contract_schema_fail_closed": set(GATES).issubset(contract_example["required_evidence_gates"]) and contract_schema["properties"]["target_regions"]["minItems"] == 1,
        "ISM-007_evidence_schema_requires_four_gates": set(GATES).issubset(required_schema) and evidence_schema["properties"]["continuity_score"]["maximum"] == 1,
        "ISM-008_qa_threshold_bounded": qa_schema["properties"]["acceptance_threshold"]["minimum"] == 0 and qa_schema["properties"]["acceptance_threshold"]["maximum"] == 100,
        "ISM-009_scoring_registry_forbids_override": scoring["required_gate_fields"] == GATES and scoring["numeric_score_override_allowed"] is False and scoring["visual_authority_required"] is True,
        "ISM-010_rerun_policy_blocks_visual_failures": {"lighting_consistency_failed_or_blocked", "material_state_continuity_failed_or_blocked", "macro_or_full_frame_review_missing", "visual_qa_certification_not_allowed"}.issubset(block_conditions),
        "ISM-011_eight_regressions_pass": unit.returncode == 0 and "Ran 8 tests" in unit.stderr and "OK" in unit.stderr,
        "ISM-012_wave18_pack_pass": pack.returncode == 0 and pack_json_count >= 5026 and pack_required_count == 13,
        "ISM-013_compile_validate_roundtrip": compile_run.returncode == 0 and validate_run.returncode == 0 and compiled.get("required_evidence_gates") == GATES,
        "ISM-014_blocked_example_scores_fail_closed": score_run.returncode == 0 and blocked_score.get("pass") is False and len(blocked_score.get("automatic_fail_flags", [])) >= 1,
        "ISM-015_normal_v2_is_mixed_nonpromotable": normal["certification_allowed"] is False and normal["improvement_against_v1"]["promotion_decision"].startswith("do_not_promote"),
        "ISM-016_normal_v2_texture_goal_missed": "not_materially_improved" in normal["improvement_against_v1"]["skin_texture"] and "not_improved" in normal["improvement_against_v1"]["shirt_fabric_texture"],
        "ISM-017_realvis_is_bounded_whole_image_support": realvis["qa_score"] >= realvis["pass_threshold"] and "matrix_sample3" in realvis["result"] and "macro" not in json.dumps(realvis).lower(),
        "ISM-018_visual_artifacts_hash_bound": normal_image.is_file() and sha(normal_image) == normal["generated_artifact"]["sha256"] and realvis_image.is_file(),
        "ISM-019_no_scope_matched_paired_authority": evidence_example["visual_qa_reference"]["certification_allowed"] is False and evidence_example["visual_score_threshold"]["macro_review_status"] == "blocked",
        "ISM-020_gold_mask_boundary_preserved": "trusted manual gold masks" in dependency_path.read_text(encoding="utf-8-sig").lower() and "canonical body-part mask promotion" in dependency_path.read_text(encoding="utf-8-sig").lower() and normal["aws_contacted"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed skin-material invariants: " + ", ".join(failed))

    groups = {
        "surface_texture_check": ["ISM-001", "ISM-002", "ISM-007", "ISM-011", "ISM-016"],
        "lighting_consistency": ["ISM-003", "ISM-005", "ISM-008", "ISM-015", "ISM-017"],
        "material_state_continuity": ["ISM-004", "ISM-006", "ISM-009", "ISM-010", "ISM-018"],
        "visual_score_threshold": ["ISM-012", "ISM-013", "ISM-014", "ISM-019", "ISM-020"],
    }
    stamped = QA / f"IMAGE_SKIN_MATERIAL_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_skin_material_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-014_image_skin_material.json"
    blocker = "No trusted owned regional mask and no paired Wave18 before/after set provide both macro and full-frame skin/material visual authority; existing W69 Normal v2 is mixed/non-promotable and W66 sample3 is bounded whole-image support only."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "surface_texture_check": {"status": "partial_bounded_whole_image_support_macro_regional_authority_blocked", "checks": groups["surface_texture_check"]},
            "lighting_consistency": {"status": "partial_existing_whole_image_lighting_support_no_paired_regional_pass", "checks": groups["lighting_consistency"]},
            "material_state_continuity": {"status": "blocked_no_paired_before_after_material_state_authority", "checks": groups["material_state_continuity"]},
            "visual_score_threshold": {"status": "blocked_macro_and_full_frame_certifying_record_missing", "checks": groups["visual_score_threshold"]},
        },
        "exact_blocker": blocker,
        "codex_visual_review": {
            "reviewed_existing_images_only": True,
            "images": [rel(normal_image), rel(realvis_image)],
            "findings": [
                "Normal v2 is coherent but retains a mildly beauty-polished facial surface and weak shirt weave, matching its mixed non-promotable QA record.",
                "RealVisXL sample3 shows visible age detail, pores, lace texture, and coherent window/lamp lighting, but remains one bounded whole-image base-generation sample.",
                "Neither artifact is a linked Wave18 before/after regional pass with both macro and full-frame certification, so neither can clear Row014 promotion.",
            ],
        },
        "test_results": {"unit_tests": {"run": 8, "passed": 8}, "wave18_pack": {"json_files_checked": pack_json_count, "required_files_checked": pack_required_count, "minimum_json_files_required": 5026, "result": "pass"}},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "mask_promotion_performed": False, "hard_gates_rerun": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, qa_gates_path, compiler_path, validator_path, scorer_path, pack_path, contract_schema_path, evidence_schema_path, qa_schema_path, contract_example_path, evidence_example_path, profiles_path, scoring_path, rerun_path, tests_path, dependency_path, normal_qa_path, realvis_qa_path, normal_image, realvis_image)],
        "next_action": "Proceed to TRK-W64-015 / ITEM-W64-015 in strict sequence. Reopen Row014 only with a trusted owned regional mask and linked paired before/after evidence that passes macro and full-frame visual review.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(normal_qa_path), rel(realvis_qa_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": DECISION, "test_results": payload["test_results"], "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "implementation": {"required_machine_gates": GATES, "fail_closed_defaults": True, "numeric_override_forbidden": True, "visual_qa_reference_required": True}, "exact_blocker": blocker, "codex_visual_review": payload["codex_visual_review"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row014 {stamp}: implemented four fail-closed skin/material evidence gates, passed 8/8 regressions and the 5026-plus-JSON Wave18 pack, and preserved promotion blocking because no trusted owned regional mask or linked macro/full-frame before/after authority exists; 20/20 split-state checks pass."
    tags = ["wave64_row014_contract_gates_implemented", "bounded_visual_support_only", "gold_mask_dependency_blocked", "macro_full_frame_authority_missing", "row015_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row014 Skin Material And Surface Hyperrealism Review - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Wave18 now requires machine-readable `surface_texture_check`, `lighting_consistency`, `material_state_continuity`, and `visual_score_threshold` gates. Empty regions, unknown profiles, unbounded scores, uninspectable passes, broken lighting/material continuity, missing macro/full-frame review, and non-certifying visual references fail closed. Eight regressions pass and the Wave18 pack validates at least 5,026 JSON files plus all 13 required files. Direct Codex review confirms W69 Normal v2 is coherent but mixed/non-promotable and W66 RealVisXL sample3 is stronger bounded whole-image support; neither is paired regional before/after authority. No generation, AWS, EC2, mask truth consumption/promotion, hard-gate rerun, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-015 / ITEM-W64-015`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields, proof_rows = reader.fieldnames or [], list(reader)
    record = {"Timestamp": iso, "Wave": "64", "Task": TRK, "Action": "Implemented fail-closed skin/material gates and reconciled bounded visual evidence.", "Files_Changed": "; ".join(evidence_paths), "Validation_Run": "8/8 regressions; 5026-plus JSON pack validation; 20/20 audit checks", "Result": DECISION, "Evidence_Path": rel(canonical), "Next_Action": "Proceed to TRK-W64-015 / ITEM-W64-015."}
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
