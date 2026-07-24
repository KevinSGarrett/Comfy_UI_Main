#!/usr/bin/env python3
"""Fail-closed local A6000 executor for a sealed nonpromoting visual review.

The bridge is intentionally a one-shot operation.  It validates immutable
contracts, records a durable deferral when the local A6000 is unavailable, and
loads the two reviewers sequentially only after a fresh direct admission.
It does not submit to Serverless, alter the ComfyUI queue, or promote a result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Callable


ZERO_HASH = "0" * 64
RECEIPT_SCHEMA = "w64.deferred_visual_review_execution_receipt.v1"
DEFERRED_SCHEMA = "w64.deferred_gpu_visual_review_queue.v1"
EXECUTION_SCHEMA = "w64.reference_image_visual_review_execution_contract.v1"
REQUIRED_REVIEWERS = {
    "GLM_4_1V_9B_THINKING": "primary_visual_reviewer",
    "MINICPM_V_4_5_BF16": "independent_family_juror",
}


class BridgeError(RuntimeError):
    """Raised when immutable review work cannot be safely admitted or bound."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BridgeError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise BridgeError(f"JSON artifact root must be an object: {path}")
    return value


def is_safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts and ":" not in path.parts[0]


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise BridgeError(f"receipt output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _seal_value(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["receipt_sha256"] = ZERO_HASH
    sealed["receipt_sha256"] = digest(sealed)
    return sealed


def _matches_seal(path: Path, expected: str) -> bool:
    if not path.is_file():
        return False
    if sha256_file(path) == expected:
        return True
    try:
        payload = read_json(path)
    except BridgeError:
        return False
    return expected in {
        payload.get("final_sha256"),
        payload.get("seal_sha256"),
        payload.get("sha256"),
    }


def model_tree(root: Path, model_id: str) -> dict[str, Any]:
    if not root.is_dir():
        raise BridgeError(f"reviewer model root is missing: {model_id}")
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BridgeError(f"reviewer model contains a symlink: {path}")
        if not path.is_file():
            continue
        files.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if not files:
        raise BridgeError(f"reviewer model has no files: {model_id}")
    return {
        "model_id": model_id,
        "root": str(root),
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
        "tree_sha256": digest(files),
    }


def _reviewer_bindings(
    execution: dict[str, Any],
    binding_contract: dict[str, Any],
    binding_seal: dict[str, Any],
    model_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if binding_seal.get("final_sha256") != execution.get("reviewer_binding_final_sha256"):
        raise BridgeError("reviewer binding seal identity mismatch")
    if binding_seal.get("contract_sha256") != binding_contract.get("contract_sha256"):
        raise BridgeError("reviewer binding contract identity mismatch")
    declared = {
        item.get("model_id"): item
        for item in execution.get("reviewers", [])
        if isinstance(item, dict) and item.get("model_id") in REQUIRED_REVIEWERS
    }
    if set(declared) != set(REQUIRED_REVIEWERS):
        raise BridgeError("execution contract reviewer set is incomplete")
    contract_models = {
        item.get("model_id"): item
        for item in binding_contract.get("models", [])
        if isinstance(item, dict)
    }
    manifest_models = {
        item.get("model_id"): item
        for item in model_manifest.get("models", [])
        if isinstance(item, dict)
    }
    bindings: list[dict[str, Any]] = []
    for model_id, role in REQUIRED_REVIEWERS.items():
        expected_tree = declared[model_id].get("model_tree_sha256")
        bound = contract_models.get(model_id)
        manifest = manifest_models.get(model_id)
        if not isinstance(expected_tree, str) or not isinstance(bound, dict) or not isinstance(manifest, dict):
            raise BridgeError(f"reviewer binding is incomplete: {model_id}")
        if (
            bound.get("tree_sha256") != expected_tree
            or manifest.get("tree_sha256") != expected_tree
            or binding_seal.get("model_tree_hashes", {}).get(model_id) != expected_tree
        ):
            raise BridgeError(f"reviewer tree identity mismatch: {model_id}")
        root = Path(str(bound.get("root", ""))).resolve()
        if root != Path(str(manifest.get("root", ""))).resolve():
            raise BridgeError(f"reviewer root mismatch: {model_id}")
        bindings.append(
            {
                "model_id": model_id,
                "role": role,
                "root": root,
                "tree_sha256": expected_tree,
            }
        )
    return bindings


def validate_contracts(
    deferred_path: Path,
    execution_path: Path,
    binding_contract_path: Path,
    binding_seal_path: Path,
    model_manifest_path: Path,
) -> dict[str, Any]:
    deferred = read_json(deferred_path)
    execution = read_json(execution_path)
    binding_contract = read_json(binding_contract_path)
    binding_seal = read_json(binding_seal_path)
    model_manifest = read_json(model_manifest_path)
    if deferred.get("schema") != DEFERRED_SCHEMA:
        raise BridgeError("deferred queue schema is invalid")
    if execution.get("schema") != EXECUTION_SCHEMA:
        raise BridgeError("visual review execution schema is invalid")
    if Path(str(deferred.get("execution_contract_path", ""))).resolve() != execution_path.resolve():
        raise BridgeError("deferred job execution contract path mismatch")
    if deferred.get("execution_contract_sha256") != sha256_file(execution_path):
        raise BridgeError("deferred job execution contract hash mismatch")
    if deferred.get("state") != "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000":
        raise BridgeError("deferred job is not awaiting local A6000 admission")
    if execution.get("state") != "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000":
        raise BridgeError("execution contract is not awaiting local A6000 admission")
    if execution.get("authority") != "NONPROMOTING_UNQUALIFIED_REVIEW_ONLY":
        raise BridgeError("visual review authority boundary is invalid")
    if execution.get("serverless_eligibility", {}).get("eligible") is not False:
        raise BridgeError("standalone visual review must not be routed to Serverless")
    panel_path = Path(str(execution.get("input_panel_path", ""))).resolve()
    panel = read_json(panel_path)
    if panel.get("contract_sha256") != execution.get("panel_contract_sha256"):
        raise BridgeError("input panel contract hash mismatch")
    panel_seal = panel_path.with_name("semantic_review_panel_seal.json")
    if not _matches_seal(panel_seal, str(execution.get("input_panel_seal_sha256", ""))):
        raise BridgeError("input panel seal mismatch")
    items = panel.get("items")
    if not isinstance(items, list) or not items:
        raise BridgeError("input panel has no review items")
    artifact_root = panel_path.parent.parent.resolve()
    resolved_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not is_safe_relative(item.get("source_root")) or not is_safe_relative(item.get("path")):
            raise BridgeError("input panel contains an unsafe source path")
        path = (artifact_root / item["source_root"] / item["path"]).resolve()
        try:
            path.relative_to(artifact_root)
        except ValueError as exc:
            raise BridgeError("input panel path escapes artifact root") from exc
        if not path.is_file() or path.stat().st_size != item.get("bytes"):
            raise BridgeError(f"input panel artifact is missing or changed: {item.get('path')}")
        if sha256_file(path) != item.get("sha256"):
            raise BridgeError(f"input panel artifact hash mismatch: {item.get('path')}")
        resolved_items.append({**item, "absolute_path": str(path)})
    bindings = _reviewer_bindings(execution, binding_contract, binding_seal, model_manifest)
    return {
        "deferred": deferred,
        "execution": execution,
        "panel": panel,
        "items": resolved_items,
        "reviewer_bindings": bindings,
        "input_panel_path": panel_path,
    }


def local_probe() -> dict[str, Any]:
    pod_id = os.environ.get("RUNPOD_POD_ID")
    try:
        free_output = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip().splitlines()
        free_mib = int(free_output[0].strip())
        process_output = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        gpu_processes = [int(line.split(",", 1)[0].strip()) for line in process_output.splitlines() if line.strip() and line.split(",", 1)[0].strip().isdigit()]
    except (OSError, ValueError, subprocess.SubprocessError):
        free_mib = -1
        gpu_processes = [-1]
    try:
        with urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=3) as response:
            queue = json.loads(response.read().decode("utf-8"))
        queue_idle = not queue.get("queue_running") and not queue.get("queue_pending")
    except (OSError, ValueError, json.JSONDecodeError):
        queue_idle = False
    return {
        "pod_id": pod_id,
        "queue_idle": queue_idle,
        "gpu_processes": gpu_processes,
        "free_mib": free_mib,
    }


def admission(snapshot: dict[str, Any], execution: dict[str, Any], *, allowed_pids: set[int] | None = None, require_free_memory: bool = True) -> list[str]:
    allowed = allowed_pids or set()
    reasons: list[str] = []
    if snapshot.get("pod_id") != execution.get("target_pod_id"):
        reasons.append("POD_IDENTITY_MISMATCH")
    if snapshot.get("queue_idle") is not True:
        reasons.append("COMFYUI_QUEUE_NOT_IDLE")
    observed = snapshot.get("gpu_processes")
    if not isinstance(observed, list) or any(not isinstance(pid, int) for pid in observed):
        reasons.append("GPU_PROCESS_PROBE_INVALID")
    elif set(observed) - allowed:
        reasons.append("FOREIGN_GPU_PROCESS_PRESENT")
    if require_free_memory:
        minimum = execution.get("admission_conditions", {}).get("minimum_free_vram_mib")
        if not isinstance(minimum, int) or not isinstance(snapshot.get("free_mib"), int) or snapshot["free_mib"] < minimum:
            reasons.append("INSUFFICIENT_FREE_VRAM")
    return sorted(set(reasons))


def _review_prompt(item: dict[str, Any]) -> str:
    return (
        "Review this reference image for visual suitability. Return JSON with "
        "decision (PASS, FAIL, or ABSTAIN), confidence from 0 to 1, defects, "
        "and concise rationale. This is nonpromoting review only; do not claim "
        "product, role, or golden-mask authority. "
        f"Image SHA-256: {item['sha256']}; dimensions: {item['width']}x{item['height']}."
    )


def _run_glm(model_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(str(model_root), local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        str(model_root), local_files_only=True, torch_dtype=torch.bfloat16, device_map="cuda:0"
    ).eval()
    output: list[dict[str, Any]] = []
    try:
        for item in items:
            messages = [{"role": "user", "content": [{"type": "image", "url": item["absolute_path"]}, {"type": "text", "text": _review_prompt(item)}]}]
            inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to(model.device)
            generated = model.generate(**inputs, max_new_tokens=512, do_sample=False)
            prompt_length = inputs["input_ids"].shape[-1]
            output.append({"item_sha256": item["sha256"], "raw_response": processor.decode(generated[0][prompt_length:], skip_special_tokens=True)})
    finally:
        del model
        torch.cuda.empty_cache()
    return output


def _run_minicpm(model_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_root), trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(
        str(model_root), trust_remote_code=True, local_files_only=True, torch_dtype=torch.bfloat16
    ).eval().cuda()
    output: list[dict[str, Any]] = []
    try:
        for item in items:
            with Image.open(item["absolute_path"]) as opened:
                image = opened.convert("RGB")
                messages = [{"role": "user", "content": [image, _review_prompt(item)]}]
                response = model.chat(image=None, msgs=messages, tokenizer=tokenizer, sampling=False, max_new_tokens=512, enable_thinking=False)
            output.append({"item_sha256": item["sha256"], "raw_response": str(response)})
    finally:
        del model
        torch.cuda.empty_cache()
    return output


def default_reviewer(model_id: str, model_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if model_id == "GLM_4_1V_9B_THINKING":
        return _run_glm(model_root, items)
    if model_id == "MINICPM_V_4_5_BF16":
        return _run_minicpm(model_root, items)
    raise BridgeError(f"unsupported reviewer: {model_id}")


def run_bridge(
    *,
    deferred_path: Path,
    execution_path: Path,
    binding_contract_path: Path,
    binding_seal_path: Path,
    model_manifest_path: Path,
    output_path: Path,
    execute: bool,
    probe: Callable[[], dict[str, Any]] = local_probe,
    reviewer: Callable[[str, Path, list[dict[str, Any]]], list[dict[str, Any]]] = default_reviewer,
) -> dict[str, Any]:
    validated = validate_contracts(deferred_path, execution_path, binding_contract_path, binding_seal_path, model_manifest_path)
    execution = validated["execution"]
    snapshot = probe()
    reasons = admission(snapshot, execution)
    base = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_sha256": ZERO_HASH,
        "execution_contract_sha256": sha256_file(execution_path),
        "deferred_job_sha256": sha256_file(deferred_path),
        "input_panel_contract_sha256": execution["panel_contract_sha256"],
        "input_item_count": len(validated["items"]),
        "reviewer_tree_hashes": {item["model_id"]: item["tree_sha256"] for item in validated["reviewer_bindings"]},
        "authority": "NONPROMOTING_UNQUALIFIED_REVIEW_ONLY",
        "serverless_submitted": False,
        "gpu_models_loaded": False,
        "admission_snapshot": snapshot,
    }
    if reasons:
        return _persist_receipt(output_path, {**base, "state": "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000", "deferral_reasons": reasons, "reviews": []})
    if not execute:
        return _persist_receipt(output_path, {**base, "state": "READY_FOR_EXCLUSIVE_LOCAL_A6000_REVIEW", "deferral_reasons": [], "reviews": []})
    reviews: list[dict[str, Any]] = []
    for binding in validated["reviewer_bindings"]:
        fresh = probe()
        fresh_reasons = admission(fresh, execution)
        if fresh_reasons:
            return _persist_receipt(output_path, {**base, "state": "DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000", "deferral_reasons": fresh_reasons, "admission_snapshot": fresh, "reviews": reviews})
        observed_tree = model_tree(binding["root"], binding["model_id"])
        if observed_tree["tree_sha256"] != binding["tree_sha256"]:
            raise BridgeError(f"reviewer tree changed before load: {binding['model_id']}")
        responses = reviewer(binding["model_id"], binding["root"], validated["items"])
        if not isinstance(responses, list) or {item.get("item_sha256") for item in responses if isinstance(item, dict)} != {item["sha256"] for item in validated["items"]}:
            raise BridgeError(f"reviewer response coverage is incomplete: {binding['model_id']}")
        reviews.append({"model_id": binding["model_id"], "role": binding["role"], "responses": responses})
    return _persist_receipt(output_path, {**base, "state": "COMPLETED_NONPROMOTING_UNQUALIFIED_REVIEW", "deferral_reasons": [], "gpu_models_loaded": True, "reviews": reviews})


def _persist_receipt(output_path: Path, value: dict[str, Any]) -> dict[str, Any]:
    sealed = _seal_value(value)
    write_json_new(output_path, sealed)
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deferred-job", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    parser.add_argument("--binding-contract", type=Path, required=True)
    parser.add_argument("--binding-seal", type=Path, required=True)
    parser.add_argument("--model-tree-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="load reviewers after fresh direct admission")
    args = parser.parse_args()
    try:
        receipt = run_bridge(
            deferred_path=args.deferred_job.resolve(),
            execution_path=args.execution_contract.resolve(),
            binding_contract_path=args.binding_contract.resolve(),
            binding_seal_path=args.binding_seal.resolve(),
            model_manifest_path=args.model_tree_manifest.resolve(),
            output_path=args.output.resolve(),
            execute=args.execute,
        )
    except BridgeError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"status": receipt["state"], "receipt_sha256": receipt["receipt_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
