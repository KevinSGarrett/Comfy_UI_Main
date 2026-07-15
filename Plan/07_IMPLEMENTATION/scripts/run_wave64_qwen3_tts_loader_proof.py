#!/usr/bin/env python3
"""Run a hash-bound local Qwen3-TTS VoiceDesign loader proof without generation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
EXPECTED_PACKAGES = {
    "qwen-tts": "0.1.1",
    "transformers": "4.57.3",
    "accelerate": "1.12.0",
    "huggingface-hub": "0.36.2",
    "sox": "1.5.0",
}
MODEL_LOGICAL_ROOT = Path("models/audio/tts/qwen3_tts_1_7b_voicedesign")


class LoaderProofError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise LoaderProofError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def validate_acquisition(root: Path, bundle: dict[str, Any], acquisition: dict[str, Any]) -> list[dict[str, Any]]:
    if bundle.get("asset_id") != "qwen3_tts_1_7b_voicedesign":
        raise LoaderProofError("loader proof accepts only the selected Qwen3-TTS VoiceDesign asset")
    if acquisition.get("classification") != "HF_SPEECH_REPOSITORY_ACQUIRED_HASH_VERIFIED_RUNTIME_PENDING":
        raise LoaderProofError("repository acquisition is not hash-verified/runtime-pending")
    if bundle.get("revision") != acquisition.get("revision"):
        raise LoaderProofError("acquisition revision differs from bundle")
    expected = {item["source_path"]: item for item in bundle.get("files", [])}
    observed = {item["source_path"]: item for item in acquisition.get("files", [])}
    if not expected or set(expected) != set(observed):
        raise LoaderProofError("acquired repository file set differs from exact bundle")
    results = []
    for source_path in sorted(expected):
        wanted = expected[source_path]
        actual = observed[source_path]
        target = resolve(root, actual["target_path"])
        if not target.is_file():
            raise LoaderProofError(f"acquired target is missing: {target}")
        if target.stat().st_size != int(wanted["bytes"]):
            raise LoaderProofError(f"acquired target byte count mismatch: {source_path}")
        digest = sha256_file(target)
        if digest != wanted["sha256"] or actual["sha256"] != wanted["sha256"]:
            raise LoaderProofError(f"acquired target SHA-256 mismatch: {source_path}")
        results.append(
            {
                "filename": source_path,
                "path": (MODEL_LOGICAL_ROOT / source_path).as_posix(),
                "sha256": digest,
                "bytes": target.stat().st_size,
            }
        )
    return results


def package_identity(site_packages: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    sys.path.insert(0, str(site_packages))
    identities: dict[str, str] = {}
    for name, expected in EXPECTED_PACKAGES.items():
        observed = importlib.metadata.version(name)
        if observed != expected:
            raise LoaderProofError(f"runtime package drift for {name}: expected {expected}, observed {observed}")
        identities[name] = observed
    wheels = []
    wheel_root = site_packages.parent / "wheels"
    for path in sorted(wheel_root.glob("*")):
        if path.is_file():
            wheels.append(
                {
                    "filename": path.name,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    if not wheels:
        raise LoaderProofError("isolated runtime wheel/source artifacts are missing")
    return identities, wheels


def build_adapter_registry(
    model_files: list[dict[str, Any]],
    packages: dict[str, str],
    wheels: list[dict[str, Any]],
    proof_path: str,
    proof_sha256: str,
    load_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "registry_id": "wave64_speech_engine_adapters",
        "adapters": [
            {
                "schema_version": "1.0",
                "adapter_id": "qwen3_tts_1_7b_voicedesign_official_0_1_1",
                "engine_family": "qwen3_tts",
                "repository": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                "revision": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
                "model_files": model_files,
                "license": {
                    "id": "Apache-2.0",
                    "source": "official Hugging Face repository and qwen-tts PyPI package",
                },
                "environment": {
                    "isolation": "target_directory_over_validated_comfyui_cuda_runtime",
                    "packages": packages,
                    "package_artifacts": wheels,
                    "torch_runtime_reused": "2.11.0+cu128",
                    "flash_attention": "not_installed_eager_pytorch_used",
                    "sox_executable_available": bool(load_metrics["sox_executable_available"]),
                },
                "capabilities": {
                    "voice_design": True,
                    "reference_voice_clone": False,
                    "languages": "engine_declared_multilingual_not_yet_runtime_benchmarked",
                    "candidate_generation_proven": False,
                },
                "runtime_status": "load_proven",
                "load_proof": {"path": proof_path, "sha256": proof_sha256},
                "known_blockers": [
                    "speech generation and audio decode are not yet executed",
                    "system sox executable is absent",
                    "Flash Attention is absent; eager PyTorch is slower",
                    "continuity, playback, and final-production authority are pending",
                ],
                "production_ready": False,
                "content_based_suppression": False,
            }
        ],
        "content_based_suppression": False,
    }


def run_loader(model_dir: Path) -> dict[str, Any]:
    import torch
    from qwen_tts import Qwen3TTSModel

    if not torch.cuda.is_available():
        raise LoaderProofError("CUDA is required for the selected local loader proof")
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(model_dir),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="eager",
    )
    elapsed = time.perf_counter() - started
    metrics = {
        "model_type": type(model).__name__,
        "load_seconds": round(elapsed, 3),
        "device": torch.cuda.get_device_name(0),
        "cuda_architecture": torch.cuda.get_device_capability(0),
        "cuda_memory_allocated_bytes": torch.cuda.memory_allocated(),
        "cuda_memory_reserved_bytes": torch.cuda.memory_reserved(),
        "cuda_peak_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        "sox_executable_available": shutil.which("sox") is not None,
        "flash_attention_available": importlib.util.find_spec("flash_attn") is not None,
    }
    del model
    torch.cuda.empty_cache()
    return metrics


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--acquisition-result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--out-adapter-registry", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        model_dir = resolve(root, args.model_dir)
        site_packages = resolve(root, args.site_packages)
        bundle_path = resolve(root, args.bundle)
        acquisition_path = resolve(root, args.acquisition_result)
        output = resolve(root, args.out)
        adapter_output = resolve(root, args.out_adapter_registry)
        model_files = validate_acquisition(root, load_json(bundle_path), load_json(acquisition_path))
        packages, wheels = package_identity(site_packages)
        metrics = run_loader(model_dir)
        evidence = {
            "schema_version": "1.0",
            "artifact_type": "wave64_qwen3_tts_voicedesign_loader_proof",
            "created_at": now_iso(),
            "classification": "QWEN3_TTS_VOICEDESIGN_LOAD_PROOF_PASS_AUDIO_GENERATION_PENDING",
            "asset_id": "qwen3_tts_1_7b_voicedesign",
            "repository": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "revision": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
            "license": "Apache-2.0",
            "model_files": model_files,
            "environment": {"packages": packages, "package_artifacts": wheels},
            "runtime": {**metrics, "official_loader_completed": True, "audio_generated": False},
            "acceptance": {
                "exact_file_set_hash_pass": True,
                "package_identity_pass": True,
                "cuda_loader_pass": True,
                "audio_generation_pass": False,
                "playback_review_pass": False,
                "production_authority_pass": False,
                "row117_complete": False,
            },
            "boundaries": {
                "rejected_candidate_rerun": False,
                "generation_executed": False,
                "download_claimed_as_ready": False,
                "production_ready": False,
                "content_based_suppression": False,
            },
        }
        write_json_atomic(output, evidence)
        proof_sha = sha256_file(output)
        registry = build_adapter_registry(
            model_files,
            packages,
            wheels,
            display(root, output),
            proof_sha,
            metrics,
        )
        write_json_atomic(adapter_output, registry)
        print(
            json.dumps(
                {
                    "classification": evidence["classification"],
                    "evidence": display(root, output),
                    "evidence_sha256": proof_sha,
                    "adapter_registry": display(root, adapter_output),
                    "load_seconds": metrics["load_seconds"],
                },
                indent=2,
            )
        )
        return 0
    except (LoaderProofError, OSError, ValueError, json.JSONDecodeError, ImportError, RuntimeError) as exc:
        print(json.dumps({"classification": "QWEN3_TTS_VOICEDESIGN_LOAD_PROOF_FAILED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
