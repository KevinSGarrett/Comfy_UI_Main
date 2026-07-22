from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_runtime_lock_v2.py"
V1 = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_wheels.toml"
V2 = ROOT / "Plan/10_REGISTRIES/Locks/pylock.wave64_latentsync_1_6_py311_cu121_local_runtime_wheels_v2.toml"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_runtime_lock_v2", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inputs() -> tuple[dict, dict]:
    return (
        tomllib.loads(V1.read_text(encoding="utf-8")),
        tomllib.loads(V2.read_text(encoding="utf-8")),
    )


def test_real_v2_lock_is_valid() -> None:
    v1, v2 = load_inputs()
    assert MODULE.validate(v1, v2, V1, V2) == []


def test_unrelated_package_change_fails_closed() -> None:
    v1, v2 = load_inputs()
    v2 = copy.deepcopy(v2)
    next(item for item in v2["packages"] if item["name"] == "transformers")["version"] = "0"
    assert "transformers: package changed outside decord repair" in MODULE.validate(
        v1, v2, V1, V2
    )


def test_decord_hash_drift_fails_closed() -> None:
    v1, v2 = load_inputs()
    v2 = copy.deepcopy(v2)
    package = next(item for item in v2["packages"] if item["name"] == "decord")
    package["wheels"][0]["hashes"]["sha256"] = "0" * 64
    assert "decord repaired wheel binding mismatch" in MODULE.validate(v1, v2, V1, V2)


def test_remote_host_drift_fails_closed() -> None:
    v1, v2 = load_inputs()
    v2 = copy.deepcopy(v2)
    package = next(item for item in v2["packages"] if item["name"] == "transformers")
    package["wheels"][0]["url"] = "https://example.invalid/transformers.whl"
    assert "v2 remote wheel host allowlist mismatch" in MODULE.validate(v1, v2, V1, V2)
