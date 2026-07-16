#!/usr/bin/env python3
"""Package Wave64 Rows135, 136, and 138 evidence and reconcile blocked states."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_CLASSIFICATION = "PASS_ROWS135_136_138_BOUNDED_AUTOMATED_RUNTIME_PRODUCTION_AUTHORITY_BLOCKED"
ROW_STATUS = {
    "135": "Blocked_Mandated_Alignment_Assets_And_True_Phoneme_Authority_Pending",
    "136": "Blocked_Production_Phoneme_Alignment_Input_Pending_Compiler_Runtime_Pass",
    "138": "Blocked_Independent_Spatial_Playback_And_Production_Scene_Authority_Pending",
}
ROW_BLOCKERS = {
    "135": [
        "true MFA-style phoneme forced-alignment authority is not implemented",
        "mandatory Whisper large-v3-turbo, Pyannote Community-1, and LatentSync 1.6 route proof is incomplete",
    ],
    "136": ["production phoneme-alignment input is unavailable; the passing compiler runtime is fixture-only"],
    "138": ["independent full-play spatial listening review and final production-scene authority are pending"],
}


class FinalizationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise FinalizationError(f"required file is missing: {path}")
    return {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def copy_exact(source: Path, destination: Path) -> dict[str, Any]:
    source_binding = binding(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != source_binding["sha256"]:
            raise FinalizationError(f"durable artifact hash conflict: {destination}")
    else:
        shutil.copy2(source, destination)
    durable = binding(destination)
    if durable["sha256"] != source_binding["sha256"]:
        raise FinalizationError(f"durable artifact copy mismatch: {destination}")
    return durable


def validate_evaluation(evaluation: dict[str, Any]) -> None:
    if evaluation.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("evaluation classification is not the expected bounded runtime pass")
    gates = evaluation.get("gates")
    rows = evaluation.get("row_results")
    boundaries = evaluation.get("boundaries")
    if not all(isinstance(value, dict) for value in (gates, rows, boundaries)):
        raise FinalizationError("evaluation gates, row results, or boundaries are missing")
    required_true = (
        "runtime_manifest_lineage_pass", "source_nonmutation_pass", "word_grapheme_alignment_runtime_pass",
        "viseme_fixture_runtime_pass", "spatial_decode_pass", "spatial_duration_pass",
        "spatial_channel_motion_pass", "spatial_clipping_pass", "spatial_intelligibility_pass",
        "spatial_speaker_identity_pass",
    )
    if any(gates.get(key) is not True for key in required_true):
        raise FinalizationError("a required bounded automated gate did not pass")
    required_false = (
        "phoneme_authority_pass", "viseme_production_input_pass", "independent_playback_review_pass",
        "production_scene_authority_pass",
    )
    if any(gates.get(key) is not False for key in required_false):
        raise FinalizationError("an unavailable authority gate was not fail-closed")
    if any(rows.get(number, {}).get("row_complete") is not False for number in ROW_STATUS):
        raise FinalizationError("a row incorrectly claims completion")
    if any(boundaries.get(key) is not False for key in (
        "true_phoneme_authority_complete", "mandated_row135_asset_set_complete",
        "independent_playback_review_complete", "production_scene_authority_complete", "production_ready",
    )):
        raise FinalizationError("evaluation boundaries improperly claim production authority")


def update_rows(path: Path, id_column: str, prefix: str, evidence_root: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found: set[str] = set()
    for row in rows:
        row_id = row[id_column]
        for number, status in ROW_STATUS.items():
            if row_id != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
            row["Status"] = status
            row["Coverage_Audit_Status"] = "bounded_runtime_evidence_recorded_exact_authority_blockers_preserved"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence
            if "Status_Decision" in row:
                row["Status_Decision"] = status.lower()
            row["Notes"] = (
                f"Hash-bound Rows135/136/138 local runtime and automated QA are recorded in {evidence}. "
                "MMS word/grapheme timing is not MFA phoneme authority; the viseme result is fixture-only; "
                "spatial automated metrics are not independent playback authority. content_based_suppression=false."
            )
    if found != set(ROW_STATUS):
        raise FinalizationError(f"missing expected rows in {path}: {sorted(set(ROW_STATUS) - found)}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def build(root: Path, runtime_dir: Path, durable_dir_name: str) -> dict[str, Any]:
    names = (
        "row135_mms_fa_word_grapheme_alignment.json",
        "row136_viseme_coarticulation_fixture.json",
        "row138_l01_spatial_scene_pcm24_stereo.wav",
        "wave64_alignment_viseme_spatial_runtime_manifest.json",
        "wave64_alignment_viseme_spatial_evaluation.json",
    )
    manifest = load_object(runtime_dir / names[3])
    evaluation = load_object(runtime_dir / names[4])
    validate_evaluation(evaluation)
    if manifest.get("classification") != "W64_ROWS135_136_138_BOUNDED_RUNTIME_PASS_PRODUCTION_AUTHORITY_BLOCKED":
        raise FinalizationError("runtime manifest classification is invalid")
    expected_manifest_hash = evaluation.get("bindings", {}).get("manifest", {}).get("sha256")
    if expected_manifest_hash != sha256_file(runtime_dir / names[3]):
        raise FinalizationError("evaluation does not bind the exact runtime manifest")

    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(runtime_dir / name, durable_dir / name) for name in names}
    runtime = {name: binding(runtime_dir / name) for name in names}
    implementation = {
        key: binding(root / relative)
        for key, relative in {
            "runner": "Plan/07_IMPLEMENTATION/scripts/run_wave64_alignment_viseme_spatial.py",
            "evaluator": "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_alignment_viseme_spatial.py",
            "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows135_136_138.py",
            "runner_tests": "Plan/Instructions/QA/Scripts/test_run_wave64_alignment_viseme_spatial.py",
            "evaluator_tests": "Plan/Instructions/QA/Scripts/test_evaluate_wave64_alignment_viseme_spatial.py",
            "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows135_136_138.py",
        }.items()
    }
    implemented = {
        "135": "genuine Torchaudio MMS_FA CTC word/grapheme timing for immutable L01 with monotonic source-sample intervals and confidence",
        "136": "versioned deterministic phoneme-fixture to viseme/coarticulation compiler covering required articulation categories without interval overlap",
        "138": "deterministic stereo motion, distance, elevation, occlusion, early-reflection, reverb, and microphone-perspective render with ASR and identity QA",
    }
    common = {
        "schema_version": "1.0",
        "execution_timestamp": evaluation["execution_timestamp"],
        "runtime_classification": evaluation["classification"],
        "durable_artifacts": durable,
        "runtime_artifacts": runtime,
        "implementation": implementation,
        "manifest": manifest,
        "automated_evaluation": evaluation,
        "boundaries": {
            **evaluation["boundaries"],
            "media_regenerated": False,
            "source_media_mutated": False,
            "derived_spatial_media_created": True,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number in ROW_STATUS:
        record = {
            **common,
            "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence",
            "row": {
                "item_id": f"ITEM-W64-{number}",
                "tracker_id": f"TRK-W64-{number}",
                "implemented_capability": implemented[number],
                "status": ROW_STATUS[number],
                "automated_gates": evaluation["row_results"][number],
                "blockers": ROW_BLOCKERS[number],
                "pass_like": False,
            },
            "row_complete": False,
        }
        name = f"WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
        write_json_atomic(qa_root / name, record)
        write_json_atomic(tracker_root / name, record)

    update_rows(
        root / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
        "Item_ID", "ITEM", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    update_rows(
        root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
        "Tracker_ID", "TRK", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    return {
        "classification": "WAVE64_SPEECH_ROWS135_136_138_RUNTIME_RECONCILED_BLOCKED_CERTIFICATION",
        "durable_artifacts": durable,
        "row_status": ROW_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--durable-dir-name", required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    runtime_dir = args.runtime_dir.resolve() if args.runtime_dir.is_absolute() else (root / args.runtime_dir).resolve()
    try:
        result = build(root, runtime_dir, args.durable_dir_name)
    except Exception as exc:
        print(json.dumps({"classification": "WAVE64_SPEECH_ROWS135_136_138_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
