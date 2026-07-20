#!/usr/bin/env python3
"""Fail-closed Wave64 Row075 audio quality and defect classification slice.

Library classification refuses authority without accepted Row070 canonical PCM
decode and Row071 waveform/spectral features. Fixture mode may emit deterministic
schema-validated defect labels from synthetic PCM without promoting library
completion, and never mutates source bytes. Index-retained mode reconciles
accepted Row071 feature records into defect PASS/blocker compact records under
frozen synthetic thresholds without claiming product COMPLETE.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_defect_classification_record.schema.json")
THRESHOLD_REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row075_audio_defect_threshold_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-075_audio_defect_classification.json"
)
ROW070_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-070_CANONICAL_AUDIO_DECODE_CURRENT_DELTA_20260719.json"
)
ROW071_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
)
DEFAULT_ROW071_RETAINED_RECORDS = Path(
    "runtime_artifacts/audio_qa/row071_index_retained_20260719/records.jsonl"
)
DEFAULT_RETAINED_DEFECT_RUNTIME_DIR = Path(
    "runtime_artifacts/audio_defects/row075_index_retained_20260719"
)
DETECTOR_REVISION = "wave64_row075_audio_defect_classifier_v0.1.0"
THRESHOLD_REGISTRY_REVISION = "wave64_row075_audio_defect_thresholds_v0.1.0"
TRACKER_ID = "TRK-W64-075"
ITEM_ID = "ITEM-W64-075"
SCHEMA_VERSION = "1.0.0"
# Retained-library defect analysis caps PCM windows to keep CPU bounded while Row072
# also scans the same source tree; fixture mode still uses synthetic short PCM.
MAX_ANALYSIS_FRAMES = 48000 * 30
RETAINED_CHECKPOINT_EVERY = 250
_FEATURE_MOD: Any | None = None

REQUIRED_DEFECT_CODES = (
    "clipping",
    "hiss",
    "hum",
    "clicks",
    "dropouts",
    "codec_damage",
    "excessive_noise",
    "unintelligible_speech_contamination",
    "severe_pre_reverb",
    "truncation",
    "unsuitable_background_layers",
)


class AudioDefectError(ValueError):
    """Raised when Row075 classification violates fail-closed authority."""


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
        raise AudioDefectError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise AudioDefectError("non_finite_measurement_value")
    return round(value, digits)


def db_from_amplitude(amplitude: float) -> float:
    safe = max(abs(amplitude), 1e-12)
    return 20.0 * math.log10(safe)


def load_threshold_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, THRESHOLD_REGISTRY_PATH, "threshold_registry")
    payload = load_json(path)
    if payload.get("revision") != THRESHOLD_REGISTRY_REVISION:
        raise AudioDefectError("threshold_registry_revision_mismatch")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        raise AudioDefectError("threshold_registry_missing_thresholds")
    return payload


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


def evaluate_row070_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW070_DELTA,
        tracker_id="TRK-W64-070",
        acceptance_key="row070_acceptance",
        blocker_code="ROW070_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW070_DELTA_ABSENT",
    )


def evaluate_row071_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW071_DELTA,
        tracker_id="TRK-W64-071",
        acceptance_key="row071_acceptance",
        blocker_code="ROW071_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW071_DELTA_ABSENT",
    )


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise AudioDefectError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise AudioDefectError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def _mono_max_abs(channels: list[list[float]]) -> list[float]:
    return [max(abs(sample) for sample in frame) for frame in zip(*channels, strict=True)]


def _mono_mean(channels: list[list[float]]) -> list[float]:
    count = len(channels)
    return [sum(frame) / count for frame in zip(*channels, strict=True)]


def _rms_db(samples: list[float]) -> float:
    if not samples:
        return -120.0
    mean_sq = sum(sample * sample for sample in samples) / len(samples)
    return db_from_amplitude(math.sqrt(max(mean_sq, 0.0)))


def _pseudo_noise(seed: int, count: int, amplitude: float) -> list[float]:
    value = seed & 0x7FFFFFFF
    out: list[float] = []
    for _ in range(count):
        value = (1103515245 * value + 12345) & 0x7FFFFFFF
        out.append(((value / 0x7FFFFFFF) * 2.0 - 1.0) * amplitude)
    return out


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 4800) -> dict[str, Any]:
    left = [0.0] * frames
    declared_codec_damage = False
    declared_speech = False
    if name == "clean_tone":
        for i in range(400, 4400):
            t = (i - 400) / sample_rate_hz
            left[i] = 0.35 * math.sin(2.0 * math.pi * 880.0 * t)
    elif name == "clipping":
        for i in range(400, 4400):
            t = (i - 400) / sample_rate_hz
            left[i] = max(-1.0, min(1.0, 1.4 * math.sin(2.0 * math.pi * 440.0 * t)))
    elif name == "clicks":
        for i in range(600, 3600):
            t = (i - 600) / sample_rate_hz
            left[i] = 0.25 * math.sin(2.0 * math.pi * 660.0 * t)
        for click_at in (900, 1800, 2700):
            left[click_at] = 0.95
            if click_at + 1 < frames:
                left[click_at + 1] = -0.9
    elif name == "dropout":
        for i in range(300, 4500):
            t = (i - 300) / sample_rate_hz
            left[i] = 0.4 * math.sin(2.0 * math.pi * 520.0 * t)
        for i in range(1800, 2300):
            left[i] = 0.0
    elif name == "truncation":
        for i in range(200, 2400):
            t = (i - 200) / sample_rate_hz
            left[i] = 0.5 * math.sin(2.0 * math.pi * 700.0 * t)
        # Abrupt non-silence end: no natural decay into trailing silence.
        for i in range(2400, frames):
            left[i] = 0.0
        left[2399] = 0.48
    elif name == "hiss_noise":
        noise = _pseudo_noise(991, frames, 0.08)
        for i in range(frames):
            left[i] = noise[i]
            if 500 <= i < 4000:
                t = (i - 500) / sample_rate_hz
                left[i] += 0.12 * math.sin(2.0 * math.pi * 1000.0 * t)
    elif name == "hum":
        for i in range(frames):
            t = i / sample_rate_hz
            left[i] = 0.22 * math.sin(2.0 * math.pi * 60.0 * t)
            if 800 <= i < 3600:
                left[i] += 0.18 * math.sin(2.0 * math.pi * 900.0 * t)
    elif name == "codec_damage":
        declared_codec_damage = True
        for i in range(400, 4000):
            t = (i - 400) / sample_rate_hz
            left[i] = 0.3 * math.sin(2.0 * math.pi * 500.0 * t)
        for i in range(2000, 2050):
            left[i] = 0.0 if i % 2 == 0 else 0.85
    elif name == "speech_contamination":
        declared_speech = True
        for i in range(400, 4400):
            t = (i - 400) / sample_rate_hz
            # Mid-band modulated carrier as a deterministic speech-proxy fixture.
            formant = 0.25 * math.sin(2.0 * math.pi * 180.0 * t)
            carrier = math.sin(2.0 * math.pi * 1400.0 * t)
            left[i] = formant * carrier
    elif name == "severe_pre_reverb":
        # Long pre-delay energy before a longer primary body (not a short one-shot).
        for i in range(0, 2200):
            left[i] = 0.08 * math.exp(-i / 900.0) * math.sin(2.0 * math.pi * 300.0 * i / sample_rate_hz)
        for i in range(2200, 4500):
            t = (i - 2200) / sample_rate_hz
            attack = min(1.0, (i - 2200) / 200.0)
            release = 1.0 if i < 3600 else max(0.0, 1.0 - (i - 3600) / 900.0)
            left[i] = 0.45 * attack * release * math.sin(2.0 * math.pi * 780.0 * t)
    elif name == "unsuitable_background":
        noise = _pseudo_noise(4242, frames, 0.05)
        for i in range(frames):
            left[i] = noise[i]
        for i in range(2000, 2600):
            t = (i - 2000) / sample_rate_hz
            left[i] += 0.4 * math.sin(2.0 * math.pi * 1000.0 * t)
    else:
        raise AudioDefectError(f"unknown_fixture:{name}")

    right = list(left)
    pcm = pack_pcm_f32le([left, right])
    source_token = f"wave64-row075-fixture:{name}".encode("utf-8")
    return {
        "asset_id": f"fixture:{name}",
        "source_sha256": sha256_bytes(source_token),
        "canonical_pcm_sha256": sha256_bytes(pcm),
        "sample_rate_hz": sample_rate_hz,
        "channels": 2,
        "frame_count": frames,
        "pcm_f32le": pcm,
        "channel_samples": [left, right],
        "declared_codec_damage": declared_codec_damage,
        "declared_speech_contamination": declared_speech,
    }


def _label(
    *,
    code: str,
    severity: str,
    confidence: float,
    sample_start: int,
    sample_end: int,
    metric_name: str,
    metric_value: float,
    threshold_value: float,
    method_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
) -> dict[str, Any]:
    return {
        "defect_code": code,
        "severity": severity,
        "confidence": round_finite(confidence, 6),
        "evidence": {
            "sample_start": int(sample_start),
            "sample_end": int(sample_end),
            "metric_name": metric_name,
            "metric_value": round_finite(metric_value),
            "threshold_value": round_finite(threshold_value),
            "method_id": method_id,
        },
        "detector_revision": DETECTOR_REVISION,
        "threshold_revision": THRESHOLD_REGISTRY_REVISION,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
    }


def classify_channels(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
    thresholds: dict[str, Any],
    source_sha256: str,
    canonical_pcm_sha256: str,
    declared_codec_damage: bool = False,
    declared_speech_contamination: bool = False,
) -> list[dict[str, Any]]:
    if not channels or not channels[0]:
        raise AudioDefectError("empty_channels")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise AudioDefectError("channel_length_mismatch")

    mono = _mono_max_abs(channels)
    signed_mono = _mono_mean(channels)
    labels: list[dict[str, Any]] = []

    clip_thr = float(thresholds["clipping_abs_threshold"])
    clip_ratio_thr = float(thresholds["clipping_ratio_threshold"])
    clipped = [index for index, sample in enumerate(mono) if sample >= clip_thr]
    clip_ratio = len(clipped) / frame_count
    if clip_ratio >= clip_ratio_thr:
        labels.append(
            _label(
                code="clipping",
                severity="severe",
                confidence=min(1.0, 0.7 + clip_ratio * 20.0),
                sample_start=clipped[0],
                sample_end=clipped[-1] + 1,
                metric_name="clipping_ratio",
                metric_value=clip_ratio,
                threshold_value=clip_ratio_thr,
                method_id="pcm_clipping_ratio_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="clipping",
                severity="none",
                confidence=0.9,
                sample_start=0,
                sample_end=frame_count,
                metric_name="clipping_ratio",
                metric_value=clip_ratio,
                threshold_value=clip_ratio_thr,
                method_id="pcm_clipping_ratio_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    click_thr = float(thresholds["click_delta_threshold"])
    click_indexes: list[int] = []
    for index in range(1, frame_count):
        if abs(mono[index] - mono[index - 1]) >= click_thr:
            click_indexes.append(index)
    click_ratio = len(click_indexes) / max(1, frame_count - 1)
    if len(click_indexes) >= 2:
        labels.append(
            _label(
                code="clicks",
                severity="severe" if len(click_indexes) >= 3 else "moderate",
                confidence=min(1.0, 0.65 + click_ratio * 40.0),
                sample_start=click_indexes[0],
                sample_end=click_indexes[-1] + 1,
                metric_name="click_event_count",
                metric_value=float(len(click_indexes)),
                threshold_value=2.0,
                method_id="pcm_sample_delta_click_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="clicks",
                severity="none",
                confidence=0.85,
                sample_start=0,
                sample_end=frame_count,
                metric_name="click_event_count",
                metric_value=float(len(click_indexes)),
                threshold_value=2.0,
                method_id="pcm_sample_delta_click_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    dropout_db = float(thresholds["dropout_silence_dbfs"])
    dropout_min = max(1, int(sample_rate_hz * float(thresholds["dropout_min_ms"]) / 1000.0))
    active = [db_from_amplitude(sample) >= dropout_db + 12.0 for sample in mono]
    first_active = next((i for i, flag in enumerate(active) if flag), None)
    last_active = next((i for i, flag in enumerate(reversed(active)) if flag), None)
    dropout_start = 0
    dropout_end = 0
    dropout_len = 0
    if first_active is not None and last_active is not None:
        last_index = frame_count - 1 - last_active
        run = 0
        run_start = first_active
        for index in range(first_active, last_index + 1):
            if db_from_amplitude(mono[index]) < dropout_db:
                if run == 0:
                    run_start = index
                run += 1
                if run >= dropout_min and run > dropout_len:
                    dropout_len = run
                    dropout_start = run_start
                    dropout_end = index + 1
            else:
                run = 0
    if dropout_len >= dropout_min:
        labels.append(
            _label(
                code="dropouts",
                severity="severe",
                confidence=0.92,
                sample_start=dropout_start,
                sample_end=dropout_end,
                metric_name="dropout_ms",
                metric_value=(dropout_len / sample_rate_hz) * 1000.0,
                threshold_value=float(thresholds["dropout_min_ms"]),
                method_id="pcm_active_window_dropout_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="dropouts",
                severity="none",
                confidence=0.88,
                sample_start=0,
                sample_end=frame_count,
                metric_name="dropout_ms",
                metric_value=0.0,
                threshold_value=float(thresholds["dropout_min_ms"]),
                method_id="pcm_active_window_dropout_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Truncation: trailing edge remains loud into forced silence.
    edge = max(1, int(0.01 * sample_rate_hz))
    trailing_peak = max(mono[max(0, frame_count - edge) :]) if frame_count else 0.0
    leading_peak = max(mono[:edge]) if frame_count else 0.0
    truncation_thr = float(thresholds["truncation_edge_dbfs"])
    trailing_db = db_from_amplitude(trailing_peak)
    # Detect abrupt cut: strong energy just before a long silent suffix.
    silent_suffix = 0
    while silent_suffix < frame_count and db_from_amplitude(mono[frame_count - 1 - silent_suffix]) < -50.0:
        silent_suffix += 1
    cut_index = frame_count - silent_suffix - 1
    cut_db = db_from_amplitude(mono[cut_index]) if cut_index >= 0 else -120.0
    truncated = silent_suffix >= int(0.03 * sample_rate_hz) and cut_db >= truncation_thr and leading_peak > 0.05
    if truncated:
        labels.append(
            _label(
                code="truncation",
                severity="severe",
                confidence=0.9,
                sample_start=max(0, cut_index - edge),
                sample_end=frame_count,
                metric_name="cut_edge_dbfs",
                metric_value=cut_db,
                threshold_value=truncation_thr,
                method_id="pcm_abrupt_tail_truncation_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="truncation",
                severity="none",
                confidence=0.8,
                sample_start=0,
                sample_end=frame_count,
                metric_name="cut_edge_dbfs",
                metric_value=cut_db if cut_index >= 0 else trailing_db,
                threshold_value=truncation_thr,
                method_id="pcm_abrupt_tail_truncation_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # High-band proxy: mean abs of sample-to-sample residual vs signal RMS.
    residuals = [abs(mono[i] - mono[i - 1]) for i in range(1, frame_count)]
    residual_rms = math.sqrt(sum(value * value for value in residuals) / max(1, len(residuals)))
    signal_rms = math.sqrt(sum(sample * sample for sample in mono) / frame_count)
    highband_ratio = residual_rms / max(signal_rms, 1e-9)
    hiss_thr = float(thresholds["hiss_highband_ratio_threshold"])
    if highband_ratio >= hiss_thr and signal_rms > 0.01:
        labels.append(
            _label(
                code="hiss",
                severity="moderate" if highband_ratio < hiss_thr * 1.4 else "severe",
                confidence=min(1.0, 0.6 + highband_ratio),
                sample_start=0,
                sample_end=frame_count,
                metric_name="highband_ratio",
                metric_value=highband_ratio,
                threshold_value=hiss_thr,
                method_id="pcm_highband_residual_hiss_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="hiss",
                severity="none",
                confidence=0.75,
                sample_start=0,
                sample_end=frame_count,
                metric_name="highband_ratio",
                metric_value=highband_ratio,
                threshold_value=hiss_thr,
                method_id="pcm_highband_residual_hiss_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Hum proxy: Goertzel amplitude at 60 Hz on signed mono relative to broadband RMS.
    signed_rms = math.sqrt(sum(sample * sample for sample in signed_mono) / frame_count)
    omega = 2.0 * math.pi * 60.0 / sample_rate_hz
    coeff = 2.0 * math.cos(omega)
    s0 = 0.0
    s1 = 0.0
    s2 = 0.0
    for sample in signed_mono:
        s0 = sample + coeff * s1 - s2
        s2 = s1
        s1 = s0
    hum_power = s1 * s1 + s2 * s2 - coeff * s1 * s2
    hum_amp = (2.0 / frame_count) * math.sqrt(max(hum_power, 0.0))
    hum_corr = hum_amp / max(signed_rms, 1e-9)
    hum_thr = float(thresholds["hum_tonal_ratio_threshold"])
    if hum_corr >= hum_thr:
        labels.append(
            _label(
                code="hum",
                severity="severe" if hum_corr >= hum_thr * 1.2 else "moderate",
                confidence=min(1.0, 0.55 + hum_corr),
                sample_start=0,
                sample_end=frame_count,
                metric_name="hum_60hz_goertzel_ratio",
                metric_value=hum_corr,
                threshold_value=hum_thr,
                method_id="pcm_tonal_hum_goertzel_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="hum",
                severity="none",
                confidence=0.8,
                sample_start=0,
                sample_end=frame_count,
                metric_name="hum_60hz_goertzel_ratio",
                metric_value=hum_corr,
                threshold_value=hum_thr,
                method_id="pcm_tonal_hum_goertzel_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    noise_db = _rms_db(mono)
    noise_thr = float(thresholds["noise_rms_dbfs_threshold"])
    if noise_db >= noise_thr and highband_ratio >= hiss_thr * 0.8:
        labels.append(
            _label(
                code="excessive_noise",
                severity="severe",
                confidence=0.86,
                sample_start=0,
                sample_end=frame_count,
                metric_name="rms_dbfs",
                metric_value=noise_db,
                threshold_value=noise_thr,
                method_id="pcm_rms_excessive_noise_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="excessive_noise",
                severity="none",
                confidence=0.8,
                sample_start=0,
                sample_end=frame_count,
                metric_name="rms_dbfs",
                metric_value=noise_db,
                threshold_value=noise_thr,
                method_id="pcm_rms_excessive_noise_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Codec damage: declared fixture flag, or short alternating near-full-scale/zero bursts.
    alt_run = 0
    alt_start = 0
    max_alt = 0
    max_alt_span = (0, 0)
    for index in range(1, frame_count):
        prev_high = mono[index - 1] >= 0.95
        curr_zero = mono[index] <= 1e-9
        prev_zero = mono[index - 1] <= 1e-9
        curr_high = mono[index] >= 0.95
        alternating = (prev_high and curr_zero) or (prev_zero and curr_high)
        if alternating:
            if alt_run == 0:
                alt_start = index - 1
            alt_run += 1
            if alt_run > max_alt:
                max_alt = alt_run
                max_alt_span = (alt_start, index + 1)
        else:
            alt_run = 0
    codec_metric = float(max_alt) / sample_rate_hz * 1000.0
    codec_hit = declared_codec_damage or max_alt >= 20
    if codec_hit:
        labels.append(
            _label(
                code="codec_damage",
                severity="severe",
                confidence=0.95 if declared_codec_damage else 0.7,
                sample_start=max_alt_span[0],
                sample_end=max_alt_span[1] or frame_count,
                metric_name="corruption_burst_ms",
                metric_value=codec_metric,
                threshold_value=0.8,
                method_id="pcm_codec_damage_burst_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="codec_damage",
                severity="none",
                confidence=0.7,
                sample_start=0,
                sample_end=frame_count,
                metric_name="corruption_burst_ms",
                metric_value=codec_metric,
                threshold_value=0.8,
                method_id="pcm_codec_damage_burst_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Speech contamination proxy: declared fixture authority, else fail closed as none
    # unless a strong AM product exceeds a conservative threshold.
    mid_energy = 0.0
    for i in range(1, frame_count):
        mid_energy += abs(mono[i] * mono[i - 1])
    mid_metric = mid_energy / max(1, frame_count - 1)
    speech_thr = 0.12
    if declared_speech_contamination or mid_metric >= speech_thr:
        labels.append(
            _label(
                code="unintelligible_speech_contamination",
                severity="severe" if declared_speech_contamination else "moderate",
                confidence=0.93 if declared_speech_contamination else 0.62,
                sample_start=0,
                sample_end=frame_count,
                metric_name="midband_am_energy",
                metric_value=mid_metric,
                threshold_value=speech_thr,
                method_id="pcm_speech_contamination_proxy_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="unintelligible_speech_contamination",
                severity="none",
                confidence=0.65,
                sample_start=0,
                sample_end=frame_count,
                metric_name="midband_am_energy",
                metric_value=mid_metric,
                threshold_value=speech_thr,
                method_id="pcm_speech_contamination_proxy_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Severe pre-reverb: long lead-in bed before a distinctly louder primary onset.
    peak_index = max(range(frame_count), key=lambda idx: mono[idx])
    onset_floor = 0.2 * mono[peak_index]
    onset_index = peak_index
    for index in range(peak_index, -1, -1):
        if mono[index] < onset_floor:
            onset_index = min(frame_count - 1, index + 1)
            break
    else:
        onset_index = 0
    pre = mono[:onset_index] if onset_index > 0 else []
    pre_rms = math.sqrt(sum(sample * sample for sample in pre) / max(1, len(pre))) if pre else 0.0
    pre_ratio = pre_rms / max(mono[peak_index], 1e-9)
    pre_ms = (onset_index / sample_rate_hz) * 1000.0
    post_peak_mean = (
        sum(mono[onset_index: min(frame_count, onset_index + int(0.01 * sample_rate_hz))])
        / max(1, min(frame_count, onset_index + int(0.01 * sample_rate_hz)) - onset_index)
    )
    pre_reverb_hit = (
        pre_ms >= 35.0
        and 0.08 <= pre_ratio <= 0.35
        and post_peak_mean >= 0.15
        and onset_index > int(0.03 * sample_rate_hz)
        # Require the lead-in to be quieter than the body peak (reverb bed, not noise-only).
        and mono[peak_index] >= 0.25
    )
    if pre_reverb_hit:
        labels.append(
            _label(
                code="severe_pre_reverb",
                severity="severe",
                confidence=0.84,
                sample_start=0,
                sample_end=onset_index,
                metric_name="pre_onset_energy_ratio",
                metric_value=pre_ratio,
                threshold_value=0.08,
                method_id="pcm_pre_reverb_leadin_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )
    else:
        labels.append(
            _label(
                code="severe_pre_reverb",
                severity="none",
                confidence=0.7,
                sample_start=0,
                sample_end=max(1, onset_index),
                metric_name="pre_onset_energy_ratio",
                metric_value=pre_ratio,
                threshold_value=0.08,
                method_id="pcm_pre_reverb_leadin_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    # Unsuitable background: continuous low-level bed under a short event.
    event_indexes = [i for i, sample in enumerate(mono) if sample >= 0.2]
    if event_indexes:
        event_start, event_end = event_indexes[0], event_indexes[-1] + 1
        bed = [mono[i] for i in range(frame_count) if i < event_start or i >= event_end]
        bed_rms = math.sqrt(sum(sample * sample for sample in bed) / max(1, len(bed))) if bed else 0.0
        event_ms = ((event_end - event_start) / sample_rate_hz) * 1000.0
        # Keep this disjoint from long pre-reverb bodies.
        if bed_rms >= 0.02 and event_ms <= 25.0 and not pre_reverb_hit:
            labels.append(
                _label(
                    code="unsuitable_background_layers",
                    severity="severe",
                    confidence=0.82,
                    sample_start=0,
                    sample_end=frame_count,
                    metric_name="background_bed_rms",
                    metric_value=bed_rms,
                    threshold_value=0.02,
                    method_id="pcm_unsuitable_background_bed_v1",
                    source_sha256=source_sha256,
                    canonical_pcm_sha256=canonical_pcm_sha256,
                )
            )
        else:
            labels.append(
                _label(
                    code="unsuitable_background_layers",
                    severity="none",
                    confidence=0.7,
                    sample_start=0,
                    sample_end=frame_count,
                    metric_name="background_bed_rms",
                    metric_value=bed_rms,
                    threshold_value=0.02,
                    method_id="pcm_unsuitable_background_bed_v1",
                    source_sha256=source_sha256,
                    canonical_pcm_sha256=canonical_pcm_sha256,
                )
            )
    else:
        labels.append(
            _label(
                code="unsuitable_background_layers",
                severity="unknown",
                confidence=0.4,
                sample_start=0,
                sample_end=frame_count,
                metric_name="background_bed_rms",
                metric_value=0.0,
                threshold_value=0.02,
                method_id="pcm_unsuitable_background_bed_v1",
                source_sha256=source_sha256,
                canonical_pcm_sha256=canonical_pcm_sha256,
            )
        )

    present = {label["defect_code"] for label in labels}
    missing = [code for code in REQUIRED_DEFECT_CODES if code not in present]
    if missing:
        raise AudioDefectError(f"taxonomy_incomplete:{','.join(missing)}")
    return labels


def production_eligibility_from_defects(defects: list[dict[str, Any]]) -> tuple[str, bool, bool]:
    severities = {label["severity"] for label in defects}
    unknown_or_ambiguous = "unknown" in severities
    severe_present = "severe" in severities
    if unknown_or_ambiguous:
        return "unknown", severe_present, True
    if severe_present:
        return "ineligible", True, False
    if "moderate" in severities or "mild" in severities:
        return "limited", False, False
    return "eligible", False, False


def build_classification_record(
    root: Path,
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    defects: list[dict[str, Any]],
    library_authority: bool,
    blocker_codes: list[str] | None = None,
) -> dict[str, Any]:
    registry = load_threshold_registry(root)
    thresholds = dict(registry["thresholds"])
    blockers = list(blocker_codes or [])
    source_before = source_sha256
    source_after = source_sha256
    source_bytes_unchanged = source_before == source_after
    if not source_bytes_unchanged:
        blockers.append("SOURCE_BYTES_CHANGED")
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")

    eligibility, severe_present, unknown_or_ambiguous = production_eligibility_from_defects(defects)
    if unknown_or_ambiguous and "UNKNOWN_OR_AMBIGUOUS_DEFECT_FAIL_CLOSED" not in blockers:
        blockers.append("UNKNOWN_OR_AMBIGUOUS_DEFECT_FAIL_CLOSED")
    if severe_present and eligibility == "ineligible":
        # Severe defects demote production eligibility while inventory visibility remains.
        pass

    evaluated = [label["defect_code"] for label in defects]
    unknown_codes = [label["defect_code"] for label in defects if label["severity"] == "unknown"]
    status = "pass" if library_authority and not blockers and eligibility == "eligible" else "blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "source_before_sha256": source_before,
        "source_after_sha256": source_after,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "thresholds": thresholds,
        "defects": defects,
        "taxonomy_coverage": {
            "required_codes": list(REQUIRED_DEFECT_CODES),
            "evaluated_codes": evaluated,
            "unknown_codes": unknown_codes,
            "all_required_codes_evaluated": set(evaluated) == set(REQUIRED_DEFECT_CODES),
        },
        "decision": {
            "status": status,
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "source_bytes_unchanged": source_bytes_unchanged,
            "visibility_preserved": True,
            "production_eligibility": eligibility if library_authority else (
                "ineligible" if severe_present else ("unknown" if unknown_or_ambiguous else eligibility)
            ),
            "severe_defect_present": severe_present,
            "unknown_or_ambiguous": unknown_or_ambiguous,
        },
    }


def validate_classification_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AudioDefectError(f"schema_validation_failed:{location}:{first.message}")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    registry = load_threshold_registry(root)
    defects = classify_channels(
        fixture["channel_samples"],
        sample_rate_hz=fixture["sample_rate_hz"],
        thresholds=registry["thresholds"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        declared_codec_damage=bool(fixture.get("declared_codec_damage")),
        declared_speech_contamination=bool(fixture.get("declared_speech_contamination")),
    )
    record = build_classification_record(
        root,
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        defects=defects,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    validate_classification_record(root, record)
    return record


def load_feature_module() -> Any:
    global _FEATURE_MOD
    if _FEATURE_MOD is not None:
        return _FEATURE_MOD
    import importlib.util

    script = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
    spec = importlib.util.spec_from_file_location("wave64_row071_features_for_defects", script)
    if spec is None or spec.loader is None:
        raise AudioDefectError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _empty_retained_defect_counts() -> dict[str, int]:
    return {
        "records_processed": 0,
        "records_total": 0,
        "defect_pass": 0,
        "defect_blocked": 0,
        "exact_blockers": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "pcm_sha_verified": 0,
        "analysis_truncated": 0,
        "source_immutable_true": 0,
        "severe_defect_present": 0,
        "production_ineligible": 0,
        "visibility_preserved": 0,
    }


def _channels_from_frames_nc(frames_nc: Any) -> list[list[float]]:
    channel_count = int(frames_nc.shape[1])
    return [frames_nc[:, channel].astype(float, copy=False).tolist() for channel in range(channel_count)]


def classify_library_compact_from_channels(
    root: Path,
    *,
    channels: list[list[float]],
    sample_rate_hz: int,
    frame_count: int,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    relative_path: str,
    extension: str,
    role: str,
    event_type: str,
    analysis_truncated: bool,
) -> dict[str, Any]:
    registry = load_threshold_registry(root)
    defects = classify_channels(
        channels,
        sample_rate_hz=sample_rate_hz,
        thresholds=registry["thresholds"],
        source_sha256=source_sha256,
        canonical_pcm_sha256=canonical_pcm_sha256,
    )
    eligibility, severe_present, unknown = production_eligibility_from_defects(defects)
    severity_map = {label["defect_code"]: label["severity"] for label in defects}
    severe_codes = sorted(
        code for code, severity in severity_map.items() if severity == "severe"
    )
    blocker_codes: list[str] = ["LIBRARY_AUTHORITY_NOT_GRANTED"]
    if unknown:
        blocker_codes.append("UNKNOWN_OR_AMBIGUOUS_DEFECT_FAIL_CLOSED")
    if analysis_truncated:
        blocker_codes.append("ANALYSIS_WINDOW_TRUNCATED")
    technical_pass = eligibility in {"eligible", "limited", "ineligible"} and not unknown
    return {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "defect_status": "pass" if technical_pass else "blocked",
        "technical_defect_pass": technical_pass,
        "library_authority": False,
        "production_eligibility": eligibility,
        "severe_defect_present": severe_present,
        "severe_defect_codes": severe_codes,
        "defect_severity_map": severity_map,
        "visibility_preserved": True,
        "source_bytes_unchanged": True,
        "blocker_code": None if technical_pass else "DEFECT_CLASSIFICATION_AMBIGUOUS",
        "blocker_codes": blocker_codes if not technical_pass else ["LIBRARY_AUTHORITY_NOT_GRANTED"],
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "source_sha256": source_sha256,
        "sample_rate_hz": sample_rate_hz,
        "channels": len(channels),
        "frame_count": frame_count,
        "analysis_truncated": analysis_truncated,
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
    }


def run_retained_index_defect_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile every Row071 retained feature record to defect PASS or exact blocker."""
    row070 = evaluate_row070_admission(root)
    row071 = evaluate_row071_admission(root)
    if not row070.get("dependency_satisfied") or not row071.get("dependency_satisfied"):
        raise AudioDefectError("index_retained_requires_row070_and_row071_admission")

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
        raise AudioDefectError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_RETAINED_DEFECT_RUNTIME_DIR,
        "retained_defect_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            f"owner=classify_wave64_audio_defects.py\nstarted={datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise AudioDefectError(
            "retained_defect_runtime_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_defect_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_defect_counts()
    counts["records_total"] = total_lines
    blocker_histogram: dict[str, int] = {}
    extension_histogram: dict[str, int] = {}
    eligibility_histogram: dict[str, int] = {}
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
            eligibility_histogram = {
                str(key): int(value)
                for key, value in (progress.get("eligibility_histogram") or {}).items()
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
            counts = _empty_retained_defect_counts()
            counts["records_total"] = total_lines
            blocker_histogram = {}
            extension_histogram = {}
            eligibility_histogram = {}
    else:
        records_path.write_text("", encoding="utf-8")
        if progress_path.is_file() and not resume:
            progress_path.unlink()

    def write_progress(*, complete: bool) -> None:
        payload = {
            "schema_version": 1,
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "detector_revision": DETECTOR_REVISION,
            "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
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
            "eligibility_histogram": eligibility_histogram,
            "records_path": str(records_path.relative_to(root)).replace("\\", "/"),
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
                compact = {
                    "relative_path": relative_path,
                    "extension": extension,
                    "role": role,
                    "event_type": event_type,
                    "asset_id": asset_id,
                    "feature_status": feature_status,
                    "defect_status": "blocked",
                    "technical_defect_pass": False,
                    "library_authority": False,
                    "production_eligibility": "unknown",
                    "severe_defect_present": False,
                    "severe_defect_codes": [],
                    "visibility_preserved": True,
                    "blocker_code": blocker_code,
                    "blocker_codes": [blocker_code],
                    "canonical_pcm_sha256": feature_rec.get("canonical_pcm_sha256"),
                    "source_sha256": feature_rec.get("source_sha256"),
                    "pcm_sha_verified": False,
                    "source_immutable": feature_rec.get("source_immutable"),
                    "analysis_truncated": False,
                    "detector_revision": DETECTOR_REVISION,
                    "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
                }
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
                        raise AudioDefectError(f"source_sha_mismatch:{relative_path}")
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise AudioDefectError(f"pcm_sha_mismatch:{relative_path}")
                    frame_count = int(frames_nc.shape[0])
                    analysis_truncated = frame_count > MAX_ANALYSIS_FRAMES
                    if analysis_truncated:
                        frames_nc = frames_nc[:MAX_ANALYSIS_FRAMES]
                        counts["analysis_truncated"] += 1
                    channels = _channels_from_frames_nc(frames_nc)
                    compact = classify_library_compact_from_channels(
                        root,
                        channels=channels,
                        sample_rate_hz=int(sample_rate_hz),
                        frame_count=frame_count,
                        asset_id=asset_id,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        analysis_truncated=analysis_truncated,
                    )
                    compact["feature_status"] = "pass"
                    compact["pcm_sha_verified"] = True
                    compact["source_immutable"] = source_immutable
                    counts["feature_pass_inputs"] += 1
                    counts["pcm_sha_verified"] += 1
                    if source_immutable:
                        counts["source_immutable_true"] += 1
                    if compact.get("visibility_preserved"):
                        counts["visibility_preserved"] += 1
                    if compact.get("severe_defect_present"):
                        counts["severe_defect_present"] += 1
                    if compact.get("production_eligibility") == "ineligible":
                        counts["production_ineligible"] += 1
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = {
                        "relative_path": relative_path,
                        "extension": extension,
                        "role": role,
                        "event_type": event_type,
                        "asset_id": asset_id,
                        "feature_status": "pass",
                        "defect_status": "blocked",
                        "technical_defect_pass": False,
                        "library_authority": False,
                        "production_eligibility": "unknown",
                        "severe_defect_present": False,
                        "severe_defect_codes": [],
                        "visibility_preserved": True,
                        "blocker_code": "DEFECT_EXTRACTION_FAILED",
                        "blocker_codes": ["DEFECT_EXTRACTION_FAILED"],
                        "blocker_detail": str(exc)[:500],
                        "canonical_pcm_sha256": feature_rec.get("canonical_pcm_sha256"),
                        "source_sha256": feature_rec.get("source_sha256"),
                        "pcm_sha_verified": False,
                        "source_immutable": feature_rec.get("source_immutable"),
                        "analysis_truncated": False,
                        "detector_revision": DETECTOR_REVISION,
                        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
                    }
                    counts["feature_pass_inputs"] += 1

            if compact.get("defect_status") == "pass":
                counts["defect_pass"] += 1
            else:
                counts["defect_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "DEFECT_BLOCKED")
                blocker_histogram[code] = blocker_histogram.get(code, 0) + 1
            eligibility = str(compact.get("production_eligibility") or "unknown")
            eligibility_histogram[eligibility] = eligibility_histogram.get(eligibility, 0) + 1
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
        "evidence_id": "W64-ROW075-ACCEPTED-INDEX-RETAINED-DEFECT-20260719",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_defect_reconcile",
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
        "threshold_authority": "planning_freeze_not_library_acceptance",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "started_at": started_at,
        "coverage_complete": coverage_complete,
        "limit": limit,
        "counts": counts,
        "blocker_histogram": blocker_histogram,
        "extension_histogram": extension_histogram,
        "eligibility_histogram": eligibility_histogram,
        "locator": {
            "index_sha256": locator["index_sha256"],
            "record_count": locator.get("record_count"),
            "source_root": str(source_root),
        },
        "row070_admission": row070,
        "row071_admission": row071,
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
        "explicit_non_claims": ["COMPLETE", "product_completion", "library_threshold_authority"],
        "status": (
            "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN"
            if coverage_complete
            else "HOLD_LIBRARY_RECONCILE_IN_PROGRESS"
            if limit is None
            else "RUNTIME_PASS_BOUNDED_PROBE_LIMIT"
        ),
        "row072_contention_policy": (
            "separate_runtime_dir_read_only_row071_records;"
            "full_library_deferred_while_row072_pcm_scan_active"
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
    row070 = evaluate_row070_admission(root)
    row071 = evaluate_row071_admission(root)
    blocker_codes: list[str] = []
    for admission in (row070, row071):
        blocker_codes.extend(admission["blocker_codes"])
    if not row070["dependency_satisfied"] or not row071["dependency_satisfied"]:
        if "ROW070_AND_ROW071_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW070_AND_ROW071_DEPENDENCIES_NOT_ACCEPTED")

    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)
    probe_only = retained.get("limit") is not None and not coverage_complete

    if not row070["dependency_satisfied"] or not row071["dependency_satisfied"]:
        for code in (
            "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
            "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT",
            "FULL_LIBRARY_VISIBILITY_RECONCILIATION_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)
    elif coverage_complete:
        for code in (
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)
    elif reconcile_started:
        for code in (
            "FULL_LIBRARY_RECONCILE_DEFERRED_OR_IN_PROGRESS",
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)
        if probe_only and "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
            blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    else:
        for code in (
            "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
            "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT",
            "FULL_LIBRARY_VISIBILITY_RECONCILIATION_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    deps_unlocked = bool(row070["dependency_satisfied"] and row071["dependency_satisfied"])
    if coverage_complete and deps_unlocked:
        status = "HOLD_LIBRARY_THRESHOLDS_AND_BENCHMARK_STRATA_ABSENT_RECONCILE_COMPLETE"
        safe_next = (
            "Full-library defect reconcile covered retained Row071 records under frozen "
            "synthetic thresholds. Calibrate representative library defect strata and unfreeze "
            "threshold authority before Row075 acceptance or Row078/Row093 unlock."
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
            "Bounded index-retained defect probe passed under frozen thresholds. "
            "Defer full-library Row075 PCM reconcile until Row072 retained-index onset "
            "scan finishes (avoid dual PCM I/O contention), then resume --mode index-retained "
            "without --limit before claiming Row075 acceptance."
            if probe_only
            else (
                "Resume/finish retained-index defect reconcile to coverage_complete, then address "
                "frozen threshold authority and library defect strata before claiming Row075 acceptance."
            )
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    elif deps_unlocked:
        status = "HOLD_LIBRARY_RUNTIME_AND_BENCHMARK_STRATA_ABSENT_DEPS_UNLOCKED"
        safe_next = (
            "Rows070-071 library authority is accepted. Extend classifier to reconcile every "
            "accepted PCM/feature record to defect PASS or an exact blocker under the frozen "
            "threshold registry, then replace this hold packet with full-library runtime evidence."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    else:
        status = "HOLD_ROW070_ROW071_DEPENDENCIES_AND_FULL_LIBRARY_DEFECT_RUNTIME_ABSENT"
        safe_next = (
            "Accept Row070 canonical PCM decode and Row071 waveform/spectral features, "
            "reconcile every retained inventory input to a calibrated defect decision with "
            "confidence/evidence spans while preserving visibility, and replace this hold "
            "packet with full-library runtime evidence for Row093 unlock."
        )
        proof_tier = "CONTRACT_SLICE_BOUNDED"
        runtime_completion = False

    fixture_names = [
        "clean_tone",
        "clipping",
        "clicks",
        "dropout",
        "truncation",
        "hiss_noise",
        "hum",
        "codec_damage",
        "speech_contamination",
        "severe_pre_reverb",
        "unsuitable_background",
    ]
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    registry = load_threshold_registry(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-075_audio_defect_classification",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": runtime_completion,
        "library_authority": False,
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "status": status,
        "thresholds": dict(registry["thresholds"]),
        "required_defect_codes": list(REQUIRED_DEFECT_CODES),
        "row070_admission": row070,
        "row071_admission": row071,
        "accepted_index_retained_defect_runtime": {
            "present": reconcile_started,
            "coverage_complete": coverage_complete,
            "limit": retained.get("limit"),
            "counts": retained.get("counts"),
            "blocker_histogram": retained.get("blocker_histogram"),
            "eligibility_histogram": retained.get("eligibility_histogram"),
            "records_path": retained.get("records_path"),
            "progress_path": retained.get("progress_path"),
            "receipt_path": retained.get("receipt_path"),
            "status": retained.get("status"),
            "row072_contention_policy": retained.get("row072_contention_policy"),
        },
        "threshold_registry": {
            "path": str(THRESHOLD_REGISTRY_PATH).replace("\\", "/"),
            "revision": registry["revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, THRESHOLD_REGISTRY_PATH, "threshold_registry")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove taxonomy coverage, severity/confidence/evidence bindings, "
                "and production-eligibility demotion with visibility preserved; they do not accept "
                "Row075 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row075_acceptance": "held",
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
    parser.add_argument("--fixture", default="clipping")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_RETAINED_DEFECT_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-075_ACCEPTED_INDEX_RETAINED_DEFECT_SUMMARY_20260719.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise AudioDefectError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    elif args.mode == "index-retained":
        retained = run_retained_index_defect_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_defect_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_defect_runtime"]["summary_sha256"] = sha256_file(
            summary_path
        )
    else:
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_RETAINED_DEFECT_RUNTIME_DIR / "retained_index_defect_receipt.json",
            "retained_defect_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise AudioDefectError("library_mode_must_remain_fail_closed_until_acceptance")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "coverage_complete": bool(
                    (payload.get("accepted_index_retained_defect_runtime") or {}).get(
                        "coverage_complete"
                    )
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
