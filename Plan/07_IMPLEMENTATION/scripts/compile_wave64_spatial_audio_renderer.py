#!/usr/bin/env python3
"""Fail-closed Wave64 Row095 spatial audio renderer contract slice.

Production spatial rendering refuses authority without accepted Row088 depth/
listener geometry, Row091 visual event manifests, and Row093 prepared clips.
Fixture mode may emit deterministic schema-validated synthetic trajectory
manifests and hold evidence without granting production, runtime, or row
completion authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path(
    "Plan/08_SCHEMAS/wave64_row095_spatial_audio_render_manifest.schema.json"
)
REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row095_spatial_audio_renderer_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-095_spatial_audio_renderer.json"
)
ROW088_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-088_DEPTH_CAMERA_SOURCE_POSITION_CURRENT_DELTA_20260719.json"
)
ROW091_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"
)
ROW093_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-093_CANONICAL_CLIP_PREPARATION_CURRENT_DELTA_20260719.json"
)

COMPILER_REVISION = "wave64_row095_spatial_audio_renderer_compiler_v0.1.0"
REGISTRY_REVISION = "wave64_row095_spatial_audio_renderer_registry_v0.1.0"
TRACKER_ID = "TRK-W64-095"
ITEM_ID = "ITEM-W64-095"
SCHEMA_VERSION = "1.0.0"

FIXTURE_NAMES = (
    "moving_source_trajectory_pass",
    "time_varying_occlusion_offscreen",
    "reject_wet_source_blocked",
    "unknown_room_blocked",
    "gate_failure_blocked",
)

REQUIRED_CAPABILITIES = (
    "stereo_or_binaural_pan",
    "distance_attenuation",
    "air_absorption",
    "elevation_cue",
    "screen_movement",
    "occlusion_filtering",
    "offscreen_continuity",
    "phase_integrity",
    "clipping_integrity",
    "loudness_integrity",
)


class SpatialAudioRendererError(ValueError):
    """Raised when Row095 spatial compilation violates fail-closed authority."""


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


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def canonical_json_sha256(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SpatialAudioRendererError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row095_fixture:{label}".encode("utf-8"))


def load_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, REGISTRY_PATH, "registry")
    payload = load_json(path)
    if payload.get("registry_revision") != REGISTRY_REVISION:
        raise SpatialAudioRendererError("registry_revision_mismatch")
    if payload.get("compiler_revision") != COMPILER_REVISION:
        raise SpatialAudioRendererError("compiler_revision_mismatch")
    caps = payload.get("required_capabilities")
    if not isinstance(caps, list) or tuple(caps) != REQUIRED_CAPABILITIES:
        raise SpatialAudioRendererError("required_capabilities_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
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
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    acceptance_values = [
        str(decision.get(key, "")).lower()
        for key in (
            "status",
            "row088_acceptance",
            "row091_acceptance",
            "row093_acceptance",
            "acceptance",
        )
    ]
    accepted = row_complete and any(
        value in {"accepted", "pass", "passed"} for value in acceptance_values
    )
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        accepted = False
    if any(value == "held" for value in acceptance_values):
        accepted = False
    dependency_satisfied = bool(accepted)
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


def evaluate_row088_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW088_DELTA,
        tracker_id="TRK-W64-088",
        blocker_code="ROW088_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW088_DELTA_ABSENT",
    )


def evaluate_row091_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW091_DELTA,
        tracker_id="TRK-W64-091",
        blocker_code="ROW091_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW091_DELTA_ABSENT",
    )


def evaluate_row093_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW093_DELTA,
        tracker_id="TRK-W64-093",
        blocker_code="ROW093_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW093_DELTA_ABSENT",
    )


def validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise SpatialAudioRendererError(
            f"schema_validation_failed:{location}:{first.message}"
        )
    if manifest.get("production_authority") is True:
        raise SpatialAudioRendererError("production_authority_forbidden_in_contract_slice")
    if manifest.get("decision", {}).get("promotion_eligible") is True:
        raise SpatialAudioRendererError("promotion_eligible_forbidden_in_contract_slice")
    if manifest.get("is_synthetic") is True and manifest.get("decision", {}).get(
        "product_completion"
    ):
        raise SpatialAudioRendererError("synthetic_product_completion_forbidden")


def _trajectory_pair(
    *,
    start: dict[str, Any],
    end: dict[str, Any],
) -> list[dict[str, Any]]:
    return [start, end]


def _output_block(registry: dict[str, Any], seed: str) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "path": f"fixtures/row095/{seed}.wav",
        "sha256": _stable_hash(f"wav:{seed}"),
        "canonical_pcm_sha256": _stable_hash(f"pcm:{seed}"),
        "sample_rate_hz": int(contract["sample_rate_hz"]),
        "channels": int(contract["channels"]),
        "duration_seconds": 3.2,
        "peak_absolute": 0.42,
        "true_peak_dbfs": -3.5,
        "integrated_loudness_lufs": float(contract["integrated_loudness_lufs_target"]),
    }


def _renderer_block(registry: dict[str, Any], seed: str) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    configuration = {
        "distance_model": contract["distance_model"],
        "elevation_model": contract["elevation_model"],
        "air_absorption_model": contract["air_absorption_model"],
        "screen_motion_model": contract["screen_motion_model"],
        "occlusion_filter_model": contract["occlusion_filter_model"],
        "seed": seed,
    }
    return {
        "name": "wave64_row095_synthetic_spatial_fixture_renderer",
        "revision": COMPILER_REVISION,
        "configuration_sha256": canonical_json_sha256(configuration),
        "sample_rate_hz": int(contract["sample_rate_hz"]),
        "channels": int(contract["channels"]),
        "deterministic": True,
    }


def _base_source(
    registry: dict[str, Any],
    *,
    event_id: str,
    trajectory: list[dict[str, Any]],
    wet_source_policy: str = "dry_render",
) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "event_id": event_id,
        "prepared_clip_sha256": _stable_hash(f"clip:{event_id}"),
        "trajectory": trajectory,
        "distance_model": contract["distance_model"],
        "occlusion": {
            "enabled": True,
            "filter_model": contract["occlusion_filter_model"],
            "time_varying": True,
        },
        "wet_source_policy": wet_source_policy,
        "elevation_model": contract["elevation_model"],
        "air_absorption_model": contract["air_absorption_model"],
        "screen_motion_model": contract["screen_motion_model"],
    }


def _validation_pass(registry: dict[str, Any]) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "measured_rt60_seconds": float(registry["room_fixture"]["target_rt60_seconds"]),
        "rt60_pass": True,
        "trajectory_pass": True,
        "phase_pass": True,
        "clipping_pass": True,
        "elevation_pass": True,
        "air_absorption_pass": True,
        "offscreen_continuity_pass": True,
        "loudness_pass": True,
        "occlusion_pass": True,
        "phase_correlation": float(contract["phase_correlation_min"]),
        "clipping_ratio": 0.0,
        "trajectory_max_error_m": float(contract["trajectory_max_error_m_max"]),
        "decision": "pass",
    }


def _validation_blocked(
    registry: dict[str, Any],
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "measured_rt60_seconds": float(registry["room_fixture"]["target_rt60_seconds"]),
        "rt60_pass": False,
        "trajectory_pass": False,
        "phase_pass": False,
        "clipping_pass": False,
        "elevation_pass": False,
        "air_absorption_pass": False,
        "offscreen_continuity_pass": False,
        "loudness_pass": False,
        "occlusion_pass": False,
        "phase_correlation": 0.1,
        "clipping_ratio": 0.0,
        "trajectory_max_error_m": 1.0,
        "decision": "blocked",
    }
    if overrides:
        payload.update(overrides)
    return payload


def build_manifest(
    root: Path,
    *,
    render_id: str,
    room: dict[str, Any],
    sources: list[dict[str, Any]],
    validation: dict[str, Any],
    blocker_codes: list[str],
    status: str,
    acceptance: str,
) -> dict[str, Any]:
    registry = load_registry(root)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "render_id": render_id,
        "event_manifest_sha256": _stable_hash("event_manifest"),
        "rights_decision_sha256": _stable_hash("rights_decision"),
        "depth_camera_authority_sha256": _stable_hash("depth_camera"),
        "prepared_clip_authority_sha256": _stable_hash("prepared_clip"),
        "room": room,
        "listener": deepcopy(registry["listener_fixture"]),
        "sources": sources,
        "renderer": _renderer_block(registry, render_id),
        "output": _output_block(registry, render_id),
        "validation": validation,
        "is_synthetic": True,
        "production_authority": False,
        "decision": {
            "status": status,
            "row095_acceptance": acceptance,
            "product_completion": False,
            "runtime_completion": False,
            "promotion_eligible": False,
            "blocker_codes": sorted(set(blocker_codes)),
            "advisory_only": True,
        },
    }
    validate_manifest(root, manifest)
    return manifest


def extract_fixture_manifest(root: Path, fixture_name: str) -> dict[str, Any]:
    if fixture_name not in FIXTURE_NAMES:
        raise SpatialAudioRendererError(f"unknown_fixture:{fixture_name}")
    registry = load_registry(root)
    room = deepcopy(registry["room_fixture"])
    common_blockers = [
        "PRODUCTION_AUTHORITY_NOT_GRANTED",
        "ROW088_ROW091_ROW093_DEPENDENCIES_NOT_ACCEPTED",
    ]

    if fixture_name == "moving_source_trajectory_pass":
        trajectory = _trajectory_pair(
            start={
                "time_s": 0.0,
                "position_m": [-1.5, 1.2, 1.6],
                "distance_m": 1.92,
                "azimuth_deg": -51.3,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
            end={
                "time_s": 3.2,
                "position_m": [1.5, 1.2, 1.6],
                "distance_m": 1.92,
                "azimuth_deg": 51.3,
                "elevation_deg": 5.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
        )
        return build_manifest(
            root,
            render_id="fixture:moving_source_trajectory_pass",
            room=room,
            sources=[
                _base_source(
                    registry,
                    event_id="fixture_event_moving_source",
                    trajectory=trajectory,
                )
            ],
            validation=_validation_pass(registry),
            blocker_codes=common_blockers,
            status="fixture_ok",
            acceptance="fixture_only",
        )

    if fixture_name == "time_varying_occlusion_offscreen":
        trajectory = _trajectory_pair(
            start={
                "time_s": 0.0,
                "position_m": [0.8, 2.0, 1.7],
                "distance_m": 2.15,
                "azimuth_deg": 22.0,
                "elevation_deg": 3.0,
                "occlusion_amount": 0.2,
                "visibility": "partial",
                "offscreen": False,
                "air_absorption_db_per_m": 0.015,
            },
            end={
                "time_s": 2.5,
                "position_m": [2.8, 0.4, 1.7],
                "distance_m": 2.83,
                "azimuth_deg": 82.0,
                "elevation_deg": 2.0,
                "occlusion_amount": 0.85,
                "visibility": "offscreen",
                "offscreen": True,
                "air_absorption_db_per_m": 0.02,
            },
        )
        return build_manifest(
            root,
            render_id="fixture:time_varying_occlusion_offscreen",
            room=room,
            sources=[
                _base_source(
                    registry,
                    event_id="fixture_event_occlusion_offscreen",
                    trajectory=trajectory,
                )
            ],
            validation=_validation_pass(registry),
            blocker_codes=common_blockers,
            status="fixture_ok",
            acceptance="fixture_only",
        )

    if fixture_name == "reject_wet_source_blocked":
        trajectory = _trajectory_pair(
            start={
                "time_s": 0.0,
                "position_m": [0.5, 1.0, 1.6],
                "distance_m": 1.12,
                "azimuth_deg": 26.6,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
            end={
                "time_s": 1.0,
                "position_m": [0.6, 1.0, 1.6],
                "distance_m": 1.17,
                "azimuth_deg": 31.0,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
        )
        return build_manifest(
            root,
            render_id="fixture:reject_wet_source_blocked",
            room=room,
            sources=[
                _base_source(
                    registry,
                    event_id="fixture_event_reject_wet",
                    trajectory=trajectory,
                    wet_source_policy="reject",
                )
            ],
            validation=_validation_blocked(
                registry,
                overrides={
                    "rt60_pass": True,
                    "trajectory_pass": True,
                    "phase_pass": True,
                    "clipping_pass": True,
                    "elevation_pass": True,
                    "air_absorption_pass": True,
                    "offscreen_continuity_pass": True,
                    "loudness_pass": True,
                    "occlusion_pass": True,
                    "phase_correlation": 0.9,
                    "trajectory_max_error_m": 0.01,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["WET_SOURCE_REJECT_POLICY"],
            status="blocked",
            acceptance="held",
        )

    if fixture_name == "unknown_room_blocked":
        unknown_room = deepcopy(room)
        unknown_room["authority"] = "unknown"
        trajectory = _trajectory_pair(
            start={
                "time_s": 0.0,
                "position_m": [0.0, 1.5, 1.6],
                "distance_m": 1.5,
                "azimuth_deg": 0.0,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
            end={
                "time_s": 1.5,
                "position_m": [0.2, 1.5, 1.6],
                "distance_m": 1.51,
                "azimuth_deg": 7.6,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
        )
        return build_manifest(
            root,
            render_id="fixture:unknown_room_blocked",
            room=unknown_room,
            sources=[
                _base_source(
                    registry,
                    event_id="fixture_event_unknown_room",
                    trajectory=trajectory,
                )
            ],
            validation=_validation_blocked(
                registry,
                overrides={
                    "rt60_pass": False,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["UNKNOWN_ROOM_AUTHORITY"],
            status="blocked",
            acceptance="held",
        )

    if fixture_name == "gate_failure_blocked":
        trajectory = _trajectory_pair(
            start={
                "time_s": 0.0,
                "position_m": [-0.5, 1.0, 1.6],
                "distance_m": 1.12,
                "azimuth_deg": -26.6,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.0,
                "visibility": "visible",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
            end={
                "time_s": 1.0,
                "position_m": [0.5, 1.0, 1.6],
                "distance_m": 1.12,
                "azimuth_deg": 26.6,
                "elevation_deg": 0.0,
                "occlusion_amount": 0.4,
                "visibility": "partial",
                "offscreen": False,
                "air_absorption_db_per_m": 0.01,
            },
        )
        return build_manifest(
            root,
            render_id="fixture:gate_failure_blocked",
            room=room,
            sources=[
                _base_source(
                    registry,
                    event_id="fixture_event_gate_failure",
                    trajectory=trajectory,
                )
            ],
            validation=_validation_blocked(
                registry,
                overrides={
                    "phase_pass": False,
                    "loudness_pass": False,
                    "clipping_pass": False,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + [
                "PHASE_INTEGRITY_FAILED",
                "LOUDNESS_INTEGRITY_FAILED",
                "CLIPPING_INTEGRITY_FAILED",
            ],
            status="blocked",
            acceptance="held",
        )

    raise SpatialAudioRendererError(f"unhandled_fixture:{fixture_name}")


def assert_schema_rejects(root: Path, manifest: dict[str, Any], *, expected_fragment: str) -> None:
    try:
        validate_manifest(root, manifest)
    except SpatialAudioRendererError as exc:
        if expected_fragment not in str(exc):
            raise SpatialAudioRendererError(
                f"unexpected_rejection:{exc}:expected:{expected_fragment}"
            ) from exc
        return
    raise SpatialAudioRendererError(f"expected_schema_rejection_missing:{expected_fragment}")


def adversarial_false_open_cases(root: Path) -> list[dict[str, Any]]:
    """Reproduce the seven planning-schema false-open probes against the strict contract."""
    baseline = extract_fixture_manifest(root, "moving_source_trajectory_pass")
    cases: list[dict[str, Any]] = []

    def probe(name: str, mutator) -> None:
        mutated = deepcopy(baseline)
        mutator(mutated)
        accepted = True
        error = ""
        try:
            validate_manifest(root, mutated)
        except SpatialAudioRendererError as exc:
            accepted = False
            error = str(exc)
        cases.append(
            {
                "name": name,
                "schema_accepted": accepted,
                "strict_expected_accepted": False,
                "false_open": accepted,
                "error": error,
            }
        )

    probe(
        "pass_with_all_validation_gates_false",
        lambda m: m["validation"].update(
            {
                "rt60_pass": False,
                "trajectory_pass": False,
                "phase_pass": False,
                "clipping_pass": False,
                "elevation_pass": False,
                "air_absorption_pass": False,
                "offscreen_continuity_pass": False,
                "loudness_pass": False,
                "occlusion_pass": False,
                "decision": "pass",
            }
        ),
    )
    probe(
        "trajectory_point_empty",
        lambda m: m["sources"][0].__setitem__("trajectory", [{}]),
    )
    probe(
        "listener_position_and_orientation_wrong_types",
        lambda m: (
            m["listener"].__setitem__("position_m", "origin"),
            m["listener"].__setitem__("orientation", "forward"),
        ),
    )
    probe(
        "source_reject_policy_but_pass",
        lambda m: (
            m["sources"][0].__setitem__("wet_source_policy", "reject"),
            m["validation"].__setitem__("decision", "pass"),
        ),
    )
    probe(
        "unknown_room_authority_but_pass",
        lambda m: (
            m["room"].__setitem__("authority", "unknown"),
            m["validation"].__setitem__("decision", "pass"),
        ),
    )
    probe(
        "renderer_and_output_required_fields_wrong_types",
        lambda m: (
            m["renderer"].__setitem__("configuration_sha256", 123),
            m["output"].__setitem__("channels", "stereo"),
            m["output"].__setitem__("sample_rate_hz", "24k"),
        ),
    )
    probe(
        "missing_elevation_air_absorption_offscreen_loudness_proof",
        lambda m: (
            m["validation"].pop("elevation_pass", None),
            m["validation"].pop("air_absorption_pass", None),
            m["validation"].pop("offscreen_continuity_pass", None),
            m["validation"].pop("loudness_pass", None),
        ),
    )
    return cases


def build_production_blocker_packet(root: Path) -> dict[str, Any]:
    row088 = evaluate_row088_admission(root)
    row091 = evaluate_row091_admission(root)
    row093 = evaluate_row093_admission(root)
    registry = load_registry(root)
    blocker_codes: list[str] = []
    for admission in (row088, row091, row093):
        blocker_codes.extend(admission["blocker_codes"])
    if not (
        row088["dependency_satisfied"]
        and row091["dependency_satisfied"]
        and row093["dependency_satisfied"]
    ):
        blocker_codes.append("ROW088_ROW091_ROW093_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "EVENT_DRIVEN_PRODUCTION_RENDERER_ABSENT",
        "EXPECTED_TRAJECTORY_METRIC_COMPARISON_ABSENT",
        "CALIBRATED_ELEVATION_OR_HRTF_PROOF_ABSENT",
        "GENUINE_ROW095_RUNTIME_PROOF_ABSENT",
        "INDEPENDENT_SPATIAL_AUDIO_REVIEW_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_manifests = [extract_fixture_manifest(root, name) for name in FIXTURE_NAMES]
    adversarial = adversarial_false_open_cases(root)
    false_open_count = sum(1 for case in adversarial if case["false_open"])
    if false_open_count != 0:
        raise SpatialAudioRendererError(
            f"strict_schema_still_false_open:{false_open_count}"
        )

    first = extract_fixture_manifest(root, "moving_source_trajectory_pass")
    second = extract_fixture_manifest(root, "moving_source_trajectory_pass")
    determinism_identical = first == second

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-095_spatial_audio_renderer",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "production_authority": False,
        "status": (
            "HOLD_ROW088_ROW091_ROW093_DEPENDENCIES_EVENT_DRIVEN_PRODUCTION_"
            "SPATIAL_RENDERER_RUNTIME_AND_AUDIO_QA_ABSENT"
        ),
        "required_capabilities": list(REQUIRED_CAPABILITIES),
        "required_gates": list(registry["required_gates"]),
        "planning_schema_boundary": {
            "planning_schema_path": "Plan/08_SCHEMAS/audio_spatial_render_manifest.schema.json",
            "strict_contract_schema_path": str(SCHEMA_PATH).replace("\\", "/"),
            "planning_schema_remains_non_authority": True,
            "strict_contract_closes_seven_false_open_cases": True,
        },
        "row088_admission": row088,
        "row091_admission": row091,
        "row093_admission": row093,
        "spatial_registry": {
            "path": str(REGISTRY_PATH).replace("\\", "/"),
            "registry_revision": registry["registry_revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, REGISTRY_PATH, "registry")),
        },
        "strict_schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(resolve_under(root, SCHEMA_PATH, "schema")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_production",
            "fixture_count": len(fixture_manifests),
            "determinism_identical_bytes": determinism_identical,
            "records": fixture_manifests,
            "determinism_note": (
                "Fixture manifests prove fail-closed trajectory, occlusion/"
                "offscreen, wet-source reject, unknown-room, and gate-failure "
                "contracts; they do not accept Row095 production completion or "
                "emit real spatial audio."
            ),
        },
        "adversarial_schema_probe": {
            "validator": "jsonschema.Draft202012Validator",
            "case_count": len(adversarial),
            "false_open_count": false_open_count,
            "cases": adversarial,
        },
        "blocker_codes": sorted(set(blocker_codes)),
        "decision": {
            "status": "blocked",
            "row095_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows088, 091, and 093; compile accepted source/listener "
                "trajectories and prepared clips into the strict Row095 manifest; "
                "apply calibrated pan/elevation, distance and air absorption, "
                "time-varying occlusion and offscreen continuity; measure phase, "
                "true peak, clipping, loudness, and trajectory error; preserve "
                "hash-bound replay; validate synthetic truth and genuine scene "
                "fixtures; perform independent spatial playback review; then "
                "replace this hold packet with production spatial evidence."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("production", "fixture"), default="production")
    parser.add_argument("--fixture", default="moving_source_trajectory_pass")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise SpatialAudioRendererError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_manifest(root, args.fixture)
    else:
        payload = build_production_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise SpatialAudioRendererError(
                "production_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise SpatialAudioRendererError("production_mode_must_not_claim_row_complete")
        if payload.get("production_authority") is True:
            raise SpatialAudioRendererError(
                "production_mode_must_not_claim_production_authority"
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
