#!/usr/bin/env python3
"""Evaluate Row101 video-conditioned Foley without granting synthetic authority."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = Path("Plan/08_SCHEMAS/video_conditioned_foley_decision.schema.json")
POLICY = Path("Plan/10_REGISTRIES/wave64_row101_video_conditioned_foley_policy_registry.json")
DEPENDENCIES = ("TRK-W64-083", "TRK-W64-091", "TRK-W64-092", "TRK-W64-097", "TRK-W64-099")


class FoleyDecisionError(ValueError):
    """Raised for malformed or contradictory Row101 decision packets."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row101:{label}".encode()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dependency_state(root: Path) -> dict[str, bool]:
    evidence_root = root / "Plan/Instructions/QA/Evidence/Wave64"
    result = {}
    for tracker in DEPENDENCIES:
        files = sorted(evidence_root.glob(f"{tracker}_*CURRENT_DELTA*.json"))
        accepted = False
        if len(files) == 1:
            payload = load_json(files[0])
            accepted = payload.get("tracker_id") == tracker and payload.get("row_complete") is True and str(payload.get("status", "")).lower().startswith(("pass", "accepted", "complete"))
        result[tracker] = accepted
    return result


def evaluate(root: Path, *, video_sha256: str, event_script_sha256: str, candidate_sha256: str,
             engine: dict[str, Any], anchors: list[dict[str, Any]], anchor_decisions: list[dict[str, Any]],
             alignments: list[dict[str, Any]], runtime_evidence_sha256: str | None, is_synthetic: bool,
             dependencies: dict[str, bool] | None = None) -> dict[str, Any]:
    policy = load_json(root / POLICY)
    dependency_admission = dependency_state(root) if dependencies is None else dependencies
    if tuple(dependency_admission) != DEPENDENCIES:
        raise FoleyDecisionError("dependency_set_or_order_mismatch")
    anchor_ids = [item["anchor_id"] for item in anchors]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise FoleyDecisionError("duplicate_anchor_id")
    decision_ids = [item["anchor_id"] for item in anchor_decisions]
    alignment_ids = [item["anchor_id"] for item in alignments]
    if sorted(decision_ids) != sorted(anchor_ids) or sorted(alignment_ids) != sorted(anchor_ids):
        raise FoleyDecisionError("anchor_coverage_mismatch")
    for anchor in anchors:
        if anchor["end_sample"] <= anchor["start_sample"]:
            raise FoleyDecisionError("invalid_anchor_sample_range")
    blockers = [f"{tracker.replace('-', '_')}_HELD" for tracker, accepted in dependency_admission.items() if not accepted]
    if engine.get("family") not in policy["registered_engine_families"]:
        blockers.append("ENGINE_FAMILY_NOT_REGISTERED")
    if not engine.get("qualified") or not engine.get("qualification_evidence_sha256"):
        blockers.append("ENGINE_NOT_INDEPENDENTLY_QUALIFIED")
    if not runtime_evidence_sha256:
        blockers.append("GENUINE_RUNTIME_EVIDENCE_ABSENT")
    for item in anchor_decisions:
        if item.get("action") not in policy["allowed_anchor_actions"] or item.get("explicit") is not True:
            blockers.append(f"ANCHOR_{item['anchor_id']}_OVERWRITE_OR_IMPLICIT_DECISION")
    for item in alignments:
        if item["onset_error_ms"] > policy["maximum_onset_error_ms"] or item["coverage"] < policy["minimum_anchor_coverage"]:
            blockers.append(f"ANCHOR_{item['anchor_id']}_ALIGNMENT_FAILED")
    if is_synthetic:
        blockers.append("SYNTHETIC_PRODUCTION_AUTHORITY_FORBIDDEN")
    blockers = list(dict.fromkeys(blockers))
    candidate_authority = bool(candidate_sha256 and engine.get("family") in policy["registered_engine_families"])
    production_authority = not blockers
    report = {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-101",
        "video_sha256": video_sha256, "event_script_sha256": event_script_sha256,
        "candidate_sha256": candidate_sha256, "engine": engine, "anchors": anchors,
        "anchor_decisions": anchor_decisions, "alignments": alignments,
        "runtime_evidence_sha256": runtime_evidence_sha256, "is_synthetic": is_synthetic,
        "decision": {"status": "pass" if production_authority else "blocked", "candidate_authority": candidate_authority,
                     "production_authority": production_authority, "blocker_codes": blockers},
    }
    report["report_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    validate_report(root, report)
    return report


def validate_report(root: Path, report: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA)).validate(report)
    candidate = deepcopy(report)
    observed = candidate.pop("report_sha256")
    if observed != hashlib.sha256(canonical_bytes(candidate)).hexdigest():
        raise FoleyDecisionError("report_sha256_mismatch")
    if report["decision"]["production_authority"] and (report["is_synthetic"] or report["decision"]["blocker_codes"]):
        raise FoleyDecisionError("invalid_production_authority")


def fixture_packet(*, synthetic: bool = True) -> dict[str, Any]:
    anchor = {"anchor_id": "contact-001", "source_sha256": stable_hash("one-shot"), "start_sample": 12000, "end_sample": 16800, "trusted_exact_one_shot": True}
    return {
        "video_sha256": stable_hash("video"), "event_script_sha256": stable_hash("events"), "candidate_sha256": stable_hash("candidate"),
        "engine": {"family": "mmaudio", "revision": "fixture-revision", "model_sha256": stable_hash("model"), "qualification_evidence_sha256": stable_hash("qualification"), "qualified": True},
        "anchors": [anchor], "anchor_decisions": [{"anchor_id": "contact-001", "action": "supplement", "explicit": True, "generated_gain_db": -9.0}],
        "alignments": [{"anchor_id": "contact-001", "onset_error_ms": 12.0, "coverage": 0.95}],
        "runtime_evidence_sha256": stable_hash("runtime"), "is_synthetic": synthetic,
    }
