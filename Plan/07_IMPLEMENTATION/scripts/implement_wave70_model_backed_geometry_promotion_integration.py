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
NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_MODEL_BACKED_GEOMETRY_PROMOTION_INTEGRATION_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_model_backed_geometry_promotion_integration.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_model_backed_geometry_promotion_integration" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQ_FILES = {
    "model_geometry_dependency_probe": QA_DIR / "model_geometry_dependency_probe.json",
    "face_landmark_authority": QA_DIR / "face_landmark_authority.json",
    "face_parsing_authority": QA_DIR / "face_parsing_authority.json",
    "segmentation_refinement_authority": QA_DIR / "segmentation_refinement_authority.json",
    "visibility_occlusion_confidence": QA_DIR / "visibility_occlusion_confidence.json",
    "gold_trace_dataset_manifest": QA_DIR / "gold_trace_dataset_manifest.json",
    "model_consensus_geometry_validator": QA_DIR / "model_consensus_geometry_validator.json",
    "canonical_geometry_polygon_export": QA_DIR / "canonical_geometry_polygon_export.json",
    "model_geometry_reference_matrix": QA_DIR / "model_geometry_reference_matrix.json",
    "body_hand_contact_geometry_authority": QA_DIR / "body_hand_contact_geometry_authority.json",
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


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "error": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    mbga = payload.get("model_backed_geometry_authority")
    matrix = payload.get("model_geometry_reference_matrix")
    gold = payload.get("gold_trace_dataset_manifest")
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
        "model_geometry_dependency_probe_pass": deep_get(mbga, ["model_geometry_dependency_probe_pass"]),
        "reference_image_matrix_pass": deep_get(matrix, ["reference_image_matrix_pass"])
        if isinstance(matrix, dict)
        else deep_get(mbga, ["reference_image_matrix_pass"]),
        "cross_subject_generalization_pass": deep_get(matrix, ["cross_subject_generalization_pass"])
        if isinstance(matrix, dict)
        else deep_get(mbga, ["cross_subject_generalization_pass"]),
        "source_visibility_matrix_pass": deep_get(matrix, ["source_visibility_matrix_pass"])
        if isinstance(matrix, dict)
        else deep_get(mbga, ["source_visibility_matrix_pass"]),
        "whole_body_geometry_authority_pass": deep_get(mbga, ["whole_body_geometry_authority_pass"]),
        "registered_reference_count": deep_get(gold, ["registered_reference_count"]),
        "blocked_reason": deep_get(mbga, ["blocked_reason"]) or payload.get("blocked_reason"),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_json(path) for name, path in PREREQ_FILES.items()}


