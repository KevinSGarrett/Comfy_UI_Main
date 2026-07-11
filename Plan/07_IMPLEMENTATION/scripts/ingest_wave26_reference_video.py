from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any

import cv2

try:
    import jsonschema
    from jsonschema import exceptions as jsonschema_exceptions
except Exception:  # pragma: no cover - dependency failures are handled at runtime
    jsonschema = None
    jsonschema_exceptions = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FORMAT_REGISTRY = PROJECT_ROOT / "Plan/10_REGISTRIES/wave26_reference_video_input_format_registry.json"
EXTRACTION_PROFILE_REGISTRY = PROJECT_ROOT / "Plan/10_REGISTRIES/wave26_reference_video_extraction_profiles.json"
MANIFEST_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/reference_video_manifest.schema.json"
FRAME_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/reference_video_frame_manifest.schema.json"
EVIDENCE_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/wave26_reference_video_ingest_evidence.schema.json"

SUPPORTED_IMPLEMENTED_PROFILES = {"all_frames_short_clip", "sample_every_n"}
RECOGNIZED_BLOCKED_PROFILES = {
    "motion_peak_sampling",
    "contact_phase_sampling",
    "shot_boundary_sampling",
    "loop_candidate_sampling",
}


class IngestError(Exception):
    def __init__(self, message: str, *, error_type: str = "invalid_or_corrupt_input") -> None:
        super().__init__(message)
        self.error_type = error_type


