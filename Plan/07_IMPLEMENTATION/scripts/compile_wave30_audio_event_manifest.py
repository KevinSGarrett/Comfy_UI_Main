#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
import wave
from pathlib import Path
from typing import Any

EVENT_TYPES_REQUIRING_CHARACTER = {"dialogue", "voice_reaction", "breath"}
EVENT_TYPES_REQUIRING_SUBJECT = {
    "body_foley",
    "clothing_foley",
    "prop_foley",
    "furniture_foley",
    "impact",
    "action_sfx",
    "transition_sfx",
}
ALLOWED_TOP_LEVEL_FIELDS = {
    "run_id",
    "scene_id",
    "shot_id",
    "is_synthetic",
    "audio_events",
    "required_lanes",
    "av_frame_rate",
}
ALLOWED_EVENT_FIELDS = {
    "audio_event_id",
    "scene_id",
    "shot_id",
    "event_type",
    "sync_class",
    "source_event_id",
    "purpose",
    "start_seconds",
    "end_seconds",
    "expected_video_frame_range",
    "qa_rules",
    "layer",
    "routing",
    "subject_binding",
    "artifact",
}


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _assert_keys_exact(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(unknown)}")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError(f"{label} must be finite")
    return as_float


def _validate_subject_binding(event_type: str, subject_binding: Any, index: int) -> dict[str, Any]:
    if not isinstance(subject_binding, dict):
        raise ValueError(f"audio_events[{index}].subject_binding must be an object")
    binding_type = _expect_non_empty_string(
        subject_binding.get("binding_type"), f"audio_events[{index}].subject_binding.binding_type"
    )
    character_id = subject_binding.get("character_id")
    object_id = subject_binding.get("object_id")

    if event_type in EVENT_TYPES_REQUIRING_CHARACTER:
        if binding_type != "character":
            raise ValueError(
                f"audio_events[{index}] event_type {event_type} requires subject_binding.binding_type=character"
            )
        _expect_non_empty_string(character_id, f"audio_events[{index}].subject_binding.character_id")
    elif event_type in EVENT_TYPES_REQUIRING_SUBJECT:
        if binding_type not in {"character", "object"}:
            raise ValueError(
                f"audio_events[{index}] event_type {event_type} requires subject_binding.binding_type=character|object"
            )
        if binding_type == "character":
            _expect_non_empty_string(character_id, f"audio_events[{index}].subject_binding.character_id")
        if binding_type == "object":
            _expect_non_empty_string(object_id, f"audio_events[{index}].subject_binding.object_id")
    else:
        if binding_type not in {"environment", "none"}:
            raise ValueError(
                f"audio_events[{index}] event_type {event_type} allows only environment/none subject binding"
            )
    return {
        "binding_type": binding_type,
        "character_id": character_id if isinstance(character_id, str) and character_id.strip() else None,
        "object_id": object_id if isinstance(object_id, str) and object_id.strip() else None,
    }


def _read_wav_metrics(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = int(handle.getnchannels())
        sample_rate = int(handle.getframerate())
        sample_width = int(handle.getsampwidth())
        frame_count = int(handle.getnframes())
        all_frames = handle.readframes(frame_count)
        expected_data_bytes = frame_count * channels * sample_width
        if len(all_frames) != expected_data_bytes:
            raise ValueError(
                "decoded WAV frame payload length mismatch "
                f"({len(all_frames)} != {expected_data_bytes})"
            )
    if channels <= 0 or sample_rate <= 0 or sample_width <= 0 or frame_count <= 0:
        raise ValueError("WAV stream metrics must be positive")
    duration_seconds = frame_count / float(sample_rate)
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": round(duration_seconds, 6),
    }


