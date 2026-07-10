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


RUN_STAMP = "20260710T025200-0500"
TIMESTAMP = "2026-07-10T02:52:00-05:00"
MASK_TYPE_ID = "mf70_teeth_mouth_area"
SOURCE_IMAGE = Path("ComfyUI/input/wave70_mf70_face_identity_source_canny_v3.png")
PARSER_MASK_DIR = Path(
    "runtime_artifacts/mask_factory/wave70_face_parsing_authority/"
    "20260708T102325-0500/face_parsing_bisenet/output/masks/source"
)
PARSER_MOUTH = PARSER_MASK_DIR / "11_mouth.png"
PARSER_UPPER_LIP = PARSER_MASK_DIR / "12_u_lip.png"
PARSER_LOWER_LIP = PARSER_MASK_DIR / "13_l_lip.png"
PARSER_NOSE = PARSER_MASK_DIR / "10_nose.png"
ACTIVE_TEETH_MASK = Path("ComfyUI/input/wave70_mf70_teeth_mask.png")
ROUTE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_BLOCKED_FACIAL_POSTPROCESS_ROUTE_EVAL_20260710T024500-0500.json"
)
OUT_DIR = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_teeth_mouth_area_postprocess_v2_{RUN_STAMP}"
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


def load_mask(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(path)
    return ((image > 0).astype(np.uint8)) * 255


def postprocess_mouth_area(mask: np.ndarray) -> np.ndarray:
    eroded = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 3)))
    return cv2.dilate(eroded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 7)))


def stats(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        bbox = None
    else:
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return {"pixels": int((mask > 0).sum()), "bbox": bbox, "width": int(mask.shape[1]), "height": int(mask.shape[0])}


def overlap(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.logical_and(a > 0, b > 0).sum())


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask).save(path)


def overlay(source: Image.Image, mask: np.ndarray, color: tuple[int, int, int], alpha: float = 0.58) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[mask > 0] = (*color, int(255 * alpha))
    layer = Image.fromarray(arr, mode="RGBA")
    return Image.alpha_composite(base, layer).convert("RGB")


def combo_overlay(source: Image.Image, candidate: np.ndarray, lips: np.ndarray, nose: np.ndarray) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[lips > 0] = (0, 200, 255, 115)
    arr[nose > 0] = (255, 80, 80, 115)
    arr[candidate > 0] = (255, 210, 0, 165)
    return Image.alpha_composite(base, Image.fromarray(arr, mode="RGBA")).convert("RGB")


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


