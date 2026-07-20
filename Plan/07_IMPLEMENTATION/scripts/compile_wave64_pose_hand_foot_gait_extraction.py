#!/usr/bin/env python3
"""Fail-closed Row086 pose/hand/foot/gait extraction compiler.

Compiles fixture landmark/trajectory/phase packets into a content-addressed
manifest. Production completion remains blocked until Rows084-085, annotated
benchmarks, runtime receipts, and combined visual review authorities pass.
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


ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "manifest_id",
    "revision",
    "run_id",
    "scene_id",
    "shot_id",
    "take_id",
    "is_synthetic",
    "video_sha256",
    "timeline_binding",
    "owner_track_binding",
    "detector_stack",
    "dependency_authority",
    "runtime_authority",
    "instances",
    "thresholds",
    "provenance",
}

ALLOWED_TIMELINE_BINDING_FIELDS = {
    "timeline_id",
    "timeline_sha256",
    "frame_count",
    "frame_rate",
    "frame_time_origin_seconds",
}

ALLOWED_OWNER_TRACK_BINDING_FIELDS = {
    "tracking_manifest_id",
    "tracking_manifest_sha256",
    "owner_id",
    "track_id",
}

ALLOWED_DETECTOR_STACK_FIELDS = {
    "pose_detector_id",
    "hand_detector_id",
    "foot_detector_id",
    "gait_estimator_id",
    "revision",
    "parameter_digest_sha256",
}

ALLOWED_INSTANCE_FIELDS = {
    "instance_id",
    "owner_id",
    "track_id",
    "landmarks",
    "trajectories",
    "gait_phases",
    "contact_phases",
}

ALLOWED_LANDMARK_FIELDS = {
    "landmark_id",
    "landmark_class",
    "side",
    "frame_index",
    "pts",
    "x",
    "y",
    "confidence",
    "observation_state",
}

ALLOWED_TRAJECTORY_FIELDS = {
    "landmark_id",
    "samples",
}

ALLOWED_TRAJECTORY_SAMPLE_FIELDS = {
    "frame_index",
    "pts",
    "x",
    "y",
    "vx",
    "vy",
    "confidence",
    "observation_state",
}

ALLOWED_GAIT_PHASE_FIELDS = {
    "side",
    "phase",
    "frame_index",
    "pts",
    "confidence",
}

ALLOWED_CONTACT_PHASE_FIELDS = {
    "effector",
    "phase",
    "frame_index",
    "pts",
    "target_owner_id",
    "confidence",
}

ALLOWED_THRESHOLD_FIELDS = {
    "min_landmark_confidence",
    "max_trajectory_gap_frames",
    "max_fabricated_hidden_joint_count",
    "min_gait_phase_confidence",
    "min_contact_phase_confidence",
}

ALLOWED_LANDMARK_CLASSES = {
    "body",
    "hand",
    "foot",
}

ALLOWED_SIDES = {"left", "right", "center", "none"}
ALLOWED_OBSERVATION_STATES = {
    "observed",
    "inferred",
    "occluded",
    "outside_frame",
    "unknown",
    "invalid",
}
HIDDEN_OR_UNKNOWN_STATES = {"occluded", "outside_frame", "unknown", "invalid"}
ALLOWED_GAIT_PHASES = {
    "stance",
    "swing",
    "heel_strike",
    "sole_contact",
    "toe_off",
}
ALLOWED_CONTACT_PHASES = {
    "approach",
    "contact",
    "compression",
    "recoil",
    "release",
    "settle",
}
ALLOWED_EFFECTORS = {
    "hand_left",
    "hand_right",
    "foot_left",
    "foot_right",
    "body",
}
SHA256_HEX_CHARS = set("0123456789abcdef")
REQUIRED_LANDMARK_CLASSES = {"body", "hand", "foot"}
CONTENT_ADDRESSED_EXCLUDED_FIELDS = frozenset({"created_at", "manifest_sha256"})
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = (
    REPO_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Wave64" / "fixtures" / "row086"
)

# Checked-in synthetic landmark / gait / contact-phase fixture packets.
BENCHMARK_FIXTURE_PACKETS: tuple[dict[str, str], ...] = (
    {
        "name": "case_visible_landmark_trajectory.json",
        "role": "visible_landmark_trajectory",
        "case_id": "visible_landmark_trajectory",
    },
    {
        "name": "case_gait_contact_phases.json",
        "role": "gait_contact_phases",
        "case_id": "gait_contact_phases",
    },
    {
        "name": "case_partial_view_hidden_joint.json",
        "role": "partial_view_hidden_joint",
        "case_id": "partial_view_hidden_joint",
    },
)


def _assert_keys_exact(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(unknown)}")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_optional_string_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or null")
    stripped = value.strip()
    return stripped if stripped else None


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


def _expect_optional_number_or_none(value: Any, label: str) -> float | None:
    if value is None:
        return None
    return _expect_number(value, label)


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


def content_addressed_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic body hashed for replay/tamper checks.

    Wall-clock ``created_at`` and the self-referential ``manifest_sha256`` are
    excluded so identical fixture packets replay to the same digest.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return {key: value for key, value in payload.items() if key not in CONTENT_ADDRESSED_EXCLUDED_FIELDS}


def content_addressed_manifest_sha256(payload: dict[str, Any]) -> str:
    return _canonical_sha256(content_addressed_body(payload))


def verify_manifest_integrity(payload: dict[str, Any]) -> str:
    """Recompute content-addressed digest and reject tampered manifests."""
    recorded = _expect_sha256(payload.get("manifest_sha256"), "manifest_sha256")
    recomputed = content_addressed_manifest_sha256(payload)
    if recorded != recomputed:
        raise ValueError(
            "manifest_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    return recomputed


def load_fixture_packet(name: str, *, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load a checked-in Row086 fixture packet by filename."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row086 fixture packet missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row086 fixture packet must be a JSON object: {path}")
    return payload


def fixture_file_sha256(name: str, *, fixture_dir: Path | None = None) -> str:
    """Return the lowercase sha256 of a checked-in fixture packet file bytes."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row086 fixture packet missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_timeline_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("timeline_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_TIMELINE_BINDING_FIELDS, "timeline_binding")
    frame_rate = _expect_number(raw.get("frame_rate"), "timeline_binding.frame_rate")
    if frame_rate <= 0:
        raise ValueError("timeline_binding.frame_rate must be > 0")
    return {
        "timeline_id": _expect_non_empty_string(raw.get("timeline_id"), "timeline_binding.timeline_id"),
        "timeline_sha256": _expect_sha256(raw.get("timeline_sha256"), "timeline_binding.timeline_sha256"),
        "frame_count": _expect_positive_int(raw.get("frame_count"), "timeline_binding.frame_count"),
        "frame_rate": frame_rate,
        "frame_time_origin_seconds": _expect_number(
            raw.get("frame_time_origin_seconds"), "timeline_binding.frame_time_origin_seconds"
        ),
    }


