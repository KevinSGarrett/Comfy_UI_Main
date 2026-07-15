#!/usr/bin/env python3
"""Calibrate CV3 matched-speaker scoring and evaluate one derived voice stem."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import shutil
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


BASE_ADAPTER_SHA256 = "f3810a26e129021c8179c982eb0901c5f8f3f07b6508ab4c56cace6bfb3862c8"
CV3_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
ERES2NET_SHA256 = "d8941f5952e31820173c8854562cb6d7897aaa58cd65c18f30d5a2e52d30847d"
CV3_MAPS = {
    "emotion": {
        "directory": "data/subjective_continue/emotion/en",
        "prompt_wav.scp": "b73af92b2b2b8efba01f63fe1f32b6bebbca68f137d0ee14d56dd740743f0c72",
        "gt_wav.scp": "c613ac577692b2f372968f437e210e9b81a00d11f344eed6f1ea22e4a09ed285",
        "prompt_text": "575dc32cc26a8b186e9cb5db1a5317a27fdee0b24a09b7216bfc94de507fa02f",
        "text": "e552deced3b90389ec573f14c6b4c25b072204eb7e309a952ca3cbb2aaf0e912",
        "count": 16,
    },
    "speed": {
        "directory": "data/subjective_continue/speed/en",
        "prompt_wav.scp": "4752386ebc4a912eeeb64127d0d06e256a62cfcdc6904bcfb9e4555e5ceeadb3",
        "gt_wav.scp": "987034e9fc38e8adafa035a6055d3f1f707b1639809f25323685df45a6f56300",
        "prompt_text": "31fa365f765934d0dc886fb63087872eea2418b7b291118ef253ac0cba52dc7b",
        "text": "f4d22db79ce8e14a163f913d87426473dfd793996d6f21e5dc712a97f925a30f",
        "count": 10,
    },
    "volume": {
        "directory": "data/subjective_continue/volume/en",
        "prompt_wav.scp": "217eaf230def521f6802edd0e914126f3973140d72924418323b01e3c547bb56",
        "gt_wav.scp": "5b2b0c1fad0d3b8a0591195f29dd08a0656e12196cbba088faf20120803a3fdc",
        "prompt_text": "607349ad5ff1a7c968958c0e6112e2b2fa08ec15b4e60a3071e765a7e6594c7a",
        "text": "203878600f2820c72176a6d1dfc351328248df8b6ec40322fb4c696adda51cda",
        "count": 10,
    },
    "rhyme": {
        "directory": "data/subjective_continue/rhyme/en_rhyme",
        "prompt_wav.scp": "13f447ad330d8291e46049ad6566d40327426adf720ed8b02b7dce5b00e20bc7",
        "gt_wav.scp": "f4b75eee57e95d97101d91b468aad97bd98fec6673b1ee477a4137d9303af4e7",
        "prompt_text": "251f661d9afc01597ec85a91c92ed6a598c45bcfb73e4f562654551d08750a6a",
        "text": "f048b12285751adbd570cdce24d3178664b2e992098f2b69916c3b1ace7c566d",
        "count": 10,
    },
}
LEGACY_MAP_PREFIX = "data/subjective_zeroshot_continue/"
CANONICAL_MAP_PREFIX = "data/subjective_continue/"


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
    if actual.lower() != expected.lower():
        raise ValueError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def published_binding(source: Path, published: Path) -> dict:
    if not source.is_file():
        raise ValueError(f"published binding source is missing: {source}")
    return {"path": str(published), "sha256": sha256(source), "bytes": source.stat().st_size}


def load_json_binding(path: Path, expected: str, label: str) -> tuple[dict, dict]:
    binding = require_hash(path, expected, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def load_base_adapter(path: Path, expected: str):
    require_hash(path, expected, "CV3 base calibration adapter")
    spec = importlib.util.spec_from_file_location("wave64_cv3_base_adapter", path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load CV3 base calibration adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_kaldi_map(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"invalid Kaldi map line {line_number}: {path}")
        if parts[0] in entries:
            raise ValueError(f"duplicate Kaldi key {parts[0]}: {path}")
        entries[parts[0]] = parts[1]
    if not entries:
        raise ValueError(f"Kaldi map is empty: {path}")
    return entries


def resolve_cv3_waveform(cv3_root: Path, mapped_path: str) -> Path:
    normalized = mapped_path.replace("\\", "/")
    if not normalized.startswith(LEGACY_MAP_PREFIX):
        raise ValueError(f"unsupported CV3 waveform map prefix: {mapped_path}")
    normalized = CANONICAL_MAP_PREFIX + normalized[len(LEGACY_MAP_PREFIX) :]
    resolved = (cv3_root / normalized).resolve()
    try:
        resolved.relative_to(cv3_root)
    except ValueError as exc:
        raise ValueError(f"CV3 waveform escapes dataset root: {resolved}") from exc
    if not resolved.is_file():
        raise ValueError(f"CV3 waveform is missing after canonical prefix repair: {resolved}")
    return resolved


def load_cv3_pairs(cv3_root: Path) -> tuple[list[dict], dict]:
    pairs: list[dict] = []
    map_bindings: dict[str, dict] = {}
    for category, config in CV3_MAPS.items():
        directory = cv3_root / config["directory"]
        bound_maps = {
            name: require_hash(directory / name, digest, f"CV3 {category} {name}")
            for name, digest in config.items()
            if name in {"prompt_wav.scp", "gt_wav.scp", "prompt_text", "text"}
        }
        map_bindings[category] = bound_maps
        prompt_wavs = parse_kaldi_map(directory / "prompt_wav.scp")
        target_wavs = parse_kaldi_map(directory / "gt_wav.scp")
        prompt_text = parse_kaldi_map(directory / "prompt_text")
        target_text = parse_kaldi_map(directory / "text")
        key_sets = [set(values) for values in (prompt_wavs, target_wavs, prompt_text, target_text)]
        if any(keys != key_sets[0] for keys in key_sets[1:]):
            raise ValueError(f"CV3 {category} map keys do not match")
        if len(prompt_wavs) != config["count"]:
            raise ValueError(f"CV3 {category} pair count mismatch")
        for sample_id in prompt_wavs:
            prompt_path = resolve_cv3_waveform(cv3_root, prompt_wavs[sample_id])
            target_path = resolve_cv3_waveform(cv3_root, target_wavs[sample_id])
            if prompt_path == target_path:
                raise ValueError(f"CV3 {category} pair aliases one waveform: {sample_id}")
            pairs.append(
                {
                    "category": category,
                    "sample_id": sample_id,
                    "prompt": require_hash(prompt_path, sha256(prompt_path), f"CV3 prompt {sample_id}"),
                    "groundtruth": require_hash(target_path, sha256(target_path), f"CV3 groundtruth {sample_id}"),
                    "prompt_text": prompt_text[sample_id],
                    "groundtruth_text": target_text[sample_id],
                }
            )
    if len(pairs) != sum(config["count"] for config in CV3_MAPS.values()):
        raise ValueError("CV3 total pair count mismatch")
    return pairs, map_bindings


def rates(labels: list[bool], scores: list[float], threshold: float) -> dict:
    if len(labels) != len(scores) or not labels:
        raise ValueError("rates require equal non-empty labels and scores")
    tp = sum(label and score >= threshold for label, score in zip(labels, scores))
    fn = sum(label and score < threshold for label, score in zip(labels, scores))
    fp = sum(not label and score >= threshold for label, score in zip(labels, scores))
    tn = sum(not label and score < threshold for label, score in zip(labels, scores))
    return {
        "threshold": threshold,
        "true_positive": tp,
        "false_negative": fn,
        "false_positive": fp,
        "true_negative": tn,
        "true_positive_rate": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "balanced_accuracy": ((tp / (tp + fn)) + (tn / (tn + fp))) / 2.0,
    }


def select_threshold(labels: list[bool], scores: list[float]) -> tuple[float, dict]:
    unique = sorted(set(scores))
    candidates = [-1.0, *[(left + right) / 2.0 for left, right in zip(unique, unique[1:])], 1.0]
    evaluations = [rates(labels, scores, threshold) for threshold in candidates]
    eligible = [
        entry
        for entry in evaluations
        if entry["true_positive_rate"] >= 0.90 and entry["false_positive_rate"] <= 0.10
    ]
    if not eligible:
        best = max(
            evaluations,
            key=lambda entry: (
                entry["balanced_accuracy"],
                entry["true_positive_rate"],
                -entry["false_positive_rate"],
                entry["threshold"],
            ),
        )
        return best["threshold"], {**best, "training_constraints_pass": False}
    best = max(
        eligible,
        key=lambda entry: (
            entry["balanced_accuracy"],
            entry["true_positive_rate"],
            -entry["false_positive_rate"],
            entry["threshold"],
        ),
    )
    return best["threshold"], {**best, "training_constraints_pass": True}


def score_pairs(pairs: list[dict], evaluator) -> tuple[list[dict], dict[str, object]]:
    embeddings: dict[tuple[str, str, str], object] = {}
    scored_pairs: list[dict] = []
    for pair in pairs:
        category = pair["category"]
        sample_id = pair["sample_id"]
        prompt = evaluator.embedding(Path(pair["prompt"]["path"]))
        target = evaluator.embedding(Path(pair["groundtruth"]["path"]))
        embeddings[(category, sample_id, "prompt")] = prompt
        embeddings[(category, sample_id, "groundtruth")] = target
        scored_pairs.append(
            {
                **pair,
                "matched_similarity": evaluator.similarity(prompt, target),
            }
        )
    return scored_pairs, embeddings


def category_examples(scored_pairs: list[dict], embeddings: dict, evaluator, categories: set[str]):
    labels: list[bool] = []
    scores: list[float] = []
    for category in sorted(categories):
        members = [pair for pair in scored_pairs if pair["category"] == category]
        for pair in members:
            labels.append(True)
            scores.append(pair["matched_similarity"])
            prompt = embeddings[(category, pair["sample_id"], "prompt")]
            for other in members:
                if other["sample_id"] == pair["sample_id"]:
                    continue
                labels.append(False)
                target = embeddings[(category, other["sample_id"], "groundtruth")]
                scores.append(evaluator.similarity(prompt, target))
    return labels, scores


def calibrate(scored_pairs: list[dict], embeddings: dict, evaluator) -> dict:
    categories = set(CV3_MAPS)
    folds = []
    for held_out in sorted(categories):
        train_labels, train_scores = category_examples(
            scored_pairs, embeddings, evaluator, categories - {held_out}
        )
        threshold, train_metrics = select_threshold(train_labels, train_scores)
        test_labels, test_scores = category_examples(scored_pairs, embeddings, evaluator, {held_out})
        test_metrics = rates(test_labels, test_scores, threshold)
        held_out_pass = (
            train_metrics["training_constraints_pass"]
            and test_metrics["true_positive_rate"] >= 0.80
            and test_metrics["false_positive_rate"] <= 0.10
        )
        folds.append(
            {
                "held_out_category": held_out,
                "training_positive_count": sum(train_labels),
                "training_nonmatching_count": len(train_labels) - sum(train_labels),
                "held_out_positive_count": sum(test_labels),
                "held_out_nonmatching_count": len(test_labels) - sum(test_labels),
                "training": train_metrics,
                "held_out": test_metrics,
                "fold_pass": held_out_pass,
            }
        )
    labels, scores = category_examples(scored_pairs, embeddings, evaluator, categories)
    threshold, full_metrics = select_threshold(labels, scores)
    cross_validation_pass = all(fold["fold_pass"] for fold in folds)
    return {
        "method": "leave_one_cv3_continuation_category_out_v1",
        "positive_definition": "CV3 prompt_audio and groundtruth_audio with the same published sample ID",
        "negative_definition": "CV3 prompt_audio and groundtruth_audio with different sample IDs inside one category",
        "negative_identity_caveat": "different sample IDs are nonmatching benchmark pairs, not universal biometric different-speaker labels",
        "training_constraints": {"true_positive_rate_min": 0.90, "false_positive_rate_max": 0.10},
        "held_out_constraints": {"true_positive_rate_min": 0.80, "false_positive_rate_max": 0.10},
        "folds": folds,
        "cross_validation_pass": cross_validation_pass,
        "full_fit": {
            **full_metrics,
            "positive_count": sum(labels),
            "nonmatching_count": len(labels) - sum(labels),
            "deployment_threshold_allowed": cross_validation_pass
            and full_metrics["training_constraints_pass"],
        },
    }


def extract_segments(delivery_manifest: dict, temporary: Path) -> tuple[Path, Path, dict]:
    import soundfile as sf

    source = delivery_manifest.get("source_bindings", {}).get("voice_source", {})
    output = delivery_manifest.get("outputs", {}).get("voice_stem", {})
    source_path = Path(str(source.get("path", ""))).resolve()
    stem_path = Path(str(output.get("path", ""))).resolve()
    source_binding = require_hash(source_path, str(source.get("sha256", "")), "voice source")
    stem_binding = require_hash(stem_path, str(output.get("sha256", "")), "voice stem")
    if source_path == stem_path or source_binding["sha256"] == stem_binding["sha256"]:
        raise ValueError("voice source and derived stem must be distinct artifacts")
    start = float(source.get("excerpt_start_seconds", -1))
    end = float(source.get("excerpt_end_seconds", -1))
    delay = float(delivery_manifest.get("sync", {}).get("voice_start_seconds", -1))
    if start < 0 or end <= start or delay < 0:
        raise ValueError("delivery manifest voice segment timing is invalid")
    duration = end - start
    with sf.SoundFile(str(source_path)) as handle:
        handle.seek(round(start * handle.samplerate))
        source_audio = handle.read(round(duration * handle.samplerate), dtype="float32", always_2d=True)
        source_rate = handle.samplerate
    with sf.SoundFile(str(stem_path)) as handle:
        handle.seek(round(delay * handle.samplerate))
        stem_audio = handle.read(round(duration * handle.samplerate), dtype="float32", always_2d=True)
        stem_rate = handle.samplerate
    if not len(source_audio) or not len(stem_audio):
        raise ValueError("voice identity segment extraction produced empty audio")
    source_segment = temporary / "librivox_reference_excerpt.wav"
    stem_segment = temporary / "derived_voice_stem_active_excerpt.wav"
    sf.write(str(source_segment), source_audio, source_rate, subtype="PCM_16")
    sf.write(str(stem_segment), stem_audio, stem_rate, subtype="PCM_16")
    return source_segment, stem_segment, {
        "source": source_binding,
        "derived_stem": stem_binding,
        "source_excerpt_start_seconds": start,
        "source_excerpt_end_seconds": end,
        "derived_stem_start_seconds": delay,
        "duration_seconds": duration,
    }


def runtime_identity(device: str) -> dict:
    import torch
    import torchaudio

    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torchaudio": torchaudio.__version__,
        "soundfile": metadata.version("soundfile"),
        "device": device,
        "cuda_available": torch.cuda.is_available(),
    }


def build(args: argparse.Namespace) -> dict:
    cv3_root = Path(args.cv3_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if args.device.startswith("cuda"):
        import torch

        if not torch.cuda.is_available():
            raise ValueError("CUDA requested for speaker calibration but unavailable")

    base_path = Path(args.base_adapter_script).resolve()
    base = load_base_adapter(base_path, args.expected_base_adapter_sha256)
    cv3_license = require_hash(cv3_root / "LICENSE", CV3_LICENSE_SHA256, "CV3 license")
    checkpoint_path = (
        cv3_root
        / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    )
    checkpoint = require_hash(checkpoint_path, ERES2NET_SHA256, "ERes2Net checkpoint")
    delivery_evidence_binding, delivery_evidence = load_json_binding(
        Path(args.delivery_evidence).resolve(),
        args.expected_delivery_evidence_sha256,
        "genuine audio delivery evidence",
    )
    delivery_manifest_path = Path(args.delivery_manifest).resolve()
    delivery_manifest_binding, delivery_manifest = load_json_binding(
        delivery_manifest_path,
        args.expected_delivery_manifest_sha256,
        "genuine audio delivery manifest",
    )
    evidence_delivery = delivery_evidence.get("delivery", {})
    if Path(str(evidence_delivery.get("manifest_path", ""))).resolve() != delivery_manifest_path:
        raise ValueError("delivery evidence does not bind the delivery manifest path")
    if str(evidence_delivery.get("manifest_sha256", "")).lower() != delivery_manifest_binding["sha256"]:
        raise ValueError("delivery evidence does not bind the delivery manifest SHA256")
    if delivery_evidence.get("status") != "PASS" or delivery_evidence.get("promotion_claimed") is not False:
        raise ValueError("delivery evidence is not a non-promoted technical PASS")

    pairs, map_bindings = load_cv3_pairs(cv3_root)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        evaluator = base.SpeakerEvaluator(cv3_root / "utils/3D-Speaker", checkpoint_path, args.device)
        scored_pairs, embeddings = score_pairs(pairs, evaluator)
        calibration = calibrate(scored_pairs, embeddings, evaluator)
        reference_segment, stem_segment, chain_binding = extract_segments(delivery_manifest, temporary)
        reference_embedding = evaluator.embedding(reference_segment)
        stem_embedding = evaluator.embedding(stem_segment)
        chain_score = evaluator.similarity(reference_embedding, stem_embedding)
        threshold = calibration["full_fit"]["threshold"]
        threshold_allowed = calibration["full_fit"]["deployment_threshold_allowed"]
        identity_pass = threshold_allowed and chain_score >= threshold
        status = (
            "PASS_CHAIN_SPECIFIC_IDENTITY_PRESERVATION_PRODUCTION_AUTHORITY_BLOCKED"
            if identity_pass
            else "BLOCKED_SPEAKER_CALIBRATION_OR_CHAIN_IDENTITY_THRESHOLD"
        )
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "wave64_cv3_speaker_identity_calibration",
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "classification": "CV3_MATCHED_SPEAKER_CALIBRATION_AND_CHAIN_SPECIFIC_IDENTITY_REVIEW",
            "source_authority": {
                "cv3_repository": "CV3-Eval",
                "cv3_license": "Apache-2.0",
                "cv3_license_binding": cv3_license,
                "base_adapter": require_hash(base_path, BASE_ADAPTER_SHA256, "CV3 base calibration adapter"),
                "eres2net_checkpoint": checkpoint,
                "map_bindings": map_bindings,
                "published_map_prefix_repair": {
                    "from": LEGACY_MAP_PREFIX,
                    "to": CANONICAL_MAP_PREFIX,
                    "other_prefixes_allowed": False,
                },
            },
            "runtime_identity": runtime_identity(args.device),
            "dataset": {
                "pair_count": len(scored_pairs),
                "category_counts": {
                    category: sum(pair["category"] == category for pair in scored_pairs)
                    for category in sorted(CV3_MAPS)
                },
                "pairs": scored_pairs,
            },
            "calibration": calibration,
            "chain_specific_evaluation": {
                "delivery_evidence": delivery_evidence_binding,
                "delivery_manifest": delivery_manifest_binding,
                "binding": chain_binding,
                "reference_excerpt": published_binding(
                    reference_segment, output_dir / reference_segment.name
                ),
                "derived_stem_active_excerpt": published_binding(
                    stem_segment, output_dir / stem_segment.name
                ),
                "speaker_similarity": chain_score,
                "threshold": threshold,
                "threshold_deployment_allowed": threshold_allowed,
                "chain_specific_identity_preservation_pass": identity_pass,
                "claim_scope": "public-domain source excerpt to its derived voice stem in this one delivery chain",
                "independent_reference_for_parler_or_other_tts": False,
            },
            "acceptance": {
                "all_source_hashes_verified": True,
                "cv3_published_pair_keys_exact": True,
                "cv3_pair_waveforms_distinct": True,
                "category_held_out_validation_pass": calibration["cross_validation_pass"],
                "deployment_threshold_allowed": threshold_allowed,
                "chain_specific_identity_preservation_pass": identity_pass,
                "universal_biometric_identity_claim_allowed": False,
                "parler_candidate_reference_identity_claim_allowed": False,
                "emotion_or_style_claim_allowed": False,
                "independent_perceptual_playback_review_pass": False,
                "production_review_authority_allowed": False,
                "authority_registry_mutation_allowed": False,
                "row_completion_allowed": False,
            },
            "remaining_blockers": [
                "the CV3 nonmatching pairs are not universal biometric different-speaker labels",
                "the LibriVox check proves only source-to-derived-stem identity preservation for one chain",
                "the Parler candidates remain rejected and have no independent reference-speaker binding",
                "focused and controlled remain outside the calibrated emotion and style taxonomy",
                "independent perceptual playback and production review authority remain absent",
            ],
            "runtime_boundary": {
                "candidate_regenerated": False,
                "new_voice_generated": False,
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
        (temporary / "calibration_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        temporary.rename(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--base-adapter-script", required=True)
    parser.add_argument("--expected-base-adapter-sha256", default=BASE_ADAPTER_SHA256)
    parser.add_argument("--delivery-evidence", required=True)
    parser.add_argument("--expected-delivery-evidence-sha256", required=True)
    parser.add_argument("--delivery-manifest", required=True)
    parser.add_argument("--expected-delivery-manifest-sha256", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2))
