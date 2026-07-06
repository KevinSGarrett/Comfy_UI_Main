#!/usr/bin/env python3
"""Validate a Wave16 image-refine bridge plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_plan(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not plan.get("plan_id"):
        errors.append("missing plan_id")
    if not isinstance(plan.get("passes"), list) or not plan["passes"]:
        errors.append("missing passes")
    for i, p in enumerate(plan.get("passes", [])):
        denoise = p.get("denoise")
        if denoise is None:
            errors.append(f"pass {i} missing denoise")
        elif not (0 <= float(denoise) <= 1):
            errors.append(f"pass {i} denoise outside 0..1")
        if p.get("mask_required") and not (p.get("mask_contract_id") or p.get("mask_id")):
            if p.get("pass_id") != "REFINE-50-CROSS-ENGINE-SDXL-BRIDGE":
                errors.append(f"pass {i} requires mask but no mask id/contract")
        if p.get("target_engine") == "pony_sdxl_specialty" and not p.get("mask_required"):
            errors.append(f"pass {i} Pony specialty must be masked")
        if float(p.get("denoise", 0)) > 0.4:
            errors.append(f"pass {i} denoise > 0.4 is regeneration, not refine")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    plan = load_json(args.plan)
    ok, errors = validate_plan(plan)
    report = {"passed": ok, "errors": errors, "plan_id": plan.get("plan_id")}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
