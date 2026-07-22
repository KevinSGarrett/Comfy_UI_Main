from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_layered_python_environment.py"


def _module():
    spec = importlib.util.spec_from_file_location("layered_python_environment", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dist(root: Path, name: str, version: str, requires: list[str] | None = None) -> None:
    dist_info = root / f"{name}-{version}.dist-info"
    dist_info.mkdir(parents=True)
    lines = [f"Name: {name}", f"Version: {version}"]
    lines.extend(f"Requires-Dist: {requirement}" for requirement in requires or [])
    (dist_info / "METADATA").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_layered_metadata_closure_passes_without_importing_packages(tmp_path: Path) -> None:
    module = _module()
    base, overlay = tmp_path / "base", tmp_path / "overlay"
    base.mkdir()
    overlay.mkdir()
    _dist(base, "torch", "2.4.1")
    _dist(base, "PyYAML", "6.0.3")
    _dist(overlay, "timm", "1.0.28", ["torch>=2.0", "PyYAML"])
    result = module.validate_layer(base, overlay, ["timm"])
    assert result["result"] == "PASS"
    assert result["authority"] == {"metadata_dependency_closure": True, "package_import": False, "model_load": False, "gpu_use": False}


def test_layered_metadata_closure_reports_gaps_and_duplicate_names(tmp_path: Path) -> None:
    module = _module()
    base, overlay = tmp_path / "base", tmp_path / "overlay"
    base.mkdir()
    overlay.mkdir()
    _dist(base, "torch", "1.0")
    _dist(overlay, "timm", "1.0.28", ["torch>=2.0", "missing"])
    result = module.validate_layer(base, overlay, ["timm"])
    assert result["result"] == "FAIL"
    assert len(result["errors"]) == 2
    _dist(base, "timm", "1.0.28")
    with pytest.raises(ValueError, match="duplicate distribution"):
        module.validate_layer(base, overlay, ["timm"])
