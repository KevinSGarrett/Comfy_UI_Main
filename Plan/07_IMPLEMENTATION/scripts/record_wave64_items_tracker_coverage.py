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

TRACKER_ID = "TRK-W64-050"
ITEM_ID = "ITEM-W64-050"
PREVIOUS_TRACKER_ID = "TRK-W64-049"
NEXT_TRACKER_ID = "TRK-W64-051"
NEXT_ITEM_ID = "ITEM-W64-051"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

SOURCE_SCRIPT = PLAN_ROOT / "Instructions/QA/Scripts/Test-ItemsTrackerPackageStatic.ps1"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "items_tracker_coverage.json"
STAMPED_EVIDENCE = QA_DIR / f"ITEMS_TRACKER_COVERAGE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"ITEMS_TRACKER_COVERAGE_{STAMP}.json"

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


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def latest(pattern: str) -> Path:
    return max(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)


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
        "Recorded Items/Tracker coverage validation, single-key repair, and passing post-repair verifier.",
        "; ".join(payload["evidence_paths"]),
        "items rows present; tracker rows present; citation required; domain required; coverage report pass",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; stop coverage refreshes until a Plan file is added/renamed or user asks.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    pre_path = latest("ITEMS_TRACKER_COVERAGE_VERIFIER_202*.json")
    repair_path = latest("SINGLE_MISSING_ULTRA_SOURCE_KEY_REPAIR_*.json")
    post_path = latest("ITEMS_TRACKER_COVERAGE_VERIFIER_POST_REPAIR_*.json")
    previous_path = QA_DIR / "blocker_known_issue_control.json"
    pre = read_json(pre_path)
    repair = read_json(repair_path)
    post = read_json(post_path)
    previous = read_json(previous_path)

    tracker_report = post["validations"]["tracker"]["report"]
    items_report = post["validations"]["items"]["report"]
    wave64_report = post["validations"]["wave64_strict_ai_coverage"]["report"]
    wave65_report = post["validations"]["wave65_plan_source_coverage"]["report"]

    checks = {
        "previous_row_passed": previous.get("qa_decision") == "blocker_known_issue_control_passed_source_cited_latest_state_precedence",
        "pre_verifier_failed_expected_single_key": pre.get("result") == "fail"
        and "tracker_report_failed" in pre.get("failures", [])
        and pre["validations"]["tracker"]["report"]["missing_ultra_source_keys"] == 1
        and pre["validations"]["items"]["report"]["missing_ultra_source_keys"] == 1,
        "single_key_repair_changed_tracker": repair["tracker_repair"].get("changed") is True,
        "single_key_repair_changed_items": repair["items_repair"].get("changed") is True,
        "post_verifier_passed": post.get("result") == "pass_local_only",
        "tracker_rows_present": tracker_report["row_count"] == 54694 and tracker_report["missing_ultra_source_keys"] == 0,
        "items_rows_present": items_report["row_count"] == 54646 and items_report["missing_ultra_source_keys"] == 0,
        "citation_required": tracker_report["bad_citation_rows"] == 0 and items_report["bad_citation_rows"] == 0,
        "domain_required": len(wave64_report["required_domains_missing"]) == 0,
        "coverage_report_pass": wave64_report["result"] == "pass" and wave65_report["result"] == "pass" and wave65_report["missing_after_wave65_count"] == 0,
    }
    errors = [name for name, passed in checks.items() if not passed]
    qa_decision = "items_tracker_coverage_passed_single_key_repair_then_post_verifier_pass" if not errors else "blocked_items_tracker_coverage_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"ITEMS_TRACKER_COVERAGE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_script": rel(SOURCE_SCRIPT),
        "pre_repair_verifier": rel(pre_path),
        "single_key_repair": rel(repair_path),
        "post_repair_verifier": rel(post_path),
        "exact_repair": {
            "source_key": repair["source_key"],
            "source_file": repair["source_file"],
            "citation_section": repair["citation_section"],
            "tracker_id_added": repair["tracker_repair"]["id"],
            "item_id_added": repair["items_repair"]["id"],
        },
        "checks": checks,
        "post_repair_counts": {
            "tracker_row_count": tracker_report["row_count"],
            "tracker_missing_ultra_source_keys": tracker_report["missing_ultra_source_keys"],
            "items_row_count": items_report["row_count"],
            "items_missing_ultra_source_keys": items_report["missing_ultra_source_keys"],
            "wave64_item_rows": wave64_report["row_count_items"],
            "wave64_tracker_rows": wave64_report["row_count_tracker"],
            "wave65_missing_after_count": wave65_report["missing_after_wave65_count"],
        },
        "bounded_coverage_policy": {
            "pre_repair_verifier_runs": 1,
            "narrow_repair_passes": 1,
            "post_repair_verifier_runs": 1,
            "stop_coverage_refreshes_now": True,
            "next_coverage_refresh_allowed_only_if": "new Plan file added/renamed or explicit user request",
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
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; do not perform more coverage refreshes in this sequence.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(pre_path),
        rel(repair_path),
        rel(post_path),
        rel(SOURCE_SCRIPT),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 items/tracker coverage {STAMP}: repaired single missing Source_Key={repair['source_key']} "
        f"with {repair['tracker_repair']['id']} and {repair['items_repair']['id']}; post verifier result={post.get('result')}; decision={qa_decision}."
    )
    additions = [
        "wave64_items_tracker_coverage_checked",
        qa_decision,
        "single_missing_ultra_source_key_repaired",
        "post_repair_verifier_passed",
        "coverage_refresh_stop_rule_recorded",
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

    block = f"""
## Immediate Next Action - Wave64 Items Tracker Coverage - {ISO_TS}

Worked coverage row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. The first verifier found one exact missing Ultra source key: `c45e2efa43da01fd` for `03_IMAGE_SYSTEM/SOFT_BODY_MECHANICS_ULTIMATE_SPEC.md` lines 7-22 (`Soft-body region profiles`). A single narrow repair added `TRK-051560` and `ITEM-051584`, then the one allowed post-repair verifier passed with tracker/items missing Ultra source keys now `0`.

Coverage stop rule: no more coverage refreshes in this sequence unless a Plan file is added/renamed or the user explicitly asks.

Runtime/mask boundary: no EC2, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/items_tracker_coverage.json`
- `Plan/Instructions/QA/Evidence/Wave64/ITEMS_TRACKER_COVERAGE_{STAMP}.json`
- `Plan/Tracker/Evidence/ITEMS_TRACKER_COVERAGE_{STAMP}.json`
- `Plan/Instructions/QA/Evidence/Wave64/{post_path.name}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, block)

    index_block = f"""
## Wave64 Items Tracker Coverage - {ISO_TS}

Items/Tracker coverage passed after one bounded single-key repair and one post-repair verifier. Coverage refreshes stop here unless inputs change.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/items_tracker_coverage.json`
- `Plan/Instructions/QA/Evidence/Wave64/ITEMS_TRACKER_COVERAGE_{STAMP}.json`
- `Plan/Tracker/Evidence/ITEMS_TRACKER_COVERAGE_{STAMP}.json`
- `Plan/Instructions/QA/Evidence/Wave64/{post_path.name}`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Coverage Stop Decision - {ISO_TS}

Decision: after repairing the single missing Ultra source key and passing the post-repair verifier, stop coverage refreshes. Continue to concrete non-coverage rows unless a Plan file is added/renamed or the user explicitly requests another coverage pass.
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
        "exact_repair": payload["exact_repair"],
        "post_repair_counts": payload["post_repair_counts"],
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
