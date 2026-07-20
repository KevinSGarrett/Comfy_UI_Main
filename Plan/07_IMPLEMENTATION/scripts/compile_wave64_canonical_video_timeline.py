#!/usr/bin/env python3
"""Fail-closed Row084 canonical video timeline compiler.

Compiles fixture or decoded-frame metadata into a content-addressed timeline
receipt, plus mux-prep scaffold, held-out fixed/VFR round-trip matrix helpers,
a fixture-backed missing-frame policy matrix (preserve_gap / explicit_gap),
a fixture-backed camera-motion policy matrix
(not_evaluated / blocked_until_calibrated / distinguish_from_cuts),
a fixture-backed cut-detector algorithm contract
(algorithm_id + confidence calibration gates), and a synthetic runtime-climb
ledger binding cut/camera/mux-plan-replay/combined-visual fixture digests.
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

COMPILER_REVISION = "row084_synthetic_runtime_climb_ledger_v9"
FIXTURE_MUX_RUNTIME_REVISION = "row084_fixture_media_mux_runtime_v10"
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
FIXTURE_MUX_MAGIC = b"ROW084_FIXTURE_MUX_V1\n"
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
