#!/usr/bin/env python3
"""Evaluate Wave64 Rows128-130 speech acoustics with calibrated local models."""

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


EXPECTED_TEXT = "We hold the frame steady and move on the beat."


class EvaluationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise EvaluationError(f"required file is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise EvaluationError(f"SHA-256 mismatch for {path}: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def load_object(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = bind(path, expected_sha256)
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise EvaluationError(f"JSON root must be an object: {path}")
    return binding, value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise EvaluationError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_audio(path: Path) -> tuple[dict[str, Any], Any, int]:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or rate <= 0 or not np.isfinite(audio).all():
        raise EvaluationError(f"audio is empty, non-finite, or invalid: {path}")
    mono = audio.mean(axis=1)
    rms = float(np.sqrt(np.mean(np.square(mono))))
    return {
        "sample_rate_hz": int(rate),
        "samples": int(audio.shape[0]),
        "channels": int(audio.shape[1]),
        "duration_seconds": round(audio.shape[0] / rate, 9),
        "peak_absolute": round(float(np.max(np.abs(audio))), 9),
        "rms": round(rms, 9),
        "clipping_ratio": round(float(np.mean(np.abs(audio) >= 0.999)), 9),
        "silence_ratio": round(float(np.mean(np.abs(audio) < 1e-4)), 9),
        "finite": True,
    }, mono, int(rate)


def rms_delta_db(before: dict[str, Any], after: dict[str, Any]) -> float:
    return round(20.0 * math.log10(max(after["rms"], 1e-9) / max(before["rms"], 1e-9)), 6)


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Path]:
    if manifest.get("classification") != "WAVE64_ROWS128_130_RUNTIME_RENDERED_AUTOMATED_QA_PENDING":
        raise EvaluationError("runtime manifest classification is invalid")
    dry = manifest.get("dry_speech")
    source = manifest.get("nonverbal_source")
    recipes = manifest.get("recipes")
    outputs = manifest.get("outputs")
    boundaries = manifest.get("boundaries")
    if not all(isinstance(value, dict) for value in (dry, source, recipes, outputs, boundaries)):
        raise EvaluationError("runtime manifest is structurally incomplete")
    if dry.get("expected_text") != EXPECTED_TEXT or dry.get("media_mutated") is not False:
        raise EvaluationError("dry speech lineage is invalid")
    if source.get("production_character_authority") is not False:
        raise EvaluationError("nonverbal source incorrectly claims production authority")
    record = source.get("record")
    if not isinstance(record, dict) or record.get("event_type") not in {"breath", "voice_reaction"}:
        raise EvaluationError("nonverbal functional-index record is invalid")
    if record.get("content_based_suppression") is not False or record.get("quality_defects"):
        raise EvaluationError("nonverbal source violates visibility or quality boundaries")
    if boundaries.get("source_bytes_modified") is not False or boundaries.get("production_promotion_claimed") is not False:
        raise EvaluationError("runtime manifest violates source or promotion boundaries")
    paths = {"dry": Path(dry["path"]).resolve(), "nonverbal_source": Path(source["path"]).resolve()}
    bind(paths["dry"], dry["sha256"])
    bind(paths["nonverbal_source"], source["sha256"])
    for key in ("nonverbal_candidate", "virtual_microphone_candidate", "restored_candidate"):
        value = outputs.get(key)
        if not isinstance(value, dict):
            raise EvaluationError(f"missing output binding: {key}")
        paths[key] = Path(value["path"]).resolve()
        bind(paths[key], value["sha256"])
    return paths


def classify(rows: dict[str, dict[str, Any]]) -> str:
    if not rows["129"]["automated_runtime_pass"]:
        return "FAIL_WAVE64_SPEECH_VIRTUAL_MICROPHONE_QA"
    if not rows["130"]["automated_runtime_pass"]:
        return "FAIL_WAVE64_SPEECH_RESTORATION_QA"
    return "PASS_WAVE64_ROWS129_130_AUTOMATED_QA_ROW128_IDENTITY_AUTHORITY_BLOCKED"


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_binding, manifest = load_object(args.manifest.resolve(), args.expected_manifest_sha256)
    paths = verify_manifest(manifest)
    adapter_binding = bind(args.cv3_adapter_script.resolve(), args.expected_cv3_adapter_sha256)
    threshold_binding, threshold_evidence = load_object(args.speaker_threshold_evidence.resolve(), args.expected_speaker_threshold_evidence_sha256)
    threshold_validation = threshold_evidence.get("threshold_validation", {})
    threshold = float(threshold_validation.get("threshold", math.nan))
    if not math.isfinite(threshold) or threshold_validation.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise EvaluationError("speaker threshold is not deployable")

    cv3 = load_module(args.cv3_adapter_script.resolve(), "wave64_cv3_for_speech_acoustics")
    cv3_root = args.cv3_root.resolve()
    whisper_dir = args.whisper_model_dir.resolve()
    cv3.require_hash(whisper_dir / "model.safetensors", cv3.WHISPER_SHA256, "Whisper weight")
    checkpoint = cv3_root / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    cv3.require_hash(checkpoint, cv3.ERES2NET_SHA256, "ERes2Net checkpoint")
    whisper = cv3.WhisperEvaluator(whisper_dir, args.transformers_overlay.resolve(), args.device)
    speaker = cv3.SpeakerEvaluator(cv3_root / "utils/3D-Speaker", checkpoint, args.device)

    technical: dict[str, dict[str, Any]] = {}
    mono: dict[str, Any] = {}
    for key, path in paths.items():
        technical[key], mono[key], _ = inspect_audio(path)

    transcripts = {key: whisper.transcribe(paths[key]) for key in ("dry", "virtual_microphone_candidate", "restored_candidate")}
    wer = {key: float(cv3.normalized_wer(EXPECTED_TEXT, transcripts[key])) for key in transcripts}
    dry_embedding = speaker.embedding(paths["dry"])
    similarity = {
        "virtual_microphone_to_dry": float(speaker.similarity(dry_embedding, speaker.embedding(paths["virtual_microphone_candidate"]))),
        "restored_to_dry": float(speaker.similarity(dry_embedding, speaker.embedding(paths["restored_candidate"]))),
        "nonverbal_to_dry": float(speaker.similarity(dry_embedding, speaker.embedding(paths["nonverbal_candidate"]))),
    }
    recipes = manifest["recipes"]
    restoration_recipe = recipes.get("restoration", {})
    record = manifest["nonverbal_source"]["record"]
    nonverbal_technical = technical["nonverbal_candidate"]
    dry_technical = technical["dry"]
    mic_technical = technical["virtual_microphone_candidate"]
    restored_technical = technical["restored_candidate"]
    duration_preserved = mic_technical["samples"] == dry_technical["samples"] and restored_technical["samples"] == dry_technical["samples"]
    rows = {
        "128": {
            "runtime_candidate_pass": nonverbal_technical["finite"] and nonverbal_technical["clipping_ratio"] == 0.0,
            "event_metadata_pass": record.get("event_type") in {"breath", "voice_reaction"} and record.get("role") == "voice",
            "rights_metadata_pass": bool(record.get("license_classification")) and bool(record.get("attribution")),
            "chain_specific_identity_similarity": round(similarity["nonverbal_to_dry"], 9),
            "chain_specific_identity_threshold": threshold,
            "chain_specific_identity_metric_pass": similarity["nonverbal_to_dry"] >= threshold,
            "production_character_identity_authority_pass": False,
            "independent_playback_review_pass": False,
            "automated_runtime_pass": True,
            "row_complete": False,
        },
        "129": {
            "technical_audio_pass": mic_technical["finite"] and mic_technical["clipping_ratio"] <= args.max_clipping_ratio,
            "duration_and_sample_count_preserved": duration_preserved,
            "asr_transcript": transcripts["virtual_microphone_candidate"],
            "normalized_wer": round(wer["virtual_microphone_candidate"], 6),
            "intelligibility_pass": wer["virtual_microphone_candidate"] <= args.max_wer,
            "speaker_similarity_to_dry": round(similarity["virtual_microphone_to_dry"], 9),
            "speaker_similarity_threshold": threshold,
            "identity_preservation_pass": similarity["virtual_microphone_to_dry"] >= threshold,
            "rms_delta_db": rms_delta_db(dry_technical, mic_technical),
            "dry_source_and_recipe_retained": recipes.get("virtual_microphone", {}).get("nondestructive_source_retained") is True,
            "independent_playback_review_pass": False,
            "final_production_authority_pass": False,
        },
        "130": {
            "technical_audio_pass": restored_technical["finite"] and restored_technical["clipping_ratio"] <= args.max_clipping_ratio,
            "duration_and_sample_count_preserved": duration_preserved,
            "asr_transcript": transcripts["restored_candidate"],
            "normalized_wer": round(wer["restored_candidate"], 6),
            "phoneme_content_proxy_pass": wer["restored_candidate"] <= args.max_wer,
            "speaker_similarity_to_dry": round(similarity["restored_to_dry"], 9),
            "speaker_similarity_threshold": threshold,
            "identity_preservation_pass": similarity["restored_to_dry"] >= threshold,
            "rms_delta_db_from_virtual_microphone": rms_delta_db(mic_technical, restored_technical),
            "bounded_level_change_pass": abs(rms_delta_db(mic_technical, restored_technical)) <= args.max_restoration_rms_delta_db,
            "bounded_repair_sample_ratio_pass": float(restoration_recipe.get("declick_repair_sample_ratio", math.inf)) <= float(restoration_recipe.get("declick_max_repair_sample_ratio", -math.inf)) <= 0.001,
            "repair_recipe": restoration_recipe,
            "source_and_intermediate_retained": restoration_recipe.get("source_and_intermediate_retained") is True,
            "independent_playback_review_pass": False,
            "final_production_authority_pass": False,
        },
    }
    rows["129"]["automated_runtime_pass"] = all(rows["129"][name] is True for name in ("technical_audio_pass", "duration_and_sample_count_preserved", "intelligibility_pass", "identity_preservation_pass", "dry_source_and_recipe_retained"))
    rows["129"]["row_complete"] = False
    rows["130"]["automated_runtime_pass"] = all(rows["130"][name] is True for name in ("technical_audio_pass", "duration_and_sample_count_preserved", "phoneme_content_proxy_pass", "identity_preservation_pass", "bounded_level_change_pass", "bounded_repair_sample_ratio_pass", "source_and_intermediate_retained"))
    rows["130"]["row_complete"] = False
    classification = classify(rows)
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_rows128_130_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": classification,
        "classification": classification,
        "bindings": {"manifest": manifest_binding, "cv3_adapter": adapter_binding, "speaker_threshold_evidence": threshold_binding},
        "technical_audio": technical,
        "dry_baseline": {"asr_transcript": transcripts["dry"], "normalized_wer": round(wer["dry"], 6)},
        "rows": rows,
        "remaining_blockers": {
            "128": ["indexed source has no locked production-character ownership", "nonverbal semantic and full-play listening review remain pending"],
            "129": ["independent full-play listening and final production recording-chain approval remain pending"],
            "130": ["independent before/after listening and final production restoration approval remain pending"],
        },
        "boundaries": {
            "source_media_modified": False,
            "rejected_speech_candidate_rerun": False,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise EvaluationError(f"immutable evaluation already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", type=Path, required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--speaker-threshold-evidence", type=Path, required=True)
    parser.add_argument("--expected-speaker-threshold-evidence-sha256", required=True)
    parser.add_argument("--cv3-root", type=Path, required=True)
    parser.add_argument("--whisper-model-dir", type=Path, required=True)
    parser.add_argument("--transformers-overlay", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--max-clipping-ratio", type=float, default=0.0001)
    parser.add_argument("--max-restoration-rms-delta-db", type=float, default=3.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = evaluate(args)
        write_json_new(args.output.resolve(), value)
    except Exception as exc:
        print(json.dumps({"classification": "WAVE64_ROWS128_130_EVALUATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"classification": value["classification"], "rows": value["rows"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
