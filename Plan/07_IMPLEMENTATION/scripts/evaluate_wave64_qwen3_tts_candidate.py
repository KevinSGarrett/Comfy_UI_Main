#!/usr/bin/env python3
"""Evaluate one immutable Qwen3-TTS candidate without mutating its media."""

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


EXPECTED_ENGINE = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
EXPECTED_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"


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


def verify_lineage(
    manifest: dict[str, Any],
    candidate: Path,
    candidate_sha256: str,
    runner: Path,
    runner_sha256: str,
    plan: Path,
    plan_sha256: str,
) -> tuple[str, float, float]:
    if manifest.get("classification") != "QWEN3_TTS_GENUINE_CANDIDATE_GENERATED_AUTOMATED_QA_PENDING":
        raise EvaluationError("candidate manifest classification is invalid")
    if manifest.get("candidate_id") != "W64-QWEN3-VOICE-DESIGN-SEED-12345":
        raise EvaluationError("candidate manifest is not the authorized immutable seed")
    engine = manifest.get("engine")
    output = manifest.get("output")
    request = manifest.get("request")
    boundaries = manifest.get("boundaries")
    plan_binding = manifest.get("plan")
    if not all(isinstance(value, dict) for value in (engine, output, request, boundaries, plan_binding)):
        raise EvaluationError("candidate manifest is structurally incomplete")
    if engine.get("repository") != EXPECTED_ENGINE or engine.get("revision") != EXPECTED_REVISION:
        raise EvaluationError("candidate manifest engine identity is invalid")
    if Path(str(output.get("path", ""))).resolve() != candidate.resolve():
        raise EvaluationError("candidate manifest path binding is invalid")
    if output.get("sha256") != candidate_sha256:
        raise EvaluationError("candidate manifest SHA-256 binding is invalid")
    if plan_binding.get("sha256") != plan_sha256:
        raise EvaluationError("candidate manifest plan binding is invalid")
    if boundaries.get("automated_qa_complete") is not False:
        raise EvaluationError("candidate manifest improperly claims automated QA")
    if boundaries.get("playback_review_complete") is not False or boundaries.get("production_ready") is not False:
        raise EvaluationError("candidate manifest improperly claims review or production readiness")
    if boundaries.get("rejected_candidate_rerun") is not False:
        raise EvaluationError("candidate manifest indicates a rejected-candidate rerun")
    if request.get("seed") != 12345:
        raise EvaluationError("candidate manifest seed is invalid")
    if sha256_file(runner) != runner_sha256:
        raise EvaluationError("runner changed during lineage validation")
    plan_value = json.loads(plan.read_text(encoding="utf-8-sig"))
    expected_text = str(plan_value.get("normalization", {}).get("normalized_text", "")).strip()
    target_seconds = float(plan_value.get("duration", {}).get("target_seconds", 0.0))
    tolerance_seconds = float(plan_value.get("duration", {}).get("tolerance_seconds", -1.0))
    if request.get("text") != expected_text or not expected_text:
        raise EvaluationError("candidate text does not match the synthesis plan")
    if target_seconds <= 0 or tolerance_seconds < 0:
        raise EvaluationError("synthesis plan timing contract is invalid")
    return expected_text, target_seconds, tolerance_seconds


def inspect_audio(path: Path) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or rate <= 0 or not np.isfinite(audio).all():
        raise EvaluationError("candidate audio is empty, non-finite, or has an invalid sample rate")
    peak = float(np.max(np.abs(audio)))
    clipping_ratio = float(np.mean(np.abs(audio) >= 0.999))
    silence_ratio = float(np.mean(np.abs(audio) < 1e-4))
    rms = float(np.sqrt(np.mean(np.square(audio))))
    return {
        "sample_rate_hz": int(rate),
        "samples": int(audio.shape[0]),
        "channels": int(audio.shape[1]),
        "duration_seconds": round(audio.shape[0] / rate, 9),
        "peak_absolute": round(peak, 9),
        "rms": round(rms, 9),
        "clipping_ratio": round(clipping_ratio, 9),
        "silence_ratio": round(silence_ratio, 9),
        "finite": True,
    }


