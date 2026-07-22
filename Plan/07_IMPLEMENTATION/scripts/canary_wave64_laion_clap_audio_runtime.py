#!/usr/bin/env python3
"""Run one offline, hash-bound LAION CLAP current-pod audio canary."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path
from typing import Any


PACKAGE_ID = "W64-AQA-PKG-LAION-CLAP-GENERAL"
UPSTREAM_REPOSITORY = "laion/larger_clap_general"
UPSTREAM_REVISION = "ada0c23a36c4e8582805bb38fec3905903f18b41"
EXPECTED_FILES: dict[str, tuple[int, str]] = {
    ".cache/huggingface/.gitignore": (
        1,
        "684888c0ebb17f374298b65ee2807526c066094c701bcc7ebbe1c1095f494fc1",
    ),
    ".cache/huggingface/download/config.json.metadata": (
        103,
        "ed06c93ed750135074067abde62ec2c87a6c201199b689dc5c89f28efa76083d",
    ),
    ".cache/huggingface/download/merges.txt.metadata": (
        104,
        "84a9a375bf410021e5d207018bca0c4874487e0132a65dbb3d846646d4b3da85",
    ),
    ".cache/huggingface/download/preprocessor_config.json.metadata": (
        104,
        "1651b3eaa9a39ac5840b90af753c3757d6a0cc27d3febcf1fb205e5505d147de",
    ),
    ".cache/huggingface/download/pytorch_model.bin.metadata": (
        128,
        "abf75a5801acf3805b9de2b1c6cbcfaa0439628f4d03f494c4d90368e45cbe97",
    ),
    ".cache/huggingface/download/special_tokens_map.json.metadata": (
        104,
        "8e8d1c3343359997110f0322dde379848352c28940e86ac9e2e66310e3990769",
    ),
    ".cache/huggingface/download/tokenizer_config.json.metadata": (
        104,
        "c2833a6ee39e6eefa66425de4e25878944fa0fd2db6fb9939a8b75e416e46104",
    ),
    ".cache/huggingface/download/vocab.json.metadata": (
        104,
        "2a83eaa0f45656989f7e2bab91dd3f1eeb585109b4222bfc7c8e681ed545ef1b",
    ),
    "config.json": (
        643,
        "6268f76a067e3104bf9001e97d7dcc0fcfb16f3086cfb478ee72d95900d7fc1d",
    ),
    "merges.txt": (
        456318,
        "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
    ),
    "preprocessor_config.json": (
        541,
        "9739f58296aa6f9ac18008fd0150fb2649bc554985fbde86d0a4041c882ac753",
    ),
    "pytorch_model.bin": (
        776444665,
        "314eb00cce6ad68d25237b8446b659ccdb136ed4672c1bca470f142f72455026",
    ),
    "special_tokens_map.json": (
        280,
        "06e405a36dfe4b9604f484f6a1e619af1a7f7d09e34a8555eb0b77b66318067f",
    ),
    "tokenizer_config.json": (
        1362,
        "e2eb445cfdbf4711de620cbdf10478b0423950799e85652d9f28da47066ab86d",
    ),
    "vocab.json": (
        798293,
        "ed19656ea1707df69134c4af35c8ceda2cc9860bf2c3495026153a133670ab5e",
    ),
}
TEXT_LABELS = (
    "a person speaking clearly",
    "instrumental music",
    "mechanical engine noise",
    "silence",
)
EXPECTED_TOP_LABEL = TEXT_LABELS[0]


class CanaryError(RuntimeError):
    """Raised when the admitted package, fixture, or runtime boundary is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_package(model_root: Path) -> dict[str, Any]:
    if not model_root.is_dir() or model_root.is_symlink():
        raise CanaryError("model root is absent or unsafe")
    observed: dict[str, Path] = {}
    for path in model_root.rglob("*"):
        if path.is_symlink():
            raise CanaryError(f"model package symlink is forbidden: {path}")
        if path.is_file():
            observed[path.relative_to(model_root).as_posix()] = path
    missing = sorted(set(EXPECTED_FILES) - set(observed))
    extra = sorted(set(observed) - set(EXPECTED_FILES))
    if missing or extra:
        raise CanaryError(f"model package file-set mismatch: missing={missing}; extra={extra}")
    members: list[dict[str, Any]] = []
    for relative_path in sorted(EXPECTED_FILES):
        expected_bytes, expected_sha256 = EXPECTED_FILES[relative_path]
        path = observed[relative_path]
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            raise CanaryError(f"model package byte-count mismatch: {relative_path}")
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            raise CanaryError(f"model package SHA-256 mismatch: {relative_path}")
        members.append(
            {"path": relative_path, "bytes": actual_bytes, "sha256": actual_sha256}
        )
    return {
        "package_id": PACKAGE_ID,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_revision": UPSTREAM_REVISION,
        "file_count": len(members),
        "total_bytes": sum(member["bytes"] for member in members),
        "aggregate_manifest_sha256": canonical_sha256(members),
        "members": members,
    }


