#!/usr/bin/env python3
"""Evaluate one bounded AnimateDiff WebP without claiming visual certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageSequence, ImageStat


ROOT = Path(__file__).resolve().parents[3]
LANE_ID = "animatediff_fallback"
TRACKER_ID = "TRK-W64-019"
ITEM_ID = "ITEM-W64-019"
EVALUATOR_VERSION = "1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def node_of_type(graph: dict[str, Any], class_type: str) -> dict[str, Any]:
    nodes = [node for node in graph.values() if node.get("class_type") == class_type]
    if len(nodes) != 1:
        raise ValueError(f"Expected one {class_type}, found {len(nodes)}")
    return nodes[0]


def percentile(histogram: list[int], fraction: float) -> int:
    total = sum(histogram)
    target = max(1, round(total * fraction))
    cumulative = 0
    for value, count in enumerate(histogram):
        cumulative += count
        if cumulative >= target:
            return value
    return 255


def frame_metrics(frame: Image.Image) -> dict[str, Any]:
    gray = frame.convert("L")
    histogram = gray.histogram()
    pixels = gray.width * gray.height
    p01 = percentile(histogram, 0.01)
    p99 = percentile(histogram, 0.99)
    std = float(ImageStat.Stat(gray).stddev[0])
    white_clip_ratio = sum(histogram[250:]) / pixels
    black_clip_ratio = sum(histogram[:5]) / pixels
    passed = std >= 2.0 and (p99 - p01) >= 8
    return {
        "std": std,
        "p01": p01,
        "p99": p99,
        "intensity_range_p01_p99": p99 - p01,
        "white_clip_ratio": white_clip_ratio,
        "black_clip_ratio": black_clip_ratio,
        "nonblank_pass": passed,
    }


def pair_metrics(left: Image.Image, right: Image.Image) -> dict[str, Any]:
    difference = ImageChops.difference(left.convert("L"), right.convert("L"))
    histogram = difference.histogram()
    pixels = difference.width * difference.height
    mad = sum(value * count for value, count in enumerate(histogram)) / pixels
    changed = sum(histogram[6:]) / pixels
    return {"mean_absolute_difference": mad, "changed_pixel_ratio_delta_gt_5": changed}


def make_contact_sheet(frames: list[Image.Image], path: Path) -> None:
    columns = 4
    rows = (len(frames) + columns - 1) // columns
    width, height = frames[0].size
    sheet = Image.new("RGB", (columns * width, rows * height), "black")
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % columns) * width, (index // columns) * height))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, format="PNG")


def git_commit(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--runtime-evidence", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--motion-model", type=Path, required=True)
    parser.add_argument("--custom-node-dir", type=Path, required=True)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--frame-records-out", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--evidence-timestamp",
        help="Stable ISO-8601 timestamp for reproducible evidence regeneration.",
    )
    args = parser.parse_args()

    evidence_timestamp = args.evidence_timestamp or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    datetime.fromisoformat(evidence_timestamp)

    paths = {
        name: resolve(getattr(args, name))
        for name in (
            "workflow",
            "requirements",
            "runtime_evidence",
            "artifact",
            "checkpoint",
            "motion_model",
            "custom_node_dir",
            "frames_dir",
            "contact_sheet",
            "frame_records_out",
            "out",
        )
    }
    required_files = [
        paths[name]
        for name in ("workflow", "requirements", "runtime_evidence", "artifact", "checkpoint", "motion_model")
    ]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required files missing: {missing}")
    if not paths["custom_node_dir"].is_dir():
        raise FileNotFoundError(f"Custom node directory missing: {paths['custom_node_dir']}")

    workflow = read_json(paths["workflow"])
    requirements = read_json(paths["requirements"])
    runtime = read_json(paths["runtime_evidence"])
    scope = requirements["smoke_scope"]
    assets = {entry["role"]: entry for entry in requirements["assets"]}

    latent = node_of_type(workflow, "EmptyLatentImage")["inputs"]
    save = node_of_type(workflow, "SaveAnimatedWEBP")["inputs"]
    checkpoint_node = node_of_type(workflow, "CheckpointLoaderSimple")["inputs"]
    motion_node = node_of_type(workflow, "ADE_LoadAnimateDiffModel")["inputs"]

    artifact_hash = sha256(paths["artifact"])
    runtime_artifacts = runtime.get("artifacts") or []
    matching_runtime_artifacts = [
        entry
        for entry in runtime_artifacts
        if entry.get("local_path") == rel(paths["artifact"])
    ]

    expected_width = int(scope["width"])
    expected_height = int(scope["height"])
    expected_frames = int(scope["frame_count"])
    expected_fps = float(scope["fps"])
    expected_duration_ms = round(1000.0 / expected_fps)

    decoded_frames: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(paths["artifact"]) as animation:
        format_name = animation.format
        animated = bool(getattr(animation, "is_animated", False))
        for frame in ImageSequence.Iterator(animation):
            decoded_frames.append(frame.convert("RGB").copy())
            durations.append(int(frame.info.get("duration", animation.info.get("duration", 0))))

    if not decoded_frames:
        raise ValueError("Animated WebP decoded zero frames")

    paths["frames_dir"].mkdir(parents=True, exist_ok=True)
    frame_records: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for index, frame in enumerate(decoded_frames):
        frame_path = paths["frames_dir"] / f"frame_{index:04d}.png"
        frame.save(frame_path, format="PNG")
        current_metrics = frame_metrics(frame)
        current_metrics.update(
            {
                "frame_index": index,
                "duration_ms": durations[index],
                "width": frame.width,
                "height": frame.height,
                "path": rel(frame_path),
                "sha256": sha256(frame_path),
                "size_bytes": frame_path.stat().st_size,
            }
        )
        metrics.append(current_metrics)
        frame_records.append(
            {
                "frame_index": index,
                "time_seconds": index / expected_fps,
                "source_route": "local_animatediff_fallback_runtime_smoke",
                "engine_name": LANE_ID,
                "shot_id": "wave64_row019_animatediff_smoke",
                "visible_characters": ["adult_catalog_subject"],
                "camera_state": {"framing": "portrait", "camera_motion": "locked"},
                "qa_scores": {},
                "repair_status": "unknown",
                "artifact_path": str(frame_path.resolve()),
                "artifact_sha256": current_metrics["sha256"],
                "notes": "Technical extraction only; visual and temporal QA remain separate.",
            }
        )

    pairs = [pair_metrics(decoded_frames[index], decoded_frames[index + 1]) for index in range(len(decoded_frames) - 1)]
    for index, pair in enumerate(pairs):
        pair["left_frame_index"] = index
        pair["right_frame_index"] = index + 1

    make_contact_sheet(decoded_frames, paths["contact_sheet"])
    write_json(paths["frame_records_out"], frame_records)

    nonblank_count = sum(1 for entry in metrics if entry["nonblank_pass"])
    moving_pair_count = sum(1 for pair in pairs if pair["mean_absolute_difference"] >= 1.5)
    mean_pair_mad = (
        sum(pair["mean_absolute_difference"] for pair in pairs) / len(pairs) if pairs else 0.0
    )
    max_changed_ratio = max((pair["changed_pixel_ratio_delta_gt_5"] for pair in pairs), default=0.0)
    timing_pass = all(
        duration > 0 and abs(duration - expected_duration_ms) <= 40 for duration in durations
    ) and abs(sum(durations) - round(expected_frames / expected_fps * 1000)) <= 50

    checks = {
        "runtime_lane_bound": runtime.get("lane_id") == LANE_ID,
        "runtime_result_pass": runtime.get("result") == "pass_local_animatediff_fallback_runtime_smoke",
        "runtime_completed_without_node_errors": runtime.get("history", {}).get("completed") is True
        and not runtime.get("history", {}).get("node_errors"),
        "runtime_artifact_hash_bound": len(matching_runtime_artifacts) == 1
        and matching_runtime_artifacts[0].get("sha256") == artifact_hash,
        "workflow_lane_dimensions_bound": int(latent["width"]) == expected_width
        and int(latent["height"]) == expected_height
        and int(latent["batch_size"]) == expected_frames,
        "workflow_export_bound": float(save["fps"]) == expected_fps
        and save["filename_prefix"] == "wave64_animatediff_fallback_seed6401901",
        "workflow_checkpoint_bound": checkpoint_node["ckpt_name"] == assets["checkpoint"]["file_name"],
        "workflow_motion_model_bound": motion_node["model_name"]
        == assets["animatediff_motion_model"]["file_name"],
        "checkpoint_hash_bound": sha256(paths["checkpoint"]) == assets["checkpoint"]["sha256"],
        "motion_model_size_bound": paths["motion_model"].stat().st_size
        == int(assets["animatediff_motion_model"]["size_bytes"]),
        "motion_model_hash_bound": sha256(paths["motion_model"])
        == assets["animatediff_motion_model"]["sha256"],
        "custom_node_commit_bound": git_commit(paths["custom_node_dir"])
        == requirements["custom_node"]["commit"],
        "artifact_is_animated_webp": format_name == "WEBP" and animated,
        "frame_count_exact": len(decoded_frames) == expected_frames,
        "dimensions_exact_all_frames": all(
            frame.size == (expected_width, expected_height) for frame in decoded_frames
        ),
        "timing_exact_with_tolerance": timing_pass,
        "nonblank_frames_at_least_7_of_8": nonblank_count >= max(1, expected_frames - 1),
        "nonstatic_motion_pair_count": moving_pair_count >= 3,
        "nonstatic_motion_mean_mad": mean_pair_mad >= 1.0,
        "nonstatic_motion_changed_pixel_ratio": max_changed_ratio >= 0.005,
    }
    failed = [name for name, passed in checks.items() if not passed]
    technical_pass = not failed
    evidence = {
        "schema_name": "wave64_animatediff_webp_technical_evidence",
        "schema_version": "1.0",
        "evaluator_version": EVALUATOR_VERSION,
        "timestamp": evidence_timestamp,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "lane_id": LANE_ID,
        "source_bindings": {
            "workflow": {"path": rel(paths["workflow"]), "sha256": sha256(paths["workflow"])},
            "runtime_requirements": {
                "path": rel(paths["requirements"]),
                "sha256": sha256(paths["requirements"]),
            },
            "runtime_evidence": {
                "path": rel(paths["runtime_evidence"]),
                "sha256": sha256(paths["runtime_evidence"]),
                "prompt_id": runtime.get("prompt_id"),
            },
            "artifact": {
                "path": rel(paths["artifact"]),
                "sha256": artifact_hash,
                "size_bytes": paths["artifact"].stat().st_size,
            },
        },
        "decoded_sequence": {
            "format": format_name,
            "is_animated": animated,
            "frame_count": len(decoded_frames),
            "width": decoded_frames[0].width,
            "height": decoded_frames[0].height,
            "durations_ms": durations,
            "total_duration_ms": sum(durations),
            "expected_frame_duration_ms": expected_duration_ms,
        },
        "frame_metrics": metrics,
        "pair_metrics": pairs,
        "summary_metrics": {
            "nonblank_frame_count": nonblank_count,
            "moving_pair_count_mad_gte_1_5": moving_pair_count,
            "mean_adjacent_pair_mad": mean_pair_mad,
            "max_changed_pixel_ratio_delta_gt_5": max_changed_ratio,
        },
        "outputs": {
            "frames_dir": rel(paths["frames_dir"]),
            "contact_sheet": {
                "path": rel(paths["contact_sheet"]),
                "sha256": sha256(paths["contact_sheet"]),
            },
            "wave27_frame_records": {
                "path": rel(paths["frame_records_out"]),
                "sha256": sha256(paths["frame_records_out"]),
            },
        },
        "checks": checks,
        "failed_checks": failed,
        "technical_pass": technical_pass,
        "result": (
            "pass_local_animatediff_fallback_technical_smoke"
            if technical_pass
            else "fail_local_animatediff_fallback_technical_smoke"
        ),
        "boundaries": {
            "visual_quality_reviewed": False,
            "strict_temporal_qa_claimed": False,
            "production_video_lane_certification_claimed": False,
            "target_runtime_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
            "wave71_activation_claimed": False,
        },
        "next_action": "Compile the extracted frame records with the existing Wave27 manifest compiler, then perform direct contact-sheet and animated-artifact visual review.",
    }
    write_json(paths["out"], evidence)
    print(json.dumps(evidence, indent=2))
    return 0 if technical_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
