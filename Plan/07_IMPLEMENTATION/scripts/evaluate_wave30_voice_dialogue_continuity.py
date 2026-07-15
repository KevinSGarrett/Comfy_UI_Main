#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PASS = "PASS"
BLOCKED = "BLOCKED"
FAIL = "FAIL"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

GATE_NAMES = (
    "voice_profile_match",
    "dialogue_timing",
    "intelligibility_score",
    "emotional_tone",
    "voice_continuity",
    "audio_review_record",
    "production_runtime_proof",
    "production_proof_authority",
    "overall_pass",
)

DEFAULT_THRESHOLDS: dict[str, float] = {
    "max_line_duration_delta_seconds": 0.35,
    "max_asr_segment_timing_delta_seconds": 0.30,
    "max_normalized_wer": 0.20,
    "min_speaker_similarity": 0.80,
    "min_cross_line_continuity": 0.75,
    "min_emotion_confidence": 0.70,
    "min_intensity_score": 0.70,
    "max_clipping_ratio": 0.0001,
    "max_silence_ratio": 0.9950,
    "min_rms_ratio": 0.0050,
}

ASR_SCHEMA_NAME = "wave30_asr_proof"
ASR_PROOF_KIND = "asr"
SPEAKER_SCHEMA_NAME = "wave30_speaker_proof"
SPEAKER_PROOF_KIND = "speaker"
EMOTION_SCHEMA_NAME = "wave30_emotion_proof"
EMOTION_PROOF_KIND = "emotion"
PLAYBACK_SCHEMA_NAME = "wave30_playback_review_proof"
PLAYBACK_PROOF_KIND = "playback_review"
RUNTIME_SCHEMA_NAME = "wave30_production_runtime_proof"
RUNTIME_PROOF_KIND = "production_runtime"
PROOF_BUNDLE_SCHEMA_NAME = "wave30_production_proof_bundle"
PROOF_BUNDLE_KIND = "production_proof_bundle"
AUTHORITY_REGISTRY_SCHEMA_NAME = "wave30_voice_proof_authority_registry"

ASR_PROOF_KEYS = {
    "schema_name",
    "proof_kind",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_results",
}
ASR_LINE_KEYS = {"line_id", "audio_sha256", "transcript", "start_time", "end_time"}

SPEAKER_PROOF_KEYS = {
    "schema_name",
    "proof_kind",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_results",
}
SPEAKER_LINE_KEYS = {
    "line_id",
    "character_id",
    "voice_profile_id",
    "audio_sha256",
    "speaker_similarity",
    "continuity_with_previous",
}

EMOTION_PROOF_KEYS = {
    "schema_name",
    "proof_kind",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_results",
}
EMOTION_LINE_KEYS = {
    "line_id",
    "audio_sha256",
    "predicted_emotion",
    "emotion_confidence",
    "predicted_intensity",
    "intensity_score",
}

LINE_AUDIO_HASH_KEYS = {"line_id", "audio_sha256"}

PLAYBACK_PROOF_KEYS = {
    "schema_name",
    "proof_kind",
    "review_method",
    "reviewer_id",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_audio_bindings",
    "voice_identity",
    "intelligibility",
    "timing",
    "emotional_tone",
    "continuity",
    "noise_free",
    "clipping_free",
}

RUNTIME_PROOF_KEYS = {
    "schema_name",
    "proof_kind",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_audio_bindings",
    "runtime_executed",
    "decode_succeeded",
}

PROOF_BUNDLE_KEYS = {
    "schema_name",
    "proof_kind",
    "bundle_version",
    "bundle_id",
    "authority_id",
    "run_id",
    "is_synthetic",
    "dialogue_contract_sha256",
    "voice_profile_sha256",
    "line_audio_bindings",
    "asr_proof_sha256",
    "speaker_proof_sha256",
    "emotion_proof_sha256",
    "playback_review_proof_sha256",
    "production_runtime_proof_sha256",
}

AUTHORITY_REGISTRY_KEYS = {
    "schema_name",
    "registry_version",
    "approved_proof_bundles",
}
APPROVED_BUNDLE_KEYS = {
    "bundle_id",
    "authority_id",
    "proof_bundle_sha256",
    "revoked",
}

AUTHORITY_REGISTRY_RELATIVE = Path("Plan/10_REGISTRIES/wave30_voice_proof_authority_registry.json")
CANONICAL_ROOT = Path(__file__).resolve().parents[3]


class InvalidInputError(ValueError):
    pass


@dataclass(frozen=True)
class Binding:
    path: Path
    sha256: str


def _reject_nonfinite_json(token: str) -> Any:
    raise InvalidInputError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"invalid JSON in {path}: {exc}") from exc


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect_exact_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(keys - observed)
    extra = sorted(observed - keys)
    if missing or extra:
        detail: list[str] = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if extra:
            detail.append(f"unknown={','.join(extra)}")
        raise InvalidInputError(f"{label} key mismatch ({'; '.join(detail)})")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_non_empty_string(value, label)
    if not SHA256_RE.fullmatch(sha):
        raise InvalidInputError(f"{label} must be lowercase SHA-256")
    return sha


def _expect_finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f"{label} must be numeric")
    value_f = float(value)
    if not math.isfinite(value_f):
        raise InvalidInputError(f"{label} must be finite")
    return value_f


def _expect_ratio_0_1(value: Any, label: str) -> float:
    ratio = _expect_finite_number(value, label)
    if ratio < 0.0 or ratio > 1.0:
        raise InvalidInputError(f"{label} must be in [0, 1]")
    return ratio


def _validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path)
        raise InvalidInputError(f"{label} schema validation failed at {path}: {first.message}")


def _resolve_under_root(root: Path, candidate: str, label: str) -> Path:
    raw_path = Path(candidate)
    resolved = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    if not resolved.is_relative_to(root):
        raise InvalidInputError(f"{label} escapes root: {resolved}")
    return resolved


