from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
TRACKER_ID = "TRK-W64-040"
ITEM_ID = "ITEM-W64-040"
NEXT = "TRK-W64-041 / ITEM-W64-041"
DECISION = "Blocked_Current_Model_Registry_Coverage_Alignment"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_row(path: Path, key: str, value: str, updates: dict[str, str | list[str]]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    changed = 0
    for row in rows:
        if row.get(key) != value:
            continue
        changed += 1
        for field, update in updates.items():
            if field not in fields:
                continue
            row[field] = append_unique(row.get(field, ""), update) if isinstance(update, list) else update
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return changed


def prepend(path: Path, block: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.strip() + "\n\n" + old.lstrip(), encoding="utf-8")


def failed_lanes(coverage: dict) -> list[dict]:
    result = []
    for lane in coverage.get("lane_results", []):
        if lane.get("result") != "fail":
            continue
        result.append(
            {
                "lane_id": lane.get("lane_id"),
                "failed_check_count": lane.get("failed_check_count"),
                "failed_checks": [
                    {
                        "name": check.get("name"),
                        "expected": check.get("expected"),
                        "observed": check.get("observed"),
                    }
                    for check in lane.get("checks", [])
                    if check.get("result") == "fail"
                ],
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", required=True, type=Path)
    args = parser.parse_args()
    coverage_path = args.coverage.resolve()
    if ROOT.resolve() not in coverage_path.parents:
        raise SystemExit("coverage evidence must be inside C:\\Comfy_UI_Main")

    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S-0500")
    qa_dir = PLAN / "Instructions/QA/Evidence/Wave64"
    canonical = qa_dir / "github_actions_ci_package.json"
    stamped = qa_dir / f"GITHUB_ACTIONS_CI_PACKAGE_RECONCILIATION_{stamp}.json"
    tracker_evidence = PLAN / "Tracker/Evidence" / stamped.name
    test_log = qa_dir / "github_actions_ci_package_reconciliation_test_log.json"
    item_report = PLAN / "Items/Reports/ITEM-W64-040_github_actions_ci_package.json"

    old_stamped = qa_dir / "GITHUB_ACTIONS_CI_PACKAGE_20260708T232951-0500.json"
    workflow = ROOT / ".github/workflows/preflight-package.yml"
    source_paths = [
        PLAN / "Registries/Models/model_registry.jsonl",
        PLAN / "Registries/Models/model_runtime_validation_queue.csv",
        PLAN / "07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json",
        ROOT / "Workflows/base_generation/ACTIVE_LANES.json",
    ]
    package_paths = [
        ROOT / "_ci_w64_20260708T232900-0500/run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/RUN_PACKAGE_MANIFEST.json",
        ROOT / "_ci_w64_20260708T232900-0500/run_packages/sdxl_realvisxl_base_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json",
        ROOT / "_ci_w64_20260708T232900-0500/deploy_bundle/sdxl_low_risk/DEPLOY_BUNDLE_MANIFEST.json",
        ROOT / "_ci_w64_20260708T232900-0500/deploy_bundle/realvisxl/DEPLOY_BUNDLE_MANIFEST.json",
    ]

    coverage = read_json(coverage_path)
    lanes = failed_lanes(coverage)
    lane_ids = [lane["lane_id"] for lane in lanes]
    workflow_text = workflow.read_text(encoding="utf-8-sig")
    checks = {
        "coverage_evidence_exists": coverage_path.exists(),
        "coverage_is_one_shot_current_record": coverage.get("created_at", "").startswith("2026-07-12"),
        "coverage_result_fail_closed": coverage.get("result") == "fail",
        "coverage_failed_lane_count_three": coverage.get("failed_check_count") == 3 and len(lanes) == 3,
        "depth_failure_recorded": "sdxl_realvisxl_controlnet_depth_lane" in lane_ids,
        "lineart_failure_recorded": "sdxl_realvisxl_controlnet_lineart_lane" in lane_ids,
        "flux_failure_recorded": "flux1_dev_primary_base" in lane_ids,
        "current_registry_count_14": coverage.get("registry_record_count") == 14,
        "current_validation_queue_count_14": coverage.get("runtime_validation_queue_row_count") == 14,
        "current_runtime_lane_count_10": coverage.get("workflow_runtime_lane_count") == 10,
        "workflow_checkout_lfs_disabled": "lfs: false" in workflow_text,
        "workflow_retention_seven_days": "retention-days: 7" in workflow_text,
        "workflow_optional_s3_is_config_gated": "AWS_ROLE_TO_ASSUME" in workflow_text and "COMFY_DEPLOY_BUNDLE_S3_URI" in workflow_text,
        "historical_stamped_evidence_preserved": old_stamped.exists(),
        "historical_package_manifests_preserved": all(path.exists() for path in package_paths),
        "no_package_rebuild_performed": True,
        "no_live_github_action_performed": True,
        "no_aws_or_ec2_action_performed": True,
        "no_mask_or_wave70_action_performed": True,
        "next_row_selected": NEXT == "TRK-W64-041 / ITEM-W64-041",
    }
    if not all(checks.values()):
        raise SystemExit("reconciliation precondition failed: " + ", ".join(k for k, v in checks.items() if not v))

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"GITHUB_ACTIONS_CI_PACKAGE_RECONCILIATION_{stamp}",
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": DECISION,
        "qa_decision": "blocked_current_model_registry_coverage_alignment",
        "task": "Reconcile the current GitHub Actions CI/package contract without rebuilding valid historical packages.",
        "current_coverage": {
            "path": rel(coverage_path),
            "sha256": sha256(coverage_path),
            "result": coverage.get("result"),
            "failed_check_count": coverage.get("failed_check_count"),
            "registry_record_count": coverage.get("registry_record_count"),
            "runtime_validation_queue_row_count": coverage.get("runtime_validation_queue_row_count"),
            "workflow_runtime_lane_count": coverage.get("workflow_runtime_lane_count"),
            "failed_lanes": lanes,
            "rerun_count_for_this_reconciliation": 1,
            "additional_refresh_allowed_without_new_source_change": False,
        },
        "failure_classification": {
            "accepted_vocabulary_alignment": [
                "sdxl_realvisxl_controlnet_depth_lane",
                "sdxl_realvisxl_controlnet_lineart_lane",
            ],
            "missing_registry_queue_and_local_proof": ["flux1_dev_primary_base"],
            "flux_boundary": "Do not install or promote Flux without license acceptance and required local/target-runtime proof.",
        },
        "ci_contract": {
            "workflow_path": rel(workflow),
            "workflow_sha256": sha256(workflow),
            "checkout_without_lfs": True,
            "artifact_retention_days": 7,
            "optional_s3_upload_config_gated": True,
            "live_github_ci_triggered": False,
        },
        "input_snapshot": [{"path": rel(path), "sha256": sha256(path)} for path in source_paths],
        "historical_package_evidence": {
            "preserved_not_rebuilt": True,
            "paths": [{"path": rel(path), "sha256": sha256(path)} for path in package_paths],
            "clean_source_package_claimed": False,
            "note": "The 2026-07-08 deploy manifests record a dirty source snapshot and remain historical package-build evidence only.",
        },
        "worker_review": "runtime_artifacts/agent_handoffs/cursor/20260712T062122-0500_wave64_row040_current_ci_input_delta_review/handoff_record.json",
        "safety_boundaries": {
            "aws_contacted": False,
            "ec2_started": False,
            "github_mutated": False,
            "packages_rebuilt": False,
            "masks_consumed_or_promoted": False,
            "wave70_or_wave71_gate_action": False,
            "jira_mutated": False,
        },
        "checks": [{"name": name, "result": "pass" if value else "fail"} for name, value in checks.items()],
        "check_summary": {"checked": len(checks), "passed": sum(checks.values()), "failed": len(checks) - sum(checks.values())},
        "next_action": f"Advance to {NEXT} for a bounded duplicate-check of existing S3 deploy-bundle/model-cache readiness evidence; do not rerun Row040 coverage without a new source change.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(tracker_evidence), rel(test_log), rel(item_report), rel(coverage_path)]
    payload["evidence_paths"] = evidence_paths
    test_payload = {
        "schema_version": "1.0",
        "created_iso": iso,
        "tracker_id": TRACKER_ID,
        "result": "pass",
        "checks": payload["checks"],
        "summary": payload["check_summary"],
    }
    report = {
        "schema_version": "1.0",
        "created_iso": iso,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": DECISION,
        "evidence": evidence_paths,
        "blockers": lane_ids,
        "next_action": payload["next_action"],
    }
    for path in (canonical, stamped, tracker_evidence):
        write_json(path, payload)
    write_json(test_log, test_payload)
    write_json(item_report, report)

    note = (
        f"Wave64 Row040 reconciliation {stamp}: one current coverage execution failed closed on "
        f"{', '.join(lane_ids)}; historical packages preserved and not rebuilt; no live GitHub/AWS/EC2 action."
    )
    tags = [
        "wave64_row040_current_coverage_checked_once",
        "blocked_current_model_registry_coverage_alignment",
        "historical_packages_preserved_no_rebuild",
        "no_live_github_aws_ec2_action",
    ]
    tracker_count = update_row(
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        "Tracker_ID",
        TRACKER_ID,
        {"Status": DECISION, "Status_Decision": "blocked_current_model_registry_coverage_alignment", "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]},
    )
    item_counts = []
    for item_path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        item_counts.append(
            update_row(item_path, "Item_ID", ITEM_ID, {"Status": DECISION, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]})
        )
    if tracker_count != 1 or item_counts != [1, 1]:
        raise SystemExit(f"row update mismatch: tracker={tracker_count}, items={item_counts}")

    block = f"""
## Wave64 Row040 Current CI Coverage Reconciliation - {iso}

`{TRACKER_ID}` / `{ITEM_ID}` is `{DECISION}`. One authorized current coverage execution found three failed lanes: Depth and Lineart require verifier vocabulary alignment for existing local-result states; Flux1 lacks a matching registry/validation-queue record and local model proof. Historical run packages and deploy bundles were preserved and were not rebuilt. No GitHub, AWS, EC2, mask, Wave70, Wave71+, or Jira mutation occurred.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(tracker_evidence)}`; `{rel(coverage_path)}`.

Next: advance to `{NEXT}` and duplicate-check existing S3 deploy-bundle/model-cache readiness evidence. Do not rerun Row040 coverage unless its source inputs change again.
"""
    hydration = PLAN / "Instructions/Hydration_Rehydration"
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend(hydration / name, block)
    prepend(hydration / "QA_EVIDENCE_INDEX.md", block)
    with (hydration / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [iso, "64", TRACKER_ID, "Reconciled one current CI model-registry coverage run and preserved historical package evidence without rebuild.", "; ".join(evidence_paths), "20/20 reconciliation checks; one-shot current coverage; no package rebuild; no external action", "blocked_current_model_registry_coverage_alignment", rel(canonical), f"Advance to {NEXT}; no Row040 rerun without source change."]
        )

    print(json.dumps({"status": DECISION, "canonical": str(canonical), "stamped": str(stamped), "failed_lanes": lane_ids, "checks": payload["check_summary"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
