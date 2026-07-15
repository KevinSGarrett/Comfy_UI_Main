#!/usr/bin/env python3
"""Package OpenSLR31 speaker validation into durable Wave64 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_SHA256 = "24666924428f8b23c3db4c15597713590171133c1f91288bc69925b41772a092"
INVENTORY_SHA256 = "363c871b263873e4efbbb9e8f60ed5ab0e506c572d4983e9b06e85727690f34d"
RESOURCE_PAGE_SHA256 = "3da285125fce2c3a7131d45206ae86f7ed8fd47a4a5b3425f793c0c8ff11bb2f"
IMPLEMENTATION_SHA256 = "7eff346864dae0836eec5d9bd29e68496dbaeadbcaba2f16576abeae86c36470"


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


def verify_manifest(payload: dict) -> None:
    if payload.get("status") != (
        "PASS_DISJOINT_SPEAKER_THRESHOLD_AND_CHAIN_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED"
    ):
        raise ValueError("OpenSLR31 speaker validation status drift")
    dataset = payload.get("dataset", {})
    if dataset.get("speaker_count") != 26 or dataset.get("utterance_count") != 1089:
        raise ValueError("OpenSLR31 speaker or utterance count drift")
    if dataset.get("clips_per_speaker") != 6 or dataset.get("speaker_overlap_count") != 0:
        raise ValueError("OpenSLR31 selection or speaker-overlap drift")
    if len(dataset.get("calibration_speaker_ids", [])) != 13:
        raise ValueError("OpenSLR31 calibration speaker count drift")
    if len(dataset.get("validation_speaker_ids", [])) != 13:
        raise ValueError("OpenSLR31 validation speaker count drift")
    pairs = payload.get("pair_scoring", {})
    for partition in ("calibration", "validation"):
        if pairs.get(partition, {}).get("positive_count") != 195:
            raise ValueError(f"OpenSLR31 {partition} positive-pair count drift")
        if pairs.get(partition, {}).get("different_speaker_count") != 2808:
            raise ValueError(f"OpenSLR31 {partition} different-speaker count drift")
    threshold = payload.get("threshold_validation", {})
    expected = {
        "threshold": 0.33445611596107483,
        "calibration_tpr": 1.0,
        "calibration_fpr": 0.02207977207977208,
        "validation_tpr": 0.9948717948717949,
        "validation_fpr": 0.02564102564102564,
    }
    observed = {
        "threshold": threshold.get("threshold"),
        "calibration_tpr": threshold.get("calibration", {}).get("true_positive_rate"),
        "calibration_fpr": threshold.get("calibration", {}).get("false_positive_rate"),
        "validation_tpr": threshold.get("validation", {}).get("true_positive_rate"),
        "validation_fpr": threshold.get("validation", {}).get("false_positive_rate"),
    }
    if observed != expected:
        raise ValueError(f"OpenSLR31 threshold metrics drift: {observed}")
    if threshold.get("speaker_disjoint_validation_pass") is not True:
        raise ValueError("OpenSLR31 speaker-disjoint validation must pass")
    chain = payload.get("chain_specific_evaluation", {})
    if chain.get("speaker_similarity") != 0.9932656288146973:
        raise ValueError("chain-specific speaker score drift")
    if chain.get("chain_specific_identity_preservation_pass") is not True:
        raise ValueError("chain-specific identity preservation must pass")
    acceptance = payload.get("acceptance", {})
    required_true = (
        "official_archive_hash_verified",
        "official_resource_license_declaration_verified",
        "numeric_speaker_labels_verified",
        "speaker_disjoint_validation_pass",
        "threshold_deployment_allowed_for_chain_specific_evaluation",
        "chain_specific_identity_preservation_pass",
    )
    for key in required_true:
        if acceptance.get(key) is not True:
            raise ValueError(f"{key} must be true")
    required_false = (
        "universal_biometric_identity_claim_allowed",
        "parler_candidate_reference_identity_claim_allowed",
        "emotion_or_style_claim_allowed",
        "independent_perceptual_playback_review_pass",
        "production_review_authority_allowed",
        "authority_registry_mutation_allowed",
        "row_completion_allowed",
    )
    for key in required_false:
        if acceptance.get(key) is not False:
            raise ValueError(f"{key} must remain false")
    if payload.get("row_complete") is not False:
        raise ValueError("OpenSLR31 speaker validation cannot complete a row")


def copy_exact(source: Path, destination: Path, expected: str, label: str) -> dict:
    require_hash(source, expected, label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or sha256(destination) != expected:
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    return require_hash(destination, expected, f"durable {label}")


def package(
    runtime_manifest: Path,
    dataset_inventory: Path,
    resource_page: Path,
    artifact_dir: Path,
    implementation: Path,
) -> dict:
    manifest_binding, manifest = load_bound_json(
        runtime_manifest, MANIFEST_SHA256, "OpenSLR31 speaker validation manifest"
    )
    verify_manifest(manifest)
    implementation_binding = require_hash(
        implementation, IMPLEMENTATION_SHA256, "OpenSLR31 speaker validation implementation"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    durable = {
        "validation_manifest": copy_exact(
            runtime_manifest,
            artifact_dir / runtime_manifest.name,
            MANIFEST_SHA256,
            "OpenSLR31 speaker validation manifest",
        ),
        "dataset_inventory": copy_exact(
            dataset_inventory,
            artifact_dir / dataset_inventory.name,
            INVENTORY_SHA256,
            "OpenSLR31 dataset inventory",
        ),
        "resource_page": copy_exact(
            resource_page,
            artifact_dir / resource_page.name,
            RESOURCE_PAGE_SHA256,
            "OpenSLR31 resource page",
        ),
    }
    threshold = manifest["threshold_validation"]
    chain = manifest["chain_specific_evaluation"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_openslr31_speaker_identity_validation_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "PASS_CHAIN_SPECIFIC_SPEAKER_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED",
        "classification": (
            "OPENSLR31_DISJOINT_SPEAKER_THRESHOLD_AND_CHAIN_SPECIFIC_IDENTITY_PASS_"
            "PRODUCTION_AUTHORITY_BLOCKED"
        ),
        "artifact_bindings": {
            "runtime_validation_manifest": manifest_binding,
            "durable_artifacts": durable,
        },
        "implementation_binding": implementation_binding,
        "source_authority": {
            "dataset": "OpenSLR31 Mini LibriSpeech dev-clean-2",
            "resource_url": "https://www.openslr.org/31/",
            "archive_url": "https://www.openslr.org/resources/31/dev-clean-2.tar.gz",
            "license": "CC BY 4.0",
            "archive_sha256": "176ec501490eced2d6c1f89f4f0ddc7dfe799e649e5322f8ba49fe3ff50c8012",
            "archive_md5": "6d7ab67ac6a1d2c993d050e16d61080d",
            "archive_copied_to_repository": False,
        },
        "runtime_identity": manifest["runtime_identity"],
        "dataset": {
            "speaker_count": manifest["dataset"]["speaker_count"],
            "utterance_count": manifest["dataset"]["utterance_count"],
            "clips_per_speaker": manifest["dataset"]["clips_per_speaker"],
            "calibration_speaker_count": len(manifest["dataset"]["calibration_speaker_ids"]),
            "validation_speaker_count": len(manifest["dataset"]["validation_speaker_ids"]),
            "speaker_overlap_count": manifest["dataset"]["speaker_overlap_count"],
        },
        "pair_scoring": manifest["pair_scoring"],
        "threshold_validation": threshold,
        "chain_specific_result": {
            "speaker_similarity": chain["speaker_similarity"],
            "validated_threshold": chain["validated_threshold"],
            "identity_preservation_verified": chain[
                "chain_specific_identity_preservation_pass"
            ],
            "claim_scope": chain["claim_scope"],
            "parler_or_other_tts_reference_identity_verified": False,
        },
        "acceptance": {
            "speaker_model_execution_path_verified": True,
            "independent_numeric_speaker_labels_verified": True,
            "speaker_disjoint_threshold_generalization_pass": True,
            "chain_specific_identity_preservation_verified": True,
            "parler_reference_speaker_identity_verified": False,
            "emotion_or_style_verified": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "authority_registry_mutation_allowed": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "remaining_blockers": manifest["remaining_blockers"],
        "affected_rows": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "runtime_boundary": manifest["runtime_boundary"],
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
        raise ValueError("QA and Tracker OpenSLR31 evidence mirrors diverged")
    return evidence_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-manifest", required=True)
    parser.add_argument("--dataset-inventory", required=True)
    parser.add_argument("--resource-page", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--qa-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(
        Path(args.runtime_manifest).resolve(),
        Path(args.dataset_inventory).resolve(),
        Path(args.resource_page).resolve(),
        Path(args.artifact_dir).resolve(),
        Path(args.implementation).resolve(),
    )
    outputs = [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()]
    evidence_sha256 = write_exact(payload, outputs)
    print(
        json.dumps(
            {"classification": payload["classification"], "sha256": evidence_sha256}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
