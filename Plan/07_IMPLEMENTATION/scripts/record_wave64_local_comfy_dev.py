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

TRACKER_ID = "TRK-W64-039"
ITEM_ID = "ITEM-W64-039"
LANE_ID = "sdxl_low_risk_fallback_lane"

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"

PREFLIGHT = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness/W64_LOCAL_COMFY_DEV_PREFLIGHT_SDXL_LOW_RISK_20260708T232400-0500.json"
START_DRY_RUN = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness/W64_LOCAL_COMFY_DEV_START_DRY_RUN_LOWVRAM_20260708T232500-0500.json"
RUNTIME_SMOKE = QA_DIR / "workflow_runtime_smoke.json"
SOURCE_RUNBOOK = PLAN_ROOT / "Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md"

EVIDENCE = QA_DIR / "local_comfy_dev.json"
STAMPED_EVIDENCE = QA_DIR / f"LOCAL_COMFY_DEV_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"LOCAL_COMFY_DEV_{STAMP}.json"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> object:
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
        "Recorded current local ComfyUI development lane readiness without EC2 equivalence claim.",
        "; ".join(payload["evidence_paths"]),
        "local GPU check; main.py check; CUDA Torch check; required model check; static validation; low-VRAM start dry-run; no-EC2-equivalence boundary",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Use local ComfyUI for bounded previews and workflow iteration; EC2 target proof remains blocked separately.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    preflight = read_json(PREFLIGHT)
    start_plan = read_json(START_DRY_RUN)
    runtime_smoke = read_json(RUNTIME_SMOKE) if RUNTIME_SMOKE.exists() else {}
    errors: list[str] = []

    if preflight.get("result") != "pass_local_gpu_generation_candidate":
        errors.append(f"preflight_not_pass:{preflight.get('result')}")
    if preflight.get("failed_check_count") != 0:
        errors.append(f"preflight_failed_check_count:{preflight.get('failed_check_count')}")
    if preflight.get("local_dev_replaces_ec2_final_proof") is not False:
        errors.append("preflight_claims_ec2_equivalence")
    if preflight.get("ec2_final_proof_still_required") is not True:
        errors.append("preflight_missing_ec2_final_proof_boundary")
    if start_plan.get("result") != "dry_run_local_comfyui_start_plan":
        errors.append(f"start_plan_result_unexpected:{start_plan.get('result')}")
    if start_plan.get("low_vram_args_enabled") is not True:
        errors.append("low_vram_args_not_enabled")
    if start_plan.get("execute") is not False:
        errors.append("start_plan_executed_unexpectedly")
    if start_plan.get("ec2_started") is not False:
        errors.append("ec2_started_unexpectedly")

    qa_decision = "local_comfy_dev_passed_non_ec2_preview_lane" if not errors else "blocked_local_comfy_dev_preflight_or_boundary_failure"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"LOCAL_COMFY_DEV_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "lane_id": LANE_ID,
        "task": "Validate local ComfyUI development lane for low-cost preview work without EC2 equivalence claim.",
        "source_runbook": rel(SOURCE_RUNBOOK),
        "preflight_evidence": rel(PREFLIGHT),
        "start_dry_run_evidence": rel(START_DRY_RUN),
        "runtime_smoke_evidence": rel(RUNTIME_SMOKE) if RUNTIME_SMOKE.exists() else "",
        "local_gpu": preflight.get("local_gpu"),
        "local_python": preflight.get("local_python"),
        "local_comfyui": preflight.get("local_comfyui"),
        "local_required_models": preflight.get("local_required_models"),
        "checks": {
            "failed_check_count": preflight.get("failed_check_count"),
            "local_dev_can_reduce_ec2_starts": preflight.get("local_dev_can_reduce_ec2_starts"),
            "local_gpu_generation_candidate": preflight.get("local_gpu_generation_candidate"),
            "local_dev_replaces_ec2_final_proof": preflight.get("local_dev_replaces_ec2_final_proof"),
            "ec2_final_proof_still_required": preflight.get("ec2_final_proof_still_required"),
            "low_vram_args_enabled": start_plan.get("low_vram_args_enabled"),
            "low_vram_command": start_plan.get("command"),
            "server_already_verified_by_local_smoke": runtime_smoke.get("qa_decision") == "workflow_runtime_smoke_passed_local_nonmask_safe",
        },
        "runtime_boundary": {
            "local_preview_lane_only": True,
            "ec2_equivalence_claimed": False,
            "ec2_final_proof_still_required": True,
            "ec2_started": False,
            "generation_executed_by_this_row": False,
            "local_generation_reused_as_supporting_evidence": runtime_smoke.get("qa_decision") == "workflow_runtime_smoke_passed_local_nonmask_safe",
        },
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "qa_decision": qa_decision,
        "next_step": "Continue concrete non-EC2 work while EC2 auth/git gates remain blocked; use local ComfyUI only for bounded previews and workflow iteration.",
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(PREFLIGHT),
        rel(START_DRY_RUN),
    ]
    if RUNTIME_SMOKE.exists():
        payload["evidence_paths"].append(rel(RUNTIME_SMOKE))

    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)

    note = (
        f"Wave64 local ComfyUI dev {STAMP}: preflight={preflight.get('result')} failed_checks={preflight.get('failed_check_count')}; "
        f"gpu={preflight.get('local_gpu', {}).get('name')} memory_mib={preflight.get('local_gpu', {}).get('memory_total_mib')}; "
        f"low_vram_args_enabled={start_plan.get('low_vram_args_enabled')}; "
        f"ec2_equivalence_claimed=False; ec2_final_proof_still_required=True; decision={qa_decision}."
    )
    additions = [
        "wave64_local_comfy_dev_checked",
        qa_decision,
        "local_preview_lane_only",
        "ec2_final_proof_still_required",
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
## Immediate Next Action - Wave64 Local ComfyUI Development Lane - {ISO_TS}

Worked non-EC2 cost-control row `{TRACKER_ID}` / `{ITEM_ID}` for `{LANE_ID}`.

Result: `{qa_decision}`. Fresh local preflight passed with failed_check_count=`{preflight.get('failed_check_count')}`; local GPU is `{preflight.get('local_gpu', {}).get('name')}` with `{preflight.get('local_gpu', {}).get('memory_total_mib')}` MiB; low-VRAM start dry-run enabled `--lowvram`.

Boundary: local ComfyUI may reduce EC2 starts for previews and workflow iteration only. It does not replace EC2 final proof. EC2 was not started, no generation was run by this row, no masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(PREFLIGHT)}`
- `{rel(START_DRY_RUN)}`

Next exact local action: continue concrete non-EC2 work while EC2 auth/git gates remain blocked.
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
## Wave64 Local ComfyUI Development Lane - {ISO_TS}

Local ComfyUI development lane preflight and low-VRAM dry-run. Local preview lane only; no EC2 equivalence claim.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(PREFLIGHT)}`
- `{rel(START_DRY_RUN)}`
""",
    )
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "tracker_evidence": str(TRACKER_EVIDENCE),
        "qa_decision": qa_decision,
        "errors": errors,
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
