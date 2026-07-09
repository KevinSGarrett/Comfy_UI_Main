from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
CONSENSUS_STAMP = "20260708T181943-0500"
GATE_STAMP = "20260708T181943-0500"
MISSING_TRACKER_ID = "TRK-W70-0173"
MISSING_ITEM_ID = "ITEM-W70-0173"
TRACKER_ID = "TRK-W70-0148"
ITEM_ID = "ITEM-W70-0148"
NEXT_TRACKER_ID = "TRK-W70-0174"
NEXT_ITEM_ID = "ITEM-W70-0174"

STATUS_DECISION = "ref_images_1_2_reference_context_available_model_consensus_route_not_complete_sequence_ledger_gap_global_gates_pass"
COVERAGE_TOKENS = [
    "ref_images_1_2_combined_body_reference_matrix_available",
    "model_consensus_not_computable_from_reference_masks_alone",
    "wave70_0173_sequence_ledger_gap_detected",
    "actual_consensus_row_0148_updated",
    "model_consensus_route_not_complete_no_promotion",
    "post_model_consensus_ref_images_1_2_geometry_gate_pass",
    "post_model_consensus_ref_images_1_2_promotion_gate_pass",
]

QA_GEOMETRY_GATE = f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGES_1_2_{GATE_STAMP}.json"
QA_PROMOTION_GATE = f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGES_1_2_{GATE_STAMP}.json"
TRACKER_GEOMETRY_GATE = f"Plan/Tracker/Evidence/W70_MASK_GEOMETRY_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGES_1_2_{GATE_STAMP}.json"
TRACKER_PROMOTION_GATE = f"Plan/Tracker/Evidence/W70_MASK_PROMOTION_HARD_GATE_POST_MODEL_CONSENSUS_REF_IMAGES_1_2_{GATE_STAMP}.json"

EVIDENCE_PATHS = [
    f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MODEL_CONSENSUS_GEOMETRY_VALIDATOR_{CONSENSUS_STAMP}.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/model_consensus_geometry_validator.json",
    f"Plan/Tracker/Evidence/W70_MODEL_CONSENSUS_GEOMETRY_VALIDATOR_{CONSENSUS_STAMP}.json",
    "Plan/Tracker/Evidence/model_consensus_geometry_validator.json",
    f"runtime_artifacts/mask_factory/wave70_model_consensus_geometry_validator/{CONSENSUS_STAMP}/model_consensus_geometry_validator.json",
    f"runtime_artifacts/mask_factory/wave70_model_consensus_geometry_validator/{CONSENSUS_STAMP}/model_consensus_geometry_validator_reference_route_panel.png",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_full_body_references.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_2_body_reference.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json",
    QA_GEOMETRY_GATE,
    QA_PROMOTION_GATE,
    TRACKER_GEOMETRY_GATE,
    TRACKER_PROMOTION_GATE,
]

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
HYDRATION_FILES = {
    "CURRENT_SESSION_STATE.md": "Session State Update - Model Consensus Ref Images 1 2 Gates Passed With 0173 Ledger Gap",
    "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Model Consensus Ref Images 1 2 Gates Passed With 0173 Ledger Gap",
    "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Model Consensus Ref Images 1 2 Gates Passed With 0173 Ledger Gap",
    "NEXT_ACTION.md": "Immediate Next Action - Ref Images 1 2 - Work TRK-W70-0174 Soft-Body Protected Anchor Geometry",
    "QA_EVIDENCE_INDEX.md": "Wave70 Model Consensus Ref Images 1 2 Gate Evidence With 0173 Ledger Gap",
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
        f"Model consensus validator {CONSENSUS_STAMP}: `{MISSING_TRACKER_ID}` / `{MISSING_ITEM_ID}` is absent from Wave70 CSVs "
        f"and recorded as MILESTONE_SEQUENCE_LEDGER_GAP. Actual consensus row `{TRACKER_ID}` / `{ITEM_ID}` was updated with "
        "Ref_Image_1+Ref_Image_2 combined context. Independent model consensus remains not computable from reference masks alone. "
        "Geometry and promotion hard gates passed with 332 checked rows, zero pass-like rows, and zero failures. No masks promoted."
    )
    changed = 0
    for row in rows:
        if row.get(key) != target:
            continue
        changed += 1
        if "Status" in row:
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return changed