def _compile_event(
    raw_event: dict[str, Any],
    index: int,
    manifest_scene_id: str,
    manifest_shot_id: str,
    taxonomy_event_types: set[str],
    artifact_base_dir: Path,
) -> dict[str, Any]:
    _assert_keys_exact(raw_event, ALLOWED_EVENT_FIELDS, f"audio_events[{index}]")
    event_type = _expect_non_empty_string(raw_event.get("event_type"), f"audio_events[{index}].event_type")
    if event_type not in taxonomy_event_types:
        raise ValueError(
            f"audio_events[{index}].event_type={event_type!r} is not in taxonomy registry"
        )
    scene_id = _expect_non_empty_string(raw_event.get("scene_id"), f"audio_events[{index}].scene_id")
    shot_id = _expect_non_empty_string(raw_event.get("shot_id"), f"audio_events[{index}].shot_id")
    if scene_id != manifest_scene_id or shot_id != manifest_shot_id:
        raise ValueError(
            f"audio_events[{index}] scene/shot mismatch against packet ({scene_id}/{shot_id})"
        )

    start_seconds = _expect_finite_number(raw_event.get("start_seconds"), f"audio_events[{index}].start_seconds")
    end_seconds = _expect_finite_number(raw_event.get("end_seconds"), f"audio_events[{index}].end_seconds")
    if end_seconds <= start_seconds:
        raise ValueError(f"audio_events[{index}] requires end_seconds > start_seconds")

    expected_video_frame_range = raw_event.get("expected_video_frame_range")
    if not isinstance(expected_video_frame_range, dict):
        raise ValueError(f"audio_events[{index}].expected_video_frame_range must be an object")
    start_frame = expected_video_frame_range.get("start_frame")
    end_frame = expected_video_frame_range.get("end_frame")
    frame_rate = _expect_finite_number(
        expected_video_frame_range.get("frame_rate"), f"audio_events[{index}].expected_video_frame_range.frame_rate"
    )
    if (
        not isinstance(start_frame, int)
        or isinstance(start_frame, bool)
        or not isinstance(end_frame, int)
        or isinstance(end_frame, bool)
        or start_frame < 0
        or end_frame < start_frame
    ):
        raise ValueError(
            f"audio_events[{index}].expected_video_frame_range requires non-negative integer start/end with end>=start"
        )

    artifact = raw_event.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError(f"audio_events[{index}].artifact must be an object")
    artifact_path_raw = Path(
        _expect_non_empty_string(artifact.get("path"), f"audio_events[{index}].artifact.path")
    )
    artifact_path = artifact_path_raw if artifact_path_raw.is_absolute() else (artifact_base_dir / artifact_path_raw).resolve()
    artifact_sha = _expect_non_empty_string(artifact.get("sha256"), f"audio_events[{index}].artifact.sha256")
    artifact_bytes = artifact.get("bytes")
    if not isinstance(artifact_bytes, int) or isinstance(artifact_bytes, bool) or artifact_bytes <= 0:
        raise ValueError(f"audio_events[{index}].artifact.bytes must be a positive integer")
    if artifact_path.suffix.lower() != ".wav":
        raise ValueError(f"audio_events[{index}] artifact path must reference a .wav file")
    if not artifact_path.is_file():
        raise ValueError(f"audio_events[{index}] artifact path does not exist: {artifact_path}")
    observed_bytes = artifact_path.stat().st_size
    if observed_bytes != artifact_bytes:
        raise ValueError(
            f"audio_events[{index}] artifact byte mismatch ({artifact_bytes} != {observed_bytes})"
        )
    observed_sha = _sha256_of(artifact_path)
    if observed_sha != artifact_sha:
        raise ValueError(
            f"audio_events[{index}] artifact sha256 mismatch ({artifact_sha} != {observed_sha})"
        )
    wav_metrics = _read_wav_metrics(artifact_path)
    event_duration = end_seconds - start_seconds
    if abs(event_duration - wav_metrics["duration_seconds"]) > 0.05:
        raise ValueError(
            f"audio_events[{index}] duration mismatch against WAV metrics "
            f"({event_duration:.6f} != {wav_metrics['duration_seconds']:.6f})"
        )

    expected_frame_count = int(round(event_duration * frame_rate))
    observed_frame_count = int(end_frame - start_frame)
    if abs(expected_frame_count - observed_frame_count) > 1:
        raise ValueError(
            f"audio_events[{index}] AV frame range mismatch (expected~{expected_frame_count}, got {observed_frame_count})"
        )

    qa_rules = raw_event.get("qa_rules")
    if not isinstance(qa_rules, list) or not qa_rules:
        raise ValueError(f"audio_events[{index}].qa_rules must be a non-empty list")
    normalized_qa_rules: list[str] = []
    for qa_idx, rule in enumerate(qa_rules):
        normalized_qa_rules.append(
            _expect_non_empty_string(rule, f"audio_events[{index}].qa_rules[{qa_idx}]")
        )

    layer = _expect_non_empty_string(raw_event.get("layer"), f"audio_events[{index}].layer")
    routing = raw_event.get("routing")
    if not isinstance(routing, dict) or not routing:
        raise ValueError(f"audio_events[{index}].routing must be a non-empty object")

    return {
        "audio_event_id": _expect_non_empty_string(raw_event.get("audio_event_id"), f"audio_events[{index}].audio_event_id"),
        "scene_id": scene_id,
        "shot_id": shot_id,
        "event_type": event_type,
        "sync_class": _expect_non_empty_string(raw_event.get("sync_class"), f"audio_events[{index}].sync_class"),
        "purpose": _expect_non_empty_string(raw_event.get("purpose"), f"audio_events[{index}].purpose"),
        "source_event_id": _expect_non_empty_string(
            raw_event.get("source_event_id"), f"audio_events[{index}].source_event_id"
        ),
        "start_seconds": round(start_seconds, 6),
        "end_seconds": round(end_seconds, 6),
        "expected_video_frame_range": {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frame_rate": frame_rate,
        },
        "qa_rules": normalized_qa_rules,
        "layer": layer,
        "routing": routing,
        "subject_binding": _validate_subject_binding(event_type, raw_event.get("subject_binding"), index),
        "artifact": {
            "path": str(artifact_path),
            "sha256": observed_sha,
            "bytes": observed_bytes,
            "duration_seconds": wav_metrics["duration_seconds"],
            "sample_rate_hz": wav_metrics["sample_rate_hz"],
            "channels": wav_metrics["channels"],
            "sample_width_bytes": wav_metrics["sample_width_bytes"],
            "frame_count": wav_metrics["frame_count"],
        },
        "synthetic_state": {
            "synthetic_origin": "offline_structural_validation",
            "production_proof_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    root = Path(args.root).resolve()
    taxonomy_path = root / "Plan/10_REGISTRIES/wave30_audio_event_taxonomy.json"

    try:
        src = _load_json(input_path)
        taxonomy = _load_json(taxonomy_path)
        taxonomy_event_types = {
            _expect_non_empty_string(value, "taxonomy.event_types[]")
            for value in taxonomy.get("event_types", [])
        }
        if not taxonomy_event_types:
            raise ValueError("taxonomy registry has no event_types")
        if not isinstance(src, dict):
            raise ValueError("input must be an object")
        if "audio_events" in src:
            _assert_keys_exact(src, ALLOWED_TOP_LEVEL_FIELDS, "input")
        else:
            # Backward-compatible single-event mode.
            _assert_keys_exact(src, ALLOWED_EVENT_FIELDS, "input(single_event)")
            src = {
                "run_id": "wave30_single_event",
                "scene_id": src.get("scene_id"),
                "shot_id": src.get("shot_id"),
                "is_synthetic": True,
                "required_lanes": [],
                "audio_events": [src],
            }

        run_id = _expect_non_empty_string(src.get("run_id"), "input.run_id")
        scene_id = _expect_non_empty_string(src.get("scene_id"), "input.scene_id")
        shot_id = _expect_non_empty_string(src.get("shot_id"), "input.shot_id")
        is_synthetic = bool(src.get("is_synthetic", True))
        if output_path == input_path:
            raise ValueError("--output must be different from --input")
        raw_events = src.get("audio_events")
        if not isinstance(raw_events, list) or not raw_events:
            raise ValueError("input.audio_events must be a non-empty list")
        raw_required_lanes = src.get("required_lanes", [])
        if not isinstance(raw_required_lanes, list):
            raise ValueError("input.required_lanes must be a list")
        normalized_required_lanes: list[str] = []
        for lane_idx, lane in enumerate(raw_required_lanes):
            normalized_required_lanes.append(
                _expect_non_empty_string(lane, f"input.required_lanes[{lane_idx}]")
            )
        if len(set(normalized_required_lanes)) != len(normalized_required_lanes):
            raise ValueError("input.required_lanes must not contain duplicates")

        compiled_events: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for idx, raw_event in enumerate(raw_events):
            if not isinstance(raw_event, dict):
                raise ValueError(f"audio_events[{idx}] must be an object")
            compiled = _compile_event(
                raw_event,
                idx,
                scene_id,
                shot_id,
                taxonomy_event_types,
                input_path.parent,
            )
            event_id = compiled["audio_event_id"]
            if event_id in seen_ids:
                raise ValueError(f"audio_events has duplicate audio_event_id: {event_id}")
            seen_ids.add(event_id)
            compiled_events.append(compiled)

        compiled_events.sort(key=lambda item: (item["start_seconds"], item["audio_event_id"]))
        manifest = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_event_manifest",
            "event_manifest_version": 1,
            "run_id": run_id,
            "scene_id": scene_id,
            "shot_id": shot_id,
            "is_synthetic": is_synthetic,
            "production_proof": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "taxonomy_registry_path": str(taxonomy_path),
            "taxonomy_registry_sha256": _sha256_of(taxonomy_path),
            "audio_event_count": len(compiled_events),
            "required_lanes": normalized_required_lanes,
            "audio_events": compiled_events,
            "artifact_manifest": {
                "source_input_path": str(input_path),
                "source_input_sha256": _sha256_of(input_path),
            },
            "av_sync_binding": {
                "frame_rate": float(src.get("av_frame_rate", 24.0)),
                "sync_scope": "event_level",
            },
        }
        _write_json_atomic(output_path, manifest)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
