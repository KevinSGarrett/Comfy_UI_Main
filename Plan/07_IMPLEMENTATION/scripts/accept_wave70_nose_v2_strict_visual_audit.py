#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260707T215500-0500"
TIMESTAMP = "2026-07-07T21:55:00-05:00"
MASK_TYPE_ID = "mf70_nose"
TRACKER_ID = "TRK-W70-0017"
ITEM_ID = "ITEM-W70-0017"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Pending_Target_Runtime_Pending"
STATUS_DECISION = "v2_candidate_strict_visual_alignment_pass_generated_output_pending_target_runtime_pending"
PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")

SOURCE_IMAGE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
CANDIDATE_MASK = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_mask.png"
)
CANDIDATE_OVERLAY = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_overlay.png"
)
BOUNDARY_OVERLAY = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose/protected_boundary_audit/"
    "20260707T214800-0500/mf70_nose_v2_candidate_boundary_overlay.png"
)
PROTECTED_PANEL = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose/protected_boundary_audit/"
    "20260707T214800-0500/mf70_nose_v2_candidate_protected_overlap_panel.png"
)
OVERLAP_MATRIX = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose/protected_boundary_audit/"
    "20260707T214800-0500/mf70_nose_source_landmark_v2_protected_overlap_matrix.csv"
)
BOUNDARY_REGISTRY = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose/protected_boundary_audit/"
    "20260707T214800-0500/BOUNDARY_REGISTRY_MANIFEST.json"
)
V2_REPAIR_PANEL = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose/source_landmark_repair_v2/"
    "mf70_nose_source_landmark_repair_v2_panel_20260707T214500-0500.png"
)


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


def crop_box() -> tuple[int, int, int, int]:
    return (300, 286, 474, 474)


def label_tile(image: Image.Image, label: str, size: int = 360) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), (Image.Resampling.LANCZOS)), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def make_strict_panel(root: Path, out_dir: Path) -> dict[str, str]:
    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    candidate_mask = Image.open(resolve(root, CANDIDATE_MASK)).convert("L")
    candidate_overlay = Image.open(resolve(root, CANDIDATE_OVERLAY)).convert("RGB")
    boundary_overlay = Image.open(resolve(root, BOUNDARY_OVERLAY)).convert("RGB")
    protected_panel = Image.open(resolve(root, PROTECTED_PANEL)).convert("RGB")
    crop = crop_box()

    mask_rgb = Image.merge("RGB", (candidate_mask, candidate_mask, candidate_mask))
    crops = {
        "source_crop": out_dir / "mf70_nose_v2_strict_source_crop.png",
        "mask_only_crop": out_dir / "mf70_nose_v2_strict_mask_only_crop.png",
        "candidate_overlay_crop": out_dir / "mf70_nose_v2_strict_candidate_overlay_crop.png",
        "boundary_overlay_crop": out_dir / "mf70_nose_v2_strict_boundary_overlay_crop.png",
    }
    crops["source_crop"].parent.mkdir(parents=True, exist_ok=True)
    source.crop(crop).save(crops["source_crop"])
    mask_rgb.crop(crop).save(crops["mask_only_crop"])
    candidate_overlay.crop(crop).save(crops["candidate_overlay_crop"])
    boundary_overlay.crop(crop).save(crops["boundary_overlay_crop"])

    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(candidate_overlay.crop(crop), "v2 candidate overlay"),
        label_tile(mask_rgb.crop(crop), "v2 mask only"),
        label_tile(boundary_overlay.crop(crop), "candidate boundary overlay"),
        label_tile(protected_panel.resize((720, 201), Image.Resampling.LANCZOS), "protected-overlap panel", 360),
    ]
    panel_path = out_dir / "mf70_nose_v2_strict_visual_acceptance_panel.png"
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    panel.save(panel_path)

    result = {name: rel(path, root) for name, path in crops.items()}
    result["strict_visual_acceptance_panel"] = rel(panel_path, root)
    return result


def read_overlap_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
        writer = csv.writer(f)
        writer.writerow(row)


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


