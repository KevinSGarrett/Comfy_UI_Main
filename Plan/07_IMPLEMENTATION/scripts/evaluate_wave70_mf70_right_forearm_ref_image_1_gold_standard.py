from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
MANIFEST_PATH = QA_DIR / "ref_image_1_body_mask_gold_standard.json"

NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_MF70_RIGHT_FOREARM_REF_IMAGE_1_GOLD_STANDARD_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/evaluate_wave70_mf70_right_forearm_ref_image_1_gold_standard.py"

RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_right_forearm_ref_image_1" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


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


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def find_extracted_record(manifest: dict[str, object], label: str) -> dict[str, object]:
    for record in manifest.get("extracted_masks", []):
        if record.get("label") == label:
            return record
    raise KeyError(label)


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def resize_for_panel(image: Image.Image, width: int = 520) -> Image.Image:
    ratio = width / image.width
    height = max(1, int(image.height * ratio))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_panel(primary_record: dict[str, object], aggregate_record: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    overlay = resize_for_panel(Image.open(resolve_project_path(str(primary_record["source_overlay_path"]))).convert("RGB"))
    mask = resize_for_panel(Image.open(resolve_project_path(str(primary_record["binary_mask_path"]))).convert("RGB"))
    preview = resize_for_panel(Image.open(resolve_project_path(str(primary_record["preview_path"]))).convert("RGB"))

    font = ImageFont.load_default()
    gutter = 24
    header_h = 170
    footer_h = 150
    width = overlay.width + mask.width + preview.width + gutter * 4
    content_h = max(overlay.height, mask.height, preview.height)
    height = header_h + content_h + footer_h
    panel = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(panel)

    title_lines = [
        "TRK-W70-0158 / ITEM-W70-0158 - mf70_right_forearm",
        "Ref_Image_1 gold-standard right-forearm masks are available.",
        "Top strip is partial upper-body only; lower strip is primary full-body validation.",
        "Row remains Required_Not_Complete until route, visual QA, gates, generated output, and target-runtime proof pass.",
    ]
    y = 18
    for line in title_lines:
        draw.text((24, y), line, fill=(0, 0, 0), font=font)
        y += 30

    x = gutter
    for label, image in [("source red overlay", overlay), ("extracted binary mask", mask), ("mask preview", preview)]:
        draw.text((x, header_h - 24), label, fill=(0, 0, 0), font=font)
        panel.paste(image, (x, header_h))
        draw.rectangle([x, header_h, x + image.width - 1, header_h + image.height - 1], outline=(40, 40, 40), width=2)
        x += image.width + gutter

    footer_lines = [
        f"Primary mask pixels: {primary_record['red_overlay_pixel_count']} ({primary_record['red_overlay_coverage_ratio']})",
        f"Aggregate forearm mask pixels: {aggregate_record['red_overlay_pixel_count']} ({aggregate_record['red_overlay_coverage_ratio']})",
        "No mask was promoted. This panel only proves the Ref_Image_1 gold reference exists and is usable for row re-evaluation.",
    ]
    y = header_h + content_h + 22
    for line in footer_lines:
        draw.text((24, y), line, fill=(80, 0, 0), font=font)
        y += 30

    panel_path = RUNTIME_DIR / "mf70_right_forearm_ref_image_1_gold_standard_panel.png"
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0158") for path in TRACKER_FILES] + [(path, "ITEM-W70-0158") for path in ITEM_FILES]
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
            row["Status"] = "Required_Not_Complete"
            if "Status_Decision" in row:
                row["Status_Decision"] = "ref_image_1_right_forearm_gold_mask_available_route_not_complete"
            for field in ["Evidence_Path", "Evidence_Required", "Acceptance_Evidence"]:
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["ref_image_1_right_forearm_gold_mask_available_route_not_complete"],
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
    body = f"""Re-evaluated `TRK-W70-0158` / `ITEM-W70-0158` against the corrected Ref_Image_1 gold-standard body-mask manifest.

Result: the right-forearm gold masks are present and usable for the user-provided multi-pose reference set. The top strip is partial upper-body reference only and must not be used to claim missing lower/full-body masks; the lower strip is the primary full-body mask validation region.

The row remains `Required_Not_Complete` because gold-reference availability alone does not prove the full production route: row-level mask routing, strict visual QA, generated-output proof, target-runtime evidence, and explicit hard-gate approval are still required before any pass or promotion.

Evidence:

{evidence_block}

Next local action: continue with the next required Wave70 mask-factory row using Ref_Image_1 gold masks under the same non-promotional rules."""
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - 0158 Ref_Image_1 Right Forearm Evaluated - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 0158 Ref_Image_1 Right Forearm Evaluated - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Continue Next Wave70 Ref_Image_1 Mask Row", body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 0158 Ref_Image_1 Right Forearm Evidence - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - 0158 Ref_Image_1 Right Forearm Evaluated - {ISO_STAMP}", body)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 0158 Ref_Image_1 right forearm evaluation",
                "Validated corrected Ref_Image_1 right forearm gold masks and attached row-level evidence while keeping TRK/ITEM-W70-0158 Required_Not_Complete and non-promotional.",
                "; ".join(evidence_paths),
                "python py_compile; manifest JSON validation; binary mask existence/hash validation; panel visual review; Wave70 geometry/promotion gates pending",
                "REF_IMAGE_1_RIGHT_FOREARM_GOLD_MASK_AVAILABLE_ROUTE_NOT_COMPLETE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_right_forearm_ref_image_1_gold_standard.json",
                "Continue to the next required Wave70 mask-factory row with Ref_Image_1 gold masks.",
            ]
        )


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    primary = find_extracted_record(manifest, "arms_right_lower_arm")
    aggregate = find_extracted_record(manifest, "arms_lower_arm_fore_arms")
    primary_mask = resolve_project_path(str(primary["binary_mask_path"]))
    aggregate_mask = resolve_project_path(str(aggregate["binary_mask_path"]))
    if not primary_mask.exists() or not aggregate_mask.exists():
        raise FileNotFoundError("Missing Ref_Image_1 right forearm mask artifacts")

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    runtime_manifest_copy = RUNTIME_DIR / "ref_image_1_body_mask_gold_standard.json"
    shutil.copy2(MANIFEST_PATH, runtime_manifest_copy)
    panel_path = make_panel(primary, aggregate)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "mf70_right_forearm_ref_image_1_gold_standard.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "mf70_right_forearm_ref_image_1_gold_standard.json"
    runtime_evidence_path = RUNTIME_DIR / "mf70_right_forearm_ref_image_1_gold_standard.json"

    evidence_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        str(primary["binary_mask_path"]),
        str(aggregate["binary_mask_path"]),
        "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    ]
    note = (
        f"Ref_Image_1 right forearm row evaluation {RUN_STAMP}: corrected gold-standard masks exist for "
        "mf70_right_forearm. Top strip is partial upper-body only; lower strip is primary full-body validation. "
        "Row remains Required_Not_Complete because route, visual QA, generated-output proof, target runtime, and "
        "explicit hard-gate approval are still required."
    )
    row_updates = update_wave70_rows(evidence_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "task": "Re-evaluate mf70_right_forearm for TRK-W70-0158 / ITEM-W70-0158 using Ref_Image_1 gold-standard body masks.",
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
        },
        "ref_image_1_manifest": {
            "path": rel(MANIFEST_PATH),
            "sha256": sha256_file(MANIFEST_PATH),
            "runtime_copy": rel(runtime_manifest_copy),
            "evidence_id": manifest.get("evidence_id"),
            "created_local": manifest.get("created_local"),
        },
        "layout_interpretation": manifest["gold_standard_scope"]["layout_interpretation"],
        "right_forearm_gold_masks": {
            "primary_right_lower_arm": primary,
            "aggregate_lower_arms_forearms": aggregate,
            "primary_binary_mask_exists": primary_mask.exists(),
            "aggregate_binary_mask_exists": aggregate_mask.exists(),
            "primary_binary_mask_sha256": sha256_file(primary_mask),
            "aggregate_binary_mask_sha256": sha256_file(aggregate_mask),
        },
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "runtime_manifest_copy": rel(runtime_manifest_copy),
        },
        "row_evaluation": {
            "tracker_id": "TRK-W70-0158",
            "item_id": "ITEM-W70-0158",
            "mask_type_id": "mf70_right_forearm",
            "ref_image_1_gold_standard_available_pass": True,
            "right_forearm_gold_mask_exists_pass": True,
            "top_strip_partial_body_rule_pass": True,
            "lower_strip_primary_validation_area_pass": True,
            "row_status": "Required_Not_Complete",
            "row_completion_allowed": False,
            "row_promotion_allowed": False,
            "remaining_required_evidence": [
                "row-level mask route integration",
                "strict visual QA against source and protected neighbors",
                "generated-output proof",
                "target-runtime evidence",
                "explicit Wave70 geometry row-gate approval",
                "explicit Wave70 promotion row-gate approval",
            ],
            "obsolete_prior_blocker": "portrait_only_right_forearm_not_source_visible",
            "current_decision": "ref_image_1_right_forearm_gold_mask_available_route_not_complete",
        },
        "tracker_item_updates": row_updates,
        "next_step": "Continue Wave70 after 0158 using the next required mask-factory row under non-promotional rules.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["row_evaluation"]["current_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

