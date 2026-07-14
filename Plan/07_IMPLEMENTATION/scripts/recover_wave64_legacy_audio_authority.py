#!/usr/bin/env python3
"""Recover existing legacy Row025 audio evidence without regenerating media."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
LEGACY_ROOT = Path(r"C:\Comfy_UI")
STAMP = "20260714T063840-0500"
TIMESTAMP = "2026-07-14T06:38:40-05:00"
STATUS = "Blocked_Audio_Production_Runtime_Proof_Missing"
INSTANCE_ID = "i-0560bf8d143f93bb1"
RECOVERY_ROOT = (
    PLAN
    / "Instructions/Operations/Pulled_Back_Artifacts"
    / f"wave42_legacy_audio_recovery_{STAMP}"
)
EVIDENCE_PATH = PLAN / f"Instructions/QA/Evidence/Wave64/AUDIO_PIPELINE_LEGACY_RECOVERY_{STAMP}.json"
TRACKER_EVIDENCE_PATH = PLAN / f"Tracker/Evidence/AUDIO_PIPELINE_LEGACY_RECOVERY_{STAMP}.json"
NOTE = (
    "Wave64 Row025 legacy recovery 2026-07-14: hash-verified existing C:\\Comfy_UI diagnostic "
    "SAPI/procedural audio and the original returned-EC2 AV packet were imported without "
    "regeneration. AV timing was provisionally accepted, but autonomous multimodal QA rejected "
    "final release; production runtime, playback-quality, loudness, and certification gates remain blocked."
)


@dataclass(frozen=True)
class ArtifactSpec:
    source: Path
    destination_group: str
    expected_sha256: str | None = None
    expected_bytes: int | None = None
    wav: tuple[int, int, int, int] | None = None
    classification: str = "authority_context"


SAPI_ROOT = LEGACY_ROOT / "Generated_Outputs/audio_candidates/release_scene_03/20260702_034909"
PROCEDURAL_ROOT = LEGACY_ROOT / "Generated_Outputs/audio_candidates/release_scene_03/20260702_034918"
RETURNED_ROOT = (
    LEGACY_ROOT
    / "Implementation/evidence/ec2_returned_runtime/20260701_101322_final_runtime"
    / "remote_artifacts/Implementation/final_media_inbox/release_scene_03"
)


def wav_spec(source: Path, group: str, sha256: str, size: int, rate: int, frames: int,
             classification: str) -> ArtifactSpec:
    return ArtifactSpec(source, group, sha256, size, (rate, 1, 2, frames), classification)


ARTIFACTS = (
    wav_spec(SAPI_ROOT / "L001_C01_sapi_dialogue.wav", "sapi_diagnostic",
             "2c4188a284f1b19df16ddad759ddb96a2f9ca96f232f71d5097701136f477ed6",
             137374, 22050, 68664, "diagnostic_sapi_line"),
    wav_spec(SAPI_ROOT / "L002_C02_sapi_dialogue.wav", "sapi_diagnostic",
             "583a7ac689846b32634c6813cceeb86391009067a82cf303c77d9d814cc5044e",
             143110, 22050, 71532, "diagnostic_sapi_line"),
    wav_spec(SAPI_ROOT / "wave42_release_scene_03_sapi_dialogue_candidate.wav", "sapi_diagnostic",
             "280d14fa93dca03e3ed393139d5826de30cee16cbc8fa547ae628fe96ae66cd7",
             363608, 22050, 181782, "diagnostic_sapi_mix"),
    ArtifactSpec(SAPI_ROOT / "L001_text.txt", "sapi_diagnostic", classification="diagnostic_source_text"),
    ArtifactSpec(SAPI_ROOT / "L002_text.txt", "sapi_diagnostic", classification="diagnostic_source_text"),
    ArtifactSpec(SAPI_ROOT / "render_sapi_line.ps1", "sapi_diagnostic", classification="diagnostic_renderer"),
    ArtifactSpec(
        LEGACY_ROOT / "Implementation/manifests/local_sapi_audio_candidate/local_sapi_audio_candidate_20260702_034909.json",
        "sapi_diagnostic", classification="diagnostic_manifest"),
    wav_spec(PROCEDURAL_ROOT / "wave42_release_scene_03_dialogue_stem.wav", "procedural_mix_diagnostic",
             "61f5b11f8ef6cc30f4ed21a49baf76d7db7575eafc7e7cc1ae203f7ef0f17fc2",
             441044, 22050, 220500, "diagnostic_procedural_stem"),
    wav_spec(PROCEDURAL_ROOT / "wave42_release_scene_03_sfx_foley_stem.wav", "procedural_mix_diagnostic",
             "5e98e62b21dce499275bc185cda01bc237446114073386dd045f79f13e65a4c1",
             441044, 22050, 220500, "diagnostic_procedural_stem"),
    wav_spec(PROCEDURAL_ROOT / "wave42_release_scene_03_ambience_stem.wav", "procedural_mix_diagnostic",
             "7cae8926bd2863915e6cbd0df98826367dde1b10f0d42c0e08662197ab17ddaf",
             441044, 22050, 220500, "diagnostic_procedural_stem"),
    wav_spec(PROCEDURAL_ROOT / "wave42_release_scene_03_music_stem.wav", "procedural_mix_diagnostic",
             "d32d6b26015b7e07b325b34335c078aabed2a682f11cdc2c06450cc660d9d24b",
             441044, 22050, 220500, "diagnostic_procedural_stem"),
    wav_spec(PROCEDURAL_ROOT / "wave42_release_scene_03_procedural_audio_mix_candidate.wav",
             "procedural_mix_diagnostic",
             "cbe1bb2d357193fd56212a6b520be300e326d267d6b06d3922307543ca0fa0dd",
             441044, 22050, 220500, "diagnostic_procedural_mix"),
    ArtifactSpec(
        LEGACY_ROOT / "Implementation/manifests/local_procedural_audio_mix_candidate/local_procedural_audio_mix_candidate_20260702_034918.json",
        "procedural_mix_diagnostic", classification="diagnostic_manifest"),
    wav_spec(RETURNED_ROOT / "dialogue_procedural_provisional.wav", "returned_ec2_20260701T101322",
             "c5f604eadbd5e153b017ae2af4c979ad658c648d99e07b254b43aacd3c1c182c",
             960044, 48000, 480000, "returned_runtime_provisional_audio"),
    wav_spec(RETURNED_ROOT / "sfx_foley_original_generated.wav", "returned_ec2_20260701T101322",
             "a9e14beacd8ef15fc983af60f8fd266cf38f21434285907ff22ae59e37a51312",
             960044, 48000, 480000, "returned_runtime_diagnostic_audio"),
    wav_spec(RETURNED_ROOT / "music_original_generated_bed.wav", "returned_ec2_20260701T101322",
             "df743754556612f09f57fdce9b47716fd743a287a6a85320782b9da8a9548f66",
             960044, 48000, 480000, "returned_runtime_diagnostic_audio"),
    wav_spec(RETURNED_ROOT / "final_audio_mix_provisional.wav", "returned_ec2_20260701T101322",
             "65ded4d70ec8b68cc04672df16edb411f593ec8c527c3bd2987d5e0e44deaadb",
             960044, 48000, 480000, "returned_runtime_provisional_mix"),
    ArtifactSpec(RETURNED_ROOT / "release_scene_03_final_video_candidate.mp4", "returned_ec2_20260701T101322",
                 "65a69b8f16a92e0a119f68698b45537076c58da647113d37cb78e8bb352e4718",
                 812208, classification="returned_runtime_provisional_av"),
    ArtifactSpec(RETURNED_ROOT / "KF_INIT.png", "returned_ec2_20260701T101322",
                 "9d526b45a660c80d584e153e5a7431ea7ef4c1bc83b94e08b652208e572cb71c",
                 1114334, classification="returned_runtime_keyframe"),
    ArtifactSpec(RETURNED_ROOT / "KF_MID.png", "returned_ec2_20260701T101322",
                 "4d2e1237bd318161786eb1d2d4c73e91479dcfd1d2ddaadf038058d745a70982",
                 1022207, classification="returned_runtime_keyframe"),
    ArtifactSpec(RETURNED_ROOT / "KF_END.png", "returned_ec2_20260701T101322",
                 "9b5e02983bdd8a82706854d642e2181edb58fb150b1fbae4772e3d53db6ff072",
                 1079610, classification="returned_runtime_keyframe"),
    ArtifactSpec(RETURNED_ROOT / "final_ec2_returned_media_manifest.json", "returned_ec2_20260701T101322",
                 classification="returned_runtime_manifest"),
    ArtifactSpec(RETURNED_ROOT / "av_sync_validation_report.json", "returned_ec2_20260701T101322",
                 "b59618d65b89d07513214063272a6775519a1be33a1c70bf8c12ab04c1824b47",
                 1071, classification="provisional_av_sync_review"),
    ArtifactSpec(RETURNED_ROOT / "human_review_decision.json", "returned_ec2_20260701T101322",
                 "9a4af29ff72b888456d0fbf97a7383fe702ad099515bea754cb1fd9a29a60ff9",
                 1197, classification="final_release_rejection"),
    ArtifactSpec(RETURNED_ROOT / "WAVE42_PROVISIONAL_RELEASE_MANIFEST.json", "returned_ec2_20260701T101322",
                 "c52ab316899dbedb111b54755a48581ec6cbd96e9b6689e2a12af20f21870574",
                 17085, classification="rejected_provisional_release_manifest"),
    ArtifactSpec(RETURNED_ROOT / "rendered_media_drop_manifest.json", "returned_ec2_20260701T101322",
                 classification="returned_runtime_drop_manifest"),
    ArtifactSpec(LEGACY_ROOT / "Implementation/audio/audio_rights_policy.json", "authority",
                 classification="legacy_rights_authority_context"),
    ArtifactSpec(LEGACY_ROOT / "Implementation/audio/audio_output_metadata.release_scene_03.generated.json",
                 "authority", classification="legacy_audio_output_metadata"),
    ArtifactSpec(LEGACY_ROOT / "Implementation/audio/tts_model_adapter_registry.json", "authority",
                 classification="legacy_tts_adapter_registry"),
    ArtifactSpec(
        LEGACY_ROOT / "Implementation/manifests/audio_generation_path_probe/audio_generation_path_probe_20260702_034932.json",
        "authority", classification="legacy_generation_path_probe"),
)


CONTAINER_BOXES = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf", b"udta"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def project_path_or_absolute(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def wav_metadata(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        frames = handle.getnframes()
        return {
            "sample_rate_hz": rate,
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "frame_count": frames,
            "duration_seconds": round(frames / rate, 6),
            "compression_type": handle.getcomptype(),
        }


def iter_boxes(data: bytes, start: int = 0, end: int | None = None):
    limit = len(data) if end is None else min(end, len(data))
    offset = start
    while offset + 8 <= limit:
        size = struct.unpack_from(">I", data, offset)[0]
        box_type = data[offset + 4:offset + 8]
        payload_start = offset + 8
        if size == 1:
            if offset + 16 > limit:
                return
            size = struct.unpack_from(">Q", data, offset + 8)[0]
            payload_start = offset + 16
        elif size == 0:
            size = limit - offset
        if size < payload_start - offset or offset + size > limit:
            return
        yield offset, offset + size, payload_start, box_type
        offset += size


def mp4_handler_types(path: Path) -> set[str]:
    data = path.read_bytes()
    handlers: set[str] = set()

    def walk(start: int, end: int) -> None:
        for _, box_end, payload_start, box_type in iter_boxes(data, start, end):
            if box_type == b"hdlr" and payload_start + 12 <= box_end:
                handlers.add(data[payload_start + 8:payload_start + 12].decode("ascii", errors="replace"))
            elif box_type in CONTAINER_BOXES:
                walk(payload_start, box_end)

    walk(0, len(data))
    return handlers


def verify_spec(spec: ArtifactSpec) -> dict[str, Any]:
    if not spec.source.is_file():
        raise FileNotFoundError(spec.source)
    actual_hash = digest(spec.source)
    actual_bytes = spec.source.stat().st_size
    if spec.expected_sha256 and actual_hash != spec.expected_sha256:
        raise ValueError(f"SHA256 mismatch for {spec.source}: {actual_hash}")
    if spec.expected_bytes is not None and actual_bytes != spec.expected_bytes:
        raise ValueError(f"Byte-size mismatch for {spec.source}: {actual_bytes}")
    metadata = None
    if spec.wav:
        metadata = wav_metadata(spec.source)
        expected_rate, expected_channels, expected_width, expected_frames = spec.wav
        expected = (expected_rate, expected_channels, expected_width, expected_frames, "NONE")
        actual = (
            metadata["sample_rate_hz"], metadata["channels"], metadata["sample_width_bytes"],
            metadata["frame_count"], metadata["compression_type"],
        )
        if actual != expected:
            raise ValueError(f"WAV metadata mismatch for {spec.source}: {actual} != {expected}")
    return {"sha256": actual_hash, "bytes": actual_bytes, "wav_metadata": metadata}


def copy_verified(spec: ArtifactSpec, destination_root: Path) -> dict[str, Any]:
    verified = verify_spec(spec)
    destination = destination_root / spec.destination_group / spec.source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination) != verified["sha256"]:
            raise FileExistsError(f"Destination exists with different content: {destination}")
    else:
        shutil.copy2(spec.source, destination)
    if digest(destination) != verified["sha256"] or destination.stat().st_size != verified["bytes"]:
        raise IOError(f"Copied artifact verification failed: {destination}")
    return {
        "classification": spec.classification,
        "source_path": str(spec.source),
        "destination_path": project_path_or_absolute(destination),
        **verified,
        "copied_not_generated": True,
    }


def private_use_authority_present(rights: dict[str, Any]) -> bool:
    return (
        rights.get("default_status") == "private_personal_use_pre_authorized"
        and any("private personal-use project" in str(rule).lower() for rule in rights.get("rules", []))
    )


def validate_semantics() -> dict[str, bool]:
    sapi = load(LEGACY_ROOT / "Implementation/manifests/local_sapi_audio_candidate/local_sapi_audio_candidate_20260702_034909.json")
    procedural = load(LEGACY_ROOT / "Implementation/manifests/local_procedural_audio_mix_candidate/local_procedural_audio_mix_candidate_20260702_034918.json")
    returned = load(RETURNED_ROOT / "final_ec2_returned_media_manifest.json")
    av_sync = load(RETURNED_ROOT / "av_sync_validation_report.json")
    review = load(RETURNED_ROOT / "human_review_decision.json")
    provisional = load(RETURNED_ROOT / "WAVE42_PROVISIONAL_RELEASE_MANIFEST.json")
    rights = load(LEGACY_ROOT / "Implementation/audio/audio_rights_policy.json")
    checks = {
        "sapi_diagnostic_not_production": sapi.get("production_grade") is False and sapi.get("completion_claim_allowed") is False,
        "sapi_qa_failed": sapi.get("qa", {}).get("pass") is False,
        "procedural_diagnostic_not_production": procedural.get("production_grade") is False and procedural.get("completion_claim_allowed") is False,
        "procedural_qa_failed": procedural.get("qa", {}).get("pass") is False,
        "returned_from_approved_instance": returned.get("generated_on_ec2_instance_id") == INSTANCE_ID,
        "returned_media_ready_for_review": returned.get("rendered_media_ready_for_review") is True,
        "returned_completion_unclaimed": returned.get("completion_claim") is False and returned.get("final_release_package_created") is False,
        "av_sync_provisional_pass_present": av_sync.get("overall_status") == "pass" and any(item.get("status") == "provisional_pass" for item in av_sync.get("checks", [])),
        "final_release_rejected": review.get("decision") == "autonomous_qa_rejected_for_final_release" and review.get("human_review_accepted") is False,
        "provisional_manifest_rejected": provisional.get("status") == "provisional_machine_package_autonomous_qa_rejected" and provisional.get("completion_claim") is False,
        "private_use_authority_context_present": private_use_authority_present(rights),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Legacy semantic authority checks failed: {failed}")
    return checks


def update_csv(path: Path, id_field: str, row_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matches = [row for row in rows if row.get(id_field) == row_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one {row_id} row in {path}, found {len(matches)}")
    row = matches[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row025 Legacy Audio Authority Recovery"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-025` / `ITEM-W64-025` remains `{STATUS}`, but its earlier inventory conclusion is corrected. Existing diagnostic SAPI dialogue, procedural stems/mix, and the original returned-EC2 audio/video packet were hash-verified in `C:\\Comfy_UI` and copied into the authoritative project without regeneration. The returned packet proves runtime provenance and a provisional AV-sync pass; its autonomous multimodal review explicitly rejected final release, and all audio remains diagnostic or provisional.

Production audio-engine quality/provenance, strict playback acceptance, BS.1770/true-peak authority, final certification, masks, Wave71+, and Jira remain unclaimed. EC2 stayed stopped and AWS was not contacted during this recovery.

Next action: feed the recovered packet through the existing strict Row025/027/028/030 evaluators so missing-input gates become exact quality/authority failures without recreating media.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def append_proof_log(path: Path, evidence_path: str) -> None:
    marker = "row025_legacy_audio_authority_recovered_without_regeneration"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    row = (
        f"{TIMESTAMP},64,TRK-W64-025,Recovered hash-verified legacy diagnostic audio and returned-EC2 AV authority without regeneration,"
        f"{evidence_path},{len(ARTIFACTS)} artifacts copied; provisional AV sync preserved; final release rejection preserved,"
        f"blocked,{evidence_path},Run recovered packet through strict existing audio evaluators; {marker}\n"
    )
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(row)


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/audio_pipeline_build.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/audio_pipeline_build.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-025_audio_pipeline_build.json"
    for path in (canonical_path, tracker_canonical_path, report_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if RECOVERY_ROOT.exists() or EVIDENCE_PATH.exists() or TRACKER_EVIDENCE_PATH.exists():
        raise FileExistsError("Recovery destination or evidence already exists")

    semantics = validate_semantics()
    staging = RECOVERY_ROOT.with_name(RECOVERY_ROOT.name + ".staging")
    if staging.exists():
        raise FileExistsError(staging)
    try:
        artifacts = [copy_verified(spec, staging) for spec in ARTIFACTS]
        handlers = sorted(mp4_handler_types(staging / "returned_ec2_20260701T101322/release_scene_03_final_video_candidate.mp4"))
        if handlers != ["soun", "vide"]:
            raise ValueError(f"Returned MP4 does not contain expected audio/video handlers: {handlers}")
        staging.rename(RECOVERY_ROOT)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    # Destination paths were computed under the staging name; replace them after the atomic rename.
    for artifact in artifacts:
        artifact["destination_path"] = artifact["destination_path"].replace(
            RECOVERY_ROOT.name + ".staging", RECOVERY_ROOT.name, 1)

    evidence_rel = rel(EVIDENCE_PATH)
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-PIPELINE-LEGACY-RECOVERY-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-025",
        "item_id": "ITEM-W64-025",
        "status_decision": STATUS,
        "correction": {
            "previous_inventory_scope": "current ComfyUI/input, current pulled-back artifacts, and approved current S3 prefixes",
            "missing_scope_now_reconciled": r"legacy C:\Comfy_UI audio candidates and preserved returned-EC2 packet",
            "previous_no_candidate_conclusion_superseded": True,
            "corrected_conclusion": "Existing diagnostic/provisional audio and a returned-runtime AV packet are present, but final autonomous QA rejected release and no production audio proof bundle passes.",
        },
        "recovery_root": rel(RECOVERY_ROOT),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "semantic_checks": semantics,
        "returned_mp4_handler_types": handlers,
        "authority_classification": {
            "sapi": "diagnostic_candidate_qa_failed",
            "procedural_mix": "diagnostic_candidate_qa_failed",
            "returned_ec2_packet": "runtime_provenance_present_provisional_av_sync_final_release_rejected",
            "rights_policy": "private_use_generation_authority_context_not_production_quality_acceptance",
        },
        "gate_results": {
            "recovered_diagnostic_audio_present": True,
            "returned_ec2_runtime_packet_present": True,
            "provisional_av_sync_review_present": True,
            "final_multimodal_review_present": True,
            "final_multimodal_review_passed": False,
            "genuine_audio_engine_runtime_proof": False,
            "genuine_audio_playback_review": False,
            "certification_loudness_authority": False,
            "final_audio_certification": False,
            "production_acceptance": False,
        },
        "boundaries": {
            "duplicate_work_recreated": False,
            "generation_executed": False,
            "source_files_modified": False,
            "ec2_started": False,
            "aws_contacted": False,
            "candidate_promoted": False,
            "completed_runtime_rerun": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_legacy_audio_recovered_but_provisional_and_final_release_rejected",
        "next_action": "Feed the recovered packet through the existing strict Row025/027/028/030 producers and evaluators without regenerating media.",
    }
    dump(EVIDENCE_PATH, evidence)
    dump(TRACKER_EVIDENCE_PATH, evidence)

    canonical = load(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    canonical["legacy_audio_recovery"] = {
        "evidence": evidence_rel,
        "recovery_root": rel(RECOVERY_ROOT),
        "artifact_count": len(artifacts),
        "recovered_diagnostic_candidate_present": True,
        "returned_ec2_runtime_packet_present": True,
        "provisional_av_sync_review_present": True,
        "final_multimodal_review_present": True,
        "final_multimodal_review_passed": False,
        "production_eligible": False,
    }
    canonical["acceptance_gates"].update({
        "recovered_diagnostic_audio_present": True,
        "returned_ec2_runtime_packet_present": True,
        "provisional_av_sync_review_present": True,
        "final_multimodal_review_present": True,
        "final_multimodal_review_passed": False,
        "genuine_audio_engine_runtime_proof": False,
        "genuine_audio_playback_review": False,
        "final_audio_certification": False,
    })
    canonical["runtime"].update({
        "recovered_runtime_packet_count": 1,
        "recovery_generation_executed": False,
        "recovery_aws_contacted": False,
        "recovery_ec2_started": False,
    })
    canonical["blockers"][0]["reason"] = (
        "Legacy diagnostic audio and the original returned-EC2 AV packet are now recovered and hash-verified, "
        "but SAPI/procedural candidates failed QA and the returned packet was rejected for final release; no "
        "approved production audio-engine proof bundle passes."
    )
    canonical["blockers"][1]["reason"] = (
        "A provisional automated AV-sync review exists, but the authoritative autonomous multimodal review "
        "rejected final release and does not prove production speaker identity, voice consistency, foley/action "
        "alignment, ambience/dialogue balance, clipping safety, or final mix quality."
    )
    canonical["result"] = evidence["result"]
    canonical["reconciliation_evidence"] = evidence_rel
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report = load(report_path)
    report["timestamp"] = TIMESTAMP
    report["validation"].update({
        "legacy_audio_recovery": "pass",
        "legacy_recovery_artifact_count": len(artifacts),
        "recovered_diagnostic_audio_present": True,
        "returned_ec2_runtime_packet_present": True,
        "provisional_av_sync_review_present": True,
        "final_multimodal_review": "present_rejected_for_final_release",
    })
    report["acceptance_gates"].update({
        "recovered_diagnostic_audio_present": True,
        "returned_ec2_runtime_packet_present": True,
        "provisional_av_sync_review_present": True,
        "final_multimodal_review_passed": False,
        "genuine_audio_engine_runtime": False,
        "genuine_audio_review_record": False,
        "final_audio_certification": False,
    })
    report["runtime"].update({
        "recovered_runtime_packet_count": 1,
        "recovery_generation_executed": False,
        "recovery_aws_contacted": False,
        "recovery_ec2_started": False,
    })
    report["blockers"] = canonical["blockers"]
    for record in report["evidence"]:
        if record.get("path") == rel(canonical_path):
            record["sha256"] = digest(canonical_path)
    report["evidence"].append({"path": evidence_rel, "sha256": digest(EVIDENCE_PATH)})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", "TRK-W64-025")
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-025")
    for name in (
        "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "NEXT_ACTION.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ):
        prepend_hydration(PLAN / "Instructions/Hydration_Rehydration" / name, evidence_rel)
    append_proof_log(PLAN / "Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv", evidence_rel)
    print(json.dumps({
        "status": STATUS,
        "artifacts_recovered": len(artifacts),
        "recovery_root": rel(RECOVERY_ROOT),
        "returned_mp4_handlers": handlers,
        "final_release_passed": False,
        "generation_executed": False,
        "next_action": evidence["next_action"],
    }, indent=2))


if __name__ == "__main__":
    main()
