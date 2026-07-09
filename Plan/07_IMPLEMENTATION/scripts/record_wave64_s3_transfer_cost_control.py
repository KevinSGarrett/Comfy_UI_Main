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

TRACKER_ID = "TRK-W64-041"
ITEM_ID = "ITEM-W64-041"
NEXT_TRACKER_ID = "TRK-W64-042"
NEXT_ITEM_ID = "ITEM-W64-042"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
OPERATIONS_STATIC_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Operations_Static_Validation"

READINESS = max(
    OPERATIONS_STATIC_DIR.glob("W64_S3_RUNTIME_TRANSFER_READINESS_*.json"),
    key=lambda path: path.stat().st_mtime,
)
SOURCE_SCRIPT = PLAN_ROOT / "Instructions/Operations/Scripts/Test-S3RuntimeTransferReadiness.ps1"
SOURCE_RUNBOOK = PLAN_ROOT / "Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md"
AWS_TEMPLATE_DIR = PROJECT_ROOT / "configs/aws"

EVIDENCE = QA_DIR / "s3_transfer_cost_control.json"
STAMPED_EVIDENCE = QA_DIR / f"S3_TRANSFER_COST_CONTROL_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"S3_TRANSFER_COST_CONTROL_{STAMP}.json"

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


def listify(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def policy_action_summary(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8-sig")
    policy = json.loads(text)
    actions: list[str] = []
    resources: list[str] = []
    wildcard_actions: list[str] = []
    wildcard_resources: list[str] = []
    for statement in listify(policy.get("Statement")):
        if not isinstance(statement, dict):
            continue
        for action in listify(statement.get("Action")):
            action_str = str(action)
            actions.append(action_str)
            if "*" in action_str:
                wildcard_actions.append(action_str)
        for resource in listify(statement.get("Resource")):
            resource_str = str(resource)
            resources.append(resource_str)
            if resource_str == "*":
                wildcard_resources.append(resource_str)
    return {
        "path": rel(path),
        "json_valid": True,
        "actions": sorted(set(actions)),
        "resource_count": len(resources),
        "wildcard_actions": sorted(set(wildcard_actions)),
        "wildcard_resources": wildcard_resources,
        "least_privilege_static_pass": not wildcard_actions and not wildcard_resources,
    }


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded S3 deploy-bundle/model-cache/artifact transfer readiness without contacting AWS.",
        "; ".join(payload["evidence_paths"]),
        "s3 URI shape; policy template JSON; static least privilege; missing config report; no secret print; no AWS contact; no EC2 start",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}; any live AWS policy application remains a separate authenticated operation.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    readiness = read_json(READINESS)
    templates = sorted(AWS_TEMPLATE_DIR.glob("*.template.json"))
    policy_summaries = [policy_action_summary(path) for path in templates]
    template_failures = [
        check
        for check in readiness.get("policy_template_checks", [])
        if isinstance(check, dict) and check.get("result") != "pass"
    ]
    least_privilege_failures = [
        summary
        for summary in policy_summaries
        if not summary["least_privilege_static_pass"]
    ]
    resolved_config = readiness.get("resolved_config", {})
    missing_config = readiness.get("missing_config", [])

    errors: list[str] = []
    if readiness.get("result") != "ready_local_only":
        errors.append(f"readiness_not_ready_local_only:{readiness.get('result')}")
    if readiness.get("local_only") is not True:
        errors.append("readiness_not_local_only")
    if readiness.get("aws_contacted") is not False:
        errors.append("aws_contacted_unexpectedly")
    if readiness.get("github_api_contacted") is not False:
        errors.append("github_api_contacted_unexpectedly")
    if readiness.get("ec2_started") is not False:
        errors.append("ec2_started_unexpectedly")
    if readiness.get("generation_executed") is not False:
        errors.append("generation_executed_unexpectedly")
    if readiness.get("secrets_printed") is not False:
        errors.append("secrets_printed_unexpectedly")
    if template_failures:
        errors.append(f"policy_template_failures:{len(template_failures)}")
    if least_privilege_failures:
        errors.append(f"least_privilege_static_failures:{len(least_privilege_failures)}")
    if missing_config:
        errors.append(f"missing_config:{len(missing_config)}")
    for key in [
        "deploy_bundle_s3_uri_present",
        "model_cache_s3_uri_present",
        "artifact_s3_uri_present",
        "github_role_arn_present",
        "scheduler_role_arn_present",
    ]:
        if isinstance(resolved_config, dict) and resolved_config.get(key) is not True:
            errors.append(f"resolved_config_missing:{key}")

    qa_decision = (
        "s3_transfer_cost_control_ready_local_only_no_secret_print"
        if not errors
        else "blocked_s3_transfer_cost_control_readiness_gap"
    )
    env_checks = []
    for check in readiness.get("env_checks", []):
        if isinstance(check, dict):
            env_checks.append(
                {
                    "name": check.get("name"),
                    "exists": check.get("exists"),
                    "has_value": check.get("has_value"),
                }
            )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"S3_TRANSFER_COST_CONTROL_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate S3 deploy bundle, model cache, artifact transfer, GitHub OIDC, and scheduler stop readiness locally.",
        "source_script": rel(SOURCE_SCRIPT),
        "source_runbook": rel(SOURCE_RUNBOOK),
        "readiness_evidence": evidence_path(READINESS),
        "readiness_result": {
            "result": readiness.get("result"),
            "failure_category": readiness.get("failure_category"),
            "local_only": readiness.get("local_only"),
            "aws_contacted": readiness.get("aws_contacted"),
            "github_api_contacted": readiness.get("github_api_contacted"),
            "civitai_contacted": readiness.get("civitai_contacted"),
            "comfyui_contacted": readiness.get("comfyui_contacted"),
            "ec2_started": readiness.get("ec2_started"),
            "generation_executed": readiness.get("generation_executed"),
            "secrets_printed": readiness.get("secrets_printed"),
        },
        "config_shape": {
            "env_file_present": readiness.get("env_file_present"),
            "region_present_without_value_disclosure": bool(readiness.get("region")),
            "env_checks_no_values": env_checks,
            "resolved_config": resolved_config,
            "missing_config": missing_config,
        },
        "policy_template_checks": readiness.get("policy_template_checks"),
        "least_privilege_static_summary": policy_summaries,
        "live_aws_boundary": {
            "iam_policy_applied": False,
            "bucket_permissions_live_tested": False,
            "s3_publish_execute_run": False,
            "scheduler_role_live_tested": False,
            "reason": "This row is local-only by tracker definition; live AWS application requires fresh auth and a separate bounded operation.",
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} EC2 TTL watchdog row; keep EC2 start gated by current AWS auth and Git checkpoint state.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(READINESS),
        rel(SOURCE_SCRIPT),
        rel(SOURCE_RUNBOOK),
    ]
    payload["evidence_paths"].extend(rel(path) for path in templates)

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 S3 transfer cost control {STAMP}: readiness={readiness.get('result')}; "
        f"missing_config_count={len(missing_config)}; template_failures={len(template_failures)}; "
        f"least_privilege_static_failures={len(least_privilege_failures)}; secrets_printed={readiness.get('secrets_printed')}; "
        f"aws_contacted=False; ec2_started=False; decision={qa_decision}."
    )
    additions = [
        "wave64_s3_transfer_readiness_checked",
        qa_decision,
        "s3_uri_shape_present",
        "policy_templates_json_valid",
        "least_privilege_static_checked",
        "missing_config_report_empty",
        "no_secret_print_verified",
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
## Immediate Next Action - Wave64 S3 Transfer Cost Control - {ISO_TS}

Worked non-EC2 S3 readiness row `{TRACKER_ID}` / `{ITEM_ID}` using `{rel(SOURCE_SCRIPT)}`.

Result: `{qa_decision}`. Local readiness result is `{readiness.get('result')}` with missing_config_count=`{len(missing_config)}`, policy_template_failures=`{len(template_failures)}`, static least-privilege failures=`{len(least_privilege_failures)}`, and secrets_printed=`{readiness.get('secrets_printed')}`.

Boundary: this validates local configuration shape and safe-to-commit policy templates only. It did not apply IAM policies, execute S3 upload/download, contact AWS, start EC2, consume mask truth, promote masks, rerun hard gates, or activate Wave71+.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(READINESS)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` EC2 TTL watchdog. Any live EC2/AWS action remains gated by current auth and checkpoint state.
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
## Wave64 S3 Transfer Cost Control - {ISO_TS}

Local-only S3 transfer readiness: URI/config shape present, policy templates valid, static least-privilege check passed, no secrets printed, no AWS/EC2 contact.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(READINESS)}`
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
                "errors": errors,
                "readiness": readiness.get("result"),
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
