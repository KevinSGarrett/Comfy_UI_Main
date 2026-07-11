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

from jsonschema import Draft202012Validator

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ESCALATION_FAILURE = "persistent_shot_instability"


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


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_required_schemas(repo_root: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "manifest": repo_root / "Plan/08_SCHEMAS/wave27_frame_manifest.schema.json",
        "evidence": repo_root / "Plan/08_SCHEMAS/wave27_temporal_evidence.schema.json",
        "ledger": repo_root / "Plan/08_SCHEMAS/wave27_frame_repair_ledger.schema.json",
    }
    loaded: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        if not path.is_file():
            raise ValueError(f"required schema missing: {path}")
        loaded_schema = _load_json(path)
        Draft202012Validator.check_schema(loaded_schema)
        loaded[key] = loaded_schema
    return loaded


def _validate_against_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.absolute_path)
        if where:
            raise ValueError(f"{label} schema validation failed at {where}: {first.message}")
        raise ValueError(f"{label} schema validation failed: {first.message}")


def _resolve_artifact(path_str: str, manifest_path: Path) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = (manifest_path.parent / path).resolve()
    return path


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


def _normalize_and_validate_manifest(
    manifest: dict[str, Any], manifest_path: Path
) -> list[dict[str, Any]]:
    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("manifest.frames must be a non-empty array")
    frame_count = manifest.get("frame_count")
    if frame_count != len(frames):
        raise ValueError("manifest.frame_count must match len(manifest.frames)")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
        raise ValueError("manifest.frame_count must be a positive integer")
    if manifest.get("schema_name") != "wave27_frame_manifest":
        raise ValueError("manifest.schema_name must be wave27_frame_manifest")

    ordered = sorted(frames, key=lambda item: item["frame_index"])
    expected_indexes = list(range(0, len(ordered)))
    observed_indexes = [item["frame_index"] for item in ordered]
    if observed_indexes != expected_indexes:
        raise ValueError(f"manifest frame_index sequence invalid: {observed_indexes}")

    previous_time: float | None = None
    normalized: list[dict[str, Any]] = []
    for idx, frame in enumerate(ordered):
        if not isinstance(frame["time_seconds"], (int, float)) or isinstance(frame["time_seconds"], bool):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be numeric")
        time_seconds = float(frame["time_seconds"])
        if not math.isfinite(time_seconds):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be finite")
        if previous_time is not None and time_seconds <= previous_time:
            raise ValueError("manifest time_seconds must be strictly increasing")
        previous_time = time_seconds

        artifact_sha = frame["artifact_sha256"]
        if not isinstance(artifact_sha, str) or SHA256_RE.fullmatch(artifact_sha) is None:
            raise ValueError(f"manifest.frames[{idx}].artifact_sha256 must be lowercase SHA256")
        artifact_bytes = frame["artifact_bytes"]
        if (
            not isinstance(artifact_bytes, int)
            or isinstance(artifact_bytes, bool)
            or artifact_bytes <= 0
        ):
            raise ValueError(f"manifest.frames[{idx}].artifact_bytes must be positive")
        artifact_path = _resolve_artifact(frame["artifact_path"], manifest_path)
        if not artifact_path.is_file():
            raise ValueError(f"manifest frame artifact missing: {artifact_path}")
        observed_bytes = artifact_path.stat().st_size
        if observed_bytes != artifact_bytes:
            raise ValueError(
                f"manifest.frames[{idx}] artifact_bytes mismatch: {artifact_bytes} != {observed_bytes}"
            )
        observed_sha = _sha256_of_path(artifact_path)
        if observed_sha != artifact_sha:
            raise ValueError(
                f"manifest.frames[{idx}] artifact_sha256 mismatch: {artifact_sha} != {observed_sha}"
            )

        normalized.append(
            {
                "frame_index": frame["frame_index"],
                "time_seconds": time_seconds,
                "source_route": frame["source_route"],
                "engine_name": frame["engine_name"],
                "shot_id": frame["shot_id"],
                "visible_characters": frame["visible_characters"],
                "camera_state": frame["camera_state"],
                "qa_scores": frame["qa_scores"],
                "repair_status": frame["repair_status"],
                "artifact_path": frame["artifact_path"],
                "artifact_path_resolved": str(artifact_path),
                "artifact_sha256": observed_sha,
                "artifact_bytes": observed_bytes,
            }
        )

    recomputed_sequence = _compute_manifest_sequence_sha256(ordered)
    if manifest.get("sequence_sha256") != recomputed_sequence:
        raise ValueError("manifest.sequence_sha256 mismatch")
    return normalized


