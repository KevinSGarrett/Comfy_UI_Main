#!/usr/bin/env python3
"""Fail-closed Wave64 Row112 full-system audio certification gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row112_audio_full_system_certification_policy_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_full_system_certification_report.schema.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-112_audio_full_system_certification.json")
POLICY_REVISION = "wave64_row112_audio_full_system_certification_policy_v0.1.0"
REQUIRED_TRACKERS = tuple(f"TRK-W64-{number:03d}" for number in range(67, 112))
REQUIRED_GATES = (
    "genuine_runtime", "rights", "provenance", "full_duration_review",
    "av_sync", "global_qa", "multimodal_release", "replay_reconstruction",
)
PASS_PREFIXES = ("pass", "accepted", "complete")


class CertificationError(ValueError):
    """Raised when certification evidence is incomplete or contradictory."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row112:{label}".encode()).hexdigest()


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _candidate_delta_paths(evidence_root: Path, tracker_id: str) -> list[Path]:
    return sorted(path for path in evidence_root.glob(f"{tracker_id}_*CURRENT_DELTA*.json") if path.is_file())


def inspect_dependency(evidence_root: Path, tracker_id: str) -> dict[str, Any]:
    candidates = _candidate_delta_paths(evidence_root, tracker_id)
    def relative(path: Path) -> str:
        return str(path.relative_to(evidence_root.parents[4])).replace("\\", "/")
    if not candidates:
        return {"tracker_id": tracker_id, "disposition": "absent", "candidate_paths": [], "evidence_sha256": None, "row_complete": False, "status": "ABSENT", "accepted": False}
    if len(candidates) > 1:
        return {"tracker_id": tracker_id, "disposition": "ambiguous", "candidate_paths": [relative(path) for path in candidates], "evidence_sha256": None, "row_complete": False, "status": "AMBIGUOUS_MULTIPLE_CURRENT_DELTAS", "accepted": False}
    path = candidates[0]
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {"tracker_id": tracker_id, "disposition": "invalid", "candidate_paths": [relative(path)], "evidence_sha256": sha256_file(path), "row_complete": False, "status": "INVALID_JSON", "accepted": False}
    if not isinstance(payload, dict) or payload.get("tracker_id") != tracker_id:
        return {"tracker_id": tracker_id, "disposition": "invalid", "candidate_paths": [relative(path)], "evidence_sha256": sha256_file(path), "row_complete": False, "status": "INVALID_TRACKER_BINDING", "accepted": False}
    complete = payload.get("row_complete") is True
    status = str(payload.get("status", ""))
    accepted = complete and status.lower().startswith(PASS_PREFIXES)
    return {"tracker_id": tracker_id, "disposition": "accepted" if accepted else "held", "candidate_paths": [relative(path)], "evidence_sha256": sha256_file(path), "row_complete": complete, "status": status, "accepted": accepted}


def inspect_all_dependencies(root: Path) -> list[dict[str, Any]]:
    evidence_root = root / "Plan/Instructions/QA/Evidence/Wave64"
    return [inspect_dependency(evidence_root, tracker) for tracker in REQUIRED_TRACKERS]


def empty_gate() -> dict[str, Any]:
    return {"evidence_path": None, "evidence_sha256": None, "artifact_sha256": None, "accepted": False, "is_synthetic": False}


