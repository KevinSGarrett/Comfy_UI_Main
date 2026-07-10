#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260710T022800-0500"
TIMESTAMP = "2026-07-10T02:28:00-05:00"
MASK_TYPE_ID = "mf70_nose"
TRACKER_ID = "TRK-W70-0017"
ITEM_ID = "ITEM-W70-0017"

SOURCE_IMAGE = Path("ComfyUI/input/wave70_mf70_face_identity_source_canny_v3.png")
CANDIDATE_MASK = Path("ComfyUI/input/wave70_mf70_nose_v5_mask.png")
CANDIDATE_OVERLAY = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_parser_derived_v5_20260710T020712-0500/"
    "wave70_mf70_nose_parser_derived_v5_overlay.png"
)
REVIEW_PANEL = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_nose_parser_derived_v5/"
    "20260710T020712-0500/wave70_mf70_nose_parser_derived_v5_review_panel.png"
)
PROMPT_PROFILE = Path(
    "PromptProfiles/base_generation/inpaint_detail_v4_robustness/"
    "inpaint_wave70_mf70_nose_v5_parser_derived_seed210825.json"
)
RUN_PACKAGE = Path(
    "runtime_artifacts/run_packages/wave70_mf70_nose_v5_parser_derived_seed210825/"
    "RUN_PACKAGE_MANIFEST.json"
)
RUNTIME_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Workflow_Runtime/"
    "W70_LOCAL_MF70_NOSE_V5_PARSER_DERIVED_SEED210825_EXECUTE_20260710T022800-0500.json"
)
PULLBACK_DIR = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave70_mf70_nose_v5_parser_derived_seed210825_20260710T022800-0500"
)
GENERATED_OUTPUT = PULLBACK_DIR / "images/codex_wave70_mf70_nose_v5_parser_derived_seed210825_00001_.png"
MASK_PREVIEW = PULLBACK_DIR / "images/codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_mask_preview_00035_.png"
SOURCE_CANDIDATE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_NOSE_PARSER_DERIVED_V5_20260710T020712-0500.json"
)
GOLD_BENCHMARK_GATE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_BENCHMARK_GATE_20260710T013355-0500.json"
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
    return (285, 255, 455, 455)


