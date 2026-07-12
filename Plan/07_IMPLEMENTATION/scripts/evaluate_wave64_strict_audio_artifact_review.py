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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_request.schema.json"
REPORT_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json"
REGISTRY_PATH = PROJECT_ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"
W30_EVENT_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json"
W30_MIX_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json"
W30_REPORT_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json"
ROW030_SYNC_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"

GATES = (
    "audio_metadata_check",
    "playback_review",
    "prompt_alignment",
    "sync_evidence",
    "promotion_decision",
    "overall_pass",
)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UPSTREAM_PRODUCTION_REQUIRED_HARD_GATES = (
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
IDENTITY_RECORD_KEYS = {
    "proof_kind",
    "producer_id",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "authority_id",
    "synthetic_only",
}


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


def _expect_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_string(value, label)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ValueError(f"{label} must be lowercase 64-char hex")
    return sha


def _validate_with_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(item) for item in first.path)
        raise ValueError(f"{label} schema validation failed at {location}: {first.message}")


def _resolve_binding(binding: Any, label: str, *, require_exists: bool = True) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise ValueError(f"{label} must be an object")
    _expect_exact_object_keys(binding, {"path", "sha256", "bytes"}, label)
    raw_path = _expect_string(binding.get("path"), f"{label}.path")
    sha = _expect_string(binding.get("sha256"), f"{label}.sha256")
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ValueError(f"{label}.sha256 must be lowercase 64-char hex")
    byte_count = binding.get("bytes")
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
        raise ValueError(f"{label}.bytes must be a positive integer")
    resolved = Path(raw_path).resolve()
    if not _is_under_root(resolved, PROJECT_ROOT):
        raise ValueError(f"{label}.path escapes canonical project root: {resolved}")
    if require_exists and not resolved.is_file():
        raise ValueError(f"{label}.path does not exist: {resolved}")
    if require_exists:
        observed_bytes = resolved.stat().st_size
        if observed_bytes != byte_count:
            raise ValueError(f"{label}.bytes mismatch ({byte_count} != {observed_bytes})")
        observed_sha = _sha256_of(resolved)
        if observed_sha != sha:
            raise ValueError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return {"path": str(resolved), "sha256": sha, "bytes": byte_count}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_wav_metrics(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = int(handle.getnchannels())
            sample_rate = int(handle.getframerate())
            sample_width = int(handle.getsampwidth())
            frame_count = int(handle.getnframes())
            data = handle.readframes(frame_count)
    except wave.Error as exc:
        raise ValueError(f"mix_wav_binding is not a valid WAV: {exc}") from exc
    expected = channels * sample_width * frame_count
    if len(data) != expected:
        raise ValueError(f"WAV payload byte mismatch ({len(data)} != {expected})")
    if channels <= 0 or sample_rate <= 0 or sample_width <= 0 or frame_count <= 0:
        raise ValueError("WAV metrics must be positive")
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": frame_count / float(sample_rate),
    }


def _levenshtein(tokens_a: list[str], tokens_b: list[str]) -> int:
    if not tokens_a:
        return len(tokens_b)
    if not tokens_b:
        return len(tokens_a)
    prev = list(range(len(tokens_b) + 1))
    for i, token_a in enumerate(tokens_a, start=1):
        cur = [i]
        for j, token_b in enumerate(tokens_b, start=1):
            cost = 0 if token_a == token_b else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def _normalized_wer(expected: str, observed: str) -> float:
    expected_tokens = [token for token in expected.strip().lower().split() if token]
    observed_tokens = [token for token in observed.strip().lower().split() if token]
    baseline = max(1, len(expected_tokens))
    return _levenshtein(expected_tokens, observed_tokens) / float(baseline)


def _binding_matches(binding: dict[str, Any], path_value: Any, sha_value: Any) -> bool:
    if not isinstance(path_value, str) or not isinstance(sha_value, str):
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


