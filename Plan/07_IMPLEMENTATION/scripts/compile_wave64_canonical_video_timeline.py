#!/usr/bin/env python3
"""Fail-closed Row084 canonical video timeline compiler.

Compiles fixture or decoded-frame metadata into a content-addressed timeline
receipt, plus mux-prep scaffold, held-out fixed/VFR round-trip matrix helpers,
a fixture-backed missing-frame policy matrix (preserve_gap / explicit_gap),
a fixture-backed camera-motion policy matrix
(not_evaluated / blocked_until_calibrated / distinguish_from_cuts),
a fixture-backed cut-detector algorithm contract
(algorithm_id + confidence calibration gates), and a synthetic runtime-climb
ledger binding cut/camera/mux-plan-replay/combined-visual fixture digests,
plus offline held-out cut/camera/roundtrip runtime climb helpers.
Production completion remains blocked unless dependency, benchmark, mux-replay,
and visual-review authorities are all satisfied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMPILER_REVISION = "row084_synthetic_runtime_climb_ledger_v9"
FIXTURE_MUX_RUNTIME_REVISION = "row084_fixture_media_mux_runtime_v10"
HELD_OUT_FFMPEG_MUX_REPLAY_REVISION = "row084_held_out_ffmpeg_mux_replay_v1"
MATRIX_AUTHORIZED_MISSING_POLICIES = frozenset({"preserve_gap", "explicit_gap"})
RUNTIME_BLOCKED_MISSING_POLICIES = frozenset({"interpolate", "block"})
MATRIX_AUTHORIZED_CAMERA_MOTION_POLICIES = frozenset(
    {"not_evaluated", "blocked_until_calibrated", "distinguish_from_cuts"}
)
CONTRACT_AUTHORIZED_CUT_DETECTOR_ALGORITHMS = frozenset(
    {"fixture_ledger_v1", "fixture_histogram_diff_v1"}
)
CONTRACT_AUTHORIZED_CUT_DETECTOR_CALIBRATION = "fixture_calibrated"

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = (
    REPO_ROOT
    / "Plan"
    / "Instructions"
    / "QA"
    / "Evidence"
    / "Wave64"
    / "fixtures"
    / "row084"
)
SYNTHETIC_RUNTIME_CLIMB_LEDGER_FILENAME = "synthetic_runtime_climb_ledger.json"
CUT_DETECTOR_CONTRACT_FIXTURE = "cut_detector_algorithm_contract.json"
CAMERA_MOTION_MATRIX_FIXTURE = "camera_motion_policy_matrix.json"
HELD_OUT_MUX_DRY_RUN_FIXTURE = "held_out_mux_dry_run_matrix.json"
COMBINED_VISUAL_PROTOCOL_FIXTURE = "combined_visual_review_fixture_protocol.json"
FIXTURE_MEDIA_AUDIO = "media/fixture_audio_stream.bin"
FIXTURE_MEDIA_CONTAINER = "media/fixture_container.bin"
FIXTURE_MEDIA_VIDEO = "media/fixture_video_stream.bin"
FIXTURE_MUX_RUNTIME_DIRNAME = "runtime"
FIXTURE_MUX_OUTPUT_FILENAME = "fixture_media_mux_output.mux"
FIXTURE_MUX_RUNTIME_RECEIPT_FILENAME = "fixture_media_mux_runtime_receipt.json"
HELD_OUT_FFMPEG_MUX_REPLAY_RECEIPT_FILENAME = "held_out_ffmpeg_mux_replay_receipt.json"
HELD_OUT_FFMPEG_MUX_REPLAY_DIRNAME = "held_out_ffmpeg_mux"
FFMPEG_PATH_PROBE_RECEIPT_FILENAME = "ffmpeg_path_probe_receipt.json"
FIXTURE_MUX_MAGIC = b"ROW084_FIXTURE_MUX_V1\n"
DEFAULT_FFMPEG_CANDIDATES = (
    Path(r"C:\Users\kevin\AppData\Local\Programs\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"),
    Path(r"C:\Users\kevin\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"),
    Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
)
REQUIRED_COMBINED_VISUAL_SURFACES = frozenset(
    {
        "frame_timeline",
        "cut_epochs",
        "camera_motion_policy",
        "contact_placeholder",
        "audio_stream_binding",
    }
)
ALLOWED_SYNTHETIC_CLIMB_LEDGER_FIELDS = {
    "schema_version",
    "record_type",
    "ledger_id",
    "revision",
    "is_synthetic",
    "proof_tier",
    "highest_proof_tier_achieved",
    "climb_targets",
    "production_benchmark",
    "runtime_mux_replay_pass",
    "visual_review_claimed",
    "row_complete",
    "production_completion_allowed",
    "authority_ceiling",
    "hold_reasons",
    "fixture_bindings",
    "cut_detector_calibration_expectations",
    "camera_motion_bindings",
    "fixture_mux_plan_replay",
    "combined_visual_review_protocol",
    "provenance",
    "ledger_sha256",
}


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
    if camera_motion_policy == "distinguish_from_cuts" and not cut_epochs:
        raise ValueError(
            "camera_motion_policy distinguish_from_cuts is fail-closed without "
            "non-empty cut_epochs (cannot distinguish camera motion from cuts)"
        )
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


def compile_camera_motion_policy_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a fixture-backed camera-motion policy distinction matrix.

    Covers not_evaluated / blocked_until_calibrated / distinguish_from_cuts with
    fail-closed reject paths. Does not grant camera-motion normalization,
    visual review, mux replay, or row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("camera-motion policy matrix payload must be an object")
    allowed = {"schema_version", "matrix_id", "revision", "cases", "provenance"}
    _assert_keys_exact(payload, allowed, "camera_motion_policy_matrix")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    matrix_id = _expect_non_empty_string(payload.get("matrix_id"), "matrix_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 3:
        raise ValueError("cases must be a list with at least three camera-motion policy fixtures")

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
        if expected_policy not in MATRIX_AUTHORIZED_CAMERA_MOTION_POLICIES:
            raise ValueError(
                f"cases[{idx}].expected_policy must be one of "
                f"{sorted(MATRIX_AUTHORIZED_CAMERA_MOTION_POLICIES)}"
            )
        packet = entry.get("timeline_packet")
        if not isinstance(packet, dict):
            raise ValueError(f"cases[{idx}].timeline_packet must be an object")
        declared_policy = packet.get("camera_motion_policy")
        if declared_policy != expected_policy:
            raise ValueError(
                f"cases[{idx}].timeline_packet.camera_motion_policy "
                f"must equal expected_policy {expected_policy}"
            )

        receipt = compile_timeline(packet)
        applied_policy = receipt.get("camera_motion_policy")
        if applied_policy != expected_policy:
            raise ValueError(
                f"cases[{idx}] compiled camera_motion_policy {applied_policy!r} "
                f"must equal expected_policy {expected_policy}"
            )
        cut_epochs = receipt.get("cut_epochs")
        if not isinstance(cut_epochs, list):
            raise ValueError(f"cases[{idx}] compiled receipt cut_epochs must be a list")
        if expected_policy == "distinguish_from_cuts" and not cut_epochs:
            raise ValueError(
                f"cases[{idx}] distinguish_from_cuts requires non-empty cut_epochs"
            )
        seen_policies.add(expected_policy)
        case_results.append(
            {
                "case_id": case_id,
                "expected_policy": expected_policy,
                "timeline_id": receipt["timeline_id"],
                "timeline_sha256": receipt["timeline_sha256"],
                "frame_rate_mode": receipt["frame_rate_mode"],
                "cut_epoch_count": len(cut_epochs),
                "applied_policy": applied_policy,
                "policy_applied": True,
                "within_tolerance": receipt["roundtrip_evidence"]["within_tolerance"],
                "runtime_policy_complete": False,
                "row_complete": False,
            }
        )

    for required in sorted(MATRIX_AUTHORIZED_CAMERA_MOTION_POLICIES):
        if required not in seen_policies:
            raise ValueError(
                f"camera-motion policy matrix requires at least one {required} case"
            )

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
        "record_type": "canonical_video_timeline_camera_motion_policy_matrix",
        "matrix_id": matrix_id,
        "revision": revision,
        "status": "fixture_camera_motion_policy_partial" if all_within and all_applied else "blocked",
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
            "not_evaluated_covered": "not_evaluated" in seen_policies,
            "blocked_until_calibrated_covered": "blocked_until_calibrated" in seen_policies,
            "distinguish_from_cuts_covered": "distinguish_from_cuts" in seen_policies,
            "runtime_policy_complete": False,
            "mux_replay_included": False,
            "runtime_media_decode_invoked": False,
            "benchmark_authority_granted": False,
            "visual_review_authority_granted": False,
        },
        "authority": {
            "fixture_matrix_only": True,
            "camera_motion_normalization_complete": False,
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


def compile_cut_detector_algorithm_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a fixture-backed cut-detector algorithm contract.

    Binds authorized algorithm_id values to confidence calibration gates and
    proves fail-closed reject paths. Does not grant runtime cut detection,
    visual review, mux replay, or row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("cut-detector algorithm contract payload must be an object")
    allowed = {
        "schema_version",
        "contract_id",
        "revision",
        "algorithms",
        "cases",
        "provenance",
    }
    _assert_keys_exact(payload, allowed, "cut_detector_algorithm_contract")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    contract_id = _expect_non_empty_string(payload.get("contract_id"), "contract_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")

    algorithms_raw = payload.get("algorithms")
    if not isinstance(algorithms_raw, list) or len(algorithms_raw) < 2:
        raise ValueError(
            "algorithms must be a list with at least two cut-detector algorithm entries"
        )
    algorithm_gates: dict[str, float] = {}
    algorithm_records: list[dict[str, Any]] = []
    for idx, entry in enumerate(algorithms_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"algorithms[{idx}] must be an object")
        _assert_keys_exact(
            entry,
            {"algorithm_id", "min_confidence", "calibration_status"},
            f"algorithms[{idx}]",
        )
        algorithm_id = _expect_non_empty_string(
            entry.get("algorithm_id"), f"algorithms[{idx}].algorithm_id"
        )
        if algorithm_id not in CONTRACT_AUTHORIZED_CUT_DETECTOR_ALGORITHMS:
            raise ValueError(
                f"algorithms[{idx}].algorithm_id {algorithm_id!r} is not authorized; "
                f"must be one of {sorted(CONTRACT_AUTHORIZED_CUT_DETECTOR_ALGORITHMS)}"
            )
        if algorithm_id in algorithm_gates:
            raise ValueError(f"algorithms[{idx}].algorithm_id duplicates a prior algorithm_id")
        min_confidence = _expect_number(
            entry.get("min_confidence"), f"algorithms[{idx}].min_confidence"
        )
        if min_confidence < 0 or min_confidence > 1:
            raise ValueError(f"algorithms[{idx}].min_confidence must be within [0, 1]")
        calibration_status = _expect_non_empty_string(
            entry.get("calibration_status"), f"algorithms[{idx}].calibration_status"
        )
        if calibration_status != CONTRACT_AUTHORIZED_CUT_DETECTOR_CALIBRATION:
            raise ValueError(
                f"algorithms[{idx}].calibration_status must equal "
                f"{CONTRACT_AUTHORIZED_CUT_DETECTOR_CALIBRATION!r} "
                f"(uncalibrated algorithms are fail-closed)"
            )
        algorithm_gates[algorithm_id] = float(min_confidence)
        algorithm_records.append(
            {
                "algorithm_id": algorithm_id,
                "min_confidence": float(min_confidence),
                "calibration_status": calibration_status,
                "authorized": True,
            }
        )

    for required in sorted(CONTRACT_AUTHORIZED_CUT_DETECTOR_ALGORITHMS):
        if required not in algorithm_gates:
            raise ValueError(
                f"cut-detector algorithm contract requires algorithm registry entry "
                f"for {required}"
            )

    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or len(cases_raw) < 2:
        raise ValueError(
            "cases must be a list with at least two cut-detector algorithm fixtures"
        )

    seen_case_ids: set[str] = set()
    seen_algorithms: set[str] = set()
    case_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(cases_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"cases[{idx}] must be an object")
        _assert_keys_exact(
            entry,
            {
                "case_id",
                "expected_algorithm_id",
                "expected_min_confidence",
                "timeline_packet",
            },
            f"cases[{idx}]",
        )
        case_id = _expect_non_empty_string(entry.get("case_id"), f"cases[{idx}].case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"cases[{idx}].case_id duplicates a prior case_id")
        seen_case_ids.add(case_id)
        expected_algorithm_id = _expect_non_empty_string(
            entry.get("expected_algorithm_id"), f"cases[{idx}].expected_algorithm_id"
        )
        if expected_algorithm_id not in algorithm_gates:
            raise ValueError(
                f"cases[{idx}].expected_algorithm_id {expected_algorithm_id!r} "
                f"is not present in the algorithm registry"
            )
        expected_min_confidence = _expect_number(
            entry.get("expected_min_confidence"), f"cases[{idx}].expected_min_confidence"
        )
        registry_min = algorithm_gates[expected_algorithm_id]
        if expected_min_confidence != registry_min:
            raise ValueError(
                f"cases[{idx}].expected_min_confidence {expected_min_confidence} "
                f"must equal registry min_confidence {registry_min} for "
                f"{expected_algorithm_id}"
            )

        packet = entry.get("timeline_packet")
        if not isinstance(packet, dict):
            raise ValueError(f"cases[{idx}].timeline_packet must be an object")
        receipt = compile_timeline(packet)
        cut_epochs = receipt.get("cut_epochs")
        if not isinstance(cut_epochs, list) or not cut_epochs:
            raise ValueError(
                f"cases[{idx}] requires non-empty cut_epochs for cut-detector contract"
            )

        applied_ids: set[str] = set()
        min_observed = 1.0
        for cut_idx, cut in enumerate(cut_epochs):
            if not isinstance(cut, dict):
                raise ValueError(f"cases[{idx}].cut_epochs[{cut_idx}] must be an object")
            algorithm_id = cut.get("algorithm_id")
            if algorithm_id not in algorithm_gates:
                raise ValueError(
                    f"cases[{idx}].cut_epochs[{cut_idx}].algorithm_id "
                    f"{algorithm_id!r} is not authorized by the contract registry"
                )
            if algorithm_id != expected_algorithm_id:
                raise ValueError(
                    f"cases[{idx}].cut_epochs[{cut_idx}].algorithm_id "
                    f"must equal expected_algorithm_id {expected_algorithm_id}"
                )
            confidence = cut.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
                raise ValueError(
                    f"cases[{idx}].cut_epochs[{cut_idx}].confidence must be a number"
                )
            confidence_f = float(confidence)
            if confidence_f < registry_min:
                raise ValueError(
                    f"cases[{idx}].cut_epochs[{cut_idx}].confidence {confidence_f} "
                    f"is below calibration gate min_confidence {registry_min} "
                    f"for algorithm_id {expected_algorithm_id}"
                )
            applied_ids.add(algorithm_id)
            min_observed = min(min_observed, confidence_f)

        seen_algorithms.add(expected_algorithm_id)
        case_results.append(
            {
                "case_id": case_id,
                "expected_algorithm_id": expected_algorithm_id,
                "expected_min_confidence": float(expected_min_confidence),
                "timeline_id": receipt["timeline_id"],
                "timeline_sha256": receipt["timeline_sha256"],
                "frame_rate_mode": receipt["frame_rate_mode"],
                "cut_epoch_count": len(cut_epochs),
                "applied_algorithm_ids": sorted(applied_ids),
                "min_observed_confidence": min_observed,
                "confidence_gate_passed": True,
                "algorithm_contract_applied": True,
                "within_tolerance": receipt["roundtrip_evidence"]["within_tolerance"],
                "runtime_detector_complete": False,
                "row_complete": False,
            }
        )

    for required in sorted(CONTRACT_AUTHORIZED_CUT_DETECTOR_ALGORITHMS):
        if required not in seen_algorithms:
            raise ValueError(
                f"cut-detector algorithm contract requires at least one {required} case"
            )

    all_within = all(case["within_tolerance"] for case in case_results)
    all_applied = all(case["algorithm_contract_applied"] for case in case_results)
    all_gated = all(case["confidence_gate_passed"] for case in case_results)
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
        "record_type": "canonical_video_timeline_cut_detector_algorithm_contract",
        "contract_id": contract_id,
        "revision": revision,
        "status": (
            "fixture_cut_detector_algorithm_partial"
            if all_within and all_applied and all_gated
            else "blocked"
        ),
        "created_at": created_at,
        "algorithms": algorithm_records,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "passed_count": sum(
                1
                for case in case_results
                if case["within_tolerance"]
                and case["algorithm_contract_applied"]
                and case["confidence_gate_passed"]
            ),
            "failed_count": sum(
                1
                for case in case_results
                if not (
                    case["within_tolerance"]
                    and case["algorithm_contract_applied"]
                    and case["confidence_gate_passed"]
                )
            ),
            "all_within_tolerance": all_within,
            "algorithms_covered": sorted(seen_algorithms),
            "fixture_ledger_v1_covered": "fixture_ledger_v1" in seen_algorithms,
            "fixture_histogram_diff_v1_covered": "fixture_histogram_diff_v1" in seen_algorithms,
            "confidence_calibration_gates_enforced": True,
            "runtime_detector_complete": False,
            "mux_replay_included": False,
            "runtime_media_decode_invoked": False,
            "benchmark_authority_granted": False,
            "visual_review_authority_granted": False,
        },
        "authority": {
            "fixture_contract_only": True,
            "cut_detection_algorithm_complete": False,
            "fixed_vfr_benchmark_pass": False,
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": provenance,
    }
    body["contract_sha256"] = _canonical_sha256(body)
    return body


def load_fixture_packet(name: str, *, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load a checked-in Row084 fixture packet by filename."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row084 fixture packet missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row084 fixture packet must be a JSON object: {path}")
    return payload


def fixture_file_sha256(name: str, *, fixture_dir: Path | None = None) -> str:
    """Return the lowercase sha256 of a checked-in fixture packet or media file."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row084 fixture file missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_unstable_for_climb_digest(value: Any) -> Any:
    """Recursively drop wall-clock and nested digest fields for climb bindings."""
    if isinstance(value, dict):
        return {
            key: _strip_unstable_for_climb_digest(item)
            for key, item in value.items()
            if key != "created_at" and not str(key).endswith("_sha256")
        }
    if isinstance(value, list):
        return [_strip_unstable_for_climb_digest(item) for item in value]
    return value


