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
PERSON_MODEL = Path(r"C:\Users\kevin\.cache\torch\hub\checkpoints\rtmdet_m_8xb32-100e_coco-obj365-person-235e8209.pth")
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_PERSON_INSTANCE_OWNER_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_person_instance_owner_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_person_instance_owner_authority" / RUN_STAMP

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


def try_ultralytics_inference() -> dict[str, object]:
    record: dict[str, object] = {
        "runtime": "ultralytics.YOLO",
        "attempted": True,
        "loaded": False,
        "inference_pass": False,
        "error": None,
        "detections": [],
    }
    try:
        from ultralytics import YOLO

        model = YOLO(str(PERSON_MODEL), task="detect")
        record["loaded"] = True
        results = model.predict(source=str(SOURCE_IMAGE), imgsz=640, conf=0.25, verbose=False, device="cpu")
        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                detections.append(
                    {
                        "class_id": int(box.cls.item()),
                        "confidence": float(box.conf.item()),
                        "xyxy": [float(value) for value in box.xyxy[0].tolist()],
                    }
                )
        record["detections"] = detections
        record["inference_pass"] = bool(detections)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def make_blocker_panel(source: Image.Image, evidence: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "person_instance_owner_authority_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 150], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0163 blocked",
        "No proven local person-instance owner route.",
        "RTMDet checkpoint exists but runtime cannot run it.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 24
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0163") for path in TRACKER_FILES] + [(path, "ITEM-W70-0163") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Person_Instance_Owner_Route_Unloadable"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_person_instance_owner_route_unloadable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_person_instance_owner_route_unloadable"],
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
    source_hash = sha256_file(SOURCE_IMAGE)
    model_record = {
        "path": str(PERSON_MODEL),
        "exists": PERSON_MODEL.exists(),
        "size_bytes": PERSON_MODEL.stat().st_size if PERSON_MODEL.exists() else None,
        "sha256": sha256_file(PERSON_MODEL) if PERSON_MODEL.exists() and PERSON_MODEL.stat().st_size <= 256 * 1024 * 1024 else None,
    }
    modules = {name: module_available(name) for name in ["ultralytics", "torch", "torchvision", "mmdet", "mmengine", "mmcv", "cv2"]}
    inference = try_ultralytics_inference() if PERSON_MODEL.exists() else {"attempted": False, "error": "person_model_missing"}
    blocker_reasons = []
    if not modules["mmdet"]["available"] or not modules["mmengine"]["available"]:
        blocker_reasons.append("mmdet_mmengine_runtime_not_installed_for_rtmdet_checkpoint")
    if inference.get("error"):
        blocker_reasons.append("ultralytics_inference_failed_for_local_checkpoint")
    if not inference.get("inference_pass"):
        blocker_reasons.append("no_person_instance_detection_produced")
    panel_path = make_blocker_panel(source, {"inference": inference})

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "person_instance_owner_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "person_instance_owner_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "person_instance_owner_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
    ]
    note = (
        f"Person instance owner authority {RUN_STAMP}: exact local blocker. "
        "Local RTMDet checkpoint exists, but installed runtimes cannot produce a proven person instance/owner record from it. "
        "No active masks changed or promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement person instance and owner separation authority for TRK-W70-0163 / ITEM-W70-0163.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": source_hash,
            "dimensions": [width, height],
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "modules": modules,
        },
        "model": model_record,
        "runtime_attempts": {
            "ultralytics": inference,
            "mmdet_mmengine_available": bool(modules["mmdet"]["available"] and modules["mmengine"]["available"]),
        },
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "person_instance_owner_authority": {
            "result": "blocked",
            "person_instance_pass": False,
            "owner_assignment_pass": False,
            "multi_person_overlap_check_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "detected_person_instance_count": 0,
            "person_instances": [],
            "owner_map_path": "",
            "confidence_threshold": 0.25,
            "blocked_reason": "; ".join(blocker_reasons),
            "findings": [
                "A local person checkpoint exists, but it is an RTMDet .pth checkpoint.",
                "MMDetection/MMEngine runtime is not installed in the local environment.",
                "Ultralytics cannot run inference from the local .pth checkpoint in this environment.",
                "No trustworthy person instance or owner assignment was produced.",
            ],
        },
        "qa_decision": "blocked_person_instance_owner_route_unloadable",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_person_instance_owner_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Install/register a compatible local person-instance runtime for the existing RTMDet checkpoint or provide an approved YOLO/instance model that can run locally.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
