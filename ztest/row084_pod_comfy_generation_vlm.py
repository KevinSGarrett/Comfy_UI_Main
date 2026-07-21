#!/usr/bin/env python3
"""Row084 Class E: real Comfy generation + Ollama VLM on RunPod. Does NOT clear 011."""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
OLLAMA = "http://127.0.0.1:11434"
CKPT = "realvisxlV50_v50Bakedvae.safetensors"
VLM_MODEL = "qwen2.5vl:7b"
PREFIX = "row084_class_e_gen"
OUT_ROOT = Path("/workspace/tmp")
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT_DIR = OUT_ROOT / f"row084_class_e_comfy_gen_{STAMP}"
CLIENT_ID = f"row084-class-e-{uuid.uuid4().hex[:12]}"


def now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 60.0) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def build_workflow() -> dict:
    # Bounded SDXL T2I — real generation receipt only; not production timeline authority.
    return {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CKPT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 768, "height": 1024, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": (
                    "photorealistic adult woman standing in a plain studio, "
                    "black one-piece swimsuit, soft even lighting, full body, "
                    "neutral expression, sharp focus"
                ),
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": (
                    "minor, child, cartoon, anime, blurry, lowres, watermark, text, "
                    "deformed, extra limbs, nsfw explicit"
                ),
            },
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 84011021,
                "steps": 18,
                "cfg": 5.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": PREFIX,
                "images": ["8", 0],
            },
        },
    }


def wait_history(prompt_id: str, timeout_s: float = 600.0) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        hist = http_json("GET", f"{COMFY}/history/{prompt_id}", timeout=30.0)
        if prompt_id in hist:
            return hist[prompt_id]
        q = http_json("GET", f"{COMFY}/queue", timeout=15.0)
        running = any(prompt_id in str(x) for x in q.get("queue_running", []))
        pending = any(prompt_id in str(x) for x in q.get("queue_pending", []))
        if not running and not pending:
            # may have finished between polls
            hist = http_json("GET", f"{COMFY}/history/{prompt_id}", timeout=30.0)
            if prompt_id in hist:
                return hist[prompt_id]
        time.sleep(2.0)
    raise TimeoutError(f"prompt_id {prompt_id} not complete after {timeout_s}s")


def view_image(filename: str, subfolder: str, folder_type: str) -> bytes:
    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": folder_type}
    )
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as resp:
        return resp.read()


