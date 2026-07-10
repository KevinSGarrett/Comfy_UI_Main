from __future__ import annotations

import csv
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
HYDRATION_DIR = PLAN_ROOT / "Instructions/Hydration_Rehydration"
RUNTIME_READINESS_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"

ACTIVE_LANES = PROJECT_ROOT / "Workflows/base_generation/ACTIVE_LANES.json"
PROTOCOL = PLAN_ROOT / "Instructions/QA/COMFYUI_WORKFLOW_TESTING_PROTOCOL.md"
EVIDENCE = QA_DIR / "workflow_static_validation.json"
STAMPED_EVIDENCE = QA_DIR / f"WORKFLOW_STATIC_VALIDATION_{STAMP}.json"
TRACKER_EVIDENCE = TRACKER_EVIDENCE_DIR / f"WORKFLOW_STATIC_VALIDATION_{STAMP}.json"
LANE_CSV = QA_DIR / f"workflow_static_validation_lanes_{STAMP}.csv"

TRACKER_FILES = [
    PLAN_ROOT / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
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


def latest_object_info() -> tuple[Path | None, dict[str, object]]:
    for path in sorted(RUNTIME_READINESS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("object_info"), dict):
            return path, payload["object_info"]
    return None, {}


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


def validate_lane(lane: dict[str, object], object_info: dict[str, object]) -> dict[str, object]:
    lane_id = str(lane.get("lane_id", ""))
    workflow_path = resolve_project_path(lane.get("workflow"))
    smoke_path = resolve_project_path(lane.get("smoke_request"))
    runtime_path = resolve_project_path(lane.get("runtime_requirements"))
    patch_path = resolve_project_path(lane.get("patch_points"))
    issues: list[str] = []
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
            issues.append(f"{label}_missing:{path}")
            parse_pass = False
            continue
        try:
            data = read_json(path)
        except Exception as exc:
            issues.append(f"{label}_json_parse_failed:{exc}")
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
            issues.append(f"{label}_not_object")
            parse_pass = False
    if workflow:
        issues.extend(validate_api_links(workflow))
        if not any(isinstance(node, dict) and node.get("class_type") == "SaveImage" for node in workflow.values()):
            issues.append("missing_SaveImage_node")
    if workflow and patch_points:
        issues.extend(validate_patch_points(workflow, patch_points))
    if smoke:
        issues.extend(validate_smoke_request(smoke))
    if workflow and runtime_req:
        issues.extend(validate_runtime_requirements(workflow, runtime_req))

    class_types = sorted({str(node.get("class_type")) for node in workflow.values() if isinstance(node, dict) and node.get("class_type")})
    object_info_is_raw_node_map = bool(object_info) and not {"status", "node_count"}.issubset(set(object_info.keys()))
    missing_object_info = [node_type for node_type in class_types if object_info_is_raw_node_map and node_type not in object_info]
    if not object_info:
        issues.append("object_info_snapshot_missing")
    elif not object_info_is_raw_node_map:
        issues.append("object_info_raw_node_class_map_unavailable")
    elif missing_object_info:
        issues.extend(f"object_info_missing_node:{node_type}" for node_type in missing_object_info)

    refs = collect_model_refs(workflow)
    local_hits = model_local_hits(refs)
    missing_local_refs = [ref for ref in refs if ref not in local_hits]
    issues.extend(f"local_model_reference_missing:{ref}" for ref in missing_local_refs)
    result = "PASS" if parse_pass and not issues else "FAIL"
    return {
        "lane_id": lane_id,
        "workflow": rel(workflow_path) if workflow_path.exists() else str(workflow_path),
        "parse_pass": parse_pass,
        "api_link_issue_count": len([issue for issue in issues if "missing_link_source" in issue or "output_index" in issue or "missing_class_type" in issue]),
        "issue_count": len(issues),
        "result": result,
        "node_count": len(workflow),
        "node_type_count": len(class_types),
        "model_reference_count": len(refs),
        "missing_local_model_reference_count": len(missing_local_refs),
        "missing_local_model_references": missing_local_refs,
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
    path.write_text(block.lstrip() + "\n\n" + existing.lstrip(), encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
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
    lanes_payload = read_json(ACTIVE_LANES)
    lanes = lanes_payload.get("lanes", []) if isinstance(lanes_payload, dict) else []
    object_info_path, object_info = latest_object_info()
    lane_results = [validate_lane(lane, object_info) for lane in lanes if isinstance(lane, dict)]
    summary_counts = Counter(str(result["result"]) for result in lane_results)
    failed = [result for result in lane_results if result["result"] != "PASS"]
    failed_issues = [
        str(issue)
        for result in failed
        for issue in result.get("issues", [])
    ]
    local_model_only_blocker = bool(failed) and bool(failed_issues) and all(
        issue.startswith("local_model_reference_missing:")
        for issue in failed_issues
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
        "object_info_evidence": rel(object_info_path) if object_info_path else "",
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
        "next_step": (
            "Provision and hash the exact missing local model asset(s), or record an intentional lane deferral before runtime smoke."
            if local_model_only_blocker
            else "Fix exact static workflow blockers before any runtime smoke, or advance to runtime smoke only if all lanes pass."
        ),
    }
    payload["evidence_paths"] = [
        rel(EVIDENCE),
        rel(STAMPED_EVIDENCE),
        rel(TRACKER_EVIDENCE),
        rel(LANE_CSV),
    ]
    write_json(EVIDENCE, payload)
    write_json(STAMPED_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    csv_rows = []
    for result in lane_results:
        csv_rows.append({
            "lane_id": result["lane_id"],
            "result": result["result"],
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
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
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
                "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
                "Evidence_Required": payload["evidence_paths"],
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    next_action = (
        "advance to TRK-W64-037 workflow runtime smoke proof only after intentional runtime selection"
        if not failed
        else "provision and hash the exact missing local model asset(s), or record an intentional lane deferral before runtime smoke"
        if local_model_only_blocker
        else "fix the exact static workflow API/object_info blockers recorded in the lane CSV before runtime smoke"
    )
    top_block = f"""
## Immediate Next Action - Wave64 Workflow Static Validation - {ISO_TS}

Worked concrete non-mask orchestration task `{TRACKER_ID}` / `{ITEM_ID}`: ComfyUI workflow static validation.

Result: checked `{len(lane_results)}` active base-generation API workflows from `{rel(ACTIVE_LANES)}`. Summary: `{dict(summary_counts)}`. Decision: `{qa_decision}`.

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
