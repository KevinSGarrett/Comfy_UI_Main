#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
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
REGISTRY_RELATIVE = {
    "scoring_rules": "Plan/10_REGISTRIES/wave27_temporal_qa_scoring_rules.json",
    "repair_policy": "Plan/10_REGISTRIES/wave27_frame_repair_policy.json",
    "loop_profile": "Plan/10_REGISTRIES/wave26_gif_loop_profile_registry.json",
    "engine_registry": "Plan/10_REGISTRIES/wave27_video_engine_registry.json",
}
ALLOWED_INPUT_FIELDS = {
    "run_id",
    "engine_name",
    "frame_count",
    "loop_profile",
    "identity_drift_score",
    "flicker_score",
    "pose_continuity_score",
    "depth_continuity_score",
    "contact_continuity_score",
    "export_integrity_score",
    "hard_failures",
    "repair_events",
    "promotion_decision",
}


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _resolve_repo_root(start: Path) -> Path:
    candidate = start.resolve()
    if (candidate / "Plan").is_dir():
        return candidate
    if candidate.name == "Plan" and (candidate / "10_REGISTRIES").is_dir():
        return candidate.parent
    raise ValueError(f"unable to resolve repository root from: {candidate}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)


def _load_registries(repo_root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for key, relative in REGISTRY_RELATIVE.items():
        path = repo_root / relative
        if not path.is_file():
            raise ValueError(f"required registry missing: {path}")
        loaded[key] = _load_json(path)
    return loaded


def _as_score(src: dict[str, Any], key: str) -> float:
    value = src.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    score = float(value)
    if not math.isfinite(score) or score < 0 or score > 100:
        raise ValueError(f"{key} must be finite in [0, 100]")
    return score


def _as_nonempty_str(src: dict[str, Any], key: str) -> str:
    value = src.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _normalize_repair_events(
    src: dict[str, Any], frame_count: int, allowed_actions: set[str]
) -> list[dict[str, Any]]:
    events = src.get("repair_events")
    if not isinstance(events, list):
        raise ValueError("repair_events must be a list")
    normalized: list[dict[str, Any]] = []
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"repair_events[{idx}] must be an object")
        allowed_keys = {"frame_index", "event_type", "action", "status"}
        unknown = sorted(set(event.keys()) - allowed_keys)
        if unknown:
            raise ValueError(f"repair_events[{idx}] has unknown fields: {', '.join(unknown)}")
        frame_index = event["frame_index"]
        if (
            not isinstance(frame_index, int)
            or isinstance(frame_index, bool)
            or frame_index < 0
            or frame_index >= frame_count
        ):
            raise ValueError(f"repair_events[{idx}].frame_index out of range")
        action_value = event.get("action")
        event_type_value = event.get("event_type")
        if (
            action_value is not None
            and event_type_value is not None
            and action_value != event_type_value
        ):
            raise ValueError(f"repair_events[{idx}].action and event_type must match")
        action_raw = action_value if action_value is not None else event_type_value
        if not isinstance(action_raw, str) or not action_raw.strip():
            raise ValueError(f"repair_events[{idx}].action must be non-empty string")
        action = action_raw.strip()
        if action not in allowed_actions:
            raise ValueError(f"repair_events[{idx}].action not allowed by repair policy: {action}")
        status = event["status"]
        if status not in REPAIR_EVENT_STATUS:
            allowed = ", ".join(sorted(REPAIR_EVENT_STATUS))
            raise ValueError(f"repair_events[{idx}].status must be one of: {allowed}")
        normalized.append(
            {
                "frame_index": frame_index,
                "event_type": action,
                "action": action,
                "status": status,
            }
        )
    normalized.sort(key=lambda item: (item["frame_index"], item["action"], item["status"]))
    return normalized


def _compute_dimension_scores(src: dict[str, Any]) -> dict[str, float]:
    identity_drift = _as_score(src, "identity_drift_score")
    flicker = _as_score(src, "flicker_score")
    pose_continuity = _as_score(src, "pose_continuity_score")
    depth_continuity = _as_score(src, "depth_continuity_score")
    contact_continuity = _as_score(src, "contact_continuity_score")
    export_integrity = _as_score(src, "export_integrity_score")
    return {
        "identity_drift": round(max(0.0, 100.0 - identity_drift), 2),
        "flicker": round(max(0.0, 100.0 - flicker), 2),
        "pose_continuity": pose_continuity,
        "depth_continuity": depth_continuity,
        "contact_continuity": contact_continuity,
        "export_integrity": export_integrity,
    }


def _derive_decision(
    overall: float,
    promote_threshold: float,
    repair_threshold: float,
    hard_fail_hit: bool,
    policy_consistent: bool,
    repair_events: list[dict[str, Any]],
) -> str:
    if hard_fail_hit or not policy_consistent:
        return "block"
    promote_eligible = all(item["status"] in {"applied", "not_needed"} for item in repair_events)
    if overall >= promote_threshold and promote_eligible:
        return "promote"
    if overall >= repair_threshold:
        return "repair"
    return "rerun"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    try:
        repo_root = _resolve_repo_root(Path(args.root))
        registries = _load_registries(repo_root)
        src = _load_json(Path(args.input).resolve())
        if not isinstance(src, dict):
            raise ValueError("input must be a JSON object")
        unknown_input_fields = sorted(set(src) - ALLOWED_INPUT_FIELDS)
        if unknown_input_fields:
            raise ValueError(f"unknown input fields: {', '.join(unknown_input_fields)}")

        run_id = _as_nonempty_str(src, "run_id")
        engine_name = _as_nonempty_str(src, "engine_name")
        engine_ids = {
            str(entry["id"])
            for entry in registries["engine_registry"].get("engines", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        if not engine_ids:
            raise ValueError("no engine IDs found in wave27 engine registry")
        if engine_name not in engine_ids:
            raise ValueError(f"engine_name not found in wave27 registry: {engine_name}")
        frame_count_raw = src.get("frame_count")
        if (
            not isinstance(frame_count_raw, int)
            or isinstance(frame_count_raw, bool)
            or frame_count_raw <= 0
        ):
            raise ValueError("frame_count must be a positive integer")
        frame_count = int(frame_count_raw)

        scoring_rules = registries["scoring_rules"]
        if scoring_rules.get("dimensions") != list(REQUIRED_DIMENSIONS):
            raise ValueError("wave27 scoring registry dimensions do not match required six dimensions")
        promote_threshold = float(scoring_rules["promotion_threshold"])
        repair_threshold = float(scoring_rules["repair_threshold"])
        if (
            not math.isfinite(promote_threshold)
            or not math.isfinite(repair_threshold)
            or repair_threshold < 0
            or promote_threshold > 100
            or repair_threshold > promote_threshold
        ):
            raise ValueError("wave27 scoring thresholds must satisfy 0 <= repair <= promote <= 100")
        raw_hard_fail_conditions = scoring_rules.get("hard_fail_conditions", [])
        if not isinstance(raw_hard_fail_conditions, list) or any(
            not isinstance(item, str) or not item.strip() for item in raw_hard_fail_conditions
        ):
            raise ValueError("hard_fail_conditions registry value must contain non-empty strings")
        hard_fail_conditions = {item.strip() for item in raw_hard_fail_conditions}
        if not hard_fail_conditions:
            raise ValueError("hard_fail_conditions must not be empty")

        repair_policy = registries["repair_policy"]
        allowed_actions = {
            str(entry["action"])
            for entry in repair_policy.get("repair_classes", [])
            if isinstance(entry, dict) and isinstance(entry.get("action"), str)
        }
        if not allowed_actions:
            raise ValueError("no repair actions found in repair policy registry")

        loop_registry = registries["loop_profile"]
        loop_profiles = {
            str(entry["id"])
            for entry in loop_registry.get("profiles", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        if not loop_profiles:
            raise ValueError("no loop profiles found in wave26 loop registry")
        loop_profile = _as_nonempty_str(src, "loop_profile")
        if loop_profile not in loop_profiles:
            raise ValueError(f"loop_profile not found in wave26 registry: {loop_profile}")

        dimension_scores = _compute_dimension_scores(src)
        overall = round(sum(dimension_scores.values()) / float(len(REQUIRED_DIMENSIONS)), 2)
        raw_hard_failures = src.get("hard_failures", [])
        if not isinstance(raw_hard_failures, list) or any(
            not isinstance(item, str) or not item.strip() for item in raw_hard_failures
        ):
            raise ValueError("hard_failures must be a list of non-empty strings")
        hard_failures = [item.strip() for item in raw_hard_failures]
        if len(set(hard_failures)) != len(hard_failures):
            raise ValueError("hard_failures must be unique")
        unknown_hard_failures = sorted(set(hard_failures) - hard_fail_conditions)
        if unknown_hard_failures:
            raise ValueError(
                f"hard_failures contain unknown taxonomy values: {', '.join(unknown_hard_failures)}"
            )
        hard_failures.sort()
        hard_fail_hit = bool(hard_failures)

        repair_events = _normalize_repair_events(src, frame_count, allowed_actions)
        repair_policy_consistent = all(item["status"] in {"applied", "not_needed"} for item in repair_events)
        decision = _derive_decision(
            overall=overall,
            promote_threshold=promote_threshold,
            repair_threshold=repair_threshold,
            hard_fail_hit=hard_fail_hit,
            policy_consistent=repair_policy_consistent,
            repair_events=repair_events,
        )

        provided_decision = src.get("promotion_decision")
        if provided_decision is not None:
            if provided_decision not in DECISIONS:
                raise ValueError("promotion_decision must be promote, repair, rerun, or block")
            if provided_decision != decision:
                raise ValueError(
                    f"promotion_decision mismatch: expected {decision}, got {provided_decision}"
                )

        out = {
            "schema_name": "wave27_temporal_evidence",
            "evidence_version": 1,
            "run_id": run_id,
            "engine_name": engine_name,
            "frame_count": frame_count,
            "loop_profile": loop_profile,
            "identity_drift_score": _as_score(src, "identity_drift_score"),
            "flicker_score": _as_score(src, "flicker_score"),
            "pose_continuity_score": _as_score(src, "pose_continuity_score"),
            "depth_continuity_score": _as_score(src, "depth_continuity_score"),
            "contact_continuity_score": _as_score(src, "contact_continuity_score"),
            "export_integrity_score": _as_score(src, "export_integrity_score"),
            "dimension_scores": dimension_scores,
            "overall_temporal_score": overall,
            "hard_failures": hard_failures,
            "repair_events": repair_events,
            "repair_policy_consistent": repair_policy_consistent,
            "promotion_decision": decision,
            "loop_export": {
                "structural_gate_passed": True,
                "final_export_ready": False,
                "final_export_passed": False,
                "decision_scope": "offline_structural_only",
                "reason": "offline_structural_gate_only",
            },
        }
    except Exception as exc:
        _error(str(exc))
        return 1

    output_path = Path(args.output).resolve()
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        _error(f"unable to write temporal evidence: {exc}")
        return 1
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