class BlockedProfileError(Exception):
    def __init__(self, profile_id: str, reason: str) -> None:
        super().__init__(reason)
        self.profile_id = profile_id
        self.reason = reason


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave26 strict reference-video ingest/extraction")
    parser.add_argument("--source-video", required=True, help="Absolute or relative path to source video file")
    parser.add_argument("--output-dir", required=True, help="Output directory for ingest artifacts")
    parser.add_argument("--extraction-profile-id", required=True, help="Profile from wave26 registry")
    parser.add_argument("--source-video-id", default="", help="Optional stable source ID")
    parser.add_argument("--sample-stride", type=int, default=None, help="Optional positive stride override")
    parser.add_argument(
        "--audio-present",
        choices=("true", "false"),
        default=None,
        help="Required explicit declaration for implemented profiles; OpenCV does not verify audio",
    )
    parser.add_argument(
        "--strict-short-clip-gate",
        action="store_true",
        help="Deprecated compatibility flag; short-clip gate is always enforced",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: reject_nonfinite_json(value, path),
        )
    except FileNotFoundError as exc:
        raise IngestError(f"Required file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IngestError(f"Invalid JSON in {path}: {exc}") from exc


def reject_nonfinite_json(value: str, path: Path) -> Any:
    raise IngestError(f"Non-finite JSON token is not allowed in {path}: {value}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_float(value: float, ndigits: int = 6) -> float:
    return round(float(value), ndigits)


def finite_float_or_none(value: float) -> float | None:
    parsed = float(value)
    return stable_float(parsed) if math.isfinite(parsed) else None


def ensure_finite_positive(value: float, label: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise IngestError(f"{label} must be finite and > 0, got {value!r}")


def assess_frame_count_consistency(reported: int, decoded: int) -> dict[str, Any]:
    if decoded <= 0:
        raise IngestError("Decoded frame count must be positive")
    if reported <= 0:
        return {
            "status": "metadata_unavailable",
            "delta": None,
            "tolerance_frames": None,
        }

    tolerance = max(2, int(math.ceil(reported * 0.01)))
    delta = decoded - reported
    if abs(delta) > tolerance:
        raise IngestError(
            "Decoded frame count differs from container metadata beyond tolerance: "
            f"metadata={reported}, decoded={decoded}, tolerance={tolerance}"
        )
    return {
        "status": "exact" if delta == 0 else "within_tolerance",
        "delta": delta,
        "tolerance_frames": tolerance,
    }


def validate_required_fields(payload: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    required = schema.get("required", [])
    if not isinstance(required, list):
        raise IngestError(f"Schema {schema_path} has invalid 'required' field")
    missing = [field for field in required if field not in payload]
    if missing:
        raise IngestError(f"Schema-required fields missing for {schema_path.name}: {missing}")


def load_schema_validator(schema_path: Path) -> Any:
    if jsonschema is None:
        raise IngestError(
            "jsonschema dependency is required for Wave26 ingest validation",
            error_type="dependency_missing",
        )
    schema = load_json(schema_path)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise IngestError(
            f"Invalid JSON schema at {schema_path}: {exc}",
            error_type="schema_invalid",
        ) from exc
    return jsonschema.Draft202012Validator(schema)


def validate_instance(instance: Any, validator: Any, label: str) -> None:
    try:
        validator.validate(instance)
    except jsonschema_exceptions.ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise IngestError(
            f"{label} failed schema validation at {path}: {exc.message}",
            error_type="schema_validation_failed",
        ) from exc


def sanitize_source_video_id(raw: str) -> str:
    base = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw.strip())
    base = base.strip("_")
    return (base or "source_video")[:48]


def parse_registries(profile_id: str) -> tuple[set[str], dict[str, Any], dict[str, Any]]:
    format_registry = load_json(INPUT_FORMAT_REGISTRY)
    profile_registry = load_json(EXTRACTION_PROFILE_REGISTRY)

    extensions = set(str(ext).lower() for ext in format_registry.get("supported_video_extensions", []))
    if not extensions:
        raise IngestError("Input-format registry has no supported_video_extensions")

    profile_map: dict[str, dict[str, Any]] = {}
    for item in profile_registry.get("profiles", []):
        if isinstance(item, dict) and "id" in item:
            profile_map[str(item["id"])] = item

    if profile_id not in profile_map:
        raise IngestError(f"Unknown extraction profile id: {profile_id}")

    return extensions, profile_map[profile_id], format_registry


def make_blocker(profile_id: str, reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocker_type": "unsupported_extraction_profile",
        "profile_id": profile_id,
        "reason": reason,
        "supported_profiles": sorted(SUPPORTED_IMPLEMENTED_PROFILES),
        "recognized_blocked_profiles": sorted(RECOGNIZED_BLOCKED_PROFILES),
    }


def decode_and_extract_frames(
    source_video: Path,
    extracted_frames_dir: Path,
    source_video_id: str,
    profile_id: str,
    stride: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    capture = cv2.VideoCapture(str(source_video))
    if not capture.isOpened():
        raise IngestError("cv2.VideoCapture failed to open source video")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        reported_width = int(round(float(capture.get(cv2.CAP_PROP_FRAME_WIDTH))))
        reported_height = int(round(float(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        prop_frame_count = int(round(float(capture.get(cv2.CAP_PROP_FRAME_COUNT))))

        orientation_meta_prop = getattr(cv2, "CAP_PROP_ORIENTATION_META", None)
        orientation_auto_prop = getattr(cv2, "CAP_PROP_ORIENTATION_AUTO", None)
        orientation_metadata = (
            finite_float_or_none(float(capture.get(orientation_meta_prop)))
            if orientation_meta_prop is not None
            else None
        )
        orientation_auto = (
            finite_float_or_none(float(capture.get(orientation_auto_prop)))
            if orientation_auto_prop is not None
            else None
        )

        ensure_finite_positive(fps, "fps")

        frame_records: list[dict[str, Any]] = []
        decoded_total = 0
        decoded_width: int | None = None
        decoded_height: int | None = None
        sample_stride = 1 if profile_id == "all_frames_short_clip" else stride

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame is None or frame.size == 0:
                raise IngestError(f"Decoded blank/corrupt frame at index {decoded_total}")
            frame_h, frame_w = frame.shape[:2]
            if frame_w <= 0 or frame_h <= 0:
                raise IngestError(f"Decoded frame has invalid dimensions at index {decoded_total}: {frame_w}x{frame_h}")
            if decoded_width is None or decoded_height is None:
                decoded_width = frame_w
                decoded_height = frame_h
            elif frame_w != decoded_width or frame_h != decoded_height:
                raise IngestError(
                    f"Decoded frame dimensions inconsistent at index {decoded_total}: "
                    f"{frame_w}x{frame_h} != {decoded_width}x{decoded_height}"
                )

            if decoded_total % sample_stride == 0:
                frame_name = f"frame_{decoded_total:06d}.png"
                frame_path = extracted_frames_dir / frame_name
                write_ok = cv2.imwrite(str(frame_path), frame)
                if not write_ok or not frame_path.exists():
                    raise IngestError(f"Failed to write extracted frame PNG for index {decoded_total}")
                frame_hash = sha256_file(frame_path)
                timestamp_seconds = stable_float(decoded_total / fps)
                frame_id = f"{source_video_id}_f{decoded_total:06d}"
                frame_records.append(
                    {
                        "source_video_id": source_video_id,
                        "frame_id": frame_id,
                        "frame_index": decoded_total,
                        "timestamp_seconds": timestamp_seconds,
                        "frame_path_or_asset_id": f"frames/{frame_name}",
                        "width": frame_w,
                        "height": frame_h,
                        "qa_status": "decoded_png_hash_verified",
                        "png_sha256": frame_hash,
                    }
                )

            decoded_total += 1
    finally:
        capture.release()

    if decoded_total <= 0:
        raise IngestError("Decoded frame count is zero")
    frame_count_consistency = assess_frame_count_consistency(
        reported=prop_frame_count,
        decoded=decoded_total,
    )
    if decoded_width is None or decoded_height is None:
        raise IngestError("Decoded frame dimensions could not be established")

    duration_seconds = stable_float(decoded_total / fps)
    ensure_finite_positive(duration_seconds, "duration_seconds")
    if not frame_records:
        raise IngestError("No frames selected for extraction under requested profile")

    metadata = {
        "fps": stable_float(fps),
        "width": decoded_width,
        "height": decoded_height,
        "decoded_frame_count": decoded_total,
        "duration_seconds": duration_seconds,
        "metadata_frame_count": prop_frame_count if prop_frame_count > 0 else None,
        "frame_count_consistency": frame_count_consistency["status"],
        "frame_count_delta": frame_count_consistency["delta"],
        "frame_count_tolerance_frames": frame_count_consistency["tolerance_frames"],
        "reported_width": reported_width,
        "reported_height": reported_height,
        "orientation_metadata_degrees": orientation_metadata,
        "orientation_auto_flag": orientation_auto,
    }
    return frame_records, metadata


def main() -> int:
    args = parse_args()
    source_video = Path(args.source_video).resolve()
    output_dir = Path(args.output_dir).resolve()
    profile_id = str(args.extraction_profile_id).strip()

    if not source_video.exists() or not source_video.is_file():
        raise IngestError(f"Source video does not exist: {source_video}")
    if source_video.stat().st_size <= 0:
        raise IngestError(f"Source video is empty: {source_video}")

    supported_exts, selected_profile, format_registry = parse_registries(profile_id)
    extension = source_video.suffix.lower()
    if extension not in supported_exts:
        raise IngestError(f"Unsupported source extension {extension!r}; allowed={sorted(supported_exts)}")

    if profile_id in RECOGNIZED_BLOCKED_PROFILES:
        raise BlockedProfileError(
            profile_id=profile_id,
            reason="Profile is recognized but intentionally blocked pending semantic analyzers",
        )
    if profile_id not in SUPPORTED_IMPLEMENTED_PROFILES:
        raise IngestError(f"Profile {profile_id} is neither implemented nor recognized as blocked")
    if args.audio_present is None:
        raise IngestError(
            "Implemented profiles require --audio-present true|false declaration",
            error_type="missing_required_argument",
        )

    if args.sample_stride is not None and args.sample_stride <= 0:
        raise IngestError("sample_stride must be > 0 when provided")

    default_stride = int(selected_profile.get("default_stride", 1))
    sample_stride = args.sample_stride if args.sample_stride is not None else default_stride
    if profile_id == "sample_every_n" and sample_stride <= 0:
        raise IngestError("sample_every_n requires a positive sample stride")
    if profile_id == "all_frames_short_clip":
        sample_stride = 1

    source_hash = sha256_file(source_video)
    audio_present = args.audio_present == "true"
    source_video_label = sanitize_source_video_id(args.source_video_id) if args.source_video_id.strip() else "refvid"
    source_video_id = f"{source_video_label}_{source_hash[:16]}"

    manifest_validator = load_schema_validator(MANIFEST_SCHEMA)
    frame_validator = load_schema_validator(FRAME_SCHEMA)
    evidence_validator = load_schema_validator(EVIDENCE_SCHEMA)

    if output_dir.exists():
        raise IngestError(
            f"Refusing to overwrite existing output path: {output_dir}",
            error_type="output_path_exists",
        )
    output_parent = output_dir.parent
    try:
        output_parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise IngestError(
            f"Unable to prepare output parent {output_parent}: {exc}",
            error_type="output_parent_unavailable",
        ) from exc

    tmp_prefix = f".wave26_ingest_{source_video_id}_"
    temp_dir = Path(tempfile.mkdtemp(prefix=tmp_prefix, dir=str(output_parent)))
    runtime_dir = temp_dir / "artifacts"
    frames_dir = runtime_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        frame_records, decode_meta = decode_and_extract_frames(
            source_video=source_video,
            extracted_frames_dir=frames_dir,
            source_video_id=source_video_id,
            profile_id=profile_id,
            stride=sample_stride,
        )

        max_short_clip = float(selected_profile.get("max_recommended_seconds", 8.0))
        ensure_finite_positive(max_short_clip, "max_recommended_seconds")
        if profile_id == "all_frames_short_clip" and decode_meta["duration_seconds"] > max_short_clip:
            raise IngestError(
                f"all_frames_short_clip duration gate failed: {decode_meta['duration_seconds']} > {max_short_clip}"
            )

        manifest = {
            "source_video_id": source_video_id,
            "original_path_or_asset_id": str(source_video),
            "file_extension": extension,
            "container_format": extension.lstrip("."),
            "duration_seconds": decode_meta["duration_seconds"],
            "fps": decode_meta["fps"],
            "frame_count": decode_meta["decoded_frame_count"],
            "width": decode_meta["width"],
            "height": decode_meta["height"],
            "audio_present": audio_present,
            "fingerprint": f"sha256:{source_hash}",
            "extraction_profile_id": profile_id,
            "orientation_assumption": "opencv_properties_recorded_no_explicit_ingest_rotation",
            "fps_assumption": "opencv_container_reported_fps_unverified",
            "orientation_metadata_degrees_reported_by_opencv": decode_meta["orientation_metadata_degrees"],
            "orientation_auto_flag_reported_by_opencv": decode_meta["orientation_auto_flag"],
            "reported_dimensions_from_container": {
                "width": decode_meta["reported_width"],
                "height": decode_meta["reported_height"],
            },
            "explicit_ingest_rotation_applied": False,
        }
        required_metadata_fields = format_registry.get("required_metadata")
        if not isinstance(required_metadata_fields, list) or not all(
            isinstance(field, str) and field for field in required_metadata_fields
        ):
            raise IngestError("Input-format registry required_metadata must be a string array")
        missing_registry_metadata = [
            field for field in required_metadata_fields if field not in manifest
        ]
        if missing_registry_metadata:
            raise IngestError(
                "Manifest is missing registry-required metadata fields: "
                f"{missing_registry_metadata}"
            )
        validate_required_fields(manifest, MANIFEST_SCHEMA)
        validate_instance(manifest, manifest_validator, "reference_video_manifest")

        frame_manifest_path = runtime_dir / "frame_manifest.jsonl"
        with frame_manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in frame_records:
                validate_required_fields(record, FRAME_SCHEMA)
                validate_instance(record, frame_validator, "frame_manifest_record")
                handle.write(
                    json.dumps(
                        record,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                )

        manifest_path = runtime_dir / "reference_video_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest_sha256 = sha256_file(manifest_path)
        frame_manifest_sha256 = sha256_file(frame_manifest_path)

        evidence = {
            "schema_version": "1.0.0",
            "status": "success",
            "source_video": {
                "path": str(source_video),
                "sha256": source_hash,
                "bytes": source_video.stat().st_size,
                "extension": extension,
            },
            "ingest": {
                "source_video_id": source_video_id,
                "extraction_profile_id": profile_id,
                "sample_stride": sample_stride,
                "frames_extracted": len(frame_records),
                "decoded_frame_count": decode_meta["decoded_frame_count"],
                "reported_frame_count": decode_meta["metadata_frame_count"],
                "frame_count_consistency": decode_meta["frame_count_consistency"],
                "frame_count_delta": decode_meta["frame_count_delta"],
                "frame_count_tolerance_frames": decode_meta["frame_count_tolerance_frames"],
                "duration_seconds": decode_meta["duration_seconds"],
                "fps": decode_meta["fps"],
                "width": decode_meta["width"],
                "height": decode_meta["height"],
                "strict_short_clip_gate": True,
                "max_recommended_seconds": max_short_clip if profile_id == "all_frames_short_clip" else None,
                "audio_present": audio_present,
                "audio_evidence_provenance": "explicit_cli_declaration_not_verified_by_opencv",
                "reported_width": decode_meta["reported_width"],
                "reported_height": decode_meta["reported_height"],
                "decoded_width": decode_meta["width"],
                "decoded_height": decode_meta["height"],
                "orientation_metadata_degrees_reported_by_opencv": decode_meta["orientation_metadata_degrees"],
                "orientation_auto_flag_reported_by_opencv": decode_meta["orientation_auto_flag"],
            },
            "assumptions": {
                "orientation": "opencv_properties_recorded_no_explicit_ingest_rotation",
                "fps": "opencv_container_reported_fps_unverified",
                "audio": "explicit_cli_declaration_not_verified_by_opencv",
            },
            "blocked_profiles": sorted(RECOGNIZED_BLOCKED_PROFILES),
            "unsupported_semantic_analyzers": sorted(RECOGNIZED_BLOCKED_PROFILES),
            "claims": {
                "pose_timeline_generated": False,
                "depth_timeline_generated": False,
                "mask_timeline_generated": False,
                "contact_timeline_generated": False,
                "shot_matching_performed": False,
                "visual_qa_complete": False,
                "orientation_normalization_verified": False,
                "fps_normalization_verified": False,
                "production_proof_complete": False,
                "final_promotion_ready": False,
            },
            "artifacts": {
                "manifest_path": "reference_video_manifest.json",
                "frame_manifest_path": "frame_manifest.jsonl",
                "frames_dir": "frames",
                "evidence_path": "wave26_reference_video_ingest_evidence.json",
                "manifest_sha256": manifest_sha256,
                "manifest_bytes": manifest_path.stat().st_size,
                "frame_manifest_sha256": frame_manifest_sha256,
                "frame_manifest_bytes": frame_manifest_path.stat().st_size,
            },
            "determinism": {
                "id_strategy": "sha256-derived source id and frame index ids",
                "timestamp_strategy": "frame_index_div_fps_rounded_6",
                "record_ordering": "ascending_frame_index",
                "jsonl_serialization": "sorted_keys_compact",
            },
            "registry_checks": {
                "input_format_registry": str(INPUT_FORMAT_REGISTRY),
                "extraction_profile_registry": str(EXTRACTION_PROFILE_REGISTRY),
                "supported_video_extensions": sorted(supported_exts),
                "required_metadata_fields": required_metadata_fields,
            },
        }
        validate_required_fields(evidence, EVIDENCE_SCHEMA)
        validate_instance(evidence, evidence_validator, "wave26_reference_video_ingest_evidence")
        evidence_path = runtime_dir / "wave26_reference_video_ingest_evidence.json"
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )

        success_line = json.dumps(
            {
                "status": "success",
                "source_video_id": source_video_id,
                "profile": profile_id,
                "frames_extracted": len(frame_records),
                "output_dir": str(output_dir),
            },
            sort_keys=True,
            allow_nan=False,
        )
        if output_dir.exists():
            raise IngestError(
                f"Output path appeared before publication: {output_dir}",
                error_type="output_path_exists",
            )
        runtime_dir.rename(output_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

        try:
            print(success_line)
        except (BrokenPipeError, OSError, ValueError):
            pass
        return 0
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BlockedProfileError as blocked:
        print(json.dumps(make_blocker(blocked.profile_id, blocked.reason), sort_keys=True))
        raise SystemExit(2)
    except IngestError as ingest_error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_type": ingest_error.error_type,
                    "message": str(ingest_error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1)
    except Exception as unexpected_error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_type": "unexpected_exception",
                    "message": str(unexpected_error),
                    "exception_class": type(unexpected_error).__name__,
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1)
