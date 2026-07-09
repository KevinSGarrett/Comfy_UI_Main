#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT_DEFAULT = Path(r"C:\Comfy_UI_Main")
SOURCE_IMAGE_REL = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)


TARGET_RULES: dict[str, dict[str, Any]] = {
    "mf70_cheeks_skin": {
        "target_definition": "visible cheek-skin regions only; excludes nose, mouth, eyes, brows, hair, jaw/neck",
        "allowed_bbox": [215, 325, 535, 475],
        "min_area": 3000,
        "max_area": 36000,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["eyes_full", "mouth_lips", "nose_core", "hair_left"],
    },
    "mf70_expression_region": {
        "target_definition": "compound expression regions must be split or explicitly bounded; broad face shortcut polygons fail closed",
        "allowed_bbox": [220, 265, 535, 485],
        "min_area": 4000,
        "max_area": 56000,
        "max_outside_allowed_ratio": 0.10,
        "forbidden": ["hair_left", "hair_right", "neck_collar", "background_right"],
        "must_fail_reason": "broad expression-region masks require subpart decomposition before row promotion",
    },
    "mf70_eyebrows": {
        "target_definition": "visible eyebrow hair bands only; excludes eyelids, forehead slabs, hair, eyes",
        "allowed_bbox": [215, 268, 540, 306],
        "min_area": 500,
        "max_area": 3600,
        "max_outside_allowed_ratio": 0.05,
        "forbidden": ["eyes_full", "forehead_center"],
    },
    "mf70_eyelashes": {
        "target_definition": "visible lash-line strokes only; excludes eyelid skin and eye aperture",
        "allowed_bbox": [230, 300, 515, 350],
        "min_area": 150,
        "max_area": 2200,
        "max_outside_allowed_ratio": 0.12,
        "forbidden": ["brows_band", "nose_core", "mouth_lips"],
        "must_fail_reason": "lash-line masks require per-eye zoom and strand/lid boundary proof before promotion",
    },
    "mf70_eyelids": {
        "target_definition": "thin upper and lower eyelid bands only; excludes eye aperture, eyebrows, broad orbital skin, nose",
        "allowed_bbox": [276, 304, 508, 351],
        "allowed_zone": "eyelids_allowed_visible_bands",
        "min_area": 250,
        "max_area": 2600,
        "max_outside_allowed_ratio": 0.06,
        "forbidden": [
            "viewer_left_eye_aperture_poly",
            "viewer_right_eye_aperture_poly",
            "viewer_left_brow_poly",
            "viewer_right_brow_poly",
            "viewer_left_hair_occlusion_poly",
            "nose_bridge_poly",
        ],
    },
    "mf70_eyes_full": {
        "target_definition": "visible full eye regions only; excludes broad orbital skin and eyebrows",
        "allowed_bbox": [235, 292, 515, 352],
        "min_area": 1400,
        "max_area": 7400,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["brows_band", "nose_core", "mouth_lips"],
    },
    "mf70_face_full_instance": {
        "target_definition": "visible face skin instance; excludes hair, background, neck, collar",
        "allowed_bbox": [205, 168, 535, 548],
        "min_area": 36000,
        "max_area": 100000,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["hair_left", "hair_right", "neck_collar", "background_right"],
        "must_fail_reason": "full-face instance requires source contour trace and hair/neck protected-boundary proof",
    },
    "mf70_face_identity_critical": {
        "target_definition": "identity-critical visible face zones; excludes hair/background and must not be a broad shortcut polygon",
        "allowed_bbox": [205, 168, 535, 542],
        "min_area": 20000,
        "max_area": 92000,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["hair_left", "hair_right", "neck_collar", "background_right"],
        "must_fail_reason": "identity-critical region must be decomposed or source-contour-traced before promotion",
    },
    "mf70_forehead_skin": {
        "target_definition": "visible forehead skin between hairline and brows only",
        "allowed_bbox": [250, 178, 505, 295],
        "min_area": 2800,
        "max_area": 22000,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["brows_band", "hair_top", "eyes_full"],
    },
    "mf70_jawline_chin": {
        "target_definition": "visible jawline and chin skin contour only; excludes neck/collar and mouth",
        "allowed_bbox": [250, 438, 500, 560],
        "min_area": 1200,
        "max_area": 15000,
        "max_outside_allowed_ratio": 0.10,
        "forbidden": ["mouth_lips", "neck_collar"],
    },
    "mf70_left_eye": {
        "target_definition": "source subject left eye / viewer-right visible eye region only",
        "allowed_bbox": [405, 292, 518, 350],
        "min_area": 500,
        "max_area": 4600,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["brows_right", "nose_core"],
    },
    "mf70_mouth_lips": {
        "target_definition": "visible upper and lower lip surfaces; excludes philtrum, teeth, chin, cheeks",
        "allowed_bbox": [290, 430, 455, 488],
        "min_area": 650,
        "max_area": 5200,
        "max_outside_allowed_ratio": 0.06,
        "forbidden": ["nose_core", "teeth_inner", "chin_skin"],
        "must_fail_reason": "current mouth/lips mask is not proven as full-region mouth/lip coverage by row-level zoom proof",
    },
    "mf70_nose": {
        "target_definition": "visible nose bridge, sidewalls, tip, alae, nostrils; excludes philtrum and lips",
        "allowed_bbox": [330, 270, 455, 430],
        "min_area": 1800,
        "max_area": 10500,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["mouth_lips", "upper_lip_philtrum", "viewer_left_eye_aperture", "viewer_right_eye_aperture"],
    },
    "mf70_pupils_iris_sclera": {
        "target_definition": "visible eye apertures containing pupil/iris/sclera per eye; excludes skin bands between eyes",
        "allowed_bbox": [245, 306, 515, 335],
        "min_area": 500,
        "max_area": 3500,
        "max_outside_allowed_ratio": 0.05,
        "forbidden": ["between_eyes_bridge", "brows_band"],
        "must_fail_reason": "must be separated into per-eye apertures; a cross-face strip fails closed",
    },
    "mf70_right_eye": {
        "target_definition": "source subject right eye / viewer-left visible eye region only",
        "allowed_bbox": [235, 292, 355, 352],
        "min_area": 400,
        "max_area": 4600,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["brows_left", "hair_left"],
    },
    "mf70_skin_tone_continuity": {
        "target_definition": "explicit skin-tone continuity zones; broad whole-face/neck shortcuts fail closed",
        "allowed_bbox": [205, 175, 535, 540],
        "min_area": 10000,
        "max_area": 95000,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["hair_left", "hair_right", "neck_collar", "background_right"],
        "must_fail_reason": "skin-tone continuity requires subregion definitions and protected hair/neck exclusion proof",
    },
    "mf70_teeth": {
        "target_definition": "visible teeth enamel strip only; excludes lips, tongue, inner mouth, skin",
        "allowed_bbox": [334, 456, 405, 469],
        "min_area": 35,
        "max_area": 700,
        "max_outside_allowed_ratio": 0.12,
        "forbidden": ["upper_lip_philtrum", "lip_surfaces"],
        "must_fail_reason": "teeth mask requires row-level zoom proof; full contact sheet is insufficient for promotion",
    },
    "mf70_under_eye": {
        "target_definition": "under-eye skin/tear-trough zones below lower lids; excludes eye apertures, nose bridge, broad cheek band",
        "allowed_bbox": [235, 328, 515, 376],
        "min_area": 500,
        "max_area": 5200,
        "max_outside_allowed_ratio": 0.08,
        "forbidden": ["eye_apertures", "nose_core", "mouth_lips"],
    },
}


