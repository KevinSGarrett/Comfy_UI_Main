from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T14:15:12-05:00"
PROBE_STAMP = "20260708T141411-0500"
GATE_STAMP = "20260708T141512-0500"
TRACKER_ID = "TRK-W70-0162"
ITEM_ID = "ITEM-W70-0162"
NEXT_TRACKER_ID = "TRK-W70-0164"
NEXT_ITEM_ID = "ITEM-W70-0164"

STATUS_DECISION = (
    "blocked_body_geometry_dependency_missing_human_part_person_instance_temporal_contact_routes_missing_"
    "pose_hand_sam_assets_available_runtime_unvalidated"
)
COVERAGE_TOKENS = [
    "post_whole_body_dependency_probe_geometry_gate_pass",
    "post_whole_body_dependency_probe_promotion_gate_pass",
    "whole_body_dependency_probe_pose_hand_sam_assets_available_runtime_unvalidated",
    "whole_body_dependency_probe_human_part_person_instance_temporal_contact_routes_missing",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_WHOLE_BODY_GEOMETRY_DEPENDENCY_PROBE_{PROBE_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_geometry_dependency_probe.json",
    f"Plan/Tracker/Evidence/W70_WHOLE_BODY_GEOMETRY_DEPENDENCY_PROBE_{PROBE_STAMP}.json",
    "Plan/Tracker/Evidence/body_geometry_dependency_probe.json",
    f"runtime_artifacts/mask_factory/wave70_whole_body_geometry_dependency_probe/{PROBE_STAMP}/body_geometry_dependency_probe.json",
    f"runtime_artifacts/mask_factory/wave70_whole_body_geometry_dependency_probe/{PROBE_STAMP}/body_geometry_dependency_probe_panel.png",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_{GATE_STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_{GATE_STAMP}.json",
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - 0162 Whole-Body Dependency Probe Gates Passed",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0162 Whole-Body Dependency Probe Gates Passed",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0162 Whole-Body Dependency Probe Gates Passed",
    "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:15:12-05:00 - Re-evaluate TRK-W70-0164 Pose Landmark Authority",
    "QA_EVIDENCE_INDEX.md": "Wave70 0162 Whole-Body Dependency Probe Gate Evidence",
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
        "Whole-body geometry dependency probe 20260708T141411-0500 refreshed current local model state: "
        "pose, hand, and SAM-style refinement assets are present but runtime-unvalidated; full-body human-part parsing, "
        "person-instance segmentation, temporal propagation, and contact ownership remain missing or unproven. "
        "Post-probe geometry and promotion gates passed with 332 checked rows, zero pass-like rows, and zero failures. "
        "No masks promoted."
    )
    for row in rows:
        if row.get(key) != target:
            continue
        changed += 1
        row["Status"] = "Blocked_Body_Geometry_Dependency_Missing"
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


def block(kind: str) -> str:
    if kind == "NEXT_ACTION.md":
        heading = HYDRATION_FILES[kind]
        tail = (
            f"Next exact local action: re-evaluate `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` with the current local pose "
            "asset state. Keep `0163` person-instance ownership blocked because the refreshed dependency probe still "
            "does not find a proven person-instance segmentation route."
        )
    elif kind == "RESUME_HERE_NEXT_CODEX_SESSION.md":
        heading = HYDRATION_FILES[kind]
        tail = (
            f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` pose landmark authority re-evaluation. Do not promote "
            "masks; local pose assets are available but runtime proof is still required."
        )
    elif kind == "QA_EVIDENCE_INDEX.md":
        heading = HYDRATION_FILES[kind]
        tail = "QA note: both post-probe hard gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    elif kind == "CURRENT_PURSUING_GOAL.md":
        heading = HYDRATION_FILES[kind]
        tail = f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` pose landmark authority re-evaluation."
    else:
        heading = HYDRATION_FILES[kind]
        tail = f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` pose landmark authority re-evaluation."
    evidence = "\n".join(f"- `{path}`" for path in EVIDENCE_PATHS)
    return f"""## {heading}

Refreshed `{TRACKER_ID}` / `{ITEM_ID}` whole-body dependency/model probe against current local model state.

Result: pose, hand, and SAM-style refinement assets are now detected locally, but they remain runtime-unvalidated. Full-body human-part parsing, person-instance segmentation, temporal propagation, and contact ownership remain missing or unproven, so whole-body geometry authority stays fail-closed and no body/hand/contact mask is promoted. Ref_Image_1 is present and its top strip remains partial upper-body only; the lower strip remains the full-body validation region.

Post-probe gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

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
        "Wave70 0162 whole-body dependency probe refreshed and gates passed",
        (
            "Reran TRK/ITEM-W70-0162 current-state whole-body dependency probe, detected local pose/hand/SAM assets "
            "as available but runtime-unvalidated, preserved fail-closed blockers for human parsing, person-instance "
            "segmentation, temporal propagation, and contact ownership, attached post-probe hard-gate evidence, and "
            "kept all masks non-promotional."
        ),
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; dependency/model-file scan; JSON validation; panel inspection; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "WHOLE_BODY_DEPENDENCY_PROBE_REFINED_BLOCKER_LOCKDOWN_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_WHOLE_BODY_GEOMETRY_DEPENDENCY_PROBE_{PROBE_STAMP}.json",
        f"Re-evaluate {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} pose landmark authority with current local pose assets; do not promote masks.",
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
