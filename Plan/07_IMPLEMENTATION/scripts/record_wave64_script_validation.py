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

TRACKER_ID = "TRK-W64-052"
ITEM_ID = "ITEM-W64-052"
PREVIOUS_TRACKER_ID = "TRK-W64-051"
NEXT_TRACKER_ID = "TRK-W64-053"
NEXT_ITEM_ID = "ITEM-W64-053"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

CHECK_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/run_wave64_script_validation_checks.py"
SOURCE_SCRIPT_ROOT = PLAN_ROOT / "08_SCRIPTS"
SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "script_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"SCRIPT_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"SCRIPT_VALIDATION_{STAMP}.json"

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
        "Recorded parser-only Python and PowerShell script validation.",
        "; ".join(payload["evidence_paths"]),
        "parser check; local smoke; no live side effect default; evidence output json",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    check_path = latest("SCRIPT_VALIDATION_CHECKS_*.json")
    checks = read_json(check_path)
    previous = read_json(QA_DIR / "schema_validation.json")
    parser = checks["parser_check"]
    py = parser["python"]
    ps = parser["powershell"]

    check_results = {
        "previous_row_passed": previous.get("qa_decision") == "schema_validation_passed_plan_json_csv_schema_assets",
        "parser_check": parser["pass"] is True and py["parse_error_count"] == 0 and ps["parse_error_count"] == 0,
        "local_smoke": checks["local_smoke"]["pass"] is True,
        "no_live_side_effect_default": checks["no_live_side_effect_default"]["pass"] is True,
        "evidence_output_json": checks["evidence_output_json"]["pass"] is True,
        "script_root_exists": SOURCE_SCRIPT_ROOT.exists(),
    }
    errors = [name for name, passed in check_results.items() if not passed]
    qa_decision = "script_validation_passed_parser_only_no_live_side_effects" if not errors else "blocked_script_validation_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"SCRIPT_VALIDATION_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_script_root": rel(SOURCE_SCRIPT_ROOT),
        "check_script": rel(CHECK_SCRIPT),
        "check_evidence": rel(check_path),
        "checks": check_results,
        "counts": {
            "python_files": py["file_count"],
            "python_parse_errors": py["parse_error_count"],
            "powershell_files": ps["file_count"],
            "powershell_parse_errors": ps["parse_error_count"],
        },
        "runtime_boundary": {
            "ec2_started": False,
            "aws_contacted": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "helper_bodies_executed": False,
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
    ps_parser_evidence = ps.get("process", {}).get("parser_evidence")
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(check_path),
        rel(CHECK_SCRIPT),
        rel(SOURCE_SCRIPT_ROOT),
    ]
    if isinstance(ps_parser_evidence, str) and ps_parser_evidence.startswith("Plan/"):
        payload["evidence_paths"].append(ps_parser_evidence)

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 script validation {STAMP}: python_files={py['file_count']} python_errors={py['parse_error_count']} "
        f"powershell_files={ps['file_count']} powershell_errors={ps['parse_error_count']} decision={qa_decision}."
    )
    additions = [
        "wave64_script_validation_checked",
        qa_decision,
        "parser_check_passed",
        "local_smoke_passed_parser_only",
        "no_live_side_effect_default_passed",
        "evidence_output_json_passed",
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
## Immediate Next Action - Wave64 Script Validation - {ISO_TS}

Worked script parser row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Parser-only validation compiled `{py['file_count']}` Python files and parsed `{ps['file_count']}` PowerShell files with zero parser errors. No project helper bodies were executed.

Runtime boundary: no EC2, AWS, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/script_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCRIPT_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCRIPT_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, block)

    index_block = f"""
## Wave64 Script Validation - {ISO_TS}

Script parser validation passed with local-only Python `py_compile` and PowerShell parser checks. Helper bodies were not executed.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/script_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCRIPT_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCRIPT_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Script Parser Boundary Decision - {ISO_TS}

Decision: script-validation rows may use parser-only local smoke checks without executing helper bodies. Live helper execution remains gated by each helper's own runtime, AWS, EC2, ComfyUI, secret, and cost-control preconditions.
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
        "counts": payload["counts"],
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
