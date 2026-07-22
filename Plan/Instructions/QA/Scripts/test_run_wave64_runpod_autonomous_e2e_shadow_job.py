from __future__ import annotations

import base64
import importlib.util
import io
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_e2e_shadow_job.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("w64_aqa_e2e_shadow", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_bytes(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 17) % 256, (y * 31) % 256, ((x + y) * 13) % 256)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def object_info(input_filename: str) -> dict:
    return {
        "LoadImage": {
            "input": {"required": {"image": [[input_filename]]}},
            "output": ["IMAGE", "MASK"],
            "output_node": False,
        },
        "ImageScale": {
            "input": {
                "required": {
                    "image": ["IMAGE"],
                    "upscale_method": [["nearest-exact", "bilinear"]],
                    "width": ["INT"],
                    "height": ["INT"],
                    "crop": [["disabled", "center"]],
                }
            },
            "output": ["IMAGE"],
            "output_node": False,
        },
        "SaveImage": {
            "input": {
                "required": {"images": ["IMAGE"], "filename_prefix": ["STRING"]}
            },
            "output": ["IMAGE"],
            "output_node": True,
        },
    }


def fake_remote(module, *, foreign: bool = False):
    stored_input = {}
    output_counter = 0

    def remote(host, port, request, *, timeout_seconds):
        nonlocal output_counter
        if request["action"] == "probe":
            return {
                "observed_at": "2026-07-21T22:00:00Z",
                "queue_running": 0,
                "queue_pending": 0,
                "comfyui_system_stats_healthy": True,
                "loaded_models": [],
                "active_foreign_workloads": (
                    [{"pid": 123, "workload_class": "maskfactory_hand_tournament"}]
                    if foreign
                    else []
                ),
                "gpu": {
                    "name": "NVIDIA RTX 6000 Ada Generation",
                    "total_mib": 49140,
                    "used_mib": 648,
                    "free_mib": 47993,
                    "utilization_percent": 0,
                },
                "overlay": {"used_percent": 79.0},
                "workspace": {"used_percent": 74.0},
            }
        if request["action"] == "upload":
            stored_input["filename"] = request["filename"]
            stored_input["content"] = base64.b64decode(request["content_b64"])
            return {
                "relative_path": request["filename"],
                "sha256": request["sha256"],
                "byte_size": len(stored_input["content"]),
                "disposition": "CREATED",
            }
        if request["action"] == "object_info":
            return object_info(stored_input["filename"])
        if request["action"] == "execute":
            output_counter += 1
            width = request["workflow"]["2"]["inputs"]["width"]
            height = request["workflow"]["2"]["inputs"]["height"]
            content = png_bytes((width, height))
            relative = (
                "w64_aqa_shadow/base_00001_.png"
                if output_counter == 1
                else "w64_aqa_shadow/corrected_00001_.png"
            )
            return {
                "prompt_id": f"prompt-{output_counter}",
                "output_relative_path": relative,
                "output_sha256": module.sha256_bytes(content),
                "output_size_bytes": len(content),
                "output_b64": base64.b64encode(content).decode("ascii"),
                "queue_idle_after": True,
                "gpu_after": {"free_mib": 47993},
            }
        if request["action"] == "cleanup":
            return {"removed": request["artifacts"]}
        raise AssertionError(request)

    return remote


def test_full_shadow_job_repairs_replays_and_cleans_up(tmp_path: Path) -> None:
    module = load_runner()
    source = tmp_path / "source.png"
    source.write_bytes(png_bytes((64, 64)))
    artifact_dir = tmp_path / "evidence"
    result = module.run_shadow_job(
        source_path=source,
        artifact_dir=artifact_dir,
        host="root@example.invalid",
        port=22,
        pod_id="pod-test",
        network_volume_id="volume-test",
        hourly_compute_usd=0.77,
        remote=fake_remote(module),
    )
    assert result["initial_disposition"] == "FAIL_DETERMINISTIC_GATES"
    assert result["correction_disposition"] == "RETAIN_CANDIDATE_EXIT_REPAIR_LOOP"
    assert result["accepted_disposition"] == "PASS_EVIDENCE_ONLY_SHADOW_INFRASTRUCTURE"
    assert result["replay_disposition"] == "MATCH"
    assert result["remote_cleanup_pass"] is True
    assert result["lease_final_state"] == "IDLE"
    assert result["product_promotion_claimed"] is False
    assert (artifact_dir / "accepted_candidate.png").is_file()
    assert (artifact_dir / "evidence_bundle.json").is_file()


def test_foreign_workload_is_observed_but_does_not_override_capacity_lease(tmp_path: Path) -> None:
    module = load_runner()
    source = tmp_path / "source.png"
    source.write_bytes(png_bytes((64, 64)))
    artifact_dir = tmp_path / "evidence"
    result = module.run_shadow_job(
        source_path=source,
        artifact_dir=artifact_dir,
        host="root@example.invalid",
        port=22,
        pod_id="pod-test",
        network_volume_id="volume-test",
        hourly_compute_usd=0.77,
        remote=fake_remote(module, foreign=True),
    )
    runtime = json.loads((artifact_dir / "runtime_receipt.json").read_text())
    assert runtime["preflight"]["active_foreign_workloads"]
    assert result["accepted_disposition"] == "PASS_EVIDENCE_ONLY_SHADOW_INFRASTRUCTURE"
