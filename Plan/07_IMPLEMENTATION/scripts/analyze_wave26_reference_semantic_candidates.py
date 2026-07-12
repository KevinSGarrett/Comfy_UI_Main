#!/usr/bin/env python3
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
import jsonschema
import numpy as np

DEFAULT_THRESHOLDS = "Plan/10_REGISTRIES/wave26_reference_semantic_candidate_thresholds.json"
OUTPUT_SCHEMA = "Plan/08_SCHEMAS/wave26_reference_semantic_candidates.schema.json"
INGEST_SCHEMA = "Plan/08_SCHEMAS/wave26_reference_video_ingest_evidence.schema.json"
REFERENCE_MANIFEST_SCHEMA = "Plan/08_SCHEMAS/reference_video_manifest.schema.json"
FRAME_MANIFEST_SCHEMA = "Plan/08_SCHEMAS/reference_video_frame_manifest.schema.json"
INGEST_EVIDENCE = "wave26_reference_video_ingest_evidence.json"


def _reject_nonfinite(token: str) -> Any:
    raise ValueError(f"non-finite JSON token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite)


def _parse_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_nonfinite)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _root(value: str) -> Path:
    path = Path(value).resolve()
    if (path / "Plan").is_dir():
        return path
    if path.name == "Plan" and (path / "08_SCHEMAS").is_dir():
        return path.parent
    raise ValueError(f"unable to resolve repository root from {value}")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _validate(instance: Any, schema_path: Path) -> None:
    validator = jsonschema.Draft202012Validator(_load_json(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "root"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def _finite_number(src: dict[str, Any], key: str, low: float, high: float) -> float:
    value = src.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"threshold {key} must be finite numeric")
    result = float(value)
    if result < low or result > high:
        raise ValueError(f"threshold {key} outside [{low}, {high}]")
    return result


def _thresholds(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    digest = _sha256_bytes(raw)
    data = _parse_json_bytes(raw, "threshold registry")
    expected = {
        "schema_name", "version", "algorithm", "rounding_digits", "minimum_frame_count",
        "motion_peak", "shot_boundary", "loop_candidate",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("threshold registry fields mismatch")
    if data.get("schema_name") != "wave26_reference_semantic_candidate_thresholds" or data.get("version") != 1:
        raise ValueError("unsupported threshold registry")
    if data.get("algorithm") != "opencv_farneback_histogram_luma_v1" or data.get("minimum_frame_count") != 3:
        raise ValueError("unsupported threshold algorithm or minimum frame count")
    digits = data.get("rounding_digits")
    if not isinstance(digits, int) or isinstance(digits, bool) or not 0 <= digits <= 12:
        raise ValueError("rounding_digits must be integer in [0, 12]")
    motion, shot, loop = data.get("motion_peak"), data.get("shot_boundary"), data.get("loop_candidate")
    if not all(isinstance(group, dict) for group in (motion, shot, loop)):
        raise ValueError("threshold groups must be objects")
    _finite_number(motion, "minimum_flow_p95_diagonal_ratio", 0, 10)
    _finite_number(motion, "direction_change_degrees", 0, 180)
    _finite_number(motion, "direction_vector_floor_diagonal_ratio", 0, 10)
    _finite_number(shot, "minimum_luma_mae_percent", 0, 100)
    _finite_number(shot, "minimum_histogram_bhattacharyya", 0, 1)
    _finite_number(loop, "minimum_span_seconds", 0, 3600)
    if loop.get("endpoint_luma_basis") != "32x32_area_downsampled_grayscale":
        raise ValueError("unsupported loop endpoint luma basis")
    _finite_number(loop, "maximum_endpoint_descriptor_luma_mae_percent", 0, 100)
    _finite_number(loop, "maximum_endpoint_histogram_bhattacharyya", 0, 1)
    maximum = loop.get("maximum_candidates")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 100:
        raise ValueError("maximum_candidates must be integer in [1, 100]")
    return data, digest


def _bound_bytes(base: Path, relative: str, expected_hash: str, expected_bytes: int) -> tuple[Path, bytes]:
    path = (base / relative).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes ingest directory: {relative}") from exc
    if not path.is_file():
        raise ValueError(f"artifact binding failed: {relative}")
    raw = path.read_bytes()
    if len(raw) != expected_bytes or _sha256_bytes(raw) != expected_hash:
        raise ValueError(f"artifact binding failed: {relative}")
    return path, raw


def _load_source(ingest_dir: Path, root: Path) -> tuple[dict[str, Any], dict[str, str], Path, Path, list[dict[str, Any]], list[np.ndarray]]:
    evidence_path = ingest_dir / INGEST_EVIDENCE
    if not evidence_path.is_file():
        raise ValueError("ingest evidence is missing")
    evidence_raw = evidence_path.read_bytes()
    evidence = _parse_json_bytes(evidence_raw, "ingest evidence")
    _validate(evidence, root / INGEST_SCHEMA)
    if not isinstance(evidence, dict) or evidence.get("status") != "success":
        raise ValueError("ingest evidence is not successful")
    ingest = evidence.get("ingest")
    artifacts = evidence.get("artifacts")
    if not isinstance(ingest, dict) or not isinstance(artifacts, dict):
        raise ValueError("ingest evidence sections are malformed")
    if ingest.get("extraction_profile_id") != "all_frames_short_clip" or ingest.get("sample_stride") != 1:
        raise ValueError("semantic candidates require all_frames_short_clip with stride 1")
    frame_count = ingest.get("frames_extracted")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count < 3 or frame_count != ingest.get("decoded_frame_count"):
        raise ValueError("semantic candidates require at least 3 fully extracted frames")
    manifest_path, manifest_raw = _bound_bytes(ingest_dir, artifacts["manifest_path"], artifacts["manifest_sha256"], artifacts["manifest_bytes"])
    frame_manifest_path, frame_manifest_raw = _bound_bytes(ingest_dir, artifacts["frame_manifest_path"], artifacts["frame_manifest_sha256"], artifacts["frame_manifest_bytes"])
    manifest = _parse_json_bytes(manifest_raw, "reference manifest")
    _validate(manifest, root / REFERENCE_MANIFEST_SCHEMA)
    if manifest.get("source_video_id") != ingest.get("source_video_id") or manifest.get("extraction_profile_id") != "all_frames_short_clip":
        raise ValueError("reference manifest does not match ingest evidence")
    lines = frame_manifest_raw.decode("utf-8").splitlines()
    if len(lines) != frame_count:
        raise ValueError("frame manifest count mismatch")
    records = [json.loads(line, parse_constant=_reject_nonfinite) for line in lines]
    for record in records:
        _validate(record, root / FRAME_MANIFEST_SCHEMA)
    if [record.get("frame_index") for record in records] != list(range(frame_count)):
        raise ValueError("frame manifest must be contiguous and ordered from zero")
    frames_dir = (ingest_dir / artifacts["frames_dir"]).resolve()
    try:
        frames_dir.relative_to(ingest_dir.resolve())
    except ValueError as exc:
        raise ValueError("frames directory escapes ingest directory") from exc
    images: list[np.ndarray] = []
    source_id = ingest["source_video_id"]
    width, height = ingest["width"], ingest["height"]
    for record in records:
        if record.get("source_video_id") != source_id or record.get("qa_status") != "decoded_png_hash_verified":
            raise ValueError("frame record source or QA binding failed")
        path = (ingest_dir / str(record.get("frame_path_or_asset_id"))).resolve()
        try:
            path.relative_to(frames_dir)
        except ValueError as exc:
            raise ValueError("frame path escapes declared frames directory") from exc
        digest = record.get("png_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or not path.is_file():
            raise ValueError(f"frame PNG binding failed: {record.get('frame_index')}")
        frame_raw = path.read_bytes()
        if _sha256_bytes(frame_raw) != digest:
            raise ValueError(f"frame PNG binding failed: {record.get('frame_index')}")
        image = cv2.imdecode(np.frombuffer(frame_raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (height, width):
            raise ValueError(f"frame decode or dimension binding failed: {record.get('frame_index')}")
        images.append(image)
    bindings = {
        "ingest_evidence": _sha256_bytes(evidence_raw),
        "reference_manifest": _sha256_bytes(manifest_raw),
        "frame_manifest": _sha256_bytes(frame_manifest_raw),
    }
    return evidence, bindings, manifest_path, frame_manifest_path, records, images


def _rounded(value: float, digits: int) -> float:
    if not math.isfinite(float(value)):
        raise ValueError("analysis produced non-finite metric")
    return round(float(value), digits)


def _gray_hist(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    histogram = cv2.calcHist([gray], [0], None, [64], [0, 256])
    cv2.normalize(histogram, histogram, 1.0, 0.0, cv2.NORM_L1)
    descriptor = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    return gray, histogram, descriptor


def _angle(previous: tuple[float, float] | None, current: tuple[float, float], floor: float) -> float | None:
    if previous is None:
        return None
    p_mag, c_mag = math.hypot(*previous), math.hypot(*current)
    if p_mag < floor or c_mag < floor:
        return None
    cosine = max(-1.0, min(1.0, (previous[0] * current[0] + previous[1] * current[1]) / (p_mag * c_mag)))
    return math.degrees(math.acos(cosine))


def _analyze(records: list[dict[str, Any]], images: list[np.ndarray], thresholds: dict[str, Any]) -> tuple[list[dict[str, Any]], list[np.ndarray], list[np.ndarray]]:
    digits = int(thresholds["rounding_digits"])
    diagonal = math.hypot(images[0].shape[1], images[0].shape[0])
    floor = float(thresholds["motion_peak"]["direction_vector_floor_diagonal_ratio"])
    prepared = [_gray_hist(image) for image in images]
    metrics: list[dict[str, Any]] = []
    previous_vector: tuple[float, float] | None = None
    for index in range(1, len(images)):
        prev_gray, prev_hist, _ = prepared[index - 1]
        curr_gray, curr_hist, _ = prepared[index]
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        vector = (float(np.mean(flow[..., 0])) / diagonal, float(np.mean(flow[..., 1])) / diagonal)
        direction = _angle(previous_vector, vector, floor)
        metrics.append({
            "from_frame": index - 1, "to_frame": index,
            "timestamp_seconds": _rounded(float(records[index]["timestamp_seconds"]), digits),
            "luma_mae_percent": _rounded(float(np.mean(np.abs(curr_gray.astype(np.float32) - prev_gray.astype(np.float32))) / 255.0 * 100.0), digits),
            "histogram_bhattacharyya": _rounded(float(cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_BHATTACHARYYA)), digits),
            "flow_p95_diagonal_ratio": _rounded(float(np.percentile(magnitude, 95)) / diagonal, digits),
            "flow_mean_x_diagonal_ratio": _rounded(vector[0], digits),
            "flow_mean_y_diagonal_ratio": _rounded(vector[1], digits),
            "direction_change_degrees": None if direction is None else _rounded(direction, digits),
            "finite": True,
        })
        previous_vector = vector
    return metrics, [item[1] for item in prepared], [item[2] for item in prepared]


def _candidates(records: list[dict[str, Any]], metrics: list[dict[str, Any]], histograms: list[np.ndarray], descriptors: list[np.ndarray], thresholds: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    motion_t, shot_t, loop_t = thresholds["motion_peak"], thresholds["shot_boundary"], thresholds["loop_candidate"]
    digits = int(thresholds["rounding_digits"])
    motion: list[dict[str, Any]] = []
    for index, item in enumerate(metrics):
        score = item["flow_p95_diagonal_ratio"]
        previous = metrics[index - 1]["flow_p95_diagonal_ratio"] if index > 0 else -1.0
        following = metrics[index + 1]["flow_p95_diagonal_ratio"] if index + 1 < len(metrics) else -1.0
        peak = score >= motion_t["minimum_flow_p95_diagonal_ratio"] and score >= previous and score > following
        change = item["direction_change_degrees"] is not None and item["direction_change_degrees"] >= motion_t["direction_change_degrees"]
        if peak or change:
            reason = "local_motion_peak_and_direction_change" if peak and change else ("local_motion_peak" if peak else "direction_change")
            motion.append({"frame_index": item["to_frame"], "timestamp_seconds": item["timestamp_seconds"], "reason": reason, "flow_p95_diagonal_ratio": score, "direction_change_degrees": item["direction_change_degrees"]})
    shots: list[dict[str, Any]] = []
    for item in metrics:
        luma = item["luma_mae_percent"] >= shot_t["minimum_luma_mae_percent"]
        histogram = item["histogram_bhattacharyya"] >= shot_t["minimum_histogram_bhattacharyya"]
        if luma or histogram:
            reason = "luma_and_histogram_threshold" if luma and histogram else ("luma_threshold" if luma else "histogram_threshold")
            shots.append({"frame_index": item["to_frame"], "timestamp_seconds": item["timestamp_seconds"], "luma_mae_percent": item["luma_mae_percent"], "histogram_bhattacharyya": item["histogram_bhattacharyya"], "reason": reason})
    loops: list[dict[str, Any]] = []
    for start in range(len(records) - 1):
        for end in range(start + 1, len(records)):
            span = float(records[end]["timestamp_seconds"]) - float(records[start]["timestamp_seconds"])
            if span < loop_t["minimum_span_seconds"]:
                continue
            luma = float(np.mean(np.abs(descriptors[end] - descriptors[start])) / 255.0 * 100.0)
            histogram = float(cv2.compareHist(histograms[start], histograms[end], cv2.HISTCMP_BHATTACHARYYA))
            if luma <= loop_t["maximum_endpoint_descriptor_luma_mae_percent"] and histogram <= loop_t["maximum_endpoint_histogram_bhattacharyya"]:
                luma_norm = luma / max(float(loop_t["maximum_endpoint_descriptor_luma_mae_percent"]), 1e-12)
                hist_norm = histogram / max(float(loop_t["maximum_endpoint_histogram_bhattacharyya"]), 1e-12)
                closure = max(0.0, 1.0 - (luma_norm + hist_norm) / 2.0)
                loops.append({"start_frame": start, "end_frame": end, "start_seconds": _rounded(float(records[start]["timestamp_seconds"]), digits), "end_seconds": _rounded(float(records[end]["timestamp_seconds"]), digits), "span_seconds": _rounded(span, digits), "endpoint_descriptor_luma_mae_percent": _rounded(luma, digits), "endpoint_histogram_bhattacharyya": _rounded(histogram, digits), "closure_score": _rounded(closure, digits)})
    loops.sort(key=lambda item: (-item["closure_score"], -item["span_seconds"], item["start_frame"], item["end_frame"]))
    return motion, shots, loops[: int(loop_t["maximum_candidates"])]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--thresholds")
    args = parser.parse_args()
    temp_path: Path | None = None
    try:
        cv2.setNumThreads(1)
        cv2.setRNGSeed(0)
        root = _root(args.root)
        ingest_dir, output = Path(args.ingest_dir).resolve(), Path(args.output).resolve()
        if output.exists():
            raise ValueError("output path already exists")
        threshold_path = Path(args.thresholds).resolve() if args.thresholds else root / DEFAULT_THRESHOLDS
        thresholds, threshold_sha = _thresholds(threshold_path)
        evidence, source_hashes, manifest_path, frame_manifest_path, records, images = _load_source(ingest_dir, root)
        metrics, histograms, descriptors = _analyze(records, images, thresholds)
        motion, shots, loops = _candidates(records, metrics, histograms, descriptors, thresholds)
        payload = {
            "schema_name": "wave26_reference_semantic_candidates", "version": 1,
            "source_video_id": evidence["ingest"]["source_video_id"],
            "source_bindings": {
                "ingest_evidence": {"path": _relative(ingest_dir / INGEST_EVIDENCE, root), "sha256": source_hashes["ingest_evidence"]},
                "reference_manifest": {"path": _relative(manifest_path, root), "sha256": source_hashes["reference_manifest"]},
                "frame_manifest": {"path": _relative(frame_manifest_path, root), "sha256": source_hashes["frame_manifest"]},
            },
            "threshold_registry": {"path": _relative(threshold_path, root), "sha256": threshold_sha, "version": thresholds["version"]},
            "analyzer": {"algorithm": thresholds["algorithm"], "opencv_version": cv2.__version__, "thread_count": 1, "rng_seed": 0, "rounding_digits": thresholds["rounding_digits"], "candidate_scope": "non_authoritative_candidate_generation_only"},
            "frame_count": len(records), "fps": evidence["ingest"]["fps"],
            "image_dimensions": {"width": evidence["ingest"]["width"], "height": evidence["ingest"]["height"]},
            "adjacency_metrics": metrics, "motion_peak_candidates": motion, "shot_boundary_candidates": shots, "loop_candidates": loops,
            "claims": {"motion_peak_sampling_ready": True, "shot_boundary_sampling_ready": True, "loop_candidate_sampling_ready": True, "contact_phase_sampling_ready": False, "pose_timeline_generated": False, "depth_timeline_generated": False, "mask_timeline_generated": False, "contact_timeline_generated": False, "shot_matching_performed": False, "loop_export_ready": False, "source_reference_visual_review": False, "production_proof_complete": False, "final_promotion_ready": False},
        }
        _validate(payload, root / OUTPUT_SCHEMA)
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        os.close(fd)
        temp_path = Path(temporary)
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        temp_path.replace(output)
        temp_path = None
        print(json.dumps({"status": "pass", "output": str(output), "motion_peak_candidates": len(motion), "shot_boundary_candidates": len(shots), "loop_candidates": len(loops)}, sort_keys=True))
        return 0
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
