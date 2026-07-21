from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_s3_bundle_transaction.py"
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}
        self.put_order: list[str] = []

    def head(self, bucket: str, key: str):
        value = self.objects.get((bucket, key))
        return copy.deepcopy(value) if value else None

    def put_if_absent(self, bucket: str, key: str, source: Path, content_sha256: str, bundle_id: str) -> bool:
        identity = (bucket, key)
        if identity in self.objects:
            return False
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == content_sha256
        self.put_order.append(key)
        self.objects[identity] = {
            "ContentLength": len(raw),
            "ChecksumSHA256": base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii"),
            "ServerSideEncryption": "AES256",
            "VersionId": f"version-{len(self.put_order)}",
            "Metadata": {"content-sha256": content_sha256, "bundle-id": bundle_id},
        }
        return True


def qualification_fixture(tmp_path: Path):
    compiler = load(COMPILER_PATH, "w64_s3_bundle_fixture_compiler")
    contents = {
        "candidate": b"candidate", "workflow": b"workflow", "measurement": b"measurement",
        "review_primary": b"review-primary", "review_juror": b"review-juror",
        "runtime_receipt": b"runtime", "correction_state": b"correction",
        "cost_receipt": b"cost", "rollback_parent": b"parent",
    }
    types = {
        "candidate": "candidate", "workflow": "workflow", "measurement": "measurement",
        "review_primary": "review", "review_juror": "review",
        "runtime_receipt": "runtime_receipt", "correction_state": "correction_state",
        "cost_receipt": "cost_receipt", "rollback_parent": "rollback_parent",
    }
    paths = {}
    for name, raw in contents.items():
        path = tmp_path / f"{name}.bin"
        path.write_bytes(raw)
        paths[name] = path
    hashes = {name: compiler.sha256_file(path) for name, path in paths.items()}
    specs = [
        {"record_type": types[name], "source_path": str(path),
         "durable_relative_path": f"jobs/W64-AQA-JOB-s3-qualification/evidence/{path.name}"}
        for name, path in paths.items()
    ]
    contract = {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64,
        "job_id": "W64-AQA-JOB-s3-qualification", "modality": "image",
        "quality_profile": {"required_approval_roles": [
            "W64-AQA-ROLE-PRIMARY-VISUAL", "W64-AQA-ROLE-INDEPENDENT-JUROR"
        ]},
    }
    decision = {
        "schema_version": "wave64.aqa.decision.v1", "program_id": "W64-AQA",
        "job_id": contract["job_id"], "modality": "image",
        "authority": {"host": "runpod", "pod_id": "pod-storage-qualification", "ec2_forbidden": True, "fail_closed": True},
        "lineage": {"candidate_sha256": hashes["candidate"], "workflow_sha256": hashes["workflow"],
                    "quality_contract_sha256": "a" * 64, "source_sha256": None},
        "measurements": [{"metric_id": "storage-fixture", "applicable": True, "passed": True,
                          "implementation_version": "v1", "evidence_sha256": hashes["measurement"]}],
        "reviewers": [
            {"role_id": "W64-AQA-ROLE-PRIMARY-VISUAL", "state": "QUALIFIED", "product_authority": True,
             "response_valid": True, "observation_sha256": hashes["review_primary"]},
            {"role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR", "state": "QUALIFIED", "product_authority": True,
             "response_valid": True, "observation_sha256": hashes["review_juror"]},
        ],
        "attempt_state": {"defect_attempt": 0, "total_generation_attempt": 1, "consecutive_no_progress": 0,
                          "ceilings": {"per_defect": 2, "total_generation": 4, "no_progress": 2}},
        "blocking_defects": [], "decision": "PASS", "rollback_parent_sha256": hashes["rollback_parent"],
        "promotion_claimed": False, "cost_usd": 0.0, "runtime_receipt_sha256": hashes["runtime_receipt"],
    }
    return compiler.compile_bundle(contract, decision, specs), contract, decision, specs


def test_full_bundle_stages_objects_then_manifest_and_replays(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_s3_bundle_success")
    bundle, contract, decision, specs = qualification_fixture(tmp_path)
    client = FakeS3()
    first = module.execute_bundle_transaction(bundle, contract, decision, specs, client, "a" * 40)
    assert first["disposition"] == "PASS_VERIFIED_RESUMABLE_S3_BUNDLE_STAGING_ONLY"
    assert first["created_object_count"] == len(first["objects"]) + 1
    assert first["reused_object_count"] == 0
    assert client.put_order[-1].endswith("/bundle.json")
    assert first["s3_presence_is_acceptance"] is False
    assert first["product_promotion_granted"] is False
    second = module.execute_bundle_transaction(bundle, contract, decision, specs, client, "a" * 40)
    assert second["created_object_count"] == 0
    assert second["reused_object_count"] == len(second["objects"]) + 1


def test_crash_before_manifest_resumes_by_verified_reuse(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_s3_bundle_resume")
    bundle, contract, decision, specs = qualification_fixture(tmp_path)
    client = FakeS3()
    with pytest.raises(module.BundleTransactionError, match="INJECTED_CRASH"):
        module.execute_bundle_transaction(
            bundle, contract, decision, specs, client, "b" * 40, inject_crash_after_objects=2
        )
    assert len(client.objects) == 2
    receipt = module.execute_bundle_transaction(bundle, contract, decision, specs, client, "b" * 40)
    assert receipt["reused_object_count"] == 2
    assert receipt["created_object_count"] == len(receipt["objects"]) - 1
    assert receipt["manifest_written_last"] is True


def test_existing_tampered_object_and_source_change_fail_closed(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_s3_bundle_tamper")
    bundle, contract, decision, specs = qualification_fixture(tmp_path)
    client = FakeS3()
    module.execute_bundle_transaction(bundle, contract, decision, specs, client, "c" * 40)
    identity = next(iter(client.objects))
    client.objects[identity]["Metadata"]["content-sha256"] = "f" * 64
    with pytest.raises(module.BundleTransactionError, match="METADATA_HASH_MISMATCH"):
        module.execute_bundle_transaction(bundle, contract, decision, specs, client, "c" * 40)
    Path(specs[0]["source_path"]).write_bytes(b"changed")
    with pytest.raises(Exception, match="missing|match"):
        module.execute_bundle_transaction(bundle, contract, decision, specs, FakeS3(), "c" * 40)


def test_policy_weakening_and_bad_source_head_fail_closed(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_s3_bundle_policy")
    bundle, contract, decision, specs = qualification_fixture(tmp_path)
    policy = module._load_json(module.POLICY_PATH)
    weakened = copy.deepcopy(policy)
    weakened["overwrite_allowed"] = True
    with pytest.raises(module.BundleTransactionError, match="changed or weakened"):
        module.execute_bundle_transaction(bundle, contract, decision, specs, FakeS3(), "d" * 40, policy=weakened)
    with pytest.raises(module.BundleTransactionError, match="40-character"):
        module.execute_bundle_transaction(bundle, contract, decision, specs, FakeS3(), "short")
