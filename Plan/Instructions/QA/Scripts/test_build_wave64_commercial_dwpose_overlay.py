from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_commercial_dwpose_overlay.py"


def _module():
    spec = importlib.util.spec_from_file_location("dwpose_overlay", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _spec(path: Path) -> dict[str, object]:
    module = _module()
    return {"filename": path.name, "bytes": path.stat().st_size, "sha256": module._sha256(path)}


def test_overlay_build_is_exact_offline_and_copy_on_write(tmp_path: Path) -> None:
    module = _module()
    wheelhouse, models = tmp_path / "wheels", tmp_path / "models"
    wheelhouse.mkdir()
    models.mkdir()
    wheel = wheelhouse / "runtime.whl"
    model = models / "pose.onnx"
    wheel.write_bytes(b"wheel")
    model.write_bytes(b"model")
    lock = tmp_path / "lock.json"
    staging = tmp_path / "staging.json"
    node = tmp_path / "node.py"
    lock.write_text(json.dumps({"wheels": [_spec(wheel)]}), encoding="utf-8")
    staging.write_text(json.dumps({"wheels": [_spec(wheel)], "models": [_spec(model)]}), encoding="utf-8")
    node.write_text("NODE_CLASS_MAPPINGS = {}\n", encoding="utf-8")

    def fake_installer(_python: Path, site_packages: Path, wheels: list[Path]) -> None:
        assert wheels == [wheel.resolve()]
        (site_packages / "installed.txt").write_text("offline", encoding="utf-8")

    output = tmp_path / "overlay"
    manifest = module.build_overlay(wheelhouse, models, output, lock, staging, node, installer=fake_installer)
    assert manifest["status"] == "OFFLINE_OVERLAY_BUILT_NOT_IMPORTED"
    assert (output / "site_packages/installed.txt").read_text(encoding="utf-8") == "offline"
    assert (output / "custom_nodes/wave64_commercial_dwpose/models/pose.onnx").read_bytes() == b"model"
    assert json.loads((output / "OVERLAY_MANIFEST.json").read_text(encoding="utf-8"))["authority"]["custom_node_import"] is False
    with pytest.raises(module.OverlayBuildError, match="already exists"):
        module.build_overlay(wheelhouse, models, output, lock, staging, node, installer=fake_installer)


def test_overlay_rejects_extra_or_drifted_artifacts(tmp_path: Path) -> None:
    module = _module()
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel = wheelhouse / "runtime.whl"
    wheel.write_bytes(b"wheel")
    spec = _spec(wheel)
    (wheelhouse / "extra.whl").write_bytes(b"extra")
    with pytest.raises(module.OverlayBuildError, match="set mismatch"):
        module._verify_files(wheelhouse, [spec])
    (wheelhouse / "extra.whl").unlink()
    wheel.write_bytes(b"drift")
    with pytest.raises(module.OverlayBuildError, match="identity mismatch"):
        module._verify_files(wheelhouse, [spec])
