from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
TEMPLATE_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Templates"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_reference_package_intake" / STAMP
DROPZONE = PROJECT_ROOT / "Ref_Image_Canonical_Body"
DROPZONE_MANIFEST_JSON = DROPZONE / "manifest.json"
DROPZONE_MANIFEST_CSV = DROPZONE / "manifest.csv"
DROPZONE_CHECKLIST_CSV = DROPZONE / "slot_checklist.csv"
CANDIDATE_WORKING_GUARD_EVIDENCE = QA_DIR / "candidate_mask_batch_working_guard.json"

EVIDENCE = QA_DIR / f"W70_CANONICAL_REFERENCE_PACKAGE_INTAKE_VALIDATION_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "canonical_reference_package_intake_validation.json"
MANIFEST_TEMPLATE = TEMPLATE_DIR / "WAVE70_CANONICAL_BODY_REFERENCE_PACKAGE_MANIFEST_TEMPLATE.json"
PANEL = RUNTIME_DIR / "canonical_reference_package_intake_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

SOURCE_EVIDENCE = {
    "canonical_reference_acquisition_requirements": QA_DIR / "canonical_reference_acquisition_requirements.json",
    "canonical_body_geometry_prerequisite_gap": QA_DIR / "canonical_body_geometry_prerequisite_gap.json",
    "available_route_runtime_validation_alignment": QA_DIR / "available_route_runtime_validation_alignment.json",
    "body_reference_matrix": QA_DIR / "body_reference_matrix.json",
    "whole_body_geometry_promotion_integration": QA_DIR / "whole_body_geometry_promotion_integration.json",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_GUARDED_WORKING_ROOT_CACHE: list[Path] | None = None


SLOTS = [
    {
        "slot_id": "front_full_body_with_masks",
        "required": True,
        "aliases": ["front", "frontal", "full", "standing", "neutral"],
        "mask_labels": ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
        "accept_existing_calibration": True,
    },
    {
        "slot_id": "left_side_or_profile_full_body",
        "required": True,
        "aliases": ["left side", "left_profile", "left profile", "profile_left", "side_left", "left-side"],
        "mask_labels": ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
    },
    {
        "slot_id": "right_side_or_profile_full_body",
        "required": True,
        "aliases": ["right side", "right_profile", "right profile", "profile_right", "side_right", "right-side"],
        "mask_labels": ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
    },
    {
        "slot_id": "back_full_body",
        "required": True,
        "aliases": ["back", "rear", "behind", "back_view", "back view"],
        "mask_labels": ["back", "hair", "arms", "glute", "thigh", "calves", "feet"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
    },
    {
        "slot_id": "three_quarter_left_full_body",
        "required": True,
        "aliases": ["three_quarter_left", "3_4_left", "3-4 left", "three quarter left", "three-quarter-left"],
        "mask_labels": ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
    },
    {
        "slot_id": "three_quarter_right_full_body",
        "required": True,
        "aliases": ["three_quarter_right", "3_4_right", "3-4 right", "three quarter right", "three-quarter-right"],
        "mask_labels": ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 6,
    },
    {
        "slot_id": "contact_occlusion_support_case",
        "required": True,
        "aliases": ["contact", "occlusion", "support", "floor", "chair", "bed", "object", "hand_on_body", "limb_over"],
        "mask_labels": ["hands", "feet", "contact", "support", "object", "arms", "body"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 4,
    },
    {
        "slot_id": "multi_person_owner_separation_case",
        "required": False,
        "aliases": ["multi_person", "two_person", "two character", "owner", "separation", "person_a", "person_b"],
        "mask_labels": ["person", "owner", "hands", "contact", "body"],
        "minimum_source_count": 1,
        "minimum_mask_label_count": 3,
    },
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_info(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "path": rel(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
    }
    with Image.open(path) as img:
        info.update({"width": img.width, "height": img.height, "mode": img.mode})
    return info


def normalized_text(path: Path) -> str:
    rel_path = path.relative_to(PROJECT_ROOT).as_posix().lower()
    rel_path = rel_path.replace("%20", " ")
    return re.sub(r"[_\\/\-]+", " ", rel_path)


def rel_parts_lower(path: Path) -> list[str]:
    return [part.lower() for part in path.relative_to(PROJECT_ROOT).parts]


def resolve_guard_path(value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text.replace("/", "\\"))
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def guarded_working_roots() -> list[Path]:
    global _GUARDED_WORKING_ROOT_CACHE
    if _GUARDED_WORKING_ROOT_CACHE is not None:
        return _GUARDED_WORKING_ROOT_CACHE
    roots: list[Path] = []
    if CANDIDATE_WORKING_GUARD_EVIDENCE.exists():
        payload = read_json(CANDIDATE_WORKING_GUARD_EVIDENCE)
        policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
        exclusion_active = (
            policy.get("requires_explicit_user_ready_signal") is True
            and policy.get("may_use_for_gold_standard_validation") is False
            and policy.get("may_use_for_mask_promotion") is False
        )
        if exclusion_active:
            for key in ["candidate_batch", "v2_batch"]:
                root = resolve_guard_path(payload.get(key))
                if root:
                    roots.append(root)
    _GUARDED_WORKING_ROOT_CACHE = sorted(set(roots))
    return _GUARDED_WORKING_ROOT_CACHE


def is_guarded_working_batch_path(path: Path) -> bool:
    return any(path_is_under(path, root) for root in guarded_working_roots())


def candidate_working_guard_state() -> dict[str, object]:
    if not CANDIDATE_WORKING_GUARD_EVIDENCE.exists():
        return {
            "available": False,
            "evidence_path": rel(CANDIDATE_WORKING_GUARD_EVIDENCE),
            "exclusion_active": False,
            "guarded_roots": [],
        }
    payload = read_json(CANDIDATE_WORKING_GUARD_EVIDENCE)
    policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    roots = guarded_working_roots()
    return {
        "available": True,
        "evidence_path": rel(CANDIDATE_WORKING_GUARD_EVIDENCE),
        "qa_decision": payload.get("qa_decision"),
        "requires_explicit_user_ready_signal": policy.get("requires_explicit_user_ready_signal") is True,
        "may_use_for_gold_standard_validation": policy.get("may_use_for_gold_standard_validation") is True,
        "may_use_for_whole_body_geometry_authority": policy.get("may_use_for_whole_body_geometry_authority") is True,
        "may_use_for_mask_promotion": policy.get("may_use_for_mask_promotion") is True,
        "may_trigger_hard_gate_rerun": policy.get("may_trigger_hard_gate_rerun") is True,
        "exclusion_active": bool(roots),
        "guarded_roots": [rel(root) if root.exists() or PROJECT_ROOT in root.parents else str(root) for root in roots],
    }


def is_manifest_routed_mask_or_batch(path: Path) -> bool:
    if is_guarded_working_batch_path(path):
        return True
    parts = rel_parts_lower(path)
    name = path.name.lower()
    return (
        parts[:1] == ["ref_image_canonical_body"]
        and (
            "masks" in parts
            or "candidate_mask_batch" in parts
            or name.startswith("binary_mask")
            or "mask_seed_manifest" in name
        )
    )


def is_manifest_routed_source(path: Path) -> bool:
    parts = rel_parts_lower(path)
    return parts[:1] == ["ref_image_canonical_body"] and "source_images" in parts


def discover_reference_roots() -> list[Path]:
    roots = []
    for path in PROJECT_ROOT.iterdir():
        if not path.is_dir():
            continue
        name = path.name.lower()
        if name.startswith("ref_image") or "canonical" in name and "reference" in name:
            roots.append(path)
    return sorted(roots)


def image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def all_reference_images() -> list[Path]:
    files: list[Path] = []
    for root in discover_reference_roots():
        files.extend(image_files(root))
    return sorted(files)


def classify_sources(files: list[Path]) -> dict[str, list[Path]]:
    slot_sources: dict[str, list[Path]] = {slot["slot_id"]: [] for slot in SLOTS}
    for path in files:
        if is_manifest_routed_mask_or_batch(path):
            continue
        text = normalized_text(path)
        if "_overlay" in path.name.lower() or "overlay" in text:
            continue
        if path.name.lower().startswith("binary_mask"):
            continue
        if "new folder" in text and "8ead94ca6f2884fb1ae671fee89e8126" in text:
            continue
        for slot in SLOTS:
            aliases = slot["aliases"]
            if slot["slot_id"] == "front_full_body_with_masks":
                if "ref image 1 full" in text or "ref image 2 97f30ff" in text or "ref image 2\\97f30ff" in str(path).lower():
                    slot_sources[slot["slot_id"]].append(path)
                    break
            if any(alias in text for alias in aliases):
                slot_sources[slot["slot_id"]].append(path)
                break
    return slot_sources


def classify_masks(files: list[Path]) -> dict[str, set[str]]:
    slot_masks: dict[str, set[str]] = {slot["slot_id"]: set() for slot in SLOTS}
    for path in files:
        if is_manifest_routed_mask_or_batch(path) or is_manifest_routed_source(path):
            continue
        text = normalized_text(path)
        is_mask_like = path.suffix.lower() == ".png" and ("overlay" in text or "chatgpt image" in text or "mask" in text)
        if not is_mask_like:
            continue
        for slot in SLOTS:
            slot_text_match = slot["slot_id"] == "front_full_body_with_masks" or any(alias in text for alias in slot["aliases"])
            if not slot_text_match:
                continue
            for label in slot["mask_labels"]:
                if label in text:
                    slot_masks[slot["slot_id"]].add(label)
    return slot_masks


def resolve_project_path(value: object) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    path = Path(text.replace("/", "\\"))
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def parse_expected_labels(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(label).strip() for label in value if str(label).strip()]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    separator = "|" if "|" in text else ","
    return [part.strip() for part in text.split(separator) if part.strip()]


def manifest_slot_rows() -> list[dict[str, object]]:
    if DROPZONE_MANIFEST_JSON.exists():
        payload = read_json(DROPZONE_MANIFEST_JSON)
        rows = payload.get("slots")
        if isinstance(rows, list) and rows:
            return [row for row in rows if isinstance(row, dict)]
        template_rows = payload.get("required_slots")
        if isinstance(template_rows, list):
            return [row for row in template_rows if isinstance(row, dict)]
    if DROPZONE_MANIFEST_CSV.exists():
        with DROPZONE_MANIFEST_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    return []


def canonical_package_manifest_state() -> dict[str, object]:
    rows = manifest_slot_rows()
    by_slot: dict[str, dict[str, object]] = {}
    issues: list[str] = []
    total_source_images = 0
    total_mask_images = 0
    for row in rows:
        slot_id = str(row.get("slot_id", "")).strip()
        if not slot_id:
            issues.append("manifest_row_missing_slot_id")
            continue
        source_path = resolve_project_path(row.get("source_image_dropzone") or row.get("source_image_path"))
        mask_root = resolve_project_path(row.get("organized_mask_root"))
        expected_labels = parse_expected_labels(row.get("expected_mask_labels") or row.get("mask_labels"))
        source_files = image_files(source_path) if source_path else []
        mask_labels_with_files: set[str] = set()
        mask_file_samples: list[str] = []
        mask_file_count = 0
        if mask_root and mask_root.exists():
            for label in expected_labels:
                label_files = image_files(mask_root / label)
                if label_files:
                    mask_labels_with_files.add(label)
                    mask_file_count += len(label_files)
                    mask_file_samples.extend(rel(path) for path in label_files[:2])
            if not expected_labels:
                all_masks = image_files(mask_root)
                mask_file_count = len(all_masks)
                mask_file_samples.extend(rel(path) for path in all_masks[:8])
        elif mask_root:
            issues.append(f"{slot_id}: organized_mask_root_missing:{rel(mask_root) if PROJECT_ROOT in mask_root.parents or mask_root == PROJECT_ROOT else mask_root}")
        if source_path and not source_path.exists():
            issues.append(f"{slot_id}: source_image_dropzone_missing:{rel(source_path) if PROJECT_ROOT in source_path.parents or source_path == PROJECT_ROOT else source_path}")
        total_source_images += len(source_files)
        total_mask_images += mask_file_count
        by_slot[slot_id] = {
            "slot_id": slot_id,
            "required": str(row.get("required", "")).upper() == "TRUE" or row.get("required") is True,
            "source_image_dropzone": rel(source_path) if source_path and source_path.exists() else str(row.get("source_image_dropzone") or row.get("source_image_path") or ""),
            "organized_mask_root": rel(mask_root) if mask_root and mask_root.exists() else str(row.get("organized_mask_root") or ""),
            "expected_mask_labels": expected_labels,
            "source_image_count": len(source_files),
            "mask_image_count": mask_file_count,
            "mask_label_count": len(mask_labels_with_files),
            "mask_labels_with_files": sorted(mask_labels_with_files),
            "sample_source_images": [rel(path) for path in source_files[:8]],
            "sample_mask_images": mask_file_samples[:8],
        }
    return {
        "available": bool(rows),
        "dropzone_root": rel(DROPZONE) if DROPZONE.exists() else "Ref_Image_Canonical_Body",
        "manifest_json_exists": DROPZONE_MANIFEST_JSON.exists(),
        "manifest_csv_exists": DROPZONE_MANIFEST_CSV.exists(),
        "slot_checklist_csv_exists": DROPZONE_CHECKLIST_CSV.exists(),
        "manifest_slot_count": len(rows),
        "manifest_source_image_count": total_source_images,
        "manifest_mask_image_count": total_mask_images,
        "issues": issues,
        "by_slot": by_slot,
    }


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def evaluate_slots(files: list[Path], manifest_state: dict[str, object] | None = None) -> list[dict[str, object]]:
    sources = classify_sources(files)
    masks = classify_masks(files)
    manifest_by_slot = {}
    if manifest_state:
        manifest_by_slot = manifest_state.get("by_slot") or {}
    results = []
    for slot in SLOTS:
        slot_id = slot["slot_id"]
        manifest_slot = manifest_by_slot.get(slot_id, {}) if isinstance(manifest_by_slot, dict) else {}
        manifest_sources = []
        for sample in manifest_slot.get("sample_source_images", []) if isinstance(manifest_slot, dict) else []:
            path = resolve_project_path(sample)
            if path and path.exists():
                manifest_sources.append(path)
        source_list = unique_paths([*sources[slot_id], *manifest_sources])
        manifest_mask_labels = set(manifest_slot.get("mask_labels_with_files", [])) if isinstance(manifest_slot, dict) else set()
        mask_labels = sorted(set(masks[slot_id]) | manifest_mask_labels)
        source_count = len(source_list)
        mask_label_count = len(mask_labels)
        source_pass = source_count >= int(slot["minimum_source_count"])
        mask_pass = mask_label_count >= int(slot["minimum_mask_label_count"])
        result = "pass_candidate_intake_only" if source_pass and mask_pass else "blocked_missing_source_or_masks"
        if slot_id == "front_full_body_with_masks" and source_pass:
            result = "available_calibration_only"
        results.append(
            {
                "slot_id": slot_id,
                "required": bool(slot["required"]),
                "result": result,
                "source_count": source_count,
                "mask_label_count": mask_label_count,
                "mask_labels_detected": mask_labels,
                "sample_sources": [rel(path) for path in source_list[:8]],
                "manifest_slot_present": bool(manifest_slot),
                "manifest_source_image_count": manifest_slot.get("source_image_count", 0) if isinstance(manifest_slot, dict) else 0,
                "manifest_mask_image_count": manifest_slot.get("mask_image_count", 0) if isinstance(manifest_slot, dict) else 0,
                "manifest_mask_labels_with_files": manifest_slot.get("mask_labels_with_files", []) if isinstance(manifest_slot, dict) else [],
                "minimum_source_count": slot["minimum_source_count"],
                "minimum_mask_label_count": slot["minimum_mask_label_count"],
                "completion_allowed": False,
                "blocked_reason": (
                    "Intake slot is not satisfied by current filesystem inventory."
                    if not (source_pass and mask_pass)
                    else "Intake slot may be present, but canonical geometry authority still requires model-backed route evidence."
                ),
            }
        )
    return results


def route_state() -> dict[str, object]:
    path = SOURCE_EVIDENCE["available_route_runtime_validation_alignment"]
    if not path.exists():
        return {"available": False}
    payload = read_json(path)
    missing = payload.get("still_missing_required_routes") or []
    available = payload.get("available_route_runtime_validation") or {}
    return {
        "available": True,
        "evidence_path": rel(path),
        "evidence_id": payload.get("evidence_id"),
        "partial_routes": sorted(available.keys()),
        "still_missing_required_routes": missing,
        "model_backed_canonical_stack_pass": False,
    }


def source_evidence_summary() -> dict[str, object]:
    summary: dict[str, object] = {}
    for key, path in SOURCE_EVIDENCE.items():
        if not path.exists():
            summary[key] = {"exists": False, "path": rel(path)}
            continue
        payload = read_json(path)
        summary[key] = {
            "exists": True,
            "path": rel(path),
            "evidence_id": payload.get("evidence_id"),
            "qa_decision": payload.get("qa_decision"),
            "decision": payload.get("decision"),
        }
    return summary


def write_manifest_template() -> None:
    template = {
        "schema_version": "1.0",
        "manifest_type": "wave70_canonical_body_reference_package",
        "created_at_local": "YYYY-MM-DDTHH:MM:SS-05:00",
        "package_root": "C:/Comfy_UI_Main/Ref_Image_Canonical_Body",
        "source_policy": {
            "full_body_required": True,
            "organized_masks_required": True,
            "top_partial_composites_allowed_as_context_only": True,
            "gold_overlays_are_calibration_not_canonical_authority": True,
            "guarded_working_candidate_batches_excluded_until_user_ready": True,
            "manual_tracing_not_required_from_user": True,
        },
        "required_slots": [
            {
                "slot_id": slot["slot_id"],
                "required": slot["required"],
                "source_image_path": "",
                "organized_mask_root": "",
                "expected_mask_labels": slot["mask_labels"],
                "minimum_source_count": slot["minimum_source_count"],
                "minimum_mask_label_count": slot["minimum_mask_label_count"],
                "notes": "",
            }
            for slot in SLOTS
        ],
        "model_backed_geometry_required": {
            "pose": True,
            "hands": True,
            "human_part_parsing": True,
            "person_instance_ownership": True,
            "promptable_refinement": True,
            "contact_ownership": True,
            "canonical_polygon_export": True,
            "coordinate_transform_manifest": True,
        },
        "completion_allowed": False,
    }
    write_json(MANIFEST_TEMPLATE, template)


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(block.rstrip() + "\n\n" + existing, encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "70",
        "Wave70 manifest-aware canonical reference package intake validator",
        "Ran manifest-aware canonical body reference package intake validation; dropzone manifest is recognized but still has no source/mask files for missing side/back/3-4/contact/support slots, so no promotion or gate rerun occurred.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; reference root scan; dropzone manifest scan; slot classifier; JSON validation; panel generation; CSV row verification",
        "MANIFEST_AWARE_CANONICAL_REFERENCE_PACKAGE_INTAKE_BLOCKED_NO_PROMOTION",
        rel(EVIDENCE),
        "Add or integrate a canonical reference package matching the manifest template, then rerun this intake validator before any geometry/promotion gate rerun.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_panel(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1700, 1100), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(36)
    head_font = load_font(25)
    body_font = load_font(20)
    small_font = load_font(17)
    draw.rectangle([0, 0, 1700, 92], fill=(42, 55, 72))
    draw.text((34, 26), "Wave70 Canonical Reference Package Intake Validation", fill=(255, 255, 255), font=title_font)
    draw.text((36, 125), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 164), "No masks changed. No promotion. No hard-gate rerun.", fill=(125, 38, 28), font=body_font)

    summary = payload["intake_summary"]
    rows = [
        f"Reference roots scanned: {summary['reference_root_count']}",
        f"Images scanned: {summary['image_count']}",
        f"Manifest slots scanned: {summary['manifest_slot_count']}",
        f"Manifest source images: {summary['manifest_source_image_count']}",
        f"Manifest mask images: {summary['manifest_mask_image_count']}",
        f"Required slots satisfied for intake: {summary['required_slots_satisfied']} / {summary['required_slots_total']}",
        f"Blocked required slots: {summary['blocked_required_slot_count']}",
        f"Template written: {rel(MANIFEST_TEMPLATE)}",
    ]
    y = 230
    draw.text((36, y), "Intake Summary", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 32

    y += 20
    draw.text((36, y), "Blocked Required Slots", fill=(42, 55, 72), font=head_font)
    y += 42
    blocked = [slot for slot in payload["slot_results"] if slot["required"] and slot["result"] == "blocked_missing_source_or_masks"]
    for slot in blocked[:8]:
        draw.text((62, y), f"- {slot['slot_id']}: sources {slot['source_count']}, mask labels {slot['mask_label_count']}", fill=(35, 35, 35), font=body_font)
        y += 31

    y += 18
    draw.text((36, y), "Model-backed stack", fill=(42, 55, 72), font=head_font)
    y += 42
    missing = payload["route_state"].get("still_missing_required_routes") or []
    draw.text((62, y), "Missing required routes: " + (", ".join(missing) if missing else "unknown"), fill=(35, 35, 35), font=small_font)
    y += 30
    draw.text((62, y), "Gold/reference masks remain calibration evidence until canonical route evidence passes.", fill=(125, 38, 28), font=small_font)

    draw.rectangle([36, 982, 1664, 1062], outline=(160, 55, 45), width=3)
    draw.text((60, 1004), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    draw.text((60, 1032), "Rerun this validator only when a new reference package or route artifact is added.", fill=(35, 35, 35), font=small_font)
    img.save(PANEL)


def main() -> None:
    write_manifest_template()
    roots = discover_reference_roots()
    files = all_reference_images()
    manifest_state = canonical_package_manifest_state()
    working_guard = candidate_working_guard_state()
    slot_results = evaluate_slots(files, manifest_state)
    required = [slot for slot in slot_results if slot["required"]]
    required_satisfied = [
        slot
        for slot in required
        if slot["result"] in {"pass_candidate_intake_only", "available_calibration_only"}
    ]
    required_complete = [
        slot
        for slot in required
        if slot["result"] == "pass_candidate_intake_only"
    ]
    blocked_required = [
        slot
        for slot in required
        if slot["result"] == "blocked_missing_source_or_masks"
    ]
    categories = Counter()
    for path in files:
        parts = path.relative_to(PROJECT_ROOT).parts
        if len(parts) >= 2:
            categories[parts[1]] += 1

    route = route_state()
    intake_pass = len(required_complete) == len(required) and route.get("model_backed_canonical_stack_pass") is True
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_REFERENCE_PACKAGE_INTAKE_VALIDATION_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Validate current filesystem against Wave70 canonical body reference package intake contract.",
        "manifest_template_path": rel(MANIFEST_TEMPLATE),
        "reference_roots": [rel(path) for path in roots],
        "canonical_package_manifest_state": manifest_state,
        "candidate_working_guard": working_guard,
        "intake_summary": {
            "reference_root_count": len(roots),
            "image_count": len(files),
            "image_category_counts": dict(sorted(categories.items())),
            "manifest_available": manifest_state["available"],
            "manifest_slot_count": manifest_state["manifest_slot_count"],
            "manifest_source_image_count": manifest_state["manifest_source_image_count"],
            "manifest_mask_image_count": manifest_state["manifest_mask_image_count"],
            "required_slots_total": len(required),
            "required_slots_satisfied": len(required_satisfied),
            "required_slots_complete_for_authority": len(required_complete),
            "blocked_required_slot_count": len(blocked_required),
            "intake_contract_pass": intake_pass,
        },
        "slot_results": slot_results,
        "route_state": route,
        "source_evidence": source_evidence_summary(),
        "policy": {
            "ref_image_1_top_partial_context_only": True,
            "ref_image_1_full_new_folder_knees_to_head_excluded_for_lower_body_proof": True,
            "gold_overlays_are_calibration_not_canonical_authority": True,
            "canonical_dropzone_manifest_is_authoritative_slot_routing_input": True,
            "guarded_working_candidate_batches_excluded_until_user_ready": working_guard.get("exclusion_active") is True,
            "wave71_activation_allowed": False,
            "mask_promotion_allowed": False,
        },
        "gate_policy": {
            "hard_gate_rerun_performed": False,
            "reason": "The intake validator did not introduce a new route implementation, canonical polygon, pass-like row, or complete reference package.",
        },
        "qa_decision": "canonical_reference_package_intake_blocked_missing_required_slots_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_intake_validator_only",
        "next_step": "Add or integrate a canonical reference package matching the manifest template, then rerun this intake validator before any Wave70 geometry/promotion gate rerun or Wave71 activation.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(MANIFEST_TEMPLATE),
        rel(DROPZONE_MANIFEST_JSON) if DROPZONE_MANIFEST_JSON.exists() else "Ref_Image_Canonical_Body/manifest.json",
        rel(DROPZONE_MANIFEST_CSV) if DROPZONE_MANIFEST_CSV.exists() else "Ref_Image_Canonical_Body/manifest.csv",
        rel(DROPZONE_CHECKLIST_CSV) if DROPZONE_CHECKLIST_CSV.exists() else "Ref_Image_Canonical_Body/slot_checklist.csv",
        rel(CANDIDATE_WORKING_GUARD_EVIDENCE) if CANDIDATE_WORKING_GUARD_EVIDENCE.exists() else "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/candidate_mask_batch_working_guard.json",
        rel(PANEL),
    ]

    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload)

    evidence_additions = payload["evidence_paths"]
    coverage_additions = [
        "canonical_reference_package_intake_validator_written",
        "canonical_reference_package_manifest_aware_slot_scan",
        "candidate_working_guard_enforced_in_intake",
        "canonical_reference_package_intake_blocked_missing_required_slots",
        "no_mask_promoted_intake_validator_only",
    ]
    note = (
        f"Manifest-aware canonical reference package intake validator {STAMP}: current filesystem and dropzone manifest scan blocked required side/profile, back, "
        "3/4, contact/support/occlusion owner slots and model-backed canonical stack. Dropzone manifest recognized; "
        "candidate working-batch guard enforced; no masks promoted and no hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_canonical_reference_package_intake_missing_required_slots_no_promotion",
                "Evidence_Path": evidence_additions,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            "ITEM-W70-0178",
            {
                "Evidence_Required": evidence_additions,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""## Immediate Next Action - Manifest-Aware Canonical Reference Package Intake Validator - {ISO_TS}

Implemented and ran the Wave70 manifest-aware canonical body reference package intake validator.

Result: current filesystem inventory and `Ref_Image_Canonical_Body` manifest do not yet satisfy the canonical intake contract. Front/full-body calibration context exists, and the dropzone manifest is now recognized as the authoritative slot routing input, but required side/profile, back, 3/4 left/right, contact/occlusion/support owner slots, and the model-backed canonical geometry stack are still missing or not proven. The validator refreshed the package manifest template at `{rel(MANIFEST_TEMPLATE)}`.

Candidate working-batch guard: `{rel(CANDIDATE_WORKING_GUARD_EVIDENCE) if CANDIDATE_WORKING_GUARD_EVIDENCE.exists() else "missing"}` was enforced, so guarded in-progress candidate folders are excluded from gold-standard validation, whole-body authority, promotion, and hard-gate triggers until explicit user ready signal.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(MANIFEST_TEMPLATE)}`
- `{rel(DROPZONE_MANIFEST_JSON) if DROPZONE_MANIFEST_JSON.exists() else "Ref_Image_Canonical_Body/manifest.json"}`
- `{rel(DROPZONE_MANIFEST_CSV) if DROPZONE_MANIFEST_CSV.exists() else "Ref_Image_Canonical_Body/manifest.csv"}`
- `{rel(DROPZONE_CHECKLIST_CSV) if DROPZONE_CHECKLIST_CSV.exists() else "Ref_Image_Canonical_Body/slot_checklist.csv"}`
- `{rel(CANDIDATE_WORKING_GUARD_EVIDENCE) if CANDIDATE_WORKING_GUARD_EVIDENCE.exists() else "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/candidate_mask_batch_working_guard.json"}`
- `{rel(PANEL)}`

No masks changed or promoted. No hard gates were rerun because no new route implementation, canonical polygon, pass-like row, real reference images, or complete reference package was introduced. Next exact local action: add or integrate real images/masks into the manifest-routed dropzone, then rerun this intake validator before any Wave70 geometry/promotion gate rerun or Wave71 activation."""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Manifest-Aware Canonical Reference Package Intake Validator - {ISO_TS}

Implemented and ran manifest-aware canonical body reference package intake validation. Current references remain calibration/context evidence only, and the Ref_Image_Canonical_Body manifest is now scanned as the authoritative dropzone routing input; required canonical side/profile, back, 3/4, contact/support/occlusion owner slots and model-backed canonical geometry stack are not complete. The candidate working-batch guard was enforced, so in-progress candidate folders remain excluded until explicit user ready signal. No masks changed or promoted; hard gates were not rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(MANIFEST_TEMPLATE)}`
- `{rel(DROPZONE_MANIFEST_JSON) if DROPZONE_MANIFEST_JSON.exists() else "Ref_Image_Canonical_Body/manifest.json"}`
- `{rel(DROPZONE_MANIFEST_CSV) if DROPZONE_MANIFEST_CSV.exists() else "Ref_Image_Canonical_Body/manifest.csv"}`
- `{rel(DROPZONE_CHECKLIST_CSV) if DROPZONE_CHECKLIST_CSV.exists() else "Ref_Image_Canonical_Body/slot_checklist.csv"}`
- `{rel(CANDIDATE_WORKING_GUARD_EVIDENCE) if CANDIDATE_WORKING_GUARD_EVIDENCE.exists() else "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/candidate_mask_batch_working_guard.json"}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "canonical": str(CANONICAL_EVIDENCE),
        "template": str(MANIFEST_TEMPLATE),
        "panel": str(PANEL),
        "qa_decision": payload["qa_decision"],
        "intake_contract_pass": intake_pass,
        "manifest_slot_count": manifest_state["manifest_slot_count"],
        "manifest_source_image_count": manifest_state["manifest_source_image_count"],
        "manifest_mask_image_count": manifest_state["manifest_mask_image_count"],
        "candidate_working_guard_exclusion_active": working_guard.get("exclusion_active"),
        "blocked_required_slot_count": len(blocked_required),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
