#!/usr/bin/env python3
"""Fail-closed Wave64 Row096 room acoustic renderer contract slice.

Production RIR/early-reflection/RT60/convolution rendering refuses authority
without accepted Row076 reverb dryness, Row088 depth/camera geometry, Row089
visual material recognition, and Row095 spatial renderer prerequisites.
Fixture mode may emit deterministic schema-validated synthetic manifests and
hold evidence without granting production, runtime, or row completion authority.
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
    "Plan/08_SCHEMAS/wave64_row096_room_acoustic_render_manifest.schema.json"
)
REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row096_room_acoustic_renderer_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-096_room_acoustic_renderer.json"
)
ROW076_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
)
ROW088_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-088_DEPTH_CAMERA_SOURCE_POSITION_CURRENT_DELTA_20260719.json"
)
ROW089_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-089_VISUAL_MATERIAL_RECOGNITION_CURRENT_DELTA_20260719.json"
)
ROW095_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-095_SPATIAL_AUDIO_RENDERER_CURRENT_DELTA_20260719.json"
)

COMPILER_REVISION = "wave64_row096_room_acoustic_renderer_compiler_v0.1.0"
REGISTRY_REVISION = "wave64_row096_room_acoustic_renderer_registry_v0.1.0"
TRACKER_ID = "TRK-W64-096"
ITEM_ID = "ITEM-W64-096"
SCHEMA_VERSION = "1.0.0"

FIXTURE_NAMES = (
    "measured_rir_convolution_pass",
    "early_reflection_rt60_pass",
    "reject_wet_source_blocked",
    "unknown_room_geometry_blocked",
    "gate_failure_blocked",
)

REQUIRED_GATES = (
    "room_geometry",
    "material_absorption",
    "rir",
    "early_reflections",
    "rt60",
    "wet_source_guard",
)


class RoomAcousticRendererError(ValueError):
    """Raised when Row096 room-acoustic compilation violates fail-closed authority."""


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
        raise RoomAcousticRendererError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row096_fixture:{label}".encode("utf-8"))


def load_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, REGISTRY_PATH, "registry")
    payload = load_json(path)
    if payload.get("registry_revision") != REGISTRY_REVISION:
        raise RoomAcousticRendererError("registry_revision_mismatch")
    if payload.get("compiler_revision") != COMPILER_REVISION:
        raise RoomAcousticRendererError("compiler_revision_mismatch")
    gates = payload.get("required_gates")
    if not isinstance(gates, list) or tuple(gates) != REQUIRED_GATES:
        raise RoomAcousticRendererError("required_gates_mismatch")
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
            "status": "",
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": "0" * 64,
            "bytes": 0,
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
            "row076_acceptance",
            "row088_acceptance",
            "row089_acceptance",
            "row095_acceptance",
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


def evaluate_row076_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW076_DELTA,
        tracker_id="TRK-W64-076",
        blocker_code="ROW076_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW076_DELTA_ABSENT",
    )


def evaluate_row088_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW088_DELTA,
        tracker_id="TRK-W64-088",
        blocker_code="ROW088_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW088_DELTA_ABSENT",
    )


def evaluate_row089_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW089_DELTA,
        tracker_id="TRK-W64-089",
        blocker_code="ROW089_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW089_DELTA_ABSENT",
    )


def evaluate_row095_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW095_DELTA,
        tracker_id="TRK-W64-095",
        blocker_code="ROW095_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW095_DELTA_ABSENT",
    )


def evaluate_all_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "TRK-W64-076": evaluate_row076_admission(root),
        "TRK-W64-088": evaluate_row088_admission(root),
        "TRK-W64-089": evaluate_row089_admission(root),
        "TRK-W64-095": evaluate_row095_admission(root),
    }


def validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RoomAcousticRendererError(
            f"schema_validation_failed:{location}:{first.message}"
        )
    if manifest.get("production_authority") is True:
        raise RoomAcousticRendererError("production_authority_forbidden_in_contract_slice")
    if manifest.get("decision", {}).get("promotion_eligible") is True:
        raise RoomAcousticRendererError("promotion_eligible_forbidden_in_contract_slice")
    if manifest.get("is_synthetic") is True and manifest.get("decision", {}).get(
        "product_completion"
    ):
        raise RoomAcousticRendererError("synthetic_product_completion_forbidden")
    if (
        manifest.get("wet_source", {}).get("policy") == "reject"
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise RoomAcousticRendererError("reject_wet_source_cannot_pass")
    if (
        manifest.get("room", {}).get("authority") == "unknown"
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise RoomAcousticRendererError("unknown_room_cannot_pass")


def _output_block(
    registry: dict[str, Any],
    *,
    seed: str,
    measured_rt60: float,
) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "path": f"fixtures/row096/{seed}.wav",
        "sha256": _stable_hash(f"wav:{seed}"),
        "canonical_pcm_sha256": _stable_hash(f"pcm:{seed}"),
        "sample_rate_hz": int(contract["sample_rate_hz"]),
        "channels": int(contract["channels"]),
        "duration_seconds": 2.8,
        "peak_absolute": 0.38,
        "true_peak_dbfs": -3.8,
        "integrated_loudness_lufs": float(contract["integrated_loudness_lufs_target"]),
        "measured_rt60_seconds": float(measured_rt60),
    }


def _rir_block(registry: dict[str, Any], *, seed: str) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "selection_mode": contract["rir_selection_mode"],
        "rir_asset_id": f"fixture:rir:{seed}",
        "rir_sha256": _stable_hash(f"rir:{seed}"),
        "sample_rate_hz": int(contract["sample_rate_hz"]),
        "channels": int(contract["channels"]),
        "duration_seconds": 1.2,
    }


def _early_reflections_block(
    registry: dict[str, Any],
    *,
    reflection_count: int,
    first_onset_ms: float,
    energy_ratio: float,
) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "model": contract["early_reflection_model"],
        "reflection_count": int(reflection_count),
        "first_onset_ms": float(first_onset_ms),
        "energy_ratio": float(energy_ratio),
    }


def _convolution_block(registry: dict[str, Any]) -> dict[str, Any]:
    contract = registry["fixture_render_contract"]
    return {
        "mode": contract["convolution_mode"],
        "dry_gain": 0.85,
        "wet_gain": 0.35,
        "latency_samples": 128,
        "deterministic": True,
    }


def _wet_source_block(
    *,
    policy: str = "dry_render",
    source_was_wet: bool = False,
    guard_triggered: bool = False,
) -> dict[str, Any]:
    return {
        "policy": policy,
        "source_was_wet": source_was_wet,
        "guard_triggered": guard_triggered,
    }


def _validation_pass(registry: dict[str, Any], *, measured_rt60: float) -> dict[str, Any]:
    target = float(registry["room_fixture"]["target_rt60_seconds"])
    return {
        "room_geometry_pass": True,
        "material_absorption_pass": True,
        "rir_pass": True,
        "early_reflections_pass": True,
        "rt60_pass": True,
        "wet_source_guard_pass": True,
        "measured_rt60_seconds": float(measured_rt60),
        "rt60_error_seconds": round(abs(measured_rt60 - target), 6),
        "early_reflection_count": 12,
        "decision": "pass",
    }


def _validation_blocked(
    registry: dict[str, Any],
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = float(registry["room_fixture"]["target_rt60_seconds"])
    payload = {
        "room_geometry_pass": False,
        "material_absorption_pass": False,
        "rir_pass": False,
        "early_reflections_pass": False,
        "rt60_pass": False,
        "wet_source_guard_pass": False,
        "measured_rt60_seconds": target,
        "rt60_error_seconds": 0.25,
        "early_reflection_count": 0,
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
    source_listener: dict[str, Any],
    rir: dict[str, Any],
    early_reflections: dict[str, Any],
    convolution: dict[str, Any],
    wet_source: dict[str, Any],
    output: dict[str, Any],
    validation: dict[str, Any],
    blocker_codes: list[str],
    status: str,
    acceptance: str,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "render_id": render_id,
        "reverb_dryness_authority_sha256": _stable_hash("reverb_dryness"),
        "depth_camera_authority_sha256": _stable_hash("depth_camera"),
        "visual_material_authority_sha256": _stable_hash("visual_material"),
        "spatial_renderer_authority_sha256": _stable_hash("spatial_renderer"),
        "room": room,
        "source_listener": source_listener,
        "rir": rir,
        "early_reflections": early_reflections,
        "convolution": convolution,
        "wet_source": wet_source,
        "output": output,
        "validation": validation,
        "is_synthetic": True,
        "production_authority": False,
        "decision": {
            "status": status,
            "row096_acceptance": acceptance,
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
        raise RoomAcousticRendererError(f"unknown_fixture:{fixture_name}")
    registry = load_registry(root)
    room = deepcopy(registry["room_fixture"])
    source_listener = deepcopy(registry["source_listener_fixture"])
    contract = registry["fixture_render_contract"]
    common_blockers = [
        "PRODUCTION_AUTHORITY_NOT_GRANTED",
        "ROW076_ROW088_ROW089_ROW095_DEPENDENCIES_NOT_ACCEPTED",
    ]
    target_rt60 = float(room["target_rt60_seconds"])

    if fixture_name == "measured_rir_convolution_pass":
        measured = target_rt60 + 0.01
        return build_manifest(
            root,
            render_id="fixture:measured_rir_convolution_pass",
            room=room,
            source_listener=source_listener,
            rir=_rir_block(registry, seed="measured_rir_convolution_pass"),
            early_reflections=_early_reflections_block(
                registry,
                reflection_count=14,
                first_onset_ms=8.5,
                energy_ratio=0.28,
            ),
            convolution=_convolution_block(registry),
            wet_source=_wet_source_block(),
            output=_output_block(
                registry, seed="measured_rir_convolution_pass", measured_rt60=measured
            ),
            validation=_validation_pass(registry, measured_rt60=measured),
            blocker_codes=common_blockers,
            status="fixture_ok",
            acceptance="fixture_only",
        )

    if fixture_name == "early_reflection_rt60_pass":
        measured = target_rt60 - 0.02
        return build_manifest(
            root,
            render_id="fixture:early_reflection_rt60_pass",
            room=room,
            source_listener=source_listener,
            rir=_rir_block(registry, seed="early_reflection_rt60_pass"),
            early_reflections=_early_reflections_block(
                registry,
                reflection_count=int(contract["early_reflection_count_min"]) + 4,
                first_onset_ms=12.0,
                energy_ratio=0.33,
            ),
            convolution=_convolution_block(registry),
            wet_source=_wet_source_block(),
            output=_output_block(
                registry, seed="early_reflection_rt60_pass", measured_rt60=measured
            ),
            validation=_validation_pass(registry, measured_rt60=measured),
            blocker_codes=common_blockers,
            status="fixture_ok",
            acceptance="fixture_only",
        )

    if fixture_name == "reject_wet_source_blocked":
        return build_manifest(
            root,
            render_id="fixture:reject_wet_source_blocked",
            room=room,
            source_listener=source_listener,
            rir=_rir_block(registry, seed="reject_wet_source_blocked"),
            early_reflections=_early_reflections_block(
                registry,
                reflection_count=10,
                first_onset_ms=9.0,
                energy_ratio=0.25,
            ),
            convolution=_convolution_block(registry),
            wet_source=_wet_source_block(
                policy="reject",
                source_was_wet=True,
                guard_triggered=True,
            ),
            output=_output_block(
                registry, seed="reject_wet_source_blocked", measured_rt60=target_rt60
            ),
            validation=_validation_blocked(
                registry,
                overrides={
                    "room_geometry_pass": True,
                    "material_absorption_pass": True,
                    "rir_pass": True,
                    "early_reflections_pass": True,
                    "rt60_pass": True,
                    "wet_source_guard_pass": False,
                    "measured_rt60_seconds": target_rt60,
                    "rt60_error_seconds": 0.0,
                    "early_reflection_count": 10,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["WET_SOURCE_REJECT_POLICY"],
            status="blocked",
            acceptance="held",
        )

    if fixture_name == "unknown_room_geometry_blocked":
        unknown_room = deepcopy(room)
        unknown_room["authority"] = "unknown"
        unknown_room["material_absorption_coefficients"] = {
            "floor": 0.0,
            "walls": 0.0,
            "ceiling": 0.0,
        }
        return build_manifest(
            root,
            render_id="fixture:unknown_room_geometry_blocked",
            room=unknown_room,
            source_listener=source_listener,
            rir=_rir_block(registry, seed="unknown_room_geometry_blocked"),
            early_reflections=_early_reflections_block(
                registry,
                reflection_count=0,
                first_onset_ms=0.0,
                energy_ratio=0.0,
            ),
            convolution=_convolution_block(registry),
            wet_source=_wet_source_block(),
            output=_output_block(
                registry,
                seed="unknown_room_geometry_blocked",
                measured_rt60=target_rt60 + 0.4,
            ),
            validation=_validation_blocked(
                registry,
                overrides={
                    "room_geometry_pass": False,
                    "material_absorption_pass": False,
                    "rir_pass": False,
                    "early_reflections_pass": False,
                    "rt60_pass": False,
                    "wet_source_guard_pass": True,
                    "measured_rt60_seconds": target_rt60 + 0.4,
                    "rt60_error_seconds": 0.4,
                    "early_reflection_count": 0,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + ["UNKNOWN_ROOM_AUTHORITY", "MATERIAL_ABSORPTION_MISSING"],
            status="blocked",
            acceptance="held",
        )

    if fixture_name == "gate_failure_blocked":
        measured = target_rt60 + 0.22
        return build_manifest(
            root,
            render_id="fixture:gate_failure_blocked",
            room=room,
            source_listener=source_listener,
            rir=_rir_block(registry, seed="gate_failure_blocked"),
            early_reflections=_early_reflections_block(
                registry,
                reflection_count=1,
                first_onset_ms=120.0,
                energy_ratio=0.05,
            ),
            convolution=_convolution_block(registry),
            wet_source=_wet_source_block(),
            output=_output_block(
                registry, seed="gate_failure_blocked", measured_rt60=measured
            ),
            validation=_validation_blocked(
                registry,
                overrides={
                    "room_geometry_pass": True,
                    "material_absorption_pass": True,
                    "rir_pass": False,
                    "early_reflections_pass": False,
                    "rt60_pass": False,
                    "wet_source_guard_pass": True,
                    "measured_rt60_seconds": measured,
                    "rt60_error_seconds": 0.22,
                    "early_reflection_count": 1,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + [
                "RIR_SELECTION_FAILED",
                "EARLY_REFLECTION_TOLERANCE_FAILED",
                "RT60_TOLERANCE_FAILED",
            ],
            status="blocked",
            acceptance="held",
        )

    raise RoomAcousticRendererError(f"unhandled_fixture:{fixture_name}")


def adversarial_false_open_cases(root: Path) -> list[dict[str, Any]]:
    """Probe strict schema against false-open mutations that must remain rejected."""
    baseline = extract_fixture_manifest(root, "measured_rir_convolution_pass")
    cases: list[dict[str, Any]] = []

    def probe(name: str, mutator) -> None:
        mutated = deepcopy(baseline)
        mutator(mutated)
        accepted = True
        error = ""
        try:
            validate_manifest(root, mutated)
        except RoomAcousticRendererError as exc:
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
        "pass_with_all_room_gates_false",
        lambda m: m["validation"].update(
            {
                "room_geometry_pass": False,
                "material_absorption_pass": False,
                "rir_pass": False,
                "early_reflections_pass": False,
                "rt60_pass": False,
                "wet_source_guard_pass": False,
                "decision": "pass",
            }
        ),
    )
    probe(
        "reject_wet_source_but_pass",
        lambda m: (
            m["wet_source"].__setitem__("policy", "reject"),
            m["wet_source"].__setitem__("source_was_wet", True),
            m["wet_source"].__setitem__("guard_triggered", True),
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
        "missing_material_absorption_coefficients",
        lambda m: m["room"].pop("material_absorption_coefficients", None),
    )
    probe(
        "production_authority_true_on_synthetic",
        lambda m: (
            m.__setitem__("production_authority", True),
            m["decision"].update(
                {
                    "status": "accepted",
                    "row096_acceptance": "accepted",
                    "product_completion": True,
                    "runtime_completion": True,
                }
            ),
        ),
    )
    probe(
        "rir_sha256_wrong_type",
        lambda m: m["rir"].__setitem__("rir_sha256", 123),
    )
    probe(
        "missing_early_reflections_and_rt60_proof",
        lambda m: (
            m["validation"].pop("early_reflections_pass", None),
            m["validation"].pop("rt60_pass", None),
        ),
    )
    return cases


def build_production_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    registry = load_registry(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW076_ROW088_ROW089_ROW095_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "EVENT_DRIVEN_ROOM_ACOUSTIC_RUNTIME_ABSENT",
        "MEASURED_RIR_SELECTION_OR_SYNTHESIS_ABSENT",
        "EARLY_REFLECTION_RT60_TOLERANCE_PROOF_ABSENT",
        "DRY_SOURCE_CONVOLUTION_RUNTIME_ABSENT",
        "GENUINE_ROW096_RUNTIME_PROOF_ABSENT",
        "INDEPENDENT_ROOM_ACOUSTIC_AUDIO_REVIEW_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_manifests = [extract_fixture_manifest(root, name) for name in FIXTURE_NAMES]
    adversarial = adversarial_false_open_cases(root)
    false_open_count = sum(1 for case in adversarial if case["false_open"])
    if false_open_count != 0:
        raise RoomAcousticRendererError(
            f"strict_schema_still_false_open:{false_open_count}"
        )

    first = extract_fixture_manifest(root, "measured_rir_convolution_pass")
    second = extract_fixture_manifest(root, "measured_rir_convolution_pass")
    determinism_identical = first == second

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-096_room_acoustic_renderer",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "production_authority": False,
        "status": (
            "HOLD_ROW076_ROW088_ROW089_ROW095_DEPENDENCIES_EVENT_DRIVEN_"
            "ROOM_ACOUSTIC_RUNTIME_AND_AUDIO_QA_ABSENT"
        ),
        "required_gates": list(REQUIRED_GATES),
        "planning_schema_boundary": {
            "planning_schema_path": "Plan/08_SCHEMAS/wave31_room_acoustics.schema.json",
            "strict_contract_schema_path": str(SCHEMA_PATH).replace("\\", "/"),
            "planning_schema_remains_non_authority": True,
            "spatial_room_evaluator_reuse_does_not_grant_row096": True,
            "strict_contract_closes_seven_false_open_cases": True,
        },
        "dependency_admissions": admissions,
        "room_acoustic_registry": {
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
                "Fixture manifests prove fail-closed RIR/convolution, early-"
                "reflection/RT60, wet-source reject, unknown-room geometry, and "
                "gate-failure contracts; they do not accept Row096 production "
                "completion or emit real convolved audio."
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
            "row096_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows076, 088, 089, and 095; bind measured/registered room "
                "geometry and material absorption into RIR selection or synthesis; "
                "convolve dry sources with early-reflection and RT60-tolerant "
                "impulse responses under wet-source guard; measure output RT60 and "
                "early reflections; preserve hash-bound replay; validate synthetic "
                "truth and genuine scene fixtures; perform independent room-acoustic "
                "audio review; then replace this hold packet with production "
                "Row096 evidence."
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
    parser.add_argument("--fixture", default="measured_rir_convolution_pass")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise RoomAcousticRendererError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_manifest(root, args.fixture)
    else:
        payload = build_production_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise RoomAcousticRendererError(
                "production_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise RoomAcousticRendererError("production_mode_must_not_claim_row_complete")
        if payload.get("production_authority") is True:
            raise RoomAcousticRendererError(
                "production_mode_must_not_claim_production_authority"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "row_complete": payload.get("row_complete", False),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