PROTECTED_ZONES: dict[str, list[int]] = {
    "background_right": [545, 150, 768, 620],
    "between_eyes_bridge": [335, 300, 418, 336],
    "brows_band": [215, 270, 542, 308],
    "brows_left": [215, 270, 335, 308],
    "brows_right": [405, 270, 542, 308],
    "chin_skin": [285, 488, 470, 545],
    "eye_apertures": [245, 306, 515, 336],
    "eyes_full": [235, 292, 515, 356],
    "forehead_center": [260, 180, 505, 286],
    "hair_left": [0, 150, 245, 550],
    "hair_right": [520, 125, 768, 575],
    "hair_top": [170, 0, 565, 205],
    "lip_surfaces": [292, 436, 452, 484],
    "mouth_lips": [290, 430, 455, 488],
    "neck_collar": [220, 535, 565, 768],
    "nose_core": [330, 270, 455, 430],
    "teeth_inner": [330, 454, 410, 470],
    "upper_lip_philtrum": [315, 410, 430, 458],
    "viewer_left_eye_aperture": [245, 306, 333, 337],
    "viewer_right_eye_aperture": [420, 306, 515, 337],
}

POLYGON_ZONES: dict[str, list[list[tuple[int, int]]]] = {
    "eyelids_allowed_visible_bands": [
        # Viewer-left visible eyelid bands, avoiding the hair-heavy outer corner.
        [(276, 305), (303, 305), (326, 311), (321, 316), (286, 313), (276, 311)],
        [(276, 337), (287, 344), (316, 341), (326, 336), (321, 348), (286, 351), (276, 344)],
        # Viewer-right visible eyelid bands.
        [(426, 305), (454, 303), (485, 304), (508, 311), (501, 316), (464, 313), (429, 315)],
        [(428, 337), (459, 345), (490, 342), (506, 336), (500, 348), (462, 351), (429, 344)],
    ],
    "viewer_left_eye_aperture_poly": [
        [(247, 318), (261, 309), (292, 308), (322, 316), (328, 324), (313, 335), (281, 335), (257, 329)],
    ],
    "viewer_right_eye_aperture_poly": [
        [(424, 318), (449, 309), (483, 309), (505, 316), (511, 324), (491, 335), (456, 335), (429, 329)],
    ],
    "viewer_left_brow_poly": [
        [(213, 286), (247, 274), (310, 275), (337, 289), (323, 298), (267, 292), (222, 299)],
    ],
    "viewer_right_brow_poly": [
        [(406, 284), (454, 272), (515, 278), (548, 294), (529, 302), (465, 293), (416, 296)],
    ],
    "viewer_left_hair_occlusion_poly": [
        [(190, 252), (236, 264), (268, 297), (279, 342), (254, 374), (208, 379), (178, 340), (170, 286)],
    ],
    "nose_bridge_poly": [
        [(346, 284), (410, 284), (424, 430), (338, 430)],
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def mask_label(path: Path) -> str:
    return path.stem.replace("wave70_", "").replace("_mask", "")


def rect_area(rect: list[int]) -> int:
    return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])


