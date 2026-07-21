#!/usr/bin/env python3
"""Produce retained local evidence for typed copy-on-write workflow candidate staging."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_RECEIPT_BOUND_SHADOW_20260721T231000Z"
STAGER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/stage_wave64_runpod_autonomous_workflow_candidate.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
JOB_ID = "W64-AQA-JOB-workflow-receipt-shadow"


class CandidateEvidenceError(ValueError):
    """Raised when retained candidate-staging evidence cannot be built exactly."""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CandidateEvidenceError(f"cannot load component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CandidateEvidenceError(f"JSON root must be an object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def produce(output: Path, source_head: str, generated_at_utc: str) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise CandidateEvidenceError("output already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        source_job = SOURCE_ROOT / "jobs" / JOB_ID
        target_job = temporary / "jobs" / JOB_ID
        shutil.copytree(source_job / "inputs", target_job / "inputs")
        (target_job / "proposals").mkdir()
        (target_job / "candidates").mkdir()
        (temporary / "requests").mkdir()
        (temporary / "decisions").mkdir()
        (temporary / "receipts").mkdir()
        shutil.copy2(SOURCE_ROOT / "input_receipt_bundle.json", target_job / "inputs" / "input_receipt_bundle.json")

        stager = _load(STAGER_PATH, "w64_candidate_evidence_stager")
        validator = stager._load_component(stager.VALIDATOR_PATH, "w64_candidate_evidence_validator")
        workflow = _read(target_job / "inputs" / "workflow.json")
        contract = _read(target_job / "inputs" / "contract.json")
        patch = {
            "schema_version": "wave64.aqa.workflow_patch.v1",
            "patch_id": "W64-AQA-PATCH-retained-candidate-staging",
            "base_workflow_sha256": validator.content_hash(workflow),
            "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
            "operations": [{
                "operation": "replace_bounded_numeric",
                "node_id": "2",
                "input_name": "cfg",
                "expected_old_value": 7.0,
                "new_value": 6.5,
            }],
        }
        patch_path = target_job / "proposals" / "workflow.patch.json"
        _write(patch_path, patch)
        request = {
            "schema_version": "wave64.aqa.tool_gateway_request.v1",
            "request_id": "W64-AQA-TOOL-candidate-write-retained",
            "job_id": JOB_ID,
            "actor_role_id": "W64-AQA-ROLE-CONTROLLER",
            "authority_binding_sha256": contract["contract_id"],
            "execution_mode": "shadow_qualification",
            "action_type": "candidate_write",
            "target": f"jobs/{JOB_ID}/candidates/workflow.candidate.json",
            "parameters": {},
        }
        gateway = _load(GATEWAY_PATH, "w64_candidate_evidence_gateway")
        decision = gateway.evaluate_request(request)
        base_path = target_job / "inputs" / "workflow.json"
        base_before = hashlib.sha256(base_path.read_bytes()).hexdigest()
        receipt = stager.stage_candidate(request, decision, temporary)
        base_after = hashlib.sha256(base_path.read_bytes()).hexdigest()
        if base_before != base_after:
            raise CandidateEvidenceError("base workflow changed during retained staging")
        _write(temporary / "requests" / "candidate_write.request.json", request)
        _write(temporary / "decisions" / "candidate_write.decision.json", decision)
        _write(temporary / "receipts" / "candidate_write.receipt.json", receipt)

        manifest: dict[str, str] = {}
        for path in sorted(temporary.rglob("*")):
            if path.is_file():
                manifest[path.relative_to(temporary).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence = {
            "schema_version": "wave64.aqa.workflow_candidate_staging_evidence.v1",
            "program_id": "W64-AQA",
            "evidence_id": "W64-AQA-WORKFLOW-CANDIDATE-STAGING-20260721T232803Z",
            "source_head": source_head,
            "generated_at_utc": generated_at_utc,
            "job_id": JOB_ID,
            "authority_binding_sha256": contract["contract_id"],
            "input_receipt_bundle_id": _read(target_job / "inputs" / "input_receipt_bundle.json")["bundle_id"],
            "candidate_staging_receipt_id": receipt["receipt_id"],
            "base_file_sha256_before": base_before,
            "base_file_sha256_after": base_after,
            "candidate_file_sha256": receipt["candidate_file_sha256"],
            "copy_on_write_verified": base_before == base_after,
            "runtime_claims": {
                "runpod_contacted": False,
                "gpu_used": False,
                "comfyui_execution_performed": False,
                "model_inference_performed": False,
                "candidate_staging_write_performed": True,
                "base_input_write_performed": False,
                "network_used": False,
                "production_promotion_granted": False
            },
            "disposition": "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGING_ONLY",
            "remaining_unqualified": [
                "comfyui_sandbox_execution",
                "regression.workflow.v1",
                "coder_patch_proposal",
                "production_candidate_write",
                "product_promotion"
            ],
            "file_manifest_sha256": manifest,
        }
        _write(temporary / "evidence.json", evidence)
        os.replace(temporary, output)
        return evidence
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("source_head")
    parser.add_argument("generated_at_utc")
    args = parser.parse_args()
    try:
        print(json.dumps(produce(args.output, args.source_head, args.generated_at_utc), indent=2, sort_keys=True))
    except (CandidateEvidenceError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
