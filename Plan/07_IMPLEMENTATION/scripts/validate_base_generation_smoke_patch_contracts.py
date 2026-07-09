from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
WORKFLOWS_ROOT = PROJECT_ROOT / "Workflows/base_generation"
ACTIVE_LANES = WORKFLOWS_ROOT / "ACTIVE_LANES.json"
OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Static_Validation"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()
OUT_FILE = OUT_DIR / f"BASE_GENERATION_SMOKE_PATCH_CONTRACTS_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def project_path(raw: str) -> Path:
    return PROJECT_ROOT / raw.replace("/", "\\")


def runtime_model_filenames(requirements: dict[str, Any]) -> set[str]:
    filenames = set()
    for model in requirements.get("required_models", []):
        if isinstance(model, dict) and model.get("filename"):
            filenames.add(str(model["filename"]))
    return filenames


def runtime_input_filenames(requirements: dict[str, Any]) -> set[str]:
    filenames = set()
    for asset in requirements.get("required_input_assets", []):
        if isinstance(asset, dict):
            for key in ("filename", "file_name", "asset_filename"):
                if asset.get(key):
                    filenames.add(str(asset[key]))
    return filenames


def validate_lane(active_lane: dict[str, Any]) -> dict[str, Any]:
    lane_id = str(active_lane.get("lane_id", ""))
    lane_dir = WORKFLOWS_ROOT / lane_id
    paths = {
        "workflow": project_path(str(active_lane.get("workflow", ""))),
        "smoke_request": project_path(str(active_lane.get("smoke_request", ""))),
        "runtime_requirements": project_path(str(active_lane.get("runtime_requirements", ""))),
        "patch_points": project_path(str(active_lane.get("patch_points", ""))),
    }
    report: dict[str, Any] = {
        "lane_id": lane_id,
        "lane_dir": rel(lane_dir) if lane_dir.exists() else str(lane_dir),
        "errors": [],
        "warnings": [],
        "paths": {key: rel(path) if path.exists() else str(path) for key, path in paths.items()},
        "checks": {},
    }

    payloads: dict[str, Any] = {}
    for key, path in paths.items():
        payload, error = read_json(path)
        report["checks"][f"{key}_exists"] = path.exists()
        report["checks"][f"{key}_json_valid"] = error is None
        if not path.exists():
            report["errors"].append(f"{key}_missing")
        elif error:
            report["errors"].append(f"{key}_json_error:{error}")
        else:
            payloads[key] = payload

    if report["errors"]:
        return report

    workflow = payloads["workflow"]
    smoke = payloads["smoke_request"]
    requirements = payloads["runtime_requirements"]
    patch = payloads["patch_points"]
    nodes = workflow if isinstance(workflow, dict) else {}
    patch_values = smoke.get("request_patch_values", {}) if isinstance(smoke, dict) else {}
    expected_outputs = smoke.get("expected_outputs", {}) if isinstance(smoke, dict) else {}

    for name, payload in [("smoke_request", smoke), ("runtime_requirements", requirements), ("patch_points", patch)]:
        report["checks"][f"{name}_lane_id_matches"] = isinstance(payload, dict) and payload.get("lane_id") == lane_id
        if not report["checks"][f"{name}_lane_id_matches"]:
            report["errors"].append(f"{name}_lane_id_mismatch:{payload.get('lane_id') if isinstance(payload, dict) else None}")

    patch_entries = patch.get("patch_points", []) if isinstance(patch, dict) else []
    patch_names = [entry.get("name") for entry in patch_entries if isinstance(entry, dict)]
    duplicate_patch_names = sorted({name for name in patch_names if name and patch_names.count(name) > 1})
    report["checks"]["patch_names_unique"] = not duplicate_patch_names
    if duplicate_patch_names:
        report["errors"].append(f"duplicate_patch_names:{duplicate_patch_names}")

    for entry in patch_entries:
        if not isinstance(entry, dict):
            report["errors"].append("malformed_patch_point")
            continue
        name = str(entry.get("name", ""))
        required = entry.get("required") is True
        node_id = entry.get("node_id")
        node_type = entry.get("node_type")
        declared_inputs = []
        if entry.get("input"):
            declared_inputs.append(str(entry["input"]))
        declared_inputs.extend(str(item) for item in entry.get("inputs", []) if item)

        if required and name not in patch_values:
            report["errors"].append(f"required_patch_value_missing:{name}")
        if not node_id:
            if required:
                report["errors"].append(f"required_patch_node_missing:{name}")
            continue
        node = nodes.get(str(node_id))
        if not isinstance(node, dict):
            report["errors"].append(f"patch_node_missing:{name}:{node_id}")
            continue
        actual_type = node.get("class_type")
        if actual_type != node_type:
            report["errors"].append(f"patch_node_type_mismatch:{name}:{node_id}:{actual_type}!={node_type}")
        node_inputs = node.get("inputs", {})
        if not isinstance(node_inputs, dict):
            report["errors"].append(f"patch_node_inputs_missing:{name}:{node_id}")
            continue
        for input_name in declared_inputs:
            if input_name not in node_inputs:
                report["errors"].append(f"patch_input_missing:{name}:{node_id}:{input_name}")
        if isinstance(patch_values.get(name), dict):
            for value_key in patch_values[name].keys():
                if declared_inputs and value_key not in declared_inputs:
                    report["warnings"].append(f"patch_value_key_not_declared:{name}:{value_key}")

    required_model_names = runtime_model_filenames(requirements)
    required_input_names = runtime_input_filenames(requirements)
    for value_key in ("model_asset", "controlnet_asset"):
        value = patch_values.get(value_key)
        if value:
            match = str(value) in required_model_names
            report["checks"][f"{value_key}_listed_in_runtime_requirements"] = match
            if not match:
                report["errors"].append(f"{value_key}_not_in_required_models:{value}")
    control_image = patch_values.get("control_image")
    if control_image:
        match = str(control_image) in required_input_names if required_input_names else True
        report["checks"]["control_image_listed_in_runtime_requirements"] = match
        if not match:
            report["errors"].append(f"control_image_not_in_required_input_assets:{control_image}")

    report["checks"]["expected_output_defined"] = (
        isinstance(expected_outputs, dict)
        and expected_outputs.get("artifact_type") == "image"
        and int(expected_outputs.get("minimum_output_count", 0)) >= 1
        and bool(expected_outputs.get("output_prefix"))
    )
    if not report["checks"]["expected_output_defined"]:
        report["errors"].append("expected_output_not_defined")

    qa_protocols = smoke.get("qa_protocols", []) if isinstance(smoke, dict) else []
    missing_protocols = []
    for raw in qa_protocols:
        path = project_path(str(raw))
        if not path.exists():
            missing_protocols.append(str(raw))
    report["checks"]["qa_protocols_exist"] = not missing_protocols
    if missing_protocols:
        report["errors"].append(f"qa_protocols_missing:{missing_protocols}")

    report["checks"]["execution_remains_disabled"] = smoke.get("execution_allowed") is False
    if not report["checks"]["execution_remains_disabled"]:
        report["errors"].append("execution_allowed_not_false")

    report["checks"]["lane_folder_present"] = lane_dir.exists()
    if not lane_dir.exists():
        report["errors"].append("lane_folder_missing")

    return report


def main() -> int:
    active, active_error = read_json(ACTIVE_LANES)
    lane_reports = []
    if active_error is None and isinstance(active, dict):
        lane_reports = [validate_lane(lane) for lane in active.get("lanes", []) if isinstance(lane, dict)]
    failed_lanes = [lane for lane in lane_reports if lane.get("errors")]
    warning_lanes = [lane for lane in lane_reports if lane.get("warnings")]
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_SMOKE_PATCH_CONTRACTS_{STAMP}",
        "created_iso": ISO_TS,
        "active_lanes_path": rel(ACTIVE_LANES),
        "active_lanes_json_valid": active_error is None,
        "active_lanes_error": active_error,
        "counts": {
            "lanes_checked": len(lane_reports),
            "failed_lanes": len(failed_lanes),
            "warning_lanes": len(warning_lanes),
        },
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
    payload["pass"] = active_error is None and not failed_lanes
    payload["decision"] = "base_generation_smoke_patch_contracts_passed" if payload["pass"] else "blocked_base_generation_smoke_patch_contract_gap"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "counts": payload["counts"],
        "failed_lanes": [lane["lane_id"] for lane in failed_lanes],
        "warning_lanes": [lane["lane_id"] for lane in warning_lanes],
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
