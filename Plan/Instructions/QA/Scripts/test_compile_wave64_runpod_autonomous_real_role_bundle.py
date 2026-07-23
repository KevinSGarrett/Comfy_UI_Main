from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_real_role_bundle.py"
)
SPEC = importlib.util.spec_from_file_location("real_role_bundle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_real_role_bundle_is_truthful_and_fails_closed(tmp_path: Path) -> None:
    packet = MODULE.execute(tmp_path / "bundle")
    contract = packet["contract"]
    report = packet["report"]
    assert contract["schema_version"] == "wave64.aqa.campaign.v2"
    assert contract["admission_disposition"] == "BLOCKED_UNQUALIFIED"
    assert report["status"] == "PASS_TRUTHFUL_BINDINGS_BLOCKED_UNQUALIFIED"
    assert report["binding_count"] == 8
    assert report["qualified_component_count"] == 2
    assert report["unqualified_model_role_count"] == 6
    assert report["runpod_contacted"] is False
    assert report["gpu_used"] is False


def test_exact_real_package_and_component_mappings() -> None:
    bindings = {item["role_id"]: item for item in MODULE.build_bindings()}
    assert bindings["W64-AQA-ROLE-CONTROLLER"]["package_id"] == (
        "W64-AQA-PKG-QWEN36-35B-A3B"
    )
    assert bindings["W64-AQA-ROLE-IMPLEMENTER"]["package_id"] == (
        "W64-AQA-PKG-QWEN3-CODER-NEXT"
    )
    assert bindings["W64-AQA-ROLE-REVIEWER"]["package_id"] == (
        "W64-AQA-PKG-QWEN25VL32"
    )
    assert bindings["W64-AQA-ROLE-INDEPENDENT-JUROR"]["package_id"] == (
        "W64-AQA-PKG-INTERNVL35-241B-A28B"
    )
    assert bindings["W64-AQA-ROLE-ARBITER"]["package_id"] == (
        "W64-AQA-PKG-QWEN35-397B-A17B"
    )
    assert bindings["W64-AQA-ROLE-REPAIR-PLANNER"]["package_id"] == (
        "W64-AQA-PKG-QWEN25TEXT7"
    )
    for role_id in (
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-EVIDENCE-COMPILER",
    ):
        binding = bindings[role_id]
        assert binding["binding_kind"] == "CERTIFIED_COMPONENT"
        assert len(binding["certificate_id"]) == 64
        assert len(binding["checkpoint_sha256"]) == 64
        assert len(binding["environment_sha256"]) == 64


def test_unavailable_model_hashes_are_omitted_not_fabricated() -> None:
    bindings = {item["role_id"]: item for item in MODULE.build_bindings()}
    for role_id in (
        "W64-AQA-ROLE-IMPLEMENTER",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
        "W64-AQA-ROLE-ARBITER",
    ):
        binding = bindings[role_id]
        assert binding["qualification_state"] == "UNQUALIFIED"
        assert binding["capacity_state"] == "NOT_MEASURED"
        assert "checkpoint_sha256" not in binding
        assert "environment_sha256" not in binding


def test_missing_real_package_fails_exactly(tmp_path: Path) -> None:
    registry = json.loads(MODULE.ROLE_REGISTRY_PATH.read_text(encoding="utf-8"))
    for role in registry["roles"]:
        if role["role_id"] == "W64-AQA-ROLE-IMPLEMENTER":
            role["package_id"] = "W64-AQA-PKG-ABSENT"
    registry_path = (
        tmp_path
        / MODULE.ROLE_REGISTRY_PATH.relative_to(MODULE.ROOT)
    )
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    inventory_path = (
        tmp_path
        / MODULE.PACKAGE_INVENTORY_PATH.relative_to(MODULE.ROOT)
    )
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_bytes(MODULE.PACKAGE_INVENTORY_PATH.read_bytes())
    with pytest.raises(
        MODULE.RoleBundleError,
        match="model package is absent: W64-AQA-ROLE-IMPLEMENTER",
    ):
        MODULE.build_bindings(tmp_path)