def validate_audio(audio_path: Path, expected_audio_sha256: str) -> dict[str, Any]:
    if not audio_path.is_file() or audio_path.is_symlink():
        raise CanaryError("audio fixture is absent or unsafe")
    observed_sha256 = sha256_file(audio_path)
    if observed_sha256 != expected_audio_sha256:
        raise CanaryError("audio fixture SHA-256 mismatch")
    return {
        "path": audio_path.as_posix(),
        "bytes": audio_path.stat().st_size,
        "sha256": observed_sha256,
    }


def decode_pcm16_wave_mono(audio_path: Path) -> tuple[list[float], int, dict[str, int]]:
    try:
        with wave.open(str(audio_path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            compression = handle.getcomptype()
            raw = handle.readframes(frame_count)
    except (wave.Error, OSError) as exc:
        raise CanaryError(f"audio fixture wave decode failed: {exc}") from exc
    if compression != "NONE" or sample_width != 2 or channels not in {1, 2}:
        raise CanaryError("audio fixture must be mono/stereo uncompressed PCM16 wave")
    expected_bytes = frame_count * channels * sample_width
    if len(raw) != expected_bytes or frame_count < 1:
        raise CanaryError("audio fixture PCM payload is incomplete")
    samples: list[float] = []
    stride = channels * 2
    for offset in range(0, len(raw), stride):
        channel_values = [
            int.from_bytes(raw[offset + (index * 2) : offset + (index * 2) + 2], "little", signed=True)
            for index in range(channels)
        ]
        samples.append(sum(channel_values) / (channels * 32768.0))
    return samples, sample_rate, {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
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


def cosine_similarity(left: Any, right: Any) -> float:
    numerator = float((left * right).sum().item())
    denominator = math.sqrt(float((left * left).sum().item())) * math.sqrt(
        float((right * right).sum().item())
    )
    if denominator <= 0:
        raise CanaryError("zero-norm CLAP embedding")
    return numerator / denominator


def prepare_audio_inputs(
    processor: Any, samples: list[float], sample_rate: int
) -> dict[str, Any]:
    """Use the exact CLAP processor audio keyword pinned by Transformers 4.46.3."""
    return processor(
        audios=[samples], sampling_rate=sample_rate, return_tensors="pt", padding=True
    )


def evaluate_embedding_gate(
    first_audio: Any, second_audio: Any, text_embeddings: Any
) -> dict[str, Any]:
    if tuple(first_audio.shape) != (1, 512) or tuple(second_audio.shape) != (1, 512):
        raise CanaryError("CLAP audio embedding dimension mismatch")
    if tuple(text_embeddings.shape) != (len(TEXT_LABELS), 512):
        raise CanaryError("CLAP text embedding dimension mismatch")
    repeat_delta = float((first_audio - second_audio).abs().max().item())
    scores = [
        cosine_similarity(first_audio[0], text_embeddings[index])
        for index in range(len(TEXT_LABELS))
    ]
    top_index = max(range(len(scores)), key=scores.__getitem__)
    runner_up = max(score for index, score in enumerate(scores) if index != top_index)
    expected_top = top_index == 0
    deterministic = repeat_delta <= 1e-6
    finite = all(math.isfinite(value) for value in scores + [repeat_delta])
    passed = expected_top and deterministic and finite
    return {
        "labels": list(TEXT_LABELS),
        "cosine_similarities": scores,
        "top_label": TEXT_LABELS[top_index],
        "expected_top_label": EXPECTED_TOP_LABEL,
        "expected_top_label_pass": expected_top,
        "top_margin": scores[top_index] - runner_up,
        "repeat_max_abs_delta": repeat_delta,
        "repeat_tolerance": 1e-6,
        "determinism_pass": deterministic,
        "finite_values_pass": finite,
        "vector_dimension": 512,
        "passed": passed,
        "disposition": (
            "PASS_EXACT_FIXTURE_SPEECH_LABEL_AND_DETERMINISM"
            if passed
            else "FAIL_EXACT_FIXTURE_SPEECH_LABEL_OR_DETERMINISM"
        ),
    }


def run_worker(
    *, model_root: Path, audio_path: Path, expected_audio_sha256: str
) -> tuple[dict[str, Any], int]:
    package = validate_package(model_root)
    audio = validate_audio(audio_path, expected_audio_sha256)
    samples, sample_rate, wave_metadata = decode_pcm16_wave_mono(audio_path)
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
    started = time.monotonic()
    model = None
    gate = None
    loaded = None
    inferred = None
    load_seconds = None
    inference_seconds = None
    versions: dict[str, str] = {}
    error = None
    try:
        import torch
        import transformers
        from transformers import ClapModel, ClapProcessor

        if not torch.cuda.is_available():
            raise CanaryError("CUDA is required for current-pod qualification")
        versions = {"torch": torch.__version__, "transformers": transformers.__version__}
        load_started = time.monotonic()
        processor = ClapProcessor.from_pretrained(str(model_root), local_files_only=True)
        model = ClapModel.from_pretrained(str(model_root), local_files_only=True)
        model.to("cuda:0")
        model.eval()
        torch.cuda.synchronize()
        load_seconds = time.monotonic() - load_started
        loaded = gpu_snapshot()
        inference_started = time.monotonic()
        audio_inputs = prepare_audio_inputs(processor, samples, sample_rate)
        audio_inputs = {key: value.to("cuda:0") for key, value in audio_inputs.items()}
        text_inputs = processor(text=list(TEXT_LABELS), return_tensors="pt", padding=True)
        text_inputs = {key: value.to("cuda:0") for key, value in text_inputs.items()}
        with torch.inference_mode():
            first_audio = model.get_audio_features(**audio_inputs)
            second_audio = model.get_audio_features(**audio_inputs)
            text_embeddings = model.get_text_features(**text_inputs)
            first_audio = torch.nn.functional.normalize(first_audio, dim=-1)
            second_audio = torch.nn.functional.normalize(second_audio, dim=-1)
            text_embeddings = torch.nn.functional.normalize(text_embeddings, dim=-1)
        torch.cuda.synchronize()
        inference_seconds = time.monotonic() - inference_started
        inferred = gpu_snapshot()
        gate = evaluate_embedding_gate(first_audio, second_audio, text_embeddings)
    except Exception as exc:  # noqa: BLE001 - runtime failure must become retained evidence.
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
        except Exception:  # noqa: BLE001 - final process-exit cleanup is authoritative.
            pass
    after = gpu_snapshot()
    in_process_delta_mib = after["used_mib"] - before["used_mib"]
    passed = error is None and bool(gate and gate["passed"])
    evidence = {
        "schema_version": "wave64.aqa.laion_clap_audio_runtime_canary.v1",
        "program_id": "W64-AQA",
        "package": package,
        "fixture": {**audio, **wave_metadata},
        "status": "PASS_EXACT_FIXTURE_RUNTIME" if passed else "FAIL_RUNTIME_OR_FIXTURE_GATE",
        "offline_policy": {
            "local_model_path_only": True,
            "local_audio_path_only": True,
            "hub_offline": True,
            "external_inference": False,
            "service_binding": False,
        },
        "runtime": {
            "device": "cuda:0",
            "dtype": "float32",
            "duration_seconds": time.monotonic() - started,
            "load_seconds": load_seconds,
            "inference_seconds": inference_seconds,
            "gpu_before": before,
            "gpu_loaded": loaded,
            "gpu_after_inference": inferred,
            "gpu_after_in_process_cleanup": after,
            "in_process_cleanup_delta_mib": in_process_delta_mib,
            "versions": versions,
        },
        "embedding_gate": gate,
        "error": error,
        "authority": {
            "package_identity": True,
            "current_pod_runtime_capacity": passed,
            "exact_fixture_speech_event": passed,
            "exact_fixture_embedding_determinism": passed,
            "general_audio_semantic_quality": False,
            "speaker_identity": False,
            "forced_alignment": False,
            "av_sync": False,
            "independent_juror": False,
            "product_promotion": False,
        },
    }
    return evidence, 0 if passed else 1


def finalize_process_exit_cleanup(
    evidence: dict[str, Any],
    *,
    gpu_before_worker: dict[str, Any],
    gpu_after_worker_exit: dict[str, Any],
    worker_returncode: int,
    worker_stdout: str,
    worker_stderr: str,
) -> tuple[dict[str, Any], int]:
    delta_mib = gpu_after_worker_exit["used_mib"] - gpu_before_worker["used_mib"]
    cleanup_pass = delta_mib <= 1024
    evidence["runtime"].update(
        {
            "gpu_before_worker_process": gpu_before_worker,
            "gpu_after_worker_process_exit": gpu_after_worker_exit,
            "process_exit_cleanup_delta_mib": delta_mib,
            "process_exit_cleanup_pass": cleanup_pass,
            "cleanup_boundary": "isolated_worker_process_exit",
            "worker_returncode": worker_returncode,
            "worker_stdout": worker_stdout[-4000:],
            "worker_stderr": worker_stderr[-4000:],
        }
    )
    gate = evidence.get("embedding_gate")
    gate_pass = bool(isinstance(gate, dict) and gate.get("passed"))
    worker_completed = worker_returncode in {0, 1} and evidence.get("error") is None
    passed = worker_completed and gate_pass and cleanup_pass
    evidence["schema_version"] = "wave64.aqa.laion_clap_audio_runtime_canary.v2"
    evidence["status"] = (
        "PASS_EXACT_FIXTURE_RUNTIME_AND_PROCESS_EXIT_CLEANUP"
        if passed
        else "FAIL_RUNTIME_FIXTURE_GATE_OR_PROCESS_EXIT_CLEANUP"
    )
    evidence["authority"]["current_pod_runtime_capacity"] = passed
    evidence["authority"]["exact_fixture_speech_event"] = gate_pass
    evidence["authority"]["exact_fixture_embedding_determinism"] = gate_pass
    return evidence, 0 if passed else 1


def run_isolated_canary(
    *,
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
    output_path: Path,
) -> tuple[dict[str, Any], int]:
    validate_package(model_root)
    validate_audio(audio_path, expected_audio_sha256)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    worker_output = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.worker"
    gpu_before_worker = gpu_snapshot()
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--inner-worker",
        "--model-root",
        str(model_root),
        "--audio",
        str(audio_path),
        "--expected-audio-sha256",
        expected_audio_sha256,
        "--output",
        str(worker_output),
    ]
    completed = subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=600
    )
    try:
        if not worker_output.is_file():
            raise CanaryError(
                "isolated CLAP worker did not emit evidence; "
                f"returncode={completed.returncode}; stderr={completed.stderr[-1000:]}"
            )
        evidence = json.loads(worker_output.read_text(encoding="utf-8"))
    finally:
        worker_output.unlink(missing_ok=True)
    time.sleep(2)
    return finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker=gpu_before_worker,
        gpu_after_worker_exit=gpu_snapshot(),
        worker_returncode=completed.returncode,
        worker_stdout=completed.stdout,
        worker_stderr=completed.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    try:
        runner = run_worker if args.inner_worker else run_isolated_canary
        runner_args: dict[str, Any] = {
            "model_root": args.model_root,
            "audio_path": args.audio,
            "expected_audio_sha256": args.expected_audio_sha256,
        }
        if not args.inner_worker:
            runner_args["output_path"] = args.output
        evidence, exit_code = runner(**runner_args)
    except (CanaryError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": evidence["status"], "output": str(args.output)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
