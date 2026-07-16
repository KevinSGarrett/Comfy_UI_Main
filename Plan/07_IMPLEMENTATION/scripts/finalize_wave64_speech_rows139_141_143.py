#!/usr/bin/env python3
"""Package Wave64 Rows139, 141, and 143 evidence without promoting authority."""

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


EXPECTED_CLASSIFICATION = "W64_ROWS139_141_143_PACKET_PREPARED_PRODUCTION_AUTHORITY_BLOCKED"
ROW_STATUS = {
    "139": "Blocked_Independent_Full_Duration_Playback_And_Production_Mix_Authority_Pending",
    "141": "Blocked_Mandatory_Ensemble_Assets_And_Production_Authority_Pending",
    "143": "Blocked_Real_Human_Playback_Record_Pending_Request_Packet_Pass",
}
ROW_BLOCKERS = {
    "139": ["independent full-duration playback and production mix authority are pending"],
    "141": [
        "measured RT60 is outside the allowed range",
        "measured reverb tail is outside the allowed range",
        "mandatory ensemble assets, runtime proof, playback proof, and production authority are pending",
    ],
    "143": ["a real independent human playback record and proof bundle are pending"],
}
RUNTIME_FILES = (
    "ambience_bed_pcm24_stereo_16k.wav",
    "current_ambience_pcm24_stereo_16k.wav",
    "dry_dialogue_pcm24_stereo_16k.wav",
    "final_mix_pcm24_stereo_16k.wav",
    "previous_ambience_pcm24_stereo_16k.wav",
    "row139_spatial_room_evidence_bundle.json",
    "row141_spatial_room_evaluator_report.json",
    "row143_human_playback_review_request.json",
    "spatial_dialogue_pcm24_stereo_16k.wav",
    "wave31_room_acoustics_manifest.json",
    "wave31_spatial_audio_mix_manifest.json",
    "wave64_speech_mix_evaluator_review_packet_manifest.json",
)


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


def require_bound_file(record: dict[str, Any], path: Path, label: str) -> None:
    expected = record.get("sha256")
    if expected != sha256_file(path):
        raise FinalizationError(f"{label} SHA-256 binding mismatch")


