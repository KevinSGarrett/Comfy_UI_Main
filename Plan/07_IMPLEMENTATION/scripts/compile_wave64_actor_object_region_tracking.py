#!/usr/bin/env python3
"""Fail-closed Row085 actor/object/region tracking compiler.

Compiles fixture track packets into a content-addressed ownership manifest.
Production completion remains blocked until Row084, annotated benchmarks,
runtime receipts, and combined visual review authorities are satisfied.
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
    "detector_stack",
    "dependency_authority",
    "runtime_authority",
    "tracks",
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

ALLOWED_DETECTOR_STACK_FIELDS = {
    "detector_id",
    "segmenter_id",
    "tracker_id",
    "association_id",
    "revision",
    "parameter_digest_sha256",
}

ALLOWED_TRACK_FIELDS = {
    "track_id",
    "owner_id",
    "entity_class",
    "parent_owner_id",
    "samples",
    "lifecycle_events",
}

ALLOWED_SAMPLE_FIELDS = {
    "frame_index",
    "pts",
    "bbox_xywh",
    "visibility",
    "state",
    "confidence",
    "mask_ref",
    "occluder_owner_ids",
    "depth_order",
}

ALLOWED_LIFECYCLE_FIELDS = {
    "event_type",
    "frame_index",
    "reason",
    "related_track_id",
}

ALLOWED_ENTITY_CLASSES = {
    "actor",
    "limb",
    "hand",
    "foot",
    "clothing_region",
    "prop",
    "furniture",
    "surface",
}

ALLOWED_VISIBILITY = {"visible", "partial", "occluded", "offscreen", "unknown"}
ALLOWED_STATES = {
    "active",
    "occluded",
    "lost",
    "reidentified",
    "terminated",
    "split",
    "merged",
}
ALLOWED_LIFECYCLE_EVENTS = {
    "spawn",
    "identity_switch",
    "occlusion_gap_start",
    "occlusion_gap_end",
    "reappearance",
    "lost",
    "reidentified",
    "split",
    "merged",
    "terminated",
}
ALLOWED_METRIC_FIELDS = {
    "identity_switch_count",
    "lost_track_count",
    "occlusion_gap_frames",
    "reappearance_count",
    "fragmentation_count",
    "merge_count",
    "split_count",
    "false_positive_count",
    "false_negative_count",
}
ALLOWED_THRESHOLD_FIELDS = {
    "max_identity_switch_count",
    "max_lost_track_count",
    "max_occlusion_gap_frames",
    "max_fragmentation_count",
    "max_merge_count",
    "max_split_count",
    "min_track_confidence",
}
SHA256_HEX_CHARS = set("0123456789abcdef")
BODY_ATTACHED_CLASSES = {"limb", "hand", "foot", "clothing_region"}
CONTENT_ADDRESSED_EXCLUDED_FIELDS = frozenset({"created_at", "manifest_sha256"})
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = (
    REPO_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Wave64" / "fixtures" / "row085"
)

# Checked-in synthetic benchmark packets for occlusion / reappearance / lost-track.
BENCHMARK_FIXTURE_PACKETS: tuple[dict[str, str], ...] = (
    {
        "name": "case_occlusion_gap.json",
        "role": "occlusion_gap",
        "case_id": "occlusion_gap",
    },
    {
        "name": "case_reappearance.json",
        "role": "reappearance",
        "case_id": "reappearance",
    },
    {
        "name": "case_lost_track.json",
        "role": "lost_track",
        "case_id": "lost_track",
    },
)

SYNTHETIC_BENCHMARK_LEDGER_FILENAME = "synthetic_tracking_benchmark_ledger.json"
ALLOWED_SYNTHETIC_LEDGER_FIELDS = {
    "schema_version",
    "record_type",
    "ledger_id",
    "revision",
    "is_synthetic",
    "production_benchmark",
    "annotated_tracking_benchmark_pass",
    "row_complete",
    "production_completion_allowed",
    "visual_review_claimed",
    "row084_acceptance_claimed",
    "authority_ceiling",
    "hold_reasons",
    "fixture_bindings",
    "tracking_metric_expectations",
    "provenance",
    "ledger_sha256",
}
ALLOWED_TRACKING_METRIC_EXPECTATION_FIELDS = {
    "case_id",
    "role",
    "source_fixture",
    "source_fixture_file_sha256",
    "source_compiled_manifest_sha256",
    "expected_occlusion_gap_frames",
    "expected_reappearance_count",
    "expected_lost_track_count",
    "expected_identity_switch_count",
}
LEDGER_EXPECTED_METRIC_KEYS = (
    "expected_occlusion_gap_frames",
    "expected_reappearance_count",
    "expected_lost_track_count",
    "expected_identity_switch_count",
)
COMPILED_METRIC_KEYS_FOR_LEDGER = (
    "occlusion_gap_frames",
    "reappearance_count",
    "lost_track_count",
    "identity_switch_count",
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
    """Load a checked-in Row085 fixture packet by filename."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row085 fixture packet missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row085 fixture packet must be a JSON object: {path}")
    return payload


