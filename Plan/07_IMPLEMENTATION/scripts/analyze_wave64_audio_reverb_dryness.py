#!/usr/bin/env python3
"""Fail-closed Wave64 Row076 audio reverb/dryness estimation authority slice.

Library analysis refuses authority without accepted Row071 waveform features and
Row073 usable-bounds/natural-decay records. Fixture mode may compute deterministic
suggestion-only acoustic estimates from synthetic PCM without promoting library
completion, and never mutates source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_reverb_dryness_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_audio_reverb_dryness_estimation.json"
)
ROW071_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
)
ROW073_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
)
ANALYSIS_PIPELINE_REVISION = "wave64_row076_audio_reverb_dryness_v0.1.0"
TRACKER_ID = "TRK-W64-076"
ITEM_ID = "ITEM-W64-076"
SCHEMA_VERSION = "1.0.0"

THRESHOLDS: dict[str, Any] = {
    "direct_window_ms": 10.0,
    "early_reflection_window_ms": 50.0,
    "tail_floor_dbfs": -50.0,
    "dry_drr_min_db": 12.0,
    "wet_drr_max_db": 3.0,
    "rt60_dry_max_s": 0.08,
    "rt60_wet_min_s": 0.20,
    "early_reflection_density_wet_min": 3.0,
    "stereo_imprint_correlation_wet_max": 0.85,
    "channel_policy": "max_abs_mono_plus_stereo_imprint",
    "compatible_room_passthrough_requires_rule_id": True,
    "suggestion_only": True,
    "source_mutation_allowed": False,
}

METHOD_PROVENANCE: dict[str, dict[str, str]] = {
    "direct_to_reverberant": {
        "method_id": "pcm_direct_to_reverberant_energy_ratio_v1",
        "unit": "decibels",
        "window": "direct_window_then_post_direct_to_tail",
    },
    "rt60": {
        "method_id": "pcm_schroeder_style_t20_extrapolated_rt60_v1",
        "unit": "seconds",
        "window": "peak_to_tail_floor_energy_decay",
    },
    "early_reflections": {
        "method_id": "pcm_early_local_peak_density_v1",
        "unit": "peaks_per_early_window",
        "window": "post_direct_to_early_reflection_window",
    },
    "stereo_room_imprint": {
        "method_id": "pcm_stereo_correlation_rms_asymmetry_width_v1",
        "unit": "correlation_and_normalized_scores",
        "window": "full_usable_stereo_region",
    },
    "reverb_tail": {
        "method_id": "pcm_peak_to_tail_floor_duration_v1",
        "unit": "seconds",
        "window": "peak_to_tail_floor",
    },
    "double_reverb_guard": {
        "method_id": "pcm_wet_source_policy_double_reverb_guard_v1",
        "unit": "policy_enum",
        "window": "classification_plus_compatible_room_rule",
    },
}

FIXTURE_NAMES = (
    "dry_impulse",
    "dry_tone_burst",
    "wet_exponential_tail",
    "wet_stereo_room",
    "mono_noise",
    "ambiguous_medium_tail",
)


class AudioReverbDrynessError(ValueError):
    """Raised when Row076 analysis violates fail-closed authority."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AudioReverbDrynessError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise AudioReverbDrynessError("non_finite_measurement_value")
    return round(value, digits)


def db_from_energy(energy: float) -> float:
    return 10.0 * math.log10(max(energy, 1e-24))