def classify(gates: dict[str, Any]) -> str:
    if gates["technical_audio_pass"] is not True:
        return "FAIL_QWEN3_TTS_TECHNICAL_AUDIO"
    if gates["dialogue_timing_pass"] is not True:
        return "FAIL_QWEN3_TTS_DIALOGUE_TIMING"
    if gates["candidate_asr_pass"] is not True:
        return "FAIL_QWEN3_TTS_DIALOGUE_INTELLIGIBILITY"
    return "PASS_QWEN3_TTS_AUTOMATED_QA_PLAYBACK_AND_AUTHORITY_PENDING"


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    candidate = Path(args.candidate_audio).resolve()
    candidate_binding = bind(candidate, args.expected_candidate_sha256, "Qwen candidate")
    manifest_binding, manifest = load_json(
        Path(args.candidate_manifest), args.expected_candidate_manifest_sha256, "Qwen candidate manifest"
    )
    runner = Path(args.runner_script).resolve()
    runner_binding = bind(runner, args.expected_runner_sha256, "Qwen candidate runner")
    plan = Path(args.plan).resolve()
    plan_binding = bind(plan, args.expected_plan_sha256, "dialogue synthesis plan")
    cv3_binding, cv3_evidence = load_json(
        Path(args.cv3_evidence), args.expected_cv3_evidence_sha256, "CV3 calibration evidence"
    )
    adapter = Path(args.cv3_adapter_script).resolve()
    adapter_binding = bind(adapter, args.expected_cv3_adapter_sha256, "CV3 calibration adapter")
    expected_text, target_seconds, tolerance_seconds = verify_lineage(
        manifest,
        candidate,
        candidate_binding["sha256"],
        runner,
        runner_binding["sha256"],
        plan,
        plan_binding["sha256"],
    )
    technical = inspect_audio(candidate)
    source = cv3_evidence.get("source_authority")
    if (
        not isinstance(source, dict)
        or cv3_evidence.get("acceptance", {}).get("candidate_asr_threshold_pass") is not True
    ):
        raise EvaluationError("CV3 calibration evidence is not deployable for ASR")
    whisper_path = Path(source.get("whisper", {}).get("path", "")).resolve()
    if not whisper_path.is_file() or sha256_file(whisper_path) != source["whisper"]["sha256"]:
        raise EvaluationError("CV3 Whisper authority binding is invalid")
    cv3_module = load_module(adapter, "wave64_cv3_eval_for_qwen")
    whisper = cv3_module.WhisperEvaluator(
        whisper_path.parent,
        Path(args.transformers_overlay).resolve(),
        args.device,
    )
    transcript = whisper.transcribe(candidate)
    wer = float(cv3_module.normalized_wer(expected_text, transcript))
    timing_delta = abs(float(technical["duration_seconds"]) - target_seconds)
    gates = {
        "technical_audio_pass": (
            technical["channels"] == 1
            and technical["sample_rate_hz"] >= 16_000
            and technical["clipping_ratio"] <= args.max_clipping_ratio
            and technical["silence_ratio"] < args.max_silence_ratio
        ),
        "dialogue_timing_pass": timing_delta <= tolerance_seconds,
        "candidate_asr_pass": wer <= args.max_wer,
        "speaker_identity_pass": None,
        "emotion_class_pass": None,
        "delivery_style_pass": None,
        "intensity_pass": None,
        "independent_playback_review_pass": False,
        "production_proof_authority_pass": False,
        "row_complete": False,
        "final_voice_certification_pass": False,
    }
    classification = classify(gates)
    blockers = [
        "speaker identity is not measurable for a VoiceDesign candidate without an approved C01 reference authority",
        "emotion, focused delivery style, and controlled intensity require perceptual playback review",
        "independent playback review and final production authority remain pending",
        "Row123 requires a bounded multi-engine candidate set; this record evaluates one immutable Qwen candidate only",
    ]
    if not gates["technical_audio_pass"]:
        blockers.insert(0, "candidate technical audio failed the finite/channel/rate/clipping/silence gate")
    if not gates["dialogue_timing_pass"]:
        blockers.insert(0, f"raw duration differs from {target_seconds:.3f} seconds by {timing_delta:.6f} seconds")
    if not gates["candidate_asr_pass"]:
        blockers.insert(0, f"normalized Whisper WER {wer:.6f} exceeds {args.max_wer:.6f}")
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_candidate_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": classification,
        "classification": classification,
        "bindings": {
            "candidate": candidate_binding,
            "candidate_manifest": manifest_binding,
            "runner": runner_binding,
            "synthesis_plan": plan_binding,
            "cv3_evidence": cv3_binding,
            "cv3_adapter": adapter_binding,
            "whisper_model": source["whisper"],
        },
        "candidate": {
            "candidate_id": manifest["candidate_id"],
            "expected_text": expected_text,
            "asr_transcript": transcript,
            "normalized_wer": round(wer, 6),
            "wer_threshold": args.max_wer,
            "technical_audio": technical,
            "target_duration_seconds": target_seconds,
            "duration_tolerance_seconds": tolerance_seconds,
            "duration_delta_seconds": round(timing_delta, 9),
            "media_mutated": False,
            "spoken_content_trimmed": False,
            "time_stretched": False,
        },
        "gates": gates,
        "remaining_blockers": blockers,
        "boundaries": {
            "candidate_regenerated": False,
            "candidate_media_mutated": False,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
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
    parser.add_argument("--expected-candidate-manifest-sha256", required=True)
    parser.add_argument("--runner-script", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--cv3-evidence", required=True)
    parser.add_argument("--expected-cv3-evidence-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--transformers-overlay", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--max-clipping-ratio", type=float, default=0.0001)
    parser.add_argument("--max-silence-ratio", type=float, default=0.995)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = evaluate(args)
        write_json_new(args.output.resolve(), value)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"classification": value["classification"], "candidate": value["candidate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
