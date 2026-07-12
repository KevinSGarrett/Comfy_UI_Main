from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(r"C:\Comfy_UI_Main")
REGISTRY = ROOT / "Plan/Registries/Models/model_registry.jsonl"
QUEUE = ROOT / "Plan/Registries/Models/model_runtime_validation_queue.csv"
TZ = ZoneInfo("America/Chicago")

TARGET_LANES = {
    "sdxl_realvisxl_controlnet_depth_lane": "Plan/Instructions/QA/Evidence/Done_Certifications/W66_DEPTH_LANE_FINAL_CERTIFICATION_20260711T000500-0500.json",
    "sdxl_realvisxl_controlnet_lineart_lane": "Plan/Instructions/QA/Evidence/Done_Certifications/W66_LINEART_LANE_FINAL_CERTIFICATION_20260711T004700-0500.json",
}


def main() -> None:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    records = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    updated_records = 0
    for record in records:
        lane = record.get("workflow_lane")
        if lane not in TARGET_LANES:
            continue
        record["updated_at"] = now
        record["compatibility_status"] = "runtime_smoke_validated"
        record["runtime_validation_status"] = "runtime_smoke_complete"
        record["qa_status"] = "pass_with_notes_for_runtime_smoke"
        evidence = list(record.get("evidence_paths") or [])
        if TARGET_LANES[lane] not in evidence:
            evidence.append(TARGET_LANES[lane])
        record["evidence_paths"] = evidence
        record["known_issues"] = [
            issue for issue in (record.get("known_issues") or [])
            if "Target-runtime EC2 proof is separate" not in issue
        ]
        record["known_issues"].append("Target-runtime proof is lane- and scope-specific; it is not full-project certification.")
        updated_records += 1

    flux_id = "MODEL-FLUX1-DEV-PRIMARY-BASE-CHECKPOINT-001"
    if any(record.get("record_id") == flux_id for record in records):
        raise SystemExit(f"duplicate existing Flux record: {flux_id}")
    records.append({
        "registry_schema_version": "1.0",
        "record_id": flux_id,
        "created_at": now,
        "updated_at": now,
        "source": "huggingface",
        "source_url": "https://huggingface.co/Comfy-Org/flux1-dev/blob/0f6b956e6e2e041fb73d079b72ec0e761506f601/flux1-dev-fp8.safetensors",
        "source_model_id": "Comfy-Org/flux1-dev",
        "source_model_version_id": "0f6b956e6e2e041fb73d079b72ec0e761506f601",
        "model_name": "FLUX.1-dev fp8",
        "model_type": "Checkpoint",
        "base_model": "flux1",
        "version_name": "fp8",
        "file_name": "flux1-dev-fp8.safetensors",
        "file_extension": ".safetensors",
        "file_size_bytes": 17246524772,
        "sha256": "8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a",
        "source_hashes": {"SHA256": "8E91B68084B53A7FC44ED2A3756D821E355AC1A7B6FE29BE760C1DB532F3D88A"},
        "local_path": "models/checkpoints/flux1-dev-fp8.safetensors",
        "storage_location": "not_installed_license_acceptance_pending",
        "workflow_lane": "flux1_dev_primary_base",
        "compatibility_status": "needs_runtime_validation",
        "compatible_engines": ["flux1"],
        "trigger_words": [],
        "intended_use": "Primary FLUX.1-dev base lane after explicit noncommercial license acceptance, hash-verified installation, and runtime QA.",
        "prompt_notes": "Do not execute or promote while license acceptance and local installation proof are absent.",
        "negative_prompt_notes": "No runtime prompt claims are authorized before installation and QA.",
        "qa_status": "not_tested",
        "runtime_validation_status": "queued",
        "visual_impact": "Unknown until licensed installation and lane-scoped runtime/visual QA complete.",
        "video_impact": "Not certified.",
        "audio_impact": "None.",
        "known_issues": [
            "Noncommercial license acceptance is not asserted by automation.",
            "The checkpoint is not present locally.",
            "Local path/hash, model load, generation, technical QA, and visual QA proof are pending.",
            "Promotion is prohibited until all runtime requirements pass."
        ],
        "last_tested_at": None,
        "evidence_paths": [
            "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_FLUX1_DEV_ASSET_AUTHORITY_20260710T222500-0500.json",
            "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_FLUX1_DEV_LICENSED_INSTALL_DRY_RUN_20260710T224500-0500.json",
            "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LICENSED_MODEL_INSTALL_REGRESSION_20260710T224500-0500.json"
        ]
    })
    REGISTRY.write_text("\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n", encoding="utf-8")

    with QUEUE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    updated_queue = 0
    for row in rows:
        lane = row.get("workflow_lane")
        if lane not in TARGET_LANES:
            continue
        row["status"] = "runtime_smoke_complete"
        row["evidence_path"] = TARGET_LANES[lane]
        updated_queue += 1
    flux_queue_id = "MRQ-W64-100"
    if any(row.get("queue_id") == flux_queue_id or row.get("workflow_lane") == "flux1_dev_primary_base" for row in rows):
        raise SystemExit("duplicate existing Flux queue row")
    rows.append({
        "queue_id": flux_queue_id,
        "created_at": now,
        "model_name": "FLUX.1-dev fp8",
        "model_type": "Checkpoint",
        "base_model": "flux1",
        "local_path": "models/checkpoints/flux1-dev-fp8.safetensors",
        "workflow_lane": "flux1_dev_primary_base",
        "test_workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_dev_primary_base/workflow.api.json",
        "expected_result": "install_hash_verify_then_runtime_smoke_after_explicit_license_acceptance",
        "priority": "100",
        "status": "queued",
        "evidence_path": "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_FLUX1_DEV_ASSET_AUTHORITY_20260710T222500-0500.json",
    })
    with QUEUE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    if updated_records != 4 or updated_queue != 4 or len(records) != 15 or len(rows) != 15:
        raise SystemExit(f"alignment count mismatch: records={updated_records}/{len(records)}, queue={updated_queue}/{len(rows)}")
    print(json.dumps({"updated_target_runtime_registry_records": updated_records, "updated_target_runtime_queue_rows": updated_queue, "flux_registry_record_added": flux_id, "flux_queue_row_added": flux_queue_id, "registry_count": len(records), "queue_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
