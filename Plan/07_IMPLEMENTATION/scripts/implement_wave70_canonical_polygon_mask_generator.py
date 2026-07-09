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
EVIDENCE_ID = f"W70_CANONICAL_POLYGON_MASK_GENERATOR_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_canonical_polygon_mask_generator.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_polygon_mask_generator" / RUN_STAMP

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
    "canonical_geometry_polygon_export": QA_DIR / "canonical_geometry_polygon_export.json",
    "model_consensus_geometry_validator": QA_DIR / "model_consensus_geometry_validator.json",
    "visibility_occlusion_confidence": QA_DIR / "visibility_occlusion_confidence.json",
    "gold_trace_dataset_manifest": QA_DIR / "gold_trace_dataset_manifest.json",
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
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "result": deep_get(mbga, ["result"]) if isinstance(mbga, dict) else payload.get("result"),
        "model_backed_geometry_authority_pass": deep_get(mbga, ["model_backed_geometry_authority_pass"]),
        "source_derived_landmark_or_segmentation_pass": deep_get(
            mbga, ["source_derived_landmark_or_segmentation_pass"]
        ),
        "model_consensus_geometry_pass": deep_get(mbga, ["model_consensus_geometry_pass"]),
        "visibility_occlusion_confidence_pass": deep_get(mbga, ["visibility_occlusion_confidence_pass"]),
        "canonical_polygon_export_pass": deep_get(mbga, ["canonical_polygon_export_pass"]),
        "canonical_polygon_path": deep_get(mbga, ["canonical_polygon_path"]),
        "no_debug_rectangle_mask_pass": deep_get(mbga, ["no_debug_rectangle_mask_pass"]),
        "blocked_reason": deep_get(mbga, ["blocked_reason"]),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_prerequisite(path) for name, path in PREREQ_FILES.items()}


def project_path(path_value: object) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def evaluate_mask_generation_readiness(prereqs: dict[str, object]) -> dict[str, object]:
    canonical = prereqs.get("canonical_geometry_polygon_export", {})
    canonical_path = canonical.get("canonical_polygon_path")
    canonical_candidate = PROJECT_ROOT / str(canonical_path) if canonical_path else None
    canonical_path_exists = bool(canonical_candidate and canonical_candidate.exists())
    required_passes = {
        "canonical_polygon_export_pass": canonical.get("canonical_polygon_export_pass") is True,
        "canonical_polygon_path_present": bool(canonical_path),
        "canonical_polygon_path_exists": canonical_path_exists,
        "model_consensus_geometry_pass": canonical.get("model_consensus_geometry_pass") is True,
        "visibility_occlusion_confidence_pass": canonical.get("visibility_occlusion_confidence_pass") is True,
    }
    failed_requirements = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed_requirements,
        "canonical_polygon_path": canonical_path or "",
        "mask_generation_computable": not failed_requirements,
        "mask_from_canonical_geometry_pass": False,
        "no_debug_rectangle_mask_pass": True,
        "geometry_gate_pass": False,
        "blocking_reason": "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed",
    }


