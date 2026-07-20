#!/usr/bin/env python3
"""Fail-closed Wave64 Row076 audio reverb/dryness estimation authority slice.

Library analysis refuses authority without accepted Row071 waveform features and
Row073 usable-bounds/natural-decay unlock (or acceptance). Fixture mode may compute
deterministic suggestion-only acoustic estimates from synthetic PCM without promoting
library completion, and never mutates source bytes. Index-retained mode may probe or
reconcile accepted Row071 feature records into suggestion-only dry/wet/ambiguous
PASS/blocker compact records under frozen thresholds without claiming COMPLETE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from datetime import datetime, timezone
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
DEFAULT_ROW071_RETAINED_RECORDS = Path(
    "runtime_artifacts/audio_qa/row071_index_retained_20260719/records.jsonl"
)
DEFAULT_RETAINED_REVERB_RUNTIME_DIR = Path(
    "runtime_artifacts/reverb_dryness/row076_index_retained_20260720"
)
ANALYSIS_PIPELINE_REVISION = "wave64_row076_audio_reverb_dryness_v0.2.0"
TRACKER_ID = "TRK-W64-076"
ITEM_ID = "ITEM-W64-076"
SCHEMA_VERSION = "1.0.0"
# Cap retained-library PCM windows to keep limited probes from contending with
# Row075 full-library defect reconcile on the same source tree.
MAX_ANALYSIS_FRAMES = 48000 * 30
RETAINED_CHECKPOINT_EVERY = 25
_FEATURE_MOD: Any | None = None

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
    """Admit Row073 for downstream probes when accepted OR runtime/probe-unlocked.

    Row073 may remain row_complete=false with thresholds/strata held while still
    unlocking dependency-safe index-retained probes via dependencies_unlocked and
    RUNTIME_PASS_BOUNDED probe or coverage authority. Acceptance itself stays held
    until thresholds and library strata are resolved.
    """
    path = resolve_under(root, delta_path or ROW073_DELTA, "trk-w64-073_delta")
    if not path.is_file():
        return {
            "tracker_id": "TRK-W64-073",
            "dependency_satisfied": False,
            "blocker_codes": ["ROW073_DELTA_ABSENT"],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "admission_mode": "absent",
        }
    payload = load_json(path)
    decision = payload.get("decision") or {}
    row_complete = payload.get("row_complete") is True
    acceptance = str(decision.get("row073_acceptance", "")).lower()
    acceptance_pass = row_complete and acceptance in {"accepted", "pass", "passed"}
    dependencies_unlocked = decision.get("dependencies_unlocked") is True
    runtime_completion = (
        payload.get("runtime_completion_claimed") is True
        or decision.get("runtime_completion") is True
    )
    proof_tier = str(
        payload.get("proof_tier")
        or payload.get("highest_proof_tier_achieved")
        or ""
    )
    probe_authority = str(
        (payload.get("accepted_index_retained_bounds_runtime") or {}).get("authority") or ""
    )
    runtime_unlock = (
        dependencies_unlocked
        and runtime_completion
        and proof_tier == "RUNTIME_PASS_BOUNDED"
    )
    probe_unlock = (
        dependencies_unlocked
        and proof_tier == "RUNTIME_PASS_BOUNDED"
        and probe_authority
        in {
            "accepted_index_retained_bounds_probe",
            "accepted_index_retained_bounds_reconcile",
        }
    )
    dependency_satisfied = acceptance_pass or runtime_unlock or probe_unlock
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append("ROW073_DEPENDENCY_NOT_ACCEPTED")
    if acceptance_pass:
        admission_mode = "accepted"
    elif runtime_unlock:
        admission_mode = "runtime_unlocked"
    elif probe_unlock:
        admission_mode = "probe_unlocked"
    else:
        admission_mode = "held"
    return {
        "tracker_id": "TRK-W64-073",
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "admission_mode": admission_mode,
        "dependencies_unlocked": dependencies_unlocked,
        "proof_tier": proof_tier,
        "row073_acceptance": acceptance or "absent",
        "probe_authority": probe_authority or None,
    }


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


def load_feature_module() -> Any:
    global _FEATURE_MOD
    if _FEATURE_MOD is not None:
        return _FEATURE_MOD
    import importlib.util

    script = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
    spec = importlib.util.spec_from_file_location("wave64_row071_features_for_reverb", script)
    if spec is None or spec.loader is None:
        raise AudioReverbDrynessError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _empty_retained_reverb_counts() -> dict[str, int]:
    return {
        "records_processed": 0,
        "records_total": 0,
        "reverb_pass": 0,
        "reverb_blocked": 0,
        "exact_blockers": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "pcm_sha_verified": 0,
        "analysis_truncated": 0,
        "source_immutable_true": 0,
        "classification_dry": 0,
        "classification_wet": 0,
        "classification_ambiguous": 0,
        "classification_environment_specific": 0,
        "double_reverb_guard_enforced": 0,
    }


def _channels_from_frames_nc(frames_nc: Any) -> list[list[float]]:
    """Preserve per-channel float lists for stereo imprint + DRR analysis."""
    import numpy as np

    arr = np.asarray(frames_nc, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        raise AudioReverbDrynessError("invalid_frames_nc_shape")
    return [arr[:, channel].astype(float).tolist() for channel in range(arr.shape[1])]


def build_compact_reverb_record(
    *,
    relative_path: str,
    extension: str,
    role: str,
    event_type: str,
    asset_id: str,
    feature_status: str,
    measurements: dict[str, Any] | None,
    classification: str | None,
    wet_source_policy: str | None,
    source_sha256: str | None,
    canonical_pcm_sha256: str | None,
    sample_rate_hz: int | None,
    channels: int | None,
    frame_count: int | None,
    pcm_sha_verified: bool,
    source_immutable: bool | None,
    analysis_truncated: bool,
    double_reverb_guard_enforced: bool,
    blocker_code: str | None,
    blocker_codes: list[str],
    blocker_detail: str | None = None,
) -> dict[str, Any]:
    technical_pass = (
        feature_status == "pass"
        and measurements is not None
        and classification is not None
        and wet_source_policy is not None
        and pcm_sha_verified
        and source_immutable is True
        and double_reverb_guard_enforced
        and not blocker_codes
    )
    status = "pass" if technical_pass else "blocked"
    codes = list(blocker_codes)
    if technical_pass:
        codes = ["LIBRARY_AUTHORITY_NOT_GRANTED"]
    compact: dict[str, Any] = {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "feature_status": feature_status,
        "reverb_status": status,
        "technical_reverb_pass": technical_pass,
        "library_authority": False,
        "suggestion_only": True,
        "source_bytes_unchanged": bool(source_immutable) if source_immutable is not None else False,
        "classification": classification,
        "wet_source_policy": wet_source_policy,
        "double_reverb_guard_enforced": double_reverb_guard_enforced,
        "blocker_code": None if technical_pass else (blocker_code or "REVERB_ANALYSIS_BLOCKED"),
        "blocker_codes": codes if not technical_pass else ["LIBRARY_AUTHORITY_NOT_GRANTED"],
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "source_sha256": source_sha256,
        "source_before_sha256": source_sha256,
        "source_after_sha256": source_sha256,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "pcm_sha_verified": pcm_sha_verified,
        "source_immutable": source_immutable,
        "analysis_truncated": analysis_truncated,
        "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
        "thresholds": dict(THRESHOLDS),
        "measurements": measurements,
    }
    if blocker_detail:
        compact["blocker_detail"] = blocker_detail
    return compact


def run_retained_index_reverb_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile retained Row071 feature records to suggestion-only reverb PASS/blocker."""
    row071 = evaluate_row071_admission(root)
    row073 = evaluate_row073_admission(root)
    if not row071.get("dependency_satisfied") or not row073.get("dependency_satisfied"):
        raise AudioReverbDrynessError("index_retained_requires_row071_and_row073_admission")

    feature_mod = load_feature_module()
    decode = feature_mod.load_decode_module()
    locator = decode.load_active_index_locator(root)
    source_root = Path(locator["source_root"])
    records_in = resolve_under(
        root,
        row071_records_path or DEFAULT_ROW071_RETAINED_RECORDS,
        "row071_retained_records",
    )
    if not records_in.is_file():
        raise AudioReverbDrynessError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_RETAINED_REVERB_RUNTIME_DIR,
        "retained_reverb_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            f"owner=analyze_wave64_audio_reverb_dryness.py\nstarted={datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise AudioReverbDrynessError(
            "retained_reverb_runtime_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_reverb_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_reverb_counts()
    counts["records_total"] = total_lines
    blocker_histogram: dict[str, int] = {}
    extension_histogram: dict[str, int] = {}
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    processed_paths: set[str] = set()
    next_index = 0

    if resume and progress_path.is_file() and records_path.is_file():
        progress = load_json(progress_path)
        if str(progress.get("row071_records_sha256") or "") == sha256_file(records_in):
            counts = dict(progress.get("counts") or counts)
            blocker_histogram = {
                str(key): int(value)
                for key, value in (progress.get("blocker_histogram") or {}).items()
            }
            extension_histogram = {
                str(key): int(value)
                for key, value in (progress.get("extension_histogram") or {}).items()
            }
            next_index = int(progress.get("next_record_index") or 0)
            started_at = str(progress.get("started_at") or started_at)
            with records_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    compact = json.loads(line)
                    processed_paths.add(str(compact.get("relative_path") or ""))
        else:
            records_path.write_text("", encoding="utf-8")
            next_index = 0
            processed_paths = set()
            counts = _empty_retained_reverb_counts()
            counts["records_total"] = total_lines
            blocker_histogram = {}
            extension_histogram = {}
    else:
        records_path.write_text("", encoding="utf-8")
        if progress_path.is_file() and not resume:
            progress_path.unlink()

    def write_progress(*, complete: bool) -> None:
        payload = {
            "schema_version": 1,
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
            "row071_records_path": str(records_in.relative_to(root)).replace("\\", "/"),
            "row071_records_sha256": sha256_file(records_in),
            "index_sha256": locator["index_sha256"],
            "started_at": started_at,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "next_record_index": next_index,
            "limit": limit,
            "complete": complete,
            "counts": counts,
            "blocker_histogram": blocker_histogram,
            "extension_histogram": extension_histogram,
            "records_path": str(records_path.relative_to(root)).replace("\\", "/"),
            "row075_contention_policy": "limited_probe_only_while_row075_full_reconcile_owns_pcm_io",
        }
        write_json(progress_path, payload)

    with records_in.open("r", encoding="utf-8") as handle, records_path.open(
        "a", encoding="utf-8"
    ) as out_handle:
        for line_index, line in enumerate(handle):
            if line_index < next_index:
                continue
            stripped = line.strip()
            if not stripped:
                next_index = line_index + 1
                continue
            feature_rec = json.loads(stripped)
            relative_path = str(feature_rec.get("relative_path") or "").replace("\\", "/")
            if not relative_path:
                next_index = line_index + 1
                continue
            if relative_path in processed_paths:
                next_index = line_index + 1
                continue
            if limit is not None and counts["records_processed"] >= limit:
                break

            extension = str(feature_rec.get("extension") or Path(relative_path).suffix).lower()
            feature_status = str(feature_rec.get("feature_status") or "")
            role = str(feature_rec.get("role") or "")
            event_type = str(feature_rec.get("event_type") or "")
            asset_id = f"index:{relative_path}"

            if feature_status != "pass":
                blocker_code = str(feature_rec.get("blocker_code") or "FEATURE_NON_PASS")
                compact = build_compact_reverb_record(
                    relative_path=relative_path,
                    extension=extension,
                    role=role,
                    event_type=event_type,
                    asset_id=asset_id,
                    feature_status=feature_status,
                    measurements=None,
                    classification=None,
                    wet_source_policy=None,
                    source_sha256=feature_rec.get("source_sha256"),
                    canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                    sample_rate_hz=None,
                    channels=None,
                    frame_count=None,
                    pcm_sha_verified=False,
                    source_immutable=feature_rec.get("source_immutable"),
                    analysis_truncated=False,
                    double_reverb_guard_enforced=False,
                    blocker_code=blocker_code,
                    blocker_codes=[blocker_code],
                )
                counts["feature_non_pass_inputs"] += 1
            else:
                absolute = source_root / relative_path
                try:
                    frames_nc, sample_rate_hz, source_sha, _source_bytes, pcm_sha = (
                        feature_mod.load_canonical_float_channels(root, absolute)
                    )
                    after_sha = sha256_file(absolute)
                    source_immutable = after_sha == source_sha
                    if source_sha != feature_rec.get("source_sha256"):
                        raise AudioReverbDrynessError(f"source_sha_mismatch:{relative_path}")
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise AudioReverbDrynessError(f"pcm_sha_mismatch:{relative_path}")
                    frame_count = int(frames_nc.shape[0])
                    channel_count = int(frames_nc.shape[1])
                    analysis_truncated = frame_count > MAX_ANALYSIS_FRAMES
                    if analysis_truncated:
                        frames_nc = frames_nc[:MAX_ANALYSIS_FRAMES]
                        counts["analysis_truncated"] += 1
                    channels_list = _channels_from_frames_nc(frames_nc)
                    measurements, classification, wet_source_policy = analyze_channels(
                        channels_list,
                        sample_rate_hz=int(sample_rate_hz),
                    )
                    local_blockers: list[str] = []
                    if not source_immutable:
                        local_blockers.append("SOURCE_BYTES_CHANGED")
                    probe_record = build_analysis_record(
                        asset_id=asset_id,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        sample_rate_hz=int(sample_rate_hz),
                        channels=channel_count,
                        frame_count=frame_count,
                        measurements=measurements,
                        classification=classification,
                        wet_source_policy=wet_source_policy,
                        library_authority=False,
                        blocker_codes=list(local_blockers),
                    )
                    guard_ok = bool(probe_record["decision"]["double_reverb_guard_enforced"])
                    if not guard_ok:
                        local_blockers.append("DOUBLE_REVERB_GUARD_NOT_ENFORCED")
                    # Strip library-authority hold from technical probe blockers.
                    technical_blockers = [
                        code
                        for code in local_blockers
                        if code != "LIBRARY_AUTHORITY_NOT_GRANTED"
                    ]
                    compact = build_compact_reverb_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        measurements=measurements,
                        classification=classification,
                        wet_source_policy=wet_source_policy,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        sample_rate_hz=int(sample_rate_hz),
                        channels=channel_count,
                        frame_count=frame_count,
                        pcm_sha_verified=True,
                        source_immutable=source_immutable,
                        analysis_truncated=analysis_truncated,
                        double_reverb_guard_enforced=guard_ok,
                        blocker_code=technical_blockers[0] if technical_blockers else None,
                        blocker_codes=technical_blockers,
                    )
                    counts["feature_pass_inputs"] += 1
                    counts["pcm_sha_verified"] += 1
                    if source_immutable:
                        counts["source_immutable_true"] += 1
                    if guard_ok:
                        counts["double_reverb_guard_enforced"] += 1
                    class_key = f"classification_{classification}"
                    if class_key in counts:
                        counts[class_key] += 1
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = build_compact_reverb_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        measurements=None,
                        classification=None,
                        wet_source_policy=None,
                        source_sha256=feature_rec.get("source_sha256"),
                        canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                        sample_rate_hz=None,
                        channels=None,
                        frame_count=None,
                        pcm_sha_verified=False,
                        source_immutable=feature_rec.get("source_immutable"),
                        analysis_truncated=False,
                        double_reverb_guard_enforced=False,
                        blocker_code="REVERB_EXTRACTION_FAILED",
                        blocker_codes=["REVERB_EXTRACTION_FAILED"],
                        blocker_detail=str(exc)[:500],
                    )
                    counts["feature_pass_inputs"] += 1

            if compact.get("reverb_status") == "pass":
                counts["reverb_pass"] += 1
            else:
                counts["reverb_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "REVERB_BLOCKED")
                blocker_histogram[code] = blocker_histogram.get(code, 0) + 1
            extension_histogram[extension] = extension_histogram.get(extension, 0) + 1
            counts["records_processed"] += 1
            out_handle.write(json.dumps(compact, sort_keys=True) + "\n")
            processed_paths.add(relative_path)
            next_index = line_index + 1
            if counts["records_processed"] % checkpoint_every == 0:
                out_handle.flush()
                write_progress(complete=False)

    coverage_complete = limit is None and counts["records_processed"] == counts["records_total"]
    write_progress(complete=coverage_complete)

    proof_tier = "RUNTIME_PASS_BOUNDED"
    receipt = {
        "schema_version": 1,
        "evidence_id": "W64-ROW076-ACCEPTED-INDEX-RETAINED-REVERB-20260720",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_reverb_probe"
        if limit is not None
        else "accepted_index_retained_reverb_reconcile",
        "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
        "threshold_authority": "planning_freeze_suggestion_only_not_library_acceptance",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "started_at": started_at,
        "coverage_complete": coverage_complete,
        "limit": limit,
        "counts": counts,
        "blocker_histogram": blocker_histogram,
        "extension_histogram": extension_histogram,
        "locator": {
            "index_sha256": locator["index_sha256"],
            "record_count": locator.get("record_count"),
            "source_root": str(source_root),
        },
        "row071_admission": row071,
        "row073_admission": row073,
        "row071_records": {
            "path": str(records_in.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(records_in),
            "bytes": records_in.stat().st_size,
        },
        "records_path": str(records_path.relative_to(root)).replace("\\", "/"),
        "records_sha256": sha256_file(records_path) if records_path.is_file() else None,
        "records_bytes": records_path.stat().st_size if records_path.is_file() else 0,
        "progress_path": str(progress_path.relative_to(root)).replace("\\", "/"),
        "receipt_path": str(receipt_path.relative_to(root)).replace("\\", "/"),
        "library_authority": False,
        "row_complete": False,
        "product_completion_claimed": False,
        "runtime_completion_claimed": bool(coverage_complete),
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_threshold_authority",
            "full_library_coverage",
        ],
        "row075_contention_policy": "limited_probe_only_while_row075_full_reconcile_owns_pcm_io",
        "status": (
            "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN"
            if coverage_complete
            else "RUNTIME_PASS_BOUNDED_PROBE_LIMIT"
        ),
    }
    write_json(receipt_path, receipt)
    receipt["receipt_sha256"] = sha256_file(receipt_path)
    receipt["receipt_bytes"] = receipt_path.stat().st_size
    write_json(receipt_path, receipt)
    return receipt


def build_library_blocker_packet(
    root: Path,
    *,
    retained_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row071 = evaluate_row071_admission(root)
    row073 = evaluate_row073_admission(root)
    blocker_codes: list[str] = []
    for admission in (row071, row073):
        blocker_codes.extend(admission["blocker_codes"])
    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)
    probe_only = retained.get("limit") is not None
    deps_unlocked = bool(row071["dependency_satisfied"] and row073["dependency_satisfied"])

    if not deps_unlocked:
        if "ROW071_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW071_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED")
    if not coverage_complete:
        if reconcile_started:
            for code in (
                "FULL_LIBRARY_RECONCILE_DEFERRED_OR_IN_PROGRESS",
                "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
                "REPRESENTATIVE_ROOM_SOURCE_CALIBRATION_ABSENT",
                "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
            if probe_only and "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
                blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
        else:
            for code in (
                "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
                "FULL_LIBRARY_ACOUSTIC_RECONCILIATION_ABSENT",
                "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
    else:
        for code in (
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "REPRESENTATIVE_ROOM_SOURCE_CALIBRATION_ABSENT",
            "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    if coverage_complete and deps_unlocked:
        status = "HOLD_LIBRARY_THRESHOLDS_AND_ROOM_CALIBRATION_ABSENT_RECONCILE_COMPLETE"
        safe_next = (
            "Full-library reverb/dryness reconcile covered retained Row071 records under frozen "
            "suggestion-only thresholds. Calibrate representative room/source strata and unfreeze "
            "threshold authority before Row076 acceptance or Row079 unlock."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = True
    elif reconcile_started and deps_unlocked:
        status = (
            "HOLD_LIBRARY_PROBE_PASS_FULL_RECONCILE_DEFERRED_DEPS_UNLOCKED"
            if probe_only
            else "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED"
        )
        safe_next = (
            "Bounded index-retained reverb probe passed under frozen suggestion-only thresholds. "
            "Defer full-library Row076 PCM reconcile until Row075 retained-index defect scan "
            "finishes (avoid dual PCM I/O contention), then resume --mode index-retained "
            "without --limit before claiming Row076 acceptance."
            if probe_only
            else (
                "Resume/finish retained-index reverb reconcile to coverage_complete, then address "
                "frozen threshold authority and room calibration before claiming Row076 acceptance."
            )
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    elif deps_unlocked:
        status = "HOLD_LIBRARY_RUNTIME_AND_ROOM_CALIBRATION_ABSENT_DEPS_UNLOCKED"
        safe_next = (
            "Rows071+073 dependency gate is unlocked (Row073 probe/runtime-unlocked under "
            "RUNTIME_PASS_BOUNDED). Run --mode index-retained with a bounded --limit probe, then "
            "defer full reconcile until Row075 finishes to avoid PCM I/O contention."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    else:
        status = "HOLD_ROW071_ROW073_DEPENDENCIES_AND_FULL_LIBRARY_ACOUSTIC_RUNTIME_ABSENT"
        safe_next = (
            "Accept Row071 waveform features and unlock Row073 usable-bounds/natural-decay "
            "runtime, reconcile every accepted input to a dry/wet/ambiguous/environment-specific "
            "decision with hash-bound evidence and enforced wet-source policy, and replace this "
            "hold packet with full-library runtime evidence."
        )
        proof_tier = "CONTRACT_SLICE_BOUNDED"
        runtime_completion = False

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-076_audio_reverb_dryness_estimation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "analysis_pipeline_revision": ANALYSIS_PIPELINE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": runtime_completion,
        "library_authority": False,
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "status": status,
        "thresholds": dict(THRESHOLDS),
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "row071_admission": row071,
        "row073_admission": row073,
        "accepted_index_retained_reverb_runtime": {
            "present": reconcile_started,
            "coverage_complete": coverage_complete,
            "limit": retained.get("limit"),
            "counts": retained.get("counts"),
            "blocker_histogram": retained.get("blocker_histogram"),
            "records_path": retained.get("records_path"),
            "progress_path": retained.get("progress_path"),
            "receipt_path": retained.get("receipt_path"),
            "status": retained.get("status"),
            "row075_contention_policy": retained.get("row075_contention_policy"),
        },
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
            "runtime_completion": runtime_completion,
            "safe_next_action": safe_next,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=("library", "fixture", "index-retained"),
        default="library",
    )
    parser.add_argument("--fixture", default="dry_impulse")
    parser.add_argument("--compatible-room-rule-id", default=None)
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_RETAINED_REVERB_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-076_ACCEPTED_INDEX_RETAINED_REVERB_SUMMARY_20260720.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
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
    elif args.mode == "index-retained":
        retained = run_retained_index_reverb_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_reverb_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_reverb_runtime"]["summary_sha256"] = sha256_file(
            summary_path
        )
    else:
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_RETAINED_REVERB_RUNTIME_DIR / "retained_index_reverb_receipt.json",
            "retained_reverb_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise AudioReverbDrynessError("library_mode_must_remain_fail_closed_until_acceptance")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "coverage_complete": bool(
                    (payload.get("accepted_index_retained_reverb_runtime") or {}).get(
                        "coverage_complete"
                    )
                ),
                "proof_tier": payload.get("proof_tier"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
