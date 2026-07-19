#!/usr/bin/env python3
"""Fail-closed Wave64 Row071 waveform feature extraction authority slice.

Library extraction refuses to claim authority without an accepted Row070
canonical PCM record. Fixture mode may compute deterministic PCM-domain
features for known synthetic signals without promoting library completion.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/waveform_feature_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_waveform_feature_extraction.json"
)
ROW070_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-070_CANONICAL_AUDIO_DECODE_CURRENT_DELTA_20260719.json"
)
FEATURE_PIPELINE_REVISION = "wave64_row071_waveform_features_v0.1.0"
TRACKER_ID = "TRK-W64-071"
ITEM_ID = "ITEM-W64-071"
SCHEMA_VERSION = "1.0.0"

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
        "method_id": "pcm_mean_square_dbfs_v1",
        "unit": "dBFS",
        "window": "full_signal",
    },
    "true_peak": {
        "method_id": "pcm_sample_peak_dbfs_v1",
        "unit": "dBFS",
        "window": "full_signal",
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
        "window": "full_signal_rfft",
    },
    "spectral_bandwidth": {
        "method_id": "pcm_rfft_power_bandwidth_hz_v1",
        "unit": "Hz",
        "window": "full_signal_rfft",
    },
    "spectral_rolloff": {
        "method_id": "pcm_rfft_power_rolloff_85pct_hz_v1",
        "unit": "Hz",
        "window": "full_signal_rfft",
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


def db_from_power(power: float) -> float:
    safe = max(power, 1e-24)
    return 10.0 * math.log10(safe)


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


def _rfft_power(signal: list[float]) -> tuple[list[float], list[float]]:
    n = len(signal)
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

    spectrum = fft([complex(sample, 0.0) for sample in signal])
    half = n // 2
    power = [(spectrum[k].real ** 2 + spectrum[k].imag ** 2) / (n * n) for k in range(half + 1)]
    freqs = list(range(half + 1))
    return freqs, power


def extract_features_from_channels(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
) -> dict[str, Any]:
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
    noise_db = db_from_amplitude(noise)
    peak_db = db_from_amplitude(peak)
    dynamic_range = peak_db - noise_db

    freqs, power = _rfft_power(mono)
    total = sum(power)
    if total <= 0:
        centroid = 0.0
        bandwidth = 0.0
        rolloff = 0.0
    else:
        hz = [(bin_index * sample_rate_hz) / frame_count for bin_index in freqs]
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

    features = {
        "integrated_loudness": round_finite(db_from_power(mean_square)),
        "true_peak": round_finite(peak_db),
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
    return features


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
    features = extract_features_from_channels(
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


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admission = evaluate_row070_admission(root)
    blocker_codes = list(admission["blocker_codes"])
    if "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
        blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    if "BS1770_LOUDNESS_AUTHORITY_NOT_WIRED" not in blocker_codes:
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
        "status": "HOLD_ROW070_CANONICAL_DECODE_AND_FULL_LIBRARY_FEATURE_RUNTIME_ABSENT",
        "row070_admission": admission,
        "required_features": list(REQUIRED_FEATURES),
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": "Fixture records prove PCM-domain method identity only; they do not accept Row071 library completion.",
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row071_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row070 canonical PCM authority, wire BS.1770 loudness/true-peak library methods, "
                "reconcile every accepted decode record to feature PASS or an exact blocker, and replace "
                "this hold packet with full-library runtime evidence."
            ),
        },
    }
    return packet


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture"), default="library")
    parser.add_argument("--fixture", default="tone_1k")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve():
        # Allow tests to pass the same canonical root explicitly.
        if root != Path("C:/Comfy_UI_Main").resolve():
            raise WaveformFeatureError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise WaveformFeatureError("library_mode_must_remain_fail_closed_until_row070_accepted")
    write_json(output, payload)
    print(json.dumps({"output": str(output), "status": payload.get("status") or payload["decision"]["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