def fixture_file_sha256(name: str, *, fixture_dir: Path | None = None) -> str:
    """Return the lowercase sha256 of a checked-in fixture packet file bytes."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row085 fixture packet missing: {path}")
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
    """Load the checked-in non-production synthetic tracking benchmark ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Row085 synthetic benchmark ledger missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row085 synthetic benchmark ledger must be a JSON object: {path}")
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

    Recompiles every ledger-bound fixture packet and rejects:
    - fixture-file digest drift
    - compiled-manifest digest drift
    - expected occlusion/reappearance/lost-track metric drift

    Explicitly refuses annotated tracking benchmark pass, visual-review,
    Row084 acceptance, and row completion claims. Synthetic fixture authority only.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    payload = ledger if ledger is not None else load_synthetic_benchmark_ledger(fixture_dir=directory)
    if not isinstance(payload, dict):
        raise ValueError("synthetic ledger must be an object")
    _assert_keys_exact(payload, ALLOWED_SYNTHETIC_LEDGER_FIELDS, "synthetic_ledger")
    ledger_digest = verify_synthetic_benchmark_ledger_integrity(payload)

    if payload.get("record_type") != "row085_synthetic_tracking_benchmark_ledger":
        raise ValueError("synthetic ledger record_type mismatch")
    if payload.get("is_synthetic") is not True:
        raise ValueError("synthetic ledger must set is_synthetic=true")
    if payload.get("authority_ceiling") != "fixture_synthetic_only":
        raise ValueError("synthetic ledger authority_ceiling must remain fixture_synthetic_only")

    false_flags = (
        "production_benchmark",
        "annotated_tracking_benchmark_pass",
        "row_complete",
        "production_completion_allowed",
        "visual_review_claimed",
        "row084_acceptance_claimed",
    )
    for flag in false_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"synthetic ledger must keep {flag}=false")

    bindings = payload.get("fixture_bindings")
    if not isinstance(bindings, list) or len(bindings) != len(BENCHMARK_FIXTURE_PACKETS):
        raise ValueError(
            "synthetic ledger fixture_bindings must cover exactly three tracking cases"
        )
    expectations = payload.get("tracking_metric_expectations")
    if not isinstance(expectations, list) or len(expectations) != len(BENCHMARK_FIXTURE_PACKETS):
        raise ValueError(
            "synthetic ledger tracking_metric_expectations must cover exactly three cases"
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
        if compiled["runtime_authority"].get("annotated_benchmark_pass"):
            raise ValueError(f"{label}: compiled fixture must not claim annotated_benchmark_pass")
        if compiled["dependency_authority"].get("row084_complete"):
            raise ValueError(f"{label}: compiled fixture must not claim row084_complete")

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
        label = f"tracking_metric_expectations[{idx}]"
        if not isinstance(expectation, dict):
            raise ValueError(f"{label} must be an object")
        _assert_keys_exact(expectation, ALLOWED_TRACKING_METRIC_EXPECTATION_FIELDS, label)
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
            "synthetic ledger tracking case set drift: "
            f"ledger={sorted(seen_cases)} expected={sorted(expected_cases)}"
        )

    return {
        "status": "ok",
        "verifier": "verify_synthetic_ledger_vs_compiled_manifest_expectations",
        "ledger_sha256": ledger_digest,
        "fixture_binding_count": len(bindings),
        "tracking_metric_expectation_count": len(expectations),
        "digest_drift_rejected": True,
        "production_benchmark": False,
        "annotated_tracking_benchmark_pass": False,
        "visual_review_claimed": False,
        "row084_acceptance_claimed": False,
        "row_complete": False,
        "authority_ceiling": "fixture_synthetic_only",
    }


