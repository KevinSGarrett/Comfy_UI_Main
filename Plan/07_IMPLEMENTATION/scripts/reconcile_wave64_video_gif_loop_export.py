#!/usr/bin/env python3
"""Reconcile Row024 against the real deterministic GIF export and visual failure."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T044336-0500"
TIMESTAMP = "2026-07-13T04:43:36-05:00"
STATUS = "Blocked_Video_GIF_Loop_Playback_Quality_Failure"
NOTE = (
    "Wave64 Row024 real deterministic export 2026-07-13: the actual eight-frame sequence "
    "exports as a hash-bound GIF89a with verified non-synthetic runtime proof and full technical "
    "parity, but direct playback/contact-sheet review fails frames 5-7 and the frame-7-to-frame-0 "
    "loop seam. Final export and promotion remain blocked."
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


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
    marker = "## Wave64 Row024 Real GIF Loop Export"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-024` / `ITEM-W64-024` is `{STATUS}`. The real Row019 eight-frame sequence was exported deterministically to an 8-frame, 256x320 GIF89a with 250 ms frame timing, infinite looping, hash-bound non-synthetic runtime proof, and full technical parity. Direct review of the candidate and decoded contact sheet fails frames 5-7 for background/lighting discontinuity and terminal face/clothing/color collapse; the frame-7-to-frame-0 boundary has a severe visible pop. The certifier correctly remains blocked on visual playback only. No ComfyUI generation, AWS, EC2, mask use/promotion, hard-gate rerun, Jira mutation, or Wave71+ activation occurred.

Next action: preserve this failed real loop and continue `TRK-W64-025` / `ITEM-W64-025` audio-pipeline reconciliation without treating the GIF as final-export ready.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + text, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_gif_loop_export.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/video_gif_loop_export.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-024_video_gif_loop_export.json"
    test_log_path = PLAN / "Instructions/QA/Evidence/Wave64/video_gif_loop_export_test_log.json"
    base = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500"
    manifest_path = base / "wave27_frame_manifest.json"
    temporal_path = base / "wave27_temporal_review/wave27_temporal_evidence.json"
    export_dir = base / "wave26_gif_export"
    candidate_path = export_dir / "candidate.gif"
    contact_sheet_path = export_dir / "candidate_contact_sheet.png"
    export_manifest_path = export_dir / "export_manifest.json"
    runtime_proof_path = export_dir / "runtime_proof.json"
    attestation_path = export_dir / "attestation.json"
    certifier_path = export_dir / "gif_loop_export_evidence_attested.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_REAL_GIF_LOOP_VISUAL_QA_20260713T044336-0500.json"
    row023_path = PLAN / "Instructions/QA/Evidence/Wave64/VIDEO_FRAME_REPAIR_REAL_SEQUENCE_ROUTING_20260713T042629-0500.json"
    worker_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T043909-0500_w64_row024_real_export_cli_mapping/handoff_record.json"
    claude_review_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T044734-0500_w64_row024_semantic_final_review/handoff_record.json"
    claude_confirmation_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T045400-0500_w64_row024_semantic_remediation_review/handoff_record.json"
    required = [canonical_path, report_path, test_log_path, manifest_path, temporal_path, candidate_path, contact_sheet_path, export_manifest_path, runtime_proof_path, attestation_path, certifier_path, visual_path, row023_path, worker_path, claude_review_path, claude_confirmation_path]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row024 inputs: {missing}")

    canonical = load(canonical_path)
    report = load(report_path)
    test_log = load(test_log_path)
    manifest = load(manifest_path)
    temporal = load(temporal_path)
    export_manifest = load(export_manifest_path)
    runtime_proof = load(runtime_proof_path)
    attestation = load(attestation_path)
    certifier = load(certifier_path)
    visual = load(visual_path)
    row023 = load(row023_path)
    worker = load(worker_path)
    claude_review = load(claude_review_path)
    claude_confirmation = load(claude_confirmation_path)
    checks = {
        "canonical_row_exact": canonical["tracker_id"] == "TRK-W64-024" and canonical["item_id"] == "ITEM-W64-024",
        "report_row_exact": report["tracker_id"] == "TRK-W64-024" and report["item_id"] == "ITEM-W64-024",
        "candidate_hash_bound": export_manifest["candidate_gif"]["sha256"] == digest(candidate_path) == runtime_proof["candidate_gif_sha256"],
        "manifest_hash_bound": export_manifest["source_bindings"]["frame_manifest"]["sha256"] == digest(manifest_path) == runtime_proof["manifest_sha256"],
        "temporal_hash_bound": export_manifest["source_bindings"]["temporal_evidence"]["sha256"] == digest(temporal_path) == runtime_proof["temporal_evidence_sha256"],
        "eight_frame_parity": export_manifest["frame_count"] == 8 and certifier["candidate_binding"]["decoded_frame_count"] == 8,
        "dimension_parity": export_manifest["dimensions"] == {"width": 256, "height": 320} and certifier["parity_checks"]["dimensions_match"] is True,
        "timing_parity": export_manifest["frame_durations_ms"] == [250] * 8 and certifier["parity_checks"]["timing_match"] is True,
        "infinite_loop_parity": export_manifest["loop_count"] == 0 and certifier["parity_checks"]["loop_count_match"] is True,
        "gif89a_container": export_manifest["candidate_gif"]["container_header"] == "GIF89a" and certifier["candidate_binding"]["container_header"] == "GIF89a",
        "attestation_non_synthetic": attestation["synthetic_input"] is False and certifier["synthetic_input"] is False,
        "runtime_proof_verified": certifier["runtime_proof"]["verified"] is True and certifier["runtime_proof"]["generation_executed"] is True,
        "runtime_proof_scope_exact": runtime_proof["generation_scope"] == "deterministic_gif_export_only" and runtime_proof["comfyui_generation_executed"] is False,
        "technical_checks_passed": certifier["technical_checks"]["technical_passed"] is True,
        "visual_review_executed": visual["checks"]["candidate_decoded_and_reviewed"] is True and visual["checks"]["all_eight_frames_reviewed"] is True,
        "visual_failed_indexes_exact": visual["failed_frame_indexes"] == [5, 6, 7],
        "visual_loop_failed": visual["visual_loop_pass"] is False and visual["checks"]["first_last_loop_seam_passed"] is False,
        "certifier_visual_only_blocker": certifier["decision"]["blocker_codes"] == ["visual_playback_review_absent_or_failed"],
        "certifier_final_blocked": certifier["decision"]["blocked"] is True and certifier["decision"]["final_export_passed"] is False,
        "row023_rerun_preserved": row023["routing"]["recommended_action"] == "rerun_shot",
        "worker_handoff_passed": worker["status"] == "PASS" and worker["classification"] == "CURSOR_HANDOFF_COMPLETED",
        "claude_initial_review_passed": claude_review["status"] == "PASS" and "One MEDIUM" in claude_review["result_excerpt"],
        "claude_confirmation_passed": claude_confirmation["status"] == "PASS" and "No HIGH or MEDIUM findings remain" in claude_confirmation["result_excerpt"],
        "existing_tests_passed": test_log["tests_run"] == 26 and test_log["failures"] == 0 and test_log["errors"] == 0,
        "candidate_masks_not_consumed": visual["boundaries"]["gold_masks_consumed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row024 reconciliation checks failed: {failed}")

    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_GIF_LOOP_EXPORT_REAL_RUNTIME_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/VIDEO_GIF_LOOP_EXPORT_REAL_RUNTIME_{STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-GIF-LOOP-EXPORT-REAL-RUNTIME-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-024",
        "item_id": "ITEM-W64-024",
        "status_decision": STATUS,
        "inputs": [{"path": rel(path), "sha256": digest(path)} for path in [manifest_path, temporal_path, candidate_path, contact_sheet_path, export_manifest_path, runtime_proof_path, attestation_path, certifier_path, visual_path, row023_path]],
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "validation": {
            "command": "python -m unittest Plan.Instructions.QA.Scripts.test_wave26_gif_loop_export_strict Plan.Instructions.QA.Scripts.test_export_wave26_deterministic_gif",
            "tests_passed": 26,
            "tests_failed": 0,
            "elapsed_seconds": 78.283,
            "python_compile": "pass"
        },
        "real_export": {"candidate_path": rel(candidate_path), "candidate_sha256": digest(candidate_path), "candidate_bytes": candidate_path.stat().st_size, "frame_count": 8, "width": 256, "height": 320, "frame_durations_ms": [250] * 8, "loop_count": 0, "container_header": "GIF89a", "technical_seam_metric": certifier["technical_checks"]["seam_metric_value"]},
        "gate_results": {"real_non_synthetic_candidate_present": True, "technical_export_pass": True, "runtime_generation_proof": True, "candidate_visual_review_executed": True, "loop_playback_visual_pass": False, "identity_and_no_popping_visual_pass": False, "final_export_certification": False},
        "failed_frame_indexes": [5, 6, 7],
        "semantic_worker": {"path": rel(worker_path), "sha256": digest(worker_path)},
        "semantic_review": {"initial_path": rel(claude_review_path), "initial_sha256": digest(claude_review_path), "medium_findings_remediated": 1, "confirmation_path": rel(claude_confirmation_path), "confirmation_sha256": digest(claude_confirmation_path), "remaining_high_or_medium_findings": 0},
        "boundaries": {"comfyui_generation_executed": False, "gif_export_executed": True, "aws_contacted": False, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "mask_promotion_claimed": False, "wave70_hard_gate_rerun": False, "wave71_activation_claimed": False},
        "result": "blocked_real_gif_loop_playback_quality_failure",
        "next_action": "Continue TRK-W64-025 / ITEM-W64-025 audio-pipeline reconciliation; preserve this failed GIF and do not claim final export readiness.",
    }
    dump(output_path, evidence)
    dump(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    implementation_hashes = {
        "Plan/07_IMPLEMENTATION/scripts/certify_wave26_gif_loop_export.py": "2a83fe9de7edeaa85bae37920692193ee2737732f2a642b9d467947160eb2c96",
        "Plan/Instructions/QA/Scripts/test_wave26_gif_loop_export_strict.py": "f2fc7de1c5b8d96ab9aaab63f932f0c2ce63e61aafa003bc97fe3c68915f6f3b",
    }
    for artifact in canonical["implementation_artifacts"]:
        if artifact["path"] in implementation_hashes:
            artifact["sha256"] = implementation_hashes[artifact["path"]]
    canonical["acceptance_gates"].update({"production_gif_candidate_present": True, "production_runtime_proof": True, "loop_playback_visual_review": True, "identity_and_no_popping_visual_pass": False, "final_export_certification": False})
    canonical["real_runtime_export"] = {"evidence": rel(output_path), "candidate": rel(candidate_path), "candidate_sha256": digest(candidate_path), "runtime_proof_verified": True, "technical_passed": True, "visual_review_executed": True, "visual_loop_pass": False, "failed_frame_indexes": [5, 6, 7]}
    canonical["review"].update({"cursor_real_export_cli_mapping": rel(worker_path), "codex_real_candidate_visual_review": rel(visual_path), "claude_real_export_review": rel(claude_review_path), "claude_real_export_medium_findings_remediated": 1, "claude_real_export_confirmation": rel(claude_confirmation_path), "remaining_remediable_high_or_medium_findings": 0})
    canonical["offline_validation"].update({"last_targeted_rerun": TIMESTAMP, "last_targeted_rerun_tests_passed": 26, "last_targeted_rerun_tests_failed": 0})
    canonical["runtime"].update({"production_gif_generation_count": 1, "production_runtime_proof_count": 1, "production_loop_playback_review_count": 1, "comfyui_started": False, "generation_executed": False, "aws_contacted": False, "ec2_started": False})
    canonical["blockers"] = [{"classification": STATUS, "scope": "primary_row_blocker", "reason": "The real deterministic GIF passes technical/runtime gates but fails direct playback review for frames 5-7, background/identity corruption, and a severe terminal-to-first loop pop."}]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update({"row_complete": False, "production_runtime_claimed": True, "visual_loop_review_claimed": True, "visual_loop_pass_claimed": False, "final_export_claimed": False, "certification_claimed": False, "wave71_activation_claimed": False})
    canonical["reconciliation_evidence"] = rel(output_path)
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update({"real_deterministic_export": "pass", "real_candidate_sha256": digest(candidate_path), "real_runtime_proof": "verified", "real_technical_certifier": "pass", "real_visual_review": "fail", "real_failed_frame_indexes": [5, 6, 7], "targeted_test_rerun_passed": 26, "targeted_test_rerun_failed": 0, "claude_semantic_confirmation": "PASS_NO_HIGH_OR_MEDIUM_FINDINGS"})
    report["acceptance_gates"].update({"production_gif_candidate": True, "production_runtime_ready": True, "visual_loop_playback_review": True, "identity_and_no_popping_pass": False, "final_export_certification": False})
    report["blockers"] = canonical["blockers"]
    report["evidence"] = [{"path": rel(canonical_path), "sha256": digest(canonical_path)}, {"path": rel(test_log_path), "sha256": digest(test_log_path)}, {"path": rel(output_path), "sha256": digest(output_path)}, {"path": rel(visual_path), "sha256": digest(visual_path)}]
    report["runtime"].update({"production_gif_generation_count": 1, "production_runtime_proof_count": 1, "production_visual_review_count": 1, "comfyui_started": False, "aws_contacted": False, "ec2_started": False})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-024")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-024")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))
    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "real_export": evidence["real_export"], "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
