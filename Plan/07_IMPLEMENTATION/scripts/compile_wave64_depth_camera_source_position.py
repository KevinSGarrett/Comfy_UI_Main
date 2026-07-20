#!/usr/bin/env python3
"""Fail-closed Row088 depth/camera/source-position compiler.

Compiles fixture camera, depth, listener, and source-position packets into a
content-addressed spatial manifest. Production completion remains blocked until
Rows084-085, calibrated trajectory benchmarks, runtime receipts, and combined
frame/contact/audio review authorities are satisfied.
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
    "camera_id",
    "is_synthetic",
    "video_sha256",
    "timeline_binding",
    "owner_track_binding",
    "camera_binding",
    "coordinate_space",
    "estimator_stack",
    "dependency_authority",
    "runtime_authority",
    "depth_authority",
    "listener_trajectory",
    "source_trajectories",
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

ALLOWED_CAMERA_BINDING_FIELDS = {
    "camera_id",
    "shot_id",
    "take_id",
    "intrinsics_present",
    "extrinsics_present",
    "calibration_authority",
    "pose_model",
}

ALLOWED_COORDINATE_SPACE_FIELDS = {
    "frame_id",
    "handedness",
    "units",
    "origin",
    "up_axis",
}

ALLOWED_ESTIMATOR_STACK_FIELDS = {
    "depth_estimator_id",
    "camera_pose_estimator_id",
    "source_position_estimator_id",
    "listener_estimator_id",
    "revision",
    "parameter_digest_sha256",
}

ALLOWED_DEPTH_AUTHORITY_FIELDS = {
    "depth_mode",
    "calibration_source",
    "scale_uncertainty",
}

ALLOWED_LISTENER_FIELDS = {"listener_id", "samples"}
ALLOWED_LISTENER_SAMPLE_FIELDS = {
    "frame_index",
    "pts",
    "position",
    "forward",
    "up",
    "confidence",
    "observation_state",
}
ALLOWED_SOURCE_FIELDS = {"source_id", "owner_id", "track_id", "samples"}
ALLOWED_SOURCE_SAMPLE_FIELDS = {
    "frame_index",
    "pts",
    "position",
    "depth_mode",
    "relative_depth",
    "metric_depth_m",
    "source_camera_distance",
    "source_listener_distance",
    "screen_azimuth_deg",
    "screen_elevation_deg",
    "occlusion_state",
    "visibility",
    "confidence",
    "uncertainty",
    "observation_state",
}

ALLOWED_CALIBRATION_AUTHORITY = {"none", "relative_only", "metric_calibrated"}
ALLOWED_POSE_MODELS = {"static", "moving", "cut_aware_unknown"}
ALLOWED_HANDEDNESS = {"right", "left"}
ALLOWED_UNITS = {"relative", "meters", "centimeters"}
ALLOWED_ORIGINS = {"camera", "world", "listener"}
ALLOWED_UP_AXIS = {"+y", "+z", "-y", "-z"}
ALLOWED_DEPTH_MODES = {"relative", "metric", "abstain"}
ALLOWED_OBSERVATION_STATES = {"observed", "interpolated", "abstain", "unknown"}
ALLOWED_OCCLUSION_STATES = {"clear", "partial", "occluded", "unknown"}
ALLOWED_VISIBILITY = {"visible", "partial", "occluded", "offscreen", "unknown"}
ALLOWED_THRESHOLD_FIELDS = {
    "min_position_confidence",
    "max_scale_uncertainty",
    "max_abstention_ratio",
    "max_occlusion_ratio",
}
SHA256_HEX_CHARS = set("0123456789abcdef")


CONTENT_ADDRESSED_EXCLUDED_FIELDS = frozenset({"created_at", "manifest_sha256"})
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = (
    REPO_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Wave64" / "fixtures" / "row088"
)

BENCHMARK_FIXTURE_PACKETS: tuple[dict[str, str], ...] = (
    {
        "name": "case_static_camera_listener_source.json",
        "role": "static",
        "case_id": "static",
    },
    {
        "name": "case_moving_camera_listener_source.json",
        "role": "moving",
        "case_id": "moving",
    },
)

SYNTHETIC_BENCHMARK_LEDGER_FILENAME = "synthetic_camera_listener_source_trajectory_ledger.json"
ALLOWED_SYNTHETIC_LEDGER_FIELDS = {
    "schema_version",
    "record_type",
    "ledger_id",
    "revision",
    "is_synthetic",
    "production_benchmark",
    "calibrated_trajectory_benchmark_pass",
    "row_complete",
    "production_completion_allowed",
    "visual_review_claimed",
    "rows084_085_acceptance_claimed",
    "authority_ceiling",
    "hold_reasons",
    "fixture_bindings",
    "trajectory_metric_expectations",
    "provenance",
    "ledger_sha256",
}
ALLOWED_TRAJECTORY_METRIC_EXPECTATION_FIELDS = {
    "case_id",
    "role",
    "source_fixture",
    "source_fixture_file_sha256",
    "source_compiled_manifest_sha256",
    "expected_listener_sample_count",
    "expected_source_sample_count",
    "expected_relative_only_sample_count",
    "expected_occlusion_sample_count",
    "expected_metric_claim_count",
}
LEDGER_EXPECTED_METRIC_KEYS = (
    "expected_listener_sample_count",
    "expected_source_sample_count",
    "expected_relative_only_sample_count",
    "expected_occlusion_sample_count",
    "expected_metric_claim_count",
)
COMPILED_METRIC_KEYS_FOR_LEDGER = (
    "listener_sample_count",
    "source_sample_count",
    "relative_only_sample_count",
    "occlusion_sample_count",
    "metric_claim_count",
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


def _expect_optional_number(value: Any, label: str) -> float | None:
    if value is None:
        return None
    return _expect_number(value, label)


def _expect_sha256(value: Any, label: str) -> str:
    text = _expect_non_empty_string(value, label)
    if len(text) != 64 or any(ch not in SHA256_HEX_CHARS for ch in text):
        raise ValueError(f"{label} must be a lowercase 64-char sha256")
    return text


def _expect_vec3(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a 3-number array")
    return [_expect_number(item, f"{label}[{idx}]") for idx, item in enumerate(value)]


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

    Wall-clock created_at and the self-referential manifest_sha256 are
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
    """Load a checked-in Row088 fixture packet by filename."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row088 fixture packet missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row088 fixture packet must be a JSON object: {path}")
    return payload


