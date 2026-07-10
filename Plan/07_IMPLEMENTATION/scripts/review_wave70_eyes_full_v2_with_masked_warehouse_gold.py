#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Comfy_UI_Main")
EYES_EVIDENCE = (
    ROOT
    / "Plan"
    / "Instructions"
    / "QA"
    / "Evidence"
    / "Mask_Factory"
    / "Wave70"
    / "W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V2_20260709T215300-0500.json"
)
GOLD_EVIDENCE = (
    ROOT
    / "Plan"
    / "Instructions"
    / "QA"
    / "Evidence"
    / "Mask_Factory"
    / "Wave70"
    / "W70_MASKED_WAREHOUSE_FACIAL_GOLD_STANDARD_INTAKE_20260709T221608-0500.json"
)
OUT_DIR = ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = ROOT / "Plan" / "Tracker" / "Evidence"
PANEL_DIR = ROOT / "runtime_artifacts" / "mask_factory" / "wave70_mf70_eyes_full_gold_standard_review"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def thumb(path: Path, size: tuple[int, int], mode: str = "RGB") -> Image.Image:
    im = Image.open(path).convert(mode)
    im.thumbnail(size)
    canvas = Image.new(mode, size, "white" if mode == "RGB" else 0)
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return canvas.convert("RGB")


