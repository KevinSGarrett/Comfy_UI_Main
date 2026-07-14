#!/usr/bin/env python3
"""Complete Wave64 Row021 for the bounded Wan 2.2 temporal QA envelope."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260714T051404-0500"
TIMESTAMP = "2026-07-14T05:14:04-05:00"
STATUS = "Completed_Bounded_Wan22_Temporal_QA_Pass_Fine_Finger_Toe_Certification_Excluded"
NOTE = (
    "Wave64 Row021 completion 2026-07-14: four existing Wan 2.2 clips spanning four "
    "seeds and two sources pass bounded identity, face-at-resolution, gross anatomy, "
    "silhouette, gross hand/foot, floor-contact, motion, flicker, background, camera, "
    "and terminal-frame continuity. Fine finger/toe certification is explicitly excluded "
    "pending a separate higher-resolution or cropped-region gate; production video "
    "certification is not claimed. No generation was rerun."
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


def run_tests() -> tuple[int, str]:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "Plan.Instructions.QA.Scripts.test_analyze_wave27_frame_continuity",
        "Plan.Instructions.QA.Scripts.test_prepare_wave27_strict_visual_review_packet",
        "-v",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Temporal QA tests failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    test_count = sum(1 for line in result.stderr.splitlines() if line.rstrip().endswith("... ok"))
    if test_count != 26:
        raise RuntimeError(f"Expected 26 passing temporal QA tests, observed {test_count}")
    return test_count, " ".join(command)


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
        row["Final_Render_Gate"] = (
            "BOUNDED_TEMPORAL_QA_COMPLETE_FINE_DIGIT_CERTIFICATION_EXCLUDED"
        )
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row021 Bounded Wan 2.2 Temporal QA Complete"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-021` / `ITEM-W64-021` is `{STATUS}`. Four existing 49-frame Wan 2.2 clips across four seeds and two sources pass direct and technical review for bounded identity, face-at-resolution, gross anatomy/silhouette, gross hands/feet, floor contact, motion, flicker, background/camera, and terminal-frame continuity. Fine finger/toe certification is explicitly excluded for this full-body 480x640 envelope and remains a separate higher-resolution or cropped-region follow-up. No masks were required or consumed, no completed seed was rerun, and production video certification remains false.

Next action: continue `TRK-W64-022` / `ITEM-W64-022` reference-video input reconciliation without new generation. Preserve stopped EC2, the manual body-gold-mask boundary, and all Wave71+/Jira restrictions.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def main() -> None:
    script_path = Path(__file__).resolve()
    source_path = PLAN / "04_VIDEO_GIF_SYSTEM/TEMPORAL_QA_AND_KEYFRAME_SYSTEM.md"
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_temporal_visual_review.json"
    canonical_mirror_path = PLAN / "Tracker/Evidence/Wave64/video_temporal_visual_review.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-021_video_temporal_visual_review.json"
    baseline_runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_TI2V5B_TARGET_RUNTIME_SMOKE_20260714T004424-0500.json"
    seed_runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SEED_ROBUSTNESS_TARGET_RUNTIME_20260714T030930-0500.json"
    source_runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SOURCE_DIVERSITY_TARGET_RUNTIME_20260714T043510-0500.json"
    baseline_technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_TECHNICAL_QA_20260714T004424-0500.json"
    seed_technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SEED_ROBUSTNESS_TECHNICAL_QA_20260714T030930-0500.json"
    source_technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_TECHNICAL_QA_20260714T043510-0500.json"
    baseline_visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_VISUAL_QA_20260714T004424-0500.json"
    seed_visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SEED_ROBUSTNESS_VISUAL_QA_20260714T030930-0500.json"
    source_visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_VISUAL_QA_20260714T043510-0500.json"
    test_log_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_TEST_LOG_{STAMP}.json"
    test_log_mirror_path = PLAN / f"Tracker/Evidence/Wave64/VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_TEST_LOG_{STAMP}.json"
    evidence_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_COMPLETION_{STAMP}.json"
    evidence_mirror_path = PLAN / f"Tracker/Evidence/VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_COMPLETION_{STAMP}.json"
    done_path = PLAN / f"Instructions/QA/Evidence/Done_Certifications/W64_VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_BOUNDED_DONE_{STAMP}.json"
    done_mirror_path = PLAN / f"Tracker/Evidence/Done_Certifications/W64_VIDEO_TEMPORAL_VISUAL_REVIEW_WAN22_BOUNDED_DONE_{STAMP}.json"

    source_inputs = [
        script_path,
        source_path,
        baseline_runtime_path,
        seed_runtime_path,
        source_runtime_path,
        baseline_technical_path,
        seed_technical_path,
        source_technical_path,
        baseline_visual_path,
        seed_visual_path,
        source_visual_path,
    ]
    required = [canonical_path, report_path, *source_inputs]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row021 completion inputs: {missing}")

    test_count, test_command = run_tests()
    baseline_runtime = read_json(baseline_runtime_path)
    seed_runtime = read_json(seed_runtime_path)
    source_runtime = read_json(source_runtime_path)
    baseline_technical = read_json(baseline_technical_path)
    seed_technical = read_json(seed_technical_path)
    source_technical = read_json(source_technical_path)
    baseline_visual = read_json(baseline_visual_path)
    seed_visual = read_json(seed_visual_path)
    source_visual = read_json(source_visual_path)

    seed_reviews = seed_visual["seed_reviews"]
    unseen_seed_reviews = [item for item in seed_reviews if item["seed"] in (2271302, 2271303)]
    technical_artifacts = seed_technical["artifacts"]
    unique_artifact_hashes = {
        *(item["sha256"] for item in technical_artifacts),
        source_technical["artifact"]["sha256"],
    }
    checks = {
        "four_unique_clips_bound": len(unique_artifact_hashes) == 4,
        "four_expected_seeds_present": (
            {item["seed"] for item in technical_artifacts} | {source_visual["seed"]}
        ) == {2271301, 2271302, 2271303, 2271401},
        "two_distinct_sources_present": (
            baseline_visual["source_image"]["sha256"]
            != source_runtime["source_contract"]["sha256"]
        ),
        "all_clips_exact_bounded_shape": (
            all(
                item["width"] == 480
                and item["height"] == 640
                and item["decoded_frames"] == 49
                and item["unique_frames"] == 49
                and item["fps"] == 24
                for item in technical_artifacts
            )
            and source_technical["decoder"]["width"] == 480
            and source_technical["decoder"]["height"] == 640
            and source_technical["decoder"]["decoded_frames"] == 49
            and source_technical["decoder"]["unique_frames"] == 49
            and source_technical["decoder"]["fps"] == 24
        ),
        "all_technical_reviews_pass": all(
            item["technical_pass"] is True and not item["failed_checks"]
            for item in (baseline_technical, seed_technical, source_technical)
        ),
        "no_black_or_disallowed_freeze_events": (
            baseline_technical["temporal_detectors"]["blackdetect_event_count"] == 0
            and baseline_technical["temporal_detectors"]["freezedetect_event_count"] == 0
            and seed_technical["checks"]["no_black_frames"] is True
            and seed_technical["checks"]["freeze_runs_within_threshold"] is True
            and source_technical["checks"]["no_black_frames"] is True
            and source_technical["checks"]["freeze_run_within_limit"] is True
        ),
        "baseline_direct_visual_pass": baseline_visual["visual_pass"] is True and not baseline_visual["failed_checks"],
        "three_seed_direct_visual_pass": seed_visual["visual_pass"] is True and not seed_visual["failed_checks"],
        "changed_source_direct_visual_pass": source_visual["visual_pass"] is True and not source_visual["failed_checks"],
        "identity_and_face_pass_at_available_resolution": (
            baseline_visual["checks"]["source_identity_recognizable_through_terminal_frame"] is True
            and baseline_visual["checks"]["face_temporally_coherent"] is True
            and seed_visual["checks"]["same_subject_preserved_across_all_three_seeds"] is True
            and seed_visual["checks"]["face_temporally_coherent_at_available_resolution"] is True
            and source_visual["checks"]["identity_continuity_passed"] is True
            and source_visual["checks"]["face_temporally_coherent_at_available_resolution"] is True
        ),
        "gross_anatomy_and_silhouette_pass": (
            baseline_visual["checks"]["gross_body_warp_or_extra_limb_absent"] is True
            and baseline_visual["checks"]["torso_and_clothing_remain_stable"] is True
            and seed_visual["checks"]["gross_body_warp_or_extra_limb_absent"] is True
            and seed_visual["checks"]["clothing_and_silhouette_continuity_passed"] is True
            and source_visual["checks"]["gross_body_warp_or_extra_limb_absent"] is True
            and source_visual["checks"]["clothing_and_silhouette_continuity_passed"] is True
        ),
        "gross_hands_and_feet_pass": (
            baseline_visual["checks"]["hands_remain_anatomically_stable"] is True
            and baseline_visual["checks"]["legs_and_feet_remain_stable"] is True
            and all(
                item["hands_and_feet_gross_stability"] == "pass_at_available_resolution"
                for item in unseen_seed_reviews
            )
            and source_visual["review"]["hands_gross_stability"] == "pass_at_available_resolution"
            and source_visual["review"]["feet_gross_stability"] == "pass_at_available_resolution"
        ),
        "floor_contact_pass": (
            all(
                item["floor_contact_and_foot_sliding"] == "pass_no_obvious_failure"
                for item in unseen_seed_reviews
            )
            and source_visual["review"]["floor_contact_and_foot_sliding"]
            == "pass_no_obvious_failure"
        ),
        "motion_pass": (
            baseline_visual["checks"]["motion_present_and_restrained"] is True
            and seed_visual["checks"]["motion_present_and_restrained"] is True
            and source_visual["checks"]["motion_present_and_restrained"] is True
        ),
        "background_and_camera_pass": (
            baseline_visual["checks"]["background_continuity_passed"] is True
            and baseline_visual["checks"]["camera_jump_or_cut_absent"] is True
            and seed_visual["checks"]["background_and_camera_continuity_passed"] is True
            and source_visual["checks"]["background_and_camera_continuity_passed"] is True
        ),
        "terminal_frame_pass": (
            baseline_visual["checks"]["terminal_frame_collapse_absent"] is True
            and seed_visual["checks"]["terminal_frame_collapse_absent"] is True
            and source_visual["checks"]["terminal_frame_collapse_absent"] is True
        ),
        "fine_digit_certification_explicitly_excluded": (
            seed_visual["boundaries"]["fine_hand_finger_foot_or_toe_certification_claimed"] is False
            and source_visual["boundaries"]["fine_hand_finger_foot_or_toe_certification_claimed"] is False
        ),
        "production_video_certification_not_claimed": all(
            evidence["boundaries"]["production_video_lane_certification_claimed"] is False
            for evidence in (
                baseline_runtime,
                seed_runtime,
                source_runtime,
                baseline_technical,
                seed_technical,
                source_technical,
                baseline_visual,
                seed_visual,
                source_visual,
            )
        ),
        "masks_not_consumed_or_required": (
            baseline_visual["boundaries"]["gold_masks_consumed"] is False
            and seed_visual["boundaries"]["gold_masks_consumed"] is False
            and source_visual["boundaries"]["gold_masks_consumed"] is False
        ),
        "later_runtime_windows_closed": (
            seed_runtime["execution_reconciliation"]["final_instance_state"] == "stopped"
            and source_runtime["aws_safety"]["final_instance_state"] == "stopped"
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row021 completion checks failed: {failed}")

    test_log = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-TEMPORAL-VISUAL-REVIEW-WAN22-TEST-LOG-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-021",
        "item_id": "ITEM-W64-021",
        "command": test_command,
        "result": "pass",
        "tests_run": test_count,
        "failures": 0,
        "errors": 0,
    }
    write_json(test_log_path, test_log)
    write_json(test_log_mirror_path, test_log)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-TEMPORAL-VISUAL-REVIEW-WAN22-COMPLETION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-021",
        "item_id": "ITEM-W64-021",
        "status_decision": STATUS,
        "source_citation": rel(source_path),
        "inputs": [
            {"path": rel(path), "sha256": sha256(path)}
            for path in [*source_inputs, test_log_path]
        ],
        "bounded_evidence_scope": {
            "engine": "wan_2_2_ti2v_5b_primary_lane",
            "clip_count": 4,
            "seed_count": 4,
            "source_count": 2,
            "frame_count_per_clip": 49,
            "total_decoded_frames": 196,
            "width": 480,
            "height": 640,
            "fps": 24,
        },
        "gate_results": {
            "per_frame_qa": True,
            "temporal_identity_check": True,
            "face_consistency_at_available_resolution": True,
            "gross_body_silhouette_consistency": True,
            "gross_hand_foot_consistency_at_available_resolution": True,
            "floor_contact_consistency": True,
            "flicker_and_freeze_detection": True,
            "motion_consistency": True,
            "object_background_camera_consistency": True,
            "terminal_frame_continuity": True,
            "fine_hand_finger_foot_toe_certification": False,
            "bounded_temporal_visual_pass": True,
            "production_video_lane_certification": False,
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "fine_digit_followup": {
            "required_for_this_bounded_pass": False,
            "certified_here": False,
            "future_gate": "higher_resolution_or_cropped_hand_foot_temporal_review",
        },
        "boundaries": {
            "existing_clips_reused": True,
            "new_generation_executed": False,
            "completed_seeds_rerun": False,
            "aws_contacted_by_this_reconciliation": False,
            "ec2_started_by_this_reconciliation": False,
            "fine_hand_finger_foot_or_toe_certification_claimed": False,
            "long_duration_quality_claimed": False,
            "production_video_lane_certification_claimed": False,
            "gold_masks_consumed": False,
            "mask_or_geometry_authority_claimed": False,
            "wave71_activation_claimed": False,
            "jira_mutated": False,
        },
        "semantic_review": {
            "record": "runtime_artifacts/agent_handoffs/claude_subscription/20260714T051244-0500_w64_row021_wan22_temporal_boundary_review/handoff_record.json",
            "status": "PASS",
            "classification": "CLAUDE_SONNET_HANDOFF_COMPLETED",
            "confidence": "high",
            "blockers": [],
        },
        "result": "pass_bounded_wan22_temporal_qa_fine_digit_certification_excluded",
        "next_action": "Continue Row022 reference-video input reconciliation without new generation.",
    }
    write_json(evidence_path, evidence)
    write_json(evidence_mirror_path, evidence)

    canonical = read_json(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    canonical["production_evidence_inventory"].update(
        {
            "wan22_clip_count": 4,
            "wan22_seed_count": 4,
            "wan22_source_count": 2,
            "wan22_direct_visual_reviews_present": True,
            "wan22_technical_reviews_present": True,
            "production_detector_evidence_present": False,
            "search_scope": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_*",
        }
    )
    canonical["acceptance_gates"].update(evidence["gate_results"])
    canonical["runtime"] = {
        "new_generation_executed": False,
        "existing_wan_clip_count_reused": 4,
        "aws_contacted_by_this_reconciliation": False,
        "ec2_started_by_this_reconciliation": False,
        "final_instance_state_in_reused_proof": "stopped",
    }
    canonical["blockers"] = []
    canonical["excluded_followup"] = evidence["fine_digit_followup"]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = True
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update(
        {
            "row_complete": True,
            "production_visual_review_claimed": True,
            "runtime_proof_claimed": True,
            "bounded_temporal_visual_pass_claimed": True,
            "final_temporal_visual_pass_claimed": True,
            "fine_digit_certification_claimed": False,
            "production_video_lane_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
            "wave71_activation_claimed": False,
        }
    )
    canonical["completion_evidence"] = rel(evidence_path)
    canonical.setdefault("review", {})["claude_wan_boundary_review"] = evidence[
        "semantic_review"
    ]["record"]
    write_json(canonical_path, canonical)
    write_json(canonical_mirror_path, canonical)

    report = read_json(report_path)
    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = True
    historical_validation = {
        "animatediff_fallback_review": {
            "motion_analysis_result": report["validation"].pop(
                "motion_analysis_result", "pass"
            ),
            "background_camera_analysis_result": report["validation"].pop(
                "background_camera_analysis_result", "fail"
            ),
            "codex_visual_verdict": report["validation"].pop(
                "codex_visual_verdict", "fail"
            ),
            "status": "historical_failed_sequence_superseded_by_wan22_evidence",
        }
    }
    report["validation"].update(
        {
            "unit_tests_passed": test_count,
            "unit_test_failures": 0,
            "wan22_clip_count": 4,
            "wan22_seed_count": 4,
            "wan22_source_count": 2,
            "wan22_bounded_temporal_visual_pass": True,
            "fine_digit_certification_excluded": True,
            "historical_validation": historical_validation,
        }
    )
    report["acceptance_gates"].update(evidence["gate_results"])
    report["blockers"] = []
    report["excluded_followup"] = evidence["fine_digit_followup"]
    report["evidence"] = [
        {"path": rel(canonical_path), "sha256": sha256(canonical_path)},
        {"path": rel(evidence_path), "sha256": sha256(evidence_path)},
        {"path": rel(done_path)},
    ]
    report["runtime"] = {
        "new_generation_count": 0,
        "existing_wan_clip_count_reused": 4,
        "ec2_started": False,
        "production_video_certification_claimed": False,
    }
    report["next_action"] = evidence["next_action"]
    write_json(report_path, report)

    done = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-TEMPORAL-VISUAL-REVIEW-WAN22-BOUNDED-DONE-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-021",
        "item_id": "ITEM-W64-021",
        "status_decision": STATUS,
        "done": True,
        "row_scope": "bounded_wan22_temporal_qa",
        "completion_evidence": {"path": rel(evidence_path), "sha256": sha256(evidence_path)},
        "canonical_evidence": {"path": rel(canonical_path), "sha256": sha256(canonical_path)},
        "certification_ceiling": {
            "bounded_temporal_qa_complete": True,
            "fine_hand_finger_foot_or_toe_certified": False,
            "production_video_lane_certified": False,
            "mask_or_geometry_authority_certified": False,
            "wave71_activated": False,
        },
        "rerun_policy": "Do not rerun seeds 2271301, 2271302, 2271303, or 2271401 for Row021.",
    }
    write_json(done_path, done)
    write_json(done_mirror_path, done)
    report["evidence"][-1]["sha256"] = sha256(done_path)
    write_json(report_path, report)

    evidence_rel = rel(evidence_path)
    for path in (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", "TRK-W64-021", evidence_rel)
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-021", evidence_rel)
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
                "clips": 4,
                "seeds": 4,
                "sources": 2,
                "fine_digit_certification": False,
                "production_video_certification": False,
                "next_action": evidence["next_action"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
