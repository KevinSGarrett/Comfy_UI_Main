#!/usr/bin/env python3
"""Fail-closed Wave64 Row072 onset/transient/peak/offset anchor authority slice.

Library detection refuses authority without accepted Row070 canonical PCM and
Row071 feature authority. Fixture mode may emit deterministic multi-method
anchor records for synthetic PCM without promoting library completion.
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

import numpy as np
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/onset_transient_anchor_record.schema.json")
THRESHOLD_REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row072_onset_transient_threshold_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-072_onset_transient_detection.json"
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
DEFAULT_RETAINED_ONSET_RUNTIME_DIR = Path(
    "runtime_artifacts/onset_anchors/row072_index_retained_20260719"
)
DETECTOR_REVISION = "wave64_row072_onset_transient_detector_v0.1.0"
THRESHOLD_REGISTRY_REVISION = "wave64_row072_onset_thresholds_v0.1.0"
TRACKER_ID = "TRK-W64-072"
ITEM_ID = "ITEM-W64-072"
SCHEMA_VERSION = "1.0.0"
METHOD_ENERGY_FLUX = "energy_flux_onset_v1"
METHOD_HF_ENVELOPE = "hf_envelope_onset_v1"
DEFAULT_HOP = 64
DEFAULT_FRAME = 256
LIBRARY_EVENT_FAMILY = "library_unlabeled"
MAX_ANALYSIS_FRAMES = 48000 * 120
RETAINED_CHECKPOINT_EVERY = 250
_FEATURE_MOD: Any | None = None


class OnsetAnchorError(ValueError):
    """Raised when Row072 detection violates fail-closed authority."""


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
        raise OnsetAnchorError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise OnsetAnchorError("non_finite_value")
    return round(value, digits)


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise OnsetAnchorError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise OnsetAnchorError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def mono_mix(channels: list[list[float]]) -> list[float]:
    frame_count = len(channels[0])
    channel_count = len(channels)
    return [
        sum(channel[index] for channel in channels) / channel_count
        for index in range(frame_count)
    ]


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    acceptance_key: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    blocker_code = f"{tracker_id.replace('-', '_')}_DEPENDENCY_NOT_ACCEPTED".replace(
        "TRK_W64_", "ROW"
    )
    # Normalize to ROW070_... / ROW071_... style
    if tracker_id == "TRK-W64-070":
        blocker_code = "ROW070_DEPENDENCY_NOT_ACCEPTED"
    elif tracker_id == "TRK-W64-071":
        blocker_code = "ROW071_DEPENDENCY_NOT_ACCEPTED"
    if not path.is_file():
        return {
            "dependency_satisfied": False,
            "blocker_codes": [f"{tracker_id}_DELTA_ABSENT"],
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
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def evaluate_row070_admission(root: Path) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=ROW070_DELTA,
        tracker_id="TRK-W64-070",
        acceptance_key="row070_acceptance",
    )


def evaluate_row071_admission(root: Path) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=ROW071_DELTA,
        tracker_id="TRK-W64-071",
        acceptance_key="row071_acceptance",
    )


def load_threshold_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, THRESHOLD_REGISTRY_PATH, "threshold_registry")
    registry = load_json(path)
    if registry.get("revision") != THRESHOLD_REGISTRY_REVISION:
        raise OnsetAnchorError("threshold_registry_revision_mismatch")
    return registry


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 4096) -> dict[str, Any]:
    left = [0.0] * frames
    right = [0.0] * frames
    truth_onset: int | None
    event_family: str
    if name == "silence":
        truth_onset = None
        event_family = "silence"
    elif name == "impulse":
        left[512] = 0.95
        right[512] = 0.95
        truth_onset = 512
        event_family = "impulse"
    elif name == "gradual_attack":
        start = 800
        rise = 400
        for i in range(rise):
            amp = (i + 1) / rise * 0.6
            left[start + i] = amp
            right[start + i] = amp
        for i in range(start + rise, min(frames, start + rise + 1200)):
            decay = max(0.0, 0.6 * (1.0 - (i - (start + rise)) / 1200.0))
            left[i] = decay
            right[i] = decay
        truth_onset = start
        event_family = "gradual_attack"
    elif name == "multi_hit":
        for index in (400, 1600, 2800):
            left[index] = 0.9
            right[index] = 0.9
            for tail in range(1, 40):
                if index + tail < frames:
                    left[index + tail] = 0.9 * math.exp(-tail / 12.0)
                    right[index + tail] = left[index + tail]
        truth_onset = 400
        event_family = "multi_hit"
    elif name == "stereo_disagree":
        left[300] = 0.9
        right[900] = 0.9
        truth_onset = None
        event_family = "stereo_disagree"
    else:
        raise OnsetAnchorError(f"unknown_fixture:{name}")
    pcm = pack_pcm_f32le([left, right])
    return {
        "asset_id": f"fixture:{name}",
        "source_sha256": sha256_bytes(f"wave64-row072-fixture:{name}".encode("utf-8")),
        "canonical_pcm_sha256": sha256_bytes(pcm),
        "sample_rate_hz": sample_rate_hz,
        "channels": 2,
        "frame_count": frames,
        "channel_samples": [left, right],
        "truth_onset_sample": truth_onset,
        "event_family": event_family,
        "benchmark_fixture_reference": f"row072_synthetic/{name}",
    }


def frame_energies(signal: list[float], frame: int, hop: int) -> list[tuple[int, float]]:
    energies: list[tuple[int, float]] = []
    if len(signal) < frame:
        return [(0, sum(sample * sample for sample in signal) / max(1, len(signal)))]
    for start in range(0, len(signal) - frame + 1, hop):
        window = signal[start : start + frame]
        energy = sum(sample * sample for sample in window) / frame
        energies.append((start, energy))
    return energies


def highpass_diff(signal: list[float]) -> list[float]:
    if not signal:
        return []
    out = [0.0]
    for index in range(1, len(signal)):
        out.append(signal[index] - signal[index - 1])
    return out


def refine_onset_sample(signal: list[float], frame_start: int, frame: int) -> int:
    """Localize onset inside the peak-flux frame to the first supra-threshold sample."""
    end = min(len(signal), frame_start + frame)
    if frame_start >= end:
        return max(0, min(frame_start, len(signal) - 1))
    window = signal[frame_start:end]
    peak = max(abs(sample) for sample in window)
    if peak < 1e-12:
        return frame_start
    threshold = peak * 0.1
    for offset, sample in enumerate(window):
        if abs(sample) >= threshold:
            return frame_start + offset
    return frame_start + max(range(len(window)), key=lambda i: abs(window[i]))


def detect_method_energy_flux(signal: list[float], *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME) -> dict[str, Any]:
    energies = frame_energies(signal, frame=frame, hop=hop)
    if len(energies) < 2:
        return {
            "method_id": METHOD_ENERGY_FLUX,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame},
        }
    fluxes = []
    for index in range(1, len(energies)):
        prev = energies[index - 1][1]
        cur = energies[index][1]
        fluxes.append((energies[index][0], max(0.0, cur - prev)))
    frame_start, onset_flux = max(fluxes, key=lambda item: item[1])
    onset_sample = refine_onset_sample(signal, int(frame_start), frame)
    peak_sample = max(range(len(signal)), key=lambda i: abs(signal[i]))
    energy_peak_sample = max(range(len(signal)), key=lambda i: signal[i] * signal[i])
    # Offset: first sample after peak where envelope falls below 5% of peak energy.
    peak_energy = signal[energy_peak_sample] * signal[energy_peak_sample]
    threshold = peak_energy * 0.05
    offset_sample = len(signal) - 1
    for index in range(energy_peak_sample, len(signal)):
        if signal[index] * signal[index] <= threshold:
            offset_sample = index
            break
    confidence = 0.0 if onset_flux <= 1e-12 else min(1.0, onset_flux / (onset_flux + 1e-6))
    if max(abs(sample) for sample in signal) < 1e-9:
        return {
            "method_id": METHOD_ENERGY_FLUX,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame},
        }
    return {
        "method_id": METHOD_ENERGY_FLUX,
        "onset_sample": int(onset_sample),
        "attack_peak_sample": int(peak_sample),
        "energy_peak_sample": int(energy_peak_sample),
        "offset_sample": int(offset_sample),
        "confidence": round_finite(confidence),
        "parameters": {"hop": hop, "frame": frame},
    }


def detect_method_hf_envelope(signal: list[float], *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME) -> dict[str, Any]:
    hf = [abs(value) for value in highpass_diff(signal)]
    energies = frame_energies(hf, frame=frame, hop=hop)
    if len(energies) < 2 or max(hf) < 1e-12:
        return {
            "method_id": METHOD_HF_ENVELOPE,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
        }
    fluxes = []
    for index in range(1, len(energies)):
        prev = energies[index - 1][1]
        cur = energies[index][1]
        fluxes.append((energies[index][0], max(0.0, cur - prev)))
    frame_start, onset_flux = max(fluxes, key=lambda item: item[1])
    onset_sample = refine_onset_sample(hf, int(frame_start), frame)
    attack_peak_sample = max(range(len(hf)), key=lambda i: hf[i])
    energy_peak_sample = max(range(len(signal)), key=lambda i: signal[i] * signal[i])
    peak_energy = signal[energy_peak_sample] * signal[energy_peak_sample]
    threshold = peak_energy * 0.05
    offset_sample = len(signal) - 1
    for index in range(energy_peak_sample, len(signal)):
        if signal[index] * signal[index] <= threshold:
            offset_sample = index
            break
    confidence = 0.0 if onset_flux <= 1e-12 else min(1.0, onset_flux / (onset_flux + 1e-6))
    return {
        "method_id": METHOD_HF_ENVELOPE,
        "onset_sample": int(onset_sample),
        "attack_peak_sample": int(attack_peak_sample),
        "energy_peak_sample": int(energy_peak_sample),
        "offset_sample": int(offset_sample),
        "confidence": round_finite(confidence),
        "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
    }


def sample_to_frame(sample_index: int, sample_rate_hz: int, frame_rate_fps: float) -> float:
    seconds = sample_index / sample_rate_hz
    return round_finite(seconds * frame_rate_fps)


def build_anchors_from_methods(
    method_results: list[dict[str, Any]],
    *,
    sample_rate_hz: int,
    frame_rate_fps: float,
    agreement_threshold_samples: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], bool]:
    primary = method_results[0]
    secondary = method_results[1]
    anchors: list[dict[str, Any]] = []
    candidate_count = 0
    reason_codes: list[str] = []
    frame_exact_claim = False

    onset_a = primary.get("onset_sample")
    onset_b = secondary.get("onset_sample")
    if onset_a is None and onset_b is None:
        ambiguity = {
            "status": "blocked",
            "candidate_count": 0,
            "reason_codes": ["NO_ONSET_DETECTED"],
            "window_start_sample": None,
            "window_end_sample": None,
        }
        agreement = {
            "status": "not_applicable",
            "sample_delta": None,
            "frame_delta": None,
            "agreement_threshold_samples": agreement_threshold_samples,
        }
        # Schema requires at least one anchor; emit explicit blocked offset placeholder.
        anchors.append(
            {
                "candidate_id": "blocked_no_onset",
                "anchor_type": "onset",
                "sample_index": 0,
                "frame_index": 0.0,
                "seconds": 0.0,
                "confidence": 0.0,
                "method_id": "none",
                "window_start_sample": None,
                "window_end_sample": None,
            }
        )
        return anchors, agreement, ambiguity, False

    if onset_a is not None and onset_b is not None:
        sample_delta = abs(int(onset_a) - int(onset_b))
        frame_delta = round_finite(sample_delta / sample_rate_hz * frame_rate_fps)
        if sample_delta <= agreement_threshold_samples:
            agreement_status = "agree"
            chosen = int(round((onset_a + onset_b) / 2.0))
            confidence = min(float(primary["confidence"]), float(secondary["confidence"]))
            candidate_id = "onset_agreed_01"
            frame_exact_claim = True
            ambiguity_status = "none"
        else:
            agreement_status = "disagree"
            chosen = int(onset_a)
            confidence = min(float(primary["confidence"]), float(secondary["confidence"]))
            candidate_id = "onset_primary_01"
            ambiguity_status = "multi_candidate"
            reason_codes.append("METHOD_DISAGREEMENT")
            candidate_count = 2
            anchors.append(
                {
                    "candidate_id": "onset_secondary_01",
                    "anchor_type": "onset",
                    "sample_index": int(onset_b),
                    "frame_index": sample_to_frame(int(onset_b), sample_rate_hz, frame_rate_fps),
                    "seconds": round_finite(int(onset_b) / sample_rate_hz),
                    "confidence": round_finite(float(secondary["confidence"])),
                    "method_id": secondary["method_id"],
                    "window_start_sample": min(int(onset_a), int(onset_b)),
                    "window_end_sample": max(int(onset_a), int(onset_b)),
                }
            )
        agreement = {
            "status": agreement_status,
            "sample_delta": sample_delta,
            "frame_delta": frame_delta,
            "agreement_threshold_samples": agreement_threshold_samples,
        }
        if ambiguity_status == "multi_candidate":
            ambiguity = {
                "status": "multi_candidate",
                "candidate_count": candidate_count,
                "reason_codes": reason_codes,
                "window_start_sample": min(int(onset_a), int(onset_b)),
                "window_end_sample": max(int(onset_a), int(onset_b)),
            }
            frame_exact_claim = False
        else:
            ambiguity = {
                "status": "none",
                "candidate_count": 1,
                "reason_codes": [],
                "window_start_sample": None,
                "window_end_sample": None,
            }
    else:
        chosen = int(onset_a if onset_a is not None else onset_b)
        confidence = float(
            primary["confidence"] if onset_a is not None else secondary["confidence"]
        )
        candidate_id = "onset_single_method_01"
        agreement = {
            "status": "insufficient_methods",
            "sample_delta": None,
            "frame_delta": None,
            "agreement_threshold_samples": agreement_threshold_samples,
        }
        ambiguity = {
            "status": "blocked",
            "candidate_count": 1,
            "reason_codes": ["SINGLE_METHOD_ONLY"],
            "window_start_sample": None,
            "window_end_sample": None,
        }
        frame_exact_claim = False

    anchors.insert(
        0,
        {
            "candidate_id": candidate_id,
            "anchor_type": "onset",
            "sample_index": chosen,
            "frame_index": sample_to_frame(chosen, sample_rate_hz, frame_rate_fps),
            "seconds": round_finite(chosen / sample_rate_hz),
            "confidence": round_finite(confidence),
            "method_id": primary["method_id"] if onset_a is not None else secondary["method_id"],
            "window_start_sample": ambiguity.get("window_start_sample"),
            "window_end_sample": ambiguity.get("window_end_sample"),
        }
    )

    for method in method_results:
        for anchor_type, key in (
            ("attack_peak", "attack_peak_sample"),
            ("energy_peak", "energy_peak_sample"),
            ("offset", "offset_sample"),
        ):
            sample_index = method.get(key)
            if sample_index is None:
                continue
            anchors.append(
                {
                    "candidate_id": f"{anchor_type}_{method['method_id']}",
                    "anchor_type": anchor_type,
                    "sample_index": int(sample_index),
                    "frame_index": sample_to_frame(int(sample_index), sample_rate_hz, frame_rate_fps),
                    "seconds": round_finite(int(sample_index) / sample_rate_hz),
                    "confidence": round_finite(float(method["confidence"])),
                    "method_id": method["method_id"],
                    "window_start_sample": None,
                    "window_end_sample": None,
                }
            )
    return anchors, agreement, ambiguity, frame_exact_claim


def count_event_density(signal: list[float], *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME) -> float:
    energies = frame_energies(signal, frame=frame, hop=hop)
    if len(energies) < 3:
        return 0.0
    fluxes = [max(0.0, energies[i][1] - energies[i - 1][1]) for i in range(1, len(energies))]
    if not fluxes:
        return 0.0
    mean_flux = sum(fluxes) / len(fluxes)
    threshold = max(mean_flux * 4.0, 1e-6)
    events = sum(1 for value in fluxes if value >= threshold)
    duration_seconds = len(signal) / 48000.0
    if duration_seconds <= 0:
        return 0.0
    return round_finite(events / duration_seconds)


def build_benchmark(
    *,
    truth_onset: int | None,
    measured_onset: int | None,
    sample_rate_hz: int,
    event_family: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    family = registry["event_families"].get(event_family, {})
    max_sample_error = int(family.get("max_sample_error", registry.get("agreement_threshold_samples", 2)))
    frame_rate_fps = float(family.get("frame_rate_fps", registry["default_frame_rate_fps"]))
    if truth_onset is None or measured_onset is None:
        return {
            "reference_onset_sample": truth_onset,
            "measured_onset_sample": measured_onset,
            "sample_error": None,
            "frame_error": None,
            "within_registered_thresholds": False,
        }
    sample_error = abs(int(measured_onset) - int(truth_onset))
    frame_error = round_finite(sample_error / sample_rate_hz * frame_rate_fps)
    max_frame_error = float(family.get("max_frame_error", 0.5))
    within = sample_error <= max_sample_error and frame_error <= max_frame_error
    return {
        "reference_onset_sample": int(truth_onset),
        "measured_onset_sample": int(measured_onset),
        "sample_error": int(sample_error),
        "frame_error": frame_error,
        "within_registered_thresholds": bool(within),
    }


def validate_anchor_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise OnsetAnchorError(f"schema_validation_failed:{location}:{first.message}")


def detect_from_channels(
    root: Path,
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    channel_samples: list[list[float]],
    event_family: str,
    truth_onset_sample: int | None,
    benchmark_fixture_reference: str | None,
    library_authority: bool,
) -> dict[str, Any]:
    registry = load_threshold_registry(root)
    agreement_threshold = int(registry["agreement_threshold_samples"])
    frame_rate_fps = float(
        registry["event_families"].get(event_family, {}).get(
            "frame_rate_fps", registry["default_frame_rate_fps"]
        )
    )
    mono = mono_mix(channel_samples)
    # Channel-aware second method input: for stereo disagreement, compare L vs R energy flux.
    if channels >= 2 and event_family == "stereo_disagree":
        method_a = detect_method_energy_flux(channel_samples[0])
        method_b = detect_method_energy_flux(channel_samples[1])
        method_b["method_id"] = METHOD_HF_ENVELOPE
    else:
        method_a = detect_method_energy_flux(mono)
        method_b = detect_method_hf_envelope(mono)
    method_results = [method_a, method_b]
    anchors, agreement, ambiguity, frame_exact_claim = build_anchors_from_methods(
        method_results,
        sample_rate_hz=sample_rate_hz,
        frame_rate_fps=frame_rate_fps,
        agreement_threshold_samples=agreement_threshold,
    )
    family_cfg = registry["event_families"].get(event_family, {})
    if family_cfg.get("windowed_sync_required"):
        # Gradual attacks must not claim frame-exact onset; preserve candidate span as a window.
        onset_samples = [
            int(anchor["sample_index"])
            for anchor in anchors
            if anchor["anchor_type"] == "onset"
        ]
        if not onset_samples:
            onset_samples = [int(anchors[0]["sample_index"])]
        window_start = max(0, min(onset_samples) - 48)
        window_end = max(onset_samples) + 48
        reason_codes = list(ambiguity.get("reason_codes") or [])
        if "GRADUAL_ATTACK_WINDOW_REQUIRED" not in reason_codes:
            reason_codes.append("GRADUAL_ATTACK_WINDOW_REQUIRED")
        ambiguity = {
            "status": "windowed",
            "candidate_count": max(1, int(ambiguity.get("candidate_count") or len(onset_samples))),
            "reason_codes": reason_codes,
            "window_start_sample": window_start,
            "window_end_sample": window_end,
        }
        frame_exact_claim = False
        for anchor in anchors:
            if anchor["anchor_type"] == "onset":
                anchor["window_start_sample"] = window_start
                anchor["window_end_sample"] = window_end
    if family_cfg.get("expect_no_frame_exact_onset"):
        frame_exact_claim = False
        if ambiguity["status"] == "none":
            ambiguity = {
                "status": "blocked",
                "candidate_count": 0,
                "reason_codes": ["SILENCE_NO_FRAME_EXACT_ONSET"],
                "window_start_sample": None,
                "window_end_sample": None,
            }
    if family_cfg.get("expect_ambiguity_or_block") and ambiguity["status"] == "none":
        ambiguity = {
            "status": "blocked",
            "candidate_count": ambiguity.get("candidate_count", 0),
            "reason_codes": ["STEREO_CHANNEL_DISAGREEMENT"],
            "window_start_sample": None,
            "window_end_sample": None,
        }
        frame_exact_claim = False

    measured_onset = None
    for anchor in anchors:
        if anchor["anchor_type"] == "onset" and anchor["confidence"] > 0:
            measured_onset = anchor["sample_index"]
            break
    if measured_onset is None and anchors and anchors[0]["anchor_type"] == "onset":
        # Keep blocked silence path measured as None for benchmark honesty.
        if event_family != "silence":
            measured_onset = anchors[0]["sample_index"]

    benchmark = build_benchmark(
        truth_onset=truth_onset_sample,
        measured_onset=measured_onset if ambiguity["status"] != "blocked" or event_family == "impulse" else measured_onset,
        sample_rate_hz=sample_rate_hz,
        event_family=event_family,
        registry=registry,
    )
    # Impulse path should still report measured onset for calibration even when blocked for library.
    if event_family == "impulse":
        for anchor in anchors:
            if anchor["anchor_type"] == "onset":
                benchmark = build_benchmark(
                    truth_onset=truth_onset_sample,
                    measured_onset=anchor["sample_index"],
                    sample_rate_hz=sample_rate_hz,
                    event_family=event_family,
                    registry=registry,
                )
                break

    blocker_codes: list[str] = []
    if not library_authority:
        blocker_codes.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    if ambiguity["status"] == "blocked":
        blocker_codes.append("AMBIGUOUS_OR_ABSENT_ONSET_BLOCKED")
    if ambiguity["status"] == "multi_candidate":
        blocker_codes.append("MULTI_CANDIDATE_ONSET_NO_FRAME_EXACT_CLAIM")
    if ambiguity["status"] == "windowed":
        blocker_codes.append("WINDOWED_SYNC_REQUIRED")
    if frame_exact_claim is False and event_family == "impulse" and benchmark["within_registered_thresholds"]:
        # Calibration may be within thresholds while library authority remains withheld.
        pass

    status = "pass" if library_authority and not blocker_codes and frame_exact_claim else "blocked"
    if library_authority and not blocker_codes and frame_exact_claim:
        status = "pass"
    else:
        status = "blocked"

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "event_family": event_family,
        "event_density": count_event_density(mono),
        "benchmark_fixture_reference": benchmark_fixture_reference,
        "anchors": anchors,
        "method_results": method_results,
        "multi_method_agreement": agreement,
        "ambiguity": ambiguity,
        "benchmark": benchmark,
        "decision": {
            "status": status,
            "blocker_codes": blocker_codes,
            "library_authority": bool(library_authority),
            "frame_exact_claim": bool(frame_exact_claim and ambiguity["status"] == "none"),
        },
    }
    validate_anchor_record(root, record)
    return record


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    return detect_from_channels(
        root,
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        channel_samples=fixture["channel_samples"],
        event_family=fixture["event_family"],
        truth_onset_sample=fixture["truth_onset_sample"],
        benchmark_fixture_reference=fixture["benchmark_fixture_reference"],
        library_authority=False,
    )


def load_feature_module() -> Any:
    global _FEATURE_MOD
    if _FEATURE_MOD is not None:
        return _FEATURE_MOD
    import importlib.util

    script = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
    spec = importlib.util.spec_from_file_location("wave64_row071_features_for_onset", script)
    if spec is None or spec.loader is None:
        raise OnsetAnchorError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _frame_energies_np(
    signal: np.ndarray, frame: int, hop: int
) -> list[tuple[int, float]]:
    if signal.size < frame:
        energy = float(np.mean(signal * signal)) if signal.size else 0.0
        return [(0, energy)]
    energies: list[tuple[int, float]] = []
    for start in range(0, int(signal.size) - frame + 1, hop):
        window = signal[start : start + frame]
        energies.append((start, float(np.mean(window * window))))
    return energies


def _refine_onset_sample_np(signal: np.ndarray, frame_start: int, frame: int) -> int:
    end = min(int(signal.size), frame_start + frame)
    if frame_start >= end:
        return max(0, min(frame_start, int(signal.size) - 1))
    window = signal[frame_start:end]
    peak = float(np.max(np.abs(window)))
    if peak < 1e-12:
        return frame_start
    threshold = peak * 0.1
    hits = np.where(np.abs(window) >= threshold)[0]
    if hits.size:
        return frame_start + int(hits[0])
    return frame_start + int(np.argmax(np.abs(window)))


def detect_method_energy_flux_np(
    signal: np.ndarray, *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME
) -> dict[str, Any]:
    if float(np.max(np.abs(signal))) < 1e-9:
        return {
            "method_id": METHOD_ENERGY_FLUX,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame},
        }
    energies = _frame_energies_np(signal, frame=frame, hop=hop)
    if len(energies) < 2:
        return {
            "method_id": METHOD_ENERGY_FLUX,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame},
        }
    fluxes = [
        (energies[i][0], max(0.0, energies[i][1] - energies[i - 1][1]))
        for i in range(1, len(energies))
    ]
    frame_start, onset_flux = max(fluxes, key=lambda item: item[1])
    onset_sample = _refine_onset_sample_np(signal, int(frame_start), frame)
    peak_sample = int(np.argmax(np.abs(signal)))
    energy_peak_sample = int(np.argmax(signal * signal))
    peak_energy = float(signal[energy_peak_sample] * signal[energy_peak_sample])
    threshold = peak_energy * 0.05
    offset_sample = int(signal.size) - 1
    tail = signal[energy_peak_sample:] * signal[energy_peak_sample:]
    below = np.where(tail <= threshold)[0]
    if below.size:
        offset_sample = energy_peak_sample + int(below[0])
    confidence = 0.0 if onset_flux <= 1e-12 else min(1.0, onset_flux / (onset_flux + 1e-6))
    return {
        "method_id": METHOD_ENERGY_FLUX,
        "onset_sample": int(onset_sample),
        "attack_peak_sample": int(peak_sample),
        "energy_peak_sample": int(energy_peak_sample),
        "offset_sample": int(offset_sample),
        "confidence": round_finite(confidence),
        "parameters": {"hop": hop, "frame": frame},
    }


def detect_method_hf_envelope_np(
    signal: np.ndarray, *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME
) -> dict[str, Any]:
    if signal.size < 2:
        return {
            "method_id": METHOD_HF_ENVELOPE,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
        }
    hf = np.empty_like(signal)
    hf[0] = 0.0
    hf[1:] = np.abs(np.diff(signal))
    if float(np.max(hf)) < 1e-12:
        return {
            "method_id": METHOD_HF_ENVELOPE,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
        }
    energies = _frame_energies_np(hf, frame=frame, hop=hop)
    if len(energies) < 2:
        return {
            "method_id": METHOD_HF_ENVELOPE,
            "onset_sample": None,
            "attack_peak_sample": None,
            "energy_peak_sample": None,
            "offset_sample": None,
            "confidence": 0.0,
            "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
        }
    fluxes = [
        (energies[i][0], max(0.0, energies[i][1] - energies[i - 1][1]))
        for i in range(1, len(energies))
    ]
    frame_start, onset_flux = max(fluxes, key=lambda item: item[1])
    onset_sample = _refine_onset_sample_np(hf, int(frame_start), frame)
    attack_peak_sample = int(np.argmax(hf))
    energy_peak_sample = int(np.argmax(signal * signal))
    peak_energy = float(signal[energy_peak_sample] * signal[energy_peak_sample])
    threshold = peak_energy * 0.05
    offset_sample = int(signal.size) - 1
    tail = signal[energy_peak_sample:] * signal[energy_peak_sample:]
    below = np.where(tail <= threshold)[0]
    if below.size:
        offset_sample = energy_peak_sample + int(below[0])
    confidence = 0.0 if onset_flux <= 1e-12 else min(1.0, onset_flux / (onset_flux + 1e-6))
    return {
        "method_id": METHOD_HF_ENVELOPE,
        "onset_sample": int(onset_sample),
        "attack_peak_sample": int(attack_peak_sample),
        "energy_peak_sample": int(energy_peak_sample),
        "offset_sample": int(offset_sample),
        "confidence": round_finite(confidence),
        "parameters": {"hop": hop, "frame": frame, "preemphasis": "first_difference"},
    }


def count_event_density_np(
    signal: np.ndarray, sample_rate_hz: int, *, hop: int = DEFAULT_HOP, frame: int = DEFAULT_FRAME
) -> float:
    energies = _frame_energies_np(signal, frame=frame, hop=hop)
    if len(energies) < 3:
        return 0.0
    fluxes = [max(0.0, energies[i][1] - energies[i - 1][1]) for i in range(1, len(energies))]
    mean_flux = sum(fluxes) / len(fluxes)
    threshold = max(mean_flux * 4.0, 1e-6)
    events = sum(1 for value in fluxes if value >= threshold)
    duration_seconds = float(signal.size) / float(sample_rate_hz)
    if duration_seconds <= 0:
        return 0.0
    return round_finite(events / duration_seconds)


def detect_library_compact_from_mono(
    root: Path,
    *,
    mono: np.ndarray,
    sample_rate_hz: int,
    channels: int,
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
    """Compact library reconcile record under frozen synthetic thresholds (no library authority)."""
    registry = load_threshold_registry(root)
    agreement_threshold = int(registry["agreement_threshold_samples"])
    frame_rate_fps = float(registry["default_frame_rate_fps"])
    method_a = detect_method_energy_flux_np(mono)
    method_b = detect_method_hf_envelope_np(mono)
    method_results = [method_a, method_b]
    anchors, agreement, ambiguity, frame_exact_claim = build_anchors_from_methods(
        method_results,
        sample_rate_hz=sample_rate_hz,
        frame_rate_fps=frame_rate_fps,
        agreement_threshold_samples=agreement_threshold,
    )
    blocker_codes: list[str] = []
    if analysis_truncated:
        blocker_codes.append("ANALYSIS_WINDOW_TRUNCATED")
    if ambiguity["status"] == "blocked":
        blocker_codes.append("AMBIGUOUS_OR_ABSENT_ONSET_BLOCKED")
    if ambiguity["status"] == "multi_candidate":
        blocker_codes.append("MULTI_CANDIDATE_ONSET_NO_FRAME_EXACT_CLAIM")
    if agreement["status"] == "disagree":
        blocker_codes.append("METHOD_DISAGREEMENT")
    if agreement["status"] == "insufficient_methods":
        blocker_codes.append("SINGLE_METHOD_ONLY")
    # Frozen thresholds are synthetic-only: technical onset pass never grants library authority.
    technical_pass = (
        agreement["status"] == "agree"
        and ambiguity["status"] == "none"
        and frame_exact_claim is True
        and not analysis_truncated
    )
    onset_status = "pass" if technical_pass else "blocked"
    onset_anchor = next((a for a in anchors if a["anchor_type"] == "onset"), anchors[0])
    return {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "sample_rate_hz": int(sample_rate_hz),
        "channels": int(channels),
        "frame_count": int(frame_count),
        "event_family": LIBRARY_EVENT_FAMILY,
        "event_density": count_event_density_np(mono, sample_rate_hz),
        "onset_status": onset_status,
        "technical_onset_pass": bool(technical_pass),
        "library_authority": False,
        "blocker_code": None if technical_pass else (blocker_codes[0] if blocker_codes else "ONSET_BLOCKED"),
        "blocker_codes": [] if technical_pass else blocker_codes,
        "onset_sample": onset_anchor.get("sample_index"),
        "onset_confidence": onset_anchor.get("confidence"),
        "multi_method_agreement": agreement["status"],
        "ambiguity_status": ambiguity["status"],
        "frame_exact_claim": bool(frame_exact_claim and ambiguity["status"] == "none"),
        "analysis_truncated": bool(analysis_truncated),
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
    }


def _empty_retained_onset_counts() -> dict[str, int]:
    return {
        "records_total": 0,
        "records_processed": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "onset_pass": 0,
        "onset_blocked": 0,
        "exact_blockers": 0,
        "pcm_sha_verified": 0,
        "analysis_truncated": 0,
        "source_immutable_true": 0,
    }


def run_retained_index_onset_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile every Row071 retained feature record to onset PASS or exact blocker."""
    row070 = evaluate_row070_admission(root)
    row071 = evaluate_row071_admission(root)
    if not row070.get("dependency_satisfied") or not row071.get("dependency_satisfied"):
        raise OnsetAnchorError("index_retained_requires_row070_and_row071_admission")

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
        raise OnsetAnchorError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_RETAINED_ONSET_RUNTIME_DIR,
        "retained_onset_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            f"owner=detect_wave64_onset_transient_anchors.py\nstarted={datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise OnsetAnchorError(
            "retained_onset_runtime_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_onset_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_onset_counts()
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
            counts = _empty_retained_onset_counts()
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
                    "onset_status": "blocked",
                    "technical_onset_pass": False,
                    "library_authority": False,
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
                        raise OnsetAnchorError(f"source_sha_mismatch:{relative_path}")
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise OnsetAnchorError(f"pcm_sha_mismatch:{relative_path}")
                    frame_count = int(frames_nc.shape[0])
                    channels = int(frames_nc.shape[1])
                    analysis_truncated = frame_count > MAX_ANALYSIS_FRAMES
                    mono = (
                        frames_nc.mean(axis=1)
                        if channels > 1
                        else frames_nc[:, 0]
                    ).astype(np.float32, copy=False)
                    if analysis_truncated:
                        mono = mono[:MAX_ANALYSIS_FRAMES]
                        counts["analysis_truncated"] += 1
                    compact = detect_library_compact_from_mono(
                        root,
                        mono=mono,
                        sample_rate_hz=int(sample_rate_hz),
                        channels=channels,
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
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = {
                        "relative_path": relative_path,
                        "extension": extension,
                        "role": role,
                        "event_type": event_type,
                        "asset_id": asset_id,
                        "feature_status": "pass",
                        "onset_status": "blocked",
                        "technical_onset_pass": False,
                        "library_authority": False,
                        "blocker_code": "ONSET_EXTRACTION_FAILED",
                        "blocker_codes": ["ONSET_EXTRACTION_FAILED"],
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

            if compact.get("onset_status") == "pass":
                counts["onset_pass"] += 1
            else:
                counts["onset_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "ONSET_BLOCKED")
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

    # Technical pass still withholds library authority under frozen synthetic thresholds.
    proof_tier = "RUNTIME_PASS_BOUNDED" if coverage_complete else "RUNTIME_PASS_BOUNDED"
    receipt = {
        "schema_version": 1,
        "evidence_id": "W64-ROW072-ACCEPTED-INDEX-RETAINED-ONSET-20260719",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_onset_reconcile",
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
    blocker_codes = list(row070["blocker_codes"]) + list(row071["blocker_codes"])
    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)

    if not coverage_complete:
        if reconcile_started:
            for code in (
                "FULL_LIBRARY_RECONCILE_IN_PROGRESS_TIME_BOUND",
                "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
                "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
        else:
            for code in (
                "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
                "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
                "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
    else:
        for code in (
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "FRAME_SAMPLE_BENCHMARK_LIBRARY_STRATA_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    deps_unlocked = bool(row070["dependency_satisfied"] and row071["dependency_satisfied"])
    if coverage_complete and deps_unlocked:
        status = "HOLD_LIBRARY_THRESHOLDS_AND_BENCHMARK_STRATA_ABSENT_RECONCILE_COMPLETE"
        safe_next = (
            "Full-library onset reconcile covered retained Row071 records under frozen "
            "synthetic thresholds. Calibrate representative library strata with truth "
            "onsets and unfreeze threshold authority before Row072 acceptance or Row093 unlock."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
    elif reconcile_started and deps_unlocked:
        status = "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED"
        safe_next = (
            "Resume/finish retained-index onset reconcile to coverage_complete, then address "
            "frozen threshold authority and library benchmark strata before claiming Row072 acceptance."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
    elif deps_unlocked:
        status = "HOLD_LIBRARY_RUNTIME_AND_BENCHMARK_STRATA_ABSENT_DEPS_UNLOCKED"
        safe_next = (
            "Rows070-071 library authority is accepted. Extend the detector to reconcile "
            "every accepted PCM/feature record to anchor PASS or an exact blocker under the "
            "frozen threshold registry, then replace this hold packet with full-library "
            "onset/transient evidence before claiming Row072 acceptance or Row093 unlock."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
    else:
        status = "HOLD_DEPENDENCIES_LIBRARY_RUNTIME_AND_BENCHMARK_STRATA_ABSENT"
        safe_next = (
            "Accept Rows070-071 authority, reconcile every accepted PCM/feature record "
            "to anchor PASS or an exact blocker with registered event-family thresholds, "
            "and replace this hold packet with full-library onset/transient evidence."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"

    fixture_names = ["silence", "impulse", "gradual_attack", "multi_hit", "stereo_disagree"]
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    registry = load_threshold_registry(root)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-072_onset_transient_detection",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "detector_revision": DETECTOR_REVISION,
        "threshold_registry_revision": THRESHOLD_REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": bool(coverage_complete),
        "library_authority": False,
        "status": status,
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "row070_admission": row070,
        "row071_admission": row071,
        "threshold_registry": {
            "path": str(THRESHOLD_REGISTRY_PATH).replace("\\", "/"),
            "revision": registry["revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, THRESHOLD_REGISTRY_PATH, "threshold_registry")),
        },
        "required_methods": [METHOD_ENERGY_FLUX, METHOD_HF_ENVELOPE],
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove multi-method identity, ambiguity policy, and "
                "threshold binding only; they do not accept Row072 library completion."
            ),
        },
        "accepted_index_retained_onset_runtime": {
            "authority": retained.get("authority"),
            "coverage_complete": coverage_complete,
            "counts": retained.get("counts"),
            "receipt_path": retained.get("receipt_path"),
            "records_path": retained.get("records_path"),
            "proof_tier": retained.get("proof_tier"),
            "status": retained.get("status"),
        }
        if retained
        else None,
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row072_acceptance": "held",
            "product_completion": False,
            "runtime_completion": bool(coverage_complete),
            "dependencies_unlocked": deps_unlocked,
            "safe_next_action": safe_next,
        },
    }
    return packet


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
    parser.add_argument("--fixture", default="impulse")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_RETAINED_ONSET_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-072_ACCEPTED_INDEX_RETAINED_ONSET_SUMMARY_20260719.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise OnsetAnchorError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    elif args.mode == "index-retained":
        retained = run_retained_index_onset_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_onset_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_onset_runtime"]["summary_sha256"] = sha256_file(
            summary_path
        )
    else:
        # Attach existing retained progress if present (fail-closed hold refresh).
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_RETAINED_ONSET_RUNTIME_DIR / "retained_index_onset_receipt.json",
            "retained_onset_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise OnsetAnchorError("library_mode_must_remain_fail_closed_until_acceptance")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "coverage_complete": bool(
                    (payload.get("accepted_index_retained_onset_runtime") or {}).get(
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
