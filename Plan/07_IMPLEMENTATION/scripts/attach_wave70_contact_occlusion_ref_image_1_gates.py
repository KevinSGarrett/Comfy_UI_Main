from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T14:55:09-05:00"
CONTACT_STAMP = "20260708T145450-0500"
FULL_REF_STAMP = "20260708T143650-0500"
GATE_STAMP = "20260708T145509-0500"
TRACKER_ID = "TRK-W70-0171"
ITEM_ID = "ITEM-W70-0171"
NEXT_TRACKER_ID = "TRK-W70-0172"
NEXT_ITEM_ID = "ITEM-W70-0172"

STATUS_DECISION = "ref_image_1_contact_actor_references_available_route_not_complete_global_gates_pass"
COVERAGE_TOKENS = [
    "ref_image_1_contact_actor_references_available",
    "contact_occlusion_ownership_route_not_complete_no_promotion",
    "post_contact_occlusion_ref_image_1_geometry_gate_pass",
    "post_contact_occlusion_ref_image_1_promotion_gate_pass",
]

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_CONTACT_OCCLUSION_OWNERSHIP_AUTHORITY_{CONTACT_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/contact_occlusion_ownership_authority.json",
    f"Plan/Tracker/Evidence/W70_CONTACT_OCCLUSION_OWNERSHIP_AUTHORITY_{CONTACT_STAMP}.json",
    "Plan/Tracker/Evidence/contact_occlusion_ownership_authority.json",
    f"runtime_artifacts/mask_factory/wave70_contact_occlusion_ownership_authority/{CONTACT_STAMP}/contact_occlusion_ownership_authority.json",
    f"runtime_artifacts/mask_factory/wave70_contact_occlusion_ownership_authority/{CONTACT_STAMP}/contact_occlusion_ownership_authority_reference_route_panel.png",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_REF_IMAGE_1_FULL_BODY_REFERENCES_{FULL_REF_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_full_body_references.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_CONTACT_OCCLUSION_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_CONTACT_OCCLUSION_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_CONTACT_OCCLUSION_REF_IMAGE_1_{GATE_STAMP}.json",
    f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_CONTACT_OCCLUSION_REF_IMAGE_1_{GATE_STAMP}.json",
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - 0171 Contact Occlusion Ref_Image_1 Gates Passed",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - 0171 Contact Occlusion Ref_Image_1 Gates Passed",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - 0171 Contact Occlusion Ref_Image_1 Gates Passed",
    "NEXT_ACTION.md": "Immediate Next Action - 2026-07-08T14:55:09-05:00 - Re-evaluate TRK-W70-0172 Body Region Geometry",
    "QA_EVIDENCE_INDEX.md": "Wave70 0171 Contact Occlusion Ref_Image_1 Gate Evidence",
}


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def gate_summary(path: str) -> dict[str, int]:
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
        "Contact occlusion ownership authority 20260708T145450-0500: Ref_Image_1 gold standard provides 8 hand/finger "
        "actor masks, 4 foot/support actor masks, and 20 body surface masks; Ref_Image_1/Full provides 8 context references. "
        "Prior portrait-only contact blocker is superseded for this reference evaluation. Post-evaluation geometry and promotion "
        "gates passed with 332 checked rows, zero pass-like rows, and zero failures. Row remains Required_Not_Complete; no masks promoted."
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
        tail = f"Next exact local action: re-evaluate `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body region geometry resolver with Ref_Image_1/Full and gold-mask context."
    elif name == "RESUME_HERE_NEXT_CODEX_SESSION.md":
        tail = f"Resume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body region geometry resolver."
    elif name == "QA_EVIDENCE_INDEX.md":
        tail = "QA note: both post-rerun hard gates passed with 332 checked rows, zero pass-like rows, and zero failures."
    elif name == "CURRENT_PURSUING_GOAL.md":
        tail = f"Current pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body region geometry resolver."
    else:
        tail = f"Next local action is `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body region geometry resolver."
    return f"""## {heading}

Re-ran `{TRACKER_ID}` / `{ITEM_ID}` contact occlusion ownership authority with Ref_Image_1 gold actor references and Full context.

Result: Ref_Image_1 supplies 8 hand/finger actor masks, 4 foot/support actor masks, and 20 body-surface references. `Ref_Image_1/Full` supplies 8 context references. The prior portrait-only contact blocker is superseded for this reference evaluation.

The row remains `Required_Not_Complete` because reference actors do not prove contact pair ownership, parser-backed body/object ownership, occlusion transfer, protected-overlap thresholds, owner-overlap metrics, canonical contact polygons, generated output, target runtime, visual QA, or promotion evidence. No masks were promoted.

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
        "Wave70 0171 contact occlusion Ref_Image_1 rerun and gates passed",
        (
            "Reran TRK/ITEM-W70-0171 with Ref_Image_1 contact actor references and Full context, attached evidence "
            "and post-rerun geometry/promotion gates, and kept the row Required_Not_Complete/non-promotional."
        ),
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; Ref_Image_1 gold actor manifest validation; Full reference manifest validation; JSON validation; reference panel inspection; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "CONTACT_OCCLUSION_REF_IMAGE_1_REFERENCE_AVAILABLE_ROUTE_NOT_COMPLETE_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_CONTACT_OCCLUSION_OWNERSHIP_AUTHORITY_{CONTACT_STAMP}.json",
        f"Re-evaluate {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} body region geometry resolver; no promotion without row-level proof.",
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
