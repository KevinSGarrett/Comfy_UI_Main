#!/usr/bin/env python3
"""Run one hash-bound local Parler-TTS dialogue inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
import wave
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


DEFAULT_MODEL_REVISION = "0392b9451a601e528fd863bbb0598431fee810d9"
DEFAULT_MODEL_WEIGHT_SHA256 = "bc430eb6752b96ffb3f67036d1a6e207fbd031575a775716ffa64ef1eeb03692"
EXPECTED_ENGINE_VERSION = "0.2.2"
EXPECTED_ENGINE_COMMIT = "d108732cd57788ec86bc857d99a6cabd66663d68"
CODEC_FRAME_RATE_HZ = 86


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
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


def max_tokens_for_contract(start: float, end: float, allowed_delta: float) -> int:
    if end <= start or allowed_delta < 0:
        raise ValueError("invalid dialogue timing contract")
    return int(math.ceil(((end - start) + allowed_delta) * CODEC_FRAME_RATE_HZ))


def verify_engine_identity() -> dict:
    distribution = metadata.distribution("parler_tts")
    direct_url_text = distribution.read_text("direct_url.json")
    if not direct_url_text:
        raise ValueError("Parler-TTS direct_url.json is required for runtime identity proof")
    direct_url = json.loads(direct_url_text)
    commit = direct_url.get("vcs_info", {}).get("commit_id")
    if distribution.version != EXPECTED_ENGINE_VERSION or commit != EXPECTED_ENGINE_COMMIT:
        raise ValueError(
            f"Parler-TTS package identity mismatch: version={distribution.version}, commit={commit}"
        )
    return {
        "version": distribution.version,
        "commit": commit,
        "source_url": direct_url.get("url"),
        "direct_url_sha256": hashlib.sha256(direct_url_text.encode("utf-8")).hexdigest(),
    }


def validate_inputs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    weight = model_dir / "model.safetensors"
    if not model_dir.is_dir() or not weight.is_file():
        raise ValueError(f"complete local model directory is required: {model_dir}")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if not args.prompt.strip() or not args.description.strip():
        raise ValueError("prompt and description must be non-empty")
    if args.contract_end <= args.contract_start:
        raise ValueError("contract end must exceed contract start")
    actual_hash = sha256(weight)
    if actual_hash != args.model_weight_sha256.lower():
        raise ValueError(f"model weight SHA-256 mismatch: {actual_hash}")
    return model_dir, output_dir, weight


def run(args: argparse.Namespace) -> dict:
    model_dir, output_dir, weight = validate_inputs(args)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        import numpy as np
        import soundfile as sf
        import torch
        import transformers
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        if not torch.cuda.is_available():
            raise ValueError("CUDA is required for this production runtime proof")
        if transformers.__version__ != "4.46.1":
            raise ValueError(f"pinned transformers 4.46.1 required, got {transformers.__version__}")
        engine_identity = verify_engine_identity()

        device = torch.device("cuda:0")
        dtype = torch.float16
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        model = ParlerTTSForConditionalGeneration.from_pretrained(
            str(model_dir),
            local_files_only=True,
            torch_dtype=dtype,
            attn_implementation="eager",
        ).to(device)
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        description_tokens = tokenizer(args.description, return_tensors="pt")
        prompt_tokens = tokenizer(args.prompt, return_tensors="pt")
        description_ids = description_tokens.input_ids.to(device)
        description_mask = description_tokens.attention_mask.to(device)
        prompt_ids = prompt_tokens.input_ids.to(device)
        prompt_mask = prompt_tokens.attention_mask.to(device)
        max_new_tokens = max_tokens_for_contract(
            args.contract_start, args.contract_end, args.max_duration_delta
        )
        with torch.inference_mode():
            generated = model.generate(
                input_ids=description_ids,
                attention_mask=description_mask,
                prompt_input_ids=prompt_ids,
                prompt_attention_mask=prompt_mask,
                do_sample=False,
                max_new_tokens=max_new_tokens,
            )
        inference_seconds = time.perf_counter() - started
        audio = generated.detach().float().cpu().numpy().squeeze()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError("model returned invalid audio samples")
        if float(np.max(np.abs(audio))) > 1.0:
            raise ValueError("model returned out-of-range audio samples")

        wav = temporary / args.output_name
        sf.write(str(wav), audio, int(model.config.sampling_rate), subtype="PCM_16")
        pcm = inspect_pcm(wav)
        expected_duration = args.contract_end - args.contract_start
        duration_delta = abs(pcm["duration_seconds"] - expected_duration)
        technical_pass = (
            pcm["clipping_ratio"] <= 0.0001
            and pcm["silence_ratio"] < 0.995
            and pcm["rms_dbfs"] > -46.0
        )
        timing_pass = duration_delta <= args.max_duration_delta
        manifest = {
            "schema_version": "1.0",
            "run_id": args.run_id,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "engine": "Parler-TTS",
            "engine_version": engine_identity["version"],
            "engine_commit": engine_identity["commit"],
            "engine_source_url": engine_identity["source_url"],
            "engine_direct_url_sha256": engine_identity["direct_url_sha256"],
            "engine_package_identity_verified": True,
            "model": {
                "model_id": "parler-tts/parler-tts-mini-v1",
                "revision": args.model_revision,
                "local_files_only": True,
                "weight_path": str(weight),
                "weight_sha256": args.model_weight_sha256.lower(),
                "license": "Apache-2.0",
            },
            "runtime": {
                "device": torch.cuda.get_device_name(),
                "torch_version": torch.__version__,
                "transformers_version": transformers.__version__,
                "dtype": "float16",
                "attention": "eager",
                "seed": args.seed,
                "max_new_tokens": max_new_tokens,
                "codec_frame_rate_hz": CODEC_FRAME_RATE_HZ,
                "explicit_attention_masks": True,
                "inference_seconds": round(inference_seconds, 4),
                "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated()),
                "runtime_executed": True,
                "decode_succeeded": True,
            },
            "dialogue": {
                "character_id": args.character_id,
                "line_id": args.line_id,
                "prompt": args.prompt,
                "description": args.description,
                "contract_start_seconds": args.contract_start,
                "contract_end_seconds": args.contract_end,
                "expected_duration_seconds": expected_duration,
                "emotion": args.emotion,
            },
            "output": {
                "path": str(output_dir / wav.name),
                "sha256": sha256(wav),
                "bytes": wav.stat().st_size,
                "pcm": pcm,
            },
            "gates": {
                "technical_audio_pass": technical_pass,
                "dialogue_timing_pass": timing_pass,
                "duration_delta_seconds": round(duration_delta, 6),
                "asr_pass": None,
                "speaker_identity_pass": None,
                "emotion_pass": None,
                "independent_playback_review_pass": None,
                "production_proof_authority_pass": False,
            },
            "boundaries": {
                "network_used_for_inference": False,
                "comfyui_core_environment_modified": False,
                "ec2_started": False,
                "aws_mutated": False,
                "final_voice_certification_claimed": False,
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
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--model-revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--model-weight-sha256", default=DEFAULT_MODEL_WEIGHT_SHA256)
    parser.add_argument("--output-name", default="L001_C01_parler_tts.wav")
    parser.add_argument("--character-id", default="C01")
    parser.add_argument("--line-id", default="L001")
    parser.add_argument("--emotion", default="focused")
    parser.add_argument("--contract-start", type=float, default=1.2)
    parser.add_argument("--contract-end", type=float, default=4.2)
    parser.add_argument("--max-duration-delta", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=64027)
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
