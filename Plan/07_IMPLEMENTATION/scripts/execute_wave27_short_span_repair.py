#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import cv2
import jsonschema
import numpy as np

LEDGER_SCHEMA = "Plan/08_SCHEMAS/wave27_frame_repair_ledger.schema.json"
MANIFEST_SCHEMA = "Plan/08_SCHEMAS/wave27_frame_manifest.schema.json"
EXECUTION_SCHEMA = "Plan/08_SCHEMAS/wave27_short_span_repair_execution.schema.json"
DEFAULT_REGISTRY = "Plan/10_REGISTRIES/wave27_short_span_repair_executor.json"


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


def _resolve_bound(path_value: str, base: Path, expected_sha: str, label: str) -> tuple[Path, bytes]:
    path = Path(path_value)
    path = path.resolve() if path.is_absolute() else (base / path).resolve()
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    raw = path.read_bytes()
    if _sha(raw) != expected_sha:
        raise ValueError(f"{label} SHA256 binding mismatch")
    return path, raw


def _registry(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    data = _parse_json(raw, "executor registry")
    expected = {
        "schema_name", "version", "algorithm", "supported_failure", "supported_actions",
        "maximum_span_frames", "opencv", "candidate_source_route", "candidate_engine_name",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("executor registry fields mismatch")
    if data.get("schema_name") != "wave27_short_span_repair_executor" or data.get("version") != 1:
        raise ValueError("unsupported executor registry")
    if data.get("algorithm") != "opencv_bidirectional_farneback_interpolation_v1":
        raise ValueError("unsupported repair algorithm")
    if data.get("supported_failure") != "isolated_flicker":
        raise ValueError("unsupported failure taxonomy")
    if data.get("supported_actions") != ["frame_local_visual_repair", "short_span_repair"]:
        raise ValueError("unsupported repair actions")
    if data.get("maximum_span_frames") != 5:
        raise ValueError("unsupported maximum span")
    opencv = data.get("opencv")
    if not isinstance(opencv, dict) or set(opencv) != {"pyr_scale", "levels", "winsize", "iterations", "poly_n", "poly_sigma", "flags", "thread_count", "rng_seed"}:
        raise ValueError("OpenCV settings mismatch")
    for key in ("pyr_scale", "poly_sigma"):
        value = opencv[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError(f"OpenCV setting {key} must be finite and positive")
    for key in ("levels", "winsize", "iterations", "poly_n"):
        if not isinstance(opencv[key], int) or isinstance(opencv[key], bool) or opencv[key] <= 0:
            raise ValueError(f"OpenCV setting {key} must be positive integer")
    if opencv["flags"] != 0 or opencv["thread_count"] != 1 or opencv["rng_seed"] != 0:
        raise ValueError("unsupported deterministic OpenCV settings")
    for key in ("candidate_source_route", "candidate_engine_name"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"registry {key} must be non-empty")
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


def _load_source_frames(manifest: dict[str, Any], manifest_path: Path) -> tuple[list[dict[str, Any]], list[bytes], list[np.ndarray], tuple[int, ...]]:
    frames = manifest["frames"]
    if [frame["frame_index"] for frame in frames] != list(range(len(frames))):
        raise ValueError("source frames must be ordered and contiguous")
    if _sequence_sha(frames) != manifest["sequence_sha256"]:
        raise ValueError("source manifest sequence SHA256 mismatch")
    raw_frames: list[bytes] = []
    images: list[np.ndarray] = []
    source_shape: tuple[int, ...] | None = None
    for frame in frames:
        path = Path(frame["artifact_path"])
        path = path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()
        if not path.is_file():
            raise ValueError(f"source frame missing: {frame['frame_index']}")
        raw = path.read_bytes()
        if len(raw) != frame["artifact_bytes"] or _sha(raw) != frame["artifact_sha256"]:
            raise ValueError(f"source frame binding failed: {frame['frame_index']}")
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"source frame is not decodable: {frame['frame_index']}")
        current = tuple(int(value) for value in image.shape)
        channels = 1 if image.ndim == 2 else int(image.shape[2])
        if image.dtype != np.uint8 or channels not in {1, 3, 4}:
            raise ValueError("source frame channel format must be uint8 grayscale, BGR, or BGRA")
        if source_shape is None:
            source_shape = current
        elif source_shape != current:
            raise ValueError("source frame dimensions or channel format differ")
        raw_frames.append(raw)
        images.append(image)
    assert source_shape is not None
    return frames, raw_frames, images, source_shape


def _validate_ledger_source(ledger: dict[str, Any], frames: list[dict[str, Any]], registry: dict[str, Any]) -> tuple[set[int], list[dict[str, Any]]]:
    if ledger.get("planning_status") != "repair_plan_pending_candidate":
        raise ValueError("ledger must be pending a candidate")
    if ledger.get("frame_count") != len(frames):
        raise ValueError("ledger frame_count mismatch")
    failed_entries = ledger.get("failed_frames", [])
    passing_entries = ledger.get("passing_frames", [])
    targets = {entry["frame_index"] for entry in failed_entries}
    passing = {entry["frame_index"] for entry in passing_entries}
    if targets | passing != set(range(len(frames))) or targets & passing:
        raise ValueError("ledger failed/passing partition mismatch")
    for entry in failed_entries + passing_entries:
        frame = frames[entry["frame_index"]]
        if entry["original_artifact_sha256"] != frame["artifact_sha256"] or entry["original_artifact_bytes"] != frame["artifact_bytes"] or entry["time_seconds"] != frame["time_seconds"]:
            raise ValueError(f"ledger frame binding mismatch: {entry['frame_index']}")
    for entry in failed_entries:
        if set(entry["failures"]) != {registry["supported_failure"]}:
            raise ValueError("executor supports isolated_flicker failures only")
    spans = ledger.get("repair_spans", [])
    covered: set[int] = set()
    for span in spans:
        indexes = span["frame_indices"]
        if indexes != list(range(span["start_frame_index"], span["end_frame_index"] + 1)) or span["span_length"] != len(indexes):
            raise ValueError("repair span is not contiguous")
        if len(indexes) > registry["maximum_span_frames"] or span["recommended_action"] not in registry["supported_actions"]:
            raise ValueError("repair span action is not executable locally")
        if set(span["failures"]) != {registry["supported_failure"]}:
            raise ValueError("repair span includes unsupported failure")
        overlap = covered.intersection(indexes)
        if overlap:
            raise ValueError(f"repair spans overlap at frames: {sorted(overlap)}")
        covered.update(indexes)
    if covered != targets:
        raise ValueError("repair spans do not exactly cover failed frames")
    return targets, spans


def _warp(image: np.ndarray, flow: np.ndarray, scale: float) -> np.ndarray:
    height, width = image.shape[:2]
    grid_x, grid_y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    map_x = grid_x - np.float32(scale) * flow[..., 0]
    map_y = grid_y - np.float32(scale) * flow[..., 1]
    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _interpolate(left: np.ndarray, right: np.ndarray, alpha: float, settings: dict[str, Any]) -> np.ndarray:
    left_gray = _to_gray(left)
    right_gray = _to_gray(right)
    args = (settings["pyr_scale"], settings["levels"], settings["winsize"], settings["iterations"], settings["poly_n"], settings["poly_sigma"], settings["flags"])
    forward = cv2.calcOpticalFlowFarneback(left_gray, right_gray, None, *args)
    backward = cv2.calcOpticalFlowFarneback(right_gray, left_gray, None, *args)
    left_mid = _warp(left, forward, alpha)
    right_mid = _warp(right, backward, 1.0 - alpha)
    return cv2.addWeighted(left_mid, 1.0 - alpha, right_mid, alpha, 0.0)


def _write_png(path: Path, image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:
        raise ValueError(f"unable to encode candidate PNG: {path.name}")
    raw = encoded.tobytes()
    path.write_bytes(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair-ledger", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--registry")
    args = parser.parse_args()
    stage: Path | None = None
    try:
        cv2.setNumThreads(1)
        cv2.setRNGSeed(0)
        root = _root(args.root)
        ledger_path = Path(args.repair_ledger).resolve()
        output_dir = Path(args.output_dir).resolve()
        if output_dir.exists():
            raise ValueError("output directory already exists")
        ledger_raw = ledger_path.read_bytes()
        ledger = _parse_json(ledger_raw, "repair ledger")
        _validate(ledger, root / LEDGER_SCHEMA, "repair ledger")
        registry_path = Path(args.registry).resolve() if args.registry else root / DEFAULT_REGISTRY
        registry, registry_sha = _registry(registry_path)
        manifest_path, manifest_raw = _resolve_bound(ledger["source_bindings"]["manifest_path"], ledger_path.parent, ledger["source_bindings"]["manifest_sha256"], "source manifest")
        manifest = _parse_json(manifest_raw, "source manifest")
        _validate(manifest, root / MANIFEST_SCHEMA, "source manifest")
        if manifest["sequence_sha256"] != ledger["source_bindings"]["manifest_sequence_sha256"]:
            raise ValueError("ledger source sequence binding mismatch")
        frames, source_raw, images, source_shape = _load_source_frames(manifest, manifest_path)
        targets, spans = _validate_ledger_source(ledger, frames, registry)
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
        frame_dir = stage / "frames"
        frame_dir.mkdir()
        candidate_frames: list[dict[str, Any]] = []
        generated: dict[int, bytes] = {}
        span_executions: list[dict[str, Any]] = []
        passing = set(range(len(frames))) - targets
        for span in spans:
            start, end = span["start_frame_index"], span["end_frame_index"]
            left_index, right_index = start - 1, end + 1
            if left_index not in passing or right_index not in passing:
                raise ValueError("repair span requires immediate passing boundaries on both sides")
            left_frame, right_frame = frames[left_index], frames[right_index]
            for field in ("shot_id", "visible_characters", "camera_state"):
                if left_frame[field] != right_frame[field]:
                    raise ValueError(f"repair boundaries differ in protected {field}")
                for interior_index in range(left_index + 1, right_index):
                    if frames[interior_index][field] != left_frame[field]:
                        raise ValueError(f"repair interior differs in protected {field} at frame {interior_index}")
            left_time, right_time = float(left_frame["time_seconds"]), float(right_frame["time_seconds"])
            if right_time <= left_time:
                raise ValueError("repair boundary timestamps are not increasing")
            weights: list[dict[str, Any]] = []
            for index in span["frame_indices"]:
                alpha = (float(frames[index]["time_seconds"]) - left_time) / (right_time - left_time)
                if not 0.0 < alpha < 1.0 or not math.isfinite(alpha):
                    raise ValueError("target timestamp is outside repair boundaries")
                repaired = _interpolate(images[left_index], images[right_index], alpha, registry["opencv"])
                path = frame_dir / f"frame_{index:06d}.png"
                raw = _write_png(path, repaired)
                if _sha(raw) == frames[index]["artifact_sha256"] and len(raw) == frames[index]["artifact_bytes"]:
                    raise ValueError(f"repair produced unchanged target frame: {index}")
                generated[index] = raw
                weights.append({"frame_index": index, "right_boundary_weight": round(alpha, 8)})
            span_executions.append({
                "start_frame_index": start, "end_frame_index": end, "span_length": span["span_length"],
                "left_boundary_frame": left_index, "right_boundary_frame": right_index,
                "failure": registry["supported_failure"], "recommended_action": span["recommended_action"],
                "target_weights": weights,
            })
        for index, source in enumerate(frames):
            path = frame_dir / f"frame_{index:06d}.png"
            raw = generated.get(index)
            if raw is None:
                raw = source_raw[index]
                path.write_bytes(raw)
            candidate = dict(source)
            candidate["artifact_path"] = f"frames/{path.name}"
            candidate["artifact_sha256"] = _sha(raw)
            candidate["artifact_bytes"] = len(raw)
            if index in targets:
                candidate["source_route"] = registry["candidate_source_route"]
                candidate["engine_name"] = registry["candidate_engine_name"]
                candidate["repair_status"] = "repaired"
            candidate_frames.append(candidate)
        candidate_manifest = {
            "schema_name": "wave27_frame_manifest", "manifest_version": manifest["manifest_version"],
            "frame_count": len(candidate_frames), "frames": candidate_frames,
            "sequence_sha256": _sequence_sha(candidate_frames),
        }
        _validate(candidate_manifest, root / MANIFEST_SCHEMA, "candidate manifest")
        candidate_path = stage / "candidate_manifest.json"
        candidate_raw = (json.dumps(candidate_manifest, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        candidate_path.write_bytes(candidate_raw)
        execution = {
            "schema_name": "wave27_short_span_repair_execution", "version": 1,
            "source_bindings": {
                "repair_ledger": {"path": _relative(ledger_path, root), "sha256": _sha(ledger_raw)},
                "source_manifest": {"path": _relative(manifest_path, root), "sha256": _sha(manifest_raw)},
            },
            "executor_registry": {"path": _relative(registry_path, root), "sha256": registry_sha, "version": registry["version"]},
            "algorithm": {"name": registry["algorithm"], "opencv_version": cv2.__version__, "thread_count": 1, "rng_seed": 0, "candidate_scope": "technical_candidate_generation_only"},
            "frame_count": len(frames),
            "image_format": {"width": int(source_shape[1]), "height": int(source_shape[0]), "channel_count": 1 if len(source_shape) == 2 else int(source_shape[2]), "dtype": "uint8"},
            "target_frame_indices": sorted(targets), "preserved_frame_indices": sorted(passing),
            "span_executions": span_executions,
            "candidate_manifest": {"path": "candidate_manifest.json", "sha256": _sha(candidate_raw)},
            "claims": {"technical_candidate_generated": True, "passing_frames_preserved": True, "identity_repair": False, "contact_deformation_repair": False, "before_after_visual_review": False, "identity_environment_visual_preservation": False, "runtime_repair_proof": False, "final_temporal_acceptance": False, "final_promotion": False},
        }
        _validate(execution, root / EXECUTION_SCHEMA, "repair execution")
        (stage / "repair_execution.json").write_text(json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        if output_dir.exists():
            raise ValueError("output directory appeared before publication")
        os.rename(stage, output_dir)
        stage = None
        print(json.dumps({"status": "pass", "output_dir": str(output_dir), "candidate_manifest": str(output_dir / "candidate_manifest.json"), "target_frames": sorted(targets)}, sort_keys=True))
        return 0
    except Exception as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