def mask_to_color(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    im = Image.open(path).convert("L")
    im.thumbnail(size)
    mask = Image.new("L", size, 0)
    mask.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    bg = Image.new("RGB", size, "black")
    fg = Image.new("RGB", size, color)
    return Image.composite(fg, bg, mask.point(lambda v: 255 if v else 0))


def lapa_color_label(path: Path, size: tuple[int, int]) -> Image.Image:
    palette = {
        0: (20, 20, 20),
        1: (55, 200, 210),
        2: (220, 150, 230),
        3: (220, 150, 230),
        4: (255, 220, 0),
        5: (255, 220, 0),
        6: (210, 40, 60),
        7: (255, 90, 70),
        8: (255, 255, 255),
        9: (160, 100, 220),
        10: (0, 140, 170),
    }
    src = Image.open(path).convert("L")
    rgb = Image.new("RGB", src.size)
    src_px = src.load()
    out_px = rgb.load()
    for y in range(src.height):
        for x in range(src.width):
            out_px[x, y] = palette.get(src_px[x, y], (120, 120, 120))
    rgb.thumbnail(size)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(rgb, ((size[0] - rgb.width) // 2, (size[1] - rgb.height) // 2))
    return canvas


def cell(image: Image.Image, title: str, note: str = "") -> Image.Image:
    header = 56
    out = Image.new("RGB", (image.width, image.height + header), "white")
    out.paste(image, (0, header))
    draw = ImageDraw.Draw(out)
    draw.text((8, 6), title, fill=(0, 0, 0), font=font(18))
    if note:
        draw.text((8, 30), note, fill=(65, 65, 65), font=font(13))
    return out


def part_from_celeba(path: Path) -> str:
    return path.stem.split("_", 1)[1]


def current_mask_stats(mask_path: Path) -> dict:
    im = Image.open(mask_path).convert("L")
    bbox = im.getbbox()
    pixels = sum(1 for v in im.getdata() if v)
    area = im.width * im.height
    return {
        "image_size": [im.width, im.height],
        "nonzero_pixels": pixels,
        "nonzero_ratio": round(pixels / area, 6) if area else 0,
        "bbox": list(bbox) if bbox else None,
        "bbox_ratio": [
            round(bbox[0] / im.width, 6),
            round(bbox[1] / im.height, 6),
            round(bbox[2] / im.width, 6),
            round(bbox[3] / im.height, 6),
        ]
        if bbox
        else None,
    }


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S-0500")
    eyes = load_json(EYES_EVIDENCE)
    gold = load_json(GOLD_EVIDENCE)
    artifacts = eyes["artifacts"]
    current_mask = ROOT / artifacts["mask"]
    current_overlay = ROOT / artifacts["overlay"]
    current_review_panel = ROOT / artifacts["review_panel"]

    celeba_sample = gold["datasets"]["CelebAMask-HQ"]["selected_sample"]
    lapa_sample = gold["datasets"]["LaPa"]["selected_sample"]
    celeba_image = Path(celeba_sample["image"])
    celeba_masks = {part_from_celeba(Path(p)): Path(p) for p in celeba_sample["masks"]}
    lapa_image = Path(lapa_sample["image"])
    lapa_label = Path(lapa_sample["label"])

    cells = [
        cell(thumb(current_overlay, (300, 300)), "Current mf70_eyes_full v2", "candidate only, not promoted"),
        cell(mask_to_color(current_mask, (300, 300), (255, 220, 0)), "Current mask bitmap", "yellow = proposed eye apertures"),
        cell(thumb(current_review_panel, (300, 300)), "Current review panel", "source/overlay/mask triptych"),
        cell(thumb(celeba_image, (300, 300)), "Gold source image", "CelebAMask-HQ paired source"),
        cell(mask_to_color(celeba_masks["l_eye"], (300, 300), (255, 220, 0)), "Gold left eye mask", "small aperture-hugging region"),
        cell(mask_to_color(celeba_masks["r_eye"], (300, 300), (255, 220, 0)), "Gold right eye mask", "small aperture-hugging region"),
        cell(mask_to_color(celeba_masks["l_brow"], (300, 300), (220, 150, 230)), "Gold left brow mask", "separate from eyelid/eye"),
        cell(mask_to_color(celeba_masks["r_brow"], (300, 300), (220, 150, 230)), "Gold right brow mask", "separate from eyelid/eye"),
        cell(thumb(lapa_image, (300, 300)), "LaPa source image", "image + parsing label + landmarks"),
        cell(lapa_color_label(lapa_label, (300, 300)), "LaPa facial parsing", "yellow eyes, purple brows, red nose"),
    ]

    cols = 5
    cell_w = max(c.width for c in cells)
    cell_h = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for i, c in enumerate(cells):
        panel.paste(c, ((i % cols) * cell_w, (i // cols) * cell_h))

    panel_path = PANEL_DIR / timestamp / "mf70_eyes_full_v2_masked_warehouse_gold_review_panel.png"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)

    evidence = {
        "evidence_id": f"W70_MF70_EYES_FULL_V2_MASKED_WAREHOUSE_GOLD_REVIEW_{timestamp}",
        "timestamp": timestamp,
        "scope": "local strict visual bridge review of mf70_eyes_full v2 against MaskedWarehouse facial gold-standard datasets",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "current_candidate_evidence": rel(EYES_EVIDENCE),
        "gold_standard_intake_evidence": rel(GOLD_EVIDENCE),
        "current_artifacts": {
            "mask": rel(current_mask),
            "overlay": rel(current_overlay),
            "review_panel": rel(current_review_panel),
            "mask_sha256": sha256(current_mask),
            "overlay_sha256": sha256(current_overlay),
        },
        "gold_artifacts_used": {
            "celeba_image": str(celeba_image),
            "celeba_left_eye": str(celeba_masks["l_eye"]),
            "celeba_right_eye": str(celeba_masks["r_eye"]),
            "celeba_left_brow": str(celeba_masks["l_brow"]),
            "celeba_right_brow": str(celeba_masks["r_brow"]),
            "lapa_image": str(lapa_image),
            "lapa_label": str(lapa_label),
        },
        "current_mask_stats": current_mask_stats(current_mask),
        "strict_visual_findings": [
            "Gold references confirm eyes_full should hug visible eye apertures and stay separate from eyebrow and hair regions.",
            "Gold brow references confirm eyebrows are separate narrow regions above the eyes, not part of the eyes_full mask.",
            "The current v2 eyes_full candidate is materially better than the old broad eye block, but this bridge review is not a promotion proof.",
            "Future facial-mask repair must use MaskedWarehouse references for eye, brow, nose, lip, mouth, hair, skin, and neck neighbor boundaries before promotion.",
        ],
        "decision": "gold_standard_bridge_review_created_current_eyes_full_v2_remains_candidate_not_promoted",
        "next_required_action": (
            "Use the MaskedWarehouse gold references to produce the next facial-mask repair/review packet, "
            "starting with eyes/eyebrows separation and then nose/lips/hair/skin neighbor boundaries."
        ),
        "panel_path": rel(panel_path),
        "panel_sha256": sha256(panel_path),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{evidence['evidence_id']}.json"
    tracker_path = TRACKER_DIR / f"{evidence['evidence_id']}.json"
    text = json.dumps(evidence, indent=2, sort_keys=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    tracker_path.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"evidence": rel(out_path), "tracker": rel(tracker_path), "panel": rel(panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