def _validate_evidence(evidence: dict[str, Any], expected_frame_count: int) -> None:
    if evidence.get("schema_name") != "wave27_temporal_evidence":
        raise ValueError("evidence.schema_name must be wave27_temporal_evidence")
    frame_count = evidence.get("frame_count")
    if frame_count != expected_frame_count:
        raise ValueError("evidence.frame_count must match manifest.frame_count")
    repair_events = evidence.get("repair_events")
    if not isinstance(repair_events, list):
        raise ValueError("evidence.repair_events must be an array")
    for idx, event in enumerate(repair_events):
        if not isinstance(event, dict):
            raise ValueError(f"evidence.repair_events[{idx}] must be object")
        frame_index = event.get("frame_index")
        if (
            not isinstance(frame_index, int)
            or isinstance(frame_index, bool)
            or frame_index < 0
            or frame_index >= expected_frame_count
        ):
            raise ValueError(f"evidence.repair_events[{idx}].frame_index out of range")


def _load_failure_action_map(policy: dict[str, Any]) -> dict[str, str]:
    entries = policy.get("repair_classes")
    if not isinstance(entries, list) or not entries:
        raise ValueError("repair policy repair_classes must be a non-empty list")
    mapping: dict[str, str] = {}
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"repair policy entry[{idx}] must be object")
        failure = entry.get("failure")
        action = entry.get("action")
        if (
            not isinstance(failure, str)
            or not failure.strip()
            or not isinstance(action, str)
            or not action.strip()
        ):
            raise ValueError(f"repair policy entry[{idx}] failure/action must be non-empty strings")
        if failure in mapping:
            raise ValueError(f"repair policy duplicates failure taxonomy: {failure}")
        mapping[failure] = action
    return mapping


def _validate_policy_covers_hardcoded_actions(policy_map: dict[str, str]) -> None:
    required_actions = {
        "frame_local_identity_repair",
        "frame_local_visual_repair",
        "short_span_repair",
        "rerun_shot",
    }
    observed_actions = set(policy_map.values())
    missing = sorted(required_actions - observed_actions)
    if missing:
        raise ValueError(f"repair policy missing hardcoded actions: {', '.join(missing)}")