def _validate_binding(root: Path, binding: Any, label: str) -> Binding:
    if not isinstance(binding, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(binding, {"path", "sha256"}, label)
    path = _resolve_under_root(root, _expect_non_empty_string(binding["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(binding["sha256"], f"{label}.sha256")
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed = _sha256_of(path)
    if observed != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed})")
    return Binding(path=path, sha256=sha)


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


def _normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, token_a in enumerate(a, start=1):
        current = [i]
        for j, token_b in enumerate(b, start=1):
            substitution = previous[j - 1] + (0 if token_a == token_b else 1)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def _decode_pcm_samples(payload: bytes, sample_width: int) -> tuple[int, int, int, float]:
    if sample_width == 1:
        max_value = 127
        peak = 0
        clipping = 0
        silence = 0
        sum_squares = 0.0
        for raw in payload:
            signed = raw - 128
            level = abs(signed)
            if level > peak:
                peak = level
            if level >= max_value:
                clipping += 1
            if level == 0:
                silence += 1
            sum_squares += float(signed * signed)
        return peak, clipping, silence, sum_squares
    if sample_width == 2:
        max_value = 32767
        peak = 0
        clipping = 0
        silence = 0
        sum_squares = 0.0
        for (sample,) in struct.iter_unpack("<h", payload):
            level = abs(sample)
            if level > peak:
                peak = level
            if level >= max_value:
                clipping += 1
            if level == 0:
                silence += 1
            sum_squares += float(sample * sample)
        return peak, clipping, silence, sum_squares
    if sample_width == 3:
        max_value = (1 << 23) - 1
        peak = 0
        clipping = 0
        silence = 0
        sum_squares = 0.0
        for index in range(0, len(payload), 3):
            chunk = payload[index : index + 3]
            signed = int.from_bytes(chunk + (b"\xff" if chunk[2] & 0x80 else b"\x00"), "little", signed=True)
            level = abs(signed)
            if level > peak:
                peak = level
            if level >= max_value:
                clipping += 1
            if level == 0:
                silence += 1
            sum_squares += float(signed * signed)
        return peak, clipping, silence, sum_squares
    if sample_width == 4:
        max_value = (1 << 31) - 1
        peak = 0
        clipping = 0
        silence = 0
        sum_squares = 0.0
        for (sample,) in struct.iter_unpack("<i", payload):
            level = abs(sample)
            if level > peak:
                peak = level
            if level >= max_value:
                clipping += 1
            if level == 0:
                silence += 1
            sum_squares += float(sample * sample)
        return peak, clipping, silence, sum_squares
    raise InvalidInputError(f"unsupported sample width: {sample_width}")


def _read_wav_metrics(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            comp_type = handle.getcomptype()
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise InvalidInputError(f"malformed WAV at {path}: {exc}") from exc
    if comp_type != "NONE":
        raise InvalidInputError(f"non-PCM WAV is not allowed: {path}")
    if channels <= 0 or sample_rate <= 0 or frame_count <= 0:
        raise InvalidInputError(f"invalid WAV metrics in {path}")
    if sample_width not in (1, 2, 3, 4):
        raise InvalidInputError(f"unsupported sample width in {path}: {sample_width}")
    expected_size = frame_count * channels * sample_width
    if len(payload) != expected_size:
        raise InvalidInputError(f"WAV payload length mismatch in {path} ({len(payload)} != {expected_size})")
    peak_sample, clipping_count, silence_count, sum_squares = _decode_pcm_samples(payload, sample_width)
    max_possible = float(127 if sample_width == 1 else (1 << (8 * sample_width - 1)) - 1)
    sample_total = frame_count * channels
    peak_ratio = 0.0 if max_possible <= 0 else min(1.0, peak_sample / max_possible)
    clipping_ratio = 0.0 if sample_total <= 0 else clipping_count / float(sample_total)
    silence_ratio = 0.0 if sample_total <= 0 else silence_count / float(sample_total)
    rms_ratio = 0.0
    if max_possible > 0 and sample_total > 0:
        rms_ratio = min(1.0, math.sqrt(sum_squares / float(sample_total)) / max_possible)
    return {
        "frames": frame_count,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "duration_seconds": frame_count / float(sample_rate),
        "peak_ratio": round(float(peak_ratio), 6),
        "rms_ratio": round(float(rms_ratio), 6),
        "silence_ratio": round(float(silence_ratio), 6),
        "clipping_sample_count": int(clipping_count),
        "clipping_ratio": round(float(clipping_ratio), 6),
    }


def _make_gate_result(status: str, blockers: list[str], artifact_bindings: list[str]) -> dict[str, Any]:
    return {"status": status, "blockers": blockers, "artifact_bindings": artifact_bindings}


def _binding_to_dict(binding: Binding | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    return {"path": str(binding.path), "sha256": binding.sha256}


def _expect_proof_header(payload: dict[str, Any], schema_name: str, proof_kind: str, label: str) -> None:
    if payload.get("schema_name") != schema_name:
        raise InvalidInputError(f"{label}.schema_name must be {schema_name}")
    if payload.get("proof_kind") != proof_kind:
        raise InvalidInputError(f"{label}.proof_kind must be {proof_kind}")
    for field in ("engine", "model", "model_version"):
        _expect_non_empty_string(payload.get(field), f"{label}.{field}")
    _expect_sha256(payload.get("model_sha256"), f"{label}.model_sha256")


def _validate_exact_line_audio_bindings(
    payload: Any,
    label: str,
    ordered_line_ids: list[str],
    line_bindings: dict[str, Binding],
) -> None:
    if not isinstance(payload, list):
        raise InvalidInputError(f"{label} must be an array")
    if len(payload) != len(ordered_line_ids):
        raise InvalidInputError(f"{label} must include every line exactly once")
    for idx, (entry, line_id) in enumerate(zip(payload, ordered_line_ids)):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"{label}[{idx}] must be object")
        _expect_exact_keys(entry, LINE_AUDIO_HASH_KEYS, f"{label}[{idx}]")
        observed_line_id = _expect_non_empty_string(entry["line_id"], f"{label}[{idx}].line_id")
        if observed_line_id != line_id:
            raise InvalidInputError(f"{label}[{idx}].line_id must be {line_id}")
        observed_sha = _expect_sha256(entry["audio_sha256"], f"{label}[{idx}].audio_sha256")
        if observed_sha != line_bindings[line_id].sha256:
            raise InvalidInputError(f"{label}[{idx}] audio hash mismatch for line {line_id}")


def _validate_authority_registry(registry_binding: Binding) -> list[dict[str, Any]]:
    registry_obj = _load_json(registry_binding.path)
    if not isinstance(registry_obj, dict):
        raise InvalidInputError("authority registry must be an object")
    _expect_exact_keys(registry_obj, AUTHORITY_REGISTRY_KEYS, "authority_registry")
    if registry_obj.get("schema_name") != AUTHORITY_REGISTRY_SCHEMA_NAME:
        raise InvalidInputError("authority_registry.schema_name mismatch")
    version = registry_obj.get("registry_version")
    if version != 1:
        raise InvalidInputError("authority_registry.registry_version must be 1")
    approved = registry_obj.get("approved_proof_bundles")
    if not isinstance(approved, list):
        raise InvalidInputError("authority_registry.approved_proof_bundles must be an array")
    entries: list[dict[str, Any]] = []
    seen_triples: set[tuple[str, str, str]] = set()
    for idx, entry in enumerate(approved):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"authority_registry.approved_proof_bundles[{idx}] must be object")
        _expect_exact_keys(entry, APPROVED_BUNDLE_KEYS, f"authority_registry.approved_proof_bundles[{idx}]")
        bundle_id = _expect_non_empty_string(entry.get("bundle_id"), f"approved_proof_bundles[{idx}].bundle_id")
        authority_id = _expect_non_empty_string(
            entry.get("authority_id"), f"approved_proof_bundles[{idx}].authority_id"
        )
        proof_bundle_sha256 = _expect_sha256(
            entry.get("proof_bundle_sha256"), f"approved_proof_bundles[{idx}].proof_bundle_sha256"
        )
        revoked = entry.get("revoked")
        if not isinstance(revoked, bool):
            raise InvalidInputError(f"approved_proof_bundles[{idx}].revoked must be boolean")
        triple = (bundle_id, authority_id, proof_bundle_sha256)
        if triple in seen_triples:
            raise InvalidInputError("authority_registry contains duplicate approved bundle entries")
        seen_triples.add(triple)
        entries.append(
            {
                "bundle_id": bundle_id,
                "authority_id": authority_id,
                "proof_bundle_sha256": proof_bundle_sha256,
                "revoked": revoked,
            }
        )
    return entries


def evaluate(root: Path, request_path: Path, output_path: Path) -> int:
    request_schema = _load_json(root / "Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_request.schema.json")
    evidence_schema = _load_json(root / "Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_evidence.schema.json")
    request_payload = _load_json(request_path)
    _validate_schema(request_payload, request_schema, "request")

    run_id = _expect_non_empty_string(request_payload["run_id"], "run_id")
    is_synthetic = bool(request_payload["is_synthetic"])
    request_binding = Binding(path=request_path.resolve(), sha256=_sha256_of(request_path.resolve()))

    voice_binding = _validate_binding(root, request_payload["voice_profile_binding"], "voice_profile_binding")
    contract_binding = _validate_binding(root, request_payload["dialogue_contract_binding"], "dialogue_contract_binding")

    thresholds = dict(DEFAULT_THRESHOLDS)
    threshold_input = request_payload.get("thresholds")
    if threshold_input is not None:
        if not isinstance(threshold_input, dict):
            raise InvalidInputError("thresholds must be an object")
        for key, value in threshold_input.items():
            if key not in thresholds:
                raise InvalidInputError(f"unknown threshold: {key}")
            thresholds[key] = _expect_finite_number(value, f"thresholds.{key}")
    for ratio_key in (
        "max_normalized_wer",
        "min_speaker_similarity",
        "min_cross_line_continuity",
        "min_emotion_confidence",
        "min_intensity_score",
        "max_clipping_ratio",
        "max_silence_ratio",
        "min_rms_ratio",
    ):
        _expect_ratio_0_1(thresholds[ratio_key], f"thresholds.{ratio_key}")
    for positive_key in ("max_line_duration_delta_seconds", "max_asr_segment_timing_delta_seconds"):
        if thresholds[positive_key] <= 0.0:
            raise InvalidInputError(f"thresholds.{positive_key} must be > 0")

    voice_profile = _load_json(voice_binding.path)
    if not isinstance(voice_profile, dict):
        raise InvalidInputError("voice profile must be a JSON object")
    for field in ("voice_profile_id", "character_id"):
        _expect_non_empty_string(voice_profile.get(field), f"voice_profile.{field}")
    voice_profile_id = _expect_non_empty_string(voice_profile["voice_profile_id"], "voice_profile.voice_profile_id")
    character_id = _expect_non_empty_string(voice_profile["character_id"], "voice_profile.character_id")

    dialogue_contract = _load_json(contract_binding.path)
    if not isinstance(dialogue_contract, dict):
        raise InvalidInputError("dialogue contract must be a JSON object")
    contract_lines = dialogue_contract.get("lines")
    if not isinstance(contract_lines, list) or not contract_lines:
        raise InvalidInputError("dialogue contract lines must be a non-empty array")

    expected_lines: dict[str, dict[str, Any]] = {}
    all_line_ids: list[str] = []
    dialogue_contract_version = dialogue_contract.get("dialogue_contract_version", 1)
    if not isinstance(dialogue_contract_version, int) or isinstance(dialogue_contract_version, bool):
        raise InvalidInputError("dialogue_contract_version must be integer")
    if dialogue_contract_version not in {1, 2}:
        raise InvalidInputError("dialogue_contract_version must be 1 or 2")
    for idx, line in enumerate(contract_lines):
        if not isinstance(line, dict):
            raise InvalidInputError(f"dialogue_contract.lines[{idx}] must be an object")
        expected_keys = {
            "line_id",
            "character_id",
            "voice_profile_id",
            "text",
            "start_time",
            "end_time",
            "emotion",
            "intensity",
            "sync_required",
            "output_file",
        }
        if dialogue_contract_version == 2:
            expected_keys.remove("emotion")
            expected_keys.update(
                {
                    "emotion_class",
                    "delivery_style",
                    "pace_wpm",
                    "emphasis",
                    "articulation",
                    "duration_target_seconds",
                }
            )
        _expect_exact_keys(line, expected_keys, f"dialogue_contract.lines[{idx}]")
        line_id = _expect_non_empty_string(line["line_id"], f"dialogue_contract.lines[{idx}].line_id")
        if line_id in expected_lines:
            raise InvalidInputError(f"duplicate line_id in dialogue contract: {line_id}")
        start_time = _expect_finite_number(line["start_time"], f"dialogue_contract.lines[{idx}].start_time")
        end_time = _expect_finite_number(line["end_time"], f"dialogue_contract.lines[{idx}].end_time")
        if end_time <= start_time:
            raise InvalidInputError(f"dialogue_contract.lines[{idx}] end_time must be > start_time")
        if dialogue_contract_version == 2:
            emotion_class = line["emotion_class"]
            if emotion_class is not None:
                _expect_non_empty_string(emotion_class, f"dialogue_contract.lines[{idx}].emotion_class")
            _expect_non_empty_string(line["delivery_style"], f"dialogue_contract.lines[{idx}].delivery_style")
            _expect_non_empty_string(line["intensity"], f"dialogue_contract.lines[{idx}].intensity")
            _expect_non_empty_string(line["emphasis"], f"dialogue_contract.lines[{idx}].emphasis")
            _expect_non_empty_string(line["articulation"], f"dialogue_contract.lines[{idx}].articulation")
            pace_wpm = _expect_finite_number(line["pace_wpm"], f"dialogue_contract.lines[{idx}].pace_wpm")
            duration_target = _expect_finite_number(
                line["duration_target_seconds"],
                f"dialogue_contract.lines[{idx}].duration_target_seconds",
            )
            if pace_wpm <= 0 or duration_target <= 0:
                raise InvalidInputError(f"dialogue_contract.lines[{idx}] pace and duration target must be positive")
        expected_lines[line_id] = line
        all_line_ids.append(line_id)

    line_id_set = set(all_line_ids)
    line_bindings_payload = request_payload["line_audio_bindings"]
    line_bindings: dict[str, Binding] = {}
    line_declared_bytes: dict[str, int] = {}
    seen_audio_paths: dict[Path, str] = {}
    seen_audio_shas: dict[str, str] = {}
    for idx, entry in enumerate(line_bindings_payload):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"line_audio_bindings[{idx}] must be an object")
        _expect_exact_keys(entry, {"line_id", "path", "sha256", "bytes"}, f"line_audio_bindings[{idx}]")
        line_id = _expect_non_empty_string(entry["line_id"], f"line_audio_bindings[{idx}].line_id")
        if line_id not in line_id_set:
            raise InvalidInputError(f"line_audio_bindings references unknown line_id: {line_id}")
        if line_id in line_bindings:
            raise InvalidInputError(f"duplicate line_id in line_audio_bindings: {line_id}")
        binding = _validate_binding(root, {"path": entry["path"], "sha256": entry["sha256"]}, f"line_audio_bindings[{idx}]")
        if binding.path in seen_audio_paths and seen_audio_paths[binding.path] != line_id:
            raise InvalidInputError(f"duplicate audio path reused across lines: {line_id}")
        if binding.sha256 in seen_audio_shas and seen_audio_shas[binding.sha256] != line_id:
            raise InvalidInputError(f"duplicate audio hash reused across lines: {line_id}")
        bytes_value = entry["bytes"]
        if not isinstance(bytes_value, int) or isinstance(bytes_value, bool) or bytes_value <= 0:
            raise InvalidInputError(f"line_audio_bindings[{idx}].bytes must be positive integer")
        if binding.path.stat().st_size != bytes_value:
            raise InvalidInputError(f"line_audio_bindings[{idx}].bytes mismatch")
        line_bindings[line_id] = binding
        line_declared_bytes[line_id] = bytes_value
        seen_audio_paths[binding.path] = line_id
        seen_audio_shas[binding.sha256] = line_id
    if set(line_bindings.keys()) != line_id_set:
        missing = sorted(line_id_set - set(line_bindings.keys()))
        extra = sorted(set(line_bindings.keys()) - line_id_set)
        raise InvalidInputError(f"line_audio_bindings must match exact line set (missing={missing}, extra={extra})")

    proof_bindings_payload = request_payload.get("proof_bindings")
    if not isinstance(proof_bindings_payload, dict):
        raise InvalidInputError("proof_bindings must be an object")
    proof_bindings: dict[str, Binding | None] = {}
    for key in (
        "asr_proof",
        "speaker_proof",
        "emotion_proof",
        "playback_review_proof",
        "production_runtime_proof",
        "production_proof_bundle_binding",
    ):
        value = proof_bindings_payload.get(key)
        if value is None:
            proof_bindings[key] = None
        else:
            proof_bindings[key] = _validate_binding(root, value, f"proof_bindings.{key}")

    authority_registry_binding = _validate_binding(
        root,
        {"path": str((root / AUTHORITY_REGISTRY_RELATIVE).resolve()), "sha256": _sha256_of((root / AUTHORITY_REGISTRY_RELATIVE).resolve())},
        "proof_bindings.authority_registry",
    )
    approved_registry_entries = _validate_authority_registry(authority_registry_binding)

    audio_metrics: list[dict[str, Any]] = []
    for line_id in all_line_ids:
        line = expected_lines[line_id]
        expected_output_file = _resolve_under_root(
            root, _expect_non_empty_string(line["output_file"], f"{line_id}.output_file"), f"{line_id}.output_file"
        )
        binding = line_bindings[line_id]
        if binding.path != expected_output_file:
            raise InvalidInputError(f"line {line_id} output_file mismatch ({expected_output_file} != {binding.path})")
        wav_metrics = _read_wav_metrics(binding.path)
        audio_metrics.append(
            {
                "line_id": line_id,
                "path": str(binding.path),
                "sha256": binding.sha256,
                "bytes": line_declared_bytes[line_id],
                **wav_metrics,
            }
        )

    bound_paths: set[Path] = {request_binding.path, voice_binding.path, contract_binding.path, authority_registry_binding.path}
    bound_paths.update(binding.path for binding in line_bindings.values())
    for proof_key in (
        "asr_proof",
        "speaker_proof",
        "emotion_proof",
        "playback_review_proof",
        "production_runtime_proof",
        "production_proof_bundle_binding",
    ):
        binding = proof_bindings[proof_key]
        if binding is not None:
            bound_paths.add(binding.path)
    if output_path in bound_paths:
        raise InvalidInputError("output path collides with bound request/artifact path")

    blockers: list[str] = []
    gates: dict[str, dict[str, Any]] = {}

    voice_blockers: list[str] = []
    for line_id, line in expected_lines.items():
        if line["character_id"] != character_id:
            voice_blockers.append(f"line {line_id} character_id does not match voice profile")
        if line["voice_profile_id"] != voice_profile_id:
            voice_blockers.append(f"line {line_id} voice_profile_id does not match voice profile")
    voice_status = PASS if not voice_blockers else FAIL
    gates["voice_profile_match"] = _make_gate_result(voice_status, voice_blockers, [voice_binding.sha256, contract_binding.sha256])

    timing_blockers: list[str] = []
    duration_map = {entry["line_id"]: entry["duration_seconds"] for entry in audio_metrics}
    for line_id, line in expected_lines.items():
        expected_duration = float(line["end_time"]) - float(line["start_time"])
        actual_duration = float(duration_map[line_id])
        if abs(expected_duration - actual_duration) > thresholds["max_line_duration_delta_seconds"]:
            timing_blockers.append(f"line {line_id} duration delta exceeds threshold")

    expected_token_count = 0
    total_distance = 0
    empty_expected_lines = 0
    empty_asr_lines = 0
    intelligibility_blockers: list[str] = []
    if proof_bindings["asr_proof"] is None:
        intelligibility_status = BLOCKED
        intelligibility_blockers.append("missing asr_proof")
    else:
        asr_payload_obj = _load_json(proof_bindings["asr_proof"].path)
        if not isinstance(asr_payload_obj, dict):
            raise InvalidInputError("ASR proof must be an object")
        _expect_exact_keys(asr_payload_obj, ASR_PROOF_KEYS, "asr_proof")
        _expect_proof_header(asr_payload_obj, ASR_SCHEMA_NAME, ASR_PROOF_KIND, "asr_proof")
        if asr_payload_obj["dialogue_contract_sha256"] != contract_binding.sha256:
            raise InvalidInputError("asr_proof dialogue_contract_sha256 mismatch")
        if asr_payload_obj["voice_profile_sha256"] != voice_binding.sha256:
            raise InvalidInputError("asr_proof voice_profile_sha256 mismatch")
        asr_lines = asr_payload_obj.get("line_results")
        if not isinstance(asr_lines, list):
            raise InvalidInputError("asr_proof.line_results must be an array")
        seen_line_ids: set[str] = set()
        for idx, entry in enumerate(asr_lines):
            if not isinstance(entry, dict):
                raise InvalidInputError(f"asr_proof.line_results[{idx}] must be object")
            _expect_exact_keys(entry, ASR_LINE_KEYS, f"asr_proof.line_results[{idx}]")
            line_id = _expect_non_empty_string(entry["line_id"], f"asr_proof.line_results[{idx}].line_id")
            if line_id not in line_id_set:
                raise InvalidInputError(f"asr_proof references unknown line_id: {line_id}")
            if line_id in seen_line_ids:
                raise InvalidInputError(f"asr_proof duplicate line_id: {line_id}")
            seen_line_ids.add(line_id)
            if entry["audio_sha256"] != line_bindings[line_id].sha256:
                raise InvalidInputError(f"asr_proof audio hash mismatch for line {line_id}")
            start_time = _expect_finite_number(entry["start_time"], f"asr line {line_id} start_time")
            end_time = _expect_finite_number(entry["end_time"], f"asr line {line_id} end_time")
            if end_time <= start_time:
                raise InvalidInputError(f"asr segment timing invalid for line {line_id}")
            expected_start = float(expected_lines[line_id]["start_time"])
            expected_end = float(expected_lines[line_id]["end_time"])
            if abs(start_time - expected_start) > thresholds["max_asr_segment_timing_delta_seconds"]:
                timing_blockers.append(f"line {line_id} ASR start timing delta exceeds threshold")
            if abs(end_time - expected_end) > thresholds["max_asr_segment_timing_delta_seconds"]:
                timing_blockers.append(f"line {line_id} ASR end timing delta exceeds threshold")
            expected_text = _expect_non_empty_string(expected_lines[line_id]["text"], f"{line_id}.text")
            expected_tokens = _normalize_tokens(expected_text)
            transcript = _expect_non_empty_string(entry["transcript"], f"asr line {line_id} transcript")
            observed_tokens = _normalize_tokens(transcript)
            if not expected_tokens:
                empty_expected_lines += 1
                intelligibility_blockers.append(f"line {line_id} expected text normalizes to empty tokens")
            if not observed_tokens:
                empty_asr_lines += 1
                intelligibility_blockers.append(f"line {line_id} ASR transcript normalizes to empty tokens")
            expected_token_count += len(expected_tokens)
            total_distance += _levenshtein(expected_tokens, observed_tokens)
        missing_asr_lines = sorted(line_id_set - seen_line_ids)
        for line_id in missing_asr_lines:
            intelligibility_blockers.append(f"asr_proof missing line {line_id}")
        denominator = max(1, expected_token_count)
        normalized_wer = min(1.0, total_distance / float(denominator))
        if normalized_wer > thresholds["max_normalized_wer"]:
            intelligibility_blockers.append("normalized WER exceeds threshold")
        intelligibility_status = PASS if not intelligibility_blockers else FAIL

    timing_status = PASS if not timing_blockers else FAIL
    gates["dialogue_timing"] = _make_gate_result(
        timing_status, timing_blockers, [contract_binding.sha256] + [item["sha256"] for item in audio_metrics]
    )
    gates["intelligibility_score"] = _make_gate_result(
        intelligibility_status,
        intelligibility_blockers,
        [contract_binding.sha256, proof_bindings["asr_proof"].sha256] if proof_bindings["asr_proof"] else [contract_binding.sha256],
    )

    speaker_blockers: list[str] = []
    if proof_bindings["speaker_proof"] is None:
        speaker_status = BLOCKED
        speaker_blockers.append("missing speaker_proof")
    else:
        speaker_obj = _load_json(proof_bindings["speaker_proof"].path)
        if not isinstance(speaker_obj, dict):
            raise InvalidInputError("speaker_proof must be an object")
        _expect_exact_keys(speaker_obj, SPEAKER_PROOF_KEYS, "speaker_proof")
        _expect_proof_header(speaker_obj, SPEAKER_SCHEMA_NAME, SPEAKER_PROOF_KIND, "speaker_proof")
        if speaker_obj["dialogue_contract_sha256"] != contract_binding.sha256:
            raise InvalidInputError("speaker_proof dialogue_contract_sha256 mismatch")
        if speaker_obj["voice_profile_sha256"] != voice_binding.sha256:
            raise InvalidInputError("speaker_proof voice_profile_sha256 mismatch")
        line_results = speaker_obj.get("line_results")
        if not isinstance(line_results, list):
            raise InvalidInputError("speaker_proof.line_results must be an array")
        seen: set[str] = set()
        for idx, entry in enumerate(line_results):
            if not isinstance(entry, dict):
                raise InvalidInputError(f"speaker_proof.line_results[{idx}] must be object")
            _expect_exact_keys(entry, SPEAKER_LINE_KEYS, f"speaker_proof.line_results[{idx}]")
            line_id = _expect_non_empty_string(entry["line_id"], f"speaker line {idx} line_id")
            if line_id not in line_id_set:
                raise InvalidInputError(f"speaker_proof references unknown line_id: {line_id}")
            if line_id in seen:
                raise InvalidInputError(f"speaker_proof duplicate line_id: {line_id}")
            seen.add(line_id)
            if entry["audio_sha256"] != line_bindings[line_id].sha256:
                raise InvalidInputError(f"speaker_proof audio hash mismatch for line {line_id}")
            if entry["character_id"] != expected_lines[line_id]["character_id"]:
                speaker_blockers.append(f"speaker proof character mismatch for line {line_id}")
            if entry["voice_profile_id"] != expected_lines[line_id]["voice_profile_id"]:
                speaker_blockers.append(f"speaker proof profile mismatch for line {line_id}")
            similarity = _expect_ratio_0_1(entry["speaker_similarity"], f"speaker line {line_id} similarity")
            if similarity < thresholds["min_speaker_similarity"]:
                speaker_blockers.append(f"speaker similarity below threshold for line {line_id}")
            continuity = entry["continuity_with_previous"]
            if continuity is not None:
                continuity_value = _expect_ratio_0_1(continuity, f"speaker line {line_id} continuity")
                if continuity_value < thresholds["min_cross_line_continuity"]:
                    speaker_blockers.append(f"cross-line continuity below threshold for line {line_id}")
        for missing_line in sorted(line_id_set - seen):
            speaker_blockers.append(f"speaker_proof missing line {missing_line}")
        speaker_status = PASS if not speaker_blockers else FAIL
    gates["voice_continuity"] = _make_gate_result(
        speaker_status,
        speaker_blockers,
        [contract_binding.sha256, voice_binding.sha256]
        + ([proof_bindings["speaker_proof"].sha256] if proof_bindings["speaker_proof"] else []),
    )

    emotion_blockers: list[str] = []
    emotion_targets_required = dialogue_contract_version == 1 or any(
        line.get("emotion_class") not in {None, "unspecified"} for line in expected_lines.values()
    )
    if proof_bindings["emotion_proof"] is None and not emotion_targets_required:
        emotion_status = PASS
    elif proof_bindings["emotion_proof"] is None:
        emotion_status = BLOCKED
        emotion_blockers.append("missing emotion_proof")
    else:
        emotion_obj = _load_json(proof_bindings["emotion_proof"].path)
        if not isinstance(emotion_obj, dict):
            raise InvalidInputError("emotion_proof must be an object")
        _expect_exact_keys(emotion_obj, EMOTION_PROOF_KEYS, "emotion_proof")
        _expect_proof_header(emotion_obj, EMOTION_SCHEMA_NAME, EMOTION_PROOF_KIND, "emotion_proof")
        if emotion_obj["dialogue_contract_sha256"] != contract_binding.sha256:
            raise InvalidInputError("emotion_proof dialogue_contract_sha256 mismatch")
        if emotion_obj["voice_profile_sha256"] != voice_binding.sha256:
            raise InvalidInputError("emotion_proof voice_profile_sha256 mismatch")
        line_results = emotion_obj.get("line_results")
        if not isinstance(line_results, list):
            raise InvalidInputError("emotion_proof.line_results must be an array")
        seen: set[str] = set()
        for idx, entry in enumerate(line_results):
            if not isinstance(entry, dict):
                raise InvalidInputError(f"emotion_proof.line_results[{idx}] must be object")
            _expect_exact_keys(entry, EMOTION_LINE_KEYS, f"emotion_proof.line_results[{idx}]")
            line_id = _expect_non_empty_string(entry["line_id"], f"emotion line {idx} line_id")
            if line_id not in line_id_set:
                raise InvalidInputError(f"emotion_proof references unknown line_id: {line_id}")
            if line_id in seen:
                raise InvalidInputError(f"emotion_proof duplicate line_id: {line_id}")
            seen.add(line_id)
            if entry["audio_sha256"] != line_bindings[line_id].sha256:
                raise InvalidInputError(f"emotion_proof audio hash mismatch for line {line_id}")
            predicted_emotion = _expect_non_empty_string(entry["predicted_emotion"], "predicted_emotion")
            _expect_non_empty_string(entry["predicted_intensity"], "predicted_intensity")
            if dialogue_contract_version == 1:
                if predicted_emotion != expected_lines[line_id]["emotion"]:
                    emotion_blockers.append(f"emotion label mismatch for line {line_id}")
                if entry["predicted_intensity"] != expected_lines[line_id]["intensity"]:
                    emotion_blockers.append(f"intensity label mismatch for line {line_id}")
            else:
                expected_emotion = expected_lines[line_id]["emotion_class"]
                if expected_emotion not in {None, "unspecified"} and predicted_emotion != expected_emotion:
                    emotion_blockers.append(f"emotion label mismatch for line {line_id}")
            confidence = _expect_ratio_0_1(entry["emotion_confidence"], "emotion_confidence")
            intensity_score = _expect_ratio_0_1(entry["intensity_score"], "intensity_score")
            if (dialogue_contract_version == 1 or expected_lines[line_id].get("emotion_class") not in {None, "unspecified"}) and confidence < thresholds["min_emotion_confidence"]:
                emotion_blockers.append(f"emotion confidence below threshold for line {line_id}")
            if dialogue_contract_version == 1 and intensity_score < thresholds["min_intensity_score"]:
                emotion_blockers.append(f"intensity score below threshold for line {line_id}")
        for missing_line in sorted(line_id_set - seen):
            emotion_blockers.append(f"emotion_proof missing line {missing_line}")
        emotion_status = PASS if not emotion_blockers else FAIL
    gates["emotional_tone"] = _make_gate_result(
        emotion_status,
        emotion_blockers,
        [contract_binding.sha256, voice_binding.sha256]
        + ([proof_bindings["emotion_proof"].sha256] if proof_bindings["emotion_proof"] else []),
    )

    playback_blockers: list[str] = []
    if proof_bindings["playback_review_proof"] is None:
        playback_status = BLOCKED
        playback_blockers.append("missing playback_review_proof")
    else:
        playback_obj = _load_json(proof_bindings["playback_review_proof"].path)
        if not isinstance(playback_obj, dict):
            raise InvalidInputError("playback_review_proof must be an object")
        _expect_exact_keys(playback_obj, PLAYBACK_PROOF_KEYS, "playback_review_proof")
        _expect_proof_header(playback_obj, PLAYBACK_SCHEMA_NAME, PLAYBACK_PROOF_KIND, "playback_review_proof")
        for field in ("review_method", "reviewer_id"):
            _expect_non_empty_string(playback_obj.get(field), f"playback_review_proof.{field}")
        if playback_obj["dialogue_contract_sha256"] != contract_binding.sha256:
            raise InvalidInputError("playback_review_proof dialogue_contract_sha256 mismatch")
        if playback_obj["voice_profile_sha256"] != voice_binding.sha256:
            raise InvalidInputError("playback_review_proof voice_profile_sha256 mismatch")
        _validate_exact_line_audio_bindings(
            playback_obj.get("line_audio_bindings"),
            "playback_review_proof.line_audio_bindings",
            all_line_ids,
            line_bindings,
        )
        for key in ("voice_identity", "intelligibility", "timing", "emotional_tone", "continuity", "noise_free", "clipping_free"):
            value = playback_obj.get(key)
            if not isinstance(value, bool):
                raise InvalidInputError(f"playback_review_proof.{key} must be boolean")
            if value is not True:
                playback_blockers.append(f"playback review predicate failed: {key}")
        for metric in audio_metrics:
            line_id = metric["line_id"]
            if metric["rms_ratio"] < thresholds["min_rms_ratio"]:
                playback_blockers.append(f"line {line_id} rms ratio below threshold")
            if metric["silence_ratio"] > thresholds["max_silence_ratio"]:
                playback_blockers.append(f"line {line_id} silence ratio exceeds threshold")
            if metric["clipping_ratio"] > thresholds["max_clipping_ratio"]:
                playback_blockers.append(f"line {line_id} clipping ratio exceeds threshold")
        playback_status = PASS if not playback_blockers else FAIL
    gates["audio_review_record"] = _make_gate_result(
        playback_status,
        playback_blockers,
        [contract_binding.sha256, voice_binding.sha256]
        + [entry["sha256"] for entry in audio_metrics]
        + ([proof_bindings["playback_review_proof"].sha256] if proof_bindings["playback_review_proof"] else []),
    )

    runtime_blockers: list[str] = []
    if proof_bindings["production_runtime_proof"] is None:
        runtime_status = BLOCKED
        runtime_blockers.append("missing production_runtime_proof")
    else:
        runtime_obj = _load_json(proof_bindings["production_runtime_proof"].path)
        if not isinstance(runtime_obj, dict):
            raise InvalidInputError("production_runtime_proof must be object")
        _expect_exact_keys(runtime_obj, RUNTIME_PROOF_KEYS, "production_runtime_proof")
        _expect_proof_header(runtime_obj, RUNTIME_SCHEMA_NAME, RUNTIME_PROOF_KIND, "production_runtime_proof")
        if runtime_obj["dialogue_contract_sha256"] != contract_binding.sha256:
            raise InvalidInputError("production_runtime_proof dialogue_contract_sha256 mismatch")
        if runtime_obj["voice_profile_sha256"] != voice_binding.sha256:
            raise InvalidInputError("production_runtime_proof voice_profile_sha256 mismatch")
        _validate_exact_line_audio_bindings(
            runtime_obj.get("line_audio_bindings"),
            "production_runtime_proof.line_audio_bindings",
            all_line_ids,
            line_bindings,
        )
        for key in ("runtime_executed", "decode_succeeded"):
            value = runtime_obj.get(key)
            if value is not True:
                runtime_blockers.append(f"production_runtime_proof boolean failed: {key}")
        runtime_status = PASS if not runtime_blockers else FAIL
    if is_synthetic:
        runtime_status = BLOCKED
        runtime_blockers.append("synthetic input cannot satisfy production runtime proof gate")
    gates["production_runtime_proof"] = _make_gate_result(
        runtime_status,
        runtime_blockers,
        [contract_binding.sha256, voice_binding.sha256]
        + ([proof_bindings["production_runtime_proof"].sha256] if proof_bindings["production_runtime_proof"] else []),
    )

    authority_blockers: list[str] = []
    bundle_binding = proof_bindings["production_proof_bundle_binding"]
    if is_synthetic:
        authority_status = BLOCKED
        authority_blockers.append("synthetic input cannot satisfy production proof authority gate")
    elif bundle_binding is None:
        authority_status = BLOCKED
        authority_blockers.append("missing production_proof_bundle_binding")
    else:
        bundle_obj = _load_json(bundle_binding.path)
        if not isinstance(bundle_obj, dict):
            raise InvalidInputError("production proof bundle must be object")
        _expect_exact_keys(bundle_obj, PROOF_BUNDLE_KEYS, "production_proof_bundle")
        if bundle_obj.get("schema_name") != PROOF_BUNDLE_SCHEMA_NAME:
            raise InvalidInputError("production_proof_bundle.schema_name mismatch")
        if bundle_obj.get("proof_kind") != PROOF_BUNDLE_KIND:
            raise InvalidInputError("production_proof_bundle.proof_kind mismatch")
        if bundle_obj.get("bundle_version") != 1:
            raise InvalidInputError("production_proof_bundle.bundle_version must be 1")
        bundle_id = _expect_non_empty_string(bundle_obj.get("bundle_id"), "production_proof_bundle.bundle_id")
        authority_id = _expect_non_empty_string(bundle_obj.get("authority_id"), "production_proof_bundle.authority_id")
        if _expect_non_empty_string(bundle_obj.get("run_id"), "production_proof_bundle.run_id") != run_id:
            raise InvalidInputError("production_proof_bundle.run_id mismatch")
        if bundle_obj.get("is_synthetic") is not False:
            raise InvalidInputError("production_proof_bundle.is_synthetic must be false")
        if bundle_obj.get("dialogue_contract_sha256") != contract_binding.sha256:
            raise InvalidInputError("production_proof_bundle dialogue_contract_sha256 mismatch")
        if bundle_obj.get("voice_profile_sha256") != voice_binding.sha256:
            raise InvalidInputError("production_proof_bundle voice_profile_sha256 mismatch")
        _validate_exact_line_audio_bindings(
            bundle_obj.get("line_audio_bindings"),
            "production_proof_bundle.line_audio_bindings",
            all_line_ids,
            line_bindings,
        )
        required_proof_shas = {
            "asr_proof_sha256": proof_bindings["asr_proof"],
            "speaker_proof_sha256": proof_bindings["speaker_proof"],
            "emotion_proof_sha256": proof_bindings["emotion_proof"],
            "playback_review_proof_sha256": proof_bindings["playback_review_proof"],
            "production_runtime_proof_sha256": proof_bindings["production_runtime_proof"],
        }
        for field, binding in required_proof_shas.items():
            expected_sha = _expect_sha256(bundle_obj.get(field), f"production_proof_bundle.{field}")
            if binding is None:
                authority_blockers.append(f"{field} requires corresponding proof binding")
                continue
            if expected_sha != binding.sha256:
                authority_blockers.append(f"production proof bundle mismatch for {field}")
        matching = [
            entry
            for entry in approved_registry_entries
            if entry["bundle_id"] == bundle_id
            and entry["authority_id"] == authority_id
            and entry["proof_bundle_sha256"] == bundle_binding.sha256
        ]
        if not matching:
            authority_blockers.append("production proof bundle not allowlisted in authority registry")
        elif any(entry["revoked"] for entry in matching):
            authority_blockers.append("production proof bundle is revoked in authority registry")
        authority_status = PASS if not authority_blockers else BLOCKED
    gates["production_proof_authority"] = _make_gate_result(
        authority_status,
        authority_blockers,
        [authority_registry_binding.sha256] + ([bundle_binding.sha256] if bundle_binding else []),
    )

    for gate_name in (
        "voice_profile_match",
        "dialogue_timing",
        "intelligibility_score",
        "emotional_tone",
        "voice_continuity",
        "audio_review_record",
        "production_runtime_proof",
        "production_proof_authority",
    ):
        blockers.extend(gates[gate_name]["blockers"])

    if is_synthetic:
        blockers.append("synthetic input cannot pass overall gate")

    non_overall_statuses = [gates[name]["status"] for name in GATE_NAMES if name != "overall_pass"]
    if not is_synthetic and all(status == PASS for status in non_overall_statuses):
        overall_status = PASS
        overall_pass = True
    elif any(status == FAIL for status in non_overall_statuses):
        overall_status = FAIL
        overall_pass = False
    else:
        overall_status = BLOCKED
        overall_pass = False
    gates["overall_pass"] = _make_gate_result(overall_status, sorted(set(blockers)), [request_binding.sha256])

    normalized_wer = min(1.0, total_distance / float(max(1, expected_token_count)))
    evidence = {
        "schema_name": "wave30_voice_dialogue_continuity_evidence",
        "evidence_version": 1,
        "run_id": run_id,
        "is_synthetic": is_synthetic,
        "request_binding": {"path": str(request_binding.path), "sha256": request_binding.sha256},
        "artifact_bindings": {
            "voice_profile": {"path": str(voice_binding.path), "sha256": voice_binding.sha256},
            "dialogue_contract": {"path": str(contract_binding.path), "sha256": contract_binding.sha256},
            "line_audio": [
                {
                    "line_id": entry["line_id"],
                    "path": entry["path"],
                    "sha256": entry["sha256"],
                    "bytes": entry["bytes"],
                }
                for entry in audio_metrics
            ],
            "proofs": {
                "asr_proof": _binding_to_dict(proof_bindings["asr_proof"]),
                "speaker_proof": _binding_to_dict(proof_bindings["speaker_proof"]),
                "emotion_proof": _binding_to_dict(proof_bindings["emotion_proof"]),
                "playback_review_proof": _binding_to_dict(proof_bindings["playback_review_proof"]),
                "production_runtime_proof": _binding_to_dict(proof_bindings["production_runtime_proof"]),
                "production_proof_bundle_binding": _binding_to_dict(proof_bindings["production_proof_bundle_binding"]),
                "authority_registry": _binding_to_dict(authority_registry_binding),
            },
        },
        "metrics": {
            "line_count": len(all_line_ids),
            "normalized_wer": round(normalized_wer, 6),
            "empty_expected_line_count": empty_expected_lines,
            "empty_asr_line_count": empty_asr_lines,
            "line_audio_metrics": audio_metrics,
        },
        "gates": gates,
        "blockers": sorted(set(blockers)),
        "overall_pass": overall_pass,
    }
    _validate_schema(evidence, evidence_schema, "evidence")
    _write_json_atomic(output_path, evidence)
    return 0 if overall_pass else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()

    try:
        requested_root = Path(args.root).resolve()
        if requested_root != CANONICAL_ROOT:
            raise InvalidInputError(
                f"root must match canonical project root ({CANONICAL_ROOT}); got {requested_root}"
            )
        root = CANONICAL_ROOT
        request = _resolve_under_root(root, args.input, "input")
        output = _resolve_under_root(root, args.output, "output")
        return evaluate(root=root, request_path=request, output_path=output)
    except InvalidInputError as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive fail-safe
        print(f"ERROR: unexpected evaluator failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
