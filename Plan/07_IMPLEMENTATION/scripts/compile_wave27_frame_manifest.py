#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_RECORD_FIELDS = (
    "frame_index",
    "time_seconds",
    "source_route",
    "engine_name",
    "shot_id",
    "visible_characters",
    "camera_state",
    "qa_scores",
    "repair_status",
    "artifact_path",
    "artifact_sha256",
)
OPTIONAL_RECORD_FIELDS = (
    "keyframe_phase",
    "identity_targets",
    "contact_state",
    "deformation_state",
    "export_target",
    "notes",
)
ALLOWED_RECORD_FIELDS = set(REQUIRED_RECORD_FIELDS + OPTIONAL_RECORD_FIELDS)
REPAIR_STATUS_ENUM = {"none", "repaired", "needs_repair", "unknown"}
QA_SCORE_FIELDS = {
    "identity_drift_score",
    "flicker_score",
    "pose_continuity_score",
    "depth_continuity_score",
    "contact_continuity_score",
    "export_integrity_score",
    "overall_temporal_score",
}
EXPORT_TARGETS = {"gif", "mp4", "webm"}


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _load_input_records(input_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(input_path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        if not raw:
            raise ValueError(f"{input_path}: input list is empty")
        if any(not isinstance(item, dict) for item in raw):
            raise ValueError(f"{input_path}: every list entry must be a JSON object")
        return raw
    raise ValueError(f"{input_path}: input must be a JSON object or list of objects")


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _normalize_artifact_path(artifact_path: Path, output_parent: Path) -> str:
    resolved = artifact_path.resolve()
    try:
        rel = resolved.relative_to(output_parent)
        return rel.as_posix()
    except ValueError:
        return resolved.as_posix()


def _validate_record(record: dict[str, Any], source_path: Path, ordinal: int) -> dict[str, Any]:
    prefix = f"{source_path} record[{ordinal}]"
    unknown_fields = sorted(set(record.keys()) - ALLOWED_RECORD_FIELDS)
    if unknown_fields:
        raise ValueError(f"{prefix}: unknown fields: {', '.join(unknown_fields)}")
    missing_fields = [field for field in REQUIRED_RECORD_FIELDS if field not in record]
    if missing_fields:
        raise ValueError(f"{prefix}: missing fields: {', '.join(missing_fields)}")

    frame_index = record["frame_index"]
    if not isinstance(frame_index, int) or isinstance(frame_index, bool) or frame_index < 0:
        raise ValueError(f"{prefix}: frame_index must be a non-negative integer")

    time_seconds = record["time_seconds"]
    if not isinstance(time_seconds, (int, float)) or isinstance(time_seconds, bool):
        raise ValueError(f"{prefix}: time_seconds must be numeric")
    if not math.isfinite(float(time_seconds)) or float(time_seconds) < 0:
        raise ValueError(f"{prefix}: time_seconds must be finite and >= 0")

    for key in ("source_route", "engine_name", "shot_id", "artifact_path"):
        value = record[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{prefix}: {key} must be a non-empty string")

    visible_characters = record["visible_characters"]
    if not isinstance(visible_characters, list):
        raise ValueError(f"{prefix}: visible_characters must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in visible_characters):
        raise ValueError(f"{prefix}: visible_characters must contain non-empty strings")
    normalized_characters = [item.strip() for item in visible_characters]
    if len(set(normalized_characters)) != len(normalized_characters):
        raise ValueError(f"{prefix}: visible_characters must be unique")

    camera_state = record["camera_state"]
    if not isinstance(camera_state, dict):
        raise ValueError(f"{prefix}: camera_state must be an object")

    qa_scores = record["qa_scores"]
    if not isinstance(qa_scores, dict):
        raise ValueError(f"{prefix}: qa_scores must be an object")
    unknown_qa_scores = sorted(set(qa_scores) - QA_SCORE_FIELDS)
    if unknown_qa_scores:
        raise ValueError(f"{prefix}: unknown qa_scores: {', '.join(unknown_qa_scores)}")
    for key, value in qa_scores.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{prefix}: qa_scores.{key} must be numeric")
        if not math.isfinite(float(value)) or float(value) < 0 or float(value) > 100:
            raise ValueError(f"{prefix}: qa_scores.{key} must be finite in [0, 100]")

    repair_status = record["repair_status"]
    if repair_status not in REPAIR_STATUS_ENUM:
        allowed = ", ".join(sorted(REPAIR_STATUS_ENUM))
        raise ValueError(f"{prefix}: repair_status must be one of: {allowed}")

    artifact_hash = record["artifact_sha256"]
    if not isinstance(artifact_hash, str) or not SHA256_RE.match(artifact_hash):
        raise ValueError(f"{prefix}: artifact_sha256 must be a lowercase 64-char SHA256 hex")

    artifact_path = Path(record["artifact_path"])
    if not artifact_path.is_absolute():
        artifact_path = (source_path.parent / artifact_path).resolve()
    if not artifact_path.exists() or not artifact_path.is_file():
        raise ValueError(f"{prefix}: artifact does not exist: {artifact_path}")

    observed_hash = _sha256_of(artifact_path)
    if observed_hash != artifact_hash:
        raise ValueError(
            f"{prefix}: artifact_sha256 mismatch for {artifact_path}: "
            f"expected {artifact_hash}, got {observed_hash}"
        )
    artifact_bytes = artifact_path.stat().st_size
    if artifact_bytes <= 0:
        raise ValueError(f"{prefix}: artifact must be non-empty: {artifact_path}")

    if "contact_state" in record and not isinstance(record["contact_state"], dict):
        raise ValueError(f"{prefix}: contact_state must be an object when provided")
    if "deformation_state" in record and not isinstance(record["deformation_state"], dict):
        raise ValueError(f"{prefix}: deformation_state must be an object when provided")
    if "keyframe_phase" in record and (
        not isinstance(record["keyframe_phase"], str) or not record["keyframe_phase"].strip()
    ):
        raise ValueError(f"{prefix}: keyframe_phase must be a non-empty string when provided")
    if "identity_targets" in record:
        identity_targets = record["identity_targets"]
        if not isinstance(identity_targets, list) or any(
            not isinstance(item, str) or not item.strip() for item in identity_targets
        ):
            raise ValueError(f"{prefix}: identity_targets must contain non-empty strings")
        normalized_targets = [item.strip() for item in identity_targets]
        if len(set(normalized_targets)) != len(normalized_targets):
            raise ValueError(f"{prefix}: identity_targets must be unique")
        record = dict(record)
        record["identity_targets"] = normalized_targets
    if "export_target" in record and record["export_target"] not in EXPORT_TARGETS:
        raise ValueError(
            f"{prefix}: export_target must be one of: {', '.join(sorted(EXPORT_TARGETS))}"
        )
    if "notes" in record and not isinstance(record["notes"], str):
        raise ValueError(f"{prefix}: notes must be a string when provided")

    normalized: dict[str, Any] = {}
    normalized["frame_index"] = frame_index
    normalized["time_seconds"] = float(time_seconds)
    normalized["source_route"] = str(record["source_route"]).strip()
    normalized["engine_name"] = str(record["engine_name"]).strip()
    normalized["shot_id"] = str(record["shot_id"]).strip()
    normalized["visible_characters"] = normalized_characters
    normalized["camera_state"] = record["camera_state"]
    normalized["qa_scores"] = record["qa_scores"]
    normalized["repair_status"] = repair_status
    normalized["artifact_path"] = artifact_path
    normalized["artifact_sha256"] = observed_hash
    normalized["artifact_bytes"] = artifact_bytes
    for field in OPTIONAL_RECORD_FIELDS:
        if field in record:
            normalized[field] = record[field]
    return normalized


def _validate_sequence(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_indexes = sorted(item["frame_index"] for item in records)
    if len(set(sorted_indexes)) != len(sorted_indexes):
        duplicates = []
        for index in sorted(set(sorted_indexes)):
            if sorted_indexes.count(index) > 1:
                duplicates.append(str(index))
        raise ValueError(f"duplicate frame_index values: {', '.join(duplicates)}")
    if not sorted_indexes or sorted_indexes[0] != 0:
        raise ValueError("frame_index sequence must start at 0")
    expected = list(range(0, len(sorted_indexes)))
    if sorted_indexes != expected:
        raise ValueError(
            "frame_index sequence must be contiguous; "
            f"expected {expected}, got {sorted_indexes}"
        )
    ordered = sorted(records, key=lambda item: item["frame_index"])
    previous_time = None
    for idx, record in enumerate(ordered):
        current_time = float(record["time_seconds"])
        if not math.isfinite(current_time):
            raise ValueError(f"frame[{idx}]: time_seconds must be finite")
        if previous_time is not None and current_time <= previous_time:
            raise ValueError("time_seconds must be strictly increasing in frame_index order")
        previous_time = current_time
    return ordered


def _compute_sequence_sha256(records: list[dict[str, Any]]) -> str:
    payload = []
    for item in records:
        payload.append(
            {
                "frame_index": item["frame_index"],
                "time_seconds": float(item["time_seconds"]),
                "artifact_path": item["artifact_path"],
                "artifact_sha256": item["artifact_sha256"],
                "artifact_bytes": item["artifact_bytes"],
            }
        )
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    all_records: list[dict[str, Any]] = []
    try:
        output_path = Path(args.output).resolve()
        output_parent = output_path.parent
        for input_name in args.input:
            input_path = Path(input_name).resolve()
            if not input_path.exists():
                raise ValueError(f"input does not exist: {input_path}")
            for idx, raw_record in enumerate(_load_input_records(input_path)):
                validated = _validate_record(raw_record, input_path, idx)
                artifact_resolved = Path(str(validated["artifact_path"])).resolve()
                if artifact_resolved == output_path:
                    raise ValueError("output path must not overwrite a frame artifact")
                validated["artifact_path"] = _normalize_artifact_path(artifact_resolved, output_parent)
                all_records.append(validated)
        if not all_records:
            raise ValueError("no frame records were provided")

        all_records = _validate_sequence(all_records)
    except Exception as exc:
        _error(str(exc))
        return 1

    sequence_sha256 = _compute_sequence_sha256(all_records)
    output = {
        "schema_name": "wave27_frame_manifest",
        "manifest_version": 1,
        "frame_count": len(all_records),
        "frames": all_records,
        "sequence_sha256": sequence_sha256,
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        _error(f"unable to write output manifest: {exc}")
        return 1
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
