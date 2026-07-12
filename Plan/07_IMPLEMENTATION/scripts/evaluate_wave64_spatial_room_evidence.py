#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

GATE_NAMES = (
    "spatial_position_check",
    "room_reverb_check",
    "ambience_continuity",
    "mix_balance_review",
    "spatial_audio_playback_review",
    "production_runtime_proof",
    "production_spatial_room_authority",
    "overall_pass",
)

CANONICAL_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_spatial_room_evidence_bundle.schema.json")
REPORT_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_spatial_room_evaluator_report.schema.json")
WAVE64_GATE_RULES_RELATIVE = Path("Plan/10_REGISTRIES/wave64_spatial_room_gate_rules.json")
WAVE31_SPATIAL_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave31_spatial_audio_mix.schema.json")
WAVE31_ROOM_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave31_room_acoustics.schema.json")
WAVE31_SPATIAL_REGISTRY_RELATIVE = Path("Plan/10_REGISTRIES/wave31_spatial_audio_profiles.json")
WAVE31_ROOM_REGISTRY_RELATIVE = Path("Plan/10_REGISTRIES/wave31_room_acoustics_profiles.json")


class InvalidInputError(ValueError):
    pass


@dataclass(frozen=True)
class Binding:
    path: Path
    sha256: str
    bytes: int | None = None


@dataclass(frozen=True)
class HardCutApproval:
    cut_id: str
    reason: str
    approver_id: str
    approval_authority_id: str
    synthetic_only_approver: bool


@dataclass(frozen=True)
class ProofProducerAuthority:
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


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInputError(f"{label} must be boolean")
    return bool(value)


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_non_empty_string(value, label)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise InvalidInputError(f"{label} must be lowercase SHA-256")
    return sha


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


def _expect_ratio(value: Any, label: str) -> float:
    ratio = _expect_finite_number(value, label)
    if ratio < 0.0 or ratio > 1.0:
        raise InvalidInputError(f"{label} must be in [0, 1]")
    return ratio


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _db(value: float) -> float:
    floor = 1e-12
    return 20.0 * math.log10(max(value, floor))


def _distance3(a: dict[str, float], b: dict[str, float]) -> float:
    dx = float(a["x"]) - float(b["x"])
    dy = float(a["y"]) - float(b["y"])
    dz = float(a["z"]) - float(b["z"])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _resolve_under_root(root: Path, candidate: str, label: str) -> Path:
    raw = Path(candidate)
    resolved = (raw if raw.is_absolute() else (root / raw)).resolve()
    if not resolved.is_relative_to(root):
        raise InvalidInputError(f"{label} escapes root: {resolved}")
    return resolved


def _validate_binding(root: Path, payload: Any, label: str) -> Binding:
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


