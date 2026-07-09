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
EVIDENCE_ID = f"W70_MF70_BODY_SKIN_VISIBLE_REF_IMAGE_1_GOLD_STANDARD_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/evaluate_wave70_mf70_body_skin_visible_ref_image_1_gold_standard.py"

RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_body_skin_visible_ref_image_1" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

# Component overlays that represent visible body skin regions in Ref_Image_1.
# Face detail, hair, clothing, and background are intentionally excluded.
BODY_SKIN_COMPONENT_LABELS = [
    "arms_upper_arms",
    "arms_lower_arm_fore_arms",
    "hands_both_hands",
    "breasts_both",
    "abdomen_stomach",
    "pelvic_pelvic_region",
    "glute_both",
    "thigh_both_thighs",
    "calves_both_calves",
    "feet_both_feet",
    "feet_toes_feet",
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


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def find_record(manifest: dict[str, object], label: str) -> dict[str, object]:
    for record in manifest.get("extracted_masks", []):
        if record.get("label") == label:
            return record
    raise KeyError(label)


def make_composite_mask(records: list[dict[str, object]], group_name: str) -> dict[str, object]:
    if not records:
        raise ValueError("No body-skin component records supplied")
    first_mask = Image.open(resolve_project_path(str(records[0]["binary_mask_path"]))).convert("L")
    composite = Image.new("L", first_mask.size, 0)
    comp_pixels = composite.load()
    component_summaries = []

    for record in records:
        mask_path = resolve_project_path(str(record["binary_mask_path"]))
        mask = Image.open(mask_path).convert("L")
        if mask.size != composite.size:
            raise ValueError(f"Mask size mismatch for {record['label']}: {mask.size} != {composite.size}")
        pixels = mask.load()
        component_count = 0
        for y in range(mask.height):
            for x in range(mask.width):
                if pixels[x, y] > 0:
                    component_count += 1
                    comp_pixels[x, y] = 255
        component_summaries.append(
            {
                "label": record["label"],
                "source_overlay_path": record["source_overlay_path"],
                "binary_mask_path": record["binary_mask_path"],
                "binary_mask_sha256": record["binary_mask_sha256"],
                "component_pixel_count": component_count,
                "component_coverage_ratio": round(component_count / float(mask.width * mask.height), 6),
            }
        )

    composite_path = RUNTIME_DIR / f"mf70_body_skin_visible_ref_image_1_{group_name}_composite_mask.png"
    composite_path.parent.mkdir(parents=True, exist_ok=True)
    composite.save(composite_path)
    composite_count = composite.histogram()[255]
    return {
        "composite_mask_path": rel(composite_path),
        "composite_mask_sha256": sha256_file(composite_path),
        "dimensions": [composite.width, composite.height],
        "composite_pixel_count": composite_count,
        "composite_coverage_ratio": round(composite_count / float(composite.width * composite.height), 6),
        "components": component_summaries,
    }


def make_composite_masks_by_layout(records: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, int], list[dict[str, object]]] = {}
    for record in records:
        mask = Image.open(resolve_project_path(str(record["binary_mask_path"]))).convert("L")
        groups.setdefault(mask.size, []).append(record)

    composites = []
    for index, (size, group_records) in enumerate(sorted(groups.items(), key=lambda item: item[0]), start=1):
        composite = make_composite_mask(group_records, f"layout_{index}_{size[0]}x{size[1]}")
        composite["layout_group"] = f"layout_{index}"
        composite["layout_dimensions"] = [size[0], size[1]]
        composite["layout_component_count"] = len(group_records)
        composites.append(composite)
    return composites


def resize_for_panel(image: Image.Image, width: int = 520) -> Image.Image:
    ratio = width / image.width
    height = max(1, int(image.height * ratio))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_preview(source_overlay_path: Path, composite_mask_path: Path, group_name: str) -> Path:
    source = Image.open(source_overlay_path).convert("RGB")
    mask = Image.open(composite_mask_path).convert("L")
    preview = source.copy()
    src_pixels = preview.load()
    mask_pixels = mask.load()
    for y in range(preview.height):
        for x in range(preview.width):
            if mask_pixels[x, y] > 0:
                r, g, b = src_pixels[x, y]
                src_pixels[x, y] = (min(255, int(r * 0.45) + 140), int(g * 0.45), int(b * 0.45))
    preview_path = RUNTIME_DIR / f"mf70_body_skin_visible_ref_image_1_{group_name}_composite_preview.png"
    preview.save(preview_path)
    return preview_path


