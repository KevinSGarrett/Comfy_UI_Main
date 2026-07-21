#!/usr/bin/env python3
"""Produce a non-product evidence bundle for live S3 transaction qualification."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py"
JOB_ID = "W64-AQA-JOB-s3-bundle-qualification"


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_s3_qualification_compiler", COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load evidence bundle compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def produce(output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        compiler = load_compiler()
        records_dir = temporary / "records"
        records_dir.mkdir()
        contents = {
            "candidate": b"W64-AQA storage qualification candidate\n",
            "workflow": b"W64-AQA storage qualification workflow\n",
            "measurement": b"W64-AQA storage qualification measurement\n",
            "review_primary": b"W64-AQA storage qualification primary review unavailable\n",
            "review_juror": b"W64-AQA storage qualification independent review unavailable\n",
            "runtime_receipt": b"W64-AQA storage qualification no runtime execution\n",
            "correction_state": b"W64-AQA storage qualification no correction\n",
            "cost_receipt": b"W64-AQA storage qualification bounded object storage only\n",
            "rollback_parent": b"W64-AQA storage qualification rollback parent\n",
        }
        types = {
            "candidate": "candidate", "workflow": "workflow", "measurement": "measurement",
            "review_primary": "review", "review_juror": "review",
            "runtime_receipt": "runtime_receipt", "correction_state": "correction_state",
            "cost_receipt": "cost_receipt", "rollback_parent": "rollback_parent",
        }
        paths = {}
        for name, raw in contents.items():
            path = records_dir / f"{name}.txt"
            path.write_bytes(raw)
            paths[name] = path
        hashes = {name: compiler.sha256_file(path) for name, path in paths.items()}
        specs = [
            {"record_type": types[name], "source_path": str(output / "records" / path.name),
             "durable_relative_path": f"jobs/{JOB_ID}/evidence/{path.name}"}
            for name, path in paths.items()
        ]
        contract = {
            "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64,
            "job_id": JOB_ID, "modality": "image",
            "quality_profile": {"required_approval_roles": [
                "W64-AQA-ROLE-PRIMARY-VISUAL", "W64-AQA-ROLE-INDEPENDENT-JUROR"
            ]},
        }
        decision = {
            "schema_version": "wave64.aqa.decision.v1", "program_id": "W64-AQA",
            "job_id": JOB_ID, "modality": "image",
            "authority": {"host": "runpod", "pod_id": "not-contacted-storage-only", "ec2_forbidden": True, "fail_closed": True},
            "lineage": {"candidate_sha256": hashes["candidate"], "workflow_sha256": hashes["workflow"],
                        "quality_contract_sha256": "a" * 64, "source_sha256": None},
            "measurements": [{"metric_id": "storage-integrity-only", "applicable": True, "passed": True,
                              "implementation_version": "v1", "evidence_sha256": hashes["measurement"]}],
            "reviewers": [
                {"role_id": "W64-AQA-ROLE-PRIMARY-VISUAL", "state": "BLOCKED_UNQUALIFIED",
                 "product_authority": False, "response_valid": False, "observation_sha256": hashes["review_primary"]},
                {"role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR", "state": "BLOCKED_UNQUALIFIED",
                 "product_authority": False, "response_valid": False, "observation_sha256": hashes["review_juror"]},
            ],
            "attempt_state": {"defect_attempt": 0, "total_generation_attempt": 1, "consecutive_no_progress": 0,
                              "ceilings": {"per_defect": 2, "total_generation": 4, "no_progress": 2}},
            "blocking_defects": [{"code": "STORAGE_QUALIFICATION_ONLY", "severity": "blocking",
                                  "detail": "No runtime or semantic product review was performed."}],
            "decision": "BLOCKED", "rollback_parent_sha256": hashes["rollback_parent"],
            "promotion_claimed": False, "cost_usd": 0.0,
            "runtime_receipt_sha256": hashes["runtime_receipt"],
        }
        bundle = compiler.compile_bundle(contract, decision, [
            {**spec, "source_path": str(temporary / "records" / Path(spec["source_path"]).name)} for spec in specs
        ])
        write_json(temporary / "contract.json", contract)
        write_json(temporary / "decision.json", decision)
        write_json(temporary / "records.json", specs)
        write_json(temporary / "bundle.json", bundle)
        write_json(temporary / "packet.json", {
            "schema_version": "wave64.aqa.s3_bundle_qualification_packet.v1",
            "job_id": JOB_ID,
            "bundle_id": bundle["bundle_id"],
            "decision": "BLOCKED",
            "runtime_execution_performed": False,
            "semantic_review_performed": False,
            "product_promotion_granted": False,
            "disposition": "READY_FOR_STORAGE_TRANSACTION_QUALIFICATION_ONLY",
        })
        os.replace(temporary, output)
        return bundle
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        bundle = produce(args.output)
        print(json.dumps({"status": "PASS", "bundle_id": bundle["bundle_id"]}))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
