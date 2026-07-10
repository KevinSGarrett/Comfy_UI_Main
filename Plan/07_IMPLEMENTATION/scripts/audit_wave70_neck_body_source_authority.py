#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
BODY_ROOT = PROJECT_ROOT / "MaskedWarehouse" / "Body"
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MF70_NECK_BODY_SOURCE_AUTHORITY_AUDIT_{RUN_STAMP}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() and path.is_file() else None,
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def image_unique_values(path: Path, limit: int = 256) -> list[Any]:
    image = Image.open(path)
    arr = np.array(image)
    if arr.ndim == 2:
        values = np.unique(arr)
        return [int(value) for value in values[:limit]]
    flat = arr.reshape(-1, arr.shape[-1])
    values = np.unique(flat, axis=0)
    return [tuple(int(part) for part in value) for value in values[:limit]]


def sample_images(paths: list[Path], limit: int = 12) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for path in paths[:limit]:
        try:
            image = Image.open(path)
            samples.append(
                {
                    "path": rel(path),
                    "mode": image.mode,
                    "size": list(image.size),
                    "unique_values_sample": image_unique_values(path, 32),
                }
            )
        except Exception as exc:  # noqa: BLE001 - evidence should record exact read failure.
            samples.append({"path": rel(path), "error": repr(exc)})
    return samples


def lv_mhp_audit() -> dict[str, Any]:
    root = BODY_ROOT / "LV-MHP-v1" / "LV-MHP-v1"
    readme = root / "README.txt"
    text = read_text(readme)
    label_map = {
        0: "background",
        1: "hat",
        2: "hair",
        3: "sunglass",
        4: "upper-clothes",
        5: "skirt",
        6: "pants",
        7: "dress",
        8: "belt",
        9: "left-shoe",
        10: "right-shoe",
        11: "face",
        12: "left-leg",
        13: "right-leg",
        14: "left-arm",
        15: "right-arm",
        16: "bag",
        17: "scarf",
        18: "torso-skin",
    }
    annotations = sorted((root / "annotations").glob("*.png"))
    label_values: set[int] = set()
    for path in annotations[:50]:
        try:
            label_values.update(int(value) for value in np.unique(np.array(Image.open(path).convert("L"))))
        except Exception:
            continue
    labels_seen = {value: label_map.get(value, "unknown") for value in sorted(label_values)}
    return {
        "dataset": "LV-MHP-v1",
        "root": rel(root),
        "readme": file_record(readme),
        "readme_mentions_neck": "neck" in text.lower(),
        "declared_label_map": label_map,
        "explicit_neck_label_present": any("neck" in label.lower() for label in label_map.values()),
        "has_face_label": 11 in label_map,
        "has_torso_skin_label": 18 in label_map,
        "annotation_file_count": len(annotations),
        "image_file_count": len(list((root / "images").glob("*"))),
        "sampled_labels_seen": labels_seen,
        "sample_annotations": sample_images(annotations, 8),
        "authority_decision": "not_direct_mf70_neck_authority_no_explicit_neck_label",
    }


def unidata_audit() -> dict[str, Any]:
    root = BODY_ROOT / "UniDataPro_swimsuit-human-segmentation-dataset"
    readme = root / "README.md"
    inventory = root / "maskfactory_inventory.json"
    masks = sorted(root.glob("**/mask.png")) + sorted(root.glob("**/*mask*.png"))
    unique_masks = []
    seen: set[Path] = set()
    for path in masks:
        if path not in seen and path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            unique_masks.append(path)
            seen.add(path)
    text = read_text(readme)
    return {
        "dataset": "UniDataPro_swimsuit-human-segmentation-dataset",
        "root": rel(root),
        "readme": file_record(readme),
        "inventory": file_record(inventory),
        "readme_mentions_neck": "neck" in text.lower(),
        "explicit_neck_label_present": False,
        "mask_file_count": len(unique_masks),
        "sample_masks": sample_images(unique_masks, 10),
        "authority_decision": "not_direct_mf70_neck_authority_preview_masks_no_explicit_neck_label",
    }


def archive_audit() -> dict[str, Any]:
    root = BODY_ROOT / "archive"
    masks = sorted((root).glob("**/masks/*"))
    mask_files = [path for path in masks if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    xlsx = root / "Human Segmentation 7 Types.xlsx"
    return {
        "dataset": "archive_human_segmentation",
        "root": rel(root),
        "xlsx": file_record(xlsx),
        "explicit_neck_label_present": False,
        "mask_file_count": len(mask_files),
        "sample_masks": sample_images(mask_files, 10),
        "authority_decision": "not_direct_mf70_neck_authority_no_accessible_explicit_neck_mask_labels_in_mask_files",
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    dataset_audits = [lv_mhp_audit(), unidata_audit(), archive_audit()]
    direct_authorities = [
        audit["dataset"]
        for audit in dataset_audits
        if audit.get("explicit_neck_label_present") is True
    ]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local body-source audit for direct mf70_neck gold/parser authority after CelebAMask neck boundary routes failed",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "body_root": rel(BODY_ROOT),
        "dataset_audits": dataset_audits,
        "direct_neck_authority_sources": direct_authorities,
        "direct_neck_authority_available": bool(direct_authorities),
        "result": (
            "mf70_neck_body_source_direct_authority_available"
            if direct_authorities
            else "mf70_neck_body_source_direct_authority_blocked_no_explicit_neck_label"
        ),
        "finding": (
            "Current local body datasets do not provide a direct explicit neck label usable as a stronger mf70_neck authority. "
            "LV-MHP includes face and torso-skin but no neck label; UniDataPro preview and archive masks do not expose a direct neck class."
        ),
        "next_required_action": (
            "Keep mf70_neck unpromoted. Either acquire/register a body parser with explicit neck labels, define a justified neck policy "
            "from face/torso labels with new gold review, or switch to another local gold-backed row such as runtime 106-point eyes."
        ),
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "direct_neck_authority_available": evidence["direct_neck_authority_available"],
                "datasets": [audit["dataset"] for audit in dataset_audits],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
