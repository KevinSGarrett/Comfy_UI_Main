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


RUN_STAMP = "20260710T032500-0500"
TIMESTAMP = "2026-07-10T03:25:00-05:00"
MASK_TYPE_ID = "mf70_face_skin"
SOURCE_IMAGE = Path("ComfyUI/input/wave70_mf70_face_identity_source_canny_v3.png")
PARSER_MASK_DIR = Path(
    "runtime_artifacts/mask_factory/wave70_face_parsing_authority/"
    "20260708T102325-0500/face_parsing_bisenet/output/masks/source"
)
PARSER_SKIN = PARSER_MASK_DIR / "01_skin.png"
PARSER_BROW = PARSER_MASK_DIR / "02_l_brow.png"
PARSER_EYE = PARSER_MASK_DIR / "04_l_eye.png"
PARSER_NOSE = PARSER_MASK_DIR / "10_nose.png"
PARSER_MOUTH = PARSER_MASK_DIR / "11_mouth.png"
PARSER_UPPER_LIP = PARSER_MASK_DIR / "12_u_lip.png"
PARSER_LOWER_LIP = PARSER_MASK_DIR / "13_l_lip.png"
PARSER_HAIR = PARSER_MASK_DIR / "17_hair.png"
PARSER_CLOTH = PARSER_MASK_DIR / "16_cloth.png"
ROUTE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_BLOCKED_FACIAL_POSTPROCESS_ROUTE_EVAL_20260710T024500-0500.json"
)
OUT_DIR = Path(
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_face_skin_hull_v2_{RUN_STAMP}"
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


def overlap(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.logical_and(a > 0, b > 0).sum())


def save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask).save(path)


def overlay(source: Image.Image, mask: np.ndarray, color: tuple[int, int, int], alpha: float = 0.55) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[mask > 0] = (*color, int(255 * alpha))
    return Image.alpha_composite(base, Image.fromarray(arr, mode="RGBA")).convert("RGB")


