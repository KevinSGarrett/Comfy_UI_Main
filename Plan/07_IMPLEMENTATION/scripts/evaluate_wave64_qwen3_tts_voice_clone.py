#!/usr/bin/env python3
"""Evaluate one immutable Qwen3-TTS Base clone with calibrated local metrics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_ENGINE = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
EXPECTED_REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"
EXPECTED_CANDIDATE_ID = "W64-QWEN3-BASE-ICL-CLONE-SEED-12401"
EXPECTED_REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
EXPECTED_TEXT = "We hold the frame steady and move on the beat."
EXPECTED_REFERENCE_TEXT = "Once upon a midnight dreary, while I pondered, weak and weary."


class EvaluationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise EvaluationError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected_sha256.lower():
        raise EvaluationError(f"{label} SHA-256 mismatch: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def load_json(path: Path, expected_sha256: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = bind(path, expected_sha256, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} root must be an object")
    return binding, value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise EvaluationError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_lineage(manifest: dict[str, Any], candidate: Path, candidate_sha256: str) -> Path:
    if manifest.get("classification") != "QWEN3_TTS_BASE_ICL_CLONE_GENERATED_AUTOMATED_QA_PENDING":
        raise EvaluationError("clone manifest classification is invalid")
    if manifest.get("candidate_id") != EXPECTED_CANDIDATE_ID:
        raise EvaluationError("clone manifest is not the authorized immutable seed")
    engine = manifest.get("engine")
    request = manifest.get("request")
    reference = manifest.get("reference")
    output = manifest.get("output")
    boundaries = manifest.get("boundaries")
    if not all(isinstance(value, dict) for value in (engine, request, reference, output, boundaries)):
        raise EvaluationError("clone manifest is structurally incomplete")
    if engine.get("repository") != EXPECTED_ENGINE or engine.get("revision") != EXPECTED_REVISION:
        raise EvaluationError("clone engine identity is invalid")
    if request.get("text") != EXPECTED_TEXT or request.get("seed") != 12401:
        raise EvaluationError("clone request text or seed is invalid")
    if request.get("clone_mode") != "icl" or request.get("x_vector_only_mode") is not False:
        raise EvaluationError("clone did not use the authorized ICL mode")
    if reference.get("sha256") != EXPECTED_REFERENCE_SHA256 or reference.get("transcript") != EXPECTED_REFERENCE_TEXT:
        raise EvaluationError("clone reference binding is invalid")
    reference_path = Path(str(reference.get("path", ""))).resolve()
    bind(reference_path, EXPECTED_REFERENCE_SHA256, "clone reference audio")
    if reference.get("production_authorized") is not False:
        raise EvaluationError("reference incorrectly claims production authorization")
    if Path(str(output.get("path", ""))).resolve() != candidate.resolve() or output.get("sha256") != candidate_sha256:
        raise EvaluationError("clone output binding is invalid")
    if output.get("sha256") == reference.get("sha256"):
        raise EvaluationError("clone output duplicates reference audio")
    if boundaries.get("automated_qa_complete") is not False or boundaries.get("production_ready") is not False:
        raise EvaluationError("clone manifest improperly claims QA or production readiness")
    return reference_path


def inspect_audio(path: Path) -> tuple[dict[str, Any], Any, int]:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or rate <= 0 or not np.isfinite(audio).all():
        raise EvaluationError("candidate audio is empty, non-finite, or has an invalid sample rate")
    mono = audio.mean(axis=1)
    result = {
        "sample_rate_hz": int(rate),
        "samples": int(audio.shape[0]),
        "channels": int(audio.shape[1]),
        "duration_seconds": round(audio.shape[0] / rate, 9),
        "peak_absolute": round(float(np.max(np.abs(audio))), 9),
        "rms": round(float(np.sqrt(np.mean(np.square(audio)))), 9),
        "clipping_ratio": round(float(np.mean(np.abs(audio) >= 0.999)), 9),
        "silence_ratio": round(float(np.mean(np.abs(audio) < 1e-4)), 9),
        "finite": True,
    }
    return result, mono, int(rate)


def measure_prosody(audio, sample_rate: int, word_count: int) -> dict[str, Any]:
    import librosa
    import numpy as np

    duration = audio.size / sample_rate
    hop = 256
    frame = 2048
    rms = librosa.feature.rms(y=audio, frame_length=frame, hop_length=hop, center=True)[0]
    threshold = max(0.003, float(np.max(rms)) * 0.08)
    active = rms >= threshold
    f0 = librosa.yin(audio, fmin=65.0, fmax=500.0, sr=sample_rate, frame_length=frame, hop_length=hop)
    usable = f0[: active.size][active[: f0.size]]
    usable = usable[np.isfinite(usable)]
    pauses = []
    start = None
    for index, is_active in enumerate(active):
        if not is_active and start is None:
            start = index
        if is_active and start is not None:
            seconds = (index - start) * hop / sample_rate
            if seconds >= 0.12:
                pauses.append(seconds)
            start = None
    if start is not None:
        seconds = (active.size - start) * hop / sample_rate
        if seconds >= 0.12:
            pauses.append(seconds)
    pause_seconds = min(duration, sum(pauses))
    active_seconds = max(1e-6, duration - pause_seconds)
    return {
        "method": "librosa_yin_rms_pause_v1",
        "duration_seconds": round(duration, 6),
        "word_count": int(word_count),
        "pace_wpm_raw_duration": round(word_count * 60.0 / duration, 3),
        "articulation_rate_wpm_active_audio": round(word_count * 60.0 / active_seconds, 3),
        "pitch_median_hz": round(float(np.median(usable)), 3) if usable.size else None,
        "pitch_p10_hz": round(float(np.percentile(usable, 10)), 3) if usable.size else None,
        "pitch_p90_hz": round(float(np.percentile(usable, 90)), 3) if usable.size else None,
        "voiced_frame_ratio": round(float(usable.size / max(1, active.size)), 6),
        "pause_count_ge_120ms": len(pauses),
        "pause_seconds_total": round(pause_seconds, 6),
        "longest_pause_seconds": round(max(pauses, default=0.0), 6),
        "delivery_style_inferred": False,
        "intensity_class_inferred": False,
        "emotion_class_inferred": False,
    }


def classify(gates: dict[str, Any]) -> str:
    if not gates["technical_audio_pass"]:
        return "FAIL_QWEN3_CLONE_TECHNICAL_AUDIO"
    if not gates["candidate_asr_pass"]:
        return "FAIL_QWEN3_CLONE_INTELLIGIBILITY"
    if not gates["chain_specific_speaker_identity_pass"]:
        return "FAIL_QWEN3_CLONE_SPEAKER_IDENTITY"
    return "PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED"


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    candidate = Path(args.candidate_audio).resolve()
    candidate_binding = bind(candidate, args.expected_candidate_sha256, "clone candidate")
    manifest_binding, manifest = load_json(Path(args.candidate_manifest), args.expected_manifest_sha256, "clone manifest")
    runner_binding = bind(Path(args.runner_script), args.expected_runner_sha256, "clone runner")
    reference = verify_lineage(manifest, candidate, candidate_binding["sha256"])
    adapter = Path(args.cv3_adapter_script).resolve()
    adapter_binding = bind(adapter, args.expected_cv3_adapter_sha256, "CV3 adapter")
    threshold_binding, threshold_evidence = load_json(
        Path(args.speaker_threshold_evidence), args.expected_speaker_threshold_evidence_sha256, "speaker threshold evidence"
    )
    threshold_data = threshold_evidence.get("threshold_validation", {})
    threshold = float(threshold_data.get("threshold", math.nan))
    if not math.isfinite(threshold) or threshold_data.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise EvaluationError("speaker threshold is not deployable for chain-specific evaluation")

    cv3 = load_module(adapter, "wave64_cv3_eval_for_clone")
    cv3_root = Path(args.cv3_root).resolve()
    whisper_dir = Path(args.whisper_model_dir).resolve()
    cv3.require_hash(whisper_dir / "model.safetensors", cv3.WHISPER_SHA256, "Whisper weight")
    checkpoint = cv3_root / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    cv3.require_hash(checkpoint, cv3.ERES2NET_SHA256, "ERes2Net checkpoint")
    whisper = cv3.WhisperEvaluator(whisper_dir, Path(args.transformers_overlay).resolve(), args.device)
    speaker = cv3.SpeakerEvaluator(cv3_root / "utils/3D-Speaker", checkpoint, args.device)
    transcript = whisper.transcribe(candidate)
    wer = float(cv3.normalized_wer(EXPECTED_TEXT, transcript))
    similarity = speaker.similarity(speaker.embedding(reference), speaker.embedding(candidate))
    technical, audio, rate = inspect_audio(candidate)
    prosody = measure_prosody(audio, rate, len(cv3.normalized_tokens(EXPECTED_TEXT)))
    timing_delta = abs(technical["duration_seconds"] - args.target_duration_seconds)
    gates = {
        "technical_audio_pass": technical["channels"] == 1 and technical["sample_rate_hz"] >= 16000 and technical["clipping_ratio"] <= args.max_clipping_ratio and technical["silence_ratio"] < args.max_silence_ratio,
        "candidate_asr_pass": wer <= args.max_wer,
        "chain_specific_speaker_identity_pass": similarity >= threshold,
        "raw_dialogue_timing_pass": timing_delta <= args.duration_tolerance_seconds,
        "prosody_measurement_complete": prosody["pitch_median_hz"] is not None,
        "emotion_class_pass": None,
        "delivery_style_pass": None,
        "intensity_pass": None,
        "independent_playback_review_pass": False,
        "production_reference_authority_pass": False,
        "final_voice_certification_pass": False,
        "row_complete": False,
    }
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_base_icl_clone_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": classify(gates),
        "classification": classify(gates),
        "bindings": {"candidate": candidate_binding, "candidate_manifest": manifest_binding, "runner": runner_binding, "cv3_adapter": adapter_binding, "speaker_threshold_evidence": threshold_binding},
        "candidate": {
            "candidate_id": manifest["candidate_id"],
            "expected_text": EXPECTED_TEXT,
            "asr_transcript": transcript,
            "normalized_wer": round(wer, 6),
            "speaker_similarity": round(similarity, 9),
            "speaker_similarity_threshold": threshold,
            "technical_audio": technical,
            "target_duration_seconds": args.target_duration_seconds,
            "duration_tolerance_seconds": args.duration_tolerance_seconds,
            "duration_delta_seconds": round(timing_delta, 9),
            "prosody": prosody,
            "media_mutated": False,
        },
        "gates": gates,
        "remaining_blockers": [
            "the public-domain reference is approved for chain-specific evaluation but is not a locked production character identity authority",
            "focused delivery style and controlled intensity remain separate unmeasured controls and are not emotion2vec aliases",
            "independent full-play listening review and final production authority remain pending",
        ] + ([] if gates["raw_dialogue_timing_pass"] else ["raw candidate duration is outside the 3.000 second plus-or-minus 0.080 second timing gate"]),
        "boundaries": {"candidate_regenerated": False, "candidate_media_mutated": False, "subjective_review_fabricated": False, "production_promotion_claimed": False, "content_based_suppression": False, "aws_or_ec2_used": False, "mask_or_wave71_touched": False},
    }


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise EvaluationError(f"immutable evaluation already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-audio", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--runner-script", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--speaker-threshold-evidence", required=True)
    parser.add_argument("--expected-speaker-threshold-evidence-sha256", required=True)
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--whisper-model-dir", required=True)
    parser.add_argument("--transformers-overlay", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--max-clipping-ratio", type=float, default=0.0001)
    parser.add_argument("--max-silence-ratio", type=float, default=0.995)
    parser.add_argument("--target-duration-seconds", type=float, default=3.0)
    parser.add_argument("--duration-tolerance-seconds", type=float, default=0.08)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = evaluate(args)
        write_json_new(args.output.resolve(), value)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"classification": value["classification"], "candidate": value["candidate"], "gates": value["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
