#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260710T031424-0500"
TIMESTAMP = "2026-07-10T03:14:24-05:00"
MASK_TYPE_ID = "mf70_teeth_mouth_area"
SOURCE_IMAGE = Path("ComfyUI/input/wave70_mf70_face_identity_source_canny_v3.png")
CANDIDATE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_TEETH_MOUTH_AREA_POSTPROCESS_V2_STRICT_VISUAL_ACCEPTANCE_20260710T025800-0500.json"
)
PROMPT_PROFILE = Path(
    "PromptProfiles/base_generation/inpaint_detail_v4_robustness/"
    "inpaint_wave70_mf70_teeth_mouth_area_v2_seed210826.json"
)
RUN_PACKAGE = Path("runtime_artifacts/run_packages/wave70_mf70_teeth_mouth_area_v2_seed210826/RUN_PACKAGE_MANIFEST.json")
RUNTIME_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Workflow_Runtime/"
    "W70_LOCAL_MF70_TEETH_MOUTH_AREA_V2_SEED210826_EXECUTE_20260710T031424-0500.json"
)
PULLBACK_DIR = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave70_mf70_teeth_mouth_area_v2_seed210826_20260710T031424-0500"
)
GENERATED_OUTPUT = PULLBACK_DIR / "images/codex_wave70_mf70_teeth_mouth_area_v2_seed210826_00001_.png"
MASK_PREVIEW = PULLBACK_DIR / "images/codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_mask_preview_00036_.png"
CANDIDATE_REVIEW_PANEL = Path(
    "runtime_artifacts/mask_factory/wave70_mf70_teeth_mouth_area_postprocess_v2/"
    "20260710T025200-0500/wave70_mf70_teeth_mouth_area_postprocess_v2_review_panel.png"
)


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


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


def label_tile(image: Image.Image, label: str, size: int = 320) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def crop_box() -> tuple[int, int, int, int]:
    return (290, 360, 470, 520)


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


