#!/usr/bin/env python3
"""Apply hash-bound Rows113-117 decisions to the additive Items/Tracker package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
ITEMS_CSV = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv")
TRACKER_CSV = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv")
ITEMS_REQUIREMENTS = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
TRACKER_REQUIREMENTS = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
WORK_PACKAGE = Path("Plan/10_REGISTRIES/wave64_autonomous_hyperreal_speech_work_package_registry.json")
EVIDENCE_RELATIVE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_HYPERREAL_SPEECH_ROWS113_117_AUTHORITY_20260715.json")
LOADER_PROOF_RELATIVE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_QWEN3_TTS_VOICEDESIGN_LOADER_PROOF_20260715.json")
MODEL_REGISTRY = Path("Plan/Registries/Models/model_registry.jsonl")
MODEL_QUEUE = Path("Plan/Registries/Models/model_runtime_validation_queue.csv")


class TrackingError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TrackingError(f"JSON root must be an object: {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    write_bytes_atomic(path, json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise TrackingError(f"CSV header missing: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_atomic(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def status_for(decision: dict[str, Any]) -> str:
    classification = str(decision.get("classification", ""))
    if not classification:
        raise TrackingError("row decision classification missing")
    return classification


def append_note(current: str, evidence_path: str) -> str:
    marker = f"Rows113-117 authority evidence: {evidence_path}"
    if marker in current:
        return current
    return f"{current.rstrip()} {marker}".strip()


def update_csvs(root: Path, decisions: dict[str, Any], evidence_path: str) -> None:
    item_fields, item_rows = read_csv(root / ITEMS_CSV)
    tracker_fields, tracker_rows = read_csv(root / TRACKER_CSV)
    for number in range(113, 118):
        tracker_id = f"TRK-W64-{number:03d}"
        item_id = f"ITEM-W64-{number:03d}"
        decision = decisions[tracker_id]
        items = [row for row in item_rows if row.get("Item_ID") == item_id]
        trackers = [row for row in tracker_rows if row.get("Tracker_ID") == tracker_id]
        if len(items) != 1 or len(trackers) != 1:
            raise TrackingError(f"Expected one Items and Tracker row for {tracker_id}")
        items[0]["Status"] = status_for(decision)
        items[0]["Notes"] = append_note(items[0].get("Notes", ""), evidence_path)
        trackers[0]["Status"] = status_for(decision)
        trackers[0]["Status_Decision"] = status_for(decision)
        trackers[0]["Notes"] = append_note(trackers[0].get("Notes", ""), evidence_path)
    write_csv_atomic(root / ITEMS_CSV, item_fields, item_rows)
    write_csv_atomic(root / TRACKER_CSV, tracker_fields, tracker_rows)


def update_requirements(root: Path, decisions: dict[str, Any], evidence_path: str) -> None:
    value = load_json(root / ITEMS_REQUIREMENTS)
    requirements = value.get("requirements", [])
    for number in range(113, 118):
        tracker_id = f"TRK-W64-{number:03d}"
        matches = [item for item in requirements if item.get("tracker_id") == tracker_id]
        if len(matches) != 1:
            raise TrackingError(f"Expected one requirements row for {tracker_id}")
        matches[0]["status"] = status_for(decisions[tracker_id])
        matches[0]["decision_evidence"] = evidence_path
        matches[0]["remaining_blockers"] = list(decisions[tracker_id].get("blockers", []))
    value["status"] = "Implementation_Active_Rows113_115_117_PassLike_Row116_Blocked"
    payload = json_bytes(value)
    write_bytes_atomic(root / ITEMS_REQUIREMENTS, payload)
    write_bytes_atomic(root / TRACKER_REQUIREMENTS, payload)


def update_work_package(root: Path, decisions: dict[str, Any], evidence_path: str) -> None:
    value = load_json(root / WORK_PACKAGE)
    packages = value.get("work_packages", [])
    for number in range(113, 118):
        tracker_id = f"TRK-W64-{number:03d}"
        matches = [item for item in packages if item.get("tracker_id") == tracker_id]
        if len(matches) != 1:
            raise TrackingError(f"Expected one work-package row for {tracker_id}")
        matches[0]["status"] = status_for(decisions[tracker_id])
        matches[0]["decision_evidence"] = evidence_path
    write_json_atomic(root / WORK_PACKAGE, value)


def update_model_runtime_records(root: Path) -> dict[str, int]:
    proof_path = root / LOADER_PROOF_RELATIVE
    proof = load_json(proof_path)
    if proof.get("classification") != "QWEN3_TTS_VOICEDESIGN_LOAD_PROOF_PASS_AUDIO_GENERATION_PENDING":
        raise TrackingError("Qwen3-TTS loader proof classification is invalid")
    expected_hashes = {item["sha256"] for item in proof.get("model_files", [])}
    logical_path_by_hash = {
        item["sha256"]: item["path"]
        for item in proof.get("model_files", [])
        if item.get("sha256") and item.get("path")
    }
    if len(expected_hashes) != 11:
        raise TrackingError("Qwen3-TTS loader proof does not bind 11 unique files")
    registry_path = root / MODEL_REGISTRY
    registry_records = []
    for line_number, line in enumerate(registry_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TrackingError(f"model registry row {line_number} is not an object")
        registry_records.append(value)
    matches = [
        record
        for record in registry_records
        if record.get("workflow_lane") == "wave64_hyperreal_speech_rows113_117"
        and record.get("source_model_id") == "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
        and record.get("source_model_version_id") == "5ecdb67327fd37bb2e042aab12ff7391903235d3"
    ]
    if len(matches) != 11 or {record.get("sha256") for record in matches} != expected_hashes:
        raise TrackingError("model registry does not exactly match the Qwen3-TTS loader proof file set")
    for record in matches:
        record["local_path"] = logical_path_by_hash[record["sha256"]]
        record["compatibility_status"] = "loader_validated_audio_generation_pending"
        record["runtime_validation_status"] = "load_proven_audio_generation_pending"
        record["qa_status"] = "loader_pass_generation_not_tested"
        record["last_tested_at"] = proof["created_at"]
        evidence_paths = record.setdefault("evidence_paths", [])
        proof_relative = LOADER_PROOF_RELATIVE.as_posix()
        if proof_relative not in evidence_paths:
            evidence_paths.append(proof_relative)
        record["known_issues"] = [
            "Official loader passed; speech generation, audio decode, playback, and production authority remain required."
        ]
    registry_payload = "".join(json.dumps(record, separators=(",", ":"), ensure_ascii=True) + "\n" for record in registry_records)
    write_bytes_atomic(registry_path, registry_payload.encode("utf-8"))

    fields, queue_rows = read_csv(root / MODEL_QUEUE)
    queue_matches = [
        row
        for row in queue_rows
        if row.get("workflow_lane") == "wave64_hyperreal_speech_rows113_117"
        and row.get("model_name") == "qwen3_tts_1_7b_voicedesign"
    ]
    if len(queue_matches) != 11:
        raise TrackingError("runtime queue does not contain exactly 11 selected Qwen3-TTS files")
    path_by_suffix = {
        record["record_id"].rsplit("-", 1)[-1]: record["local_path"]
        for record in matches
    }
    for row in queue_matches:
        suffix = row["queue_id"].rsplit("-", 1)[-1]
        if suffix not in path_by_suffix:
            raise TrackingError(f"runtime queue row has no matching Qwen registry record: {row['queue_id']}")
        row["local_path"] = path_by_suffix[suffix]
        row["status"] = "load_proven_audio_generation_pending"
        row["evidence_path"] = LOADER_PROOF_RELATIVE.as_posix()
    write_csv_atomic(root / MODEL_QUEUE, fields, queue_rows)
    return {"model_registry_records_updated": len(matches), "runtime_queue_rows_updated": len(queue_matches)}


def mirror_evidence(root: Path, source_relative: Path) -> tuple[str, str]:
    source = root / source_relative
    if not source.is_file():
        raise TrackingError(f"evidence source missing: {source}")
    relative_under_instructions = source_relative.relative_to("Plan/Instructions/QA/Evidence")
    target = root / "Plan/Tracker/Evidence" / relative_under_instructions
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    source_hash = sha256_file(source)
    if sha256_file(target) != source_hash:
        raise TrackingError(f"evidence mirror hash mismatch: {target}")
    return source_relative.as_posix(), target.relative_to(root).as_posix()


def apply(root: Path, out: Path) -> dict[str, Any]:
    evidence_path = root / EVIDENCE_RELATIVE
    evidence = load_json(evidence_path)
    if evidence.get("classification") != "W64_ROWS113_117_IMPLEMENTATION_PARTIAL_FAIL_CLOSED":
        raise TrackingError("Rows113-117 authority evidence classification is invalid")
    decisions = evidence.get("row_decisions", {})
    expected = {f"TRK-W64-{number:03d}" for number in range(113, 118)}
    if set(decisions) != expected:
        raise TrackingError("Rows113-117 authority evidence row set is incomplete")
    evidence_relative = EVIDENCE_RELATIVE.as_posix()
    update_csvs(root, decisions, evidence_relative)
    update_requirements(root, decisions, evidence_relative)
    update_work_package(root, decisions, evidence_relative)
    model_updates = update_model_runtime_records(root)
    mirror_sources = [
        EVIDENCE_RELATIVE,
        Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_VOICE_REFERENCE_CARD_LIBRIVOX_CHRIS_GORINGE_20260715.json"),
        Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_VOICE_REFERENCE_INTAKE_LIBRIVOX_CHRIS_GORINGE_20260715.json"),
        Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/W64_QWEN3_TTS_VOICEDESIGN_LOADER_PROOF_20260715.json"),
    ]
    mirrors = []
    for source in mirror_sources:
        left, right = mirror_evidence(root, source)
        mirrors.append({"source": left, "mirror": right, "sha256": sha256_file(root / source)})
    result = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows113_117_tracking_reconciliation",
        "created_at": now_iso(),
        "classification": "W64_ROWS113_117_ITEMS_TRACKER_RECONCILED",
        "authority_evidence": {"path": evidence_relative, "sha256": sha256_file(evidence_path)},
        "row_decisions": decisions,
        "mirrors": mirrors,
        "requirements_mirror_byte_identical": (root / ITEMS_REQUIREMENTS).read_bytes() == (root / TRACKER_REQUIREMENTS).read_bytes(),
        "model_runtime_updates": model_updates,
        "boundaries": {
            "row116_promoted": False,
            "candidate_generated": False,
            "production_authority_claimed": False,
            "content_based_suppression": False,
        },
    }
    write_json_atomic(out, result)
    mirror_evidence(root, out.relative_to(root))
    return result


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    out = args.out.resolve() if args.out.is_absolute() else (root / args.out).resolve()
    try:
        result = apply(root, out)
        print(json.dumps({"classification": result["classification"], "output": out.relative_to(root).as_posix()}, indent=2))
        return 0
    except (TrackingError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"classification": "W64_ROWS113_117_TRACKING_RECONCILIATION_FAILED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
