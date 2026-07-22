from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_aqa_deterministic_role_qualification.py"
EVIDENCE = ROOT / "Plan/Tracker/Evidence/W64_AQA_DETERMINISTIC_ROLE_QUALIFICATION_20260722T163804Z"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_aqa_deterministic_role", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_in_bundle_replays_without_executing_held_out() -> None:
    module = load_module()
    result = module.validate(ROOT, EVIDENCE)
    assert result == {
        "status": "PASS",
        "bundle_id": "f385abbb1b4eda4b7ccd84f2b277818b782a167fd48eedb4c6724d60c9464253",
        "certificate_id": "81329165d759a60fc0b112dff3b606163a38bffa48b9c0f4d90a0ee4400296a1",
    }


def test_partition_counts_threshold_freeze_and_certificate_scope() -> None:
    bundle = json.loads((EVIDENCE / "execution_bundle.json").read_text(encoding="utf-8"))
    report = json.loads((EVIDENCE / "qualification_report.json").read_text(encoding="utf-8"))
    certificate = json.loads((EVIDENCE / "qualification_certificate.json").read_text(encoding="utf-8"))
    assert len(bundle["calibration_runs"]) == 8
    assert len(bundle["held_out_runs"]) == 5
    assert all(run["run_index"] == 1 for run in bundle["held_out_runs"])
    assert bundle["threshold_freeze"]["frozen"] is True
    assert report["execution_matrix_sha256"] == bundle["inputs"]["matrix"]["sha256"]
    assert certificate["qualification_disposition"] == "QUALIFIED_FOR_DECLARED_SCOPE"
    assert certificate["metrics"]["repeatability_rate"] == 1
    assert certificate["metrics"]["held_out_run_count"] == 5
    assert certificate["operational_authority_granted"] is True
    assert bundle["authority"]["visual_semantics"] is False
    assert bundle["authority"]["promotion"] is False


def test_validation_rejects_repeated_held_out_and_decision_tamper(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, copied)
    bundle_path = copied / "execution_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["held_out_runs"].append(bundle["held_out_runs"][0])
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(Exception):
        module.validate(ROOT, copied)
    shutil.rmtree(copied)
    shutil.copytree(EVIDENCE, copied)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["calibration_runs"][0]["decision"]["reason_code"] = "TAMPERED"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(module.DeterministicQualificationError, match="bundle identity mismatch|decision identity mismatch"):
        module.validate(ROOT, copied)


def test_execute_refuses_existing_output_before_any_reexecution() -> None:
    module = load_module()
    with pytest.raises(module.DeterministicQualificationError, match="already exists"):
        module.execute(ROOT, EVIDENCE)
