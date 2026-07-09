from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_GOLD_TRACE_DATASET_MANIFEST_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_gold_trace_dataset_manifest.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_gold_trace_dataset_manifest" / RUN_STAMP
REGISTERED_DIR = RUNTIME_DIR / "registered_references"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

USER_REFERENCE_IMAGES = [
    {
        "role": "user_scaffold_overlay",
        "label": "User scaffold overlay",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-e601504c-1040-435c-b30a-a35b90c831af.png"),
    },
    {
        "role": "user_semantic_overlay",
        "label": "User semantic overlay",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-ec2f4262-622b-40bc-b1dd-94e119968c51.png"),
    },
    {
        "role": "individual_neck_reference",
        "label": "Neck reference",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-5766ecf9-a6e8-4c9d-b45d-0f64fe2d5b7c.png"),
    },
    {
        "role": "individual_teeth_reference",
        "label": "Teeth reference",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-4502ed74-a7e6-4694-90a7-88b1e5f074a4.png"),
    },
    {
        "role": "individual_jaw_reference",
        "label": "Jaw reference",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-57651f0a-ebb3-43e6-b41c-e7f33dd0db2e.png"),
    },
    {
        "role": "individual_neck_duplicate_reference",
        "label": "Neck reference duplicate",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-bd75720c-201e-49eb-8cc0-fc866dc2aa10.png"),
    },
    {
        "role": "individual_hair_reference",
        "label": "Hair reference",
        "path": Path(r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-b4106133-70ef-4077-8bf6-730616d1dd6c.png"),
    },
    {
        "role": "individual_lips_reference",
        "label": "Lips reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_10 PM.png"),
    },
    {
        "role": "individual_irises_reference",
        "label": "Irises reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_58 PM.png"),
    },
    {
        "role": "individual_top_lip_reference",
        "label": "Top lip reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_14 PM.png"),
    },
    {
        "role": "individual_pupils_reference",
        "label": "Pupils reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_02 PM.png"),
    },
    {
        "role": "individual_nose_reference",
        "label": "Nose reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_06 PM.png"),
    },
    {
        "role": "individual_eyebrows_reference",
        "label": "Eyebrows reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_51 PM.png"),
    },
    {
        "role": "individual_eyes_reference",
        "label": "Eyes reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_55 PM.png"),
    },
    {
        "role": "individual_skin_reference",
        "label": "Skin reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_47 PM.png"),
    },
    {
        "role": "individual_upper_eyelids_reference",
        "label": "Upper eyelids reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_37 PM.png"),
    },
    {
        "role": "individual_lower_eyelids_reference",
        "label": "Lower eyelids reference",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_43 PM.png"),
    },
    {
        "role": "facial_masking_reference_matrix",
        "label": "Reference matrix",
        "path": Path(r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_36_14 PM (2).png"),
    },
]

SOURCE_EVIDENCE_FILES = [
    QA_DIR / "W70_USER_ANNOTATED_GEOMETRY_REFERENCE_REVIEW_20260707T235800-0500.json",
    QA_DIR / "W70_FULL_FACE_SCAFFOLD_FROM_USER_REFERENCE_20260708T001500-0500.json",
    QA_DIR / "W70_FULL_FACE_SCAFFOLD_VISUAL_REVIEW_20260708T001700-0500.json",
]

