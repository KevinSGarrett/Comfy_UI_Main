from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_comfyui_main_local_storage_admission.py"
POLICY = ROOT / "Plan/10_REGISTRIES/comfyui_main_local_storage_admission_policy.json"


def load_module():
    spec = importlib.util.spec_from_file_location("local_storage_admission", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_worker_worktree_is_denied_below_25_gib_floor() -> None:
    module = load_module()
    result = module.evaluate(module.load_policy(POLICY), "worker_worktree", 8 * 1024**3)
    assert result["status"] == "DENIED"
    assert result["reasons"] == [
        "FREE_SPACE_BELOW_WORKTREE_ADMISSION_FLOOR",
        "PROJECTED_FREE_SPACE_BELOW_WORKTREE_RESERVE",
    ]


def test_worker_worktree_is_admitted_only_with_before_and_after_reserve() -> None:
    module = load_module()
    result = module.evaluate(module.load_policy(POLICY), "worker_worktree", 30 * 1024**3)
    assert result["status"] == "ADMITTED"
    assert result["projected_free_after_bytes"] == 28 * 1024**3


@pytest.mark.parametrize(
    "operation",
    [
        "docker_start",
        "local_model_download",
        "local_runtime_artifact_materialization",
        "local_dataset_materialization",
    ],
)
def test_runpod_only_operations_are_always_denied(operation: str) -> None:
    module = load_module()
    result = module.evaluate(module.load_policy(POLICY), operation, 100 * 1024**3)
    assert result["status"] == "DENIED"
    assert result["classification"] == "COMFYUI_LOCAL_STORAGE_DENIED_RUNPOD_ONLY"


def test_small_source_edit_is_allowed_above_control_plane_reserve() -> None:
    module = load_module()
    result = module.evaluate(
        module.load_policy(POLICY), "source_edit_test", 8 * 1024**3, 128 * 1024**2
    )
    assert result["status"] == "ADMITTED"


def test_large_source_edit_is_denied_even_with_free_space() -> None:
    module = load_module()
    result = module.evaluate(
        module.load_policy(POLICY), "source_edit_test", 100 * 1024**3, 513 * 1024**2
    )
    assert result["status"] == "DENIED"
    assert result["reasons"] == ["PROJECTED_LOCAL_CONTROL_PLANE_WRITE_EXCEEDS_LIMIT"]


def test_unknown_operation_fails_closed() -> None:
    module = load_module()
    with pytest.raises(module.AdmissionError, match="unsupported local storage operation"):
        module.evaluate(module.load_policy(POLICY), "unknown", 100 * 1024**3)
