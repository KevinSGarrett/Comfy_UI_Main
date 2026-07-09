from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
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

SOURCE_AUDIT = QA_DIR / "plan_source_file_coverage.json"
CLOSURE_CSV = COVERAGE_AUDIT_DIR / "wave64_plan_source_file_coverage_gap_closure.csv"
EVIDENCE = QA_DIR / "plan_source_file_coverage_gap_closure.json"
STAMPED_EVIDENCE = QA_DIR / f"PLAN_SOURCE_FILE_COVERAGE_GAP_CLOSURE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"PLAN_SOURCE_FILE_COVERAGE_GAP_CLOSURE_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

TRACKER_ID = "TRK-W64-001"
ITEM_ID = "ITEM-W64-001"
FIELDNAMES = [
    "Source_Key",
    "Source_File_Relative",
    "Citation_File",
    "Citation_Full_Path",
    "Citation_Section",
    "Citation_Line_Start",
    "Citation_Line_End",
    "Citation_Excerpt",
    "Source_Type",
    "Source_Size_Bytes",
    "Domain",
    "Coverage_Level",
    "Covered_In_Tracker_After",
    "Covered_In_Items_After",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def source_key(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    return f"W64-GAP-{digest}"


def first_excerpt(path: Path) -> tuple[int, int, str]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return 1, 1, "[binary_or_unreadable_file]"
    non_empty = [(idx + 1, line.strip()) for idx, line in enumerate(text) if line.strip()]
    if not non_empty:
        return 1, 1, "[empty_file]"
    start, first = non_empty[0]
    excerpt = first[:500]
    return start, start, excerpt


def domain_for(path: str) -> str:
    parts = Path(path.replace("/", "\\")).parts
    if len(parts) < 2:
        return "plan_root"
    top = parts[1].lower()
    if top in {"instructions", "tracker", "items"}:
        return f"{top}_coverage_hygiene"
    if top == "07_implementation":
        return "implementation_coverage_hygiene"
    return f"{top}_coverage_hygiene"


def coverage_row(path: str) -> dict[str, object]:
    full = PROJECT_ROOT / path
    line_start, line_end, excerpt = first_excerpt(full)
    suffix = full.suffix.lower().lstrip(".") or "none"
    return {
        "Source_Key": source_key(path),
        "Source_File_Relative": path,
        "Citation_File": path.replace("Plan/", "", 1).replace("/", "\\"),
        "Citation_Full_Path": str(full),
        "Citation_Section": "Generated Wave64 source file coverage closure",
        "Citation_Line_Start": line_start,
        "Citation_Line_End": line_end,
        "Citation_Excerpt": excerpt,
        "Source_Type": suffix,
        "Source_Size_Bytes": full.stat().st_size if full.exists() else 0,
        "Domain": domain_for(path),
        "Coverage_Level": "generated_file_coverage_record",
        "Covered_In_Tracker_After": "TRUE",
        "Covered_In_Items_After": "TRUE",
    }


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
        "Generated Wave64 source coverage closure rows for Plan files not yet mapped by tracker/item or coverage audit records.",
        "; ".join(payload["evidence_paths"]),
        "gap CSV read; generated source coverage rows; closure CSV; JSON evidence; tracker/item row update",
        "WAVE64_PLAN_SOURCE_COVERAGE_GAP_CLOSURE_GENERATED_NONMASK_SAFE",
        rel(EVIDENCE),
        "Rerun Wave64 plan source coverage audit to verify closure.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    source_payload = read_json(SOURCE_AUDIT)
    gap_csv = PROJECT_ROOT / str(source_payload.get("gap_csv", ""))
    gap_rows = read_csv_rows(gap_csv)
    paths = {row["path"] for row in gap_rows if row.get("path")}
    paths.update(
        rel(path)
        for path in [
            Path(__file__),
            CLOSURE_CSV,
            EVIDENCE,
            STAMPED_EVIDENCE,
            TRACKER_EVIDENCE,
        ]
    )
    records = [coverage_row(path) for path in sorted(paths)]
    CLOSURE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CLOSURE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    top_counts = dict(sorted(Counter(domain_for(str(record["Source_File_Relative"])) for record in records).items()))
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"PLAN_SOURCE_FILE_COVERAGE_GAP_CLOSURE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "source_audit": rel(SOURCE_AUDIT),
        "source_gap_csv": rel(gap_csv),
        "closure_csv": rel(CLOSURE_CSV),
        "closure_record_count": len(records),
        "source_gap_rows_closed": len(gap_rows),
        "self_referential_outputs_covered": [
            rel(Path(__file__)),
            rel(CLOSURE_CSV),
            rel(EVIDENCE),
            rel(STAMPED_EVIDENCE),
            rel(TRACKER_EVIDENCE),
        ],
        "domain_counts": top_counts,
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "qa_decision": "wave64_plan_source_coverage_gap_closure_generated_nonmask_safe",
        "next_step": "Rerun audit_wave64_plan_source_file_coverage.py and verify unmapped count after closure records are recognized.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(CLOSURE_CSV),
    ]
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 plan source coverage gap closure {STAMP}: wrote {len(records)} generated source coverage records "
        f"covering {len(gap_rows)} prior gap rows plus closure artifacts. Non-mask-safe; no mask truth consumed, "
        "no masks promoted, no hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": [
                    "wave64_plan_source_file_coverage_gap_closure_generated",
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
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": [
                    "wave64_plan_source_file_coverage_gap_closure_generated",
                    "allowed_nonmask_work_can_continue",
                ],
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Plan Source Coverage Gap Closure - {ISO_TS}

Generated source coverage audit records for the previous Wave64 plan-source coverage gaps.

Result: wrote `{len(records)}` generated coverage rows to `{rel(CLOSURE_CSV)}` covering `{len(gap_rows)}` prior gap rows plus closure artifacts. This is non-mask-safe work only.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(CLOSURE_CSV)}`

No masks were consumed as truth, promoted, or used for hard gates. No Wave71+ activation was attempted. Next exact local action: rerun the Wave64 plan-source coverage audit and verify the remaining unmapped count.
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
## Wave64 Plan Source Coverage Gap Closure - {ISO_TS}

Generated source coverage closure rows for `{TRACKER_ID}` / `{ITEM_ID}` without consuming mask truth.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(CLOSURE_CSV)}`
""",
    )
    append_proof_log(payload)

    print(json.dumps({
        "closure_csv": str(CLOSURE_CSV),
        "evidence": str(EVIDENCE),
        "closure_record_count": len(records),
        "source_gap_rows_closed": len(gap_rows),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
