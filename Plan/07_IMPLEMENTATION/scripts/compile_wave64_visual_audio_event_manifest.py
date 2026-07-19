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
    "video_sha256",
    "scene_state_sha256",
    "timeline",
    "detectors",
    "traceability_events",
    "dependency_authority",
    "runtime_authority",
    "rights_decision_sha256",
}

ALLOWED_TRACEABILITY_EVENT_FIELDS = {
    "traceability_id",
    "event_id",
    "event_type",
    "source_owner",
    "target_owner",
    "source_body_part",
    "target_body_part",
    "start_frame",
    "anchor_frame",
    "end_frame",
    "anchor_seconds",
    "anchor_sample",
    "material",
    "footwear",
    "force_band",
    "expected_layers",
    "confidence",
    "authority_ceiling",
    "evidence",
    "decision",
    "decision_reason",
}

ALLOWED_DECISIONS = {"cover", "silent", "blocked"}
ALLOWED_AUTHORITY_CEILINGS = {"candidate", "technical", "certification"}
SHA256_HEX_CHARS = set("0123456789abcdef")


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


def _parse_time_base_fps(time_base: str) -> float:
    parts = time_base.split("/")
    if len(parts) != 2:
        raise ValueError("timeline.time_base must be in numerator/denominator format")
    numerator = _expect_positive_int(int(parts[0]), "timeline.time_base.numerator")
    denominator = _expect_positive_int(int(parts[1]), "timeline.time_base.denominator")
    return numerator / float(denominator)


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


def _validate_timeline(raw_timeline: Any) -> tuple[dict[str, Any], float]:
    if not isinstance(raw_timeline, dict):
        raise ValueError("timeline must be an object")
    required_keys = {"time_base", "frame_count", "duration_seconds", "target_sample_rate_hz"}
    if set(raw_timeline.keys()) != required_keys:
        missing = sorted(required_keys - set(raw_timeline.keys()))
        extra = sorted(set(raw_timeline.keys()) - required_keys)
        raise ValueError(
            f"timeline must include exactly {sorted(required_keys)}; missing={missing} extra={extra}"
        )
    time_base = _expect_non_empty_string(raw_timeline.get("time_base"), "timeline.time_base")
    fps = _parse_time_base_fps(time_base)
    frame_count = _expect_positive_int(raw_timeline.get("frame_count"), "timeline.frame_count")
    duration_seconds = _expect_number(raw_timeline.get("duration_seconds"), "timeline.duration_seconds")
    if duration_seconds <= 0:
        raise ValueError("timeline.duration_seconds must be > 0")
    # Bind declared duration to Row084-style frame/time_base identity so fixture and
    # declared packets cannot drift from the canonical clock without failing closed.
    expected_duration = frame_count / fps
    if abs(duration_seconds - expected_duration) > (1.0 / fps):
        raise ValueError(
            "timeline.duration_seconds disagrees with frame_count/time_base "
            f"(expected≈{expected_duration}, observed={duration_seconds})"
        )
    sample_rate = _expect_positive_int(raw_timeline.get("target_sample_rate_hz"), "timeline.target_sample_rate_hz")
    return {
        "time_base": time_base,
        "frame_count": frame_count,
        "duration_seconds": duration_seconds,
        "target_sample_rate_hz": sample_rate,
    }, fps


def _validate_detectors(raw_detectors: Any) -> list[dict[str, str]]:
    if not isinstance(raw_detectors, list) or not raw_detectors:
        raise ValueError("detectors must be a non-empty list")
    detectors: list[dict[str, str]] = []
    for idx, detector in enumerate(raw_detectors):
        if not isinstance(detector, dict):
            raise ValueError(f"detectors[{idx}] must be an object")
        if set(detector.keys()) != {"name", "revision"}:
            raise ValueError(f"detectors[{idx}] must contain only name/revision")
        detectors.append(
            {
                "name": _expect_non_empty_string(detector.get("name"), f"detectors[{idx}].name"),
                "revision": _expect_non_empty_string(detector.get("revision"), f"detectors[{idx}].revision"),
            }
        )
    return detectors


def _runtime_ready(runtime_authority: dict[str, Any]) -> bool:
    runtime_proof = _expect_boolean(runtime_authority.get("runtime_proof_present"), "runtime_authority.runtime_proof_present")
    audio_review = _expect_boolean(runtime_authority.get("audio_review_present"), "runtime_authority.audio_review_present")
    combined_review = _expect_boolean(
        runtime_authority.get("combined_frame_contact_audio_review_present"),
        "runtime_authority.combined_frame_contact_audio_review_present",
    )
    return runtime_proof and audio_review and combined_review


def _dependency_ready(dependency_authority: dict[str, Any]) -> bool:
    row084 = _expect_boolean(dependency_authority.get("row084_complete"), "dependency_authority.row084_complete")
    row090 = _expect_boolean(dependency_authority.get("row090_complete"), "dependency_authority.row090_complete")
    for key in ("row084_evidence_sha256", "row090_evidence_sha256"):
        if key in dependency_authority and dependency_authority.get(key) is not None:
            _expect_sha256(dependency_authority.get(key), f"dependency_authority.{key}")
    return row084 and row090


