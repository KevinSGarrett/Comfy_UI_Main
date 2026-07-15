#!/usr/bin/env python3
"""Calibrate emotion2vec on CV3 labels and score an immutable Parler take."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Callable


MODEL_ID = "iic/emotion2vec_plus_large"
MODEL_REVISION = "v2.0.5"
TOKEN_REVISION = "767b2e00f04e0b75b5408c73be0d666328808af5"
MODEL_SHA256 = "be501a01f26fcdc7663a062dff86af839afbaef7c4de32f5e42d7e1ad2784da4"
CONFIG_SHA256 = "f4fa0eb82cc78bfebb43c56d68791afb01788085a18897d20999af7bc45d51d3"
TOKENS_SHA256 = "866121e470057b847d7a50e9923509141fb2924392f53385a186482a1ec0fb7f"
CV3_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
CV3_EMOTION_MAP_HASHES = {
    "en": "d9ea33b3b9f7ef17b0c05f760a3eb5707b81e7123663843ad6aaf2201f389c67",
    "zh": "4607c8fd0a44d8a61f2a7c76102061aad6e818ff094a314366c86582ef6531ec",
}
EXPECTED_MODEL_LABELS = [
    "angry",
    "disgusted",
    "fearful",
    "happy",
    "neutral",
    "other",
    "sad",
    "surprised",
    "unknown",
]
CV3_REFERENCE_LABELS = ["angry", "happy", "sad"]
CV3_INTENSITIES = ["high", "low"]
CV3_LANGUAGES = ["en", "zh"]
CORPUS_KEY = re.compile(r"^(angry|happy|sad)_(high|low)_uttid_(\d+)$")


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
    return {"path": str(path.resolve()), "sha256": actual, "bytes": path.stat().st_size}


def load_json_binding(path: Path, expected_sha256: str, label: str) -> tuple[dict, dict]:
    binding = require_hash(path, expected_sha256, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return binding, payload


def bind_candidate_lineage(
    candidate: Path,
    expected_candidate_sha256: str,
    packet_path: Path,
    expected_packet_sha256: str,
    contract_path: Path,
    expected_contract_sha256: str,
) -> dict:
    candidate = candidate.resolve()
    candidate_binding = require_hash(candidate, expected_candidate_sha256, "Parler candidate")
    packet_binding, packet = load_json_binding(packet_path, expected_packet_sha256, "Parler packet manifest")
    contract_binding, contract = load_json_binding(contract_path, expected_contract_sha256, "dialogue contract")

    verified_media = packet.get("verified_media")
    timeline = packet.get("timeline_conformance")
    if not isinstance(verified_media, dict) or not isinstance(timeline, dict):
        raise ValueError("Parler packet lacks verified media or timeline conformance")
    if packet.get("result") != "pass" or packet.get("execution_passed") is not True:
        raise ValueError("Parler packet is not a passing runtime packet")
    if timeline.get("speech_truncated") is not False:
        raise ValueError("Parler packet does not prove zero speech truncation")
    if Path(str(verified_media.get("media_path", ""))).resolve() != candidate:
        raise ValueError("Parler packet does not bind the exact candidate path")
    if str(verified_media.get("sha256", "")).lower() != expected_candidate_sha256.lower():
        raise ValueError("Parler packet does not bind the exact candidate SHA256")

    lines = contract.get("lines")
    if not isinstance(lines, list) or len(lines) != 1 or not isinstance(lines[0], dict):
        raise ValueError("dialogue contract must bind exactly one line")
    line = lines[0]
    if Path(str(line.get("output_file", ""))).resolve() != candidate:
        raise ValueError("dialogue contract output_file does not bind the candidate")
    target_emotion = str(line.get("emotion", "")).strip().lower()
    target_intensity = str(line.get("intensity", "")).strip().lower()
    if not target_emotion or not target_intensity:
        raise ValueError("dialogue contract emotion and intensity must be non-empty")

    return {
        "candidate": candidate_binding,
        "packet_manifest": packet_binding,
        "dialogue_contract": contract_binding,
        "line_id": line.get("line_id"),
        "character_id": line.get("character_id"),
        "voice_profile_id": line.get("voice_profile_id"),
        "target_emotion": target_emotion,
        "target_intensity": target_intensity,
        "speech_truncated": False,
    }


def normalize_model_token(value: str) -> str:
    token = value.strip()
    if "/" in token:
        token = token.rsplit("/", 1)[1]
    token = token.strip("<>").strip().lower()
    return "unknown" if token == "unk" else token


def read_model_labels(tokens_path: Path) -> list[str]:
    labels = [normalize_model_token(line) for line in tokens_path.read_text(encoding="utf-8").splitlines()]
    if labels != EXPECTED_MODEL_LABELS:
        raise ValueError(f"emotion2vec token taxonomy mismatch: {labels}")
    return labels


def bind_model(model_dir: Path, intake_manifest: Path, expected_manifest_sha256: str) -> dict:
    manifest_binding, manifest = load_json_binding(
        intake_manifest, expected_manifest_sha256, "emotion2vec intake manifest"
    )
    authority = manifest.get("authority")
    files = manifest.get("files")
    if not isinstance(authority, dict) or not isinstance(files, dict):
        raise ValueError("emotion2vec intake manifest is structurally incomplete")
    if manifest.get("classification") != "W64_EMOTION2VEC_MODELSCOPE_INTAKE_PASS":
        raise ValueError("emotion2vec intake classification is not passing")
    if authority.get("model_id") != MODEL_ID or authority.get("license") != "Apache License 2.0":
        raise ValueError("emotion2vec intake authority does not match the approved ModelScope model")
    if authority.get("model_revision") != MODEL_REVISION or authority.get("token_revision") != TOKEN_REVISION:
        raise ValueError("emotion2vec intake revisions do not match the approved revisions")

    model_dir = model_dir.resolve()
    expected_files = {
        "model.pt": MODEL_SHA256,
        "config.yaml": CONFIG_SHA256,
        "tokens.txt": TOKENS_SHA256,
    }
    bindings = {}
    for name, expected_hash in expected_files.items():
        path = model_dir / name
        binding = require_hash(path, expected_hash, f"emotion2vec {name}")
        manifest_file = files.get(name)
        if not isinstance(manifest_file, dict):
            raise ValueError(f"emotion2vec intake manifest lacks {name}")
        if Path(str(manifest_file.get("path", ""))).resolve() != path:
            raise ValueError(f"emotion2vec intake manifest path mismatch for {name}")
        if str(manifest_file.get("sha256", "")).lower() != expected_hash:
            raise ValueError(f"emotion2vec intake manifest hash mismatch for {name}")
        bindings[name] = binding

    return {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "token_revision": TOKEN_REVISION,
        "license": authority["license"],
        "license_source_url": authority.get("license_source_url"),
        "intake_manifest": manifest_binding,
        "files": bindings,
        "labels": read_model_labels(model_dir / "tokens.txt"),
    }


def parse_cv3_corpus(cv3_root: Path) -> tuple[list[dict], dict]:
    cv3_root = cv3_root.resolve()
    license_binding = require_hash(cv3_root / "LICENSE", CV3_LICENSE_SHA256, "CV3-Eval license")
    records = []
    map_bindings = {}
    for language in CV3_LANGUAGES:
        map_path = cv3_root / "data/emotion_zeroshot" / language / "prompt_wav.scp"
        map_bindings[language] = require_hash(
            map_path, CV3_EMOTION_MAP_HASHES[language], f"CV3 {language} emotion map"
        )
        seen = set()
        for line_number, raw in enumerate(map_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            parts = raw.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"invalid CV3 Kaldi row at {map_path}:{line_number}")
            key, relative = parts
            match = CORPUS_KEY.fullmatch(key)
            if not match:
                raise ValueError(f"unsupported CV3 emotion key: {key}")
            if key in seen:
                raise ValueError(f"duplicate CV3 emotion key: {language}/{key}")
            seen.add(key)
            audio = (cv3_root / relative).resolve()
            try:
                audio.relative_to(cv3_root)
            except ValueError as exc:
                raise ValueError(f"CV3 audio escapes the dataset root: {relative}") from exc
            if not audio.is_file():
                raise ValueError(f"CV3 emotion audio is missing: {audio}")
            records.append(
                {
                    "key": key,
                    "language": language,
                    "reference_label": match.group(1),
                    "intensity": match.group(2),
                    "utterance_index": int(match.group(3)),
                    "audio_path": str(audio),
                }
            )

    counts = Counter((r["language"], r["reference_label"], r["intensity"]) for r in records)
    expected = {
        (language, label, intensity): 25
        for language in CV3_LANGUAGES
        for label in CV3_REFERENCE_LABELS
        for intensity in CV3_INTENSITIES
    }
    if counts != Counter(expected):
        raise ValueError(f"CV3 emotion corpus strata mismatch: {dict(counts)}")
    if len(records) != 300:
        raise ValueError(f"CV3 emotion corpus must contain 300 rows, got {len(records)}")
    return records, {"license": license_binding, "maps": map_bindings, "strata": len(expected)}


def select_records(records: list[dict], limit_per_stratum: int) -> list[dict]:
    if limit_per_stratum < 0 or limit_per_stratum > 25:
        raise ValueError("limit_per_stratum must be between 0 and 25")
    if limit_per_stratum == 0:
        return list(records)
    selected = []
    counts = Counter()
    for record in records:
        key = (record["language"], record["reference_label"], record["intensity"])
        if counts[key] < limit_per_stratum:
            selected.append(record)
            counts[key] += 1
    if len(selected) != 12 * limit_per_stratum:
        raise ValueError("deterministic CV3 sample selection did not cover every stratum")
    return selected


def score_metrics(records: list[dict]) -> dict:
    if not records:
        raise ValueError("emotion metrics require at least one record")
    confusion = {
        reference: {predicted: 0 for predicted in EXPECTED_MODEL_LABELS}
        for reference in CV3_REFERENCE_LABELS
    }
    strata = Counter()
    strata_correct = Counter()
    correct = 0
    for record in records:
        reference = record["reference_label"]
        predicted = record["predicted_label"]
        if reference not in confusion or predicted not in EXPECTED_MODEL_LABELS:
            raise ValueError("emotion metric record contains an unsupported label")
        confusion[reference][predicted] += 1
        stratum = (record["language"], reference, record["intensity"])
        strata[stratum] += 1
        if predicted == reference:
            correct += 1
            strata_correct[stratum] += 1

    per_class = {}
    for label in CV3_REFERENCE_LABELS:
        true_positive = confusion[label][label]
        false_negative = sum(confusion[label].values()) - true_positive
        false_positive = sum(confusion[other][label] for other in CV3_REFERENCE_LABELS if other != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": true_positive + false_negative}

    return {
        "sample_count": len(records),
        "accuracy": correct / len(records),
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(per_class),
        "per_class": per_class,
        "confusion": confusion,
        "stratum_accuracy": {
            "|".join(key): strata_correct[key] / count for key, count in sorted(strata.items())
        },
    }


def parse_inference_result(result: object, labels: list[str]) -> dict:
    if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
        raise ValueError("emotion2vec inference must return one result object")
    scores = result[0].get("scores")
    if hasattr(scores, "tolist"):
        scores = scores.tolist()
    if not isinstance(scores, list) or len(scores) != len(labels):
        raise ValueError("emotion2vec inference returned an invalid score vector")
    numeric = [float(value) for value in scores]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("emotion2vec inference returned non-finite scores")
    winner = max(range(len(numeric)), key=numeric.__getitem__)
    return {
        "predicted_label": labels[winner],
        "predicted_score": numeric[winner],
        "scores": dict(zip(labels, numeric)),
    }


class EmotionEvaluator:
    def __init__(self, model_dir: Path, labels: list[str], device: str, ncpu: int):
        from funasr import AutoModel

        self.labels = labels
        self.model = AutoModel(
            model=str(model_dir),
            device=device,
            ncpu=ncpu,
            batch_size=1,
            disable_update=True,
            log_level="ERROR",
        )

    def score(self, path: Path) -> dict:
        import librosa

        waveform, source_rate = librosa.load(str(path), sr=None, mono=True)
        if source_rate != 16_000:
            waveform = librosa.resample(waveform, orig_sr=source_rate, target_sr=16_000)
        if waveform.size == 0 or not bool(math.isfinite(float(waveform.min())) and math.isfinite(float(waveform.max()))):
            raise ValueError(f"audio decode produced empty or non-finite samples: {path}")
        result = self.model.generate(
            waveform,
            granularity="utterance",
            extract_embedding=False,
            batch_size=1,
            disable_pbar=True,
        )
        return {
            **parse_inference_result(result, self.labels),
            "source_sample_rate_hz": int(source_rate),
            "analysis_sample_rate_hz": 16_000,
            "analysis_sample_count": int(waveform.size),
        }


def runtime_identity(device: str) -> dict:
    import torch

    packages = {}
    for name in ("funasr", "torch", "torchaudio", "librosa", "soundfile", "numpy"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "packages": packages,
        "requested_device": device,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def build(
    args: argparse.Namespace,
    evaluator_factory: Callable[[Path, list[str], str, int], object] = EmotionEvaluator,
) -> dict:
    cv3_root = Path(args.cv3_root).resolve()
    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_binding = bind_model(
        model_dir,
        Path(args.model_intake_manifest).resolve(),
        args.expected_model_intake_manifest_sha256,
    )
    corpus, corpus_binding = parse_cv3_corpus(cv3_root)
    selected = select_records(corpus, args.limit_per_stratum)
    candidate_lineage = bind_candidate_lineage(
        Path(args.candidate_audio),
        args.expected_candidate_sha256,
        Path(args.candidate_packet_manifest),
        args.expected_candidate_packet_sha256,
        Path(args.dialogue_contract),
        args.expected_dialogue_contract_sha256,
    )

    evaluator = evaluator_factory(model_dir, model_binding["labels"], args.device, args.ncpu)
    evaluated = []
    for record in selected:
        audio = Path(record["audio_path"])
        evaluated.append(
            {
                **record,
                "audio_sha256": sha256(audio),
                **evaluator.score(audio),
            }
        )
    metrics = score_metrics(evaluated)

    candidate_result = evaluator.score(Path(args.candidate_audio).resolve())
    target_emotion = candidate_lineage["target_emotion"]
    target_intensity = candidate_lineage["target_intensity"]
    emotion_supported = target_emotion in model_binding["labels"]
    intensity_supported = target_intensity in CV3_INTENSITIES
    candidate_match = candidate_result["predicted_label"] == target_emotion if emotion_supported else None

    result = {
        "schema_version": "1.0",
        "classification": "W64_EMOTION2VEC_EXECUTION_PASS_TAXONOMY_BLOCKED",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "model": model_binding,
        "runtime_identity": runtime_identity(args.device),
        "cv3_corpus": {
            **corpus_binding,
            "total_rows": len(corpus),
            "evaluated_rows": len(evaluated),
            "limit_per_stratum": args.limit_per_stratum,
            "reference_labels": CV3_REFERENCE_LABELS,
            "intensities": CV3_INTENSITIES,
            "languages": CV3_LANGUAGES,
        },
        "calibration": {
            "metrics": metrics,
            "records": evaluated,
            "execution_pass": True,
            "registered_acceptance_threshold_present": False,
            "emotion_authority_pass": False,
        },
        "candidate": {
            "lineage": candidate_lineage,
            **candidate_result,
            "target_emotion_supported": emotion_supported,
            "target_intensity_supported": intensity_supported,
            "target_emotion_match": candidate_match,
            "emotion_pass": None,
            "status": "BLOCKED_EMOTION_TAXONOMY_UNSUPPORTED",
        },
        "gates": {
            "exact_model_identity_pass": True,
            "exact_model_hash_pass": True,
            "model_license_bound_pass": True,
            "cv3_reference_pairing_pass": True,
            "emotion_model_execution_pass": True,
            "registered_calibration_threshold_pass": False,
            "candidate_target_taxonomy_supported_pass": False,
            "candidate_emotion_pass": None,
            "production_emotion_authority_pass": False,
            "row_completion_pass": False,
            "final_voice_certification_pass": False,
        },
        "remaining_blockers": [
            "the dialogue target emotion 'focused' is not in the nine-class emotion2vec taxonomy",
            "the dialogue intensity 'controlled' is not in the CV3 high/low intensity taxonomy",
            "no project acceptance threshold authorizes CV3 emotion metrics for production promotion",
            "independent playback review and production authority remain absent",
        ],
        "boundaries": {
            "candidate_regenerated": False,
            "candidate_media_mutated": False,
            "cv3_gold_labels_used_for_model_input": False,
            "taxonomy_mapping_inferred": False,
            "row_status_changed": False,
            "certification_claimed": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    output = output_dir / "emotion_calibration_manifest.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    return {"manifest_path": str(output), "manifest_sha256": sha256(output), **result}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-intake-manifest", required=True)
    parser.add_argument("--expected-model-intake-manifest-sha256", required=True)
    parser.add_argument("--candidate-audio", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--candidate-packet-manifest", required=True)
    parser.add_argument("--expected-candidate-packet-sha256", required=True)
    parser.add_argument("--dialogue-contract", required=True)
    parser.add_argument("--expected-dialogue-contract-sha256", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--ncpu", type=int, default=4)
    parser.add_argument("--limit-per-stratum", type=int, default=0)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
