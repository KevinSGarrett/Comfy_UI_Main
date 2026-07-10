#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFont

from wave70_model_registry import file_record, first_existing_asset


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
COMFYUI_VENV_PYTHON = PROJECT_ROOT / "ComfyUI" / ".venv" / "Scripts" / "python.exe"
WAREHOUSE = PROJECT_ROOT / "MaskedWarehouse"
CELEBA = WAREHOUSE / "CelebAMask-HQ"
CELEBA_IMAGES = CELEBA / "CelebA-HQ-img"
CELEBA_MASKS = CELEBA / "CelebAMask-HQ-mask-anno"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_FACIAL_GOLD_STANDARD_BENCHMARK_{RUN_STAMP}"
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts" / "mask_factory" / "wave70_facial_gold_standard_benchmark" / RUN_STAMP
INPUT_DIR = RUNTIME_DIR / "bisenet_input_512"
OUTPUT_DIR = RUNTIME_DIR / "bisenet_output"
PANEL_DIR = RUNTIME_DIR / "review_panels"

SAMPLE_CANDIDATES = [0, 18000, 26000, 1, 10, 100]
SAMPLE_LIMIT = 3

REGIONS: dict[str, tuple[str, ...]] = {
    "mf70_face_skin": ("skin",),
    "mf70_hair": ("hair",),
    "mf70_nose": ("nose",),
    "mf70_eyes_full": ("l_eye", "r_eye"),
    "mf70_eyebrows": ("l_brow", "r_brow"),
    "mf70_lips_top": ("u_lip",),
    "mf70_lips_bottom": ("l_lip",),
    "mf70_lips_combined": ("u_lip", "l_lip"),
    "mf70_teeth_mouth_area": ("mouth",),
    "mf70_neck": ("neck", "neck_l"),
}

PRED_BY_PART = {
    "skin": "skin",
    "hair": "hair",
    "nose": "nose",
    "l_eye": "l_eye",
    "r_eye": "r_eye",
    "l_brow": "l_brow",
    "r_brow": "r_brow",
    "u_lip": "u_lip",
    "l_lip": "l_lip",
    "mouth": "mouth",
    "neck": "neck",
    "neck_l": "neck_l",
}


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


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def mask_dir_for_sample(sample_id: int) -> Path:
    return CELEBA_MASKS / str(sample_id // 2000)


def gold_part_path(sample_id: int, part: str) -> Path:
    return mask_dir_for_sample(sample_id) / f"{sample_id:05d}_{part}.png"


def sample_has_required_parts(sample_id: int) -> bool:
    image = CELEBA_IMAGES / f"{sample_id}.jpg"
    if not image.exists():
        return False
    required = {"skin", "hair", "nose", "l_eye", "r_eye", "l_brow", "r_brow", "u_lip", "l_lip", "mouth", "neck"}
    return all(gold_part_path(sample_id, part).exists() for part in required)


def choose_samples() -> list[int]:
    selected = [sample_id for sample_id in SAMPLE_CANDIDATES if sample_has_required_parts(sample_id)]
    if len(selected) >= SAMPLE_LIMIT:
        return selected[:SAMPLE_LIMIT]
    for image in sorted(CELEBA_IMAGES.glob("*.jpg"), key=lambda p: int(p.stem)):
        sample_id = int(image.stem)
        if sample_id not in selected and sample_has_required_parts(sample_id):
            selected.append(sample_id)
        if len(selected) >= SAMPLE_LIMIT:
            break
    return selected


def binary_mask(path: Path | None, size: tuple[int, int]) -> Image.Image:
    if path is None or not path.exists():
        return Image.new("L", size, 0)
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return image.point(lambda value: 255 if value > 0 else 0)


def combine_masks(paths: list[Path], size: tuple[int, int]) -> Image.Image:
    out = Image.new("L", size, 0)
    for path in paths:
        out = ImageChops.lighter(out, binary_mask(path, size))
    return out.point(lambda value: 255 if value > 0 else 0)


def find_pred_mask(sample_stem: str, part: str) -> Path | None:
    sample_mask_dir = OUTPUT_DIR / "masks" / sample_stem
    if not sample_mask_dir.exists():
        return None
    matches = sorted(sample_mask_dir.glob(f"??_{part}.png"))
    return matches[0] if matches else None


def metrics(gold: Image.Image, pred: Image.Image) -> dict[str, Any]:
    gold_bits = [1 if value else 0 for value in gold.getdata()]
    pred_bits = [1 if value else 0 for value in pred.getdata()]
    gold_count = sum(gold_bits)
    pred_count = sum(pred_bits)
    intersection = sum(1 for g, p in zip(gold_bits, pred_bits) if g and p)
    union = sum(1 for g, p in zip(gold_bits, pred_bits) if g or p)
    false_positive = sum(1 for g, p in zip(gold_bits, pred_bits) if not g and p)
    false_negative = sum(1 for g, p in zip(gold_bits, pred_bits) if g and not p)
    dice_denominator = gold_count + pred_count
    return {
        "gold_pixels": gold_count,
        "pred_pixels": pred_count,
        "intersection_pixels": intersection,
        "union_pixels": union,
        "false_positive_pixels": false_positive,
        "false_negative_pixels": false_negative,
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / dice_denominator, 6) if dice_denominator else 1.0,
        "false_positive_ratio_vs_gold": round(false_positive / gold_count, 6) if gold_count else None,
        "false_negative_ratio_vs_gold": round(false_negative / gold_count, 6) if gold_count else None,
    }


