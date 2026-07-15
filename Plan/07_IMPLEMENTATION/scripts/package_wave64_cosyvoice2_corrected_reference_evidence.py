#!/usr/bin/env python3
"""Package the corrected-reference CosyVoice2 timing rejection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CANDIDATE_SHA256 = "845b8971bd9ca8e3898e632cd02ad14f0eb0c1d2d6b1ec3cdd2e537fb94295ba"
RUNTIME_MANIFEST_SHA256 = "c9f5aab38c53ba6f11fb62425dea4e52f4663808d072f5451b46c6f7905bafe5"
EVALUATION_SHA256 = "5c9a5d8377e7b6e34f6391b1bc110502a5530eaa5c7fe64ac902bbaf0cded0b3"
REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
REFERENCE_SOURCE_SHA256 = "9d8bc88e382c47b9493e3e881931692be893e69c602761072f9f80ae41ae7db0"
RUNNER_SHA256 = "9ea4d3a7851013e5353be17bff9c97cee3f455389c0f3770a4f71cdaa5357850"
EVALUATOR_SHA256 = "9f3a4c286be24729abecdf9dc99c50cb6968d3975820ec65f86ca88720ae3006"
REFERENCE_TRANSCRIPT = "Once upon a midnight dreary, while I pondered, weak and weary."


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
    bound = require_hash(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return bound, payload


def verify_runtime(payload: dict) -> None:
    if payload.get("engine") != "CosyVoice2":
        raise ValueError("runtime engine drift")
    reference = payload.get("reference_speaker", {})
    if reference.get("sha256") != REFERENCE_SHA256:
        raise ValueError("corrected reference binding drift")
    if reference.get("expected_transcript") != REFERENCE_TRANSCRIPT:
        raise ValueError("corrected reference transcript drift")
    if reference.get("pcm", {}).get("duration_seconds") != 5.0:
        raise ValueError("corrected reference duration drift")
    output = payload.get("output", {})
    if output.get("sha256") != CANDIDATE_SHA256 or output.get("bytes") != 232364:
        raise ValueError("corrected candidate binding drift")
    if output.get("pcm", {}).get("duration_seconds") != 4.84:
        raise ValueError("corrected candidate duration drift")
    gates = payload.get("gates", {})
    if gates.get("dialogue_timing_pass") is not False:
        raise ValueError("corrected candidate timing must remain false")
    if gates.get("production_proof_authority_pass") is not False:
        raise ValueError("corrected candidate production authority must remain false")


def verify_evaluation(payload: dict) -> None:
    if payload.get("status") != "FAIL_COSYVOICE2_DIALOGUE_TIMING":
        raise ValueError("corrected candidate evaluation status drift")
    candidate = payload.get("candidate", {})
    expected = {
        "normalized_wer": 0.0,
        "speaker_similarity": 0.6607623100280762,
        "validated_speaker_threshold": 0.33445611596107483,
        "dnsmos_reference_percentile": 0.75,
        "duration_seconds": 4.84,
        "expected_duration_seconds": 3.0,
    }
    if any(candidate.get(key) != value for key, value in expected.items()):
        raise ValueError("corrected candidate metric drift")
    if candidate.get("dnsmos", {}).get("OVRL") != 3.174097435695213:
        raise ValueError("corrected candidate DNSMOS drift")
    gates = payload.get("gates", {})
    required_true = (
        "candidate_asr_pass",
        "candidate_reference_speaker_identity_pass",
        "candidate_dnsmos_worst_reference_floor_pass",
    )
    if any(gates.get(key) is not True for key in required_true):
        raise ValueError("corrected candidate narrow pass gate drift")
    required_false = (
        "dialogue_timing_pass",
        "target_emotion_taxonomy_supported",
        "independent_playback_review_pass",
        "production_proof_authority_pass",
        "row_complete",
        "final_voice_certification_pass",
    )
    if any(gates.get(key) is not False for key in required_false):
        raise ValueError("corrected candidate fail-closed gate drift")
    if gates.get("candidate_dnsmos_quality_certification_pass") is not None:
        raise ValueError("DNSMOS floor cannot certify candidate quality")
    if gates.get("target_intensity_taxonomy_supported") is not None:
        raise ValueError("intensity taxonomy must remain unmeasured")


def copy_exact(source: Path, destination: Path, expected: str, label: str) -> dict:
    require_hash(source, expected, label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or sha256(destination) != expected:
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    return require_hash(destination, expected, f"durable {label}")


def package(args: argparse.Namespace) -> dict:
    candidate = Path(args.candidate).resolve()
    runtime_path = Path(args.runtime_manifest).resolve()
    evaluation_path = Path(args.evaluation).resolve()
    reference = Path(args.reference).resolve()
    source = Path(args.reference_source).resolve()
    runtime_binding, runtime = load_bound_json(
        runtime_path, RUNTIME_MANIFEST_SHA256, "corrected runtime manifest"
    )
    evaluation_binding, evaluation = load_bound_json(
        evaluation_path, EVALUATION_SHA256, "corrected candidate evaluation"
    )
    verify_runtime(runtime)
    verify_evaluation(evaluation)
    bindings = {
        "candidate": require_hash(candidate, CANDIDATE_SHA256, "corrected candidate WAV"),
        "runtime_manifest": runtime_binding,
        "evaluation": evaluation_binding,
        "reference": require_hash(reference, REFERENCE_SHA256, "corrected reference WAV"),
        "reference_source": require_hash(
            source, REFERENCE_SOURCE_SHA256, "public-domain reference source"
        ),
        "runner": require_hash(Path(args.runner), RUNNER_SHA256, "corrected runner"),
        "evaluator": require_hash(Path(args.evaluator), EVALUATOR_SHA256, "corrected evaluator"),
    }
    artifact_dir = Path(args.artifact_dir).resolve()
    durable = {
        "candidate": copy_exact(candidate, artifact_dir / candidate.name, CANDIDATE_SHA256, "candidate"),
        "runtime_manifest": copy_exact(
            runtime_path, artifact_dir / runtime_path.name, RUNTIME_MANIFEST_SHA256, "runtime manifest"
        ),
        "evaluation": copy_exact(
            evaluation_path, artifact_dir / evaluation_path.name, EVALUATION_SHA256, "evaluation"
        ),
        "reference": copy_exact(
            reference, artifact_dir / reference.name, REFERENCE_SHA256, "reference"
        ),
    }
    candidate_metrics = evaluation["candidate"]
    gates = evaluation["gates"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_cosyvoice2_corrected_reference_candidate_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "FAIL_COSYVOICE2_CORRECTED_REFERENCE_CANDIDATE_TIMING",
        "classification": "COSYVOICE2_CONTENT_SPEAKER_METRICS_PASS_TIMING_AND_STYLE_BLOCKED",
        "artifact_bindings": bindings,
        "durable_artifacts": durable,
        "reference_derivation": {
            "source_start_seconds": 20.4,
            "source_end_seconds": 25.4,
            "duration_seconds": 5.0,
            "transcript": REFERENCE_TRANSCRIPT,
            "license": runtime["reference_speaker"]["license"],
            "source_page": runtime["reference_speaker"]["source_page"],
        },
        "runtime": runtime["runtime"],
        "candidate": candidate_metrics,
        "acceptance": {
            "pytorch_model_stack_cuda_executed": True,
            "onnx_frontend_cuda_executed": False,
            "candidate_exact_content_pass": gates["candidate_asr_pass"],
            "candidate_reference_speaker_score_pass": gates[
                "candidate_reference_speaker_identity_pass"
            ],
            "candidate_dnsmos_worst_reference_floor_pass": gates[
                "candidate_dnsmos_worst_reference_floor_pass"
            ],
            "candidate_dnsmos_quality_certification_pass": None,
            "candidate_dialogue_timing_pass": False,
            "candidate_emotion_pass": None,
            "candidate_intensity_pass": None,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "decision": {
            "candidate_preserved": True,
            "candidate_rejected": True,
            "candidate_truncated": False,
            "candidate_time_stretched": False,
            "additional_generation_authorized": False,
            "reason": (
                "The corrected reference eliminates the repetitive collapse and produces exact content, "
                "but the 4.84-second take exceeds the immutable 3.0-second dialogue contract."
            ),
        },
        "remaining_blockers": evaluation["remaining_blockers"],
        "affected_rows": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "boundaries": evaluation["boundaries"],
        "row_complete": False,
    }


def write_exact(payload: dict, paths: list[Path]) -> str:
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    digest = hashlib.sha256(encoded).hexdigest()
    if any(sha256(path) != digest for path in paths):
        raise ValueError("corrected-reference evidence mirrors diverged")
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "candidate",
        "runtime-manifest",
        "evaluation",
        "reference",
        "reference-source",
        "runner",
        "evaluator",
        "artifact-dir",
        "qa-output",
        "tracker-output",
    ):
        parser.add_argument(f"--{name}", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(args)
    digest = write_exact(
        payload, [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()]
    )
    print(json.dumps({"classification": payload["classification"], "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
