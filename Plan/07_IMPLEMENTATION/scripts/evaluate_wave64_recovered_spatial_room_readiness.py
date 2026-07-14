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
RECOVERY_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "AUDIO_PIPELINE_LEGACY_RECOVERY_20260714T063840-0500.json"
)
PROCEDURAL_ROOT = RECOVERY_ROOT / "procedural_mix_diagnostic"
PROCEDURAL_MANIFEST = PROCEDURAL_ROOT / "local_procedural_audio_mix_candidate_20260702_034918.json"
RETURNED_ROOT = RECOVERY_ROOT / "returned_ec2_20260701T101322"
RETURNED_MANIFEST = RETURNED_ROOT / "final_ec2_returned_media_manifest.json"
GATE_RULES = Path("Plan/10_REGISTRIES/wave64_spatial_room_gate_rules.json")

PROCEDURAL_ROLES = {
    "dry_dialogue": "wave42_release_scene_03_dialogue_stem.wav",
    "sfx_foley": "wave42_release_scene_03_sfx_foley_stem.wav",
    "ambience_bed": "wave42_release_scene_03_ambience_stem.wav",
    "music_bed": "wave42_release_scene_03_music_stem.wav",
    "final_mix": "wave42_release_scene_03_procedural_audio_mix_candidate.wav",
}
RETURNED_ROLES = {
    "dry_dialogue": "dialogue_procedural_provisional.wav",
    "sfx_foley": "sfx_foley_original_generated.wav",
    "music_bed": "music_original_generated_bed.wav",
    "final_mix": "final_audio_mix_provisional.wav",
}
MISSING_REQUIRED_BINDINGS = (
    "run_id",
    "shot_id",
    "take_id",
    "is_synthetic",
    "evidence_origin",
    "listener_position",
    "camera_position",
    "camera_orientation",
    "source_position",
    "wave31_spatial_mix_binding",
    "wave31_room_acoustics_binding",
    "spatial_dialogue_artifact_binding",
    "ambience_previous_segment_binding",
    "ambience_current_segment_binding",
)
MISSING_PRODUCTION_PROOFS = (
    "playback_proof_binding",
    "runtime_proof_binding",
    "production_authority_bundle_binding",
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


def probe_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        return {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "sample_rate_hz": sample_rate,
            "frame_count": frames,
            "duration_seconds": round(frames / sample_rate, 6),
            "compression_type": handle.getcomptype(),
            "decode_probe_succeeded": True,
        }


def recovery_records(recovery: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for record in recovery.get("artifacts", []):
        destination = record.get("destination_path")
        if isinstance(destination, str):
            records[destination.replace("\\", "/")] = record
    return records


def verify_recovered_file(root: Path, relative: Path, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    normalized = relative.as_posix()
    record = records.get(normalized)
    if record is None:
        raise ValueError(f"recovery record missing: {normalized}")
    path = project_path(root, relative)
    if not path.is_file():
        raise ValueError(f"recovered artifact missing: {normalized}")
    observed_hash = sha256(path)
    observed_bytes = path.stat().st_size
    if observed_hash != record.get("sha256"):
        raise ValueError(f"recovered artifact hash mismatch: {normalized}")
    if observed_bytes != record.get("bytes"):
        raise ValueError(f"recovered artifact byte-size mismatch: {normalized}")
    return {
        "path": normalized,
        "sha256": observed_hash,
        "bytes": observed_bytes,
        "recovery_classification": record.get("classification"),
        "copied_not_generated": record.get("copied_not_generated") is True,
    }


def verified_wav(
    root: Path,
    relative: Path,
    records: dict[str, dict[str, Any]],
    required_sample_rate: int,
    required_channels: int,
) -> dict[str, Any]:
    result = verify_recovered_file(root, relative, records)
    probe = probe_wav(project_path(root, relative))
    result.update(probe)
    result["strict_profile_checks"] = {
        "sample_rate_matches": probe["sample_rate_hz"] == required_sample_rate,
        "channel_count_matches": probe["channels"] == required_channels,
    }
    result["strict_profile_pass"] = all(result["strict_profile_checks"].values())
    return result


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    recovery_path = project_path(root, RECOVERY_EVIDENCE)
    procedural_manifest_path = project_path(root, PROCEDURAL_MANIFEST)
    returned_manifest_path = project_path(root, RETURNED_MANIFEST)
    rules_path = project_path(root, GATE_RULES)
    recovery = load_json(recovery_path)
    procedural_manifest = load_json(procedural_manifest_path)
    returned_manifest = load_json(returned_manifest_path)
    rules = load_json(rules_path)
    if rules.get("production_rules", {}).get("approved_bundle_allowlist") != []:
        raise ValueError("production bundle allowlist is no longer empty; reassess Row029")

    records = recovery_records(recovery)
    procedural_manifest_record = verify_recovered_file(root, PROCEDURAL_MANIFEST, records)
    returned_manifest_record = verify_recovered_file(root, RETURNED_MANIFEST, records)
    required_sample_rate = rules["mix_rules"]["required_sample_rate_hz"]
    required_channels = rules["mix_rules"]["required_channels"]

    procedural_wavs = {
        role: verified_wav(
            root,
            PROCEDURAL_ROOT / filename,
            records,
            required_sample_rate,
            required_channels,
        )
        for role, filename in PROCEDURAL_ROLES.items()
    }
    returned_wavs = {
        role: verified_wav(
            root,
            RETURNED_ROOT / filename,
            records,
            required_sample_rate,
            required_channels,
        )
        for role, filename in RETURNED_ROLES.items()
    }
    all_wavs = [*procedural_wavs.values(), *returned_wavs.values()]

    procedural_declared = {
        item["stem_id"]: {
            "rms": item.get("rms"),
            "peak": item.get("peak"),
            "nonzero_sample_ratio": item.get("nonzero_sample_ratio"),
        }
        for item in procedural_manifest.get("stems", [])
    }
    procedural_declared["final_mix"] = {
        "rms": procedural_manifest.get("final_mix", {}).get("rms"),
        "peak": procedural_manifest.get("final_mix", {}).get("peak"),
        "nonzero_sample_ratio": procedural_manifest.get("final_mix", {}).get(
            "nonzero_sample_ratio"
        ),
    }

    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-SPATIAL-ROOM-RECOVERED-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-029",
        "item_id": "ITEM-W64-029",
        "status_decision": "Blocked_Spatial_Room_Production_Proof_Missing",
        "source_manifests": {
            "recovery_evidence": {
                "path": relative_path(root, recovery_path),
                "sha256": sha256(recovery_path),
            },
            "procedural_diagnostic": {
                **procedural_manifest_record,
                "quality_label": procedural_manifest.get("quality_label"),
                "production_grade": procedural_manifest.get("production_grade"),
                "completion_claim_allowed": procedural_manifest.get("completion_claim_allowed"),
                "declared_level_metrics": procedural_declared,
            },
            "returned_runtime": {
                **returned_manifest_record,
                "scene_id": returned_manifest.get("scene_id"),
                "release_scene_id": returned_manifest.get("release_scene_id"),
                "completion_claim": returned_manifest.get("completion_claim"),
                "final_release_package_created": returned_manifest.get(
                    "final_release_package_created"
                ),
            },
        },
        "recovered_audio_sets": {
            "procedural_diagnostic": procedural_wavs,
            "returned_runtime_provisional": returned_wavs,
        },
        "strict_profile_comparison": {
            "required_sample_rate_hz": required_sample_rate,
            "required_channels": required_channels,
            "checked_wav_count": len(all_wavs),
            "passed_wav_count": sum(item["strict_profile_pass"] for item in all_wavs),
            "failed_wav_count": sum(not item["strict_profile_pass"] for item in all_wavs),
            "all_recovered_wavs_decode": all(item["decode_probe_succeeded"] for item in all_wavs),
            "all_recovered_wavs_match_strict_profile": all(
                item["strict_profile_pass"] for item in all_wavs
            ),
            "spatial_pan_measurable": False,
            "spatial_pan_unavailable_reason": "All recovered WAVs are mono.",
            "room_rt60_or_reverb_tail_measurable_from_current_evidence": False,
        },
        "mapping_decision": {
            "recoverable_audio_roles": ["dry_dialogue", "ambience_bed", "final_mix"],
            "unproven_audio_roles": ["spatial_dialogue"],
            "missing_required_bindings": list(MISSING_REQUIRED_BINDINGS),
            "missing_production_proofs": list(MISSING_PRODUCTION_PROOFS),
            "legacy_scene_id_accepted_as_complete_identity": False,
            "legacy_level_metrics_accepted_as_room_or_spatial_measurements": False,
            "eligible_for_strict_bundle": False,
            "strict_producer_invoked": False,
            "strict_evaluator_invoked": False,
            "skip_reason": (
                "Fail closed before bundle production: identity, listener/camera/source geometry, "
                "Wave31 spatial and room bindings, spatial dialogue, ambience continuity, and "
                "production proofs are absent; all recovered WAVs also miss the strict mix profile."
            ),
        },
        "boundaries": {
            "existing_audio_reused": True,
            "generation_executed": False,
            "audio_modified_or_remixed": False,
            "identity_geometry_or_proof_fields_invented": False,
            "legacy_provisional_result_promoted": False,
            "production_playback_claimed": False,
            "production_runtime_claimed": False,
            "production_bundle_claimed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_audio_decodable_but_not_spatial_room_bundle_eligible",
        "next_action": (
            "Retain the recovered stems and mixes as diagnostic lineage evidence. Do not remix, "
            "upmix, or assign room geometry until a selected production audio task supplies exact "
            "Wave31, continuity, playback, runtime, and authority bindings."
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
                "checked_wav_count": evidence["strict_profile_comparison"]["checked_wav_count"],
                "all_recovered_wavs_decode": evidence["strict_profile_comparison"][
                    "all_recovered_wavs_decode"
                ],
                "eligible_for_strict_bundle": evidence["mapping_decision"][
                    "eligible_for_strict_bundle"
                ],
                "generation_executed": evidence["boundaries"]["generation_executed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
