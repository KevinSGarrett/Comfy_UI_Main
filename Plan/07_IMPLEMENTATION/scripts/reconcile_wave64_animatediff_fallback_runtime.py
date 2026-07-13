#!/usr/bin/env python3
"""Reconcile bounded AnimateDiff runtime proof without promoting video quality."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TRACKER_ID = "TRK-W64-019"
ITEM_ID = "ITEM-W64-019"
STATUS = "Blocked_Video_Visual_Temporal_Quality_Failure"
DECISION = "animatediff_local_runtime_and_manifest_pass_visual_temporal_quality_blocked"
MODEL_RECORD_ID = "MODEL-ANIMATEDIFF-SDXL-V10-BETA-MOTION-001"
QUEUE_ID = "MRQ-W64-110"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def add_entries(current: str, values: list[str]) -> str:
    entries = [item.strip() for item in (current or "").split(";") if item.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def rewrite_csv(
    path: Path, key: str, expected: str, changes: dict[str, Any], note: str
) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        if "Notes" in fields:
            row["Notes"] = note
        for field, value in changes.items():
            if field not in fields:
                continue
            row[field] = add_entries(row.get(field, ""), value) if isinstance(value, list) else str(value)
    if matched != 1:
        raise ValueError(f"Expected one {expected} row in {path}, found {matched}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def upsert_model_registry(path: Path, record: dict[str, Any]) -> None:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [index for index, item in enumerate(records) if item.get("record_id") == record["record_id"]]
    if len(matches) > 1:
        raise ValueError(f"Duplicate model record: {record['record_id']}")
    if matches:
        records[matches[0]] = record
    else:
        records.append(record)
    path.write_text(
        "\n".join(json.dumps(item, separators=(",", ":"), ensure_ascii=True) for item in records)
        + "\n",
        encoding="utf-8",
    )


def upsert_queue(path: Path, record: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matches = [index for index, item in enumerate(rows) if item.get("queue_id") == record["queue_id"]]
    if len(matches) > 1:
        raise ValueError(f"Duplicate queue record: {record['queue_id']}")
    if matches:
        rows[matches[0]] = record
    else:
        rows.append(record)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row019 AnimateDiff Fallback Runtime"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def main() -> None:
    canonical = QA / "video_pipeline_build.json"
    runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_ANIMATEDIFF_FALLBACK_EXECUTE_20260713T022708-0500.json"
    technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_TECHNICAL_QA_20260713T023200-0500.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_VISUAL_QA_20260713T023500-0500.json"
    workflow_path = ROOT / "Workflows/video_generation/animatediff_fallback_lane/workflow.api.json"
    requirements_path = ROOT / "Workflows/video_generation/animatediff_fallback_lane/runtime_requirements.json"
    evaluator_path = PLAN / "07_IMPLEMENTATION/scripts/evaluate_wave64_animatediff_webp_technical.py"
    pullback = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500"
    artifact_path = pullback / "wave64_animatediff_fallback_seed6401901_00001_.webp"
    contact_sheet_path = pullback / "contact_sheet.png"
    manifest_path = pullback / "wave27_frame_manifest.json"
    model_path = ROOT / "ComfyUI/models/animatediff_models/mm_sdxl_v10_beta.ckpt"
    engine_registry_path = PLAN / "10_REGISTRIES/wave27_video_engine_registry.json"
    model_registry_path = PLAN / "Registries/Models/model_registry.jsonl"
    queue_path = PLAN / "Registries/Models/model_runtime_validation_queue.csv"

    required = [
        canonical,
        runtime_path,
        technical_path,
        visual_path,
        workflow_path,
        requirements_path,
        evaluator_path,
        artifact_path,
        contact_sheet_path,
        manifest_path,
        model_path,
        engine_registry_path,
        model_registry_path,
        queue_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing reconciliation inputs: {missing}")

    canonical_payload = read_json(canonical)
    runtime = read_json(runtime_path)
    technical = read_json(technical_path)
    visual = read_json(visual_path)
    requirements = read_json(requirements_path)
    manifest = read_json(manifest_path)
    model_asset = next(item for item in requirements["assets"] if item["role"] == "animatediff_motion_model")
    runtime_artifact = runtime["artifacts"][0]

    checks = {
        "runtime_identity_exact": runtime["tracker_id"] == TRACKER_ID
        and runtime["item_id"] == ITEM_ID
        and runtime["lane_id"] == "animatediff_fallback",
        "runtime_pass_local": runtime["result"] == "pass_local_animatediff_fallback_runtime_smoke"
        and runtime["history"]["completed"] is True
        and not runtime["history"]["node_errors"],
        "artifact_hash_exact": runtime_artifact["sha256"] == sha256(artifact_path),
        "technical_pass": technical["technical_pass"] is True
        and technical["result"] == "pass_local_animatediff_fallback_technical_smoke"
        and not technical["failed_checks"],
        "visual_technical_hash_exact": visual["artifacts"]["technical_qa"]["sha256"]
        == sha256(technical_path),
        "frame_manifest_exact": manifest["frame_count"] == 8 and len(manifest["frames"]) == 8,
        "visual_failure_exact": visual["visual_temporal_pass"] is False
        and visual["status_decision"] == STATUS
        and visual["failed_frame_indexes"] == [5, 6, 7],
        "model_size_exact": model_path.stat().st_size == int(model_asset["size_bytes"]),
        "model_hash_exact": sha256(model_path) == model_asset["sha256"],
        "no_mask_or_wave71_claim": all(
            value is False
            for value in (
                runtime["boundaries"]["mask_or_geometry_authority_claimed"],
                runtime["boundaries"]["wave71_activation_claimed"],
                technical["boundaries"]["mask_or_geometry_authority_claimed"],
                technical["boundaries"]["wave71_activation_claimed"],
                visual["boundaries"]["mask_or_geometry_authority_claimed"],
                visual["boundaries"]["wave71_activation_claimed"],
            )
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Reconciliation checks failed: " + ", ".join(failed))

    existing_attempt = canonical_payload.get("latest_runtime_attempt", {})
    if existing_attempt.get("runtime_evidence") == rel(runtime_path):
        timestamp = canonical_payload["timestamp"]
        stamp = canonical_payload["evidence_id"].removeprefix("W64-VIDEO-PIPELINE-BUILD-RUNTIME-RECONCILIATION-")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        timestamp = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")

    evidence_paths = [
        rel(canonical),
        rel(runtime_path),
        rel(technical_path),
        rel(visual_path),
        rel(workflow_path),
        rel(requirements_path),
        rel(evaluator_path),
        rel(artifact_path),
        rel(contact_sheet_path),
        rel(manifest_path),
    ]

    model_record = {
        "registry_schema_version": "1.0",
        "record_id": MODEL_RECORD_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "source": "aws_s3_existing_mirror",
        "source_url": "s3://comfyui-lora-outputs-029530099913-us-east-1/wave42/ec2_mirror/20260628_211600/ComfyUI/models/animatediff_models/mm_sdxl_v10_beta.ckpt",
        "source_model_id": "wave42-ec2-mirror-mm-sdxl-v10-beta",
        "source_model_version_id": "NwwmypePmWmWRFSnb1mDPgqTNd.eMtfU",
        "model_name": "AnimateDiff SDXL v1.0 beta motion model",
        "model_type": "MotionModel",
        "base_model": "sdxl",
        "version_name": "v1.0 beta",
        "file_name": "mm_sdxl_v10_beta.ckpt",
        "file_extension": ".ckpt",
        "file_size_bytes": model_path.stat().st_size,
        "sha256": sha256(model_path),
        "source_hashes": {"SHA256": sha256(model_path).upper()},
        "local_path": "ComfyUI/models/animatediff_models/mm_sdxl_v10_beta.ckpt",
        "storage_location": "local_runtime_checkout_and_existing_s3_mirror",
        "workflow_lane": "animatediff_fallback",
        "compatibility_status": "local_runtime_smoke_validated_visual_blocked",
        "compatible_engines": ["animatediff", "sdxl"],
        "trigger_words": [],
        "intended_use": "Bounded local AnimateDiff fallback frame-sequence smoke using the existing Wave42 S3 mirror assets.",
        "prompt_notes": "Use only with a scope-bound SDXL checkpoint and explicit frame count, timing, manifest, and visual QA.",
        "negative_prompt_notes": "Block flicker, camera movement, identity drift, background jumps, and terminal-frame corruption.",
        "qa_status": "technical_runtime_pass_visual_temporal_fail",
        "runtime_validation_status": "local_generation_smoke_complete",
        "visual_impact": "The eight-frame smoke is readable but soft and overexposed, then develops background discontinuity and severe terminal-frame color corruption.",
        "video_impact": "Local runtime and frame-manifest handoff are proven; visual/temporal promotion remains blocked.",
        "audio_impact": "None.",
        "known_issues": [
            "This asset was reconciled from an existing S3 mirror rather than newly downloaded from the original publisher.",
            "Frames 5-7 fail strict visual continuity; frame 7 is severely corrupted.",
            "The bounded local smoke is not target-runtime or production video-lane certification.",
        ],
        "last_tested_at": timestamp,
        "evidence_paths": evidence_paths,
    }
    upsert_model_registry(model_registry_path, model_record)
    upsert_queue(
        queue_path,
        {
            "queue_id": QUEUE_ID,
            "created_at": timestamp,
            "model_name": model_record["model_name"],
            "model_type": model_record["model_type"],
            "base_model": model_record["base_model"],
            "local_path": model_record["local_path"],
            "workflow_lane": model_record["workflow_lane"],
            "test_workflow_path": rel(workflow_path),
            "expected_result": "local_8_frame_runtime_and_manifest_pass_visual_temporal_quality_fail",
            "priority": "110",
            "status": "local_generation_smoke_complete",
            "evidence_path": rel(visual_path),
        },
    )

    engine_registry = read_json(engine_registry_path)
    matches = [entry for entry in engine_registry["engines"] if entry.get("id") == "animatediff_fallback"]
    if len(matches) != 1:
        raise ValueError(f"Expected one animatediff_fallback engine, found {len(matches)}")
    engine = matches[0]
    engine.update(
        {
            "model_registry_link": {
                "verification_status": "verified_local_runtime_visual_blocked",
                "value": MODEL_RECORD_ID,
            },
            "object_info_evidence": {
                "verification_status": "verified_local",
                "value": rel(runtime_path),
            },
            "runtime_proof": {
                "verification_status": "verified_local_technical_visual_failed",
                "value": rel(technical_path),
            },
            "supported_outputs": {
                "verification_status": "verified_bounded_local",
                "values": ["animated_webp", "png_frame_sequence", "wave27_frame_manifest"],
            },
            "supported_features": {
                "verification_status": "verified_bounded_local",
                "values": ["sdxl_motion_model", "eight_frame_sequence", "locked_camera_prompt"],
            },
            "resource_limits": {
                "verification_status": "bounded_local_smoke_only",
                "max_width": 256,
                "max_height": 320,
                "max_duration_seconds": 2.0,
                "max_fps": 4.0,
                "min_vram_gb": None,
            },
            "execution_targets": {
                "verification_status": "verified_bounded_local",
                "values": ["local_windows_comfyui"],
            },
            "cost_tiers": {
                "verification_status": "verified_existing_asset_reuse",
                "values": ["local_compute", "existing_s3_cache_read"],
            },
            "availability": {
                "verification_status": "verified_local",
                "state": "runtime_available_visual_quality_blocked",
            },
            "promotion_proof": {
                "verification_status": "blocked_visual_temporal_quality_failure",
                "items": [rel(visual_path)],
            },
        }
    )
    write_json(engine_registry_path, engine_registry)

    implementation = canonical_payload.setdefault("implementation", {})
    implementation.update(
        {
            "existing_wave42_animatediff_assets_reconciled": True,
            "new_video_model_download_avoided": True,
            "animatediff_fallback_workflow_bound": True,
            "animated_webp_technical_evaluator": True,
            "wave27_frame_manifest_compiled_from_runtime": True,
        }
    )
    canonical_payload.update(
        {
            "evidence_id": f"W64-VIDEO-PIPELINE-BUILD-RUNTIME-RECONCILIATION-{stamp}",
            "timestamp": timestamp,
            "status_decision": STATUS,
            "result": "blocked_video_visual_temporal_quality_failure_and_gold_mask_proof_missing",
            "overall_pass": False,
            "latest_runtime_attempt": {
                "lane_id": "animatediff_fallback",
                "runtime_evidence": rel(runtime_path),
                "technical_evidence": rel(technical_path),
                "visual_evidence": rel(visual_path),
                "runtime_pass": True,
                "technical_pass": True,
                "visual_temporal_pass": False,
                "generated_frame_count": 8,
                "animated_export_count": 1,
                "failed_frame_indexes": [5, 6, 7],
                "further_seed_loop_authorized": False,
            },
            "acceptance_gates": {
                "video_workflow_valid": True,
                "keyframe_manifest": False,
                "frame_sequence_manifest": True,
                "frame_sequence_manifest_structural_validator_ready": True,
                "loop_export_gate": False,
                "loop_export_structural_gate_ready": True,
                "artifact_evidence": True,
                "frame_repair_effectiveness": False,
                "frame_repair_policy_structural_gate_ready": True,
                "visual_review_prerequisite_gate_ready": True,
                "strict_frame_sequence_visual_review": False,
            },
            "runtime": {
                "generation_executed": True,
                "generated_frame_count": 8,
                "animated_webp_export_count": 1,
                "final_gif_mp4_webm_export_count": 0,
                "visual_review_executed": True,
                "visual_review_pass": False,
                "aws_contacted_for_existing_asset_discovery": True,
                "ec2_started": False,
                "comfyui_started_and_stopped": True,
                "reason": "Existing Wave42 S3 assets produced one local AnimateDiff frame sequence and animated WebP. Technical runtime and manifest handoff pass, but frames 5-7 fail strict temporal visual quality.",
            },
            "blockers": [
                {
                    "classification": STATUS,
                    "reason": "Frames 5-6 introduce abrupt background changes and frame 7 has severe saturated color and anatomy corruption; visual and temporal promotion fail.",
                },
                {
                    "classification": "Blocked_Gold_Mask_Dependency_Missing",
                    "reason": "Trusted body/contact masks remain unavailable for contact and soft-body video proof; the non-contact fallback smoke does not clear that separate scope.",
                },
            ],
            "strict_decision": {
                "row_complete": False,
                "offline_implementation_pass": True,
                "bounded_local_runtime_pass": True,
                "frame_manifest_pass": True,
                "visual_temporal_pass": False,
                "runtime_or_visual_certification_claimed": False,
                "mask_or_geometry_authority_claimed": False,
                "wave71_activation_claimed": False,
                "reason": "A real local fallback sequence now exists, but strict visual/temporal quality and final export gates fail.",
            },
            "evidence_paths": evidence_paths,
            "next_action": "Preserve this runtime proof. Do not seed-loop. Reopen the fallback only for a materially changed quality configuration; continue other non-mask video orchestration work meanwhile.",
        }
    )
    canonical_payload.setdefault("source_hashes", [])
    canonical_payload["source_hashes"] = [
        {"path": rel(path), "sha256": sha256(path)}
        for path in (runtime_path, technical_path, visual_path, workflow_path, requirements_path, evaluator_path, artifact_path, contact_sheet_path, manifest_path, model_path)
    ]
    stamped = QA / f"VIDEO_PIPELINE_BUILD_RUNTIME_RECONCILIATION_{stamp}.json"
    tracker_mirror = PLAN / "Tracker/Evidence" / stamped.name
    for path in (canonical, stamped, tracker_mirror):
        write_json(path, canonical_payload)

    report_path = PLAN / "Items/Reports/ITEM-W64-019_video_pipeline_build.json"
    report = read_json(report_path)
    report.update(
        {
            "timestamp": timestamp,
            "status": STATUS,
            "row_complete": False,
            "latest_runtime_attempt": canonical_payload["latest_runtime_attempt"],
            "acceptance_gates": canonical_payload["acceptance_gates"],
            "runtime": canonical_payload["runtime"],
            "blockers": canonical_payload["blockers"],
            "evidence": [{"path": path, "sha256": sha256(ROOT / path)} for path in evidence_paths],
            "next_action": canonical_payload["next_action"],
        }
    )
    write_json(report_path, report)

    note = (
        f"Wave64 Row019 {stamp}: reconciled existing AWS Wave42 AnimateDiff assets, verified the motion model hash and node surface, produced one local 8-frame animated WebP, passed technical and Wave27 frame-manifest checks, and failed strict visual/temporal QA on frames 5-7. Runtime proof is no longer missing; promotion remains blocked and no seed loop is authorized."
    )
    tags = [
        "wave64_row019_local_runtime_pass",
        "animatediff_existing_s3_assets_reused",
        "frame_manifest_pass",
        "visual_temporal_quality_blocked",
        "further_seed_loop_prohibited",
    ]
    tracker_paths = (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    )
    item_paths = (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    )
    for path in tracker_paths:
        rewrite_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": STATUS,
                "Status_Decision": DECISION,
                "Evidence_Path": evidence_paths + [rel(stamped), rel(tracker_mirror)],
                "Coverage_Audit_Status": tags,
            },
            note,
        )
    for path in item_paths:
        rewrite_csv(
            path,
            "Item_ID",
            ITEM_ID,
            {
                "Status": STATUS,
                "Evidence_Required": evidence_paths + [rel(stamped), rel(tracker_mirror)],
                "Coverage_Audit_Status": tags,
            },
            note,
        )

    block = f"""## Wave64 Row019 AnimateDiff Fallback Runtime - {timestamp}

`{TRACKER_ID}` / `{ITEM_ID}` is `{STATUS}`. Existing Wave42 AnimateDiff assets were found in S3 and reused: the motion model hash, custom-node commit, live object-info surface, local eight-frame runtime, animated WebP export, technical evaluator, and Wave27 frame manifest all pass. Direct review fails frames 5-7 for background discontinuity and terminal-frame color/anatomy corruption, so no visual, temporal, target-runtime, or production-lane certification is claimed. No EC2 start, masks, Wave71+, FLUX, or Jira action occurred.

Next action: preserve this proof and continue the next concrete non-mask video orchestration task without seed-looping Row019.

Evidence: `{rel(canonical)}`; `{rel(runtime_path)}`; `{rel(technical_path)}`; `{rel(visual_path)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(HYD / name, block)

    print(
        json.dumps(
            {
                "status": STATUS,
                "checks": {"checked": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
                "model_record": MODEL_RECORD_ID,
                "queue_id": QUEUE_ID,
                "engine_state": engine["availability"]["state"],
                "runtime_pass": True,
                "visual_temporal_pass": False,
                "row_complete": False,
                "next_action": canonical_payload["next_action"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
