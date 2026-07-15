#!/usr/bin/env python3
"""Run one baseline-anchored img2img correction for Wave64 fluid-state continuity."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import run_wave64_fluid_state_continuity_pair as pair


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
DEFAULT_PROFILE = PROJECT_ROOT / "PromptProfiles/regional_detail/fluid_state_continuity_sdxl_tears/profile.img2img_state_v2.json"
DEFAULT_WORKFLOW = PROJECT_ROOT / "Workflows/regional_detail/fluid_state_continuity_sdxl_tears/workflow.img2img_state_v2.api.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_artifacts/wave64_fluid_state_img2img_refinement"
TZ = ZoneInfo("America/Chicago")


def validate_workflow(workflow: dict[str, Any], profile: dict[str, Any]) -> None:
    prompt = pair.strip_metadata(workflow)
    required = {
        "1": "CheckpointLoaderSimple",
        "2": "LoraLoader",
        "3": "CLIPTextEncode",
        "4": "CLIPTextEncode",
        "5": "LoadImage",
        "6": "VAEEncode",
        "7": "KSampler",
        "8": "VAEDecode",
        "9": "SaveImage",
    }
    for node_id, class_type in required.items():
        if prompt.get(node_id, {}).get("class_type") != class_type:
            raise ValueError(f"node {node_id} class drift")
    contract = profile["revision_contract"]
    sampler = prompt["7"]["inputs"]
    for key in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"):
        profile_key = {"sampler_name": "sampler"}.get(key, key)
        if sampler.get(key) != contract[profile_key]:
            raise ValueError(f"img2img {key} drift")
    if prompt["2"]["inputs"].get("strength_model") != 0.3:
        raise ValueError("state adapter model strength drift")
    if prompt["2"]["inputs"].get("strength_clip") != 0.2:
        raise ValueError("state adapter clip strength drift")


def multipart_image_body(path: Path, upload_name: str, boundary: str) -> bytes:
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )

    add_field("type", "input")
    add_field("overwrite", "true")
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="image"; filename="{upload_name}"\r\n'
                "Content-Type: image/png\r\n\r\n"
            ).encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts)


def upload_image(api_url: str, path: Path, upload_name: str) -> dict[str, Any]:
    boundary = f"wave64-{uuid.uuid4().hex}"
    body = multipart_image_body(path, upload_name, boundary)
    request = urllib.request.Request(
        f"{api_url}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not payload.get("name"):
        raise ValueError("ComfyUI upload returned no input name")
    return payload


def execute_candidate(
    api_url: str,
    workflow: dict[str, Any],
    candidate_dir: Path,
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    if not pair.queue_is_idle(pair.http_json("GET", f"{api_url}/queue", timeout=10)):
        raise ValueError("ComfyUI queue is not idle before img2img candidate")
    request_payload = {
        "prompt": pair.strip_metadata(workflow),
        "client_id": f"wave64-fluid-state-img2img-{uuid.uuid4()}",
        "extra_data": {
            "tracker_id": "TRK-W64-056",
            "system_id": "fluid_body_state_continuity",
            "route_revision": "img2img_state_v2",
            "authorized_candidate_count": 1,
            "retry_allowed": False,
            "content_based_suppression": False,
        },
    }
    pair.write_json(candidate_dir / "prompt_request.json", request_payload)
    response = pair.http_json("POST", f"{api_url}/prompt", request_payload, timeout=30)
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise ValueError("ComfyUI returned no prompt_id")
    pair.write_json(candidate_dir / "prompt_response.json", response)
    history: dict[str, Any] | None = None
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        candidate = pair.http_json("GET", f"{api_url}/history/{prompt_id}", timeout=30)
        if isinstance(candidate, dict) and pair.image_records(candidate, prompt_id):
            history = candidate
            break
        time.sleep(poll_seconds)
    if history is None:
        raise TimeoutError("no img2img output before timeout")
    pair.write_json(candidate_dir / "history.json", history)
    records = pair.image_records(history, prompt_id)
    if len(records) != 1:
        raise ValueError(f"expected exactly one img2img output, got {len(records)}")
    record = records[0]
    query = urllib.parse.urlencode(
        {"filename": record["filename"], "subfolder": record["subfolder"], "type": record["type"]}
    )
    image_path = candidate_dir / "img2img_tears_state_v2.png"
    image_path.write_bytes(pair.http_bytes(f"{api_url}/view?{query}"))
    technical = pair.image_technical_qa(image_path)
    if not technical["nonblank_variance_pass"]:
        raise ValueError("img2img output is blank or flat")
    return {
        "prompt_id": prompt_id,
        "history_output": record,
        "image": {
            "path": str(image_path),
            "bytes": image_path.stat().st_size,
            "sha256": pair.sha256_file(image_path),
            "technical_qa": technical,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=3)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    profile_path = Path(args.profile).resolve()
    workflow_path = Path(args.workflow).resolve()
    profile = pair.read_json(profile_path)
    workflow = pair.read_json(workflow_path)
    validate_workflow(workflow, profile)
    boundaries = profile["boundaries"]
    if boundaries.get("new_route_revision_not_pair_retry") is not True:
        raise ValueError("route-revision boundary drift")
    if boundaries.get("content_based_suppression") is not False:
        raise ValueError("content-based suppression boundary drift")
    contract = profile["revision_contract"]
    if contract.get("authorized_candidate_count") != 1 or contract.get("retry_allowed") is not False:
        raise ValueError("single-candidate no-retry contract drift")

    baseline = Path(profile["source_pair"]["baseline_path"])
    if not baseline.is_file():
        raise ValueError(f"immutable baseline missing: {baseline}")
    if baseline.stat().st_size != profile["source_pair"]["baseline_bytes"]:
        raise ValueError("immutable baseline byte-size drift")
    if pair.sha256_file(baseline) != profile["source_pair"]["baseline_sha256"]:
        raise ValueError("immutable baseline hash drift")
    for label in ("checkpoint", "state_adapter"):
        binding = profile[label]
        path = Path(binding["runtime_path"])
        if not path.is_file() or path.stat().st_size != binding["bytes"]:
            raise ValueError(f"{label} file/size drift")
        if pair.sha256_file(path) != binding["sha256"]:
            raise ValueError(f"{label} hash drift")

    object_info = pair.http_json("GET", f"{api_url}/object_info", timeout=30)
    checkpoints = {
        pair.normalized_model_name(value)
        for value in pair.input_choices(object_info, "CheckpointLoaderSimple", "ckpt_name")
    }
    loras = {
        pair.normalized_model_name(value)
        for value in pair.input_choices(object_info, "LoraLoader", "lora_name")
    }
    if pair.normalized_model_name(profile["checkpoint"]["name"]) not in checkpoints:
        raise ValueError("checkpoint not visible")
    if pair.normalized_model_name(profile["state_adapter"]["name"]) not in loras:
        raise ValueError("state adapter not visible")
    if not pair.queue_is_idle(pair.http_json("GET", f"{api_url}/queue", timeout=10)):
        raise ValueError("ComfyUI queue is not idle before revision execution")

    now = datetime.now(TZ)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    run_dir = Path(args.output_root).resolve() / stamp
    candidate_dir = run_dir / "img2img_tears_state_v2"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    upload_name = f"wave64_fluid_state_baseline_{profile['source_pair']['baseline_sha256'][:12]}.png"
    upload = upload_image(api_url, baseline, upload_name)
    uploaded_name = str(upload["name"])
    if upload.get("subfolder"):
        uploaded_name = f"{upload['subfolder']}/{uploaded_name}"
    workflow["5"]["inputs"]["image"] = uploaded_name
    workflow["9"]["inputs"]["filename_prefix"] = f"wave64_fluid_state_continuity/{stamp}_img2img_state_v2"
    pair.write_json(candidate_dir / "workflow.bound.api.json", workflow)
    result = execute_candidate(api_url, workflow, candidate_dir, args.timeout_seconds, args.poll_seconds)
    comparison = pair.compare_images(baseline, Path(result["image"]["path"]))
    manifest = {
        "schema_version": "1.0",
        "run_id": stamp,
        "created_iso": now.replace(microsecond=0).isoformat(),
        "tracker_id": "TRK-W64-056",
        "item_id": "ITEM-W64-056",
        "system_id": "fluid_body_state_continuity",
        "status": "PASS_IMG2IMG_TECHNICAL_PENDING_DIRECT_VISUAL_REVIEW",
        "profile": {"path": str(profile_path), "sha256": pair.sha256_file(profile_path), "bytes": profile_path.stat().st_size},
        "workflow": {"path": str(workflow_path), "sha256": pair.sha256_file(workflow_path), "bytes": workflow_path.stat().st_size},
        "source_baseline": profile["source_pair"],
        "upload_response": upload,
        "revision_contract": contract,
        "candidate": result,
        "technical_comparison": comparison,
        "runtime": {
            "api_url": api_url,
            "object_info_visibility_pass": True,
            "authorized_candidate_count": 1,
            "actual_candidate_count": 1,
            "retry_count": 0,
        },
        "gates": {
            "baseline_hash_binding_pass": True,
            "model_hash_binding_pass": True,
            "object_info_visibility_pass": True,
            "candidate_technical_pass": True,
            "distinct_media_pass": comparison["distinct_media_hashes"],
            "planned_generated_state_match": None,
            "shot_continuity_pass": None,
            "direct_visual_review_pass": None,
            "bounded_direct_runtime_proof_pass": False,
            "production_certification_pass": False,
            "row_complete": False,
        },
        "boundaries": {
            "local_comfyui_only": True,
            "new_route_revision_not_pair_retry": True,
            "source_pair_preserved": True,
            "ec2_started": False,
            "aws_contacted": False,
            "mask_truth_consumed": False,
            "content_based_suppression": False,
            "adult_or_nsfw_asset_visibility_restricted": False,
            "candidate_retry_count": 0,
            "wave70_hard_gates_rerun": False,
            "wave71_activated": False,
            "jira_mutated": False,
        },
    }
    manifest_path = run_dir / "runtime_manifest.json"
    pair.write_json(manifest_path, manifest)
    print(json.dumps({"status": manifest["status"], "run_dir": str(run_dir), "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
