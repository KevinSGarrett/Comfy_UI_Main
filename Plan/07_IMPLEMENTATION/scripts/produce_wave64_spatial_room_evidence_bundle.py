#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()
OPTIONAL_FILES = {
    "playback_proof_binding": "playback_proof.json",
    "runtime_proof_binding": "runtime_proof.json",
    "production_authority_bundle_binding": "production_authority_bundle.json",
}


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root") from exc
    return path


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    if path.stat().st_size < 1:
        raise ValueError(f"{label} must not be empty: {path}")


def file_binding(path: Path, *, include_bytes: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "sha256": sha256(path)}
    if include_bytes:
        result["bytes"] = path.stat().st_size
    return result


def parse_vector(raw: str, label: str) -> dict[str, float]:
    parts = raw.split(",")
    if len(parts) != 3:
        raise ValueError(f"{label} must be x,y,z")
    values = [float(part.strip()) for part in parts]
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{label} values must be finite")
    return dict(zip(("x", "y", "z"), values, strict=True))


def validate_identity(payload: dict[str, Any], label: str, identity: dict[str, Any]) -> None:
    for field in ("run_id", "scene_id", "shot_id", "take_id", "is_synthetic"):
        if field not in payload:
            raise ValueError(f"{label}.{field} missing")
        if payload[field] != identity[field]:
            raise ValueError(f"{label}.{field} mismatch")


def canonical_thresholds(gate_rules: dict[str, Any], room_manifest: dict[str, Any]) -> dict[str, float]:
    room_profile = room_manifest.get("room_profile_id")
    reverb_profile = room_manifest.get("reverb_profile")
    profile = next(
        (
            item
            for item in gate_rules["room_rules"]["profile_rules"]
            if item["room_profile_id"] == room_profile and item["reverb_profile"] == reverb_profile
        ),
        None,
    )
    if profile is None:
        raise ValueError("room profile and reverb pair is not present in canonical gate rules")
    spatial = gate_rules["spatial_rules"]
    room = gate_rules["room_rules"]
    ambience = gate_rules["ambience_rules"]
    mix = gate_rules["mix_rules"]
    return {
        "max_camera_listener_distance_delta": spatial["max_camera_listener_distance_delta"],
        "max_pan_error": spatial["max_pan_error"],
        "min_attenuation_ratio": spatial["min_attenuation_ratio"],
        "max_attenuation_ratio": spatial["max_attenuation_ratio"],
        "min_rt60_seconds": profile["rt60_seconds_range"][0],
        "max_rt60_seconds": profile["rt60_seconds_range"][1],
        "max_reverb_tail_error_seconds": room["max_reverb_tail_error_seconds"],
        "max_ambience_drift": ambience["max_continuity_drift"],
        "min_dialogue_to_ambience_db": mix["min_dialogue_to_ambience_db"],
        "max_clipping_ratio": mix["max_clipping_ratio"],
        "max_stereo_balance_delta": mix["max_stereo_balance_delta"],
        "max_duration_delta_seconds": mix["max_duration_delta_seconds"],
    }


