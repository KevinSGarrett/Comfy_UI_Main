#!/usr/bin/env python3
"""Build, execute, and validate Row022 pose and relative-depth timelines."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-022"
ITEM_ID = "ITEM-W64-022"
POSE_NODE_ID = "200"
POSE_IMAGE_NODE_ID = "201"
POSE_JSON_NODE_ID = "202"
DEPTH_NODE_ID = "203"
DEPTH_IMAGE_NODE_ID = "204"


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
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not all(isinstance(record, dict) for record in records):
        raise TypeError(f"JSONL objects required: {path}")
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temp.replace(path)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=True) + "\n")
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


def validate_source_frames(
    records: list[dict[str, Any]], frames_dir: Path, scope: dict[str, Any]
) -> list[Path]:
    expected_count = int(scope["frame_count"])
    if len(records) != expected_count:
        raise ValueError(f"Expected {expected_count} source records, found {len(records)}")
    expected_indexes = list(range(expected_count))
    observed_indexes = [int(record["frame_index"]) for record in records]
    if observed_indexes != expected_indexes:
        raise ValueError("Source frame records are not ordered and contiguous")

    source_paths: list[Path] = []
    for record in records:
        path = frames_dir / Path(str(record["frame_path_or_asset_id"])).name
        if not path.is_file():
            raise FileNotFoundError(path)
        observed_hash = sha256(path)
        if observed_hash != record.get("png_sha256"):
            raise ValueError(f"Source frame hash mismatch: {path}")
        with Image.open(path) as image:
            if image.size != (int(scope["width"]), int(scope["height"])):
                raise ValueError(f"Source frame dimensions mismatch: {path} {image.size}")
        source_paths.append(path)
    return source_paths


def build_workflow(input_names: list[str], output_prefix: str, config: dict[str, Any]) -> dict[str, Any]:
    if len(input_names) < 2:
        raise ValueError("At least two ordered input images are required")
    workflow: dict[str, Any] = {}
    load_ids: list[str] = []
    for index, name in enumerate(input_names, start=1):
        node_id = str(index)
        load_ids.append(node_id)
        workflow[node_id] = {"class_type": "LoadImage", "inputs": {"image": name}}

    previous: list[Any] = [load_ids[0], 0]
    for offset, load_id in enumerate(load_ids[1:]):
        batch_id = str(100 + offset)
        workflow[batch_id] = {
            "class_type": "ImageBatch",
            "inputs": {"image1": previous, "image2": [load_id, 0]},
        }
        previous = [batch_id, 0]

    workflow[POSE_NODE_ID] = {
        "class_type": "DWPreprocessor",
        "inputs": {
            "image": previous,
            "detect_hand": "enable",
            "detect_body": "enable",
            "detect_face": "enable",
            "resolution": int(config["resolution"]),
            "bbox_detector": config["dwpose_bbox_detector"],
            "pose_estimator": config["dwpose_pose_estimator"],
            "scale_stick_for_xinsr_cn": "disable",
        },
    }
    workflow[POSE_IMAGE_NODE_ID] = {
        "class_type": "SaveImage",
        "inputs": {"images": [POSE_NODE_ID, 0], "filename_prefix": f"{output_prefix}/pose/frame"},
    }
    workflow[POSE_JSON_NODE_ID] = {
        "class_type": "SavePoseKpsAsJsonFile",
        "inputs": {
            "pose_kps": [POSE_NODE_ID, 1],
            "filename_prefix": f"{output_prefix}/pose_keypoints/timeline",
        },
    }
    workflow[DEPTH_NODE_ID] = {
        "class_type": "DepthAnythingV2Preprocessor",
        "inputs": {
            "image": previous,
            "ckpt_name": config["depth_checkpoint"],
            "resolution": int(config["resolution"]),
        },
    }
    workflow[DEPTH_IMAGE_NODE_ID] = {
        "class_type": "SaveImage",
        "inputs": {"images": [DEPTH_NODE_ID, 0], "filename_prefix": f"{output_prefix}/depth/frame"},
    }
    return workflow


def count_valid_keypoints(values: Any) -> int:
    if not isinstance(values, list) or len(values) % 3:
        return 0
    return sum(1 for index in range(2, len(values), 3) if float(values[index]) > 0.0)


def expected_preprocessor_dimensions(scope: dict[str, Any], resolution: int) -> tuple[int, int]:
    source_width = int(scope["width"])
    source_height = int(scope["height"])
    scale = float(resolution) / min(source_width, source_height)
    return round(source_width * scale), round(source_height * scale)


def image_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        gray = image.convert("L")
        histogram = gray.histogram()
        pixel_count = gray.width * gray.height
        nonblack = sum(histogram[2:]) / pixel_count
        occupied = [index for index, count in enumerate(histogram) if count]
        return {
            "width": image.width,
            "height": image.height,
            "stddev": float(ImageStat.Stat(gray).stddev[0]),
            "nonblack_ratio": nonblack,
            "dynamic_range": max(occupied) - min(occupied) if occupied else 0,
        }


def adjacent_mad(paths: list[Path]) -> list[float]:
    values: list[float] = []
    for left_path, right_path in zip(paths, paths[1:]):
        with Image.open(left_path) as left_source, Image.open(right_path) as right_source:
            left = left_source.convert("L")
            right = right_source.convert("L")
            histogram = ImageChops.difference(left, right).histogram()
            values.append(
                sum(value * count for value, count in enumerate(histogram))
                / (left.width * left.height)
            )
    return values


def make_contact_sheet(paths: list[Path], destination: Path) -> None:
    columns = 7
    tile_width, tile_height = 180, 240
    header = 22
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * (tile_height + header)), "black")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = source.convert("RGB")
            image.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
            x = (index % columns) * tile_width + (tile_width - image.width) // 2
            y = (index // columns) * (tile_height + header) + header
            sheet.paste(image, (x, y))
            draw.text((index % columns * tile_width + 5, y - 18), f"frame {index:02d}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")


def evaluate_timelines(
    source_records: list[dict[str, Any]],
    pose_paths: list[Path],
    depth_paths: list[Path],
    pose_frames: Any,
    requirements: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    scope = requirements["source_scope"]
    limits = requirements["technical_thresholds"]
    expected_count = int(scope["frame_count"])
    source_dimensions = (int(scope["width"]), int(scope["height"]))
    render_dimensions = expected_preprocessor_dimensions(
        scope, int(requirements["workflow"]["resolution"])
    )
    render_to_source_transform = {
        "mode": "deterministic_short_edge_scale_inverse",
        "render_width": render_dimensions[0],
        "render_height": render_dimensions[1],
        "source_width": source_dimensions[0],
        "source_height": source_dimensions[1],
        "source_x_per_render_x": source_dimensions[0] / render_dimensions[0],
        "source_y_per_render_y": source_dimensions[1] / render_dimensions[1],
        "padding_removed_by_preprocessor": True,
    }
    if not isinstance(pose_frames, list):
        raise TypeError("Saved pose keypoints must be a JSON list")

    pose_metrics = [image_metrics(path) for path in pose_paths]
    depth_metrics = [image_metrics(path) for path in depth_paths]
    pose_records: list[dict[str, Any]] = []
    depth_records: list[dict[str, Any]] = []
    for index in range(min(len(source_records), len(pose_paths), len(depth_paths), len(pose_frames))):
        source = source_records[index]
        pose_frame = pose_frames[index]
        people = pose_frame.get("people", []) if isinstance(pose_frame, dict) else []
        body_counts = [count_valid_keypoints(person.get("pose_keypoints_2d")) for person in people]
        left_hand_counts = [count_valid_keypoints(person.get("hand_left_keypoints_2d")) for person in people]
        right_hand_counts = [count_valid_keypoints(person.get("hand_right_keypoints_2d")) for person in people]
        face_counts = [count_valid_keypoints(person.get("face_keypoints_2d")) for person in people]
        pose_records.append(
            {
                "frame_id": source["frame_id"],
                "frame_index": index,
                "timestamp_seconds": source["timestamp_seconds"],
                "source_png_sha256": source["png_sha256"],
                "pose_render_path": rel(pose_paths[index]),
                "pose_render_sha256": sha256(pose_paths[index]),
                "person_count": len(people),
                "body_valid_keypoints": body_counts,
                "left_hand_valid_keypoints": left_hand_counts,
                "right_hand_valid_keypoints": right_hand_counts,
                "face_valid_keypoints": face_counts,
                "canvas_width": pose_frame.get("canvas_width") if isinstance(pose_frame, dict) else None,
                "canvas_height": pose_frame.get("canvas_height") if isinstance(pose_frame, dict) else None,
                "render_to_source_transform": render_to_source_transform,
            }
        )
        depth_records.append(
            {
                "frame_id": source["frame_id"],
                "frame_index": index,
                "timestamp_seconds": source["timestamp_seconds"],
                "source_png_sha256": source["png_sha256"],
                "depth_render_path": rel(depth_paths[index]),
                "depth_render_sha256": sha256(depth_paths[index]),
                "relative_depth_only": True,
                "render_to_source_transform": render_to_source_transform,
                **depth_metrics[index],
            }
        )

    checks = {
        "pose_output_count_exact": len(pose_paths) == expected_count,
        "depth_output_count_exact": len(depth_paths) == expected_count,
        "pose_keypoint_frame_count_exact": len(pose_frames) == expected_count,
        "pose_preprocessor_dimensions_exact": len(pose_metrics) == expected_count
        and all((item["width"], item["height"]) == render_dimensions for item in pose_metrics),
        "depth_preprocessor_dimensions_exact": len(depth_metrics) == expected_count
        and all((item["width"], item["height"]) == render_dimensions for item in depth_metrics),
        "one_person_each_frame": len(pose_records) == expected_count
        and all(item["person_count"] == 1 for item in pose_records),
        "body_keypoints_each_frame": len(pose_records) == expected_count
        and all(
            item["body_valid_keypoints"]
            and item["body_valid_keypoints"][0] >= int(limits["minimum_body_keypoints_per_frame"])
            for item in pose_records
        ),
        "pose_canvas_dimensions_exact": len(pose_records) == expected_count
        and all(
            (item["canvas_width"], item["canvas_height"]) == source_dimensions
            for item in pose_records
        ),
        "pose_render_nonblank": len(pose_metrics) == expected_count
        and all(
            item["nonblack_ratio"] >= float(limits["minimum_pose_nonblack_ratio"])
            and item["stddev"] >= float(limits["minimum_pose_stddev"])
            for item in pose_metrics
        ),
        "depth_render_nonblank": len(depth_metrics) == expected_count
        and all(
            item["stddev"] >= float(limits["minimum_depth_stddev"])
            and item["dynamic_range"] >= int(limits["minimum_depth_dynamic_range"])
            for item in depth_metrics
        ),
        "pose_hash_diversity": len({sha256(path) for path in pose_paths})
        >= int(limits["minimum_unique_pose_hashes"]),
        "depth_hash_diversity": len({sha256(path) for path in depth_paths})
        >= int(limits["minimum_unique_depth_hashes"]),
        "source_timestamps_monotonic": [record["timestamp_seconds"] for record in source_records]
        == sorted(record["timestamp_seconds"] for record in source_records),
    }

    pose_timeline = output_dir / "pose_timeline.jsonl"
    depth_timeline = output_dir / "depth_timeline.jsonl"
    write_jsonl(pose_timeline, pose_records)
    write_jsonl(depth_timeline, depth_records)
    pose_sheet = output_dir / "pose_contact_sheet.png"
    depth_sheet = output_dir / "depth_contact_sheet.png"
    if pose_paths:
        make_contact_sheet(pose_paths, pose_sheet)
    if depth_paths:
        make_contact_sheet(depth_paths, depth_sheet)

    pose_mads = adjacent_mad(pose_paths) if len(pose_paths) > 1 else []
    depth_mads = adjacent_mad(depth_paths) if len(depth_paths) > 1 else []
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "checks": checks,
        "failed_checks": failed_checks,
        "technical_pass": not failed_checks,
        "coordinate_contract": {
            "source_dimensions": list(source_dimensions),
            "preprocessor_render_dimensions": list(render_dimensions),
            "pose_keypoint_canvas_is_source_coordinates": True,
            "render_to_source_transform": render_to_source_transform,
        },
        "pose_timeline": {"path": rel(pose_timeline), "sha256": sha256(pose_timeline)},
        "depth_timeline": {"path": rel(depth_timeline), "sha256": sha256(depth_timeline)},
        "pose_contact_sheet": {
            "path": rel(pose_sheet),
            "sha256": sha256(pose_sheet) if pose_sheet.is_file() else None,
        },
        "depth_contact_sheet": {
            "path": rel(depth_sheet),
            "sha256": sha256(depth_sheet) if depth_sheet.is_file() else None,
        },
        "pose_summary": {
            "frame_count": len(pose_records),
            "person_count_range": [
                min((item["person_count"] for item in pose_records), default=0),
                max((item["person_count"] for item in pose_records), default=0),
            ],
            "minimum_body_keypoints": min(
                (item["body_valid_keypoints"][0] for item in pose_records if item["body_valid_keypoints"]),
                default=0,
            ),
            "frames_with_left_hand": sum(
                bool(item["left_hand_valid_keypoints"] and item["left_hand_valid_keypoints"][0])
                for item in pose_records
            ),
            "frames_with_right_hand": sum(
                bool(item["right_hand_valid_keypoints"] and item["right_hand_valid_keypoints"][0])
                for item in pose_records
            ),
            "frames_with_face": sum(
                bool(item["face_valid_keypoints"] and item["face_valid_keypoints"][0])
                for item in pose_records
            ),
            "unique_render_hashes": len({sha256(path) for path in pose_paths}),
            "mean_adjacent_render_mad": statistics.fmean(pose_mads) if pose_mads else 0.0,
        },
        "depth_summary": {
            "frame_count": len(depth_records),
            "minimum_stddev": min((item["stddev"] for item in depth_metrics), default=0.0),
            "minimum_dynamic_range": min(
                (item["dynamic_range"] for item in depth_metrics), default=0
            ),
            "unique_render_hashes": len({sha256(path) for path in depth_paths}),
            "mean_adjacent_render_mad": statistics.fmean(depth_mads) if depth_mads else 0.0,
            "metric_depth_claimed": False,
        },
    }


def asset_preflight(requirements: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for asset in requirements["assets"]:
        path = Path(asset["local_path"])
        observed_hash = sha256(path) if path.is_file() else None
        observed_size = path.stat().st_size if path.is_file() else None
        results.append(
            {
                "role": asset["role"],
                "path": str(path),
                "exists": path.is_file(),
                "expected_sha256": asset["sha256"],
                "observed_sha256": observed_hash,
                "expected_size_bytes": asset["size_bytes"],
                "observed_size_bytes": observed_size,
                "pass": observed_hash == asset["sha256"]
                and observed_size == int(asset["size_bytes"]),
            }
        )
    repository = Path(requirements["custom_node_repository"]["path"])
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    results.append(
        {
            "role": "controlnet_aux_repository_commit",
            "path": str(repository),
            "expected_commit": requirements["custom_node_repository"]["commit"],
            "observed_commit": commit,
            "pass": commit == requirements["custom_node_repository"]["commit"],
        }
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-frames-dir", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--comfy-input-dir", type=Path, required=True)
    parser.add_argument("--comfy-output-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--run-id")
    parser.add_argument("--timestamp")
    args = parser.parse_args()

    requirements = read_json(args.requirements)
    records = read_jsonl(args.source_manifest)
    source_paths = validate_source_frames(records, args.source_frames_dir, requirements["source_scope"])
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory must be empty or absent: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = args.timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = args.run_id or datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    run_id = run_id.replace("+", "p").replace("-", "m")
    output_prefix = f"wave64_row022_pose_depth/{run_id}"
    stage_dir = args.comfy_input_dir.resolve() / output_prefix / "source"
    if stage_dir.exists():
        raise FileExistsError(f"ComfyUI input stage already exists: {stage_dir}")
    stage_dir.mkdir(parents=True)

    asset_checks = asset_preflight(requirements)
    if not all(item["pass"] for item in asset_checks):
        write_json(output_dir / "asset_preflight_failure.json", asset_checks)
        raise RuntimeError("Required model/repository preflight failed")

    input_names: list[str] = []
    for index, source in enumerate(source_paths):
        destination = stage_dir / f"frame_{index:06d}.png"
        shutil.copy2(source, destination)
        if sha256(destination) != records[index]["png_sha256"]:
            raise RuntimeError(f"Staged source hash mismatch: {destination}")
        input_names.append(destination.relative_to(args.comfy_input_dir.resolve()).as_posix())

    workflow = build_workflow(input_names, output_prefix, requirements["workflow"])
    write_json(output_dir / "workflow.api.json", workflow)
    base_url = args.runtime_url.rstrip("/")
    queue = http_json("GET", f"{base_url}/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not idle")
    object_info = http_json("GET", f"{base_url}/object_info", timeout=90)
    required_nodes = set(requirements["workflow"]["required_nodes"])
    missing_nodes = sorted(required_nodes - set(object_info))
    if missing_nodes:
        raise RuntimeError(f"Required ComfyUI nodes missing: {missing_nodes}")

    request_payload = {"prompt": workflow, "client_id": "wave64-row022-pose-depth-timeline"}
    write_json(output_dir / "prompt_request.json", request_payload)
    response = http_json("POST", f"{base_url}/prompt", request_payload, timeout=60)
    write_json(output_dir / "prompt_response.json", response)
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise RuntimeError(f"Prompt response missing prompt_id: {response}")

    deadline = time.monotonic() + args.timeout_seconds
    history_entry: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        history = http_json("GET", f"{base_url}/history/{prompt_id}", timeout=60)
        if prompt_id in history:
            history_entry = history[prompt_id]
            break
        time.sleep(3)
    if history_entry is None:
        raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")
    write_json(output_dir / "history.json", {prompt_id: history_entry})
    status = history_entry.get("status") or {}
    if not status.get("completed") or status.get("status_str") != "success":
        raise RuntimeError(f"ComfyUI execution did not complete successfully: {status}")

    outputs = history_entry.get("outputs") or {}
    pose_meta = (outputs.get(POSE_IMAGE_NODE_ID) or {}).get("images") or []
    depth_meta = (outputs.get(DEPTH_IMAGE_NODE_ID) or {}).get("images") or []
    pose_dir = output_dir / "pose"
    depth_dir = output_dir / "depth"
    pose_paths: list[Path] = []
    depth_paths: list[Path] = []
    for index, metadata in enumerate(pose_meta):
        destination = pose_dir / f"frame_{index:06d}.png"
        download_output(base_url, metadata, destination)
        pose_paths.append(destination)
    for index, metadata in enumerate(depth_meta):
        destination = depth_dir / f"frame_{index:06d}.png"
        download_output(base_url, metadata, destination)
        depth_paths.append(destination)

    pose_json_dir = args.comfy_output_dir.resolve() / output_prefix / "pose_keypoints"
    pose_json_candidates = sorted(pose_json_dir.glob("timeline_*.json"))
    if len(pose_json_candidates) != 1:
        raise RuntimeError(f"Expected one pose-keypoint JSON, found {len(pose_json_candidates)}")
    pose_json_path = output_dir / "pose_keypoints.json"
    shutil.copy2(pose_json_candidates[0], pose_json_path)
    pose_frames = json.loads(pose_json_path.read_text(encoding="utf-8"))

    technical = evaluate_timelines(
        records, pose_paths, depth_paths, pose_frames, requirements, output_dir
    )
    evidence = {
        "schema_name": "wave64_reference_pose_depth_timeline_runtime_evidence",
        "schema_version": "1.0",
        "timestamp": timestamp,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "result": (
            "pass_pose_and_relative_depth_timelines_target_mask_contact_authority_blocked"
            if technical["technical_pass"]
            else "blocked_pose_or_relative_depth_technical_validation_failed"
        ),
        "prompt_id": prompt_id,
        "source_manifest": {"path": rel(args.source_manifest), "sha256": sha256(args.source_manifest)},
        "source_frame_count": len(records),
        "workflow": {"path": rel(output_dir / "workflow.api.json"), "sha256": sha256(output_dir / "workflow.api.json")},
        "runtime_requirements": {"path": rel(args.requirements), "sha256": sha256(args.requirements)},
        "asset_preflight": asset_checks,
        "runtime": {
            "url": base_url,
            "queue_idle_before_submission": True,
            "required_nodes_present": True,
            "completed": True,
            "status": status,
        },
        "pose_keypoints": {"path": rel(pose_json_path), "sha256": sha256(pose_json_path)},
        "technical_evaluation": technical,
        "authority_boundaries": requirements["authority_boundaries"],
        "next_action": (
            "Perform direct visual review of both 49-frame contact sheets, then reconcile Row022 without clearing mask/contact or target-shot-match blockers."
        ),
    }
    write_json(output_dir / "runtime_technical_evidence.json", evidence)
    print(
        json.dumps(
            {
                "result": evidence["result"],
                "prompt_id": prompt_id,
                "output_dir": str(output_dir),
                "technical_pass": technical["technical_pass"],
                "failed_checks": technical["failed_checks"],
            },
            indent=2,
        )
    )
    return 0 if technical["technical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
