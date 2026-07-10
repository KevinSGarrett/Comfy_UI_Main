#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260710T033800-0500"
TIMESTAMP = "2026-07-10T03:38:00-05:00"
MASK_TYPE_ID = "mf70_face_skin"
SOURCE_IMAGE = Path("ComfyUI/input/wave70_mf70_face_identity_source_canny_v3.png")
PARSER_MASK_DIR = Path(
    "runtime_artifacts/mask_factory/wave70_face_parsing_authority/"
    "20260708T102325-0500/face_parsing_bisenet/output/masks/source"
)
PARSER_SKIN = PARSER_MASK_DIR / "01_skin.png"
PROTECTED_NAMES = [
    "02_l_brow.png",
    "04_l_eye.png",
    "11_mouth.png",
    "12_u_lip.png",
    "13_l_lip.png",
    "16_cloth.png",
    "17_hair.png",
]
HULL_REVIEW = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_FACE_SKIN_HULL_V2_STRICT_VISUAL_REVIEW_20260710T033200-0500.json"
)
OUT_DIR = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_face_skin_protected_v3_{RUN_STAMP}"
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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_mask(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(path)
    return ((image > 0).astype(np.uint8)) * 255


def hull(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(mask)
    for contour in contours:
        if cv2.contourArea(contour) >= 2:
            cv2.drawContours(out, [cv2.convexHull(contour)], -1, 255, -1)
    return out


def stats(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask > 0)
    bbox = None if len(xs) == 0 else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return {"pixels": int((mask > 0).sum()), "bbox": bbox, "width": int(mask.shape[1]), "height": int(mask.shape[0])}


def overlay(source: Image.Image, mask: np.ndarray, color: tuple[int, int, int], alpha: float = 0.55) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[mask > 0] = (*color, int(255 * alpha))
    return Image.alpha_composite(base, Image.fromarray(arr, mode="RGBA")).convert("RGB")


def multi_overlay(source: Image.Image, protected: np.ndarray, candidate: np.ndarray) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[candidate > 0] = (0, 220, 220, 145)
    arr[protected > 0] = (255, 60, 180, 145)
    return Image.alpha_composite(base, Image.fromarray(arr, mode="RGBA")).convert("RGB")


def label_tile(image: Image.Image, label: str, size: int = 320) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), (Image.Resampling.LANCZOS)), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


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

    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    skin = load_mask(resolve(root, PARSER_SKIN))
    protected = np.zeros_like(skin)
    for name in PROTECTED_NAMES:
        path = resolve(root, PARSER_MASK_DIR / name)
        if path.exists():
            protected = np.maximum(protected, load_mask(path))
    candidate = np.where(protected > 0, 0, hull(skin)).astype(np.uint8)

    out_dir = resolve(root, OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / "wave70_mf70_face_skin_protected_v3_mask.png"
    overlay_path = out_dir / "wave70_mf70_face_skin_protected_v3_overlay.png"
    protected_overlay_path = out_dir / "wave70_mf70_face_skin_protected_v3_protected_overlay.png"
    Image.fromarray(candidate).save(mask_path)
    overlay(source, candidate, (0, 220, 220)).save(overlay_path)
    multi_overlay(source, protected, candidate).save(protected_overlay_path)

    tiles = [
        label_tile(source, "target source"),
        label_tile(overlay(source, hull(skin), (0, 220, 220)), "hull v2 runtime-blocked"),
        label_tile(overlay(source, candidate, (0, 220, 220)), "protected v3 candidate"),
        label_tile(multi_overlay(source, protected, candidate), "protected v3 cyan / exclusions magenta"),
    ]
    panel = Image.new("RGB", (320 * len(tiles), 354), (0, 0, 0))
    for i, tile in enumerate(tiles):
        panel.paste(tile, (320 * i, 0))
    panel_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_face_skin_protected_v3" / RUN_STAMP
    panel_dir.mkdir(parents=True, exist_ok=True)
    panel_path = panel_dir / "wave70_mf70_face_skin_protected_v3_review_panel.png"
    panel.save(panel_path)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-FACE-SKIN-PROTECTED-V3-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "target_specific_protected_candidate_creation_benchmark_tradeoff_recorded",
        "mask_type_id": MASK_TYPE_ID,
        "hull_runtime_blocker": rel(resolve(root, HULL_REVIEW), root),
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": sha256_file(mask_path),
        "candidate_overlay": rel(overlay_path, root),
        "protected_overlay": rel(protected_overlay_path, root),
        "review_panel": rel(panel_path, root),
        "review_panel_sha256": sha256_file(panel_path),
        "protected_route_gold_benchmark_tradeoff": {
            "mean_iou": 0.821973,
            "mean_false_positive_ratio_vs_gold": 0.000662,
            "mean_false_negative_ratio_vs_gold": 0.177463,
            "passes_current_gold_gate": False,
            "reason": "Feature-protection removes pixels that the current CelebAMask-HQ skin benchmark counts as skin, so the route is safer for runtime but below the current gold gate."
        },
        "stats": {
            "parser_skin": stats(skin),
            "protected_exclusions": stats(protected),
            "candidate": stats(candidate),
        },
        "decision": "candidate_created_benchmark_tradeoff_generated_output_blocked_pending_policy_choice",
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "candidate_created_benchmark_tradeoff_generated_output_blocked_pending_policy_choice",
        "next_required_action": "Choose whether mf70_face_skin should follow dataset skin benchmark or runtime-protected feature-safe mask before any generated-output proof.",
    }
    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_FACE_SKIN_PROTECTED_V3_{RUN_STAMP}.json"
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_face_skin Protected V3 Candidate - {TIMESTAMP}

Created protected `mf70_face_skin` v3 candidate after hull v2 passed the benchmark but failed runtime visual safety. Evidence `{rel(out, root)}` reports `candidate_created_benchmark_tradeoff_generated_output_blocked_pending_policy_choice`: protected v3 excludes feature/hair/clothing regions and is visually safer, but its measured gold benchmark tradeoff is mean IoU `0.821973`, below the current `0.85` gate. Do not run generated-output proof until the face-skin row policy is clarified as dataset-skin benchmark versus runtime-protected skin mask. No active input, generation, EC2, AWS, GitHub, S3, Civitai, promotion, or row completion occurred.
"""
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)

    print(json.dumps({"result": evidence["result"], "evidence": rel(out, root), "tracker": rel(tracker, root), "panel": rel(panel_path, root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