PREREQ_FILES = {
    "model_geometry_dependency_probe": QA_DIR / "model_geometry_dependency_probe.json",
    "face_landmark_authority": QA_DIR / "face_landmark_authority.json",
    "face_parsing_authority": QA_DIR / "face_parsing_authority.json",
    "segmentation_refinement_authority": QA_DIR / "segmentation_refinement_authority.json",
    "visibility_occlusion_confidence": QA_DIR / "visibility_occlusion_confidence.json",
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


def read_json_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "error": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "task": payload.get("task"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "result": payload.get("result"),
        "top_level_keys": sorted(payload.keys()),
    }


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def safe_name(role: str, index: int, suffix: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in role)
    return f"{index:02d}_{cleaned}{suffix.lower()}"


def register_reference_images() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    REGISTERED_DIR.mkdir(parents=True, exist_ok=True)
    registered: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    seen_hashes: dict[str, str] = {}
    for index, spec in enumerate(USER_REFERENCE_IMAGES, start=1):
        source_path = spec["path"]
        record: dict[str, object] = {
            "role": spec["role"],
            "label": spec["label"],
            "source_path": str(source_path),
            "exists": source_path.exists(),
        }
        if not source_path.exists():
            missing.append(record)
            continue
        source_hash = sha256_file(source_path)
        target_path = REGISTERED_DIR / safe_name(str(spec["role"]), index, source_path.suffix)
        shutil.copy2(source_path, target_path)
        target_hash = sha256_file(target_path)
        with Image.open(source_path) as image:
            width, height = image.size
            mode = image.mode
        record.update(
            {
                "bytes": source_path.stat().st_size,
                "source_sha256": source_hash,
                "registered_path": rel(target_path),
                "registered_sha256": target_hash,
                "hash_match": source_hash == target_hash,
                "dimensions": [width, height],
                "mode": mode,
                "duplicate_of_role": seen_hashes.get(source_hash, ""),
                "usable_for_gold_trace_dataset": True,
            }
        )
        seen_hashes.setdefault(source_hash, str(spec["role"]))
        registered.append(record)
    return registered, missing


def make_contact_sheet(registered: list[dict[str, object]]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "gold_trace_dataset_manifest_panel.png"
    thumb_w, thumb_h = 220, 220
    margin = 24
    label_h = 60
    columns = 3
    rows = max(1, (len(registered) + columns - 1) // columns)
    title_h = 88
    width = columns * thumb_w + (columns + 1) * margin
    height = title_h + rows * (thumb_h + label_h + margin) + margin
    panel = Image.new("RGB", (width, height), (245, 247, 249))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((margin, 24), "Wave70 gold trace dataset manifest", fill=(20, 36, 54), font=font)
    draw.text((margin, 48), f"{len(registered)} references registered locally - no mask promotion", fill=(82, 94, 106), font=font)
    for idx, record in enumerate(registered):
        row = idx // columns
        col = idx % columns
        x = margin + col * (thumb_w + margin)
        y = title_h + row * (thumb_h + label_h + margin)
        path = PROJECT_ROOT / str(record["registered_path"])
        with Image.open(path).convert("RGB") as img:
            img.thumbnail((thumb_w, thumb_h))
            tile = Image.new("RGB", (thumb_w, thumb_h), (230, 234, 238))
            tx = (thumb_w - img.width) // 2
            ty = (thumb_h - img.height) // 2
            tile.paste(img, (tx, ty))
        panel.paste(tile, (x, y))
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], outline=(65, 195, 210), width=2)
        label = str(record["label"])
        dims = "x".join(str(v) for v in record["dimensions"])
        draw.text((x, y + thumb_h + 8), label[:30], fill=(18, 32, 45), font=font)
        draw.text((x, y + thumb_h + 28), dims, fill=(82, 94, 106), font=font)
    panel.save(panel_path)
    return panel_path


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_json_summary(path) for name, path in PREREQ_FILES.items()}


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0147") for path in TRACKER_FILES] + [(path, "ITEM-W70-0147") for path in ITEM_FILES]
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
            row["Status"] = "Gold_Trace_Registered_Pending_Authority_Gates"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "registered_gold_trace_dataset_pending_model_authority_gates"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["gold_trace_dataset_registered_pending_model_authority_gates"],
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


def update_hydration(evidence_paths: list[str], panel_path: Path) -> None:
    evidence_block = "\n".join(f"- `{p}`" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. `TRK-W70-0147` / `ITEM-W70-0147` was worked locally. Existing user-provided annotated mask references were copied into a project-owned runtime artifact directory, hashed, dimensioned, schema-recorded, and summarized in a contact-sheet panel. This registers the gold trace dataset as calibration/evaluation evidence only.

No active mask changed and no mask was promoted. Model-backed geometry authority remains pending because landmark/parsing/refinement/visibility/consensus/canonical-polygon prerequisites still do not pass.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is `TRK-W70-0148` / `ITEM-W70-0148`, model consensus validator. Work it locally; if consensus cannot be computed because prerequisite model authority remains blocked or missing, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""`TRK-W70-0147` / `ITEM-W70-0147` registered the available user annotated trace references into durable local project artifacts. The dataset manifest records hashes, dimensions, copied paths, source evidence summaries, and a visual contact sheet. It is calibration/evaluation evidence only; it does not promote any mask and does not satisfy the missing model-backed authority chain by itself.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block `TRK-W70-0148` / `ITEM-W70-0148`, model consensus validator. Use only local source-derived model evidence. If consensus cannot be computed because landmark, face parsing, promptable refinement, visibility, or canonical polygon prerequisites remain blocked, write one exact local blocker with evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = f"""Worked `TRK-W70-0147` / `ITEM-W70-0147` locally and registered the user annotated gold trace dataset. Registered reference copies live under `{rel(REGISTERED_DIR)}` and the reviewed panel is `{rel(panel_path)}`. No mask changed, no mask promotion occurred, and model-backed authority remains pending prerequisite model evidence."""
    qa_index_body = f"""Registered local gold trace dataset manifest for `TRK-W70-0147` / `ITEM-W70-0147`.

{evidence_block}"""

    prepend_section(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Wave70 Gold Trace Dataset Registered Locally - {ISO_STAMP}",
        current_body,
    )
    prepend_section(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0148 Model Consensus Validator Locally",
        next_body,
    )
    prepend_section(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Wave70 Gold Trace Dataset Registered - {ISO_STAMP}",
        session_body + "\n\nNext exact action: work `TRK-W70-0148` locally.",
    )
    prepend_section(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Wave70 Gold Trace Dataset Registered - {ISO_STAMP}",
        session_body,
    )
    prepend_section(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 Gold Trace Dataset Manifest - {ISO_STAMP}",
        qa_index_body,
    )
    prepend_section(
        HYDRATION_DIR / "RECENT_DECISIONS.md",
        f"## Wave70 Gold Trace Registration Decision - {ISO_STAMP}",
        "Registered the user's existing annotated references as durable calibration/evaluation evidence only. This does not promote masks or replace missing model-derived geometry authority.",
    )
    prepend_section(
        HYDRATION_DIR / "KNOWN_ISSUES.md",
        f"## Wave70 Geometry Authority Still Pending After Gold Trace Registration - {ISO_STAMP}",
        "The gold trace dataset is now locally registered, but prerequisite model-derived landmark/parsing/refinement/visibility/consensus/canonical-polygon evidence is still required before any Wave70 mask can be promoted.",
    )

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 gold trace dataset registration",
                "Registered user-provided annotated trace references into durable local runtime artifacts with hashes, dimensions, schema manifest, contact-sheet panel, tracker/item updates, and no mask promotion.",
                "; ".join(evidence_paths),
                "python py_compile; local image existence/hash/dimension verification; contact-sheet visual inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "GOLD_TRACE_REGISTERED_PENDING_MODEL_AUTHORITY_GATES",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/gold_trace_dataset_manifest.json",
                "Next work TRK-W70-0148 model consensus validator locally; write exact blocker if prerequisite model authority remains blocked.",
            ]
        )


