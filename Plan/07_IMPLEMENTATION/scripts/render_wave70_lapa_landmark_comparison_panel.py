#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_gold_points(path: Path) -> list[tuple[float, float]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    count = int(lines[0])
    points = [tuple(float(value) for value in line.split()) for line in lines[1:]]
    if len(points) != count:
        raise ValueError(f"gold_point_count_mismatch:{path}")
    return points


def load_predicted_points(path: Path) -> list[tuple[float, float]]:
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"prediction_points_not_list:{path}")
    points = [tuple(float(value) for value in point) for point in payload]
    if len(points) != 106 or any(len(point) != 2 for point in payload):
        raise ValueError(f"prediction_point_count_invalid:{path}")
    return points


def draw_points(image: Image.Image, points: list[tuple[float, float]], color: tuple[int, int, int]) -> Image.Image:
    output = image.copy()
    draw = ImageDraw.Draw(output)
    radius = max(2, round(min(image.size) / 250))
    for index, (x, y) in enumerate(points):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=(0, 0, 0))
        if index in {35, 39, 89, 93}:
            draw.text((x + radius + 1, y - radius - 1), str(index), fill=color, stroke_width=1, stroke_fill=(0, 0, 0))
    return output


def draw_comparison(
    image: Image.Image, gold: list[tuple[float, float]], predicted: list[tuple[float, float]]
) -> Image.Image:
    output = image.copy()
    draw = ImageDraw.Draw(output)
    radius = max(2, round(min(image.size) / 250))
    for gold_point, predicted_point in zip(gold, predicted):
        draw.line((gold_point[0], gold_point[1], predicted_point[0], predicted_point[1]), fill=(255, 220, 0), width=1)
        draw.ellipse(
            (gold_point[0] - radius, gold_point[1] - radius, gold_point[0] + radius, gold_point[1] + radius),
            fill=(0, 255, 120),
        )
        draw.ellipse(
            (
                predicted_point[0] - radius,
                predicted_point[1] - radius,
                predicted_point[0] + radius,
                predicted_point[1] + radius,
            ),
            fill=(255, 60, 200),
        )
    return output


def render_panel(project_root: Path, manifest_path: Path, out_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    producer = manifest.get("producer_contract", {})
    if producer.get("originals_only") is not True or producer.get("gold_paths_exposed_to_route") is not False:
        raise ValueError("manifest_not_originals_only")
    split = str(manifest.get("split", ""))
    if split not in {"train", "val", "test"}:
        raise ValueError("manifest_split_invalid")
    samples = manifest.get("samples", [])
    if not samples:
        raise ValueError("manifest_samples_missing")

    thumb_size = (360, 360)
    header_height = 78
    label_height = 26
    panel = Image.new("RGB", (thumb_size[0] * 4, header_height + len(samples) * (thumb_size[1] + label_height)), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((10, 8), "LaPa originals-only InsightFace 106 landmark comparison", fill="black", font=font)
    draw.text((10, 28), "green=LaPa evaluator gold; magenta=InsightFace prediction; yellow=paired index displacement", fill="black", font=font)
    draw.text((10, 48), "Gold points are loaded only by this QA renderer after prediction hashes exist.", fill="black", font=font)
    headings = ("source", "gold 106", "predicted 106", "same-index comparison")
    for column, heading in enumerate(headings):
        draw.text((column * thumb_size[0] + 8, header_height - 18), heading, fill="black", font=font)

    sample_records = []
    for row, sample in enumerate(samples):
        source = resolve_path(project_root, sample["source_path"])
        prediction = resolve_path(project_root, sample["prediction_landmarks_path"])
        gold_path = project_root / "MaskedWarehouse" / "LaPa" / split / "landmarks" / f"{sample['sample_id']}.txt"
        if sha256_file(prediction) != sample["prediction_landmarks_sha256"]:
            raise ValueError(f"prediction_hash_mismatch:{sample['sample_id']}")
        source_image = Image.open(source).convert("RGB")
        gold = load_gold_points(gold_path)
        predicted = load_predicted_points(prediction)
        cells = (
            source_image,
            draw_points(source_image, gold, (0, 255, 120)),
            draw_points(source_image, predicted, (255, 60, 200)),
            draw_comparison(source_image, gold, predicted),
        )
        y = header_height + row * (thumb_size[1] + label_height)
        for column, cell in enumerate(cells):
            fitted = cell.copy()
            fitted.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", thumb_size, (245, 245, 245))
            offset = ((thumb_size[0] - fitted.width) // 2, (thumb_size[1] - fitted.height) // 2)
            canvas.paste(fitted, offset)
            panel.paste(canvas, (column * thumb_size[0], y))
        draw.text((8, y + thumb_size[1] + 5), str(sample["sample_id"]), fill="black", font=font)
        sample_records.append(
            {
                "sample_id": sample["sample_id"],
                "source_sha256": sha256_file(source),
                "prediction_sha256": sha256_file(prediction),
                "gold_landmark_sha256": sha256_file(gold_path),
                "point_count": len(predicted),
            }
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)
    return {
        "result": "lapa_landmark_comparison_panel_rendered",
        "panel": str(out_path),
        "panel_sha256": sha256_file(out_path),
        "prediction_manifest": str(manifest_path),
        "prediction_manifest_sha256": sha256_file(manifest_path),
        "samples": sample_records,
        "model_route_executed": manifest.get("route_execution", {}).get("model_route_executed") is True,
        "gold_exposed_to_producer": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render LaPa gold versus predicted landmark QA panel.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--prediction-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--record-out", required=True)
    args = parser.parse_args()
    record = render_panel(
        Path(args.project_root).resolve(), Path(args.prediction_manifest).resolve(), Path(args.out).resolve()
    )
    record_out = Path(args.record_out).resolve()
    record_out.parent.mkdir(parents=True, exist_ok=True)
    record_out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
