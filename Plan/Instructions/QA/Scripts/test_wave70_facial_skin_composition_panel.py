from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/render_wave70_facial_skin_composition_panel.py"
spec = importlib.util.spec_from_file_location("skin_panel", SCRIPT)
assert spec and spec.loader
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


def test_collect_samples_requires_composition_contract(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": [{"sample_id": "1"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="skin_composition_contract_missing:1"):
        panel.collect_samples([manifest])


def test_collect_samples_preserves_manifest_order(tmp_path: Path) -> None:
    paths = []
    for index, ids in enumerate((("0", "1"), ("6",))):
        path = tmp_path / f"manifest-{index}.json"
        samples = [
            {"sample_id": sample_id, "composition": {"composition_rule_id": "celeb_skin_nested_union_v1"}}
            for sample_id in ids
        ]
        path.write_text(json.dumps({"samples": samples}), encoding="utf-8")
        paths.append(path)
    assert [sample["sample_id"] for sample in panel.collect_samples(paths)] == ["0", "1", "6"]


def test_error_overlay_uses_red_for_false_positive_and_blue_for_false_negative() -> None:
    source = Image.new("RGB", (2, 1), (0, 0, 0))
    gold = Image.new("L", (2, 1), 0)
    prediction = Image.new("L", (2, 1), 0)
    gold.putpixel((0, 0), 255)
    prediction.putpixel((1, 0), 255)
    result = panel.error_overlay(source, gold, prediction)
    left = result.getpixel((0, 0))
    right = result.getpixel((1, 0))
    assert left[2] > left[0]
    assert right[0] > right[2]


def test_render_writes_five_column_panel(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source = project / "source/0.jpg"
    base = project / "base/0"
    prediction = project / "prediction/0"
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0/00000_skin.png"
    source.parent.mkdir(parents=True)
    base.mkdir(parents=True)
    prediction.mkdir(parents=True)
    gold.parent.mkdir(parents=True)
    Image.new("RGB", (4, 4), (30, 60, 90)).save(source)
    Image.new("L", (4, 4), 255).save(base / "skin.png")
    Image.new("L", (4, 4), 255).save(prediction / "skin.png")
    Image.new("L", (4, 4), 255).save(gold)
    sample = {
        "sample_id": "0",
        "source_path": str(source),
        "prediction_path": str(prediction),
        "composition": {"base_prediction_path": str(base)},
    }
    out = tmp_path / "panel.png"
    panel.render(project, [sample], out)
    with Image.open(out) as rendered:
        assert rendered.size == (panel.TILE[0] * 5, 68 + panel.TILE[1] + 34)
