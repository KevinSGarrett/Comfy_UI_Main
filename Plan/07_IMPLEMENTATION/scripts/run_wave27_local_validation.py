#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import py_compile
import re
from pathlib import Path
from typing import Any

DECISIONS = {"promote", "repair", "rerun", "block"}
REPAIR_EVENT_STATUS = {"applied", "skipped", "failed", "not_needed"}
REQUIRED_DIMENSIONS = (
    "identity_drift",
    "flicker",
    "pose_continuity",
    "depth_continuity",
    "contact_continuity",
    "export_integrity",
)
REQUIRED_OFFLINE_FILES = (
    "Plan/08_SCHEMAS/wave27_frame_manifest.schema.json",
    "Plan/08_SCHEMAS/wave27_temporal_evidence.schema.json",
    "Plan/09_EXAMPLES/wave27_frame_manifest.example.json",
    "Plan/09_EXAMPLES/wave27_temporal_evidence.example.json",
    "Plan/07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py",
    "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py",
    "Plan/07_IMPLEMENTATION/scripts/run_wave27_local_validation.py",
    "Plan/10_REGISTRIES/wave27_temporal_qa_scoring_rules.json",
    "Plan/10_REGISTRIES/wave27_frame_repair_policy.json",
    "Plan/10_REGISTRIES/wave27_video_engine_registry.json",
    "Plan/10_REGISTRIES/wave27_video_route_selection_rules.json",
    "Plan/10_REGISTRIES/wave27_main_flow_video_routing_inventory.json",
    "Plan/10_REGISTRIES/wave26_gif_loop_profile_registry.json",
    "Plan/07_IMPLEMENTATION/templates/powershell/Run-Wave27-VideoRoutingTemporalQAValidation.ps1",
)


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_roots(root_arg: str) -> tuple[Path, Path]:
    root = Path(root_arg).resolve()
    if (root / "Plan").is_dir():
        return root, root / "Plan"
    if root.name == "Plan" and root.is_dir():
        return root.parent, root
    raise ValueError(f"unable to resolve repository or Plan root from --root={root}")


def _type_ok(expected: str, value: Any) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _validate_schema_instance(
    schema: dict[str, Any], instance: Any, path: str, errors: list[str]
) -> None:
    expected_type = schema.get("type")
    if expected_type is not None and not _type_ok(expected_type, instance):
        errors.append(f"{path}: expected {expected_type}, got {type(instance).__name__}")
        return

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if not math.isfinite(float(instance)):
            errors.append(f"{path}: number must be finite")
            return
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: value {instance} > maximum {schema['maximum']}")

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(instance) < min_length:
            errors.append(f"{path}: string length < minLength {min_length}")
        pattern = schema.get("pattern")
        if pattern is not None:
            import re

            if not re.match(pattern, instance):
                errors.append(f"{path}: string does not match pattern {pattern!r}")

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: item count < minItems {min_items}")
        if schema.get("uniqueItems") is True:
            seen: list[Any] = []
            for item in instance:
                if item in seen:
                    errors.append(f"{path}: duplicate item violates uniqueItems")
                    break
                seen.append(item)
        item_schema = schema.get("items")
        if item_schema is not None:
            for idx, item in enumerate(instance):
                _validate_schema_instance(item_schema, item, f"{path}[{idx}]", errors)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for field in required:
            if field not in instance:
                errors.append(f"{path}: missing required field {field!r}")
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(instance.keys()) - set(props.keys()))
            for field in unknown:
                errors.append(f"{path}: unknown field {field!r}")
        for field, value in instance.items():
            if field in props:
                _validate_schema_instance(props[field], value, f"{path}.{field}", errors)


def _validate_contiguous_indexes(frames: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    indexes = [frame.get("frame_index") for frame in frames]
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indexes):
        errors.append("manifest.frames: frame_index must be integer for all frames")
        return errors
    expected = list(range(0, len(frames)))
    if indexes != expected:
        errors.append(
            f"manifest.frames: frame_index order must be exact {expected}; got {indexes}"
        )
    return errors


