from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_and_evaluate_wave64_runpod_autonomous_role_qualification.py"
CATEGORIES = ["known_good", "known_bad", "borderline", "adversarial", "refusal", "identity", "temporal", "audio_mask", "workflow"]


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_aqa_role_qualification", COMPILER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report() -> dict:
    fixtures = []
    for index, category in enumerate(CATEGORIES):
        expected = "PASS" if category == "known_good" else "REFUSE" if category == "refusal" else "FAIL"
        partition = "calibration" if index < 4 else "held_out"
        runs = [
            {"disposition": expected, "schema_valid": True, "output_sha256": f"{index + 1:x}" * 64},
            {"disposition": expected, "schema_valid": True, "output_sha256": f"{index + 1:x}" * 64},
        ] if partition == "calibration" else [
            {"disposition": expected, "schema_valid": True, "output_sha256": f"{index + 1:x}" * 64},
        ]
        fixtures.append({
            "fixture_id": f"fixture-{category}", "category": category,
            "partition": partition,
            "expected_disposition": expected,
            "runs": runs,
        })
    return {
        "schema_version": "wave64.aqa.role_qualification_report.v1",
        "report_id": "W64-AQA-QUAL-test-001", "role_id": "W64-AQA-ROLE-PRIMARY-VISUAL",
        "model_id": "model-test", "checkpoint_sha256": "a" * 64,
        "runtime_digest": "b" * 64, "prompt_sha256": "c" * 64, "corpus_sha256": "d" * 64,
        "execution_matrix_sha256": "e" * 64,
        "issued_at": "2026-07-21T00:00:00Z", "expires_at": "2026-08-21T00:00:00Z",
        "scope": {"modalities": ["image"], "max_width": 2048, "max_height": 2048, "max_duration_seconds": 0, "quantization": "int4", "gpu_profile": "2xA40"},
        "capacity": {"passed": True, "peak_vram_gb": 40, "max_vram_gb": 48, "peak_ram_gb": 70, "max_ram_gb": 100, "p95_latency_seconds": 12, "max_latency_seconds": 30},
        "thresholds": {"max_false_accept_rate": 0, "max_false_reject_rate": 0, "max_invalid_schema_rate": 0, "min_repeatability_rate": 1, "min_refusal_correctness_rate": 1, "max_behavior_metric_delta": 0},
        "fixtures": fixtures,
    }


def test_complete_capacity_and_quality_report_qualifies_deterministically() -> None:
    module = load_compiler()
    first, second = module.compile_certificate(report()), module.compile_certificate(report())
    assert first == second
    assert first["qualification_disposition"] == "QUALIFIED_FOR_DECLARED_SCOPE"
    assert first["operational_authority_granted"] is True
    assert set(first["coverage_categories"]) == set(CATEGORIES)
    assert first["metrics"]["calibration_fixture_count"] == 4
    assert first["metrics"]["held_out_fixture_count"] == 5
    assert first["metrics"]["held_out_run_count"] == 5
    assert first["metrics"]["repeatability_fixture_count"] == 4


def test_refusal_only_scope_never_grants_operational_role_authority() -> None:
    module = load_compiler()
    value = report()
    value["authority_scope"] = "REFUSAL_DISCIPLINE_SCOPE_ONLY"
    for fixture in value["fixtures"]:
        fixture["expected_disposition"] = "REFUSE"
        for run in fixture["runs"]:
            run["disposition"] = "REFUSE"
    certificate = module.compile_certificate(value)
    assert certificate["authority_scope"] == "REFUSAL_DISCIPLINE_SCOPE_ONLY"
    assert certificate["qualification_disposition"] == "QUALIFIED_REFUSAL_DISCIPLINE_SCOPE_ONLY"
    assert certificate["operational_authority_granted"] is False


