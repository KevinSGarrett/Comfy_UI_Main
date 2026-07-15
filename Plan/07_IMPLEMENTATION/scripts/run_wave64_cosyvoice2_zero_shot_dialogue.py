#!/usr/bin/env python3
"""Run one source-bound local CosyVoice2 zero-shot dialogue inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


EXPECTED_COSYVOICE_COMMIT = "074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc"
EXPECTED_MATCHA_COMMIT = "dd9105b34bf2be2230f4aa1e4769fb586a3c824e"
EXPECTED_SAMPLE_RATE_HZ = 24000
REQUIRED_MODEL_FILES = (
    "README.md",
    "campplus.onnx",
    "config.json",
    "configuration.json",
    "cosyvoice2.yaml",
    "flow.decoder.estimator.fp32.onnx",
    "flow.pt",
    "hift.pt",
    "llm.pt",
    "speech_tokenizer_v2.onnx",
    "CosyVoice-BlankEN/config.json",
    "CosyVoice-BlankEN/generation_config.json",
    "CosyVoice-BlankEN/merges.txt",
    "CosyVoice-BlankEN/model.safetensors",
    "CosyVoice-BlankEN/tokenizer_config.json",
    "CosyVoice-BlankEN/vocab.json",
)
RUNTIME_DISTRIBUTIONS = (
    "HyperPyYAML",
    "diffusers",
    "inflect",
    "modelscope",
    "numpy",
    "onnxruntime-gpu",
    "openai-whisper",
    "pyarrow",
    "pyworld",
    "soundfile",
    "torch",
    "torchaudio",
    "transformers",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_pcm(path: Path) -> dict:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        payload = handle.readframes(frames)
    if channels != 1 or sample_width != 2 or sample_rate <= 0 or frames <= 0:
        raise ValueError("generated WAV must be non-empty mono PCM16")
    samples = memoryview(payload).cast("h")
    peak = max(abs(int(value)) for value in samples) / 32768.0
    rms = math.sqrt(sum(int(value) ** 2 for value in samples) / len(samples)) / 32768.0
    clipping = sum(abs(int(value)) >= 32767 for value in samples)
    silence = sum(abs(int(value)) <= 32 for value in samples)
    return {
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frame_count": frames,
        "duration_seconds": round(frames / sample_rate, 6),
        "peak_dbfs": round(20.0 * math.log10(max(peak, 1e-12)), 4),
        "rms_dbfs": round(20.0 * math.log10(max(rms, 1e-12)), 4),
        "clipping_ratio": round(clipping / len(samples), 8),
        "silence_ratio": round(silence / len(samples), 8),
    }


def load_wav_soundfile_compat(path: str, target_sr: int, min_sr: int = 16000):
    """Decode PCM without Torchaudio's Windows TorchCodec dependency."""
    import soundfile as sf
    import torch
    import torchaudio

    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate < min_sr:
        raise ValueError(f"WAV sample rate {sample_rate} must be at least {min_sr}")
    speech = torch.from_numpy(audio.mean(axis=1)).unsqueeze(0)
    if sample_rate != target_sr:
        speech = torchaudio.functional.resample(speech, sample_rate, target_sr)
    return speech


def git_commit(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().lower()


def verify_source_identity(source_dir: Path) -> dict:
    source_commit = git_commit(source_dir)
    matcha_dir = source_dir / "third_party/Matcha-TTS"
    matcha_commit = git_commit(matcha_dir)
    if source_commit != EXPECTED_COSYVOICE_COMMIT:
        raise ValueError(f"CosyVoice source commit mismatch: {source_commit}")
    if matcha_commit != EXPECTED_MATCHA_COMMIT:
        raise ValueError(f"Matcha-TTS source commit mismatch: {matcha_commit}")
    return {
        "source_url": "https://github.com/FunAudioLLM/CosyVoice",
        "cosyvoice_commit": source_commit,
        "matcha_tts_commit": matcha_commit,
        "license": "Apache-2.0",
    }


def hash_model_payloads(model_dir: Path) -> list[dict]:
    payloads = []
    for relative in REQUIRED_MODEL_FILES:
        path = model_dir / relative
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"required CosyVoice2 payload is missing or empty: {relative}")
        payloads.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return payloads


def runtime_package_identity() -> dict:
    result = {}
    for name in RUNTIME_DISTRIBUTIONS:
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError as exc:
            raise ValueError(f"required runtime distribution is missing: {name}") from exc
    return result


