import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/"
    "activate_wave64_wav2vec2_phoneme_aligner_environment.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("phoneme_environment_activation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(os.name == "nt", reason="Windows test user lacks symlink privilege")
def test_exact_binding_is_created_and_reused(tmp_path: Path) -> None:
    module = load_module()
    data_path = tmp_path / "environment" / "espeak-ng-data"
    data_path.mkdir(parents=True)
    binding = tmp_path / "embedded" / "share" / "espeak-ng-data"

    assert module.ensure_exact_binding(binding, data_path) == "CREATED_EXACT_BINDING"
    assert binding.is_symlink()
    assert binding.resolve() == data_path.resolve()
    assert module.ensure_exact_binding(binding, data_path) == "REUSED_EXACT_BINDING"


@pytest.mark.skipif(os.name == "nt", reason="Windows test user lacks symlink privilege")
def test_exact_binding_refuses_foreign_target(tmp_path: Path) -> None:
    module = load_module()
    expected = tmp_path / "expected"
    foreign = tmp_path / "foreign"
    expected.mkdir()
    foreign.mkdir()
    binding = tmp_path / "binding"
    binding.symlink_to(foreign, target_is_directory=True)

    with pytest.raises(module.ActivationError, match="another target"):
        module.ensure_exact_binding(binding, expected)


def test_exact_binding_refuses_non_symlink_occupant(tmp_path: Path) -> None:
    module = load_module()
    data_path = tmp_path / "data"
    data_path.mkdir()
    binding = tmp_path / "binding"
    binding.mkdir()

    with pytest.raises(module.ActivationError, match="non-symlink"):
        module.ensure_exact_binding(binding, data_path)


def test_environment_root_requires_allowed_parent_and_lock_name(tmp_path: Path) -> None:
    module = load_module()
    allowed = tmp_path / "allowed"
    root = allowed / module.LOCK_SHA256
    root.mkdir(parents=True)

    assert module.validate_environment_root(root, allowed) == root.resolve()

    wrong_hash = allowed / "wrong-hash"
    wrong_hash.mkdir()
    with pytest.raises(module.ActivationError, match="lock hash"):
        module.validate_environment_root(wrong_hash, allowed)


def test_environment_root_refuses_escape(tmp_path: Path) -> None:
    module = load_module()
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    escaped = tmp_path / module.LOCK_SHA256
    escaped.mkdir()

    with pytest.raises(module.ActivationError, match="escapes"):
        module.validate_environment_root(escaped, allowed)
