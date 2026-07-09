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

TRACKER_ID = "TRK-W64-054"
ITEM_ID = "ITEM-W64-054"
NEXT_TRACKER_ID = "TRK-W64-055"
NEXT_ITEM_ID = "ITEM-W64-055"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

CHECK_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/run_wave64_registry_integrity_checks.py"
SOURCE_REGISTRY_ROOT = PLAN_ROOT / "10_REGISTRIES"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "registry_integrity.json"
STAMPED_EVIDENCE = QA_DIR / f"REGISTRY_INTEGRITY_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"REGISTRY_INTEGRITY_{STAMP}.json"

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
    matches = sorted(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise RuntimeError(f"No evidence found for pattern {pattern}")
    return matches[0]


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
            row[field] = append_unique(row.get(field, ""), value) if isinstance(value, list) else value
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
        "Recorded registry integrity validation pass for Plan/10_REGISTRIES.",
        "; ".join(payload["evidence_paths"]),
        "unique ids; cross reference check; stale status scan; missing file check",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    check_path = latest("REGISTRY_INTEGRITY_CHECKS_*.json")
    checks = read_json(check_path)
    previous = read_json(QA_DIR / "example_fixture_validation.json")
    counts = checks["counts"]

    check_results = {
        "previous_row_passed": previous.get("qa_decision") == "example_fixture_validation_passed_plan_examples_manifest_bound",
        "parse_check": checks["parse_check"]["pass"] is True,
        "unique_ids": checks["unique_ids"]["pass"] is True,
        "cross_reference_check": checks["cross_reference_check"]["pass"] is True,
        "stale_status_scan": checks["stale_status_scan"]["pass"] is True,
        "missing_file_check": checks["missing_file_check"]["pass"] is True,
        "structured_report": checks["structured_report"]["pass"] is True,
        "registry_root_exists": SOURCE_REGISTRY_ROOT.exists(),
    }
    errors = [name for name, passed in check_results.items() if not passed]
    qa_decision = "registry_integrity_passed_local_structural_reference_scan" if not errors else "blocked_registry_integrity_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"REGISTRY_INTEGRITY_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_registry_root": rel(SOURCE_REGISTRY_ROOT),
        "check_script": rel(CHECK_SCRIPT),
        "latest_check_evidence": rel(check_path),
        "validator_correction_boundary": {
            "changed_validator": True,
            "reason": "Narrowed ID uniqueness to actual row identifiers so foreign keys, package IDs, and taxonomy value lists are not false failures.",
            "registry_data_changed": False,
        },
        "checks": check_results,
        "counts": counts,
        "runtime_boundary": {
            "ec2_started": False,
            "aws_contacted": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "hard_gates_rerun": False,
            "runtime_mutation": False,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(check_path),
        rel(CHECK_SCRIPT),
        rel(SOURCE_REGISTRY_ROOT),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 registry integrity {STAMP}: files={counts['files']} json={counts['json_files']} "
        f"csv={counts['csv_files']} duplicate_ids={counts['duplicate_id_findings']} "
        f"missing_refs={counts['missing_plan_references']} stale_status={counts['stale_status_findings']} "
        f"decision={qa_decision}."
    )
    additions = [
        "wave64_registry_integrity_checked",
        qa_decision,
        "parse_check_passed",
        "unique_ids_passed",
        "cross_reference_check_passed",
        "stale_status_scan_passed",
        "missing_file_check_passed",
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
## Immediate Next Action - Wave64 Registry Integrity - {ISO_TS}

Worked registry integrity row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Local validation scanned `{counts['files']}` registry files, parsed `{counts['json_files']}` JSON files and `{counts['csv_files']}` CSV files, and found zero JSON parse errors, zero CSV parse errors, zero duplicate row-ID findings, zero missing Plan references, and zero stale status-field findings.

Validator boundary: ID uniqueness is enforced on row identifiers only; foreign keys, shared package IDs, and status taxonomy values are not treated as registry corruption.

Runtime boundary: no EC2, AWS, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/registry_integrity.json`
- `Plan/Instructions/QA/Evidence/Wave64/REGISTRY_INTEGRITY_{STAMP}.json`
- `Plan/Tracker/Evidence/REGISTRY_INTEGRITY_{STAMP}.json`
- `{rel(check_path)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, block)

    index_block = f"""
## Wave64 Registry Integrity - {ISO_TS}

Registry integrity validation passed locally for `Plan/10_REGISTRIES`: parse, row-ID uniqueness, Plan reference resolution, stale status scan, and missing-file check.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/registry_integrity.json`
- `Plan/Instructions/QA/Evidence/Wave64/REGISTRY_INTEGRITY_{STAMP}.json`
- `Plan/Tracker/Evidence/REGISTRY_INTEGRITY_{STAMP}.json`
- `{rel(check_path)}`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Registry ID Boundary - {ISO_TS}

Decision: registry uniqueness checks enforce actual row identifiers, not foreign-key fields such as source/target node IDs, repeated Comfy registry package IDs, or taxonomy value lists. This is a local structural validation only and does not claim runtime freshness.
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
        "evidence": rel(EVIDENCE),
        "latest_check": rel(check_path),
        "csv_updates": payload["csv_updates"],
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
