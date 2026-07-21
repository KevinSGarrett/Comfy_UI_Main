#!/usr/bin/env python3
"""Produce immutable deterministic W64-AQA-006 evidence for a retained audio artifact."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
COMPILER_PATH = SCRIPT_DIR / "compile_wave64_runpod_autonomous_multimodal_job_contract.py"
MEASURER_PATH = SCRIPT_DIR / "measure_wave64_runpod_autonomous_audio_quality.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_audio_shadow_evidence.schema.json"
ZERO_HASH = "0" * 64


class EvidenceError(ValueError):
    """Raised when source lineage or evidence invariants fail."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = _load_module("w64_aqa_contract_compiler_for_audio_shadow", COMPILER_PATH)
MEASURER = _load_module("w64_aqa_audio_measurer_for_shadow", MEASURER_PATH)


def canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON root must be an object: {path}")
    return value


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("generated_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("generated_at must include a timezone")


def _ffmpeg_runtime_digest() -> str:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], check=True, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError("ffmpeg runtime is unavailable") from exc
    first_line = result.stdout.splitlines()[0]
    return f"ffmpeg-version-sha256:{hashlib.sha256(first_line.encode('utf-8')).hexdigest()}"


def _resolve_manifest_asset(manifest_path: Path, declared_path: str) -> Path:
    candidate = Path(declared_path)
    if candidate.is_file():
        return candidate
    fallback = manifest_path.parent / candidate.name
    if fallback.is_file():
        return fallback
    raise EvidenceError(f"manifest diagnostic asset is absent: {candidate.name}")


