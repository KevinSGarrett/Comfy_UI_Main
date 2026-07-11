from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave70_lapa_insightface_landmarks.py"
SPEC = importlib.util.spec_from_file_location("lapa_insightface_producer", SCRIPT)
assert SPEC and SPEC.loader
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


def face(bbox: list[float], score: float, point_count: int = 106) -> dict:
    return {
        "bbox": np.asarray(bbox, dtype=np.float32),
        "det_score": score,
        "landmark_2d_106": np.zeros((point_count, 2), dtype=np.float32),
    }


def test_parse_stems_is_unique_and_rejects_paths() -> None:
    assert producer.parse_stems("a,b,a") == ["a", "b"]
    with pytest.raises(ValueError, match="sample_stem_invalid"):
        producer.parse_stems("../bad")


def test_primary_face_uses_largest_bbox_then_score() -> None:
    small = face([0, 0, 10, 10], 0.99)
    large_low = face([0, 0, 20, 20], 0.50)
    large_high = face([0, 0, 20, 20], 0.80)
    assert producer.choose_primary_face([small, large_low, large_high]) is large_high
    assert producer.choose_primary_face([]) is None


def test_route_configuration_hash_binds_settings_and_assets() -> None:
    assets = [{"name": name, "sha256": value} for name, value in producer.MODEL_HASHES.items()]
    first = producer.route_configuration_sha256("1" * 64, assets)
    second = producer.route_configuration_sha256("2" * 64, assets)
    assert first != second
    assert len(first) == 64


def test_model_verifier_rejects_missing_asset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="insightface_model_missing"):
        producer.verify_model_assets(tmp_path)


def test_source_contains_no_gold_annotation_route_access() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower().replace("\\", "/")
    assert "mask-anno" not in source
    assert "/labels/" not in source
    assert "/landmarks/" not in source