def test_missing_coverage_capacity_false_accept_schema_and_repeatability_fail() -> None:
    module = load_compiler()
    missing = report()
    missing["fixtures"] = missing["fixtures"][:-1]
    assert "REQUIRED_FIXTURE_COVERAGE_INCOMPLETE" in module.compile_certificate(missing)["reason_codes"]
    capacity = report()
    capacity["capacity"]["peak_vram_gb"] = 60
    assert "CAPACITY_OR_LATENCY_QUALIFICATION_FAILED" in module.compile_certificate(capacity)["reason_codes"]
    bad = report()
    bad["fixtures"][1]["runs"][0]["disposition"] = "PASS"
    bad["fixtures"][2]["runs"][0]["schema_valid"] = False
    certificate = module.compile_certificate(bad)
    assert {"FALSE_ACCEPT_RATE_EXCEEDED", "STRUCTURED_OUTPUT_RELIABILITY_FAILED", "REPEATABILITY_FAILED"}.issubset(certificate["reason_codes"])
    assert certificate["operational_authority_granted"] is False


def test_unchanged_qualified_report_remains_active_before_expiration() -> None:
    module = load_compiler()
    baseline = module.compile_certificate(report())
    decision = module.evaluate_drift(baseline, report(), "2026-07-22T00:00:00Z")
    assert decision["disposition"] == "ACTIVE_SCOPE_UNCHANGED"
    assert decision["scope_operational"] is True


def test_fingerprint_scope_behavior_and_expiration_drift_suspend_scope() -> None:
    module = load_compiler()
    baseline = module.compile_certificate(report())
    fingerprint = report()
    fingerprint["runtime_digest"] = "e" * 64
    assert module.evaluate_drift(baseline, fingerprint, "2026-07-22T00:00:00Z")["disposition"] == "SUSPEND_FINGERPRINT_DRIFT"
    scope = report()
    scope["scope"]["max_width"] = 4096
    assert module.evaluate_drift(baseline, scope, "2026-07-22T00:00:00Z")["disposition"] == "SUSPEND_SCOPE_DRIFT"
    behavior = report()
    behavior["fixtures"][1]["runs"][0]["disposition"] = "PASS"
    assert module.evaluate_drift(baseline, behavior, "2026-07-22T00:00:00Z")["disposition"] == "SUSPEND_BEHAVIOR_DRIFT"
    assert module.evaluate_drift(baseline, report(), "2026-08-21T00:00:00Z")["disposition"] == "SUSPEND_EXPIRED"


def test_partition_discipline_rejects_single_calibration_and_repeated_held_out() -> None:
    module = load_compiler()
    single_calibration = report()
    single_calibration["fixtures"][0]["runs"] = single_calibration["fixtures"][0]["runs"][:1]
    with pytest.raises(module.QualificationError, match="calibration fixtures require at least two runs"):
        module.compile_certificate(single_calibration)
    repeated_held_out = report()
    repeated_held_out["fixtures"][4]["runs"].append(copy.deepcopy(repeated_held_out["fixtures"][4]["runs"][0]))
    with pytest.raises(module.QualificationError, match="held-out fixtures must execute exactly once"):
        module.compile_certificate(repeated_held_out)


def test_matrix_identity_drift_suspends_scope() -> None:
    module = load_compiler()
    baseline = module.compile_certificate(report())
    changed = report()
    changed["execution_matrix_sha256"] = "f" * 64
    assert module.evaluate_drift(baseline, changed, "2026-07-22T00:00:00Z")["disposition"] == "SUSPEND_FINGERPRINT_DRIFT"


def test_failed_baseline_never_becomes_operational() -> None:
    module = load_compiler()
    failed_report = report()
    failed_report["capacity"]["passed"] = False
    baseline = module.compile_certificate(failed_report)
    decision = module.evaluate_drift(baseline, report(), "2026-07-22T00:00:00Z")
    assert decision["disposition"] == "SUSPEND_BASELINE_NOT_QUALIFIED"
    assert decision["scope_operational"] is False


def test_certificate_is_bound_to_report_and_current_report_is_not_mutated() -> None:
    module = load_compiler()
    current = report()
    baseline = module.compile_certificate(current)
    before = copy.deepcopy(current)
    module.evaluate_drift(baseline, current, "2026-07-22T00:00:00Z")
    assert current == before
    changed = copy.deepcopy(current)
    changed["fixtures"][0]["runs"][0]["output_sha256"] = "f" * 64
    assert module.compile_certificate(changed)["report_sha256"] != baseline["report_sha256"]
