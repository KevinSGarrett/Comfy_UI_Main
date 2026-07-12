#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()
OPTIONAL_FILES = {
    "playback_proof_binding": "playback_proof.json",
    "runtime_proof_binding": "runtime_proof.json",
    "production_certification_bundle_binding": "production_certification_bundle.json",
}
OPTIONAL_CONTRACTS = {
    "playback_proof_binding": ("wave64_av_sync_playback_proof", "av_sync_playback_review"),
    "runtime_proof_binding": ("wave64_production_runtime_proof", "production_runtime"),
    "production_certification_bundle_binding": (
        "wave64_av_sync_production_authority_bundle",
        "production_av_sync_authority",
    ),
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


def binding(path: Path, media_type: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "sha256": sha256(path)}
    if media_type is not None:
        result.update({"bytes": path.stat().st_size, "media_type": media_type})
    return result


def require_identity(payload: dict[str, Any], label: str, identity: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field not in payload:
            raise ValueError(f"{label}.{field} missing")
        if payload[field] != identity[field]:
            raise ValueError(f"{label}.{field} mismatch")


def require_hash_lineage(payload: dict[str, Any], label: str, expected: dict[str, str]) -> None:
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"{label}.{field} mismatch")


def write_atomic_no_clobber(path: Path, payload: dict[str, Any]) -> None:
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
    root = Path(args.root).resolve()
    if root != CANONICAL_ROOT:
        raise ValueError(f"root must match canonical project root ({CANONICAL_ROOT})")
    paths = {
        name: resolve_under(root, Path(getattr(args, name)), name)
        for name in (
            "source_video",
            "source_audio_mix",
            "final_mux",
            "wave30_event_manifest",
            "wave30_mix_manifest",
            "anchor_measurement_proof",
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
    if not optional_dir.is_dir():
        raise ValueError(f"optional_dir missing: {optional_dir}")
    required_names = tuple(name for name in paths if name not in {"optional_dir", "output"})
    for name in required_names:
        require_file(paths[name], name)
    if len({paths[name] for name in required_names}) != len(required_names):
        raise ValueError("all required artifacts and manifests must use distinct paths")

    event_manifest = load_json(paths["wave30_event_manifest"])
    mix_manifest = load_json(paths["wave30_mix_manifest"])
    anchor_proof = load_json(paths["anchor_measurement_proof"])
    if not all(isinstance(payload, dict) for payload in (event_manifest, mix_manifest, anchor_proof)):
        raise ValueError("event manifest, mix manifest, and anchor proof must contain JSON objects")

    identity = {
        "run_id": args.run_id.strip(),
        "scene_id": args.scene_id.strip(),
        "shot_id": args.shot_id.strip(),
        "take_id": args.take_id.strip(),
        "is_synthetic": not args.production_input,
        "evidence_origin": "technical_capture" if args.production_input else "synthetic_fixture",
    }
    if any(not identity[field] for field in ("run_id", "scene_id", "shot_id", "take_id")):
        raise ValueError("run, scene, shot, and take identifiers must be non-empty")
    manifest_fields = ("run_id", "scene_id", "shot_id", "is_synthetic")
    require_identity(event_manifest, "wave30_event_manifest", identity, manifest_fields)
    require_identity(mix_manifest, "wave30_mix_manifest", identity, manifest_fields)
    require_identity(
        anchor_proof,
        "anchor_measurement_proof",
        identity,
        ("run_id", "scene_id", "shot_id", "take_id", "is_synthetic", "evidence_origin"),
    )
    if anchor_proof.get("schema_name") != "wave64_av_sync_anchor_measurement_proof":
        raise ValueError("anchor_measurement_proof.schema_name mismatch")
    if anchor_proof.get("proof_kind") != "anchor_measurement":
        raise ValueError("anchor_measurement_proof.proof_kind mismatch")

    event_binding = binding(paths["wave30_event_manifest"])
    audio_binding = binding(paths["source_audio_mix"], "audio/wav")
    event_links = mix_manifest.get("event_manifest_bindings")
    if not isinstance(event_links, list) or len(event_links) != 1 or event_links[0] != event_binding:
        raise ValueError("wave30_mix_manifest event manifest binding mismatch")
    mixdown = mix_manifest.get("mixdown_artifact")
    expected_mixdown = {key: audio_binding[key] for key in ("path", "sha256", "bytes")}
    if mixdown != expected_mixdown:
        raise ValueError("wave30_mix_manifest mixdown artifact mismatch")

    lineage = {
        "source_video_sha256": sha256(paths["source_video"]),
        "source_audio_sha256": audio_binding["sha256"],
        "mux_sha256": sha256(paths["final_mux"]),
    }
    require_hash_lineage(anchor_proof, "anchor_measurement_proof", lineage)
    anchor_sha = sha256(paths["anchor_measurement_proof"])

    optional_bindings: dict[str, dict[str, str] | None] = {}
    optional_payloads: dict[str, dict[str, Any]] = {}
    for field, filename in OPTIONAL_FILES.items():
        path = optional_dir / filename
        if not path.is_file():
            optional_bindings[field] = None
            continue
        require_file(path, field)
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"{field} must contain a JSON object")
        expected_schema, expected_kind = OPTIONAL_CONTRACTS[field]
        if payload.get("schema_name") != expected_schema:
            raise ValueError(f"{field}.schema_name mismatch")
        if payload.get("proof_kind") != expected_kind:
            raise ValueError(f"{field}.proof_kind mismatch")
        require_identity(
            payload,
            field,
            identity,
            ("run_id", "scene_id", "shot_id", "take_id", "is_synthetic", "evidence_origin"),
        )
        require_hash_lineage(payload, field, lineage)
        optional_payloads[field] = payload
        optional_bindings[field] = binding(path)

    for field in ("playback_proof_binding", "runtime_proof_binding"):
        if field in optional_payloads and optional_payloads[field].get("measurement_proof_sha256") != anchor_sha:
            raise ValueError(f"{field}.measurement_proof_sha256 mismatch")
    if "production_certification_bundle_binding" in optional_payloads:
        bundle = optional_payloads["production_certification_bundle_binding"]
        if bundle.get("measurement_proof_sha256") != anchor_sha:
            raise ValueError("production_certification_bundle_binding.measurement_proof_sha256 mismatch")
        for field, hash_field in (
            ("playback_proof_binding", "playback_proof_sha256"),
            ("runtime_proof_binding", "runtime_proof_sha256"),
        ):
            if optional_bindings[field] is None:
                raise ValueError("production certification bundle requires playback and runtime proof files")
            if bundle.get(hash_field) != optional_bindings[field]["sha256"]:
                raise ValueError(f"production_certification_bundle_binding.{hash_field} mismatch")

    packet = {
        "schema_name": "wave64_av_sync_measurement_packet",
        "packet_version": 1,
        **identity,
        "source_video_artifact": binding(paths["source_video"], "video/x-matroska"),
        "source_audio_mix_artifact": audio_binding,
        "final_mux_artifact": binding(paths["final_mux"], "video/x-matroska"),
        "wave30_event_manifest_binding": event_binding,
        "wave30_mix_manifest_binding": binding(paths["wave30_mix_manifest"]),
        "observed_anchor_measurement_proof_binding": binding(paths["anchor_measurement_proof"]),
        **optional_bindings,
        "caller_claimed_overall_pass": False,
    }
    schema = load_json(root / "Plan/08_SCHEMAS/wave64_av_sync_measurement_packet.schema.json")
    Draft202012Validator(schema).validate(packet)
    write_atomic_no_clobber(output, packet)
    return output, packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-video", required=True)
    parser.add_argument("--source-audio-mix", required=True)
    parser.add_argument("--final-mux", required=True)
    parser.add_argument("--wave30-event-manifest", required=True)
    parser.add_argument("--wave30-mix-manifest", required=True)
    parser.add_argument("--anchor-measurement-proof", required=True)
    parser.add_argument("--optional-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--take-id", required=True)
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        output, packet = produce(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": "pass",
                "output": str(output),
                "missing_optional_count": sum(packet[field] is None for field in OPTIONAL_FILES),
                "caller_claimed_overall_pass": packet["caller_claimed_overall_pass"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
