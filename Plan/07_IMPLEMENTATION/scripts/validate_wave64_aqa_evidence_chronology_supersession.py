#!/usr/bin/env python3
"""Validate immutable evidence chronology supersession bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT = Path("Plan/Tracker/Evidence/W64_AQA_EVIDENCE_CHRONOLOGY_SUPERSESSION_20260722T182334Z.json")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate(root: Path, value: dict) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != "wave64.aqa.evidence_chronology_supersession.v1":
        errors.append("schema_version mismatch")
    if value.get("source_records_preserved") is not True or value.get("technical_findings_reinterpreted") is not False:
        errors.append("supersession preservation boundary mismatch")
    seen: set[str] = set()
    for record in value.get("records", []):
        path = record.get("path", "")
        if path in seen:
            errors.append(f"duplicate source path: {path}")
            continue
        seen.add(path)
        source = root / path
        if not source.is_file():
            errors.append(f"source missing: {path}")
            continue
        payload = source.read_bytes()
        if len(payload) != record.get("bytes"):
            errors.append(f"source byte count mismatch: {path}")
        if hashlib.sha256(payload).hexdigest() != record.get("sha256"):
            errors.append(f"source hash mismatch: {path}")
        if parse_utc(record["invalid_recorded_at_utc"]) <= parse_utc(record["containing_commit_time_utc"]):
            errors.append(f"source chronology was not invalid: {path}")
        if parse_utc(value["recorded_at_utc"]) <= parse_utc(record["containing_commit_time_utc"]):
            errors.append(f"supersession predates source commit: {path}")
    if len(seen) != 4:
        errors.append("exactly four superseded source records required")
    authority = value.get("authority", {})
    if authority != {"chronology_correction": True, "source_evidence_mutation": False, "runtime": False, "quality": False, "activation": False, "promotion": False}:
        errors.append("authority boundary mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT)
    args = parser.parse_args()
    path = args.path if args.path.is_absolute() else ROOT / args.path
    errors = validate(ROOT, json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
