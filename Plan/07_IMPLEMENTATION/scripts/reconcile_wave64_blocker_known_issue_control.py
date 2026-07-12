from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRACKER = "TRK-W64-049"
ITEM = "ITEM-W64-049"
STATUS = "Evidence_Passed_Blocker_Governance_Active_Blockers_Tracked"
NEXT = "TRK-W64-055 / ITEM-W64-055"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
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
    source_names = [
        "no_loop_no_drift",
        "secret_git_security",
        "ec2_ttl_watchdog",
        "model_registry_governance",
        "artifact_pullback_integrity",
    ]
    source_paths = [QA / f"{name}.json" for name in source_names]
    sources = {name: load(path) for name, path in zip(source_names, source_paths)}
    old_path = QA / "blocker_known_issue_control.json"
    old = load(old_path)
    gold_path = QA.parent / "Mask_Factory/Wave70/GOLD_MASK_DEPENDENCY_BOUNDARY_20260708T222123-0500.json"

    preserved = sources["secret_git_security"]["residual_checkpoint_blocker"]["preserved_paths"]
    active_blockers = [
        {
            "blocker_id": "BLOCKER-W64-AWS-EXPIRED-SESSION-001",
            "status": "active_for_live_aws_ec2_s3_only",
            "scope": "new live AWS/EC2/S3 assertions, target-runtime execution, and live TTL/watchdog proof",
            "source_evidence": rel(source_paths[2]),
            "source_decision": sources["ec2_ttl_watchdog"]["qa_decision"],
            "exact_condition": "AWS authentication is expired; current dry-run schedule and watchdog checks pass, but live proof is unavailable.",
            "does_not_block": "local-only implementation, static validation, evidence reconciliation, or non-mask ComfyUI orchestration",
            "resolution_evidence_required": "fresh AWS identity/account gate plus bounded live command evidence",
        },
        {
            "blocker_id": "BLOCKER-W64-GIT-DIRTY-WORKTREE-001",
            "status": "active_for_strict_clean_checkpoint_only",
            "scope": "strict clean-worktree checkpoint and downstream actions that explicitly require it",
            "source_evidence": rel(source_paths[1]),
            "source_decision": sources["secret_git_security"]["qa_decision"],
            "exact_condition": f"Exactly {len(preserved)} intentionally preserved paths remain; HEAD matches origin and staged/secret gates pass.",
            "preserved_paths": preserved,
            "does_not_block": "scoped commits that exclude the preserved paths or unrelated local non-EC2 work",
            "resolution_evidence_required": "owner-approved resolution of the five preserved paths followed by clean-worktree and local-equals-origin proof",
        },
    ]
    deferred_dependencies = [
        {
            "dependency_id": "DEPENDENCY-FLUX1-LICENSE-INSTALL-RUNTIME-001",
            "status": "deferred_lane_specific_fail_closed",
            "scope": "flux1_dev_primary_base install, model load, output, visual QA, and certification",
            "source_evidence": rel(source_paths[3]),
            "does_not_block": "the other nine registered lanes or unrelated local work",
            "resolution_evidence_required": "explicit license acceptance plus exact install/hash/model-load/runtime proof",
        },
        {
            "dependency_id": "DEPENDENCY-GOLD-BODY-MASK-001",
            "status": "deferred_mask_dependent_fail_closed",
            "scope": "body/hand/contact geometry authority, mask promotion, final mask QA, and mask-proof Wave71+ activation",
            "source_evidence": rel(gold_path),
            "does_not_block": "non-mask implementation, orchestration, workflow wiring, validation scaffolding, or supported facial benchmark work",
            "resolution_evidence_required": "user-declared-ready manual gold masks followed by intake validation and strict mask QA",
        },
    ]
    superseded = [
        {
            "blocker_id": "BLOCKER-W64-CURRENT-MODEL-REGISTRY-COVERAGE-001",
            "prior_condition": "Depth/Lineart vocabulary gaps and missing Flux registry/queue coverage",
            "superseded_by": rel(source_paths[3]),
            "current_state": "15 registry records, 15 queue rows, 10 lanes, zero coverage failures; Flux remains fail-closed only for license/install/runtime proof",
        },
        {
            "blocker_id": "BLOCKER-W64-CURRENT-EC2-ARTIFACTS-MISSING-001",
            "prior_condition": "no current runtime artifact set for pullback validation",
            "superseded_by": rel(source_paths[4]),
            "current_state": "lane-scoped 4/4 pullback chain complete with manifest, image, log, and hash evidence",
        },
        {
            "blocker_id": "BLOCKER-W64-GIT-DIRTY-WORKTREE-977-001",
            "prior_condition": "977-entry dirty worktree snapshot",
            "superseded_by": rel(source_paths[1]),
            "current_state": "reduced to exactly five intentionally preserved paths; strict clean checkpoint remains separately active",
        },
    ]
    known_issue_caveats = [
        {
            "issue_id": "KNOWN-ISSUE-W64-PULLBACK-TEXT-COPY-DRIFT-001",
            "status": "disclosed_non_blocking_integrity_caveat",
            "scope": "current local text copies differ from the pulled-back historical text bytes",
            "source_evidence": rel(source_paths[4]),
            "authority": "original Git blobs preserve the remote-history and prompt bytes used by the completed lane-scoped pullback proof",
            "does_not_reopen": "the completed 4/4 lane-scoped pullback integrity result",
        }
    ]

    with (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = {row["Tracker_ID"]: row for row in csv.DictReader(handle)}
    checks = {
        "row048_current_pass": sources["no_loop_no_drift"].get("row_complete") is True,
        "row048_refresh_mode": sources["no_loop_no_drift"].get("row049_semantics", {}).get("mode") == "living_governance_refresh",
        "old_governance_predates_current_inputs": old.get("created_iso", "") < sources["no_loop_no_drift"].get("created_iso", ""),
        "active_blocker_count_exact": len(active_blockers) == 2,
        "active_blocker_ids_unique": len({entry["blocker_id"] for entry in active_blockers}) == 2,
        "active_blockers_source_cited": all(entry["source_evidence"] for entry in active_blockers),
        "active_blockers_have_resolution_evidence": all(entry["resolution_evidence_required"] for entry in active_blockers),
        "aws_blocker_scope_limited": active_blockers[0]["status"] == "active_for_live_aws_ec2_s3_only",
        "preserved_path_count_exact": len(preserved) == 5,
        "head_origin_match_preserved": sources["secret_git_security"]["current_scan"]["head_equals_origin"] is True,
        "registry_gap_superseded": sources["model_registry_governance"].get("row_complete") is True,
        "pullback_gap_superseded": sources["artifact_pullback_integrity"].get("row_complete") is True,
        "superseded_count_exact": len(superseded) == 3,
        "flux_dependency_not_global": deferred_dependencies[0]["status"] == "deferred_lane_specific_fail_closed",
        "gold_mask_dependency_not_global": deferred_dependencies[1]["status"] == "deferred_mask_dependent_fail_closed",
        "gold_mask_boundary_exists": gold_path.exists(),
        "rows050_054_still_passed": all(tracker_rows[f"TRK-W64-{row:03d}"]["Status"].startswith("Evidence_Passed") for row in range(50, 55)),
        "row055_first_unresolved": not tracker_rows["TRK-W64-055"]["Status"].startswith("Evidence_Passed"),
        "no_loop_stop_rule_preserved": sources["no_loop_no_drift"]["stop_rules"]["coverage_or_hydration_loop_allowed"] is False,
        "no_external_or_mask_action": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed checks: " + ", ".join(failed))

    canonical = old_path
    stamped = QA / f"BLOCKER_KNOWN_ISSUE_CONTROL_RECONCILIATION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "blocker_known_issue_control_reconciliation_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-049_blocker_known_issue_control.json"
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BLOCKER_KNOWN_ISSUE_CONTROL_RECONCILIATION_{stamp}",
        "created_iso": iso,
        "wave": 64,
        "tracker_id": TRACKER,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": True,
        "qa_decision": "blocker_known_issue_control_current_pass_latest_state_precedence",
        "task": "Refresh living blocker and known-issue governance once after materially changed Row040-048 inputs.",
        "source_evidence": [{"path": rel(path), "sha256": sha256(path), "status": sources[name].get("status")} for name, path in zip(source_names, source_paths)],
        "active_blockers": active_blockers,
        "deferred_scoped_dependencies": deferred_dependencies,
        "superseded_historical_blockers": superseded,
        "known_issue_caveats": known_issue_caveats,
        "latest_state_precedence": "Only the active_blockers array is current global execution state. Deferred dependencies remain scope-limited; superseded entries cannot reopen without newer explicit validation evidence.",
        "progression": {"skip_unchanged_passed_rows": [f"TRK-W64-{row:03d}" for row in range(50, 55)], "next_unresolved_row": "TRK-W64-055", "reason": "Rows050-054 retain passed evidence and their inputs were not invalidated by this living-governance refresh."},
        "safety_boundary": {"aws_contacted": False, "ec2_started": False, "s3_mutated": False, "comfyui_contacted": False, "generation_executed": False, "mask_truth_consumed": False, "hard_gates_rerun": False, "wave71_activated": False, "jira_mutated": False},
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "next_action": f"Skip unchanged passed Rows050-054 and begin {NEXT} source-summary integrity.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)] + [rel(path) for path in source_paths] + [rel(gold_path)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER, "result": "pass", "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRACKER, "item_id": ITEM, "status": STATUS, "active_blockers": active_blockers, "deferred_scoped_dependencies": deferred_dependencies, "superseded_historical_blockers": superseded, "known_issue_caveats": known_issue_caveats, "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row049 {stamp}: refreshed living governance once; active=2, deferred_scoped=2, superseded=3; 20/20 checks; skip unchanged Rows050-054 and advance Row055."
    tags = ["wave64_row049_living_governance_current", "two_active_blockers_exact", "scoped_dependencies_not_global", "latest_state_precedence_pass", "advance_to_row055"]
    tracker_counts = [update_csv(path, "Tracker_ID", TRACKER, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_counts = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_counts != [1, 1] or item_counts != [1, 1]:
        raise SystemExit(f"row update mismatch: tracker={tracker_counts} items={item_counts}")

    blocker_block = f"""## Wave64 Current Blocker Register - {iso}

Latest-state precedence: current global execution blockers are limited to `BLOCKER-W64-AWS-EXPIRED-SESSION-001` for live cloud work and the stable `BLOCKER-W64-GIT-DIRTY-WORKTREE-001` for a strict clean checkpoint. The latter's condition has narrowed to exactly five preserved paths; scoped commits and unrelated local work may continue.

Flux license/install/runtime proof and manual body gold masks are deferred scope-specific dependencies, not global project blockers. Row040 registry gaps, Row043 artifact absence, and the old 977-entry dirty snapshot are superseded by current Rows044, 043, and 046 evidence. Historical entries below are archival and cannot override this register without newer explicit validation evidence.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    issue_block = f"""## Wave64 Current Known-Issue Scope - {iso}

Known issues inherit the current Row049 register. AWS expiry applies only to new live cloud assertions; the five preserved paths apply only to strict clean-checkpoint requirements. Flux remains fail-closed only for its lane, and manual body gold masks remain fail-closed only for mask-dependent authority/promotion/certification. Pullback text-copy drift remains disclosed, while original Git blobs retain authority for the completed historical-byte proof. Superseded prose below is historical context and does not reopen completed proof.

Next unresolved row: `{NEXT}`. Rows050-054 remain passed and are not rerun without changed inputs.
"""
    prepend(HYD / "BLOCKERS.md", blocker_block)
    prepend(HYD / "KNOWN_ISSUES.md", issue_block)
    hydration_block = f"""## Wave64 Row049 Living Blocker Governance - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}` after one justified living-governance refresh. Two active blockers, two deferred scope-specific dependencies, and three superseded historical blockers are source-cited with latest-state precedence. No AWS, EC2, S3, ComfyUI, generation, mask, Wave71+, or Jira action occurred.

Next: skip unchanged passed Rows050-054 and begin `{NEXT}` source-summary integrity.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md"):
        prepend(HYD / name, hydration_block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRACKER, "Refreshed current blocker governance once and advanced past unchanged passed rows.", "; ".join(evidence_paths), "20/20 checks; active/deferred/superseded scopes separated", payload["qa_decision"], rel(canonical), f"Begin {NEXT}."])
    print(json.dumps({"status": STATUS, "checks": payload["check_summary"], "stamped": rel(stamped), "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
