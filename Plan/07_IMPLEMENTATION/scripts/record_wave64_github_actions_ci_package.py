from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W64-040"
ITEM_ID = "ITEM-W64-040"
NEXT_TRACKER_ID = "TRK-W64-041"
NEXT_ITEM_ID = "ITEM-W64-041"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

CI_ROOT = PROJECT_ROOT / "_ci_w64_20260708T232900-0500"
CI_SUMMARY = CI_ROOT / "LOCAL_CI_PACKAGE_MIRROR_SUMMARY.json"
MODEL_REGISTRY_COVERAGE = CI_ROOT / "model_registry/model_registry_coverage.json"
WORKFLOW_FILE = PROJECT_ROOT / ".github/workflows/preflight-package.yml"
SOURCE_RUNBOOK = PLAN_ROOT / "Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md"

LOW_RISK_RUN_PACKAGE = CI_ROOT / "run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/RUN_PACKAGE_MANIFEST.json"
REALVISXL_RUN_PACKAGE = CI_ROOT / "run_packages/sdxl_realvisxl_base_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json"
LOW_RISK_DEPLOY_BUNDLE = CI_ROOT / "deploy_bundle/sdxl_low_risk/DEPLOY_BUNDLE_MANIFEST.json"
REALVISXL_DEPLOY_BUNDLE = CI_ROOT / "deploy_bundle/realvisxl/DEPLOY_BUNDLE_MANIFEST.json"

EVIDENCE = QA_DIR / "github_actions_ci_package.json"
STAMPED_EVIDENCE = QA_DIR / f"GITHUB_ACTIONS_CI_PACKAGE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"GITHUB_ACTIONS_CI_PACKAGE_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def summarize_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": evidence_path(path), "exists": False}
    manifest = read_json(path)
    return {
        "path": evidence_path(path),
        "exists": True,
        "result": manifest.get("result"),
        "lane_id": manifest.get("lane_id"),
        "run_id": manifest.get("run_id"),
        "file_count": manifest.get("file_count"),
        "bundle_zip": manifest.get("bundle_zip"),
        "bundle_zip_sha256": manifest.get("bundle_zip_sha256"),
        "source_git_clean": manifest.get("source_git_clean"),
        "source_git_status_count": manifest.get("source_git_status_count"),
    }


