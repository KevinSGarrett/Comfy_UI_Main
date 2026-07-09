#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


RUN_STAMP = "20260707T211500-0500"
DISPUTE_EVIDENCE = (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MASK_ALIGNMENT_USER_DISPUTE_GLOBAL_REVIEW_20260707T211000-0500.json"
)
SOURCE_IMAGE = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
MASK_RECORDS = [
    {
        "mask_type_id": "mf70_under_eye",
        "tracker_id": "TRK-W70-0015",
        "item_id": "ITEM-W70-0015",
        "corrected_status": "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "decision": "needs_revision_user_disputed",
    },
    {
        "mask_type_id": "mf70_eyebrows",
        "tracker_id": "TRK-W70-0016",
        "item_id": "ITEM-W70-0016",
        "corrected_status": "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "decision": "needs_revision_user_disputed",
    },
    {
        "mask_type_id": "mf70_nose",
        "tracker_id": "TRK-W70-0017",
        "item_id": "ITEM-W70-0017",
        "corrected_status": "Mask_Alignment_Fail_Generated_Output_Safe_Target_Runtime_Pending",
        "decision": "fail_user_disputed",
    },
    {
        "mask_type_id": "mf70_mouth_lips",
        "tracker_id": "TRK-W70-0018",
        "item_id": "ITEM-W70-0018",
        "corrected_status": "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "decision": "needs_revision_user_disputed",
    },
    {
        "mask_type_id": "mf70_teeth",
        "tracker_id": "TRK-W70-0019",
        "item_id": "ITEM-W70-0019",
        "corrected_status": "Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending",
        "decision": "needs_revision_user_disputed",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_rel(root: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / raw.replace("/", "\\")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mask_bbox(mask: Image.Image, margin: int) -> tuple[int, int, int, int]:
    bbox = mask.point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return (0, 0, mask.width, mask.height)
    left, top, right, bottom = bbox
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(mask.width, right + margin),
        min(mask.height, bottom + margin),
    )


def fit_crop_to_square(crop: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = crop
    crop_w = right - left
    crop_h = bottom - top
    side = max(crop_w, crop_h)
    cx = (left + right) // 2
    cy = (top + bottom) // 2
    left = max(0, cx - side // 2)
    top = max(0, cy - side // 2)
    right = min(width, left + side)
    bottom = min(height, top + side)
    left = max(0, right - side)
    top = max(0, bottom - side)
    return (left, top, right, bottom)


def make_source_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (0, 255, 128, 0))
    fill.putalpha(mask.point(lambda v: min(150, int(v * 0.58))))
    edges = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 8 else 0)
    outline = Image.new("RGBA", rgba.size, (255, 0, 0, 0))
    outline.putalpha(edges)
    return Image.alpha_composite(Image.alpha_composite(rgba, fill), outline)


def label_tile(image: Image.Image, label: str, size: int) -> Image.Image:
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    resized = image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    tile.paste(resized, (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def make_mask_tile(mask: Image.Image) -> Image.Image:
    return Image.merge("RGB", (mask, mask, mask))


def make_panel(
    source: Image.Image,
    mask: Image.Image,
    existing_overlay: Image.Image | None,
    generated_output: Image.Image | None,
    crop: tuple[int, int, int, int],
    out_path: Path,
) -> None:
    tile_size = 360
    source_overlay = make_source_overlay(source, mask)
    tiles = [
        label_tile(source.crop(crop), "source crop", tile_size),
        label_tile(source_overlay.crop(crop), "source + mask edge", tile_size),
        label_tile(make_mask_tile(mask).crop(crop), "mask only", tile_size),
    ]
    if existing_overlay is not None:
        tiles.append(label_tile(existing_overlay.crop(crop), "existing overlay", tile_size))
    if generated_output is not None:
        tiles.append(label_tile(generated_output.crop(crop), "generated output crop", tile_size))
    panel = Image.new("RGB", (len(tiles) * tile_size, tile_size + 34), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * tile_size, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)


def extract_generated_output_path(record: dict[str, Any]) -> str | None:
    proof = record.get("generated_output_proof")
    if isinstance(proof, dict):
        generated = proof.get("generated_output")
        if isinstance(generated, str):
            return generated
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    parser.add_argument("--source-image", default=SOURCE_IMAGE)
    args = parser.parse_args()

    root = args.project_root
    source_path = resolve_rel(root, args.source_image)
    if source_path is None or not source_path.exists():
        raise FileNotFoundError(f"source image not found: {args.source_image}")
    source = Image.open(source_path).convert("RGB")

    audit_dir = root / "runtime_artifacts" / "mask_factory" / f"wave70_alignment_audit_{RUN_STAMP}"
    qa_out = root / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70" / f"W70_MASK_ALIGNMENT_FAIL_CLOSED_AUDIT_{RUN_STAMP}.json"
    tracker_out = root / "Plan" / "Tracker" / "Evidence" / f"W70_MASK_ALIGNMENT_FAIL_CLOSED_AUDIT_{RUN_STAMP}.json"

    audited_masks: list[dict[str, Any]] = []
    for spec in MASK_RECORDS:
        mask_type = spec["mask_type_id"]
        qa_path = root / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70" / f"{mask_type}.json"
        record = load_json(qa_path)
        mask_path = resolve_rel(root, record.get("mask_asset", {}).get("path"))
        overlay_path = resolve_rel(root, record.get("artifacts", {}).get("preview_overlay"))
        generated_path = resolve_rel(root, extract_generated_output_path(record))
        if mask_path is None or not mask_path.exists():
            raise FileNotFoundError(f"mask missing for {mask_type}: {mask_path}")

        mask = Image.open(mask_path).convert("L")
        overlay = Image.open(overlay_path).convert("RGB") if overlay_path and overlay_path.exists() else None
        generated = Image.open(generated_path).convert("RGB") if generated_path and generated_path.exists() else None
        crop = fit_crop_to_square(mask_bbox(mask, margin=72), source.width, source.height)
        panel_path = audit_dir / f"{mask_type}_source_mask_alignment_panel.png"
        make_panel(source, mask, overlay, generated, crop, panel_path)

        audited_masks.append(
            {
                "mask_type_id": mask_type,
                "tracker_id": spec["tracker_id"],
                "item_id": spec["item_id"],
                "decision": spec["decision"],
                "corrected_status": spec["corrected_status"],
                "qa_record": rel(qa_path, root),
                "mask_path": rel(mask_path, root),
                "mask_sha256": sha256_file(mask_path),
                "overlay_path": rel(overlay_path, root) if overlay_path and overlay_path.exists() else None,
                "generated_output": rel(generated_path, root) if generated_path and generated_path.exists() else None,
                "audit_panel": rel(panel_path, root),
                "audit_panel_sha256": sha256_file(panel_path),
                "crop_box": {"x_min": crop[0], "y_min": crop[1], "x_max": crop[2] - 1, "y_max": crop[3] - 1},
                "semantic_mask_alignment_pass": False,
                "generated_output_safe_pass": True,
                "completion_allowed_by_mask_alignment": False,
                "fail_closed_reason": (
                    "User disputed all current Wave70 mask alignments as visibly off from the source. "
                    "This audit panel is evidence for repair targeting, not a pass gate."
                ),
            }
        )

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MASK-ALIGNMENT-FAIL-CLOSED-AUDIT-{RUN_STAMP}",
        "timestamp": "2026-07-07T21:15:00-05:00",
        "project_root": str(root),
        "qa_type": "wave70_mask_alignment_fail_closed_source_overlay_panel_audit",
        "implementation_script": rel(Path(__file__).resolve(), root),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "source_image": rel(source_path, root),
        "source_image_sha256": sha256_file(source_path),
        "superseding_user_dispute": DISPUTE_EVIDENCE,
        "audit_directory": rel(audit_dir, root),
        "audited_masks": audited_masks,
        "method": {
            "source_crop_required": True,
            "mask_edge_overlay_required": True,
            "mask_only_crop_required": True,
            "existing_overlay_crop_required_when_available": True,
            "generated_output_crop_included_when_available": True,
            "fail_closed_until_source_geometry_rebuilt": True,
            "generated_output_safety_does_not_prove_alignment": True,
        },
        "result": "fail_closed_user_disputed_wave70_masks_have_audit_panels_pending_source_geometry_rebuild",
        "next_required_action": (
            "Replace hard-coded coordinate masks with a source-aware or manually verified geometry path, "
            "then rerun this audit before any generated-output proof or pass claim."
        ),
    }
    write_json(qa_out, evidence)

    tracker = {
        "schema_version": "1.0",
        "tracker_evidence_id": f"W70_MASK_ALIGNMENT_FAIL_CLOSED_AUDIT_{RUN_STAMP}",
        "created_at": "2026-07-07T21:15:00-05:00",
        "project_root": str(root),
        "source_evidence": rel(qa_out, root),
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "status": "Wave70 disputed mask alignment audit panels generated; pass promotion remains blocked.",
        "affected_tracker_ids": [item["tracker_id"] for item in audited_masks],
        "affected_item_ids": [item["item_id"] for item in audited_masks],
        "audit_panels": [{"mask_type_id": item["mask_type_id"], "path": item["audit_panel"], "sha256": item["audit_panel_sha256"]} for item in audited_masks],
        "result": "tracker_evidence_wave70_fail_closed_alignment_audit_panels_created",
    }
    write_json(tracker_out, tracker)

    print(
        json.dumps(
            {
                "result": evidence["result"],
                "qa_evidence": rel(qa_out, root),
                "tracker_evidence": rel(tracker_out, root),
                "audit_directory": rel(audit_dir, root),
                "panel_count": len(audited_masks),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
