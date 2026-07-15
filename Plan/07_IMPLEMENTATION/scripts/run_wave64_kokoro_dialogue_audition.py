#!/usr/bin/env python3
"""Run the immutable three-candidate Wave64 Kokoro dialogue audition."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import soundfile as sf


EXPECTED_TEXT = "We hold the frame steady and move on the beat."
EXPECTED_SPEEDS = (1.00, 1.15, 1.30)
EXPECTED_SAMPLE_RATE_HZ = 24000
EXPECTED_DURATION_SECONDS = 3.0
EXPECTED_SAMPLE_COUNT = 72000
EXPECTED_SEED = 64033
EXPECTED_MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
EXPECTED_ASSETS = {
    "model": {
        "sha256": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
        "bytes": 327212226,
    },
    "config": {
        "sha256": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
        "bytes": 2351,
    },
    "voice": {
        "sha256": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
        "bytes": 523425,
    },
}
EXPECTED_PACKAGES = {
    "en-core-web-sm": "3.8.0",
    "kokoro": "0.9.4",
    "misaki": "0.9.4",
    "espeakng-loader": "0.2.4",
    "soundfile": "0.14.0",
}
EXPECTED_TORCH_VERSION = "2.12.1+cpu"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind_file(path: Path, label: str, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    result = {"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size}
    if expected and (result["sha256"] != expected["sha256"] or result["bytes"] != expected["bytes"]):
        raise ValueError(f"{label} hash or byte count mismatch")
    return result


def runtime_package_identity() -> dict[str, str]:
    import torch

    identity = {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
    identity["torch"] = torch.__version__
    expected = dict(EXPECTED_PACKAGES)
    expected["torch"] = EXPECTED_TORCH_VERSION
    if identity != expected:
        raise ValueError(f"runtime package identity mismatch: expected {expected}, got {identity}")
    identity["python"] = sys.version.split()[0]
    return identity


def parse_speeds(values: Iterable[str | float]) -> tuple[float, ...]:
    speeds = tuple(float(value) for value in values)
    if speeds != EXPECTED_SPEEDS:
        raise ValueError(f"audition speeds must be exactly {EXPECTED_SPEEDS}")
    return speeds


def prepare_output_dir(path: Path) -> Path:
    if path.exists():
        raise ValueError(f"output directory already exists; retries are prohibited: {path}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def set_seed(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def collect_audio(results: Iterable[Any]) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for result in results:
        audio = getattr(result, "audio", None)
        if audio is None:
            continue
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        array = np.asarray(audio, dtype=np.float32).reshape(-1)
        if array.size:
            chunks.append(array)
    if not chunks:
        raise ValueError("Kokoro returned no audio samples")
    merged = np.concatenate(chunks)
    if not np.all(np.isfinite(merged)):
        raise ValueError("Kokoro returned non-finite audio")
    if float(np.max(np.abs(merged))) > 1.0:
        raise ValueError("Kokoro audio exceeds PCM range; normalization is prohibited")
    return merged


def write_pcm16(path: Path, audio: np.ndarray) -> dict[str, Any]:
    sf.write(path, audio, EXPECTED_SAMPLE_RATE_HZ, subtype="PCM_16", format="WAV")
    info = sf.info(path)
    if info.samplerate != EXPECTED_SAMPLE_RATE_HZ or info.channels != 1 or info.subtype != "PCM_16":
        raise ValueError("serialized WAV does not match the mono PCM16 contract")
    return {
        **bind_file(path, "serialized WAV"),
        "sample_rate_hz": info.samplerate,
        "channels": info.channels,
        "subtype": info.subtype,
        "sample_count": info.frames,
        "duration_seconds": info.frames / info.samplerate,
    }


def package_candidate(raw_audio: np.ndarray) -> tuple[np.ndarray | None, int]:
    raw_samples = int(raw_audio.size)
    if raw_samples > EXPECTED_SAMPLE_COUNT:
        return None, 0
    padding = EXPECTED_SAMPLE_COUNT - raw_samples
    if padding == 0:
        return raw_audio.copy(), 0
    return np.pad(raw_audio, (0, padding), mode="constant", constant_values=0), padding


def build_control_contract(args: argparse.Namespace, speeds: tuple[float, ...]) -> dict[str, Any]:
    if args.text != EXPECTED_TEXT:
        raise ValueError("dialogue text differs from the immutable audition line")
    if args.seed != EXPECTED_SEED:
        raise ValueError("seed differs from the immutable audition seed")
    if args.character_id != "C01" or args.line_id != "L001":
        raise ValueError("character or line identifier differs from the audition contract")
    if args.delivery_style != "focused" or args.intensity != "controlled":
        raise ValueError("delivery style or intensity differs from the audition contract")
    return {
        "contract_version": 1,
        "character_id": args.character_id,
        "line_id": args.line_id,
        "text": args.text,
        "emotion_class": None,
        "delivery_style": args.delivery_style,
        "intensity": args.intensity,
        "duration_target_seconds": EXPECTED_DURATION_SECONDS,
        "sample_rate_hz": EXPECTED_SAMPLE_RATE_HZ,
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "speeds": list(speeds),
        "candidate_count": len(speeds),
        "seed": args.seed,
        "engine": "kokoro",
        "engine_version": EXPECTED_PACKAGES["kokoro"],
        "model_revision": EXPECTED_MODEL_REVISION,
        "voice": "af_heart",
        "voice_identity_policy": "designed_synthetic_voice",
        "retry_allowed": False,
        "adaptive_speed_tuning_allowed": False,
        "truncation_allowed": False,
        "time_stretch_allowed": False,
        "loudness_normalization_allowed": False,
        "trailing_silence_padding_allowed": True,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    speeds = parse_speeds(args.speeds)
    model_path = Path(args.model).resolve()
    config_path = Path(args.config).resolve()
    voice_path = Path(args.voice).resolve()
    assets = {
        "model": bind_file(model_path, "Kokoro model", EXPECTED_ASSETS["model"]),
        "config": bind_file(config_path, "Kokoro config", EXPECTED_ASSETS["config"]),
        "voice": bind_file(voice_path, "Kokoro voice", EXPECTED_ASSETS["voice"]),
    }
    packages = runtime_package_identity()
    contract = build_control_contract(args, speeds)
    output_dir = prepare_output_dir(Path(args.output_dir).resolve())
    contract_bytes = (json.dumps(contract, indent=2, sort_keys=True) + "\n").encode("utf-8")
    contract_path = output_dir / "audition_control_contract.json"
    contract_path.write_bytes(contract_bytes)

    from kokoro import KModel, KPipeline

    set_seed(args.seed)
    model = KModel(config=str(config_path), model=str(model_path))
    pipeline = KPipeline(lang_code="a", repo_id=None, model=model, device="cpu")
    candidates: list[dict[str, Any]] = []
    for ordinal, speed in enumerate(speeds, start=1):
        set_seed(args.seed)
        raw_audio = collect_audio(pipeline(args.text, voice=str(voice_path), speed=speed))
        raw_name = f"L001_C01_kokoro_speed_{speed:.2f}_raw.wav"
        raw_binding = write_pcm16(output_dir / raw_name, raw_audio)
        packaged_audio, padding_samples = package_candidate(raw_audio)
        packaged_binding = None
        timing_pass = packaged_audio is not None
        if packaged_audio is not None:
            packaged_name = f"L001_C01_kokoro_speed_{speed:.2f}_pcm3s.wav"
            packaged_binding = write_pcm16(output_dir / packaged_name, packaged_audio)
            if packaged_binding["sample_count"] != EXPECTED_SAMPLE_COUNT:
                raise ValueError("packaged candidate does not contain exactly 72,000 samples")
        candidates.append(
            {
                "candidate_id": f"KOKORO-C01-L001-{ordinal:02d}",
                "ordinal": ordinal,
                "speed": speed,
                "raw_audio": raw_binding,
                "packaged_audio": packaged_binding,
                "raw_sample_count": raw_binding["sample_count"],
                "padding_samples": padding_samples,
                "packaged_sample_count": packaged_binding["sample_count"] if packaged_binding else None,
                "timing_packaging_pass": timing_pass,
                "speech_truncated": False,
                "time_stretched": False,
                "loudness_normalized": False,
                "retry_count": 0,
            }
        )

    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_kokoro_dialogue_audition_manifest",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "status": "PASS_BOUNDED_AUDITION_GENERATED_AUTOMATED_EVALUATION_PENDING",
        "classification": "KOKORO_THREE_SPEED_IMMUTABLE_AUDITION_GENERATED",
        "runner": bind_file(Path(__file__).resolve(), "runner script"),
        "control_contract": {**contract, "binding": bind_file(contract_path, "control contract")},
        "assets": assets,
        "runtime_identity": packages,
        "candidates": candidates,
        "acceptance": {
            "exact_asset_hashes_pass": True,
            "runtime_package_identity_pass": True,
            "predeclared_three_candidate_batch_pass": True,
            "no_retry_pass": True,
            "no_truncation_pass": True,
            "no_time_stretch_pass": True,
            "no_loudness_normalization_pass": True,
            "automated_candidate_acceptance_pass": None,
            "human_playback_review_pass": False,
            "production_authority_pass": False,
        },
        "boundaries": {
            "designed_synthetic_voice_not_human_reference": True,
            "emotion_class_forced_mapping_performed": False,
            "media_regenerated_outside_declared_batch": False,
            "ec2_started": False,
            "s3_mutated": False,
            "mask_truth_consumed": False,
            "wave71_activated": False,
            "jira_mutated": False,
            "promotion_claimed": False,
        },
        "row_complete": False,
    }
    manifest_path = output_dir / "kokoro_audition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**manifest, "manifest_binding": bind_file(manifest_path, "audition manifest")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--text", default=EXPECTED_TEXT)
    parser.add_argument("--speeds", nargs=3, default=[str(value) for value in EXPECTED_SPEEDS])
    parser.add_argument("--seed", type=int, default=EXPECTED_SEED)
    parser.add_argument("--character-id", default="C01")
    parser.add_argument("--line-id", default="L001")
    parser.add_argument("--delivery-style", default="focused")
    parser.add_argument("--intensity", default="controlled")
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": result["status"], "manifest": result["manifest_binding"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
