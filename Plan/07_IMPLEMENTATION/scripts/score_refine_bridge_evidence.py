#!/usr/bin/env python3
"""Score Wave16 refine bridge evidence from a JSON manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


HIGH_SEVERITY = {"DRIFT-IDENTITY", "DRIFT-POSE", "DRIFT-CROP", "ENGINE-MISMATCH", "OVER-DENOISE"}


def score(report: Dict[str, Any]) -> Dict[str, Any]:
    risks = report.get("risks", [])
    risk_ids = {r.get("risk_id") if isinstance(r, dict) else str(r) for r in risks}
    qa_score = float(report.get("qa_score", 0.0))
    passed = qa_score >= 0.85 and not (risk_ids & HIGH_SEVERITY)
    return {
        "passed": passed,
        "qa_score": qa_score,
        "high_severity_risks": sorted(risk_ids & HIGH_SEVERITY),
        "risk_count": len(risks),
        "decision": "promote" if passed else "rerun_or_block",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    result = score(data)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
