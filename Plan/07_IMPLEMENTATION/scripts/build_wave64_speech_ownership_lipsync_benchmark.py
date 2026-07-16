#!/usr/bin/env python3
"""Build Wave64 Rows134, 137, and 147 controls from immutable local evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLASSIFICATION = "W64_ROWS134_137_147_CONTROLS_EXECUTED_PRODUCTION_BLOCKED"
EXPECTED_OVERLAP_CLASSIFICATION = "W64_ROWS140_142_144_CONTROLS_EXECUTED_PRODUCTION_BLOCKED"
EXPECTED_CONTINUITY_CLASSIFICATION = "PASS_CONTINUITY_PILOT_PRODUCTION_AUTHORITY_BLOCKED"


class ControlBuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise ControlBuildError(f"required file is missing: {path}")
    actual = sha256_file(path)
    if expected_sha256 and actual != expected_sha256:
        raise ControlBuildError(f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControlBuildError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ControlBuildError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _validate_overlap(overlap: dict[str, Any]) -> dict[str, Any]:
    if overlap.get("classification") != EXPECTED_OVERLAP_CLASSIFICATION:
        raise ControlBuildError("overlap manifest classification is not the accepted bounded control result")
    metrics = overlap.get("overlap", {}).get("metrics", {})
    gates = overlap.get("overlap", {}).get("gates", {})
    required_metrics = (
        "sample_rate_hz", "samples_per_channel", "kokoro_start_sample", "qwen_start_sample",
        "overlap_start_sample", "overlap_end_sample",
    )
    if any(not isinstance(metrics.get(key), int) for key in required_metrics):
        raise ControlBuildError("overlap sample topology is incomplete")
    if metrics["kokoro_start_sample"] != 0 or metrics["qwen_start_sample"] != metrics["overlap_start_sample"]:
        raise ControlBuildError("overlap source starts do not describe the expected topology")
    if not 0 < metrics["overlap_start_sample"] < metrics["overlap_end_sample"] < metrics["samples_per_channel"]:
        raise ControlBuildError("overlap interval is outside the media bounds")
    for key in (
        "overlap_interval_present_pass", "source_ownership_from_isolated_stems_pass",
        "sample_sum_integrity_pass", "technical_clipping_pass", "spatial_separation_pass",
    ):
        if gates.get(key) is not True:
            raise ControlBuildError(f"required overlap technical gate did not pass: {key}")
    for key in (
        "independent_diarization_pass", "independent_overlap_intelligibility_pass",
        "human_playback_review_pass", "production_authority_pass",
    ):
        if gates.get(key) is not False:
            raise ControlBuildError(f"unavailable overlap authority gate was not fail-closed: {key}")
    return metrics


def _validate_alignment(alignment: dict[str, Any], expected_source_sha256: str) -> list[dict[str, Any]]:
    if alignment.get("artifact_sha256") != expected_source_sha256:
        raise ControlBuildError("alignment does not bind the overlap Qwen source")
    if alignment.get("pass") is not True or alignment.get("monotonic") is not True:
        raise ControlBuildError("word/grapheme alignment did not pass")
    authority = alignment.get("alignment_authority")
    if not isinstance(authority, dict):
        raise ControlBuildError("alignment authority is not the expected bounded word/grapheme route")
    if authority.get("method") != "torchaudio_mms_fa_ctc_grapheme_word_alignment":
        raise ControlBuildError("alignment authority method is not the expected MMS-FA route")
    if authority.get("word_timing_runtime_pass") is not True or authority.get("grapheme_ctc_runtime_pass") is not True:
        raise ControlBuildError("bounded word/grapheme authority gates did not pass")
    if any(authority.get(key) is not False for key in (
        "phoneme_forced_alignment_pass", "mfa_style_phoneme_authority", "whisperx_style_word_authority",
    )):
        raise ControlBuildError("alignment authority exceeded its bounded word/grapheme route")
    words = alignment.get("words")
    if not isinstance(words, list) or not words:
        raise ControlBuildError("alignment words are missing")
    previous_end = -1
    for word in words:
        start = word.get("start_sample")
        end = word.get("end_sample")
        if not isinstance(start, int) or not isinstance(end, int) or start < previous_end or end <= start:
            raise ControlBuildError("alignment intervals are invalid or non-monotonic")
        previous_end = end
    return words


def _resolve_continuity_audio(
    line: dict[str, Any], continuity_dir: Path, baseline_path: Path
) -> dict[str, Any]:
    line_id = line.get("line_id")
    expected = line.get("audio_binding", {})
    if line_id == "L01":
        path = baseline_path
    else:
        source_name = Path(str(expected.get("path", ""))).name
        path = continuity_dir / source_name
    result = binding(path, str(expected.get("sha256", "")))
    if result["bytes"] != expected.get("bytes"):
        raise ControlBuildError(f"continuity byte count mismatch for {line_id}")
    return result


def build(
    root: Path,
    output_dir: Path,
    overlap_dir: Path,
    alignment_dir: Path,
    continuity_dir: Path,
) -> dict[str, Any]:
    overlap_path = overlap_dir / "wave64_rows140_142_144_runtime_manifest.json"
    alignment_path = alignment_dir / "row135_mms_fa_word_grapheme_alignment.json"
    viseme_path = alignment_dir / "row136_viseme_coarticulation_fixture.json"
    continuity_manifest_path = continuity_dir / "wave64_qwen3_tts_continuity_matrix_manifest.json"
    continuity_evaluation_path = continuity_dir / "wave64_qwen3_tts_continuity_matrix_evaluation.json"

    overlap = load_object(overlap_path)
    alignment = load_object(alignment_path)
    viseme = load_object(viseme_path)
    continuity_manifest = load_object(continuity_manifest_path)
    continuity_evaluation = load_object(continuity_evaluation_path)
    metrics = _validate_overlap(overlap)
    qwen_source = overlap.get("sources", {}).get("qwen_wav", {})
    words = _validate_alignment(alignment, str(qwen_source.get("sha256", "")))

    if viseme.get("fixture_runtime_pass") is not True or viseme.get("production_phoneme_input_used") is not False:
        raise ControlBuildError("viseme fixture does not preserve its non-production boundary")
    if continuity_evaluation.get("classification") != EXPECTED_CONTINUITY_CLASSIFICATION:
        raise ControlBuildError("continuity evaluation classification is invalid")
    contract = continuity_manifest.get("matrix_contract", {})
    calibration_ids = contract.get("calibration_line_ids", [])
    held_out_ids = contract.get("held_out_line_ids", [])
    if len(calibration_ids) != 5 or len(held_out_ids) != 5 or set(calibration_ids) & set(held_out_ids):
        raise ControlBuildError("calibration and held-out partitions are not five disjoint lines")
    line_metrics = continuity_evaluation.get("line_metrics")
    if not isinstance(line_metrics, list) or {line.get("line_id") for line in line_metrics} != set(calibration_ids + held_out_ids):
        raise ControlBuildError("continuity line inventory does not match the declared partitions")

    overlap_media = {}
    for key, record in overlap.get("overlap_artifacts", {}).items():
        overlap_media[key] = binding(overlap_dir / Path(str(record.get("path", ""))).name, record.get("sha256"))

    shifted_words = []
    for word in words:
        shifted = {
            "label": word["label"],
            "start_sample": word["start_sample"] + metrics["qwen_start_sample"],
            "end_sample": word["end_sample"] + metrics["qwen_start_sample"],
            "confidence": word["confidence"],
        }
        if shifted["end_sample"] > metrics["samples_per_channel"]:
            raise ControlBuildError("shifted Qwen alignment exceeds the overlap media duration")
        shifted_words.append(shifted)

    ownership = {
        "schema_version": "1.0",
        "artifact_type": "wave64_source_level_speaker_ownership_timeline",
        "authority": "isolated_source_stem_diagnostic_not_character_identity_or_independent_diarization",
        "sample_rate_hz": metrics["sample_rate_hz"],
        "samples_per_channel": metrics["samples_per_channel"],
        "segments": [
            {"start_sample": 0, "end_sample": metrics["overlap_start_sample"], "active_source_ids": ["diagnostic_kokoro_source"], "overlap": False},
            {"start_sample": metrics["overlap_start_sample"], "end_sample": metrics["overlap_end_sample"], "active_source_ids": ["diagnostic_kokoro_source", "diagnostic_qwen_source"], "priority_source_id": "diagnostic_qwen_source", "overlap": True},
            {"start_sample": metrics["overlap_end_sample"], "end_sample": metrics["samples_per_channel"], "active_source_ids": ["diagnostic_qwen_source"], "overlap": False},
        ],
        "qwen_word_alignment_shifted_to_mix": shifted_words,
        "media": overlap_media,
        "gates": {
            "timeline_contiguous_pass": True,
            "source_stem_ownership_pass": True,
            "overlap_state_bound_pass": True,
            "word_alignment_within_media_pass": True,
            "independent_diarization_pass": False,
            "visual_active_speaker_ownership_pass": False,
            "production_character_identity_pass": False,
            "independent_playback_review_pass": False,
        },
        "row_complete": False,
    }

    lipsync = {
        "schema_version": "1.0",
        "artifact_type": "wave64_identity_preserving_lipsync_correction_admission",
        "candidate_audio_sha256": qwen_source.get("sha256"),
        "admission_prerequisites": {
            "speech_candidate_accepted_for_production": False,
            "true_phoneme_alignment_authority_pass": False,
            "production_viseme_input_pass": False,
            "target_video_hash_bound": False,
            "face_identity_baseline_hash_bound": False,
            "validated_lipsync_runtime_route_pass": False,
            "independent_speech_video_playback_review_pass": False,
        },
        "bounded_inputs": {
            "word_grapheme_alignment": binding(alignment_path),
            "viseme_fixture": binding(viseme_path),
        },
        "decision": "REFUSE_CORRECTION_PREREQUISITES_INCOMPLETE",
        "correction_executed": False,
        "video_read_or_written": False,
        "identity_drift_claimed_measured": False,
        "frame_corruption_claimed_measured": False,
        "incorrect_speech_claimed_accepted": False,
        "row_complete": False,
    }

    baseline_path = Path(str(continuity_manifest.get("baseline", {}).get("path", "")))
    corpus_entries = []
    for line in line_metrics:
        line_id = line["line_id"]
        role = "calibration" if line_id in calibration_ids else "held_out_test"
        corpus_entries.append({
            "line_id": line_id,
            "role": role,
            "scene_id": line["scene_id"],
            "language": line["language"],
            "language_role": line["language_role"],
            "expected_text": line["expected_text"],
            "audio": _resolve_continuity_audio(line, continuity_dir, baseline_path),
            "duration_seconds": line["technical_audio"]["duration_seconds"],
            "content_evaluation_status": line["multilingual_content_evaluation_status"],
            "normalized_wer": line["normalized_wer"],
            "speaker_similarity_to_reference": line["speaker_similarity_to_reference"],
            "microphone_chain_id": "qwen_base_dry_icl_v1",
            "room_profile_id": "dry_reference_condition",
        })
    corpus_entries.sort(key=lambda entry: entry["line_id"])
    coverage = {
        "disjoint_calibration_test_roles": True,
        "line_count": 10,
        "scene_count": 3,
        "identity_chain_count": 1,
        "certified_character_count": 0,
        "certified_gender_coverage_count": 0,
        "language_roles_present": sorted({entry["language_role"] for entry in corpus_entries}),
        "multilingual_content_authority_pass": False,
        "delivery_style_class_count": 0,
        "nonverbal_event_class_count": 0,
        "room_profile_count": 1,
        "microphone_chain_count": 1,
        "minimum_duration_seconds": min(entry["duration_seconds"] for entry in corpus_entries),
        "maximum_duration_seconds": max(entry["duration_seconds"] for entry in corpus_entries),
        "broad_duration_spread_pass": False,
        "overlap_fixture_role": "diagnostic_only_not_calibration_or_held_out_test",
        "rights_validated_for_final_certification": False,
        "independent_playback_review_pass": False,
        "full_certification_matrix_coverage_pass": False,
    }
    benchmark = {
        "schema_version": "1.0",
        "artifact_type": "wave64_hyperreal_speech_benchmark_certification_corpus",
        "source_continuity_manifest": binding(continuity_manifest_path),
        "source_continuity_evaluation": binding(continuity_evaluation_path),
        "calibration_line_ids": calibration_ids,
        "held_out_test_line_ids": held_out_ids,
        "entries": corpus_entries,
        "diagnostic_fixtures": {
            "overlap_manifest": binding(overlap_path),
            "viseme_fixture": binding(viseme_path),
        },
        "coverage": coverage,
        "row_complete": False,
    }

    execution_timestamp = datetime.now(timezone.utc).isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "row134_speaker_ownership_timeline.json": ownership,
        "row137_lipsync_correction_admission.json": lipsync,
        "row147_benchmark_certification_corpus.json": benchmark,
    }
    for name, value in artifacts.items():
        write_json_atomic(output_dir / name, value)

    source_bindings = {
        "overlap_manifest": binding(overlap_path),
        "alignment": binding(alignment_path),
        "viseme_fixture": binding(viseme_path),
        "continuity_manifest": binding(continuity_manifest_path),
        "continuity_evaluation": binding(continuity_evaluation_path),
    }
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows134_137_147_control_manifest",
        "execution_timestamp": execution_timestamp,
        "classification": CLASSIFICATION,
        "sources": source_bindings,
        "outputs": {name: binding(output_dir / name) for name in artifacts},
        "boundaries": {
            "media_regenerated": False,
            "media_mutated": False,
            "video_read_or_written": False,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    write_json_atomic(output_dir / "wave64_rows134_137_147_control_manifest.json", manifest)
    evaluation = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows134_137_147_control_evaluation",
        "execution_timestamp": execution_timestamp,
        "classification": CLASSIFICATION,
        "manifest_binding": binding(output_dir / "wave64_rows134_137_147_control_manifest.json"),
        "gates": {
            "source_hashes_verified_pass": True,
            "ownership_timeline_technical_pass": True,
            "independent_diarization_pass": False,
            "visual_active_speaker_ownership_pass": False,
            "lipsync_admission_refusal_pass": True,
            "lipsync_correction_executed": False,
            "benchmark_partition_disjoint_pass": True,
            "benchmark_media_hashes_verified_pass": True,
            "benchmark_full_coverage_pass": False,
            "production_authority_pass": False,
        },
        "row_results": {
            "134": {"bounded_control_pass": True, "row_complete": False},
            "137": {"prerequisite_refusal_pass": True, "row_complete": False},
            "147": {"disjoint_partition_and_hash_binding_pass": True, "row_complete": False},
        },
        "remaining_blockers": {
            "134": ["independent diarization, visual active-speaker ownership, production character identity, and playback authority are absent"],
            "137": ["accepted speech, true phoneme authority, production visemes, target video, identity baseline, validated runtime route, and visual playback are absent"],
            "147": ["certified characters/genders, styles, duration spread, nonverbal events, rooms, multilingual QA, rights validation, and playback coverage are incomplete"],
        },
        "boundaries": manifest["boundaries"],
    }
    write_json_atomic(output_dir / "wave64_rows134_137_147_evaluation.json", evaluation)
    return evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overlap-dir", type=Path, required=True)
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--continuity-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    resolve = lambda path: path.resolve() if path.is_absolute() else (root / path).resolve()
    result = build(root, resolve(args.output_dir), resolve(args.overlap_dir), resolve(args.alignment_dir), resolve(args.continuity_dir))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
