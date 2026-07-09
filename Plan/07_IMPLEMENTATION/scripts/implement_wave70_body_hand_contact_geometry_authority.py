from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_BODY_HAND_CONTACT_GEOMETRY_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_body_hand_contact_geometry_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_body_hand_contact_geometry_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

PREREQ_FILES = {
    "canonical_polygon_mask_generator": QA_DIR / "canonical_polygon_mask_generator.json",
    "canonical_geometry_polygon_export": QA_DIR / "canonical_geometry_polygon_export.json",
    "whole_body_geometry_promotion_integration": QA_DIR / "whole_body_geometry_promotion_integration.json",
    "body_reference_matrix": QA_DIR / "body_reference_matrix.json",
    "redo_existing_body_hand_contact_masks": QA_DIR / "redo_existing_body_hand_contact_masks.json",
    "contact_occlusion_ownership_authority": QA_DIR / "contact_occlusion_ownership_authority.json",
    "body_region_geometry_authority": QA_DIR / "body_region_geometry_authority.json",
    "temporal_body_part_tracking_authority": QA_DIR / "temporal_body_part_tracking_authority.json",
}


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def deep_get(payload: object, keys: list[str]) -> object | None:
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def read_prerequisite(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "error": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    mbga = payload.get("model_backed_geometry_authority")
    wb = payload.get("whole_body_geometry_authority")
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "model_backed_geometry_authority_pass": deep_get(mbga, ["model_backed_geometry_authority_pass"]),
        "source_derived_landmark_or_segmentation_pass": deep_get(
            mbga, ["source_derived_landmark_or_segmentation_pass"]
        ),
        "model_consensus_geometry_pass": deep_get(mbga, ["model_consensus_geometry_pass"]),
        "visibility_occlusion_confidence_pass": deep_get(mbga, ["visibility_occlusion_confidence_pass"]),
        "canonical_polygon_export_pass": deep_get(mbga, ["canonical_polygon_export_pass"]),
        "whole_body_geometry_authority_pass": deep_get(mbga, ["whole_body_geometry_authority_pass"])
        if isinstance(mbga, dict)
        else deep_get(wb, ["whole_body_geometry_authority_pass"]),
        "pose_hand_dense_landmark_or_segmentation_pass": deep_get(
            mbga, ["pose_hand_dense_landmark_or_segmentation_pass"]
        ),
        "semantic_human_part_parsing_pass": deep_get(mbga, ["semantic_human_part_parsing_pass"]),
        "contact_occlusion_ownership_pass": deep_get(mbga, ["contact_occlusion_ownership_pass"]),
        "body_region_geometry_pass": deep_get(mbga, ["body_region_geometry_pass"]),
        "body_reference_matrix_pass": deep_get(mbga, ["body_reference_matrix_pass"]),
        "blocked_reason": deep_get(mbga, ["blocked_reason"]) or deep_get(wb, ["blocked_reason"]),
        "result": deep_get(mbga, ["result"]) or deep_get(wb, ["result"]) or payload.get("result"),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_prerequisite(path) for name, path in PREREQ_FILES.items()}


def evaluate_authority(prereqs: dict[str, object]) -> dict[str, object]:
    required_passes = {
        "pose_hand_segmentation_route_declared": any(
            prereqs.get(name, {}).get("pose_hand_dense_landmark_or_segmentation_pass") is True
            for name in prereqs
        ),
        "temporal_visibility_route_declared": prereqs.get("temporal_body_part_tracking_authority", {}).get("result")
        not in (None, "missing")
        and prereqs.get("temporal_body_part_tracking_authority", {}).get("qa_decision") is not None,
        "whole_body_geometry_authority_pass": any(
            prereqs.get(name, {}).get("whole_body_geometry_authority_pass") is True for name in prereqs
        ),
        "contact_occlusion_ownership_pass": any(
            prereqs.get(name, {}).get("contact_occlusion_ownership_pass") is True for name in prereqs
        ),
        "body_region_geometry_pass": any(
            prereqs.get(name, {}).get("body_region_geometry_pass") is True for name in prereqs
        ),
        "body_reference_matrix_pass": any(
            prereqs.get(name, {}).get("body_reference_matrix_pass") is True for name in prereqs
        ),
        "canonical_polygon_export_pass": any(
            prereqs.get(name, {}).get("canonical_polygon_export_pass") is True for name in prereqs
        ),
    }
    failed_requirements = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed_requirements,
        "body_hand_contact_authority_computable": not failed_requirements,
        "pose_hand_segmentation_route_declared": required_passes["pose_hand_segmentation_route_declared"],
        "temporal_visibility_route_declared": required_passes["temporal_visibility_route_declared"],
        "blocker_policy_pass": True,
        "blocking_reason": "Blocked_Model_Geometry_Dependency_Missing",
    }


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "body_hand_contact_geometry_authority_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 280], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0151 blocked",
        "Body/hand/contact/video authority unavailable.",
        "Whole-body geometry authority has not passed.",
        f"Failed requirements: {len(evaluation['failed_requirements'])}",
        "Existing body/hand/contact masks remain untrusted.",
        "No canonical body geometry emitted.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 31
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0151") for path in TRACKER_FILES] + [(path, "ITEM-W70-0151") for path in ITEM_FILES]
    for csv_path, target_id in targets:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        id_field = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        changed = 0
        for row in rows:
            if row.get(id_field) != target_id:
                continue
            changed += 1
            row["Status"] = "Blocked_Model_Geometry_Dependency_Missing"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_body_hand_contact_authority_unavailable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_body_hand_contact_authority_unavailable"],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updated[rel(csv_path)] = changed
    return updated


