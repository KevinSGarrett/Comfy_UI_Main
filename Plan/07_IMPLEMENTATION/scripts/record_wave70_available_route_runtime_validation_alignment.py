from __future__ import annotations

import csv
import json
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

DEPENDENCY_ALIGNMENT = QA_DIR / "dependency_probe_refresh_alignment.json"
POSE_AUTHORITY = QA_DIR / "pose_landmark_authority.json"
HAND_AUTHORITY = QA_DIR / "hand_finger_landmark_authority.json"
SEGMENTATION_REFINEMENT = QA_DIR / "segmentation_refinement_authority.json"

EVIDENCE = QA_DIR / f"W70_AVAILABLE_ROUTE_RUNTIME_VALIDATION_ALIGNMENT_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "available_route_runtime_validation_alignment.json"

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


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def update_row_evidence(evidence_paths: list[str], note: str) -> dict[str, int]:
    updates: dict[str, int] = {}
    pairs = [(path, "TRK-W70-0162") for path in TRACKER_FILES] + [(path, "ITEM-W70-0162") for path in ITEM_FILES]
    for csv_path, target_id in pairs:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        key = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        changed = 0
        for row in rows:
            if row.get(key) != target_id:
                continue
            changed += 1
            row["Status"] = "Blocked_Body_Geometry_Dependency_Missing"
            for field in ("Evidence_Path", "Acceptance_Evidence"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Status_Decision" in row and target_id.startswith("TRK-"):
                row["Status_Decision"] = "available_routes_runtime_executed_partial_missing_required_whole_body_routes"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["available_routes_runtime_executed_partial_missing_required_whole_body_routes"],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(csv_path)] = changed
    return updates


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def main() -> None:
    dep = read_json(DEPENDENCY_ALIGNMENT)
    pose = read_json(POSE_AUTHORITY)
    hand = read_json(HAND_AUTHORITY)
    seg = read_json(SEGMENTATION_REFINEMENT)

    dep_routes = dep.get("route_state") or {}
    missing = dep_routes.get("missing_required_routes") or []
    pose_auth = pose.get("pose_landmark_authority") or {}
    hand_auth = hand.get("hand_finger_landmark_authority") or {}
    seg_auth = seg.get("segmentation_refinement_authority") or {}

    require(dep.get("qa_decision") == "dependency_probe_refreshed_missing_routes_recorded_ref_images_1_2_prerequisite_gap_aligned_no_promotion", "Dependency alignment evidence is not current")
    require(set(missing) == {"human_part_parsing_route", "person_instance_segmentation_route", "temporal_propagation_route", "contact_occlusion_ownership_route"}, f"Unexpected missing routes: {missing}")
    require(pose_auth.get("result") == "source_derived_pose_landmarks_partial", "Pose route is not runtime-executed partial")
    require(pose_auth.get("pose_landmark_pass") is True, "Pose landmark runtime pass is not true")
    require(hand_auth.get("blocked_reason") == "local_hand_landmarker_executed_detected_zero_hands_on_active_source", "Hand route was not runtime-executed zero-hand blocker")
    require(hand_auth.get("detected_hand_count") == 0, "Unexpected detected hand count")
    require(seg_auth.get("result") == "sam2_refinement_executed_pending_consensus", "Promptable segmentation route is not runtime-executed pending consensus")
    require(seg_auth.get("sam_refinement_pass") is True, "SAM refinement pass is not true")

    route_validation = {
        "pose_landmark_route": {
            "runtime_executed": True,
            "route_level_result": pose_auth.get("result"),
            "source_scope": "active portrait only",
            "authority_limit": pose_auth.get("blocked_reason"),
            "evidence_path": rel(POSE_AUTHORITY),
        },
        "hand_landmark_route": {
            "runtime_executed": True,
            "route_level_result": hand_auth.get("result"),
            "detected_hand_count": hand_auth.get("detected_hand_count"),
            "authority_limit": hand_auth.get("blocked_reason"),
            "evidence_path": rel(HAND_AUTHORITY),
        },
        "promptable_segmentation_refinement_route": {
            "runtime_executed": True,
            "route_level_result": seg_auth.get("result"),
            "sam_refinement_pass": seg_auth.get("sam_refinement_pass"),
            "authority_limit": seg_auth.get("blocked_reason"),
            "evidence_path": rel(SEGMENTATION_REFINEMENT),
        },
    }
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_AVAILABLE_ROUTE_RUNTIME_VALIDATION_ALIGNMENT_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record runtime-executed status for locally available Wave70 whole-body routes without promoting masks.",
        "dependency_alignment": {
            "path": rel(DEPENDENCY_ALIGNMENT),
            "evidence_id": dep.get("evidence_id"),
            "qa_decision": dep.get("qa_decision"),
        },
        "available_route_runtime_validation": route_validation,
        "still_missing_required_routes": missing,
        "full_stack_state": {
            "required_stack_available": False,
            "whole_body_geometry_authority_pass": False,
            "canonical_polygon_export_allowed": False,
            "body_hand_contact_support_soft_body_promotion_allowed": False,
            "wave71_activation_allowed": False,
        },
        "qa_decision": "available_routes_runtime_executed_partial_but_whole_body_stack_still_blocked_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_available_route_validation_only",
        "next_step": "Resolve/register human parsing, person-instance segmentation, temporal propagation, and contact ownership routes, then rerun dependency probe and hard gates before canonical polygon work.",
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(DEPENDENCY_ALIGNMENT),
        rel(POSE_AUTHORITY),
        rel(HAND_AUTHORITY),
        rel(SEGMENTATION_REFINEMENT),
    ]
    note = (
        "Available route runtime validation aligned: pose executed partial, hand executed with zero hands on active source, "
        "SAM2 promptable refinement executed pending consensus; whole-body stack remains blocked by missing human parsing, "
        "person-instance segmentation, temporal propagation, and contact ownership."
    )
    payload["tracker_item_updates"] = update_row_evidence(evidence_paths, note)
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Recorded available-route runtime validation alignment for Wave70 whole-body geometry.

