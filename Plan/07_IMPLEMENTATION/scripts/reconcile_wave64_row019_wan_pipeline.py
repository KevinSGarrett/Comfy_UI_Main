#!/usr/bin/env python3
"""Reconcile bounded WAN proof into Row019 without claiming full certification."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path("C:/Comfy_UI_Main")
TRK = "TRK-W64-019"
ITEM = "ITEM-W64-019"
STATUS = "Blocked_Keyframe_Repair_Loop_And_Production_Sequence_Proof_Missing"
DECISION = "wan_primary_bounded_runtime_technical_visual_pass_remaining_video_pipeline_gates_fail_closed"
CANONICAL = Path("Plan/Instructions/QA/Evidence/Wave64/video_pipeline_build.json")
SOURCES = {
    "prior": Path("Plan/Instructions/QA/Evidence/Wave64/VIDEO_PIPELINE_BUILD_RUNTIME_RECONCILIATION_20260713T024108-0500.json"),
    "runtime": Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_TI2V5B_TARGET_RUNTIME_SMOKE_20260714T004424-0500.json"),
    "technical": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_TECHNICAL_QA_20260714T004424-0500.json"),
    "visual": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_VISUAL_QA_20260714T004424-0500.json"),
    "repair": Path("Plan/Instructions/QA/Evidence/Wave64/VIDEO_FRAME_REPAIR_REAL_SEQUENCE_ROUTING_20260713T042629-0500.json"),
    "loop": Path("Plan/Instructions/QA/Evidence/Wave64/VIDEO_GIF_LOOP_EXPORT_REAL_RUNTIME_20260713T044336-0500.json"),
    "portfolio": Path("Plan/10_REGISTRIES/comfyui_delivery_portfolio_registry.json"),
}
NOTE = (
    "Wave64 Row019 WAN reconciliation: one hash-bound 49-frame primary clip passed target runtime, technical QA, "
    "and bounded direct temporal review. Keyframe manifest integration, effective repair, clean loop export, and "
    "production-sequence review remain fail-closed, and the failed AnimateDiff fallback remains historical evidence."
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(label)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def bind(path: Path, root: Path) -> dict[str, Any]:
    before = path.stat()
    result = {"path": rel(path, root), "sha256": sha(path), "bytes": before.st_size}
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f"source changed while hashing: {path}")
    return result


def append_many(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def normalize_note(current: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip() and not entry.strip().startswith("Wave64 Row019 WAN reconciliation:")]
    entries.append(NOTE)
    return "; ".join(entries)


def replace_coverage(current: str) -> str:
    stale = {"video_visual_temporal_quality_failure", "animatediff_visual_temporal_failure_active"}
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip() and entry.strip() not in stale]
    for value in ("wan_primary_bounded_runtime_pass", "wan_49_frame_technical_pass", "wan_bounded_direct_temporal_review_pass", "video_pipeline_remaining_gates_fail_closed"):
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def build(root: Path, source_paths: dict[str, Path], timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    paths = {name: (path if path.is_absolute() else root / path).resolve() for name, path in source_paths.items()}
    data = {name: load(path) for name, path in paths.items()}
    prior, runtime, technical, visual = data["prior"], data["runtime"], data["technical"], data["visual"]
    repair, loop, portfolio = data["repair"], data["loop"], data["portfolio"]

    require(prior.get("tracker_id") == TRK and prior.get("item_id") == ITEM, "prior Row019 identity mismatch")
    prior_gates = prior.get("acceptance_gates", {})
    require(prior_gates.get("video_workflow_valid") is True, "prior workflow gate missing")
    require(prior_gates.get("frame_sequence_manifest") is True, "prior frame manifest gate missing")
    require(prior_gates.get("keyframe_manifest") is False, "prior keyframe blocker missing")
    require(prior_gates.get("loop_export_gate") is False, "prior loop blocker missing")
    require(prior_gates.get("frame_repair_effectiveness") is False, "prior repair blocker missing")
    require(prior.get("latest_runtime_attempt", {}).get("visual_temporal_pass") is False, "failed AnimateDiff attempt missing")

    lane = "wan_2_2_ti2v_5b_primary_lane"
    run_id = "aws_gpu_workflow_smoke_20260714T002123-0500"
    require(runtime.get("lane_id") == lane and runtime.get("run_id") == run_id, "WAN runtime identity mismatch")
    rr = runtime.get("runtime_result", {})
    require(runtime.get("result") == "pass_bounded_wan22_ti2v5b_target_runtime_smoke", "WAN runtime did not pass")
    require(rr.get("generation_executed") is True and not rr.get("errors"), "WAN generation proof invalid")
    require(rr.get("pullback_hashes_verified") is True, "WAN pullback hash proof missing")
    require(runtime.get("execution_target", {}).get("final_instance_state") == "stopped", "EC2 final state is not stopped")
    require(runtime.get("boundaries", {}).get("production_video_lane_certification_claimed") is False, "WAN runtime overclaims certification")

    require(technical.get("lane_id") == lane and technical.get("run_id") == run_id, "WAN technical identity mismatch")
    decode = technical.get("decode", {})
    require(technical.get("technical_pass") is True, "WAN technical QA did not pass")
    require(decode.get("frame_count") == 49 and decode.get("unique_decoded_frame_count") == 49, "WAN 49-frame proof missing")
    require(decode.get("all_frames_extracted") is True and decode.get("decode_exit_code") == 0, "WAN frame extraction failed")
    require(technical.get("artifact", {}).get("sha256") == runtime.get("artifact", {}).get("sha256"), "WAN artifact hash mismatch")
    technical_boundaries = technical.get("boundaries", {})
    require(technical_boundaries.get("single_clip_only") is True, "WAN technical scope is not single-clip")
    require(technical_boundaries.get("production_video_lane_certification_claimed") is False, "WAN technical evidence overclaims certification")

    require(visual.get("lane_id") == lane and visual.get("run_id") == run_id, "WAN visual identity mismatch")
    require(visual.get("visual_pass") is True, "WAN bounded visual QA did not pass")
    require(len(visual.get("reviewed_frames", [])) == 9 and visual.get("reviewed_frames", [])[-1] == 49, "WAN sampled-frame review scope missing")
    require(visual.get("result") == "pass_bounded_single_clip_direct_temporal_review", "WAN visual result is not bounded pass")
    visual_boundaries = visual.get("boundaries", {})
    require(visual_boundaries.get("single_seed_single_source_single_profile") is True, "WAN visual scope is not bounded to one configuration")
    require(visual_boundaries.get("production_video_lane_certification_claimed") is False, "WAN visual evidence overclaims certification")
    require(visual_boundaries.get("long_duration_quality_claimed") is False, "WAN visual evidence overclaims duration quality")
    require(visual_boundaries.get("multiseed_robustness_claimed") is False, "WAN visual evidence overclaims multiseed robustness")

    repair_gates = repair.get("gate_results", {})
    require(repair.get("tracker_id") == "TRK-W64-023", "repair evidence identity mismatch")
    require(repair_gates.get("repaired_candidate_present") is False and repair_gates.get("frame_repair_effectiveness", False) is False, "repair unexpectedly proven")
    require(repair_gates.get("final_temporal_acceptance") is False, "repair final acceptance unexpectedly true")
    loop_gates = loop.get("gate_results", {})
    require(loop.get("tracker_id") == "TRK-W64-024", "loop evidence identity mismatch")
    require(loop_gates.get("technical_export_pass") is True, "loop technical export proof missing")
    require(loop_gates.get("loop_playback_visual_pass") is False and loop_gates.get("final_export_certification") is False, "loop visual failure missing")

    portfolio_row = next((row for row in portfolio.get("lanes", []) if row.get("lane_id") == "wan_2_2_primary_candidate"), None)
    require(bool(portfolio_row), "WAN portfolio row missing")
    require(portfolio_row.get("state") == "bounded_target_runtime_smoke_complete", "WAN portfolio state mismatch")
    require(portfolio_row.get("production_lane_certified") is False, "portfolio overclaims WAN certification")

    gates = {
        "video_workflow_valid": True,
        "keyframe_manifest": False,
        "frame_sequence_manifest": True,
        "loop_export_gate": False,
        "artifact_evidence": True,
        "frame_repair_effectiveness": False,
        "strict_frame_sequence_visual_review": False,
        "bounded_primary_clip_runtime": True,
        "bounded_primary_clip_technical_qa": True,
        "bounded_primary_clip_direct_temporal_review": True,
    }
    checks = {
        "VPB-R01_prior_row019_contract_preserved": True,
        "VPB-R02_wan_target_runtime_pass": rr.get("generation_executed") is True,
        "VPB-R03_wan_artifact_hash_bound": technical["artifact"]["sha256"] == runtime["artifact"]["sha256"],
        "VPB-R04_wan_49_unique_frames_decoded": decode["unique_decoded_frame_count"] == 49,
        "VPB-R05_wan_technical_qa_pass": technical["technical_pass"] is True,
        "VPB-R06_wan_bounded_direct_temporal_review_pass": visual["visual_pass"] is True,
        "VPB-R07_production_certification_not_claimed": portfolio_row["production_lane_certified"] is False,
        "VPB-R07A_technical_certification_not_claimed": technical_boundaries["production_video_lane_certification_claimed"] is False,
        "VPB-R07B_visual_certification_duration_and_robustness_not_claimed": not any((visual_boundaries["production_video_lane_certification_claimed"], visual_boundaries["long_duration_quality_claimed"], visual_boundaries["multiseed_robustness_claimed"])),
        "VPB-R08_keyframe_manifest_remains_blocked": gates["keyframe_manifest"] is False,
        "VPB-R09_repair_effectiveness_remains_blocked": gates["frame_repair_effectiveness"] is False,
        "VPB-R10_loop_export_remains_blocked": gates["loop_export_gate"] is False,
        "VPB-R11_production_sequence_review_remains_blocked": gates["strict_frame_sequence_visual_review"] is False,
        "VPB-R12_failed_animatediff_fallback_preserved": prior["latest_runtime_attempt"]["visual_temporal_pass"] is False,
        "VPB-R13_instance_stopped": runtime["execution_target"]["final_instance_state"] == "stopped",
        "VPB-R14_no_generation_or_cloud_action_in_reconciliation": True,
    }
    require(all(checks.values()), "Row019 reconciliation checks failed")

    blockers = [
        {"blocker_id": "KEYFRAME_MANIFEST_INTEGRATION_MISSING", "resolution": "Bind a real shot/keyframe manifest to a selected production sequence."},
        {"blocker_id": "FRAME_REPAIR_EFFECTIVENESS_NOT_PROVEN", "resolution": "Produce and directly compare a repaired candidate for a real failed span."},
        {"blocker_id": "FINAL_LOOP_EXPORT_VISUAL_QA_FAILED", "resolution": "Produce a loop candidate without the recorded frames 5-7 popping and corruption."},
        {"blocker_id": "PRODUCTION_SEQUENCE_REVIEW_NOT_PROVEN", "resolution": "Run scope-matched multi-clip production review; do not generalize one bounded WAN clip."},
        {"blocker_id": "CONTACT_SOFT_BODY_VIDEO_SCOPE_BLOCKED_GOLD_MASKS", "resolution": "Keep contact and soft-body claims blocked until trusted body/contact masks are available."},
    ]
    bindings = {name: bind(path, root) for name, path in paths.items()}
    return {
        "schema_version": "1.1",
        "evidence_id": "",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": False,
        "status_decision": DECISION,
        "acceptance_gates": gates,
        "primary_runtime_attempt": {
            "lane_id": lane,
            "run_id": run_id,
            "runtime_pass": True,
            "technical_pass": True,
            "bounded_direct_temporal_review_pass": True,
            "frame_count": 49,
            "artifact": runtime["artifact"],
            "production_lane_certified": False,
        },
        "historical_fallback_attempt": deepcopy(prior["latest_runtime_attempt"]),
        "repair_state": {"status_decision": repair.get("status_decision"), "gate_results": repair_gates},
        "loop_export_state": {"status_decision": loop.get("status_decision"), "gate_results": loop_gates, "failed_frame_indexes": loop.get("failed_frame_indexes")},
        "normalized_blockers": blockers,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "source_bindings": bindings,
        "safety_boundary": {"generation_executed_in_reconciliation": False, "aws_contacted_in_reconciliation": False, "ec2_started": False, "mask_or_wave71_or_jira_touched": False, "full_video_certification_claimed": False},
        "next_action": "Implement a real keyframe manifest and select one changed production sequence that can exercise repair and loop acceptance without repeating the completed WAN smoke.",
    }


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_csv(path: Path, key: str, expected: str, changes: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle); fields = reader.fieldnames or []; rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = value
    require(matched == 1, f"ledger row mismatch: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    timestamp = args.timestamp or datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
    stamp = datetime.fromisoformat(timestamp).strftime("%Y%m%dT%H%M%S%z")
    payload = build(root, SOURCES, timestamp)
    canonical = root / CANONICAL
    stamped = canonical.parent / f"VIDEO_PIPELINE_BUILD_WAN_RECONCILIATION_{stamp}.json"
    mirror = root / "Plan/Tracker/Evidence" / stamped.name
    log = canonical.parent / "video_pipeline_build_test_log.json"
    report = root / "Plan/Items/Reports/ITEM-W64-019_video_pipeline_build.json"
    paths = [rel(path, root) for path in (canonical, stamped, mirror, log, report)]
    payload["evidence_id"] = stamped.stem
    payload["evidence_paths"] = paths
    for path in (canonical, stamped, mirror): write(path, payload)
    write(log, {"schema_version": "1.0", "timestamp": timestamp, "tracker_id": TRK, "result": "pass_bounded_wan_row019_reconciliation", "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.1", "timestamp": timestamp, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "row_complete": False, "acceptance_gates": payload["acceptance_gates"], "normalized_blockers": payload["normalized_blockers"], "evidence": paths, "next_action": payload["next_action"]})
    if not args.no_ledger:
        for path in (root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv", root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Tracker_ID") == TRK)
            update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": append_many(row.get("Evidence_Path", ""), paths), "Coverage_Audit_Status": replace_coverage(row.get("Coverage_Audit_Status", "")), "Notes": normalize_note(row.get("Notes", ""))})
        for path in (root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv", root / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Item_ID") == ITEM)
            update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": append_many(row.get("Evidence_Required", ""), paths), "Coverage_Audit_Status": replace_coverage(row.get("Coverage_Audit_Status", "")), "Notes": normalize_note(row.get("Notes", ""))})
    print(json.dumps({"status": STATUS, "checks": payload["check_summary"], "gates": payload["acceptance_gates"], "evidence": paths}, indent=2))


if __name__ == "__main__": main()
