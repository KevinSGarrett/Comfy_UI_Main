#!/usr/bin/env python3
"""Produce immutable deterministic W64-AQA-006 evidence for a retained AV mux."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "produce_wave64_runpod_autonomous_audio_shadow_evidence.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_av_shadow_evidence.schema.json"
ZERO_HASH = "0" * 64


class EvidenceError(ValueError):
    """Raised when AV source lineage or evidence invariants fail."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_module("w64_aqa_audio_shadow_base_for_av", BASE_PATH)
COMPILER = BASE.COMPILER
MEASURER = BASE.MEASURER


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("generated_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("generated_at must include a timezone")


def _decoded_frame_sha256(mux_path: Path, timestamp_seconds: float) -> str:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-ss",
                f"{timestamp_seconds:.6f}", "-i", str(mux_path), "-frames:v", "1",
                "-f", "image2pipe", "-vcodec", "png", "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError("bounded decoded-frame extraction failed") from exc
    if not result.stdout:
        raise EvidenceError("bounded decoded-frame extraction returned no bytes")
    return hashlib.sha256(result.stdout).hexdigest()


def build_evidence(
    *,
    mux_path: Path,
    source_video_path: Path,
    manifest_path: Path,
    role_registry_path: Path,
    generated_at: str,
    mux_relative_path: str,
    source_video_relative_path: str,
    manifest_relative_path: str,
    frame_timestamp_seconds: float,
    frame_observations: list[str],
) -> dict[str, Any]:
    _validate_timestamp(generated_at)
    if not frame_observations or any(not item.strip() for item in frame_observations):
        raise EvidenceError("at least one bounded decoded-frame observation is required")
    for path in (mux_path, source_video_path, manifest_path, role_registry_path):
        if not path.is_file():
            raise EvidenceError(f"required input is absent: {path}")
    manifest = BASE._json(manifest_path)
    registry = BASE._json(role_registry_path)
    try:
        mux_declared = manifest["outputs"]["review_mux"]
        video_declared = manifest["outputs"]["strict_source_video"]
        audio_declared = manifest["pcm_technical"]["final_mix"]
        loudness = manifest["loudness_measurement"]
        declared_fps = float(manifest["sync"]["video_frame_rate"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceError("manifest lacks required canonical AV fields") from exc

    mux_sha = BASE.sha256_file(mux_path)
    video_sha = BASE.sha256_file(source_video_path)
    if mux_declared.get("sha256") != mux_sha or video_declared.get("sha256") != video_sha:
        raise EvidenceError("AV artifact hash does not match delivery manifest")
    probe = MEASURER._probe(mux_path)
    video_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "video"]
    if len(video_streams) != 1:
        raise EvidenceError("AV mux must contain exactly one video stream")
    video_stream = video_streams[0]
    fps = float(Fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")))
    if abs(fps - declared_fps) > 1e-9:
        raise EvidenceError("AV mux frame rate does not match delivery manifest")

    roles = {item.get("role_id"): item for item in registry.get("roles", [])}
    role_states = {}
    for role_id in (
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-STRICT-VISUAL",
        "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
    ):
        role = roles.get(role_id)
        if not role or not isinstance(role.get("state"), str):
            raise EvidenceError(f"required role is absent from registry: {role_id}")
        role_states[role_id] = role["state"]
    if role_states["W64-AQA-ROLE-DETERMINISTIC"] != "ACTIVE_REQUIRED":
        raise EvidenceError("deterministic measurement role is not active")

    duration = float(probe.get("format", {}).get("duration"))
    manifest_sha = BASE.sha256_file(manifest_path)
    contract_draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-row006-canonical-av-shadow-v1",
        "revision": 1,
        "created_at": generated_at,
        "modality": "av",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{"output_id": "retained-review-mux", "media_type": "video/x-matroska", "durable_relative_path": mux_relative_path}],
        "quality_profile": {
            "profile_id": "w64-aqa-row006-canonical-av-technical-v1",
            "hard_gates": [
                {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
                {"gate_id": "clipping", "metric": "clipped_sample_fraction", "operator": "lte", "threshold": 0.0, "on_failure": "REPAIR"},
                {"gate_id": "dc-offset", "metric": "max_abs_dc_offset", "operator": "lte", "threshold": 0.01, "on_failure": "REPAIR"},
                {"gate_id": "silence", "metric": "silence_frame_fraction", "operator": "lt", "threshold": 0.9, "on_failure": "REPAIR"},
                {"gate_id": "true-peak", "metric": "true_peak_dbfs", "operator": "lte", "threshold": -1.0, "on_failure": "REPAIR"},
                {"gate_id": "stereo-phase", "metric": "stereo_phase_correlation", "operator": "gte", "threshold": -0.9, "on_failure": "REPAIR"},
                {"gate_id": "av-duration-alignment", "metric": "av_stream_duration_delta_ms", "operator": "lte", "threshold": 50.0, "on_failure": "HOLD"}
            ],
            "review_roles": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "authority": "deterministic", "can_approve": True, "required": True},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "authority": "strict", "can_approve": False, "required": False},
                {"role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC", "authority": "audio_semantic", "can_approve": False, "required": False}
            ],
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC"]
        },
        "resource_budget": {
            "max_gpu_seconds": 1, "max_gpu_hour_usd": 0.01,
            "max_output_bytes": int(mux_declared["bytes"]), "deadline_seconds": 120,
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
                {"artifact_id": "source-video", "sha256": video_sha, "durable_relative_path": source_video_relative_path},
                {"artifact_id": "review-mux", "sha256": mux_sha, "durable_relative_path": mux_relative_path}
            ],
            "model_bindings": [{
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "model_id": "deterministic-tool/measure_wave64_runpod_autonomous_audio_quality.py",
                "checkpoint_sha256": BASE.sha256_file(BASE.MEASURER_PATH),
                "runtime_digest": BASE._ffmpeg_runtime_digest(),
                "qualification_state": "QUALIFIED"
            }],
            "calibration_ids": [f"W64-AQA-CAL-row006-av-{manifest_sha[:16]}"]
        },
        "video_spec": {"width": int(video_stream["width"]), "height": int(video_stream["height"]), "fps": fps, "duration_seconds": duration, "sample_policy": "all_frames"},
        "audio_spec": {"sample_rate_hz": int(audio_declared["sample_rate_hz"]), "channels": int(audio_declared["channels"]), "duration_seconds": duration, "lufs_target": float(loudness["target_integrated_lufs"])},
        "av_spec": {"max_sync_error_ms": 50.0, "alignment_required": True}
    }
    contract = COMPILER.compile_contract(contract_draft)
    measurement = MEASURER.measure_audio(mux_path, contract)
    decoded_frame_sha = _decoded_frame_sha256(mux_path, frame_timestamp_seconds)
    deterministic_pass = measurement["disposition"] == "PASS_DETERMINISTIC_GATES"
    evidence = {
        "schema_version": "wave64.aqa.av_shadow_evidence.v1",
        "evidence_id": ZERO_HASH,
        "generated_at": generated_at,
        "row_id": "W64-AQA-006",
        "source": {
            "mux_relative_path": mux_relative_path, "mux_sha256": mux_sha,
            "source_video_relative_path": source_video_relative_path,
            "source_video_sha256": video_sha,
            "manifest_relative_path": manifest_relative_path,
            "manifest_sha256": manifest_sha, "manifest_hashes_match": True
        },
        "technical_contract": contract,
        "measurement": measurement,
        "decoded_frame_review": {
            "timestamp_seconds": frame_timestamp_seconds,
            "frame_sha256": decoded_frame_sha,
            "observations": frame_observations,
            "single_frame_only": True,
            "motion_review_claimed": False,
            "av_sync_review_claimed": False,
            "product_visual_approval_claimed": False
        },
        "release_gates": {
            "strict_visual": {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "registry_state": role_states["W64-AQA-ROLE-STRICT-VISUAL"], "runtime_executed": False, "disposition": "RUNTIME_NOT_EXECUTED"},
            "audio_semantic": {"role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC", "registry_state": role_states["W64-AQA-ROLE-AUDIO-SEMANTIC"], "runtime_executed": False, "disposition": "BLOCKED_UNQUALIFIED"},
            "independent_juror": {"role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR", "registry_state": role_states["W64-AQA-ROLE-INDEPENDENT-JUROR"], "runtime_executed": False, "disposition": "BLOCKED_UNQUALIFIED"}
        },
        "product_promotion_eligible": False,
        "overall_disposition": "PASS_DETERMINISTIC_AV_SHADOW_BLOCKED_SEMANTIC_AUTHORITIES" if deterministic_pass else "FAIL_DETERMINISTIC_AV_SHADOW"
    }
    identity_input = copy.deepcopy(evidence)
    identity_input["evidence_id"] = ZERO_HASH
    evidence["evidence_id"] = hashlib.sha256(BASE.canonical_bytes(identity_input)).hexdigest()
    schema = BASE._json(SCHEMA_PATH)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mux", type=Path)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("role_registry", type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--mux-relative-path", required=True)
    parser.add_argument("--source-video-relative-path", required=True)
    parser.add_argument("--manifest-relative-path", required=True)
    parser.add_argument("--frame-timestamp-seconds", type=float, required=True)
    parser.add_argument("--frame-observation", action="append", dest="frame_observations", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence = build_evidence(
            mux_path=args.mux, source_video_path=args.source_video,
            manifest_path=args.manifest, role_registry_path=args.role_registry,
            generated_at=args.generated_at, mux_relative_path=args.mux_relative_path,
            source_video_relative_path=args.source_video_relative_path,
            manifest_relative_path=args.manifest_relative_path,
            frame_timestamp_seconds=args.frame_timestamp_seconds,
            frame_observations=args.frame_observations,
        )
        rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise EvidenceError("output already exists; evidence is immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, EvidenceError, BASE.EvidenceError, COMPILER.ContractError, MEASURER.MeasurementError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
