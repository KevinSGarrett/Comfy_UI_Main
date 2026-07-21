#!/usr/bin/env python3
"""Measure deterministic container, sampled-frame, and temporal W64-AQA video gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import cv2
import jsonschema
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_video_measurement.schema.json"
EVALUATOR_VERSION = "w64-aqa-video-measure-v1"
ZERO_HASH = "0" * 64
MAX_SAMPLES = 24
DECODE_TIMEOUT_SECONDS = 300


class MeasurementError(ValueError):
    """Raised when a video or contract cannot be measured safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], timeout: int = DECODE_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise MeasurementError(f"bounded media command timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise MeasurementError(f"media tool could not start: {exc}") from exc


def _probe(path: Path) -> dict[str, Any]:
    result = _run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)])
    if result.returncode != 0:
        raise MeasurementError(f"ffprobe failed: {result.stderr.strip()[:500]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MeasurementError("ffprobe returned invalid JSON") from exc


def _full_decode(path: Path) -> None:
    result = _run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"])
    if result.returncode != 0:
        raise MeasurementError(f"full video decode failed: {result.stderr.strip()[:500]}")


def _positive_float(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise MeasurementError(f"invalid {label}") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise MeasurementError(f"invalid {label}")
    return parsed


def _frame_count(stream: dict[str, Any], duration: float, fps: float) -> int:
    for key in ("nb_read_frames", "nb_frames"):
        raw = stream.get(key)
        if raw not in (None, "N/A"):
            try:
                count = int(raw)
            except (TypeError, ValueError):
                continue
            if count > 0:
                return count
    estimate = int(round(duration * fps))
    if estimate < 1:
        raise MeasurementError("video frame count is unavailable")
    return estimate


def _sample_indices(frame_count: int) -> list[int]:
    count = min(MAX_SAMPLES, frame_count)
    return sorted({int(round(value)) for value in np.linspace(0, frame_count - 1, count)})


def _read_samples(path: Path, indices: list[int], fps: float) -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise MeasurementError("OpenCV could not open the video")
    manifest: list[dict[str, Any]] = []
    frames: list[np.ndarray] = []
    try:
        for index in indices:
            if not capture.set(cv2.CAP_PROP_POS_FRAMES, index):
                raise MeasurementError(f"could not seek to sample frame {index}")
            ok, bgr = capture.read()
            if not ok or bgr is None:
                raise MeasurementError(f"could not decode sample frame {index}")
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
            manifest.append({
                "frame_index": index,
                "timestamp_seconds": index / fps,
                "frame_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(),
                "luminance_mean": float(np.mean(gray)),
                "sharpness_laplacian_variance": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            })
            frames.append(gray)
    finally:
        capture.release()
    if len(manifest) < 2:
        raise MeasurementError("video requires at least two sampled frames")
    return manifest, frames


def _compare(observed: Any, operator: str, threshold: Any) -> bool:
    if operator == "eq":
        return observed == threshold
    if operator == "ne":
        return observed != threshold
    if operator == "lt":
        return observed < threshold
    if operator == "lte":
        return observed <= threshold
    if operator == "gt":
        return observed > threshold
    if operator == "gte":
        return observed >= threshold
    if operator == "between":
        return threshold[0] <= observed <= threshold[1]
    if operator == "contains":
        return threshold in observed
    if operator == "not_contains":
        return threshold not in observed
    raise MeasurementError(f"unsupported gate operator: {operator}")


def _validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1":
        raise MeasurementError("unsupported contract schema_version")
    if contract.get("modality") not in {"video", "av"}:
        raise MeasurementError("video measurement requires video or av modality")
    if contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise MeasurementError("contract is not ready for a lease")
    if not isinstance(contract.get("video_spec"), dict):
        raise MeasurementError("contract lacks video_spec")


def measure_video(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    _validate_contract(contract)
    if not path.is_file():
        raise MeasurementError("artifact path is not a file")
    artifact_hash = sha256_file(path)
    probe = _probe(path)
    streams = probe.get("streams", [])
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    if len(video_streams) != 1:
        raise MeasurementError("exactly one video stream is required")
    stream = video_streams[0]
    audio_present = any(item.get("codec_type") == "audio" for item in streams)
    format_info = probe.get("format", {})
    duration = _positive_float(stream.get("duration") or format_info.get("duration"), "duration")
    try:
        fps = float(Fraction(stream.get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError) as exc:
        raise MeasurementError("invalid average frame rate") from exc
    if not math.isfinite(fps) or fps <= 0:
        raise MeasurementError("invalid average frame rate")
    width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
    if width < 1 or height < 1:
        raise MeasurementError("invalid video geometry")
    frame_count = _frame_count(stream, duration, fps)
    _full_decode(path)
    manifest, frames = _read_samples(path, _sample_indices(frame_count), fps)
    motion = [float(np.mean(np.abs(frames[i] - frames[i - 1]))) for i in range(1, len(frames))]
    luma = [entry["luminance_mean"] for entry in manifest]
    luma_jumps = [abs(luma[i] - luma[i - 1]) for i in range(1, len(luma))]
    sharpness = [entry["sharpness_laplacian_variance"] for entry in manifest]
    spec = contract["video_spec"]
    expected_frames = int(round(spec["fps"] * spec["duration_seconds"]))
    metrics: dict[str, Any] = {
        "decode_success": True, "width": width, "height": height, "fps": fps,
        "duration_seconds": duration, "frame_count": frame_count,
        "fps_delta": abs(fps - spec["fps"]),
        "duration_delta_seconds": abs(duration - spec["duration_seconds"]),
        "frame_count_delta": abs(frame_count - expected_frames),
        "sample_count": len(manifest),
        "duplicate_sample_fraction": float(np.mean(np.asarray(motion) <= 0.5)),
        "sampled_motion_mean": float(np.mean(motion)), "sampled_motion_max": float(np.max(motion)),
        "sampled_luminance_jump_max": float(np.max(luma_jumps)),
        "sampled_luminance_std": float(np.std(luma)),
        "sampled_sharpness_min": float(np.min(sharpness)), "audio_stream_present": audio_present,
    }
    motion_index, exposure_index, sharp_index = int(np.argmax(motion)) + 1, int(np.argmax(luma_jumps)) + 1, int(np.argmin(sharpness))
    spans = [
        {"category": "largest_motion", "frame_start": manifest[motion_index - 1]["frame_index"], "frame_end": manifest[motion_index]["frame_index"], "severity_value": motion[motion_index - 1]},
        {"category": "largest_exposure_jump", "frame_start": manifest[exposure_index - 1]["frame_index"], "frame_end": manifest[exposure_index]["frame_index"], "severity_value": luma_jumps[exposure_index - 1]},
        {"category": "lowest_sharpness", "frame_start": manifest[sharp_index]["frame_index"], "frame_end": manifest[sharp_index]["frame_index"], "severity_value": sharpness[sharp_index]},
    ]
    frame_tolerance = max(1, int(math.ceil(spec["fps"] * 0.1)))
    implicit_gates = [
        {"gate_id": "contract-width", "metric": "width", "operator": "eq", "threshold": spec["width"], "on_failure": "REJECT"},
        {"gate_id": "contract-height", "metric": "height", "operator": "eq", "threshold": spec["height"], "on_failure": "REJECT"},
        {"gate_id": "contract-fps", "metric": "fps_delta", "operator": "lte", "threshold": 0.01, "on_failure": "REJECT"},
        {"gate_id": "contract-duration", "metric": "duration_delta_seconds", "operator": "lte", "threshold": max(0.1, 1 / spec["fps"]), "on_failure": "REJECT"},
        {"gate_id": "contract-frame-count", "metric": "frame_count_delta", "operator": "lte", "threshold": frame_tolerance, "on_failure": "REJECT"},
    ]
    gate_results, seen = [], set()
    for gate in implicit_gates + contract["quality_profile"]["hard_gates"]:
        if gate["gate_id"] in seen:
            raise MeasurementError(f"duplicate implicit/declared gate ID: {gate['gate_id']}")
        seen.add(gate["gate_id"])
        observed = metrics.get(gate["metric"])
        if gate["metric"] not in metrics:
            status, observed = "MEASUREMENT_UNAVAILABLE", None
        else:
            try:
                status = "PASS" if _compare(observed, gate["operator"], gate["threshold"]) else "FAIL"
            except (TypeError, ValueError, IndexError) as exc:
                raise MeasurementError(f"invalid threshold for gate {gate['gate_id']}") from exc
        gate_results.append({"gate_id": gate["gate_id"], "metric": gate["metric"], "status": status, "observed": observed, "operator": gate["operator"], "threshold": gate["threshold"], "on_failure": gate["on_failure"]})
    measurement = {
        "schema_version": "wave64.aqa.video_measurement.v1", "measurement_id": ZERO_HASH,
        "contract_id": contract["contract_id"], "artifact_sha256": artifact_hash,
        "evaluator_version": EVALUATOR_VERSION,
        "container": {"format_name": format_info.get("format_name") or "unknown", "duration_seconds": duration, "size_bytes": path.stat().st_size, "full_decode_pass": True},
        "video_stream": {"codec_name": stream.get("codec_name") or "unknown", "pixel_format": stream.get("pix_fmt") or "unknown", "width": width, "height": height, "fps": fps, "frame_count": frame_count},
        "audio_stream_present": audio_present, "sample_manifest": manifest,
        "metric_selected_spans": spans, "metrics": metrics, "gate_results": gate_results,
        "disposition": "PASS_DETERMINISTIC_GATES" if all(item["status"] == "PASS" for item in gate_results) else "FAIL_DETERMINISTIC_GATES",
    }
    measurement["measurement_id"] = hashlib.sha256(canonical_bytes(measurement)).hexdigest()
    jsonschema.Draft7Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))).validate(measurement)
    return measurement


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = measure_video(args.artifact, json.loads(args.contract.read_text(encoding="utf-8")))
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise MeasurementError("output already exists; measurements are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, MeasurementError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
