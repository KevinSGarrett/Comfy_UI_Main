#!/usr/bin/env python3
"""Prepare a hash-verifiable DWPose control map from one original image."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = PROJECT_ROOT / "Ref_Image_1/Full/59bcb65a41a752476c58e9c81f70681a.jpg"
DEFAULT_MODEL_DIR = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "Plan/Instructions/Operations/Prepared_Input_Assets/openpose_full_body_walking_w70_v1"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def visible_body_keypoints(person: dict) -> int:
    values = person.get("pose_keypoints_2d") or []
    return sum(
        1
        for index in range(0, len(values) - 2, 3)
        if float(values[index + 2]) > 0.0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--resolution", type=int, default=768)
    parser.add_argument("--active-input-name", default="controlnet_openpose_full_body_walking_w70_v1.png")
    parser.add_argument(
        "--selection-reason",
        default="true full body with head, both hands, both legs, and both feet visible",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    model_dir = args.model_dir.resolve()
    output_dir = args.output_dir.resolve()
    detector_path = model_dir / "yolox_l.onnx"
    pose_path = model_dir / "dw-ll_ucoco_384.onnx"
    required = [source, detector_path, pose_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required local input missing: {missing}")

    aux_src = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_original.jpg"
    control_map = output_dir / args.active_input_name
    keypoints_file = output_dir / "openpose_keypoints.json"
    manifest_file = output_dir / "PREPARATION_MANIFEST.json"

    with Image.open(source) as loaded:
        source_image = loaded.convert("RGB")
        source_size = source_image.size
        source_image.save(source_copy, format="JPEG", quality=95, subsampling=0)

    detector = DwposeDetector(
        Wholebody(str(detector_path), str(pose_path), torchscript_device="cpu")
    )
    rendered, keypoints = detector(
        np.asarray(source_image),
        detect_resolution=args.resolution,
        include_body=True,
        include_hand=True,
        include_face=True,
        output_type="pil",
        image_and_json=True,
    )
    rendered.save(control_map, format="PNG")
    keypoints_file.write_text(json.dumps(keypoints, indent=2) + "\n", encoding="utf-8")

    people = keypoints.get("people") or []
    visible_body_counts = [visible_body_keypoints(person) for person in people]
    checks = {
        "exactly_one_person_detected": len(people) == 1,
        "at_least_14_body_keypoints_visible": (
            len(visible_body_counts) == 1 and visible_body_counts[0] >= 14
        ),
        "control_map_nonempty": control_map.stat().st_size > 0,
        "source_is_outside_excluded_new_folder": "new folder" not in str(source).lower(),
        "gold_masks_not_consumed": True,
    }
    passed = all(checks.values())
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": (
            "pass_local_dwpose_full_body_control_map_prepared"
            if passed
            else "blocked_local_dwpose_full_body_detection_incomplete"
        ),
        "pass": passed,
        "scope": "single_original_full_body_pose_variety_control_map",
        "limitations": [
            "This is a local control-map preparation check, not body-mask authority.",
            "No gold mask was read, compared, promoted, or treated as truth.",
            "One detected pose does not certify full-body geometry or target-runtime readiness.",
        ],
        "source": {
            "path": repo_path(source),
            "sha256": sha256_file(source),
            "width": source_size[0],
            "height": source_size[1],
            "selection_reason": args.selection_reason,
        },
        "models": {
            "detector": {"path": str(detector_path), "sha256": sha256_file(detector_path)},
            "pose_estimator": {"path": str(pose_path), "sha256": sha256_file(pose_path)},
        },
        "outputs": {
            "source_copy": {"path": repo_path(source_copy), "sha256": sha256_file(source_copy)},
            "control_map": {
                "path": repo_path(control_map),
                "sha256": sha256_file(control_map),
                "width": rendered.width,
                "height": rendered.height,
            },
            "keypoints": {"path": repo_path(keypoints_file), "sha256": sha256_file(keypoints_file)},
        },
        "detections": {
            "person_count": len(people),
            "visible_body_keypoint_counts": visible_body_counts,
        },
        "checks": checks,
    }
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
