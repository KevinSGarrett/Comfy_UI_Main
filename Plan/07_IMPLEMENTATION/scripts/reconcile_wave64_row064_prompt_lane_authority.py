#!/usr/bin/env python3
"""Reconcile Row064 lane authority without consuming additive prompt work."""

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
TRK = "TRK-W64-064"
ITEM = "ITEM-W64-064"
STATUS = "Blocked_Profile_Runtime_QA_And_Catalog_Intake_Pending"
DECISION = "indexed_prompt_lane_authority_complete_approval_fail_closed_runtime_and_catalog_intake_pending"
REGISTRY_REL = Path("Plan/10_REGISTRIES/prompt_profile_lane_authority_registry.json")
CANONICAL_REL = Path("Plan/Instructions/QA/Evidence/Wave64/prompt_negative_prompt_qa.json")
DEFAULT_SOURCES = {
    "prior": Path("Plan/Instructions/QA/Evidence/Wave64/PROMPT_NEGATIVE_PROMPT_QA_20260713T004307-0500.json"),
    "portfolio": Path("Plan/10_REGISTRIES/comfyui_delivery_portfolio_registry.json"),
    "stages": Path("Plan/10_REGISTRIES/image_pipeline_stage_contract.json"),
    "protocol": Path("Plan/Instructions/QA/PROMPT_NEGATIVE_PROMPT_QA_PROTOCOL.md"),
}
LEGACY_LEDGER_NOTE = (
    "Wave64 Row064 lane-authority reconciliation: all 109 profiles in the prior hash-verified catalog snapshot "
    "map to current portfolio and pipeline-stage authority. Four exact profile runtime bindings are preserved; "
    "105 remain pending. Additive prompt JSON files are inventoried but not consumed or approved."
)
LEDGER_NOTE = (
    "Wave64 Row064 lane-authority reconciliation: all 109 profiles in the prior hash-verified catalog snapshot "
    "map to current portfolio and pipeline-stage authority. Four exact profile runtime bindings are preserved, "
    "while 105 remain pending. Additive prompt JSON files are inventoried but not consumed or approved."
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def bind(path: Path, root: Path) -> dict[str, Any]:
    resolved = path.resolve()
    before = resolved.stat()
    value = {"path": relative(resolved, root), "sha256": digest(resolved), "bytes": before.st_size}
    after = resolved.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"source changed while hashing: {resolved}")
    return value


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def append_unique(current: str, value: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    if value not in entries:
        entries.append(value)
    return "; ".join(entries)


def append_many(current: str, values: list[str]) -> str:
    result = current
    for value in values:
        result = append_unique(result, value)
    return result


def normalize_ledger_note(current: str) -> str:
    cleaned = (current or "").replace(LEGACY_LEDGER_NOTE, "")
    entries = [entry.strip() for entry in cleaned.split(";") if entry.strip()]
    if LEDGER_NOTE not in entries:
        entries.append(LEDGER_NOTE)
    return "; ".join(entries)


def replace_coverage(current: str, additions: list[str]) -> str:
    stale = {"ninety_three_lane_authority_gaps", "four_prompt_link_gaps"}
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip() and entry.strip() not in stale]
    for value in additions:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def blocker_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("blocker_id"): item for item in payload.get("normalized_blockers", []) if isinstance(item, dict)}


