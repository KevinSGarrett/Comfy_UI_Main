#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

try:
    import av
except Exception as exc:  # pragma: no cover
    av = None
    AV_IMPORT_ERROR = exc
else:
    AV_IMPORT_ERROR = None

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

GATE_NAMES = (
    "sync_offset_threshold",
    "drift_check",
    "mux_manifest",
    "event_owner_alignment",
    "av_review_record",
    "production_runtime_proof",
    "production_av_sync_authority",
    "overall_pass",
)

CANONICAL_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_av_sync_measurement_packet.schema.json")
REPORT_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json")
WAVE30_EVENT_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json")
WAVE30_MIX_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json")
GATE_RULES_RELATIVE = Path("Plan/10_REGISTRIES/wave64_av_sync_gate_rules.json")


class InvalidInputError(ValueError):
    pass


@dataclass(frozen=True)
class Binding:
    path: Path
    sha256: str
    bytes: int | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class ProducerIdentity:
    proof_kind: str
    engine: str
    model: str
    model_version: str
    model_sha256: str
    authority_id: str
    synthetic_only: bool


def _reject_nonfinite_json(token: str) -> Any:
    raise InvalidInputError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"invalid JSON in {path}: {exc}") from exc


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.path)
        raise InvalidInputError(f"{label} schema validation failed at {where}: {first.message}")


def _expect_exact_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(keys - observed)
    extra = sorted(observed - keys)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"unknown={','.join(extra)}")
        raise InvalidInputError(f"{label} key mismatch ({'; '.join(parts)})")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_non_empty_string(value, label)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise InvalidInputError(f"{label} must be lowercase SHA-256")
    return sha


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInputError(f"{label} must be boolean")
    return bool(value)


def _expect_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise InvalidInputError(f"{label} must be >= {minimum}")
    return value


def _expect_finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise InvalidInputError(f"{label} must be finite")
    return as_float


def _resolve_under_root(root: Path, candidate: str, label: str) -> Path:
    raw = Path(candidate)
    resolved = (raw if raw.is_absolute() else (root / raw)).resolve()
    if not resolved.is_relative_to(root):
        raise InvalidInputError(f"{label} escapes root: {resolved}")
    return resolved


def _validate_path_sha_binding(root: Path, payload: Any, label: str) -> Binding:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256"}, label)
    path = _resolve_under_root(root, _expect_non_empty_string(payload["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(payload["sha256"], f"{label}.sha256")
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed = _sha256_of(path)
    if observed != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed})")
    return Binding(path=path, sha256=sha)


def _validate_path_sha_bytes_media_binding(root: Path, payload: Any, label: str, expected_media: set[str]) -> Binding:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256", "bytes", "media_type"}, label)
    path = _resolve_under_root(root, _expect_non_empty_string(payload["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(payload["sha256"], f"{label}.sha256")
    size = _expect_int(payload["bytes"], f"{label}.bytes", minimum=1)
    media_type = _expect_non_empty_string(payload["media_type"], f"{label}.media_type")
    if media_type not in expected_media:
        raise InvalidInputError(f"{label}.media_type must be one of: {sorted(expected_media)}")
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed_size = path.stat().st_size
    if observed_size != size:
        raise InvalidInputError(f"{label}.bytes mismatch ({size} != {observed_size})")
    observed_sha = _sha256_of(path)
    if observed_sha != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return Binding(path=path, sha256=sha, bytes=size, media_type=media_type)


def _safe_ratio(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        as_float = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(as_float):
        return 0.0
    return as_float


def _update_video_digest(digest: "hashlib._Hash", frame: Any) -> None:
    normalized = frame.reformat(format="rgb24")
    plane = normalized.planes[0]
    raw = bytes(plane)
    width = int(normalized.width)
    height = int(normalized.height)
    stride = int(plane.line_size)
    digest.update(width.to_bytes(4, byteorder="little", signed=False))
    digest.update(height.to_bytes(4, byteorder="little", signed=False))
    row_bytes = width * 3
    for row in range(height):
        start = row * stride
        digest.update(raw[start : start + row_bytes])


def _scan_packet_pts(container: Any, stream: Any) -> tuple[bool, int]:
    packet_pts_monotonic = True
    missing_packet_pts_count = 0
    pending_empty_untimed_packets = 0
    previous_packet_pts: float | None = None
    for packet in container.demux(stream):
        pts = packet.pts if packet.pts is not None else packet.dts
        if pts is None:
            # PyAV emits a zero-byte flush sentinel after the final media packet.
            # Delay classification so only one trailing sentinel is ignored.
            if int(packet.size or 0) == 0 and int(packet.duration or 0) == 0:
                pending_empty_untimed_packets += 1
                continue
            if pending_empty_untimed_packets:
                missing_packet_pts_count += pending_empty_untimed_packets
                pending_empty_untimed_packets = 0
            missing_packet_pts_count += 1
            continue
        if pending_empty_untimed_packets:
            missing_packet_pts_count += pending_empty_untimed_packets
            pending_empty_untimed_packets = 0
        if stream.time_base is None:
            missing_packet_pts_count += 1
            continue
        pts_seconds = float(pts * stream.time_base)
        if previous_packet_pts is not None and pts_seconds < previous_packet_pts - 1e-9:
            packet_pts_monotonic = False
        previous_packet_pts = pts_seconds
    if pending_empty_untimed_packets > 1:
        missing_packet_pts_count += pending_empty_untimed_packets - 1
    return packet_pts_monotonic, missing_packet_pts_count


def _decode_video_container(path: Path, label: str) -> dict[str, Any]:
    try:
        packet_container = av.open(str(path))
    except Exception as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} cannot be opened by PyAV: {exc}") from exc
    try:
        video_streams = [stream for stream in packet_container.streams if stream.type == "video"]
        if not video_streams:
            raise InvalidInputError(f"{label} has no video stream")
        stream_for_packets = video_streams[0]
        packet_pts_monotonic, missing_packet_pts_count = _scan_packet_pts(packet_container, stream_for_packets)
    finally:
        packet_container.close()

    try:
        frame_container = av.open(str(path))
    except Exception as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} cannot be reopened by PyAV: {exc}") from exc
    try:
        format_name = _expect_non_empty_string(frame_container.format.name or "unknown", f"{label}.container_format")
        video_streams = [stream for stream in frame_container.streams if stream.type == "video"]
        audio_streams = [stream for stream in frame_container.streams if stream.type == "audio"]
        if not video_streams:
            raise InvalidInputError(f"{label} has no video stream")
        stream = video_streams[0]
        codec_name = _expect_non_empty_string(stream.codec_context.name or "unknown", f"{label}.video_codec")
        time_base = _safe_ratio(stream.time_base)
        frame_rate = _safe_ratio(stream.average_rate) or _safe_ratio(stream.base_rate)
        if frame_rate <= 0.0 and time_base > 0.0:
            frame_rate = 1.0 / time_base
        if frame_rate <= 0.0:
            raise InvalidInputError(f"{label} does not expose a valid frame rate")
        digest = hashlib.sha256()
        frame_count = 0
        width = int(stream.codec_context.width or stream.width or 0)
        height = int(stream.codec_context.height or stream.height or 0)
        if width <= 0 or height <= 0:
            raise InvalidInputError(f"{label} has invalid dimensions")
        frame_pts_monotonic = True
        missing_frame_pts_count = 0
        previous_frame_pts: float | None = None
        first_pts_seconds: float | None = None
        last_pts_seconds: float | None = None
        last_frame_duration_seconds: float | None = None
        last_observed_interval_seconds: float | None = None
        for frame in frame_container.decode(video=0):
            frame_count += 1
            _update_video_digest(digest, frame)
            pts_seconds: float | None = None
            if frame.pts is not None and frame.time_base is not None:
                pts_seconds = float(frame.pts * frame.time_base)
            elif frame.pts is not None and time_base > 0.0:
                pts_seconds = float(frame.pts) * time_base
            if pts_seconds is None:
                missing_frame_pts_count += 1
            else:
                if first_pts_seconds is None:
                    first_pts_seconds = pts_seconds
                last_pts_seconds = pts_seconds
                if previous_frame_pts is not None and pts_seconds < previous_frame_pts - 1e-9:
                    frame_pts_monotonic = False
                if previous_frame_pts is not None and pts_seconds > previous_frame_pts:
                    last_observed_interval_seconds = pts_seconds - previous_frame_pts
                previous_frame_pts = pts_seconds
                frame_duration = _safe_ratio(frame.duration) * _safe_ratio(frame.time_base)
                if frame_duration > 0.0:
                    last_frame_duration_seconds = frame_duration
            width = int(frame.width)
            height = int(frame.height)
        if frame_count <= 0:
            raise InvalidInputError(f"{label} decoded zero video frames")
        fallback_frame_duration_seconds = 1.0 / frame_rate
        if first_pts_seconds is None or last_pts_seconds is None:
            first_pts_seconds = 0.0
            last_pts_seconds = (frame_count - 1) * fallback_frame_duration_seconds
        endpoint_frame_duration_seconds = (
            last_frame_duration_seconds or last_observed_interval_seconds or fallback_frame_duration_seconds
        )
        duration_seconds = max(0.0, (last_pts_seconds - first_pts_seconds) + endpoint_frame_duration_seconds)
        end_timestamp_seconds = last_pts_seconds + endpoint_frame_duration_seconds
        return {
            "container_format": format_name,
            "stream_count_video": len(video_streams),
            "stream_count_audio": len(audio_streams),
            "codec": codec_name,
            "time_base": time_base if time_base > 0.0 else (1.0 / frame_rate),
            "frame_rate": frame_rate,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "first_pts_seconds": round(first_pts_seconds, 6),
            "last_pts_seconds": round(last_pts_seconds, 6),
            "duration_seconds": round(duration_seconds, 6),
            "end_timestamp_seconds": round(end_timestamp_seconds, 6),
            "packet_pts_monotonic": packet_pts_monotonic,
            "frame_pts_monotonic": frame_pts_monotonic,
            "missing_packet_pts_count": missing_packet_pts_count,
            "missing_frame_pts_count": missing_frame_pts_count,
            "decoded_video_hash": digest.hexdigest(),
        }
    except av.AVError as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} decode failed: {exc}") from exc
    finally:
        frame_container.close()


def _read_wav_pcm(path: Path, label: str) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            comp_type = handle.getcomptype()
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise InvalidInputError(f"{label} malformed WAV: {exc}") from exc
    if comp_type != "NONE":
        raise InvalidInputError(f"{label} must be PCM WAV")
    if channels <= 0 or sample_rate <= 0 or sample_width <= 0 or frame_count <= 0:
        raise InvalidInputError(f"{label} has invalid WAV metrics")
    expected_size = frame_count * channels * sample_width
    if len(payload) != expected_size:
        raise InvalidInputError(f"{label} WAV payload length mismatch ({len(payload)} != {expected_size})")
    digest = hashlib.sha256()
    digest.update(payload)
    duration_seconds = frame_count / float(sample_rate)
    return {
        "stream_count_audio": 1,
        "codec": "pcm_s16le" if sample_width == 2 else f"pcm_s{sample_width * 8}le",
        "time_base": 1.0 / float(sample_rate),
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "channel_layout": "mono" if channels == 1 else f"{channels}ch",
        "sample_count": frame_count * channels,
        "first_pts_seconds": 0.0,
        "last_pts_seconds": round(max(0.0, duration_seconds - (1.0 / sample_rate)), 6),
        "duration_seconds": round(duration_seconds, 6),
        "end_timestamp_seconds": round(duration_seconds, 6),
        "packet_pts_monotonic": True,
        "frame_pts_monotonic": True,
        "missing_packet_pts_count": 0,
        "missing_frame_pts_count": 0,
        "decoded_audio_hash": digest.hexdigest(),
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
    }


def _decode_mux_audio(path: Path, label: str, target_rate: int) -> dict[str, Any]:
    try:
        packet_container = av.open(str(path))
    except Exception as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} cannot be opened by PyAV: {exc}") from exc
    try:
        audio_streams = [stream for stream in packet_container.streams if stream.type == "audio"]
        if not audio_streams:
            raise InvalidInputError(f"{label} has no audio stream")
        stream_for_packets = audio_streams[0]
        packet_pts_monotonic, missing_packet_pts_count = _scan_packet_pts(packet_container, stream_for_packets)
    finally:
        packet_container.close()

    try:
        frame_container = av.open(str(path))
    except Exception as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} cannot be reopened by PyAV: {exc}") from exc
    try:
        audio_streams = [stream for stream in frame_container.streams if stream.type == "audio"]
        if not audio_streams:
            raise InvalidInputError(f"{label} has no audio stream")
        stream = audio_streams[0]
        codec_name = _expect_non_empty_string(stream.codec_context.name or "unknown", f"{label}.audio_codec")
        stream_time_base = _safe_ratio(stream.time_base)
        sample_rate = int(stream.codec_context.sample_rate or stream.rate or target_rate)
        channels = int(stream.codec_context.channels or 0)
        if channels <= 0 and stream.layout is not None:
            channels = int(len(stream.layout.channels))
        if channels <= 0:
            raise InvalidInputError(f"{label} has invalid channel count")
        if channels == 1:
            layout_name = "mono"
        elif channels == 2:
            layout_name = "stereo"
        else:
            layout_name = stream.layout.name if stream.layout is not None else f"{channels}ch"
        resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=target_rate)
        digest = hashlib.sha256()
        sample_count = 0
        frame_pts_monotonic = True
        missing_frame_pts_count = 0
        previous_frame_pts: float | None = None
        first_pts_seconds: float | None = None
        last_pts_seconds: float | None = None
        last_frame_samples = 0
        for frame in frame_container.decode(audio=0):
            converted = resampler.resample(frame)
            converted_frames = converted if isinstance(converted, list) else [converted]
            for converted_frame in converted_frames:
                if converted_frame is None:
                    continue
                frame_samples = int(converted_frame.samples)
                bytes_per_sample = int(converted_frame.format.bytes)
                valid_byte_count = frame_samples * len(converted_frame.layout.channels) * bytes_per_sample
                plane_bytes = bytes(converted_frame.planes[0])
                if len(plane_bytes) < valid_byte_count:
                    raise InvalidInputError(f"{label} decoded audio plane is shorter than its declared sample payload")
                digest.update(plane_bytes[:valid_byte_count])
                sample_count += frame_samples
                last_frame_samples = frame_samples
                pts_seconds: float | None = None
                if converted_frame.pts is not None and converted_frame.time_base is not None:
                    pts_seconds = float(converted_frame.pts * converted_frame.time_base)
                elif frame.pts is not None and frame.time_base is not None:
                    pts_seconds = float(frame.pts * frame.time_base)
                elif frame.pts is not None and stream_time_base > 0.0:
                    pts_seconds = float(frame.pts) * stream_time_base
                if pts_seconds is None:
                    missing_frame_pts_count += 1
                else:
                    if first_pts_seconds is None:
                        first_pts_seconds = pts_seconds
                    last_pts_seconds = pts_seconds
                    if previous_frame_pts is not None and pts_seconds < previous_frame_pts - 1e-9:
                        frame_pts_monotonic = False
                    previous_frame_pts = pts_seconds
        if sample_count <= 0:
            raise InvalidInputError(f"{label} decoded zero audio samples")
        duration_seconds = sample_count / float(target_rate)
        frame_duration_seconds = last_frame_samples / float(target_rate)
        if first_pts_seconds is None or last_pts_seconds is None:
            first_pts_seconds = 0.0
            last_pts_seconds = max(0.0, duration_seconds - frame_duration_seconds)
        end_timestamp_seconds = last_pts_seconds + frame_duration_seconds
        return {
            "stream_count_audio": len(audio_streams),
            "codec": codec_name,
            "time_base": stream_time_base if stream_time_base > 0.0 else (1.0 / float(target_rate)),
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "channel_layout": _expect_non_empty_string(layout_name, f"{label}.channel_layout"),
            "sample_count": sample_count,
            "first_pts_seconds": round(first_pts_seconds, 6),
            "last_pts_seconds": round(last_pts_seconds, 6),
            "duration_seconds": round(duration_seconds, 6),
            "end_timestamp_seconds": round(end_timestamp_seconds, 6),
            "packet_pts_monotonic": packet_pts_monotonic,
            "frame_pts_monotonic": frame_pts_monotonic,
            "missing_packet_pts_count": missing_packet_pts_count,
            "missing_frame_pts_count": missing_frame_pts_count,
            "decoded_audio_hash": digest.hexdigest(),
        }
    except av.AVError as exc:  # pragma: no cover
        raise InvalidInputError(f"{label} audio decode failed: {exc}") from exc
    finally:
        frame_container.close()


