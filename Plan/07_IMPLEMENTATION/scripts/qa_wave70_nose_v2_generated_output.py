#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260707T220500-0500"
TIMESTAMP = "2026-07-07T22:05:00-05:00"
MASK_TYPE_ID = "mf70_nose"
TRACKER_ID = "TRK-W70-0017"
ITEM_ID = "ITEM-W70-0017"
STATUS = "Mask_Alignment_Candidate_Pass_Generated_Output_Safe_Target_Runtime_Pending"
STATUS_DECISION = "v2_candidate_strict_visual_alignment_pass_generated_output_safe_target_runtime_pending_reference_matrix_pending"

SOURCE_IMAGE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
CANDIDATE_OVERLAY = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_overlay.png"
)
CANDIDATE_MASK = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v2_20260707T214500-0500/"
    "wave70_mf70_nose_mask.png"
)
PROMPT_PROFILE = Path("PromptProfiles/base_generation/inpaint_detail_v4_robustness/inpaint_wave70_mf70_nose_v2_source_landmark_seed210820.json")
RUN_PACKAGE = Path("runtime_artifacts/run_packages/wave70_mf70_nose_v2_source_landmark_seed210820/RUN_PACKAGE_MANIFEST.json")
RUNTIME_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_MF70_NOSE_V2_SOURCE_LANDMARK_SEED210820_EXECUTE_20260707T220000-0500.json")
PULLBACK_DIR = Path("Plan/Instructions/Operations/Pulled_Back_Artifacts/wave70_mf70_nose_v2_source_landmark_seed210820_20260707T211135-0500")
GENERATED_OUTPUT = PULLBACK_DIR / "images/codex_wave70_mf70_nose_v2_source_landmark_seed210820_00001_.png"
MASK_PREVIEW = PULLBACK_DIR / "images/codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_mask_preview_00026_.png"
STRICT_VISUAL_ACCEPTANCE = Path("Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_NOSE_V2_STRICT_VISUAL_ACCEPTANCE_20260707T215500-0500.json")


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
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def image_record(path: Path, root: Path) -> dict[str, Any]:
    image = Image.open(path)
    return {
        "path": rel(path, root),
        "sha256": sha256_file(path),
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": image.format,
        "bytes": path.stat().st_size,
    }