def db_from_amplitude(amplitude: float) -> float:
    return 20.0 * math.log10(max(abs(amplitude), 1e-12))


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    acceptance_key: str,
    blocker_code: str,
    absent_code: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    if not path.is_file():
        return {
            "tracker_id": tracker_id,
            "dependency_satisfied": False,
            "blocker_codes": [absent_code],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    acceptance = str(payload.get("decision", {}).get(acceptance_key, "")).lower()
    dependency_satisfied = row_complete and acceptance in {"accepted", "pass", "passed"}
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append(blocker_code)
    return {
        "tracker_id": tracker_id,
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def evaluate_row071_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW071_DELTA,
        tracker_id="TRK-W64-071",
        acceptance_key="row071_acceptance",
        blocker_code="ROW071_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW071_DELTA_ABSENT",
    )


def evaluate_row073_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW073_DELTA,
        tracker_id="TRK-W64-073",
        acceptance_key="row073_acceptance",
        blocker_code="ROW073_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW073_DELTA_ABSENT",
    )


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise AudioReverbDrynessError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise AudioReverbDrynessError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 9600) -> dict[str, Any]:
    left = [0.0] * frames
    right = [0.0] * frames
    if name == "dry_impulse":
        left[400] = 0.95
        for i in range(401, 520):
            left[i] = 0.95 * math.exp(-(i - 400) / 18.0)
        right = list(left)
    elif name == "dry_tone_burst":
        for i in range(800, 1600):
            t = (i - 800) / sample_rate_hz
            left[i] = 0.5 * math.sin(2.0 * math.pi * 1000.0 * t)
        right = list(left)
    elif name == "wet_exponential_tail":
        left[300] = 0.9
        for i in range(301, frames):
            left[i] = 0.62 * math.exp(-(i - 300) / 3200.0)
            if (i - 300) % 240 == 0 and i + 40 < frames:
                left[i] += 0.22 * math.exp(-(i - 300) / 2600.0)
        right = list(left)
    elif name == "wet_stereo_room":
        left[280] = 0.85
        right[280] = 0.75
        for i in range(281, frames):
            decay = math.exp(-(i - 280) / 2400.0)
            left[i] = 0.42 * decay
            delay = 96
            right[i] = 0.38 * math.exp(-(i - 280) / 2500.0)
            if i - delay >= 280:
                right[i] += 0.22 * math.exp(-(i - delay - 280) / 2100.0)
            if (i - 280) % 180 == 0:
                left[i] += 0.12 * decay
                right[i] += 0.16 * decay
    elif name == "mono_noise":
        value = 777001
        for i in range(frames):
            value = (1103515245 * value + 12345) & 0x7FFFFFFF
            left[i] = ((value / 0x7FFFFFFF) * 2.0 - 1.0) * 0.08
        right = list(left)
    elif name == "ambiguous_medium_tail":
        left[350] = 0.8
        for i in range(351, 4200):
            left[i] = 0.28 * math.exp(-(i - 350) / 900.0)
        right = list(left)
    else:
        raise AudioReverbDrynessError(f"unknown_fixture:{name}")

    pcm = pack_pcm_f32le([left, right])
    source_token = f"wave64-row076-fixture:{name}".encode("utf-8")
    return {
        "asset_id": f"fixture:{name}",
        "source_sha256": sha256_bytes(source_token),
        "canonical_pcm_sha256": sha256_bytes(pcm),
        "sample_rate_hz": sample_rate_hz,
        "channels": 2,
        "frame_count": frames,
        "pcm_f32le": pcm,
        "channel_samples": [left, right],
    }


def _mono_max_abs(channels: list[list[float]]) -> list[float]:
    return [max(abs(sample) for sample in frame) for frame in zip(*channels, strict=True)]


def _energy(samples: list[float]) -> float:
    return sum(sample * sample for sample in samples)


def _stereo_imprint(left: list[float], right: list[float]) -> dict[str, float]:
    if len(left) != len(right) or not left:
        raise AudioReverbDrynessError("stereo_imprint_length_mismatch")
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    cov = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right, strict=True)) / len(left)
    var_l = sum((a - mean_l) ** 2 for a in left) / len(left)
    var_r = sum((b - mean_r) ** 2 for b in right) / len(right)
    denom = math.sqrt(max(var_l, 1e-24) * max(var_r, 1e-24))
    correlation = cov / denom
    rms_l = math.sqrt(max(_energy(left) / len(left), 0.0))
    rms_r = math.sqrt(max(_energy(right) / len(right), 0.0))
    asymmetry = abs(rms_l - rms_r) / max(rms_l + rms_r, 1e-12)
    width = max(0.0, min(1.0, (1.0 - correlation) * 0.7 + asymmetry * 0.3))
    return {
        "channel_correlation": round_finite(max(-1.0, min(1.0, correlation))),
        "left_right_rms_asymmetry": round_finite(asymmetry),
        "width_score": round_finite(width),
    }


def _count_early_peaks(mono: list[float], start: int, end: int) -> int:
    if end - start < 3:
        return 0
    count = 0
    last_peak = -10_000
    min_gap = 24
    for index in range(start + 1, end - 1):
        prev_v = mono[index - 1]
        cur = mono[index]
        next_v = mono[index + 1]
        prominent = cur > prev_v * 1.25 and cur >= next_v * 1.25
        above_floor = db_from_amplitude(cur) > float(THRESHOLDS["tail_floor_dbfs"]) + 12.0
        if prominent and above_floor and (index - last_peak) >= min_gap:
            count += 1
            last_peak = index
    return count


