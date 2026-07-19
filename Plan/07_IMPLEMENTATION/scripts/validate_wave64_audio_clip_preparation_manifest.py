#!/usr/bin/env python3
"""Fail-closed validator for Wave64 Row093 audio clip preparation manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = ROOT / "Plan/08_SCHEMAS/audio_clip_preparation_manifest.schema.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return sorted(error.message for error in validator.iter_errors(payload))


def semantic_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = payload.get("source")
    if isinstance(source, dict):
        start = source.get("segment_start_sample")
        end = source.get("segment_end_sample")
        if isinstance(start, int) and isinstance(end, int) and end <= start:
            errors.append(
                "source.segment_end_sample must be greater than source.segment_start_sample"
            )

    transforms = payload.get("transforms")
    if isinstance(transforms, list) and len(transforms) == 0:
        errors.append("transforms must be a nonempty ordered chain")

    validation = payload.get("validation")
    decision = validation.get("decision") if isinstance(validation, dict) else None
    if decision == "PASS":
        anchor = payload.get("anchor")
        if isinstance(anchor, dict) and anchor.get("within_tolerance") is not True:
            errors.append("PASS requires anchor.within_tolerance == true")
        tail = payload.get("tail")
        if isinstance(tail, dict) and tail.get("tail_preserved") is not True:
            errors.append("PASS requires tail.tail_preserved == true")
        phase = payload.get("phase")
        if not isinstance(phase, dict):
            errors.append("PASS requires recorded phase preservation measurements")
        else:
            if phase.get("within_tolerance") is not True:
                errors.append("PASS requires phase.within_tolerance == true")
            if phase.get("polarity_inverted") is not False:
                errors.append("PASS requires phase.polarity_inverted == false")
        if isinstance(validation, dict):
            defects = validation.get("defects")
            if not isinstance(defects, list) or len(defects) != 0:
                errors.append("PASS requires validation.defects to be empty")
    return errors


def validate_manifest(
    payload: dict[str, Any],
    *,
    schema: dict[str, Any] | None = None,
    schema_path: Path | None = None,
) -> list[str]:
    resolved_schema = schema
    if resolved_schema is None:
        path = schema_path or DEFAULT_SCHEMA
        resolved_schema = load_json(path)
    return schema_errors(resolved_schema, payload) + semantic_errors(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to clip preparation manifest JSON")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to audio_clip_preparation_manifest.schema.json",
    )
    args = parser.parse_args(argv)

    payload = load_json(args.manifest)
    if not isinstance(payload, dict):
        print("manifest root must be an object", file=sys.stderr)
        return 2

    errors = validate_manifest(payload, schema_path=args.schema)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