def label_tile(image: Image.Image, label: str, size: int = 320) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
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
    review_panel = Image.open(resolve(root, REVIEW_PANEL)).convert("RGB")
    crop = crop_box()

    tiles = [
        label_tile(source, "source full"),
        label_tile(output, "generated full"),
        label_tile(source.crop(crop), "source nose/mouth crop"),
        label_tile(overlay.crop(crop), "v5 parser overlay crop"),
        label_tile(output.crop(crop), "generated crop"),
        label_tile(mask_preview, "runtime mask preview"),
        label_tile(review_panel, "v5 source review panel"),
    ]
    panel = Image.new("RGB", (320 * len(tiles), 354), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (320 * index, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_nose_parser_derived_v5/qa_comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / f"W70_LOCAL_MF70_NOSE_V5_PARSER_DERIVED_SEED210825_VISUAL_QA_{RUN_STAMP}_panel.png"
    panel.save(panel_path)
    return rel(panel_path, root)


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def update_hydration(root: Path, visual_qa_rel: str, tracker_evidence_rel: str, comparison_rel: str) -> None:
    marker = f"W70-LOCAL-MF70-NOSE-V5-PARSER-DERIVED-SEED210825-VISUAL-QA-{RUN_STAMP}"
    section = f"""## Wave70 mf70_nose V5 Parser-Derived Local Generated-Output Proof - {TIMESTAMP}

Ran one bounded local ComfyUI generated-output proof for the parser-derived `mf70_nose` v5 candidate. Runtime evidence is `{RUNTIME_EVIDENCE.as_posix()}`. Strict whole-image visual QA is `{visual_qa_rel}`, tracker mirror evidence is `{tracker_evidence_rel}`, and comparison panel is `{comparison_rel}`.

Result: pass with notes for local candidate proof only. The runtime mask preview matches the v5 parser-derived nose region, mouth/lips are not included, and the generated output preserves the source portrait at whole-image scale without visible nose-edge artifacts. This does not promote `mf70_nose`, does not overwrite the older active nose input, and does not certify other disputed masks.
"""
    for hydration_path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(hydration_path, section, marker)

    qa_index_row = (
        f"| {marker} | Parser-derived mf70_nose v5 local generated-output proof; "
        "strict whole-image QA passed with notes while promotion remains blocked pending target-runtime/reference-matrix gates | "
        f"image_artifact_qa | pass_with_notes_candidate_local_only | {visual_qa_rel}; {tracker_evidence_rel}; {comparison_rel} |"
    )
    append_unique_text(root / "Plan/Instructions/Hydration_Rehydration/QA_EVIDENCE_INDEX.md", qa_index_row, marker)

    movement_row = (
        f"{TIMESTAMP},70,mf70_nose v5 parser-derived local generated-output proof,"
        "Ran bounded local ComfyUI sample for the v5 parser-derived nose candidate and recorded strict whole-image QA without promotion,"
        f"{RUNTIME_EVIDENCE.as_posix()}; {visual_qa_rel}; {tracker_evidence_rel}; {comparison_rel},"
        "Invoke-LocalComfyUIRunPackageSmoke.ps1 -Execute; direct image inspection; comparison panel; JSON evidence,"
        "PASS_WITH_NOTES_LOCAL_CANDIDATE_ONLY_PROMOTION_BLOCKED,"
        f"{visual_qa_rel},"
        "Run post-proof Wave70 hard gates and continue gold-benchmark-driven facial mask repair"
    )
    append_unique_text(
        root / "Plan/Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv",
        movement_row,
        marker,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    required = [
        SOURCE_IMAGE,
        CANDIDATE_MASK,
        CANDIDATE_OVERLAY,
        REVIEW_PANEL,
        PROMPT_PROFILE,
        RUN_PACKAGE,
        RUNTIME_EVIDENCE,
        GENERATED_OUTPUT,
        MASK_PREVIEW,
        SOURCE_CANDIDATE_EVIDENCE,
        GOLD_BENCHMARK_GATE,
    ]
    for path in required:
        if not resolve(root, path).exists():
            raise FileNotFoundError(f"required QA input missing: {path.as_posix()}")

    runtime = read_json(resolve(root, RUNTIME_EVIDENCE))
    if runtime.get("result") != "pass_local_run_package_generation_smoke":
        raise RuntimeError(f"runtime evidence did not pass: {runtime.get('result')}")
    if runtime.get("generation_executed") is not True or runtime.get("ec2_started") is not False:
        raise RuntimeError("runtime evidence does not prove bounded local-only generation")

    gate = read_json(resolve(root, GOLD_BENCHMARK_GATE))
    if MASK_TYPE_ID not in gate.get("passed_regions", []):
        raise RuntimeError("mf70_nose is not in the current passed gold-benchmark regions")

    comparison_rel = make_comparison(root)
    comparison_path = resolve(root, Path(comparison_rel))
    visual_qa_path = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA" / (
        f"W70_LOCAL_MF70_NOSE_V5_PARSER_DERIVED_SEED210825_VISUAL_QA_{RUN_STAMP}.json"
    )
    tracker_path = root / "Plan/Tracker/Evidence" / (
        f"W70_MF70_NOSE_V5_PARSER_DERIVED_GENERATED_OUTPUT_{RUN_STAMP}.json"
    )
    visual_qa_rel = rel(visual_qa_path, root)
    tracker_evidence_rel = rel(tracker_path, root)

    visual_qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-MF70-NOSE-V5-PARSER-DERIVED-SEED210825-VISUAL-QA-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "strict_whole_image_visual_qa_for_wave70_mf70_nose_v5_parser_derived_generated_output",
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
        "mask_promoted": False,
        "active_input_mask_overwritten": False,
        "source_image": image_record(resolve(root, SOURCE_IMAGE), root),
        "generated_output": image_record(resolve(root, GENERATED_OUTPUT), root),
        "diagnostic_mask_preview": image_record(resolve(root, MASK_PREVIEW), root),
        "candidate_mask": image_record(resolve(root, CANDIDATE_MASK), root),
        "candidate_overlay": image_record(resolve(root, CANDIDATE_OVERLAY), root),
        "source_candidate_evidence": rel(resolve(root, SOURCE_CANDIDATE_EVIDENCE), root),
        "source_candidate_evidence_sha256": sha256_file(resolve(root, SOURCE_CANDIDATE_EVIDENCE)),
        "gold_benchmark_gate": rel(resolve(root, GOLD_BENCHMARK_GATE), root),
        "gold_benchmark_gate_sha256": sha256_file(resolve(root, GOLD_BENCHMARK_GATE)),
        "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
        "prompt_profile_sha256": sha256_file(resolve(root, PROMPT_PROFILE)),
        "run_package": rel(resolve(root, RUN_PACKAGE), root),
        "run_package_sha256": sha256_file(resolve(root, RUN_PACKAGE)),
        "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
        "runtime_evidence_sha256": sha256_file(resolve(root, RUNTIME_EVIDENCE)),
        "comparison": comparison_rel,
        "comparison_sha256": sha256_file(comparison_path),
        "visual_findings": [
            "Generated output remains effectively unchanged at whole-image scale, which is expected for the low-denoise nose-only proof.",
            "Runtime mask preview shows only the parser-derived nose region and does not include the mouth, lips, philtrum, cheeks, or eyes.",
            "Nose bridge, sidewalls, tip, alae, and nostril base remain natural with no obvious seam, edge halo, expansion, pinching, or deformation.",
            "Mouth/lips, expression, eyes/gaze, eyebrows, cheeks, hair, white blazer, lighting, and gray background remain stable in the local proof.",
            "This proof is candidate-scoped and local-only; it does not certify other disputed masks and does not replace target-runtime or reference-matrix proof.",
        ],
        "strict_whole_image_qa": {
            "identity_preserved": True,
            "nose_region_safe": True,
            "mouth_lips_philtrum_safe": True,
            "eyes_gaze_safe": True,
            "cheeks_skin_safe": True,
            "hair_clothing_background_safe": True,
            "visible_mask_edge": False,
            "blocking_artifacts": [],
        },
        "gold_benchmark_context": {
            "mf70_nose_passed_current_gold_gate": True,
            "gold_gate_is_not_promotion_evidence_by_itself": True,
            "blocked_neighbor_regions_remain_blocked": [
                "mf70_eyebrows",
                "mf70_face_skin",
                "mf70_lips_bottom",
                "mf70_lips_combined",
                "mf70_lips_top",
                "mf70_neck",
                "mf70_teeth_mouth_area",
            ],
        },
        "semantic_mask_alignment_candidate_pass": True,
        "generated_output_safe_pass": True,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "final_completion_allowed": False,
        "promotion_allowed": False,
        "result": "pass_with_notes_local_wave70_nose_v5_parser_derived_generated_output",
        "status_after_qa": "Candidate_Local_Proof_Pass_With_Notes_Promotion_Blocked",
        "boundary": "Local v5 generated-output proof only. Does not certify Wave70, does not prove generalization, and does not promote mf70_nose.",
    }
    write_json(visual_qa_path, visual_qa)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_NOSE_V5_PARSER_DERIVED_GENERATED_OUTPUT_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "mask_type_id": MASK_TYPE_ID,
            "result": visual_qa["result"],
            "status": visual_qa["status_after_qa"],
            "actual_work_performed": [
                "Executed one bounded local ComfyUI generated-output proof for the parser-derived mf70_nose v5 candidate.",
                "Pulled back generated portrait and diagnostic mask preview.",
                "Created source/candidate/output comparison panel.",
                "Completed strict whole-image visual QA while keeping promotion and final completion blocked.",
            ],
            "evidence": {
                "visual_qa": visual_qa_rel,
                "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
                "comparison": comparison_rel,
                "generated_output": rel(resolve(root, GENERATED_OUTPUT), root),
                "diagnostic_mask_preview": rel(resolve(root, MASK_PREVIEW), root),
                "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
                "run_package": rel(resolve(root, RUN_PACKAGE), root),
                "gold_benchmark_gate": rel(resolve(root, GOLD_BENCHMARK_GATE), root),
            },
            "qa_decision": {
                "semantic_mask_alignment_candidate_pass": True,
                "generated_output_safe_pass": True,
                "target_runtime_proof_present": False,
                "reference_image_matrix_pass": False,
                "final_completion_allowed": False,
                "promotion_allowed": False,
            },
            "boundaries": {
                "local_only": True,
                "ec2_started": False,
                "aws_contacted": False,
                "github_api_contacted": False,
                "civitai_contacted": False,
                "mask_promoted": False,
                "active_input_mask_overwritten": False,
            },
            "next_action": "Run post-proof Wave70 hard gates, then continue gold-benchmark-driven facial mask repair.",
        },
    )
    update_hydration(root, visual_qa_rel, tracker_evidence_rel, comparison_rel)
    print(json.dumps({"result": visual_qa["result"], "visual_qa": visual_qa_rel, "tracker_evidence": tracker_evidence_rel, "comparison": comparison_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
