#!/usr/bin/env python3
"""Deterministically evaluate hash-bound video artifact technical quality."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "mean": None, "max": None, "p95": None}
    data = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(data)),
        "mean": float(np.mean(data)),
        "max": float(np.max(data)),
        "p95": float(np.percentile(data, 95)),
    }


def _border_pixels(frame: np.ndarray, border: int) -> np.ndarray:
    top = frame[:border, :, :].reshape(-1, 3)
    bottom = frame[-border:, :, :].reshape(-1, 3)
    left = frame[border:-border, :border, :].reshape(-1, 3)
    right = frame[border:-border, -border:, :].reshape(-1, 3)
    return np.concatenate((top, bottom, left, right), axis=0)


def evaluate_video(
    video_path: Path,
    *,
    expected_sha256: str | None = None,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_frame_count: int | None = None,
    expected_fps: float | None = None,
    fps_tolerance: float = 0.05,
    black_luma_threshold: float = 8.0,
    freeze_mae_threshold: float = 0.0005,
    max_freeze_run_frames: int = 2,
    max_luminance_span: float = 12.0,
    max_border_mae: float = 0.05,
) -> dict[str, Any]:
    path = video_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video artifact not found: {path}")

    artifact_hash = sha256_file(path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video artifact: {path}")

    reported_width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
    reported_height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    reported_frame_count = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    reported_fps = float(capture.get(cv2.CAP_PROP_FPS))
    fourcc_int = int(capture.get(cv2.CAP_PROP_FOURCC))
    fourcc = "".join(chr((fourcc_int >> (8 * index)) & 0xFF) for index in range(4)).rstrip("\x00")

    decoded_frame_hashes: list[str] = []
    adjacent_mae: list[float] = []
    border_adjacent_mae: list[float] = []
    luminance_means: list[float] = []
    luminance_stds: list[float] = []
    gradient_sharpness: list[float] = []
    black_frame_indexes: list[int] = []
    freeze_transition_indexes: list[int] = []
    freeze_runs: list[int] = []
    current_freeze_run = 0
    first_frame: np.ndarray | None = None
    previous_frame: np.ndarray | None = None
    last_frame: np.ndarray | None = None
    decoded_width = 0
    decoded_height = 0

    try:
        frame_index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame is None or frame.size == 0:
                raise ValueError(f"Decoded empty frame at index {frame_index}")
            if frame.ndim != 3 or frame.shape[2] != 3:
                raise ValueError(f"Unexpected decoded frame shape at index {frame_index}: {frame.shape}")

            decoded_height, decoded_width = frame.shape[:2]
            if first_frame is None:
                first_frame = frame.copy()
            last_frame = frame.copy()
            decoded_frame_hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            luma_mean = float(np.mean(gray))
            luminance_means.append(luma_mean)
            luminance_stds.append(float(np.std(gray)))
            gradient_sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            if luma_mean <= black_luma_threshold:
                black_frame_indexes.append(frame_index)

            if previous_frame is not None:
                mae = float(np.mean(np.abs(frame.astype(np.float32) - previous_frame.astype(np.float32))) / 255.0)
                adjacent_mae.append(mae)
                border = max(1, int(round(min(decoded_width, decoded_height) * 0.05)))
                current_border = _border_pixels(frame.astype(np.float32), border)
                previous_border = _border_pixels(previous_frame.astype(np.float32), border)
                border_adjacent_mae.append(float(np.mean(np.abs(current_border - previous_border)) / 255.0))
                if mae <= freeze_mae_threshold:
                    freeze_transition_indexes.append(frame_index)
                    current_freeze_run += 1
                else:
                    if current_freeze_run:
                        freeze_runs.append(current_freeze_run)
                    current_freeze_run = 0

            previous_frame = frame.copy()
            frame_index += 1
    finally:
        capture.release()

    if current_freeze_run:
        freeze_runs.append(current_freeze_run)

    decoded_frame_count = len(decoded_frame_hashes)
    unique_frame_count = len(set(decoded_frame_hashes))
    first_last_mae = None
    if first_frame is not None and last_frame is not None:
        first_last_mae = float(np.mean(np.abs(first_frame.astype(np.float32) - last_frame.astype(np.float32))) / 255.0)
    luminance_span = (max(luminance_means) - min(luminance_means)) if luminance_means else math.inf
    max_freeze_run = max(freeze_runs, default=0)

    checks = {
        "artifact_sha256_matches": expected_sha256 is None or artifact_hash == expected_sha256.lower(),
        "decode_produced_frames": decoded_frame_count > 0,
        "decoded_dimensions_consistent": decoded_width == reported_width and decoded_height == reported_height,
        "width_exact": expected_width is None or decoded_width == expected_width,
        "height_exact": expected_height is None or decoded_height == expected_height,
        "frame_count_exact": expected_frame_count is None or decoded_frame_count == expected_frame_count,
        "reported_frame_count_matches_decode": reported_frame_count in (0, decoded_frame_count),
        "fps_exact_within_tolerance": expected_fps is None or abs(reported_fps - expected_fps) <= fps_tolerance,
        "all_frames_unique": unique_frame_count == decoded_frame_count,
        "no_black_frames": len(black_frame_indexes) == 0,
        "freeze_run_within_limit": max_freeze_run <= max_freeze_run_frames,
        "luminance_span_within_limit": luminance_span <= max_luminance_span,
        "border_motion_within_limit": not border_adjacent_mae or max(border_adjacent_mae) <= max_border_mae,
        "terminal_frame_decoded": last_frame is not None,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]

    return {
        "schema_version": "1.0",
        "artifact_type": "video_artifact_technical_qa",
        "artifact": {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": artifact_hash,
        },
        "decoder": {
            "tool": "opencv-python",
            "version": cv2.__version__,
            "fourcc": fourcc,
            "reported_width": reported_width,
            "reported_height": reported_height,
            "reported_frame_count": reported_frame_count,
            "reported_fps": reported_fps,
            "decoded_width": decoded_width,
            "decoded_height": decoded_height,
            "decoded_frame_count": decoded_frame_count,
            "unique_decoded_frame_count": unique_frame_count,
            "duration_seconds": (decoded_frame_count / reported_fps) if reported_fps > 0 else None,
        },
        "thresholds": {
            "fps_tolerance": fps_tolerance,
            "black_luma_threshold": black_luma_threshold,
            "freeze_mae_threshold": freeze_mae_threshold,
            "max_freeze_run_frames": max_freeze_run_frames,
            "max_luminance_span": max_luminance_span,
            "max_border_mae": max_border_mae,
        },
        "temporal_detectors": {
            "black_frame_indexes": black_frame_indexes,
            "freeze_transition_indexes": freeze_transition_indexes,
            "freeze_run_lengths": freeze_runs,
            "max_freeze_run_frames": max_freeze_run,
        },
        "frame_metrics": {
            "adjacent_rgb_mae_normalized": _stats(adjacent_mae),
            "border_adjacent_rgb_mae_normalized": _stats(border_adjacent_mae),
            "first_last_rgb_mae_normalized": first_last_mae,
            "luminance_mean_0_255": _stats(luminance_means),
            "luminance_std_0_255": _stats(luminance_stds),
            "luminance_mean_span_0_255": float(luminance_span),
            "gradient_sharpness_variance": _stats(gradient_sharpness),
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "technical_pass": not failed_checks,
        "result": "pass_bounded_video_technical_qa" if not failed_checks else "fail_bounded_video_technical_qa",
        "boundaries": {
            "visual_quality_reviewed_here": False,
            "identity_or_anatomy_certified_here": False,
            "production_video_lane_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
        },
        "next_action": "Perform direct temporal visual review of the exact hash-bound artifact before any robustness claim.",
    }


def write_json_atomic(payload: dict[str, Any], out_path: Path) -> None:
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{out_path.name}.", suffix=".tmp", dir=out_path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=False)
            stream.write("\n")
        os.replace(temp_name, out_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-width", type=int)
    parser.add_argument("--expected-height", type=int)
    parser.add_argument("--expected-frame-count", type=int)
    parser.add_argument("--expected-fps", type=float)
    parser.add_argument("--fps-tolerance", type=float, default=0.05)
    parser.add_argument("--black-luma-threshold", type=float, default=8.0)
    parser.add_argument("--freeze-mae-threshold", type=float, default=0.0005)
    parser.add_argument("--max-freeze-run-frames", type=int, default=2)
    parser.add_argument("--max-luminance-span", type=float, default=12.0)
    parser.add_argument("--max-border-mae", type=float, default=0.05)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.video.resolve() == args.out.resolve():
        raise ValueError("Output path must differ from the video artifact path.")
    payload = evaluate_video(
        args.video,
        expected_sha256=args.expected_sha256,
        expected_width=args.expected_width,
        expected_height=args.expected_height,
        expected_frame_count=args.expected_frame_count,
        expected_fps=args.expected_fps,
        fps_tolerance=args.fps_tolerance,
        black_luma_threshold=args.black_luma_threshold,
        freeze_mae_threshold=args.freeze_mae_threshold,
        max_freeze_run_frames=args.max_freeze_run_frames,
        max_luminance_span=args.max_luminance_span,
        max_border_mae=args.max_border_mae,
    )
    write_json_atomic(payload, args.out)
    print(json.dumps(payload, indent=2))
    return 0 if payload["technical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
