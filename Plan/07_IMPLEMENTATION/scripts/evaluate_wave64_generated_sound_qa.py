#!/usr/bin/env python3
"""Fail-closed Wave64 Row103 generated-sound QA slice.

Library evaluation refuses authority without accepted
Rows071/072/075/076/079/083/102. Fixture mode may emit deterministic
schema-validated multi-signal QA receipts from synthetic candidate packets
without promoting library completion or claiming production audio QA.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/generated_sound_qa_evaluation.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row103_generated_sound_qa_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-103_generated_sound_qa.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-071": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-072": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-075": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-076": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-079": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-083": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-083_RETRIEVAL_FALLBACK_CALIBRATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-102": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-102_GENERATED_ASSET_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
}

EVALUATOR_REVISION = "wave64_row103_generated_sound_qa_evaluator_v0.1.0"
POLICY_REVISION = "wave64_row103_generated_sound_qa_policy_v0.1.0"
TRACKER_ID = "TRK-W64-103"
ITEM_ID = "ITEM-W64-103"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "technical_qa",
    "semantic_qa",
    "timing_qa",
    "acoustic_qa",
    "dedup",
    "negative_evidence",
)

FIXTURE_NAMES = (
    "clean_multi_signal_accept",
    "semantic_mismatch_rejected",
    "extra_event_rejected",
    "timing_defect_rejected",
    "technical_defect_rejected",
    "unsuitable_acoustics_rejected",
    "near_duplicate_rejected",
    "single_metric_cannot_grant_authority",
    "failed_candidate_immutable_negative_evidence",
)


class GeneratedSoundQAError(ValueError):
    """Raised when Row103 evaluation violates fail-closed authority."""


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
        raise GeneratedSoundQAError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row103_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise GeneratedSoundQAError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise GeneratedSoundQAError("policy_required_gates_mismatch")
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
    expected_event_family: str,
    event_family: str,
    thresholds: dict[str, Any],
    prior_failure_codes: list[str],
    rewrite_attempt: bool,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blockers: list[str] = []
    gates: dict[str, dict[str, Any]] = {}

    technical_codes: list[str] = []
    if signals["decode_ok"] is not True:
        technical_codes.append("DECODE_FAILURE")
    if float(signals["duration_ms"]) < float(thresholds["min_duration_ms"]):
        technical_codes.append("DURATION_TOO_SHORT")
    if float(signals["silence_ratio"]) > float(thresholds["max_silence_ratio"]):
        technical_codes.append("EXCESSIVE_SILENCE")
    if signals["clipping"] is True:
        technical_codes.append("CLIPPING")
    if float(signals["true_peak_dbfs"]) > float(thresholds["max_true_peak_dbfs"]):
        technical_codes.append("TRUE_PEAK_EXCEEDED")
    if signals["spectral_defect"] is True:
        technical_codes.append("SPECTRAL_DEFECT")
    if signals["provenance_present"] is not True:
        technical_codes.append("MISSING_PROVENANCE")
    gates["technical_qa"] = (
        _gate("pass") if not technical_codes else _gate("fail", *technical_codes)
    )
    blockers.extend(technical_codes)

    semantic_codes: list[str] = []
    if event_family != expected_event_family:
        semantic_codes.append("SEMANTIC_MISMATCH")
    if float(signals["semantic_score"]) < float(thresholds["semantic_min_score"]):
        semantic_codes.append("SEMANTIC_SCORE_BELOW_THRESHOLD")
    if float(signals["material_action_score"]) < float(thresholds["material_action_min_score"]):
        semantic_codes.append("MATERIAL_ACTION_MISMATCH")
    if int(signals["extra_event_count"]) > int(thresholds["max_extra_events"]):
        semantic_codes.append("EXTRA_EVENTS")
    if signals["source_leakage"] is True:
        semantic_codes.append("SOURCE_LEAKAGE")
    # Single model metric alone cannot grant semantic authority.
    if (
        float(signals["model_metric_score"]) >= 0.99
        and float(signals["semantic_score"]) < float(thresholds["semantic_min_score"])
    ):
        semantic_codes.append("SINGLE_METRIC_AUTHORITY_DENIED")
    gates["semantic_qa"] = (
        _gate("pass") if not semantic_codes else _gate("fail", *semantic_codes)
    )
    blockers.extend(semantic_codes)

    timing_codes: list[str] = []
    if abs(float(signals["onset_offset_ms"])) > float(thresholds["max_onset_offset_ms"]):
        timing_codes.append("ONSET_OFFSET_EXCEEDED")
    if abs(float(signals["endpoint_drift_ms"])) > float(thresholds["max_endpoint_drift_ms"]):
        timing_codes.append("ENDPOINT_DRIFT_EXCEEDED")
    gates["timing_qa"] = _gate("pass") if not timing_codes else _gate("fail", *timing_codes)
    blockers.extend(timing_codes)

    acoustic_codes: list[str] = []
    if float(signals["acoustic_suitability_score"]) < 0.70:
        acoustic_codes.append("UNSUITABLE_ACOUSTICS")
    gates["acoustic_qa"] = (
        _gate("pass") if not acoustic_codes else _gate("fail", *acoustic_codes)
    )
    blockers.extend(acoustic_codes)

    dedup_codes: list[str] = []
    if float(signals["near_duplicate_similarity"]) > float(
        thresholds["max_near_duplicate_similarity"]
    ):
        dedup_codes.append("NEAR_DUPLICATE")
    gates["dedup"] = _gate("pass") if not dedup_codes else _gate("fail", *dedup_codes)
    blockers.extend(dedup_codes)

    negative_codes: list[str] = []
    if rewrite_attempt and prior_failure_codes:
        negative_codes.append("NEGATIVE_EVIDENCE_REWRITE_BLOCKED")
    if prior_failure_codes and not rewrite_attempt:
        # Prior failures retained as immutable evidence without blocking a fresh
        # synthetic packet that is not attempting rewrite-to-pass.
        pass
    gates["negative_evidence"] = (
        _gate("pass") if not negative_codes else _gate("fail", *negative_codes)
    )
    blockers.extend(negative_codes)

    return gates, sorted(set(blockers))


def validate_evaluation_semantics(record: dict[str, Any]) -> None:
    if record.get("library_authority") is not False:
        raise GeneratedSoundQAError("library_authority_must_be_false")
    if record.get("decision", {}).get("product_completion") is not False:
        raise GeneratedSoundQAError("product_completion_must_be_false")
    gates = record.get("gate_results") or {}
    if tuple(record.get("required_gates") or ()) != REQUIRED_GATES:
        raise GeneratedSoundQAError("required_gates_mismatch")
    for gate in REQUIRED_GATES:
        if gate not in gates:
            raise GeneratedSoundQAError(f"missing_gate:{gate}")
    route = record["decision"]["route"]
    status = record["decision"]["status"]
    failed = [name for name, result in gates.items() if result.get("status") == "fail"]
    if failed and route == "accept_candidate":
        raise GeneratedSoundQAError("failed_gates_cannot_accept")
    if failed and status == "pass":
        raise GeneratedSoundQAError("failed_gates_cannot_pass_status")
    if not failed and route == "reject_candidate":
        raise GeneratedSoundQAError("reject_requires_failed_gate")
    signals = record.get("signals") or {}
    if (
        float(signals.get("model_metric_score", 0.0)) >= 0.99
        and float(signals.get("semantic_score", 0.0)) < 0.78
        and "SINGLE_METRIC_AUTHORITY_DENIED"
        not in (gates.get("semantic_qa") or {}).get("reason_codes", [])
    ):
        raise GeneratedSoundQAError("single_metric_authority_must_be_denied")
    negative = record.get("negative_evidence") or {}
    if negative.get("immutable") is not True:
        raise GeneratedSoundQAError("negative_evidence_must_be_immutable")
    if negative.get("retained") is not True:
        raise GeneratedSoundQAError("negative_evidence_must_be_retained")


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
        "decode_ok": bool(packet["decode_ok"]),
        "duration_ms": float(packet["duration_ms"]),
        "onset_offset_ms": float(packet["onset_offset_ms"]),
        "endpoint_drift_ms": float(packet["endpoint_drift_ms"]),
        "event_count": int(packet["event_count"]),
        "extra_event_count": int(packet["extra_event_count"]),
        "silence_ratio": float(packet["silence_ratio"]),
        "true_peak_dbfs": float(packet["true_peak_dbfs"]),
        "clipping": bool(packet["clipping"]),
        "spectral_defect": bool(packet["spectral_defect"]),
        "semantic_score": float(packet["semantic_score"]),
        "material_action_score": float(packet["material_action_score"]),
        "acoustic_suitability_score": float(packet["acoustic_suitability_score"]),
        "near_duplicate_similarity": float(packet["near_duplicate_similarity"]),
        "source_leakage": bool(packet["source_leakage"]),
        "model_metric_score": float(packet["model_metric_score"]),
        "provenance_present": bool(packet["provenance_present"]),
    }
    prior_failure_codes = list(packet.get("prior_failure_codes") or [])
    rewrite_attempt = bool(packet.get("rewrite_attempt", False))
    gates, blockers = evaluate_gates(
        signals,
        expected_event_family=str(packet["expected_event_family"]),
        event_family=str(packet["event_family"]),
        thresholds=thresholds,
        prior_failure_codes=prior_failure_codes,
        rewrite_attempt=rewrite_attempt,
    )

    if blockers:
        route = "reject_candidate"
        status = "fail"
        reason = "multi_signal_gate_failure"
    else:
        route = "accept_candidate"
        status = "pass"
        reason = "all_required_gates_passed_fixture_only"

    negative_evidence = {
        "immutable": True,
        "retained": True,
        "prior_failure_codes": sorted(set(prior_failure_codes + (blockers if status == "fail" else []))),
        "rewrite_blocked": bool(rewrite_attempt and prior_failure_codes),
        "evidence_sha256": sha256_bytes(
            canonical_json_bytes(
                {
                    "candidate_pcm_sha256": packet["candidate_pcm_sha256"],
                    "prior_failure_codes": prior_failure_codes,
                    "blockers": blockers,
                    "rewrite_attempt": rewrite_attempt,
                }
            )
        ),
    }

    explanation = [
        f"route={route}",
        f"status={status}",
        f"reason={reason}",
        f"blockers={blockers or ['none']}",
        "no_single_model_metric_grants_production_authority",
        "failed_candidates_remain_immutable_negative_evidence",
        "library_authority=false",
    ]
    if rewrite_attempt and prior_failure_codes:
        explanation.append("negative_evidence_rewrite_to_pass_blocked")

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "generated_sound_qa_evaluation",
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "candidate_id": str(packet["candidate_id"]),
        "candidate_pcm_sha256": str(packet["candidate_pcm_sha256"]),
        "event_id": str(packet["event_id"]),
        "event_family": str(packet["event_family"]),
        "expected_event_family": str(packet["expected_event_family"]),
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": gates,
        "signals": signals,
        "negative_evidence": negative_evidence,
        "decision": {
            "route": route,
            "status": status,
            "reason": reason,
            "blocker_codes": blockers,
            "explanation": explanation,
            "product_completion": False,
            "row103_acceptance": "fixture_only" if is_synthetic else "held",
        },
    }
    sealed = seal_record(record)
    validate_evaluation_record(root, sealed)
    return sealed


def _base_packet(
    name: str,
    *,
    event_family: str = "footstep_wood_heel",
    expected_event_family: str = "footstep_wood_heel",
    **overrides: Any,
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "candidate_id": f"cand_{name}",
        "candidate_pcm_sha256": _stable_hash(f"pcm:{name}"),
        "event_id": f"evt_{name}",
        "event_family": event_family,
        "expected_event_family": expected_event_family,
        "decode_ok": True,
        "duration_ms": 320.0,
        "onset_offset_ms": 2.0,
        "endpoint_drift_ms": 4.0,
        "event_count": 1,
        "extra_event_count": 0,
        "silence_ratio": 0.12,
        "true_peak_dbfs": -3.5,
        "clipping": False,
        "spectral_defect": False,
        "semantic_score": 0.91,
        "material_action_score": 0.88,
        "acoustic_suitability_score": 0.86,
        "near_duplicate_similarity": 0.41,
        "source_leakage": False,
        "model_metric_score": 0.83,
        "provenance_present": True,
        "prior_failure_codes": [],
        "rewrite_attempt": False,
    }
    packet.update(overrides)
    return packet


def fixture_candidate_packet(name: str) -> dict[str, Any]:
    if name == "clean_multi_signal_accept":
        return _base_packet(name)
    if name == "semantic_mismatch_rejected":
        return _base_packet(
            name,
            event_family="fabric_rustle",
            expected_event_family="footstep_wood_heel",
            semantic_score=0.42,
            material_action_score=0.40,
        )
    if name == "extra_event_rejected":
        return _base_packet(
            name,
            event_count=3,
            extra_event_count=2,
        )
    if name == "timing_defect_rejected":
        return _base_packet(
            name,
            onset_offset_ms=28.0,
            endpoint_drift_ms=40.0,
        )
    if name == "technical_defect_rejected":
        return _base_packet(
            name,
            clipping=True,
            true_peak_dbfs=0.5,
            spectral_defect=True,
        )
    if name == "unsuitable_acoustics_rejected":
        return _base_packet(
            name,
            acoustic_suitability_score=0.31,
        )
    if name == "near_duplicate_rejected":
        return _base_packet(
            name,
            near_duplicate_similarity=0.995,
        )
    if name == "single_metric_cannot_grant_authority":
        return _base_packet(
            name,
            semantic_score=0.40,
            material_action_score=0.39,
            model_metric_score=0.999,
        )
    if name == "failed_candidate_immutable_negative_evidence":
        return _base_packet(
            name,
            clipping=True,
            prior_failure_codes=["CLIPPING", "SPECTRAL_DEFECT"],
            rewrite_attempt=True,
            # Rewrite attempt tries to look clean except technical remains fail via clipping
            # and negative-evidence rewrite is blocked.
            semantic_score=0.95,
            material_action_score=0.93,
        )
    raise GeneratedSoundQAError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_candidate_packet(name)
    return build_evaluation_record(root, packet=packet, is_synthetic=True)


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW103_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "REFERENCE_CALIBRATION_CORPUS_ABSENT",
        "DEDICATED_GENERATED_SOUND_QA_RUNTIME_ABSENT",
        "GENUINE_AUDIO_QA_AND_RUNTIME_PROOF_ABSENT",
        "ROW102_PROVENANCE_STAGING_AUTHORITY_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-103_generated_sound_qa",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_GENERATED_SOUND_QA_RUNTIME_ABSENT",
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
                "Fixture records prove technical, semantic, timing, acoustic, dedup, "
                "single-metric denial, and immutable negative-evidence gates; they do not "
                "accept Row103 library completion or substitute for reference-calibrated "
                "runtime QA."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row103_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows072, 075, 076, 079, 083, and 102 (Row071 already accepted); "
                "freeze a reference calibration corpus with immutable train/calibration/"
                "final-test partitions; bind multi-signal thresholds so no single model "
                "metric grants production authority; retain failed candidates as immutable "
                "negative evidence; execute genuine generated-sound QA with waveform/"
                "spectrogram review; then replace this hold packet."
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
    parser.add_argument("--fixture", default="clean_multi_signal_accept")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise GeneratedSoundQAError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise GeneratedSoundQAError(
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