def _binding_or_none(binding: Binding | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    payload = {"path": str(binding.path), "sha256": binding.sha256}
    if binding.bytes is not None:
        payload["bytes"] = binding.bytes
    return payload


def _make_gate(status: str, blockers: list[str], artifact_bindings: list[str]) -> dict[str, Any]:
    if status == PASS and blockers:
        raise InvalidInputError("internal gate invariant violated: PASS gate contains blockers")
    return {"status": status, "blockers": blockers, "artifact_bindings": artifact_bindings}


def _status_from_fail_and_blocked(fail: list[str], blocked: list[str]) -> str:
    if fail:
        return FAIL
    if blocked:
        return BLOCKED
    return PASS


def _append_pts_blockers(blockers: list[str], label: str, payload: dict[str, Any]) -> None:
    if not payload["packet_pts_monotonic"]:
        blockers.append(f"{label} packet timestamps are non-monotonic")
    if not payload["frame_pts_monotonic"]:
        blockers.append(f"{label} frame timestamps are non-monotonic")
    if int(payload["missing_packet_pts_count"]) > 0:
        blockers.append(f"{label} has missing packet timestamps")
    if int(payload["missing_frame_pts_count"]) > 0:
        blockers.append(f"{label} has missing frame timestamps")


def _parse_gate_registry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError("wave64_av_sync_gate_rules must be an object")
    _expect_exact_keys(
        payload,
        {"schema_name", "registry_version", "parser_rules", "sync_rules", "mux_rules", "producer_rules", "production_rules"},
        "wave64_av_sync_gate_rules",
    )
    if payload["schema_name"] != "wave64_av_sync_gate_rules":
        raise InvalidInputError("wave64_av_sync_gate_rules.schema_name mismatch")
    if _expect_int(payload["registry_version"], "wave64_av_sync_gate_rules.registry_version", minimum=1) != 1:
        raise InvalidInputError("wave64_av_sync_gate_rules.registry_version must be 1")

    parser_rules = payload["parser_rules"]
    if not isinstance(parser_rules, dict):
        raise InvalidInputError("parser_rules must be an object")
    _expect_exact_keys(parser_rules, {"allowed_pyav_versions"}, "parser_rules")
    allowed_pyav_versions_raw = parser_rules["allowed_pyav_versions"]
    if not isinstance(allowed_pyav_versions_raw, list) or not allowed_pyav_versions_raw:
        raise InvalidInputError("parser_rules.allowed_pyav_versions must be a non-empty array")
    allowed_pyav_versions = [_expect_non_empty_string(item, "parser_rules.allowed_pyav_versions[]") for item in allowed_pyav_versions_raw]

    sync_rules = payload["sync_rules"]
    if not isinstance(sync_rules, dict):
        raise InvalidInputError("sync_rules must be an object")
    _expect_exact_keys(
        sync_rules,
        {"max_start_offset_seconds", "max_cumulative_endpoint_drift_seconds", "max_anchor_frame_delta"},
        "sync_rules",
    )
    max_start_offset_seconds = _expect_finite_number(sync_rules["max_start_offset_seconds"], "sync_rules.max_start_offset_seconds")
    max_cumulative_endpoint_drift_seconds = _expect_finite_number(
        sync_rules["max_cumulative_endpoint_drift_seconds"], "sync_rules.max_cumulative_endpoint_drift_seconds"
    )
    max_anchor_frame_delta = _expect_finite_number(sync_rules["max_anchor_frame_delta"], "sync_rules.max_anchor_frame_delta")
    if max_start_offset_seconds < 0.0 or max_cumulative_endpoint_drift_seconds < 0.0 or max_anchor_frame_delta < 0.0:
        raise InvalidInputError("sync_rules values must be non-negative")

    mux_rules = payload["mux_rules"]
    if not isinstance(mux_rules, dict):
        raise InvalidInputError("mux_rules must be an object")
    _expect_exact_keys(
        mux_rules,
        {
            "allowed_container_formats",
            "required_video_stream_count",
            "required_audio_stream_count",
            "required_video_codec",
            "required_audio_codec",
            "required_audio_sample_rate_hz",
            "required_audio_channels",
            "required_audio_layouts",
        },
        "mux_rules",
    )
    allowed_container_formats_raw = mux_rules["allowed_container_formats"]
    if not isinstance(allowed_container_formats_raw, list) or not allowed_container_formats_raw:
        raise InvalidInputError("mux_rules.allowed_container_formats must be a non-empty array")
    allowed_container_formats = {_expect_non_empty_string(item, "mux_rules.allowed_container_formats[]") for item in allowed_container_formats_raw}
    required_audio_layouts_raw = mux_rules["required_audio_layouts"]
    if not isinstance(required_audio_layouts_raw, list) or not required_audio_layouts_raw:
        raise InvalidInputError("mux_rules.required_audio_layouts must be a non-empty array")
    required_audio_layouts = {_expect_non_empty_string(item, "mux_rules.required_audio_layouts[]") for item in required_audio_layouts_raw}
    parsed_mux_rules = {
        "allowed_container_formats": allowed_container_formats,
        "required_video_stream_count": _expect_int(mux_rules["required_video_stream_count"], "mux_rules.required_video_stream_count", minimum=1),
        "required_audio_stream_count": _expect_int(mux_rules["required_audio_stream_count"], "mux_rules.required_audio_stream_count", minimum=1),
        "required_video_codec": _expect_non_empty_string(mux_rules["required_video_codec"], "mux_rules.required_video_codec"),
        "required_audio_codec": _expect_non_empty_string(mux_rules["required_audio_codec"], "mux_rules.required_audio_codec"),
        "required_audio_sample_rate_hz": _expect_int(
            mux_rules["required_audio_sample_rate_hz"], "mux_rules.required_audio_sample_rate_hz", minimum=1
        ),
        "required_audio_channels": _expect_int(mux_rules["required_audio_channels"], "mux_rules.required_audio_channels", minimum=1),
        "required_audio_layouts": required_audio_layouts,
    }

    producer_rules = payload["producer_rules"]
    if not isinstance(producer_rules, dict):
        raise InvalidInputError("producer_rules must be an object")
    _expect_exact_keys(
        producer_rules,
        {
            "measurement_allowlist",
            "playback_allowlist",
            "runtime_allowlist",
            "forbid_self_authorization",
            "require_distinct_authority_ids_across_roles",
            "required_review_results",
        },
        "producer_rules",
    )
    required_review_results_raw = producer_rules["required_review_results"]
    if not isinstance(required_review_results_raw, list) or not required_review_results_raw:
        raise InvalidInputError("producer_rules.required_review_results must be a non-empty array")
    required_review_results = [
        _expect_non_empty_string(item, "producer_rules.required_review_results[]") for item in required_review_results_raw
    ]
    forbid_self_authorization = _expect_bool(producer_rules["forbid_self_authorization"], "producer_rules.forbid_self_authorization")
    require_distinct_authority_ids = _expect_bool(
        producer_rules["require_distinct_authority_ids_across_roles"],
        "producer_rules.require_distinct_authority_ids_across_roles",
    )

    def parse_allowlist(raw: Any, label: str, expected_kind: str) -> dict[tuple[str, str, str, str], ProducerIdentity]:
        if not isinstance(raw, list) or not raw:
            raise InvalidInputError(f"{label} must be a non-empty array")
        records: dict[tuple[str, str, str, str], ProducerIdentity] = {}
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise InvalidInputError(f"{label}[{idx}] must be an object")
            _expect_exact_keys(
                item,
                {"proof_kind", "engine", "model", "model_version", "model_sha256", "authority_id", "synthetic_only"},
                f"{label}[{idx}]",
            )
            proof_kind = _expect_non_empty_string(item["proof_kind"], f"{label}[{idx}].proof_kind")
            if proof_kind != expected_kind:
                raise InvalidInputError(f"{label}[{idx}].proof_kind must be {expected_kind}")
            engine = _expect_non_empty_string(item["engine"], f"{label}[{idx}].engine")
            model = _expect_non_empty_string(item["model"], f"{label}[{idx}].model")
            model_version = _expect_non_empty_string(item["model_version"], f"{label}[{idx}].model_version")
            model_sha256 = _expect_sha256(item["model_sha256"], f"{label}[{idx}].model_sha256")
            authority_id = _expect_non_empty_string(item["authority_id"], f"{label}[{idx}].authority_id")
            synthetic_only = _expect_bool(item["synthetic_only"], f"{label}[{idx}].synthetic_only")
            key = (engine, model, model_version, model_sha256)
            if key in records:
                raise InvalidInputError(f"{label} duplicate producer record for {engine}/{model}/{model_version}")
            records[key] = ProducerIdentity(
                proof_kind=proof_kind,
                engine=engine,
                model=model,
                model_version=model_version,
                model_sha256=model_sha256,
                authority_id=authority_id,
                synthetic_only=synthetic_only,
            )
        return records

    measurement_allowlist = parse_allowlist(producer_rules["measurement_allowlist"], "measurement_allowlist", "anchor_measurement")
    playback_allowlist = parse_allowlist(producer_rules["playback_allowlist"], "playback_allowlist", "av_sync_playback_review")
    runtime_allowlist = parse_allowlist(producer_rules["runtime_allowlist"], "runtime_allowlist", "production_runtime")

    production_rules = payload["production_rules"]
    if not isinstance(production_rules, dict):
        raise InvalidInputError("production_rules must be an object")
    _expect_exact_keys(production_rules, {"approved_certification_bundle_allowlist"}, "production_rules")
    raw_allowlist = production_rules["approved_certification_bundle_allowlist"]
    if not isinstance(raw_allowlist, list):
        raise InvalidInputError("production_rules.approved_certification_bundle_allowlist must be an array")
    production_allowlist: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_allowlist):
        if not isinstance(item, dict):
            raise InvalidInputError(f"approved_certification_bundle_allowlist[{idx}] must be an object")
        _expect_exact_keys(
            item,
            {"bundle_id", "authority_id", "bundle_sha256", "revoked"},
            f"approved_certification_bundle_allowlist[{idx}]",
        )
        production_allowlist.append(
            {
                "bundle_id": _expect_non_empty_string(item["bundle_id"], f"approved_certification_bundle_allowlist[{idx}].bundle_id"),
                "authority_id": _expect_non_empty_string(
                    item["authority_id"], f"approved_certification_bundle_allowlist[{idx}].authority_id"
                ),
                "bundle_sha256": _expect_sha256(item["bundle_sha256"], f"approved_certification_bundle_allowlist[{idx}].bundle_sha256"),
                "revoked": _expect_bool(item["revoked"], f"approved_certification_bundle_allowlist[{idx}].revoked"),
            }
        )

    if require_distinct_authority_ids:
        authority_roles: dict[str, set[str]] = {}
        for role, records in (
            ("measurement", measurement_allowlist.values()),
            ("playback", playback_allowlist.values()),
            ("runtime", runtime_allowlist.values()),
        ):
            for record in records:
                authority_roles.setdefault(record.authority_id, set()).add(role)
        for record in production_allowlist:
            authority_roles.setdefault(record["authority_id"], set()).add("production")
        collisions = {
            authority_id: sorted(roles)
            for authority_id, roles in authority_roles.items()
            if len(roles) > 1
        }
        if collisions:
            raise InvalidInputError(
                "producer authority_id cannot authorize multiple proof roles: "
                + "; ".join(f"{authority_id}={','.join(roles)}" for authority_id, roles in sorted(collisions.items()))
            )

    return {
        "allowed_pyav_versions": allowed_pyav_versions,
        "sync_rules": {
            "max_start_offset_seconds": max_start_offset_seconds,
            "max_cumulative_endpoint_drift_seconds": max_cumulative_endpoint_drift_seconds,
            "max_anchor_frame_delta": max_anchor_frame_delta,
        },
        "mux_rules": parsed_mux_rules,
        "producer_rules": {
            "measurement_allowlist": measurement_allowlist,
            "playback_allowlist": playback_allowlist,
            "runtime_allowlist": runtime_allowlist,
            "forbid_self_authorization": forbid_self_authorization,
            "require_distinct_authority_ids_across_roles": require_distinct_authority_ids,
            "required_review_results": required_review_results,
        },
        "production_rules": {"approved_certification_bundle_allowlist": production_allowlist},
    }


