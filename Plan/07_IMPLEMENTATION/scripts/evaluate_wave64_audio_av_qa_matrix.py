#!/usr/bin/env python3
"""Fail-closed Wave64 Row106 audio/AV QA matrix evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_av_qa_matrix_evaluation.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row106_audio_av_qa_matrix_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-106_audio_av_qa_matrix.json"
)
DEPENDENCY_DELTAS = {
    "TRK-W64-090": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-090_CONTACT_INFERENCE_OWNERSHIP_CURRENT_DELTA_20260719.json"),
    "TRK-W64-091": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"),
    "TRK-W64-097": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-097_SAMPLE_ACCURATE_MIX_MUX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-103": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-103_GENERATED_SOUND_QA_CURRENT_DELTA_20260719.json"),
    "TRK-W64-105": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_AUDIO_END_TO_END_ORCHESTRATOR_CURRENT_DELTA_20260722.json"),
}
EVALUATOR_REVISION = "wave64_row106_audio_av_qa_matrix_evaluator_v0.1.0"
POLICY_REVISION = "wave64_row106_audio_av_qa_matrix_policy_v0.1.0"
TRACKER_ID = "TRK-W64-106"
ITEM_ID = "ITEM-W64-106"
REQUIRED_DIMENSIONS = (
    "event_coverage", "false_event", "contact_offset", "endpoint_drift",
    "semantic_match", "room_consistency", "global_review",
)
FIXTURE_NAMES = (
    "all_dimensions_pass", "event_coverage_fail", "false_event_fail",
    "contact_offset_fail", "endpoint_drift_fail", "semantic_match_fail",
    "room_consistency_fail", "global_review_fail", "technical_fail",
    "single_metric_cannot_grant_authority", "binding_mismatch_rejected",
)


class AudioAVMatrixError(ValueError):
    """Raised for malformed or authority-invalid Row106 input."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row106:{label}".encode()).hexdigest()


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for tracker_id, relative in DEPENDENCY_DELTAS.items():
        path = root / relative
        if not path.is_file():
            result[tracker_id] = {
                "tracker_id": tracker_id, "path": relative.as_posix(),
                "sha256": "0" * 64, "row_complete": False,
                "dependency_satisfied": False, "status": "ABSENT",
            }
            continue
        payload = load_json(path)
        row_complete = payload.get("row_complete") is True
        status = str(payload.get("status", ""))
        accepted = row_complete and not status.lower().startswith("hold")
        result[tracker_id] = {
            "tracker_id": tracker_id, "path": relative.as_posix(),
            "sha256": sha256_file(path), "row_complete": row_complete,
            "dependency_satisfied": accepted, "status": status,
        }
    return result


def base_packet(name: str) -> dict[str, Any]:
    run_id = f"run_{name}"
    video = stable_hash(f"video:{name}")
    audio = stable_hash(f"audio:{name}")
    bindings = [
        {"component": component, "receipt_sha256": stable_hash(f"{component}:{name}"),
         "run_id": run_id, "video_sha256": video, "audio_sha256": audio}
        for component in ("event_manifest", "mix_mux", "generated_sound_qa", "global_review")
    ]
    return {
        "run_id": run_id, "video_sha256": video, "audio_sha256": audio,
        "component_bindings": bindings,
        "metrics": {
            "event_coverage": 0.98, "false_event": 0.0, "contact_offset": 5.0,
            "endpoint_drift": 4.0, "semantic_match": 0.91,
            "room_consistency": 0.9, "global_review": 0.92,
        },
        "technical_checks": {
            "decode_ok": True, "full_duration_reviewed": True, "clipping": False,
            "true_peak_dbfs": -2.0, "integrated_loudness_lufs": -18.0,
            "dialogue_masking_score": 0.1, "repetition_score": 0.1,
        },
    }