def evaluate_integration(prereqs: dict[str, object]) -> dict[str, object]:
    matrix = prereqs.get("model_geometry_reference_matrix", {})
    required_passes = {
        "model_geometry_dependency_probe_pass": prereqs.get("model_geometry_dependency_probe", {}).get(
            "model_geometry_dependency_probe_pass"
        )
        is True,
        "source_derived_landmark_or_segmentation_pass": any(
            prereqs.get(name, {}).get("source_derived_landmark_or_segmentation_pass") is True
            for name in ["face_landmark_authority", "face_parsing_authority", "segmentation_refinement_authority"]
        ),
        "visibility_occlusion_confidence_pass": prereqs.get("visibility_occlusion_confidence", {}).get(
            "visibility_occlusion_confidence_pass"
        )
        is True,
        "model_consensus_geometry_pass": prereqs.get("model_consensus_geometry_validator", {}).get(
            "model_consensus_geometry_pass"
        )
        is True,
        "canonical_polygon_export_pass": prereqs.get("canonical_geometry_polygon_export", {}).get(
            "canonical_polygon_export_pass"
        )
        is True,
        "reference_image_matrix_pass": matrix.get("reference_image_matrix_pass") is True,
        "model_backed_geometry_authority_pass": matrix.get("model_backed_geometry_authority_pass") is True,
    }
    failed = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed,
        "promotion_gate_integration_pass": False,
        "model_backed_geometry_authority_row_gate_token_emitted": False,
        "wave70_mask_geometry_row_gate_token_emitted": False,
        "wave70_mask_promotion_row_gate_token_emitted": False,
        "completion_allowed": False,
        "blocking_reason": "Blocked_Model_Geometry_Authority_Not_Integrated",
    }


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "model_backed_geometry_promotion_integration_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))

    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 318], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0153 blocked",
        "Model-backed authority cannot be integrated as pass.",
        f"Failed requirements: {len(evaluation['failed_requirements'])}",
        "No row-gate approval token emitted.",
        "Promotion gate remains fail-closed.",
        "Generated-output proof cannot override geometry.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 34

    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0153") for path in TRACKER_FILES] + [(path, "ITEM-W70-0153") for path in ITEM_FILES]
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
            if "Status" in row:
                row["Status"] = "Blocked_Model_Geometry_Authority_Not_Integrated"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_model_backed_geometry_authority_not_integrated"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_model_backed_geometry_authority_not_integrated"],
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
    evidence_block = "\n".join(f"- {p}" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. TRK-W70-0153 / ITEM-W70-0153 was worked locally and is exactly blocked: model-backed authority cannot be integrated into the Wave70 promotion gate as a passing route because dependency, source-derived geometry, visibility, consensus, canonical polygon, and reference-matrix prerequisites remain blocked.

No model-backed row-gate approval token was emitted. No active mask changed and no mask was promoted.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is TRK-W70-0154 / ITEM-W70-0154, prove Mask Factory mask type mf70_belly_button_umbilicus. Work it locally under the same authority rules; if whole-body/model-backed geometry prerequisites remain blocked, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""TRK-W70-0153 / ITEM-W70-0153 is exactly blocked with local model-backed promotion integration evidence. Model-backed authority is now explicitly integrated as a fail-closed promotion prerequisite; no approval token, generalized claim, active mask change, or mask promotion occurred.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block TRK-W70-0154 / ITEM-W70-0154, mf70_belly_button_umbilicus. Use only source-derived whole-body/model-backed geometry evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = (
        "Worked TRK-W70-0153 / ITEM-W70-0153 locally. Model-backed authority promotion integration is blocked "
        "because prerequisite authority remains unavailable. No row-gate token or mask promotion occurred."
    )
    blocker_body = (
        "TRK-W70-0153 / ITEM-W70-0153: Blocked_Model_Geometry_Authority_Not_Integrated. "
        "The Wave70 promotion gate must remain fail-closed until exact model-backed authority evidence passes."
    )

    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 Model-Backed Promotion Integration Blocked Locally - {ISO_STAMP}", current_body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0154 Belly Button Umbilicus Locally", next_body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - Wave70 Model-Backed Promotion Integration Blocked - {ISO_STAMP}", session_body + "\n\nNext exact action: work TRK-W70-0154 locally.")
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - Wave70 Model-Backed Promotion Integration Blocked - {ISO_STAMP}", session_body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 Model-Backed Promotion Integration Evidence - {ISO_STAMP}", f"{session_body}\n\n{evidence_block}")
    prepend_section(HYDRATION_DIR / "BLOCKERS.md", f"## Wave70 Model-Backed Promotion Integration Blocker - {ISO_STAMP}", blocker_body + "\n\n" + evidence_block)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 model-backed promotion integration blocker",
                "Worked TRK/ITEM-W70-0153 locally. Model-backed authority could not be integrated into the promotion gate as pass because prerequisite authority remains blocked. Wrote stamped/canonical evidence, generated a blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; model-backed authority prerequisite review; promotion protocol review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_MODEL_GEOMETRY_AUTHORITY_NOT_INTEGRATED",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/model_backed_geometry_promotion_integration.json",
                "Next work TRK-W70-0154 belly button/umbilicus locally; write exact blocker if authority remains blocked.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_integration(prereqs)
    panel_path = make_blocker_panel(source, evaluation)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "model_backed_geometry_promotion_integration.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "model_backed_geometry_promotion_integration.json"
    runtime_evidence_path = RUNTIME_DIR / "model_backed_geometry_promotion_integration.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"Model-backed geometry promotion integration {RUN_STAMP}: exact local blocker. "
        "Model-backed authority cannot be integrated as pass because prerequisite model-backed geometry authority "
        "and reference-matrix evidence remain blocked. No row-gate approval token emitted and no masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Integrate model-backed authority into Wave70 promotion gate for TRK-W70-0153 / ITEM-W70-0153.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prereqs,
        "promotion_integration_readiness": evaluation,
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
            "mask_type_id": "MBGA-012",
            "matrix_slot_id": "TRK-W70-0153",
            "models_attempted": ["model_backed_geometry_promotion_gate_integration"],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": rel(QA_DIR / "visibility_occlusion_confidence.json"),
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": "",
            "gold_trace_comparison_path": rel(QA_DIR / "gold_trace_dataset_manifest.json"),
            "model_geometry_dependency_probe_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "reference_image_matrix_pass": False,
            "cross_subject_generalization_pass": False,
            "source_visibility_matrix_pass": False,
            "whole_body_geometry_authority_pass": False,
            "blocked_reason": "Blocked_Model_Geometry_Authority_Not_Integrated",
            "findings": [
                "Model-backed authority is now represented as a fail-closed promotion prerequisite.",
                "No model-backed geometry route currently passes, so no W70_MODEL_BACKED_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE token was emitted.",
                "No wave70_mask_geometry_gate_pass or wave70_mask_promotion_gate_pass approval token was emitted for a mask row by this integration.",
                "Generated-output stability remains insufficient to promote masks without model-backed authority.",
                "No active mask changed and no mask was promoted.",
            ],
        },
        "model_backed_geometry_promotion_integration": {
            "result": "blocked",
            "blocker_status": "Blocked_Model_Geometry_Authority_Not_Integrated",
            "promotion_gate_integration_pass": False,
            "model_backed_geometry_authority_row_gate_token_emitted": False,
            "wave70_mask_geometry_row_gate_token_emitted": False,
            "wave70_mask_promotion_row_gate_token_emitted": False,
            "fail_closed_policy_confirmed": True,
            "completion_allowed": False,
            "masks_changed": [],
            "masks_promoted": [],
            "failed_requirements": evaluation["failed_requirements"],
        },
        "qa_decision": "blocked_exact_local_model_backed_geometry_authority_not_integrated",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_model_backed_integration_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0154 / ITEM-W70-0154 mf70_belly_button_umbilicus locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
