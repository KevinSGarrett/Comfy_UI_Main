#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
from PIL import Image, UnidentifiedImageError

MANIFEST_SCHEMA = "Plan/08_SCHEMAS/wave27_frame_manifest.schema.json"
TEMPORAL_SCHEMA = "Plan/08_SCHEMAS/wave27_temporal_evidence.schema.json"
EXPORT_SCHEMA = "Plan/08_SCHEMAS/wave26_deterministic_gif_export.schema.json"
LOOP_PROFILES = "Plan/10_REGISTRIES/wave26_gif_loop_profile_registry.json"
DEFAULT_REGISTRY = "Plan/10_REGISTRIES/wave26_deterministic_gif_exporter.json"


def _reject_nonfinite(token: str) -> Any:
    raise ValueError(f"non-finite JSON token is not allowed: {token}")


def _parse_json(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_nonfinite)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _root(value: str) -> Path:
    path = Path(value).resolve()
    if (path / "Plan").is_dir():
        return path
    if path.name == "Plan" and (path / "08_SCHEMAS").is_dir():
        return path.parent
    raise ValueError(f"unable to resolve repository root from {value}")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _validate(instance: Any, schema_path: Path, label: str) -> None:
    schema = _parse_json(schema_path.read_bytes(), f"{label} schema")
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "root"
        raise ValueError(f"{label} schema validation failed at {location}: {error.message}")


