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

TRACKER_ID = "TRK-W64-046"
ITEM_ID = "ITEM-W64-046"
NEXT_TRACKER_ID = "TRK-W64-047"
NEXT_ITEM_ID = "ITEM-W64-047"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
SECURITY_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Security"

CHECKS = max(SECURITY_DIR.glob("W64_SECRET_GIT_SECURITY_CHECKS_*.json"), key=lambda path: path.stat().st_mtime)
SOURCE_PROTOCOL = PLAN_ROOT / "Instructions/Operations/SECRETS_ENV_HANDLING_PROTOCOL.md"
CHECK_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/run_wave64_secret_git_security_checks.py"
CHECKPOINT_SCRIPT = PLAN_ROOT / "Instructions/Operations/Scripts/Invoke-GitHubCheckpoint.ps1"

EVIDENCE = QA_DIR / "secret_git_security.json"
STAMPED_EVIDENCE = QA_DIR / f"SECRET_GIT_SECURITY_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"SECRET_GIT_SECURITY_{STAMP}.json"

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
        "Recorded secret/Git security scan and exact dirty-worktree checkpoint blocker.",
        "; ".join(payload["evidence_paths"]),
        "secret scan; gitignore check; head equals origin; clean worktree; no binary model commit",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Do not start EC2 until checkpoint blocker is resolved; advance only to safe non-EC2 {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    checks = read_json(CHECKS)
    git = checks["git_checkpoint"]
    blocked = checks["blocked_path_scan"]
    secret = checks["secret_scan"]
    gitignore = checks["gitignore_check"]
    env_presence = checks["env_presence"]

    errors: list[str] = []
    if gitignore.get("pass") is not True:
        errors.append("gitignore_required_patterns_missing")
    if blocked.get("tracked_blocked_count") != 0:
        errors.append(f"tracked_blocked_paths:{blocked.get('tracked_blocked_count')}")
    if blocked.get("staged_blocked_count") != 0:
        errors.append(f"staged_blocked_paths:{blocked.get('staged_blocked_count')}")
    if blocked.get("no_binary_model_commit") is not True:
        errors.append("binary_model_commit_detected")
    if secret.get("tracked_secret_match_count") != 0:
        errors.append(f"tracked_secret_matches:{secret.get('tracked_secret_match_count')}")
    if secret.get("staged_secret_match_count") != 0:
        errors.append(f"staged_secret_matches:{secret.get('staged_secret_match_count')}")
    if git.get("head_equals_origin") is not True:
        errors.append("head_not_equal_origin_main")
    if git.get("clean_worktree") is not True:
        errors.append("worktree_dirty")

    qa_decision = (
        "blocked_secret_git_security_dirty_worktree_checkpoint"
        if errors == ["worktree_dirty"]
        else ("secret_git_security_passed" if not errors else "blocked_secret_git_security")
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"SECRET_GIT_SECURITY_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate secrets, gitignore, Git checkpoint, and blocked binary/model commit safety.",
        "source_protocol": rel(SOURCE_PROTOCOL),
        "check_script": rel(CHECK_SCRIPT),
        "checkpoint_script": rel(CHECKPOINT_SCRIPT),
        "security_check_evidence": evidence_path(CHECKS),
        "secret_handling": {
            "env_exists": env_presence.get("env_exists"),
            "env_example_exists": env_presence.get("env_example_exists"),
            "root_sensitive_files": env_presence.get("root_sensitive_files"),
            "secrets_printed": checks.get("secrets_printed"),
            "tracked_secret_match_count": secret.get("tracked_secret_match_count"),
            "staged_secret_match_count": secret.get("staged_secret_match_count"),
        },
        "gitignore_check": gitignore,
        "blocked_path_scan": blocked,
        "git_checkpoint": git,
        "checkpoint_boundary": {
            "commit_attempted": False,
            "push_attempted": False,
            "cleaned_or_reverted_files": False,
            "ec2_start_allowed": False,
            "blocked_reason": "Worktree is not clean; existing and current changes must be intentionally reviewed/committed or otherwise resolved before EC2 checkpoint gates pass.",
        },
        "runtime_boundary": {
            "ec2_started": False,
            "generation_executed": False,
            "comfyui_contacted": False,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Continue only non-EC2-safe work while dirty-worktree checkpoint remains blocked; next row is {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(CHECKS),
        rel(SOURCE_PROTOCOL),
        rel(CHECK_SCRIPT),
        rel(CHECKPOINT_SCRIPT),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 secret/Git security {STAMP}: gitignore_pass={gitignore.get('pass')} "
        f"tracked_secret_matches={secret.get('tracked_secret_match_count')} staged_secret_matches={secret.get('staged_secret_match_count')} "
        f"tracked_blocked={blocked.get('tracked_blocked_count')} staged_blocked={blocked.get('staged_blocked_count')} "
        f"head_equals_origin={git.get('head_equals_origin')} clean_worktree={git.get('clean_worktree')} "
        f"porcelain_count={git.get('porcelain_count')} tracked_porcelain_count={git.get('tracked_porcelain_count')} decision={qa_decision}."
    )
    additions = [
        "wave64_secret_git_security_checked",
        qa_decision,
        "secret_scan_passed",
        "gitignore_check_passed",
        "head_equals_origin_passed",
        "no_binary_model_commit_passed",
        "clean_worktree_blocked",
        "ec2_not_allowed_until_checkpoint_clean",
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
## Immediate Next Action - Wave64 Secret Git Security - {ISO_TS}

Worked non-EC2 security row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Secret and blocked-path checks passed: tracked_secret_match_count=`{secret.get('tracked_secret_match_count')}`, staged_secret_match_count=`{secret.get('staged_secret_match_count')}`, tracked_blocked_count=`{blocked.get('tracked_blocked_count')}`, staged_blocked_count=`{blocked.get('staged_blocked_count')}`, no_binary_model_commit=`{blocked.get('no_binary_model_commit')}`, and gitignore_pass=`{gitignore.get('pass')}`.

Exact checkpoint blocker: HEAD equals origin/main=`{git.get('head_equals_origin')}`, but clean_worktree=`{git.get('clean_worktree')}` with porcelain_count=`{git.get('porcelain_count')}` and tracked_porcelain_count=`{git.get('tracked_porcelain_count')}`. No commit, push, cleanup, reset, or revert was attempted.

Boundary: do not start EC2 until the checkpoint gate is clean. No EC2, generation, ComfyUI contact, mask truth, mask promotion, hard-gate rerun, or Wave71+ activation occurred.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(CHECKS)}`

Next exact local action: continue only non-EC2-safe work; next row is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
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
## Wave64 Secret Git Security - {ISO_TS}

Secret/Git security checks passed except clean-worktree checkpoint. EC2 remains blocked until checkpoint is clean.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(CHECKS)}`
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