def _validate_defect_report(
    defect_report: dict[str, Any],
    frame_count: int,
    expected_manifest_sequence_sha256: str,
    expected_evidence_sha256: str,
    allowed_failures: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(defect_report, dict):
        raise ValueError("defect report must be a JSON object")
    allowed_keys = {
        "schema_name",
        "report_version",
        "frame_count",
        "manifest_sequence_sha256",
        "temporal_evidence_sha256",
        "defects",
    }
    unknown = sorted(set(defect_report.keys()) - allowed_keys)
    if unknown:
        raise ValueError(f"defect report has unknown fields: {', '.join(unknown)}")
    if defect_report.get("schema_name") != "wave27_frame_defect_report":
        raise ValueError("defect report schema_name must be wave27_frame_defect_report")
    report_version = defect_report.get("report_version")
    if not isinstance(report_version, int) or isinstance(report_version, bool) or report_version < 1:
        raise ValueError("defect report report_version must be integer >= 1")
    if defect_report.get("frame_count") != frame_count:
        raise ValueError("defect report frame_count must match manifest/evidence frame_count")
    manifest_sequence_sha256 = defect_report.get("manifest_sequence_sha256")
    if manifest_sequence_sha256 != expected_manifest_sequence_sha256:
        raise ValueError("defect report manifest_sequence_sha256 binding mismatch")
    evidence_sha256 = defect_report.get("temporal_evidence_sha256")
    if evidence_sha256 != expected_evidence_sha256:
        raise ValueError("defect report temporal_evidence_sha256 binding mismatch")
    if not isinstance(manifest_sequence_sha256, str) or SHA256_RE.fullmatch(manifest_sequence_sha256) is None:
        raise ValueError("defect report manifest_sequence_sha256 must be lowercase SHA256")
    if not isinstance(evidence_sha256, str) or SHA256_RE.fullmatch(evidence_sha256) is None:
        raise ValueError("defect report temporal_evidence_sha256 must be lowercase SHA256")

    defects = defect_report.get("defects")
    if not isinstance(defects, list):
        raise ValueError("defect report defects must be an array")

    normalized: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, str]] = set()
    for idx, defect in enumerate(defects):
        if not isinstance(defect, dict):
            raise ValueError(f"defects[{idx}] must be object")
        defect_allowed_keys = {"frame_index", "failure", "region_note", "evidence_note"}
        defect_unknown = sorted(set(defect.keys()) - defect_allowed_keys)
        if defect_unknown:
            raise ValueError(f"defects[{idx}] has unknown fields: {', '.join(defect_unknown)}")

        frame_index = defect.get("frame_index")
        if (
            not isinstance(frame_index, int)
            or isinstance(frame_index, bool)
            or frame_index < 0
            or frame_index >= frame_count
        ):
            raise ValueError(f"defects[{idx}].frame_index out of range")
        failure = defect.get("failure")
        if not isinstance(failure, str) or not failure.strip():
            raise ValueError(f"defects[{idx}].failure must be non-empty string")
        failure = failure.strip()
        if failure not in allowed_failures:
            raise ValueError(f"defects[{idx}].failure not in repair policy taxonomy: {failure}")
        pair = (frame_index, failure)
        if pair in seen_pairs:
            raise ValueError(f"duplicate defect record for frame_index={frame_index}, failure={failure}")
        seen_pairs.add(pair)

        out: dict[str, Any] = {"frame_index": frame_index, "failure": failure}
        for note_field in ("region_note", "evidence_note"):
            if note_field in defect:
                value = defect[note_field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"defects[{idx}].{note_field} must be non-empty string when present")
                out[note_field] = value.strip()
        normalized.append(out)

    normalized.sort(key=lambda item: (item["frame_index"], item["failure"]))
    return normalized