def rect_intersection(a: list[int], b: list[int]) -> list[int] | None:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


def expand_rect(rect: list[int], margin: int, width: int, height: int) -> list[int]:
    return [
        max(0, rect[0] - margin),
        max(0, rect[1] - margin),
        min(width, rect[2] + margin),
        min(height, rect[3] + margin),
    ]


def square_crop(rect: list[int], width: int, height: int, margin: int = 72) -> list[int]:
    expanded = expand_rect(rect, margin, width, height)
    side = max(expanded[2] - expanded[0], expanded[3] - expanded[1], 180)
    cx = (expanded[0] + expanded[2]) // 2
    cy = (expanded[1] + expanded[3]) // 2
    left = max(0, cx - side // 2)
    top = max(0, cy - side // 2)
    right = min(width, left + side)
    bottom = min(height, top + side)
    left = max(0, right - side)
    top = max(0, bottom - side)
    return [left, top, right, bottom]


def count_nonzero(mask: Image.Image) -> int:
    return sum(1 for value in mask.getdata() if value > 0)


def count_inside_rect(mask: Image.Image, rect: list[int]) -> int:
    cropped = mask.crop(tuple(rect))
    return count_nonzero(cropped)


def zone_mask(size: tuple[int, int], zone_name: str) -> Image.Image:
    out = Image.new("L", size, 0)
    draw = ImageDraw.Draw(out)
    if zone_name in POLYGON_ZONES:
        for polygon in POLYGON_ZONES[zone_name]:
            draw.polygon(polygon, fill=255)
        return out
    rect = PROTECTED_ZONES[zone_name]
    draw.rectangle(rect, fill=255)
    return out


def allowed_geometry_mask(size: tuple[int, int], rule: dict[str, Any]) -> Image.Image:
    out = Image.new("L", size, 0)
    draw = ImageDraw.Draw(out)
    allowed_zone = rule.get("allowed_zone")
    if allowed_zone in POLYGON_ZONES:
        for polygon in POLYGON_ZONES[allowed_zone]:
            draw.polygon(polygon, fill=255)
    else:
        draw.rectangle(rule["allowed_bbox"], fill=255)
    return out


def count_inside_zone(mask: Image.Image, zone_name: str) -> int:
    zone = zone_mask(mask.size, zone_name)
    return count_nonzero(Image.composite(mask, Image.new("L", mask.size, 0), zone))


def zone_bbox(zone_name: str) -> list[int]:
    if zone_name in POLYGON_ZONES:
        xs: list[int] = []
        ys: list[int] = []
        for polygon in POLYGON_ZONES[zone_name]:
            for x, y in polygon:
                xs.append(x)
                ys.append(y)
        return [min(xs), min(ys), max(xs), max(ys)]
    return PROTECTED_ZONES[zone_name]


def mask_bbox(mask: Image.Image) -> list[int] | None:
    bbox = mask.point(lambda value: 255 if value > 8 else 0).getbbox()
    return list(bbox) if bbox else None


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", source.size, (255, 0, 0, 0))
    fill.putalpha(mask.point(lambda value: 130 if value > 8 else 0))
    return Image.alpha_composite(rgba, fill).convert("RGB")


def draw_rule_overlay(source: Image.Image, rule: dict[str, Any]) -> Image.Image:
    out = source.copy()
    draw = ImageDraw.Draw(out)
    if rule.get("allowed_zone") in POLYGON_ZONES:
        for polygon in POLYGON_ZONES[rule["allowed_zone"]]:
            draw.line(polygon + [polygon[0]], fill=(0, 255, 0), width=4)
    else:
        allowed = rule["allowed_bbox"]
        draw.rectangle(allowed, outline=(0, 255, 0), width=4)
    for zone_name in rule.get("forbidden", []):
        if zone_name in POLYGON_ZONES:
            for polygon in POLYGON_ZONES[zone_name]:
                draw.line(polygon + [polygon[0]], fill=(255, 200, 0), width=3)
        else:
            zone = PROTECTED_ZONES[zone_name]
            draw.rectangle(zone, outline=(255, 200, 0), width=3)
    return out


def label_tile(image: Image.Image, label: str, size: int = 310) -> Image.Image:
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    tile = Image.new("RGB", (size, size + 30), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 30))
    draw = ImageDraw.Draw(tile)
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def make_panel(
    source: Image.Image,
    mask: Image.Image,
    rule: dict[str, Any],
    crop: list[int],
    out_path: Path,
) -> None:
    overlay = make_overlay(source, mask)
    rule_overlay = draw_rule_overlay(overlay, rule)
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(tuple(crop)), "source crop"),
        label_tile(mask_rgb.crop(tuple(crop)), "mask only"),
        label_tile(overlay.crop(tuple(crop)), "source + mask"),
        label_tile(rule_overlay.crop(tuple(crop)), "green allowed / amber protected"),
    ]
    panel = Image.new("RGB", (len(tiles) * tiles[0].width, tiles[0].height), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * tile.width, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out_path)


