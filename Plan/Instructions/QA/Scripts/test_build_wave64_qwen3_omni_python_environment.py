from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_qwen3_omni_python_environment.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_omni_dependency_environment_admission.json"
SPEC = importlib.util.spec_from_file_location("build_qwen3_omni_environment", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_authoritative_admission_is_hash_bound() -> None:
    admission = MODULE.load_admission(ADMISSION)
    assert admission["resolution"]["lock_sha256"] == MODULE.EXPECTED_LOCK_SHA256


def test_changed_admission_fails_closed(tmp_path: Path) -> None:
    changed = tmp_path / "admission.json"
    changed.write_text(json.dumps(load_admission()), encoding="utf-8")
    with pytest.raises(MODULE.BuildError, match="admission hash mismatch"):
        MODULE.load_admission(changed)


def test_runtime_authority_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    admission = load_admission()
    admission["authority"]["model_library_import"] = True
    monkeypatch.setattr(MODULE, "sha256_file", lambda _path: MODULE.EXPECTED_ADMISSION_SHA256)
    monkeypatch.setattr(MODULE.json, "loads", lambda _text: admission)
    with pytest.raises(MODULE.BuildError, match="forbidden runtime authority"):
        MODULE.load_admission(ADMISSION)


def test_target_must_be_exact_lock_address(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    admission = copy.deepcopy(load_admission())
    admission["targets"]["environment_root"] = "/workspace/w64_aqa/environments/Qwen3-Omni-30B-A3B-Thinking/not-the-lock"
    lock = tmp_path / "lock.toml"
    lock.write_text("x", encoding="utf-8")
    monkeypatch.setattr(MODULE, "sha256_file", lambda _path: MODULE.EXPECTED_LOCK_SHA256)
    with pytest.raises(MODULE.BuildError, match="not lock-addressed"):
        MODULE.validate_paths(admission, lock, Path("/workspace/w64_aqa/control/receipt.json"))


def test_receipt_must_stay_in_control_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE, "sha256_file", lambda _path: MODULE.EXPECTED_LOCK_SHA256)
    with pytest.raises(MODULE.BuildError, match="unsafe receipt"):
        MODULE.validate_paths(load_admission(), tmp_path / "lock", tmp_path / "receipt.json")


def test_distribution_gate_checks_count_and_key_versions() -> None:
    rows = [{"name": name, "version": version} for name, version in MODULE.EXPECTED_KEY_DISTRIBUTIONS.items()]
    rows.extend({"name": f"package-{index}", "version": "1"} for index in range(75 - len(rows)))
    MODULE.validate_distributions(rows)
    rows[0]["version"] = "0"
    with pytest.raises(MODULE.BuildError, match="version mismatch"):
        MODULE.validate_distributions(rows)


def test_uv_identity_accepts_platform_suffix_but_not_another_version() -> None:
    MODULE.validate_uv_identity("uv 0.11.30 (x86_64-unknown-linux-gnu)")
    with pytest.raises(MODULE.BuildError, match="uv version mismatch"):
        MODULE.validate_uv_identity("uv 0.11.29 (x86_64-unknown-linux-gnu)")


def test_tree_manifest_is_deterministic_and_symlink_aware(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.txt").write_text("bb", encoding="utf-8")
    first = MODULE.tree_manifest(tmp_path)
    second = MODULE.tree_manifest(tmp_path)
    assert first == second
    assert first["regular_file_count"] == 2
    assert first["total_regular_file_bytes"] == 3


def test_receipt_write_is_no_overwrite(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    MODULE.write_receipt(receipt, {"status": "test"})
    with pytest.raises(MODULE.BuildError, match="already exists"):
        MODULE.write_receipt(receipt, {"status": "changed"})
    assert json.loads(receipt.read_text(encoding="utf-8"))["status"] == "test"


def test_source_contains_no_gpu_or_model_import_operations() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = ["nvidia-smi", "torch.cuda", "from transformers", "import transformers", "Qwen3Omni"]
    assert all(token not in source for token in forbidden)
