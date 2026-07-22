#!/usr/bin/env python3
"""Fail-closed Wave64 Row148 speech full-system certification gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row148_speech_full_system_certification_policy_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/speech_full_system_certification_report.schema.json")
TRACKER_PATH = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW148.json")
POLICY_REVISION = "wave64_row148_speech_full_system_certification_policy_v0.1.0"
REQUIRED_TRACKERS = tuple(f"TRK-W64-{number:03d}" for number in range(113, 148))
REQUIRED_GATES = (
    "genuine_runtime", "rights", "provenance", "independent_playback",
    "identity_continuity", "av_sync", "adversarial_qa",
    "comfyui_integration", "replay", "rollback",
)
MINIMUM_COVERAGE = {"character_sha256s": 2, "engine_ids": 2, "scene_sha256s": 3, "mux_video_sha256s": 3}
PASS_PREFIXES = ("pass", "accepted", "complete")


class CertificationError(ValueError):
    """Raised when certification evidence is incomplete or contradictory."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row148:{label}".encode()).hexdigest()


def tracker_rows(root: Path) -> dict[str, dict[str, str]]:
    with (root / TRACKER_PATH).open(encoding="utf-8-sig", newline="") as handle:
        return {row["Tracker_ID"]: row for row in csv.DictReader(handle)}


def inspect_dependencies(root: Path) -> list[dict[str, Any]]:
    rows = tracker_rows(root)
    results = []
    for tracker_id in REQUIRED_TRACKERS:
        row = rows[tracker_id]
        declared = Path(row["Evidence_Path"])
        path = root / declared
        status = row["Status"]
        row_complete = row["Status_Decision"].lower().startswith(("pass", "accepted", "complete"))
        accepted = row_complete and status.lower().startswith(PASS_PREFIXES) and path.is_file()
        results.append({
            "tracker_id": tracker_id,
            "evidence_path": declared.as_posix() if path.is_file() else None,
            "evidence_sha256": sha256_file(path) if path.is_file() else None,
            "row_complete": row_complete,
            "status": status,
            "accepted": accepted,
        })
    return results


def empty_gate() -> dict[str, Any]:
    return {"evidence_path": None, "evidence_sha256": None, "artifact_sha256": None, "accepted": False, "is_synthetic": False}


def synthetic_gate(name: str) -> dict[str, Any]:
    return {"evidence_path": f"fixtures/{name}.json", "evidence_sha256": stable_hash(f"evidence:{name}"), "artifact_sha256": stable_hash(f"artifact:{name}"), "accepted": True, "is_synthetic": True}


def synthetic_dependencies() -> list[dict[str, Any]]:
    return [{"tracker_id": tracker, "evidence_path": f"fixtures/{tracker}.json", "evidence_sha256": stable_hash(tracker), "row_complete": True, "status": "PASS_FIXTURE", "accepted": True} for tracker in REQUIRED_TRACKERS]


def evaluate(*, root: Path, dependencies: list[dict[str, Any]], gates: dict[str, dict[str, Any]], coverage: dict[str, list[str]], is_synthetic: bool) -> dict[str, Any]:
    if [item["tracker_id"] for item in dependencies] != list(REQUIRED_TRACKERS):
        raise CertificationError("dependency_set_or_order_mismatch")
    if set(gates) != set(REQUIRED_GATES):
        raise CertificationError("production_gate_set_mismatch")
    if set(coverage) != set(MINIMUM_COVERAGE):
        raise CertificationError("coverage_set_mismatch")
    blockers = [f"{item['tracker_id'].replace('-', '_')}_NOT_ACCEPTED" for item in dependencies if not item["accepted"]]
    for name, gate in gates.items():
        if not gate["accepted"]:
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_NOT_ACCEPTED")
        if gate["is_synthetic"]:
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_SYNTHETIC")
        if not all(gate[key] for key in ("evidence_path", "evidence_sha256", "artifact_sha256")):
            blockers.append(f"PRODUCTION_GATE_{name.upper()}_BINDING_INCOMPLETE")
    for name, minimum in MINIMUM_COVERAGE.items():
        values = coverage[name]
        if len(values) != len(set(values)) or len(values) < minimum:
            blockers.append(f"{name.upper()}_COVERAGE_INSUFFICIENT")
    if is_synthetic:
        blockers.append("SYNTHETIC_CERTIFICATION_FORBIDDEN")
    blockers = list(dict.fromkeys(blockers))
    accepted = not blockers
    report = {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-148", "item_id": "ITEM-W64-148",
        "record_type": "speech_full_system_certification_report", "policy_revision": POLICY_REVISION,
        "is_synthetic": is_synthetic, "dependency_admissions": dependencies,
        "production_gates": gates, "coverage": coverage,
        "decision": {"status": "pass" if accepted else "blocked", "certification_authority": accepted,
                     "row148_acceptance": "accepted" if accepted else ("fixture_only" if is_synthetic else "held"),
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
    if report["decision"]["certification_authority"] and (report["is_synthetic"] or report["decision"]["blocker_codes"]):
        raise CertificationError("invalid_certification_authority")


def fixture_coverage() -> dict[str, list[str]]:
    return {
        "character_sha256s": [stable_hash(f"character:{index}") for index in range(2)],
        "engine_ids": [f"fixture_engine_{index}" for index in range(2)],
        "scene_sha256s": [stable_hash(f"scene:{index}") for index in range(3)],
        "mux_video_sha256s": [stable_hash(f"mux:{index}") for index in range(3)],
    }


def build_evidence(root: Path) -> dict[str, Any]:
    dependencies = inspect_dependencies(root)
    live = evaluate(root=root, dependencies=dependencies, gates={name: empty_gate() for name in REQUIRED_GATES}, coverage={name: [] for name in MINIMUM_COVERAGE}, is_synthetic=False)
    fixture = evaluate(root=root, dependencies=synthetic_dependencies(), gates={name: synthetic_gate(name) for name in REQUIRED_GATES}, coverage=fixture_coverage(), is_synthetic=True)
    accepted_count = sum(item["accepted"] for item in dependencies)
    return {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-148", "item_id": "ITEM-W64-148",
        "status": "IMPLEMENTED_FAIL_CLOSED_CERTIFICATION_MATRIX_RUNTIME_AND_PRODUCTION_AUTHORITY_HELD",
        "row_complete": False, "implementation_completion_claimed": True, "runtime_completion_claimed": False,
        "dependency_counts": {"required": 35, "accepted": accepted_count, "held": 35 - accepted_count},
        "live_hold_report": live, "synthetic_mechanism_fixture": fixture,
        "implementation": {"script": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"), "script_sha256": sha256_file(Path(__file__).resolve()), "schema": SCHEMA_PATH.as_posix(), "schema_sha256": sha256_file(root / SCHEMA_PATH), "policy": POLICY_PATH.as_posix(), "policy_sha256": sha256_file(root / POLICY_PATH)},
        "decision": {"status": "blocked", "row148_acceptance": "held", "product_completion": False, "blocker_codes": ["ROW148_ALL_DEPENDENCIES_NOT_ACCEPTED", "GENUINE_MULTI_CHARACTER_ENGINE_SCENE_CERTIFICATION_PACKET_ABSENT"]},
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
