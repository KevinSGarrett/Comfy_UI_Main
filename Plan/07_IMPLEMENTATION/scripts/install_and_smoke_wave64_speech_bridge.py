#!/usr/bin/env python3
"""Install the Wave64 speech bridge and execute a no-media ComfyUI API smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


class SmokeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise SmokeError(f"required file is missing: {path}")
    return {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with open(descriptor, "w", encoding="utf-8", newline="\n", closefd=True) as handle:
            handle.write(content)
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def http_json(method: str, url: str, value: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = None if value is None else json.dumps(value).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SmokeError(f"ComfyUI request failed: {method} {url}: {exc}") from exc


def install(root: Path) -> dict[str, Any]:
    source = root / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_speech_bridge/__init__.py"
    destination = root / "ComfyUI/custom_nodes/wave64_speech_bridge/__init__.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file() or sha256_file(destination) != sha256_file(source):
        shutil.copy2(source, destination)
    source_binding = binding(source)
    installed_binding = binding(destination)
    if source_binding["sha256"] != installed_binding["sha256"]:
        raise SmokeError("installed bridge does not match canonical source")
    return {"canonical": source_binding, "installed": installed_binding}


def snapshot_tree(path: Path) -> dict[str, tuple[int, int]]:
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)).replace("\\", "/"): (item.stat().st_size, item.stat().st_mtime_ns)
        for item in sorted(path.rglob("*")) if item.is_file()
    }


def sample_request() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": "w64_row145_146_live_smoke_001",
        "engine": {
            "family": "qwen3_tts_base_icl_diagnostic",
            "revision_sha256": "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c",
            "model_asset_sha256": ["836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258"],
        },
        "line_contract_sha256": "aa4f67bf968bf8af1f9fe5964ef06e16b626aca866bc57871c64323f604abe56",
        "reference_bindings": [{
            "sha256": "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932",
            "rights_valid": True,
            "provenance_valid": True,
        }],
        "seed": 12401,
        "sampling_params": {"temperature": 0.9, "top_k": 50, "top_p": 1.0},
        "preprocessing_transform_ids": ["none"],
        "authority": {
            "voice_authority_valid": False,
            "engine_runtime_valid": True,
            "asset_license_valid": True,
            "exact_assets_resolved": True,
            "production_authorized": False,
        },
        "dry_run": True,
    }


def extract_result(history: dict[str, Any], prompt_id: str) -> dict[str, Any]:
    record = history.get(prompt_id)
    if not isinstance(record, dict):
        raise SmokeError("history does not contain the submitted prompt")
    status = record.get("status", {})
    if status.get("status_str") != "success" or status.get("completed") is not True:
        raise SmokeError(f"ComfyUI prompt did not complete successfully: {status}")
    outputs = record.get("outputs", {})
    node = outputs.get("1", {})
    text = node.get("text")
    if not isinstance(text, list) or not text or not isinstance(text[0], str):
        raise SmokeError(f"bridge output text is missing: {node}")
    if any(key in node for key in ("images", "audio", "gifs")):
        raise SmokeError("bridge smoke unexpectedly emitted media")
    value = json.loads(text[0])
    if not isinstance(value, dict):
        raise SmokeError("bridge result root is not an object")
    return value


def smoke(root: Path, api_url: str, output: Path) -> dict[str, Any]:
    base = api_url.rstrip("/")
    queue = http_json("GET", f"{base}/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise SmokeError("ComfyUI queue is not idle")
    object_info = http_json("GET", f"{base}/object_info", timeout=60)
    if "Wave64SpeechBridge" not in object_info:
        raise SmokeError("Wave64SpeechBridge is not visible; restart ComfyUI after installation")
    candidate_root = root / "runtime_artifacts/audio_speech_candidates"
    promoted_root = root / "runtime_artifacts/audio_speech_promoted"
    before = {"candidates": snapshot_tree(candidate_root), "promoted": snapshot_tree(promoted_root)}
    request_value = sample_request()
    graph = {
        "prompt": {
            "1": {
                "class_type": "Wave64SpeechBridge",
                "inputs": {"request_json": json.dumps(request_value, sort_keys=True), "dry_run": True},
            }
        },
        "client_id": f"wave64-speech-smoke-{uuid.uuid4().hex}",
    }
    submitted = http_json("POST", f"{base}/prompt", graph)
    prompt_id = submitted.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise SmokeError(f"ComfyUI did not return prompt_id: {submitted}")
    deadline = time.monotonic() + 60
    history = {}
    while time.monotonic() < deadline:
        history = http_json("GET", f"{base}/history/{prompt_id}")
        if prompt_id in history:
            break
        time.sleep(0.25)
    result = extract_result(history, prompt_id)
    after = {"candidates": snapshot_tree(candidate_root), "promoted": snapshot_tree(promoted_root)}
    if before != after:
        raise SmokeError("candidate or promoted media tree changed during dry-run smoke")
    expected_blockers = {"BLOCKED_VOICE_AUTHORITY_MISSING", "BLOCKED_PRODUCTION_CERTIFICATION_INCOMPLETE"}
    if result.get("classification") != "W64_SPEECH_BRIDGE_DRY_RUN_VALIDATED_AUTHORITY_BLOCKED":
        raise SmokeError(f"unexpected bridge classification: {result.get('classification')}")
    if not expected_blockers.issubset(set(result.get("blockers", []))):
        raise SmokeError(f"expected authority blockers are missing: {result.get('blockers')}")
    evidence = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_bridge_live_headless_smoke",
        "classification": "W64_ROWS145_146_LIVE_COMFYUI_BRIDGE_SMOKE_PASS_PRODUCTION_BLOCKED",
        "api_url": base,
        "prompt_id": prompt_id,
        "node_object_info": object_info["Wave64SpeechBridge"],
        "request": request_value,
        "result": result,
        "media_tree_unchanged": True,
        "queue_idle_before": True,
        "boundaries": {
            "media_generated": False,
            "candidate_media_written": False,
            "promotion_attempted": False,
            "production_authority_claimed": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
            "content_based_suppression": False,
        },
    }
    write_json_atomic(output, evidence)
    return {"evidence": binding(output), "prompt_id": prompt_id, "result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--install-only", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        installed = None if args.smoke_only else install(root)
        smoked = None
        if not args.install_only:
            if args.output is None:
                raise SmokeError("--output is required for smoke execution")
            output = args.output.resolve() if args.output.is_absolute() else (root / args.output).resolve()
            smoked = smoke(root, args.api_url, output)
        result = {"classification": "W64_SPEECH_BRIDGE_INSTALL_SMOKE_PASS", "installed": installed, "smoke": smoked}
    except Exception as exc:
        print(json.dumps({"classification": "W64_SPEECH_BRIDGE_INSTALL_SMOKE_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
