from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
ISO_TS = "2026-07-08T15:18:23-05:00"
STAMP = "20260708T151823-0500"
TRACKER_ID = "TRK-W70-0175"
ITEM_ID = "ITEM-W70-0175"
NEXT_TRACKER_ID = "TRK-W70-0176"
NEXT_ITEM_ID = "ITEM-W70-0176"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

TEMPORAL_STAMPED = QA_DIR / f"W70_TEMPORAL_BODY_PART_TRACKING_AUTHORITY_{STAMP}.json"
TEMPORAL_CANONICAL = QA_DIR / "temporal_body_part_tracking_authority.json"
TRACKER_TEMPORAL_STAMPED = TRACKER_EVIDENCE_DIR / TEMPORAL_STAMPED.name
TRACKER_TEMPORAL_CANONICAL = TRACKER_EVIDENCE_DIR / TEMPORAL_CANONICAL.name
GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_TEMPORAL_REF_IMAGE_1_{STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_TEMPORAL_REF_IMAGE_1_{STAMP}.json"
TRACKER_GEOMETRY_GATE = TRACKER_EVIDENCE_DIR / GEOMETRY_GATE.name
TRACKER_PROMOTION_GATE = TRACKER_EVIDENCE_DIR / PROMOTION_GATE.name

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
]

STATUS_DECISION = "ref_image_1_temporal_reference_context_available_route_not_complete_global_gates_pass"
COVERAGE_TOKENS = [
    "ref_image_1_temporal_static_reference_context_available",
    "temporal_body_part_tracking_route_not_complete_no_promotion",
    "post_temporal_ref_image_1_geometry_gate_pass",
    "post_temporal_ref_image_1_promotion_gate_pass",
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
    for path in [TEMPORAL_STAMPED, TEMPORAL_CANONICAL, TRACKER_TEMPORAL_STAMPED, TRACKER_TEMPORAL_CANONICAL]:
        payload = read_json(path)
        artifacts = payload.setdefault("artifacts", {})
        artifacts["post_temporal_geometry_gate"] = rel(GEOMETRY_GATE)
        artifacts["post_temporal_promotion_gate"] = rel(PROMOTION_GATE)
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
        "Temporal Ref_Image_1 post-evaluation gates 20260708T151823-0500: geometry and promotion hard gates passed "
        "with 332 checked rows, zero pass-like rows, and zero failures. Static references are available but temporal route remains Required_Not_Complete; no masks promoted."
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

Temporal body-part tracking remains `Required_Not_Complete`: Ref_Image_1 supplies static body-pose/gold-mask context, but it is not an ordered video or frame-grid sequence. Per-frame body polygons, mask drift metrics, frame-grid visual QA, generated output, target-runtime proof, and promotion evidence are still missing. No masks were promoted.

Post-temporal gates: geometry and promotion hard gates both passed with 332 checked rows, zero pass-like rows, and zero failures.

Evidence:

{evidence_block}"""
    updates = {
        "CURRENT_SESSION_STATE.md": prepend(
            HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
            f"## Session State Update - 0175 Temporal Gates Attached - {ISO_TS}",
            body + f"\n\nNext local action: `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body reference matrix.",
        ),
        "CURRENT_PURSUING_GOAL.md": prepend(
            HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
            f"## Current Pursuing Goal Update - 0175 Temporal Gates Attached - {ISO_TS}",
            body,
        ),
        "RESUME_HERE_NEXT_CODEX_SESSION.md": prepend(
            HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
            f"## Resume Update - 0175 Temporal Gates Attached - {ISO_TS}",
            body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body reference matrix.",
        ),
        "NEXT_ACTION.md": prepend(
            HYDRATION_DIR / "NEXT_ACTION.md",
            f"## Immediate Next Action - {ISO_TS} - Work TRK-W70-0176 Body Reference Matrix",
            body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` body reference matrix.",
        ),
        "QA_EVIDENCE_INDEX.md": prepend(
            HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
            f"## Wave70 0175 Temporal Gate Evidence - {ISO_TS}",
            body,
        ),
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 0175 temporal hard gates",
                "Attached post-temporal geometry/promotion hard gates; both passed fail-closed with 332 checked rows, zero pass-like rows, and zero failures. No masks promoted.",
                "; ".join(evidence_paths),
                "Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1; JSON summary validation; tracker evidence copy; CSV row verification",
                "TEMPORAL_REF_IMAGE_1_ROUTE_NOT_COMPLETE_GATES_PASS",
                rel(TEMPORAL_CANONICAL),
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} body reference matrix next.",
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
    evidence_paths = [
        rel(TEMPORAL_STAMPED),
        rel(TEMPORAL_CANONICAL),
        rel(TRACKER_TEMPORAL_STAMPED),
        rel(TRACKER_TEMPORAL_CANONICAL),
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