def _validate_wave30_bindings(
    event_manifest: dict[str, Any],
    mix_manifest: dict[str, Any],
    *,
    run_id: str,
    scene_id: str,
    shot_id: str,
    is_synthetic: bool,
    event_binding: Binding,
    source_audio_binding: Binding,
) -> None:
    for label, payload in (("wave30_event_manifest", event_manifest), ("wave30_mix_manifest", mix_manifest)):
        if not isinstance(payload, dict):
            raise InvalidInputError(f"{label} must be an object")
        if payload.get("run_id") != run_id:
            raise InvalidInputError(f"{label}.run_id mismatch")
        if payload.get("scene_id") != scene_id:
            raise InvalidInputError(f"{label}.scene_id mismatch")
        if payload.get("shot_id") != shot_id:
            raise InvalidInputError(f"{label}.shot_id mismatch")
        if _expect_bool(payload.get("is_synthetic"), f"{label}.is_synthetic") != is_synthetic:
            raise InvalidInputError(f"{label}.is_synthetic mismatch")

    declared_bindings = mix_manifest.get("event_manifest_bindings")
    if not isinstance(declared_bindings, list) or len(declared_bindings) != 1 or not isinstance(declared_bindings[0], dict):
        raise InvalidInputError("wave30_mix_manifest.event_manifest_bindings must contain exactly one object")
    if declared_bindings[0].get("path") != str(event_binding.path):
        raise InvalidInputError("wave30_mix_manifest.event_manifest_bindings[0].path mismatch")
    if declared_bindings[0].get("sha256") != event_binding.sha256:
        raise InvalidInputError("wave30_mix_manifest.event_manifest_bindings[0].sha256 mismatch")

    mixdown_artifact = mix_manifest.get("mixdown_artifact")
    if not isinstance(mixdown_artifact, dict):
        raise InvalidInputError("wave30_mix_manifest.mixdown_artifact must be an object")
    if mixdown_artifact.get("path") != str(source_audio_binding.path):
        raise InvalidInputError("wave30_mix_manifest.mixdown_artifact.path mismatch against packet source_audio_mix_artifact")
    if mixdown_artifact.get("sha256") != source_audio_binding.sha256:
        raise InvalidInputError("wave30_mix_manifest.mixdown_artifact.sha256 mismatch against packet source_audio_mix_artifact")
    if mixdown_artifact.get("bytes") != source_audio_binding.bytes:
        raise InvalidInputError("wave30_mix_manifest.mixdown_artifact.bytes mismatch against packet source_audio_mix_artifact")


