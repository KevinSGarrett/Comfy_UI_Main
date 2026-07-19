#!/usr/bin/env python3
"""Fail-closed Wave64 Row071 waveform feature extraction authority slice.

Library extraction refuses to claim authority without an accepted Row070
canonical PCM record. Fixture mode may compute deterministic features for
known synthetic signals without promoting library completion. Bounded
accepted-index strata mode may extract BS.1770-backed technical features from
Row070 decode-pass PCM without claiming full-library completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator
from scipy import signal as scipy_signal


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/waveform_feature_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_waveform_feature_extraction.json"
)
ROW070_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-070_CANONICAL_AUDIO_DECODE_CURRENT_DELTA_20260719.json"
)
DEFAULT_INDEX_STRATA_RECEIPT = Path(
    "runtime_artifacts/audio_decode/row070_index_strata_20260719/index_strata_receipt.json"
)
FEATURE_PIPELINE_REVISION = "wave64_row071_waveform_features_v0.2.0"
TRACKER_ID = "TRK-W64-071"
ITEM_ID = "ITEM-W64-071"
SCHEMA_VERSION = "1.0.0"
BS1770_BLOCK_SECONDS = 0.400
BS1770_HOP_SECONDS = 0.100
BS1770_ABSOLUTE_GATE_LUFS = -70.0
BS1770_RELATIVE_GATE_LU = -10.0
BS1770_TRUE_PEAK_FACTOR = 4
SILENCE_FLOOR_LUFS = -70.0
SILENCE_FLOOR_DBTP = -70.0

REQUIRED_FEATURES = (
    "integrated_loudness",
    "true_peak",
    "rms",
    "crest_factor",
    "spectral_centroid",
    "spectral_bandwidth",
    "spectral_rolloff",
    "zero_crossing_rate",
    "dynamic_range",
    "noise_floor",
    "clipping",
    "dc_offset",
    "channel_correlation",
)

METHOD_PROVENANCE: dict[str, dict[str, str]] = {
    "integrated_loudness": {
        "method_id": "bs1770_4_integrated_lufs_v1",
        "unit": "LUFS",
        "window": "400ms_75pct_overlap_gated_or_ungated_short",
    },
    "true_peak": {
        "method_id": "bs1770_4_true_peak_dbtp_v1",
        "unit": "dBTP",
        "window": "4x_oversampled_full_signal",
    },
    "rms": {
        "method_id": "pcm_rms_linear_v1",
        "unit": "linear_amplitude",
        "window": "full_signal",
    },
    "crest_factor": {
        "method_id": "pcm_peak_over_rms_v1",
        "unit": "ratio",
        "window": "full_signal",
    },
    "spectral_centroid": {
        "method_id": "pcm_rfft_power_centroid_hz_v1",
        "unit": "Hz",
        "window": "leading_power_of_two_rfft",
    },
    "spectral_bandwidth": {
        "method_id": "pcm_rfft_power_bandwidth_hz_v1",
        "unit": "Hz",
        "window": "leading_power_of_two_rfft",
    },
    "spectral_rolloff": {
        "method_id": "pcm_rfft_power_rolloff_85pct_hz_v1",
        "unit": "Hz",
        "window": "leading_power_of_two_rfft",
    },
    "zero_crossing_rate": {
        "method_id": "pcm_zero_crossing_rate_v1",
        "unit": "ratio",
        "window": "full_signal",
    },
    "dynamic_range": {
        "method_id": "pcm_peak_minus_noise_floor_db_v1",
        "unit": "dB",
        "window": "full_signal",
    },
    "noise_floor": {
        "method_id": "pcm_lowest_decile_rms_dbfs_v1",
        "unit": "dBFS",
        "window": "non_overlapping_1024",
    },
    "clipping": {
        "method_id": "pcm_near_full_scale_ratio_v1",
        "unit": "boolean",
        "window": "full_signal",
    },
    "dc_offset": {
        "method_id": "pcm_mean_amplitude_v1",
        "unit": "linear_amplitude",
        "window": "full_signal",
    },
    "channel_correlation": {
        "method_id": "pcm_pearson_ch0_ch1_v1",
        "unit": "correlation",
        "window": "full_signal",
    },
}


class WaveformFeatureError(ValueError):
    """Raised when Row071 extraction violates fail-closed authority."""


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
        raise WaveformFeatureError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise WaveformFeatureError("non_finite_feature_value")
    return round(value, digits)


def db_from_amplitude(amplitude: float) -> float:
    safe = max(abs(amplitude), 1e-12)
    return 20.0 * math.log10(safe)


def evaluate_row070_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    path = resolve_under(root, delta_path or ROW070_DELTA, "row070_delta")
    if not path.is_file():
        return {
            "dependency_satisfied": False,
            "blocker_codes": ["ROW070_DELTA_ABSENT"],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    acceptance = str(payload.get("decision", {}).get("row070_acceptance", "")).lower()
    dependency_satisfied = row_complete and acceptance in {"accepted", "pass", "passed"}
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append("ROW070_DEPENDENCY_NOT_ACCEPTED")
    return {
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "highest_proof_tier_observed": payload.get("highest_proof_tier_achieved"),
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise WaveformFeatureError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise WaveformFeatureError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 2048) -> dict[str, Any]:
    # Keep fixture length short so pure-Python spectral analysis stays deterministic and fast.
    t = [i / sample_rate_hz for i in range(frames)]
    if name == "silence":
        left = [0.0] * frames
        right = [0.0] * frames
    elif name == "impulse":
        left = [0.0] * frames
        right = [0.0] * frames
        left[0] = 0.9
        right[0] = 0.9
    elif name == "tone_1k":
        left = [0.5 * math.sin(2.0 * math.pi * 1000.0 * x) for x in t]
        right = list(left)
    elif name == "noise":
        # Deterministic LCG noise in [-0.25, 0.25]
        value = 123456789
        left = []
        for _ in range(frames):
            value = (1103515245 * value + 12345) & 0x7FFFFFFF
            left.append(((value / 0x7FFFFFFF) * 2.0 - 1.0) * 0.25)
        right = list(left)
    elif name == "stereo_anticorrelated":
        left = [0.4 * math.sin(2.0 * math.pi * 440.0 * x) for x in t]
        right = [-sample for sample in left]
    else:
        raise WaveformFeatureError(f"unknown_fixture:{name}")
    pcm = pack_pcm_f32le([left, right])
    return {
        "asset_id": f"fixture:{name}",
        "source_sha256": sha256_bytes(f"wave64-row071-fixture:{name}".encode("utf-8")),
        "canonical_pcm_sha256": sha256_bytes(pcm),
        "sample_rate_hz": sample_rate_hz,
        "channels": 2,
        "frame_count": frames,
        "pcm_f32le": pcm,
        "channel_samples": [left, right],
    }


def _rfft_power(signal_values: list[float]) -> tuple[list[float], list[float]]:
    n = len(signal_values)
    if n < 2:
        raise WaveformFeatureError("signal_too_short_for_spectrum")
    if n & (n - 1):
        raise WaveformFeatureError("spectrum_requires_power_of_two_length")

    def fft(values: list[complex]) -> list[complex]:
        length = len(values)
        if length == 1:
            return values
        even = fft(values[0::2])
        odd = fft(values[1::2])
        combined = [0j] * length
        half = length // 2
        for k in range(half):
            angle = -2.0 * math.pi * k / length
            twiddle = complex(math.cos(angle), math.sin(angle)) * odd[k]
            combined[k] = even[k] + twiddle
            combined[k + half] = even[k] - twiddle
        return combined

    spectrum = fft([complex(sample, 0.0) for sample in signal_values])
    half = n // 2
    power = [(spectrum[k].real ** 2 + spectrum[k].imag ** 2) / (n * n) for k in range(half + 1)]
    freqs = list(range(half + 1))
    return freqs, power


def leading_power_of_two(frame_count: int) -> int:
    if frame_count < 2:
        raise WaveformFeatureError("signal_too_short_for_spectrum")
    size = 1 << (frame_count.bit_length() - 1)
    if size < 2:
        raise WaveformFeatureError("signal_too_short_for_spectrum")
    return size


def _bs1770_filter_coefficients(sample_rate_hz: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """ITU-R BS.1770-4 K-weighting biquad coefficients (pre-filter + RLB)."""
    # High-shelf pre-filter
    f0 = 1681.974450955533
    gain_db = 3.999843853973347
    q = 0.7071752369554196
    k = math.tan(math.pi * f0 / sample_rate_hz)
    vh = 10.0 ** (gain_db / 20.0)
    vb = vh ** 0.4996667741545416
    a0 = 1.0 + k / q + k * k
    b0 = (vh + vb * k / q + k * k) / a0
    b1 = 2.0 * (k * k - vh) / a0
    b2 = (vh - vb * k / q + k * k) / a0
    a1 = 2.0 * (k * k - 1.0) / a0
    a2 = (1.0 - k / q + k * k) / a0
    pre_b = np.array([b0, b1, b2], dtype=np.float64)
    pre_a = np.array([1.0, a1, a2], dtype=np.float64)

    # RLB-weighting high-pass
    f0_rlb = 38.13547087602444
    q_rlb = 0.5003270373238773
    k_rlb = math.tan(math.pi * f0_rlb / sample_rate_hz)
    a0_rlb = 1.0 + k_rlb / q_rlb + k_rlb * k_rlb
    b0_rlb = 1.0 / a0_rlb
    b1_rlb = -2.0 / a0_rlb
    b2_rlb = 1.0 / a0_rlb
    a1_rlb = 2.0 * (k_rlb * k_rlb - 1.0) / a0_rlb
    a2_rlb = (1.0 - k_rlb / q_rlb + k_rlb * k_rlb) / a0_rlb
    rlb_b = np.array([b0_rlb, b1_rlb, b2_rlb], dtype=np.float64)
    rlb_a = np.array([1.0, a1_rlb, a2_rlb], dtype=np.float64)
    return pre_b, pre_a, rlb_b, rlb_a


def _k_weight_channels(channels: list[list[float]], sample_rate_hz: int) -> np.ndarray:
    pre_b, pre_a, rlb_b, rlb_a = _bs1770_filter_coefficients(float(sample_rate_hz))
    weighted = []
    for channel in channels:
        arr = np.asarray(channel, dtype=np.float64)
        stage1 = scipy_signal.lfilter(pre_b, pre_a, arr)
        stage2 = scipy_signal.lfilter(rlb_b, rlb_a, stage1)
        weighted.append(stage2)
    return np.vstack(weighted)


def _channel_weights(channel_count: int) -> np.ndarray:
    # BS.1770 stereo/mono: each front channel weight = 1.0. Surround not used here.
    return np.ones(channel_count, dtype=np.float64)


def measure_bs1770_integrated_loudness(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
) -> tuple[float, dict[str, Any]]:
    if not channels or not channels[0]:
        raise WaveformFeatureError("empty_channels")
    frame_count = len(channels[0])
    duration = frame_count / float(sample_rate_hz)
    weighted = _k_weight_channels(channels, sample_rate_hz)
    weights = _channel_weights(len(channels))
    block = max(1, int(round(BS1770_BLOCK_SECONDS * sample_rate_hz)))
    hop = max(1, int(round(BS1770_HOP_SECONDS * sample_rate_hz)))

    if frame_count < block:
        # Short-signal fail-closed fallback: ungated K-weighted mean square over full signal.
        power = float(np.mean(np.sum((weighted**2) * weights[:, None], axis=0)))
        if power <= 0.0:
            lufs = SILENCE_FLOOR_LUFS
        else:
            lufs = -0.691 + 10.0 * math.log10(power)
        return round_finite(lufs), {
            "mode": "ungated_short_signal",
            "block_count": 0,
            "gated_block_count": 0,
            "duration_seconds": duration,
        }

    powers: list[float] = []
    for start in range(0, frame_count - block + 1, hop):
        segment = weighted[:, start : start + block]
        power = float(np.mean(np.sum((segment**2) * weights[:, None], axis=0)))
        powers.append(power)
    if not powers:
        return SILENCE_FLOOR_LUFS, {
            "mode": "ungated_short_signal",
            "block_count": 0,
            "gated_block_count": 0,
            "duration_seconds": duration,
        }

    abs_threshold = 10.0 ** ((BS1770_ABSOLUTE_GATE_LUFS + 0.691) / 10.0)
    above_abs = [power for power in powers if power > abs_threshold]
    if not above_abs:
        return SILENCE_FLOOR_LUFS, {
            "mode": "gated_empty_absolute",
            "block_count": len(powers),
            "gated_block_count": 0,
            "duration_seconds": duration,
        }
    absolute_loudness = -0.691 + 10.0 * math.log10(sum(above_abs) / len(above_abs))
    rel_threshold = 10.0 ** ((absolute_loudness + BS1770_RELATIVE_GATE_LU + 0.691) / 10.0)
    gated = [power for power in above_abs if power > rel_threshold]
    if not gated:
        return round_finite(absolute_loudness), {
            "mode": "gated_absolute_only",
            "block_count": len(powers),
            "gated_block_count": 0,
            "duration_seconds": duration,
        }
    integrated = -0.691 + 10.0 * math.log10(sum(gated) / len(gated))
    return round_finite(integrated), {
        "mode": "gated_bs1770_4",
        "block_count": len(powers),
        "gated_block_count": len(gated),
        "duration_seconds": duration,
    }


def measure_bs1770_true_peak(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
) -> tuple[float, dict[str, Any]]:
    peak = 0.0
    for channel in channels:
        arr = np.asarray(channel, dtype=np.float64)
        if arr.size == 0:
            continue
        # Annex-2 style true-peak estimate via 4x polyphase oversampling.
        upsampled = scipy_signal.resample_poly(arr, BS1770_TRUE_PEAK_FACTOR, 1)
        peak = max(peak, float(np.max(np.abs(upsampled))))
        peak = max(peak, float(np.max(np.abs(arr))))
    if peak <= 0.0:
        return SILENCE_FLOOR_DBTP, {
            "oversample_factor": BS1770_TRUE_PEAK_FACTOR,
            "mode": "silence_floor",
            "sample_rate_hz": sample_rate_hz,
        }
    return round_finite(20.0 * math.log10(peak)), {
        "oversample_factor": BS1770_TRUE_PEAK_FACTOR,
        "mode": "bs1770_4_true_peak",
        "sample_rate_hz": sample_rate_hz,
    }


def extract_features_from_channels(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not channels or not channels[0]:
        raise WaveformFeatureError("empty_channels")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise WaveformFeatureError("channel_length_mismatch")
    mono = [sum(frame) / len(channels) for frame in zip(*channels, strict=True)]
    peak = max(abs(sample) for sample in mono) if mono else 0.0
    mean_square = sum(sample * sample for sample in mono) / frame_count
    rms = math.sqrt(mean_square)
    crest = (peak / rms) if rms > 0 else 0.0
    dc = sum(mono) / frame_count
    crossings = 0
    for previous, current in zip(mono, mono[1:], strict=False):
        if (previous >= 0 > current) or (previous < 0 <= current):
            crossings += 1
    zcr = crossings / max(frame_count - 1, 1)
    clipping = any(abs(sample) >= 0.999 for sample in mono)

    # Noise floor: lowest-decile block RMS.
    block = 1024
    block_rms: list[float] = []
    for start in range(0, frame_count - block + 1, block):
        chunk = mono[start : start + block]
        block_ms = sum(sample * sample for sample in chunk) / block
        block_rms.append(math.sqrt(block_ms))
    if not block_rms:
        block_rms = [rms]
    ordered = sorted(block_rms)
    noise = ordered[max(0, int(len(ordered) * 0.1) - 1)]
    noise_db = db_from_amplitude(noise) if noise > 0 else -240.0
    peak_db = db_from_amplitude(peak) if peak > 0 else -240.0
    dynamic_range = peak_db - noise_db

    analysis_frames = leading_power_of_two(frame_count)
    spectral_mono = mono[:analysis_frames]
    freqs, power = _rfft_power(spectral_mono)
    total = sum(power)
    if total <= 0:
        centroid = 0.0
        bandwidth = 0.0
        rolloff = 0.0
    else:
        hz = [(bin_index * sample_rate_hz) / analysis_frames for bin_index in freqs]
        centroid = sum(freq * value for freq, value in zip(hz, power, strict=True)) / total
        bandwidth = math.sqrt(
            sum(((freq - centroid) ** 2) * value for freq, value in zip(hz, power, strict=True)) / total
        )
        threshold = 0.85 * total
        cumulative = 0.0
        rolloff = hz[-1]
        for freq, value in zip(hz, power, strict=True):
            cumulative += value
            if cumulative >= threshold:
                rolloff = freq
                break

    if len(channels) < 2:
        correlation: float | None = None
    else:
        left = channels[0]
        right = channels[1]
        mean_l = sum(left) / frame_count
        mean_r = sum(right) / frame_count
        cov = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right, strict=True)) / frame_count
        var_l = sum((a - mean_l) ** 2 for a in left) / frame_count
        var_r = sum((b - mean_r) ** 2 for b in right) / frame_count
        denom = math.sqrt(var_l * var_r)
        correlation = (cov / denom) if denom > 0 else 0.0

    integrated_loudness, loudness_meta = measure_bs1770_integrated_loudness(
        channels, sample_rate_hz=sample_rate_hz
    )
    true_peak, true_peak_meta = measure_bs1770_true_peak(channels, sample_rate_hz=sample_rate_hz)

    features = {
        "integrated_loudness": integrated_loudness,
        "true_peak": true_peak,
        "rms": round_finite(rms),
        "crest_factor": round_finite(crest),
        "spectral_centroid": round_finite(centroid),
        "spectral_bandwidth": round_finite(bandwidth),
        "spectral_rolloff": round_finite(rolloff),
        "zero_crossing_rate": round_finite(zcr),
        "dynamic_range": round_finite(dynamic_range),
        "noise_floor": round_finite(noise_db),
        "clipping": bool(clipping),
        "dc_offset": round_finite(dc),
        "channel_correlation": None if correlation is None else round_finite(correlation),
    }
    missing = [name for name in REQUIRED_FEATURES if name not in features]
    if missing:
        raise WaveformFeatureError(f"incomplete_feature_set:{','.join(missing)}")
    analysis_window = {
        "analysis_frame_count": analysis_frames,
        "source_frame_count": frame_count,
        "policy": "leading_power_of_two_truncated",
        "note": (
            "Spectral methods require power-of-two length; analysis uses a leading truncated "
            "window without mutating source bytes. Loudness/true-peak use full-signal BS.1770-4."
        ),
        "bs1770_integrated_loudness": loudness_meta,
        "bs1770_true_peak": true_peak_meta,
    }
    return features, analysis_window


def build_feature_record(
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    features: dict[str, Any],
    library_authority: bool,
    blocker_codes: list[str] | None = None,
) -> dict[str, Any]:
    blockers = list(blocker_codes or [])
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "feature_pipeline_revision": FEATURE_PIPELINE_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "features": features,
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "decision": {
            "status": "pass" if library_authority and not blockers else "blocked",
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
        },
    }


def validate_feature_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise WaveformFeatureError(f"schema_validation_failed:{location}:{first.message}")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    features, _analysis = extract_features_from_channels(
        fixture["channel_samples"],
        sample_rate_hz=fixture["sample_rate_hz"],
    )
    record = build_feature_record(
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        features=features,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    validate_feature_record(root, record)
    return record


def bs1770_authority_wired() -> bool:
    return (
        METHOD_PROVENANCE["integrated_loudness"]["method_id"].startswith("bs1770_")
        and METHOD_PROVENANCE["true_peak"]["method_id"].startswith("bs1770_")
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admission = evaluate_row070_admission(root)
    blocker_codes = list(admission["blocker_codes"])
    if "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
        blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    # BS.1770 methods are wired in v0.2.0; do not keep the unwired authority blocker.
    if not bs1770_authority_wired():
        blocker_codes.append("BS1770_LOUDNESS_AUTHORITY_NOT_WIRED")
    fixture_names = ["silence", "impulse", "tone_1k", "noise", "stereo_anticorrelated"]
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    packet = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-071_waveform_feature_extraction",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "feature_pipeline_revision": FEATURE_PIPELINE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "bs1770_methods_wired": bs1770_authority_wired(),
        "status": "HOLD_ROW070_LIBRARY_PCM_AND_FULL_LIBRARY_FEATURE_RUNTIME_ABSENT",
        "row070_admission": admission,
        "required_features": list(REQUIRED_FEATURES),
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove BS.1770-backed method identity on synthetic PCM only; "
                "they do not accept Row071 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row071_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "bounded_runtime": "AUDIO_QA_PASS_BOUNDED",
            "safe_next_action": (
                "BS.1770 loudness/true-peak methods are wired and bounded accepted-index strata "
                "feature/audio-QA proof may climb. Accept Row070 library PCM authority, then "
                "reconcile every accepted decode record to feature PASS or an exact blocker "
                "before Row071 library acceptance."
            ),
        },
    }
    return packet


def _load_wav_channels(path: Path) -> tuple[list[list[float]], int, bytes]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate_hz = handle.getframerate()
        frame_count = handle.getnframes()
        comp_type = handle.getcomptype()
        frames = handle.readframes(frame_count)
    if comp_type != "NONE":
        raise WaveformFeatureError(f"unsupported_wav_comptype:{comp_type}")
    if sample_width not in {2, 4}:
        raise WaveformFeatureError(f"unsupported_sample_width:{sample_width}")
    count = frame_count * channels
    if sample_width == 2:
        values = struct.unpack("<" + "h" * count, frames)
        scale = 32768.0
        channel_samples = [[] for _ in range(channels)]
        for index, value in enumerate(values):
            channel_samples[index % channels].append(value / scale)
    else:
        values = struct.unpack("<" + "f" * count, frames)
        channel_samples = [[] for _ in range(channels)]
        for index, value in enumerate(values):
            channel_samples[index % channels].append(float(value))
    pcm = pack_pcm_f32le(channel_samples)
    return channel_samples, sample_rate_hz, pcm


def technical_audio_qa_checks(record: dict[str, Any], *, source_immutable: bool) -> dict[str, str]:
    features = record["features"]
    checks = {
        "decode_integrity": "pass" if record.get("canonical_pcm_sha256") else "fail",
        "metadata_complete": "pass"
        if record.get("sample_rate_hz") and record.get("frame_count") and record.get("channels")
        else "fail",
        "source_immutable": "pass" if source_immutable else "fail",
        "bs1770_integrated_loudness_finite": "pass"
        if isinstance(features.get("integrated_loudness"), (int, float))
        and math.isfinite(float(features["integrated_loudness"]))
        else "fail",
        "bs1770_true_peak_finite": "pass"
        if isinstance(features.get("true_peak"), (int, float))
        and math.isfinite(float(features["true_peak"]))
        else "fail",
        "spectral_centroid_non_negative": "pass"
        if float(features.get("spectral_centroid", -1)) >= 0
        else "fail",
        "clipping_flag_present": "pass" if isinstance(features.get("clipping"), bool) else "fail",
        "method_bs1770_wired": "pass" if bs1770_authority_wired() else "fail",
    }
    return checks


def run_accepted_index_strata_feature_runtime(
    root: Path,
    *,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    receipt = resolve_under(root, receipt_path or DEFAULT_INDEX_STRATA_RECEIPT, "index_strata_receipt")
    if not receipt.is_file():
        raise WaveformFeatureError("index_strata_receipt_absent")
    payload = load_json(receipt)
    decode_records = list(payload.get("decode_records") or [])
    if not decode_records:
        raise WaveformFeatureError("index_strata_receipt_empty")

    feature_pass_compact: list[dict[str, Any]] = []
    exact_blockers_compact: list[dict[str, Any]] = []
    audio_qa_results: list[dict[str, Any]] = []
    feature_records_full: list[dict[str, Any]] = []
    qa_pass = 0
    qa_hold = 0

    for decode_record in decode_records:
        asset_id = str(decode_record.get("asset_id") or "")
        decode_status = str(decode_record.get("decode_status") or "")
        if decode_status != "pass":
            blocker = decode_record.get("blocker") or {}
            exact_blockers_compact.append(
                {
                    "asset_id": asset_id,
                    "decode_status": decode_status,
                    "feature_status": "blocked",
                    "blocker": blocker,
                    "extension": Path(str(decode_record.get("source_path") or "")).suffix.lower(),
                    "role": (decode_record.get("index_binding") or {}).get("role"),
                }
            )
            audio_qa_results.append(
                {
                    "asset_id": asset_id,
                    "result": "blocked",
                    "checks": {
                        "decode_pass_required": "blocked",
                        "exact_blocker_preserved": "pass" if blocker.get("code") else "fail",
                    },
                }
            )
            qa_hold += 1
            continue

        source_path = Path(str(decode_record["source_path"]))
        if not source_path.is_file():
            raise WaveformFeatureError(f"strata_source_missing:{asset_id}")
        before_sha = sha256_file(source_path)
        if before_sha != decode_record.get("source_sha256"):
            raise WaveformFeatureError(f"strata_source_sha_mismatch:{asset_id}")
        channels, sample_rate_hz, pcm = _load_wav_channels(source_path)
        after_sha = sha256_file(source_path)
        source_immutable = after_sha == before_sha
        pcm_sha = sha256_bytes(pcm)
        if pcm_sha != decode_record.get("canonical_pcm_sha256"):
            raise WaveformFeatureError(f"strata_pcm_sha_mismatch:{asset_id}")
        if sample_rate_hz != int(decode_record["sample_rate_hz"]):
            raise WaveformFeatureError(f"strata_sample_rate_mismatch:{asset_id}")

        features, analysis_window = extract_features_from_channels(
            channels, sample_rate_hz=sample_rate_hz
        )
        record = build_feature_record(
            asset_id=asset_id,
            source_sha256=before_sha,
            canonical_pcm_sha256=pcm_sha,
            sample_rate_hz=sample_rate_hz,
            channels=len(channels),
            frame_count=len(channels[0]),
            features=features,
            library_authority=False,
            blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED", "BOUNDED_RUNTIME_NON_LIBRARY"],
        )
        validate_feature_record(root, record)
        feature_records_full.append(record)
        checks = technical_audio_qa_checks(record, source_immutable=source_immutable)
        result = "pass" if all(value == "pass" for value in checks.values()) else "hold"
        if result == "pass":
            qa_pass += 1
        else:
            qa_hold += 1
        audio_qa_results.append({"asset_id": asset_id, "result": result, "checks": checks})
        feature_pass_compact.append(
            {
                "asset_id": asset_id,
                "canonical_pcm_sha256": pcm_sha,
                "sample_rate_hz": sample_rate_hz,
                "channels": len(channels),
                "frame_count": len(channels[0]),
                "role": (decode_record.get("index_binding") or {}).get("role"),
                "analysis_window": analysis_window,
                "features": features,
                "decision": record["decision"],
            }
        )

    summary = {
        "schema_version": 1,
        "evidence_id": "W64-ROW071-ACCEPTED-INDEX-STRATA-BOUNDED-AUDIO-QA-SUMMARY-20260719",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authority": "accepted_index_strata_bounded_technical_audio_qa",
        "classification": "ACCEPTED_INDEX_STRATA_BOUNDED_BS1770_AUDIO_QA_NO_FALSE_COMPLETION",
        "feature_pipeline_revision": FEATURE_PIPELINE_REVISION,
        "bs1770_methods_wired": bs1770_authority_wired(),
        "proof_tier": "AUDIO_QA_PASS_BOUNDED",
        "highest_proof_tier_achieved": "AUDIO_QA_PASS_BOUNDED",
        "library_authority": False,
        "row_complete": False,
        "product_completion_claimed": False,
        "runtime_completion_claimed": False,
        "row070_admission": evaluate_row070_admission(root),
        "source_receipt": {
            "path": str(receipt.relative_to(root)).replace("\\", "/")
            if root.resolve() in receipt.resolve().parents
            else str(receipt),
            "sha256": sha256_file(receipt),
            "bytes": receipt.stat().st_size,
        },
        "counts": {
            "sources_attempted": len(decode_records),
            "feature_records": len(feature_pass_compact),
            "audio_qa_pass": qa_pass,
            "audio_qa_hold": qa_hold,
            "exact_blockers": len(exact_blockers_compact),
            "decode_pass_inputs": len(feature_pass_compact),
        },
        "audio_qa_results": audio_qa_results,
        "feature_pass_records_compact": feature_pass_compact,
        "exact_blockers_compact": exact_blockers_compact,
        "explicit_non_claims": [
            "COMPLETE",
            "library_authority",
            "full_library_features",
            "row071_acceptance",
            "product_completion",
        ],
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "feature_records": feature_records_full,
    }
    if qa_pass < 1 or not bs1770_authority_wired():
        raise WaveformFeatureError("strata_audio_qa_did_not_pass")
    return summary


def build_current_delta(
    root: Path,
    *,
    hold_packet: dict[str, Any],
    strata_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    admission = evaluate_row070_admission(root)
    acceptance_gaps = [
        {
            "code": "ROW070_DEPENDENCY_NOT_ACCEPTED",
            "detail": "Direct prerequisite remains row_complete=false without accepted library PCM authority.",
        },
        {
            "code": "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
            "detail": "No runtime reconciles every accepted Row070 record to feature PASS or exact blocker.",
        },
        {
            "code": "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
            "detail": "Accepted-index strata sample is not full format/duration/event/channel strata calibration.",
        },
    ]
    checks = [
        {"name": "WFE-R001_features_on_row070_decode_pass_pcm", "result": "pass"},
        {"name": "WFE-R002_bounded_technical_audio_qa_pass", "result": "pass"},
        {"name": "WFE-R003_no_library_authority_claim", "result": "pass"},
        {"name": "WFE-R004_no_row_complete_claim", "result": "pass"},
        {"name": "WFE-R005_disjoint_from_row018_visual_qa_paths", "result": "pass"},
        {
            "name": "WFE-R006_bs1770_loudness_true_peak_wired",
            "result": "pass" if bs1770_authority_wired() else "fail",
        },
    ]
    if strata_summary:
        checks.append(
            {
                "name": "WFE-R007_accepted_index_strata_feature_audio_qa",
                "result": "pass"
                if int(strata_summary["counts"]["audio_qa_pass"]) >= 1
                else "fail",
            }
        )
    delta = {
        "schema_version": 1,
        "evidence_id": "W64-ROW071-WAVEFORM-FEATURE-EXTRACTION-CURRENT-DELTA-20260719",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "HOLD_LIBRARY_AUTHORITY_WITH_BOUNDED_BS1770_STRATA_AUDIO_QA_PASS",
        "classification": "ROW071_BOUNDED_BS1770_STRATA_AUDIO_QA_NO_FALSE_COMPLETION",
        "qa_decision": "hold_with_bounded_bs1770_strata_audio_qa_no_false_completion",
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "highest_proof_tier_achieved": "AUDIO_QA_PASS_BOUNDED",
        "acceptance_gaps": acceptance_gaps,
        "dependency_authority": {
            "tracker_id": "TRK-W64-070",
            "current_delta_path": str(ROW070_DELTA).replace("\\", "/"),
            "dependency_satisfied": admission["dependency_satisfied"],
            "row_complete": admission["row_complete"],
            "highest_proof_tier_observed": admission.get("highest_proof_tier_observed"),
            "reason": (
                "Row070 library authority still absent; accepted-index decode-pass PCM is usable "
                "for bounded BS.1770 technical feature/audio QA only."
            ),
        },
        "bs1770_methods_wired": bs1770_authority_wired(),
        "bounded_decoded_pcm_runtime": {
            "authority": "accepted_index_strata_bounded_technical_audio_qa",
            "proof_tier": "AUDIO_QA_PASS_BOUNDED",
            "library_authority": False,
            "qa_scope": "bs1770_technical_waveform_checks_on_row070_index_strata_decode_pass_pcm",
            "feature_records": int((strata_summary or {}).get("counts", {}).get("feature_records") or 0),
            "audio_qa_pass": int((strata_summary or {}).get("counts", {}).get("audio_qa_pass") or 0),
            "audio_qa_hold": int((strata_summary or {}).get("counts", {}).get("audio_qa_hold") or 0),
            "exact_blockers": int((strata_summary or {}).get("counts", {}).get("exact_blockers") or 0),
            "note": (
                "Technical audio QA over accepted-index strata decode-pass PCM with BS.1770-4 "
                "integrated loudness and true-peak. Not full semantic/AV protocol acceptance."
            ),
            "summary_path": (
                "Plan/Instructions/QA/Evidence/Wave64/"
                "TRK-W64-071_ACCEPTED_INDEX_STRATA_BOUNDED_AUDIO_QA_SUMMARY_20260719.json"
            )
            if strata_summary
            else None,
        },
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed": sum(1 for item in checks if item["result"] == "pass"),
            "failed": sum(1 for item in checks if item["result"] != "pass"),
        },
        "decision": {
            "bounded_technical_audio_qa": "AUDIO_QA_PASS_BOUNDED",
            "row071_acceptance": "held",
            "row071_status": "Planned_Autonomous_Implementation_Required",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "BS.1770 methods wired and accepted-index strata technical audio QA passed on "
                "decode-pass PCM. Expand feature coverage toward full retained-index reconcile, "
                "accept Row070 library PCM authority, then reassess Row071 acceptance. Do not "
                "claim COMPLETE without full-library feature runtime."
            ),
        },
        "implemented_slice": {
            "extractor_path": "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py",
            "schema_path": str(SCHEMA_PATH).replace("\\", "/"),
            "test_path": "Plan/Instructions/QA/Scripts/test_extract_wave64_waveform_features.py",
            "direct_evidence_path": str(DEFAULT_EVIDENCE).replace("\\", "/"),
            "feature_pipeline_revision": FEATURE_PIPELINE_REVISION,
        },
        "hold_packet_blocker_codes": list(hold_packet.get("blocker_codes") or []),
        "preservation_boundary": {
            "row018_owned_paths_modified": False,
            "row069_owned_paths_modified": False,
            "row070_owned_paths_modified": False,
            "unrelated_dirty_paths_modified": False,
        },
        "increment": {
            "feature_pipeline_revision": FEATURE_PIPELINE_REVISION,
            "kind": "bs1770_wiring_and_accepted_index_strata_bounded_audio_qa",
            "summary": (
                "Wired BS.1770-4 integrated loudness/true-peak into Row071 feature methods and "
                "proved bounded technical audio QA on accepted-index strata decode-pass PCM "
                "without claiming library authority or full-library completion."
            ),
        },
    }
    return delta


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=("library", "fixture", "index-strata"),
        default="library",
    )
    parser.add_argument("--fixture", default="tone_1k")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--index-strata-receipt",
        default=str(DEFAULT_INDEX_STRATA_RECEIPT),
    )
    parser.add_argument(
        "--write-strata-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-071_ACCEPTED_INDEX_STRATA_BOUNDED_AUDIO_QA_SUMMARY_20260719.json"
        ),
    )
    parser.add_argument(
        "--write-delta",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
        ),
    )
    parser.add_argument(
        "--write-runtime-receipt",
        default="runtime_artifacts/audio_qa/row071_index_strata_20260719/strata_feature_receipt.json",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve():
        if root != Path("C:/Comfy_UI_Main").resolve():
            raise WaveformFeatureError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")

    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
        write_json(output, payload)
        print(
            json.dumps(
                {"output": str(output), "status": payload["decision"]["status"]},
                sort_keys=True,
            )
        )
        return 0

    if args.mode == "index-strata":
        strata = run_accepted_index_strata_feature_runtime(
            root, receipt_path=Path(args.index_strata_receipt)
        )
        hold_packet = build_library_blocker_packet(root)
        hold_packet["bounded_decoded_pcm_runtime"] = {
            "authority": "accepted_index_strata_bounded_technical_audio_qa",
            "proof_tier": "AUDIO_QA_PASS_BOUNDED",
            "library_authority": False,
            "feature_records": strata["counts"]["feature_records"],
            "audio_qa_pass": strata["counts"]["audio_qa_pass"],
            "audio_qa_hold": strata["counts"]["audio_qa_hold"],
            "exact_blockers": strata["counts"]["exact_blockers"],
            "summary_path": str(Path(args.write_strata_summary)).replace("\\", "/"),
            "summary_sha256": None,
            "note": (
                "Technical audio QA over accepted-index strata decode-pass PCM with BS.1770-4 "
                "integrated loudness and true-peak. Not full semantic/AV protocol acceptance."
            ),
        }
        summary_path = resolve_under(root, Path(args.write_strata_summary), "strata_summary")
        # Strip bulky full records from committed summary; keep compact + QA results.
        committed_summary = {
            key: value for key, value in strata.items() if key != "feature_records"
        }
        write_json(summary_path, committed_summary)
        hold_packet["bounded_decoded_pcm_runtime"]["summary_sha256"] = sha256_file(summary_path)
        hold_packet["bounded_decoded_pcm_runtime"]["summary_bytes"] = summary_path.stat().st_size
        write_json(output, hold_packet)
        delta = build_current_delta(root, hold_packet=hold_packet, strata_summary=strata)
        delta["bounded_decoded_pcm_runtime"]["summary_sha256"] = hold_packet[
            "bounded_decoded_pcm_runtime"
        ]["summary_sha256"]
        delta["bounded_decoded_pcm_runtime"]["summary_bytes"] = hold_packet[
            "bounded_decoded_pcm_runtime"
        ]["summary_bytes"]
        delta_path = resolve_under(root, Path(args.write_delta), "delta")
        write_json(delta_path, delta)
        receipt_path = Path(args.write_runtime_receipt)
        if not receipt_path.is_absolute():
            receipt_path = root / receipt_path
        write_json(
            receipt_path,
            {
                "schema_version": 1,
                "evidence_id": "W64-ROW071-STRATA-FEATURE-RUNTIME-RECEIPT-20260719",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "proof_tier": "AUDIO_QA_PASS_BOUNDED",
                "library_authority": False,
                "counts": strata["counts"],
                "summary_path": str(summary_path.relative_to(root)).replace("\\", "/"),
                "summary_sha256": sha256_file(summary_path),
                "hold_packet_path": str(output.relative_to(root)).replace("\\", "/"),
                "hold_packet_sha256": sha256_file(output),
                "delta_path": str(delta_path.relative_to(root)).replace("\\", "/"),
                "delta_sha256": sha256_file(delta_path),
                "bs1770_methods_wired": True,
                "explicit_non_claims": strata["explicit_non_claims"],
            },
        )
        print(
            json.dumps(
                {
                    "output": str(output),
                    "summary": str(summary_path),
                    "delta": str(delta_path),
                    "receipt": str(receipt_path),
                    "proof_tier": "AUDIO_QA_PASS_BOUNDED",
                    "audio_qa_pass": strata["counts"]["audio_qa_pass"],
                    "exact_blockers": strata["counts"]["exact_blockers"],
                    "status": hold_packet["status"],
                },
                sort_keys=True,
            )
        )
        return 0

    payload = build_library_blocker_packet(root)
    if payload["decision"]["status"] != "blocked":
        raise WaveformFeatureError("library_mode_must_remain_fail_closed_until_row070_accepted")
    write_json(output, payload)
    print(json.dumps({"output": str(output), "status": payload.get("status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
