#!/usr/bin/env python3
"""Prepare exact Qwen3-TTS Base acquisition requests and manifests for Row124."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


REPO_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"
TARGET_ROOT = "audio/tts/qwen3_tts_1_7b_base"
SOURCE_FILES: dict[str, tuple[int, str]] = {
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


class PreparationError(RuntimeError):
    pass


def load_manager(root: Path):
    path = root / "Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py"
    spec = importlib.util.spec_from_file_location("model_asset_manager_for_qwen_base", path)
    if not spec or not spec.loader:
        raise PreparationError(f"unable to load acquisition manager: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slug(relative: str) -> str:
    return relative.replace("/", "-").replace("_", "-").replace(".", "-")


def build_request(relative: str, size: int, digest: str) -> dict[str, Any]:
    source_path = Path(relative)
    parent = source_path.parent.as_posix()
    target_subdir = TARGET_ROOT if parent == "." else f"{TARGET_ROOT}/{parent}"
    request_id = f"w64-qwen3-tts-1-7b-base-{slug(relative)}"
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "capability_need": f"Pinned Qwen3-TTS Base file for genuine Wave64 reference-conditioned cloning: {relative}",
        "intended_use": "TRK-W64-124 reference-conditioned voice cloning runtime and identity evaluation",
        "selection_rationale": "Official immutable Apache-2.0 Base repository; exact hashes permit reuse before network acquisition.",
        "provider": "huggingface",
        "source": {
            "repo_id": REPO_ID,
            "revision": REVISION,
            "filename": relative,
            "sha256": digest,
            "bytes": size,
        },
        "asset": {
            "model_name": "qwen3_tts_1_7b_base",
            "model_type": "audio_model",
            "base_model": "reference_voice_cloning_and_general_synthesis",
            "target_subdir": target_subdir,
            "filename": source_path.name,
            "audio_impact": "reference-conditioned speech engine file; runtime, identity, timing, and listening QA remain required",
        },
        "integration": {
            "workflow_lane": "wave64_hyperreal_speech_row124",
            "compatible_engines": ["qwen3_tts_1_7b_base"],
            "model_role": f"reference_clone_repository_file:{relative}",
            "expected_runtime_result": "load pinned Base model and generate one immutable reference-conditioned candidate",
            "priority": 1,
        },
        "policy": {
            "license_status": "public_permissive",
            "license_id": "apache-2.0",
            "license_url": f"https://huggingface.co/{REPO_ID}",
            "commercial_use_scope": "subject to Apache-2.0 and recorded reference-audio rights",
            "content_based_suppression": False,
            "adult_or_nsfw_metadata_is_not_a_filter": True,
            "allow_browser_fallback": False,
        },
    }


def prepare(root: Path, output_root: Path) -> dict[str, Any]:
    if len(SOURCE_FILES) != 11 or len({digest for _, digest in SOURCE_FILES.values()}) != 11:
        raise PreparationError("Qwen Base source file set must contain 11 unique exact hashes")
    manager = load_manager(root)
    request_dir = output_root / "requests"
    manifest_dir = output_root / "manifests"
    request_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    records = []
    reuse_count = 0
    voice_design_root = root / "models/audio/tts/qwen3_tts_1_7b_voicedesign"
    for relative, (size, digest) in SOURCE_FILES.items():
        request = build_request(relative, size, digest)
        manager.require_request(request)
        manifest = manager.resolve_request(root, request)
        filename = f"{request['request_id']}.json"
        request_path = request_dir / filename
        manifest_path = manifest_dir / filename
        manager.write_json_atomic(request_path, request)
        manager.write_json_atomic(manifest_path, manifest)
        reuse_source = voice_design_root / relative
        reusable = (
            reuse_source.is_file()
            and reuse_source.stat().st_size == size
            and manager.sha256_file(reuse_source) == digest
        )
        reuse_count += int(reusable)
        records.append({
            "relative_path": relative,
            "bytes": size,
            "sha256": digest,
            "request_path": str(request_path),
            "manifest_path": str(manifest_path),
            "exact_local_reuse_candidate": reusable,
            "reuse_source": str(reuse_source) if reusable else None,
        })
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_base_acquisition_preparation",
        "classification": "QWEN3_TTS_BASE_EXACT_ACQUISITION_PREPARED",
        "repo_id": REPO_ID,
        "revision": REVISION,
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "exact_local_reuse_count": reuse_count,
        "network_acquisition_count": len(records) - reuse_count,
        "records": records,
        "boundaries": {
            "download_executed": False,
            "registry_mutated": False,
            "runtime_executed": False,
            "production_ready": False,
            "content_based_suppression": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_root = args.output_root.resolve() if args.output_root.is_absolute() else (root / args.output_root).resolve()
    try:
        result = prepare(root, output_root)
    except Exception as exc:
        print(json.dumps({"classification": "QWEN3_TTS_BASE_ACQUISITION_PREPARATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    summary = output_root / "preparation_summary.json"
    load_manager(root).write_json_atomic(summary, result)
    print(json.dumps({
        "classification": result["classification"],
        "file_count": result["file_count"],
        "exact_local_reuse_count": result["exact_local_reuse_count"],
        "network_acquisition_count": result["network_acquisition_count"],
        "summary": str(summary),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
