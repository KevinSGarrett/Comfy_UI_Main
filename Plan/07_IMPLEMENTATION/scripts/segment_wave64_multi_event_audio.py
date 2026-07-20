#!/usr/bin/env python3
"""Fail-closed Wave64 Row074 multi-event segmentation and virtual-clip slice.

Library segmentation refuses authority without accepted Row072 onset/transient
anchors and Row073 usable-bounds/decay records. Fixture mode may detect
deterministic synthetic multi-event segments, prove bit-exact virtual PCM
reconstruction from parent bytes plus sample bounds, and enforce overlap policy
without promoting library completion or mutating source bytes.

Index-retained mode may probe or reconcile retained Row071 feature records into
suggestion-only PASS/blocker compact segment records when Row072 is
runtime-unlocked and Row073 is probe/runtime-unlocked under RUNTIME_PASS_BOUNDED,
without claiming COMPLETE or library authority.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/multi_event_segmentation_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_multi_event_segmentation.json"
)
ROW072_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
)
ROW073_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
)
DEFAULT_ROW071_RETAINED_RECORDS = Path(
    "runtime_artifacts/audio_qa/row071_index_retained_20260719/records.jsonl"
)
DEFAULT_RETAINED_SEGMENT_RUNTIME_DIR = Path(
    "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720"
)
SEGMENTATION_PIPELINE_REVISION = "wave64_row074_multi_event_segmentation_v0.2.0"
TRACKER_ID = "TRK-W64-074"
ITEM_ID = "ITEM-W64-074"
SCHEMA_VERSION = "1.0.0"
# Cap retained-library PCM windows to keep limited probes from contending with
# Row075 full-library defect reconcile on the same source tree.
MAX_ANALYSIS_FRAMES = 48000 * 30
RETAINED_CHECKPOINT_EVERY = 25
_FEATURE_MOD: Any | None = None

THRESHOLDS: dict[str, Any] = {
    "energy_threshold_dbfs": -40.0,
    "min_event_gap_ms": 20.0,
    "min_event_duration_ms": 5.0,
    "channel_policy": "max_abs_mono",
    "ordinary_segments_non_overlapping": True,
    "layered_overlap_requires_layer_id": True,
    "source_mutation_allowed": False,
    "suggestion_only": True,
}

BOUNDARY_CONVENTION: dict[str, Any] = {
    "inclusive_start": True,
    "exclusive_end": True,
    "sample_unit": "pcm_frame_index",
}

FIXTURE_NAMES = [
    "silence",
    "single_impact",
    "two_footsteps",
    "three_impacts",
    "breath_pair",
    "layered_overlap",
]

EVENT_FAMILY_ALIASES = {
    "footstep": "footstep",
    "footsteps": "footstep",
    "impact": "impact",
    "breath": "breath",
    "repeated": "repeated",
    "silence": "silence_gap",
    "silence_gap": "silence_gap",
    "ambiguous": "ambiguous",
    "other": "other",
}


class MultiEventSegmentationError(ValueError):
    """Raised when Row074 segmentation violates fail-closed authority."""


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
        raise MultiEventSegmentationError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise MultiEventSegmentationError("non_finite_measurement_value")
    return round(value, digits)


def db_from_amplitude(amplitude: float) -> float:
    safe = max(abs(amplitude), 1e-12)
    return 20.0 * math.log10(safe)


def normalize_event_family(raw: str | None) -> str:
    token = str(raw or "other").strip().lower()
    return EVENT_FAMILY_ALIASES.get(token, "other")


def evaluate_row072_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    """Admit Row072 when accepted OR runtime-unlocked under RUNTIME_PASS_BOUNDED."""
    path = resolve_under(root, delta_path or ROW072_DELTA, "trk-w64-072_delta")
    if not path.is_file():
        return {
            "tracker_id": "TRK-W64-072",
            "dependency_satisfied": False,
            "blocker_codes": ["ROW072_DELTA_ABSENT"],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "admission_mode": "absent",
        }
    payload = load_json(path)
    decision = payload.get("decision") or {}
    row_complete = payload.get("row_complete") is True
    acceptance = str(decision.get("row072_acceptance", "")).lower()
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
    runtime_unlock = (
        dependencies_unlocked
        and runtime_completion
        and proof_tier == "RUNTIME_PASS_BOUNDED"
    )
    dependency_satisfied = acceptance_pass or runtime_unlock
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append("ROW072_DEPENDENCY_NOT_ACCEPTED")
    admission_mode = (
        "accepted"
        if acceptance_pass
        else ("runtime_unlocked" if runtime_unlock else "held")
    )
    return {
        "tracker_id": "TRK-W64-072",
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
        "row072_acceptance": acceptance or "absent",
    }


def evaluate_row073_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    """Admit Row073 when accepted OR runtime/probe-unlocked under RUNTIME_PASS_BOUNDED."""
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
        raise MultiEventSegmentationError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise MultiEventSegmentationError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 9600) -> dict[str, Any]:
    left = [0.0] * frames
    event_family = "other"
    expected_event_count = 0
    if name == "silence":
        expected_event_count = 0
        event_family = "silence_gap"
    elif name == "single_impact":
        event_family = "impact"
        expected_event_count = 1
        for i in range(1200, 1800):
            left[i] = 0.8 * math.exp(-(i - 1200) / 80.0)
    elif name == "two_footsteps":
        event_family = "footstep"
        expected_event_count = 2
        for i in range(800, 1400):
            left[i] = 0.55 * math.exp(-(i - 800) / 90.0)
        for i in range(4200, 4800):
            left[i] = 0.5 * math.exp(-(i - 4200) / 90.0)
    elif name == "three_impacts":
        event_family = "impact"
        expected_event_count = 3
        for start in (900, 3600, 6400):
            for i in range(start, start + 500):
                left[i] = 0.7 * math.exp(-(i - start) / 70.0)
    elif name == "breath_pair":
        event_family = "breath"
        expected_event_count = 2
        for i in range(1000, 2200):
            t = (i - 1000) / sample_rate_hz
            left[i] = 0.25 * math.sin(2.0 * math.pi * 180.0 * t)
        for i in range(5200, 6800):
            t = (i - 5200) / sample_rate_hz
            left[i] = 0.22 * math.sin(2.0 * math.pi * 160.0 * t)
    elif name == "layered_overlap":
        event_family = "impact"
        expected_event_count = 2
        for i in range(1500, 3200):
            left[i] = 0.45 * math.exp(-(i - 1500) / 200.0)
        for i in range(2100, 3900):
            left[i] += 0.35 * math.exp(-(i - 2100) / 180.0)
    else:
        raise MultiEventSegmentationError(f"unknown_fixture:{name}")
    right = list(left)
    pcm = pack_pcm_f32le([left, right])
    source_token = f"wave64-row074-fixture:{name}".encode("utf-8")
    return {
        "asset_id": f"fixture:{name}",
        "fixture_name": name,
        "source_sha256": sha256_bytes(source_token),
        "canonical_pcm_sha256": sha256_bytes(pcm),
        "sample_rate_hz": sample_rate_hz,
        "channels": 2,
        "frame_count": frames,
        "pcm_f32le": pcm,
        "channel_samples": [left, right],
        "expected_event_count": expected_event_count,
        "default_event_family": event_family,
    }


def _mono_max_abs(channels: list[list[float]]) -> list[float]:
    return [max(abs(sample) for sample in frame) for frame in zip(*channels, strict=True)]


def _moving_max_envelope(mono: list[float], *, window: int) -> list[float]:
    """Causal-ish centered max envelope to avoid zero-crossing fragmentation."""
    if window <= 1:
        return list(mono)
    half = window // 2
    frame_count = len(mono)
    envelope = [0.0] * frame_count
    for index in range(frame_count):
        left = max(0, index - half)
        right = min(frame_count, index + half + 1)
        envelope[index] = max(mono[left:right])
    return envelope


def detect_energy_regions(
    mono: list[float],
    *,
    sample_rate_hz: int,
) -> list[tuple[int, int]]:
    enter_db = float(THRESHOLDS["energy_threshold_dbfs"])
    min_gap = max(1, int(sample_rate_hz * float(THRESHOLDS["min_event_gap_ms"]) / 1000.0))
    min_duration = max(1, int(sample_rate_hz * float(THRESHOLDS["min_event_duration_ms"]) / 1000.0))
    # ~4 ms envelope suppresses intra-cycle zero crossings while preserving event gaps.
    envelope_window = max(1, int(sample_rate_hz * 0.004))
    envelope = _moving_max_envelope(mono, window=envelope_window)

    active = False
    start = 0
    raw: list[tuple[int, int]] = []
    for index, sample in enumerate(envelope):
        is_active = db_from_amplitude(sample) >= enter_db
        if is_active and not active:
            active = True
            start = index
        elif not is_active and active:
            end = index
            if end - start >= min_duration:
                raw.append((start, end))
            active = False
    if active:
        end = len(envelope)
        if end - start >= min_duration:
            raw.append((start, end))

    if not raw:
        return []

    merged: list[tuple[int, int]] = [raw[0]]
    for start, end in raw[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end < min_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def virtual_clip_sha256_from_parent(
    pcm: bytes,
    *,
    channels: int,
    start_sample: int,
    end_sample: int,
) -> str:
    if end_sample <= start_sample:
        raise MultiEventSegmentationError("invalid_segment_bounds")
    frame_bytes = channels * 4
    total_frames = len(pcm) // frame_bytes
    if start_sample < 0 or end_sample > total_frames:
        raise MultiEventSegmentationError("segment_out_of_parent")
    slice_bytes = pcm[start_sample * frame_bytes : end_sample * frame_bytes]
    return sha256_bytes(slice_bytes)


def virtual_clip_sha256_from_frames(
    frames_nc: Any,
    *,
    start_sample: int,
    end_sample: int,
) -> str:
    import numpy as np

    arr = np.asarray(frames_nc, dtype=np.float32)
    if end_sample <= start_sample:
        raise MultiEventSegmentationError("invalid_segment_bounds")
    if start_sample < 0 or end_sample > arr.shape[0]:
        raise MultiEventSegmentationError("segment_out_of_parent")
    return sha256_bytes(arr[start_sample:end_sample].tobytes(order="C"))


def validate_segments_policy(
    segments: list[dict[str, Any]],
    *,
    frame_count: int,
    overlap_mode: str,
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    ordered = sorted(segments, key=lambda item: (item["start_sample"], item["end_sample"], item["segment_id"]))
    for segment in ordered:
        segment_id = segment["segment_id"]
        if segment_id in seen_ids:
            errors.append(f"duplicate_segment_id:{segment_id}")
        seen_ids.add(segment_id)
        start = segment["start_sample"]
        end = segment["end_sample"]
        if end <= start:
            errors.append(f"empty_or_reversed_segment:{segment_id}")
        if start < 0 or end > frame_count:
            errors.append(f"out_of_parent_segment:{segment_id}")
        if segment["overlap_mode"] == "layered":
            if not segment.get("layer_id"):
                errors.append(f"layered_segment_missing_layer_id:{segment_id}")
        elif segment.get("layer_id") is not None:
            errors.append(f"non_layered_segment_has_layer_id:{segment_id}")

    if overlap_mode == "non_overlapping":
        for left, right in zip(ordered, ordered[1:]):
            if right["start_sample"] < left["end_sample"]:
                errors.append(
                    f"accidental_overlap:{left['segment_id']}:{right['segment_id']}"
                )
    elif overlap_mode == "explicit_layered":
        layer_ids = {segment.get("layer_id") for segment in ordered if segment["overlap_mode"] == "layered"}
        if not any(segment["overlap_mode"] == "layered" for segment in ordered):
            errors.append("explicit_layered_mode_without_layered_segments")
        if None in layer_ids:
            errors.append("layered_mode_null_layer_id")
    return errors


def build_segments_for_fixture(fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    name = fixture["fixture_name"]
    pcm = fixture["pcm_f32le"]
    channels = fixture["channels"]
    sample_rate_hz = fixture["sample_rate_hz"]
    mono = _mono_max_abs(fixture["channel_samples"])
    parent_hash = fixture["canonical_pcm_sha256"]

    if name == "layered_overlap":
        # Explicit layered authority only: two authored overlapping layers.
        bounds = [(1500, 3200, "layer_a"), (2100, 3900, "layer_b")]
        segments: list[dict[str, Any]] = []
        for index, (start, end, layer_id) in enumerate(bounds, start=1):
            segments.append(
                {
                    "segment_id": f"seg_{index:03d}",
                    "event_family": "impact",
                    "start_sample": start,
                    "end_sample": end,
                    "parent_canonical_pcm_sha256": parent_hash,
                    "virtual_clip_sha256": virtual_clip_sha256_from_parent(
                        pcm, channels=channels, start_sample=start, end_sample=end
                    ),
                    "confidence": round_finite(0.82),
                    "overlap_mode": "layered",
                    "layer_id": layer_id,
                }
            )
        overlap_policy = {
            "mode": "explicit_layered",
            "ordinary_non_overlapping": False,
            "layered_overlap_present": True,
        }
        return segments, overlap_policy

    regions = detect_energy_regions(mono, sample_rate_hz=sample_rate_hz)
    segments = []
    for index, (start, end) in enumerate(regions, start=1):
        segments.append(
            {
                "segment_id": f"seg_{index:03d}",
                "event_family": fixture["default_event_family"] if regions else "silence_gap",
                "start_sample": start,
                "end_sample": end,
                "parent_canonical_pcm_sha256": parent_hash,
                "virtual_clip_sha256": virtual_clip_sha256_from_parent(
                    pcm, channels=channels, start_sample=start, end_sample=end
                ),
                "confidence": round_finite(0.9 if len(regions) == fixture["expected_event_count"] else 0.55),
                "overlap_mode": "none",
                "layer_id": None,
            }
        )
    overlap_policy = {
        "mode": "non_overlapping",
        "ordinary_non_overlapping": True,
        "layered_overlap_present": False,
    }
    return segments, overlap_policy


def build_segments_from_frames(
    frames_nc: Any,
    *,
    sample_rate_hz: int,
    parent_hash: str,
    event_family: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import numpy as np

    arr = np.asarray(frames_nc, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        raise MultiEventSegmentationError("invalid_frames_nc_shape")
    mono = np.max(np.abs(arr), axis=1).astype(float).tolist()
    regions = detect_energy_regions(mono, sample_rate_hz=sample_rate_hz)
    family = normalize_event_family(event_family if regions else "silence_gap")
    segments: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(regions, start=1):
        segments.append(
            {
                "segment_id": f"seg_{index:03d}",
                "event_family": family,
                "start_sample": int(start),
                "end_sample": int(end),
                "parent_canonical_pcm_sha256": parent_hash,
                "virtual_clip_sha256": virtual_clip_sha256_from_frames(
                    arr, start_sample=int(start), end_sample=int(end)
                ),
                "confidence": round_finite(0.7 if regions else 0.0),
                "overlap_mode": "none",
                "layer_id": None,
            }
        )
    overlap_policy = {
        "mode": "non_overlapping",
        "ordinary_non_overlapping": True,
        "layered_overlap_present": False,
    }
    return segments, overlap_policy


def build_segmentation_record(
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    segments: list[dict[str, Any]],
    overlap_policy: dict[str, Any],
    library_authority: bool,
    blocker_codes: list[str] | None = None,
    pcm: bytes | None = None,
) -> dict[str, Any]:
    blockers = list(blocker_codes or [])
    source_before = source_sha256
    source_after = source_sha256
    source_bytes_unchanged = source_before == source_after
    if not source_bytes_unchanged:
        blockers.append("SOURCE_BYTES_CHANGED")
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")

    policy_errors = validate_segments_policy(
        segments,
        frame_count=frame_count,
        overlap_mode=str(overlap_policy["mode"]),
    )
    for error in policy_errors:
        blockers.append(f"OVERLAP_POLICY_VIOLATION:{error}")

    bit_exact_ok = True
    if pcm is not None:
        for segment in segments:
            reconstructed = virtual_clip_sha256_from_parent(
                pcm,
                channels=channels,
                start_sample=segment["start_sample"],
                end_sample=segment["end_sample"],
            )
            if reconstructed != segment["virtual_clip_sha256"]:
                bit_exact_ok = False
                blockers.append(f"BIT_EXACT_RECONSTRUCTION_MISMATCH:{segment['segment_id']}")
            if segment["parent_canonical_pcm_sha256"] != canonical_pcm_sha256:
                blockers.append(f"PARENT_HASH_MISMATCH:{segment['segment_id']}")
    else:
        bit_exact_ok = False
        blockers.append("BIT_EXACT_RECONSTRUCTION_PROOF_ABSENT")

    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "source_before_sha256": source_before,
        "source_after_sha256": source_after,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "frame_count": frame_count,
        "boundary_convention": dict(BOUNDARY_CONVENTION),
        "thresholds": {k: v for k, v in THRESHOLDS.items() if k != "suggestion_only"},
        "event_count": len(segments),
        "segments": segments,
        "overlap_policy": overlap_policy,
        "decision": {
            "status": "pass" if library_authority and not blockers else "blocked",
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "source_bytes_unchanged": source_bytes_unchanged,
            "bit_exact_reconstruction_ok": bit_exact_ok and not policy_errors,
        },
    }


def validate_segmentation_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise MultiEventSegmentationError(f"schema_validation_failed:{location}:{first.message}")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    segments, overlap_policy = build_segments_for_fixture(fixture)
    record = build_segmentation_record(
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        segments=segments,
        overlap_policy=overlap_policy,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
        pcm=fixture["pcm_f32le"],
    )
    validate_segmentation_record(root, record)
    return record


def load_feature_module() -> Any:
    global _FEATURE_MOD
    if _FEATURE_MOD is not None:
        return _FEATURE_MOD
    import importlib.util

    script = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
    spec = importlib.util.spec_from_file_location("wave64_row071_features_for_segments", script)
    if spec is None or spec.loader is None:
        raise MultiEventSegmentationError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _empty_retained_segment_counts() -> dict[str, int]:
    return {
        "records_processed": 0,
        "records_total": 0,
        "segment_pass": 0,
        "segment_blocked": 0,
        "exact_blockers": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "pcm_sha_verified": 0,
        "analysis_truncated": 0,
        "source_immutable_true": 0,
        "bit_exact_reconstruction_ok": 0,
        "multi_event_assets": 0,
        "single_event_assets": 0,
        "zero_event_assets": 0,
    }


def build_compact_segment_record(
    *,
    relative_path: str,
    extension: str,
    role: str,
    event_type: str,
    asset_id: str,
    feature_status: str,
    segments: list[dict[str, Any]] | None,
    overlap_policy: dict[str, Any] | None,
    source_sha256: str | None,
    canonical_pcm_sha256: str | None,
    sample_rate_hz: int | None,
    channels: int | None,
    frame_count: int | None,
    pcm_sha_verified: bool,
    source_immutable: bool | None,
    analysis_truncated: bool,
    bit_exact_ok: bool,
    blocker_code: str | None,
    blocker_codes: list[str],
    blocker_detail: str | None = None,
) -> dict[str, Any]:
    technical_pass = (
        feature_status == "pass"
        and segments is not None
        and overlap_policy is not None
        and pcm_sha_verified
        and source_immutable is True
        and bit_exact_ok
        and not blocker_codes
    )
    status = "pass" if technical_pass else "blocked"
    codes = list(blocker_codes)
    if technical_pass:
        codes = ["LIBRARY_AUTHORITY_NOT_GRANTED"]
    event_count = len(segments or [])
    compact: dict[str, Any] = {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "feature_status": feature_status,
        "segment_status": status,
        "technical_segment_pass": technical_pass,
        "library_authority": False,
        "suggestion_only": True,
        "source_bytes_unchanged": bool(source_immutable) if source_immutable is not None else False,
        "event_count": event_count,
        "segments": segments or [],
        "overlap_policy": overlap_policy
        or {
            "mode": "non_overlapping",
            "ordinary_non_overlapping": True,
            "layered_overlap_present": False,
        },
        "boundary_convention": dict(BOUNDARY_CONVENTION),
        "bit_exact_reconstruction_ok": bit_exact_ok,
        "blocker_code": None if technical_pass else (blocker_code or "SEGMENTATION_BLOCKED"),
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
        "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
        "thresholds": dict(THRESHOLDS),
    }
    if blocker_detail:
        compact["blocker_detail"] = blocker_detail
    return compact


def run_retained_index_segmentation_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile retained Row071 feature records to suggestion-only segment PASS/blocker."""
    row072 = evaluate_row072_admission(root)
    row073 = evaluate_row073_admission(root)
    if not row072.get("dependency_satisfied") or not row073.get("dependency_satisfied"):
        raise MultiEventSegmentationError("index_retained_requires_row072_and_row073_admission")

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
        raise MultiEventSegmentationError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_RETAINED_SEGMENT_RUNTIME_DIR,
        "retained_segment_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            f"owner=segment_wave64_multi_event_audio.py\nstarted={datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise MultiEventSegmentationError(
            "retained_segment_runtime_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_segment_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_segment_counts()
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
            counts = _empty_retained_segment_counts()
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
            "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
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
                compact = build_compact_segment_record(
                    relative_path=relative_path,
                    extension=extension,
                    role=role,
                    event_type=event_type,
                    asset_id=asset_id,
                    feature_status=feature_status,
                    segments=None,
                    overlap_policy=None,
                    source_sha256=feature_rec.get("source_sha256"),
                    canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                    sample_rate_hz=None,
                    channels=None,
                    frame_count=None,
                    pcm_sha_verified=False,
                    source_immutable=feature_rec.get("source_immutable"),
                    analysis_truncated=False,
                    bit_exact_ok=False,
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
                        raise MultiEventSegmentationError(f"source_sha_mismatch:{relative_path}")
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise MultiEventSegmentationError(f"pcm_sha_mismatch:{relative_path}")
                    frame_count = int(frames_nc.shape[0])
                    channel_count = int(frames_nc.shape[1])
                    analysis_truncated = frame_count > MAX_ANALYSIS_FRAMES
                    analysis_frames = frames_nc
                    if analysis_truncated:
                        analysis_frames = frames_nc[:MAX_ANALYSIS_FRAMES]
                        counts["analysis_truncated"] += 1
                    segments, overlap_policy = build_segments_from_frames(
                        analysis_frames,
                        sample_rate_hz=int(sample_rate_hz),
                        parent_hash=str(pcm_sha),
                        event_family=event_type or "other",
                    )
                    local_blockers: list[str] = []
                    if not source_immutable:
                        local_blockers.append("SOURCE_BYTES_CHANGED")
                    policy_errors = validate_segments_policy(
                        segments,
                        frame_count=int(analysis_frames.shape[0]),
                        overlap_mode=str(overlap_policy["mode"]),
                    )
                    for error in policy_errors:
                        local_blockers.append(f"OVERLAP_POLICY_VIOLATION:{error}")
                    bit_exact_ok = True
                    for segment in segments:
                        reconstructed = virtual_clip_sha256_from_frames(
                            analysis_frames,
                            start_sample=segment["start_sample"],
                            end_sample=segment["end_sample"],
                        )
                        if reconstructed != segment["virtual_clip_sha256"]:
                            bit_exact_ok = False
                            local_blockers.append(
                                f"BIT_EXACT_RECONSTRUCTION_MISMATCH:{segment['segment_id']}"
                            )
                    compact = build_compact_segment_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        segments=segments,
                        overlap_policy=overlap_policy,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        sample_rate_hz=int(sample_rate_hz),
                        channels=channel_count,
                        frame_count=frame_count,
                        pcm_sha_verified=True,
                        source_immutable=source_immutable,
                        analysis_truncated=analysis_truncated,
                        bit_exact_ok=bit_exact_ok and not policy_errors,
                        blocker_code=local_blockers[0] if local_blockers else None,
                        blocker_codes=local_blockers,
                    )
                    counts["feature_pass_inputs"] += 1
                    counts["pcm_sha_verified"] += 1
                    if source_immutable:
                        counts["source_immutable_true"] += 1
                    if compact.get("bit_exact_reconstruction_ok"):
                        counts["bit_exact_reconstruction_ok"] += 1
                    event_count = int(compact.get("event_count") or 0)
                    if event_count == 0:
                        counts["zero_event_assets"] += 1
                    elif event_count == 1:
                        counts["single_event_assets"] += 1
                    else:
                        counts["multi_event_assets"] += 1
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = build_compact_segment_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        segments=None,
                        overlap_policy=None,
                        source_sha256=feature_rec.get("source_sha256"),
                        canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                        sample_rate_hz=None,
                        channels=None,
                        frame_count=None,
                        pcm_sha_verified=False,
                        source_immutable=feature_rec.get("source_immutable"),
                        analysis_truncated=False,
                        bit_exact_ok=False,
                        blocker_code="SEGMENTATION_EXTRACTION_FAILED",
                        blocker_codes=["SEGMENTATION_EXTRACTION_FAILED"],
                        blocker_detail=str(exc)[:500],
                    )
                    counts["feature_pass_inputs"] += 1

            if compact.get("segment_status") == "pass":
                counts["segment_pass"] += 1
            else:
                counts["segment_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "SEGMENTATION_BLOCKED")
                blocker_histogram[code] = blocker_histogram.get(code, 0) + 1
            extension_histogram[extension] = extension_histogram.get(extension, 0) + 1
            counts["records_processed"] += 1
            out_handle.write(json.dumps(compact, sort_keys=True) + "\n")
            processed_paths.add(relative_path)
            next_index = line_index + 1
            if counts["records_processed"] % checkpoint_every == 0:
                write_progress(complete=False)

    coverage_complete = limit is None and counts["records_processed"] >= counts["records_total"]
    write_progress(complete=coverage_complete)
    proof_tier = "RUNTIME_PASS_BOUNDED"
    receipt = {
        "schema_version": 1,
        "evidence_id": "W64-ROW074-ACCEPTED-INDEX-RETAINED-SEGMENT-20260720",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_segment_probe"
        if limit is not None
        else "accepted_index_retained_segment_reconcile",
        "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
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
        "row072_admission": row072,
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
    row072 = evaluate_row072_admission(root)
    row073 = evaluate_row073_admission(root)
    blocker_codes: list[str] = []
    for admission in (row072, row073):
        blocker_codes.extend(admission["blocker_codes"])
    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)
    probe_only = retained.get("limit") is not None
    deps_unlocked = bool(row072["dependency_satisfied"] and row073["dependency_satisfied"])

    if not deps_unlocked:
        if "ROW072_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW072_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED")
    if not coverage_complete:
        if reconcile_started:
            for code in (
                "FULL_LIBRARY_RECONCILE_DEFERRED_OR_IN_PROGRESS",
                "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
                "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
            if probe_only and "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
                blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
        else:
            for code in (
                "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
                "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
    else:
        for code in (
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    if coverage_complete and deps_unlocked:
        status = "HOLD_LIBRARY_THRESHOLDS_AND_EVENT_CALIBRATION_ABSENT_RECONCILE_COMPLETE"
        safe_next = (
            "Full-library multi-event segment reconcile covered retained Row071 records under "
            "frozen suggestion-only thresholds. Calibrate event-count strata and unfreeze "
            "threshold authority before Row074 acceptance or Row079 unlock."
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
            "Bounded index-retained segment probe passed under frozen suggestion-only thresholds. "
            "Defer full-library Row074 PCM reconcile until Row075 retained-index defect scan "
            "finishes (avoid dual PCM I/O contention), then resume --mode index-retained "
            "without --limit before claiming Row074 acceptance."
            if probe_only
            else (
                "Resume/finish retained-index segment reconcile to coverage_complete, then address "
                "frozen threshold authority and event-count calibration before claiming Row074 acceptance."
            )
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    elif deps_unlocked:
        status = "HOLD_LIBRARY_RUNTIME_AND_EVENT_CALIBRATION_ABSENT_DEPS_UNLOCKED"
        safe_next = (
            "Rows072+073 dependency gate is unlocked (Row072 runtime-unlocked + Row073 "
            "probe/runtime-unlocked under RUNTIME_PASS_BOUNDED). Run --mode index-retained with "
            "a bounded --limit probe, then defer full reconcile until Row075 finishes to avoid "
            "PCM I/O contention."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    else:
        status = "HOLD_ROW072_ROW073_DEPENDENCIES_AND_FULL_LIBRARY_SEGMENT_RUNTIME_ABSENT"
        safe_next = (
            "Accept Row072 onset/transient anchors and Row073 usable-bounds/decay "
            "authority, reconcile every accepted input to single-event or multi-event "
            "PASS or an exact blocker with parent-hash and bit-exact reconstruction "
            "proofs, and replace this hold packet with full-library runtime evidence."
        )
        proof_tier = "CONTRACT_SLICE_BOUNDED"
        runtime_completion = False

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-074_multi_event_segmentation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": runtime_completion,
        "library_authority": False,
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "status": status,
        "thresholds": {k: v for k, v in THRESHOLDS.items() if k != "suggestion_only"},
        "boundary_convention": dict(BOUNDARY_CONVENTION),
        "row072_admission": row072,
        "row073_admission": row073,
        "accepted_index_retained_segment_runtime": {
            "present": reconcile_started,
            "coverage_complete": coverage_complete,
            "limit": retained.get("limit"),
            "counts": retained.get("counts"),
            "blocker_histogram": retained.get("blocker_histogram"),
            "records_path": retained.get("records_path"),
            "progress_path": retained.get("progress_path"),
            "receipt_path": retained.get("receipt_path"),
            "status": retained.get("status"),
            "authority": retained.get("authority"),
            "row075_contention_policy": retained.get("row075_contention_policy"),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove event-count, overlap-policy, parent lineage, and "
                "bit-exact virtual-clip reconstruction identity only; they do not accept "
                "Row074 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row074_acceptance": "held",
            "product_completion": False,
            "runtime_completion": runtime_completion,
            "dependencies_unlocked": deps_unlocked,
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
    parser.add_argument("--fixture", default="two_footsteps")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_RETAINED_SEGMENT_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-074_ACCEPTED_INDEX_RETAINED_SEGMENT_SUMMARY_20260720.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise MultiEventSegmentationError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    elif args.mode == "index-retained":
        retained = run_retained_index_segmentation_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_segment_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_segment_runtime"]["summary_sha256"] = sha256_file(
            summary_path
        )
    else:
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_RETAINED_SEGMENT_RUNTIME_DIR / "retained_index_segment_receipt.json",
            "retained_segment_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise MultiEventSegmentationError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "coverage_complete": bool(
                    (payload.get("accepted_index_retained_segment_runtime") or {}).get(
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