def write_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def produce(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    requested_root = Path(args.root).resolve()
    if requested_root != CANONICAL_ROOT:
        raise ValueError(f"root must match canonical project root ({CANONICAL_ROOT})")
    root = CANONICAL_ROOT
    paths = {
        name: resolve_under(root, Path(getattr(args, name)), name)
        for name in (
            "spatial_mix",
            "room_acoustics",
            "dry_dialogue",
            "spatial_dialogue",
            "ambience_bed",
            "final_mix",
            "previous_ambience",
            "current_ambience",
            "optional_dir",
            "output",
        )
    }
    output = paths["output"]
    optional_dir = paths["optional_dir"]
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    if output == optional_dir or optional_dir in output.parents:
        raise ValueError("output must not be inside optional artifact directory")

    for name, path in paths.items():
        if name not in {"optional_dir", "output"}:
            require_file(path, name)
    if not optional_dir.is_dir():
        raise ValueError(f"optional_dir missing: {optional_dir}")
    if len({paths[name] for name in paths if name not in {"optional_dir", "output"}}) != 8:
        raise ValueError("all bound manifest and audio artifact paths must be distinct")

    spatial_manifest = load_json(paths["spatial_mix"])
    room_manifest = load_json(paths["room_acoustics"])
    if not isinstance(spatial_manifest, dict) or not isinstance(room_manifest, dict):
        raise ValueError("Wave31 manifests must contain JSON objects")

    identity = {
        "run_id": args.run_id.strip(),
        "scene_id": args.scene_id.strip(),
        "shot_id": args.shot_id.strip(),
        "take_id": args.take_id.strip(),
        "is_synthetic": not args.production_input,
    }
    if any(not identity[field] for field in ("run_id", "scene_id", "shot_id", "take_id")):
        raise ValueError("run, scene, shot, and take identifiers must be non-empty")
    validate_identity(spatial_manifest, "spatial_mix", identity)
    validate_identity(room_manifest, "room_acoustics", identity)

    gate_rules = load_json(root / "Plan/10_REGISTRIES/wave64_spatial_room_gate_rules.json")
    hard_cut_path = optional_dir / "hard_cut_contract.json"
    hard_cut_contract = load_json(hard_cut_path) if hard_cut_path.is_file() else None
    if hard_cut_contract is not None and not isinstance(hard_cut_contract, dict):
        raise ValueError("hard_cut_contract must contain a JSON object")

    optional_bindings: dict[str, dict[str, str] | None] = {}
    for field, filename in OPTIONAL_FILES.items():
        path = optional_dir / filename
        if path.is_file():
            require_file(path, field)
            if not isinstance(load_json(path), dict):
                raise ValueError(f"{field} must contain a JSON object")
            optional_bindings[field] = file_binding(path)
        else:
            optional_bindings[field] = None

    request = {
        "schema_name": "wave64_spatial_room_evidence_bundle",
        "bundle_version": 1,
        **identity,
        "evidence_origin": "technical_capture" if args.production_input else "synthetic_fixture",
        "listener_position": parse_vector(args.listener_position, "listener_position"),
        "camera_position": parse_vector(args.camera_position, "camera_position"),
        "camera_orientation": {
            "right_unit_vector": parse_vector(args.camera_right, "camera_right"),
            "forward_unit_vector": parse_vector(args.camera_forward, "camera_forward"),
        },
        "source_position": parse_vector(args.source_position, "source_position"),
        "wave31_spatial_mix_binding": file_binding(paths["spatial_mix"]),
        "wave31_room_acoustics_binding": file_binding(paths["room_acoustics"]),
        "audio_artifacts": {
            "dry_dialogue": file_binding(paths["dry_dialogue"], include_bytes=True),
            "spatial_dialogue": file_binding(paths["spatial_dialogue"], include_bytes=True),
            "ambience_bed": file_binding(paths["ambience_bed"], include_bytes=True),
            "final_mix": file_binding(paths["final_mix"], include_bytes=True),
        },
        "ambience_continuity_evidence": {
            "previous_segment": file_binding(paths["previous_ambience"], include_bytes=True),
            "current_segment": file_binding(paths["current_ambience"], include_bytes=True),
            "hard_cut_contract": hard_cut_contract,
        },
        **optional_bindings,
        "threshold_overrides": canonical_thresholds(gate_rules, room_manifest),
    }
    schema = load_json(root / "Plan/08_SCHEMAS/wave64_spatial_room_evidence_bundle.schema.json")
    Draft202012Validator(schema).validate(request)
    write_atomic(output, request)
    return output, request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spatial-mix", required=True)
    parser.add_argument("--room-acoustics", required=True)
    parser.add_argument("--dry-dialogue", required=True)
    parser.add_argument("--spatial-dialogue", required=True)
    parser.add_argument("--ambience-bed", required=True)
    parser.add_argument("--final-mix", required=True)
    parser.add_argument("--previous-ambience", required=True)
    parser.add_argument("--current-ambience", required=True)
    parser.add_argument("--optional-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--take-id", required=True)
    parser.add_argument("--listener-position", required=True)
    parser.add_argument("--camera-position", required=True)
    parser.add_argument("--camera-right", required=True)
    parser.add_argument("--camera-forward", required=True)
    parser.add_argument("--source-position", required=True)
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        output, request = produce(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": "pass",
                "output": str(output),
                "missing_optional_count": sum(request[field] is None for field in OPTIONAL_FILES),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