def _estimate_rt60_seconds(mono: list[float], peak_index: int, sample_rate_hz: int) -> float:
    peak = max(abs(mono[peak_index]), 1e-12)
    peak_db = db_from_amplitude(peak)
    target_db = peak_db - 20.0
    floor_db = float(THRESHOLDS["tail_floor_dbfs"])
    crossed_index = None
    for index in range(peak_index, len(mono)):
        level = db_from_amplitude(mono[index])
        if level <= target_db or level <= floor_db:
            crossed_index = index
            break
    if crossed_index is None:
        return round_finite((len(mono) - peak_index) / sample_rate_hz * 3.0)
    t20 = (crossed_index - peak_index) / sample_rate_hz
    return round_finite(max(0.0, t20 * 3.0))


def analyze_channels(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
    compatible_room_rule_id: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    if not channels or not channels[0]:
        raise AudioReverbDrynessError("empty_channels")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise AudioReverbDrynessError("channel_length_mismatch")

    mono = _mono_max_abs(channels)
    peak_index = max(range(frame_count), key=lambda idx: mono[idx])
    direct_samples = max(1, int(sample_rate_hz * float(THRESHOLDS["direct_window_ms"]) / 1000.0))
    early_samples = max(
        direct_samples + 1,
        int(sample_rate_hz * float(THRESHOLDS["early_reflection_window_ms"]) / 1000.0),
    )
    direct_end = min(frame_count, peak_index + direct_samples)
    early_end = min(frame_count, peak_index + early_samples)
    floor_db = float(THRESHOLDS["tail_floor_dbfs"])

    tail_end = peak_index
    for index in range(frame_count - 1, peak_index - 1, -1):
        if db_from_amplitude(mono[index]) > floor_db:
            tail_end = index + 1
            break

    direct_energy = _energy(mono[peak_index:direct_end])
    reverberant_energy = _energy(mono[direct_end:tail_end]) if tail_end > direct_end else 0.0
    drr_db = db_from_energy(direct_energy) - db_from_energy(reverberant_energy)
    rt60 = _estimate_rt60_seconds(mono, peak_index, sample_rate_hz)
    early_density = float(_count_early_peaks(mono, direct_end, early_end))
    imprint = _stereo_imprint(channels[0], channels[1] if len(channels) > 1 else channels[0])
    reverb_tail = round_finite(max(0.0, (tail_end - peak_index) / sample_rate_hz))

    dry_votes = 0
    wet_votes = 0
    if drr_db >= float(THRESHOLDS["dry_drr_min_db"]):
        dry_votes += 1
    if drr_db <= float(THRESHOLDS["wet_drr_max_db"]):
        wet_votes += 1
    if rt60 <= float(THRESHOLDS["rt60_dry_max_s"]):
        dry_votes += 1
    if rt60 >= float(THRESHOLDS["rt60_wet_min_s"]):
        wet_votes += 1
    if early_density >= float(THRESHOLDS["early_reflection_density_wet_min"]):
        wet_votes += 1
    elif early_density <= 1.0:
        dry_votes += 1
    # Stereo imprint contributes a wet vote only; mono-identical dry sources must not
    # be penalized merely for perfect left/right correlation.
    if imprint["channel_correlation"] <= float(THRESHOLDS["stereo_imprint_correlation_wet_max"]) and imprint[
        "width_score"
    ] >= 0.15:
        wet_votes += 1

    rms_db = db_from_amplitude(math.sqrt(max(_energy(mono) / frame_count, 0.0)))
    noise_like = rms_db > floor_db + 20.0 and abs(drr_db) < 4.0 and early_density >= 40.0
    if noise_like and wet_votes < 3 and dry_votes < 3:
        classification = "ambiguous"
        confidence = 0.35
    elif wet_votes >= 3 and wet_votes > dry_votes:
        classification = "wet"
        confidence = min(0.95, 0.55 + 0.1 * wet_votes)
    elif dry_votes >= 3 and dry_votes > wet_votes:
        classification = "dry"
        confidence = min(0.95, 0.55 + 0.1 * dry_votes)
    else:
        classification = "ambiguous"
        confidence = 0.45

    # Environment-specific remains reserved for accepted library room metadata binding.
    # Synthetic fixtures never claim environment_specific authority.

    if classification == "dry":
        wet_source_policy = "dry_render"
        additional_convolution_safe = True
    elif classification == "wet":
        if compatible_room_rule_id and THRESHOLDS["compatible_room_passthrough_requires_rule_id"]:
            wet_source_policy = "compatible_wet_passthrough"
            additional_convolution_safe = False
        else:
            wet_source_policy = "reject"
            additional_convolution_safe = False
    elif classification == "environment_specific":
        wet_source_policy = "limited_processing"
        additional_convolution_safe = False
    else:
        wet_source_policy = "limited_processing"
        additional_convolution_safe = False

    measurements = {
        "direct_to_reverberant_ratio_db": round_finite(drr_db),
        "rt60_seconds": rt60,
        "early_reflection_density": round_finite(early_density),
        "stereo_room_imprint": imprint,
        "reverb_tail_seconds": reverb_tail,
        "additional_convolution_safe": bool(additional_convolution_safe),
        "confidence": round_finite(confidence, 6),
        "compatible_room_rule_id": compatible_room_rule_id,
    }
    return measurements, classification, wet_source_policy


def build_analysis_record(
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    measurements: dict[str, Any],
    classification: str,
    wet_source_policy: str,
    library_authority: bool,
    blocker_codes: list[str] | None = None,
) -> dict[str, Any]:
    blockers = list(blocker_codes or [])
    source_before = source_sha256
    source_after = source_sha256
    source_bytes_unchanged = source_before == source_after
    if not source_bytes_unchanged:
        blockers.append("SOURCE_BYTES_CHANGED")
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")

    double_reverb_guard_enforced = True
    if classification == "wet" and wet_source_policy not in {
        "reject",
        "compatible_wet_passthrough",
        "limited_processing",
    }:
        double_reverb_guard_enforced = False
        blockers.append("DOUBLE_REVERB_GUARD_NOT_ENFORCED")
    if classification == "wet" and measurements.get("additional_convolution_safe") is True:
        double_reverb_guard_enforced = False
        blockers.append("WET_ASSET_MARKED_CONVOLUTION_SAFE")
    if (
        wet_source_policy == "compatible_wet_passthrough"
        and not measurements.get("compatible_room_rule_id")
        and THRESHOLDS["compatible_room_passthrough_requires_rule_id"]
    ):
        double_reverb_guard_enforced = False
        blockers.append("COMPATIBLE_ROOM_RULE_MISSING")

    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "source_before_sha256": source_before,
        "source_after_sha256": source_after,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "thresholds": dict(THRESHOLDS),
        "measurements": measurements,
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "classification": classification,
        "wet_source_policy": wet_source_policy,
        "decision": {
            "status": "pass" if library_authority and not blockers else "blocked",
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "suggestion_only": True,
            "source_bytes_unchanged": source_bytes_unchanged,
            "double_reverb_guard_enforced": double_reverb_guard_enforced,
        },
    }


