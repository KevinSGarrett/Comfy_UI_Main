#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path
from typing import Any


ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "manifest_id",
    "run_id",
    "scene_id",
    "shot_id",
    "take_id",
    "is_synthetic",
    "video_sha256",
    "timeline",
    "input_bindings",
    "dependency_authority",
    "runtime_authority",
    "contact_candidates",
    "visual_take_artifact",
    "contact_evidence_artifact",
}

ALLOWED_CONTACT_FIELDS = {
    "contact_id",
    "source_owner",
    "target_owner",
    "source_body_region",
    "target_body_region_or_surface",
    "object_or_surface",
    "source_entity_id",
    "target_entity_id",
    "source_material",
    "target_material",
    "approach_frame",
    "onset_frame",
    "peak_frame",
    "release_frame",
    "end_frame",
    "force_band",
    "visibility",
    "ownership_trusted",
    "confidence",
    "authority_ceiling",
    "decision",
    "decision_reason",
    "blockers",
    "evidence",
    "audio_expected",
    "min_expected_force_events",
    "max_expected_force_events",
}

ALLOWED_FORCE_BANDS = {"none", "light", "medium", "heavy"}
ALLOWED_VISIBILITY = {"visible", "partial", "occluded", "offscreen", "unknown"}
ALLOWED_AUTHORITY_CEILINGS = {"candidate", "technical", "certification"}
ALLOWED_DECISIONS = {"candidate", "blocked", "certified"}
SHA256_HEX_CHARS = set("0123456789abcdef")
INPUT_BINDING_KEYS = ("tracked_masks", "landmarks", "depth", "motion", "materials")
DEPENDENCY_KEYS = (
    "row085_complete",
    "row086_complete",
    "row087_complete",
    "row088_complete",
    "row089_complete",
)


def _assert_keys_exact(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(unknown)}")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_optional_string_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or null")
    stripped = value.strip()
    return stripped if stripped else None


def _expect_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _expect_non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return int(value)


def _expect_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return int(value)


def _expect_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError(f"{label} must be finite")
    return as_float


def _expect_sha256(value: Any, label: str) -> str:
    text = _expect_non_empty_string(value, label)
    if len(text) != 64 or any(ch not in SHA256_HEX_CHARS for ch in text):
        raise ValueError(f"{label} must be a lowercase 64-char sha256")
    return text


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _validate_timeline(raw_timeline: Any) -> dict[str, Any]:
    if not isinstance(raw_timeline, dict):
        raise ValueError("timeline must be an object")
    required = {
        "frame_rate",
        "frame_count",
        "frame_time_origin_seconds",
        "target_sample_rate_hz",
    }
    if set(raw_timeline.keys()) != required:
        missing = sorted(required - set(raw_timeline.keys()))
        extra = sorted(set(raw_timeline.keys()) - required)
        raise ValueError(f"timeline must include exactly {sorted(required)}; missing={missing} extra={extra}")
    frame_rate = _expect_number(raw_timeline.get("frame_rate"), "timeline.frame_rate")
    if frame_rate <= 0:
        raise ValueError("timeline.frame_rate must be > 0")
    frame_count = _expect_positive_int(raw_timeline.get("frame_count"), "timeline.frame_count")
    origin = _expect_number(
        raw_timeline.get("frame_time_origin_seconds"), "timeline.frame_time_origin_seconds"
    )
    sample_rate = _expect_positive_int(
        raw_timeline.get("target_sample_rate_hz"), "timeline.target_sample_rate_hz"
    )
    duration_seconds = frame_count / frame_rate
    return {
        "frame_rate": frame_rate,
        "frame_count": frame_count,
        "frame_time_origin_seconds": origin,
        "target_sample_rate_hz": sample_rate,
        "duration_seconds": duration_seconds,
    }


