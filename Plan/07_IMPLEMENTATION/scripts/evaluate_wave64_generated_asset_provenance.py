#!/usr/bin/env python3
"""Fail-closed Wave64 Row102 generated-asset provenance staging slice.

Library staging refuses authority without accepted Rows068/098/099/100/101.
Fixture mode may emit deterministic schema-validated staging receipts from
synthetic provenance packets without promoting library completion or claiming
production candidate staging runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path(
    "Plan/08_SCHEMAS/generated_asset_provenance_staging_decision.schema.json"
)
PROVENANCE_SCHEMA_PATH = Path(
    "Plan/08_SCHEMAS/generated_audio_asset_provenance.schema.json"
)
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row102_generated_asset_provenance_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-102_generated_asset_provenance.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-098": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-098_DETERMINISTIC_SOUND_VARIATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-099": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-099_NEURAL_TEXT_TO_AUDIO_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-100": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-100_REFERENCE_AUDIO_VARIATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-101": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "TRK-W64-101_VIDEO_CONDITIONED_FOLEY_CURRENT_DELTA_20260719.json"
    ),
}

EVALUATOR_REVISION = "wave64_row102_generated_asset_provenance_evaluator_v0.1.0"
POLICY_REVISION = "wave64_row102_generated_asset_provenance_policy_v0.1.0"
TRACKER_ID = "TRK-W64-102"
ITEM_ID = "ITEM-W64-102"
SCHEMA_VERSION = "1.0.0"
HASH_RE = re.compile(r"^[a-f0-9]{64}$")

REQUIRED_GATES = (
    "input_hashes",
    "prompt_hash",
    "engine_hashes",
    "seed",
    "output_hash",
    "rights",
    "staging_boundary",
)

FIXTURE_NAMES = (
    "clean_staged_candidate_accept",
    "missing_input_hashes_rejected",
    "missing_prompt_hash_rejected",
    "missing_engine_hashes_rejected",
    "missing_seed_rejected",
    "missing_output_hash_rejected",
    "rights_blocked_rejected",
    "selector_visible_boundary_rejected",
    "approved_library_path_boundary_rejected",
    "content_suppression_rejected",
)


class GeneratedAssetProvenanceError(ValueError):
    """Raised when Row102 evaluation violates fail-closed authority."""


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
        raise GeneratedAssetProvenanceError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row102_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise GeneratedAssetProvenanceError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise GeneratedAssetProvenanceError("policy_required_gates_mismatch")
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


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HASH_RE.fullmatch(value))


def path_outside_approved_library(output_path: str, policy: dict[str, Any]) -> bool:
    normalized = output_path.replace("\\", "/").lstrip("./")
    prefixes = policy["staging_rules"]["approved_library_path_prefixes"]
    return not any(normalized.startswith(prefix) for prefix in prefixes)


def evaluate_gates(
    signals: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blockers: list[str] = []
    gates: dict[str, dict[str, Any]] = {}

    input_codes: list[str] = []
    if int(signals["input_hash_count"]) < 1:
        input_codes.append("INPUT_HASHES_MISSING")
    if signals["all_input_hashes_valid"] is not True:
        input_codes.append("INPUT_HASH_INVALID")
    gates["input_hashes"] = _gate("pass") if not input_codes else _gate("fail", *input_codes)
    blockers.extend(input_codes)

    prompt_codes: list[str] = []
    if signals["prompt_hash_present"] is not True:
        prompt_codes.append("PROMPT_HASH_MISSING")
    gates["prompt_hash"] = _gate("pass") if not prompt_codes else _gate("fail", *prompt_codes)
    blockers.extend(prompt_codes)

    engine_codes: list[str] = []
    if signals["engine_model_sha256_present"] is not True:
        engine_codes.append("ENGINE_MODEL_HASH_MISSING")
    if signals["engine_configuration_sha256_present"] is not True:
        engine_codes.append("ENGINE_CONFIGURATION_HASH_MISSING")
    if signals["engine_environment_sha256_present"] is not True:
        engine_codes.append("ENGINE_ENVIRONMENT_HASH_MISSING")
    gates["engine_hashes"] = _gate("pass") if not engine_codes else _gate("fail", *engine_codes)
    blockers.extend(engine_codes)

    seed_codes: list[str] = []
    if signals["seed_present"] is not True:
        seed_codes.append("SEED_MISSING")
    gates["seed"] = _gate("pass") if not seed_codes else _gate("fail", *seed_codes)
    blockers.extend(seed_codes)

    output_codes: list[str] = []
    if signals["output_sha256_present"] is not True:
        output_codes.append("OUTPUT_HASH_MISSING")
    if signals["canonical_pcm_sha256_present"] is not True:
        output_codes.append("CANONICAL_PCM_HASH_MISSING")
    gates["output_hash"] = _gate("pass") if not output_codes else _gate("fail", *output_codes)
    blockers.extend(output_codes)

    rights_codes: list[str] = []
    if signals["rights_decision"] != "pass":
        rights_codes.append("RIGHTS_DECISION_NOT_PASS")
    if signals["rights_decision_sha256_present"] is not True:
        rights_codes.append("RIGHTS_DECISION_HASH_MISSING")
    gates["rights"] = _gate("pass") if not rights_codes else _gate("fail", *rights_codes)
    blockers.extend(rights_codes)

    staging_codes: list[str] = []
    if signals["content_based_suppression"] is True:
        staging_codes.append("CONTENT_BASED_SUPPRESSION_FORBIDDEN")
    if signals["selector_visible"] is True:
        staging_codes.append("SELECTOR_VISIBLE_BEFORE_PROMOTION")
    if signals["path_outside_approved_library"] is not True:
        staging_codes.append("APPROVED_LIBRARY_PATH_BEFORE_PROMOTION")
    if signals["promotion_state"] == "promoted":
        staging_codes.append("PROMOTED_STATE_WITHOUT_ROW104_AUTHORITY")
    allowed = set(policy["staging_rules"]["allowed_promotion_states_for_stage"])
    if signals["promotion_state"] not in allowed and signals["promotion_state"] != "promoted":
        staging_codes.append("PROMOTION_STATE_NOT_STAGING_ELIGIBLE")
    gates["staging_boundary"] = (
        _gate("pass") if not staging_codes else _gate("fail", *staging_codes)
    )
    blockers.extend(staging_codes)

    return gates, sorted(set(blockers))


def validate_decision_semantics(record: dict[str, Any]) -> None:
    if record.get("library_authority") is not False:
        raise GeneratedAssetProvenanceError("library_authority_must_be_false")
    if record.get("decision", {}).get("product_completion") is not False:
        raise GeneratedAssetProvenanceError("product_completion_must_be_false")
    if tuple(record.get("required_gates") or ()) != REQUIRED_GATES:
        raise GeneratedAssetProvenanceError("required_gates_mismatch")
    gates = record.get("gate_results") or {}
    for gate in REQUIRED_GATES:
        if gate not in gates:
            raise GeneratedAssetProvenanceError(f"missing_gate:{gate}")
    route = record["decision"]["route"]
    status = record["decision"]["status"]
    failed = [name for name, result in gates.items() if result.get("status") == "fail"]
    if failed and route == "stage_candidate":
        raise GeneratedAssetProvenanceError("failed_gates_cannot_stage")
    if failed and status == "pass":
        raise GeneratedAssetProvenanceError("failed_gates_cannot_pass_status")
    if not failed and route == "reject_candidate":
        raise GeneratedAssetProvenanceError("reject_requires_failed_gate")
    binding = record.get("provenance_binding") or {}
    if binding.get("immutable") is not True:
        raise GeneratedAssetProvenanceError("provenance_binding_must_be_immutable")
    if record.get("selector_visible") is True and route == "stage_candidate":
        raise GeneratedAssetProvenanceError("staged_candidate_cannot_be_selector_visible")


def validate_decision_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_decision_semantics(record)


def validate_provenance_record(root: Path, provenance: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, PROVENANCE_SCHEMA_PATH, "provenance_schema"))
    Draft202012Validator(schema).validate(provenance)


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def derive_signals(
    provenance: dict[str, Any],
    *,
    selector_visible: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    inputs = provenance.get("inputs") if isinstance(provenance.get("inputs"), list) else []
    valid_inputs = [
        item
        for item in inputs
        if isinstance(item, dict) and _is_hash(item.get("sha256"))
    ]
    engine = provenance.get("engine") if isinstance(provenance.get("engine"), dict) else {}
    output = provenance.get("output") if isinstance(provenance.get("output"), dict) else {}
    rights = provenance.get("rights") if isinstance(provenance.get("rights"), dict) else {}
    output_path = str(output.get("path") or "")
    rights_decision = rights.get("decision")
    if rights_decision not in {"pass", "blocked", "failed"}:
        rights_decision = "missing"
    promotion_state = provenance.get("promotion_state")
    if promotion_state not in {
        "staged_candidate",
        "rejected",
        "promoted",
        "revoked",
        "superseded",
    }:
        promotion_state = "missing"
    seed = provenance.get("seed")
    seed_present = seed is not None and seed != ""
    return {
        "input_hash_count": len(valid_inputs),
        "all_input_hashes_valid": bool(inputs) and len(valid_inputs) == len(inputs),
        "prompt_hash_present": _is_hash(provenance.get("structured_prompt_sha256")),
        "engine_model_sha256_present": _is_hash(engine.get("model_sha256")),
        "engine_configuration_sha256_present": _is_hash(engine.get("configuration_sha256")),
        "engine_environment_sha256_present": _is_hash(engine.get("environment_sha256")),
        "seed_present": seed_present,
        "output_sha256_present": _is_hash(output.get("sha256")),
        "canonical_pcm_sha256_present": _is_hash(output.get("canonical_pcm_sha256")),
        "rights_decision": rights_decision,
        "rights_decision_sha256_present": _is_hash(rights.get("rights_decision_sha256")),
        "promotion_state": promotion_state,
        "content_based_suppression": bool(provenance.get("content_based_suppression", False)),
        "path_outside_approved_library": path_outside_approved_library(output_path, policy),
        "selector_visible": bool(selector_visible),
    }


def build_decision_record(
    root: Path,
    *,
    provenance: dict[str, Any],
    selector_visible: bool,
    is_synthetic: bool,
    skip_provenance_schema: bool = False,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    if not skip_provenance_schema:
        validate_provenance_record(root, provenance)
    admissions = evaluate_all_dependency_admissions(root)
    signals = derive_signals(provenance, selector_visible=selector_visible, policy=policy)
    gates, blockers = evaluate_gates(signals, policy=policy)

    if blockers:
        route = "reject_candidate"
        status = "fail"
        reason = "provenance_or_staging_gate_failure"
    else:
        route = "stage_candidate"
        status = "pass"
        reason = "all_required_provenance_staging_gates_passed_fixture_only"

    output = provenance.get("output") if isinstance(provenance.get("output"), dict) else {}
    rights = provenance.get("rights") if isinstance(provenance.get("rights"), dict) else {}
    explanation = [
        f"route={route}",
        f"status={status}",
        f"reason={reason}",
        f"blockers={blockers or ['none']}",
        "staging_is_evidence_boundary_not_content_suppression",
        "selector_visibility_forbidden_until_promotion",
        "library_authority=false",
        "candidate_record_immutable=true",
    ]
    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "generated_asset_provenance_staging_decision",
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "candidate_id": str(provenance.get("generated_asset_id") or "unknown"),
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "selector_visible": bool(selector_visible),
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": gates,
        "signals": signals,
        "provenance_binding": {
            "immutable": True,
            "generated_asset_id": str(provenance.get("generated_asset_id") or "unknown"),
            "output_path": str(output.get("path") or "missing"),
            "output_sha256": output.get("sha256") if _is_hash(output.get("sha256")) else None,
            "canonical_pcm_sha256": (
                output.get("canonical_pcm_sha256")
                if _is_hash(output.get("canonical_pcm_sha256"))
                else None
            ),
            "structured_prompt_sha256": (
                provenance.get("structured_prompt_sha256")
                if _is_hash(provenance.get("structured_prompt_sha256"))
                else None
            ),
            "rights_decision_sha256": (
                rights.get("rights_decision_sha256")
                if _is_hash(rights.get("rights_decision_sha256"))
                else None
            ),
            "qa_state": str(provenance.get("qa_state") or "missing"),
            "promotion_state": str(provenance.get("promotion_state") or "missing"),
        },
        "decision": {
            "route": route,
            "status": status,
            "reason": reason,
            "blocker_codes": blockers,
            "explanation": explanation,
            "product_completion": False,
            "row102_acceptance": "fixture_only" if is_synthetic else "held",
        },
    }
    sealed = seal_record(record)
    validate_decision_record(root, sealed)
    return sealed


def _base_provenance(name: str, **overrides: Any) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_asset_id": f"gen_{name}",
        "generation_route": "deterministic_variation",
        "engine": {
            "name": "wave64_fixture_engine",
            "revision": "v0.0.1-fixture",
            "model": "fixture-model",
            "model_revision": "fixture-rev",
            "model_sha256": _stable_hash(f"model:{name}"),
            "configuration_sha256": _stable_hash(f"config:{name}"),
            "environment_sha256": _stable_hash(f"env:{name}"),
        },
        "inputs": [
            {"role": "source_event_manifest", "sha256": _stable_hash(f"input:{name}:0")},
            {"role": "source_clip", "sha256": _stable_hash(f"input:{name}:1")},
        ],
        "structured_prompt_sha256": _stable_hash(f"prompt:{name}"),
        "event_manifest_sha256": _stable_hash(f"event:{name}"),
        "seed": 10201,
        "output": {
            "path": f"staging/generated_candidates/{name}.wav",
            "sha256": _stable_hash(f"output:{name}"),
            "canonical_pcm_sha256": _stable_hash(f"pcm:{name}"),
            "duration_seconds": 0.42,
            "sample_rate_hz": 48000,
            "channels": 1,
        },
        "rights": {
            "decision": "pass",
            "output_use": "internal_staging_only",
            "derivative_chain": [_stable_hash(f"rights_parent:{name}")],
            "license": "project_owned",
            "attribution": "Comfy_UI_Main fixture",
            "rights_decision_sha256": _stable_hash(f"rights:{name}"),
            "commercial_use": "allowed",
            "redistribution_allowed": "forbidden",
            "engine_license": "project_owned",
        },
        "qa_state": "not_run",
        "qa_report_sha256": None,
        "promotion_state": "staged_candidate",
        "content_based_suppression": False,
    }
    provenance.update(overrides)
    return provenance


def fixture_packet(name: str) -> tuple[dict[str, Any], bool, bool]:
    """Return (provenance, selector_visible, skip_provenance_schema)."""
    if name == "clean_staged_candidate_accept":
        return _base_provenance(name), False, False
    if name == "missing_input_hashes_rejected":
        return _base_provenance(name, inputs=[]), False, True
    if name == "missing_prompt_hash_rejected":
        payload = _base_provenance(name)
        payload["structured_prompt_sha256"] = "not-a-hash"
        return payload, False, True
    if name == "missing_engine_hashes_rejected":
        payload = _base_provenance(name)
        payload["engine"]["model_sha256"] = "bad"
        payload["engine"]["configuration_sha256"] = "bad"
        payload["engine"]["environment_sha256"] = "bad"
        return payload, False, True
    if name == "missing_seed_rejected":
        payload = _base_provenance(name)
        payload["seed"] = ""
        return payload, False, True
    if name == "missing_output_hash_rejected":
        payload = _base_provenance(name)
        payload["output"]["sha256"] = "bad"
        payload["output"]["canonical_pcm_sha256"] = "bad"
        return payload, False, True
    if name == "rights_blocked_rejected":
        payload = _base_provenance(name)
        payload["rights"]["decision"] = "blocked"
        return payload, False, False
    if name == "selector_visible_boundary_rejected":
        return _base_provenance(name), True, False
    if name == "approved_library_path_boundary_rejected":
        payload = _base_provenance(name)
        payload["output"]["path"] = "library/approved/generated/footstep.wav"
        return payload, False, False
    if name == "content_suppression_rejected":
        payload = _base_provenance(name)
        payload["content_based_suppression"] = True
        return payload, False, True
    raise GeneratedAssetProvenanceError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    provenance, selector_visible, skip_schema = fixture_packet(name)
    return build_decision_record(
        root,
        provenance=provenance,
        selector_visible=selector_visible,
        is_synthetic=True,
        skip_provenance_schema=skip_schema,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW102_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_GENERATED_ASSET_STAGING_RUNTIME_ABSENT",
        "GENUINE_GENERATED_CANDIDATE_RUNTIME_PROOF_ABSENT",
        "ROW098_099_100_101_GENERATION_ROUTE_AUTHORITY_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-102_generated_asset_provenance",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_GENERATED_ASSET_STAGING_RUNTIME_ABSENT",
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
        "provenance_schema": {
            "path": str(PROVENANCE_SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(
                resolve_under(root, PROVENANCE_SCHEMA_PATH, "provenance_schema")
            ),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove input/prompt/engine/seed/output/rights and "
                "staging-boundary gates; they do not accept Row102 library completion "
                "or substitute for genuine generation-route runtime staging."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row102_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Keep Row068 rights authority; accept Rows098/099/100/101 generation "
                "routes; stage genuine generated candidates outside the approved library "
                "with immutable provenance bindings; keep selector visibility false until "
                "Row104 promotion; then replace this hold packet."
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
    parser.add_argument("--fixture", default="clean_staged_candidate_accept")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise GeneratedAssetProvenanceError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise GeneratedAssetProvenanceError(
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
