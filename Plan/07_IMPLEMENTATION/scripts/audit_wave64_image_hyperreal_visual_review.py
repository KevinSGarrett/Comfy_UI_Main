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
TRK, ITEM = "TRK-W64-016", "ITEM-W64-016"
STATUS = "Blocked_No_Promoted_Image_Set_And_Upstream_Quality_Authority_Missing"
DECISION = "row016_contract_pass_bounded_certificates_reconciled_no_promoted_outputs"
GATES = ["technical_image_qa", "visual_review_scorecard", "prompt_alignment", "artifact_hash_manifest", "promotion_decision"]


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
    marker = "## Wave64 Row016 Strict Hyperreal Image Visual Certification"
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
    canonical = QA / "image_hyperreal_visual_review.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_HYPERREAL_VISUAL_REVIEW_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    protocol_path = PLAN / "Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md"
    schema_path = PLAN / "08_SCHEMAS/image_hyperreal_visual_certification.schema.json"
    example_path = PLAN / "09_EXAMPLES/image_hyperreal_visual_certification.example.json"
    validator_path = PLAN / "07_IMPLEMENTATION/scripts/validate_image_hyperreal_visual_certification.py"
    tests_path = PLAN / "Instructions/QA/Scripts/test_image_hyperreal_visual_certification.py"
    matrix_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json"
    canny_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_CANNY_LANE_FINAL_CERTIFICATION_20260711T024500-0500.json"
    depth_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_DEPTH_LANE_FINAL_CERTIFICATION_20260711T000500-0500.json"
    lineart_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_LINEART_LANE_FINAL_CERTIFICATION_20260711T004700-0500.json"
    promotion_path = PLAN / "07_IMPLEMENTATION/manifests/generated/W69_LOCAL_IMAGE_QA_ORCHESTRATOR_PROMOTION_MANIFEST_20260707T102500-0500.json"
    superseded_path = PLAN / "07_IMPLEMENTATION/manifests/generated/W69_LOCAL_IMAGE_QA_ORCHESTRATOR_PROMOTION_MANIFEST_SUPERSEDED_20260707T103500-0500.json"
    readiness_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_POST_ALIGNMENT_20260709T210200-0500.json"
    queue_path = PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
    anatomy_path = QA / "image_body_anatomy.json"
    skin_path = QA / "image_skin_material.json"
    contact_path = QA / "image_contact_physics.json"

    protocol = protocol_path.read_text(encoding="utf-8-sig")
    schema, example, matrix, canny, depth, lineart, promotion, superseded, readiness, queue, anatomy, skin, contact = map(load, (schema_path, example_path, matrix_path, canny_path, depth_path, lineart_path, promotion_path, superseded_path, readiness_path, queue_path, anatomy_path, skin_path, contact_path))
    validator = validator_path.read_text(encoding="utf-8-sig")
    matrix_images = [(ROOT / sample["image_path"], sample["image_sha256"]) for sample in matrix["samples"]]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    unit = run(tests_path)
    example_validation = run(validator_path, "--input", example_path)
    required_schema = set(schema.get("required", []))
    bounded_ids = set(queue["selection_policy"]["bounded_certification_present_lane_ids"])
    readiness_time = datetime.fromisoformat(readiness["created_at"])
    canny_time = datetime.fromisoformat(canny["timestamp"])
    checks = {
        "IHV-001_row016_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IHV-002_protocol_binds_five_gates": all(gate in protocol for gate in GATES) and "does not silently become per-image promotion" in protocol,
        "IHV-003_schema_requires_five_gates": set(GATES).issubset(required_schema),
        "IHV-004_schema_hash_and_upstream_constraints": schema["properties"]["artifact_hash_manifest"]["allOf"][1]["properties"]["artifacts"]["items"]["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}$" and schema["properties"]["upstream_quality_rows"]["minItems"] == 3,
        "IHV-005_validator_requires_all_gates": all(gate in validator for gate in GATES),
        "IHV-006_validator_requires_nonempty_promoted_outputs": "nonempty hash-bound promoted outputs" in validator,
        "IHV-007_validator_requires_prompt_alignment": "explicit prompt alignment evidence" in validator,
        "IHV-008_validator_requires_strict_score": "strict visual score threshold" in validator,
        "IHV-009_validator_requires_complete_upstream": "complete upstream quality rows" in validator,
        "IHV-010_eight_regressions_pass": unit.returncode == 0 and "Ran 8 tests" in unit.stderr and "OK" in unit.stderr,
        "IHV-011_blocked_example_validates": example_validation.returncode == 0 and example["promotion_decision"]["decision"] == "not_promoted",
        "IHV-012_promotion_manifests_empty": all(row["promotion_allowed"] is False and row["promoted_outputs"] == [] for row in (promotion, superseded)),
        "IHV-013_matrix_is_bounded_not_project_final": matrix["certification_status"] == "matrix_sample_set_certified" and matrix["not_project_final_done"] is True,
        "IHV-014_matrix_artifact_hashes_exact": len(matrix_images) == 3 and all(path.is_file() and sha(path) == expected for path, expected in matrix_images),
        "IHV-015_canny_bounded_final_only": canny["final_lane_certification"] is True and canny["full_project_certification"] is False and len(canny["excluded_scope"]) >= 1,
        "IHV-016_depth_lineart_bounded_final_only": all(row["final_lane_certification"] is True and row["full_project_certification"] is False for row in (depth, lineart)),
        "IHV-017_readiness_timing_reconciled": readiness_time < canny_time and {"sdxl_realvisxl_controlnet_canny_lane", "sdxl_realvisxl_controlnet_depth_lane", "sdxl_realvisxl_controlnet_lineart_lane"}.issubset(bounded_ids),
        "IHV-018_queue_remains_bounded": len(queue["lanes"]) == 10 and len(bounded_ids) == 5 and queue["runtime_boundary"]["ec2_start_allowed_by_queue_file"] is False,
        "IHV-019_upstream_rows_incomplete": all(row["row_complete"] is False for row in (anatomy, skin, contact)),
        "IHV-020_no_new_runtime_or_promotion": promotion["ec2_started"] is False and promotion["promotion_allowed"] is False and example["promotion_decision"]["promoted_outputs"] == [],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed hyperreal-certification invariants: " + ", ".join(failed))

    groups = {
        "technical_image_qa": ["IHV-001", "IHV-003", "IHV-005", "IHV-015"],
        "visual_review_scorecard": ["IHV-002", "IHV-008", "IHV-010", "IHV-013"],
        "prompt_alignment": ["IHV-007", "IHV-011", "IHV-016", "IHV-019"],
        "artifact_hash_manifest": ["IHV-004", "IHV-006", "IHV-009", "IHV-014"],
        "promotion_decision": ["IHV-012", "IHV-017", "IHV-018", "IHV-020"],
    }
    stamped = QA / f"IMAGE_HYPERREAL_VISUAL_REVIEW_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_hyperreal_visual_review_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-016_image_hyperreal_visual_review.json"
    blocker = "No current promoted output exists, no single certificate binds all five Row016 gates for the same image scope, and Rows013-015 remain incomplete; bounded lane and matrix certificates cannot be generalized into per-image or full-project promotion."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "technical_image_qa": {"status": "partial_bounded_lane_and_matrix_technical_qa_pass", "checks": groups["technical_image_qa"]},
            "visual_review_scorecard": {"status": "partial_bounded_visual_scorecards_pass_with_notes", "checks": groups["visual_review_scorecard"]},
            "prompt_alignment": {"status": "blocked_no_single_promoted_image_record_binds_explicit_prompt_alignment", "checks": groups["prompt_alignment"]},
            "artifact_hash_manifest": {"status": "partial_bounded_artifact_hashes_verified_no_promoted_set", "checks": groups["artifact_hash_manifest"]},
            "promotion_decision": {"status": "blocked_no_current_promoted_outputs_and_upstream_rows_incomplete", "checks": groups["promotion_decision"]},
        },
        "exact_blocker": blocker,
        "certificate_reconciliation": {
            "current_promoted_output_count": 0,
            "bounded_certified_lane_ids": sorted(bounded_ids),
            "matrix_certification": "bounded_three_sample_pass_with_notes_not_project_final",
            "historical_readiness_note": "The 2026-07-09 readiness snapshot predates the 2026-07-11 Canny, Depth, and Lineart final lane certificates; it remains historical evidence and is not rewritten.",
            "scope_boundary": "No new visual judgment was substituted for existing strict QA; certificates were reconciled only within their explicit bounded scopes.",
        },
        "test_results": {"unit_tests": {"run": 8, "passed": 8}, "contract_example_validation": "pass"},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "mask_promotion_performed": False, "image_promotion_performed": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (protocol_path, schema_path, example_path, validator_path, tests_path, matrix_path, canny_path, depth_path, lineart_path, promotion_path, superseded_path, readiness_path, queue_path, anatomy_path, skin_path, contact_path, *[path for path, _ in matrix_images])],
        "next_action": "Proceed to TRK-W64-017 / ITEM-W64-017 in strict sequence. Reopen Row016 only for a scope-matched image record binding all five gates and a nonempty hash-verified promoted-output set after upstream quality authority clears.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(matrix_path), rel(canny_path), rel(depth_path), rel(lineart_path), rel(promotion_path), rel(queue_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": DECISION, "test_results": payload["test_results"], "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "implementation": {"required_machine_gates": GATES, "fail_closed_promotion": True, "per_image_scope_binding_required": True}, "exact_blocker": blocker, "certificate_reconciliation": payload["certificate_reconciliation"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row016 {stamp}: implemented the five-field image certification contract, passed 8/8 regressions, reconciled bounded matrix/lane certificates and the dated readiness snapshot, and preserved no-promotion state because promoted outputs are empty and Rows013-015 are incomplete; 20/20 checks pass."
    tags = ["wave64_row016_certification_contract_implemented", "bounded_certificates_reconciled", "no_promoted_outputs", "upstream_quality_incomplete", "row017_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row016 Strict Hyperreal Image Visual Certification - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The visual-review protocol now requires one scope-matched machine record binding `technical_image_qa`, `visual_review_scorecard`, `prompt_alignment`, `artifact_hash_manifest`, and `promotion_decision`. Promotion fails closed without strict scores, explicit prompt alignment, nonempty hash-bound outputs, and completed upstream quality rows. Eight regressions pass and the split-state audit passes 20/20 checks. Existing RealVisXL matrix and Canny/Depth/Lineart certificates remain valid only for their bounded scopes; both W69 promotion manifests contain zero promoted outputs, and Rows013-015 remain incomplete. No generation, AWS, EC2, mask/image promotion, hard-gate rerun, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-017 / ITEM-W64-017`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        proof_fields, proof_rows = reader.fieldnames or [], list(reader)
    record = {"Timestamp": iso, "Wave": "64", "Task": TRK, "Action": "Implemented strict image certification contract and reconciled bounded certificates.", "Files_Changed": "; ".join(evidence_paths), "Validation_Run": "8/8 regressions; contract validation; 20/20 audit checks", "Result": DECISION, "Evidence_Path": rel(canonical), "Next_Action": "Proceed to TRK-W64-017 / ITEM-W64-017."}
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
