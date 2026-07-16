#!/usr/bin/env python3
"""Evaluate the immutable Qwen3-TTS continuity matrix for Wave64 Rows131-133."""

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


EXPECTED_CLASSIFICATION = "QWEN3_TTS_CONTINUITY_MATRIX_GENERATED_AUTOMATED_QA_PENDING"
EXPECTED_REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
EXPECTED_BASELINE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
CALIBRATION_IDS = {"L01", "L02", "L03", "L04", "L08"}
HELD_OUT_IDS = {"L05", "L06", "L07", "L09", "L10"}


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


def verify_manifest(manifest: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    if manifest.get("classification") != EXPECTED_CLASSIFICATION:
        raise EvaluationError("continuity manifest classification is invalid")
    reference = manifest.get("reference")
    baseline = manifest.get("baseline")
    new_lines = manifest.get("new_lines")
    contract = manifest.get("matrix_contract")
    boundaries = manifest.get("boundaries")
    if not isinstance(reference, dict) or not isinstance(baseline, dict) or not isinstance(new_lines, list):
        raise EvaluationError("continuity manifest is structurally incomplete")
    if not isinstance(contract, dict) or not isinstance(boundaries, dict):
        raise EvaluationError("continuity contract or boundaries are missing")
    if reference.get("sha256") != EXPECTED_REFERENCE_SHA256 or reference.get("production_authorized") is not False:
        raise EvaluationError("reference identity or production boundary is invalid")
    reference_path = Path(str(reference.get("path", ""))).resolve()
    bind(reference_path, EXPECTED_REFERENCE_SHA256, "reference audio")
    if baseline.get("sha256") != EXPECTED_BASELINE_SHA256 or baseline.get("line_id") != "L01":
        raise EvaluationError("baseline binding is invalid")
    records = [{**baseline, "output": {"path": baseline.get("path"), "sha256": baseline.get("sha256"), "bytes": baseline.get("bytes")}}]
    records.extend(new_lines)
    line_ids = {record.get("line_id") for record in records}
    if len(records) != 10 or line_ids != {f"L{index:02d}" for index in range(1, 11)}:
        raise EvaluationError("continuity matrix must contain exactly L01-L10")
    if {record.get("scene_id") for record in records} != {"SCENE-A", "SCENE-B", "SCENE-C"}:
        raise EvaluationError("continuity matrix must contain exactly three scenes")
    if contract.get("calibration_line_ids") != ["L01", "L02", "L03", "L04", "L08"]:
        raise EvaluationError("calibration partition drift")
    if contract.get("held_out_line_ids") != ["L05", "L06", "L07", "L09", "L10"]:
        raise EvaluationError("held-out partition drift")
    required_false = (
        "production_character_authority",
        "multilingual_content_qa_complete",
        "accent_qa_complete",
        "independent_playback_review_complete",
        "production_ready",
    )
    if any(boundaries.get(key) is not False for key in required_false):
        raise EvaluationError("continuity manifest improperly claims production authority")
    return reference_path, records


def summarize_partition(line_metrics: list[dict[str, Any]], ids: set[str], threshold: float) -> dict[str, Any]:
    selected = [line for line in line_metrics if line["line_id"] in ids]
    failures = [line["line_id"] for line in selected if line["speaker_similarity_to_reference"] < threshold]
    return {
        "line_ids": [line["line_id"] for line in selected],
        "sample_count": len(selected),
        "reference_similarity_min": round(min(line["speaker_similarity_to_reference"] for line in selected), 9),
        "reference_similarity_mean": round(sum(line["speaker_similarity_to_reference"] for line in selected) / len(selected), 9),
        "false_rejection_count_at_chain_specific_threshold": len(failures),
        "false_rejection_rate_at_chain_specific_threshold": round(len(failures) / len(selected), 9),
        "false_rejection_line_ids": failures,
        "false_acceptance_measured": False,
        "false_acceptance_rate": None,
        "production_calibration_allowed": False,
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_binding, manifest = load_json(args.manifest.resolve(), args.expected_manifest_sha256, "continuity manifest")
    runner_binding = bind(args.runner_script.resolve(), args.expected_runner_sha256, "continuity runner")
    base_evaluator_binding = bind(args.base_evaluator_script.resolve(), args.expected_base_evaluator_sha256, "base evaluator")
    adapter_binding = bind(args.cv3_adapter_script.resolve(), args.expected_cv3_adapter_sha256, "CV3 adapter")
    threshold_binding, threshold_evidence = load_json(
        args.speaker_threshold_evidence.resolve(), args.expected_speaker_threshold_evidence_sha256, "speaker threshold evidence"
    )
    threshold_data = threshold_evidence.get("threshold_validation", {})
    threshold = float(threshold_data.get("threshold", math.nan))
    if not math.isfinite(threshold) or threshold_data.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise EvaluationError("speaker threshold is not deployable for chain-specific evaluation")
    reference, records = verify_manifest(manifest)
    audio_bindings: dict[str, dict[str, Any]] = {}
    for record in records:
        output = record.get("output")
        if not isinstance(output, dict):
            raise EvaluationError(f"line {record.get('line_id')} output binding is missing")
        audio_bindings[record["line_id"]] = bind(
            Path(str(output.get("path", ""))), str(output.get("sha256", "")), f"line {record['line_id']} audio"
        )

    cv3 = load_module(args.cv3_adapter_script.resolve(), "wave64_cv3_eval_for_continuity")
    base_eval = load_module(args.base_evaluator_script.resolve(), "wave64_qwen_base_evaluator_for_continuity")
    cv3_root = args.cv3_root.resolve()
    whisper_dir = args.whisper_model_dir.resolve()
    cv3.require_hash(whisper_dir / "model.safetensors", cv3.WHISPER_SHA256, "Whisper weight")
    checkpoint = cv3_root / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    cv3.require_hash(checkpoint, cv3.ERES2NET_SHA256, "ERes2Net checkpoint")
    whisper = cv3.WhisperEvaluator(whisper_dir, args.transformers_overlay.resolve(), args.device)
    speaker = cv3.SpeakerEvaluator(cv3_root / "utils/3D-Speaker", checkpoint, args.device)
    reference_embedding = speaker.embedding(reference)
    embeddings: dict[str, Any] = {}
    line_metrics: list[dict[str, Any]] = []
    for record in records:
        line_id = record["line_id"]
        path = Path(audio_bindings[line_id]["path"])
        embedding = speaker.embedding(path)
        embeddings[line_id] = embedding
        technical, audio, rate = base_eval.inspect_audio(path)
        text = str(record.get("text", ""))
        language_role = record.get("language_role")
        transcript = whisper.transcribe(path) if language_role == "english" else None
        wer = float(cv3.normalized_wer(text, transcript)) if transcript is not None else None
        line_metrics.append({
            "line_id": line_id,
            "scene_id": record.get("scene_id"),
            "language": record.get("language"),
            "language_role": language_role,
            "expected_text": text,
            "asr_transcript": transcript,
            "normalized_wer": round(wer, 6) if wer is not None else None,
            "multilingual_content_evaluation_status": "NOT_EVALUATED_ENGLISH_ONLY_WHISPER" if transcript is None else "ENGLISH_ASR_EVALUATED",
            "speaker_similarity_to_reference": round(speaker.similarity(reference_embedding, embedding), 9),
            "technical_audio": technical,
            "prosody": base_eval.measure_prosody(audio, rate, len(cv3.normalized_tokens(text))),
            "audio_binding": audio_bindings[line_id],
        })

    pairwise = []
    for left_index, left in enumerate(records):
        for right in records[left_index + 1:]:
            pairwise.append({
                "left_line_id": left["line_id"],
                "right_line_id": right["line_id"],
                "speaker_similarity": round(speaker.similarity(embeddings[left["line_id"]], embeddings[right["line_id"]]), 9),
            })
    calibration = summarize_partition(line_metrics, CALIBRATION_IDS, threshold)
    held_out = summarize_partition(line_metrics, HELD_OUT_IDS, threshold)
    technical_pass = all(
        line["technical_audio"]["channels"] == 1
        and line["technical_audio"]["sample_rate_hz"] >= 16000
        and line["technical_audio"]["clipping_ratio"] <= args.max_clipping_ratio
        and line["technical_audio"]["silence_ratio"] < args.max_silence_ratio
        for line in line_metrics
    )
    english = [line for line in line_metrics if line["language_role"] == "english"]
    english_asr_pass = all(line["normalized_wer"] is not None and line["normalized_wer"] <= args.max_wer for line in english)
    identity_diagnostic_pass = all(line["speaker_similarity_to_reference"] >= threshold for line in line_metrics)
    stable_acoustic_contract = len({record.get("microphone_chain_id") for record in records}) == 1 and len({record.get("room_profile_id") for record in records}) == 1
    row132_pilot_pass = technical_pass and english_asr_pass and identity_diagnostic_pass and stable_acoustic_contract
    pitch_values = [line["prosody"]["pitch_median_hz"] for line in line_metrics if line["prosody"]["pitch_median_hz"] is not None]
    pace_values = [line["prosody"]["pace_wpm_raw_duration"] for line in line_metrics]
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_continuity_matrix_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS_CONTINUITY_PILOT_PRODUCTION_AUTHORITY_BLOCKED" if row132_pilot_pass else "FAIL_CONTINUITY_PILOT_AUTOMATED_GATES",
        "classification": "PASS_CONTINUITY_PILOT_PRODUCTION_AUTHORITY_BLOCKED" if row132_pilot_pass else "FAIL_CONTINUITY_PILOT_AUTOMATED_GATES",
        "bindings": {"manifest": manifest_binding, "runner": runner_binding, "base_evaluator": base_evaluator_binding, "cv3_adapter": adapter_binding, "speaker_threshold_evidence": threshold_binding, "audio": audio_bindings},
        "line_metrics": line_metrics,
        "pairwise_identity_matrix": {"route": "ERes2Net", "pair_count": len(pairwise), "values": pairwise},
        "partition_diagnostics": {"calibration": calibration, "held_out": held_out},
        "continuity_summary": {
            "line_count": len(line_metrics),
            "scene_count": len({line["scene_id"] for line in line_metrics}),
            "english_line_count": len(english),
            "multilingual_or_code_switch_line_count": len(line_metrics) - len(english),
            "speaker_similarity_threshold": threshold,
            "reference_similarity_min": round(min(line["speaker_similarity_to_reference"] for line in line_metrics), 9),
            "pairwise_similarity_min": round(min(pair["speaker_similarity"] for pair in pairwise), 9),
            "pitch_median_range_hz": round(max(pitch_values) - min(pitch_values), 3) if pitch_values else None,
            "pace_wpm_range": round(max(pace_values) - min(pace_values), 3),
            "microphone_chain_ids": sorted({record.get("microphone_chain_id") for record in records}),
            "room_profile_ids": sorted({record.get("room_profile_id") for record in records}),
        },
        "row_gates": {
            "131": {"diagnostic_matrix_complete": True, "calibration_and_held_out_partitions_disjoint": True, "false_rejection_measured": True, "false_acceptance_measured": False, "independent_source_reference_count": 1, "calibrated_embedding_route_count": 1, "automated_runtime_pass": False, "row_complete": False},
            "132": {"ten_line_three_scene_pilot_pass": row132_pilot_pass, "technical_audio_pass": technical_pass, "english_asr_pass": english_asr_pass, "identity_diagnostic_pass": identity_diagnostic_pass, "microphone_and_room_contract_stable": stable_acoustic_contract, "certified_character_authority_pass": False, "independent_playback_review_pass": False, "automated_runtime_pass": row132_pilot_pass, "row_complete": False},
            "133": {"cross_language_identity_diagnostic_complete": True, "multilingual_content_qa_pass": False, "accent_qa_pass": False, "code_switch_content_qa_pass": False, "independent_playback_review_pass": False, "automated_runtime_pass": False, "row_complete": False},
        },
        "remaining_blockers": {
            "131": ["only one source reference is available, so false acceptance cannot be measured", "only one calibrated embedding route is available", "the chain-specific threshold cannot authorize production identity"],
            "132": ["the reference pool is not a certified production character identity", "independent full-play continuity review is pending"],
            "133": ["the local Whisper route is English-only and cannot score Spanish, French, or code-switch content", "accent authority and multilingual independent playback review are pending"],
        },
        "boundaries": {"media_regenerated_during_evaluation": False, "media_mutated": False, "subjective_review_fabricated": False, "production_promotion_claimed": False, "content_based_suppression": False, "aws_or_ec2_used": False, "mask_or_wave71_touched": False},
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--runner-script", type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--base-evaluator-script", type=Path, required=True)
    parser.add_argument("--expected-base-evaluator-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", type=Path, required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--speaker-threshold-evidence", type=Path, required=True)
    parser.add_argument("--expected-speaker-threshold-evidence-sha256", required=True)
    parser.add_argument("--cv3-root", type=Path, required=True)
    parser.add_argument("--whisper-model-dir", type=Path, required=True)
    parser.add_argument("--transformers-overlay", type=Path, required=True)
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
        print(json.dumps({"classification": "QWEN3_TTS_CONTINUITY_EVALUATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"classification": value["classification"], "continuity_summary": value["continuity_summary"], "row_gates": value["row_gates"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
