#!/usr/bin/env python3
"""Validate the current RunPod-only production-platform authority boundary."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_sole_production_platform_policy.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_sole_production_platform_policy.schema.json")
TRACKER_PATH = Path("Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv")
ITEMS_PATH = Path("Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv")
REQUIREMENTS_PATH = Path("Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_REQUIREMENTS.json")
LEGACY_S3_POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_s3_evidence_staging_policy.json")


class PlatformPolicyError(ValueError):
    """Raised when active-platform authority or tracker state drifts."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PlatformPolicyError(f"JSON root must be an object: {path}")
    return value


def row_by_id(path: Path, row_id: str) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row[next(iter(row))]: row for row in csv.DictReader(handle)}
    if row_id not in rows:
        raise PlatformPolicyError(f"missing row {row_id}: {path}")
    return rows[row_id]


def validate_policy(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    tracker = row_by_id(root / TRACKER_PATH, "W64-AQA-012")
    item = row_by_id(root / ITEMS_PATH, "W64-AQA-012")
    if tracker["Status"] != value["tracker_reclassification"]["classification"]:
        raise PlatformPolicyError("W64-AQA-012 tracker classification drift")
    if item["Status"] != value["tracker_reclassification"]["classification"]:
        raise PlatformPolicyError("W64-AQA-012 item classification drift")
    if item["Autonomous_Required"] != "No":
        raise PlatformPolicyError("legacy AWS lineage remains required")
    requirements = load_json(root / REQUIREMENTS_PATH)
    requirement = next(entry for entry in requirements["requirements"] if entry["id"] == "W64-AQA-012")
    if requirement["required"] is not False:
        raise PlatformPolicyError("W64-AQA-012 remains required in requirements")
    legacy_s3 = load_json(root / LEGACY_S3_POLICY_PATH)
    if legacy_s3.get("classification") != "LEGACY_AWS_EVIDENCE_LINEAGE_AUDIT_ONLY":
        raise PlatformPolicyError("S3 policy is not classified as legacy audit lineage")
    if legacy_s3.get("active_production_platform") or legacy_s3.get("runpod_critical_path_dependency"):
        raise PlatformPolicyError("legacy S3 policy remains on the production path")
    for row_id in ("W64-AQA-013", "W64-AQA-016"):
        for path in (root / TRACKER_PATH, root / ITEMS_PATH):
            if "W64-AQA-012" in row_by_id(path, row_id).get("Dependencies", "").split("|"):
                raise PlatformPolicyError(f"legacy AWS lineage remains on active dependency edge: {row_id}")
    if value["legacy_cloud"]["active_production_blocker"] or value["legacy_cloud"]["automatic_access_allowed"]:
        raise PlatformPolicyError("legacy cloud authority expanded")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.policy if args.policy.is_absolute() else root / args.policy
    value = load_json(path)
    validate_policy(root, value)
    print(json.dumps({"status": "PASS", "policy_id": value["policy_id"], "active_platform": "RUNPOD", "aws_active_blocker": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