def build_synthetic_tracking_benchmark_ledger(
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Bind fixture digests into a non-production tracking benchmark ledger.

    Records expected occlusion/reappearance/lost-track metrics per fixture case.
    Explicitly refuses annotated tracking benchmark pass, visual-review, and
    Row084 acceptance claims. ``row_complete`` remains false.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    fixture_bindings: list[dict[str, Any]] = []
    tracking_metric_expectations: list[dict[str, Any]] = []

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
        if compiled["runtime_authority"].get("annotated_benchmark_pass"):
            raise ValueError(
                f"fixture {name} must not claim annotated_benchmark_pass in synthetic ledger"
            )
        if compiled["dependency_authority"].get("row084_complete"):
            raise ValueError(
                f"fixture {name} must not claim row084_complete in synthetic ledger"
            )

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
        tracking_metric_expectations.append(
            {
                "case_id": case_id,
                "role": role,
                "source_fixture": name,
                "source_fixture_file_sha256": file_digest,
                "source_compiled_manifest_sha256": compiled_digest,
                "expected_occlusion_gap_frames": metrics["occlusion_gap_frames"],
                "expected_reappearance_count": metrics["reappearance_count"],
                "expected_lost_track_count": metrics["lost_track_count"],
                "expected_identity_switch_count": metrics["identity_switch_count"],
            }
        )

    if len(fixture_bindings) != 3 or len(tracking_metric_expectations) != 3:
        raise ValueError("synthetic ledger requires exactly three tracking fixture cases")

    fixture_bindings.sort(key=lambda item: item["fixture_name"])
    tracking_metric_expectations.sort(key=lambda item: item["case_id"])

    ledger_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row085_synthetic_tracking_benchmark_ledger",
        "ledger_id": "row085_synthetic_tracking_benchmark_ledger_v1",
        "revision": "row085_synthetic_ledger_v1",
        "is_synthetic": True,
        "production_benchmark": False,
        "annotated_tracking_benchmark_pass": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "visual_review_claimed": False,
        "row084_acceptance_claimed": False,
        "authority_ceiling": "fixture_synthetic_only",
        "hold_reasons": [
            "synthetic_fixture_ledger_only",
            "dependency_row084_incomplete",
            "annotated_tracking_benchmark_absent",
            "runtime_receipt_absent",
            "combined_track_overlay_contact_audio_review_absent",
        ],
        "fixture_bindings": fixture_bindings,
        "tracking_metric_expectations": tracking_metric_expectations,
        "provenance": {
            "compiler": "compile_wave64_actor_object_region_tracking.py",
            "compiler_revision": "row085_synthetic_tracking_benchmark_ledger_v1",
            "non_production": True,
            "binds_fixture_file_and_compiled_manifest_digests": True,
            "records_expected_occlusion_reappearance_lost_track_metrics": True,
        },
    }
    _assert_keys_exact(
        ledger_body, ALLOWED_SYNTHETIC_LEDGER_FIELDS - {"ledger_sha256"}, "synthetic_ledger"
    )
    ledger_body["ledger_sha256"] = _canonical_sha256(ledger_body)
    verify_synthetic_benchmark_ledger_integrity(ledger_body)
    return ledger_body


