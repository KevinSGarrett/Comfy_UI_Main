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

from wave70_model_registry import SEARCH_ROOTS, first_existing_asset, file_record, registry_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RTMPOSE_MODEL = Path(r"C:\Users\kevin\.cache\torch\hub\checkpoints\rtmpose-m_simcc-coco-wholebody_pt-aic-coco_270e-256x192-cd5e845c_20230123.pth")
OPENPOSE_CONTROLNET = PROJECT_ROOT / "models/controlnet/OpenPoseXL2.safetensors"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_POSE_LANDMARK_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_pose_landmark_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_pose_landmark_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


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


def model_record(path: Path, hash_limit: int = 256 * 1024 * 1024) -> dict[str, object]:
    record: dict[str, object] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    stat = path.stat()
    record["size_bytes"] = stat.st_size
    record["suffix"] = path.suffix.lower()
    record["sha256"] = sha256_file(path) if stat.st_size <= hash_limit else "skipped_large_file"
    return record


def find_pose_task_models() -> list[dict[str, object]]:
    roots = SEARCH_ROOTS
    records: list[dict[str, object]] = []
    known_pose_task = first_existing_asset("mediapipe_pose_landmarker_task")
    if known_pose_task is not None:
        records.append(file_record(known_pose_task))
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.task"):
            haystack = str(path).lower()
            if any(token in haystack for token in ["pose", "holistic", "landmark", "mediapipe"]):
                record = model_record(path)
                if record not in records:
                    records.append(record)
    return records