def validate_packet(manifest: dict[str, Any], report: dict[str, Any], request: dict[str, Any]) -> None:
    if manifest.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("packet classification is invalid")
    if manifest.get("source_media_unchanged") is not True:
        raise FinalizationError("source non-mutation is not proven")
    for number, expected_status in ROW_STATUS.items():
        row = manifest.get(f"row{number}")
        if not isinstance(row, dict) or row.get("status") != expected_status or row.get("row_complete") is not False:
            raise FinalizationError(f"Row{number} is not fail-closed with the expected status")
    row139 = manifest["row139"]
    if row139.get("ambience_continuity_gate_pass") is not True or row139.get("mix_balance_gate_pass") is not True:
        raise FinalizationError("Row139 bounded automated mix gates did not pass")
    row141 = manifest["row141"]
    if row141.get("spatial_room_evaluator_executed") is not True or row141.get("mandatory_ensemble_complete") is not False:
        raise FinalizationError("Row141 evaluator or ensemble boundary is invalid")
    row143 = manifest["row143"]
    if row143.get("request_schema_valid") is not True:
        raise FinalizationError("Row143 review request is not schema-valid")
    if row143.get("human_review_record_present") is not False or row143.get("human_playback_proof_present") is not False:
        raise FinalizationError("Row143 improperly claims human review authority")

    gates = report.get("gates")
    if not isinstance(gates, dict) or report.get("overall_pass") is not False or report.get("is_synthetic") is not True:
        raise FinalizationError("strict evaluator did not preserve the synthetic fail-closed result")
    required_pass = ("ambience_continuity", "mix_balance_review", "spatial_position_check")
    if any(gates.get(name, {}).get("status") != "PASS" for name in required_pass):
        raise FinalizationError("a required bounded spatial/mix gate did not pass")
    if gates.get("room_reverb_check", {}).get("status") != "FAIL":
        raise FinalizationError("room conformance failure is not preserved")
    required_blocked = (
        "spatial_audio_playback_review", "production_runtime_proof", "production_spatial_room_authority",
    )
    if any(gates.get(name, {}).get("status") != "BLOCKED" for name in required_blocked):
        raise FinalizationError("an unavailable playback/runtime/authority gate is not blocked")

    boundaries = manifest.get("boundaries")
    if not isinstance(boundaries, dict) or boundaries.get("is_synthetic") is not True:
        raise FinalizationError("synthetic diagnostic boundary is missing")
    required_false = (
        "automated_metrics_are_human_review", "human_review_fabricated", "production_runtime_proof_present",
        "production_authority_present", "production_ready", "content_based_suppression", "aws_or_ec2_used",
        "mask_or_wave71_touched",
    )
    if any(boundaries.get(name) is not False for name in required_false):
        raise FinalizationError("a packet boundary improperly claims authority or prohibited work")
    if request.get("schema_name") != "wave64_human_audio_review_request":
        raise FinalizationError("Row143 request schema identity is invalid")
    if request.get("review_id") != "W64-SPEECH-L01-SPATIAL-MIX-HUMAN-REVIEW-001":
        raise FinalizationError("Row143 review request identity is invalid")


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
                f"Hash-bound Rows139/141/143 packet evidence is recorded in {evidence}. "
                "Sample-accurate mix gates pass; room conformance fails; automated metrics and a review request "
                "are not human playback or production authority. content_based_suppression=false."
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
    manifest_path = runtime_dir / RUNTIME_FILES[-1]
    report_path = runtime_dir / "row141_spatial_room_evaluator_report.json"
    request_path = runtime_dir / "row143_human_playback_review_request.json"
    manifest = load_object(manifest_path)
    report = load_object(report_path)
    request = load_object(request_path)
    validate_packet(manifest, report, request)
    require_bound_file(manifest["row141"]["strict_evaluator_report"], report_path, "Row141 report")
    require_bound_file(manifest["row143"]["human_review_request"], request_path, "Row143 request")
    require_bound_file(request["artifact_binding"], runtime_dir / "final_mix_pcm24_stereo_16k.wav", "Row143 audio")

    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(runtime_dir / name, durable_dir / name) for name in RUNTIME_FILES}
    runtime = {name: binding(runtime_dir / name) for name in RUNTIME_FILES}
    implementation_paths = {
        "packet_builder": "Plan/07_IMPLEMENTATION/scripts/build_wave64_speech_mix_evaluator_review_packet.py",
        "spatial_room_producer": "Plan/07_IMPLEMENTATION/scripts/produce_wave64_spatial_room_evidence_bundle.py",
        "spatial_room_evaluator": "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_spatial_room_evidence.py",
        "human_review_request_producer": "Plan/07_IMPLEMENTATION/scripts/prepare_wave64_human_audio_review.py",
        "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows139_141_143.py",
        "packet_builder_tests": "Plan/Instructions/QA/Scripts/test_build_wave64_speech_mix_evaluator_review_packet.py",
        "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows139_141_143.py",
    }
    implementation = {name: binding(root / relative) for name, relative in implementation_paths.items()}
    implemented = {
        "139": "sample-accurate PCM24 stereo dry, spatial, ambience, and exact sample-sum mix stems with continuity and balance QA",
        "141": "strict spatial-room evaluator execution with exact automated pass, acoustic failure, and authority-blocker preservation",
        "143": "schema-valid hash-bound human playback review request with no fabricated review record or proof",
    }
    row_gates = {
        "139": {name: report["gates"][name] for name in ("ambience_continuity", "mix_balance_review")},
        "141": {name: report["gates"][name] for name in (
            "spatial_position_check", "room_reverb_check", "spatial_audio_playback_review",
            "production_runtime_proof", "production_spatial_room_authority", "overall_pass",
        )},
        "143": {
            "request_schema_valid": True,
            "human_review_record_present": False,
            "human_playback_proof_present": False,
        },
    }
    common = {
        "schema_version": "1.0",
        "execution_timestamp": manifest["created_at"],
        "runtime_classification": manifest["classification"],
        "durable_artifacts": durable,
        "runtime_artifacts": runtime,
        "implementation": implementation,
        "packet_manifest": manifest,
        "strict_evaluator_report": report,
        "human_playback_review_request": request,
        "boundaries": {
            **manifest["boundaries"],
            "source_media_mutated": False,
            "derived_mix_media_created": True,
            "review_request_is_review_record": False,
            "production_promotion_claimed": False,
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
                "automated_gates": row_gates[number],
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
        "classification": "WAVE64_SPEECH_ROWS139_141_143_RUNTIME_RECONCILED_BLOCKED_CERTIFICATION",
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
        print(json.dumps({"classification": "WAVE64_SPEECH_ROWS139_141_143_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