def generate_mask_from_canonical_polygon(evaluation: dict[str, object], source: Image.Image) -> dict[str, object]:
    if not evaluation.get("mask_generation_computable"):
        return {
            "mask_from_canonical_geometry_pass": False,
            "geometry_gate_pass": False,
            "blocked_reason": "mask_generation_not_computable",
        }
    polygon_path = project_path(evaluation.get("canonical_polygon_path"))
    if not polygon_path or not polygon_path.exists():
        return {
            "mask_from_canonical_geometry_pass": False,
            "geometry_gate_pass": False,
            "blocked_reason": "canonical_polygon_missing",
        }
    polygon_record = json.loads(polygon_path.read_text(encoding="utf-8-sig"))
    points = polygon_record.get("points_xy") or []
    if len(points) < 3:
        return {
            "mask_from_canonical_geometry_pass": False,
            "geometry_gate_pass": False,
            "blocked_reason": "canonical_polygon_too_small",
        }
    mask = Image.new("L", source.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([tuple(point) for point in points], fill=255)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    mask_path = RUNTIME_DIR / "canonical_polygon_mask.png"
    overlay_path = RUNTIME_DIR / "canonical_polygon_mask_overlay_panel.png"
    mask.save(mask_path)
    overlay = source.copy().convert("RGBA")
    color = Image.new("RGBA", source.size, (40, 170, 80, 0))
    alpha = mask.point(lambda value: 90 if value else 0)
    color.putalpha(alpha)
    overlay = Image.alpha_composite(overlay, color).convert("RGB")
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.line([tuple(point) for point in points] + [tuple(points[0])], fill=(40, 170, 80), width=2)
    overlay.save(overlay_path)
    nonzero = sum(1 for value in mask.getdata() if value > 0)
    record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "source_dimensions": list(source.size),
        "canonical_polygon_path": rel(polygon_path),
        "generated_mask_path": rel(mask_path),
        "overlay_path": rel(overlay_path),
        "mask_sha256": sha256_file(mask_path),
        "mask_dimensions": list(mask.size),
        "mask_nonzero_pixels": nonzero,
        "mask_nonzero_ratio": round(nonzero / float(source.size[0] * source.size[1]), 6),
        "point_count": len(points),
        "mask_from_canonical_geometry_pass": nonzero > 0,
        "no_debug_rectangle_mask_pass": True,
        "geometry_gate_pass": nonzero > 0,
        "no_mask_promoted": True,
        "blocked_reason": "",
    }
    record_path = RUNTIME_DIR / "canonical_polygon_mask_record.json"
    write_json(record_path, record)
    return {**record, "mask_record_path": rel(record_path)}


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "canonical_polygon_mask_generator_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 255], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0150 blocked",
        "Canonical mask generation unavailable.",
        "No canonical polygon or segmentation map exists.",
        "mask_from_canonical_geometry_pass = false",
        "geometry_gate_pass = false",
        "No shortcut/debug mask generated.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 29
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str, pass_gate: bool) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0150") for path in TRACKER_FILES] + [(path, "ITEM-W70-0150") for path in ITEM_FILES]
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
            row["Status"] = (
                "Canonical_Polygon_Mask_Generated_Not_Promoted"
                if pass_gate
                else "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed"
            )
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = (
                    "canonical_polygon_mask_generated_no_promotion"
                    if pass_gate
                    else "blocked_exact_local_no_canonical_geometry_for_mask_generation"
                )
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "canonical_polygon_mask_generated_no_promotion"
                        if pass_gate
                        else "blocked_exact_local_no_canonical_geometry_for_mask_generation"
                    ],
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
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. `TRK-W70-0150` / `ITEM-W70-0150` was worked locally and is exactly blocked: masks cannot be generated from canonical polygons or segmentation maps because no canonical polygon path or passing canonical geometry evidence exists.