def evaluate_mask(mask_type_id: str, mask_path: Path, source: Image.Image, out_dir: Path, root: Path) -> dict[str, Any]:
    rule = TARGET_RULES[mask_type_id]
    mask = Image.open(mask_path).convert("L").point(lambda value: 255 if value > 8 else 0)
    total = count_nonzero(mask)
    bbox = mask_bbox(mask)
    findings: list[str] = []
    geometry_findings: list[str] = [
        "geometry_gate_blocked_current_allowed_protected_overlays_are_debug_not_canonical",
        "coordinate_transform_manifest_missing_or_unproven",
    ]
    protected_hits: dict[str, int] = {}
    geometry_conflicts: dict[str, int] = {}

    if not rule.get("allowed_zone"):
        geometry_findings.append("allowed_geometry_rectangular_debug_only_not_source_boundary")
    rectangular_forbidden = [zone_name for zone_name in rule.get("forbidden", []) if zone_name not in POLYGON_ZONES]
    if rectangular_forbidden:
        geometry_findings.append(
            "protected_geometry_rectangular_debug_only_not_source_boundary:" + ",".join(rectangular_forbidden)
        )

    allowed_geom = allowed_geometry_mask(mask.size, rule)
    empty = Image.new("L", mask.size, 0)
    for zone_name in rule.get("forbidden", []):
        zone = zone_mask(mask.size, zone_name)
        overlap = count_nonzero(Image.composite(allowed_geom, empty, zone))
        if overlap > 0:
            geometry_conflicts[zone_name] = overlap
    if geometry_conflicts:
        geometry_findings.append("green_allowed_amber_protected_overlap_conflict")

    if total == 0 or bbox is None:
        findings.append("empty_mask")
        bbox = [0, 0, source.width, source.height]

    inside_allowed = count_inside_zone(mask, rule["allowed_zone"]) if rule.get("allowed_zone") else count_inside_rect(mask, rule["allowed_bbox"])
    outside_allowed = max(0, total - inside_allowed)
    outside_ratio = outside_allowed / total if total else 1.0

    if total < int(rule["min_area"]):
        findings.append(f"area_too_small:{total}<min:{rule['min_area']}")
    if total > int(rule["max_area"]):
        findings.append(f"area_too_large:{total}>max:{rule['max_area']}")
    if outside_ratio > float(rule["max_outside_allowed_ratio"]):
        findings.append(
            f"outside_allowed_region_ratio_too_high:{outside_ratio:.4f}>max:{rule['max_outside_allowed_ratio']}"
        )

    bbox_allowed_intersection = rect_intersection(bbox, rule["allowed_bbox"])
    bbox_inside_allowed_ratio = (
        rect_area(bbox_allowed_intersection) / rect_area(bbox) if bbox_allowed_intersection else 0.0
    )
    if bbox_inside_allowed_ratio < 0.65:
        findings.append(f"bbox_not_source_target_aligned:{bbox_inside_allowed_ratio:.4f}<0.65")

    for zone_name in rule.get("forbidden", []):
        hit = count_inside_zone(mask, zone_name)
        if hit > max(15, math.ceil(total * 0.02)):
            protected_hits[zone_name] = hit
            findings.append(f"protected_zone_overlap:{zone_name}:{hit}")

    if rule.get("must_fail_reason"):
        findings.append(rule["must_fail_reason"])

    findings.extend(geometry_findings)
    findings.append("unresolved_user_global_mask_alignment_dispute_requires_row_level_zoom_proof")

    decision = "fail_closed_source_alignment_not_promotable" if findings else "needs_manual_review_no_promotion"
    panel_path = out_dir / f"{mask_type_id}_source_alignment_fail_closed_panel.png"
    crop_source = bbox if bbox else rule["allowed_bbox"]
    crop = square_crop(
        [
            min(crop_source[0], rule["allowed_bbox"][0]),
            min(crop_source[1], rule["allowed_bbox"][1]),
            max(crop_source[2], rule["allowed_bbox"][2]),
            max(crop_source[3], rule["allowed_bbox"][3]),
        ],
        source.width,
        source.height,
    )
    make_panel(source, mask, rule, crop, panel_path)

    return {
        "mask_type_id": mask_type_id,
        "mask_path": rel(mask_path, root),
        "mask_sha256": sha256_file(mask_path),
        "target_definition": rule["target_definition"],
        "allowed_bbox": rule["allowed_bbox"],
        "protected_zones_checked": rule.get("forbidden", []),
        "mask_bbox": bbox,
        "mask_pixels": total,
        "inside_allowed_pixels": inside_allowed,
        "outside_allowed_pixels": outside_allowed,
        "outside_allowed_ratio": round(outside_ratio, 6),
        "bbox_inside_allowed_ratio": round(bbox_inside_allowed_ratio, 6),
        "protected_zone_hits": protected_hits,
        "geometry_gate": {
            "result": "fail",
            "wave70_mask_geometry_gate_pass": False,
            "approval_token": "",
            "source_dimensions": [source.width, source.height],
            "mask_dimensions": [mask.width, mask.height],
            "crop_rect_full_image_xyxy": crop,
            "coordinate_transform_manifest_pass": False,
            "allowed_geometry_source_derived_pass": False,
            "protected_geometry_source_derived_pass": False,
            "green_amber_conflict_pass": len(geometry_conflicts) == 0,
            "debug_rectangle_only": bool((not rule.get("allowed_zone")) or rectangular_forbidden),
            "panel_readable_pass": True,
            "geometry_conflicts": geometry_conflicts,
            "findings": geometry_findings,
            "required_protocol": "Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md",
        },
        "findings": findings,
        "decision": decision,
        "promotion_decision": "blocked_no_wave70_mask_promotion_row_gate_pass_true",
        "panel": rel(panel_path, root),
        "panel_sha256": sha256_file(panel_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT_DEFAULT)
    parser.add_argument("--stamp", default="20260707T223600-0500")
    args = parser.parse_args()

    root = args.project_root
    source_path = root / SOURCE_IMAGE_REL
    source = Image.open(source_path).convert("RGB")
    input_dir = root / "ComfyUI/input"
    out_dir = root / "runtime_artifacts/mask_factory" / f"wave70_source_alignment_fail_closed_{args.stamp}"

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for mask_type_id in sorted(TARGET_RULES):
        mask_path = input_dir / f"wave70_{mask_type_id}_mask.png"
        if not mask_path.exists():
            missing.append(mask_type_id)
            continue
        records.append(evaluate_mask(mask_type_id, mask_path, source, out_dir, root))

    failing_records = [record for record in records if record["decision"].startswith("fail_closed")]
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_SOURCE_ALIGNMENT_FAIL_CLOSED_VALIDATION_{args.stamp}",
        "timestamp_local": args.stamp,
        "project_root": str(root),
        "source_image": rel(source_path, root),
        "source_sha256": sha256_file(source_path),
        "validator": "Plan/07_IMPLEMENTATION/scripts/validate_wave70_source_alignment_fail_closed.py",
        "qa_type": "wave70_source_alignment_fail_closed_validator",
        "result": "fail_closed_current_masks_not_promotable",
        "mask_count": len(records),
        "missing_mask_count": len(missing),
        "failing_mask_count": len(failing_records),
        "missing_masks": missing,
        "user_dispute_state": "unresolved_global_mask_alignment_dispute",
        "promotion_policy": "No row may be promoted without exact W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE evidence and no unresolved user visual dispute.",
        "generated_output_policy": "Generated-output stability is output-geometry evidence only; it is not source-alignment proof.",
        "records": records,
    }
    qa_path = root / (
        "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
        f"W70_SOURCE_ALIGNMENT_FAIL_CLOSED_VALIDATION_{args.stamp}.json"
    )
    tracker_path = root / (
        "Plan/Tracker/Evidence/"
        f"W70_SOURCE_ALIGNMENT_FAIL_CLOSED_VALIDATION_{args.stamp}.json"
    )
    write_json(qa_path, payload)
    write_json(tracker_path, payload)
    print(qa_path)
    print(tracker_path)
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
