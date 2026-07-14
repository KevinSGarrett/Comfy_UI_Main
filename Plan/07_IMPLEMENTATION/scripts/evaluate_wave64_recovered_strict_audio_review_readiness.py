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
PROCEDURAL_MANIFEST = RECOVERY_ROOT / (
    "procedural_mix_diagnostic/local_procedural_audio_mix_candidate_20260702_034918.json"
)
RETURNED_MANIFEST = RECOVERY_ROOT / (
    "returned_ec2_20260701T101322/final_ec2_returned_media_manifest.json"
)
SUPPORTING_EVIDENCE = {
    "row027_voice": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_VOICE_DIALOGUE_RECOVERED_SAPI_EVALUATION_20260714T070304-0500.json"
    ),
    "row029_spatial_room": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_SPATIAL_ROOM_RECOVERED_READINESS_20260714T082800-0500.json"
    ),
    "row030_av_sync": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_AV_SYNC_RECOVERED_READINESS_20260714T075606-0500.json"
    ),
}
AUTHORITY_REGISTRY = Path(
    "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"
)
MISSING_REQUIRED_BINDINGS = (
    "run_id",
    "is_synthetic",
    "capture_mode",
    "wave30_event_manifest_binding",
    "wave30_mix_manifest_binding",
    "wave30_qa_report_binding",
    "prompt_reference_binding",
    "prompt_alignment_proof_binding",
)
MISSING_OPTIONAL_PROOFS = (
    "playback_proof_binding",
    "row030_av_sync_report_binding",
    "production_review_bundle_binding",
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
    return {
        item["destination_path"].replace("\\", "/"): item
        for item in recovery.get("artifacts", [])
        if isinstance(item.get("destination_path"), str)
    }


def verify_record(root: Path, relative: Path, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    normalized = relative.as_posix()
    record = records.get(normalized)
    if record is None:
        raise ValueError(f"recovery record missing: {normalized}")
    path = project_path(root, relative)
    if not path.is_file():
        raise ValueError(f"recovered artifact missing: {normalized}")
    observed_hash = sha256(path)
    observed_bytes = path.stat().st_size
    if observed_hash != record.get("sha256") or observed_bytes != record.get("bytes"):
        raise ValueError(f"recovered artifact hash or size mismatch: {normalized}")
    return {
        "path": normalized,
        "sha256": observed_hash,
        "bytes": observed_bytes,
        "recovery_classification": record.get("classification"),
        "copied_not_generated": record.get("copied_not_generated") is True,
    }


def verified_mix(
    root: Path,
    relative: Path,
    records: dict[str, dict[str, Any]],
    nested_record: dict[str, Any],
    authority_class: str,
) -> dict[str, Any]:
    result = verify_record(root, relative, records)
    if result["sha256"] != nested_record.get("sha256"):
        raise ValueError(f"nested manifest hash mismatch: {relative}")
    nested_bytes = nested_record.get("bytes", nested_record.get("size_bytes"))
    if result["bytes"] != nested_bytes:
        raise ValueError(f"nested manifest byte-size mismatch: {relative}")
    result.update(probe_wav(project_path(root, relative)))
    result.update(
        {
            "authority_class": authority_class,
            "eligible_as_mix_wav_binding": True,
            "eligible_as_prompt_alignment_proof": False,
            "eligible_as_playback_review_proof": False,
        }
    )
    return result


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    recovery_path = project_path(root, RECOVERY_EVIDENCE)
    procedural_path = project_path(root, PROCEDURAL_MANIFEST)
    returned_path = project_path(root, RETURNED_MANIFEST)
    registry_path = project_path(root, AUTHORITY_REGISTRY)
    recovery = load_json(recovery_path)
    procedural = load_json(procedural_path)
    returned = load_json(returned_path)
    registry = load_json(registry_path)
    if registry.get("production_review_authorities") != []:
        raise ValueError("production review authorities changed; reassess Row031")
    if registry.get("production_review_bundle_allowlist") != []:
        raise ValueError("production review bundle allowlist changed; reassess Row031")

    records = recovery_records(recovery)
    procedural_manifest_record = verify_record(root, PROCEDURAL_MANIFEST, records)
    returned_manifest_record = verify_record(root, RETURNED_MANIFEST, records)
    procedural_mix_relative = RECOVERY_ROOT / (
        "procedural_mix_diagnostic/wave42_release_scene_03_procedural_audio_mix_candidate.wav"
    )
    returned_mix_relative = RECOVERY_ROOT / (
        "returned_ec2_20260701T101322/final_audio_mix_provisional.wav"
    )
    returned_mix_record = next(
        item
        for item in returned["required_artifacts"]["audio"]
        if item["role"] == "final_audio_mix_provisional"
    )
    candidates = {
        "procedural_diagnostic": verified_mix(
            root,
            procedural_mix_relative,
            records,
            procedural["final_mix"],
            "diagnostic_full_mix_candidate",
        ),
        "returned_runtime_provisional": verified_mix(
            root,
            returned_mix_relative,
            records,
            returned_mix_record,
            "provisional_returned_runtime_mix",
        ),
    }

    supporting: dict[str, Any] = {}
    for role, relative in SUPPORTING_EVIDENCE.items():
        path = project_path(root, relative)
        payload = load_json(path)
        supporting[role] = {
            "path": relative_path(root, path),
            "sha256": sha256(path),
            "status_decision": payload.get("status_decision"),
            "accepted_as_row031_authority": False,
        }

    production_prompt_count = sum(
        not item.get("synthetic_only", False)
        for item in registry.get("prompt_alignment_allowlist", [])
    )
    production_playback_count = sum(
        not item.get("synthetic_only", False)
        for item in registry.get("playback_review_allowlist", [])
    )
    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-STRICT-AUDIO-RECOVERED-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-031",
        "item_id": "ITEM-W64-031",
        "status_decision": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
        "source_manifests": {
            "recovery_evidence": {
                "path": relative_path(root, recovery_path),
                "sha256": sha256(recovery_path),
            },
            "procedural_diagnostic": procedural_manifest_record,
            "returned_runtime": returned_manifest_record,
        },
        "recovered_mix_candidates": candidates,
        "supporting_recovered_evidence": supporting,
        "authority_state": {
            "approved_non_synthetic_prompt_alignment_producer_count": production_prompt_count,
            "approved_non_synthetic_playback_producer_count": production_playback_count,
            "approved_production_review_authority_count": len(
                registry["production_review_authorities"]
            ),
            "approved_production_review_bundle_count": len(
                registry["production_review_bundle_allowlist"]
            ),
            "legacy_qa_labels_accepted_as_prompt_alignment": False,
            "legacy_qa_labels_accepted_as_playback_review": False,
            "legacy_av_report_accepted_as_strict_row030_report": False,
        },
        "mapping_decision": {
            "reusable_mix_binding_candidate_count": len(candidates),
            "missing_required_bindings": list(MISSING_REQUIRED_BINDINGS),
            "missing_optional_proofs": list(MISSING_OPTIONAL_PROOFS),
            "eligible_for_strict_request": False,
            "strict_producer_invoked": False,
            "strict_evaluator_invoked": False,
            "skip_reason": (
                "Fail closed before request production: strict Wave30 event/mix/QA lineage, run "
                "identity, capture classification, prompt reference/alignment, playback, strict "
                "Row030 sync, and production review authority are absent."
            ),
        },
        "boundaries": {
            "existing_audio_reused": True,
            "generation_executed": False,
            "audio_modified_or_remixed": False,
            "identity_or_review_proof_invented": False,
            "legacy_provisional_result_promoted": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_mixes_decodable_but_not_strict_audio_review_request_eligible",
        "next_action": (
            "Retain both mixes as hash-bound diagnostic lineage. Do not form a strict Row031 "
            "request until exact Wave30, prompt-alignment, playback, strict sync, and production "
            "review authority artifacts exist for one selected mix."
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
                "mix_candidates": evidence["mapping_decision"][
                    "reusable_mix_binding_candidate_count"
                ],
                "eligible_for_strict_request": evidence["mapping_decision"][
                    "eligible_for_strict_request"
                ],
                "generation_executed": evidence["boundaries"]["generation_executed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
