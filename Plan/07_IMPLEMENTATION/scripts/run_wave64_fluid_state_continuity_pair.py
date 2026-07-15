#!/usr/bin/env python3
"""Run one predeclared same-seed fluid-state baseline/state pair on local ComfyUI."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageStat


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
DEFAULT_PROFILE = PROJECT_ROOT / "PromptProfiles/regional_detail/fluid_state_continuity_sdxl_tears/profile.json"
DEFAULT_BASELINE = PROJECT_ROOT / "Workflows/regional_detail/fluid_state_continuity_sdxl_tears/workflow.baseline.api.json"
DEFAULT_STATE = PROJECT_ROOT / "Workflows/regional_detail/fluid_state_continuity_sdxl_tears/workflow.state.api.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_artifacts/wave64_fluid_state_continuity"
TZ = ZoneInfo("America/Chicago")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def http_json(method: str, url: str, payload: Any | None = None, timeout: int = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_bytes(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def strip_metadata(workflow: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in workflow.items() if not str(key).startswith("_")}


def normalized_model_name(value: str) -> str:
    return value.replace("/", "\\").lower()


def input_choices(object_info: dict[str, Any], node: str, input_name: str) -> list[str]:
    try:
        values = object_info[node]["input"]["required"][input_name][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"object_info missing {node}.{input_name}") from exc
    if not isinstance(values, list):
        raise ValueError(f"object_info choices are not a list: {node}.{input_name}")
    return [str(value) for value in values]


def queue_is_idle(queue: dict[str, Any]) -> bool:
    return not queue.get("queue_running") and not queue.get("queue_pending")


def validate_workflow(workflow: dict[str, Any], role: str, profile: dict[str, Any]) -> None:
    prompt = strip_metadata(workflow)
    required_nodes = {
        "1": "CheckpointLoaderSimple",
        "2": "LoraLoader",
        "3": "CLIPTextEncode",
        "4": "CLIPTextEncode",
        "5": "EmptyLatentImage",
        "6": "KSampler",
        "7": "VAEDecode",
        "8": "SaveImage",
    }
    for node_id, class_type in required_nodes.items():
        if prompt.get(node_id, {}).get("class_type") != class_type:
            raise ValueError(f"{role} node {node_id} class drift")
    contract = profile["pair_contract"]
    if prompt["6"]["inputs"].get("seed") != contract["same_seed"]:
        raise ValueError(f"{role} seed drift")
    for key in ("width", "height"):
        if prompt["5"]["inputs"].get(key) != contract[key]:
            raise ValueError(f"{role} {key} drift")
    if prompt["6"]["inputs"].get("steps") != contract["steps"]:
        raise ValueError(f"{role} step drift")
    if role == "baseline_dry_state":
        if prompt["2"]["inputs"].get("strength_model") != 0.0:
            raise ValueError("baseline model strength must be zero")
        if prompt["2"]["inputs"].get("strength_clip") != 0.0:
            raise ValueError("baseline clip strength must be zero")
    elif role == "generated_tears_state":
        if prompt["2"]["inputs"].get("strength_model") != 0.25:
            raise ValueError("state model strength drift")
        if prompt["2"]["inputs"].get("strength_clip") != 0.18:
            raise ValueError("state clip strength drift")
    else:
        raise ValueError(f"unknown pair role: {role}")


def image_records(history: dict[str, Any], prompt_id: str) -> list[dict[str, str]]:
    outputs = history.get(prompt_id, {}).get("outputs", {})
    records: list[dict[str, str]] = []
    if not isinstance(outputs, dict):
        return records
    for node_id, output in outputs.items():
        if not isinstance(output, dict):
            continue
        for image in output.get("images", []) or []:
            if isinstance(image, dict):
                records.append(
                    {
                        "node_id": str(node_id),
                        "filename": str(image.get("filename") or ""),
                        "subfolder": str(image.get("subfolder") or ""),
                        "type": str(image.get("type") or "output"),
                    }
                )
    return records


def image_technical_qa(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        extrema = rgb.getextrema()
        stats = ImageStat.Stat(rgb)
        return {
            "png_opened": True,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "channel_means": [round(value, 6) for value in stats.mean],
            "channel_stddev": [round(value, 6) for value in stats.stddev],
            "nonblank_variance_pass": any(high > low for low, high in extrema),
        }


def compare_images(baseline: Path, state: Path) -> dict[str, Any]:
    with Image.open(baseline) as baseline_image, Image.open(state) as state_image:
        baseline_rgb = baseline_image.convert("RGB")
        state_rgb = state_image.convert("RGB")
        if baseline_rgb.size != state_rgb.size:
            raise ValueError("pair dimension mismatch")
        difference = ImageChops.difference(baseline_rgb, state_rgb)
        gray = difference.convert("L")
        histogram = gray.histogram()
        pixel_count = baseline_rgb.width * baseline_rgb.height
        changed = pixel_count - histogram[0]
        mean_abs = ImageStat.Stat(gray).mean[0]
        return {
            "same_dimensions": True,
            "width": baseline_rgb.width,
            "height": baseline_rgb.height,
            "changed_pixel_ratio": round(changed / pixel_count, 8),
            "normalized_mean_absolute_difference": round(mean_abs / 255.0, 8),
            "distinct_media_hashes": sha256_file(baseline) != sha256_file(state),
            "identity_continuity_pass": None,
            "planned_state_match_pass": None,
            "visual_review_status": "pending_direct_codex_review",
        }


def execute_role(
    api_url: str,
    role: str,
    workflow: dict[str, Any],
    role_dir: Path,
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    if not queue_is_idle(http_json("GET", f"{api_url}/queue", timeout=10)):
        raise ValueError(f"ComfyUI queue is not idle before {role}")
    prompt = strip_metadata(workflow)
    request_payload = {
        "prompt": prompt,
        "client_id": f"wave64-fluid-state-{role}-{uuid.uuid4()}",
        "extra_data": {
            "tracker_id": "TRK-W64-056",
            "system_id": "fluid_body_state_continuity",
            "pair_role": role,
            "authorized_generation_count": 2,
            "retry_allowed": False,
            "content_based_suppression": False,
        },
    }
    write_json(role_dir / "prompt_request.json", request_payload)
    response = http_json("POST", f"{api_url}/prompt", request_payload, timeout=30)
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise ValueError(f"ComfyUI returned no prompt_id for {role}")
    write_json(role_dir / "prompt_response.json", response)
    deadline = time.monotonic() + timeout_seconds
    history: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        candidate = http_json("GET", f"{api_url}/history/{prompt_id}", timeout=30)
        if isinstance(candidate, dict) and image_records(candidate, prompt_id):
            history = candidate
            break
        time.sleep(poll_seconds)
    if history is None:
        raise TimeoutError(f"no image output for {role} within {timeout_seconds} seconds")
    write_json(role_dir / "history.json", history)
    records = image_records(history, prompt_id)
    if len(records) != 1:
        raise ValueError(f"{role} expected exactly one output image, got {len(records)}")
    record = records[0]
    query = urllib.parse.urlencode(
        {
            "filename": record["filename"],
            "subfolder": record["subfolder"],
            "type": record["type"],
        }
    )
    image_bytes = http_bytes(f"{api_url}/view?{query}")
    image_path = role_dir / f"{role}.png"
    image_path.write_bytes(image_bytes)
    technical = image_technical_qa(image_path)
    if not technical["nonblank_variance_pass"]:
        raise ValueError(f"{role} output is blank or flat")
    return {
        "role": role,
        "prompt_id": prompt_id,
        "history_output": record,
        "image": {
            "path": str(image_path),
            "bytes": image_path.stat().st_size,
            "sha256": sha256_file(image_path),
            "technical_qa": technical,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--baseline-workflow", default=str(DEFAULT_BASELINE))
    parser.add_argument("--state-workflow", default=str(DEFAULT_STATE))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=3)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    profile_path = Path(args.profile).resolve()
    workflow_paths = {
        "baseline_dry_state": Path(args.baseline_workflow).resolve(),
        "generated_tears_state": Path(args.state_workflow).resolve(),
    }
    profile = read_json(profile_path)
    if profile.get("boundaries", {}).get("content_based_suppression") is not False:
        raise ValueError("content-based suppression boundary drift")
    if profile.get("pair_contract", {}).get("authorized_generation_count") != 2:
        raise ValueError("pair generation-count contract drift")
    if profile.get("pair_contract", {}).get("retry_allowed") is not False:
        raise ValueError("pair retry boundary drift")
    workflows = {role: read_json(path) for role, path in workflow_paths.items()}
    for role, workflow in workflows.items():
        validate_workflow(workflow, role, profile)

    checkpoint = profile["checkpoint"]
    adapter = profile["state_adapter"]
    checkpoint_path = Path(checkpoint["runtime_path"])
    adapter_path = Path(adapter["runtime_path"])
    for label, path, binding in (
        ("checkpoint", checkpoint_path, checkpoint),
        ("state adapter", adapter_path, adapter),
    ):
        if not path.is_file():
            raise ValueError(f"{label} missing: {path}")
        if path.stat().st_size != binding["bytes"] or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"{label} byte/hash drift")

    system_stats = http_json("GET", f"{api_url}/system_stats", timeout=10)
    object_info = http_json("GET", f"{api_url}/object_info", timeout=30)
    checkpoints = {normalized_model_name(value) for value in input_choices(object_info, "CheckpointLoaderSimple", "ckpt_name")}
    loras = {normalized_model_name(value) for value in input_choices(object_info, "LoraLoader", "lora_name")}
    if normalized_model_name(checkpoint["name"]) not in checkpoints:
        raise ValueError("checkpoint is not visible in current object_info")
    if normalized_model_name(adapter["name"]) not in loras:
        raise ValueError("state adapter is not visible in current object_info")
    if not queue_is_idle(http_json("GET", f"{api_url}/queue", timeout=10)):
        raise ValueError("ComfyUI queue is not idle before pair execution")

    now = datetime.now(TZ)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    run_dir = Path(args.output_root).resolve() / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, Any]] = []
    for role in profile["pair_contract"]["roles"]:
        role_dir = run_dir / role
        role_dir.mkdir(parents=True, exist_ok=False)
        results.append(
            execute_role(
                api_url,
                role,
                workflows[role],
                role_dir,
                args.timeout_seconds,
                args.poll_seconds,
            )
        )
    if len(results) != 2:
        raise ValueError("exactly two predeclared generations are required")
    baseline_image = Path(results[0]["image"]["path"])
    state_image = Path(results[1]["image"]["path"])
    comparison = compare_images(baseline_image, state_image)
    if not comparison["distinct_media_hashes"]:
        raise ValueError("baseline and state images are byte-identical")

    manifest = {
        "schema_version": "1.0",
        "run_id": stamp,
        "created_iso": now.replace(microsecond=0).isoformat(),
        "tracker_id": "TRK-W64-056",
        "item_id": "ITEM-W64-056",
        "system_id": "fluid_body_state_continuity",
        "status": "PASS_TECHNICAL_PAIR_PENDING_DIRECT_VISUAL_REVIEW",
        "profile": {
            "path": str(profile_path),
            "bytes": profile_path.stat().st_size,
            "sha256": sha256_file(profile_path),
        },
        "workflows": {
            role: {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for role, path in workflow_paths.items()
        },
        "models": {
            "checkpoint": checkpoint,
            "state_adapter": adapter,
        },
        "runtime": {
            "api_url": api_url,
            "system_stats": system_stats,
            "object_info_visibility_pass": True,
            "queue_idle_before_execution": True,
            "authorized_generation_count": 2,
            "actual_generation_count": len(results),
            "retry_count": 0,
        },
        "pair_contract": profile["pair_contract"],
        "outputs": results,
        "technical_comparison": comparison,
        "gates": {
            "model_hash_binding_pass": True,
            "object_info_visibility_pass": True,
            "baseline_technical_pass": True,
            "state_technical_pass": True,
            "distinct_media_pass": True,
            "planned_generated_state_match": None,
            "shot_continuity_pass": None,
            "direct_visual_review_pass": None,
            "bounded_direct_runtime_proof_pass": False,
            "production_certification_pass": False,
            "row_complete": False,
        },
        "boundaries": {
            "local_comfyui_only": True,
            "ec2_started": False,
            "aws_contacted": False,
            "mask_truth_consumed": False,
            "content_based_suppression": False,
            "adult_or_nsfw_asset_visibility_restricted": False,
            "candidate_regenerated_or_retried": False,
            "wave70_hard_gates_rerun": False,
            "wave71_activated": False,
            "jira_mutated": False,
        },
    }
    manifest_path = run_dir / "runtime_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"status": manifest["status"], "run_dir": str(run_dir), "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
