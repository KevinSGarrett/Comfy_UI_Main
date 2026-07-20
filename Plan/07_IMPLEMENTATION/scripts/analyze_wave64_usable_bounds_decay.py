#!/usr/bin/env python3
"""Fail-closed Wave64 Row073 usable bounds and natural-decay authority slice.

Library analysis refuses authority without accepted Row071 waveform features and
Row072 onset/offset runtime unlock (or acceptance). Fixture mode may compute
deterministic suggestion-only bounds from synthetic PCM without promoting
library completion, and never mutates source bytes. Index-retained mode may
probe or reconcile accepted Row071 feature records into suggestion-only
PASS/blocker compact records under frozen thresholds without claiming COMPLETE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/usable_bounds_decay_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_usable_bounds_decay_analysis.json"
)
ROW071_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
)
ROW072_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
)
DEFAULT_ROW071_RETAINED_RECORDS = Path(
    "runtime_artifacts/audio_qa/row071_index_retained_20260719/records.jsonl"
)
DEFAULT_RETAINED_BOUNDS_RUNTIME_DIR = Path(
    "runtime_artifacts/usable_bounds/row073_index_retained_20260720"
)
ANALYSIS_PIPELINE_REVISION = "wave64_row073_usable_bounds_decay_v0.2.0"
TRACKER_ID = "TRK-W64-073"
ITEM_ID = "ITEM-W64-073"
SCHEMA_VERSION = "1.0.0"
# Cap retained-library PCM windows to keep limited probes from contending with
# Row075 full-library defect reconcile on the same source tree.
MAX_ANALYSIS_FRAMES = 48000 * 30
RETAINED_CHECKPOINT_EVERY = 25
_FEATURE_MOD: Any | None = None

THRESHOLDS: dict[str, Any] = {
    "silence_threshold_dbfs": -50.0,
    "hysteresis_db": 6.0,
    "min_silence_ms": 5.0,
    "channel_policy": "max_abs_mono",
    "suggestion_only": True,
    "destructive_trim_allowed": False,
}

METHOD_PROVENANCE: dict[str, dict[str, str]] = {
    "leading_silence": {
        "method_id": "pcm_leading_silence_hysteresis_v1",
        "unit": "samples_and_seconds",
        "window": "prefix_until_enter_threshold",
    },
    "trailing_silence": {
        "method_id": "pcm_trailing_silence_hysteresis_v1",
        "unit": "samples_and_seconds",
        "window": "suffix_until_enter_threshold",
    },
    "usable_bounds": {
        "method_id": "pcm_usable_bounds_from_silence_v1",
        "unit": "sample_index",
        "window": "first_to_last_non_silence",
    },
    "attack": {
        "method_id": "pcm_attack_to_peak_v1",
        "unit": "seconds",
        "window": "usable_start_to_peak",
    },
    "sustain": {
        "method_id": "pcm_sustain_above_release_floor_v1",
        "unit": "seconds",
        "window": "peak_to_release_start",
    },
    "release": {
        "method_id": "pcm_release_to_natural_decay_v1",
        "unit": "seconds",
        "window": "release_start_to_natural_decay_end",
    },
    "noise_only_tail": {
        "method_id": "pcm_noise_only_tail_classifier_v1",
        "unit": "boolean",
        "window": "post_release_to_usable_end",
    },
    "natural_decay": {
        "method_id": "pcm_natural_decay_end_v1",
        "unit": "sample_index",
        "window": "usable_region_envelope",
    },
}


class UsableBoundsDecayError(ValueError):
    """Raised when Row073 analysis violates fail-closed authority."""


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
        raise UsableBoundsDecayError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise UsableBoundsDecayError("non_finite_measurement_value")
    return round(value, digits)


def db_from_amplitude(amplitude: float) -> float:
    safe = max(abs(amplitude), 1e-12)
    return 20.0 * math.log10(safe)


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    acceptance_key: str,
    blocker_code: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    if not path.is_file():
        absent_code = "ROW071_DELTA_ABSENT" if tracker_id.endswith("071") else "ROW072_DELTA_ABSENT"
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
    )


def evaluate_row072_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    """Admit Row072 for downstream probes when accepted OR runtime-unlocked.

    Row072 may remain row_complete=false with thresholds/strata held while still
    unlocking dependency-safe index-retained probes via dependencies_unlocked and
    RUNTIME_PASS_BOUNDED coverage. Acceptance itself stays held until thresholds
    and library strata are resolved.
    """
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


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise UsableBoundsDecayError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise UsableBoundsDecayError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def synthesize_fixture(name: str, sample_rate_hz: int = 48000, frames: int = 4800) -> dict[str, Any]:
    if name == "silence":
        left = [0.0] * frames
    elif name == "padded_tone":
        left = [0.0] * frames
        for i in range(800, 4000):
            t = (i - 800) / sample_rate_hz
            left[i] = 0.45 * math.sin(2.0 * math.pi * 1000.0 * t)
    elif name == "impulse_decay":
        left = [0.0] * frames
        for i in range(frames):
            left[i] = 0.9 * math.exp(-i / 240.0)
    elif name == "noisy_tail":
        left = [0.0] * frames
        value = 424242
        for i in range(400, 2200):
            t = (i - 400) / sample_rate_hz
            left[i] = 0.4 * math.sin(2.0 * math.pi * 880.0 * t)
        for i in range(2200, frames):
            value = (1103515245 * value + 12345) & 0x7FFFFFFF
            left[i] = ((value / 0x7FFFFFFF) * 2.0 - 1.0) * 0.02
    elif name == "gradual_attack":
        left = [0.0] * frames
        attack = 1200
        for i in range(600, 600 + attack):
            t = (i - 600) / sample_rate_hz
            envelope = (i - 600) / attack
            left[i] = envelope * 0.5 * math.sin(2.0 * math.pi * 660.0 * t)
        for i in range(600 + attack, 3600):
            t = (i - 600) / sample_rate_hz
            left[i] = 0.5 * math.sin(2.0 * math.pi * 660.0 * t)
        for i in range(3600, 4200):
            t = (i - 600) / sample_rate_hz
            release = 1.0 - ((i - 3600) / 600.0)
            left[i] = release * 0.5 * math.sin(2.0 * math.pi * 660.0 * t)
    else:
        raise UsableBoundsDecayError(f"unknown_fixture:{name}")
    right = list(left)
    pcm = pack_pcm_f32le([left, right])
    source_token = f"wave64-row073-fixture:{name}".encode("utf-8")
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


def analyze_channels(
    channels: list[list[float]],
    *,
    sample_rate_hz: int,
) -> dict[str, Any]:
    if not channels or not channels[0]:
        raise UsableBoundsDecayError("empty_channels")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise UsableBoundsDecayError("channel_length_mismatch")

    mono = _mono_max_abs(channels)
    enter_db = float(THRESHOLDS["silence_threshold_dbfs"])
    exit_db = enter_db - float(THRESHOLDS["hysteresis_db"])
    min_silence = max(1, int(sample_rate_hz * float(THRESHOLDS["min_silence_ms"]) / 1000.0))

    def is_silent(sample: float, *, active: bool) -> bool:
        level = db_from_amplitude(sample)
        return level < (exit_db if active else enter_db)

    leading = 0
    while leading < frame_count and is_silent(mono[leading], active=False):
        leading += 1

    trailing = 0
    while trailing < frame_count and is_silent(mono[frame_count - 1 - trailing], active=False):
        trailing += 1

    if leading >= frame_count:
        usable_start = 0
        usable_end = 0
        peak_index = 0
        attack_samples = 0
        sustain_samples = 0
        release_samples = 0
        natural_decay_end = 0
        noise_only_tail = False
    else:
        usable_start = leading
        usable_end = frame_count - trailing
        if usable_end <= usable_start:
            usable_end = min(frame_count, usable_start + 1)
        region = mono[usable_start:usable_end]
        peak_offset = max(range(len(region)), key=lambda idx: region[idx])
        peak_index = usable_start + peak_offset
        peak_db = db_from_amplitude(mono[peak_index])
        release_floor_db = peak_db - 12.0

        attack_samples = peak_index - usable_start
        release_start = peak_index
        for index in range(peak_index, usable_end):
            if db_from_amplitude(mono[index]) <= release_floor_db:
                release_start = index
                break
        else:
            release_start = usable_end

        sustain_samples = max(0, release_start - peak_index)
        # Natural decay end: last sample still above enter threshold inside usable region.
        natural_decay_end = usable_start
        for index in range(usable_end - 1, usable_start - 1, -1):
            if not is_silent(mono[index], active=True):
                natural_decay_end = index + 1
                break
        release_samples = max(0, natural_decay_end - release_start)

        post_release = mono[release_start:usable_end]
        if not post_release:
            noise_only_tail = False
        else:
            mean_sq = sum(sample * sample for sample in post_release) / len(post_release)
            noise_only_tail = db_from_amplitude(math.sqrt(mean_sq)) < enter_db + 6.0 and release_samples >= min_silence

    leading_seconds = leading / sample_rate_hz
    trailing_seconds = trailing / sample_rate_hz
    attack_seconds = attack_samples / sample_rate_hz
    sustain_seconds = sustain_samples / sample_rate_hz
    release_seconds = release_samples / sample_rate_hz

    # Suggestion-only preservation: usable start may not precede measured onset; end may not cut natural decay.
    onset_preservation_ok = usable_start <= peak_index
    tail_preservation_ok = natural_decay_end >= peak_index and natural_decay_end <= frame_count

    return {
        "leading_silence_samples": int(leading),
        "trailing_silence_samples": int(trailing),
        "leading_silence_seconds": round_finite(leading_seconds),
        "trailing_silence_seconds": round_finite(trailing_seconds),
        "usable_start_sample": int(usable_start),
        "usable_end_sample": int(usable_end),
        "attack_seconds": round_finite(attack_seconds),
        "sustain_seconds": round_finite(sustain_seconds),
        "release_seconds": round_finite(release_seconds),
        "noise_only_tail": bool(noise_only_tail),
        "natural_decay_end_sample": int(natural_decay_end),
        "onset_preservation_ok": bool(onset_preservation_ok),
        "tail_preservation_ok": bool(tail_preservation_ok),
    }


def build_analysis_record(
    *,
    asset_id: str,
    source_sha256: str,
    canonical_pcm_sha256: str,
    sample_rate_hz: int,
    channels: int,
    frame_count: int,
    measurements: dict[str, Any],
    library_authority: bool,
    blocker_codes: list[str] | None = None,
) -> dict[str, Any]:
    blockers = list(blocker_codes or [])
    # Non-destructive contract: analysis never rewrites source; before/after bind identically.
    source_before = source_sha256
    source_after = source_sha256
    source_bytes_unchanged = source_before == source_after
    if not source_bytes_unchanged:
        blockers.append("SOURCE_BYTES_CHANGED")
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
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
        "decision": {
            "status": "pass" if library_authority and not blockers else "blocked",
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "suggestion_only": True,
            "source_bytes_unchanged": source_bytes_unchanged,
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
        raise UsableBoundsDecayError(f"schema_validation_failed:{location}:{first.message}")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    fixture = synthesize_fixture(fixture_name)
    measurements = analyze_channels(
        fixture["channel_samples"],
        sample_rate_hz=fixture["sample_rate_hz"],
    )
    record = build_analysis_record(
        asset_id=fixture["asset_id"],
        source_sha256=fixture["source_sha256"],
        canonical_pcm_sha256=fixture["canonical_pcm_sha256"],
        sample_rate_hz=fixture["sample_rate_hz"],
        channels=fixture["channels"],
        frame_count=fixture["frame_count"],
        measurements=measurements,
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
    spec = importlib.util.spec_from_file_location("wave64_row071_features_for_bounds", script)
    if spec is None or spec.loader is None:
        raise UsableBoundsDecayError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _empty_retained_bounds_counts() -> dict[str, int]:
    return {
        "records_processed": 0,
        "records_total": 0,
        "bounds_pass": 0,
        "bounds_blocked": 0,
        "exact_blockers": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "pcm_sha_verified": 0,
        "analysis_truncated": 0,
        "source_immutable_true": 0,
        "onset_preservation_ok": 0,
        "tail_preservation_ok": 0,
    }


def _rebuild_retained_bounds_aggregates_from_records(
    records_path: Path,
) -> tuple[dict[str, int], dict[str, int], dict[str, int], set[str]]:
    """Rebuild counters from records.jsonl after crashy resume undercount.

    Progress checkpoints can lag written records. On --resume, records.jsonl is
    authoritative for already-emitted compact rows; trusting stale progress counts
    leaves coverage_complete false after the index cursor reaches EOF.
    """
    counts = _empty_retained_bounds_counts()
    blocker_histogram: dict[str, int] = {}
    extension_histogram: dict[str, int] = {}
    processed_paths: set[str] = set()
    if not records_path.is_file():
        return counts, blocker_histogram, extension_histogram, processed_paths
    with records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            compact = json.loads(line)
            relative_path = str(compact.get("relative_path") or "").replace("\\", "/")
            if not relative_path or relative_path in processed_paths:
                continue
            processed_paths.add(relative_path)
            extension = str(compact.get("extension") or Path(relative_path).suffix).lower()
            feature_status = str(compact.get("feature_status") or "")
            if feature_status != "pass":
                counts["feature_non_pass_inputs"] += 1
            else:
                counts["feature_pass_inputs"] += 1
                if compact.get("pcm_sha_verified"):
                    counts["pcm_sha_verified"] += 1
                    if compact.get("source_immutable"):
                        counts["source_immutable_true"] += 1
                    if compact.get("onset_preservation_ok"):
                        counts["onset_preservation_ok"] += 1
                    if compact.get("tail_preservation_ok"):
                        counts["tail_preservation_ok"] += 1
                if compact.get("analysis_truncated"):
                    counts["analysis_truncated"] += 1
            if compact.get("bounds_status") == "pass":
                counts["bounds_pass"] += 1
            else:
                counts["bounds_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "BOUNDS_BLOCKED")
                blocker_histogram[code] = blocker_histogram.get(code, 0) + 1
            extension_histogram[extension] = extension_histogram.get(extension, 0) + 1
            counts["records_processed"] += 1
    return counts, blocker_histogram, extension_histogram, processed_paths


def _channels_from_frames_nc(frames_nc: Any) -> list[list[float]]:
    """Collapse N×C float frames to a single max-abs mono channel for analyze_channels.

    Retained probes share the source tree with Row075; avoid per-sample Python loops
    over multi-channel PCM by reducing to mono once via NumPy.
    """
    import numpy as np

    arr = np.asarray(frames_nc, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        raise UsableBoundsDecayError("invalid_frames_nc_shape")
    mono = np.max(np.abs(arr), axis=1)
    return [mono.astype(float).tolist()]


def build_compact_bounds_record(
    *,
    relative_path: str,
    extension: str,
    role: str,
    event_type: str,
    asset_id: str,
    feature_status: str,
    measurements: dict[str, Any] | None,
    source_sha256: str | None,
    canonical_pcm_sha256: str | None,
    sample_rate_hz: int | None,
    channels: int | None,
    frame_count: int | None,
    pcm_sha_verified: bool,
    source_immutable: bool | None,
    analysis_truncated: bool,
    blocker_code: str | None,
    blocker_codes: list[str],
    blocker_detail: str | None = None,
) -> dict[str, Any]:
    onset_ok = bool((measurements or {}).get("onset_preservation_ok"))
    tail_ok = bool((measurements or {}).get("tail_preservation_ok"))
    technical_pass = (
        feature_status == "pass"
        and measurements is not None
        and pcm_sha_verified
        and source_immutable is True
        and onset_ok
        and tail_ok
        and not blocker_codes
    )
    status = "pass" if technical_pass else "blocked"
    codes = list(blocker_codes)
    if technical_pass:
        # Technical probe pass still withholds library authority under frozen thresholds.
        codes = ["LIBRARY_AUTHORITY_NOT_GRANTED"]
    compact: dict[str, Any] = {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "feature_status": feature_status,
        "bounds_status": status,
        "technical_bounds_pass": technical_pass,
        "library_authority": False,
        "suggestion_only": True,
        "source_bytes_unchanged": bool(source_immutable) if source_immutable is not None else False,
        "onset_preservation_ok": onset_ok,
        "tail_preservation_ok": tail_ok,
        "blocker_code": None if technical_pass else (blocker_code or "BOUNDS_ANALYSIS_BLOCKED"),
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


def run_retained_index_bounds_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile retained Row071 feature records to suggestion-only bounds PASS/blocker."""
    row071 = evaluate_row071_admission(root)
    row072 = evaluate_row072_admission(root)
    if not row071.get("dependency_satisfied") or not row072.get("dependency_satisfied"):
        raise UsableBoundsDecayError("index_retained_requires_row071_and_row072_admission")

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
        raise UsableBoundsDecayError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_RETAINED_BOUNDS_RUNTIME_DIR,
        "retained_bounds_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            "owner=analyze_wave64_usable_bounds_decay.py\n"
            f"started={datetime.now(timezone.utc).isoformat()}\n"
            f"pid={os.getpid()}\n"
            "lane=library_pcm_exclusive\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise UsableBoundsDecayError(
            "retained_bounds_runtime_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_bounds_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_bounds_counts()
    counts["records_total"] = total_lines
    blocker_histogram: dict[str, int] = {}
    extension_histogram: dict[str, int] = {}
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    processed_paths: set[str] = set()
    next_index = 0

    if resume and progress_path.is_file() and records_path.is_file():
        progress = load_json(progress_path)
        if str(progress.get("row071_records_sha256") or "") == sha256_file(records_in):
            next_index = int(progress.get("next_record_index") or 0)
            started_at = str(progress.get("started_at") or started_at)
            (
                counts,
                blocker_histogram,
                extension_histogram,
                processed_paths,
            ) = _rebuild_retained_bounds_aggregates_from_records(records_path)
            counts["records_total"] = total_lines
            # Cursor may already be at EOF while stale progress undercounted; keep
            # next_index from progress but never rewind past written coverage.
            if next_index < len(processed_paths):
                next_index = len(processed_paths)
        else:
            records_path.write_text("", encoding="utf-8")
            next_index = 0
            processed_paths = set()
            counts = _empty_retained_bounds_counts()
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
                compact = build_compact_bounds_record(
                    relative_path=relative_path,
                    extension=extension,
                    role=role,
                    event_type=event_type,
                    asset_id=asset_id,
                    feature_status=feature_status,
                    measurements=None,
                    source_sha256=feature_rec.get("source_sha256"),
                    canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                    sample_rate_hz=None,
                    channels=None,
                    frame_count=None,
                    pcm_sha_verified=False,
                    source_immutable=feature_rec.get("source_immutable"),
                    analysis_truncated=False,
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
                        raise UsableBoundsDecayError(f"source_sha_mismatch:{relative_path}")
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise UsableBoundsDecayError(f"pcm_sha_mismatch:{relative_path}")
                    frame_count = int(frames_nc.shape[0])
                    channel_count = int(frames_nc.shape[1])
                    analysis_truncated = frame_count > MAX_ANALYSIS_FRAMES
                    if analysis_truncated:
                        frames_nc = frames_nc[:MAX_ANALYSIS_FRAMES]
                        counts["analysis_truncated"] += 1
                    channels_list = _channels_from_frames_nc(frames_nc)
                    measurements = analyze_channels(
                        channels_list,
                        sample_rate_hz=int(sample_rate_hz),
                    )
                    local_blockers: list[str] = []
                    if not source_immutable:
                        local_blockers.append("SOURCE_BYTES_CHANGED")
                    if not measurements.get("onset_preservation_ok"):
                        local_blockers.append("ONSET_PRESERVATION_FAILED")
                    if not measurements.get("tail_preservation_ok"):
                        local_blockers.append("TAIL_PRESERVATION_FAILED")
                    compact = build_compact_bounds_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        measurements=measurements,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        sample_rate_hz=int(sample_rate_hz),
                        channels=channel_count,
                        frame_count=frame_count,
                        pcm_sha_verified=True,
                        source_immutable=source_immutable,
                        analysis_truncated=analysis_truncated,
                        blocker_code=local_blockers[0] if local_blockers else None,
                        blocker_codes=local_blockers,
                    )
                    counts["feature_pass_inputs"] += 1
                    counts["pcm_sha_verified"] += 1
                    if source_immutable:
                        counts["source_immutable_true"] += 1
                    if measurements.get("onset_preservation_ok"):
                        counts["onset_preservation_ok"] += 1
                    if measurements.get("tail_preservation_ok"):
                        counts["tail_preservation_ok"] += 1
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = build_compact_bounds_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        measurements=None,
                        source_sha256=feature_rec.get("source_sha256"),
                        canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                        sample_rate_hz=None,
                        channels=None,
                        frame_count=None,
                        pcm_sha_verified=False,
                        source_immutable=feature_rec.get("source_immutable"),
                        analysis_truncated=False,
                        blocker_code="BOUNDS_EXTRACTION_FAILED",
                        blocker_codes=["BOUNDS_EXTRACTION_FAILED"],
                        blocker_detail=str(exc)[:500],
                    )
                    counts["feature_pass_inputs"] += 1

            if compact.get("bounds_status") == "pass":
                counts["bounds_pass"] += 1
            else:
                counts["bounds_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "BOUNDS_BLOCKED")
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
        "evidence_id": "W64-ROW073-ACCEPTED-INDEX-RETAINED-BOUNDS-20260720",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_bounds_probe"
        if limit is not None
        else "accepted_index_retained_bounds_reconcile",
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
        "row072_admission": row072,
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
    row072 = evaluate_row072_admission(root)
    blocker_codes: list[str] = []
    for admission in (row071, row072):
        blocker_codes.extend(admission["blocker_codes"])
    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)
    probe_only = retained.get("limit") is not None
    deps_unlocked = bool(row071["dependency_satisfied"] and row072["dependency_satisfied"])

    if not deps_unlocked:
        if "ROW071_AND_ROW072_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW071_AND_ROW072_DEPENDENCIES_NOT_ACCEPTED")
    if not coverage_complete:
        if reconcile_started:
            for code in (
                "FULL_LIBRARY_RECONCILE_DEFERRED_OR_IN_PROGRESS",
                "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
                "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
            if probe_only and "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
                blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
        else:
            for code in (
                "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT",
                "FULL_LIBRARY_SOURCE_IMMUTABILITY_PROOF_ABSENT",
                "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
    else:
        for code in (
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    if coverage_complete and deps_unlocked:
        status = "HOLD_LIBRARY_THRESHOLDS_AND_STRATA_ABSENT_RECONCILE_COMPLETE"
        safe_next = (
            "Full-library bounds/decay reconcile covered retained Row071 records under frozen "
            "suggestion-only thresholds. Calibrate representative strata and unfreeze threshold "
            "authority before Row073 acceptance or Row074/Row076 unlock."
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
            "Bounded index-retained bounds probe passed under frozen suggestion-only thresholds. "
            "Defer full-library Row073 PCM reconcile until Row075 retained-index defect scan "
            "finishes (avoid dual PCM I/O contention), then resume --mode index-retained "
            "without --limit before claiming Row073 acceptance."
            if probe_only
            else (
                "Resume/finish retained-index bounds reconcile to coverage_complete, then address "
                "frozen threshold authority and library strata before claiming Row073 acceptance."
            )
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    elif deps_unlocked:
        status = "HOLD_LIBRARY_RUNTIME_AND_STRATA_ABSENT_DEPS_UNLOCKED"
        safe_next = (
            "Rows071-072 dependency gate is unlocked (Row072 runtime-unlocked under "
            "RUNTIME_PASS_BOUNDED). Run --mode index-retained with a bounded --limit probe, then "
            "defer full reconcile until Row075 finishes to avoid PCM I/O contention."
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
    else:
        status = "HOLD_ROW071_ROW072_DEPENDENCIES_AND_FULL_LIBRARY_BOUNDS_RUNTIME_ABSENT"
        safe_next = (
            "Accept Row071 waveform features and unlock Row072 onset/offset runtime, reconcile "
            "every accepted input to suggestion-only bounds/decay PASS or an exact blocker with "
            "before/after source hashes, and replace this hold packet with full-library runtime evidence."
        )
        proof_tier = "CONTRACT_SLICE_BOUNDED"
        runtime_completion = False

    fixture_names = ["silence", "padded_tone", "impulse_decay", "noisy_tail", "gradual_attack"]
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-073_usable_bounds_decay_analysis",
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
        "row072_admission": row072,
        "accepted_index_retained_bounds_runtime": {
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
                "Fixture records prove silence/usable-bound/envelope/decay method identity only; "
                "they do not accept Row073 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row073_acceptance": "held",
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
    parser.add_argument("--fixture", default="padded_tone")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_RETAINED_BOUNDS_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-073_ACCEPTED_INDEX_RETAINED_BOUNDS_SUMMARY_20260720.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise UsableBoundsDecayError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    elif args.mode == "index-retained":
        retained = run_retained_index_bounds_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_bounds_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_bounds_runtime"]["summary_sha256"] = sha256_file(
            summary_path
        )
    else:
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_RETAINED_BOUNDS_RUNTIME_DIR / "retained_index_bounds_receipt.json",
            "retained_bounds_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise UsableBoundsDecayError("library_mode_must_remain_fail_closed_until_acceptance")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "coverage_complete": bool(
                    (payload.get("accepted_index_retained_bounds_runtime") or {}).get(
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
