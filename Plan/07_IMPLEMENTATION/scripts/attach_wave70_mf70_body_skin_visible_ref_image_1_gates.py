from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
STAMP = "20260708T140617-0500"
ISO_TS = "2026-07-08T14:06:17-05:00"

TRACKER_ID = "TRK-W70-0159"
ITEM_ID = "ITEM-W70-0159"
NEXT_TRACKER_ID = "TRK-W70-0162"
NEXT_ITEM_ID = "ITEM-W70-0162"

STATUS_DECISION = (
    "ref_image_1_body_skin_composite_gold_mask_available_route_not_complete_global_gates_pass"
)
COVERAGE_TOKENS = [
    "post_mf70_body_skin_visible_ref_image_1_geometry_gate_pass",
    "post_mf70_body_skin_visible_ref_image_1_promotion_gate_pass",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_MF70_BODY_SKIN_VISIBLE_REF_IMAGE_1_{STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_MF70_BODY_SKIN_VISIBLE_REF_IMAGE_1_{STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_MF70_BODY_SKIN_VISIBLE_REF_IMAGE_1_{STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_MF70_BODY_SKIN_VISIBLE_REF_IMAGE_1_{STAMP}.json",
]

ROW_NOTE = (
    "Ref_Image_1 body skin visible post-evaluation gates 20260708T140617-0500: "
    "geometry and promotion hard gates passed with 332 checked rows, zero pass-like rows, "
    "and zero failures. Composite visible-body-skin gold reference remains available across "
    "two Ref_Image_1 layout groups. Top strip is partial upper-body only; lower strip is "
    "primary full-body validation. Row remains Required_Not_Complete until route, visual QA, "
    "generated-output proof, target runtime, and explicit row approval evidence pass."
)

CSV_TARGETS = [
    (
        PROJECT_ROOT
        / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
        "Tracker_ID",
        TRACKER_ID,
    ),
    (
        PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
        "Tracker_ID",
        TRACKER_ID,
    ),
    (
        PROJECT_ROOT
        / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
        "Item_ID",
        ITEM_ID,
    ),
    (
        PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
        "Item_ID",
        ITEM_ID,
    ),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = [
    "CURRENT_SESSION_STATE.md",
    "CURRENT_PURSUING_GOAL.md",
    "RESUME_HERE_NEXT_CODEX_SESSION.md",
    "NEXT_ACTION.md",
    "QA_EVIDENCE_INDEX.md",
]


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, target: str) -> int:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    updates = 0
    for row in rows:
        if row.get(key) != target:
            continue
        updates += 1
        row["Status"] = "Required_Not_Complete"
        if "Status_Decision" in row:
            row["Status_Decision"] = STATUS_DECISION
        if "Evidence_Path" in row:
            row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), EVIDENCE_PATHS)
        if "Evidence_Required" in row:
            row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), EVIDENCE_PATHS)
        if "Acceptance_Evidence" in row:
            row["Acceptance_Evidence"] = append_unique(
                row.get("Acceptance_Evidence", ""), EVIDENCE_PATHS
            )
        if "Acceptance_Criteria" in row:
            row["Acceptance_Criteria"] = append_unique(
                row.get("Acceptance_Criteria", ""), EVIDENCE_PATHS
            )
        if "Coverage_Audit_Status" in row:
            row["Coverage_Audit_Status"] = append_unique(
                row.get("Coverage_Audit_Status", ""), COVERAGE_TOKENS
            )
        if "Notes" in row:
            row["Notes"] = append_unique(row.get("Notes", ""), [ROW_NOTE])

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return updates


