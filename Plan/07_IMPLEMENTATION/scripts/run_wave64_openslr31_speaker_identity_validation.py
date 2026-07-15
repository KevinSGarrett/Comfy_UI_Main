#!/usr/bin/env python3
"""Validate the Wave64 speaker threshold on disjoint OpenSLR31 speakers."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


SPEAKER_CALIBRATION_SCRIPT_SHA256 = "05054695645ed51ee6aa04a43366057cd256101a80469eea0759b837f9edf05a"
OPENSLR31_ARCHIVE_SHA256 = "176ec501490eced2d6c1f89f4f0ddc7dfe799e649e5322f8ba49fe3ff50c8012"
OPENSLR31_ARCHIVE_MD5 = "6d7ab67ac6a1d2c993d050e16d61080d"
OPENSLR31_INVENTORY_SHA256 = "363c871b263873e4efbbb9e8f60ed5ab0e506c572d4983e9b06e85727690f34d"
PREVIOUS_CALIBRATION_MANIFEST_SHA256 = "0dd33697af5b1ea6c6d1ebbc8a0cb61b15ad39a8f9025d64f269b26c49468d90"
EXPECTED_SPEAKER_COUNT = 26
EXPECTED_UTTERANCE_COUNT = 1089
DEFAULT_CLIPS_PER_SPEAKER = 6
RESOURCE_URL = "https://www.openslr.org/31/"
ARCHIVE_URL = "https://www.openslr.org/resources/31/dev-clean-2.tar.gz"


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def require_hash(path: Path, expected: str, label: str, algorithm: str = "sha256") -> dict:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = digest(path, algorithm)
    if actual.lower() != expected.lower():
        raise ValueError(f"{label} {algorithm.upper()} mismatch: expected {expected}, got {actual}")
    return {"path": str(path), algorithm: actual, "bytes": path.stat().st_size}


def load_json_binding(path: Path, expected: str, label: str) -> tuple[dict, dict]:
    binding = require_hash(path, expected, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def load_module(path: Path, expected: str, name: str):
    require_hash(path, expected, name)
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def verify_resource_page(path: Path, expected_sha256: str) -> dict:
    binding = require_hash(path, expected_sha256, "OpenSLR31 resource page")
    parser = TextExtractor()
    parser.feed(path.read_text(encoding="utf-8"))
    text = " ".join(parser.parts)
    required = ["Mini LibriSpeech ASR corpus", "CC BY 4.0", "dev-clean-2.tar.gz"]
    missing = [value for value in required if value not in text]
    if missing:
        raise ValueError(f"OpenSLR31 resource page is missing required declarations: {missing}")
    return {**binding, "url": RESOURCE_URL, "required_declarations": required}


def select_spread(items: list[Path], count: int) -> list[Path]:
    if count < 2:
        raise ValueError("clips per speaker must be at least two")
    if len(items) < count:
        raise ValueError(f"speaker has only {len(items)} utterances, needs {count}")
    if len(items) == count:
        return list(items)
    indices = [round(index * (len(items) - 1) / (count - 1)) for index in range(count)]
    if len(set(indices)) != count:
        raise ValueError("spread selection produced duplicate indices")
    return [items[index] for index in indices]


def validate_utterance_path(dataset_root: Path, speaker_id: str, path: Path) -> None:
    try:
        relative = path.resolve().relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError(f"utterance escapes dataset root: {path}") from exc
    if len(relative.parts) != 3 or relative.parts[0] != speaker_id:
        raise ValueError(f"utterance is outside its speaker directory: {relative}")
    chapter_id = relative.parts[1]
    stem_parts = path.stem.split("-")
    if len(stem_parts) != 3 or stem_parts[0] != speaker_id or stem_parts[1] != chapter_id:
        raise ValueError(f"utterance filename does not bind speaker/chapter identity: {relative}")


def discover_speakers(dataset_root: Path, clips_per_speaker: int) -> tuple[list[dict], int]:
    if not dataset_root.is_dir():
        raise ValueError(f"OpenSLR31 dataset root is missing: {dataset_root}")
    speaker_dirs = [path for path in dataset_root.iterdir() if path.is_dir()]
    if any(not path.name.isdigit() for path in speaker_dirs):
        raise ValueError("OpenSLR31 speaker directories must use numeric speaker IDs")
    speaker_dirs.sort(key=lambda path: int(path.name))
    if len(speaker_dirs) != EXPECTED_SPEAKER_COUNT:
        raise ValueError(
            f"OpenSLR31 speaker count mismatch: expected {EXPECTED_SPEAKER_COUNT}, got {len(speaker_dirs)}"
        )

    records: list[dict] = []
    total_utterances = 0
    for speaker_dir in speaker_dirs:
        utterances = sorted(speaker_dir.rglob("*.flac"), key=lambda path: path.as_posix())
        total_utterances += len(utterances)
        for path in utterances:
            validate_utterance_path(dataset_root, speaker_dir.name, path)
        selected = select_spread(utterances, clips_per_speaker)
        records.append(
            {
                "speaker_id": speaker_dir.name,
                "utterance_count": len(utterances),
                "selected": [
                    {
                        "path": str(path),
                        "relative_path": path.relative_to(dataset_root).as_posix(),
                        "sha256": digest(path),
                        "bytes": path.stat().st_size,
                    }
                    for path in selected
                ],
            }
        )
    if total_utterances != EXPECTED_UTTERANCE_COUNT:
        raise ValueError(
            f"OpenSLR31 utterance count mismatch: expected {EXPECTED_UTTERANCE_COUNT}, got {total_utterances}"
        )
    return records, total_utterances


def verify_inventory(inventory: dict, speakers: list[dict], utterance_count: int) -> None:
    if inventory.get("schema_version") != "wave64_openslr31_dataset_inventory_v1":
        raise ValueError("OpenSLR31 inventory schema is unsupported")
    if inventory.get("source", {}).get("license") != "CC BY 4.0":
        raise ValueError("OpenSLR31 inventory license declaration is missing")
    if inventory.get("archive", {}).get("sha256") != OPENSLR31_ARCHIVE_SHA256:
        raise ValueError("OpenSLR31 inventory archive SHA256 does not match authority")
    if inventory.get("archive", {}).get("md5") != OPENSLR31_ARCHIVE_MD5:
        raise ValueError("OpenSLR31 inventory archive MD5 does not match authority")
    inventory_ids = [str(item.get("speaker_id", "")) for item in inventory.get("speakers", [])]
    observed_ids = [item["speaker_id"] for item in speakers]
    if inventory_ids != observed_ids:
        raise ValueError("OpenSLR31 inventory speaker IDs do not match extracted data")
    if inventory.get("speaker_count") != len(speakers) or inventory.get("utterance_count") != utterance_count:
        raise ValueError("OpenSLR31 inventory counts do not match extracted data")


def partition_speakers(speakers: list[dict]) -> tuple[list[dict], list[dict]]:
    calibration = speakers[::2]
    validation = speakers[1::2]
    calibration_ids = {item["speaker_id"] for item in calibration}
    validation_ids = {item["speaker_id"] for item in validation}
    if len(calibration) != 13 or len(validation) != 13 or calibration_ids & validation_ids:
        raise ValueError("OpenSLR31 speaker-disjoint 13/13 partition failed")
    return calibration, validation


def embed_partition(speakers: list[dict], evaluator) -> dict[str, list]:
    return {
        speaker["speaker_id"]: [
            evaluator.embedding(Path(item["path"])) for item in speaker["selected"]
        ]
        for speaker in speakers
    }


def pair_examples(speakers: list[dict], embeddings: dict[str, list], evaluator) -> tuple[list[bool], list[float]]:
    labels: list[bool] = []
    scores: list[float] = []
    for speaker in speakers:
        values = embeddings[speaker["speaker_id"]]
        for left_index in range(len(values)):
            for right_index in range(left_index + 1, len(values)):
                labels.append(True)
                scores.append(evaluator.similarity(values[left_index], values[right_index]))
    for left_speaker_index, left_speaker in enumerate(speakers):
        left_values = embeddings[left_speaker["speaker_id"]]
        for right_speaker in speakers[left_speaker_index + 1 :]:
            right_values = embeddings[right_speaker["speaker_id"]]
            for left in left_values:
                for right in right_values:
                    labels.append(False)
                    scores.append(evaluator.similarity(left, right))
    return labels, scores


def score_summary(labels: list[bool], scores: list[float]) -> dict:
    positive_scores = [score for label, score in zip(labels, scores) if label]
    negative_scores = [score for label, score in zip(labels, scores) if not label]
    return {
        "positive_count": len(positive_scores),
        "different_speaker_count": len(negative_scores),
        "positive_min": min(positive_scores),
        "positive_max": max(positive_scores),
        "different_speaker_min": min(negative_scores),
        "different_speaker_max": max(negative_scores),
    }


def evaluate_threshold(calibration_labels, calibration_scores, validation_labels, validation_scores, authority):
    threshold, calibration_metrics = authority.select_threshold(calibration_labels, calibration_scores)
    validation_metrics = authority.rates(validation_labels, validation_scores, threshold)
    validation_pass = (
        calibration_metrics["training_constraints_pass"]
        and validation_metrics["true_positive_rate"] >= 0.80
        and validation_metrics["false_positive_rate"] <= 0.10
    )
    return {
        "method": "openslr31_numeric_speaker_id_disjoint_even_odd_partition_v1",
        "positive_definition": "two distinct utterances under the same published numeric speaker directory",
        "negative_definition": "utterances under different published numeric speaker directories",
        "calibration_constraints": {"true_positive_rate_min": 0.90, "false_positive_rate_max": 0.10},
        "validation_constraints": {"true_positive_rate_min": 0.80, "false_positive_rate_max": 0.10},
        "threshold": threshold,
        "calibration": calibration_metrics,
        "validation": validation_metrics,
        "speaker_disjoint_validation_pass": validation_pass,
        "threshold_deployment_allowed_for_chain_specific_evaluation": validation_pass,
    }


def validate_previous_manifest(payload: dict) -> dict:
    if payload.get("artifact_type") != "wave64_cv3_speaker_identity_calibration":
        raise ValueError("previous speaker calibration manifest has the wrong artifact type")
    chain = payload.get("chain_specific_evaluation", {})
    score = chain.get("speaker_similarity")
    if not isinstance(score, (int, float)) or not math.isfinite(score):
        raise ValueError("previous speaker calibration manifest lacks a finite chain score")
    if chain.get("threshold_deployment_allowed") is not False:
        raise ValueError("previous speaker calibration must preserve its blocked threshold decision")
    return {"speaker_similarity": float(score), "binding": chain.get("binding", {})}


def build(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    dataset_root = Path(args.dataset_root).resolve()
    archive_path = Path(args.archive).resolve()
    resource_page_path = Path(args.resource_page).resolve()
    inventory_path = Path(args.dataset_inventory).resolve()
    previous_path = Path(args.previous_calibration_manifest).resolve()
    cv3_root = Path(args.cv3_root).resolve()

    archive_binding = require_hash(archive_path, args.expected_archive_sha256, "OpenSLR31 archive")
    archive_md5 = require_hash(archive_path, OPENSLR31_ARCHIVE_MD5, "OpenSLR31 archive", "md5")
    resource_binding = verify_resource_page(resource_page_path, args.expected_resource_page_sha256)
    inventory_binding, inventory = load_json_binding(
        inventory_path, args.expected_inventory_sha256, "OpenSLR31 dataset inventory"
    )
    previous_binding, previous = load_json_binding(
        previous_path, args.expected_previous_calibration_sha256, "previous speaker calibration manifest"
    )
    previous_chain = validate_previous_manifest(previous)

    speakers, utterance_count = discover_speakers(dataset_root, args.clips_per_speaker)
    verify_inventory(inventory, speakers, utterance_count)
    calibration_speakers, validation_speakers = partition_speakers(speakers)

    speaker_script_path = Path(args.speaker_calibration_script).resolve()
    authority = load_module(
        speaker_script_path,
        args.expected_speaker_calibration_script_sha256,
        "wave64_speaker_calibration_authority",
    )
    base_path = Path(args.base_adapter_script).resolve()
    base = authority.load_base_adapter(base_path, args.expected_base_adapter_sha256)
    checkpoint_path = (
        cv3_root
        / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    )
    checkpoint = require_hash(checkpoint_path, authority.ERES2NET_SHA256, "ERes2Net checkpoint")
    cv3_license = require_hash(cv3_root / "LICENSE", authority.CV3_LICENSE_SHA256, "CV3 tooling license")

    if args.device.startswith("cuda"):
        import torch

        if not torch.cuda.is_available():
            raise ValueError("CUDA requested for OpenSLR31 speaker validation but unavailable")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        evaluator = base.SpeakerEvaluator(cv3_root / "utils/3D-Speaker", checkpoint_path, args.device)
        calibration_embeddings = embed_partition(calibration_speakers, evaluator)
        validation_embeddings = embed_partition(validation_speakers, evaluator)
        calibration_labels, calibration_scores = pair_examples(
            calibration_speakers, calibration_embeddings, evaluator
        )
        validation_labels, validation_scores = pair_examples(
            validation_speakers, validation_embeddings, evaluator
        )
        threshold_result = evaluate_threshold(
            calibration_labels,
            calibration_scores,
            validation_labels,
            validation_scores,
            authority,
        )
        threshold_allowed = threshold_result[
            "threshold_deployment_allowed_for_chain_specific_evaluation"
        ]
        chain_score = previous_chain["speaker_similarity"]
        chain_pass = threshold_allowed and chain_score >= threshold_result["threshold"]
        status = (
            "PASS_DISJOINT_SPEAKER_THRESHOLD_AND_CHAIN_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED"
            if chain_pass
            else "BLOCKED_DISJOINT_SPEAKER_THRESHOLD_OR_CHAIN_IDENTITY"
        )
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "wave64_openslr31_speaker_identity_validation",
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "classification": "OPENSLR31_SPEAKER_DISJOINT_THRESHOLD_VALIDATION",
            "source_authority": {
                "dataset": "OpenSLR31 Mini LibriSpeech dev-clean-2",
                "resource_url": RESOURCE_URL,
                "archive_url": ARCHIVE_URL,
                "license": "CC BY 4.0",
                "resource_page": resource_binding,
                "archive_sha256": archive_binding,
                "archive_md5": archive_md5,
                "dataset_inventory": inventory_binding,
                "speaker_calibration_authority": require_hash(
                    speaker_script_path,
                    args.expected_speaker_calibration_script_sha256,
                    "speaker calibration authority",
                ),
                "base_adapter": require_hash(
                    base_path, args.expected_base_adapter_sha256, "CV3 base adapter"
                ),
                "cv3_tooling_license": cv3_license,
                "eres2net_checkpoint": checkpoint,
            },
            "runtime_identity": authority.runtime_identity(args.device),
            "dataset": {
                "speaker_count": len(speakers),
                "utterance_count": utterance_count,
                "clips_per_speaker": args.clips_per_speaker,
                "speaker_partition_rule": "numeric speaker IDs sorted ascending; zero-based even ordinals calibrate, odd ordinals validate",
                "calibration_speaker_ids": [item["speaker_id"] for item in calibration_speakers],
                "validation_speaker_ids": [item["speaker_id"] for item in validation_speakers],
                "speaker_overlap_count": 0,
                "speakers": speakers,
            },
            "pair_scoring": {
                "calibration": score_summary(calibration_labels, calibration_scores),
                "validation": score_summary(validation_labels, validation_scores),
                "same_speaker_pairs_exhaustive_within_selected_clips": True,
                "different_speaker_pairs_exhaustive_across_selected_clips": True,
            },
            "threshold_validation": threshold_result,
            "chain_specific_evaluation": {
                "previous_calibration_manifest": previous_binding,
                "previous_chain_binding": previous_chain["binding"],
                "speaker_similarity": chain_score,
                "validated_threshold": threshold_result["threshold"],
                "threshold_deployment_allowed": threshold_allowed,
                "chain_specific_identity_preservation_pass": chain_pass,
                "claim_scope": "the existing public-domain source excerpt and its derived voice stem only",
                "independent_reference_for_parler_or_other_tts": False,
            },
            "acceptance": {
                "official_archive_hash_verified": True,
                "official_resource_license_declaration_verified": True,
                "numeric_speaker_labels_verified": True,
                "speaker_disjoint_validation_pass": threshold_result[
                    "speaker_disjoint_validation_pass"
                ],
                "threshold_deployment_allowed_for_chain_specific_evaluation": threshold_allowed,
                "chain_specific_identity_preservation_pass": chain_pass,
                "universal_biometric_identity_claim_allowed": False,
                "parler_candidate_reference_identity_claim_allowed": False,
                "emotion_or_style_claim_allowed": False,
                "independent_perceptual_playback_review_pass": False,
                "production_review_authority_allowed": False,
                "authority_registry_mutation_allowed": False,
                "row_completion_allowed": False,
            },
            "remaining_blockers": [
                "the independently labeled threshold applies only to this ERes2Net evaluation configuration",
                "the Parler candidates remain rejected and have no independent reference-speaker binding",
                "focused and controlled remain outside the calibrated emotion and style taxonomy",
                "independent perceptual playback and production review authority remain absent",
            ],
            "runtime_boundary": {
                "candidate_regenerated": False,
                "new_voice_generated": False,
                "dataset_download_performed": True,
                "model_download_performed": False,
                "ec2_started": False,
                "s3_mutated": False,
                "mask_truth_consumed": False,
                "wave71_activated": False,
                "jira_mutated": False,
                "promotion_claimed": False,
            },
            "row_complete": False,
        }
        (temporary / "openslr31_speaker_identity_validation_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        temporary.rename(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--expected-archive-sha256", default=OPENSLR31_ARCHIVE_SHA256)
    parser.add_argument("--resource-page", required=True)
    parser.add_argument("--expected-resource-page-sha256", required=True)
    parser.add_argument("--dataset-inventory", required=True)
    parser.add_argument("--expected-inventory-sha256", default=OPENSLR31_INVENTORY_SHA256)
    parser.add_argument("--previous-calibration-manifest", required=True)
    parser.add_argument(
        "--expected-previous-calibration-sha256", default=PREVIOUS_CALIBRATION_MANIFEST_SHA256
    )
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--speaker-calibration-script", required=True)
    parser.add_argument(
        "--expected-speaker-calibration-script-sha256",
        default=SPEAKER_CALIBRATION_SCRIPT_SHA256,
    )
    parser.add_argument("--base-adapter-script", required=True)
    parser.add_argument("--expected-base-adapter-sha256", required=True)
    parser.add_argument("--clips-per-speaker", type=int, default=DEFAULT_CLIPS_PER_SPEAKER)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2))
