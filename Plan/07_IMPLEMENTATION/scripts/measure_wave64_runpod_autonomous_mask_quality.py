#!/usr/bin/env python3
"""Measure deterministic W64-AQA candidate masks against an immutable golden reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import jsonschema
import numpy as np
from PIL import Image, UnidentifiedImageError
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_mask_measurement.schema.json"
EVALUATOR_VERSION = "w64-aqa-mask-measure-v1"
ZERO_HASH = "0" * 64
MASK_THRESHOLD = 0.5
EPSILON = 1e-12


class MeasurementError(ValueError):
    """Raised when a mask or its contract cannot be measured safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_mask(path: Path) -> np.ndarray:
    if not path.is_file():
        raise MeasurementError(f"mask path is not a file: {path}")
    try:
        with Image.open(path) as image:
            image.load()
            if "A" in image.getbands():
                channel = image.getchannel("A")
            elif image.mode in {"I", "I;16", "F"}:
                channel = image.copy()
            else:
                channel = image.convert("L")
            mode = channel.mode
            raw = np.asarray(channel)
    except (OSError, UnidentifiedImageError) as exc:
        raise MeasurementError(f"mask decode failed: {exc}") from exc
    values = raw.astype(np.float64)
    if mode == "F":
        scale = 1.0
    elif mode == "I;16" or float(np.max(values, initial=0)) > 255:
        scale = 65535.0
    else:
        scale = 255.0
    values /= scale
    if values.ndim != 2 or values.size == 0:
        raise MeasurementError("mask must decode to one non-empty channel")
    if not np.all(np.isfinite(values)) or float(np.min(values)) < 0 or float(np.max(values)) > 1:
        raise MeasurementError("mask samples must be finite values in [0, 1]")
    return values


def _boundary(mask: np.ndarray) -> np.ndarray:
    if not np.any(mask):
        return np.zeros_like(mask, dtype=bool)
    eroded = ndimage.binary_erosion(mask, structure=np.ones((3, 3), dtype=bool), border_value=0)
    return np.logical_xor(mask, eroded)


def _boundary_metrics(candidate: np.ndarray, golden: np.ndarray) -> tuple[float, float, float, float]:
    candidate_boundary, golden_boundary = _boundary(candidate), _boundary(golden)
    if not np.any(candidate_boundary) and not np.any(golden_boundary):
        return 1.0, 0.0, 0.0, 0.0
    if not np.any(candidate_boundary) or not np.any(golden_boundary):
        diagonal = math.hypot(*candidate.shape)
        return 0.0, diagonal, diagonal, diagonal
    tolerance_structure = ndimage.iterate_structure(ndimage.generate_binary_structure(2, 2), 2)
    golden_dilated = ndimage.binary_dilation(golden_boundary, structure=tolerance_structure)
    candidate_dilated = ndimage.binary_dilation(candidate_boundary, structure=tolerance_structure)
    precision = float(np.mean(golden_dilated[candidate_boundary]))
    recall = float(np.mean(candidate_dilated[golden_boundary]))
    f1 = 2 * precision * recall / max(precision + recall, EPSILON)
    distance_to_golden = ndimage.distance_transform_edt(~golden_boundary)[candidate_boundary]
    distance_to_candidate = ndimage.distance_transform_edt(~candidate_boundary)[golden_boundary]
    combined = np.concatenate((distance_to_golden, distance_to_candidate))
    return f1, float(np.mean(combined)), float(np.percentile(combined, 95)), float(np.max(combined))


def _topology(mask: np.ndarray) -> tuple[int, int]:
    binary = mask.astype(np.uint8)
    components, _ = cv2.connectedComponents(binary, connectivity=8)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = 0
    if contours and hierarchy is not None:
        holes = sum(1 for entry in hierarchy[0] if entry[3] >= 0)
    return max(0, components - 1), holes


