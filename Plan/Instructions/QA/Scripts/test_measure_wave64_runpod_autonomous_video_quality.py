from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[4]
MEASURER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_video_quality.py"


def load_measurer():
    spec = importlib.util.spec_from_file_location("w64_aqa_video_measure", MEASURER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(*, width: int = 64, height: int = 48, fps: float = 16, duration: float = 2) -> dict:
    return {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64,
        "modality": "video", "preflight_disposition": "READY_FOR_LEASE",
        "video_spec": {"width": width, "height": height, "fps": fps, "duration_seconds": duration, "sample_policy": "uniform_plus_change_points"},
        "quality_profile": {"hard_gates": [
            {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
            {"gate_id": "duplicates", "metric": "duplicate_sample_fraction", "operator": "lt", "threshold": 0.8, "on_failure": "REPAIR"},
        ]},
    }


def write_video(path: Path, *, static: bool = False, width: int = 64, height: int = 48) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 16, (width, height))
    assert writer.isOpened()
    try:
        for index in range(32):
            y, x = np.indices((height, width))
            shift = 0 if static else index * 3
            frame = np.stack(((x * 4 + shift) % 256, (y * 5 + shift) % 256, ((x + y) * 2 + shift) % 256), axis=-1).astype(np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_video_measurement_is_deterministic_and_selects_spans(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "motion.mp4"
    write_video(path)
    first, second = module.measure_video(path, contract()), module.measure_video(path, contract())
    assert first == second
    assert first["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert len(first["sample_manifest"]) >= 16
    assert {item["category"] for item in first["metric_selected_spans"]} == {"largest_motion", "largest_exposure_jump", "lowest_sharpness"}


def test_geometry_mismatch_fails_implicit_contract_gate(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "motion.mp4"
    write_video(path)
    result = module.measure_video(path, contract(width=128))
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"
    assert next(item for item in result["gate_results"] if item["gate_id"] == "contract-width")["status"] == "FAIL"


def test_static_video_fails_duplicate_gate(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "static.mp4"
    write_video(path, static=True)
    result = module.measure_video(path, contract())
    assert result["metrics"]["duplicate_sample_fraction"] >= 0.8
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_unknown_specialist_metric_fails_closed(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "motion.mp4"
    write_video(path)
    spec = contract()
    spec["quality_profile"]["hard_gates"].append({"gate_id": "identity", "metric": "temporal_identity_similarity", "operator": "gte", "threshold": 0.9, "on_failure": "HOLD"})
    result = module.measure_video(path, spec)
    assert next(item for item in result["gate_results"] if item["gate_id"] == "identity")["status"] == "MEASUREMENT_UNAVAILABLE"
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_corrupt_and_unready_video_are_rejected(tmp_path: Path) -> None:
    module = load_measurer()
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(module.MeasurementError, match="ffprobe failed"):
        module.measure_video(bad, contract())
    path = tmp_path / "motion.mp4"
    write_video(path)
    held = contract()
    held["preflight_disposition"] = "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    with pytest.raises(module.MeasurementError, match="not ready"):
        module.measure_video(path, held)
