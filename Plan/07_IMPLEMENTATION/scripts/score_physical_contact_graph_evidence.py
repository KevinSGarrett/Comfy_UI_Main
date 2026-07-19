#!/usr/bin/env python3
"""Score Wave 22 physical contact graph evidence with exact Boolean truth."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLAN_ROOT = Path(__file__).resolve().parents[2]
SCORING_REGISTRY = PLAN_ROOT / "10_REGISTRIES/wave22_contact_graph_qa_scoring_rules.json"
CHECK_TO_DIMENSION = {
    "source_target_ownership_pass": "source_target_ownership",
    "pressure_intensity_pass": "pressure_intensity_valid",
    "occlusion_pass": "occlusion_valid",
    "duration_pass": "duration_valid",
    "audio_force_pass": "audio_force_valid",
    "deformation_evidence_pass": "deformation_evidence",
    "preservation_pass": "preservation_pass",
}
ALLOWED_FIELDS = set(CHECK_TO_DIMENSION) | {"failure_flags"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_scoring_registry() -> tuple[float, dict[str, float], set[str]]:
    payload = _load_json(SCORING_REGISTRY)
    if not isinstance(payload, dict) or set(payload) != {"minimum_pass_score", "dimensions", "hard_fail_flags"}:
        raise ValueError("scoring registry must contain exact required fields")
    minimum = payload["minimum_pass_score"]
    if type(minimum) not in (int, float) or isinstance(minimum, bool) or not 0 <= float(minimum) <= 1:
        raise ValueError("minimum_pass_score must be a finite ratio")
    dimensions = payload["dimensions"]
    if not isinstance(dimensions, dict) or set(dimensions) != set(CHECK_TO_DIMENSION.values()):
        raise ValueError("scoring dimensions mismatch")
    weights: dict[str, float] = {}
    for key, value in dimensions.items():
        if type(value) not in (int, float) or isinstance(value, bool) or not 0 <= float(value) <= 1:
            raise ValueError(f"invalid scoring weight: {key}")
        weights[key] = float(value)
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("scoring weights must sum to 1")
    hard_flags = payload["hard_fail_flags"]
    if not isinstance(hard_flags, list) or not hard_flags:
        raise ValueError("hard_fail_flags must be a non-empty array")
    if any(type(flag) is not str or not flag.strip() for flag in hard_flags):
        raise ValueError("hard_fail_flags must contain non-empty strings")
    normalized = [flag.strip() for flag in hard_flags]
    if len(normalized) != len(set(normalized)):
        raise ValueError("hard_fail_flags must be unique")
    return float(minimum), weights, set(normalized)


def score_evidence(payload: Any) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, bool] = {}
    failure_flags: list[str] = []
    minimum = 1.0
    weights: dict[str, float] = {}
    registered_hard_flags: set[str] = set()

    try:
        minimum, weights, registered_hard_flags = _load_scoring_registry()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"authority registry invalid: {exc}")

    if not isinstance(payload, dict):
        errors.append("evidence must be an object")
    else:
        missing = sorted(set(CHECK_TO_DIMENSION) - set(payload))
        unexpected = sorted(set(payload) - ALLOWED_FIELDS)
        errors.extend(f"missing evidence field: {key}" for key in missing)
        errors.extend(f"unexpected evidence field: {key}" for key in unexpected)

        for key in CHECK_TO_DIMENSION:
            value = payload.get(key)
            if type(value) is not bool:
                errors.append(f"{key} must be an exact Boolean")
            else:
                checks[key] = value

        raw_flags = payload.get("failure_flags", [])
        if not isinstance(raw_flags, list):
            errors.append("failure_flags must be an array")
        else:
            for idx, flag in enumerate(raw_flags):
                if type(flag) is not str or not flag.strip():
                    errors.append(f"failure_flags[{idx}] must be a non-empty string")
                else:
                    failure_flags.append(flag.strip())
            if len(failure_flags) != len(set(failure_flags)):
                errors.append("failure_flags must be unique")

    weighted_score = 0.0
    if not errors:
        weighted_score = sum(
            weights[dimension] for check, dimension in CHECK_TO_DIMENSION.items() if checks[check]
        )
    hard_fail_flags = sorted(set(failure_flags) & registered_hard_flags)
    unregistered_failure_flags = sorted(set(failure_flags) - registered_hard_flags)
    passed = (
        not errors
        and all(checks.values())
        and weighted_score >= minimum
        and not failure_flags
    )
    return {
        "evidence_version": "wave22.v2",
        "classification": "WAVE22_PHYSICAL_CONTACT_GRAPH_EVIDENCE_PASS" if passed else "WAVE22_PHYSICAL_CONTACT_GRAPH_EVIDENCE_FAIL",
        "checks": checks,
        "score": round(weighted_score, 4),
        "minimum_pass_score": minimum,
        "pass": passed,
        "failure_flags": failure_flags,
        "hard_fail_flags": hard_fail_flags,
        "unregistered_failure_flags": unregistered_failure_flags,
        "errors": errors,
        "exact_boolean_truth_enforced": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        payload = _load_json(Path(args.input))
        report = score_evidence(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        report = score_evidence(None)
        report["errors"] = [f"invalid input JSON: {exc}"]
        report["classification"] = "WAVE22_PHYSICAL_CONTACT_GRAPH_EVIDENCE_FAIL"
        report["pass"] = False

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
