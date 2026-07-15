#!/usr/bin/env python3
"""Package the rejected CosyVoice2 candidate into durable Wave64 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CANDIDATE_SHA256 = "13dbaefb9080fe0a6a8d6445f3daf568b6cb2a59df7e324cb3a99427d377ff47"
RUNTIME_MANIFEST_SHA256 = "865d8237f3e894a71d74a5af8ea23a01d2e86bb5a5614b198db01cd53ba3e2b2"
EVALUATION_SHA256 = "29e52721a349b6ff0730e80906ba0fcea72c32704a915dec811e3dd02603ca7a"
RUNNER_SHA256 = "8f0d35e055089ceb72d5802be59bc50cfe1a7d32c7946b60e8cc5d8678e8be5a"
EVALUATOR_SHA256 = "9a05db0a7ced13019d063c32efc219a77b964ebba9e31767584aa40a7dcc543e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def load_bound_json(path: Path, expected: str, label: str) -> tuple[dict, dict]:
    binding = require_hash(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def verify_runtime(payload: dict) -> None:
    if payload.get("engine") != "CosyVoice2":
        raise ValueError("runtime engine drift")
    if payload.get("model", {}).get("model_id") != "FunAudioLLM/CosyVoice2-0.5B":
        raise ValueError("CosyVoice2 model identity drift")
    output = payload.get("output", {})
    if output.get("sha256") != CANDIDATE_SHA256 or output.get("bytes") != 422444:
        raise ValueError("candidate output binding drift")
    if output.get("pcm", {}).get("duration_seconds") != 8.8:
        raise ValueError("candidate duration drift")
    gates = payload.get("gates", {})
    required_true = (
        "model_payload_hash_binding_pass",
        "source_code_identity_pass",
        "independent_reference_speaker_bound",
        "technical_audio_pass",
    )
    if any(gates.get(key) is not True for key in required_true):
        raise ValueError("runtime provenance or technical-audio gate drift")
    if gates.get("dialogue_timing_pass") is not False:
        raise ValueError("rejected candidate timing gate must remain false")
    if gates.get("production_proof_authority_pass") is not False:
        raise ValueError("production authority must remain false")
    boundaries = payload.get("boundaries", {})
    if boundaries.get("final_voice_certification_claimed") is not False:
        raise ValueError("runtime must not claim final voice certification")


def verify_evaluation(payload: dict) -> None:
    if payload.get("status") != "FAIL_COSYVOICE2_DIALOGUE_TIMING":
        raise ValueError("CosyVoice2 evaluation status drift")
    candidate = payload.get("candidate", {})
    expected = {
        "normalized_wer": 4.8,
        "speaker_similarity": 0.3992827236652374,
        "validated_speaker_threshold": 0.33445611596107483,
        "duration_seconds": 8.8,
        "expected_duration_seconds": 3.0,
        "target_emotion": "focused",
        "target_intensity": "controlled",
    }
    if any(candidate.get(key) != value for key, value in expected.items()):
        raise ValueError("CosyVoice2 candidate metric drift")
    gates = payload.get("gates", {})
    required_false = (
        "candidate_asr_pass",
        "dialogue_timing_pass",
        "target_emotion_taxonomy_supported",
        "independent_playback_review_pass",
        "production_proof_authority_pass",
        "row_complete",
        "final_voice_certification_pass",
    )
    if any(gates.get(key) is not False for key in required_false):
        raise ValueError("rejected candidate fail-closed gate drift")
    if gates.get("target_intensity_taxonomy_supported") is not None:
        raise ValueError("candidate intensity taxonomy must remain explicitly unmeasured")
    if gates.get("target_intensity_taxonomy_status") != (
        "unmeasured_no_calibrated_intensity_evaluator"
    ):
        raise ValueError("candidate intensity measurement status drift")
    if gates.get("candidate_reference_speaker_identity_pass") is not True:
        raise ValueError("candidate reference-speaker score drift")
    if gates.get("candidate_dnsmos_worst_reference_floor_pass") is not True:
        raise ValueError("candidate DNSMOS worst-reference floor result drift")
    if gates.get("candidate_dnsmos_quality_certification_pass") is not None:
        raise ValueError("candidate DNSMOS quality certification must remain unmeasured")
    bindings = payload.get("bindings", {})
    expected_bindings = {
        "candidate": CANDIDATE_SHA256,
        "candidate_manifest": RUNTIME_MANIFEST_SHA256,
    }
    for key, expected_hash in expected_bindings.items():
        if bindings.get(key, {}).get("sha256") != expected_hash:
            raise ValueError(f"evaluation {key} binding drift")


def copy_exact(source: Path, destination: Path, expected: str, label: str) -> dict:
    require_hash(source, expected, label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or sha256(destination) != expected:
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    return require_hash(destination, expected, f"durable {label}")


def package(
    candidate: Path,
    runtime_manifest: Path,
    evaluation: Path,
    runner: Path,
    evaluator: Path,
    artifact_dir: Path,
) -> dict:
    runtime_binding, runtime = load_bound_json(
        runtime_manifest, RUNTIME_MANIFEST_SHA256, "CosyVoice2 runtime manifest"
    )
    evaluation_binding, evaluation_payload = load_bound_json(
        evaluation, EVALUATION_SHA256, "CosyVoice2 candidate evaluation"
    )
    verify_runtime(runtime)
    verify_evaluation(evaluation_payload)
    candidate_binding = require_hash(candidate, CANDIDATE_SHA256, "CosyVoice2 candidate WAV")
    runner_binding = require_hash(runner, RUNNER_SHA256, "CosyVoice2 runner")
    evaluator_binding = require_hash(evaluator, EVALUATOR_SHA256, "CosyVoice2 evaluator")
    durable = {
        "candidate_wav": copy_exact(
            candidate, artifact_dir / candidate.name, CANDIDATE_SHA256, "candidate WAV"
        ),
        "runtime_manifest": copy_exact(
            runtime_manifest,
            artifact_dir / runtime_manifest.name,
            RUNTIME_MANIFEST_SHA256,
            "runtime manifest",
        ),
        "candidate_evaluation": copy_exact(
            evaluation,
            artifact_dir / evaluation.name,
            EVALUATION_SHA256,
            "candidate evaluation",
        ),
    }
    candidate_result = evaluation_payload["candidate"]
    gates = evaluation_payload["gates"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_cosyvoice2_zero_shot_candidate_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "FAIL_COSYVOICE2_CANDIDATE_REJECTED",
        "classification": (
            "COSYVOICE2_REFERENCE_BOUND_CANDIDATE_REJECTED_"
            "TIMING_INTELLIGIBILITY_AND_STYLE"
        ),
        "artifact_bindings": {
            "runtime_candidate": candidate_binding,
            "runtime_manifest": runtime_binding,
            "runtime_evaluation": evaluation_binding,
            "durable_artifacts": durable,
        },
        "implementation_bindings": {
            "runner": runner_binding,
            "evaluator": evaluator_binding,
        },
        "source_authority": {
            "engine": runtime["engine_source"],
            "model_id": runtime["model"]["model_id"],
            "model_license": runtime["model"]["license"],
            "model_local_files_only": runtime["model"]["local_files_only"],
            "reference_speaker": runtime["reference_speaker"],
        },
        "runtime": runtime["runtime"],
        "candidate": candidate_result,
        "acceptance": {
            "pytorch_model_stack_cuda_executed": True,
            "onnx_frontend_cuda_executed": False,
            "onnx_frontend_execution_providers": runtime["runtime"][
                "onnx_available_providers"
            ],
            "model_and_source_hash_binding_pass": True,
            "independent_reference_speaker_bound": True,
            "candidate_reference_speaker_score_pass": gates[
                "candidate_reference_speaker_identity_pass"
            ],
            "candidate_dnsmos_worst_reference_floor_pass": gates[
                "candidate_dnsmos_worst_reference_floor_pass"
            ],
            "candidate_dnsmos_quality_certification_pass": None,
            "candidate_intelligibility_pass": gates["candidate_asr_pass"],
            "candidate_dialogue_timing_pass": gates["dialogue_timing_pass"],
            "candidate_style_contract_pass": False,
            "candidate_intensity_taxonomy_status": gates[
                "target_intensity_taxonomy_status"
            ],
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "decision": {
            "candidate_preserved": True,
            "candidate_rejected": True,
            "candidate_regeneration_count": 0,
            "candidate_media_mutated": False,
            "promotion_claimed": False,
            "reason": (
                "The reference-bound score and DNSMOS floor pass, but the 8.8-second output "
                "exceeds the 3.0-second contract and Whisper detects repetitive non-dialogue "
                "content at WER 4.8. Focused emotion is unsupported and controlled intensity "
                "is unmeasured. The DNSMOS result clears only the worst-reference floor and "
                "is not a quality certification."
            ),
        },
        "remaining_blockers": evaluation_payload["remaining_blockers"],
        "affected_rows": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "boundaries": evaluation_payload["boundaries"],
        "row_complete": False,
    }


def write_exact(payload: dict, paths: list[Path]) -> str:
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    evidence_sha256 = hashlib.sha256(encoded).hexdigest()
    if any(sha256(path) != evidence_sha256 for path in paths):
        raise ValueError("QA and Tracker CosyVoice2 evidence mirrors diverged")
    return evidence_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--runtime-manifest", required=True)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--qa-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(
        Path(args.candidate).resolve(),
        Path(args.runtime_manifest).resolve(),
        Path(args.evaluation).resolve(),
        Path(args.runner).resolve(),
        Path(args.evaluator).resolve(),
        Path(args.artifact_dir).resolve(),
    )
    evidence_sha256 = write_exact(
        payload,
        [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()],
    )
    print(json.dumps({"classification": payload["classification"], "sha256": evidence_sha256}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