def hydration_block(name: str) -> str:
    evidence = "\n".join(f"- `{path}`" for path in EVIDENCE_PATHS)
    tail = f"Next exact local action: work `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body deformation and protected anchor geometry authority using Ref_Image_1+Ref_Image_2 combined references."
    if name == "CURRENT_PURSUING_GOAL.md":
        tail = f"Current pursuit remains Wave70 and advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`."
    return f"""## {HYDRATION_FILES[name]} - {ISO_TS}

Re-evaluated model consensus geometry with Ref_Image_1 plus Ref_Image_2 combined body-reference context.

Result: `{MISSING_TRACKER_ID}` / `{MISSING_ITEM_ID}` is absent from the Wave70 tracker/item CSVs and is recorded as `MILESTONE_SEQUENCE_LEDGER_GAP`. Evidence and gate attachments were applied to the actual model-consensus row `{TRACKER_ID}` / `{ITEM_ID}`. Combined reference context records 9 full/near-full references and 78 gold masks.

The row remains `Required_Not_Complete` because reference masks do not prove independent model consensus, multi-model parser/dense-pose agreement, canonical body polygons, IoU/boundary/center/protected-overlap metrics, generated output, visual QA, or promotion evidence. No masks were promoted.

Post-rerun gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence}

{tail}

"""


def prepend_once(path: Path, text: str, marker: str) -> bool:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing[:10000]:
        return False
    path.write_text(text + existing, encoding="utf-8", newline="\n")
    return True


def append_proof_log() -> None:
    row = [
        ISO_TS,
        "70",
        "Wave70 model consensus Ref_Image_1+2 gates passed with 0173 ledger gap",
        "Attached Ref_Image_1+2 model-consensus evidence and gates to actual row 0148; recorded missing 0173 row as MILESTONE_SEQUENCE_LEDGER_GAP; kept no-promotion Required_Not_Complete state.",
        "; ".join(EVIDENCE_PATHS),
        "python py_compile; implement_wave70_model_consensus_geometry_validator.py; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; CSV row verification",
        "REF_IMAGES_1_2_MODEL_CONSENSUS_ROUTE_NOT_COMPLETE_SEQUENCE_LEDGER_GAP_GATES_PASS",
        f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MODEL_CONSENSUS_GEOMETRY_VALIDATOR_{CONSENSUS_STAMP}.json",
        f"Continue Wave70 at {NEXT_TRACKER_ID} / {NEXT_ITEM_ID}.",
    ]
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(row)


def main() -> None:
    shutil.copyfile(PROJECT_ROOT / QA_GEOMETRY_GATE, PROJECT_ROOT / TRACKER_GEOMETRY_GATE)
    shutil.copyfile(PROJECT_ROOT / QA_PROMOTION_GATE, PROJECT_ROOT / TRACKER_PROMOTION_GATE)
    geometry = gate_summary(QA_GEOMETRY_GATE)
    promotion = gate_summary(QA_PROMOTION_GATE)
    if geometry != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected geometry gate summary: {geometry}")
    if promotion != {"checked": 332, "pass_like": 0, "failures": 0}:
        raise RuntimeError(f"Unexpected promotion gate summary: {promotion}")
    csv_updates = {str(path.relative_to(PROJECT_ROOT)): update_csv(path, key, target) for path, key, target in CSV_TARGETS}
    hydration_updates = {
        name: prepend_once(HYDRATION_DIR / name, hydration_block(name), marker)
        for name, marker in HYDRATION_FILES.items()
    }
    append_proof_log()
    print(
        json.dumps(
            {
                "csv_updates": csv_updates,
                "hydration_updates": hydration_updates,
                "proof_log_appended": True,
                "geometry_gate": geometry,
                "promotion_gate": promotion,
                "missing_row": f"{MISSING_TRACKER_ID} / {MISSING_ITEM_ID}",
                "actual_row": f"{TRACKER_ID} / {ITEM_ID}",
                "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
