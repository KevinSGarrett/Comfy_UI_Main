#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ITEM_ID = "ITEM-W70-0144"
TRACKER_ID = "TRK-W70-0144"
EXPECTED_STATUS = "Semantic_Face_Parsing_Authority_Implemented_Pending_Consensus"
MARKER = "LaPa/InsightFace 106 ordering mismatch recorded 20260710T224500-0500"
BOUNDARY = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/"
    "FACIAL_GOLD_LAPA_INSIGHTFACE_106_VAL_ROUTE_BOUNDARY_20260710T224500-0500.json"
)
BENCHMARK = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/"
    "FACIAL_GOLD_LAPA_INSIGHTFACE_106_VAL_BENCHMARK_20260710T223500-0500.json"
)
PANEL = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/Panels/"
    "FACIAL_GOLD_LAPA_INSIGHTFACE_106_VAL_COMPARISON_PANEL_20260710T224000-0500.png"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_unique(current: str, value: str) -> str:
    if value in current:
        return current
    return f"{current}; {value}" if current else value


def update_csv(path: Path, id_column: str, id_value: str, item_mode: bool) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    matches = [row for row in rows if row.get(id_column) == id_value]
    if len(matches) != 1:
        raise ValueError(f"ledger_row_count_invalid:{path}:{id_value}:{len(matches)}")
    row = matches[0]
    if row.get("Status") != EXPECTED_STATUS:
        raise ValueError(f"ledger_status_unexpected:{path}:{row.get('Status')}")
    values = {
        "Notes": (
            f"{MARKER}: originals-only route executed, but same-index NME/visual QA prove incompatible LaPa and "
            "InsightFace anatomical ordering; no gold-derived remap, promotion, or rerun."
        )
    }
    if item_mode:
        values["Evidence_Required"] = f"{BOUNDARY}; {BENCHMARK}"
    else:
        values.update(
            {
                "Acceptance_Evidence": f"{BOUNDARY}; {BENCHMARK}",
                "Evidence_Path": f"{BOUNDARY}; {BENCHMARK}",
                "Output_Artifact": PANEL,
            }
        )
    changed = False
    for key, value in values.items():
        if key not in row:
            continue
        updated = append_unique(row.get(key, ""), value)
        if updated != row.get(key, ""):
            row[key] = updated
            changed = True
    if changed:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return {"path": str(path), "row_id": id_value, "changed": changed, "status": row.get("Status")}


def synchronize_row(source: Path, target: Path, id_column: str, id_value: str) -> dict[str, object]:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        source_reader = csv.DictReader(handle)
        source_rows = [row for row in source_reader if row.get(id_column) == id_value]
        source_fields = source_reader.fieldnames or []
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        target_reader = csv.DictReader(handle)
        target_rows = list(target_reader)
        target_fields = target_reader.fieldnames or []
    if len(source_rows) != 1 or source_fields != target_fields:
        raise ValueError(f"ledger_mirror_shape_invalid:{source}:{target}:{id_value}")
    changed = False
    for index, row in enumerate(target_rows):
        if row.get(id_column) == id_value:
            if row != source_rows[0]:
                target_rows[index] = dict(source_rows[0])
                changed = True
            break
    else:
        raise ValueError(f"ledger_mirror_row_missing:{target}:{id_value}")
    if changed:
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=target_fields)
            writer.writeheader()
            writer.writerows(target_rows)
    return {"source": str(source), "target": str(target), "row_id": id_value, "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the LaPa/InsightFace 106 ordering boundary.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    required = [root / BOUNDARY, root / BENCHMARK, root / PANEL]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required_evidence_missing:{','.join(missing)}")
    item_master = root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv"
    item_mirror = root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv"
    tracker_master = root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
    tracker_mirror = root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv"
    updates = [
        update_csv(item_master, "Item_ID", ITEM_ID, True),
        update_csv(item_mirror, "Item_ID", ITEM_ID, True),
        update_csv(tracker_master, "Tracker_ID", TRACKER_ID, False),
        update_csv(tracker_mirror, "Tracker_ID", TRACKER_ID, False),
    ]
    mirrors = [
        synchronize_row(item_master, item_mirror, "Item_ID", ITEM_ID),
        synchronize_row(tracker_master, tracker_mirror, "Tracker_ID", TRACKER_ID),
    ]
    record = {
        "schema_version": "1.0",
        "evidence_id": "W70-LAPA-INSIGHTFACE-106-BOUNDARY-LEDGER-UPDATE-20260710T225000-0500",
        "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "result": "lapa_insightface_ordering_boundary_recorded_status_unchanged",
        "item_id": ITEM_ID,
        "tracker_id": TRACKER_ID,
        "status": EXPECTED_STATUS,
        "updates": updates,
        "mirror_sync": mirrors,
        "evidence_hashes": {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in required},
        "mask_promoted": False,
        "row_completed": False,
        "wave70_hard_gate_rerun": False,
        "wave71_activated": False,
    }
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