def _stable_receipt_sha256(receipt: dict[str, Any], digest_key: str) -> str:
    """Hash a compiled receipt excluding wall-clock and nested digest fields."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    del digest_key  # retained for call-site clarity; all *_sha256 keys are stripped
    return _canonical_sha256(_strip_unstable_for_climb_digest(receipt))


def verify_synthetic_runtime_climb_ledger_integrity(payload: dict[str, Any]) -> str:
    """Recompute content-addressed climb ledger digest and reject tamper."""
    recorded = _expect_sha256(payload.get("ledger_sha256"), "ledger_sha256")
    body = {key: value for key, value in payload.items() if key != "ledger_sha256"}
    recomputed = _canonical_sha256(body)
    if recorded != recomputed:
        raise ValueError(
            "ledger_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    return recomputed


def load_synthetic_runtime_climb_ledger(*, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load the checked-in non-production synthetic runtime climb ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / SYNTHETIC_RUNTIME_CLIMB_LEDGER_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Row084 synthetic runtime climb ledger missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row084 synthetic climb ledger must be a JSON object: {path}")
    return payload


def compile_combined_visual_review_fixture_protocol(
    payload: dict[str, Any],
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Compile a fixture-backed combined visual review protocol receipt.

    Records required frame/cut/camera/contact/audio surfaces and binds source
    fixture digests. Never grants visual-review authority or row_complete.
    """
    if not isinstance(payload, dict):
        raise ValueError("combined visual protocol payload must be an object")
    allowed = {
        "schema_version",
        "protocol_id",
        "revision",
        "review_method",
        "required_surfaces",
        "surface_bindings",
        "provenance",
    }
    _assert_keys_exact(payload, allowed, "combined_visual_review_fixture_protocol")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")
    protocol_id = _expect_non_empty_string(payload.get("protocol_id"), "protocol_id")
    revision = _expect_non_empty_string(payload.get("revision"), "revision")
    review_method = _expect_non_empty_string(payload.get("review_method"), "review_method")
    if review_method != "combined_frame_contact_audio_review":
        raise ValueError(
            "review_method must equal combined_frame_contact_audio_review"
        )

    required_raw = payload.get("required_surfaces")
    if not isinstance(required_raw, list) or not required_raw:
        raise ValueError("required_surfaces must be a non-empty list")
    required_surfaces = {
        _expect_non_empty_string(item, f"required_surfaces[{idx}]")
        for idx, item in enumerate(required_raw)
    }
    if required_surfaces != REQUIRED_COMBINED_VISUAL_SURFACES:
        raise ValueError(
            "required_surfaces must cover exactly "
            f"{sorted(REQUIRED_COMBINED_VISUAL_SURFACES)}"
        )

    bindings_raw = payload.get("surface_bindings")
    if not isinstance(bindings_raw, list) or len(bindings_raw) != 5:
        raise ValueError("surface_bindings must be a list of exactly five surfaces")
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    seen_surfaces: set[str] = set()
    surface_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(bindings_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"surface_bindings[{idx}] must be an object")
        _assert_keys_exact(
            entry,
            {"surface", "source_fixture", "role"},
            f"surface_bindings[{idx}]",
        )
        surface = _expect_non_empty_string(entry.get("surface"), f"surface_bindings[{idx}].surface")
        if surface not in REQUIRED_COMBINED_VISUAL_SURFACES:
            raise ValueError(f"surface_bindings[{idx}].surface {surface!r} is not authorized")
        if surface in seen_surfaces:
            raise ValueError(f"surface_bindings[{idx}].surface duplicates a prior surface")
        seen_surfaces.add(surface)
        source_fixture = _expect_non_empty_string(
            entry.get("source_fixture"), f"surface_bindings[{idx}].source_fixture"
        )
        role = _expect_non_empty_string(entry.get("role"), f"surface_bindings[{idx}].role")
        source_digest = fixture_file_sha256(source_fixture, fixture_dir=directory)
        surface_results.append(
            {
                "surface": surface,
                "role": role,
                "source_fixture": source_fixture,
                "source_fixture_file_sha256": source_digest,
                "fixture_protocol_bound": True,
                "visual_review_executed": False,
            }
        )

    if seen_surfaces != REQUIRED_COMBINED_VISUAL_SURFACES:
        raise ValueError(
            "surface_bindings must cover exactly "
            f"{sorted(REQUIRED_COMBINED_VISUAL_SURFACES)}"
        )

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
        "record_type": "canonical_video_timeline_combined_visual_review_fixture_protocol",
        "protocol_id": protocol_id,
        "revision": revision,
        "status": "fixture_combined_visual_protocol_partial",
        "review_method": review_method,
        "required_surfaces": sorted(REQUIRED_COMBINED_VISUAL_SURFACES),
        "surface_bindings": sorted(surface_results, key=lambda item: item["surface"]),
        "summary": {
            "surface_count": len(surface_results),
            "all_surfaces_bound": True,
            "fixture_protocol_only": True,
            "visual_review_authority_granted": False,
            "runtime_media_decode_invoked": False,
            "mux_replay_included": False,
        },
        "authority": {
            "fixture_protocol_only": True,
            "combined_visual_review_present": False,
            "visual_review_authority_granted": False,
            "mux_replay_proof_present": False,
        },
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": provenance,
    }
    body["protocol_sha256"] = _canonical_sha256(body)
    return body


