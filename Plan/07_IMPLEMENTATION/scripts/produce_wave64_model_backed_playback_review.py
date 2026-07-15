#!/usr/bin/env python3
"""Produce fail-closed Wave64 playback evidence from calibrated local models."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = ["beginning", "middle", "end", "loud", "quiet", "transitions"]
REQUIRED_CATEGORIES = {
    "intelligibility",
    "cleanliness",
    "stylistic_fit",
    "technical_consistency",
    "content_correctness",
}
IDENTITY_KEYS = {
    "proof_kind",
    "producer_id",
    "engine",
    "model",
    "model_version",
    "model_sha256",
    "authority_id",
    "synthetic_only",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_bundle_sha256(components: dict[str, Any]) -> str:
    lines = []
    for key in sorted(components):
        record = components[key]
        if not isinstance(record, dict) or not re.fullmatch(r"[0-9a-fA-F]{64}", str(record.get("sha256", ""))):
            raise ValueError(f"model component {key} has invalid SHA256")
        lines.append(f"{key}={str(record['sha256']).lower()}")
    if not lines:
        raise ValueError("model component registry is empty")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def resolve_path(value: str, project_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def require_binding(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError(f"{label} SHA256 mismatch: expected {expected_sha256}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def require_declared_binding(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"{label} binding is missing")
    path = Path(str(record.get("path", ""))).resolve()
    expected_sha256 = str(record.get("sha256", ""))
    expected_bytes = record.get("bytes")
    if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool) or expected_bytes <= 0:
        raise ValueError(f"{label} binding bytes are invalid")
    verified = require_binding(path, expected_sha256, label)
    if verified["bytes"] != expected_bytes:
        raise ValueError(f"{label} byte count mismatch")
    return verified


def load_json_binding(path: Path, expected_sha256: str | None, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if expected_sha256 is not None and actual.lower() != expected_sha256.lower():
        raise ValueError(f"{label} SHA256 mismatch: expected {expected_sha256}, got {actual}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}, payload


def normalized_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def levenshtein(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, 1):
        next_row = [left_index]
        for right_index, right_value in enumerate(right, 1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    row[right_index] + 1,
                    row[right_index - 1] + (left_value != right_value),
                )
            )
        row = next_row
    return row[-1]


def normalized_wer(expected: str, observed: str) -> float:
    expected_tokens = normalized_tokens(expected)
    if not expected_tokens:
        raise ValueError("expected transcript normalizes to empty")
    return levenshtein(expected_tokens, normalized_tokens(observed)) / len(expected_tokens)


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def read_audio_metrics(path: Path) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError("candidate audio is empty or contains nonfinite samples")
    mono = audio.mean(axis=1)
    absolute = np.abs(audio)
    duration = len(mono) / float(sample_rate)
    if duration <= 0.0:
        raise ValueError("candidate audio duration is invalid")

    block_size = max(1, int(sample_rate * 0.1))
    block_rms = []
    for start in range(0, len(mono), block_size):
        block = mono[start : start + block_size]
        block_rms.append(float(np.sqrt(np.mean(np.square(block), dtype=np.float64))))
    transition_jumps = [
        abs(_db(right) - _db(left))
        for left, right in zip(block_rms, block_rms[1:])
        if left >= 1e-3 and right >= 1e-3
    ]

    third = max(1, len(mono) // 3)
    named_ranges = {
        "beginning": mono[:third],
        "middle": mono[third : min(len(mono), third * 2)],
        "end": mono[min(len(mono), third * 2) :],
    }
    section_rms = {
        name: float(np.sqrt(np.mean(np.square(values), dtype=np.float64))) if len(values) else 0.0
        for name, values in named_ranges.items()
    }
    section_rms["loud"] = max(block_rms)
    section_rms["quiet"] = min(block_rms)
    section_rms["transitions"] = max(transition_jumps, default=0.0)

    return {
        "sample_rate": int(sample_rate),
        "channels": int(audio.shape[1]),
        "frames": int(audio.shape[0]),
        "duration_seconds": duration,
        "peak_absolute": float(absolute.max()),
        "clipped_sample_ratio": float(np.mean(absolute >= 0.999)),
        "silence_sample_ratio": float(np.mean(np.abs(mono) <= 1e-4)),
        "rms": float(np.sqrt(np.mean(np.square(mono), dtype=np.float64))),
        "max_transition_jump_db": max(transition_jumps, default=0.0),
        "section_metrics": section_rms,
    }


def score_intelligibility(wer: float) -> float:
    if wer == 0.0:
        return 5.0
    if wer <= 0.05:
        return 4.5
    if wer <= 0.10:
        return 4.0
    if wer <= 0.20:
        return 3.0
    if wer <= 0.25:
        return 2.0
    return 0.0


def score_cleanliness(ovrl: float, thresholds: dict[str, Any]) -> float:
    minimum = float(thresholds["dnsmos_ovrl_reference_min"])
    maximum = float(thresholds["dnsmos_ovrl_reference_max"])
    if maximum <= minimum:
        raise ValueError("DNSMOS reference range is invalid")
    return round(max(0.0, min(5.0, (ovrl - minimum) / (maximum - minimum) * 5.0)), 6)


def build_decision(
    *,
    expected_text: str,
    observed_text: str,
    dnsmos: dict[str, Any],
    emotion: dict[str, Any],
    audio_metrics: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    thresholds = registry["thresholds"]
    wer = normalized_wer(expected_text, observed_text)
    expected_tokens = normalized_tokens(expected_text)
    observed_tokens = normalized_tokens(observed_text)
    defects: list[dict[str, str]] = []

    if expected_tokens != observed_tokens:
        defects.append(
            {
                "code": "CRITICAL_CONTENT_MISMATCH",
                "severity": "critical",
                "description": f"Expected normalized tokens {expected_tokens}; observed {observed_tokens}.",
            }
        )
    if float(audio_metrics["clipped_sample_ratio"]) >= float(thresholds["clipped_sample_ratio_block_min"]):
        defects.append(
            {
                "code": "MAJOR_CLIPPING",
                "severity": "high",
                "description": "Clipped-sample ratio exceeds the calibrated playback threshold.",
            }
        )
    if float(audio_metrics["silence_sample_ratio"]) >= float(thresholds["silence_ratio_block_min"]):
        defects.append(
            {
                "code": "SEVERE_GLITCH",
                "severity": "high",
                "description": "Silence ratio exceeds the calibrated playback threshold.",
            }
        )
    target_emotion = str(emotion.get("target_emotion", "")).strip().lower()
    target_intensity = str(emotion.get("target_intensity", "")).strip().lower()
    calibrated_emotions = {str(value).lower() for value in registry["calibrated_emotion_labels"]}
    calibrated_intensities = {str(value).lower() for value in registry["calibrated_intensity_labels"]}
    unsupported = []
    if not target_emotion or target_emotion not in calibrated_emotions:
        unsupported.append("stylistic_fit.target_emotion")
    if target_intensity and target_intensity not in calibrated_intensities:
        unsupported.append("stylistic_fit.target_intensity")

    category_scores: dict[str, float | None] = {
        "intelligibility": score_intelligibility(wer),
        "cleanliness": score_cleanliness(float(dnsmos["OVRL"]), thresholds),
        "stylistic_fit": None,
        "technical_consistency": 0.0 if any(d["code"] != "CRITICAL_CONTENT_MISMATCH" for d in defects) else 5.0,
        "content_correctness": 5.0 if expected_tokens == observed_tokens else 0.0,
    }
    if not unsupported:
        predicted = str(emotion.get("predicted_label", "")).strip().lower()
        confidence = float(emotion.get("predicted_score"))
        category_scores["stylistic_fit"] = round(5.0 * confidence, 6) if predicted == target_emotion else 0.0
        if predicted != target_emotion:
            defects.append(
                {
                    "code": "STYLE_MISMATCH",
                    "severity": "medium",
                    "description": f"Expected calibrated emotion {target_emotion}; observed {predicted}.",
                }
            )

    return {
        "normalized_wer": wer,
        "expected_tokens": expected_tokens,
        "observed_tokens": observed_tokens,
        "category_scores": category_scores,
        "defects": defects,
        "unsupported_required_categories": unsupported,
        "proof_eligible": not unsupported,
    }


def _runtime_identity() -> dict[str, Any]:
    packages = ("numpy", "soundfile")
    return {
        "python": platform.python_version(),
        "packages": {name: metadata.version(name) for name in packages},
    }


def _preflight_output(path: Path, project_root: Path, overwrite: bool) -> None:
    try:
        path.resolve().relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"output path must stay inside project root: {path}") from exc
    if path.exists() and not overwrite:
        raise ValueError(f"output exists and overwrite is disabled: {path}")


def atomic_write_json(path: Path, payload: dict[str, Any], overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise ValueError(f"output exists and overwrite is disabled: {path}")
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def build(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any] | None]:
    project_root = Path(args.project_root).resolve()
    registry_path = resolve_path(args.producer_registry, project_root)
    registry_binding, registry = load_json_binding(registry_path, None, "playback producer registry")
    if registry.get("schema_name") != "wave64_model_backed_playback_producer_registry":
        raise ValueError("playback producer registry schema mismatch")

    identity = registry.get("producer_identity")
    if not isinstance(identity, dict) or set(identity) != IDENTITY_KEYS:
        raise ValueError("producer identity keys mismatch")
    components = registry.get("model_components")
    if not isinstance(components, dict):
        raise ValueError("model component registry is invalid")
    component_bindings = {
        key: require_binding(resolve_path(record["path"], project_root), record["sha256"], f"model component {key}")
        for key, record in components.items()
    }
    calculated_model_hash = model_bundle_sha256(components)
    if calculated_model_hash != str(identity.get("model_sha256", "")).lower():
        raise ValueError("producer model bundle SHA256 mismatch")

    supporting = registry.get("supporting_bindings")
    if not isinstance(supporting, dict):
        raise ValueError("supporting binding registry is invalid")
    supporting_bindings = {
        key: require_binding(resolve_path(record["path"], project_root), record["sha256"], f"supporting binding {key}")
        for key, record in supporting.items()
    }

    calibration = registry.get("calibration_evidence")
    if not isinstance(calibration, dict):
        raise ValueError("calibration evidence registry is invalid")
    cv3_binding, cv3 = load_json_binding(
        resolve_path(calibration["cv3_eval"]["path"], project_root),
        calibration["cv3_eval"]["sha256"],
        "CV3 evaluator evidence",
    )
    emotion_binding, emotion_evidence = load_json_binding(
        resolve_path(calibration["cv3_emotion"]["path"], project_root),
        calibration["cv3_emotion"]["sha256"],
        "CV3 emotion evidence",
    )

    candidate = Path(args.candidate_audio).resolve()
    candidate_binding = require_binding(candidate, args.expected_candidate_sha256, "candidate audio")
    cv3_candidate = cv3.get("candidate")
    emotion_candidate = emotion_evidence.get("candidate")
    if not isinstance(cv3_candidate, dict) or not isinstance(emotion_candidate, dict):
        raise ValueError("calibration evidence candidate records are missing")
    emotion_lineage = emotion_candidate.get("lineage")
    if not isinstance(emotion_lineage, dict) or not isinstance(emotion_lineage.get("candidate"), dict):
        raise ValueError("emotion candidate lineage is missing")
    for label, record in (("CV3", cv3_candidate), ("emotion", emotion_lineage["candidate"])):
        if Path(str(record.get("path", ""))).resolve() != candidate:
            raise ValueError(f"{label} evidence candidate path mismatch")
        if str(record.get("sha256", "")).lower() != candidate_binding["sha256"]:
            raise ValueError(f"{label} evidence candidate SHA256 mismatch")

    cv3_lineage = cv3_candidate.get("lineage")
    if not isinstance(cv3_lineage, dict):
        raise ValueError("CV3 candidate lineage is missing")
    original_lineage_bindings = {}
    for key, label in (("packet_manifest", "original packet manifest"), ("dialogue_contract", "original dialogue contract")):
        verified = require_declared_binding(cv3_lineage.get(key), label)
        emotion_record = emotion_lineage.get(key)
        if not isinstance(emotion_record, dict):
            raise ValueError(f"emotion evidence {label} binding is missing")
        if (
            Path(str(emotion_record.get("path", ""))).resolve() != Path(verified["path"])
            or str(emotion_record.get("sha256", "")).lower() != verified["sha256"]
            or emotion_record.get("bytes") != verified["bytes"]
        ):
            raise ValueError(f"CV3 and emotion evidence disagree on {label} binding")
        original_lineage_bindings[key] = verified

    authority_path = resolve_path(registry["authority_registry_path"], project_root)
    authority_binding, authority = load_json_binding(authority_path, None, "strict audio authority registry")
    allowlist = authority.get("playback_review_allowlist", [])
    if allowlist.count(identity) != 1:
        raise ValueError("producer identity must appear exactly once in playback allowlist")
    production_authorities = authority.get("production_review_authorities", [])
    if any(isinstance(record, dict) and record.get("authority_id") == identity["authority_id"] for record in production_authorities):
        raise ValueError("playback producer must not appear in production review authorities")

    audio_metrics = read_audio_metrics(candidate)
    expected_text = str(cv3_candidate.get("expected_text", ""))
    observed_text = str(cv3_candidate.get("asr_transcript", ""))
    recorded_wer = float(cv3_candidate.get("normalized_wer"))
    if not math.isclose(recorded_wer, normalized_wer(expected_text, observed_text), abs_tol=1e-12):
        raise ValueError("CV3 candidate WER is inconsistent with bound transcripts")
    dnsmos = cv3_candidate.get("dnsmos")
    if not isinstance(dnsmos, dict):
        raise ValueError("CV3 candidate DNSMOS record is missing")
    emotion_input = {
        "target_emotion": emotion_lineage.get("target_emotion"),
        "target_intensity": emotion_lineage.get("target_intensity"),
        "predicted_label": emotion_candidate.get("predicted_label"),
        "predicted_score": emotion_candidate.get("predicted_score"),
    }
    decision = build_decision(
        expected_text=expected_text,
        observed_text=observed_text,
        dnsmos=dnsmos,
        emotion=emotion_input,
        audio_metrics=audio_metrics,
        registry=registry,
    )

    proof = None
    if decision["proof_eligible"]:
        scores = decision["category_scores"]
        if set(scores) != REQUIRED_CATEGORIES or any(value is None for value in scores.values()):
            raise ValueError("eligible playback proof does not contain all numeric category scores")
        proof = {
            "schema_name": "wave64_playback_review_proof",
            **identity,
            "audio_sha256": candidate_binding["sha256"],
            "is_synthetic": False,
            "production_evidence": True,
            "self_authorized": False,
            "sections_reviewed": REQUIRED_SECTIONS,
            "category_scores": scores,
            "defects": decision["defects"],
        }

    blocking = any(defect["severity"] in {"critical", "high"} for defect in decision["defects"])
    if not decision["proof_eligible"]:
        status = "BLOCKED"
        classification = "MODEL_BACKED_PLAYBACK_REVIEW_ABSTAINED_UNSUPPORTED_REQUIRED_CATEGORY"
    elif blocking:
        status = "BLOCKED"
        classification = "MODEL_BACKED_PLAYBACK_REVIEW_PROOF_WITH_BLOCKING_DEFECT"
    else:
        status = "PASS"
        classification = "MODEL_BACKED_PLAYBACK_REVIEW_PROOF_PASS"

    evidence = {
        "schema_version": "1.0",
        "artifact_type": "wave64_model_backed_playback_execution_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": status,
        "classification": classification,
        "producer_identity": identity,
        "runtime_identity": _runtime_identity(),
        "bindings": {
            "producer_registry": registry_binding,
            "strict_authority_registry": authority_binding,
            "model_components": component_bindings,
            "supporting_files": supporting_bindings,
            "cv3_eval_evidence": cv3_binding,
            "cv3_emotion_evidence": emotion_binding,
            "candidate_audio": candidate_binding,
            "original_lineage_files": original_lineage_bindings,
        },
        "observations": {
            "expected_text": expected_text,
            "observed_text": observed_text,
            "dnsmos": dnsmos,
            "emotion": emotion_input,
            "audio_metrics": audio_metrics,
        },
        "decision": decision,
        "proof_emitted": proof is not None,
        "authority_boundary": {
            "playback_review_only": True,
            "production_review_authority": False,
            "production_review_bundle_authority": False,
            "row_complete": False,
            "certification_pass": False,
        },
    }
    return evidence, proof


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument(
        "--producer-registry",
        default="Plan/10_REGISTRIES/wave64_model_backed_playback_producer_registry.json",
    )
    parser.add_argument("--candidate-audio", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--output-evidence", required=True)
    parser.add_argument("--output-proof", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    evidence_path = resolve_path(args.output_evidence, project_root)
    proof_path = resolve_path(args.output_proof, project_root)
    _preflight_output(evidence_path, project_root, args.overwrite)
    _preflight_output(proof_path, project_root, args.overwrite)
    evidence, proof = build(args)
    if proof is not None:
        atomic_write_json(proof_path, proof, args.overwrite)
        evidence["playback_proof_binding"] = {
            "path": str(proof_path),
            "sha256": sha256(proof_path),
            "bytes": proof_path.stat().st_size,
        }
    else:
        proof_path.unlink(missing_ok=True)
        evidence["playback_proof_binding"] = None
    atomic_write_json(evidence_path, evidence, args.overwrite)
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "classification": evidence["classification"],
                "evidence_path": str(evidence_path),
                "evidence_sha256": sha256(evidence_path),
                "proof_emitted": proof is not None,
                "proof_path": str(proof_path) if proof is not None else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
