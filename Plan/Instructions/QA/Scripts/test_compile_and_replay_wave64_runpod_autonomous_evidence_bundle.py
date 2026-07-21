from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py"


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_aqa_evidence_bundle", COMPILER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract() -> dict:
    return {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64,
        "job_id": "W64-AQA-JOB-test", "modality": "image",
        "quality_profile": {"required_approval_roles": ["W64-AQA-ROLE-PRIMARY-VISUAL", "W64-AQA-ROLE-INDEPENDENT-JUROR"]},
    }


def write_record(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def record_specs(module, tmp_path: Path) -> tuple[list[dict], dict[str, str]]:
    sources = {
        "candidate": write_record(tmp_path, "candidate.bin", b"candidate"),
        "workflow": write_record(tmp_path, "workflow.json", b"workflow"),
        "measurement": write_record(tmp_path, "measurement.json", b"measurement"),
        "review_primary": write_record(tmp_path, "review-primary.json", b"review-primary"),
        "review_juror": write_record(tmp_path, "review-juror.json", b"review-juror"),
        "runtime_receipt": write_record(tmp_path, "runtime.json", b"runtime"),
        "correction_state": write_record(tmp_path, "correction.json", b"correction"),
        "cost_receipt": write_record(tmp_path, "cost.json", b"cost"),
        "rollback_parent": write_record(tmp_path, "parent.bin", b"parent"),
    }
    types = {
        "candidate": "candidate", "workflow": "workflow", "measurement": "measurement",
        "review_primary": "review", "review_juror": "review", "runtime_receipt": "runtime_receipt",
        "correction_state": "correction_state", "cost_receipt": "cost_receipt",
        "rollback_parent": "rollback_parent",
    }
    specs = [
        {"record_type": types[name], "source_path": str(path), "durable_relative_path": f"jobs/W64-AQA-JOB-test/evidence/{path.name}"}
        for name, path in sources.items()
    ]
    return specs, {name: module.sha256_file(path) for name, path in sources.items()}


def decision(hashes: dict[str, str], *, recorded: str = "PASS", measurement_pass: bool = True, qualified: bool = True) -> dict:
    reviewer_state = "QUALIFIED" if qualified else "BLOCKED_UNQUALIFIED"
    return {
        "schema_version": "wave64.aqa.decision.v1", "program_id": "W64-AQA",
        "job_id": "W64-AQA-JOB-test", "modality": "image",
        "authority": {"host": "runpod", "pod_id": "pod-test", "ec2_forbidden": True, "fail_closed": True},
        "lineage": {
            "candidate_sha256": hashes["candidate"], "workflow_sha256": hashes["workflow"],
            "quality_contract_sha256": "a" * 64, "source_sha256": None,
        },
        "measurements": [{
            "metric_id": "image-hard-gates", "applicable": True, "passed": measurement_pass,
            "implementation_version": "v1", "evidence_sha256": hashes["measurement"],
        }],
        "reviewers": [
            {"role_id": "W64-AQA-ROLE-PRIMARY-VISUAL", "state": reviewer_state, "product_authority": True, "response_valid": qualified, "observation_sha256": hashes["review_primary"]},
            {"role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR", "state": reviewer_state, "product_authority": True, "response_valid": qualified, "observation_sha256": hashes["review_juror"]},
        ],
        "attempt_state": {
            "defect_attempt": 0, "total_generation_attempt": 1, "consecutive_no_progress": 0,
            "ceilings": {"per_defect": 2, "total_generation": 4, "no_progress": 2},
        },
        "blocking_defects": [] if measurement_pass else [{"code": "IMAGE_GATE", "severity": "blocking", "detail": "gate failed"}],
        "decision": recorded, "rollback_parent_sha256": hashes["rollback_parent"],
        "promotion_claimed": False, "cost_usd": 0.1,
        "runtime_receipt_sha256": hashes["runtime_receipt"],
    }


def test_bundle_compile_and_replay_are_deterministic_and_content_addressed(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    recorded = decision(hashes)
    first = module.compile_bundle(contract(), recorded, specs)
    second = module.compile_bundle(contract(), recorded, specs)
    assert first == second
    assert first["replayed_decision"] == "PASS"
    assert first["replay_disposition"] == "MATCH"
    assert first["promotion_invariants"]["s3_presence_is_acceptance"] is False
    replay = module.replay_bundle(first, contract(), recorded, specs)
    assert replay["replay_disposition"] == "MATCH"
    assert replay["stored_bundle_id"] == replay["recompiled_bundle_id"]


def test_changed_record_causes_replay_mismatch_or_missing_hash(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    recorded = decision(hashes)
    bundle = module.compile_bundle(contract(), recorded, specs)
    Path(specs[2]["source_path"]).write_bytes(b"changed measurement")
    with pytest.raises(module.EvidenceBundleError, match="missing"):
        module.replay_bundle(bundle, contract(), recorded, specs)


def test_recorded_decision_must_match_deterministic_replay(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    wrong = decision(hashes, recorded="PASS", measurement_pass=False)
    with pytest.raises(module.EvidenceBundleError, match="replay mismatch"):
        module.compile_bundle(contract(), wrong, specs)
    blocked = decision(hashes, recorded="BLOCKED", qualified=False)
    assert module.compile_bundle(contract(), blocked, specs)["replayed_decision"] == "BLOCKED"
    repair = decision(hashes, recorded="REPAIR", measurement_pass=False)
    assert module.compile_bundle(contract(), repair, specs)["replayed_decision"] == "REPAIR"


def test_missing_required_record_type_or_referenced_hash_fails_closed(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    without_cost = [entry for entry in specs if entry["record_type"] != "cost_receipt"]
    with pytest.raises(module.EvidenceBundleError, match="missing required record types"):
        module.compile_bundle(contract(), decision(hashes), without_cost)
    without_review = [entry for entry in specs if not entry["source_path"].endswith("review-juror.json")]
    with pytest.raises(module.EvidenceBundleError, match="missing"):
        module.compile_bundle(contract(), decision(hashes), without_review)


def test_promotion_plan_requires_pass_replay_and_integration_authority_and_never_executes(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    bundle = module.compile_bundle(contract(), decision(hashes), specs)
    held = module.plan_promotion(bundle, "comfy-ui-main-runtime-test", "w64-aqa/promotions", None)
    assert held["disposition"] == "HELD_PENDING_INTEGRATION_AUTHORITY"
    assert held["execution_performed"] is False
    ready = module.plan_promotion(bundle, "comfy-ui-main-runtime-test", "w64-aqa/promotions", "b" * 64)
    assert ready["disposition"] == "READY_FOR_INTEGRATION_AUTHORITY_EXECUTION"
    assert ready["execution_performed"] is False
    repair_bundle = module.compile_bundle(contract(), decision(hashes, recorded="REPAIR", measurement_pass=False), specs)
    nonpass = module.plan_promotion(repair_bundle, "comfy-ui-main-runtime-test", "w64-aqa/promotions", "b" * 64)
    assert nonpass["disposition"] == "HELD_NON_PASS_DECISION"


def test_paths_duplicate_records_and_unsupported_authority_decisions_are_rejected(tmp_path: Path) -> None:
    module = load_compiler()
    specs, hashes = record_specs(module, tmp_path)
    unsafe = [dict(entry) for entry in specs]
    unsafe[0]["durable_relative_path"] = "../escape"
    with pytest.raises(module.EvidenceBundleError, match="normalized and relative"):
        module.compile_bundle(contract(), decision(hashes), unsafe)
    duplicate = [dict(entry) for entry in specs]
    duplicate[1]["durable_relative_path"] = duplicate[0]["durable_relative_path"]
    with pytest.raises(module.EvidenceBundleError, match="unique"):
        module.compile_bundle(contract(), decision(hashes), duplicate)
    unsupported = decision(hashes, recorded="REJECT")
    with pytest.raises(module.EvidenceBundleError, match="does not authorize"):
        module.compile_bundle(contract(), unsupported, specs)
