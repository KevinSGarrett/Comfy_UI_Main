#!/usr/bin/env python3
"""Reconcile Row022 after genuine pose and relative-depth timeline execution."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260715T145349-0500"
TIMESTAMP = "2026-07-15T14:53:49-05:00"
STATUS = "Blocked_Mask_Contact_And_Target_Shot_Match_Missing_Pose_Depth_Timeline_Pass"
FINAL_GATE = "BLOCKED_MASK_CONTACT_AND_TARGET_SHOT_MATCH"
NOTE = (
    "Wave64 Row022 pose/depth timeline runtime 2026-07-15: one local ComfyUI prompt processed all "
    "49 existing hash-bound Wan reference frames through exact installed DWPose and Depth Anything V2 "
    "assets. Pose and relative-depth timelines, exact source-coordinate transforms, technical QA, and "
    "direct contact-sheet review pass. The row remains blocked on independently verified audio metadata, "
    "trusted mask/contact timelines, and target-output shot matching; no mask or promotion authority changed."
)

RUNNER_PATH = PLAN / "07_IMPLEMENTATION/scripts/run_wave64_reference_pose_depth_timelines.py"
SPEC = importlib.util.spec_from_file_location("row022_pose_depth_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUNNER)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temp.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def run_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "Plan/Instructions/QA/Scripts/test_run_wave64_reference_pose_depth_timelines.py",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Focused Row022 tests failed\n{result.stdout}\n{result.stderr}")
    summary = next((line for line in reversed(result.stdout.splitlines()) if "passed" in line), "")
    if "10 passed" not in summary:
        raise RuntimeError(f"Expected 10 focused tests: {summary}")
    return {"command": " ".join(command), "passed": 10, "failed": 0, "summary": summary}


def update_csv(path: Path, id_field: str, row_id: str, evidence_path: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matches = [row for row in rows if row.get(id_field) == row_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {row_id} in {path}, found {len(matches)}")
    row = matches[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if "Evidence_Path" in row:
        row["Evidence_Path"] = evidence_path
    if "Final_Render_Gate" in row:
        row["Final_Render_Gate"] = FINAL_GATE
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    runtime_dir = PLAN / (
        "Instructions/Operations/Pulled_Back_Artifacts/"
        "wave64_row022_pose_depth_timelines_20260715T145006-0500"
    )
    correction_dir = runtime_dir / "coordinate_contract_revalidation"
    correction_path = correction_dir / "coordinate_revalidation_evidence.json"
    prior_runtime_path = runtime_dir / "runtime_technical_evidence.json"
    requirements_path = ROOT / (
        "Workflows/video_generation/reference_pose_depth_timeline/runtime_requirements.json"
    )
    source_manifest_path = PLAN / (
        "Instructions/QA/Evidence/Wave64/Reference_Video_Input/"
        "wan22_source_diversity_frame_manifest.jsonl"
    )
    source_frames_dir = Path(
        "C:/Comfy_UI_Main/runtime_artifacts/wave64_reference_video_input/"
        "wan22_source_diversity_seed2271401_ingest_20260714/frames"
    )
    timeline_path = PLAN / (
        "Instructions/QA/Evidence/Wave64/Reference_Video_Input/"
        "wan22_source_diversity_timeline_manifest.json"
    )
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_reference_input.json"
    canonical_mirror_path = PLAN / "Tracker/Evidence/Wave64/video_reference_input.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-022_video_reference_input.json"
    evidence_path = PLAN / (
        f"Instructions/QA/Evidence/Wave64/VIDEO_REFERENCE_POSE_DEPTH_TIMELINES_{STAMP}.json"
    )
    evidence_mirror_path = PLAN / (
        f"Tracker/Evidence/Wave64/VIDEO_REFERENCE_POSE_DEPTH_TIMELINES_{STAMP}.json"
    )
    visual_path = PLAN / (
        f"Instructions/QA/Evidence/Wave64/VIDEO_REFERENCE_POSE_DEPTH_VISUAL_QA_{STAMP}.json"
    )
    visual_mirror_path = PLAN / (
        f"Tracker/Evidence/Wave64/VIDEO_REFERENCE_POSE_DEPTH_VISUAL_QA_{STAMP}.json"
    )
    alignment_path = correction_dir / "source_pose_depth_alignment_sheet.png"
    visual_request_path = correction_dir / "visual_review_request.json"

    required = [
        RUNNER_PATH,
        correction_path,
        prior_runtime_path,
        requirements_path,
        source_manifest_path,
        timeline_path,
        canonical_path,
        report_path,
        alignment_path,
        visual_request_path,
        visual_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row022 timeline reconciliation inputs: {missing}")

    tests = run_tests()
    correction = read_json(correction_path)
    prior_runtime = read_json(prior_runtime_path)
    requirements = read_json(requirements_path)
    timeline = read_json(timeline_path)
    canonical = read_json(canonical_path)
    report = read_json(report_path)
    visual_request = read_json(visual_request_path)
    visual = read_json(visual_path)
    records = RUNNER.read_jsonl(source_manifest_path)
    source_paths = RUNNER.validate_source_frames(
        records, source_frames_dir, requirements["source_scope"]
    )
    pose_paths = sorted((runtime_dir / "pose").glob("frame_*.png"))
    depth_paths = sorted((runtime_dir / "depth").glob("frame_*.png"))
    if correction["result"] != (
        "pass_pose_and_relative_depth_timelines_target_mask_contact_authority_blocked"
    ) or not correction["technical_evaluation"]["technical_pass"]:
        raise ValueError("Coordinate-contract revalidation is not pass-like")
    if len(source_paths) != 49 or len(pose_paths) != 49 or len(depth_paths) != 49:
        raise ValueError("Expected exactly 49 source, pose, and depth frames")

    pose_sheet = correction_dir / "pose_contact_sheet.png"
    depth_sheet = correction_dir / "depth_contact_sheet.png"
    if visual_request.get("decision_claimed") is not False:
        raise ValueError("Visual review request improperly claims a decision")
    if visual.get("record_producer") != "Codex_Desktop_after_direct_view_image_review":
        raise ValueError("Independent Codex visual-review record is missing")
    if visual.get("automated_reconciliation_generated") is not False:
        raise ValueError("Automated reconciliation cannot produce the visual-pass decision")
    if visual.get("result") != "pass_motion_pose_and_relative_depth_reference_only":
        raise ValueError("Direct visual review is not pass-like")
    expected_visual_inputs = {
        "pose_contact_sheet": {"path": rel(pose_sheet), "sha256": sha256(pose_sheet)},
        "depth_contact_sheet": {"path": rel(depth_sheet), "sha256": sha256(depth_sheet)},
        "alignment_sheet": {"path": rel(alignment_path), "sha256": sha256(alignment_path)},
    }
    if visual.get("inputs") != expected_visual_inputs or visual_request.get("inputs") != expected_visual_inputs:
        raise ValueError("Visual-review input hashes do not match the prepared packet")
    visual_mirror_path.parent.mkdir(parents=True, exist_ok=True)
    visual_mirror_path.write_bytes(visual_path.read_bytes())

    correction_technical = correction["technical_evaluation"]
    timeline["timestamp"] = TIMESTAMP
    timeline["derived_timelines"]["pose"] = {
        "status": "pass_motion_reference_only",
        "authority_claimed": True,
        "timeline_path": correction_technical["pose_timeline"]["path"],
        "timeline_sha256": correction_technical["pose_timeline"]["sha256"],
        "coordinate_space": "source_480x640",
        "frame_count": 49,
    }
    timeline["derived_timelines"]["depth"] = {
        "status": "pass_relative_depth_reference_only",
        "authority_claimed": True,
        "timeline_path": correction_technical["depth_timeline"]["path"],
        "timeline_sha256": correction_technical["depth_timeline"]["sha256"],
        "metric_depth_claimed": False,
        "render_to_source_transform": correction_technical["coordinate_contract"][
            "render_to_source_transform"
        ],
        "frame_count": 49,
    }
    timeline["derived_timelines"]["mask"] = {
        "status": "blocked_trusted_manual_gold_masks_missing",
        "authority_claimed": False,
    }
    timeline["derived_timelines"]["contact"] = {
        "status": "blocked_trusted_mask_and_contact_timeline_missing",
        "authority_claimed": False,
    }
    timeline["runtime_proof"] = {
        "prompt_id": prior_runtime["prompt_id"],
        "prior_runtime_evidence": rel(prior_runtime_path),
        "prior_runtime_evidence_sha256": sha256(prior_runtime_path),
        "coordinate_revalidation": rel(correction_path),
        "coordinate_revalidation_sha256": sha256(correction_path),
        "direct_visual_qa": rel(visual_path),
        "direct_visual_qa_sha256": sha256(visual_path),
        "runtime_rerun_for_coordinate_correction": False,
    }
    timeline["promotion_ready"] = False
    write_json(timeline_path, timeline)

    evidence = {
        "schema_name": "wave64_reference_pose_depth_timeline_reconciliation",
        "schema_version": "1.0",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-022",
        "item_id": "ITEM-W64-022",
        "result": "pose_and_relative_depth_timeline_pass_mask_contact_and_target_match_blocked",
        "status_decision": STATUS,
        "row_complete": False,
        "source": {
            "frame_manifest": rel(source_manifest_path),
            "frame_manifest_sha256": sha256(source_manifest_path),
            "frame_count": 49,
        },
        "runtime": {
            "prompt_id": prior_runtime["prompt_id"],
            "comfyui_execution_success": True,
            "single_batched_prompt": True,
            "pose_preprocessor_executions": 1,
            "depth_preprocessor_executions": 1,
            "media_generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
        },
        "model_assets": prior_runtime["asset_preflight"],
        "technical_validation": {
            "result": correction["result"],
            "checks": correction_technical["checks"],
            "failed_checks": correction_technical["failed_checks"],
            "pose_summary": correction_technical["pose_summary"],
            "depth_summary": correction_technical["depth_summary"],
            "coordinate_contract": correction_technical["coordinate_contract"],
            "initial_dimension_assumption_preserved": rel(prior_runtime_path),
            "coordinate_correction_without_runtime_rerun": True,
        },
        "direct_visual_qa": {
            "path": rel(visual_path),
            "sha256": sha256(visual_path),
            "result": visual["result"],
        },
        "timeline_manifest": {"path": rel(timeline_path), "sha256": sha256(timeline_path)},
        "tests": tests,
        "resolved_blockers": ["Blocked_Pose_Depth_Timeline_Proof_Missing"],
        "remaining_blockers": [
            "Blocked_Audio_Stream_Independent_Verification_Missing",
            "Blocked_Gold_Mask_Dependency_Missing",
            "Blocked_Target_Shot_Match_Proof_Missing",
        ],
        "authority_boundaries": requirements["authority_boundaries"],
        "next_action": (
            "Preserve completed pose/depth proof. Continue a concrete target-output shot-matching task only "
            "when an exact target derived from this reference exists; keep mask/contact behind trusted gold masks."
        ),
    }
    write_json(evidence_path, evidence)
    write_json(evidence_mirror_path, evidence)
    evidence_rel = rel(evidence_path)

    canonical["timestamp"] = TIMESTAMP
    canonical["implementation"].update(
        {
            "pose_timeline_runtime_ready": True,
            "relative_depth_timeline_runtime_ready": True,
            "coordinate_transform_inversion_recorded": True,
        }
    )
    canonical["acceptance_gates"].update(
        {
            "pose_timeline_generated": True,
            "depth_timeline_generated": True,
            "pose_depth_direct_visual_review": True,
            "mask_timeline_generated": False,
            "contact_timeline_generated": False,
            "target_shot_matching_performed": False,
            "final_promotion_ready": False,
        }
    )
    canonical["blockers"] = [
        blocker
        for blocker in canonical["blockers"]
        if blocker.get("classification") != "Blocked_Pose_Depth_Timeline_Proof_Missing"
    ]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update(
        {
            "derived_timeline_claimed": True,
            "pose_depth_timeline_claimed": True,
            "mask_contact_timeline_claimed": False,
            "source_reference_visual_pass_claimed": True,
            "final_promotion_claimed": False,
        }
    )
    canonical["runtime"].update(
        {
            "comfyui_runtime_prompt_count": 1,
            "comfyui_preexisting_server_used": True,
            "comfyui_server_started_by_this_task": False,
            "pose_frames_generated": 49,
            "relative_depth_frames_generated": 49,
            "media_generation_executed": False,
        }
    )
    canonical["pose_depth_timeline_evidence"] = evidence_rel
    canonical["reconciliation_evidence"] = evidence_rel
    write_json(canonical_path, canonical)
    write_json(canonical_mirror_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["implementation"].update(
        {
            "pose_timeline_runtime_ready": True,
            "relative_depth_timeline_runtime_ready": True,
            "coordinate_transform_inversion_recorded": True,
        }
    )
    report["validation"].update(
        {
            "pose_depth_focused_tests_passed": 10,
            "pose_depth_runtime_prompt": "pass",
            "pose_frames_validated": 49,
            "relative_depth_frames_validated": 49,
            "pose_depth_direct_visual_review": "pass_limited_authority",
        }
    )
    report["acceptance_gates"].update(
        {
            "production_reference_video_runtime": True,
            "pose_timeline_generated": True,
            "depth_timeline_generated": True,
            "pose_depth_direct_visual_review": True,
            "mask_timeline_generated": False,
            "contact_timeline_generated": False,
            "target_shot_matching_performed": False,
            "final_promotion_ready": False,
        }
    )
    report["blockers"] = [
        blocker
        for blocker in report["blockers"]
        if blocker.get("classification") != "Blocked_Pose_Depth_Timeline_Proof_Missing"
    ]
    new_evidence = {"path": evidence_rel, "sha256": sha256(evidence_path)}
    report["evidence"] = [
        entry for entry in report["evidence"] if entry.get("path") != evidence_rel
    ] + [new_evidence]
    report["runtime"].update(
        {
            "comfyui_prompt_count": 1,
            "comfyui_preexisting_server_used": True,
            "comfyui_server_started_by_this_task": False,
            "pose_frames_generated": 49,
            "relative_depth_frames_generated": 49,
            "media_generation_count": 0,
        }
    )
    report["next_action"] = evidence["next_action"]
    write_json(report_path, report)

    tracker_paths = [
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ]
    item_paths = [
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ]
    for path in tracker_paths:
        update_csv(path, "Tracker_ID", "TRK-W64-022", evidence_rel)
    for path in item_paths:
        update_csv(path, "Item_ID", "ITEM-W64-022", evidence_rel)

    print(
        json.dumps(
            {
                "result": evidence["result"],
                "status": STATUS,
                "row_complete": False,
                "pose_frames": 49,
                "relative_depth_frames": 49,
                "tests_passed": 10,
                "evidence": evidence_rel,
                "visual_qa": rel(visual_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