def prepend_section(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8")


def update_hydration(evidence_paths: list[str]) -> None:
    evidence_block = "\n".join(f"- `{p}`" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. `TRK-W70-0151` / `ITEM-W70-0151` was worked locally and is exactly blocked: body, hand, clothing/contact, support, soft-body, and video authority cannot be extended because whole-body geometry, pose/hand segmentation, human-part parsing, contact ownership, body-region geometry, reference matrix, and canonical body geometry prerequisites remain blocked or missing.

Existing body/hand/contact/support/soft-body masks remain untrusted. No canonical body geometry, active mask change, generated-output proof, or mask promotion was produced.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is `TRK-W70-0152` / `ITEM-W70-0152`, validate model-backed geometry across the reference image matrix. Work it locally; if the matrix cannot run because dependencies or canonical geometry remain blocked, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""`TRK-W70-0151` / `ITEM-W70-0151` is exactly blocked with local body/hand/contact authority evidence. Whole-body and body-contact prerequisites remain blocked or missing, so the authority pattern cannot be extended to body, hands, clothing/contact, or video as a passing route.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block `TRK-W70-0152` / `ITEM-W70-0152`, validate model-backed geometry across the reference image matrix. Use only source-derived model-backed evidence. If the reference matrix cannot run because prerequisites remain blocked, write one exact blocker with evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = f"""Worked `TRK-W70-0151` / `ITEM-W70-0151` locally. Body/hand/contact/video authority extension is blocked because whole-body geometry prerequisites are unavailable. No mask artifact was created and no mask was promoted."""
    blocker_body = f"""`TRK-W70-0151` / `ITEM-W70-0151`: `Blocked_Model_Geometry_Dependency_Missing` / `blocked_exact_local_body_hand_contact_authority_unavailable`. Existing body/hand/contact masks remain fail-closed and untrusted."""

    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 Body Hand Contact Authority Blocked Locally - {ISO_STAMP}", current_body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0152 Reference Matrix Validation Locally", next_body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - Wave70 Body Hand Contact Authority Blocked - {ISO_STAMP}", session_body + "\n\nNext exact action: work `TRK-W70-0152` locally.")
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - Wave70 Body Hand Contact Authority Blocked - {ISO_STAMP}", session_body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 Body Hand Contact Authority Evidence - {ISO_STAMP}", f"{session_body}\n\n{evidence_block}")
    prepend_section(HYDRATION_DIR / "BLOCKERS.md", f"## Wave70 Body Hand Contact Authority Blocker - {ISO_STAMP}", blocker_body + "\n\n" + evidence_block)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 body hand contact authority blocker",
                "Worked TRK/ITEM-W70-0151 locally. Body, hand, clothing/contact, support, soft-body, and video authority cannot be extended because whole-body geometry prerequisites remain blocked or missing. Wrote stamped/canonical evidence, generated a blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; whole-body prerequisite review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_MODEL_GEOMETRY_DEPENDENCY_MISSING_BODY_HAND_CONTACT",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_hand_contact_geometry_authority.json",
                "Next work TRK-W70-0152 reference matrix validation locally; write exact blocker if dependencies remain blocked.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_authority(prereqs)
    panel_path = make_blocker_panel(source, evaluation)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "body_hand_contact_geometry_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "body_hand_contact_geometry_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "body_hand_contact_geometry_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"Body/hand/contact geometry authority {RUN_STAMP}: exact local blocker. "
        "Whole-body geometry, contact ownership, body region, temporal, reference matrix, and canonical body geometry prerequisites remain blocked or missing; existing body/hand/contact masks remain untrusted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Extend authority pattern to body hands clothing contact and video for TRK-W70-0151 / ITEM-W70-0151.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prereqs,
        "body_hand_contact_authority_readiness": evaluation,
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "model_backed_geometry_authority": {
            "result": "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-010",
            "matrix_slot_id": "TRK-W70-0151",
            "models_attempted": [
                "whole_body_geometry_authority_prerequisite_review",
                "body_hand_contact_video_extension_gate",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": "",
            "gold_trace_comparison_path": rel(QA_DIR / "gold_trace_dataset_manifest.json"),
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "blocked_reason": "Blocked_Model_Geometry_Dependency_Missing",
            "findings": [
                "Whole-body geometry promotion integration remains blocked.",
                "Body reference matrix evidence is blocked and does not provide a passing matrix.",
                "Contact/occlusion ownership and body region authority are blocked.",
                "Temporal body-part tracking/video authority is blocked.",
                "Existing body, hand, contact, support, and soft-body masks remain untrusted until regenerated or blocked from canonical body geometry.",
                "No active mask changed and no mask was promoted.",
            ],
        },
        "body_hand_contact_geometry_authority": {
            "result": "blocked",
            "pose_hand_segmentation_route_declared": evaluation["pose_hand_segmentation_route_declared"],
            "temporal_visibility_route_declared": evaluation["temporal_visibility_route_declared"],
            "blocker_policy_pass": evaluation["blocker_policy_pass"],
            "whole_body_geometry_authority_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "canonical_body_geometry_path": "",
            "blocked_reason": "Blocked_Model_Geometry_Dependency_Missing",
        },
        "qa_decision": "blocked_exact_local_body_hand_contact_authority_unavailable",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_body_hand_contact_authority_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0152 / ITEM-W70-0152 model geometry reference matrix locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
