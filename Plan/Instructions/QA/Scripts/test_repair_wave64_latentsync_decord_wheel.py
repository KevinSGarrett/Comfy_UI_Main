from __future__ import annotations

import copy
import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/repair_wave64_latentsync_decord_wheel.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_decord_0_6_0_wheel_repair_admission.json"
SPEC = importlib.util.spec_from_file_location("repair_latentsync_decord", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_authoritative_admission_is_hash_bound() -> None:
    admission = MODULE.load_admission(ADMISSION)
    assert admission["source"]["sha256"] == MODULE.EXPECTED_SOURCE_SHA256


def test_changed_admission_fails_closed(tmp_path: Path) -> None:
    changed = tmp_path / "admission.json"
    changed.write_text(json.dumps(load_admission()), encoding="utf-8")
    with pytest.raises(MODULE.RepairError, match="admission hash mismatch"):
        MODULE.load_admission(changed)


def test_runtime_authority_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    admission = copy.deepcopy(load_admission())
    admission["authority"]["package_install"] = True
    monkeypatch.setattr(MODULE, "sha256_file", lambda _path: MODULE.EXPECTED_ADMISSION_SHA256)
    monkeypatch.setattr(MODULE.json, "loads", lambda _text: admission)
    with pytest.raises(MODULE.RepairError, match="exceeds wheel repair authority"):
        MODULE.load_admission(ADMISSION)


def test_tag_replacement_changes_only_exact_line() -> None:
    original = b"Wheel-Version: 1.0\n" + MODULE.OLD_TAG + b"\n"
    repaired = original.replace(MODULE.OLD_TAG, MODULE.NEW_TAG)
    assert MODULE.OLD_TAG not in repaired
    assert repaired == b"Wheel-Version: 1.0\n" + MODULE.NEW_TAG + b"\n"


def test_record_regeneration_rehashes_changed_entry() -> None:
    contents = {
        MODULE.WHEEL_PATH: b"changed",
        MODULE.RECORD_PATH: b"",
        "decord/__init__.py": b"value = 1\n",
    }
    original = (
        f"{MODULE.WHEEL_PATH},old,1\n"
        f"decord/__init__.py,old,1\n"
        f"{MODULE.RECORD_PATH},,\n"
    ).encode()
    regenerated = MODULE.regenerate_record(contents, original)
    rows = {row[0]: row[1:] for row in csv.reader(io.StringIO(regenerated.decode()))}
    assert rows[MODULE.WHEEL_PATH] == [MODULE.record_digest(b"changed"), "7"]
    assert rows[MODULE.RECORD_PATH] == ["", ""]


def test_record_verification_allows_explicit_directory_entries() -> None:
    contents = {
        "decord/": b"",
        MODULE.WHEEL_PATH: b"wheel",
        MODULE.RECORD_PATH: b"",
    }
    contents[MODULE.RECORD_PATH] = (
        f"{MODULE.WHEEL_PATH},{MODULE.record_digest(b'wheel')},5\n"
        f"{MODULE.RECORD_PATH},,\n"
    ).encode()
    MODULE.verify_record(contents)


def test_unsafe_member_paths_fail() -> None:
    assert MODULE.safe_member_path("decord/__init__.py")
    assert not MODULE.safe_member_path("../escape")
    assert not MODULE.safe_member_path("/absolute")


def test_tree_manifest_requires_one_regular_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / MODULE.OUTPUT_FILENAME
    wheel.write_bytes(b"wheel")
    assert MODULE.tree_manifest(tmp_path)["file_count"] == 1
    (tmp_path / "extra").write_bytes(b"x")
    with pytest.raises(MODULE.RepairError, match="exactly one regular file"):
        MODULE.tree_manifest(tmp_path)


def test_source_contains_no_install_import_or_gpu_operations() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = ["pip install", "uv pip", "nvidia-smi", "torch.cuda", "import decord"]
    assert all(token not in source for token in forbidden)
