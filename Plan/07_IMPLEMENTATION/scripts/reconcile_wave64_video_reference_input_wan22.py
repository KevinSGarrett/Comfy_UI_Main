#!/usr/bin/env python3
"""Reconcile Row022 with an existing hash-bound Wan 2.2 MP4 reference input."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260714T052800-0500"
TIMESTAMP = "2026-07-14T05:28:00-05:00"
STATUS = "Blocked_Derived_Timeline_And_Target_Shot_Match_Proof_Missing_Production_Reference_Ingest_Pass"
NOTE = (
    "Wave64 Row022 production-reference reconciliation 2026-07-14: the existing changed-source "
    "Wan MP4 is now a hash-bound production reference input. All 49 frames decode and extract, "
    "source/frame manifests verify, direct frame QA passes, and ten loop candidates produce a "
    "bounded loop-reference shot plan. Remaining blockers are independently verified audio "
    "metadata, derived pose/depth/mask/contact timelines, and target-output shot matching. "
    "No generation or AWS action occurred."
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run_tests() -> tuple[int, str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "Plan/Instructions/QA/Scripts/test_ingest_wave26_reference_video.py",
        "Plan/Instructions/QA/Scripts/test_analyze_wave26_reference_semantic_candidates.py",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Row022 tests failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    summary_line = next(
        (line for line in reversed(result.stdout.splitlines()) if "passed" in line), ""
    )
    if "40 passed" not in summary_line:
        raise RuntimeError(f"Expected 40 passing Row022 tests, got: {summary_line}")
    return 40, " ".join(command)


def update_csv(path: Path, id_field: str, row_id: str, evidence_path: str) -> None:
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
    if "Evidence_Path" in row:
        row["Evidence_Path"] = evidence_path
    if "Final_Render_Gate" in row:
        row["Final_Render_Gate"] = "BLOCKED_DERIVED_TIMELINES_AND_TARGET_SHOT_MATCH"
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row022 Wan Production Reference Ingest"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-022` / `ITEM-W64-022` is `{STATUS}`. The prior zero-input inventory is superseded by the existing changed-source Wan MP4 already stored under authoritative pulled-back artifacts. The selected source hash is exact; all 49 frames decode and extract at 480x640/24 fps, source and frame manifests verify, existing direct temporal QA supplies semantic frame review, and ten deterministic loop candidates produce a bounded loop-reference shot plan. No completed seed was rerun and no ComfyUI, AWS, EC2, mask promotion, Wave70 hard gate, Wave71+, or Jira action occurred.

Remaining Row022 blockers: audio absence is still an explicit ingest declaration rather than independent stream proof; pose/depth timelines are not generated; mask/contact timelines remain behind trusted manual gold masks; and no target output has been generated from this reference for shot matching. Continue `TRK-W64-023` / `ITEM-W64-023` while preserving these exact Row022 blockers.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def main() -> None:
    script_path = Path(__file__).resolve()
    source_protocol_path = PLAN / "04_VIDEO_GIF_SYSTEM/WAVE26_REFERENCE_VIDEO_INPUT_PIPELINE.md"
    source_video_path = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260714T041921-0500/images/12_wan22_ti2v5b_source_diversity_ref1_78b8_seed2271401_00001_.mp4"
    runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SOURCE_DIVERSITY_TARGET_RUNTIME_20260714T043510-0500.json"
    technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_TECHNICAL_QA_20260714T043510-0500.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_VISUAL_QA_20260714T043510-0500.json"
    ingest_dir = ROOT / "runtime_artifacts/wave64_reference_video_input/wan22_source_diversity_seed2271401_ingest_20260714"
    ingest_evidence_path = ingest_dir / "wave26_reference_video_ingest_evidence.json"
    runtime_reference_manifest_path = ingest_dir / "reference_video_manifest.json"
    runtime_frame_manifest_path = ingest_dir / "frame_manifest.jsonl"
    semantic_path = ROOT / "runtime_artifacts/wave64_reference_video_input/wan22_source_diversity_seed2271401_semantic_candidates_20260714.json"
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_reference_input.json"
    canonical_mirror_path = PLAN / "Tracker/Evidence/Wave64/video_reference_input.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-022_video_reference_input.json"
    durable_dir = PLAN / "Instructions/QA/Evidence/Wave64/Reference_Video_Input"
    durable_manifest_path = durable_dir / "wan22_source_diversity_reference_video_manifest.json"
    durable_frame_manifest_path = durable_dir / "wan22_source_diversity_frame_manifest.jsonl"
    durable_semantic_path = durable_dir / "wan22_source_diversity_semantic_candidates.json"
    timeline_path = durable_dir / "wan22_source_diversity_timeline_manifest.json"
    shot_plan_path = durable_dir / "wan22_source_diversity_loop_shot_plan.json"
    test_log_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_REFERENCE_INPUT_WAN22_TEST_LOG_{STAMP}.json"
    test_log_mirror_path = PLAN / f"Tracker/Evidence/Wave64/VIDEO_REFERENCE_INPUT_WAN22_TEST_LOG_{STAMP}.json"
    evidence_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_REFERENCE_INPUT_WAN22_RECONCILIATION_{STAMP}.json"
    evidence_mirror_path = PLAN / f"Tracker/Evidence/VIDEO_REFERENCE_INPUT_WAN22_RECONCILIATION_{STAMP}.json"

    required = [
        script_path,
        source_protocol_path,
        source_video_path,
        runtime_path,
        technical_path,
        visual_path,
        ingest_evidence_path,
        runtime_reference_manifest_path,
        runtime_frame_manifest_path,
        semantic_path,
        canonical_path,
        report_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row022 Wan reconciliation inputs: {missing}")

    test_count, test_command = run_tests()
    runtime = read_json(runtime_path)
    technical = read_json(technical_path)
    visual = read_json(visual_path)
    ingest = read_json(ingest_evidence_path)
    reference_manifest = read_json(runtime_reference_manifest_path)
    frame_records = read_jsonl(runtime_frame_manifest_path)
    semantic = read_json(semantic_path)

    source_sha = sha256(source_video_path)
    runtime_frame_sha = sha256(runtime_frame_manifest_path)
    frames_dir = ingest_dir / "frames"
    frame_hashes_exact = all(
        (frames_dir / Path(record["frame_path_or_asset_id"]).name).is_file()
        and sha256(frames_dir / Path(record["frame_path_or_asset_id"]).name)
        == record["png_sha256"]
        for record in frame_records
    )
    top_loop = semantic["loop_candidates"][0]
    checks = {
        "source_video_hash_exact": (
            source_sha
            == "5006e96e211538f3d2bb6795e93014d6642946583cc31aa635e171e13e1c80bf"
            == runtime["artifact"]["sha256"]
            == technical["artifact"]["sha256"]
            == ingest["source_video"]["sha256"]
        ),
        "visual_provenance_chain_exact": (
            visual["runtime_evidence"] == rel(runtime_path)
            and visual["technical_evidence"] == rel(technical_path)
            and visual["seed"] == runtime["runtime_unit"]["seed"]
        ),
        "production_runtime_proof_passed": (
            runtime["result"] == "pass_bounded_wan22_changed_source_target_runtime"
            and not runtime["failed_checks"]
        ),
        "technical_decode_passed": technical["technical_pass"] is True and not technical["failed_checks"],
        "direct_visual_frame_qa_passed": visual["visual_pass"] is True and not visual["failed_checks"],
        "ingest_succeeded": ingest["status"] == "success",
        "all_frames_extracted": (
            ingest["ingest"]["decoded_frame_count"] == 49
            and ingest["ingest"]["frames_extracted"] == 49
            and len(frame_records) == 49
        ),
        "frame_indices_and_timestamps_exact": (
            [record["frame_index"] for record in frame_records] == list(range(49))
            and frame_records[0]["timestamp_seconds"] == 0.0
            and frame_records[-1]["timestamp_seconds"] == 2.0
        ),
        "all_frame_png_hashes_exact": frame_hashes_exact,
        "manifest_hashes_exact": (
            sha256(runtime_reference_manifest_path) == ingest["artifacts"]["manifest_sha256"]
            and runtime_frame_sha == ingest["artifacts"]["frame_manifest_sha256"]
        ),
        "selected_source_shape_exact": (
            reference_manifest["width"] == 480
            and reference_manifest["height"] == 640
            and reference_manifest["fps"] == 24
            and reference_manifest["frame_count"] == 49
        ),
        "orientation_noop_cross_checked": (
            reference_manifest["orientation_auto_flag_reported_by_opencv"] == 0
            and reference_manifest["orientation_metadata_degrees_reported_by_opencv"] == 0
            and reference_manifest["explicit_ingest_rotation_applied"] is False
            and technical["decoder"]["width"] == reference_manifest["width"]
            and technical["decoder"]["height"] == reference_manifest["height"]
        ),
        "fps_noop_cross_checked": (
            reference_manifest["fps"] == technical["decoder"]["fps"] == runtime["runtime_unit"]["fps"]
        ),
        "semantic_analysis_bound_to_manifests": (
            semantic["source_bindings"]["frame_manifest"]["sha256"] == runtime_frame_sha
            and semantic["source_bindings"]["reference_manifest"]["sha256"]
            == sha256(runtime_reference_manifest_path)
            and semantic["frame_count"] == 49
        ),
        "semantic_candidate_analysis_completed": (
            semantic["claims"]["motion_peak_sampling_ready"] is True
            and semantic["claims"]["shot_boundary_sampling_ready"] is True
            and semantic["claims"]["loop_candidate_sampling_ready"] is True
        ),
        "loop_candidates_present": len(semantic["loop_candidates"]) == 10,
        "single_shot_no_boundary_candidate": not semantic["shot_boundary_candidates"],
        "audio_independent_verification_missing": (
            ingest["assumptions"]["audio"] == "explicit_cli_declaration_not_verified_by_opencv"
        ),
        "derived_timelines_not_claimed": all(
            ingest["claims"][name] is False
            for name in (
                "pose_timeline_generated",
                "depth_timeline_generated",
                "mask_timeline_generated",
                "contact_timeline_generated",
            )
        ),
        "target_shot_matching_not_claimed": ingest["claims"]["shot_matching_performed"] is False,
        "promotion_remains_fail_closed": (
            ingest["claims"]["final_promotion_ready"] is False
            and semantic["claims"]["final_promotion_ready"] is False
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row022 Wan reconciliation checks failed: {failed}")

    durable_dir.mkdir(parents=True, exist_ok=True)
    write_json(durable_manifest_path, reference_manifest)
    durable_frame_manifest_path.write_bytes(runtime_frame_manifest_path.read_bytes())
    write_json(durable_semantic_path, semantic)

    timeline = {
        "schema_version": "1.0",
        "timeline_id": "wan22_source_diversity_seed2271401_reference_timeline",
        "timestamp": TIMESTAMP,
        "source_video": {"path": rel(source_video_path), "sha256": source_sha},
        "frame_manifest": {
            "path": rel(durable_frame_manifest_path),
            "sha256": sha256(durable_frame_manifest_path),
            "frame_count": 49,
            "fps": 24.0,
        },
        "normalization": {
            "orientation_mode": "verified_bounded_noop_for_selected_source",
            "fps_mode": "verified_bounded_noop_24fps_for_selected_source",
            "audio_mode": "blocked_explicit_declaration_not_independently_verified",
        },
        "semantic_frame_qa": {
            "status": "pass_existing_direct_temporal_visual_review",
            "evidence": rel(visual_path),
            "sha256": sha256(visual_path),
        },
        "derived_timelines": {
            "pose": {"status": "blocked_not_generated", "authority_claimed": False},
            "depth": {"status": "blocked_not_generated", "authority_claimed": False},
            "mask": {
                "status": "blocked_trusted_manual_gold_masks_missing",
                "authority_claimed": False,
            },
            "contact": {
                "status": "blocked_trusted_mask_and_contact_timeline_missing",
                "authority_claimed": False,
            },
        },
        "promotion_ready": False,
    }
    write_json(timeline_path, timeline)

    shot_plan = {
        "schema_version": "1.0",
        "shot_plan_id": "wan22_source_diversity_seed2271401_loop_reference_candidate",
        "timestamp": TIMESTAMP,
        "source_mode": "loop_reference",
        "source_video": {"path": rel(source_video_path), "sha256": source_sha},
        "timeline_manifest": {"path": rel(timeline_path), "sha256": sha256(timeline_path)},
        "selection_method": "highest_deterministic_loop_closure_score",
        "selected_segment": top_loop,
        "shot_boundary_candidate_count": len(semantic["shot_boundary_candidates"]),
        "loop_candidate_count": len(semantic["loop_candidates"]),
        "single_shot_source": True,
        "target_output_generated": False,
        "target_shot_matching_performed": False,
        "candidate_only": True,
        "promotion_ready": False,
    }
    write_json(shot_plan_path, shot_plan)

    test_log = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-REFERENCE-INPUT-WAN22-TEST-LOG-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-022",
        "item_id": "ITEM-W64-022",
        "command": test_command,
        "result": "pass",
        "tests_run": test_count,
        "failures": 0,
        "errors": 0,
    }
    write_json(test_log_path, test_log)
    write_json(test_log_mirror_path, test_log)

    evidence_inputs = [
        script_path,
        source_protocol_path,
        source_video_path,
        runtime_path,
        technical_path,
        visual_path,
        durable_manifest_path,
        durable_frame_manifest_path,
        durable_semantic_path,
        timeline_path,
        shot_plan_path,
        test_log_path,
    ]
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-REFERENCE-INPUT-WAN22-RECONCILIATION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-022",
        "item_id": "ITEM-W64-022",
        "status_decision": STATUS,
        "source_citation": rel(source_protocol_path),
        "inputs": [{"path": rel(path), "sha256": sha256(path)} for path in evidence_inputs],
        "production_reference": {
            "path": rel(source_video_path),
            "sha256": source_sha,
            "provenance": "existing_changed_source_wan22_target_runtime_output_reused_as_reference_input",
            "runtime_proof": rel(runtime_path),
            "technical_qa": rel(technical_path),
            "direct_visual_qa": rel(visual_path),
        },
        "gate_results": {
            "production_reference_video_supplied": True,
            "production_reference_video_runtime_proof": True,
            "reference_frame_extract": True,
            "source_and_frame_hash_binding": True,
            "orientation_noop_verified_for_selected_source": True,
            "fps_noop_verified_for_selected_source": True,
            "audio_presence_independently_verified": False,
            "semantic_frame_qa": True,
            "loop_candidate_shot_plan": True,
            "pose_timeline_generated": False,
            "depth_timeline_generated": False,
            "mask_timeline_generated": False,
            "contact_timeline_generated": False,
            "target_shot_matching_performed": False,
            "source_reference_visual_comparison": False,
            "final_promotion_ready": False,
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "blockers": [
            {
                "classification": "Blocked_Audio_Stream_Independent_Verification_Missing",
                "scope": "selected_reference_metadata",
                "reason": "Audio absence is explicitly declared to ingest but no local ffprobe or equivalent independent stream proof is available.",
            },
            {
                "classification": "Blocked_Pose_Depth_Timeline_Proof_Missing",
                "scope": "derived_pose_depth_timelines",
                "reason": "No pose or depth timeline has been generated for the extracted reference frames.",
            },
            {
                "classification": "Blocked_Gold_Mask_Dependency_Missing",
                "scope": "mask_and_contact_timelines_only",
                "reason": "Trusted manual body masks are still unavailable, so mask/contact timeline authority is not claimed.",
            },
            {
                "classification": "Blocked_Target_Shot_Match_Proof_Missing",
                "scope": "reference_to_target_output_comparison",
                "reason": "A deterministic reference shot plan exists, but no target output has been generated from it for shot matching or visual comparison.",
            },
        ],
        "boundaries": {
            "existing_generated_video_reused_as_reference": True,
            "new_generation_executed": False,
            "completed_seed_rerun": False,
            "aws_contacted": False,
            "ec2_started": False,
            "candidate_masks_consumed_as_truth": False,
            "mask_promotion_claimed": False,
            "production_reference_pipeline_certified": False,
            "wave71_activation_claimed": False,
            "jira_mutated": False,
        },
        "result": "production_reference_ingest_and_loop_shot_plan_pass_derived_timelines_and_target_match_blocked",
        "next_action": "Continue Row023 frame repair/inpainting while preserving Row022 derived-timeline and target-shot-match blockers.",
    }
    write_json(evidence_path, evidence)
    write_json(evidence_mirror_path, evidence)

    canonical = read_json(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    canonical["production_reference_inventory"] = {
        "previous_inventory_evidence": canonical["production_reference_inventory"]["evidence"],
        "previous_candidate_count": canonical["production_reference_inventory"]["candidate_count"],
        "selected_production_reference": rel(source_video_path),
        "selected_reference_sha256": source_sha,
        "production_candidate_discovered": True,
        "inventory_superseded_by_new_authoritative_pulled_back_artifact": True,
    }
    canonical["acceptance_gates"].update(evidence["gate_results"])
    canonical["runtime"].update(
        {
            "production_video_used": True,
            "production_video_count": 1,
            "production_frames_extracted": 49,
            "generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
        }
    )
    canonical["blockers"] = evidence["blockers"]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update(
        {
            "row_complete": False,
            "production_runtime_claimed": True,
            "production_reference_ingest_claimed": True,
            "derived_timeline_claimed": False,
            "source_reference_visual_pass_claimed": False,
            "final_promotion_claimed": False,
            "wave71_activation_claimed": False,
        }
    )
    canonical["reconciliation_evidence"] = rel(evidence_path)
    write_json(canonical_path, canonical)
    write_json(canonical_mirror_path, canonical)

    report = read_json(report_path)
    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update(
        {
            "targeted_test_rerun_passed": test_count,
            "targeted_test_rerun_failed": 0,
            "production_reference_ingest": "pass",
            "production_reference_frames_extracted": 49,
            "production_reference_frame_hashes_verified": 49,
            "semantic_loop_candidates": len(semantic["loop_candidates"]),
            "loop_reference_shot_plan": "pass_candidate_only",
        }
    )
    report["acceptance_gates"].update(evidence["gate_results"])
    report["blockers"] = evidence["blockers"]
    report["evidence"] = [
        {"path": rel(canonical_path), "sha256": sha256(canonical_path)},
        {"path": rel(evidence_path), "sha256": sha256(evidence_path)},
        {"path": rel(timeline_path), "sha256": sha256(timeline_path)},
        {"path": rel(shot_plan_path), "sha256": sha256(shot_plan_path)},
    ]
    report["runtime"].update(
        {
            "production_video_count": 1,
            "production_reference_frames_extracted": 49,
            "generation_count": 0,
            "aws_contacted": False,
            "ec2_started": False,
        }
    )
    report["next_action"] = evidence["next_action"]
    write_json(report_path, report)

    evidence_rel = rel(evidence_path)
    for path in (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", "TRK-W64-022", evidence_rel)
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-022", evidence_rel)
    for name in (
        "NEXT_ACTION.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
        "CURRENT_SESSION_STATE.md",
    ):
        prepend_hydration(PLAN / "Instructions/Hydration_Rehydration" / name, evidence_rel)

    print(
        json.dumps(
            {
                "status": STATUS,
                "checks": evidence["check_summary"],
                "tests": test_count,
                "frames_extracted": 49,
                "loop_candidates": len(semantic["loop_candidates"]),
                "row_complete": False,
                "next_action": evidence["next_action"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
