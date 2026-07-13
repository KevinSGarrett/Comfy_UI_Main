#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
ROW031_REQUIRED_TECHNICAL_GATES = (
    "audio_metadata_check",
    "prompt_alignment",
    "playback_review",
    "sync_evidence",
)
WAVE30_REQUIRED_TECHNICAL_HARD_GATES = (
    "decode",
    "duration",
    "loudness",
    "clipping",
    "sync",
    "voice_identity",
    "event_coverage",
    "mix_balance",
    "artifact_manifest",
)

GATES = (
    "full_duration_playback_review",
    "required_target_audio_check",
    "required_non_target_audio_scan",
    "clipping_noise_voice_ambience_foley_sync_check",
    "reject_on_any_global_audio_defect",
    "promotion_decision",
    "overall_pass",
)

CANONICAL_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_request.schema.json"
REPORT_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
ROW031_REPORT_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json"
ROW030_REPORT_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"
W30_EVENT_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json"
W30_MIX_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json"
W30_QA_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json"
REGISTRY_PATH = CANONICAL_ROOT / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key is not allowed: {key}")
        payload[key] = value
    return payload


def _load_json_strict(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_nonfinite_json,
        object_pairs_hook=_reject_duplicate_keys,
    )


def _validate_with_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.path)
        raise ValueError(f"{label} schema validation failed at {where}: {first.message}")


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _expect_exact_object_keys(payload: dict[str, Any], required: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(required - observed)
    extra = sorted(observed - required)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"unknown={','.join(extra)}")
        raise ValueError(f"{label} key mismatch ({'; '.join(parts)})")


def _expect_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _resolve_under_root(raw_path: str, label: str) -> Path:
    candidate = Path(raw_path).resolve()
    if not _is_under_root(candidate, CANONICAL_ROOT):
        raise ValueError(f"{label} escapes canonical root: {candidate}")
    return candidate


def _resolve_binding(binding: Any, label: str) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise ValueError(f"{label} must be object")
    _expect_exact_object_keys(binding, {"path", "sha256", "bytes"}, label)
    path = _resolve_under_root(_expect_str(binding.get("path"), f"{label}.path"), f"{label}.path")
    sha = _expect_str(binding.get("sha256"), f"{label}.sha256")
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ValueError(f"{label}.sha256 must be lowercase SHA-256")
    size = binding.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError(f"{label}.bytes must be a positive integer")
    if not path.is_file():
        raise ValueError(f"{label}.path does not exist: {path}")
    observed_bytes = path.stat().st_size
    if observed_bytes != size:
        raise ValueError(f"{label}.bytes mismatch ({size} != {observed_bytes})")
    observed_sha = _sha256_of(path)
    if observed_sha != sha:
        raise ValueError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return {"path": str(path), "sha256": sha, "bytes": size}


def _binding_matches(binding: dict[str, Any], candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    path_value = candidate.get("path")
    sha_value = candidate.get("sha256")
    bytes_value = candidate.get("bytes")
    if not isinstance(path_value, str) or not isinstance(sha_value, str):
        return False
    if bytes_value is not None and (not isinstance(bytes_value, int) or isinstance(bytes_value, bool) or bytes_value <= 0):
        return False
    if bytes_value is not None and bytes_value != binding["bytes"]:
        return False
    return str(Path(path_value).resolve()) == binding["path"] and sha_value == binding["sha256"]


def _binding_matches_with_bytes(binding: dict[str, Any], candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    path_value = candidate.get("path")
    sha_value = candidate.get("sha256")
    bytes_value = candidate.get("bytes")
    if not isinstance(path_value, str) or not isinstance(sha_value, str):
        return False
    if not isinstance(bytes_value, int) or isinstance(bytes_value, bool) or bytes_value <= 0:
        return False
    return (
        str(Path(path_value).resolve()) == binding["path"]
        and sha_value == binding["sha256"]
        and bytes_value == binding["bytes"]
    )


def _normalize_authority_id(value: Any, label: str) -> str:
    authority_id = _expect_str(value, label)
    if len(authority_id) > 256:
        raise ValueError(f"{label} exceeds max length")
    return authority_id


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(tmp_path, path)
        tmp_path.unlink()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_pcm_wav(path: Path, label: str) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            comp = handle.getcomptype()
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise ValueError(f"{label} is not valid WAV: {exc}") from exc
    if comp != "NONE":
        raise ValueError(f"{label} must be PCM")
    if channels <= 0 or sample_rate <= 0 or frame_count <= 0:
        raise ValueError(f"{label} has invalid WAV metrics")
    if sample_width != 2:
        raise ValueError(f"{label} must be 16-bit PCM")
    expected = frame_count * channels * sample_width
    if len(payload) != expected:
        raise ValueError(f"{label} payload mismatch ({len(payload)} != {expected})")
    samples = list(memoryview(payload).cast("h"))
    channels_data: list[list[float]] = [[] for _ in range(channels)]
    for idx, sample in enumerate(samples):
        channels_data[idx % channels].append(float(sample) / 32768.0)
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": frame_count / float(sample_rate),
        "channels_data": channels_data,
    }


def _normalize_windows(raw: Any, label: str, max_duration: float) -> list[tuple[float, float]]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be array")
    out: list[tuple[float, float]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{idx}] must be object")
        _expect_exact_object_keys(item, {"start_seconds", "end_seconds"}, f"{label}[{idx}]")
        start = float(item["start_seconds"])
        end = float(item["end_seconds"])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError(f"{label}[{idx}] invalid range")
        if end > max_duration + 1e-9:
            raise ValueError(f"{label}[{idx}] exceeds duration")
        out.append((start, end))
    out.sort()
    merged: list[tuple[float, float]] = []
    for start, end in out:
        if not merged or start > merged[-1][1] + 1e-9:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _windows_equal(a: list[tuple[float, float]], b: list[tuple[float, float]], tol: float = 1e-6) -> bool:
    if len(a) != len(b):
        return False
    for idx in range(len(a)):
        if abs(a[idx][0] - b[idx][0]) > tol or abs(a[idx][1] - b[idx][1]) > tol:
            return False
    return True


def _intervals_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return min(a[1], b[1]) > max(a[0], b[0]) + 1e-9


def _mask_for_windows(frame_count: int, sample_rate: int, windows: list[tuple[float, float]]) -> list[bool]:
    mask = [False] * frame_count
    for start, end in windows:
        start_i = max(0, int(math.floor(start * sample_rate)))
        end_i = min(frame_count, int(math.ceil(end * sample_rate)))
        for idx in range(start_i, end_i):
            mask[idx] = True
    return mask


def _rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / float(len(values)))


def _run_lengths(mask: list[bool]) -> list[int]:
    out: list[int] = []
    run = 0
    for flag in mask:
        if flag:
            run += 1
        elif run > 0:
            out.append(run)
            run = 0
    if run > 0:
        out.append(run)
    return out


