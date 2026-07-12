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
TRK, ITEM = "TRK-W64-012", "ITEM-W64-012"
STATUS = "Blocked_Gold_Mask_Dependency_Missing"
DECISION = "schemas_and_bounded_mask_behavior_partial_trusted_mask_authority_blocked"
GATES = ["mask_schema_check", "mask_boundary_visual_review", "inpaint_delta_check", "protected_region_preservation"]


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
    marker = "## Wave64 Row012 Mask Factory And Regional Control Integrity"
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
    canonical = QA / "image_mask_control.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_MASK_CONTROL_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "03_IMAGE_SYSTEM/MASK_FACTORY_SPEC.md"
    protocol_path = PLAN / "Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md"
    boundary_path = PLAN / "Instructions/QA/Evidence/Mask_Factory/Wave70/GOLD_MASK_DEPENDENCY_BOUNDARY_20260708T222123-0500.json"
    geometry_path = PLAN / "Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_LATEST.json"
    promotion_path = PLAN / "Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_LATEST.json"
    schema_paths = [PLAN / value for value in ("08_SCHEMAS/mask_factory_contract.schema.json", "08_SCHEMAS/mask_evidence.schema.json", "08_SCHEMAS/body_part_mask.schema.json", "08_SCHEMAS/contact_mask.schema.json")]
    contact_path = PLAN / "Instructions/QA/Evidence/Mask_Factory/W69_LOCAL_WAVE13_CONTACT_MASK_QA_TWO_CHARACTER_HAND_TO_BODY_20260707T122500-0500.json"
    inpaint_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_ROBUSTNESS_VISUAL_QA_20260707T034000-0500.json"
    certificate_path = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_INPAINT_BOUNDED_TARGET_RUNTIME_SMOKE_CERTIFICATE_20260711T031500-0500.json"
    source = source_path.read_text(encoding="utf-8-sig")
    boundary, geometry, promotion, contact, inpaint, certificate = map(load, (boundary_path, geometry_path, promotion_path, contact_path, inpaint_path, certificate_path))
    schemas = [load(path) for path in schema_paths]
    overlay_path = ROOT / contact["overlay"]["path"]
    inpaint_images = [ROOT / row["image_path"] for row in inpaint["artifacts_reviewed"]]
    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]

    checks = {
        "IMC-001_row012_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IMC-002_source_trusted_truth_boundary": all(token in source for token in ("supporting\nevidence", "must remain blocked", "must not be promoted")),
        "IMC-003_four_schemas_parse": len(schemas) == 4 and all(isinstance(row, dict) for row in schemas),
        "IMC-004_schema_titles_unique": len({row.get("title") for row in schemas}) == 4,
        "IMC-005_gold_boundary_exact": boundary["blocker_code"] == STATUS and boundary["manual_gold_mask_status"] == "Manual_Gold_Mask_Work_In_Progress",
        "IMC-006_candidate_truth_forbidden": boundary["candidate_mask_truth_consumption_allowed"] is False,
        "IMC-007_no_mask_promotion_or_wave71": boundary["masks_promoted"] is False and boundary["wave71_activation_allowed_from_candidate_or_guarded_masks"] is False,
        "IMC-008_boundary_records_no_hard_gate_rerun": boundary["hard_gates_rerun"] is False,
        "IMC-009_geometry_gate_zero_pass_like": geometry["checked_row_count"] == 332 and geometry["pass_like_row_count"] == 0 and geometry["result"] == "pass_wave70_mask_geometry_hard_gate",
        "IMC-010_promotion_gate_zero_pass_like": promotion["checked_row_count"] == 332 and promotion["pass_like_row_count"] == 0 and promotion["result"] == "pass_wave70_mask_promotion_hard_gate",
        "IMC-011_contact_mask_local_qa_pass": contact["result"] == "pass_local_contact_mask_qa" and contact["local_only"] is True,
        "IMC-012_contact_mask_metrics_bounded": contact["contact_mask"]["contact_pixel_count"] > 0 and contact["overlap"]["outside_participant_percent"] <= contact["overlap"]["max_outside_participant_percent"],
        "IMC-013_contact_overlay_hash_exact": overlay_path.is_file() and sha(overlay_path) == contact["overlay"]["sha256"],
        "IMC-014_contact_qa_non_certifying": "Local mask QA only" in contact["certification_boundary"],
        "IMC-015_inpaint_two_seed_local_pass": inpaint["robustness_summary"]["sample_count"] == 2 and inpaint["robustness_summary"]["passed_with_notes_count"] == 2 and inpaint["overall_result"] == "pass_with_notes_for_local_robustness",
        "IMC-016_inpaint_image_hashes_exact": all(path.is_file() and sha(path) == row["sha256"] for path, row in zip(inpaint_images, inpaint["artifacts_reviewed"])),
        "IMC-017_protected_regions_stable": all(any(token in row["whole_image_findings"]["hair_clothing_background"] for token in ("remain stable", "remain unchanged")) for row in inpaint["artifacts_reviewed"]),
        "IMC-018_no_hard_mask_edges_observed": all("no obvious hard" in row["whole_image_findings"]["mask_edge_blending"].lower() for row in inpaint["artifacts_reviewed"]),
        "IMC-019_bounded_certificate_excludes_authority": certificate["final_lane_certification"] is False and certificate["mask_promotion_allowed"] is False and "body_hand_contact_or_whole_body_authority" in certificate["explicit_exclusions"],
        "IMC-020_no_false_mask_readiness": certificate["wave71_activation_allowed"] is False and certificate["full_route_certification"] is False and boundary["masks_promoted"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed mask-control invariants: " + ", ".join(failed))

    groups = {
        "mask_schema_check": ["IMC-001", "IMC-002", "IMC-003", "IMC-004", "IMC-005"],
        "mask_boundary_visual_review": ["IMC-006", "IMC-011", "IMC-012", "IMC-013", "IMC-014"],
        "inpaint_delta_check": ["IMC-008", "IMC-015", "IMC-016", "IMC-018", "IMC-019"],
        "protected_region_preservation": ["IMC-007", "IMC-009", "IMC-010", "IMC-017", "IMC-020"],
    }
    stamped = QA / f"IMAGE_MASK_CONTROL_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_mask_control_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-012_image_mask_control.json"
    blocker = "Manual trusted body/body-part gold masks are not ready or validated; bounded candidate/contact/inpaint evidence cannot establish spatial truth or promotion authority."
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "mask_schema_check": {"status": "partial_static_schemas_no_trusted_authority", "checks": groups["mask_schema_check"]},
            "mask_boundary_visual_review": {"status": "partial_local_contact_overlay_non_certifying", "checks": groups["mask_boundary_visual_review"]},
            "inpaint_delta_check": {"status": "partial_bounded_inpaint_preservation", "checks": groups["inpaint_delta_check"]},
            "protected_region_preservation": {"status": "partial_local_preservation_no_promotion", "checks": groups["protected_region_preservation"]},
        },
        "exact_blocker": blocker,
        "codex_visual_review": {
            "reviewed_existing_artifacts_only": True, "artifacts": [rel(overlay_path), *[rel(path) for path in inpaint_images]],
            "findings": [
                "The contact overlay is localized around the hand and sleeve interface and does not cover either whole person.",
                "Both no-mouth inpaint samples retain face, gaze, clothing, hair, and background without an obvious hard edit boundary.",
                "These are bounded behavior observations and do not validate body/body-part mask truth against manual gold annotations.",
            ],
        },
        "hard_gate_read_only_snapshot": {"geometry_sha256": sha(geometry_path), "promotion_sha256": sha(promotion_path), "checked_rows_each": 332, "pass_like_rows_each": 0, "rerun_by_this_audit": False},
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"candidate_masks_consumed_as_truth": False, "hard_gates_rerun": False, "mask_promotion_performed": False, "new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, protocol_path, boundary_path, geometry_path, promotion_path, *schema_paths, contact_path, inpaint_path, certificate_path, overlay_path, *inpaint_images)],
        "next_action": "Proceed to TRK-W64-013 / ITEM-W64-013 in strict sequence. Reopen Row012 only after manual gold masks are declared ready and pass intake validation; do not rerun hard gates or consume candidate masks as truth.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(boundary_path), rel(contact_path), rel(inpaint_path), rel(certificate_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_partial_support_gold_mask_dependency_blocked", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "exact_blocker": blocker, "codex_visual_review": payload["codex_visual_review"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row012 {stamp}: static schemas and bounded local contact-mask/inpaint/protected-region evidence are partial only; manual trusted gold-mask dependency remains blocked, hard gates stayed read-only at 332 rows and zero pass-like rows, and 20/20 split-state checks pass without mask truth consumption or promotion."
    tags = ["wave64_row012_partial_support", "gold_mask_dependency_blocked", "hard_gates_not_rerun", "no_mask_promotion", "row013_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row012 Mask Factory And Regional Control Integrity - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Four mask schemas parse, and bounded historical contact-mask, inpaint-delta, and protected-region evidence provides local support. Direct Codex review confirms a localized hand/sleeve overlay and two stable no-mouth inpaint outputs without obvious hard boundaries. These artifacts are candidate/bounded evidence, not trusted body/body-part spatial truth. Manual gold masks remain in progress, no masks are promoted, and the latest Wave70 geometry/promotion snapshots remained read-only at 332 checked rows and zero pass-like rows. The split-state audit passes 20/20 checks. No hard-gate rerun, new generation, AWS, EC2, mask truth consumption/promotion, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-013 / ITEM-W64-013`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Reconciled mask schemas, bounded visual behavior, and trusted-mask dependency.", "; ".join(evidence_paths), "20/20 checks; four gates partial; gold mask dependency blocked", DECISION, rel(canonical), "Proceed to TRK-W64-013 / ITEM-W64-013."])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