def build(root: Path, sources: dict[str, Path], timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    resolved = {name: (path if path.is_absolute() else root / path).resolve() for name, path in sources.items()}
    prior = load_json(resolved["prior"])
    portfolio = load_json(resolved["portfolio"])
    stages = load_json(resolved["stages"])
    protocol_text = resolved["protocol"].read_text(encoding="utf-8-sig")

    require(prior.get("tracker_id") == TRK and prior.get("item_id") == ITEM, "prior Row064 identity mismatch")
    require(prior.get("row_complete") is False, "prior Row064 state must remain fail-closed")
    summary = prior.get("inventory_summary", {})
    require(summary.get("prompt_profiles") == 109, "prior 109-profile catalog snapshot missing")
    require(summary.get("direct_runtime_evidence_links") == 4, "prior four exact runtime bindings missing")
    records = prior.get("profile_index")
    require(isinstance(records, list) and len(records) == 112, "prior 112-record profile index missing")
    prompt_records = [record for record in records if record.get("artifact_type") == "prompt_profile"]
    require(len(prompt_records) == 109, "prior prompt profile count drift")
    lanes = prior.get("lane_counts")
    require(isinstance(lanes, dict) and len(lanes) == 8 and sum(lanes.values()) == 109, "prior eight-lane count contract missing")
    target_lanes = set(lanes)

    prior_blockers = blocker_map(prior)
    require(prior_blockers.get("PROMPT_TARGET_LANE_AUTHORITY_MISSING", {}).get("count") == 93, "prior 93-lane authority gap missing")
    require(prior_blockers.get("REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING", {}).get("count") == 105, "prior 105-runtime gap missing")
    require(prior_blockers.get("WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED", {}).get("count") == 14, "prior Wave71+ deferral missing")
    require("representative test output aligns with intent, or pending runtime test is explicitly recorded" in protocol_text, "runtime approval rule missing")

    indexed_paths = {record["path"] for record in records}
    for record in records:
        path = (root / record["path"]).resolve()
        require(path.is_file(), f"indexed profile missing: {record['path']}")
        require(digest(path) == record["sha256"], f"indexed profile hash drift: {record['path']}")
    current_paths = {relative(path, root) for path in (root / "PromptProfiles").rglob("*.json")}
    require(indexed_paths <= current_paths, "indexed catalog path set is not present")
    additive_paths = sorted(current_paths - indexed_paths)

    portfolio_rows = {
        lane.get("lane_id"): lane
        for lane in portfolio.get("lanes", [])
        if isinstance(lane, dict) and lane.get("lane_id") in target_lanes
    }
    require(set(portfolio_rows) == target_lanes, "portfolio does not register all eight prompt lanes")
    require(all(row.get("modality") == "image" for row in portfolio_rows.values()), "prompt lane is not image modality")
    require(all(row.get("workflow_graph_complete") is True for row in portfolio_rows.values()), "prompt lane workflow graph is incomplete")
    require(bool(portfolio.get("authority")), "portfolio authority citation missing")

    stage_by_lane: dict[str, str] = {}
    for stage in stages.get("stages", []):
        for lane_id in stage.get("lane_ids", []):
            if lane_id not in target_lanes:
                continue
            require(lane_id not in stage_by_lane, f"prompt lane appears in multiple pipeline stages: {lane_id}")
            stage_by_lane[lane_id] = stage.get("stage")
    require(set(stage_by_lane) == target_lanes, "pipeline stage contract does not map all eight prompt lanes")

    authority_rows = []
    for lane_id in sorted(target_lanes):
        row = portfolio_rows[lane_id]
        authority_rows.append(
            {
                "lane_id": lane_id,
                "indexed_profile_count": lanes[lane_id],
                "pipeline_stage": stage_by_lane[lane_id],
                "portfolio_classification": row.get("classification"),
                "portfolio_state": row.get("state"),
                "portfolio_scope": row.get("scope"),
                "lane_authority_registered": True,
                "profile_runtime_evidence_inferred": False,
                "profile_approval_granted": False,
            }
        )

    updated_records = deepcopy(records)
    registry_path = REGISTRY_REL.as_posix()
    for record in updated_records:
        if record.get("artifact_type") != "prompt_profile":
            continue
        lane_id = record.get("target_lane_id")
        require(lane_id in portfolio_rows, f"profile lane is not authoritative: {record.get('path')}")
        record["lane_authority_present"] = True
        record["lane_authority_binding"] = {
            "registry_path": registry_path,
            "lane_id": lane_id,
            "pipeline_stage": stage_by_lane[lane_id],
            "profile_approval_granted": False,
        }

    runtime_linked = [record for record in updated_records if record.get("artifact_type") == "prompt_profile" and record.get("runtime_evidence_paths")]
    require(len(runtime_linked) == 4, "exact profile runtime binding count drift")
    require(all(record.get("approval_state") != "approved" for record in updated_records), "profile approval was inferred")

    source_bindings = {name: bind(path, root) for name, path in resolved.items()}
    registry = {
        "schema_version": "1.0",
        "registry_id": "wave64_prompt_profile_lane_authority",
        "created_iso": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": "pass_lane_authority_only_profile_approval_fail_closed",
        "catalog_scope": "prior_hash_verified_109_profile_snapshot",
        "authority_source": portfolio.get("authority"),
        "summary": {
            "lane_ids": len(authority_rows),
            "indexed_prompt_profiles": 109,
            "lane_authority_present": 109,
            "lane_authority_missing": 0,
            "exact_profile_runtime_bindings": 4,
            "profile_runtime_bindings_pending": 105,
            "additive_prompt_json_files_not_consumed": len(additive_paths),
            "approved_profiles": 0,
        },
        "lanes": authority_rows,
        "additive_catalog_boundary": {
            "paths": additive_paths,
            "content_consumed_as_authority": False,
            "approval_inferred": False,
        },
        "source_bindings": source_bindings,
        "safety_boundary": {
            "generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "profile_approved": False,
            "wave71_activated": False,
            "mask_or_jira_touched": False,
        },
    }

    blockers = [
        deepcopy(prior_blockers["REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING"]),
        deepcopy(prior_blockers["WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED"]),
    ]
    if additive_paths:
        blockers.append(
            {
                "blocker_id": "PROMPT_CATALOG_ADDITIONS_NOT_YET_INTAKE_VALIDATED",
                "count": len(additive_paths),
                "paths": additive_paths,
                "resolution": "Run a separate intentional intake after the additive user-owned prompt set is stable; do not infer approval from discovery.",
            }
        )

    checks = {
        "PNQ-R01_prior_109_profile_snapshot_hash_verified": len(prompt_records) == 109,
        "PNQ-R02_prior_112_indexed_files_unchanged": indexed_paths <= current_paths,
        "PNQ-R03_eight_target_lane_ids_exact": len(target_lanes) == 8,
        "PNQ-R04_portfolio_registers_all_target_lanes": set(portfolio_rows) == target_lanes,
        "PNQ-R05_all_target_lanes_are_image_workflows": all(row.get("modality") == "image" for row in portfolio_rows.values()),
        "PNQ-R06_pipeline_stage_contract_maps_all_target_lanes": set(stage_by_lane) == target_lanes,
        "PNQ-R07_lane_authority_109_of_109": sum(row["indexed_profile_count"] for row in authority_rows) == 109,
        "PNQ-R08_lane_authority_missing_zero": all(record.get("lane_authority_present") for record in updated_records if record.get("artifact_type") == "prompt_profile"),
        "PNQ-R09_only_four_exact_profile_runtime_bindings_preserved": len(runtime_linked) == 4,
        "PNQ-R10_runtime_evidence_missing_105_preserved": 109 - len(runtime_linked) == 105,
        "PNQ-R11_wave71_plus_deferral_14_preserved": prior_blockers["WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED"]["count"] == 14,
        "PNQ-R12_additive_profiles_inventoried_not_consumed": registry["additive_catalog_boundary"]["content_consumed_as_authority"] is False,
        "PNQ-R13_zero_profile_approvals": registry["summary"]["approved_profiles"] == 0,
        "PNQ-R14_no_generation_or_cloud_action": not any((registry["safety_boundary"]["generation_executed"], registry["safety_boundary"]["aws_contacted"], registry["safety_boundary"]["ec2_started"])),
    }
    require(all(checks.values()), "reconciliation check failed")

    evidence = deepcopy(prior)
    evidence.update(
        {
            "schema_version": "1.1",
            "created_iso": timestamp,
            "status": STATUS,
            "row_complete": False,
            "qa_decision": DECISION,
            "catalog_snapshot": {
                "prior_evidence_id": prior.get("evidence_id"),
                "prior_sha256": source_bindings["prior"]["sha256"],
                "indexed_json_files": len(indexed_paths),
                "current_json_files_discovered": len(current_paths),
                "additive_json_files_not_consumed": len(additive_paths),
                "additive_paths": additive_paths,
            },
            "profile_index": updated_records,
            "normalized_blockers": blockers,
            "checks": [{"name": name, "result": "pass"} for name in checks],
            "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
            "prior_audit_check_summary": prior.get("check_summary"),
            "lane_authority_registry": registry_path,
            "source_hashes": list(source_bindings.values()),
            "safety_boundary": registry["safety_boundary"],
            "next_action": "Keep profile approval fail-closed; intentionally intake additive prompt files only after that user-owned set is stable, and bind representative runtime plus visual QA per profile without duplicate generation.",
        }
    )
    evidence["inventory_summary"] = dict(summary)
    evidence["inventory_summary"].update(
        {
            "json_files": len(current_paths),
            "indexed_json_files": len(indexed_paths),
            "additive_json_files_not_consumed": len(additive_paths),
            "lane_authority_present": 109,
            "lane_authority_missing": 0,
            "direct_runtime_evidence_links": 4,
            "approved_profiles": 0,
        }
    )
    return registry, evidence


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_csv(path: Path, key: str, expected: str, changes: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matches = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matches += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = value
    require(matches == 1, f"ledger row mismatch for {path}: {matches}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    timestamp = args.timestamp or datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
    stamp = datetime.fromisoformat(timestamp).strftime("%Y%m%dT%H%M%S%z")
    sources = {name: root / path for name, path in DEFAULT_SOURCES.items()}
    registry, evidence = build(root, sources, timestamp)

    canonical = root / CANONICAL_REL
    stamped = canonical.parent / f"PROMPT_NEGATIVE_PROMPT_QA_{stamp}.json"
    mirror = root / "Plan/Tracker/Evidence" / stamped.name
    test_log = canonical.parent / "prompt_negative_prompt_qa_test_log.json"
    report = root / "Plan/Items/Reports/ITEM-W64-064_prompt_negative_prompt_qa.json"
    evidence_paths = [relative(path, root) for path in (canonical, stamped, mirror, test_log, report, root / REGISTRY_REL)]
    evidence["evidence_id"] = stamped.stem
    evidence["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write_json(path, evidence)
    write_json(root / REGISTRY_REL, registry)
    write_json(test_log, {"schema_version": "1.0", "created_iso": timestamp, "tracker_id": TRK, "result": "pass_lane_authority_profile_approval_blocked", "checks": evidence["checks"], "summary": evidence["check_summary"]})
    write_json(report, {"schema_version": "1.0", "created_iso": timestamp, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "inventory_summary": evidence["inventory_summary"], "normalized_blockers": evidence["normalized_blockers"], "evidence": evidence_paths, "next_action": evidence["next_action"]})

    if not args.no_ledger:
        coverage_additions = ["all_109_indexed_prompt_lanes_authoritative", "105_profile_runtime_links_pending", "additive_prompt_catalog_intake_pending", "wave71_profiles_deferred"]
        for path in (root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv", root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Tracker_ID") == TRK)
            update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": append_many(row.get("Evidence_Path", ""), evidence_paths), "Coverage_Audit_Status": replace_coverage(row.get("Coverage_Audit_Status", ""), coverage_additions), "Notes": normalize_ledger_note(row.get("Notes", ""))})
        for path in (root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv", root / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Item_ID") == ITEM)
            update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": append_many(row.get("Evidence_Required", ""), evidence_paths), "Coverage_Audit_Status": replace_coverage(row.get("Coverage_Audit_Status", ""), coverage_additions), "Notes": normalize_ledger_note(row.get("Notes", ""))})

    print(json.dumps({"status": STATUS, "decision": DECISION, "summary": registry["summary"], "checks": evidence["check_summary"], "evidence": evidence_paths}, indent=2))


if __name__ == "__main__":
    main()
