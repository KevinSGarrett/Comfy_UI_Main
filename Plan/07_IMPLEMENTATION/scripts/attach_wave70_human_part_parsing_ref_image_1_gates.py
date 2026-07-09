from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T14:27:40-05:00"
PARSER_STAMP = "20260708T142544-0500"
GATE_STAMP = "20260708T142740-0500"
TRACKER_ID = "TRK-W70-0166"
ITEM_ID = "ITEM-W70-0166"
NEXT_TRACKER_ID = "TRK-W70-0167"
NEXT_ITEM_ID = "ITEM-W70-0167"

STATUS_DECISION = "blocked_exact_local_human_part_parsing_route_unavailable_ref_image_1_reference_masks_available_global_gates_pass"
COVERAGE_TOKENS = [
    "post_human_part_parsing_ref_image_1_geometry_gate_pass",
    "post_human_part_parsing_ref_image_1_promotion_gate_pass",
    "human_part_parser_runtime_unavailable",
    "ref_image_1_labeled_part_masks_available_reference_only",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_HUMAN_PART_PARSING_AUTHORITY_{PARSER_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/human_part_parsing_authority.json",
    f"Plan/Tracker/Evidence/W70_HUMAN_PART_PARSING_AUTHORITY_{PARSER_STAMP}.json",
    "Plan/Tracker/Evidence/human_part_parsing_authority.json",
    f"runtime_artifacts/mask_factory/wave70_human_part_parsing_authority/{PARSER_STAMP}/human_part_parsing_authority.json",
    f"runtime_artifacts/mask_factory/wave70_human_part_parsing_authority/{PARSER_STAMP}/human_part_parsing_authority_blocker_panel.png",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_HUMAN_PART_PARSING_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_HUMAN_PART_PARSING_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_HUMAN_PART_PARSING_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_HUMAN_PART_PARSING_REF_IMAGE_1_{GATE_STAMP}.json",
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - 0166 Human Part Parsing Ref_Image_1 Gates Passed",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0166 Human Part Parsing Ref_Image_1 Gates Passed",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0166 Human Part Parsing Ref_Image_1 Gates Passed",
    "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:27:40-05:00 - Re-evaluate TRK-W70-0167 Torso Region Authority",
    "QA_EVIDENCE_INDEX.md": "Wave70 0166 Human Part Parsing Ref_Image_1 Gate Evidence",
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
        "Human part parsing authority rerun 20260708T142544-0500: local OneFormer/Uniformer/DensePose/SAM routes still "
        "do not produce semantic full-body part parsing; face/lip parsing assets are not full-body parser proof. "
        "Ref_Image_1 supplies 34 labeled body-part masks as reference-only evidence, not parser runtime output. "
        "Post-rerun geometry and promotion gates passed with 332 checked rows, zero pass-like rows, and zero failures. "
        "No masks promoted."
    )
    for row in rows:
        if row.get(key) != target:
            continue
        changed += 1
        row["Status"] = "Blocked_Human_Part_Parsing_Route_Unavailable"
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
            f"Next exact local action: re-evaluate `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` torso/abdomen/umbilicus "
            "authority. Use Ref_Image_1 torso/abdomen masks as reference-only evidence while keeping active portrait "
            "source visibility separate."
        )
    elif name == "RESUME_HERE_NEXT_CODEX_SESSION.md":
        tail = f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` torso region authority re-evaluation."
    elif name == "QA_EVIDENCE_INDEX.md":
        tail = "QA note: both post-rerun hard gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    elif name == "CURRENT_PURSUING_GOAL.md":
        tail = f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` torso region authority re-evaluation."
    else:
        tail = f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` torso region authority re-evaluation."
    return f"""## {heading}

Re-ran `{TRACKER_ID}` / `{ITEM_ID}` human-part parsing authority with Ref_Image_1 reference context.

Result: no local route produced semantic full-body human-part parsing for skin, hair, clothing, torso, limbs, feet, and background. Ref_Image_1 provides 34 labeled body-part masks as reference/gold evidence, but those masks are not parser runtime output and do not prove active-source semantic parsing. No masks were promoted.

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
        "Wave70 0166 human part parsing Ref_Image_1 rerun and gates passed",
        (
            "Reran TRK/ITEM-W70-0166 human-part parsing authority, recorded that local parser routes still do not "
            "produce semantic full-body part parsing, captured Ref_Image_1 labeled masks as reference-only evidence, "
            "attached post-rerun geometry and promotion gate evidence, and kept masks non-promotional."
        ),
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; local ControlNet Aux parser route probes; Ref_Image_1 manifest validation; JSON validation; panel inspection; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "HUMAN_PART_PARSING_REF_IMAGE_1_REFERENCE_ONLY_LOCKDOWN_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_HUMAN_PART_PARSING_AUTHORITY_{PARSER_STAMP}.json",
        f"Re-evaluate {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} torso region authority with active-source and Ref_Image_1 contexts separate.",
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