def fixture_packet(name: str) -> dict[str, Any]:
    if name not in FIXTURE_NAMES:
        raise AudioAVMatrixError(f"unknown_fixture:{name}")
    packet = base_packet(name)
    failures = {
        "event_coverage_fail": ("event_coverage", 0.7),
        "false_event_fail": ("false_event", 0.2),
        "contact_offset_fail": ("contact_offset", 45.0),
        "endpoint_drift_fail": ("endpoint_drift", 55.0),
        "semantic_match_fail": ("semantic_match", 0.4),
        "room_consistency_fail": ("room_consistency", 0.4),
        "global_review_fail": ("global_review", 0.5),
    }
    if name in failures:
        key, value = failures[name]
        packet["metrics"][key] = value
    elif name == "technical_fail":
        packet["technical_checks"].update({"clipping": True, "decode_ok": False})
    elif name == "single_metric_cannot_grant_authority":
        packet["metrics"].update({"semantic_match": 0.999, "event_coverage": 0.4})
    elif name == "binding_mismatch_rejected":
        packet["component_bindings"][2]["audio_sha256"] = stable_hash("wrong_audio")
    return packet


def _dimension(value: float, threshold: float, comparison: str) -> dict[str, Any]:
    passed = value >= threshold if comparison == "gte" else abs(value) <= threshold
    return {"value": value, "threshold": threshold, "comparison": comparison,
            "status": "pass" if passed else "fail"}


def validate_semantics(record: dict[str, Any]) -> None:
    failed = [key for key, value in record["dimensions"].items() if value["status"] != "pass"]
    if failed and record["decision"]["route"] == "accept_fixture":
        raise AudioAVMatrixError("failed_dimensions_cannot_accept")
    if record["is_synthetic"] and record["release_authority"]:
        raise AudioAVMatrixError("synthetic_release_authority_forbidden")
    if record["decision"]["product_completion"]:
        raise AudioAVMatrixError("product_completion_forbidden")


def validate_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(root / SCHEMA_PATH)
    Draft202012Validator(schema).validate(record)
    expected = deepcopy(record)
    receipt = expected.pop("receipt_sha256")
    if receipt != hashlib.sha256(canonical_bytes(expected)).hexdigest():
        raise AudioAVMatrixError("receipt_sha256_mismatch")
    validate_semantics(record)


