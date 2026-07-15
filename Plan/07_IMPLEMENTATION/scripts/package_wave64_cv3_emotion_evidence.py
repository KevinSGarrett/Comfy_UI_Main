#!/usr/bin/env python3
"""Package the full CV3 emotion2vec calibration into durable Wave64 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CALIBRATION_SHA256 = "c09954c013263e47a9b9d825a69033ad040ee057104da2fc16fe2e1095499b20"
INTAKE_SHA256 = "0c83b3f6cdde19723f782903680a73654028d60aa8d944fe1be2a3c7857305c2"
EVIDENCE_NAME = "W64_CV3_EMOTION2VEC_LOCAL_CALIBRATION_20260715T001113-0500.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bound_json(path: Path, expected_sha256: str, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != expected_sha256:
        raise ValueError(f"{label} SHA256 mismatch: expected {expected_sha256}, got {actual}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def verify_calibration(payload: dict) -> None:
    if payload.get("classification") != "W64_EMOTION2VEC_EXECUTION_PASS_TAXONOMY_BLOCKED":
        raise ValueError("emotion calibration classification drift")
    metrics = payload.get("calibration", {}).get("metrics", {})
    if metrics.get("sample_count") != 300:
        raise ValueError("emotion calibration must include all 300 CV3 references")
    if metrics.get("accuracy") != 0.7233333333333334:
        raise ValueError("emotion calibration accuracy drift")
    if metrics.get("macro_f1") != 0.7967110893382565:
        raise ValueError("emotion calibration macro F1 drift")
    candidate = payload.get("candidate", {})
    if candidate.get("predicted_label") != "neutral":
        raise ValueError("Parler candidate emotion prediction drift")
    if candidate.get("target_emotion_supported") is not False:
        raise ValueError("focused must remain unsupported by the model taxonomy")
    if candidate.get("target_intensity_supported") is not False:
        raise ValueError("controlled must remain unsupported by the CV3 intensity taxonomy")
    if candidate.get("emotion_pass") is not None:
        raise ValueError("candidate emotion pass must remain unresolved")
    gates = payload.get("gates", {})
    if gates.get("emotion_model_execution_pass") is not True:
        raise ValueError("emotion model execution must be passing")
    for key in ("production_emotion_authority_pass", "row_completion_pass", "final_voice_certification_pass"):
        if gates.get(key) is not False:
            raise ValueError(f"{key} must remain false")


def package(calibration_path: Path, intake_path: Path, durable_intake_copy: Path) -> dict:
    calibration = load_bound_json(calibration_path, CALIBRATION_SHA256, "emotion calibration manifest")
    intake = load_bound_json(intake_path, INTAKE_SHA256, "emotion2vec intake manifest")
    verify_calibration(calibration)
    if intake.get("classification") != "W64_EMOTION2VEC_MODELSCOPE_INTAKE_PASS":
        raise ValueError("emotion2vec intake is not passing")
    authority = intake.get("authority", {})
    if authority.get("license") != "Apache License 2.0":
        raise ValueError("emotion2vec intake does not bind the approved license")

    durable_intake_copy.parent.mkdir(parents=True, exist_ok=True)
    if not durable_intake_copy.exists() or sha256(durable_intake_copy) != INTAKE_SHA256:
        temporary = durable_intake_copy.with_suffix(".json.tmp")
        shutil.copyfile(intake_path, temporary)
        os.replace(temporary, durable_intake_copy)

    candidate = calibration["candidate"]
    script_root = Path(__file__).resolve().parent
    implementation_bindings = {}
    for name in (
        "install_wave64_emotion2vec_model.py",
        "run_wave64_cv3_emotion_calibration.py",
        "package_wave64_cv3_emotion_evidence.py",
    ):
        path = script_root / name
        implementation_bindings[name] = {
            "path": str(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    evidence = {
        "schema_version": "1.0",
        "artifact_type": "wave64_cv3_emotion2vec_local_calibration",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "PASS_MODEL_EXECUTION_CALIBRATION_OBSERVED_TARGET_TAXONOMY_BLOCKED",
        "classification": "CV3_EMOTION2VEC_FULL_CALIBRATION_EXECUTION_PASS",
        "source_authority": {
            "model_id": authority["model_id"],
            "license": authority["license"],
            "license_source_url": authority["license_source_url"],
            "model_revision": authority["model_revision"],
            "token_revision": authority["token_revision"],
            "model_files": intake["files"],
            "cv3_license": calibration["cv3_corpus"]["license"],
            "cv3_maps": calibration["cv3_corpus"]["maps"],
        },
        "artifact_bindings": {
            "full_calibration_manifest": {
                "path": str(calibration_path.resolve()),
                "sha256": CALIBRATION_SHA256,
                "bytes": calibration_path.stat().st_size,
            },
            "durable_model_intake_manifest": {
                "path": str(durable_intake_copy.resolve()),
                "sha256": INTAKE_SHA256,
                "bytes": durable_intake_copy.stat().st_size,
            },
        },
        "implementation_bindings": implementation_bindings,
        "runtime_identity": calibration["runtime_identity"],
        "calibration": {
            "total_reference_rows": calibration["cv3_corpus"]["total_rows"],
            "evaluated_reference_rows": calibration["cv3_corpus"]["evaluated_rows"],
            "reference_labels": calibration["cv3_corpus"]["reference_labels"],
            "intensities": calibration["cv3_corpus"]["intensities"],
            "languages": calibration["cv3_corpus"]["languages"],
            "metrics": calibration["calibration"]["metrics"],
            "model_execution_pass": True,
            "registered_acceptance_threshold_present": False,
            "production_emotion_authority_pass": False,
        },
        "candidate": {
            "lineage": candidate["lineage"],
            "predicted_label": candidate["predicted_label"],
            "predicted_score": candidate["predicted_score"],
            "scores": candidate["scores"],
            "target_emotion_supported": candidate["target_emotion_supported"],
            "target_intensity_supported": candidate["target_intensity_supported"],
            "target_emotion_match": candidate["target_emotion_match"],
            "emotion_pass": candidate["emotion_pass"],
            "status": candidate["status"],
        },
        "acceptance": {
            "model_identity_hash_and_license_pass": True,
            "cv3_pairing_and_full_corpus_execution_pass": True,
            "emotion_model_execution_path_verified": True,
            "candidate_emotion_score_present": True,
            "candidate_emotion_verified": False,
            "candidate_intensity_verified": False,
            "independent_playback_review_pass": False,
            "production_proof_authority_pass": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "remaining_blockers": calibration["remaining_blockers"],
        "affected_rows": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "row_complete": False,
        "boundaries": calibration["boundaries"],
    }
    return evidence


def write_exact(payload: dict, paths: list[Path]) -> str:
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    digest = hashlib.sha256(encoded).hexdigest()
    if any(sha256(path) != digest for path in paths):
        raise ValueError("QA and Tracker emotion evidence mirrors diverged")
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-manifest", required=True)
    parser.add_argument("--model-intake-manifest", required=True)
    parser.add_argument("--durable-model-intake-copy", required=True)
    parser.add_argument("--qa-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(
        Path(args.calibration_manifest).resolve(),
        Path(args.model_intake_manifest).resolve(),
        Path(args.durable_model_intake_copy).resolve(),
    )
    paths = [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()]
    digest = write_exact(payload, paths)
    print(json.dumps({"classification": payload["classification"], "sha256": digest, "outputs": [str(p) for p in paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
