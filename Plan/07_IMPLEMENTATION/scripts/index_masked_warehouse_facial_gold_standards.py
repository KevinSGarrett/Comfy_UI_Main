#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Comfy_UI_Main")
WAREHOUSE = ROOT / "MaskedWarehouse"
OUT_DIR = ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = ROOT / "Plan" / "Tracker" / "Evidence"
PANEL_DIR = ROOT / "runtime_artifacts" / "mask_factory" / "masked_warehouse_gold_standard_intake"

CELEBA_PARTS = {
    "skin": "mf70_face_skin",
    "hair": "mf70_hair",
    "nose": "mf70_nose",
    "l_eye": "mf70_eyes_full",
    "r_eye": "mf70_eyes_full",
    "l_brow": "mf70_eyebrows",
    "r_brow": "mf70_eyebrows",
    "u_lip": "mf70_lips_top",
    "l_lip": "mf70_lips_bottom",
    "mouth": "mf70_teeth_mouth_area",
    "neck": "mf70_neck",
    "neck_l": "mf70_neck",
    "cloth": "mf70_clothing_boundary_reference",
    "l_ear": "mf70_ear_reference",
    "r_ear": "mf70_ear_reference",
    "ear_l": "mf70_ear_reference",
    "ear_r": "mf70_ear_reference",
    "eye_g": "mf70_eye_glasses_reference",
    "hat": "mf70_hat_reference",
}

# LaPa label IDs follow the common face-parsing order used by the dataset.
LAPA_LABELS = {
    0: "background",
    1: "skin",
    2: "left_eyebrow",
    3: "right_eyebrow",
    4: "left_eye",
    5: "right_eye",
    6: "nose",
    7: "upper_lip",
    8: "inner_mouth",
    9: "lower_lip",
    10: "hair",
}