def build_evidence(
    *,
    artifact_path: Path,
    manifest_path: Path,
    role_registry_path: Path,
    generated_at: str,
    artifact_relative_path: str,
    manifest_relative_path: str,
    observations: list[str],
) -> dict[str, Any]:
    _validate_timestamp(generated_at)
    if not observations or any(not item.strip() for item in observations):
        raise EvidenceError("at least one bounded diagnostic observation is required")
    if not artifact_path.is_file() or not manifest_path.is_file() or not role_registry_path.is_file():
        raise EvidenceError("artifact, manifest, and role registry must exist")

    manifest = _json(manifest_path)
    registry = _json(role_registry_path)
    try:
        declared = manifest["outputs"]["final_mix"]
        waveform = manifest["outputs"]["waveform"]
        spectrogram = manifest["outputs"]["spectrogram"]
        audio_spec = manifest["pcm_technical"]["final_mix"]
        loudness = manifest["loudness_measurement"]
    except (KeyError, TypeError) as exc:
        raise EvidenceError("manifest lacks required canonical audio fields") from exc

    artifact_sha = sha256_file(artifact_path)
    if declared.get("sha256") != artifact_sha:
        raise EvidenceError("artifact hash does not match delivery manifest")
    waveform_path = _resolve_manifest_asset(manifest_path, waveform["path"])
    spectrogram_path = _resolve_manifest_asset(manifest_path, spectrogram["path"])
    if sha256_file(waveform_path) != waveform.get("sha256"):
        raise EvidenceError("waveform hash does not match delivery manifest")
    if sha256_file(spectrogram_path) != spectrogram.get("sha256"):
        raise EvidenceError("spectrogram hash does not match delivery manifest")

    roles = {item.get("role_id"): item for item in registry.get("roles", [])}
    deterministic = roles.get("W64-AQA-ROLE-DETERMINISTIC")
    semantic = roles.get("W64-AQA-ROLE-AUDIO-SEMANTIC")
    if not deterministic or deterministic.get("state") != "ACTIVE_REQUIRED":
        raise EvidenceError("deterministic measurement role is not active")
    if not semantic or not isinstance(semantic.get("state"), str):
        raise EvidenceError("semantic audio role is absent from the role registry")

    manifest_sha = sha256_file(manifest_path)
    contract_draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-row006-canonical-audio-shadow-v1",
        "revision": 1,
        "created_at": generated_at,
        "modality": "audio",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{
            "output_id": "retained-final-mix",
            "media_type": "audio/wav",
            "durable_relative_path": artifact_relative_path,
        }],
        "quality_profile": {
            "profile_id": "w64-aqa-row006-canonical-audio-technical-v1",
            "hard_gates": [
                {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
                {"gate_id": "clipping", "metric": "clipped_sample_fraction", "operator": "lte", "threshold": 0.0, "on_failure": "REPAIR"},
                {"gate_id": "dc-offset", "metric": "max_abs_dc_offset", "operator": "lte", "threshold": 0.01, "on_failure": "REPAIR"},
                {"gate_id": "silence", "metric": "silence_frame_fraction", "operator": "lt", "threshold": 0.9, "on_failure": "REPAIR"},
                {"gate_id": "true-peak", "metric": "true_peak_dbfs", "operator": "lte", "threshold": -1.0, "on_failure": "REPAIR"},
                {"gate_id": "stereo-phase", "metric": "stereo_phase_correlation", "operator": "gte", "threshold": -0.9, "on_failure": "REPAIR"},
                {"gate_id": "duplicate-segments", "metric": "duplicate_segment_fraction", "operator": "lte", "threshold": 0.95, "on_failure": "HOLD"}
            ],
            "review_roles": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "authority": "deterministic", "can_approve": True, "required": True},
                {"role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC", "authority": "audio_semantic", "can_approve": False, "required": False}
            ],
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC"]
        },
        "resource_budget": {
            "max_gpu_seconds": 1,
            "max_gpu_hour_usd": 0.01,
            "max_output_bytes": int(declared["bytes"]),
            "deadline_seconds": 120,
            "secondary_burst": {"enabled": False, "max_cost_usd": 0, "max_seconds": 0, "idle_ttl_seconds": 0, "eligible_gpu_classes": []}
        },
        "attempt_policy": {"max_repairs_per_defect": 0, "max_total_generations": 1, "max_no_progress_cycles": 0},
        "authority_policy": {
            "generation_host": "runpod_only", "ec2_allowed": False, "local_comfyui_allowed": False,
            "triage_can_approve": False, "model_can_promote": False,
            "workflow_model_proposal_only": True, "secrets_visible_to_models": False,
            "external_inference_allowed": False
        },
        "rollback_policy": {"revert_on_regression": True, "promotion_requires_replay": True, "retain_failed_evidence": True, "previous_accepted_artifact_sha256": None},
        "provenance": {
            "workflow_sha256": manifest_sha,
            "input_artifacts": [
                {"artifact_id": "delivery-manifest", "sha256": manifest_sha, "durable_relative_path": manifest_relative_path},
                {"artifact_id": "retained-final-mix", "sha256": artifact_sha, "durable_relative_path": artifact_relative_path}
            ],
            "model_bindings": [{
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "model_id": "deterministic-tool/measure_wave64_runpod_autonomous_audio_quality.py",
                "checkpoint_sha256": sha256_file(MEASURER_PATH),
                "runtime_digest": _ffmpeg_runtime_digest(),
                "qualification_state": "QUALIFIED"
            }],
            "calibration_ids": [f"W64-AQA-CAL-row006-{manifest_sha[:16]}"]
        },
        "audio_spec": {
            "sample_rate_hz": int(audio_spec["sample_rate_hz"]),
            "channels": int(audio_spec["channels"]),
            "duration_seconds": float(audio_spec["duration_seconds"]),
            "lufs_target": float(loudness["target_integrated_lufs"])
        }
    }
    contract = COMPILER.compile_contract(contract_draft)
    measurement = MEASURER.measure_audio(artifact_path, contract)
    semantic_blocked = semantic["state"] == "BLOCKED_UNQUALIFIED"
    if measurement["disposition"] == "FAIL_DETERMINISTIC_GATES":
        overall = "FAIL_DETERMINISTIC_SHADOW"
    elif semantic_blocked:
        overall = "PASS_DETERMINISTIC_SHADOW_BLOCKED_SEMANTIC_AUDIO_AUTHORITY"
    else:
        overall = "PASS_DETERMINISTIC_SHADOW_SEMANTIC_REVIEW_REQUIRED"

    evidence = {
        "schema_version": "wave64.aqa.audio_shadow_evidence.v1",
        "evidence_id": ZERO_HASH,
        "generated_at": generated_at,
        "row_id": "W64-AQA-006",
        "source": {
            "artifact_relative_path": artifact_relative_path,
            "artifact_sha256": artifact_sha,
            "manifest_relative_path": manifest_relative_path,
            "manifest_sha256": manifest_sha,
            "manifest_declared_artifact_sha256": declared["sha256"],
            "hash_match": True
        },
        "technical_contract": contract,
        "measurement": measurement,
        "diagnostic_review": {
            "scope": "rendered_waveform_and_spectrogram_only",
            "waveform_sha256": waveform["sha256"],
            "spectrogram_sha256": spectrogram["sha256"],
            "observations": observations,
            "semantic_audio_review_claimed": False
        },
        "semantic_release_gate": {
            "required_for_product_release": True,
            "role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC",
            "role_registry_sha256": sha256_file(role_registry_path),
            "registry_state": semantic["state"],
            "runtime_executed": False,
            "independent_perceptual_playback_present": False,
            "disposition": "BLOCKED_UNQUALIFIED" if semantic_blocked else "SEMANTIC_REVIEW_REQUIRED",
            "missing_authority": [
                "qualified semantic audio runtime",
                "independent perceptual playback review",
                "ASR and event-alignment evidence",
                "independent product juror approval"
            ]
        },
        "product_promotion_eligible": False,
        "overall_disposition": overall
    }
    identity_input = copy.deepcopy(evidence)
    identity_input["evidence_id"] = ZERO_HASH
    evidence["evidence_id"] = hashlib.sha256(canonical_bytes(identity_input)).hexdigest()
    schema = _json(SCHEMA_PATH)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("role_registry", type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--artifact-relative-path", required=True)
    parser.add_argument("--manifest-relative-path", required=True)
    parser.add_argument("--diagnostic-observation", action="append", dest="observations", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence = build_evidence(
            artifact_path=args.artifact,
            manifest_path=args.manifest,
            role_registry_path=args.role_registry,
            generated_at=args.generated_at,
            artifact_relative_path=args.artifact_relative_path,
            manifest_relative_path=args.manifest_relative_path,
            observations=args.observations,
        )
        rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise EvidenceError("output already exists; evidence is immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, EvidenceError, COMPILER.ContractError, MEASURER.MeasurementError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