def _validate_registry_shape(registry: Any) -> dict[str, Any]:
    if not isinstance(registry, dict):
        raise ValueError("registry must be object")
    required_top_level = {
        "schema_name",
        "registry_version",
        "required_row031_technical_gates",
        "window_rules",
        "non_target_rules",
        "global_audio_rules",
        "production_rules",
    }
    _expect_exact_object_keys(
        registry,
        required_top_level,
        "registry",
    )
    if registry.get("schema_name") != "wave64_global_audio_review_gate_rules":
        raise ValueError("registry.schema_name mismatch")
    if registry.get("registry_version") != 1:
        raise ValueError("registry.registry_version must be 1")

    row031_gates = registry.get("required_row031_technical_gates")
    if not isinstance(row031_gates, list) or sorted(row031_gates) != sorted(ROW031_REQUIRED_TECHNICAL_GATES):
        raise ValueError("registry.required_row031_technical_gates must match exact required set")

    window_rules = registry.get("window_rules")
    if not isinstance(window_rules, dict):
        raise ValueError("registry.window_rules must be object")
    _expect_exact_object_keys(
        window_rules,
        {"target_padding_before_seconds", "target_padding_after_seconds", "max_total_target_window_seconds"},
        "registry.window_rules",
    )
    before = float(window_rules.get("target_padding_before_seconds"))
    after = float(window_rules.get("target_padding_after_seconds"))
    max_window = float(window_rules.get("max_total_target_window_seconds"))
    if not math.isfinite(before) or not math.isfinite(after) or before < 0 or after < 0:
        raise ValueError("registry.window_rules padding must be finite and >= 0")
    if before > 0.25 or after > 0.25:
        raise ValueError("registry.window_rules padding exceeds 0.25 second safety ceiling")
    if not math.isfinite(max_window) or max_window <= 0 or max_window > 60.0:
        raise ValueError("registry.window_rules.max_total_target_window_seconds must be in (0, 60]")

    non_target_rules = registry.get("non_target_rules")
    if not isinstance(non_target_rules, dict):
        raise ValueError("registry.non_target_rules must be object")
    _expect_exact_object_keys(
        non_target_rules,
        {"max_outside_target_diff_rms", "max_outside_target_peak_delta", "max_duration_delta_seconds", "per_target_min_rms_delta"},
        "registry.non_target_rules",
    )
    non_target_ceilings = {
        "max_outside_target_diff_rms": 0.05,
        "max_outside_target_peak_delta": 0.10,
        "max_duration_delta_seconds": 0.10,
        "per_target_min_rms_delta": 0.10,
    }
    for key, ceiling in non_target_ceilings.items():
        value = float(non_target_rules.get(key))
        if not math.isfinite(value) or value < 0 or value > ceiling:
            raise ValueError(f"registry.non_target_rules.{key} must be finite and in [0, {ceiling}]")
    if float(non_target_rules["per_target_min_rms_delta"]) <= 0:
        raise ValueError("registry.non_target_rules.per_target_min_rms_delta must be > 0")

    global_rules = registry.get("global_audio_rules")
    if not isinstance(global_rules, dict):
        raise ValueError("registry.global_audio_rules must be object")
    _expect_exact_object_keys(
        global_rules,
        {
            "max_clipping_ratio",
            "min_clipping_run_samples",
            "max_click_ratio",
            "click_delta_threshold",
            "silence_rms_threshold",
            "max_silence_run_seconds",
            "loudness_window_seconds",
            "max_loudness_jump_db",
            "max_channel_imbalance_db",
            "required_event_min_rms",
            "max_single_channel_clipping_regression_ratio",
            "max_single_channel_dropout_regression_seconds",
        },
        "registry.global_audio_rules",
    )
    global_ceilings = {
        "max_clipping_ratio": 0.01,
        "max_click_ratio": 0.01,
        "click_delta_threshold": 1.50,
        "silence_rms_threshold": 0.02,
        "max_silence_run_seconds": 1.0,
        "loudness_window_seconds": 1.0,
        "max_loudness_jump_db": 30.0,
        "max_channel_imbalance_db": 6.0,
        "required_event_min_rms": 0.10,
        "max_single_channel_clipping_regression_ratio": 0.01,
        "max_single_channel_dropout_regression_seconds": 0.50,
    }
    for key, ceiling in global_ceilings.items():
        value = float(global_rules.get(key))
        if not math.isfinite(value) or value < 0 or value > ceiling:
            raise ValueError(f"registry.global_audio_rules.{key} must be finite and in [0, {ceiling}]")
    for key in ("click_delta_threshold", "silence_rms_threshold", "max_silence_run_seconds", "loudness_window_seconds", "max_loudness_jump_db", "max_channel_imbalance_db", "required_event_min_rms"):
        if float(global_rules[key]) <= 0:
            raise ValueError(f"registry.global_audio_rules.{key} must be > 0")
    min_clipping_run_samples = global_rules.get("min_clipping_run_samples")
    if not isinstance(min_clipping_run_samples, int) or isinstance(min_clipping_run_samples, bool) or min_clipping_run_samples < 1:
        raise ValueError("registry.global_audio_rules.min_clipping_run_samples must be integer >= 1")

    prod = registry.get("production_rules")
    if not isinstance(prod, dict):
        raise ValueError("registry.production_rules must be object")
    _expect_exact_object_keys(
        prod,
        {
            "require_non_synthetic_lineage",
            "require_technical_capture",
            "require_row031_promotion_pass",
            "require_upstream_production_eligible",
            "approved_production_baselines",
            "approved_production_bundles",
        },
        "registry.production_rules",
    )
    if not isinstance(prod.get("approved_production_baselines"), list):
        raise ValueError("registry.production_rules.approved_production_baselines must be array")
    if not isinstance(prod.get("approved_production_bundles"), list):
        raise ValueError("registry.production_rules.approved_production_bundles must be array")
    for idx, item in enumerate(prod.get("approved_production_baselines", [])):
        if not isinstance(item, dict):
            raise ValueError(f"registry.production_rules.approved_production_baselines[{idx}] must be object")
        _expect_exact_object_keys(
            item,
            {
                "scene_id",
                "baseline_authority_id",
                "baseline_run_id",
                "synthetic_only",
                "baseline_mix_wav_sha256",
                "baseline_row031_sha256",
            },
            f"registry.production_rules.approved_production_baselines[{idx}]",
        )
        _expect_str(item.get("scene_id"), f"registry.production_rules.approved_production_baselines[{idx}].scene_id")
        _normalize_authority_id(
            item.get("baseline_authority_id"), f"registry.production_rules.approved_production_baselines[{idx}].baseline_authority_id"
        )
        _expect_str(item.get("baseline_run_id"), f"registry.production_rules.approved_production_baselines[{idx}].baseline_run_id")
        if item.get("synthetic_only") is not False:
            raise ValueError(f"registry.production_rules.approved_production_baselines[{idx}].synthetic_only must be false")
        _expect_sha = _expect_str(item.get("baseline_mix_wav_sha256"), f"registry.production_rules.approved_production_baselines[{idx}].baseline_mix_wav_sha256")
        if len(_expect_sha) != 64 or any(ch not in "0123456789abcdef" for ch in _expect_sha):
            raise ValueError(f"registry.production_rules.approved_production_baselines[{idx}].baseline_mix_wav_sha256 must be lowercase SHA-256")
        _expect_sha = _expect_str(item.get("baseline_row031_sha256"), f"registry.production_rules.approved_production_baselines[{idx}].baseline_row031_sha256")
        if len(_expect_sha) != 64 or any(ch not in "0123456789abcdef" for ch in _expect_sha):
            raise ValueError(f"registry.production_rules.approved_production_baselines[{idx}].baseline_row031_sha256 must be lowercase SHA-256")
    for idx, item in enumerate(prod.get("approved_production_bundles", [])):
        if not isinstance(item, dict):
            raise ValueError(f"registry.production_rules.approved_production_bundles[{idx}] must be object")
        _expect_exact_object_keys(
            item,
            {
                "scene_id",
                "baseline_authority_id",
                "bundle_authority_id",
                "bundle_id",
                "baseline_run_id",
                "candidate_run_id",
                "review_run_id",
                "synthetic_only",
                "bundle_sha256",
                "baseline_mix_wav_sha256",
                "baseline_row031_sha256",
                "candidate_mix_wav_sha256",
                "candidate_row031_sha256",
                "candidate_wave30_qa_sha256",
            },
            f"registry.production_rules.approved_production_bundles[{idx}]",
        )
        _expect_str(item.get("scene_id"), f"registry.production_rules.approved_production_bundles[{idx}].scene_id")
        base_authority = _normalize_authority_id(
            item.get("baseline_authority_id"), f"registry.production_rules.approved_production_bundles[{idx}].baseline_authority_id"
        )
        bundle_authority = _normalize_authority_id(
            item.get("bundle_authority_id"), f"registry.production_rules.approved_production_bundles[{idx}].bundle_authority_id"
        )
        if base_authority == bundle_authority:
            raise ValueError(f"registry.production_rules.approved_production_bundles[{idx}] baseline_authority_id must differ from bundle_authority_id")
        _expect_str(item.get("bundle_id"), f"registry.production_rules.approved_production_bundles[{idx}].bundle_id")
        _expect_str(item.get("baseline_run_id"), f"registry.production_rules.approved_production_bundles[{idx}].baseline_run_id")
        _expect_str(item.get("candidate_run_id"), f"registry.production_rules.approved_production_bundles[{idx}].candidate_run_id")
        _expect_str(item.get("review_run_id"), f"registry.production_rules.approved_production_bundles[{idx}].review_run_id")
        if item.get("synthetic_only") is not False:
            raise ValueError(f"registry.production_rules.approved_production_bundles[{idx}].synthetic_only must be false")
        for key in (
            "bundle_sha256",
            "baseline_mix_wav_sha256",
            "baseline_row031_sha256",
            "candidate_mix_wav_sha256",
            "candidate_row031_sha256",
            "candidate_wave30_qa_sha256",
        ):
            value = _expect_str(item.get(key), f"registry.production_rules.approved_production_bundles[{idx}].{key}")
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError(f"registry.production_rules.approved_production_bundles[{idx}].{key} must be lowercase SHA-256")
    if prod.get("require_non_synthetic_lineage") is not True:
        raise ValueError("registry.production_rules.require_non_synthetic_lineage must remain true")
    if prod.get("require_technical_capture") is not True:
        raise ValueError("registry.production_rules.require_technical_capture must remain true")
    if prod.get("require_row031_promotion_pass") is not True:
        raise ValueError("registry.production_rules.require_row031_promotion_pass must remain true")
    if prod.get("require_upstream_production_eligible") is not True:
        raise ValueError("registry.production_rules.require_upstream_production_eligible must remain true")
    baseline_ids = [item["baseline_authority_id"] for item in prod["approved_production_baselines"]]
    if len(baseline_ids) != len(set(baseline_ids)):
        raise ValueError("registry.production_rules.approved_production_baselines baseline_authority_id must be unique")
    bundle_ids = [item["bundle_id"] for item in prod["approved_production_bundles"]]
    if len(bundle_ids) != len(set(bundle_ids)):
        raise ValueError("registry.production_rules.approved_production_bundles bundle_id must be unique")
    return registry


