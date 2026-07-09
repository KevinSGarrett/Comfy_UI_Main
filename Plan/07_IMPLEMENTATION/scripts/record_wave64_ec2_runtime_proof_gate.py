from __future__ import annotations

import csv
import hashlib
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

TRACKER_ID = "TRK-W64-038"
ITEM_ID = "ITEM-W64-038"
LANE_ID = "sdxl_low_risk_fallback_lane"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

DRY_RUN = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Runtime/W64_EC2_TARGET_RUNTIME_PROOF_DRY_RUN_CURRENT_GATES_20260708T232200-0500.json"
REQUEST = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Runtime/W64_EC2_TARGET_RUNTIME_PROOF_REQUEST_CURRENT_GATES_20260708T232200-0500.json"
AUTH_GATE = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness/W64_AWS_AUTH_GATE_EC2_TARGET_RUNTIME_PROOF_20260708T232100-0500.json"
SOURCE_PLAN = PLAN_ROOT / "07_IMPLEMENTATION/EC2_DEPLOYMENT_AND_RUNTIME_PROOF_PLAN.md"

EVIDENCE = QA_DIR / "ec2_runtime_proof.json"
STAMPED_EVIDENCE = QA_DIR / f"EC2_RUNTIME_PROOF_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"EC2_RUNTIME_PROOF_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        "Ran current-gate EC2 target-runtime proof dry run without starting EC2.",
        "; ".join(payload["evidence_paths"]),
        "AWS auth gate; local Git checkpoint gate; lane JSON contract; readiness gate; static proof gate; prompt request build",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Resolve expired AWS session and local Git checkpoint before any EC2 target-runtime execution.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    dry_run = read_json(DRY_RUN)
    auth_gate = read_json(AUTH_GATE)
    request_exists = REQUEST.exists()
    blocked_reasons = list(dry_run.get("blocked_reasons", [])) if isinstance(dry_run, dict) else []
    local_git = dry_run.get("local_git_checkpoint_gate", {}) if isinstance(dry_run, dict) else {}
    static_proof = dry_run.get("ec2_static_proof", {}) if isinstance(dry_run, dict) else {}
    readiness = dry_run.get("readiness_gate", {}) if isinstance(dry_run, dict) else {}
    smoke_request = dry_run.get("smoke_request", {}) if isinstance(dry_run, dict) else {}

    errors: list[str] = []
    if dry_run.get("lane_id") != LANE_ID:
        errors.append(f"lane_id_mismatch:{dry_run.get('lane_id')}")
    if dry_run.get("mode") != "dry_run":
        errors.append(f"mode_not_dry_run:{dry_run.get('mode')}")
    if dry_run.get("ec2_started") is not False:
        errors.append("ec2_started_unexpectedly")
    if dry_run.get("generation_executed") is not False:
        errors.append("generation_executed_unexpectedly")
    if not request_exists:
        errors.append("target_runtime_prompt_request_missing")
    if not blocked_reasons:
        errors.append("blocked_reasons_missing")

    qa_decision = "blocked_ec2_target_runtime_proof_pre_start_gates" if not errors else "invalid_ec2_target_runtime_gate_record"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"EC2_RUNTIME_PROOF_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "lane_id": LANE_ID,
        "task": "Evaluate EC2 target runtime proof gates without starting EC2.",
        "source_plan": rel(SOURCE_PLAN),
        "dry_run_record": rel(DRY_RUN),
        "prompt_request": {
            "path": rel(REQUEST),
            "exists": request_exists,
            "sha256": sha256(REQUEST) if request_exists else "",
        },
        "aws_auth_gate": {
            "path": rel(AUTH_GATE),
            "result": auth_gate.get("result"),
            "failure_category": auth_gate.get("failure_category"),
            "safe_to_start_ec2": auth_gate.get("safe_to_start_ec2"),
            "generation_allowed": auth_gate.get("generation_allowed"),
            "secrets_printed": auth_gate.get("secrets_printed"),
            "auth_url_recorded": auth_gate.get("auth_url_recorded"),
        },
        "local_git_checkpoint_gate": {
            "result": local_git.get("result"),
            "clean": local_git.get("clean"),
            "local_matches_origin": local_git.get("local_matches_origin"),
            "porcelain_count": local_git.get("porcelain_count"),
            "head": local_git.get("head"),
            "origin_main": local_git.get("origin_main"),
        },
        "lane_readiness_gate": {
            "file": readiness.get("file"),
            "lane_match": readiness.get("lane_match"),
            "ready_for_generation": readiness.get("ready_for_generation"),
            "result": readiness.get("result"),
        },
        "ec2_static_proof_gate": {
            "file": static_proof.get("file"),
            "valid": static_proof.get("valid"),
            "lane_match": static_proof.get("lane_match"),
            "object_info_status": static_proof.get("object_info_status"),
            "model_proof_count": static_proof.get("model_proof_count"),
        },
        "smoke_request_gate": {
            "request_file_exists": smoke_request.get("request_file_exists"),
            "json_parsed": smoke_request.get("json_parsed"),
            "execution_allowed": smoke_request.get("execution_allowed"),
            "errors": smoke_request.get("errors", []),
        },
        "runtime_execution": {
            "ec2_started": dry_run.get("ec2_started"),
            "generation_executed": dry_run.get("generation_executed"),
            "execute_gates_pass": dry_run.get("execute_gates_pass"),
            "result": dry_run.get("result"),
            "failure_category": dry_run.get("failure_category"),
            "blocked_reasons": blocked_reasons,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": "Resolve expired AWS session and local Git checkpoint gate before any EC2 target-runtime execution; continue only with non-EC2 work meanwhile.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(DRY_RUN),
        rel(REQUEST),
        rel(AUTH_GATE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 EC2 target runtime proof gate {STAMP}: result={dry_run.get('result')}; "
        f"failure_category={dry_run.get('failure_category')}; blocked_reasons={blocked_reasons}; "
        f"ec2_started={dry_run.get('ec2_started')}; generation_executed={dry_run.get('generation_executed')}; "
        f"aws_auth={auth_gate.get('result')}/{auth_gate.get('failure_category')}; "
        f"git_clean={local_git.get('clean')} porcelain_count={local_git.get('porcelain_count')}."
    )
    additions = [
        "wave64_ec2_target_runtime_proof_gate_checked",
        qa_decision,
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
## Immediate Next Action - Wave64 EC2 Target Runtime Proof Gate - {ISO_TS}

Worked tracked target-runtime row `{TRACKER_ID}` / `{ITEM_ID}` with a dry-run gate check only. EC2 was not started.

Result: `{qa_decision}`. Current blockers before any EC2 start: `{'; '.join(blocked_reasons)}`.

Current gate facts: AWS auth result `{auth_gate.get('result')}` / `{auth_gate.get('failure_category')}`; local Git checkpoint clean=`{local_git.get('clean')}` with porcelain_count=`{local_git.get('porcelain_count')}`. Lane contract, readiness, EC2 static proof, and prompt request build were present enough for dry-run evaluation.

Runtime boundary: EC2 was not started, no generation ran on EC2, no masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(DRY_RUN)}`
- `{rel(AUTH_GATE)}`

Next exact local action: continue concrete non-EC2 work while AWS auth and local Git checkpoint remain blocked for target-runtime execution.
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
## Wave64 EC2 Target Runtime Proof Gate - {ISO_TS}

Dry-run EC2 target-runtime proof gate for `{LANE_ID}`. EC2 not started; current blockers recorded before any start attempt.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(DRY_RUN)}`
- `{rel(AUTH_GATE)}`
""",
    )
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "tracker_evidence": str(TRACKER_EVIDENCE),
        "qa_decision": qa_decision,
        "blocked_reasons": blocked_reasons,
        "errors": errors,
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
