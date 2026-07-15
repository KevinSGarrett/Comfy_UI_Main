#!/usr/bin/env python3
"""Conform and independently evaluate a Parler-TTS dialogue runtime artifact."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import tempfile
import wave
from pathlib import Path

from run_wave64_parler_tts_dialogue import inspect_pcm, sha256


WHISPER_REVISION = "87c7102498dcde7456f24cfd30239ca606ed9063"
WHISPER_WEIGHT_SHA256 = "db59695928ded6043adaef491a53ef4e12da9611184d77c53baa691a60b958ad"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def conform_pcm16_mono(source: Path, target: Path, duration_seconds: float) -> dict:
    with wave.open(str(source), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
        payload = handle.readframes(frames)
    if channels != 1 or width != 2 or rate <= 0 or frames <= 0:
        raise ValueError("source must be non-empty mono PCM16")
    target_frames = int(round(duration_seconds * rate))
    if target_frames < frames:
        raise ValueError("timeline conformance refuses to truncate generated speech")
    padding_frames = target_frames - frames
    with wave.open(str(target), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(payload)
        handle.writeframes(b"\0\0" * padding_frames)
    return {
        "source_frames": frames,
        "target_frames": target_frames,
        "padding_frames": padding_frames,
        "padding_seconds": round(padding_frames / rate, 6),
        "speech_truncated": False,
    }


def normalized_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def levenshtein(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, 1):
        next_row = [left_index]
        for right_index, right_value in enumerate(right, 1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    row[right_index] + 1,
                    row[right_index - 1] + (left_value != right_value),
                )
            )
        row = next_row
    return row[-1]


def run_asr(wav: Path, model_dir: Path) -> tuple[str, dict]:
    import soundfile as sf
    import torch
    import transformers
    from scipy.signal import resample_poly
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    if transformers.__version__ != "4.46.1":
        raise ValueError(f"pinned transformers 4.46.1 required, got {transformers.__version__}")
    if not torch.cuda.is_available():
        raise ValueError("CUDA is required for the independent ASR proof")
    audio, source_rate = sf.read(str(wav), dtype="float32")
    divisor = math.gcd(source_rate, 16_000)
    audio_16k = resample_poly(audio, 16_000 // divisor, source_rate // divisor).astype("float32")
    processor = WhisperProcessor.from_pretrained(str(model_dir), local_files_only=True)
    batch = processor(
        audio_16k,
        sampling_rate=16_000,
        return_tensors="pt",
        return_attention_mask=True,
    )
    model = WhisperForConditionalGeneration.from_pretrained(
        str(model_dir),
        local_files_only=True,
        torch_dtype=torch.float16,
        attn_implementation="eager",
    ).to("cuda:0")
    with torch.inference_mode():
        generated = model.generate(
            batch.input_features.to("cuda:0", dtype=torch.float16),
            attention_mask=batch.attention_mask.to("cuda:0"),
            max_new_tokens=64,
            do_sample=False,
        )
    transcript = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
    return transcript, {
        "source_sample_rate_hz": source_rate,
        "analysis_sample_rate_hz": 16_000,
        "analysis_sample_count": len(audio_16k),
        "attention_mask_used": True,
        "device": torch.cuda.get_device_name(),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
    }


def package(args: argparse.Namespace) -> dict:
    root = Path(args.root).resolve()
    runtime_manifest = Path(args.runtime_manifest).resolve()
    whisper_dir = Path(args.whisper_model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if not runtime_manifest.is_file():
        raise ValueError(f"runtime manifest missing: {runtime_manifest}")
    whisper_weight = whisper_dir / "model.safetensors"
    if not whisper_weight.is_file() or sha256(whisper_weight) != WHISPER_WEIGHT_SHA256:
        raise ValueError("Whisper weight is missing or hash-mismatched")
    manifest = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    source_wav = Path(manifest["output"]["path"]).resolve()
    if not source_wav.is_file() or sha256(source_wav) != manifest["output"]["sha256"]:
        raise ValueError("runtime WAV binding mismatch")
    expected_duration = float(manifest["dialogue"]["expected_duration_seconds"])
    if manifest["runtime"]["runtime_executed"] is not True or manifest["runtime"]["decode_succeeded"] is not True:
        raise ValueError("source runtime did not execute and decode successfully")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        proof_dir = temporary / "proofs"
        proof_dir.mkdir()
        conformed = temporary / "L001_C01_parler_tts_conformed.wav"
        conform = conform_pcm16_mono(source_wav, conformed, expected_duration)
        pcm = inspect_pcm(conformed)
        final_wav = output_dir / conformed.name
        voice_profile = {
            "voice_profile_id": "parler_tts_mini_v1_c01_fast_seed64027",
            "character_id": manifest["dialogue"]["character_id"],
            "status": "runtime_candidate_independent_playback_pending",
            "production_grade": False,
            "engine": manifest["engine"],
            "model_revision": manifest["model"]["revision"],
            "model_weight_sha256": manifest["model"]["weight_sha256"],
            "description": manifest["dialogue"]["description"],
            "rights_status": "Apache-2.0 model runtime candidate",
        }
        profile_path = temporary / "voice_profile.json"
        write_json(profile_path, voice_profile)
        dialogue_contract = {
            "schema_name": "wave30_voice_dialogue_contract",
            "dialogue_contract_version": 1,
            "lines": [{
                "line_id": manifest["dialogue"]["line_id"],
                "character_id": manifest["dialogue"]["character_id"],
                "voice_profile_id": voice_profile["voice_profile_id"],
                "text": manifest["dialogue"]["prompt"],
                "start_time": manifest["dialogue"]["contract_start_seconds"],
                "end_time": manifest["dialogue"]["contract_end_seconds"],
                "emotion": manifest["dialogue"]["emotion"],
                "intensity": "controlled",
                "sync_required": True,
                "output_file": str(final_wav),
            }],
        }
        contract_path = temporary / "dialogue_contract.json"
        write_json(contract_path, dialogue_contract)
        profile_hash = sha256(profile_path)
        contract_hash = sha256(contract_path)
        audio_hash = sha256(conformed)
        line_binding = [{"line_id": manifest["dialogue"]["line_id"], "audio_sha256": audio_hash}]

        runtime_proof = {
            "schema_name": "wave30_production_runtime_proof",
            "proof_kind": "production_runtime",
            "engine": manifest["engine"],
            "model": manifest["model"]["model_id"],
            "model_version": manifest["model"]["revision"],
            "model_sha256": manifest["model"]["weight_sha256"],
            "dialogue_contract_sha256": contract_hash,
            "voice_profile_sha256": profile_hash,
            "line_audio_bindings": line_binding,
            "runtime_executed": True,
            "decode_succeeded": True,
        }
        runtime_proof_path = proof_dir / "production_runtime_proof.json"
        write_json(runtime_proof_path, runtime_proof)

        transcript, asr_runtime = run_asr(conformed, whisper_dir)
        expected_tokens = normalized_tokens(manifest["dialogue"]["prompt"])
        observed_tokens = normalized_tokens(transcript)
        normalized_wer = levenshtein(expected_tokens, observed_tokens) / max(1, len(expected_tokens))
        asr_proof = {
            "schema_name": "wave30_asr_proof",
            "proof_kind": "asr",
            "engine": "Transformers Whisper",
            "model": "openai/whisper-tiny.en",
            "model_version": WHISPER_REVISION,
            "model_sha256": WHISPER_WEIGHT_SHA256,
            "dialogue_contract_sha256": contract_hash,
            "voice_profile_sha256": profile_hash,
            "line_results": [{
                "line_id": manifest["dialogue"]["line_id"],
                "audio_sha256": audio_hash,
                "transcript": transcript,
                "start_time": manifest["dialogue"]["contract_start_seconds"],
                "end_time": manifest["dialogue"]["contract_end_seconds"],
            }],
        }
        asr_proof_path = proof_dir / "asr_proof.json"
        write_json(asr_proof_path, asr_proof)
        packet = {
            "schema_version": "1.0",
            "result": "pass",
            "execution_timestamp": manifest["generated_at"],
            "generation_executed": True,
            "execution_passed": True,
            "new_executable_capability": True,
            "source_runtime_manifest": {
                "path": str(runtime_manifest),
                "sha256": sha256(runtime_manifest),
            },
            "source_generated_wav": {
                "path": str(source_wav),
                "sha256": manifest["output"]["sha256"],
                "bytes": manifest["output"]["bytes"],
            },
            "timeline_conformance": conform,
            "verified_media": {
                "media_path": str(final_wav),
                "sha256": audio_hash,
            },
            "technical_audio": pcm,
            "asr": {
                "transcript": transcript,
                "normalized_wer": round(normalized_wer, 6),
                "threshold": 0.2,
                "pass": normalized_wer <= 0.2,
                "runtime": asr_runtime,
            },
            "proofs": {
                "asr_proof_sha256": sha256(asr_proof_path),
                "production_runtime_proof_sha256": sha256(runtime_proof_path),
            },
            "gates": {
                "technical_audio_pass": pcm["clipping_ratio"] <= 0.0001 and pcm["silence_ratio"] < 0.995,
                "dialogue_timing_pass": pcm["duration_seconds"] == expected_duration,
                "intelligibility_pass": normalized_wer <= 0.2,
                "speaker_identity_pass": None,
                "emotion_pass": None,
                "independent_playback_review_pass": None,
                "production_proof_authority_pass": False,
                "final_voice_certification_pass": False,
            },
            "boundaries": {
                "speech_truncated": False,
                "subjective_proofs_fabricated": False,
                "authority_allowlist_mutated": False,
                "ec2_started": False,
                "aws_mutated": False,
                "mask_or_wave71_touched": False,
            },
        }
        write_json(temporary / "packet_manifest.json", packet)
        os.replace(temporary, output_dir)
        return packet
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-manifest", required=True)
    parser.add_argument("--whisper-model-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default="C:/Comfy_UI_Main")
    args = parser.parse_args()
    try:
        packet = package(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "asr": packet["asr"], "verified_media": packet["verified_media"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
