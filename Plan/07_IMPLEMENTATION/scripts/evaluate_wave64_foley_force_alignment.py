#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

SHA256_RE = r"^[0-9a-f]{64}$"
GATE_NAMES = (
    "event_binding_check",
    "frame_to_audio_alignment",
    "foley_presence",
    "false_event_reject",
    "av_event_alignment_review",
    "production_runtime_proof",
    "production_alignment_authority",
    "overall_pass",
)

DEFAULT_THRESHOLDS: dict[str, float | int] = {
    "min_force_confidence": 0.7,
    "max_frame_drift": 2,
    "max_seconds_drift": 0.08,
    "max_wav_duration_drift_seconds": 0.05,
    "max_clipping_ratio": 0.0003,
    "min_rms_ratio": 0.005,
}
FRAME_RATE_TOLERANCE = 0.000001
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VISUAL_TAKE_MEDIA_TYPES = {"image/png": ".png"}
CONTACT_EVIDENCE_MEDIA_TYPES = {"application/json": ".json"}
SYNTHETIC_ORIGINS = {"synthetic", "synthetic_fixture", "fixture", "generated", "simulated"}
NON_SYNTHETIC_ORIGINS = {"captured_live", "recorded_live", "production_capture", "live_capture"}
CONTACT_AUTHORITY_SCOPES = {"body", "contact", "body_contact", "non_body_contact"}
CONTACT_AUTHORITY_GOLD_MASK_STATUSES = {"cleared", "missing", "not_applicable"}
CONTACT_AUTHORITY_CLASSES = {"gold_mask_validated", "deterministic_parser", "manual_review"}

CANONICAL_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_foley_force_alignment_request.schema.json")
REPORT_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave64_foley_force_alignment_report.schema.json")
WAVE30_SCHEMA_RELATIVE = Path("Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json")
AUTHORITY_REGISTRY_RELATIVE = Path("Plan/10_REGISTRIES/wave64_foley_force_alignment_authority_registry.json")


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


def _expect_exact_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(keys - observed)
    extra = sorted(observed - keys)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"unknown={','.join(extra)}")
        raise InvalidInputError(f"{label} key mismatch ({'; '.join(parts)})")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_allowed_string(value: Any, label: str, allowed: set[str]) -> str:
    text = _expect_non_empty_string(value, label)
    if text not in allowed:
        choices = ", ".join(sorted(allowed))
        raise InvalidInputError(f"{label} must be one of: {choices}")
    return text


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInputError(f"{label} must be boolean")
    return bool(value)


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_non_empty_string(value, label)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise InvalidInputError(f"{label} must be lowercase SHA-256")
    return sha


def _expect_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise InvalidInputError(f"{label} must be >= {minimum}")
    return value


def _expect_finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise InvalidInputError(f"{label} must be finite")
    return as_float


def _expect_ratio(value: Any, label: str) -> float:
    ratio = _expect_finite_number(value, label)
    if ratio < 0.0 or ratio > 1.0:
        raise InvalidInputError(f"{label} must be in [0, 1]")
    return ratio


def _validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.path)
        raise InvalidInputError(f"{label} schema validation failed at {where}: {first.message}")


def _resolve_under_root(root: Path, candidate: str, label: str) -> Path:
    raw = Path(candidate)
    resolved = (raw if raw.is_absolute() else (root / raw)).resolve()
    if not resolved.is_relative_to(root):
        raise InvalidInputError(f"{label} escapes root: {resolved}")
    return resolved


