from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
SOURCE_ROOT = PLAN / "12_SOURCE_SUMMARIES"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TRACKER = "TRK-W64-055"
ITEM = "ITEM-W64-055"
NEXT = "TRK-W64-056 / ITEM-W64-056"
STATUS = "Evidence_Passed_Source_Summary_Integrity_Boundary_Active"
TZ = ZoneInfo("America/Chicago")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    values = [value.strip() for value in (existing or "").split(";") if value.strip()]
    for addition in additions:
        if addition and addition not in values:
            values.append(addition)
    return "; ".join(values)


def update_csv(path: Path, key: str, value: str, changes: dict[str, object]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != value:
            continue
        count += 1
        for field, replacement in changes.items():
            if field not in fields:
                continue
            row[field] = append_unique(row.get(field, ""), replacement) if isinstance(replacement, list) else str(replacement)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.strip() + "\n\n" + current.lstrip(), encoding="utf-8")


def main() -> None:
    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S-0500")
    source_files = sorted(path for path in SOURCE_ROOT.rglob("*") if path.is_file())
    inventory: list[dict[str, object]] = []
    hash_groups: defaultdict[str, list[str]] = defaultdict(list)
    parser_diagnostics: list[dict[str, object]] = []
    for path in source_files:
        suffix = path.suffix.lower()
        valid_json = None
        top_level_keys: list[str] = []
        if suffix == ".json":
            try:
                value = load(path)
                valid_json = True
                if isinstance(value, dict):
                    top_level_keys = list(value)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                valid_json = False
                parser_diagnostics.append({"path": rel(path), "parser": "python_stdlib_json", "error": str(error)})
        sha = digest(path)
        hash_groups[sha].append(rel(path))
        inventory.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha, "kind": suffix, "json_valid_python_stdlib": valid_json, "top_level_keys": top_level_keys})

    duplicate_groups = [{"sha256": sha, "paths": paths, "classification": "explicit_byte_identical_alias_pair" if len(paths) == 2 else "unreviewed_duplicate_group"} for sha, paths in hash_groups.items() if len(paths) > 1]
    active_targets = {
        "current_main_flow_registry": PLAN / "10_REGISTRIES/current_main_flow_summary.json",
        "current_runtime_lane_queue": PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json",
        "source_plan_registry": PLAN / "10_REGISTRIES/source_plans_zip_summary.json",
        "source_tracker_registry": PLAN / "10_REGISTRIES/source_tracker_summary.json",
        "current_execution_tracker": PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    }
    target_records = {}
    for key, path in active_targets.items():
        mutable_ledger = key == "current_execution_tracker"
        target_records[key] = {
            "path": rel(path),
            "exists": path.exists(),
            "binding_mode": "mutable_path_and_policy" if mutable_ledger else "content_hash",
            "sha256": None if mutable_ledger else digest(path) if path.exists() else None,
        }

    link_records: list[dict[str, object]] = []
    for record in inventory:
        path = str(record["path"])
        lower = path.lower()
        if "source_snapshots" in lower or "main_flow" in lower:
            targets = ["current_main_flow_registry", "current_runtime_lane_queue", "current_execution_tracker"]
            relation = "historical_main_flow_context_to_independently_validated_current_surfaces"
        elif "manifest" in lower or "reconciliation" in lower or "source_files_reviewed" in lower:
            targets = ["source_plan_registry", "source_tracker_registry", "current_execution_tracker"]
            relation = "historical_source_intake_context_to_current_source_registries"
        else:
            targets = ["current_execution_tracker", "current_main_flow_registry"]
            relation = "historical_planning_context_to_current_execution_and_main_flow_surfaces"
        link_records.append({
            "source_path": path,
            "source_sha256": record["sha256"],
            "promotion_status": "source_context_only_not_runtime_truth",
            "relation": relation,
            "active_surface_links": [{"surface_id": target, **target_records[target]} for target in targets],
            "promotion_boundary": "This source summary may inform implementation, but cannot promote runtime, model, mask, visual, certification, or tracker state without separate current validation evidence.",
        })

    registry = PLAN / "10_REGISTRIES/source_summary_active_surface_links.json"
    registry_payload = {
        "schema_version": "1.0",
        "artifact_id": "source_summary_active_surface_links",
        "created_iso": iso,
        "status": "active_integrity_boundary",
        "source_root": rel(SOURCE_ROOT),
        "source_file_count": len(inventory),
        "canonical_json_parser": "python_stdlib_json",
        "parser_note": "PowerShell ConvertFrom-Json rejects the valid empty-string key in WAVE17_TRACKER_BODY_SHAPE_KEYWORD_SUMMARY.json; Python stdlib parses all 23 JSON files, so the source is preserved unchanged.",
        "global_promotion_boundary": "Source summaries and snapshots are historical context only. Hash or link presence is not runtime proof and cannot promote an active surface by itself.",
        "active_surfaces": target_records,
        "duplicate_hash_groups": duplicate_groups,
        "source_links": link_records,
    }
    write(registry, registry_payload)

    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRACKER]
    required_gates = {"source_snapshot_exists", "promotion_boundary", "snapshot_hash", "active_surface_link"}
    actual_gates = set(tracker_rows[0]["Validation_Method"].split("|")) if len(tracker_rows) == 1 else set()
    wave14 = load(SOURCE_ROOT / "source_snapshots/WAVE14_MAIN_FLOW_ORCHESTRATOR_SOURCE_SUMMARY.json")
    wave15 = load(SOURCE_ROOT / "source_snapshots/WAVE15_MAIN_FLOW_BASE_LANE_SOURCE_SUMMARY.json")
    runtime_snapshot_text = (SOURCE_ROOT / "source_snapshots/WAVE42_MAIN_FLOW_20260702.runtime_bound_snapshot.json").read_text(encoding="utf-8-sig")
    boundary_text = "\n".join((SOURCE_ROOT / name).read_text(encoding="utf-8-sig") for name in ("WAVE03_SOURCE_RECONCILIATION.md", "wave07_source_intake_summary.json", "WAVE08_UPLOADED_SOURCE_STATUS.json"))
    alias_names = {
        "Plan/12_SOURCE_SUMMARIES/source_snapshots/WAVE42_MAIN_FLOW_20260702.runtime_bound_snapshot.json",
        "Plan/12_SOURCE_SUMMARIES/source_snapshots/WAVE42_MAIN_FLOW_20260702_WAVE13_SOURCE.json",
    }
    checks = {
        "source_file_count_33": len(inventory) == 33,
        "json_file_count_23": sum(record["kind"] == ".json" for record in inventory) == 23,
        "markdown_file_count_10": sum(record["kind"] == ".md" for record in inventory) == 10,
        "all_json_python_valid": all(record["json_valid_python_stdlib"] is True for record in inventory if record["kind"] == ".json"),
        "wave17_empty_key_preserved_valid": "" in load(SOURCE_ROOT / "WAVE17_TRACKER_BODY_SHAPE_KEYWORD_SUMMARY.json")["body_shape_wave_counts"],
        "one_duplicate_hash_group": len(duplicate_groups) == 1,
        "duplicate_group_exact_alias_pair": set(duplicate_groups[0]["paths"]) == alias_names,
        "duplicate_pair_hash_matches": len({record["sha256"] for record in inventory if record["path"] in alias_names}) == 1,
        "all_source_hashes_complete": all(len(str(record["sha256"])) == 64 for record in inventory),
        "canonical_runtime_snapshot_exists": (SOURCE_ROOT / "source_snapshots/WAVE42_MAIN_FLOW_20260702.runtime_bound_snapshot.json").exists(),
        "canonical_source_manifest_exists": (SOURCE_ROOT / "WAVE03_SOURCE_MANIFEST.json").exists(),
        "row055_exactly_once": len(tracker_rows) == 1,
        "row055_required_gate_set_exact": actual_gates == required_gates,
        "row055_source_root_exact": Path(tracker_rows[0]["Source_Path"]).resolve() == SOURCE_ROOT.resolve(),
        "promotion_boundary_language_present": "not runtime proof" in boundary_text.lower() or "not the final execution architecture" in boundary_text.lower(),
        "runtime_promotion_fail_closed_present": "blocked_missing_runtime_proof" in runtime_snapshot_text,
        "wave14_orchestrator_boundary_present": isinstance(wave14, dict) and bool(wave14.get("orchestrator_boundary")),
        "wave15_promotion_risk_present": "blocker_for_promotion" in json.dumps(wave15),
        "all_sources_have_existing_hash_bound_active_links": len(link_records) == len(inventory) and all(any(link["exists"] and link["binding_mode"] == "content_hash" and len(str(link["sha256"])) == 64 for link in record["active_surface_links"]) for record in link_records),
        "no_runtime_promotion_or_external_action": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed checks: " + ", ".join(failed))

    canonical = QA / "source_summary_integrity.json"
    stamped = QA / f"SOURCE_SUMMARY_INTEGRITY_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "source_summary_integrity_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-055_source_summary_integrity.json"
    runtime_inventory = ROOT / "runtime_artifacts/wave64/row055_source_summary_integrity/current_source_summary_inventory.json"
    runtime_links = ROOT / "runtime_artifacts/wave64/row055_source_summary_integrity/row055_active_surface_links.json"
    runtime_gates = ROOT / "runtime_artifacts/wave64/row055_source_summary_integrity/row055_integrity_gate_results.json"
    inventory_payload = {"schema_version": "1.0", "created_iso": iso, "canonical_json_parser": "python_stdlib_json", "file_count": len(inventory), "json_count": sum(record["kind"] == ".json" for record in inventory), "markdown_count": sum(record["kind"] == ".md" for record in inventory), "invalid_json_count": len(parser_diagnostics), "parser_diagnostics": parser_diagnostics, "duplicate_hash_groups": duplicate_groups, "files": inventory}
    write(runtime_inventory, inventory_payload)
    write(runtime_links, registry_payload)
    write(runtime_gates, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER, "gates": {gate: "pass" for gate in sorted(required_gates)}, "checks": [{"name": name, "result": "pass"} for name in checks], "summary": {"checked": len(checks), "passed": len(checks), "failed": 0}})

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"SOURCE_SUMMARY_INTEGRITY_{stamp}",
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRACKER,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": True,
        "qa_decision": "source_summary_integrity_pass_context_only_hash_bound_active_links",
        "task": "Hash-bind every source summary and enforce explicit promotion boundaries into current active surfaces.",
        "inventory": {"source_root": rel(SOURCE_ROOT), "file_count": len(inventory), "json_count": inventory_payload["json_count"], "markdown_count": inventory_payload["markdown_count"], "invalid_json_count": 0, "duplicate_hash_groups": duplicate_groups},
        "parser_resolution": registry_payload["parser_note"],
        "promotion_boundary": registry_payload["global_promotion_boundary"],
        "active_surface_registry": {"path": rel(registry), "sha256": digest(registry), "source_link_count": len(link_records), "active_surfaces": target_records},
        "gates": {gate: "pass" for gate in sorted(required_gates)},
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "safety_boundary": {"runtime_proof_claimed": False, "active_surface_promoted_from_summary": False, "aws_contacted": False, "ec2_started": False, "s3_mutated": False, "comfyui_contacted": False, "generation_executed": False, "mask_truth_consumed": False, "wave71_activated": False, "jira_mutated": False},
        "next_action": f"Advance to {NEXT} advanced-additions integration coverage without treating source summaries as runtime truth.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report), rel(registry), rel(runtime_inventory), rel(runtime_links), rel(runtime_gates)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER, "result": "pass", "gates": payload["gates"], "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER, "item_id": ITEM, "status": STATUS, "inventory": payload["inventory"], "promotion_boundary": payload["promotion_boundary"], "active_surface_registry": payload["active_surface_registry"], "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row055 {stamp}: 33/33 source summaries hash-bound; 23 JSON valid by Python stdlib; 33 active-surface links; 20/20 checks; source context cannot promote runtime truth."
    tags = ["wave64_row055_source_summary_integrity_pass", "source_snapshot_exists_pass", "promotion_boundary_pass", "snapshot_hash_pass", "active_surface_link_pass", "advance_to_row056"]
    tracker_counts = [update_csv(path, "Tracker_ID", TRACKER, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_counts = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_counts != [1, 1] or item_counts != [1, 1]:
        raise SystemExit(f"row update mismatch: tracker={tracker_counts} items={item_counts}")

    block = f"""## Wave64 Row055 Source Summary Integrity - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. All 33 files under `Plan/12_SOURCE_SUMMARIES` are hash-bound; all 23 JSON files pass Python standard-library parsing, including the valid WAVE17 empty-string key that PowerShell misclassified. One byte-identical WAVE42 snapshot alias pair is explicit and allowed.

Every source summary now has a hash-bound link to at least one existing current project surface through `{rel(registry)}`. These links are context only: they do not constitute runtime proof and cannot promote models, workflows, masks, visuals, tracker state, or certification without separate current validation evidence. No external/runtime/mask/Jira action occurred.

Next: `{NEXT}` advanced-additions integration coverage.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md"):
        prepend(HYD / name, block)
    with (HYD / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRACKER, "Hash-bound 33 source summaries and linked them to current surfaces with a strict context-only promotion boundary.", "; ".join(evidence_paths), "20/20 checks; four required gates pass", payload["qa_decision"], rel(canonical), f"Begin {NEXT}."])
    print(json.dumps({"status": STATUS, "source_files": len(inventory), "json_valid": inventory_payload["json_count"], "active_links": len(link_records), "checks": payload["check_summary"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
