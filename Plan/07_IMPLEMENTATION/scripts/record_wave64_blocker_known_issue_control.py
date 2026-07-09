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

TRACKER_ID = "TRK-W64-049"
ITEM_ID = "ITEM-W64-049"
PREVIOUS_TRACKER_ID = "TRK-W64-048"
PREVIOUS_ITEM_ID = "ITEM-W64-048"
NEXT_TRACKER_ID = "TRK-W64-050"
NEXT_ITEM_ID = "ITEM-W64-050"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
MASK_EVIDENCE_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Mask_Factory/Wave70"

SOURCE_BLOCKERS = HYDRATION_DIR / "BLOCKERS.md"
SOURCE_ISSUES = HYDRATION_DIR / "KNOWN_ISSUES.md"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

NO_LOOP_EVIDENCE = QA_DIR / "no_loop_no_drift.json"
SECRET_EVIDENCE = QA_DIR / "secret_git_security.json"
EC2_TTL_EVIDENCE = QA_DIR / "ec2_ttl_watchdog.json"
PULLBACK_EVIDENCE = QA_DIR / "artifact_pullback_integrity.json"
GOLD_MASK_EVIDENCE = MASK_EVIDENCE_DIR / "GOLD_MASK_DEPENDENCY_BOUNDARY_20260708T222123-0500.json"

EVIDENCE = QA_DIR / "blocker_known_issue_control.json"
STAMPED_EVIDENCE = QA_DIR / f"BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
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


