from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
TRACKER_CANONICAL_MIRROR = TRACKER_EVIDENCE_DIR / "Wave64/workflow_static_validation.json"
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
RUNTIME_READINESS_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"
ITEM_REPORT = PLAN_ROOT / "Items/Reports/ITEM-W64-036_workflow_static_validation.json"

ACTIVE_LANES = PROJECT_ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
PROTOCOL = PLAN_ROOT / "Instructions/QA/COMFYUI_WORKFLOW_TESTING_PROTOCOL.md"
EVIDENCE = QA_DIR / "workflow_static_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"WORKFLOW_STATIC_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"WORKFLOW_STATIC_VALIDATION_{STAMP}.json"
LANE_CSV = QA_DIR / f"workflow_static_validation_lanes_{STAMP}.csv"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    PLAN_ROOT / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PLAN_ROOT / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    PLAN_ROOT / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
]

TRACKER_ID = "TRK-W64-036"
ITEM_ID = "ITEM-W64-036"
MODEL_INPUT_KEYS = {
    "ckpt_name",
    "control_net_name",
    "lora_name",
    "vae_name",
    "model_name",
    "upscale_model_name",
}
FLUX_LANE_ID = "flux1_dev_primary_base"
FLUX_MODEL_FILENAME = "flux1-dev-fp8.safetensors"
FLUX_MODEL_SHA256 = "8e91b68084b53a7fc44ed2a3756d821e355ac1a7b6fe29be760c1db532f3d88a"
FLUX_MODEL_BYTES = 17246524772


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def resolve_project_path(value: object) -> Path:
    text = str(value or "").replace("/", "\\")
    path = Path(text)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["lane_id", "result"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_valid_raw_object_info_map(candidate: object) -> bool:
    if not isinstance(candidate, dict):
        return False
    if len(candidate) < 100:
        return False
    if "KSampler" not in candidate or "SaveImage" not in candidate:
        return False
    return all(isinstance(value, dict) for value in candidate.values())


def latest_object_info() -> tuple[Path | None, dict[str, object]]:
    for path in sorted(RUNTIME_READINESS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        candidates = []
        if "object_info" in payload:
            candidates.append(payload.get("object_info"))
        candidates.append(payload)
        for candidate in candidates:
            if is_valid_raw_object_info_map(candidate):
                return path, dict(candidate)
    return None, {}


def latest_flux_model_preflight() -> tuple[Path | None, dict[str, object], dict[str, str], list[str], dict[str, object]]:
    issues: list[str] = []
    current_rehash: dict[str, object] = {
        "attempted": False,
        "path": "",
        "observed_bytes": 0,
        "observed_sha256": "",
        "size_match": False,
        "hash_match": False,
    }
    candidates = sorted(
        RUNTIME_READINESS_DIR.glob("W66_FLUX1_DEV_EXISTING_EXTERNAL_MODEL_PREFLIGHT_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None, {}, {}, ["flux_external_model_preflight_missing"], current_rehash
    path = candidates[0]
    try:
        payload = read_json(path)
    except Exception as exc:
        return path, {}, {}, [f"flux_external_model_preflight_parse_failed:{exc}"], current_rehash
    if not isinstance(payload, dict):
        return path, {}, {}, ["flux_external_model_preflight_not_object"], current_rehash

    expected_top = {
        "lane_id": FLUX_LANE_ID,
        "result": "pass_local_gpu_generation_candidate",
        "failed_check_count": 0,
        "local_only": True,
        "aws_contacted": False,
        "comfyui_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "local_dev_replaces_ec2_final_proof": False,
        "ec2_final_proof_still_required": True,
    }
    for key, expected in expected_top.items():
        if payload.get(key) != expected:
            issues.append(f"flux_external_model_preflight_{key}_mismatch:{payload.get(key)!r}")
    extra_paths = payload.get("configured_extra_model_paths")
    if not isinstance(extra_paths, dict) or extra_paths.get("status") != "ready":
        issues.append("flux_external_model_paths_not_ready")
    runtime_req = payload.get("runtime_requirements")
    if not isinstance(runtime_req, dict):
        issues.append("flux_external_model_runtime_requirements_missing")
    else:
        if runtime_req.get("status") != "ready":
            issues.append("flux_external_model_runtime_requirements_not_ready")
        if runtime_req.get("required_model_count") != 1:
            issues.append("flux_external_model_required_model_count_not_one")
        if runtime_req.get("hash_verified_model_count") != 1:
            issues.append("flux_external_model_hash_verified_count_not_one")
        if runtime_req.get("hash_mismatch_count") != 0:
            issues.append("flux_external_model_hash_mismatch_present")

    trusted_hits: dict[str, str] = {}
    models = payload.get("local_required_models")
    if not isinstance(models, list) or len(models) != 1 or not isinstance(models[0], dict):
        issues.append("flux_external_model_record_count_not_one")
    else:
        model = models[0]
        expected_model = {
            "filename": FLUX_MODEL_FILENAME,
            "comfyui_model_subdir": "checkpoints",
            "expected_sha256": FLUX_MODEL_SHA256,
            "observed_sha256": FLUX_MODEL_SHA256,
            "contract_valid": True,
            "exists_locally": True,
            "hash_match": True,
        }
        for key, expected in expected_model.items():
            if model.get(key) != expected:
                issues.append(f"flux_external_model_{key}_mismatch:{model.get(key)!r}")
        existing_path = str(model.get("existing_path", ""))
        if not existing_path:
            issues.append("flux_external_model_existing_path_missing")
        else:
            resolved_model_path = resolve_project_path(existing_path).resolve()
            current_rehash["attempted"] = True
            current_rehash["path"] = evidence_path(resolved_model_path)
            if not resolved_model_path.is_file():
                issues.append("flux_external_model_current_file_missing")
            else:
                observed_bytes = resolved_model_path.stat().st_size
                observed_sha256 = sha256_file(resolved_model_path)
                current_rehash.update({
                    "observed_bytes": observed_bytes,
                    "observed_sha256": observed_sha256,
                    "size_match": observed_bytes == FLUX_MODEL_BYTES,
                    "hash_match": observed_sha256 == FLUX_MODEL_SHA256,
                })
                if observed_bytes != FLUX_MODEL_BYTES:
                    issues.append(f"flux_external_model_current_size_mismatch:{observed_bytes}")
                if observed_sha256 != FLUX_MODEL_SHA256:
                    issues.append(f"flux_external_model_current_sha256_mismatch:{observed_sha256}")
        if not issues:
            trusted_hits[FLUX_MODEL_FILENAME] = existing_path
    return path, payload, trusted_hits, issues, current_rehash


def collect_model_refs(workflow: dict[str, object]) -> list[str]:
    refs: list[str] = []
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        for key, value in inputs.items():
            if key in MODEL_INPUT_KEYS and isinstance(value, str):
                refs.append(value)
    return sorted(set(refs))


def validate_api_links(workflow: dict[str, object]) -> list[str]:
    issues: list[str] = []
    node_ids = set(workflow.keys())
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            issues.append(f"{node_id}: node_not_object")
            continue
        if not node.get("class_type"):
            issues.append(f"{node_id}: missing_class_type")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            issues.append(f"{node_id}: inputs_not_object")
            continue
        for input_name, value in inputs.items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                if value[0] not in node_ids:
                    issues.append(f"{node_id}.{input_name}: missing_link_source:{value[0]}")
                if not isinstance(value[1], int):
                    issues.append(f"{node_id}.{input_name}: output_index_not_int:{value[1]}")
    return issues


def validate_patch_points(workflow: dict[str, object], patch_points: dict[str, object]) -> list[str]:
    issues: list[str] = []
    points = patch_points.get("patch_points") if isinstance(patch_points, dict) else []
    if not isinstance(points, list):
        return ["patch_points_not_list"]
    for point in points:
        if not isinstance(point, dict) or not point.get("required"):
            continue
        node_id = str(point.get("node_id", ""))
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            issues.append(f"{point.get('name')}: missing_node:{node_id}")
            continue
        expected_type = point.get("node_type")
        if expected_type and node.get("class_type") != expected_type:
            issues.append(f"{point.get('name')}: node_type_mismatch:{node_id}:{node.get('class_type')}!={expected_type}")
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        names = []
        if point.get("input"):
            names.append(str(point["input"]))
        names.extend(str(name) for name in point.get("inputs", []) if isinstance(point.get("inputs"), list))
        for name in names:
            if name not in inputs:
                issues.append(f"{point.get('name')}: missing_input:{node_id}.{name}")
    return issues


def validate_smoke_request(smoke: dict[str, object]) -> list[str]:
    issues: list[str] = []
    for key in ["request_patch_values", "expected_outputs", "qa_protocols"]:
        if key not in smoke:
            issues.append(f"missing_{key}")
    if smoke.get("execution_allowed") is not False:
        issues.append("execution_allowed_not_false_for_static_manifest")
    expected = smoke.get("expected_outputs") if isinstance(smoke.get("expected_outputs"), dict) else {}
    if not expected.get("output_prefix"):
        issues.append("missing_expected_output_prefix")
    return issues


def validate_runtime_requirements(workflow: dict[str, object], runtime_req: dict[str, object]) -> list[str]:
    issues: list[str] = []
    class_types = {node.get("class_type") for node in workflow.values() if isinstance(node, dict)}
    for node_type in runtime_req.get("required_nodes", []) if isinstance(runtime_req.get("required_nodes"), list) else []:
        if node_type not in class_types:
            issues.append(f"required_node_missing:{node_type}")
    workflow_refs = set(collect_model_refs(workflow))
    for model in runtime_req.get("required_models", []) if isinstance(runtime_req.get("required_models"), list) else []:
        if not isinstance(model, dict):
            continue
        filename = model.get("filename")
        if filename and filename not in workflow_refs:
            issues.append(f"required_model_not_referenced:{filename}")
    return issues


def model_local_hits(model_refs: list[str]) -> dict[str, str]:
    roots = [
        PROJECT_ROOT / "Runtime_Data/models/checkpoints",
        PROJECT_ROOT / "Runtime_Data/models/controlnet",
        PROJECT_ROOT / "Runtime_Data/models/loras",
        PROJECT_ROOT / "Runtime_Data/models/upscale_models",
        PROJECT_ROOT / "Runtime_Data/models/vae",
        PROJECT_ROOT / "models/checkpoints",
        PROJECT_ROOT / "models/controlnet",
        PROJECT_ROOT / "models/loras",
        PROJECT_ROOT / "models/upscale_models",
        PROJECT_ROOT / "models/vae",
        PROJECT_ROOT / "ComfyUI/models/checkpoints",
        PROJECT_ROOT / "ComfyUI/models/controlnet",
        PROJECT_ROOT / "ComfyUI/models/loras",
        PROJECT_ROOT / "ComfyUI/models/upscale_models",
        PROJECT_ROOT / "ComfyUI/models/vae",
    ]
    hits: dict[str, str] = {}
    for ref in model_refs:
        for root in roots:
            direct = root / ref
            if direct.exists():
                hits[ref] = evidence_path(direct)
                break
    return hits


def validate_lane(
    lane: dict[str, object],
    object_info: dict[str, object],
    trusted_flux_model_hits: dict[str, str],
    flux_preflight_issues: list[str],
) -> dict[str, object]:
    lane_id = str(lane.get("lane_id", ""))
    workflow_path = resolve_project_path(lane.get("workflow"))
    smoke_path = resolve_project_path(lane.get("smoke_request"))
    runtime_path = resolve_project_path(lane.get("runtime_requirements"))
    patch_path = resolve_project_path(lane.get("patch_points"))
    structural_issues: list[str] = []
    parse_pass = True
    workflow: dict[str, object] = {}
    smoke: dict[str, object] = {}
    runtime_req: dict[str, object] = {}
    patch_points: dict[str, object] = {}
    for label, path in [
        ("workflow", workflow_path),
        ("smoke_request", smoke_path),
        ("runtime_requirements", runtime_path),
        ("patch_points", patch_path),
    ]:
        if not path.exists():
            structural_issues.append(f"{label}_missing:{path}")
            parse_pass = False
            continue
        try:
            data = read_json(path)
        except Exception as exc:
            structural_issues.append(f"{label}_json_parse_failed:{exc}")
            parse_pass = False
            continue
        if label == "workflow" and isinstance(data, dict):
            workflow = data
        elif label == "smoke_request" and isinstance(data, dict):
            smoke = data
        elif label == "runtime_requirements" and isinstance(data, dict):
            runtime_req = data
        elif label == "patch_points" and isinstance(data, dict):
            patch_points = data
        else:
            structural_issues.append(f"{label}_not_object")
            parse_pass = False
    workflow_sha256 = sha256_file(workflow_path) if workflow_path.exists() else ""
    smoke_request_sha256 = sha256_file(smoke_path) if smoke_path.exists() else ""
    runtime_requirements_sha256 = sha256_file(runtime_path) if runtime_path.exists() else ""
    patch_points_sha256 = sha256_file(patch_path) if patch_path.exists() else ""
    if workflow:
        structural_issues.extend(validate_api_links(workflow))
        if not any(isinstance(node, dict) and node.get("class_type") == "SaveImage" for node in workflow.values()):
            structural_issues.append("missing_SaveImage_node")
    if workflow and patch_points:
        structural_issues.extend(validate_patch_points(workflow, patch_points))
    if smoke:
        structural_issues.extend(validate_smoke_request(smoke))
    if workflow and runtime_req:
        structural_issues.extend(validate_runtime_requirements(workflow, runtime_req))

    class_types = sorted({str(node.get("class_type")) for node in workflow.values() if isinstance(node, dict) and node.get("class_type")})
    object_info_is_raw_node_map = is_valid_raw_object_info_map(object_info)
    missing_object_info = [node_type for node_type in class_types if object_info_is_raw_node_map and node_type not in object_info]
    object_info_issues: list[str] = []
    if not object_info:
        object_info_issues.append("object_info_snapshot_missing")
    elif not object_info_is_raw_node_map:
        object_info_issues.append("object_info_raw_node_class_map_unavailable")
    elif missing_object_info:
        object_info_issues.extend(f"object_info_missing_node:{node_type}" for node_type in missing_object_info)

    refs = collect_model_refs(workflow)
    local_hits = model_local_hits(refs)
    model_dependency_evidence = "direct_project_model_search"
    if lane_id == FLUX_LANE_ID:
        if flux_preflight_issues:
            local_model_preflight_issues = list(flux_preflight_issues)
        else:
            local_model_preflight_issues = []
            for ref in refs:
                if ref in trusted_flux_model_hits:
                    local_hits[ref] = trusted_flux_model_hits[ref]
            model_dependency_evidence = "hash_verified_configured_external_model_preflight"
    else:
        local_model_preflight_issues = []
    missing_local_refs = [ref for ref in refs if ref not in local_hits]
    local_model_issues = [
        *local_model_preflight_issues,
        *[f"local_model_reference_missing:{ref}" for ref in missing_local_refs],
    ]
    issues = [*structural_issues, *object_info_issues, *local_model_issues]
    structural_static_pass = parse_pass and not structural_issues
    object_info_static_pass = not object_info_issues
    local_model_dependency_pass = not local_model_issues
    runtime_proof_present = False
    result = "PASS" if parse_pass and not issues else "FAIL"
    return {
        "lane_id": lane_id,
        "workflow": rel(workflow_path) if workflow_path.exists() else str(workflow_path),
        "workflow_sha256": workflow_sha256,
        "smoke_request_sha256": smoke_request_sha256,
        "runtime_requirements_sha256": runtime_requirements_sha256,
        "patch_points_sha256": patch_points_sha256,
        "parse_pass": parse_pass,
        "structural_static_pass": structural_static_pass,
        "structural_issue_count": len(structural_issues),
        "object_info_static_pass": object_info_static_pass,
        "object_info_issue_count": len(object_info_issues),
        "local_model_dependency_pass": local_model_dependency_pass,
        "local_model_dependency_issue_count": len(local_model_issues),
        "runtime_proof_present": runtime_proof_present,
        "api_link_issue_count": len([issue for issue in issues if "missing_link_source" in issue or "output_index" in issue or "missing_class_type" in issue]),
        "issue_count": len(issues),
        "result": result,
        "node_count": len(workflow),
        "node_type_count": len(class_types),
        "model_reference_count": len(refs),
        "missing_local_model_reference_count": len(missing_local_refs),
        "missing_local_model_references": missing_local_refs,
        "local_model_hits": local_hits,
        "model_dependency_evidence": model_dependency_evidence,
        "external_model_hash_verified": lane_id == FLUX_LANE_ID and not local_model_issues,
        "object_info_missing_node_count": len(missing_object_info),
        "object_info_missing_nodes": missing_object_info,
        "issues": issues[:100],
    }


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
    marker = "## Immediate Next Action - Wave64 Workflow Static Validation"
    marker_index = existing.find(marker)
    if marker_index >= 0:
        next_heading = existing.find("\n## ", marker_index + len(marker))
        if next_heading >= 0:
            existing = existing[:marker_index] + existing[next_heading + 1 :]
        else:
            existing = existing[:marker_index]
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    stamped_path = rel(STAMPED_EVIDENCE)
    with proof_path.open("r", encoding="utf-8-sig", newline="") as f:
        if any(
            row.get("Task") == TRACKER_ID and stamped_path in row.get("Evidence_Path", "")
            for row in csv.DictReader(f)
        ):
            return
    line = [
        ISO_TS,
        "64",
        TRACKER_ID,
        "Ran bounded static validation over active base-generation API workflows without runtime execution.",
        "; ".join(payload["evidence_paths"]),
        "API JSON parse; node-link check; patch-point check; runtime requirements check; smoke request check; object_info static check",
        payload["qa_decision"],
        rel(EVIDENCE),
        "Address exact workflow static blockers or advance to runtime smoke only after local static blockers clear.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Wave64 workflow static validation evidence.")
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Write evidence outputs only and skip tracker/items/hydration/proof-log mutations.",
    )
    args = parser.parse_args()
    lanes_payload = read_json(ACTIVE_LANES)
    lanes = lanes_payload.get("lanes", []) if isinstance(lanes_payload, dict) else []
    prior_payload = read_json(EVIDENCE) if EVIDENCE.exists() else None
    prior_evidence_sha256 = sha256_file(EVIDENCE) if EVIDENCE.exists() else ""
    active_lanes_sha256 = sha256_file(ACTIVE_LANES)
    object_info_path, object_info = latest_object_info()
    object_info_evidence_sha256 = sha256_file(object_info_path) if object_info_path and object_info_path.exists() else ""
    flux_preflight_path, flux_preflight, trusted_flux_model_hits, flux_preflight_issues, flux_current_rehash = latest_flux_model_preflight()
    flux_preflight_sha256 = sha256_file(flux_preflight_path) if flux_preflight_path and flux_preflight_path.exists() else ""
    lane_results = [
        validate_lane(lane, object_info, trusted_flux_model_hits, flux_preflight_issues)
        for lane in lanes
        if isinstance(lane, dict)
    ]
    summary_counts = Counter(str(result["result"]) for result in lane_results)
    failed = [result for result in lane_results if result["result"] != "PASS"]
    failed_issues = [
        str(issue)
        for result in failed
        for issue in result.get("issues", [])
    ]
    local_model_only_blocker = bool(failed) and all(
        result.get("structural_static_pass")
        and result.get("object_info_static_pass")
        and not result.get("local_model_dependency_pass")
        for result in failed
    )
    missing_local_model_references = sorted({
        str(ref)
        for result in failed
        for ref in result.get("missing_local_model_references", [])
    })
    qa_decision = (
        "workflow_static_validation_passed_nonmask_safe_no_runtime"
        if not failed
        else "blocked_local_model_dependency_provisioning_required"
        if local_model_only_blocker
        else "blocked_workflow_static_validation_api_contract_or_object_info_gaps"
    )
    current_lane_ids = sorted(str(result.get("lane_id", "")) for result in lane_results if str(result.get("lane_id", "")))
    prior_lane_ids = []
    historical_hash_comparison_available = False
    prior_lane_hashes_by_id: dict[str, dict[str, str]] = {}
    if isinstance(prior_payload, dict):
        prior_lane_ids = sorted(
            str(entry.get("lane_id", ""))
            for entry in prior_payload.get("lane_results", [])
            if isinstance(entry, dict) and str(entry.get("lane_id", ""))
        )
        historical_hash_comparison_available = all(
            isinstance(entry, dict)
            and all(
                isinstance(entry.get(key), str) and bool(entry.get(key))
                for key in [
                    "workflow_sha256",
                    "smoke_request_sha256",
                    "runtime_requirements_sha256",
                    "patch_points_sha256",
                ]
            )
            for entry in prior_payload.get("lane_results", [])
            if isinstance(entry, dict)
        ) and bool(prior_payload.get("lane_results"))
        if historical_hash_comparison_available:
            for entry in prior_payload.get("lane_results", []):
                if not isinstance(entry, dict):
                    continue
                lane_id = str(entry.get("lane_id", ""))
                if not lane_id:
                    continue
                prior_lane_hashes_by_id[lane_id] = {
                    "workflow_sha256": str(entry.get("workflow_sha256", "")),
                    "smoke_request_sha256": str(entry.get("smoke_request_sha256", "")),
                    "runtime_requirements_sha256": str(entry.get("runtime_requirements_sha256", "")),
                    "patch_points_sha256": str(entry.get("patch_points_sha256", "")),
                }
    added_lane_ids = sorted(set(current_lane_ids) - set(prior_lane_ids))
    removed_lane_ids = sorted(set(prior_lane_ids) - set(current_lane_ids))
    current_lane_hashes_by_id = {
        str(result["lane_id"]): {
            "workflow_sha256": str(result.get("workflow_sha256", "")),
            "smoke_request_sha256": str(result.get("smoke_request_sha256", "")),
            "runtime_requirements_sha256": str(result.get("runtime_requirements_sha256", "")),
            "patch_points_sha256": str(result.get("patch_points_sha256", "")),
        }
        for result in lane_results
    }

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"WORKFLOW_STATIC_VALIDATION_{STAMP}",
        "created_iso": ISO_TS,
        "wave": 64,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "task": "Validate active base-generation ComfyUI API workflows before runtime.",
        "protocol": rel(PROTOCOL),
        "active_lanes": rel(ACTIVE_LANES),
        "active_lanes_sha256": active_lanes_sha256,
        "object_info_evidence": rel(object_info_path) if object_info_path else "",
        "object_info_evidence_sha256": object_info_evidence_sha256,
        "flux_external_model_preflight": {
            "path": rel(flux_preflight_path) if flux_preflight_path else "",
            "sha256": flux_preflight_sha256,
            "accepted_for_static_model_presence": not flux_preflight_issues,
            "issues": flux_preflight_issues,
            "license_acceptance_asserted": False,
            "live_model_load_proven": False,
            "generation_executed": bool(flux_preflight.get("generation_executed", False)),
            "current_file_rehash": flux_current_rehash,
        },
        "lane_count": len(lane_results),
        "summary_counts": dict(summary_counts),
        "failed_lane_count": len(failed),
        "lane_results": lane_results,
        "gold_mask_dependency_boundary": {
            "mask_truth_consumed": False,
            "masks_promoted": False,
            "hard_gates_rerun": False,
            "wave71_activation_attempted": False,
        },
        "runtime_execution": {
            "local_generation_executed": False,
            "ec2_started": False,
            "reason": "Static validation only; runtime smoke remains a separate gate.",
        },
        "blocking_model_references": missing_local_model_references,
        "qa_decision": qa_decision,
        "runtime_proof_present": False,
        "prior_canonical_evidence": {
            "path": rel(EVIDENCE),
            "sha256": prior_evidence_sha256,
            "exists": EVIDENCE.exists(),
            "prior_lane_ids": prior_lane_ids,
            "historical_hash_comparison_available": historical_hash_comparison_available,
            "prior_lane_hashes_by_id": prior_lane_hashes_by_id,
        },
        "current_lane_ids": current_lane_ids,
        "added_lane_ids": added_lane_ids,
        "removed_lane_ids": removed_lane_ids,
        "current_lane_hashes_by_id": current_lane_hashes_by_id,
        "next_step": (
            "Resolve the exact missing local model dependency evidence before runtime smoke."
            if local_model_only_blocker
            else "Preserve the static pass; retain the FLUX noncommercial-license and live model-load/output/QA boundaries before execution or promotion."
            if not failed
            else "Fix exact static workflow blockers before any runtime smoke."
        ),
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(LANE_CSV),
        rel(TRACKER_CANONICAL_MIRROR),
        rel(ITEM_REPORT),
    ]
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    TRACKER_CANONICAL_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_CANONICAL_MIRROR.write_bytes(EVIDENCE.read_bytes())
    csv_rows = []
    for result in lane_results:
        csv_rows.append({
            "lane_id": result["lane_id"],
            "result": result["result"],
            "workflow_sha256": result["workflow_sha256"],
            "smoke_request_sha256": result["smoke_request_sha256"],
            "runtime_requirements_sha256": result["runtime_requirements_sha256"],
            "patch_points_sha256": result["patch_points_sha256"],
            "structural_static_pass": result["structural_static_pass"],
            "structural_issue_count": result["structural_issue_count"],
            "object_info_static_pass": result["object_info_static_pass"],
            "object_info_issue_count": result["object_info_issue_count"],
            "local_model_dependency_pass": result["local_model_dependency_pass"],
            "local_model_dependency_issue_count": result["local_model_dependency_issue_count"],
            "runtime_proof_present": result["runtime_proof_present"],
            "issue_count": result["issue_count"],
            "node_count": result["node_count"],
            "model_reference_count": result["model_reference_count"],
            "missing_local_model_reference_count": result["missing_local_model_reference_count"],
            "missing_local_model_references": "|".join(result["missing_local_model_references"]),
            "object_info_missing_node_count": result["object_info_missing_node_count"],
            "issues": "|".join(result["issues"]),
            "workflow": result["workflow"],
        })
    write_csv(LANE_CSV, csv_rows)

    if args.evidence_only:
        print(json.dumps({
            "evidence": str(EVIDENCE),
            "stamped_evidence": str(STAMPED_EVIDENCE),
            "tracker_evidence": str(TRACKER_EVIDENCE),
            "tracker_canonical_mirror": str(TRACKER_CANONICAL_MIRROR),
            "lane_csv": str(LANE_CSV),
            "qa_decision": qa_decision,
            "lane_count": len(lane_results),
            "summary_counts": dict(summary_counts),
            "failed_lane_count": len(failed),
            "evidence_only": True,
            "historical_hash_comparison_available": historical_hash_comparison_available,
        }, indent=2))
        return

    completed_status = "Completed_Workflow_Static_Validation_Pass"
    blocked_status = (
        "Blocked_Local_Model_Dependency_Evidence_Missing"
        if local_model_only_blocker
        else "Blocked_Workflow_Static_Validation_Gaps"
    )
    row_status = completed_status if not failed else blocked_status

    note = (
        f"Wave64 workflow static validation {STAMP}: checked {len(lane_results)} active base-generation API workflows; "
        f"summary={dict(summary_counts)}; decision={qa_decision}. Static only: no EC2 start, no generation, no mask truth."
    )
    coverage_additions = [
        "wave64_workflow_static_validation_ran",
        qa_decision,
        "allowed_nonmask_work_can_continue",
    ]
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            TRACKER_ID,
            {
                "Status": row_status,
                "Status_Decision": qa_decision,
                "Evidence_Path": payload["evidence_paths"],
                "Coverage_Audit_Status": coverage_additions,
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
                "Status": row_status,
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    next_action = (
        "retain the FLUX license-rights boundary, then run a bounded local model-list/object_info/model-load proof only after use rights are documented"
        if not failed
        else "resolve the exact missing local model dependency evidence before runtime smoke"
        if local_model_only_blocker
        else "fix the exact static workflow API/object_info blockers recorded in the lane CSV before runtime smoke"
    )
    top_block = f"""
## Immediate Next Action - Wave64 Workflow Static Validation - {ISO_TS}

Worked concrete non-mask orchestration task `{TRACKER_ID}` / `{ITEM_ID}`: ComfyUI workflow static validation.

Result: checked `{len(lane_results)}` active base-generation API workflows from `{rel(ACTIVE_LANES)}`. Summary: `{dict(summary_counts)}`. Decision: `{qa_decision}`.

FLUX boundary: the existing configured external checkpoint is accepted for static presence only when its preflight records the exact required SHA256. License acceptance, live model loading, output, technical QA, visual QA, target-runtime proof, and certification remain unproven.

Runtime boundary: no local generation was executed, EC2 was not started, no masks were consumed as truth, no masks were promoted, no hard gates were rerun, and no Wave71+ activation was attempted.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(LANE_CSV)}`

Next exact local action: {next_action}.
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
## Wave64 Workflow Static Validation - {ISO_TS}

Bounded static validation for active base-generation ComfyUI API workflows; no runtime execution and no mask truth consumed.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(STAMPED_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE)}`
- `{rel(LANE_CSV)}`
""",
    )
    append_proof_log(payload)

    flux_result = next((result for result in lane_results if result.get("lane_id") == FLUX_LANE_ID), {})
    report = {
        "schema_version": "1.0",
        "report_id": f"ITEM-W64-036-WORKFLOW-STATIC-VALIDATION-{STAMP}",
        "timestamp": ISO_TS,
        "item_id": ITEM_ID,
        "tracker_id": TRACKER_ID,
        "workstream": "workflow_static_validation",
        "status": row_status,
        "row_complete": not failed,
        "current_scope": {
            "active_lanes_sha256": active_lanes_sha256,
            "lane_count": len(lane_results),
            "pass_count": int(summary_counts.get("PASS", 0)),
            "fail_count": int(summary_counts.get("FAIL", 0)),
            "runtime_proof_present": False,
        },
        FLUX_LANE_ID: {
            "workflow_sha256": flux_result.get("workflow_sha256", ""),
            "runtime_requirements_sha256": flux_result.get("runtime_requirements_sha256", ""),
            "structural_static_pass": flux_result.get("structural_static_pass", False),
            "object_info_static_pass": flux_result.get("object_info_static_pass", False),
            "local_model_dependency_pass": flux_result.get("local_model_dependency_pass", False),
            "external_model_hash_verified": flux_result.get("external_model_hash_verified", False),
            "model_dependency_evidence": flux_result.get("model_dependency_evidence", ""),
            "local_model_hits": flux_result.get("local_model_hits", {}),
            "runtime_proof_present": False,
            "license_acceptance_asserted": False,
            "automated_install_performed": False,
        },
        "validation": {
            "qa_decision": qa_decision,
            "preflight_path": rel(flux_preflight_path) if flux_preflight_path else "",
            "preflight_sha256": flux_preflight_sha256,
            "preflight_accepted": not flux_preflight_issues,
            "preflight_issues": flux_preflight_issues,
            "canonical_tracker_mirror_exact": True,
        },
        "evidence": [
            {"path": rel(EVIDENCE), "sha256": sha256_file(EVIDENCE)},
            {"path": rel(LANE_CSV), "sha256": sha256_file(LANE_CSV)},
            {
                "path": rel(flux_preflight_path) if flux_preflight_path else "",
                "sha256": flux_preflight_sha256,
            },
            {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        ],
        "runtime_boundaries": {
            "comfyui_contacted": False,
            "generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "model_downloaded_or_copied": False,
            "mask_truth_consumed": False,
            "mask_promotion_executed": False,
            "wave70_hard_gate_executed": False,
            "wave71_activated": False,
        },
        "residual_blockers": [
            "FLUX.1 Dev noncommercial-license acceptance and use rights are not asserted by automation.",
            "Lane-specific live object_info/model listing, model load, output, technical QA, visual QA, target-runtime proof, and certification remain unproven.",
        ],
        "next_action": next_action,
    }
    write_json(ITEM_REPORT, report)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "stamped_evidence": str(STAMPED_EVIDENCE),
        "lane_csv": str(LANE_CSV),
        "qa_decision": qa_decision,
        "lane_count": len(lane_results),
        "summary_counts": dict(summary_counts),
        "failed_lane_count": len(failed),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
