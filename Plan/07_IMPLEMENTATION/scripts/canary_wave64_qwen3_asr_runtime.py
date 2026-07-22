#!/usr/bin/env python3
"""Run one offline, hash-bound Qwen3-ASR current-pod transcription canary."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


MODEL_REVISION = "7278e1e70fe206f11671096ffdd38061171dd6e5"
MODEL_MANIFEST_SHA256 = "e733f6863ecf6e3cd2d5579cd50c6e8cd35c78739316757633ad70c879edba60"


class CanaryError(RuntimeError):
    """Raised when the admitted runtime boundary is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_transcript(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9']+", " ", value.lower()).split())


def evaluate_transcript(observed: str, expected_phrase: str) -> dict[str, Any]:
    normalized_observed = normalize_transcript(observed)
    normalized_expected = normalize_transcript(expected_phrase)
    passed = bool(normalized_expected) and normalized_expected in normalized_observed
    return {
        "expected_normalized": normalized_expected,
        "observed_normalized": normalized_observed,
        "expected_phrase_present": passed,
        "disposition": "PASS_EXPECTED_TRANSCRIPT_PRESENT" if passed else "FAIL_EXPECTED_TRANSCRIPT_ABSENT",
    }


def validate_inputs(
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
) -> dict[str, Any]:
    if not model_root.is_dir() or model_root.is_symlink():
        raise CanaryError("model root is absent or unsafe")
    receipt_path = model_root / ".w64_aqa_install_receipt.json"
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise CanaryError("verified model installation receipt is absent")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("manifest_sha256") != MODEL_MANIFEST_SHA256:
        raise CanaryError("model installation manifest identity mismatch")
    if receipt.get("source_revision") != MODEL_REVISION:
        raise CanaryError("model source revision mismatch")
    if not audio_path.is_file() or audio_path.is_symlink():
        raise CanaryError("audio fixture is absent or unsafe")
    observed_audio_sha256 = sha256_file(audio_path)
    if observed_audio_sha256 != expected_audio_sha256:
        raise CanaryError("audio fixture SHA-256 mismatch")
    return {
        "model_receipt": receipt_path.as_posix(),
        "model_manifest_sha256": receipt["manifest_sha256"],
        "model_revision": receipt["source_revision"],
        "audio_sha256": observed_audio_sha256,
        "audio_bytes": audio_path.stat().st_size,
    }


def gpu_snapshot() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    rows = [row.strip() for row in completed.stdout.splitlines() if row.strip()]
    if len(rows) != 1:
        raise CanaryError("exactly one current-pod GPU is required")
    name, total, used, free, utilization = [part.strip() for part in rows[0].split(",")]
    return {
        "name": name,
        "total_mib": int(total),
        "used_mib": int(used),
        "free_mib": int(free),
        "utilization_percent": int(utilization),
    }


def host_memory_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise CanaryError("MemAvailable is absent")


def run_canary(
    *,
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
    expected_phrase: str,
    max_new_tokens: int,
) -> tuple[dict[str, Any], int]:
    identity = validate_inputs(model_root, audio_path, expected_audio_sha256)
    if max_new_tokens < 1 or max_new_tokens > 256:
        raise CanaryError("max_new_tokens must be between 1 and 256")
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    before = gpu_snapshot()
    host_before = host_memory_available_bytes()
    started = time.monotonic()
    model = None
    result = None
    error = None
    loaded = None
    inferred = None
    load_seconds = None
    inference_seconds = None
    versions: dict[str, str] = {}
    try:
        import torch
        from qwen_asr import Qwen3ASRModel

        versions = {"torch": torch.__version__}
        load_started = time.monotonic()
        model = Qwen3ASRModel.from_pretrained(
            str(model_root),
            dtype=torch.bfloat16,
            device_map="cuda:0",
            max_inference_batch_size=1,
            max_new_tokens=max_new_tokens,
        )
        torch.cuda.synchronize()
        load_seconds = time.monotonic() - load_started
        loaded = gpu_snapshot()
        inference_started = time.monotonic()
        results = model.transcribe(audio=str(audio_path), language=None)
        torch.cuda.synchronize()
        inference_seconds = time.monotonic() - inference_started
        inferred = gpu_snapshot()
        if len(results) != 1:
            raise CanaryError("transcription returned an unexpected result count")
        result = {
            "language": str(results[0].language),
            "text": str(results[0].text),
            "gate": evaluate_transcript(str(results[0].text), expected_phrase),
        }
    except Exception as exc:  # noqa: BLE001 - runtime failures must become retained evidence.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if model is not None:
            del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception:  # noqa: BLE001 - cleanup evidence records the final GPU state.
            pass
    after = gpu_snapshot()
    cleanup_delta_mib = after["used_mib"] - before["used_mib"]
    cleanup_pass = cleanup_delta_mib <= 1024
    transcript_pass = bool(result and result["gate"]["expected_phrase_present"])
    passed = error is None and cleanup_pass and transcript_pass
    evidence = {
        "schema_version": "wave64.aqa.qwen3_asr_runtime_canary.v1",
        "program_id": "W64-AQA",
        "package_id": "W64-AQA-PKG-QWEN3-ASR-17B",
        "status": "PASS_RUNTIME_TRANSCRIPT_AND_CLEANUP" if passed else "FAIL_RUNTIME_OR_TRANSCRIPT_OR_CLEANUP",
        "identity": identity,
        "offline_policy": {
            "local_model_path_only": True,
            "local_audio_path_only": True,
            "hub_offline": True,
            "service_binding": False,
            "external_inference": False,
        },
        "runtime": {
            "device_map": "cuda:0",
            "dtype": "bfloat16",
            "max_inference_batch_size": 1,
            "max_new_tokens": max_new_tokens,
            "duration_seconds": time.monotonic() - started,
            "load_seconds": load_seconds,
            "inference_seconds": inference_seconds,
            "host_memory_available_before_bytes": host_before,
            "gpu_before": before,
            "gpu_loaded": loaded,
            "gpu_after_inference": inferred,
            "gpu_after_cleanup": after,
            "cleanup_delta_mib": cleanup_delta_mib,
            "cleanup_pass": cleanup_pass,
            "versions": versions,
        },
        "transcription": result,
        "error": error,
        "authority": {
            "runtime_capacity": passed,
            "exact_fixture_transcription": passed,
            "general_asr_quality": False,
            "forced_alignment": False,
            "semantic_audio_quality": False,
            "product_promotion": False,
        },
    }
    return evidence, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--expected-phrase", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    try:
        evidence, exit_code = run_canary(
            model_root=args.model_root,
            audio_path=args.audio,
            expected_audio_sha256=args.expected_audio_sha256,
            expected_phrase=args.expected_phrase,
            max_new_tokens=args.max_new_tokens,
        )
    except (CanaryError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "output": str(args.output)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