def _normalize_producer_for_report(identity: ProducerIdentity | None) -> dict[str, Any] | None:
    if identity is None:
        return None
    return {
        "proof_kind": identity.proof_kind,
        "engine": identity.engine,
        "model": identity.model,
        "model_version": identity.model_version,
        "model_sha256": identity.model_sha256,
        "authority_id": identity.authority_id,
        "synthetic_only": identity.synthetic_only,
    }


def _validate_producer_identity(
    payload: dict[str, Any],
    label: str,
    expected_kind: str,
    allowlist: dict[tuple[str, str, str, str], ProducerIdentity],
    *,
    is_synthetic: bool,
    evidence_origin: str,
) -> tuple[ProducerIdentity | None, list[str]]:
    blocked: list[str] = []
    proof_kind = _expect_non_empty_string(payload.get("proof_kind"), f"{label}.proof_kind")
    if proof_kind != expected_kind:
        raise InvalidInputError(f"{label}.proof_kind mismatch")
    engine = _expect_non_empty_string(payload.get("engine"), f"{label}.engine")
    model = _expect_non_empty_string(payload.get("model"), f"{label}.model")
    model_version = _expect_non_empty_string(payload.get("model_version"), f"{label}.model_version")
    model_sha256 = _expect_sha256(payload.get("model_sha256"), f"{label}.model_sha256")
    authority_id = _expect_non_empty_string(payload.get("authority_id"), f"{label}.authority_id")
    key = (engine, model, model_version, model_sha256)
    if key not in allowlist:
        blocked.append(f"{label} producer is not allowlisted")
        return None, blocked
    allowed = allowlist[key]
    if authority_id != allowed.authority_id:
        blocked.append(f"{label} authority_id is not allowlisted for producer identity")
    if allowed.synthetic_only and not is_synthetic:
        blocked.append(f"{label} producer is synthetic-only for non-synthetic evidence")
    if allowed.synthetic_only and evidence_origin == "hand_authored_relabel":
        blocked.append(f"{label} synthetic-only producer cannot certify hand-authored relabel evidence")
    return allowed, blocked