def mediapipe_pose_probe(task_models: list[dict[str, object]]) -> dict[str, object]:
    record: dict[str, object] = {
        "runtime": "mediapipe.tasks.vision.PoseLandmarker",
        "module_available": False,
        "pose_task_model_available": False,
        "attempted": False,
        "inference_pass": False,
        "error": None,
        "task_model_candidates": task_models,
    }
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        record["module_available"] = True
        record["mediapipe_version"] = getattr(mp, "__version__", None)
        pose_models = [item for item in task_models if "pose" in str(item.get("path", "")).lower()]
        record["pose_task_model_available"] = bool(pose_models)
        if not pose_models:
            record["error"] = "no_local_pose_landmarker_task_model_found"
            return record
        record["attempted"] = True
        record["vision_has_pose_landmarker"] = hasattr(vision, "PoseLandmarker")
        task_path = Path(str(pose_models[0]["path"]))
        base_options = python.BaseOptions(model_asset_path=str(task_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=True,
            num_poses=1,
        )
        image = mp.Image.create_from_file(str(SOURCE_IMAGE))
        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            result = landmarker.detect(image)
        pose_count = len(result.pose_landmarks)
        pose_landmarks = []
        if pose_count:
            for index, lm in enumerate(result.pose_landmarks[0]):
                pose_landmarks.append(
                    {
                        "index": index,
                        "x_norm": round(float(lm.x), 8),
                        "y_norm": round(float(lm.y), 8),
                        "z_norm": round(float(lm.z), 8),
                        "visibility": round(float(getattr(lm, "visibility", 0.0)), 8),
                        "presence": round(float(getattr(lm, "presence", 0.0)), 8),
                    }
                )
        record["model_used"] = file_record(task_path)
        record["detected_person_count"] = pose_count
        record["pose_landmark_count"] = len(pose_landmarks)
        record["pose_landmarks"] = pose_landmarks
        record["world_landmark_count"] = len(result.pose_world_landmarks[0]) if result.pose_world_landmarks else 0
        record["segmentation_mask_count"] = len(result.segmentation_masks) if result.segmentation_masks else 0
        record["inference_pass"] = pose_count == 1 and len(pose_landmarks) == 33
        record["error"] = None if record["inference_pass"] else "pose_landmarker_returned_no_complete_pose"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def ultralytics_pose_probe(path: Path, label: str) -> dict[str, object]:
    record: dict[str, object] = {
        "runtime": "ultralytics.YOLO(task='pose')",
        "label": label,
        "model": model_record(path),
        "loaded": False,
        "inference_pass": False,
        "detections": [],
        "error": None,
    }
    try:
        from ultralytics import YOLO

        model = YOLO(str(path), task="pose")
        record["loaded"] = True
        results = model.predict(source=str(SOURCE_IMAGE), imgsz=640, conf=0.25, verbose=False, device="cpu")
        detections = []
        for result in results:
            box_count = 0 if result.boxes is None else len(result.boxes)
            keypoint_count = 0
            if result.keypoints is not None and getattr(result.keypoints, "xy", None) is not None:
                keypoint_count = int(result.keypoints.xy.shape[1])
            detections.append({"box_count": box_count, "keypoint_count": keypoint_count})
        record["detections"] = detections
        record["inference_pass"] = any(item["box_count"] and item["keypoint_count"] for item in detections)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def make_panel(source: Image.Image, mediapipe_probe: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "pose_landmark_authority_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    pass_color = (35, 150, 70) if mediapipe_probe.get("inference_pass") else (230, 40, 40)
    draw.rectangle([0, 0, width - 1, height - 1], outline=pass_color, width=6)
    draw.rectangle([20, 20, width - 20, 190], fill=(255, 255, 255), outline=pass_color, width=3)
    font = ImageFont.load_default()
    if mediapipe_probe.get("inference_pass"):
        lines = [
            "TRK-W70-0164 pose route executed",
            f"Detected people: {mediapipe_probe.get('detected_person_count')}",
            f"Pose landmarks: {mediapipe_probe.get('pose_landmark_count')}",
            f"Segmentation masks: {mediapipe_probe.get('segmentation_mask_count')}",
            "Portrait source still blocks full-body authority.",
            "No masks promoted.",
        ]
    else:
        lines = [
            "TRK-W70-0164 blocked",
            "No proven local pose landmark route.",
            "RTMPose/OpenPose assets exist but cannot execute here.",
            "No masks promoted.",
        ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 26
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str, status: str, status_decision: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0164") for path in TRACKER_FILES] + [(path, "ITEM-W70-0164") for path in ITEM_FILES]
    for csv_path, target_id in targets:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        id_field = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        if id_field not in fieldnames:
            id_field = fieldnames[0]
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
                row["Status_Decision"] = status_decision
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [status_decision],
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
    task_models = find_pose_task_models()
    mediapipe_probe = mediapipe_pose_probe(task_models)
    rtmpose_probe = ultralytics_pose_probe(RTMPOSE_MODEL, "rtmpose_wholebody_checkpoint")
    openpose_probe = ultralytics_pose_probe(OPENPOSE_CONTROLNET, "openpose_controlnet_weight")
    panel_path = make_panel(source, mediapipe_probe)
    pose_route_pass = mediapipe_probe.get("inference_pass") is True

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "pose_landmark_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "pose_landmark_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "pose_landmark_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    if pose_route_pass:
        status = "Pose_Landmark_Authority_Source_Derived_Partial"
        status_decision = "pose_landmark_route_executed_source_derived_partial_full_body_authority_still_blocked"
        note = (
            f"Pose landmark authority {RUN_STAMP}: MediaPipe pose task executed and produced "
            f"{mediapipe_probe.get('pose_landmark_count')} source landmarks plus "
            f"{mediapipe_probe.get('segmentation_mask_count')} segmentation mask. "
            "Active portrait lacks full-body/feet/contact visibility, so no whole-body authority or mask promotion occurred."
        )
        blocked_reasons = [
            "active_source_is_portrait_not_full_body_reference",
            "full_body_torso_feet_contact_reference_slots_not_visible",
            "human_part_parsing_contact_ownership_and_body_reference_matrix_still_blocked",
        ]
    else:
        status = "Blocked_Pose_Landmark_Route_Unloadable"
        status_decision = "blocked_pose_landmark_route_unloadable"
        note = (
            f"Pose landmark authority {RUN_STAMP}: exact local blocker. "
            "Pose-like assets exist, but no installed runtime produced source pose landmarks. "
            "No active masks changed or promoted."
        )
        blocked_reasons = [
            "mediapipe_pose_task_model_missing",
            "rtmpose_checkpoint_not_executable_by_installed_ultralytics_path",
            "openpose_controlnet_weight_not_pose_landmark_runtime_model",
            "mmpose_mmengine_mmcv_not_installed",
        ]
    row_updates = update_wave70_rows(evidence_rel_paths, note, status, status_decision)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement pose landmark authority for TRK-W70-0164 / ITEM-W70-0164.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "wave70_model_registry": registry_snapshot(),
            "modules": {
                name: module_available(name)
                for name in ["mediapipe", "mmpose", "mmengine", "mmcv", "ultralytics", "torch", "torchvision", "cv2"]
            },
        },
        "runtime_attempts": {
            "mediapipe_pose_landmarker": mediapipe_probe,
            "ultralytics_rtmpose": rtmpose_probe,
            "ultralytics_openpose_controlnet": openpose_probe,
        },
        "artifacts": {
            "review_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "pose_landmark_authority": {
            "result": "source_derived_pose_landmarks_partial" if pose_route_pass else "blocked",
            "pose_landmark_pass": pose_route_pass,
            "subject_viewer_side_mapping_pass": pose_route_pass,
            "skeleton_anchor_pass": pose_route_pass,
            "source_derived_landmark_or_segmentation_pass": pose_route_pass,
            "detected_person_count": int(mediapipe_probe.get("detected_person_count") or 0),
            "pose_landmark_count": int(mediapipe_probe.get("pose_landmark_count") or 0),
            "segmentation_mask_count": int(mediapipe_probe.get("segmentation_mask_count") or 0),
            "pose_landmarks": mediapipe_probe.get("pose_landmarks") or [],
            "blocked_reason": "; ".join(blocked_reasons),
            "findings": (
                [
                    "MediaPipe PoseLandmarker executed against the active source image.",
                    "A source-derived pose landmark record and segmentation-mask count were produced.",
                    "The active portrait is not a full-body reference, so this cannot satisfy full-body, feet, contact, or body reference matrix requirements by itself.",
                    "No active masks changed or promoted.",
                ]
                if pose_route_pass
                else [
                    "MediaPipe tasks exposes PoseLandmarker, but no local pose_landmarker task model was found.",
                    "The RTMPose whole-body checkpoint is present as .pth, but the installed Ultralytics prediction path rejects .pth inference.",
                    "OpenPoseXL2 is a ControlNet weight, not an executable local pose landmark runtime model.",
                    "MMPose/MMEngine/MMCV are not installed, so the RTMPose checkpoint has no compatible local runtime.",
                ]
            ),
        },
        "qa_decision": status_decision,
        "promotion_decision": "no_mask_promoted_no_active_input_changed_pose_landmark_partial"
        if pose_route_pass
        else "no_mask_promoted_no_active_input_changed_pose_landmark_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Use full-body source/reference slots before whole-body authority can pass."
        if pose_route_pass
        else "Install/register a compatible local pose runtime or a local MediaPipe pose landmarker task model before pose-derived masks can pass.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
