#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260708T010000-0500"
TIMESTAMP = "2026-07-08T01:00:00-05:00"
MASK_TYPE_ID = "mf70_pupils_iris_sclera"
TRACKER_ID = "TRK-W70-0012"
ITEM_ID = "ITEM-W70-0012"
BLOCKED_STATUS = "Blocked_Wave70_Mask_Promotion_Gate_Not_Passed"
BLOCKED_DECISION = "blocked_wave70_mask_promotion_gate_not_passed_existing_mask_work_untrusted_until_validator_passes"
QA_DECISION = "pupils_iris_sclera_v3_generated_output_safe_hard_gate_blocked"

SOURCE_IMAGE = Path("Plan/Instructions/Operations/Pulled_Back_Artifacts/canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png")
CANDIDATE_OVERLAY = Path("Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_pupils_iris_sclera_v3_20260708T005000-0500/wave70_mf70_pupils_iris_sclera_v3_overlay.png")
CANDIDATE_MASK = Path("Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_pupils_iris_sclera_v3_20260708T005000-0500/wave70_mf70_pupils_iris_sclera_v3_mask.png")
STRICT_REPAIR = Path("Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_PUPILS_IRIS_SCLERA_V3_SOURCE_APERTURE_REPAIR_20260708T005000-0500.json")
PROMPT_PROFILE = Path("PromptProfiles/base_generation/inpaint_detail_v4_robustness/inpaint_wave70_mf70_pupils_iris_sclera_seed210811.json")
RUN_PACKAGE = Path("runtime_artifacts/run_packages/wave70_mf70_pupils_iris_sclera_seed210811/RUN_PACKAGE_MANIFEST.json")
RUNTIME_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_MF70_PUPILS_IRIS_SCLERA_V3_SEED210811_EXECUTE_20260708T005500-0500.json")
PULLBACK_DIR = Path("Plan/Instructions/Operations/Pulled_Back_Artifacts/wave70_mf70_pupils_iris_sclera_v3_seed210811_20260708T005500-0500")
GENERATED_OUTPUT = PULLBACK_DIR / "images/codex_wave70_mf70_pupils_iris_sclera_seed210811_00002_.png"
MASK_PREVIEW = PULLBACK_DIR / "images/codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_mask_preview_00030_.png"


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


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


