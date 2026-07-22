from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_internvl_dependency_overlay.py"


def _module():
    spec = importlib.util.spec_from_file_location("internvl_environment_overlay", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path):
    module = _module()
    base = tmp_path / "base"
    site = base / "lib/python3.12/site-packages"
    (base / "bin").mkdir(parents=True)
    site.mkdir(parents=True)
    (base / "bin/python").write_bytes(b"python")
    (base / "pyvenv.cfg").write_text("include-system-site-packages = false\n", encoding="utf-8")
    (site / "transformers-5.2.0.dist-info").mkdir()
    (site / "transformers/models/qwen3").mkdir(parents=True)
    (site / "transformers/models/qwen3/modeling_qwen3.py").write_bytes(b"qwen3")
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel = wheelhouse / "addon.whl"
    wheel.write_bytes(b"wheel")
    lock_material = {
        "base_environment": {
            "root": str(base.resolve()),
            "required_paths": ["transformers-5.2.0.dist-info", "transformers/models/qwen3/modeling_qwen3.py"],
        },
        "wheels": [{"filename": wheel.name, "bytes": wheel.stat().st_size, "sha256": module._sha256(wheel)}],
    }
    output = tmp_path / "overlay"
    admission = tmp_path / "admission.json"
    admission.write_text(
        json.dumps({"lock_material": lock_material, "lock_sha256": module._canonical_sha256(lock_material), "target_root": str(output.resolve())}),
        encoding="utf-8",
    )
    return module, admission, wheelhouse, output, base


def test_overlay_builds_atomically_without_mutating_or_importing_base(tmp_path: Path) -> None:
    module, admission, wheelhouse, output, base = _fixture(tmp_path)
    before = sorted(path.relative_to(base).as_posix() for path in base.rglob("*"))

    def fake_installer(python: Path, target: Path, wheels: list[Path]) -> None:
        assert python == (base / "bin/python").resolve()
        assert [path.name for path in wheels] == ["addon.whl"]
        (target / "addon.py").write_bytes(b"installed")

    manifest = module.build_overlay(admission, wheelhouse, output, installer=fake_installer)
    assert manifest["status"] == "IMMUTABLE_ADDON_OVERLAY_BUILT_NOT_IMPORTED"
    assert manifest["authority"] == {"offline_addon_install": True, "base_environment_mutated": False, "custom_code_import": False, "model_load": False, "gpu_use": False}
    assert (output / "site_packages/addon.py").read_bytes() == b"installed"
    assert before == sorted(path.relative_to(base).as_posix() for path in base.rglob("*"))
    with pytest.raises(module.EnvironmentOverlayError, match="already exists"):
        module.build_overlay(admission, wheelhouse, output, installer=fake_installer)


def test_overlay_rejects_lock_wheel_and_system_site_drift(tmp_path: Path) -> None:
    module, admission, wheelhouse, output, base = _fixture(tmp_path)
    data = json.loads(admission.read_text(encoding="utf-8"))
    data["lock_material"]["wheels"][0]["bytes"] += 1
    admission.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(module.EnvironmentOverlayError, match="lock digest"):
        module.build_overlay(admission, wheelhouse, output)
    data["lock_sha256"] = module._canonical_sha256(data["lock_material"])
    admission.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(module.EnvironmentOverlayError, match="wheel identity"):
        module.build_overlay(admission, wheelhouse, output)
    data["lock_material"]["wheels"][0]["bytes"] -= 1
    data["lock_sha256"] = module._canonical_sha256(data["lock_material"])
    admission.write_text(json.dumps(data), encoding="utf-8")
    (base / "pyvenv.cfg").write_text("include-system-site-packages = true\n", encoding="utf-8")
    with pytest.raises(module.EnvironmentOverlayError, match="exclude system"):
        module.build_overlay(admission, wheelhouse, output)


def test_pure_wheel_extractor_rejects_unsafe_member(tmp_path: Path) -> None:
    module = _module()
    python = tmp_path / "python"
    python.write_bytes(b"")
    target = tmp_path / "target"
    target.mkdir()
    good = tmp_path / "good-1.0-py3-none-any.whl"
    with zipfile.ZipFile(good, "w") as archive:
        archive.writestr("good/__init__.py", "VALUE = 1\n")
        archive.writestr("good-1.0.dist-info/WHEEL", "Root-Is-Purelib: true\nTag: py3-none-any\n")
    module._offline_install(python, target, [good])
    assert (target / "good/__init__.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    unsafe = tmp_path / "unsafe-1.0-py3-none-any.whl"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../escape.py", "bad\n")
        archive.writestr("unsafe-1.0.dist-info/WHEEL", "Root-Is-Purelib: true\nTag: py3-none-any\n")
    with pytest.raises(module.EnvironmentOverlayError, match="unsafe wheel member"):
        module._offline_install(python, target, [unsafe])
