from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

DEPENDENCY_PROBE = QA_DIR / "body_geometry_dependency_probe.json"
PREREQ_GAP = QA_DIR / "canonical_body_geometry_prerequisite_gap.json"
GEOMETRY_GATE = QA_DIR / "W70_MASK_GEOMETRY_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_REFRESH_20260708T184528-0500.json"
PROMOTION_GATE = QA_DIR / "W70_MASK_PROMOTION_HARD_GATE_POST_WHOLE_BODY_DEPENDENCY_PROBE_REFRESH_20260708T184528-0500.json"
EVIDENCE = QA_DIR / f"W70_DEPENDENCY_PROBE_REFRESH_ALIGNMENT_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "dependency_probe_refresh_alignment.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def gate_summary(path: Path) -> dict[str, int]:
    payload = read_json(path)
    checked = payload.get("checked_rows") or []
    failures = payload.get("failures") or []
    pass_like = [row for row in checked if row.get("pass_like_status")]
    return {"checked": len(checked), "pass_like": len(pass_like), "failures": len(failures)}


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def find_row(path: Path, row_id: str) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    key = "Tracker_ID" if row_id.startswith("TRK-") else "Item_ID"
    for row in rows:
        if row.get(key) == row_id:
            return row
    raise RuntimeError(f"Missing {row_id} in {path}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def copy_to_tracker(path: Path) -> str:
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = TRACKER_EVIDENCE_DIR / path.name
    shutil.copy2(path, target)
    return rel(target)


def main() -> None:
    probe = read_json(DEPENDENCY_PROBE)
    gap = read_json(PREREQ_GAP)
    geometry = gate_summary(GEOMETRY_GATE)
    promotion = gate_summary(PROMOTION_GATE)
    route_eval = probe.get("route_evaluation") or {}
    missing = route_eval.get("missing_required_routes") or []
    unvalidated = route_eval.get("available_but_unvalidated_routes") or []

    require(probe.get("qa_decision") == "blocked_body_geometry_dependency_missing", "Unexpected dependency probe decision")
    require(set(missing) == {"human_part_parsing_route", "person_instance_segmentation_route", "temporal_propagation_route", "contact_occlusion_ownership_route"}, f"Unexpected missing routes: {missing}")
    require(set(unvalidated) == {"pose_landmark_route", "hand_landmark_route", "promptable_segmentation_refinement_route"}, f"Unexpected unvalidated routes: {unvalidated}")
    require(gap.get("qa_decision") == "canonical_body_geometry_prerequisite_gap_recorded_ref_images_1_2_context_available_no_promotion", "Prerequisite gap evidence is not current")
    require(geometry == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected geometry gate: {geometry}")
    require(promotion == {"checked": 332, "pass_like": 0, "failures": 0}, f"Unexpected promotion gate: {promotion}")

    tracker_row = find_row(TRACKER_FILES[0], "TRK-W70-0162")
    item_row = find_row(ITEM_FILES[0], "ITEM-W70-0162")
    require(tracker_row.get("Status") == "Blocked_Body_Geometry_Dependency_Missing", "Tracker 0162 status was not updated")
    require(item_row.get("Status") == "Blocked_Body_Geometry_Dependency_Missing", "Item 0162 status was not updated")

    tracker_gate_paths = [copy_to_tracker(GEOMETRY_GATE), copy_to_tracker(PROMOTION_GATE)]

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_DEPENDENCY_PROBE_REFRESH_ALIGNMENT_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Align refreshed Wave70 whole-body dependency probe with current Ref_Image_1+2 prerequisite gap and post-probe hard gates.",
        "source_evidence": {
            "dependency_probe": {
                "path": rel(DEPENDENCY_PROBE),
                "evidence_id": probe.get("evidence_id"),
                "qa_decision": probe.get("qa_decision"),
            },
            "canonical_body_geometry_prerequisite_gap": {
                "path": rel(PREREQ_GAP),
                "evidence_id": gap.get("evidence_id"),
                "qa_decision": gap.get("qa_decision"),
            },
        },
        "route_state": {
            "required_stack_available": route_eval.get("required_stack_available"),
            "missing_required_routes": missing,
            "available_but_runtime_unvalidated_routes": unvalidated,
            "models_available": (probe.get("whole_body_geometry_authority") or {}).get("models_available"),
            "blocked_reason": (probe.get("whole_body_geometry_authority") or {}).get("blocked_reason"),
        },
        "tracker_item_state": {
            "tracker_0162_status": tracker_row.get("Status"),
            "tracker_0162_status_decision": tracker_row.get("Status_Decision"),
            "item_0162_status": item_row.get("Status"),
        },
        "gates": {
            "geometry": {"path": rel(GEOMETRY_GATE), **geometry},
            "promotion": {"path": rel(PROMOTION_GATE), **promotion},
            "tracker_copies": tracker_gate_paths,
        },
        "promotion_policy": {
            "masks_changed": [],
            "masks_promoted": [],
            "completion_allowed": False,
            "wave71_activation_allowed": False,
        },
        "qa_decision": "dependency_probe_refreshed_missing_routes_recorded_ref_images_1_2_prerequisite_gap_aligned_no_promotion",
        "next_step": "Resolve or register local human parsing, person-instance segmentation, temporal propagation, and contact ownership routes; then runtime-validate pose, hand, and promptable segmentation routes before deriving canonical polygons.",
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(DEPENDENCY_PROBE),
        rel(PREREQ_GAP),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
        *tracker_gate_paths,
    ]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Refreshed the Wave70 whole-body dependency/model probe and aligned it with the current Ref_Image_1+2 canonical body-geometry prerequisite gap.

Exact local route state: missing required routes are `human_part_parsing_route`, `person_instance_segmentation_route`, `temporal_propagation_route`, and `contact_occlusion_ownership_route`. Local `pose_landmark_route`, `hand_landmark_route`, and `promptable_segmentation_refinement_route` are present only as available-but-runtime-unvalidated routes, so they cannot yet provide canonical polygons or mask promotion authority.

`TRK-W70-0162` / `ITEM-W70-0162` remains `Blocked_Body_Geometry_Dependency_Missing`. Ref_Image_1+2 still provide 9 full/near-full references and 78 gold masks as calibration/reference context, but static overlays are not canonical body geometry authority.

Post-refresh Wave70 hard gates passed fail-closed: geometry and promotion each checked 332 rows with zero pass-like rows and zero failures. No masks were changed or promoted, and Wave71+ remains deferred.

Evidence:

{evidence_block}

Next exact local action: resolve or register local human parsing, person-instance segmentation, temporal propagation, and contact ownership routes; then runtime-validate pose, hand, and promptable segmentation routes before deriving canonical polygons."""

    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - Whole Body Dependency Probe Refreshed",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Whole Body Dependency Probe Refreshed",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Whole Body Dependency Probe Refreshed",
            "NEXT_ACTION.md": "Immediate Next Action - Resolve Whole Body Geometry Dependency Routes",
            "QA_EVIDENCE_INDEX.md": "Wave70 Whole Body Dependency Probe Refresh Evidence",
            "BLOCKERS.md": "Wave70 Whole Body Dependency Route Blocker",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 whole-body dependency probe refreshed",
                "Recorded exact missing model-backed geometry routes, post-probe hard gates, and 0162 blocker alignment.",
                "; ".join(evidence_paths),
                "probe_wave70_whole_body_geometry_dependencies.py; Test-Wave70MaskGeometryGate.ps1; Test-Wave70MaskPromotionGate.ps1",
                "WHOLE_BODY_DEPENDENCY_PROBE_REFRESH_NO_PROMOTION",
                rel(EVIDENCE),
                "Resolve/register missing local geometry routes; runtime-validate unvalidated routes before canonical polygon work.",
            ]
        )
    print(json.dumps({"evidence": rel(EVIDENCE), "hydration_updates": updates, "qa_decision": payload["qa_decision"]}, indent=2))


if __name__ == "__main__":
    main()