def validate_analysis_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AudioReverbDrynessError(f"schema_validation_failed:{location}:{first.message}")


def extract_fixture_record(
    root: Path,
    fixture_name: str,
    *,
    compatible_room_rule_id: str | None = None,
) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    measurements, classification, wet_source_policy = analyze_channels(
        fixture["channel_samples"],
        sample_rate_hz=fixture["sample_rate_hz"],
        compatible_room_rule_id=compatible_room_rule_id,
    )
    record = build_analysis_record(
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        measurements=measurements,
        classification=classification,
        wet_source_policy=wet_source_policy,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    validate_analysis_record(root, record)
    return record


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row071 = evaluate_row071_admission(root)
    row073 = evaluate_row073_admission(root)
    blocker_codes: list[str] = []
    for admission in (row071, row073):
        blocker_codes.extend(admission["blocker_codes"])
    if not row071["dependency_satisfied"] or not row073["dependency_satisfied"]:
        if "ROW071_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW071_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED")
    if "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
        blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    if "FULL_LIBRARY_ACOUSTIC_RECONCILIATION_ABSENT" not in blocker_codes:
        blocker_codes.append("FULL_LIBRARY_ACOUSTIC_RECONCILIATION_ABSENT")
    if "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT" not in blocker_codes:
        blocker_codes.append("DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT")

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-076_audio_reverb_dryness_estimation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW071_ROW073_DEPENDENCIES_AND_FULL_LIBRARY_ACOUSTIC_RUNTIME_ABSENT",
        "thresholds": dict(THRESHOLDS),
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "row071_admission": row071,
        "row073_admission": row073,
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove direct/reverberant, RT60-style decay, early-reflection "
                "density, stereo imprint, wet-source policy, and double-reverb guard method "
                "identity only; they do not accept Row076 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row076_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row071 waveform/spectral features and Row073 usable-bounds/natural-decay "
                "authority, reconcile every accepted input to a dry/wet/ambiguous/environment-specific "
                "decision with hash-bound evidence and enforced wet-source policy, and replace this "
                "hold packet with full-library runtime evidence."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture"), default="library")
    parser.add_argument("--fixture", default="dry_impulse")
    parser.add_argument("--compatible-room-rule-id", default=None)
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise AudioReverbDrynessError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(
            root,
            args.fixture,
            compatible_room_rule_id=args.compatible_room_rule_id,
        )
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise AudioReverbDrynessError("library_mode_must_remain_fail_closed_until_dependencies_accepted")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