def _collect_required_anchor_events(event_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events = event_manifest.get("audio_events")
    if not isinstance(events, list):
        raise InvalidInputError("wave30_event_manifest.audio_events must be an array")
    required: dict[str, dict[str, Any]] = {}
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise InvalidInputError(f"wave30_event_manifest.audio_events[{idx}] must be an object")
        audio_event_id = _expect_non_empty_string(event.get("audio_event_id"), f"wave30_event_manifest.audio_events[{idx}].audio_event_id")
        if audio_event_id in required:
            raise InvalidInputError(f"duplicate wave30 audio_event_id: {audio_event_id}")
        sync_class = _expect_non_empty_string(event.get("sync_class"), f"wave30_event_manifest.audio_events[{idx}].sync_class")
        if sync_class not in {"frame_exact", "windowed"}:
            continue
        frame_range = event.get("expected_video_frame_range")
        if not isinstance(frame_range, dict):
            raise InvalidInputError(
                f"wave30_event_manifest.audio_events[{idx}].expected_video_frame_range must be an object for sync-scoped event"
            )
        start_frame = _expect_int(
            frame_range.get("start_frame"),
            f"wave30_event_manifest.audio_events[{idx}].expected_video_frame_range.start_frame",
            minimum=0,
        )
        end_frame = _expect_int(
            frame_range.get("end_frame"),
            f"wave30_event_manifest.audio_events[{idx}].expected_video_frame_range.end_frame",
            minimum=0,
        )
        if end_frame < start_frame:
            raise InvalidInputError(f"wave30_event_manifest.audio_events[{idx}] invalid expected frame range")
        frame_rate = _expect_finite_number(
            frame_range.get("frame_rate"),
            f"wave30_event_manifest.audio_events[{idx}].expected_video_frame_range.frame_rate",
        )
        if frame_rate <= 0.0:
            raise InvalidInputError(f"wave30_event_manifest.audio_events[{idx}] expected frame rate must be > 0")
        source_event_id = _expect_non_empty_string(
            event.get("source_event_id"), f"wave30_event_manifest.audio_events[{idx}].source_event_id"
        )
        subject_binding = event.get("subject_binding")
        if not isinstance(subject_binding, dict):
            raise InvalidInputError(f"wave30_event_manifest.audio_events[{idx}].subject_binding must be an object")
        binding_type = _expect_non_empty_string(
            subject_binding.get("binding_type"), f"wave30_event_manifest.audio_events[{idx}].subject_binding.binding_type"
        )
        expected_owner_id: str | None = None
        if binding_type == "character":
            expected_owner_id = _expect_non_empty_string(
                subject_binding.get("character_id"),
                f"wave30_event_manifest.audio_events[{idx}].subject_binding.character_id",
            )
        elif binding_type == "object":
            expected_owner_id = _expect_non_empty_string(
                subject_binding.get("object_id"),
                f"wave30_event_manifest.audio_events[{idx}].subject_binding.object_id",
            )
        required[audio_event_id] = {
            "audio_event_id": audio_event_id,
            "source_event_id": source_event_id,
            "sync_class": sync_class,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frame_rate": frame_rate,
            "expected_owner_id": expected_owner_id,
        }
    return required


def _validate_wave30_sync_evidence(
    mix_manifest: dict[str, Any],
    required_events: dict[str, dict[str, Any]],
    *,
    mux_video_frame_rate: float,
    mux_video_frame_count: int,
    observed_start_offset_seconds: float,
    max_anchor_frame_delta: float,
) -> tuple[list[str], list[str]]:
    payload = mix_manifest.get("av_sync_evidence")
    if not isinstance(payload, dict):
        raise InvalidInputError("wave30_mix_manifest.av_sync_evidence must be an object")
    _expect_exact_keys(
        payload,
        {"frame_rate", "start_frame", "end_frame", "frame_offset"},
        "wave30_mix_manifest.av_sync_evidence",
    )
    declared_frame_rate = _expect_finite_number(payload["frame_rate"], "wave30_mix_manifest.av_sync_evidence.frame_rate")
    if declared_frame_rate <= 0.0:
        raise InvalidInputError("wave30_mix_manifest.av_sync_evidence.frame_rate must be positive")
    declared_start = _expect_int(payload["start_frame"], "wave30_mix_manifest.av_sync_evidence.start_frame", minimum=0)
    declared_end = _expect_int(payload["end_frame"], "wave30_mix_manifest.av_sync_evidence.end_frame", minimum=0)
    declared_offset = _expect_int(payload["frame_offset"], "wave30_mix_manifest.av_sync_evidence.frame_offset")

    offset_fail: list[str] = []
    alignment_fail: list[str] = []
    if declared_end < declared_start:
        alignment_fail.append("wave30 mix av_sync_evidence frame range is invalid")
    if not math.isclose(declared_frame_rate, mux_video_frame_rate, rel_tol=0.0, abs_tol=1e-6):
        alignment_fail.append("wave30 mix av_sync_evidence frame_rate mismatches decoded mux video")
    if declared_start >= mux_video_frame_count or declared_end >= mux_video_frame_count:
        alignment_fail.append("wave30 mix av_sync_evidence frame range exceeds decoded mux video")

    if required_events:
        expected_start = min(int(event["start_frame"]) for event in required_events.values())
        expected_end = max(int(event["end_frame"]) for event in required_events.values())
        if declared_start != expected_start or declared_end != expected_end:
            alignment_fail.append("wave30 mix av_sync_evidence frame range mismatches sync-scoped event envelope")

    measured_offset_frames = observed_start_offset_seconds * mux_video_frame_rate
    if abs(float(declared_offset) - measured_offset_frames) > max_anchor_frame_delta:
        offset_fail.append("wave30 mix av_sync_evidence frame_offset contradicts decoded AV start offset")
    return offset_fail, alignment_fail


def _validate_anchor_measurement_proof(
    payload: Any,
    *,
    run_id: str,
    scene_id: str,
    shot_id: str,
    take_id: str,
    is_synthetic: bool,
    evidence_origin: str,
    source_video_sha256: str,
    source_audio_sha256: str,
    mux_sha256: str,
    required_events: dict[str, dict[str, Any]],
    allowlist: dict[tuple[str, str, str, str], ProducerIdentity],
    max_anchor_frame_delta: float,
    mux_video_frame_count: int,
    mux_video_end_seconds: float,
) -> tuple[list[str], list[str], ProducerIdentity | None, dict[str, int]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("observed_anchor_measurement_proof must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "proof_kind",
            "engine",
            "model",
            "model_version",
            "model_sha256",
            "authority_id",
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "evidence_origin",
            "source_video_sha256",
            "source_audio_sha256",
            "mux_sha256",
            "anchors",
        },
        "observed_anchor_measurement_proof",
    )
    if payload["schema_name"] != "wave64_av_sync_anchor_measurement_proof":
        raise InvalidInputError("observed_anchor_measurement_proof.schema_name mismatch")
    producer_identity, blocked = _validate_producer_identity(
        payload,
        "observed_anchor_measurement_proof",
        "anchor_measurement",
        allowlist,
        is_synthetic=is_synthetic,
        evidence_origin=evidence_origin,
    )
    fail: list[str] = []
    if payload["run_id"] != run_id:
        fail.append("observed_anchor_measurement_proof run_id mismatch")
    if payload["scene_id"] != scene_id:
        fail.append("observed_anchor_measurement_proof scene_id mismatch")
    if payload["shot_id"] != shot_id:
        fail.append("observed_anchor_measurement_proof shot_id mismatch")
    if payload["take_id"] != take_id:
        fail.append("observed_anchor_measurement_proof take_id mismatch")
    if _expect_bool(payload["is_synthetic"], "observed_anchor_measurement_proof.is_synthetic") != is_synthetic:
        fail.append("observed_anchor_measurement_proof is_synthetic mismatch")
    if _expect_non_empty_string(payload["evidence_origin"], "observed_anchor_measurement_proof.evidence_origin") != evidence_origin:
        fail.append("observed_anchor_measurement_proof evidence_origin mismatch")
    if payload["source_video_sha256"] != source_video_sha256:
        fail.append("observed_anchor_measurement_proof source_video_sha256 mismatch")
    if payload["source_audio_sha256"] != source_audio_sha256:
        fail.append("observed_anchor_measurement_proof source_audio_sha256 mismatch")
    if payload["mux_sha256"] != mux_sha256:
        fail.append("observed_anchor_measurement_proof mux_sha256 mismatch")

    anchors = payload["anchors"]
    if not isinstance(anchors, list):
        raise InvalidInputError("observed_anchor_measurement_proof.anchors must be an array")
    seen_ids: set[str] = set()
    duplicate_count = 0
    extra_count = 0
    missing_count = 0
    for audio_event_id, event in sorted(required_events.items()):
        if int(event["start_frame"]) >= mux_video_frame_count or int(event["end_frame"]) >= mux_video_frame_count:
            fail.append(f"expected anchor frame range exceeds decoded mux video for {audio_event_id}")
    for idx, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            raise InvalidInputError(f"observed_anchor_measurement_proof.anchors[{idx}] must be an object")
        _expect_exact_keys(
            anchor,
            {
                "audio_event_id",
                "source_event_id",
                "sync_class",
                "expected_start_frame",
                "expected_end_frame",
                "observed_frame",
                "observed_time_seconds",
                "observed_owner_id",
            },
            f"observed_anchor_measurement_proof.anchors[{idx}]",
        )
        audio_event_id = _expect_non_empty_string(
            anchor["audio_event_id"], f"observed_anchor_measurement_proof.anchors[{idx}].audio_event_id"
        )
        if audio_event_id in seen_ids:
            duplicate_count += 1
            fail.append(f"duplicate observed anchor for audio_event_id: {audio_event_id}")
            continue
        seen_ids.add(audio_event_id)
        if audio_event_id not in required_events:
            extra_count += 1
            fail.append(f"observed anchor references unknown or non-sync-scoped audio_event_id: {audio_event_id}")
            continue
        event = required_events[audio_event_id]
        if anchor["source_event_id"] != event["source_event_id"]:
            fail.append(f"anchor source_event_id mismatch for {audio_event_id}")
        if anchor["sync_class"] != event["sync_class"]:
            fail.append(f"anchor sync_class mismatch for {audio_event_id}")
        expected_start = _expect_int(anchor["expected_start_frame"], f"anchors[{idx}].expected_start_frame", minimum=0)
        expected_end = _expect_int(anchor["expected_end_frame"], f"anchors[{idx}].expected_end_frame", minimum=0)
        if expected_end < expected_start:
            fail.append(f"anchor expected frame range invalid for {audio_event_id}")
        if expected_start != event["start_frame"] or expected_end != event["end_frame"]:
            fail.append(f"anchor expected frame range mismatch for {audio_event_id}")
        observed_frame = _expect_int(anchor["observed_frame"], f"anchors[{idx}].observed_frame", minimum=0)
        observed_time_seconds = _expect_finite_number(anchor["observed_time_seconds"], f"anchors[{idx}].observed_time_seconds")
        if observed_frame < event["start_frame"] or observed_frame > event["end_frame"]:
            fail.append(f"anchor observed_frame out of expected window for {audio_event_id}")
        if observed_frame >= mux_video_frame_count:
            fail.append(f"anchor observed_frame exceeds decoded mux video for {audio_event_id}")
        if observed_time_seconds < 0.0 or observed_time_seconds >= mux_video_end_seconds:
            fail.append(f"anchor observed_time_seconds exceeds decoded mux timeline for {audio_event_id}")
        derived_frame = observed_time_seconds * float(event["frame_rate"])
        if abs(derived_frame - observed_frame) > max_anchor_frame_delta:
            fail.append(f"anchor observed_time_seconds/frame mismatch for {audio_event_id}")
        expected_owner_id = event["expected_owner_id"]
        if expected_owner_id is not None:
            observed_owner_id = _expect_non_empty_string(anchor["observed_owner_id"], f"anchors[{idx}].observed_owner_id")
            if observed_owner_id != expected_owner_id:
                fail.append(f"anchor observed_owner_id mismatch for {audio_event_id}")

    missing_ids = sorted(set(required_events.keys()) - seen_ids)
    if missing_ids:
        missing_count = len(missing_ids)
        for audio_event_id in missing_ids:
            fail.append(f"missing observed anchor for required audio_event_id: {audio_event_id}")
    return fail, blocked, producer_identity, {
        "required_anchor_event_count": len(required_events),
        "observed_anchor_count": len(anchors),
        "missing_anchor_count": missing_count,
        "extra_anchor_count": extra_count,
        "duplicate_anchor_count": duplicate_count,
    }


def _validate_optional_hash_bound_proof(
    payload: Any,
    label: str,
    *,
    expected_schema_name: str,
    expected_kind: str,
    run_id: str,
    scene_id: str,
    shot_id: str,
    take_id: str,
    is_synthetic: bool,
    evidence_origin: str,
    source_video_sha256: str,
    source_audio_sha256: str,
    mux_sha256: str,
    measurement_proof_sha256: str,
    allowlist: dict[tuple[str, str, str, str], ProducerIdentity],
    required_review_results: list[str],
    forbid_self_authorization: bool,
) -> tuple[list[str], list[str], ProducerIdentity | None]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "proof_kind",
            "engine",
            "model",
            "model_version",
            "model_sha256",
            "authority_id",
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "evidence_origin",
            "source_video_sha256",
            "source_audio_sha256",
            "mux_sha256",
            "measurement_proof_sha256",
            "review_results",
            "self_authorized",
        },
        label,
    )
    if payload["schema_name"] != expected_schema_name:
        raise InvalidInputError(f"{label}.schema_name mismatch")
    producer_identity, blocked = _validate_producer_identity(
        payload,
        label,
        expected_kind,
        allowlist,
        is_synthetic=is_synthetic,
        evidence_origin=evidence_origin,
    )
    fail: list[str] = []
    if payload["run_id"] != run_id:
        fail.append(f"{label} run_id mismatch")
    if payload["scene_id"] != scene_id:
        fail.append(f"{label} scene_id mismatch")
    if payload["shot_id"] != shot_id:
        fail.append(f"{label} shot_id mismatch")
    if payload["take_id"] != take_id:
        fail.append(f"{label} take_id mismatch")
    if _expect_bool(payload["is_synthetic"], f"{label}.is_synthetic") != is_synthetic:
        fail.append(f"{label} is_synthetic mismatch")
    if _expect_non_empty_string(payload["evidence_origin"], f"{label}.evidence_origin") != evidence_origin:
        fail.append(f"{label} evidence_origin mismatch")
    if payload["source_video_sha256"] != source_video_sha256:
        fail.append(f"{label} source_video_sha256 mismatch")
    if payload["source_audio_sha256"] != source_audio_sha256:
        fail.append(f"{label} source_audio_sha256 mismatch")
    if payload["mux_sha256"] != mux_sha256:
        fail.append(f"{label} mux_sha256 mismatch")
    if payload["measurement_proof_sha256"] != measurement_proof_sha256:
        fail.append(f"{label} measurement_proof_sha256 mismatch")
    review_results = payload["review_results"]
    if not isinstance(review_results, list) or not review_results:
        raise InvalidInputError(f"{label}.review_results must be a non-empty array")
    normalized = [_expect_non_empty_string(item, f"{label}.review_results[]") for item in review_results]
    for required in required_review_results:
        if required not in normalized:
            fail.append(f"{label} missing required review result: {required}")
    for result in normalized:
        if result != "PASS":
            fail.append(f"{label} contains non-PASS review result: {result}")
    self_authorized = _expect_bool(payload["self_authorized"], f"{label}.self_authorized")
    if forbid_self_authorization and self_authorized:
        fail.append(f"{label} self_authorized is forbidden")
    return fail, blocked, producer_identity


