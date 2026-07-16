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
EXPECTED_MODEL_FILES = {
    "config.json": (4421, "aecd2cc4c1fe9edef1cb7ca7c401685a43879ad43f3f9e883f1c6760b61731e0"),
    "generation_config.json": (245, "f1b90b4513f3b34c62851049e2492d7b4c5940daf1276f89c82b8ef04127f3aa"),
    "merges.txt": (1671839, "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"),
    "model.safetensors": (3833402552, "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522"),
    "preprocessor_config.json": (127, "efdde1022ea9d76928bf7a9cd53139138f5ba2e466e837f08f6105ab1af1c119"),
    "speech_tokenizer/config.json": (2336, "ee65bb901c876664ab8707c487157aa1a6ee57c65969b28fb5ec9dc211e68167"),
    "speech_tokenizer/configuration.json": (76, "6bc26d64eb5024b4d1dab5a52371958b429256d6c9d59787f1f5294a54e0cebd"),
    "speech_tokenizer/model.safetensors": (682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258"),
    "speech_tokenizer/preprocessor_config.json": (234, "fcb3805e597e786d4067706e602f6688524640f8d3396790e2e09b5942fcbdfb"),
    "tokenizer_config.json": (7344, "dc3c31c3bdaedd5016382bb3cbe07323026775ad51f5a4fb564505992ae4a670"),
    "vocab.json": (2776833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
}
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
VOICE_INSTRUCTION = (
    "A natural adult female American English voice. Calm and focused, with controlled low intensity, "
    "clear articulation, and steady medium-fast pacing near 200 words per minute. Subtly emphasize "
    "the words steady and beat. Complete every word without rushing or trailing off."
)


class CandidateError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise CandidateError(f"JSON root must be an object: {path}")
    return value


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise CandidateError(f"immutable output already exists: {path}")
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


def validate_plan(plan: dict[str, Any]) -> str:
    if plan.get("generation_executed") is not False or plan.get("production_ready") is not False:
        raise CandidateError("planning artifact truth boundary is invalid")
    if plan.get("pronunciation", {}).get("pass") is not True:
        raise CandidateError("pronunciation plan is not pass-like")
    if plan.get("duration", {}).get("pass") is not True:
        raise CandidateError("duration plan is not pass-like")
    if plan.get("duration", {}).get("spoken_content_trim_allowed") is not False:
        raise CandidateError("duration plan permits spoken-content trimming")
    if plan.get("performance", {}).get("taxonomy_conflation") is not False:
        raise CandidateError("performance plan conflates control taxonomies")
    text = str(plan.get("normalization", {}).get("normalized_text", "")).strip()
    if not text:
        raise CandidateError("normalized synthesis text is empty")
    return text


def verify_model_files(model_dir: Path) -> list[dict[str, Any]]:
    results = []
    for relative, (expected_bytes, expected_hash) in EXPECTED_MODEL_FILES.items():
        path = model_dir / relative
        if not path.is_file() or path.stat().st_size != expected_bytes:
            raise CandidateError(f"model file size mismatch: {relative}")
        digest = sha256_file(path)
        if digest != expected_hash:
            raise CandidateError(f"model file hash mismatch: {relative}")
        results.append({"path": f"models/audio/tts/qwen3_tts_1_7b_voicedesign/{relative}", "bytes": expected_bytes, "sha256": digest})
    return results


def verify_packages(site_packages: Path) -> dict[str, str]:
    sys.path.insert(0, str(site_packages))
    observed = {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
    if observed != EXPECTED_PACKAGES:
        raise CandidateError(f"runtime package identity drift: {observed}")
    return observed


def candidate_paths(output_dir: Path, seed: int) -> tuple[Path, Path]:
    stem = f"qwen3_tts_voicedesign_seed{seed}"
    return output_dir / f"{stem}.wav", output_dir / f"{stem}.manifest.json"


def run(model_dir: Path, site_packages: Path, plan_path: Path, output_dir: Path, seed: int) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch

    plan = load_json(plan_path)
    text = validate_plan(plan)
    wav_path, manifest_path = candidate_paths(output_dir, seed)
    if wav_path.exists() or manifest_path.exists():
        raise CandidateError("immutable candidate seed output already exists")
    model_files = verify_model_files(model_dir)
    packages = verify_packages(site_packages)
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
    wavs, sample_rate = model.generate_voice_design(
        text=text,
        language="English",
        instruct=VOICE_INSTRUCTION,
        **GENERATION,
    )
    generated = time.perf_counter()
    if len(wavs) != 1:
        raise CandidateError(f"expected one generated waveform, observed {len(wavs)}")
    waveform = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
    if not waveform.size or not np.isfinite(waveform).all():
        raise CandidateError("generated waveform is empty or non-finite")
    peak = float(np.max(np.abs(waveform)))
    if peak > 1.0:
        waveform = waveform / peak
    output_dir.mkdir(parents=True, exist_ok=True)
    sf.write(wav_path, waveform, sample_rate, subtype="PCM_16")
    if not wav_path.is_file():
        raise CandidateError("candidate WAV write failed")
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_voicedesign_candidate_manifest",
        "created_at": now_iso(),
        "classification": "QWEN3_TTS_GENUINE_CANDIDATE_GENERATED_AUTOMATED_QA_PENDING",
        "candidate_id": f"W64-QWEN3-VOICE-DESIGN-SEED-{seed}",
        "plan": {"path": "Plan/10_REGISTRIES/wave64_dialogue_synthesis_plan_registry.json", "sha256": sha256_file(plan_path)},
        "engine": {
            "repository": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "revision": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
            "model_files": model_files,
            "packages": packages,
            "torch": torch.__version__,
            "device": torch.cuda.get_device_name(0),
            "dtype": "bfloat16",
            "attention": "eager",
        },
        "request": {
            "text": text,
            "language": "English",
            "voice_instruction": VOICE_INSTRUCTION,
            "seed": seed,
            "generation_parameters": GENERATION,
        },
        "output": {
            "path": str(wav_path.resolve()),
            "sha256": sha256_file(wav_path),
            "bytes": wav_path.stat().st_size,
            "sample_rate_hz": sample_rate,
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
            "playback_review_complete": False,
            "production_ready": False,
            "rejected_candidate_rerun": False,
            "content_based_suppression": False,
        },
    }
    write_json_new(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    manifest = run(args.model_dir.resolve(), args.site_packages.resolve(), args.plan.resolve(), args.output_dir.resolve(), args.seed)
    print(json.dumps({"classification": manifest["classification"], "candidate_id": manifest["candidate_id"], "output": manifest["output"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
