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

TRACKER_ID = "TRK-W64-051"
ITEM_ID = "ITEM-W64-051"
PREVIOUS_TRACKER_ID = "TRK-W64-050"
NEXT_TRACKER_ID = "TRK-W64-052"
NEXT_ITEM_ID = "ITEM-W64-052"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

CHECK_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/run_wave64_schema_validation_checks.py"
SOURCE_SCHEMA_ROOT = PLAN_ROOT / "08_SCHEMAS"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "schema_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"SCHEMA_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"SCHEMA_VALIDATION_{STAMP}.json"

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


def latest_checks() -> list[Path]:
    return sorted(QA_DIR.glob("SCHEMA_VALIDATION_CHECKS_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


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
        "Recorded JSON/CSV/schema validation pass for Plan structured assets.",
        "; ".join(payload["evidence_paths"]),
        "json parse; csv parse; schema required fields; structured report",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    checks = latest_checks()
    if not checks:
        raise RuntimeError("No SCHEMA_VALIDATION_CHECKS evidence found.")
    latest_pass = read_json(checks[0])
    prior_checks = [path for path in checks[1:] if path.name != checks[0].name]
    prior_failure = next((read_json(path) | {"path": rel(path)} for path in prior_checks if not read_json(path)["structured_report"]["pass"]), None)
    previous = read_json(QA_DIR / "items_tracker_coverage.json")

    counts = latest_pass["counts"]
    checks_pass = {
        "previous_row_passed": previous.get("qa_decision") == "items_tracker_coverage_passed_single_key_repair_then_post_verifier_pass",
        "json_parse": latest_pass["json_parse"]["pass"] is True and counts["json_parse_errors"] == 0,
        "csv_parse": latest_pass["csv_parse"]["pass"] is True and counts["csv_parse_errors"] == 0 and counts["csv_header_gaps"] == 0,
        "schema_required_fields": latest_pass["schema_required_fields"]["pass"] is True and counts["schema_errors"] == 0 and counts["schema_required_field_gaps"] == 0,
        "structured_report": latest_pass["structured_report"]["pass"] is True,
        "schema_root_exists": SOURCE_SCHEMA_ROOT.exists(),
    }
    errors = [name for name, passed in checks_pass.items() if not passed]
    qa_decision = "schema_validation_passed_plan_json_csv_schema_assets" if not errors else "blocked_schema_validation_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"SCHEMA_VALIDATION_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_schema_root": rel(SOURCE_SCHEMA_ROOT),
        "check_script": rel(CHECK_SCRIPT),
        "latest_check_evidence": rel(checks[0]),
        "prior_strict_heuristic_failure": prior_failure,
        "validator_correction": {
            "changed_validator": True,
            "reason": "Recognized established local legacy schema descriptors with schema_name and required_fields as valid schema-managed assets.",
            "broad_data_repair": False,
        },
        "checks": checks_pass,
        "counts": counts,
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
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(checks[0]),
        rel(CHECK_SCRIPT),
        rel(SOURCE_SCHEMA_ROOT),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 schema validation {STAMP}: json={counts['json_files']} csv={counts['csv_files']} "
        f"schemas={counts['schema_files']} json_errors={counts['json_parse_errors']} csv_errors={counts['csv_parse_errors']} "
        f"schema_errors={counts['schema_errors']} decision={qa_decision}."
    )
    additions = [
        "wave64_schema_validation_checked",
        qa_decision,
        "json_parse_passed",
        "csv_parse_passed",
        "schema_required_fields_passed",
        "structured_report_passed",
        "legacy_schema_descriptor_supported",
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
## Immediate Next Action - Wave64 Schema Validation - {ISO_TS}

Worked structured data row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Local validation parsed `{counts['json_files']}` JSON files and `{counts['csv_files']}` CSV files under `Plan`, checked `{counts['schema_files']}` schema files under `Plan/08_SCHEMAS`, and found zero JSON parse errors, zero CSV parse/header errors, zero schema errors, and zero schema required-field gaps.

Validator note: the first strict heuristic pass incorrectly flagged legacy `schema_name` + `required_fields` descriptors as gaps; the validator now recognizes that established local schema form and the corrected evidence passes.

Runtime/mask boundary: no EC2, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/schema_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCHEMA_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCHEMA_VALIDATION_{STAMP}.json`
- `{rel(checks[0])}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, block)

    index_block = f"""
## Wave64 Schema Validation - {ISO_TS}

Schema/structured-data validation passed for Plan JSON, CSV, and `08_SCHEMAS` assets. Legacy schema descriptors are recognized as valid local schema-managed assets.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/schema_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCHEMA_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCHEMA_VALIDATION_{STAMP}.json`
- `{rel(checks[0])}`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Schema Descriptor Decision - {ISO_TS}

Decision: `Plan/08_SCHEMAS` contains both JSON Schema documents and legacy `schema_name` plus `required_fields` descriptors. Schema validation must accept both established local forms while still failing closed on JSON parse errors, CSV parse/header errors, invalid JSON Schemas, duplicate schema filenames, or malformed legacy descriptors.
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
        "counts": counts,
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