def _validate_path_sha_bytes(root: Path, payload: Any, label: str) -> Binding:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256", "bytes"}, label)
    path = _resolve_under_root(root, _expect_non_empty_string(payload["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(payload["sha256"], f"{label}.sha256")
    declared_bytes = _expect_int(payload["bytes"], f"{label}.bytes", minimum=1)
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed_bytes = path.stat().st_size
    if observed_bytes != declared_bytes:
        raise InvalidInputError(f"{label}.bytes mismatch ({declared_bytes} != {observed_bytes})")
    observed_sha = _sha256_of(path)
    if observed_sha != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return Binding(path=path, sha256=sha, bytes=declared_bytes)


def _decode_pcm(payload: bytes, sample_width: int) -> tuple[list[int], int]:
    if sample_width == 1:
        return [value - 128 for value in payload], 127
    if sample_width == 2:
        return [item[0] for item in struct.iter_unpack("<h", payload)], 32767
    if sample_width == 3:
        values: list[int] = []
        max_value = (1 << 23) - 1
        for idx in range(0, len(payload), 3):
            chunk = payload[idx : idx + 3]
            suffix = b"\xff" if chunk[2] & 0x80 else b"\x00"
            values.append(int.from_bytes(chunk + suffix, "little", signed=True))
        return values, max_value
    if sample_width == 4:
        return [item[0] for item in struct.iter_unpack("<i", payload)], (1 << 31) - 1
    raise InvalidInputError(f"unsupported sample width: {sample_width}")


def _estimate_rt60_and_tail(frame_levels: list[float], sample_rate: int) -> tuple[float, float]:
    if not frame_levels or sample_rate <= 0:
        return 0.0, 0.0
    window_size = max(1, int(sample_rate * 0.02))
    smoothed: list[float] = []
    for start in range(0, len(frame_levels), window_size):
        chunk = frame_levels[start : start + window_size]
        smoothed.append(sum(chunk) / float(len(chunk)))
    peak_idx = max(range(len(smoothed)), key=smoothed.__getitem__)
    peak_level = smoothed[peak_idx]
    if peak_level <= 0.0:
        return 0.0, 0.0
    target = peak_level * 0.001
    decay_idx = len(smoothed) - 1
    for idx in range(peak_idx, len(smoothed)):
        if smoothed[idx] <= target:
            decay_idx = idx
            break
    rt60 = max(0.0, (decay_idx - peak_idx) * window_size / float(sample_rate))
    tail = max(0.0, (len(smoothed) - peak_idx) * window_size / float(sample_rate))
    return round(rt60, 6), round(tail, 6)


def _read_wav_pcm(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            comp_type = handle.getcomptype()
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise InvalidInputError(f"malformed WAV at {path}: {exc}") from exc
    if comp_type != "NONE":
        raise InvalidInputError(f"non-PCM WAV is not allowed: {path}")
    if channels <= 0 or sample_rate <= 0 or frame_count <= 0:
        raise InvalidInputError(f"invalid WAV metrics in {path}")
    if sample_width not in (1, 2, 3, 4):
        raise InvalidInputError(f"unsupported sample width in {path}: {sample_width}")
    expected_size = frame_count * channels * sample_width
    if len(payload) != expected_size:
        raise InvalidInputError(f"WAV payload length mismatch in {path} ({len(payload)} != {expected_size})")

    samples, max_possible = _decode_pcm(payload, sample_width)
    if len(samples) != frame_count * channels:
        raise InvalidInputError(f"decoded sample count mismatch in {path}")
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "samples": samples,
        "max_possible": max_possible,
    }


def _read_wav_metrics(path: Path) -> dict[str, Any]:
    pcm_data = _read_wav_pcm(path)
    channels = int(pcm_data["channels"])
    sample_rate = int(pcm_data["sample_rate_hz"])
    sample_width = int(pcm_data["sample_width_bytes"])
    frame_count = int(pcm_data["frame_count"])
    samples = pcm_data["samples"]
    max_possible = int(pcm_data["max_possible"])

    channel_sum_squares = [0.0 for _ in range(channels)]
    channel_peaks = [0.0 for _ in range(channels)]
    clip_count = 0
    frame_levels: list[float] = []
    sum_squares_total = 0.0
    for frame_idx in range(frame_count):
        frame_level = 0.0
        for channel_idx in range(channels):
            sample = samples[frame_idx * channels + channel_idx]
            abs_sample = abs(sample)
            if abs_sample >= max_possible:
                clip_count += 1
            normalized = float(abs_sample) / float(max_possible)
            frame_level += normalized
            if normalized > channel_peaks[channel_idx]:
                channel_peaks[channel_idx] = normalized
            channel_sum_squares[channel_idx] += float(sample * sample)
            sum_squares_total += float(sample * sample)
        frame_levels.append(frame_level / float(channels))

    sample_total = frame_count * channels
    overall_rms = (
        0.0 if sample_total <= 0 else math.sqrt(sum_squares_total / float(sample_total)) / float(max_possible)
    )
    channel_rms = [
        0.0 if frame_count <= 0 else math.sqrt(value / float(frame_count)) / float(max_possible)
        for value in channel_sum_squares
    ]
    peak_ratio = max(channel_peaks) if channel_peaks else 0.0
    clipping_ratio = 0.0 if sample_total <= 0 else clip_count / float(sample_total)
    stereo_pan = 0.0
    if channels >= 2:
        left = channel_rms[0]
        right = channel_rms[1]
        denom = max(left + right, 1e-12)
        stereo_pan = _clamp((right - left) / denom, -1.0, 1.0)
    rt60_seconds, tail_seconds = _estimate_rt60_and_tail(frame_levels, sample_rate)
    return {
        "duration_seconds": round(frame_count / float(sample_rate), 6),
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "channels": channels,
        "frame_count": frame_count,
        "overall_rms_ratio": round(float(overall_rms), 6),
        "peak_ratio": round(float(peak_ratio), 6),
        "clipping_ratio": round(float(clipping_ratio), 6),
        "stereo_pan": round(float(stereo_pan), 6),
        "rt60_seconds": rt60_seconds,
        "reverb_tail_seconds": tail_seconds,
        "channel_rms_ratios": [round(float(value), 6) for value in channel_rms],
    }


def _normalize_hard_cut_approval_for_report(approval: HardCutApproval | None) -> dict[str, Any] | None:
    if approval is None:
        return None
    return {
        "cut_id": approval.cut_id,
        "reason": approval.reason,
        "approver_id": approval.approver_id,
        "approval_authority_id": approval.approval_authority_id,
        "synthetic_only_approver": approval.synthetic_only_approver,
    }


def _normalize_proof_producer_for_report(authority: ProofProducerAuthority | None) -> dict[str, Any] | None:
    if authority is None:
        return None
    return {
        "proof_kind": authority.proof_kind,
        "engine": authority.engine,
        "model": authority.model,
        "model_version": authority.model_version,
        "model_sha256": authority.model_sha256,
        "authority_id": authority.authority_id,
        "synthetic_only": authority.synthetic_only,
    }


def _compute_mix_reconstruction_residual_ratio(
    spatial_pcm: dict[str, Any],
    ambience_pcm: dict[str, Any],
    final_mix_pcm: dict[str, Any],
) -> tuple[bool, float]:
    aligned = (
        int(spatial_pcm["sample_rate_hz"]) == int(ambience_pcm["sample_rate_hz"]) == int(final_mix_pcm["sample_rate_hz"])
        and int(spatial_pcm["sample_width_bytes"])
        == int(ambience_pcm["sample_width_bytes"])
        == int(final_mix_pcm["sample_width_bytes"])
        and int(spatial_pcm["channels"]) == int(ambience_pcm["channels"]) == int(final_mix_pcm["channels"])
        and int(spatial_pcm["frame_count"]) == int(ambience_pcm["frame_count"]) == int(final_mix_pcm["frame_count"])
    )
    if not aligned:
        return False, 0.0
    max_possible = int(final_mix_pcm["max_possible"])
    if int(spatial_pcm["max_possible"]) != max_possible or int(ambience_pcm["max_possible"]) != max_possible:
        return False, 0.0
    spatial_samples = spatial_pcm["samples"]
    ambience_samples = ambience_pcm["samples"]
    final_samples = final_mix_pcm["samples"]
    total_samples = len(final_samples)
    if total_samples <= 0:
        return True, 0.0
    sum_abs_residual = 0.0
    sum_abs_expected = 0.0
    for idx in range(total_samples):
        expected = int(spatial_samples[idx]) + int(ambience_samples[idx])
        if expected > max_possible:
            expected = max_possible
        elif expected < -max_possible:
            expected = -max_possible
        observed = int(final_samples[idx])
        sum_abs_residual += abs(observed - expected) / float(max_possible)
        sum_abs_expected += abs(expected) / float(max_possible)
    mean_abs_residual = sum_abs_residual / float(total_samples)
    mean_abs_expected = sum_abs_expected / float(total_samples)
    normalized = mean_abs_residual / max(mean_abs_expected, 1e-12)
    return True, float(normalized)


def _binding_or_none(binding: Binding | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    return {"path": str(binding.path), "sha256": binding.sha256}


def _make_gate(status: str, blockers: list[str], artifact_bindings: list[str]) -> dict[str, Any]:
    if status == PASS and blockers:
        raise InvalidInputError("internal gate invariant: PASS gate cannot contain blockers")
    return {"status": status, "blockers": blockers, "artifact_bindings": artifact_bindings}


def _validate_wave31_schema(schema_payload: Any, label: str, required_schema_keys: set[str]) -> dict[str, Any]:
    if not isinstance(schema_payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(schema_payload, required_schema_keys, label)
    required_fields = schema_payload["required_fields"]
    if not isinstance(required_fields, list) or not required_fields:
        raise InvalidInputError(f"{label}.required_fields must be a non-empty array")
    for idx, field in enumerate(required_fields):
        _expect_non_empty_string(field, f"{label}.required_fields[{idx}]")
    return schema_payload


def _validate_wave31_manifest(payload: Any, schema_payload: dict[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    required_fields = schema_payload["required_fields"]
    for field in required_fields:
        if field not in payload:
            raise InvalidInputError(f"{label} missing required field: {field}")
    if "spatial_layer_fields" in schema_payload:
        expected_layer_fields = schema_payload["spatial_layer_fields"]
        layers = payload.get("spatial_layers")
        if not isinstance(layers, list) or not layers:
            raise InvalidInputError(f"{label}.spatial_layers must be a non-empty array")
        for layer_idx, layer in enumerate(layers):
            if not isinstance(layer, dict):
                raise InvalidInputError(f"{label}.spatial_layers[{layer_idx}] must be an object")
            for field in expected_layer_fields:
                if field not in layer:
                    raise InvalidInputError(f"{label}.spatial_layers[{layer_idx}] missing field: {field}")
    return payload


def _parse_wave31_room_registry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError("wave31_room_acoustics_profiles registry must be an object")
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise InvalidInputError("wave31_room_acoustics_profiles.profiles must be a non-empty array")
    by_id: dict[str, dict[str, Any]] = {}
    for idx, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            raise InvalidInputError(f"wave31_room_acoustics_profiles.profiles[{idx}] must be an object")
        profile_id = _expect_non_empty_string(profile.get("id"), f"wave31_room_acoustics_profiles.profiles[{idx}].id")
        reverb = _expect_non_empty_string(profile.get("reverb"), f"wave31_room_acoustics_profiles.profiles[{idx}].reverb")
        surfaces = profile.get("surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            raise InvalidInputError(f"wave31_room_acoustics_profiles.profiles[{idx}].surfaces must be a non-empty array")
        normalized_surfaces = {_expect_non_empty_string(item, f"surfaces[{idx}]").lower() for item in surfaces}
        by_id[profile_id] = {"reverb": reverb, "surfaces": normalized_surfaces}
    return by_id


def _parse_wave31_spatial_registry(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        raise InvalidInputError("wave31_spatial_audio_profiles registry must be an object")
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise InvalidInputError("wave31_spatial_audio_profiles.profiles must be a non-empty array")
    reverbs: set[str] = set()
    for idx, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            raise InvalidInputError(f"wave31_spatial_audio_profiles.profiles[{idx}] must be an object")
        reverb = profile.get("reverb")
        if isinstance(reverb, str) and reverb.strip():
            reverbs.add(reverb.strip())
    return reverbs


def _parse_wave64_gate_rules(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "registry_version",
            "spatial_rules",
            "room_rules",
            "ambience_rules",
            "mix_rules",
            "proof_rules",
            "production_rules",
        },
        "wave64_spatial_room_gate_rules",
    )
    if payload["schema_name"] != "wave64_spatial_room_gate_rules":
        raise InvalidInputError("wave64_spatial_room_gate_rules.schema_name mismatch")
    if _expect_int(payload["registry_version"], "wave64_spatial_room_gate_rules.registry_version", minimum=1) != 1:
        raise InvalidInputError("wave64_spatial_room_gate_rules.registry_version must be 1")

    spatial = payload["spatial_rules"]
    if not isinstance(spatial, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.spatial_rules must be an object")
    _expect_exact_keys(
        spatial,
        {
            "max_camera_listener_distance_delta",
            "max_pan_error",
            "min_attenuation_ratio",
            "max_attenuation_ratio",
            "max_source_listener_distance_meters",
        },
        "wave64_spatial_room_gate_rules.spatial_rules",
    )
    max_camera_listener_distance_delta = _expect_finite_number(
        spatial["max_camera_listener_distance_delta"], "spatial_rules.max_camera_listener_distance_delta"
    )
    max_pan_error = _expect_ratio(spatial["max_pan_error"], "spatial_rules.max_pan_error")
    min_attenuation_ratio = _expect_ratio(spatial["min_attenuation_ratio"], "spatial_rules.min_attenuation_ratio")
    max_attenuation_ratio = _expect_finite_number(spatial["max_attenuation_ratio"], "spatial_rules.max_attenuation_ratio")
    if max_attenuation_ratio < 0.0:
        raise InvalidInputError("spatial_rules.max_attenuation_ratio must be non-negative")
    if max_attenuation_ratio < min_attenuation_ratio:
        raise InvalidInputError("spatial_rules max_attenuation_ratio must be >= min_attenuation_ratio")
    max_distance = _expect_finite_number(
        spatial["max_source_listener_distance_meters"], "spatial_rules.max_source_listener_distance_meters"
    )
    if max_distance <= 0.0:
        raise InvalidInputError("spatial_rules.max_source_listener_distance_meters must be > 0")

    room = payload["room_rules"]
    if not isinstance(room, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.room_rules must be an object")
    _expect_exact_keys(
        room,
        {"known_reverb_profiles", "profile_rules", "max_reverb_tail_error_seconds"},
        "wave64_spatial_room_gate_rules.room_rules",
    )
    max_reverb_tail_error_seconds = _expect_finite_number(
        room["max_reverb_tail_error_seconds"],
        "room_rules.max_reverb_tail_error_seconds",
    )
    if max_reverb_tail_error_seconds < 0.0:
        raise InvalidInputError("room_rules.max_reverb_tail_error_seconds must be non-negative")
    known_reverb_profiles_raw = room["known_reverb_profiles"]
    if not isinstance(known_reverb_profiles_raw, list) or not known_reverb_profiles_raw:
        raise InvalidInputError("room_rules.known_reverb_profiles must be a non-empty array")
    known_reverb_profiles = {
        _expect_non_empty_string(item, "room_rules.known_reverb_profiles[]") for item in known_reverb_profiles_raw
    }
    profile_rules_raw = room["profile_rules"]
    if not isinstance(profile_rules_raw, list) or not profile_rules_raw:
        raise InvalidInputError("room_rules.profile_rules must be a non-empty array")
    profile_rules: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, item in enumerate(profile_rules_raw):
        if not isinstance(item, dict):
            raise InvalidInputError(f"room_rules.profile_rules[{idx}] must be an object")
        _expect_exact_keys(
            item,
            {"room_profile_id", "reverb_profile", "allowed_materials", "rt60_seconds_range", "tail_seconds_range"},
            f"room_rules.profile_rules[{idx}]",
        )
        profile_id = _expect_non_empty_string(item["room_profile_id"], f"room_rules.profile_rules[{idx}].room_profile_id")
        reverb_profile = _expect_non_empty_string(item["reverb_profile"], f"room_rules.profile_rules[{idx}].reverb_profile")
        allowed_materials_raw = item["allowed_materials"]
        if not isinstance(allowed_materials_raw, list) or not allowed_materials_raw:
            raise InvalidInputError(f"room_rules.profile_rules[{idx}].allowed_materials must be non-empty array")
        allowed_materials = {
            _expect_non_empty_string(material, f"room_rules.profile_rules[{idx}].allowed_materials[]").lower()
            for material in allowed_materials_raw
        }
        rt60_range_raw = item["rt60_seconds_range"]
        tail_range_raw = item["tail_seconds_range"]
        if not isinstance(rt60_range_raw, list) or len(rt60_range_raw) != 2:
            raise InvalidInputError(f"room_rules.profile_rules[{idx}].rt60_seconds_range must contain two values")
        if not isinstance(tail_range_raw, list) or len(tail_range_raw) != 2:
            raise InvalidInputError(f"room_rules.profile_rules[{idx}].tail_seconds_range must contain two values")
        rt60_min = _expect_finite_number(rt60_range_raw[0], f"room_rules.profile_rules[{idx}].rt60_seconds_range[0]")
        rt60_max = _expect_finite_number(rt60_range_raw[1], f"room_rules.profile_rules[{idx}].rt60_seconds_range[1]")
        tail_min = _expect_finite_number(tail_range_raw[0], f"room_rules.profile_rules[{idx}].tail_seconds_range[0]")
        tail_max = _expect_finite_number(tail_range_raw[1], f"room_rules.profile_rules[{idx}].tail_seconds_range[1]")
        if rt60_min < 0.0 or rt60_max < rt60_min:
            raise InvalidInputError(f"room_rules.profile_rules[{idx}] invalid rt60_seconds_range")
        if tail_min < 0.0 or tail_max < tail_min:
            raise InvalidInputError(f"room_rules.profile_rules[{idx}] invalid tail_seconds_range")
        key = (profile_id, reverb_profile)
        if key in profile_rules:
            raise InvalidInputError("duplicate room profile/reverb pair in gate rules registry")
        profile_rules[key] = {
            "allowed_materials": allowed_materials,
            "rt60_seconds_range": [rt60_min, rt60_max],
            "tail_seconds_range": [tail_min, tail_max],
        }

    ambience = payload["ambience_rules"]
    if not isinstance(ambience, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.ambience_rules must be an object")
    _expect_exact_keys(ambience, {"max_continuity_drift"}, "wave64_spatial_room_gate_rules.ambience_rules")
    max_continuity_drift = _expect_finite_number(ambience["max_continuity_drift"], "ambience_rules.max_continuity_drift")
    if max_continuity_drift < 0.0:
        raise InvalidInputError("ambience_rules.max_continuity_drift must be non-negative")

    mix = payload["mix_rules"]
    if not isinstance(mix, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.mix_rules must be an object")
    _expect_exact_keys(
        mix,
        {
            "min_dialogue_to_ambience_db",
            "max_clipping_ratio",
            "max_stereo_balance_delta",
            "max_mix_reconstruction_residual_ratio",
            "min_final_mix_energy_ratio",
            "max_final_mix_energy_ratio",
            "required_sample_rate_hz",
            "required_channels",
            "max_duration_delta_seconds",
        },
        "wave64_spatial_room_gate_rules.mix_rules",
    )
    min_dialogue_to_ambience_db = _expect_finite_number(mix["min_dialogue_to_ambience_db"], "mix_rules.min_dialogue_to_ambience_db")
    max_clipping_ratio = _expect_ratio(mix["max_clipping_ratio"], "mix_rules.max_clipping_ratio")
    max_stereo_balance_delta = _expect_ratio(mix["max_stereo_balance_delta"], "mix_rules.max_stereo_balance_delta")
    max_mix_reconstruction_residual_ratio = _expect_finite_number(
        mix["max_mix_reconstruction_residual_ratio"],
        "mix_rules.max_mix_reconstruction_residual_ratio",
    )
    if max_mix_reconstruction_residual_ratio < 0.0:
        raise InvalidInputError("mix_rules.max_mix_reconstruction_residual_ratio must be non-negative")
    min_final_mix_energy_ratio = _expect_finite_number(
        mix["min_final_mix_energy_ratio"],
        "mix_rules.min_final_mix_energy_ratio",
    )
    max_final_mix_energy_ratio = _expect_finite_number(
        mix["max_final_mix_energy_ratio"],
        "mix_rules.max_final_mix_energy_ratio",
    )
    if min_final_mix_energy_ratio < 0.0 or max_final_mix_energy_ratio < min_final_mix_energy_ratio:
        raise InvalidInputError("mix_rules final mix energy ratio range is invalid")
    required_sample_rate_hz = _expect_int(mix["required_sample_rate_hz"], "mix_rules.required_sample_rate_hz", minimum=1)
    required_channels = _expect_int(mix["required_channels"], "mix_rules.required_channels", minimum=1)
    max_duration_delta_seconds = _expect_finite_number(mix["max_duration_delta_seconds"], "mix_rules.max_duration_delta_seconds")
    if max_duration_delta_seconds < 0.0:
        raise InvalidInputError("mix_rules.max_duration_delta_seconds must be non-negative")

    proof = payload["proof_rules"]
    if not isinstance(proof, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.proof_rules must be an object")
    _expect_exact_keys(
        proof,
        {"required_review_results", "forbid_self_authorization", "hard_cut_approvers", "producer_allowlist"},
        "wave64_spatial_room_gate_rules.proof_rules",
    )
    required_review_results_raw = proof["required_review_results"]
    if not isinstance(required_review_results_raw, list) or not required_review_results_raw:
        raise InvalidInputError("proof_rules.required_review_results must be a non-empty array")
    required_review_results = [
        _expect_non_empty_string(item, "proof_rules.required_review_results[]") for item in required_review_results_raw
    ]
    forbid_self_authorization = _expect_bool(proof["forbid_self_authorization"], "proof_rules.forbid_self_authorization")
    hard_cut_approvers_raw = proof["hard_cut_approvers"]
    if not isinstance(hard_cut_approvers_raw, list) or not hard_cut_approvers_raw:
        raise InvalidInputError("proof_rules.hard_cut_approvers must be a non-empty array")
    hard_cut_approvers: dict[str, dict[str, Any]] = {}
    for idx, entry in enumerate(hard_cut_approvers_raw):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"proof_rules.hard_cut_approvers[{idx}] must be an object")
        _expect_exact_keys(
            entry,
            {"approver_id", "approval_authority_id", "allowed_reasons", "synthetic_only"},
            f"proof_rules.hard_cut_approvers[{idx}]",
        )
        approver_id = _expect_non_empty_string(entry["approver_id"], f"proof_rules.hard_cut_approvers[{idx}].approver_id")
        approval_authority_id = _expect_non_empty_string(
            entry["approval_authority_id"],
            f"proof_rules.hard_cut_approvers[{idx}].approval_authority_id",
        )
        allowed_reasons_raw = entry["allowed_reasons"]
        if not isinstance(allowed_reasons_raw, list) or not allowed_reasons_raw:
            raise InvalidInputError(f"proof_rules.hard_cut_approvers[{idx}].allowed_reasons must be non-empty array")
        allowed_reasons = {
            _expect_non_empty_string(reason, f"proof_rules.hard_cut_approvers[{idx}].allowed_reasons[]")
            for reason in allowed_reasons_raw
        }
        synthetic_only = _expect_bool(entry["synthetic_only"], f"proof_rules.hard_cut_approvers[{idx}].synthetic_only")
        if approver_id in hard_cut_approvers:
            raise InvalidInputError("duplicate hard-cut approver id in proof rules")
        hard_cut_approvers[approver_id] = {
            "approval_authority_id": approval_authority_id,
            "allowed_reasons": allowed_reasons,
            "synthetic_only": synthetic_only,
        }

    producer_allowlist_raw = proof["producer_allowlist"]
    if not isinstance(producer_allowlist_raw, list) or not producer_allowlist_raw:
        raise InvalidInputError("proof_rules.producer_allowlist must be a non-empty array")
    producer_allowlist: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for idx, entry in enumerate(producer_allowlist_raw):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"proof_rules.producer_allowlist[{idx}] must be an object")
        _expect_exact_keys(
            entry,
            {"proof_kind", "engine", "model", "model_version", "model_sha256", "authority_id", "synthetic_only"},
            f"proof_rules.producer_allowlist[{idx}]",
        )
        proof_kind = _expect_non_empty_string(entry["proof_kind"], f"proof_rules.producer_allowlist[{idx}].proof_kind")
        if proof_kind not in {"spatial_audio_playback_review", "production_runtime"}:
            raise InvalidInputError(f"proof_rules.producer_allowlist[{idx}].proof_kind is unsupported")
        engine = _expect_non_empty_string(entry["engine"], f"proof_rules.producer_allowlist[{idx}].engine")
        model = _expect_non_empty_string(entry["model"], f"proof_rules.producer_allowlist[{idx}].model")
        model_version = _expect_non_empty_string(
            entry["model_version"],
            f"proof_rules.producer_allowlist[{idx}].model_version",
        )
        model_sha256 = _expect_sha256(entry["model_sha256"], f"proof_rules.producer_allowlist[{idx}].model_sha256")
        authority_id = _expect_non_empty_string(
            entry["authority_id"],
            f"proof_rules.producer_allowlist[{idx}].authority_id",
        )
        synthetic_only = _expect_bool(entry["synthetic_only"], f"proof_rules.producer_allowlist[{idx}].synthetic_only")
        key = (proof_kind, engine, model, model_version, model_sha256)
        if key in producer_allowlist:
            raise InvalidInputError("duplicate producer allowlist record in proof rules")
        producer_allowlist[key] = {
            "authority_id": authority_id,
            "synthetic_only": synthetic_only,
        }

    production = payload["production_rules"]
    if not isinstance(production, dict):
        raise InvalidInputError("wave64_spatial_room_gate_rules.production_rules must be an object")
    _expect_exact_keys(
        production, {"approved_bundle_allowlist"}, "wave64_spatial_room_gate_rules.production_rules"
    )
    allowlist_raw = production["approved_bundle_allowlist"]
    if not isinstance(allowlist_raw, list):
        raise InvalidInputError("production_rules.approved_bundle_allowlist must be an array")
    allowlist: list[dict[str, Any]] = []
    for idx, entry in enumerate(allowlist_raw):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"production_rules.approved_bundle_allowlist[{idx}] must be an object")
        _expect_exact_keys(
            entry,
            {"bundle_id", "authority_id", "bundle_sha256", "revoked"},
            f"production_rules.approved_bundle_allowlist[{idx}]",
        )
        allowlist.append(
            {
                "bundle_id": _expect_non_empty_string(
                    entry["bundle_id"], f"production_rules.approved_bundle_allowlist[{idx}].bundle_id"
                ),
                "authority_id": _expect_non_empty_string(
                    entry["authority_id"], f"production_rules.approved_bundle_allowlist[{idx}].authority_id"
                ),
                "bundle_sha256": _expect_sha256(
                    entry["bundle_sha256"], f"production_rules.approved_bundle_allowlist[{idx}].bundle_sha256"
                ),
                "revoked": _expect_bool(entry["revoked"], f"production_rules.approved_bundle_allowlist[{idx}].revoked"),
            }
        )

    return {
        "spatial_rules": {
            "max_camera_listener_distance_delta": max_camera_listener_distance_delta,
            "max_pan_error": max_pan_error,
            "min_attenuation_ratio": min_attenuation_ratio,
            "max_attenuation_ratio": max_attenuation_ratio,
            "max_source_listener_distance_meters": max_distance,
        },
        "room_rules": {
            "known_reverb_profiles": known_reverb_profiles,
            "profile_rules": profile_rules,
            "max_reverb_tail_error_seconds": max_reverb_tail_error_seconds,
        },
        "ambience_rules": {
            "max_continuity_drift": max_continuity_drift,
        },
        "mix_rules": {
            "min_dialogue_to_ambience_db": min_dialogue_to_ambience_db,
            "max_clipping_ratio": max_clipping_ratio,
            "max_stereo_balance_delta": max_stereo_balance_delta,
            "max_mix_reconstruction_residual_ratio": max_mix_reconstruction_residual_ratio,
            "min_final_mix_energy_ratio": min_final_mix_energy_ratio,
            "max_final_mix_energy_ratio": max_final_mix_energy_ratio,
            "required_sample_rate_hz": required_sample_rate_hz,
            "required_channels": required_channels,
            "max_duration_delta_seconds": max_duration_delta_seconds,
        },
        "proof_rules": {
            "required_review_results": required_review_results,
            "forbid_self_authorization": forbid_self_authorization,
            "hard_cut_approvers": hard_cut_approvers,
            "producer_allowlist": producer_allowlist,
        },
        "production_rules": {
            "approved_bundle_allowlist": allowlist,
        },
    }


def _validate_position(payload: Any, label: str) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"x", "y", "z"}, label)
    return {
        "x": _expect_finite_number(payload["x"], f"{label}.x"),
        "y": _expect_finite_number(payload["y"], f"{label}.y"),
        "z": _expect_finite_number(payload["z"], f"{label}.z"),
    }


def _dot3(a: dict[str, float], b: dict[str, float]) -> float:
    return float(a["x"]) * float(b["x"]) + float(a["y"]) * float(b["y"]) + float(a["z"]) * float(b["z"])


def _vector_norm3(vector: dict[str, float]) -> float:
    return math.sqrt(_dot3(vector, vector))


def _validate_unit_vector(payload: Any, label: str) -> dict[str, float]:
    vector = _validate_position(payload, label)
    norm = _vector_norm3(vector)
    if norm <= 1e-9:
        raise InvalidInputError(f"{label} must be non-degenerate")
    if abs(norm - 1.0) > 1e-3:
        raise InvalidInputError(f"{label} must be a unit vector")
    return vector


def _validate_camera_orientation(payload: Any) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("camera_orientation must be an object")
    _expect_exact_keys(payload, {"right_unit_vector", "forward_unit_vector"}, "camera_orientation")
    right_unit_vector = _validate_unit_vector(payload["right_unit_vector"], "camera_orientation.right_unit_vector")
    forward_unit_vector = _validate_unit_vector(payload["forward_unit_vector"], "camera_orientation.forward_unit_vector")
    if abs(_dot3(right_unit_vector, forward_unit_vector)) > 1e-3:
        raise InvalidInputError("camera_orientation right and forward vectors must be orthogonal")
    return {
        "right_unit_vector": right_unit_vector,
        "forward_unit_vector": forward_unit_vector,
    }


def _validate_thresholds(payload: Any) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise InvalidInputError("threshold_overrides must be an object")
    _expect_exact_keys(
        payload,
        {
            "max_camera_listener_distance_delta",
            "max_pan_error",
            "min_attenuation_ratio",
            "max_attenuation_ratio",
            "min_rt60_seconds",
            "max_rt60_seconds",
            "max_reverb_tail_error_seconds",
            "max_ambience_drift",
            "min_dialogue_to_ambience_db",
            "max_clipping_ratio",
            "max_stereo_balance_delta",
            "max_duration_delta_seconds",
        },
        "threshold_overrides",
    )
    thresholds = {
        "max_camera_listener_distance_delta": _expect_finite_number(
            payload["max_camera_listener_distance_delta"], "threshold_overrides.max_camera_listener_distance_delta"
        ),
        "max_pan_error": _expect_ratio(payload["max_pan_error"], "threshold_overrides.max_pan_error"),
        "min_attenuation_ratio": _expect_ratio(
            payload["min_attenuation_ratio"], "threshold_overrides.min_attenuation_ratio"
        ),
        "max_attenuation_ratio": _expect_finite_number(
            payload["max_attenuation_ratio"], "threshold_overrides.max_attenuation_ratio"
        ),
        "min_rt60_seconds": _expect_finite_number(payload["min_rt60_seconds"], "threshold_overrides.min_rt60_seconds"),
        "max_rt60_seconds": _expect_finite_number(payload["max_rt60_seconds"], "threshold_overrides.max_rt60_seconds"),
        "max_reverb_tail_error_seconds": _expect_finite_number(
            payload["max_reverb_tail_error_seconds"], "threshold_overrides.max_reverb_tail_error_seconds"
        ),
        "max_ambience_drift": _expect_finite_number(payload["max_ambience_drift"], "threshold_overrides.max_ambience_drift"),
        "min_dialogue_to_ambience_db": _expect_finite_number(
            payload["min_dialogue_to_ambience_db"], "threshold_overrides.min_dialogue_to_ambience_db"
        ),
        "max_clipping_ratio": _expect_ratio(payload["max_clipping_ratio"], "threshold_overrides.max_clipping_ratio"),
        "max_stereo_balance_delta": _expect_ratio(
            payload["max_stereo_balance_delta"], "threshold_overrides.max_stereo_balance_delta"
        ),
        "max_duration_delta_seconds": _expect_finite_number(
            payload["max_duration_delta_seconds"], "threshold_overrides.max_duration_delta_seconds"
        ),
    }
    if thresholds["max_camera_listener_distance_delta"] < 0.0:
        raise InvalidInputError("threshold_overrides.max_camera_listener_distance_delta must be non-negative")
    if thresholds["max_attenuation_ratio"] < 0.0:
        raise InvalidInputError("threshold_overrides.max_attenuation_ratio must be non-negative")
    if thresholds["max_attenuation_ratio"] < thresholds["min_attenuation_ratio"]:
        raise InvalidInputError("threshold_overrides max_attenuation_ratio must be >= min_attenuation_ratio")
    if thresholds["min_rt60_seconds"] < 0.0 or thresholds["max_rt60_seconds"] < thresholds["min_rt60_seconds"]:
        raise InvalidInputError("threshold_overrides RT60 range is invalid")
    if thresholds["max_reverb_tail_error_seconds"] < 0.0:
        raise InvalidInputError("threshold_overrides.max_reverb_tail_error_seconds must be non-negative")
    if thresholds["max_ambience_drift"] < 0.0:
        raise InvalidInputError("threshold_overrides.max_ambience_drift must be non-negative")
    if thresholds["max_duration_delta_seconds"] < 0.0:
        raise InvalidInputError("threshold_overrides.max_duration_delta_seconds must be non-negative")
    return thresholds


def _validate_hard_cut_contract(payload: Any) -> dict[str, str] | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise InvalidInputError("ambience_continuity_evidence.hard_cut_contract must be an object or null")
    _expect_exact_keys(payload, {"cut_id", "reason", "approver_id"}, "ambience_continuity_evidence.hard_cut_contract")
    return {
        "cut_id": _expect_non_empty_string(payload["cut_id"], "hard_cut_contract.cut_id"),
        "reason": _expect_non_empty_string(payload["reason"], "hard_cut_contract.reason"),
        "approver_id": _expect_non_empty_string(payload["approver_id"], "hard_cut_contract.approver_id"),
    }


def _resolve_hard_cut_approval(
    hard_cut_contract: dict[str, str] | None,
    *,
    hard_cut_approvers: dict[str, dict[str, Any]],
    is_synthetic: bool,
) -> tuple[HardCutApproval | None, list[str]]:
    if hard_cut_contract is None:
        return None, []
    approver_id = hard_cut_contract["approver_id"]
    if approver_id not in hard_cut_approvers:
        return None, [f"hard-cut approver is not allowlisted: {approver_id}"]
    approver_record = hard_cut_approvers[approver_id]
    reason = hard_cut_contract["reason"]
    blockers: list[str] = []
    if reason not in approver_record["allowed_reasons"]:
        blockers.append(f"hard-cut reason is not allowlisted for approver: {reason}")
    synthetic_only = bool(approver_record["synthetic_only"])
    if synthetic_only and not is_synthetic:
        blockers.append("hard-cut approver is synthetic-only and cannot approve non-synthetic bundles")
    approval = HardCutApproval(
        cut_id=hard_cut_contract["cut_id"],
        reason=reason,
        approver_id=approver_id,
        approval_authority_id=str(approver_record["approval_authority_id"]),
        synthetic_only_approver=synthetic_only,
    )
    return approval, blockers


def _validate_optional_proof(
    payload: Any,
    label: str,
    *,
    expected_schema_name: str,
    expected_proof_kind: str,
    run_id: str,
    scene_id: str,
    shot_id: str,
    take_id: str,
    is_synthetic: bool,
    evidence_origin: str,
    dry_dialogue_sha: str,
    spatial_dialogue_sha: str,
    ambience_bed_sha: str,
    final_mix_sha: str,
    required_review_results: list[str],
    forbid_self_authorization: bool,
    producer_allowlist: dict[tuple[str, str, str, str, str], dict[str, Any]],
) -> tuple[list[str], list[str], ProofProducerAuthority | None]:
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
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "evidence_origin",
            "artifact_hashes",
            "review_results",
            "self_authorized",
        },
        label,
    )
    if payload["schema_name"] != expected_schema_name:
        raise InvalidInputError(f"{label}.schema_name mismatch")
    if payload["proof_kind"] != expected_proof_kind:
        raise InvalidInputError(f"{label}.proof_kind mismatch")
    engine = _expect_non_empty_string(payload["engine"], f"{label}.engine")
    model = _expect_non_empty_string(payload["model"], f"{label}.model")
    model_version = _expect_non_empty_string(payload["model_version"], f"{label}.model_version")
    model_sha256 = _expect_sha256(payload["model_sha256"], f"{label}.model_sha256")
    fail_blockers: list[str] = []
    blocked_blockers: list[str] = []
    allowlist_key = (expected_proof_kind, engine, model, model_version, model_sha256)
    producer_authority = None
    if allowlist_key not in producer_allowlist:
        blocked_blockers.append(f"{label} producer is not allowlisted")
    else:
        producer_record = producer_allowlist[allowlist_key]
        producer_authority = ProofProducerAuthority(
            proof_kind=expected_proof_kind,
            engine=engine,
            model=model,
            model_version=model_version,
            model_sha256=model_sha256,
            authority_id=str(producer_record["authority_id"]),
            synthetic_only=bool(producer_record["synthetic_only"]),
        )
        if producer_authority.synthetic_only and not is_synthetic:
            blocked_blockers.append(f"{label} producer authority is synthetic-only for non-synthetic evidence")
    if payload["run_id"] != run_id:
        fail_blockers.append(f"{label} run_id mismatch")
    if payload["scene_id"] != scene_id:
        fail_blockers.append(f"{label} scene_id mismatch")
    if payload["shot_id"] != shot_id:
        fail_blockers.append(f"{label} shot_id mismatch")
    if payload["take_id"] != take_id:
        fail_blockers.append(f"{label} take_id mismatch")
    if _expect_bool(payload["is_synthetic"], f"{label}.is_synthetic") != is_synthetic:
        fail_blockers.append(f"{label} is_synthetic mismatch")
    if _expect_non_empty_string(payload["evidence_origin"], f"{label}.evidence_origin") != evidence_origin:
        fail_blockers.append(f"{label} evidence_origin mismatch")
    artifact_hashes = payload["artifact_hashes"]
    if not isinstance(artifact_hashes, dict):
        raise InvalidInputError(f"{label}.artifact_hashes must be an object")
    _expect_exact_keys(
        artifact_hashes,
        {"dry_dialogue_sha256", "spatial_dialogue_sha256", "ambience_bed_sha256", "final_mix_sha256"},
        f"{label}.artifact_hashes",
    )
    if artifact_hashes["dry_dialogue_sha256"] != dry_dialogue_sha:
        fail_blockers.append(f"{label} dry_dialogue hash mismatch")
    if artifact_hashes["spatial_dialogue_sha256"] != spatial_dialogue_sha:
        fail_blockers.append(f"{label} spatial_dialogue hash mismatch")
    if artifact_hashes["ambience_bed_sha256"] != ambience_bed_sha:
        fail_blockers.append(f"{label} ambience_bed hash mismatch")
    if artifact_hashes["final_mix_sha256"] != final_mix_sha:
        fail_blockers.append(f"{label} final_mix hash mismatch")
    review_results = payload["review_results"]
    if not isinstance(review_results, list) or not review_results:
        raise InvalidInputError(f"{label}.review_results must be a non-empty array")
    normalized_results = [_expect_non_empty_string(item, f"{label}.review_results[]") for item in review_results]
    for required in required_review_results:
        if required not in normalized_results:
            fail_blockers.append(f"{label} missing required review result: {required}")
    for result in normalized_results:
        if result != "PASS":
            fail_blockers.append(f"{label} contains non-PASS review result: {result}")
    self_authorized = _expect_bool(payload["self_authorized"], f"{label}.self_authorized")
    if forbid_self_authorization and self_authorized:
        fail_blockers.append(f"{label} self_authorized is forbidden")
    return fail_blockers, blocked_blockers, producer_authority


def _validate_production_bundle(
    payload: Any,
    *,
    run_id: str,
    scene_id: str,
    shot_id: str,
    take_id: str,
    is_synthetic: bool,
    evidence_origin: str,
    playback_binding: Binding,
    runtime_binding: Binding,
    dry_dialogue_sha: str,
    spatial_dialogue_sha: str,
    ambience_bed_sha: str,
    final_mix_sha: str,
    forbid_self_authorization: bool,
) -> tuple[str, str, list[str]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("production_authority_bundle must be an object")
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
            "playback_proof_sha256",
            "runtime_proof_sha256",
            "artifact_hashes",
            "self_authorized",
        },
        "production_authority_bundle",
    )
    if payload["schema_name"] != "wave64_production_spatial_room_authority_bundle":
        raise InvalidInputError("production_authority_bundle.schema_name mismatch")
    if payload["proof_kind"] != "production_spatial_room_authority":
        raise InvalidInputError("production_authority_bundle.proof_kind mismatch")
    if _expect_int(payload["bundle_version"], "production_authority_bundle.bundle_version", minimum=1) != 1:
        raise InvalidInputError("production_authority_bundle.bundle_version must be 1")
    bundle_id = _expect_non_empty_string(payload["bundle_id"], "production_authority_bundle.bundle_id")
    authority_id = _expect_non_empty_string(payload["authority_id"], "production_authority_bundle.authority_id")
    blockers: list[str] = []
    if payload["run_id"] != run_id:
        blockers.append("production_authority_bundle run_id mismatch")
    if payload["scene_id"] != scene_id:
        blockers.append("production_authority_bundle scene_id mismatch")
    if payload["shot_id"] != shot_id:
        blockers.append("production_authority_bundle shot_id mismatch")
    if payload["take_id"] != take_id:
        blockers.append("production_authority_bundle take_id mismatch")
    if _expect_bool(payload["is_synthetic"], "production_authority_bundle.is_synthetic") != is_synthetic:
        blockers.append("production_authority_bundle is_synthetic mismatch")
    if _expect_non_empty_string(payload["evidence_origin"], "production_authority_bundle.evidence_origin") != evidence_origin:
        blockers.append("production_authority_bundle evidence_origin mismatch")
    if payload["playback_proof_sha256"] != playback_binding.sha256:
        blockers.append("production_authority_bundle playback proof hash mismatch")
    if payload["runtime_proof_sha256"] != runtime_binding.sha256:
        blockers.append("production_authority_bundle runtime proof hash mismatch")
    artifact_hashes = payload["artifact_hashes"]
    if not isinstance(artifact_hashes, dict):
        raise InvalidInputError("production_authority_bundle.artifact_hashes must be an object")
    _expect_exact_keys(
        artifact_hashes,
        {"dry_dialogue_sha256", "spatial_dialogue_sha256", "ambience_bed_sha256", "final_mix_sha256"},
        "production_authority_bundle.artifact_hashes",
    )
    if artifact_hashes["dry_dialogue_sha256"] != dry_dialogue_sha:
        blockers.append("production_authority_bundle dry_dialogue hash mismatch")
    if artifact_hashes["spatial_dialogue_sha256"] != spatial_dialogue_sha:
        blockers.append("production_authority_bundle spatial_dialogue hash mismatch")
    if artifact_hashes["ambience_bed_sha256"] != ambience_bed_sha:
        blockers.append("production_authority_bundle ambience_bed hash mismatch")
    if artifact_hashes["final_mix_sha256"] != final_mix_sha:
        blockers.append("production_authority_bundle final_mix hash mismatch")
    self_authorized = _expect_bool(payload["self_authorized"], "production_authority_bundle.self_authorized")
    if forbid_self_authorization and self_authorized:
        blockers.append("production_authority_bundle self_authorized is forbidden")
    return bundle_id, authority_id, blockers


def evaluate(root: Path, request_path: Path, output_path: Path) -> int:
    bundle_schema = _load_json(root / BUNDLE_SCHEMA_RELATIVE)
    report_schema = _load_json(root / REPORT_SCHEMA_RELATIVE)
    wave31_spatial_schema = _validate_wave31_schema(
        _load_json(root / WAVE31_SPATIAL_SCHEMA_RELATIVE),
        "wave31_spatial_audio_mix_schema",
        {"schema_name", "required_fields", "spatial_layer_fields"},
    )
    wave31_room_schema = _validate_wave31_schema(
        _load_json(root / WAVE31_ROOM_SCHEMA_RELATIVE),
        "wave31_room_acoustics_schema",
        {"schema_name", "required_fields"},
    )
    wave31_spatial_registry_reverbs = _parse_wave31_spatial_registry(_load_json(root / WAVE31_SPATIAL_REGISTRY_RELATIVE))
    wave31_room_registry = _parse_wave31_room_registry(_load_json(root / WAVE31_ROOM_REGISTRY_RELATIVE))
    gate_rules_binding = Binding(
        path=(root / WAVE64_GATE_RULES_RELATIVE).resolve(),
        sha256=_sha256_of((root / WAVE64_GATE_RULES_RELATIVE).resolve()),
    )
    gate_rules = _parse_wave64_gate_rules(_load_json(gate_rules_binding.path))

    request_payload = _load_json(request_path)
    _validate_schema(request_payload, bundle_schema, "request")
    request_binding = Binding(path=request_path.resolve(), sha256=_sha256_of(request_path.resolve()))

    run_id = _expect_non_empty_string(request_payload["run_id"], "request.run_id")
    scene_id = _expect_non_empty_string(request_payload["scene_id"], "request.scene_id")
    shot_id = _expect_non_empty_string(request_payload["shot_id"], "request.shot_id")
    take_id = _expect_non_empty_string(request_payload["take_id"], "request.take_id")
    is_synthetic = _expect_bool(request_payload["is_synthetic"], "request.is_synthetic")
    evidence_origin = _expect_non_empty_string(request_payload["evidence_origin"], "request.evidence_origin")
    if is_synthetic and evidence_origin != "synthetic_fixture":
        raise InvalidInputError("request evidence_origin must be synthetic_fixture when is_synthetic is true")
    if not is_synthetic and evidence_origin == "synthetic_fixture":
        raise InvalidInputError("request evidence_origin synthetic_fixture requires is_synthetic true")
    if evidence_origin == "hand_authored_relabel" and is_synthetic:
        raise InvalidInputError("hand_authored_relabel evidence cannot be marked synthetic")

    listener_position = _validate_position(request_payload["listener_position"], "request.listener_position")
    camera_position = _validate_position(request_payload["camera_position"], "request.camera_position")
    camera_orientation = _validate_camera_orientation(request_payload["camera_orientation"])
    source_position = _validate_position(request_payload["source_position"], "request.source_position")

    threshold_overrides = _validate_thresholds(request_payload["threshold_overrides"])
    thresholds = {
        "max_camera_listener_distance_delta": min(
            threshold_overrides["max_camera_listener_distance_delta"],
            gate_rules["spatial_rules"]["max_camera_listener_distance_delta"],
        ),
        "max_pan_error": min(threshold_overrides["max_pan_error"], gate_rules["spatial_rules"]["max_pan_error"]),
        "min_attenuation_ratio": max(
            threshold_overrides["min_attenuation_ratio"], gate_rules["spatial_rules"]["min_attenuation_ratio"]
        ),
        "max_attenuation_ratio": min(
            threshold_overrides["max_attenuation_ratio"], gate_rules["spatial_rules"]["max_attenuation_ratio"]
        ),
        "min_rt60_seconds": threshold_overrides["min_rt60_seconds"],
        "max_rt60_seconds": threshold_overrides["max_rt60_seconds"],
        "max_reverb_tail_error_seconds": min(
            threshold_overrides["max_reverb_tail_error_seconds"],
            gate_rules["room_rules"]["max_reverb_tail_error_seconds"],
        ),
        "max_ambience_drift": min(
            threshold_overrides["max_ambience_drift"], gate_rules["ambience_rules"]["max_continuity_drift"]
        ),
        "min_dialogue_to_ambience_db": max(
            threshold_overrides["min_dialogue_to_ambience_db"], gate_rules["mix_rules"]["min_dialogue_to_ambience_db"]
        ),
        "max_clipping_ratio": min(
            threshold_overrides["max_clipping_ratio"], gate_rules["mix_rules"]["max_clipping_ratio"]
        ),
        "max_stereo_balance_delta": min(
            threshold_overrides["max_stereo_balance_delta"], gate_rules["mix_rules"]["max_stereo_balance_delta"]
        ),
        "max_duration_delta_seconds": min(
            threshold_overrides["max_duration_delta_seconds"], gate_rules["mix_rules"]["max_duration_delta_seconds"]
        ),
    }
    if thresholds["max_attenuation_ratio"] < thresholds["min_attenuation_ratio"]:
        raise InvalidInputError("effective attenuation ratio thresholds are invalid")
    if thresholds["max_rt60_seconds"] < thresholds["min_rt60_seconds"]:
        raise InvalidInputError("effective RT60 thresholds are invalid")

    wave31_spatial_mix_binding = _validate_binding(
        root, request_payload["wave31_spatial_mix_binding"], "wave31_spatial_mix_binding"
    )
    wave31_room_acoustics_binding = _validate_binding(
        root, request_payload["wave31_room_acoustics_binding"], "wave31_room_acoustics_binding"
    )
    audio_artifacts = request_payload["audio_artifacts"]
    if not isinstance(audio_artifacts, dict):
        raise InvalidInputError("request.audio_artifacts must be an object")
    _expect_exact_keys(
        audio_artifacts,
        {"dry_dialogue", "spatial_dialogue", "ambience_bed", "final_mix"},
        "request.audio_artifacts",
    )
    dry_dialogue_binding = _validate_path_sha_bytes(root, audio_artifacts["dry_dialogue"], "audio_artifacts.dry_dialogue")
    spatial_dialogue_binding = _validate_path_sha_bytes(
        root, audio_artifacts["spatial_dialogue"], "audio_artifacts.spatial_dialogue"
    )
    ambience_bed_binding = _validate_path_sha_bytes(root, audio_artifacts["ambience_bed"], "audio_artifacts.ambience_bed")
    final_mix_binding = _validate_path_sha_bytes(root, audio_artifacts["final_mix"], "audio_artifacts.final_mix")

    ambience_continuity = request_payload["ambience_continuity_evidence"]
    if not isinstance(ambience_continuity, dict):
        raise InvalidInputError("request.ambience_continuity_evidence must be an object")
    _expect_exact_keys(
        ambience_continuity,
        {"previous_segment", "current_segment", "hard_cut_contract"},
        "request.ambience_continuity_evidence",
    )
    ambience_previous_binding = _validate_path_sha_bytes(
        root, ambience_continuity["previous_segment"], "ambience_continuity_evidence.previous_segment"
    )
    ambience_current_binding = _validate_path_sha_bytes(
        root, ambience_continuity["current_segment"], "ambience_continuity_evidence.current_segment"
    )
    if ambience_previous_binding.path == ambience_current_binding.path:
        raise InvalidInputError("ambience continuity previous/current segments must use distinct paths")
    if ambience_previous_binding.sha256 == ambience_current_binding.sha256:
        raise InvalidInputError("ambience continuity previous/current segments must use distinct SHA-256 hashes")
    hard_cut_contract = _validate_hard_cut_contract(ambience_continuity["hard_cut_contract"])
    hard_cut_approval, hard_cut_authority_blockers = _resolve_hard_cut_approval(
        hard_cut_contract,
        hard_cut_approvers=gate_rules["proof_rules"]["hard_cut_approvers"],
        is_synthetic=is_synthetic,
    )

    playback_proof_binding = None
    if request_payload["playback_proof_binding"] is not None:
        playback_proof_binding = _validate_binding(root, request_payload["playback_proof_binding"], "playback_proof_binding")
    runtime_proof_binding = None
    if request_payload["runtime_proof_binding"] is not None:
        runtime_proof_binding = _validate_binding(root, request_payload["runtime_proof_binding"], "runtime_proof_binding")
    production_authority_bundle_binding = None
    if request_payload["production_authority_bundle_binding"] is not None:
        production_authority_bundle_binding = _validate_binding(
            root, request_payload["production_authority_bundle_binding"], "production_authority_bundle_binding"
        )

    wave31_spatial_mix = _validate_wave31_manifest(
        _load_json(wave31_spatial_mix_binding.path),
        wave31_spatial_schema,
        "wave31_spatial_mix_manifest",
    )
    wave31_room_acoustics = _validate_wave31_manifest(
        _load_json(wave31_room_acoustics_binding.path),
        wave31_room_schema,
        "wave31_room_acoustics_manifest",
    )
    for payload_label, payload in (
        ("wave31_spatial_mix_manifest", wave31_spatial_mix),
        ("wave31_room_acoustics_manifest", wave31_room_acoustics),
    ):
        for field, expected in (("scene_id", scene_id), ("shot_id", shot_id)):
            if field not in payload:
                raise InvalidInputError(f"{payload_label}.{field} missing")
            if payload[field] != expected:
                raise InvalidInputError(f"{payload_label}.{field} mismatch")
        if "run_id" not in payload:
            raise InvalidInputError(f"{payload_label}.run_id missing")
        if payload["run_id"] != run_id:
            raise InvalidInputError(f"{payload_label}.run_id mismatch")
        if "take_id" not in payload:
            raise InvalidInputError(f"{payload_label}.take_id missing")
        if payload["take_id"] != take_id:
            raise InvalidInputError(f"{payload_label}.take_id mismatch")
        if "is_synthetic" not in payload:
            raise InvalidInputError(f"{payload_label}.is_synthetic missing")
        if _expect_bool(payload["is_synthetic"], f"{payload_label}.is_synthetic") != is_synthetic:
            raise InvalidInputError(f"{payload_label}.is_synthetic mismatch")

    bound_paths: set[Path] = {
        request_binding.path,
        wave31_spatial_mix_binding.path,
        wave31_room_acoustics_binding.path,
        dry_dialogue_binding.path,
        spatial_dialogue_binding.path,
        ambience_bed_binding.path,
        final_mix_binding.path,
        ambience_previous_binding.path,
        ambience_current_binding.path,
        gate_rules_binding.path,
    }
    if playback_proof_binding is not None:
        bound_paths.add(playback_proof_binding.path)
    if runtime_proof_binding is not None:
        bound_paths.add(runtime_proof_binding.path)
    if production_authority_bundle_binding is not None:
        bound_paths.add(production_authority_bundle_binding.path)
    if output_path in bound_paths:
        raise InvalidInputError("output path collides with bound request/artifact path")

    dry_metrics = _read_wav_metrics(dry_dialogue_binding.path)
    spatial_metrics_wav = _read_wav_metrics(spatial_dialogue_binding.path)
    ambience_metrics_wav = _read_wav_metrics(ambience_bed_binding.path)
    final_mix_metrics = _read_wav_metrics(final_mix_binding.path)
    spatial_pcm = _read_wav_pcm(spatial_dialogue_binding.path)
    ambience_pcm = _read_wav_pcm(ambience_bed_binding.path)
    final_mix_pcm = _read_wav_pcm(final_mix_binding.path)
    ambience_previous_metrics = _read_wav_metrics(ambience_previous_binding.path)
    ambience_current_metrics = _read_wav_metrics(ambience_current_binding.path)

    gates: dict[str, dict[str, Any]] = {}
    all_blockers: list[str] = []

    source_listener_distance = _distance3(source_position, listener_position)
    camera_listener_distance = _distance3(camera_position, listener_position)
    source_listener_vector = {
        "x": source_position["x"] - listener_position["x"],
        "y": source_position["y"] - listener_position["y"],
        "z": source_position["z"] - listener_position["z"],
    }
    right_projection = _dot3(source_listener_vector, camera_orientation["right_unit_vector"])
    expected_pan = _clamp(right_projection / max(source_listener_distance, 1e-12), -1.0, 1.0)
    observed_pan = float(spatial_metrics_wav["stereo_pan"])
    pan_error = abs(expected_pan - observed_pan)
    attenuation_ratio = float(spatial_metrics_wav["overall_rms_ratio"]) / max(float(dry_metrics["overall_rms_ratio"]), 1e-12)

    spatial_gate_blockers: list[str] = []
    if source_listener_distance > gate_rules["spatial_rules"]["max_source_listener_distance_meters"]:
        spatial_gate_blockers.append("source/listener distance exceeds gate registry maximum")
    if camera_listener_distance > thresholds["max_camera_listener_distance_delta"]:
        spatial_gate_blockers.append("camera/listener distance exceeds threshold")
    if pan_error > thresholds["max_pan_error"]:
        spatial_gate_blockers.append("observed pan deviates from expected pan")
    if attenuation_ratio < thresholds["min_attenuation_ratio"] or attenuation_ratio > thresholds["max_attenuation_ratio"]:
        spatial_gate_blockers.append("dry-to-spatial attenuation ratio out of threshold range")
    gates["spatial_position_check"] = _make_gate(
        PASS if not spatial_gate_blockers else FAIL,
        spatial_gate_blockers,
        [
            dry_dialogue_binding.sha256,
            spatial_dialogue_binding.sha256,
        ],
    )

    room_profile_id = _expect_non_empty_string(wave31_room_acoustics["room_profile_id"], "wave31_room_acoustics.room_profile_id")
    reverb_profile = _expect_non_empty_string(wave31_room_acoustics["reverb_profile"], "wave31_room_acoustics.reverb_profile")
    surface_materials_raw = wave31_room_acoustics["surface_materials"]
    if not isinstance(surface_materials_raw, list) or not surface_materials_raw:
        raise InvalidInputError("wave31_room_acoustics.surface_materials must be a non-empty array")
    surface_materials = {_expect_non_empty_string(item, "wave31_room_acoustics.surface_materials[]").lower() for item in surface_materials_raw}
    room_gate_blockers: list[str] = []
    if room_profile_id not in wave31_room_registry:
        room_gate_blockers.append("unknown room profile in Wave31 room registry")
    else:
        registry_reverb = wave31_room_registry[room_profile_id]["reverb"]
        if registry_reverb != reverb_profile:
            room_gate_blockers.append("room profile and reverb mismatch against Wave31 room registry")
        registry_surfaces = wave31_room_registry[room_profile_id]["surfaces"]
        unknown_surfaces = sorted(surface_materials - registry_surfaces)
        if unknown_surfaces:
            room_gate_blockers.append(f"room materials missing from Wave31 profile: {','.join(unknown_surfaces)}")
    if reverb_profile not in gate_rules["room_rules"]["known_reverb_profiles"]:
        room_gate_blockers.append("reverb profile is not allowlisted by Wave64 gate rules")
    profile_key = (room_profile_id, reverb_profile)
    if profile_key not in gate_rules["room_rules"]["profile_rules"]:
        room_gate_blockers.append("unknown room profile + reverb combination in Wave64 gate rules")
        profile_rule = None
    else:
        profile_rule = gate_rules["room_rules"]["profile_rules"][profile_key]
        unknown_materials = sorted(surface_materials - profile_rule["allowed_materials"])
        if unknown_materials:
            room_gate_blockers.append(f"room materials not allowlisted for room profile: {','.join(unknown_materials)}")
    spatial_manifest_room_profile = wave31_spatial_mix.get("room_profile")
    if isinstance(spatial_manifest_room_profile, dict):
        spatial_manifest_room_profile = spatial_manifest_room_profile.get("room_profile_id")
    if isinstance(spatial_manifest_room_profile, str) and spatial_manifest_room_profile != room_profile_id:
        room_gate_blockers.append("Wave31 spatial mix room profile does not match Wave31 room acoustics profile")

    measured_rt60_seconds = float(spatial_metrics_wav["rt60_seconds"])
    measured_tail_seconds = float(spatial_metrics_wav["reverb_tail_seconds"])
    if profile_rule is not None:
        rt60_low = max(profile_rule["rt60_seconds_range"][0], thresholds["min_rt60_seconds"])
        rt60_high = min(profile_rule["rt60_seconds_range"][1], thresholds["max_rt60_seconds"])
        if rt60_high < rt60_low:
            raise InvalidInputError("effective RT60 bounds are inconsistent after tightening")
        if measured_rt60_seconds < rt60_low or measured_rt60_seconds > rt60_high:
            room_gate_blockers.append("measured RT60 is outside allowed range")
        tail_low, tail_high = profile_rule["tail_seconds_range"]
        tail_error = 0.0
        if measured_tail_seconds < tail_low:
            tail_error = tail_low - measured_tail_seconds
        elif measured_tail_seconds > tail_high:
            tail_error = measured_tail_seconds - tail_high
        if tail_error > thresholds["max_reverb_tail_error_seconds"]:
            room_gate_blockers.append("measured reverb tail is outside allowed range")
    gates["room_reverb_check"] = _make_gate(
        PASS if not room_gate_blockers else FAIL,
        room_gate_blockers,
        [wave31_room_acoustics_binding.sha256, wave31_spatial_mix_binding.sha256, spatial_dialogue_binding.sha256],
    )

    ambience_gate_blockers: list[str] = []
    ambience_drift = abs(
        float(ambience_current_metrics["overall_rms_ratio"]) - float(ambience_previous_metrics["overall_rms_ratio"])
    ) / max(float(ambience_previous_metrics["overall_rms_ratio"]), 1e-12)
    ambience_gate_blockers.extend(hard_cut_authority_blockers)
    hard_cut_used = hard_cut_contract is not None
    if ambience_drift > thresholds["max_ambience_drift"] and not hard_cut_used:
        ambience_gate_blockers.append("ambience continuity drift exceeds threshold without hard-cut contract")
    gates["ambience_continuity"] = _make_gate(
        PASS if not ambience_gate_blockers else FAIL,
        ambience_gate_blockers,
        [ambience_previous_binding.sha256, ambience_current_binding.sha256],
    )

    mix_gate_blockers: list[str] = []
    final_mix_distinct_path_from_stems = all(
        final_mix_binding.path != stem_binding.path
        for stem_binding in (dry_dialogue_binding, spatial_dialogue_binding, ambience_bed_binding)
    )
    final_mix_distinct_sha_from_stems = all(
        final_mix_binding.sha256 != stem_binding.sha256
        for stem_binding in (dry_dialogue_binding, spatial_dialogue_binding, ambience_bed_binding)
    )
    if not final_mix_distinct_path_from_stems:
        mix_gate_blockers.append("final mix path must be distinct from every stem path")
    if not final_mix_distinct_sha_from_stems:
        mix_gate_blockers.append("final mix SHA-256 must be distinct from every stem SHA-256")
    dialogue_to_ambience_db = _db(float(spatial_metrics_wav["overall_rms_ratio"])) - _db(
        float(ambience_metrics_wav["overall_rms_ratio"])
    )
    if dialogue_to_ambience_db < thresholds["min_dialogue_to_ambience_db"]:
        mix_gate_blockers.append("dialogue is masked by ambience")
    if float(final_mix_metrics["clipping_ratio"]) > thresholds["max_clipping_ratio"]:
        mix_gate_blockers.append("final mix clipping ratio exceeds threshold")
    final_channel_rms = final_mix_metrics["channel_rms_ratios"]
    stereo_balance_delta = 0.0
    if len(final_channel_rms) >= 2:
        stereo_balance_delta = abs(float(final_channel_rms[0]) - float(final_channel_rms[1]))
    if stereo_balance_delta > thresholds["max_stereo_balance_delta"]:
        mix_gate_blockers.append("final mix stereo balance delta exceeds threshold")
    sample_rates = {
        int(dry_metrics["sample_rate_hz"]),
        int(spatial_metrics_wav["sample_rate_hz"]),
        int(ambience_metrics_wav["sample_rate_hz"]),
        int(final_mix_metrics["sample_rate_hz"]),
    }
    channels_set = {
        int(dry_metrics["channels"]),
        int(spatial_metrics_wav["channels"]),
        int(ambience_metrics_wav["channels"]),
        int(final_mix_metrics["channels"]),
    }
    sample_widths = {
        int(dry_metrics["sample_width_bytes"]),
        int(spatial_metrics_wav["sample_width_bytes"]),
        int(ambience_metrics_wav["sample_width_bytes"]),
        int(final_mix_metrics["sample_width_bytes"]),
    }
    durations = [
        float(dry_metrics["duration_seconds"]),
        float(spatial_metrics_wav["duration_seconds"]),
        float(ambience_metrics_wav["duration_seconds"]),
        float(final_mix_metrics["duration_seconds"]),
    ]
    sample_rate_match = len(sample_rates) == 1 and next(iter(sample_rates)) == gate_rules["mix_rules"]["required_sample_rate_hz"]
    channel_match = len(channels_set) == 1 and next(iter(channels_set)) == gate_rules["mix_rules"]["required_channels"]
    sample_width_match = len(sample_widths) == 1
    duration_delta_seconds = max(durations) - min(durations)
    if not sample_rate_match:
        mix_gate_blockers.append("sample-rate parity mismatch across stems/final mix")
    if not channel_match:
        mix_gate_blockers.append("channel-count parity mismatch across stems/final mix")
    if not sample_width_match:
        mix_gate_blockers.append("sample-width parity mismatch across stems/final mix")
    if duration_delta_seconds > thresholds["max_duration_delta_seconds"]:
        mix_gate_blockers.append("duration parity mismatch across stems/final mix")
    used_sample_reconstruction, normalized_reconstruction_residual_ratio = _compute_mix_reconstruction_residual_ratio(
        spatial_pcm, ambience_pcm, final_mix_pcm
    )
    if not used_sample_reconstruction:
        mix_gate_blockers.append("final mix reconstruction requires exact PCM frame and format parity")
    elif normalized_reconstruction_residual_ratio > gate_rules["mix_rules"]["max_mix_reconstruction_residual_ratio"]:
        mix_gate_blockers.append("final mix reconstruction residual exceeds registry maximum")
    expected_mix_energy = math.sqrt(
        float(spatial_metrics_wav["overall_rms_ratio"]) ** 2 + float(ambience_metrics_wav["overall_rms_ratio"]) ** 2
    )
    final_mix_energy_ratio = float(final_mix_metrics["overall_rms_ratio"]) / max(expected_mix_energy, 1e-12)
    if final_mix_energy_ratio < gate_rules["mix_rules"]["min_final_mix_energy_ratio"]:
        mix_gate_blockers.append("final mix energy is below registry floor")
    if final_mix_energy_ratio > gate_rules["mix_rules"]["max_final_mix_energy_ratio"]:
        mix_gate_blockers.append("final mix energy exceeds registry ceiling")
    gates["mix_balance_review"] = _make_gate(
        PASS if not mix_gate_blockers else FAIL,
        mix_gate_blockers,
        [
            dry_dialogue_binding.sha256,
            spatial_dialogue_binding.sha256,
            ambience_bed_binding.sha256,
            final_mix_binding.sha256,
        ],
    )

    playback_gate_blockers: list[str] = []
    playback_producer_authority = None
    if playback_proof_binding is None:
        playback_gate_status = BLOCKED
        playback_gate_blockers.append("missing playback_proof_binding")
    else:
        playback_fail_blockers, playback_blocked_blockers, playback_producer_authority = _validate_optional_proof(
            _load_json(playback_proof_binding.path),
            "playback_proof",
            expected_schema_name="wave64_spatial_audio_playback_proof",
            expected_proof_kind="spatial_audio_playback_review",
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            dry_dialogue_sha=dry_dialogue_binding.sha256,
            spatial_dialogue_sha=spatial_dialogue_binding.sha256,
            ambience_bed_sha=ambience_bed_binding.sha256,
            final_mix_sha=final_mix_binding.sha256,
            required_review_results=gate_rules["proof_rules"]["required_review_results"],
            forbid_self_authorization=gate_rules["proof_rules"]["forbid_self_authorization"],
            producer_allowlist=gate_rules["proof_rules"]["producer_allowlist"],
        )
        playback_gate_blockers.extend(playback_fail_blockers)
        playback_gate_blockers.extend(playback_blocked_blockers)
        if playback_fail_blockers:
            playback_gate_status = FAIL
        elif playback_blocked_blockers:
            playback_gate_status = BLOCKED
        else:
            playback_gate_status = PASS
    gates["spatial_audio_playback_review"] = _make_gate(
        playback_gate_status,
        playback_gate_blockers,
        [playback_proof_binding.sha256] if playback_proof_binding is not None else [],
    )

    runtime_gate_blockers: list[str] = []
    runtime_producer_authority = None
    if runtime_proof_binding is None:
        runtime_gate_status = BLOCKED
        runtime_gate_blockers.append("missing runtime_proof_binding")
    else:
        runtime_fail_blockers, runtime_blocked_blockers, runtime_producer_authority = _validate_optional_proof(
            _load_json(runtime_proof_binding.path),
            "runtime_proof",
            expected_schema_name="wave64_production_runtime_proof",
            expected_proof_kind="production_runtime",
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            dry_dialogue_sha=dry_dialogue_binding.sha256,
            spatial_dialogue_sha=spatial_dialogue_binding.sha256,
            ambience_bed_sha=ambience_bed_binding.sha256,
            final_mix_sha=final_mix_binding.sha256,
            required_review_results=gate_rules["proof_rules"]["required_review_results"],
            forbid_self_authorization=gate_rules["proof_rules"]["forbid_self_authorization"],
            producer_allowlist=gate_rules["proof_rules"]["producer_allowlist"],
        )
        runtime_gate_blockers.extend(runtime_fail_blockers)
        runtime_gate_blockers.extend(runtime_blocked_blockers)
        if runtime_fail_blockers:
            runtime_gate_status = FAIL
        elif runtime_blocked_blockers:
            runtime_gate_status = BLOCKED
        else:
            runtime_gate_status = PASS
    if is_synthetic:
        runtime_gate_status = BLOCKED
        runtime_gate_blockers.append("synthetic input cannot satisfy production runtime proof gate")
    gates["production_runtime_proof"] = _make_gate(
        runtime_gate_status,
        runtime_gate_blockers,
        [runtime_proof_binding.sha256] if runtime_proof_binding is not None else [],
    )

    authority_gate_blockers: list[str] = []
    authority_prereqs = (
        "spatial_position_check",
        "room_reverb_check",
        "ambience_continuity",
        "mix_balance_review",
        "spatial_audio_playback_review",
        "production_runtime_proof",
    )
    failed_prereqs = [name for name in authority_prereqs if gates[name]["status"] == FAIL]
    blocked_prereqs = [name for name in authority_prereqs if gates[name]["status"] == BLOCKED]
    if is_synthetic:
        authority_gate_status = BLOCKED
        authority_gate_blockers.append("synthetic input cannot satisfy production spatial-room authority")
    elif evidence_origin == "hand_authored_relabel":
        authority_gate_status = BLOCKED
        authority_gate_blockers.append("hand-authored relabel evidence cannot satisfy production spatial-room authority")
    elif failed_prereqs:
        authority_gate_status = FAIL
        authority_gate_blockers.extend(f"upstream gate failed: {name}" for name in failed_prereqs)
    elif blocked_prereqs:
        authority_gate_status = BLOCKED
        authority_gate_blockers.extend(f"upstream gate blocked: {name}" for name in blocked_prereqs)
    elif production_authority_bundle_binding is None:
        authority_gate_status = BLOCKED
        authority_gate_blockers.append("missing production_authority_bundle_binding")
    elif playback_proof_binding is None or runtime_proof_binding is None:
        authority_gate_status = BLOCKED
        authority_gate_blockers.append("production authority requires playback and runtime proofs")
    else:
        bundle_id, authority_id, bundle_blockers = _validate_production_bundle(
            _load_json(production_authority_bundle_binding.path),
            run_id=run_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            is_synthetic=is_synthetic,
            evidence_origin=evidence_origin,
            playback_binding=playback_proof_binding,
            runtime_binding=runtime_proof_binding,
            dry_dialogue_sha=dry_dialogue_binding.sha256,
            spatial_dialogue_sha=spatial_dialogue_binding.sha256,
            ambience_bed_sha=ambience_bed_binding.sha256,
            final_mix_sha=final_mix_binding.sha256,
            forbid_self_authorization=gate_rules["proof_rules"]["forbid_self_authorization"],
        )
        authority_gate_blockers.extend(bundle_blockers)
        matches = [
            entry
            for entry in gate_rules["production_rules"]["approved_bundle_allowlist"]
            if entry["bundle_id"] == bundle_id
            and entry["authority_id"] == authority_id
            and entry["bundle_sha256"] == production_authority_bundle_binding.sha256
        ]
        if bundle_blockers:
            authority_gate_status = FAIL
        elif not matches:
            authority_gate_status = BLOCKED
            authority_gate_blockers.append("production authority bundle is not allowlisted")
        elif any(entry["revoked"] for entry in matches):
            authority_gate_status = BLOCKED
            authority_gate_blockers.append("production authority bundle is revoked")
        else:
            authority_gate_status = PASS
    gates["production_spatial_room_authority"] = _make_gate(
        authority_gate_status,
        authority_gate_blockers,
        [production_authority_bundle_binding.sha256] if production_authority_bundle_binding is not None else [],
    )

    for name in GATE_NAMES:
        if name == "overall_pass":
            continue
        all_blockers.extend(gates[name]["blockers"])
    overall_blockers = sorted(set(all_blockers))
    non_overall_gate_statuses = [gates[name]["status"] for name in GATE_NAMES if name != "overall_pass"]
    if (not is_synthetic) and evidence_origin == "technical_capture" and all(status == PASS for status in non_overall_gate_statuses):
        overall_status = PASS
        overall_pass = True
    elif any(status == FAIL for status in non_overall_gate_statuses):
        overall_status = FAIL
        overall_pass = False
    else:
        overall_status = BLOCKED
        overall_pass = False
    gates["overall_pass"] = _make_gate(overall_status, overall_blockers, [request_binding.sha256])

    report = {
        "schema_name": "wave64_spatial_room_evaluator_report",
        "report_version": 1,
        "run_id": run_id,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "take_id": take_id,
        "is_synthetic": is_synthetic,
        "evidence_origin": evidence_origin,
        "request_binding": {
            "path": str(request_binding.path),
            "sha256": request_binding.sha256,
        },
        "artifact_bindings": {
            "wave31_spatial_mix": _binding_or_none(wave31_spatial_mix_binding),
            "wave31_room_acoustics": _binding_or_none(wave31_room_acoustics_binding),
            "dry_dialogue": {
                "path": str(dry_dialogue_binding.path),
                "sha256": dry_dialogue_binding.sha256,
                "bytes": dry_dialogue_binding.bytes,
            },
            "spatial_dialogue": {
                "path": str(spatial_dialogue_binding.path),
                "sha256": spatial_dialogue_binding.sha256,
                "bytes": spatial_dialogue_binding.bytes,
            },
            "ambience_bed": {
                "path": str(ambience_bed_binding.path),
                "sha256": ambience_bed_binding.sha256,
                "bytes": ambience_bed_binding.bytes,
            },
            "final_mix": {
                "path": str(final_mix_binding.path),
                "sha256": final_mix_binding.sha256,
                "bytes": final_mix_binding.bytes,
            },
            "ambience_previous_segment": {
                "path": str(ambience_previous_binding.path),
                "sha256": ambience_previous_binding.sha256,
                "bytes": ambience_previous_binding.bytes,
            },
            "ambience_current_segment": {
                "path": str(ambience_current_binding.path),
                "sha256": ambience_current_binding.sha256,
                "bytes": ambience_current_binding.bytes,
            },
            "playback_proof": _binding_or_none(playback_proof_binding),
            "runtime_proof": _binding_or_none(runtime_proof_binding),
            "production_authority_bundle": _binding_or_none(production_authority_bundle_binding),
            "wave64_gate_registry": {
                "path": str(gate_rules_binding.path),
                "sha256": gate_rules_binding.sha256,
            },
        },
        "metrics": {
            "audio_files": {
                "dry_dialogue": {k: v for k, v in dry_metrics.items() if k != "channel_rms_ratios"},
                "spatial_dialogue": {k: v for k, v in spatial_metrics_wav.items() if k != "channel_rms_ratios"},
                "ambience_bed": {k: v for k, v in ambience_metrics_wav.items() if k != "channel_rms_ratios"},
                "final_mix": {k: v for k, v in final_mix_metrics.items() if k != "channel_rms_ratios"},
                "ambience_previous_segment": {k: v for k, v in ambience_previous_metrics.items() if k != "channel_rms_ratios"},
                "ambience_current_segment": {k: v for k, v in ambience_current_metrics.items() if k != "channel_rms_ratios"},
            },
            "spatial_metrics": {
                "source_listener_distance_meters": round(source_listener_distance, 6),
                "camera_listener_distance_meters": round(camera_listener_distance, 6),
                "expected_pan": round(expected_pan, 6),
                "observed_pan": round(observed_pan, 6),
                "pan_error": round(pan_error, 6),
                "attenuation_ratio": round(attenuation_ratio, 6),
            },
            "room_metrics": {
                "room_profile_id": room_profile_id,
                "reverb_profile": reverb_profile,
                "measured_rt60_seconds": round(measured_rt60_seconds, 6),
                "measured_reverb_tail_seconds": round(measured_tail_seconds, 6),
            },
            "ambience_metrics": {
                "drift_ratio": round(ambience_drift, 6),
                "hard_cut_used": hard_cut_used,
                "hard_cut_contract": _normalize_hard_cut_approval_for_report(hard_cut_approval),
            },
            "mix_metrics": {
                "dialogue_to_ambience_db": round(dialogue_to_ambience_db, 6),
                "final_mix_clipping_ratio": float(final_mix_metrics["clipping_ratio"]),
                "stereo_balance_delta": round(stereo_balance_delta, 6),
                "sample_rate_match": sample_rate_match,
                "channel_match": channel_match,
                "sample_width_match": sample_width_match,
                "duration_delta_seconds": round(duration_delta_seconds, 6),
                "final_mix_distinct_path_from_stems": final_mix_distinct_path_from_stems,
                "final_mix_distinct_sha_from_stems": final_mix_distinct_sha_from_stems,
                "used_sample_reconstruction": used_sample_reconstruction,
                "normalized_reconstruction_residual_ratio": round(normalized_reconstruction_residual_ratio, 6),
                "final_mix_energy_ratio": round(final_mix_energy_ratio, 6),
            },
            "proof_metrics": {
                "playback_producer_authority": _normalize_proof_producer_for_report(playback_producer_authority),
                "runtime_producer_authority": _normalize_proof_producer_for_report(runtime_producer_authority),
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
