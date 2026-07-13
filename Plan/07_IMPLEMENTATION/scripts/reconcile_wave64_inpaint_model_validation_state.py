from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
LANE_ID = "sdxl_realvisxl_inpaint_detail_lane"
QUEUE_ID = "MRQ-20260707-005"
RECORD_ID = "MODEL-REALVISXL-V50-INPAINT-DETAIL-CHECKPOINT-001"
CERTIFICATE = PLAN / "Instructions/QA/Evidence/Done_Certifications/W66_INPAINT_BOUNDED_TARGET_RUNTIME_SMOKE_CERTIFICATE_20260711T031500-0500.json"
RUNTIME = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_SMOKE_SELECTED_INPAINT_20260710T220500-0500.json"
VISUAL = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W66_SELECTED_INPAINT_TARGET_RUNTIME_VISUAL_QA_20260710T212500-0500.json"
QUEUE = PLAN / "Registries/Models/model_runtime_validation_queue.csv"
REGISTRY = PLAN / "Registries/Models/model_registry.jsonl"
CONTRACT = PLAN / "10_REGISTRIES/model_asset_storage_cache_contract.json"
EVIDENCE_DIR = PLAN / "Instructions/QA/Evidence/Model_Registry"
TRACKER_EVIDENCE_DIR = PLAN / "Tracker/Evidence/Model_Registry"
TZ = ZoneInfo("America/Chicago")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(value, encoding="utf-8", newline="")
    os.replace(temp, path)


def atomic_write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, indent=2) + "\n")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify_authority() -> tuple[dict[str, object], dict[str, object], dict[str, object], list[str]]:
    certificate = read_json(CERTIFICATE)
    runtime = read_json(RUNTIME)
    visual = read_json(VISUAL)
    failures: list[str] = []

    require(certificate.get("lane_id") == LANE_ID, "certificate_lane_mismatch", failures)
    require(certificate.get("result") == "bounded_target_runtime_smoke_certified_with_notes", "certificate_result_mismatch", failures)
    require(certificate.get("final_decision") == "pass_bounded_smoke_scope_only", "certificate_decision_mismatch", failures)
    require(certificate.get("closes_prior_runtime_blockers") is True, "certificate_does_not_close_prior_runtime_blockers", failures)
    require(certificate.get("bounded_target_runtime_smoke_certificate") is True, "bounded_certificate_flag_missing", failures)
    require(certificate.get("final_lane_certification") is False, "certificate_false_full_lane_boundary_missing", failures)
    require(certificate.get("full_route_certification") is False, "certificate_false_full_route_boundary_missing", failures)
    require(certificate.get("mask_promotion_allowed") is False, "certificate_mask_boundary_missing", failures)
    require(certificate.get("wave71_activation_allowed") is False, "certificate_wave71_boundary_missing", failures)

    require(runtime.get("lane_id") == LANE_ID, "runtime_lane_mismatch", failures)
    require(runtime.get("result") == "workflow_smoke_generation_complete", "runtime_result_mismatch", failures)
    require(runtime.get("generation_executed") is True, "runtime_generation_not_executed", failures)
    require(runtime.get("execute_gates_pass") is True, "runtime_execute_gates_failed", failures)
    require(runtime.get("final_state") == "stopped", "runtime_final_state_not_stopped", failures)
    require(not runtime.get("errors"), "runtime_errors_present", failures)
    static_proof = runtime.get("ec2_static_proof")
    require(isinstance(static_proof, dict) and static_proof.get("valid") is True, "runtime_static_proof_invalid", failures)
    require(isinstance(static_proof, dict) and static_proof.get("lane_match") is True, "runtime_static_proof_lane_mismatch", failures)
    remote_result = runtime.get("remote_result")
    prompt_response = remote_result.get("prompt_response") if isinstance(remote_result, dict) else None
    require(isinstance(prompt_response, dict) and not prompt_response.get("node_errors"), "runtime_prompt_node_errors_present", failures)

    require(visual.get("qa_status") == "pass_target_runtime_smoke_with_notes", "visual_qa_result_mismatch", failures)
    require(visual.get("target_runtime_generation_confirmed") is True, "visual_generation_not_confirmed", failures)
    require(visual.get("target_runtime_pullback_confirmed") is True, "visual_pullback_not_confirmed", failures)
    require(visual.get("selected_lane_smoke_complete") is True, "visual_selected_lane_smoke_not_complete", failures)
    require(visual.get("mask_promotion_allowed") is False, "visual_mask_boundary_missing", failures)
    require(visual.get("full_route_certification_allowed") is False, "visual_full_route_boundary_missing", failures)
    require(visual.get("wave71_activation_allowed") is False, "visual_wave71_boundary_missing", failures)
    require(visual.get("runtime_evidence") == rel(RUNTIME), "visual_runtime_evidence_mismatch", failures)

    return certificate, runtime, visual, failures


