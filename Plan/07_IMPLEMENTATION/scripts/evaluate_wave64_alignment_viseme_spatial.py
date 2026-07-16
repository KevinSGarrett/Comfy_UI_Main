#!/usr/bin/env python3
"""Strict automated evaluation for the Wave64 Rows135, 136, and 138 packet."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_MANIFEST_CLASSIFICATION = "W64_ROWS135_136_138_BOUNDED_RUNTIME_PASS_PRODUCTION_AUTHORITY_BLOCKED"
EXPECTED_SOURCE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
EXPECTED_TEXT = "We hold the frame steady and move on the beat."


class EvaluationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise EvaluationError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected_sha256.lower():
        raise EvaluationError(f"{label} SHA-256 mismatch: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def load_json(path: Path, expected_sha256: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = bind(path, expected_sha256, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} root must be an object")
    return binding, value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise EvaluationError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise EvaluationError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return {"path": str(path.resolve()), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def verify_runtime_manifest(manifest: dict[str, Any]) -> dict[str, Path]:
    if manifest.get("classification") != EXPECTED_MANIFEST_CLASSIFICATION:
        raise EvaluationError("runtime manifest classification is invalid")
    source = manifest.get("source")
    row135 = manifest.get("row135")
    row136 = manifest.get("row136")
    row138 = manifest.get("row138")
    boundaries = manifest.get("boundaries")
    if not all(isinstance(value, dict) for value in (source, row135, row136, row138, boundaries)):
        raise EvaluationError("runtime manifest is structurally incomplete")
    if source.get("sha256") != EXPECTED_SOURCE_SHA256 or source.get("transcript") != EXPECTED_TEXT:
        raise EvaluationError("source identity or transcript is invalid")
    if source.get("source_unchanged_after_runtime") is not True:
        raise EvaluationError("source non-mutation proof is absent")
    required_false = ("mms_grapheme_is_phoneme_authority", "fixture_is_production_alignment", "automated_metrics_are_human_playback", "production_ready")
    if any(boundaries.get(key) is not False for key in required_false):
        raise EvaluationError("runtime manifest contains a false authority claim")
    if row135.get("word_alignment_pass") is not True or row135.get("phoneme_alignment_pass") is not False:
        raise EvaluationError("Row135 authority boundary is invalid")
    if row136.get("fixture_runtime_pass") is not True or row136.get("production_input_pass") is not False:
        raise EvaluationError("Row136 authority boundary is invalid")
    if any(row.get("row_complete") is not False for row in (row135, row136, row138)):
        raise EvaluationError("runtime manifest improperly completes a row")
    alignment = row135.get("alignment")
    fixture = row136.get("fixture")
    output = row138.get("output")
    if not all(isinstance(value, dict) for value in (alignment, fixture, output)):
        raise EvaluationError("runtime artifact bindings are incomplete")
    paths = {
        "source": Path(str(source.get("path", ""))).resolve(),
        "alignment": Path(str(alignment.get("path", ""))).resolve(),
        "fixture": Path(str(fixture.get("path", ""))).resolve(),
        "spatial": Path(str(output.get("path", ""))).resolve(),
    }
    bind(paths["source"], EXPECTED_SOURCE_SHA256, "source audio")
    bind(paths["alignment"], str(alignment.get("sha256", "")), "Row135 alignment")
    bind(paths["fixture"], str(fixture.get("sha256", "")), "Row136 fixture")
    bind(paths["spatial"], str(output.get("sha256", "")), "Row138 spatial audio")
    return paths


def inspect_spatial(path: Path) -> tuple[dict[str, Any], Any, int]:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or rate <= 0 or audio.shape[1] != 2 or not np.isfinite(audio).all():
        raise EvaluationError("spatial output must be finite stereo audio")
    midpoint = audio.shape[0] // 2
    first = audio[:midpoint]
    second = audio[midpoint:]
    rms = lambda values: float(np.sqrt(np.mean(np.square(values), dtype=np.float64)))
    metrics = {
        "sample_rate_hz": int(rate),
        "samples_per_channel": int(audio.shape[0]),
        "channels": int(audio.shape[1]),
        "duration_seconds": round(audio.shape[0] / rate, 9),
        "peak_absolute": round(float(np.max(np.abs(audio))), 9),
        "clipping_ratio": round(float(np.mean(np.abs(audio) >= 0.999)), 9),
        "first_half_left_rms": round(rms(first[:, 0]), 9),
        "first_half_right_rms": round(rms(first[:, 1]), 9),
        "second_half_left_rms": round(rms(second[:, 0]), 9),
        "second_half_right_rms": round(rms(second[:, 1]), 9),
    }
    metrics["trajectory_channel_motion_pass"] = (
        metrics["first_half_left_rms"] > metrics["first_half_right_rms"]
        and metrics["second_half_right_rms"] > metrics["second_half_left_rms"]
    )
    return metrics, audio, int(rate)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_binding, manifest = load_json(args.manifest.resolve(), args.expected_manifest_sha256, "runtime manifest")
    runner_binding = bind(args.runner_script.resolve(), args.expected_runner_sha256, "runtime runner")
    paths = verify_runtime_manifest(manifest)
    spatial_metrics, _, _ = inspect_spatial(paths["spatial"])

    import soundfile as sf

    source_info = sf.info(str(paths["source"]))
    duration_delta = abs(spatial_metrics["duration_seconds"] - source_info.frames / source_info.samplerate)
    adapter_binding = bind(args.cv3_adapter_script.resolve(), args.expected_cv3_adapter_sha256, "CV3 adapter")
    threshold_binding, threshold_evidence = load_json(
        args.speaker_threshold_evidence.resolve(), args.expected_speaker_threshold_evidence_sha256, "speaker threshold evidence"
    )
    threshold_data = threshold_evidence.get("threshold_validation", {})
    speaker_threshold = float(threshold_data.get("threshold", math.nan))
    if not math.isfinite(speaker_threshold) or threshold_data.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise EvaluationError("speaker threshold is not deployable for chain-specific evaluation")

    cv3 = load_module(args.cv3_adapter_script.resolve(), "wave64_cv3_eval_for_spatial")
    whisper_dir = args.whisper_model_dir.resolve()
    cv3.require_hash(whisper_dir / "model.safetensors", cv3.WHISPER_SHA256, "Whisper weight")
    checkpoint = args.cv3_root.resolve() / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    cv3.require_hash(checkpoint, cv3.ERES2NET_SHA256, "ERes2Net checkpoint")
    whisper = cv3.WhisperEvaluator(whisper_dir, args.transformers_overlay.resolve(), args.device)
    speaker = cv3.SpeakerEvaluator(args.cv3_root.resolve() / "utils/3D-Speaker", checkpoint, args.device)
    transcript = whisper.transcribe(paths["spatial"])
    wer = float(cv3.normalized_wer(EXPECTED_TEXT, transcript))
    similarity = float(speaker.similarity(speaker.embedding(paths["source"]), speaker.embedding(paths["spatial"])))
    gates = {
        "runtime_manifest_lineage_pass": True,
        "source_nonmutation_pass": True,
        "word_grapheme_alignment_runtime_pass": True,
        "phoneme_authority_pass": False,
        "viseme_fixture_runtime_pass": True,
        "viseme_production_input_pass": False,
        "spatial_decode_pass": True,
        "spatial_duration_pass": duration_delta <= args.max_duration_delta_seconds,
        "spatial_channel_motion_pass": bool(spatial_metrics["trajectory_channel_motion_pass"]),
        "spatial_clipping_pass": spatial_metrics["clipping_ratio"] <= args.max_clipping_ratio,
        "spatial_intelligibility_pass": wer <= args.max_wer,
        "spatial_speaker_identity_pass": similarity >= speaker_threshold,
        "independent_playback_review_pass": False,
        "production_scene_authority_pass": False,
    }
    automated_pass = all(gates[key] for key in (
        "runtime_manifest_lineage_pass", "source_nonmutation_pass", "word_grapheme_alignment_runtime_pass",
        "viseme_fixture_runtime_pass", "spatial_decode_pass", "spatial_duration_pass",
        "spatial_channel_motion_pass", "spatial_clipping_pass", "spatial_intelligibility_pass",
        "spatial_speaker_identity_pass",
    ))
    classification = (
        "PASS_ROWS135_136_138_BOUNDED_AUTOMATED_RUNTIME_PRODUCTION_AUTHORITY_BLOCKED"
        if automated_pass else "FAIL_ROWS135_136_138_BOUNDED_AUTOMATED_RUNTIME"
    )
    result = {
        "schema_version": "1.0",
        "artifact_type": "wave64_alignment_viseme_spatial_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": classification,
        "classification": classification,
        "bindings": {
            "manifest": manifest_binding,
            "runner": runner_binding,
            "cv3_adapter": adapter_binding,
            "speaker_threshold_evidence": threshold_binding,
            "source_audio": bind(paths["source"], EXPECTED_SOURCE_SHA256, "source audio"),
            "spatial_audio": bind(paths["spatial"], str(manifest["row138"]["output"]["sha256"]), "spatial audio"),
        },
        "metrics": {
            "expected_transcript": EXPECTED_TEXT,
            "observed_transcript": transcript,
            "normalized_wer": round(wer, 9),
            "max_wer": args.max_wer,
            "dry_to_spatial_speaker_similarity": round(similarity, 9),
            "speaker_similarity_threshold": round(speaker_threshold, 9),
            "duration_delta_seconds": round(duration_delta, 9),
            "spatial_audio": spatial_metrics,
        },
        "gates": gates,
        "row_results": {
            "135": {"status": manifest["row135"]["status"], "automated_word_grapheme_runtime_pass": True, "row_complete": False},
            "136": {"status": manifest["row136"]["status"], "automated_fixture_runtime_pass": True, "row_complete": False},
            "138": {"status": manifest["row138"]["status"], "automated_spatial_runtime_pass": automated_pass, "row_complete": False},
        },
        "boundaries": {
            "true_phoneme_authority_complete": False,
            "mandated_row135_asset_set_complete": False,
            "independent_playback_review_complete": False,
            "production_scene_authority_complete": False,
            "production_ready": False,
            "content_based_suppression": False,
        },
    }
    if not automated_pass:
        raise EvaluationError(json.dumps(result, ensure_ascii=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--runner-script", type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", type=Path, required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--speaker-threshold-evidence", type=Path, required=True)
    parser.add_argument("--expected-speaker-threshold-evidence-sha256", required=True)
    parser.add_argument("--cv3-root", type=Path, required=True)
    parser.add_argument("--whisper-model-dir", type=Path, required=True)
    parser.add_argument("--transformers-overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--max-duration-delta-seconds", type=float, default=0.001)
    parser.add_argument("--max-clipping-ratio", type=float, default=0.0001)
    args = parser.parse_args()
    try:
        result = evaluate(args)
        binding = write_json_new(args.output.resolve(), result)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS135_136_138_EVALUATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"classification": result["classification"], "evaluation": binding, "metrics": result["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
