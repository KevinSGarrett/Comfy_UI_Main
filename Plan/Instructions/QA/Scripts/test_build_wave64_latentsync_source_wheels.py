from __future__ import annotations

import importlib.util
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_latentsync_source_wheels.py"
SPEC = importlib.util.spec_from_file_location("build_latentsync_source_wheels", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_safe_member_path_rejects_absolute_and_traversal() -> None:
    assert MODULE.safe_member_path("package/setup.py")
    assert not MODULE.safe_member_path("/package/setup.py")
    assert not MODULE.safe_member_path("package/../setup.py")


def test_static_scan_accepts_declarative_setup(tmp_path: Path) -> None:
    setup = tmp_path / "setup.py"
    setup.write_text("from setuptools import setup\nsetup(name='fixture', version='1')\n", encoding="utf-8")
    assert MODULE.scan_build_script(setup) == []


@pytest.mark.parametrize(
    "source,expected",
    [
        ("import subprocess\n", "import:subprocess"),
        ("import os\nos.system('echo bad')\n", "call:os.system"),
        ("import urllib.request\nurllib.request.urlopen('https://example.invalid')\n", "import:urllib.request"),
    ],
)
def test_static_scan_rejects_process_or_network_build_logic(
    tmp_path: Path, source: str, expected: str
) -> None:
    setup = tmp_path / "setup.py"
    setup.write_text(source, encoding="utf-8")
    assert expected in MODULE.scan_build_script(setup)


def test_wheel_inspection_binds_metadata_record_and_hash(tmp_path: Path) -> None:
    wheel = tmp_path / "fixture-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("fixture/__init__.py", "")
        archive.writestr("fixture-1.0.dist-info/METADATA", "Name: fixture\nVersion: 1.0\n")
        archive.writestr("fixture-1.0.dist-info/RECORD", "")
    observed = MODULE.inspect_wheel(wheel)
    assert observed["name"] == "fixture"
    assert observed["version"] == "1.0"
    assert len(observed["sha256"]) == 64
    assert observed["record_present"] is True
