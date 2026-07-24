from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_deferred_visual_review_dispatcher.py"
BRIDGE_TEST = ROOT / "Plan/Instructions/QA/Scripts/test_run_wave64_deferred_visual_review_bridge.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load(SCRIPT, "w64_visual_review_dispatcher")
BRIDGE = load(BRIDGE_TEST, "w64_visual_review_bridge_test_support")


def dispatch(tmp_path: Path, *, paths: dict[str, Path] | None = None, **kwargs):
    paths = paths or BRIDGE.fixture(tmp_path / "fixture")
    return MODULE.run_dispatcher(
        bridge_path=ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_deferred_visual_review_bridge.py",
        deferred_path=paths["deferred"],
        execution_path=paths["execution"],
        binding_contract_path=paths["binding_contract"],
        binding_seal_path=paths["binding_seal"],
        model_manifest_path=paths["manifest"],
        dispatch_root=tmp_path / "dispatches",
        **kwargs,
    )


def test_blocked_dispatch_seals_one_no_load_timeout(tmp_path: Path) -> None:
    receipt = dispatch(
        tmp_path,
        max_wait_seconds=0,
        poll_interval_seconds=1,
        probe=BRIDGE.blocked_probe,
    )
    assert receipt["state"] == "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000"
    assert receipt["bridge_receipt"] is None
    assert receipt["serverless_submitted"] is False
    assert receipt["event_count"] == 3
    assert not list((tmp_path / "dispatches").rglob("active.lock"))


def test_clean_dispatch_invokes_bridge_once_after_fresh_admission(tmp_path: Path) -> None:
    calls: list[str] = []

    def reviewer(model_id: str, root: Path, items: list[dict]) -> list[dict]:
        calls.append(model_id)
        return [
            {"item_sha256": item["sha256"], "raw_response": f"{model_id}: PASS"}
            for item in items
        ]

    receipt = dispatch(
        tmp_path,
        max_wait_seconds=1,
        poll_interval_seconds=1,
        probe=BRIDGE.clean_probe,
        reviewer=reviewer,
    )
    assert receipt["state"] == "COMPLETED_NONPROMOTING_UNQUALIFIED_REVIEW"
    assert receipt["bridge_receipt"]["gpu_model_load_attempted"] is True
    assert receipt["bridge_receipt"]["gpu_models_loaded"] is True
    assert calls == ["GLM_4_1V_9B_THINKING", "MINICPM_V_4_5_BF16"]


def test_terminal_dispatch_refuses_duplicate_run(tmp_path: Path) -> None:
    paths = BRIDGE.fixture(tmp_path / "fixture")
    kwargs = {
        "max_wait_seconds": 0,
        "poll_interval_seconds": 1,
        "probe": BRIDGE.blocked_probe,
    }
    dispatch(tmp_path, paths=paths, **kwargs)
    with pytest.raises(MODULE.DispatcherError, match="terminal dispatch receipt"):
        dispatch(tmp_path, paths=paths, **kwargs)


def test_restart_before_direct_admission_reuses_verified_journal(tmp_path: Path) -> None:
    paths = BRIDGE.fixture(tmp_path / "fixture")
    source_paths = {
        "bridge": (ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_deferred_visual_review_bridge.py").resolve(),
        "deferred_job": paths["deferred"].resolve(),
        "execution_contract": paths["execution"].resolve(),
        "binding_contract": paths["binding_contract"].resolve(),
        "binding_seal": paths["binding_seal"].resolve(),
        "model_manifest": paths["manifest"].resolve(),
    }
    inputs = MODULE._input_manifest(source_paths)
    job_id = MODULE._job_id(inputs)
    job_root = tmp_path / "dispatches" / job_id
    job_root.mkdir(parents=True)
    MODULE.write_json_new(job_root / "dispatch_contract.json", MODULE._dispatch_contract(job_id, inputs))
    _, _ = MODULE._append_event(
        job_root / "events.jsonl",
        job_id=job_id,
        sequence=0,
        previous_hash=MODULE.GENESIS_HASH,
        event_type="DISPATCH_ADMITTED",
        payload={"max_wait_seconds": 0, "poll_interval_seconds": 1},
        at="2026-07-24T00:00:00Z",
    )
    receipt = dispatch(
        tmp_path,
        paths=paths,
        max_wait_seconds=0,
        poll_interval_seconds=1,
        probe=BRIDGE.blocked_probe,
    )
    assert receipt["state"] == "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000"
    events = (job_root / "events.jsonl").read_text(encoding="utf-8")
    assert "DISPATCH_RESUMED" in events


def test_crash_after_admission_never_retries_model_execution(tmp_path: Path) -> None:
    paths = BRIDGE.fixture(tmp_path / "fixture")
    source_paths = {
        "bridge": (ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_deferred_visual_review_bridge.py").resolve(),
        "deferred_job": paths["deferred"].resolve(),
        "execution_contract": paths["execution"].resolve(),
        "binding_contract": paths["binding_contract"].resolve(),
        "binding_seal": paths["binding_seal"].resolve(),
        "model_manifest": paths["manifest"].resolve(),
    }
    inputs = MODULE._input_manifest(source_paths)
    job_id = MODULE._job_id(inputs)
    job_root = tmp_path / "dispatches" / job_id
    job_root.mkdir(parents=True)
    MODULE.write_json_new(job_root / "dispatch_contract.json", MODULE._dispatch_contract(job_id, inputs))
    _, head = MODULE._append_event(
        job_root / "events.jsonl",
        job_id=job_id,
        sequence=0,
        previous_hash=MODULE.GENESIS_HASH,
        event_type="DISPATCH_ADMITTED",
        payload={"max_wait_seconds": 1, "poll_interval_seconds": 1},
        at="2026-07-24T00:00:00Z",
    )
    MODULE._append_event(
        job_root / "events.jsonl",
        job_id=job_id,
        sequence=1,
        previous_hash=head,
        event_type="DIRECT_ADMISSION_GRANTED",
        payload={"snapshot": BRIDGE.clean_probe()},
        at="2026-07-24T00:00:01Z",
    )
    receipt = dispatch(
        tmp_path,
        paths=paths,
        max_wait_seconds=1,
        poll_interval_seconds=1,
        probe=BRIDGE.clean_probe,
    )
    assert receipt["state"] == "FAILED_DISPATCH_CRASH_AFTER_ADMISSION"
    assert receipt["bridge_receipt"] is None
