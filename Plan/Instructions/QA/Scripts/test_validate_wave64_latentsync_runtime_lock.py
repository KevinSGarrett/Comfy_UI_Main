from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_runtime_lock.py"
SOURCE_PATH = ROOT / "Plan/10_REGISTRIES/Locks/wave64_latentsync_1_6_py311_cu121.pylock.toml"
RUNTIME_PATH = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_wheels.toml"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_runtime_lock", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        tomllib.loads(SOURCE_PATH.read_text(encoding="utf-8")),
        tomllib.loads(RUNTIME_PATH.read_text(encoding="utf-8")),
    )


def test_real_runtime_lock_is_valid() -> None:
    source, runtime = load_inputs()
    assert MODULE.validate(source, runtime, SOURCE_PATH, RUNTIME_PATH) == []


def test_non_source_package_change_fails_closed() -> None:
    source, runtime = load_inputs()
    runtime = copy.deepcopy(runtime)
    next(item for item in runtime["packages"] if item["name"] == "transformers")["version"] = "0"
    assert "transformers: non-source-only package changed" in MODULE.validate(
        source, runtime, SOURCE_PATH, RUNTIME_PATH
    )


def test_local_wheel_hash_mismatch_fails_closed() -> None:
    source, runtime = load_inputs()
    runtime = copy.deepcopy(runtime)
    package = next(item for item in runtime["packages"] if item["name"] == "insightface")
    package["wheels"][0]["hashes"]["sha256"] = "0" * 64
    assert "insightface: local wheel hash or size mismatch" in MODULE.validate(
        source, runtime, SOURCE_PATH, RUNTIME_PATH
    )


def test_source_only_artifact_reintroduction_fails_closed() -> None:
    source, runtime = load_inputs()
    runtime = copy.deepcopy(runtime)
    package = next(item for item in runtime["packages"] if item["name"] == "python-speech-features")
    package["sdist"] = copy.deepcopy(
        next(item for item in source["packages"] if item["name"] == "python-speech-features")["sdist"]
    )
    assert "python-speech-features: runtime artifact must be one local wheel" in MODULE.validate(
        source, runtime, SOURCE_PATH, RUNTIME_PATH
    )
