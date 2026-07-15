#!/usr/bin/env python3
"""Package the single-candidate CosyVoice2 instruct-control rejection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CANDIDATE_SHA256 = "87db819128b524c4ff3b14e80445785aed2b5aa43665ed65c0686dccae27fb39"
RUNTIME_MANIFEST_SHA256 = "53633fe03c0c8b3612ebee80d3ff9f64fbeaac106354e125ab71401f6eeafddc"
EVALUATION_SHA256 = "83da7315093baa0ac692ae8e07309ecd19ff6f1fe625f848aa1639b0dc74588d"
REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
REFERENCE_SOURCE_SHA256 = "9d8bc88e382c47b9493e3e881931692be893e69c602761072f9f80ae41ae7db0"
RUNNER_SHA256 = "e187e4032d2578a28810ecedb0b6b36b138a6ba9fe1af93ee0df73e71b37e961"
EVALUATOR_SHA256 = "d3db37c209023b56b090478b8eb5ee5bb432a9b0abc535795e76b44129229d19"
INSTRUCT_TEXT = (
    "You are a helpful assistant. Speak this sentence as quickly as possible with a "
    "focused, controlled delivery.<|endofprompt|>"
)
INSTRUCT_SHA256 = "64f3e22c534c9489d3174b5d99de9bae20dcb6ece246595014a863671a131e05"


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


def require_git_normalized_text_hash(path: Path, expected: str, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    actual = hashlib.sha256(normalized).hexdigest()
    if actual != expected:
        raise ValueError(
            f"{label} Git-normalized SHA256 mismatch: expected {expected}, got {actual}"
        )
    return {
        "path": str(path),
        "sha256": actual,
        "bytes": path.stat().st_size,
        "hash_basis": "git_normalized_lf",
    }


def load_bound_json(path: Path, expected: str, label: str) -> tuple[dict, dict]:
    bound = require_hash(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return bound, payload


def verify_runtime(payload: dict) -> None:
    runtime = payload.get("runtime", {})
    dialogue = payload.get("dialogue", {})
    boundaries = payload.get("boundaries", {})
    output = payload.get("output", {})
    gates = payload.get("gates", {})
    if payload.get("engine") != "CosyVoice2" or runtime.get("inference_mode") != "instruct2":
        raise ValueError("runtime is not the CosyVoice2 instruct2 path")
    if dialogue.get("instruct_text") != INSTRUCT_TEXT:
        raise ValueError("instruct text drift")
    if dialogue.get("instruct_text_sha256") != INSTRUCT_SHA256:
        raise ValueError("instruct text hash drift")
    if runtime.get("speed") != 1.2 or runtime.get("model_native_speed_control") is not True:
        raise ValueError("model-native speed control drift")
    if runtime.get("post_generation_truncation_applied") is not False:
        raise ValueError("post-generation truncation must remain false")
    if runtime.get("post_generation_time_stretch_applied") is not False:
        raise ValueError("post-generation time stretch must remain false")
    if boundaries.get("authorized_candidate_ordinal") != 1:
        raise ValueError("candidate ordinal drift")
    if boundaries.get("maximum_candidates_for_control_path") != 1:
        raise ValueError("one-candidate stop-rule drift")
    if output.get("sha256") != CANDIDATE_SHA256 or output.get("bytes") != 351404:
        raise ValueError("candidate binding drift")
    if output.get("pcm", {}).get("duration_seconds") != 7.32:
        raise ValueError("candidate duration drift")
    if gates.get("dialogue_timing_pass") is not False:
        raise ValueError("candidate timing must remain false")
    if gates.get("production_proof_authority_pass") is not False:
        raise ValueError("production authority must remain false")


def verify_evaluation(payload: dict) -> None:
    if payload.get("status") != "FAIL_COSYVOICE2_DIALOGUE_TIMING":
        raise ValueError("evaluation status drift")
    candidate = payload.get("candidate", {})
    expected = {
        "asr_transcript": "I'm not sure if I can get it.",
        "normalized_wer": 1.0,
        "speaker_similarity": 0.34052106738090515,
        "validated_speaker_threshold": 0.33445611596107483,
        "dnsmos_reference_percentile": 0.5,
        "inference_mode": "instruct2",
        "duration_seconds": 7.32,
        "expected_duration_seconds": 3.0,
    }
    if any(candidate.get(key) != value for key, value in expected.items()):
        raise ValueError("candidate metric drift")
    if candidate.get("dnsmos", {}).get("OVRL") != 2.8629396650581356:
        raise ValueError("candidate DNSMOS drift")
    if candidate.get("predicted_emotion", {}).get("predicted_label") != "happy":
        raise ValueError("candidate emotion drift")
    gates = payload.get("gates", {})
    if gates.get("candidate_asr_pass") is not False:
        raise ValueError("candidate ASR failure drift")
    if gates.get("candidate_reference_speaker_identity_pass") is not True:
        raise ValueError("candidate speaker score drift")
    if gates.get("candidate_dnsmos_worst_reference_floor_pass") is not True:
        raise ValueError("candidate DNSMOS floor drift")
    for key in (
        "dialogue_timing_pass",
        "target_emotion_taxonomy_supported",
        "independent_playback_review_pass",
        "production_proof_authority_pass",
        "row_complete",
        "final_voice_certification_pass",
    ):
        if gates.get(key) is not False:
            raise ValueError(f"fail-closed gate drift: {key}")


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
    reference_source = Path(args.reference_source).resolve()
    runtime_binding, runtime = load_bound_json(
        runtime_path, RUNTIME_MANIFEST_SHA256, "instruct-control runtime manifest"
    )
    evaluation_binding, evaluation = load_bound_json(
        evaluation_path, EVALUATION_SHA256, "instruct-control evaluation"
    )
    verify_runtime(runtime)
    verify_evaluation(evaluation)
    bindings = {
        "candidate": require_hash(candidate, CANDIDATE_SHA256, "instruct-control WAV"),
        "runtime_manifest": runtime_binding,
        "evaluation": evaluation_binding,
        "reference": require_hash(reference, REFERENCE_SHA256, "reference WAV"),
        "reference_source": require_hash(
            reference_source, REFERENCE_SOURCE_SHA256, "public-domain source"
        ),
        "runner": require_git_normalized_text_hash(
            Path(args.runner), RUNNER_SHA256, "instruct-control runner"
        ),
        "evaluator": require_git_normalized_text_hash(
            Path(args.evaluator), EVALUATOR_SHA256, "instruct-control evaluator"
        ),
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
    gates = evaluation["gates"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_cosyvoice2_instruct_control_rejection_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "FAIL_COSYVOICE2_INSTRUCT_CONTROL_CONTENT_TIMING_STYLE",
        "classification": "COSYVOICE2_INSTRUCT_CONTROL_REJECTED_NO_RETRY",
        "artifact_bindings": bindings,
        "durable_artifacts": durable,
        "control_contract": {
            "inference_mode": "instruct2",
            "instruct_text": INSTRUCT_TEXT,
            "instruct_text_sha256": INSTRUCT_SHA256,
            "model_native_speed": 1.2,
            "post_generation_truncation_applied": False,
            "post_generation_time_stretch_applied": False,
            "authorized_candidate_count": 1,
        },
        "runtime": runtime["runtime"],
        "candidate": evaluation["candidate"],
        "acceptance": {
            "model_native_instruct_control_executed": True,
            "candidate_exact_content_pass": gates["candidate_asr_pass"],
            "candidate_reference_speaker_score_pass": gates[
                "candidate_reference_speaker_identity_pass"
            ],
            "candidate_dnsmos_worst_reference_floor_pass": gates[
                "candidate_dnsmos_worst_reference_floor_pass"
            ],
            "candidate_dnsmos_quality_certification_pass": None,
            "candidate_dialogue_timing_pass": False,
            "candidate_style_contract_pass": False,
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
            "same_instruct_control_retry_authorized": False,
            "reason": (
                "The single model-native instruct2 take changed the required dialogue to unrelated "
                "speech at WER 1.0 and expanded duration to 7.32 seconds against the 3.0-second contract."
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
        raise ValueError("instruct-control evidence mirrors diverged")
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