def _compute_sequence_sha256(frames: list[dict[str, Any]]) -> str:
    payload: list[dict[str, Any]] = []
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
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_manifest_strict(manifest: dict[str, Any], manifest_path: Path) -> list[str]:
    errors: list[str] = []
    frames = manifest.get("frames")
    if not isinstance(frames, list):
        errors.append("manifest.frames: must be a list")
        return errors
    manifest_count = manifest.get("frame_count")
    if manifest_count != len(frames):
        errors.append(
            f"manifest.frame_count must equal len(frames) ({manifest_count} != {len(frames)})"
        )
    errors.extend(_validate_contiguous_indexes(frames))

    previous_time: float | None = None
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            errors.append(f"manifest.frames[{idx}]: must be object")
            continue
        visible = frame.get("visible_characters")
        if not isinstance(visible, list):
            errors.append(f"manifest.frames[{idx}].visible_characters must be list")
        else:
            normalized = [item.strip() for item in visible if isinstance(item, str)]
            if len(normalized) != len(visible):
                errors.append(f"manifest.frames[{idx}].visible_characters must be non-empty strings")
            elif len(set(normalized)) != len(normalized):
                errors.append(f"manifest.frames[{idx}].visible_characters must be unique")
        for optional_obj in ("contact_state", "deformation_state"):
            if optional_obj in frame and not isinstance(frame[optional_obj], dict):
                errors.append(f"manifest.frames[{idx}].{optional_obj} must be an object when provided")
        raw_time = frame.get("time_seconds")
        if not isinstance(raw_time, (int, float)) or isinstance(raw_time, bool):
            errors.append(f"manifest.frames[{idx}].time_seconds must be numeric")
            continue
        current_time = float(raw_time)
        if not math.isfinite(current_time):
            errors.append(f"manifest.frames[{idx}].time_seconds must be finite")
            continue
        if previous_time is not None and current_time <= previous_time:
            errors.append("manifest.frames: time_seconds must be strictly increasing")
        previous_time = current_time

        artifact_rel = frame.get("artifact_path")
        artifact_sha = frame.get("artifact_sha256")
        artifact_bytes = frame.get("artifact_bytes")
        if not isinstance(artifact_rel, str) or not artifact_rel.strip():
            errors.append(f"manifest.frames[{idx}].artifact_path must be a non-empty string")
            continue
        if not isinstance(artifact_sha, str) or re.fullmatch(r"[a-f0-9]{64}", artifact_sha) is None:
            errors.append(f"manifest.frames[{idx}].artifact_sha256 must be 64 lowercase hex chars")
            continue
        if (
            not isinstance(artifact_bytes, int)
            or isinstance(artifact_bytes, bool)
            or artifact_bytes <= 0
        ):
            errors.append(f"manifest.frames[{idx}].artifact_bytes must be a positive integer")
            continue
        artifact_path = Path(artifact_rel)
        if not artifact_path.is_absolute():
            artifact_path = (manifest_path.parent / artifact_path).resolve()
        if not artifact_path.is_file():
            errors.append(f"manifest.frames[{idx}] artifact missing: {artifact_path}")
            continue
        observed_bytes = artifact_path.stat().st_size
        if observed_bytes <= 0:
            errors.append(f"manifest.frames[{idx}] artifact is empty: {artifact_path}")
        if observed_bytes != artifact_bytes:
            errors.append(
                f"manifest.frames[{idx}] artifact_bytes mismatch ({artifact_bytes} != {observed_bytes})"
            )
        observed_sha = _sha256_of(artifact_path)
        if observed_sha != artifact_sha:
            errors.append(
                f"manifest.frames[{idx}] artifact_sha256 mismatch ({artifact_sha} != {observed_sha})"
            )

    try:
        expected_sequence = _compute_sequence_sha256(frames)
    except Exception as exc:
        expected_sequence = None
        errors.append(f"manifest.sequence_sha256 could not be recomputed: {exc}")
    actual_sequence = manifest.get("sequence_sha256")
    if not isinstance(actual_sequence, str):
        errors.append("manifest.sequence_sha256 must be a string")
    elif expected_sequence is not None and actual_sequence != expected_sequence:
        errors.append(
            f"manifest.sequence_sha256 mismatch ({actual_sequence} != {expected_sequence})"
        )
    return errors