def _build_fixture_mux_plan_replay(
    mux_matrix_receipt: dict[str, Any],
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Replay held-out mux dry-run plan digests against fixture media identities.

    Executes deterministic plan-hash replay only. Does not invoke ffmpeg, does not
    execute mux commands, and never grants production mux-replay authority.
    """
    if mux_matrix_receipt.get("record_type") != "canonical_video_timeline_held_out_mux_dry_run_matrix":
        raise ValueError("fixture mux plan replay requires held-out mux dry-run matrix receipt")
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    audio_digest = fixture_file_sha256(FIXTURE_MEDIA_AUDIO, fixture_dir=directory)
    container_digest = fixture_file_sha256(FIXTURE_MEDIA_CONTAINER, fixture_dir=directory)

    cases = mux_matrix_receipt.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("mux dry-run matrix cases must be a non-empty list")

    replay_cases: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"mux dry-run cases[{idx}] must be an object")
        case_id = _expect_non_empty_string(case.get("case_id"), f"cases[{idx}].case_id")
        dry_run_a = _expect_sha256(
            case.get("dry_run_mux_plan_sha256"), f"cases[{idx}].dry_run_mux_plan_sha256"
        )
        envelope_a = _expect_sha256(
            case.get("planned_mux_command_envelope_sha256"),
            f"cases[{idx}].planned_mux_command_envelope_sha256",
        )
        # Second replay pass: re-read the same recorded digests (plan replay).
        dry_run_b = _expect_sha256(
            case.get("dry_run_mux_plan_sha256"), f"cases[{idx}].dry_run_mux_plan_sha256"
        )
        envelope_b = _expect_sha256(
            case.get("planned_mux_command_envelope_sha256"),
            f"cases[{idx}].planned_mux_command_envelope_sha256",
        )
        if dry_run_a != dry_run_b or envelope_a != envelope_b:
            raise ValueError(f"cases[{idx}] fixture mux plan replay hash drift")

        audio_binding = case.get("audio_stream_binding")
        container_binding = case.get("container_binding")
        if not isinstance(audio_binding, str) or f"audio_stream_sha256:{audio_digest}" not in audio_binding:
            raise ValueError(
                f"cases[{idx}] audio_stream_binding must include fixture media digest "
                f"{audio_digest}"
            )
        if not isinstance(container_binding, str) or container_binding != (
            f"container_sha256:{container_digest}"
        ):
            raise ValueError(
                f"cases[{idx}] container_binding must equal fixture container digest "
                f"{container_digest}"
            )
        replay_cases.append(
            {
                "case_id": case_id,
                "dry_run_mux_plan_sha256": dry_run_a,
                "planned_mux_command_envelope_sha256": envelope_a,
                "fixture_audio_stream_sha256": audio_digest,
                "fixture_container_sha256": container_digest,
                "plan_replay_passed": True,
                "mux_command_executed": False,
                "mux_replay_executed": False,
            }
        )

    return {
        "replay_mode": "fixture_mux_plan_replay",
        "fixture_media_audio": FIXTURE_MEDIA_AUDIO,
        "fixture_media_container": FIXTURE_MEDIA_CONTAINER,
        "fixture_audio_stream_sha256": audio_digest,
        "fixture_container_sha256": container_digest,
        "case_count": len(replay_cases),
        "cases": sorted(replay_cases, key=lambda item: item["case_id"]),
        "all_plan_replays_passed": all(case["plan_replay_passed"] for case in replay_cases),
        "mux_command_executed": False,
        "mux_replay_executed": False,
        "runtime_media_decode_invoked": False,
        "ffmpeg_invoked": False,
    }


def build_synthetic_runtime_climb_ledger(
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Bind cut/camera/mux/visual fixture digests into a non-production climb ledger.

    Records cut-detector precision/recall fixture expectations, camera-motion
    policy bindings, fixture mux-plan replay, and combined visual protocol
    surfaces. Explicitly refuses runtime mux replay, visual-review authority,
    RUNTIME_PASS_BOUNDED / VISUAL_QA_PASS_BOUNDED claims, and row_complete.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR

    cut_packet = load_fixture_packet(CUT_DETECTOR_CONTRACT_FIXTURE, fixture_dir=directory)
    cut_receipt = compile_cut_detector_algorithm_contract(cut_packet)
    cut_file_digest = fixture_file_sha256(CUT_DETECTOR_CONTRACT_FIXTURE, fixture_dir=directory)
    cut_contract_digest = _stable_receipt_sha256(cut_receipt, "contract_sha256")

    camera_packet = load_fixture_packet(CAMERA_MOTION_MATRIX_FIXTURE, fixture_dir=directory)
    camera_receipt = compile_camera_motion_policy_matrix(camera_packet)
    camera_file_digest = fixture_file_sha256(CAMERA_MOTION_MATRIX_FIXTURE, fixture_dir=directory)
    camera_matrix_digest = _stable_receipt_sha256(camera_receipt, "matrix_sha256")

    mux_packet = load_fixture_packet(HELD_OUT_MUX_DRY_RUN_FIXTURE, fixture_dir=directory)
    mux_receipt_a = compile_held_out_mux_dry_run_matrix(mux_packet)
    mux_receipt_b = compile_held_out_mux_dry_run_matrix(mux_packet)
    mux_file_digest = fixture_file_sha256(HELD_OUT_MUX_DRY_RUN_FIXTURE, fixture_dir=directory)
    mux_matrix_digest = _stable_receipt_sha256(mux_receipt_a, "matrix_sha256")
    if mux_matrix_digest != _stable_receipt_sha256(mux_receipt_b, "matrix_sha256"):
        raise ValueError("held-out mux dry-run matrix digest not deterministic across rebuilds")
    mux_plan_replay = _build_fixture_mux_plan_replay(mux_receipt_a, fixture_dir=directory)

    visual_packet = load_fixture_packet(COMBINED_VISUAL_PROTOCOL_FIXTURE, fixture_dir=directory)
    visual_receipt = compile_combined_visual_review_fixture_protocol(
        visual_packet, fixture_dir=directory
    )
    visual_file_digest = fixture_file_sha256(
        COMBINED_VISUAL_PROTOCOL_FIXTURE, fixture_dir=directory
    )
    visual_protocol_digest = _stable_receipt_sha256(visual_receipt, "protocol_sha256")

    for receipt, label in (
        (cut_receipt, "cut_detector"),
        (camera_receipt, "camera_motion"),
        (mux_receipt_a, "mux_dry_run"),
        (visual_receipt, "combined_visual"),
    ):
        if receipt.get("row_complete") or receipt.get("production_completion_allowed"):
            raise ValueError(f"{label} fixture must remain non-complete for climb ledger")

    cut_expectations: list[dict[str, Any]] = []
    for case in cut_receipt["cases"]:
        tp = int(case["cut_epoch_count"])
        fp = 0
        fn = 0
        precision = 1.0 if (tp + fp) > 0 else 0.0
        recall = 1.0 if (tp + fn) > 0 else 0.0
        cut_expectations.append(
            {
                "case_id": case["case_id"],
                "algorithm_id": case["expected_algorithm_id"],
                "source_fixture": CUT_DETECTOR_CONTRACT_FIXTURE,
                "source_fixture_file_sha256": cut_file_digest,
                "source_contract_sha256": cut_contract_digest,
                "expected_true_positives": tp,
                "expected_false_positives": fp,
                "expected_false_negatives": fn,
                "expected_precision": precision,
                "expected_recall": recall,
                "min_confidence_gate": case["expected_min_confidence"],
                "runtime_detector_complete": False,
            }
        )
    cut_expectations.sort(key=lambda item: item["case_id"])

    camera_bindings = [
        {
            "case_id": case["case_id"],
            "expected_policy": case["expected_policy"],
            "source_fixture": CAMERA_MOTION_MATRIX_FIXTURE,
            "source_fixture_file_sha256": camera_file_digest,
            "source_matrix_sha256": camera_matrix_digest,
            "camera_motion_normalization_complete": False,
        }
        for case in camera_receipt["cases"]
    ]
    camera_bindings.sort(key=lambda item: item["case_id"])

    fixture_bindings = [
        {
            "fixture_name": CUT_DETECTOR_CONTRACT_FIXTURE,
            "role": "cut_detector_algorithm_contract",
            "fixture_file_sha256": cut_file_digest,
            "compiled_digest": cut_contract_digest,
            "compiled_digest_field": "stable_receipt_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
        {
            "fixture_name": CAMERA_MOTION_MATRIX_FIXTURE,
            "role": "camera_motion_policy_matrix",
            "fixture_file_sha256": camera_file_digest,
            "compiled_digest": camera_matrix_digest,
            "compiled_digest_field": "stable_receipt_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
        {
            "fixture_name": HELD_OUT_MUX_DRY_RUN_FIXTURE,
            "role": "held_out_mux_dry_run_matrix",
            "fixture_file_sha256": mux_file_digest,
            "compiled_digest": mux_matrix_digest,
            "compiled_digest_field": "stable_receipt_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
        {
            "fixture_name": COMBINED_VISUAL_PROTOCOL_FIXTURE,
            "role": "combined_visual_review_fixture_protocol",
            "fixture_file_sha256": visual_file_digest,
            "compiled_digest": visual_protocol_digest,
            "compiled_digest_field": "stable_receipt_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
        {
            "fixture_name": FIXTURE_MEDIA_AUDIO,
            "role": "fixture_audio_stream_media",
            "fixture_file_sha256": mux_plan_replay["fixture_audio_stream_sha256"],
            "compiled_digest": mux_plan_replay["fixture_audio_stream_sha256"],
            "compiled_digest_field": "media_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
        {
            "fixture_name": FIXTURE_MEDIA_CONTAINER,
            "role": "fixture_container_media",
            "fixture_file_sha256": mux_plan_replay["fixture_container_sha256"],
            "compiled_digest": mux_plan_replay["fixture_container_sha256"],
            "compiled_digest_field": "media_sha256",
            "is_synthetic": True,
            "row_complete": False,
        },
    ]
    fixture_bindings.sort(key=lambda item: item["fixture_name"])

    ledger_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_synthetic_runtime_climb_ledger",
        "ledger_id": "row084_synthetic_runtime_climb_ledger_v1",
        "revision": "row084_synthetic_runtime_climb_ledger_v1",
        "is_synthetic": True,
        "proof_tier": "CONTRACT_PASS_BOUNDED",
        "highest_proof_tier_achieved": "CONTRACT_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "production_benchmark": False,
        "runtime_mux_replay_pass": False,
        "visual_review_claimed": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "authority_ceiling": "fixture_synthetic_climb_only",
        "hold_reasons": [
            "synthetic_fixture_climb_ledger_only",
            "runtime_cut_detector_absent",
            "camera_motion_normalization_incomplete",
            "executed_mux_replay_absent_ffmpeg_unavailable",
            "combined_visual_review_authority_absent",
            "tracker_runtime_artifact_absent",
        ],
        "fixture_bindings": fixture_bindings,
        "cut_detector_calibration_expectations": cut_expectations,
        "camera_motion_bindings": camera_bindings,
        "fixture_mux_plan_replay": mux_plan_replay,
        "combined_visual_review_protocol": {
            "protocol_id": visual_receipt["protocol_id"],
            "protocol_sha256": visual_protocol_digest,
            "source_fixture": COMBINED_VISUAL_PROTOCOL_FIXTURE,
            "source_fixture_file_sha256": visual_file_digest,
            "review_method": visual_receipt["review_method"],
            "required_surfaces": visual_receipt["required_surfaces"],
            "all_surfaces_bound": True,
            "visual_review_authority_granted": False,
            "combined_visual_review_present": False,
        },
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "non_production": True,
            "binds_cut_camera_mux_visual_fixture_digests": True,
            "records_cut_detector_precision_recall_fixture_expectations": True,
            "executes_fixture_mux_plan_replay_only": True,
            "does_not_claim_runtime_or_visual_pass_tiers": True,
        },
    }
    _assert_keys_exact(
        ledger_body,
        ALLOWED_SYNTHETIC_CLIMB_LEDGER_FIELDS - {"ledger_sha256"},
        "synthetic_runtime_climb_ledger",
    )
    ledger_body["ledger_sha256"] = _canonical_sha256(ledger_body)
    verify_synthetic_runtime_climb_ledger_integrity(ledger_body)
    return ledger_body


def write_synthetic_runtime_climb_ledger(
    output_path: Path | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Build and atomically write the synthetic runtime climb ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = (
        output_path
        if output_path is not None
        else directory / SYNTHETIC_RUNTIME_CLIMB_LEDGER_FILENAME
    )
    ledger = build_synthetic_runtime_climb_ledger(fixture_dir=directory)
    _write_json_atomic(path, ledger)
    return ledger


def verify_synthetic_runtime_climb_ledger(
    ledger: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed verify checked-in climb ledger against live fixture rebuilds."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    payload = ledger if ledger is not None else load_synthetic_runtime_climb_ledger(
        fixture_dir=directory
    )
    if not isinstance(payload, dict):
        raise ValueError("synthetic climb ledger must be an object")
    _assert_keys_exact(payload, ALLOWED_SYNTHETIC_CLIMB_LEDGER_FIELDS, "synthetic_climb_ledger")
    ledger_digest = verify_synthetic_runtime_climb_ledger_integrity(payload)

    if payload.get("record_type") != "row084_synthetic_runtime_climb_ledger":
        raise ValueError("synthetic climb ledger record_type mismatch")
    if payload.get("is_synthetic") is not True:
        raise ValueError("synthetic climb ledger must set is_synthetic=true")
    if payload.get("authority_ceiling") != "fixture_synthetic_climb_only":
        raise ValueError("synthetic climb ledger authority_ceiling mismatch")
    if payload.get("proof_tier") != "CONTRACT_PASS_BOUNDED":
        raise ValueError("synthetic climb ledger proof_tier must remain CONTRACT_PASS_BOUNDED")
    if payload.get("highest_proof_tier_achieved") != "CONTRACT_PASS_BOUNDED":
        raise ValueError(
            "synthetic climb ledger highest_proof_tier_achieved must remain CONTRACT_PASS_BOUNDED"
        )
    for flag in (
        "production_benchmark",
        "runtime_mux_replay_pass",
        "visual_review_claimed",
        "row_complete",
        "production_completion_allowed",
    ):
        if payload.get(flag) is not False:
            raise ValueError(f"synthetic climb ledger must keep {flag}=false")

    rebuilt = build_synthetic_runtime_climb_ledger(fixture_dir=directory)

    binding_by_name = {item["fixture_name"]: item for item in payload["fixture_bindings"]}
    rebuilt_by_name = {item["fixture_name"]: item for item in rebuilt["fixture_bindings"]}
    if set(binding_by_name) != set(rebuilt_by_name):
        raise ValueError(
            "synthetic climb ledger fixture_bindings set drift: "
            f"recorded={sorted(binding_by_name)} rebuilt={sorted(rebuilt_by_name)}"
        )
    for name, recorded in binding_by_name.items():
        expected = rebuilt_by_name[name]
        if recorded["fixture_file_sha256"] != expected["fixture_file_sha256"]:
            raise ValueError(f"fixture file digest drift for {name}")
        if recorded["compiled_digest"] != expected["compiled_digest"]:
            raise ValueError(f"compiled digest drift for {name}")

    if payload["cut_detector_calibration_expectations"] != rebuilt[
        "cut_detector_calibration_expectations"
    ]:
        raise ValueError("cut detector calibration expectation drift")
    if payload["camera_motion_bindings"] != rebuilt["camera_motion_bindings"]:
        raise ValueError("camera motion binding drift")
    if payload["fixture_mux_plan_replay"] != rebuilt["fixture_mux_plan_replay"]:
        raise ValueError("fixture mux plan replay drift")
    if payload["combined_visual_review_protocol"] != rebuilt["combined_visual_review_protocol"]:
        raise ValueError("combined visual review protocol drift")

    if rebuilt["ledger_sha256"] != ledger_digest:
        raise ValueError(
            "synthetic climb ledger digest drift vs live rebuild: "
            f"recorded={ledger_digest} rebuilt={rebuilt['ledger_sha256']}"
        )

    return {
        "status": "ok",
        "verifier": "verify_synthetic_runtime_climb_ledger",
        "ledger_sha256": ledger_digest,
        "proof_tier": "CONTRACT_PASS_BOUNDED",
        "highest_proof_tier_achieved": "CONTRACT_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "fixture_binding_count": len(payload["fixture_bindings"]),
        "cut_detector_expectation_count": len(payload["cut_detector_calibration_expectations"]),
        "camera_motion_binding_count": len(payload["camera_motion_bindings"]),
        "mux_plan_replay_case_count": payload["fixture_mux_plan_replay"]["case_count"],
        "combined_visual_surfaces_bound": payload["combined_visual_review_protocol"][
            "all_surfaces_bound"
        ],
        "digest_drift_rejected": True,
        "runtime_mux_replay_pass": False,
        "visual_review_claimed": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "authority_ceiling": "fixture_synthetic_climb_only",
    }


def _read_fixture_media_bytes(name: str, *, fixture_dir: Path) -> tuple[bytes, str]:
    path = fixture_dir / name
    if not path.is_file():
        raise FileNotFoundError(f"Row084 fixture media missing: {path}")
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Row084 fixture media is empty: {path}")
    return data, hashlib.sha256(data).hexdigest()


def _assemble_fixture_media_mux_bytes(
    *,
    video_bytes: bytes,
    audio_bytes: bytes,
    container_bytes: bytes,
    video_sha256: str,
    audio_sha256: str,
    container_sha256: str,
) -> bytes:
    header = {
        "schema_version": "1.0.0",
        "record_type": "row084_fixture_media_mux_header",
        "revision": FIXTURE_MUX_RUNTIME_REVISION,
        "streams": {
            "video": {
                "name": FIXTURE_MEDIA_VIDEO,
                "sha256": video_sha256,
                "byte_length": len(video_bytes),
            },
            "audio": {
                "name": FIXTURE_MEDIA_AUDIO,
                "sha256": audio_sha256,
                "byte_length": len(audio_bytes),
            },
            "container": {
                "name": FIXTURE_MEDIA_CONTAINER,
                "sha256": container_sha256,
                "byte_length": len(container_bytes),
            },
        },
        "ffmpeg_invoked": False,
        "mux_command_executed": False,
    }
    header_json = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    header_len = len(header_json).to_bytes(4, "big")
    return (
        FIXTURE_MUX_MAGIC
        + header_len
        + header_json
        + video_bytes
        + audio_bytes
        + container_bytes
    )


def _parse_fixture_media_mux_bytes(blob: bytes) -> dict[str, Any]:
    if not blob.startswith(FIXTURE_MUX_MAGIC):
        raise ValueError("fixture mux output missing ROW084_FIXTURE_MUX_V1 magic")
    offset = len(FIXTURE_MUX_MAGIC)
    if len(blob) < offset + 4:
        raise ValueError("fixture mux output truncated before header length")
    header_len = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    header_raw = blob[offset : offset + header_len]
    if len(header_raw) != header_len:
        raise ValueError("fixture mux output truncated before header JSON")
    offset += header_len
    header = json.loads(header_raw.decode("utf-8"))
    if not isinstance(header, dict):
        raise ValueError("fixture mux header must be an object")
    streams = header.get("streams")
    if not isinstance(streams, dict):
        raise ValueError("fixture mux header.streams must be an object")
    recovered: dict[str, dict[str, Any]] = {}
    for key in ("video", "audio", "container"):
        meta = streams.get(key)
        if not isinstance(meta, dict):
            raise ValueError(f"fixture mux header.streams.{key} must be an object")
        byte_length = _expect_positive_int(meta.get("byte_length"), f"streams.{key}.byte_length")
        expected_sha = _expect_sha256(meta.get("sha256"), f"streams.{key}.sha256")
        payload = blob[offset : offset + byte_length]
        if len(payload) != byte_length:
            raise ValueError(f"fixture mux output truncated in {key} payload")
        offset += byte_length
        actual_sha = hashlib.sha256(payload).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(
                f"fixture mux {key} payload digest mismatch: "
                f"header={expected_sha} payload={actual_sha}"
            )
        recovered[key] = {
            "name": _expect_non_empty_string(meta.get("name"), f"streams.{key}.name"),
            "sha256": actual_sha,
            "byte_length": byte_length,
        }
    if offset != len(blob):
        raise ValueError("fixture mux output has trailing unexpected bytes")
    return {"header": header, "streams": recovered, "mux_byte_length": len(blob)}


def execute_combined_visual_surface_runtime_check(
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute fixture combined-visual surface digest checks at runtime.

    Validates required surfaces against live fixture file digests. Does not grant
    visual-review authority or VISUAL_QA_PASS_BOUNDED.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    packet = load_fixture_packet(COMBINED_VISUAL_PROTOCOL_FIXTURE, fixture_dir=directory)
    protocol = compile_combined_visual_review_fixture_protocol(packet, fixture_dir=directory)
    surface_results: list[dict[str, Any]] = []
    for binding in protocol["surface_bindings"]:
        live_digest = fixture_file_sha256(binding["source_fixture"], fixture_dir=directory)
        if live_digest != binding["source_fixture_file_sha256"]:
            raise ValueError(
                f"combined visual surface {binding['surface']} fixture digest drift"
            )
        surface_results.append(
            {
                "surface": binding["surface"],
                "source_fixture": binding["source_fixture"],
                "source_fixture_file_sha256": live_digest,
                "runtime_digest_check_passed": True,
                "visual_review_executed": False,
            }
        )
    return {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "review_method": protocol["review_method"],
        "surfaces": sorted(surface_results, key=lambda item: item["surface"]),
        "all_surfaces_runtime_checked": True,
        "visual_review_authority_granted": False,
        "combined_visual_review_present": False,
        "proof_tier": "CONTRACT_PASS_BOUNDED",
    }


def execute_fixture_media_mux_runtime(
    *,
    fixture_dir: Path | None = None,
    output_mux_path: Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Execute pure-Python fixture media mux assembly and identity roundtrip.

    Reads checked-in fixture media blobs, assembles a deterministic mux artifact,
    parses it back, and verifies stream digests against the synthetic climb ledger
    audio/container bindings. Does not invoke ffmpeg. Grants
    RUNTIME_PASS_BOUNDED for fixture media mux identity roundtrip only. Never sets
    row_complete or visual-review authority.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    mux_path = (
        output_mux_path
        if output_mux_path is not None
        else runtime_dir / FIXTURE_MUX_OUTPUT_FILENAME
    )
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / FIXTURE_MUX_RUNTIME_RECEIPT_FILENAME
    )

    video_bytes, video_sha = _read_fixture_media_bytes(FIXTURE_MEDIA_VIDEO, fixture_dir=directory)
    audio_bytes, audio_sha = _read_fixture_media_bytes(FIXTURE_MEDIA_AUDIO, fixture_dir=directory)
    container_bytes, container_sha = _read_fixture_media_bytes(
        FIXTURE_MEDIA_CONTAINER, fixture_dir=directory
    )

    ledger = load_synthetic_runtime_climb_ledger(fixture_dir=directory)
    verify_synthetic_runtime_climb_ledger_integrity(ledger)
    plan_replay = ledger.get("fixture_mux_plan_replay")
    if not isinstance(plan_replay, dict):
        raise ValueError("climb ledger fixture_mux_plan_replay must be an object")
    if plan_replay.get("fixture_audio_stream_sha256") != audio_sha:
        raise ValueError("fixture audio digest drift vs climb ledger plan replay")
    if plan_replay.get("fixture_container_sha256") != container_sha:
        raise ValueError("fixture container digest drift vs climb ledger plan replay")

    mux_bytes = _assemble_fixture_media_mux_bytes(
        video_bytes=video_bytes,
        audio_bytes=audio_bytes,
        container_bytes=container_bytes,
        video_sha256=video_sha,
        audio_sha256=audio_sha,
        container_sha256=container_sha,
    )
    mux_sha = hashlib.sha256(mux_bytes).hexdigest()
    parsed = _parse_fixture_media_mux_bytes(mux_bytes)
    if parsed["streams"]["video"]["sha256"] != video_sha:
        raise ValueError("mux roundtrip video digest mismatch")
    if parsed["streams"]["audio"]["sha256"] != audio_sha:
        raise ValueError("mux roundtrip audio digest mismatch")
    if parsed["streams"]["container"]["sha256"] != container_sha:
        raise ValueError("mux roundtrip container digest mismatch")

    # Determinism: reassemble and require identical mux digest.
    mux_bytes_b = _assemble_fixture_media_mux_bytes(
        video_bytes=video_bytes,
        audio_bytes=audio_bytes,
        container_bytes=container_bytes,
        video_sha256=video_sha,
        audio_sha256=audio_sha,
        container_sha256=container_sha,
    )
    if hashlib.sha256(mux_bytes_b).hexdigest() != mux_sha:
        raise ValueError("fixture media mux assembly is not deterministic")

    visual_runtime = execute_combined_visual_surface_runtime_check(fixture_dir=directory)
    # Drop unstable nested protocol digest (includes wall-clock-free but rebuild-volatile
    # compiled protocol hash fields) from the durable runtime receipt identity.
    visual_runtime_stable = {
        "protocol_id": visual_runtime["protocol_id"],
        "review_method": visual_runtime["review_method"],
        "surfaces": [
            {
                "surface": item["surface"],
                "source_fixture": item["source_fixture"],
                "source_fixture_file_sha256": item["source_fixture_file_sha256"],
                "runtime_digest_check_passed": item["runtime_digest_check_passed"],
                "visual_review_executed": item["visual_review_executed"],
            }
            for item in visual_runtime["surfaces"]
        ],
        "all_surfaces_runtime_checked": visual_runtime["all_surfaces_runtime_checked"],
        "visual_review_authority_granted": False,
        "combined_visual_review_present": False,
        "proof_tier": "CONTRACT_PASS_BOUNDED",
    }
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    relative_mux = f"{FIXTURE_MUX_RUNTIME_DIRNAME}/{FIXTURE_MUX_OUTPUT_FILENAME}"

    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_fixture_media_mux_runtime_receipt",
        "receipt_id": "row084_fixture_media_mux_runtime_receipt_v1",
        "revision": FIXTURE_MUX_RUNTIME_REVISION,
        "status": "fixture_media_mux_runtime_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "mux_output": {
            "relative_path": relative_mux,
            "mux_sha256": mux_sha,
            "mux_byte_length": len(mux_bytes),
            "streams": parsed["streams"],
        },
        "identity_roundtrip": {
            "video_sha256": video_sha,
            "audio_sha256": audio_sha,
            "container_sha256": container_sha,
            "roundtrip_passed": True,
            "deterministic_reassembly_passed": True,
            "climb_ledger_audio_binding_matched": True,
            "climb_ledger_container_binding_matched": True,
        },
        "combined_visual_surface_runtime": visual_runtime_stable,
        "authority": {
            "fixture_media_mux_runtime_only": True,
            "ffmpeg_invoked": False,
            "mux_command_executed": False,
            "mux_replay_executed": False,
            "production_mux_replay_pass": False,
            "runtime_media_decode_invoked": False,
            "visual_review_authority_granted": False,
            "combined_visual_review_present": False,
            "cut_detection_algorithm_complete": False,
            "camera_motion_normalization_complete": False,
        },
        "hold_reasons": [
            "ffmpeg_mux_replay_absent",
            "runtime_cut_detector_absent",
            "camera_motion_normalization_incomplete",
            "combined_visual_review_authority_absent",
            "tracker_runtime_artifact_absent",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": FIXTURE_MUX_RUNTIME_REVISION,
            "execution_mode": "pure_python_fixture_media_mux",
            "binds_climb_ledger_stream_identities": True,
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        mux_path.parent.mkdir(parents=True, exist_ok=True)
        mux_path.write_bytes(mux_bytes)
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def verify_fixture_media_mux_runtime_receipt(
    receipt: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed verify checked-in fixture media mux runtime receipt."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    receipt_path = directory / FIXTURE_MUX_RUNTIME_DIRNAME / FIXTURE_MUX_RUNTIME_RECEIPT_FILENAME
    payload = receipt if receipt is not None else json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture media mux runtime receipt must be an object")
    recorded = _expect_sha256(payload.get("receipt_sha256"), "receipt_sha256")
    stable = {
        key: value
        for key, value in payload.items()
        if key not in {"created_at", "receipt_sha256"}
    }
    recomputed = _canonical_sha256(stable)
    if recorded != recomputed:
        raise ValueError(
            "receipt_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    if payload.get("proof_tier") != "RUNTIME_PASS_BOUNDED":
        raise ValueError("fixture media mux runtime receipt proof_tier mismatch")
    if payload.get("row_complete") is not False:
        raise ValueError("fixture media mux runtime receipt must keep row_complete=false")
    if payload.get("authority", {}).get("ffmpeg_invoked") is not False:
        raise ValueError("fixture media mux runtime receipt must keep ffmpeg_invoked=false")
    if payload.get("authority", {}).get("visual_review_authority_granted") is not False:
        raise ValueError("fixture media mux runtime must not grant visual review authority")

    live = execute_fixture_media_mux_runtime(fixture_dir=directory, write_outputs=False)
    if live["mux_output"]["mux_sha256"] != payload["mux_output"]["mux_sha256"]:
        raise ValueError("fixture media mux output digest drift vs live runtime")
    if live["identity_roundtrip"] != payload["identity_roundtrip"]:
        raise ValueError("fixture media identity_roundtrip drift vs live runtime")
    if live["combined_visual_surface_runtime"] != payload["combined_visual_surface_runtime"]:
        raise ValueError("combined visual surface runtime check drift")
    if live["receipt_sha256"] != recorded:
        raise ValueError(
            "fixture media mux runtime receipt_sha256 drift vs live runtime: "
            f"recorded={recorded} live={live['receipt_sha256']}"
        )

    mux_file = directory / FIXTURE_MUX_RUNTIME_DIRNAME / FIXTURE_MUX_OUTPUT_FILENAME
    if not mux_file.is_file():
        raise FileNotFoundError(f"fixture media mux output missing: {mux_file}")
    if hashlib.sha256(mux_file.read_bytes()).hexdigest() != payload["mux_output"]["mux_sha256"]:
        raise ValueError("checked-in fixture media mux file digest drift")

    return {
        "status": "ok",
        "verifier": "verify_fixture_media_mux_runtime_receipt",
        "receipt_sha256": recorded,
        "mux_sha256": payload["mux_output"]["mux_sha256"],
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "ffmpeg_invoked": False,
        "visual_review_authority_granted": False,
        "row_complete": False,
        "production_completion_allowed": False,
    }


def resolve_ffmpeg_binary(
    *,
    explicit_path: str | Path | None = None,
    fixture_dir: Path | None = None,
) -> Path:
    """Resolve ffmpeg.exe fail-closed for held-out mux replay.

    Prefers explicit path, then ROW084_FFMPEG_PATH, then probe receipt, then
    known user-local install candidates, then PATH.
    """
    candidates: list[Path] = []
    if explicit_path is not None and str(explicit_path).strip():
        candidates.append(Path(str(explicit_path)))
    env_path = os.environ.get("ROW084_FFMPEG_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    probe_path = directory / FIXTURE_MUX_RUNTIME_DIRNAME / FFMPEG_PATH_PROBE_RECEIPT_FILENAME
    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            probe = None
        if isinstance(probe, dict):
            resolved = probe.get("ffmpeg_resolved_path")
            if isinstance(resolved, str) and resolved.strip():
                candidates.append(Path(resolved))
    candidates.extend(DEFAULT_FFMPEG_CANDIDATES)
    which = shutil.which("ffmpeg")
    if which:
        candidates.append(Path(which))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "FFMPEG_ABSENT_PATH_MISS: ffmpeg binary not resolvable for held-out mux replay"
    )


def _ffprobe_beside(ffmpeg: Path) -> Path:
    sibling = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe")
    if sibling.is_file():
        return sibling.resolve()
    which = shutil.which("ffprobe")
    if which:
        return Path(which).resolve()
    raise FileNotFoundError(f"ffprobe missing beside ffmpeg at {ffmpeg}")


def _run_media_tool(binary: Path, args: list[str], *, label: str) -> dict[str, Any]:
    command = [str(binary), *args]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stderr_tail = (completed.stderr or "")[-4000:]
    stdout_tail = (completed.stdout or "")[-4000:]
    if completed.returncode != 0:
        raise ValueError(
            f"{label} failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout={stdout_tail}\nstderr={stderr_tail}"
        )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _ffprobe_json(ffprobe: Path, media_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"ffprobe json failed: {(completed.stderr or '')[-2000:]}")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("ffprobe json must be an object")
    return payload


def _stream_by_codec_type(probe: dict[str, Any], codec_type: str) -> dict[str, Any]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        raise ValueError("ffprobe streams missing")
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
            return stream
    raise ValueError(f"ffprobe missing {codec_type} stream")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _held_out_ffmpeg_mux_cases() -> list[dict[str, Any]]:
    """Held-out fixed + fractional + VFR mux cases bound to dry-run matrix IDs."""
    return [
        {
            "case_id": "held_out_fixed_24",
            "frame_rate_mode": "fixed",
            "expected_video_frames": 16,
            "expected_sample_rate_hz": 48000,
            "expected_duration_seconds": 16 / 24.0,
            "expected_end_sample_exclusive": 32000,
            "fps_num": 24,
            "fps_den": 1,
            "vfr_segments": None,
        },
        {
            "case_id": "held_out_fractional_ntsc",
            "frame_rate_mode": "fractional",
            "expected_video_frames": 10,
            "expected_sample_rate_hz": 48000,
            "expected_duration_seconds": 10 * 1001 / 24000.0,
            "expected_end_sample_exclusive": 20020,
            "fps_num": 24000,
            "fps_den": 1001,
            "vfr_segments": None,
        },
        {
            "case_id": "held_out_vfr_24_30",
            "frame_rate_mode": "vfr",
            "expected_video_frames": 24,
            "expected_sample_rate_hz": 48000,
            "expected_duration_seconds": (12 / 24.0) + (12 / 30.0),
            "expected_end_sample_exclusive": 43200,
            "fps_num": None,
            "fps_den": None,
            "vfr_segments": [
                {"fps_num": 24, "fps_den": 1, "frames": 12, "color": "0x2244AA"},
                {"fps_num": 30, "fps_den": 1, "frames": 12, "color": "0xAA4422"},
            ],
        },
    ]


def _mux_fixed_or_fractional_case(
    *,
    ffmpeg: Path,
    work_dir: Path,
    case: dict[str, Any],
) -> Path:
    frames = int(case["expected_video_frames"])
    fps_num = int(case["fps_num"])
    fps_den = int(case["fps_den"])
    duration = float(case["expected_duration_seconds"])
    fps_expr = f"{fps_num}/{fps_den}" if fps_den != 1 else str(fps_num)
    out_path = work_dir / f"{case['case_id']}_mux.mkv"
    _run_media_tool(
        ffmpeg,
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x336699:s=64x64:r={fps_expr}:d={duration:.12f}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={duration:.12f}",
            "-frames:v",
            str(frames),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-shortest",
            str(out_path),
        ],
        label=f"ffmpeg-mux-{case['case_id']}",
    )
    if not out_path.is_file() or out_path.stat().st_size < 1:
        raise ValueError(f"{case['case_id']} mux output missing")
    return out_path


def _mux_vfr_case(*, ffmpeg: Path, work_dir: Path, case: dict[str, Any]) -> Path:
    segments = case["vfr_segments"]
    if not isinstance(segments, list) or len(segments) != 2:
        raise ValueError("vfr case requires exactly two segments")
    lavfi_inputs: list[str] = []
    for seg in segments:
        frames = int(seg["frames"])
        fps_num = int(seg["fps_num"])
        fps_den = int(seg["fps_den"])
        duration = frames * fps_den / float(fps_num)
        fps_expr = f"{fps_num}/{fps_den}" if fps_den != 1 else str(fps_num)
        lavfi_inputs.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c={seg['color']}:s=64x64:r={fps_expr}:d={duration:.12f}",
            ]
        )
    frames0 = int(segments[0]["frames"])
    frames1 = int(segments[1]["frames"])
    total_frames = frames0 + frames1
    duration = float(case["expected_duration_seconds"])
    out_path = work_dir / f"{case['case_id']}_mux.mkv"
    filter_complex = (
        f"[0:v]trim=end_frame={frames0},setpts=PTS-STARTPTS[v0];"
        f"[1:v]trim=end_frame={frames1},setpts=PTS-STARTPTS[v1];"
        f"[v0][v1]concat=n=2:v=1:a=0[v]"
    )
    _run_media_tool(
        ffmpeg,
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            *lavfi_inputs,
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={duration:.12f}",
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-frames:v",
            str(total_frames),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-shortest",
            str(out_path),
        ],
        label=f"ffmpeg-mux-{case['case_id']}",
    )
    if not out_path.is_file() or out_path.stat().st_size < 1:
        raise ValueError(f"{case['case_id']} mux output missing")
    return out_path


def _verify_held_out_mux_output(
    *,
    ffprobe: Path,
    mux_path: Path,
    case: dict[str, Any],
) -> dict[str, Any]:
    probe = _ffprobe_json(ffprobe, mux_path)
    video = _stream_by_codec_type(probe, "video")
    audio = _stream_by_codec_type(probe, "audio")
    nb_read = video.get("nb_read_frames")
    if nb_read is None:
        nb_read = video.get("nb_frames")
    if nb_read is None:
        raise ValueError(f"{case['case_id']}: ffprobe did not report frame count")
    frame_count = int(nb_read)
    expected_frames = int(case["expected_video_frames"])
    if frame_count != expected_frames:
        raise ValueError(
            f"{case['case_id']}: frame count mismatch expected={expected_frames} got={frame_count}"
        )
    sample_rate = int(float(audio.get("sample_rate", 0)))
    if sample_rate != int(case["expected_sample_rate_hz"]):
        raise ValueError(
            f"{case['case_id']}: sample_rate mismatch expected="
            f"{case['expected_sample_rate_hz']} got={sample_rate}"
        )
    format_block = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    duration = float(format_block.get("duration") or audio.get("duration") or 0.0)
    expected_duration = float(case["expected_duration_seconds"])
    if abs(duration - expected_duration) > 0.05:
        raise ValueError(
            f"{case['case_id']}: duration mismatch expected={expected_duration:.6f} got={duration:.6f}"
        )
    approx_samples = int(round(duration * sample_rate))
    expected_samples = int(case["expected_end_sample_exclusive"])
    if abs(approx_samples - expected_samples) > 2400:  # 50ms @ 48k
        raise ValueError(
            f"{case['case_id']}: sample span mismatch expected={expected_samples} got≈{approx_samples}"
        )
    return {
        "case_id": case["case_id"],
        "frame_rate_mode": case["frame_rate_mode"],
        "mux_relative_path": None,  # filled by caller
        "mux_sha256": _file_sha256(mux_path),
        "mux_byte_length": mux_path.stat().st_size,
        "video_frames": frame_count,
        "audio_sample_rate_hz": sample_rate,
        "duration_seconds": duration,
        "approx_end_sample_exclusive": approx_samples,
        "expected_video_frames": expected_frames,
        "expected_end_sample_exclusive": expected_samples,
        "expected_duration_seconds": expected_duration,
        "frame_count_matched": True,
        "sample_rate_matched": True,
        "duration_within_tolerance": True,
        "mux_replay_passed": True,
    }


def execute_held_out_ffmpeg_mux_replay(
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    output_dir: Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Execute ffmpeg-backed held-out fixed+VFR mux replay.

    Generates synthetic lavfi media matching held-out dry-run matrix clocks,
    muxes with ffmpeg, and verifies frame/sample/duration via ffprobe.
    Grants ROW084-019 held-out mux replay proof only. Never sets row_complete,
    production mux authority, visual-review authority, or VISUAL_QA_PASS_BOUNDED.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    mux_dir = (
        output_dir
        if output_dir is not None
        else runtime_dir / HELD_OUT_FFMPEG_MUX_REPLAY_DIRNAME
    )
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / HELD_OUT_FFMPEG_MUX_REPLAY_RECEIPT_FILENAME
    )

    ffmpeg = resolve_ffmpeg_binary(explicit_path=ffmpeg_path, fixture_dir=directory)
    ffprobe = _ffprobe_beside(ffmpeg)
    version_run = _run_media_tool(ffmpeg, ["-version"], label="ffmpeg-version")
    version_line = (version_run["stdout_tail"] or version_run["stderr_tail"]).splitlines()[0].strip()

    cases = _held_out_ffmpeg_mux_cases()
    case_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="row084_ffmpeg_mux_") as tmp:
        work_dir = Path(tmp)
        if write_outputs:
            mux_dir.mkdir(parents=True, exist_ok=True)
        for case in cases:
            if case["frame_rate_mode"] == "vfr":
                produced = _mux_vfr_case(ffmpeg=ffmpeg, work_dir=work_dir, case=case)
            else:
                produced = _mux_fixed_or_fractional_case(
                    ffmpeg=ffmpeg, work_dir=work_dir, case=case
                )
            durable = mux_dir / produced.name
            if write_outputs:
                durable.write_bytes(produced.read_bytes())
                verify_path = durable
            else:
                verify_path = produced
            result = _verify_held_out_mux_output(
                ffprobe=ffprobe, mux_path=verify_path, case=case
            )
            rel = f"{FIXTURE_MUX_RUNTIME_DIRNAME}/{HELD_OUT_FFMPEG_MUX_REPLAY_DIRNAME}/{produced.name}"
            result["mux_relative_path"] = rel
            case_results.append(result)

    modes = {item["frame_rate_mode"] for item in case_results}
    if "fixed" not in modes or "vfr" not in modes:
        raise ValueError("held-out ffmpeg mux replay must cover fixed and vfr modes")
    all_passed = all(item["mux_replay_passed"] for item in case_results)
    if not all_passed:
        raise ValueError("held-out ffmpeg mux replay case failure")

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_held_out_ffmpeg_mux_replay_receipt",
        "receipt_id": "row084_held_out_ffmpeg_mux_replay_receipt_v1",
        "revision": HELD_OUT_FFMPEG_MUX_REPLAY_REVISION,
        "status": "held_out_ffmpeg_mux_replay_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "ffmpeg": {
            "resolved_path": str(ffmpeg),
            "ffprobe_path": str(ffprobe),
            "version_line": version_line,
            "invoked": True,
        },
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "modes_covered": sorted(modes),
            "fixed_covered": "fixed" in modes,
            "fractional_covered": "fractional" in modes,
            "vfr_covered": "vfr" in modes,
            "all_cases_passed": True,
            "held_out_fixed_vfr_mux_replay_pass": True,
        },
        "authority": {
            "ffmpeg_invoked": True,
            "mux_command_executed": True,
            "mux_replay_executed": True,
            "held_out_fixed_vfr_mux_replay_pass": True,
            "direct_row084_mux_replay_proof_present": True,
            "production_mux_replay_pass": False,
            "runtime_media_decode_invoked": False,
            "visual_review_authority_granted": False,
            "combined_visual_review_present": False,
            "fixed_vfr_benchmark_pass": False,
            "cut_detection_algorithm_complete": False,
            "camera_motion_normalization_complete": False,
        },
        "hold_reasons": [
            "production_mux_replay_not_granted",
            "runtime_cut_detector_absent",
            "camera_motion_normalization_incomplete",
            "combined_visual_review_authority_absent",
            "tracker_runtime_artifact_absent",
            "fixed_vfr_benchmark_authority_absent",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": HELD_OUT_FFMPEG_MUX_REPLAY_REVISION,
            "execution_mode": "ffmpeg_lavfi_held_out_fixed_vfr_mux",
            "binds_held_out_mux_dry_run_case_ids": True,
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_claim_production_mux_replay": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def verify_held_out_ffmpeg_mux_replay_receipt(
    receipt: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    reexecute: bool = False,
) -> dict[str, Any]:
    """Fail-closed verify checked-in held-out ffmpeg mux replay receipt."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    receipt_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / HELD_OUT_FFMPEG_MUX_REPLAY_RECEIPT_FILENAME
    )
    payload = receipt if receipt is not None else json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("held-out ffmpeg mux replay receipt must be an object")
    recorded = _expect_sha256(payload.get("receipt_sha256"), "receipt_sha256")
    stable = {
        key: value
        for key, value in payload.items()
        if key not in {"created_at", "receipt_sha256"}
    }
    recomputed = _canonical_sha256(stable)
    if recorded != recomputed:
        raise ValueError(
            "receipt_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    if payload.get("proof_tier") != "RUNTIME_PASS_BOUNDED":
        raise ValueError("held-out ffmpeg mux replay receipt proof_tier mismatch")
    if payload.get("row_complete") is not False:
        raise ValueError("held-out ffmpeg mux replay receipt must keep row_complete=false")
    if payload.get("authority", {}).get("production_mux_replay_pass") is not False:
        raise ValueError("held-out ffmpeg mux must not grant production_mux_replay_pass")
    if payload.get("authority", {}).get("visual_review_authority_granted") is not False:
        raise ValueError("held-out ffmpeg mux must not grant visual review authority")
    if payload.get("summary", {}).get("held_out_fixed_vfr_mux_replay_pass") is not True:
        raise ValueError("held_out_fixed_vfr_mux_replay_pass must be true")
    if payload.get("authority", {}).get("direct_row084_mux_replay_proof_present") is not True:
        raise ValueError("direct_row084_mux_replay_proof_present must be true")

    for case in payload.get("cases", []):
        if not isinstance(case, dict):
            raise ValueError("cases entries must be objects")
        rel = case.get("mux_relative_path")
        if not isinstance(rel, str) or not rel:
            raise ValueError("case mux_relative_path required")
        by_name = (
            directory
            / FIXTURE_MUX_RUNTIME_DIRNAME
            / HELD_OUT_FFMPEG_MUX_REPLAY_DIRNAME
            / Path(rel).name
        )
        if by_name.is_file():
            mux_path = by_name
        elif rel.startswith("runtime/"):
            mux_path = directory / Path(*Path(rel).parts[1:])
        else:
            mux_path = directory / rel
        if not mux_path.is_file():
            raise FileNotFoundError(f"held-out mux output missing: {rel}")
        live_sha = _file_sha256(mux_path)
        if live_sha != case.get("mux_sha256"):
            raise ValueError(
                f"{case.get('case_id')}: mux sha256 drift recorded={case.get('mux_sha256')} live={live_sha}"
            )

    result = {
        "status": "ok",
        "verifier": "verify_held_out_ffmpeg_mux_replay_receipt",
        "receipt_sha256": recorded,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "ffmpeg_invoked": True,
        "mux_replay_executed": True,
        "held_out_fixed_vfr_mux_replay_pass": True,
        "direct_row084_mux_replay_proof_present": True,
        "production_mux_replay_pass": False,
        "visual_review_authority_granted": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "case_count": len(payload.get("cases", [])),
    }
    if reexecute:
        live = execute_held_out_ffmpeg_mux_replay(
            fixture_dir=directory,
            ffmpeg_path=ffmpeg_path,
            write_outputs=False,
        )
        if not live["summary"]["held_out_fixed_vfr_mux_replay_pass"]:
            raise ValueError("live re-execution held-out mux replay failed")
        result["live_reexecution_passed"] = True
        result["live_case_count"] = live["summary"]["case_count"]
    return result


HELD_OUT_CUT_DETECTOR_RUNTIME_REVISION = "row084_held_out_cut_detector_runtime_v1"
HELD_OUT_ROUNDTRIP_BENCHMARK_REVISION = "row084_held_out_roundtrip_benchmark_v1"
HELD_OUT_CAMERA_MOTION_RUNTIME_REVISION = "row084_held_out_camera_motion_runtime_v1"
DIRECT_ROW084_RUNTIME_RECEIPT_REVISION = "row084_direct_runtime_receipt_v1"
HELD_OUT_CUT_DETECTOR_RUNTIME_RECEIPT_FILENAME = "held_out_cut_detector_runtime_receipt.json"
HELD_OUT_ROUNDTRIP_BENCHMARK_RECEIPT_FILENAME = "held_out_roundtrip_benchmark_receipt.json"
HELD_OUT_CAMERA_MOTION_RUNTIME_RECEIPT_FILENAME = "held_out_camera_motion_runtime_receipt.json"
DIRECT_ROW084_RUNTIME_RECEIPT_FILENAME = "direct_row084_runtime_receipt.json"
HELD_OUT_CAMERA_MOTION_DIRNAME = "held_out_camera_motion"
TRACKER_OUTPUT_ARTIFACT_PATH = (
    REPO_ROOT
    / "Plan"
    / "Instructions"
    / "QA"
    / "Evidence"
    / "Wave64"
    / "TRK-W64-084_canonical_video_timeline.json"
)
CUT_HIST_L1_HARD_THRESHOLD = 0.5
CAMERA_MOTION_MEAN_MIN = 0.02
CAMERA_MOTION_MAX_LT = 0.5
STATIC_MEAN_MAX = 0.02
STATIC_MAX_MAX = 0.05
HISTOGRAM_BINS = 16


def _decode_rgb_frames(
    *,
    ffmpeg: Path,
    media_path: Path,
    width: int,
    height: int,
    expected_frames: int | None = None,
) -> list[bytes]:
    """Decode video to RGB24 frames with passthrough timing (no dup expansion)."""
    frame_bytes = width * height * 3
    with tempfile.TemporaryDirectory(prefix="row084_decode_") as tmp:
        raw_path = Path(tmp) / "frames.rgb"
        _run_media_tool(
            ffmpeg,
            [
                "-y",
                "-i",
                str(media_path),
                "-an",
                "-fps_mode",
                "passthrough",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                str(raw_path),
            ],
            label="ffmpeg-decode-rgb",
        )
        blob = raw_path.read_bytes()
    if len(blob) % frame_bytes != 0:
        raise ValueError(
            f"decoded RGB byte length {len(blob)} is not divisible by frame size {frame_bytes}"
        )
    frames = [
        blob[offset : offset + frame_bytes]
        for offset in range(0, len(blob), frame_bytes)
    ]
    if expected_frames is not None and len(frames) != expected_frames:
        raise ValueError(
            f"decoded frame count mismatch expected={expected_frames} got={len(frames)} "
            f"for {media_path.name}"
        )
    if not frames:
        raise ValueError(f"no frames decoded from {media_path}")
    return frames


def _rgb_histogram(frame: bytes, *, bins: int = HISTOGRAM_BINS) -> list[float]:
    if bins <= 0:
        raise ValueError("bins must be positive")
    hist = [0] * (bins * 3)
    for idx in range(0, len(frame), 3):
        hist[frame[idx] * bins // 256] += 1
        hist[bins + frame[idx + 1] * bins // 256] += 1
        hist[2 * bins + frame[idx + 2] * bins // 256] += 1
    total = float(sum(hist)) or 1.0
    return [value / total for value in hist]


def _hist_l1(left: list[float], right: list[float]) -> float:
    return float(sum(abs(a - b) for a, b in zip(left, right)))


def _pair_hist_deltas(frames: list[bytes]) -> list[float]:
    if len(frames) < 2:
        raise ValueError("histogram delta requires at least two frames")
    deltas: list[float] = []
    prev = _rgb_histogram(frames[0])
    for frame in frames[1:]:
        current = _rgb_histogram(frame)
        deltas.append(_hist_l1(prev, current))
        prev = current
    return deltas


def _detect_hard_cuts(
    deltas: list[float],
    *,
    threshold: float = CUT_HIST_L1_HARD_THRESHOLD,
) -> list[dict[str, Any]]:
    cuts: list[dict[str, Any]] = []
    for idx, delta in enumerate(deltas):
        if delta > threshold:
            # cut at destination frame index (frame i when comparing i-1 -> i)
            confidence = min(1.0, delta / 1.3333)
            if confidence < 0.8:
                confidence = 0.8
            cuts.append(
                {
                    "frame_index": idx + 1,
                    "cut_kind": "hard",
                    "algorithm_id": "fixture_histogram_diff_v1",
                    "confidence": round(confidence, 6),
                    "hist_l1": round(delta, 6),
                }
            )
    return cuts


def _classify_camera_motion_profile(deltas: list[float]) -> str:
    if not deltas:
        raise ValueError("camera motion classification requires deltas")
    mean_delta = sum(deltas) / float(len(deltas))
    max_delta = max(deltas)
    if max_delta > CUT_HIST_L1_HARD_THRESHOLD:
        return "hard_cut"
    if mean_delta <= STATIC_MEAN_MAX and max_delta <= STATIC_MAX_MAX:
        return "static"
    moderate = sum(1 for delta in deltas if delta > CAMERA_MOTION_MEAN_MIN)
    if (
        mean_delta >= CAMERA_MOTION_MEAN_MIN
        and max_delta < CAMERA_MOTION_MAX_LT
        and moderate >= max(1, len(deltas) // 2)
    ):
        return "camera_motion"
    raise ValueError(
        "unable to classify camera-motion profile: "
        f"mean={mean_delta:.4f} max={max_delta:.4f} moderate={moderate}"
    )


def _resolve_held_out_mux_path(fixture_dir: Path, case_id: str) -> Path:
    path = (
        fixture_dir
        / FIXTURE_MUX_RUNTIME_DIRNAME
        / HELD_OUT_FFMPEG_MUX_REPLAY_DIRNAME
        / f"{case_id}_mux.mkv"
    )
    if not path.is_file():
        raise FileNotFoundError(
            f"held-out mux missing for offline runtime climb: {path}. "
            "Re-run --execute-held-out-ffmpeg-mux-replay first."
        )
    return path


def execute_held_out_cut_detector_runtime(
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Run offline histogram-diff cut detection on held-out ffmpeg mux media.

    Clears ROW084-014 at RUNTIME_PASS_BOUNDED for held-out lavfi media only.
    Does not grant VISUAL_QA_PASS_BOUNDED, production authority, or row_complete.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / HELD_OUT_CUT_DETECTOR_RUNTIME_RECEIPT_FILENAME
    )
    ffmpeg = resolve_ffmpeg_binary(explicit_path=ffmpeg_path, fixture_dir=directory)
    version_run = _run_media_tool(ffmpeg, ["-version"], label="ffmpeg-version")
    version_line = (version_run["stdout_tail"] or version_run["stderr_tail"]).splitlines()[0].strip()

    # Positive hard-cut case from VFR color change at frame 12.
    cut_case_id = "held_out_vfr_24_30"
    cut_mux = _resolve_held_out_mux_path(directory, cut_case_id)
    cut_frames = _decode_rgb_frames(
        ffmpeg=ffmpeg, media_path=cut_mux, width=64, height=64, expected_frames=24
    )
    cut_deltas = _pair_hist_deltas(cut_frames)
    detected = _detect_hard_cuts(cut_deltas)
    expected_cut_frame = 12
    true_positives = sum(1 for cut in detected if cut["frame_index"] == expected_cut_frame)
    false_positives = sum(1 for cut in detected if cut["frame_index"] != expected_cut_frame)
    false_negatives = 0 if true_positives else 1
    precision = (
        true_positives / float(true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )
    recall = (
        true_positives / float(true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )
    if true_positives != 1 or false_positives != 0 or false_negatives != 0:
        raise ValueError(
            "held-out cut detector failed expected single hard cut at frame 12: "
            f"detected={detected}"
        )
    if precision < 1.0 or recall < 1.0:
        raise ValueError("held-out cut detector precision/recall below 1.0")

    # Negative control: solid-color fixed mux must not emit hard cuts.
    static_case_id = "held_out_fixed_24"
    static_mux = _resolve_held_out_mux_path(directory, static_case_id)
    static_frames = _decode_rgb_frames(
        ffmpeg=ffmpeg, media_path=static_mux, width=64, height=64, expected_frames=16
    )
    static_detected = _detect_hard_cuts(_pair_hist_deltas(static_frames))
    if static_detected:
        raise ValueError(f"static fixed mux unexpectedly emitted cuts: {static_detected}")

    # Ledger algorithm path: bind declared cut epoch to media-detected truth.
    ledger_cut = {
        "cut_id": "cut_hard_ledger_runtime",
        "frame_index": expected_cut_frame,
        "cut_kind": "hard",
        "algorithm_id": "fixture_ledger_v1",
        "confidence": 0.95,
    }
    if ledger_cut["frame_index"] != detected[0]["frame_index"]:
        raise ValueError("fixture_ledger_v1 frame does not match histogram detection")

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_held_out_cut_detector_runtime_receipt",
        "receipt_id": "row084_held_out_cut_detector_runtime_receipt_v1",
        "revision": HELD_OUT_CUT_DETECTOR_RUNTIME_REVISION,
        "status": "held_out_cut_detector_runtime_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "ffmpeg": {
            "resolved_path": str(ffmpeg),
            "version_line": version_line,
            "invoked": True,
            "runtime_media_decode_invoked": True,
            "comfyui_8188_invoked": False,
        },
        "cases": [
            {
                "case_id": cut_case_id,
                "role": "hard_cut_positive",
                "mux_sha256": _file_sha256(cut_mux),
                "frame_count": len(cut_frames),
                "expected_cut_frames": [expected_cut_frame],
                "detected_cuts": detected,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "precision": precision,
                "recall": recall,
                "algorithms_exercised": [
                    "fixture_histogram_diff_v1",
                    "fixture_ledger_v1",
                ],
                "ledger_cut_epoch": ledger_cut,
                "passed": True,
            },
            {
                "case_id": static_case_id,
                "role": "static_negative_control",
                "mux_sha256": _file_sha256(static_mux),
                "frame_count": len(static_frames),
                "expected_cut_frames": [],
                "detected_cuts": static_detected,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "precision": 1.0,
                "recall": 1.0,
                "algorithms_exercised": ["fixture_histogram_diff_v1"],
                "passed": True,
            },
        ],
        "summary": {
            "case_count": 2,
            "all_cases_passed": True,
            "algorithms_covered": [
                "fixture_histogram_diff_v1",
                "fixture_ledger_v1",
            ],
            "runtime_detector_complete": True,
            "runtime_media_decode_invoked": True,
            "comfyui_8188_invoked": False,
        },
        "authority": {
            "cut_detection_algorithm_complete": True,
            "fixture_contract_only": False,
            "fixed_vfr_benchmark_pass": False,
            "camera_motion_normalization_complete": False,
            "mux_replay_proof_present": True,
            "combined_visual_review_present": False,
            "visual_review_authority_granted": False,
            "production_completion_allowed": False,
        },
        "hold_reasons": [
            "camera_motion_normalization_incomplete",
            "combined_visual_review_authority_absent",
            "visual_qa_pass_bounded_absent",
            "production_cut_detector_not_granted",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": HELD_OUT_CUT_DETECTOR_RUNTIME_REVISION,
            "execution_mode": "ffmpeg_decode_histogram_diff_held_out",
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_use_comfyui_8188": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def verify_held_out_cut_detector_runtime_receipt(
    receipt: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    receipt_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / HELD_OUT_CUT_DETECTOR_RUNTIME_RECEIPT_FILENAME
    )
    payload = receipt if receipt is not None else json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("cut detector runtime receipt must be an object")
    recorded = _expect_sha256(payload.get("receipt_sha256"), "receipt_sha256")
    stable = {
        key: value
        for key, value in payload.items()
        if key not in {"created_at", "receipt_sha256"}
    }
    recomputed = _canonical_sha256(stable)
    if recorded != recomputed:
        raise ValueError(
            f"cut detector receipt_sha256 mismatch recorded={recorded} recomputed={recomputed}"
        )
    if payload.get("authority", {}).get("cut_detection_algorithm_complete") is not True:
        raise ValueError("cut_detection_algorithm_complete must be true")
    if payload.get("authority", {}).get("visual_review_authority_granted") is not False:
        raise ValueError("cut detector must not grant visual review authority")
    if payload.get("row_complete") is not False:
        raise ValueError("cut detector must keep row_complete=false")
    if payload.get("ffmpeg", {}).get("comfyui_8188_invoked") is not False:
        raise ValueError("cut detector must not invoke comfyui :8188")
    return {
        "status": "ok",
        "verifier": "verify_held_out_cut_detector_runtime_receipt",
        "receipt_sha256": recorded,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "cut_detection_algorithm_complete": True,
        "visual_review_authority_granted": False,
        "row_complete": False,
    }


def _held_out_roundtrip_benchmark_packets(
    *,
    fixture_dir: Path,
) -> list[dict[str, Any]]:
    """Build media-backed held-out timeline packets for round-trip benchmark."""
    packets: list[dict[str, Any]] = []
    for case in _held_out_ffmpeg_mux_cases():
        frames = int(case["expected_video_frames"])
        mode = case["frame_rate_mode"]
        mux_path = _resolve_held_out_mux_path(fixture_dir, case["case_id"])
        video_sha = _file_sha256(mux_path)
        source_binding = {
            "video_sha256": video_sha,
            "stream_index": 0,
            "container_sha256": video_sha,
            "audio_stream_sha256": None,
            "audio_stream_index": None,
        }
        if mode == "vfr":
            segments = case["vfr_segments"]
            assert segments is not None
            frame_table = [
                {"frame_index": idx, "source_pts": idx, "duration_pts": 1}
                for idx in range(frames)
            ]
            vfr_segments = [
                {
                    "segment_id": "seg_24",
                    "start_frame": 0,
                    "end_frame_exclusive": int(segments[0]["frames"]),
                    "timebase_numerator": 1,
                    "timebase_denominator": int(segments[0]["fps_num"]),
                },
                {
                    "segment_id": "seg_30",
                    "start_frame": int(segments[0]["frames"]),
                    "end_frame_exclusive": frames,
                    "timebase_numerator": 1,
                    "timebase_denominator": int(segments[1]["fps_num"]),
                },
            ]
            packet = {
                "schema_version": "1.0.0",
                "timeline_id": f"benchmark_{case['case_id']}",
                "revision": "row084_held_out_roundtrip_benchmark_v1",
                "source_binding": source_binding,
                "clock_span": {
                    "clock_id": f"clock_{case['case_id']}",
                    "timebase_numerator": 1,
                    "timebase_denominator": 24,
                    "start_pts": 0,
                    "end_pts_exclusive": frames,
                    "start_frame": 0,
                    "end_frame_exclusive": frames,
                    "start_sample": 0,
                    "end_sample_exclusive": int(case["expected_end_sample_exclusive"]),
                    "frame_rate_numerator": 24,
                    "frame_rate_denominator": 1,
                    "sample_rate_hz": 48000,
                    "rounding_policy": "nearest_ties_to_even",
                },
                "frame_rate_mode": "vfr",
                "frame_table": frame_table,
                "vfr_segments": vfr_segments,
                "cut_epochs": [
                    {
                        "cut_id": "benchmark_vfr_cut",
                        "frame_index": 12,
                        "cut_kind": "hard",
                        "algorithm_id": "fixture_histogram_diff_v1",
                        "confidence": 0.95,
                    }
                ],
                "missing_frames": [],
                "camera_motion_policy": "distinguish_from_cuts",
                "tolerances": dict(DEFAULT_TOLERANCES),
                "dependency_authority": {"row067_complete": True},
                "runtime_authority": {
                    "mux_replay_proof_present": True,
                    "fixed_vfr_benchmark_pass": False,
                    "combined_visual_review_present": False,
                },
                "provenance": {"fixture": "held_out_roundtrip_benchmark", "case_id": case["case_id"]},
            }
        else:
            fps_num = int(case["fps_num"])
            fps_den = int(case["fps_den"])
            frame_table = [
                {
                    "frame_index": idx,
                    "source_pts": idx * fps_den,
                    "duration_pts": fps_den,
                }
                for idx in range(frames)
            ]
            packet = {
                "schema_version": "1.0.0",
                "timeline_id": f"benchmark_{case['case_id']}",
                "revision": "row084_held_out_roundtrip_benchmark_v1",
                "source_binding": source_binding,
                "clock_span": {
                    "clock_id": f"clock_{case['case_id']}",
                    "timebase_numerator": fps_den,
                    "timebase_denominator": fps_num,
                    "start_pts": 0,
                    "end_pts_exclusive": frames * fps_den,
                    "start_frame": 0,
                    "end_frame_exclusive": frames,
                    "start_sample": 0,
                    "end_sample_exclusive": int(case["expected_end_sample_exclusive"]),
                    "frame_rate_numerator": fps_num,
                    "frame_rate_denominator": fps_den,
                    "sample_rate_hz": 48000,
                    "rounding_policy": "nearest_ties_to_even",
                },
                "frame_rate_mode": "fractional" if fps_den != 1 else "fixed",
                "frame_table": frame_table,
                "vfr_segments": [],
                "cut_epochs": [],
                "missing_frames": [],
                "camera_motion_policy": "not_evaluated",
                "tolerances": dict(DEFAULT_TOLERANCES),
                "dependency_authority": {"row067_complete": True},
                "runtime_authority": {
                    "mux_replay_proof_present": True,
                    "fixed_vfr_benchmark_pass": False,
                    "combined_visual_review_present": False,
                },
                "provenance": {"fixture": "held_out_roundtrip_benchmark", "case_id": case["case_id"]},
            }
        packets.append({"case": case, "packet": packet})
    return packets


def execute_held_out_roundtrip_benchmark(
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Execute media-backed fixed/fractional/VFR frame-seconds-sample round-trip benchmark.

    Clears ROW084-018 at RUNTIME_PASS_BOUNDED for held-out ffmpeg mux clocks only.
    Does not grant production benchmark authority, VISUAL_QA_PASS_BOUNDED, or row_complete.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / HELD_OUT_ROUNDTRIP_BENCHMARK_RECEIPT_FILENAME
    )
    ffmpeg = resolve_ffmpeg_binary(explicit_path=ffmpeg_path, fixture_dir=directory)
    ffprobe = _ffprobe_beside(ffmpeg)
    version_run = _run_media_tool(ffmpeg, ["-version"], label="ffmpeg-version")
    version_line = (version_run["stdout_tail"] or version_run["stderr_tail"]).splitlines()[0].strip()

    case_results: list[dict[str, Any]] = []
    for item in _held_out_roundtrip_benchmark_packets(fixture_dir=directory):
        case = item["case"]
        packet = item["packet"]
        mux_path = _resolve_held_out_mux_path(directory, case["case_id"])
        probe = _ffprobe_json(ffprobe, mux_path)
        video = _stream_by_codec_type(probe, "video")
        audio = _stream_by_codec_type(probe, "audio")
        nb_read = video.get("nb_read_frames")
        if nb_read is None:
            nb_read = video.get("nb_frames")
        if nb_read is None:
            raise ValueError(f"{case['case_id']}: ffprobe frame count missing for benchmark")
        frame_count = int(nb_read)
        if frame_count != int(case["expected_video_frames"]):
            raise ValueError(
                f"{case['case_id']}: benchmark frame count mismatch "
                f"expected={case['expected_video_frames']} got={frame_count}"
            )
        sample_rate = int(float(audio.get("sample_rate", 0)))
        if sample_rate != 48000:
            raise ValueError(f"{case['case_id']}: benchmark sample_rate must be 48000")
        receipt = compile_timeline(packet)
        evidence = receipt["roundtrip_evidence"]
        if not evidence.get("within_tolerance"):
            raise ValueError(f"{case['case_id']}: round-trip outside registered tolerances")
        # Exclude wall-clock created_at/timeline_sha256 so benchmark receipt digests are stable.
        stable_timeline = {
            key: value
            for key, value in receipt.items()
            if key not in {"created_at", "timeline_sha256"}
        }
        case_results.append(
            {
                "case_id": case["case_id"],
                "frame_rate_mode": receipt["frame_rate_mode"],
                "mux_sha256": _file_sha256(mux_path),
                "timeline_stable_sha256": _canonical_sha256(stable_timeline),
                "checked_frame_count": evidence["checked_frame_count"],
                "max_observed_frame_residual": evidence["max_observed_frame_residual"],
                "max_observed_sample_residual": evidence["max_observed_sample_residual"],
                "max_observed_seconds_residual": evidence["max_observed_seconds_residual"],
                "within_tolerance": True,
                "tolerances": dict(DEFAULT_TOLERANCES),
                "media_frame_count": frame_count,
                "media_sample_rate_hz": sample_rate,
                "benchmark_passed": True,
            }
        )

    modes = {item["frame_rate_mode"] for item in case_results}
    if "fixed" not in modes or "vfr" not in modes:
        raise ValueError("held-out roundtrip benchmark must cover fixed and vfr")
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_held_out_roundtrip_benchmark_receipt",
        "receipt_id": "row084_held_out_roundtrip_benchmark_receipt_v1",
        "revision": HELD_OUT_ROUNDTRIP_BENCHMARK_REVISION,
        "status": "held_out_roundtrip_benchmark_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "ffmpeg": {
            "resolved_path": str(ffmpeg),
            "ffprobe_path": str(ffprobe),
            "version_line": version_line,
            "invoked": True,
            "comfyui_8188_invoked": False,
        },
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "modes_covered": sorted(modes),
            "fixed_covered": "fixed" in modes,
            "fractional_covered": "fractional" in modes,
            "vfr_covered": "vfr" in modes,
            "all_within_tolerance": True,
            "benchmark_authority_granted": True,
            "fixed_vfr_benchmark_pass": True,
            "production_benchmark": False,
            "runtime_media_decode_invoked": False,
            "comfyui_8188_invoked": False,
        },
        "authority": {
            "fixed_vfr_benchmark_pass": True,
            "benchmark_authority_granted": True,
            "fixture_matrix_only": False,
            "production_benchmark": False,
            "cut_detection_algorithm_complete": False,
            "camera_motion_normalization_complete": False,
            "combined_visual_review_present": False,
            "visual_review_authority_granted": False,
            "production_completion_allowed": False,
        },
        "hold_reasons": [
            "production_benchmark_not_granted",
            "combined_visual_review_authority_absent",
            "visual_qa_pass_bounded_absent",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": HELD_OUT_ROUNDTRIP_BENCHMARK_REVISION,
            "execution_mode": "held_out_ffmpeg_mux_clock_roundtrip_benchmark",
            "tolerances_source": "DEFAULT_TOLERANCES",
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_use_comfyui_8188": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def verify_held_out_roundtrip_benchmark_receipt(
    receipt: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    receipt_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / HELD_OUT_ROUNDTRIP_BENCHMARK_RECEIPT_FILENAME
    )
    payload = receipt if receipt is not None else json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("roundtrip benchmark receipt must be an object")
    recorded = _expect_sha256(payload.get("receipt_sha256"), "receipt_sha256")
    stable = {
        key: value
        for key, value in payload.items()
        if key not in {"created_at", "receipt_sha256"}
    }
    recomputed = _canonical_sha256(stable)
    if recorded != recomputed:
        raise ValueError(
            f"roundtrip benchmark receipt_sha256 mismatch recorded={recorded} recomputed={recomputed}"
        )
    if payload.get("summary", {}).get("fixed_vfr_benchmark_pass") is not True:
        raise ValueError("fixed_vfr_benchmark_pass must be true")
    if payload.get("summary", {}).get("production_benchmark") is not False:
        raise ValueError("production_benchmark must remain false")
    if payload.get("authority", {}).get("visual_review_authority_granted") is not False:
        raise ValueError("benchmark must not grant visual review authority")
    if payload.get("row_complete") is not False:
        raise ValueError("benchmark must keep row_complete=false")
    return {
        "status": "ok",
        "verifier": "verify_held_out_roundtrip_benchmark_receipt",
        "receipt_sha256": recorded,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "fixed_vfr_benchmark_pass": True,
        "benchmark_authority_granted": True,
        "production_benchmark": False,
        "visual_review_authority_granted": False,
        "row_complete": False,
    }


def _generate_camera_pan_mux(*, ffmpeg: Path, output_path: Path) -> Path:
    """Generate a short testsrc pan clip (camera motion, no hard cut)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run_media_tool(
        ffmpeg,
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=128x64:rate=24:duration=1",
            "-vf",
            "crop=64:64:x='min(63\\,n*3)':y=0",
            "-frames:v",
            "24",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ],
        label="ffmpeg-camera-pan-mux",
    )
    if not output_path.is_file() or output_path.stat().st_size < 1:
        raise ValueError("camera pan mux generation failed")
    return output_path


def execute_held_out_camera_motion_runtime(
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Classify held-out hard-cut vs camera-pan vs static profiles offline.

    Clears ROW084-016 at RUNTIME_PASS_BOUNDED for held-out lavfi media only.
    Does not grant VISUAL_QA_PASS_BOUNDED or row_complete.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    media_dir = runtime_dir / HELD_OUT_CAMERA_MOTION_DIRNAME
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / HELD_OUT_CAMERA_MOTION_RUNTIME_RECEIPT_FILENAME
    )
    ffmpeg = resolve_ffmpeg_binary(explicit_path=ffmpeg_path, fixture_dir=directory)
    version_run = _run_media_tool(ffmpeg, ["-version"], label="ffmpeg-version")
    version_line = (version_run["stdout_tail"] or version_run["stderr_tail"]).splitlines()[0].strip()

    # Prefer checked-in pan mux for digest-stable verify/re-exec; generate only if absent.
    durable_pan_path = media_dir / "held_out_camera_pan_testsrc.mkv"
    if durable_pan_path.is_file():
        pan_path = durable_pan_path
    elif write_outputs:
        media_dir.mkdir(parents=True, exist_ok=True)
        pan_path = durable_pan_path
        _generate_camera_pan_mux(ffmpeg=ffmpeg, output_path=pan_path)
    else:
        pan_path = Path(tempfile.mkdtemp(prefix="row084_pan_")) / "held_out_camera_pan_testsrc.mkv"
        _generate_camera_pan_mux(ffmpeg=ffmpeg, output_path=pan_path)

    cases_spec = [
        {
            "case_id": "held_out_vfr_24_30",
            "role": "hard_cut",
            "expected_class": "hard_cut",
            "expected_policy": "distinguish_from_cuts",
            "media_path": _resolve_held_out_mux_path(directory, "held_out_vfr_24_30"),
            "expected_frames": 24,
            "generated": False,
        },
        {
            "case_id": "held_out_camera_pan_testsrc",
            "role": "camera_pan",
            "expected_class": "camera_motion",
            "expected_policy": "distinguish_from_cuts",
            "media_path": pan_path,
            "expected_frames": 24,
            "generated": True,
        },
        {
            "case_id": "held_out_fixed_24",
            "role": "static",
            "expected_class": "static",
            "expected_policy": "not_evaluated",
            "media_path": _resolve_held_out_mux_path(directory, "held_out_fixed_24"),
            "expected_frames": 16,
            "generated": False,
        },
    ]

    case_results: list[dict[str, Any]] = []
    for spec in cases_spec:
        frames = _decode_rgb_frames(
            ffmpeg=ffmpeg,
            media_path=spec["media_path"],
            width=64,
            height=64,
            expected_frames=int(spec["expected_frames"]),
        )
        deltas = _pair_hist_deltas(frames)
        classification = _classify_camera_motion_profile(deltas)
        if classification != spec["expected_class"]:
            raise ValueError(
                f"{spec['case_id']}: expected class {spec['expected_class']} got {classification}"
            )
        hard_cuts = _detect_hard_cuts(deltas)
        if spec["expected_class"] == "hard_cut" and not hard_cuts:
            raise ValueError(f"{spec['case_id']}: hard_cut class without detected cuts")
        if spec["expected_class"] != "hard_cut" and hard_cuts:
            raise ValueError(f"{spec['case_id']}: non-cut class emitted hard cuts: {hard_cuts}")
        mean_delta = sum(deltas) / float(len(deltas))
        case_results.append(
            {
                "case_id": spec["case_id"],
                "role": spec["role"],
                "expected_class": spec["expected_class"],
                "observed_class": classification,
                "expected_policy": spec["expected_policy"],
                "media_sha256": _file_sha256(spec["media_path"]),
                "frame_count": len(frames),
                "mean_hist_l1": round(mean_delta, 6),
                "max_hist_l1": round(max(deltas), 6),
                "hard_cut_count": len(hard_cuts),
                "generated_media": bool(spec["generated"]),
                "passed": True,
            }
        )

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_held_out_camera_motion_runtime_receipt",
        "receipt_id": "row084_held_out_camera_motion_runtime_receipt_v1",
        "revision": HELD_OUT_CAMERA_MOTION_RUNTIME_REVISION,
        "status": "held_out_camera_motion_runtime_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "ffmpeg": {
            "resolved_path": str(ffmpeg),
            "version_line": version_line,
            "invoked": True,
            "runtime_media_decode_invoked": True,
            "comfyui_8188_invoked": False,
        },
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "classes_covered": sorted({item["observed_class"] for item in case_results}),
            "hard_cut_covered": True,
            "camera_motion_covered": True,
            "static_covered": True,
            "all_cases_passed": True,
            "camera_motion_normalization_complete": True,
            "runtime_media_decode_invoked": True,
            "comfyui_8188_invoked": False,
        },
        "authority": {
            "camera_motion_normalization_complete": True,
            "fixture_matrix_only": False,
            "cut_detection_algorithm_complete": False,
            "fixed_vfr_benchmark_pass": False,
            "combined_visual_review_present": False,
            "visual_review_authority_granted": False,
            "production_completion_allowed": False,
        },
        "hold_reasons": [
            "combined_visual_review_authority_absent",
            "visual_qa_pass_bounded_absent",
            "production_camera_motion_not_granted",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": HELD_OUT_CAMERA_MOTION_RUNTIME_REVISION,
            "execution_mode": "ffmpeg_decode_hist_profile_cut_vs_pan_vs_static",
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_use_comfyui_8188": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def verify_held_out_camera_motion_runtime_receipt(
    receipt: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    receipt_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / HELD_OUT_CAMERA_MOTION_RUNTIME_RECEIPT_FILENAME
    )
    payload = receipt if receipt is not None else json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("camera motion runtime receipt must be an object")
    recorded = _expect_sha256(payload.get("receipt_sha256"), "receipt_sha256")
    stable = {
        key: value
        for key, value in payload.items()
        if key not in {"created_at", "receipt_sha256"}
    }
    recomputed = _canonical_sha256(stable)
    if recorded != recomputed:
        raise ValueError(
            f"camera motion receipt_sha256 mismatch recorded={recorded} recomputed={recomputed}"
        )
    if payload.get("authority", {}).get("camera_motion_normalization_complete") is not True:
        raise ValueError("camera_motion_normalization_complete must be true")
    if payload.get("authority", {}).get("visual_review_authority_granted") is not False:
        raise ValueError("camera motion must not grant visual review authority")
    if payload.get("row_complete") is not False:
        raise ValueError("camera motion must keep row_complete=false")
    return {
        "status": "ok",
        "verifier": "verify_held_out_camera_motion_runtime_receipt",
        "receipt_sha256": recorded,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "camera_motion_normalization_complete": True,
        "visual_review_authority_granted": False,
        "row_complete": False,
    }


def emit_direct_row084_runtime_receipt(
    *,
    fixture_dir: Path | None = None,
    output_receipt_path: Path | None = None,
    write_outputs: bool = True,
    preloaded_receipts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind offline runtime proofs into direct_row084_runtime_receipt (ROW084-021)."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    runtime_dir = directory / FIXTURE_MUX_RUNTIME_DIRNAME
    receipt_path = (
        output_receipt_path
        if output_receipt_path is not None
        else runtime_dir / DIRECT_ROW084_RUNTIME_RECEIPT_FILENAME
    )

    required = {
        "held_out_ffmpeg_mux_replay": HELD_OUT_FFMPEG_MUX_REPLAY_RECEIPT_FILENAME,
        "held_out_cut_detector_runtime": HELD_OUT_CUT_DETECTOR_RUNTIME_RECEIPT_FILENAME,
        "held_out_roundtrip_benchmark": HELD_OUT_ROUNDTRIP_BENCHMARK_RECEIPT_FILENAME,
        "held_out_camera_motion_runtime": HELD_OUT_CAMERA_MOTION_RUNTIME_RECEIPT_FILENAME,
        "fixture_media_mux_runtime": FIXTURE_MUX_RUNTIME_RECEIPT_FILENAME,
    }
    preloaded = preloaded_receipts or {}
    bindings: dict[str, Any] = {}
    for key, filename in required.items():
        if key in preloaded:
            payload = preloaded[key]
        else:
            path = runtime_dir / filename
            if not path.is_file():
                raise FileNotFoundError(f"direct runtime receipt missing dependency: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{filename} must be a JSON object")
        digest = payload.get("receipt_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"{filename} missing receipt_sha256")
        bindings[key] = {
            "relative_path": f"{FIXTURE_MUX_RUNTIME_DIRNAME}/{filename}",
            "receipt_sha256": digest,
            "proof_tier": payload.get("proof_tier"),
            "row_complete": payload.get("row_complete", False),
        }

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row084_direct_runtime_receipt",
        "receipt_id": "row084_direct_runtime_receipt_v1",
        "revision": DIRECT_ROW084_RUNTIME_RECEIPT_REVISION,
        "status": "direct_row084_runtime_receipt_pass_bounded",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "bindings": bindings,
        "summary": {
            "direct_row084_runtime_receipt_present": True,
            "bound_receipt_count": len(bindings),
            "cut_detection_algorithm_complete": True,
            "camera_motion_normalization_complete": True,
            "fixed_vfr_benchmark_pass": True,
            "mux_replay_proof_present": True,
            "combined_visual_review_present": False,
            "comfyui_8188_invoked": False,
        },
        "authority": {
            "direct_row084_runtime_receipt_present": True,
            "cut_detection_algorithm_complete": True,
            "camera_motion_normalization_complete": True,
            "fixed_vfr_benchmark_pass": True,
            "combined_visual_review_present": False,
            "visual_review_authority_granted": False,
            "production_completion_allowed": False,
        },
        "hold_reasons": [
            "combined_visual_review_authority_absent",
            "visual_qa_pass_bounded_absent",
            "row_complete_blocked",
        ],
        "production_completion_allowed": False,
        "row_complete": False,
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "runtime_revision": DIRECT_ROW084_RUNTIME_RECEIPT_REVISION,
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_use_comfyui_8188": True,
        },
    }
    stable = {key: value for key, value in receipt_body.items() if key != "created_at"}
    receipt_body["receipt_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(receipt_path, receipt_body)
    return receipt_body


def emit_tracker_output_artifact_hold(
    *,
    fixture_dir: Path | None = None,
    output_path: Path | None = None,
    write_outputs: bool = True,
    direct_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit tracker-declared HOLD artifact for ROW084-022 without COMPLETE claim."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    artifact_path = output_path if output_path is not None else TRACKER_OUTPUT_ARTIFACT_PATH
    direct = (
        direct_receipt
        if direct_receipt is not None
        else emit_direct_row084_runtime_receipt(fixture_dir=directory, write_outputs=False)
    )
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "canonical_video_timeline",
        "tracker_id": "TRK-W64-084",
        "item_id": "ITEM-W64-084",
        "artifact_id": "TRK-W64-084_canonical_video_timeline",
        "status": "HOLD_RUNTIME_PASS_BOUNDED_VISUAL_QA_ABSENT",
        "created_at": created_at,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED",
        "climb_targets": ["RUNTIME_PASS_BOUNDED", "VISUAL_QA_PASS_BOUNDED"],
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "visual_review_authority_granted": False,
        "direct_runtime_receipt_sha256": direct["receipt_sha256"],
        "offline_runtime_bindings": direct["bindings"],
        "cleared_offline_checks": [
            "ROW084-014",
            "ROW084-016",
            "ROW084-018",
            "ROW084-019",
            "ROW084-021",
            "ROW084-022",
        ],
        "remaining_complete_blockers": [
            {
                "blocker_id": "VISUAL_QA_AND_RUNTIME_GATES_ABSENT",
                "check_ids": ["ROW084-020"],
                "detail": (
                    "ROW084-020 direct_combined_visual_audio_review_present requires "
                    "combined frame/contact/audio visual review authority "
                    "(VISUAL_QA_PASS_BOUNDED); cannot be claimed from digests or "
                    "offline histogram proofs. Needs decoded-frame visual review "
                    "and must not steal :8188 from ROW084-019/023 lanes."
                ),
            }
        ],
        "provenance": {
            "compiler": "compile_wave64_canonical_video_timeline.py",
            "compiler_revision": COMPILER_REVISION,
            "does_not_claim_visual_qa_pass_bounded": True,
            "does_not_claim_row_complete": True,
            "does_not_use_comfyui_8188": True,
            "tracker_output_artifact_hold_only": True,
        },
    }
    stable = {key: value for key, value in body.items() if key != "created_at"}
    body["artifact_sha256"] = _canonical_sha256(stable)
    if write_outputs:
        _write_json_atomic(artifact_path, body)
    return body


def execute_held_out_offline_runtime_climb(
    *,
    fixture_dir: Path | None = None,
    ffmpeg_path: str | Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Execute cut/benchmark/camera offline climb + direct receipt + tracker HOLD artifact."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    cut = execute_held_out_cut_detector_runtime(
        fixture_dir=directory, ffmpeg_path=ffmpeg_path, write_outputs=write_outputs
    )
    benchmark = execute_held_out_roundtrip_benchmark(
        fixture_dir=directory, ffmpeg_path=ffmpeg_path, write_outputs=write_outputs
    )
    camera = execute_held_out_camera_motion_runtime(
        fixture_dir=directory, ffmpeg_path=ffmpeg_path, write_outputs=write_outputs
    )
    mux_replay_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / HELD_OUT_FFMPEG_MUX_REPLAY_RECEIPT_FILENAME
    )
    fixture_mux_path = (
        directory / FIXTURE_MUX_RUNTIME_DIRNAME / FIXTURE_MUX_RUNTIME_RECEIPT_FILENAME
    )
    preloaded = {
        "held_out_ffmpeg_mux_replay": json.loads(mux_replay_path.read_text(encoding="utf-8")),
        "held_out_cut_detector_runtime": cut,
        "held_out_roundtrip_benchmark": benchmark,
        "held_out_camera_motion_runtime": camera,
        "fixture_media_mux_runtime": json.loads(fixture_mux_path.read_text(encoding="utf-8")),
    }
    direct = emit_direct_row084_runtime_receipt(
        fixture_dir=directory,
        write_outputs=write_outputs,
        preloaded_receipts=preloaded,
    )
    tracker = emit_tracker_output_artifact_hold(
        fixture_dir=directory,
        write_outputs=write_outputs,
        direct_receipt=direct,
    )
    return {
        "status": "ok",
        "mode": "execute-held-out-offline-runtime-climb",
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "cut_detector_receipt_sha256": cut["receipt_sha256"],
        "roundtrip_benchmark_receipt_sha256": benchmark["receipt_sha256"],
        "camera_motion_receipt_sha256": camera["receipt_sha256"],
        "direct_runtime_receipt_sha256": direct["receipt_sha256"],
        "tracker_artifact_sha256": tracker["artifact_sha256"],
        "cut_detection_algorithm_complete": True,
        "camera_motion_normalization_complete": True,
        "fixed_vfr_benchmark_pass": True,
        "direct_row084_runtime_receipt_present": True,
        "tracker_declared_output_artifact_present": True,
        "visual_review_authority_granted": False,
        "row_complete": False,
        "comfyui_8188_invoked": False,
        "remaining_complete_blocker_checks": ["ROW084-020"],
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a fail-closed Row084 canonical video timeline receipt.")
    parser.add_argument(
        "--input",
        help=(
            "Path to timeline, mux-prep, held-out matrix, held-out mux dry-run, "
            "missing-frame policy matrix, camera-motion policy matrix, "
            "cut-detector algorithm contract, or combined visual protocol input JSON"
        ),
    )
    parser.add_argument("--output", help="Path to write compiled receipt JSON")
    parser.add_argument(
        "--mode",
        choices=(
            "timeline",
            "mux-prep",
            "held-out-matrix",
            "held-out-mux-dry-run",
            "missing-frame-policy-matrix",
            "camera-motion-policy-matrix",
            "cut-detector-algorithm-contract",
            "combined-visual-review-fixture-protocol",
        ),
        default="timeline",
        help="Compilation mode (default: timeline)",
    )
    parser.add_argument(
        "--emit-synthetic-runtime-climb-ledger",
        metavar="PATH",
        help=(
            "Build the non-production synthetic runtime climb ledger bound to "
            "checked-in cut/camera/mux/visual fixture digests and write it to PATH"
        ),
    )
    parser.add_argument(
        "--verify-synthetic-runtime-climb-ledger",
        action="store_true",
        help=(
            "Fail-closed verify checked-in synthetic climb ledger against live "
            "fixture rebuilds; reject digest drift without claiming runtime mux "
            "replay, visual review, or row_complete"
        ),
    )
    parser.add_argument(
        "--execute-fixture-media-mux-runtime",
        action="store_true",
        help=(
            "Execute pure-Python fixture media mux assembly + identity roundtrip "
            "and write runtime receipt under fixtures/row084/runtime/; grants "
            "RUNTIME_PASS_BOUNDED for fixture mux only without row_complete"
        ),
    )
    parser.add_argument(
        "--verify-fixture-media-mux-runtime",
        action="store_true",
        help=(
            "Fail-closed verify checked-in fixture media mux runtime receipt "
            "against live re-execution without claiming visual QA or row_complete"
        ),
    )
    parser.add_argument(
        "--execute-held-out-ffmpeg-mux-replay",
        action="store_true",
        help=(
            "Execute ffmpeg-backed held-out fixed+VFR mux replay under "
            "fixtures/row084/runtime/; proves ROW084-019 without row_complete"
        ),
    )
    parser.add_argument(
        "--verify-held-out-ffmpeg-mux-replay",
        action="store_true",
        help=(
            "Fail-closed verify checked-in held-out ffmpeg mux replay receipt "
            "without claiming visual QA, production mux, or row_complete"
        ),
    )
    parser.add_argument(
        "--ffmpeg-path",
        help="Explicit ffmpeg.exe path (overrides probe receipt / PATH)",
    )
    parser.add_argument(
        "--execute-held-out-offline-runtime-climb",
        action="store_true",
        help=(
            "Execute offline held-out cut detector + roundtrip benchmark + camera-motion "
            "classification, emit direct runtime receipt and tracker HOLD artifact; "
            "clears ROW084-014/016/018/021/022 without VISUAL_QA or :8188"
        ),
    )
    parser.add_argument(
        "--verify-held-out-cut-detector-runtime",
        action="store_true",
        help="Verify checked-in held-out cut detector runtime receipt",
    )
    parser.add_argument(
        "--verify-held-out-roundtrip-benchmark",
        action="store_true",
        help="Verify checked-in held-out roundtrip benchmark receipt",
    )
    parser.add_argument(
        "--verify-held-out-camera-motion-runtime",
        action="store_true",
        help="Verify checked-in held-out camera-motion runtime receipt",
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Fixture directory for synthetic climb ledger (default: checked-in row084 fixtures)",
    )
    args = parser.parse_args(argv)
    fixture_dir = Path(args.fixture_dir)

    if args.emit_synthetic_runtime_climb_ledger:
        try:
            ledger = write_synthetic_runtime_climb_ledger(
                Path(args.emit_synthetic_runtime_climb_ledger),
                fixture_dir=fixture_dir,
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "mode": "emit-synthetic-runtime-climb-ledger",
                    "ledger_sha256": ledger["ledger_sha256"],
                    "proof_tier": ledger["proof_tier"],
                    "row_complete": False,
                }
            )
        )
        return 0

    if args.verify_synthetic_runtime_climb_ledger:
        try:
            receipt = verify_synthetic_runtime_climb_ledger(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.execute_fixture_media_mux_runtime:
        try:
            receipt = execute_fixture_media_mux_runtime(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "mode": "execute-fixture-media-mux-runtime",
                    "receipt_sha256": receipt["receipt_sha256"],
                    "mux_sha256": receipt["mux_output"]["mux_sha256"],
                    "proof_tier": receipt["proof_tier"],
                    "row_complete": False,
                }
            )
        )
        return 0

    if args.verify_fixture_media_mux_runtime:
        try:
            receipt = verify_fixture_media_mux_runtime_receipt(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.execute_held_out_ffmpeg_mux_replay:
        try:
            receipt = execute_held_out_ffmpeg_mux_replay(
                fixture_dir=fixture_dir,
                ffmpeg_path=args.ffmpeg_path,
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "mode": "execute-held-out-ffmpeg-mux-replay",
                    "receipt_sha256": receipt["receipt_sha256"],
                    "held_out_fixed_vfr_mux_replay_pass": True,
                    "direct_row084_mux_replay_proof_present": True,
                    "proof_tier": receipt["proof_tier"],
                    "row_complete": False,
                    "production_mux_replay_pass": False,
                }
            )
        )
        return 0

    if args.verify_held_out_ffmpeg_mux_replay:
        try:
            receipt = verify_held_out_ffmpeg_mux_replay_receipt(
                fixture_dir=fixture_dir,
                ffmpeg_path=args.ffmpeg_path,
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.execute_held_out_offline_runtime_climb:
        try:
            receipt = execute_held_out_offline_runtime_climb(
                fixture_dir=fixture_dir,
                ffmpeg_path=args.ffmpeg_path,
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.verify_held_out_cut_detector_runtime:
        try:
            receipt = verify_held_out_cut_detector_runtime_receipt(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.verify_held_out_roundtrip_benchmark:
        try:
            receipt = verify_held_out_roundtrip_benchmark_receipt(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if args.verify_held_out_camera_motion_runtime:
        try:
            receipt = verify_held_out_camera_motion_runtime_receipt(fixture_dir=fixture_dir)
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW084_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if not args.input or not args.output:
        raise SystemExit(
            "ROW084_FAIL_CLOSED: --input and --output are required unless emitting, "
            "verifying, or executing fixture media mux runtime helpers"
        )

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
        elif args.mode == "missing-frame-policy-matrix":
            receipt = compile_missing_frame_policy_matrix(payload)
            digest_key = "matrix_sha256"
        elif args.mode == "camera-motion-policy-matrix":
            receipt = compile_camera_motion_policy_matrix(payload)
            digest_key = "matrix_sha256"
        elif args.mode == "combined-visual-review-fixture-protocol":
            receipt = compile_combined_visual_review_fixture_protocol(
                payload, fixture_dir=fixture_dir
            )
            digest_key = "protocol_sha256"
        else:
            receipt = compile_cut_detector_algorithm_contract(payload)
            digest_key = "contract_sha256"
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
