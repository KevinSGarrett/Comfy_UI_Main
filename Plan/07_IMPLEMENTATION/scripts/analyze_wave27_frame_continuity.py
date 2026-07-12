#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import cv2
import jsonschema
import numpy as np

DEFAULT_THRESHOLDS = "Plan/10_REGISTRIES/wave27_frame_continuity_thresholds.json"
MANIFEST_SCHEMA = "Plan/08_SCHEMAS/wave27_frame_manifest.schema.json"
METRICS_SCHEMA = "Plan/08_SCHEMAS/wave27_frame_continuity_metrics.schema.json"


def _reject_nonfinite(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root(path: Path) -> Path:
    resolved = path.resolve()
    if (resolved / "Plan").is_dir():
        return resolved
    if resolved.name == "Plan" and (resolved / "08_SCHEMAS").is_dir():
        return resolved.parent
    raise ValueError(f"unable to resolve repository root from {path}")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _validate(instance: Any, schema_path: Path) -> None:
    validator = jsonschema.Draft202012Validator(_load_json(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "root"
        raise ValueError(f"schema validation failed at {location}: {first.message}")


def _sequence_sha(frames: list[dict[str, Any]]) -> str:
    payload = [
        {
            "frame_index": item["frame_index"],
            "time_seconds": float(item["time_seconds"]),
            "artifact_path": item["artifact_path"],
            "artifact_sha256": item["artifact_sha256"],
            "artifact_bytes": item["artifact_bytes"],
        }
        for item in frames
    ]
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _frame_path(manifest_path: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (manifest_path.parent / candidate).resolve()


def _number(src: dict[str, Any], key: str, low: float, high: float | None = None) -> float:
    value = src.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"threshold {key} must be finite numeric")
    result = float(value)
    if result < low or (high is not None and result > high):
        raise ValueError(f"threshold {key} outside [{low}, {high}]")
    return result


def _load_thresholds(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict) or data.get("schema_name") != "wave27_frame_continuity_thresholds":
        raise ValueError("threshold registry schema_name mismatch")
    expected = {
        "schema_name", "version", "algorithm", "rounding_digits", "minimum_frame_count",
        "static_camera_declaration", "border_fraction", "motion_analysis",
        "object_background_camera_analysis",
    }
    if set(data) != expected:
        raise ValueError("threshold registry fields mismatch")
    if data.get("version") != 1 or data.get("minimum_frame_count") != 2:
        raise ValueError("unsupported threshold registry version or minimum_frame_count")
    if data.get("algorithm") != "opencv_phase_correlation_farneback_v1":
        raise ValueError("unsupported threshold algorithm")
    digits = data.get("rounding_digits")
    if not isinstance(digits, int) or isinstance(digits, bool) or not 0 <= digits <= 12:
        raise ValueError("rounding_digits must be integer in [0, 12]")
    declaration = data.get("static_camera_declaration")
    if declaration != {"field": "temporal_motion_mode", "value": "static"}:
        raise ValueError("unsupported static camera declaration")
    _number(data, "border_fraction", 0.01, 0.49)
    motion = data.get("motion_analysis")
    camera = data.get("object_background_camera_analysis")
    if not isinstance(motion, dict) or not isinstance(camera, dict):
        raise ValueError("threshold groups must be objects")
    _number(motion, "max_adjacent_luma_mae_percent", 0.0, 100.0)
    _number(motion, "max_flow_p95_diagonal_ratio", 0.0, 10.0)
    _number(camera, "minimum_phase_response", 0.0, 1.0)
    _number(camera, "max_camera_shift_diagonal_ratio", 0.0, 10.0)
    _number(camera, "max_aligned_border_residual_percent", 0.0, 100.0)
    return data


def _load_frames(manifest: dict[str, Any], manifest_path: Path) -> tuple[list[np.ndarray], int, int]:
    frames = manifest["frames"]
    if len(frames) < 2:
        raise ValueError("frame_count must be at least 2 for adjacency analysis")
    if [item["frame_index"] for item in frames] != list(range(len(frames))):
        raise ValueError("frames must be ordered and contiguous from zero")
    if _sequence_sha(frames) != manifest["sequence_sha256"]:
        raise ValueError("manifest sequence_sha256 mismatch")
    loaded: list[np.ndarray] = []
    dimensions: tuple[int, int] | None = None
    for item in frames:
        path = _frame_path(manifest_path, item["artifact_path"])
        if not path.is_file() or path.stat().st_size != item["artifact_bytes"] or _sha256(path) != item["artifact_sha256"]:
            raise ValueError(f"frame artifact binding failed: {item['frame_index']}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"frame cannot be decoded: {item['frame_index']}")
        current = (int(image.shape[1]), int(image.shape[0]))
        if dimensions is None:
            dimensions = current
        elif current != dimensions:
            raise ValueError("frame dimensions must match")
        loaded.append(image)
    assert dimensions is not None
    return loaded, dimensions[0], dimensions[1]


def _round(value: float, digits: int) -> float:
    if not math.isfinite(value):
        raise ValueError("analysis produced non-finite metric")
    return round(float(value), digits)


def _pair_metrics(previous: np.ndarray, current: np.ndarray, diagonal: float, border_fraction: float, digits: int) -> dict[str, float | bool]:
    prev_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY).astype(np.float32)
    curr_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY).astype(np.float32)
    shift, response = cv2.phaseCorrelate(prev_gray, curr_gray)
    dx, dy = float(shift[0]), float(shift[1])
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray.astype(np.uint8), curr_gray.astype(np.uint8), None,
        0.5, 3, 15, 3, 5, 1.2, 0,
    )
    magnitudes = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    aligned = cv2.warpAffine(previous, matrix, (previous.shape[1], previous.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    residual = cv2.cvtColor(cv2.absdiff(aligned, current), cv2.COLOR_BGR2GRAY)
    h, w = residual.shape
    margin = max(1, int(round(min(w, h) * border_fraction)))
    mask = np.zeros((h, w), dtype=bool)
    mask[:margin, :] = True
    mask[-margin:, :] = True
    mask[:, :margin] = True
    mask[:, -margin:] = True
    values = {
        "luma_mae_percent": float(np.mean(np.abs(curr_gray - prev_gray)) / 255.0 * 100.0),
        "phase_response": max(0.0, float(response)),
        "camera_shift_x_diagonal_ratio": dx / diagonal,
        "camera_shift_y_diagonal_ratio": dy / diagonal,
        "camera_shift_diagonal_ratio": math.hypot(dx, dy) / diagonal,
        "flow_median_diagonal_ratio": float(np.median(magnitudes)) / diagonal,
        "flow_p95_diagonal_ratio": float(np.percentile(magnitudes, 95)) / diagonal,
        "aligned_border_residual_percent": float(np.mean(residual[mask]) / 255.0 * 100.0),
    }
    rounded = {key: _round(value, digits) for key, value in values.items()}
    return {**rounded, "finite": True}


def _decision(failures: list[str]) -> dict[str, Any]:
    return {"result": "fail" if failures else "pass", "failures": sorted(set(failures))}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--thresholds")
    args = parser.parse_args()
    temp_dir: Path | None = None
    try:
        root = _root(Path(args.root))
        cv2.setNumThreads(1)
        cv2.setRNGSeed(0)
        manifest_path = Path(args.manifest).resolve()
        output_dir = Path(args.output_dir).resolve()
        if output_dir.exists():
            raise ValueError("output directory already exists")
        threshold_path = Path(args.thresholds).resolve() if args.thresholds else root / DEFAULT_THRESHOLDS
        thresholds = _load_thresholds(threshold_path)
        manifest = _load_json(manifest_path)
        _validate(manifest, root / MANIFEST_SCHEMA)
        images, width, height = _load_frames(manifest, manifest_path)
        digits = int(thresholds["rounding_digits"])
        diagonal = math.hypot(width, height)
        pairs: list[dict[str, Any]] = []
        for index in range(1, len(images)):
            metrics = _pair_metrics(images[index - 1], images[index], diagonal, float(thresholds["border_fraction"]), digits)
            pairs.append({
                "from_frame": index - 1,
                "to_frame": index,
                "elapsed_seconds": _round(float(manifest["frames"][index]["time_seconds"]) - float(manifest["frames"][index - 1]["time_seconds"]), digits),
                **metrics,
            })
        aggregate = {
            "max_luma_mae_percent": max(item["luma_mae_percent"] for item in pairs),
            "min_phase_response": min(item["phase_response"] for item in pairs),
            "max_camera_shift_diagonal_ratio": max(item["camera_shift_diagonal_ratio"] for item in pairs),
            "max_flow_p95_diagonal_ratio": max(item["flow_p95_diagonal_ratio"] for item in pairs),
            "max_aligned_border_residual_percent": max(item["aligned_border_residual_percent"] for item in pairs),
        }
        motion_limits = thresholds["motion_analysis"]
        camera_limits = thresholds["object_background_camera_analysis"]
        motion_failures: list[str] = []
        if aggregate["max_luma_mae_percent"] > motion_limits["max_adjacent_luma_mae_percent"]:
            motion_failures.append("adjacent_luma_change_above_limit")
        if aggregate["max_flow_p95_diagonal_ratio"] > motion_limits["max_flow_p95_diagonal_ratio"]:
            motion_failures.append("optical_flow_above_limit")
        declaration = thresholds["static_camera_declaration"]
        all_static = all(frame["camera_state"].get(declaration["field"]) == declaration["value"] for frame in manifest["frames"])
        camera_failures: list[str] = []
        if not all_static:
            camera_failures.append("validated_static_camera_declaration_missing_or_planned_motion_unsupported")
        if aggregate["min_phase_response"] < camera_limits["minimum_phase_response"]:
            camera_failures.append("phase_correlation_confidence_below_limit")
        if aggregate["max_camera_shift_diagonal_ratio"] > camera_limits["max_camera_shift_diagonal_ratio"]:
            camera_failures.append("camera_shift_above_static_limit")
        if aggregate["max_aligned_border_residual_percent"] > camera_limits["max_aligned_border_residual_percent"]:
            camera_failures.append("aligned_border_residual_above_limit")
        decisions = {
            "motion_analysis": _decision(motion_failures),
            "object_background_camera_analysis": _decision(camera_failures),
        }
        metrics = {
            "schema_name": "wave27_frame_continuity_metrics",
            "version": 1,
            "sequence_sha256": manifest["sequence_sha256"],
            "manifest": {"path": _relative(manifest_path, root), "sha256": _sha256(manifest_path)},
            "threshold_registry": {"path": _relative(threshold_path, root), "sha256": _sha256(threshold_path), "version": thresholds["version"]},
            "analyzer": {"algorithm": thresholds["algorithm"], "opencv_version": cv2.__version__, "thread_count": 1, "rng_seed": 0, "rounding_digits": digits},
            "frame_count": len(images),
            "image_dimensions": {"width": width, "height": height},
            "camera_intent_policy": {"required_field": declaration["field"], "required_value": declaration["value"], "all_frames_declared_static": all_static, "planned_motion_supported": False},
            "pair_metrics": pairs,
            "aggregate_metrics": aggregate,
            "decisions": decisions,
            "non_claims": {key: False for key in ("identity", "face", "body", "hands", "contact", "audio", "flicker_score_authority", "runtime_generation", "final_visual_acceptance", "promotion")},
        }
        _validate(metrics, root / METRICS_SCHEMA)
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
        metrics_path = temp_dir / "temporal_continuity_metrics.json"
        _write_json(metrics_path, metrics)
        metrics_sha = _sha256(metrics_path)
        for category in ("motion_analysis", "object_background_camera_analysis"):
            outcome = decisions[category]
            notes = f"deterministic frame-continuity measurement only; metrics=temporal_continuity_metrics.json; metrics_sha256={metrics_sha}; failures={','.join(outcome['failures']) or 'none'}"
            _write_json(temp_dir / f"{category}.json", {"evidence_type": category, "sequence_sha256": manifest["sequence_sha256"], "result": outcome["result"], "notes": notes})
        temp_dir.rename(output_dir)
        temp_dir = None
        print(json.dumps({"status": "pass", "output_dir": str(output_dir), "decisions": decisions}, sort_keys=True))
        return 0
    except Exception as exc:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
