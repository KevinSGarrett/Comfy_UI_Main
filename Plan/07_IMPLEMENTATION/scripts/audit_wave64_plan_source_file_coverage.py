from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
COVERAGE_AUDIT_DIR = PLAN_ROOT / "Tracker/Coverage_Audit"

EVIDENCE = QA_DIR / "plan_source_file_coverage.json"
STAMPED_EVIDENCE = QA_DIR / f"PLAN_SOURCE_FILE_COVERAGE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"PLAN_SOURCE_FILE_COVERAGE_{STAMP}.json"
SUMMARY_CSV = QA_DIR / f"plan_source_file_coverage_gaps_{STAMP}.csv"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

TRACKER_ID = "TRK-W64-001"
ITEM_ID = "ITEM-W64-001"
TRANSIENT_PARTS = {"__pycache__"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}
REFERENCE_FIELD_NAMES = {
    "Acceptance_Evidence",
    "Citation_File",
    "Citation_Full_Path",
    "Evidence_Path",
    "Evidence_Required",
    "Output_Artifact",
    "Related_Source_Paths",
    "Source_File_Relative",
    "Source_Path",
    "Source_Plan_Root",
    "Citation_Full_Path",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def plan_rel(path: Path) -> str:
    return rel(path)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def normalize_ref(value: object) -> set[str]:
    text = str(value or "").strip()
    if not text:
        return set()
    refs: set[str] = set()
    chunks = re.split(r"[;\n|]", text)
    for chunk in chunks:
        chunk = chunk.strip().strip("`\"'")
        if not chunk:
            continue
        chunk = chunk.replace("\\", "/")
        if "C:/Comfy_UI_Main/" in chunk:
            chunk = chunk.split("C:/Comfy_UI_Main/", 1)[1]
        elif "C:/Comfy_UI_Main" == chunk:
            chunk = "Plan"
        if chunk.startswith("Plan/"):
            refs.add(chunk)
        elif chunk.startswith("C:/"):
            continue
        elif chunk.startswith("Instructions/") or chunk.startswith("Tracker/") or chunk.startswith("Items/"):
            refs.add("Plan/" + chunk)
        elif chunk.startswith("../"):
            continue
        elif "/" in chunk and not chunk.startswith(("http://", "https://")):
            if chunk.split("/", 1)[0] in {
                "00_PROJECT_CONTROL",
                "01_CURRENT_SYSTEM_REVIEW",
                "02_TARGET_ARCHITECTURE",
                "03_IMAGE_SYSTEM",
                "04_VIDEO_GIF_SYSTEM",
                "05_AUDIO_SYSTEM",
                "06_QA_TESTING",
                "07_IMPLEMENTATION",
                "08_SCHEMAS",
                "08_SCRIPTS",
                "09_EXAMPLES",
                "10_REGISTRIES",
                "11_RELEASES",
                "11_SCHEMAS",
                "12_SOURCE_SUMMARIES",
                "13_ADVANCED_ADDITIONS_INTEGRATION",
                "14_ORGANIZATION_SYSTEM",
                "15_BLUEPRINT_PROJECTPLAN_COMBINATION",
                "Registries",
            }:
                refs.add("Plan/" + chunk)
    return refs


def is_source_file(path: Path) -> bool:
    if any(part in TRANSIENT_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in TRANSIENT_SUFFIXES:
        return False
    return True


def plan_files() -> list[str]:
    files = []
    for path in PLAN_ROOT.rglob("*"):
        if path.is_file() and is_source_file(path):
            files.append(plan_rel(path))
    return sorted(files)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def coverage_index_refs() -> set[str]:
    refs: set[str] = set()
    paths = [
        COVERAGE_AUDIT_DIR / "ultra_blueprint_coverage_after.csv",
        COVERAGE_AUDIT_DIR / "ultra_blueprint_source_section_index.csv",
    ]
    paths.extend(sorted(COVERAGE_AUDIT_DIR.glob("wave64_plan_source_file_coverage*_closure*.csv")))
    for path in paths:
        for row in read_csv_rows(path):
            for field in ["Source_File_Relative", "Citation_File", "Citation_Full_Path"]:
                refs.update(normalize_ref(row.get(field)))
    return refs


def row_refs(root: Path, subdir: str) -> tuple[set[str], dict[str, int]]:
    refs: set[str] = set()
    rows_by_file: dict[str, int] = {}
    for path in sorted((root / subdir).rglob("*.csv")):
        rows = read_csv_rows(path)
        rows_by_file[rel(path)] = len(rows)
        for row in rows:
            for field, value in row.items():
                if not field:
                    continue
                if field in REFERENCE_FIELD_NAMES or field.endswith("_Path") or field.endswith("_File"):
                    refs.update(normalize_ref(value))
    return refs, rows_by_file


def write_gap_csv(path: Path, gaps: list[dict[str, object]]) -> None:
    fieldnames = ["path", "top_level", "suffix", "bytes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(gaps)


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
        "Audited Plan source file coverage as non-mask-safe work under the gold-mask dependency boundary.",
        "; ".join(payload["evidence_paths"]),
        "plan file scan; coverage audit index scan; tracker/item citation scan; gap CSV; JSON evidence; row update",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Continue non-mask-safe coverage closure; do not treat gold-mask dependency as global blocker.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    files = plan_files()
    file_set = set(files)
    coverage_refs = coverage_index_refs()
    tracker_refs, tracker_row_counts = row_refs(PLAN_ROOT, "Tracker")
    item_refs, item_row_counts = row_refs(PLAN_ROOT, "Items")
    current_run_refs = {rel(path) for path in [EVIDENCE, STAMPED_EVIDENCE, TRACKER_EVIDENCE, SUMMARY_CSV]}
    mapped = file_set & (coverage_refs | tracker_refs | item_refs)
    mapped |= file_set & current_run_refs
    unmapped = sorted(file_set - mapped)
    gap_records = [
        {
            "path": path,
            "top_level": path.split("/", 2)[1] if path.startswith("Plan/") and "/" in path[5:] else "Plan",
            "suffix": Path(path).suffix.lower() or "[none]",
            "bytes": (PROJECT_ROOT / path).stat().st_size if (PROJECT_ROOT / path).exists() else 0,
        }
        for path in unmapped
    ]
    write_gap_csv(SUMMARY_CSV, gap_records)

    gap_top_counts = dict(sorted(Counter(str(row["top_level"]) for row in gap_records).items()))
    gap_suffix_counts = dict(sorted(Counter(str(row["suffix"]) for row in gap_records).items()))
    coverage_pass = len(unmapped) == 0
    qa_decision = (
        "plan_source_file_coverage_passed_nonmask_safe"
        if coverage_pass
        else "blocked_plan_source_file_coverage_gaps_remain_nonmask_safe"
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"PLAN_SOURCE_FILE_COVERAGE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Audit every non-transient file under Plan for coverage-index or tracker/item citation mapping.",
        "gold_mask_dependency_boundary": {
            "policy": "Gold masks are a scoped dependency only; this audit does not consume masks as truth.",
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "coverage_summary": {
            "plan_file_count": len(files),
            "mapped_file_count": len(mapped),
            "unmapped_file_count": len(unmapped),
            "coverage_pass": coverage_pass,
            "coverage_index_ref_count": len(coverage_refs),
            "tracker_ref_count": len(tracker_refs),
            "item_ref_count": len(item_refs),
            "tracker_csv_files_scanned": len(tracker_row_counts),
            "item_csv_files_scanned": len(item_row_counts),
            "gap_top_level_counts": gap_top_counts,
            "gap_suffix_counts": gap_suffix_counts,
        },
        "scanned_row_counts": {
            "tracker": tracker_row_counts,
            "items": item_row_counts,
        },
        "unmapped_sample": gap_records[:100],
        "gap_csv": rel(SUMMARY_CSV),
        "qa_decision": qa_decision,
        "status": "Allowed_NonMask_Work_Can_Continue",
        "next_step": "Close unmapped Plan coverage gaps by extending source coverage audit records or exact tracker/item citations without touching mask truth.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(SUMMARY_CSV),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 plan source file coverage audit {STAMP}: scanned {len(files)} non-transient Plan files, "
        f"mapped {len(mapped)}, and found {len(unmapped)} unmapped files. This is non-mask-safe work under the "
        "gold-mask dependency boundary; no masks consumed, promoted, or used for gates."
    )
    next_action = (
        "advance to TRK-W64-002 project control autonomy evidence, still staying outside mask-truth work until the user says manual masks are ready."
        if coverage_pass
        else "close unmapped Plan coverage gaps by extending source coverage audit records or exact tracker/item citations, still staying outside mask-truth work until the user says manual masks are ready."
    )
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
                "Coverage_Audit_Status": [
                    "wave64_plan_source_file_coverage_audited",
                    qa_decision,
                    "allowed_nonmask_work_can_continue",
                ],
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
                "Coverage_Audit_Status": [
                    "wave64_plan_source_file_coverage_audited",
                    qa_decision,
                    "allowed_nonmask_work_can_continue",
                ],
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Plan Source File Coverage Audit - {ISO_TS}

Worked the next explicit non-mask-safe task: `{TRACKER_ID}` / `{ITEM_ID}` plan source file coverage.

Result: scanned `{len(files)}` non-transient files under `Plan`, mapped `{len(mapped)}`, and found `{len(unmapped)}` unmapped files. Decision: `{qa_decision}`.

Gold-mask boundary: this audit did not consume candidate masks as truth, did not promote masks, did not rerun hard gates, and did not activate Wave71+. Missing manual gold masks remain scoped only to mask-dependent rows/gates.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(SUMMARY_CSV)}`

Next exact local action: {next_action}
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave64 Plan Source File Coverage Audit - {ISO_TS}

Non-mask-safe coverage audit for `{TRACKER_ID}` / `{ITEM_ID}` recorded `{len(unmapped)}` unmapped Plan files; no mask truth was consumed and no hard gates were rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(SUMMARY_CSV)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "gap_csv": str(SUMMARY_CSV),
        "qa_decision": qa_decision,
        "plan_file_count": len(files),
        "mapped_file_count": len(mapped),
        "unmapped_file_count": len(unmapped),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