def _compile_traceability_event(
    *,
    raw_event: dict[str, Any],
    index: int,
    timeline: dict[str, Any],
    fps: float,
    dependency_ready: bool,
    runtime_ready: bool,
) -> tuple[dict[str, Any], str]:
    _assert_keys_exact(raw_event, ALLOWED_TRACEABILITY_EVENT_FIELDS, f"traceability_events[{index}]")

    start_frame = _expect_non_negative_int(raw_event.get("start_frame"), f"traceability_events[{index}].start_frame")
    anchor_frame = _expect_non_negative_int(raw_event.get("anchor_frame"), f"traceability_events[{index}].anchor_frame")
    end_frame = _expect_non_negative_int(raw_event.get("end_frame"), f"traceability_events[{index}].end_frame")
    if not (start_frame <= anchor_frame <= end_frame):
        raise ValueError(f"traceability_events[{index}] must satisfy start_frame<=anchor_frame<=end_frame")
    if end_frame >= timeline["frame_count"]:
        raise ValueError(
            f"traceability_events[{index}] end_frame must be < timeline.frame_count ({timeline['frame_count']})"
        )

    computed_anchor_seconds = anchor_frame / fps
    computed_anchor_sample = int(round(computed_anchor_seconds * timeline["target_sample_rate_hz"]))
    provided_anchor_seconds = raw_event.get("anchor_seconds")
    if provided_anchor_seconds is not None:
        observed = _expect_number(provided_anchor_seconds, f"traceability_events[{index}].anchor_seconds")
        if abs(observed - computed_anchor_seconds) > (1.0 / timeline["target_sample_rate_hz"]):
            raise ValueError(
                f"traceability_events[{index}].anchor_seconds disagrees with frame anchor"
            )
    provided_anchor_sample = raw_event.get("anchor_sample")
    if provided_anchor_sample is not None:
        observed_sample = _expect_non_negative_int(
            provided_anchor_sample, f"traceability_events[{index}].anchor_sample"
        )
        if abs(observed_sample - computed_anchor_sample) > 1:
            raise ValueError(
                f"traceability_events[{index}].anchor_sample disagrees with frame/sample conversion"
            )

    expected_layers_raw = raw_event.get("expected_layers")
    if not isinstance(expected_layers_raw, list) or not expected_layers_raw:
        raise ValueError(f"traceability_events[{index}].expected_layers must be a non-empty list")
    expected_layers = [
        _expect_non_empty_string(layer, f"traceability_events[{index}].expected_layers[{layer_idx}]")
        for layer_idx, layer in enumerate(expected_layers_raw)
    ]

    evidence_raw = raw_event.get("evidence")
    if not isinstance(evidence_raw, list) or not evidence_raw:
        raise ValueError(f"traceability_events[{index}].evidence must be a non-empty list")
    evidence: list[dict[str, Any]] = []
    for evidence_idx, entry in enumerate(evidence_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"traceability_events[{index}].evidence[{evidence_idx}] must be an object")
        evidence.append(entry)

    decision = _expect_non_empty_string(raw_event.get("decision"), f"traceability_events[{index}].decision")
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(
            f"traceability_events[{index}].decision must be one of {sorted(ALLOWED_DECISIONS)}"
        )
    decision_reason = _expect_non_empty_string(
        raw_event.get("decision_reason"), f"traceability_events[{index}].decision_reason"
    )

    authority_ceiling = _expect_non_empty_string(
        raw_event.get("authority_ceiling"), f"traceability_events[{index}].authority_ceiling"
    )
    if authority_ceiling not in ALLOWED_AUTHORITY_CEILINGS:
        raise ValueError(
            f"traceability_events[{index}].authority_ceiling must be one of {sorted(ALLOWED_AUTHORITY_CEILINGS)}"
        )
    if (not dependency_ready) and decision == "cover":
        raise ValueError(
            f"traceability_events[{index}] cannot be decision=cover while dependency authority is unsatisfied"
        )
    if (not dependency_ready) and authority_ceiling != "candidate":
        raise ValueError(
            f"traceability_events[{index}] must remain candidate ceiling while dependency authority is unsatisfied"
        )
    if (not runtime_ready) and authority_ceiling == "certification":
        raise ValueError(
            f"traceability_events[{index}] cannot claim certification without runtime+review authority"
        )

    evidence.append(
        {
            "kind": "traceability_decision",
            "decision": decision,
            "reason": decision_reason,
            "dependency_ready": dependency_ready,
            "runtime_ready": runtime_ready,
        }
    )

    event = {
        "event_id": _expect_non_empty_string(raw_event.get("event_id"), f"traceability_events[{index}].event_id"),
        "event_type": _expect_non_empty_string(raw_event.get("event_type"), f"traceability_events[{index}].event_type"),
        "source_owner": _expect_optional_string_or_none(raw_event.get("source_owner"), f"traceability_events[{index}].source_owner"),
        "target_owner": _expect_optional_string_or_none(raw_event.get("target_owner"), f"traceability_events[{index}].target_owner"),
        "source_body_part": _expect_optional_string_or_none(
            raw_event.get("source_body_part"), f"traceability_events[{index}].source_body_part"
        ),
        "target_body_part": _expect_optional_string_or_none(
            raw_event.get("target_body_part"), f"traceability_events[{index}].target_body_part"
        ),
        "start_frame": start_frame,
        "anchor_frame": anchor_frame,
        "end_frame": end_frame,
        "anchor_seconds": round(computed_anchor_seconds, 6),
        "anchor_sample": computed_anchor_sample,
        "material": _expect_non_empty_string(raw_event.get("material"), f"traceability_events[{index}].material"),
        "footwear": _expect_optional_string_or_none(raw_event.get("footwear"), f"traceability_events[{index}].footwear"),
        "force_band": _expect_non_empty_string(raw_event.get("force_band"), f"traceability_events[{index}].force_band"),
        "expected_layers": expected_layers,
        "confidence": _expect_number(raw_event.get("confidence"), f"traceability_events[{index}].confidence"),
        "authority_ceiling": authority_ceiling,
        "evidence": evidence,
    }
    confidence = float(event["confidence"])
    if confidence < 0 or confidence > 1:
        raise ValueError(f"traceability_events[{index}].confidence must be within [0, 1]")
    return event, decision


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "input.schema_version")
    if schema_version != "1.0":
        raise ValueError("input.schema_version must equal 1.0")
    timeline, fps = _validate_timeline(payload.get("timeline"))
    detectors = _validate_detectors(payload.get("detectors"))

    dependency_authority = payload.get("dependency_authority")
    if not isinstance(dependency_authority, dict):
        raise ValueError("dependency_authority must be an object")
    runtime_authority = payload.get("runtime_authority")
    if not isinstance(runtime_authority, dict):
        raise ValueError("runtime_authority must be an object")
    dependency_ready = _dependency_ready(dependency_authority)
    runtime_ready = _runtime_ready(runtime_authority)

    raw_events = payload.get("traceability_events")
    if not isinstance(raw_events, list) or not raw_events:
        raise ValueError("traceability_events must be a non-empty list")

    seen_event_ids: set[str] = set()
    seen_traceability_ids: set[str] = set()
    compiled_events: list[dict[str, Any]] = []
    covered_events = 0
    silent_events = 0
    blocked_events = 0
    for idx, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, dict):
            raise ValueError(f"traceability_events[{idx}] must be an object")
        traceability_id = _expect_non_empty_string(
            raw_event.get("traceability_id"), f"traceability_events[{idx}].traceability_id"
        )
        if traceability_id in seen_traceability_ids:
            raise ValueError(f"duplicate traceability_id detected: {traceability_id}")
        seen_traceability_ids.add(traceability_id)

        compiled, decision = _compile_traceability_event(
            raw_event=raw_event,
            index=idx,
            timeline=timeline,
            fps=fps,
            dependency_ready=dependency_ready,
            runtime_ready=runtime_ready,
        )
        if compiled["event_id"] in seen_event_ids:
            raise ValueError(f"duplicate event_id detected: {compiled['event_id']}")
        seen_event_ids.add(compiled["event_id"])

        if decision == "cover":
            covered_events += 1
        elif decision == "silent":
            silent_events += 1
        elif decision == "blocked":
            blocked_events += 1
        compiled_events.append(compiled)

    required_events = len(compiled_events)
    if required_events != covered_events + silent_events + blocked_events:
        raise ValueError("coverage invariant failed: required != covered + silent + blocked")

    compiled_events.sort(key=lambda event: (event["anchor_frame"], event["event_id"]))
    return {
        "schema_version": "1.0",
        "manifest_id": _expect_non_empty_string(payload.get("manifest_id"), "input.manifest_id"),
        "video_sha256": _expect_sha256(payload.get("video_sha256"), "input.video_sha256"),
        "scene_state_sha256": _expect_optional_string_or_none(payload.get("scene_state_sha256"), "input.scene_state_sha256"),
        "timeline": timeline,
        "detectors": detectors,
        "events": compiled_events,
        "coverage": {
            "required_events": required_events,
            "covered_events": covered_events,
            "silent_events": silent_events,
            "blocked_events": blocked_events,
        },
        "rights_decision_sha256": _expect_sha256(
            payload.get("rights_decision_sha256"), "input.rights_decision_sha256"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Traceability packet JSON path")
    parser.add_argument("--output", required=True, help="Compiled manifest JSON path")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("input must be an object")
        manifest = compile_manifest(payload)
        _write_json_atomic(output_path, manifest)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