def _group_contiguous_spans(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    sorted_unique = sorted(set(indices))
    spans: list[list[int]] = [[sorted_unique[0]]]
    for index in sorted_unique[1:]:
        if index == spans[-1][-1] + 1:
            spans[-1].append(index)
        else:
            spans.append([index])
    return spans


def _choose_span_action(span_failures: set[str], span_size: int, policy_map: dict[str, str]) -> tuple[str, str]:
    if ESCALATION_FAILURE in span_failures or span_size > 5:
        reason = (
            "persistent_shot_instability_escalation"
            if ESCALATION_FAILURE in span_failures
            else "span_length_gt_5_escalation"
        )
        return "rerun_shot", reason
    if 2 <= span_size <= 5:
        return "short_span_repair", "contiguous_span_2_to_5"

    mapped_actions = {policy_map[failure] for failure in span_failures}
    if "frame_local_identity_repair" in mapped_actions:
        return "frame_local_identity_repair", "single_frame_identity_mapping"
    if "frame_local_visual_repair" in mapped_actions:
        return "frame_local_visual_repair", "single_frame_visual_mapping"
    return sorted(mapped_actions)[0], "single_frame_policy_mapping"


def _validate_candidate_manifest(
    source_frames: list[dict[str, Any]],
    candidate_manifest: dict[str, Any],
    candidate_manifest_path: Path,
    target_indexes: set[int],
) -> dict[str, Any]:
    candidate_frames = _normalize_and_validate_manifest(candidate_manifest, candidate_manifest_path)
    if len(candidate_frames) != len(source_frames):
        raise ValueError("candidate manifest frame_count mismatch with source manifest")

    target_frame_deltas: list[dict[str, Any]] = []
    preserved_frame_verifications: list[dict[str, Any]] = []
    for source, candidate in zip(source_frames, candidate_frames):
        if source["frame_index"] != candidate["frame_index"]:
            raise ValueError("candidate frame_index sequence mismatch")
        index = source["frame_index"]
        artifact_hash_unchanged = source["artifact_sha256"] == candidate["artifact_sha256"]
        artifact_bytes_unchanged = source["artifact_bytes"] == candidate["artifact_bytes"]
        artifact_changed = not (artifact_hash_unchanged and artifact_bytes_unchanged)

        if index in target_indexes:
            if source["time_seconds"] != candidate["time_seconds"]:
                raise ValueError(f"candidate timestamp drift at target frame {index}")
            if source["shot_id"] != candidate["shot_id"]:
                raise ValueError(f"candidate shot_id drift at target frame {index}")
            if source["visible_characters"] != candidate["visible_characters"]:
                raise ValueError(f"candidate visible_characters drift at target frame {index}")
            if source["camera_state"] != candidate["camera_state"]:
                raise ValueError(f"candidate camera_state drift at target frame {index}")
            if not artifact_changed:
                raise ValueError(f"candidate unchanged target frame: {index}")
            target_frame_deltas.append(
                {
                    "frame_index": index,
                    "time_seconds": source["time_seconds"],
                    "shot_id": source["shot_id"],
                    "visible_characters": source["visible_characters"],
                    "camera_state": source["camera_state"],
                    "protected_metadata_unchanged": True,
                    "original_artifact_path": source["artifact_path"],
                    "original_artifact_bytes": source["artifact_bytes"],
                    "original_artifact_sha256": source["artifact_sha256"],
                    "candidate_artifact_path": candidate["artifact_path"],
                    "candidate_artifact_bytes": candidate["artifact_bytes"],
                    "candidate_artifact_sha256": candidate["artifact_sha256"],
                    "artifact_changed": True,
                    "original_source_route": source["source_route"],
                    "candidate_source_route": candidate["source_route"],
                    "source_route_changed": source["source_route"] != candidate["source_route"],
                    "original_engine_name": source["engine_name"],
                    "candidate_engine_name": candidate["engine_name"],
                    "engine_name_changed": source["engine_name"] != candidate["engine_name"],
                    "original_qa_scores": source["qa_scores"],
                    "candidate_qa_scores": candidate["qa_scores"],
                    "qa_scores_changed": source["qa_scores"] != candidate["qa_scores"],
                    "original_repair_status": source["repair_status"],
                    "candidate_repair_status": candidate["repair_status"],
                    "repair_status_changed": source["repair_status"] != candidate["repair_status"],
                }
            )
        else:
            if source["frame_index"] != candidate["frame_index"]:
                raise ValueError(f"candidate frame_index drift at passing frame {index}")
            if source["time_seconds"] != candidate["time_seconds"]:
                raise ValueError(f"candidate time_seconds drift at passing frame {index}")
            if source["source_route"] != candidate["source_route"]:
                raise ValueError(f"candidate source_route drift at passing frame {index}")
            if source["engine_name"] != candidate["engine_name"]:
                raise ValueError(f"candidate engine_name drift at passing frame {index}")
            if source["shot_id"] != candidate["shot_id"]:
                raise ValueError(f"candidate shot_id drift at passing frame {index}")
            if source["visible_characters"] != candidate["visible_characters"]:
                raise ValueError(f"candidate visible_characters drift at passing frame {index}")
            if source["camera_state"] != candidate["camera_state"]:
                raise ValueError(f"candidate camera_state drift at passing frame {index}")
            if source["qa_scores"] != candidate["qa_scores"]:
                raise ValueError(f"candidate qa_scores drift at passing frame {index}")
            if source["repair_status"] != candidate["repair_status"]:
                raise ValueError(f"candidate repair_status drift at passing frame {index}")
            if not artifact_hash_unchanged:
                raise ValueError(f"candidate changed passing frame out-of-target: {index}")
            if not artifact_bytes_unchanged:
                raise ValueError(f"candidate changed passing frame bytes out-of-target: {index}")
            preserved_frame_verifications.append(
                {
                    "frame_index": index,
                    "source_route_unchanged": True,
                    "engine_name_unchanged": True,
                    "shot_id_unchanged": True,
                    "visible_characters_unchanged": True,
                    "camera_state_unchanged": True,
                    "qa_scores_unchanged": True,
                    "repair_status_unchanged": True,
                    "time_seconds_unchanged": True,
                    "artifact_sha256_unchanged": True,
                    "artifact_bytes_unchanged": True,
                    "artifact_path_relocated": source["artifact_path"] != candidate["artifact_path"],
                    "all_protected_metadata_unchanged": True,
                    "preserved_artifact_unchanged": True,
                }
            )

    return {
        "candidate_manifest_path": str(candidate_manifest_path),
        "candidate_manifest_sha256": _sha256_of_path(candidate_manifest_path),
        "candidate_manifest_sequence_sha256": str(candidate_manifest["sequence_sha256"]),
        "target_frame_deltas": target_frame_deltas,
        "target_frame_delta_count": len(target_frame_deltas),
        "preserved_frame_verifications": preserved_frame_verifications,
        "preserved_frame_verification_count": len(preserved_frame_verifications),
    }


def _write_transactional_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        if path.exists():
            raise ValueError(f"output ledger already exists: {path}")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent), delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
            handle.write("\n")
        if path.exists():
            raise ValueError(f"output ledger already exists: {path}")
        if os.name == "nt":
            os.rename(temp_path, path)
        else:
            os.link(temp_path, path)
            temp_path.unlink()
            temp_path = None
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--defect-report", required=True)
    parser.add_argument("--output-ledger", required=True)
    parser.add_argument("--candidate-manifest")
    args = parser.parse_args()

    try:
        repo_root = _resolve_repo_root()
        schemas = _load_required_schemas(repo_root)
        policy_path = repo_root / "Plan/10_REGISTRIES/wave27_frame_repair_policy.json"
        if not policy_path.is_file():
            raise ValueError(f"missing repair policy registry: {policy_path}")
        policy = _load_json(policy_path)
        policy_map = _load_failure_action_map(policy)
        _validate_policy_covers_hardcoded_actions(policy_map)
        policy_sha256 = _sha256_of_path(policy_path)

        manifest_path = Path(args.manifest).resolve()
        evidence_path = Path(args.evidence).resolve()
        defect_report_path = Path(args.defect_report).resolve()
        output_path = Path(args.output_ledger).resolve()

        manifest = _load_json(manifest_path)
        evidence = _load_json(evidence_path)
        defect_report = _load_json(defect_report_path)

        _validate_against_schema(manifest, schemas["manifest"], "manifest")
        _validate_against_schema(evidence, schemas["evidence"], "evidence")

        source_frames = _normalize_and_validate_manifest(manifest, manifest_path)
        _validate_evidence(evidence, expected_frame_count=len(source_frames))

        manifest_sequence_sha256 = str(manifest["sequence_sha256"])
        evidence_sha256 = _sha256_of_path(evidence_path)
        manifest_sha256 = _sha256_of_path(manifest_path)
        defect_report_sha256 = _sha256_of_path(defect_report_path)
        defects = _validate_defect_report(
            defect_report=defect_report,
            frame_count=len(source_frames),
            expected_manifest_sequence_sha256=manifest_sequence_sha256,
            expected_evidence_sha256=evidence_sha256,
            allowed_failures=set(policy_map.keys()),
        )

        by_frame: dict[int, list[dict[str, Any]]] = {}
        for defect in defects:
            by_frame.setdefault(defect["frame_index"], []).append(defect)
        failed_indexes = sorted(by_frame.keys())
        failed_index_set = set(failed_indexes)
        spans_raw = _group_contiguous_spans(failed_indexes)

        failed_frames: list[dict[str, Any]] = []
        passing_frames: list[dict[str, Any]] = []
        source_index_map = {frame["frame_index"]: frame for frame in source_frames}
        for frame in source_frames:
            index = frame["frame_index"]
            common = {
                "frame_index": index,
                "time_seconds": frame["time_seconds"],
                "original_artifact_path": frame["artifact_path"],
                "original_artifact_bytes": frame["artifact_bytes"],
                "original_artifact_sha256": frame["artifact_sha256"],
            }
            if index in failed_index_set:
                frame_defects = by_frame[index]
                frame_failures = [item["failure"] for item in frame_defects]
                mapped_actions = sorted(
                    {policy_map[failure] for failure in frame_failures}
                )
                entry = dict(common)
                entry["failures"] = frame_failures
                entry["policy_actions"] = mapped_actions
                notes = []
                for item in frame_defects:
                    for note_key in ("region_note", "evidence_note"):
                        if note_key in item:
                            notes.append(item[note_key])
                if notes:
                    entry["notes"] = notes
                failed_frames.append(entry)
            else:
                passing_frames.append(common)

        spans: list[dict[str, Any]] = []
        for span_indexes in spans_raw:
            span_failures = {
                defect["failure"] for frame_idx in span_indexes for defect in by_frame[frame_idx]
            }
            action, reason = _choose_span_action(span_failures, len(span_indexes), policy_map)
            spans.append(
                {
                    "start_frame_index": span_indexes[0],
                    "end_frame_index": span_indexes[-1],
                    "span_length": len(span_indexes),
                    "frame_indices": span_indexes,
                    "failures": sorted(span_failures),
                    "recommended_action": action,
                    "reason": reason,
                }
            )

        has_defects = bool(defects)

        final_flags = {
            "before_after_visual_review": False,
            "identity_environment_preservation_visual_pass": False,
            "runtime_repair_proof": False,
            "final_temporal_acceptance": False,
            "final_promotion": False,
        }

        candidate_validation: dict[str, Any] = {
            "status": "blocked_pending_repair_artifacts" if has_defects else "no_repair_required",
            "candidate_manifest_path": None,
            "candidate_manifest_sha256": None,
            "candidate_manifest_sequence_sha256": None,
            "candidate_manifest_provided": bool(args.candidate_manifest),
            "target_frame_deltas": [],
            "target_frame_delta_count": 0,
            "preserved_frame_verifications": [],
            "preserved_frame_verification_count": 0,
        }
        if args.candidate_manifest:
            candidate_path = Path(args.candidate_manifest).resolve()
            candidate_manifest = _load_json(candidate_path)
            _validate_against_schema(candidate_manifest, schemas["manifest"], "candidate_manifest")
            candidate_details = _validate_candidate_manifest(
                source_frames=source_frames,
                candidate_manifest=candidate_manifest,
                candidate_manifest_path=candidate_path,
                target_indexes=failed_index_set,
            )
            candidate_validation.update(candidate_details)
            candidate_validation["status"] = (
                "candidate_verified_technical_only" if has_defects else "no_repair_required"
            )

        ledger = {
            "schema_name": "wave27_frame_repair_ledger",
            "ledger_version": 1,
            "planning_status": (
                "repair_plan_candidate_verified"
                if candidate_validation["status"] == "candidate_verified_technical_only"
                else (
                    "repair_not_required"
                    if candidate_validation["status"] == "no_repair_required"
                    else "repair_plan_pending_candidate"
                )
            ),
            "frame_count": len(source_frames),
            "source_bindings": {
                "manifest_path": str(manifest_path),
                "manifest_sha256": manifest_sha256,
                "manifest_sequence_sha256": manifest_sequence_sha256,
                "temporal_evidence_path": str(evidence_path),
                "temporal_evidence_sha256": evidence_sha256,
                "defect_report_path": str(defect_report_path),
                "defect_report_sha256": defect_report_sha256,
                "normalized_defects_sha256": _sha256_of_json_payload(defects),
                "repair_policy_path": str(policy_path),
                "repair_policy_sha256": policy_sha256,
            },
            "failed_frames": failed_frames,
            "passing_frames": passing_frames,
            "repair_spans": spans,
            "candidate_validation": candidate_validation,
            "final_flags": final_flags,
        }

        _validate_against_schema(ledger, schemas["ledger"], "ledger")
        _write_transactional_json(output_path, ledger)
    except Exception as exc:
        _error(str(exc))
        return 1

    print(str(output_path))
    if has_defects and not args.candidate_manifest:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
