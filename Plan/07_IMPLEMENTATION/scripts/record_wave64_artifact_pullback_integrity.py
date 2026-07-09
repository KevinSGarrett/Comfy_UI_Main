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

TRACKER_ID = "TRK-W64-043"
ITEM_ID = "ITEM-W64-043"
NEXT_TRACKER_ID = "TRK-W64-044"
NEXT_ITEM_ID = "ITEM-W64-044"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
RUNTIME_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"

PULLBACK_DRY_RUN = max(RUNTIME_DIR.glob("W64_EC2_PULLBACK_RECORD_DRY_RUN_*.json"), key=lambda path: path.stat().st_mtime)
AUTH_GATE = max(RUNTIME_DIR.glob("W64_AWS_AUTH_GATE_EC2_TTL_WATCHDOG_*.json"), key=lambda path: path.stat().st_mtime)
EC2_DRY_RUN = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Runtime/W64_EC2_TARGET_RUNTIME_PROOF_DRY_RUN_CURRENT_GATES_20260708T232200-0500.json"

SOURCE_PROTOCOL = PLAN_ROOT / "Instructions/Operations/EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md"
SOURCE_SCRIPT = PLAN_ROOT / "Instructions/Operations/Scripts/New-EC2PullbackRecord.ps1"

EVIDENCE = QA_DIR / "artifact_pullback_integrity.json"
STAMPED_EVIDENCE = QA_DIR / f"ARTIFACT_PULLBACK_INTEGRITY_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"ARTIFACT_PULLBACK_INTEGRITY_{STAMP}.json"

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


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded artifact pullback dry-run and exact missing-current-runtime-artifact blocker.",
        "; ".join(payload["evidence_paths"]),
        "pullback dry-run; remote manifest requirement; local file count; hash parity boundary; QA follow-up requirement; EC2/auth blocker",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Continue {NEXT_TRACKER_ID} because current artifact pullback requires a future EC2 runtime proof first.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    pullback = read_json(PULLBACK_DRY_RUN)
    auth = read_json(AUTH_GATE)
    ec2_dry_run = read_json(EC2_DRY_RUN) if EC2_DRY_RUN.exists() else {}

    errors: list[str] = []
    if pullback.get("mode") != "dry_run":
        errors.append(f"pullback_mode_unexpected:{pullback.get('mode')}")
    if pullback.get("status") != "pending_runtime_artifacts":
        errors.append(f"pullback_status_unexpected:{pullback.get('status')}")
    if pullback.get("file_count_local") != 0:
        errors.append(f"local_file_count_unexpected:{pullback.get('file_count_local')}")
    if pullback.get("hashes_verified") is not False:
        errors.append("hashes_verified_unexpectedly_true")
    if auth.get("safe_to_start_ec2") is not False:
        errors.append("auth_gate_unexpectedly_safe_to_start_ec2")
    if auth.get("secrets_printed") is not False:
        errors.append("auth_gate_printed_secret_unexpectedly")
    if ec2_dry_run and ec2_dry_run.get("ec2_started") is not False:
        errors.append("ec2_dry_run_started_ec2_unexpectedly")

    qa_decision = (
        "blocked_artifact_pullback_integrity_current_ec2_runtime_artifacts_missing"
        if not errors
        else "invalid_artifact_pullback_integrity_evidence_record"
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"ARTIFACT_PULLBACK_INTEGRITY_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate artifact pullback and hash integrity requirements for the current Wave64 EC2 runtime path.",
        "source_protocol": rel(SOURCE_PROTOCOL),
        "source_script": rel(SOURCE_SCRIPT),
        "pullback_dry_run": {
            "path": evidence_path(PULLBACK_DRY_RUN),
            "run_id": pullback.get("run_id"),
            "mode": pullback.get("mode"),
            "status": pullback.get("status"),
            "file_count_remote": pullback.get("file_count_remote"),
            "file_count_local": pullback.get("file_count_local"),
            "hashes_verified": pullback.get("hashes_verified"),
            "qa_required_files_count": len(pullback.get("qa_required_files", []) or []),
            "errors": pullback.get("errors", []),
        },
        "current_ec2_runtime_dependency": {
            "auth_gate_path": evidence_path(AUTH_GATE),
            "auth_result": auth.get("result"),
            "auth_failure_category": auth.get("failure_category"),
            "safe_to_start_ec2": auth.get("safe_to_start_ec2"),
            "ec2_target_runtime_dry_run": evidence_path(EC2_DRY_RUN) if EC2_DRY_RUN.exists() else "",
            "ec2_target_runtime_result": ec2_dry_run.get("result"),
            "ec2_target_runtime_failure_category": ec2_dry_run.get("failure_category"),
            "ec2_started": ec2_dry_run.get("ec2_started") if ec2_dry_run else False,
            "generation_executed": ec2_dry_run.get("generation_executed") if ec2_dry_run else False,
        },
        "integrity_gate": {
            "remote_manifest_available": pullback.get("file_count_remote") is not None,
            "local_artifacts_available": (pullback.get("file_count_local") or 0) > 0,
            "remote_local_count_match": False,
            "sha256_match": False,
            "qa_record_required": True,
            "qa_record_complete": False,
            "blocker_reason": "No current EC2 runtime artifact set exists because target runtime execution is blocked before EC2 start.",
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} model registry governance; do not rerun pullback until a current EC2 runtime proof produces artifacts.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(PULLBACK_DRY_RUN),
        evidence_path(AUTH_GATE),
        evidence_path(EC2_DRY_RUN) if EC2_DRY_RUN.exists() else "",
        rel(SOURCE_PROTOCOL),
        rel(SOURCE_SCRIPT),
    ]
    payload["evidence_paths"] = [path for path in payload["evidence_paths"] if path]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 artifact pullback integrity {STAMP}: pullback_status={pullback.get('status')} "
        f"mode={pullback.get('mode')} local_files={pullback.get('file_count_local')} remote_files={pullback.get('file_count_remote')} "
        f"hashes_verified={pullback.get('hashes_verified')}; auth={auth.get('result')}/{auth.get('failure_category')}; "
        f"current_ec2_artifacts_missing=True; decision={qa_decision}."
    )
    additions = [
        "wave64_artifact_pullback_integrity_checked",
        qa_decision,
        "pullback_dry_run_recorded",
        "current_ec2_runtime_artifacts_missing",
        "remote_manifest_missing_for_current_run",
        "hash_parity_blocked",
        "qa_record_blocked_until_artifacts_exist",
        "ec2_not_started",
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
## Immediate Next Action - Wave64 Artifact Pullback Integrity - {ISO_TS}

Worked artifact pullback row `{TRACKER_ID}` / `{ITEM_ID}` using a local dry-run only.

Result: `{qa_decision}`. Pullback dry-run status is `{pullback.get('status')}` with local file count `{pullback.get('file_count_local')}`, remote file count `{pullback.get('file_count_remote')}`, and hashes_verified=`{pullback.get('hashes_verified')}`.

Exact blocker: no current EC2 runtime artifact set exists because target runtime execution is still blocked before EC2 start (`{auth.get('result')}` / `{auth.get('failure_category')}`). Therefore no remote manifest, local pullback count parity, SHA256 parity, or pulled-back artifact QA record can honestly pass.

Boundary: do not rerun pullback until a current EC2 runtime proof produces artifacts. No EC2 was started here, no masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(PULLBACK_DRY_RUN)}`
- `{evidence_path(AUTH_GATE)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` model registry governance, a non-EC2 row.
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
## Wave64 Artifact Pullback Integrity - {ISO_TS}

Current-run artifact pullback integrity is blocked because no current EC2 runtime artifact set exists. Dry-run pullback record preserved.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(PULLBACK_DRY_RUN)}`
- `{evidence_path(AUTH_GATE)}`
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
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
