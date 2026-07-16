#!/usr/bin/env python3
"""Package immutable speech evidence and reconcile Wave64 Rows124-127."""

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


ROW_STATUS = {
    "124": "Blocked_Production_Voice_Authority_And_Multi_Reference_Validation_Pending",
    "125": "Blocked_Designed_Voice_Continuity_And_Playback_Approval_Pending",
    "126": "Blocked_Unmeasured_Prosody_Control_Claims_Pending",
    "127": "Blocked_Delivery_Style_Intensity_And_Playback_Authority_Pending",
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
    value = json.loads(path.read_text(encoding="utf-8-sig"))
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


def update_rows(path: Path, id_column: str, prefix: str, evidence_root: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found = set()
    for row in rows:
        row_id = row[id_column]
        for number, status in ROW_STATUS.items():
            if row_id == f"{prefix}-W64-{number}":
                found.add(number)
                row["Status"] = status
                row["Coverage_Audit_Status"] = "runtime_implementation_evidence_recorded_exact_blockers_preserved"
                evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
                if "Evidence_Path" in row:
                    row["Evidence_Path"] = evidence
                    row["Status_Decision"] = status.lower()
                row["Notes"] = (
                    f"Hash-bound runtime implementation and exact blocked certification state recorded in {evidence}. "
                    "No rejected candidate rerun, media mutation, subjective-review fabrication, or production promotion. "
                    "content_based_suppression=false."
                )
    if found != set(ROW_STATUS):
        raise FinalizationError(f"missing expected rows in {path}: {sorted(set(ROW_STATUS) - found)}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def build(root: Path, runtime_dir: Path) -> dict[str, Any]:
    wav = runtime_dir / "qwen3_tts_base_icl_clone_seed12401.wav"
    manifest_path = runtime_dir / "qwen3_tts_base_icl_clone_seed12401.manifest.json"
    evaluation_path = runtime_dir / "qwen3_tts_base_icl_clone_seed12401.evaluation.json"
    manifest = load_object(manifest_path)
    evaluation = load_object(evaluation_path)
    if manifest.get("candidate_id") != "W64-QWEN3-BASE-ICL-CLONE-SEED-12401":
        raise FinalizationError("unexpected clone candidate ID")
    if evaluation.get("classification") != "PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED":
        raise FinalizationError("clone evaluation classification is not the expected partial pass")
    gates = evaluation.get("gates", {})
    required_true = ("technical_audio_pass", "candidate_asr_pass", "chain_specific_speaker_identity_pass", "prosody_measurement_complete")
    if any(gates.get(name) is not True for name in required_true):
        raise FinalizationError("clone evaluation is missing required automated passes")
    if gates.get("raw_dialogue_timing_pass") is not False or gates.get("row_complete") is not False:
        raise FinalizationError("clone evaluation no longer preserves the blocked timing/completion boundary")

    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_qwen3_tts_base_icl_clone_20260715T195516-0500"
    durable = {
        "candidate": copy_exact(wav, durable_dir / wav.name),
        "candidate_manifest": copy_exact(manifest_path, durable_dir / manifest_path.name),
        "candidate_evaluation": copy_exact(evaluation_path, durable_dir / evaluation_path.name),
    }
    implementation = {
        name: binding(root / relative)
        for name, relative in {
            "acquisition_preparer": "Plan/07_IMPLEMENTATION/scripts/prepare_wave64_qwen3_tts_base_acquisition.py",
            "clone_runner": "Plan/07_IMPLEMENTATION/scripts/run_wave64_qwen3_tts_voice_clone.py",
            "clone_evaluator": "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_qwen3_tts_voice_clone.py",
            "acquisition_tests": "Plan/Instructions/QA/Scripts/test_prepare_wave64_qwen3_tts_base_acquisition.py",
            "runner_tests": "Plan/Instructions/QA/Scripts/test_run_wave64_qwen3_tts_voice_clone.py",
            "evaluator_tests": "Plan/Instructions/QA/Scripts/test_evaluate_wave64_qwen3_tts_voice_clone.py",
        }.items()
    }
    existing_voice_design = {
        "candidate": binding(root / "runtime_artifacts/wave64_qwen3_tts_candidate/20260715T190042-0500_seed12345/qwen3_tts_voicedesign_seed12345.wav"),
        "candidate_manifest": binding(root / "runtime_artifacts/wave64_qwen3_tts_candidate/20260715T190042-0500_seed12345/qwen3_tts_voicedesign_seed12345.manifest.json"),
        "row123_evidence": binding(root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW123.json"),
    }
    emotion_authority = binding(root / "Plan/Instructions/QA/Evidence/Wave64/W64_CV3_EMOTION2VEC_LOCAL_CALIBRATION_20260715T001113-0500.json")
    acquisition_summary = binding(root / "runtime_artifacts/model_acquisition/wave64_qwen3_tts_1_7b_base/preparation_summary.json")
    common = {
        "schema_version": "1.0",
        "execution_timestamp": evaluation["execution_timestamp"],
        "runtime_classification": evaluation["classification"],
        "durable_artifacts": durable,
        "runtime_artifacts": {"candidate": binding(wav), "candidate_manifest": binding(manifest_path), "candidate_evaluation": binding(evaluation_path)},
        "implementation": implementation,
        "acquisition_summary": acquisition_summary,
        "automated_metrics": evaluation["candidate"],
        "automated_gates": gates,
        "boundaries": evaluation["boundaries"],
    }
    rows = {
        "124": {
            "implemented_capability": "pinned Qwen3-TTS Base ICL reference-conditioned cloning with exact reference/model/package lineage and calibrated identity evaluation",
            "status": ROW_STATUS["124"],
            "pass_like": False,
            "blockers": ["only one evaluation reference and one candidate line are bound; multi-reference continuity/drift/leakage validation is incomplete", "the public-domain evaluation reference is not a locked production character identity authority", "raw timing failed and independent listening/final production authority remain pending"],
        },
        "125": {
            "implemented_capability": "immutable Qwen3-TTS VoiceDesign seed/model/configuration baseline distinct from the ICL clone route",
            "status": ROW_STATUS["125"],
            "pass_like": False,
            "existing_voice_design": existing_voice_design,
            "blockers": ["the existing designed candidate failed its raw timing gate", "a multi-line continuity corpus, character approval record, independent playback review, and locked production voice remain absent"],
        },
        "126": {
            "implemented_capability": "deterministic F0, raw pace, articulation-rate, pause, voiced-frame, technical, timing, and ASR measurement on immutable output",
            "status": ROW_STATUS["126"],
            "pass_like": False,
            "blockers": ["one candidate does not establish target-versus-output distributions or cross-line continuity", "emphasis and articulation quality are not independently measured; no control-effect intervention matrix exists", "raw timing failed and playback review remains pending"],
        },
        "127": {
            "implemented_capability": "separate emotion_class, delivery_style, and intensity evidence fields with unsupported focused/controlled targets left unset",
            "status": ROW_STATUS["127"],
            "pass_like": False,
            "emotion2vec_authority": emotion_authority,
            "blockers": ["focused delivery style and controlled intensity are not emotion2vec classes and were not force-mapped", "no calibrated delivery-style or intensity evaluator has passed this candidate", "independent playback and final production authority remain pending"],
        },
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number, row in rows.items():
        record = {**common, "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence", "row": {"item_id": f"ITEM-W64-{number}", "tracker_id": f"TRK-W64-{number}", **row}, "row_complete": False}
        name = f"WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
        write_json_atomic(qa_root / name, record)
        write_json_atomic(tracker_root / name, record)

    update_rows(root / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv", "Item_ID", "ITEM", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake")
    update_rows(root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv", "Tracker_ID", "TRK", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake")
    return {"classification": "WAVE64_SPEECH_ROWS124_127_RUNTIME_RECONCILED_BLOCKED_CERTIFICATION", "durable_artifacts": durable, "row_status": ROW_STATUS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--runtime-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    runtime_dir = args.runtime_dir.resolve() if args.runtime_dir.is_absolute() else (root / args.runtime_dir).resolve()
    try:
        result = build(root, runtime_dir)
    except Exception as exc:
        print(json.dumps({"classification": "WAVE64_SPEECH_ROWS124_127_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