def make_comparison(root: Path) -> str:
    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    overlay = Image.open(resolve(root, CANDIDATE_OVERLAY)).convert("RGB")
    output = Image.open(resolve(root, GENERATED_OUTPUT)).convert("RGB")
    mask_preview = Image.open(resolve(root, MASK_PREVIEW)).convert("RGB")
    crop = crop_box()

    tiles = [
        label_tile(source, "source full"),
        label_tile(output, "generated full"),
        label_tile(source.crop(crop), "source nose crop"),
        label_tile(overlay.crop(crop), "accepted v2 overlay"),
        label_tile(output.crop(crop), "generated nose crop"),
        label_tile(mask_preview, "runtime mask preview"),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_nose/qa_comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "wave70_mf70_nose_v2_source_landmark_source_overlay_output_compare.png"
    panel.save(panel_path)
    return rel(panel_path, root)


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


def update_ledgers(root: Path, visual_qa_rel: str, tracker_evidence_rel: str, comparison_rel: str) -> None:
    note = (
        " V2 generated-output proof executed locally with accepted v2 source-landmark mask; strict whole-image QA "
        "passes with notes. Nose remains natural, no mouth/lip/philtrum/eye/cheek drift or visible mask edge observed. "
        "Status remains candidate-local because target-runtime and reference-matrix proof are pending, and other disputed masks remain untrusted."
    )
    evidence_append = f"{visual_qa_rel}; {tracker_evidence_rel}"
    updates = {
        "Status": STATUS,
        "Status_Decision": STATUS_DECISION,
        "Coverage_Audit_Status": STATUS_DECISION,
        "Final_Render_Gate": "Blocked until target-runtime proof and reference-image matrix proof are complete.",
    }
    append_fields = {
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Acceptance_Evidence": evidence_append,
        "Output_Artifact": comparison_rel,
        "Notes": note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, updates, append_fields)


def update_mask_qa(root: Path, visual_qa_rel: str, tracker_evidence_rel: str, comparison_rel: str) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_nose.json"
    data = read_json(path)
    data["result"] = STATUS_DECISION
    data["source_landmark_repair_v2_generated_output_proof"] = {
        "visual_qa": visual_qa_rel,
        "tracker_evidence": tracker_evidence_rel,
        "timestamp": TIMESTAMP,
        "result": "pass_with_notes_local_wave70_nose_v2_generated_output",
        "status": STATUS_DECISION,
        "generated_output_safe_pass": True,
        "semantic_mask_alignment_candidate_pass": True,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "final_completion_allowed": False,
        "comparison_artifact": comparison_rel,
        "notes": [
            "Local generated-output proof used the accepted v2 source-landmark mask.",
            "Whole-image QA did not find nose shape mutation, mouth/lip/philtrum drift, eye/gaze drift, cheek deformation, visible edge, clothing drift, or background regression.",
            "This proof does not certify other disputed masks and does not replace target-runtime or reference-matrix proof.",
        ],
    }
    v2 = data.setdefault("source_landmark_repair_v2_candidate", {})
    v2["generated_output_executed"] = True
    v2["generated_output_safe_pass"] = True
    v2["generated_output_visual_qa"] = visual_qa_rel
    v2["status"] = STATUS_DECISION
    write_json(path, data)


def update_hydration(root: Path, visual_qa_rel: str, tracker_evidence_rel: str, comparison_rel: str) -> None:
    section = f"""## Wave70 mf70_nose V2 Local Generated-Output Proof - {TIMESTAMP}

Ran exactly one bounded local ComfyUI generated-output proof for the accepted `mf70_nose` v2 source-landmark mask. Runtime evidence is `{RUNTIME_EVIDENCE.as_posix()}`. Strict visual QA is `{visual_qa_rel}`, tracker evidence is `{tracker_evidence_rel}`, and comparison panel is `{comparison_rel}`.

Result: pass with notes for local candidate proof. The output preserves identity, gaze, eyes, nose shape, mouth/lips, philtrum, cheeks, clothing, lighting, and background without a visible nose-mask edge. This proof is local-only and candidate-scoped: target-runtime proof, reference-image matrix proof, and repair of the other disputed masks remain pending.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, visual_qa_rel)

    qa_index_row = (
        f"| W70-LOCAL-MF70-NOSE-V2-SOURCE-LANDMARK-SEED210820-VISUAL-QA-{RUN_STAMP} | "
        "Local generated-output proof for accepted mf70_nose v2 source-landmark mask passed strict whole-image QA with notes; "
        "target-runtime/reference-matrix proof and other disputed masks remain pending | image_artifact_qa | pass_with_notes_candidate_local_only | "
        f"{visual_qa_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, f"W70-LOCAL-MF70-NOSE-V2-SOURCE-LANDMARK-SEED210820-VISUAL-QA-{RUN_STAMP}")
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_nose v2 local generated-output proof",
            "Executed one bounded local ComfyUI sample using the accepted v2 source-landmark nose mask, created a source/overlay/output comparison panel, and recorded strict whole-image QA pass with notes while preserving target-runtime and matrix blockers.",
            f"{RUNTIME_EVIDENCE.as_posix()}; {visual_qa_rel}; {tracker_evidence_rel}; {comparison_rel}",
            "Invoke-LocalComfyUIRunPackageSmoke.ps1 -Execute; direct image inspection; comparison panel; JSON parse; tracker/item row update",
            "PASS_WITH_NOTES_LOCAL_CANDIDATE_GENERATED_OUTPUT_SAFE_FINAL_BLOCKED_TARGET_RUNTIME_MATRIX",
            visual_qa_rel,
            "Repair the next downgraded Wave70 mask with the same fail-closed source-overlay method or run target-runtime proof only when intentionally selected",
        ],
        f"W70_LOCAL_MF70_NOSE_V2_SOURCE_LANDMARK_SEED210820_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    for path in [SOURCE_IMAGE, CANDIDATE_OVERLAY, CANDIDATE_MASK, PROMPT_PROFILE, RUN_PACKAGE, RUNTIME_EVIDENCE, GENERATED_OUTPUT, MASK_PREVIEW, STRICT_VISUAL_ACCEPTANCE]:
        if not resolve(root, path).exists():
            raise FileNotFoundError(f"required QA input missing: {path.as_posix()}")

    runtime = read_json(resolve(root, RUNTIME_EVIDENCE))
    if runtime.get("result") != "pass_local_run_package_generation_smoke":
        raise RuntimeError(f"runtime evidence did not pass: {runtime.get('result')}")

    comparison_rel = make_comparison(root)
    comparison_path = resolve(root, Path(comparison_rel))
    visual_qa_path = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA" / f"W70_LOCAL_MF70_NOSE_V2_SOURCE_LANDMARK_SEED210820_VISUAL_QA_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_NOSE_V2_GENERATED_OUTPUT_{RUN_STAMP}.json"
    visual_qa_rel = rel(visual_qa_path, root)
    tracker_evidence_rel = rel(tracker_path, root)

    visual_qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-MF70-NOSE-V2-SOURCE-LANDMARK-SEED210820-VISUAL-QA-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "strict_whole_image_visual_qa_for_wave70_mf70_nose_v2_generated_output",
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
        "generation_executed": True,
        "source_image": image_record(resolve(root, SOURCE_IMAGE), root),
        "generated_output": image_record(resolve(root, GENERATED_OUTPUT), root),
        "diagnostic_mask_preview": image_record(resolve(root, MASK_PREVIEW), root),
        "candidate_mask": image_record(resolve(root, CANDIDATE_MASK), root),
        "candidate_overlay": image_record(resolve(root, CANDIDATE_OVERLAY), root),
        "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
        "prompt_profile_sha256": sha256_file(resolve(root, PROMPT_PROFILE)),
        "run_package": rel(resolve(root, RUN_PACKAGE), root),
        "run_package_sha256": sha256_file(resolve(root, RUN_PACKAGE)),
        "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
        "runtime_evidence_sha256": sha256_file(resolve(root, RUNTIME_EVIDENCE)),
        "strict_visual_acceptance": rel(resolve(root, STRICT_VISUAL_ACCEPTANCE), root),
        "strict_visual_acceptance_sha256": sha256_file(resolve(root, STRICT_VISUAL_ACCEPTANCE)),
        "comparison": comparison_rel,
        "comparison_sha256": sha256_file(comparison_path),
        "visual_findings": [
            "Generated portrait remains coherent at whole-image scale with no obvious global style drift.",
            "Nose bridge, sidewalls, tip, alae, and nostril base look natural; no obvious shape expansion, pinching, seam, or edge halo is visible.",
            "Mouth, lips, philtrum, cheeks, eyes, gaze, eyebrows, hair, blazer, lighting, and gray background remain stable.",
            "Diagnostic mask preview confirms the local run used the accepted small v2 nose mask, not the old broad disputed mask.",
            "This is a local candidate proof only; target-runtime proof, reference-image matrix proof, and other mask repairs remain pending.",
        ],
        "strict_whole_image_qa": {
            "identity_preserved": True,
            "nose_region_safe": True,
            "mouth_lips_philtrum_safe": True,
            "eyes_gaze_safe": True,
            "cheeks_skin_safe": True,
            "clothing_background_safe": True,
            "visible_mask_edge": False,
            "blocking_artifacts": [],
        },
        "semantic_mask_alignment_candidate_pass": True,
        "generated_output_safe_pass": True,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "final_completion_allowed": False,
        "result": "pass_with_notes_local_wave70_nose_v2_generated_output",
        "status_after_qa": STATUS,
        "status_decision_after_qa": STATUS_DECISION,
        "boundary": "Local v2 generated-output proof only. Does not certify Wave70, does not prove generalization, and does not rehabilitate other disputed masks.",
    }
    write_json(visual_qa_path, visual_qa)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_NOSE_V2_GENERATED_OUTPUT_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "status": STATUS,
            "status_decision": STATUS_DECISION,
            "actual_work_performed": [
                "Executed one bounded local ComfyUI generated-output proof for accepted mf70_nose v2 source-landmark mask.",
                "Pulled back generated portrait and diagnostic mask preview.",
                "Created source/overlay/output comparison panel.",
                "Completed strict whole-image visual QA and kept target-runtime/reference-matrix gates pending.",
            ],
            "evidence": {
                "visual_qa": visual_qa_rel,
                "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
                "comparison": comparison_rel,
                "generated_output": rel(resolve(root, GENERATED_OUTPUT), root),
                "diagnostic_mask_preview": rel(resolve(root, MASK_PREVIEW), root),
                "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
                "run_package": rel(resolve(root, RUN_PACKAGE), root),
            },
            "qa_decision": {
                "semantic_mask_alignment_candidate_pass": True,
                "generated_output_safe_pass": True,
                "target_runtime_proof_present": False,
                "reference_image_matrix_pass": False,
                "final_completion_allowed": False,
            },
            "boundaries": {
                "local_only": True,
                "ec2_started": False,
                "aws_contacted": False,
                "github_api_contacted": False,
                "civitai_contacted": False,
            },
            "result": visual_qa["result"],
            "next_action": "Repair the next downgraded Wave70 mask with the same fail-closed standard or run target-runtime proof only when intentionally selected.",
        },
    )
    update_mask_qa(root, visual_qa_rel, tracker_evidence_rel, comparison_rel)
    update_ledgers(root, visual_qa_rel, tracker_evidence_rel, comparison_rel)
    update_hydration(root, visual_qa_rel, tracker_evidence_rel, comparison_rel)
    print(json.dumps({"result": visual_qa["result"], "visual_qa": visual_qa_rel, "tracker_evidence": tracker_evidence_rel, "comparison": comparison_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
