from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_WHOLE_BODY_ROWS_GATE_TOKEN_BACKFILL_{RUN_STAMP}"
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"

CSV_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

MODEL_TOKENS = [
    "model_backed_geometry_authority_evidence",
    "Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md",
    "Plan/07_IMPLEMENTATION/mask_factory/WAVE70_MODEL_BACKED_GEOMETRY_AUTHORITY.md",
    "Plan/07_IMPLEMENTATION/mask_factory/WAVE70_MODEL_BACKED_GEOMETRY_AUTHORITY_MATRIX.csv",
    "model_backed_geometry_authority_pass",
    "source_derived_landmark_or_segmentation_pass",
    "model_consensus_geometry_pass",
    "visibility_occlusion_confidence_pass",
    "no_symmetry_guessing_pass",
    "canonical_polygon_export_pass",
    "model_geometry_dependency_probe_pass",
]

GEOMETRY_TOKENS = [
    "wave70_mask_geometry_gate_pass",
    "Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md",
    "Plan/Instructions/QA/Scripts/Test-Wave70MaskGeometryGate.ps1",
]

PROMOTION_TOKENS = [
    "wave70_mask_promotion_gate_pass",
    "Plan/Instructions/QA/MASK_PROMOTION_HARD_GATE_PROTOCOL.md",
    "Plan/Instructions/QA/Scripts/Test-Wave70MaskPromotionGate.ps1",
]

NOTE = (
    "Whole-body row hard-gate backfill: newly added Wave70 whole-body rows remain fail-closed and now cite "
    "model-backed geometry, geometry hard-gate, and promotion hard-gate requirement tokens where missing. "
    "No masks promoted and no approval token emitted."
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [p.strip() for p in (existing or "").split(";") if p.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def row_number(row: dict[str, str]) -> int | None:
    raw = row.get("Tracker_ID") or row.get("Item_ID") or ""
    try:
        return int(raw.rsplit("-", 1)[1])
    except Exception:
        return None


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    updates: dict[str, list[str]] = {}

    for csv_path in CSV_FILES:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)

        changed_ids: list[str] = []
        for row in rows:
            n = row_number(row)
            if n is None or n < 154:
                continue
            row_id = row.get("Tracker_ID") or row.get("Item_ID") or ""
            additions = MODEL_TOKENS + GEOMETRY_TOKENS + PROMOTION_TOKENS

            for field in ["Completion_Criteria", "Acceptance_Criteria", "Acceptance_Evidence", "Evidence_Path", "Evidence_Required", "Validation_Method", "QA_Gates_Required"]:
                if field in row:
                    before = row.get(field, "")
                    row[field] = append_unique(before, additions)
                    if row[field] != before and row_id not in changed_ids:
                        changed_ids.append(row_id)

            if "Blocker_Policy" in row:
                row["Blocker_Policy"] = append_unique(
                    row.get("Blocker_Policy", ""),
                    [
                        "If model-backed geometry, whole-body geometry, mask geometry, or promotion hard gates are missing, write the exact blocker and do not promote generated-output stability.",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [NOTE])
            if "Status_Decision" in row and not row.get("Status_Decision"):
                row["Status_Decision"] = "required_not_complete_until_all_geometry_authority_and_hard_gate_evidence_passes"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_model_and_whole_body_geometry_authority_not_passed_until_exact_source_evidence"],
                )

        if changed_ids:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(csv_path)] = changed_ids

    evidence = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "result": "whole_body_rows_gate_tokens_backfilled_fail_closed",
        "task": "Backfill missing fail-closed Wave70 gate requirement tokens on newly added whole-body rows 0154..0178.",
        "updated_files": updates,
        "tokens_added_if_missing": {
            "model_backed_geometry": MODEL_TOKENS,
            "geometry_gate": GEOMETRY_TOKENS,
            "promotion_gate": PROMOTION_TOKENS,
        },
        "promotion_decision": "no_mask_promoted_no_active_input_changed_no_approval_token_emitted",
    }
    for path in [
        QA_DIR / f"{EVIDENCE_ID}.json",
        TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json",
    ]:
        path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(json.dumps({"result": evidence["result"], "evidence": f"Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/{EVIDENCE_ID}.json", "updated": updates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
