#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any
from PIL import Image, ImageSequence, UnidentifiedImageError

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
GIF_HEADERS = {b"GIF87a", b"GIF89a"}
BLOCKED_EXIT_CODE = 2
INVALID_EXIT_CODE = 1
MIN_GIF_FRAME_DURATION_MS = 10
GIF_DURATION_QUANTUM_MS = 10
RUNTIME_PROOF_REQUIRED_KEYS = {
    "runtime_ready",
    "runtime_proof_present",
    "generation_executed",
    "production_proof",
    "generation_scope",
    "comfyui_generation_executed",
    "candidate_gif_sha256",
    "manifest_sha256",
    "temporal_evidence_sha256",
}
VISUAL_REVIEW_REQUIRED_KEYS = {
    "review_method",
    "no_visible_pop_passed",
    "intentional_cadence_passed",
    "identity_preservation_passed",
    "background_continuity_passed",
    "contact_deformation_continuity",
    "candidate_gif_sha256",
    "manifest_sha256",
    "temporal_evidence_sha256",
}
ATTESTATION_ALLOWED_KEYS = {
    "synthetic_input",
    "runtime_proof_path",
    "runtime_proof_sha256",
    "visual_review_path",
    "visual_review_sha256",
}


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)


def _sha256_of_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_of_json_payload(payload: Any) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_repo_root(root_arg: str | None) -> Path:
    if root_arg:
        candidate = Path(root_arg).resolve()
    else:
        candidate = Path(__file__).resolve().parents[3]
    if not (candidate / "Plan").is_dir():
        raise ValueError(f"unable to resolve repository root from: {candidate}")
    return candidate


def _compute_manifest_sequence_sha256(frames: list[dict[str, Any]]) -> str:
    payload = []
    for frame in frames:
        payload.append(
            {
                "frame_index": frame["frame_index"],
                "time_seconds": float(frame["time_seconds"]),
                "artifact_path": frame["artifact_path"],
                "artifact_sha256": frame["artifact_sha256"],
                "artifact_bytes": frame["artifact_bytes"],
            }
        )
    return _sha256_of_json_payload(payload)


