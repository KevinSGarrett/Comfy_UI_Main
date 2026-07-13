#!/usr/bin/env python3
"""Reconcile Row023 against the real Row019/Row021 failed frame sequence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T042629-0500"
TIMESTAMP = "2026-07-13T04:26:29-05:00"
STATUS = "Blocked_Video_Frame_Repair_Rerun_Shot_Required"
NOTE = (
    "Wave64 Row023 real-sequence routing 2026-07-13: frames 5-7 are hash-bound to "
    "persistent shot instability, with frame 7 also carrying identity drift. The strict planner "
    "routes the span to rerun_shot; the isolated-flicker executor rejects it transactionally, so "
    "no repaired candidate, runtime repair, visual pass, or promotion is claimed."
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
    marker = "## Wave64 Row023 Real Sequence Repair Routing"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-023` / `ITEM-W64-023` is `{STATUS}`. The real Row019/Row021 eight-frame sequence now has a hash-bound defect report and strict repair ledger: frames 5-7 carry `persistent_shot_instability`, frame 7 additionally carries `single_frame_identity_drift`, and the contiguous span correctly routes to `rerun_shot`. The local OpenCV executor supports only pure `isolated_flicker` and rejected this ledger with expected exit 2 without publishing an output directory. No repaired frames, generation, AWS, EC2, mask use/promotion, hard-gate rerun, Jira mutation, or Wave71+ activation occurred.

Next action: preserve this fail-closed rerun decision and continue `TRK-W64-024` / `ITEM-W64-024` GIF loop/export reconciliation without treating the failed sequence as promotable.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + text, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_frame_repair.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/video_frame_repair.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-023_video_frame_repair.json"
    test_log_path = PLAN / "Instructions/QA/Evidence/Wave64/video_frame_repair_test_log.json"
    base = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500"
    manifest_path = base / "wave27_frame_manifest.json"
    temporal_path = base / "wave27_temporal_review/wave27_temporal_evidence.json"
    verdict_path = base / "wave27_temporal_review/codex_visual_verdict.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_VISUAL_QA_20260713T023500-0500.json"
    defect_path = base / "wave27_frame_repair/row023_real_defect_report.json"
    ledger_path = base / "wave27_frame_repair/row023_real_repair_ledger.json"
    policy_path = PLAN / "10_REGISTRIES/wave27_frame_repair_policy.json"
    executor_registry_path = PLAN / "10_REGISTRIES/wave27_short_span_repair_executor.json"
    broad_worker_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T041421-0500_w64_row023_real_sequence_repair_compatibility/handoff_record.json"
    narrow_worker_path = ROOT / "runtime_artifacts/agent_handoffs/cursor/20260713T042447-0500_w64_row023_real_sequence_repair_compatibility_narrow/handoff_record.json"
    claude_review_path = ROOT / "runtime_artifacts/agent_handoffs/claude_subscription/20260713T043239-0500_w64_row023_semantic_final_review/handoff_record.json"
    stderr_path = ROOT / "runtime_artifacts/wave64_video_frame_repair/row023_real_executor_fail_closed_20260713T042629-0500.stderr.txt"
    required = [canonical_path, report_path, test_log_path, manifest_path, temporal_path, verdict_path, visual_path, defect_path, ledger_path, policy_path, executor_registry_path, broad_worker_path, narrow_worker_path, claude_review_path, stderr_path]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row023 inputs: {missing}")

    canonical = load(canonical_path)
    report = load(report_path)
    test_log = load(test_log_path)
    manifest = load(manifest_path)
    temporal = load(temporal_path)
    verdict = load(verdict_path)
    visual = load(visual_path)
    defects = load(defect_path)
    ledger = load(ledger_path)
    policy = load(policy_path)
    executor = load(executor_registry_path)
    broad_worker = load(broad_worker_path)
    narrow_worker = load(narrow_worker_path)
    claude_review = load(claude_review_path)
    defect_indexes = sorted({item["frame_index"] for item in defects["defects"]})
    ledger_indexes = [item["frame_index"] for item in ledger["failed_frames"]]
    span = ledger["repair_spans"][0]
    checks = {
        "canonical_row_exact": canonical["tracker_id"] == "TRK-W64-023" and canonical["item_id"] == "ITEM-W64-023",
        "report_row_exact": report["tracker_id"] == "TRK-W64-023" and report["item_id"] == "ITEM-W64-023",
        "manifest_sequence_bound": defects["manifest_sequence_sha256"] == manifest["sequence_sha256"],
        "temporal_evidence_hash_bound": defects["temporal_evidence_sha256"] == digest(temporal_path),
        "ledger_manifest_hash_bound": ledger["source_bindings"]["manifest_sha256"] == digest(manifest_path),
        "ledger_defect_hash_bound": ledger["source_bindings"]["defect_report_sha256"] == digest(defect_path),
        "ledger_temporal_hash_bound": ledger["source_bindings"]["temporal_evidence_sha256"] == digest(temporal_path),
        "visual_failed_indexes_exact": visual["failed_frame_indexes"] == [5, 6, 7],
        "defect_indexes_exact": defect_indexes == [5, 6, 7],
        "ledger_indexes_exact": ledger_indexes == [5, 6, 7],
        "persistent_instability_all_failed_frames": all(any(item["frame_index"] == index and item["failure"] == "persistent_shot_instability" for item in defects["defects"]) for index in [5, 6, 7]),
        "frame7_identity_drift_recorded": any(item["frame_index"] == 7 and item["failure"] == "single_frame_identity_drift" for item in defects["defects"]),
        "single_span_exact": len(ledger["repair_spans"]) == 1 and span["frame_indices"] == [5, 6, 7],
        "rerun_shot_route_exact": span["recommended_action"] == "rerun_shot" and span["reason"] == "persistent_shot_instability_escalation",
        "candidate_remains_absent": ledger["planning_status"] == "repair_plan_pending_candidate" and ledger["candidate_validation"]["candidate_manifest_provided"] is False,
        "executor_isolated_flicker_only": executor["supported_failure"] == "isolated_flicker",
        "ledger_not_executor_eligible": set(span["failures"]) != {executor["supported_failure"]},
        "executor_failed_closed": "executor supports isolated_flicker failures only" in stderr_path.read_text(encoding="utf-16"),
        "executor_output_absent": not (ROOT / "runtime_artifacts/wave64_video_frame_repair/row023_real_executor_fail_closed_20260713T042629-0500").exists(),
        "visual_verdict_failed": verdict["result"] == "fail",
        "temporal_promotion_blocked": temporal["promotion_decision"] == "block",
        "existing_tests_passed": test_log["tests_run"] == 29 and test_log["failures"] == 0 and test_log["errors"] == 0,
        "worker_attempts_recorded": broad_worker["classification"] == "CURSOR_HANDOFF_WRAPPER_FAILED" and narrow_worker["classification"] == "CURSOR_HANDOFF_INCOMPLETE_OUTPUT_CONTRACT",
        "claude_review_passed": claude_review["status"] == "PASS" and claude_review["classification"] == "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED",
        "claude_no_high_or_medium_findings": "No HIGH or MEDIUM findings remain" in claude_review["result_excerpt"],
        "candidate_masks_not_consumed": visual["boundaries"]["gold_masks_consumed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row023 reconciliation checks failed: {failed}")

    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_FRAME_REPAIR_REAL_SEQUENCE_ROUTING_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/VIDEO_FRAME_REPAIR_REAL_SEQUENCE_ROUTING_{STAMP}.json"
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-FRAME-REPAIR-REAL-SEQUENCE-ROUTING-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-023",
        "item_id": "ITEM-W64-023",
        "status_decision": STATUS,
        "inputs": [{"path": rel(path), "sha256": digest(path)} for path in [manifest_path, temporal_path, verdict_path, visual_path, defect_path, ledger_path, policy_path, executor_registry_path, stderr_path]],
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "validation": {
            "command": "python -m unittest Plan.Instructions.QA.Scripts.test_wave27_frame_repair_ledger_strict Plan.Instructions.QA.Scripts.test_execute_wave27_short_span_repair",
            "tests_passed": 29,
            "tests_failed": 0,
            "elapsed_seconds": 104.914,
            "python_compile": "pass",
        },
        "routing": {
            "failed_frame_indexes": [5, 6, 7],
            "span_failures": span["failures"],
            "recommended_action": span["recommended_action"],
            "reason": span["reason"],
            "isolated_flicker_executor_eligible": False,
            "executor_probe_exit_code": 2,
            "executor_probe_stderr": {"path": rel(stderr_path), "sha256": digest(stderr_path)},
            "executor_output_published": False,
        },
        "worker_fallback": {
            "broad_attempt": rel(broad_worker_path),
            "broad_result": "timeout",
            "narrow_attempt": rel(narrow_worker_path),
            "narrow_result": "incomplete_output_contract",
            "fallback_scope": "planner and executor taxonomy/routing blocks only",
        },
        "semantic_review": {"path": rel(claude_review_path), "sha256": digest(claude_review_path), "remaining_high_or_medium_findings": 0},
        "gate_results": {
            "real_defect_report_present": True,
            "real_repair_ledger_present": True,
            "real_failed_frames_hash_bound": True,
            "local_short_span_executor_eligible": False,
            "repaired_candidate_present": False,
            "before_after_visual_review": False,
            "runtime_repair_proof": False,
            "final_temporal_acceptance": False,
        },
        "boundaries": {"new_generation_executed": False, "aws_contacted": False, "ec2_started": False, "candidate_masks_consumed_as_truth": False, "mask_promotion_claimed": False, "wave70_hard_gate_rerun": False, "wave71_activation_claimed": False},
        "result": "blocked_real_sequence_requires_rerun_shot",
        "next_action": "Continue TRK-W64-024 / ITEM-W64-024 GIF loop/export reconciliation; preserve this failed sequence and do not treat it as promotable.",
    }
    dump(output_path, evidence)
    dump(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    canonical["acceptance_gates"].update({"real_defect_report_present": True, "real_repair_ledger_present": True, "real_repaired_candidate_frames_present": False, "before_after_frame_repair_review": False, "runtime_repair_proof": False, "final_temporal_acceptance": False, "final_promotion": False})
    canonical["real_sequence_routing"] = {"evidence": rel(output_path), "source_sequence_sha256": manifest["sequence_sha256"], "failed_frame_indexes": [5, 6, 7], "recommended_action": "rerun_shot", "isolated_flicker_executor_eligible": False, "executor_fail_closed_exit_code": 2, "executor_output_published": False}
    canonical["review"].update({"cursor_real_sequence_attempt": rel(broad_worker_path), "cursor_real_sequence_retry": rel(narrow_worker_path), "cursor_real_sequence_fallback": "compact_codex_taxonomy_mapping_after_timeout_and_incomplete_retry", "claude_real_sequence_routing_review": rel(claude_review_path), "remaining_high_or_medium_findings": 0})
    canonical["offline_validation"].update({"last_targeted_rerun": TIMESTAMP, "last_targeted_rerun_tests_passed": 29, "last_targeted_rerun_tests_failed": 0})
    canonical["runtime"].update({"repair_executed": False, "candidate_frames_generated": False, "comfyui_started": False, "generation_executed": False, "aws_contacted": False, "ec2_started": False})
    canonical["blockers"] = [{"classification": STATUS, "scope": "primary_row_blocker", "reason": "The real frames 5-7 span contains persistent shot instability and frame-7 identity drift, so policy requires rerunning the shot; the isolated-flicker executor is ineligible and failed closed."}, {"classification": "Blocked_Video_Frame_Repair_Visual_Proof_Missing", "scope": "before_after_and_preservation_review", "reason": "No truthful repaired candidate exists, so no before/after visual preservation review can run."}, {"classification": "Blocked_Gold_Mask_Dependency_Missing", "scope": "contact_and_deformation_repair_subgates_only", "reason": "Contact/deformation repair cannot use candidate masks as truth while manual body gold masks remain unavailable."}]
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update({"row_complete": False, "real_defect_localization_claimed": True, "real_repair_ledger_claimed": True, "repair_execution_claimed": False, "candidate_verification_claimed": False, "visual_preservation_claimed": False, "runtime_repair_claimed": False, "final_promotion_claimed": False, "wave71_activation_claimed": False})
    canonical["reconciliation_evidence"] = rel(output_path)
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update({"real_defect_report": "pass", "real_repair_ledger": "pass_expected_exit_2_pending_candidate", "real_failed_frame_indexes": [5, 6, 7], "real_route": "rerun_shot", "isolated_flicker_executor": "blocked_expected_exit_2_no_output", "targeted_test_rerun_passed": 29, "targeted_test_rerun_failed": 0, "claude_semantic_review": "PASS_NO_HIGH_OR_MEDIUM_FINDINGS"})
    report["acceptance_gates"].update({"real_defect_localization": True, "real_repair_ledger": True, "real_repaired_candidate": False, "before_after_visual_review": False, "runtime_repair_proof": False, "final_temporal_acceptance": False})
    report["blockers"] = canonical["blockers"]
    report["evidence"] = [{"path": rel(canonical_path), "sha256": digest(canonical_path)}, {"path": rel(test_log_path), "sha256": digest(test_log_path)}, {"path": rel(output_path), "sha256": digest(output_path)}]
    report["runtime"].update({"repair_execution_count": 0, "candidate_frame_count": 0, "visual_review_count": 0, "comfyui_started": False, "aws_contacted": False, "ec2_started": False})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-023")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-023")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))
    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "routing": evidence["routing"], "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