def _bounding_box(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    y, x = np.where(mask)
    if not x.size:
        return None
    return int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1


def _bounding_box_iou(candidate: np.ndarray, golden: np.ndarray) -> float:
    left, right = _bounding_box(candidate), _bounding_box(golden)
    if left is None and right is None:
        return 1.0
    if left is None or right is None:
        return 0.0
    ix0, iy0, ix1, iy1 = max(left[0], right[0]), max(left[1], right[1]), min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    return intersection / max(left_area + right_area - intersection, 1)


def _largest_region(mask: np.ndarray, category: str) -> dict[str, Any] | None:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if count <= 1:
        return None
    index = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return {
        "category": category,
        "x": int(stats[index, cv2.CC_STAT_LEFT]),
        "y": int(stats[index, cv2.CC_STAT_TOP]),
        "width": int(stats[index, cv2.CC_STAT_WIDTH]),
        "height": int(stats[index, cv2.CC_STAT_HEIGHT]),
        "pixels": int(stats[index, cv2.CC_STAT_AREA]),
    }


def _compare(observed: Any, operator: str, threshold: Any) -> bool:
    if operator == "eq":
        return observed == threshold
    if operator == "ne":
        return observed != threshold
    if operator == "lt":
        return observed < threshold
    if operator == "lte":
        return observed <= threshold
    if operator == "gt":
        return observed > threshold
    if operator == "gte":
        return observed >= threshold
    if operator == "between":
        return threshold[0] <= observed <= threshold[1]
    if operator == "contains":
        return threshold in observed
    if operator == "not_contains":
        return threshold not in observed
    raise MeasurementError(f"unsupported gate operator: {operator}")


def _validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "wave64.aqa.job_contract.v1":
        raise MeasurementError("unsupported contract schema_version")
    if contract.get("modality") != "mask":
        raise MeasurementError("mask measurement requires mask modality")
    if contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise MeasurementError("contract is not ready for a lease")
    if not isinstance(contract.get("image_spec"), dict) or not isinstance(contract.get("mask_spec"), dict):
        raise MeasurementError("contract lacks image_spec or mask_spec")


def measure_mask(candidate_path: Path, golden_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    _validate_contract(contract)
    golden_hash = sha256_file(golden_path) if golden_path.is_file() else ""
    expected_hash = contract["mask_spec"]["golden_reference_sha256"]
    if golden_hash != expected_hash:
        raise MeasurementError("golden reference hash does not match the immutable contract")
    candidate_alpha, golden_alpha = _load_mask(candidate_path), _load_mask(golden_path)
    candidate_height, candidate_width = candidate_alpha.shape
    golden_height, golden_width = golden_alpha.shape
    comparable = candidate_alpha.shape == golden_alpha.shape
    if comparable:
        candidate_binary, golden_binary = candidate_alpha >= MASK_THRESHOLD, golden_alpha >= MASK_THRESHOLD
        intersection = int(np.count_nonzero(candidate_binary & golden_binary))
        union = int(np.count_nonzero(candidate_binary | golden_binary))
        candidate_area, golden_area = int(np.count_nonzero(candidate_binary)), int(np.count_nonzero(golden_binary))
        false_negative = golden_binary & ~candidate_binary
        false_positive = candidate_binary & ~golden_binary
        boundary_f1, boundary_mean, boundary_p95, boundary_hausdorff = _boundary_metrics(candidate_binary, golden_binary)
        candidate_components, candidate_holes = _topology(candidate_binary)
        golden_components, golden_holes = _topology(golden_binary)
        alpha_delta = candidate_alpha - golden_alpha
        metrics_body = {
            "candidate_foreground_fraction": candidate_area / candidate_binary.size,
            "golden_foreground_fraction": golden_area / golden_binary.size,
            "intersection_over_union": intersection / max(union, 1),
            "dice_coefficient": 2 * intersection / max(candidate_area + golden_area, 1),
            "foreground_completeness": intersection / max(golden_area, 1),
            "foreground_leakage_fraction": int(np.count_nonzero(false_positive)) / max(candidate_area, 1),
            "false_negative_pixel_fraction": float(np.mean(false_negative)),
            "false_positive_pixel_fraction": float(np.mean(false_positive)),
            "alpha_mae": float(np.mean(np.abs(alpha_delta))),
            "alpha_rmse": math.sqrt(float(np.mean(np.square(alpha_delta)))),
            "non_binary_pixel_fraction": float(np.mean((candidate_alpha > 0.001) & (candidate_alpha < 0.999))),
            "boundary_f1_tolerance_2px": boundary_f1,
            "boundary_mean_distance_px": boundary_mean,
            "boundary_p95_distance_px": boundary_p95,
            "boundary_hausdorff_distance_px": boundary_hausdorff,
            "candidate_component_count": candidate_components,
            "golden_component_count": golden_components,
            "component_count_delta": abs(candidate_components - golden_components),
            "candidate_hole_count": candidate_holes,
            "golden_hole_count": golden_holes,
            "hole_count_delta": abs(candidate_holes - golden_holes),
            "bounding_box_iou": _bounding_box_iou(candidate_binary, golden_binary),
        }
        defect_regions = [
            region for region in (
                _largest_region(false_negative, "largest_missing_region"),
                _largest_region(false_positive, "largest_leakage_region"),
            ) if region is not None
        ]
    else:
        metrics_body = {
            "candidate_foreground_fraction": float(np.mean(candidate_alpha >= MASK_THRESHOLD)),
            "golden_foreground_fraction": float(np.mean(golden_alpha >= MASK_THRESHOLD)),
            "intersection_over_union": 0.0, "dice_coefficient": 0.0,
            "foreground_completeness": 0.0, "foreground_leakage_fraction": 1.0,
            "false_negative_pixel_fraction": 1.0, "false_positive_pixel_fraction": 1.0,
            "alpha_mae": 1.0, "alpha_rmse": 1.0,
            "non_binary_pixel_fraction": float(np.mean((candidate_alpha > 0.001) & (candidate_alpha < 0.999))),
            "boundary_f1_tolerance_2px": 0.0,
            "boundary_mean_distance_px": math.hypot(golden_height, golden_width),
            "boundary_p95_distance_px": math.hypot(golden_height, golden_width),
            "boundary_hausdorff_distance_px": math.hypot(golden_height, golden_width),
            "candidate_component_count": _topology(candidate_alpha >= MASK_THRESHOLD)[0],
            "golden_component_count": _topology(golden_alpha >= MASK_THRESHOLD)[0],
            "component_count_delta": abs(_topology(candidate_alpha >= MASK_THRESHOLD)[0] - _topology(golden_alpha >= MASK_THRESHOLD)[0]),
            "candidate_hole_count": _topology(candidate_alpha >= MASK_THRESHOLD)[1],
            "golden_hole_count": _topology(golden_alpha >= MASK_THRESHOLD)[1],
            "hole_count_delta": abs(_topology(candidate_alpha >= MASK_THRESHOLD)[1] - _topology(golden_alpha >= MASK_THRESHOLD)[1]),
            "bounding_box_iou": 0.0,
        }
        defect_regions = []

    image_spec, mask_spec = contract["image_spec"], contract["mask_spec"]
    metrics: dict[str, Any] = {
        "decode_success": True,
        "candidate_width": candidate_width, "candidate_height": candidate_height,
        "golden_width": golden_width, "golden_height": golden_height,
        "width_delta": abs(candidate_width - int(image_spec["width"])),
        "height_delta": abs(candidate_height - int(image_spec["height"])),
        "reference_width_delta": abs(candidate_width - golden_width),
        "reference_height_delta": abs(candidate_height - golden_height),
        **metrics_body,
    }
    implicit_gates = [
        {"gate_id": "contract-width", "metric": "width_delta", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
        {"gate_id": "contract-height", "metric": "height_delta", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
        {"gate_id": "reference-width", "metric": "reference_width_delta", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
        {"gate_id": "reference-height", "metric": "reference_height_delta", "operator": "eq", "threshold": 0, "on_failure": "REJECT"},
    ]
    if mask_spec["alpha_mode"] == "binary":
        implicit_gates.append({
            "gate_id": "contract-binary-alpha", "metric": "non_binary_pixel_fraction",
            "operator": "lte", "threshold": 0.001, "on_failure": "REJECT",
        })

    gate_results, seen = [], set()
    for gate in implicit_gates + contract["quality_profile"]["hard_gates"]:
        if gate["gate_id"] in seen:
            raise MeasurementError(f"duplicate implicit/declared gate ID: {gate['gate_id']}")
        seen.add(gate["gate_id"])
        observed = metrics.get(gate["metric"])
        if gate["metric"] not in metrics:
            status, observed = "MEASUREMENT_UNAVAILABLE", None
        else:
            try:
                status = "PASS" if _compare(observed, gate["operator"], gate["threshold"]) else "FAIL"
            except (TypeError, ValueError, IndexError) as exc:
                raise MeasurementError(f"invalid threshold for gate {gate['gate_id']}") from exc
        gate_results.append({
            "gate_id": gate["gate_id"], "metric": gate["metric"], "status": status,
            "observed": observed, "operator": gate["operator"], "threshold": gate["threshold"],
            "on_failure": gate["on_failure"],
        })

    measurement = {
        "schema_version": "wave64.aqa.mask_measurement.v1",
        "measurement_id": ZERO_HASH,
        "contract_id": contract["contract_id"],
        "candidate_sha256": sha256_file(candidate_path),
        "golden_reference_sha256": golden_hash,
        "target_binding": mask_spec["target_binding"],
        "evaluator_version": EVALUATOR_VERSION,
        "geometry": {
            "candidate_width": candidate_width, "candidate_height": candidate_height,
            "golden_width": golden_width, "golden_height": golden_height,
        },
        "alpha_mode": mask_spec["alpha_mode"],
        "defect_regions": defect_regions,
        "metrics": metrics,
        "gate_results": gate_results,
        "disposition": "PASS_DETERMINISTIC_GATES" if all(item["status"] == "PASS" for item in gate_results) else "FAIL_DETERMINISTIC_GATES",
    }
    measurement["measurement_id"] = hashlib.sha256(canonical_bytes(measurement)).hexdigest()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(measurement)
    return measurement


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("golden_reference", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        result = measure_mask(args.candidate, args.golden_reference, contract)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise MeasurementError("output already exists; measurements are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, MeasurementError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
