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
TRK, ITEM = "TRK-W64-010", "ITEM-W64-010"
STATUS = "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass"
DECISION = "identity_reference_blocked_multi_instance_occlusion_and_merge_rejection_supported"
GATES = ["identity_reference_check", "multi_instance_check", "occlusion_depth_check", "visual_reject_on_merge"]


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
    marker = "## Wave64 Row010 Character Identity And Multi-Character Separation"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "image_identity_multicharacter.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("IMAGE_IDENTITY_MULTICHARACTER_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    source_path = PLAN / "03_IMAGE_SYSTEM/CHARACTER_IDENTITY_AND_MULTICHARACTER_SPEC.md"
    w66_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_QA_20260711T035500-0500.json"
    w69_contact_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_HAND_CONTACT_VISUAL_CERTIFICATION_TWO_CHARACTER_HAND_TO_BODY_20260707T123500-0500.json"
    w69_robustness_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_WAVE25_TWO_CHARACTER_CONTACT_REFINE_ROBUSTNESS_VISUAL_QA_20260707T121500-0500.json"
    interaction_path = ROOT / "runtime_artifacts/multi_character_interaction/two_character_hand_to_body_w69/WAVE25_INTERACTION_VALIDATION_RECHECK.json"
    layout_path = ROOT / "runtime_artifacts/instance_layout/two_character_hand_to_body_w69/INSTANCE_LAYOUT_VALIDATION_RECHECK.json"
    graph_path = ROOT / "runtime_artifacts/physical_contact_graph/two_character_hand_to_body_w69/CONTACT_GRAPH_VALIDATION_RECHECK.json"
    prompt_paths = [PLAN.parent / f"PromptProfiles/base_generation/realvisxl_multisample_certification/realvisxl_two_character_openpose_contact_robustness_seed715202625{seed}.json" for seed in (3, 4)]
    source = source_path.read_text(encoding="utf-8-sig")
    w66, w69_contact, w69_robustness = load(w66_path), load(w69_contact_path), load(w69_robustness_path)
    interaction, layout, graph = load(interaction_path), load(layout_path), load(graph_path)
    baseline_image = ROOT / w66["baseline"]["image"]
    failure_images = [ROOT / sample["image"] for sample in w66["samples"]]
    refine_images = [ROOT / sample["image"] for sample in w69_robustness["generated_images"]]
    supplied_text = "\n".join(path.read_text(encoding="utf-8-sig") for path in (w66_path, w69_contact_path, w69_robustness_path, interaction_path, layout_path, graph_path, *prompt_paths))

    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    checks = {
        "IMC-001_row010_contract_exact": len(tracker_rows) == 1 and tracker_rows[0]["Validation_Method"].split("|") == GATES,
        "IMC-002_source_requires_per_character_reference_chain": all(token in source for token in ("unique character_id", "separate references", "separate person mask", "separate QA crops")),
        "IMC-003_source_separates_identity_from_instance_proof": "do not prove\nidentity preservation" in source,
        "IMC-004_w66_two_samples_exact": len(w66["samples"]) == 2,
        "IMC-005_w66_runtime_integrity_passes": w66["aggregate"]["technical_runtime_pass_count"] == 2,
        "IMC-006_w66_wrong_interactions_rejected": w66["aggregate"]["interaction_contract_pass_count"] == 0 and w66["aggregate"]["interaction_contract_fail_count"] == 2,
        "IMC-007_baseline_hash_exact": baseline_image.is_file() and sha(baseline_image) == w66["baseline"]["sha256"],
        "IMC-008_failure_image_hashes_exact": all(path.is_file() and sha(path) == sample["image_sha256"] for path, sample in zip(failure_images, w66["samples"])),
        "IMC-009_w69_participants_distinct": w69_contact["visual_review"]["participants_distinct"] is True,
        "IMC-010_w69_no_body_merge": w69_contact["visual_review"]["no_body_merge"] is True,
        "IMC-011_w69_local_support_only": w69_contact["local_support_passed"] is True and w69_contact["final_certification_allowed"] is False,
        "IMC-012_refine_pair_stable_without_merge": not w69_robustness["whole_image_visual_qa"]["failures"] and w69_robustness["qa_decision"]["local_robustness_pair_passed"] is True,
        "IMC-013_refine_image_hashes_exact": all(path.is_file() and sha(path) == sample["sha256"] for path, sample in zip(refine_images, w69_robustness["generated_images"])),
        "IMC-014_interaction_structure_pass": interaction["passed"] is True and interaction["character_instance_count"] == 2 and interaction["merge_prevention_check_count"] == 3,
        "IMC-015_depth_ownership_pass": interaction["depth_order_count"] == 2 and layout["passed"] is True and layout["depth_order_count"] == 2 and layout["region_ownership_map_count"] == 2,
        "IMC-016_contact_graph_pass": graph["passed"] is True and graph["contact_edge_count"] == 1,
        "IMC-017_prompt_profiles_distinct": all(path.is_file() for path in prompt_paths) and len({load(path)["request_patch_values"]["seed"] for path in prompt_paths}) == 2,
        "IMC-018_identity_reference_chain_absent": "character_id" not in supplied_text and "character_bible" not in supplied_text.lower(),
        "IMC-019_visual_reject_examples_bound": all(sample["visual_result"].startswith("fail_wrong_interaction") for sample in w66["samples"]),
        "IMC-020_no_false_identity_or_final_claim": w66["strict_decision"]["base_final_certification_allowed"] is False and w69_robustness["qa_decision"]["final_certification_allowed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed identity/multi-character invariants: " + ", ".join(failed))

    groups = {
        "identity_reference_check": ["IMC-002", "IMC-003", "IMC-017", "IMC-018", "IMC-020"],
        "multi_instance_check": ["IMC-001", "IMC-004", "IMC-009", "IMC-010", "IMC-014"],
        "occlusion_depth_check": ["IMC-007", "IMC-013", "IMC-015", "IMC-016", "IMC-020"],
        "visual_reject_on_merge": ["IMC-005", "IMC-006", "IMC-008", "IMC-011", "IMC-019"],
    }
    stamped = QA / f"IMAGE_IDENTITY_MULTICHARACTER_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_identity_multicharacter_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-010_image_identity_multicharacter.json"
    blocker = "No supplied artifact binds each generated person to a unique character_id, isolated identity references, and a per-character comparison crop."
    visual_review = {
        "reviewed_by": "Codex Desktop", "reviewed_existing_images_only": True,
        "images": [rel(path) for path in (baseline_image, *failure_images, *refine_images)],
        "findings": [
            "Exactly two visually distinct adults remain spatially separated in the baseline and failure exemplars.",
            "The two W66 failures correctly reject handshake/clasp interactions instead of the requested one-way upper-arm contact.",
            "The W69 contact crops preserve a stable open hand and separate sleeve/body boundary across three seeds.",
            "No reviewed image is paired to independent per-character identity references, so identity preservation is not certifiable.",
        ],
    }
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso, "wave": 64, "tracker_id": TRK, "item_id": ITEM,
        "status": STATUS, "row_complete": False, "qa_decision": DECISION,
        "validation_gates": {
            "identity_reference_check": {"status": "blocked_missing_per_character_reference_chain", "checks": groups["identity_reference_check"]},
            "multi_instance_check": {"status": "pass_reused_local_evidence", "checks": groups["multi_instance_check"]},
            "occlusion_depth_check": {"status": "pass_with_local_limits", "checks": groups["occlusion_depth_check"]},
            "visual_reject_on_merge": {"status": "pass_reject_logic_demonstrated", "checks": groups["visual_reject_on_merge"]},
        },
        "exact_blocker": blocker, "codex_visual_review": visual_review,
        "checks": [{"name": name, "result": "pass"} for name in checks], "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "candidate_or_gold_masks_consumed": False, "mask_promotion_performed": False, "wave71_activated": False, "jira_mutated": False},
        "project_completion": {"level": "BELOW_LEVEL_7", "full_project_complete": False, "final_certification_decision": "blocked"},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (source_path, w66_path, w69_contact_path, w69_robustness_path, interaction_path, layout_path, graph_path, *prompt_paths, baseline_image, *failure_images, *refine_images)],
        "next_action": "Proceed to TRK-W64-011 / ITEM-W64-011 in strict sequence. Reopen Row010 only when a per-character identity-reference chain and comparison crops exist; do not regenerate the demonstrated separation/contact scope.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_three_gates_identity_reference_blocked", "validation_gates": payload["validation_gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "exact_blocker": blocker, "codex_visual_review": visual_review, "project_completion": payload["project_completion"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row010 {stamp}: reused W66/W69 proof and Codex visual review to pass multi-instance, depth/occlusion, and merge-rejection gates; identity-reference preservation remains blocked because no unique character_id-to-reference-to-QA-crop chain exists; 20/20 split-state checks pass without regeneration."
    tags = ["wave64_row010_three_gates_supported", "identity_reference_proof_missing", "no_regeneration", "no_false_identity_claim", "row011_next"]
    tracker_paths = (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")
    item_paths = (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")
    tracker_changes = [rewrite_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in tracker_paths]
    item_changes = [rewrite_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags}, note) for path in item_paths]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row010 Character Identity And Multi-Character Separation - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Existing W66/W69 runtime and visual evidence plus direct Codex review support exactly two distinct people, separate body/region ownership, depth ordering, contact ownership, and strict rejection of wrong handshake/clasp interactions. These artifacts do not bind either generated person to a unique `character_id`, isolated identity references, and a per-character comparison crop, so `identity_reference_check` remains blocked. The split-state audit passes 20/20 checks. No new generation, AWS, EC2, mask use/promotion, Jira, or Wave71+ action occurred.

Next safe local action in strict sequence: `TRK-W64-011 / ITEM-W64-011`.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Reconciled multi-character identity, separation, occlusion, and merge-rejection evidence.", "; ".join(evidence_paths), "20/20 checks; three gates supported; identity reference blocked", DECISION, rel(canonical), "Proceed to TRK-W64-011 / ITEM-W64-011."])
    print(json.dumps({"status": STATUS, "row_complete": False, "gates": {gate: payload["validation_gates"][gate]["status"] for gate in GATES}, "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
