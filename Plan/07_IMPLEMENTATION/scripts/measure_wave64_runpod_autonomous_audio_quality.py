#!/usr/bin/env python3
"""Measure fail-closed deterministic W64-AQA audio and container-level AV gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_audio_measurement.schema.json"
EVALUATOR_VERSION = "w64-aqa-audio-measure-v1"
ZERO_HASH = "0" * 64
DECODE_TIMEOUT_SECONDS = 300
MAX_DECODED_BYTES = 512 * 1024 * 1024
SILENCE_DBFS = -60.0
FRAME_MILLISECONDS = 20
SEGMENT_MILLISECONDS = 100
EPSILON = 1e-12


class MeasurementError(ValueError):
    """Raised when an audio artifact or contract cannot be measured safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_text(command: list[str], timeout: int = DECODE_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise MeasurementError(f"bounded media command timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise MeasurementError(f"media tool could not start: {exc}") from exc


def _run_bytes(command: list[str], timeout: int = DECODE_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(command, check=False, capture_output=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise MeasurementError(f"bounded media command timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise MeasurementError(f"media tool could not start: {exc}") from exc


def _probe(path: Path) -> dict[str, Any]:
    result = _run_text(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    if result.returncode != 0:
        raise MeasurementError(f"ffprobe failed: {result.stderr.strip()[:500]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MeasurementError("ffprobe returned invalid JSON") from exc


def _finite_float(value: Any, label: str, *, positive: bool = False) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise MeasurementError(f"invalid {label}") from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise MeasurementError(f"invalid {label}")
    return parsed


def _decode_pcm(path: Path, sample_rate: int, channels: int, duration: float) -> np.ndarray:
    estimated_bytes = math.ceil(sample_rate * channels * duration * 4 * 1.02)
    if estimated_bytes > MAX_DECODED_BYTES:
        raise MeasurementError(
            f"decoded PCM estimate {estimated_bytes} exceeds bounded limit {MAX_DECODED_BYTES}"
        )
    result = _run_bytes([
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
        "-f", "f32le", "-acodec", "pcm_f32le", "-",
    ])
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:500]
        raise MeasurementError(f"full audio decode failed: {detail}")
    if len(result.stdout) > MAX_DECODED_BYTES:
        raise MeasurementError("decoded PCM exceeded bounded limit")
    stride = channels * 4
    if not result.stdout or len(result.stdout) % stride:
        raise MeasurementError("decoded PCM is empty or channel alignment is invalid")
    pcm = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, channels).astype(np.float64)
    if not np.all(np.isfinite(pcm)):
        raise MeasurementError("decoded PCM contains non-finite samples")
    return pcm


def _ebur128(path: Path) -> tuple[float | None, float | None]:
    result = _run_text([
        "ffmpeg", "-nostdin", "-hide_banner", "-v", "info", "-i", str(path),
        "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-",
    ])
    if result.returncode != 0:
        return None, None
    integrated_matches = re.findall(r"\bI:\s*(-?inf|[-+]?\d+(?:\.\d+)?)\s+LUFS", result.stderr, re.IGNORECASE)
    peak_matches = re.findall(r"\bPeak:\s*(-?inf|[-+]?\d+(?:\.\d+)?)\s+dBFS", result.stderr, re.IGNORECASE)

    def parsed(matches: list[str]) -> float | None:
        if not matches or matches[-1].lower().endswith("inf"):
            return None
        value = float(matches[-1])
        return value if math.isfinite(value) else None

    return parsed(integrated_matches), parsed(peak_matches)


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, EPSILON))


def _framed_rms(mono: np.ndarray, frame_length: int) -> np.ndarray:
    values = []
    for start in range(0, len(mono), frame_length):
        frame = mono[start : start + frame_length]
        if frame.size:
            values.append(math.sqrt(float(np.mean(np.square(frame)))))
    return np.asarray(values, dtype=np.float64)


def _longest_true_run(values: np.ndarray) -> tuple[int, int]:
    best_start = best_end = current_start = 0
    in_run = False
    for index, value in enumerate(values.tolist() + [False]):
        if value and not in_run:
            current_start, in_run = index, True
        elif not value and in_run:
            if index - current_start > best_end - best_start:
                best_start, best_end = current_start, index
            in_run = False
    return best_start, best_end


def _duplicate_segment_fraction(pcm: np.ndarray, segment_length: int) -> float:
    hashes: list[str] = []
    for start in range(0, len(pcm) - segment_length + 1, segment_length):
        segment = np.round(pcm[start : start + segment_length], decimals=6).astype("<f4", copy=False)
        hashes.append(hashlib.sha256(segment.tobytes()).hexdigest())
    if len(hashes) < 2:
        return 0.0
    return (len(hashes) - len(set(hashes))) / len(hashes)


def _spectral_centroid(mono: np.ndarray, sample_rate: int) -> float:
    if mono.size > 131072:
        indices = np.linspace(0, mono.size - 1, 131072, dtype=np.int64)
        mono = mono[indices]
    window = np.hanning(mono.size)
    magnitude = np.abs(np.fft.rfft(mono * window))
    total = float(np.sum(magnitude))
    if total <= EPSILON:
        return 0.0
    frequencies = np.fft.rfftfreq(mono.size, d=1.0 / sample_rate)
    return float(np.sum(frequencies * magnitude) / total)


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
    if contract.get("modality") not in {"audio", "av"}:
        raise MeasurementError("audio measurement requires audio or av modality")
    if contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise MeasurementError("contract is not ready for a lease")
    if not isinstance(contract.get("audio_spec"), dict):
        raise MeasurementError("contract lacks audio_spec")
    if contract.get("modality") == "av" and not isinstance(contract.get("av_spec"), dict):
        raise MeasurementError("AV contract lacks av_spec")


def measure_audio(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    _validate_contract(contract)
    if not path.is_file():
        raise MeasurementError("artifact path is not a file")
    probe = _probe(path)
    streams = probe.get("streams", [])
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    if len(audio_streams) != 1:
        raise MeasurementError("exactly one audio stream is required")
    stream = audio_streams[0]
    format_info = probe.get("format", {})
    sample_rate = int(_finite_float(stream.get("sample_rate"), "sample rate", positive=True))
    channels = int(_finite_float(stream.get("channels"), "channel count", positive=True))
    probed_duration = _finite_float(stream.get("duration") or format_info.get("duration"), "duration", positive=True)
    start_time = _finite_float(stream.get("start_time", 0), "audio start time")
    pcm = _decode_pcm(path, sample_rate, channels, probed_duration)
    sample_count = int(pcm.shape[0])
    duration = sample_count / sample_rate
    mono = np.mean(pcm, axis=1)
    absolute = np.abs(pcm)
    absolute_peak = float(np.max(absolute))
    peak_location = int(np.unravel_index(np.argmax(absolute), absolute.shape)[0])
    differences = np.abs(np.diff(pcm, axis=0))
    max_discontinuity = float(np.max(differences)) if differences.size else 0.0
    discontinuity_location = int(np.unravel_index(np.argmax(differences), differences.shape)[0] + 1) if differences.size else 0
    frame_length = max(1, round(sample_rate * FRAME_MILLISECONDS / 1000))
    framed_rms = _framed_rms(mono, frame_length)
    silence_flags = np.asarray([_dbfs(value) <= SILENCE_DBFS for value in framed_rms], dtype=bool)
    silence_start, silence_end = _longest_true_run(silence_flags)
    channel_rms = np.sqrt(np.mean(np.square(pcm), axis=0))
    channel_rms_db = np.asarray([_dbfs(float(value)) for value in channel_rms])
    integrated_lufs, true_peak_dbfs = _ebur128(path)
    spec = contract["audio_spec"]
    metrics: dict[str, Any] = {
        "decode_success": True,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "duration_seconds": duration,
        "sample_count": sample_count,
        "sample_rate_delta_hz": abs(sample_rate - int(spec["sample_rate_hz"])),
        "channel_delta": abs(channels - int(spec["channels"])),
        "duration_delta_seconds": abs(duration - float(spec["duration_seconds"])),
        "absolute_peak": absolute_peak,
        "peak_dbfs": _dbfs(absolute_peak),
        "clipped_sample_fraction": float(np.mean(absolute >= 0.999)),
        "max_abs_dc_offset": float(np.max(np.abs(np.mean(pcm, axis=0)))),
        "silence_frame_fraction": float(np.mean(silence_flags)),
        "rms_dbfs": _dbfs(math.sqrt(float(np.mean(np.square(pcm))))),
        "max_channel_rms_db_delta": float(np.max(channel_rms_db) - np.min(channel_rms_db)),
        "max_sample_discontinuity": max_discontinuity,
        "duplicate_segment_fraction": _duplicate_segment_fraction(
            pcm, max(1, round(sample_rate * SEGMENT_MILLISECONDS / 1000))
        ),
        "spectral_centroid_hz": _spectral_centroid(mono, sample_rate),
    }
    if channels == 2:
        left, right = pcm[:, 0], pcm[:, 1]
        if float(np.std(left)) > EPSILON and float(np.std(right)) > EPSILON:
            metrics["stereo_phase_correlation"] = float(np.corrcoef(left, right)[0, 1])
    if integrated_lufs is not None:
        metrics["integrated_lufs"] = integrated_lufs
        metrics["integrated_lufs_delta"] = abs(integrated_lufs - float(spec["lufs_target"]))
    if true_peak_dbfs is not None:
        metrics["true_peak_dbfs"] = true_peak_dbfs

    av_container = None
    implicit_gates = [
        {"gate_id": "contract-sample-rate", "metric": "sample_rate_delta_hz", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
        {"gate_id": "contract-channels", "metric": "channel_delta", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
        {"gate_id": "contract-duration", "metric": "duration_delta_seconds", "operator": "lte", "threshold": max(0.05, 2 / sample_rate), "on_failure": "REJECT"},
        {"gate_id": "contract-loudness", "metric": "integrated_lufs_delta", "operator": "lte", "threshold": 2.0, "on_failure": "REPAIR"},
    ]
    if contract["modality"] == "av":
        video_streams = [item for item in streams if item.get("codec_type") == "video"]
        if len(video_streams) != 1:
            raise MeasurementError("AV measurement requires exactly one video stream")
        video = video_streams[0]
        video_duration = _finite_float(video.get("duration") or format_info.get("duration"), "video duration", positive=True)
        video_start = _finite_float(video.get("start_time", 0), "video start time")
        metrics["av_stream_start_offset_ms"] = abs(start_time - video_start) * 1000
        metrics["av_stream_duration_delta_ms"] = abs(duration - video_duration) * 1000
        av_container = {
            "video_codec_name": video.get("codec_name") or "unknown",
            "video_duration_seconds": video_duration,
            "video_start_time_seconds": video_start,
        }
        implicit_gates.append({
            "gate_id": "contract-av-stream-start-offset",
            "metric": "av_stream_start_offset_ms",
            "operator": "lte",
            "threshold": float(contract["av_spec"]["max_sync_error_ms"]),
            "on_failure": "REJECT",
        })

    spans = [
        {"category": "absolute_peak", "start_seconds": peak_location / sample_rate, "end_seconds": min(duration, (peak_location + 1) / sample_rate), "severity_value": absolute_peak},
        {"category": "largest_discontinuity", "start_seconds": max(0.0, (discontinuity_location - 1) / sample_rate), "end_seconds": min(duration, discontinuity_location / sample_rate), "severity_value": max_discontinuity},
    ]
    if silence_end > silence_start:
        spans.append({
            "category": "longest_silence",
            "start_seconds": silence_start * frame_length / sample_rate,
            "end_seconds": min(duration, silence_end * frame_length / sample_rate),
            "severity_value": (silence_end - silence_start) * frame_length / sample_rate,
        })

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
        gate_results.append({
            "gate_id": gate["gate_id"], "metric": gate["metric"], "status": status,
            "observed": observed, "operator": gate["operator"], "threshold": gate["threshold"],
            "on_failure": gate["on_failure"],
        })

    measurement = {
        "schema_version": "wave64.aqa.audio_measurement.v1",
        "measurement_id": ZERO_HASH,
        "contract_id": contract["contract_id"],
        "artifact_sha256": sha256_file(path),
        "evaluator_version": EVALUATOR_VERSION,
        "container": {
            "format_name": format_info.get("format_name") or "unknown",
            "duration_seconds": probed_duration,
            "size_bytes": path.stat().st_size,
            "full_decode_pass": True,
        },
        "audio_stream": {
            "codec_name": stream.get("codec_name") or "unknown",
            "sample_format": stream.get("sample_fmt") or "unknown",
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "sample_count": sample_count,
            "start_time_seconds": start_time,
        },
        "av_container": av_container,
        "loudness": {
            "integrated_lufs": integrated_lufs,
            "true_peak_dbfs": true_peak_dbfs,
            "measurement_standard": "FFmpeg ebur128 peak=true",
        },
        "metric_selected_spans": spans,
        "metrics": metrics,
        "gate_results": gate_results,
        "disposition": "PASS_DETERMINISTIC_GATES" if all(item["status"] == "PASS" for item in gate_results) else "FAIL_DETERMINISTIC_GATES",
    }
    measurement["measurement_id"] = hashlib.sha256(canonical_bytes(measurement)).hexdigest()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(measurement)
    return measurement


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = measure_audio(args.artifact, json.loads(args.contract.read_text(encoding="utf-8")))
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