LAPA_TO_MF70 = {
    "skin": "mf70_face_skin",
    "left_eyebrow": "mf70_eyebrows",
    "right_eyebrow": "mf70_eyebrows",
    "left_eye": "mf70_eyes_full",
    "right_eye": "mf70_eyes_full",
    "nose": "mf70_nose",
    "upper_lip": "mf70_lips_top",
    "inner_mouth": "mf70_teeth_mouth_area",
    "lower_lip": "mf70_lips_bottom",
    "hair": "mf70_hair",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_count(path: Path, pattern: str) -> int:
    return sum(1 for _ in path.rglob(pattern)) if path.exists() else 0


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def part_from_celeba_mask(path: Path) -> str:
    stem = path.stem
    return stem.split("_", 1)[1] if "_" in stem else stem


def collect_celeba(root: Path) -> dict:
    dataset = root / "CelebAMask-HQ"
    image_dir = dataset / "CelebA-HQ-img"
    mask_dir = dataset / "CelebAMask-HQ-mask-anno"
    masks = list(mask_dir.rglob("*.png")) if mask_dir.exists() else []
    part_counts = Counter(part_from_celeba_mask(p) for p in masks)
    sample_ids = sorted(
        {
            p.stem.split("_", 1)[0]
            for p in masks
            if "_" in p.stem and (image_dir / f"{int(p.stem.split('_', 1)[0])}.jpg").exists()
        },
        key=lambda s: int(s),
    )
    selected_id = sample_ids[0] if sample_ids else None
    selected_image = image_dir / f"{int(selected_id)}.jpg" if selected_id is not None else None
    selected_masks = []
    if selected_id is not None:
        selected_masks = sorted(mask_dir.rglob(f"{int(selected_id):05d}_*.png"))
    return {
        "dataset_root": str(dataset),
        "image_count": file_count(image_dir, "*.jpg"),
        "mask_count": len(masks),
        "part_counts": dict(sorted(part_counts.items())),
        "mapped_parts": {part: CELEBA_PARTS.get(part, "unmapped_reference_part") for part in sorted(part_counts)},
        "selected_sample": {
            "id": selected_id,
            "image": str(selected_image) if selected_image and selected_image.exists() else None,
            "mask_count": len(selected_masks),
            "masks": [str(p) for p in selected_masks],
        },
    }


def collect_lapa(root: Path) -> dict:
    dataset = root / "LaPa"
    split_records = {}
    label_values = Counter()
    selected = None
    for split in ("train", "val", "test"):
        split_root = dataset / split
        images = split_root / "images"
        labels = split_root / "labels"
        landmarks = split_root / "landmarks"
        image_count = file_count(images, "*.jpg")
        label_count = file_count(labels, "*.png")
        landmark_count = file_count(landmarks, "*.txt")
        split_records[split] = {
            "image_count": image_count,
            "label_count": label_count,
            "landmark_count": landmark_count,
        }
        if selected is None and image_count and label_count and landmark_count:
            image = next(iter(sorted(images.glob("*.jpg"))), None)
            if image:
                stem = image.stem
                label = labels / f"{stem}.png"
                landmark = landmarks / f"{stem}.txt"
                if label.exists() and landmark.exists():
                    selected = {"split": split, "image": image, "label": label, "landmark": landmark}
        for label_path in list(sorted(labels.glob("*.png")))[:25]:
            with Image.open(label_path) as im:
                label_values.update(im.getdata())
    selected_record = None
    if selected:
        landmark_lines = selected["landmark"].read_text(encoding="utf-8", errors="replace").splitlines()
        selected_record = {
            "split": selected["split"],
            "image": str(selected["image"]),
            "label": str(selected["label"]),
            "landmark": str(selected["landmark"]),
            "landmark_count_declared": int(float(landmark_lines[0].strip())) if landmark_lines else None,
            "landmark_preview": landmark_lines[1:6],
        }
    return {
        "dataset_root": str(dataset),
        "splits": split_records,
        "sampled_label_values": {
            str(k): {
                "label": LAPA_LABELS.get(k, "unknown"),
                "mf70_target": LAPA_TO_MF70.get(LAPA_LABELS.get(k, ""), "unmapped_reference_label"),
                "sampled_pixel_count": v,
            }
            for k, v in sorted(label_values.items())
        },
        "selected_sample": selected_record,
    }


def thumbnail(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im.thumbnail(size)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return canvas


def mask_thumb(path: Path, size: tuple[int, int], tint: tuple[int, int, int]) -> Image.Image:
    im = Image.open(path).convert("L")
    im.thumbnail(size)
    canvas = Image.new("RGBA", size, (0, 0, 0, 255))
    alpha = Image.new("L", size, 0)
    alpha.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    color = Image.new("RGBA", size, (*tint, 255))
    canvas = Image.composite(color, canvas, alpha.point(lambda v: 180 if v else 0))
    return canvas.convert("RGB")


def lapa_label_rgb(path: Path, size: tuple[int, int]) -> Image.Image:
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
    pix = rgb.load()
    vals = src.load()
    for y in range(src.height):
        for x in range(src.width):
            pix[x, y] = palette.get(vals[x, y], (120, 120, 120))
    rgb.thumbnail(size)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(rgb, ((size[0] - rgb.width) // 2, (size[1] - rgb.height) // 2))
    return canvas


def label_cell(im: Image.Image, title: str) -> Image.Image:
    font = load_font(18)
    out = Image.new("RGB", (im.width, im.height + 34), "white")
    out.paste(im, (0, 34))
    draw = ImageDraw.Draw(out)
    draw.text((8, 7), title, fill=(0, 0, 0), font=font)
    return out


def make_panel(celeba: dict, lapa: dict, out_path: Path) -> None:
    cells = []
    c_sample = celeba["selected_sample"]
    if c_sample.get("image"):
        cells.append(label_cell(thumbnail(Path(c_sample["image"]), (220, 220)), "CelebAMask image"))
        masks_by_part = {part_from_celeba_mask(Path(p)): Path(p) for p in c_sample.get("masks", [])}
        for part, tint in [
            ("skin", (55, 200, 210)),
            ("hair", (0, 140, 170)),
            ("nose", (210, 40, 60)),
            ("l_eye", (255, 220, 0)),
            ("r_eye", (255, 220, 0)),
            ("l_brow", (220, 150, 230)),
            ("r_brow", (220, 150, 230)),
            ("u_lip", (255, 90, 70)),
            ("l_lip", (160, 100, 220)),
        ]:
            p = masks_by_part.get(part)
            if p:
                cells.append(label_cell(mask_thumb(p, (220, 220), tint), f"CelebAMask {part}"))
    l_sample = lapa.get("selected_sample")
    if l_sample:
        cells.append(label_cell(thumbnail(Path(l_sample["image"]), (220, 220)), "LaPa image"))
        cells.append(label_cell(lapa_label_rgb(Path(l_sample["label"]), (220, 220)), "LaPa label map"))
    if not cells:
        return
    cols = 4
    cell_w = max(c.width for c in cells)
    cell_h = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for i, cell in enumerate(cells):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        panel.paste(cell, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S-0500")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    PANEL_DIR.mkdir(parents=True, exist_ok=True)

    celeba = collect_celeba(WAREHOUSE)
    lapa = collect_lapa(WAREHOUSE)
    panel_path = PANEL_DIR / timestamp / "masked_warehouse_facial_gold_standard_reference_panel.png"
    make_panel(celeba, lapa, panel_path)

    evidence = {
        "evidence_id": f"W70_MASKED_WAREHOUSE_FACIAL_GOLD_STANDARD_INTAKE_{timestamp}",
        "timestamp": timestamp,
        "scope": "local facial-mask gold-standard dataset intake for Wave70 facial and hair mask QA",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "warehouse_root": str(WAREHOUSE),
        "datasets": {
            "CelebAMask-HQ": celeba,
            "LaPa": lapa,
        },
        "mf70_usage_plan": {
            "facial_rows_supported": sorted(
                {
                    *[v for v in CELEBA_PARTS.values() if v.startswith("mf70_")],
                    *[v for v in LAPA_TO_MF70.values() if v.startswith("mf70_")],
                }
            ),
            "use_as": [
                "gold-standard facial part shape and neighbor-boundary examples",
                "landmark/reference masks for eyes, eyebrows, nose, lips, mouth, hair, skin, and neck QA",
                "source-derived review standard for future facial-mask repair scripts",
            ],
            "not_use_as": [
                "automatic promotion proof for current generated masks",
                "body or body-part mask authority",
                "permission to start EC2 or run generation",
            ],
        },
        "panel_path": str(panel_path),
        "panel_sha256": sha256(panel_path) if panel_path.exists() else None,
        "decision": "facial_gold_standard_datasets_indexed_for_local_mask_repair_and_review_not_promoted",
        "next_required_action": (
            "Update the active facial-mask repair/review path to compare current source facial masks "
            "against CelebAMask-HQ part masks and LaPa label/landmark references before any facial mask promotion."
        ),
    }
    out_path = OUT_DIR / f"{evidence['evidence_id']}.json"
    tracker_path = TRACKER_DIR / f"{evidence['evidence_id']}.json"
    text = json.dumps(evidence, indent=2, sort_keys=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    tracker_path.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(out_path), "tracker": str(tracker_path), "panel": str(panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
