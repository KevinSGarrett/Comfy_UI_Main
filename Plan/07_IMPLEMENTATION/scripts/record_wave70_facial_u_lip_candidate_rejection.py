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
MARKER = "u_lip_dilate_exclusive_v1 rejected 20260710T222000-0500"
REJECTION = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/"
    "FACIAL_GOLD_U_LIP_DILATE_EXCLUSIVE_REJECTION_20260710T222000-0500.json"
)
REGRESSION = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/"
    "FACIAL_GOLD_U_LIP_DILATE_EXCLUSIVE_REGRESSION_20260710T222000-0500.json"
)
CONTROL_PANEL = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/Panels/"
    "FACIAL_GOLD_U_LIP_DILATE_EXCLUSIVE_CONTROL_PANEL_20260710T221000-0500.png"
)
HELDOUT_PANEL = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Facial_Gold_Standards/Panels/"
    "FACIAL_GOLD_U_LIP_DILATE_EXCLUSIVE_HELDOUT_PANEL_20260710T221000-0500.png"
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
        fieldnames = reader.fieldnames or []
    matches = [row for row in rows if row.get(id_column) == id_value]
    if len(matches) != 1:
        raise ValueError(f"ledger_row_count_invalid:{path}:{id_value}:{len(matches)}")
    row = matches[0]
    if row.get("Status") != EXPECTED_STATUS:
        raise ValueError(f"ledger_status_unexpected:{path}:{row.get('Status')}")
    changed = False
    values = {
        "Notes": (
            f"{MARKER}: fixed gold-blind square-3x3 upper-lip dilation improved recall but increased false "
            "positives and reduced IoU on controlled and held-out sets; retained as rejected regression fixture only."
        ),
    }
    if item_mode:
        values["Evidence_Required"] = f"{REJECTION}; {REGRESSION}"
    else:
        values.update(
            {
                "Acceptance_Evidence": f"{REJECTION}; {REGRESSION}",
                "Evidence_Path": f"{REJECTION}; {REGRESSION}",
                "Output_Artifact": f"{CONTROL_PANEL}; {HELDOUT_PANEL}",
            }
        )
    for key, value in values.items():
        if key not in row:
            continue
        updated = append_unique(row.get(key, ""), value)
        if updated != row.get(key, ""):
            row[key] = updated
            changed = True
    if changed:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
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
        if row.get(id_column) != id_value:
            continue
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
    parser = argparse.ArgumentParser(description="Record rejected upper-lip facial candidate in Wave70 ledgers.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    required = [root / REJECTION, root / REGRESSION, root / CONTROL_PANEL, root / HELDOUT_PANEL]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required_evidence_missing:{','.join(missing)}")
    item_master = root / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv"
    item_mirror = root / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv"
    tracker_master = root / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
    tracker_mirror = root / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv"
    updates = [
        update_csv(item_master, "Item_ID", ITEM_ID, True),
        update_csv(
            item_mirror,
            "Item_ID",
            ITEM_ID,
            True,
        ),
        update_csv(tracker_master, "Tracker_ID", TRACKER_ID, False),
        update_csv(
            tracker_mirror,
            "Tracker_ID",
            TRACKER_ID,
            False,
        ),
    ]
    mirror_sync = [
        synchronize_row(item_master, item_mirror, "Item_ID", ITEM_ID),
        synchronize_row(tracker_master, tracker_mirror, "Tracker_ID", TRACKER_ID),
    ]
    record = {
        "schema_version": "1.0",
        "evidence_id": "W70-FACIAL-U-LIP-CANDIDATE-REJECTION-LEDGER-UPDATE-20260710T222500-0500",
        "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "result": "facial_u_lip_rejection_recorded_status_unchanged",
        "item_id": ITEM_ID,
        "tracker_id": TRACKER_ID,
        "status": EXPECTED_STATUS,
        "updates": updates,
        "mirror_sync": mirror_sync,
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