def make_panel(source_overlay_path: Path, composite: dict[str, object], preview_path: Path, composite_count: int) -> Path:
    source = resize_for_panel(Image.open(source_overlay_path).convert("RGB"))
    mask = resize_for_panel(Image.open(resolve_project_path(str(composite["composite_mask_path"]))).convert("RGB"))
    preview = resize_for_panel(Image.open(preview_path).convert("RGB"))

    font = ImageFont.load_default()
    gutter = 24
    header_h = 190
    footer_h = 170
    width = source.width + mask.width + preview.width + gutter * 4
    content_h = max(source.height, mask.height, preview.height)
    height = header_h + content_h + footer_h
    panel = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(panel)

    title_lines = [
        "TRK-W70-0159 / ITEM-W70-0159 - mf70_body_skin_visible",
        "Ref_Image_1 has no single body-skin overlay; this is a composite from labeled skin/body-part masks.",
        "Top strip is partial upper-body only; lower strip is primary full-body validation.",
        "Row remains Required_Not_Complete until route, visual QA, gates, generated output, and target-runtime proof pass.",
    ]
    y = 18
    for line in title_lines:
        draw.text((24, y), line, fill=(0, 0, 0), font=font)
        y += 32

    x = gutter
    for label, image in [("component source sample", source), ("composite binary mask", mask), ("composite preview", preview)]:
        draw.text((x, header_h - 24), label, fill=(0, 0, 0), font=font)
        panel.paste(image, (x, header_h))
        draw.rectangle([x, header_h, x + image.width - 1, header_h + image.height - 1], outline=(40, 40, 40), width=2)
        x += image.width + gutter

    footer_lines = [
        f"Components: {len(composite['components'])}",
        f"Composite pixels: {composite['composite_pixel_count']} ({composite['composite_coverage_ratio']})",
        f"Composite layout groups built: {composite_count}",
        "No mask was promoted. This panel proves composite gold-reference availability only.",
        "Direct all-visible-body-skin overlay is missing, so the row remains route-not-complete.",
    ]
    y = header_h + content_h + 22
    for line in footer_lines:
        draw.text((24, y), line, fill=(80, 0, 0), font=font)
        y += 30

    panel_path = RUNTIME_DIR / "mf70_body_skin_visible_ref_image_1_gold_standard_panel.png"
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0159") for path in TRACKER_FILES] + [(path, "ITEM-W70-0159") for path in ITEM_FILES]
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
                row["Status_Decision"] = "ref_image_1_body_skin_composite_gold_mask_available_route_not_complete"
            for field in ["Evidence_Path", "Evidence_Required", "Acceptance_Evidence"]:
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["ref_image_1_body_skin_composite_gold_mask_available_route_not_complete"],
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
    body = f"""Re-evaluated `TRK-W70-0159` / `ITEM-W70-0159` against the corrected Ref_Image_1 gold-standard body-mask manifest.

Result: Ref_Image_1 does not contain one direct all-visible-body-skin overlay, but a composite body-skin reference was built from labeled visible-skin/body-part gold masks while excluding face detail, hair, clothing, and background. The top strip is partial upper-body reference only and must not be used to claim missing lower/full-body masks; the lower strip is the primary full-body validation region.

The row remains `Required_Not_Complete` because composite gold-reference availability alone does not prove the full production route: row-level mask routing, strict visual QA, generated-output proof, target-runtime evidence, and explicit hard-gate approval are still required before any pass or promotion.

Evidence:

{evidence_block}

Next local action: identify and work the next required Wave70 mask-factory row using Ref_Image_1 gold masks where applicable, under the same non-promotional rules."""
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - 0159 Ref_Image_1 Body Skin Composite Evaluated - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 0159 Ref_Image_1 Body Skin Composite Evaluated - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Continue Next Wave70 Ref_Image_1 Mask Row", body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 0159 Ref_Image_1 Body Skin Composite Evidence - {ISO_STAMP}", body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - 0159 Ref_Image_1 Body Skin Composite Evaluated - {ISO_STAMP}", body)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 0159 Ref_Image_1 body skin composite evaluation",
                "Built and validated a Ref_Image_1 composite visible-body-skin gold reference from labeled skin/body-part overlays while keeping TRK/ITEM-W70-0159 Required_Not_Complete and non-promotional.",
                "; ".join(evidence_paths),
                "python py_compile; manifest JSON validation; component mask existence/hash validation; composite mask generation; panel visual review; Wave70 geometry/promotion gates pending",
                "REF_IMAGE_1_BODY_SKIN_COMPOSITE_GOLD_MASK_AVAILABLE_ROUTE_NOT_COMPLETE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_body_skin_visible_ref_image_1_gold_standard.json",
                "Identify and work next required Wave70 mask-factory row with Ref_Image_1 gold masks.",
            ]
        )


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = [find_record(manifest, label) for label in BODY_SKIN_COMPONENT_LABELS]
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    runtime_manifest_copy = RUNTIME_DIR / "ref_image_1_body_mask_gold_standard.json"
    shutil.copy2(MANIFEST_PATH, runtime_manifest_copy)

    composites = make_composite_masks_by_layout(records)
    primary_composite = max(composites, key=lambda item: item["layout_component_count"])
    primary_component = primary_composite["components"][0]
    sample_source = resolve_project_path(str(primary_component["source_overlay_path"]))
    preview_path = make_preview(
        sample_source,
        resolve_project_path(str(primary_composite["composite_mask_path"])),
        str(primary_composite["layout_group"]),
    )
    panel_path = make_panel(sample_source, primary_composite, preview_path, len(composites))

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "mf70_body_skin_visible_ref_image_1_gold_standard.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "mf70_body_skin_visible_ref_image_1_gold_standard.json"
    runtime_evidence_path = RUNTIME_DIR / "mf70_body_skin_visible_ref_image_1_gold_standard.json"

    component_paths = [str(record["binary_mask_path"]) for record in records]
    evidence_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        *[str(composite["composite_mask_path"]) for composite in composites],
        rel(preview_path),
        "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    ] + component_paths
    note = (
        f"Ref_Image_1 body skin visible evaluation {RUN_STAMP}: no direct all-visible-body-skin overlay exists, "
        "but a composite visible-body-skin gold reference was built from labeled skin/body-part overlays. "
        "Top strip is partial upper-body only; lower strip is primary full-body validation. Row remains "
        "Required_Not_Complete because route, visual QA, generated-output proof, target runtime, and explicit "
        "hard-gate approval are still required."
    )
    row_updates = update_wave70_rows(evidence_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "task": "Re-evaluate mf70_body_skin_visible for TRK-W70-0159 / ITEM-W70-0159 using Ref_Image_1 gold-standard body masks.",
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
        "body_skin_gold_reference": {
            "direct_all_visible_body_skin_overlay_exists": False,
            "composite_body_skin_reference_built": True,
            "composite_layout_group_count": len(composites),
            "composite_layout_rule": "Component overlays have different dimensions; composites are built per matching overlay layout instead of forcing incompatible pixel spaces together.",
            "excluded_regions": ["face_detail", "hair", "clothing", "background"],
            "component_labels": BODY_SKIN_COMPONENT_LABELS,
            "composites": composites,
            "primary_panel_composite": primary_composite["layout_group"],
            "preview_path": rel(preview_path),
            "preview_sha256": sha256_file(preview_path),
        },
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "runtime_manifest_copy": rel(runtime_manifest_copy),
        },
        "row_evaluation": {
            "tracker_id": "TRK-W70-0159",
            "item_id": "ITEM-W70-0159",
            "mask_type_id": "mf70_body_skin_visible",
            "ref_image_1_gold_standard_available_pass": True,
            "direct_body_skin_overlay_exists_pass": False,
            "composite_body_skin_gold_mask_exists_pass": True,
            "top_strip_partial_body_rule_pass": True,
            "lower_strip_primary_validation_area_pass": True,
            "row_status": "Required_Not_Complete",
            "row_completion_allowed": False,
            "row_promotion_allowed": False,
            "remaining_required_evidence": [
                "direct or accepted composite body-skin route integration",
                "strict visual QA against source and protected neighbors",
                "generated-output proof",
                "target-runtime evidence",
                "explicit Wave70 geometry row-gate approval",
                "explicit Wave70 promotion row-gate approval",
            ],
            "current_decision": "ref_image_1_body_skin_composite_gold_mask_available_route_not_complete",
        },
        "tracker_item_updates": row_updates,
        "next_step": "Identify and work the next required Wave70 mask-factory row using Ref_Image_1 gold masks under non-promotional rules.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["row_evaluation"]["current_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