def evaluate(root: Path, *, gates: dict[str, dict[str, Any]], video_hashes: list[str], is_synthetic: bool,
             dependencies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if set(gates) != set(REQUIRED_GATES):
        raise CertificationError("production_gate_set_mismatch")
    deps = dependencies if dependencies is not None else inspect_all_dependencies(root)
    if len(deps) != 45 or [item["tracker_id"] for item in deps] != list(REQUIRED_TRACKERS):
        raise CertificationError("dependency_set_or_order_mismatch")
    blockers = []
    for item in deps:
        if not item["accepted"]:
            blockers.append(f"{item['tracker_id'].replace('-', '_')}_{item['disposition'].upper()}")
    for name, gate in gates.items():
        if not gate.get("accepted"):
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_NOT_ACCEPTED")
        if gate.get("is_synthetic"):
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_SYNTHETIC")
        if not gate.get("evidence_sha256") or not gate.get("artifact_sha256") or not gate.get("evidence_path"):
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_BINDING_INCOMPLETE")
    unique_video_hashes = list(dict.fromkeys(video_hashes))
    if len(unique_video_hashes) < 3 or len(video_hashes) != len(unique_video_hashes):
        blockers.append("GENUINE_VIDEO_COVERAGE_INSUFFICIENT")
    if is_synthetic:
        blockers.append("SYNTHETIC_CERTIFICATION_FORBIDDEN")
    blockers = list(dict.fromkeys(blockers))
    accepted = not blockers
    report = {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-112", "item_id": "ITEM-W64-112",
        "record_type": "audio_full_system_certification_report", "policy_revision": POLICY_REVISION,
        "is_synthetic": is_synthetic, "dependency_admissions": deps, "production_gates": gates,
        "genuine_video_sha256s": unique_video_hashes,
        "decision": {"status": "pass" if accepted else "blocked", "certification_authority": accepted,
                     "row112_acceptance": "accepted" if accepted else ("fixture_only" if is_synthetic else "held"),
                     "product_completion": accepted, "blocker_codes": blockers},
    }
    report["report_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    validate_report(root, report)
    return report


def validate_report(root: Path, report: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(report)
    candidate = deepcopy(report)
    observed = candidate.pop("report_sha256")
    if observed != hashlib.sha256(canonical_bytes(candidate)).hexdigest():
        raise CertificationError("report_sha256_mismatch")
    accepted = report["decision"]["certification_authority"]
    if accepted and (report["is_synthetic"] or report["decision"]["blocker_codes"]):
        raise CertificationError("invalid_certification_authority")
    if accepted and (not all(item["accepted"] for item in report["dependency_admissions"]) or not all(gate["accepted"] and not gate["is_synthetic"] for gate in report["production_gates"].values())):
        raise CertificationError("certification_requirements_unsatisfied")


def synthetic_dependencies() -> list[dict[str, Any]]:
    return [{"tracker_id": tracker, "disposition": "accepted", "candidate_paths": [f"Plan/Instructions/QA/Evidence/Wave64/{tracker}_FIXTURE_CURRENT_DELTA.json"], "evidence_sha256": stable_hash(tracker), "row_complete": True, "status": "PASS_FIXTURE", "accepted": True} for tracker in REQUIRED_TRACKERS]


def synthetic_gates() -> dict[str, dict[str, Any]]:
    return {name: {"evidence_path": f"fixtures/{name}.json", "evidence_sha256": stable_hash(f"evidence:{name}"), "artifact_sha256": stable_hash(f"artifact:{name}"), "accepted": True, "is_synthetic": True} for name in REQUIRED_GATES}


def build_evidence(root: Path) -> dict[str, Any]:
    dependencies = inspect_all_dependencies(root)
    live = evaluate(root, gates={name: empty_gate() for name in REQUIRED_GATES}, video_hashes=[], is_synthetic=False, dependencies=dependencies)
    fixture = evaluate(root, gates=synthetic_gates(), video_hashes=[stable_hash(f"video:{index}") for index in range(3)], is_synthetic=True, dependencies=synthetic_dependencies())
    counts: dict[str, int] = {}
    for item in dependencies:
        counts[item["disposition"]] = counts.get(item["disposition"], 0) + 1
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-112_audio_full_system_certification",
        "tracker_id": "TRK-W64-112", "item_id": "ITEM-W64-112",
        "status": "HOLD_DEPENDENCIES_AND_GENUINE_PRODUCTION_AUTHORITY_ABSENT_WITH_FAIL_CLOSED_CERTIFICATION_MATRIX_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True, "runtime_completion_claimed": False,
        "dependency_disposition_counts": counts, "live_hold_report": live,
        "synthetic_mechanism_fixture": fixture,
        "implementation": {"script": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"), "script_sha256": sha256_file(Path(__file__).resolve()),
                           "schema": SCHEMA_PATH.as_posix(), "schema_sha256": sha256_file(root / SCHEMA_PATH),
                           "policy": POLICY_PATH.as_posix(), "policy_sha256": sha256_file(root / POLICY_PATH)},
        "decision": {"status": "blocked", "row112_acceptance": "held", "product_completion": False,
                     "blocker_codes": ["ROW112_ALL_DEPENDENCIES_NOT_ACCEPTED", "GENUINE_PRODUCTION_CERTIFICATION_PACKET_ABSENT"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--emit-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build_evidence(root)
    output = args.output or (root / DEFAULT_EVIDENCE if args.emit_evidence else None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
