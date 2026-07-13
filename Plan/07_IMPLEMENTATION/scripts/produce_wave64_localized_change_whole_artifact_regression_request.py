#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()
REVIEWER_ROLE = "Codex Desktop autonomous QA"
BINDING_ARGUMENTS = (
    "baseline_row033_report", "candidate_row033_report", "row032_global_audio_report", "wave33_preview_qa",
    "baseline_artifact_manifest", "candidate_artifact_manifest", "failure_record", "retest_record",
    "whole_artifact_delta", "whole_artifact_review", "runtime_proof", "baseline_primary_media",
    "candidate_primary_media", "change_manifest",
)
METADATA_KEYS = {
    "regression_id", "change_id", "scene_id", "shot_id", "take_id", "baseline_artifact_id",
    "candidate_artifact_id", "baseline_run_id", "candidate_run_id", "review_run_id", "change_kind",
    "audio_change_expected", "production_authority_claim", "canonical_partitions", "target_partition_ids",
    "non_target_partition_ids", "attempt_history",
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")),
    )


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root") from exc
    return path


def binding(path: Path) -> dict[str, Any]:
    before = path.stat()
    if not path.is_file() or before.st_size < 1:
        raise ValueError(f"input missing or empty: {path}")
    digest = file_sha256(path)
    after = path.stat()
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise ValueError(f"input changed while hashing: {path}")
    return {"path": str(path), "sha256": digest, "bytes": after.st_size}


