#!/usr/bin/env python3
"""Score Wave17 body-shape evidence using the weighted QA catalog."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


AUTO_FAIL_FLAGS = {
    "face_identity_changed",
    "merged_body_detected",
    "extra_limb_or_body_fragment_created",
    "requested_character_missing",
    "mask_owner_mismatch",
    "full_image_redraw_used_for_body_correction",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def score(evidence: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    scores = evidence.get("scores", {})
    fail_flags = set(evidence.get("fail_flags", []))
    if fail_flags.intersection(AUTO_FAIL_FLAGS):
        evidence["weighted_score"] = 0.0
        evidence["decision"] = "blocked"
        return evidence

    metrics = rules.get("metrics", [])
    total_weight = sum(float(m.get("weight", 0)) for m in metrics) or 1.0
    weighted = 0.0
    missing = []
    for m in metrics:
        mid = m["metric_id"]
        weight = float(m.get("weight", 0))
        if mid not in scores:
            missing.append(mid)
            value = 0.0
        else:
            value = float(scores[mid])
        weighted += value * weight
    weighted = weighted / total_weight
    evidence["weighted_score"] = round(weighted, 4)

    bands = rules.get("score_bands", {"pass": 0.86, "review": 0.72, "fail_below": 0.72})
    if missing:
        evidence["decision"] = "review"
        evidence.setdefault("notes", []).append(f"missing metrics: {', '.join(missing)}")
    elif weighted >= float(bands.get("pass", 0.86)):
        evidence["decision"] = "pass"
    elif weighted >= float(bands.get("review", 0.72)):
        evidence["decision"] = "review"
    else:
        evidence["decision"] = "fail"
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    evidence = load_json(Path(args.evidence))
    rules = load_json(Path(args.rules))
    result = score(evidence, rules)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{result['decision'].upper()}: weighted_score={result.get('weighted_score')}")
    return 0 if result["decision"] in {"pass", "review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
