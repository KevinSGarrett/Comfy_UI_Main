#!/usr/bin/env python3
"""Reconcile Row021 against the existing AnimateDiff strict review packet."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T032400-0500"
TIMESTAMP = "2026-07-13T03:24:00-05:00"
STATUS = "Blocked_Video_Temporal_Visual_Quality_And_Prerequisite_Failure"
NOTE = (
    "Wave64 Row021 reconciliation 2026-07-13: the existing eight-frame sequence now has a "
    "strict review packet, frame grid, GIF playback, continuity measurements, and direct visual "
    "verdict. Motion measurement passes; background/camera and visual quality fail; detector and "
    "body/hand/contact prerequisites remain unavailable. No new generation occurred."
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def update_csv(path: Path, id_field: str, row_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matched = [row for row in rows if row.get(id_field) == row_id]
    if len(matched) != 1:
        raise ValueError(f"Expected one {row_id} row in {path}, found {len(matched)}")
    row = matched[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row021 Strict Temporal Visual Review"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-021` / `ITEM-W64-021` is `{STATUS}`. The existing Row019 eight-frame sequence now has a strict Wave27 packet, frame grid, GIF playback, continuity metrics, and a hash-bound negative Codex visual verdict. Motion measurement passes, but background/camera continuity and direct visual quality fail; identity/face detector evidence is absent, and body/hand/contact subgates remain blocked by visibility and trusted-gold-mask dependencies. No new generation, EC2, FLUX, Jira, mask promotion, hard-gate rerun, or Wave71+ action occurred.

Next action: preserve this failed review and continue `TRK-W64-022` reference-video input reconciliation without treating this sequence as promotable.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + text, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_temporal_visual_review.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-021_video_temporal_visual_review.json"
    base = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500"
    manifest_path = base / "wave27_frame_manifest.json"
    review_dir = base / "wave27_temporal_review"
    packet_path = review_dir / "strict_review_packet/visual_review_packet.json"
    metrics_path = review_dir / "temporal_continuity_metrics.json"
    motion_path = review_dir / "motion_analysis.json"
    background_path = review_dir / "object_background_camera_analysis.json"
    verdict_path = review_dir / "codex_visual_verdict.json"
    temporal_path = review_dir / "wave27_temporal_evidence.json"
    technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_TECHNICAL_QA_20260713T023200-0500.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_VISUAL_QA_20260713T023500-0500.json"
    source_inputs = [manifest_path, packet_path, metrics_path, motion_path, background_path, verdict_path, temporal_path, technical_path, visual_path]
    required = [canonical_path, report_path, *source_inputs]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row021 inputs: {missing}")

    canonical = load(canonical_path)
    report = load(report_path)
    packet = load(packet_path)
    motion = load(motion_path)
    background = load(background_path)
    verdict = load(verdict_path)
    temporal = load(temporal_path)
    technical = load(technical_path)
    visual = load(visual_path)
    expected_missing = {"identity_detector", "face_detector", "body_silhouette_evidence", "hand_finger_evidence", "trusted_contact_mask_evidence"}
    checks = {
        "strict_packet_blocked_expected": packet["status"] == "blocked_missing_prerequisites",
        "review_assets_ready": packet["review_assets_ready"] is True,
        "visual_review_complete": packet["visual_review_complete"] is True,
        "final_pass_false": packet["final_temporal_visual_pass"] is False and packet["final_acceptance_claimed"] is False,
        "eight_frames_bound": len(packet["frames"]) == 8 and packet["source_bindings"]["frame_count"] == 8,
        "missing_categories_exact": set(packet["missing_prerequisite_categories"]) == expected_missing,
        "failed_categories_exact": packet["failed_prerequisite_categories"] == ["object_background_camera_analysis"],
        "motion_measurement_pass": motion["result"] == "pass",
        "background_camera_fail": background["result"] == "fail",
        "codex_verdict_fail": verdict["result"] == "fail",
        "temporal_promotion_blocked": temporal["promotion_decision"] == "block",
        "conservative_identity_flicker_dimensions": temporal["dimension_scores"]["identity_drift"] == 0.0 and temporal["dimension_scores"]["flicker"] == 0.0,
        "packet_manifest_hash_exact": packet["source_bindings"]["manifest_sha256"] == digest(manifest_path),
        "packet_temporal_evidence_hash_exact": packet["source_bindings"]["evidence_sha256"] == digest(temporal_path),
        "verified_prerequisite_hashes_exact": all(
            item["declared_sha256"] == item["observed_sha256"]
            for item in packet["prerequisite_evidence_results"]
            if item["status"] == "verified"
        ),
        "technical_runtime_valid": technical["technical_pass"] is True,
        "visual_quality_failed": visual["visual_temporal_pass"] is False and visual["failed_frame_indexes"] == [5, 6, 7],
        "gold_masks_not_consumed": visual["boundaries"]["gold_masks_consumed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row021 reconciliation checks failed: {failed}")

    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_TEMPORAL_VISUAL_REVIEW_RECONCILIATION_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/VIDEO_TEMPORAL_VISUAL_REVIEW_RECONCILIATION_{STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-TEMPORAL-VISUAL-REVIEW-RECONCILIATION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-021",
        "item_id": "ITEM-W64-021",
        "status_decision": STATUS,
        "inputs": [{"path": rel(path), "sha256": digest(path)} for path in source_inputs],
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "gate_results": {
            "production_frame_sequence_present": True,
            "production_temporal_evidence_present": True,
            "frame_grid_present": True,
            "review_playback_present": True,
            "direct_visual_review_executed": True,
            "motion_analysis_pass": True,
            "object_background_camera_pass": False,
            "identity_face_detector_proof": False,
            "body_hand_contact_proof": False,
            "runtime_proof": True,
            "final_temporal_visual_pass": False,
        },
        "failed_frame_indexes": [5, 6, 7],
        "missing_prerequisite_categories": packet["missing_prerequisite_categories"],
        "failed_prerequisite_categories": packet["failed_prerequisite_categories"],
        "boundaries": {"new_generation_executed": False, "row019_proof_reused": True, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "mask_promotion_claimed": False, "wave71_activation_claimed": False, "production_video_certification_claimed": False},
        "result": "blocked_temporal_visual_quality_and_prerequisite_failure",
        "next_action": "Continue Row022 reference-video input reconciliation; preserve this failed sequence and do not seed-loop or promote it.",
    }
    dump(output_path, evidence)
    dump(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    canonical["production_evidence_inventory"].update({"production_wave27_frame_manifest_present": True, "production_wave27_temporal_evidence_present": True, "production_frame_grid_present": True, "production_review_playback_present": True, "production_detector_evidence_present": False, "production_motion_analysis_present": True, "production_codex_visual_verdict_present": True, "search_scope": rel(review_dir)})
    canonical["acceptance_gates"].update({"per_frame_qa": True, "temporal_identity_check": False, "face_consistency_check": False, "body_silhouette_check": False, "hand_finger_check": False, "contact_zone_check": False, "flicker_detection": False, "motion_consistency": False, "object_background_camera_consistency": False, "frame_grid_and_playback_visual_review": True, "runtime_proof": True, "final_temporal_visual_pass": False, "motion_analysis_measurement_pass": True})
    canonical["runtime"].update({"generation_executed": False, "production_packet_generated": True, "visual_review_executed": True, "comfyui_started": False, "existing_row019_generation_reused": True, "reason": "Strict review executed on the existing sequence and failed visual/background quality while detector and trusted-mask prerequisites remain missing."})
    canonical["blockers"] = [{"classification": STATUS, "scope": "primary_row_blocker", "reason": "Strict packet and direct review exist, but visual/background continuity fails and identity/face detector prerequisites are missing."}, {"classification": "Blocked_Gold_Mask_Dependency_Missing", "scope": "body_hand_contact_subgates_only", "reason": "Full-body visibility and trusted manual body/hand/contact masks remain unavailable; candidate masks were not consumed as truth."}]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update({"row_complete": False, "production_visual_review_claimed": True, "runtime_proof_claimed": True, "final_temporal_visual_pass_claimed": False, "mask_or_geometry_authority_claimed": False, "wave71_activation_claimed": False})
    canonical["reconciliation_evidence"] = rel(output_path)
    dump(canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update({"production_frame_sequence_present": True, "production_visual_review_executed": True, "strict_packet_generated": True, "motion_analysis_result": "pass", "background_camera_analysis_result": "fail", "codex_visual_verdict": "fail"})
    report["acceptance_gates"].update({"per_frame_qa": True, "temporal_identity_check": False, "flicker_detection": False, "motion_consistency": False, "body_hand_contact_consistency": False, "frame_grid_and_playback_visual_review": True, "runtime_proof": True, "final_temporal_visual_pass": False})
    report["blockers"] = canonical["blockers"]
    report["evidence"] = [{"path": rel(canonical_path), "sha256": digest(canonical_path)}, {"path": rel(output_path), "sha256": digest(output_path)}]
    report["runtime"].update({"generation_count": 0, "production_packet_count": 1, "visual_review_count": 1, "comfyui_started": False, "existing_row019_generation_reused": True})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-021")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-021")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))
    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "packet": packet["status"], "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
