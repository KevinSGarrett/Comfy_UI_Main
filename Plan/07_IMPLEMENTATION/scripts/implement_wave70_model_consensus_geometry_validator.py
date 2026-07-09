from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_MODEL_CONSENSUS_GEOMETRY_VALIDATOR_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_model_consensus_geometry_validator.py"

TRACKER_ID = "TRK-W70-0173"
ITEM_ID = "ITEM-W70-0173"
ACTUAL_CONSENSUS_TRACKER_ID = "TRK-W70-0148"
ACTUAL_CONSENSUS_ITEM_ID = "ITEM-W70-0148"
NEXT_TRACKER_ID = "TRK-W70-0174"
NEXT_ITEM_ID = "ITEM-W70-0174"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_model_consensus_geometry_validator" / RUN_STAMP

MAIN_REFERENCE = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
FULL_REFERENCE_MANIFEST = QA_DIR / "ref_image_1_full_body_references.json"
GOLD_MASK_MANIFEST = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
BODY_REFERENCE_MATRIX = QA_DIR / "body_reference_matrix.json"

CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ITEM_ID),
]

ACTUAL_CONSENSUS_CSV_TARGETS = [
    (PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv", "Tracker_ID", ACTUAL_CONSENSUS_TRACKER_ID),
    (PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv", "Tracker_ID", ACTUAL_CONSENSUS_TRACKER_ID),
    (PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv", "Item_ID", ACTUAL_CONSENSUS_ITEM_ID),
    (PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv", "Item_ID", ACTUAL_CONSENSUS_ITEM_ID),
]

REFERENCE_ROUTE_EVIDENCE = {
    "torso_abdomen_umbilicus": QA_DIR / "torso_abdomen_umbilicus_authority.json",
    "limb_joint_region": QA_DIR / "limb_joint_region_authority.json",
    "feet_toes": QA_DIR / "feet_toes_authority.json",
    "hair_body_skin_marks": QA_DIR / "hair_body_skin_marks_authority.json",
    "contact_occlusion_ownership": QA_DIR / "contact_occlusion_ownership_authority.json",
    "body_region_geometry": QA_DIR / "body_region_geometry_authority.json",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(value: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def csv_presence() -> dict[str, object]:
    result: dict[str, object] = {}
    total = 0
    for path, key, target in CSV_TARGETS:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        count = sum(1 for row in rows if row.get(key) == target)
        total += count
        result[rel(path)] = {"key": key, "target": target, "matches": count}
    result["total_matches"] = total
    result["row_present"] = total > 0
    return result


def summarize_full_references() -> dict[str, object]:
    payload = read_json(FULL_REFERENCE_MANIFEST)
    refs = payload.get("full_body_references") if isinstance(payload, dict) else []
    if not isinstance(refs, list):
        refs = []
    knees_to_head = []
    feet_eligible = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        limitations = ref.get("coverage_limitations") or []
        rel_path = str(ref.get("path", ""))
        if any("knees_to_top_of_head" in str(item) for item in limitations) or "New folder" in rel_path:
            knees_to_head.append(ref)
        else:
            feet_eligible.append(ref)
    return {
        "manifest_path": rel(FULL_REFERENCE_MANIFEST),
        "manifest_exists": FULL_REFERENCE_MANIFEST.exists(),
        "sha256": sha256_file(FULL_REFERENCE_MANIFEST) if FULL_REFERENCE_MANIFEST.exists() else "",
        "total_reference_count": len(refs),
        "feet_lower_leg_eligible_reference_count": len(feet_eligible),
        "knees_to_head_limited_reference_count": len(knees_to_head),
        "knees_to_head_limited_paths": [ref.get("path", "") for ref in knees_to_head],
        "user_correction_applied": (
            "Ref_Image_1/Full/New folder/8ead94ca6f2884fb1ae671fee89e8126.jpg is not full body; "
            "it covers knees to top of head and is excluded from feet, toes, ankles, lower-calf, and support proof."
        ),
    }


def summarize_gold_masks() -> dict[str, object]:
    payload = read_json(GOLD_MASK_MANIFEST)
    masks = payload.get("gold_standard_masks") or payload.get("extracted_masks") or []
    if not isinstance(masks, list):
        masks = []
    return {
        "manifest_path": rel(GOLD_MASK_MANIFEST),
        "manifest_exists": GOLD_MASK_MANIFEST.exists(),
        "sha256": sha256_file(GOLD_MASK_MANIFEST) if GOLD_MASK_MANIFEST.exists() else "",
        "gold_mask_count": payload.get("extracted_nonzero_mask_count", len(masks)),
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body masks here are not failures",
            "lower_strip": "primary full-body pose/body-mask validation area",
        },
    }


def summarize_combined_body_reference_matrix() -> dict[str, object]:
    payload = read_json(BODY_REFERENCE_MATRIX)
    ref1 = payload.get("ref_image_1_body_mask_gold_refs", {}) if isinstance(payload, dict) else {}
    ref2 = payload.get("ref_image_2_body_mask_gold_refs", {}) if isinstance(payload, dict) else {}
    ref1_full = payload.get("ref_image_1_full_body_references", {}) if isinstance(payload, dict) else {}
    combined = payload.get("combined_body_reference_matrix", {}) if isinstance(payload, dict) else {}
    ref2_exists = bool(ref2.get("main_reference", {}).get("exists")) if isinstance(ref2, dict) else False
    return {
        "manifest_path": rel(BODY_REFERENCE_MATRIX),
        "manifest_exists": BODY_REFERENCE_MATRIX.exists(),
        "sha256": sha256_file(BODY_REFERENCE_MATRIX) if BODY_REFERENCE_MATRIX.exists() else "",
        "evidence_id": payload.get("evidence_id") if isinstance(payload, dict) else "",
        "qa_decision": payload.get("qa_decision") if isinstance(payload, dict) else "",
        "ref_image_1_gold_mask_count": ref1.get("all_gold_mask_count", 0) if isinstance(ref1, dict) else 0,
        "ref_image_2_gold_mask_count": ref2.get("all_gold_mask_count", 0) if isinstance(ref2, dict) else 0,
        "combined_gold_mask_count": combined.get(
            "combined_gold_mask_count",
            int(ref1.get("all_gold_mask_count", 0) or 0) + int(ref2.get("all_gold_mask_count", 0) or 0),
        )
        if isinstance(combined, dict)
        else 0,
        "ref_image_1_full_or_near_full_reference_count": ref1_full.get("static_pose_reference_count", 0)
        if isinstance(ref1_full, dict)
        else 0,
        "ref_image_2_full_body_reference_count": 1 if ref2_exists else 0,
        "combined_full_or_near_full_reference_count": combined.get(
            "combined_full_or_near_full_reference_count",
            int(ref1_full.get("static_pose_reference_count", 0) or 0) + (1 if ref2_exists else 0),
        )
        if isinstance(combined, dict)
        else 0,
        "limited_reference_policy": "Ref_Image_1/Full/New folder remains knees-to-head only and is not full-body support/feet proof.",
    }


def summarize_route_evidence() -> dict[str, object]:
    result: dict[str, object] = {}
    for name, path in REFERENCE_ROUTE_EVIDENCE.items():
        payload = read_json(path)
        result[name] = {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else "",
            "evidence_id": payload.get("evidence_id"),
            "status": payload.get("status"),
            "qa_decision": payload.get("qa_decision"),
            "decision": payload.get("decision") or payload.get("status_decision"),
            "model_backed_geometry_authority_pass": (payload.get("model_backed_geometry_authority") or {}).get(
                "model_backed_geometry_authority_pass"
            ),
            "model_consensus_geometry_pass": (payload.get("model_backed_geometry_authority") or {}).get(
                "model_consensus_geometry_pass"
            ),
            "canonical_polygon_export_pass": (payload.get("model_backed_geometry_authority") or {}).get(
                "canonical_polygon_export_pass"
            ),
        }
    return result


def evaluate_consensus(route_summary: dict[str, object]) -> dict[str, object]:
    available_reference_routes = [
        name for name, record in route_summary.items() if isinstance(record, dict) and record.get("exists")
    ]
    passing_independent_model_routes = [
        name
        for name, record in route_summary.items()
        if isinstance(record, dict) and record.get("model_consensus_geometry_pass") is True
    ]
    return {
        "consensus_computable": False,
        "model_consensus_geometry_pass": False,
        "available_reference_route_count": len(available_reference_routes),
        "available_reference_routes": available_reference_routes,
        "passing_independent_model_route_count": len(passing_independent_model_routes),
        "passing_independent_model_routes": passing_independent_model_routes,
        "required_for_pass": [
            "two_or_more_independent_model_derived_body_geometry_routes",
            "semantic_human_part_parser_or_dense_pose_output",
            "visibility_occlusion_confidence_for_body_part_ownership",
            "canonical_body_region_polygons",
            "numeric_iou_boundary_center_and_protected_overlap_metrics",
        ],
        "blocked_reason": "Blocked_Model_Consensus_Not_Computable_From_Reference_Manifests_Alone",
        "decision": "ref_images_1_2_reference_context_available_model_consensus_route_not_complete_sequence_ledger_gap",
        "no_mask_promotion": True,
    }


def update_actual_consensus_rows(evidence_paths: list[str], combined_summary: dict[str, object]) -> dict[str, int]:
    updates: dict[str, int] = {}
    note = (
        f"Model consensus validator {RUN_STAMP}: Ref_Image_1+Ref_Image_2 combined body matrix records "
        f"{combined_summary['combined_full_or_near_full_reference_count']} full/near-full references and "
        f"{combined_summary['combined_gold_mask_count']} gold masks, but independent model consensus remains not computable. "
        f"`{TRACKER_ID}` / `{ITEM_ID}` is missing from Wave70 CSVs, so this evidence is attached to actual consensus row "
        f"`{ACTUAL_CONSENSUS_TRACKER_ID}` / `{ACTUAL_CONSENSUS_ITEM_ID}` as a sequence ledger gap. No masks promoted."
    )
    for path, key, target in ACTUAL_CONSENSUS_CSV_TARGETS:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        changed = 0
        for row in rows:
            if row.get(key) != target:
                continue
            changed += 1
            if "Status" in row:
                row["Status"] = "Required_Not_Complete"
            if "Status_Decision" in row:
                row["Status_Decision"] = "ref_images_1_2_reference_context_available_model_consensus_route_not_complete_sequence_ledger_gap"
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_images_1_2_combined_body_reference_matrix_available",
                        "model_consensus_not_computable_from_reference_masks_alone",
                        "wave70_0173_sequence_ledger_gap_detected",
                        "actual_consensus_row_0148_updated",
                        "model_consensus_route_not_complete_no_promotion",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(path)] = changed
    return updates


def make_panel(
    full_summary: dict[str, object],
    gold_summary: dict[str, object],
    combined_summary: dict[str, object],
    csv_summary: dict[str, object],
) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "model_consensus_geometry_validator_reference_route_panel.png"
    panel = Image.new("RGB", (1400, 860), (248, 248, 246))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()

    draw.rectangle([0, 0, 1399, 859], outline=(80, 80, 80), width=2)
    draw.text((36, 28), "Wave70 0173 Model Consensus Geometry Validator", fill=(20, 20, 20), font=title_font)
    draw.text((36, 62), "Ref_Image_1+2 context available; model consensus remains not computable.", fill=(20, 20, 20), font=font)

    lines = [
        f"Gold body mask manifest exists: {gold_summary['manifest_exists']} | masks: {gold_summary['gold_mask_count']}",
        f"Full/near-full references: {full_summary['total_reference_count']}",
        f"Combined Ref_Image_1+2 refs: {combined_summary['combined_full_or_near_full_reference_count']}",
        f"Combined Ref_Image_1+2 gold masks: {combined_summary['combined_gold_mask_count']}",
        f"Feet/lower-leg eligible Full references: {full_summary['feet_lower_leg_eligible_reference_count']}",
        f"Knees-to-head limited references: {full_summary['knees_to_head_limited_reference_count']}",
        "Top strip is partial upper-body only; lower strip is the primary full-body mask validation area.",
        "New folder / 8ead... is excluded from feet, toes, ankles, lower-calf, and support proof.",
        f"{TRACKER_ID} / {ITEM_ID} CSV row present: {csv_summary['row_present']} (ledger gap)",
        f"Actual model-consensus row: {ACTUAL_CONSENSUS_TRACKER_ID} / {ACTUAL_CONSENSUS_ITEM_ID}",
        "No independent multi-model body parser/dense-pose/canonical-polygon consensus metrics exist yet.",
        "No mask was promoted.",
    ]
    y = 120
    for line in lines:
        draw.text((48, y), line, fill=(0, 0, 0), font=font)
        y += 42

    if MAIN_REFERENCE.exists():
        source = Image.open(MAIN_REFERENCE).convert("RGB")
        source.thumbnail((540, 540))
        panel.paste(source, (805, 150))
        draw.rectangle([800, 145, 1350, 695], outline=(120, 120, 120), width=2)
        draw.text((805, 710), "Main Ref_Image_1: top partial strip + lower full-body mask section", fill=(0, 0, 0), font=font)

    panel.save(panel_path)
    return panel_path


def copy_evidence(stamped: Path, canonical: Path, runtime: Path, payload: dict[str, object]) -> list[str]:
    tracker_stamped = TRACKER_EVIDENCE_DIR / stamped.name
    tracker_canonical = TRACKER_EVIDENCE_DIR / canonical.name
    for path in (stamped, canonical, runtime, tracker_stamped, tracker_canonical):
        write_json(path, payload)
    return [rel(stamped), rel(canonical), rel(tracker_stamped), rel(tracker_canonical), rel(runtime)]


def prepend(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    marker = heading[:80]
    if marker in old[:12000]:
        return
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")


def update_hydration(
    evidence_paths: list[str],
    full_summary: dict[str, object],
    combined_summary: dict[str, object],
    csv_summary: dict[str, object],
    row_updates: dict[str, int],
) -> None:
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-evaluated `{TRACKER_ID}` / `{ITEM_ID}` model consensus geometry validator with the corrected Ref_Image_1+Ref_Image_2 context.

Result: Ref_Image_1 gold masks, `Ref_Image_1/Full`, and Ref_Image_2 organized masks are registered through the combined body reference matrix. Combined context now records `{combined_summary['combined_full_or_near_full_reference_count']}` full/near-full references and `{combined_summary['combined_gold_mask_count']}` gold masks. The image under `Ref_Image_1/Full/New folder` remains explicitly limited to knees-to-head coverage and is not used for feet/toes/ankles/lower-calf/support proof.

The validator remains `Required_Not_Complete`: reference masks do not prove independent model consensus. There are no passing multi-model body parser/dense-pose/canonical-polygon metrics, no IoU/boundary/center/protected-overlap consensus record, no generated output proof, and no promotion evidence.

CSV note: `{TRACKER_ID}` / `{ITEM_ID}` is not present in the current Wave70 tracker/item CSVs (`matches={csv_summary['total_matches']}`). This is recorded as a Wave70 sequence ledger gap. Evidence was attached to the actual model-consensus rows `{ACTUAL_CONSENSUS_TRACKER_ID}` / `{ACTUAL_CONSENSUS_ITEM_ID}` with update counts `{json.dumps(row_updates, sort_keys=True)}`.

Reference counts: total Full refs `{full_summary['total_reference_count']}`, feet/lower-leg eligible `{full_summary['feet_lower_leg_eligible_reference_count']}`, knees-to-head limited `{full_summary['knees_to_head_limited_reference_count']}`.

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - 0173 Model Consensus Ref_Image_1 Evidence - {ISO_STAMP}",
        body + f"\n\nNext local action: work `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body protected anchor geometry authority.",
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - 0173 Model Consensus Ref_Image_1 Evidence - {ISO_STAMP}",
        body + f"\n\nCurrent pursuit advances to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}`.",
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - 0173 Model Consensus Ref_Image_1 Evidence - {ISO_STAMP}",
        body + f"\n\nResume at `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body protected anchor geometry authority.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0174 Soft-Body Protected Anchor Geometry",
        body + f"\n\nNext exact local action: implement or exactly block `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` soft-body deformation and protected anchor geometry authority. Do not start EC2 or promote masks without row-level proof.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 0173 Model Consensus Ref_Image_1 Evidence - {ISO_STAMP}",
        body,
    )
    with (HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv").open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 0173 model consensus geometry validator",
                (
                    "Re-evaluated model consensus with Ref_Image_1+Ref_Image_2 combined reference context; recorded "
                    "the knees-to-head New folder limitation; kept consensus fail-closed because independent model "
                    "geometry and canonical polygon metrics are not available; detected absent 0173 CSV control row "
                    "and updated actual model-consensus row 0148."
                ),
                "; ".join(evidence_paths),
                "python py_compile; Ref_Image_1 manifest validation; CSV row presence audit; JSON validation; panel generation",
                "MODEL_CONSENSUS_REF_IMAGES_1_2_REFERENCE_CONTEXT_AVAILABLE_ROUTE_NOT_COMPLETE_SEQUENCE_LEDGER_GAP",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/model_consensus_geometry_validator.json",
                f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} soft-body protected anchor geometry authority next.",
            ]
        )


def main() -> int:
    if not MAIN_REFERENCE.exists():
        raise FileNotFoundError(MAIN_REFERENCE)
    full_summary = summarize_full_references()
    gold_summary = summarize_gold_masks()
    combined_summary = summarize_combined_body_reference_matrix()
    route_summary = summarize_route_evidence()
    csv_summary = csv_presence()
    consensus = evaluate_consensus(route_summary)
    panel_path = make_panel(full_summary, gold_summary, combined_summary, csv_summary)

    stamped_path = QA_DIR / f"{EVIDENCE_ID}.json"
    canonical_path = QA_DIR / "model_consensus_geometry_validator.json"
    runtime_path = RUNTIME_DIR / "model_consensus_geometry_validator.json"

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": f"Re-evaluate {TRACKER_ID} / {ITEM_ID} model consensus geometry validator with Ref_Image_1 context.",
        "script": SCRIPT_REL,
        "main_reference": {
            "path": rel(MAIN_REFERENCE),
            "sha256": sha256_file(MAIN_REFERENCE),
        },
        "full_reference_summary": full_summary,
        "gold_mask_summary": gold_summary,
        "combined_body_reference_matrix": combined_summary,
        "reference_route_evidence": route_summary,
        "csv_control_row_presence": csv_summary,
        "wave70_sequence_ledger_gap": {
            "missing_tracker_id": TRACKER_ID,
            "missing_item_id": ITEM_ID,
            "missing_row_present": bool(csv_summary["row_present"]),
            "actual_consensus_tracker_id": ACTUAL_CONSENSUS_TRACKER_ID,
            "actual_consensus_item_id": ACTUAL_CONSENSUS_ITEM_ID,
            "classification": "MILESTONE_SEQUENCE_LEDGER_GAP",
        },
        "consensus_evaluation": consensus,
        "artifacts": {"panel": rel(panel_path), "runtime_evidence": rel(runtime_path)},
        "model_backed_geometry_authority": {
            "result": "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "canonical_polygon_export_pass": False,
            "no_symmetry_guessing_pass": True,
            "no_human_work_dependency": True,
            "blocked_reason": consensus["blocked_reason"],
        },
        "qa_decision": consensus["decision"],
        "promotion_decision": "no_mask_promoted_no_active_input_changed_model_consensus_reference_context_only",
        "next_step": f"Work {NEXT_TRACKER_ID} / {NEXT_ITEM_ID} soft-body protected anchor geometry authority.",
    }

    evidence_paths = copy_evidence(stamped_path, canonical_path, runtime_path, payload)
    evidence_paths.append(rel(panel_path))
    evidence_paths.extend([rel(FULL_REFERENCE_MANIFEST), rel(GOLD_MASK_MANIFEST), rel(BODY_REFERENCE_MATRIX)])
    row_updates = update_actual_consensus_rows(evidence_paths, combined_summary)
    payload["actual_consensus_row_updates"] = row_updates
    for path in [
        stamped_path,
        canonical_path,
        runtime_path,
        TRACKER_EVIDENCE_DIR / stamped_path.name,
        TRACKER_EVIDENCE_DIR / canonical_path.name,
    ]:
        write_json(path, payload)
    update_hydration(evidence_paths, full_summary, combined_summary, csv_summary, row_updates)

    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "qa_decision": payload["qa_decision"],
                "missing_0173_row_present": csv_summary["row_present"],
                "actual_consensus_row_updates": row_updates,
                "combined_full_or_near_full_reference_count": combined_summary["combined_full_or_near_full_reference_count"],
                "combined_gold_mask_count": combined_summary["combined_gold_mask_count"],
                "evidence": rel(stamped_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
