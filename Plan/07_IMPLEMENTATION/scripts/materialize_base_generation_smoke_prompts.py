from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
WORKFLOWS_ROOT = PROJECT_ROOT / "Workflows/base_generation"
ACTIVE_LANES = WORKFLOWS_ROOT / "ACTIVE_LANES.json"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

RUN_ROOT = PROJECT_ROOT / f"runtime_artifacts/base_generation_smoke_prompt_materialization/{STAMP}"
QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Static_Validation"
OUT_FILE = QA_DIR / f"BASE_GENERATION_SMOKE_PROMPT_MATERIALIZATION_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(raw: str) -> Path:
    return PROJECT_ROOT / raw.replace("/", "\\")


def node_inputs(prompt: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    node = prompt.get(str(node_id))
    if not isinstance(node, dict):
        return None
    inputs = node.get("inputs")
    return inputs if isinstance(inputs, dict) else None


def patch_prompt(workflow: dict[str, Any], patch_points: dict[str, Any], patch_values: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    patched = copy.deepcopy(workflow)
    errors: list[str] = []
    applied: list[dict[str, Any]] = []

    for point in patch_points.get("patch_points", []):
        if not isinstance(point, dict):
            errors.append("malformed_patch_point")
            continue
        name = str(point.get("name", ""))
        required = point.get("required") is True
        node_id = point.get("node_id")
        if name not in patch_values:
            if required:
                errors.append(f"required_patch_value_missing:{name}")
            continue
        if not node_id:
            if required:
                errors.append(f"required_patch_node_missing:{name}")
            continue

        inputs = node_inputs(patched, str(node_id))
        if inputs is None:
            errors.append(f"patch_node_inputs_missing:{name}:{node_id}")
            continue

        value = patch_values[name]
        if point.get("input"):
            input_name = str(point["input"])
            before = copy.deepcopy(inputs.get(input_name))
            inputs[input_name] = value
            applied.append({"name": name, "node_id": str(node_id), "input": input_name, "before": before, "after": value})
        else:
            if not isinstance(value, dict):
                errors.append(f"compound_patch_value_not_object:{name}")
                continue
            for input_name in point.get("inputs", []):
                input_key = str(input_name)
                if input_key not in value:
                    errors.append(f"compound_patch_value_key_missing:{name}:{input_key}")
                    continue
                before = copy.deepcopy(inputs.get(input_key))
                inputs[input_key] = value[input_key]
                applied.append({"name": name, "node_id": str(node_id), "input": input_key, "before": before, "after": value[input_key]})
    return patched, errors, applied


def verify_applied(prompt: dict[str, Any], applied: list[dict[str, Any]]) -> list[str]:
    errors = []
    for record in applied:
        inputs = node_inputs(prompt, record["node_id"])
        if inputs is None:
            errors.append(f"verify_node_inputs_missing:{record['name']}:{record['node_id']}")
            continue
        actual = inputs.get(record["input"])
        if actual != record["after"]:
            errors.append(f"verify_patch_value_mismatch:{record['name']}:{record['node_id']}:{record['input']}")
    return errors


def materialize_lane(active_lane: dict[str, Any]) -> dict[str, Any]:
    lane_id = str(active_lane.get("lane_id", ""))
    workflow_path = project_path(str(active_lane["workflow"]))
    smoke_path = project_path(str(active_lane["smoke_request"]))
    patch_path = project_path(str(active_lane["patch_points"]))
    requirements_path = project_path(str(active_lane["runtime_requirements"]))
    workflow = read_json(workflow_path)
    smoke = read_json(smoke_path)
    patch_points = read_json(patch_path)
    requirements = read_json(requirements_path)

    errors = []
    if smoke.get("execution_allowed") is not False:
        errors.append("execution_allowed_not_false")
    patched_prompt, patch_errors, applied = patch_prompt(workflow, patch_points, smoke.get("request_patch_values", {}))
    errors.extend(patch_errors)
    errors.extend(verify_applied(patched_prompt, applied))

    prompt_payload = {
        "prompt": patched_prompt,
        "client_id": f"codex-local-dry-run-{lane_id}-{STAMP}",
        "extra_data": {
            "lane_id": lane_id,
            "source": "base_generation_smoke_prompt_materialization",
            "execution_allowed": False,
            "created_iso": ISO_TS,
        },
    }
    lane_dir = RUN_ROOT / lane_id
    prompt_file = lane_dir / "prompt_request.json"
    prompt_only_file = lane_dir / "prompt_only.json"
    manifest_file = lane_dir / "PROMPT_MATERIALIZATION_MANIFEST.json"
    write_json(prompt_file, prompt_payload)
    write_json(prompt_only_file, patched_prompt)

    expected_outputs = smoke.get("expected_outputs", {})
    manifest = {
        "schema_version": "1.0",
        "lane_id": lane_id,
        "created_iso": ISO_TS,
        "workflow": rel(workflow_path),
        "smoke_request": rel(smoke_path),
        "patch_points": rel(patch_path),
        "runtime_requirements": rel(requirements_path),
        "prompt_request": rel(prompt_file),
        "prompt_only": rel(prompt_only_file),
        "workflow_sha256": sha256_file(workflow_path),
        "smoke_request_sha256": sha256_file(smoke_path),
        "patch_points_sha256": sha256_file(patch_path),
        "runtime_requirements_sha256": sha256_file(requirements_path),
        "prompt_request_sha256": sha256_file(prompt_file),
        "patches_applied": len(applied),
        "applied_patch_records": applied,
        "expected_outputs": expected_outputs,
        "required_models": requirements.get("required_models", []),
        "required_input_assets": requirements.get("required_input_assets", []),
        "errors": errors,
        "pass": not errors,
    }
    write_json(manifest_file, manifest)
    manifest["manifest_path"] = rel(manifest_file)
    manifest["manifest_sha256"] = sha256_file(manifest_file)
    write_json(manifest_file, manifest)
    return manifest


def main() -> int:
    active = read_json(ACTIVE_LANES)
    lane_reports = [materialize_lane(lane) for lane in active.get("lanes", []) if isinstance(lane, dict)]
    failed = [lane for lane in lane_reports if not lane.get("pass")]
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_SMOKE_PROMPT_MATERIALIZATION_{STAMP}",
        "created_iso": ISO_TS,
        "active_lanes_path": rel(ACTIVE_LANES),
        "runtime_artifact_root": rel(RUN_ROOT),
        "counts": {
            "lanes_materialized": len(lane_reports),
            "failed_lanes": len(failed),
            "prompt_requests_written": len(lane_reports),
        },
        "lane_reports": lane_reports,
        "runtime_boundary": {
            "dry_run_only": True,
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
    payload["pass"] = not failed
    payload["decision"] = "base_generation_smoke_prompt_materialization_passed" if payload["pass"] else "blocked_base_generation_smoke_prompt_materialization_gap"
    write_json(OUT_FILE, payload)
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "runtime_artifact_root": rel(RUN_ROOT),
        "counts": payload["counts"],
        "failed_lanes": [lane["lane_id"] for lane in failed],
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
