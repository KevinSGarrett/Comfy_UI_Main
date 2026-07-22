from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_latentsync_python_environment.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_dependency_environment_admission.json"
LOCK = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_wheels.toml"
SPEC = importlib.util.spec_from_file_location("build_latentsync_environment", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_authoritative_admission_and_lock_are_hash_bound() -> None:
    admission, lock = MODULE.load_admission(ADMISSION, LOCK)
    assert admission["resolution"]["lock_sha256"] == MODULE.EXPECTED_LOCK_SHA256
    assert len(lock["packages"]) == 149


def test_changed_admission_fails_closed(tmp_path: Path) -> None:
    changed = tmp_path / "admission.json"
    changed.write_text(json.dumps(load_admission()), encoding="utf-8")
    with pytest.raises(MODULE.BuildError, match="admission hash mismatch"):
        MODULE.load_admission(changed, LOCK)


def test_runtime_authority_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    admission = load_admission()
    admission["authority"]["model_load"] = True
    monkeypatch.setattr(MODULE, "sha256_file", lambda path: (
        MODULE.EXPECTED_LOCK_SHA256 if path == LOCK else MODULE.EXPECTED_ADMISSION_SHA256
    ))
    original_loads = MODULE.json.loads
    monkeypatch.setattr(
        MODULE.json,
        "loads",
        lambda text: admission if text.lstrip().startswith("{") else original_loads(text),
    )
    with pytest.raises(MODULE.BuildError, match="forbidden runtime authority"):
        MODULE.load_admission(ADMISSION, LOCK)


def test_target_must_be_exact_lock_address(tmp_path: Path) -> None:
    admission = copy.deepcopy(load_admission())
    admission["targets"]["environment_root"] = (
        "/workspace/w64_aqa/environments/LatentSync-1.6/not-the-lock"
    )
    with pytest.raises(MODULE.BuildError, match="not lock-addressed"):
        MODULE.validate_paths(
            admission,
            Path("/workspace/w64_aqa/control/receipts/latentsync-test.json"),
        )


def test_receipt_must_stay_in_control_root(tmp_path: Path) -> None:
    with pytest.raises(MODULE.BuildError, match="unsafe receipt"):
        MODULE.validate_paths(load_admission(), tmp_path / "receipt.json")


def test_expected_distribution_manifest_is_exact() -> None:
    _, lock = MODULE.load_admission(ADMISSION, LOCK)
    rows = MODULE.expected_distribution_manifest(lock)
    assert len(rows) == 149
    assert {row["name"] for row in rows} >= {"torch", "transformers", "insightface"}


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
    temporary = MODULE.write_receipt_temp(receipt, {"status": "test"})
    temporary.replace(receipt)
    with pytest.raises(MODULE.BuildError, match="already exists"):
        MODULE.write_receipt_temp(receipt, {"status": "changed"})


def test_source_contains_no_gpu_model_or_project_import_operations() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = [
        "nvidia-smi",
        "torch.cuda",
        "from transformers",
        "import transformers",
        "from latentsync",
        "import latentsync",
    ]
    assert all(token not in source for token in forbidden)
