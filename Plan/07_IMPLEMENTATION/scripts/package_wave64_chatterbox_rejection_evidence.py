#!/usr/bin/env python3
"""Package the immutable single-candidate Chatterbox dialogue rejection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CANDIDATE_SHA256 = "cde61c59adace5b0674ee05268f56a091b0921b196bc7ad54ad0a06fc17a5b96"
RUNTIME_MANIFEST_SHA256 = "f391619ec532bf3ebbe9f0c2ef6e4d89b632621ffc50bdccdaac1c0640446e20"
EVALUATION_SHA256 = "7834e2c5e682122f837d6050eece725cab180cd91fa41030f70f13c31436a281"
REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
RUNNER_SHA256 = "0653b7c570fe37e39fce600769164d4b714cc46e1905ff8e284203cb034aa5a1"
EVALUATOR_SHA256 = "27c1319f67eff7424282259d12881e6c6a732f720fcb927e35d92429096b145f"
CONTROL_CONTRACT_SHA256 = "fdb59d03446f8b2f78cf19cd771e4d8b6f5236b763ed6a2ed78936cc7208e644"
EXPECTED_TEXT = "We hold the frame steady and move on the beat."


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
    binding = require_hash(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def verify_runtime(payload: dict) -> None:
    if payload.get("engine") != "ChatterboxTTS":
        raise ValueError("runtime engine drift")
    implementation = payload.get("implementation", {})
    contract = implementation.get("control_contract", {})
    runtime = payload.get("runtime", {})
    output = payload.get("output", {})
    gates = payload.get("gates", {})
    boundaries = payload.get("boundaries", {})
    expected_contract = {
        "text": EXPECTED_TEXT,
        "expected_duration_seconds": 3.0,
        "max_duration_delta_seconds": 0.35,
        "style_emotion": "focused",
        "style_intensity": "controlled",
        "seed": 64032,
        "candidate_ordinal": 1,
        "exaggeration": 0.6,
        "cfg_weight": 0.3,
        "temperature": 0.8,
        "repetition_penalty": 1.2,
        "min_p": 0.05,
        "top_p": 1.0,
        "post_generation_truncation_allowed": False,
        "post_generation_time_stretch_allowed": False,
        "same_control_path_retry_allowed": False,
    }
    for key, value in expected_contract.items():
        if contract.get(key) != value:
            raise ValueError(f"control contract drift: {key}")
    if implementation.get("control_contract_sha256") != CONTROL_CONTRACT_SHA256:
        raise ValueError("control contract hash drift")
    if runtime.get("runtime_executed") is not True or runtime.get("decode_succeeded") is not True:
        raise ValueError("runtime execution proof drift")
    if runtime.get("post_generation_truncation_applied") is not False:
        raise ValueError("post-generation truncation must remain false")
    if runtime.get("post_generation_time_stretch_applied") is not False:
        raise ValueError("post-generation time stretch must remain false")
    if output.get("sha256") != CANDIDATE_SHA256 or output.get("bytes") != 188204:
        raise ValueError("candidate binding drift")
    if output.get("pcm", {}).get("duration_seconds") != 3.92:
        raise ValueError("candidate duration drift")
    if output.get("perth_watermark_detected") is not True:
        raise ValueError("watermark evidence drift")
    if gates.get("dialogue_timing_pass") is not False:
        raise ValueError("candidate timing must remain false")
    if gates.get("production_proof_authority_pass") is not False:
        raise ValueError("production authority must remain false")
    if boundaries.get("maximum_candidates_for_control_path") != 1:
        raise ValueError("one-candidate stop-rule drift")
    if boundaries.get("same_control_path_retry_allowed") is not False:
        raise ValueError("same-path retry boundary drift")


def verify_evaluation(payload: dict) -> None:
    if payload.get("status") != "FAIL_CHATTERBOX_DIALOGUE_TIMING":
        raise ValueError("evaluation status drift")
    candidate = payload.get("candidate", {})
    expected = {
        "expected_text": EXPECTED_TEXT,
        "asr_transcript": EXPECTED_TEXT,
        "normalized_wer": 0.0,
        "speaker_similarity": 0.6610352993011475,
        "validated_speaker_threshold": 0.33445611596107483,
        "dnsmos_reference_percentile": 0.875,
        "target_emotion": "focused",
        "target_intensity": "controlled",
        "duration_seconds": 3.92,
        "expected_duration_seconds": 3.0,
        "perth_watermark_score": 1.0,
    }
    for key, value in expected.items():
        if candidate.get(key) != value:
            raise ValueError(f"candidate metric drift: {key}")
    if candidate.get("dnsmos", {}).get("OVRL") != 3.200727064729366:
        raise ValueError("candidate DNSMOS drift")
    emotion = candidate.get("predicted_emotion", {})
    if emotion.get("predicted_label") != "neutral":
        raise ValueError("candidate emotion drift")
    gates = payload.get("gates", {})
    for key in (
        "candidate_asr_pass",
        "candidate_reference_speaker_identity_pass",
        "candidate_dnsmos_worst_reference_floor_pass",
    ):
        if gates.get(key) is not True:
            raise ValueError(f"validated automated gate drift: {key}")
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
    if gates.get("candidate_dnsmos_quality_certification_pass") is not None:
        raise ValueError("DNSMOS must not self-certify production quality")
    if gates.get("target_intensity_taxonomy_supported") is not None:
        raise ValueError("unmeasured intensity must remain null")


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
    runtime_binding, runtime = load_bound_json(
        runtime_path, RUNTIME_MANIFEST_SHA256, "Chatterbox runtime manifest"
    )
    evaluation_binding, evaluation = load_bound_json(
        evaluation_path, EVALUATION_SHA256, "Chatterbox evaluation"
    )
    verify_runtime(runtime)
    verify_evaluation(evaluation)
    bindings = {
        "candidate": require_hash(candidate, CANDIDATE_SHA256, "Chatterbox WAV"),
        "runtime_manifest": runtime_binding,
        "evaluation": evaluation_binding,
        "reference": require_hash(reference, REFERENCE_SHA256, "reference WAV"),
        "runner": require_git_normalized_text_hash(
            Path(args.runner), RUNNER_SHA256, "Chatterbox runner"
        ),
        "evaluator": require_git_normalized_text_hash(
            Path(args.evaluator), EVALUATOR_SHA256, "Chatterbox evaluator"
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
        "reference": copy_exact(reference, artifact_dir / reference.name, REFERENCE_SHA256, "reference"),
    }
    gates = evaluation["gates"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_chatterbox_dialogue_rejection_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "FAIL_CHATTERBOX_DIALOGUE_TIMING",
        "classification": "CHATTERBOX_DIALOGUE_REJECTED_NO_RETRY",
        "artifact_bindings": bindings,
        "durable_artifacts": durable,
        "control_contract": runtime["implementation"]["control_contract"],
        "runtime": runtime["runtime"],
        "candidate": evaluation["candidate"],
        "acceptance": {
            "engine_runtime_executed": True,
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
            "same_control_path_retry_authorized": False,
            "reason": (
                "The one authorized Chatterbox take preserves the exact dialogue at WER 0.0, "
                "passes the calibrated speaker and DNSMOS floor checks, and retains its watermark, "
                "but lasts 3.92 seconds against the 3.0-second contract. Focused emotion, controlled "
                "intensity, independent playback, and production authority also remain unproven."
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
        raise ValueError("Chatterbox evidence mirrors diverged")
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "candidate",
        "runtime-manifest",
        "evaluation",
        "reference",
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