def _validate_production_bundle(
    payload: Any,
    *,
    run_id: str,
    scene_id: str,
    shot_id: str,
    take_id: str,
    is_synthetic: bool,
    evidence_origin: str,
    source_video_sha256: str,
    source_audio_sha256: str,
    mux_sha256: str,
    measurement_proof_sha256: str,
    playback_proof_sha256: str,
    runtime_proof_sha256: str,
    forbid_self_authorization: bool,
) -> tuple[str, str, list[str]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("production_certification_bundle must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "proof_kind",
            "bundle_version",
            "bundle_id",
            "authority_id",
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "evidence_origin",
            "source_video_sha256",
            "source_audio_sha256",
            "mux_sha256",
            "measurement_proof_sha256",
            "playback_proof_sha256",
            "runtime_proof_sha256",
            "self_authorized",
        },
        "production_certification_bundle",
    )
    if payload["schema_name"] != "wave64_av_sync_production_authority_bundle":
        raise InvalidInputError("production_certification_bundle.schema_name mismatch")
    if payload["proof_kind"] != "production_av_sync_authority":
        raise InvalidInputError("production_certification_bundle.proof_kind mismatch")
    if _expect_int(payload["bundle_version"], "production_certification_bundle.bundle_version", minimum=1) != 1:
        raise InvalidInputError("production_certification_bundle.bundle_version must be 1")
    bundle_id = _expect_non_empty_string(payload["bundle_id"], "production_certification_bundle.bundle_id")
    authority_id = _expect_non_empty_string(payload["authority_id"], "production_certification_bundle.authority_id")
    blockers: list[str] = []
    if payload["run_id"] != run_id:
        blockers.append("production_certification_bundle run_id mismatch")
    if payload["scene_id"] != scene_id:
        blockers.append("production_certification_bundle scene_id mismatch")
    if payload["shot_id"] != shot_id:
        blockers.append("production_certification_bundle shot_id mismatch")
    if payload["take_id"] != take_id:
        blockers.append("production_certification_bundle take_id mismatch")
    if _expect_bool(payload["is_synthetic"], "production_certification_bundle.is_synthetic") != is_synthetic:
        blockers.append("production_certification_bundle is_synthetic mismatch")
    if _expect_non_empty_string(payload["evidence_origin"], "production_certification_bundle.evidence_origin") != evidence_origin:
        blockers.append("production_certification_bundle evidence_origin mismatch")
    if payload["source_video_sha256"] != source_video_sha256:
        blockers.append("production_certification_bundle source_video_sha256 mismatch")
    if payload["source_audio_sha256"] != source_audio_sha256:
        blockers.append("production_certification_bundle source_audio_sha256 mismatch")
    if payload["mux_sha256"] != mux_sha256:
        blockers.append("production_certification_bundle mux_sha256 mismatch")
    if payload["measurement_proof_sha256"] != measurement_proof_sha256:
        blockers.append("production_certification_bundle measurement_proof_sha256 mismatch")
    if payload["playback_proof_sha256"] != playback_proof_sha256:
        blockers.append("production_certification_bundle playback_proof_sha256 mismatch")
    if payload["runtime_proof_sha256"] != runtime_proof_sha256:
        blockers.append("production_certification_bundle runtime_proof_sha256 mismatch")
    self_authorized = _expect_bool(payload["self_authorized"], "production_certification_bundle.self_authorized")
    if forbid_self_authorization and self_authorized:
        blockers.append("production_certification_bundle self_authorized is forbidden")
    return bundle_id, authority_id, blockers