def _registry(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    data = _parse_json(raw, "GIF exporter registry")
    expected = {
        "schema_name", "version", "algorithm", "palette_colors", "transparency_index",
        "alpha_threshold", "dither", "optimize", "disposal", "loop_count",
        "minimum_frame_duration_ms", "palette_sample_edge", "last_frame_duration_policy",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("GIF exporter registry fields mismatch")
    fixed = {
        "schema_name": "wave26_deterministic_gif_exporter", "version": 1,
        "algorithm": "pillow_global_palette_gif89a_v1", "palette_colors": 255,
        "transparency_index": 255, "dither": "none", "optimize": False,
        "disposal": 2, "loop_count": 0, "last_frame_duration_policy": "repeat_first_duration",
        "minimum_frame_duration_ms": 10,
    }
    for key, value in fixed.items():
        if data.get(key) != value:
            raise ValueError(f"unsupported GIF exporter registry value: {key}")
    for key in ("alpha_threshold", "palette_sample_edge"):
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"registry {key} must be positive integer")
    if data["alpha_threshold"] > 255 or data["palette_sample_edge"] > 1024:
        raise ValueError("GIF exporter registry value exceeds limit")
    return data, _sha(raw)


def _sequence_sha(frames: list[dict[str, Any]]) -> str:
    payload = [
        {
            "frame_index": frame["frame_index"], "time_seconds": float(frame["time_seconds"]),
            "artifact_path": frame["artifact_path"], "artifact_sha256": frame["artifact_sha256"],
            "artifact_bytes": frame["artifact_bytes"],
        }
        for frame in frames
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _quantize_gif_durations(durations: list[int], minimum_duration_ms: int) -> list[int]:
    """Map millisecond timing to GIF centiseconds while preserving cumulative cadence."""
    quantum_ms = 10
    quantized: list[int] = []
    source_cumulative = 0
    encoded_cumulative = 0
    for duration in durations:
        source_cumulative += duration
        target_cumulative = ((source_cumulative + (quantum_ms // 2)) // quantum_ms) * quantum_ms
        encoded_duration = target_cumulative - encoded_cumulative
        if encoded_duration < minimum_duration_ms:
            encoded_duration = minimum_duration_ms
            target_cumulative = encoded_cumulative + encoded_duration
        quantized.append(encoded_duration)
        encoded_cumulative = target_cumulative
    return quantized


def _load_frames(manifest: dict[str, Any], manifest_path: Path, minimum_duration_ms: int) -> tuple[list[Image.Image], list[int], int, int]:
    frames = sorted(manifest["frames"], key=lambda frame: frame["frame_index"])
    if [frame["frame_index"] for frame in frames] != list(range(len(frames))) or _sequence_sha(frames) != manifest["sequence_sha256"]:
        raise ValueError("manifest sequence binding failed")
    images: list[Image.Image] = []
    width = height = 0
    previous_time: float | None = None
    times: list[float] = []
    for frame in frames:
        timestamp = float(frame["time_seconds"])
        if not math.isfinite(timestamp) or (previous_time is not None and timestamp <= previous_time):
            raise ValueError("manifest frame times must be finite and strictly increasing")
        previous_time = timestamp
        times.append(timestamp)
        path = Path(frame["artifact_path"])
        path = path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()
        if not path.is_file():
            raise ValueError(f"source frame missing: {frame['frame_index']}")
        raw = path.read_bytes()
        if len(raw) != frame["artifact_bytes"] or _sha(raw) != frame["artifact_sha256"]:
            raise ValueError(f"source frame binding failed: {frame['frame_index']}")
        try:
            with Image.open(io.BytesIO(raw)) as source:
                source.load()
                image = source.convert("RGBA")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(f"source frame cannot be decoded: {frame['frame_index']}") from exc
        if not images:
            width, height = image.size
        elif image.size != (width, height):
            raise ValueError("source frame dimensions differ")
        images.append(image)
    if len(times) == 1:
        durations = [100]
    else:
        durations = []
        for index in range(1, len(times)):
            duration = int(round((times[index] - times[index - 1]) * 1000.0))
            if duration < minimum_duration_ms:
                raise ValueError(f"manifest frame duration must be at least {minimum_duration_ms}ms for GIF timing")
            durations.append(duration)
        durations.append(durations[0])
    return images, _quantize_gif_durations(durations, minimum_duration_ms), width, height


def _global_palette(images: list[Image.Image], sample_edge: int, colors: int) -> Image.Image:
    samples: list[Image.Image] = []
    for image in images:
        sample = image.convert("RGB")
        sample.thumbnail((sample_edge, sample_edge), Image.Resampling.LANCZOS)
        samples.append(sample)
    width = sum(image.width for image in samples)
    height = max(image.height for image in samples)
    composite = Image.new("RGB", (width, height), (0, 0, 0))
    offset = 0
    for sample in samples:
        composite.paste(sample, (offset, 0))
        offset += sample.width
    return composite.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def _quantize_frames(images: list[Image.Image], palette: Image.Image, alpha_threshold: int, transparency_index: int) -> list[Image.Image]:
    palette_data = list(palette.getpalette() or [])[:768]
    palette_data.extend([0] * (768 - len(palette_data)))
    palette_data[transparency_index * 3 : transparency_index * 3 + 3] = [0, 0, 0]
    palette_rgb = np.asarray(palette_data, dtype=np.int32).reshape(256, 3)[:transparency_index]
    output: list[Image.Image] = []
    for image in images:
        quantized = image.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
        quantized.putpalette(palette_data)
        alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
        source_rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        indexes = np.asarray(quantized, dtype=np.uint8).copy()
        collision = (alpha >= alpha_threshold) & (indexes == transparency_index)
        if np.any(collision):
            for color in np.unique(source_rgb[collision].reshape(-1, 3), axis=0):
                color_mask = collision & np.all(source_rgb == color, axis=2)
                distances = np.sum((palette_rgb - color.astype(np.int32)) ** 2, axis=1)
                indexes[color_mask] = np.uint8(int(np.argmin(distances)))
        indexes[alpha < alpha_threshold] = transparency_index
        result = Image.fromarray(indexes, mode="P")
        result.putpalette(palette_data)
        result.info["transparency"] = transparency_index
        output.append(result)
    return output


def _seam(images: list[Image.Image]) -> float:
    first = np.asarray(images[0], dtype=np.int16)
    last = np.asarray(images[-1], dtype=np.int16)
    return round(float(np.mean(np.abs(first - last))) / 255.0, 8)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--temporal-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--registry")
    args = parser.parse_args()
    stage: Path | None = None
    try:
        root = _root(args.root)
        manifest_path = Path(args.manifest).resolve()
        temporal_path = Path(args.temporal_evidence).resolve()
        output_dir = Path(args.output_dir).resolve()
        if output_dir.exists():
            raise ValueError("output directory already exists")
        manifest_raw, temporal_raw = manifest_path.read_bytes(), temporal_path.read_bytes()
        manifest = _parse_json(manifest_raw, "frame manifest")
        temporal = _parse_json(temporal_raw, "temporal evidence")
        _validate(manifest, root / MANIFEST_SCHEMA, "frame manifest")
        _validate(temporal, root / TEMPORAL_SCHEMA, "temporal evidence")
        if temporal["frame_count"] != manifest["frame_count"]:
            raise ValueError("temporal evidence frame_count mismatch")
        profile_registry = _parse_json((root / LOOP_PROFILES).read_bytes(), "loop profile registry")
        profile_ids = {entry["id"] for entry in profile_registry.get("profiles", []) if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
        loop_profile = temporal["loop_profile"]
        if loop_profile not in profile_ids:
            raise ValueError("unknown loop profile")
        registry_path = Path(args.registry).resolve() if args.registry else root / DEFAULT_REGISTRY
        registry, registry_sha = _registry(registry_path)
        images, durations, width, height = _load_frames(manifest, manifest_path, registry["minimum_frame_duration_ms"])
        palette = _global_palette(images, registry["palette_sample_edge"], registry["palette_colors"])
        frames = _quantize_frames(images, palette, registry["alpha_threshold"], registry["transparency_index"])
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
        gif_path = stage / "candidate.gif"
        frames[0].save(
            gif_path, format="GIF", save_all=True, append_images=frames[1:], duration=durations,
            loop=registry["loop_count"], optimize=registry["optimize"], disposal=registry["disposal"],
            transparency=registry["transparency_index"],
        )
        gif_raw = gif_path.read_bytes()
        if gif_raw[:6] not in {b"GIF87a", b"GIF89a"}:
            raise ValueError("Pillow export did not produce GIF container")
        export = {
            "schema_name": "wave26_deterministic_gif_export", "version": 1,
            "source_bindings": {
                "frame_manifest": {"path": _relative(manifest_path, root), "sha256": _sha(manifest_raw)},
                "temporal_evidence": {"path": _relative(temporal_path, root), "sha256": _sha(temporal_raw)},
            },
            "exporter_registry": {"path": _relative(registry_path, root), "sha256": registry_sha, "version": registry["version"]},
            "algorithm": {"name": registry["algorithm"], "pillow_version": metadata.version("Pillow"), "palette_colors": registry["palette_colors"], "transparency_index": registry["transparency_index"], "alpha_threshold": registry["alpha_threshold"], "minimum_frame_duration_ms": registry["minimum_frame_duration_ms"], "dither": registry["dither"], "optimize": registry["optimize"], "disposal": registry["disposal"], "candidate_scope": "technical_gif_export_only"},
            "loop_profile": loop_profile, "frame_count": len(frames), "dimensions": {"width": width, "height": height},
            "frame_durations_ms": durations, "loop_count": registry["loop_count"],
            "candidate_gif": {"path": "candidate.gif", "sha256": _sha(gif_raw), "bytes": len(gif_raw), "container_header": gif_raw[:6].decode("ascii")},
            "technical_seam": {"metric_name": "source_first_last_rgba_mean_absolute_difference_normalized", "source_rgba_mean_absolute_difference_normalized": _seam(images), "visual_pass_claimed": False},
            "claims": {"technical_gif_export_generated": True, "manifest_timing_applied": True, "runtime_generation_proof": False, "production_candidate": False, "loop_playback_visual_review": False, "identity_no_popping_visual_pass": False, "contact_deformation_visual_pass": False, "final_export_certification": False, "final_promotion": False},
        }
        _validate(export, root / EXPORT_SCHEMA, "GIF export")
        (stage / "export_manifest.json").write_text(json.dumps(export, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        if output_dir.exists():
            raise ValueError("output directory appeared before publication")
        os.rename(stage, output_dir)
        stage = None
        print(json.dumps({"status": "pass", "output_dir": str(output_dir), "candidate_gif": str(output_dir / "candidate.gif"), "frame_count": len(frames)}, sort_keys=True))
        return 0
    except Exception as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
