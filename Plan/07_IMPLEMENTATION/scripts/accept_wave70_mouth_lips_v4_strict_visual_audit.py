#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


RUN_STAMP = "20260707T224000-0500"
TIMESTAMP = "2026-07-07T22:40:00-05:00"
MASK_TYPE_ID = "mf70_mouth_lips"
TRACKER_ID = "TRK-W70-0018"
ITEM_ID = "ITEM-W70-0018"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Pending_Target_Runtime_Pending"
STATUS_DECISION = "mouth_lips_v4_candidate_strict_visual_alignment_pass_generated_output_pending_target_runtime_pending"
PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
V4_REPAIR_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_V2_20260707T223500-0500.json")


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def append_unique_csv_row(path: Path, row: list[str], marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(row)


def csv_update_row(path: Path, id_column: str, id_value: str, updates: dict[str, str], append_fields: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    changed = False
    for row in rows:
        if row.get(id_column) != id_value:
            continue
        for key, value in updates.items():
            if key in row:
                row[key] = value
                changed = True
        for key, value in append_fields.items():
            if key not in row:
                continue
            current = row.get(key, "")
            if value not in current:
                row[key] = f"{current}; {value}" if current else value
                changed = True
    if changed:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def update_ledgers(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    note = (
        " Mouth/lips v4 strict visual review accepted the source-landmark candidate as active-source aligned: "
        "it removes old mask speckles, targets visible outer upper/lower lip surfaces, excludes inner-mouth/teeth, "
        "and stays clear of nose, philtrum skin, chin, and cheeks. This is candidate-only; generated-output proof, "
        "target-runtime proof, and reference-matrix proof remain pending."
    )
    evidence_append = f"{evidence_rel}; {tracker_evidence_rel}"
    updates = {
        "Status": STATUS,
        "Status_Decision": STATUS_DECISION,
        "Coverage_Audit_Status": STATUS_DECISION,
        "Final_Render_Gate": "Blocked until repaired-candidate generated-output proof, target-runtime proof, and reference-image matrix proof are complete.",
    }
    append_fields = {
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Acceptance_Evidence": evidence_append,
        "Output_Artifact": panel_rel,
        "Notes": note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, updates, append_fields)


def update_mask_qa(root: Path, evidence_rel: str, tracker_evidence_rel: str, repair: dict[str, Any]) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_mouth_lips.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["source_landmark_repair_candidates"] = {
        "v1_evidence": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_20260707T221500-0500.json",
        "v2_evidence": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_V2_20260707T222500-0500.json",
        "v3_evidence": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_MOUTH_LIPS_SOURCE_LANDMARK_REPAIR_V2_20260707T223000-0500.json",
        "v4_evidence": rel(resolve(root, V4_REPAIR_EVIDENCE), root),
        "v4_result": repair.get("result"),
        "v4_protected_overlap_matrix_pass": repair.get("protected_overlap_matrix_pass"),
    }
    data["strict_visual_acceptance_v4"] = {
        "evidence": evidence_rel,
        "tracker_evidence": tracker_evidence_rel,
        "timestamp": TIMESTAMP,
        "result": "pass_candidate_strict_visual_alignment_pending_generated_output_and_target_runtime",
        "status": STATUS_DECISION,
        "semantic_mask_alignment_candidate_pass": True,
        "protected_overlap_matrix_pass": True,
        "generated_output_executed_for_v4": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "candidate_mask": repair["candidate_mask"],
        "candidate_overlay": repair["candidate_overlay"],
        "review_panel": repair["review_panel"],
        "findings": [
            "Candidate follows the visible closed-mouth upper and lower lip surfaces more tightly than the old disputed overlay.",
            "Candidate removes the old right-side speckle/fragment artifacts.",
            "Candidate excludes the protected inner-mouth/teeth slit and clears philtrum skin, nose, chin, and cheek protected regions.",
            "This acceptance applies only to the active single-anchor source image and does not certify generalized Wave70 mouth/lips masking.",
        ],
    }
    write_json(path, data)


def update_hydration(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    section = f"""## Wave70 mf70_mouth_lips V4 Strict Visual Candidate Acceptance - {TIMESTAMP}

Local fail-closed visual review accepted the `mf70_mouth_lips` v4 source-landmark candidate as source-aligned for the active single-anchor MOD-17 portrait. Evidence is `{evidence_rel}` with tracker evidence `{tracker_evidence_rel}` and review panel `{panel_rel}`.

The accepted candidate removes the old right-side speckles, targets the visible outer upper/lower lip surfaces, protects the inner-mouth/teeth strip, and stays clear of nose, philtrum skin, chin, and cheeks. No ComfyUI generation, EC2, AWS, GitHub, Civitai, Wave65, S3 publish, broad validator, or helper-evidence loop was run.

Current row status for `TRK-W70-0018` / `ITEM-W70-0018` is `{STATUS}`. Next action for this row is one bounded local generated-output proof with the v4 mask, or continue repairing another downgraded Wave70 mask with the same source-overlay/protected-boundary standard.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, evidence_rel)

    qa_index_row = (
        f"| W70-MF70-MOUTH-LIPS-V4-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP} | "
        "mf70_mouth_lips v4 candidate accepted by strict source-overlay visual review for the active single-anchor portrait; "
        "generated-output, target-runtime, and reference-matrix gates remain pending | "
        "mask_factory_strict_visual_acceptance | pass_candidate_no_final_promotion | "
        f"{evidence_rel} |"
    )
    append_unique_text(
        root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md",
        qa_index_row,
        f"W70-MF70-MOUTH-LIPS-V4-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
    )
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_mouth_lips v4 strict visual candidate acceptance",
            "Accepted the v4 source-landmark mouth/lips mask candidate after protected-overlap pass and strict visual review; generated-output, target-runtime, and matrix proof remain pending.",
            f"{evidence_rel}; {tracker_evidence_rel}; {panel_rel}",
            "direct visual inspection; protected-overlap matrix review; JSON parse; tracker/item row update",
            "PASS_CANDIDATE_STRICT_VISUAL_ALIGNMENT_NO_FINAL_PROMOTION",
            evidence_rel,
            "Run one bounded local generated-output proof for mf70_mouth_lips v4 or repair another downgraded Wave70 mask",
        ],
        f"W70_MF70_MOUTH_LIPS_V4_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), type=Path)
    args = parser.parse_args()
    root = args.project_root
    repair_path = resolve(root, V4_REPAIR_EVIDENCE)
    repair = read_json(repair_path)
    if repair.get("result") != "pass_candidate_protected_overlap_pending_strict_visual_review":
        raise RuntimeError(f"repair candidate is not ready for visual acceptance: {repair.get('result')}")

    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_MOUTH_LIPS_V4_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_MOUTH_LIPS_V4_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    evidence_rel = rel(evidence_path, root)
    tracker_evidence_rel = rel(tracker_path, root)
    panel_rel = repair["review_panel"]
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-MOUTH-LIPS-V4-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_mouth_lips_v4_strict_visual_fail_closed_acceptance",
        "implementation_script": rel(Path(__file__).resolve(), root),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "mask_type_id": MASK_TYPE_ID,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "candidate_repair_evidence": rel(repair_path, root),
        "candidate_repair_evidence_sha256": sha256_file(repair_path),
        "candidate_mask": repair["candidate_mask"],
        "candidate_mask_sha256": repair["candidate_mask_sha256"],
        "candidate_overlay": repair["candidate_overlay"],
        "candidate_overlay_sha256": repair["candidate_overlay_sha256"],
        "protected_overlap_matrix": repair["protected_overlap_matrix"],
        "protected_overlap_matrix_sha256": repair["protected_overlap_matrix_sha256"],
        "review_panel": panel_rel,
        "review_panel_sha256": repair["review_panel_sha256"],
        "protected_overlap_rows": repair["protected_overlap_rows"],
        "protected_overlap_matrix_pass": True,
        "visual_review_findings": [
            "Accepted: candidate follows the visible closed-mouth upper and lower lip surfaces without the old right-side speckle fragments.",
            "Accepted: candidate protects the central inner-mouth/teeth slit and does not cross into nose, philtrum skin, chin, or broad cheek regions.",
            "Accepted with boundary: this is a single-source candidate acceptance only and does not prove reference-matrix/generalized readiness.",
            "Blocked for final completion: generated-output proof with this v4 mask, target-runtime proof, and reference-image matrix proof have not been run.",
        ],
        "semantic_mask_alignment_candidate_pass": True,
        "generated_output_proof_present": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "result": "pass_candidate_strict_visual_alignment_pending_generated_output_and_target_runtime",
        "status_after_audit": STATUS,
        "status_decision_after_audit": STATUS_DECISION,
        "boundary": "This evidence accepts only the v4 mf70_mouth_lips candidate on the active source portrait. It does not certify Wave70 and does not replace generated-output or target-runtime proof.",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_MOUTH_LIPS_V4_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "status": STATUS,
            "status_decision": STATUS_DECISION,
            "evidence": evidence_rel,
            "review_panel": panel_rel,
            "local_only": True,
            "aws_contacted": False,
            "github_api_contacted": False,
            "civitai_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "result": evidence["result"],
            "next_required_action": "Run one bounded local generated-output proof with the v4 candidate mask or repair another downgraded Wave70 mask.",
        },
    )
    update_mask_qa(root, evidence_rel, tracker_evidence_rel, repair)
    update_ledgers(root, evidence_rel, tracker_evidence_rel, panel_rel)
    update_hydration(root, evidence_rel, tracker_evidence_rel, panel_rel)
    print(json.dumps({"result": evidence["result"], "evidence": evidence_rel, "tracker_evidence": tracker_evidence_rel, "panel": panel_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
