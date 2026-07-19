#!/usr/bin/env python3
"""Fail-closed Row084 canonical video timeline compiler.

Compiles fixture or decoded-frame metadata into a content-addressed timeline
receipt, plus mux-prep scaffold, held-out fixed/VFR round-trip matrix helpers,
and a fixture-backed missing-frame policy matrix (preserve_gap / explicit_gap).
Production completion remains blocked unless dependency, benchmark, mux-replay,
and visual-review authorities are all satisfied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMPILER_REVISION = "row084_missing_frame_policy_matrix_v6"
MATRIX_AUTHORIZED_MISSING_POLICIES = frozenset({"preserve_gap", "explicit_gap"})
RUNTIME_BLOCKED_MISSING_POLICIES = frozenset({"interpolate", "block"})


ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "timeline_id",
    "revision",
    "source_binding",
    "clock_span",
    "frame_rate_mode",
    "frame_table",
    "vfr_segments",
    "cut_epochs",
    "missing_frames",
    "camera_motion_policy",
    "tolerances",
    "dependency_authority",
    "runtime_authority",
    "provenance",
}

ALLOWED_CLOCK_SPAN_FIELDS = {
    "clock_id",
    "timebase_numerator",
    "timebase_denominator",
    "start_pts",
    "end_pts_exclusive",
    "start_frame",
    "end_frame_exclusive",
    "start_sample",
    "end_sample_exclusive",
    "frame_rate_numerator",
    "frame_rate_denominator",
    "sample_rate_hz",
    "rounding_policy",
}

ALLOWED_FRAME_FIELDS = {
    "frame_index",
    "source_pts",
    "duration_pts",
}

ALLOWED_ROUNDING = {"floor_start_ceil_end", "nearest_ties_to_even", "exact_only"}
ALLOWED_FRAME_RATE_MODES = {"fixed", "fractional", "vfr"}
ALLOWED_CAMERA_MOTION = {
    "not_evaluated",
    "distinguish_from_cuts",
    "blocked_until_calibrated",
}
ALLOWED_MISSING_POLICIES = {"preserve_gap", "interpolate", "block", "explicit_gap"}
ALLOWED_CUT_KINDS = {"hard", "match", "dissolve", "unknown"}
SUPPORTED_SAMPLE_RATES = {48000}
SHA256_HEX_CHARS = set("0123456789abcdef")

DEFAULT_TOLERANCES = {
    "max_frame_residual": 0.0,
    "max_sample_residual": 1.0,
    "max_seconds_residual": 1.0 / 48000.0,
}


def _assert_keys_exact(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(unknown)}")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _expect_non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return int(value)


def _expect_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return int(value)


def _expect_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError(f"{label} must be finite")
    return as_float


def _expect_sha256(value: Any, label: str) -> str:
    text = _expect_non_empty_string(value, label)
    if len(text) != 64 or any(ch not in SHA256_HEX_CHARS for ch in text):
        raise ValueError(f"{label} must be a lowercase 64-char sha256")
    return text


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seconds_from_frame(frame_index: int, fps_num: int, fps_den: int) -> float:
    return (frame_index * fps_den) / float(fps_num)


def sample_from_seconds(seconds: float, sample_rate_hz: int, rounding_policy: str) -> int:
    scaled = seconds * sample_rate_hz
    if rounding_policy == "exact_only":
        if abs(scaled - round(scaled)) > 1e-9:
            raise ValueError("exact_only rounding rejected non-integral sample conversion")
        return int(round(scaled))
    if rounding_policy == "nearest_ties_to_even":
        return int(round(scaled))
    if rounding_policy == "floor_start_ceil_end":
        return int(math.floor(scaled))
    raise ValueError(f"unsupported rounding_policy: {rounding_policy}")


def frame_from_seconds(seconds: float, fps_num: int, fps_den: int, rounding_policy: str) -> int:
    scaled = seconds * fps_num / float(fps_den)
    if rounding_policy == "exact_only":
        if abs(scaled - round(scaled)) > 1e-9:
            raise ValueError("exact_only rounding rejected non-integral frame conversion")
        return int(round(scaled))
    if rounding_policy == "nearest_ties_to_even":
        return int(round(scaled))
    if rounding_policy == "floor_start_ceil_end":
        return int(math.floor(scaled + 1e-12))
    raise ValueError(f"unsupported rounding_policy: {rounding_policy}")


def _round_scaled_index(scaled: float, rounding_policy: str, label: str) -> int:
    if rounding_policy == "exact_only":
        if abs(scaled - round(scaled)) > 1e-9:
            raise ValueError(f"exact_only rounding rejected non-integral {label}")
        return int(round(scaled))
    if rounding_policy == "nearest_ties_to_even":
        return int(round(scaled))
    if rounding_policy == "floor_start_ceil_end":
        return int(math.floor(scaled + 1e-12))
    raise ValueError(f"unsupported rounding_policy: {rounding_policy}")


def seconds_from_vfr_frame(frame_index: int, segments: list[dict[str, Any]]) -> float:
    """Accumulate seconds using contiguous VFR segment timebases (tb_num/tb_den seconds per frame)."""
    if not segments:
        raise ValueError("vfr seconds conversion requires a non-empty vfr_segments map")
    seconds = 0.0
    for seg in segments:
        start = seg["start_frame"]
        end = seg["end_frame_exclusive"]
        tb_num = seg["timebase_numerator"]
        tb_den = seg["timebase_denominator"]
        if frame_index < start:
            raise ValueError(f"frame {frame_index} precedes vfr_segments coverage")
        if frame_index >= end:
            seconds += (end - start) * tb_num / float(tb_den)
            continue
        seconds += (frame_index - start) * tb_num / float(tb_den)
        return seconds
    raise ValueError(f"frame {frame_index} outside vfr_segments coverage")


def frame_from_vfr_seconds(
    seconds: float, segments: list[dict[str, Any]], rounding_policy: str
) -> int:
    """Invert VFR segment accumulation for sample/frame round-trip checks."""
    if not segments:
        raise ValueError("vfr frame conversion requires a non-empty vfr_segments map")
    if seconds < -1e-12:
        raise ValueError("vfr seconds must be non-negative")
    cursor = 0.0
    for idx, seg in enumerate(segments):
        start = seg["start_frame"]
        end = seg["end_frame_exclusive"]
        tb_num = seg["timebase_numerator"]
        tb_den = seg["timebase_denominator"]
        frame_duration = tb_num / float(tb_den)
        seg_duration = (end - start) * frame_duration
        is_last = idx == len(segments) - 1
        if seconds + 1e-12 < cursor + seg_duration or is_last:
            local = max(0.0, seconds - cursor)
            offset = _round_scaled_index(local / frame_duration, rounding_policy, "vfr frame conversion")
            frame = start + offset
            if frame < start:
                return start
            if frame >= end:
                return end - 1 if is_last else end
            return frame
        cursor += seg_duration
    raise ValueError("seconds outside vfr_segments coverage")


def validate_clock_span_invariants(span: dict[str, Any], label: str = "clock_span") -> dict[str, Any]:
    _assert_keys_exact(span, ALLOWED_CLOCK_SPAN_FIELDS, label)
    validated = {
        "clock_id": _expect_non_empty_string(span.get("clock_id"), f"{label}.clock_id"),
        "timebase_numerator": _expect_positive_int(span.get("timebase_numerator"), f"{label}.timebase_numerator"),
        "timebase_denominator": _expect_positive_int(
            span.get("timebase_denominator"), f"{label}.timebase_denominator"
        ),
        "start_pts": _expect_non_negative_int(span.get("start_pts"), f"{label}.start_pts"),
        "end_pts_exclusive": _expect_positive_int(span.get("end_pts_exclusive"), f"{label}.end_pts_exclusive"),
        "start_frame": _expect_non_negative_int(span.get("start_frame"), f"{label}.start_frame"),
        "end_frame_exclusive": _expect_positive_int(
            span.get("end_frame_exclusive"), f"{label}.end_frame_exclusive"
        ),
        "start_sample": _expect_non_negative_int(span.get("start_sample"), f"{label}.start_sample"),
        "end_sample_exclusive": _expect_positive_int(
            span.get("end_sample_exclusive"), f"{label}.end_sample_exclusive"
        ),
        "frame_rate_numerator": _expect_positive_int(
            span.get("frame_rate_numerator"), f"{label}.frame_rate_numerator"
        ),
        "frame_rate_denominator": _expect_positive_int(
            span.get("frame_rate_denominator"), f"{label}.frame_rate_denominator"
        ),
        "sample_rate_hz": _expect_positive_int(span.get("sample_rate_hz"), f"{label}.sample_rate_hz"),
        "rounding_policy": _expect_non_empty_string(span.get("rounding_policy"), f"{label}.rounding_policy"),
    }
    if validated["start_pts"] >= validated["end_pts_exclusive"]:
        raise ValueError(f"{label}: start_pts must precede end_pts_exclusive")
    if validated["start_frame"] >= validated["end_frame_exclusive"]:
        raise ValueError(f"{label}: start_frame must precede end_frame_exclusive")
    if validated["start_sample"] >= validated["end_sample_exclusive"]:
        raise ValueError(f"{label}: start_sample must precede end_sample_exclusive")
    if validated["rounding_policy"] not in ALLOWED_ROUNDING:
        raise ValueError(f"{label}.rounding_policy must be one of {sorted(ALLOWED_ROUNDING)}")
    if validated["sample_rate_hz"] not in SUPPORTED_SAMPLE_RATES:
        raise ValueError(
            f"{label}.sample_rate_hz unsupported; allowed={sorted(SUPPORTED_SAMPLE_RATES)}"
        )
    return validated


def _validate_source_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("source_binding must be an object")
    allowed = {
        "video_sha256",
        "stream_index",
        "container_sha256",
        "audio_stream_sha256",
        "audio_stream_index",
    }
    _assert_keys_exact(raw, allowed, "source_binding")
    container = raw.get("container_sha256")
    audio_stream = raw.get("audio_stream_sha256")
    audio_stream_index = raw.get("audio_stream_index")
    binding = {
        "video_sha256": _expect_sha256(raw.get("video_sha256"), "source_binding.video_sha256"),
        "stream_index": _expect_non_negative_int(raw.get("stream_index"), "source_binding.stream_index"),
        "container_sha256": None
        if container is None
        else _expect_sha256(container, "source_binding.container_sha256"),
        "audio_stream_sha256": None
        if audio_stream is None
        else _expect_sha256(audio_stream, "source_binding.audio_stream_sha256"),
        "audio_stream_index": None
        if audio_stream_index is None
        else _expect_non_negative_int(audio_stream_index, "source_binding.audio_stream_index"),
    }
    if binding["audio_stream_sha256"] is None and binding["audio_stream_index"] is not None:
        raise ValueError(
            "source_binding.audio_stream_index requires source_binding.audio_stream_sha256"
        )
    return binding


def _format_audio_stream_binding(source_binding: dict[str, Any]) -> str | None:
    audio_sha = source_binding.get("audio_stream_sha256")
    if audio_sha is None:
        return None
    audio_index = source_binding.get("audio_stream_index")
    if audio_index is None:
        return f"audio_stream_sha256:{audio_sha}"
    return f"audio_stream_sha256:{audio_sha};audio_stream_index:{int(audio_index)}"


def _format_container_binding(source_binding: dict[str, Any]) -> str | None:
    container_sha = source_binding.get("container_sha256")
    if container_sha is None:
        return None
    return f"container_sha256:{container_sha}"


def _format_video_stream_binding(source_binding: dict[str, Any]) -> str:
    video_sha = _expect_sha256(source_binding.get("video_sha256"), "source_binding.video_sha256")
    stream_index = _expect_non_negative_int(source_binding.get("stream_index"), "source_binding.stream_index")
    return f"video_sha256:{video_sha};stream_index:{stream_index}"


def _stable_timeline_plan_sha256(timeline_receipt: dict[str, Any]) -> str:
    """Hash timeline receipt content excluding wall-clock and self-digest fields."""
    if not isinstance(timeline_receipt, dict):
        raise ValueError("timeline_receipt must be an object")
    stable = {
        key: value
        for key, value in timeline_receipt.items()
        if key not in {"created_at", "timeline_sha256"}
    }
    return _canonical_sha256(stable)


def _build_planned_mux_command_envelope(
    *,
    timeline_id: str,
    revision: str,
    timeline_plan_sha256: str,
    source_binding: dict[str, Any],
    mux_prep: dict[str, Any],
) -> dict[str, Any]:
    """Build a fixture-backed dry-run mux command envelope (never executed)."""
    audio_stream_binding = mux_prep.get("audio_stream_binding")
    container_binding = mux_prep.get("container_binding")
    if not isinstance(audio_stream_binding, str) or not audio_stream_binding.strip():
        raise ValueError("planned mux command envelope requires audio_stream_binding")
    if not isinstance(container_binding, str) or not container_binding.strip():
        raise ValueError("planned mux command envelope requires container_binding")
    return {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline_planned_mux_command_envelope",
        "execution_mode": "dry_run_non_executed",
        "command_status": "planned_only",
        "timeline_id": timeline_id,
        "revision": revision,
        "timeline_plan_sha256": timeline_plan_sha256,
        "inputs": {
            "video_stream_binding": _format_video_stream_binding(source_binding),
            "audio_stream_binding": audio_stream_binding,
            "container_binding": container_binding,
        },
        "plan": {
            "planned_sample_rate_hz": mux_prep["planned_sample_rate_hz"],
            "planned_frame_count": mux_prep["planned_frame_count"],
            "planned_start_sample": mux_prep["planned_start_sample"],
            "planned_end_sample_exclusive": mux_prep["planned_end_sample_exclusive"],
            "frame_rate_mode": mux_prep["frame_rate_mode"],
            "vfr_segment_count": mux_prep["vfr_segment_count"],
            "cut_epoch_count": mux_prep["cut_epoch_count"],
        },
        "execution_guards": {
            "mux_command_executed": False,
            "mux_replay_executed": False,
            "runtime_media_decode_invoked": False,
            "visual_review_authority_granted": False,
        },
    }


def _planned_mux_command_envelope_sha256(envelope: dict[str, Any]) -> str:
    """Content-addressed planned mux command envelope digest (no wall-clock)."""
    return _canonical_sha256(envelope)


def _dry_run_mux_plan_sha256(
    *,
    timeline_id: str,
    timeline_plan_sha256: str,
    revision: str,
    mux_prep: dict[str, Any],
    planned_mux_command_envelope_sha256: str | None,
) -> str:
    """Content-addressed dry-run mux plan digest (excludes created_at / wall-clock)."""
    return _canonical_sha256(
        {
            "record_type": "canonical_video_timeline_mux_prep_dry_run_plan",
            "timeline_id": timeline_id,
            "timeline_plan_sha256": timeline_plan_sha256,
            "revision": revision,
            "mux_prep": mux_prep,
            "planned_mux_command_envelope_sha256": planned_mux_command_envelope_sha256,
            "mux_command_executed": False,
            "mux_replay_executed": False,
        }
    )


def _validate_tolerances(raw: Any) -> dict[str, float]:
    if raw is None:
        return dict(DEFAULT_TOLERANCES)
    if not isinstance(raw, dict):
        raise ValueError("tolerances must be an object")
    allowed = {"max_frame_residual", "max_sample_residual", "max_seconds_residual"}
    _assert_keys_exact(raw, allowed, "tolerances")
    return {
        "max_frame_residual": _expect_number(raw.get("max_frame_residual"), "tolerances.max_frame_residual"),
        "max_sample_residual": _expect_number(raw.get("max_sample_residual"), "tolerances.max_sample_residual"),
        "max_seconds_residual": _expect_number(
            raw.get("max_seconds_residual"), "tolerances.max_seconds_residual"
        ),
    }


def _validate_frame_table(raw: Any, clock_span: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("frame_table must be a non-empty list")
    frames: list[dict[str, Any]] = []
    previous_pts: int | None = None
    previous_index: int | None = None
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"frame_table[{idx}] must be an object")
        _assert_keys_exact(entry, ALLOWED_FRAME_FIELDS, f"frame_table[{idx}]")
        frame_index = _expect_non_negative_int(entry.get("frame_index"), f"frame_table[{idx}].frame_index")
        source_pts = _expect_non_negative_int(entry.get("source_pts"), f"frame_table[{idx}].source_pts")
        duration_pts = _expect_positive_int(entry.get("duration_pts"), f"frame_table[{idx}].duration_pts")
        if previous_index is not None and frame_index != previous_index + 1:
            raise ValueError(f"frame_table[{idx}].frame_index must be contiguous")
        if previous_pts is not None and source_pts < previous_pts:
            raise ValueError(f"frame_table[{idx}].source_pts must be monotonic non-decreasing")
        if frame_index < clock_span["start_frame"] or frame_index >= clock_span["end_frame_exclusive"]:
            raise ValueError(f"frame_table[{idx}].frame_index outside clock_span frame bounds")
        frames.append(
            {
                "frame_index": frame_index,
                "source_pts": source_pts,
                "duration_pts": duration_pts,
            }
        )
        previous_index = frame_index
        previous_pts = source_pts
    if frames[0]["frame_index"] != clock_span["start_frame"]:
        raise ValueError("frame_table must begin at clock_span.start_frame")
    if frames[-1]["frame_index"] != clock_span["end_frame_exclusive"] - 1:
        raise ValueError("frame_table must end at clock_span.end_frame_exclusive - 1")
    return frames


def _validate_vfr_segments(raw: Any, frame_rate_mode: str, clock_span: dict[str, Any]) -> list[dict[str, Any]]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("vfr_segments must be a list")
    if frame_rate_mode == "vfr" and not raw:
        raise ValueError("vfr frame_rate_mode requires a non-empty vfr_segments map")
    if frame_rate_mode != "vfr" and raw:
        raise ValueError("vfr_segments must be empty unless frame_rate_mode is vfr")
    segments: list[dict[str, Any]] = []
    previous_end: int | None = None
    seen_ids: set[str] = set()
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"vfr_segments[{idx}] must be an object")
        allowed = {
            "segment_id",
            "start_frame",
            "end_frame_exclusive",
            "timebase_numerator",
            "timebase_denominator",
        }
        _assert_keys_exact(entry, allowed, f"vfr_segments[{idx}]")
        start_frame = _expect_non_negative_int(entry.get("start_frame"), f"vfr_segments[{idx}].start_frame")
        end_frame = _expect_positive_int(
            entry.get("end_frame_exclusive"), f"vfr_segments[{idx}].end_frame_exclusive"
        )
        if start_frame >= end_frame:
            raise ValueError(f"vfr_segments[{idx}] start_frame must precede end_frame_exclusive")
        if previous_end is not None and start_frame < previous_end:
            raise ValueError(f"vfr_segments[{idx}] overlaps prior segment")
        if previous_end is not None and start_frame > previous_end:
            raise ValueError(f"vfr_segments[{idx}] leaves an unmapped frame gap")
        segment_id = _expect_non_empty_string(entry.get("segment_id"), f"vfr_segments[{idx}].segment_id")
        if segment_id in seen_ids:
            raise ValueError(f"vfr_segments[{idx}].segment_id duplicates a prior segment_id")
        seen_ids.add(segment_id)
        segments.append(
            {
                "segment_id": segment_id,
                "start_frame": start_frame,
                "end_frame_exclusive": end_frame,
                "timebase_numerator": _expect_positive_int(
                    entry.get("timebase_numerator"), f"vfr_segments[{idx}].timebase_numerator"
                ),
                "timebase_denominator": _expect_positive_int(
                    entry.get("timebase_denominator"), f"vfr_segments[{idx}].timebase_denominator"
                ),
            }
        )
        previous_end = end_frame
    if segments:
        if segments[0]["start_frame"] != clock_span["start_frame"]:
            raise ValueError("vfr_segments must begin at clock_span.start_frame")
        if segments[-1]["end_frame_exclusive"] != clock_span["end_frame_exclusive"]:
            raise ValueError("vfr_segments must end at clock_span.end_frame_exclusive")
    return segments


def _validate_cut_epochs(raw: Any, clock_span: dict[str, Any]) -> list[dict[str, Any]]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("cut_epochs must be a list")
    cuts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_frame: int | None = None
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"cut_epochs[{idx}] must be an object")
        allowed = {"cut_id", "frame_index", "cut_kind", "algorithm_id", "confidence"}
        _assert_keys_exact(entry, allowed, f"cut_epochs[{idx}]")
        frame_index = _expect_non_negative_int(entry.get("frame_index"), f"cut_epochs[{idx}].frame_index")
        if frame_index < clock_span["start_frame"] or frame_index >= clock_span["end_frame_exclusive"]:
            raise ValueError(f"cut_epochs[{idx}].frame_index outside clock_span bounds")
        if previous_frame is not None and frame_index <= previous_frame:
            raise ValueError(f"cut_epochs[{idx}].frame_index must be strictly increasing")
        cut_kind = _expect_non_empty_string(entry.get("cut_kind"), f"cut_epochs[{idx}].cut_kind")
        if cut_kind not in ALLOWED_CUT_KINDS:
            raise ValueError(f"cut_epochs[{idx}].cut_kind must be one of {sorted(ALLOWED_CUT_KINDS)}")
        confidence = _expect_number(entry.get("confidence"), f"cut_epochs[{idx}].confidence")
        if confidence < 0 or confidence > 1:
            raise ValueError(f"cut_epochs[{idx}].confidence must be within [0, 1]")
        cut_id = _expect_non_empty_string(entry.get("cut_id"), f"cut_epochs[{idx}].cut_id")
        if cut_id in seen_ids:
            raise ValueError(f"cut_epochs[{idx}].cut_id duplicates a prior cut_id")
        seen_ids.add(cut_id)
        cuts.append(
            {
                "cut_id": cut_id,
                "frame_index": frame_index,
                "cut_kind": cut_kind,
                "algorithm_id": _expect_non_empty_string(
                    entry.get("algorithm_id"), f"cut_epochs[{idx}].algorithm_id"
                ),
                "confidence": confidence,
            }
        )
        previous_frame = frame_index
    return cuts


def _validate_missing_frames(raw: Any, clock_span: dict[str, Any]) -> list[dict[str, Any]]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("missing_frames must be a list")
    missing: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"missing_frames[{idx}] must be an object")
        _assert_keys_exact(entry, {"frame_index", "policy"}, f"missing_frames[{idx}]")
        frame_index = _expect_non_negative_int(entry.get("frame_index"), f"missing_frames[{idx}].frame_index")
        if frame_index < clock_span["start_frame"] or frame_index >= clock_span["end_frame_exclusive"]:
            raise ValueError(f"missing_frames[{idx}].frame_index outside clock_span bounds")
        if frame_index in seen_indices:
            raise ValueError(f"missing_frames[{idx}].frame_index duplicates a prior missing frame")
        seen_indices.add(frame_index)
        policy = _expect_non_empty_string(entry.get("policy"), f"missing_frames[{idx}].policy")
        if policy not in ALLOWED_MISSING_POLICIES:
            raise ValueError(
                f"missing_frames[{idx}].policy must be one of {sorted(ALLOWED_MISSING_POLICIES)}"
            )
        if policy in RUNTIME_BLOCKED_MISSING_POLICIES:
            raise ValueError(
                f"missing_frames[{idx}].policy {policy} is fail-closed until missing-frame "
                "runtime completion (authorized fixture policies: preserve_gap, explicit_gap)"
            )
        missing.append({"frame_index": frame_index, "policy": policy})
    missing.sort(key=lambda item: item["frame_index"])
    return missing


def _build_normalized_frames(
    frames: list[dict[str, Any]],
    clock_span: dict[str, Any],
    tolerances: dict[str, float],
    *,
    frame_rate_mode: str,
    vfr_segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fps_num = clock_span["frame_rate_numerator"]
    fps_den = clock_span["frame_rate_denominator"]
    sample_rate = clock_span["sample_rate_hz"]
    rounding = clock_span["rounding_policy"]
    normalized: list[dict[str, Any]] = []
    max_frame_residual = 0.0
    max_sample_residual = 0.0
    max_seconds_residual = 0.0
    for entry in frames:
        frame_index = entry["frame_index"]
        if frame_rate_mode == "vfr":
            seconds = seconds_from_vfr_frame(frame_index, vfr_segments)
        else:
            seconds = seconds_from_frame(frame_index, fps_num, fps_den)
        sample = sample_from_seconds(seconds, sample_rate, rounding)
        roundtrip_seconds = sample / float(sample_rate)
        if frame_rate_mode == "vfr":
            roundtrip_frame = frame_from_vfr_seconds(roundtrip_seconds, vfr_segments, rounding)
        else:
            roundtrip_frame = frame_from_seconds(roundtrip_seconds, fps_num, fps_den, rounding)
        frame_residual = abs(roundtrip_frame - frame_index)
        sample_residual = abs(sample - round(seconds * sample_rate))
        seconds_residual = abs(roundtrip_seconds - seconds)
        max_frame_residual = max(max_frame_residual, float(frame_residual))
        max_sample_residual = max(max_sample_residual, float(sample_residual))
        max_seconds_residual = max(max_seconds_residual, float(seconds_residual))
        if frame_residual > tolerances["max_frame_residual"]:
            raise ValueError(
                f"frame {frame_index} round-trip frame residual {frame_residual} exceeds tolerance"
            )
        if sample_residual > tolerances["max_sample_residual"]:
            raise ValueError(
                f"frame {frame_index} round-trip sample residual {sample_residual} exceeds tolerance"
            )
        if seconds_residual > tolerances["max_seconds_residual"]:
            raise ValueError(
                f"frame {frame_index} round-trip seconds residual {seconds_residual} exceeds tolerance"
            )
        normalized.append(
            {
                "frame_index": frame_index,
                "source_pts": entry["source_pts"],
                "duration_pts": entry["duration_pts"],
                "normalized_seconds": round(seconds, 12),
                "normalized_sample": sample,
            }
        )
    evidence = {
        "checked_frame_count": len(normalized),
        "max_observed_frame_residual": max_frame_residual,
        "max_observed_sample_residual": max_sample_residual,
        "max_observed_seconds_residual": max_seconds_residual,
        "within_tolerance": True,
        "frame_rate_mode": frame_rate_mode,
        "vfr_segment_count": len(vfr_segments) if frame_rate_mode == "vfr" else 0,
    }
    return normalized, evidence


def compile_timeline(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    frame_rate_mode = _expect_non_empty_string(payload.get("frame_rate_mode"), "frame_rate_mode")
    if frame_rate_mode not in ALLOWED_FRAME_RATE_MODES:
        raise ValueError(f"frame_rate_mode must be one of {sorted(ALLOWED_FRAME_RATE_MODES)}")

    camera_motion_policy = _expect_non_empty_string(
        payload.get("camera_motion_policy"), "camera_motion_policy"
    )
    if camera_motion_policy not in ALLOWED_CAMERA_MOTION:
        raise ValueError(f"camera_motion_policy must be one of {sorted(ALLOWED_CAMERA_MOTION)}")

    clock_span = validate_clock_span_invariants(payload.get("clock_span") or {})
    source_binding = _validate_source_binding(payload.get("source_binding"))
    tolerances = _validate_tolerances(payload.get("tolerances"))
    frames = _validate_frame_table(payload.get("frame_table"), clock_span)
    vfr_segments = _validate_vfr_segments(payload.get("vfr_segments"), frame_rate_mode, clock_span)
    cut_epochs = _validate_cut_epochs(payload.get("cut_epochs"), clock_span)
    missing_frames = _validate_missing_frames(payload.get("missing_frames"), clock_span)

    dependency_raw = payload.get("dependency_authority")
    if not isinstance(dependency_raw, dict):
        raise ValueError("dependency_authority must be an object")
    _assert_keys_exact(dependency_raw, {"row067_complete"}, "dependency_authority")
    row067_complete = _expect_boolean(dependency_raw.get("row067_complete"), "dependency_authority.row067_complete")

    runtime_raw = payload.get("runtime_authority")
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_allowed = {
        "mux_replay_proof_present",
        "combined_visual_review_present",
        "fixed_vfr_benchmark_pass",
    }
    _assert_keys_exact(runtime_raw, runtime_allowed, "runtime_authority")
    mux_replay = _expect_boolean(
        runtime_raw.get("mux_replay_proof_present"), "runtime_authority.mux_replay_proof_present"
    )
    visual_review = _expect_boolean(
        runtime_raw.get("combined_visual_review_present"),
        "runtime_authority.combined_visual_review_present",
    )
    benchmark_pass = _expect_boolean(
        runtime_raw.get("fixed_vfr_benchmark_pass"), "runtime_authority.fixed_vfr_benchmark_pass"
    )

    normalized_frames, roundtrip_evidence = _build_normalized_frames(
        frames,
        clock_span,
        tolerances,
        frame_rate_mode=frame_rate_mode,
        vfr_segments=vfr_segments,
    )
    roundtrip_evidence["cut_epoch_count"] = len(cut_epochs)

    dependency_ready = row067_complete
    runtime_ready = mux_replay and visual_review and benchmark_pass
    production_completion_allowed = bool(dependency_ready and runtime_ready and roundtrip_evidence["within_tolerance"])
    if production_completion_allowed:
        # Still fail closed in this increment: no direct Row084 tracker receipt path yet.
        production_completion_allowed = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    elif not runtime_ready:
        authority_ceiling = "technical"
        status = "technical_partial"
    else:
        authority_ceiling = "technical"
        status = "technical_partial"

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline",
        "timeline_id": _expect_non_empty_string(payload.get("timeline_id"), "timeline_id"),
        "revision": _expect_non_empty_string(payload.get("revision"), "revision"),
        "status": status,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_binding": source_binding,
        "clock_span": clock_span,
        "frame_rate_mode": frame_rate_mode,
        "frame_table": normalized_frames,
        "vfr_segments": vfr_segments,
        "cut_epochs": cut_epochs,
        "missing_frames": missing_frames,
        "camera_motion_policy": camera_motion_policy,
        "tolerances": tolerances,
        "roundtrip_evidence": roundtrip_evidence,
        "dependency_authority": {"row067_complete": row067_complete},
        "runtime_authority": {
            "mux_replay_proof_present": mux_replay,
            "combined_visual_review_present": visual_review,
            "fixed_vfr_benchmark_pass": benchmark_pass,
        },
        "authority_ceiling": authority_ceiling,
        "production_completion_allowed": production_completion_allowed,
        "row_complete": False,
        "provenance": provenance,
    }
    timeline_sha256 = _canonical_sha256(receipt_body)
    receipt_body["timeline_sha256"] = timeline_sha256
    return receipt_body


def build_mux_prep_scaffold(timeline_receipt: dict[str, Any]) -> dict[str, Any]:
    """Build a fail-closed mux-prep receipt scaffold from a compiled timeline.

    This records planned mux bindings only. It never executes mux, never grants
    mux-replay authority, and never flips row_complete.
    """
    if not isinstance(timeline_receipt, dict):
        raise ValueError("timeline_receipt must be an object")
    if timeline_receipt.get("record_type") != "canonical_video_timeline":
        raise ValueError("timeline_receipt.record_type must equal canonical_video_timeline")
    timeline_id = _expect_non_empty_string(timeline_receipt.get("timeline_id"), "timeline_id")
    timeline_sha256 = _expect_sha256(timeline_receipt.get("timeline_sha256"), "timeline_sha256")
    revision = _expect_non_empty_string(timeline_receipt.get("revision"), "revision")
    clock_span = timeline_receipt.get("clock_span")
    if not isinstance(clock_span, dict):
        raise ValueError("timeline_receipt.clock_span must be an object")
    frame_table = timeline_receipt.get("frame_table")
    if not isinstance(frame_table, list) or not frame_table:
        raise ValueError("timeline_receipt.frame_table must be a non-empty list")
    vfr_segments = timeline_receipt.get("vfr_segments")
    if not isinstance(vfr_segments, list):
        raise ValueError("timeline_receipt.vfr_segments must be a list")
    cut_epochs = timeline_receipt.get("cut_epochs")
    if not isinstance(cut_epochs, list):
        raise ValueError("timeline_receipt.cut_epochs must be a list")
    runtime_authority = timeline_receipt.get("runtime_authority")
    if not isinstance(runtime_authority, dict):
        raise ValueError("timeline_receipt.runtime_authority must be an object")
    source_binding = timeline_receipt.get("source_binding")
    if not isinstance(source_binding, dict):
        raise ValueError("timeline_receipt.source_binding must be an object")

    # Scaffold remains fail-closed even if an upstream packet falsely claims mux proof.
    mux_replay_claimed = _expect_boolean(
        runtime_authority.get("mux_replay_proof_present"),
        "runtime_authority.mux_replay_proof_present",
    )
    audio_stream_binding = _format_audio_stream_binding(source_binding)
    container_binding = _format_container_binding(source_binding)
    stream_identities_bound = audio_stream_binding is not None and container_binding is not None
    timeline_plan_sha256 = _stable_timeline_plan_sha256(timeline_receipt)
    mux_prep = {
        "planned_sample_rate_hz": _expect_positive_int(
            clock_span.get("sample_rate_hz"), "clock_span.sample_rate_hz"
        ),
        "planned_frame_count": len(frame_table),
        "planned_start_sample": _expect_non_negative_int(
            clock_span.get("start_sample"), "clock_span.start_sample"
        ),
        "planned_end_sample_exclusive": _expect_positive_int(
            clock_span.get("end_sample_exclusive"), "clock_span.end_sample_exclusive"
        ),
        "frame_rate_mode": _expect_non_empty_string(
            timeline_receipt.get("frame_rate_mode"), "frame_rate_mode"
        ),
        "vfr_segment_count": len(vfr_segments),
        "cut_epoch_count": len(cut_epochs),
        "audio_stream_binding": audio_stream_binding,
        "container_binding": container_binding,
        "stream_identities_bound": stream_identities_bound,
        "timeline_plan_sha256": timeline_plan_sha256,
        "mux_command_planned": stream_identities_bound,
        "mux_command_executed": False,
    }
    if stream_identities_bound:
        planned_mux_command_envelope = _build_planned_mux_command_envelope(
            timeline_id=timeline_id,
            revision=revision,
            timeline_plan_sha256=timeline_plan_sha256,
            source_binding=source_binding,
            mux_prep=mux_prep,
        )
        planned_mux_command_envelope_sha256 = _planned_mux_command_envelope_sha256(
            planned_mux_command_envelope
        )
        # Determinism gate for the envelope itself (no wall-clock inputs).
        envelope_recomputed = _planned_mux_command_envelope_sha256(planned_mux_command_envelope)
        if planned_mux_command_envelope_sha256 != envelope_recomputed:
            raise ValueError("planned_mux_command_envelope_sha256 recomputation mismatch")
        if planned_mux_command_envelope["execution_guards"]["mux_command_executed"]:
            raise ValueError("planned mux command envelope must remain non-executed")
    else:
        planned_mux_command_envelope = None
        planned_mux_command_envelope_sha256 = None

    dry_run_mux_plan_sha256 = _dry_run_mux_plan_sha256(
        timeline_id=timeline_id,
        timeline_plan_sha256=timeline_plan_sha256,
        revision=revision,
        mux_prep=mux_prep,
        planned_mux_command_envelope_sha256=planned_mux_command_envelope_sha256,
    )
    # Determinism gate: recompute must match without wall-clock inputs.
    recomputed = _dry_run_mux_plan_sha256(
        timeline_id=timeline_id,
        timeline_plan_sha256=timeline_plan_sha256,
        revision=revision,
        mux_prep=mux_prep,
        planned_mux_command_envelope_sha256=planned_mux_command_envelope_sha256,
    )
    if dry_run_mux_plan_sha256 != recomputed:
        raise ValueError("dry_run_mux_plan_sha256 recomputation mismatch")

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    body = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline_mux_prep_receipt",
        "timeline_id": timeline_id,
        "timeline_sha256": timeline_sha256,
        "revision": revision,
        "status": "scaffold_hold",
        "created_at": created_at,
        "mux_prep": mux_prep,
        "planned_mux_command_envelope": planned_mux_command_envelope,
        "planned_mux_command_envelope_sha256": planned_mux_command_envelope_sha256,
        "dry_run_mux_plan_sha256": dry_run_mux_plan_sha256,
        "authority": {
            "scaffold_only": True,
            "mux_replay_executed": False,
            "mux_replay_proof_present": False,
            "mux_authority_granted": False,
            "upstream_mux_replay_claim_ignored": mux_replay_claimed,
            "dry_run_plan_only": True,
            "stream_identities_bound": stream_identities_bound,
            "planned_mux_command_envelope_bound": stream_identities_bound,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "scaffold_kind": "mux_prep_receipt",
        },
    }
    body["mux_prep_sha256"] = _canonical_sha256(body)
    return body


def compile_held_out_roundtrip_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a held-out fixed/VFR round-trip fixture matrix.

    Fixture matrix success does not grant runtime benchmark, mux-replay, or
    visual-review authority and never sets row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("held-out matrix payload must be an object")
    allowed = {"schema_version", "matrix_id", "revision", "cases", "provenance"}
    _assert_keys_exact(payload, allowed, "held_out_matrix")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    matrix_id = _expect_non_empty_string(payload.get("matrix_id"), "matrix_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 2:
        raise ValueError("cases must be a list with at least two held-out fixtures")

    seen_case_ids: set[str] = set()
    seen_modes: set[str] = set()
    case_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(cases_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"cases[{idx}] must be an object")
        _assert_keys_exact(entry, {"case_id", "partition", "timeline_packet"}, f"cases[{idx}]")
        case_id = _expect_non_empty_string(entry.get("case_id"), f"cases[{idx}].case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"cases[{idx}].case_id duplicates a prior case_id")
        seen_case_ids.add(case_id)
        partition = _expect_non_empty_string(entry.get("partition"), f"cases[{idx}].partition")
        if partition != "held_out":
            raise ValueError(f"cases[{idx}].partition must equal held_out")
        packet = entry.get("timeline_packet")
        if not isinstance(packet, dict):
            raise ValueError(f"cases[{idx}].timeline_packet must be an object")
        receipt = compile_timeline(packet)
        mode = receipt["frame_rate_mode"]
        seen_modes.add(mode)
        evidence = receipt["roundtrip_evidence"]
        case_results.append(
            {
                "case_id": case_id,
                "partition": partition,
                "timeline_id": receipt["timeline_id"],
                "timeline_sha256": receipt["timeline_sha256"],
                "frame_rate_mode": mode,
                "checked_frame_count": evidence["checked_frame_count"],
                "within_tolerance": evidence["within_tolerance"],
                "max_observed_frame_residual": evidence["max_observed_frame_residual"],
                "max_observed_sample_residual": evidence["max_observed_sample_residual"],
                "max_observed_seconds_residual": evidence["max_observed_seconds_residual"],
                "vfr_segment_count": evidence["vfr_segment_count"],
                "cut_epoch_count": evidence["cut_epoch_count"],
                "row_complete": False,
            }
        )

    if "fixed" not in seen_modes and "fractional" not in seen_modes:
        raise ValueError("held-out matrix requires at least one fixed or fractional case")
    if "vfr" not in seen_modes:
        raise ValueError("held-out matrix requires at least one vfr case")

    all_within = all(case["within_tolerance"] for case in case_results)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    body = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline_held_out_roundtrip_matrix",
        "matrix_id": matrix_id,
        "revision": revision,
        "status": "fixture_matrix_partial" if all_within else "blocked",
        "created_at": created_at,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "passed_count": sum(1 for case in case_results if case["within_tolerance"]),
            "failed_count": sum(1 for case in case_results if not case["within_tolerance"]),
            "all_within_tolerance": all_within,
            "modes_covered": sorted(seen_modes),
            "mux_replay_included": False,
            "runtime_media_decode_invoked": False,
            "benchmark_authority_granted": False,
            "visual_review_authority_granted": False,
        },
        "authority": {
            "fixture_matrix_only": True,
            "fixed_vfr_benchmark_pass": False,
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": provenance,
    }
    body["matrix_sha256"] = _canonical_sha256(body)
    return body


def compile_held_out_mux_dry_run_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile held-out matrix with stream-bound mux-prep dry-run hash checks.

    Requires audio/container stream identities on every case. Proves deterministic
    dry-run mux plan digests only. Never executes mux, never grants mux-replay or
    visual-review authority, and never sets row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("held-out mux dry-run payload must be an object")
    allowed = {"schema_version", "matrix_id", "revision", "cases", "provenance"}
    _assert_keys_exact(payload, allowed, "held_out_mux_dry_run_matrix")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    matrix_id = _expect_non_empty_string(payload.get("matrix_id"), "matrix_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 2:
        raise ValueError("cases must be a list with at least two held-out fixtures")

    seen_case_ids: set[str] = set()
    seen_modes: set[str] = set()
    case_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(cases_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"cases[{idx}] must be an object")
        _assert_keys_exact(entry, {"case_id", "partition", "timeline_packet"}, f"cases[{idx}]")
        case_id = _expect_non_empty_string(entry.get("case_id"), f"cases[{idx}].case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"cases[{idx}].case_id duplicates a prior case_id")
        seen_case_ids.add(case_id)
        partition = _expect_non_empty_string(entry.get("partition"), f"cases[{idx}].partition")
        if partition != "held_out":
            raise ValueError(f"cases[{idx}].partition must equal held_out")
        packet = entry.get("timeline_packet")
        if not isinstance(packet, dict):
            raise ValueError(f"cases[{idx}].timeline_packet must be an object")

        source_binding = packet.get("source_binding")
        if not isinstance(source_binding, dict):
            raise ValueError(f"cases[{idx}].timeline_packet.source_binding must be an object")
        if source_binding.get("audio_stream_sha256") is None:
            raise ValueError(
                f"cases[{idx}] mux dry-run requires source_binding.audio_stream_sha256"
            )
        if source_binding.get("container_sha256") is None:
            raise ValueError(
                f"cases[{idx}] mux dry-run requires source_binding.container_sha256"
            )

        timeline_receipt = compile_timeline(packet)
        mux_prep_a = build_mux_prep_scaffold(timeline_receipt)
        mux_prep_b = build_mux_prep_scaffold(timeline_receipt)
        digest_a = mux_prep_a["dry_run_mux_plan_sha256"]
        digest_b = mux_prep_b["dry_run_mux_plan_sha256"]
        if digest_a != digest_b:
            raise ValueError(
                f"cases[{idx}] dry_run_mux_plan_sha256 not deterministic across rebuilds"
            )
        envelope_digest_a = mux_prep_a["planned_mux_command_envelope_sha256"]
        envelope_digest_b = mux_prep_b["planned_mux_command_envelope_sha256"]
        if not isinstance(envelope_digest_a, str) or len(envelope_digest_a) != 64:
            raise ValueError(
                f"cases[{idx}] planned_mux_command_envelope_sha256 must be bound for mux dry-run"
            )
        if envelope_digest_a != envelope_digest_b:
            raise ValueError(
                f"cases[{idx}] planned_mux_command_envelope_sha256 not deterministic across rebuilds"
            )
        envelope_a = mux_prep_a["planned_mux_command_envelope"]
        if not isinstance(envelope_a, dict):
            raise ValueError(f"cases[{idx}] planned_mux_command_envelope must be an object")
        if envelope_a.get("execution_mode") != "dry_run_non_executed":
            raise ValueError(f"cases[{idx}] planned mux envelope must remain dry_run_non_executed")
        if envelope_a.get("command_status") != "planned_only":
            raise ValueError(f"cases[{idx}] planned mux envelope command_status must be planned_only")
        if envelope_a.get("execution_guards", {}).get("mux_command_executed"):
            raise ValueError(f"cases[{idx}] planned mux envelope must remain non-executed")
        if not mux_prep_a["mux_prep"]["stream_identities_bound"]:
            raise ValueError(f"cases[{idx}] stream identities must be bound for mux dry-run")
        if not mux_prep_a["mux_prep"]["mux_command_planned"]:
            raise ValueError(f"cases[{idx}] mux_command_planned must be true for mux dry-run")
        if mux_prep_a["mux_prep"]["mux_command_executed"]:
            raise ValueError(f"cases[{idx}] mux_command_executed must remain false")
        if not mux_prep_a["authority"].get("planned_mux_command_envelope_bound"):
            raise ValueError(f"cases[{idx}] planned_mux_command_envelope_bound must be true")

        mode = timeline_receipt["frame_rate_mode"]
        seen_modes.add(mode)
        evidence = timeline_receipt["roundtrip_evidence"]
        case_results.append(
            {
                "case_id": case_id,
                "partition": partition,
                "timeline_id": timeline_receipt["timeline_id"],
                "timeline_sha256": timeline_receipt["timeline_sha256"],
                "frame_rate_mode": mode,
                "checked_frame_count": evidence["checked_frame_count"],
                "within_tolerance": evidence["within_tolerance"],
                "audio_stream_binding": mux_prep_a["mux_prep"]["audio_stream_binding"],
                "container_binding": mux_prep_a["mux_prep"]["container_binding"],
                "stream_identities_bound": True,
                "mux_command_planned": True,
                "mux_command_executed": False,
                "planned_mux_command_envelope_sha256": envelope_digest_a,
                "envelope_hash_deterministic": True,
                "dry_run_mux_plan_sha256": digest_a,
                "dry_run_hash_deterministic": True,
                "row_complete": False,
            }
        )

    if "fixed" not in seen_modes and "fractional" not in seen_modes:
        raise ValueError("held-out mux dry-run matrix requires at least one fixed or fractional case")
    if "vfr" not in seen_modes:
        raise ValueError("held-out mux dry-run matrix requires at least one vfr case")

    all_within = all(case["within_tolerance"] for case in case_results)
    all_dry_run_deterministic = all(case["dry_run_hash_deterministic"] for case in case_results)
    all_envelope_deterministic = all(case["envelope_hash_deterministic"] for case in case_results)
    all_deterministic = all_dry_run_deterministic and all_envelope_deterministic
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    body = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline_held_out_mux_dry_run_matrix",
        "matrix_id": matrix_id,
        "revision": revision,
        "status": "fixture_mux_dry_run_partial" if all_within and all_deterministic else "blocked",
        "created_at": created_at,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "passed_count": sum(1 for case in case_results if case["within_tolerance"]),
            "failed_count": sum(1 for case in case_results if not case["within_tolerance"]),
            "all_within_tolerance": all_within,
            "modes_covered": sorted(seen_modes),
            "stream_identities_bound": True,
            "dry_run_mux_hash_check_passed": all_dry_run_deterministic,
            "planned_mux_envelope_hash_check_passed": all_envelope_deterministic,
            "mux_replay_included": False,
            "runtime_media_decode_invoked": False,
            "benchmark_authority_granted": False,
            "visual_review_authority_granted": False,
        },
        "authority": {
            "fixture_matrix_only": True,
            "dry_run_plan_only": True,
            "planned_mux_command_envelope_only": True,
            "fixed_vfr_benchmark_pass": False,
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": provenance,
    }
    body["matrix_sha256"] = _canonical_sha256(body)
    return body


def compile_missing_frame_policy_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a fixture-backed preserve_gap / explicit_gap missing-frame policy matrix.

    Proves fail-closed acceptance of the two authorized fixture policies only.
    Does not grant missing-frame runtime completion, mux replay, visual review,
    or row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("missing-frame policy matrix payload must be an object")
    allowed = {"schema_version", "matrix_id", "revision", "cases", "provenance"}
    _assert_keys_exact(payload, allowed, "missing_frame_policy_matrix")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    matrix_id = _expect_non_empty_string(payload.get("matrix_id"), "matrix_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 2:
        raise ValueError("cases must be a list with at least two missing-frame policy fixtures")

    seen_case_ids: set[str] = set()
    seen_policies: set[str] = set()
    case_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(cases_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"cases[{idx}] must be an object")
        _assert_keys_exact(
            entry,
            {"case_id", "expected_policy", "timeline_packet"},
            f"cases[{idx}]",
        )
        case_id = _expect_non_empty_string(entry.get("case_id"), f"cases[{idx}].case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"cases[{idx}].case_id duplicates a prior case_id")
        seen_case_ids.add(case_id)
        expected_policy = _expect_non_empty_string(
            entry.get("expected_policy"), f"cases[{idx}].expected_policy"
        )
        if expected_policy not in MATRIX_AUTHORIZED_MISSING_POLICIES:
            raise ValueError(
                f"cases[{idx}].expected_policy must be one of "
                f"{sorted(MATRIX_AUTHORIZED_MISSING_POLICIES)}"
            )
        packet = entry.get("timeline_packet")
        if not isinstance(packet, dict):
            raise ValueError(f"cases[{idx}].timeline_packet must be an object")
        declared = packet.get("missing_frames")
        if not isinstance(declared, list) or not declared:
            raise ValueError(f"cases[{idx}].timeline_packet.missing_frames must be a non-empty list")
        for miss_idx, miss in enumerate(declared):
            if not isinstance(miss, dict):
                raise ValueError(
                    f"cases[{idx}].timeline_packet.missing_frames[{miss_idx}] must be an object"
                )
            policy = miss.get("policy")
            if policy != expected_policy:
                raise ValueError(
                    f"cases[{idx}].timeline_packet.missing_frames[{miss_idx}].policy "
                    f"must equal expected_policy {expected_policy}"
                )

        receipt = compile_timeline(packet)
        applied = receipt.get("missing_frames")
        if not isinstance(applied, list) or not applied:
            raise ValueError(f"cases[{idx}] compiled receipt missing_frames must be non-empty")
        applied_policies = {item["policy"] for item in applied if isinstance(item, dict)}
        if applied_policies != {expected_policy}:
            raise ValueError(
                f"cases[{idx}] compiled missing_frames policies {sorted(applied_policies)} "
                f"must equal {{{expected_policy}}}"
            )
        seen_policies.add(expected_policy)
        case_results.append(
            {
                "case_id": case_id,
                "expected_policy": expected_policy,
                "timeline_id": receipt["timeline_id"],
                "timeline_sha256": receipt["timeline_sha256"],
                "frame_rate_mode": receipt["frame_rate_mode"],
                "missing_frame_count": len(applied),
                "applied_policies": sorted(applied_policies),
                "policy_applied": True,
                "within_tolerance": receipt["roundtrip_evidence"]["within_tolerance"],
                "runtime_policy_complete": False,
                "row_complete": False,
            }
        )

    if "preserve_gap" not in seen_policies:
        raise ValueError("missing-frame policy matrix requires at least one preserve_gap case")
    if "explicit_gap" not in seen_policies:
        raise ValueError("missing-frame policy matrix requires at least one explicit_gap case")

    all_within = all(case["within_tolerance"] for case in case_results)
    all_applied = all(case["policy_applied"] for case in case_results)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    body = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline_missing_frame_policy_matrix",
        "matrix_id": matrix_id,
        "revision": revision,
        "status": "fixture_missing_frame_policy_partial" if all_within and all_applied else "blocked",
        "created_at": created_at,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "passed_count": sum(
                1 for case in case_results if case["within_tolerance"] and case["policy_applied"]
            ),
            "failed_count": sum(
                1
                for case in case_results
                if not (case["within_tolerance"] and case["policy_applied"])
            ),
            "all_within_tolerance": all_within,
            "policies_covered": sorted(seen_policies),
            "preserve_gap_covered": "preserve_gap" in seen_policies,
            "explicit_gap_covered": "explicit_gap" in seen_policies,
            "runtime_policy_complete": False,
            "mux_replay_included": False,
            "runtime_media_decode_invoked": False,
            "benchmark_authority_granted": False,
            "visual_review_authority_granted": False,
        },
        "authority": {
            "fixture_matrix_only": True,
            "missing_frame_policy_runtime_complete": False,
            "fixed_vfr_benchmark_pass": False,
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": provenance,
    }
    body["matrix_sha256"] = _canonical_sha256(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a fail-closed Row084 canonical video timeline receipt.")
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Path to timeline, mux-prep, held-out matrix, held-out mux dry-run, "
            "or missing-frame policy matrix input JSON"
        ),
    )
    parser.add_argument("--output", required=True, help="Path to write compiled receipt JSON")
    parser.add_argument(
        "--mode",
        choices=(
            "timeline",
            "mux-prep",
            "held-out-matrix",
            "held-out-mux-dry-run",
            "missing-frame-policy-matrix",
        ),
        default="timeline",
        help="Compilation mode (default: timeline)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input packet must be a JSON object")
    try:
        if args.mode == "timeline":
            receipt = compile_timeline(payload)
            digest_key = "timeline_sha256"
        elif args.mode == "mux-prep":
            # Accept either a raw timeline packet or an already-compiled timeline receipt.
            if payload.get("record_type") == "canonical_video_timeline":
                timeline_receipt = payload
            else:
                timeline_receipt = compile_timeline(payload)
            receipt = build_mux_prep_scaffold(timeline_receipt)
            digest_key = "mux_prep_sha256"
        elif args.mode == "held-out-matrix":
            receipt = compile_held_out_roundtrip_matrix(payload)
            digest_key = "matrix_sha256"
        elif args.mode == "held-out-mux-dry-run":
            receipt = compile_held_out_mux_dry_run_matrix(payload)
            digest_key = "matrix_sha256"
        else:
            receipt = compile_missing_frame_policy_matrix(payload)
            digest_key = "matrix_sha256"
    except ValueError as exc:
        raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": args.mode,
                digest_key: receipt[digest_key],
                "row_complete": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