def relative_binding(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "path": Path(value["path"]).resolve().relative_to(root).as_posix()}


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def write_atomic_no_clobber(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def validate_metadata(metadata: dict[str, Any], bindings: dict[str, dict[str, Any]]) -> None:
    observed = set(metadata)
    if observed != METADATA_KEYS:
        raise ValueError(f"metadata key mismatch: missing={sorted(METADATA_KEYS-observed)} unknown={sorted(observed-METADATA_KEYS)}")
    for key in (
        "regression_id", "change_id", "scene_id", "shot_id", "take_id", "baseline_artifact_id",
        "candidate_artifact_id", "baseline_run_id", "candidate_run_id", "review_run_id", "change_kind",
    ):
        require_nonempty_string(metadata[key], f"metadata.{key}")
    if not isinstance(metadata["audio_change_expected"], bool):
        raise ValueError("metadata.audio_change_expected must be boolean")
    claim = require_object(metadata["production_authority_claim"], "metadata.production_authority_claim")
    if set(claim) != {"authority_id", "bundle_id"}:
        raise ValueError("production_authority_claim key mismatch")
    require_nonempty_string(claim["authority_id"], "authority_id")
    require_nonempty_string(claim["bundle_id"], "bundle_id")

    partitions = require_object(metadata["canonical_partitions"], "canonical_partitions")
    visual_domain = require_object(partitions.get("visual_domain"), "visual_domain")
    audio_domain = require_object(partitions.get("audio_domain"), "audio_domain")
    def integer(value: Any, label: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{label} must be an integer")
        return value
    total_frames = integer(visual_domain.get("total_frames"), "visual_domain.total_frames")
    width = integer(visual_domain.get("width"), "visual_domain.width")
    height = integer(visual_domain.get("height"), "visual_domain.height")
    if total_frames <= 0 or width <= 0 or height <= 0:
        raise ValueError("visual domain dimensions must be positive")
    if integer(visual_domain.get("timeline_start_frame"), "timeline_start_frame") != 0 or integer(visual_domain.get("timeline_end_frame"), "timeline_end_frame") != total_frames - 1:
        raise ValueError("visual timeline must exactly cover all frames")
    total_samples = integer(audio_domain.get("total_samples"), "audio_domain.total_samples")
    sample_rate = integer(audio_domain.get("sample_rate_hz"), "audio_domain.sample_rate_hz")
    channel_count = integer(audio_domain.get("channel_count"), "audio_domain.channel_count")
    duration = audio_domain.get("duration_seconds")
    if total_samples <= 0 or sample_rate <= 0 or channel_count <= 0 or not isinstance(duration, (int, float)) or isinstance(duration, bool):
        raise ValueError("audio domain values must be positive numeric values")
    if abs(float(duration) - total_samples / sample_rate) > 1e-6:
        raise ValueError("audio duration does not match total_samples/sample_rate")
    visual = partitions.get("visual_partitions")
    audio = partitions.get("audio_partitions")
    if not isinstance(visual, list) or not isinstance(audio, list) or not visual or not audio:
        raise ValueError("canonical visual and audio partitions are required")
    ids = [item.get("partition_id") for item in visual + audio if isinstance(item, dict)]
    if len(ids) != len(visual) + len(audio) or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("every canonical partition needs a partition_id")
    if len(set(ids)) != len(ids):
        raise ValueError("canonical partition IDs must be unique")
    visual_ranges: list[tuple[int, int]] = []
    for item in visual:
        start = integer(item.get("start_frame"), "visual.start_frame")
        end = integer(item.get("end_frame"), "visual.end_frame")
        x = integer(item.get("x"), "visual.x")
        y = integer(item.get("y"), "visual.y")
        part_width = integer(item.get("width"), "visual.width")
        part_height = integer(item.get("height"), "visual.height")
        if start < 0 or end < start or end >= total_frames or x < 0 or y < 0 or part_width <= 0 or part_height <= 0 or x + part_width > width or y + part_height > height:
            raise ValueError("visual partition range or geometry is invalid")
        visual_ranges.append((start, end))
    audio_ranges: list[tuple[int, int]] = []
    for item in audio:
        start = integer(item.get("start_sample"), "audio.start_sample")
        end = integer(item.get("end_sample"), "audio.end_sample")
        channel_start = integer(item.get("channel_start"), "audio.channel_start")
        channel_end = integer(item.get("channel_end"), "audio.channel_end")
        if item.get("sample_rate_hz") != sample_rate or item.get("channel_count") != channel_count:
            raise ValueError("audio partition format mismatches audio domain")
        if start < 0 or end < start or end >= total_samples or channel_start < 0 or channel_end < channel_start or channel_end >= channel_count:
            raise ValueError("audio partition sample or channel range is invalid")
        if abs(float(item.get("start_seconds")) - start / sample_rate) > 1e-6 or abs(float(item.get("end_seconds")) - (end + 1) / sample_rate) > 1e-6:
            raise ValueError("audio partition sample/time conversion mismatch")
        audio_ranges.append((start, end))
    def exact_coverage(ranges: list[tuple[int, int]], final: int, label: str) -> None:
        ordered = sorted(ranges)
        if not ordered or ordered[0][0] != 0 or ordered[-1][1] != final:
            raise ValueError(f"{label} must cover its complete domain")
        previous = -1
        for start, end in ordered:
            if start != previous + 1:
                raise ValueError(f"{label} contains an overlap or gap")
            previous = end
    exact_coverage(visual_ranges, total_frames - 1, "visual partitions")
    exact_coverage(audio_ranges, total_samples - 1, "audio partitions")
    targets = metadata["target_partition_ids"]
    non_targets = metadata["non_target_partition_ids"]
    if not isinstance(targets, list) or not isinstance(non_targets, list):
        raise ValueError("target and non-target partition IDs must be arrays")
    if set(targets) & set(non_targets) or set(targets) | set(non_targets) != set(ids):
        raise ValueError("target and non-target IDs must form an exact disjoint canonical partition")

    history = require_object(metadata["attempt_history"], "attempt_history")
    if set(history) != {"attempts", "attempt_history_digest", "deeper_diagnosis", "new_direction_hash"}:
        raise ValueError("attempt_history key mismatch")
    attempts = history["attempts"]
    if not isinstance(attempts, list) or history["attempt_history_digest"] != stable_sha256(attempts):
        raise ValueError("attempt_history_digest mismatch")
    for index, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict) or attempt.get("attempt_number") != index:
            raise ValueError("attempt history must be sequential from attempt 1")
    deeper = require_object(history["deeper_diagnosis"], "deeper_diagnosis")
    if deeper.get("binding") != bindings["retest_record_binding"]:
        raise ValueError("deeper diagnosis must bind the exact retest record")


def production_authority_matches(
    root: Path,
    request: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    rules: dict[str, Any],
    paths: dict[str, Path],
) -> bool:
    authority_rules = require_object(rules.get("authority_rules"), "rules.authority_rules")
    objects = authority_rules.get("production_authority_exact_objects")
    if not isinstance(objects, list):
        raise ValueError("production_authority_exact_objects must be an array")
    claim = request["production_authority_claim"]
    candidates = [
        item for item in objects
        if isinstance(item, dict)
        and item.get("authority_id") == claim["authority_id"]
        and item.get("bundle_id") == claim["bundle_id"]
    ]
    if len(candidates) != 1:
        return False
    history = request["attempt_history"]
    attempts = history["attempts"]
    attempt_number = attempts[-1]["attempt_number"] + 1 if attempts else 1
    review = require_object(load_json(paths["whole_artifact_review_binding"]), "whole_artifact_review")
    runtime = require_object(load_json(paths["runtime_proof_binding"]), "runtime_proof")
    change = require_object(load_json(paths["change_manifest_binding"]), "change_manifest")
    expected = {
        **request["production_authority_claim"],
        **{key: request[key] for key in (
            "regression_id", "change_id", "scene_id", "shot_id", "take_id", "baseline_artifact_id",
            "candidate_artifact_id", "baseline_run_id", "candidate_run_id", "review_run_id", "change_kind",
            "audio_change_expected",
        )},
        "current_attempt_number": attempt_number,
        "attempt_history_digest": history["attempt_history_digest"],
        "canonical_partition_digest": stable_sha256(request["canonical_partitions"]),
        "producer_id": require_nonempty_string(require_object(runtime.get("identity"), "runtime.identity").get("producer_id"), "producer_id"),
        "reviewer_id": require_nonempty_string(require_object(review.get("reviewer_identity"), "review.reviewer_identity").get("reviewer_id"), "reviewer_id"),
        "reviewer_role": REVIEWER_ROLE,
        "change_summary_hash": require_nonempty_string(change.get("change_summary_hash"), "change_summary_hash"),
        "input_bindings": {key: relative_binding(root, value) for key, value in bindings.items()},
    }
    return candidates[0] == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    for name in BINDING_ARGUMENTS:
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if root != CANONICAL_ROOT:
            raise ValueError("root must be the canonical project root")
        output = resolve_under(root, Path(args.output), "output")
        output_report = resolve_under(root, Path(args.output_report), "output_report")
        metadata_path = resolve_under(root, Path(args.metadata), "metadata")
        if output == output_report or output in (metadata_path,) or output_report == metadata_path:
            raise ValueError("request, report, and metadata paths must be distinct")
        if output.exists() or output_report.exists():
            raise ValueError("request or report output collision")

        paths: dict[str, Path] = {}
        bindings: dict[str, dict[str, Any]] = {}
        for name in BINDING_ARGUMENTS:
            field = f"{name}_binding"
            path = resolve_under(root, Path(getattr(args, name)), name)
            paths[field] = path
            bindings[field] = binding(path)
        if len(set(paths.values())) != len(paths):
            raise ValueError("all 14 upstream artifacts must be distinct")
        if output_report in paths.values() or metadata_path in paths.values():
            raise ValueError("report, metadata, and upstream artifact paths must be distinct")

        metadata = require_object(load_json(metadata_path), "metadata")
        validate_metadata(metadata, bindings)
        request = {
            "schema_name": "wave64_localized_change_whole_artifact_regression_request",
            "request_version": 3,
            "tracker_id": "TRK-W64-034",
            "item_id": "ITEM-W64-034",
            **metadata,
            "bindings": bindings,
            "output_report_path": str(output_report),
        }
        schema = require_object(load_json(root / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_request.schema.json"), "schema")
        errors = sorted(Draft202012Validator(schema).iter_errors(request), key=lambda item: list(item.path))
        if errors:
            raise ValueError(f"request schema validation failed: {errors[0].message}")
        rules = require_object(load_json(root / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json"), "rules")
        if args.production_input and not production_authority_matches(root, request, bindings, rules, paths):
            raise ValueError("exact production authority object is required")
        write_atomic_no_clobber(output, request)
        print(json.dumps({"output": str(output), "production_input": args.production_input, "status": "pass"}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
