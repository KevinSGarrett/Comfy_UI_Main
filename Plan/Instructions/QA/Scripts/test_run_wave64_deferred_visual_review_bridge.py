from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_deferred_visual_review_bridge.py"


def load():
    spec = importlib.util.spec_from_file_location("w64_visual_review_bridge", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(tmp_path: Path) -> dict[str, Path]:
    artifacts = tmp_path / "runtime_artifacts"
    image = artifacts / "intake-a" / "incoming" / "one.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"one-real-reference-image")
    panel = artifacts / "panel" / "semantic_review_panel.json"
    panel_contract = "a" * 64
    write_json(
        panel,
        {
            "schema": "w64.reference_image_semantic_review_panel.v1",
            "state": "RECORDED_PANEL_READY",
            "contract_sha256": panel_contract,
            "items": [
                {
                    "source_root": "intake-a",
                    "path": "incoming/one.jpg",
                    "sha256": sha(image),
                    "bytes": image.stat().st_size,
                    "width": 10,
                    "height": 10,
                    "format": "JPEG",
                    "mode": "RGB",
                    "frames": 1,
                    "result": "PASS",
                }
            ],
        },
    )
    panel_seal = panel.with_name("semantic_review_panel_seal.json")
    write_json(panel_seal, {"final_sha256": "panel-seal"})
    bindings_root = tmp_path / "bindings"
    models: list[dict] = []
    reviewer_entries: list[dict] = []
    for model_id, role in MODULE.REQUIRED_REVIEWERS.items():
        model_root = tmp_path / "models" / model_id
        model_root.mkdir(parents=True)
        (model_root / "config.json").write_text(model_id, encoding="utf-8")
        tree = MODULE.model_tree(model_root, model_id)
        models.append(tree)
        reviewer_entries.append(
            {"model_id": model_id, "model_tree_sha256": tree["tree_sha256"], "role": role}
        )
    binding_contract = bindings_root / "contract.json"
    write_json(binding_contract, {"contract_sha256": "binding-contract", "models": models})
    binding_seal = bindings_root / "sealed.json"
    write_json(
        binding_seal,
        {
            "final_sha256": "binding-seal",
            "contract_sha256": "binding-contract",
            "model_tree_hashes": {item["model_id"]: item["tree_sha256"] for item in models},
        },
    )
    manifest = bindings_root / "model-tree-manifests.json"
    write_json(manifest, {"models": models})
    execution = tmp_path / "execution.json"
    write_json(
        execution,
        {
            "schema": MODULE.EXECUTION_SCHEMA,
            "state": "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000",
            "authority": "NONPROMOTING_UNQUALIFIED_REVIEW_ONLY",
            "target_pod_id": "a6000-test",
            "input_panel_path": str(panel),
            "input_panel_seal_sha256": "panel-seal",
            "panel_contract_sha256": panel_contract,
            "reviewer_binding_final_sha256": "binding-seal",
            "reviewers": reviewer_entries,
            "admission_conditions": {"minimum_free_vram_mib": 40000},
            "serverless_eligibility": {"eligible": False},
        },
    )
    deferred = tmp_path / "deferred.json"
    write_json(
        deferred,
        {
            "schema": MODULE.DEFERRED_SCHEMA,
            "state": "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000",
            "execution_contract_path": str(execution),
            "execution_contract_sha256": sha(execution),
        },
    )
    return {
        "deferred": deferred,
        "execution": execution,
        "binding_contract": binding_contract,
        "binding_seal": binding_seal,
        "manifest": manifest,
        "image": image,
    }


def blocked_probe() -> dict:
    return {
        "pod_id": "a6000-test",
        "queue_idle": True,
        "gpu_processes": [42],
        "free_mib": 24000,
    }


def clean_probe() -> dict:
    return {
        "pod_id": "a6000-test",
        "queue_idle": True,
        "gpu_processes": [],
        "free_mib": 49000,
    }


def run_paths(paths: dict[str, Path], output: Path, **kwargs):
    return MODULE.run_bridge(
        deferred_path=paths["deferred"],
        execution_path=paths["execution"],
        binding_contract_path=paths["binding_contract"],
        binding_seal_path=paths["binding_seal"],
        model_manifest_path=paths["manifest"],
        output_path=output,
        **kwargs,
    )


def test_foreign_gpu_process_defers_without_loading_models(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    called = False

    def reviewer(*args):
        nonlocal called
        called = True
        return []

    receipt = run_paths(
        paths,
        tmp_path / "blocked.json",
        execute=True,
        probe=blocked_probe,
        reviewer=reviewer,
    )
    assert receipt["state"] == "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000"
    assert set(receipt["deferral_reasons"]) == {
        "FOREIGN_GPU_PROCESS_PRESENT",
        "INSUFFICIENT_FREE_VRAM",
    }
    assert receipt["gpu_models_loaded"] is False
    assert called is False
    assert json.loads((tmp_path / "blocked.json").read_text(encoding="utf-8"))["receipt_sha256"] == receipt["receipt_sha256"]


def test_clean_check_is_ready_but_does_not_load_models(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    receipt = run_paths(paths, tmp_path / "ready.json", execute=False, probe=clean_probe)
    assert receipt["state"] == "READY_FOR_EXCLUSIVE_LOCAL_A6000_REVIEW"
    assert receipt["gpu_models_loaded"] is False
    assert receipt["input_item_count"] == 1


def test_execute_rechecks_bound_trees_and_runs_reviewers_sequentially(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    calls: list[str] = []

    def reviewer(model_id: str, root: Path, items: list[dict]) -> list[dict]:
        calls.append(model_id)
        assert root.is_dir()
        return [{"item_sha256": item["sha256"], "raw_response": f"{model_id}: PASS"} for item in items]

    receipt = run_paths(
        paths,
        tmp_path / "complete.json",
        execute=True,
        probe=clean_probe,
        reviewer=reviewer,
    )
    assert receipt["state"] == "COMPLETED_NONPROMOTING_UNQUALIFIED_REVIEW"
    assert receipt["gpu_models_loaded"] is True
    assert calls == ["GLM_4_1V_9B_THINKING", "MINICPM_V_4_5_BF16"]
    assert receipt["authority"] == "NONPROMOTING_UNQUALIFIED_REVIEW_ONLY"
    assert receipt["serverless_submitted"] is False


def test_tampered_panel_artifact_fails_closed(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    paths["image"].write_bytes(b"tampered")
    with pytest.raises(MODULE.BridgeError, match="artifact is missing or changed"):
        run_paths(paths, tmp_path / "never.json", execute=False, probe=clean_probe)


def test_output_receipt_is_immutable(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    output = tmp_path / "fixed.json"
    run_paths(paths, output, execute=False, probe=clean_probe)
    with pytest.raises(MODULE.BridgeError, match="already exists"):
        run_paths(paths, output, execute=False, probe=clean_probe)