def _cross_validate_strict(
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    scoring_rules: dict[str, Any],
    repair_policy: dict[str, Any],
    loop_registry: dict[str, Any],
    engine_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    manifest_count = manifest.get("frame_count")
    evidence_count = evidence.get("frame_count")
    if manifest_count != evidence_count:
        errors.append(
            "cross_file: frame_count mismatch between manifest and temporal evidence "
            f"({manifest_count} != {evidence_count})"
        )

    dimension_names = scoring_rules.get("dimensions")
    if dimension_names != list(REQUIRED_DIMENSIONS):
        errors.append("scoring registry dimensions are not the required six dimensions")
        return errors
    try:
        promote_threshold = float(scoring_rules["promotion_threshold"])
        repair_threshold = float(scoring_rules["repair_threshold"])
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"scoring registry thresholds are invalid: {exc}")
        return errors
    if (
        not math.isfinite(promote_threshold)
        or not math.isfinite(repair_threshold)
        or repair_threshold < 0
        or promote_threshold > 100
        or repair_threshold > promote_threshold
    ):
        errors.append("scoring registry thresholds must satisfy 0 <= repair <= promote <= 100")
    raw_hard_fail_conditions = scoring_rules.get("hard_fail_conditions", [])
    if not isinstance(raw_hard_fail_conditions, list) or any(
        not isinstance(item, str) or not item.strip() for item in raw_hard_fail_conditions
    ):
        errors.append("scoring registry hard_fail_conditions must contain non-empty strings")
        raw_hard_fail_conditions = []
    hard_fail_conditions = {item.strip() for item in raw_hard_fail_conditions}
    if not hard_fail_conditions:
        errors.append("scoring registry hard_fail_conditions must not be empty")

    allowed_actions = {
        entry.get("action")
        for entry in repair_policy.get("repair_classes", [])
        if isinstance(entry, dict) and isinstance(entry.get("action"), str)
    }
    allowed_actions.discard(None)
    if not allowed_actions:
        errors.append("repair policy registry has no usable actions")

    loop_profiles = {
        entry.get("id")
        for entry in loop_registry.get("profiles", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    loop_profiles.discard(None)
    if not loop_profiles:
        errors.append("loop profile registry has no usable profile IDs")

    engine_ids = {
        entry.get("id")
        for entry in engine_registry.get("engines", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    engine_ids.discard(None)
    if not engine_ids:
        errors.append("video engine registry has no usable engine IDs")
    evidence_engine = evidence.get("engine_name")
    if evidence_engine not in engine_ids:
        errors.append(f"temporal_evidence.engine_name not found in registry: {evidence_engine}")
    frame_engines = {
        frame.get("engine_name")
        for frame in manifest.get("frames", [])
        if isinstance(frame, dict)
    }
    unknown_frame_engines = sorted(
        str(engine) for engine in frame_engines if engine not in engine_ids
    )
    if unknown_frame_engines:
        errors.append(
            f"manifest contains engine_name values not found in registry: {', '.join(unknown_frame_engines)}"
        )
    if evidence_engine not in frame_engines:
        errors.append("temporal_evidence.engine_name must appear in the frame manifest")

    raw_dimension_scores = evidence.get("dimension_scores")
    if not isinstance(raw_dimension_scores, dict):
        errors.append("temporal_evidence.dimension_scores must be an object")
        return errors
    if set(raw_dimension_scores.keys()) != set(REQUIRED_DIMENSIONS):
        errors.append(
            "temporal_evidence.dimension_scores must include exactly identity_drift, flicker, "
            "pose_continuity, depth_continuity, contact_continuity, export_integrity"
        )

    recomputed_dimension_scores: dict[str, float] = {}
    numeric_sources = {
        "identity_drift": evidence.get("identity_drift_score"),
        "flicker": evidence.get("flicker_score"),
        "pose_continuity": evidence.get("pose_continuity_score"),
        "depth_continuity": evidence.get("depth_continuity_score"),
        "contact_continuity": evidence.get("contact_continuity_score"),
        "export_integrity": evidence.get("export_integrity_score"),
    }
    for key in REQUIRED_DIMENSIONS:
        value = numeric_sources.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            errors.append(f"temporal_evidence.{key}_score source value must be finite numeric")
            continue
        score = float(value)
        if score < 0 or score > 100:
            errors.append(f"temporal_evidence.{key}_score source value must be in [0,100]")
            continue
        if key in {"identity_drift", "flicker"}:
            recomputed_dimension_scores[key] = round(max(0.0, 100.0 - score), 2)
        else:
            recomputed_dimension_scores[key] = round(score, 2)

    for key, expected in recomputed_dimension_scores.items():
        reported = raw_dimension_scores.get(key)
        if not isinstance(reported, (int, float)) or isinstance(reported, bool):
            errors.append(f"temporal_evidence.dimension_scores.{key} must be numeric")
            continue
        if round(float(reported), 2) != expected:
            errors.append(
                f"temporal_evidence.dimension_scores.{key} mismatch ({reported} != {expected})"
            )

    recomputed_overall = None
    if len(recomputed_dimension_scores) == len(REQUIRED_DIMENSIONS):
        recomputed_overall = round(
            sum(recomputed_dimension_scores.values()) / float(len(REQUIRED_DIMENSIONS)), 2
        )
    reported_overall = evidence.get("overall_temporal_score")
    if (
        recomputed_overall is None
        or
        not isinstance(reported_overall, (int, float))
        or isinstance(reported_overall, bool)
        or round(float(reported_overall), 2) != recomputed_overall
    ):
        errors.append(
            f"temporal_evidence.overall_temporal_score mismatch ({reported_overall} != {recomputed_overall})"
        )

    loop_profile = evidence.get("loop_profile")
    if not isinstance(loop_profile, str) or not loop_profile.strip():
        errors.append("temporal_evidence.loop_profile must be a non-empty string")
    elif loop_profile not in loop_profiles:
        errors.append(f"temporal_evidence.loop_profile not found in registry: {loop_profile}")

    hard_failures = evidence.get("hard_failures")
    if not isinstance(hard_failures, list):
        errors.append("temporal_evidence.hard_failures must be a list")
        hard_failures = []
    elif any(not isinstance(item, str) or not item.strip() for item in hard_failures):
        errors.append("temporal_evidence.hard_failures must contain non-empty strings")
        hard_failures = []
    else:
        hard_failures = [item.strip() for item in hard_failures]
        if len(set(hard_failures)) != len(hard_failures):
            errors.append("temporal_evidence.hard_failures must be unique")
        unknown_hard_failures = sorted(set(hard_failures) - hard_fail_conditions)
        if unknown_hard_failures:
            errors.append(
                "temporal_evidence.hard_failures contain unknown taxonomy values: "
                + ", ".join(unknown_hard_failures)
            )
    hard_fail_hit = bool(hard_failures) and not bool(set(hard_failures) - hard_fail_conditions)

    frames = manifest.get("frames", [])
    manifest_indexes = {
        frame.get("frame_index")
        for frame in frames
        if isinstance(frame, dict) and isinstance(frame.get("frame_index"), int)
    }
    repair_events = evidence.get("repair_events", [])
    if not isinstance(repair_events, list):
        errors.append("temporal_evidence.repair_events must be a list")
        repair_events = []
    for idx, event in enumerate(repair_events):
        if not isinstance(event, dict):
            errors.append(f"temporal_evidence.repair_events[{idx}] must be an object")
            continue
        frame_index = event.get("frame_index")
        if frame_index not in manifest_indexes:
            errors.append(
                f"cross_file: repair_events[{idx}].frame_index {frame_index} not in manifest"
            )
        action_value = event.get("action")
        event_type_value = event.get("event_type")
        if (
            action_value is not None
            and event_type_value is not None
            and action_value != event_type_value
        ):
            errors.append(
                f"temporal_evidence.repair_events[{idx}].action and event_type must match"
            )
        action = action_value if action_value is not None else event_type_value
        if not isinstance(action, str) or not action.strip():
            errors.append(f"temporal_evidence.repair_events[{idx}].action must be non-empty string")
        elif action not in allowed_actions:
            errors.append(
                f"temporal_evidence.repair_events[{idx}].action not allowed by repair policy: {action}"
            )
        status = event.get("status")
        if status not in REPAIR_EVENT_STATUS:
            errors.append(f"temporal_evidence.repair_events[{idx}].status invalid: {status}")

    statuses = [event.get("status") for event in repair_events if isinstance(event, dict)]
    has_failed_or_skipped = any(status in {"failed", "skipped"} for status in statuses)
    recomputed_policy_consistent = not has_failed_or_skipped
    reported_policy = evidence.get("repair_policy_consistent")
    if reported_policy is not recomputed_policy_consistent:
        errors.append(
            "temporal_evidence.repair_policy_consistent mismatch "
            f"({reported_policy} != {recomputed_policy_consistent})"
        )

    promote_eligible_events = all(status in {"applied", "not_needed"} for status in statuses)
    if hard_fail_hit or not recomputed_policy_consistent:
        expected_decision = "block"
    elif recomputed_overall is not None and recomputed_overall >= promote_threshold and promote_eligible_events:
        expected_decision = "promote"
    elif recomputed_overall is not None and recomputed_overall >= repair_threshold:
        expected_decision = "repair"
    else:
        expected_decision = "rerun"

    decision = evidence.get("promotion_decision")
    if decision not in DECISIONS:
        errors.append("temporal_evidence.promotion_decision invalid")
    elif decision != expected_decision:
        errors.append(f"temporal_evidence.promotion_decision mismatch ({decision} != {expected_decision})")

    loop_export = evidence.get("loop_export", {})
    if isinstance(loop_export, dict):
        if loop_export.get("structural_gate_passed") is not True:
            errors.append("cross_file: loop_export.structural_gate_passed must be true")
        if loop_export.get("decision_scope") != "offline_structural_only":
            errors.append("cross_file: loop_export.decision_scope must be offline_structural_only")
        if loop_export.get("final_export_ready") is not False:
            errors.append("cross_file: final_export_ready must remain false for offline packet")
        if loop_export.get("final_export_passed") is not False:
            errors.append("cross_file: final_export_passed is unsupported in offline packet")
    else:
        errors.append("cross_file: loop_export must be an object")
    return errors


def _run_pack_integrity(repo_root: Path) -> tuple[dict[str, Any], int]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for relative in REQUIRED_OFFLINE_FILES:
        path = repo_root / relative
        result: dict[str, Any] = {"path": str(path), "exists": path.exists()}
        if not path.exists():
            errors.append(f"missing required file: {path}")
            checks.append(result)
            continue
        if path.suffix.lower() == ".json":
            try:
                _load_json(path)
                result["json_parse"] = "pass"
            except Exception as exc:
                result["json_parse"] = f"fail: {exc}"
                errors.append(f"json parse failed: {path}: {exc}")
        if path.suffix.lower() == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                result["python_compile"] = "pass"
            except Exception as exc:
                result["python_compile"] = f"fail: {exc}"
                errors.append(f"python compile failed: {path}: {exc}")
        checks.append(result)
    report = {
        "status": "pass" if not errors else "fail",
        "mode": "pack_integrity",
        "checked_root": str(repo_root),
        "checks": {"pack_integrity": checks},
        "error_count": len(errors),
    }
    return report, 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest")
    parser.add_argument("--evidence")
    parser.add_argument("--frame-schema")
    parser.add_argument("--evidence-schema")
    parser.add_argument("--strict-packet", action="store_true")
    args = parser.parse_args()

    try:
        repo_root, plan_root = _resolve_roots(args.root)
    except Exception as exc:
        print(json.dumps({"status": "fail", "checks": {"schema_validation": [str(exc)]}}, indent=2, sort_keys=True))
        return 1

    strict_requested = args.strict_packet or args.manifest is not None or args.evidence is not None
    if not strict_requested:
        report, code = _run_pack_integrity(repo_root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return code

    if args.manifest is None or args.evidence is None:
        report = {
            "status": "fail",
            "mode": "strict_packet",
            "checks": {
                "schema_validation": [
                    "strict packet mode requires both --manifest and --evidence"
                ],
                "cross_file_consistency": [],
            },
            "error_count": 1,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    frame_schema_path = (
        Path(args.frame_schema).resolve()
        if args.frame_schema
        else plan_root / "08_SCHEMAS/wave27_frame_manifest.schema.json"
    )
    evidence_schema_path = (
        Path(args.evidence_schema).resolve()
        if args.evidence_schema
        else plan_root / "08_SCHEMAS/wave27_temporal_evidence.schema.json"
    )
    manifest_path = Path(args.manifest).resolve()
    evidence_path = Path(args.evidence).resolve()

    report: dict[str, Any] = {
        "status": "pass",
        "mode": "strict_packet",
        "checked": {
            "frame_schema": str(frame_schema_path),
            "temporal_schema": str(evidence_schema_path),
            "manifest": str(manifest_path),
            "temporal_evidence": str(evidence_path),
        },
        "checks": {
            "schema_validation": [],
            "cross_file_consistency": [],
        },
    }
    errors: list[str] = []

    try:
        frame_schema = _load_json(frame_schema_path)
        evidence_schema = _load_json(evidence_schema_path)
        manifest = _load_json(manifest_path)
        evidence = _load_json(evidence_path)
        scoring_rules = _load_json(repo_root / "Plan/10_REGISTRIES/wave27_temporal_qa_scoring_rules.json")
        repair_policy = _load_json(repo_root / "Plan/10_REGISTRIES/wave27_frame_repair_policy.json")
        loop_registry = _load_json(repo_root / "Plan/10_REGISTRIES/wave26_gif_loop_profile_registry.json")
        engine_registry = _load_json(repo_root / "Plan/10_REGISTRIES/wave27_video_engine_registry.json")
    except Exception as exc:
        report["status"] = "fail"
        report["checks"]["schema_validation"].append(f"io_or_json_error: {exc}")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    schema_errors: list[str] = []
    _validate_schema_instance(frame_schema, manifest, "manifest", schema_errors)
    _validate_schema_instance(evidence_schema, evidence, "temporal_evidence", schema_errors)
    report["checks"]["schema_validation"] = schema_errors
    errors.extend(schema_errors)

    try:
        strict_manifest_errors = _validate_manifest_strict(manifest, manifest_path)
    except Exception as exc:
        strict_manifest_errors = [f"manifest strict validation internal failure: {exc}"]
    report["checks"]["manifest_strict"] = strict_manifest_errors
    errors.extend(strict_manifest_errors)

    try:
        cross_file_errors = _cross_validate_strict(
            manifest=manifest,
            evidence=evidence,
            scoring_rules=scoring_rules,
            repair_policy=repair_policy,
            loop_registry=loop_registry,
            engine_registry=engine_registry,
        )
    except Exception as exc:
        cross_file_errors = [f"cross-file validation internal failure: {exc}"]
    report["checks"]["cross_file_consistency"] = cross_file_errors
    errors.extend(cross_file_errors)

    if errors:
        report["status"] = "fail"
        report["error_count"] = len(errors)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    report["status"] = "pass"
    report["error_count"] = 0
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
