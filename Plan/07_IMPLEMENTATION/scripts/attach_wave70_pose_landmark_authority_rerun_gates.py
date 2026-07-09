from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T14:18:39-05:00"
POSE_STAMP = "20260708T141735-0500"
GATE_STAMP = "20260708T141839-0500"
TRACKER_ID = "TRK-W70-0164"
ITEM_ID = "ITEM-W70-0164"
NEXT_TRACKER_ID = "TRK-W70-0165"
NEXT_ITEM_ID = "ITEM-W70-0165"

STATUS_DECISION = "pose_landmark_route_executed_source_derived_partial_full_body_authority_still_blocked_global_gates_pass"
COVERAGE_TOKENS = [
    "post_pose_landmark_authority_rerun_geometry_gate_pass",
    "post_pose_landmark_authority_rerun_promotion_gate_pass",
    "pose_landmark_route_executed_source_derived_partial",
    "whole_body_authority_still_blocked_no_mask_promotion",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_POSE_LANDMARK_AUTHORITY_{POSE_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/pose_landmark_authority.json",
    f"Plan/Tracker/Evidence/W70_POSE_LANDMARK_AUTHORITY_{POSE_STAMP}.json",
    "Plan/Tracker/Evidence/pose_landmark_authority.json",
    f"runtime_artifacts/mask_factory/wave70_pose_landmark_authority/{POSE_STAMP}/pose_landmark_authority.json",
    f"runtime_artifacts/mask_factory/wave70_pose_landmark_authority/{POSE_STAMP}/pose_landmark_authority_panel.png",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_POSE_LANDMARK_AUTHORITY_RERUN_{GATE_STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_POSE_LANDMARK_AUTHORITY_RERUN_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_POSE_LANDMARK_AUTHORITY_RERUN_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_POSE_LANDMARK_AUTHORITY_RERUN_{GATE_STAMP}.json",
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - 0164 Pose Landmark Rerun Gates Passed",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0164 Pose Landmark Rerun Gates Passed",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0164 Pose Landmark Rerun Gates Passed",
    "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:18:39-05:00 - Re-evaluate TRK-W70-0165 Hand Finger Authority",
    "QA_EVIDENCE_INDEX.md": "Wave70 0164 Pose Landmark Rerun Gate Evidence",
}


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, target: str) -> int:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    changed = 0
    note = (
        "Pose landmark authority rerun 20260708T141735-0500: MediaPipe PoseLandmarker executed on the active portrait "
        "source and produced one detected person, 33 pose landmarks, and one segmentation mask. This is source-derived "
        "partial pose evidence only; full-body/contact authority remains blocked and no masks were promoted. "
        "Post-rerun geometry and promotion gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    )
    for row in rows:
        if row.get(key) != target:
            continue
        changed += 1
        row["Status"] = "Pose_Landmark_Authority_Source_Derived_Partial"
        if "Status_Decision" in row:
            row["Status_Decision"] = STATUS_DECISION
        for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
            if field in row:
                row[field] = append_unique(row.get(field, ""), EVIDENCE_PATHS)
        if "Coverage_Audit_Status" in row:
            row["Coverage_Audit_Status"] = append_unique(row.get("Coverage_Audit_Status", ""), COVERAGE_TOKENS)
        if "Notes" in row:
            row["Notes"] = append_unique(row.get("Notes", ""), [note])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return changed


def block(name: str) -> str:
    heading = HYDRATION_FILES[name]
    evidence = "\n".join(f"- `{path}`" for path in EVIDENCE_PATHS)
    if name == "NEXT_ACTION.md":
        tail = (
            f"Next exact local action: re-evaluate `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` hand/finger landmark authority. "
            "Keep the active portrait and Ref_Image_1 contexts separate: active portrait hand visibility may still be absent, "
            "while Ref_Image_1 lower strip can support reference/gold-standard checks without promoting masks."
        )
    elif name == "RESUME_HERE_NEXT_CODEX_SESSION.md":
        tail = f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` hand/finger authority re-evaluation."
    elif name == "QA_EVIDENCE_INDEX.md":
        tail = "QA note: both post-rerun hard gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    elif name == "CURRENT_PURSUING_GOAL.md":
        tail = f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` hand/finger authority re-evaluation."
    else:
        tail = f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` hand/finger authority re-evaluation."
    return f"""## {heading}

Re-ran `{TRACKER_ID}` / `{ITEM_ID}` pose landmark authority against current local pose assets.

Result: MediaPipe PoseLandmarker executed on the active portrait source and produced one detected person, 33 pose landmarks, and one segmentation mask. This is valid source-derived partial pose evidence, but it does not satisfy whole-body geometry authority because the source lacks full-body, feet, temporal, and contact coverage. No masks were promoted.

Post-rerun gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence}

{tail}

"""


def prepend_once(path: Path, text: str, marker: str) -> bool:
    existing = path.read_text(encoding="utf-8")
    if marker in existing[:6000]:
        return False
    path.write_text(text + existing, encoding="utf-8", newline="\n")
    return True


def append_proof_log() -> None:
    row = [
        ISO_TS,
        "70",
        "Wave70 0164 pose landmark authority rerun and gates passed",
        (
            "Reran TRK/ITEM-W70-0164 with current local MediaPipe pose asset, produced one portrait person, 33 pose "
            "landmarks, and one segmentation mask, preserved partial/non-promotional status, attached post-rerun "
            "geometry and promotion gate evidence, and kept whole-body authority blocked."
        ),
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; MediaPipe PoseLandmarker inference; JSON validation; panel inspection; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "POSE_LANDMARK_AUTHORITY_PARTIAL_RERUN_LOCKDOWN_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_POSE_LANDMARK_AUTHORITY_{POSE_STAMP}.json",
        f"Re-evaluate {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} hand/finger authority with active-source and Ref_Image_1 contexts kept separate.",
    ]
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(row)


def main() -> None:
    csv_updates = {str(path.relative_to(PROJECT_ROOT)): update_csv(path, key, target) for path, key, target in CSV_TARGETS}
    hydration_updates = {
        name: prepend_once(HYDRATION_DIR / name, block(name), marker)
        for name, marker in HYDRATION_FILES.items()
    }
    append_proof_log()
    print(
        {
            "csv_updates": csv_updates,
            "hydration_updates": hydration_updates,
            "proof_log_appended": True,
            "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
        }
    )


if __name__ == "__main__":
    main()