def summarize_failed_lanes(coverage: dict[str, object]) -> list[dict[str, object]]:
    failed: list[dict[str, object]] = []
    for lane in coverage.get("lane_results", []):
        if not isinstance(lane, dict):
            continue
        if lane.get("result") == "pass" and not lane.get("failed_check_count"):
            continue
        failed_checks: list[dict[str, object]] = []
        for check in lane.get("checks", []):
            if isinstance(check, dict) and check.get("result") == "fail":
                failed_checks.append(
                    {
                        "name": check.get("name"),
                        "expected": check.get("expected"),
                        "observed": check.get("observed"),
                    }
                )
        failed.append(
            {
                "lane_id": lane.get("lane_id"),
                "result": lane.get("result"),
                "failed_check_count": lane.get("failed_check_count"),
                "failed_checks": failed_checks,
            }
        )
    return failed


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Mirrored GitHub Actions preflight/package lane locally and recorded exact coverage-gate blocker.",
        "; ".join(payload["evidence_paths"]),
        "workflow contract; local CI mirror; no-lfs checkout policy; artifact retention; optional S3 gate; run package manifests; deploy bundle manifests; model registry coverage gate",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Stop CI package reruns for this row; advance to {NEXT_TRACKER_ID} unless source/config changes.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    summary = read_json(CI_SUMMARY)
    coverage = read_json(MODEL_REGISTRY_COVERAGE)
    workflow_text = WORKFLOW_FILE.read_text(encoding="utf-8-sig")
    failed_lanes = summarize_failed_lanes(coverage)
    steps = summary.get("steps", [])
    step_statuses = {
        step.get("name"): step.get("status")
        for step in steps
        if isinstance(step, dict)
    }

    errors: list[str] = []
    if summary.get("local_only") is not True:
        errors.append("ci_mirror_not_local_only")
    if summary.get("ec2_started") is not False:
        errors.append("ec2_started_unexpectedly")
    if summary.get("aws_contacted") is not False:
        errors.append("aws_contacted_unexpectedly")
    if summary.get("github_api_contacted") is not False:
        errors.append("github_api_contacted_unexpectedly")
    if summary.get("no_lfs_default") is not True or "lfs: false" not in workflow_text:
        errors.append("no_lfs_default_not_verified")
    if summary.get("artifact_retention_days_declared") != 7 or "retention-days: 7" not in workflow_text:
        errors.append("artifact_retention_7_days_not_verified")
    if summary.get("optional_s3_upload_config_gated") is not True:
        errors.append("optional_s3_upload_not_config_gated")
    if summary.get("failed_step_count") != 1:
        errors.append(f"unexpected_failed_step_count:{summary.get('failed_step_count')}")
    if step_statuses.get("model_registry_coverage_gate") != "fail":
        errors.append("model_registry_coverage_gate_failure_not_observed")
    for step_name in [
        "sync_workflow_exports",
        "build_run_package_low_risk",
        "build_deploy_bundle_low_risk",
        "build_run_package_realvisxl",
        "build_deploy_bundle_realvisxl",
    ]:
        if step_statuses.get(step_name) != "pass":
            errors.append(f"{step_name}_not_pass:{step_statuses.get(step_name)}")
    if coverage.get("result") != "fail":
        errors.append(f"coverage_gate_result_unexpected:{coverage.get('result')}")
    if not failed_lanes:
        errors.append("coverage_gate_failed_lanes_missing")

    qa_decision = (
        "blocked_github_actions_ci_package_model_registry_coverage_gate"
        if not errors
        else "invalid_github_actions_ci_package_evidence_record"
    )
    deploy_bundle_manifests = [
        summarize_manifest(LOW_RISK_DEPLOY_BUNDLE),
        summarize_manifest(REALVISXL_DEPLOY_BUNDLE),
    ]
    run_package_manifests = [
        summarize_manifest(LOW_RISK_RUN_PACKAGE),
        summarize_manifest(REALVISXL_RUN_PACKAGE),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"GITHUB_ACTIONS_CI_PACKAGE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate GitHub Actions preflight/package lane locally without EC2 or external service contact.",
        "source_runbook": rel(SOURCE_RUNBOOK),
        "workflow_file": rel(WORKFLOW_FILE),
        "local_ci_mirror_summary": evidence_path(CI_SUMMARY),
        "model_registry_coverage_evidence": evidence_path(MODEL_REGISTRY_COVERAGE),
        "ci_contract": {
            "workflow_exists": WORKFLOW_FILE.exists(),
            "checkout_without_lfs": "lfs: false" in workflow_text,
            "artifact_retention_days": summary.get("artifact_retention_days_declared"),
            "optional_s3_upload_config_gated": summary.get("optional_s3_upload_config_gated"),
            "matrix_lane_ids": [
                "sdxl_low_risk_fallback_lane",
                "sdxl_realvisxl_base_lane",
            ],
            "live_github_ci_status_checked": False,
            "live_github_ci_status_blocked_reason": "No push/live CI run was triggered by this row; local mirror is the bounded evidence while worktree remains dirty.",
        },
        "local_mirror": {
            "ci_root": evidence_path(CI_ROOT),
            "local_only": summary.get("local_only"),
            "ec2_started": summary.get("ec2_started"),
            "aws_contacted": summary.get("aws_contacted"),
            "github_api_contacted": summary.get("github_api_contacted"),
            "civitai_contacted": summary.get("civitai_contacted"),
            "comfyui_contacted": summary.get("comfyui_contacted"),
            "failed_step_count": summary.get("failed_step_count"),
            "steps": steps,
        },
        "model_registry_coverage_gate": {
            "result": coverage.get("result"),
            "failed_check_count": coverage.get("failed_check_count"),
            "registry_record_count": coverage.get("registry_record_count"),
            "runtime_validation_queue_row_count": coverage.get("runtime_validation_queue_row_count"),
            "workflow_runtime_lane_count": coverage.get("workflow_runtime_lane_count"),
            "active_lane_ids": coverage.get("active_lane_ids"),
            "failed_lanes": failed_lanes,
        },
        "run_package_manifests": run_package_manifests,
        "deploy_bundle_manifests": deploy_bundle_manifests,
        "blocker": {
            "reason": "Model registry coverage gate fails for RealVisXL/ControlNet lane registry, queue, and lane-state alignment.",
            "coverage_gate_failed": True,
            "package_builds_preserved": True,
            "coverage_refresh_loop_allowed": False,
            "next_allowed_action": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} unless model registry sources are intentionally changed.",
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} S3 deploy bundle/model cache readiness; do not rerun coverage for this row unless source/config changes.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(CI_SUMMARY),
        evidence_path(MODEL_REGISTRY_COVERAGE),
        evidence_path(LOW_RISK_RUN_PACKAGE),
        evidence_path(REALVISXL_RUN_PACKAGE),
        evidence_path(LOW_RISK_DEPLOY_BUNDLE),
        evidence_path(REALVISXL_DEPLOY_BUNDLE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    failed_lane_ids = [str(lane.get("lane_id")) for lane in failed_lanes]
    note = (
        f"Wave64 GitHub Actions CI/package {STAMP}: local mirror failed exactly one step, "
        f"model_registry_coverage_gate; coverage_result={coverage.get('result')} failed_check_count={coverage.get('failed_check_count')}; "
        f"failed_lanes={failed_lane_ids}; run_packages_built=True; deploy_bundles_built=True; "
        f"no_lfs_default={summary.get('no_lfs_default')}; artifact_retention_days={summary.get('artifact_retention_days_declared')}; "
        f"optional_s3_gated={summary.get('optional_s3_upload_config_gated')}; ec2_started=False."
    )
    additions = [
        "wave64_github_actions_ci_package_checked",
        qa_decision,
        "run_packages_built",
        "deploy_bundles_built",
        "model_registry_coverage_gate_failed",
        "no_lfs_default_verified",
        "artifact_retention_verified",
        "optional_s3_upload_gated",
        "allowed_nonmask_work_can_continue",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            ITEM_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 GitHub Actions CI Package Lane - {ISO_TS}

Worked non-EC2 CI/package row `{TRACKER_ID}` / `{ITEM_ID}` with a bounded local mirror of `.github/workflows/preflight-package.yml`.

Result: `{qa_decision}`. The workflow contract verifies checkout without LFS, 7-day deploy-bundle artifact retention, and optional S3 upload gated by repository variables. Local run packages and deploy bundles were built for the low-risk SDXL lane and RealVisXL base lane.

Exact blocker: `model_registry_coverage_gate` failed with coverage result `{coverage.get('result')}` and failed_check_count=`{coverage.get('failed_check_count')}`. Failed lanes: `{', '.join(failed_lane_ids)}`. No live GitHub CI run was triggered here, no EC2 was started, and no external services were contacted.

Boundary: stop CI/package reruns for this row unless workflow/model-registry sources change. No masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(CI_SUMMARY)}`
- `{evidence_path(MODEL_REGISTRY_COVERAGE)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` S3 deploy bundle/model cache readiness, which is non-EC2 and non-mask.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"""
## Wave64 GitHub Actions CI Package Lane - {ISO_TS}

Bounded local mirror of GitHub Actions preflight/package lane. Run packages and deploy bundles built; model registry coverage gate remains blocked.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(CI_SUMMARY)}`
- `{evidence_path(MODEL_REGISTRY_COVERAGE)}`
""",
    )
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "stamped_evidence": str(STAMPED_EVIDENCE),
                "tracker_evidence": str(TRACKER_EVIDENCE),
                "qa_decision": qa_decision,
                "failed_lane_ids": failed_lane_ids,
                "errors": errors,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
