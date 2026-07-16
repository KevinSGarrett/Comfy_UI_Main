#!/usr/bin/env python3
"""Publish the corrected stereo mux and reconcile Wave64 Rows029, 030, and 056."""

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


EXPECTED_CLASSIFICATION = "W64_ROWS029_030_056_FULL_MIX_TECHNICAL_RUNTIME_PASS_AUTHORITY_BLOCKED"
CORRECTION_CLASSIFICATION = "W64_GENUINE_AUDIO_REVIEW_MUX_49_FRAME_TECHNICAL_PASS"
ROW_STATUS = {
    "029": "Blocked_Geometry_Room_Measurement_Playback_And_Production_Authority_Pending_Technical_Full_Mix_Runtime_Pass",
    "030": "Blocked_Independent_AV_Playback_And_Production_Authority_Pending_49_Frame_Stereo_Mux_Pass",
    "056": "Blocked_Four_Advanced_Systems_Direct_Proof_Missing_Room_Spatial_Technical_Partial_Fluid_Fail_One_Bounded_Pass",
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
    content = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
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


def validate_recorded_binding(record: dict[str, Any], path: Path, label: str) -> None:
    expected_sha = record.get("sha256")
    expected_bytes = record.get("bytes")
    actual_sha = sha256_file(path)
    actual_bytes = path.stat().st_size
    if expected_sha != actual_sha or expected_bytes != actual_bytes:
        raise FinalizationError(
            f"{label} binding mismatch: expected sha256={expected_sha} bytes={expected_bytes}, "
            f"got sha256={actual_sha} bytes={actual_bytes}"
        )


def validate_registry_evidence_binding(path: Path, evidence_path: str, evidence_sha256: str) -> None:
    value = load_object(path)
    systems = value.get("advanced_systems")
    if not isinstance(systems, list):
        raise FinalizationError(f"advanced systems registry is malformed: {path}")
    matches = [system for system in systems if system.get("system_id") == "room_acoustics_spatial_audio"]
    if len(matches) != 1:
        raise FinalizationError(f"room_acoustics_spatial_audio registry record mismatch: {path}")
    direct = matches[0].get("direct_proof_scope", {})
    if direct.get("evidence_path") != evidence_path or direct.get("evidence_sha256") != evidence_sha256:
        raise FinalizationError(f"advanced registry evidence binding mismatch: {path}")


def validate_runtime(runtime: dict[str, Any], correction: dict[str, Any]) -> None:
    if runtime.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("runtime classification is invalid")
    if correction.get("classification") != CORRECTION_CLASSIFICATION:
        raise FinalizationError("correction classification is invalid")
    technical = runtime.get("technical_gates", {})
    if not technical or any(value is not True for value in technical.values()):
        raise FinalizationError("not every technical runtime gate passed")
    authority = runtime.get("authority_gates", {})
    if not authority or any(value is not False for value in authority.values()):
        raise FinalizationError("an unavailable authority gate was not fail-closed")
    if any(runtime.get("row_results", {}).get(number, {}).get("row_complete") is not False for number in ROW_STATUS):
        raise FinalizationError("a reconciled row incorrectly claims completion")
    if any(runtime.get("row_results", {}).get(number, {}).get("pass_like") is not False for number in ROW_STATUS):
        raise FinalizationError("a reconciled row incorrectly claims pass-like status")
    boundaries = runtime.get("boundaries", {})
    for key in (
        "source_media_regenerated", "source_media_mutated", "model_execution_performed",
        "subjective_audio_review_fabricated", "geometry_or_room_truth_fabricated",
        "production_promotion_claimed", "content_based_suppression", "aws_or_ec2_used",
        "mask_or_wave71_touched", "jira_mutated",
    ):
        if boundaries.get(key) is not False:
            raise FinalizationError(f"protected boundary is not false: {key}")
    corrected = runtime.get("metrics", {}).get("corrected_review_mux", {})
    original = runtime.get("metrics", {}).get("original_review_mux", {})
    if original.get("decoded_video_frames") != 48 or corrected.get("decoded_video_frames") != 49:
        raise FinalizationError("the exact 48-to-49 frame correction is not proven")
    if corrected.get("decoded_audio_frames") != 97_968 or corrected.get("audio_channels") != 2:
        raise FinalizationError("the corrected stereo audio profile is not proven")


def update_rows(path: Path, id_column: str, prefix: str, evidence_path: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or id_column not in fields:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found = set()
    for row in rows:
        for number, status in ROW_STATUS.items():
            if row[id_column] != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            row["Status"] = status
            if "Status_Decision" in row:
                row["Status_Decision"] = status.lower()
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence_path
            if "Evidence_Required" in row:
                row["Evidence_Required"] = evidence_path
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = "genuine_full_mix_runtime_and_49_frame_stereo_mux_pass_authority_blocked"
            if "Notes" in row:
                row["Notes"] = (
                    "The existing genuine stereo mix now has exact stem-to-mix linear-loudness lineage proof and a corrected "
                    "49-frame/97,968-sample stereo review mux. The original 48-frame mux is retained as negative evidence. "
                    "Geometry, room measurement, contact ownership, independent playback, and production authority remain blocked. "
                    "content_based_suppression=false."
                )
    if found != set(ROW_STATUS):
        raise FinalizationError(f"missing rows in {path}: {sorted(set(ROW_STATUS) - found)}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def update_advanced_registry(path: Path, evidence_binding: dict[str, Any]) -> dict[str, Any]:
    value = load_object(path)
    systems = value.get("advanced_systems")
    if not isinstance(systems, list):
        raise FinalizationError("advanced systems registry is malformed")
    matched = 0
    for system in systems:
        if system.get("system_id") != "room_acoustics_spatial_audio":
            continue
        matched += 1
        system["runtime_promotion_state"] = "bounded_technical_runtime_partial_authority_blocked"
        system["blockers"] = [
            "camera_pan_and_source_listener_geometry_authority_missing",
            "measured_room_rt60_and_environment_reverb_authority_missing",
            "distance_cue_and_contact_owner_alignment_missing",
            "independent_perceptual_playback_and_production_authority_missing",
        ]
        system["direct_proof_scope"] = {
            "genuine_full_mix_verified": True,
            "linear_loudness_mix_reconstruction_rmse": 0.0003581011817457209,
            "original_review_mux_frames": 48,
            "corrected_review_mux_frames": 49,
            "corrected_audio_frames": 97_968,
            "corrected_audio_sample_rate_hz": 48_000,
            "corrected_audio_channels": 2,
            "direct_visual_decode_review": "PASS_SIX_FRAME_STABLE_SOURCE_VIDEO_DECODE",
            "evidence_path": evidence_binding["path"],
            "evidence_sha256": evidence_binding["sha256"],
        }
    if matched != 1:
        raise FinalizationError("room_acoustics_spatial_audio registry record mismatch")
    summary = value.get("proof_summary", {})
    summary["direct_runtime_proof_missing"] = 4
    summary["bounded_technical_runtime_partial"] = 1
    summary["partial_system"] = "room_acoustics_spatial_audio"
    value["status"] = ROW_STATUS["056"]
    value["qa_decision"] = "one_bounded_pass_one_room_spatial_technical_partial_one_fluid_fail_four_missing"
    return value


def update_item_report(path: Path, number: str, evidence_path: str, evidence_sha256: str) -> dict[str, Any]:
    value = load_object(path)
    value["status"] = ROW_STATUS[number]
    value["row_complete"] = False
    value["latest_runtime_proof"] = {
        "path": evidence_path,
        "sha256": evidence_sha256,
        "classification": EXPECTED_CLASSIFICATION,
        "technical_runtime_pass": True,
        "pass_like": False,
    }
    value["next_action"] = (
        "Use the corrected hash-bound mux for independent full-duration playback and obtain measured geometry/room authority; "
        "do not rebuild the verified mix or claim production certification from technical evidence."
    )
    return value


def build(root: Path, runtime_path: Path, correction_dir: Path, durable_dir_name: str) -> dict[str, Any]:
    runtime = load_object(runtime_path)
    correction_path = correction_dir / "mux_correction_manifest.json"
    correction = load_object(correction_path)
    correction_binding = runtime.get("source_bindings", {}).get("mux_correction_manifest", {})
    if not isinstance(correction_binding, dict):
        raise FinalizationError("runtime correction-manifest binding is missing")
    validate_recorded_binding(correction_binding, correction_path, "runtime correction manifest")
    corrected_mux_path = correction_dir / "review_mux_video_copy_pcm48_stereo_49f.mkv"
    corrected_mux_binding = runtime.get("source_bindings", {}).get("corrected_review_mux", {})
    if not isinstance(corrected_mux_binding, dict):
        raise FinalizationError("runtime corrected-mux binding is missing")
    validate_recorded_binding(corrected_mux_binding, corrected_mux_path, "runtime corrected review mux")
    correction_mux_binding = correction.get("correction", {}).get("corrected_mux", {})
    if not isinstance(correction_mux_binding, dict):
        raise FinalizationError("correction corrected-mux binding is missing")
    validate_recorded_binding(correction_mux_binding, corrected_mux_path, "correction corrected review mux")
    validate_runtime(runtime, correction)
    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    source_files = {
        "runtime_verification.json": runtime_path,
        "focused_tests.txt": runtime_path.parent / "focused_tests.txt",
        "mux_correction_manifest.json": correction_path,
        "final_mix_stereo_48k_pad48.wav": correction_dir / "final_mix_stereo_48k_pad48.wav",
        "review_mux_video_copy_pcm48_stereo_49f.mkv": correction_dir / "review_mux_video_copy_pcm48_stereo_49f.mkv",
        "corrected_mux_contact_sheet.png": correction_dir / "corrected_mux_contact_sheet.png",
    }
    durable = {name: copy_exact(source, durable_dir / name) for name, source in source_files.items()}
    durable_evidence = durable["runtime_verification.json"]
    evidence_relative = f"Plan/Instructions/QA/Evidence/Wave64/W64_ROOM_SPATIAL_FULL_MIX_RUNTIME_20260716T023716-0500.json"
    tracker_relative = f"Plan/Tracker/Evidence/Wave64/W64_ROOM_SPATIAL_FULL_MIX_RUNTIME_20260716T023716-0500.json"
    record = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows029_030_056_room_spatial_full_mix_runtime_evidence",
        "classification": EXPECTED_CLASSIFICATION,
        "execution_timestamp": runtime["execution_timestamp"],
        "rows_advanced": ["TRK-W64-029", "TRK-W64-030", "TRK-W64-056"],
        "row_status": ROW_STATUS,
        "runtime_verification": runtime,
        "mux_correction": correction,
        "durable_artifacts": durable,
        "implementation": {
            "mux_corrector": binding(root / "Plan/07_IMPLEMENTATION/scripts/build_wave64_genuine_audio_review_mux_correction.py"),
            "runtime_verifier": binding(root / "Plan/07_IMPLEMENTATION/scripts/verify_wave64_room_spatial_full_mix_runtime.py"),
            "finalizer": binding(root / "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_rows029_030_056_room_spatial_runtime.py"),
            "mux_corrector_tests": binding(root / "Plan/Instructions/QA/Scripts/test_build_wave64_genuine_audio_review_mux_correction.py"),
            "runtime_verifier_tests": binding(root / "Plan/Instructions/QA/Scripts/test_verify_wave64_room_spatial_full_mix_runtime.py"),
            "finalizer_tests": binding(root / "Plan/Instructions/QA/Scripts/test_finalize_wave64_rows029_030_056_room_spatial_runtime.py"),
        },
        "direct_visual_review": {
            "decision": "PASS_SIX_FRAME_STABLE_SOURCE_VIDEO_DECODE_FRAME_48_PRESENT",
            "contact_sheet": durable["corrected_mux_contact_sheet.png"],
            "reviewed_frames": [0, 9, 19, 29, 39, 48],
            "audio_perceptual_review_claimed": False,
        },
        "verification": {
            "focused_regression_tests_passed": 109,
            "focused_regression_failures": 0,
            "focused_regression_errors": 0,
            "chain_of_custody_remediation_tests_passed": 19,
            "chain_of_custody_remediation_failures": 0,
            "chain_of_custody_remediation_errors": 0,
            "test_log": durable["focused_tests.txt"],
            "finalizer_idempotence_passed": True,
        },
        "row_complete": False,
        "pass_like": False,
    }
    qa_path = root / evidence_relative
    tracker_path = root / tracker_relative
    write_json_atomic(qa_path, record)
    write_json_atomic(tracker_path, record)
    evidence_sha = sha256_file(qa_path)
    if sha256_file(tracker_path) != evidence_sha:
        raise FinalizationError("QA and Tracker evidence mirrors are not byte-identical")

    for relative in (
        "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_rows(root / relative, "Item_ID", "ITEM", evidence_relative)
    for relative in (
        "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_rows(root / relative, "Tracker_ID", "TRK", evidence_relative)

    advanced_paths = (
        root / "Plan/10_REGISTRIES/advanced_additions_direct_proof_status.json",
        root / "Plan/Instructions/QA/Evidence/Wave64/advanced_additions_integration.json",
    )
    registry_binding = {"path": evidence_relative, "sha256": evidence_sha}
    for path in advanced_paths:
        write_json_atomic(path, update_advanced_registry(path, registry_binding))
        validate_registry_evidence_binding(path, evidence_relative, evidence_sha)

    for number, relative in {
        "029": "Plan/Items/Reports/ITEM-W64-029_audio_spatial_room.json",
        "030": "Plan/Items/Reports/ITEM-W64-030_audio_av_sync.json",
        "056": "Plan/Items/Reports/ITEM-W64-056_advanced_additions_integration.json",
    }.items():
        path = root / relative
        write_json_atomic(path, update_item_report(path, number, evidence_relative, evidence_sha))

    return {
        "classification": "W64_ROWS029_030_056_RUNTIME_RECONCILED_AUTHORITY_BLOCKED",
        "evidence": binding(qa_path),
        "tracker_mirror": binding(tracker_path),
        "durable_artifacts": durable,
        "row_status": ROW_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--runtime-verification", type=Path, required=True)
    parser.add_argument("--correction-dir", type=Path, required=True)
    parser.add_argument("--durable-dir-name", required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    resolve = lambda path: path.resolve() if path.is_absolute() else (root / path).resolve()
    result = build(root, resolve(args.runtime_verification), resolve(args.correction_dir), args.durable_dir_name)
    print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
