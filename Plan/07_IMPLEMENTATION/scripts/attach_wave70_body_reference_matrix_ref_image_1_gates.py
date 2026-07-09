from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T15:31:18-05:00"
STAMP = "20260708T153118-0500"
TRACKER_ID = "TRK-W70-0176"
ITEM_ID = "ITEM-W70-0176"
NEXT_TRACKER_ID = "TRK-W70-0177"
NEXT_ITEM_ID = "ITEM-W70-0177"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

BODY_STAMPED = QA_DIR / f"W70_BODY_REFERENCE_MATRIX_AUTHORITY_{STAMP}.json"
BODY_CANONICAL = QA_DIR / "body_reference_matrix.json"
TRACKER_BODY_STAMPED = TRACKER_EVIDENCE_DIR / BODY_STAMPED.name
TRACKER_BODY_CANONICAL = TRACKER_EVIDENCE_DIR / BODY_CANONICAL.name
REF_IMAGE_2_STAMPED = QA_DIR / "W70_REF_IMAGE_2_BODY_REFERENCE_20260708T153111-0500.json"
REF_IMAGE_2_CANONICAL = QA_DIR / "ref_image_2_body_reference.json"
TRACKER_REF_IMAGE_2_STAMPED = TRACKER_EVIDENCE_DIR / REF_IMAGE_2_STAMPED.name
TRACKER_REF_IMAGE_2_CANONICAL = TRACKER_EVIDENCE_DIR / REF_IMAGE_2_CANONICAL.name
GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_{STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_{STAMP}.json"
TRACKER_GEOMETRY_GATE = TRACKER_EVIDENCE_DIR / GEOMETRY_GATE.name
TRACKER_PROMOTION_GATE = TRACKER_EVIDENCE_DIR / PROMOTION_GATE.name

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
]