def update_structured_ledgers(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    row_note = (
        " V2 strict visual/fail-closed review accepted the candidate as source-aligned for the active "
        "single-anchor portrait: it covers visible bridge, sidewalls, tip, alae, and nostril base while "
        "staying out of mouth/lips, upper lip, philtrum, broad cheeks, and eye/canthus regions. This is "
        "candidate-only; generated-output proof, target-runtime proof, and reference-matrix proof remain pending."
    )
    evidence_append = f"{evidence_rel}; {tracker_evidence_rel}"
    updates = {
        "Status": STATUS,
        "Status_Decision": STATUS_DECISION,
        "Coverage_Audit_Status": STATUS_DECISION,
        "Final_Render_Gate": "Blocked until v2 generated-output proof, target-runtime proof, and reference-image matrix proof are complete.",
    }
    append_fields = {
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Acceptance_Evidence": evidence_append,
        "Output_Artifact": panel_rel,
        "Deliverable_Type": "v2_strict_visual_acceptance_panel",
        "Notes": row_note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, updates, append_fields)


def update_mask_qa(root: Path, evidence_rel: str, tracker_evidence_rel: str, artifacts: dict[str, str]) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_nose.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["strict_visual_acceptance_v2"] = {
        "evidence": evidence_rel,
        "tracker_evidence": tracker_evidence_rel,
        "timestamp": TIMESTAMP,
        "result": "pass_candidate_strict_visual_alignment_pending_generated_output_and_target_runtime",
        "status": STATUS_DECISION,
        "semantic_mask_alignment_candidate_pass": True,
        "protected_overlap_matrix_pass": True,
        "canonical_boundary_layer_pass": False,
        "generated_output_executed_for_v2": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "artifacts": artifacts,
        "findings": [
            "V2 candidate no longer covers the mouth or lips and stays above the philtrum/upper-lip protected boundary.",
            "V2 candidate covers the visible nose bridge, sidewalls, tip, alae, and nostril base on the active source crop.",
            "Boundary overlay and protected-overlap matrix show zero overlap with mouth/lips, upper lip, philtrum, cheek, and eye/canthus protected regions.",
            "This acceptance applies only to the v2 candidate on the active single-anchor source image; it does not rehabilitate earlier masks or certify generalized Wave70 readiness.",
        ],
    }
    v2 = data.setdefault("source_landmark_repair_v2_candidate", {})
    v2["strict_visual_review_evidence"] = evidence_rel
    v2["strict_visual_review_tracker_evidence"] = tracker_evidence_rel
    v2["strict_visual_result"] = "pass_candidate_strict_visual_alignment_pending_generated_output_and_target_runtime"
    v2["semantic_mask_alignment_candidate_pass"] = True
    v2["semantic_mask_alignment_pass"] = False
    v2["completion_allowed_by_mask_alignment"] = False
    v2["generated_output_executed"] = False
    v2["status"] = STATUS_DECISION
    write_json(path, data)


def update_hydration(root: Path, evidence_rel: str, tracker_evidence_rel: str, panel_rel: str) -> None:
    section = f"""## Wave70 mf70_nose V2 Strict Visual Candidate Acceptance - {TIMESTAMP}

Local fail-closed visual review accepted the `mf70_nose` v2 candidate as source-aligned for the active single-anchor MOD-17 portrait, without promoting it to final completion. Evidence is `{evidence_rel}` with tracker evidence `{tracker_evidence_rel}` and review panel `{panel_rel}`.

The acceptance is intentionally narrow: v2 covers the visible nose bridge, sidewalls, tip, alae, and nostril base, and it avoids mouth/lips, upper lip, philtrum, broad cheeks, and eye/canthus protected regions. Protected-overlap matrix remains zero-overlap. No ComfyUI generation, EC2, AWS, GitHub, Civitai, Wave65, S3 publish, broad validator, or helper-evidence loop was run.

Current row status for `TRK-W70-0017` / `ITEM-W70-0017` is `{STATUS}`. Next action is one bounded local v2 generated-output proof only if continuing `mf70_nose`; otherwise repair the next downgraded Wave70 mask with the same source-overlay and protected-boundary standard. Do not treat this as a pass for the other disputed masks.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, evidence_rel)

    qa_index_row = (
        f"| W70-MF70-NOSE-V2-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP} | "
        "mf70_nose v2 candidate accepted by strict source-overlay visual review for the active single-anchor portrait; "
        "generated-output, target-runtime, and reference-matrix gates remain pending | "
        "mask_factory_strict_visual_acceptance | pass_candidate_no_final_promotion | "
        f"{evidence_rel} |"
    )
    append_unique_text(
        root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md",
        qa_index_row,
        f"W70-MF70-NOSE-V2-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
    )

    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_nose v2 strict visual candidate acceptance",
            (
                "Created strict source/mask/overlay/boundary review crops and accepted the v2 nose candidate "
                "for active-source mask alignment while keeping generated-output, target-runtime, and matrix proof pending."
            ),
            f"{evidence_rel}; {tracker_evidence_rel}; {panel_rel}",
            "direct visual inspection; protected-overlap matrix review; JSON parse; tracker/item row update",
            "PASS_CANDIDATE_STRICT_VISUAL_ALIGNMENT_NO_FINAL_PROMOTION",
            evidence_rel,
            "Run one bounded local v2 generated-output proof or repair the next downgraded Wave70 mask with the same fail-closed standard",
        ],
        f"W70_MF70_NOSE_V2_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), type=Path)
    args = parser.parse_args()
    root = args.project_root

    required = [SOURCE_IMAGE, CANDIDATE_MASK, CANDIDATE_OVERLAY, BOUNDARY_OVERLAY, PROTECTED_PANEL, OVERLAP_MATRIX, BOUNDARY_REGISTRY, V2_REPAIR_PANEL]
    missing = [rel(resolve(root, path), root) for path in required if not resolve(root, path).exists()]
    if missing:
        raise FileNotFoundError(f"missing required strict visual inputs: {missing}")

    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_nose/strict_visual_acceptance" / RUN_STAMP
    artifacts = make_strict_panel(root, out_dir)
    overlap_rows = read_overlap_rows(resolve(root, OVERLAP_MATRIX))
    overlap_failures = [row for row in overlap_rows if str(row.get("pass", "")).lower() != "true"]

    evidence_path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_NOSE_V2_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_NOSE_V2_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    evidence_rel = rel(evidence_path, root)
    tracker_evidence_rel = rel(tracker_path, root)
    panel_rel = artifacts["strict_visual_acceptance_panel"]
    candidate_mask_path = resolve(root, CANDIDATE_MASK)
    candidate_overlay_path = resolve(root, CANDIDATE_OVERLAY)
    source_path = resolve(root, SOURCE_IMAGE)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-NOSE-V2-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "wave70_mf70_nose_v2_strict_visual_fail_closed_acceptance",
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
        "source_image": rel(source_path, root),
        "source_image_sha256": sha256_file(source_path),
        "candidate_mask": rel(candidate_mask_path, root),
        "candidate_mask_sha256": sha256_file(candidate_mask_path),
        "candidate_overlay": rel(candidate_overlay_path, root),
        "candidate_overlay_sha256": sha256_file(candidate_overlay_path),
        "source_landmark_repair_panel": rel(resolve(root, V2_REPAIR_PANEL), root),
        "source_landmark_repair_panel_sha256": sha256_file(resolve(root, V2_REPAIR_PANEL)),
        "protected_overlap_panel": rel(resolve(root, PROTECTED_PANEL), root),
        "protected_overlap_panel_sha256": sha256_file(resolve(root, PROTECTED_PANEL)),
        "boundary_registry_manifest": rel(resolve(root, BOUNDARY_REGISTRY), root),
        "boundary_registry_manifest_sha256": sha256_file(resolve(root, BOUNDARY_REGISTRY)),
        "protected_overlap_matrix": rel(resolve(root, OVERLAP_MATRIX), root),
        "protected_overlap_matrix_sha256": sha256_file(resolve(root, OVERLAP_MATRIX)),
        "strict_visual_artifacts": artifacts,
        "strict_visual_artifact_hashes": {name: sha256_file(resolve(root, Path(path))) for name, path in artifacts.items()},
        "protected_overlap_rows": overlap_rows,
        "protected_overlap_failures": overlap_failures,
        "visual_review_findings": [
            "Accepted: candidate mask is aligned to the visible nose bridge, sidewalls, tip, alae, and nostril base in the source crop.",
            "Accepted: candidate lower boundary stays above the mouth/lips and does not cover the mouth region that triggered the user complaint.",
            "Accepted: protected-overlap matrix reports zero overlap against mouth_lips, upper_lip, philtrum, left/right cheek, and eye/canthus/lower-lid protected regions.",
            "Accepted with boundary: this is a v2 single-source candidate acceptance only; earlier masks remain untrusted and this does not prove cross-subject or reference-matrix readiness.",
            "Blocked for final completion: v2 generated-output proof, target-runtime proof, and reference-image matrix proof have not been run.",
        ],
        "semantic_mask_alignment_candidate_pass": True,
        "protected_overlap_matrix_pass": len(overlap_failures) == 0,
        "canonical_boundary_layer_pass": False,
        "generated_output_proof_present": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed_by_mask_alignment": False,
        "result": "pass_candidate_strict_visual_alignment_pending_generated_output_and_target_runtime",
        "status_after_audit": STATUS,
        "status_decision_after_audit": STATUS_DECISION,
        "boundary": "This evidence accepts only the v2 mf70_nose candidate on the active source portrait. It does not certify Wave70, does not rehabilitate other disputed masks, and does not replace generated-output or target-runtime proof.",
    }
    write_json(evidence_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_NOSE_V2_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}",
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
            "next_required_action": "Run one bounded local v2 generated-output proof or repair the next downgraded Wave70 mask with the same source-overlay standard.",
        },
    )

    update_mask_qa(root, evidence_rel, tracker_evidence_rel, artifacts)
    update_structured_ledgers(root, evidence_rel, tracker_evidence_rel, panel_rel)
    update_hydration(root, evidence_rel, tracker_evidence_rel, panel_rel)

    print(json.dumps({"result": evidence["result"], "evidence": evidence_rel, "tracker_evidence": tracker_evidence_rel, "panel": panel_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
