from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
REGISTRY = PLAN_ROOT / "Registries/Models/model_registry.jsonl"
QUEUE = PLAN_ROOT / "Registries/Models/model_runtime_validation_queue.csv"
REQUIREMENTS_ROOT = PLAN_ROOT / "07_IMPLEMENTATION/workflow_templates/base_generation"

REALVISXL_SOURCE_RECORD_ID = "MODEL-REALVISXL-V50-BAKEDVAE-CHECKPOINT-001"

LANE_SPECS = {
    "sdxl_realvisxl_controlnet_depth_lane": {
        "record_id": "MODEL-REALVISXL-V50-DEPTH-LANE-CHECKPOINT-001",
        "model_name": "RealVisXL V5.0",
        "status": "local_generation_smoke_complete",
        "compatibility_status": "local_runtime_smoke_validated_with_notes",
        "qa_status": "pass_with_notes_for_local_depth_smoke",
        "last_tested_at": "2026-07-07T05:52:00-05:00",
        "intended_use": "Checkpoint component for MOD-18 SDXL RealVisXL ControlNet Depth lane.",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_DEPTH_CONTROLNET_V1_VISUAL_QA_20260707T055200-0500.json",
        "priority": "50",
        "expected_result": "load_checkpoint_with_controlnet_depth_local_smoke_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_lineart_lane": {
        "record_id": "MODEL-REALVISXL-V50-LINEART-LANE-CHECKPOINT-001",
        "model_name": "RealVisXL V5.0",
        "status": "local_generation_followup_complete",
        "compatibility_status": "local_runtime_followup_validated_with_notes",
        "qa_status": "pass_with_notes_for_local_lineart_v2_followup",
        "last_tested_at": "2026-07-07T06:12:00-05:00",
        "intended_use": "Checkpoint component for MOD-19 SDXL RealVisXL ControlNet Lineart lane.",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_LINEART_CONTROLNET_V2_VISUAL_QA_20260707T061200-0500.json",
        "priority": "60",
        "expected_result": "load_checkpoint_with_controlnet_lineart_local_followup_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_openpose_lane": {
        "record_id": "MODEL-REALVISXL-V50-OPENPOSE-LANE-CHECKPOINT-001",
        "model_name": "RealVisXL V5.0",
        "status": "local_generation_smoke_complete",
        "compatibility_status": "local_runtime_smoke_validated_with_notes",
        "qa_status": "pass_with_notes_for_local_openpose_controlnet_smoke",
        "last_tested_at": "2026-07-07T06:28:00-05:00",
        "intended_use": "Checkpoint component for MOD-20 SDXL RealVisXL ControlNet OpenPose lane.",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_OPENPOSE_CONTROLNET_V1_VISUAL_QA_20260707T062800-0500.json",
        "priority": "70",
        "expected_result": "load_checkpoint_with_controlnet_openpose_local_smoke_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_normal_lane": {
        "record_id": "MODEL-REALVISXL-V50-NORMAL-LANE-CHECKPOINT-001",
        "model_name": "RealVisXL V5.0",
        "status": "local_generation_smoke_complete",
        "compatibility_status": "local_runtime_smoke_validated_with_notes",
        "qa_status": "pass_with_notes_for_local_normal_controlnet_smoke",
        "last_tested_at": "2026-07-07T06:40:00-05:00",
        "intended_use": "Checkpoint component for MOD-21 SDXL RealVisXL ControlNet Normal lane.",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_NORMAL_CONTROLNET_V1_VISUAL_QA_20260707T064000-0500.json",
        "priority": "80",
        "expected_result": "load_checkpoint_with_controlnet_normal_local_smoke_pending_target_runtime",
    },
}

CONTROLNET_QUEUE_SPECS = {
    "sdxl_realvisxl_controlnet_depth_lane": {
        "model_name": "SDXL Depth ControlNet small",
        "model_type": "ControlNet",
        "local_path": "models/controlnet/controlnet-depth-sdxl-1.0-small.safetensors",
        "status": "local_generation_smoke_complete",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_DEPTH_CONTROLNET_V1_VISUAL_QA_20260707T055200-0500.json",
        "priority": "51",
        "expected_result": "load_depth_controlnet_local_smoke_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_lineart_lane": {
        "model_name": "Lineart SDXL ControlNet fp16",
        "model_type": "ControlNet",
        "local_path": "models/controlnet/controlnet-lineart-sdxl-fp16.safetensors",
        "status": "local_generation_followup_complete",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_LINEART_CONTROLNET_V2_VISUAL_QA_20260707T061200-0500.json",
        "priority": "61",
        "expected_result": "load_lineart_controlnet_local_followup_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_openpose_lane": {
        "model_name": "OpenPoseXL2 SDXL ControlNet",
        "model_type": "ControlNet",
        "local_path": "models/controlnet/OpenPoseXL2.safetensors",
        "status": "local_generation_smoke_complete",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_OPENPOSE_CONTROLNET_V1_VISUAL_QA_20260707T062800-0500.json",
        "priority": "71",
        "expected_result": "load_openpose_controlnet_local_smoke_pending_target_runtime",
    },
    "sdxl_realvisxl_controlnet_normal_lane": {
        "model_name": "ControlNet Union SDXL 1.0 Normal",
        "model_type": "ControlNet",
        "local_path": "models/controlnet/controlnet-union-sdxl-1.0.safetensors",
        "status": "local_generation_smoke_complete",
        "evidence_path": "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_NORMAL_CONTROLNET_V1_VISUAL_QA_20260707T064000-0500.json",
        "priority": "81",
        "expected_result": "load_normal_controlnet_local_smoke_pending_target_runtime",
    },
}


def read_registry() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def write_registry(records: list[dict[str, object]]) -> None:
    REGISTRY.write_text("\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n", encoding="utf-8")


def read_queue() -> tuple[list[str], list[dict[str, str]]]:
    with QUEUE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_queue(fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with QUEUE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_requirement_statuses() -> int:
    changed = 0
    for lane in LANE_SPECS:
        path = REQUIREMENTS_ROOT / lane / "runtime_requirements.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        touched = False
        for model in data.get("required_models", []):
            if not model.get("hash_status"):
                model["hash_status"] = "pending_ec2_static_match"
                touched = True
            if not model.get("path_status"):
                model["path_status"] = "pending_ec2_static_match"
                touched = True
        if touched:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            changed += 1
    return changed


def add_lane_checkpoint_records(records: list[dict[str, object]]) -> int:
    source = next(record for record in records if record["record_id"] == REALVISXL_SOURCE_RECORD_ID)
    existing_ids = {str(record["record_id"]) for record in records}
    added = 0
    for lane, spec in LANE_SPECS.items():
        if spec["record_id"] in existing_ids:
            continue
        record = deepcopy(source)
        record.update(
            {
                "record_id": spec["record_id"],
                "created_at": "2026-07-08T23:38:00-05:00",
                "updated_at": "2026-07-08T23:38:00-05:00",
                "workflow_lane": lane,
                "compatibility_status": spec["compatibility_status"],
                "runtime_validation_status": spec["status"],
                "qa_status": spec["qa_status"],
                "intended_use": spec["intended_use"],
                "last_tested_at": spec["last_tested_at"],
                "visual_impact": "Local pre-EC2 lane evidence exists with notes; target-runtime EC2 proof and final certification remain separate.",
                "known_issues": [
                    "Local model binary remains ignored and uncommitted by design.",
                    "Target-runtime EC2 proof is separate from local pre-EC2 validation.",
                    "Single-lane local evidence is not final portfolio certification.",
                ],
                "evidence_paths": [spec["evidence_path"]],
            }
        )
        records.append(record)
        existing_ids.add(spec["record_id"])
        added += 1
    return added


def add_queue_rows(fieldnames: list[str], rows: list[dict[str, str]]) -> int:
    existing = {
        (row.get("workflow_lane", ""), row.get("local_path", "").replace("\\", "/"))
        for row in rows
    }
    added = 0
    for lane, spec in LANE_SPECS.items():
        checkpoint_key = (lane, "models/checkpoints/realvisxlV50_v50Bakedvae.safetensors")
        if checkpoint_key not in existing:
            rows.append(
                {
                    "queue_id": f"MRQ-W64-{int(spec['priority']):03d}",
                    "created_at": "2026-07-08T23:38:00-05:00",
                    "model_name": spec["model_name"],
                    "model_type": "Checkpoint",
                    "base_model": "sdxl",
                    "local_path": checkpoint_key[1],
                    "workflow_lane": lane,
                    "test_workflow_path": f"Plan/07_IMPLEMENTATION/workflow_templates/base_generation/{lane}/workflow.api.json",
                    "expected_result": spec["expected_result"],
                    "priority": spec["priority"],
                    "status": spec["status"],
                    "evidence_path": spec["evidence_path"],
                }
            )
            existing.add(checkpoint_key)
            added += 1
        control_spec = CONTROLNET_QUEUE_SPECS[lane]
        control_key = (lane, control_spec["local_path"])
        if control_key not in existing:
            rows.append(
                {
                    "queue_id": f"MRQ-W64-{int(control_spec['priority']):03d}",
                    "created_at": "2026-07-08T23:38:00-05:00",
                    "model_name": control_spec["model_name"],
                    "model_type": control_spec["model_type"],
                    "base_model": "sdxl",
                    "local_path": control_spec["local_path"],
                    "workflow_lane": lane,
                    "test_workflow_path": f"Plan/07_IMPLEMENTATION/workflow_templates/base_generation/{lane}/workflow.api.json",
                    "expected_result": control_spec["expected_result"],
                    "priority": control_spec["priority"],
                    "status": control_spec["status"],
                    "evidence_path": control_spec["evidence_path"],
                }
            )
            existing.add(control_key)
            added += 1
    rows.sort(key=lambda row: int(row.get("priority") or "999"))
    return added


def main() -> None:
    records = read_registry()
    registry_added = add_lane_checkpoint_records(records)
    write_registry(records)

    fieldnames, rows = read_queue()
    queue_added = add_queue_rows(fieldnames, rows)
    write_queue(fieldnames, rows)

    requirements_changed = update_requirement_statuses()
    print(
        json.dumps(
            {
                "registry_added": registry_added,
                "queue_rows_added": queue_added,
                "requirements_files_changed": requirements_changed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
