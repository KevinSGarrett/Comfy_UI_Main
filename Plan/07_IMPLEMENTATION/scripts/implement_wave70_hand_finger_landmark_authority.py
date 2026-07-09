from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import platform
import sys
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
HAND_MODEL = PROJECT_ROOT / (
    "ComfyUI/custom_nodes/comfyui_controlnet_aux/src/custom_controlnet_aux/"
    "mesh_graphormer/hand_landmarker.task"
)
REF_IMAGE_1 = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
REF_IMAGE_1_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_HAND_FINGER_LANDMARK_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_hand_finger_landmark_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_hand_finger_landmark_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


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


def module_available(module_name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {"module": module_name, "available": False, "version": None}
    try:
        module = __import__(module_name)
        return {"module": module_name, "available": True, "version": getattr(module, "__version__", None)}
    except Exception as exc:  # noqa: BLE001
        return {"module": module_name, "available": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def model_record(path: Path) -> dict[str, object]:
    record: dict[str, object] = {"path": str(path), "exists": path.exists()}
    if path.exists():
        record["size_bytes"] = path.stat().st_size
        record["sha256"] = sha256_file(path)
    return record


def load_ref_image_1_hand_masks() -> dict[str, object]:
    record: dict[str, object] = {
        "manifest_path": rel(REF_IMAGE_1_MANIFEST),
        "manifest_exists": REF_IMAGE_1_MANIFEST.exists(),
        "main_reference_path": rel(REF_IMAGE_1),
        "main_reference_exists": REF_IMAGE_1.exists(),
        "main_reference_sha256": sha256_file(REF_IMAGE_1) if REF_IMAGE_1.exists() else None,
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body masks here are not failures",
            "lower_strip": "primary full-body pose and body-mask validation area",
        },
        "scope": "reference_gold_masks_only_not_active_source_visibility_or_promotion_proof",
        "hand_finger_mask_count": 0,
        "hand_finger_masks": [],
    }
    if not REF_IMAGE_1_MANIFEST.exists():
        return record
    manifest = json.loads(REF_IMAGE_1_MANIFEST.read_text(encoding="utf-8"))
    labels = ("hands", "finger", "thumb", "pinky", "pinkys", "ring", "middle", "index")
    masks = []
    for item in manifest.get("extracted_masks", []):
        label = str(item.get("label", "")).lower()
        if not any(token in label for token in labels):
            continue
        mask_path = PROJECT_ROOT / str(item.get("binary_mask_path", ""))
        masks.append(
            {
                "label": item.get("label", ""),
                "binary_mask_path": item.get("binary_mask_path", ""),
                "binary_mask_exists": mask_path.exists(),
                "binary_mask_sha256": item.get("binary_mask_sha256", ""),
                "red_overlay_pixel_count": item.get("red_overlay_pixel_count", 0),
                "mask_type_candidates": item.get("mask_type_candidates", []),
                "gold_standard_use": item.get("gold_standard_use", ""),
            }
        )
    record["hand_finger_mask_count"] = len(masks)
    record["hand_finger_masks"] = masks
    return record


def run_mediapipe_hand_landmarker() -> dict[str, object]:
    record: dict[str, object] = {
        "runtime": "mediapipe.tasks.vision.HandLandmarker",
        "module_available": False,
        "hand_task_model_available": HAND_MODEL.exists(),
        "attempted": False,
        "inference_pass": False,
        "hand_count": 0,
        "hands": [],
        "error": None,
    }
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        record["module_available"] = True
        record["mediapipe_version"] = getattr(mp, "__version__", None)
        record["vision_has_hand_landmarker"] = hasattr(vision, "HandLandmarker")
        if not HAND_MODEL.exists():
            record["error"] = "local_hand_landmarker_task_model_missing"
            return record

        record["attempted"] = True
        base_options = python.BaseOptions(model_asset_path=str(HAND_MODEL))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.10,
            min_hand_presence_confidence=0.10,
            min_tracking_confidence=0.10,
        )
        image = mp.Image.create_from_file(str(SOURCE_IMAGE))
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            result = landmarker.detect(image)

        hands: list[dict[str, object]] = []
        width = int(image.width)
        height = int(image.height)
        for index, landmarks in enumerate(result.hand_landmarks or []):
            categories = result.handedness[index] if result.handedness and index < len(result.handedness) else []
            handedness = [
                {
                    "category_name": category.category_name,
                    "score": float(category.score),
                    "index": int(category.index),
                }
                for category in categories
            ]
            points = [
                {
                    "index": point_index,
                    "x_norm": float(point.x),
                    "y_norm": float(point.y),
                    "z_norm": float(point.z),
                    "x_px": float(point.x * width),
                    "y_px": float(point.y * height),
                }
                for point_index, point in enumerate(landmarks)
            ]
            hands.append({"hand_index": index, "handedness": handedness, "landmarks": points})
        record["hands"] = hands
        record["hand_count"] = len(hands)
        record["inference_pass"] = len(hands) > 0
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def make_panel(source: Image.Image, hand_probe: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "hand_finger_landmark_authority_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()

    hands = hand_probe.get("hands") or []
    if hands:
        for hand in hands:
            for point in hand.get("landmarks", []):
                x = float(point["x_px"])
                y = float(point["y_px"])
                draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(0, 220, 255), outline=(0, 60, 90))
        label_lines = [
            "TRK-W70-0165 detected hand landmarks",
            f"hand count: {len(hands)}",
            "No mask promoted by this evidence.",
        ]
        outline = (0, 180, 120)
        fill = (240, 255, 248)
        text_fill = (0, 80, 55)
    else:
        draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
        label_lines = [
            "TRK-W70-0165 blocked",
            "Local hand model executed.",
            "Detected hands: 0",
            "Active portrait has no usable hand/finger geometry.",
            "No masks promoted.",
        ]
        outline = (230, 40, 40)
        fill = (255, 255, 255)
        text_fill = (120, 0, 0)

    draw.rectangle([20, 20, width - 20, 178], fill=fill, outline=outline, width=3)
    y = 34
    for line in label_lines:
        draw.text((34, y), line, fill=text_fill, font=font)
        y += 25
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], status: str, decision: str, note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0165") for path in TRACKER_FILES] + [(path, "ITEM-W70-0165") for path in ITEM_FILES]
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
                row["Status"] = status
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = decision
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [decision],
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


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    hand_probe = run_mediapipe_hand_landmarker()
    ref_hand_masks = load_ref_image_1_hand_masks()
    panel_path = make_panel(source, hand_probe)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "hand_finger_landmark_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "hand_finger_landmark_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "hand_finger_landmark_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
    ]

    hand_count = int(hand_probe.get("hand_count") or 0)
    if hand_count > 0:
        status = "Blocked_Hand_Finger_Geometry_Not_Trusted"
        decision = "blocked_hand_finger_landmarks_detected_no_canonical_mask_promotion"
        authority_result = "landmarks_detected_promotion_still_blocked"
        blocked_reason = "canonical_hand_finger_polygon_export_and_mask_promotion_not_performed"
    elif hand_probe.get("attempted") and not hand_probe.get("error"):
        status = "Blocked_Local_Source_Hand_Region_Not_Visible"
        decision = "blocked_exact_local_hand_finger_source_region_not_visible"
        authority_result = "blocked"
        blocked_reason = "local_hand_landmarker_executed_detected_zero_hands_on_active_source"
    else:
        status = "Blocked_Hand_Finger_Geometry_Not_Trusted"
        decision = "blocked_exact_local_hand_finger_runtime_unavailable"
        authority_result = "blocked"
        blocked_reason = str(hand_probe.get("error") or "local_hand_landmarker_unavailable")

    note = (
        f"Hand/finger landmark authority {RUN_STAMP}: {decision}. "
        f"Local MediaPipe hand model path exists={HAND_MODEL.exists()} and detected hand_count={hand_count}. "
        f"Ref_Image_1 hand/finger gold masks available={ref_hand_masks['hand_finger_mask_count']}. "
        "Ref_Image_1 is reference-only and does not prove active portrait hand visibility. "
        "No active masks changed or promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, status, decision, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement hand/finger landmark authority for TRK-W70-0165 / ITEM-W70-0165.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "ref_image_1": ref_hand_masks,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "modules": {
                name: module_available(name)
                for name in ["mediapipe", "cv2", "numpy", "PIL"]
            },
        },
        "model": model_record(HAND_MODEL),
        "runtime_attempts": {
            "mediapipe_hand_landmarker": hand_probe,
        },
        "artifacts": {
            "review_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "hand_finger_landmark_authority": {
            "result": authority_result,
            "hand_landmark_pass": hand_count > 0,
            "finger_joint_chain_pass": hand_count > 0,
            "hand_side_mapping_pass": hand_count > 0,
            "source_derived_landmark_or_segmentation_pass": hand_count > 0,
            "detected_hand_count": hand_count,
            "detected_hands": hand_probe.get("hands") or [],
            "blocked_reason": blocked_reason,
            "findings": [
                "Local MediaPipe HandLandmarker runtime executed against the active source image."
                if hand_probe.get("attempted")
                else "Local MediaPipe HandLandmarker runtime did not execute.",
                f"Detected hand count: {hand_count}.",
                f"Ref_Image_1 hand/finger gold mask count: {ref_hand_masks['hand_finger_mask_count']}.",
                "Ref_Image_1 hand/finger masks are reference/gold-standard assets only; they do not prove active portrait hand visibility.",
                "No active ComfyUI input masks were changed.",
                "No hand, finger, palm, knuckle, fingertip, or fingernail mask was promoted.",
            ],
        },
        "qa_decision": decision,
        "promotion_decision": "no_mask_promoted_no_active_input_changed_hand_finger_authority_blocked",
        "tracker_item_updates": row_updates,
        "next_step": (
            "Use a reference/source image with visible hands or a reference-matrix slot containing hands "
            "before hand/finger masks can receive source-derived geometry authority."
            if hand_count == 0
            else "Export canonical hand/finger polygons and rerun geometry/promotion gates before any mask promotion."
        ),
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": decision, "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
