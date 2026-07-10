from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave70_facial_original_predictions.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("facial_prediction_producer", SCRIPT)
assert spec and spec.loader
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)

RUNNER_SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave70_facial_bisenet_inference.py"
runner_spec = importlib.util.spec_from_file_location("facial_bisenet_runner", RUNNER_SCRIPT)
assert runner_spec and runner_spec.loader
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)


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


def test_skin_composition_unions_nested_classes_and_preserves_sources(tmp_path: Path) -> None:
    base = tmp_path / "base"
    for class_name in producer.CLASS_ORDER:
        save_mask(base / f"{class_name}.png", 0)
    save_mask(base / "nose.png", 255)
    output = tmp_path / "output"
    record = producer.materialize_composition(base, output, "skin_nested_union_v1")
    assert record is not None
    assert record["union_sources"] == list(producer.SKIN_UNION_SOURCES)
    assert Image.open(output / "skin.png").getbbox() == (0, 0, 8, 6)
    assert producer.sha256_file(base / "nose.png") == producer.sha256_file(output / "nose.png")
    assert producer.sha256_file(base / "skin.png") == record["base_skin_sha256_preserved"]


def test_skin_composition_fails_when_base_class_is_missing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    for class_name in producer.CLASS_ORDER:
        if class_name != "hat":
            save_mask(base / f"{class_name}.png", 0)
    with pytest.raises(FileNotFoundError, match="base_prediction_class_missing:hat"):
        producer.materialize_composition(base, tmp_path / "output", "skin_nested_union_v1")


def test_configuration_hash_binds_component_order_and_content(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    baseline = producer.sha256_files([first, second])
    assert baseline != producer.sha256_files([second, first])
    second.write_text("changed", encoding="utf-8")
    assert baseline != producer.sha256_files([first, second])


def test_route_specs_keep_single_pass_default_separate_from_tta(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model.pth"
    single = producer.build_route_spec("single_pass", tmp_path / "input", tmp_path / "output", checkpoint)
    tta = producer.build_route_spec("hflip_logit_mean", tmp_path / "input", tmp_path / "output", checkpoint)
    assert single["route_id"] == "face_parsing.segment.evaluate"
    assert single["inference_metadata"] == {
        "mode": "single_pass", "logit_fusion": "none", "spatial_unflip": False, "semantic_channel_swaps": []
    }
    assert len(single["configuration_components"]) == 1
    assert tta["route_id"] == "run_wave70_facial_bisenet_inference"
    assert tta["inference_metadata"]["mode"] == "hflip_logit_mean"
    assert tta["inference_metadata"]["spatial_unflip"] is True
    assert len(tta["configuration_components"]) == 2
    assert str(producer.TTA_RUNNER) in tta["command"]


def test_ear_multiscale_route_is_fixed_and_ear_only(tmp_path: Path) -> None:
    route = producer.build_route_spec(
        "ear_multiscale_union_v1", tmp_path / "input", tmp_path / "output", tmp_path / "model.pth"
    )
    metadata = route["inference_metadata"]
    assert metadata["scales"] == [384, 512, 640]
    assert metadata["canonical_grid"] == [512, 512]
    assert metadata["target_classes"] == ["l_ear", "r_ear", "ear_r"]
    assert metadata["non_target_masks_preserved_from_scale"] == 512
    assert metadata["gold_exposed_to_route"] is False
    assert "ear_multiscale_union_v1" in route["command"]


def test_ear_overrides_preserve_non_target_masks(tmp_path: Path) -> None:
    parsing = np.array([[1, 1, 7], [17, 8, 0]], dtype=np.uint8)
    overrides = {
        7: np.array([[False, True, True], [False, False, False]]),
        8: np.array([[False, False, False], [False, True, True]]),
        9: np.array([[False, False, False], [True, False, False]]),
    }
    runner.save_masks(parsing, tmp_path, "sample", overrides)
    sample = tmp_path / "masks/sample"
    assert np.array_equal(np.asarray(Image.open(sample / "01_skin.png")) > 0, parsing == 1)
    assert np.array_equal(np.asarray(Image.open(sample / "17_hair.png")) > 0, parsing == 17)
    assert np.array_equal(np.asarray(Image.open(sample / "07_l_ear.png")) > 0, overrides[7])
    assert np.array_equal(np.asarray(Image.open(sample / "09_ear_r.png")) > 0, overrides[9])


def test_ear_multiscale_inference_returns_canonical_non_target_logits() -> None:
    class ScaleTaggedNet(runner.torch.nn.Module):
        def forward(self, tensor):
            size = tensor.shape[-1]
            logits = runner.torch.zeros((1, len(runner.CLASS_NAMES), size, size), dtype=tensor.dtype)
            tagged_class = {384: 7, 512: 1, 640: 8}[size]
            logits[:, tagged_class] = 2.0
            return (logits,)

    tensor = runner.torch.zeros((1, 3, 512, 512), dtype=runner.torch.float32)
    canonical_logits, ear_masks = runner.infer_ear_multiscale_masks(ScaleTaggedNet(), tensor)
    canonical_parsing = canonical_logits.argmax(dim=1).squeeze(0).numpy()
    assert canonical_logits.shape == (1, len(runner.CLASS_NAMES), 512, 512)
    assert np.all(canonical_parsing == 1)
    assert np.all(ear_masks[7])
    assert np.all(ear_masks[8])
    assert not np.any(ear_masks[9])


def test_ear_override_rejects_wrong_shape(tmp_path: Path) -> None:
    parsing = np.zeros((2, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="override_mask_shape_mismatch"):
        runner.save_masks(parsing, tmp_path, "sample", {7: np.zeros((3, 2), dtype=bool)})


def test_route_spec_rejects_unknown_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported_inference_mode"):
        producer.build_route_spec("unknown", tmp_path / "input", tmp_path / "output", tmp_path / "model")


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
