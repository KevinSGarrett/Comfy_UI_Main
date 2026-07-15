#!/usr/bin/env python3
"""Package the CV3 speaker-threshold blocker into durable Wave64 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CALIBRATION_SHA256 = "0dd33697af5b1ea6c6d1ebbc8a0cb61b15ad39a8f9025d64f269b26c49468d90"
REFERENCE_SHA256 = "ac013d29e84309abd52c49720fe1a9caf2550fd83ce2f8e248be6e4329145f48"
STEM_SHA256 = "c336f9b191e75e4f9306f7dbeb2e2c2e042d2465750c9bab22a526ffd18350dd"
IMPLEMENTATION_SHA256 = "1efb201d31cf6b0d479fd4f92df699a3f9d9f34635f80a66ab781583a9dcdf05"


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
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def verify_calibration(payload: dict) -> None:
    if payload.get("status") != "BLOCKED_SPEAKER_CALIBRATION_OR_CHAIN_IDENTITY_THRESHOLD":
        raise ValueError("speaker calibration must remain blocked")
    if payload.get("dataset", {}).get("pair_count") != 46:
        raise ValueError("speaker calibration must bind all 46 CV3 continuation pairs")
    calibration = payload.get("calibration", {})
    if calibration.get("cross_validation_pass") is not False:
        raise ValueError("speaker calibration cross-validation must remain failed")
    folds = {fold.get("held_out_category"): fold for fold in calibration.get("folds", [])}
    if set(folds) != {"emotion", "rhyme", "speed", "volume"}:
        raise ValueError("speaker calibration fold set drift")
    emotion = folds["emotion"]
    if emotion.get("fold_pass") is not False:
        raise ValueError("emotion held-out fold must remain failed")
    if emotion.get("held_out", {}).get("false_positive_rate") != 0.15416666666666667:
        raise ValueError("emotion held-out false-positive rate drift")
    full_fit = calibration.get("full_fit", {})
    if full_fit.get("deployment_threshold_allowed") is not False:
        raise ValueError("speaker deployment threshold must remain unauthorized")
    chain = payload.get("chain_specific_evaluation", {})
    if chain.get("speaker_similarity") != 0.9932656288146973:
        raise ValueError("chain-specific speaker similarity drift")
    if chain.get("chain_specific_identity_preservation_pass") is not False:
        raise ValueError("chain identity preservation must remain unresolved")
    acceptance = payload.get("acceptance", {})
    for key in (
        "universal_biometric_identity_claim_allowed",
        "parler_candidate_reference_identity_claim_allowed",
        "emotion_or_style_claim_allowed",
        "independent_perceptual_playback_review_pass",
        "production_review_authority_allowed",
        "authority_registry_mutation_allowed",
        "row_completion_allowed",
    ):
        if acceptance.get(key) is not False:
            raise ValueError(f"{key} must remain false")
    if payload.get("row_complete") is not False:
        raise ValueError("speaker calibration cannot complete a row")


def copy_exact(source: Path, destination: Path, expected: str, label: str) -> dict:
    require_hash(source, expected, label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or sha256(destination) != expected:
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    return require_hash(destination, expected, f"durable {label}")


def package(runtime_dir: Path, artifact_dir: Path, implementation: Path) -> dict:
    calibration_path = runtime_dir / "calibration_manifest.json"
    calibration_binding, calibration = load_bound_json(
        calibration_path, CALIBRATION_SHA256, "speaker calibration manifest"
    )
    verify_calibration(calibration)
    implementation_binding = require_hash(
        implementation, IMPLEMENTATION_SHA256, "speaker calibration implementation"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    durable = {
        "calibration_manifest": copy_exact(
            calibration_path,
            artifact_dir / calibration_path.name,
            CALIBRATION_SHA256,
            "speaker calibration manifest",
        ),
        "reference_excerpt": copy_exact(
            runtime_dir / "librivox_reference_excerpt.wav",
            artifact_dir / "librivox_reference_excerpt.wav",
            REFERENCE_SHA256,
            "LibriVox reference excerpt",
        ),
        "derived_stem_active_excerpt": copy_exact(
            runtime_dir / "derived_voice_stem_active_excerpt.wav",
            artifact_dir / "derived_voice_stem_active_excerpt.wav",
            STEM_SHA256,
            "derived voice stem active excerpt",
        ),
    }
    folds = {fold["held_out_category"]: fold for fold in calibration["calibration"]["folds"]}
    full_fit = calibration["calibration"]["full_fit"]
    chain = calibration["chain_specific_evaluation"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_cv3_speaker_identity_calibration_blocker",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "BLOCKED_CV3_SPEAKER_THRESHOLD_GENERALIZATION",
        "classification": "CV3_MATCHED_SPEAKER_EXECUTION_PASS_HELD_OUT_GENERALIZATION_BLOCKED",
        "artifact_bindings": {
            "runtime_calibration_manifest": calibration_binding,
            "durable_artifacts": durable,
        },
        "implementation_binding": implementation_binding,
        "runtime_identity": calibration["runtime_identity"],
        "dataset": {
            "pair_count": calibration["dataset"]["pair_count"],
            "category_counts": calibration["dataset"]["category_counts"],
            "source_hashes_verified": calibration["acceptance"]["all_source_hashes_verified"],
        },
        "calibration": {
            "method": calibration["calibration"]["method"],
            "cross_validation_pass": calibration["calibration"]["cross_validation_pass"],
            "folds": calibration["calibration"]["folds"],
            "full_fit": full_fit,
            "blocking_fold": {
                "held_out_category": "emotion",
                "true_positive_rate": folds["emotion"]["held_out"]["true_positive_rate"],
                "false_positive_rate": folds["emotion"]["held_out"]["false_positive_rate"],
                "required_false_positive_rate_max": 0.10,
            },
        },
        "chain_specific_observation": {
            "source_sha256": chain["binding"]["source"]["sha256"],
            "derived_stem_sha256": chain["binding"]["derived_stem"]["sha256"],
            "speaker_similarity": chain["speaker_similarity"],
            "observed_full_fit_threshold": chain["threshold"],
            "threshold_deployment_allowed": chain["threshold_deployment_allowed"],
            "identity_preservation_verified": chain["chain_specific_identity_preservation_pass"],
            "claim_scope": chain["claim_scope"],
        },
        "acceptance": {
            "speaker_model_execution_path_verified": True,
            "cv3_matched_pair_execution_verified": True,
            "chain_specific_similarity_observed": True,
            "speaker_threshold_generalization_pass": False,
            "chain_specific_identity_preservation_verified": False,
            "parler_reference_speaker_identity_verified": False,
            "emotion_or_style_verified": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "authority_registry_mutation_allowed": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "remaining_blockers": calibration["remaining_blockers"],
        "affected_rows": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "runtime_boundary": calibration["runtime_boundary"],
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
        raise ValueError("QA and Tracker speaker evidence mirrors diverged")
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--qa-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(
        Path(args.runtime_dir).resolve(),
        Path(args.artifact_dir).resolve(),
        Path(args.implementation).resolve(),
    )
    outputs = [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()]
    digest = write_exact(payload, outputs)
    print(json.dumps({"classification": payload["classification"], "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