def _validate_binding(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    required = {"present", "path", "sha256", "bytes", "blocker"}
    if set(raw.keys()) != required:
        raise ValueError(f"{label} must include exactly {sorted(required)}")
    present = _expect_boolean(raw.get("present"), f"{label}.present")
    path = raw.get("path")
    sha256 = raw.get("sha256")
    size = raw.get("bytes")
    blocker = raw.get("blocker")
    if present:
        path_text = _expect_non_empty_string(path, f"{label}.path")
        sha_text = _expect_sha256(sha256, f"{label}.sha256")
        size_int = _expect_non_negative_int(size, f"{label}.bytes")
        if blocker is not None:
            raise ValueError(f"{label}.blocker must be null when present=true")
        return {
            "present": True,
            "path": path_text,
            "sha256": sha_text,
            "bytes": size_int,
            "blocker": None,
        }
    if path is not None or sha256 is not None or size is not None:
        raise ValueError(f"{label} absent binding must null path/sha256/bytes")
    blocker_text = _expect_non_empty_string(blocker, f"{label}.blocker")
    return {
        "present": False,
        "path": None,
        "sha256": None,
        "bytes": None,
        "blocker": blocker_text,
    }


def _validate_input_bindings(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("input_bindings must be an object")
    if set(raw.keys()) != set(INPUT_BINDING_KEYS):
        raise ValueError(f"input_bindings must include exactly {sorted(INPUT_BINDING_KEYS)}")
    return {key: _validate_binding(raw.get(key), f"input_bindings.{key}") for key in INPUT_BINDING_KEYS}


def _dependency_ready(dependency_authority: dict[str, Any]) -> tuple[bool, dict[str, bool], list[str]]:
    if set(dependency_authority.keys()) != set(DEPENDENCY_KEYS):
        raise ValueError(f"dependency_authority must include exactly {sorted(DEPENDENCY_KEYS)}")
    flags = {
        key: _expect_boolean(dependency_authority.get(key), f"dependency_authority.{key}")
        for key in DEPENDENCY_KEYS
    }
    ready = all(flags.values())
    holds = [key for key, value in flags.items() if not value]
    return ready, flags, holds


def _runtime_ready(runtime_authority: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    required = {"runtime_proof_present", "combined_frame_contact_audio_review_present"}
    if set(runtime_authority.keys()) != required:
        raise ValueError(f"runtime_authority must include exactly {sorted(required)}")
    flags = {
        key: _expect_boolean(runtime_authority.get(key), f"runtime_authority.{key}")
        for key in sorted(required)
    }
    return all(flags.values()), flags


def _frame_to_seconds(frame: int, timeline: dict[str, Any]) -> float:
    return timeline["frame_time_origin_seconds"] + (frame / timeline["frame_rate"])


def _seconds_to_sample(seconds: float, timeline: dict[str, Any]) -> int:
    return int(round(seconds * timeline["target_sample_rate_hz"]))


def _compile_contact(
    *,
    raw: dict[str, Any],
    index: int,
    timeline: dict[str, Any],
    dependency_ready: bool,
    runtime_ready: bool,
    input_bindings: dict[str, Any],
) -> dict[str, Any]:
    _assert_keys_exact(raw, ALLOWED_CONTACT_FIELDS, f"contact_candidates[{index}]")
    label = f"contact_candidates[{index}]"

    contact_id = _expect_non_empty_string(raw.get("contact_id"), f"{label}.contact_id")
    source_owner = _expect_optional_string_or_none(raw.get("source_owner"), f"{label}.source_owner")
    target_owner = _expect_optional_string_or_none(raw.get("target_owner"), f"{label}.target_owner")
    source_region = _expect_optional_string_or_none(
        raw.get("source_body_region"), f"{label}.source_body_region"
    )
    target_region = _expect_optional_string_or_none(
        raw.get("target_body_region_or_surface"), f"{label}.target_body_region_or_surface"
    )
    object_or_surface = _expect_optional_string_or_none(
        raw.get("object_or_surface"), f"{label}.object_or_surface"
    )

    approach_raw = raw.get("approach_frame")
    approach_frame = (
        None
        if approach_raw is None
        else _expect_non_negative_int(approach_raw, f"{label}.approach_frame")
    )
    onset_frame = _expect_non_negative_int(raw.get("onset_frame"), f"{label}.onset_frame")
    peak_frame = _expect_non_negative_int(raw.get("peak_frame"), f"{label}.peak_frame")
    release_frame = _expect_non_negative_int(raw.get("release_frame"), f"{label}.release_frame")
    end_frame = _expect_non_negative_int(raw.get("end_frame"), f"{label}.end_frame")

    ordered = [onset_frame, peak_frame, release_frame, end_frame]
    if approach_frame is not None:
        ordered = [approach_frame, *ordered]
    if ordered != sorted(ordered):
        raise ValueError(f"{label} phase frames must be non-decreasing")
    if end_frame >= timeline["frame_count"]:
        raise ValueError(f"{label}.end_frame must be < timeline.frame_count")

    force_band = _expect_non_empty_string(raw.get("force_band"), f"{label}.force_band")
    if force_band not in ALLOWED_FORCE_BANDS:
        raise ValueError(f"{label}.force_band must be one of {sorted(ALLOWED_FORCE_BANDS)}")
    visibility = _expect_non_empty_string(raw.get("visibility"), f"{label}.visibility")
    if visibility not in ALLOWED_VISIBILITY:
        raise ValueError(f"{label}.visibility must be one of {sorted(ALLOWED_VISIBILITY)}")
    ownership_trusted = _expect_boolean(raw.get("ownership_trusted"), f"{label}.ownership_trusted")
    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    authority_ceiling = _expect_non_empty_string(
        raw.get("authority_ceiling"), f"{label}.authority_ceiling"
    )
    if authority_ceiling not in ALLOWED_AUTHORITY_CEILINGS:
        raise ValueError(
            f"{label}.authority_ceiling must be one of {sorted(ALLOWED_AUTHORITY_CEILINGS)}"
        )
    decision = _expect_non_empty_string(raw.get("decision"), f"{label}.decision")
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"{label}.decision must be one of {sorted(ALLOWED_DECISIONS)}")
    decision_reason = _expect_non_empty_string(
        raw.get("decision_reason"), f"{label}.decision_reason"
    )

    blockers_raw = raw.get("blockers")
    if not isinstance(blockers_raw, list):
        raise ValueError(f"{label}.blockers must be an array")
    blockers = [
        _expect_non_empty_string(item, f"{label}.blockers[{idx}]")
        for idx, item in enumerate(blockers_raw)
    ]

    evidence_raw = raw.get("evidence")
    if not isinstance(evidence_raw, list) or not evidence_raw:
        raise ValueError(f"{label}.evidence must be a non-empty list")
    evidence = []
    for evidence_idx, entry in enumerate(evidence_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{label}.evidence[{evidence_idx}] must be an object")
        evidence.append(entry)

    missing_inputs = [
        key for key, binding in input_bindings.items() if not binding["present"]
    ]
    if missing_inputs:
        blockers.append(f"missing_input_bindings:{','.join(missing_inputs)}")

    if source_owner is None or target_owner is None:
        ownership_trusted = False
        blockers.append("unowned_source_or_target")
    if not ownership_trusted and decision == "certified":
        raise ValueError(f"{label} cannot certify without ownership_trusted=true")
    if (source_owner is None or target_owner is None) and decision == "certified":
        raise ValueError(f"{label} cannot certify with null source_owner/target_owner")

    if not dependency_ready:
        if decision == "certified":
            raise ValueError(f"{label} cannot decision=certified while dependencies incomplete")
        if authority_ceiling != "candidate":
            raise ValueError(
                f"{label} must remain candidate ceiling while dependencies incomplete"
            )
        blockers.append("dependency_authority_unsatisfied")
    if not runtime_ready and authority_ceiling == "certification":
        raise ValueError(f"{label} cannot claim certification without runtime+review authority")
    if decision == "certified" and authority_ceiling != "certification":
        raise ValueError(f"{label} certified decision requires authority_ceiling=certification")
    if decision == "blocked" and not blockers:
        raise ValueError(f"{label} blocked decision requires at least one blocker")

    onset_seconds = _frame_to_seconds(onset_frame, timeline)
    peak_seconds = _frame_to_seconds(peak_frame, timeline)
    release_seconds = _frame_to_seconds(release_frame, timeline)
    duration_frames = end_frame - onset_frame
    duration_seconds = duration_frames / timeline["frame_rate"]
    uncertainty_frames = 0.0 if dependency_ready and ownership_trusted else 1.0

    evidence.append(
        {
            "kind": "contact_inference_authority_gate",
            "dependency_ready": dependency_ready,
            "runtime_ready": runtime_ready,
            "decision": decision,
            "authority_ceiling": authority_ceiling,
        }
    )

    return {
        "contact_id": contact_id,
        "source_owner": source_owner,
        "target_owner": target_owner,
        "source_body_region": source_region,
        "target_body_region_or_surface": target_region,
        "object_or_surface": object_or_surface,
        "source_entity_id": _expect_optional_string_or_none(
            raw.get("source_entity_id"), f"{label}.source_entity_id"
        ),
        "target_entity_id": _expect_optional_string_or_none(
            raw.get("target_entity_id"), f"{label}.target_entity_id"
        ),
        "source_material": _expect_optional_string_or_none(
            raw.get("source_material"), f"{label}.source_material"
        ),
        "target_material": _expect_optional_string_or_none(
            raw.get("target_material"), f"{label}.target_material"
        ),
        "audio_expected": _expect_boolean(raw.get("audio_expected"), f"{label}.audio_expected")
        if "audio_expected" in raw
        else force_band != "none",
        "min_expected_force_events": _expect_non_negative_int(
            raw.get("min_expected_force_events"), f"{label}.min_expected_force_events"
        )
        if "min_expected_force_events" in raw
        else (0 if force_band == "none" else 1),
        "max_expected_force_events": _expect_non_negative_int(
            raw.get("max_expected_force_events"), f"{label}.max_expected_force_events"
        )
        if "max_expected_force_events" in raw
        else (0 if force_band == "none" else 1),
        "phases": {
            "approach_frame": approach_frame,
            "onset_frame": onset_frame,
            "peak_frame": peak_frame,
            "release_frame": release_frame,
            "end_frame": end_frame,
            "onset_seconds": round(onset_seconds, 6),
            "peak_seconds": round(peak_seconds, 6),
            "release_seconds": round(release_seconds, 6),
            "onset_sample": _seconds_to_sample(onset_seconds, timeline),
            "peak_sample": _seconds_to_sample(peak_seconds, timeline),
            "release_sample": _seconds_to_sample(release_seconds, timeline),
            "duration_frames": duration_frames,
            "duration_seconds": round(duration_seconds, 6),
            "uncertainty_frames": uncertainty_frames,
        },
        "force_band": force_band,
        "visibility": visibility,
        "ownership_trusted": ownership_trusted,
        "confidence": confidence,
        "authority_ceiling": authority_ceiling,
        "decision": decision,
        "decision_reason": decision_reason,
        "blockers": sorted(set(blockers)),
        "evidence": evidence,
    }


def _validate_media_artifact(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    required = {"path", "sha256", "bytes", "media_type"}
    if set(raw.keys()) != required:
        raise ValueError(f"{label} must include exactly {sorted(required)}")
    return {
        "path": _expect_non_empty_string(raw.get("path"), f"{label}.path"),
        "sha256": _expect_sha256(raw.get("sha256"), f"{label}.sha256"),
        "bytes": _expect_non_negative_int(raw.get("bytes"), f"{label}.bytes"),
        "media_type": _expect_non_empty_string(raw.get("media_type"), f"{label}.media_type"),
    }


def _project_visual_contact_manifest(
    *,
    payload: dict[str, Any],
    timeline: dict[str, Any],
    contacts: list[dict[str, Any]],
    dependency_ready: bool,
    runtime_ready: bool,
) -> dict[str, Any]:
    visual_take = _validate_media_artifact(payload.get("visual_take_artifact"), "visual_take_artifact")
    contact_evidence = _validate_media_artifact(
        payload.get("contact_evidence_artifact"), "contact_evidence_artifact"
    )
    edges: list[dict[str, Any]] = []
    for contact in contacts:
        if contact["decision"] == "blocked" and (
            contact["source_owner"] is None or contact["target_owner"] is None
        ):
            continue
        if contact["source_owner"] is None or contact["target_owner"] is None:
            raise ValueError(
                f"contact {contact['contact_id']} cannot project visual edge without owners"
            )
        source_entity = contact["source_entity_id"] or (
            f"{contact['source_owner']}:{contact['source_body_region'] or 'region'}"
        )
        target_entity = contact["target_entity_id"] or (
            f"{contact['target_owner']}:{contact['target_body_region_or_surface'] or contact['object_or_surface'] or 'surface'}"
        )
        edges.append(
            {
                "contact_edge_id": contact["contact_id"],
                "source_entity_id": source_entity,
                "target_entity_id": target_entity,
                "source_owner_id": contact["source_owner"],
                "target_owner_id": contact["target_owner"],
                "source_material": contact["source_material"] or "unknown",
                "target_material": contact["target_material"] or "unknown",
                "visual_force_intensity": contact["force_band"],
                "start_frame": contact["phases"]["onset_frame"],
                "end_frame": contact["phases"]["end_frame"],
                "audio_expected": contact["audio_expected"],
                "min_expected_force_events": contact["min_expected_force_events"],
                "max_expected_force_events": contact["max_expected_force_events"],
            }
        )

    production_trust = dependency_ready and runtime_ready and all(
        contact["decision"] == "certified" for contact in contacts if contact["decision"] != "blocked"
    )
    if not dependency_ready or not runtime_ready:
        production_trust = False

    return {
        "run_id": _expect_non_empty_string(payload.get("run_id"), "run_id"),
        "scene_id": _expect_non_empty_string(payload.get("scene_id"), "scene_id"),
        "shot_id": _expect_non_empty_string(payload.get("shot_id"), "shot_id"),
        "take_id": _expect_non_empty_string(payload.get("take_id"), "take_id"),
        "is_synthetic": _expect_boolean(payload.get("is_synthetic"), "is_synthetic"),
        "frame_rate": timeline["frame_rate"],
        "frame_time_origin_seconds": timeline["frame_time_origin_seconds"],
        "visual_take_artifact": visual_take,
        "contact_evidence_artifact": contact_evidence,
        "contact_authority": {
            "authority_scope": "body_contact",
            "gold_mask_dependency_status": "cleared" if dependency_ready else "missing",
            "evidence_authority_class": (
                "gold_mask_validated" if dependency_ready and runtime_ready else "untrusted"
            ),
            "production_trust_claim": production_trust,
        },
        "contact_edges": edges,
    }


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "input.schema_version")
    if schema_version != "1.0":
        raise ValueError("input.schema_version must equal 1.0")

    timeline = _validate_timeline(payload.get("timeline"))
    input_bindings = _validate_input_bindings(payload.get("input_bindings"))

    dependency_authority_raw = payload.get("dependency_authority")
    if not isinstance(dependency_authority_raw, dict):
        raise ValueError("dependency_authority must be an object")
    dependency_ready, dependency_flags, dependency_holds = _dependency_ready(dependency_authority_raw)

    runtime_authority_raw = payload.get("runtime_authority")
    if not isinstance(runtime_authority_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_ready, runtime_flags = _runtime_ready(runtime_authority_raw)

    raw_contacts = payload.get("contact_candidates")
    if not isinstance(raw_contacts, list) or not raw_contacts:
        raise ValueError("contact_candidates must be a non-empty list")

    seen_ids: set[str] = set()
    contacts: list[dict[str, Any]] = []
    for idx, raw_contact in enumerate(raw_contacts):
        if not isinstance(raw_contact, dict):
            raise ValueError(f"contact_candidates[{idx}] must be an object")
        compiled = _compile_contact(
            raw=raw_contact,
            index=idx,
            timeline=timeline,
            dependency_ready=dependency_ready,
            runtime_ready=runtime_ready,
            input_bindings=input_bindings,
        )
        if compiled["contact_id"] in seen_ids:
            raise ValueError(f"duplicate contact_id detected: {compiled['contact_id']}")
        seen_ids.add(compiled["contact_id"])
        # Strip projection-only helper fields from ownership events.
        ownership_event = {
            key: value
            for key, value in compiled.items()
            if key
            not in {
                "source_entity_id",
                "target_entity_id",
                "source_material",
                "target_material",
                "audio_expected",
                "min_expected_force_events",
                "max_expected_force_events",
            }
        }
        contacts.append(ownership_event)
        # Keep helpers on a side channel for visual projection.
        ownership_event["_projection"] = {
            "source_entity_id": compiled["source_entity_id"],
            "target_entity_id": compiled["target_entity_id"],
            "source_material": compiled["source_material"],
            "target_material": compiled["target_material"],
            "audio_expected": compiled["audio_expected"],
            "min_expected_force_events": compiled["min_expected_force_events"],
            "max_expected_force_events": compiled["max_expected_force_events"],
        }

    candidate_count = sum(1 for contact in contacts if contact["decision"] == "candidate")
    blocked_count = sum(1 for contact in contacts if contact["decision"] == "blocked")
    certified_count = sum(1 for contact in contacts if contact["decision"] == "certified")
    if candidate_count + blocked_count + certified_count != len(contacts):
        raise ValueError("authority summary invariant failed")

    hold_reasons: list[str] = []
    if dependency_holds:
        hold_reasons.append("dependencies_incomplete:" + ",".join(dependency_holds))
    if not runtime_ready:
        hold_reasons.append("runtime_or_combined_review_absent")
    missing_inputs = [key for key, binding in input_bindings.items() if not binding["present"]]
    if missing_inputs:
        hold_reasons.append("missing_input_bindings:" + ",".join(missing_inputs))

    production_trust_allowed = dependency_ready and runtime_ready and certified_count > 0
    visual_projection_contacts = []
    for contact in contacts:
        projection = contact.pop("_projection")
        visual_projection_contacts.append({**contact, **projection})

    visual_manifest = _project_visual_contact_manifest(
        payload=payload,
        timeline=timeline,
        contacts=visual_projection_contacts,
        dependency_ready=dependency_ready,
        runtime_ready=runtime_ready,
    )
    if visual_manifest["contact_authority"]["production_trust_claim"] and not production_trust_allowed:
        raise ValueError("production_trust_claim cannot be true under hold")

    return {
        "schema_version": "1.0",
        "manifest_id": _expect_non_empty_string(payload.get("manifest_id"), "manifest_id"),
        "run_id": _expect_non_empty_string(payload.get("run_id"), "run_id"),
        "scene_id": _expect_non_empty_string(payload.get("scene_id"), "scene_id"),
        "shot_id": _expect_non_empty_string(payload.get("shot_id"), "shot_id"),
        "take_id": _expect_non_empty_string(payload.get("take_id"), "take_id"),
        "is_synthetic": _expect_boolean(payload.get("is_synthetic"), "is_synthetic"),
        "video_sha256": _expect_sha256(payload.get("video_sha256"), "video_sha256"),
        "timeline": timeline,
        "input_bindings": input_bindings,
        "dependency_authority": {
            **dependency_flags,
            "all_dependencies_complete": dependency_ready,
        },
        "runtime_authority": {
            **runtime_flags,
            "runtime_ready": runtime_ready,
        },
        "contacts": contacts,
        "authority_summary": {
            "contact_count": len(contacts),
            "candidate_count": candidate_count,
            "blocked_count": blocked_count,
            "certified_count": certified_count,
            "production_trust_allowed": production_trust_allowed,
            "hold_reasons": hold_reasons,
        },
        "visual_contact_manifest": visual_manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile a fail-closed Row090 contact inference ownership manifest."
    )
    parser.add_argument("--input", required=True, help="Contact inference packet JSON path")
    parser.add_argument("--output", required=True, help="Compiled ownership manifest JSON path")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("input must be an object")
        manifest = compile_manifest(payload)
        _write_json_atomic(output_path, manifest)
    except Exception as exc:  # noqa: BLE001 - CLI fail-closed boundary
        print(f"ERROR: {exc}")
        return 1
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