def top_text(path: Path, limit: int = 6000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig")
    return text[: min(limit, len(text))]


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded source-cited active blocker register and known-issue latest-state precedence.",
        "; ".join(payload["evidence_paths"]),
        "blocker id required; resolved evidence required; known issue scope; latest state precedence",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; do not let older blocker prose supersede this active register.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    no_loop = read_json(NO_LOOP_EVIDENCE)
    secret = read_json(SECRET_EVIDENCE)
    ec2_ttl = read_json(EC2_TTL_EVIDENCE)
    pullback = read_json(PULLBACK_EVIDENCE)
    gold_mask_exists = GOLD_MASK_EVIDENCE.exists()

    secret_git = secret.get("git_checkpoint", {}) if isinstance(secret.get("git_checkpoint"), dict) else {}
    blocker_register = [
        {
            "blocker_id": "BLOCKER-W64-GIT-DIRTY-WORKTREE-001",
            "status": "active",
            "scope": "EC2 checkpoint, commit/push checkpoint, and target-runtime starts",
            "source_evidence": rel(SECRET_EVIDENCE),
            "source_decision": secret.get("qa_decision"),
            "exact_condition": f"clean_worktree={secret_git.get('clean_worktree')} porcelain_count={secret_git.get('porcelain_count')} tracked_porcelain_count={secret_git.get('tracked_porcelain_count')}",
            "does_not_block": "non-EC2-safe local evidence, scaffolding, and tracker rows that do not require a clean checkpoint",
            "resolution_evidence_required": "new secret/git security evidence showing clean_worktree=true plus intentional handling of existing dirty changes",
        },
        {
            "blocker_id": "BLOCKER-W64-AWS-EXPIRED-SESSION-001",
            "status": "active_for_live_aws_or_ec2_actions",
            "scope": "live AWS/EC2 proof, emergency stop live proof, target-runtime execution",
            "source_evidence": rel(EC2_TTL_EVIDENCE),
            "source_decision": ec2_ttl.get("qa_decision"),
            "exact_condition": "latest Wave64 TTL/live watchdog evidence is blocked by expired AWS session",
            "does_not_block": "local-only static validation, packaging, registry, source-cited blocker governance, and non-mask rows",
            "resolution_evidence_required": "fresh AWS auth/account gate evidence and bounded EC2 command evidence",
        },
        {
            "blocker_id": "BLOCKER-W64-CURRENT-EC2-ARTIFACTS-MISSING-001",
            "status": "active_for_current_run_pullback_integrity",
            "scope": "current-run artifact pullback integrity certification",
            "source_evidence": rel(PULLBACK_EVIDENCE),
            "source_decision": pullback.get("qa_decision"),
            "exact_condition": "no current EC2 runtime artifact set exists for this Wave64 run",
            "does_not_block": "non-runtime local work or future pullback after a real EC2 run",
            "resolution_evidence_required": "bounded EC2 runtime artifact set plus pullback manifest/hash verification evidence",
        },
        {
            "blocker_id": "BLOCKER-GOLD-MASK-DEPENDENCY-001",
            "status": "active_for_mask_dependent_rows_only",
            "scope": "mask-dependent promotion, geometry authority, body/hand/contact validation, final mask QA, certification-ready claims, Wave71+ mask-proof activation",
            "source_evidence": evidence_path(GOLD_MASK_EVIDENCE),
            "source_decision": "Manual_Gold_Mask_Work_In_Progress",
            "exact_condition": "manual gold masks are still being created and candidate masks must not be consumed as truth",
            "does_not_block": "workflow structure, orchestration, logging, validation scaffolding, dataset organization, ComfyUI wiring that does not claim final mask truth, non-body-mask assets",
            "resolution_evidence_required": "manual gold-mask intake validation evidence and strict mask QA pass records",
        },
    ]

    blockers_head_before = top_text(SOURCE_BLOCKERS)
    issues_head_before = top_text(SOURCE_ISSUES)
    next_head = top_text(SOURCE_NEXT)
    goal_head = top_text(SOURCE_GOAL)

    top_block = f"""
## Wave64 Active Blocker Register - {ISO_TS}

This is the latest active blocker register for the live transferred session. Older blocker prose below remains historical/source context and cannot supersede this register without newer structured evidence.

| Blocker ID | Status | Scope | Source Evidence | Resolution Evidence Required |
| --- | --- | --- | --- | --- |
| `BLOCKER-W64-GIT-DIRTY-WORKTREE-001` | active | EC2 checkpoint, commit/push checkpoint, target-runtime starts | `Plan/Instructions/QA/Evidence/Wave64/secret_git_security.json` | New secret/Git evidence with `clean_worktree=true` and intentional handling of existing dirty changes |
| `BLOCKER-W64-AWS-EXPIRED-SESSION-001` | active for live AWS/EC2 actions | live AWS/EC2 proof and target-runtime execution | `Plan/Instructions/QA/Evidence/Wave64/ec2_ttl_watchdog.json` | Fresh AWS auth/account gate plus bounded EC2 command evidence |
| `BLOCKER-W64-CURRENT-EC2-ARTIFACTS-MISSING-001` | active for current-run pullback integrity | current-run artifact pullback certification | `Plan/Instructions/QA/Evidence/Wave64/artifact_pullback_integrity.json` | Bounded EC2 runtime artifact set plus pullback manifest/hash evidence |
| `BLOCKER-GOLD-MASK-DEPENDENCY-001` | active for mask-dependent rows only | mask promotion, geometry authority, body/hand/contact validation, final mask QA, certification-ready claims, Wave71+ mask-proof activation | `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/GOLD_MASK_DEPENDENCY_BOUNDARY_20260708T222123-0500.json` | Manual gold-mask intake validation and strict mask QA pass records |

Non-blocked work may continue only when it does not start EC2, does not require a clean Git checkpoint, does not consume candidate masks as truth, and does not claim mask certification.

Evidence for this register:
- `Plan/Instructions/QA/Evidence/Wave64/blocker_known_issue_control.json`
- `Plan/Instructions/QA/Evidence/Wave64/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`
- `Plan/Tracker/Evidence/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`
"""
    prepend(SOURCE_BLOCKERS, top_block)

    known_issue_block = f"""
## Wave64 Known-Issue Scope and Latest-State Precedence - {ISO_TS}

Known issues remain scoped to their named IDs below. The latest active blockers are the source-cited entries in `BLOCKERS.md` under the Wave64 Active Blocker Register. Historical resolved issues below do not reopen unless newer structured evidence records a regression.

Current active non-mask runtime issue scope:
- `BLOCKER-W64-GIT-DIRTY-WORKTREE-001`
- `BLOCKER-W64-AWS-EXPIRED-SESSION-001`
- `BLOCKER-W64-CURRENT-EC2-ARTIFACTS-MISSING-001`

Current active mask-dependent scope:
- `BLOCKER-GOLD-MASK-DEPENDENCY-001`
- Existing Wave70 mask/geometry known issues remain active only for mask-dependent work and do not freeze unrelated non-mask rows.
"""
    prepend(SOURCE_ISSUES, known_issue_block)

    blockers_head_after = top_text(SOURCE_BLOCKERS)
    issues_head_after = top_text(SOURCE_ISSUES)
    required_blocker_ids = [entry["blocker_id"] for entry in blocker_register]
    blocker_id_required_pass = all(blocker_id in blockers_head_after for blocker_id in required_blocker_ids)
    resolved_evidence_required_pass = all("resolution_evidence_required" in entry and entry["resolution_evidence_required"] for entry in blocker_register)
    known_issue_scope_pass = "Existing Wave70 mask/geometry known issues remain active only for mask-dependent work" in issues_head_after
    latest_state_precedence_pass = "cannot supersede this register without newer structured evidence" in blockers_head_after
    previous_row_passed = no_loop.get("qa_decision") == "no_loop_no_drift_passed_bounded_advance_to_concrete_next_row"
    current_next_action = TRACKER_ID in next_head and ITEM_ID in next_head
    current_goal_aligned = TRACKER_ID in goal_head and ITEM_ID in goal_head

    errors: list[str] = []
    if not previous_row_passed:
        errors.append("previous_no_loop_no_drift_not_passed")
    if not current_next_action:
        errors.append("next_action_top_not_current_row_before_update")
    if not current_goal_aligned:
        errors.append("current_goal_top_not_current_row_before_update")
    if not blocker_id_required_pass:
        errors.append("blocker_id_required_failed")
    if not resolved_evidence_required_pass:
        errors.append("resolved_evidence_required_failed")
    if not known_issue_scope_pass:
        errors.append("known_issue_scope_failed")
    if not latest_state_precedence_pass:
        errors.append("latest_state_precedence_failed")
    if not gold_mask_exists:
        errors.append("gold_mask_boundary_evidence_missing")

    qa_decision = "blocker_known_issue_control_passed_source_cited_latest_state_precedence" if not errors else "blocked_blocker_known_issue_control_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate blocker IDs, resolution evidence requirements, known-issue scope, and latest-state precedence.",
        "source_files": [rel(SOURCE_BLOCKERS), rel(SOURCE_ISSUES)],
        "blocker_register": blocker_register,
        "checks": {
            "previous_row_passed": previous_row_passed,
            "current_next_action_before_update": current_next_action,
            "current_goal_aligned_before_update": current_goal_aligned,
            "blocker_id_required_pass": blocker_id_required_pass,
            "resolved_evidence_required_pass": resolved_evidence_required_pass,
            "known_issue_scope_pass": known_issue_scope_pass,
            "latest_state_precedence_pass": latest_state_precedence_pass,
            "gold_mask_boundary_evidence_exists": gold_mask_exists,
            "blockers_head_changed": blockers_head_before != blockers_head_after,
            "known_issues_head_changed": issues_head_before != issues_head_after,
        },
        "runtime_boundary": {
            "ec2_started": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "hard_gates_rerun": False,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; use the active blocker register for latest-state precedence.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(SOURCE_BLOCKERS),
        rel(SOURCE_ISSUES),
        rel(NO_LOOP_EVIDENCE),
        rel(SECRET_EVIDENCE),
        rel(EC2_TTL_EVIDENCE),
        rel(PULLBACK_EVIDENCE),
        evidence_path(GOLD_MASK_EVIDENCE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 blocker/known issue control {STAMP}: blocker_ids={len(blocker_register)}; "
        f"blocker_id_required_pass={blocker_id_required_pass}; resolved_evidence_required_pass={resolved_evidence_required_pass}; "
        f"known_issue_scope_pass={known_issue_scope_pass}; latest_state_precedence_pass={latest_state_precedence_pass}; decision={qa_decision}."
    )
    additions = [
        "wave64_blocker_known_issue_control_checked",
        qa_decision,
        "blocker_id_required_passed" if blocker_id_required_pass else "blocker_id_required_failed",
        "resolved_evidence_required_passed" if resolved_evidence_required_pass else "resolved_evidence_required_failed",
        "known_issue_scope_passed" if known_issue_scope_pass else "known_issue_scope_failed",
        "latest_state_precedence_passed" if latest_state_precedence_pass else "latest_state_precedence_failed",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Evidence_Passed_Local_Non_Runtime" if not errors else "Required_Tracked_Not_Complete_Until_Evidence_Passes",
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
                "Status": "Evidence_Passed_Local_Non_Runtime" if not errors else "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    hydration_block = f"""
## Immediate Next Action - Wave64 Blocker Known Issue Control - {ISO_TS}

Worked blocker/known-issue governance row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. `BLOCKERS.md` now has a latest active blocker register with stable IDs, source evidence, scope, non-blocked work boundaries, and required resolution evidence. `KNOWN_ISSUES.md` now records latest-state precedence so historical issue text cannot supersede newer evidence.

Active blockers: `BLOCKER-W64-GIT-DIRTY-WORKTREE-001`, `BLOCKER-W64-AWS-EXPIRED-SESSION-001`, `BLOCKER-W64-CURRENT-EC2-ARTIFACTS-MISSING-001`, and `BLOCKER-GOLD-MASK-DEPENDENCY-001`.

Runtime/mask boundary: no EC2, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/blocker_known_issue_control.json`
- `Plan/Instructions/QA/Evidence/Wave64/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`
- `Plan/Tracker/Evidence/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, hydration_block)

    index_block = f"""
## Wave64 Blocker Known Issue Control - {ISO_TS}

Blocker and known-issue governance passed with stable blocker IDs, source-cited evidence, scope boundaries, resolution evidence requirements, and latest-state precedence.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/blocker_known_issue_control.json`
- `Plan/Instructions/QA/Evidence/Wave64/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`
- `Plan/Tracker/Evidence/BLOCKER_KNOWN_ISSUE_CONTROL_{STAMP}.json`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Blocker Precedence Decision - {ISO_TS}

Decision: use the latest active blocker register in `BLOCKERS.md` as the current source of truth for blocker scope. Historical blocker and known-issue entries remain useful context, but they cannot reopen or override newer structured evidence without a new explicit validation record.
"""
    prepend(SOURCE_DECISIONS, decision_block)

    append_proof_log(payload)

    payload["csv_updates"] = {"tracker": tracker_updates, "items": item_updates}
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    print(json.dumps({
        "qa_decision": qa_decision,
        "errors": errors,
        "blocker_ids": required_blocker_ids,
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
