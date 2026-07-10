from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave70_facial_original_predictions.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("facial_prediction_producer", SCRIPT)
assert spec and spec.loader
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


def save_mask(path: Path, value: int = 0, size: tuple[int, int] = (8, 6)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", size, value).save(path)


def test_parse_ids_accepts_shard_boundaries() -> None:
    assert producer.parse_ids("0,1999,0") == [0, 1999]


def test_parse_ids_rejects_outside_shard() -> None:
    with pytest.raises(ValueError, match="sample_id_out_of_eligible_range"):
        producer.parse_ids("2000")


def test_normalize_materializes_explicit_empty_classes(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    save_mask(raw / "00_background.png", 0)
    save_mask(raw / "01_skin.png", 255)
    save_mask(raw / "14_neck.png", 255)
    destination = tmp_path / "normalized"
    classes, size, empty = producer.normalize_predictions(raw, destination)
    assert size == (8, 6)
    assert classes == list(producer.CLASS_ORDER)
    assert "neck_l" in empty
    assert all((destination / f"{name}.png").is_file() for name in producer.CLASS_ORDER)
    assert Image.open(destination / "neck_l.png").getbbox() is None


def test_normalize_rejects_index_name_mismatch(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    save_mask(raw / "00_background.png", 0)
    save_mask(raw / "02_skin.png", 255)
    with pytest.raises(ValueError, match="route_taxonomy_binding_mismatch"):
        producer.normalize_predictions(raw, tmp_path / "normalized")


def test_prepare_route_input_uses_native_parser_size(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (1024, 1024), (50, 100, 150)).save(source)
    destination = tmp_path / "route.png"
    source_size, route_size = producer.prepare_route_input(source, destination)
    assert source_size == (1024, 1024)
    assert route_size == producer.ROUTE_INPUT_SIZE == (512, 512)
    with Image.open(destination) as prepared:
        assert prepared.size == (512, 512)
        assert prepared.format == "PNG"


def test_prediction_directory_hash_is_stable(tmp_path: Path) -> None:
    save_mask(tmp_path / "b.png", 0)
    save_mask(tmp_path / "a.png", 255)
    assert producer.sha256_directory(tmp_path) == producer.sha256_directory(tmp_path)


def test_protected_neighbors_are_explicit_and_anatomy_aware() -> None:
    assert set(producer.PROTECTED_NEIGHBORS) == set(producer.CLASS_ORDER)
    for class_name, neighbors in producer.PROTECTED_NEIGHBORS.items():
        assert class_name not in neighbors
        assert len(neighbors) == len(set(neighbors))
        assert set(neighbors) <= set(producer.CLASS_ORDER)
    assert "skin" not in producer.PROTECTED_NEIGHBORS["nose"]
    assert "skin" not in producer.PROTECTED_NEIGHBORS["l_eye"]
    assert "neck" not in producer.PROTECTED_NEIGHBORS["neck_l"]
    assert set(producer.PROTECTED_NEIGHBORS["skin"]) != set(producer.CLASS_ORDER) - {"skin"}


def test_producer_source_contains_no_annotation_route_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower().replace("\\", "/")
    assert "mask-anno" not in source
    assert "/labels/" not in source
    assert "/landmarks/" not in source
