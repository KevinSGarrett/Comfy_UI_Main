from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T14:38:46-05:00"
TORSO_STAMP = "20260708T143828-0500"
FULL_REF_STAMP = "20260708T143650-0500"
GATE_STAMP = "20260708T143846-0500"
TRACKER_ID = "TRK-W70-0167"
ITEM_ID = "ITEM-W70-0167"
NEXT_TRACKER_ID = "TRK-W70-0168"
NEXT_ITEM_ID = "ITEM-W70-0168"

STATUS_DECISION = "ref_image_1_full_body_torso_references_available_route_not_complete_global_gates_pass"
COVERAGE_TOKENS = [
    "ref_image_1_full_body_torso_references_available",
    "ref_image_1_full_new_folder_knees_to_head_not_full_body_exception_recorded",
    "torso_route_not_complete_no_promotion",
    "post_torso_region_full_ref_image_1_geometry_gate_pass",
    "post_torso_region_full_ref_image_1_promotion_gate_pass",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_REF_IMAGE_1_FULL_BODY_REFERENCES_{FULL_REF_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_full_body_references.json",
    f"Plan/Tracker/Evidence/W70_REF_IMAGE_1_FULL_BODY_REFERENCES_{FULL_REF_STAMP}.json",
    "Plan/Tracker/Evidence/ref_image_1_full_body_references.json",
    f"runtime_artifacts/mask_factory/ref_image_1_full_body_references/{FULL_REF_STAMP}/ref_image_1_full_body_references.json",
    f"runtime_artifacts/mask_factory/ref_image_1_full_body_references/{FULL_REF_STAMP}/ref_image_1_full_body_references_contact_sheet.png",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_TORSO_ABDOMEN_UMBILICUS_AUTHORITY_{TORSO_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/torso_abdomen_umbilicus_authority.json",
    f"Plan/Tracker/Evidence/W70_TORSO_ABDOMEN_UMBILICUS_AUTHORITY_{TORSO_STAMP}.json",
    "Plan/Tracker/Evidence/torso_abdomen_umbilicus_authority.json",
    f"runtime_artifacts/mask_factory/wave70_torso_abdomen_umbilicus_authority/{TORSO_STAMP}/torso_abdomen_umbilicus_authority.json",
    f"runtime_artifacts/mask_factory/wave70_torso_abdomen_umbilicus_authority/{TORSO_STAMP}/torso_abdomen_umbilicus_authority_reference_route_panel.png",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_TORSO_REGION_FULL_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_TORSO_REGION_FULL_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_TORSO_REGION_FULL_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_TORSO_REGION_FULL_REF_IMAGE_1_{GATE_STAMP}.json",
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - 0167 Full Reference Torso Gates Passed",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0167 Full Reference Torso Gates Passed",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0167 Full Reference Torso Gates Passed",
    "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:38:46-05:00 - Re-evaluate TRK-W70-0168 Limb Joint Authority",
    "QA_EVIDENCE_INDEX.md": "Wave70 0167 Full Reference Torso Gate Evidence",
}


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def gate_summary(path: str) -> dict[str, object]:
    payload = json.loads((PROJECT_ROOT / path).read_text(encoding="utf-8"))
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def update_csv(path: Path, key: str, target: str) -> int:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    note = (
        "Torso abdomen umbilicus authority 20260708T143828-0500: Ref_Image_1/Full provides 8 full/near-full body "
        "references with one user-corrected knees-to-head near-full exception under Full/New folder. Ref_Image_1 gold "
        "standard provides 9 torso/abdomen/pelvic/glute/breast masks. Prior portrait-only visibility blocker is "
        "superseded for this reference evaluation. Post-evaluation geometry and promotion gates passed with 332 checked "
        "rows, zero pass-like rows, and zero failures. Row remains Required_Not_Complete; no masks promoted."
    )
    changed = 0
    for row in rows:
        if row.get(key) != target:
            continue
        changed += 1
        row["Status"] = "Required_Not_Complete"
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
            f"Next exact local action: re-evaluate `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` limb joint authority. "
            "Use `Ref_Image_1/Full` plus the gold masks as body reference inputs; keep the `Full/New folder` image "
            "limited to knees-to-head coverage and do not use it for feet/toes/lower-calf proof."
        )
    elif name == "RESUME_HERE_NEXT_CODEX_SESSION.md":
        tail = f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` limb joint authority re-evaluation."
    elif name == "QA_EVIDENCE_INDEX.md":
        tail = "QA note: both post-rerun hard gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    elif name == "CURRENT_PURSUING_GOAL.md":
        tail = f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` limb joint authority re-evaluation."
    else:
        tail = f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` limb joint authority re-evaluation."
    return f"""## {heading}

Re-ran `{TRACKER_ID}` / `{ITEM_ID}` torso/abdomen/umbilicus authority with the corrected body reference inputs.

Result: `Ref_Image_1/Full` now provides 8 full/near-full reference images, with the `Full/New folder` image explicitly limited to knees-to-head coverage. `Ref_Image_1` gold-standard masks provide 9 torso/abdomen/pelvic/glute/breast references. The prior portrait-only torso visibility blocker is superseded for this reference evaluation.

The row remains `Required_Not_Complete` because reference availability does not prove semantic human-part parsing, contact ownership, canonical body polygons, generated output, target runtime, visual QA, or promotion evidence. No masks were promoted.

Post-rerun gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence}

{tail}

"""


def prepend_once(path: Path, text: str, marker: str) -> bool:
    existing = path.read_text(encoding="utf-8")
    if marker in existing[:8000]:
        return False
    path.write_text(text + existing, encoding="utf-8", newline="\n")
    return True


def append_proof_log() -> None:
    row = [
        ISO_TS,
        "70",
        "Wave70 0167 torso full-reference rerun and gates passed",
        (
            "Reran TRK/ITEM-W70-0167 with Ref_Image_1/Full as body reference input, recorded 8 full/near-full images "
            "and the knees-to-head exception, attached torso gold masks and post-rerun geometry/promotion gates, and "
            "kept the row Required_Not_Complete/non-promotional."
        ),
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; Ref_Image_1/Full recursive manifest; Ref_Image_1 gold mask manifest validation; JSON validation; reference panel inspection; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "TORSO_FULL_REFERENCE_AVAILABLE_ROUTE_NOT_COMPLETE_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_TORSO_ABDOMEN_UMBILICUS_AUTHORITY_{TORSO_STAMP}.json",
        f"Re-evaluate {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} limb joint authority with Ref_Image_1/Full and gold masks; no promotion without row-level proof.",
    ]
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(row)


def main() -> None:
    geometry = gate_summary(EVIDENCE_PATHS[-4])
    promotion = gate_summary(EVIDENCE_PATHS[-3])
    if geometry != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected geometry gate summary: {geometry}")
    if promotion != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected promotion gate summary: {promotion}")
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
            "geometry_gate": geometry,
            "promotion_gate": promotion,
            "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
        }
    )


if __name__ == "__main__":
    main()
