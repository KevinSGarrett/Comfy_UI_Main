#!/usr/bin/env python3
"""Generate one immutable Qwen3-TTS Base ICL voice-clone candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_PACKAGES = {
    "qwen-tts": "0.1.1",
    "transformers": "4.57.3",
    "accelerate": "1.12.0",
    "huggingface-hub": "0.36.2",
    "sox": "1.5.0",
}
EXPECTED_RUNTIME_PACKAGES = {"torch": "2.11.0+cu128", "torchaudio": "2.11.0+cu128"}
EXPECTED_MODEL_FILES = {
    "config.json": (4494, "b4f01752d15a488abde3e1ab44723ae4f4b9e68a4037257b098b3737893cc1f9"),
    "generation_config.json": (245, "f1b90b4513f3b34c62851049e2492d7b4c5940daf1276f89c82b8ef04127f3aa"),
    "merges.txt": (1671839, "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"),
    "model.safetensors": (3857413744, "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c"),
    "preprocessor_config.json": (127, "efdde1022ea9d76928bf7a9cd53139138f5ba2e466e837f08f6105ab1af1c119"),
    "speech_tokenizer/config.json": (2336, "ee65bb901c876664ab8707c487157aa1a6ee57c65969b28fb5ec9dc211e68167"),
    "speech_tokenizer/configuration.json": (76, "6bc26d64eb5024b4d1dab5a52371958b429256d6c9d59787f1f5294a54e0cebd"),
    "speech_tokenizer/model.safetensors": (682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258"),
    "speech_tokenizer/preprocessor_config.json": (234, "fcb3805e597e786d4067706e602f6688524640f8d3396790e2e09b5942fcbdfb"),
    "tokenizer_config.json": (7344, "dc3c31c3bdaedd5016382bb3cbe07323026775ad51f5a4fb564505992ae4a670"),
    "vocab.json": (2776833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
}
EXPECTED_REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
REFERENCE_TRANSCRIPT = "Once upon a midnight dreary, while I pondered, weak and weary."
TARGET_TEXT = "We hold the frame steady and move on the beat."
GENERATION = {
    "do_sample": True,
    "top_k": 50,
    "top_p": 1.0,
    "temperature": 0.9,
    "repetition_penalty": 1.05,
    "subtalker_dosample": True,
    "subtalker_top_k": 50,
    "subtalker_top_p": 1.0,
    "subtalker_temperature": 0.9,
    "max_new_tokens": 512,
}


class CloneError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise CloneError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_files(model_dir: Path) -> list[dict[str, Any]]:
    bindings = []
    for relative, (expected_bytes, expected_hash) in EXPECTED_MODEL_FILES.items():
        path = model_dir / relative
        if not path.is_file() or path.stat().st_size != expected_bytes:
            raise CloneError(f"model file size mismatch: {relative}")
        observed = sha256_file(path)
        if observed != expected_hash:
            raise CloneError(f"model file hash mismatch: {relative}")
        bindings.append({"path": relative, "bytes": expected_bytes, "sha256": observed})
    return bindings


def verify_reference(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CloneError(f"reference audio is missing: {path}")
    observed = sha256_file(path)
    if observed != EXPECTED_REFERENCE_SHA256:
        raise CloneError(f"reference audio SHA-256 mismatch: {observed}")
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": observed}


def verify_packages(site_packages: Path) -> dict[str, str]:
    sys.path.insert(0, str(site_packages))
    observed = {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
    if observed != EXPECTED_PACKAGES:
        raise CloneError(f"runtime package identity drift: {observed}")
    return observed


def validate_runtime_versions(observed: dict[str, str]) -> dict[str, str]:
    if observed != EXPECTED_RUNTIME_PACKAGES:
        raise CloneError(f"Torch runtime identity drift: {observed}")
    return observed


def candidate_paths(output_dir: Path, seed: int) -> tuple[Path, Path]:
    stem = f"qwen3_tts_base_icl_clone_seed{seed}"
    return output_dir / f"{stem}.wav", output_dir / f"{stem}.manifest.json"


def run(model_dir: Path, site_packages: Path, reference: Path, output_dir: Path, seed: int) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio

    wav_path, manifest_path = candidate_paths(output_dir, seed)
    if wav_path.exists() or manifest_path.exists():
        raise CloneError("immutable candidate seed output already exists")
    model_files = verify_files(model_dir)
    reference_binding = verify_reference(reference)
    packages = verify_packages(site_packages)
    runtime_packages = validate_runtime_versions(
        {"torch": torch.__version__, "torchaudio": torchaudio.__version__}
    )

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)

    from qwen_tts import Qwen3TTSModel

    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(model_dir),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="eager",
    )
    loaded = time.perf_counter()
    wavs, sample_rate = model.generate_voice_clone(
        text=TARGET_TEXT,
        language="English",
        ref_audio=str(reference),
        ref_text=REFERENCE_TRANSCRIPT,
        x_vector_only_mode=False,
        non_streaming_mode=False,
        **GENERATION,
    )
    generated = time.perf_counter()
    if len(wavs) != 1:
        raise CloneError(f"expected one generated waveform, observed {len(wavs)}")
    waveform = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
    if not waveform.size or not np.isfinite(waveform).all():
        raise CloneError("generated waveform is empty or non-finite")
    peak = float(np.max(np.abs(waveform)))
    if peak > 1.0:
        waveform = waveform / peak
    output_dir.mkdir(parents=True, exist_ok=True)
    sf.write(wav_path, waveform, sample_rate, subtype="PCM_16")
    if sha256_file(wav_path) == reference_binding["sha256"]:
        raise CloneError("generated output duplicates the reference audio")

    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_base_icl_voice_clone_candidate_manifest",
        "created_at": now_iso(),
        "classification": "QWEN3_TTS_BASE_ICL_CLONE_GENERATED_AUTOMATED_QA_PENDING",
        "candidate_id": f"W64-QWEN3-BASE-ICL-CLONE-SEED-{seed}",
        "engine": {
            "repository": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "revision": "fd4b254389122332181a7c3db7f27e918eec64e3",
            "license": "Apache-2.0",
            "model_files": model_files,
            "packages": packages,
            "runtime_packages": runtime_packages,
            "device": torch.cuda.get_device_name(0),
            "dtype": "bfloat16",
            "attention": "eager",
        },
        "request": {
            "text": TARGET_TEXT,
            "language": "English",
            "seed": seed,
            "clone_mode": "icl",
            "x_vector_only_mode": False,
            "non_streaming_mode": False,
            "generation_parameters": GENERATION,
        },
        "reference": {
            **reference_binding,
            "transcript": REFERENCE_TRANSCRIPT,
            "source": "Chris Goringe / LibriVox",
            "rights": "Public Domain Mark 1.0",
            "production_authorized": False,
        },
        "output": {
            "path": str(wav_path.resolve()),
            "sha256": sha256_file(wav_path),
            "bytes": wav_path.stat().st_size,
            "sample_rate_hz": int(sample_rate),
            "samples": int(waveform.size),
            "duration_seconds": round(waveform.size / sample_rate, 9),
            "channels": 1,
            "subtype": "PCM_16",
        },
        "runtime": {
            "load_seconds": round(loaded - started, 3),
            "generation_seconds": round(generated - loaded, 3),
            "total_seconds": round(generated - started, 3),
        },
        "boundaries": {
            "automated_qa_complete": False,
            "speaker_identity_measured": False,
            "independent_playback_review_complete": False,
            "production_ready": False,
            "reference_authorized_for_production": False,
            "candidate_regenerated": False,
            "content_based_suppression": False,
        },
    }
    write_json_new(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    try:
        result = run(
            args.model_dir.resolve(),
            args.site_packages.resolve(),
            args.reference.resolve(),
            args.output_dir.resolve(),
            args.seed,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"classification": result["classification"], "candidate_id": result["candidate_id"], "output": result["output"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
