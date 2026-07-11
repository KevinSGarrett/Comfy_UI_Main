#!/usr/bin/env python3
"""Prepare a fail-closed two-person DWPose control map for contact remediation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "realvisxl_two_character_hand_to_body_w69_seed7152026252_20260707T113434-0500/"
    "images/codex_realvisxl_two_character_hand_to_body_seed7152026252_00001_.png"
)
DEFAULT_MODEL_DIR = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "base_two_character_openpose_contact_w70_v1"
)
DEFAULT_ACTIVE_INPUT = "controlnet_openpose_two_character_contact_w70_v1.png"
EXPECTED_SOURCE_SHA256 = "d6ef67713167d55696b1f07e86c88e9ee0a038f946be9cd8cc56810f724b81a7"
EXPECTED_DETECTOR_SHA256 = "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411"
EXPECTED_POSE_SHA256 = "724f4ff2439ed61afb86fb8a1951ec39c6220682803b4a8bd4f598cd913b1843"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def visible_body_keypoints(person: dict[str, Any]) -> int:
    values = person.get("pose_keypoints_2d") or []
    return sum(
        1
        for index in range(0, len(values) - 2, 3)
        if float(values[index + 2]) > 0.0
    )


def summarize_people(keypoints: dict[str, Any]) -> list[dict[str, int]]:
    people = keypoints.get("people") or []
    return [
        {
            "person_index": index,
            "visible_body_keypoints": visible_body_keypoints(person),
            "pose_keypoint_triplets": len(person.get("pose_keypoints_2d") or []) // 3,
        }
        for index, person in enumerate(people)
    ]


def run_checks(
    people_summary: list[dict[str, int]],
    min_visible_keypoints: int,
    control_size: tuple[int, int],
    source_size: tuple[int, int],
    control_bytes: int,
) -> dict[str, bool]:
    return {
        "exactly_two_people_detected": len(people_summary) == 2,
        "each_person_has_min_visible_body_keypoints": (
            len(people_summary) == 2
            and all(
                person["visible_body_keypoints"] >= min_visible_keypoints
                for person in people_summary
            )
        ),
        "control_map_nonempty": control_bytes > 0,
        "control_map_dimensions_match_source": control_size == source_size,
    }


def require_expected_hash(path: Path, expected_sha256: str, role: str) -> str:
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise ValueError(
            f"{role} SHA256 mismatch: expected {expected_sha256}, observed {observed}"
        )
    return observed


def validate_active_input_name(value: str) -> str:
    candidate = Path(value)
    if candidate.name != value or candidate.suffix.lower() != ".png":
        raise ValueError("active input name must be one PNG basename")
    return value


def main() -> int:
    import numpy as np
    from PIL import Image

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--active-input-name", default=DEFAULT_ACTIVE_INPUT)
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--min-visible-keypoints", type=int, default=10)
    args = parser.parse_args()

    active_input_name = validate_active_input_name(args.active_input_name)
    source = args.source.resolve()
    model_dir = args.model_dir.resolve()
    output_dir = args.output_dir.resolve()
    detector_path = model_dir / "yolox_l.onnx"
    pose_path = model_dir / "dw-ll_ucoco_384.onnx"
    missing = [
        str(path)
        for path in (source, detector_path, pose_path)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Required local input missing: {missing}")

    source_sha256 = require_expected_hash(source, EXPECTED_SOURCE_SHA256, "source")
    detector_sha256 = require_expected_hash(
        detector_path, EXPECTED_DETECTOR_SHA256, "detector"
    )
    pose_sha256 = require_expected_hash(pose_path, EXPECTED_POSE_SHA256, "pose model")

    aux_src = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_preferred_seed7152026252.png"
    control_map = output_dir / active_input_name
    keypoints_file = output_dir / "openpose_keypoints.json"
    manifest_file = output_dir / "PREPARATION_MANIFEST.json"
    active_input = PROJECT_ROOT / "ComfyUI/input" / active_input_name

    with Image.open(source) as loaded:
        source_rgb = loaded.convert("RGB")
        source_size = source_rgb.size
        source_rgb.save(source_copy, format="PNG")

    detector = DwposeDetector(
        Wholebody(str(detector_path), str(pose_path), torchscript_device="cpu")
    )
    rendered, keypoints = detector(
        np.asarray(source_rgb),
        detect_resolution=args.resolution,
        include_body=True,
        include_hand=True,
        include_face=True,
        output_type="pil",
        image_and_json=True,
    )
    if not isinstance(keypoints, dict):
        raise TypeError("DWPose did not return an OpenPose JSON object")

    rendered.save(control_map, format="PNG")
    keypoints_file.write_text(json.dumps(keypoints, indent=2) + "\n", encoding="utf-8")
    people_summary = summarize_people(keypoints)
    checks = run_checks(
        people_summary=people_summary,
        min_visible_keypoints=args.min_visible_keypoints,
        control_size=rendered.size,
        source_size=source_size,
        control_bytes=control_map.stat().st_size,
    )
    passed = all(checks.values())

    active_input_written = False
    active_input_sha256 = None
    if passed:
        active_input.parent.mkdir(parents=True, exist_ok=True)
        partial = active_input.with_name(active_input.name + ".partial")
        partial.write_bytes(control_map.read_bytes())
        partial.replace(active_input)
        active_input_written = True
        active_input_sha256 = sha256_file(active_input)

    manifest = {
        "schema_version": "1.0",
        "manifest_id": "W70-LOCAL-BASE-TWO-CHARACTER-OPENPOSE-CONTACT-CONTROL-MAP-V1",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pass": passed,
        "scope": "two_character_contact_composition_control_from_preferred_base_sample",
        "source": {
            "path": rel_path(source),
            "sha256": source_sha256,
            "expected_sha256": EXPECTED_SOURCE_SHA256,
            "width": source_size[0],
            "height": source_size[1],
            "selected_seed": 7152026252,
        },
        "models": {
            "detector": {
                "path": str(detector_path),
                "sha256": detector_sha256,
                "expected_sha256": EXPECTED_DETECTOR_SHA256,
            },
            "pose_estimator": {
                "path": str(pose_path),
                "sha256": pose_sha256,
                "expected_sha256": EXPECTED_POSE_SHA256,
            },
        },
        "outputs": {
            "source_copy": {
                "path": rel_path(source_copy),
                "sha256": sha256_file(source_copy),
            },
            "control_map": {
                "path": rel_path(control_map),
                "sha256": sha256_file(control_map),
                "width": rendered.width,
                "height": rendered.height,
            },
            "keypoints": {
                "path": rel_path(keypoints_file),
                "sha256": sha256_file(keypoints_file),
            },
            "active_input_copy": {
                "path": rel_path(active_input),
                "written": active_input_written,
                "sha256": active_input_sha256,
            },
        },
        "detections": {
            "people_count": len(people_summary),
            "people": people_summary,
            "minimum_visible_body_keypoints_per_person": args.min_visible_keypoints,
        },
        "checks": checks,
        "result": (
            "pass_local_two_character_openpose_contact_control_map_prepared"
            if passed
            else "blocked_two_character_geometry_not_detected"
        ),
        "fail_closed_reason": (
            None
            if passed
            else "Two-person geometry or control-map integrity did not satisfy the fixed gate."
        ),
        "boundaries": {
            "local_only": True,
            "generation_executed": False,
            "gold_masks_consumed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_promotion_performed": False,
        },
    }
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
