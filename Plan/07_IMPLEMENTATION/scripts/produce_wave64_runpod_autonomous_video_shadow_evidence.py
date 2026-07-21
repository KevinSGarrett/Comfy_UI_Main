#!/usr/bin/env python3
"""Produce immutable deterministic W64-AQA-005 evidence for a retained video."""

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
VIDEO_MEASURER_PATH = SCRIPT_DIR / "measure_wave64_runpod_autonomous_video_quality.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_video_shadow_evidence.schema.json"
ZERO_HASH = "0" * 64
CONTACT_SHEET_INDICES = [0, 12, 24, 36, 48]


class EvidenceError(ValueError):
    """Raised when video lineage or evidence invariants fail."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_module("w64_aqa_audio_shadow_base_for_video", BASE_PATH)
COMPILER = BASE.COMPILER
MEASURER = _load_module("w64_aqa_video_measurer_for_shadow", VIDEO_MEASURER_PATH)


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("generated_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("generated_at must include a timezone")


def _contact_sheet_sha256(video_path: Path) -> str:
    selection = "+".join(f"eq(n\\,{index})" for index in CONTACT_SHEET_INDICES)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-i", str(video_path),
                "-vf", f"select='{selection}',scale=240:320:flags=lanczos,tile=5x1",
                "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceError("bounded contact-sheet extraction failed") from exc
    if not result.stdout:
        raise EvidenceError("bounded contact-sheet extraction returned no bytes")
    return hashlib.sha256(result.stdout).hexdigest()


def build_evidence(
    *,
    video_path: Path,
    delivery_manifest_path: Path,
    original_technical_qa_path: Path,
    av_shadow_evidence_path: Path,
    strict_hold_path: Path,
    generated_at: str,
    video_relative_path: str,
    delivery_manifest_relative_path: str,
    original_technical_qa_relative_path: str,
    av_shadow_evidence_relative_path: str,
    observations: list[str],
) -> dict[str, Any]:
    _validate_timestamp(generated_at)
    if not observations or any(not item.strip() for item in observations):
        raise EvidenceError("at least one bounded contact-sheet observation is required")
    for path in (
        video_path, delivery_manifest_path, original_technical_qa_path,
        av_shadow_evidence_path, strict_hold_path,
    ):
        if not path.is_file():
            raise EvidenceError(f"required input is absent: {path}")
    manifest = BASE._json(delivery_manifest_path)
    original_qa = BASE._json(original_technical_qa_path)
    av_shadow = BASE._json(av_shadow_evidence_path)
    strict_hold = BASE._json(strict_hold_path)
    video_sha = BASE.sha256_file(video_path)
    try:
        declared_video = manifest["outputs"]["strict_source_video"]
        original_source_sha = manifest["source_bindings"]["source_video"]["sha256"]
    except (KeyError, TypeError) as exc:
        raise EvidenceError("delivery manifest lacks canonical video lineage") from exc
    if declared_video.get("sha256") != video_sha:
        raise EvidenceError("video hash does not match delivery manifest")
    if original_qa.get("artifact", {}).get("sha256") != original_source_sha:
        raise EvidenceError("original technical QA does not match source lineage")
    if original_qa.get("technical_pass") is not True:
        raise EvidenceError("original source technical QA did not pass")
    if av_shadow.get("source", {}).get("source_video_sha256") != video_sha:
        raise EvidenceError("paired AV shadow does not match retained video")
    if av_shadow.get("product_promotion_eligible") is not False:
        raise EvidenceError("paired AV shadow must remain evidence-only")
    if strict_hold.get("inference_executed") is not False or strict_hold.get("lease_acquired") is not False:
        raise EvidenceError("strict admission evidence must not claim runtime execution")
    if "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT" not in strict_hold.get("blocker_codes", []):
        raise EvidenceError("strict admission evidence lacks the foreign-workload blocker")
    installed = {
        item.get("name"): item.get("digest")
        for item in strict_hold.get("resource_snapshot", {}).get("installed_models", [])
    }
    strict_digest = installed.get("qwen2.5vl:32b")
    if not isinstance(strict_digest, str) or len(strict_digest) != 64:
        raise EvidenceError("strict model digest is absent from admission evidence")

    probe = MEASURER._probe(video_path)
    streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "video"]
    if len(streams) != 1:
        raise EvidenceError("retained video must contain exactly one video stream")
    stream = streams[0]
    frame_count = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    if frame_count != 49:
        raise EvidenceError("canonical contact-sheet policy requires exactly 49 frames")
    fps = float(Fraction(stream["avg_frame_rate"]))
    duration = float(stream.get("duration") or probe.get("format", {}).get("duration"))
    hold_sha = BASE.sha256_file(strict_hold_path)
    contract_draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-row005-retained-ffv1-video-shadow-v1",
        "revision": 1,
        "created_at": generated_at,
        "modality": "video",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{"output_id": "retained-ffv1-video", "media_type": "video/x-matroska", "durable_relative_path": video_relative_path}],
        "quality_profile": {
            "profile_id": "w64-aqa-row005-real-ffv1-video-v1",
            "hard_gates": [
                {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
                {"gate_id": "no-audio-stream", "metric": "audio_stream_present", "operator": "eq", "threshold": False, "on_failure": "REJECT"},
                {"gate_id": "sample-duplicates", "metric": "duplicate_sample_fraction", "operator": "lt", "threshold": 0.95, "on_failure": "HOLD"},
                {"gate_id": "sample-motion", "metric": "sampled_motion_mean", "operator": "gt", "threshold": 0.0, "on_failure": "HOLD"},
                {"gate_id": "sample-exposure-jump", "metric": "sampled_luminance_jump_max", "operator": "lte", "threshold": 30.0, "on_failure": "REPAIR"},
                {"gate_id": "sample-sharpness", "metric": "sampled_sharpness_min", "operator": "gt", "threshold": 10.0, "on_failure": "REPAIR"}
            ],
            "review_roles": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "authority": "deterministic", "can_approve": True, "required": True},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "authority": "strict", "can_approve": True, "required": True}
            ],
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-STRICT-VISUAL"]
        },
        "resource_budget": {
            "max_gpu_seconds": 120, "max_gpu_hour_usd": 0.77,
            "max_output_bytes": int(declared_video["bytes"]), "deadline_seconds": 300,
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
            "workflow_sha256": BASE.sha256_file(delivery_manifest_path),
            "input_artifacts": [
                {"artifact_id": "retained-ffv1-video", "sha256": video_sha, "durable_relative_path": video_relative_path},
                {"artifact_id": "original-technical-qa", "sha256": BASE.sha256_file(original_technical_qa_path), "durable_relative_path": original_technical_qa_relative_path},
                {"artifact_id": "paired-av-shadow", "sha256": BASE.sha256_file(av_shadow_evidence_path), "durable_relative_path": av_shadow_evidence_relative_path}
            ],
            "model_bindings": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "model_id": "deterministic-tool/measure_wave64_runpod_autonomous_video_quality.py", "checkpoint_sha256": BASE.sha256_file(VIDEO_MEASURER_PATH), "runtime_digest": BASE._ffmpeg_runtime_digest(), "qualification_state": "QUALIFIED"},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "model_id": "ollama/qwen2.5vl:32b", "checkpoint_sha256": strict_digest, "runtime_digest": f"admission-evidence-sha256:{hold_sha}", "qualification_state": "QUALIFIED"}
            ],
            "calibration_ids": ["W64-AQA-CAL-row005-subtle-motion-video-v1"]
        },
        "video_spec": {"width": int(stream["width"]), "height": int(stream["height"]), "fps": fps, "duration_seconds": duration, "sample_policy": "uniform_plus_change_points"}
    }
    contract = COMPILER.compile_contract(contract_draft)
    measurement = MEASURER.measure_video(video_path, contract)
    deterministic_pass = measurement["disposition"] == "PASS_DETERMINISTIC_GATES"
    evidence = {
        "schema_version": "wave64.aqa.video_shadow_evidence.v1",
        "evidence_id": ZERO_HASH,
        "generated_at": generated_at,
        "row_id": "W64-AQA-005",
        "source": {
            "video_relative_path": video_relative_path, "video_sha256": video_sha,
            "delivery_manifest_relative_path": delivery_manifest_relative_path,
            "delivery_manifest_sha256": BASE.sha256_file(delivery_manifest_path),
            "original_source_sha256": original_source_sha,
            "original_technical_qa_relative_path": original_technical_qa_relative_path,
            "original_technical_qa_sha256": BASE.sha256_file(original_technical_qa_path),
            "av_shadow_evidence_relative_path": av_shadow_evidence_relative_path,
            "av_shadow_evidence_sha256": BASE.sha256_file(av_shadow_evidence_path),
            "all_hashes_match": True
        },
        "technical_contract": contract,
        "measurement": measurement,
        "contact_sheet_review": {
            "frame_indices": CONTACT_SHEET_INDICES,
            "contact_sheet_sha256": _contact_sheet_sha256(video_path),
            "observations": observations,
            "diagnostic_only": True,
            "motion_review_claimed": False,
            "temporal_identity_claimed": False,
            "whole_clip_review_claimed": False,
            "product_visual_approval_claimed": False
        },
        "strict_model_gate": {
            "role_id": "W64-AQA-ROLE-STRICT-VISUAL", "model": "qwen2.5vl:32b",
            "checkpoint_digest": strict_digest, "admission_evidence_sha256": hold_sha,
            "runtime_executed": False, "disposition": "HELD_ACTIVE_FOREIGN_GPU_WORKLOAD",
            "blocker_code": "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT"
        },
        "product_promotion_eligible": False,
        "overall_disposition": "PASS_DETERMINISTIC_VIDEO_GATES_DIAGNOSTIC_CONTACT_SHEET_ONLY_STRICT_RUNTIME_HELD" if deterministic_pass else "FAIL_DETERMINISTIC_VIDEO_GATES"
    }
    identity_input = copy.deepcopy(evidence)
    identity_input["evidence_id"] = ZERO_HASH
    evidence["evidence_id"] = hashlib.sha256(BASE.canonical_bytes(identity_input)).hexdigest()
    schema = BASE._json(SCHEMA_PATH)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("delivery_manifest", type=Path)
    parser.add_argument("original_technical_qa", type=Path)
    parser.add_argument("av_shadow_evidence", type=Path)
    parser.add_argument("strict_hold", type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--video-relative-path", required=True)
    parser.add_argument("--delivery-manifest-relative-path", required=True)
    parser.add_argument("--original-technical-qa-relative-path", required=True)
    parser.add_argument("--av-shadow-evidence-relative-path", required=True)
    parser.add_argument("--contact-sheet-observation", action="append", dest="observations", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence = build_evidence(
            video_path=args.video, delivery_manifest_path=args.delivery_manifest,
            original_technical_qa_path=args.original_technical_qa,
            av_shadow_evidence_path=args.av_shadow_evidence,
            strict_hold_path=args.strict_hold, generated_at=args.generated_at,
            video_relative_path=args.video_relative_path,
            delivery_manifest_relative_path=args.delivery_manifest_relative_path,
            original_technical_qa_relative_path=args.original_technical_qa_relative_path,
            av_shadow_evidence_relative_path=args.av_shadow_evidence_relative_path,
            observations=args.observations,
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