def hydration_block(title_kind: str) -> str:
    if title_kind == "next":
        heading = (
            f"## Immediate Next Action - {ISO_TS} - Work {NEXT_TRACKER_ID} "
            "Whole-Body Dependency Probe Locally"
        )
        tail = (
            f"Next exact local action: work `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`. "
            "Do not start EC2, do not promote body/hand/contact masks, and keep Ref_Image_1 "
            "top-strip partial-body semantics in force for later body-mask rows."
        )
    elif title_kind == "resume":
        heading = f"## Resume Update - 0159 Ref_Image_1 Gates Passed - {ISO_TS}"
        tail = (
            f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`. Keep 0159 non-promotional; "
            "the gates prove lockdown consistency only, not production-route completion."
        )
    elif title_kind == "qa":
        heading = f"## Wave70 0159 Ref_Image_1 Gate Evidence - {ISO_TS}"
        tail = (
            "QA note: both post-evaluation hard gates passed with 332 checked rows, zero "
            "pass-like rows, and zero failures."
        )
    elif title_kind == "goal":
        heading = f"## Current Pursuing Goal Update - 0159 Gates Passed - {ISO_TS}"
        tail = (
            f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` after "
            "0159 gate attachment."
        )
    else:
        heading = f"## Session State Update - 0159 Ref_Image_1 Gates Passed - {ISO_TS}"
        tail = (
            f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`, the whole-body "
            "dependency/model probe."
        )

    bullets = "\n".join(f"- `{path}`" for path in EVIDENCE_PATHS)
    return f"""{heading}

Re-evaluated `{TRACKER_ID}` / `{ITEM_ID}` against the corrected Ref_Image_1 body-skin composite gold reference and attached the post-evaluation hard-gate evidence.

Result: the Ref_Image_1 composite visible-body-skin reference remains available, but the row stays `Required_Not_Complete` because reference availability and global lockdown gates do not prove routing, generated output, target runtime, visual QA, or explicit row approval. The top strip is partial upper-body reference only; the lower strip is the primary full-body validation region.

Gate evidence:

{bullets}

{tail}

"""


def prepend_once(path: Path, block: str, marker: str) -> bool:
    existing = path.read_text(encoding="utf-8")
    if marker in existing[:4000]:
        return False
    path.write_text(block + existing, encoding="utf-8", newline="\n")
    return True


def append_proof_log() -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    row = [
        ISO_TS,
        "70",
        "Wave70 0159 Ref_Image_1 body skin post-evaluation gates",
        (
            "Ran post-Ref_Image_1 geometry and promotion hard gates for TRK/ITEM-W70-0159, "
            "attached gate evidence, preserved the corrected top-strip partial-body rule, "
            "and kept the row Required_Not_Complete/non-promotional."
        ),
        "; ".join(
            [
                *EVIDENCE_PATHS,
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_body_skin_visible_ref_image_1_gold_standard.json",
                "runtime_artifacts/mask_factory/wave70_mf70_body_skin_visible_ref_image_1/20260708T140318-0500/mf70_body_skin_visible_ref_image_1_gold_standard_panel.png",
            ]
        ),
        "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; JSON validation; panel inspection; CSV row verification",
        "REF_IMAGE_1_BODY_SKIN_VISIBLE_GATES_PASS_ROUTE_NOT_COMPLETE",
        "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_body_skin_visible_ref_image_1_gold_standard.json",
        f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} local whole-body dependency/model probe; do not promote masks.",
    ]
    with proof_path.open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(row)


def main() -> None:
    updates = {}
    for path, key, target in CSV_TARGETS:
        updates[str(path.relative_to(PROJECT_ROOT))] = update_csv(path, key, target)

    markers = {
        "CURRENT_SESSION_STATE.md": "Session State Update - 0159 Ref_Image_1 Gates Passed",
        "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0159 Gates Passed",
        "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0159 Ref_Image_1 Gates Passed",
        "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:06:17-05:00 - Work TRK-W70-0162",
        "QA_EVIDENCE_INDEX.md": "Wave70 0159 Ref_Image_1 Gate Evidence",
    }
    block_types = {
        "CURRENT_SESSION_STATE.md": "state",
        "CURRENT_PURSUING_GOAL.md": "goal",
        "RESUME_HERE_NEXT_CODEX_SESSION.md": "resume",
        "NEXT_ACTION.md": "next",
        "QA_EVIDENCE_INDEX.md": "qa",
    }
    hydration_updates = {}
    for name in HYDRATION_FILES:
        path = HYDRATION_DIR / name
        hydration_updates[name] = prepend_once(
            path, hydration_block(block_types[name]), markers[name]
        )

    append_proof_log()

    print(
        {
            "csv_updates": updates,
            "hydration_updates": hydration_updates,
            "proof_log_appended": True,
            "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
        }
    )


if __name__ == "__main__":
    main()