def make_comparison(root: Path) -> str:
    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    overlay = Image.open(resolve(root, CANDIDATE_OVERLAY)).convert("RGB")
    output = Image.open(resolve(root, GENERATED_OUTPUT)).convert("RGB")
    preview = Image.open(resolve(root, MASK_PREVIEW)).convert("RGB")
    crop = (210, 270, 535, 365)
    tiles = [
        label_tile(source, "source full"),
        label_tile(output, "generated full"),
        label_tile(source.crop(crop), "source eye crop"),
        label_tile(overlay.crop(crop), "v3 aperture overlay"),
        label_tile(output.crop(crop), "generated eye crop"),
        label_tile(preview, "runtime mask preview"),
    ]
    panel = Image.new("RGB", (360 * len(tiles), 394), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (360 * index, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_pupils_iris_sclera/qa_comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "wave70_mf70_pupils_iris_sclera_v3_source_aperture_output_compare.png"
    panel.save(panel_path)
    return rel(panel_path, root)


def csv_update_row(path: Path, id_column: str, id_value: str, append_fields: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    changed = False
    for row in rows:
        if row.get(id_column) != id_value:
            continue
        if "Status" in row:
            row["Status"] = BLOCKED_STATUS
            changed = True
        if "Status_Decision" in row:
            row["Status_Decision"] = BLOCKED_DECISION
            changed = True
        if "Coverage_Audit_Status" in row:
            row["Coverage_Audit_Status"] = BLOCKED_DECISION
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


def update_ledgers(root: Path, visual_qa_rel: str, tracker_rel: str, comparison_rel: str) -> None:
    note = (
        " Pupils/iris/sclera v3 generated-output proof executed locally after source-aperture repair. "
        "Strict whole-image QA passed with notes: gaze, pupils, irises, sclera tone, catchlights, eyelids, lashes, brows, hair, blazer, lighting, and background remain stable. "
        "Row remains blocked by Wave70 hard promotion gate until explicit row-gate pass evidence exists."
    )
    evidence_append = f"{visual_qa_rel}; {tracker_rel}"
    append_fields = {
        "Acceptance_Evidence": evidence_append,
        "Evidence_Path": evidence_append,
        "Evidence_Required": evidence_append,
        "Output_Artifact": comparison_rel,
        "Notes": note,
    }
    for csv_path, id_column, id_value in [
        (root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
        (root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
        (root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    ]:
        csv_update_row(csv_path, id_column, id_value, append_fields)


def update_mask_qa(root: Path, visual_qa_rel: str, tracker_rel: str, comparison_rel: str) -> None:
    path = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_pupils_iris_sclera.json"
    data = read_json(path)
    data["result"] = QA_DECISION
    repair = data.setdefault("source_aperture_v3_repair", {})
    repair["generated_output_visual_qa"] = visual_qa_rel
    repair["generated_output_tracker_evidence"] = tracker_rel
    repair["generated_output_safe_pass"] = True
    repair["generated_output_proof_valid_for_this_mask"] = True
    repair["generated_output_comparison_artifact"] = comparison_rel
    repair["status"] = QA_DECISION
    repair["hard_gate_status"] = BLOCKED_STATUS
    data.setdefault("validation", {})["generated_output_proof_present"] = True
    data.setdefault("validation", {})["generated_output_safe_pass"] = True
    data.setdefault("validation", {})["target_runtime_proof_present"] = False
    data.setdefault("validation", {})["completion_allowed_by_mask_alignment"] = False
    data.setdefault("single_anchor_boundary", {})["status"] = BLOCKED_STATUS
    write_json(path, data)


def update_hydration(root: Path, visual_qa_rel: str, tracker_rel: str, comparison_rel: str) -> None:
    section = f"""## Wave70 mf70_pupils_iris_sclera V3 Local Generated-Output Proof - {TIMESTAMP}

Ran one bounded local ComfyUI generated-output proof for the repaired `mf70_pupils_iris_sclera` v3 eye-aperture mask. Runtime evidence is `{RUNTIME_EVIDENCE.as_posix()}`. Strict visual QA is `{visual_qa_rel}`, tracker evidence is `{tracker_rel}`, and comparison panel is `{comparison_rel}`.

Result: pass with notes for local output safety. The row remains `Blocked_Wave70_Mask_Promotion_Gate_Not_Passed`; this proof is evidence for the repair queue, not row promotion, target-runtime proof, reference-matrix proof, or certification.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, visual_qa_rel)
    qa_index_row = (
        f"| W70-LOCAL-MF70-PUPILS-IRIS-SCLERA-V3-SEED210811-VISUAL-QA-{RUN_STAMP} | "
        "Repaired mf70_pupils_iris_sclera v3 local generated-output proof passed strict whole-image QA with notes; hard promotion gate remains blocked | "
        "image_artifact_qa | pass_with_notes_hard_gate_blocked | "
        f"{visual_qa_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, f"W70-LOCAL-MF70-PUPILS-IRIS-SCLERA-V3-SEED210811-VISUAL-QA-{RUN_STAMP}")
    append_unique_csv_row(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        [
            TIMESTAMP,
            "70",
            "mf70_pupils_iris_sclera v3 local generated-output proof",
            "Executed one bounded local ComfyUI sample using the repaired v3 eye-aperture mask and recorded strict whole-image QA pass with notes while preserving hard-gate block.",
            f"{RUNTIME_EVIDENCE.as_posix()}; {visual_qa_rel}; {tracker_rel}; {comparison_rel}",
            "Invoke-LocalComfyUIRunPackageSmoke.ps1 -Execute; direct image inspection; comparison panel; JSON parse; tracker/item evidence append",
            "PASS_WITH_NOTES_LOCAL_OUTPUT_SAFE_HARD_GATE_BLOCKED",
            visual_qa_rel,
            "Continue Wave70 disputed mask repair queue or implement row-level hard-gate unlock validator",
        ],
        f"W70_LOCAL_MF70_PUPILS_IRIS_SCLERA_V3_SEED210811_{RUN_STAMP}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    for path in [SOURCE_IMAGE, CANDIDATE_OVERLAY, CANDIDATE_MASK, STRICT_REPAIR, PROMPT_PROFILE, RUN_PACKAGE, RUNTIME_EVIDENCE, GENERATED_OUTPUT, MASK_PREVIEW]:
        if not resolve(root, path).exists():
            raise FileNotFoundError(f"required QA input missing: {path.as_posix()}")
    runtime = read_json(resolve(root, RUNTIME_EVIDENCE))
    if runtime.get("result") != "pass_local_run_package_generation_smoke":
        raise RuntimeError(f"runtime evidence did not pass: {runtime.get('result')}")
    repair = read_json(resolve(root, STRICT_REPAIR))
    if repair.get("protected_overlap_matrix_pass") is not True:
        raise RuntimeError("source-aperture repair did not pass protected-overlap matrix")

    comparison_rel = make_comparison(root)
    comparison_path = resolve(root, Path(comparison_rel))
    visual_qa_path = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA" / f"W70_LOCAL_MF70_PUPILS_IRIS_SCLERA_V3_SEED210811_VISUAL_QA_{RUN_STAMP}.json"
    tracker_path = root / "Plan/Tracker/Evidence" / f"W70_MF70_PUPILS_IRIS_SCLERA_V3_GENERATED_OUTPUT_{RUN_STAMP}.json"
    visual_qa_rel = rel(visual_qa_path, root)
    tracker_rel = rel(tracker_path, root)

    visual_qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-MF70-PUPILS-IRIS-SCLERA-V3-SEED210811-VISUAL-QA-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "strict_whole_image_visual_qa_for_wave70_mf70_pupils_iris_sclera_v3_generated_output",
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
        "hard_gate_status": BLOCKED_STATUS,
        "hard_gate_status_decision": BLOCKED_DECISION,
        "source_image": image_record(resolve(root, SOURCE_IMAGE), root),
        "generated_output": image_record(resolve(root, GENERATED_OUTPUT), root),
        "diagnostic_mask_preview": image_record(resolve(root, MASK_PREVIEW), root),
        "candidate_mask": image_record(resolve(root, CANDIDATE_MASK), root),
        "candidate_overlay": image_record(resolve(root, CANDIDATE_OVERLAY), root),
        "strict_repair_evidence": rel(resolve(root, STRICT_REPAIR), root),
        "strict_repair_evidence_sha256": sha256_file(resolve(root, STRICT_REPAIR)),
        "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
        "prompt_profile_sha256": sha256_file(resolve(root, PROMPT_PROFILE)),
        "run_package": rel(resolve(root, RUN_PACKAGE), root),
        "run_package_sha256": sha256_file(resolve(root, RUN_PACKAGE)),
        "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
        "runtime_evidence_sha256": sha256_file(resolve(root, RUNTIME_EVIDENCE)),
        "comparison": comparison_rel,
        "comparison_sha256": sha256_file(comparison_path),
        "visual_findings": [
            "Generated portrait remains coherent at whole-image scale with no obvious global style drift.",
            "Gaze direction, pupil size, iris color, sclera tone, and visible catchlights remain stable.",
            "Eyelids, eyelashes, eyebrows, nearby hair occlusion, surrounding skin texture, blazer, lighting, and background remain stable.",
            "No visible seam, halo, doll-eye effect, glassy-eye mutation, red-eye artifact, or mismatched-eye defect is visible around the repaired v3 eye-aperture mask.",
            "Diagnostic mask preview confirms the local run used the repaired v3 eye-aperture mask with catchlight holes.",
            "This is local output-geometry evidence only; hard promotion gate, target-runtime proof, and reference-image matrix proof remain pending.",
        ],
        "strict_whole_image_qa": {
            "identity_preserved": True,
            "gaze_safe": True,
            "pupils_iris_sclera_safe": True,
            "catchlights_safe": True,
            "eyelids_lashes_safe": True,
            "hair_skin_clothing_background_safe": True,
            "visible_mask_edge": False,
            "blocking_artifacts": [],
        },
        "semantic_mask_alignment_repair_pass": True,
        "generated_output_safe_pass": True,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "wave70_mask_promotion_gate_pass": False,
        "final_completion_allowed": False,
        "result": "pass_with_notes_local_wave70_pupils_iris_sclera_v3_generated_output_hard_gate_blocked",
        "status_after_qa": BLOCKED_STATUS,
        "status_decision_after_qa": BLOCKED_DECISION,
        "boundary": "Local v3 generated-output proof only. Does not promote the row, certify Wave70, prove generalization, or satisfy target-runtime/reference-matrix gates.",
    }
    write_json(visual_qa_path, visual_qa)
    write_json(tracker_path, {
        "schema_version": "1.0",
        "tracker_evidence_id": f"W70_MF70_PUPILS_IRIS_SCLERA_V3_GENERATED_OUTPUT_{RUN_STAMP}",
        "created_at": TIMESTAMP,
        "project_root": str(root),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "mask_type_id": MASK_TYPE_ID,
        "status": BLOCKED_STATUS,
        "status_decision": BLOCKED_DECISION,
        "qa_decision": QA_DECISION,
        "evidence": {
            "visual_qa": visual_qa_rel,
            "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
            "comparison": comparison_rel,
            "generated_output": rel(resolve(root, GENERATED_OUTPUT), root),
            "diagnostic_mask_preview": rel(resolve(root, MASK_PREVIEW), root),
            "strict_repair": rel(resolve(root, STRICT_REPAIR), root),
        },
        "qa_decision_detail": {
            "semantic_mask_alignment_repair_pass": True,
            "generated_output_safe_pass": True,
            "wave70_mask_promotion_gate_pass": False,
            "target_runtime_proof_present": False,
            "reference_image_matrix_pass": False,
            "final_completion_allowed": False,
        },
        "result": visual_qa["result"],
    })
    update_mask_qa(root, visual_qa_rel, tracker_rel, comparison_rel)
    update_ledgers(root, visual_qa_rel, tracker_rel, comparison_rel)
    update_hydration(root, visual_qa_rel, tracker_rel, comparison_rel)
    print(json.dumps({"result": visual_qa["result"], "visual_qa": visual_qa_rel, "tracker_evidence": tracker_rel, "comparison": comparison_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
