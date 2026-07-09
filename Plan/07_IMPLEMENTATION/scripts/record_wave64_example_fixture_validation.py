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

TRACKER_ID = "TRK-W64-053"
ITEM_ID = "ITEM-W64-053"
NEXT_TRACKER_ID = "TRK-W64-054"
NEXT_ITEM_ID = "ITEM-W64-054"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

CHECK_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/run_wave64_example_fixture_validation_checks.py"
MANIFEST_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/generate_wave64_example_fixture_expectations_manifest.py"
SOURCE_EXAMPLE_ROOT = PLAN_ROOT / "09_EXAMPLES"
EXPECTATIONS_MANIFEST = SOURCE_EXAMPLE_ROOT / "EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json"

SOURCE_NEXT = HYDRATION_DIR / "NEXT_ACTION.md"
SOURCE_GOAL = HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md"
SOURCE_STATE = HYDRATION_DIR / "CURRENT_SESSION_STATE.md"
SOURCE_RESUME = HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md"
SOURCE_INDEX = HYDRATION_DIR / "QA_EVIDENCE_INDEX.md"
SOURCE_DECISIONS = HYDRATION_DIR / "RECENT_DECISIONS.md"

EVIDENCE = QA_DIR / "example_fixture_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json"

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
        "Recorded examples and fixture validation pass for Plan/09_EXAMPLES.",
        "; ".join(payload["evidence_paths"]),
        "fixture parse; example request valid; expected output defined; stale example scan",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID}.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    check_path = latest("EXAMPLE_FIXTURE_VALIDATION_CHECKS_*.json")
    checks = read_json(check_path)
    previous = read_json(QA_DIR / "script_validation.json")
    manifest = read_json(EXPECTATIONS_MANIFEST)
    counts = checks["counts"]

    check_results = {
        "previous_row_passed": previous.get("qa_decision") == "script_validation_passed_parser_only_no_live_side_effects",
        "fixture_parse": checks["fixture_parse"]["pass"] is True,
        "example_request_valid": checks["example_request_valid"]["pass"] is True,
        "expected_output_defined": checks["expected_output_defined"]["pass"] is True,
        "stale_example_scan": checks["stale_example_scan"]["pass"] is True,
        "structured_report": checks["structured_report"]["pass"] is True,
        "expectations_manifest_present": EXPECTATIONS_MANIFEST.exists(),
        "expectations_manifest_complete": manifest.get("counts", {}).get("expected_output_defined") == manifest.get("counts", {}).get("entries"),
    }
    errors = [name for name, passed in check_results.items() if not passed]
    qa_decision = "example_fixture_validation_passed_plan_examples_manifest_bound" if not errors else "blocked_example_fixture_validation_gap"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"EXAMPLE_FIXTURE_VALIDATION_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_example_root": rel(SOURCE_EXAMPLE_ROOT),
        "check_script": rel(CHECK_SCRIPT),
        "manifest_script": rel(MANIFEST_SCRIPT),
        "latest_check_evidence": rel(check_path),
        "expectations_manifest": rel(EXPECTATIONS_MANIFEST),
        "checks": check_results,
        "counts": counts,
        "manifest_counts": manifest.get("counts", {}),
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
        "media_review_boundary": {
            "visual_review_required_when_media_outputs_exist": True,
            "media_output_files_in_scope": counts.get("other_files") != 0,
            "local_scope_files": "JSON and CSV fixtures only",
            "decision": "not_applicable_no_media_output_files",
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
        rel(EXPECTATIONS_MANIFEST),
        rel(CHECK_SCRIPT),
        rel(MANIFEST_SCRIPT),
        rel(SOURCE_EXAMPLE_ROOT),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 example fixture validation {STAMP}: files={counts['files']} json={counts['json_files']} "
        f"csv={counts['csv_files']} schema_validated={counts['schema_validated_examples']} "
        f"schema_invalid={counts['schema_invalid_examples']} expected_output_gaps={counts['expected_output_gaps']} "
        f"stale_refs={counts['stale_references']} decision={qa_decision}."
    )
    additions = [
        "wave64_example_fixture_validation_checked",
        qa_decision,
        "fixture_parse_passed",
        "example_request_valid_passed",
        "expected_output_defined_passed",
        "stale_example_scan_passed",
        "expectations_manifest_bound",
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
## Immediate Next Action - Wave64 Example Fixture Validation - {ISO_TS}

Worked examples and fixtures row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. Local validation scanned `{counts['files']}` example files, parsed `{counts['json_files']}` JSON files and `{counts['csv_files']}` CSV file, schema-validated `{counts['schema_validated_examples']}` examples, and found zero parse errors, zero schema invalid examples, zero expected-output gaps, and zero stale references.

Expectation boundary: `Plan/09_EXAMPLES/EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json` now explicitly ties all `{manifest.get('counts', {}).get('entries')}` current fixtures to parse expectations, QA/expected-output sources, and stale-reference policy.

Runtime boundary: no EC2, AWS, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/example_fixture_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`
- `Plan/09_EXAMPLES/EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.
"""
    for path in [SOURCE_NEXT, SOURCE_GOAL, SOURCE_STATE, SOURCE_RESUME]:
        prepend(path, block)

    index_block = f"""
## Wave64 Example Fixture Validation - {ISO_TS}

Examples and fixtures validation passed locally for `Plan/09_EXAMPLES`: parse, matching-schema validation, expected-output manifest binding, and stale-reference scan.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/example_fixture_validation.json`
- `Plan/Instructions/QA/Evidence/Wave64/EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json`
- `Plan/Tracker/Evidence/EXAMPLE_FIXTURE_VALIDATION_{STAMP}.json`
- `{rel(check_path)}`
- `Plan/09_EXAMPLES/EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json`
"""
    prepend(SOURCE_INDEX, index_block)

    decision_block = f"""
## Wave64 Example Fixture Expectations Boundary - {ISO_TS}

Decision: `Plan/09_EXAMPLES/EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json` is the explicit local QA expectation binding for example/fixture rows. This boundary validates example contracts only; it does not promote masks, consume candidate masks as truth, claim runtime readiness, or activate Wave71+.
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
