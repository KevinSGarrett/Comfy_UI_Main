from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKFLOW = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_schnell_preview/workflow.api.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_schnell_preview/runtime_requirements.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def http_json(url: str, timeout: int = 60) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_history_entry(history: dict[str, Any], prompt_id: str) -> dict[str, Any]:
    entry = history.get(prompt_id)
    if not isinstance(entry, dict):
        raise ValueError(f"Prompt history is missing {prompt_id}")
    prompt_record = entry.get("prompt")
    if not isinstance(prompt_record, list) or len(prompt_record) < 5:
        raise ValueError("Prompt history has an invalid prompt record")
    if str(prompt_record[1]) != prompt_id:
        raise ValueError("Prompt history ID binding mismatch")
    if not isinstance(prompt_record[2], dict):
        raise ValueError("Prompt history workflow is missing")
    if not isinstance(prompt_record[3], dict):
        raise ValueError("Prompt history extra_data is missing")
    return entry


def history_timing(status: dict[str, Any]) -> dict[str, Any]:
    timestamps: dict[str, int] = {}
    cached_nodes: list[str] | None = None
    for message in status.get("messages", []):
        if not isinstance(message, list) or len(message) != 2 or not isinstance(message[1], dict):
            continue
        event, payload = message
        if event in {"execution_start", "execution_success"} and isinstance(payload.get("timestamp"), int):
            timestamps[event] = payload["timestamp"]
        if event == "execution_cached":
            cached_nodes = [str(item) for item in payload.get("nodes", [])]
    start = timestamps.get("execution_start")
    success = timestamps.get("execution_success")
    return {
        "execution_start_epoch_ms": start,
        "execution_success_epoch_ms": success,
        "elapsed_seconds": round((success - start) / 1000.0, 3) if start is not None and success is not None else None,
        "cached_nodes": cached_nodes,
    }


