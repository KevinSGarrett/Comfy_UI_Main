from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/install_wave64_latentsync_fixture.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_fixture_admission.json"
SPEC = importlib.util.spec_from_file_location("install_latentsync_fixture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def stage_sources(root: Path, value: dict) -> None:
    for role in ("video", "audio"):
        source = ROOT / value[role]["local_path"]
        (root / value[role]["remote_name"]).write_bytes(source.read_bytes())


def test_atomic_fixture_install_and_replay(tmp_path: Path) -> None:
    value = admission()
    source = tmp_path / "source"
    source.mkdir()
    stage_sources(source, value)
    target = tmp_path / "target"
    receipt = tmp_path / "receipt.json"
    first = MODULE.install(value, source, target, receipt, production=False)
    assert first["replay"] == "NEW_ATOMIC_FIXTURE_INSTALL"
    assert first["runtime_claims"]["model_loaded"] is False
    assert first["runtime_claims"]["inference_performed"] is False
    second = MODULE.install(value, source, target, receipt, production=False)
    assert second["replay"] == "REUSED_VERIFIED_FIXTURE"


def test_hash_drift_fails_without_publish(tmp_path: Path) -> None:
    value = admission()
    source = tmp_path / "source"
    source.mkdir()
    stage_sources(source, value)
    (source / value["audio"]["remote_name"]).write_bytes(b"drift")
    target = tmp_path / "target"
    with pytest.raises(MODULE.FixtureInstallError, match="size mismatch"):
        MODULE.install(value, source, target, tmp_path / "receipt.json", production=False)
    assert not target.exists()


def test_existing_unreceipted_target_fails_closed(tmp_path: Path) -> None:
    value = admission()
    source = tmp_path / "source"
    source.mkdir()
    stage_sources(source, value)
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(MODULE.FixtureInstallError, match="without a valid fixture receipt"):
        MODULE.install(value, source, target, tmp_path / "receipt.json", production=False)


def test_runtime_authority_drift_fails_closed(tmp_path: Path) -> None:
    value = admission()
    value["authority"]["inference"] = True
    source = tmp_path / "source"
    source.mkdir()
    stage_sources(source, value)
    with pytest.raises(MODULE.FixtureInstallError, match="exceeds storage authority"):
        MODULE.install(value, source, tmp_path / "target", tmp_path / "receipt.json", production=False)
