#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any


RECOVERY_ROOT = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave42_legacy_audio_recovery_20260714T063840-0500"
)
PROCEDURAL_MANIFEST = RECOVERY_ROOT / (
    "procedural_mix_diagnostic/local_procedural_audio_mix_candidate_20260702_034918.json"
)
RETURNED_MANIFEST = RECOVERY_ROOT / (
    "returned_ec2_20260701T101322/final_ec2_returned_media_manifest.json"
)
AUTHORITY_REGISTRY = Path(
    "Plan/10_REGISTRIES/wave64_foley_force_alignment_authority_registry.json"
)
LEGACY_SOURCE_RECORDS = {
    "foley_event_manifest": (
        RECOVERY_ROOT / "legacy_event_sources/foley_event_manifest.json",
        "74fc935dadc7d86f5798fc23f1bee5b1ca363b0fb44811c59f7ffe7e252b4525",
    ),
    "sfx_cue_manifest": (
        RECOVERY_ROOT / "legacy_event_sources/sfx_cue_manifest.json",
        "0e9da1ec9c7d754502a562c83167961d81523d7613f37fb6c9bba93c9f38574f",
    ),
    "master_av_sync_timeline": (
        RECOVERY_ROOT / "legacy_event_sources/master_av_sync_timeline.json",
        "9e6a0cb9252658c800d813b3ab47dcbe4a70ee4e1d0c9f330ca971fa78ea3876",
    ),
    "provisional_final_media_assets": (
        RECOVERY_ROOT
        / "legacy_event_sources/provisional_final_media_assets_20260630_060942.json",
        "2746e8fcd712649f3d1334e872c78d35096e3a761cc7c344cb2f1b4dd1763747",
    ),
}
MISSING_REQUIRED_BINDINGS = (
    "visual_contact_manifest_binding",
    "wave22_force_event_manifest_binding",
    "wave30_audio_event_manifest_binding",
    "run_id",
    "shot_id",
    "take_id",
)
MISSING_PRODUCTION_BINDINGS = (
    "runtime_proof_binding",
    "av_review_proof_binding",
    "production_alignment_bundle_binding",
    "manual_body_contact_gold_mask_authority",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(root: Path, relative: Path) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {relative}") from exc
    return path


def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def wav_metadata(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        return {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "sample_rate": sample_rate,
            "frames": frames,
            "duration_seconds": round(frames / sample_rate, 6),
        }


def verify_wav(
    root: Path,
    path: Path,
    expected_sha256: str,
    expected_bytes: int,
    expected_duration: float,
    origin: str,
    role: str,
    authority_class: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"recovered WAV missing: {path}")
    actual_hash = sha256(path)
    if actual_hash != expected_sha256:
        raise ValueError(f"recovered WAV hash mismatch: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"recovered WAV byte-size mismatch: {path}")
    metadata = wav_metadata(path)
    if abs(metadata["duration_seconds"] - expected_duration) > 0.000001:
        raise ValueError(f"recovered WAV duration mismatch: {path}")
    return {
        "origin": origin,
        "role": role,
        "path": relative_path(root, path),
        "sha256": actual_hash,
        "bytes": actual_bytes,
        **metadata,
        "integrity_verified": True,
        "authority_class": authority_class,
        "production_eligible": False,
    }


def verify_legacy_sources(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    records: dict[str, Any] = {}
    payloads: dict[str, Any] = {}
    for name, (relative, expected_hash) in LEGACY_SOURCE_RECORDS.items():
        path = project_path(root, relative)
        if not path.is_file():
            raise ValueError(f"recovered legacy source missing: {relative}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"recovered legacy source hash mismatch: {relative}")
        payloads[name] = load_json(path)
        records[name] = {
            "path": relative_path(root, path),
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
            "source_bytes_preserved": True,
        }
    return records, payloads


def align_legacy_events(payloads: dict[str, Any]) -> list[dict[str, Any]]:
    foley_events = payloads["foley_event_manifest"].get("events", [])
    cues = payloads["sfx_cue_manifest"].get("cues", [])
    timeline_events = {
        event.get("id"): event
        for event in payloads["master_av_sync_timeline"].get("events", [])
    }
    if len(foley_events) != 2 or len(cues) != 2:
        raise ValueError("expected exactly two recovered Foley events and two SFX cues")

    aligned: list[dict[str, Any]] = []
    used_cues: set[str] = set()
    for foley in foley_events:
        candidates = [
            cue
            for cue in cues
            if cue.get("scene_id") == foley.get("scene_id")
            and cue.get("start_seconds", -1) >= foley.get("start_seconds", 0)
            and cue.get("end_seconds", float("inf")) <= foley.get("end_seconds", 0)
            and cue.get("cue_id") not in used_cues
        ]
        if len(candidates) != 1:
            raise ValueError(f"legacy Foley event has ambiguous SFX cue mapping: {foley}")
        cue = candidates[0]
        timeline = timeline_events.get(cue["cue_id"])
        if not timeline:
            raise ValueError(f"legacy SFX cue is missing from master timeline: {cue['cue_id']}")
        if timeline.get("entity_id") != foley.get("entity_id"):
            raise ValueError(f"legacy event owner mismatch: {cue['cue_id']}")
        used_cues.add(cue["cue_id"])
        aligned.append(
            {
                "foley_id": foley["foley_id"],
                "sfx_cue_id": cue["cue_id"],
                "entity_id": foley["entity_id"],
                "scene_id": foley["scene_id"],
                "foley_window_seconds": [
                    foley["start_seconds"],
                    foley["end_seconds"],
                ],
                "sfx_window_seconds": [cue["start_seconds"], cue["end_seconds"]],
                "timeline_window_seconds": [
                    timeline["start_seconds"],
                    timeline["end_seconds"],
                ],
                "legacy_timing_and_owner_consistent": True,
                "strict_visual_contact_or_force_authority_proven": False,
            }
        )
    return aligned


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    procedural_path = project_path(root, PROCEDURAL_MANIFEST)
    returned_path = project_path(root, RETURNED_MANIFEST)
    registry_path = project_path(root, AUTHORITY_REGISTRY)
    procedural = load_json(procedural_path)
    returned = load_json(returned_path)
    registry = load_json(registry_path)
    if registry.get("approved_alignment_bundles") != []:
        raise ValueError("alignment authority registry is no longer empty; reassess Row028")

    procedural_stem = next(
        (item for item in procedural.get("stems", []) if item.get("stem_id") == "sfx_foley_stem"),
        None,
    )
    returned_foley = next(
        (
            item
            for item in returned.get("required_artifacts", {}).get("audio", [])
            if item.get("role") == "sfx_foley_original_generated"
        ),
        None,
    )
    if not procedural_stem or not returned_foley:
        raise ValueError("required recovered Foley WAV record missing from source manifests")

    procedural_wav = procedural_path.parent / Path(procedural_stem["path"]).name
    returned_wav = returned_path.parent / returned_foley["path"]
    candidates = [
        verify_wav(
            root,
            procedural_wav,
            procedural_stem["sha256"],
            procedural_stem["bytes"],
            procedural_stem["duration_seconds"],
            "legacy_local_procedural_mix",
            "sfx_foley_stem",
            "diagnostic_full_mix_candidate",
        ),
        verify_wav(
            root,
            returned_wav,
            returned_foley["sha256"],
            returned_foley["size_bytes"],
            returned_foley["duration_seconds"],
            "legacy_returned_ec2_media",
            "sfx_foley_original_generated",
            "provisional_returned_runtime_audio",
        ),
    ]
    source_records, source_payloads = verify_legacy_sources(root)
    event_alignment = align_legacy_events(source_payloads)
    stamp = timestamp.replace("-", "").replace(":", "")

    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-FOLEY-RECOVERED-PACKET-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-028",
        "item_id": "ITEM-W64-028",
        "status_decision": "Blocked_Foley_Force_Production_Proof_Missing",
        "source_manifests": {
            "procedural_mix": {
                "path": relative_path(root, procedural_path),
                "sha256": sha256(procedural_path),
            },
            "returned_ec2_media": {
                "path": relative_path(root, returned_path),
                "sha256": sha256(returned_path),
            },
            "alignment_authority_registry": {
                "path": relative_path(root, registry_path),
                "sha256": sha256(registry_path),
                "approved_alignment_bundle_count": 0,
            },
        },
        "recovered_legacy_event_sources": source_records,
        "recovered_wav_candidates": candidates,
        "legacy_event_alignment": event_alignment,
        "strict_packet_readiness": {
            "scene_id": returned.get("scene_id"),
            "run_id": None,
            "shot_id": None,
            "take_id": None,
            "required_bindings_present": 0,
            "missing_required_bindings": list(MISSING_REQUIRED_BINDINGS),
            "missing_production_bindings": list(MISSING_PRODUCTION_BINDINGS),
            "legacy_foley_manifest_is_wave22_schema": False,
            "legacy_sfx_manifest_is_wave30_schema": False,
            "returned_av_sync_report_is_independent_wave64_av_review_proof": False,
            "packet_formable": False,
            "evaluator_invoked": False,
            "evaluator_skip_reason": (
                "Fail closed before request production: required visual-contact, Wave22, "
                "Wave30, run, shot, and take bindings are unavailable."
            ),
        },
        "boundaries": {
            "existing_audio_reused": True,
            "legacy_source_bytes_recovered_without_rewrite": True,
            "generation_executed": False,
            "audio_modified": False,
            "strict_manifest_or_identity_fields_invented": False,
            "visual_contact_claimed": False,
            "force_event_authority_claimed": False,
            "manual_gold_mask_authority_claimed": False,
            "production_runtime_claimed": False,
            "production_av_review_claimed": False,
            "production_alignment_bundle_claimed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": (
            "blocked_recovered_foley_verified_packet_not_formable_missing_authoritative_bindings"
        ),
        "next_action": (
            "Use the recovered returned-EC2 mux and provisional A/V report for Row030 "
            "readiness reconciliation without inventing Row028 visual-contact or force authority."
        ),
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="C:/Comfy_UI_Main")
    parser.add_argument("--output", required=True)
    parser.add_argument("--tracker-output", required=True)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        output = project_path(root, Path(args.output))
        tracker_output = project_path(root, Path(args.tracker_output))
        if output == tracker_output:
            raise ValueError("output and tracker output must differ")
        evidence = build_evidence(root, args.timestamp)
        atomic_write(output, evidence)
        atomic_write(tracker_output, evidence)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": evidence["status_decision"],
                "recovered_wav_candidates": len(evidence["recovered_wav_candidates"]),
                "recovered_legacy_event_sources": len(evidence["recovered_legacy_event_sources"]),
                "packet_formable": evidence["strict_packet_readiness"]["packet_formable"],
                "generation_executed": evidence["boundaries"]["generation_executed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
