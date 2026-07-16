#!/usr/bin/env python3
"""Package Wave64 Rows134, 137, and 147 evidence and reconcile blocked states."""

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


EXPECTED_CLASSIFICATION = "W64_ROWS134_137_147_CONTROLS_EXECUTED_PRODUCTION_BLOCKED"
ARTIFACT_NAMES = (
    "row134_speaker_ownership_timeline.json",
    "row137_lipsync_correction_admission.json",
    "row147_benchmark_certification_corpus.json",
    "wave64_rows134_137_147_control_manifest.json",
    "wave64_rows134_137_147_evaluation.json",
)
ROW_STATUS = {
    "134": "Blocked_Independent_Diarization_Visual_Ownership_And_Playback_Authority_Pending",
    "137": "Blocked_Accepted_Speech_Phoneme_Video_Identity_And_Playback_Prerequisites_Pending",
    "147": "Blocked_Full_Certification_Corpus_Coverage_Rights_And_Playback_Authority_Pending",
}
ROW_IMPLEMENTED = {
    "134": "sample-indexed three-segment source-level ownership and overlap timeline bound to isolated stems and shifted word alignment",
    "137": "fail-closed lip-sync correction admission that refuses video mutation until every speech, alignment, identity, runtime, and playback prerequisite passes",
    "147": "hash-bound ten-line benchmark registry with immutable disjoint five-line calibration and five-line held-out-test roles plus an explicit incomplete coverage matrix",
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


def validate_packet(runtime_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = runtime_dir / ARTIFACT_NAMES[3]
    evaluation_path = runtime_dir / ARTIFACT_NAMES[4]
    manifest = load_object(manifest_path)
    evaluation = load_object(evaluation_path)
    if manifest.get("classification") != EXPECTED_CLASSIFICATION or evaluation.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("runtime classification is not the expected bounded control result")
    if evaluation.get("manifest_binding", {}).get("sha256") != sha256_file(manifest_path):
        raise FinalizationError("evaluation does not bind the exact runtime manifest")
    for name in ARTIFACT_NAMES[:3]:
        expected = manifest.get("outputs", {}).get(name, {})
        actual = binding(runtime_dir / name)
        if expected.get("sha256") != actual["sha256"] or expected.get("bytes") != actual["bytes"]:
            raise FinalizationError(f"runtime manifest output binding mismatch: {name}")
    gates = evaluation.get("gates", {})
    for key in (
        "source_hashes_verified_pass", "ownership_timeline_technical_pass", "lipsync_admission_refusal_pass",
        "benchmark_partition_disjoint_pass", "benchmark_media_hashes_verified_pass",
    ):
        if gates.get(key) is not True:
            raise FinalizationError(f"required bounded gate did not pass: {key}")
    for key in (
        "independent_diarization_pass", "visual_active_speaker_ownership_pass", "lipsync_correction_executed",
        "benchmark_full_coverage_pass", "production_authority_pass",
    ):
        if gates.get(key) is not False:
            raise FinalizationError(f"unavailable authority gate was not fail-closed: {key}")
    rows = evaluation.get("row_results", {})
    if any(rows.get(number, {}).get("row_complete") is not False for number in ROW_STATUS):
        raise FinalizationError("a row incorrectly claims completion")
    boundaries = evaluation.get("boundaries", {})
    if any(boundaries.get(key) is not False for key in (
        "media_regenerated", "media_mutated", "video_read_or_written", "subjective_review_fabricated",
        "production_promotion_claimed", "content_based_suppression", "aws_or_ec2_used", "mask_or_wave71_touched",
    )):
        raise FinalizationError("a protected boundary is not fail-closed")
    return manifest, evaluation


def update_rows(path: Path, id_column: str, prefix: str, evidence_root: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found: set[str] = set()
    for row in rows:
        for number, status in ROW_STATUS.items():
            if row[id_column] != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
            row["Status"] = status
            row["Coverage_Audit_Status"] = "bounded_control_evidence_recorded_exact_authority_blockers_preserved"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence
            if "Status_Decision" in row:
                row["Status_Decision"] = status.lower()
            row["Notes"] = (
                f"Hash-bound Rows134/137/147 controls are recorded in {evidence}. Source-level ownership is not "
                "independent diarization or visual character ownership; lip-sync correction was refused before video "
                "access; the disjoint benchmark pilot does not satisfy the full certification matrix. "
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
    manifest, evaluation = validate_packet(runtime_dir)
    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(runtime_dir / name, durable_dir / name) for name in ARTIFACT_NAMES}
    runtime = {name: binding(runtime_dir / name) for name in ARTIFACT_NAMES}
    implementation = {
        key: binding(root / relative)
        for key, relative in {
            "builder": "Plan/07_IMPLEMENTATION/scripts/build_wave64_speech_ownership_lipsync_benchmark.py",
            "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows134_137_147.py",
            "builder_tests": "Plan/Instructions/QA/Scripts/test_build_wave64_speech_ownership_lipsync_benchmark.py",
            "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows134_137_147.py",
        }.items()
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
        "boundaries": evaluation["boundaries"],
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number, status in ROW_STATUS.items():
        record = {
            **common,
            "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence",
            "row": {
                "item_id": f"ITEM-W64-{number}",
                "tracker_id": f"TRK-W64-{number}",
                "implemented_capability": ROW_IMPLEMENTED[number],
                "status": status,
                "automated_gates": evaluation["row_results"][number],
                "blockers": evaluation["remaining_blockers"][number],
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
        "classification": "WAVE64_SPEECH_ROWS134_137_147_CONTROLS_RECONCILED_BLOCKED_CERTIFICATION",
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
    result = build(root, runtime_dir, args.durable_dir_name)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
