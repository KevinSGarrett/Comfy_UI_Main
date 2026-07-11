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

from jsonschema import Draft202012Validator

GATE_NAMES = (
    "decode",
    "duration",
    "loudness",
    "clipping",
    "sync",
    "voice_identity",
    "event_coverage",
    "mix_balance",
    "artifact_manifest",
    "runtime_proof",
    "audio_review",
)
GATE_TERMINAL = {"pass", "fail", "block"}
RUNTIME_PROOF_REQUIRED_KEYS = {
    "schema_name",
    "proof_kind",
    "verified",
    "run_id",
    "mix_id",
    "event_manifest_sha256",
    "mixdown_sha256",
    "generation_executed",
    "decode_passed",
    "duration_passed",
    "artifact_hash_passed",
    "av_sync_passed",
}
REVIEW_PROOF_REQUIRED_KEYS = {
    "schema_name",
    "proof_kind",
    "verified",
    "review_method",
    "run_id",
    "mix_id",
    "event_manifest_sha256",
    "mixdown_sha256",
    "correct_speaker",
    "voice_profile_consistency",
    "speech_intelligibility",
    "foley_action_alignment",
    "ambience_dialogue_balance",
    "no_clipping",
    "mix_balance",
    "av_sync",
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


def _expect_path_sha_binding(binding: Any, label: str) -> tuple[Path, str]:
    if not isinstance(binding, dict):
        raise ValueError(f"{label} must be an object")
    path_value = binding.get("path")
    sha_value = binding.get("sha256")
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError(f"{label}.path must be a non-empty string")
    if not isinstance(sha_value, str) or len(sha_value) != 64:
        raise ValueError(f"{label}.sha256 must be 64-char SHA-256")
    path = Path(path_value).resolve()
    if not path.is_file():
        raise ValueError(f"{label}.path does not exist: {path}")
    observed = _sha256_of(path)
    if observed != sha_value:
        raise ValueError(f"{label}.sha256 mismatch ({sha_value} != {observed})")
    return path, observed


def _validate_with_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path)
        raise ValueError(f"{label} failed schema validation at {location}: {first.message}")


