#!/usr/bin/env python3
"""Fail-closed Row087 motion/force cue measurement compiler.

Compiles fixture motion/force packets into a content-addressed manifest.
Production completion remains blocked until Rows084-086, calibrated
trajectory benchmarks, runtime receipts, and combined visual review are
satisfied. Force proxies are always labeled nonphysical estimates.
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
    "flow_binding",
    "camera_model",
    "coordinate_spaces",
    "dependency_authority",
    "runtime_authority",
    "motion_samples",
    "force_cues",
    "metrics",
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

ALLOWED_FLOW_BINDING_FIELDS = {
    "optical_flow_algorithm",
    "field_sha256",
    "frame_pair_count",
    "units",
}

ALLOWED_CAMERA_MODEL_FIELDS = {
    "model_id",
    "compensation_mode",
    "transform_sha256",
    "planned_motion_supported",
}

ALLOWED_SAMPLE_FIELDS = {
    "sample_id",
    "owner_id",
    "region_class",
    "frame_index",
    "pts",
    "local_velocity_xy",
    "actor_relative_velocity_xy",
    "residual_after_camera_xy",
    "acceleration_xy",
    "velocity_units",
    "acceleration_units",
    "camera_motion_dominant",
    "confidence",
}

ALLOWED_FORCE_CUE_FIELDS = {
    "cue_id",
    "owner_id",
    "cue_class",
    "frame_index",
    "force_proxy",
    "force_is_estimate",
    "force_units",
    "uncertainty",
    "confidence",
}

ALLOWED_REGION_CLASSES = {
    "actor",
    "limb",
    "hand",
    "foot",
    "clothing_region",
    "prop",
    "surface",
    "background",
}

ALLOWED_CUE_CLASSES = {"sliding", "scuffing", "fabric", "approach", "impact", "none"}
ALLOWED_COMPENSATION_MODES = {"static_translation", "planned_transform", "unsupported"}
REQUIRED_COORDINATE_SPACES = {
    "local_image",
    "actor_relative",
    "camera_compensated",
    "surface_relative",
}
ALLOWED_COORDINATE_SPACES = REQUIRED_COORDINATE_SPACES | {"object_relative"}
ALLOWED_METRIC_FIELDS = {
    "motion_sample_count",
    "owner_count",
    "sliding_cue_count",
    "scuffing_cue_count",
    "fabric_cue_count",
    "impact_cue_count",
    "approach_cue_count",
    "force_estimate_count",
    "camera_dominant_sample_count",
}
ALLOWED_THRESHOLD_FIELDS = {
    "max_false_actor_motion_from_camera",
    "min_sample_confidence",
    "max_force_uncertainty",
}
SHA256_HEX_CHARS = set("0123456789abcdef")


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


def _expect_optional_sha256_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _expect_sha256(value, label)


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


def _magnitude(xy: list[float]) -> float:
    return math.hypot(xy[0], xy[1])


def _validate_xy(raw: Any, label: str) -> list[float]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError(f"{label} must be a 2-number [x,y] array")
    return [_expect_number(item, f"{label}[{idx}]") for idx, item in enumerate(raw)]


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


def _validate_flow_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("flow_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_FLOW_BINDING_FIELDS, "flow_binding")
    units = _expect_non_empty_string(raw.get("units"), "flow_binding.units")
    if units != "pixels_per_frame":
        raise ValueError("flow_binding.units must equal pixels_per_frame")
    return {
        "optical_flow_algorithm": _expect_non_empty_string(
            raw.get("optical_flow_algorithm"), "flow_binding.optical_flow_algorithm"
        ),
        "field_sha256": _expect_sha256(raw.get("field_sha256"), "flow_binding.field_sha256"),
        "frame_pair_count": _expect_positive_int(
            raw.get("frame_pair_count"), "flow_binding.frame_pair_count"
        ),
        "units": units,
    }


def _validate_camera_model(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("camera_model must be an object")
    _assert_keys_exact(raw, ALLOWED_CAMERA_MODEL_FIELDS, "camera_model")
    mode = _expect_non_empty_string(raw.get("compensation_mode"), "camera_model.compensation_mode")
    if mode not in ALLOWED_COMPENSATION_MODES:
        raise ValueError(
            f"camera_model.compensation_mode must be one of {sorted(ALLOWED_COMPENSATION_MODES)}"
        )
    planned = _expect_boolean(
        raw.get("planned_motion_supported"), "camera_model.planned_motion_supported"
    )
    transform = _expect_optional_sha256_or_none(
        raw.get("transform_sha256"), "camera_model.transform_sha256"
    )
    if mode == "planned_transform":
        if not planned:
            raise ValueError("planned_transform requires planned_motion_supported=true")
        if transform is None:
            raise ValueError("planned_transform requires transform_sha256")
    if mode == "unsupported" and planned:
        raise ValueError("unsupported compensation_mode cannot claim planned_motion_supported=true")
    return {
        "model_id": _expect_non_empty_string(raw.get("model_id"), "camera_model.model_id"),
        "compensation_mode": mode,
        "transform_sha256": transform,
        "planned_motion_supported": planned,
    }


def _validate_coordinate_spaces(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("coordinate_spaces must be a non-empty list")
    spaces: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw):
        space = _expect_non_empty_string(item, f"coordinate_spaces[{idx}]")
        if space not in ALLOWED_COORDINATE_SPACES:
            raise ValueError(
                f"coordinate_spaces[{idx}] must be one of {sorted(ALLOWED_COORDINATE_SPACES)}"
            )
        if space in seen:
            raise ValueError(f"coordinate_spaces contains duplicate entry: {space}")
        seen.add(space)
        spaces.append(space)
    missing = sorted(REQUIRED_COORDINATE_SPACES - seen)
    if missing:
        raise ValueError(f"coordinate_spaces missing required spaces: {', '.join(missing)}")
    return spaces


def _validate_motion_sample(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    previous_by_owner: dict[str, tuple[int, int]],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"motion_samples[{index}] must be an object")
    label = f"motion_samples[{index}]"
    _assert_keys_exact(raw, ALLOWED_SAMPLE_FIELDS, label)

    owner_id = _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id")
    region_class = _expect_non_empty_string(raw.get("region_class"), f"{label}.region_class")
    if region_class not in ALLOWED_REGION_CLASSES:
        raise ValueError(f"{label}.region_class must be one of {sorted(ALLOWED_REGION_CLASSES)}")

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")

    previous = previous_by_owner.get(owner_id)
    if previous is not None:
        prev_frame, prev_pts = previous
        if frame_index <= prev_frame:
            raise ValueError(f"{label}.frame_index must be unique and strictly increasing per owner")
        if pts <= prev_pts:
            raise ValueError(f"{label}.pts must be unique and strictly increasing per owner")

    velocity_units = _expect_non_empty_string(raw.get("velocity_units"), f"{label}.velocity_units")
    if velocity_units != "pixels_per_frame":
        raise ValueError(f"{label}.velocity_units must equal pixels_per_frame")
    acceleration_units = _expect_non_empty_string(
        raw.get("acceleration_units"), f"{label}.acceleration_units"
    )
    if acceleration_units != "pixels_per_frame_squared":
        raise ValueError(f"{label}.acceleration_units must equal pixels_per_frame_squared")

    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    sample = {
        "sample_id": _expect_non_empty_string(raw.get("sample_id"), f"{label}.sample_id"),
        "owner_id": owner_id,
        "region_class": region_class,
        "frame_index": frame_index,
        "pts": pts,
        "local_velocity_xy": _validate_xy(raw.get("local_velocity_xy"), f"{label}.local_velocity_xy"),
        "actor_relative_velocity_xy": _validate_xy(
            raw.get("actor_relative_velocity_xy"), f"{label}.actor_relative_velocity_xy"
        ),
        "residual_after_camera_xy": _validate_xy(
            raw.get("residual_after_camera_xy"), f"{label}.residual_after_camera_xy"
        ),
        "acceleration_xy": _validate_xy(raw.get("acceleration_xy"), f"{label}.acceleration_xy"),
        "velocity_units": velocity_units,
        "acceleration_units": acceleration_units,
        "camera_motion_dominant": _expect_boolean(
            raw.get("camera_motion_dominant"), f"{label}.camera_motion_dominant"
        ),
        "confidence": confidence,
    }
    previous_by_owner[owner_id] = (frame_index, pts)
    return sample


def _validate_force_cue(raw: Any, *, index: int, frame_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"force_cues[{index}] must be an object")
    label = f"force_cues[{index}]"
    _assert_keys_exact(raw, ALLOWED_FORCE_CUE_FIELDS, label)

    cue_class = _expect_non_empty_string(raw.get("cue_class"), f"{label}.cue_class")
    if cue_class not in ALLOWED_CUE_CLASSES:
        raise ValueError(f"{label}.cue_class must be one of {sorted(ALLOWED_CUE_CLASSES)}")

    force_is_estimate = _expect_boolean(raw.get("force_is_estimate"), f"{label}.force_is_estimate")
    if force_is_estimate is not True:
        raise ValueError(f"{label}.force_is_estimate must be true; force proxies are nonphysical estimates")

    force_units = _expect_non_empty_string(raw.get("force_units"), f"{label}.force_units")
    if force_units != "nonphysical_proxy":
        raise ValueError(f"{label}.force_units must equal nonphysical_proxy")

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")

    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    return {
        "cue_id": _expect_non_empty_string(raw.get("cue_id"), f"{label}.cue_id"),
        "owner_id": _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id"),
        "cue_class": cue_class,
        "frame_index": frame_index,
        "force_proxy": _expect_number(raw.get("force_proxy"), f"{label}.force_proxy"),
        "force_is_estimate": True,
        "force_units": force_units,
        "uncertainty": _expect_number(raw.get("uncertainty"), f"{label}.uncertainty"),
        "confidence": confidence,
    }


def _validate_metrics(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError("metrics must be an object")
    _assert_keys_exact(raw, ALLOWED_METRIC_FIELDS, "metrics")
    return {
        key: _expect_non_negative_int(raw.get(key), f"metrics.{key}") for key in sorted(ALLOWED_METRIC_FIELDS)
    }


def _validate_thresholds(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    _assert_keys_exact(raw, ALLOWED_THRESHOLD_FIELDS, "thresholds")
    max_false = _expect_number(
        raw.get("max_false_actor_motion_from_camera"),
        "thresholds.max_false_actor_motion_from_camera",
    )
    if max_false < 0:
        raise ValueError("thresholds.max_false_actor_motion_from_camera must be >= 0")
    min_conf = _expect_number(raw.get("min_sample_confidence"), "thresholds.min_sample_confidence")
    if min_conf < 0 or min_conf > 1:
        raise ValueError("thresholds.min_sample_confidence must be within [0, 1]")
    max_unc = _expect_number(raw.get("max_force_uncertainty"), "thresholds.max_force_uncertainty")
    if max_unc < 0:
        raise ValueError("thresholds.max_force_uncertainty must be >= 0")
    return {
        "max_false_actor_motion_from_camera": max_false,
        "min_sample_confidence": min_conf,
        "max_force_uncertainty": max_unc,
    }


def _derive_metrics(samples: list[dict[str, Any]], cues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "motion_sample_count": len(samples),
        "owner_count": len({sample["owner_id"] for sample in samples}),
        "sliding_cue_count": sum(1 for cue in cues if cue["cue_class"] == "sliding"),
        "scuffing_cue_count": sum(1 for cue in cues if cue["cue_class"] == "scuffing"),
        "fabric_cue_count": sum(1 for cue in cues if cue["cue_class"] == "fabric"),
        "impact_cue_count": sum(1 for cue in cues if cue["cue_class"] == "impact"),
        "approach_cue_count": sum(1 for cue in cues if cue["cue_class"] == "approach"),
        "force_estimate_count": sum(1 for cue in cues if cue["force_is_estimate"]),
        "camera_dominant_sample_count": sum(1 for sample in samples if sample["camera_motion_dominant"]),
    }


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    timeline_binding = _validate_timeline_binding(payload.get("timeline_binding"))
    flow_binding = _validate_flow_binding(payload.get("flow_binding"))
    camera_model = _validate_camera_model(payload.get("camera_model"))
    coordinate_spaces = _validate_coordinate_spaces(payload.get("coordinate_spaces"))

    dependency_raw = payload.get("dependency_authority")
    if not isinstance(dependency_raw, dict):
        raise ValueError("dependency_authority must be an object")
    _assert_keys_exact(
        dependency_raw,
        {"row084_complete", "row085_complete", "row086_complete"},
        "dependency_authority",
    )
    row084_complete = _expect_boolean(dependency_raw.get("row084_complete"), "dependency_authority.row084_complete")
    row085_complete = _expect_boolean(dependency_raw.get("row085_complete"), "dependency_authority.row085_complete")
    row086_complete = _expect_boolean(dependency_raw.get("row086_complete"), "dependency_authority.row086_complete")

    runtime_raw = payload.get("runtime_authority")
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_allowed = {
        "calibrated_trajectory_benchmark_pass",
        "runtime_receipt_present",
        "combined_flow_track_contact_audio_review_present",
    }
    _assert_keys_exact(runtime_raw, runtime_allowed, "runtime_authority")
    calibrated_benchmark_pass = _expect_boolean(
        runtime_raw.get("calibrated_trajectory_benchmark_pass"),
        "runtime_authority.calibrated_trajectory_benchmark_pass",
    )
    runtime_receipt_present = _expect_boolean(
        runtime_raw.get("runtime_receipt_present"), "runtime_authority.runtime_receipt_present"
    )
    combined_review_present = _expect_boolean(
        runtime_raw.get("combined_flow_track_contact_audio_review_present"),
        "runtime_authority.combined_flow_track_contact_audio_review_present",
    )

    samples_raw = payload.get("motion_samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise ValueError("motion_samples must be a non-empty list")
    previous_by_owner: dict[str, tuple[int, int]] = {}
    samples: list[dict[str, Any]] = []
    seen_sample_ids: set[str] = set()
    for idx, sample_raw in enumerate(samples_raw):
        sample = _validate_motion_sample(
            sample_raw,
            index=idx,
            frame_count=timeline_binding["frame_count"],
            previous_by_owner=previous_by_owner,
        )
        if sample["sample_id"] in seen_sample_ids:
            raise ValueError(f"duplicate sample_id detected: {sample['sample_id']}")
        seen_sample_ids.add(sample["sample_id"])
        samples.append(sample)

    cues_raw = payload.get("force_cues")
    if not isinstance(cues_raw, list):
        raise ValueError("force_cues must be an array")
    cues: list[dict[str, Any]] = []
    seen_cue_ids: set[str] = set()
    for idx, cue_raw in enumerate(cues_raw):
        cue = _validate_force_cue(cue_raw, index=idx, frame_count=timeline_binding["frame_count"])
        if cue["cue_id"] in seen_cue_ids:
            raise ValueError(f"duplicate cue_id detected: {cue['cue_id']}")
        seen_cue_ids.add(cue["cue_id"])
        cues.append(cue)

    if flow_binding["frame_pair_count"] < max(1, timeline_binding["frame_count"] - 1):
        raise ValueError("flow_binding.frame_pair_count must cover adjacent timeline frame pairs")

    declared_metrics = _validate_metrics(payload.get("metrics"))
    derived_metrics = _derive_metrics(samples, cues)
    for key, derived_value in derived_metrics.items():
        if declared_metrics[key] != derived_value:
            raise ValueError(
                f"metrics.{key}={declared_metrics[key]} does not match derived count {derived_value}"
            )
    metrics = derived_metrics
    thresholds = _validate_thresholds(payload.get("thresholds"))

    threshold_violations: list[str] = []
    camera_false_actor_motion = False
    for sample in samples:
        actor_mag = _magnitude(sample["actor_relative_velocity_xy"])
        if sample["camera_motion_dominant"] and actor_mag > thresholds["max_false_actor_motion_from_camera"]:
            camera_false_actor_motion = True
            raise ValueError(
                "camera motion cannot become false actor motion: "
                f"sample {sample['sample_id']} camera_motion_dominant with "
                f"actor_relative magnitude {actor_mag}"
            )
        if sample["confidence"] < thresholds["min_sample_confidence"]:
            threshold_violations.append(f"min_sample_confidence:{sample['sample_id']}")

    for cue in cues:
        if cue["uncertainty"] > thresholds["max_force_uncertainty"]:
            threshold_violations.append(f"max_force_uncertainty:{cue['cue_id']}")

    if camera_model["compensation_mode"] == "unsupported" and any(
        not sample["camera_motion_dominant"] and _magnitude(sample["local_velocity_xy"]) > 0
        for sample in samples
    ):
        # Unsupported camera models may still declare local image motion, but may not
        # claim compensated actor-relative authority without residual isolation.
        unsupported_actor_claims = [
            sample["sample_id"]
            for sample in samples
            if _magnitude(sample["actor_relative_velocity_xy"]) > thresholds["max_false_actor_motion_from_camera"]
            and _magnitude(sample["residual_after_camera_xy"])
            > thresholds["max_false_actor_motion_from_camera"]
        ]
        if unsupported_actor_claims:
            raise ValueError(
                "unsupported camera compensation cannot certify actor-relative motion for samples: "
                + ",".join(unsupported_actor_claims)
            )

    dependency_ready = row084_complete and row085_complete and row086_complete
    runtime_ready = calibrated_benchmark_pass and runtime_receipt_present and combined_review_present
    force_proxies_are_estimates = all(cue["force_is_estimate"] for cue in cues) if cues else True
    contact_force_certification_allowed = (
        dependency_ready
        and runtime_ready
        and force_proxies_are_estimates
        and not threshold_violations
        and not camera_false_actor_motion
        and camera_model["compensation_mode"] != "unsupported"
    )
    # Fail closed in this increment: no production tracker runtime authority yet.
    production_completion_allowed = False
    row_complete = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    elif not runtime_ready or threshold_violations:
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
    if not row086_complete:
        hold_reasons.append("dependency_row086_incomplete")
    if not calibrated_benchmark_pass:
        hold_reasons.append("calibrated_trajectory_benchmark_absent")
    if not runtime_receipt_present:
        hold_reasons.append("runtime_receipt_absent")
    if not combined_review_present:
        hold_reasons.append("combined_flow_track_contact_audio_review_absent")
    if camera_model["compensation_mode"] == "unsupported":
        hold_reasons.append("planned_camera_compensation_unsupported")
    if threshold_violations:
        hold_reasons.append("threshold_violations:" + ",".join(threshold_violations))

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_motion_force_cues.py",
            "compiler_revision": "row087_fail_closed_v1",
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "motion_force_cues_manifest",
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
        "flow_binding": flow_binding,
        "camera_model": camera_model,
        "coordinate_spaces": coordinate_spaces,
        "dependency_authority": {
            "row084_complete": row084_complete,
            "row085_complete": row085_complete,
            "row086_complete": row086_complete,
            "dependency_ready": dependency_ready,
        },
        "runtime_authority": {
            "calibrated_trajectory_benchmark_pass": calibrated_benchmark_pass,
            "runtime_receipt_present": runtime_receipt_present,
            "combined_flow_track_contact_audio_review_present": combined_review_present,
            "runtime_ready": runtime_ready,
        },
        "motion_samples": samples,
        "force_cues": cues,
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_violations": threshold_violations,
        "authority_summary": {
            "motion_sample_count": len(samples),
            "force_cue_count": len(cues),
            "force_proxies_are_estimates": force_proxies_are_estimates,
            "camera_false_actor_motion_blocked": True,
            "contact_force_certification_allowed": contact_force_certification_allowed,
            "hold_reasons": hold_reasons,
        },
        "authority_ceiling": authority_ceiling,
        "production_completion_allowed": production_completion_allowed,
        "row_complete": row_complete,
        "provenance": provenance,
    }
    manifest_sha256 = _canonical_sha256(receipt_body)
    receipt_body["manifest_sha256"] = manifest_sha256
    return receipt_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a fail-closed Row087 motion/force cues manifest.")
    parser.add_argument("--input", required=True, help="Path to motion/force input packet JSON")
    parser.add_argument("--output", required=True, help="Path to write compiled motion/force manifest JSON")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input packet must be a JSON object")
    try:
        receipt = compile_manifest(payload)
    except ValueError as exc:
        raise SystemExit(f"ROW087_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_sha256": receipt["manifest_sha256"],
                "row_complete": False,
                "contact_force_certification_allowed": receipt["authority_summary"][
                    "contact_force_certification_allowed"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