def _event_map(event_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events_raw = event_manifest.get("audio_events")
    if not isinstance(events_raw, list) or not events_raw:
        raise ValueError("wave30_event_manifest.audio_events must be non-empty array")
    out: dict[str, dict[str, Any]] = {}
    for idx, event in enumerate(events_raw):
        if not isinstance(event, dict):
            raise ValueError(f"wave30_event_manifest.audio_events[{idx}] must be object")
        event_id = _expect_str(event.get("audio_event_id"), f"audio_events[{idx}].audio_event_id")
        start = float(event.get("start_seconds"))
        end = float(event.get("end_seconds"))
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError(f"invalid event window for {event_id}")
        if event_id in out:
            raise ValueError(f"duplicate audio_event_id in event manifest: {event_id}")
        out[event_id] = event
    return out


def _mix_meta_map(mix_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = mix_manifest.get("mix_event_metadata")
    if not isinstance(rows, list):
        raise ValueError("wave30_mix_manifest.mix_event_metadata must be array")
    out: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"mix_event_metadata[{idx}] must be object")
        event_id = _expect_str(row.get("audio_event_id"), f"mix_event_metadata[{idx}].audio_event_id")
        if event_id in out:
            raise ValueError(f"duplicate mix_event_metadata audio_event_id: {event_id}")
        out[event_id] = row
    return out


def _validate_wave30_chain(
    *,
    side: str,
    event_manifest: dict[str, Any],
    mix_manifest: dict[str, Any],
    qa_report: dict[str, Any],
    expected_run_id: str,
    expected_is_synthetic: bool,
    event_binding: dict[str, Any],
    mix_binding: dict[str, Any],
    wav_binding: dict[str, Any],
    wav_metrics: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if event_manifest.get("run_id") != expected_run_id or mix_manifest.get("run_id") != expected_run_id or qa_report.get("run_id") != expected_run_id:
        issues.append(f"{side} wave30 run_id lineage mismatch")
    if (
        event_manifest.get("is_synthetic") is not expected_is_synthetic
        or mix_manifest.get("is_synthetic") is not expected_is_synthetic
        or qa_report.get("is_synthetic") is not expected_is_synthetic
    ):
        issues.append(f"{side} wave30 synthetic lineage mismatch")
    if event_manifest.get("scene_id") != mix_manifest.get("scene_id"):
        issues.append(f"{side} wave30 scene_id mismatch between event/mix manifests")

    mix_bindings = mix_manifest.get("event_manifest_bindings")
    if not isinstance(mix_bindings, list) or len(mix_bindings) < 1 or not any(_binding_matches(event_binding, item) for item in mix_bindings):
        issues.append(f"{side} wave30 mix manifest missing event manifest binding")
    if not _binding_matches(event_binding, qa_report.get("event_manifest_binding")):
        issues.append(f"{side} wave30 qa event manifest binding mismatch")
    if not _binding_matches(mix_binding, qa_report.get("mix_manifest_binding")):
        issues.append(f"{side} wave30 qa mix manifest binding mismatch")

    hard = qa_report.get("hard_gate_statuses")
    if not isinstance(hard, dict):
        issues.append(f"{side} wave30 qa hard_gate_statuses must be object")
    else:
        for gate in WAVE30_REQUIRED_TECHNICAL_HARD_GATES:
            if hard.get(gate) != "pass":
                issues.append(f"{side} wave30 required technical hard gate not pass: {gate}")
    proof = qa_report.get("proof_verification")
    if not isinstance(proof, dict):
        issues.append(f"{side} wave30 qa proof_verification must be object")
    elif proof.get("artifact_bindings_verified") is not True:
        issues.append(f"{side} wave30 proof_verification.artifact_bindings_verified must be true")

    mixdown = mix_manifest.get("mixdown_artifact")
    if not _binding_matches_with_bytes(wav_binding, mixdown):
        issues.append(f"{side} wave30 mixdown_artifact binding mismatch")
    mix_technical = mix_manifest.get("mix_technical")
    if not isinstance(mix_technical, dict):
        issues.append(f"{side} wave30 mix_technical must be object")
    else:
        if mix_technical.get("sample_rate_hz") != wav_metrics["sample_rate_hz"]:
            issues.append(f"{side} wave30 mix_technical sample_rate_hz mismatch")
        if mix_technical.get("channels") != wav_metrics["channels"]:
            issues.append(f"{side} wave30 mix_technical channels mismatch")
        if mix_technical.get("sample_width_bytes") != wav_metrics["sample_width_bytes"]:
            issues.append(f"{side} wave30 mix_technical sample_width_bytes mismatch")
        if mix_technical.get("frame_count") != wav_metrics["frame_count"]:
            issues.append(f"{side} wave30 mix_technical frame_count mismatch")

    try:
        event_ids = set(_event_map(event_manifest).keys())
        mix_ids = set(_mix_meta_map(mix_manifest).keys())
        if event_ids != mix_ids:
            issues.append(f"{side} wave30 event ids must exactly match mix_event_metadata ids")
    except ValueError as exc:
        issues.append(str(exc))
    return issues


def _recompute_production_eligible(qa_report: dict[str, Any], run_id: str) -> bool:
    hard = qa_report.get("hard_gate_statuses")
    proof = qa_report.get("proof_verification")
    flags = qa_report.get("computed_flags")
    if not isinstance(hard, dict) or not isinstance(proof, dict) or not isinstance(flags, dict):
        return False
    required_hard = (
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
    return bool(
        all(hard.get(name) == "pass" for name in required_hard)
        and proof.get("runtime_proof_verified") is True
        and proof.get("audio_review_verified") is True
        and proof.get("artifact_bindings_verified") is True
        and flags.get("all_hard_gates_passed") is True
        and flags.get("production_eligible") is True
        and qa_report.get("promotion_decision") == "promote"
        and qa_report.get("is_synthetic") is False
        and qa_report.get("run_id") == run_id
    )


def _derive_target_windows(
    target_ids: list[str],
    baseline_events: dict[str, dict[str, Any]],
    candidate_events: dict[str, dict[str, Any]],
    padding_before: float,
    padding_after: float,
    duration: float,
) -> list[tuple[float, float]]:
    raw: list[tuple[float, float]] = []
    for event_id in target_ids:
        for source_name, source_map in (("baseline", baseline_events), ("candidate", candidate_events)):
            if event_id not in source_map:
                raise ValueError(f"target event missing from {source_name} event manifest: {event_id}")
            event = source_map[event_id]
            start = float(event["start_seconds"])
            end = float(event["end_seconds"])
            raw.append((max(0.0, start - padding_before), min(duration, end + padding_after)))
    raw.sort()
    merged: list[tuple[float, float]] = []
    for start, end in raw:
        if not merged or start > merged[-1][1] + 1e-9:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _channel_scan(
    baseline_channel: list[float],
    candidate_channel: list[float],
    outside_mask: list[bool],
    active_mask: list[bool],
    sample_rate: int,
    rules: dict[str, Any],
) -> tuple[list[str], dict[str, float]]:
    blockers: list[str] = []
    candidate_abs = [abs(v) for v in candidate_channel]
    baseline_abs = [abs(v) for v in baseline_channel]
    clipping_flags = [value >= 0.999 for value in candidate_abs]
    baseline_clipping_flags = [value >= 0.999 for value in baseline_abs]
    clipping_ratio = sum(1 for flag in clipping_flags if flag) / float(max(1, len(clipping_flags)))
    baseline_clipping_ratio = sum(1 for flag in baseline_clipping_flags if flag) / float(max(1, len(baseline_clipping_flags)))
    if clipping_ratio > float(rules["max_clipping_ratio"]):
        blockers.append("candidate clipping ratio exceeds threshold")
    run_lengths = _run_lengths(clipping_flags)
    if run_lengths and max(run_lengths) >= int(rules["min_clipping_run_samples"]):
        blockers.append("candidate clipping run length exceeds threshold")
    if clipping_ratio - baseline_clipping_ratio > float(rules["max_single_channel_clipping_regression_ratio"]):
        blockers.append("single-channel clipping regression detected")

    click_threshold = float(rules["click_delta_threshold"])
    click_deltas = [abs(candidate_channel[i] - candidate_channel[i - 1]) for i in range(1, len(candidate_channel))]
    click_flags = [delta > click_threshold for delta in click_deltas]
    click_ratio = sum(1 for flag in click_flags if flag) / float(max(1, len(click_flags)))
    max_click_delta = max(click_deltas, default=0.0)
    if max_click_delta > click_threshold:
        blockers.append("candidate click peak exceeds threshold")
    if click_ratio > float(rules["max_click_ratio"]):
        blockers.append("candidate click ratio exceeds threshold")

    window_frames = max(1, int(round(sample_rate * float(rules["loudness_window_seconds"]))))
    loudness_vals: list[float] = []
    for start in range(0, len(candidate_channel), window_frames):
        chunk = candidate_channel[start : start + window_frames]
        loudness_vals.append(20.0 * math.log10(max(_rms(chunk), 1e-12)))
    max_loudness_jump = 0.0
    for i in range(1, len(loudness_vals)):
        max_loudness_jump = max(max_loudness_jump, abs(loudness_vals[i] - loudness_vals[i - 1]))
    if max_loudness_jump > float(rules["max_loudness_jump_db"]):
        blockers.append("candidate loudness jump exceeds threshold")

    silence_threshold = float(rules["silence_rms_threshold"])
    silent_in_active = [active_mask[i] and candidate_abs[i] <= silence_threshold for i in range(len(candidate_channel))]
    baseline_silent_in_active = [active_mask[i] and baseline_abs[i] <= silence_threshold for i in range(len(baseline_channel))]
    silence_run = max(_run_lengths(silent_in_active), default=0) / float(sample_rate)
    baseline_silence_run = max(_run_lengths(baseline_silent_in_active), default=0) / float(sample_rate)
    if silence_run > float(rules["max_silence_run_seconds"]):
        blockers.append("candidate dropout or unexpected silence in active event window")
    if silence_run - baseline_silence_run > float(rules["max_single_channel_dropout_regression_seconds"]):
        blockers.append("single-channel dropout regression detected")

    diffs: list[float] = []
    peak = 0.0
    for i in range(len(outside_mask)):
        if not outside_mask[i]:
            continue
        delta = abs(candidate_channel[i] - baseline_channel[i])
        diffs.append(delta)
        peak = max(peak, delta)
    outside_rms = _rms(diffs)
    return blockers, {
        "clipping_ratio": clipping_ratio,
        "click_ratio": click_ratio,
        "max_loudness_jump_db": max_loudness_jump,
        "outside_target_diff_rms": outside_rms,
        "outside_target_peak_delta": peak,
        "max_active_silence_seconds": silence_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    if not _is_under_root(input_path, CANONICAL_ROOT):
        print(f"ERROR: input path escapes canonical project root: {input_path}")
        return 1
    if not _is_under_root(output_path, CANONICAL_ROOT):
        print(f"ERROR: output path escapes canonical project root: {output_path}")
        return 1
    if output_path.exists():
        print(f"ERROR: output collision detected: {output_path}")
        return 1

    try:
        request_payload = _load_json_strict(input_path)
        request_schema = _load_json_strict(REQUEST_SCHEMA)
        report_schema = _load_json_strict(REPORT_SCHEMA)
        row031_schema = _load_json_strict(ROW031_REPORT_SCHEMA)
        row030_schema = _load_json_strict(ROW030_REPORT_SCHEMA)
        w30_event_schema = _load_json_strict(W30_EVENT_SCHEMA)
        w30_mix_schema = _load_json_strict(W30_MIX_SCHEMA)
        w30_qa_schema = _load_json_strict(W30_QA_SCHEMA)
        registry = _validate_registry_shape(_load_json_strict(REGISTRY_PATH))
        _validate_with_schema(request_payload, request_schema, "request")

        req_output_path = _resolve_under_root(_expect_str(request_payload["output_report_path"], "request.output_report_path"), "request.output_report_path")
        if req_output_path != output_path:
            raise ValueError("request.output_report_path must exactly match --output path")

        review_run_id = _expect_str(request_payload["review_run_id"], "request.review_run_id")
        baseline_run_id = _expect_str(request_payload["baseline_run_id"], "request.baseline_run_id")
        candidate_run_id = _expect_str(request_payload["candidate_run_id"], "request.candidate_run_id")
        if len({review_run_id, baseline_run_id, candidate_run_id}) != 3:
            raise ValueError("review_run_id, baseline_run_id, and candidate_run_id must be distinct")
        is_synthetic = _expect_bool(request_payload["is_synthetic"], "request.is_synthetic")
        capture_mode = _expect_str(request_payload["capture_mode"], "request.capture_mode")

        b_mix = _resolve_binding(request_payload["baseline_mix_wav_binding"], "request.baseline_mix_wav_binding")
        c_mix = _resolve_binding(request_payload["candidate_mix_wav_binding"], "request.candidate_mix_wav_binding")
        b_row031 = _resolve_binding(request_payload["baseline_row031_strict_report_binding"], "request.baseline_row031_strict_report_binding")
        c_row031 = _resolve_binding(request_payload["candidate_row031_strict_report_binding"], "request.candidate_row031_strict_report_binding")
        b_evt_bind = _resolve_binding(request_payload["baseline_wave30_event_manifest_binding"], "request.baseline_wave30_event_manifest_binding")
        c_evt_bind = _resolve_binding(request_payload["candidate_wave30_event_manifest_binding"], "request.candidate_wave30_event_manifest_binding")
        b_mix_bind = _resolve_binding(request_payload["baseline_wave30_mix_manifest_binding"], "request.baseline_wave30_mix_manifest_binding")
        c_mix_bind = _resolve_binding(request_payload["candidate_wave30_mix_manifest_binding"], "request.candidate_wave30_mix_manifest_binding")
        b_qa_bind = _resolve_binding(request_payload["baseline_wave30_qa_report_binding"], "request.baseline_wave30_qa_report_binding")
        c_qa_bind = _resolve_binding(request_payload["candidate_wave30_qa_report_binding"], "request.candidate_wave30_qa_report_binding")
        prod_bundle = None
        if request_payload.get("production_bundle_binding") is not None:
            prod_bundle = _resolve_binding(request_payload["production_bundle_binding"], "request.production_bundle_binding")

        baseline_wav = _read_pcm_wav(Path(b_mix["path"]), "baseline_mix_wav")
        candidate_wav = _read_pcm_wav(Path(c_mix["path"]), "candidate_mix_wav")
        if baseline_wav["sample_rate_hz"] != candidate_wav["sample_rate_hz"] or baseline_wav["channels"] != candidate_wav["channels"]:
            raise ValueError("baseline/candidate WAV technical format mismatch")
        if baseline_wav["sample_width_bytes"] != candidate_wav["sample_width_bytes"]:
            raise ValueError("baseline/candidate WAV sample format mismatch")

        eval_frames = min(baseline_wav["frame_count"], candidate_wav["frame_count"])
        eval_duration = eval_frames / float(candidate_wav["sample_rate_hz"])
        duration_delta = abs(candidate_wav["duration_seconds"] - baseline_wav["duration_seconds"])

        baseline_row031 = _load_json_strict(Path(b_row031["path"]))
        candidate_row031 = _load_json_strict(Path(c_row031["path"]))
        _validate_with_schema(baseline_row031, row031_schema, "baseline_row031_report")
        _validate_with_schema(candidate_row031, row031_schema, "candidate_row031_report")

        b_evt = _load_json_strict(Path(b_evt_bind["path"]))
        c_evt = _load_json_strict(Path(c_evt_bind["path"]))
        b_mix_manifest = _load_json_strict(Path(b_mix_bind["path"]))
        c_mix_manifest = _load_json_strict(Path(c_mix_bind["path"]))
        b_qa = _load_json_strict(Path(b_qa_bind["path"]))
        c_qa = _load_json_strict(Path(c_qa_bind["path"]))
        _validate_with_schema(b_evt, w30_event_schema, "baseline_wave30_event_manifest")
        _validate_with_schema(c_evt, w30_event_schema, "candidate_wave30_event_manifest")
        _validate_with_schema(b_mix_manifest, w30_mix_schema, "baseline_wave30_mix_manifest")
        _validate_with_schema(c_mix_manifest, w30_mix_schema, "candidate_wave30_mix_manifest")
        _validate_with_schema(b_qa, w30_qa_schema, "baseline_wave30_qa_report")
        _validate_with_schema(c_qa, w30_qa_schema, "candidate_wave30_qa_report")

        blockers: list[str] = []
        review_lineage_blockers: list[str] = []
        target_blockers: list[str] = []
        non_target_blockers: list[str] = []
        global_blockers: list[str] = []
        if baseline_wav["frame_count"] != candidate_wav["frame_count"]:
            global_blockers.append("baseline/candidate frame counts differ; full-duration comparison requires exact coverage")
        gates = {gate: FAIL for gate in GATES}

        row031_required = set(registry["required_row031_technical_gates"])
        for label, report, expected_run_id, wav_binding, evt_binding, mix_binding, qa_binding in (
            ("baseline_row031_report", baseline_row031, baseline_run_id, b_mix, b_evt_bind, b_mix_bind, b_qa_bind),
            ("candidate_row031_report", candidate_row031, candidate_run_id, c_mix, c_evt_bind, c_mix_bind, c_qa_bind),
        ):
            if report.get("run_id") != expected_run_id:
                review_lineage_blockers.append(f"{label} run_id mismatch")
            if report.get("is_synthetic") is not is_synthetic:
                review_lineage_blockers.append(f"{label} is_synthetic mismatch")
            if report.get("capture_mode") != capture_mode:
                review_lineage_blockers.append(f"{label} capture_mode mismatch")
            report_gates = report.get("gates")
            if not isinstance(report_gates, dict):
                review_lineage_blockers.append(f"{label} gates missing")
                continue
            missing = [name for name in row031_required if report_gates.get(name) != PASS]
            if missing:
                review_lineage_blockers.append(f"{label} required technical gates not PASS: {sorted(missing)}")
            artifact_bindings = report.get("artifact_bindings")
            if not isinstance(artifact_bindings, dict):
                review_lineage_blockers.append(f"{label} artifact_bindings missing")
                continue
            if not _binding_matches(wav_binding, artifact_bindings.get("mix_wav")):
                review_lineage_blockers.append(f"{label} mix_wav binding mismatch")
            if not _binding_matches(evt_binding, artifact_bindings.get("wave30_event_manifest")):
                review_lineage_blockers.append(f"{label} wave30_event_manifest binding mismatch")
            if not _binding_matches(mix_binding, artifact_bindings.get("wave30_mix_manifest")):
                review_lineage_blockers.append(f"{label} wave30_mix_manifest binding mismatch")
            if not _binding_matches(qa_binding, artifact_bindings.get("wave30_qa_report")):
                review_lineage_blockers.append(f"{label} wave30_qa_report binding mismatch")

        b_evt_map = _event_map(b_evt)
        c_evt_map = _event_map(c_evt)
        b_mix_meta = _mix_meta_map(b_mix_manifest)
        c_mix_meta = _mix_meta_map(c_mix_manifest)

        for side, evt, mix_manifest, qa_report, run_id, evt_bind, mix_bind, wav_bind, wav_metrics in (
            ("baseline", b_evt, b_mix_manifest, b_qa, baseline_run_id, b_evt_bind, b_mix_bind, b_mix, baseline_wav),
            ("candidate", c_evt, c_mix_manifest, c_qa, candidate_run_id, c_evt_bind, c_mix_bind, c_mix, candidate_wav),
        ):
            review_lineage_blockers.extend(
                _validate_wave30_chain(
                    side=side,
                    event_manifest=evt,
                    mix_manifest=mix_manifest,
                    qa_report=qa_report,
                    expected_run_id=run_id,
                    expected_is_synthetic=is_synthetic,
                    event_binding=evt_bind,
                    mix_binding=mix_bind,
                    wav_binding=wav_bind,
                    wav_metrics=wav_metrics,
                )
            )

        if b_evt.get("scene_id") != c_evt.get("scene_id"):
            review_lineage_blockers.append("baseline/candidate scene_id mismatch")

        localized = request_payload["localized_change_declaration"]
        change_kind = _expect_str(localized["change_kind"], "localized_change_declaration.change_kind")
        audio_change_expected = _expect_bool(localized["audio_change_expected"], "localized_change_declaration.audio_change_expected")
        target_ids = [_expect_str(item, "target_audio_event_ids[]") for item in localized["target_audio_event_ids"]]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("target_audio_event_ids must be unique")
        all_event_ids = set(b_evt_map.keys()) | set(c_evt_map.keys())
        if not all_event_ids:
            raise ValueError("wave30 event manifests have no audio_events")
        non_target_expected = sorted(all_event_ids - set(target_ids))
        caller_non_target = sorted(_expect_str(item, "non_target_audio_event_ids[]") for item in localized["non_target_audio_event_ids"])
        if caller_non_target != non_target_expected:
            non_target_blockers.append("caller non_target_audio_event_ids mismatch against canonical recomputation")

        if change_kind == "audio_localized":
            if not audio_change_expected:
                target_blockers.append("audio_localized requires audio_change_expected=true")
            if not target_ids:
                target_blockers.append("audio_localized requires non-empty target_audio_event_ids")
            if not localized["allowed_change_windows_seconds"]:
                target_blockers.append("audio_localized requires non-empty allowed_change_windows_seconds")
        elif change_kind == "visual_localized":
            if audio_change_expected:
                if not target_ids:
                    target_blockers.append("visual_localized with audio_change_expected=true requires non-empty target_audio_event_ids")
                if not localized["allowed_change_windows_seconds"]:
                    target_blockers.append("visual_localized with audio_change_expected=true requires non-empty allowed_change_windows_seconds")
                candidate_artifacts = candidate_row031.get("artifact_bindings")
                if not isinstance(candidate_artifacts, dict):
                    review_lineage_blockers.append("candidate_row031_report artifact_bindings missing")
                else:
                    row030_binding = candidate_artifacts.get("row030_av_sync_report")
                    if not isinstance(row030_binding, dict):
                        review_lineage_blockers.append("visual_localized with audio_change_expected=true requires candidate row031 row030_av_sync_report binding")
                    else:
                        try:
                            resolved_row030 = _resolve_binding(
                                row030_binding,
                                "candidate_row031_report.artifact_bindings.row030_av_sync_report",
                            )
                            row030_report = _load_json_strict(Path(resolved_row030["path"]))
                            _validate_with_schema(row030_report, row030_schema, "candidate_row030_av_sync_report")
                            if row030_report.get("run_id") != candidate_run_id:
                                raise ValueError("candidate row030 AV sync report run_id mismatch")
                            if row030_report.get("is_synthetic") is not is_synthetic:
                                raise ValueError("candidate row030 AV sync report synthetic lineage mismatch")
                            source_audio = row030_report.get("artifact_bindings", {}).get("source_audio_mix_artifact")
                            if not _binding_matches_with_bytes(c_mix, source_audio):
                                raise ValueError("candidate row030 AV sync source audio binding mismatch")
                            row030_gates = row030_report.get("gates")
                            required_row030_gates = (
                                "sync_offset_threshold",
                                "drift_check",
                                "mux_manifest",
                                "event_owner_alignment",
                                "av_review_record",
                            )
                            if not isinstance(row030_gates, dict):
                                raise ValueError("candidate row030 AV sync gates missing")
                            for gate_name in required_row030_gates:
                                gate = row030_gates.get(gate_name)
                                if not isinstance(gate, dict) or gate.get("status") != PASS:
                                    raise ValueError(f"candidate row030 AV sync required gate not PASS: {gate_name}")
                        except Exception as exc:
                            review_lineage_blockers.append(str(exc))
            else:
                if target_ids:
                    target_blockers.append("visual_localized with audio_change_expected=false requires empty target_audio_event_ids")
                if localized["allowed_change_windows_seconds"]:
                    target_blockers.append("visual_localized with audio_change_expected=false requires empty allowed_change_windows_seconds")
                if b_mix["sha256"] != c_mix["sha256"]:
                    target_blockers.append("visual_localized with audio_change_expected=false requires byte-identical baseline and candidate WAV")
        else:
            raise ValueError("localized_change_declaration.change_kind is invalid")

        derived_windows = _derive_target_windows(
            target_ids,
            b_evt_map,
            c_evt_map,
            float(registry["window_rules"]["target_padding_before_seconds"]),
            float(registry["window_rules"]["target_padding_after_seconds"]),
            eval_duration,
        )
        total_window_seconds = sum(end - start for start, end in derived_windows)
        if total_window_seconds > float(registry["window_rules"]["max_total_target_window_seconds"]):
            target_blockers.append("derived target windows exceed registry max duration")
        caller_windows = _normalize_windows(
            localized["allowed_change_windows_seconds"],
            "localized_change_declaration.allowed_change_windows_seconds",
            eval_duration,
        )
        if not _windows_equal(caller_windows, derived_windows):
            target_blockers.append("caller change windows do not exactly match derived target windows")

        for event_id in non_target_expected:
            if event_id not in b_evt_map or event_id not in c_evt_map:
                non_target_blockers.append(f"non-target event missing baseline/candidate pair: {event_id}")
                continue
            if b_evt_map[event_id] != c_evt_map[event_id]:
                non_target_blockers.append(f"non-target event record changed: {event_id}")
            if event_id not in b_mix_meta or event_id not in c_mix_meta:
                non_target_blockers.append(f"non-target mix_event_metadata missing: {event_id}")
                continue
            if b_mix_meta[event_id] != c_mix_meta[event_id]:
                non_target_blockers.append(f"non-target mix_event_metadata changed: {event_id}")

        target_window_records: list[tuple[str, str, tuple[float, float]]] = []
        padding_before = float(registry["window_rules"]["target_padding_before_seconds"])
        padding_after = float(registry["window_rules"]["target_padding_after_seconds"])
        for target_id in target_ids:
            if target_id not in b_evt_map or target_id not in c_evt_map:
                continue
            target_start = max(
                0.0,
                min(float(b_evt_map[target_id]["start_seconds"]), float(c_evt_map[target_id]["start_seconds"]))
                - padding_before,
            )
            target_end = min(
                eval_duration,
                max(float(b_evt_map[target_id]["end_seconds"]), float(c_evt_map[target_id]["end_seconds"]))
                + padding_after,
            )
            target_layer = _expect_str(c_evt_map[target_id].get("layer"), f"target_event[{target_id}].layer")
            target_window_records.append((target_id, target_layer, (target_start, target_end)))
        for event_id in non_target_expected:
            if event_id not in c_evt_map:
                continue
            non_target_event = c_evt_map[event_id]
            non_target_window = (float(non_target_event["start_seconds"]), float(non_target_event["end_seconds"]))
            non_target_layer = _expect_str(non_target_event.get("layer"), f"non_target_event[{event_id}].layer")
            non_target_sync = _expect_str(non_target_event.get("sync_class"), f"non_target_event[{event_id}].sync_class")
            if non_target_sync in {"ambient_free", "music_scene_phase"}:
                continue
            for target_id, target_layer, target_window in target_window_records:
                if not _intervals_overlap(non_target_window, target_window):
                    continue
                if non_target_layer == target_layer:
                    non_target_blockers.append(
                        f"same-layer foreground non-target overlap with target-derived window: {event_id} vs {target_id}"
                    )
                    break

        target_mask = _mask_for_windows(eval_frames, candidate_wav["sample_rate_hz"], derived_windows)
        outside_mask = [not flag for flag in target_mask]
        active_windows = []
        for event in c_evt_map.values():
            active_windows.append((float(event["start_seconds"]), float(event["end_seconds"])))
        active_mask = _mask_for_windows(eval_frames, candidate_wav["sample_rate_hz"], active_windows)

        if duration_delta > float(registry["non_target_rules"]["max_duration_delta_seconds"]):
            non_target_blockers.append("evaluated duration delta exceeds tolerance")

        per_target_rms: dict[str, float] = {}
        min_target_rms = None
        max_target_rms = None
        min_required_target_delta = float(registry["non_target_rules"]["per_target_min_rms_delta"])
        for target_id in target_ids:
            if target_id not in b_evt_map or target_id not in c_evt_map:
                target_blockers.append(f"target event missing baseline/candidate pair: {target_id}")
                continue
            b_event = b_evt_map[target_id]
            c_event = c_evt_map[target_id]
            start_s = max(0.0, min(float(b_event["start_seconds"]), float(c_event["start_seconds"])))
            end_s = min(eval_duration, max(float(b_event["end_seconds"]), float(c_event["end_seconds"])))
            start_i = max(0, int(math.floor(start_s * candidate_wav["sample_rate_hz"])))
            end_i = min(eval_frames, int(math.ceil(end_s * candidate_wav["sample_rate_hz"])))
            best = 0.0
            for ch in range(candidate_wav["channels"]):
                diffs = [candidate_wav["channels_data"][ch][i] - baseline_wav["channels_data"][ch][i] for i in range(start_i, end_i)]
                best = max(best, _rms(diffs))
            per_target_rms[target_id] = best
            min_target_rms = best if min_target_rms is None else min(min_target_rms, best)
            max_target_rms = best if max_target_rms is None else max(max_target_rms, best)
            if audio_change_expected and best < min_required_target_delta:
                target_blockers.append(f"target event RMS delta below threshold: {target_id}")

        channel_metrics: list[dict[str, float]] = []
        for ch in range(candidate_wav["channels"]):
            baseline_channel = baseline_wav["channels_data"][ch][:eval_frames]
            candidate_channel = candidate_wav["channels_data"][ch][:eval_frames]
            scan_blockers, metrics = _channel_scan(
                baseline_channel,
                candidate_channel,
                outside_mask,
                active_mask,
                candidate_wav["sample_rate_hz"],
                registry["global_audio_rules"],
            )
            channel_metrics.append(metrics)
            global_blockers.extend([f"channel {ch}: {item}" for item in scan_blockers])
            if metrics["outside_target_diff_rms"] > float(registry["non_target_rules"]["max_outside_target_diff_rms"]):
                non_target_blockers.append(f"channel {ch}: non-target waveform regression outside target windows")
            if metrics["outside_target_peak_delta"] > float(registry["non_target_rules"]["max_outside_target_peak_delta"]):
                non_target_blockers.append(f"channel {ch}: non-target peak regression outside target windows")

        if candidate_wav["channels"] >= 2:
            left = _rms(candidate_wav["channels_data"][0][:eval_frames])
            right = _rms(candidate_wav["channels_data"][1][:eval_frames])
            imbalance = abs(20.0 * math.log10(max(left, 1e-12) / max(right, 1e-12)))
            if imbalance > float(registry["global_audio_rules"]["max_channel_imbalance_db"]):
                global_blockers.append("candidate channel imbalance exceeds threshold")
        else:
            imbalance = 0.0

        for target_id in target_ids:
            if target_id not in c_evt_map:
                continue
            event = c_evt_map[target_id]
            start_i = max(0, int(math.floor(float(event["start_seconds"]) * candidate_wav["sample_rate_hz"])))
            end_i = min(eval_frames, int(math.ceil(float(event["end_seconds"]) * candidate_wav["sample_rate_hz"])))
            max_rms = 0.0
            for ch in range(candidate_wav["channels"]):
                max_rms = max(max_rms, _rms(candidate_wav["channels_data"][ch][start_i:end_i]))
            if max_rms < float(registry["global_audio_rules"]["required_event_min_rms"]):
                target_blockers.append(f"required target event energy too low: {target_id}")

        technical_blockers = review_lineage_blockers + target_blockers + non_target_blockers + global_blockers
        blockers.extend(review_lineage_blockers)
        blockers.extend(target_blockers)
        blockers.extend(non_target_blockers)
        blockers.extend(global_blockers)

        gates["full_duration_playback_review"] = PASS if not review_lineage_blockers else FAIL
        gates["required_target_audio_check"] = PASS if not target_blockers else FAIL
        gates["required_non_target_audio_scan"] = PASS if not non_target_blockers else FAIL
        gates["clipping_noise_voice_ambience_foley_sync_check"] = PASS if not (review_lineage_blockers or global_blockers) else FAIL
        gates["reject_on_any_global_audio_defect"] = PASS if not technical_blockers else FAIL

        if review_lineage_blockers:
            baseline_wave30_eligible = False
            candidate_wave30_eligible = False
        else:
            baseline_wave30_eligible = _recompute_production_eligible(b_qa, baseline_run_id)
            candidate_wave30_eligible = _recompute_production_eligible(c_qa, candidate_run_id)
        baseline_row031_gates = baseline_row031.get("gates", {})
        candidate_row031_gates = candidate_row031.get("gates", {})
        baseline_row031_metrics = baseline_row031.get("computed_metrics")
        candidate_row031_metrics = candidate_row031.get("computed_metrics")

        authority_evidence = {
            "baseline_authority_match": False,
            "bundle_authority_match": False,
            "bundle_content_match": False,
        }
        production_blockers: list[str] = []
        prod_rules = registry["production_rules"]
        if is_synthetic and bool(prod_rules["require_non_synthetic_lineage"]):
            production_blockers.append("production decision requires non-synthetic lineage")
        if capture_mode != "technical_capture" and bool(prod_rules["require_technical_capture"]):
            production_blockers.append("production decision requires technical_capture")
        if bool(prod_rules["require_upstream_production_eligible"]) and not (baseline_wave30_eligible and candidate_wave30_eligible):
            production_blockers.append("production decision requires recomputed baseline and candidate Wave30 eligibility")
        if isinstance(baseline_row031_metrics, dict) and isinstance(candidate_row031_metrics, dict):
            if baseline_row031_metrics.get("upstream_production_eligible") is not baseline_wave30_eligible:
                production_blockers.append("baseline row031 upstream_production_eligible disagreement")
            if candidate_row031_metrics.get("upstream_production_eligible") is not candidate_wave30_eligible:
                production_blockers.append("candidate row031 upstream_production_eligible disagreement")
        else:
            production_blockers.append("row031 computed_metrics.upstream_production_eligible is required for production checks")
        if bool(prod_rules["require_row031_promotion_pass"]):
            if baseline_row031_gates.get("promotion_decision") != PASS or candidate_row031_gates.get("promotion_decision") != PASS:
                production_blockers.append("production decision requires row031 promotion_decision PASS for baseline and candidate")
            if baseline_row031_gates.get("overall_pass") != PASS or candidate_row031_gates.get("overall_pass") != PASS:
                production_blockers.append("production decision requires row031 overall_pass PASS for baseline and candidate")

        if prod_bundle is None:
            production_blockers.append("production bundle binding is required for production PASS")
        else:
            bundle_payload = _load_json_strict(Path(prod_bundle["path"]))
            if not isinstance(bundle_payload, dict):
                production_blockers.append("production bundle content must be object")
            else:
                required_bundle_keys = {
                    "schema_name",
                    "schema_version",
                    "bundle_id",
                    "scene_id",
                    "baseline_authority_id",
                    "bundle_authority_id",
                    "baseline_run_id",
                    "candidate_run_id",
                    "review_run_id",
                    "synthetic_only",
                    "baseline_mix_wav_sha256",
                    "baseline_row031_sha256",
                    "candidate_mix_wav_sha256",
                    "candidate_row031_sha256",
                    "candidate_wave30_qa_sha256",
                }
                try:
                    _expect_exact_object_keys(bundle_payload, required_bundle_keys, "production_bundle")
                    if bundle_payload.get("schema_name") != "wave64_global_audio_production_bundle":
                        raise ValueError("production bundle schema_name mismatch")
                    if bundle_payload.get("schema_version") != 1:
                        raise ValueError("production bundle schema_version must be 1")
                    _expect_str(bundle_payload.get("bundle_id"), "production_bundle.bundle_id")
                    if bundle_payload.get("scene_id") != b_evt.get("scene_id"):
                        raise ValueError("production bundle scene_id mismatch")
                    if bundle_payload.get("baseline_run_id") != baseline_run_id:
                        raise ValueError("production bundle baseline_run_id mismatch")
                    if bundle_payload.get("candidate_run_id") != candidate_run_id:
                        raise ValueError("production bundle candidate_run_id mismatch")
                    if bundle_payload.get("review_run_id") != review_run_id:
                        raise ValueError("production bundle review_run_id mismatch")
                    if bundle_payload.get("synthetic_only") is not False:
                        raise ValueError("production bundle synthetic_only must be false")
                    if bundle_payload.get("baseline_mix_wav_sha256") != b_mix["sha256"]:
                        raise ValueError("production bundle baseline_mix_wav_sha256 mismatch")
                    if bundle_payload.get("baseline_row031_sha256") != b_row031["sha256"]:
                        raise ValueError("production bundle baseline_row031_sha256 mismatch")
                    if bundle_payload.get("candidate_mix_wav_sha256") != c_mix["sha256"]:
                        raise ValueError("production bundle candidate_mix_wav_sha256 mismatch")
                    if bundle_payload.get("candidate_row031_sha256") != c_row031["sha256"]:
                        raise ValueError("production bundle candidate_row031_sha256 mismatch")
                    if bundle_payload.get("candidate_wave30_qa_sha256") != c_qa_bind["sha256"]:
                        raise ValueError("production bundle candidate_wave30_qa_sha256 mismatch")
                    if bundle_payload.get("baseline_authority_id") == bundle_payload.get("bundle_authority_id"):
                        raise ValueError("production bundle baseline_authority_id must differ from bundle_authority_id")
                    authority_evidence["bundle_content_match"] = True
                except ValueError as exc:
                    production_blockers.append(str(exc))

                expected_baseline_record = {
                    "scene_id": b_evt.get("scene_id"),
                    "baseline_authority_id": bundle_payload.get("baseline_authority_id"),
                    "baseline_run_id": baseline_run_id,
                    "synthetic_only": False,
                    "baseline_mix_wav_sha256": b_mix["sha256"],
                    "baseline_row031_sha256": b_row031["sha256"],
                }
                baseline_match = any(item == expected_baseline_record for item in prod_rules["approved_production_baselines"])
                authority_evidence["baseline_authority_match"] = baseline_match
                if not baseline_match:
                    production_blockers.append("baseline production authority is not approved")

                expected_bundle_record = {
                    "scene_id": b_evt.get("scene_id"),
                    "baseline_authority_id": bundle_payload.get("baseline_authority_id"),
                    "bundle_authority_id": bundle_payload.get("bundle_authority_id"),
                    "bundle_id": bundle_payload.get("bundle_id"),
                    "baseline_run_id": baseline_run_id,
                    "candidate_run_id": candidate_run_id,
                    "review_run_id": review_run_id,
                    "synthetic_only": False,
                    "bundle_sha256": prod_bundle["sha256"],
                    "baseline_mix_wav_sha256": b_mix["sha256"],
                    "baseline_row031_sha256": b_row031["sha256"],
                    "candidate_mix_wav_sha256": c_mix["sha256"],
                    "candidate_row031_sha256": c_row031["sha256"],
                    "candidate_wave30_qa_sha256": c_qa_bind["sha256"],
                }
                bundle_match = any(item == expected_bundle_record for item in prod_rules["approved_production_bundles"])
                authority_evidence["bundle_authority_match"] = bundle_match
                if not bundle_match:
                    production_blockers.append("production bundle authority is not approved")

        if production_blockers or any(gates[name] != PASS for name in GATES[:5]):
            gates["promotion_decision"] = BLOCKED
            blockers.extend(production_blockers)
            if any(gates[name] != PASS for name in GATES[:5]):
                blockers.append("promotion decision requires all technical gates PASS")
        else:
            gates["promotion_decision"] = PASS

        if blockers:
            if any(gates[name] == FAIL for name in GATES if name != "overall_pass"):
                gates["overall_pass"] = FAIL
            else:
                gates["overall_pass"] = BLOCKED
        elif all(gates[name] == PASS for name in GATES if name != "overall_pass"):
            gates["overall_pass"] = PASS
        elif any(gates[name] == FAIL for name in GATES if name != "overall_pass"):
            gates["overall_pass"] = FAIL
        else:
            gates["overall_pass"] = BLOCKED
        exit_code = 0 if gates["overall_pass"] == PASS and not blockers else 2

        worst_idx = 0
        if channel_metrics:
            worst_idx = max(range(len(channel_metrics)), key=lambda i: channel_metrics[i]["outside_target_diff_rms"])
        max_outside_target_peak_delta = max((item["outside_target_peak_delta"] for item in channel_metrics), default=0.0)
        max_outside_target_diff_rms = max((item["outside_target_diff_rms"] for item in channel_metrics), default=0.0)
        max_clipping_ratio = max((item["clipping_ratio"] for item in channel_metrics), default=0.0)
        max_click_ratio = max((item["click_ratio"] for item in channel_metrics), default=0.0)
        max_loudness_jump_db = max((item["max_loudness_jump_db"] for item in channel_metrics), default=0.0)

        artifact_bindings: dict[str, Any] = {
            "baseline_mix_wav": b_mix,
            "candidate_mix_wav": c_mix,
            "baseline_row031_strict_report": b_row031,
            "candidate_row031_strict_report": c_row031,
            "baseline_wave30_event_manifest": b_evt_bind,
            "candidate_wave30_event_manifest": c_evt_bind,
            "baseline_wave30_mix_manifest": b_mix_bind,
            "candidate_wave30_mix_manifest": c_mix_bind,
            "baseline_wave30_qa_report": b_qa_bind,
            "candidate_wave30_qa_report": c_qa_bind,
        }
        if prod_bundle is not None:
            artifact_bindings["production_bundle"] = prod_bundle

        report_payload: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_global_audio_review_report",
            "report_version": 1,
            "review_run_id": review_run_id,
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": candidate_run_id,
            "is_synthetic": is_synthetic,
            "capture_mode": capture_mode,
            "artifact_bindings": artifact_bindings,
            "localized_change_context": {
                "change_kind": change_kind,
                "audio_change_expected": audio_change_expected,
                "target_audio_event_ids": sorted(target_ids),
                "derived_non_target_audio_event_ids": non_target_expected,
                "derived_allowed_change_windows_seconds": [{"start_seconds": s, "end_seconds": e} for s, e in derived_windows],
                "caller_allowed_change_windows_seconds": [{"start_seconds": s, "end_seconds": e} for s, e in caller_windows],
            },
            "gates": gates,
            "computed_metrics": {
                "outside_target_diff_rms": max_outside_target_diff_rms,
                "outside_target_peak_delta": max_outside_target_peak_delta,
                "inside_target_diff_rms_per_target": per_target_rms,
                "inside_target_diff_rms_min": 0.0 if min_target_rms is None else min_target_rms,
                "inside_target_diff_rms_max": 0.0 if max_target_rms is None else max_target_rms,
                "candidate_clipping_ratio": max_clipping_ratio,
                "candidate_click_ratio": max_click_ratio,
                "candidate_max_loudness_jump_db": max_loudness_jump_db,
                "candidate_channel_imbalance_db": imbalance,
                "candidate_duration_seconds": candidate_wav["duration_seconds"],
                "evaluated_duration_seconds": eval_duration,
                "duration_delta_seconds": duration_delta,
                "worst_channel_index": worst_idx,
                "channel_count": candidate_wav["channels"],
            },
            "blockers": sorted(set(blockers)),
            "review_lineage_blockers": sorted(set(review_lineage_blockers)),
            "production_authority_evidence": authority_evidence,
            "final_decision": {"overall_status": gates["overall_pass"], "exit_code": exit_code},
        }
        _validate_with_schema(report_payload, report_schema, "report")
        _write_json_atomic(output_path, report_payload)
        print(str(output_path))
        return exit_code
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
