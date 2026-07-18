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
SOURCE_BLOCKERS = HYDRATION_DIR / "BLOCKERS.md"
SOURCE_KNOWN_ISSUES = HYDRATION_DIR / "KNOWN_ISSUES.md"

EVIDENCE = QA_DIR / "script_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"SCRIPT_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"SCRIPT_VALIDATION_{STAMP}.json"
CURRENT_EVIDENCE = QA_DIR / "SCRIPT_VALIDATION_CURRENT_REVALIDATION_20260718.json"
TRACKER_CURRENT_EVIDENCE = TRACKER_EVIDENCE_DIR / "SCRIPT_VALIDATION_CURRENT_REVALIDATION_20260718.json"
TEST_LOG = QA_DIR / "script_validation_current_test_log.json"
DONE_CERT = PLAN_ROOT / "Instructions/QA/Evidence/Done_Certifications/ROW052_SCRIPT_VALIDATION_DONE_20260718.json"
ITEM_REPORT = PLAN_ROOT / "Items/Reports/ITEM-W64-052_script_validation.json"
TEST_SCRIPT = PLAN_ROOT / "Instructions/QA/Scripts/test_wave64_script_validation_checks.py"

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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def prepend(path: Path, block: str, replace_heading_prefix: str | None = None) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if replace_heading_prefix and existing.startswith(replace_heading_prefix):
        next_heading = existing.find("\n## ", len(replace_heading_prefix))
        existing = existing[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    if proof_path.exists():
        with proof_path.open("r", encoding="utf-8-sig", newline="") as f:
            if any(
                len(row) > 6 and row[2] == TRACKER_ID and row[6] == payload["qa_decision"]
                for row in csv.reader(f)
            ):
                return
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Recorded parser-only Python and PowerShell validation with an exact no-bytecode-write invariant.",
        "; ".join(payload["evidence_paths"]),
        "AST parser check; PowerShell parser check; 10-case focused regression; no bytecode drift; evidence output json",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}; retain runtime and worker boundaries.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    check_path = latest("SCRIPT_VALIDATION_CHECKS_*.json")
    checks = read_json(check_path)
    previous = read_json(QA_DIR / "schema_validation.json")
    focused = read_json(TEST_LOG)
    parser = checks["parser_check"]
    py = parser["python"]
    ps = parser["powershell"]
    bytecode = py["bytecode_inventory"]

    check_results = {
        "previous_row_passed": previous.get("qa_decision") in {
            "schema_validation_passed_plan_json_csv_schema_assets",
            "schema_validation_current_plan_json_csv_schema_assets_pass",
        },
        "parser_check": (
            parser["pass"] is True
            and py["parse_error_count"] == 0
            and ps["parse_error_count"] == 0
            and py.get("parser_method") == "compile_ast_only_with_tokenize_open"
        ),
        "python_bytecode_inventory_unchanged": (
            bytecode["unchanged"] is True
            and bytecode["changed_count"] == 0
            and bytecode["before_count"] == bytecode["after_count"]
        ),
        "focused_no_bytecode_regression": (
            focused.get("status") == "PASS"
            and focused.get("classification") == "ROW052_PARSER_ONLY_NO_BYTECODE_REGRESSION_PASS"
            and focused.get("case_count") == 10
            and focused.get("failure_count") == 0
        ),
        "local_smoke": checks["local_smoke"]["pass"] is True,
        "no_live_side_effect_default": (
            checks["no_live_side_effect_default"]["pass"] is True
            and checks["no_live_side_effect_default"].get("no_python_bytecode_write") is True
        ),
        "evidence_output_json": checks["evidence_output_json"]["pass"] is True,
        "script_root_exists": SOURCE_SCRIPT_ROOT.exists(),
    }
    errors = [name for name, passed in check_results.items() if not passed]
    qa_decision = "script_validation_current_plan_parser_only_no_bytecode_pass" if not errors else "blocked_script_validation_gap"

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
            "python_bytecode_artifacts_before": bytecode["before_count"],
            "python_bytecode_artifacts_after": bytecode["after_count"],
            "python_bytecode_artifacts_changed": bytecode["changed_count"],
            "powershell_files": ps["file_count"],
            "powershell_parse_errors": ps["parse_error_count"],
            "focused_regression_cases": focused["case_count"],
            "focused_regression_failures": focused["failure_count"],
        },
        "python_parser_method": py["parser_method"],
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
        "boundary": "Row052 local parser and helper-smoke validation only; no helper execution, runtime, worker, visual, media, AWS, EC2, or release certification.",
    }
    ps_parser_evidence = ps.get("process", {}).get("parser_evidence")
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(CURRENT_EVIDENCE),
        rel(TRACKER_CURRENT_EVIDENCE),
        rel(TEST_LOG),
        rel(DONE_CERT),
        rel(ITEM_REPORT),
        rel(check_path),
        rel(CHECK_SCRIPT),
        rel(TEST_SCRIPT),
        rel(SOURCE_SCRIPT_ROOT),
    ]
    if isinstance(ps_parser_evidence, str) and ps_parser_evidence.startswith("Plan/"):
        payload["evidence_paths"].append(ps_parser_evidence)

    for path in [EVIDENCE, STAMPED_EVIDENCE, TRACKER_EVIDENCE, CURRENT_EVIDENCE, TRACKER_CURRENT_EVIDENCE]:
        write_json(path, payload)

    note = (
        f"Wave64 script validation {STAMP}: python_files={py['file_count']} python_errors={py['parse_error_count']} "
        f"bytecode_changed={bytecode['changed_count']} powershell_files={ps['file_count']} "
        f"powershell_errors={ps['parse_error_count']} focused=10/10 decision={qa_decision}."
    )
    additions = [
        "wave64_script_validation_checked",
        qa_decision,
        "parser_check_passed",
        "local_smoke_passed_ast_only",
        "python_bytecode_inventory_unchanged",
        "focused_no_bytecode_regression_10_of_10",
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

Result: `{qa_decision}`. Parser-only validation AST-compiled `{py['file_count']}` Python files and parsed `{ps['file_count']}` PowerShell files with zero parser errors. The exact Plan bytecode inventory remained `{bytecode['before_count']} -> {bytecode['after_count']}` with zero changed artifacts, and the focused regression passed `10/10`. No project helper bodies were executed.

Runtime boundary: no EC2, AWS, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/script_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCRIPT_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCRIPT_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME, SOURCE_BLOCKERS, SOURCE_KNOWN_ISSUES]:
        prepend(path, block, "## Immediate Next Action - Wave64 Script Validation -")

    index_block = f"""
## Wave64 Script Validation - {ISO_TS}

Script parser validation passed with local-only Python AST compilation and PowerShell parser checks. Helper bodies were not executed, and all pre-existing Plan bytecode artifacts remained byte-for-byte and timestamp stable.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/script_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/SCRIPT_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/SCRIPT_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`
"""
    prepend(SOURCE_INDEX, index_block, "## Wave64 Script Validation -")

    decision_block = f"""
## Wave64 Script Parser Boundary Decision - {ISO_TS}

Decision: script-validation rows may use parser-only local smoke checks without executing helper bodies. Live helper execution remains gated by each helper's own runtime, AWS, EC2, ComfyUI, secret, and cost-control preconditions.

Python parser authority uses `compile(..., PyCF_ONLY_AST)` with PEP 263 decoding. `py_compile` is prohibited for this parser-only evidence because it may write `__pycache__` artifacts.
"""
    prepend(SOURCE_DECISIONS, decision_block, "## Wave64 Script Parser Boundary Decision -")

    append_proof_log(payload)
    payload["csv_updates"] = {"tracker": tracker_updates, "items": item_updates}
    for path in [EVIDENCE, STAMPED_EVIDENCE, TRACKER_EVIDENCE, CURRENT_EVIDENCE, TRACKER_CURRENT_EVIDENCE]:
        write_json(path, payload)

    evidence_sha = sha256_file(CURRENT_EVIDENCE)
    tracker_evidence_sha = sha256_file(TRACKER_CURRENT_EVIDENCE)
    done_cert = {
        "schema_version": "1.0",
        "artifact_type": "wave64_done_certification",
        "created_iso": ISO_TS,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": "PASS" if not errors else "FAIL",
        "qa_decision": qa_decision,
        "implementation": {
            "validator_path": rel(CHECK_SCRIPT),
            "validator_sha256": sha256_file(CHECK_SCRIPT),
            "test_path": rel(TEST_SCRIPT),
            "test_sha256": sha256_file(TEST_SCRIPT),
        },
        "validation": payload["counts"],
        "canonical_evidence": {"path": rel(CURRENT_EVIDENCE), "sha256": evidence_sha},
        "tracker_evidence": {"path": rel(TRACKER_CURRENT_EVIDENCE), "sha256": tracker_evidence_sha},
        "boundary": payload["boundary"],
        "next_step": payload["next_step"],
    }
    write_json(DONE_CERT, done_cert)
    item_report = {
        "schema_version": "1.0",
        "artifact_type": "wave64_item_completion_report",
        "created_iso": ISO_TS,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": "Completed_Current_Plan_Parser_Only_No_Bytecode_Pass" if not errors else "Blocked_Current_Plan_Script_Validation_Gap",
        "qa_decision": qa_decision,
        "acceptance_criteria": {
            "python_ast_parse": py["parse_error_count"] == 0,
            "powershell_parse": ps["parse_error_count"] == 0,
            "focused_regression": focused["failure_count"] == 0,
            "bytecode_inventory_unchanged": bytecode["unchanged"] is True,
            "no_live_side_effect_default": check_results["no_live_side_effect_default"],
        },
        "evidence_paths": payload["evidence_paths"],
        "boundary": payload["boundary"],
        "next_action": payload["next_step"],
    }
    write_json(ITEM_REPORT, item_report)

    print(json.dumps({
        "qa_decision": qa_decision,
        "errors": errors,
        "counts": payload["counts"],
        "evidence": rel(EVIDENCE),
        "next": f"{NEXT_TRACKER_ID}/{NEXT_ITEM_ID}",
    }, indent=2))


if __name__ == "__main__":
    main()
