#!/usr/bin/env python3
"""Build fail-closed Wave30/Row030 inputs from a verified genuine mux manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()
EVENT_SCHEMA = Path("Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json")
MIX_SCHEMA = Path("Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json")
TAXONOMY = Path("Plan/10_REGISTRIES/wave30_audio_event_taxonomy.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_under(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root") from exc
    return resolved


def verified_output(root: Path, manifest: dict[str, Any], name: str) -> tuple[Path, dict[str, Any]]:
    record = manifest.get("outputs", {}).get(name)
    if not isinstance(record, dict):
        raise ValueError(f"delivery manifest output missing: {name}")
    path = require_under(root, Path(str(record.get("path", ""))), f"outputs.{name}.path")
    if not path.is_file():
        raise ValueError(f"delivery output missing: {path}")
    if path.stat().st_size != record.get("bytes"):
        raise ValueError(f"delivery output byte mismatch: {name}")
    if sha256(path) != record.get("sha256"):
        raise ValueError(f"delivery output hash mismatch: {name}")
    return path, record


def wav_metrics(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        return {
            "duration_seconds": round(frames / rate, 6),
            "sample_rate_hz": rate,
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "frame_count": frames,
        }


def parse_loudnorm(stderr: str) -> dict[str, float]:
    candidates = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.DOTALL)
    if not candidates:
        raise ValueError("ffmpeg loudnorm JSON was not found")
    payload = json.loads(candidates[-1])
    return {
        "integrated_lufs": float(payload["input_i"]),
        "true_peak_dbtp": float(payload["input_tp"]),
    }


def measure_loudness(ffmpeg: str, wav_path: Path) -> dict[str, float]:
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-i",
            str(wav_path),
            "-af",
            "loudnorm=I=-18:TP=-1.5:LRA=7:print_format=json",
            "-f",
            "null",
            "-",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"ffmpeg loudness analysis failed: {completed.stderr[-400:]}")
    return parse_loudnorm(completed.stderr)


def artifact(path: Path, record: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": record["sha256"],
        "bytes": record["bytes"],
        **metrics,
    }


def build_inputs(
    *,
    root: Path,
    delivery_manifest_path: Path,
    output_dir: Path,
    ffmpeg: str = "ffmpeg",
    loudness_override: dict[str, float] | None = None,
    final_mux_override: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = require_under(root, delivery_manifest_path, "delivery_manifest")
    output_dir = require_under(root, output_dir, "output_dir")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("is_synthetic") is not False:
        raise ValueError("delivery manifest must describe non-synthetic input")
    if manifest.get("promotion_claimed") is not False:
        raise ValueError("delivery manifest unexpectedly claims promotion")

    source_video, source_video_record = verified_output(root, manifest, "strict_source_video")
    source_audio, source_audio_record = verified_output(root, manifest, "strict_sync_audio")
    if final_mux_override is None:
        final_mux, final_mux_record = verified_output(root, manifest, "strict_sync_mux")
    else:
        final_mux = require_under(root, final_mux_override, "final_mux_override")
        if not final_mux.is_file() or final_mux.stat().st_size < 1:
            raise ValueError(f"final mux override missing or empty: {final_mux}")
        final_mux_record = {
            "path": str(final_mux),
            "sha256": sha256(final_mux),
            "bytes": final_mux.stat().st_size,
            "role": "frame_aligned_strict_mux_override",
        }
    foley_stem, foley_record = verified_output(root, manifest, "foley_stem")
    ambience_stem, ambience_record = verified_output(root, manifest, "ambience_stem")
    source_audio_metrics = wav_metrics(source_audio)
    foley_metrics = wav_metrics(foley_stem)
    ambience_metrics = wav_metrics(ambience_stem)
    expected_audio_metrics = manifest.get("pcm_technical", {}).get("strict_sync_audio")
    expected_foley_metrics = manifest.get("pcm_technical", {}).get("foley_stem")
    expected_ambience_metrics = manifest.get("pcm_technical", {}).get("ambience_stem")
    if source_audio_metrics != expected_audio_metrics:
        raise ValueError("strict sync audio PCM metadata mismatch")
    if foley_metrics != expected_foley_metrics:
        raise ValueError("foley stem PCM metadata mismatch")
    if ambience_metrics != expected_ambience_metrics:
        raise ValueError("ambience stem PCM metadata mismatch")

    sync = manifest.get("sync")
    if not isinstance(sync, dict):
        raise ValueError("delivery manifest sync record missing")
    frame_rate = float(sync["video_frame_rate"])
    anchor_frame = int(sync["foley_anchor_frame"])
    anchor_seconds = float(sync["foley_anchor_seconds"])
    if frame_rate <= 0 or anchor_frame < 0 or anchor_seconds < 0:
        raise ValueError("invalid delivery sync anchor")
    if abs(anchor_seconds * frame_rate - anchor_frame) > 1.0:
        raise ValueError("delivery sync frame/time anchor mismatch")
    window_start = max(0, anchor_frame - 2)
    window_end = anchor_frame + 2

    taxonomy = root / TAXONOMY
    event_schema = json.loads((root / EVENT_SCHEMA).read_text(encoding="utf-8"))
    mix_schema = json.loads((root / MIX_SCHEMA).read_text(encoding="utf-8"))
    loudness = loudness_override or measure_loudness(ffmpeg, source_audio)
    run_id = str(manifest["run_id"])
    scene_id = str(manifest["scene_id"])
    shot_id = str(manifest["shot_id"])
    take_id = str(manifest["take_id"])

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        final_event_path = output_dir / "wave30_event_manifest.json"
        final_runtime_boundary_path = output_dir / "runtime_boundary_not_proof.json"
        final_review_boundary_path = output_dir / "audio_review_boundary_not_proof.json"
        runtime_boundary = {
            "classification": "BOUNDARY_NOT_PRODUCTION_RUNTIME_PROOF",
            "production_runtime_proof_present": False,
            "source_execution_record": str(manifest_path.parent / "execution_record.json"),
        }
        review_boundary = {
            "classification": "BOUNDARY_NOT_INDEPENDENT_PLAYBACK_REVIEW",
            "independent_playback_review_present": False,
        }
        write_json(temporary / final_runtime_boundary_path.name, runtime_boundary)
        write_json(temporary / final_review_boundary_path.name, review_boundary)

        event_id = "audio_evt_room_tone_001"
        event = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_event_manifest",
            "event_manifest_version": 1,
            "run_id": run_id,
            "scene_id": scene_id,
            "shot_id": shot_id,
            "is_synthetic": False,
            "production_proof": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "taxonomy_registry_path": str(taxonomy),
            "taxonomy_registry_sha256": sha256(taxonomy),
            "audio_event_count": 1,
            "required_lanes": ["ambience"],
            "audio_events": [
                {
                    "audio_event_id": event_id,
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "event_type": "room_tone",
                    "sync_class": "ambient_free",
                    "purpose": "Genuine ownerless room-tone layer carried by the strict mux",
                    "source_event_id": "delivery_manifest.outputs.ambience_stem",
                    "start_seconds": round(window_start / frame_rate, 6),
                    "end_seconds": round(window_end / frame_rate, 6),
                    "expected_video_frame_range": {
                        "start_frame": window_start,
                        "end_frame": window_end,
                        "frame_rate": frame_rate,
                    },
                    "qa_rules": ["full_duration_ambience_continuity", "contact_anchor_authority_not_claimed"],
                    "layer": "ambience",
                    "routing": {"lane": "ambience", "contact_anchor_excluded": True},
                    "subject_binding": {"binding_type": "none", "character_id": None, "object_id": None},
                    "artifact": artifact(ambience_stem, ambience_record, ambience_metrics),
                    "synthetic_state": {
                        "synthetic_origin": "deterministic_original_room_tone",
                        "production_proof_claimed": False,
                    },
                }
            ],
            "artifact_manifest": {
                "source_input_path": str(manifest_path),
                "source_input_sha256": sha256(manifest_path),
            },
            "av_sync_binding": {"frame_rate": frame_rate, "sync_scope": "event_level"},
        }
        Draft202012Validator(event_schema).validate(event)
        event_path = temporary / final_event_path.name
        write_json(event_path, event)

        event_binding = {"path": str(final_event_path), "sha256": sha256(event_path)}
        mix = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_mix_manifest",
            "mix_manifest_version": 1,
            "run_id": run_id,
            "mix_id": f"{run_id}_strict_sync_mix",
            "scene_id": scene_id,
            "shot_id": shot_id,
            "is_synthetic": False,
            "event_manifest_bindings": [event_binding],
            "mixdown_artifact": {
                "path": str(source_audio),
                "sha256": source_audio_record["sha256"],
                "bytes": source_audio_record["bytes"],
            },
            "mix_technical": {**source_audio_metrics, "channel_layout": "mono"},
            "mix_event_metadata": [
                {
                    "audio_event_id": event_id,
                    "gain_db": 0.0,
                    "pan": 0.0,
                    "spatial_position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "distance_meters": 0.0,
                }
            ],
            "mix_loudness": {
                "integrated_lufs": loudness["integrated_lufs"],
                "true_peak_dbtp": loudness["true_peak_dbtp"],
                "clipping_detected": loudness["true_peak_dbtp"] >= 0.0,
            },
            "measurement_methods": {
                "integrated_loudness": "ffmpeg_loudnorm_bs1770",
                "true_peak": "ffmpeg_loudnorm_bs1770",
                "certification_authority": False,
            },
            "dialogue_ducking": {"enabled": False, "duck_db": 0.0, "recovery_ms": 0},
            "av_sync_evidence": {
                "frame_rate": frame_rate,
                "start_frame": window_start,
                "end_frame": window_end,
                "frame_offset": 0,
            },
            "runtime_proof": {
                "proof_kind": "runtime",
                "path": str(final_runtime_boundary_path),
                "sha256": sha256(temporary / final_runtime_boundary_path.name),
            },
            "audio_review": {
                "proof_kind": "audio_review",
                "path": str(final_review_boundary_path),
                "sha256": sha256(temporary / final_review_boundary_path.name),
            },
            "production_state": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "promotion_decision": "block",
        }
        Draft202012Validator(mix_schema).validate(mix)
        write_json(temporary / "wave30_mix_manifest.json", mix)

        anchor = {
            "schema_name": "wave64_av_sync_anchor_measurement_proof",
            "proof_kind": "anchor_measurement",
            "engine": "deterministic_delivery_manifest_binding",
            "model": "wave64_genuine_audio_chain_anchor_metadata",
            "model_version": "1.0",
            "model_sha256": sha256(Path(__file__).resolve()),
            "authority_id": "codex_local_technical_capture_unapproved",
            "run_id": run_id,
            "scene_id": scene_id,
            "shot_id": shot_id,
            "take_id": take_id,
            "is_synthetic": False,
            "evidence_origin": "technical_capture",
            "source_video_sha256": source_video_record["sha256"],
            "source_audio_sha256": source_audio_record["sha256"],
            "mux_sha256": final_mux_record["sha256"],
            "anchors": [],
        }
        write_json(temporary / "anchor_measurement_proof.json", anchor)
        optional = temporary / "optional_proofs"
        optional.mkdir()
        summary = {
            "schema_version": "1.0",
            "classification": "GENUINE_AV_SYNC_TECHNICAL_INPUTS_BUILT_CONTACT_ANCHOR_AUTHORITY_BLOCKED",
            "result": "pass",
            "source_delivery_manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path)},
            "final_mux_override_used": final_mux_override is not None,
            "verified_artifacts": {
                "source_video_sha256": source_video_record["sha256"],
                "source_audio_sha256": source_audio_record["sha256"],
                "mux_sha256": final_mux_record["sha256"],
            },
            "anchor": {
                "recorded_timeline_marker_frame": anchor_frame,
                "recorded_timeline_marker_seconds": anchor_seconds,
                "window_start_frame": window_start,
                "window_end_frame": window_end,
                "certifying_anchor_emitted": False,
                "owner_claimed": False,
                "visual_contact_claimed": False,
            },
            "boundaries": {
                "measurement_producer_allowlisted": False,
                "ownerless_sync_anchor_allowed_by_schema": False,
                "trusted_contact_owner_proof_present": False,
                "independent_playback_review_present": False,
                "production_runtime_proof_present": False,
                "production_authority_present": False,
                "promotion_claimed": False,
            },
        }
        write_json(temporary / "build_manifest.json", summary)
        os.replace(temporary, output_dir)
        return summary
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delivery-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--final-mux-override")
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if root != CANONICAL_ROOT:
            raise ValueError(f"root must match canonical project root ({CANONICAL_ROOT})")
        result = build_inputs(
            root=root,
            delivery_manifest_path=Path(args.delivery_manifest),
            output_dir=Path(args.output_dir),
            ffmpeg=args.ffmpeg,
            final_mux_override=Path(args.final_mux_override) if args.final_mux_override else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
