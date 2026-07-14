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

import av


RECOVERY_ROOT = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "wave42_legacy_audio_recovery_20260714T063840-0500"
)
RETURNED_ROOT = RECOVERY_ROOT / "returned_ec2_20260701T101322"
RETURNED_MANIFEST = RETURNED_ROOT / "final_ec2_returned_media_manifest.json"
LEGACY_AV_REPORT = RETURNED_ROOT / "av_sync_validation_report.json"
LEGACY_TIMELINE = RECOVERY_ROOT / "legacy_event_sources/master_av_sync_timeline.json"
GATE_RULES = Path("Plan/10_REGISTRIES/wave64_av_sync_gate_rules.json")
MISSING_REQUIRED_FIELDS = (
    "run_id",
    "shot_id",
    "take_id",
    "is_synthetic",
    "evidence_origin",
    "source_video_artifact",
    "wave30_event_manifest_binding",
    "wave30_mix_manifest_binding",
    "observed_anchor_measurement_proof_binding",
)
MISSING_PRODUCTION_PROOFS = (
    "playback_proof_binding",
    "runtime_proof_binding",
    "production_certification_bundle_binding",
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


def probe_mux(path: Path) -> dict[str, Any]:
    with av.open(str(path)) as container:
        streams = []
        for stream in container.streams:
            context = stream.codec_context
            duration = (
                round(float(stream.duration * stream.time_base), 6)
                if stream.duration is not None
                else None
            )
            streams.append(
                {
                    "index": stream.index,
                    "type": stream.type,
                    "codec": context.name,
                    "duration_seconds": duration,
                    "sample_rate": getattr(context, "sample_rate", None),
                    "channels": getattr(context, "channels", None),
                    "width": getattr(context, "width", None),
                    "height": getattr(context, "height", None),
                    "average_rate": str(getattr(stream, "average_rate", None)),
                }
            )
        return {
            "container_format": container.format.name,
            "duration_seconds": round(container.duration / 1_000_000, 6),
            "streams": streams,
            "decode_probe_succeeded": True,
        }


def probe_wav(path: Path) -> dict[str, Any]:
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


def require_file_record(path: Path, expected_hash: str, expected_bytes: int) -> None:
    if not path.is_file():
        raise ValueError(f"recovered artifact missing: {path}")
    if sha256(path) != expected_hash:
        raise ValueError(f"recovered artifact hash mismatch: {path}")
    if path.stat().st_size != expected_bytes:
        raise ValueError(f"recovered artifact byte-size mismatch: {path}")


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = project_path(root, RETURNED_MANIFEST)
    report_path = project_path(root, LEGACY_AV_REPORT)
    timeline_path = project_path(root, LEGACY_TIMELINE)
    rules_path = project_path(root, GATE_RULES)
    manifest = load_json(manifest_path)
    legacy_report = load_json(report_path)
    timeline = load_json(timeline_path)
    rules = load_json(rules_path)
    if rules.get("production_rules", {}).get("approved_certification_bundle_allowlist") != []:
        raise ValueError("production certification allowlist is no longer empty; reassess Row030")

    video_record = manifest["required_artifacts"]["video"]
    audio_record = next(
        item
        for item in manifest["required_artifacts"]["audio"]
        if item["role"] == "final_audio_mix_provisional"
    )
    mux_path = manifest_path.parent / video_record["path"]
    audio_path = manifest_path.parent / audio_record["path"]
    require_file_record(mux_path, video_record["sha256"], video_record["size_bytes"])
    require_file_record(audio_path, audio_record["sha256"], audio_record["size_bytes"])
    require_file_record(
        report_path,
        manifest["required_artifacts"]["av_sync_report"]["sha256"],
        manifest["required_artifacts"]["av_sync_report"]["size_bytes"],
    )

    mux_probe = probe_mux(mux_path)
    wav_probe = probe_wav(audio_path)
    video_stream = next(stream for stream in mux_probe["streams"] if stream["type"] == "video")
    audio_stream = next(stream for stream in mux_probe["streams"] if stream["type"] == "audio")
    expected = rules["mux_rules"]
    profile_checks = {
        "container_allowed": mux_probe["container_format"] in expected["allowed_container_formats"],
        "video_codec_allowed": video_stream["codec"] == expected["required_video_codec"],
        "audio_codec_allowed": audio_stream["codec"] == expected["required_audio_codec"],
        "audio_sample_rate_allowed": (
            audio_stream["sample_rate"] == expected["required_audio_sample_rate_hz"]
        ),
        "audio_channel_count_allowed": audio_stream["channels"] == expected["required_audio_channels"],
    }
    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-AV-SYNC-RECOVERED-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-030",
        "item_id": "ITEM-W64-030",
        "status_decision": "Blocked_AV_Sync_Production_Proof_Missing",
        "recovered_artifacts": {
            "returned_manifest": {
                "path": relative_path(root, manifest_path),
                "sha256": sha256(manifest_path),
            },
            "legacy_av_report": {
                "path": relative_path(root, report_path),
                "sha256": sha256(report_path),
                "reported_overall_status": legacy_report.get("overall_status"),
                "accepted_as_current_strict_proof": False,
                "rejection_reason": (
                    "Legacy report is explicitly provisional and does not implement any accepted "
                    "Wave64 proof schema, producer identity, or hash lineage contract."
                ),
            },
            "legacy_timeline": {
                "path": relative_path(root, timeline_path),
                "sha256": sha256(timeline_path),
                "timeline_id": timeline.get("timeline_id"),
                "accepted_as_wave30_manifest": False,
            },
            "final_audio_mix": {
                "path": relative_path(root, audio_path),
                "sha256": sha256(audio_path),
                "bytes": audio_path.stat().st_size,
                **wav_probe,
                "authority_class": "provisional_returned_runtime_audio",
            },
            "final_mux_candidate": {
                "path": relative_path(root, mux_path),
                "sha256": sha256(mux_path),
                "bytes": mux_path.stat().st_size,
                **mux_probe,
                "authority_class": "provisional_returned_runtime_mux",
            },
        },
        "strict_profile_comparison": {
            "required_profile": {
                "container_formats": expected["allowed_container_formats"],
                "video_codec": expected["required_video_codec"],
                "audio_codec": expected["required_audio_codec"],
                "audio_sample_rate_hz": expected["required_audio_sample_rate_hz"],
                "audio_channels": expected["required_audio_channels"],
            },
            "observed_profile": {
                "container_format": mux_probe["container_format"],
                "video_codec": video_stream["codec"],
                "audio_codec": audio_stream["codec"],
                "audio_sample_rate_hz": audio_stream["sample_rate"],
                "audio_channels": audio_stream["channels"],
                "duration_seconds": mux_probe["duration_seconds"],
            },
            "checks": profile_checks,
            "passed_check_count": sum(profile_checks.values()),
            "failed_check_count": sum(not value for value in profile_checks.values()),
            "strict_mux_profile_pass": all(profile_checks.values()),
        },
        "mapping_decision": {
            "scene_id": manifest.get("scene_id"),
            "missing_required_fields": list(MISSING_REQUIRED_FIELDS),
            "missing_production_proofs": list(MISSING_PRODUCTION_PROOFS),
            "source_video_distinct_from_final_mux_proven": False,
            "legacy_report_current_proof_role": None,
            "eligible_for_strict_packet": False,
            "strict_evaluator_invoked": False,
            "strict_evaluator_skip_reason": (
                "Fail closed before packet production: required identity, source-video, Wave30, "
                "and anchor bindings are absent, and recovered MP4 does not meet strict mux profile."
            ),
        },
        "boundaries": {
            "existing_media_reused": True,
            "generation_executed": False,
            "media_modified_or_remuxed": False,
            "identity_or_proof_fields_invented": False,
            "legacy_provisional_pass_promoted": False,
            "production_playback_claimed": False,
            "production_runtime_claimed": False,
            "production_bundle_claimed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_mux_decodable_but_not_strict_packet_eligible",
        "next_action": (
            "Retain the recovered mux as provisional lineage evidence; do not remux or regenerate "
            "until an explicit strict-source and proof-chain task is selected."
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
                "mux_decodable": evidence["recovered_artifacts"]["final_mux_candidate"]["decode_probe_succeeded"],
                "strict_mux_profile_pass": evidence["strict_profile_comparison"]["strict_mux_profile_pass"],
                "eligible_for_strict_packet": evidence["mapping_decision"]["eligible_for_strict_packet"],
                "generation_executed": evidence["boundaries"]["generation_executed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