STATUS_DECISION = "ref_images_1_2_body_reference_matrix_context_available_route_not_complete_global_gates_pass"
COVERAGE_TOKENS = [
    "ref_image_1_body_reference_matrix_context_available",
    "ref_image_2_body_reference_matrix_context_available",
    "body_reference_matrix_route_not_complete_no_promotion",
    "post_body_reference_matrix_ref_images_1_2_geometry_gate_pass",
    "post_body_reference_matrix_ref_images_1_2_promotion_gate_pass",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def gate_summary(path: Path) -> dict[str, int]:
    payload = read_json(path)
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def update_payloads(evidence_paths: list[str]) -> dict[str, int]:
    updates = {}
    for path in [BODY_STAMPED, BODY_CANONICAL, TRACKER_BODY_STAMPED, TRACKER_BODY_CANONICAL]:
        payload = read_json(path)
        artifacts = payload.setdefault("artifacts", {})
        artifacts["post_body_reference_matrix_geometry_gate"] = rel(GEOMETRY_GATE)
        artifacts["post_body_reference_matrix_promotion_gate"] = rel(PROMOTION_GATE)
        payload["post_evaluation_hard_gates"] = {
            "geometry": {"path": rel(GEOMETRY_GATE), **gate_summary(GEOMETRY_GATE)},
            "promotion": {"path": rel(PROMOTION_GATE), **gate_summary(PROMOTION_GATE)},
            "tracker_copies": [rel(TRACKER_GEOMETRY_GATE), rel(TRACKER_PROMOTION_GATE)],
        }
        payload["evidence_paths"] = evidence_paths
        payload["qa_decision"] = STATUS_DECISION
        write_json(path, payload)
        updates[rel(path)] = 1
    return updates


def update_csvs(evidence_paths: list[str]) -> dict[str, int]:
    note = (
        "Body reference matrix Ref_Image_1 plus Ref_Image_2 post-evaluation gates 20260708T153118-0500: geometry and promotion hard gates "
        "passed with 332 checked rows, zero pass-like rows, and zero failures. Expanded reference context is available but row remains Required_Not_Complete; no masks promoted."
    )
    updates: dict[str, int] = {}
    for path, key, target in CSV_TARGETS:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
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
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(row.get("Coverage_Audit_Status", ""), COVERAGE_TOKENS)
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        updates[rel(path)] = changed
    return updates


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(evidence_paths: list[str]) -> dict[str, bool]:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Attached post-`{TRACKER_ID}` / `{ITEM_ID}` hard-gate evidence.

Body reference matrix remains `Required_Not_Complete`: Ref_Image_1 and Ref_Image_2 supply expanded body reference context, but they do not prove cross-subject/body-size/skin-tone generalization, occlusion/multi-person coverage, parser-backed clothing/body/contact ownership, canonical polygons, generated output, target-runtime proof, visual QA, or mask promotion evidence. No masks were promoted.

Post-body-reference-matrix gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}"""
    updates = {
        "CURRENT_SESSION_STATE.md": prepend(
            HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
            f"## Session State Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Gates Attached - {ISO_TS}",
            body + f"\n\nNext local action: `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
        ),
        "CURRENT_PURSUING_GOAL.md": prepend(
            HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
            f"## Current Pursuing Goal Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Gates Attached - {ISO_TS}",
            body,
        ),
        "RESUME_HERE_NEXT_CODEX_SESSION.md": prepend(
            HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
            f"## Resume Update - 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Gates Attached - {ISO_TS}",
            body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
        ),
        "NEXT_ACTION.md": prepend(
            HYDRATION_DIR / "NEXT_ACTION.md",
            f"## Immediate Next Action - {ISO_TS} - Work TRK-W70-0177",
            body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
        ),
        "QA_EVIDENCE_INDEX.md": prepend(
            HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
            f"## Wave70 0176 Body Reference Matrix Ref_Image_1 Ref_Image_2 Gate Evidence - {ISO_TS}",
            body,
        ),
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0176 body reference matrix hard gates",
                "Attached post-body-reference-matrix Ref_Image_1 plus Ref_Image_2 geometry/promotion hard gates; both passed fail-closed with 332 checked rows, zero pass-like rows, and zero failures. No masks promoted.",
                "; ".join(evidence_paths),
                "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; JSON summary validation; tracker evidence copy; CSV row verification",
                "BODY_REFERENCE_MATRIX_REF_IMAGES_1_2_ROUTE_NOT_COMPLETE_GATES_PASS",
                rel(BODY_CANONICAL),
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} next.",
            ]
        )
    return updates


def main() -> None:
    for gate in [GEOMETRY_GATE, PROMOTION_GATE]:
        summary = gate_summary(gate)
        if summary != {"checked": 332, "pass_like": 0, "failures": 0}:
            raise RuntimeError(f"Unexpected gate summary for {gate}: {summary}")
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEOMETRY_GATE, TRACKER_GEOMETRY_GATE)
    shutil.copy2(PROMOTION_GATE, TRACKER_PROMOTION_GATE)
    shutil.copy2(REF_IMAGE_2_STAMPED, TRACKER_REF_IMAGE_2_STAMPED)
    shutil.copy2(REF_IMAGE_2_CANONICAL, TRACKER_REF_IMAGE_2_CANONICAL)
    evidence_paths = [
        rel(BODY_STAMPED),
        rel(BODY_CANONICAL),
        rel(TRACKER_BODY_STAMPED),
        rel(TRACKER_BODY_CANONICAL),
        rel(REF_IMAGE_2_STAMPED),
        rel(REF_IMAGE_2_CANONICAL),
        rel(TRACKER_REF_IMAGE_2_STAMPED),
        rel(TRACKER_REF_IMAGE_2_CANONICAL),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        rel(TRACKER_GEOMETRY_GATE),
        rel(TRACKER_PROMOTION_GATE),
    ]
    print(
        json.dumps(
            {
                "payload_updates": update_payloads(evidence_paths),
                "csv_updates": update_csvs(evidence_paths),
                "hydration_updates": update_hydration(evidence_paths),
                "geometry_gate": gate_summary(GEOMETRY_GATE),
                "promotion_gate": gate_summary(PROMOTION_GATE),
                "next": f"{NEXT_TRACKER_ID} / {NEXT_ITEM_ID}",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