Local available routes are runtime-executed but not authority-complete: pose produced partial source-derived landmarks on the active portrait, hand landmarking executed but detected zero hands on the active source, and SAM2 promptable refinement executed for face refinement but remains pending consensus/canonical polygon evidence.

The whole-body stack is still blocked by missing required routes: `human_part_parsing_route`, `person_instance_segmentation_route`, `temporal_propagation_route`, and `contact_occlusion_ownership_route`. Therefore `TRK-W70-0162` / `ITEM-W70-0162` stays `Blocked_Body_Geometry_Dependency_Missing`; no body, hand, contact, support, soft-body, or temporal mask was changed or promoted.

Evidence:

{evidence_block}

Next exact local action: resolve/register human parsing, person-instance segmentation, temporal propagation, and contact ownership routes, then rerun dependency probe and hard gates before canonical polygon work."""

    updates = {
        name: prepend(HYDRATION_DIR / name, f"## {title} - {ISO_TS}", body)
        for name, title in {
            "CURRENT_SESSION_STATE.md": "Session State Update - Available Route Runtime Validation Alignment",
            "CURRENT_PURSUING_GOAL.md": "Current Pursuing Goal Update - Available Route Runtime Validation Alignment",
            "RESUME_HERE_NEXT_CODEX_SESSION.md": "Resume Update - Available Route Runtime Validation Alignment",
            "NEXT_ACTION.md": "Immediate Next Action - Resolve Missing Whole Body Routes",
            "QA_EVIDENCE_INDEX.md": "Wave70 Available Route Runtime Validation Evidence",
            "BLOCKERS.md": "Wave70 Available Route Runtime Validation Still Blocked",
        }.items()
    }
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                ISO_TS,
                "70",
                "Wave70 available route runtime validation alignment recorded",
                "Separated runtime-executed partial routes from still-missing required whole-body routes; no promotion.",
                "; ".join(evidence_paths),
                "pose_landmark_authority.json; hand_finger_landmark_authority.json; segmentation_refinement_authority.json",
                "AVAILABLE_ROUTE_RUNTIME_EXECUTED_PARTIAL_STILL_BLOCKED",
                rel(EVIDENCE),
                "Resolve/register missing required whole-body routes before canonical polygon work.",
            ]
        )
    print(json.dumps({"evidence": rel(EVIDENCE), "hydration_updates": updates, "qa_decision": payload["qa_decision"]}, indent=2))


if __name__ == "__main__":
    main()
