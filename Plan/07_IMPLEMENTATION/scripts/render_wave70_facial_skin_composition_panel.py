#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TILE = (220, 220)


def to_abs(project_root: Path, value: str) -> Path:
    path = Path(value.replace("\\", "/"))
    return path if path.is_absolute() else project_root / path


def mask(path: Path, size: tuple[int, int]) -> Image.Image:
    return Image.open(path).convert("L").resize(size, Image.Resampling.NEAREST).point(lambda value: 255 if value else 0)


def overlay(source: Image.Image, layer: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    alpha = layer.point(lambda value: 125 if value else 0)
    return Image.composite(Image.new("RGB", source.size, color), source, alpha)


def error_overlay(source: Image.Image, gold: Image.Image, prediction: Image.Image) -> Image.Image:
    gold_pixels = np.asarray(gold) > 0
    prediction_pixels = np.asarray(prediction) > 0
    false_positive = Image.fromarray((prediction_pixels & ~gold_pixels).astype(np.uint8) * 255)
    false_negative = Image.fromarray((gold_pixels & ~prediction_pixels).astype(np.uint8) * 255)
    return overlay(overlay(source, false_positive, (230, 45, 45)), false_negative, (40, 110, 235))


def collect_samples(manifest_paths: list[Path]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for sample in manifest.get("samples", []):
            composition = sample.get("composition")
            if not isinstance(composition, dict) or composition.get("composition_rule_id") != "celeb_skin_nested_union_v1":
                raise ValueError(f"skin_composition_contract_missing:{sample.get('sample_id')}")
            samples.append(sample)
    if not samples:
        raise ValueError("skin_composition_samples_empty")
    return samples


def render(project_root: Path, samples: list[dict[str, Any]], out_path: Path) -> None:
    header_height = 68
    row_height = TILE[1] + 34
    panel = Image.new("RGB", (TILE[0] * 5, header_height + row_height * len(samples)), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((8, 8), "Skin composition QA: red=false positive, blue=false negative", fill="black", font=font)
    draw.text((8, 28), "Columns: original | base argmax skin | composed skin | gold skin | composed error", fill="black", font=font)
    draw.text((8, 48), "Rule: skin union l/r brows, l/r eyes, nose, mouth, upper lip, lower lip", fill="black", font=font)
    gold_root = project_root / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    y = header_height
    for sample in samples:
        sample_id = str(sample["sample_id"])
        source = Image.open(to_abs(project_root, str(sample["source_path"]))).convert("RGB").resize(TILE, Image.Resampling.LANCZOS)
        base = mask(to_abs(project_root, str(sample["composition"]["base_prediction_path"])) / "skin.png", TILE)
        composed = mask(to_abs(project_root, str(sample["prediction_path"])) / "skin.png", TILE)
        gold = mask(gold_root / f"{int(sample_id):05d}_skin.png", TILE)
        views = (
            source,
            overlay(source, base, (35, 190, 90)),
            overlay(source, composed, (235, 170, 25)),
            overlay(source, gold, (35, 190, 90)),
            error_overlay(source, gold, composed),
        )
        for column, view in enumerate(views):
            panel.paste(view, (column * TILE[0], y))
        draw.text((8, y + TILE[1] + 8), f"Celeb ID {sample_id}", fill="black", font=font)
        y += row_height
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render QA for derived overlapping skin masks.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifests", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    samples = collect_samples([Path(value).resolve() for value in args.manifests])
    out_path = Path(args.out).resolve()
    render(project_root, samples, out_path)
    print(json.dumps({"result": "pass_skin_composition_panel", "sample_ids": [sample["sample_id"] for sample in samples], "out": str(out_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
