#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MF70_NOSE_PARSER_DERIVED_V5_{STAMP}"

SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
V4_MASK = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_visible_surface_v4_20260710T010600-0500/"
    "wave70_mf70_nose_visible_surface_v4_mask.png"
)
PARSER_MASK_DIR = PROJECT_ROOT / (
    "runtime_artifacts/mask_factory/wave70_face_parsing_authority/"
    "20260708T102325-0500/face_parsing_bisenet/output/masks/source"
)
PARSER_NOSE = PARSER_MASK_DIR / "10_nose.png"
PARSER_MOUTH = PARSER_MASK_DIR / "11_mouth.png"
PARSER_U_LIP = PARSER_MASK_DIR / "12_u_lip.png"
PARSER_L_LIP = PARSER_MASK_DIR / "13_l_lip.png"
PARSER_SKIN = PARSER_MASK_DIR / "01_skin.png"

BENCHMARK_GATE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_BENCHMARK_GATE_20260710T013355-0500.json"
)
NOSE_V4_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_NOSE_VISIBLE_SURFACE_REPAIR_V4_20260710T010600-0500.json"
)
OUT_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "Operations" / "Prepared_Input_Assets" / f"wave70_mf70_nose_parser_derived_v5_{STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_mf70_nose_parser_derived_v5" / STAMP
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
ACTIVE_INPUT = PROJECT_ROOT / "ComfyUI" / "input" / "wave70_mf70_nose_mask.png"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_mask(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return image.point(lambda value: 255 if value > 0 else 0)


def count(mask: Image.Image) -> int:
    return sum(1 for value in mask.getdata() if value)


def overlap(a: Image.Image, b: Image.Image) -> int:
    return count(ImageChops.multiply(a, b))


def iou(a: Image.Image, b: Image.Image) -> dict[str, Any]:
    inter = overlap(a, b)
    union = count(ImageChops.lighter(a, b))
    return {
        "intersection_pixels": inter,
        "union_pixels": union,
        "iou": round(inter / union, 6) if union else 1.0,
    }


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def label_tile(image: Image.Image, title: str, subtitle: str = "", size: tuple[int, int] = (340, 340)) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail(size)
    out = Image.new("RGB", (size[0], size[1] + 54), "white")
    out.paste(image, ((size[0] - image.width) // 2, 54 + (size[1] - image.height) // 2))
    draw = ImageDraw.Draw(out)
    draw.text((8, 7), title[:44], fill=(0, 0, 0), font=font(16))
    if subtitle:
        draw.text((8, 30), subtitle[:58], fill=(70, 70, 70), font=font(12))
    return out


def overlay(source: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (*color, 0))
    fill.putalpha(mask.point(lambda value: 130 if value else 0))
    return Image.alpha_composite(rgba, fill).convert("RGB")


def protected_overlay(source: Image.Image, nose: Image.Image, protected: Image.Image) -> Image.Image:
    out = overlay(source, protected, (0, 210, 230)).convert("RGBA")
    fill = Image.new("RGBA", out.size, (255, 40, 40, 0))
    fill.putalpha(nose.point(lambda value: 140 if value else 0))
    return Image.alpha_composite(out, fill).convert("RGB")


def make_panel(source: Image.Image, v4: Image.Image, v5: Image.Image, parser_nose: Image.Image, protected: Image.Image, panel_path: Path) -> None:
    cells = [
        label_tile(source, "target source", "source portrait"),
        label_tile(overlay(source, v4, (255, 40, 40)), "v4 hand candidate", "unpromoted prior candidate"),
        label_tile(overlay(source, parser_nose, (255, 210, 0)), "parser nose", "gold-benchmark-supported route"),
        label_tile(overlay(source, v5, (40, 210, 80)), "v5 parser-derived candidate", "mouth/lip clipped"),
        label_tile(protected_overlay(source, v5, protected), "v5 vs mouth/lips", "red nose / cyan protected"),
    ]
    cols = 3
    w = max(cell.width for cell in cells)
    h = max(cell.height for cell in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * w, rows * h), "white")
    for idx, cell in enumerate(cells):
        panel.paste(cell, ((idx % cols) * w, (idx // cols) * h))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    for path in [SOURCE_IMAGE, V4_MASK, PARSER_NOSE, PARSER_MOUTH, PARSER_U_LIP, PARSER_L_LIP, PARSER_SKIN, BENCHMARK_GATE, NOSE_V4_EVIDENCE]:
        if not path.exists():
            raise FileNotFoundError(path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    size = source.size
    v4 = load_mask(V4_MASK, size)
    parser_nose = load_mask(PARSER_NOSE, size)
    protected = ImageChops.lighter(load_mask(PARSER_MOUTH, size), load_mask(PARSER_U_LIP, size))
    protected = ImageChops.lighter(protected, load_mask(PARSER_L_LIP, size)).point(lambda value: 255 if value > 0 else 0)
    skin = load_mask(PARSER_SKIN, size)

    # BiSeNet labels are mutually exclusive, so parser nose pixels are not also
    # inside the parser skin mask. Clip only explicit mouth/lip protected
    # regions; do not multiply by skin or the nose disappears.
    v5 = ImageChops.subtract(parser_nose, protected).point(lambda value: 255 if value > 0 else 0)

    mask_path = OUT_DIR / "wave70_mf70_nose_parser_derived_v5_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_nose_parser_derived_v5_overlay.png"
    panel_path = RUNTIME_DIR / "wave70_mf70_nose_parser_derived_v5_review_panel.png"
    metrics_path = OUT_DIR / "wave70_mf70_nose_parser_derived_v5_metrics.json"
    v5.save(mask_path)
    overlay(source, v5, (40, 210, 80)).save(overlay_path)
    make_panel(source, v4, v5, parser_nose, protected, panel_path)

    metrics = {
        "v4_stats": {"bbox": v4.getbbox(), "pixels": count(v4)},
        "parser_nose_stats": {"bbox": parser_nose.getbbox(), "pixels": count(parser_nose)},
        "v5_stats": {"bbox": v5.getbbox(), "pixels": count(v5)},
        "v4_vs_parser_nose": iou(v4, parser_nose),
        "v5_vs_parser_nose": iou(v5, parser_nose),
        "v4_mouth_lip_overlap_pixels": overlap(v4, protected),
        "v5_mouth_lip_overlap_pixels": overlap(v5, protected),
        "v5_skin_overlap_pixels": overlap(v5, skin),
        "note": "v5 is clipped against mouth/lip protected masks only because parser labels are mutually exclusive.",
        "active_input_sha256_before": sha256(ACTIVE_INPUT) if ACTIVE_INPUT.exists() else None,
    }
    write_json(metrics_path, metrics)

    gate = json.loads(BENCHMARK_GATE.read_text(encoding="utf-8"))
    gate_record = next(record for record in gate["region_gate_records"] if record["region"] == "mf70_nose")
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": STAMP,
        "task": "Create parser-derived mf70_nose v5 candidate after v4 hand candidate showed low target parser alignment.",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256(SOURCE_IMAGE),
        "benchmark_gate_evidence": rel(BENCHMARK_GATE),
        "benchmark_gate_mf70_nose_record": gate_record,
        "supersedes_candidate_for_review_only": rel(NOSE_V4_EVIDENCE),
        "parser_inputs": {
            "parser_nose": rel(PARSER_NOSE),
            "parser_mouth": rel(PARSER_MOUTH),
            "parser_u_lip": rel(PARSER_U_LIP),
            "parser_l_lip": rel(PARSER_L_LIP),
            "parser_skin": rel(PARSER_SKIN),
        },
        "artifacts": {
            "mask": rel(mask_path),
            "mask_sha256": sha256(mask_path),
            "overlay": rel(overlay_path),
            "overlay_sha256": sha256(overlay_path),
            "review_panel": rel(panel_path),
            "review_panel_sha256": sha256(panel_path),
            "metrics": rel(metrics_path),
            "metrics_sha256": sha256(metrics_path),
        },
        "metrics": metrics,
        "result": "candidate_created_pending_strict_visual_review_not_promoted",
        "qa_decision": "parser_derived_candidate_created_no_runtime_or_promotion",
        "strict_visual_findings": [
            "v5 is source-derived from the local BiSeNet parser nose mask, not hand-drawn geometry.",
            "v5 clips mouth, upper-lip, and lower-lip protected regions before writing the candidate.",
            "v5 aligns with the target parser nose route and keeps zero mouth/lip overlap.",
        ],
        "next_required_action": "Strict visual review the v5 panel, then only run a bounded local proof with a v5-specific input filename if the target source alignment is acceptable.",
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "panel": str(panel_path), "result": evidence["result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