def _expect_object_keys_exact(payload: dict[str, Any], required: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(required - observed)
    extra = sorted(observed - required)
    if missing or extra:
        detail: list[str] = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if extra:
            detail.append(f"unknown={','.join(extra)}")
        raise ValueError(f"{label} key mismatch ({'; '.join(detail)})")


def _all_pass(gates: dict[str, str]) -> bool:
    return all(gates.get(name) == "pass" for name in GATE_NAMES)


def _expect_bool_true(value: Any, label: str) -> None:
    if value is not True:
        raise ValueError(f"{label} must be true")


def _expect_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _read_wav_metrics(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise ValueError(f"mixdown_artifact is not a valid PCM WAV: {exc}") from exc
    expected_bytes = frame_count * channels * sample_width
    if len(payload) != expected_bytes:
        raise ValueError(
            "mixdown_artifact decoded payload mismatch "
            f"({len(payload)} != {expected_bytes})"
        )
    if channels <= 0 or sample_rate <= 0 or sample_width <= 0 or frame_count <= 0:
        raise ValueError("mixdown_artifact WAV metrics must be positive")
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": frame_count / float(sample_rate),
    }


def _verify_mixdown_artifact(mix_manifest: dict[str, Any]) -> str:
    artifact = mix_manifest.get("mixdown_artifact")
    if not isinstance(artifact, dict):
        raise ValueError("mixdown_artifact must be an object")
    path = artifact.get("path")
    sha = artifact.get("sha256")
    declared_bytes = artifact.get("bytes")
    if (
        not isinstance(path, str)
        or not path.strip()
        or not isinstance(sha, str)
        or len(sha) != 64
        or not isinstance(declared_bytes, int)
        or declared_bytes <= 0
    ):
        raise ValueError("mixdown_artifact path/sha256/bytes are invalid")
    artifact_path = Path(path).resolve()
    if not artifact_path.is_file():
        raise ValueError(f"mixdown_artifact.path does not exist: {artifact_path}")
    if artifact_path.stat().st_size != declared_bytes:
        raise ValueError("mixdown_artifact.bytes mismatch")
    observed_sha = _sha256_of(artifact_path)
    if observed_sha != sha:
        raise ValueError(f"mixdown_artifact.sha256 mismatch ({sha} != {observed_sha})")
    wav_metrics = _read_wav_metrics(artifact_path)
    mix_technical = mix_manifest.get("mix_technical")
    if not isinstance(mix_technical, dict):
        raise ValueError("mix_technical must be an object")
    if mix_technical.get("sample_rate_hz") != wav_metrics["sample_rate_hz"]:
        raise ValueError("mix_technical.sample_rate_hz mismatch against decoded WAV")
    if mix_technical.get("channels") != wav_metrics["channels"]:
        raise ValueError("mix_technical.channels mismatch against decoded WAV")
    if mix_technical.get("sample_width_bytes") != wav_metrics["sample_width_bytes"]:
        raise ValueError("mix_technical.sample_width_bytes mismatch against decoded WAV")
    if mix_technical.get("frame_count") != wav_metrics["frame_count"]:
        raise ValueError("mix_technical.frame_count mismatch against decoded WAV")
    channel_layout = mix_technical.get("channel_layout")
    if not isinstance(channel_layout, str) or not channel_layout.strip():
        raise ValueError("mix_technical.channel_layout must be a non-empty string")
    declared_duration = mix_technical.get("duration_seconds")
    if not isinstance(declared_duration, (int, float)) or isinstance(declared_duration, bool):
        raise ValueError("mix_technical.duration_seconds must be numeric")
    if abs(float(declared_duration) - wav_metrics["duration_seconds"]) > 1e-6:
        raise ValueError("mix_technical.duration_seconds mismatch against decoded WAV")
    return observed_sha


def _load_and_validate_runtime_proof(
    proof_binding: Any,
    *,
    run_id: str,
    mix_id: str,
    event_manifest_sha256: str,
    mixdown_sha256: str,
) -> bool:
    proof_path, _ = _expect_path_sha_binding(proof_binding, "mix_manifest.runtime_proof")
    try:
        payload = _load_json(proof_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"runtime proof is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("runtime proof JSON must be an object")
    _expect_object_keys_exact(payload, RUNTIME_PROOF_REQUIRED_KEYS, "runtime proof")
    if payload.get("schema_name") != "wave30_audio_runtime_proof":
        raise ValueError("runtime proof schema_name mismatch")
    if payload.get("proof_kind") != "runtime":
        raise ValueError("runtime proof proof_kind mismatch")
    _expect_bool_true(payload.get("verified"), "runtime proof verified")
    if payload.get("run_id") != run_id:
        raise ValueError("runtime proof run_id mismatch")
    if payload.get("mix_id") != mix_id:
        raise ValueError("runtime proof mix_id mismatch")
    if payload.get("event_manifest_sha256") != event_manifest_sha256:
        raise ValueError("runtime proof event_manifest_sha256 mismatch")
    if payload.get("mixdown_sha256") != mixdown_sha256:
        raise ValueError("runtime proof mixdown_sha256 mismatch")
    _expect_bool_true(payload.get("generation_executed"), "runtime proof generation_executed")
    _expect_bool_true(payload.get("decode_passed"), "runtime proof decode_passed")
    _expect_bool_true(payload.get("duration_passed"), "runtime proof duration_passed")
    _expect_bool_true(payload.get("artifact_hash_passed"), "runtime proof artifact_hash_passed")
    _expect_bool_true(payload.get("av_sync_passed"), "runtime proof av_sync_passed")
    return True


def _load_and_validate_audio_review_proof(
    proof_binding: Any,
    *,
    run_id: str,
    mix_id: str,
    event_manifest_sha256: str,
    mixdown_sha256: str,
) -> bool:
    proof_path, _ = _expect_path_sha_binding(proof_binding, "mix_manifest.audio_review")
    try:
        payload = _load_json(proof_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"audio review proof is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("audio review proof JSON must be an object")
    _expect_object_keys_exact(payload, REVIEW_PROOF_REQUIRED_KEYS, "audio review proof")
    if payload.get("schema_name") != "wave30_audio_review_proof":
        raise ValueError("audio review proof schema_name mismatch")
    if payload.get("proof_kind") != "audio_review":
        raise ValueError("audio review proof proof_kind mismatch")
    if payload.get("review_method") != "audio_playback_review":
        raise ValueError("audio review proof review_method mismatch")
    _expect_bool_true(payload.get("verified"), "audio review proof verified")
    if payload.get("run_id") != run_id:
        raise ValueError("audio review proof run_id mismatch")
    if payload.get("mix_id") != mix_id:
        raise ValueError("audio review proof mix_id mismatch")
    if payload.get("event_manifest_sha256") != event_manifest_sha256:
        raise ValueError("audio review proof event_manifest_sha256 mismatch")
    if payload.get("mixdown_sha256") != mixdown_sha256:
        raise ValueError("audio review proof mixdown_sha256 mismatch")
    _expect_bool_true(payload.get("correct_speaker"), "audio review proof correct_speaker")
    _expect_bool_true(
        payload.get("voice_profile_consistency"), "audio review proof voice_profile_consistency"
    )
    _expect_bool_true(payload.get("speech_intelligibility"), "audio review proof speech_intelligibility")
    _expect_bool_true(payload.get("foley_action_alignment"), "audio review proof foley_action_alignment")
    _expect_bool_true(
        payload.get("ambience_dialogue_balance"), "audio review proof ambience_dialogue_balance"
    )
    _expect_bool_true(payload.get("no_clipping"), "audio review proof no_clipping")
    _expect_bool_true(payload.get("mix_balance"), "audio review proof mix_balance")
    _expect_bool_true(payload.get("av_sync"), "audio review proof av_sync")
    return True


def _validate_mix_event_metadata(
    event_manifest: dict[str, Any],
    mix_manifest: dict[str, Any],
    required_lanes: list[str],
) -> None:
    source_events = event_manifest.get("audio_events")
    if not isinstance(source_events, list):
        raise ValueError("event_manifest.audio_events must be an array")
    event_by_id: dict[str, dict[str, Any]] = {}
    for entry in source_events:
        if not isinstance(entry, dict):
            raise ValueError("event_manifest.audio_events entries must be objects")
        event_id = _expect_string(entry.get("audio_event_id"), "event_manifest.audio_events[].audio_event_id")
        if event_id in event_by_id:
            raise ValueError(f"event_manifest has duplicate audio_event_id: {event_id}")
        event_by_id[event_id] = entry

    mix_entries = mix_manifest.get("mix_event_metadata")
    if not isinstance(mix_entries, list):
        raise ValueError("mix_manifest.mix_event_metadata must be an array")
    seen: dict[str, int] = {}
    for idx, entry in enumerate(mix_entries):
        if not isinstance(entry, dict):
            raise ValueError(f"mix_manifest.mix_event_metadata[{idx}] must be an object")
        event_id = _expect_string(
            entry.get("audio_event_id"), f"mix_manifest.mix_event_metadata[{idx}].audio_event_id"
        )
        seen[event_id] = seen.get(event_id, 0) + 1
    duplicates = sorted(event_id for event_id, count in seen.items() if count > 1)
    if duplicates:
        raise ValueError(f"mix_manifest.mix_event_metadata has duplicate audio_event_id entries: {duplicates}")
    source_ids = set(event_by_id.keys())
    mix_ids = set(seen.keys())
    missing = sorted(source_ids - mix_ids)
    extra = sorted(mix_ids - source_ids)
    if missing:
        raise ValueError(f"mix_manifest.mix_event_metadata missing source event IDs: {missing}")
    if extra:
        raise ValueError(f"mix_manifest.mix_event_metadata has unknown event IDs: {extra}")
    required_event_ids = sorted(
        event_id
        for event_id, entry in event_by_id.items()
        if isinstance(entry.get("layer"), str) and entry.get("layer") in set(required_lanes)
    )
    missing_required = [event_id for event_id in required_event_ids if event_id not in mix_ids]
    if missing_required:
        raise ValueError(
            "mix_manifest.mix_event_metadata missing events on required lanes: "
            f"{missing_required}"
        )


def _validate_av_sync(event_manifest: dict[str, Any], mix_manifest: dict[str, Any]) -> None:
    source_events = event_manifest.get("audio_events")
    if not isinstance(source_events, list) or not source_events:
        raise ValueError("event_manifest.audio_events must be a non-empty array")
    frame_rates: set[float] = set()
    source_start: int | None = None
    source_end: int | None = None
    for idx, entry in enumerate(source_events):
        if not isinstance(entry, dict):
            raise ValueError(f"event_manifest.audio_events[{idx}] must be an object")
        frame_range = entry.get("expected_video_frame_range")
        if not isinstance(frame_range, dict):
            raise ValueError(f"event_manifest.audio_events[{idx}].expected_video_frame_range must be object")
        start_frame = frame_range.get("start_frame")
        end_frame = frame_range.get("end_frame")
        if (
            not isinstance(start_frame, int)
            or isinstance(start_frame, bool)
            or not isinstance(end_frame, int)
            or isinstance(end_frame, bool)
            or end_frame < start_frame
        ):
            raise ValueError(f"event_manifest.audio_events[{idx}] has invalid frame range")
        rate = frame_range.get("frame_rate")
        if not isinstance(rate, (int, float)) or isinstance(rate, bool) or rate <= 0:
            raise ValueError(f"event_manifest.audio_events[{idx}] has invalid frame_rate")
        frame_rates.add(float(rate))
        source_start = start_frame if source_start is None else min(source_start, start_frame)
        source_end = end_frame if source_end is None else max(source_end, end_frame)
    if len(frame_rates) != 1:
        raise ValueError("event_manifest source events must use exactly one AV frame rate")
    source_rate = next(iter(frame_rates))
    av_sync = mix_manifest.get("av_sync_evidence")
    if not isinstance(av_sync, dict):
        raise ValueError("mix_manifest.av_sync_evidence must be an object")
    mix_rate = av_sync.get("frame_rate")
    mix_start = av_sync.get("start_frame")
    mix_end = av_sync.get("end_frame")
    mix_offset = av_sync.get("frame_offset")
    if not isinstance(mix_rate, (int, float)) or isinstance(mix_rate, bool) or float(mix_rate) <= 0:
        raise ValueError("mix_manifest.av_sync_evidence.frame_rate must be positive")
    if abs(float(mix_rate) - source_rate) > 1e-6:
        raise ValueError("mix_manifest.av_sync_evidence.frame_rate must match source event frame rate")
    if (
        not isinstance(mix_start, int)
        or isinstance(mix_start, bool)
        or not isinstance(mix_end, int)
        or isinstance(mix_end, bool)
        or mix_end < mix_start
    ):
        raise ValueError("mix_manifest.av_sync_evidence start/end frame must be valid integers")
    if mix_offset != 0:
        raise ValueError("mix_manifest.av_sync_evidence.frame_offset must be zero")
    if source_start is not None and mix_start > source_start:
        raise ValueError("mix av_sync start_frame must cover source start_frame")
    if source_end is not None and mix_end < source_end:
        raise ValueError("mix av_sync end_frame must cover source end_frame")
    mix_technical = mix_manifest.get("mix_technical")
    if not isinstance(mix_technical, dict):
        raise ValueError("mix_technical must be an object")
    duration_value = mix_technical.get("duration_seconds")
    if not isinstance(duration_value, (int, float)) or isinstance(duration_value, bool):
        raise ValueError("mix_technical.duration_seconds must be numeric")
    expected_span = float(duration_value) * float(mix_rate)
    observed_span = float(mix_end - mix_start)
    if abs(expected_span - observed_span) > 1.0:
        raise ValueError("mix AV frame span must match mix_technical.duration_seconds within one frame")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    event_schema_path = root / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json"
    mix_schema_path = root / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json"
    report_schema_path = root / "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json"

    try:
        src = _load_json(Path(args.input).resolve())
        event_schema = _load_json(event_schema_path)
        mix_schema = _load_json(mix_schema_path)
        report_schema = _load_json(report_schema_path)
        scoring_rules = _load_json(root / "Plan/10_REGISTRIES/wave30_audio_qa_scoring_rules.json")

        run_id = src.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("input.run_id must be a non-empty string")
        run_id = run_id.strip()
        if not isinstance(src.get("is_synthetic"), bool):
            raise ValueError("input.is_synthetic must be boolean")
        is_synthetic = src["is_synthetic"]

        event_bindings = src.get("event_manifest_bindings")
        if not isinstance(event_bindings, list) or len(event_bindings) != 1:
            raise ValueError("input.event_manifest_bindings must be a one-element list for strict mode")
        event_manifest_path, event_manifest_sha = _expect_path_sha_binding(
            event_bindings[0], "input.event_manifest_bindings[0]"
        )
        mix_manifest_path, mix_manifest_sha = _expect_path_sha_binding(
            src.get("mix_manifest_binding"), "input.mix_manifest_binding"
        )

        event_manifest = _load_json(event_manifest_path)
        mix_manifest = _load_json(mix_manifest_path)
        _validate_with_schema(event_manifest, event_schema, "event_manifest")
        _validate_with_schema(mix_manifest, mix_schema, "mix_manifest")

        if event_manifest.get("is_synthetic") is not is_synthetic:
            raise ValueError("input.is_synthetic must match event manifest synthetic state")
        if mix_manifest.get("is_synthetic") is not is_synthetic:
            raise ValueError("input.is_synthetic must match mix manifest synthetic state")
        manifest_run_id = event_manifest.get("run_id")
        if not isinstance(manifest_run_id, str) or not manifest_run_id.strip():
            raise ValueError("event_manifest.run_id must be non-empty string")
        mix_run_id = mix_manifest.get("run_id")
        if not isinstance(mix_run_id, str) or not mix_run_id.strip():
            raise ValueError("mix_manifest.run_id must be non-empty string")
        if run_id != manifest_run_id or run_id != mix_run_id:
            raise ValueError("run_id mismatch across scorer input/event manifest/mix manifest")

        declared_bindings = mix_manifest.get("event_manifest_bindings")
        if (
            not isinstance(declared_bindings, list)
            or len(declared_bindings) != 1
            or not isinstance(declared_bindings[0], dict)
            or declared_bindings[0].get("path") != str(event_manifest_path)
            or declared_bindings[0].get("sha256") != event_manifest_sha
        ):
            raise ValueError("mix_manifest.event_manifest_bindings must match scorer input binding")

        dimensions = scoring_rules.get("dimensions")
        if dimensions != [
            "decode",
            "duration",
            "loudness",
            "clipping",
            "sync",
            "voice_identity",
            "event_coverage",
            "mix_balance",
        ]:
            raise ValueError("wave30_audio_qa_scoring_rules dimensions registry drift detected")

        raw_scores = src.get("qa_scores")
        if not isinstance(raw_scores, dict):
            raise ValueError("input.qa_scores must be an object")
        score_values: dict[str, float] = {}
        for name in dimensions:
            value = raw_scores.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"input.qa_scores.{name} must be numeric")
            value_f = float(value)
            if not math.isfinite(value_f):
                raise ValueError(f"input.qa_scores.{name} must be finite")
            if value_f < 0.0 or value_f > 100.0:
                raise ValueError(f"input.qa_scores.{name} must be in [0,100]")
            score_values[name] = round(value_f, 2)
        overall = round(sum(score_values.values()) / float(len(score_values)), 2)

        required_lanes = src.get("required_lanes")
        if not isinstance(required_lanes, list):
            raise ValueError("input.required_lanes must be a list")
        event_lanes = {
            event["layer"]
            for event in event_manifest.get("audio_events", [])
            if isinstance(event, dict) and isinstance(event.get("layer"), str)
        }
        for lane in required_lanes:
            if not isinstance(lane, str) or not lane.strip():
                raise ValueError("input.required_lanes values must be non-empty strings")
            if lane not in event_lanes:
                raise ValueError(f"required lane missing from event manifest: {lane}")

        gates = src.get("gate_statuses")
        if not isinstance(gates, dict):
            raise ValueError("input.gate_statuses must be an object")
        gate_statuses: dict[str, str] = {}
        for gate_name in GATE_NAMES:
            value = gates.get(gate_name)
            if value not in GATE_TERMINAL:
                raise ValueError(f"input.gate_statuses.{gate_name} must be one of {sorted(GATE_TERMINAL)}")
            gate_statuses[gate_name] = value

        mix_id = mix_manifest.get("mix_id")
        if not isinstance(mix_id, str) or not mix_id.strip():
            raise ValueError("mix_manifest.mix_id must be non-empty string")
        mixdown_sha = _verify_mixdown_artifact(mix_manifest)
        _validate_mix_event_metadata(event_manifest, mix_manifest, required_lanes)
        _validate_av_sync(event_manifest, mix_manifest)
        runtime_ok = False
        if gate_statuses["runtime_proof"] == "pass":
            runtime_ok = _load_and_validate_runtime_proof(
                mix_manifest.get("runtime_proof"),
                run_id=run_id,
                mix_id=mix_id,
                event_manifest_sha256=event_manifest_sha,
                mixdown_sha256=mixdown_sha,
            )
        review_ok = False
        if gate_statuses["audio_review"] == "pass":
            review_ok = _load_and_validate_audio_review_proof(
                mix_manifest.get("audio_review"),
                run_id=run_id,
                mix_id=mix_id,
                event_manifest_sha256=event_manifest_sha,
                mixdown_sha256=mixdown_sha,
            )

        if gate_statuses["runtime_proof"] == "pass" and not runtime_ok:
            raise ValueError("runtime_proof gate cannot pass without verified runtime proof artifact")
        if gate_statuses["audio_review"] == "pass" and not review_ok:
            raise ValueError("audio_review gate cannot pass without verified review proof artifact")
        if is_synthetic and (runtime_ok or review_ok):
            raise ValueError("synthetic inputs cannot carry verified runtime/audio review proof")

        all_gates_pass = _all_pass(gate_statuses)
        promote_allowed = (
            not is_synthetic
            and all_gates_pass
            and runtime_ok
            and review_ok
            and overall >= float(scoring_rules.get("promotion_threshold", 90))
        )
        if promote_allowed:
            decision = "promote"
        else:
            decision = "block"
        if not all_gates_pass:
            decision = "block"

        report = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_qa_report",
            "report_version": 1,
            "run_id": run_id,
            "is_synthetic": is_synthetic,
            "event_manifest_binding": {
                "path": str(event_manifest_path),
                "sha256": event_manifest_sha,
            },
            "mix_manifest_binding": {
                "path": str(mix_manifest_path),
                "sha256": mix_manifest_sha,
            },
            "qa_scores": score_values,
            "overall_audio_score": overall,
            "hard_gate_statuses": gate_statuses,
            "proof_verification": {
                "runtime_proof_verified": runtime_ok,
                "audio_review_verified": review_ok,
                "artifact_bindings_verified": True,
            },
            "computed_flags": {
                "all_hard_gates_passed": all_gates_pass,
                "production_eligible": promote_allowed,
            },
            "promotion_decision": decision,
        }
        _validate_with_schema(report, report_schema, "qa_report")
        _write_json_atomic(Path(args.output).resolve(), report)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(str(Path(args.output).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