def _normalize_identity_record(
    payload: Any,
    *,
    label: str,
    expected_proof_kind: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be object")
    _expect_exact_object_keys(payload, IDENTITY_RECORD_KEYS, label)
    proof_kind = _expect_string(payload.get("proof_kind"), f"{label}.proof_kind")
    if expected_proof_kind is not None and proof_kind != expected_proof_kind:
        raise ValueError(f"{label}.proof_kind must be {expected_proof_kind}")
    normalized = {
        "proof_kind": proof_kind,
        "producer_id": _expect_string(payload.get("producer_id"), f"{label}.producer_id"),
        "engine": _expect_string(payload.get("engine"), f"{label}.engine"),
        "model": _expect_string(payload.get("model"), f"{label}.model"),
        "model_version": _expect_string(payload.get("model_version"), f"{label}.model_version"),
        "model_sha256": _expect_sha256(payload.get("model_sha256"), f"{label}.model_sha256"),
        "authority_id": _expect_string(payload.get("authority_id"), f"{label}.authority_id"),
        "synthetic_only": _expect_bool(payload.get("synthetic_only"), f"{label}.synthetic_only"),
    }
    return normalized


def _identity_key(record: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        record["producer_id"],
        record["engine"],
        record["model"],
        record["model_version"],
        record["model_sha256"],
        record["authority_id"],
    )


def _extract_identity_from_proof(
    payload: dict[str, Any],
    *,
    label: str,
    expected_proof_kind: str,
) -> dict[str, Any]:
    return _normalize_identity_record(
        {
            "proof_kind": payload.get("proof_kind"),
            "producer_id": payload.get("producer_id"),
            "engine": payload.get("engine"),
            "model": payload.get("model"),
            "model_version": payload.get("model_version"),
            "model_sha256": payload.get("model_sha256"),
            "authority_id": payload.get("authority_id"),
            "synthetic_only": payload.get("synthetic_only"),
        },
        label=label,
        expected_proof_kind=expected_proof_kind,
    )


def _evaluate_identity_policy(
    *,
    record: dict[str, Any],
    request_is_synthetic: bool,
    proof_is_synthetic: bool,
    production_evidence: bool,
    gate_label: str,
    blockers: list[str],
) -> bool:
    if record["synthetic_only"]:
        if not request_is_synthetic:
            blockers.append(f"{gate_label} synthetic-only producer cannot be used on non-synthetic request")
            return False
        if not proof_is_synthetic:
            blockers.append(f"{gate_label} synthetic-only producer requires proof.is_synthetic=true")
            return False
        if production_evidence:
            blockers.append(f"{gate_label} synthetic-only producer requires production_evidence=false")
            return False
        return True
    if request_is_synthetic:
        blockers.append(f"{gate_label} non-synthetic producer cannot be used on synthetic request")
        return False
    if proof_is_synthetic:
        blockers.append(f"{gate_label} non-synthetic producer requires proof.is_synthetic=false")
        return False
    if not production_evidence:
        blockers.append(f"{gate_label} non-synthetic producer requires production_evidence=true")
        return False
    return True


def _evaluate_prompt_alignment(
    prompt_reference: dict[str, Any],
    prompt_alignment: dict[str, Any],
    registry: dict[str, Any],
    *,
    mix_wav_sha256: str,
    prompt_reference_sha256: str,
    request_is_synthetic: bool,
    capture_mode: str,
    blockers: list[str],
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    metrics = {
        "normalized_wer": None,
        "wer_threshold": None,
        "expected_attribute_coverage": False,
    }
    producer_identity: dict[str, Any] | None = None

    try:
        _expect_exact_object_keys(
            prompt_reference,
            {"schema_name", "prompt_kind", "expected_text", "expected_attributes", "video_pairing_required"},
            "prompt_reference",
        )
        if prompt_reference.get("schema_name") != "wave64_prompt_reference":
            raise ValueError("prompt_reference.schema_name mismatch")
        prompt_kind = _expect_string(prompt_reference.get("prompt_kind"), "prompt_reference.prompt_kind")
        if prompt_kind not in {"speech", "music", "ambience", "mixed"}:
            raise ValueError("prompt_reference.prompt_kind must be one of speech/music/ambience/mixed")
        expected_text = prompt_reference.get("expected_text")
        if prompt_kind in {"speech", "mixed"}:
            expected_text = _expect_string(expected_text, "prompt_reference.expected_text")
        elif expected_text is None:
            expected_text = ""
        elif not isinstance(expected_text, str):
            raise ValueError("prompt_reference.expected_text must be string or null")
        expected_attributes = prompt_reference.get("expected_attributes")
        if not isinstance(expected_attributes, list) or not expected_attributes:
            raise ValueError("prompt_reference.expected_attributes must be a non-empty array")
        expected_attr_map: dict[str, str] = {}
        for idx, item in enumerate(expected_attributes):
            if not isinstance(item, dict):
                raise ValueError(f"prompt_reference.expected_attributes[{idx}] must be object")
            _expect_exact_object_keys(item, {"name", "value"}, f"prompt_reference.expected_attributes[{idx}]")
            name = _expect_string(item.get("name"), f"prompt_reference.expected_attributes[{idx}].name")
            value = _expect_string(item.get("value"), f"prompt_reference.expected_attributes[{idx}].value")
            if name in expected_attr_map:
                raise ValueError(f"prompt_reference.expected_attributes duplicate name: {name}")
            expected_attr_map[name] = value
        _expect_bool(prompt_reference.get("video_pairing_required"), "prompt_reference.video_pairing_required")

        _expect_exact_object_keys(
            prompt_alignment,
            {
                "schema_name",
                "proof_kind",
                "producer_id",
                "engine",
                "model",
                "model_version",
                "model_sha256",
                "authority_id",
                "synthetic_only",
                "audio_sha256",
                "prompt_reference_sha256",
                "observed_transcript",
                "observed_attributes",
                "self_authorized",
                "is_synthetic",
                "production_evidence",
            },
            "prompt_alignment_proof",
        )
        if prompt_alignment.get("schema_name") != "wave64_prompt_alignment_proof":
            raise ValueError("prompt_alignment_proof.schema_name mismatch")
        producer_identity = _extract_identity_from_proof(
            prompt_alignment,
            label="prompt_alignment_proof.identity",
            expected_proof_kind="prompt_alignment",
        )
        prompt_allowlist = registry.get("prompt_alignment_allowlist", [])
        if producer_identity not in prompt_allowlist:
            blockers.append("prompt alignment producer is not approved for strict authority")
            return BLOCKED, metrics, producer_identity
        if request_is_synthetic and capture_mode == "hand_authored_relabel":
            blockers.append("synthetic-only prompt producer cannot be used for hand_authored_relabel capture mode")
            return BLOCKED, metrics, producer_identity
        if _expect_bool(prompt_alignment.get("self_authorized"), "prompt_alignment_proof.self_authorized"):
            raise ValueError("prompt_alignment_proof.self_authorized must be false")
        if _expect_string(prompt_alignment.get("audio_sha256"), "prompt_alignment_proof.audio_sha256") != mix_wav_sha256:
            raise ValueError("prompt_alignment_proof.audio_sha256 mismatch")
        if (
            _expect_string(
                prompt_alignment.get("prompt_reference_sha256"),
                "prompt_alignment_proof.prompt_reference_sha256",
            )
            != prompt_reference_sha256
        ):
            raise ValueError("prompt_alignment_proof.prompt_reference_sha256 mismatch")
        proof_is_synthetic = _expect_bool(prompt_alignment.get("is_synthetic"), "prompt_alignment_proof.is_synthetic")
        production_evidence = _expect_bool(
            prompt_alignment.get("production_evidence"), "prompt_alignment_proof.production_evidence"
        )
        if not _evaluate_identity_policy(
            record=producer_identity,
            request_is_synthetic=request_is_synthetic,
            proof_is_synthetic=proof_is_synthetic,
            production_evidence=production_evidence,
            gate_label="prompt alignment",
            blockers=blockers,
        ):
            return BLOCKED, metrics, producer_identity
        observed_transcript = prompt_alignment.get("observed_transcript")
        if observed_transcript is None:
            observed_transcript = ""
        if not isinstance(observed_transcript, str):
            raise ValueError("prompt_alignment_proof.observed_transcript must be string or null")
        observed_attributes = prompt_alignment.get("observed_attributes")
        if not isinstance(observed_attributes, dict):
            raise ValueError("prompt_alignment_proof.observed_attributes must be object")
        observed_attr_map: dict[str, str] = {}
        for name, value in observed_attributes.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("prompt_alignment_proof.observed_attributes keys must be non-empty strings")
            if not isinstance(value, str):
                raise ValueError("prompt_alignment_proof.observed_attributes values must be strings")
            observed_attr_map[name.strip()] = value

        coverage = True
        for name, value in expected_attr_map.items():
            if observed_attr_map.get(name) != value:
                coverage = False
                break
        metrics["expected_attribute_coverage"] = coverage
        if not coverage:
            raise ValueError("prompt alignment expected attribute coverage failed")

        if prompt_kind in {"speech", "mixed"}:
            wer = _normalized_wer(expected_text, observed_transcript)
            thresholds = registry.get("wer_thresholds", {})
            threshold_value = thresholds.get(prompt_kind)
            if not isinstance(threshold_value, (int, float)) or isinstance(threshold_value, bool):
                raise ValueError(f"registry wer threshold missing for prompt kind: {prompt_kind}")
            threshold = float(threshold_value)
            if not math.isfinite(threshold) or threshold < 0:
                raise ValueError("registry wer threshold must be finite and >= 0")
            metrics["normalized_wer"] = wer
            metrics["wer_threshold"] = threshold
            if wer > threshold:
                raise ValueError(f"prompt alignment WER above threshold ({wer:.6f} > {threshold:.6f})")
        return PASS, metrics, producer_identity
    except ValueError as exc:
        blockers.append(str(exc))
        return FAIL, metrics, producer_identity


def _evaluate_playback_review(
    playback_binding: dict[str, Any] | None,
    registry: dict[str, Any],
    *,
    mix_wav_sha256: str,
    request_is_synthetic: bool,
    capture_mode: str,
    blockers: list[str],
) -> tuple[str, dict[str, Any] | None, bool]:
    if playback_binding is None:
        blockers.append("playback proof binding missing")
        return BLOCKED, None, False
    try:
        payload = _load_json_strict(Path(playback_binding["path"]))
        if not isinstance(payload, dict):
            raise ValueError("playback proof must be a JSON object")
        _expect_exact_object_keys(
            payload,
            {
                "schema_name",
                "proof_kind",
                "producer_id",
                "engine",
                "model",
                "model_version",
                "model_sha256",
                "authority_id",
                "synthetic_only",
                "audio_sha256",
                "is_synthetic",
                "production_evidence",
                "self_authorized",
                "sections_reviewed",
                "category_scores",
                "defects",
            },
            "playback_proof",
        )
        if payload.get("schema_name") != "wave64_playback_review_proof":
            raise ValueError("playback_proof.schema_name mismatch")
        producer_identity = _extract_identity_from_proof(
            payload,
            label="playback_proof.identity",
            expected_proof_kind="playback_review",
        )
        playback_allowlist = registry.get("playback_review_allowlist", [])
        if producer_identity not in playback_allowlist:
            blockers.append("playback producer is not approved for strict authority")
            return BLOCKED, producer_identity, False
        if request_is_synthetic and capture_mode == "hand_authored_relabel":
            blockers.append("synthetic-only playback producer cannot be used for hand_authored_relabel capture mode")
            return BLOCKED, producer_identity, False
        if _expect_bool(payload.get("self_authorized"), "playback_proof.self_authorized"):
            raise ValueError("playback_proof.self_authorized must be false")
        proof_is_synthetic = _expect_bool(payload.get("is_synthetic"), "playback_proof.is_synthetic")
        production_evidence = _expect_bool(payload.get("production_evidence"), "playback_proof.production_evidence")
        if not _evaluate_identity_policy(
            record=producer_identity,
            request_is_synthetic=request_is_synthetic,
            proof_is_synthetic=proof_is_synthetic,
            production_evidence=production_evidence,
            gate_label="playback",
            blockers=blockers,
        ):
            return BLOCKED, producer_identity, False
        if _expect_string(payload.get("audio_sha256"), "playback_proof.audio_sha256") != mix_wav_sha256:
            raise ValueError("playback_proof.audio_sha256 mismatch")

        sections_reviewed = payload.get("sections_reviewed")
        if not isinstance(sections_reviewed, list):
            raise ValueError("playback_proof.sections_reviewed must be an array")
        required_sections = set(registry.get("required_playback_sections", []))
        observed_sections = set()
        for idx, section in enumerate(sections_reviewed):
            observed_sections.add(_expect_string(section, f"playback_proof.sections_reviewed[{idx}]"))
        if required_sections - observed_sections:
            raise ValueError("playback proof missing required review sections")

        category_scores = payload.get("category_scores")
        if not isinstance(category_scores, dict):
            raise ValueError("playback_proof.category_scores must be an object")
        required_categories = set(registry.get("required_playback_categories", []))
        if set(category_scores.keys()) != required_categories:
            raise ValueError("playback proof category score keys mismatch")
        for category in required_categories:
            score = category_scores.get(category)
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise ValueError(f"playback category score for {category} must be numeric")
            value = float(score)
            if not math.isfinite(value) or value < 0.0 or value > 5.0:
                raise ValueError(f"playback category score for {category} must be in [0,5]")

        defects = payload.get("defects")
        if not isinstance(defects, list):
            raise ValueError("playback_proof.defects must be an array")
        blocking_codes = {
            code.strip().lower()
            for code in registry.get("blocking_defect_codes", [])
            if isinstance(code, str) and code.strip()
        }
        blocking_severities = {
            severity.strip().lower()
            for severity in registry.get("blocking_defect_severities", [])
            if isinstance(severity, str) and severity.strip()
        }
        blocking_found = False
        for idx, defect in enumerate(defects):
            if not isinstance(defect, dict):
                raise ValueError(f"playback_proof.defects[{idx}] must be object")
            _expect_exact_object_keys(defect, {"code", "severity", "description"}, f"playback_proof.defects[{idx}]")
            code = _expect_string(defect.get("code"), f"playback_proof.defects[{idx}].code").lower()
            severity = _expect_string(defect.get("severity"), f"playback_proof.defects[{idx}].severity").lower()
            _expect_string(defect.get("description"), f"playback_proof.defects[{idx}].description")
            if code in blocking_codes or severity in blocking_severities:
                blocking_found = True
        if blocking_found:
            blockers.append("playback proof contains blocking defects")
            return BLOCKED, producer_identity, True
        return PASS, producer_identity, False
    except ValueError as exc:
        blockers.append(str(exc))
        return FAIL, None, False


def _evaluate_sync_evidence(
    *,
    prompt_reference: dict[str, Any],
    row030_binding: dict[str, Any] | None,
    mix_wav_binding: dict[str, Any],
    run_id: str,
    is_synthetic: bool,
    capture_mode: str,
    row030_sync_schema: dict[str, Any],
    blockers: list[str],
) -> tuple[str, str | None]:
    video_pairing_required = bool(prompt_reference.get("video_pairing_required"))
    if not video_pairing_required:
        return PASS, "not_applicable_video_pairing_not_required_by_prompt_reference"
    if row030_binding is None:
        blockers.append("row030 AV sync report is required when video pairing is required")
        return BLOCKED, None
    try:
        row030 = _load_json_strict(Path(row030_binding["path"]))
        if not isinstance(row030, dict):
            raise ValueError("row030 AV sync report must be a JSON object")
        _validate_with_schema(row030, row030_sync_schema, "row030_av_sync_report")
        if row030.get("run_id") != run_id:
            raise ValueError("row030 AV sync report run_id mismatch")
        if row030.get("is_synthetic") is not is_synthetic:
            raise ValueError("row030 AV sync report synthetic state mismatch")
        if row030.get("evidence_origin") != capture_mode:
            raise ValueError("row030 AV sync report evidence_origin mismatch")
        artifact_bindings = row030.get("artifact_bindings")
        if not isinstance(artifact_bindings, dict):
            raise ValueError("row030 AV sync report artifact_bindings must be object")
        source_audio = artifact_bindings.get("source_audio_mix_artifact")
        if not _binding_matches_with_bytes(mix_wav_binding, source_audio):
            raise ValueError("row030 AV sync report source_audio_mix_artifact binding mismatch")
        gates = row030.get("gates")
        if not isinstance(gates, dict):
            raise ValueError("row030 AV sync report gates must be object")
        required_gates = (
            "sync_offset_threshold",
            "drift_check",
            "mux_manifest",
            "event_owner_alignment",
            "av_review_record",
        )
        for key in required_gates:
            gate = gates.get(key)
            if not isinstance(gate, dict) or not isinstance(gate.get("status"), str):
                raise ValueError(f"row030 AV sync gate {key} missing status")
            status = gate["status"]
            if status != PASS:
                blockers.append(f"row030 AV sync gate {key} is {status}")
                return FAIL, None
        return PASS, None
    except ValueError as exc:
        blockers.append(str(exc))
        return FAIL, None


def _evaluate_promotion(
    *,
    request_payload: dict[str, Any],
    upstream_production_eligible: bool,
    gate_states: dict[str, str],
    prompt_producer: dict[str, Any] | None,
    playback_producer: dict[str, Any] | None,
    production_bundle_binding: dict[str, Any] | None,
    registry: dict[str, Any],
    blockers: list[str],
) -> tuple[str, dict[str, Any] | None]:
    if request_payload["is_synthetic"]:
        blockers.append("synthetic requests cannot pass promotion decision")
        return BLOCKED, None
    if request_payload["capture_mode"] == "hand_authored_relabel":
        blockers.append("hand_authored_relabel cannot pass promotion decision")
        return BLOCKED, None
    prerequisites = (
        gate_states["audio_metadata_check"] == PASS
        and gate_states["prompt_alignment"] == PASS
        and gate_states["playback_review"] == PASS
        and gate_states["sync_evidence"] == PASS
    )
    if not prerequisites:
        blockers.append("promotion decision requires all technical gates to PASS")
        return BLOCKED, None
    if not upstream_production_eligible:
        blockers.append("upstream Wave30 QA report is not production eligible")
        return BLOCKED, None
    if not prompt_producer or not playback_producer:
        blockers.append("independent producer identities are required")
        return BLOCKED, None
    if _identity_key(prompt_producer) == _identity_key(playback_producer):
        blockers.append("independent non-synthetic producers are required")
        return BLOCKED, None
    if production_bundle_binding is None:
        blockers.append("production review bundle binding missing")
        return BLOCKED, None
    try:
        bundle = _load_json_strict(Path(production_bundle_binding["path"]))
        if not isinstance(bundle, dict):
            raise ValueError("production review bundle must be a JSON object")
        _expect_exact_object_keys(
            bundle,
            {
                "schema_name",
                "proof_kind",
                "producer_id",
                "engine",
                "model",
                "model_version",
                "model_sha256",
                "authority_id",
                "synthetic_only",
                "is_synthetic",
                "production_evidence",
                "bundle_sha256",
                "revoked",
            },
            "production_review_bundle",
        )
        if bundle.get("schema_name") != "wave64_production_review_bundle":
            raise ValueError("production_review_bundle.schema_name mismatch")
        producer_identity = _extract_identity_from_proof(
            bundle,
            label="production_review_bundle.identity",
            expected_proof_kind="production_review",
        )
        production_allowlist = registry.get("production_review_authorities", [])
        if producer_identity not in production_allowlist:
            blockers.append("production bundle producer is not allowlisted")
            return BLOCKED, producer_identity
        if producer_identity["synthetic_only"]:
            blockers.append("production bundle authority cannot be synthetic-only")
            return BLOCKED, producer_identity
        if (
            producer_identity["authority_id"] == prompt_producer["authority_id"]
            or producer_identity["authority_id"] == playback_producer["authority_id"]
        ):
            blockers.append("production bundle producer must be independent")
            return BLOCKED, producer_identity
        if _expect_bool(bundle.get("is_synthetic"), "production_review_bundle.is_synthetic"):
            blockers.append("production bundle cannot be synthetic")
            return BLOCKED, producer_identity
        if not _expect_bool(bundle.get("production_evidence"), "production_review_bundle.production_evidence"):
            blockers.append("production bundle must assert production evidence")
            return BLOCKED, producer_identity
        if _expect_bool(bundle.get("revoked"), "production_review_bundle.revoked"):
            blockers.append("production bundle is revoked")
            return BLOCKED, producer_identity
        _expect_string(bundle.get("bundle_sha256"), "production_review_bundle.bundle_sha256")
        allowlist = set(registry.get("production_review_bundle_allowlist", []))
        if production_bundle_binding["sha256"] not in allowlist:
            blockers.append("production bundle hash is not allowlisted")
            return BLOCKED, producer_identity
        return PASS, producer_identity
    except ValueError as exc:
        blockers.append(str(exc))
        return FAIL, None


def _evaluate_audio_metadata(
    *,
    run_id: str,
    is_synthetic: bool,
    binding_mix_wav: dict[str, Any],
    binding_event: dict[str, Any],
    binding_mix_manifest: dict[str, Any],
    binding_qa_report: dict[str, Any],
    event_manifest: Any,
    mix_manifest: Any,
    qa_report: Any,
    w30_event_schema: dict[str, Any],
    w30_mix_schema: dict[str, Any],
    w30_report_schema: dict[str, Any],
    required_upstream_technical_gates: list[Any],
    required_upstream_production_hard_gates: list[Any],
    blockers: list[str],
) -> tuple[str, bool]:
    try:
        if not isinstance(event_manifest, dict):
            raise ValueError("wave30_event_manifest must be a JSON object")
        if not isinstance(mix_manifest, dict):
            raise ValueError("wave30_mix_manifest must be a JSON object")
        if not isinstance(qa_report, dict):
            raise ValueError("wave30_qa_report must be a JSON object")

        _validate_with_schema(event_manifest, w30_event_schema, "wave30_event_manifest")
        _validate_with_schema(mix_manifest, w30_mix_schema, "wave30_mix_manifest")
        _validate_with_schema(qa_report, w30_report_schema, "wave30_qa_report")

        if event_manifest.get("run_id") != run_id or mix_manifest.get("run_id") != run_id or qa_report.get("run_id") != run_id:
            raise ValueError("run_id lineage mismatch across request and upstream artifacts")
        if event_manifest.get("is_synthetic") is not is_synthetic:
            raise ValueError("event manifest synthetic state mismatch")
        if mix_manifest.get("is_synthetic") is not is_synthetic:
            raise ValueError("mix manifest synthetic state mismatch")
        if qa_report.get("is_synthetic") is not is_synthetic:
            raise ValueError("qa report synthetic state mismatch")

        mix_bindings = mix_manifest.get("event_manifest_bindings")
        if not isinstance(mix_bindings, list) or len(mix_bindings) != 1:
            raise ValueError("mix manifest must contain one event manifest binding")
        upstream_mix_binding = mix_bindings[0]
        if not isinstance(upstream_mix_binding, dict) or not _binding_matches(
            binding_event,
            upstream_mix_binding.get("path"),
            upstream_mix_binding.get("sha256"),
        ):
            raise ValueError("mix manifest event manifest binding does not match request binding")

        qa_event_binding = qa_report.get("event_manifest_binding")
        qa_mix_binding = qa_report.get("mix_manifest_binding")
        if not isinstance(qa_event_binding, dict) or not _binding_matches(
            binding_event,
            qa_event_binding.get("path"),
            qa_event_binding.get("sha256"),
        ):
            raise ValueError("qa report event manifest binding mismatch")
        if not isinstance(qa_mix_binding, dict) or not _binding_matches(
            binding_mix_manifest,
            qa_mix_binding.get("path"),
            qa_mix_binding.get("sha256"),
        ):
            raise ValueError("qa report mix manifest binding mismatch")

        hard_gate_statuses = qa_report.get("hard_gate_statuses")
        if not isinstance(hard_gate_statuses, dict):
            raise ValueError("qa report hard_gate_statuses must be an object")
        for gate_name in required_upstream_technical_gates:
            if hard_gate_statuses.get(gate_name) != "pass":
                raise ValueError(f"upstream technical gate is not pass: {gate_name}")
        proof_verification = qa_report.get("proof_verification")
        if not isinstance(proof_verification, dict):
            raise ValueError("qa report proof_verification must be an object")
        if proof_verification.get("artifact_bindings_verified") is not True:
            raise ValueError("qa report proof_verification.artifact_bindings_verified must be true")

        wav_metrics = _read_wav_metrics(Path(binding_mix_wav["path"]))
        mix_technical = mix_manifest.get("mix_technical")
        if not isinstance(mix_technical, dict):
            raise ValueError("mix manifest mix_technical must be object")
        if wav_metrics["sample_rate_hz"] != mix_technical.get("sample_rate_hz"):
            raise ValueError("mix technical sample_rate_hz mismatch against decoded WAV")
        if wav_metrics["channels"] != mix_technical.get("channels"):
            raise ValueError("mix technical channels mismatch against decoded WAV")
        if wav_metrics["sample_width_bytes"] != mix_technical.get("sample_width_bytes"):
            raise ValueError("mix technical sample_width_bytes mismatch against decoded WAV")
        if wav_metrics["frame_count"] != mix_technical.get("frame_count"):
            raise ValueError("mix technical frame_count mismatch against decoded WAV")
        declared_duration = mix_technical.get("duration_seconds")
        if not isinstance(declared_duration, (int, float)) or isinstance(declared_duration, bool):
            raise ValueError("mix technical duration_seconds must be numeric")
        if abs(float(declared_duration) - wav_metrics["duration_seconds"]) > 1e-6:
            raise ValueError("mix technical duration_seconds mismatch against decoded WAV")
        mixdown = mix_manifest.get("mixdown_artifact")
        if not isinstance(mixdown, dict):
            raise ValueError("mix manifest mixdown_artifact must be object")
        if not _binding_matches(binding_mix_wav, mixdown.get("path"), mixdown.get("sha256")):
            raise ValueError("mix_wav binding must match upstream mixdown_artifact path/sha")

        computed_flags = qa_report.get("computed_flags")
        if not isinstance(computed_flags, dict):
            raise ValueError("qa report computed_flags must be an object")
        all_upstream_hard_gates_pass = all(
            hard_gate_statuses.get(gate_name) == "pass" for gate_name in required_upstream_production_hard_gates
        )
        upstream_production_eligible = bool(
            all_upstream_hard_gates_pass
            and proof_verification.get("runtime_proof_verified") is True
            and proof_verification.get("audio_review_verified") is True
            and proof_verification.get("artifact_bindings_verified") is True
            and computed_flags.get("all_hard_gates_passed") is True
            and computed_flags.get("production_eligible") is True
            and qa_report.get("promotion_decision") == "promote"
            and qa_report.get("is_synthetic") is False
            and qa_report.get("run_id") == run_id
        )
        return PASS, upstream_production_eligible
    except ValueError as exc:
        blockers.append(str(exc))
        return FAIL, False


def _ensure_registry_disjoint(registry: dict[str, Any]) -> None:
    required_registry_keys = {
        "parser_version",
        "wer_thresholds",
        "required_upstream_technical_gates",
        "required_upstream_production_hard_gates",
        "prompt_alignment_allowlist",
        "playback_review_allowlist",
        "production_review_authorities",
        "required_playback_sections",
        "required_playback_categories",
        "blocking_defect_codes",
        "blocking_defect_severities",
        "production_review_bundle_allowlist",
    }
    _expect_exact_object_keys(registry, required_registry_keys, "authority registry")
    if not isinstance(registry.get("parser_version"), str) or not registry["parser_version"].strip():
        raise ValueError("authority registry parser_version must be a non-empty string")

    prompt_records_raw = registry.get("prompt_alignment_allowlist")
    playback_records_raw = registry.get("playback_review_allowlist")
    production_records_raw = registry.get("production_review_authorities")
    if not isinstance(prompt_records_raw, list):
        raise ValueError("authority registry prompt_alignment_allowlist must be array")
    if not isinstance(playback_records_raw, list):
        raise ValueError("authority registry playback_review_allowlist must be array")
    if not isinstance(production_records_raw, list):
        raise ValueError("authority registry production_review_authorities must be array")

    prompt_records = [
        _normalize_identity_record(
            item,
            label=f"authority registry prompt_alignment_allowlist[{idx}]",
            expected_proof_kind="prompt_alignment",
        )
        for idx, item in enumerate(prompt_records_raw)
    ]
    playback_records = [
        _normalize_identity_record(
            item,
            label=f"authority registry playback_review_allowlist[{idx}]",
            expected_proof_kind="playback_review",
        )
        for idx, item in enumerate(playback_records_raw)
    ]
    production_records = [
        _normalize_identity_record(
            item,
            label=f"authority registry production_review_authorities[{idx}]",
            expected_proof_kind="production_review",
        )
        for idx, item in enumerate(production_records_raw)
    ]
    registry["prompt_alignment_allowlist"] = prompt_records
    registry["playback_review_allowlist"] = playback_records
    registry["production_review_authorities"] = production_records

    all_identities = prompt_records + playback_records + production_records
    identity_keys = [_identity_key(record) for record in all_identities]
    if len(identity_keys) != len(set(identity_keys)):
        raise ValueError("authority registry producer identities must be unique across roles")

    prompt_authorities = {record["authority_id"] for record in prompt_records}
    playback_authorities = {record["authority_id"] for record in playback_records}
    production_authorities = {record["authority_id"] for record in production_records}
    if (
        (prompt_authorities & playback_authorities)
        or (prompt_authorities & production_authorities)
        or (playback_authorities & production_authorities)
    ):
        raise ValueError("authority registry authority_id values must be disjoint across roles")


def _load_and_validate_inputs(input_path: Path) -> dict[str, Any]:
    request_payload = _load_json_strict(input_path)
    request_schema = _load_json_strict(REQUEST_SCHEMA_PATH)
    report_schema = _load_json_strict(REPORT_SCHEMA_PATH)
    registry = _load_json_strict(REGISTRY_PATH)
    w30_event_schema = _load_json_strict(W30_EVENT_SCHEMA_PATH)
    w30_mix_schema = _load_json_strict(W30_MIX_SCHEMA_PATH)
    w30_report_schema = _load_json_strict(W30_REPORT_SCHEMA_PATH)
    row030_sync_schema = _load_json_strict(ROW030_SYNC_SCHEMA_PATH)
    _validate_with_schema(request_payload, request_schema, "request")
    _ensure_registry_disjoint(registry)
    return {
        "request": request_payload,
        "report_schema": report_schema,
        "registry": registry,
        "w30_event_schema": w30_event_schema,
        "w30_mix_schema": w30_mix_schema,
        "w30_report_schema": w30_report_schema,
        "row030_sync_schema": row030_sync_schema,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    if not _is_under_root(input_path, PROJECT_ROOT):
        print(f"ERROR: input path escapes canonical project root: {input_path}")
        return 1
    if not _is_under_root(output_path, PROJECT_ROOT):
        print(f"ERROR: output path escapes canonical project root: {output_path}")
        return 1
    if output_path.exists():
        print(f"ERROR: output collision detected: {output_path}")
        return 1

    try:
        loaded = _load_and_validate_inputs(input_path)
        request_payload = loaded["request"]
        report_schema = loaded["report_schema"]
        registry = loaded["registry"]
        w30_event_schema = loaded["w30_event_schema"]
        w30_mix_schema = loaded["w30_mix_schema"]
        w30_report_schema = loaded["w30_report_schema"]
        row030_sync_schema = loaded["row030_sync_schema"]

        run_id = _expect_string(request_payload.get("run_id"), "request.run_id")
        is_synthetic = _expect_bool(request_payload.get("is_synthetic"), "request.is_synthetic")
        capture_mode = _expect_string(request_payload.get("capture_mode"), "request.capture_mode")

        binding_mix_wav = _resolve_binding(request_payload.get("mix_wav_binding"), "request.mix_wav_binding")
        binding_event = _resolve_binding(
            request_payload.get("wave30_event_manifest_binding"),
            "request.wave30_event_manifest_binding",
        )
        binding_mix_manifest = _resolve_binding(
            request_payload.get("wave30_mix_manifest_binding"),
            "request.wave30_mix_manifest_binding",
        )
        binding_qa_report = _resolve_binding(
            request_payload.get("wave30_qa_report_binding"),
            "request.wave30_qa_report_binding",
        )
        binding_prompt_reference = _resolve_binding(
            request_payload.get("prompt_reference_binding"),
            "request.prompt_reference_binding",
        )
        binding_prompt_alignment = _resolve_binding(
            request_payload.get("prompt_alignment_proof_binding"),
            "request.prompt_alignment_proof_binding",
        )
        binding_playback = None
        if request_payload.get("playback_proof_binding") is not None:
            binding_playback = _resolve_binding(
                request_payload.get("playback_proof_binding"),
                "request.playback_proof_binding",
            )
        binding_row030 = None
        if request_payload.get("row030_av_sync_report_binding") is not None:
            binding_row030 = _resolve_binding(
                request_payload.get("row030_av_sync_report_binding"),
                "request.row030_av_sync_report_binding",
            )
        binding_production_bundle = None
        if request_payload.get("production_review_bundle_binding") is not None:
            binding_production_bundle = _resolve_binding(
                request_payload.get("production_review_bundle_binding"),
                "request.production_review_bundle_binding",
            )

        event_manifest = _load_json_strict(Path(binding_event["path"]))
        mix_manifest = _load_json_strict(Path(binding_mix_manifest["path"]))
        qa_report = _load_json_strict(Path(binding_qa_report["path"]))
        prompt_reference = _load_json_strict(Path(binding_prompt_reference["path"]))
        prompt_alignment = _load_json_strict(Path(binding_prompt_alignment["path"]))

        blockers: list[str] = []
        gate_states = {name: FAIL for name in GATES}
        gate_states["audio_metadata_check"], upstream_production_eligible = _evaluate_audio_metadata(
            run_id=run_id,
            is_synthetic=is_synthetic,
            binding_mix_wav=binding_mix_wav,
            binding_event=binding_event,
            binding_mix_manifest=binding_mix_manifest,
            binding_qa_report=binding_qa_report,
            event_manifest=event_manifest,
            mix_manifest=mix_manifest,
            qa_report=qa_report,
            w30_event_schema=w30_event_schema,
            w30_mix_schema=w30_mix_schema,
            w30_report_schema=w30_report_schema,
            required_upstream_technical_gates=list(registry.get("required_upstream_technical_gates", [])),
            required_upstream_production_hard_gates=list(
                registry.get("required_upstream_production_hard_gates", UPSTREAM_PRODUCTION_REQUIRED_HARD_GATES)
            ),
            blockers=blockers,
        )

        prompt_status, prompt_metrics, prompt_producer = _evaluate_prompt_alignment(
            prompt_reference=prompt_reference,
            prompt_alignment=prompt_alignment,
            registry=registry,
            mix_wav_sha256=binding_mix_wav["sha256"],
            prompt_reference_sha256=binding_prompt_reference["sha256"],
            request_is_synthetic=is_synthetic,
            capture_mode=capture_mode,
            blockers=blockers,
        )
        gate_states["prompt_alignment"] = prompt_status

        playback_status, playback_producer, _ = _evaluate_playback_review(
            playback_binding=binding_playback,
            registry=registry,
            mix_wav_sha256=binding_mix_wav["sha256"],
            request_is_synthetic=is_synthetic,
            capture_mode=capture_mode,
            blockers=blockers,
        )
        gate_states["playback_review"] = playback_status

        sync_status, sync_not_applicable_reason = _evaluate_sync_evidence(
            prompt_reference=prompt_reference,
            row030_binding=binding_row030,
            mix_wav_binding=binding_mix_wav,
            run_id=run_id,
            is_synthetic=is_synthetic,
            capture_mode=capture_mode,
            row030_sync_schema=row030_sync_schema,
            blockers=blockers,
        )
        gate_states["sync_evidence"] = sync_status

        promotion_status, production_producer = _evaluate_promotion(
            request_payload=request_payload,
            upstream_production_eligible=upstream_production_eligible,
            gate_states=gate_states,
            prompt_producer=prompt_producer,
            playback_producer=playback_producer,
            production_bundle_binding=binding_production_bundle,
            registry=registry,
            blockers=blockers,
        )
        gate_states["promotion_decision"] = promotion_status

        if all(gate_states[name] == PASS for name in GATES if name != "overall_pass"):
            gate_states["overall_pass"] = PASS
        elif any(gate_states[name] == FAIL for name in GATES if name != "overall_pass"):
            gate_states["overall_pass"] = FAIL
        else:
            gate_states["overall_pass"] = BLOCKED

        final_exit_code = 0 if gate_states["overall_pass"] == PASS else 2

        artifact_bindings: dict[str, Any] = {
            "mix_wav": binding_mix_wav,
            "wave30_event_manifest": binding_event,
            "wave30_mix_manifest": binding_mix_manifest,
            "wave30_qa_report": binding_qa_report,
            "prompt_reference": binding_prompt_reference,
            "prompt_alignment_proof": binding_prompt_alignment,
        }
        if binding_playback is not None:
            artifact_bindings["playback_proof"] = binding_playback
        if binding_row030 is not None:
            artifact_bindings["row030_av_sync_report"] = binding_row030
        if binding_production_bundle is not None:
            artifact_bindings["production_review_bundle"] = binding_production_bundle

        report_payload = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_strict_audio_review_report",
            "report_version": 1,
            "run_id": run_id,
            "is_synthetic": is_synthetic,
            "capture_mode": capture_mode,
            "artifact_bindings": artifact_bindings,
            "gates": gate_states,
            "computed_metrics": {
                "normalized_wer": prompt_metrics["normalized_wer"],
                "wer_threshold": prompt_metrics["wer_threshold"],
                "expected_attribute_coverage": prompt_metrics["expected_attribute_coverage"],
                "upstream_production_eligible": upstream_production_eligible,
                "sync_not_applicable_reason": sync_not_applicable_reason,
            },
            "producer_identities": {
                "prompt_alignment_producer_id": prompt_producer,
                "playback_review_producer_id": playback_producer,
                "production_review_producer_id": production_producer,
            },
            "blockers": sorted(set(blockers)),
            "final_decision": {
                "overall_status": gate_states["overall_pass"],
                "exit_code": final_exit_code,
            },
        }
        _validate_with_schema(report_payload, report_schema, "wave64 strict audio report")
        _write_json_atomic(output_path, report_payload)
        print(str(output_path))
        return final_exit_code
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