def _validate_owner_track_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("owner_track_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_OWNER_TRACK_BINDING_FIELDS, "owner_track_binding")
    return {
        "tracking_manifest_id": _expect_non_empty_string(
            raw.get("tracking_manifest_id"), "owner_track_binding.tracking_manifest_id"
        ),
        "tracking_manifest_sha256": _expect_sha256(
            raw.get("tracking_manifest_sha256"), "owner_track_binding.tracking_manifest_sha256"
        ),
        "owner_id": _expect_non_empty_string(raw.get("owner_id"), "owner_track_binding.owner_id"),
        "track_id": _expect_non_empty_string(raw.get("track_id"), "owner_track_binding.track_id"),
    }


def _validate_detector_stack(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("detector_stack must be an object")
    _assert_keys_exact(raw, ALLOWED_DETECTOR_STACK_FIELDS, "detector_stack")
    return {
        "pose_detector_id": _expect_non_empty_string(
            raw.get("pose_detector_id"), "detector_stack.pose_detector_id"
        ),
        "hand_detector_id": _expect_non_empty_string(
            raw.get("hand_detector_id"), "detector_stack.hand_detector_id"
        ),
        "foot_detector_id": _expect_non_empty_string(
            raw.get("foot_detector_id"), "detector_stack.foot_detector_id"
        ),
        "gait_estimator_id": _expect_non_empty_string(
            raw.get("gait_estimator_id"), "detector_stack.gait_estimator_id"
        ),
        "revision": _expect_non_empty_string(raw.get("revision"), "detector_stack.revision"),
        "parameter_digest_sha256": _expect_sha256(
            raw.get("parameter_digest_sha256"), "detector_stack.parameter_digest_sha256"
        ),
    }


def _validate_observation_state(value: Any, label: str) -> str:
    state = _expect_non_empty_string(value, label)
    if state not in ALLOWED_OBSERVATION_STATES:
        raise ValueError(f"{label} must be one of {sorted(ALLOWED_OBSERVATION_STATES)}")
    return state


def _validate_coordinates_for_state(
    *,
    x: Any,
    y: Any,
    observation_state: str,
    label: str,
) -> tuple[float | None, float | None]:
    x_value = _expect_optional_number_or_none(x, f"{label}.x")
    y_value = _expect_optional_number_or_none(y, f"{label}.y")
    if observation_state in HIDDEN_OR_UNKNOWN_STATES:
        if x_value is not None or y_value is not None:
            raise ValueError(
                f"{label} partial-view guard: {observation_state} landmarks must not fabricate coordinates"
            )
        return None, None
    if observation_state in {"observed", "inferred"}:
        if x_value is None or y_value is None:
            raise ValueError(f"{label} {observation_state} landmarks require x and y coordinates")
    return x_value, y_value


def _validate_landmark(raw: Any, *, index: int, frame_count: int, instance_label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{instance_label}.landmarks[{index}] must be an object")
    label = f"{instance_label}.landmarks[{index}]"
    _assert_keys_exact(raw, ALLOWED_LANDMARK_FIELDS, label)

    landmark_class = _expect_non_empty_string(raw.get("landmark_class"), f"{label}.landmark_class")
    if landmark_class not in ALLOWED_LANDMARK_CLASSES:
        raise ValueError(f"{label}.landmark_class must be one of {sorted(ALLOWED_LANDMARK_CLASSES)}")
    side = _expect_non_empty_string(raw.get("side"), f"{label}.side")
    if side not in ALLOWED_SIDES:
        raise ValueError(f"{label}.side must be one of {sorted(ALLOWED_SIDES)}")
    if landmark_class in {"hand", "foot"} and side not in {"left", "right"}:
        raise ValueError(f"{label} {landmark_class} requires side left or right")

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")

    observation_state = _validate_observation_state(raw.get("observation_state"), f"{label}.observation_state")
    x_value, y_value = _validate_coordinates_for_state(
        x=raw.get("x"),
        y=raw.get("y"),
        observation_state=observation_state,
        label=label,
    )
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")
    if observation_state in HIDDEN_OR_UNKNOWN_STATES and confidence > 0.0 and observation_state != "occluded":
        # Occluded may retain detector confidence; unknown/outside/invalid must be zeroed.
        if observation_state in {"outside_frame", "unknown", "invalid"} and confidence != 0.0:
            raise ValueError(f"{label} {observation_state} confidence must be 0.0")

    return {
        "landmark_id": _expect_non_empty_string(raw.get("landmark_id"), f"{label}.landmark_id"),
        "landmark_class": landmark_class,
        "side": side,
        "frame_index": frame_index,
        "pts": pts,
        "x": x_value,
        "y": y_value,
        "confidence": confidence,
        "observation_state": observation_state,
    }


def _validate_trajectory_sample(
    raw: Any,
    *,
    index: int,
    trajectory_label: str,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{trajectory_label}.samples[{index}] must be an object")
    label = f"{trajectory_label}.samples[{index}]"
    _assert_keys_exact(raw, ALLOWED_TRAJECTORY_SAMPLE_FIELDS, label)

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    if previous_frame is not None:
        if frame_index <= previous_frame:
            raise ValueError(f"{label}.frame_index must be unique and strictly increasing")
        if pts <= previous_pts:
            raise ValueError(f"{label}.pts must be unique and strictly increasing")

    observation_state = _validate_observation_state(raw.get("observation_state"), f"{label}.observation_state")
    x_value, y_value = _validate_coordinates_for_state(
        x=raw.get("x"),
        y=raw.get("y"),
        observation_state=observation_state,
        label=label,
    )
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    vx = _expect_optional_number_or_none(raw.get("vx"), f"{label}.vx")
    vy = _expect_optional_number_or_none(raw.get("vy"), f"{label}.vy")
    if observation_state in HIDDEN_OR_UNKNOWN_STATES and (vx is not None or vy is not None):
        raise ValueError(f"{label} partial-view guard: hidden/unknown samples must not fabricate velocity")

    return {
        "frame_index": frame_index,
        "pts": pts,
        "x": x_value,
        "y": y_value,
        "vx": vx,
        "vy": vy,
        "confidence": confidence,
        "observation_state": observation_state,
    }


def _validate_trajectory(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    instance_label: str,
    known_landmark_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{instance_label}.trajectories[{index}] must be an object")
    label = f"{instance_label}.trajectories[{index}]"
    _assert_keys_exact(raw, ALLOWED_TRAJECTORY_FIELDS, label)
    landmark_id = _expect_non_empty_string(raw.get("landmark_id"), f"{label}.landmark_id")
    if landmark_id not in known_landmark_ids:
        raise ValueError(f"{label}.landmark_id must reference a declared landmark_id")

    samples_raw = raw.get("samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise ValueError(f"{label}.samples must be a non-empty list")
    samples: list[dict[str, Any]] = []
    previous_frame: int | None = None
    previous_pts: int | None = None
    for sample_idx, sample_raw in enumerate(samples_raw):
        sample = _validate_trajectory_sample(
            sample_raw,
            index=sample_idx,
            trajectory_label=label,
            frame_count=frame_count,
            previous_frame=previous_frame,
            previous_pts=previous_pts,
        )
        previous_frame = sample["frame_index"]
        previous_pts = sample["pts"]
        samples.append(sample)

    gap_frames = 0
    for left, right in zip(samples, samples[1:], strict=False):
        gap = right["frame_index"] - left["frame_index"] - 1
        if gap > gap_frames:
            gap_frames = gap

    return {
        "landmark_id": landmark_id,
        "sample_count": len(samples),
        "first_frame": samples[0]["frame_index"],
        "last_frame": samples[-1]["frame_index"],
        "max_gap_frames": gap_frames,
        "samples": samples,
    }


def _validate_gait_phase(raw: Any, *, index: int, frame_count: int, instance_label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{instance_label}.gait_phases[{index}] must be an object")
    label = f"{instance_label}.gait_phases[{index}]"
    _assert_keys_exact(raw, ALLOWED_GAIT_PHASE_FIELDS, label)
    side = _expect_non_empty_string(raw.get("side"), f"{label}.side")
    if side not in {"left", "right"}:
        raise ValueError(f"{label}.side must be left or right")
    phase = _expect_non_empty_string(raw.get("phase"), f"{label}.phase")
    if phase not in ALLOWED_GAIT_PHASES:
        raise ValueError(f"{label}.phase must be one of {sorted(ALLOWED_GAIT_PHASES)}")
    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")
    return {
        "side": side,
        "phase": phase,
        "frame_index": frame_index,
        "pts": pts,
        "confidence": confidence,
    }


def _validate_contact_phase(raw: Any, *, index: int, frame_count: int, instance_label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{instance_label}.contact_phases[{index}] must be an object")
    label = f"{instance_label}.contact_phases[{index}]"
    _assert_keys_exact(raw, ALLOWED_CONTACT_PHASE_FIELDS, label)
    effector = _expect_non_empty_string(raw.get("effector"), f"{label}.effector")
    if effector not in ALLOWED_EFFECTORS:
        raise ValueError(f"{label}.effector must be one of {sorted(ALLOWED_EFFECTORS)}")
    phase = _expect_non_empty_string(raw.get("phase"), f"{label}.phase")
    if phase not in ALLOWED_CONTACT_PHASES:
        raise ValueError(f"{label}.phase must be one of {sorted(ALLOWED_CONTACT_PHASES)}")
    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")
    return {
        "effector": effector,
        "phase": phase,
        "frame_index": frame_index,
        "pts": pts,
        "target_owner_id": _expect_non_empty_string(
            raw.get("target_owner_id"), f"{label}.target_owner_id"
        ),
        "confidence": confidence,
    }


def _compile_instance(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    bound_owner_id: str,
    bound_track_id: str,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"instances[{index}] must be an object")
    label = f"instances[{index}]"
    _assert_keys_exact(raw, ALLOWED_INSTANCE_FIELDS, label)

    owner_id = _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id")
    track_id = _expect_non_empty_string(raw.get("track_id"), f"{label}.track_id")
    if owner_id != bound_owner_id:
        raise ValueError(f"{label}.owner_id must match owner_track_binding.owner_id")
    if track_id != bound_track_id:
        raise ValueError(f"{label}.track_id must match owner_track_binding.track_id")

    landmarks_raw = raw.get("landmarks")
    if not isinstance(landmarks_raw, list) or not landmarks_raw:
        raise ValueError(f"{label}.landmarks must be a non-empty list")
    landmarks = [
        _validate_landmark(item, index=idx, frame_count=frame_count, instance_label=label)
        for idx, item in enumerate(landmarks_raw)
    ]
    landmark_ids = {item["landmark_id"] for item in landmarks}
    if len(landmark_ids) != len(landmarks):
        raise ValueError(f"{label}.landmarks landmark_id values must be unique")
    classes_present = {item["landmark_class"] for item in landmarks}
    missing_classes = sorted(REQUIRED_LANDMARK_CLASSES - classes_present)
    if missing_classes:
        raise ValueError(
            f"{label} landmark taxonomy incomplete; missing required classes: {', '.join(missing_classes)}"
        )

    trajectories_raw = raw.get("trajectories")
    if not isinstance(trajectories_raw, list) or not trajectories_raw:
        raise ValueError(f"{label}.trajectories must be a non-empty list")
    trajectories = [
        _validate_trajectory(
            item,
            index=idx,
            frame_count=frame_count,
            instance_label=label,
            known_landmark_ids=landmark_ids,
        )
        for idx, item in enumerate(trajectories_raw)
    ]

    gait_raw = raw.get("gait_phases")
    if not isinstance(gait_raw, list) or not gait_raw:
        raise ValueError(f"{label}.gait_phases must be a non-empty list")
    gait_phases = [
        _validate_gait_phase(item, index=idx, frame_count=frame_count, instance_label=label)
        for idx, item in enumerate(gait_raw)
    ]
    gait_phases = sorted(gait_phases, key=lambda item: (item["frame_index"], item["side"], item["phase"]))

    contact_raw = raw.get("contact_phases")
    if not isinstance(contact_raw, list) or not contact_raw:
        raise ValueError(f"{label}.contact_phases must be a non-empty list")
    contact_phases = [
        _validate_contact_phase(item, index=idx, frame_count=frame_count, instance_label=label)
        for idx, item in enumerate(contact_raw)
    ]
    contact_phases = sorted(
        contact_phases, key=lambda item: (item["frame_index"], item["effector"], item["phase"])
    )

    fabricated_hidden_joint_count = 0
    for landmark in landmarks:
        if landmark["observation_state"] in HIDDEN_OR_UNKNOWN_STATES and (
            landmark["x"] is not None or landmark["y"] is not None
        ):
            fabricated_hidden_joint_count += 1

    return {
        "instance_id": _expect_non_empty_string(raw.get("instance_id"), f"{label}.instance_id"),
        "owner_id": owner_id,
        "track_id": track_id,
        "landmark_count": len(landmarks),
        "trajectory_count": len(trajectories),
        "gait_phase_count": len(gait_phases),
        "contact_phase_count": len(contact_phases),
        "landmark_classes_present": sorted(classes_present),
        "fabricated_hidden_joint_count": fabricated_hidden_joint_count,
        "landmarks": landmarks,
        "trajectories": trajectories,
        "gait_phases": gait_phases,
        "contact_phases": contact_phases,
        "ownership_bound": True,
    }


def _validate_thresholds(raw: Any) -> dict[str, float | int]:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    _assert_keys_exact(raw, ALLOWED_THRESHOLD_FIELDS, "thresholds")
    result: dict[str, float | int] = {}
    for key in sorted(ALLOWED_THRESHOLD_FIELDS):
        if key.startswith("min_"):
            value = _expect_number(raw.get(key), f"thresholds.{key}")
            if value < 0 or value > 1:
                raise ValueError(f"thresholds.{key} must be within [0, 1]")
            result[key] = value
        else:
            result[key] = _expect_non_negative_int(raw.get(key), f"thresholds.{key}")
    if result["max_fabricated_hidden_joint_count"] != 0:
        raise ValueError("thresholds.max_fabricated_hidden_joint_count must equal 0")
    return result


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    timeline_binding = _validate_timeline_binding(payload.get("timeline_binding"))
    owner_track_binding = _validate_owner_track_binding(payload.get("owner_track_binding"))
    detector_stack = _validate_detector_stack(payload.get("detector_stack"))

    dependency_raw = payload.get("dependency_authority")
    if not isinstance(dependency_raw, dict):
        raise ValueError("dependency_authority must be an object")
    _assert_keys_exact(dependency_raw, {"row084_complete", "row085_complete"}, "dependency_authority")
    row084_complete = _expect_boolean(dependency_raw.get("row084_complete"), "dependency_authority.row084_complete")
    row085_complete = _expect_boolean(dependency_raw.get("row085_complete"), "dependency_authority.row085_complete")

    runtime_raw = payload.get("runtime_authority")
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_allowed = {
        "annotated_benchmark_pass",
        "runtime_receipt_present",
        "combined_landmark_track_contact_audio_review_present",
    }
    _assert_keys_exact(runtime_raw, runtime_allowed, "runtime_authority")
    annotated_benchmark_pass = _expect_boolean(
        runtime_raw.get("annotated_benchmark_pass"), "runtime_authority.annotated_benchmark_pass"
    )
    runtime_receipt_present = _expect_boolean(
        runtime_raw.get("runtime_receipt_present"), "runtime_authority.runtime_receipt_present"
    )
    combined_review_present = _expect_boolean(
        runtime_raw.get("combined_landmark_track_contact_audio_review_present"),
        "runtime_authority.combined_landmark_track_contact_audio_review_present",
    )

    instances_raw = payload.get("instances")
    if not isinstance(instances_raw, list) or not instances_raw:
        raise ValueError("instances must be a non-empty list")

    instances: list[dict[str, Any]] = []
    seen_instance_ids: set[str] = set()
    for idx, instance_raw in enumerate(instances_raw):
        compiled = _compile_instance(
            instance_raw,
            index=idx,
            frame_count=timeline_binding["frame_count"],
            bound_owner_id=owner_track_binding["owner_id"],
            bound_track_id=owner_track_binding["track_id"],
        )
        if compiled["instance_id"] in seen_instance_ids:
            raise ValueError(f"duplicate instance_id detected: {compiled['instance_id']}")
        seen_instance_ids.add(compiled["instance_id"])
        instances.append(compiled)

    thresholds = _validate_thresholds(payload.get("thresholds"))

    threshold_violations: list[str] = []
    fabricated_total = sum(item["fabricated_hidden_joint_count"] for item in instances)
    if fabricated_total > thresholds["max_fabricated_hidden_joint_count"]:
        threshold_violations.append("max_fabricated_hidden_joint_count")

    for instance in instances:
        for landmark in instance["landmarks"]:
            if (
                landmark["observation_state"] in {"observed", "inferred"}
                and landmark["confidence"] < thresholds["min_landmark_confidence"]
            ):
                threshold_violations.append("min_landmark_confidence")
                break
        for trajectory in instance["trajectories"]:
            if trajectory["max_gap_frames"] > thresholds["max_trajectory_gap_frames"]:
                threshold_violations.append("max_trajectory_gap_frames")
                break
        for gait in instance["gait_phases"]:
            if gait["confidence"] < thresholds["min_gait_phase_confidence"]:
                threshold_violations.append("min_gait_phase_confidence")
                break
        for contact in instance["contact_phases"]:
            if contact["confidence"] < thresholds["min_contact_phase_confidence"]:
                threshold_violations.append("min_contact_phase_confidence")
                break
    threshold_violations = sorted(set(threshold_violations))

    dependency_ready = row084_complete and row085_complete
    runtime_ready = annotated_benchmark_pass and runtime_receipt_present and combined_review_present
    contact_phase_certification_allowed = (
        dependency_ready and runtime_ready and not threshold_violations and fabricated_total == 0
    )
    production_completion_allowed = False
    row_complete = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    elif threshold_violations or not runtime_ready:
        authority_ceiling = "technical"
        status = "technical_partial"
    else:
        authority_ceiling = "technical"
        status = "technical_partial"

    hold_reasons: list[str] = []
    if not row084_complete:
        hold_reasons.append("dependency_row084_incomplete")
    if not row085_complete:
        hold_reasons.append("dependency_row085_incomplete")
    if not annotated_benchmark_pass:
        hold_reasons.append("annotated_benchmark_absent")
    if not runtime_receipt_present:
        hold_reasons.append("runtime_receipt_absent")
    if not combined_review_present:
        hold_reasons.append("combined_landmark_track_contact_audio_review_absent")
    if threshold_violations:
        hold_reasons.append("threshold_violations:" + ",".join(threshold_violations))

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_pose_hand_foot_gait_extraction.py",
            "compiler_revision": "row086_fail_closed_v1",
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "pose_hand_foot_gait_extraction_manifest",
        "manifest_id": _expect_non_empty_string(payload.get("manifest_id"), "manifest_id"),
        "revision": _expect_non_empty_string(payload.get("revision"), "revision"),
        "run_id": _expect_non_empty_string(payload.get("run_id"), "run_id"),
        "scene_id": _expect_non_empty_string(payload.get("scene_id"), "scene_id"),
        "shot_id": _expect_non_empty_string(payload.get("shot_id"), "shot_id"),
        "take_id": _expect_non_empty_string(payload.get("take_id"), "take_id"),
        "is_synthetic": _expect_boolean(payload.get("is_synthetic"), "is_synthetic"),
        "video_sha256": _expect_sha256(payload.get("video_sha256"), "video_sha256"),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "timeline_binding": timeline_binding,
        "owner_track_binding": owner_track_binding,
        "detector_stack": detector_stack,
        "dependency_authority": {
            "row084_complete": row084_complete,
            "row085_complete": row085_complete,
            "dependency_ready": dependency_ready,
        },
        "runtime_authority": {
            "annotated_benchmark_pass": annotated_benchmark_pass,
            "runtime_receipt_present": runtime_receipt_present,
            "combined_landmark_track_contact_audio_review_present": combined_review_present,
            "runtime_ready": runtime_ready,
        },
        "instances": instances,
        "thresholds": thresholds,
        "threshold_violations": threshold_violations,
        "authority_summary": {
            "instance_count": len(instances),
            "landmark_count": sum(item["landmark_count"] for item in instances),
            "trajectory_count": sum(item["trajectory_count"] for item in instances),
            "gait_phase_count": sum(item["gait_phase_count"] for item in instances),
            "contact_phase_count": sum(item["contact_phase_count"] for item in instances),
            "fabricated_hidden_joint_count": fabricated_total,
            "contact_phase_certification_allowed": contact_phase_certification_allowed,
            "hold_reasons": hold_reasons,
        },
        "authority_ceiling": authority_ceiling,
        "production_completion_allowed": production_completion_allowed,
        "row_complete": row_complete,
        "provenance": provenance,
    }
    # Content-addressed digest excludes wall-clock created_at for deterministic replay.
    manifest_sha256 = content_addressed_manifest_sha256(receipt_body)
    receipt_body["manifest_sha256"] = manifest_sha256
    return receipt_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a fail-closed Row086 pose/hand/foot/gait extraction manifest."
    )
    parser.add_argument("--input", help="Path to pose/gait input packet JSON")
    parser.add_argument("--output", help="Path to write compiled extraction manifest JSON")
    parser.add_argument(
        "--verify-fixture-replay",
        action="store_true",
        help=(
            "Fail-closed compile checked-in landmark/phase fixtures and verify "
            "content-addressed replay/tamper hashes without claiming annotated "
            "benchmark pass or Rows084/085 acceptance"
        ),
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Fixture directory for replay verification (default: checked-in row086 fixtures)",
    )
    args = parser.parse_args(argv)

    if args.verify_fixture_replay:
        directory = Path(args.fixture_dir)
        receipts: list[dict[str, Any]] = []
        try:
            for packet_meta in BENCHMARK_FIXTURE_PACKETS:
                name = packet_meta["name"]
                packet = load_fixture_packet(name, fixture_dir=directory)
                compiled = compile_manifest(packet)
                digest = verify_manifest_integrity(compiled)
                if compiled["row_complete"] or compiled["production_completion_allowed"]:
                    raise ValueError(f"{name}: fixture must remain non-complete")
                if compiled["dependency_authority"].get("row084_complete"):
                    raise ValueError(f"{name}: must not claim row084_complete")
                if compiled["dependency_authority"].get("row085_complete"):
                    raise ValueError(f"{name}: must not claim row085_complete")
                if compiled["runtime_authority"].get("annotated_benchmark_pass"):
                    raise ValueError(f"{name}: must not claim annotated_benchmark_pass")
                receipts.append(
                    {
                        "fixture_name": name,
                        "role": packet_meta["role"],
                        "fixture_file_sha256": fixture_file_sha256(name, fixture_dir=directory),
                        "compiled_manifest_sha256": digest,
                        "row_complete": False,
                    }
                )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW086_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "verifier": "verify_fixture_replay",
                    "fixture_count": len(receipts),
                    "fixtures": receipts,
                    "annotated_benchmark_pass": False,
                    "row084_acceptance_claimed": False,
                    "row085_acceptance_claimed": False,
                    "row_complete": False,
                    "authority_ceiling": "fixture_synthetic_only",
                }
            )
        )
        return 0

    if not args.input or not args.output:
        raise SystemExit(
            "ROW086_FAIL_CLOSED: --input and --output are required unless verifying "
            "fixture replay"
        )

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input packet must be a JSON object")
    try:
        receipt = compile_manifest(payload)
    except ValueError as exc:
        raise SystemExit(f"ROW086_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_sha256": receipt["manifest_sha256"],
                "row_complete": False,
                "contact_phase_certification_allowed": receipt["authority_summary"][
                    "contact_phase_certification_allowed"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
