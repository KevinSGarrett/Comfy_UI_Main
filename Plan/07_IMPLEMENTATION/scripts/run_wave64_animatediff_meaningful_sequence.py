#!/usr/bin/env python3
"""Execute and technically evaluate one changed-scope AnimateDiff sequence."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageSequence, ImageStat


ROOT = Path(__file__).resolve().parents[3]
LANE_ID = "animatediff_fallback_meaningful_sequence"
TRACKER_ID = "TRK-W64-019"
ITEM_ID = "ITEM-W64-019"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temp.replace(path)


def http_json(method: str, url: str, payload: Any = None, timeout: int = 30) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def download_output(base_url: str, output: dict[str, Any], destination: Path) -> None:
    query = urllib.parse.urlencode(
        {
            "filename": output["filename"],
            "subfolder": output.get("subfolder", ""),
            "type": output.get("type", "output"),
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{base_url}/view?{query}", timeout=120) as response:
        destination.write_bytes(response.read())


def frame_metrics(frame: Image.Image) -> dict[str, float]:
    gray = frame.convert("L")
    histogram = gray.histogram()
    pixels = gray.width * gray.height
    return {
        "stddev": float(ImageStat.Stat(gray).stddev[0]),
        "white_clip_ratio": sum(histogram[250:]) / pixels,
        "black_clip_ratio": sum(histogram[:5]) / pixels,
    }


def pair_mad(left: Image.Image, right: Image.Image) -> float:
    histogram = ImageChops.difference(left.convert("L"), right.convert("L")).histogram()
    pixels = left.width * left.height
    return sum(value * count for value, count in enumerate(histogram)) / pixels


def make_contact_sheet(frames: list[Image.Image], path: Path) -> None:
    columns = 4
    width, height = frames[0].size
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * width, rows * height), "black")
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % columns) * width, (index // columns) * height))
    sheet.save(path, format="PNG")


def evaluate_artifact(artifact: Path, requirements: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    scope = requirements["sequence_scope"]
    limits = requirements["technical_thresholds"]
    frames: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(artifact) as animation:
        format_name = animation.format
        is_animated = bool(getattr(animation, "is_animated", False))
        for frame in ImageSequence.Iterator(animation):
            frames.append(frame.convert("RGB").copy())
            durations.append(int(frame.info.get("duration", animation.info.get("duration", 0))))
    if not frames:
        raise ValueError("Animated artifact decoded zero frames")

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    per_frame: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        frame_path = frames_dir / f"frame_{index:04d}.png"
        frame.save(frame_path, format="PNG")
        record = frame_metrics(frame)
        record.update(
            {
                "frame_index": index,
                "duration_ms": durations[index],
                "sha256": sha256(frame_path),
                "path": rel(frame_path),
            }
        )
        per_frame.append(record)

    pair_mads = [pair_mad(frames[index], frames[index + 1]) for index in range(len(frames) - 1)]
    mean_mad = statistics.fmean(pair_mads) if pair_mads else 0.0
    median_mad = statistics.median(pair_mads) if pair_mads else 0.0
    terminal_ratio = pair_mads[-1] / max(median_mad, 0.001) if pair_mads else 0.0
    expected_duration = round(1000 / float(scope["fps"]))
    checks = {
        "artifact_is_animated_webp": format_name == "WEBP" and is_animated,
        "frame_count_exact": len(frames) == int(scope["frame_count"]),
        "dimensions_exact": all(
            frame.size == (int(scope["width"]), int(scope["height"])) for frame in frames
        ),
        "timing_exact": all(abs(value - expected_duration) <= 40 for value in durations),
        "all_frames_nonblank": sum(item["stddev"] >= 2.0 for item in per_frame)
        >= int(limits["minimum_nonblank_frames"]),
        "motion_pair_count": sum(value >= 1.5 for value in pair_mads)
        >= int(limits["minimum_moving_pair_count"]),
        "mean_motion_in_range": float(limits["minimum_mean_adjacent_mad"])
        <= mean_mad
        <= float(limits["maximum_mean_adjacent_mad"]),
        "no_adjacent_discontinuity": bool(pair_mads)
        and max(pair_mads) <= float(limits["maximum_adjacent_mad"]),
        "no_terminal_discontinuity": bool(pair_mads)
        and terminal_ratio <= float(limits["maximum_terminal_to_median_mad_ratio"]),
        "white_clip_within_limit": max(item["white_clip_ratio"] for item in per_frame)
        <= float(limits["maximum_frame_white_clip_ratio"]),
        "black_clip_within_limit": max(item["black_clip_ratio"] for item in per_frame)
        <= float(limits["maximum_frame_black_clip_ratio"]),
    }
    contact_sheet = output_dir / "contact_sheet.png"
    make_contact_sheet(frames, contact_sheet)
    return {
        "artifact": {
            "path": rel(artifact),
            "sha256": sha256(artifact),
            "size_bytes": artifact.stat().st_size,
        },
        "decoded_sequence": {
            "format": format_name,
            "is_animated": is_animated,
            "frame_count": len(frames),
            "width": frames[0].width,
            "height": frames[0].height,
            "durations_ms": durations,
        },
        "frame_metrics": per_frame,
        "adjacent_pair_mad": pair_mads,
        "summary_metrics": {
            "mean_adjacent_mad": mean_mad,
            "median_adjacent_mad": median_mad,
            "maximum_adjacent_mad": max(pair_mads, default=0.0),
            "terminal_to_median_mad_ratio": terminal_ratio,
            "maximum_white_clip_ratio": max(item["white_clip_ratio"] for item in per_frame),
            "maximum_black_clip_ratio": max(item["black_clip_ratio"] for item in per_frame),
        },
        "contact_sheet": {"path": rel(contact_sheet), "sha256": sha256(contact_sheet)},
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "technical_pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--evidence-timestamp")
    args = parser.parse_args()

    workflow = read_json(args.workflow)
    requirements = read_json(args.requirements)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = args.evidence_timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
    base_url = args.runtime_url.rstrip("/")

    assets = requirements["assets"]
    asset_checks = []
    for asset in assets:
        path = Path(asset["local_path"])
        observed = sha256(path) if path.is_file() else None
        asset_checks.append(
            {
                "role": asset["role"],
                "path": str(path),
                "exists": path.is_file(),
                "expected_sha256": asset["sha256"],
                "observed_sha256": observed,
                "hash_match": observed == asset["sha256"],
            }
        )
    if not all(item["hash_match"] for item in asset_checks):
        raise RuntimeError("Required asset hash preflight failed")

    queue = http_json("GET", f"{base_url}/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle")
    object_info = http_json("GET", f"{base_url}/object_info", timeout=60)
    required_nodes = {node["class_type"] for node in workflow.values()}
    missing_nodes = sorted(required_nodes - set(object_info))
    if missing_nodes:
        raise RuntimeError(f"Required ComfyUI nodes missing: {missing_nodes}")

    request_payload = {"prompt": workflow, "client_id": "wave64-animatediff-meaningful-sequence"}
    write_json(output_dir / "prompt_request.json", request_payload)
    response = http_json("POST", f"{base_url}/prompt", request_payload)
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise RuntimeError(f"Prompt response missing prompt_id: {response}")
    write_json(output_dir / "prompt_response.json", response)

    deadline = time.monotonic() + args.timeout_seconds
    history_entry: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        history = http_json("GET", f"{base_url}/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            history_entry = history[prompt_id]
            break
        time.sleep(2)
    if history_entry is None:
        raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")
    write_json(output_dir / "history.json", {prompt_id: history_entry})

    status = history_entry.get("status") or {}
    if not status.get("completed") or status.get("status_str") != "success":
        raise RuntimeError(f"ComfyUI execution did not complete successfully: {status}")
    outputs = history_entry.get("outputs") or {}
    node_output = outputs.get("12") or {}
    candidates = node_output.get("images") or []
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one output artifact, found {len(candidates)}")
    output_meta = candidates[0]
    artifact = output_dir / output_meta["filename"]
    download_output(base_url, output_meta, artifact)

    technical = evaluate_artifact(artifact, requirements, output_dir)
    evidence = {
        "schema_name": "wave64_animatediff_meaningful_sequence_evidence",
        "schema_version": "1.0",
        "timestamp": timestamp,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "lane_id": LANE_ID,
        "result": (
            "pass_automated_technical_direct_visual_review_required"
            if technical["technical_pass"]
            else "blocked_automated_technical_quality_failure"
        ),
        "prompt_id": prompt_id,
        "workflow": {"path": rel(args.workflow), "sha256": sha256(args.workflow)},
        "runtime_requirements": {
            "path": rel(args.requirements),
            "sha256": sha256(args.requirements),
        },
        "asset_preflight": asset_checks,
        "runtime": {
            "url": base_url,
            "queue_idle_before_submission": True,
            "required_nodes_present": True,
            "completed": True,
            "status": status,
        },
        "technical_evaluation": technical,
        "boundaries": {
            **requirements["boundaries"],
            "generation_executed": True,
            "direct_visual_review_completed": False,
            "technical_pass_does_not_imply_visual_or_production_pass": True,
        },
        "next_action": "Perform direct review of the animated WebP and all 16 contact-sheet frames. Preserve this single attempt regardless of result.",
    }
    write_json(output_dir / "runtime_technical_evidence.json", evidence)
    print(json.dumps({"result": evidence["result"], "prompt_id": prompt_id, "output_dir": str(output_dir), "technical_pass": technical["technical_pass"], "failed_checks": technical["failed_checks"]}, indent=2))
    return 0 if technical["technical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
