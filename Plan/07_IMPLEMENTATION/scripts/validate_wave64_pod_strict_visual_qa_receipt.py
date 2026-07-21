#!/usr/bin/env python3
"""Validate a pod_strict_self_hosted_llm_visual_qa_receipt (offline, fail-closed)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "wave64.pod_strict_visual_qa.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRODUCT_LANES = frozenset({"PRODUCT", "CLASS_A", "PROOF_LANDED", "IDENTITY_GATE"})
FORBIDDEN_PRODUCT_MODELS = frozenset(
    {
        "qwen2.5vl:7b",
        "qwen3-vl:4b-instruct-q4_K_M",
        "qwen3-vl:8b-instruct-q4_K_M",
        "llava:13b",
        "llama3.2-vision:11b",
        "qwen2.5:7b-instruct",
    }
)
SCORE_KEYS = (
    "anatomy_hands_fingers",
    "identity_consistency",
    "skin_realism",
    "motion_temporal",
    "artifacts_cleanliness",
    "prompt_adherence",
    "policy_project",
)


def validate_receipt(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if obj.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if obj.get("generation_receipt_is_not_visual_approval") is not True:
        errors.append("generation_receipt_is_not_visual_approval must be true")
    if obj.get("product_completion_claimed") is not False:
        errors.append("product_completion_claimed must be false")

    authority = obj.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority missing")
    else:
        if authority.get("host") != "runpod":
            errors.append("authority.host must be runpod")
        if authority.get("fail_closed") is not True:
            errors.append("authority.fail_closed must be true")
        if authority.get("ec2_forbidden") is not True:
            errors.append("authority.ec2_forbidden must be true")

    lane = obj.get("lane")
    if lane not in PRODUCT_LANES | {"SMOKE"}:
        errors.append("lane invalid")

    model = obj.get("model") if isinstance(obj.get("model"), dict) else {}
    model_name = str(model.get("name") or "")
    if not model_name:
        errors.append("model.name required")
    if lane in PRODUCT_LANES:
        if model_name in FORBIDDEN_PRODUCT_MODELS:
            errors.append(f"forbidden weak model for product lane: {model_name}")
        if model.get("approved_for_product") is not True and obj.get("strict_pod_llm_review") == "PASS":
            errors.append("PASS forbidden when model.approved_for_product is not true")

    decision = obj.get("overall_decision")
    strict = obj.get("strict_pod_llm_review")
    if decision not in {"PASS", "REJECT", "BLOCKED"}:
        errors.append("overall_decision invalid")
    if strict not in {"PASS", "REJECT", "BLOCKED"}:
        errors.append("strict_pod_llm_review invalid")
    if decision != strict:
        errors.append("overall_decision must equal strict_pod_llm_review")

    scores = obj.get("rubric_scores")
    if not isinstance(scores, dict):
        errors.append("rubric_scores missing")
    else:
        for key in SCORE_KEYS:
            cell = scores.get(key)
            if not isinstance(cell, dict) or "pass" not in cell or "applicable" not in cell:
                errors.append(f"rubric_scores.{key} incomplete")
                continue
            if cell.get("applicable") is True and decision == "PASS" and cell.get("pass") is not True:
                errors.append(f"PASS requires rubric_scores.{key}.pass")

    defects = obj.get("blocking_defects")
    if not isinstance(defects, list):
        errors.append("blocking_defects must be array")
        defects = []
    if any(
        isinstance(d, dict) and d.get("severity") == "blocking" for d in defects
    ) and decision == "PASS":
        errors.append("PASS forbidden when blocking defects present")

    guidance = obj.get("correction_guidance")
    if not isinstance(guidance, list):
        errors.append("correction_guidance must be array")
    elif decision in {"REJECT", "BLOCKED"} and not guidance:
        errors.append("REJECT/BLOCKED requires non-empty correction_guidance")

    artifact = obj.get("artifact") if isinstance(obj.get("artifact"), dict) else {}
    paths = artifact.get("paths")
    if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p.strip() for p in paths):
        errors.append("artifact.paths required")
    sha = artifact.get("sha256")
    if sha is not None and not (isinstance(sha, str) and SHA256.fullmatch(sha)):
        errors.append("artifact.sha256 invalid")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    obj = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        print("root must be object", file=sys.stderr)
        return 2
    errors = validate_receipt(obj)
    payload = {"ok": not errors, "errors": errors, "strict_pod_llm_review": obj.get("strict_pod_llm_review")}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
