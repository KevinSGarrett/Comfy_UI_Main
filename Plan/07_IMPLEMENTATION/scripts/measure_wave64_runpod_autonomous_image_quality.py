#!/usr/bin/env python3
"""Measure deterministic W64-AQA image gates before any VLM review."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_image_measurement.schema.json"
EVALUATOR_VERSION = "w64-aqa-image-measure-v1"
ZERO_HASH = "0" * 64


class MeasurementError(ValueError):
    """Raised when the artifact or contract cannot be measured safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entropy(gray_u8: np.ndarray) -> float:
    histogram = np.bincount(gray_u8.ravel(), minlength=256).astype(np.float64)
    probabilities = histogram[histogram > 0] / gray_u8.size
    return float(-(probabilities * np.log2(probabilities)).sum())


def _laplacian_variance(gray: np.ndarray) -> float:
    padded = np.pad(gray, 1, mode="edge")
    laplacian = (
        -4 * padded[1:-1, 1:-1]
        + padded[:-2, 1:-1]
        + padded[2:, 1:-1]
        + padded[1:-1, :-2]
        + padded[1:-1, 2:]
    )
    return float(np.var(laplacian))


def _high_frequency_mad(gray: np.ndarray) -> float:
    padded = np.pad(gray, 1, mode="reflect")
    smooth = sum(
        padded[y : y + gray.shape[0], x : x + gray.shape[1]]
        for y in range(3)
        for x in range(3)
    ) / 9.0
    return float(np.median(np.abs(gray - smooth)))


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
    if contract.get("modality") not in {"image", "mask", "workflow"}:
        raise MeasurementError("image measurement requires image, mask, or workflow modality")
    if contract.get("preflight_disposition") != "READY_FOR_LEASE":
        raise MeasurementError("contract is not ready for a lease")
    if not isinstance(contract.get("image_spec"), dict):
        raise MeasurementError("contract lacks image_spec")


def measure_image(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    _validate_contract(contract)
    if not path.is_file():
        raise MeasurementError("artifact path is not a file")
    artifact_hash = sha256_file(path)
    try:
        with Image.open(path) as source:
            source.load()
            image_format = source.format or "UNKNOWN"
            source_mode = source.mode
            frame_count = int(getattr(source, "n_frames", 1))
            rgba = np.asarray(source.convert("RGBA"), dtype=np.uint8)
    except (OSError, UnidentifiedImageError) as exc:
        raise MeasurementError(f"image decode failed: {exc}") from exc

    height, width = rgba.shape[:2]
    rgb = rgba[:, :, :3].astype(np.float64)
    alpha = rgba[:, :, 3].astype(np.float64)
    luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    gray_u8 = np.clip(np.rint(luminance), 0, 255).astype(np.uint8)
    p01, p99 = np.percentile(luminance, [1, 99])
    alpha_present = source_mode in {"RGBA", "LA", "PA"} or "transparency" in source.info

    metrics: dict[str, Any] = {
        "decode_success": True,
        "width": width,
        "height": height,
        "aspect_ratio": width / height,
        "file_size_bytes": path.stat().st_size,
        "luminance_mean": float(np.mean(luminance)),
        "luminance_p01": float(p01),
        "luminance_p99": float(p99),
        "dynamic_range": float(p99 - p01),
        "black_clip_fraction": float(np.mean(luminance <= 1.0)),
        "white_clip_fraction": float(np.mean(luminance >= 254.0)),
        "entropy_bits": _entropy(gray_u8),
        "sharpness_laplacian_variance": _laplacian_variance(luminance),
        "noise_high_frequency_mad": _high_frequency_mad(luminance),
        "alpha_present": alpha_present,
        "alpha_coverage_fraction": float(np.mean(alpha > 0)),
        "alpha_opaque_fraction": float(np.mean(alpha >= 255)),
    }
    spec = contract["image_spec"]
    implicit_gates = [
        {
            "gate_id": "contract-width",
            "metric": "width",
            "operator": "eq",
            "threshold": spec["width"],
            "on_failure": "REJECT",
        },
        {
            "gate_id": "contract-height",
            "metric": "height",
            "operator": "eq",
            "threshold": spec["height"],
            "on_failure": "REJECT",
        },
        {
            "gate_id": "contract-alpha",
            "metric": "alpha_present",
            "operator": "eq",
            "threshold": spec["alpha_required"],
            "on_failure": "REJECT",
        },
    ]
    declared_gates = contract["quality_profile"]["hard_gates"]
    gate_results = []
    seen = set()
    for gate in implicit_gates + declared_gates:
        if gate["gate_id"] in seen:
            raise MeasurementError(f"duplicate implicit/declared gate ID: {gate['gate_id']}")
        seen.add(gate["gate_id"])
        observed = metrics.get(gate["metric"])
        if gate["metric"] not in metrics:
            status = "MEASUREMENT_UNAVAILABLE"
            observed = None
        else:
            try:
                status = "PASS" if _compare(observed, gate["operator"], gate["threshold"]) else "FAIL"
            except (TypeError, ValueError, IndexError) as exc:
                raise MeasurementError(f"invalid threshold for gate {gate['gate_id']}") from exc
        gate_results.append(
            {
                "gate_id": gate["gate_id"],
                "metric": gate["metric"],
                "status": status,
                "observed": observed,
                "operator": gate["operator"],
                "threshold": gate["threshold"],
                "on_failure": gate["on_failure"],
            }
        )

    measurement = {
        "schema_version": "wave64.aqa.image_measurement.v1",
        "measurement_id": ZERO_HASH,
        "contract_id": contract["contract_id"],
        "artifact_sha256": artifact_hash,
        "evaluator_version": EVALUATOR_VERSION,
        "decode": {
            "success": True,
            "format": image_format,
            "mode": source_mode,
            "frame_count": frame_count,
        },
        "geometry": {
            "width": width,
            "height": height,
            "aspect_ratio": width / height,
            "expected_width": spec["width"],
            "expected_height": spec["height"],
        },
        "metrics": metrics,
        "gate_results": gate_results,
        "disposition": (
            "PASS_DETERMINISTIC_GATES"
            if all(result["status"] == "PASS" for result in gate_results)
            else "FAIL_DETERMINISTIC_GATES"
        ),
    }
    measurement["measurement_id"] = hashlib.sha256(canonical_bytes(measurement)).hexdigest()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(measurement)
    if not math.isfinite(sum(value for value in metrics.values() if isinstance(value, float))):
        raise MeasurementError("non-finite measurement produced")
    return measurement


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        result = measure_image(args.artifact, contract)
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