def _validate_binding(root: Path, payload: Any, label: str) -> Binding:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256"}, label)
    path = _resolve_under_root(root, _expect_non_empty_string(payload["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(payload["sha256"], f"{label}.sha256")
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed = _sha256_of(path)
    if observed != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed})")
    return Binding(path=path, sha256=sha)


def _validate_path_sha_bytes(root: Path, payload: Any, label: str, *, exact_keys: bool = True) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    if exact_keys:
        _expect_exact_keys(payload, {"path", "sha256", "bytes"}, label)
    else:
        required = {"path", "sha256", "bytes"}
        missing = sorted(required - set(payload.keys()))
        if missing:
            raise InvalidInputError(f"{label} missing required keys: {','.join(missing)}")
    path = _resolve_under_root(root, _expect_non_empty_string(payload["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(payload["sha256"], f"{label}.sha256")
    declared_bytes = _expect_int(payload["bytes"], f"{label}.bytes", minimum=1)
    if not path.is_file():
        raise InvalidInputError(f"{label}.path does not exist: {path}")
    observed_bytes = path.stat().st_size
    if declared_bytes != observed_bytes:
        raise InvalidInputError(f"{label}.bytes mismatch ({declared_bytes} != {observed_bytes})")
    observed_sha = _sha256_of(path)
    if observed_sha != sha:
        raise InvalidInputError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return {"path": path, "sha256": sha, "bytes": declared_bytes}


def _validate_visual_take_artifact(root: Path, payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256", "bytes", "media_type"}, label)
    validated = _validate_path_sha_bytes(root, payload, label, exact_keys=False)
    media_type = _expect_allowed_string(payload["media_type"], f"{label}.media_type", set(VISUAL_TAKE_MEDIA_TYPES.keys()))
    expected_suffix = VISUAL_TAKE_MEDIA_TYPES[media_type]
    if Path(validated["path"]).suffix.lower() != expected_suffix:
        raise InvalidInputError(f"{label}.path extension must be {expected_suffix} for media_type {media_type}")
    signature = Path(validated["path"]).read_bytes()[: len(PNG_SIGNATURE)]
    if media_type == "image/png" and signature != PNG_SIGNATURE:
        raise InvalidInputError(f"{label} does not match PNG signature")
    validated["media_type"] = media_type
    return validated


def _validate_contact_evidence_artifact(root: Path, payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{label} must be an object")
    _expect_exact_keys(payload, {"path", "sha256", "bytes", "media_type"}, label)
    validated = _validate_path_sha_bytes(root, payload, label, exact_keys=False)
    media_type = _expect_allowed_string(payload["media_type"], f"{label}.media_type", set(CONTACT_EVIDENCE_MEDIA_TYPES.keys()))
    expected_suffix = CONTACT_EVIDENCE_MEDIA_TYPES[media_type]
    if Path(validated["path"]).suffix.lower() != expected_suffix:
        raise InvalidInputError(f"{label}.path extension must be {expected_suffix} for media_type {media_type}")
    evidence_bytes = Path(validated["path"]).read_bytes()
    if media_type == "application/json":
        try:
            parsed = json.loads(evidence_bytes.decode("utf-8"), parse_constant=_reject_nonfinite_json)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidInputError(f"{label} must contain valid UTF-8 JSON") from exc
        if not isinstance(parsed, (dict, list)):
            raise InvalidInputError(f"{label} JSON payload must be an object or array")
    validated["media_type"] = media_type
    return validated


def _classify_synthetic_origin(value: Any, label: str) -> bool:
    origin = _expect_non_empty_string(value, label).lower()
    if origin in SYNTHETIC_ORIGINS:
        return True
    if origin in NON_SYNTHETIC_ORIGINS:
        return False
    allowed = ", ".join(sorted(SYNTHETIC_ORIGINS | NON_SYNTHETIC_ORIGINS))
    raise InvalidInputError(f"{label} is unknown ({origin}); allowed values: {allowed}")


def _decode_pcm_samples(payload: bytes, sample_width: int) -> tuple[int, int, float]:
    if sample_width == 1:
        max_value = 127
        clipping = 0
        sum_squares = 0.0
        for raw in payload:
            sample = raw - 128
            level = abs(sample)
            if level >= max_value:
                clipping += 1
            sum_squares += float(sample * sample)
        return clipping, max_value, sum_squares
    if sample_width == 2:
        max_value = 32767
        clipping = 0
        sum_squares = 0.0
        for (sample,) in struct.iter_unpack("<h", payload):
            level = abs(sample)
            if level >= max_value:
                clipping += 1
            sum_squares += float(sample * sample)
        return clipping, max_value, sum_squares
    if sample_width == 3:
        max_value = (1 << 23) - 1
        clipping = 0
        sum_squares = 0.0
        for idx in range(0, len(payload), 3):
            chunk = payload[idx : idx + 3]
            sample = int.from_bytes(chunk + (b"\xff" if chunk[2] & 0x80 else b"\x00"), "little", signed=True)
            level = abs(sample)
            if level >= max_value:
                clipping += 1
            sum_squares += float(sample * sample)
        return clipping, max_value, sum_squares
    if sample_width == 4:
        max_value = (1 << 31) - 1
        clipping = 0
        sum_squares = 0.0
        for (sample,) in struct.iter_unpack("<i", payload):
            level = abs(sample)
            if level >= max_value:
                clipping += 1
            sum_squares += float(sample * sample)
        return clipping, max_value, sum_squares
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
    clipping_count, max_possible, sum_squares = _decode_pcm_samples(payload, sample_width)
    sample_total = frame_count * channels
    rms_ratio = 0.0 if sample_total <= 0 else min(1.0, math.sqrt(sum_squares / float(sample_total)) / float(max_possible))
    clipping_ratio = 0.0 if sample_total <= 0 else clipping_count / float(sample_total)
    return {
        "duration_seconds": frame_count / float(sample_rate),
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "channels": channels,
        "frame_count": frame_count,
        "rms_ratio": round(float(rms_ratio), 6),
        "clipping_ratio": round(float(clipping_ratio), 6),
    }


def _make_gate(status: str, blockers: list[str], artifact_bindings: list[str]) -> dict[str, Any]:
    if status == PASS and blockers:
        raise InvalidInputError("internal gate invariant: PASS gate cannot contain blockers")
    return {"status": status, "blockers": blockers, "artifact_bindings": artifact_bindings}


def _binding_or_none(binding: Binding | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    return {"path": str(binding.path), "sha256": binding.sha256}


def _sort_pair(a: str, b: str) -> str:
    left = _expect_non_empty_string(a, "material").lower()
    right = _expect_non_empty_string(b, "material").lower()
    return "|".join(sorted([left, right]))


def _validate_registry(registry_obj: Any) -> dict[str, Any]:
    if not isinstance(registry_obj, dict):
        raise InvalidInputError("authority registry must be an object")
    _expect_exact_keys(
        registry_obj,
        {
            "schema_name",
            "registry_version",
            "visual_intensity_taxonomy",
            "force_profiles",
            "material_pair_rules",
            "body_contact_materials",
            "allowed_foley_layers",
            "sync_tolerances",
            "approved_alignment_bundles",
        },
        "authority_registry",
    )
    if registry_obj["schema_name"] != "wave64_foley_force_alignment_authority_registry":
        raise InvalidInputError("authority_registry.schema_name mismatch")
    if registry_obj["registry_version"] != 1:
        raise InvalidInputError("authority_registry.registry_version must be 1")
    visual_taxonomy = registry_obj["visual_intensity_taxonomy"]
    if not isinstance(visual_taxonomy, dict) or not visual_taxonomy:
        raise InvalidInputError("authority_registry.visual_intensity_taxonomy must be a non-empty object")
    for key, values in visual_taxonomy.items():
        _expect_non_empty_string(key, "authority_registry.visual_intensity_taxonomy key")
        if not isinstance(values, list) or not values:
            raise InvalidInputError(f"visual_intensity_taxonomy.{key} must be a non-empty array")
        for idx, item in enumerate(values):
            _expect_non_empty_string(item, f"visual_intensity_taxonomy.{key}[{idx}]")

    force_profiles = registry_obj["force_profiles"]
    if not isinstance(force_profiles, dict) or not force_profiles:
        raise InvalidInputError("authority_registry.force_profiles must be a non-empty object")
    for force_class, profile in force_profiles.items():
        _expect_non_empty_string(force_class, "authority_registry.force_profiles key")
        if not isinstance(profile, dict):
            raise InvalidInputError(f"force_profiles.{force_class} must be an object")
        _expect_exact_keys(
            profile,
            {
                "allowed_loudness_hints",
                "normalized_pcm_rms_range",
                "maximum_clipping_ratio",
                "allowed_foley_families",
            },
            f"force_profiles.{force_class}",
        )
        hints = profile["allowed_loudness_hints"]
        if not isinstance(hints, list) or not hints:
            raise InvalidInputError(f"force_profiles.{force_class}.allowed_loudness_hints must be non-empty array")
        for idx, item in enumerate(hints):
            _expect_non_empty_string(item, f"force_profiles.{force_class}.allowed_loudness_hints[{idx}]")
        rms = profile["normalized_pcm_rms_range"]
        if not isinstance(rms, list) or len(rms) != 2:
            raise InvalidInputError(f"force_profiles.{force_class}.normalized_pcm_rms_range must contain two values")
        rms_low = _expect_ratio(rms[0], f"force_profiles.{force_class}.normalized_pcm_rms_range[0]")
        rms_high = _expect_ratio(rms[1], f"force_profiles.{force_class}.normalized_pcm_rms_range[1]")
        if rms_high < rms_low:
            raise InvalidInputError(f"force_profiles.{force_class}.normalized_pcm_rms_range must be ascending")
        _expect_ratio(profile["maximum_clipping_ratio"], f"force_profiles.{force_class}.maximum_clipping_ratio")
        families = profile["allowed_foley_families"]
        if not isinstance(families, list) or not families:
            raise InvalidInputError(f"force_profiles.{force_class}.allowed_foley_families must be non-empty array")
        for idx, item in enumerate(families):
            _expect_non_empty_string(item, f"force_profiles.{force_class}.allowed_foley_families[{idx}]")

    pair_rules = registry_obj["material_pair_rules"]
    if not isinstance(pair_rules, list):
        raise InvalidInputError("authority_registry.material_pair_rules must be an array")
    normalized_pair_rules: dict[str, str] = {}
    for idx, item in enumerate(pair_rules):
        if not isinstance(item, dict):
            raise InvalidInputError(f"material_pair_rules[{idx}] must be an object")
        _expect_exact_keys(
            item,
            {"source_material", "target_material", "expected_foley_family"},
            f"material_pair_rules[{idx}]",
        )
        key = _sort_pair(item["source_material"], item["target_material"])
        family = _expect_non_empty_string(item["expected_foley_family"], f"material_pair_rules[{idx}].expected_foley_family")
        if key in normalized_pair_rules and normalized_pair_rules[key] != family:
            raise InvalidInputError(f"material_pair_rules conflict for pair {key}")
        normalized_pair_rules[key] = family

    body_contact_materials = registry_obj["body_contact_materials"]
    if not isinstance(body_contact_materials, list) or not body_contact_materials:
        raise InvalidInputError("authority_registry.body_contact_materials must be a non-empty array")
    normalized_body_contact_materials = {
        _expect_non_empty_string(item, "body_contact_materials[]").lower()
        for item in body_contact_materials
    }
    if len(normalized_body_contact_materials) != len(body_contact_materials):
        raise InvalidInputError("authority_registry.body_contact_materials must be unique")

    layers = registry_obj["allowed_foley_layers"]
    if not isinstance(layers, list) or not layers:
        raise InvalidInputError("authority_registry.allowed_foley_layers must be a non-empty array")
    allowed_layers = [_expect_non_empty_string(item, "allowed_foley_layers[]") for item in layers]

    sync = registry_obj["sync_tolerances"]
    if not isinstance(sync, dict):
        raise InvalidInputError("authority_registry.sync_tolerances must be an object")
    _expect_exact_keys(sync, {"max_frame_drift", "max_seconds_drift", "max_wav_duration_drift_seconds"}, "sync_tolerances")
    max_frame_drift = _expect_int(sync["max_frame_drift"], "sync_tolerances.max_frame_drift", minimum=0)
    max_seconds_drift = _expect_finite_number(sync["max_seconds_drift"], "sync_tolerances.max_seconds_drift")
    max_wav_duration_drift_seconds = _expect_finite_number(
        sync["max_wav_duration_drift_seconds"], "sync_tolerances.max_wav_duration_drift_seconds"
    )
    if max_seconds_drift < 0.0 or max_wav_duration_drift_seconds < 0.0:
        raise InvalidInputError("authority_registry.sync_tolerances values must be non-negative")

    approved = registry_obj["approved_alignment_bundles"]
    if not isinstance(approved, list):
        raise InvalidInputError("authority_registry.approved_alignment_bundles must be an array")
    approved_entries: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for idx, entry in enumerate(approved):
        if not isinstance(entry, dict):
            raise InvalidInputError(f"approved_alignment_bundles[{idx}] must be an object")
        _expect_exact_keys(entry, {"bundle_id", "authority_id", "bundle_sha256", "revoked"}, f"approved_alignment_bundles[{idx}]")
        bundle_id = _expect_non_empty_string(entry["bundle_id"], f"approved_alignment_bundles[{idx}].bundle_id")
        authority_id = _expect_non_empty_string(entry["authority_id"], f"approved_alignment_bundles[{idx}].authority_id")
        bundle_sha = _expect_sha256(entry["bundle_sha256"], f"approved_alignment_bundles[{idx}].bundle_sha256")
        revoked = _expect_bool(entry["revoked"], f"approved_alignment_bundles[{idx}].revoked")
        key = (bundle_id, authority_id, bundle_sha)
        if key in seen_keys:
            raise InvalidInputError("duplicate approved alignment bundle entry")
        seen_keys.add(key)
        approved_entries.append(
            {"bundle_id": bundle_id, "authority_id": authority_id, "bundle_sha256": bundle_sha, "revoked": revoked}
        )

    return {
        "visual_intensity_taxonomy": {k.lower(): [v.lower() for v in vals] for k, vals in visual_taxonomy.items()},
        "force_profiles": force_profiles,
        "material_pair_rules": normalized_pair_rules,
        "body_contact_materials": normalized_body_contact_materials,
        "allowed_foley_layers": set(allowed_layers),
        "sync_tolerances": {
            "max_frame_drift": max_frame_drift,
            "max_seconds_drift": max_seconds_drift,
            "max_wav_duration_drift_seconds": max_wav_duration_drift_seconds,
        },
        "approved_alignment_bundles": approved_entries,
    }


def _validate_visual_manifest(
    root: Path,
    payload: Any,
    body_contact_materials: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("visual_contact_manifest must be an object")
    _expect_exact_keys(
        payload,
        {
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "frame_rate",
            "frame_time_origin_seconds",
            "visual_take_artifact",
            "contact_evidence_artifact",
            "contact_authority",
            "contact_edges",
        },
        "visual_contact_manifest",
    )
    visual_take = _validate_visual_take_artifact(root, payload["visual_take_artifact"], "visual_contact_manifest.visual_take_artifact")
    contact_evidence = _validate_contact_evidence_artifact(
        root, payload["contact_evidence_artifact"], "visual_contact_manifest.contact_evidence_artifact"
    )
    contact_authority = payload["contact_authority"]
    if not isinstance(contact_authority, dict):
        raise InvalidInputError("visual_contact_manifest.contact_authority must be an object")
    _expect_exact_keys(
        contact_authority,
        {"authority_scope", "gold_mask_dependency_status", "evidence_authority_class", "production_trust_claim"},
        "visual_contact_manifest.contact_authority",
    )
    frame_rate = _expect_finite_number(payload["frame_rate"], "visual_contact_manifest.frame_rate")
    if frame_rate <= 0.0:
        raise InvalidInputError("visual_contact_manifest.frame_rate must be > 0")
    _expect_finite_number(payload["frame_time_origin_seconds"], "visual_contact_manifest.frame_time_origin_seconds")
    edges = payload["contact_edges"]
    if not isinstance(edges, list):
        raise InvalidInputError("visual_contact_manifest.contact_edges must be an array")
    normalized_edges: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise InvalidInputError(f"contact_edges[{idx}] must be an object")
        _expect_exact_keys(
            edge,
            {
                "contact_edge_id",
                "source_entity_id",
                "target_entity_id",
                "source_owner_id",
                "target_owner_id",
                "source_material",
                "target_material",
                "visual_force_intensity",
                "start_frame",
                "end_frame",
                "audio_expected",
                "min_expected_force_events",
                "max_expected_force_events",
            },
            f"contact_edges[{idx}]",
        )
        edge_id = _expect_non_empty_string(edge["contact_edge_id"], f"contact_edges[{idx}].contact_edge_id")
        if edge_id in seen_ids:
            raise InvalidInputError(f"duplicate contact_edge_id: {edge_id}")
        seen_ids.add(edge_id)
        start_frame = _expect_int(edge["start_frame"], f"contact_edges[{idx}].start_frame", minimum=0)
        end_frame = _expect_int(edge["end_frame"], f"contact_edges[{idx}].end_frame", minimum=0)
        if end_frame < start_frame:
            raise InvalidInputError(f"contact_edges[{idx}] end_frame must be >= start_frame")
        min_events = _expect_int(edge["min_expected_force_events"], f"contact_edges[{idx}].min_expected_force_events", minimum=0)
        max_events = _expect_int(edge["max_expected_force_events"], f"contact_edges[{idx}].max_expected_force_events", minimum=0)
        if max_events < min_events:
            raise InvalidInputError(f"contact_edges[{idx}] max_expected_force_events must be >= min_expected_force_events")
        normalized_edges.append(
            {
                "contact_edge_id": edge_id,
                "source_entity_id": _expect_non_empty_string(edge["source_entity_id"], f"contact_edges[{idx}].source_entity_id"),
                "target_entity_id": _expect_non_empty_string(edge["target_entity_id"], f"contact_edges[{idx}].target_entity_id"),
                "source_owner_id": _expect_non_empty_string(edge["source_owner_id"], f"contact_edges[{idx}].source_owner_id"),
                "target_owner_id": _expect_non_empty_string(edge["target_owner_id"], f"contact_edges[{idx}].target_owner_id"),
                "source_material": _expect_non_empty_string(edge["source_material"], f"contact_edges[{idx}].source_material"),
                "target_material": _expect_non_empty_string(edge["target_material"], f"contact_edges[{idx}].target_material"),
                "visual_force_intensity": _expect_non_empty_string(
                    edge["visual_force_intensity"], f"contact_edges[{idx}].visual_force_intensity"
                ),
                "start_frame": start_frame,
                "end_frame": end_frame,
                "audio_expected": _expect_bool(edge["audio_expected"], f"contact_edges[{idx}].audio_expected"),
                "min_expected_force_events": min_events,
                "max_expected_force_events": max_events,
            }
        )
    authority_scope = _expect_allowed_string(
        contact_authority["authority_scope"],
        "visual_contact_manifest.contact_authority.authority_scope",
        CONTACT_AUTHORITY_SCOPES,
    )
    gold_mask_dependency_status = _expect_allowed_string(
        contact_authority["gold_mask_dependency_status"],
        "visual_contact_manifest.contact_authority.gold_mask_dependency_status",
        CONTACT_AUTHORITY_GOLD_MASK_STATUSES,
    )
    evidence_authority_class = _expect_allowed_string(
        contact_authority["evidence_authority_class"],
        "visual_contact_manifest.contact_authority.evidence_authority_class",
        CONTACT_AUTHORITY_CLASSES,
    )
    production_trust_claim = _expect_bool(
        contact_authority["production_trust_claim"],
        "visual_contact_manifest.contact_authority.production_trust_claim",
    )
    body_authority_scopes = {"body", "contact", "body_contact"}
    has_body_material_edge = any(
        edge["source_material"].lower() in body_contact_materials
        or edge["target_material"].lower() in body_contact_materials
        for edge in normalized_edges
    )
    if authority_scope in body_authority_scopes:
        if gold_mask_dependency_status == "not_applicable":
            raise InvalidInputError(
                "body/contact authority cannot mark gold_mask_dependency_status as not_applicable"
            )
        if gold_mask_dependency_status == "cleared" and evidence_authority_class != "gold_mask_validated":
            raise InvalidInputError(
                "cleared body/contact authority requires evidence_authority_class gold_mask_validated"
            )
        if gold_mask_dependency_status == "missing" and evidence_authority_class == "gold_mask_validated":
            raise InvalidInputError(
                "missing body/contact gold-mask authority cannot use evidence_authority_class gold_mask_validated"
            )
    else:
        if has_body_material_edge:
            raise InvalidInputError(
                "non_body_contact authority conflicts with a body-contact material edge"
            )
        if gold_mask_dependency_status != "not_applicable":
            raise InvalidInputError(
                "non_body_contact authority requires gold_mask_dependency_status not_applicable"
            )
        if evidence_authority_class == "gold_mask_validated":
            raise InvalidInputError(
                "non_body_contact authority cannot use evidence_authority_class gold_mask_validated"
            )

    normalized = {
        "run_id": _expect_non_empty_string(payload["run_id"], "visual_contact_manifest.run_id"),
        "scene_id": _expect_non_empty_string(payload["scene_id"], "visual_contact_manifest.scene_id"),
        "shot_id": _expect_non_empty_string(payload["shot_id"], "visual_contact_manifest.shot_id"),
        "take_id": _expect_non_empty_string(payload["take_id"], "visual_contact_manifest.take_id"),
        "is_synthetic": _expect_bool(payload["is_synthetic"], "visual_contact_manifest.is_synthetic"),
        "frame_rate": frame_rate,
        "frame_time_origin_seconds": _expect_finite_number(
            payload["frame_time_origin_seconds"], "visual_contact_manifest.frame_time_origin_seconds"
        ),
        "contact_authority": {
            "authority_scope": authority_scope,
            "gold_mask_dependency_status": gold_mask_dependency_status,
            "evidence_authority_class": evidence_authority_class,
            "production_trust_claim": production_trust_claim,
        },
    }
    return {"manifest": normalized, "visual_take_artifact": visual_take, "contact_evidence_artifact": contact_evidence}, normalized_edges


def _validate_wave22_manifest(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise InvalidInputError("wave22_force_event_manifest must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "manifest_version",
            "run_id",
            "scene_id",
            "shot_id",
            "take_id",
            "is_synthetic",
            "frame_rate",
            "force_events",
        },
        "wave22_force_event_manifest",
    )
    events = payload["force_events"]
    if not isinstance(events, list):
        raise InvalidInputError("wave22_force_event_manifest.force_events must be an array")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise InvalidInputError(f"force_events[{idx}] must be an object")
        _expect_exact_keys(
            event,
            {
                "event_id",
                "contact_edge_id",
                "source_material",
                "target_material",
                "expected_foley_family",
                "audio_force_class",
                "loudness_hint",
                "confidence",
                "start_frame",
                "end_frame",
            },
            f"force_events[{idx}]",
        )
        event_id = _expect_non_empty_string(event["event_id"], f"force_events[{idx}].event_id")
        if event_id in seen_ids:
            raise InvalidInputError(f"duplicate force event_id: {event_id}")
        seen_ids.add(event_id)
        start_frame = _expect_int(event["start_frame"], f"force_events[{idx}].start_frame", minimum=0)
        end_frame = _expect_int(event["end_frame"], f"force_events[{idx}].end_frame", minimum=0)
        if end_frame < start_frame:
            raise InvalidInputError(f"force_events[{idx}] end_frame must be >= start_frame")
        normalized.append(
            {
                "event_id": event_id,
                "contact_edge_id": _expect_non_empty_string(event["contact_edge_id"], f"force_events[{idx}].contact_edge_id"),
                "source_material": _expect_non_empty_string(event["source_material"], f"force_events[{idx}].source_material"),
                "target_material": _expect_non_empty_string(event["target_material"], f"force_events[{idx}].target_material"),
                "expected_foley_family": _expect_non_empty_string(
                    event["expected_foley_family"], f"force_events[{idx}].expected_foley_family"
                ),
                "audio_force_class": _expect_non_empty_string(event["audio_force_class"], f"force_events[{idx}].audio_force_class"),
                "loudness_hint": _expect_non_empty_string(event["loudness_hint"], f"force_events[{idx}].loudness_hint"),
                "confidence": _expect_ratio(event["confidence"], f"force_events[{idx}].confidence"),
                "start_frame": start_frame,
                "end_frame": end_frame,
            }
        )
    meta = {
        "schema_name": _expect_non_empty_string(payload["schema_name"], "wave22_force_event_manifest.schema_name"),
        "manifest_version": _expect_int(payload["manifest_version"], "wave22_force_event_manifest.manifest_version", minimum=1),
        "run_id": _expect_non_empty_string(payload["run_id"], "wave22_force_event_manifest.run_id"),
        "scene_id": _expect_non_empty_string(payload["scene_id"], "wave22_force_event_manifest.scene_id"),
        "shot_id": _expect_non_empty_string(payload["shot_id"], "wave22_force_event_manifest.shot_id"),
        "take_id": _expect_non_empty_string(payload["take_id"], "wave22_force_event_manifest.take_id"),
        "is_synthetic": _expect_bool(payload["is_synthetic"], "wave22_force_event_manifest.is_synthetic"),
        "frame_rate": _expect_finite_number(payload["frame_rate"], "wave22_force_event_manifest.frame_rate"),
    }
    if meta["frame_rate"] <= 0.0:
        raise InvalidInputError("wave22_force_event_manifest.frame_rate must be > 0")
    return meta, normalized


def _validate_wave30_manifest(payload: Any, wave30_schema: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(payload, wave30_schema, "wave30_audio_event_manifest")
    if not isinstance(payload, dict):
        raise InvalidInputError("wave30_audio_event_manifest must be an object")
    events = payload.get("audio_events")
    if not isinstance(events, list):
        raise InvalidInputError("wave30_audio_event_manifest.audio_events must be an array")
    declared_event_count = _expect_int(payload.get("audio_event_count"), "wave30_audio_event_manifest.audio_event_count", minimum=1)
    if declared_event_count != len(events):
        raise InvalidInputError(
            f"wave30_audio_event_manifest.audio_event_count mismatch ({declared_event_count} != {len(events)})"
        )
    seen_ids: set[str] = set()
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise InvalidInputError(f"wave30_audio_events[{idx}] must be an object")
        event_id = _expect_non_empty_string(event.get("audio_event_id"), f"wave30_audio_events[{idx}].audio_event_id")
        if event_id in seen_ids:
            raise InvalidInputError(f"duplicate wave30 audio_event_id: {event_id}")
        seen_ids.add(event_id)
        if event.get("scene_id") != payload.get("scene_id"):
            raise InvalidInputError(f"wave30_audio_events[{idx}].scene_id mismatch against wave30 manifest scene_id")
        if event.get("shot_id") != payload.get("shot_id"):
            raise InvalidInputError(f"wave30_audio_events[{idx}].shot_id mismatch against wave30 manifest shot_id")
    return payload


def _validate_runtime_proof(
    payload: Any,
    force_events: list[dict[str, Any]],
    wave22_binding: Binding,
    wave30_binding: Binding,
    visual_binding: Binding,
    wave31_binding: Binding | None,
    mapped_pairs: list[tuple[dict[str, Any], dict[str, Any], Binding]],
) -> list[str]:
    if not isinstance(payload, dict):
        raise InvalidInputError("runtime_proof must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "proof_kind",
            "engine",
            "model",
            "model_version",
            "model_sha256",
            "visual_contact_manifest_sha256",
            "wave22_force_event_manifest_sha256",
            "wave30_audio_event_manifest_sha256",
            "wave31_force_event_manifest_sha256",
            "ordered_event_audio_bindings",
            "runtime_executed",
            "decode_succeeded",
        },
        "runtime_proof",
    )
    if payload["schema_name"] != "wave64_production_runtime_proof":
        raise InvalidInputError("runtime_proof.schema_name mismatch")
    if payload["proof_kind"] != "production_runtime":
        raise InvalidInputError("runtime_proof.proof_kind mismatch")
    for field in ("engine", "model", "model_version"):
        _expect_non_empty_string(payload[field], f"runtime_proof.{field}")
    _expect_sha256(payload["model_sha256"], "runtime_proof.model_sha256")
    if payload["visual_contact_manifest_sha256"] != visual_binding.sha256:
        raise InvalidInputError("runtime_proof.visual_contact_manifest_sha256 mismatch")
    if payload["wave22_force_event_manifest_sha256"] != wave22_binding.sha256:
        raise InvalidInputError("runtime_proof.wave22_force_event_manifest_sha256 mismatch")
    if payload["wave30_audio_event_manifest_sha256"] != wave30_binding.sha256:
        raise InvalidInputError("runtime_proof.wave30_audio_event_manifest_sha256 mismatch")
    if wave31_binding is None:
        if payload["wave31_force_event_manifest_sha256"] is not None:
            raise InvalidInputError("runtime_proof.wave31_force_event_manifest_sha256 must be null when wave31 absent")
    else:
        if payload["wave31_force_event_manifest_sha256"] != wave31_binding.sha256:
            raise InvalidInputError("runtime_proof.wave31_force_event_manifest_sha256 mismatch")
    ordered = payload["ordered_event_audio_bindings"]
    if not isinstance(ordered, list):
        raise InvalidInputError("runtime_proof.ordered_event_audio_bindings must be an array")
    expected_order = sorted(force_events, key=lambda item: item["event_id"])
    blockers: list[str] = []
    if len(ordered) != len(expected_order):
        blockers.append("runtime_proof ordered_event_audio_bindings length mismatch")
    else:
        mapped_by_force = {force["event_id"]: (audio, wav) for force, audio, wav in mapped_pairs}
        for idx, (entry, expected_force) in enumerate(zip(ordered, expected_order)):
            if not isinstance(entry, dict):
                raise InvalidInputError(f"runtime_proof.ordered_event_audio_bindings[{idx}] must be an object")
            _expect_exact_keys(
                entry, {"force_event_id", "audio_event_id", "wav_sha256"}, f"runtime_proof.ordered_event_audio_bindings[{idx}]"
            )
            force_id = _expect_non_empty_string(entry["force_event_id"], f"runtime_proof.ordered_event_audio_bindings[{idx}].force_event_id")
            if force_id != expected_force["event_id"]:
                blockers.append(f"runtime_proof ordered force_event_id mismatch at index {idx}")
                continue
            if force_id not in mapped_by_force:
                blockers.append(f"runtime_proof references unmapped force_event_id: {force_id}")
                continue
            expected_audio, wav_binding = mapped_by_force[force_id]
            if entry["audio_event_id"] != expected_audio["audio_event_id"]:
                blockers.append(f"runtime_proof audio_event_id mismatch for {force_id}")
            if entry["wav_sha256"] != wav_binding.sha256:
                blockers.append(f"runtime_proof wav_sha256 mismatch for {force_id}")
    if payload["runtime_executed"] is not True:
        blockers.append("runtime_proof runtime_executed must be true")
    if payload["decode_succeeded"] is not True:
        blockers.append("runtime_proof decode_succeeded must be true")
    return blockers


def _validate_av_review_proof(
    payload: Any,
    force_events: list[dict[str, Any]],
    wave22_binding: Binding,
    wave30_binding: Binding,
    visual_binding: Binding,
    wave31_binding: Binding | None,
    mapped_pairs: list[tuple[dict[str, Any], dict[str, Any], Binding]],
) -> list[str]:
    if not isinstance(payload, dict):
        raise InvalidInputError("av_review_proof must be an object")
    _expect_exact_keys(
        payload,
        {
            "schema_name",
            "proof_kind",
            "reviewer_id",
            "review_method",
            "engine",
            "model",
            "model_version",
            "model_sha256",
            "visual_contact_manifest_sha256",
            "wave22_force_event_manifest_sha256",
            "wave30_audio_event_manifest_sha256",
            "wave31_force_event_manifest_sha256",
            "results",
        },
        "av_review_proof",
    )
    if payload["schema_name"] != "wave64_av_alignment_review_proof":
        raise InvalidInputError("av_review_proof.schema_name mismatch")
    if payload["proof_kind"] != "av_alignment_review":
        raise InvalidInputError("av_review_proof.proof_kind mismatch")
    for field in ("reviewer_id", "review_method", "engine", "model", "model_version"):
        _expect_non_empty_string(payload[field], f"av_review_proof.{field}")
    _expect_sha256(payload["model_sha256"], "av_review_proof.model_sha256")
    if payload["visual_contact_manifest_sha256"] != visual_binding.sha256:
        raise InvalidInputError("av_review_proof.visual_contact_manifest_sha256 mismatch")
    if payload["wave22_force_event_manifest_sha256"] != wave22_binding.sha256:
        raise InvalidInputError("av_review_proof.wave22_force_event_manifest_sha256 mismatch")
    if payload["wave30_audio_event_manifest_sha256"] != wave30_binding.sha256:
        raise InvalidInputError("av_review_proof.wave30_audio_event_manifest_sha256 mismatch")
    if wave31_binding is None:
        if payload["wave31_force_event_manifest_sha256"] is not None:
            raise InvalidInputError("av_review_proof.wave31_force_event_manifest_sha256 must be null when wave31 absent")
    else:
        if payload["wave31_force_event_manifest_sha256"] != wave31_binding.sha256:
            raise InvalidInputError("av_review_proof.wave31_force_event_manifest_sha256 mismatch")
    results = payload["results"]
    if not isinstance(results, list):
        raise InvalidInputError("av_review_proof.results must be an array")
    blockers: list[str] = []
    mapped_by_force = {force["event_id"]: audio for force, audio, _ in mapped_pairs}
    expected_ids = sorted(force["event_id"] for force in force_events)
    if len(results) != len(expected_ids):
        blockers.append("av_review_proof results length mismatch")
    seen: set[str] = set()
    for idx, result in enumerate(results):
        if not isinstance(result, dict):
            raise InvalidInputError(f"av_review_proof.results[{idx}] must be an object")
        _expect_exact_keys(
            result,
            {
                "force_event_id",
                "audio_event_id",
                "visual_contact_present",
                "ownership_match",
                "material_family_match",
                "force_loudness_match",
                "timing_aligned",
                "foley_present",
                "false_event_absent",
            },
            f"av_review_proof.results[{idx}]",
        )
        force_id = _expect_non_empty_string(result["force_event_id"], f"av_review_proof.results[{idx}].force_event_id")
        audio_id = _expect_non_empty_string(result["audio_event_id"], f"av_review_proof.results[{idx}].audio_event_id")
        if force_id in seen:
            raise InvalidInputError(f"av_review_proof duplicate force_event_id: {force_id}")
        seen.add(force_id)
        if force_id not in mapped_by_force:
            blockers.append(f"av_review_proof unknown force_event_id: {force_id}")
            continue
        if mapped_by_force[force_id]["audio_event_id"] != audio_id:
            blockers.append(f"av_review_proof audio_event_id mismatch for {force_id}")
        for key in (
            "visual_contact_present",
            "ownership_match",
            "material_family_match",
            "force_loudness_match",
            "timing_aligned",
            "foley_present",
            "false_event_absent",
        ):
            if result[key] is not True:
                blockers.append(f"av_review_proof predicate failed for {force_id}: {key}")
    missing = sorted(set(expected_ids) - seen)
    for force_id in missing:
        blockers.append(f"av_review_proof missing force_event_id: {force_id}")
    return blockers


def evaluate(root: Path, request_path: Path, output_path: Path) -> int:
    request_schema = _load_json(root / REQUEST_SCHEMA_RELATIVE)
    report_schema = _load_json(root / REPORT_SCHEMA_RELATIVE)
    wave30_schema = _load_json(root / WAVE30_SCHEMA_RELATIVE)
    request_payload = _load_json(request_path)
    _validate_schema(request_payload, request_schema, "request")

    request_binding = Binding(path=request_path.resolve(), sha256=_sha256_of(request_path.resolve()))
    run_id = _expect_non_empty_string(request_payload["run_id"], "request.run_id")
    scene_id = _expect_non_empty_string(request_payload["scene_id"], "request.scene_id")
    shot_id = _expect_non_empty_string(request_payload["shot_id"], "request.shot_id")
    take_id = _expect_non_empty_string(request_payload["take_id"], "request.take_id")
    is_synthetic = _expect_bool(request_payload["is_synthetic"], "request.is_synthetic")

    thresholds = dict(DEFAULT_THRESHOLDS)
    for key, value in request_payload["thresholds"].items():
        thresholds[key] = value
    thresholds["min_force_confidence"] = _expect_ratio(thresholds["min_force_confidence"], "thresholds.min_force_confidence")
    thresholds["max_frame_drift"] = _expect_int(thresholds["max_frame_drift"], "thresholds.max_frame_drift", minimum=0)
    thresholds["max_seconds_drift"] = _expect_finite_number(thresholds["max_seconds_drift"], "thresholds.max_seconds_drift")
    thresholds["max_wav_duration_drift_seconds"] = _expect_finite_number(
        thresholds["max_wav_duration_drift_seconds"], "thresholds.max_wav_duration_drift_seconds"
    )
    thresholds["max_clipping_ratio"] = _expect_ratio(thresholds["max_clipping_ratio"], "thresholds.max_clipping_ratio")
    thresholds["min_rms_ratio"] = _expect_ratio(thresholds["min_rms_ratio"], "thresholds.min_rms_ratio")

    visual_binding = _validate_binding(root, request_payload["visual_contact_manifest_binding"], "visual_contact_manifest_binding")
    wave22_binding = _validate_binding(root, request_payload["wave22_force_event_manifest_binding"], "wave22_force_event_manifest_binding")
    wave30_binding = _validate_binding(root, request_payload["wave30_audio_event_manifest_binding"], "wave30_audio_event_manifest_binding")
    wave31_binding = None
    if request_payload["wave31_force_event_manifest_binding"] is not None:
        wave31_binding = _validate_binding(root, request_payload["wave31_force_event_manifest_binding"], "wave31_force_event_manifest_binding")
    runtime_binding = None
    if request_payload["runtime_proof_binding"] is not None:
        runtime_binding = _validate_binding(root, request_payload["runtime_proof_binding"], "runtime_proof_binding")
    review_binding = None
    if request_payload["av_review_proof_binding"] is not None:
        review_binding = _validate_binding(root, request_payload["av_review_proof_binding"], "av_review_proof_binding")
    bundle_binding = None
    if request_payload["production_alignment_bundle_binding"] is not None:
        bundle_binding = _validate_binding(
            root, request_payload["production_alignment_bundle_binding"], "production_alignment_bundle_binding"
        )

    authority_registry_binding = _validate_binding(
        root,
        {"path": str((root / AUTHORITY_REGISTRY_RELATIVE).resolve()), "sha256": _sha256_of((root / AUTHORITY_REGISTRY_RELATIVE).resolve())},
        "authority_registry_binding",
    )
    registry = _validate_registry(_load_json(authority_registry_binding.path))
    for key in ("max_frame_drift", "max_seconds_drift", "max_wav_duration_drift_seconds"):
        thresholds[key] = min(thresholds[key], registry["sync_tolerances"][key])

    visual_payload = _load_json(visual_binding.path)
    visual_info, contact_edges = _validate_visual_manifest(
        root,
        visual_payload,
        registry["body_contact_materials"],
    )
    visual_manifest = visual_info["manifest"]
    if visual_manifest["run_id"] != run_id or visual_manifest["scene_id"] != scene_id or visual_manifest["shot_id"] != shot_id:
        raise InvalidInputError("visual_contact_manifest run/scene/shot mismatch")
    if visual_manifest["take_id"] != take_id:
        raise InvalidInputError("visual_contact_manifest.take_id mismatch")
    if visual_manifest["is_synthetic"] != is_synthetic:
        raise InvalidInputError("visual_contact_manifest.is_synthetic mismatch")

    wave22_meta, force_events = _validate_wave22_manifest(_load_json(wave22_binding.path))
    if wave22_meta["run_id"] != run_id or wave22_meta["scene_id"] != scene_id or wave22_meta["shot_id"] != shot_id:
        raise InvalidInputError("wave22_force_event_manifest run/scene/shot mismatch")
    if wave22_meta["take_id"] != take_id:
        raise InvalidInputError("wave22_force_event_manifest.take_id mismatch")
    if wave22_meta["is_synthetic"] != is_synthetic:
        raise InvalidInputError("wave22_force_event_manifest.is_synthetic mismatch")
    if abs(wave22_meta["frame_rate"] - visual_manifest["frame_rate"]) > FRAME_RATE_TOLERANCE:
        raise InvalidInputError("wave22_force_event_manifest.frame_rate mismatch against visual_contact_manifest.frame_rate")

    wave30_manifest = _validate_wave30_manifest(_load_json(wave30_binding.path), wave30_schema)
    if wave30_manifest["run_id"] != run_id or wave30_manifest["scene_id"] != scene_id or wave30_manifest["shot_id"] != shot_id:
        raise InvalidInputError("wave30_audio_event_manifest run/scene/shot mismatch")
    if _expect_bool(wave30_manifest["is_synthetic"], "wave30_audio_event_manifest.is_synthetic") != is_synthetic:
        raise InvalidInputError("wave30_audio_event_manifest.is_synthetic mismatch")
    wave30_sync_frame_rate = _expect_finite_number(
        wave30_manifest["av_sync_binding"]["frame_rate"], "wave30_audio_event_manifest.av_sync_binding.frame_rate"
    )
    if abs(wave30_sync_frame_rate - visual_manifest["frame_rate"]) > FRAME_RATE_TOLERANCE:
        raise InvalidInputError("wave30_audio_event_manifest.av_sync_binding.frame_rate mismatch against visual manifest")
    if abs(wave30_sync_frame_rate - wave22_meta["frame_rate"]) > FRAME_RATE_TOLERANCE:
        raise InvalidInputError("wave30_audio_event_manifest.av_sync_binding.frame_rate mismatch against wave22 manifest")

    if wave31_binding is not None:
        wave31_payload = _load_json(wave31_binding.path)
        if not isinstance(wave31_payload, dict):
            raise InvalidInputError("wave31_force_event_manifest must be an object")
        for field, expected in (("run_id", run_id), ("scene_id", scene_id), ("shot_id", shot_id)):
            if wave31_payload.get(field) != expected:
                raise InvalidInputError(f"wave31_force_event_manifest.{field} mismatch")

    edge_map = {edge["contact_edge_id"]: edge for edge in contact_edges}
    for event in force_events:
        if event["contact_edge_id"] not in edge_map:
            raise InvalidInputError(f"force event references unknown contact_edge_id: {event['contact_edge_id']}")

    bound_paths: set[Path] = {
        request_binding.path,
        visual_binding.path,
        wave22_binding.path,
        wave30_binding.path,
        authority_registry_binding.path,
        visual_info["visual_take_artifact"]["path"],
        visual_info["contact_evidence_artifact"]["path"],
    }
    if wave31_binding is not None:
        bound_paths.add(wave31_binding.path)
    if runtime_binding is not None:
        bound_paths.add(runtime_binding.path)
    if review_binding is not None:
        bound_paths.add(review_binding.path)
    if bundle_binding is not None:
        bound_paths.add(bundle_binding.path)
    if output_path in bound_paths:
        raise InvalidInputError("output path collides with bound request/artifact path")

    gates: dict[str, dict[str, Any]] = {}
    all_blockers: list[str] = []

    event_binding_blockers: list[str] = []
    frame_alignment_blockers: list[str] = []
    presence_blockers: list[str] = []
    false_event_blockers: list[str] = []

    force_counts_by_edge: dict[str, int] = {edge_id: 0 for edge_id in edge_map}
    for event in force_events:
        force_counts_by_edge[event["contact_edge_id"]] += 1

        edge = edge_map[event["contact_edge_id"]]
        if event["source_material"].lower() != edge["source_material"].lower():
            event_binding_blockers.append(f"source_material mismatch for force event {event['event_id']}")
        if event["target_material"].lower() != edge["target_material"].lower():
            event_binding_blockers.append(f"target_material mismatch for force event {event['event_id']}")

        pair_key = _sort_pair(event["source_material"], event["target_material"])
        expected_family = registry["material_pair_rules"].get(pair_key)
        if expected_family is None:
            event_binding_blockers.append(f"unknown material pair for force event {event['event_id']}: {pair_key}")
        elif event["expected_foley_family"] != expected_family:
            event_binding_blockers.append(
                f"material pair rule mismatch for force event {event['event_id']}: expected {expected_family}"
            )

        profile = registry["force_profiles"].get(event["audio_force_class"])
        if profile is None:
            event_binding_blockers.append(f"unknown audio_force_class for force event {event['event_id']}")
        else:
            if event["loudness_hint"] not in profile["allowed_loudness_hints"]:
                event_binding_blockers.append(f"loudness_hint mismatch for force event {event['event_id']}")
            if event["expected_foley_family"] not in profile["allowed_foley_families"]:
                event_binding_blockers.append(f"foley family disallowed for force event {event['event_id']}")

        allowed_classes = registry["visual_intensity_taxonomy"].get(edge["visual_force_intensity"].lower())
        if allowed_classes is None:
            event_binding_blockers.append(f"unknown visual_force_intensity on edge {edge['contact_edge_id']}")
        elif event["audio_force_class"].lower() not in allowed_classes:
            event_binding_blockers.append(
                f"force class not aligned to visual intensity for force event {event['event_id']}"
            )
        if event["confidence"] < float(thresholds["min_force_confidence"]):
            event_binding_blockers.append(f"force confidence below threshold for force event {event['event_id']}")

    for edge_id, edge in edge_map.items():
        count = force_counts_by_edge.get(edge_id, 0)
        if edge["audio_expected"] is False and count != 0:
            event_binding_blockers.append(f"silent contact edge {edge_id} has unexpected force events")
        if count < edge["min_expected_force_events"] or count > edge["max_expected_force_events"]:
            event_binding_blockers.append(f"force event count out of bounds for contact edge {edge_id}")

    wave30_events = wave30_manifest["audio_events"]
    required_lanes = {
        _expect_non_empty_string(lane, "wave30_audio_event_manifest.required_lanes[]")
        for lane in wave30_manifest["required_lanes"]
    }
    force_by_id = {item["event_id"]: item for item in force_events}
    mapped_pairs: list[tuple[dict[str, Any], dict[str, Any], Binding]] = []
    wav_metrics_rows: list[dict[str, Any]] = []
    matched_lanes: set[str] = set()
    seen_wave30_ids: set[str] = set()
    force_to_matches: dict[str, list[dict[str, Any]]] = {event["event_id"]: [] for event in force_events}
    for event in wave30_events:
        source_event_id = _expect_non_empty_string(event["source_event_id"], "wave30_event.source_event_id")
        if source_event_id in force_to_matches:
            force_to_matches[source_event_id].append(event)
        else:
            if _expect_non_empty_string(event["layer"], "wave30_event.layer") in registry["allowed_foley_layers"]:
                false_event_blockers.append(f"unmatched allowlisted Wave30 event source_event_id: {source_event_id}")

    for force in force_events:
        matches = force_to_matches[force["event_id"]]
        if not matches:
            presence_blockers.append(f"missing required foley for force event {force['event_id']}")
            continue
        if len(matches) > 1:
            false_event_blockers.append(f"multiple Wave30 events mapped to force event {force['event_id']}")
            continue
        audio_event = matches[0]
        audio_id = _expect_non_empty_string(audio_event["audio_event_id"], "wave30_event.audio_event_id")
        if audio_id in seen_wave30_ids:
            raise InvalidInputError(f"duplicate mapped Wave30 audio_event_id: {audio_id}")
        seen_wave30_ids.add(audio_id)

        event_type = _expect_non_empty_string(audio_event["event_type"], f"wave30_event[{audio_id}].event_type")
        layer = _expect_non_empty_string(audio_event["layer"], f"wave30_event[{audio_id}].layer")
        if event_type != layer:
            event_binding_blockers.append(f"event_type/layer mismatch for force event {force['event_id']}")
        if event_type != force["expected_foley_family"]:
            event_binding_blockers.append(f"event_type mismatch for force event {force['event_id']}")
        if layer != force["expected_foley_family"]:
            event_binding_blockers.append(f"layer mismatch for force event {force['event_id']}")
        if layer not in registry["allowed_foley_layers"]:
            event_binding_blockers.append(f"Wave30 layer not allowlisted for force event {force['event_id']}")
        profile = registry["force_profiles"].get(force["audio_force_class"])
        if profile is not None:
            allowed_families = {str(item) for item in profile["allowed_foley_families"]}
            if event_type not in allowed_families:
                event_binding_blockers.append(f"event_type disallowed by force profile for force event {force['event_id']}")
            if layer not in allowed_families:
                event_binding_blockers.append(f"layer disallowed by force profile for force event {force['event_id']}")
        pair_expected = registry["material_pair_rules"].get(_sort_pair(force["source_material"], force["target_material"]))
        if pair_expected is None:
            event_binding_blockers.append(f"unknown material pair for mapped force event {force['event_id']}")
        else:
            if event_type != pair_expected:
                event_binding_blockers.append(
                    f"event_type does not match material pair expected family for force event {force['event_id']}"
                )
            if layer != pair_expected:
                event_binding_blockers.append(
                    f"layer does not match material pair expected family for force event {force['event_id']}"
                )

        synthetic_state = audio_event.get("synthetic_state")
        if not isinstance(synthetic_state, dict):
            raise InvalidInputError(f"wave30_event[{audio_id}].synthetic_state must be an object")
        event_is_synthetic = _classify_synthetic_origin(
            synthetic_state.get("synthetic_origin"), f"wave30_event[{audio_id}].synthetic_state.synthetic_origin"
        )
        if event_is_synthetic != is_synthetic:
            event_binding_blockers.append(f"synthetic_state mismatch for force event {force['event_id']}")

        routing = audio_event.get("routing")
        if not isinstance(routing, dict):
            raise InvalidInputError(f"wave30_event[{audio_id}].routing must be an object")
        lane_value = _expect_non_empty_string(routing.get("lane"), f"wave30_event[{audio_id}].routing.lane")
        matched_lanes.add(lane_value)

        edge = edge_map[force["contact_edge_id"]]
        permitted_subject_ids = {
            edge["source_entity_id"],
            edge["target_entity_id"],
            edge["source_owner_id"],
            edge["target_owner_id"],
        }
        subject_binding = audio_event.get("subject_binding")
        if not isinstance(subject_binding, dict):
            raise InvalidInputError(f"wave30_event[{audio_id}].subject_binding must be an object")
        binding_type = _expect_non_empty_string(subject_binding.get("binding_type"), f"wave30_event[{audio_id}].subject_binding.binding_type")
        if binding_type not in {"character", "object"}:
            event_binding_blockers.append(f"subject_binding.binding_type must be character/object for force event {force['event_id']}")
        candidate_ids: list[str] = []
        for key in ("character_id", "object_id"):
            value = subject_binding.get(key)
            if isinstance(value, str) and value.strip():
                candidate_ids.append(value.strip())
        if not candidate_ids:
            event_binding_blockers.append(f"subject_binding missing character_id/object_id for force event {force['event_id']}")
        elif not any(candidate in permitted_subject_ids for candidate in candidate_ids):
            event_binding_blockers.append(f"subject_binding ownership mismatch for force event {force['event_id']}")

        artifact = audio_event.get("artifact")
        wav = _validate_path_sha_bytes(root, artifact, f"wave30_audio_events[{audio_id}].artifact", exact_keys=False)
        if Path(wav["path"]).suffix.lower() != ".wav":
            raise InvalidInputError(f"wave30 event {audio_id} artifact must be a .wav file")
        bound_paths.add(wav["path"])
        metrics = _read_wav_metrics(wav["path"])
        profile = registry["force_profiles"].get(force["audio_force_class"])
        if profile is not None:
            rms_low, rms_high = profile["normalized_pcm_rms_range"]
            if metrics["rms_ratio"] < rms_low or metrics["rms_ratio"] > rms_high:
                event_binding_blockers.append(f"RMS range mismatch for force event {force['event_id']}")
            clipping_limit = min(float(thresholds["max_clipping_ratio"]), float(profile["maximum_clipping_ratio"]))
            if metrics["clipping_ratio"] > clipping_limit:
                event_binding_blockers.append(f"clipping ratio exceeds limit for force event {force['event_id']}")
            if metrics["rms_ratio"] < float(thresholds["min_rms_ratio"]):
                event_binding_blockers.append(f"RMS below threshold for force event {force['event_id']}")

        start_seconds = _expect_finite_number(audio_event["start_seconds"], f"wave30_event[{audio_id}].start_seconds")
        end_seconds = _expect_finite_number(audio_event["end_seconds"], f"wave30_event[{audio_id}].end_seconds")
        if end_seconds <= start_seconds:
            raise InvalidInputError(f"wave30 event {audio_id} has non-positive duration")
        event_duration = end_seconds - start_seconds
        if abs(event_duration - metrics["duration_seconds"]) > float(thresholds["max_wav_duration_drift_seconds"]):
            frame_alignment_blockers.append(f"WAV duration drift for force event {force['event_id']}")

        force_start_seconds = (
            float(visual_manifest["frame_time_origin_seconds"]) + force["start_frame"] / float(visual_manifest["frame_rate"])
        )
        force_end_seconds = (
            float(visual_manifest["frame_time_origin_seconds"]) + force["end_frame"] / float(visual_manifest["frame_rate"])
        )
        if abs(start_seconds - force_start_seconds) > float(thresholds["max_seconds_drift"]):
            frame_alignment_blockers.append(f"start seconds drift for force event {force['event_id']}")
        if abs(end_seconds - force_end_seconds) > float(thresholds["max_seconds_drift"]):
            frame_alignment_blockers.append(f"end seconds drift for force event {force['event_id']}")

        frame_range = audio_event["expected_video_frame_range"]
        wave30_start_frame = _expect_int(frame_range["start_frame"], f"wave30_event[{audio_id}].expected_video_frame_range.start_frame", minimum=0)
        wave30_end_frame = _expect_int(frame_range["end_frame"], f"wave30_event[{audio_id}].expected_video_frame_range.end_frame", minimum=0)
        wave30_frame_rate = _expect_finite_number(
            frame_range["frame_rate"], f"wave30_event[{audio_id}].expected_video_frame_range.frame_rate"
        )
        if abs(wave30_frame_rate - visual_manifest["frame_rate"]) > FRAME_RATE_TOLERANCE:
            frame_alignment_blockers.append(f"frame_rate mismatch against visual manifest for force event {force['event_id']}")
        if abs(wave30_frame_rate - wave22_meta["frame_rate"]) > FRAME_RATE_TOLERANCE:
            frame_alignment_blockers.append(f"frame_rate mismatch against wave22 manifest for force event {force['event_id']}")
        if abs(wave30_start_frame - force["start_frame"]) > int(thresholds["max_frame_drift"]):
            frame_alignment_blockers.append(f"start frame drift for force event {force['event_id']}")
        if abs(wave30_end_frame - force["end_frame"]) > int(thresholds["max_frame_drift"]):
            frame_alignment_blockers.append(f"end frame drift for force event {force['event_id']}")

        mapped_pairs.append((force, audio_event, Binding(path=wav["path"], sha256=wav["sha256"])))
        wav_metrics_rows.append(
            {
                "audio_event_id": audio_id,
                "force_event_id": force["event_id"],
                "wav_sha256": wav["sha256"],
                "duration_seconds": round(float(metrics["duration_seconds"]), 6),
                "sample_rate_hz": int(metrics["sample_rate_hz"]),
                "sample_width_bytes": int(metrics["sample_width_bytes"]),
                "channels": int(metrics["channels"]),
                "frame_count": int(metrics["frame_count"]),
                "rms_ratio": float(metrics["rms_ratio"]),
                "clipping_ratio": float(metrics["clipping_ratio"]),
            }
        )

    missing_required_lanes = sorted(matched_lanes - required_lanes)
    if missing_required_lanes:
        event_binding_blockers.append(
            f"wave30 required_lanes missing matched lanes: {','.join(missing_required_lanes)}"
        )

    contact_authority = visual_manifest["contact_authority"]
    has_missing_gold_mask_authority = (
        contact_authority["authority_scope"] in {"body", "contact", "body_contact"}
        and contact_authority["gold_mask_dependency_status"] == "missing"
    )

    gates["event_binding_check"] = _make_gate(
        PASS if not event_binding_blockers else FAIL,
        event_binding_blockers,
        [visual_binding.sha256, wave22_binding.sha256, wave30_binding.sha256],
    )
    gates["frame_to_audio_alignment"] = _make_gate(
        PASS if not frame_alignment_blockers else FAIL,
        frame_alignment_blockers,
        [visual_binding.sha256, wave22_binding.sha256, wave30_binding.sha256] + [row["wav_sha256"] for row in wav_metrics_rows],
    )
    gates["foley_presence"] = _make_gate(
        PASS if not presence_blockers else FAIL,
        presence_blockers,
        [wave22_binding.sha256, wave30_binding.sha256],
    )
    gates["false_event_reject"] = _make_gate(
        PASS if not false_event_blockers else FAIL,
        false_event_blockers,
        [wave22_binding.sha256, wave30_binding.sha256],
    )

    av_blockers: list[str] = []
    if has_missing_gold_mask_authority:
        av_blockers.append("Blocked_Gold_Mask_Authority_Missing")
        av_status = BLOCKED
    elif review_binding is None:
        av_blockers.append("missing av_review_proof_binding")
        av_status = BLOCKED
    else:
        av_proof_blockers = _validate_av_review_proof(
            _load_json(review_binding.path),
            force_events,
            wave22_binding,
            wave30_binding,
            visual_binding,
            wave31_binding,
            mapped_pairs,
        )
        av_blockers.extend(av_proof_blockers)
        av_status = PASS if not av_blockers else FAIL
    gates["av_event_alignment_review"] = _make_gate(
        av_status,
        av_blockers,
        [visual_binding.sha256, wave22_binding.sha256, wave30_binding.sha256] + ([review_binding.sha256] if review_binding else []),
    )

    runtime_blockers: list[str] = []
    if runtime_binding is None:
        runtime_blockers.append("missing runtime_proof_binding")
        runtime_status = BLOCKED
    else:
        runtime_proof_blockers = _validate_runtime_proof(
            _load_json(runtime_binding.path),
            force_events,
            wave22_binding,
            wave30_binding,
            visual_binding,
            wave31_binding,
            mapped_pairs,
        )
        runtime_blockers.extend(runtime_proof_blockers)
        runtime_status = PASS if not runtime_blockers else FAIL
    if is_synthetic:
        runtime_status = BLOCKED
        runtime_blockers.append("synthetic input cannot satisfy production runtime proof gate")
    gates["production_runtime_proof"] = _make_gate(
        runtime_status,
        runtime_blockers,
        [wave22_binding.sha256, wave30_binding.sha256] + ([runtime_binding.sha256] if runtime_binding else []),
    )

    authority_blockers: list[str] = []
    authority_status = PASS
    authority_prerequisites = (
        "event_binding_check",
        "frame_to_audio_alignment",
        "foley_presence",
        "false_event_reject",
        "av_event_alignment_review",
        "production_runtime_proof",
    )
    failed_prerequisites = [name for name in authority_prerequisites if gates[name]["status"] == FAIL]
    blocked_prerequisites = [name for name in authority_prerequisites if gates[name]["status"] == BLOCKED]
    if has_missing_gold_mask_authority:
        authority_status = BLOCKED
        authority_blockers.append("Blocked_Gold_Mask_Authority_Missing")
    elif is_synthetic:
        authority_status = BLOCKED
        authority_blockers.append("synthetic input cannot satisfy production alignment authority")
    elif failed_prerequisites:
        authority_status = FAIL
        authority_blockers.extend(f"upstream gate failed: {name}" for name in failed_prerequisites)
    elif blocked_prerequisites:
        authority_status = BLOCKED
        authority_blockers.extend(f"upstream gate blocked: {name}" for name in blocked_prerequisites)
    elif bundle_binding is None:
        authority_status = BLOCKED
        authority_blockers.append("missing production_alignment_bundle_binding")
        if visual_manifest["contact_authority"]["production_trust_claim"]:
            authority_blockers.append("self-reported production trust cannot replace allowlisted production bundle")
    elif runtime_binding is None or review_binding is None:
        authority_status = BLOCKED
        authority_blockers.append("bundle authority requires runtime and av_review proofs")
    else:
        bundle = _load_json(bundle_binding.path)
        if not isinstance(bundle, dict):
            raise InvalidInputError("production_alignment_bundle must be an object")
        _expect_exact_keys(
            bundle,
            {
                "schema_name",
                "proof_kind",
                "bundle_version",
                "bundle_id",
                "authority_id",
                "run_id",
                "scene_id",
                "shot_id",
                "take_id",
                "is_synthetic",
                "visual_contact_manifest_sha256",
                "wave22_force_event_manifest_sha256",
                "wave30_audio_event_manifest_sha256",
                "wave31_force_event_manifest_sha256",
                "runtime_proof_sha256",
                "av_review_proof_sha256",
                "owned_event_audio_bindings",
                "visual_take_artifact_sha256",
                "contact_evidence_artifact_sha256",
            },
            "production_alignment_bundle",
        )
        if bundle["schema_name"] != "wave64_production_alignment_bundle":
            raise InvalidInputError("production_alignment_bundle.schema_name mismatch")
        if bundle["proof_kind"] != "production_alignment_authority":
            raise InvalidInputError("production_alignment_bundle.proof_kind mismatch")
        if _expect_int(bundle["bundle_version"], "production_alignment_bundle.bundle_version", minimum=1) != 1:
            raise InvalidInputError("production_alignment_bundle.bundle_version must be 1")
        bundle_id = _expect_non_empty_string(bundle["bundle_id"], "production_alignment_bundle.bundle_id")
        authority_id = _expect_non_empty_string(bundle["authority_id"], "production_alignment_bundle.authority_id")
        for field, expected in (("run_id", run_id), ("scene_id", scene_id), ("shot_id", shot_id), ("take_id", take_id)):
            if bundle[field] != expected:
                authority_blockers.append(f"production_alignment_bundle.{field} mismatch")
        if bundle["is_synthetic"] is not False:
            authority_status = BLOCKED
            authority_blockers.append("production_alignment_bundle.is_synthetic must be false")
        if bundle["visual_contact_manifest_sha256"] != visual_binding.sha256:
            authority_blockers.append("production_alignment_bundle visual manifest hash mismatch")
        if bundle["wave22_force_event_manifest_sha256"] != wave22_binding.sha256:
            authority_blockers.append("production_alignment_bundle wave22 hash mismatch")
        if bundle["wave30_audio_event_manifest_sha256"] != wave30_binding.sha256:
            authority_blockers.append("production_alignment_bundle wave30 hash mismatch")
        if wave31_binding is None:
            if bundle["wave31_force_event_manifest_sha256"] is not None:
                authority_blockers.append("production_alignment_bundle wave31 hash must be null when wave31 absent")
        else:
            if bundle["wave31_force_event_manifest_sha256"] != wave31_binding.sha256:
                authority_blockers.append("production_alignment_bundle wave31 hash mismatch")
        if bundle["runtime_proof_sha256"] != runtime_binding.sha256:
            authority_blockers.append("production_alignment_bundle runtime proof hash mismatch")
        if bundle["av_review_proof_sha256"] != review_binding.sha256:
            authority_blockers.append("production_alignment_bundle av review proof hash mismatch")
        if bundle["visual_take_artifact_sha256"] != visual_info["visual_take_artifact"]["sha256"]:
            authority_blockers.append("production_alignment_bundle visual_take_artifact hash mismatch")
        if bundle["contact_evidence_artifact_sha256"] != visual_info["contact_evidence_artifact"]["sha256"]:
            authority_blockers.append("production_alignment_bundle contact_evidence_artifact hash mismatch")
        owned = bundle["owned_event_audio_bindings"]
        if not isinstance(owned, list):
            raise InvalidInputError("production_alignment_bundle.owned_event_audio_bindings must be an array")
        expected_order = sorted(mapped_pairs, key=lambda item: item[0]["event_id"])
        if len(owned) != len(expected_order):
            authority_blockers.append("production_alignment_bundle owned_event_audio_bindings length mismatch")
        else:
            for idx, (entry, expected) in enumerate(zip(owned, expected_order)):
                if not isinstance(entry, dict):
                    raise InvalidInputError(f"owned_event_audio_bindings[{idx}] must be an object")
                _expect_exact_keys(entry, {"force_event_id", "audio_event_id", "wav_sha256"}, f"owned_event_audio_bindings[{idx}]")
                force_event, audio_event, wav_binding = expected
                if entry["force_event_id"] != force_event["event_id"]:
                    authority_blockers.append(f"bundle force_event_id mismatch at index {idx}")
                if entry["audio_event_id"] != audio_event["audio_event_id"]:
                    authority_blockers.append(f"bundle audio_event_id mismatch at index {idx}")
                if entry["wav_sha256"] != wav_binding.sha256:
                    authority_blockers.append(f"bundle wav_sha256 mismatch at index {idx}")
        semantic_defect = any(
            "mismatch" in item or "length mismatch" in item for item in authority_blockers
        )
        matches = [
            row
            for row in registry["approved_alignment_bundles"]
            if row["bundle_id"] == bundle_id and row["authority_id"] == authority_id and row["bundle_sha256"] == bundle_binding.sha256
        ]
        if semantic_defect:
            authority_status = FAIL
        elif not matches:
            authority_status = BLOCKED
            authority_blockers.append("production alignment bundle not allowlisted in authority registry")
        elif any(item["revoked"] for item in matches):
            authority_status = BLOCKED
            authority_blockers.append("production alignment bundle is revoked in authority registry")
        elif authority_blockers:
            authority_status = FAIL
        else:
            authority_status = PASS
    gates["production_alignment_authority"] = _make_gate(
        authority_status,
        authority_blockers,
        [authority_registry_binding.sha256] + ([bundle_binding.sha256] if bundle_binding else []),
    )

    for name in GATE_NAMES:
        if name == "overall_pass":
            continue
        all_blockers.extend(gates[name]["blockers"])
    overall_blockers = sorted(set(all_blockers))
    non_overall = [gates[name]["status"] for name in GATE_NAMES if name != "overall_pass"]
    if not is_synthetic and all(status == PASS for status in non_overall):
        overall_status = PASS
        overall_pass = True
    elif any(status == FAIL for status in non_overall):
        overall_status = FAIL
        overall_pass = False
    else:
        overall_status = BLOCKED
        overall_pass = False
    gates["overall_pass"] = _make_gate(overall_status, overall_blockers, [request_binding.sha256])

    evaluated_wavs = [{"path": str(item[2].path), "sha256": item[2].sha256, "bytes": int(item[2].path.stat().st_size)} for item in mapped_pairs]
    report = {
        "schema_name": "wave64_foley_force_alignment_report",
        "report_version": 1,
        "run_id": run_id,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "take_id": take_id,
        "is_synthetic": is_synthetic,
        "request_binding": {"path": str(request_binding.path), "sha256": request_binding.sha256},
        "artifact_bindings": {
            "visual_contact_manifest": _binding_or_none(visual_binding),
            "wave22_force_event_manifest": _binding_or_none(wave22_binding),
            "wave30_audio_event_manifest": _binding_or_none(wave30_binding),
            "wave31_force_event_manifest": _binding_or_none(wave31_binding),
            "runtime_proof": _binding_or_none(runtime_binding),
            "av_review_proof": _binding_or_none(review_binding),
            "production_alignment_bundle": _binding_or_none(bundle_binding),
            "authority_registry": _binding_or_none(authority_registry_binding),
            "visual_take_artifact": {
                "path": str(visual_info["visual_take_artifact"]["path"]),
                "sha256": visual_info["visual_take_artifact"]["sha256"],
                "bytes": visual_info["visual_take_artifact"]["bytes"],
                "media_type": visual_info["visual_take_artifact"]["media_type"],
            },
            "contact_evidence_artifact": {
                "path": str(visual_info["contact_evidence_artifact"]["path"]),
                "sha256": visual_info["contact_evidence_artifact"]["sha256"],
                "bytes": visual_info["contact_evidence_artifact"]["bytes"],
                "media_type": visual_info["contact_evidence_artifact"]["media_type"],
            },
            "evaluated_wav_bindings": evaluated_wavs,
        },
        "metrics": {
            "contact_edge_count": len(contact_edges),
            "force_event_count": len(force_events),
            "evaluated_wave30_event_count": len(mapped_pairs),
            "unmatched_wave30_event_count": len(false_event_blockers),
            "wav_metrics": wav_metrics_rows,
        },
        "gates": gates,
        "blockers": overall_blockers,
        "overall_pass": overall_pass,
    }
    _validate_schema(report, report_schema, "report")
    _write_json_atomic(output_path, report)
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
            raise InvalidInputError(f"root must match canonical project root ({CANONICAL_ROOT}); got {requested_root}")
        root = CANONICAL_ROOT
        request = _resolve_under_root(root, args.input, "input")
        output = _resolve_under_root(root, args.output, "output")
        return evaluate(root=root, request_path=request, output_path=output)
    except InvalidInputError as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: unexpected evaluator failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
