#!/usr/bin/env python3
"""Score Wave12 frame composition evidence against a contract.

The script expects detector/skeleton/segmentation outputs already converted into the Wave12 evidence JSON format.
"""
import argparse
import json
from pathlib import Path

WEIGHTS = {
    "character_count": 0.22,
    "body_visibility": 0.20,
    "crop_boundaries": 0.18,
    "merged_body_absence": 0.22,
    "pose_skeleton_consistency": 0.10,
    "composition_balance": 0.08,
}

def clamp(x):
    return max(0.0, min(1.0, float(x)))

def score(contract, evidence):
    expected = int(contract.get("expected_character_count", 0))
    detected = len(evidence.get("detected_person_instances", []))
    skeletons = len(evidence.get("detected_skeletons", []))
    hard_fails = []
    subscores = {}

    if expected == detected:
        subscores["character_count"] = 1.0
    else:
        subscores["character_count"] = max(0.0, 1.0 - abs(expected - detected) * 0.5)
        hard_fails.append("wrong_character_count")

    vis = evidence.get("body_visibility_by_character", [])
    if vis:
        ratios = [float(v.get("visible_body_length_ratio", 0.0)) for v in vis]
        subscores["body_visibility"] = clamp(sum(ratios) / len(ratios))
    else:
        subscores["body_visibility"] = 0.0
        hard_fails.append("missing_body_visibility_evidence")

    crop = evidence.get("crop_boundary_report", {})
    crop_hard = crop.get("hard_crop_events", []) or []
    if crop_hard:
        subscores["crop_boundaries"] = 0.0
        hard_fails.extend([f"crop:{x}" for x in crop_hard])
    else:
        margin = float(crop.get("minimum_margin_ratio_observed", 0.0))
        required = float(contract.get("crop_boundary_policy", {}).get("safe_margin_ratio", 0.04))
        subscores["crop_boundaries"] = 1.0 if margin >= required else clamp(margin / required)

    merged = evidence.get("merged_body_report", {})
    if merged.get("merged_body_detected"):
        subscores["merged_body_absence"] = 0.0
        hard_fails.append("merged_bodies")
    elif int(merged.get("unassigned_body_fragments", 0)) > 0:
        subscores["merged_body_absence"] = 0.4
        hard_fails.append("unassigned_body_fragment")
    else:
        subscores["merged_body_absence"] = 1.0

    subscores["pose_skeleton_consistency"] = 1.0 if skeletons >= expected else clamp(skeletons / expected if expected else 1.0)
    if skeletons < expected:
        hard_fails.append("missing_skeletons")

    subscores["composition_balance"] = clamp(evidence.get("composition_balance_score", 0.85))
    total = sum(subscores[k] * WEIGHTS[k] for k in WEIGHTS)

    if hard_fails:
        decision = "fail"
    elif total >= contract.get("qa_thresholds", {}).get("minimum_total_score", 0.86):
        decision = "pass"
    elif total >= 0.76:
        decision = "review"
    else:
        decision = "fail"
    return {"score": round(total, 4), "decision": decision, "hard_fail_reasons": sorted(set(hard_fails)), "subscores": subscores}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    report = score(contract, evidence)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