def output_records(entry: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    outputs = entry.get("outputs", {})
    if not isinstance(outputs, dict):
        return records
    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images", []) or []:
            if isinstance(image, dict):
                records.append(
                    {
                        "node_id": str(node_id),
                        "filename": str(image.get("filename") or ""),
                        "subfolder": str(image.get("subfolder") or ""),
                        "type": str(image.get("type") or ""),
                    }
                )
    return records


def image_qa(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        extrema = rgb.getextrema()
        return {
            "opened": True,
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "channel_mean": [round(value, 6) for value in stat.mean],
            "channel_stddev": [round(value, 6) for value in stat.stddev],
            "nonblank_variance_pass": any(high > low for low, high in extrema),
        }


def checkpoint_options(object_info: dict[str, Any]) -> list[str]:
    try:
        raw = object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"]
    except (KeyError, TypeError) as exc:
        raise ValueError("CheckpointLoaderSimple options are unavailable") from exc
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        return [str(item) for item in raw[0]]
    if isinstance(raw, list) and len(raw) > 1 and isinstance(raw[1], dict):
        return [str(item) for item in raw[1].get("options", [])]
    raise ValueError("CheckpointLoaderSimple options have an unsupported shape")


def validate_visual_review(record: dict[str, Any], artifact_sha256: str) -> list[str]:
    failures: list[str] = []
    if record.get("artifact_sha256") != artifact_sha256:
        failures.append("visual_review_artifact_hash_mismatch")
    checks = record.get("checks")
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        failures.append("visual_review_checks_not_all_true")
    if record.get("visual_pass") is not True:
        failures.append("visual_review_not_passed")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package a completed FLUX.1 Schnell preview without rerunning it")
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--visual-review-record", required=True)
    parser.add_argument("--output-evidence", required=True)
    parser.add_argument("--mirror-evidence", required=True)
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--requirements", default=str(DEFAULT_REQUIREMENTS))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workflow_path = Path(args.workflow).resolve()
    requirements_path = Path(args.requirements).resolve()
    model_path = Path(args.model_path).resolve()
    source_artifact_path = Path(args.artifact_path).resolve()
    visual_review_path = Path(args.visual_review_record).resolve()
    output_path = Path(args.output_evidence).resolve()
    mirror_path = Path(args.mirror_evidence).resolve()

    workflow = load_json(workflow_path)
    requirements = load_json(requirements_path)
    expected_model = requirements["required_models"][0]
    required_nodes = [str(item) for item in requirements["required_nodes"]]
    history = http_json(f"{args.api_url.rstrip('/')}/history/{args.prompt_id}")
    object_info = http_json(f"{args.api_url.rstrip('/')}/object_info")
    entry = extract_history_entry(history, args.prompt_id)
    status = entry.get("status", {})
    prompt_record = entry["prompt"]
    submitted_workflow = prompt_record[2]
    extra_data = prompt_record[3]
    outputs = output_records(entry)
    timing = history_timing(status if isinstance(status, dict) else {})

    model_sha256 = sha256_file(model_path)
    artifact_sha256 = sha256_file(source_artifact_path)
    visual_review = load_json(visual_review_path)
    technical_qa = image_qa(source_artifact_path)
    historical_registry = PROJECT_ROOT / "Plan/10_REGISTRIES/main_flow_wave04_runtime_lanes.json"
    pulled_artifact = output_path.parent / "artifact" / source_artifact_path.name
    expected_pulled_path = pulled_artifact.relative_to(PROJECT_ROOT).as_posix()

    checks = {
        "history_status_success": status.get("status_str") == "success" and status.get("completed") is True,
        "history_workflow_matches_canonical": submitted_workflow == workflow,
        "history_lane_id_matches": extra_data.get("lane_id") == requirements["lane_id"],
        "history_checkpoint_hash_matches": extra_data.get("checkpoint_sha256") == expected_model["sha256"],
        "history_execution_allowed": extra_data.get("execution_allowed") is True,
        "history_execution_not_cached": timing["cached_nodes"] == [],
        "history_timing_complete": timing["elapsed_seconds"] is not None and timing["elapsed_seconds"] > 0,
        "single_output_present": len(outputs) == 1,
        "history_output_filename_matches_artifact": len(outputs) == 1 and outputs[0]["filename"] == source_artifact_path.name,
        "history_output_subfolder_matches_lane": len(outputs) == 1 and outputs[0]["subfolder"] == requirements["lane_id"],
        "history_output_type_is_output": len(outputs) == 1 and outputs[0]["type"] == "output",
        "model_file_present": model_path.is_file(),
        "model_bytes_match": model_path.stat().st_size == expected_model["bytes"],
        "model_sha256_match": model_sha256 == expected_model["sha256"],
        "required_nodes_present": all(node in object_info for node in required_nodes),
        "checkpoint_visible_to_comfyui": expected_model["filename"] in checkpoint_options(object_info),
        "artifact_file_present": source_artifact_path.is_file(),
        "artifact_hash_matches_visual_review": visual_review.get("artifact_sha256") == artifact_sha256,
        "artifact_dimensions_match_contract": technical_qa["width"] == 512 and technical_qa["height"] == 512,
        "artifact_nonblank": technical_qa["nonblank_variance_pass"] is True,
        "direct_visual_review_pass": not validate_visual_review(visual_review, artifact_sha256),
        "visual_review_path_matches_pulled_artifact": visual_review.get("artifact_path") == expected_pulled_path,
        "historical_schnell_lineage_present": historical_registry.is_file() and "true_flux_schnell_reference_smoke" in historical_registry.read_text(encoding="utf-8"),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"FLUX.1 Schnell proof checks failed: {failed}")

    pulled_artifact.parent.mkdir(parents=True, exist_ok=True)
    if pulled_artifact.exists() and sha256_file(pulled_artifact) != artifact_sha256:
        raise RuntimeError(f"Refusing to overwrite a different pulled artifact: {pulled_artifact}")
    if not pulled_artifact.exists():
        shutil.copy2(source_artifact_path, pulled_artifact)

    payload = {
        "schema_version": "1.0",
        "evidence_id": "W64-FLUX1-SCHNELL-FAST-PREVIEW-LOCAL-RUNTIME-20260716T115409-0500",
        "timestamp": "2026-07-16T11:54:49-05:00",
        "lane_id": requirements["lane_id"],
        "classification": "bounded_local_fast_preview_runtime_pass",
        "source_bindings": {
            "workflow": {"path": workflow_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(workflow_path)},
            "runtime_requirements": {"path": requirements_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(requirements_path)},
            "historical_lineage_registry": {"path": historical_registry.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(historical_registry)},
            "visual_review": {"path": visual_review_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(visual_review_path)},
        },
        "model": {
            "filename": expected_model["filename"],
            "source_path": str(model_path),
            "bytes": model_path.stat().st_size,
            "sha256": model_sha256,
            "license_id": requirements["licensed_source"]["license_id"],
            "network_download_performed": False,
            "existing_exact_bytes_reused": True,
        },
        "runtime": {
            "api_url": args.api_url,
            "prompt_id": args.prompt_id,
            "status": status,
            "timing": timing,
            "submitted_workflow_sha256": hashlib.sha256(json.dumps(submitted_workflow, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "history_prompt_record_sha256": hashlib.sha256(json.dumps(prompt_record, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "output_records": outputs,
            "required_node_presence": {node: node in object_info for node in required_nodes},
            "checkpoint_visible": True,
            "new_generation_count": 1,
        },
        "artifact": {
            "path": expected_pulled_path,
            "bytes": pulled_artifact.stat().st_size,
            "sha256": sha256_file(pulled_artifact),
            "technical_qa": technical_qa,
            "direct_visual_qa": visual_review,
        },
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "historical_reuse": {
            "historical_lane_id": "true_flux_schnell_reference_smoke",
            "historical_status": "deconstruct_only_not_promoted",
            "duplicate_model_download_avoided": True,
            "today_scope_change": "current local model hash, current ComfyUI runtime, generic material prompt, current output hash, and direct visual QA",
        },
        "boundaries": {
            "fast_preview_role_only": True,
            "production_base_lane_certified": False,
            "broad_prompt_or_seed_robustness_claimed": False,
            "personal_calibration_assets_used": False,
            "mask_or_geometry_authority_claimed": False,
            "ec2_started": False,
            "aws_contacted_by_generation": False,
            "jira_mutated": False,
            "wave71_activated": False,
        },
        "result": "pass_bounded_local_flux1_schnell_fast_preview",
    }
    write_json(output_path, payload)
    write_json(mirror_path, payload)
    print(json.dumps({"status": "PASS", "evidence": str(output_path), "artifact_sha256": artifact_sha256, "checks": payload["check_summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
