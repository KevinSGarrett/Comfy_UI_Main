from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/qualify_wave64_runpod_evidence_compiler_role.py"
EVIDENCE = ROOT / "Plan/Tracker/Evidence/W64_AQA_EVIDENCE_COMPILER_ROLE_QUALIFICATION_20260722T235000Z"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_aqa_evidence_compiler_role", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_in_bundle_replays_without_held_out_execution() -> None:
    module = load_module()
    result = module.validate(ROOT, EVIDENCE)
    assert result["status"] == "PASS"
    assert len(result["bundle_id"]) == 64
    assert len(result["certificate_id"]) == 64


def test_partitions_scope_and_zero_gpu_authority() -> None:
    bundle = json.loads((EVIDENCE / "execution_bundle.json").read_text(encoding="utf-8"))
    certificate = json.loads((EVIDENCE / "qualification_certificate.json").read_text(encoding="utf-8"))
    assert len(bundle["calibration_runs"]) == 8
    assert len(bundle["held_out_runs"]) == 5
    assert all(run["run_index"] == 1 for run in bundle["held_out_runs"])
    assert bundle["threshold_freeze"]["frozen"] is True
    assert bundle["capacity"]["peak_vram_gb"] == 0
    assert certificate["qualification_disposition"] == "QUALIFIED_FOR_DECLARED_SCOPE"
    assert certificate["metrics"]["false_accept_rate"] == 0
    assert certificate["metrics"]["false_reject_rate"] == 0
    assert certificate["metrics"]["repeatability_rate"] == 1
    assert certificate["metrics"]["refusal_correctness_rate"] == 1
    assert bundle["authority"]["content_agnostic_evidence_compilation"] is True
    assert all(value is False for key, value in bundle["authority"].items() if key != "content_agnostic_evidence_compilation")


def test_exact_failure_assertions_for_tamper_and_scope(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, copied)
    bundle_path = copied / "execution_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["held_out_runs"][0]["decision"]["reason_code"] = "TAMPERED"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(module.EvidenceCompilerQualificationError, match="bundle identity mismatch"):
        module.validate(ROOT, copied)
    shutil.rmtree(copied)
    shutil.copytree(EVIDENCE, copied)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["authority"]["git"] = True
    bundle["bundle_id"] = module.ZERO_HASH
    bundle["bundle_id"] = module.content_hash(bundle)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(jsonschema.ValidationError, match="False was expected"):
        module.validate(ROOT, copied)


def test_cas_escape_is_refused_before_external_write(tmp_path: Path) -> None:
    module = load_module()
    executor_module = module.import_file(ROOT / module.EXECUTOR_PATH, "campaign_executor_escape_test")
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    executor = executor_module.CampaignExecutor(module._contract(executor_module), workspace, executor_module.MemoryLeaseAdapter())
    executor.cas = outside
    with pytest.raises(ValueError, match="escaped workspace"):
        executor._store(b"no escape")
    assert not outside.exists()


def test_execute_refuses_existing_output() -> None:
    module = load_module()
    with pytest.raises(module.EvidenceCompilerQualificationError, match="already exists"):
        module.execute(ROOT, EVIDENCE)