def fixture_file_sha256(name: str, *, fixture_dir: Path | None = None) -> str:
    """Return the lowercase sha256 of a checked-in fixture packet file bytes."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row088 fixture packet missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_synthetic_benchmark_ledger_integrity(payload: dict[str, Any]) -> str:
    """Recompute content-addressed ledger digest and reject tamper."""
    recorded = _expect_sha256(payload.get("ledger_sha256"), "ledger_sha256")
    body = {key: value for key, value in payload.items() if key != "ledger_sha256"}
    recomputed = _canonical_sha256(body)
    if recorded != recomputed:
        raise ValueError(
            "ledger_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    return recomputed


def load_synthetic_benchmark_ledger(*, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load the checked-in non-production camera-listener-source trajectory ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Row088 synthetic benchmark ledger missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row088 synthetic benchmark ledger must be a JSON object: {path}")
    return payload


def _assert_metric_expectations_match_compiled(
    expectation: dict[str, Any],
    compiled: dict[str, Any],
    *,
    label: str,
) -> None:
    metrics = compiled.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"{label}: compiled manifest missing metrics")
    for expected_key, metric_key in zip(
        LEDGER_EXPECTED_METRIC_KEYS, COMPILED_METRIC_KEYS_FOR_LEDGER, strict=True
    ):
        if expected_key not in expectation:
            raise ValueError(f"{label}: missing {expected_key}")
        if expectation[expected_key] != metrics.get(metric_key):
            raise ValueError(
                f"{label}: {expected_key} mismatch "
                f"ledger={expectation[expected_key]!r} compiled={metrics.get(metric_key)!r}"
            )


def verify_synthetic_ledger_vs_compiled_manifest_expectations(
    ledger: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed ledger-vs-compiled-manifest expectation verifier.

    Recompiles every ledger-bound fixture packet and rejects digest/metric drift.
    Explicitly refuses calibrated trajectory benchmark pass, visual-review,
    Rows084/085 acceptance, and row completion claims.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    payload = ledger if ledger is not None else load_synthetic_benchmark_ledger(fixture_dir=directory)
    if not isinstance(payload, dict):
        raise ValueError("synthetic ledger must be an object")
    _assert_keys_exact(payload, ALLOWED_SYNTHETIC_LEDGER_FIELDS, "synthetic_ledger")
    ledger_digest = verify_synthetic_benchmark_ledger_integrity(payload)

    if payload.get("record_type") != "row088_synthetic_camera_listener_source_trajectory_ledger":
        raise ValueError("synthetic ledger record_type mismatch")
    if payload.get("is_synthetic") is not True:
        raise ValueError("synthetic ledger must set is_synthetic=true")
    if payload.get("authority_ceiling") != "fixture_synthetic_only":
        raise ValueError("synthetic ledger authority_ceiling must remain fixture_synthetic_only")

    false_flags = (
        "production_benchmark",
        "calibrated_trajectory_benchmark_pass",
        "row_complete",
        "production_completion_allowed",
        "visual_review_claimed",
        "rows084_085_acceptance_claimed",
    )
    for flag in false_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"synthetic ledger must keep {flag}=false")

    bindings = payload.get("fixture_bindings")
    if not isinstance(bindings, list) or len(bindings) != len(BENCHMARK_FIXTURE_PACKETS):
        raise ValueError(
            "synthetic ledger fixture_bindings must cover exactly two trajectory cases"
        )
    expectations = payload.get("trajectory_metric_expectations")
    if not isinstance(expectations, list) or len(expectations) != len(BENCHMARK_FIXTURE_PACKETS):
        raise ValueError(
            "synthetic ledger trajectory_metric_expectations must cover exactly two cases"
        )

    compiled_by_fixture: dict[str, dict[str, Any]] = {}
    live_file_digest_by_fixture: dict[str, str] = {}
    live_compiled_digest_by_fixture: dict[str, str] = {}

    for idx, binding in enumerate(bindings):
        label = f"fixture_bindings[{idx}]"
        if not isinstance(binding, dict):
            raise ValueError(f"{label} must be an object")
        fixture_name = _expect_non_empty_string(binding.get("fixture_name"), f"{label}.fixture_name")
        recorded_file = _expect_sha256(
            binding.get("fixture_file_sha256"), f"{label}.fixture_file_sha256"
        )
        recorded_compiled = _expect_sha256(
            binding.get("compiled_manifest_sha256"), f"{label}.compiled_manifest_sha256"
        )
        if binding.get("row_complete") is not False:
            raise ValueError(f"{label}.row_complete must remain false")
        if binding.get("is_synthetic") is not True:
            raise ValueError(f"{label}.is_synthetic must be true")

        live_file = fixture_file_sha256(fixture_name, fixture_dir=directory)
        if recorded_file != live_file:
            raise ValueError(
                f"{label}: fixture file digest drift for {fixture_name}: "
                f"ledger={recorded_file} live={live_file}"
            )

        compiled = compile_manifest(load_fixture_packet(fixture_name, fixture_dir=directory))
        live_compiled = verify_manifest_integrity(compiled)
        if recorded_compiled != live_compiled:
            raise ValueError(
                f"{label}: compiled manifest digest drift for {fixture_name}: "
                f"ledger={recorded_compiled} live={live_compiled}"
            )
        if compiled["row_complete"] or compiled["production_completion_allowed"]:
            raise ValueError(f"{label}: compiled fixture must remain non-complete")
        if compiled["runtime_authority"].get("calibrated_trajectory_benchmark_pass"):
            raise ValueError(
                f"{label}: compiled fixture must not claim calibrated_trajectory_benchmark_pass"
            )
        for dep in ("row084_complete", "row085_complete"):
            if compiled["dependency_authority"].get(dep):
                raise ValueError(f"{label}: compiled fixture must not claim {dep}")

        compiled_by_fixture[fixture_name] = compiled
        live_file_digest_by_fixture[fixture_name] = live_file
        live_compiled_digest_by_fixture[fixture_name] = live_compiled

    expected_fixture_names = {meta["name"] for meta in BENCHMARK_FIXTURE_PACKETS}
    if set(compiled_by_fixture) != expected_fixture_names:
        raise ValueError(
            "synthetic ledger fixture_bindings set drift: "
            f"ledger={sorted(compiled_by_fixture)} expected={sorted(expected_fixture_names)}"
        )

    seen_cases: set[str] = set()
    for idx, expectation in enumerate(expectations):
        label = f"trajectory_metric_expectations[{idx}]"
        if not isinstance(expectation, dict):
            raise ValueError(f"{label} must be an object")
        _assert_keys_exact(expectation, ALLOWED_TRAJECTORY_METRIC_EXPECTATION_FIELDS, label)
        case_id = _expect_non_empty_string(expectation.get("case_id"), f"{label}.case_id")
        if case_id in seen_cases:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        seen_cases.add(case_id)

        source_fixture = _expect_non_empty_string(
            expectation.get("source_fixture"), f"{label}.source_fixture"
        )
        if source_fixture not in compiled_by_fixture:
            raise ValueError(f"{label}: source_fixture {source_fixture!r} not bound")
        recorded_file = _expect_sha256(
            expectation.get("source_fixture_file_sha256"),
            f"{label}.source_fixture_file_sha256",
        )
        recorded_compiled = _expect_sha256(
            expectation.get("source_compiled_manifest_sha256"),
            f"{label}.source_compiled_manifest_sha256",
        )
        if recorded_file != live_file_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source fixture file digest drift for {source_fixture}: "
                f"ledger={recorded_file} live={live_file_digest_by_fixture[source_fixture]}"
            )
        if recorded_compiled != live_compiled_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source compiled manifest digest drift for {source_fixture}: "
                f"ledger={recorded_compiled} live={live_compiled_digest_by_fixture[source_fixture]}"
            )
        for expected_key in LEDGER_EXPECTED_METRIC_KEYS:
            _expect_non_negative_int(expectation.get(expected_key), f"{label}.{expected_key}")
        _assert_metric_expectations_match_compiled(
            expectation, compiled_by_fixture[source_fixture], label=label
        )

    expected_cases = {meta["case_id"] for meta in BENCHMARK_FIXTURE_PACKETS}
    if seen_cases != expected_cases:
        raise ValueError(
            "synthetic ledger trajectory case set drift: "
            f"ledger={sorted(seen_cases)} expected={sorted(expected_cases)}"
        )

    return {
        "status": "ok",
        "verifier": "verify_synthetic_ledger_vs_compiled_manifest_expectations",
        "ledger_sha256": ledger_digest,
        "fixture_binding_count": len(bindings),
        "trajectory_metric_expectation_count": len(expectations),
        "digest_drift_rejected": True,
        "production_benchmark": False,
        "calibrated_trajectory_benchmark_pass": False,
        "visual_review_claimed": False,
        "rows084_085_acceptance_claimed": False,
        "row_complete": False,
        "authority_ceiling": "fixture_synthetic_only",
    }


def build_synthetic_camera_listener_source_trajectory_ledger(
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Bind fixture digests into a non-production camera-listener-source ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    fixture_bindings: list[dict[str, Any]] = []
    trajectory_metric_expectations: list[dict[str, Any]] = []

    for packet_meta in BENCHMARK_FIXTURE_PACKETS:
        name = packet_meta["name"]
        role = packet_meta["role"]
        case_id = packet_meta["case_id"]
        file_digest = fixture_file_sha256(name, fixture_dir=directory)
        packet = load_fixture_packet(name, fixture_dir=directory)
        compiled = compile_manifest(packet)
        compiled_digest = verify_manifest_integrity(compiled)
        if compiled["row_complete"] or compiled["production_completion_allowed"]:
            raise ValueError(
                f"fixture {name} must remain non-complete for synthetic ledger binding"
            )
        if compiled["runtime_authority"].get("calibrated_trajectory_benchmark_pass"):
            raise ValueError(
                f"fixture {name} must not claim calibrated_trajectory_benchmark_pass"
            )
        for dep in ("row084_complete", "row085_complete"):
            if compiled["dependency_authority"].get(dep):
                raise ValueError(f"fixture {name} must not claim {dep}")

        metrics = compiled["metrics"]
        fixture_bindings.append(
            {
                "fixture_name": name,
                "role": role,
                "case_id": case_id,
                "fixture_file_sha256": file_digest,
                "compiled_manifest_sha256": compiled_digest,
                "is_synthetic": True,
                "row_complete": False,
            }
        )
        trajectory_metric_expectations.append(
            {
                "case_id": case_id,
                "role": role,
                "source_fixture": name,
                "source_fixture_file_sha256": file_digest,
                "source_compiled_manifest_sha256": compiled_digest,
                "expected_listener_sample_count": metrics["listener_sample_count"],
                "expected_source_sample_count": metrics["source_sample_count"],
                "expected_relative_only_sample_count": metrics["relative_only_sample_count"],
                "expected_occlusion_sample_count": metrics["occlusion_sample_count"],
                "expected_metric_claim_count": metrics["metric_claim_count"],
            }
        )

    if len(fixture_bindings) != 2 or len(trajectory_metric_expectations) != 2:
        raise ValueError("synthetic ledger requires exactly two trajectory fixture cases")

    fixture_bindings.sort(key=lambda item: item["fixture_name"])
    trajectory_metric_expectations.sort(key=lambda item: item["case_id"])

    ledger_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row088_synthetic_camera_listener_source_trajectory_ledger",
        "ledger_id": "row088_synthetic_camera_listener_source_trajectory_ledger_v1",
        "revision": "row088_synthetic_ledger_v1",
        "is_synthetic": True,
        "production_benchmark": False,
        "calibrated_trajectory_benchmark_pass": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "visual_review_claimed": False,
        "rows084_085_acceptance_claimed": False,
        "authority_ceiling": "fixture_synthetic_only",
        "hold_reasons": [
            "synthetic_fixture_ledger_only",
            "dependency_row084_incomplete",
            "dependency_row085_incomplete",
            "calibrated_trajectory_benchmark_absent",
            "runtime_receipt_absent",
            "combined_frame_contact_audio_review_absent",
            "relative_depth_only_no_metric_authority",
        ],
        "fixture_bindings": fixture_bindings,
        "trajectory_metric_expectations": trajectory_metric_expectations,
        "provenance": {
            "compiler": "compile_wave64_depth_camera_source_position.py",
            "compiler_revision": "row088_synthetic_camera_listener_source_trajectory_ledger_v1",
            "non_production": True,
            "binds_fixture_file_and_compiled_manifest_digests": True,
            "records_expected_static_moving_camera_listener_source_metrics": True,
        },
    }
    _assert_keys_exact(
        ledger_body, ALLOWED_SYNTHETIC_LEDGER_FIELDS - {"ledger_sha256"}, "synthetic_ledger"
    )
    ledger_body["ledger_sha256"] = _canonical_sha256(ledger_body)
    verify_synthetic_benchmark_ledger_integrity(ledger_body)
    return ledger_body


def write_synthetic_camera_listener_source_trajectory_ledger(
    output_path: Path | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Build and atomically write the synthetic camera-listener-source ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = output_path if output_path is not None else directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    ledger = build_synthetic_camera_listener_source_trajectory_ledger(fixture_dir=directory)
    _write_json_atomic(path, ledger)
    return ledger


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


def _validate_camera_binding(
    raw: Any, *, shot_id: str, take_id: str, camera_id: str
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("camera_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_CAMERA_BINDING_FIELDS, "camera_binding")
    bound_camera = _expect_non_empty_string(raw.get("camera_id"), "camera_binding.camera_id")
    bound_shot = _expect_non_empty_string(raw.get("shot_id"), "camera_binding.shot_id")
    bound_take = _expect_non_empty_string(raw.get("take_id"), "camera_binding.take_id")
    if bound_camera != camera_id:
        raise ValueError("camera_binding.camera_id must match top-level camera_id")
    if bound_shot != shot_id:
        raise ValueError("camera_binding.shot_id must match top-level shot_id")
    if bound_take != take_id:
        raise ValueError("camera_binding.take_id must match top-level take_id")
    calibration_authority = _expect_non_empty_string(
        raw.get("calibration_authority"), "camera_binding.calibration_authority"
    )
    if calibration_authority not in ALLOWED_CALIBRATION_AUTHORITY:
        raise ValueError(
            f"camera_binding.calibration_authority must be one of {sorted(ALLOWED_CALIBRATION_AUTHORITY)}"
        )
    pose_model = _expect_non_empty_string(raw.get("pose_model"), "camera_binding.pose_model")
    if pose_model not in ALLOWED_POSE_MODELS:
        raise ValueError(f"camera_binding.pose_model must be one of {sorted(ALLOWED_POSE_MODELS)}")
    return {
        "camera_id": bound_camera,
        "shot_id": bound_shot,
        "take_id": bound_take,
        "intrinsics_present": _expect_boolean(
            raw.get("intrinsics_present"), "camera_binding.intrinsics_present"
        ),
        "extrinsics_present": _expect_boolean(
            raw.get("extrinsics_present"), "camera_binding.extrinsics_present"
        ),
        "calibration_authority": calibration_authority,
        "pose_model": pose_model,
    }


def _validate_coordinate_space(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("coordinate_space must be an object")
    _assert_keys_exact(raw, ALLOWED_COORDINATE_SPACE_FIELDS, "coordinate_space")
    handedness = _expect_non_empty_string(raw.get("handedness"), "coordinate_space.handedness")
    if handedness not in ALLOWED_HANDEDNESS:
        raise ValueError(f"coordinate_space.handedness must be one of {sorted(ALLOWED_HANDEDNESS)}")
    units = _expect_non_empty_string(raw.get("units"), "coordinate_space.units")
    if units not in ALLOWED_UNITS:
        raise ValueError(f"coordinate_space.units must be one of {sorted(ALLOWED_UNITS)}")
    origin = _expect_non_empty_string(raw.get("origin"), "coordinate_space.origin")
    if origin not in ALLOWED_ORIGINS:
        raise ValueError(f"coordinate_space.origin must be one of {sorted(ALLOWED_ORIGINS)}")
    up_axis = _expect_non_empty_string(raw.get("up_axis"), "coordinate_space.up_axis")
    if up_axis not in ALLOWED_UP_AXIS:
        raise ValueError(f"coordinate_space.up_axis must be one of {sorted(ALLOWED_UP_AXIS)}")
    return {
        "frame_id": _expect_non_empty_string(raw.get("frame_id"), "coordinate_space.frame_id"),
        "handedness": handedness,
        "units": units,
        "origin": origin,
        "up_axis": up_axis,
    }


def _validate_estimator_stack(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("estimator_stack must be an object")
    _assert_keys_exact(raw, ALLOWED_ESTIMATOR_STACK_FIELDS, "estimator_stack")
    return {
        "depth_estimator_id": _expect_non_empty_string(
            raw.get("depth_estimator_id"), "estimator_stack.depth_estimator_id"
        ),
        "camera_pose_estimator_id": _expect_non_empty_string(
            raw.get("camera_pose_estimator_id"), "estimator_stack.camera_pose_estimator_id"
        ),
        "source_position_estimator_id": _expect_non_empty_string(
            raw.get("source_position_estimator_id"), "estimator_stack.source_position_estimator_id"
        ),
        "listener_estimator_id": _expect_non_empty_string(
            raw.get("listener_estimator_id"), "estimator_stack.listener_estimator_id"
        ),
        "revision": _expect_non_empty_string(raw.get("revision"), "estimator_stack.revision"),
        "parameter_digest_sha256": _expect_sha256(
            raw.get("parameter_digest_sha256"), "estimator_stack.parameter_digest_sha256"
        ),
    }


def _validate_depth_authority(
    raw: Any, *, camera_binding: dict[str, Any], coordinate_space: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("depth_authority must be an object")
    _assert_keys_exact(raw, ALLOWED_DEPTH_AUTHORITY_FIELDS, "depth_authority")
    depth_mode = _expect_non_empty_string(raw.get("depth_mode"), "depth_authority.depth_mode")
    if depth_mode not in ALLOWED_DEPTH_MODES:
        raise ValueError(f"depth_authority.depth_mode must be one of {sorted(ALLOWED_DEPTH_MODES)}")
    calibration_source = _expect_optional_string_or_none(
        raw.get("calibration_source"), "depth_authority.calibration_source"
    )
    scale_uncertainty = _expect_number(raw.get("scale_uncertainty"), "depth_authority.scale_uncertainty")
    if scale_uncertainty < 0:
        raise ValueError("depth_authority.scale_uncertainty must be >= 0")

    metric_claims_allowed = (
        depth_mode == "metric"
        and camera_binding["calibration_authority"] == "metric_calibrated"
        and camera_binding["intrinsics_present"]
        and camera_binding["extrinsics_present"]
        and coordinate_space["units"] in {"meters", "centimeters"}
        and calibration_source is not None
    )
    if depth_mode == "metric" and not metric_claims_allowed:
        raise ValueError(
            "metric depth claims require metric_calibrated camera authority, intrinsics, "
            "extrinsics, metric units, and calibration_source"
        )
    if depth_mode == "relative" and coordinate_space["units"] != "relative":
        raise ValueError("relative depth_mode requires coordinate_space.units=relative")
    if depth_mode == "relative" and camera_binding["calibration_authority"] == "metric_calibrated":
        raise ValueError("relative depth_mode cannot claim metric_calibrated camera authority")

    return {
        "depth_mode": depth_mode,
        "metric_claims_allowed": metric_claims_allowed,
        "relative_depth_labeled": depth_mode == "relative",
        "calibration_source": calibration_source,
        "scale_uncertainty": scale_uncertainty,
    }


def _validate_monotonic_sample(
    *,
    frame_index: int,
    pts: int,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
    label: str,
) -> None:
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    if previous_frame is not None:
        if frame_index <= previous_frame:
            raise ValueError(f"{label}.frame_index must be unique and strictly increasing")
        if pts <= previous_pts:
            raise ValueError(f"{label}.pts must be unique and strictly increasing")


def _validate_listener_sample(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"listener_trajectory.samples[{index}] must be an object")
    label = f"listener_trajectory.samples[{index}]"
    _assert_keys_exact(raw, ALLOWED_LISTENER_SAMPLE_FIELDS, label)
    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    _validate_monotonic_sample(
        frame_index=frame_index,
        pts=pts,
        frame_count=frame_count,
        previous_frame=previous_frame,
        previous_pts=previous_pts,
        label=label,
    )
    observation_state = _expect_non_empty_string(raw.get("observation_state"), f"{label}.observation_state")
    if observation_state not in ALLOWED_OBSERVATION_STATES:
        raise ValueError(f"{label}.observation_state must be one of {sorted(ALLOWED_OBSERVATION_STATES)}")
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")
    if observation_state == "abstain" and confidence > 0:
        raise ValueError(f"{label} abstain observation_state requires confidence=0")
    return {
        "frame_index": frame_index,
        "pts": pts,
        "position": _expect_vec3(raw.get("position"), f"{label}.position"),
        "forward": _expect_vec3(raw.get("forward"), f"{label}.forward"),
        "up": _expect_vec3(raw.get("up"), f"{label}.up"),
        "confidence": confidence,
        "observation_state": observation_state,
    }


def _compile_listener_trajectory(raw: Any, *, frame_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("listener_trajectory must be an object")
    _assert_keys_exact(raw, ALLOWED_LISTENER_FIELDS, "listener_trajectory")
    samples_raw = raw.get("samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise ValueError("listener_trajectory.samples must be a non-empty list")
    samples: list[dict[str, Any]] = []
    previous_frame: int | None = None
    previous_pts: int | None = None
    for idx, sample_raw in enumerate(samples_raw):
        sample = _validate_listener_sample(
            sample_raw,
            index=idx,
            frame_count=frame_count,
            previous_frame=previous_frame,
            previous_pts=previous_pts,
        )
        previous_frame = sample["frame_index"]
        previous_pts = sample["pts"]
        samples.append(sample)
    return {
        "listener_id": _expect_non_empty_string(raw.get("listener_id"), "listener_trajectory.listener_id"),
        "sample_count": len(samples),
        "first_frame": samples[0]["frame_index"],
        "last_frame": samples[-1]["frame_index"],
        "samples": samples,
    }


def _validate_source_sample(
    raw: Any,
    *,
    index: int,
    source_label: str,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
    depth_authority: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{source_label}.samples[{index}] must be an object")
    label = f"{source_label}.samples[{index}]"
    _assert_keys_exact(raw, ALLOWED_SOURCE_SAMPLE_FIELDS, label)
    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    _validate_monotonic_sample(
        frame_index=frame_index,
        pts=pts,
        frame_count=frame_count,
        previous_frame=previous_frame,
        previous_pts=previous_pts,
        label=label,
    )
    depth_mode = _expect_non_empty_string(raw.get("depth_mode"), f"{label}.depth_mode")
    if depth_mode not in ALLOWED_DEPTH_MODES:
        raise ValueError(f"{label}.depth_mode must be one of {sorted(ALLOWED_DEPTH_MODES)}")
    if depth_mode == "metric" and not depth_authority["metric_claims_allowed"]:
        raise ValueError(f"{label}.depth_mode=metric blocked without metric depth authority")
    if depth_mode == "relative" and depth_authority["depth_mode"] == "metric":
        raise ValueError(f"{label}.depth_mode=relative conflicts with metric depth_authority")

    relative_depth = _expect_optional_number(raw.get("relative_depth"), f"{label}.relative_depth")
    metric_depth_m = _expect_optional_number(raw.get("metric_depth_m"), f"{label}.metric_depth_m")
    if depth_mode == "relative":
        if relative_depth is None:
            raise ValueError(f"{label}.relative_depth required for relative depth_mode")
        if metric_depth_m is not None:
            raise ValueError(f"{label}.metric_depth_m must be null for relative depth_mode")
    if depth_mode == "metric":
        if metric_depth_m is None or metric_depth_m < 0:
            raise ValueError(f"{label}.metric_depth_m must be >= 0 for metric depth_mode")
    if depth_mode == "abstain":
        if relative_depth is not None or metric_depth_m is not None:
            raise ValueError(f"{label} abstain depth_mode requires null depth values")

    occlusion_state = _expect_non_empty_string(raw.get("occlusion_state"), f"{label}.occlusion_state")
    if occlusion_state not in ALLOWED_OCCLUSION_STATES:
        raise ValueError(f"{label}.occlusion_state must be one of {sorted(ALLOWED_OCCLUSION_STATES)}")
    visibility = _expect_non_empty_string(raw.get("visibility"), f"{label}.visibility")
    if visibility not in ALLOWED_VISIBILITY:
        raise ValueError(f"{label}.visibility must be one of {sorted(ALLOWED_VISIBILITY)}")
    observation_state = _expect_non_empty_string(raw.get("observation_state"), f"{label}.observation_state")
    if observation_state not in ALLOWED_OBSERVATION_STATES:
        raise ValueError(f"{label}.observation_state must be one of {sorted(ALLOWED_OBSERVATION_STATES)}")
    if depth_mode == "abstain" and observation_state != "abstain":
        raise ValueError(f"{label} abstain depth_mode requires observation_state=abstain")

    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")
    uncertainty = _expect_number(raw.get("uncertainty"), f"{label}.uncertainty")
    if uncertainty < 0:
        raise ValueError(f"{label}.uncertainty must be >= 0")
    if observation_state == "abstain" and confidence > 0:
        raise ValueError(f"{label} abstain observation_state requires confidence=0")

    azimuth = _expect_optional_number(raw.get("screen_azimuth_deg"), f"{label}.screen_azimuth_deg")
    elevation = _expect_optional_number(raw.get("screen_elevation_deg"), f"{label}.screen_elevation_deg")
    if azimuth is not None and (azimuth < -180 or azimuth > 180):
        raise ValueError(f"{label}.screen_azimuth_deg must be within [-180, 180]")
    if elevation is not None and (elevation < -90 or elevation > 90):
        raise ValueError(f"{label}.screen_elevation_deg must be within [-90, 90]")
    if observation_state != "abstain" and (azimuth is None or elevation is None):
        raise ValueError(f"{label} non-abstain samples require screen azimuth and elevation")

    source_camera_distance = _expect_optional_number(
        raw.get("source_camera_distance"), f"{label}.source_camera_distance"
    )
    source_listener_distance = _expect_optional_number(
        raw.get("source_listener_distance"), f"{label}.source_listener_distance"
    )
    if source_camera_distance is not None and source_camera_distance < 0:
        raise ValueError(f"{label}.source_camera_distance must be >= 0")
    if source_listener_distance is not None and source_listener_distance < 0:
        raise ValueError(f"{label}.source_listener_distance must be >= 0")

    return {
        "frame_index": frame_index,
        "pts": pts,
        "position": _expect_vec3(raw.get("position"), f"{label}.position"),
        "depth_mode": depth_mode,
        "relative_depth": relative_depth,
        "metric_depth_m": metric_depth_m,
        "source_camera_distance": source_camera_distance,
        "source_listener_distance": source_listener_distance,
        "screen_azimuth_deg": azimuth,
        "screen_elevation_deg": elevation,
        "occlusion_state": occlusion_state,
        "visibility": visibility,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "observation_state": observation_state,
    }


def _compile_source_trajectory(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    depth_authority: dict[str, Any],
    owner_track_binding: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"source_trajectories[{index}] must be an object")
    label = f"source_trajectories[{index}]"
    _assert_keys_exact(raw, ALLOWED_SOURCE_FIELDS, label)
    owner_id = _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id")
    track_id = _expect_non_empty_string(raw.get("track_id"), f"{label}.track_id")
    if owner_id != owner_track_binding["owner_id"]:
        raise ValueError(f"{label}.owner_id must match owner_track_binding.owner_id")
    if track_id != owner_track_binding["track_id"]:
        raise ValueError(f"{label}.track_id must match owner_track_binding.track_id")

    samples_raw = raw.get("samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise ValueError(f"{label}.samples must be a non-empty list")
    samples: list[dict[str, Any]] = []
    previous_frame: int | None = None
    previous_pts: int | None = None
    for sample_idx, sample_raw in enumerate(samples_raw):
        sample = _validate_source_sample(
            sample_raw,
            index=sample_idx,
            source_label=label,
            frame_count=frame_count,
            previous_frame=previous_frame,
            previous_pts=previous_pts,
            depth_authority=depth_authority,
        )
        previous_frame = sample["frame_index"]
        previous_pts = sample["pts"]
        samples.append(sample)
    return {
        "source_id": _expect_non_empty_string(raw.get("source_id"), f"{label}.source_id"),
        "owner_id": owner_id,
        "track_id": track_id,
        "sample_count": len(samples),
        "first_frame": samples[0]["frame_index"],
        "last_frame": samples[-1]["frame_index"],
        "samples": samples,
    }


def _validate_thresholds(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    _assert_keys_exact(raw, ALLOWED_THRESHOLD_FIELDS, "thresholds")
    result: dict[str, float] = {}
    for key in sorted(ALLOWED_THRESHOLD_FIELDS):
        value = _expect_number(raw.get(key), f"thresholds.{key}")
        if key != "max_scale_uncertainty" and (value < 0 or value > 1):
            raise ValueError(f"thresholds.{key} must be within [0, 1]")
        if key == "max_scale_uncertainty" and value < 0:
            raise ValueError("thresholds.max_scale_uncertainty must be >= 0")
        result[key] = value
    return result


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    shot_id = _expect_non_empty_string(payload.get("shot_id"), "shot_id")
    take_id = _expect_non_empty_string(payload.get("take_id"), "take_id")
    camera_id = _expect_non_empty_string(payload.get("camera_id"), "camera_id")

    timeline_binding = _validate_timeline_binding(payload.get("timeline_binding"))
    owner_track_binding = _validate_owner_track_binding(payload.get("owner_track_binding"))
    camera_binding = _validate_camera_binding(
        payload.get("camera_binding"), shot_id=shot_id, take_id=take_id, camera_id=camera_id
    )
    coordinate_space = _validate_coordinate_space(payload.get("coordinate_space"))
    estimator_stack = _validate_estimator_stack(payload.get("estimator_stack"))
    depth_authority = _validate_depth_authority(
        payload.get("depth_authority"),
        camera_binding=camera_binding,
        coordinate_space=coordinate_space,
    )

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
        "calibrated_trajectory_benchmark_pass",
        "runtime_receipt_present",
        "combined_frame_contact_audio_review_present",
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
        runtime_raw.get("combined_frame_contact_audio_review_present"),
        "runtime_authority.combined_frame_contact_audio_review_present",
    )

    listener_trajectory = _compile_listener_trajectory(
        payload.get("listener_trajectory"), frame_count=timeline_binding["frame_count"]
    )
    sources_raw = payload.get("source_trajectories")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ValueError("source_trajectories must be a non-empty list")
    source_trajectories: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for idx, source_raw in enumerate(sources_raw):
        compiled = _compile_source_trajectory(
            source_raw,
            index=idx,
            frame_count=timeline_binding["frame_count"],
            depth_authority=depth_authority,
            owner_track_binding=owner_track_binding,
        )
        if compiled["source_id"] in seen_source_ids:
            raise ValueError(f"duplicate source_id detected: {compiled['source_id']}")
        seen_source_ids.add(compiled["source_id"])
        source_trajectories.append(compiled)

    thresholds = _validate_thresholds(payload.get("thresholds"))

    all_source_samples = [sample for traj in source_trajectories for sample in traj["samples"]]
    source_sample_count = len(all_source_samples)
    metric_claim_count = sum(1 for sample in all_source_samples if sample["depth_mode"] == "metric")
    relative_only_sample_count = sum(1 for sample in all_source_samples if sample["depth_mode"] == "relative")
    abstention_count = sum(1 for sample in all_source_samples if sample["observation_state"] == "abstain")
    occlusion_sample_count = sum(
        1 for sample in all_source_samples if sample["occlusion_state"] in {"partial", "occluded"}
    )
    low_confidence_sample_count = sum(
        1
        for sample in all_source_samples
        if sample["observation_state"] != "abstain"
        and sample["confidence"] < thresholds["min_position_confidence"]
    )
    metrics = {
        "source_count": len(source_trajectories),
        "listener_sample_count": listener_trajectory["sample_count"],
        "source_sample_count": source_sample_count,
        "metric_claim_count": metric_claim_count,
        "relative_only_sample_count": relative_only_sample_count,
        "abstention_count": abstention_count,
        "occlusion_sample_count": occlusion_sample_count,
        "low_confidence_sample_count": low_confidence_sample_count,
    }

    threshold_violations: list[str] = []
    if depth_authority["scale_uncertainty"] > thresholds["max_scale_uncertainty"]:
        threshold_violations.append("scale_uncertainty>max_scale_uncertainty")
    if source_sample_count > 0:
        abstention_ratio = abstention_count / source_sample_count
        occlusion_ratio = occlusion_sample_count / source_sample_count
        if abstention_ratio > thresholds["max_abstention_ratio"]:
            threshold_violations.append("abstention_ratio>max_abstention_ratio")
        if occlusion_ratio > thresholds["max_occlusion_ratio"]:
            threshold_violations.append("occlusion_ratio>max_occlusion_ratio")
    if low_confidence_sample_count > 0:
        threshold_violations.append("min_position_confidence")

    unsupported_spatial_claims = bool(threshold_violations) or metric_claim_count > 0 and not depth_authority[
        "metric_claims_allowed"
    ]
    dependency_ready = row084_complete and row085_complete
    runtime_ready = calibrated_benchmark_pass and runtime_receipt_present and combined_review_present
    spatial_certification_allowed = (
        dependency_ready and runtime_ready and not unsupported_spatial_claims and not threshold_violations
    )
    # Fail closed in this increment: no production tracker runtime authority yet.
    production_completion_allowed = False
    row_complete = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    elif unsupported_spatial_claims or not runtime_ready:
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
    if not calibrated_benchmark_pass:
        hold_reasons.append("calibrated_trajectory_benchmark_absent")
    if not runtime_receipt_present:
        hold_reasons.append("runtime_receipt_absent")
    if not combined_review_present:
        hold_reasons.append("combined_frame_contact_audio_review_absent")
    if unsupported_spatial_claims:
        hold_reasons.append("unsupported_spatial_claims_block_certification")
    if threshold_violations:
        hold_reasons.append("threshold_violations:" + ",".join(threshold_violations))
    if depth_authority["relative_depth_labeled"]:
        hold_reasons.append("relative_depth_only_no_metric_authority")

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_depth_camera_source_position.py",
            "compiler_revision": "row088_fail_closed_v1",
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "depth_camera_source_position_manifest",
        "manifest_id": _expect_non_empty_string(payload.get("manifest_id"), "manifest_id"),
        "revision": _expect_non_empty_string(payload.get("revision"), "revision"),
        "run_id": _expect_non_empty_string(payload.get("run_id"), "run_id"),
        "scene_id": _expect_non_empty_string(payload.get("scene_id"), "scene_id"),
        "shot_id": shot_id,
        "take_id": take_id,
        "camera_id": camera_id,
        "is_synthetic": _expect_boolean(payload.get("is_synthetic"), "is_synthetic"),
        "video_sha256": _expect_sha256(payload.get("video_sha256"), "video_sha256"),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "timeline_binding": timeline_binding,
        "owner_track_binding": owner_track_binding,
        "camera_binding": camera_binding,
        "coordinate_space": coordinate_space,
        "estimator_stack": estimator_stack,
        "dependency_authority": {
            "row084_complete": row084_complete,
            "row085_complete": row085_complete,
            "dependency_ready": dependency_ready,
        },
        "runtime_authority": {
            "calibrated_trajectory_benchmark_pass": calibrated_benchmark_pass,
            "runtime_receipt_present": runtime_receipt_present,
            "combined_frame_contact_audio_review_present": combined_review_present,
            "runtime_ready": runtime_ready,
        },
        "depth_authority": depth_authority,
        "listener_trajectory": listener_trajectory,
        "source_trajectories": source_trajectories,
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_violations": threshold_violations,
        "authority_summary": {
            "spatial_certification_allowed": spatial_certification_allowed,
            "metric_depth_authority_present": depth_authority["metric_claims_allowed"],
            "unsupported_spatial_claims": unsupported_spatial_claims,
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
        description="Compile a fail-closed Row088 depth/camera/source-position manifest."
    )
    parser.add_argument("--input", help="Path to depth/camera/source input packet JSON")
    parser.add_argument("--output", help="Path to write compiled spatial manifest JSON")
    parser.add_argument(
        "--emit-synthetic-benchmark-ledger",
        metavar="PATH",
        help=(
            "Build the non-production synthetic camera-listener-source trajectory ledger "
            "bound to checked-in fixture digests and write it to PATH"
        ),
    )
    parser.add_argument(
        "--verify-synthetic-benchmark-ledger",
        action="store_true",
        help=(
            "Fail-closed verify checked-in synthetic ledger expectations against "
            "live compiled fixture manifests; reject digest drift without claiming "
            "calibrated trajectory benchmark pass"
        ),
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Fixture directory for synthetic ledger emission (default: checked-in row088 fixtures)",
    )
    args = parser.parse_args(argv)

    if args.emit_synthetic_benchmark_ledger:
        try:
            ledger = write_synthetic_camera_listener_source_trajectory_ledger(
                Path(args.emit_synthetic_benchmark_ledger),
                fixture_dir=Path(args.fixture_dir),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW088_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "record_type": ledger["record_type"],
                    "ledger_sha256": ledger["ledger_sha256"],
                    "row_complete": False,
                    "calibrated_trajectory_benchmark_pass": False,
                    "production_benchmark": False,
                    "visual_review_claimed": False,
                    "rows084_085_acceptance_claimed": False,
                    "fixture_binding_count": len(ledger["fixture_bindings"]),
                    "trajectory_metric_expectation_count": len(
                        ledger["trajectory_metric_expectations"]
                    ),
                }
            )
        )
        return 0

    if args.verify_synthetic_benchmark_ledger:
        try:
            receipt = verify_synthetic_ledger_vs_compiled_manifest_expectations(
                fixture_dir=Path(args.fixture_dir),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW088_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if not args.input or not args.output:
        raise SystemExit(
            "ROW088_FAIL_CLOSED: --input and --output are required unless emitting "
            "or verifying the synthetic ledger"
        )

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input packet must be a JSON object")
    try:
        receipt = compile_manifest(payload)
    except ValueError as exc:
        raise SystemExit(f"ROW088_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_sha256": receipt["manifest_sha256"],
                "row_complete": False,
                "spatial_certification_allowed": receipt["authority_summary"][
                    "spatial_certification_allowed"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