def validate_inputs(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    model_dir = Path(args.model_dir).resolve()
    source_dir = Path(args.source_dir).resolve()
    prompt_wav = Path(args.prompt_wav).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not model_dir.is_dir():
        raise ValueError(f"complete local CosyVoice2 model directory is required: {model_dir}")
    if not source_dir.is_dir():
        raise ValueError(f"pinned CosyVoice source directory is required: {source_dir}")
    if not prompt_wav.is_file():
        raise ValueError(f"independent reference-speaker WAV is required: {prompt_wav}")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if sha256(prompt_wav) != args.prompt_wav_sha256.lower():
        raise ValueError("reference-speaker WAV SHA-256 mismatch")
    for value, label in (
        (args.prompt_transcript, "prompt transcript"),
        (args.text, "dialogue text"),
        (args.style_emotion, "style emotion"),
        (args.style_intensity, "style intensity"),
    ):
        if not value.strip():
            raise ValueError(f"{label} must be non-empty")
    if args.contract_end <= args.contract_start or args.max_duration_delta < 0:
        raise ValueError("invalid dialogue timing contract")
    if not 0.8 <= args.speed <= 1.2:
        raise ValueError("speed must remain within the predeclared 0.8 to 1.2 range")
    if args.inference_mode not in {"zero_shot", "instruct2"}:
        raise ValueError(f"unsupported inference mode: {args.inference_mode}")
    if args.candidate_ordinal != 1:
        raise ValueError("the instruct-control path authorizes exactly one candidate")
    if args.inference_mode == "instruct2":
        if not args.instruct_text.strip():
            raise ValueError("instruct2 mode requires non-empty instruct text")
        if not args.instruct_text.endswith("<|endofprompt|>"):
            raise ValueError("instruct2 text must end with <|endofprompt|>")
        instruct_hash = hashlib.sha256(args.instruct_text.encode("utf-8")).hexdigest()
        if instruct_hash != args.instruct_text_sha256.lower():
            raise ValueError("instruct2 text SHA-256 mismatch")
    elif args.instruct_text or args.instruct_text_sha256:
        raise ValueError("zero_shot mode must not carry instruct2 text or hash")
    return model_dir, source_dir, prompt_wav, output_dir


def activate_source_path(source_dir: Path) -> list[str]:
    source_paths = [
        str(source_dir.resolve()),
        str((source_dir / "third_party/Matcha-TTS").resolve()),
    ]
    missing = [path for path in source_paths if not Path(path).is_dir()]
    if missing:
        raise ValueError(f"validated CosyVoice source path is missing: {missing[0]}")
    sys.path[:] = [entry for entry in sys.path if entry not in source_paths]
    sys.path[0:0] = source_paths
    return source_paths


def inference_results(engine, args: argparse.Namespace, prompt_wav: Path):
    common = {
        "stream": False,
        "speed": args.speed,
        "text_frontend": True,
    }
    if args.inference_mode == "instruct2":
        return engine.inference_instruct2(
            args.text,
            args.instruct_text,
            str(prompt_wav),
            **common,
        )
    return engine.inference_zero_shot(
        args.text,
        args.prompt_transcript,
        str(prompt_wav),
        **common,
    )


def run(args: argparse.Namespace) -> dict:
    model_dir, source_dir, prompt_wav, output_dir = validate_inputs(args)
    source_identity = verify_source_identity(source_dir)
    model_payloads = hash_model_payloads(model_dir)
    package_identity = runtime_package_identity()
    activate_source_path(source_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        import numpy as np
        import onnxruntime
        import soundfile as sf
        import torch
        import cosyvoice.cli.frontend as cosyvoice_frontend
        from cosyvoice.cli.cosyvoice import CosyVoice2

        if not torch.cuda.is_available():
            raise ValueError("CUDA is required for the CosyVoice2 neural runtime")
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        cosyvoice_frontend.load_wav = load_wav_soundfile_compat

        started = time.perf_counter()
        engine = CosyVoice2(
            str(model_dir),
            load_jit=False,
            load_trt=False,
            load_vllm=False,
            fp16=True,
        )
        if engine.sample_rate != EXPECTED_SAMPLE_RATE_HZ:
            raise ValueError(f"unexpected CosyVoice2 sample rate: {engine.sample_rate}")
        chunks = []
        with torch.inference_mode():
            for result in inference_results(engine, args, prompt_wav):
                speech = result.get("tts_speech")
                if speech is None or speech.ndim != 2 or speech.shape[0] != 1:
                    raise ValueError("CosyVoice2 returned an invalid tts_speech tensor")
                chunks.append(speech.detach().float().cpu())
        inference_seconds = time.perf_counter() - started
        if not chunks:
            raise ValueError("CosyVoice2 returned no audio chunks")
        audio = torch.cat(chunks, dim=1).numpy().squeeze()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError("CosyVoice2 returned invalid audio samples")
        if float(np.max(np.abs(audio))) > 1.0001:
            raise ValueError("CosyVoice2 returned out-of-range audio samples")

        wav = temporary / args.output_name
        sf.write(str(wav), audio, engine.sample_rate, subtype="PCM_16")
        pcm = inspect_pcm(wav)
        expected_duration = args.contract_end - args.contract_start
        duration_delta = abs(pcm["duration_seconds"] - expected_duration)
        technical_pass = (
            pcm["clipping_ratio"] <= 0.0001
            and pcm["silence_ratio"] < 0.995
            and pcm["rms_dbfs"] > -46.0
        )
        timing_pass = duration_delta <= args.max_duration_delta
        prompt_pcm = inspect_pcm(prompt_wav)
        speech_tokenizer_providers = engine.frontend.speech_tokenizer_session.get_providers()
        campplus_providers = engine.frontend.campplus_session.get_providers()
        manifest = {
            "schema_version": "1.0",
            "run_id": args.run_id,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "engine": "CosyVoice2",
            "engine_source": source_identity,
            "model": {
                "model_id": "FunAudioLLM/CosyVoice2-0.5B",
                "model_dir": str(model_dir),
                "license": "Apache-2.0",
                "local_files_only": True,
                "payloads": model_payloads,
            },
            "reference_speaker": {
                "path": str(prompt_wav),
                "sha256": args.prompt_wav_sha256.lower(),
                "bytes": prompt_wav.stat().st_size,
                "expected_transcript": args.prompt_transcript,
                "pcm": prompt_pcm,
                "source_page": args.reference_source_page,
                "license": args.reference_license,
                "license_reference": args.reference_license_reference,
                "speaker_name": args.reference_speaker_name,
                "binding_method": "zero_shot_reference_audio_plus_exact_transcript",
            },
            "runtime": {
                "device": torch.cuda.get_device_name(0),
                "torch_version": torch.__version__,
                "dtype": "float16",
                "seed": args.seed,
                "speed": args.speed,
                "stream": False,
                "text_frontend": True,
                "reference_audio_decoder": "soundfile_float32_mono_compat",
                "inference_seconds": round(inference_seconds, 4),
                "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated()),
                "onnx_available_providers": onnxruntime.get_available_providers(),
                "speech_tokenizer_session_providers": speech_tokenizer_providers,
                "campplus_session_providers": campplus_providers,
                "runtime_packages": package_identity,
                "runtime_executed": True,
                "decode_succeeded": True,
                "inference_mode": args.inference_mode,
                "model_native_speed_control": True,
                "post_generation_truncation_applied": False,
                "post_generation_time_stretch_applied": False,
            },
            "dialogue": {
                "character_id": args.character_id,
                "line_id": args.line_id,
                "text": args.text,
                "contract_start_seconds": args.contract_start,
                "contract_end_seconds": args.contract_end,
                "expected_duration_seconds": expected_duration,
                "style_emotion_required": args.style_emotion,
                "style_intensity_required": args.style_intensity,
                "instruct_text": args.instruct_text or None,
                "instruct_text_sha256": args.instruct_text_sha256.lower() or None,
                "model_native_instruction_applied": args.inference_mode == "instruct2",
                "style_instruction_applied": args.inference_mode == "instruct2",
                "style_contract_verified": False,
                "style_contract_substituted": False,
            },
            "output": {
                "path": str(output_dir / wav.name),
                "sha256": sha256(wav),
                "bytes": wav.stat().st_size,
                "pcm": pcm,
            },
            "gates": {
                "model_payload_hash_binding_pass": True,
                "source_code_identity_pass": True,
                "independent_reference_speaker_bound": True,
                "technical_audio_pass": technical_pass,
                "dialogue_timing_pass": timing_pass,
                "duration_delta_seconds": round(duration_delta, 6),
                "asr_pass": None,
                "speaker_identity_pass": None,
                "emotion_pass": None,
                "style_intensity_pass": None,
                "independent_playback_review_pass": None,
                "production_proof_authority_pass": False,
            },
            "boundaries": {
                "reference_audio_is_evaluator_or_conditioning_input_only": True,
                "style_contract_remains_unverified": True,
                "network_used_for_inference": False,
                "comfyui_core_environment_modified": False,
                "ec2_started": False,
                "aws_mutated": False,
                "final_voice_certification_claimed": False,
                "authorized_candidate_ordinal": args.candidate_ordinal,
                "maximum_candidates_for_control_path": 1,
            },
        }
        (temporary / "runtime_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--prompt-wav", required=True)
    parser.add_argument("--prompt-wav-sha256", required=True)
    parser.add_argument("--prompt-transcript", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--text", default="We hold the frame steady and move on the beat.")
    parser.add_argument("--output-name", default="L001_C01_cosyvoice2_zero_shot.wav")
    parser.add_argument("--character-id", default="C01")
    parser.add_argument("--line-id", default="L001")
    parser.add_argument("--style-emotion", default="focused")
    parser.add_argument("--style-intensity", default="controlled")
    parser.add_argument("--contract-start", type=float, default=1.2)
    parser.add_argument("--contract-end", type=float, default=4.2)
    parser.add_argument("--max-duration-delta", type=float, default=0.35)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument(
        "--inference-mode", choices=("zero_shot", "instruct2"), default="zero_shot"
    )
    parser.add_argument("--instruct-text", default="")
    parser.add_argument("--instruct-text-sha256", default="")
    parser.add_argument("--candidate-ordinal", type=int, default=1)
    parser.add_argument("--seed", type=int, default=64029)
    parser.add_argument("--reference-speaker-name", default="Chris Goringe")
    parser.add_argument(
        "--reference-source-page",
        default="https://commons.wikimedia.org/wiki/File:LibriVox_-_The_Raven_-_Chris_Goringe.ogg",
    )
    parser.add_argument("--reference-license", default="Public Domain Mark 1.0")
    parser.add_argument(
        "--reference-license-reference", default="https://librivox.org/pages/public-domain/"
    )
    args = parser.parse_args()
    try:
        manifest = run(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "output": manifest["output"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
