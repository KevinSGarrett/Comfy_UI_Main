#!/usr/bin/env python3
"""Generate the immutable Qwen3-TTS continuity matrix for Wave64 Rows131-133."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


BASELINE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
BASELINE_TEXT = "We hold the frame steady and move on the beat."
LINE_PLAN = [
    {"line_id": "L02", "scene_id": "SCENE-A", "language": "English", "language_role": "english", "seed": 13102, "text": "The camera settles as the room grows quiet."},
    {"line_id": "L03", "scene_id": "SCENE-A", "language": "English", "language_role": "english", "seed": 13103, "text": "Keep the pace even and the breath controlled."},
    {"line_id": "L04", "scene_id": "SCENE-B", "language": "English", "language_role": "english", "seed": 13104, "text": "Across the hall, I can still hear every word."},
    {"line_id": "L05", "scene_id": "SCENE-B", "language": "English", "language_role": "english", "seed": 13105, "text": "The second cue arrives before the door closes."},
    {"line_id": "L06", "scene_id": "SCENE-C", "language": "English", "language_role": "english", "seed": 13106, "text": "At sunrise, we begin the next scene together."},
    {"line_id": "L07", "scene_id": "SCENE-C", "language": "English", "language_role": "english", "seed": 13107, "text": "The final cue arrives before the lights fade."},
    {"line_id": "L08", "scene_id": "SCENE-C", "language": "Spanish", "language_role": "multilingual", "seed": 13108, "text": "Mantenemos el encuadre firme y avanzamos con calma."},
    {"line_id": "L09", "scene_id": "SCENE-C", "language": "French", "language_role": "multilingual", "seed": 13109, "text": "Nous gardons le cadre stable et avancons avec calme."},
    {"line_id": "L10", "scene_id": "SCENE-C", "language": "Auto", "language_role": "code_switch", "seed": 13110, "text": "We hold the frame steady y seguimos con calma."},
]


class MatrixError(RuntimeError):
    pass


def load_base_runner(path: Path):
    spec = importlib.util.spec_from_file_location("wave64_qwen_base_runner", path)
    if not spec or not spec.loader:
        raise MatrixError(f"unable to load base runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise MatrixError(f"required file is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise MatrixError(f"SHA-256 mismatch for {path}: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def validate_line_plan(plan: list[dict[str, Any]]) -> None:
    if len(plan) != 9 or len({line["line_id"] for line in plan}) != 9 or len({line["seed"] for line in plan}) != 9:
        raise MatrixError("continuity line plan must contain nine unique new lines")
    if {line["scene_id"] for line in plan} != {"SCENE-A", "SCENE-B", "SCENE-C"}:
        raise MatrixError("continuity line plan must cover exactly three scenes")
    roles = {line["language_role"] for line in plan}
    if roles != {"english", "multilingual", "code_switch"}:
        raise MatrixError("continuity line plan language roles are incomplete")
    if any(not line["text"].strip() for line in plan):
        raise MatrixError("continuity line text cannot be empty")


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise MatrixError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return bind(path)


def load_pinned_onnxruntime(system_site_packages: Path):
    system_site_packages = system_site_packages.resolve()
    if not system_site_packages.is_dir():
        raise MatrixError(f"ONNX Runtime site-packages directory is missing: {system_site_packages}")
    sys.path.insert(0, str(system_site_packages))
    try:
        import onnxruntime
    finally:
        if sys.path[0] == str(system_site_packages):
            sys.path.pop(0)
        else:
            sys.path.remove(str(system_site_packages))
    runtime_path = Path(onnxruntime.__file__).resolve()
    if onnxruntime.__version__ != "1.27.0" or not runtime_path.is_relative_to(system_site_packages):
        raise MatrixError(f"ONNX Runtime identity drift: {onnxruntime.__version__} at {runtime_path}")
    if str(system_site_packages) in sys.path:
        raise MatrixError("broad system site-packages path remained active after ONNX Runtime import")
    return onnxruntime


def run(args: argparse.Namespace) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio

    validate_line_plan(LINE_PLAN)
    onnxruntime = load_pinned_onnxruntime(args.onnxruntime_system_site_packages)
    base = load_base_runner(args.base_runner_script.resolve())
    base_runner_binding = bind(args.base_runner_script.resolve())
    model_files = base.verify_files(args.model_dir.resolve())
    reference = base.verify_reference(args.reference.resolve())
    packages = base.verify_packages(args.site_packages.resolve())
    runtime_packages = base.validate_runtime_versions({"torch": torch.__version__, "torchaudio": torchaudio.__version__})
    baseline = bind(args.baseline_audio.resolve(), BASELINE_SHA256)

    from transformers import AutoProcessor
    from qwen_tts import Qwen3TTSModel

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise MatrixError(f"immutable output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    load_started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(args.model_dir.resolve()),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="eager",
    )
    load_finished = time.perf_counter()
    supported = {value.casefold() for value in (model.get_supported_languages() or [])}
    requested = {line["language"].casefold() for line in LINE_PLAN}
    if not requested.issubset(supported):
        raise MatrixError(f"requested languages are unsupported: {sorted(requested - supported)}")
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(args.reference.resolve()),
        ref_text=base.REFERENCE_TRANSCRIPT,
        x_vector_only_mode=False,
    )
    outputs: list[dict[str, Any]] = []
    generation_started = time.perf_counter()
    for line in LINE_PLAN:
        seed = int(line["seed"])
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        line_started = time.perf_counter()
        wavs, sample_rate = model.generate_voice_clone(
            text=line["text"],
            language=line["language"],
            voice_clone_prompt=prompt,
            non_streaming_mode=False,
            **base.GENERATION,
        )
        if len(wavs) != 1:
            raise MatrixError(f"expected one waveform for {line['line_id']}, observed {len(wavs)}")
        waveform = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
        if not waveform.size or not np.isfinite(waveform).all():
            raise MatrixError(f"invalid waveform for {line['line_id']}")
        peak = float(np.max(np.abs(waveform)))
        if peak > 1.0:
            waveform = waveform / peak
        wav_path = output_dir / f"{line['line_id'].lower()}_{line['language_role']}_seed{seed}.wav"
        if wav_path.exists():
            raise MatrixError(f"immutable line output already exists: {wav_path}")
        sf.write(str(wav_path), waveform, sample_rate, subtype="PCM_16")
        output = bind(wav_path)
        outputs.append({
            **line,
            "microphone_chain_id": "qwen_base_dry_icl_v1",
            "room_profile_id": "dry_reference_condition",
            "output": {**output, "sample_rate_hz": int(sample_rate), "samples": int(waveform.size), "duration_seconds": round(waveform.size / sample_rate, 9), "channels": 1, "subtype": "PCM_16"},
            "generation_seconds": round(time.perf_counter() - line_started, 3),
        })
    generation_finished = time.perf_counter()
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_qwen3_tts_continuity_matrix_manifest",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "classification": "QWEN3_TTS_CONTINUITY_MATRIX_GENERATED_AUTOMATED_QA_PENDING",
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
            "supported_languages": sorted(supported),
        },
        "reference": {**reference, "transcript": base.REFERENCE_TRANSCRIPT, "rights": "Public Domain Mark 1.0", "character_id": "UNASSIGNED_REFERENCE_POOL", "production_authorized": False},
        "baseline": {**baseline, "line_id": "L01", "scene_id": "SCENE-A", "language": "English", "language_role": "english", "text": BASELINE_TEXT, "microphone_chain_id": "qwen_base_dry_icl_v1", "room_profile_id": "dry_reference_condition"},
        "new_lines": outputs,
        "matrix_contract": {"line_count_including_baseline": 10, "scene_count": 3, "new_generation_count": 9, "calibration_line_ids": ["L01", "L02", "L03", "L04", "L08"], "held_out_line_ids": ["L05", "L06", "L07", "L09", "L10"]},
        "implementation": {"base_runner": base_runner_binding},
        "runtime": {"load_seconds": round(load_finished - load_started, 3), "generation_seconds": round(generation_finished - generation_started, 3), "total_seconds": round(generation_finished - load_started, 3), "onnxruntime": onnxruntime.__version__, "onnxruntime_path": str(Path(onnxruntime.__file__).resolve()), "system_site_packages_removed_after_onnxruntime_import": str(args.onnxruntime_system_site_packages.resolve()) not in sys.path, "transformers_auto_processor_module": AutoProcessor.__module__, "qwen_model_module": Qwen3TTSModel.__module__},
        "boundaries": {"reference_count": 1, "calibrated_embedding_route_count": 1, "production_character_authority": False, "multilingual_content_qa_complete": False, "accent_qa_complete": False, "independent_playback_review_complete": False, "production_ready": False, "content_based_suppression": False, "aws_or_ec2_used": False, "mask_or_wave71_touched": False},
    }
    manifest_binding = write_json_new(output_dir / "wave64_qwen3_tts_continuity_matrix_manifest.json", manifest)
    return {"classification": manifest["classification"], "manifest": manifest_binding, "line_count": 10, "new_generation_count": 9, "runtime": manifest["runtime"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--baseline-audio", type=Path, required=True)
    parser.add_argument("--base-runner-script", type=Path, required=True)
    parser.add_argument("--onnxruntime-system-site-packages", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"classification": "QWEN3_TTS_CONTINUITY_MATRIX_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