def ollama_chat(image_b64: str) -> dict:
    prompt = (
        "Review this Wave64 Row084 Class E frame from a LIVE RunPod ComfyUI generation "
        f"(checkpoint {CKPT}). Return compact JSON only with keys: frame_ok (bool), "
        "subject, setting, decode_or_artifact_issues (string or null), "
        "generation_receipt_corroborated (bool), production_completion_allowed "
        "(must be false), row_complete (must be false). Do not claim COMPLETE."
    )
    body = {
        "model": VLM_MODEL,
        "stream": False,
        "keep_alive": "5m",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
    }
    return http_json("POST", f"{OLLAMA}/api/chat", body, timeout=360.0)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT_DIR / "visual_frames"
    frames_dir.mkdir(exist_ok=True)

    comfy_probe = {
        "created_at": now_z(),
        "COMFY_URL": COMFY,
        "COMFYUI_ROOT": "/workspace/ComfyUI",
    }
    try:
        stats = http_json("GET", f"{COMFY}/system_stats", timeout=15.0)
        queue = http_json("GET", f"{COMFY}/queue", timeout=15.0)
        comfy_probe["comfyui_serving"] = True
        comfy_probe["comfyui_version"] = stats["system"]["comfyui_version"]
        d0 = stats["devices"][0]
        comfy_probe["gpu_name"] = d0["name"]
        comfy_probe["vram_free"] = d0["vram_free"]
        comfy_probe["vram_total"] = d0["vram_total"]
        comfy_probe["queue_running"] = len(queue.get("queue_running", []))
        comfy_probe["queue_pending"] = len(queue.get("queue_pending", []))
    except Exception as e:
        comfy_probe["comfyui_serving"] = False
        comfy_probe["error"] = str(e)
        (OUT_DIR / "comfy_probe.json").write_text(json.dumps(comfy_probe, indent=2) + "\n")
        raise SystemExit(f"Comfy not serving: {e}")

    (OUT_DIR / "comfy_probe.json").write_text(json.dumps(comfy_probe, indent=2) + "\n")

    if comfy_probe["queue_running"] or comfy_probe["queue_pending"]:
        raise SystemExit("REFUSING: Comfy queue busy; will not interrupt foreign job")

    workflow = build_workflow()
    (OUT_DIR / "workflow.api.json").write_text(json.dumps(workflow, indent=2) + "\n")

    submit_t0 = time.time()
    submit = http_json(
        "POST",
        f"{COMFY}/prompt",
        {"prompt": workflow, "client_id": CLIENT_ID},
        timeout=60.0,
    )
    prompt_id = submit["prompt_id"]
    (OUT_DIR / "submit_response.json").write_text(json.dumps(submit, indent=2) + "\n")

    hist = wait_history(prompt_id, timeout_s=900.0)
    elapsed = round(time.time() - submit_t0, 2)
    (OUT_DIR / "history_entry.json").write_text(json.dumps(hist, indent=2) + "\n")

    status = hist.get("status") or {}
    outputs = hist.get("outputs") or {}
    images_meta = []
    for node_id, node_out in outputs.items():
        for img in node_out.get("images") or []:
            images_meta.append({"node_id": node_id, **img})

    local_frames = []
    for i, meta in enumerate(images_meta[:3], start=1):
        blob = view_image(meta["filename"], meta.get("subfolder", ""), meta.get("type", "output"))
        dest = frames_dir / f"frame_{i:02d}.png"
        dest.write_bytes(blob)
        # also copy into Comfy output path inventory note
        local_frames.append(
            {
                "path": str(dest),
                "name": dest.name,
                "sha256": sha256_bytes(blob),
                "bytes": len(blob),
                "comfy_filename": meta.get("filename"),
                "comfy_subfolder": meta.get("subfolder", ""),
                "comfy_type": meta.get("type", "output"),
                "node_id": meta.get("node_id"),
            }
        )

    # Prefer copying any on-disk SaveImage paths if present under Comfy output
    comfy_out = Path("/workspace/ComfyUI/output")
    on_disk = sorted(comfy_out.glob(f"{PREFIX}*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    on_disk_meta = []
    for p in on_disk:
        on_disk_meta.append(
            {
                "path": str(p),
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
        )

    reviews = []
    for fr in local_frames:
        entry = {
            "frame": fr["path"],
            "name": fr["name"],
            "sha256": fr["sha256"],
            "bytes": fr["bytes"],
        }
        t0 = time.time()
        try:
            resp = ollama_chat(base64.b64encode(Path(fr["path"]).read_bytes()).decode("ascii"))
            content = (resp.get("message") or {}).get("content") or ""
            entry["ok"] = True
            entry["seconds"] = round(time.time() - t0, 2)
            entry["raw_response"] = content[:6000]
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(content[start : end + 1])
                    if isinstance(parsed, dict):
                        parsed["production_completion_allowed"] = False
                        parsed["row_complete"] = False
                        entry["parsed"] = parsed
                except json.JSONDecodeError:
                    entry["parse_error"] = "json_decode_failed"
        except Exception as e:
            entry["ok"] = False
            entry["error"] = str(e)
            entry["seconds"] = round(time.time() - t0, 2)
        reviews.append(entry)

    history_sha = sha256_bytes(
        json.dumps(hist, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    workflow_sha = sha256_file(OUT_DIR / "workflow.api.json")

    receipt = {
        "schema_version": "1.0",
        "evidence_id": "TRK-W64-084_ROW084_CLASS_E_RUNPOD_COMFY_GENERATION_RECEIPT",
        "record_type": "row084_class_e_comfy_generation_receipt",
        "tracker_id": "TRK-W64-084",
        "item_id": "ITEM-W64-084",
        "check_id": "ROW084-011",
        "blocker_class": "E",
        "blocker_id": "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "decision": "HOLD",
        "cleared": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "implementation_completion_claimed": False,
        "do_not_clear": ["ROW084-011"],
        "do_not_thrash": ["ROW084-012"],
        "row074_left_alone": True,
        "created_at": now_z(),
        "pod": {
            "id": "1q4ji0gg1fkhvt",
            "name": "hyperreal-flux",
            "public_ip": "195.26.233.100",
            "ssh_port": 52077,
            "paths_env": "/workspace/paths.env",
        },
        "comfy_probe": comfy_probe,
        "generation": {
            "client_id": CLIENT_ID,
            "prompt_id": prompt_id,
            "checkpoint": CKPT,
            "workflow_api_path": str(OUT_DIR / "workflow.api.json"),
            "workflow_sha256": workflow_sha,
            "submit_http_ok": True,
            "number": submit.get("number"),
            "node_errors": submit.get("node_errors"),
            "elapsed_seconds": elapsed,
            "status_str": status.get("status_str"),
            "completed": status.get("completed"),
            "history_or_job_snapshot_sha256": history_sha,
            "outputs_image_count": len(images_meta),
            "on_disk_output_sample": on_disk_meta,
            "visual_frames": local_frames,
        },
        "vlm": {
            "model": VLM_MODEL,
            "ok_frame_count": sum(1 for r in reviews if r.get("ok")),
            "reviews": reviews,
            "status": "VLM_REVIEW_BOUNDED_HOLD",
        },
        "proof_tier": "RUNTIME_COMFY_GENERATION_RECEIPT_WITH_VLM_REVIEW",
        "highest_proof_tier_achieved": "RUNTIME_COMFY_GENERATION_RECEIPT_WITH_VLM_REVIEW",
        "remaining_blockers": [
            "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
            "ROW084-011_CLASS_E_INTENTIONALLY_OPEN",
            "ROW084-012_CLASS_C_OPEN_HOLD_UNCHANGED",
            "SINGLE_IMAGE_GEN_IS_NOT_PRODUCTION_MUX_CUT_CAMERA_AUTHORITY",
        ],
        "safe_next_action": (
            "Keep ROW084-011 FAIL/OPEN. Keep ROW084-012 OPEN_HOLD. Do not claim COMPLETE. "
            "Real Comfy generation receipt + VLM deepen Class E readiness only; "
            "production clearance still requires mux/cut/camera/visual authority and "
            "compiler hard-fail removal."
        ),
        "summary": (
            f"RunPod Comfy real generation prompt_id={prompt_id} ckpt={CKPT}; "
            f"VLM {VLM_MODEL} reviewed {sum(1 for r in reviews if r.get('ok'))}/{len(reviews)} frames. "
            "ROW084-011 Class E remains OPEN (not cleared); ROW084-012 HOLD untouched; "
            "no COMPLETE/row_complete; Row074 left alone."
        ),
    }
    (OUT_DIR / "class_e_comfy_generation_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "vlm_review.json").write_text(
        json.dumps(
            {
                "cleared": False,
                "row_complete": False,
                "production_completion_allowed": False,
                "model_used": VLM_MODEL,
                "prompt_id": prompt_id,
                "reviews": reviews,
                "status": "VLM_REVIEW_BOUNDED_HOLD",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "OUT_DIR": str(OUT_DIR),
                "prompt_id": prompt_id,
                "completed": status.get("completed"),
                "frames": len(local_frames),
                "vlm_ok": sum(1 for r in reviews if r.get("ok")),
                "cleared": False,
                "row_complete": False,
                "proof_tier": receipt["proof_tier"],
            },
            indent=2,
        )
    )
    print("DONE_OUT_DIR=" + str(OUT_DIR))


if __name__ == "__main__":
    main()
