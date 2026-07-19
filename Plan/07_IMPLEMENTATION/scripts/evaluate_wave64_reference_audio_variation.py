#!/usr/bin/env python3
"""Fail-closed Wave64 Row100 reference-audio variation slice.

Library evaluation refuses authority without accepted
Rows068/072/073/083/098/099. Fixture mode may emit deterministic
schema-validated variation receipts from synthetic candidate packets
without promoting library completion or claiming production audio-to-audio
variation authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/reference_audio_variation_evaluation.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row100_reference_audio_variation_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-100_reference_audio_variation.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-072": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-073": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-083": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-083_RETRIEVAL_FALLBACK_CALIBRATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-098": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-098_DETERMINISTIC_SOUND_VARIATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-099": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-099_NEURAL_TEXT_TO_AUDIO_CURRENT_DELTA_20260719.json"
    ),
}

EVALUATOR_REVISION = "wave64_row100_reference_audio_variation_evaluator_v0.1.0"
POLICY_REVISION = "wave64_row100_reference_audio_variation_policy_v0.1.0"
TRACKER_ID = "TRK-W64-100"
ITEM_ID = "ITEM-W64-100"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "source_rights",
    "conditioning_strength",
    "structure_preservation",
    "variation_measure",
    "unexpected_class_reject",
)

ALLOWED_OPERATIONS = (
    "variation",
    "inpainting",
    "continuation",
    "style_transfer",
)

FIXTURE_NAMES = (
    "clean_reference_variation_accept",
    "derivative_rights_rejected",
    "conditioning_strength_out_of_bounds_rejected",
    "structure_not_preserved_rejected",
    "variation_too_weak_rejected",
    "variation_too_strong_identity_drift_rejected",
    "timing_loss_rejected",
    "unwanted_speech_rejected",
    "unwanted_music_rejected",
)


class ReferenceAudioVariationError(ValueError):
    """Raised when Row100 evaluation violates fail-closed authority."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ReferenceAudioVariationError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row100_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise ReferenceAudioVariationError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise ReferenceAudioVariationError("policy_required_gates_mismatch")
    if tuple(payload.get("allowed_operations") or ()) != ALLOWED_OPERATIONS:
        raise ReferenceAudioVariationError("policy_allowed_operations_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    blocker_code: str,
    absent_code: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    if not path.is_file():
        return {
            "tracker_id": tracker_id,
            "dependency_satisfied": False,
            "blocker_codes": [absent_code],
            "row_complete": False,
            "status": "",
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    row_suffix = tracker_id.rsplit("-", 1)[-1].lower()
    exact_acceptance = str(decision.get(f"row{row_suffix}_acceptance", "")).lower()
    coarse_markers = [
        exact_acceptance,
        str(decision.get("status", "")).lower(),
        str(payload.get("qa_decision", "")).lower(),
    ]
    accepted_markers = {"accepted", "pass", "passed"}
    acceptance_hit = any(marker in accepted_markers for marker in coarse_markers if marker)
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        acceptance_hit = False
    if status_text.startswith("pass_") and row_complete:
        acceptance_hit = True
    dependency_satisfied = row_complete and acceptance_hit
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append(blocker_code)
    return {
        "tracker_id": tracker_id,
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def evaluate_all_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for tracker_id, delta_path in DEPENDENCY_DELTAS.items():
        code = tracker_id.replace("-", "_") + "_DEPENDENCY_NOT_ACCEPTED"
        absent = tracker_id.replace("-", "_") + "_DELTA_ABSENT"
        out[tracker_id] = evaluate_dependency_admission(
            root,
            delta_path=delta_path,
            tracker_id=tracker_id,
            blocker_code=code,
            absent_code=absent,
        )
    return out


def _gate(status: str, *codes: str) -> dict[str, Any]:
    return {"status": status, "reason_codes": sorted(set(codes))}


def evaluate_gates(
    signals: dict[str, Any],
    *,
    thresholds: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blockers: list[str] = []
    gates: dict[str, dict[str, Any]] = {}

    rights_codes: list[str] = []
    if signals["derivative_rights_pass"] is not True:
        rights_codes.append("DERIVATIVE_RIGHTS_DENIED")
    if signals["source_bytes_immutable"] is not True:
        rights_codes.append("SOURCE_BYTES_MUTATED")
    gates["source_rights"] = (
        _gate("pass") if not rights_codes else _gate("fail", *rights_codes)
    )
    blockers.extend(rights_codes)

    strength = float(signals["conditioning_strength"])
    strength_codes: list[str] = []
    if strength < float(thresholds["min_conditioning_strength"]):
        strength_codes.append("CONDITIONING_STRENGTH_TOO_LOW")
    if strength > float(thresholds["max_conditioning_strength"]):
        strength_codes.append("CONDITIONING_STRENGTH_TOO_HIGH")
    gates["conditioning_strength"] = (
        _gate("pass") if not strength_codes else _gate("fail", *strength_codes)
    )
    blockers.extend(strength_codes)

    structure_codes: list[str] = []
    if float(signals["structural_similarity"]) < float(thresholds["min_structural_similarity"]):
        structure_codes.append("STRUCTURE_NOT_PRESERVED")
    if float(signals["identity_drift"]) > float(thresholds["max_identity_drift"]):
        structure_codes.append("IDENTITY_DRIFT_EXCEEDED")
    if abs(float(signals["onset_offset_ms"])) > float(thresholds["max_onset_offset_ms"]):
        structure_codes.append("ONSET_TIMING_LOSS")
    if abs(float(signals["endpoint_drift_ms"])) > float(thresholds["max_endpoint_drift_ms"]):
        structure_codes.append("ENDPOINT_TIMING_LOSS")
    gates["structure_preservation"] = (
        _gate("pass") if not structure_codes else _gate("fail", *structure_codes)
    )
    blockers.extend(structure_codes)

    variation = float(signals["variation_distance"])
    variation_codes: list[str] = []
    if variation < float(thresholds["min_variation_distance"]):
        variation_codes.append("VARIATION_TOO_WEAK")
    if variation > float(thresholds["max_variation_distance"]):
        variation_codes.append("VARIATION_TOO_STRONG")
    gates["variation_measure"] = (
        _gate("pass") if not variation_codes else _gate("fail", *variation_codes)
    )
    blockers.extend(variation_codes)

    unexpected_codes: list[str] = []
    if signals["unwanted_speech"] is True:
        unexpected_codes.append("UNWANTED_SPEECH")
    if signals["unwanted_music"] is True:
        unexpected_codes.append("UNWANTED_MUSIC")
    gates["unexpected_class_reject"] = (
        _gate("pass") if not unexpected_codes else _gate("fail", *unexpected_codes)
    )
    blockers.extend(unexpected_codes)

    return gates, sorted(set(blockers))


def validate_evaluation_semantics(record: dict[str, Any]) -> None:
    if record.get("library_authority") is not False:
        raise ReferenceAudioVariationError("library_authority_must_be_false")
    if record.get("decision", {}).get("product_completion") is not False:
        raise ReferenceAudioVariationError("product_completion_must_be_false")
    gates = record.get("gate_results") or {}
    if tuple(record.get("required_gates") or ()) != REQUIRED_GATES:
        raise ReferenceAudioVariationError("required_gates_mismatch")
    for gate in REQUIRED_GATES:
        if gate not in gates:
            raise ReferenceAudioVariationError(f"missing_gate:{gate}")
    if record.get("operation") not in ALLOWED_OPERATIONS:
        raise ReferenceAudioVariationError("unknown_operation")
    route = record["decision"]["route"]
    status = record["decision"]["status"]
    failed = [name for name, result in gates.items() if result.get("status") == "fail"]
    if failed and route == "accept_candidate":
        raise ReferenceAudioVariationError("failed_gates_cannot_accept")
    if failed and status == "pass":
        raise ReferenceAudioVariationError("failed_gates_cannot_pass_status")
    if not failed and route == "reject_candidate":
        raise ReferenceAudioVariationError("reject_requires_failed_gate")
    if record["source_pcm_sha256"] == record["candidate_pcm_sha256"]:
        raise ReferenceAudioVariationError("candidate_must_differ_from_source_pcm")


def validate_evaluation_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_evaluation_semantics(record)


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def build_evaluation_record(
    root: Path,
    *,
    packet: dict[str, Any],
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    thresholds = policy["thresholds"]
    signals = {
        "derivative_rights_pass": bool(packet["derivative_rights_pass"]),
        "conditioning_strength": float(packet["conditioning_strength"]),
        "structural_similarity": float(packet["structural_similarity"]),
        "variation_distance": float(packet["variation_distance"]),
        "identity_drift": float(packet["identity_drift"]),
        "onset_offset_ms": float(packet["onset_offset_ms"]),
        "endpoint_drift_ms": float(packet["endpoint_drift_ms"]),
        "unwanted_speech": bool(packet["unwanted_speech"]),
        "unwanted_music": bool(packet["unwanted_music"]),
        "source_bytes_immutable": bool(packet["source_bytes_immutable"]),
    }
    gates, blockers = evaluate_gates(signals, thresholds=thresholds)

    if blockers:
        route = "reject_candidate"
        status = "fail"
        reason = "reference_variation_gate_failure"
    else:
        route = "accept_candidate"
        status = "pass"
        reason = "all_required_gates_passed_fixture_only"

    explanation = [
        f"route={route}",
        f"status={status}",
        f"reason={reason}",
        f"operation={packet['operation']}",
        f"blockers={blockers or ['none']}",
        "source_bytes_remain_immutable",
        "library_authority=false",
        "fixture_calibration_does_not_grant_production_variation_authority",
    ]

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "reference_audio_variation_evaluation",
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "candidate_id": str(packet["candidate_id"]),
        "source_pcm_sha256": str(packet["source_pcm_sha256"]),
        "candidate_pcm_sha256": str(packet["candidate_pcm_sha256"]),
        "event_id": str(packet["event_id"]),
        "operation": str(packet["operation"]),
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": gates,
        "signals": signals,
        "decision": {
            "route": route,
            "status": status,
            "reason": reason,
            "blocker_codes": blockers,
            "explanation": explanation,
            "product_completion": False,
            "row100_acceptance": "fixture_only" if is_synthetic else "held",
        },
    }
    sealed = seal_record(record)
    validate_evaluation_record(root, sealed)
    return sealed


def _base_packet(
    name: str,
    *,
    operation: str = "variation",
    **overrides: Any,
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "candidate_id": f"cand_{name}",
        "source_pcm_sha256": _stable_hash(f"source:{name}"),
        "candidate_pcm_sha256": _stable_hash(f"candidate:{name}"),
        "event_id": f"evt_{name}",
        "operation": operation,
        "derivative_rights_pass": True,
        "conditioning_strength": 0.45,
        "structural_similarity": 0.86,
        "variation_distance": 0.22,
        "identity_drift": 0.14,
        "onset_offset_ms": 3.0,
        "endpoint_drift_ms": 5.0,
        "unwanted_speech": False,
        "unwanted_music": False,
        "source_bytes_immutable": True,
    }
    packet.update(overrides)
    return packet


def fixture_candidate_packet(name: str) -> dict[str, Any]:
    if name == "clean_reference_variation_accept":
        return _base_packet(name, operation="variation")
    if name == "derivative_rights_rejected":
        return _base_packet(
            name,
            operation="inpainting",
            derivative_rights_pass=False,
        )
    if name == "conditioning_strength_out_of_bounds_rejected":
        return _base_packet(
            name,
            operation="style_transfer",
            conditioning_strength=0.97,
        )
    if name == "structure_not_preserved_rejected":
        return _base_packet(
            name,
            operation="continuation",
            structural_similarity=0.41,
            identity_drift=0.52,
        )
    if name == "variation_too_weak_rejected":
        return _base_packet(
            name,
            variation_distance=0.02,
            structural_similarity=0.99,
            identity_drift=0.01,
        )
    if name == "variation_too_strong_identity_drift_rejected":
        return _base_packet(
            name,
            variation_distance=0.78,
            identity_drift=0.61,
            structural_similarity=0.48,
        )
    if name == "timing_loss_rejected":
        return _base_packet(
            name,
            onset_offset_ms=30.0,
            endpoint_drift_ms=42.0,
        )
    if name == "unwanted_speech_rejected":
        return _base_packet(
            name,
            unwanted_speech=True,
        )
    if name == "unwanted_music_rejected":
        return _base_packet(
            name,
            unwanted_music=True,
        )
    raise ReferenceAudioVariationError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_candidate_packet(name)
    return build_evaluation_record(root, packet=packet, is_synthetic=True)


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW100_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "REFERENCE_CONDITIONED_VARIATION_RUNTIME_ABSENT",
        "GENUINE_AUDIO_TO_AUDIO_VARIATION_PROOF_ABSENT",
        "ROW098_SOUND_VARIATION_ENGINE_AUTHORITY_ABSENT",
        "ROW099_NEURAL_TEXT_TO_AUDIO_ROUTER_AUTHORITY_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-100_reference_audio_variation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_REFERENCE_AUDIO_VARIATION_RUNTIME_ABSENT",
        "required_gates": list(REQUIRED_GATES),
        "dependency_admissions": admissions,
        "policy_registry": {
            "path": str(POLICY_PATH).replace("\\", "/"),
            "revision": policy["revision"],
            "authority": policy.get("authority"),
            "sha256": sha256_file(policy_path),
        },
        "schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(resolve_under(root, SCHEMA_PATH, "schema")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove derivative-rights, conditioning-strength, "
                "structure/timing preservation, variation bounds, and unwanted "
                "speech/music rejection; they do not accept Row100 library completion "
                "or substitute for Rows068/072/073/083/098/099 authority."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row100_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows068, 072, 073, 083, 098, and 099; bind a reference-"
                "conditioned audio-to-audio variation runtime with measured structure/"
                "variation/timing gates; reject identity drift and unwanted speech/"
                "music; execute genuine waveform/spectrogram review; then replace "
                "this hold packet."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture"), default="library")
    parser.add_argument("--fixture", default="clean_reference_variation_accept")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise ReferenceAudioVariationError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise ReferenceAudioVariationError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["route"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
