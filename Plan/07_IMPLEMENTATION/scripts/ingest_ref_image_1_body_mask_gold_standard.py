from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REF_ROOT = PROJECT_ROOT / "Ref_Image_1"
MAIN_REFERENCE = REF_ROOT / "725de85824bbe45ba4601dd4a7aed698.jpg"

NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_REF_IMAGE_1_BODY_MASK_GOLD_STANDARD_{RUN_STAMP}"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/ref_image_1_body_mask_gold_standard" / RUN_STAMP
MASK_DIR = RUNTIME_DIR / "extracted_binary_masks"
PREVIEW_DIR = RUNTIME_DIR / "mask_previews"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/ingest_ref_image_1_body_mask_gold_standard.py"

MASK_TYPE_MAP = {
    "abdomen_belly_button": ["mf70_belly_button_umbilicus"],
    "abdomen_stomach": ["mf70_abdomen", "mf70_stomach"],
    "arms_left_lower_arm": ["mf70_left_forearm"],
    "arms_left_upper_arm": ["mf70_left_upper_arm"],
    "arms_lower_arm_fore_arms": ["mf70_left_forearm", "mf70_right_forearm", "mf70_forearms"],
    "arms_right_lower_arm": ["mf70_right_forearm"],
    "arms_right_upper_arm": ["mf70_right_upper_arm"],
    "arms_upper_arms": ["mf70_left_upper_arm", "mf70_right_upper_arm", "mf70_upper_arms"],
    "breasts_both": ["mf70_breasts", "mf70_left_breast", "mf70_right_breast"],
    "breasts_left_breast": ["mf70_left_breast"],
    "breasts_right": ["mf70_right_breast"],
    "calves_both_calves": ["mf70_left_calf", "mf70_right_calf", "mf70_calves"],
    "calves_left_calf": ["mf70_left_calf"],
    "calves_right_calf": ["mf70_right_calf"],
    "feet_both_feet": ["mf70_left_foot", "mf70_right_foot", "mf70_feet"],
    "feet_left_foot": ["mf70_left_foot"],
    "feet_right_foot": ["mf70_right_foot"],
    "feet_toes_feet": ["mf70_toes", "mf70_feet"],
    "glute_both": ["mf70_left_glute", "mf70_right_glute", "mf70_glutes"],
    "glute_left": ["mf70_left_glute"],
    "glute_right": ["mf70_right_glute"],
    "hair_hair": ["mf70_hair"],
    "hands_both_hands": ["mf70_left_hand", "mf70_right_hand", "mf70_hands"],
    "hands_index_fingers": ["mf70_index_fingers"],
    "hands_left_hand": ["mf70_left_hand"],
    "hands_middle_fingers": ["mf70_middle_fingers"],
    "hands_pinkys": ["mf70_pinkies"],
    "hands_right_hand": ["mf70_right_hand"],
    "hands_ring_finger": ["mf70_ring_fingers"],
    "hands_thumbs": ["mf70_thumbs"],
    "pelvic_pelvic_region": ["mf70_pelvic_region"],
    "thigh_both_thighs": ["mf70_left_thigh", "mf70_right_thigh", "mf70_thighs"],
    "thigh_left_thigh": ["mf70_left_thigh"],
    "thigh_right_thigh": ["mf70_right_thigh"],
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


def slug(path: Path) -> str:
    rel_parts = path.relative_to(REF_ROOT).parts[:-1]
    raw = "_".join(rel_parts)
    raw = raw.replace("-", " ")
    raw = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return raw


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def extract_red_overlay_mask(image_path: Path, label: str) -> dict[str, object]:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    pixels = image.load()
    mask = Image.new("L", (width, height), 0)
    mask_pixels = mask.load()
    count = 0

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            is_overlay_red = r >= 170 and g <= 125 and b <= 120 and (r - g) >= 75 and (r - b) >= 75
            if is_overlay_red:
                mask_pixels[x, y] = 255
                count += 1

    mask_path = MASK_DIR / f"{label}.png"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(mask_path)

    preview = image.copy()
    preview_pixels = preview.load()
    for y in range(height):
        for x in range(width):
            if mask_pixels[x, y]:
                r, g, b = preview_pixels[x, y]
                preview_pixels[x, y] = (min(255, int(r * 0.45) + 140), int(g * 0.45), int(b * 0.45))

    preview_path = PREVIEW_DIR / f"{label}_preview.png"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(preview_path)

    return {
        "source_overlay_path": rel(image_path),
        "source_overlay_sha256": sha256_file(image_path),
        "label": label,
        "dimensions": [width, height],
        "binary_mask_path": rel(mask_path),
        "binary_mask_sha256": sha256_file(mask_path),
        "preview_path": rel(preview_path),
        "preview_sha256": sha256_file(preview_path),
        "red_overlay_pixel_count": count,
        "red_overlay_coverage_ratio": round(count / float(width * height), 6),
        "mask_type_candidates": MASK_TYPE_MAP.get(label, []),
        "gold_standard_use": "user_provided_visual_body_part_mask_reference",
        "binary_mask_extraction_rule": "red overlay threshold: r>=170, g<=125, b<=120, r-g>=75, r-b>=75",
    }


def prepend_section(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8")


def update_hydration(evidence_paths: list[str], part_count: int, mask_count: int) -> None:
    evidence_block = "\n".join(f"- `{p}`" for p in evidence_paths)
    body = f"""A new user-provided multi-pose character body reference set was ingested from `Ref_Image_1`. The main reference image contains the same character rotated through multiple poses, and the subfolders contain labeled red-overlay body-part gold references. Extracted binary masks were created from the red overlays for local Wave70 body-mask validation.

Reference set summary:

- Main reference: `Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg`
- Layout: the top strip is partial upper-body/one-third-body pose reference and is not expected to contain all body-part masks; the lower strip is the full-body pose/mask reference area and is the primary body-part validation region.
- Part overlay files discovered: `{part_count}`
- Extracted binary masks with nonzero red-overlay pixels: `{mask_count}`
- Use: body-mask gold standard/reference matrix evidence for the character, especially body/limb/hand/glute/breast/abdomen/thigh/calf/foot/hair rows.
- Constraint: these gold references are authoritative for the provided multi-pose reference set; target-image promotion still requires row-level source/route evidence and Wave70 hard gates.
- Correction note: this is the canonical corrected extraction pass using the stricter red-overlay threshold, so it supersedes any earlier loose-threshold extraction from the same reference set.

Evidence:

{evidence_block}

Next local action: re-evaluate active Wave70 body rows against this `Ref_Image_1` gold-standard manifest before writing any further body-part not-visible blockers."""
    prepend_section(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Ref_Image_1 Body Mask Gold Standard Ingested - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Ref_Image_1 Body Mask Gold Standard Ingested - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Re-evaluate Wave70 Body Rows With Ref_Image_1 Gold Standard",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Ref_Image_1 Body Mask Gold Standard Evidence - {ISO_STAMP}",
        body,
    )
    prepend_section(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Ref_Image_1 Body Mask Gold Standard Available - {ISO_STAMP}",
        body,
    )

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        import csv

        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 Ref_Image_1 body mask gold standard ingest",
                f"Ingested user-provided multi-pose body reference set, discovered {part_count} labeled overlays, extracted {mask_count} binary red-overlay masks, and wrote manifest evidence for Wave70 body-mask validation.",
                "; ".join(evidence_paths),
                "filesystem validation; image dimension/hash validation; red-overlay binary mask extraction; manifest JSON validation pending",
                "REF_IMAGE_1_BODY_MASK_GOLD_STANDARD_INGESTED",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
                "Re-evaluate Wave70 body rows using Ref_Image_1 gold-standard evidence before additional body not-visible blockers.",
            ]
        )


