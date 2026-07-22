#!/usr/bin/env python3
"""Fail-closed Wave64 Row099 neural text-to-audio router contract slice.

Library routing refuses authority without accepted Rows068/079/083/091.
Fixture mode may emit deterministic schema-validated candidate-batch receipts
from synthetic prompts/engines without promoting library completion or claiming
audio QA.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/neural_text_to_audio_route_receipt.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row099_neural_text_to_audio_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-099_neural_text_to_audio.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-079": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-083": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-083_RETRIEVAL_FALLBACK_CALIBRATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-091": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"
    ),
}

ENGINE_REVISION = "wave64_row099_neural_text_to_audio_engine_v0.1.0"
POLICY_REVISION = "wave64_row099_neural_text_to_audio_v0.1.0"
TRACKER_ID = "TRK-W64-099"
ITEM_ID = "ITEM-W64-099"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "structured_prompt",
    "engine_authority",
    "seeded_batch",
    "rights",
    "candidate_only",
)

FIXTURE_NAMES = (
    "eligible_engine_seeded_batch_routed",
    "missing_structured_prompt_blocked",
    "unregistered_engine_rejected",
    "rights_fail_closed_rejected",
    "duration_gate_rejected",
    "semantic_gate_rejected",
    "uniqueness_duplicate_rejected",
)


class NeuralTextToAudioError(ValueError):
    """Raised when Row099 routing violates fail-closed authority."""


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
        raise NeuralTextToAudioError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row099_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise NeuralTextToAudioError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise NeuralTextToAudioError("policy_required_gates_mismatch")
    engines = payload.get("registered_engines")
    if not isinstance(engines, list) or not engines:
        raise NeuralTextToAudioError("policy_registered_engines_missing")
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


def seal_receipt(record: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in record.items() if k != "receipt_sha256"}
    sealed = deepcopy(body)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return sealed


def lookup_registered_engine(policy: dict[str, Any], engine_id: str) -> dict[str, Any] | None:
    for item in policy.get("registered_engines") or []:
        if isinstance(item, dict) and item.get("engine_id") == engine_id:
            return item
    return None


def recompute_prompt_sha256(prompt_fields: dict[str, Any]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "event_family": prompt_fields["event_family"],
                "contact_pair": prompt_fields["contact_pair"],
                "force_class": prompt_fields["force_class"],
                "material_class": prompt_fields["material_class"],
                "duration_ms": prompt_fields["duration_ms"],
                "semantic_target": prompt_fields["semantic_target"],
                "rights_decision": prompt_fields["rights_decision"],
            }
        )
    )


def derive_candidate_pcm_sha256(
    *,
    prompt_sha256: str,
    engine_id: str,
    model_id: str,
    config_id: str,
    seed: int,
    duration_ms: int,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "prompt_sha256": prompt_sha256,
                "engine_id": engine_id,
                "model_id": model_id,
                "config_id": config_id,
                "seed": seed,
                "duration_ms": duration_ms,
                "transform": "wave64_row099_deterministic_tta_candidate_v0",
            }
        )
    )


def recompute_batch_sha256(
    *,
    prompt_sha256: str,
    engine: dict[str, Any],
    admitted: list[dict[str, Any]],
    seeds: list[int],
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "engine_revision": ENGINE_REVISION,
                "policy_revision": POLICY_REVISION,
                "prompt_sha256": prompt_sha256,
                "engine_id": engine["engine_id"],
                "model_id": engine["model_id"],
                "config_id": engine["config_id"],
                "seeds": seeds,
                "candidates": [
                    {
                        "candidate_id": item["candidate_id"],
                        "seed": item["seed"],
                        "pcm_sha256": item["pcm_sha256"],
                        "duration_ms": item["duration_ms"],
                    }
                    for item in admitted
                ],
            }
        )
    )


def evaluate_structured_prompt(
    prompt: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(prompt, dict):
        return (
            {"status": "fail", "reason_codes": ["MISSING_STRUCTURED_PROMPT"]},
            ["MISSING_STRUCTURED_PROMPT"],
        )
    required = (
        "event_family",
        "contact_pair",
        "force_class",
        "material_class",
        "duration_ms",
        "semantic_target",
        "rights_decision",
    )
    missing = [key for key in required if not prompt.get(key) and prompt.get(key) != 0]
    if missing:
        return (
            {"status": "fail", "reason_codes": ["INCOMPLETE_STRUCTURED_PROMPT"]},
            ["INCOMPLETE_STRUCTURED_PROMPT"],
        )
    expected = recompute_prompt_sha256(prompt)
    if str(prompt.get("prompt_sha256") or "") != expected:
        return (
            {"status": "fail", "reason_codes": ["STRUCTURED_PROMPT_HASH_MISMATCH"]},
            ["STRUCTURED_PROMPT_HASH_MISMATCH"],
        )
    return {"status": "pass", "reason_codes": []}, []


def evaluate_engine_authority(
    engine_input: dict[str, Any],
    registered: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    if registered is None:
        binding = {
            "engine_id": str(engine_input.get("engine_id") or "unknown"),
            "model_id": str(engine_input.get("model_id") or "unknown"),
            "config_id": str(engine_input.get("config_id") or "unknown"),
            "license_class": str(engine_input.get("license_class") or "unknown"),
            "output_use_class": str(engine_input.get("output_use_class") or "unknown"),
            "derivative_rights": str(engine_input.get("derivative_rights") or "unknown"),
            "registered": False,
        }
        return (
            {"status": "fail", "reason_codes": ["UNREGISTERED_ENGINE"]},
            binding,
            ["UNREGISTERED_ENGINE"],
        )
    binding = {
        "engine_id": registered["engine_id"],
        "model_id": registered["model_id"],
        "config_id": registered["config_id"],
        "license_class": registered["license_class"],
        "output_use_class": registered["output_use_class"],
        "derivative_rights": registered["derivative_rights"],
        "registered": True,
    }
    mismatches: list[str] = []
    for key in ("model_id", "config_id", "license_class", "output_use_class", "derivative_rights"):
        if str(engine_input.get(key) or "") != str(registered.get(key) or ""):
            mismatches.append("ENGINE_BINDING_MISMATCH")
            break
    if mismatches:
        binding["registered"] = False
        return (
            {"status": "fail", "reason_codes": mismatches},
            binding,
            mismatches,
        )
    return {"status": "pass", "reason_codes": []}, binding, []


def evaluate_rights(
    prompt: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    if not isinstance(prompt, dict) or prompt.get("rights_decision") != "allow":
        codes.append("PROMPT_RIGHTS_DENIED")
    for item in candidates:
        if item.get("rights_decision") != "allow":
            codes.append("CANDIDATE_RIGHTS_DENIED")
            exclusions.append(
                {
                    "candidate_id": item["candidate_id"],
                    "reason_codes": ["CANDIDATE_RIGHTS_DENIED"],
                }
            )
    if codes:
        return {"status": "fail", "reason_codes": sorted(set(codes))}, sorted(set(codes)), exclusions
    return {"status": "pass", "reason_codes": []}, [], []


def evaluate_candidate_quality(
    *,
    prompt: dict[str, Any],
    engine: dict[str, Any],
    registered: dict[str, Any],
    thresholds: dict[str, Any],
    candidates_input: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    seen_pcm: set[str] = set()
    min_dur = int(registered["min_duration_ms"])
    max_dur = int(registered["max_duration_ms"])
    tol = int(thresholds["duration_tolerance_ms"])
    target = int(prompt["duration_ms"])
    min_sem = float(thresholds["min_semantic_similarity"])
    max_sem = float(thresholds["max_semantic_similarity"])
    min_tech = float(thresholds["min_technical_score"])

    for raw in candidates_input:
        seed = int(raw["seed"])
        duration_ms = int(raw["duration_ms"])
        semantic = float(raw["semantic_similarity"])
        technical = float(raw["technical_score"])
        rights = str(raw.get("rights_decision") or "unknown")
        pcm = str(
            raw.get("pcm_sha256")
            or derive_candidate_pcm_sha256(
                prompt_sha256=str(prompt["prompt_sha256"]),
                engine_id=engine["engine_id"],
                model_id=engine["model_id"],
                config_id=engine["config_id"],
                seed=seed,
                duration_ms=duration_ms,
            )
        )
        candidate_id = str(raw.get("candidate_id") or f"cand_seed_{seed}")
        reason_codes: list[str] = []
        if duration_ms < min_dur or duration_ms > max_dur:
            reason_codes.append("DURATION_OUT_OF_ENGINE_BAND")
        if abs(duration_ms - target) > tol:
            reason_codes.append("DURATION_TOLERANCE_EXCEEDED")
        if semantic < min_sem or semantic > max_sem:
            reason_codes.append("SEMANTIC_OUT_OF_BAND")
        if technical < min_tech:
            reason_codes.append("TECHNICAL_SCORE_BELOW_FLOOR")
        if pcm in seen_pcm:
            reason_codes.append("PCM_DUPLICATE")
        seen_pcm.add(pcm)
        if raw.get("promotion_allowed") is True:
            reason_codes.append("CANDIDATE_PROMOTION_FORBIDDEN")
        admitted = not reason_codes and rights == "allow"
        record = {
            "candidate_id": candidate_id,
            "seed": seed,
            "duration_ms": duration_ms,
            "pcm_sha256": pcm,
            "semantic_similarity": semantic,
            "technical_score": technical,
            "rights_decision": rights,
            "promotion_allowed": False,
            "admitted": admitted,
        }
        normalized.append(record)
        if reason_codes:
            codes.extend(reason_codes)
            exclusions.append({"candidate_id": candidate_id, "reason_codes": reason_codes})
    return normalized, exclusions, sorted(set(codes))


def evaluate_seeded_batch(
    *,
    registered: dict[str, Any] | None,
    seeds: list[int],
    admitted: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if registered is None:
        return (
            {"status": "fail", "reason_codes": ["SEEDED_BATCH_ENGINE_UNAVAILABLE"]},
            ["SEEDED_BATCH_ENGINE_UNAVAILABLE"],
        )
    min_seeds = int(registered["min_seed_count"])
    max_seeds = int(registered["max_seed_count"])
    codes: list[str] = []
    if len(seeds) < min_seeds or len(seeds) > max_seeds:
        codes.append("SEED_COUNT_OUT_OF_BAND")
    if len(set(seeds)) != len(seeds):
        codes.append("DUPLICATE_SEEDS")
    if len(admitted) < min_seeds:
        codes.append("INSUFFICIENT_ADMITTED_CANDIDATES")
    if codes:
        return {"status": "fail", "reason_codes": codes}, codes
    return {"status": "pass", "reason_codes": []}, []


def validate_route_semantics(record: dict[str, Any]) -> None:
    decision = record["decision"]
    route = decision["route"]
    gate_results = record["gate_results"]
    seeded = record["seeded_batch"]
    if any(gate["status"] == "fail" for gate in gate_results.values()) and route != "blocked":
        raise NeuralTextToAudioError("candidate_batch_with_failed_gate")
    if route == "candidate_batch":
        if any(gate["status"] != "pass" for gate in gate_results.values()):
            raise NeuralTextToAudioError("candidate_batch_with_non_pass_gate")
        if not seeded.get("reconstructable"):
            raise NeuralTextToAudioError("candidate_batch_not_reconstructable")
        if not seeded.get("batch_sha256"):
            raise NeuralTextToAudioError("candidate_batch_missing_batch_hash")
        admitted = [item for item in record["candidates"] if item.get("admitted") is True]
        recomputed = recompute_batch_sha256(
            prompt_sha256=record["structured_prompt"]["prompt_sha256"],
            engine=record["engine"],
            admitted=admitted,
            seeds=list(seeded["seeds"]),
        )
        if recomputed != seeded["batch_sha256"]:
            raise NeuralTextToAudioError("seeded_batch_recompute_mismatch")
        if decision.get("blocker_codes"):
            raise NeuralTextToAudioError("candidate_batch_with_blocker_codes")
        if any(item.get("promotion_allowed") is True for item in record["candidates"]):
            raise NeuralTextToAudioError("promotion_allowed_true_forbidden")
    elif route == "blocked":
        if not decision.get("blocker_codes"):
            raise NeuralTextToAudioError("blocked_without_blocker_codes")
        if seeded.get("reconstructable") is True:
            raise NeuralTextToAudioError("blocked_marked_reconstructable")
        if seeded.get("batch_sha256") is not None:
            raise NeuralTextToAudioError("blocked_with_batch_hash")
    else:
        raise NeuralTextToAudioError(f"unknown_route:{route}")
    if record.get("library_authority") is True:
        raise NeuralTextToAudioError("library_authority_true_forbidden")
    if decision.get("product_completion") is True:
        raise NeuralTextToAudioError("product_completion_true_forbidden")


def validate_route_receipt(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_route_semantics(record)
    sealed = seal_receipt({k: v for k, v in record.items() if k != "receipt_sha256"})
    if sealed["receipt_sha256"] != record.get("receipt_sha256"):
        raise NeuralTextToAudioError("receipt_sha256_mismatch")


def build_route_record(
    root: Path,
    *,
    route_id: str,
    event_id: str,
    structured_prompt: dict[str, Any] | None,
    engine_input: dict[str, Any],
    seeds: list[int],
    candidates_input: list[dict[str, Any]],
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    thresholds = policy["quality_thresholds"]
    registered = lookup_registered_engine(policy, str(engine_input.get("engine_id") or ""))

    prompt_gate, prompt_codes = evaluate_structured_prompt(structured_prompt)
    engine_gate, engine_binding, engine_codes = evaluate_engine_authority(
        engine_input, registered
    )

    candidates: list[dict[str, Any]] = []
    quality_exclusions: list[dict[str, Any]] = []
    quality_codes: list[str] = []
    if (
        prompt_gate["status"] == "pass"
        and engine_gate["status"] == "pass"
        and isinstance(structured_prompt, dict)
        and registered is not None
    ):
        candidates, quality_exclusions, quality_codes = evaluate_candidate_quality(
            prompt=structured_prompt,
            engine=engine_binding,
            registered=registered,
            thresholds=thresholds,
            candidates_input=candidates_input,
        )

    rights_gate, rights_codes, rights_exclusions = evaluate_rights(
        structured_prompt, candidates
    )
    admitted = [item for item in candidates if item.get("admitted") is True]
    seeded_gate, seeded_codes = evaluate_seeded_batch(
        registered=registered if engine_gate["status"] == "pass" else None,
        seeds=seeds,
        admitted=admitted,
    )

    # candidate_only gate: promotion always forbidden; pass only when every candidate
    # keeps promotion_allowed false and at least one admitted candidate exists for route.
    candidate_only_codes: list[str] = []
    if any(item.get("promotion_allowed") is True for item in candidates):
        candidate_only_codes.append("CANDIDATE_PROMOTION_FORBIDDEN")
    if quality_codes or rights_codes or seeded_codes or prompt_codes or engine_codes:
        # Keep candidate_only as fail when no admissible batch can be formed.
        if not admitted:
            candidate_only_codes.append("NO_ADMITTED_CANDIDATES")
    candidate_only_gate = (
        {"status": "pass", "reason_codes": []}
        if not candidate_only_codes and admitted
        else {
            "status": "fail",
            "reason_codes": sorted(set(candidate_only_codes))
            or ["NO_ADMITTED_CANDIDATES"],
        }
    )

    blocker_codes = sorted(
        set(
            prompt_codes
            + engine_codes
            + rights_codes
            + quality_codes
            + seeded_codes
            + candidate_only_gate["reason_codes"]
        )
    )
    exclusions = quality_exclusions + rights_exclusions
    route_ok = not blocker_codes and all(
        gate["status"] == "pass"
        for gate in (
            prompt_gate,
            engine_gate,
            rights_gate,
            seeded_gate,
            candidate_only_gate,
        )
    )

    if route_ok and isinstance(structured_prompt, dict):
        batch_sha = recompute_batch_sha256(
            prompt_sha256=str(structured_prompt["prompt_sha256"]),
            engine=engine_binding,
            admitted=admitted,
            seeds=seeds,
        )
        seeded_batch = {
            "seed_count": len(seeds),
            "seeds": list(seeds),
            "batch_sha256": batch_sha,
            "admitted_candidate_ids": [item["candidate_id"] for item in admitted],
            "reconstructable": True,
        }
        # Seeded-batch gate already passed; keep explicit pass marker.
        seeded_gate = {"status": "pass", "reason_codes": []}
        route = "candidate_batch"
        status = "candidates_ready"
        reason = "all_required_gates_passed_for_synthetic_or_fixture_candidate_batch"
        acceptance = "fixture_only" if is_synthetic else "held"
    else:
        seeded_batch = {
            "seed_count": len(seeds),
            "seeds": list(seeds),
            "batch_sha256": None,
            "admitted_candidate_ids": [],
            "reconstructable": False,
        }
        if seeded_gate["status"] == "pass" and blocker_codes:
            seeded_gate = {
                "status": "skipped",
                "reason_codes": ["ROUTE_BLOCKED"],
            }
        route = "blocked"
        status = "blocked"
        reason = "fail_closed_neural_text_to_audio_prompt_engine_rights_or_candidate_blocker"
        acceptance = "held"

    # Preserve quality failures on seeded_batch when they prevented admission.
    if quality_codes and route == "blocked" and seeded_gate["status"] != "fail":
        seeded_gate = {
            "status": "fail",
            "reason_codes": sorted(set(seeded_gate.get("reason_codes", []) + quality_codes)),
        }

    prompt_payload = (
        structured_prompt
        if isinstance(structured_prompt, dict)
        else {
            "prompt_sha256": _stable_hash("missing_prompt"),
            "event_family": "unknown",
            "contact_pair": "unknown",
            "force_class": "unknown",
            "material_class": "unknown",
            "duration_ms": 1,
            "semantic_target": "unknown",
            "rights_decision": "unknown",
        }
    )

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "neural_text_to_audio_route_receipt",
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "route_id": route_id,
        "event_id": event_id,
        "structured_prompt": prompt_payload,
        "engine": engine_binding,
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": {
            "structured_prompt": prompt_gate,
            "engine_authority": engine_gate,
            "seeded_batch": seeded_gate,
            "rights": rights_gate,
            "candidate_only": candidate_only_gate,
        },
        "candidates": candidates,
        "exclusions": exclusions,
        "seeded_batch": seeded_batch,
        "decision": {
            "route": route,
            "status": status,
            "blocker_codes": blocker_codes,
            "product_completion": False,
            "row099_acceptance": acceptance,
            "reason": reason,
        },
    }
    sealed = seal_receipt(record)
    validate_route_receipt(root, sealed)
    return sealed


def _default_engine() -> dict[str, Any]:
    return {
        "engine_id": "wave64_fixture_tta_engine_v1",
        "model_id": "wave64_fixture_tta_model_v1",
        "config_id": "wave64_fixture_tta_config_v1",
        "license_class": "commercial_ok_attribution_required",
        "output_use_class": "candidate_foley_sfx_only",
        "derivative_rights": "allowed_with_attribution",
    }


def _prompt(
    *,
    event_family: str = "footstep",
    contact_pair: str = "shoe_floor",
    force_class: str = "medium",
    material_class: str = "wood",
    duration_ms: int = 240,
    semantic_target: str = "dry_wood_heel_strike",
    rights_decision: str = "allow",
) -> dict[str, Any]:
    body = {
        "event_family": event_family,
        "contact_pair": contact_pair,
        "force_class": force_class,
        "material_class": material_class,
        "duration_ms": duration_ms,
        "semantic_target": semantic_target,
        "rights_decision": rights_decision,
    }
    return {**body, "prompt_sha256": recompute_prompt_sha256(body)}


def _candidate(
    seed: int,
    *,
    duration_ms: int = 240,
    semantic_similarity: float = 0.78,
    technical_score: float = 0.88,
    rights_decision: str = "allow",
    pcm_sha256: str | None = None,
    promotion_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "candidate_id": f"cand_seed_{seed}",
        "seed": seed,
        "duration_ms": duration_ms,
        "semantic_similarity": semantic_similarity,
        "technical_score": technical_score,
        "rights_decision": rights_decision,
        "promotion_allowed": promotion_allowed,
        "pcm_sha256": pcm_sha256,
    }


def fixture_route_packet(name: str) -> dict[str, Any]:
    if name == "eligible_engine_seeded_batch_routed":
        return {
            "route_id": "route_eligible_batch",
            "event_id": "evt_footstep_wood_01",
            "structured_prompt": _prompt(),
            "engine": _default_engine(),
            "seeds": [11, 22, 33],
            "candidates": [
                _candidate(11),
                _candidate(22, semantic_similarity=0.81),
                _candidate(33, semantic_similarity=0.74, technical_score=0.91),
            ],
        }
    if name == "missing_structured_prompt_blocked":
        return {
            "route_id": "route_missing_prompt",
            "event_id": "evt_missing_prompt",
            "structured_prompt": None,
            "engine": _default_engine(),
            "seeds": [1, 2],
            "candidates": [_candidate(1), _candidate(2)],
        }
    if name == "unregistered_engine_rejected":
        engine = _default_engine()
        engine["engine_id"] = "unknown_external_tta"
        return {
            "route_id": "route_unregistered_engine",
            "event_id": "evt_unregistered",
            "structured_prompt": _prompt(),
            "engine": engine,
            "seeds": [7, 8],
            "candidates": [_candidate(7), _candidate(8)],
        }
    if name == "rights_fail_closed_rejected":
        return {
            "route_id": "route_rights_denied",
            "event_id": "evt_rights_denied",
            "structured_prompt": _prompt(rights_decision="deny"),
            "engine": _default_engine(),
            "seeds": [3, 4],
            "candidates": [
                _candidate(3, rights_decision="deny"),
                _candidate(4, rights_decision="deny"),
            ],
        }
    if name == "duration_gate_rejected":
        return {
            "route_id": "route_duration_fail",
            "event_id": "evt_duration_fail",
            "structured_prompt": _prompt(duration_ms=240),
            "engine": _default_engine(),
            "seeds": [5, 6],
            "candidates": [
                _candidate(5, duration_ms=9000),
                _candidate(6, duration_ms=9000),
            ],
        }
    if name == "semantic_gate_rejected":
        return {
            "route_id": "route_semantic_fail",
            "event_id": "evt_semantic_fail",
            "structured_prompt": _prompt(),
            "engine": _default_engine(),
            "seeds": [9, 10],
            "candidates": [
                _candidate(9, semantic_similarity=0.12),
                _candidate(10, semantic_similarity=0.15),
            ],
        }
    if name == "uniqueness_duplicate_rejected":
        dup = "a" * 64
        return {
            "route_id": "route_unique_fail",
            "event_id": "evt_unique_fail",
            "structured_prompt": _prompt(),
            "engine": _default_engine(),
            "seeds": [12, 13],
            "candidates": [
                _candidate(12, pcm_sha256=dup),
                _candidate(13, pcm_sha256=dup),
            ],
        }
    raise NeuralTextToAudioError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_route_packet(name)
    return build_route_record(
        root,
        route_id=packet["route_id"],
        event_id=packet["event_id"],
        structured_prompt=packet["structured_prompt"],
        engine_input=packet["engine"],
        seeds=packet["seeds"],
        candidates_input=packet["candidates"],
        is_synthetic=True,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW099_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_NEURAL_TEXT_TO_AUDIO_RUNTIME_ABSENT",
        "PRODUCTION_ENGINE_MODEL_CONFIG_RIGHTS_BINDING_ABSENT",
        "GENUINE_AUDIO_QA_AND_RUNTIME_PROOF_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-099_neural_text_to_audio",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": True,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_NEURAL_TEXT_TO_AUDIO_RUNTIME_ABSENT",
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
                "Fixture records prove structured-prompt, engine-authority, seeded-batch, "
                "rights, and candidate-only gates with reconstructable batch hashes; "
                "they do not accept Row099 library completion or substitute for genuine audio QA."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row099_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows068, 079, 083, and 091; bind production engine/model/config with "
                "rights provenance; route structured prompts to seeded candidate batches; "
                "pass duration/semantic/technical/uniqueness gates; keep candidates "
                "promotion-forbidden; pass waveform/spectrogram review; then replace this hold packet."
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
    parser.add_argument("--fixture", default="eligible_engine_seeded_batch_routed")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise NeuralTextToAudioError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise NeuralTextToAudioError(
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
