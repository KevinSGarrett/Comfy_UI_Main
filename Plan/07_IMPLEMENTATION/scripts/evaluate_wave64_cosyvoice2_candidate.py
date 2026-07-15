#!/usr/bin/env python3
"""Evaluate one hash-bound CosyVoice2 candidate with existing Wave64 authorities."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path, expected_sha256: str, label: str) -> dict:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != expected_sha256.lower():
        raise ValueError(f"{label} SHA-256 mismatch: {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def load_json(path: Path, expected_sha256: str, label: str) -> tuple[dict, dict]:
    record = binding(path, expected_sha256, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return record, payload


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load implementation module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_candidate_lineage(
    manifest: dict,
    candidate: Path,
    candidate_sha256: str,
) -> tuple[Path, str, str, str]:
    if manifest.get("engine") != "CosyVoice2":
        raise ValueError("runtime manifest engine is not CosyVoice2")
    output = manifest.get("output")
    reference = manifest.get("reference_speaker")
    dialogue = manifest.get("dialogue")
    gates = manifest.get("gates")
    boundaries = manifest.get("boundaries")
    if not all(isinstance(value, dict) for value in (output, reference, dialogue, gates, boundaries)):
        raise ValueError("runtime manifest is structurally incomplete")
    if Path(str(output.get("path", ""))).resolve() != candidate.resolve():
        raise ValueError("runtime manifest does not bind the candidate path")
    if str(output.get("sha256", "")).lower() != candidate_sha256.lower():
        raise ValueError("runtime manifest does not bind the candidate SHA-256")
    reference_path = Path(str(reference.get("path", ""))).resolve()
    reference_hash = str(reference.get("sha256", "")).lower()
    if not reference_path.is_file() or sha256(reference_path) != reference_hash:
        raise ValueError("runtime manifest reference-speaker binding is invalid")
    if gates.get("independent_reference_speaker_bound") is not True:
        raise ValueError("runtime manifest does not assert the source binding")
    if boundaries.get("final_voice_certification_claimed") is not False:
        raise ValueError("runtime manifest improperly claims final certification")
    text = str(dialogue.get("text", "")).strip()
    emotion = str(dialogue.get("style_emotion_required", "")).strip().lower()
    intensity = str(dialogue.get("style_intensity_required", "")).strip().lower()
    if not text or not emotion or not intensity:
        raise ValueError("runtime manifest dialogue contract is incomplete")
    return reference_path, text, emotion, intensity


def classify(gates: dict) -> str:
    if gates["dialogue_timing_pass"] is not True:
        return "FAIL_COSYVOICE2_DIALOGUE_TIMING"
    if gates["candidate_asr_pass"] is not True:
        return "FAIL_COSYVOICE2_DIALOGUE_INTELLIGIBILITY"
    if gates["candidate_reference_speaker_identity_pass"] is not True:
        return "FAIL_COSYVOICE2_REFERENCE_SPEAKER_IDENTITY"
    if gates["candidate_dnsmos_worst_reference_floor_pass"] is not True:
        return "FAIL_COSYVOICE2_DNSMOS_WORST_REFERENCE_FLOOR"
    return "PASS_COSYVOICE2_CONTENT_SPEAKER_TECHNICAL_STYLE_AUTHORITY_BLOCKED"


def require_deployable_speaker_threshold(openslr_evidence: dict) -> float:
    threshold = openslr_evidence.get("threshold_validation", {}).get("threshold")
    if (
        openslr_evidence.get("acceptance", {}).get(
            "speaker_disjoint_threshold_generalization_pass"
        )
        is not True
        or not isinstance(threshold, (int, float))
    ):
        raise ValueError("OpenSLR31 threshold is not deployable for chain-specific evaluation")
    return float(threshold)


def build_metric_gates(
    *,
    wer: float,
    max_wer: float,
    similarity: float,
    threshold: float,
    dnsmos_ovrl: float,
    reference_mos: list[float],
    timing_pass: bool,
    target_emotion: str,
    emotion_labels: list[str],
) -> dict:
    if not reference_mos:
        raise ValueError("DNSMOS reference calibration is empty")
    return {
        "candidate_asr_pass": wer <= max_wer,
        "candidate_reference_speaker_identity_pass": similarity >= threshold,
        "candidate_dnsmos_worst_reference_floor_pass": dnsmos_ovrl >= min(reference_mos),
        "candidate_dnsmos_quality_certification_pass": None,
        "dialogue_timing_pass": timing_pass,
        "target_emotion_taxonomy_supported": target_emotion in emotion_labels,
        "target_intensity_taxonomy_supported": None,
        "target_intensity_taxonomy_status": "unmeasured_no_calibrated_intensity_evaluator",
        "candidate_emotion_pass": None,
        "candidate_style_intensity_pass": None,
        "independent_playback_review_pass": False,
        "production_proof_authority_pass": False,
        "row_complete": False,
        "final_voice_certification_pass": False,
    }


def timing_blocker(duration_seconds: float, expected_duration_seconds: float) -> str:
    return (
        f"the {duration_seconds}-second zero-shot candidate exceeds the "
        f"{expected_duration_seconds}-second dialogue contract"
    )


def build(args: argparse.Namespace) -> dict:
    candidate = Path(args.candidate_audio).resolve()
    candidate_binding = binding(candidate, args.expected_candidate_sha256, "CosyVoice2 candidate")
    manifest_binding, manifest = load_json(
        Path(args.candidate_manifest), args.expected_candidate_manifest_sha256, "CosyVoice2 runtime manifest"
    )
    reference_path, expected_text, target_emotion, target_intensity = verify_candidate_lineage(
        manifest, candidate, candidate_binding["sha256"]
    )
    cv3_binding, cv3_evidence = load_json(
        Path(args.cv3_evidence), args.expected_cv3_evidence_sha256, "CV3 calibration evidence"
    )
    openslr_binding, openslr_evidence = load_json(
        Path(args.openslr_evidence),
        args.expected_openslr_evidence_sha256,
        "OpenSLR31 threshold evidence",
    )
    emotion_binding, emotion_evidence = load_json(
        Path(args.emotion_evidence),
        args.expected_emotion_evidence_sha256,
        "emotion2vec calibration evidence",
    )
    cv3_adapter_binding = binding(
        Path(args.cv3_adapter_script), args.expected_cv3_adapter_sha256, "CV3 adapter"
    )
    emotion_adapter_binding = binding(
        Path(args.emotion_adapter_script), args.expected_emotion_adapter_sha256, "emotion adapter"
    )
    threshold = require_deployable_speaker_threshold(openslr_evidence)

    cv3_module = load_module(Path(args.cv3_adapter_script), "wave64_cv3_eval_for_cosyvoice2")
    source = cv3_evidence.get("source_authority")
    calibration = cv3_evidence.get("calibration")
    if not isinstance(source, dict) or not isinstance(calibration, dict):
        raise ValueError("CV3 evidence is structurally incomplete")
    whisper_dir = Path(source["whisper"]["path"]).resolve().parent
    cv3_root = Path(source["license_binding"]["path"]).resolve().parent
    speaker_root = cv3_root / "utils/3D-Speaker"
    checkpoint = Path(source["speaker_checkpoint"]["path"]).resolve()
    dnsmos_source = Path(source["dnsmos_source"]["path"]).resolve()
    dnsmos_dir = Path(source["dnsmos_models"]["sig_bak_ovr.onnx"]["path"]).resolve().parent
    whisper = cv3_module.WhisperEvaluator(
        whisper_dir, Path(args.transformers_overlay).resolve(), args.device
    )
    speaker = cv3_module.SpeakerEvaluator(speaker_root, checkpoint, args.device)
    dnsmos = cv3_module.DNSMOSEvaluator(dnsmos_source, dnsmos_dir)
    transcript = whisper.transcribe(candidate)
    wer = cv3_module.normalized_wer(expected_text, transcript)
    candidate_embedding = speaker.embedding(candidate)
    reference_embedding = speaker.embedding(reference_path)
    similarity = speaker.similarity(candidate_embedding, reference_embedding)
    dnsmos_result = dnsmos.score(candidate)
    reference_mos = [float(row["dnsmos"]["OVRL"]) for row in calibration["samples"]]
    dnsmos_percentile = cv3_module.percentile_rank(reference_mos, dnsmos_result["OVRL"])

    emotion_module = load_module(Path(args.emotion_adapter_script), "wave64_emotion_for_cosyvoice2")
    emotion_source = emotion_evidence.get("source_authority")
    emotion_artifacts = emotion_evidence.get("artifact_bindings")
    if not isinstance(emotion_source, dict) or not isinstance(emotion_artifacts, dict):
        raise ValueError("emotion evidence is structurally incomplete")
    model_dir = Path(emotion_source["model_files"]["model.pt"]["path"]).resolve().parent
    intake = emotion_artifacts["durable_model_intake_manifest"]
    emotion_model_binding = emotion_module.bind_model(
        model_dir, Path(intake["path"]), intake["sha256"]
    )
    labels = emotion_module.read_model_labels(model_dir / "tokens.txt")
    emotion_evaluator = emotion_module.EmotionEvaluator(model_dir, labels, args.device, args.ncpu)
    emotion_result = emotion_evaluator.score(candidate)

    timing_pass = manifest["gates"].get("dialogue_timing_pass") is True
    gates = build_metric_gates(
        wer=wer,
        max_wer=args.max_wer,
        similarity=similarity,
        threshold=threshold,
        dnsmos_ovrl=dnsmos_result["OVRL"],
        reference_mos=reference_mos,
        timing_pass=timing_pass,
        target_emotion=target_emotion,
        emotion_labels=labels,
    )
    classification = classify(gates)
    duration_seconds = manifest["output"]["pcm"]["duration_seconds"]
    expected_duration_seconds = manifest["dialogue"]["expected_duration_seconds"]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_cosyvoice2_candidate_evaluation",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": classification,
        "classification": classification,
        "bindings": {
            "candidate": candidate_binding,
            "candidate_manifest": manifest_binding,
            "reference_speaker": {
                "path": str(reference_path),
                "sha256": manifest["reference_speaker"]["sha256"],
                "bytes": reference_path.stat().st_size,
            },
            "cv3_evidence": cv3_binding,
            "openslr31_evidence": openslr_binding,
            "emotion_evidence": emotion_binding,
            "cv3_adapter": cv3_adapter_binding,
            "emotion_adapter": emotion_adapter_binding,
            "emotion_model": emotion_model_binding,
        },
        "candidate": {
            "expected_text": expected_text,
            "asr_transcript": transcript,
            "normalized_wer": wer,
            "wer_threshold": args.max_wer,
            "speaker_similarity": similarity,
            "validated_speaker_threshold": threshold,
            "dnsmos": dnsmos_result,
            "dnsmos_reference_percentile": dnsmos_percentile,
            "predicted_emotion": emotion_result,
            "target_emotion": target_emotion,
            "target_intensity": target_intensity,
            "duration_seconds": duration_seconds,
            "expected_duration_seconds": expected_duration_seconds,
        },
        "gates": gates,
        "remaining_blockers": [
            timing_blocker(duration_seconds, expected_duration_seconds),
            "focused remains outside the calibrated emotion taxonomy",
            "controlled intensity is unmeasured because no calibrated intensity evaluator is registered",
            "independent playback and production-review authority remain absent",
        ],
        "boundaries": {
            "calibration_corpora_rerun": False,
            "candidate_regenerated": False,
            "candidate_media_mutated": False,
            "production_promotion_claimed": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-audio", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--expected-candidate-manifest-sha256", required=True)
    parser.add_argument("--cv3-evidence", required=True)
    parser.add_argument("--expected-cv3-evidence-sha256", required=True)
    parser.add_argument("--openslr-evidence", required=True)
    parser.add_argument("--expected-openslr-evidence-sha256", required=True)
    parser.add_argument("--emotion-evidence", required=True)
    parser.add_argument("--expected-emotion-evidence-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--emotion-adapter-script", required=True)
    parser.add_argument("--expected-emotion-adapter-sha256", required=True)
    parser.add_argument("--transformers-overlay", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--ncpu", type=int, default=4)
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        print(f"ERROR: output directory already exists: {output_dir}")
        return 2
    try:
        payload = build(args)
        output_dir.mkdir(parents=True)
        (output_dir / "cosyvoice2_candidate_evaluation.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": payload["status"], "candidate": payload["candidate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