def evaluate(root: Path, request_path: Path, output_path: Path) -> int:
    if av is None:
        raise InvalidInputError(f"PyAV is required but unavailable: {AV_IMPORT_ERROR}")

    request_schema = _load_json(root / REQUEST_SCHEMA_RELATIVE)
    report_schema = _load_json(root / REPORT_SCHEMA_RELATIVE)
    wave30_event_schema = _load_json(root / WAVE30_EVENT_SCHEMA_RELATIVE)
    wave30_mix_schema = _load_json(root / WAVE30_MIX_SCHEMA_RELATIVE)
    registry_binding = Binding(path=(root / GATE_RULES_RELATIVE).resolve(), sha256=_sha256_of((root / GATE_RULES_RELATIVE).resolve()))
    registry = _parse_gate_registry(_load_json(registry_binding.path))

    pyav_version = _expect_non_empty_string(getattr(av, "__version__", "unknown"), "pyav_version")
    if pyav_version not in registry["allowed_pyav_versions"]:
        raise InvalidInputError(
            f"PyAV version {pyav_version} is not allowlisted; allowed={registry['allowed_pyav_versions']}"
        )

    request_payload = _load_json(request_path)
    _validate_schema(request_payload, request_schema, "request")
    request_binding = Binding(path=request_path.resolve(), sha256=_sha256_of(request_path.resolve()))

    run_id = _expect_non_empty_string(request_payload["run_id"], "request.run_id")
    scene_id = _expect_non_empty_string(request_payload["scene_id"], "request.scene_id")
    shot_id = _expect_non_empty_string(request_payload["shot_id"], "request.shot_id")
    take_id = _expect_non_empty_string(request_payload["take_id"], "request.take_id")
    is_synthetic = _expect_bool(request_payload["is_synthetic"], "request.is_synthetic")
    evidence_origin = _expect_non_empty_string(request_payload["evidence_origin"], "request.evidence_origin")
    _expect_bool(request_payload["caller_claimed_overall_pass"], "request.caller_claimed_overall_pass")
    if is_synthetic and evidence_origin != "synthetic_fixture":
        raise InvalidInputError("request evidence_origin must be synthetic_fixture when is_synthetic=true")
    if not is_synthetic and evidence_origin == "synthetic_fixture":
        raise InvalidInputError("request evidence_origin synthetic_fixture requires is_synthetic=true")

    source_video_binding = _validate_path_sha_bytes_media_binding(
        root,
        request_payload["source_video_artifact"],
        "request.source_video_artifact",
        {"video/x-matroska"},
    )
    source_audio_binding = _validate_path_sha_bytes_media_binding(
        root,
        request_payload["source_audio_mix_artifact"],
        "request.source_audio_mix_artifact",
        {"audio/wav", "audio/x-wav"},
    )
    final_mux_binding = _validate_path_sha_bytes_media_binding(
        root,
        request_payload["final_mux_artifact"],
        "request.final_mux_artifact",
        {"video/x-matroska"},
    )
    wave30_event_binding = _validate_path_sha_binding(
        root, request_payload["wave30_event_manifest_binding"], "request.wave30_event_manifest_binding"
    )
    wave30_mix_binding = _validate_path_sha_binding(
        root, request_payload["wave30_mix_manifest_binding"], "request.wave30_mix_manifest_binding"
    )
    anchor_proof_binding = _validate_path_sha_binding(
        root,
        request_payload["observed_anchor_measurement_proof_binding"],
        "request.observed_anchor_measurement_proof_binding",
    )
    playback_binding = None
    if request_payload["playback_proof_binding"] is not None:
        playback_binding = _validate_path_sha_binding(root, request_payload["playback_proof_binding"], "request.playback_proof_binding")
    runtime_binding = None
    if request_payload["runtime_proof_binding"] is not None:
        runtime_binding = _validate_path_sha_binding(root, request_payload["runtime_proof_binding"], "request.runtime_proof_binding")
    production_bundle_binding = None
    if request_payload["production_certification_bundle_binding"] is not None:
        production_bundle_binding = _validate_path_sha_binding(
            root,
            request_payload["production_certification_bundle_binding"],
            "request.production_certification_bundle_binding",
        )

    wave30_event_manifest = _load_json(wave30_event_binding.path)
    wave30_mix_manifest = _load_json(wave30_mix_binding.path)
    _validate_schema(wave30_event_manifest, wave30_event_schema, "wave30_event_manifest")
    _validate_schema(wave30_mix_manifest, wave30_mix_schema, "wave30_mix_manifest")
    _validate_wave30_bindings(
        wave30_event_manifest,
        wave30_mix_manifest,
        run_id=run_id,
        scene_id=scene_id,
        shot_id=shot_id,
        is_synthetic=is_synthetic,
        event_binding=wave30_event_binding,
        source_audio_binding=source_audio_binding,
    )

    bound_paths: set[Path] = {
        request_binding.path,
        source_video_binding.path,
        source_audio_binding.path,
        final_mux_binding.path,
        wave30_event_binding.path,
        wave30_mix_binding.path,
        anchor_proof_binding.path,
        registry_binding.path,
    }
    if playback_binding is not None:
        bound_paths.add(playback_binding.path)
    if runtime_binding is not None:
        bound_paths.add(runtime_binding.path)
    if production_bundle_binding is not None:
        bound_paths.add(production_bundle_binding.path)
    if output_path in bound_paths:
        raise InvalidInputError("output path collides with request/artifact/proof binding path")

    source_video_metrics = _decode_video_container(source_video_binding.path, "source_video_artifact")
    mux_video_metrics = _decode_video_container(final_mux_binding.path, "final_mux_artifact(video)")
    source_audio_metrics = _read_wav_pcm(source_audio_binding.path, "source_audio_mix_artifact")
    mux_audio_metrics = _decode_mux_audio(
        final_mux_binding.path,
        "final_mux_artifact(audio)",
        target_rate=int(source_audio_metrics["sample_rate_hz"]),
    )

    sync_rules = registry["sync_rules"]
    mux_rules = registry["mux_rules"]
    producer_rules = registry["producer_rules"]
    required_events = _collect_required_anchor_events(wave30_event_manifest)

    gates: dict[str, dict[str, Any]] = {}
    all_blockers: list[str] = []

    # sync_offset_threshold
    offset_blockers: list[str] = []
    start_offset = float(mux_audio_metrics["first_pts_seconds"]) - float(mux_video_metrics["first_pts_seconds"])
    wave30_offset_fail, wave30_alignment_fail = _validate_wave30_sync_evidence(
        wave30_mix_manifest,
        required_events,
        mux_video_frame_rate=float(mux_video_metrics["frame_rate"]),
        mux_video_frame_count=int(mux_video_metrics["frame_count"]),
        observed_start_offset_seconds=start_offset,
        max_anchor_frame_delta=float(sync_rules["max_anchor_frame_delta"]),
    )
    offset_blockers.extend(wave30_offset_fail)
    if abs(start_offset) > float(sync_rules["max_start_offset_seconds"]):
        offset_blockers.append("audio/video start offset exceeds registry threshold")
    _append_pts_blockers(offset_blockers, "final_mux_video", mux_video_metrics)
    _append_pts_blockers(offset_blockers, "final_mux_audio", mux_audio_metrics)
    gates["sync_offset_threshold"] = _make_gate(
        PASS if not offset_blockers else FAIL,
        offset_blockers,
        [source_video_binding.sha256, source_audio_binding.sha256, final_mux_binding.sha256],
    )

    # drift_check
    drift_blockers: list[str] = []
    endpoint_delta = float(mux_audio_metrics["end_timestamp_seconds"]) - float(mux_video_metrics["end_timestamp_seconds"])
    cumulative_drift = endpoint_delta - start_offset
    if abs(cumulative_drift) > float(sync_rules["max_cumulative_endpoint_drift_seconds"]):
        drift_blockers.append("cumulative endpoint drift exceeds registry threshold")
    for label, payload in (
        ("source_video_artifact", source_video_metrics),
        ("final_mux_video", mux_video_metrics),
        ("final_mux_audio", mux_audio_metrics),
    ):
        _append_pts_blockers(drift_blockers, label, payload)
    gates["drift_check"] = _make_gate(
        PASS if not drift_blockers else FAIL,
        drift_blockers,
        [source_video_binding.sha256, final_mux_binding.sha256],
    )

    # mux_manifest
    mux_blockers: list[str] = []
    if source_video_metrics["container_format"] not in mux_rules["allowed_container_formats"]:
        mux_blockers.append("source video container format is not allowlisted")
    if mux_video_metrics["container_format"] not in mux_rules["allowed_container_formats"]:
        mux_blockers.append("mux container format is not allowlisted")
    if int(mux_video_metrics["stream_count_video"]) != int(mux_rules["required_video_stream_count"]):
        mux_blockers.append("mux video stream count mismatch")
    if int(mux_video_metrics["stream_count_audio"]) != int(mux_rules["required_audio_stream_count"]):
        mux_blockers.append("mux audio stream count mismatch")
    if mux_video_metrics["codec"] != mux_rules["required_video_codec"]:
        mux_blockers.append("mux video codec mismatch")
    if mux_audio_metrics["codec"] != mux_rules["required_audio_codec"]:
        mux_blockers.append("mux audio codec mismatch")
    if int(mux_audio_metrics["sample_rate_hz"]) != int(mux_rules["required_audio_sample_rate_hz"]):
        mux_blockers.append("mux audio sample rate mismatch")
    if int(mux_audio_metrics["channels"]) != int(mux_rules["required_audio_channels"]):
        mux_blockers.append("mux audio channel count mismatch")
    if mux_audio_metrics["channel_layout"] not in mux_rules["required_audio_layouts"]:
        mux_blockers.append("mux audio layout is not allowlisted")
    if int(source_audio_metrics["sample_width_bytes"]) != 2:
        mux_blockers.append("source audio mix must be PCM s16le")
    if int(source_audio_metrics["channels"]) != int(mux_rules["required_audio_channels"]):
        mux_blockers.append("source audio channel count mismatch against registry")
    if int(source_audio_metrics["sample_rate_hz"]) != int(mux_rules["required_audio_sample_rate_hz"]):
        mux_blockers.append("source audio sample rate mismatch against registry")
    video_hash_match = source_video_metrics["decoded_video_hash"] == mux_video_metrics["decoded_video_hash"]
    audio_hash_match = source_audio_metrics["decoded_audio_hash"] == mux_audio_metrics["decoded_audio_hash"]
    if not video_hash_match:
        mux_blockers.append("mux video decoded sequence hash mismatch against source video")
    if not audio_hash_match:
        mux_blockers.append("mux audio decoded sample hash mismatch against source audio")
    video_frame_count_match = int(source_video_metrics["frame_count"]) == int(mux_video_metrics["frame_count"])
    audio_sample_count_match = int(source_audio_metrics["sample_count"]) == int(mux_audio_metrics["sample_count"])
    if not video_frame_count_match:
        mux_blockers.append("mux video frame count mismatch against source video")
    if not audio_sample_count_match:
        mux_blockers.append("mux audio sample count mismatch against source audio")
    if source_video_binding.path == final_mux_binding.path:
        mux_blockers.append("source video and final mux paths must be distinct")
    if source_audio_binding.path == final_mux_binding.path:
        mux_blockers.append("source audio mix and final mux paths must be distinct")
    gates["mux_manifest"] = _make_gate(
        PASS if not mux_blockers else FAIL,
        mux_blockers,
        [source_video_binding.sha256, source_audio_binding.sha256, final_mux_binding.sha256],
    )

    # event_owner_alignment
    anchor_payload = _load_json(anchor_proof_binding.path)
    anchor_fail, anchor_blocked, measurement_producer, anchor_counts = _validate_anchor_measurement_proof(
        anchor_payload,
        run_id=run_id,
        scene_id=scene_id,
        shot_id=shot_id,
        take_id=take_id,
        is_synthetic=is_synthetic,
        evidence_origin=evidence_origin,
        source_video_sha256=source_video_binding.sha256,
        source_audio_sha256=source_audio_binding.sha256,
        mux_sha256=final_mux_binding.sha256,
        required_events=required_events,
        allowlist=producer_rules["measurement_allowlist"],
        max_anchor_frame_delta=float(sync_rules["max_anchor_frame_delta"]),
        mux_video_frame_count=int(mux_video_metrics["frame_count"]),
        mux_video_end_seconds=float(mux_video_metrics["end_timestamp_seconds"]),
    )
    anchor_fail.extend(wave30_alignment_fail)
    anchor_gate_blockers = anchor_fail + anchor_blocked
    anchor_status = _status_from_fail_and_blocked(anchor_fail, anchor_blocked)
    gates["event_owner_alignment"] = _make_gate(
        anchor_status,
        anchor_gate_blockers,
        [anchor_proof_binding.sha256, wave30_event_binding.sha256, wave30_mix_binding.sha256],
    )

    # av_review_record
    playback_producer_identity = None
    playback_blockers: list[str] = []
    if playback_binding is None:
        playback_status = BLOCKED
        playback_blockers.append("missing playback_proof_binding")
    else:
        playback_payload = _load_json(playback_binding.path)
        playback_fail, playback_blocked, playback_producer_identity = _validate_optional_hash_bound_proof(
            playback_payload,
            "playback_proof",
            expected_schema_name="wave64_av_sync_playback_proof",
            expected_kind="av_sync_playback_review",
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            source_video_sha256=source_video_binding.sha256,
            source_audio_sha256=source_audio_binding.sha256,
            mux_sha256=final_mux_binding.sha256,
            measurement_proof_sha256=anchor_proof_binding.sha256,
            allowlist=producer_rules["playback_allowlist"],
            required_review_results=producer_rules["required_review_results"],
            forbid_self_authorization=producer_rules["forbid_self_authorization"],
        )
        playback_blockers.extend(playback_fail)
        playback_blockers.extend(playback_blocked)
        playback_status = _status_from_fail_and_blocked(playback_fail, playback_blocked)
    gates["av_review_record"] = _make_gate(
        playback_status,
        playback_blockers,
        [playback_binding.sha256] if playback_binding is not None else [],
    )

    # production_runtime_proof
    runtime_producer_identity = None
    runtime_blockers: list[str] = []
    if runtime_binding is None:
        runtime_status = BLOCKED
        runtime_blockers.append("missing runtime_proof_binding")
    else:
        runtime_payload = _load_json(runtime_binding.path)
        runtime_fail, runtime_blocked, runtime_producer_identity = _validate_optional_hash_bound_proof(
            runtime_payload,
            "runtime_proof",
            expected_schema_name="wave64_production_runtime_proof",
            expected_kind="production_runtime",
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            source_video_sha256=source_video_binding.sha256,
            source_audio_sha256=source_audio_binding.sha256,
            mux_sha256=final_mux_binding.sha256,
            measurement_proof_sha256=anchor_proof_binding.sha256,
            allowlist=producer_rules["runtime_allowlist"],
            required_review_results=producer_rules["required_review_results"],
            forbid_self_authorization=producer_rules["forbid_self_authorization"],
        )
        runtime_blockers.extend(runtime_fail)
        runtime_blockers.extend(runtime_blocked)
        runtime_status = _status_from_fail_and_blocked(runtime_fail, runtime_blocked)
    if is_synthetic:
        runtime_status = BLOCKED
        runtime_blockers.append("synthetic input cannot satisfy production runtime proof gate")
    gates["production_runtime_proof"] = _make_gate(
        runtime_status,
        runtime_blockers,
        [runtime_binding.sha256] if runtime_binding is not None else [],
    )

    # production_av_sync_authority
    authority_blockers: list[str] = []
    prereq_names = (
        "sync_offset_threshold",
        "drift_check",
        "mux_manifest",
        "event_owner_alignment",
        "av_review_record",
        "production_runtime_proof",
    )
    failed_prereqs = [name for name in prereq_names if gates[name]["status"] == FAIL]
    blocked_prereqs = [name for name in prereq_names if gates[name]["status"] == BLOCKED]
    if is_synthetic:
        authority_status = BLOCKED
        authority_blockers.append("synthetic input cannot satisfy production AV sync authority")
    elif evidence_origin == "hand_authored_relabel":
        authority_status = BLOCKED
        authority_blockers.append("hand-authored relabel evidence cannot satisfy production AV sync authority")
    elif failed_prereqs:
        authority_status = FAIL
        authority_blockers.extend(f"upstream gate failed: {name}" for name in failed_prereqs)
    elif blocked_prereqs:
        authority_status = BLOCKED
        authority_blockers.extend(f"upstream gate blocked: {name}" for name in blocked_prereqs)
    elif production_bundle_binding is None:
        authority_status = BLOCKED
        authority_blockers.append("missing production_certification_bundle_binding")
    elif playback_binding is None or runtime_binding is None:
        authority_status = BLOCKED
        authority_blockers.append("production authority requires playback and runtime proofs")
    else:
        bundle_payload = _load_json(production_bundle_binding.path)
        bundle_id, authority_id, bundle_fail = _validate_production_bundle(
            bundle_payload,
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            source_video_sha256=source_video_binding.sha256,
            source_audio_sha256=source_audio_binding.sha256,
            mux_sha256=final_mux_binding.sha256,
            measurement_proof_sha256=anchor_proof_binding.sha256,
            playback_proof_sha256=playback_binding.sha256,
            runtime_proof_sha256=runtime_binding.sha256,
            forbid_self_authorization=producer_rules["forbid_self_authorization"],
        )
        authority_blockers.extend(bundle_fail)
        if bundle_fail:
            authority_status = FAIL
        else:
            allowlist_matches = [
                row
                for row in registry["production_rules"]["approved_certification_bundle_allowlist"]
                if row["bundle_id"] == bundle_id
                and row["authority_id"] == authority_id
                and row["bundle_sha256"] == production_bundle_binding.sha256
            ]
            if not allowlist_matches:
                authority_status = BLOCKED
                authority_blockers.append("production certification bundle is not allowlisted")
            elif any(bool(row["revoked"]) for row in allowlist_matches):
                authority_status = BLOCKED
                authority_blockers.append("production certification bundle is revoked")
            else:
                authority_status = PASS
    gates["production_av_sync_authority"] = _make_gate(
        authority_status,
        authority_blockers,
        [production_bundle_binding.sha256] if production_bundle_binding is not None else [],
    )

    for name in GATE_NAMES:
        if name == "overall_pass":
            continue
        all_blockers.extend(gates[name]["blockers"])
    overall_blockers = sorted(set(all_blockers))
    gate_statuses = [gates[name]["status"] for name in GATE_NAMES if name != "overall_pass"]
    if (not is_synthetic) and evidence_origin == "technical_capture" and all(status == PASS for status in gate_statuses):
        overall_status = PASS
        overall_pass = True
    elif any(status == FAIL for status in gate_statuses):
        overall_status = FAIL
        overall_pass = False
    else:
        overall_status = BLOCKED
        overall_pass = False
    gates["overall_pass"] = _make_gate(overall_status, overall_blockers, [request_binding.sha256])

    stream_count_match = (
        int(mux_video_metrics["stream_count_video"]) == int(mux_rules["required_video_stream_count"])
        and int(mux_video_metrics["stream_count_audio"]) == int(mux_rules["required_audio_stream_count"])
        and int(mux_audio_metrics["stream_count_audio"]) == int(mux_rules["required_audio_stream_count"])
    )
    report = {
        "schema_name": "wave64_av_sync_certification_report",
        "report_version": 1,
        "run_id": run_id,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "take_id": take_id,
        "is_synthetic": is_synthetic,
        "evidence_origin": evidence_origin,
        "pyav_version": pyav_version,
        "request_binding": {"path": str(request_binding.path), "sha256": request_binding.sha256},
        "artifact_bindings": {
            "source_video_artifact": {
                "path": str(source_video_binding.path),
                "sha256": source_video_binding.sha256,
                "bytes": source_video_binding.bytes,
            },
            "source_audio_mix_artifact": {
                "path": str(source_audio_binding.path),
                "sha256": source_audio_binding.sha256,
                "bytes": source_audio_binding.bytes,
            },
            "final_mux_artifact": {
                "path": str(final_mux_binding.path),
                "sha256": final_mux_binding.sha256,
                "bytes": final_mux_binding.bytes,
            },
            "wave30_event_manifest": _binding_or_none(wave30_event_binding),
            "wave30_mix_manifest": _binding_or_none(wave30_mix_binding),
            "observed_anchor_measurement_proof": _binding_or_none(anchor_proof_binding),
            "playback_proof": _binding_or_none(playback_binding),
            "runtime_proof": _binding_or_none(runtime_binding),
            "production_certification_bundle": _binding_or_none(production_bundle_binding),
            "wave64_gate_registry": _binding_or_none(registry_binding),
        },
        "metrics": {
            "source_video_decode": {k: v for k, v in source_video_metrics.items() if k != "end_timestamp_seconds"},
            "mux_video_decode": {k: v for k, v in mux_video_metrics.items() if k != "end_timestamp_seconds"},
            "source_audio_decode": {k: v for k, v in source_audio_metrics.items() if k not in {"sample_width_bytes", "frame_count", "end_timestamp_seconds"}},
            "mux_audio_decode": {k: v for k, v in mux_audio_metrics.items() if k != "end_timestamp_seconds"},
            "lineage": {
                "video_hash_match": video_hash_match,
                "audio_hash_match": audio_hash_match,
                "video_frame_count_match": video_frame_count_match,
                "audio_sample_count_match": audio_sample_count_match,
                "stream_count_match": stream_count_match,
                "video_codec_match": mux_video_metrics["codec"] == mux_rules["required_video_codec"],
                "audio_codec_match": mux_audio_metrics["codec"] == mux_rules["required_audio_codec"],
            },
            "sync": {
                "audio_start_offset_seconds": round(start_offset, 6),
                "endpoint_delta_seconds": round(endpoint_delta, 6),
                "cumulative_endpoint_drift_seconds": round(cumulative_drift, 6),
            },
            "anchors": {
                "required_anchor_event_count": anchor_counts["required_anchor_event_count"],
                "observed_anchor_count": anchor_counts["observed_anchor_count"],
                "missing_anchor_count": anchor_counts["missing_anchor_count"],
                "extra_anchor_count": anchor_counts["extra_anchor_count"],
                "duplicate_anchor_count": anchor_counts["duplicate_anchor_count"],
                "measurement_producer": _normalize_producer_for_report(measurement_producer),
            },
            "proofs": {
                "playback_producer": _normalize_producer_for_report(playback_producer_identity),
                "runtime_producer": _normalize_producer_for_report(runtime_producer_identity),
            },
        },
        "gates": gates,
        "blockers": overall_blockers,
        "overall_pass": overall_pass,
    }
    _validate_schema(report, report_schema, "report")
    _write_json_atomic(output_path, report)
    return 0 if overall_pass else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        requested_root = Path(args.root).resolve()
        if requested_root != CANONICAL_ROOT:
            raise InvalidInputError(f"root must match canonical project root ({CANONICAL_ROOT}); got {requested_root}")
        root = CANONICAL_ROOT
        request_path = _resolve_under_root(root, args.input, "input")
        output_path = _resolve_under_root(root, args.output, "output")
        return evaluate(root=root, request_path=request_path, output_path=output_path)
    except InvalidInputError as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: unexpected evaluator failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