def _quantize_gif_durations(durations: list[int]) -> list[int]:
    """Mirror exporter centisecond quantization for exact decoded timing parity."""
    quantized: list[int] = []
    source_cumulative = 0
    encoded_cumulative = 0
    for duration in durations:
        source_cumulative += duration
        target_cumulative = (
            (source_cumulative + (GIF_DURATION_QUANTUM_MS // 2)) // GIF_DURATION_QUANTUM_MS
        ) * GIF_DURATION_QUANTUM_MS
        encoded_duration = target_cumulative - encoded_cumulative
        if encoded_duration < MIN_GIF_FRAME_DURATION_MS:
            encoded_duration = MIN_GIF_FRAME_DURATION_MS
            target_cumulative = encoded_cumulative + encoded_duration
        quantized.append(encoded_duration)
        encoded_cumulative = target_cumulative
    return quantized


def _parse_png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"artifact is not a supported PNG source frame: {path}")
    if data[12:16] != b"IHDR":
        raise ValueError(f"artifact has malformed PNG header: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise ValueError(f"artifact has invalid PNG dimensions: {path}")
    return width, height


def _normalize_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    if manifest.get("schema_name") != "wave27_frame_manifest":
        raise ValueError("manifest.schema_name must be wave27_frame_manifest")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("manifest.frames must be a non-empty array")
    frame_count = manifest.get("frame_count")
    if frame_count != len(frames):
        raise ValueError("manifest.frame_count must equal len(manifest.frames)")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
        raise ValueError("manifest.frame_count must be a positive integer")
    ordered = sorted(frames, key=lambda item: item["frame_index"])
    expected_indexes = list(range(0, len(ordered)))
    observed_indexes = [item.get("frame_index") for item in ordered]
    if observed_indexes != expected_indexes:
        raise ValueError(f"manifest.frame_index sequence is invalid: {observed_indexes}")

    normalized_frames: list[dict[str, Any]] = []
    previous_time: float | None = None
    source_dimensions: tuple[int, int] | None = None
    for idx, frame in enumerate(ordered):
        if not isinstance(frame, dict):
            raise ValueError(f"manifest.frames[{idx}] must be an object")
        time_seconds_raw = frame.get("time_seconds")
        if not isinstance(time_seconds_raw, (int, float)) or isinstance(time_seconds_raw, bool):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be numeric")
        time_seconds = float(time_seconds_raw)
        if not math.isfinite(time_seconds):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be finite")
        if previous_time is not None and time_seconds <= previous_time:
            raise ValueError("manifest frame times must be strictly increasing")
        previous_time = time_seconds

        artifact_path_raw = frame.get("artifact_path")
        if not isinstance(artifact_path_raw, str) or not artifact_path_raw.strip():
            raise ValueError(f"manifest.frames[{idx}].artifact_path must be non-empty string")
        artifact_path = Path(artifact_path_raw)
        if not artifact_path.is_absolute():
            artifact_path = (manifest_path.parent / artifact_path).resolve()
        if not artifact_path.is_file():
            raise ValueError(f"manifest source artifact missing: {artifact_path}")
        observed_sha = _sha256_of_path(artifact_path)
        observed_bytes = artifact_path.stat().st_size
        declared_sha = frame.get("artifact_sha256")
        if not isinstance(declared_sha, str) or SHA256_RE.fullmatch(declared_sha) is None:
            raise ValueError(f"manifest.frames[{idx}].artifact_sha256 must be lowercase SHA256")
        declared_bytes = frame.get("artifact_bytes")
        if (
            not isinstance(declared_bytes, int)
            or isinstance(declared_bytes, bool)
            or declared_bytes <= 0
        ):
            raise ValueError(f"manifest.frames[{idx}].artifact_bytes must be positive integer")
        if observed_sha != declared_sha:
            raise ValueError(f"manifest.frames[{idx}] artifact_sha256 mismatch")
        if observed_bytes != declared_bytes:
            raise ValueError(f"manifest.frames[{idx}] artifact_bytes mismatch")

        frame_dimensions = _parse_png_dimensions(artifact_path)
        if source_dimensions is None:
            source_dimensions = frame_dimensions
        elif source_dimensions != frame_dimensions:
            raise ValueError("source frame dimensions must be constant across the manifest")

        normalized_frames.append(
            {
                "frame_index": frame["frame_index"],
                "time_seconds": time_seconds,
                "artifact_path": frame["artifact_path"],
                "artifact_sha256": observed_sha,
                "artifact_bytes": observed_bytes,
            }
        )

    expected_sequence = _compute_manifest_sequence_sha256(normalized_frames)
    actual_sequence = manifest.get("sequence_sha256")
    if actual_sequence != expected_sequence:
        raise ValueError("manifest.sequence_sha256 mismatch")
    if source_dimensions is None:
        raise ValueError("unable to infer source dimensions from manifest artifacts")

    expected_durations_ms: list[int] = []
    for idx in range(0, len(normalized_frames) - 1):
        delta = normalized_frames[idx + 1]["time_seconds"] - normalized_frames[idx]["time_seconds"]
        duration_ms = int(round(delta * 1000.0))
        if duration_ms < MIN_GIF_FRAME_DURATION_MS:
            raise ValueError(
                f"manifest frame timing delta must be at least {MIN_GIF_FRAME_DURATION_MS}ms"
            )
        expected_durations_ms.append(duration_ms)
    if len(normalized_frames) == 1:
        expected_durations_ms = [100]
    else:
        expected_durations_ms.append(expected_durations_ms[0])
    expected_durations_ms = _quantize_gif_durations(expected_durations_ms)

    return {
        "frame_count": len(normalized_frames),
        "sequence_sha256": expected_sequence,
        "source_dimensions": source_dimensions,
        "expected_durations_ms": expected_durations_ms,
    }


def _validate_temporal_evidence(evidence: dict[str, Any], expected_frame_count: int) -> str:
    if evidence.get("schema_name") != "wave27_temporal_evidence":
        raise ValueError("temporal evidence schema_name must be wave27_temporal_evidence")
    frame_count = evidence.get("frame_count")
    if frame_count != expected_frame_count:
        raise ValueError("temporal evidence frame_count must match manifest frame_count")
    loop_profile = evidence.get("loop_profile")
    if not isinstance(loop_profile, str) or not loop_profile.strip():
        raise ValueError("temporal evidence loop_profile must be a non-empty string")
    return loop_profile.strip()


def _parse_gif_candidate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"candidate GIF does not exist: {path}")
    raw_data = path.read_bytes()
    if len(raw_data) < 14:
        raise ValueError("candidate GIF is too small")
    header = raw_data[:6]
    if header not in GIF_HEADERS:
        raise ValueError("candidate file is not a GIF87a or GIF89a container")

    # Structural preflight remains strict for malformed/truncated/LZW-invalid blocks;
    # decoder verification below still performs full Pillow frame decode.
    offset = 6
    width = int.from_bytes(raw_data[offset : offset + 2], "little")
    height = int.from_bytes(raw_data[offset + 2 : offset + 4], "little")
    packed = raw_data[offset + 4]
    offset += 7
    if width <= 0 or height <= 0:
        raise ValueError("candidate GIF dimensions must be positive")
    global_color_table_flag = (packed & 0b10000000) != 0
    global_color_table_size = 3 * (2 ** ((packed & 0b00000111) + 1))
    if global_color_table_flag:
        if offset + global_color_table_size > len(raw_data):
            raise ValueError("candidate GIF global color table is truncated")
        offset += global_color_table_size
    trailer_seen = False
    while offset < len(raw_data):
        sentinel = raw_data[offset]
        offset += 1
        if sentinel == 0x3B:
            trailer_seen = True
            break
        if sentinel == 0x21:
            if offset >= len(raw_data):
                raise ValueError("candidate GIF extension is truncated")
            offset += 1
            while True:
                if offset >= len(raw_data):
                    raise ValueError("candidate GIF extension data is truncated")
                sub_len = raw_data[offset]
                offset += 1
                if sub_len == 0:
                    break
                if offset + sub_len > len(raw_data):
                    raise ValueError("candidate GIF extension sub-block is truncated")
                offset += sub_len
            continue
        if sentinel == 0x2C:
            if offset + 9 > len(raw_data):
                raise ValueError("candidate GIF image descriptor is truncated")
            descriptor_packed = raw_data[offset + 8]
            offset += 9
            local_color_table_flag = (descriptor_packed & 0b10000000) != 0
            local_color_table_size = 3 * (2 ** ((descriptor_packed & 0b00000111) + 1))
            if local_color_table_flag:
                if offset + local_color_table_size > len(raw_data):
                    raise ValueError("candidate GIF local color table is truncated")
                offset += local_color_table_size
            if offset >= len(raw_data):
                raise ValueError("candidate GIF image data is truncated before LZW code size")
            lzw_code_size = raw_data[offset]
            offset += 1
            if lzw_code_size < 2 or lzw_code_size > 11:
                raise ValueError("candidate GIF LZW minimum code size is invalid")
            while True:
                if offset >= len(raw_data):
                    raise ValueError("candidate GIF image data sub-block is truncated")
                sub_len = raw_data[offset]
                offset += 1
                if sub_len == 0:
                    break
                if offset + sub_len > len(raw_data):
                    raise ValueError("candidate GIF image data sub-block exceeds file size")
                offset += sub_len
            continue
        raise ValueError(f"candidate GIF encountered unsupported block sentinel 0x{sentinel:02x}")
    if not trailer_seen:
        raise ValueError("candidate GIF missing trailer terminator")

    frame_hashes: list[str] = []
    frame_buffers: list[bytes] = []
    frame_durations_ms: list[int] = []
    loop_count: int | None = None
    canvas_dimensions: tuple[int, int] | None = None
    try:
        with Image.open(path) as gif:
            if getattr(gif, "format", None) != "GIF":
                raise ValueError("candidate file could not be decoded as GIF")
            loop_value = gif.info.get("loop")
            if not isinstance(loop_value, int) or isinstance(loop_value, bool) or loop_value < 0:
                raise ValueError("candidate GIF missing valid loop metadata")
            loop_count = int(loop_value)
            canvas_dimensions = (int(gif.width), int(gif.height))
            if canvas_dimensions[0] <= 0 or canvas_dimensions[1] <= 0:
                raise ValueError("candidate GIF dimensions must be positive")

            for frame in ImageSequence.Iterator(gif):
                rgba_frame = frame.convert("RGBA")
                rgba_frame.load()
                if rgba_frame.size != canvas_dimensions:
                    raise ValueError("decoded frame dimensions are inconsistent")
                duration_ms_raw = frame.info.get("duration")
                if (
                    not isinstance(duration_ms_raw, int)
                    or isinstance(duration_ms_raw, bool)
                    or duration_ms_raw <= 0
                ):
                    raise ValueError("candidate GIF has zero or missing frame duration")
                frame_durations_ms.append(int(duration_ms_raw))
                frame_bytes = rgba_frame.tobytes()
                frame_buffers.append(frame_bytes)
                frame_hashes.append(hashlib.sha256(frame_bytes).hexdigest())
    except (UnidentifiedImageError, OSError, ValueError):
        raise
    except Exception as exc:  # pragma: no cover - defensive fallback for decoder errors
        raise ValueError(f"candidate GIF decode failed: {exc}") from exc

    if not frame_hashes:
        raise ValueError("candidate GIF contains zero decodable frames")
    if canvas_dimensions is None or loop_count is None:
        raise ValueError("candidate GIF metadata could not be resolved")
    first_rgba = frame_buffers[0]
    last_rgba = frame_buffers[-1]
    if len(first_rgba) != len(last_rgba):
        raise ValueError("decoded seam metric requires equal frame byte lengths")
    channel_abs_sum = sum(abs(a - b) for a, b in zip(first_rgba, last_rgba))
    max_abs_sum = len(first_rgba) * 255
    seam_metric_value = round(channel_abs_sum / float(max_abs_sum), 8)

    return {
        "container_header": header.decode("ascii"),
        "width": canvas_dimensions[0],
        "height": canvas_dimensions[1],
        "decoded_frame_count": len(frame_hashes),
        "decoded_rgba_frame_hashes": frame_hashes,
        "frame_durations_ms": frame_durations_ms,
        "loop_count": loop_count,
        "first_frame_sha256": frame_hashes[0],
        "last_frame_sha256": frame_hashes[-1],
        "seam_metric_name": "first_last_rgba_mean_absolute_difference_normalized",
        "seam_metric_value": seam_metric_value,
    }


def _load_attestation(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("attestation must be a JSON object")
    unknown = sorted(set(payload) - ATTESTATION_ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"attestation has unknown keys: {', '.join(unknown)}")
    synthetic_raw = payload.get("synthetic_input", True)
    if not isinstance(synthetic_raw, bool):
        raise ValueError("attestation.synthetic_input must be boolean")
    for key in (
        "runtime_proof_path",
        "runtime_proof_sha256",
        "visual_review_path",
        "visual_review_sha256",
    ):
        if key in payload and payload[key] is not None and not isinstance(payload[key], str):
            raise ValueError(f"attestation.{key} must be a string when provided")
    for key in ("runtime_proof_sha256", "visual_review_sha256"):
        if key in payload and payload[key] is not None and SHA256_RE.fullmatch(payload[key]) is None:
            raise ValueError(f"attestation.{key} must be lowercase SHA256")
    return payload


def _resolve_proof_path(proof_path_raw: str, attestation_path: Path) -> Path:
    proof_path = Path(proof_path_raw)
    if not proof_path.is_absolute():
        proof_path = (attestation_path.parent / proof_path).resolve()
    if not proof_path.is_file():
        raise ValueError(f"proof artifact missing: {proof_path}")
    return proof_path


def _validate_runtime_proof_payload(
    payload: dict[str, Any], candidate_sha: str, manifest_sha: str, temporal_sha: str
) -> None:
    unknown = sorted(set(payload) - RUNTIME_PROOF_REQUIRED_KEYS)
    if unknown:
        raise ValueError(f"runtime proof has unknown keys: {', '.join(unknown)}")
    missing = sorted(RUNTIME_PROOF_REQUIRED_KEYS - set(payload))
    if missing:
        raise ValueError(f"runtime proof missing keys: {', '.join(missing)}")
    for key in ("runtime_ready", "runtime_proof_present", "generation_executed", "production_proof"):
        if payload.get(key) is not True:
            raise ValueError(f"runtime proof requires {key}=true")
    if payload.get("generation_scope") != "deterministic_gif_export_only":
        raise ValueError(
            "runtime proof generation_scope must be deterministic_gif_export_only"
        )
    if payload.get("comfyui_generation_executed") is not False:
        raise ValueError("runtime proof requires comfyui_generation_executed=false")
    if payload.get("candidate_gif_sha256") != candidate_sha:
        raise ValueError("runtime proof candidate_gif_sha256 binding mismatch")
    if payload.get("manifest_sha256") != manifest_sha:
        raise ValueError("runtime proof manifest_sha256 binding mismatch")
    if payload.get("temporal_evidence_sha256") != temporal_sha:
        raise ValueError("runtime proof temporal_evidence_sha256 binding mismatch")


def _validate_visual_review_payload(
    payload: dict[str, Any], candidate_sha: str, manifest_sha: str, temporal_sha: str
) -> None:
    unknown = sorted(set(payload) - VISUAL_REVIEW_REQUIRED_KEYS)
    if unknown:
        raise ValueError(f"visual review has unknown keys: {', '.join(unknown)}")
    missing = sorted(VISUAL_REVIEW_REQUIRED_KEYS - set(payload))
    if missing:
        raise ValueError(f"visual review missing keys: {', '.join(missing)}")
    if payload.get("review_method") != "loop_playback_review":
        raise ValueError("visual review_method must be loop_playback_review")
    for key in (
        "no_visible_pop_passed",
        "intentional_cadence_passed",
        "identity_preservation_passed",
        "background_continuity_passed",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"visual review requires {key}=true")
    contact_continuity = payload.get("contact_deformation_continuity")
    if contact_continuity not in {True, "ping_pong_compatible"}:
        raise ValueError(
            "visual review requires contact_deformation_continuity=true or ping_pong_compatible"
        )
    if payload.get("candidate_gif_sha256") != candidate_sha:
        raise ValueError("visual proof candidate_gif_sha256 binding mismatch")
    if payload.get("manifest_sha256") != manifest_sha:
        raise ValueError("visual proof manifest_sha256 binding mismatch")
    if payload.get("temporal_evidence_sha256") != temporal_sha:
        raise ValueError("visual proof temporal_evidence_sha256 binding mismatch")


def _write_transactional_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent), delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
            handle.write("\n")
        if os.name == "nt":
            os.replace(temp_path, path)
            temp_path = None
        else:
            os.replace(temp_path, path)
            temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--temporal-evidence", required=True)
    parser.add_argument("--candidate-gif", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--attestation")
    parser.add_argument("--root")
    args = parser.parse_args()

    try:
        repo_root = _resolve_repo_root(args.root)
        loop_registry_path = repo_root / "Plan/10_REGISTRIES/wave26_gif_loop_profile_registry.json"
        if not loop_registry_path.is_file():
            raise ValueError(f"missing loop profile registry: {loop_registry_path}")
        loop_registry = _load_json(loop_registry_path)
        profile_ids = {
            str(entry.get("id"))
            for entry in loop_registry.get("profiles", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        if not profile_ids:
            raise ValueError("loop profile registry has no usable profile ids")

        manifest_path = Path(args.manifest).resolve()
        temporal_evidence_path = Path(args.temporal_evidence).resolve()
        candidate_path = Path(args.candidate_gif).resolve()
        output_path = Path(args.output).resolve()
        attestation: dict[str, Any] = {}
        attestation_path: Path | None = None
        if args.attestation:
            attestation_path = Path(args.attestation).resolve()
            attestation = _load_attestation(attestation_path)

        manifest = _load_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be a JSON object")
        temporal_evidence = _load_json(temporal_evidence_path)
        if not isinstance(temporal_evidence, dict):
            raise ValueError("temporal evidence must be a JSON object")

        manifest_summary = _normalize_manifest(manifest, manifest_path)
        loop_profile = _validate_temporal_evidence(temporal_evidence, manifest_summary["frame_count"])
        if loop_profile not in profile_ids:
            raise ValueError(f"unknown loop_profile taxonomy: {loop_profile}")

        manifest_sha256 = _sha256_of_path(manifest_path)
        temporal_evidence_sha256 = _sha256_of_path(temporal_evidence_path)
        source_bindings = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha256,
            "manifest_sequence_sha256": manifest_summary["sequence_sha256"],
            "temporal_evidence_path": str(temporal_evidence_path),
            "temporal_evidence_sha256": temporal_evidence_sha256,
        }

        blockers: list[str] = []
        candidate_info: dict[str, Any] | None = None
        if candidate_path.is_file():
            try:
                candidate_info = _parse_gif_candidate(candidate_path)
            except Exception:
                blockers.append("candidate_decode_failed")
        else:
            blockers.append("candidate_missing")

        synthetic_input = bool(attestation.get("synthetic_input", True))
        runtime_ready = False
        runtime_proof_present = False
        generation_executed = False
        runtime_production_proof = False
        visual_loop_review_passed = False
        review_method = "unverified"
        contact_deformation_continuity: bool | str = False
        runtime_proof_record: dict[str, Any] = {
            "proof_path": None,
            "proof_sha256": None,
            "runtime_ready": False,
            "runtime_proof_present": False,
            "generation_executed": False,
            "production_proof": False,
            "binding_valid": False,
            "verified": False,
        }
        visual_review_record: dict[str, Any] = {
            "proof_path": None,
            "proof_sha256": None,
            "review_method": "unverified",
            "visual_loop_review_passed": False,
            "no_visible_pop_passed": False,
            "intentional_cadence_passed": False,
            "identity_preservation_passed": False,
            "background_continuity_passed": False,
            "contact_deformation_continuity": False,
            "binding_valid": False,
            "verified": False,
        }

        dimensions_match = False
        frame_count_match = False
        timing_match = False
        loop_count_match = False
        duration_mismatch_indices: list[int] = []
        seam_metric_name = "first_last_rgba_mean_absolute_difference_normalized"
        seam_metric_value = 0.0
        candidate_binding: dict[str, Any] = {
            "candidate_path": str(candidate_path),
            "candidate_sha256": None,
            "candidate_bytes": None,
            "container_format": "gif",
            "container_header": None,
            "width": None,
            "height": None,
            "decoded_frame_count": 0,
            "frame_durations_ms": [],
            "loop_count": None,
            "first_frame_sha256": None,
            "last_frame_sha256": None,
            "decoded_rgba_frame_hashes": [],
        }
        if candidate_info is not None:
            candidate_binding = {
                "candidate_path": str(candidate_path),
                "candidate_sha256": _sha256_of_path(candidate_path),
                "candidate_bytes": candidate_path.stat().st_size,
                "container_format": "gif",
                "container_header": candidate_info["container_header"],
                "width": candidate_info["width"],
                "height": candidate_info["height"],
                "decoded_frame_count": candidate_info["decoded_frame_count"],
                "frame_durations_ms": candidate_info["frame_durations_ms"],
                "loop_count": candidate_info["loop_count"],
                "first_frame_sha256": candidate_info["first_frame_sha256"],
                "last_frame_sha256": candidate_info["last_frame_sha256"],
                "decoded_rgba_frame_hashes": candidate_info["decoded_rgba_frame_hashes"],
            }
            seam_metric_name = candidate_info["seam_metric_name"]
            seam_metric_value = candidate_info["seam_metric_value"]
            frame_count_match = candidate_info["decoded_frame_count"] == manifest_summary["frame_count"]
            if not frame_count_match:
                blockers.append("frame_count_mismatch")
            dimensions_match = (candidate_info["width"], candidate_info["height"]) == manifest_summary[
                "source_dimensions"
            ]
            if not dimensions_match:
                blockers.append("dimension_mismatch")
            expected_durations = manifest_summary["expected_durations_ms"]
            observed_durations = candidate_info["frame_durations_ms"]
            if len(observed_durations) == len(expected_durations):
                duration_mismatch_indices = [
                    idx
                    for idx, (a, b) in enumerate(zip(observed_durations, expected_durations))
                    if a != b
                ]
                timing_match = not duration_mismatch_indices
            if not timing_match:
                blockers.append("duration_mismatch")
            expected_loop_count = 0
            loop_count_match = candidate_info["loop_count"] == expected_loop_count
            if not loop_count_match:
                blockers.append("loop_count_mismatch")
            if candidate_info["container_header"] not in {"GIF87a", "GIF89a"}:
                blockers.append("declared_container_mismatch")

        if synthetic_input:
            if any(
                key in attestation and attestation.get(key)
                for key in (
                    "runtime_proof_path",
                    "runtime_proof_sha256",
                    "visual_review_path",
                    "visual_review_sha256",
                )
            ):
                blockers.append("synthetic_input_cannot_claim_runtime_or_visual_proof")
            blockers.append("runtime_proof_absent")
            blockers.append("visual_playback_review_absent_or_failed")
        else:
            runtime_proof_path_raw = attestation.get("runtime_proof_path")
            runtime_proof_sha_declared = attestation.get("runtime_proof_sha256")
            visual_review_path_raw = attestation.get("visual_review_path")
            visual_review_sha_declared = attestation.get("visual_review_sha256")

            if (
                not isinstance(runtime_proof_path_raw, str)
                or not runtime_proof_path_raw.strip()
                or not isinstance(runtime_proof_sha_declared, str)
            ):
                blockers.append("runtime_proof_absent")
            if (
                not isinstance(visual_review_path_raw, str)
                or not visual_review_path_raw.strip()
                or not isinstance(visual_review_sha_declared, str)
            ):
                blockers.append("visual_playback_review_absent_or_failed")

            if candidate_binding["candidate_sha256"] is not None and attestation_path is not None:
                if "runtime_proof_absent" not in blockers:
                    try:
                        runtime_proof_path = _resolve_proof_path(runtime_proof_path_raw, attestation_path)
                        runtime_proof_observed_sha = _sha256_of_path(runtime_proof_path)
                        runtime_proof_record["proof_path"] = str(runtime_proof_path)
                        runtime_proof_record["proof_sha256"] = runtime_proof_observed_sha
                        if runtime_proof_observed_sha != runtime_proof_sha_declared:
                            blockers.append("runtime_proof_hash_mismatch")
                        runtime_payload = _load_json(runtime_proof_path)
                        if not isinstance(runtime_payload, dict):
                            raise ValueError("runtime proof must be an object")
                        _validate_runtime_proof_payload(
                            runtime_payload,
                            candidate_binding["candidate_sha256"],
                            manifest_sha256,
                            temporal_evidence_sha256,
                        )
                        runtime_ready = True
                        runtime_proof_present = True
                        generation_executed = True
                        runtime_production_proof = True
                        runtime_proof_record["runtime_ready"] = True
                        runtime_proof_record["runtime_proof_present"] = True
                        runtime_proof_record["generation_executed"] = True
                        runtime_proof_record["production_proof"] = True
                        runtime_proof_record["binding_valid"] = True
                        runtime_proof_record["verified"] = runtime_proof_observed_sha == runtime_proof_sha_declared
                        if not runtime_proof_record["verified"]:
                            runtime_proof_present = False
                            runtime_ready = False
                            generation_executed = False
                            runtime_production_proof = False
                            runtime_proof_record["runtime_ready"] = False
                            runtime_proof_record["runtime_proof_present"] = False
                            runtime_proof_record["generation_executed"] = False
                            runtime_proof_record["production_proof"] = False
                    except Exception:
                        blockers.append("runtime_proof_binding_mismatch")
                if "visual_playback_review_absent_or_failed" not in blockers:
                    try:
                        visual_review_path = _resolve_proof_path(visual_review_path_raw, attestation_path)
                        visual_review_observed_sha = _sha256_of_path(visual_review_path)
                        visual_review_record["proof_path"] = str(visual_review_path)
                        visual_review_record["proof_sha256"] = visual_review_observed_sha
                        if visual_review_observed_sha != visual_review_sha_declared:
                            blockers.append("visual_proof_hash_mismatch")
                        visual_payload = _load_json(visual_review_path)
                        if not isinstance(visual_payload, dict):
                            raise ValueError("visual review proof must be an object")
                        _validate_visual_review_payload(
                            visual_payload,
                            candidate_binding["candidate_sha256"],
                            manifest_sha256,
                            temporal_evidence_sha256,
                        )
                        review_method = str(visual_payload["review_method"])
                        contact_deformation_continuity = visual_payload[
                            "contact_deformation_continuity"
                        ]
                        visual_loop_review_passed = True
                        visual_review_record["review_method"] = review_method
                        visual_review_record["visual_loop_review_passed"] = True
                        visual_review_record["no_visible_pop_passed"] = True
                        visual_review_record["intentional_cadence_passed"] = True
                        visual_review_record["identity_preservation_passed"] = True
                        visual_review_record["background_continuity_passed"] = True
                        visual_review_record[
                            "contact_deformation_continuity"
                        ] = contact_deformation_continuity
                        visual_review_record["binding_valid"] = True
                        visual_review_record["verified"] = (
                            visual_review_observed_sha == visual_review_sha_declared
                        )
                        if not visual_review_record["verified"]:
                            visual_loop_review_passed = False
                            visual_review_record["visual_loop_review_passed"] = False
                            visual_review_record["no_visible_pop_passed"] = False
                            visual_review_record["intentional_cadence_passed"] = False
                            visual_review_record["identity_preservation_passed"] = False
                            visual_review_record["background_continuity_passed"] = False
                            visual_review_record["contact_deformation_continuity"] = False
                    except Exception:
                        blockers.append("visual_proof_binding_mismatch")

            if not runtime_proof_present:
                blockers.append("runtime_proof_absent")
            if not visual_loop_review_passed:
                blockers.append("visual_playback_review_absent_or_failed")

        blockers = sorted(set(blockers))
        technical_passed = not any(
            code
            for code in blockers
            if code
            in {
                "candidate_missing",
                "candidate_decode_failed",
                "frame_count_mismatch",
                "dimension_mismatch",
                "duration_mismatch",
                "loop_count_mismatch",
                "declared_container_mismatch",
            }
        )

        computed_final_ready = technical_passed and runtime_ready and runtime_proof_present and visual_loop_review_passed
        computed_final_passed = computed_final_ready and (not synthetic_input)
        computed_certification_ready = computed_final_passed
        computed_production_proof = computed_final_passed

        if synthetic_input and (
            computed_final_ready
            or computed_final_passed
            or computed_certification_ready
            or computed_production_proof
        ):
            blockers.append("synthetic_input_not_promotable")
            computed_final_ready = False
            computed_final_passed = False
            computed_certification_ready = False
            computed_production_proof = False

        blockers = sorted(set(blockers))
        blocked = bool(blockers)
        decision = {
            "blocked": blocked,
            "blocker_codes": blockers,
            "final_export_ready": computed_final_ready and not blocked,
            "final_export_passed": computed_final_passed and not blocked,
            "certification_ready": computed_certification_ready and not blocked,
            "production_proof": computed_production_proof and not blocked,
        }

        deterministic_export_metadata = {
            "source_manifest_sequence_sha256": manifest_summary["sequence_sha256"],
            "source_temporal_evidence_sha256": temporal_evidence_sha256,
            "candidate_sha256": candidate_binding["candidate_sha256"],
            "candidate_frame_durations_ms": candidate_binding["frame_durations_ms"],
            "candidate_loop_count": candidate_binding["loop_count"],
            "candidate_dimensions": {
                "width": candidate_binding["width"],
                "height": candidate_binding["height"],
            },
        }

        output = {
            "schema_name": "wave26_gif_loop_export_evidence",
            "evidence_version": 1,
            "loop_profile": loop_profile,
            "synthetic_input": synthetic_input,
            "source_bindings": source_bindings,
            "candidate_binding": candidate_binding,
            "parity_checks": {
                "frame_count_match": frame_count_match,
                "dimensions_match": dimensions_match,
                "timing_match": timing_match,
                "duration_mismatch_indices": duration_mismatch_indices,
                "loop_count_match": loop_count_match,
                "expected_source_dimensions": {
                    "width": manifest_summary["source_dimensions"][0],
                    "height": manifest_summary["source_dimensions"][1],
                },
                "expected_source_frame_durations_ms": manifest_summary["expected_durations_ms"],
                "expected_loop_count": 0,
            },
            "technical_checks": {
                "source_sequence_integrity": True,
                "source_hash_binding_valid": True,
                "candidate_decodable_gif": candidate_info is not None,
                "declared_container_valid": candidate_info is not None,
                "seam_metric_name": seam_metric_name,
                "seam_metric_value": seam_metric_value,
                "seam_metric_is_technical_not_visual": True,
                "seam_metric_deterministic": True,
                "technical_passed": technical_passed,
            },
            "runtime_proof": runtime_proof_record,
            "visual_review": visual_review_record,
            "decision": decision,
            "deterministic_export_metadata_sha256": _sha256_of_json_payload(deterministic_export_metadata),
        }

        _write_transactional_json(output_path, output)
        print(str(output_path))
        return 0 if not blocked and decision["final_export_passed"] else BLOCKED_EXIT_CODE
    except ValueError as exc:
        _error(str(exc))
        return INVALID_EXIT_CODE
    except Exception as exc:
        _error(f"unexpected failure: {exc}")
        return INVALID_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
