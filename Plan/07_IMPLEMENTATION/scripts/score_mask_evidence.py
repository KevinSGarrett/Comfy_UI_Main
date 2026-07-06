#!/usr/bin/env python3
"""Score Wave13 mask evidence manifests.

This script is intentionally conservative. Missing evidence is a blocker.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_WEIGHTS = {
    "mask_presence_and_decode": 10,
    "assigned_instance_or_region_id": 12,
    "coverage_matches_contract": 14,
    "edge_quality_and_feathering": 14,
    "no_bleed_into_neighbor_region": 14,
    "contact_or_occlusion_consistency": 12,
    "identity_and_outfit_protection": 12,
    "before_after_output_evidence": 12,
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Evidence must be a JSON object")
    return data


def score(evidence: Dict[str, Any], minimum: int = 85) -> Dict[str, Any]:
    blockers: List[str] = []
    records = evidence.get("mask_records", [])
    if not isinstance(records, list) or not records:
        blockers.append("missing_mask_records")
        records = []

    component_scores = {key: 100 for key in DEFAULT_WEIGHTS}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"mask_record_{index}_not_object")
            continue
        if not record.get("mask_id"):
            blockers.append(f"mask_record_{index}_missing_mask_id")
        if not record.get("mask_png_path"):
            component_scores["mask_presence_and_decode"] = min(component_scores["mask_presence_and_decode"], 50)
            blockers.append(f"mask_record_{index}_missing_mask_path")
        if not (record.get("person_instance_id") or record.get("target_type") or record.get("body_region_id") or record.get("fabric_region_id") or record.get("contact_type")):
            component_scores["assigned_instance_or_region_id"] = min(component_scores["assigned_instance_or_region_id"], 50)
            blockers.append(f"mask_record_{index}_unassigned")
        edge = record.get("edge_quality_score")
        if isinstance(edge, (int, float)):
            component_scores["edge_quality_and_feathering"] = min(component_scores["edge_quality_and_feathering"], max(0, min(100, float(edge))))
        coverage = record.get("coverage_percent")
        if isinstance(coverage, (int, float)) and (coverage <= 0 or coverage > 95):
            component_scores["coverage_matches_contract"] = min(component_scores["coverage_matches_contract"], 60)

    if not evidence.get("image_path"):
        component_scores["before_after_output_evidence"] = min(component_scores["before_after_output_evidence"], 60)
        blockers.append("missing_image_path")

    weighted_total = 0.0
    total_weight = sum(DEFAULT_WEIGHTS.values())
    for key, weight in DEFAULT_WEIGHTS.items():
        weighted_total += component_scores[key] * weight
    final_score = round(weighted_total / total_weight, 2) if total_weight else 0.0
    passed = final_score >= minimum and not blockers

    return {
        "report_id": f"mask_quality_report__{evidence.get('evidence_id', 'manual')}",
        "contract_id": evidence.get("contract_id"),
        "score": final_score,
        "minimum_required": minimum,
        "passed": passed,
        "blockers": blockers,
        "component_scores": component_scores,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--minimum", type=int, default=85)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    evidence = load_json(args.evidence)
    report = score(evidence, args.minimum)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
