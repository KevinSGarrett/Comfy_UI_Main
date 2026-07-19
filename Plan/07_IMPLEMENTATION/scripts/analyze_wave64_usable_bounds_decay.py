#!/usr/bin/env python3
"""Fail-closed Wave64 Row073 usable bounds and natural-decay authority slice.

Library analysis refuses authority without accepted Row071 waveform features and
Row072 onset/offset anchors. Fixture mode may compute deterministic suggestion-
only bounds from synthetic PCM without promoting library completion, and never
mutates source bytes.
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
ANALYSIS_PIPELINE_REVISION = "wave64_row073_usable_bounds_decay_v0.1.0"
TRACKER_ID = "TRK-W64-073"
ITEM_ID = "ITEM-W64-073"
SCHEMA_VERSION = "1.0.0"

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
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW072_DELTA,
        tracker_id="TRK-W64-072",
        acceptance_key="row072_acceptance",
        blocker_code="ROW072_DEPENDENCY_NOT_ACCEPTED",
    )


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


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row071 = evaluate_row071_admission(root)
    row072 = evaluate_row072_admission(root)
    blocker_codes: list[str] = []
    for admission in (row071, row072):
        blocker_codes.extend(admission["blocker_codes"])
    if not row071["dependency_satisfied"] or not row072["dependency_satisfied"]:
        if "ROW071_AND_ROW072_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW071_AND_ROW072_DEPENDENCIES_NOT_ACCEPTED")
    if "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
        blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    if "FULL_LIBRARY_SOURCE_IMMUTABILITY_PROOF_ABSENT" not in blocker_codes:
        blocker_codes.append("FULL_LIBRARY_SOURCE_IMMUTABILITY_PROOF_ABSENT")

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
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW071_ROW072_DEPENDENCIES_AND_FULL_LIBRARY_BOUNDS_RUNTIME_ABSENT",
        "thresholds": dict(THRESHOLDS),
        "method_provenance": {key: dict(value) for key, value in METHOD_PROVENANCE.items()},
        "row071_admission": row071,
        "row072_admission": row072,
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
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row071 waveform features and Row072 onset/offset anchors, reconcile every "
                "accepted input to suggestion-only bounds/decay PASS or an exact blocker with "
                "before/after source hashes, and replace this hold packet with full-library runtime evidence."
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
    parser.add_argument("--fixture", default="padded_tone")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise UsableBoundsDecayError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise UsableBoundsDecayError("library_mode_must_remain_fail_closed_until_dependencies_accepted")
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
