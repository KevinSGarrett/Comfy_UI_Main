from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
MEASURER_PATH = (
    ROOT / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_image_quality.py"
)


def load_measurer():
    spec = importlib.util.spec_from_file_location("w64_aqa_image_measure", MEASURER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(*, width: int = 64, height: int = 64, alpha_required: bool = False) -> dict:
    return {
        "schema_version": "wave64.aqa.job_contract.v1",
        "contract_id": "a" * 64,
        "modality": "image",
        "preflight_disposition": "READY_FOR_LEASE",
        "image_spec": {
            "width": width,
            "height": height,
            "color_space": "sRGB",
            "alpha_required": alpha_required,
        },
        "quality_profile": {
            "hard_gates": [
                {
                    "gate_id": "decode",
                    "metric": "decode_success",
                    "operator": "eq",
                    "threshold": True,
                    "on_failure": "REJECT",
                },
                {
                    "gate_id": "not-all-black",
                    "metric": "black_clip_fraction",
                    "operator": "lt",
                    "threshold": 0.99,
                    "on_failure": "REJECT",
                },
            ]
        },
    }


def write_pattern(path: Path, *, alpha: bool = False) -> None:
    y, x = np.indices((64, 64))
    rgb = np.stack(((x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256), axis=-1).astype(
        np.uint8
    )
    if alpha:
        rgba = np.concatenate((rgb, np.full((64, 64, 1), 220, dtype=np.uint8)), axis=-1)
        Image.fromarray(rgba, "RGBA").save(path)
    else:
        Image.fromarray(rgb, "RGB").save(path)


def test_measurement_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "pattern.png"
    write_pattern(path)
    first = module.measure_image(path, contract())
    second = module.measure_image(path, contract())
    assert first == second
    assert first["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["metrics"]["dynamic_range"] > 100
    assert first["metrics"]["entropy_bits"] > 4


def test_workflow_shadow_output_can_use_deterministic_image_gates(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "pattern.png"
    write_pattern(path)
    workflow_contract = contract()
    workflow_contract["modality"] = "workflow"
    result = module.measure_image(path, workflow_contract)
    assert result["disposition"] == "PASS_DETERMINISTIC_GATES"


def test_geometry_mismatch_is_hard_failure(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "pattern.png"
    write_pattern(path)
    result = module.measure_image(path, contract(width=128))
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"
    width_gate = next(item for item in result["gate_results"] if item["gate_id"] == "contract-width")
    assert width_gate["status"] == "FAIL"


def test_alpha_requirement_is_bound_to_contract(tmp_path: Path) -> None:
    module = load_measurer()
    rgb_path = tmp_path / "rgb.png"
    rgba_path = tmp_path / "rgba.png"
    write_pattern(rgb_path)
    write_pattern(rgba_path, alpha=True)
    assert module.measure_image(rgb_path, contract(alpha_required=True))["disposition"] == "FAIL_DETERMINISTIC_GATES"
    assert module.measure_image(rgba_path, contract(alpha_required=True))["disposition"] == "PASS_DETERMINISTIC_GATES"


def test_clipped_image_fails_declared_gate(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "black.png"
    Image.new("RGB", (64, 64), (0, 0, 0)).save(path)
    result = module.measure_image(path, contract())
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"
    assert result["metrics"]["black_clip_fraction"] == 1.0


def test_unknown_required_metric_fails_closed(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "pattern.png"
    write_pattern(path)
    spec = contract()
    spec["quality_profile"]["hard_gates"].append(
        {
            "gate_id": "future-specialist",
            "metric": "face_identity_similarity",
            "operator": "gte",
            "threshold": 0.9,
            "on_failure": "HOLD",
        }
    )
    result = module.measure_image(path, spec)
    gate = next(item for item in result["gate_results"] if item["gate_id"] == "future-specialist")
    assert gate["status"] == "MEASUREMENT_UNAVAILABLE"
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_corrupt_or_unready_input_is_rejected(tmp_path: Path) -> None:
    module = load_measurer()
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(module.MeasurementError, match="decode failed"):
        module.measure_image(bad, contract())
    path = tmp_path / "pattern.png"
    write_pattern(path)
    held = contract()
    held["preflight_disposition"] = "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    with pytest.raises(module.MeasurementError, match="not ready"):
        module.measure_image(path, held)