def reconcile(apply_changes: bool) -> dict[str, object]:
    certificate, runtime, visual, failures = verify_authority()
    if failures:
        raise SystemExit("authority verification failed: " + ", ".join(failures))

    before_hashes = {rel(path): sha256_file(path) for path in (QUEUE, REGISTRY, CONTRACT)}
    with QUEUE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        queue_fields = reader.fieldnames or []
        queue_rows = list(reader)
    queue_matches = [row for row in queue_rows if row.get("queue_id") == QUEUE_ID and row.get("workflow_lane") == LANE_ID]
    if len(queue_matches) != 1:
        raise SystemExit(f"expected one inpaint queue row, found {len(queue_matches)}")
    if queue_matches[0].get("status") not in {"queued", "runtime_smoke_complete"}:
        raise SystemExit(f"unexpected inpaint queue status: {queue_matches[0].get('status')}")

    registry_lines = REGISTRY.read_text(encoding="utf-8-sig").splitlines()
    registry_records = [json.loads(line) for line in registry_lines if line.strip()]
    registry_matches = [record for record in registry_records if record.get("record_id") == RECORD_ID and record.get("workflow_lane") == LANE_ID]
    if len(registry_matches) != 1:
        raise SystemExit(f"expected one inpaint registry record, found {len(registry_matches)}")
    registry_record = registry_matches[0]
    if registry_record.get("runtime_validation_status") not in {"queued", "runtime_smoke_complete"}:
        raise SystemExit(f"unexpected inpaint registry status: {registry_record.get('runtime_validation_status')}")

    contract = read_json(CONTRACT)
    for key in ("runtime_action_allowed", "model_download_allowed", "promotion_allowed", "full_project_completion_implied"):
        if contract.get(key) is not False:
            raise SystemExit(f"contract safety boundary is not false: {key}")

    now = datetime.now(TZ)
    iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    evidence_paths = [rel(CERTIFICATE), rel(RUNTIME), rel(VISUAL)]

    queue_matches[0]["status"] = "runtime_smoke_complete"
    queue_matches[0]["evidence_path"] = rel(CERTIFICATE)

    registry_record.update({
        "updated_at": iso,
        "storage_location": "local_and_target_runtime_validated",
        "compatibility_status": "bounded_target_runtime_smoke_validated",
        "qa_status": "target_runtime_smoke_pass_with_notes",
        "runtime_validation_status": "runtime_smoke_complete",
        "visual_impact": "One bounded no-mouth-v4 target-runtime smoke passed with notes; full-lane quality and robustness remain uncertified.",
        "known_issues": [
            "Only one target-runtime sample is certified.",
            "The diagnostic facial mask is a runtime input and is not promoted or treated as gold truth.",
            "Changed workflow, model, source, mask, prompt, or scene requires scope-matched reproof.",
        ],
        "last_tested_at": str(certificate.get("timestamp", "")),
        "evidence_paths": evidence_paths,
    })

    contract["current_inventory_expectation"] = {
        "registry_records": 15,
        "validation_queue_rows": 15,
        "runtime_smoke_complete": 9,
        "local_generation_smoke_complete": 5,
        "queued": 1,
    }
    contract["current_blockers"] = [
        blocker for blocker in contract.get("current_blockers", [])
        if isinstance(blocker, dict) and blocker.get("lane_id") != LANE_ID
    ]
    contract["current_decision"] = "static_governance_pass_required_model_presence_and_inpaint_state_reconciled"

    if apply_changes:
        queue_text_lines: list[str] = []
        from io import StringIO

        buffer = StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=queue_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(queue_rows)
        queue_text_lines.append(buffer.getvalue())
        atomic_write_text(QUEUE, "".join(queue_text_lines))

        registry_output = "\n".join(json.dumps(record, separators=(",", ":")) for record in registry_records) + "\n"
        atomic_write_text(REGISTRY, registry_output)
        atomic_write_json(CONTRACT, contract)

    after_hashes = {
        rel(path): sha256_file(path) if apply_changes else before_hashes[rel(path)]
        for path in (QUEUE, REGISTRY, CONTRACT)
    }
    changed_paths = [path for path in before_hashes if before_hashes[path] != after_hashes[path]]
    result = {
        "schema_version": "1.0",
        "evidence_id": f"INPAINT_MODEL_VALIDATION_STATE_RECONCILIATION_{stamp}",
        "created_iso": iso,
        "wave": 64,
        "tracker_id": "TRK-W64-007",
        "item_id": "ITEM-W64-007",
        "lane_id": LANE_ID,
        "result": "applied_runtime_smoke_complete" if apply_changes else "dry_run_authority_pass",
        "authority_checks": {
            "certificate": "pass_bounded_scope_only",
            "runtime": "pass_generation_complete_final_state_stopped",
            "visual_qa": "pass_target_runtime_smoke_with_notes",
            "failure_count": 0,
        },
        "state_transition": {
            "queue_id": QUEUE_ID,
            "registry_record_id": RECORD_ID,
            "prior_allowed_states": ["queued", "runtime_smoke_complete"],
            "current_state": "runtime_smoke_complete",
            "inventory_distribution": {"runtime_smoke_complete": 9, "local_generation_smoke_complete": 5, "queued": 1},
        },
        "source_evidence": [
            {"path": path, "sha256": sha256_file(ROOT / path)} for path in evidence_paths
        ],
        "mutated_paths": changed_paths,
        "before_hashes": before_hashes,
        "after_hashes": after_hashes,
        "boundaries": {
            "full_lane_certification": False,
            "full_route_certification": False,
            "mask_truth_consumed": False,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "new_generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "comfyui_contacted": False,
        },
        "next_action": "Run the Row007 owner once; do not rerun the selected-inpaint runtime smoke.",
    }
    if apply_changes:
        evidence_path = EVIDENCE_DIR / f"{result['evidence_id']}.json"
        mirror_path = TRACKER_EVIDENCE_DIR / evidence_path.name
        result["evidence_paths"] = [rel(evidence_path), rel(mirror_path)]
        atomic_write_json(evidence_path, result)
        atomic_write_json(mirror_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile stale selected-inpaint model validation state from bounded target-runtime proof.")
    parser.add_argument("--apply", action="store_true", help="Apply the guarded registry, queue, and Row007 contract mutation.")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.apply), indent=2))


if __name__ == "__main__":
    main()
