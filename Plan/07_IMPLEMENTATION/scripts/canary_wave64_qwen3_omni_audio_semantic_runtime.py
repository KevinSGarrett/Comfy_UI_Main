#!/usr/bin/env python3
"""Run one offline, hash-bound Qwen3-Omni audio-semantic review canary."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


MODEL_REVISION = "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b"
MODEL_MANIFEST_SHA256 = "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480"
EXPECTED_PACKAGE_ID = "W64-AQA-PKG-QWEN3-OMNI-30B-A3B"
REQUIRED_SEMANTIC_KEYS = {
    "transcript",
    "language",
    "speech_intelligible",
    "clipping_or_distortion",
    "background_audio",
    "audible_events",
    "quality_observations",
    "semantic_summary",
    "confidence",
}


class CanaryError(RuntimeError):
    """Raised when the admitted runtime or evidence boundary is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9']+", " ", value.lower()).split())


def extract_json_object(value: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(value):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise CanaryError("model response contains no JSON object")


def validate_semantic_payload(
    payload: dict[str, Any], expected_phrase: str
) -> dict[str, Any]:
    missing = sorted(REQUIRED_SEMANTIC_KEYS - payload.keys())
    extra = sorted(payload.keys() - REQUIRED_SEMANTIC_KEYS)
    type_errors: list[str] = []
    for key in (
        "transcript",
        "language",
        "clipping_or_distortion",
        "background_audio",
        "semantic_summary",
    ):
        if not isinstance(payload.get(key), str):
            type_errors.append(f"{key}:string_required")
    if not isinstance(payload.get("speech_intelligible"), bool):
        type_errors.append("speech_intelligible:boolean_required")
    for key in ("audible_events", "quality_observations"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            type_errors.append(f"{key}:string_array_required")
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        type_errors.append("confidence:number_required")
    elif not 0 <= float(confidence) <= 1:
        type_errors.append("confidence:range_0_1_required")
    transcript = payload.get("transcript", "")
    expected_normalized = normalize_text(expected_phrase)
    observed_normalized = normalize_text(transcript) if isinstance(transcript, str) else ""
    phrase_present = bool(expected_normalized) and expected_normalized in observed_normalized
    intelligible = payload.get("speech_intelligible") is True
    passed = not missing and not extra and not type_errors and phrase_present and intelligible
    return {
        "schema_keys_exact": not missing and not extra,
        "missing_keys": missing,
        "extra_keys": extra,
        "type_errors": type_errors,
        "expected_normalized": expected_normalized,
        "observed_transcript_normalized": observed_normalized,
        "expected_phrase_present": phrase_present,
        "speech_intelligible_true": intelligible,
        "disposition": (
            "PASS_EXACT_FIXTURE_STRUCTURED_AUDIO_SEMANTIC_RESPONSE"
            if passed
            else "FAIL_AUDIO_SEMANTIC_RESPONSE_GATE"
        ),
        "passed": passed,
    }


def validate_inputs(
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
    offload_root: Path,
) -> dict[str, Any]:
    if not model_root.is_dir() or model_root.is_symlink():
        raise CanaryError("model root is absent or unsafe")
    receipt_path = model_root / ".w64_aqa_install_receipt.json"
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise CanaryError("verified model installation receipt is absent")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("package_id") != EXPECTED_PACKAGE_ID:
        raise CanaryError("model package identity mismatch")
    if receipt.get("manifest_sha256") != MODEL_MANIFEST_SHA256:
        raise CanaryError("model installation manifest identity mismatch")
    if receipt.get("source_revision") != MODEL_REVISION:
        raise CanaryError("model source revision mismatch")
    if not audio_path.is_file() or audio_path.is_symlink():
        raise CanaryError("audio fixture is absent or unsafe")
    observed_audio_sha256 = sha256_file(audio_path)
    if observed_audio_sha256 != expected_audio_sha256:
        raise CanaryError("audio fixture SHA-256 mismatch")
    if not offload_root.is_dir() or offload_root.is_symlink():
        raise CanaryError("offload root is absent or unsafe")
    return {
        "model_receipt": receipt_path.as_posix(),
        "model_manifest_sha256": receipt["manifest_sha256"],
        "model_revision": receipt["source_revision"],
        "audio_sha256": observed_audio_sha256,
        "audio_bytes": audio_path.stat().st_size,
        "offload_root": offload_root.as_posix(),
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


def summarize_device_map(device_map: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for target in device_map.values():
        key = str(target)
        counts[key] = counts.get(key, 0) + 1
    return {"target_counts": counts, "module_count": len(device_map)}


def build_prompt() -> str:
    return (
        "Review the attached audio. Return ONLY one JSON object with exactly these keys: "
        "transcript (string), language (string), speech_intelligible (boolean), "
        "clipping_or_distortion (string), background_audio (string), audible_events "
        "(array of strings), quality_observations (array of strings), semantic_summary "
        "(string), confidence (number from 0 to 1). Be concise and report only what is "
        "audible; do not add markdown or infer facts that cannot be heard."
    )


def run_worker(
    *,
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
    expected_phrase: str,
    offload_root: Path,
    max_new_tokens: int,
    gpu_memory_gib: int,
    worker_offload_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    identity = validate_inputs(model_root, audio_path, expected_audio_sha256, offload_root)
    if not 1 <= max_new_tokens <= 1024:
        raise CanaryError("max_new_tokens must be between 1 and 1024")
    if not 8 <= gpu_memory_gib <= 40:
        raise CanaryError("gpu_memory_gib must be between 8 and 40")
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if worker_offload_dir is None:
        offload_dir = Path(
            tempfile.mkdtemp(prefix="qwen3-omni-audio-", dir=str(offload_root))
        )
    else:
        offload_dir = worker_offload_dir
        if (
            offload_dir.parent != offload_root
            or not offload_dir.name.startswith("qwen3-omni-audio-")
            or not offload_dir.is_dir()
            or offload_dir.is_symlink()
        ):
            raise CanaryError("worker offload directory is unsafe")
    before = gpu_snapshot()
    host_before = host_memory_available_bytes()
    started = time.monotonic()
    model = None
    processor = None
    inputs = None
    result = None
    error = None
    loaded = None
    inferred = None
    load_seconds = None
    inference_seconds = None
    device_map_summary = None
    versions: dict[str, str] = {}
    raw_response = None
    try:
        import torch
        import transformers
        from qwen_omni_utils import process_mm_info
        from transformers import (
            Qwen3OmniMoeForConditionalGeneration,
            Qwen3OmniMoeProcessor,
        )

        versions = {"torch": torch.__version__, "transformers": transformers.__version__}
        load_started = time.monotonic()
        model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
            str(model_root),
            dtype=torch.bfloat16,
            device_map="auto",
            max_memory={0: f"{gpu_memory_gib}GiB", "cpu": "360GiB"},
            offload_folder=str(offload_dir),
            offload_state_dict=True,
            low_cpu_mem_usage=True,
            local_files_only=True,
            attn_implementation="sdpa",
        )
        processor = Qwen3OmniMoeProcessor.from_pretrained(
            str(model_root), local_files_only=True
        )
        torch.cuda.synchronize()
        load_seconds = time.monotonic() - load_started
        loaded = gpu_snapshot()
        device_map_summary = summarize_device_map(getattr(model, "hf_device_map", {}))
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "audio": str(audio_path)},
                    {"type": "text", "text": build_prompt()},
                ],
            }
        ]
        rendered = processor.apply_chat_template(
            conversation, add_generation_prompt=True, tokenize=False
        )
        audios, images, videos = process_mm_info(
            conversation, use_audio_in_video=False
        )
        inputs = processor(
            text=rendered,
            audio=audios,
            images=images,
            videos=videos,
            return_tensors="pt",
            padding=True,
            use_audio_in_video=False,
        )
        inputs = inputs.to(model.device).to(model.dtype)
        inference_started = time.monotonic()
        text_ids, _ = model.generate(
            **inputs,
            return_audio=False,
            thinker_return_dict_in_generate=True,
            use_audio_in_video=False,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        torch.cuda.synchronize()
        inference_seconds = time.monotonic() - inference_started
        inferred = gpu_snapshot()
        decoded = processor.batch_decode(
            text_ids.sequences[:, inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if len(decoded) != 1:
            raise CanaryError("semantic review returned an unexpected result count")
        raw_response = str(decoded[0])
        payload = extract_json_object(raw_response)
        result = {
            "payload": payload,
            "gate": validate_semantic_payload(payload, expected_phrase),
        }
    except Exception as exc:  # noqa: BLE001 - runtime failures must become retained evidence.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        inputs = None
        processor = None
        model = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception:  # noqa: BLE001 - parent process owns final cleanup evidence.
            pass
    after = gpu_snapshot()
    passed = bool(error is None and result and result["gate"]["passed"])
    evidence = {
        "schema_version": "wave64.aqa.qwen3_omni_audio_semantic_runtime_canary.v1",
        "program_id": "W64-AQA",
        "package_id": EXPECTED_PACKAGE_ID,
        "status": (
            "PASS_WORKER_EXACT_FIXTURE_AUDIO_SEMANTIC_RESPONSE"
            if passed
            else "FAIL_WORKER_RUNTIME_OR_AUDIO_SEMANTIC_RESPONSE"
        ),
        "identity": identity,
        "offline_policy": {
            "local_model_path_only": True,
            "local_audio_path_only": True,
            "hub_offline": True,
            "service_binding": False,
            "external_inference": False,
        },
        "runtime": {
            "dtype": "bfloat16",
            "device_map": "auto",
            "gpu_memory_limit_gib": gpu_memory_gib,
            "cpu_memory_limit_gib": 360,
            "attention": "sdpa",
            "max_new_tokens": max_new_tokens,
            "duration_seconds": time.monotonic() - started,
            "load_seconds": load_seconds,
            "inference_seconds": inference_seconds,
            "host_memory_available_before_bytes": host_before,
            "gpu_before": before,
            "gpu_loaded": loaded,
            "gpu_after_inference": inferred,
            "gpu_after_in_process_cleanup": after,
            "in_process_cleanup_delta_mib": after["used_mib"] - before["used_mib"],
            "device_map_summary": device_map_summary,
            "offload_dir": offload_dir.as_posix(),
            "versions": versions,
        },
        "semantic_review": result,
        "raw_response": raw_response,
        "error": error,
        "authority": {
            "worker_runtime_completed": passed,
            "exact_fixture_structured_audio_observation": passed,
            "process_exit_cleanup": False,
            "general_audio_semantic_quality": False,
            "general_asr_quality": False,
            "av_sync_or_motion_review": False,
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
    host_memory_before_worker: int,
    host_memory_after_worker_exit: int,
    offload_dir_removed: bool,
    worker_returncode: int,
    worker_stdout: str,
    worker_stderr: str,
) -> tuple[dict[str, Any], int]:
    runtime = evidence["runtime"]
    process_exit_delta_mib = (
        gpu_after_worker_exit["used_mib"] - gpu_before_worker["used_mib"]
    )
    gpu_cleanup_pass = process_exit_delta_mib <= 1024
    host_available_delta_bytes = (
        host_memory_after_worker_exit - host_memory_before_worker
    )
    host_cleanup_pass = host_available_delta_bytes >= -(16 * 1024**3)
    runtime.update(
        {
            "gpu_before_worker_process": gpu_before_worker,
            "gpu_after_worker_process_exit": gpu_after_worker_exit,
            "process_exit_cleanup_delta_mib": process_exit_delta_mib,
            "process_exit_gpu_cleanup_pass": gpu_cleanup_pass,
            "host_memory_available_before_worker_bytes": host_memory_before_worker,
            "host_memory_available_after_worker_exit_bytes": host_memory_after_worker_exit,
            "host_memory_available_delta_bytes": host_available_delta_bytes,
            "process_exit_host_cleanup_pass": host_cleanup_pass,
            "offload_dir_removed": offload_dir_removed,
            "cleanup_boundary": "isolated_worker_process_exit",
            "worker_returncode": worker_returncode,
            "worker_stdout": worker_stdout[-4000:],
            "worker_stderr": worker_stderr[-4000:],
        }
    )
    semantic_pass = bool(
        evidence.get("semantic_review")
        and evidence["semantic_review"]["gate"]["passed"]
    )
    worker_completed = worker_returncode in {0, 1} and evidence.get("error") is None
    passed = (
        worker_completed
        and semantic_pass
        and gpu_cleanup_pass
        and host_cleanup_pass
        and offload_dir_removed
    )
    evidence["schema_version"] = (
        "wave64.aqa.qwen3_omni_audio_semantic_runtime_canary.v2"
    )
    evidence["status"] = (
        "PASS_EXACT_FIXTURE_AUDIO_SEMANTIC_AND_PROCESS_EXIT_CLEANUP"
        if passed
        else "FAIL_RUNTIME_SEMANTIC_OR_PROCESS_EXIT_CLEANUP"
    )
    evidence["authority"].update(
        {
            "process_exit_cleanup": gpu_cleanup_pass
            and host_cleanup_pass
            and offload_dir_removed,
            "exact_fixture_structured_audio_observation": semantic_pass,
        }
    )
    return evidence, 0 if passed else 1


def run_isolated_canary(
    *,
    model_root: Path,
    audio_path: Path,
    expected_audio_sha256: str,
    expected_phrase: str,
    offload_root: Path,
    max_new_tokens: int,
    gpu_memory_gib: int,
    output_path: Path,
) -> tuple[dict[str, Any], int]:
    validate_inputs(model_root, audio_path, expected_audio_sha256, offload_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    worker_output = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.worker"
    worker_offload_dir = Path(
        tempfile.mkdtemp(prefix="qwen3-omni-audio-", dir=str(offload_root))
    )
    gpu_before_worker = gpu_snapshot()
    host_memory_before_worker = host_memory_available_bytes()
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
        "--expected-phrase",
        expected_phrase,
        "--offload-root",
        str(offload_root),
        "--max-new-tokens",
        str(max_new_tokens),
        "--gpu-memory-gib",
        str(gpu_memory_gib),
        "--worker-offload-dir",
        str(worker_offload_dir),
        "--output",
        str(worker_output),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if not worker_output.is_file():
            raise CanaryError(
                "isolated Omni worker did not emit evidence; "
                f"returncode={completed.returncode}; stderr={completed.stderr[-1000:]}"
            )
        evidence = json.loads(worker_output.read_text(encoding="utf-8"))
    finally:
        worker_output.unlink(missing_ok=True)
        if worker_offload_dir.exists():
            shutil.rmtree(worker_offload_dir)
    reported_offload_dir = Path(evidence["runtime"]["offload_dir"])
    if reported_offload_dir != worker_offload_dir:
        raise CanaryError("worker reported an unsafe offload directory")
    offload_dir_removed = not worker_offload_dir.exists()
    time.sleep(2)
    return finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker=gpu_before_worker,
        gpu_after_worker_exit=gpu_snapshot(),
        host_memory_before_worker=host_memory_before_worker,
        host_memory_after_worker_exit=host_memory_available_bytes(),
        offload_dir_removed=offload_dir_removed,
        worker_returncode=completed.returncode,
        worker_stdout=completed.stdout,
        worker_stderr=completed.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--expected-phrase", required=True)
    parser.add_argument("--offload-root", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--gpu-memory-gib", type=int, default=36)
    parser.add_argument(
        "--worker-offload-dir", type=Path, help=argparse.SUPPRESS
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    try:
        runner = run_worker if args.inner_worker else run_isolated_canary
        runner_args = {
            "model_root": args.model_root,
            "audio_path": args.audio,
            "expected_audio_sha256": args.expected_audio_sha256,
            "expected_phrase": args.expected_phrase,
            "offload_root": args.offload_root,
            "max_new_tokens": args.max_new_tokens,
            "gpu_memory_gib": args.gpu_memory_gib,
        }
        if not args.inner_worker:
            runner_args["output_path"] = args.output
        else:
            runner_args["worker_offload_dir"] = args.worker_offload_dir
        evidence, exit_code = runner(**runner_args)
    except (CanaryError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
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
