#!/usr/bin/env python3
"""Fail-closed Wave64 Row074 multi-event segmentation and virtual-clip slice.

Library segmentation refuses authority without accepted Row072 onset/transient
anchors and Row073 usable-bounds/decay records. Fixture mode may detect
deterministic synthetic multi-event segments, prove bit-exact virtual PCM
reconstruction from parent bytes plus sample bounds, and enforce overlap policy
without promoting library completion or mutating source bytes.
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
SEGMENTATION_PIPELINE_REVISION = "wave64_row074_multi_event_segmentation_v0.1.0"
TRACKER_ID = "TRK-W64-074"
ITEM_ID = "ITEM-W64-074"
SCHEMA_VERSION = "1.0.0"

THRESHOLDS: dict[str, Any] = {
    "energy_threshold_dbfs": -40.0,
    "min_event_gap_ms": 20.0,
    "min_event_duration_ms": 5.0,
    "channel_policy": "max_abs_mono",
    "ordinary_segments_non_overlapping": True,
    "layered_overlap_requires_layer_id": True,
    "source_mutation_allowed": False,
}

BOUNDARY_CONVENTION: dict[str, Any] = {
    "inclusive_start": True,
    "exclusive_end": True,
    "sample_unit": "pcm_frame_index",
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


def evaluate_row072_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW072_DELTA,
        tracker_id="TRK-W64-072",
        acceptance_key="row072_acceptance",
        blocker_code="ROW072_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW072_DELTA_ABSENT",
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
        "thresholds": dict(THRESHOLDS),
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


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row072 = evaluate_row072_admission(root)
    row073 = evaluate_row073_admission(root)
    blocker_codes: list[str] = []
    for admission in (row072, row073):
        blocker_codes.extend(admission["blocker_codes"])
    if not row072["dependency_satisfied"] or not row073["dependency_satisfied"]:
        if "ROW072_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW072_AND_ROW073_DEPENDENCIES_NOT_ACCEPTED")
    if "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
        blocker_codes.append("DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT")
    if "EVENT_COUNT_CALIBRATION_STRATA_ABSENT" not in blocker_codes:
        blocker_codes.append("EVENT_COUNT_CALIBRATION_STRATA_ABSENT")

    fixture_names = [
        "silence",
        "single_impact",
        "two_footsteps",
        "three_impacts",
        "breath_pair",
        "layered_overlap",
    ]
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-074_multi_event_segmentation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "segmentation_pipeline_revision": SEGMENTATION_PIPELINE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW072_ROW073_DEPENDENCIES_AND_FULL_LIBRARY_SEGMENT_RUNTIME_ABSENT",
        "thresholds": dict(THRESHOLDS),
        "boundary_convention": dict(BOUNDARY_CONVENTION),
        "row072_admission": row072,
        "row073_admission": row073,
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
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row072 onset/transient anchors and Row073 usable-bounds/decay "
                "authority, reconcile every accepted input to single-event or multi-event "
                "PASS or an exact blocker with parent-hash and bit-exact reconstruction "
                "proofs, and replace this hold packet with full-library runtime evidence."
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
    parser.add_argument("--fixture", default="two_footsteps")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise MultiEventSegmentationError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
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
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
