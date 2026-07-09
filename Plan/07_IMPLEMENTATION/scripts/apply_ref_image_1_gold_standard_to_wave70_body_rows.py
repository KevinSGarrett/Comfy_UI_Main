from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

MANIFEST = QA_DIR / "ref_image_1_body_mask_gold_standard.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

ROW_TO_MASK_TYPE = {
    "TRK-W70-0154": "mf70_belly_button_umbilicus",
    "TRK-W70-0155": "mf70_left_upper_arm",
    "TRK-W70-0156": "mf70_right_upper_arm",
    "TRK-W70-0157": "mf70_left_forearm",
    "TRK-W70-0158": "mf70_right_forearm",
    "ITEM-W70-0154": "mf70_belly_button_umbilicus",
    "ITEM-W70-0155": "mf70_left_upper_arm",
    "ITEM-W70-0156": "mf70_right_upper_arm",
    "ITEM-W70-0157": "mf70_left_forearm",
    "ITEM-W70-0158": "mf70_right_forearm",
}

NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
ISO_STAMP = NOW.isoformat()
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def manifest_paths(payload: dict[str, object], mask_type: str) -> list[str]:
    evidence_id = str(payload["evidence_id"])
    paths = [
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/{evidence_id}.json",
        "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
        f"Plan/Tracker/Evidence/{evidence_id}.json",
        "Plan/Tracker/Evidence/ref_image_1_body_mask_gold_standard.json",
        str(payload["runtime_manifest_path"]) if "runtime_manifest_path" in payload else "",
    ]
    if not paths[-1]:
        created = str(payload["created_local"])
        paths[-1] = (
            "runtime_artifacts/mask_factory/ref_image_1_body_mask_gold_standard/"
            f"{created}/ref_image_1_body_mask_gold_standard.json"
        )
    paths.extend(payload.get("mask_type_index", {}).get(mask_type, []))
    return paths


def update_csv(path: Path, id_field: str, payload: dict[str, object]) -> int:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    changed = 0
    for row in rows:
        row_id = row.get(id_field, "")
        mask_type = ROW_TO_MASK_TYPE.get(row_id)
        if not mask_type:
            continue
        row_paths = manifest_paths(payload, mask_type)
        row["Status"] = "Required_Not_Complete"
        if "Status_Decision" in row:
            row["Status_Decision"] = "ref_image_1_gold_standard_available_re_evaluation_required"
        for evidence_field in ["Evidence_Path", "Evidence_Required", "Acceptance_Evidence"]:
            if evidence_field in row:
                row[evidence_field] = append_unique(row.get(evidence_field, ""), row_paths)
        if "Coverage_Audit_Status" in row:
            row["Coverage_Audit_Status"] = append_unique(
                row.get("Coverage_Audit_Status", ""),
                ["ref_image_1_gold_standard_available_re_evaluation_required"],
            )
        if "Notes" in row:
            row["Notes"] = append_unique(
                row.get("Notes", ""),
                [
                    (
                        f"Ref_Image_1 gold standard {payload['created_local']}: user-provided multi-pose body "
                        f"reference includes labeled red-overlay mask evidence for {mask_type}. "
                        "Top strip is partial upper-body reference only; lower strip is primary full-body mask "
                        "validation area. Prior portrait-only not-visible blockers are superseded for Ref_Image_1 "
                        "evaluation, but this row remains Required_Not_Complete until row-level mask route, visual QA, "
                        "geometry gate, and promotion gate evidence pass."
                    )
                ],
            )
        changed += 1

    if changed:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
    return changed


def prepend_section(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8")


def update_hydration(payload: dict[str, object], updates: dict[str, int]) -> None:
    manifest_rel = "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json"
    body = f"""Ref_Image_1 body-mask gold-standard evidence has been attached to Wave70 rows `0154..0158` for abdomen/belly button, upper arms, and forearms.

Important interpretation:

- The top strip of the reference image is partial upper-body/one-third-body reference only.
- The lower strip is the primary full-body pose/mask validation area.
- Missing lower-body masks in the top strip are not failures and must not be used to write body-part not-visible blockers.
- Rows remain `Required_Not_Complete`; no row is passed or promoted by this manifest alone.

Canonical evidence:

- `{manifest_rel}`
- `Plan/Tracker/Evidence/ref_image_1_body_mask_gold_standard.json`

CSV rows updated: `{updates}`.

Next local action: re-evaluate `TRK-W70-0157` / `ITEM-W70-0157` `mf70_left_forearm` against Ref_Image_1 gold masks instead of the obsolete portrait-only source-visibility blocker."""
    prepend_section(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Ref_Image_1 Attached To Wave70 Body Rows - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Re-evaluate TRK-W70-0157 With Ref_Image_1 Gold Masks",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Ref_Image_1 Attached To Wave70 Body Rows - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Ref_Image_1 Row Attachment Evidence - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Re-evaluate 0157 With Ref_Image_1 - {ISO_STAMP}",
        body,
    )

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 Ref_Image_1 gold standard attached to body rows",
                "Attached corrected Ref_Image_1 body-mask gold-standard manifest and per-mask binary evidence to rows 0154..0158 while keeping rows Required_Not_Complete and non-promotional.",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json; Plan/Tracker/Evidence/ref_image_1_body_mask_gold_standard.json",
                "CSV structured update; manifest JSON validation; visual review of corrected left forearm mask extraction",
                "REF_IMAGE_1_ATTACHED_REEVALUATION_REQUIRED",
                manifest_rel,
                "Re-evaluate TRK-W70-0157 left forearm against Ref_Image_1 gold masks.",
            ]
        )


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["runtime_manifest_path"] = (
        "runtime_artifacts/mask_factory/ref_image_1_body_mask_gold_standard/"
        f"{payload['created_local']}/ref_image_1_body_mask_gold_standard.json"
    )
    updates: dict[str, int] = {}
    for path in TRACKER_FILES:
        updates[rel(path)] = update_csv(path, "Tracker_ID", payload)
    for path in ITEM_FILES:
        updates[rel(path)] = update_csv(path, "Item_ID", payload)
    update_hydration(payload, updates)
    print(json.dumps({"result": "ref_image_1_attached_re_evaluation_required", "updates": updates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
