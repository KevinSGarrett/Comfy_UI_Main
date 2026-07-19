#!/usr/bin/env python3
"""Fail-closed Wave64 Row094 layered Foley composition slice.

Library composition refuses authority without accepted Rows068/079/081/091/093.
Fixture mode may emit deterministic schema-validated composition receipts from
synthetic layer packets without promoting library completion or claiming audio QA.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/layered_foley_composition_receipt.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row094_layered_foley_composition_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-094_layered_foley_composition.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-079": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-081": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-081_EXPLAINABLE_AUDIO_CANDIDATE_SCORING_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-091": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-093": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-093_CANONICAL_CLIP_PREPARATION_CURRENT_DELTA_20260719.json"
    ),
}

ENGINE_REVISION = "wave64_row094_layered_foley_composition_engine_v0.1.0"
POLICY_REVISION = "wave64_row094_layered_foley_composition_v0.1.0"
TRACKER_ID = "TRK-W64-094"
ITEM_ID = "ITEM-W64-094"
SCHEMA_VERSION = "1.0.0"

ALLOWED_LAYER_ROLES = (
    "transient",
    "body",
    "clothing",
    "object",
    "settle",
    "debris",
    "room",
)

REQUIRED_GATES = (
    "layer_justification",
    "license_compatibility",
    "acoustic_compatibility",
    "stem_lineage",
    "composite_hash",
)

FIXTURE_NAMES = (
    "compatible_layers_compose",
    "license_incompatible_rejected",
    "acoustic_perspective_mismatch_rejected",
    "duplicate_layer_role_rejected",
    "missing_expected_layer_blocked",
)


class LayeredFoleyError(ValueError):
    """Raised when Row094 composition violates fail-closed authority."""


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
        raise LayeredFoleyError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row094_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise LayeredFoleyError("policy_registry_revision_mismatch")
    if tuple(payload.get("allowed_layer_roles") or ()) != ALLOWED_LAYER_ROLES:
        raise LayeredFoleyError("policy_allowed_layer_roles_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise LayeredFoleyError("policy_required_gates_mismatch")
    if tuple(payload.get("layer_order") or ()) != ALLOWED_LAYER_ROLES:
        raise LayeredFoleyError("policy_layer_order_mismatch")
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
    # Row068 uses PASS_* status with row_complete true and no hold_decision.
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


def recipe_sha256(recipe: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(recipe))


def derive_stem_pcm_sha256(source_pcm_sha256: str, recipe: dict[str, Any]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "source_pcm_sha256": source_pcm_sha256,
                "recipe": recipe,
                "transform": "wave64_row094_deterministic_stem_v0",
            }
        )
    )


def environment_sha256(*, sample_rate_hz: int, channels: int, headroom_db: float) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "sample_rate_hz": sample_rate_hz,
                "channels": channels,
                "headroom_db": headroom_db,
                "engine_revision": ENGINE_REVISION,
            }
        )
    )


def recompute_output_pcm_sha256(
    ordered_stem_pcm: list[str],
    *,
    mix_recipe_sha256: str,
    environment: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "ordered_stem_pcm_sha256": ordered_stem_pcm,
                "mix_recipe_sha256": mix_recipe_sha256,
                "environment_sha256": environment,
                "mix": "wave64_row094_deterministic_sum_v0",
            }
        )
    )


def recompute_composite_hash(
    *,
    event_manifest_sha256: str,
    ordered_layers: list[dict[str, Any]],
    mix_recipe_sha256: str,
    output_pcm_sha256: str,
    environment: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "engine_revision": ENGINE_REVISION,
                "policy_revision": POLICY_REVISION,
                "event_manifest_sha256": event_manifest_sha256,
                "ordered_layers": [
                    {
                        "layer_role": item["layer_role"],
                        "source_pcm_sha256": item["source_pcm_sha256"],
                        "stem_pcm_sha256": item["stem_pcm_sha256"],
                        "recipe_sha256": item["recipe_sha256"],
                        "rights_decision_sha256": item["rights_decision_sha256"],
                    }
                    for item in ordered_layers
                ],
                "mix_recipe_sha256": mix_recipe_sha256,
                "output_pcm_sha256": output_pcm_sha256,
                "environment_sha256": environment,
            }
        )
    )


def _normalize_layer_input(raw: dict[str, Any]) -> dict[str, Any]:
    role = str(raw["layer_role"])
    if role not in ALLOWED_LAYER_ROLES:
        raise LayeredFoleyError(f"unknown_layer_role:{role}")
    recipe = {
        "gain_db": float(raw["recipe"]["gain_db"]),
        "onset_sample_offset": int(raw["recipe"]["onset_sample_offset"]),
        "attack_ms": float(raw["recipe"]["attack_ms"]),
        "hold_ms": float(raw["recipe"]["hold_ms"]),
        "release_ms": float(raw["recipe"]["release_ms"]),
        "fade_in_samples": int(raw["recipe"]["fade_in_samples"]),
        "fade_out_samples": int(raw["recipe"]["fade_out_samples"]),
    }
    acoustic = {
        "sample_rate_hz": int(raw["acoustic"]["sample_rate_hz"]),
        "channels": int(raw["acoustic"]["channels"]),
        "perspective": str(raw["acoustic"]["perspective"]),
        "dry_wet_state": str(raw["acoustic"]["dry_wet_state"]),
        "microphone_class": str(raw["acoustic"]["microphone_class"]),
        "room_id": str(raw["acoustic"]["room_id"]),
    }
    source_pcm = str(raw["source_pcm_sha256"])
    return {
        "layer_role": role,
        "asset_id": str(raw["asset_id"]),
        "source_pcm_sha256": source_pcm,
        "stem_pcm_sha256": derive_stem_pcm_sha256(source_pcm, recipe),
        "recipe_sha256": recipe_sha256(recipe),
        "rights_decision_sha256": str(raw["rights_decision_sha256"]),
        "license_classification": str(raw["license_classification"]),
        "rights_status": str(raw["rights_status"]),
        "acoustic": acoustic,
        "recipe": recipe,
        "taxonomy_class": str(raw["taxonomy_class"]),
        "score_evidence_sha256": str(raw["score_evidence_sha256"]),
        "justified": bool(raw.get("justified", True)),
        "admitted": False,
    }


def evaluate_layer_justification(
    expected_layers: list[str],
    layers: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    reason_codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    roles = [item["layer_role"] for item in layers]
    if len(roles) != len(set(roles)):
        reason_codes.append("DUPLICATE_LAYER_ROLE")
        seen: set[str] = set()
        for role in roles:
            if role in seen:
                exclusions.append(
                    {"layer_role": role, "reason_codes": ["DUPLICATE_LAYER_ROLE"]}
                )
            seen.add(role)
    expected = list(expected_layers)
    provided = set(roles)
    for role in expected:
        if role not in provided:
            reason_codes.append("MISSING_LAYER_JUSTIFICATION")
            exclusions.append(
                {"layer_role": role, "reason_codes": ["MISSING_LAYER_JUSTIFICATION"]}
            )
    for role in provided:
        if role not in expected:
            reason_codes.append("UNJUSTIFIED_EXTRA_LAYER")
            exclusions.append(
                {"layer_role": role, "reason_codes": ["UNJUSTIFIED_EXTRA_LAYER"]}
            )
    for item in layers:
        if item.get("justified") is not True:
            reason_codes.append("LAYER_NOT_JUSTIFIED")
            exclusions.append(
                {
                    "layer_role": item["layer_role"],
                    "reason_codes": ["LAYER_NOT_JUSTIFIED"],
                }
            )
    unique_reasons = sorted(set(reason_codes))
    status = "pass" if not unique_reasons else "fail"
    return (
        {"status": status, "reason_codes": unique_reasons},
        exclusions,
        unique_reasons,
    )


def evaluate_license_compatibility(
    layers: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    matrix = policy["license_compatibility_matrix"]
    reason_codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    for item in layers:
        if item["rights_status"] != "accepted" or item["license_classification"] == "denied":
            reason_codes.append("DENIED_RIGHTS")
            exclusions.append(
                {"layer_role": item["layer_role"], "reason_codes": ["DENIED_RIGHTS"]}
            )
    licenses = [item["license_classification"] for item in layers]
    for index, left in enumerate(licenses):
        allowed = set(matrix.get(left, []))
        for right in licenses[index + 1 :]:
            if right not in allowed or left not in set(matrix.get(right, [])):
                reason_codes.append("LICENSE_INCOMPATIBLE")
    unique_reasons = sorted(set(reason_codes))
    if "LICENSE_INCOMPATIBLE" in unique_reasons:
        for item in layers:
            exclusions.append(
                {
                    "layer_role": item["layer_role"],
                    "reason_codes": ["LICENSE_INCOMPATIBLE"],
                }
            )
    status = "pass" if not unique_reasons else "fail"
    return (
        {"status": status, "reason_codes": unique_reasons},
        exclusions,
        unique_reasons,
    )


def evaluate_acoustic_compatibility(
    layers: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    cfg = policy["acoustic_compatibility"]
    reason_codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    if not layers:
        return (
            {"status": "fail", "reason_codes": ["NO_LAYERS"]},
            exclusions,
            ["NO_LAYERS"],
        )
    rates = {item["acoustic"]["sample_rate_hz"] for item in layers}
    channels = {item["acoustic"]["channels"] for item in layers}
    perspectives = {item["acoustic"]["perspective"] for item in layers}
    dry_wet = {item["acoustic"]["dry_wet_state"] for item in layers}
    room_ids = {item["acoustic"]["room_id"] for item in layers}
    if cfg.get("require_matching_sample_rate") and len(rates) != 1:
        reason_codes.append("SAMPLE_RATE_MISMATCH")
    if cfg.get("require_matching_channels") and len(channels) != 1:
        reason_codes.append("CHANNEL_MISMATCH")
    if len(perspectives) != 1:
        reason_codes.append("PERSPECTIVE_MISMATCH")
    else:
        perspective = next(iter(perspectives))
        allowed = set(cfg["compatible_perspectives"].get(perspective, []))
        if perspective not in allowed:
            reason_codes.append("PERSPECTIVE_MISMATCH")
    if cfg.get("reject_dry_wet_mix_without_transform") and len(dry_wet) > 1:
        reason_codes.append("DRY_WET_MIX_WITHOUT_TRANSFORM")
    needs_room_match = any(
        item["acoustic"]["dry_wet_state"] == "wet" or item["layer_role"] == "room"
        for item in layers
    )
    if (
        cfg.get("require_matching_room_id_for_wet_or_room")
        and needs_room_match
        and len(room_ids) != 1
    ):
        reason_codes.append("ROOM_ID_MISMATCH")
    unique_reasons = sorted(set(reason_codes))
    if unique_reasons:
        for item in layers:
            exclusions.append(
                {
                    "layer_role": item["layer_role"],
                    "reason_codes": ["ACOUSTIC_INCOMPATIBLE", *unique_reasons],
                }
            )
        unique_reasons = sorted(set(["ACOUSTIC_INCOMPATIBLE", *unique_reasons]))
    status = "pass" if not unique_reasons else "fail"
    return (
        {"status": status, "reason_codes": unique_reasons},
        exclusions,
        unique_reasons,
    )


def seal_receipt(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def validate_composition_semantics(record: dict[str, Any]) -> None:
    layers = record.get("layers") or []
    expected = record.get("expected_layers") or []
    roles = [item.get("layer_role") for item in layers]
    gate_results = record.get("gate_results") or {}
    if set(gate_results.keys()) != set(REQUIRED_GATES):
        raise LayeredFoleyError("gate_result_set_mismatch")
    decision = record.get("decision") or {}
    route = decision.get("route")
    if route == "compose":
        if len(roles) != len(set(roles)):
            raise LayeredFoleyError("duplicate_layer_role_in_receipt")
        for gate in REQUIRED_GATES:
            if gate_results[gate]["status"] != "pass":
                raise LayeredFoleyError(f"compose_with_failed_gate:{gate}")
        if set(roles) != set(expected):
            raise LayeredFoleyError("compose_layer_set_mismatch")
        for item in layers:
            if item.get("admitted") is not True:
                raise LayeredFoleyError("compose_with_unadmitted_layer")
            recomputed_stem = derive_stem_pcm_sha256(
                item["source_pcm_sha256"], item["recipe"]
            )
            if recomputed_stem != item["stem_pcm_sha256"]:
                raise LayeredFoleyError("stem_lineage_recompute_mismatch")
            if recipe_sha256(item["recipe"]) != item["recipe_sha256"]:
                raise LayeredFoleyError("recipe_sha256_recompute_mismatch")
        ordered = sorted(
            layers,
            key=lambda item: ALLOWED_LAYER_ROLES.index(item["layer_role"]),
        )
        mix = record["mix_recipe"]
        env = environment_sha256(
            sample_rate_hz=int(mix["sample_rate_hz"]),
            channels=int(mix["channels"]),
            headroom_db=float(mix["headroom_db"]),
        )
        if env != record["composite"]["environment_sha256"]:
            raise LayeredFoleyError("environment_sha256_mismatch")
        mix_body = {
            "sample_rate_hz": mix["sample_rate_hz"],
            "channels": mix["channels"],
            "headroom_db": mix["headroom_db"],
            "ordered_layer_roles": mix["ordered_layer_roles"],
        }
        if recipe_sha256(mix_body) != mix["recipe_sha256"]:
            raise LayeredFoleyError("mix_recipe_sha256_recompute_mismatch")
        output = recompute_output_pcm_sha256(
            [item["stem_pcm_sha256"] for item in ordered],
            mix_recipe_sha256=mix["recipe_sha256"],
            environment=env,
        )
        if output != record["composite"]["output_pcm_sha256"]:
            raise LayeredFoleyError("output_pcm_sha256_recompute_mismatch")
        composite = recompute_composite_hash(
            event_manifest_sha256=record["event_manifest_sha256"],
            ordered_layers=ordered,
            mix_recipe_sha256=mix["recipe_sha256"],
            output_pcm_sha256=output,
            environment=env,
        )
        if composite != record["composite"]["composite_hash"]:
            raise LayeredFoleyError("composite_hash_recompute_mismatch")
        if record["composite"]["reconstructable"] is not True:
            raise LayeredFoleyError("compose_not_marked_reconstructable")
        if decision.get("blocker_codes"):
            raise LayeredFoleyError("compose_with_blocker_codes")
    elif route == "blocked":
        if not decision.get("blocker_codes"):
            raise LayeredFoleyError("blocked_without_blocker_codes")
        if record["composite"]["reconstructable"] is True:
            raise LayeredFoleyError("blocked_marked_reconstructable")
        if record["composite"]["composite_hash"] is not None:
            raise LayeredFoleyError("blocked_with_composite_hash")
        if record["composite"]["output_pcm_sha256"] is not None:
            raise LayeredFoleyError("blocked_with_output_pcm")
    else:
        raise LayeredFoleyError(f"unknown_route:{route}")
    if record.get("library_authority") is True:
        raise LayeredFoleyError("library_authority_true_forbidden")
    if decision.get("product_completion") is True:
        raise LayeredFoleyError("product_completion_true_forbidden")


def validate_composition_receipt(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_composition_semantics(record)
    sealed = seal_receipt({k: v for k, v in record.items() if k != "receipt_sha256"})
    if sealed["receipt_sha256"] != record.get("receipt_sha256"):
        raise LayeredFoleyError("receipt_sha256_mismatch")


def build_composition_record(
    root: Path,
    *,
    event_id: str,
    event_manifest_sha256: str,
    expected_layers: list[str],
    layers_input: list[dict[str, Any]],
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    layers = [_normalize_layer_input(item) for item in layers_input]

    justification, just_exclusions, just_codes = evaluate_layer_justification(
        expected_layers, layers
    )
    license_gate, license_exclusions, license_codes = evaluate_license_compatibility(
        layers, policy
    )
    acoustic_gate, acoustic_exclusions, acoustic_codes = evaluate_acoustic_compatibility(
        layers, policy
    )

    blocker_codes = sorted(set(just_codes + license_codes + acoustic_codes))
    exclusions = just_exclusions + license_exclusions + acoustic_exclusions

    defaults = policy["recipe_defaults"]
    sample_rate = int(defaults["sample_rate_hz"])
    channels = int(defaults["channels"])
    headroom = float(defaults["headroom_db"])
    if layers and acoustic_gate["status"] == "pass":
        sample_rate = int(layers[0]["acoustic"]["sample_rate_hz"])
        channels = int(layers[0]["acoustic"]["channels"])

    compose_ok = not blocker_codes and justification["status"] == "pass"
    ordered_roles = [role for role in ALLOWED_LAYER_ROLES if role in expected_layers]
    mix_body = {
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "headroom_db": headroom,
        "ordered_layer_roles": ordered_roles,
    }
    mix_sha = recipe_sha256(mix_body)
    env = environment_sha256(
        sample_rate_hz=sample_rate, channels=channels, headroom_db=headroom
    )

    gate_results = {
        "layer_justification": justification,
        "license_compatibility": license_gate,
        "acoustic_compatibility": acoustic_gate,
        "stem_lineage": {"status": "skipped", "reason_codes": ["COMPOSITION_BLOCKED"]},
        "composite_hash": {"status": "skipped", "reason_codes": ["COMPOSITION_BLOCKED"]},
    }
    composite = {
        "output_pcm_sha256": None,
        "composite_hash": None,
        "environment_sha256": env,
        "reconstructable": False,
    }

    if compose_ok:
        ordered_layers = sorted(
            layers, key=lambda item: ALLOWED_LAYER_ROLES.index(item["layer_role"])
        )
        for item in ordered_layers:
            item["admitted"] = True
        output = recompute_output_pcm_sha256(
            [item["stem_pcm_sha256"] for item in ordered_layers],
            mix_recipe_sha256=mix_sha,
            environment=env,
        )
        composite_hash = recompute_composite_hash(
            event_manifest_sha256=event_manifest_sha256,
            ordered_layers=ordered_layers,
            mix_recipe_sha256=mix_sha,
            output_pcm_sha256=output,
            environment=env,
        )
        composite = {
            "output_pcm_sha256": output,
            "composite_hash": composite_hash,
            "environment_sha256": env,
            "reconstructable": True,
        }
        gate_results["stem_lineage"] = {"status": "pass", "reason_codes": []}
        gate_results["composite_hash"] = {"status": "pass", "reason_codes": []}
        route = "compose"
        status = "composed"
        reason = "all_required_gates_passed_for_synthetic_or_fixture_composition"
        acceptance = "fixture_only" if is_synthetic else "held"
        layers = ordered_layers
    else:
        route = "blocked"
        status = "blocked"
        reason = "fail_closed_layer_compatibility_or_justification_blocker"
        acceptance = "held"
        if "STEM_LINEAGE_UNAVAILABLE" not in gate_results["stem_lineage"]["reason_codes"]:
            pass

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "layered_foley_composition_receipt",
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "event_id": event_id,
        "event_manifest_sha256": event_manifest_sha256,
        "expected_layers": list(expected_layers),
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": gate_results,
        "layers": layers,
        "exclusions": exclusions,
        "mix_recipe": {**mix_body, "recipe_sha256": mix_sha},
        "composite": composite,
        "decision": {
            "route": route,
            "status": status,
            "blocker_codes": blocker_codes,
            "product_completion": False,
            "row094_acceptance": acceptance,
            "reason": reason,
        },
    }
    sealed = seal_receipt(record)
    validate_composition_receipt(root, sealed)
    return sealed


def _base_acoustic(
    *,
    perspective: str = "mid",
    dry_wet_state: str = "dry",
    room_id: str = "room_studio_a",
) -> dict[str, Any]:
    return {
        "sample_rate_hz": 48000,
        "channels": 2,
        "perspective": perspective,
        "dry_wet_state": dry_wet_state,
        "microphone_class": "cardioid_close",
        "room_id": room_id,
    }


def _base_recipe(gain_db: float = -3.0, onset: int = 0) -> dict[str, Any]:
    return {
        "gain_db": gain_db,
        "onset_sample_offset": onset,
        "attack_ms": 2.0,
        "hold_ms": 40.0,
        "release_ms": 80.0,
        "fade_in_samples": 0,
        "fade_out_samples": 64,
    }


def _layer(
    role: str,
    *,
    license_classification: str = "cc0",
    rights_status: str = "accepted",
    acoustic: dict[str, Any] | None = None,
    gain_db: float = -3.0,
    justified: bool = True,
) -> dict[str, Any]:
    return {
        "layer_role": role,
        "asset_id": f"fixture:{role}",
        "source_pcm_sha256": _stable_hash(f"source:{role}"),
        "rights_decision_sha256": _stable_hash(f"rights:{role}:{license_classification}"),
        "license_classification": license_classification,
        "rights_status": rights_status,
        "acoustic": acoustic or _base_acoustic(),
        "recipe": _base_recipe(gain_db=gain_db, onset=ALLOWED_LAYER_ROLES.index(role) * 16),
        "taxonomy_class": f"foley.{role}.contact",
        "score_evidence_sha256": _stable_hash(f"score:{role}"),
        "justified": justified,
    }


def fixture_layer_packet(name: str) -> dict[str, Any]:
    if name == "compatible_layers_compose":
        return {
            "event_id": "evt_compatible_layers",
            "event_manifest_sha256": _stable_hash("manifest:compatible"),
            "expected_layers": ["transient", "body", "settle"],
            "layers": [
                _layer("transient", gain_db=-1.5),
                _layer("body", gain_db=-3.0),
                _layer("settle", gain_db=-6.0),
            ],
        }
    if name == "license_incompatible_rejected":
        return {
            "event_id": "evt_license_incompatible",
            "event_manifest_sha256": _stable_hash("manifest:license"),
            "expected_layers": ["transient", "body"],
            "layers": [
                _layer("transient", license_classification="cc0"),
                _layer("body", license_classification="restricted_nc"),
            ],
        }
    if name == "acoustic_perspective_mismatch_rejected":
        return {
            "event_id": "evt_acoustic_mismatch",
            "event_manifest_sha256": _stable_hash("manifest:acoustic"),
            "expected_layers": ["transient", "body"],
            "layers": [
                _layer("transient", acoustic=_base_acoustic(perspective="close")),
                _layer("body", acoustic=_base_acoustic(perspective="far")),
            ],
        }
    if name == "duplicate_layer_role_rejected":
        return {
            "event_id": "evt_duplicate_role",
            "event_manifest_sha256": _stable_hash("manifest:duplicate"),
            "expected_layers": ["transient", "body"],
            "layers": [
                _layer("transient"),
                _layer("transient", gain_db=-9.0),
                _layer("body"),
            ],
        }
    if name == "missing_expected_layer_blocked":
        return {
            "event_id": "evt_missing_layer",
            "event_manifest_sha256": _stable_hash("manifest:missing"),
            "expected_layers": ["transient", "body", "room"],
            "layers": [
                _layer("transient"),
                _layer("body"),
            ],
        }
    raise LayeredFoleyError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_layer_packet(name)
    return build_composition_record(
        root,
        event_id=packet["event_id"],
        event_manifest_sha256=packet["event_manifest_sha256"],
        expected_layers=packet["expected_layers"],
        layers_input=packet["layers"],
        is_synthetic=True,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW094_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_LAYER_COMPOSER_RUNTIME_ABSENT",
        "PRODUCTION_EVENT_MANIFEST_BINDING_ABSENT",
        "GENUINE_AUDIO_QA_AND_RUNTIME_PROOF_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-094_layered_foley_composition",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_LAYER_COMPOSER_RUNTIME_ABSENT",
        "required_gates": list(REQUIRED_GATES),
        "allowed_layer_roles": list(ALLOWED_LAYER_ROLES),
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
                "Fixture records prove layer justification, license/acoustic compatibility, "
                "stem lineage recomputation, and composite hash stability; they do not accept "
                "Row094 library completion or substitute for genuine audio QA."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row094_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows079, 081, 091, and 093 with Row068 already accepted; bind a "
                "production event manifest and accepted clip derivatives; execute the layered "
                "composer with rights/acoustic gates; recompute stem lineage and composite "
                "hashes; pass waveform/spectrogram audio review; then replace this hold packet."
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
    parser.add_argument("--fixture", default="compatible_layers_compose")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise LayeredFoleyError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise LayeredFoleyError(
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