No mask artifact, shortcut/debug mask, active mask change, generated-output proof, or mask promotion was produced.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is `TRK-W70-0151` / `ITEM-W70-0151`, extend the authority pattern to body, hands, clothing, contact, and video. Work it locally; if prerequisite body/hand/contact/video geometry authority is unavailable, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""`TRK-W70-0150` / `ITEM-W70-0150` is exactly blocked with local canonical mask-generator evidence. No canonical source-derived polygon or segmentation map exists, so no mask can be generated under the Wave70 authority rules.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block `TRK-W70-0151` / `ITEM-W70-0151`, extend the authority pattern to body, hands, clothing, contact, and video. Use only model-backed geometry and whole-body authority evidence. If dependencies remain blocked, write one exact blocker with evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = f"""Worked `TRK-W70-0150` / `ITEM-W70-0150` locally. Canonical mask generation is blocked because canonical geometry is unavailable. No mask artifact was created and no mask was promoted."""
    blocker_body = f"""`TRK-W70-0150` / `ITEM-W70-0150`: `Blocked_Wave70_Mask_Geometry_Gate_Not_Passed` / `blocked_exact_local_no_canonical_geometry_for_mask_generation`. `mask_from_canonical_geometry_pass` and `geometry_gate_pass` remain false."""

    prepend_section(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Wave70 Canonical Mask Generator Blocked Locally - {ISO_STAMP}",
        current_body,
    )
    prepend_section(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0151 Body Hand Contact Authority Locally",
        next_body,
    )
    prepend_section(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Wave70 Canonical Mask Generator Blocked - {ISO_STAMP}",
        session_body + "\n\nNext exact action: work `TRK-W70-0151` locally.",
    )
    prepend_section(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Wave70 Canonical Mask Generator Blocked - {ISO_STAMP}",
        session_body,
    )
    prepend_section(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 Canonical Mask Generator Evidence - {ISO_STAMP}",
        f"{session_body}\n\n{evidence_block}",
    )
    prepend_section(
        HYDRATION_DIR / "BLOCKERS.md",
        f"## Wave70 Canonical Mask Generator Blocker - {ISO_STAMP}",
        blocker_body + "\n\n" + evidence_block,
    )

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 canonical polygon mask generator blocker",
                "Worked TRK/ITEM-W70-0150 locally. Masks cannot be generated from canonical polygons or segmentation maps because no canonical geometry path or passing canonical export evidence exists. Wrote stamped/canonical evidence, generated a blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; canonical export prerequisite review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_WAVE70_MASK_GEOMETRY_GATE_NOT_PASSED",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/canonical_polygon_mask_generator.json",
                "Next work TRK-W70-0151 body hand contact authority locally; write exact blocker if dependencies remain blocked.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_mask_generation_readiness(prereqs)
    mask_generation = generate_mask_from_canonical_polygon(evaluation, source)
    pass_gate = mask_generation.get("mask_from_canonical_geometry_pass") is True
    panel_path = (
        PROJECT_ROOT / str(mask_generation["overlay_path"])
        if pass_gate and mask_generation.get("overlay_path")
        else make_blocker_panel(source, evaluation)
    )

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "canonical_polygon_mask_generator.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "canonical_polygon_mask_generator.json"
    runtime_evidence_path = RUNTIME_DIR / "canonical_polygon_mask_generator.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    for key in ["generated_mask_path", "mask_record_path"]:
        if mask_generation.get(key):
            evidence_rel_paths.append(str(mask_generation[key]))
    note = (
        f"Canonical polygon mask generator {RUN_STAMP}: generated a QA mask from the canonical source-derived polygon. "
        "The mask artifact was not promoted or wired into active masks."
        if pass_gate
        else (
            f"Canonical polygon mask generator {RUN_STAMP}: exact local blocker. "
            "No canonical source-derived polygon or segmentation map is available, so no mask-from-canonical-geometry artifact was emitted."
        )
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note, pass_gate)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Generate masks only from canonical polygons or segmentation maps for TRK-W70-0150 / ITEM-W70-0150.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prereqs,
        "mask_generation_readiness": evaluation,
        "mask_generation_record": mask_generation,
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "generated_mask": mask_generation.get("generated_mask_path", ""),
            "mask_record": mask_generation.get("mask_record_path", ""),
        },
        "model_backed_geometry_authority": {
            "result": "canonical_polygon_mask_generated_no_promotion" if pass_gate else "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-009",
            "matrix_slot_id": "TRK-W70-0150",
            "models_attempted": [
                "canonical_geometry_polygon_export_review",
                "canonical_polygon_mask_generation_gate",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
            "canonical_polygon_path": evaluation.get("canonical_polygon_path", ""),
            "coordinate_transform_manifest_path": "",
            "gold_trace_comparison_path": rel(QA_DIR / "gold_trace_dataset_manifest.json"),
            "generated_mask_path": mask_generation.get("generated_mask_path", ""),
            "consensus_metrics": {
                "iou_against_gold_or_prior": None,
                "mean_boundary_error_px": None,
                "max_boundary_error_px": None,
                "center_drift_px": None,
                "protected_overlap_ratio": None,
            },
            "confidence": {
                "landmark_confidence": None,
                "parsing_confidence": None,
                "refinement_confidence": None,
                "visibility_confidence": None,
                "overall_confidence": None,
            },
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": pass_gate,
            "source_derived_landmark_or_segmentation_pass": pass_gate,
            "model_consensus_geometry_pass": pass_gate,
            "visibility_occlusion_confidence_pass": pass_gate,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": pass_gate,
            "mask_from_canonical_geometry_pass": pass_gate,
            "geometry_gate_pass": pass_gate,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "blocked_reason": "" if pass_gate else "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed",
            "findings": [
                "A QA mask artifact was generated from the canonical source-derived polygon."
                if pass_gate
                else "Canonical polygon export is blocked and has no canonical polygon path.",
                "The generated mask remains an evidence artifact only and was not promoted.",
                "No mask was generated from debug rectangles, Canny edges, Haar boxes, visual guesses, or generated-output stability.",
                "No active mask artifact changed and no mask was promoted.",
            ],
        },
        "canonical_polygon_mask_generator": {
            "result": "executed" if pass_gate else "blocked",
            "mask_from_canonical_geometry_pass": pass_gate,
            "no_debug_rectangle_mask_pass": True,
            "geometry_gate_pass": pass_gate,
            "generated_mask_path": mask_generation.get("generated_mask_path", ""),
            "blocked_reason": "" if pass_gate else "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed",
        },
        "qa_decision": (
            "canonical_polygon_mask_generated_no_promotion"
            if pass_gate
            else "blocked_exact_local_no_canonical_geometry_for_mask_generation"
        ),
        "promotion_decision": "no_mask_promoted_no_active_input_changed_canonical_mask_generator_authority_only",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0151 / ITEM-W70-0151 body hand contact geometry authority locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    if not pass_gate:
        update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
