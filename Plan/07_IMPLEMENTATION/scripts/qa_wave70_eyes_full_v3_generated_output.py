from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageStat


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260709T235700-0500"
EVIDENCE_ID = f"W70_LOCAL_MF70_EYES_FULL_V3_SEED210822_VISUAL_QA_{RUN_STAMP}"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
MASK_IMAGE = PROJECT_ROOT / "ComfyUI/input/wave70_mf70_eyes_full_v3_mask.png"
GENERATED_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave70_mf70_eyes_full_v3_seed210822_20260709T235700-0500/"
    "images/codex_wave70_mf70_eyes_full_v3_seed210822_00001_.png"
)
PREVIEW_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave70_mf70_eyes_full_v3_seed210822_20260709T235700-0500/"
    "images/codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_mask_preview_00032_.png"
)
RUNTIME_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Workflow_Runtime/"
    "W70_LOCAL_MF70_EYES_FULL_V3_SEED210822_EXECUTE_20260709T235700-0500.json"
)
MASK_CANDIDATE_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V3_20260709T232402-0500.json"
)
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Image_Artifact_QA"
TRACKER_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence/Image_Artifact_QA"
PANEL_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_eyes_full_v3/qa_comparisons"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    x, y = xy
    draw.rectangle([x, y, x + 345, y + 34], fill=(0, 0, 0))
    draw.text((x + 8, y + 8), text, fill=(255, 255, 255))


def crop_eye_band(image: Image.Image) -> Image.Image:
    return image.crop((245, 270, 500, 375)).resize((510, 210), Image.Resampling.LANCZOS)


def build_panel(source: Image.Image, generated: Image.Image, mask: Image.Image, diff: Image.Image) -> Path:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    panel = Image.new("RGB", (1530, 760), (18, 18, 18))
    draw = ImageDraw.Draw(panel)

    source_full = source.resize((360, 360), Image.Resampling.LANCZOS)
    generated_full = generated.resize((360, 360), Image.Resampling.LANCZOS)
    mask_rgb = mask.convert("RGB").resize((360, 360), Image.Resampling.NEAREST)
    diff_rgb = diff.resize((360, 360), Image.Resampling.LANCZOS)

    panel.paste(source_full, (20, 60))
    panel.paste(generated_full, (400, 60))
    panel.paste(mask_rgb, (780, 60))
    panel.paste(diff_rgb, (1160, 60))
    label(draw, (20, 20), "source")
    label(draw, (400, 20), "generated v3 seed210822")
    label(draw, (780, 20), "v3 mask preview")
    label(draw, (1160, 20), "difference amplified")

    panel.paste(crop_eye_band(source), (20, 500))
    panel.paste(crop_eye_band(generated), (540, 500))
    label(draw, (20, 460), "source eye crop")
    label(draw, (540, 460), "generated eye crop")
    draw.text(
        (1060, 500),
        "QA decision: fail/iteration required\n"
        "Reason: output proves local routing, but the eye pass\n"
        "softens and slightly changes gaze/eye character.\n"
        "Next improvement: lower denoise and rerun minimum sample.",
        fill=(255, 220, 150),
    )

    panel_path = PANEL_DIR / f"{EVIDENCE_ID}_panel.png"
    panel.save(panel_path)
    return panel_path


def main() -> int:
    required = [SOURCE_IMAGE, MASK_IMAGE, GENERATED_IMAGE, PREVIEW_IMAGE, RUNTIME_EVIDENCE, MASK_CANDIDATE_EVIDENCE]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required QA inputs: {missing}")

    source = Image.open(SOURCE_IMAGE).convert("RGB")
    generated = Image.open(GENERATED_IMAGE).convert("RGB")
    mask = Image.open(MASK_IMAGE).convert("L")
    diff = ImageChops.difference(source, generated)
    amplified = diff.point(lambda value: min(255, value * 5))
    stat = ImageStat.Stat(diff)
    rms = sum(value * value for value in stat.rms) ** 0.5
    bbox = diff.getbbox()
    panel_path = build_panel(source, generated, mask, amplified)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "result": "fail_local_wave70_eyes_full_v3_generated_output_visual_qa_iteration_required",
        "local_only": True,
        "aws_contacted": False,
        "ec2_started": False,
        "generation_executed": True,
        "mask_promoted": False,
        "active_input_mask_overwritten": False,
        "source_image": rel(SOURCE_IMAGE),
        "generated_image": rel(GENERATED_IMAGE),
        "mask_image": rel(MASK_IMAGE),
        "preview_image": rel(PREVIEW_IMAGE),
        "runtime_evidence": rel(RUNTIME_EVIDENCE),
        "mask_candidate_evidence": rel(MASK_CANDIDATE_EVIDENCE),
        "comparison_panel": rel(panel_path),
        "sha256": {
            "source": sha256(SOURCE_IMAGE),
            "generated": sha256(GENERATED_IMAGE),
            "mask": sha256(MASK_IMAGE),
            "preview": sha256(PREVIEW_IMAGE),
            "panel": sha256(panel_path),
        },
        "difference_metrics": {
            "full_image_diff_bbox": list(bbox) if bbox else None,
            "full_image_diff_rms_sum": round(rms, 4),
        },
        "strict_whole_image_findings": [
            "Generated output proves the v3-specific local route executed and used the aperture-only mask preview.",
            "Identity, face outline, hair volume, blazer, lighting, and background remain broadly stable.",
            "Eye region is not acceptable for promotion: both eyes appear softened and the gaze/eye character is subtly changed versus the source.",
            "No large eyebrow or hair-region overwrite is visible, which supports the v3 geometry direction.",
            "Because the eye quality changed, this remains an iteration artifact and does not close TRK/ITEM-W70-0009.",
        ],
        "qa_decision": "do_not_promote_retry_with_lower_denoise",
        "next_required_action": "Create a lower-denoise v3b request and rerun the minimum local sample to see whether eye/gaze preservation improves.",
    }

    qa_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(qa_path, payload)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(qa_path, tracker_path)
    print(json.dumps({"qa": rel(qa_path), "tracker": rel(tracker_path), "panel": rel(panel_path), "result": payload["result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