def make_panel(
    root: Path,
    source: Image.Image,
    parser_mouth: np.ndarray,
    active_teeth: np.ndarray,
    candidate: np.ndarray,
    lips: np.ndarray,
    nose: np.ndarray,
) -> str:
    tiles = [
        label_tile(source, "target source"),
        label_tile(overlay(source, active_teeth, (0, 220, 255)), "old active teeth mask"),
        label_tile(overlay(source, parser_mouth, (255, 255, 255)), "parser mouth baseline"),
        label_tile(overlay(source, candidate, (255, 210, 0)), "v2 mouth-area candidate"),
        label_tile(combo_overlay(source, candidate, lips, nose), "candidate yellow / lips cyan / nose red"),
    ]
    panel = Image.new("RGB", (320 * len(tiles), 354), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (320 * index, 0))
    panel_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_teeth_mouth_area_postprocess_v2" / RUN_STAMP
    panel_dir.mkdir(parents=True, exist_ok=True)
    panel_path = panel_dir / "wave70_mf70_teeth_mouth_area_postprocess_v2_review_panel.png"
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

    for path in [SOURCE_IMAGE, PARSER_MOUTH, PARSER_UPPER_LIP, PARSER_LOWER_LIP, PARSER_NOSE, ACTIVE_TEETH_MASK, ROUTE_EVIDENCE]:
        if not resolve(root, path).exists():
            raise FileNotFoundError(path.as_posix())

    route_evidence = read_json(resolve(root, ROUTE_EVIDENCE))
    route = next(r for r in route_evidence["route_records"] if r["region"] == MASK_TYPE_ID)
    if not route["passes_current_gold_gate"]:
        raise RuntimeError("mf70_teeth_mouth_area route does not pass current gold gate")

    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    parser_mouth = load_mask(resolve(root, PARSER_MOUTH))
    active_teeth = load_mask(resolve(root, ACTIVE_TEETH_MASK))
    lips = np.maximum(load_mask(resolve(root, PARSER_UPPER_LIP)), load_mask(resolve(root, PARSER_LOWER_LIP)))
    nose = load_mask(resolve(root, PARSER_NOSE))
    candidate = postprocess_mouth_area(parser_mouth)

    out_dir = resolve(root, OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / "wave70_mf70_teeth_mouth_area_postprocess_v2_mask.png"
    overlay_path = out_dir / "wave70_mf70_teeth_mouth_area_postprocess_v2_overlay.png"
    protected_overlay_path = out_dir / "wave70_mf70_teeth_mouth_area_postprocess_v2_protected_overlay.png"
    save_mask(candidate, mask_path)
    overlay(source, candidate, (255, 210, 0)).save(overlay_path)
    combo_overlay(source, candidate, lips, nose).save(protected_overlay_path)
    panel_rel = make_panel(root, source, parser_mouth, active_teeth, candidate, lips, nose)

    candidate_stats = stats(candidate)
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-TEETH-MOUTH-AREA-POSTPROCESS-V2-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "target_specific_unpromoted_candidate_creation",
        "mask_type_id": MASK_TYPE_ID,
        "route_source_evidence": rel(resolve(root, ROUTE_EVIDENCE), root),
        "route_source_evidence_sha256": sha256_file(resolve(root, ROUTE_EVIDENCE)),
        "route": route["route"],
        "route_gold_benchmark_summary": route["postprocess_summary"],
        "source_image": rel(resolve(root, SOURCE_IMAGE), root),
        "parser_mouth_mask": rel(resolve(root, PARSER_MOUTH), root),
        "active_teeth_mask_compared_not_overwritten": rel(resolve(root, ACTIVE_TEETH_MASK), root),
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": sha256_file(mask_path),
        "candidate_overlay": rel(overlay_path, root),
        "candidate_overlay_sha256": sha256_file(overlay_path),
        "protected_overlay": rel(protected_overlay_path, root),
        "protected_overlay_sha256": sha256_file(protected_overlay_path),
        "review_panel": panel_rel,
        "review_panel_sha256": sha256_file(resolve(root, panel_rel)),
        "stats": {
            "parser_mouth": stats(parser_mouth),
            "old_active_teeth": stats(active_teeth),
            "candidate": candidate_stats,
            "candidate_overlap_with_predicted_lips_pixels": overlap(candidate, lips),
            "candidate_overlap_with_predicted_nose_pixels": overlap(candidate, nose),
        },
        "finding": (
            "Candidate is broader than the old active teeth-only mask because the gold benchmark region maps to CelebAMask-HQ mouth, "
            "not just visible teeth. It is suitable only for strict source-overlay review before any runtime proof."
        ),
        "decision": "candidate_created_pending_strict_visual_review_not_promoted",
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "candidate_created_pending_strict_visual_review_not_promoted",
        "next_required_action": (
            "Strictly review the panel and protected overlay. If acceptable, copy to a v2-specific ComfyUI input filename and run one bounded local proof; "
            "do not overwrite wave70_mf70_teeth_mask.png."
        ),
    }
    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_TEETH_MOUTH_AREA_POSTPROCESS_V2_{RUN_STAMP}.json"
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_teeth_mouth_area Postprocess V2 Candidate - {TIMESTAMP}

Created an unpromoted target-specific `mf70_teeth_mouth_area` candidate from the gold-benchmark-passing mouth-area postprocess route. Evidence `{rel(out, root)}` reports `candidate_created_pending_strict_visual_review_not_promoted`; review panel `{panel_rel}` compares the target source, old active teeth-only mask, parser mouth baseline, v2 candidate, and protected lip/nose overlay. The active `ComfyUI/input/wave70_mf70_teeth_mask.png` was not overwritten. No generation, EC2, AWS, GitHub, S3, Civitai, final certification, or mask promotion occurred.
"""
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)

    print(
        json.dumps(
            {
                "result": evidence["result"],
                "evidence": rel(out, root),
                "tracker": rel(tracker, root),
                "candidate_mask": rel(mask_path, root),
                "review_panel": panel_rel,
                "candidate_overlap_with_predicted_lips_pixels": evidence["stats"]["candidate_overlap_with_predicted_lips_pixels"],
                "candidate_overlap_with_predicted_nose_pixels": evidence["stats"]["candidate_overlap_with_predicted_nose_pixels"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
