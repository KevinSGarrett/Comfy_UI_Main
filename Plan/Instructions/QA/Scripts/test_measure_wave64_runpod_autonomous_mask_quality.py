from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
MEASURER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_mask_quality.py"


def load_measurer():
    spec = importlib.util.spec_from_file_location("w64_aqa_mask_measure", MEASURER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_mask(path: Path, values: np.ndarray) -> None:
    Image.fromarray(np.round(values * 255).astype(np.uint8), mode="L").save(path)


def base_mask(height: int = 64, width: int = 64) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.float64)
    mask[12:52, 16:48] = 1.0
    mask[26:34, 26:38] = 0.0
    return mask


def contract(golden: Path, *, width: int = 64, height: int = 64, alpha_mode: str = "binary") -> dict:
    return {
        "schema_version": "wave64.aqa.job_contract.v1",
        "contract_id": "c" * 64,
        "modality": "mask",
        "preflight_disposition": "READY_FOR_LEASE",
        "image_spec": {"width": width, "height": height, "color_space": "sRGB", "alpha_required": True},
        "mask_spec": {
            "target_binding": "character-001/body",
            "golden_reference_sha256": sha256_file(golden),
            "alpha_mode": alpha_mode,
            "temporal_consistency_required": False,
        },
        "quality_profile": {"hard_gates": [
            {"gate_id": "iou", "metric": "intersection_over_union", "operator": "gte", "threshold": 0.95, "on_failure": "REPAIR"},
            {"gate_id": "completeness", "metric": "foreground_completeness", "operator": "gte", "threshold": 0.95, "on_failure": "REPAIR"},
            {"gate_id": "leakage", "metric": "foreground_leakage_fraction", "operator": "lte", "threshold": 0.02, "on_failure": "REPAIR"},
            {"gate_id": "boundary", "metric": "boundary_f1_tolerance_2px", "operator": "gte", "threshold": 0.95, "on_failure": "REPAIR"},
        ]},
    }


def test_exact_golden_mask_is_deterministic_and_passes(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    values = base_mask()
    write_mask(golden, values)
    write_mask(candidate, values)
    first = module.measure_mask(candidate, golden, contract(golden))
    second = module.measure_mask(candidate, golden, contract(golden))
    assert first == second
    assert first["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["metrics"]["intersection_over_union"] == 1.0
    assert first["metrics"]["candidate_hole_count"] == 1
    assert first["target_binding"] == "character-001/body"


def test_missing_and_leaking_regions_are_localized_and_fail(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    values = base_mask()
    damaged = values.copy()
    damaged[12:30, 16:28] = 0
    damaged[4:12, 48:60] = 1
    write_mask(golden, values)
    write_mask(candidate, damaged)
    result = module.measure_mask(candidate, golden, contract(golden))
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"
    assert {item["category"] for item in result["defect_regions"]} == {"largest_missing_region", "largest_leakage_region"}
    assert result["metrics"]["foreground_completeness"] < 0.95
    assert result["metrics"]["foreground_leakage_fraction"] > 0.02


def test_geometry_and_binary_alpha_contracts_fail_closed(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    write_mask(golden, base_mask())
    write_mask(candidate, base_mask(48, 48))
    result = module.measure_mask(candidate, golden, contract(golden, width=48, height=48))
    assert next(item for item in result["gate_results"] if item["gate_id"] == "reference-width")["status"] == "FAIL"
    soft = tmp_path / "soft.png"
    soft_values = base_mask()
    soft_values[12:16, 16:48] = 0.5
    write_mask(soft, soft_values)
    soft_result = module.measure_mask(soft, golden, contract(golden))
    assert next(item for item in soft_result["gate_results"] if item["gate_id"] == "contract-binary-alpha")["status"] == "FAIL"


def test_boundary_shift_and_topology_changes_are_measured(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    values = base_mask()
    shifted = np.roll(values, 5, axis=1)
    shifted[40:44, 40:44] = 0
    write_mask(golden, values)
    write_mask(candidate, shifted)
    result = module.measure_mask(candidate, golden, contract(golden))
    assert result["metrics"]["boundary_hausdorff_distance_px"] >= 5
    assert result["metrics"]["hole_count_delta"] >= 1


def test_unknown_semantic_or_ensemble_gate_is_unavailable(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    write_mask(golden, base_mask())
    write_mask(candidate, base_mask())
    spec = contract(golden)
    spec["quality_profile"]["hard_gates"].append({
        "gate_id": "target", "metric": "target_instance_verified", "operator": "eq",
        "threshold": True, "on_failure": "HOLD",
    })
    spec["quality_profile"]["hard_gates"].append({
        "gate_id": "ensemble", "metric": "qualified_ensemble_disagreement", "operator": "lte",
        "threshold": 0.05, "on_failure": "HOLD",
    })
    result = module.measure_mask(candidate, golden, spec)
    statuses = {item["gate_id"]: item["status"] for item in result["gate_results"]}
    assert statuses["target"] == statuses["ensemble"] == "MEASUREMENT_UNAVAILABLE"
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_wrong_reference_corrupt_and_unready_inputs_are_rejected(tmp_path: Path) -> None:
    module = load_measurer()
    golden = tmp_path / "golden.png"
    candidate = tmp_path / "candidate.png"
    write_mask(golden, base_mask())
    write_mask(candidate, base_mask())
    wrong = contract(golden)
    wrong["mask_spec"]["golden_reference_sha256"] = "d" * 64
    with pytest.raises(module.MeasurementError, match="hash does not match"):
        module.measure_mask(candidate, golden, wrong)
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(module.MeasurementError, match="decode failed"):
        module.measure_mask(corrupt, golden, contract(golden))
    held = contract(golden)
    held["preflight_disposition"] = "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    with pytest.raises(module.MeasurementError, match="not ready"):
        module.measure_mask(candidate, golden, held)