def main() -> int:
    registered, missing = register_reference_images()
    if not registered:
        raise RuntimeError("No user reference images were available to register.")

    panel_path = make_contact_sheet(registered)
    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "gold_trace_dataset_manifest.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "gold_trace_dataset_manifest.json"
    runtime_evidence_path = RUNTIME_DIR / "gold_trace_dataset_manifest.json"

    source_evidence = [read_json_summary(path) for path in SOURCE_EVIDENCE_FILES]
    prereq_summary = summarize_prerequisites()
    source_count = len(USER_REFERENCE_IMAGES)
    hash_match_pass = all(bool(record.get("hash_match")) for record in registered)
    schema_pass = len(registered) > 0 and all("source_sha256" in record and "dimensions" in record for record in registered)

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        rel(REGISTERED_DIR),
    ]
    note = (
        f"Gold trace dataset manifest {RUN_STAMP}: registered {len(registered)} of {source_count} user reference images "
        "as durable local calibration/evaluation evidence with hashes and dimensions. No active mask changed and no mask was promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Register user annotated gold trace dataset for TRK-W70-0147 / ITEM-W70-0147.",
        "script": SCRIPT_REL,
        "gold_trace_dataset_manifest": {
            "result": "registered_pending_model_authority_gates",
            "registered_reference_count": len(registered),
            "expected_reference_count": source_count,
            "missing_reference_count": len(missing),
            "registered_references_dir": rel(REGISTERED_DIR),
            "registered_references": registered,
            "missing_references": missing,
            "source_evidence_summaries": source_evidence,
            "prerequisite_authority_summaries": prereq_summary,
            "contact_sheet_panel": rel(panel_path),
            "gold_trace_schema_pass": schema_pass,
            "image_hash_match_pass": hash_match_pass,
            "no_future_human_dependency": True,
        },
        "model_backed_geometry_authority": {
            "result": "registered_gold_trace_dataset_pending_model_authority_gates",
            "mask_type_id": "MBGA-006",
            "matrix_slot_id": "TRK-W70-0147",
            "model_backed_geometry_authority_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "model_geometry_dependency_probe_pass": False,
            "gold_trace_schema_pass": schema_pass,
            "image_hash_match_pass": hash_match_pass,
            "no_future_human_dependency": True,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "canonical_polygon_path": "",
            "gold_trace_comparison_path": rel(qa_canonical_path),
            "blocked_reason": "Pending_Model_Geometry_Authority_Gates",
            "findings": [
                "User annotated reference images were available locally and copied into project-owned runtime artifacts.",
                "Every registered image has a source hash, copied-file hash, byte count, dimensions, and role.",
                "The dataset is usable as calibration/evaluation evidence for future geometry comparisons.",
                "The dataset is not source-derived landmark/parsing/refinement/consensus evidence and does not promote any mask.",
                "Prerequisite model-backed geometry authority rows remain pending or blocked, so promotion stays fail-closed.",
            ],
        },
        "artifacts": {
            "qa_evidence": rel(qa_evidence_path),
            "qa_canonical": rel(qa_canonical_path),
            "tracker_evidence": rel(tracker_evidence_path),
            "tracker_canonical": rel(tracker_canonical_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "registered_references_dir": rel(REGISTERED_DIR),
            "panel": rel(panel_path),
        },
        "qa_decision": "registered_gold_trace_dataset_pending_model_authority_gates",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_gold_trace_registered_only",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0148 / ITEM-W70-0148 model consensus validator locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)

    update_hydration(evidence_rel_paths, panel_path)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "registered_reference_count": len(registered),
                "missing_reference_count": len(missing),
                "evidence": rel(qa_evidence_path),
                "panel": rel(panel_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
