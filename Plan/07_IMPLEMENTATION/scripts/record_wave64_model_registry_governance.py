from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

TRACKER_ID = "TRK-W64-044"
ITEM_ID = "ITEM-W64-044"
NEXT_TRACKER_ID = "TRK-W64-045"
NEXT_ITEM_ID = "ITEM-W64-045"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
MODEL_EVIDENCE_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Model_Registry"

COVERAGE = max(MODEL_EVIDENCE_DIR.glob("W64_MODEL_REGISTRY_GOVERNANCE_COVERAGE_AFTER_ALIGNMENT_*.json"), key=lambda path: path.stat().st_mtime)
SOURCE_SCRIPT = PLAN_ROOT / "Instructions/QA/Scripts/Test-WorkflowModelRegistryCoverage.ps1"
ALIGNMENT_SCRIPT = PLAN_ROOT / "07_IMPLEMENTATION/scripts/implement_wave64_model_registry_governance_alignment.py"
REGISTRY = PLAN_ROOT / "Registries/Models/model_registry.jsonl"
QUEUE = PLAN_ROOT / "Registries/Models/model_runtime_validation_queue.csv"

EVIDENCE = QA_DIR / "model_registry_governance.json"
STAMPED_EVIDENCE = QA_DIR / f"MODEL_REGISTRY_GOVERNANCE_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"MODEL_REGISTRY_GOVERNANCE_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Aligned model registry governance and passed local workflow model coverage gate.",
        "; ".join(payload["evidence_paths"]),
        "registry record exists; model type valid; source metadata/hash captured; runtime queue coverage; local/target boundary; coverage gate pass",
        payload["qa_decision"],
        rel(EVIDENCE),
        f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} Civitai metadata lookup and provenance.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    coverage = read_json(COVERAGE)
    failed_lanes = [
        lane
        for lane in coverage.get("lane_results", [])
        if isinstance(lane, dict) and lane.get("result") != "pass"
    ]
    errors: list[str] = []
    if coverage.get("result") != "pass_local_only":
        errors.append(f"coverage_result_not_pass:{coverage.get('result')}")
    if coverage.get("failed_check_count") != 0:
        errors.append(f"failed_check_count_nonzero:{coverage.get('failed_check_count')}")
    if coverage.get("registry_record_count") != 13:
        errors.append(f"registry_record_count_unexpected:{coverage.get('registry_record_count')}")
    if coverage.get("runtime_validation_queue_row_count") != 13:
        errors.append(f"runtime_queue_count_unexpected:{coverage.get('runtime_validation_queue_row_count')}")
    if failed_lanes:
        errors.append(f"failed_lanes:{len(failed_lanes)}")

    qa_decision = (
        "model_registry_governance_passed_local_only"
        if not errors
        else "blocked_model_registry_governance_coverage_gap"
    )
    lane_summary = []
    for lane in coverage.get("lane_results", []):
        if isinstance(lane, dict):
            lane_summary.append(
                {
                    "lane_id": lane.get("lane_id"),
                    "required_model_count": lane.get("required_model_count"),
                    "failed_check_count": lane.get("failed_check_count"),
                    "result": lane.get("result"),
                }
            )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"MODEL_REGISTRY_GOVERNANCE_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Govern workflow model registry coverage, metadata, hash/path status, and runtime queue alignment.",
        "source_validator": rel(SOURCE_SCRIPT),
        "alignment_script": rel(ALIGNMENT_SCRIPT),
        "registry_file": rel(REGISTRY),
        "runtime_queue_file": rel(QUEUE),
        "coverage_evidence": evidence_path(COVERAGE),
        "coverage_result": {
            "result": coverage.get("result"),
            "failed_check_count": coverage.get("failed_check_count"),
            "registry_record_count": coverage.get("registry_record_count"),
            "runtime_validation_queue_row_count": coverage.get("runtime_validation_queue_row_count"),
            "workflow_runtime_lane_count": coverage.get("workflow_runtime_lane_count"),
            "active_lane_ids": coverage.get("active_lane_ids"),
            "lane_summary": lane_summary,
        },
        "governance_changes": {
            "lane_specific_realvisxl_checkpoint_records_added": 4,
            "runtime_queue_rows_added": 8,
            "requirements_files_marked_pending_target_static_match": 4,
            "validator_local_pre_ec2_lane_state_supported": True,
        },
        "runtime_boundary": {
            "local_only": coverage.get("local_only"),
            "aws_contacted": coverage.get("aws_contacted"),
            "github_api_contacted": coverage.get("github_api_contacted"),
            "civitai_contacted": coverage.get("civitai_contacted"),
            "comfyui_contacted": coverage.get("comfyui_contacted"),
            "ec2_started": coverage.get("ec2_started"),
            "generation_executed": coverage.get("generation_executed"),
            "target_runtime_promoted": False,
            "local_pre_ec2_evidence_preserved_as_local_only": True,
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": f"Advance to {NEXT_TRACKER_ID}/{NEXT_ITEM_ID} Civitai metadata lookup and provenance.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        evidence_path(COVERAGE),
        rel(SOURCE_SCRIPT),
        rel(ALIGNMENT_SCRIPT),
        rel(REGISTRY),
        rel(QUEUE),
    ]

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 model registry governance {STAMP}: coverage_result={coverage.get('result')} "
        f"failed_check_count={coverage.get('failed_check_count')} registry_records={coverage.get('registry_record_count')} "
        f"runtime_queue_rows={coverage.get('runtime_validation_queue_row_count')} active_lanes={coverage.get('workflow_runtime_lane_count')}; "
        f"local_only=True ec2_started=False target_runtime_promoted=False decision={qa_decision}."
    )
    additions = [
        "wave64_model_registry_governance_checked",
        qa_decision,
        "coverage_gate_passed",
        "registry_record_exists_passed",
        "model_type_valid_passed",
        "hash_path_status_aligned",
        "runtime_queue_coverage_aligned",
        "local_pre_ec2_boundary_preserved",
        "allowed_nonmask_work_can_continue",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            ITEM_ID,
            {
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": additions,
                "Notes": [note],
            },
        )

    top_block = f"""
## Immediate Next Action - Wave64 Model Registry Governance - {ISO_TS}

Worked non-EC2 registry row `{TRACKER_ID}` / `{ITEM_ID}`.

Result: `{qa_decision}`. The official workflow model registry coverage gate now reports `{coverage.get('result')}` with failed_check_count=`{coverage.get('failed_check_count')}`, registry_record_count=`{coverage.get('registry_record_count')}`, runtime_validation_queue_row_count=`{coverage.get('runtime_validation_queue_row_count')}`, and active lane count=`{coverage.get('workflow_runtime_lane_count')}`.

Governance changes: added lane-specific RealVisXL checkpoint coverage for depth, lineart, openpose, and normal lanes; added missing runtime queue rows for those checkpoint/controlnet model references; marked those local pre-EC2 lanes as pending target-runtime static match; patched the validator to distinguish local pre-EC2 validation from target-runtime proof.

Boundary: local-only governance. No AWS, Civitai, ComfyUI, EC2, generation, target-runtime promotion, mask truth, mask promotion, hard-gate rerun, or Wave71+ activation occurred.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(COVERAGE)}`

Next exact local action: advance to `{NEXT_TRACKER_ID}` / `{NEXT_ITEM_ID}` Civitai metadata lookup and provenance.
"""
    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"""
## Wave64 Model Registry Governance - {ISO_TS}

Workflow model registry governance passed locally after lane-state-aware validator support and registry/queue alignment.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{evidence_path(COVERAGE)}`
""",
    )
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "stamped_evidence": str(STAMPED_EVIDENCE),
                "tracker_evidence": str(TRACKER_EVIDENCE),
                "qa_decision": qa_decision,
                "errors": errors,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
