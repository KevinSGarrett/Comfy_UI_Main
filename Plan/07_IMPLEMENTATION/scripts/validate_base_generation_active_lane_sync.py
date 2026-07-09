from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
WORKFLOWS_ROOT = PROJECT_ROOT / "Workflows/base_generation"
TEMPLATE_ROOT = PLAN_ROOT / "07_IMPLEMENTATION/workflow_templates/base_generation"
ACTIVE_LANES = WORKFLOWS_ROOT / "ACTIVE_LANES.json"
RUNTIME_QUEUE = TEMPLATE_ROOT / "runtime_lane_queue.json"
OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Static_Validation"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()
OUT_FILE = OUT_DIR / f"BASE_GENERATION_ACTIVE_LANE_SYNC_{STAMP}.json"

LANE_FILES = [
    "workflow.api.json",
    "smoke_test_request.json",
    "runtime_requirements.json",
    "patch_points.json",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(raw: str) -> Path:
    return PROJECT_ROOT / raw.replace("/", "\\")


def lane_file_report(lane_id: str, file_name: str) -> dict[str, Any]:
    workflow_path = WORKFLOWS_ROOT / lane_id / file_name
    template_path = TEMPLATE_ROOT / lane_id / file_name
    result: dict[str, Any] = {
        "file_name": file_name,
        "workflow_path": rel(workflow_path) if workflow_path.exists() else str(workflow_path),
        "template_path": rel(template_path) if template_path.exists() else str(template_path),
        "workflow_exists": workflow_path.exists(),
        "template_exists": template_path.exists(),
        "workflow_json_valid": None,
        "template_json_valid": None,
        "workflow_lane_id": None,
        "template_lane_id": None,
        "sha256_match": None,
        "workflow_sha256": None,
        "template_sha256": None,
        "errors": [],
    }
    if workflow_path.exists():
        payload, error = read_json(workflow_path)
        result["workflow_json_valid"] = error is None
        if isinstance(payload, dict):
            result["workflow_lane_id"] = payload.get("lane_id")
        if error:
            result["errors"].append(f"workflow_json_error:{error}")
    else:
        result["errors"].append("workflow_file_missing")
    if template_path.exists():
        payload, error = read_json(template_path)
        result["template_json_valid"] = error is None
        if isinstance(payload, dict):
            result["template_lane_id"] = payload.get("lane_id")
        if error:
            result["errors"].append(f"template_json_error:{error}")
    else:
        result["errors"].append("template_file_missing")
    if workflow_path.exists() and template_path.exists():
        workflow_hash = sha256(workflow_path)
        template_hash = sha256(template_path)
        result["workflow_sha256"] = workflow_hash
        result["template_sha256"] = template_hash
        result["sha256_match"] = workflow_hash == template_hash
        if workflow_hash != template_hash:
            result["errors"].append("workflow_template_sha256_mismatch")
    if result["workflow_lane_id"] not in (None, lane_id):
        result["errors"].append(f"workflow_lane_id_mismatch:{result['workflow_lane_id']}")
    if result["template_lane_id"] not in (None, lane_id):
        result["errors"].append(f"template_lane_id_mismatch:{result['template_lane_id']}")
    return result


def main() -> int:
    active, active_error = read_json(ACTIVE_LANES)
    queue, queue_error = read_json(RUNTIME_QUEUE)
    active_lanes = active.get("lanes", []) if isinstance(active, dict) else []
    queue_lanes = queue.get("lanes", []) if isinstance(queue, dict) else []
    active_ids = [str(lane.get("lane_id")) for lane in active_lanes if isinstance(lane, dict) and lane.get("lane_id")]
    queue_ids = [str(lane.get("lane_id")) for lane in queue_lanes if isinstance(lane, dict) and lane.get("lane_id")]
    active_set = set(active_ids)
    queue_set = set(queue_ids)
    folder_ids = sorted(path.name for path in WORKFLOWS_ROOT.iterdir() if path.is_dir())

    lane_reports = []
    for lane in active_lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("lane_id", ""))
        if not lane_id:
            continue
        manifest_file_checks = []
        for field, expected_name in [
            ("workflow", "workflow.api.json"),
            ("smoke_request", "smoke_test_request.json"),
            ("runtime_requirements", "runtime_requirements.json"),
            ("patch_points", "patch_points.json"),
        ]:
            raw = str(lane.get(field, ""))
            path = project_path(raw) if raw else PROJECT_ROOT / "__missing__"
            manifest_file_checks.append({
                "field": field,
                "path": raw,
                "exists": path.exists(),
                "expected_suffix": f"Workflows/base_generation/{lane_id}/{expected_name}",
                "suffix_matches": raw.replace("\\", "/") == f"Workflows/base_generation/{lane_id}/{expected_name}",
            })
        file_reports = [lane_file_report(lane_id, file_name) for file_name in LANE_FILES]
        lane_reports.append({
            "lane_id": lane_id,
            "order": lane.get("order"),
            "status": lane.get("status"),
            "next_gate": lane.get("next_gate"),
            "queue_present": lane_id in queue_set,
            "folder_present": lane_id in folder_ids,
            "manifest_file_checks": manifest_file_checks,
            "file_reports": file_reports,
            "errors": [
                error
                for check in manifest_file_checks
                for error in (
                    ([] if check["exists"] else [f"{check['field']}_path_missing"])
                    + ([] if check["suffix_matches"] else [f"{check['field']}_path_not_lane_scoped"])
                )
            ] + [
                error
                for report in file_reports
                for error in report["errors"]
            ] + ([] if lane_id in queue_set else ["active_lane_missing_from_queue"])
              + ([] if lane_id in folder_ids else ["active_lane_folder_missing"]),
        })

    inactive_workflow_folders = [lane_id for lane_id in folder_ids if lane_id not in active_set]
    active_missing_from_queue = sorted(active_set - queue_set)
    queue_missing_from_active = sorted(queue_set - active_set)
    duplicate_active_ids = sorted({lane_id for lane_id in active_ids if active_ids.count(lane_id) > 1})
    duplicate_queue_ids = sorted({lane_id for lane_id in queue_ids if queue_ids.count(lane_id) > 1})
    failed_lanes = [lane for lane in lane_reports if lane["errors"]]

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_ACTIVE_LANE_SYNC_{STAMP}",
        "created_iso": ISO_TS,
        "active_lanes_path": rel(ACTIVE_LANES),
        "runtime_queue_path": rel(RUNTIME_QUEUE),
        "workflow_root": rel(WORKFLOWS_ROOT),
        "template_root": rel(TEMPLATE_ROOT),
        "checks": {
            "active_lanes_json_valid": active_error is None,
            "runtime_queue_json_valid": queue_error is None,
            "active_lane_ids_unique": not duplicate_active_ids,
            "queue_lane_ids_unique": not duplicate_queue_ids,
            "active_lanes_present_in_queue": not active_missing_from_queue,
            "queue_lanes_present_in_active": not queue_missing_from_active,
            "active_lane_files_exist_and_parse": not failed_lanes,
            "runtime_boundaries_preserved": True,
        },
        "counts": {
            "active_lanes": len(active_ids),
            "queue_lanes": len(queue_ids),
            "workflow_lane_folders": len(folder_ids),
            "inactive_workflow_folders": len(inactive_workflow_folders),
            "failed_lanes": len(failed_lanes),
        },
        "inactive_workflow_folders": inactive_workflow_folders,
        "active_missing_from_queue": active_missing_from_queue,
        "queue_missing_from_active": queue_missing_from_active,
        "duplicate_active_ids": duplicate_active_ids,
        "duplicate_queue_ids": duplicate_queue_ids,
        "lane_reports": lane_reports,
        "runtime_boundary": {
            "ec2_started": False,
            "aws_contacted": False,
            "generation_executed": False,
            "comfyui_contacted": False,
            "hard_gates_rerun": False,
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
    }
    payload["pass"] = all(payload["checks"].values())
    payload["decision"] = "base_generation_active_lane_sync_passed" if payload["pass"] else "blocked_base_generation_active_lane_sync_gap"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "counts": payload["counts"],
        "active_missing_from_queue": active_missing_from_queue,
        "queue_missing_from_active": queue_missing_from_active,
        "inactive_workflow_folders": inactive_workflow_folders,
        "failed_lanes": [lane["lane_id"] for lane in failed_lanes],
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