def overlay(image: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    base = image.convert("RGBA")
    fill = Image.new("RGBA", base.size, (*color, 0))
    fill.putalpha(mask.point(lambda value: 130 if value else 0))
    return Image.alpha_composite(base, fill).convert("RGB")


def error_image(gold: Image.Image, pred: Image.Image) -> Image.Image:
    out = Image.new("RGB", gold.size, (22, 22, 22))
    pixels = out.load()
    gold_values = list(gold.getdata())
    pred_values = list(pred.getdata())
    width, _ = gold.size
    for index, (g, p) in enumerate(zip(gold_values, pred_values)):
        x = index % width
        y = index // width
        if g and p:
            pixels[x, y] = (245, 245, 245)
        elif p and not g:
            pixels[x, y] = (230, 45, 45)
        elif g and not p:
            pixels[x, y] = (40, 130, 240)
    return out


def label_tile(image: Image.Image, title: str, subtitle: str = "", size: tuple[int, int] = (210, 210)) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail(size)
    canvas = Image.new("RGB", (size[0], size[1] + 48), "white")
    canvas.paste(image, ((size[0] - image.width) // 2, 48 + (size[1] - image.height) // 2))
    draw = ImageDraw.Draw(canvas)
    font = load_font(16)
    small = load_font(12)
    draw.text((8, 6), title[:36], fill=(0, 0, 0), font=font)
    if subtitle:
        draw.text((8, 27), subtitle[:48], fill=(60, 60, 60), font=small)
    return canvas


def make_sample_panel(sample_id: int, sample_records: list[dict[str, Any]]) -> Path:
    staged_image = Image.open(INPUT_DIR / f"{sample_id:05d}.png").convert("RGB")
    cells: list[Image.Image] = [label_tile(staged_image, f"original {sample_id}", "gold source resized to 512")]
    for record in sample_records:
        region = str(record["region"])
        gold = Image.open(RUNTIME_DIR / "comparison_masks" / f"{sample_id:05d}_{region}_gold.png").convert("L")
        pred = Image.open(RUNTIME_DIR / "comparison_masks" / f"{sample_id:05d}_{region}_pred.png").convert("L")
        stats = record["metrics"]
        cells.extend(
            [
                label_tile(overlay(staged_image, gold, (0, 210, 220)), f"{region} gold", f"IoU {stats['iou']}"),
                label_tile(overlay(staged_image, pred, (255, 210, 0)), f"{region} prediction", f"Dice {stats['dice']}"),
                label_tile(error_image(gold, pred), f"{region} error", "red FP / blue FN"),
            ]
        )
    cols = 4
    cell_w = max(cell.width for cell in cells)
    cell_h = max(cell.height for cell in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for index, cell in enumerate(cells):
        panel.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = PANEL_DIR / f"{sample_id:05d}_gold_vs_bisenet_panel.png"
    panel.save(panel_path)
    return panel_path


def stage_inputs(samples: list[int]) -> list[dict[str, Any]]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for sample_id in samples:
        source = CELEBA_IMAGES / f"{sample_id}.jpg"
        staged = INPUT_DIR / f"{sample_id:05d}.png"
        image = Image.open(source).convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)
        image.save(staged)
        records.append(
            {
                "sample_id": sample_id,
                "source_image": rel(source),
                "staged_image": rel(staged),
                "source_sha256": sha256(source),
                "staged_sha256": sha256(staged),
            }
        )
    return records


def run_bisenet() -> dict[str, Any]:
    ckpt = first_existing_asset("bisenet_face_parsing_checkpoint")
    record: dict[str, Any] = {
        "route": "face_parsing.segment.evaluate",
        "python": str(COMFYUI_VENV_PYTHON),
        "checkpoint": file_record(ckpt) if ckpt else {"exists": False},
        "input_dir": rel(INPUT_DIR),
        "output_dir": rel(OUTPUT_DIR),
        "attempted": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "error": None,
    }
    if ckpt is None:
        record["error"] = "bisenet_face_parsing_checkpoint_not_found"
        return record
    if not COMFYUI_VENV_PYTHON.exists():
        record["error"] = "comfyui_venv_python_not_found"
        return record
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    code = (
        "from face_parsing.segment import evaluate\n"
        f"evaluate(r'{INPUT_DIR}', r'{OUTPUT_DIR}', r'{ckpt}', [], False, 'face-parsing-style')\n"
    )
    record["attempted"] = True
    proc = subprocess.run(
        [str(COMFYUI_VENV_PYTHON), "-c", code],
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=240,
    )
    record["returncode"] = proc.returncode
    record["stdout_tail"] = proc.stdout[-4000:]
    record["stderr_tail"] = proc.stderr[-4000:]
    if proc.returncode != 0:
        record["error"] = proc.stderr.strip() or f"exit_{proc.returncode}"
    return record


def compare_outputs(samples: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    (RUNTIME_DIR / "comparison_masks").mkdir(parents=True, exist_ok=True)
    all_records: list[dict[str, Any]] = []
    panel_records: list[dict[str, Any]] = []
    for sample_id in samples:
        sample_stem = f"{sample_id:05d}"
        sample_records: list[dict[str, Any]] = []
        for region, parts in REGIONS.items():
            gold_paths = [gold_part_path(sample_id, part) for part in parts if gold_part_path(sample_id, part).exists()]
            pred_paths = [find_pred_mask(sample_stem, PRED_BY_PART[part]) for part in parts]
            size = (512, 512)
            gold = combine_masks(gold_paths, size)
            pred = combine_masks([path for path in pred_paths if path is not None], size)
            gold_out = RUNTIME_DIR / "comparison_masks" / f"{sample_stem}_{region}_gold.png"
            pred_out = RUNTIME_DIR / "comparison_masks" / f"{sample_stem}_{region}_pred.png"
            gold.save(gold_out)
            pred.save(pred_out)
            record = {
                "sample_id": sample_id,
                "region": region,
                "gold_parts": list(parts),
                "gold_mask_paths": [rel(path) for path in gold_paths],
                "pred_mask_paths": [rel(path) for path in pred_paths if path is not None],
                "gold_comparison_mask": rel(gold_out),
                "pred_comparison_mask": rel(pred_out),
                "metrics": metrics(gold, pred),
            }
            all_records.append(record)
            sample_records.append(record)
        panel_path = make_sample_panel(sample_id, sample_records)
        panel_records.append({"sample_id": sample_id, "panel_path": rel(panel_path), "panel_sha256": sha256(panel_path)})
    return all_records, panel_records


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_region: dict[str, list[dict[str, float]]] = {}
    for record in records:
        by_region.setdefault(str(record["region"]), []).append(record["metrics"])
    region_summary = {}
    for region, values in by_region.items():
        region_summary[region] = {
            "sample_count": len(values),
            "mean_iou": round(sum(float(item["iou"]) for item in values) / len(values), 6),
            "mean_dice": round(sum(float(item["dice"]) for item in values) / len(values), 6),
            "mean_false_positive_ratio_vs_gold": round(
                sum(float(item["false_positive_ratio_vs_gold"] or 0.0) for item in values) / len(values),
                6,
            ),
            "mean_false_negative_ratio_vs_gold": round(
                sum(float(item["false_negative_ratio_vs_gold"] or 0.0) for item in values) / len(values),
                6,
            ),
        }
    return {
        "region_summary": region_summary,
        "lowest_iou_regions": sorted(
            [
                {"region": region, "mean_iou": summary["mean_iou"], "mean_dice": summary["mean_dice"]}
                for region, summary in region_summary.items()
            ],
            key=lambda item: item["mean_iou"],
        )[:5],
    }


def main() -> int:
    print(
        json.dumps(
            {
                "result": "blocked_legacy_benchmark_not_protocol_compliant",
                "replacement": "Plan/07_IMPLEMENTATION/scripts/benchmark_wave70_facial_gold_evaluator.py",
                "reason": "Legacy script predates shard-0 eligibility, neck_l separation, prediction-manifest leakage controls, and source-coordinate transform auditing.",
            },
            indent=2,
        )
    )
    return 2

    # Historical implementation retained below for evidence reproducibility only.
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    samples = choose_samples()
    staged_records = stage_inputs(samples) if samples else []
    bisenet = run_bisenet() if samples else {"attempted": False, "error": "no_gold_samples_selected"}
    comparison_records: list[dict[str, Any]] = []
    panels: list[dict[str, Any]] = []
    if bisenet.get("returncode") == 0:
        comparison_records, panels = compare_outputs(samples)

    evidence: dict[str, Any] = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local Wave70 facial gold-standard benchmark using original CelebAMask images and matching gold masks",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "runtime_dir": rel(RUNTIME_DIR),
        "warehouse_root": rel(WAREHOUSE),
        "dataset_used": "CelebAMask-HQ",
        "sample_ids": samples,
        "staged_inputs": staged_records,
        "predictor": bisenet,
        "comparison_records": comparison_records,
        "review_panels": panels,
        "summary": summarize(comparison_records) if comparison_records else {},
        "decision": (
            "gold_original_vs_gold_mask_benchmark_completed_no_promotion"
            if comparison_records
            else "gold_original_vs_gold_mask_benchmark_blocked_before_metrics"
        ),
        "finding": (
            "This is the required benchmark shape: run the same predictor on gold original images, compare to the matching gold masks, "
            "and use the resulting under-mask/over-mask evidence before applying repairs to the generated target portrait."
            if comparison_records
            else "The benchmark harness exists, but predictor execution did not produce comparable outputs."
        ),
        "next_required_action": (
            "Use the lowest-IoU region findings to choose the next facial repair; do not use hand-tuned target masks as pass evidence "
            "until this gold benchmark path is part of the gate."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "decision": evidence["decision"]}, indent=2))
    return 0 if comparison_records else 2


if __name__ == "__main__":
    raise SystemExit(main())
