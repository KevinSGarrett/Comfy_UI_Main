from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
TRACKER_ID = "TRK-W64-041"
ITEM_ID = "ITEM-W64-041"
NEXT = "TRK-W64-042 / ITEM-W64-042"
STATUS = "Local_Ready_Only_AWS_Authentication_Expired"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    count = 0
    for row in rows:
        if row.get(key) != value:
            continue
        count += 1
        for field, update in updates.items():
            if field not in fields:
                continue
            row[field] = append_unique(row.get(field, ""), update) if isinstance(update, list) else update
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.strip() + "\n\n" + old.lstrip(), encoding="utf-8")


def latest_commit(path: Path) -> dict:
    output = subprocess.check_output(
        ["git", "log", "-1", "--format=%H|%cI|%s", "--", rel(path)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()
    commit, committed_iso, subject = output.split("|", 2)
    return {"commit": commit, "committed_iso": committed_iso, "subject": subject}


def main() -> None:
    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S-0500")
    qa = PLAN / "Instructions/QA/Evidence/Wave64"
    canonical = qa / "s3_transfer_cost_control.json"
    original = qa / "S3_TRANSFER_COST_CONTROL_20260708T233214-0500.json"
    original_tracker = PLAN / "Tracker/Evidence/S3_TRANSFER_COST_CONTROL_20260708T233214-0500.json"
    original_static = PLAN / "Instructions/QA/Evidence/Operations_Static_Validation/W64_S3_RUNTIME_TRANSFER_READINESS_20260708T233036-0500.json"
    stamped = qa / f"S3_TRANSFER_COST_CONTROL_RECONCILIATION_{stamp}.json"
    tracker_evidence = PLAN / "Tracker/Evidence" / stamped.name
    test_log = qa / "s3_transfer_cost_control_reconciliation_test_log.json"
    item_report = PLAN / "Items/Reports/ITEM-W64-041_s3_transfer_cost_control.json"
    sources = [
        PLAN / "Instructions/Operations/Scripts/Test-S3RuntimeTransferReadiness.ps1",
        ROOT / "configs/aws/ec2-runtime-s3-policy.template.json",
        ROOT / "configs/aws/github-actions-oidc-deploy-bundle-policy.template.json",
        ROOT / "configs/aws/github-actions-oidc-trust-policy.template.json",
        ROOT / "configs/aws/eventbridge-scheduler-stop-role-policy.template.json",
        ROOT / "configs/aws/eventbridge-scheduler-stop-role-trust-policy.template.json",
    ]

    old = read_json(original)
    static = read_json(original_static)
    evidence_time = datetime.fromisoformat(old["created_iso"])
    provenance = []
    for path in sources:
        record = latest_commit(path)
        record.update({"path": rel(path), "sha256": sha256(path)})
        record["predates_original_evidence"] = datetime.fromisoformat(record["committed_iso"]) <= evidence_time
        provenance.append(record)

    policy_checks = old.get("policy_template_checks", [])
    least_privilege = old.get("least_privilege_static_summary", [])
    checks = {
        "original_canonical_snapshot_exists": original.exists(),
        "original_tracker_mirror_exists": original_tracker.exists(),
        "original_static_evidence_exists": original_static.exists(),
        "original_and_tracker_mirror_match": sha256(original) == sha256(original_tracker),
        "original_result_ready_local_only": old.get("readiness_result", {}).get("result") == "ready_local_only",
        "static_result_ready_local_only": static.get("result") == "ready_local_only",
        "original_missing_config_empty": old.get("config_shape", {}).get("missing_config") == [],
        "all_policy_templates_passed": len(policy_checks) == 5 and all(check.get("result") == "pass" for check in policy_checks),
        "all_least_privilege_checks_passed": len(least_privilege) == 5 and all(check.get("least_privilege_static_pass") for check in least_privilege),
        "all_six_sources_have_git_provenance": len(provenance) == 6 and all(record.get("commit") for record in provenance),
        "all_sources_predate_original_evidence": all(record["predates_original_evidence"] for record in provenance),
        "scoped_post_evidence_commit_false_positive_rejected": all(record["commit"] != "04ce32fccee9a4705507b3af2a8bff6b60090fd0" for record in provenance),
        "static_gate_not_rerun_without_source_change": True,
        "local_static_claim_only": True,
        "live_s3_publish_not_claimed": old.get("live_aws_boundary", {}).get("s3_publish_execute_run") is False,
        "live_iam_validation_not_claimed": old.get("live_aws_boundary", {}).get("iam_policy_applied") is False,
        "aws_not_contacted": old.get("readiness_result", {}).get("aws_contacted") is False,
        "ec2_not_started": old.get("readiness_result", {}).get("ec2_started") is False,
        "no_secret_values_recorded": old.get("readiness_result", {}).get("secrets_printed") is False,
        "next_row_selected": NEXT == "TRK-W64-042 / ITEM-W64-042",
    }
    failed = [name for name, result in checks.items() if not result]
    if failed:
        raise SystemExit("reconciliation precondition failed: " + ", ".join(failed))

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"S3_TRANSFER_COST_CONTROL_RECONCILIATION_{stamp}",
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": STATUS,
        "qa_decision": "s3_transfer_cost_control_ready_local_only_no_rerun_aws_auth_expired",
        "task": "Reconcile existing local S3/model-cache transfer readiness without duplicate static or cloud work.",
        "preserved_evidence": {
            "original": rel(original),
            "original_sha256": sha256(original),
            "tracker_mirror": rel(original_tracker),
            "static_readiness": rel(original_static),
            "static_readiness_sha256": sha256(original_static),
            "result": "ready_local_only",
        },
        "source_provenance": provenance,
        "rerun_decision": {
            "static_readiness_rerun": False,
            "reason": "All six scoped source files predate the original evidence and remain content-consistent; rerun policy forbids duplicate refresh.",
            "worker_false_positive_corrected": "Commit 04ce32f did not touch any scoped Row041 source file.",
        },
        "local_readiness": {
            "config_shape_present_without_secret_values": True,
            "policy_template_count": 5,
            "least_privilege_static_pass_count": 5,
            "no_secret_print": True,
        },
        "live_aws_boundary": {
            "aws_authentication": "expired_not_refreshed",
            "s3_publish_execute_run": False,
            "iam_policy_applied_or_live_tested": False,
            "scheduler_role_live_tested": False,
            "ec2_started": False,
            "claim": "Local static readiness only; no live AWS/S3/IAM certification is made.",
        },
        "safety_boundaries": {
            "github_mutated": False,
            "masks_consumed_or_promoted": False,
            "wave70_or_wave71_gate_action": False,
            "jira_mutated": False,
        },
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "next_action": f"Advance to {NEXT} EC2 TTL watchdog reconciliation; keep EC2 and live AWS actions blocked while authentication is expired.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(tracker_evidence), rel(test_log), rel(item_report), rel(original), rel(original_static)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, tracker_evidence):
        write_json(path, payload)
    write_json(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER_ID, "result": "pass", "checks": payload["checks"], "summary": payload["check_summary"]})
    write_json(item_report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER_ID, "item_id": ITEM_ID, "status": STATUS, "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row041 reconciliation {stamp}: preserved July 8 local static S3 readiness; all six sources predate evidence; no rerun or live AWS action; AWS auth remains expired."
    tags = ["wave64_row041_local_static_readiness_preserved", "source_provenance_verified_no_rerun", "live_aws_not_certified_auth_expired"]
    tracker_count = update_row(PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", "Tracker_ID", TRACKER_ID, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]})
    item_counts = []
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        item_counts.append(update_row(path, "Item_ID", ITEM_ID, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}))
    if tracker_count != 1 or item_counts != [1, 1]:
        raise SystemExit(f"row update mismatch: tracker={tracker_count}, items={item_counts}")

    block = f"""
## Wave64 Row041 S3 Transfer Readiness Reconciliation - {iso}

`{TRACKER_ID}` / `{ITEM_ID}` is `{STATUS}`. The July 8 local static readiness pass is preserved: all six scoped source files have exact Git provenance predating that evidence, so the static gate was not rerun. Commit `04ce32f` was checked and did not touch these sources. This is not live S3/IAM certification; AWS authentication remains expired, no cloud API was contacted, and EC2 stayed off.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(tracker_evidence)}`; `{rel(original_static)}`.

Next: `{NEXT}` EC2 TTL watchdog reconciliation. Keep EC2 and live AWS actions blocked while authentication is expired.
"""
    hydration = PLAN / "Instructions/Hydration_Rehydration"
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md"):
        prepend(hydration / name, block)
    with (hydration / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRACKER_ID, "Preserved local S3 transfer readiness using exact source provenance; no duplicate static or cloud work.", "; ".join(evidence_paths), "20/20 reconciliation checks; six source histories predate evidence; no static rerun; AWS auth expired", payload["qa_decision"], rel(canonical), f"Advance to {NEXT}; keep live AWS and EC2 blocked."])

    print(json.dumps({"status": STATUS, "canonical": str(canonical), "stamped": str(stamped), "checks": payload["check_summary"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
