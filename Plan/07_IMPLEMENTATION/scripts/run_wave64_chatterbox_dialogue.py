#!/usr/bin/env python3
"""Run one hash-bound local Chatterbox reference-voice dialogue candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import tempfile
import time
import wave
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


MODEL_ID = "ResembleAI/chatterbox"
MODEL_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
EXPECTED_TEXT = "We hold the frame steady and move on the beat."
EXPECTED_REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
EXPECTED_REFERENCE_TRANSCRIPT = (
    "Once upon a midnight dreary, while I pondered, weak and weary."
)
EXPECTED_SAMPLE_RATE_HZ = 24000
EXPECTED_EXAGGERATION = 0.60
EXPECTED_CFG_WEIGHT = 0.30
EXPECTED_TEMPERATURE = 0.80
EXPECTED_REPETITION_PENALTY = 1.20
EXPECTED_MIN_P = 0.05
EXPECTED_TOP_P = 1.00
EXPECTED_SEED = 64032
EXPECTED_DURATION_SECONDS = 3.0
EXPECTED_MAX_DURATION_DELTA = 0.35
EXPECTED_MODEL_HASHES = {
    "ve.safetensors": "f0921cab452fa278bc25cd23ffd59d36f816d7dc5181dd1bef9751a7fb61f63c",
    "t3_cfg.safetensors": "914cb1696f47527fe8852ca8f1fe1fa63cb34f76f9c715e84e067b744dd0da81",
    "s3gen.safetensors": "2b78103c654207393955e4900aac14a12de8ef25f4b09424f1ef91941f161d4e",
    "tokenizer.json": "d71e3a44eabb1784df9a68e9f95b251ecbf1a7af6a9f50835856b2ca9d8c14a5",
    "conds.pt": "6552d70568833628ba019c6b03459e77fe71ca197d5c560cef9411bee9d87f4e",
}
RUNTIME_DISTRIBUTIONS = (
    "chatterbox-tts",
    "diffusers",
    "librosa",
    "numpy",
    "resemble-perth",
    "s3tokenizer",
    "safetensors",
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


def hash_model_payloads(model_dir: Path) -> list[dict]:
    payloads = []
    for relative, expected_hash in EXPECTED_MODEL_HASHES.items():
        path = model_dir / relative
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"required Chatterbox payload is missing or empty: {relative}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Chatterbox payload SHA-256 mismatch: {relative}")
        payloads.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": actual_hash,
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
    if result["chatterbox-tts"] != "0.1.7":
        raise ValueError("chatterbox-tts runtime must remain pinned to 0.1.7")
    if result["torch"] != "2.11.0+cu128" or result["torchaudio"] != "2.11.0+cu128":
        raise ValueError("RTX 5060 runtime requires the validated Torch/Torchaudio 2.11.0+cu128 override")
    if result["transformers"] != "5.2.0":
        raise ValueError("Chatterbox runtime requires Transformers 5.2.0")
    return result


def validate_inputs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    model_dir = Path(args.model_dir).resolve()
    prompt_wav = Path(args.prompt_wav).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not model_dir.is_dir():
        raise ValueError(f"complete local Chatterbox model directory is required: {model_dir}")
    if not prompt_wav.is_file():
        raise ValueError(f"independent reference-speaker WAV is required: {prompt_wav}")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if sha256(prompt_wav) != EXPECTED_REFERENCE_SHA256:
        raise ValueError("reference-speaker WAV SHA-256 mismatch")
    if args.prompt_wav_sha256.lower() != EXPECTED_REFERENCE_SHA256:
        raise ValueError("declared reference-speaker SHA-256 is not the approved binding")
    if args.prompt_transcript != EXPECTED_REFERENCE_TRANSCRIPT:
        raise ValueError("reference-speaker transcript differs from the approved binding")
    if args.text != EXPECTED_TEXT:
        raise ValueError("dialogue text differs from the immutable contract")
    if args.style_emotion != "focused" or args.style_intensity != "controlled":
        raise ValueError("style targets differ from the immutable contract")
    expected_duration = args.contract_end - args.contract_start
    if not math.isclose(expected_duration, EXPECTED_DURATION_SECONDS, abs_tol=1e-9):
        raise ValueError("dialogue duration differs from the immutable 3.0-second contract")
    if not math.isclose(args.max_duration_delta, EXPECTED_MAX_DURATION_DELTA, abs_tol=1e-9):
        raise ValueError("duration tolerance differs from the approved 0.35-second gate")
    fixed_controls = {
        "exaggeration": (args.exaggeration, EXPECTED_EXAGGERATION),
        "cfg_weight": (args.cfg_weight, EXPECTED_CFG_WEIGHT),
        "temperature": (args.temperature, EXPECTED_TEMPERATURE),
        "repetition_penalty": (args.repetition_penalty, EXPECTED_REPETITION_PENALTY),
        "min_p": (args.min_p, EXPECTED_MIN_P),
        "top_p": (args.top_p, EXPECTED_TOP_P),
    }
    for label, (actual, expected) in fixed_controls.items():
        if not math.isclose(actual, expected, abs_tol=1e-9):
            raise ValueError(f"{label} differs from the predeclared one-candidate control")
    if args.seed != EXPECTED_SEED:
        raise ValueError("seed differs from the predeclared one-candidate control")
    if args.candidate_ordinal != 1:
        raise ValueError("the Chatterbox control path authorizes exactly one candidate")
    return model_dir, prompt_wav, output_dir


def normalize_watermark_score(value) -> float:
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def control_contract(args: argparse.Namespace) -> tuple[dict, str]:
    contract = {
        "text": args.text,
        "reference_sha256": EXPECTED_REFERENCE_SHA256,
        "reference_transcript": args.prompt_transcript,
        "expected_duration_seconds": EXPECTED_DURATION_SECONDS,
        "max_duration_delta_seconds": args.max_duration_delta,
        "style_emotion": args.style_emotion,
        "style_intensity": args.style_intensity,
        "seed": args.seed,
        "candidate_ordinal": args.candidate_ordinal,
        "exaggeration": args.exaggeration,
        "cfg_weight": args.cfg_weight,
        "temperature": args.temperature,
        "repetition_penalty": args.repetition_penalty,
        "min_p": args.min_p,
        "top_p": args.top_p,
        "post_generation_truncation_allowed": False,
        "post_generation_time_stretch_allowed": False,
        "same_control_path_retry_allowed": False,
    }
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return contract, hashlib.sha256(encoded).hexdigest()


def run(args: argparse.Namespace) -> dict:
    model_dir, prompt_wav, output_dir = validate_inputs(args)
    model_payloads = hash_model_payloads(model_dir)
    package_identity = runtime_package_identity()
    fixed_contract, fixed_contract_sha256 = control_contract(args)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from chatterbox.tts import ChatterboxTTS

        if not torch.cuda.is_available():
            raise ValueError("CUDA is required for the Chatterbox neural runtime")
        if "sm_120" not in torch.cuda.get_arch_list():
            raise ValueError("Torch runtime does not support the RTX 5060 sm_120 architecture")
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.use_deterministic_algorithms(False)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        started = time.perf_counter()
        engine = ChatterboxTTS.from_local(model_dir, "cuda")
        if engine.sr != EXPECTED_SAMPLE_RATE_HZ:
            raise ValueError(f"unexpected Chatterbox sample rate: {engine.sr}")
        with torch.inference_mode():
            speech = engine.generate(
                args.text,
                repetition_penalty=args.repetition_penalty,
                min_p=args.min_p,
                top_p=args.top_p,
                audio_prompt_path=str(prompt_wav),
                exaggeration=args.exaggeration,
                cfg_weight=args.cfg_weight,
                temperature=args.temperature,
            )
        inference_seconds = time.perf_counter() - started
        if speech.ndim != 2 or speech.shape[0] != 1 or speech.shape[1] <= 0:
            raise ValueError("Chatterbox returned an invalid speech tensor")
        audio = speech.detach().float().cpu().numpy().squeeze()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError("Chatterbox returned invalid audio samples")
        if float(np.max(np.abs(audio))) > 1.0001:
            raise ValueError("Chatterbox returned out-of-range audio samples")
        watermark_score = normalize_watermark_score(
            engine.watermarker.get_watermark(audio, sample_rate=engine.sr)
        )
        watermark_pass = watermark_score >= 0.5

        wav = temporary / args.output_name
        sf.write(str(wav), audio, engine.sr, subtype="PCM_16")
        pcm = inspect_pcm(wav)
        duration_delta = abs(pcm["duration_seconds"] - EXPECTED_DURATION_SECONDS)
        technical_pass = (
            pcm["clipping_ratio"] <= 0.0001
            and pcm["silence_ratio"] < 0.995
            and pcm["rms_dbfs"] > -46.0
            and watermark_pass
        )
        timing_pass = duration_delta <= args.max_duration_delta
        manifest = {
            "schema_version": "1.0",
            "run_id": args.run_id,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "engine": "ChatterboxTTS",
            "engine_source": {
                "package": "chatterbox-tts",
                "package_version": package_identity["chatterbox-tts"],
                "source_url": "https://github.com/resemble-ai/chatterbox",
                "license": "MIT",
            },
            "implementation": {
                "runner_path": str(Path(__file__).resolve()),
                "runner_sha256": sha256(Path(__file__).resolve()),
                "control_contract": fixed_contract,
                "control_contract_sha256": fixed_contract_sha256,
            },
            "model": {
                "model_id": MODEL_ID,
                "revision": MODEL_REVISION,
                "model_dir": str(model_dir),
                "license": "MIT",
                "local_files_only": True,
                "payloads": model_payloads,
            },
            "reference_speaker": {
                "path": str(prompt_wav),
                "sha256": EXPECTED_REFERENCE_SHA256,
                "bytes": prompt_wav.stat().st_size,
                "expected_transcript": args.prompt_transcript,
                "pcm": inspect_pcm(prompt_wav),
                "source_page": args.reference_source_page,
                "license": args.reference_license,
                "license_reference": args.reference_license_reference,
                "speaker_name": args.reference_speaker_name,
                "binding_method": "zero_shot_reference_audio",
            },
            "runtime": {
                "device": torch.cuda.get_device_name(0),
                "cuda_architecture": "sm_120",
                "seed": args.seed,
                "inference_seconds": round(inference_seconds, 4),
                "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated()),
                "runtime_packages": package_identity,
                "torch_pin_compatibility_override": {
                    "package_declared": "2.6.0+cu124",
                    "installed": package_identity["torch"],
                    "reason": "package pin lacks RTX 5060 sm_120 kernels",
                    "cuda_tensor_probe_pass": True,
                },
                "runtime_executed": True,
                "decode_succeeded": True,
                "post_generation_truncation_applied": False,
                "post_generation_time_stretch_applied": False,
            },
            "native_controls": {
                "exaggeration": args.exaggeration,
                "cfg_weight": args.cfg_weight,
                "temperature": args.temperature,
                "repetition_penalty": args.repetition_penalty,
                "min_p": args.min_p,
                "top_p": args.top_p,
                "controls_predeclared_before_generation": True,
                "controls_tuned_against_candidate_result": False,
                "style_contract_verified": False,
                "control_interpretation": (
                    "bounded native pacing and expression controls; not a calibrated focused/controlled taxonomy"
                ),
            },
            "dialogue": {
                "character_id": args.character_id,
                "line_id": args.line_id,
                "text": args.text,
                "contract_start_seconds": args.contract_start,
                "contract_end_seconds": args.contract_end,
                "expected_duration_seconds": EXPECTED_DURATION_SECONDS,
                "style_emotion_required": args.style_emotion,
                "style_intensity_required": args.style_intensity,
                "style_contract_verified": False,
                "style_contract_substituted": False,
            },
            "output": {
                "path": str(output_dir / wav.name),
                "sha256": sha256(wav),
                "bytes": wav.stat().st_size,
                "pcm": pcm,
                "perth_watermark_score": watermark_score,
                "perth_watermark_detected": watermark_pass,
            },
            "gates": {
                "model_payload_hash_binding_pass": True,
                "package_identity_pass": True,
                "cuda_architecture_probe_pass": True,
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
                "candidate_media_mutated": False,
                "watermark_removed": False,
                "network_used_for_inference": False,
                "comfyui_core_environment_modified": False,
                "ec2_started": False,
                "aws_mutated": False,
                "final_voice_certification_claimed": False,
                "authorized_candidate_ordinal": args.candidate_ordinal,
                "maximum_candidates_for_control_path": 1,
                "same_control_path_retry_allowed": False,
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
    parser.add_argument("--prompt-wav", required=True)
    parser.add_argument("--prompt-wav-sha256", default=EXPECTED_REFERENCE_SHA256)
    parser.add_argument("--prompt-transcript", default=EXPECTED_REFERENCE_TRANSCRIPT)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--text", default=EXPECTED_TEXT)
    parser.add_argument("--output-name", default="L001_C01_chatterbox.wav")
    parser.add_argument("--character-id", default="C01")
    parser.add_argument("--line-id", default="L001")
    parser.add_argument("--style-emotion", default="focused")
    parser.add_argument("--style-intensity", default="controlled")
    parser.add_argument("--contract-start", type=float, default=1.2)
    parser.add_argument("--contract-end", type=float, default=4.2)
    parser.add_argument("--max-duration-delta", type=float, default=EXPECTED_MAX_DURATION_DELTA)
    parser.add_argument("--exaggeration", type=float, default=EXPECTED_EXAGGERATION)
    parser.add_argument("--cfg-weight", type=float, default=EXPECTED_CFG_WEIGHT)
    parser.add_argument("--temperature", type=float, default=EXPECTED_TEMPERATURE)
    parser.add_argument("--repetition-penalty", type=float, default=EXPECTED_REPETITION_PENALTY)
    parser.add_argument("--min-p", type=float, default=EXPECTED_MIN_P)
    parser.add_argument("--top-p", type=float, default=EXPECTED_TOP_P)
    parser.add_argument("--candidate-ordinal", type=int, default=1)
    parser.add_argument("--seed", type=int, default=EXPECTED_SEED)
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
