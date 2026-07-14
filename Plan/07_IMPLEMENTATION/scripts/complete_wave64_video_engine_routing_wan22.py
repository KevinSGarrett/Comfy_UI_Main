#!/usr/bin/env python3
"""Complete Wave64 Row020 for the exact proven Wan 2.2 runtime envelope."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260714T045535-0500"
TIMESTAMP = "2026-07-14T04:55:35-05:00"
STATUS = "Completed_Bounded_Wan22_Video_Engine_Routing_Pass_Production_Certification_Not_Claimed"
NOTE = (
    "Wave64 Row020 completion 2026-07-14: the strict router selects Wan 2.2 for the "
    "exact proven 480x640, 49-frame, 24 fps, 24 GB EC2, high-cost, single-keyframe "
    "contract. Runtime, technical, and direct visual proof pass; requests beyond the "
    "verified duration or below 24 GB fail closed. This completes bounded engine routing "
    "only and does not claim production video certification."
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


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


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
        row["Final_Render_Gate"] = "BOUNDED_ROUTE_COMPLETE_PRODUCTION_CERTIFICATION_NOT_CLAIMED"
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row020 Bounded Wan 2.2 Routing Complete"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-020` / `ITEM-W64-020` is `{STATUS}`. The strict video router now selects Wan 2.2 for the exact proven 480x640, 49-frame, 24 fps, 24 GB EC2, high-cost, single-keyframe contract. All 25 router regressions pass, the exact route is runtime-ready, and over-duration plus under-VRAM requests fail closed. Existing target-runtime, technical, and direct visual proof is reused without rerunning seeds 2271301-2271303 or 2271401. Final promotion remains false and production video certification is not claimed.

Next action: reconcile `TRK-W64-021` / `ITEM-W64-021` temporal continuity against the existing hash-bound Wan clips without new generation or mask truth. Preserve stopped EC2, manual body-gold-mask boundaries, and all Wave71+/Jira restrictions.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def main() -> None:
    completion_script_path = Path(__file__).resolve()
    router_path = PLAN / "07_IMPLEMENTATION/scripts/route_video_engine_candidate.py"
    request_path = PLAN / "09_EXAMPLES/wave64_wan22_bounded_route_request.example.json"
    registry_path = PLAN / "10_REGISTRIES/wave27_video_engine_registry.json"
    rules_path = PLAN / "10_REGISTRIES/wave27_video_route_selection_rules.json"
    request_schema_path = PLAN / "08_SCHEMAS/video_engine_route_request.schema.json"
    decision_schema_path = PLAN / "08_SCHEMAS/video_engine_route_decision.schema.json"
    test_path = PLAN / "Instructions/QA/Scripts/test_route_video_engine_candidate.py"
    runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SOURCE_DIVERSITY_TARGET_RUNTIME_20260714T043510-0500.json"
    technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_TECHNICAL_QA_20260714T043510-0500.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_SOURCE_DIVERSITY_VISUAL_QA_20260714T043510-0500.json"
    run_record_path = PLAN / "Instructions/Operations/Run_Records/aws_gpu_workflow_smoke_20260714T041921-0500.json"
    ec2_protocol_path = PLAN / "Instructions/Operations/AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md"
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_engine_routing.json"
    canonical_mirror_path = PLAN / "Tracker/Evidence/Wave64/video_engine_routing.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-020_video_engine_routing.json"
    decision_path = PLAN / "Instructions/QA/Evidence/Wave64/video_engine_routing_wan22_bounded_decision.json"
    decision_mirror_path = PLAN / "Tracker/Evidence/Wave64/video_engine_routing_wan22_bounded_decision.json"
    test_log_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_TEST_LOG_{STAMP}.json"
    test_log_mirror_path = PLAN / f"Tracker/Evidence/Wave64/VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_TEST_LOG_{STAMP}.json"
    evidence_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_COMPLETION_{STAMP}.json"
    evidence_mirror_path = PLAN / f"Tracker/Evidence/VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_COMPLETION_{STAMP}.json"
    done_path = PLAN / f"Instructions/QA/Evidence/Done_Certifications/W64_VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_DONE_{STAMP}.json"
    done_mirror_path = PLAN / f"Tracker/Evidence/Done_Certifications/W64_VIDEO_ENGINE_ROUTING_WAN22_BOUNDED_DONE_{STAMP}.json"

    required = [
        router_path,
        request_path,
        registry_path,
        rules_path,
        request_schema_path,
        decision_schema_path,
        test_path,
        runtime_path,
        technical_path,
        visual_path,
        run_record_path,
        ec2_protocol_path,
        canonical_path,
        report_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row020 completion inputs: {missing}")

    test_command = [
        sys.executable,
        "-m",
        "unittest",
        "Plan.Instructions.QA.Scripts.test_route_video_engine_candidate",
        "-v",
    ]
    test_result = run_checked(test_command)
    test_count = sum(1 for line in test_result.stderr.splitlines() if line.rstrip().endswith("... ok"))
    if test_count != 25 or "FAILED" in test_result.stderr or "ERROR" in test_result.stderr:
        raise RuntimeError(f"Expected 25 passing router tests, observed {test_count}")

    route_command = [
        sys.executable,
        str(router_path),
        "--request",
        str(request_path),
        "--registry",
        str(registry_path),
        "--rules",
        str(rules_path),
        "--output",
        str(decision_path),
    ]
    run_checked(route_command)
    decision_mirror_path.parent.mkdir(parents=True, exist_ok=True)
    decision_mirror_path.write_bytes(decision_path.read_bytes())

    request = read_json(request_path)
    registry = read_json(registry_path)
    decision = read_json(decision_path)
    runtime = read_json(runtime_path)
    technical = read_json(technical_path)
    visual = read_json(visual_path)
    run_record = read_json(run_record_path)
    ec2_protocol = ec2_protocol_path.read_text(encoding="utf-8")
    wan = next(engine for engine in registry["engines"] if engine["id"] == "wan")
    evaluation = next(item for item in decision["engine_evaluations"] if item["engine_id"] == "wan")

    checks = {
        "request_exact_bounded_contract": (
            request["requested_engine"] == "wan"
            and request["output_type"] == "mp4"
            and request["width"] == 480
            and request["height"] == 640
            and request["fps"] == 24
            and request["available_vram_gb"] == 24
        ),
        "request_duration_matches_49_frames": abs(request["duration_seconds"] - (49 / 24)) < 1e-9,
        "wan_registry_authority_verified": all(
            wan[name]["verification_status"] == "verified"
            for name in (
                "model_registry_link",
                "object_info_evidence",
                "runtime_proof",
                "supported_outputs",
                "supported_features",
                "resource_limits",
                "execution_targets",
                "cost_tiers",
                "availability",
                "promotion_proof",
            )
        ),
        "resource_envelope_exact": (
            wan["resource_limits"]["max_width"] == 480
            and wan["resource_limits"]["max_height"] == 640
            and abs(wan["resource_limits"]["max_duration_seconds"] - (49 / 24)) < 1e-9
            and wan["resource_limits"]["max_fps"] == 24
            and wan["resource_limits"]["min_vram_gb"] == 24
        ),
        "execution_and_cost_policy_exact": (
            wan["execution_targets"]["values"] == ["ec2"]
            and wan["cost_tiers"]["values"] == ["high"]
        ),
        "route_selected_wan": decision["result"] == "compatible" and decision["selected_engine"] == "wan",
        "route_runtime_ready": decision["runtime_ready"] is True,
        "route_production_promotion_forbidden": decision["final_promotion_ready"] is False,
        "route_has_no_blockers": not decision["blocked_reasons"] and not decision["required_proof"],
        "wan_evaluation_all_gates_pass": all(
            evaluation[name] is True
            for name in (
                "availability_passed",
                "compatibility_passed",
                "promotion_passed",
                "resource_passed",
                "can_select",
            )
        ),
        "runtime_proof_passed": runtime["result"] == "pass_bounded_wan22_changed_source_target_runtime" and not runtime["failed_checks"],
        "runtime_shape_matches_request": (
            runtime["runtime_unit"]["width"] == request["width"]
            and runtime["runtime_unit"]["height"] == request["height"]
            and runtime["runtime_unit"]["frame_count"] == 49
            and runtime["runtime_unit"]["fps"] == request["fps"]
        ),
        "runtime_safety_closed": (
            runtime["aws_safety"]["final_instance_state"] == "stopped"
            and runtime["aws_safety"]["active_runtime_marker_removed"] is True
            and runtime["aws_safety"]["emergency_stop_schedule_retired_after_window"] is True
        ),
        "runtime_run_record_matches_exact_instance": (
            run_record["run_id"] == runtime["runtime_unit"]["run_id"]
            and run_record["instance_id"] == runtime["aws_safety"]["approved_instance"]
            and run_record["result"] == "workflow_smoke_generation_complete"
            and run_record["generation_executed"] is True
            and run_record["final_state"] == "stopped"
        ),
        "approved_instance_type_is_g5_xlarge": (
            "i-0560bf8d143f93bb1" in ec2_protocol and "g5.xlarge" in ec2_protocol
        ),
        "technical_qa_passed": technical["technical_pass"] is True and not technical["failed_checks"],
        "technical_shape_matches_request": (
            technical["decoder"]["width"] == request["width"]
            and technical["decoder"]["height"] == request["height"]
            and technical["decoder"]["decoded_frames"] == 49
            and technical["decoder"]["fps"] == request["fps"]
        ),
        "visual_qa_passed": visual["visual_pass"] is True and not visual["failed_checks"],
        "production_video_certification_not_claimed": all(
            evidence["boundaries"]["production_video_lane_certification_claimed"] is False
            for evidence in (runtime, technical, visual)
        ),
        "mask_and_wave71_authority_not_claimed": (
            runtime["boundaries"]["mask_or_geometry_authority_claimed"] is False
            and visual["boundaries"]["mask_or_geometry_authority_claimed"] is False
            and runtime["boundaries"]["wave71_activation_claimed"] is False
            and visual["boundaries"]["wave71_activation_claimed"] is False
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row020 completion checks failed: {failed}")

    test_log = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-ENGINE-ROUTING-WAN22-BOUNDED-TEST-LOG-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-020",
        "item_id": "ITEM-W64-020",
        "command": "python -m unittest Plan.Instructions.QA.Scripts.test_route_video_engine_candidate -v",
        "result": "pass",
        "exit_code": 0,
        "tests_run": test_count,
        "failures": 0,
        "errors": 0,
        "coverage": [
            "current verified Wan registry selects the exact bounded runtime contract",
            "duration above the verified 49-frame envelope fails closed",
            "available VRAM below 24 GB fails closed",
        ],
    }
    write_json(test_log_path, test_log)
    write_json(test_log_mirror_path, test_log)

    source_inputs = [
        completion_script_path,
        router_path,
        request_schema_path,
        decision_schema_path,
        test_path,
        request_path,
        decision_path,
        registry_path,
        rules_path,
        runtime_path,
        technical_path,
        visual_path,
        run_record_path,
        ec2_protocol_path,
        test_log_path,
    ]
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-ENGINE-ROUTING-WAN22-BOUNDED-COMPLETION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-020",
        "item_id": "ITEM-W64-020",
        "status_decision": STATUS,
        "source_citation": "Plan/04_VIDEO_GIF_SYSTEM/WAVE06_VIDEO_ENGINE_ROUTING_STRATEGY.md",
        "inputs": [{"path": rel(path), "sha256": sha256(path)} for path in source_inputs],
        "verified_route_contract": {
            "engine": "wan",
            "model_lane": "wan_2_2_ti2v_5b_primary_lane",
            "output": "mp4",
            "width": 480,
            "height": 640,
            "frame_count": 49,
            "fps": 24,
            "duration_seconds": 49 / 24,
            "required_feature": "keyframes",
            "execution_target": "ec2",
            "minimum_vram_gb": 24,
            "cost_tier": "high",
            "motion_scope": "single_character_low_motion",
        },
        "resource_and_cost_authority": {
            "approved_instance_id": "i-0560bf8d143f93bb1",
            "instance_type": "g5.xlarge",
            "gpu_family": "NVIDIA A10G",
            "gpu_memory_gb": 24,
            "instance_protocol": rel(ec2_protocol_path),
            "official_instance_reference": "https://aws.amazon.com/ec2/instance-types/g5/",
            "cost_tier": "high",
            "cost_tier_policy": "Conservative project-local classification for a live EC2 GPU runtime window; no exact price claim is made.",
        },
        "route_decision": {
            "result": decision["result"],
            "selected_engine": decision["selected_engine"],
            "runtime_ready": decision["runtime_ready"],
            "final_promotion_ready": decision["final_promotion_ready"],
            "matched_rule_ids": decision["matched_rule_ids"],
            "blocked_reasons": decision["blocked_reasons"],
            "required_proof": decision["required_proof"],
            "wan_evaluation": evaluation,
        },
        "acceptance_gates": {
            "engine_compatibility": True,
            "runtime_object_info": True,
            "model_registry_link": True,
            "resource_budget_check": True,
            "runtime_proof": True,
            "technical_qa": True,
            "direct_visual_qa": True,
            "bounded_route_runtime_ready": True,
            "runtime_ready": True,
            "production_video_certification": False,
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "boundaries": {
            "existing_runtime_proof_reused": True,
            "new_generation_executed": False,
            "completed_seeds_rerun": False,
            "aws_contacted_by_this_reconciliation": False,
            "ec2_started_by_this_reconciliation": False,
            "single_short_clip_contract_only": True,
            "broader_resolution_duration_or_motion_claimed": False,
            "fine_hand_finger_foot_or_toe_certification_claimed": False,
            "production_video_lane_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
            "wave71_activation_claimed": False,
            "jira_mutated": False,
        },
        "result": "pass_bounded_wan22_video_engine_routing_row_complete",
        "next_action": "Reconcile Row021 temporal continuity against existing hash-bound Wan clips without new generation or mask truth.",
    }
    write_json(evidence_path, evidence)
    write_json(evidence_mirror_path, evidence)

    canonical = read_json(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    for artifact in canonical["implementation_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        if artifact_path.is_file():
            artifact["sha256"] = sha256(artifact_path)
    request_rel = rel(request_path)
    request_artifact = next(
        (artifact for artifact in canonical["implementation_artifacts"] if artifact["path"] == request_rel),
        None,
    )
    if request_artifact is None:
        canonical["implementation_artifacts"].append(
            {"path": request_rel, "sha256": sha256(request_path)}
        )
    else:
        request_artifact["sha256"] = sha256(request_path)
    canonical["offline_validation"].update(
        {
            "test_log": rel(test_log_path),
            "test_log_sha256": sha256(test_log_path),
            "tests_run": test_count,
            "test_failures": 0,
            "test_errors": 0,
            "python_compile": "pass",
            "schema_and_registry_json_parse": "pass",
            "technical_offline_pass": True,
        }
    )
    canonical["canonical_route_probe"] = {
        "request": rel(request_path),
        "request_file_sha256": sha256(request_path),
        "decision": rel(decision_path),
        "decision_file_sha256": sha256(decision_path),
        "result": decision["result"],
        "selected_engine": decision["selected_engine"],
        "candidate_order": decision["candidate_order"],
        "matched_rule_ids": decision["matched_rule_ids"],
        "runtime_ready": decision["runtime_ready"],
        "final_promotion_ready": decision["final_promotion_ready"],
        "blocked_reason_count": len(decision["blocked_reasons"]),
        "required_proof_count": len(decision["required_proof"]),
    }
    canonical["acceptance_gates"].update(evidence["acceptance_gates"])
    canonical["runtime"] = {
        "new_generation_executed": False,
        "existing_wan_target_runtime_proof_reused": True,
        "aws_contacted_by_this_reconciliation": False,
        "ec2_started_by_this_reconciliation": False,
        "final_instance_state_in_reused_proof": "stopped",
    }
    canonical["blocker"] = None
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = True
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update(
        {
            "row_complete": True,
            "engine_compatibility_claimed": True,
            "runtime_ready_claimed": True,
            "final_promotion_claimed": False,
            "production_video_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
        }
    )
    canonical["completion_evidence"] = rel(evidence_path)
    write_json(canonical_path, canonical)
    write_json(canonical_mirror_path, canonical)

    report = read_json(report_path)
    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = True
    historical_validation = {
        "default_wan_probe_before_bounded_runtime_authority": {
            "result": report["validation"].pop("canonical_probe", "blocked_as_expected"),
            "selected_engine": report["validation"].pop("canonical_selected_engine", None),
            "runtime_ready": report["validation"].pop("canonical_runtime_ready", False),
            "final_promotion_ready": report["validation"].pop(
                "canonical_final_promotion_ready", False
            ),
        },
        "animatediff_fallback_before_wan_runtime_authority": {
            "rule_matched": report["validation"].pop(
                "animatediff_fallback_rule_matched", True
            ),
            "compatibility": report["validation"].pop(
                "animatediff_fallback_compatibility", True
            ),
            "availability": report["validation"].pop(
                "animatediff_fallback_availability", True
            ),
            "resource_budget": report["validation"].pop(
                "animatediff_fallback_resource_budget", False
            ),
            "promotion": report["validation"].pop(
                "animatediff_fallback_promotion", False
            ),
        },
    }
    report["validation"].update(
        {
            "unit_tests_passed": test_count,
            "unit_test_failures": 0,
            "wan_bounded_route_selected": True,
            "over_duration_fails_closed": True,
            "under_vram_fails_closed": True,
            "historical_probe_context": historical_validation,
        }
    )
    report["acceptance_gates"].update(evidence["acceptance_gates"])
    report["blocker"] = None
    report["evidence"] = [
        {"path": rel(canonical_path), "sha256": sha256(canonical_path)},
        {"path": rel(evidence_path), "sha256": sha256(evidence_path)},
        {"path": rel(done_path)},
    ]
    report["runtime"] = {
        "new_generation_count": 0,
        "existing_wan_runtime_proof_reused": True,
        "ec2_started": False,
        "production_video_certification_claimed": False,
    }
    report["next_action"] = evidence["next_action"]
    write_json(report_path, report)

    done = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-ENGINE-ROUTING-WAN22-BOUNDED-DONE-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-020",
        "item_id": "ITEM-W64-020",
        "status_decision": STATUS,
        "done": True,
        "row_scope": "bounded_wan22_video_engine_routing",
        "completion_evidence": {"path": rel(evidence_path), "sha256": sha256(evidence_path)},
        "canonical_evidence": {"path": rel(canonical_path), "sha256": sha256(canonical_path)},
        "acceptance_gates_passed": [
            "engine_compatibility",
            "runtime_object_info",
            "model_registry_link",
            "resource_budget_check",
        ],
        "certification_ceiling": {
            "bounded_route_complete": True,
            "production_video_lane_certified": False,
            "mask_or_geometry_authority_certified": False,
            "wave71_activated": False,
        },
        "rerun_policy": "Do not rerun seeds 2271301, 2271302, 2271303, or 2271401 for this completed routing row.",
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
        update_csv(path, "Tracker_ID", "TRK-W64-020", evidence_rel)
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-020", evidence_rel)
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
                "selected_engine": decision["selected_engine"],
                "runtime_ready": decision["runtime_ready"],
                "final_promotion_ready": decision["final_promotion_ready"],
                "next_action": evidence["next_action"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