def evaluate(root: Path, packet: dict[str, Any], *, is_synthetic: bool) -> dict[str, Any]:
    policy = load_json(root / POLICY_PATH)
    if policy.get("revision") != POLICY_REVISION:
        raise AudioAVMatrixError("policy_revision_mismatch")
    thresholds = policy["thresholds"]
    metrics = packet["metrics"]
    dimensions = {
        "event_coverage": _dimension(float(metrics["event_coverage"]), thresholds["minimum_event_coverage"], "gte"),
        "false_event": _dimension(float(metrics["false_event"]), thresholds["maximum_false_event_rate"], "lte"),
        "contact_offset": _dimension(float(metrics["contact_offset"]), thresholds["maximum_contact_offset_ms"], "abs_lte"),
        "endpoint_drift": _dimension(float(metrics["endpoint_drift"]), thresholds["maximum_endpoint_drift_ms"], "abs_lte"),
        "semantic_match": _dimension(float(metrics["semantic_match"]), thresholds["minimum_semantic_match"], "gte"),
        "room_consistency": _dimension(float(metrics["room_consistency"]), thresholds["minimum_room_consistency"], "gte"),
        "global_review": _dimension(float(metrics["global_review"]), thresholds["minimum_global_review"], "gte"),
    }
    blockers = [f"{name.upper()}_FAILED" for name, gate in dimensions.items() if gate["status"] == "fail"]
    bindings = packet["component_bindings"]
    for binding in bindings:
        if any(binding[field] != packet[field] for field in ("run_id", "video_sha256", "audio_sha256")):
            blockers.append("COMPONENT_MEDIA_BINDING_MISMATCH")
            break
    tech = packet["technical_checks"]
    if not tech["decode_ok"]:
        blockers.append("DECODE_FAILED")
    if not tech["full_duration_reviewed"]:
        blockers.append("FULL_DURATION_REVIEW_ABSENT")
    if tech["clipping"] or tech["true_peak_dbfs"] > thresholds["maximum_true_peak_dbfs"]:
        blockers.append("CLIPPING_OR_TRUE_PEAK_FAILED")
    if not thresholds["integrated_loudness_min_lufs"] <= tech["integrated_loudness_lufs"] <= thresholds["integrated_loudness_max_lufs"]:
        blockers.append("LOUDNESS_FAILED")
    if tech["dialogue_masking_score"] > thresholds["maximum_dialogue_masking_score"]:
        blockers.append("DIALOGUE_MASKING_FAILED")
    if tech["repetition_score"] > thresholds["maximum_repetition_score"]:
        blockers.append("REPETITION_FAILED")
    admissions = dependency_admissions(root)
    all_dependencies = all(item["dependency_satisfied"] for item in admissions.values())
    if not is_synthetic and not all_dependencies:
        blockers.append("ROW106_DEPENDENCIES_NOT_ACCEPTED")
    if not is_synthetic:
        blockers.extend(["GENUINE_MEDIA_REVIEW_AUTHORITY_ABSENT", "COMBINED_PLAYBACK_REVIEW_ABSENT"])
    blockers = list(dict.fromkeys(blockers))
    if blockers:
        route, status, acceptance = ("reject", "fail", "rejected") if is_synthetic else ("hold", "blocked", "held")
    else:
        route, status, acceptance = "accept_fixture", "pass", "fixture_only"
    record = {
        "schema_version": "1.0.0", "tracker_id": TRACKER_ID, "item_id": ITEM_ID,
        "record_type": "audio_av_qa_matrix_evaluation", "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION, "run_id": packet["run_id"],
        "video_sha256": packet["video_sha256"], "audio_sha256": packet["audio_sha256"],
        "is_synthetic": is_synthetic, "release_authority": False,
        "dependency_admissions": admissions, "component_bindings": bindings,
        "dimensions": dimensions, "technical_checks": tech,
        "decision": {"route": route, "status": status, "blocker_codes": blockers,
                     "product_completion": False, "row106_acceptance": acceptance},
    }
    record["receipt_sha256"] = hashlib.sha256(canonical_bytes(record)).hexdigest()
    validate_record(root, record)
    return record


def build_evidence(root: Path) -> dict[str, Any]:
    records = [evaluate(root, fixture_packet(name), is_synthetic=True) for name in FIXTURE_NAMES]
    live = evaluate(root, base_packet("production_hold"), is_synthetic=False)
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-106_audio_av_qa_matrix",
        "tracker_id": TRACKER_ID, "item_id": ITEM_ID,
        "status": "HOLD_DEPENDENCIES_AND_GENUINE_AUDIO_AV_REVIEW_ABSENT_WITH_FAIL_CLOSED_MATRIX_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True,
        "runtime_completion_claimed": False, "release_authority": False,
        "required_dimensions": list(REQUIRED_DIMENSIONS),
        "dependency_admissions": live["dependency_admissions"],
        "fixture_calibration": {"fixture_count": len(records), "records": records},
        "live_hold_evaluation": live,
        "implementation": {
            "script": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "schema": SCHEMA_PATH.as_posix(), "schema_sha256": sha256_file(root / SCHEMA_PATH),
            "policy": POLICY_PATH.as_posix(), "policy_sha256": sha256_file(root / POLICY_PATH),
        },
        "decision": {"status": "blocked", "product_completion": False,
                     "row106_acceptance": "held",
                     "blocker_codes": live["decision"]["blocker_codes"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--fixture", choices=FIXTURE_NAMES)
    parser.add_argument("--emit-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    payload = evaluate(root, fixture_packet(args.fixture), is_synthetic=True) if args.fixture else build_evidence(root)
    output = args.output or (root / DEFAULT_EVIDENCE if args.emit_evidence else None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