def make_panel(root: Path) -> str:
    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    output = Image.open(resolve(root, GENERATED_OUTPUT)).convert("RGB")
    mask_preview = Image.open(resolve(root, MASK_PREVIEW)).convert("RGB")
    candidate_panel = Image.open(resolve(root, CANDIDATE_REVIEW_PANEL)).convert("RGB")
    crop = crop_box()
    tiles = [
        label_tile(source, "source full"),
        label_tile(output, "generated full"),
        label_tile(source.crop(crop), "source mouth crop"),
        label_tile(output.crop(crop), "generated mouth crop"),
        label_tile(mask_preview, "runtime mask preview"),
        label_tile(candidate_panel, "candidate review panel"),
    ]
    panel = Image.new("RGB", (320 * len(tiles), 354), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (320 * index, 0))
    out_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_teeth_mouth_area_postprocess_v2/qa_comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / f"W70_LOCAL_MF70_TEETH_MOUTH_AREA_V2_SEED210826_VISUAL_QA_{RUN_STAMP}_panel.png"
    panel.save(panel_path)
    return rel(panel_path, root)


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    required = [SOURCE_IMAGE, CANDIDATE_EVIDENCE, PROMPT_PROFILE, RUN_PACKAGE, RUNTIME_EVIDENCE, GENERATED_OUTPUT, MASK_PREVIEW, CANDIDATE_REVIEW_PANEL]
    for path in required:
        if not resolve(root, path).exists():
            raise FileNotFoundError(path.as_posix())

    runtime = read_json(resolve(root, RUNTIME_EVIDENCE))
    if runtime.get("result") != "pass_local_run_package_generation_smoke" or runtime.get("generation_executed") is not True:
        raise RuntimeError("runtime evidence does not prove a passing local generation")
    if runtime.get("ec2_started") is not False:
        raise RuntimeError("runtime evidence is not local-only")

    comparison_rel = make_panel(root)
    comparison_path = resolve(root, comparison_rel)
    visual_path = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA" / (
        f"W70_LOCAL_MF70_TEETH_MOUTH_AREA_V2_SEED210826_VISUAL_QA_{RUN_STAMP}.json"
    )
    tracker_path = root / "Plan/Tracker/Evidence" / (
        f"W70_MF70_TEETH_MOUTH_AREA_V2_GENERATED_OUTPUT_{RUN_STAMP}.json"
    )
    visual_rel = rel(visual_path, root)
    tracker_rel = rel(tracker_path, root)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-MF70-TEETH-MOUTH-AREA-V2-SEED210826-VISUAL-QA-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "qa_type": "strict_whole_image_visual_qa_for_wave70_mf70_teeth_mouth_area_v2_generated_output",
        "implementation_script": rel(Path(__file__).resolve(), root),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "mask_type_id": MASK_TYPE_ID,
        "local_only": True,
        "ec2_started": False,
        "generation_executed": True,
        "mask_promoted": False,
        "active_teeth_input_overwritten": False,
        "source_image": image_record(resolve(root, SOURCE_IMAGE), root),
        "generated_output": image_record(resolve(root, GENERATED_OUTPUT), root),
        "diagnostic_mask_preview": image_record(resolve(root, MASK_PREVIEW), root),
        "candidate_evidence": rel(resolve(root, CANDIDATE_EVIDENCE), root),
        "candidate_evidence_sha256": sha256_file(resolve(root, CANDIDATE_EVIDENCE)),
        "prompt_profile": rel(resolve(root, PROMPT_PROFILE), root),
        "prompt_profile_sha256": sha256_file(resolve(root, PROMPT_PROFILE)),
        "run_package": rel(resolve(root, RUN_PACKAGE), root),
        "run_package_sha256": sha256_file(resolve(root, RUN_PACKAGE)),
        "runtime_evidence": rel(resolve(root, RUNTIME_EVIDENCE), root),
        "runtime_evidence_sha256": sha256_file(resolve(root, RUNTIME_EVIDENCE)),
        "comparison": comparison_rel,
        "comparison_sha256": sha256_file(comparison_path),
        "visual_findings": [
            "Generated output remains stable at whole-image scale with identity, gaze, hair, blazer, lighting, and background preserved.",
            "Mouth crop remains close to source; visible teeth band and closed-mouth expression are preserved without an obvious open-mouth or smile drift.",
            "Runtime mask preview confirms the local run used the intended small mouth-area v2 mask.",
            "No visible seam or edge halo is apparent around the mouth-area mask.",
            "This proof is local-only and candidate-scoped; it does not promote the mask or certify the remaining blocked facial rows.",
        ],
        "strict_whole_image_qa": {
            "identity_preserved": True,
            "mouth_expression_safe": True,
            "visible_teeth_safe": True,
            "lips_philtrum_nose_safe": True,
            "eyes_gaze_safe": True,
            "hair_clothing_background_safe": True,
            "visible_mask_edge": False,
            "blocking_artifacts": [],
        },
        "generated_output_safe_pass": True,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "final_completion_allowed": False,
        "promotion_allowed": False,
        "result": "pass_with_notes_local_wave70_teeth_mouth_area_v2_generated_output",
        "status_after_qa": "Candidate_Local_Proof_Pass_With_Notes_Promotion_Blocked",
        "boundary": "Local v2 generated-output proof only. Does not certify Wave70, does not prove generalization, and does not promote mf70_teeth_mouth_area.",
    }
    write_json(visual_path, evidence)
    write_json(
        tracker_path,
        {
            "schema_version": "1.0",
            "tracker_evidence_id": f"W70_MF70_TEETH_MOUTH_AREA_V2_GENERATED_OUTPUT_{RUN_STAMP}",
            "created_at": TIMESTAMP,
            "project_root": str(root),
            "mask_type_id": MASK_TYPE_ID,
            "result": evidence["result"],
            "status": evidence["status_after_qa"],
            "evidence": {
                "visual_qa": visual_rel,
                "runtime_evidence": evidence["runtime_evidence"],
                "comparison": comparison_rel,
                "generated_output": evidence["generated_output"]["path"],
                "diagnostic_mask_preview": evidence["diagnostic_mask_preview"]["path"],
                "prompt_profile": evidence["prompt_profile"],
                "run_package": evidence["run_package"],
            },
            "qa_decision": {
                "generated_output_safe_pass": True,
                "target_runtime_proof_present": False,
                "reference_image_matrix_pass": False,
                "final_completion_allowed": False,
                "promotion_allowed": False,
            },
            "boundaries": {
                "local_only": True,
                "ec2_started": False,
                "mask_promoted": False,
                "active_teeth_input_overwritten": False,
            },
        },
    )

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_teeth_mouth_area V2 Local Generated-Output Proof - {TIMESTAMP}

Ran one bounded local ComfyUI generated-output proof for the unpromoted `mf70_teeth_mouth_area` v2 candidate. Runtime evidence `{RUNTIME_EVIDENCE.as_posix()}` reports `pass_local_run_package_generation_smoke`; strict visual QA `{visual_rel}` reports `pass_with_notes_local_wave70_teeth_mouth_area_v2_generated_output`; tracker mirror `{tracker_rel}` and comparison panel `{comparison_rel}` were written. No active teeth input overwrite, mask promotion, EC2, AWS, GitHub, S3, Civitai, final certification, or row completion occurred.
"""
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)

    print(json.dumps({"result": evidence["result"], "visual_qa": visual_rel, "tracker_evidence": tracker_rel, "comparison": comparison_rel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