def protected_overlay(
    source: Image.Image,
    candidate: np.ndarray,
    eye_brow: np.ndarray,
    lips_mouth: np.ndarray,
    hair_cloth: np.ndarray,
    nose: np.ndarray,
) -> Image.Image:
    base = source.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(layer)
    arr[candidate > 0] = (0, 220, 220, 145)
    arr[hair_cloth > 0] = (255, 128, 0, 120)
    arr[nose > 0] = (255, 70, 70, 125)
    arr[lips_mouth > 0] = (255, 0, 190, 145)
    arr[eye_brow > 0] = (255, 235, 0, 145)
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
    parser_skin: np.ndarray,
    candidate: np.ndarray,
    eye_brow: np.ndarray,
    lips_mouth: np.ndarray,
    hair_cloth: np.ndarray,
    nose: np.ndarray,
) -> str:
    tiles = [
        label_tile(source, "target source"),
        label_tile(overlay(source, parser_skin, (255, 255, 255)), "parser skin baseline"),
        label_tile(overlay(source, candidate, (0, 220, 220)), "hull face-skin candidate"),
        label_tile(protected_overlay(source, candidate, eye_brow, lips_mouth, hair_cloth, nose), "skin cyan / eye-brow yellow / lips magenta / nose red / hair-cloth orange"),
    ]
    panel = Image.new("RGB", (320 * len(tiles), 354), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (320 * index, 0))
    panel_dir = root / "runtime_artifacts/mask_factory/wave70_mf70_face_skin_hull_v2" / RUN_STAMP
    panel_dir.mkdir(parents=True, exist_ok=True)
    panel_path = panel_dir / "wave70_mf70_face_skin_hull_v2_review_panel.png"
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

    required = [
        SOURCE_IMAGE,
        PARSER_SKIN,
        PARSER_BROW,
        PARSER_EYE,
        PARSER_NOSE,
        PARSER_MOUTH,
        PARSER_UPPER_LIP,
        PARSER_LOWER_LIP,
        PARSER_HAIR,
        PARSER_CLOTH,
        ROUTE_EVIDENCE,
    ]
    for path in required:
        if not resolve(root, path).exists():
            raise FileNotFoundError(path.as_posix())

    route_evidence = read_json(resolve(root, ROUTE_EVIDENCE))
    route = next(r for r in route_evidence["route_records"] if r["region"] == MASK_TYPE_ID)
    if not route["passes_current_gold_gate"]:
        raise RuntimeError("mf70_face_skin route does not pass current gold gate")

    source = Image.open(resolve(root, SOURCE_IMAGE)).convert("RGB")
    parser_skin = load_mask(resolve(root, PARSER_SKIN))
    candidate = hull(parser_skin)
    brow = load_mask(resolve(root, PARSER_BROW))
    eye = load_mask(resolve(root, PARSER_EYE))
    nose = load_mask(resolve(root, PARSER_NOSE))
    mouth = load_mask(resolve(root, PARSER_MOUTH))
    upper = load_mask(resolve(root, PARSER_UPPER_LIP))
    lower = load_mask(resolve(root, PARSER_LOWER_LIP))
    hair = load_mask(resolve(root, PARSER_HAIR))
    cloth = load_mask(resolve(root, PARSER_CLOTH))
    eye_brow = np.maximum(eye, brow)
    lips_mouth = np.maximum(mouth, np.maximum(upper, lower))
    hair_cloth = np.maximum(hair, cloth)

    out_dir = resolve(root, OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / "wave70_mf70_face_skin_hull_v2_mask.png"
    overlay_path = out_dir / "wave70_mf70_face_skin_hull_v2_overlay.png"
    protected_path = out_dir / "wave70_mf70_face_skin_hull_v2_protected_overlay.png"
    save_mask(candidate, mask_path)
    overlay(source, candidate, (0, 220, 220)).save(overlay_path)
    protected_overlay(source, candidate, eye_brow, lips_mouth, hair_cloth, nose).save(protected_path)
    panel_rel = make_panel(root, source, parser_skin, candidate, eye_brow, lips_mouth, hair_cloth, nose)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-FACE-SKIN-HULL-V2-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "target_specific_unpromoted_candidate_creation",
        "mask_type_id": MASK_TYPE_ID,
        "route_source_evidence": rel(resolve(root, ROUTE_EVIDENCE), root),
        "route_source_evidence_sha256": sha256_file(resolve(root, ROUTE_EVIDENCE)),
        "route": route["route"],
        "route_gold_benchmark_summary": route["postprocess_summary"],
        "source_image": rel(resolve(root, SOURCE_IMAGE), root),
        "parser_skin_mask": rel(resolve(root, PARSER_SKIN), root),
        "candidate_mask": rel(mask_path, root),
        "candidate_mask_sha256": sha256_file(mask_path),
        "candidate_overlay": rel(overlay_path, root),
        "candidate_overlay_sha256": sha256_file(overlay_path),
        "protected_overlay": rel(protected_path, root),
        "protected_overlay_sha256": sha256_file(protected_path),
        "review_panel": panel_rel,
        "review_panel_sha256": sha256_file(resolve(root, panel_rel)),
        "stats": {
            "parser_skin": stats(parser_skin),
            "candidate": stats(candidate),
            "candidate_overlap_with_eye_brow_pixels": overlap(candidate, eye_brow),
            "candidate_overlap_with_lips_mouth_pixels": overlap(candidate, lips_mouth),
            "candidate_overlap_with_nose_pixels": overlap(candidate, nose),
            "candidate_overlap_with_hair_cloth_pixels": overlap(candidate, hair_cloth),
        },
        "finding": (
            "Hull route matches the gold skin benchmark but target-specific protected overlay must be reviewed carefully because "
            "face-skin masks can cover nose and facial feature boundaries by design."
        ),
        "decision": "candidate_created_pending_strict_visual_review_not_promoted",
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "candidate_created_pending_strict_visual_review_not_promoted",
        "next_required_action": "Strictly review protected overlay before any generated-output proof; do not overwrite active inputs.",
    }
    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / f"W70_MF70_FACE_SKIN_HULL_V2_{RUN_STAMP}.json"
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_face_skin Hull V2 Candidate - {TIMESTAMP}

Created an unpromoted target-specific `mf70_face_skin` hull v2 candidate from the gold-benchmark-passing route. Evidence `{rel(out, root)}` reports `candidate_created_pending_strict_visual_review_not_promoted`; review panel `{panel_rel}` includes protected overlays for eye/brow, lips/mouth, nose, hair, and clothing. No active input, mask promotion, generation, EC2, AWS, GitHub, S3, Civitai, final certification, or row completion occurred.
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
                "overlaps": evidence["stats"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
