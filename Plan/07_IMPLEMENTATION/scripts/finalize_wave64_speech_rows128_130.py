#!/usr/bin/env python3
"""Package Wave64 Rows128-130 evidence and reconcile their exact blocked states."""

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


EXPECTED_CLASSIFICATION = "PASS_WAVE64_ROWS129_130_AUTOMATED_QA_ROW128_IDENTITY_AUTHORITY_BLOCKED"
ROW_STATUS = {
    "128": "Blocked_Production_Character_Identity_And_Playback_Authority_Pending",
    "129": "Blocked_Independent_Playback_And_Production_Recording_Chain_Authority_Pending",
    "130": "Blocked_Independent_Before_After_Playback_And_Production_Restoration_Authority_Pending",
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
    found: set[str] = set()
    for row in rows:
        row_id = row[id_column]
        for number, status in ROW_STATUS.items():
            if row_id != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
            row["Status"] = status
            row["Coverage_Audit_Status"] = "runtime_implementation_evidence_recorded_exact_authority_blockers_preserved"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence
                row["Status_Decision"] = status.lower()
            row["Notes"] = (
                f"Hash-bound Rows128-130 acoustics runtime and automated QA are recorded in {evidence}. "
                "Source and dry bytes are retained; subjective playback and production promotion remain fail-closed. "
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


def build(root: Path, runtime_dir: Path, durable_dir_name: str) -> dict[str, Any]:
    manifest_path = runtime_dir / "wave64_speech_rows128_130_runtime_manifest.json"
    evaluation_path = runtime_dir / "wave64_speech_rows128_130_evaluation.json"
    manifest = load_object(manifest_path)
    evaluation = load_object(evaluation_path)
    if evaluation.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("evaluation classification is not the expected partial pass")
    rows = evaluation.get("rows", {})
    if rows.get("128", {}).get("production_character_identity_authority_pass") is not False:
        raise FinalizationError("Row128 production-character authority is not fail-closed")
    if rows.get("129", {}).get("automated_runtime_pass") is not True or rows.get("130", {}).get("automated_runtime_pass") is not True:
        raise FinalizationError("Rows129-130 automated runtime gates did not pass")
    if any(rows.get(number, {}).get("row_complete") is not False for number in ROW_STATUS):
        raise FinalizationError("a row incorrectly claims completion")

    runtime_names = (
        "indexed_nonverbal_voice_candidate.wav",
        "qwen3_clone_virtual_microphone.wav",
        "qwen3_clone_restored.wav",
        manifest_path.name,
        evaluation_path.name,
    )
    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(runtime_dir / name, durable_dir / name) for name in runtime_names}
    runtime = {name: binding(runtime_dir / name) for name in runtime_names}
    implementation = {
        name: binding(root / relative)
        for name, relative in {
            "runner": "Plan/07_IMPLEMENTATION/scripts/run_wave64_speech_acoustics.py",
            "evaluator": "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_speech_acoustics.py",
            "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows128_130.py",
            "runner_tests": "Plan/Instructions/QA/Scripts/test_run_wave64_speech_acoustics.py",
            "evaluator_tests": "Plan/Instructions/QA/Scripts/test_evaluate_wave64_speech_acoustics.py",
            "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows128_130.py",
        }.items()
    }
    common = {
        "schema_version": "1.0",
        "execution_timestamp": evaluation["execution_timestamp"],
        "runtime_classification": evaluation["classification"],
        "durable_artifacts": durable,
        "runtime_artifacts": runtime,
        "implementation": implementation,
        "manifest_bindings": manifest,
        "automated_evaluation": evaluation,
        "boundaries": evaluation["boundaries"],
    }
    row_records = {
        "128": {
            "implemented_capability": "functional-index-bound nonverbal vocal event selection and immutable PCM candidate rendering",
            "status": ROW_STATUS["128"],
            "blockers": evaluation["remaining_blockers"]["128"],
        },
        "129": {
            "implemented_capability": "nondestructive deterministic virtual microphone, proximity, compression, saturation, and exact recipe lineage",
            "status": ROW_STATUS["129"],
            "blockers": evaluation["remaining_blockers"]["129"],
        },
        "130": {
            "implemented_capability": "bounded de-click, de-plosive high-pass, conditional de-ess, level limiting, and before/after automated QA",
            "status": ROW_STATUS["130"],
            "blockers": evaluation["remaining_blockers"]["130"],
        },
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number, row_record in row_records.items():
        record = {
            **common,
            "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence",
            "row": {
                "item_id": f"ITEM-W64-{number}",
                "tracker_id": f"TRK-W64-{number}",
                **row_record,
                "automated_gates": rows[number],
                "pass_like": False,
            },
            "row_complete": False,
        }
        name = f"WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
        write_json_atomic(qa_root / name, record)
        write_json_atomic(tracker_root / name, record)

    update_rows(root / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv", "Item_ID", "ITEM", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake")
    update_rows(root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv", "Tracker_ID", "TRK", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake")
    return {"classification": "WAVE64_SPEECH_ROWS128_130_RUNTIME_RECONCILED_BLOCKED_CERTIFICATION", "durable_artifacts": durable, "row_status": ROW_STATUS}


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
        print(json.dumps({"classification": "WAVE64_SPEECH_ROWS128_130_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
