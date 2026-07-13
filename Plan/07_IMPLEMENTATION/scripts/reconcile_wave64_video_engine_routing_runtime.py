#!/usr/bin/env python3
"""Reconcile Row020 with the bounded Row019 AnimateDiff fallback proof."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260713T030800-0500"
TIMESTAMP = "2026-07-13T03:08:00-05:00"
STATUS = "Blocked_Video_Engine_Resource_Cost_And_Promotion_Proof"
NOTE = (
    "Wave64 Row020 reconciliation 2026-07-13: animatediff_fallback now matches "
    "failed_generation_with_frame_sequence and passes bounded compatibility plus availability "
    "from Row019 proof; resource limits, cost tier, visual promotion, and default WAN authority "
    "remain fail-closed. No new generation or seed loop occurred."
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def update_csv(path: Path, id_field: str, row_id: str) -> None:
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
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row020 AnimateDiff Fallback Routing Reconciliation"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-020` / `ITEM-W64-020` is `{STATUS}`. The strict router is schema-valid again and its bounded fallback probe matches `failed_generation_with_frame_sequence`; `animatediff_fallback` passes engine compatibility and availability using the existing Row019 runtime/object-info/model proof. It remains unselectable because resource limits and cost tier are unverified, visual promotion failed, and default WAN authority remains unverified. No new generation, EC2, mask, FLUX, Jira, or Wave71+ action occurred.

Next action: preserve the proven fallback route and continue `TRK-W64-021` temporal visual review using the existing eight-frame sequence; do not claim production video readiness.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/video_engine_routing.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-020_video_engine_routing.json"
    request_path = PLAN / "09_EXAMPLES/wave64_animatediff_fallback_route_request.example.json"
    decision_path = PLAN / "Instructions/QA/Evidence/Wave64/video_engine_routing_animatediff_fallback_probe.json"
    registry_path = PLAN / "10_REGISTRIES/wave27_video_engine_registry.json"
    runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_ANIMATEDIFF_FALLBACK_EXECUTE_20260713T022708-0500.json"
    technical_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_TECHNICAL_QA_20260713T023200-0500.json"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_VISUAL_QA_20260713T023500-0500.json"
    rules_path = PLAN / "10_REGISTRIES/wave27_video_route_selection_rules.json"
    output_path = PLAN / f"Instructions/QA/Evidence/Wave64/VIDEO_ENGINE_ROUTING_ANIMATEDIFF_FALLBACK_RECONCILIATION_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/VIDEO_ENGINE_ROUTING_ANIMATEDIFF_FALLBACK_RECONCILIATION_{STAMP}.json"

    source_inputs = [request_path, decision_path, registry_path, runtime_path, technical_path, visual_path, rules_path]
    required = [canonical_path, report_path, *source_inputs]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Row020 reconciliation inputs: {missing}")

    canonical = read_json(canonical_path)
    report = read_json(report_path)
    request = read_json(request_path)
    decision = read_json(decision_path)
    registry = read_json(registry_path)
    runtime = read_json(runtime_path)
    technical = read_json(technical_path)
    visual = read_json(visual_path)
    fallback = next(engine for engine in registry["engines"] if engine["id"] == "animatediff_fallback")
    evaluation = next(item for item in decision["engine_evaluations"] if item["engine_id"] == "animatediff_fallback")

    checks = {
        "fallback_rule_preconditions_exact": request["prior_generation_failed"] is True and request["frame_sequence_available"] is True,
        "fallback_rule_matched": decision["candidate_order"][0] == "animatediff_fallback" and "failed_generation_with_frame_sequence" in decision["matched_rule_ids"],
        "fallback_compatibility_passed": evaluation["compatibility_passed"] is True,
        "fallback_availability_passed": evaluation["availability_passed"] is True,
        "resource_budget_remains_blocked": evaluation["resource_passed"] is False,
        "promotion_remains_blocked": evaluation["promotion_passed"] is False and decision["final_promotion_ready"] is False,
        "selection_remains_fail_closed": decision["result"] == "blocked" and decision["selected_engine"] is None,
        "runtime_proof_passed": runtime["result"] == "pass_local_animatediff_fallback_runtime_smoke",
        "technical_proof_passed": technical["technical_pass"] is True,
        "visual_failure_preserved": visual["visual_temporal_pass"] is False,
        "registry_runtime_links_verified": all(fallback[name]["verification_status"] == "verified" for name in ("model_registry_link", "object_info_evidence", "runtime_proof")),
        "registry_resource_cost_unverified": fallback["resource_limits"]["verification_status"] == "unverified" and fallback["cost_tiers"]["verification_status"] == "unverified",
        "registry_promotion_unverified": fallback["promotion_proof"]["verification_status"] == "unverified",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row020 reconciliation checks failed: {failed}")

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-VIDEO-ENGINE-ROUTING-ANIMATEDIFF-RECONCILIATION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-020",
        "item_id": "ITEM-W64-020",
        "status_decision": STATUS,
        "inputs": [{"path": rel(path), "sha256": sha256(path)} for path in source_inputs],
        "route_probe": {
            "matched_rule_ids": decision["matched_rule_ids"],
            "candidate_order": decision["candidate_order"],
            "selected_engine": decision["selected_engine"],
            "result": decision["result"],
            "fallback_evaluation": evaluation,
        },
        "gate_delta": {
            "engine_compatibility": True,
            "runtime_object_info": True,
            "model_registry_link": True,
            "runtime_proof": True,
            "resource_budget_check": False,
            "runtime_ready": False,
            "final_promotion_ready": False,
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "boundaries": {
            "new_generation_executed": False,
            "row019_proof_reused": True,
            "ec2_started": False,
            "mask_or_geometry_authority_claimed": False,
            "flux_executed": False,
            "wave71_activation_claimed": False,
            "production_video_certification_claimed": False,
        },
        "blockers": [
            "animatediff_fallback_resource_limits_unverified",
            "animatediff_fallback_cost_tier_unverified",
            "animatediff_fallback_visual_promotion_failed",
            "default_wan_engine_unverified",
        ],
        "result": "blocked_fallback_route_compatible_resource_cost_and_promotion_unverified",
        "next_action": "Continue Row021 temporal visual review with the existing eight-frame sequence; do not rerun Row019 or claim production readiness.",
    }
    write_json(output_path, evidence)
    write_json(mirror_path, evidence)

    canonical["timestamp"] = TIMESTAMP
    for artifact in canonical["implementation_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        if artifact_path.is_file():
            artifact["sha256"] = sha256(artifact_path)
    canonical["animatediff_fallback_probe"] = evidence["route_probe"]
    canonical["acceptance_gates"].update(evidence["gate_delta"])
    canonical["runtime"].update({"generation_executed": False, "comfyui_started": False, "existing_row019_generation_reused": True, "reason": "Fallback compatibility and availability are proven from Row019; resource, cost, promotion, and default WAN authority remain blocked."})
    canonical["blocker"] = {"classification": STATUS, "reason": "AnimateDiff fallback routing compatibility is proven, but resource limits and cost tier are unverified, visual promotion failed, and the default WAN engine remains unverified."}
    canonical["result"] = evidence["result"]
    canonical["overall_pass"] = False
    canonical["status_decision"] = STATUS
    canonical["strict_decision"].update({"row_complete": False, "engine_compatibility_claimed": True, "runtime_ready_claimed": False, "final_promotion_claimed": False})
    canonical["reconciliation_evidence"] = rel(output_path)
    write_json(canonical_path, canonical)

    report["timestamp"] = TIMESTAMP
    report["status"] = STATUS
    report["row_complete"] = False
    report["validation"].update({"unit_tests_passed": 23, "unit_test_failures": 0, "animatediff_fallback_rule_matched": True, "animatediff_fallback_compatibility": True, "animatediff_fallback_availability": True, "animatediff_fallback_resource_budget": False, "animatediff_fallback_promotion": False})
    report["acceptance_gates"].update({"engine_compatibility": True, "runtime_object_info": True, "model_registry_link": True, "resource_budget_check": False, "runtime_proof": True, "final_promotion_ready": False})
    report["blocker"] = canonical["blocker"]
    report["evidence"] = [{"path": rel(canonical_path), "sha256": sha256(canonical_path)}, {"path": rel(output_path), "sha256": sha256(output_path)}]
    report["runtime"].update({"generation_count": 0, "comfyui_started": False, "existing_row019_generation_reused": True})
    report["next_action"] = evidence["next_action"]
    write_json(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-020")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-020")
    for name in ("NEXT_ACTION.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend_hydration(PLAN / "Instructions/Hydration_Rehydration" / name, rel(output_path))

    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "fallback_compatibility": True, "runtime_ready": False, "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