def main() -> int:
    if not MAIN_REFERENCE.exists():
        raise FileNotFoundError(MAIN_REFERENCE)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    copied_reference = RUNTIME_DIR / MAIN_REFERENCE.name
    shutil.copy2(MAIN_REFERENCE, copied_reference)

    main_image = Image.open(MAIN_REFERENCE).convert("RGB")
    overlay_files = [
        path
        for path in sorted(REF_ROOT.rglob("*.png"))
        if path.is_file() and path.relative_to(REF_ROOT).parts[0] not in {"chest", "clothes", "Face"}
    ]

    extracted = []
    missing_map_labels = []
    for path in overlay_files:
        label = slug(path)
        if label not in MASK_TYPE_MAP:
            missing_map_labels.append(label)
        record = extract_red_overlay_mask(path, label)
        extracted.append(record)

    nonzero = [record for record in extracted if record["red_overlay_pixel_count"] > 0]

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "project_root": str(PROJECT_ROOT),
        "reference_root": rel(REF_ROOT),
        "main_reference": {
            "path": rel(MAIN_REFERENCE),
            "runtime_copy": rel(copied_reference),
            "sha256": sha256_file(MAIN_REFERENCE),
            "dimensions": [main_image.size[0], main_image.size[1]],
            "description": "User-provided single-character multi-pose body reference image.",
        },
        "gold_standard_scope": {
            "user_asserted_purpose": "gold standard for body masking of this character across multiple poses",
            "layout_interpretation": {
                "top_strip": {
                    "description": "partial upper-body / one-third-body pose reference strip",
                    "expected_body_part_completeness": "partial",
                    "absence_of_lower_body_masks_means": "not_applicable_to_top_strip_not_a_mask_failure",
                },
                "lower_strip": {
                    "description": "full-body pose strip with body-part mask overlays",
                    "expected_body_part_completeness": "primary_full_body_mask_reference_area",
                    "use_for_full_body_validation": True,
                },
                "validation_rule": "Do not mark a body part missing because it is absent from the top partial-body strip; evaluate full body-part coverage primarily against the lower full-body strip and the labeled part overlay files.",
            },
            "applies_to": [
                "body-region masks",
                "limb masks",
                "hands and fingers",
                "glutes",
                "breasts and breast skin",
                "abdomen and belly button",
                "thighs",
                "calves",
                "feet and toes",
                "hair",
            ],
            "does_not_by_itself_prove": [
                "target runtime generated-output stability",
                "non-reference image source visibility",
                "promotion of unrelated target images without row-level evidence",
            ],
        },
        "overlay_file_count": len(overlay_files),
        "extracted_nonzero_mask_count": len(nonzero),
        "missing_mask_type_map_labels": sorted(set(missing_map_labels)),
        "extracted_masks": extracted,
        "mask_type_index": {},
        "qa_decision": "ref_image_1_body_mask_gold_standard_ingested",
        "next_step": "Re-evaluate Wave70 body mask rows using Ref_Image_1 gold-standard evidence before additional body not-visible blockers.",
    }

    mask_type_index: dict[str, list[str]] = {}
    for record in extracted:
        for mask_type in record["mask_type_candidates"]:
            mask_type_index.setdefault(mask_type, []).append(record["binary_mask_path"])
    payload["mask_type_index"] = mask_type_index

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "ref_image_1_body_mask_gold_standard.json"
    runtime_manifest_path = RUNTIME_DIR / "ref_image_1_body_mask_gold_standard.json"

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_manifest_path]:
        write_json(path, payload)

    evidence_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_manifest_path),
    ]
    update_hydration(evidence_paths, len(overlay_files), len(nonzero))

    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "overlay_file_count": len(overlay_files),
                "extracted_nonzero_mask_count": len(nonzero),
                "canonical_evidence": rel(qa_canonical_path),
                "runtime_manifest": rel(runtime_manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