def write_synthetic_tracking_benchmark_ledger(
    output_path: Path | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Build and atomically write the synthetic tracking benchmark ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = output_path if output_path is not None else directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    ledger = build_synthetic_tracking_benchmark_ledger(fixture_dir=directory)
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


def _validate_detector_stack(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("detector_stack must be an object")
    _assert_keys_exact(raw, ALLOWED_DETECTOR_STACK_FIELDS, "detector_stack")
    return {
        "detector_id": _expect_non_empty_string(raw.get("detector_id"), "detector_stack.detector_id"),
        "segmenter_id": _expect_non_empty_string(raw.get("segmenter_id"), "detector_stack.segmenter_id"),
        "tracker_id": _expect_non_empty_string(raw.get("tracker_id"), "detector_stack.tracker_id"),
        "association_id": _expect_non_empty_string(
            raw.get("association_id"), "detector_stack.association_id"
        ),
        "revision": _expect_non_empty_string(raw.get("revision"), "detector_stack.revision"),
        "parameter_digest_sha256": _expect_sha256(
            raw.get("parameter_digest_sha256"), "detector_stack.parameter_digest_sha256"
        ),
    }


def _validate_bbox(raw: Any, label: str) -> list[float]:
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError(f"{label} must be a 4-number [x,y,w,h] array")
    values = [_expect_number(item, f"{label}[{idx}]") for idx, item in enumerate(raw)]
    if values[2] <= 0 or values[3] <= 0:
        raise ValueError(f"{label} width and height must be > 0")
    return values


def _validate_sample(
    raw: Any,
    *,
    index: int,
    track_label: str,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{track_label}.samples[{index}] must be an object")
    label = f"{track_label}.samples[{index}]"
    _assert_keys_exact(raw, ALLOWED_SAMPLE_FIELDS, label)

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    if previous_frame is not None:
        if frame_index <= previous_frame:
            raise ValueError(f"{label}.frame_index must be unique and strictly increasing")
        if pts <= previous_pts:
            raise ValueError(f"{label}.pts must be unique and strictly increasing")

    visibility = _expect_non_empty_string(raw.get("visibility"), f"{label}.visibility")
    if visibility not in ALLOWED_VISIBILITY:
        raise ValueError(f"{label}.visibility must be one of {sorted(ALLOWED_VISIBILITY)}")
    state = _expect_non_empty_string(raw.get("state"), f"{label}.state")
    if state not in ALLOWED_STATES:
        raise ValueError(f"{label}.state must be one of {sorted(ALLOWED_STATES)}")
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    occluders_raw = raw.get("occluder_owner_ids")
    if not isinstance(occluders_raw, list):
        raise ValueError(f"{label}.occluder_owner_ids must be an array")
    occluders = [
        _expect_non_empty_string(item, f"{label}.occluder_owner_ids[{idx}]")
        for idx, item in enumerate(occluders_raw)
    ]
    if state == "occluded" and not occluders and visibility not in {"occluded", "partial"}:
        raise ValueError(f"{label} occluded state requires occluder_owner_ids or occluded/partial visibility")

    depth_order = raw.get("depth_order")
    depth_value = None if depth_order is None else _expect_non_negative_int(depth_order, f"{label}.depth_order")

    return {
        "frame_index": frame_index,
        "pts": pts,
        "bbox_xywh": _validate_bbox(raw.get("bbox_xywh"), f"{label}.bbox_xywh"),
        "visibility": visibility,
        "state": state,
        "confidence": confidence,
        "mask_ref": _expect_optional_string_or_none(raw.get("mask_ref"), f"{label}.mask_ref"),
        "occluder_owner_ids": occluders,
        "depth_order": depth_value,
    }


def _validate_lifecycle_event(raw: Any, *, index: int, track_label: str, frame_count: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{track_label}.lifecycle_events[{index}] must be an object")
    label = f"{track_label}.lifecycle_events[{index}]"
    _assert_keys_exact(raw, ALLOWED_LIFECYCLE_FIELDS, label)
    event_type = _expect_non_empty_string(raw.get("event_type"), f"{label}.event_type")
    if event_type not in ALLOWED_LIFECYCLE_EVENTS:
        raise ValueError(f"{label}.event_type must be one of {sorted(ALLOWED_LIFECYCLE_EVENTS)}")
    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    return {
        "event_type": event_type,
        "frame_index": frame_index,
        "reason": _expect_non_empty_string(raw.get("reason"), f"{label}.reason"),
        "related_track_id": _expect_optional_string_or_none(
            raw.get("related_track_id"), f"{label}.related_track_id"
        ),
    }


def _compile_track(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    owner_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"tracks[{index}] must be an object")
    label = f"tracks[{index}]"
    _assert_keys_exact(raw, ALLOWED_TRACK_FIELDS, label)

    track_id = _expect_non_empty_string(raw.get("track_id"), f"{label}.track_id")
    owner_id = _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id")
    entity_class = _expect_non_empty_string(raw.get("entity_class"), f"{label}.entity_class")
    if entity_class not in ALLOWED_ENTITY_CLASSES:
        raise ValueError(f"{label}.entity_class must be one of {sorted(ALLOWED_ENTITY_CLASSES)}")
    parent_owner_id = _expect_optional_string_or_none(raw.get("parent_owner_id"), f"{label}.parent_owner_id")
    if entity_class in BODY_ATTACHED_CLASSES and parent_owner_id is None:
        raise ValueError(f"{label} {entity_class} requires parent_owner_id")
    if parent_owner_id is not None and parent_owner_id not in owner_ids and parent_owner_id != owner_id:
        # Parent may be declared on another actor track in the same packet; checked after full pass.
        pass

    samples_raw = raw.get("samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise ValueError(f"{label}.samples must be a non-empty list")
    samples: list[dict[str, Any]] = []
    previous_frame: int | None = None
    previous_pts: int | None = None
    for sample_idx, sample_raw in enumerate(samples_raw):
        sample = _validate_sample(
            sample_raw,
            index=sample_idx,
            track_label=label,
            frame_count=frame_count,
            previous_frame=previous_frame,
            previous_pts=previous_pts,
        )
        previous_frame = sample["frame_index"]
        previous_pts = sample["pts"]
        samples.append(sample)

    events_raw = raw.get("lifecycle_events")
    if not isinstance(events_raw, list):
        raise ValueError(f"{label}.lifecycle_events must be an array")
    lifecycle_events = [
        _validate_lifecycle_event(event_raw, index=event_idx, track_label=label, frame_count=frame_count)
        for event_idx, event_raw in enumerate(events_raw)
    ]
    lifecycle_events = sorted(lifecycle_events, key=lambda item: (item["frame_index"], item["event_type"]))

    owner_consistent = all(sample["state"] != "merged" for sample in samples) or any(
        event["event_type"] == "merged" for event in lifecycle_events
    )
    if not owner_consistent:
        raise ValueError(f"{label} merged samples require a merged lifecycle event")

    return {
        "track_id": track_id,
        "owner_id": owner_id,
        "entity_class": entity_class,
        "parent_owner_id": parent_owner_id,
        "sample_count": len(samples),
        "first_frame": samples[0]["frame_index"],
        "last_frame": samples[-1]["frame_index"],
        "samples": samples,
        "lifecycle_events": lifecycle_events,
        "ownership_trusted": True,
    }


def _validate_metrics(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError("metrics must be an object")
    _assert_keys_exact(raw, ALLOWED_METRIC_FIELDS, "metrics")
    return {
        key: _expect_non_negative_int(raw.get(key), f"metrics.{key}") for key in sorted(ALLOWED_METRIC_FIELDS)
    }


def _validate_thresholds(raw: Any) -> dict[str, float | int]:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    _assert_keys_exact(raw, ALLOWED_THRESHOLD_FIELDS, "thresholds")
    result: dict[str, float | int] = {}
    for key in sorted(ALLOWED_THRESHOLD_FIELDS):
        if key == "min_track_confidence":
            value = _expect_number(raw.get(key), f"thresholds.{key}")
            if value < 0 or value > 1:
                raise ValueError("thresholds.min_track_confidence must be within [0, 1]")
            result[key] = value
        else:
            result[key] = _expect_non_negative_int(raw.get(key), f"thresholds.{key}")
    return result


def _derive_metrics_from_tracks(tracks: list[dict[str, Any]]) -> dict[str, int]:
    identity_switch_count = 0
    lost_track_count = 0
    occlusion_gap_frames = 0
    reappearance_count = 0
    fragmentation_count = 0
    merge_count = 0
    split_count = 0

    for track in tracks:
        events = track["lifecycle_events"]
        identity_switch_count += sum(1 for event in events if event["event_type"] == "identity_switch")
        lost_track_count += sum(1 for event in events if event["event_type"] == "lost")
        reappearance_count += sum(1 for event in events if event["event_type"] == "reappearance")
        merge_count += sum(1 for event in events if event["event_type"] == "merged")
        split_count += sum(1 for event in events if event["event_type"] == "split")
        fragmentation_count += sum(1 for event in events if event["event_type"] in {"split", "merged"})

        gap_starts = [event["frame_index"] for event in events if event["event_type"] == "occlusion_gap_start"]
        gap_ends = [event["frame_index"] for event in events if event["event_type"] == "occlusion_gap_end"]
        if len(gap_starts) != len(gap_ends):
            raise ValueError(f"track {track['track_id']} occlusion gap start/end counts must match")
        for start, end in zip(sorted(gap_starts), sorted(gap_ends), strict=True):
            if end < start:
                raise ValueError(f"track {track['track_id']} occlusion gap end precedes start")
            occlusion_gap_frames += end - start + 1

    return {
        "identity_switch_count": identity_switch_count,
        "lost_track_count": lost_track_count,
        "occlusion_gap_frames": occlusion_gap_frames,
        "reappearance_count": reappearance_count,
        "fragmentation_count": fragmentation_count,
        "merge_count": merge_count,
        "split_count": split_count,
        "false_positive_count": 0,
        "false_negative_count": 0,
    }


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    timeline_binding = _validate_timeline_binding(payload.get("timeline_binding"))
    detector_stack = _validate_detector_stack(payload.get("detector_stack"))

    dependency_raw = payload.get("dependency_authority")
    if not isinstance(dependency_raw, dict):
        raise ValueError("dependency_authority must be an object")
    _assert_keys_exact(dependency_raw, {"row084_complete"}, "dependency_authority")
    row084_complete = _expect_boolean(dependency_raw.get("row084_complete"), "dependency_authority.row084_complete")

    runtime_raw = payload.get("runtime_authority")
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_allowed = {
        "annotated_benchmark_pass",
        "runtime_receipt_present",
        "combined_track_overlay_contact_audio_review_present",
    }
    _assert_keys_exact(runtime_raw, runtime_allowed, "runtime_authority")
    annotated_benchmark_pass = _expect_boolean(
        runtime_raw.get("annotated_benchmark_pass"), "runtime_authority.annotated_benchmark_pass"
    )
    runtime_receipt_present = _expect_boolean(
        runtime_raw.get("runtime_receipt_present"), "runtime_authority.runtime_receipt_present"
    )
    combined_review_present = _expect_boolean(
        runtime_raw.get("combined_track_overlay_contact_audio_review_present"),
        "runtime_authority.combined_track_overlay_contact_audio_review_present",
    )

    tracks_raw = payload.get("tracks")
    if not isinstance(tracks_raw, list) or not tracks_raw:
        raise ValueError("tracks must be a non-empty list")

    actor_owner_ids = {
        _expect_non_empty_string(track.get("owner_id"), f"tracks[{idx}].owner_id")
        for idx, track in enumerate(tracks_raw)
        if isinstance(track, dict) and track.get("entity_class") == "actor"
    }
    all_owner_ids = {
        _expect_non_empty_string(track.get("owner_id"), f"tracks[{idx}].owner_id")
        for idx, track in enumerate(tracks_raw)
        if isinstance(track, dict)
    }

    tracks: list[dict[str, Any]] = []
    seen_track_ids: set[str] = set()
    entity_classes_present: set[str] = set()
    for idx, track_raw in enumerate(tracks_raw):
        compiled = _compile_track(
            track_raw,
            index=idx,
            frame_count=timeline_binding["frame_count"],
            owner_ids=all_owner_ids,
        )
        if compiled["track_id"] in seen_track_ids:
            raise ValueError(f"duplicate track_id detected: {compiled['track_id']}")
        seen_track_ids.add(compiled["track_id"])
        if compiled["entity_class"] in BODY_ATTACHED_CLASSES:
            parent = compiled["parent_owner_id"]
            if parent not in actor_owner_ids:
                raise ValueError(
                    f"track {compiled['track_id']} parent_owner_id must reference an actor owner_id"
                )
        entity_classes_present.add(compiled["entity_class"])
        tracks.append(compiled)

    required_taxonomy = {"actor", "prop", "surface"}
    missing_taxonomy = sorted(required_taxonomy - entity_classes_present)
    if missing_taxonomy:
        raise ValueError(f"entity taxonomy incomplete; missing required classes: {', '.join(missing_taxonomy)}")

    declared_metrics = _validate_metrics(payload.get("metrics"))
    derived_metrics = _derive_metrics_from_tracks(tracks)
    # Preserve declared false positive/negative counts; derive the lifecycle metrics.
    for key in (
        "identity_switch_count",
        "lost_track_count",
        "occlusion_gap_frames",
        "reappearance_count",
        "fragmentation_count",
        "merge_count",
        "split_count",
    ):
        if declared_metrics[key] != derived_metrics[key]:
            raise ValueError(
                f"metrics.{key}={declared_metrics[key]} does not match derived lifecycle count {derived_metrics[key]}"
            )
    metrics = {
        **derived_metrics,
        "false_positive_count": declared_metrics["false_positive_count"],
        "false_negative_count": declared_metrics["false_negative_count"],
    }
    thresholds = _validate_thresholds(payload.get("thresholds"))

    threshold_violations: list[str] = []
    comparisons = (
        ("identity_switch_count", "max_identity_switch_count"),
        ("lost_track_count", "max_lost_track_count"),
        ("occlusion_gap_frames", "max_occlusion_gap_frames"),
        ("fragmentation_count", "max_fragmentation_count"),
        ("merge_count", "max_merge_count"),
        ("split_count", "max_split_count"),
    )
    for metric_key, threshold_key in comparisons:
        if metrics[metric_key] > thresholds[threshold_key]:
            threshold_violations.append(f"{metric_key}>{threshold_key}")

    low_confidence_tracks = [
        track["track_id"]
        for track in tracks
        if min(sample["confidence"] for sample in track["samples"]) < thresholds["min_track_confidence"]
    ]
    if low_confidence_tracks:
        threshold_violations.append("min_track_confidence")

    ownership_unsupported = bool(threshold_violations) or metrics["identity_switch_count"] > 0
    for track in tracks:
        track["ownership_trusted"] = not ownership_unsupported
        if ownership_unsupported:
            track["ownership_block_reason"] = "unsupported_or_threshold_violating_ownership"
        else:
            track["ownership_block_reason"] = None

    dependency_ready = row084_complete
    runtime_ready = annotated_benchmark_pass and runtime_receipt_present and combined_review_present
    contact_foley_certification_allowed = (
        dependency_ready and runtime_ready and not ownership_unsupported and not threshold_violations
    )
    # Fail closed in this increment: no production tracker runtime authority yet.
    production_completion_allowed = False
    row_complete = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    elif ownership_unsupported or not runtime_ready:
        authority_ceiling = "technical"
        status = "technical_partial"
    else:
        authority_ceiling = "technical"
        status = "technical_partial"

    hold_reasons: list[str] = []
    if not dependency_ready:
        hold_reasons.append("dependency_row084_incomplete")
    if not annotated_benchmark_pass:
        hold_reasons.append("annotated_benchmark_absent")
    if not runtime_receipt_present:
        hold_reasons.append("runtime_receipt_absent")
    if not combined_review_present:
        hold_reasons.append("combined_track_overlay_contact_audio_review_absent")
    if ownership_unsupported:
        hold_reasons.append("unsupported_ownership_blocks_contact_foley_certification")
    if threshold_violations:
        hold_reasons.append("threshold_violations:" + ",".join(threshold_violations))

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_actor_object_region_tracking.py",
            "compiler_revision": "row085_fail_closed_v1",
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "actor_object_region_tracking_manifest",
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
        "detector_stack": detector_stack,
        "dependency_authority": {
            "row084_complete": row084_complete,
            "dependency_ready": dependency_ready,
        },
        "runtime_authority": {
            "annotated_benchmark_pass": annotated_benchmark_pass,
            "runtime_receipt_present": runtime_receipt_present,
            "combined_track_overlay_contact_audio_review_present": combined_review_present,
            "runtime_ready": runtime_ready,
        },
        "entity_taxonomy_present": sorted(entity_classes_present),
        "tracks": tracks,
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_violations": threshold_violations,
        "authority_summary": {
            "track_count": len(tracks),
            "owner_count": len({track["owner_id"] for track in tracks}),
            "ownership_unsupported": ownership_unsupported,
            "contact_foley_certification_allowed": contact_foley_certification_allowed,
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
        description="Compile a fail-closed Row085 actor/object/region tracking manifest."
    )
    parser.add_argument("--input", help="Path to tracking input packet JSON")
    parser.add_argument("--output", help="Path to write compiled tracking manifest JSON")
    parser.add_argument(
        "--emit-synthetic-benchmark-ledger",
        metavar="PATH",
        help=(
            "Build the non-production synthetic tracking benchmark ledger bound to "
            "checked-in fixture digests and write it to PATH"
        ),
    )
    parser.add_argument(
        "--verify-synthetic-benchmark-ledger",
        action="store_true",
        help=(
            "Fail-closed verify checked-in synthetic ledger expectations against "
            "live compiled fixture manifests; reject digest drift without claiming "
            "annotated tracking benchmark pass"
        ),
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Fixture directory for synthetic ledger emission (default: checked-in row085 fixtures)",
    )
    args = parser.parse_args(argv)

    if args.emit_synthetic_benchmark_ledger:
        try:
            ledger = write_synthetic_tracking_benchmark_ledger(
                Path(args.emit_synthetic_benchmark_ledger),
                fixture_dir=Path(args.fixture_dir),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW085_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "record_type": ledger["record_type"],
                    "ledger_sha256": ledger["ledger_sha256"],
                    "row_complete": False,
                    "annotated_tracking_benchmark_pass": False,
                    "production_benchmark": False,
                    "visual_review_claimed": False,
                    "row084_acceptance_claimed": False,
                    "fixture_binding_count": len(ledger["fixture_bindings"]),
                    "tracking_metric_expectation_count": len(
                        ledger["tracking_metric_expectations"]
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
            raise SystemExit(f"ROW085_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if not args.input or not args.output:
        raise SystemExit(
            "ROW085_FAIL_CLOSED: --input and --output are required unless emitting "
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
        raise SystemExit(f"ROW085_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_sha256": receipt["manifest_sha256"],
                "row_complete": False,
                "contact_foley_certification_allowed": receipt["authority_summary"][
                    "contact_foley_certification_allowed"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
