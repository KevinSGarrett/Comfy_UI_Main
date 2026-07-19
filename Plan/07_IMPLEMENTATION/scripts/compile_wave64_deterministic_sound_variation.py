#!/usr/bin/env python3
"""Fail-closed Wave64 Row098 deterministic sound variation contract slice.

Production variation refuses authority without accepted Row068 rights,
Row071 waveform features, Row072 onset anchors, Row073 usable bounds,
Row079 foley taxonomy, and Row093 clip-preparation prerequisites.
Fixture mode may emit deterministic schema-validated synthetic manifests and
hold evidence without granting production, runtime, or row completion authority.
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
SCHEMA_PATH = Path(
    "Plan/08_SCHEMAS/wave64_row098_deterministic_sound_variation_manifest.schema.json"
)
REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row098_deterministic_sound_variation_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-098_deterministic_sound_variation.json"
)
ROW068_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
)
ROW071_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
)
ROW072_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
)
ROW073_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
)
ROW079_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
)
ROW093_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-093_CANONICAL_CLIP_PREPARATION_CURRENT_DELTA_20260719.json"
)

COMPILER_REVISION = "wave64_row098_deterministic_sound_variation_compiler_v0.1.0"
REGISTRY_REVISION = "wave64_row098_deterministic_sound_variation_registry_v0.1.0"
TRACKER_ID = "TRK-W64-098"
ITEM_ID = "ITEM-W64-098"
SCHEMA_VERSION = "1.0.0"

FIXTURE_NAMES = (
    "micro_variation_pass",
    "structural_variation_pass",
    "reject_canonical_pcm_duplicate",
    "reject_semantic_similarity_fail",
    "reject_original_mutation",
    "reject_license_provenance_missing",
    "reject_transform_bounds_exceeded",
    "gate_failure_blocked",
)

REQUIRED_GATES = (
    "event_identity",
    "semantic_similarity",
    "canonical_pcm_dedup",
    "license_provenance",
    "original_immutability",
    "transform_bounds",
    "anchor_preservation",
)

DEPENDENCY_SPECS = (
    (
        "TRK-W64-068",
        ROW068_DELTA,
        "ROW068_DEPENDENCY_NOT_ACCEPTED",
        "ROW068_DELTA_ABSENT",
    ),
    (
        "TRK-W64-071",
        ROW071_DELTA,
        "ROW071_DEPENDENCY_NOT_ACCEPTED",
        "ROW071_DELTA_ABSENT",
    ),
    (
        "TRK-W64-072",
        ROW072_DELTA,
        "ROW072_DEPENDENCY_NOT_ACCEPTED",
        "ROW072_DELTA_ABSENT",
    ),
    (
        "TRK-W64-073",
        ROW073_DELTA,
        "ROW073_DEPENDENCY_NOT_ACCEPTED",
        "ROW073_DELTA_ABSENT",
    ),
    (
        "TRK-W64-079",
        ROW079_DELTA,
        "ROW079_DEPENDENCY_NOT_ACCEPTED",
        "ROW079_DELTA_ABSENT",
    ),
    (
        "TRK-W64-093",
        ROW093_DELTA,
        "ROW093_DEPENDENCY_NOT_ACCEPTED",
        "ROW093_DELTA_ABSENT",
    ),
)


class DeterministicSoundVariationError(ValueError):
    """Raised when Row098 variation compilation violates fail-closed authority."""


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


def canonical_json_sha256(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DeterministicSoundVariationError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row098_fixture:{label}".encode("utf-8"))


def load_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, REGISTRY_PATH, "registry")
    payload = load_json(path)
    if payload.get("registry_revision") != REGISTRY_REVISION:
        raise DeterministicSoundVariationError("registry_revision_mismatch")
    if payload.get("compiler_revision") != COMPILER_REVISION:
        raise DeterministicSoundVariationError("compiler_revision_mismatch")
    gates = payload.get("required_gates")
    if not isinstance(gates, list) or tuple(gates) != REQUIRED_GATES:
        raise DeterministicSoundVariationError("required_gates_mismatch")
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
            "sha256": "0" * 64,
            "bytes": 0,
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    acceptance_keys = (
        "status",
        "row068_acceptance",
        "row071_acceptance",
        "row072_acceptance",
        "row073_acceptance",
        "row079_acceptance",
        "row093_acceptance",
        "acceptance",
    )
    acceptance_values = [str(decision.get(key, "")).lower() for key in acceptance_keys]
    qa_decision = str(payload.get("qa_decision", "")).lower()
    accepted = row_complete and (
        any(value in {"accepted", "pass", "passed"} for value in acceptance_values)
        or "accepted" in status_text
        or status_text.startswith("pass")
    )
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        accepted = False
    if any(value == "held" for value in acceptance_values):
        accepted = False
    if "hold" in qa_decision:
        accepted = False
    dependency_satisfied = bool(accepted)
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
    admissions: dict[str, dict[str, Any]] = {}
    for tracker_id, delta_path, blocker_code, absent_code in DEPENDENCY_SPECS:
        admissions[tracker_id] = evaluate_dependency_admission(
            root,
            delta_path=delta_path,
            tracker_id=tracker_id,
            blocker_code=blocker_code,
            absent_code=absent_code,
        )
    return admissions


def validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise DeterministicSoundVariationError(
            f"schema_validation_failed:{location}:{first.message}"
        )
    if manifest.get("production_authority") is True:
        raise DeterministicSoundVariationError(
            "production_authority_forbidden_in_contract_slice"
        )
    if manifest.get("decision", {}).get("promotion_eligible") is True:
        raise DeterministicSoundVariationError(
            "promotion_eligible_forbidden_in_contract_slice"
        )
    if manifest.get("is_synthetic") is True and manifest.get("decision", {}).get(
        "product_completion"
    ):
        raise DeterministicSoundVariationError("synthetic_product_completion_forbidden")
    if (
        manifest.get("variant", {}).get("canonical_pcm_duplicate") is True
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise DeterministicSoundVariationError("canonical_pcm_duplicate_cannot_pass")
    if (
        manifest.get("source", {}).get("original_mutated") is True
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise DeterministicSoundVariationError("original_mutation_cannot_pass")
    if (
        manifest.get("source", {}).get("license_class") in {"denied", "unknown"}
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise DeterministicSoundVariationError("invalid_license_cannot_pass")
    if (
        manifest.get("source", {}).get("rights_decision_sha256") is None
        and manifest.get("validation", {}).get("decision") == "pass"
    ):
        raise DeterministicSoundVariationError("missing_rights_cannot_pass")


def _authority_hashes() -> dict[str, str]:
    return {
        "rights_authority_sha256": _stable_hash("authority:rights"),
        "waveform_feature_authority_sha256": _stable_hash("authority:waveform"),
        "onset_anchor_authority_sha256": _stable_hash("authority:onset"),
        "usable_bounds_authority_sha256": _stable_hash("authority:bounds"),
        "foley_taxonomy_authority_sha256": _stable_hash("authority:taxonomy"),
        "clip_preparation_authority_sha256": _stable_hash("authority:clip"),
    }


def _source_block(
    *,
    seed: str,
    license_class: str = "cc0",
    rights_decision_sha256: str | None | object = ...,
    original_mutated: bool = False,
    onset_anchor_ms: float = 42.0,
) -> dict[str, Any]:
    if rights_decision_sha256 is ...:
        rights: str | None = _stable_hash(f"rights:{seed}")
    else:
        rights = rights_decision_sha256  # type: ignore[assignment]
    return {
        "asset_id": f"fixture:source:{seed}",
        "event_family": "footstep_hard_surface",
        "event_id": "evt_fixture_footstep_01",
        "canonical_pcm_sha256": _stable_hash(f"source_pcm:{seed}"),
        "source_path": f"fixtures/row098/source/{seed}.wav",
        "license_class": license_class,
        "rights_decision_sha256": rights,
        "onset_anchor_ms": float(onset_anchor_ms),
        "original_mutated": original_mutated,
    }


def _transforms_micro(seed: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "pitch",
            "parameters": {"semitones": 0.35},
            "seed": f"{seed}:pitch",
            "deterministic": True,
        },
        {
            "kind": "envelope",
            "parameters": {"attack_ms": 2.0, "release_ms": 18.0},
            "seed": f"{seed}:envelope",
            "deterministic": True,
        },
        {
            "kind": "microtiming",
            "parameters": {"offset_ms": -3.5},
            "seed": f"{seed}:microtiming",
            "deterministic": True,
        },
        {
            "kind": "stereo_perspective",
            "parameters": {"width_delta": 0.05},
            "seed": f"{seed}:stereo",
            "deterministic": True,
        },
    ]


def _transforms_structural(seed: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "layering",
            "parameters": {"layer_role": "settle", "gain_db": -6.0},
            "seed": f"{seed}:layering",
            "deterministic": True,
        },
        {
            "kind": "eq",
            "parameters": {"highshelf_db": -1.5, "lowshelf_db": 0.8},
            "seed": f"{seed}:eq",
            "deterministic": True,
        },
        {
            "kind": "transient_shaping",
            "parameters": {"attack_gain_db": 1.2},
            "seed": f"{seed}:transient",
            "deterministic": True,
        },
        {
            "kind": "duration",
            "parameters": {"scale": 1.04},
            "seed": f"{seed}:duration",
            "deterministic": True,
        },
    ]


def _transforms_out_of_bounds(seed: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "pitch",
            "parameters": {"semitones": 5.0},
            "seed": f"{seed}:pitch_oob",
            "deterministic": True,
        }
    ]


def _variant_block(
    registry: dict[str, Any],
    *,
    seed: str,
    source_pcm: str,
    semantic_similarity: float,
    canonical_pcm_duplicate: bool,
    license_class: str = "cc0",
    rights_decision_sha256: str | None | object = ...,
    onset_anchor_ms: float = 42.0,
    transforms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    contract = registry["fixture_variation_contract"]
    transforms = transforms or []
    pcm = source_pcm if canonical_pcm_duplicate else _stable_hash(f"variant_pcm:{seed}")
    if rights_decision_sha256 is ...:
        rights: str | None = _stable_hash(f"rights_variant:{seed}")
    else:
        rights = rights_decision_sha256  # type: ignore[assignment]
    return {
        "asset_id": f"fixture:variant:{seed}",
        "path": f"fixtures/row098/variant/{seed}.wav",
        "sha256": _stable_hash(f"wav:{seed}"),
        "canonical_pcm_sha256": pcm,
        "sample_rate_hz": int(contract["sample_rate_hz"]),
        "channels": int(contract["channels"]),
        "duration_seconds": 0.86,
        "semantic_similarity": float(semantic_similarity),
        "canonical_pcm_duplicate": canonical_pcm_duplicate,
        "license_class": license_class,
        "rights_decision_sha256": rights,
        "transform_recipe_sha256": canonical_json_sha256(transforms),
        "onset_anchor_ms": float(onset_anchor_ms),
    }


def _validation_pass(*, semantic_similarity: float) -> dict[str, Any]:
    return {
        "event_identity_pass": True,
        "semantic_similarity_pass": True,
        "canonical_pcm_dedup_pass": True,
        "license_provenance_pass": True,
        "original_immutability_pass": True,
        "transform_bounds_pass": True,
        "anchor_preservation_pass": True,
        "semantic_similarity": float(semantic_similarity),
        "decision": "pass",
    }


def _validation_blocked(
    *,
    semantic_similarity: float,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "event_identity_pass": False,
        "semantic_similarity_pass": False,
        "canonical_pcm_dedup_pass": False,
        "license_provenance_pass": False,
        "original_immutability_pass": False,
        "transform_bounds_pass": False,
        "anchor_preservation_pass": False,
        "semantic_similarity": float(semantic_similarity),
        "decision": "blocked",
    }
    if overrides:
        payload.update(overrides)
    return payload


def build_manifest(
    root: Path,
    *,
    variation_id: str,
    source: dict[str, Any],
    variation_tier: str,
    transforms: list[dict[str, Any]],
    variant: dict[str, Any],
    validation: dict[str, Any],
    blocker_codes: list[str],
    status: str,
    acceptance: str,
    reason: str,
) -> dict[str, Any]:
    load_registry(root)
    authorities = _authority_hashes()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "variation_id": variation_id,
        **authorities,
        "source": source,
        "variation_tier": variation_tier,
        "transforms": transforms,
        "variant": variant,
        "validation": validation,
        "is_synthetic": True,
        "production_authority": False,
        "decision": {
            "status": status,
            "row098_acceptance": acceptance,
            "product_completion": False,
            "runtime_completion": False,
            "promotion_eligible": False,
            "blocker_codes": list(blocker_codes),
            "reason": reason,
        },
    }
    validate_manifest(root, manifest)
    return manifest


def extract_fixture_manifest(root: Path, fixture_name: str) -> dict[str, Any]:
    if fixture_name not in FIXTURE_NAMES:
        raise DeterministicSoundVariationError(f"unknown_fixture:{fixture_name}")
    registry = load_registry(root)
    contract = registry["fixture_variation_contract"]
    common_blockers = [
        "SYNTHETIC_FIXTURE_ONLY",
        "PRODUCTION_VARIATION_RUNTIME_ABSENT",
    ]

    if fixture_name == "micro_variation_pass":
        seed = "micro_variation_pass"
        transforms = _transforms_micro(seed)
        source = _source_block(seed=seed)
        similarity = 0.91
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="micro_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=similarity,
                canonical_pcm_duplicate=False,
                transforms=transforms,
            ),
            validation=_validation_pass(semantic_similarity=similarity),
            blocker_codes=common_blockers,
            status="fixture_only",
            acceptance="fixture_only",
            reason="Synthetic micro-variation fixture passes bounded transform and identity gates without production authority.",
        )

    if fixture_name == "structural_variation_pass":
        seed = "structural_variation_pass"
        transforms = _transforms_structural(seed)
        source = _source_block(seed=seed, license_class="cc_by")
        similarity = 0.86
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="structural_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=similarity,
                canonical_pcm_duplicate=False,
                license_class="cc_by",
                transforms=transforms,
            ),
            validation=_validation_pass(semantic_similarity=similarity),
            blocker_codes=common_blockers,
            status="fixture_only",
            acceptance="fixture_only",
            reason="Synthetic structural-variation fixture preserves event identity and provenance without production authority.",
        )

    if fixture_name == "reject_canonical_pcm_duplicate":
        seed = "reject_canonical_pcm_duplicate"
        transforms = _transforms_micro(seed)
        source = _source_block(seed=seed)
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="micro_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=0.999,
                canonical_pcm_duplicate=True,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=0.999,
                overrides={
                    "event_identity_pass": True,
                    "semantic_similarity_pass": False,
                    "canonical_pcm_dedup_pass": False,
                    "license_provenance_pass": True,
                    "original_immutability_pass": True,
                    "transform_bounds_pass": True,
                    "anchor_preservation_pass": True,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["CANONICAL_PCM_DUPLICATE"],
            status="blocked",
            acceptance="held",
            reason="Variant canonical PCM matches the source; exact duplicates are rejected.",
        )

    if fixture_name == "reject_semantic_similarity_fail":
        seed = "reject_semantic_similarity_fail"
        transforms = _transforms_structural(seed)
        source = _source_block(seed=seed)
        similarity = 0.41
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="structural_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=similarity,
                canonical_pcm_duplicate=False,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=similarity,
                overrides={
                    "event_identity_pass": False,
                    "semantic_similarity_pass": False,
                    "canonical_pcm_dedup_pass": True,
                    "license_provenance_pass": True,
                    "original_immutability_pass": True,
                    "transform_bounds_pass": True,
                    "anchor_preservation_pass": True,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + ["SEMANTIC_SIMILARITY_OUT_OF_BOUNDS", "EVENT_IDENTITY_LOST"],
            status="blocked",
            acceptance="held",
            reason=(
                f"Semantic similarity {similarity} is below the minimum "
                f"{contract['semantic_similarity_min']}."
            ),
        )

    if fixture_name == "reject_original_mutation":
        seed = "reject_original_mutation"
        transforms = _transforms_micro(seed)
        source = _source_block(seed=seed, original_mutated=True)
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="micro_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=0.9,
                canonical_pcm_duplicate=False,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=0.9,
                overrides={
                    "event_identity_pass": True,
                    "semantic_similarity_pass": True,
                    "canonical_pcm_dedup_pass": True,
                    "license_provenance_pass": True,
                    "original_immutability_pass": False,
                    "transform_bounds_pass": True,
                    "anchor_preservation_pass": True,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["ORIGINAL_SOURCE_MUTATED"],
            status="blocked",
            acceptance="held",
            reason="Variation must never mutate the original source PCM.",
        )

    if fixture_name == "reject_license_provenance_missing":
        seed = "reject_license_provenance_missing"
        transforms = _transforms_micro(seed)
        source = _source_block(
            seed=seed,
            license_class="unknown",
            rights_decision_sha256=None,
        )
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="micro_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=0.9,
                canonical_pcm_duplicate=False,
                license_class="unknown",
                rights_decision_sha256=None,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=0.9,
                overrides={
                    "event_identity_pass": True,
                    "semantic_similarity_pass": True,
                    "canonical_pcm_dedup_pass": True,
                    "license_provenance_pass": False,
                    "original_immutability_pass": True,
                    "transform_bounds_pass": True,
                    "anchor_preservation_pass": True,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + ["LICENSE_PROVENANCE_MISSING", "UNKNOWN_OR_DENIED_RIGHTS"],
            status="blocked",
            acceptance="held",
            reason="Missing or unknown license provenance blocks variation.",
        )

    if fixture_name == "reject_transform_bounds_exceeded":
        seed = "reject_transform_bounds_exceeded"
        transforms = _transforms_out_of_bounds(seed)
        source = _source_block(seed=seed)
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="micro_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=0.7,
                canonical_pcm_duplicate=False,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=0.7,
                overrides={
                    "event_identity_pass": True,
                    "semantic_similarity_pass": True,
                    "canonical_pcm_dedup_pass": True,
                    "license_provenance_pass": True,
                    "original_immutability_pass": True,
                    "transform_bounds_pass": False,
                    "anchor_preservation_pass": True,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers + ["TRANSFORM_BOUNDS_EXCEEDED"],
            status="blocked",
            acceptance="held",
            reason=(
                f"Pitch semitone magnitude exceeds "
                f"{contract['pitch_semitone_abs_max']}."
            ),
        )

    if fixture_name == "gate_failure_blocked":
        seed = "gate_failure_blocked"
        transforms = _transforms_out_of_bounds(seed)
        source = _source_block(
            seed=seed,
            license_class="denied",
            original_mutated=True,
            onset_anchor_ms=120.0,
        )
        return build_manifest(
            root,
            variation_id=f"fixture:{seed}",
            source=source,
            variation_tier="structural_variation",
            transforms=transforms,
            variant=_variant_block(
                registry,
                seed=seed,
                source_pcm=source["canonical_pcm_sha256"],
                semantic_similarity=0.2,
                canonical_pcm_duplicate=True,
                license_class="denied",
                onset_anchor_ms=180.0,
                transforms=transforms,
            ),
            validation=_validation_blocked(
                semantic_similarity=0.2,
                overrides={
                    "event_identity_pass": False,
                    "semantic_similarity_pass": False,
                    "canonical_pcm_dedup_pass": False,
                    "license_provenance_pass": False,
                    "original_immutability_pass": False,
                    "transform_bounds_pass": False,
                    "anchor_preservation_pass": False,
                    "decision": "blocked",
                },
            ),
            blocker_codes=common_blockers
            + [
                "EVENT_IDENTITY_LOST",
                "SEMANTIC_SIMILARITY_OUT_OF_BOUNDS",
                "CANONICAL_PCM_DUPLICATE",
                "LICENSE_PROVENANCE_MISSING",
                "ORIGINAL_SOURCE_MUTATED",
                "TRANSFORM_BOUNDS_EXCEEDED",
                "ANCHOR_PRESERVATION_FAILED",
            ],
            status="blocked",
            acceptance="held",
            reason="Combined gate failures remain blocked under fail-closed variation policy.",
        )

    raise DeterministicSoundVariationError(f"unhandled_fixture:{fixture_name}")


def adversarial_false_open_cases(root: Path) -> list[dict[str, Any]]:
    """Probe strict schema against false-open mutations that must remain rejected."""
    baseline = extract_fixture_manifest(root, "micro_variation_pass")
    cases: list[dict[str, Any]] = []

    def probe(name: str, mutator) -> None:
        mutated = deepcopy(baseline)
        mutator(mutated)
        accepted = True
        error = ""
        try:
            validate_manifest(root, mutated)
        except DeterministicSoundVariationError as exc:
            accepted = False
            error = str(exc)
        cases.append(
            {
                "name": name,
                "schema_accepted": accepted,
                "strict_expected_accepted": False,
                "false_open": accepted,
                "error": error,
            }
        )

    probe(
        "pass_with_all_variation_gates_false",
        lambda m: m["validation"].update(
            {
                "event_identity_pass": False,
                "semantic_similarity_pass": False,
                "canonical_pcm_dedup_pass": False,
                "license_provenance_pass": False,
                "original_immutability_pass": False,
                "transform_bounds_pass": False,
                "anchor_preservation_pass": False,
                "decision": "pass",
            }
        ),
    )
    probe(
        "canonical_pcm_duplicate_but_pass",
        lambda m: (
            m["variant"].__setitem__("canonical_pcm_duplicate", True),
            m["variant"].__setitem__(
                "canonical_pcm_sha256", m["source"]["canonical_pcm_sha256"]
            ),
            m["validation"].__setitem__("decision", "pass"),
            m["validation"].__setitem__("canonical_pcm_dedup_pass", True),
        ),
    )
    probe(
        "original_mutated_but_pass",
        lambda m: (
            m["source"].__setitem__("original_mutated", True),
            m["validation"].__setitem__("decision", "pass"),
            m["validation"].__setitem__("original_immutability_pass", True),
        ),
    )
    probe(
        "missing_rights_decision_but_pass",
        lambda m: (
            m["source"].__setitem__("rights_decision_sha256", None),
            m["source"].__setitem__("license_class", "unknown"),
            m["validation"].__setitem__("decision", "pass"),
        ),
    )
    probe(
        "production_authority_true_on_synthetic",
        lambda m: (
            m.__setitem__("production_authority", True),
            m["decision"].update(
                {
                    "status": "accepted",
                    "row098_acceptance": "accepted",
                    "product_completion": True,
                    "runtime_completion": True,
                }
            ),
        ),
    )
    probe(
        "semantic_similarity_wrong_type",
        lambda m: m["variant"].__setitem__("semantic_similarity", "high"),
    )
    probe(
        "missing_transform_bounds_and_dedup_proof",
        lambda m: (
            m["validation"].pop("transform_bounds_pass", None),
            m["validation"].pop("canonical_pcm_dedup_pass", None),
        ),
    )
    return cases


def build_production_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    registry = load_registry(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append(
            "ROW068_ROW071_ROW072_ROW073_ROW079_ROW093_DEPENDENCIES_NOT_ACCEPTED"
        )
    for code in (
        "DETERMINISTIC_VARIATION_RUNTIME_ABSENT",
        "BOUNDED_TRANSFORM_ENGINE_ABSENT",
        "SEMANTIC_SIMILARITY_RUNTIME_PROOF_ABSENT",
        "CANONICAL_PCM_DEDUP_INDEX_ABSENT",
        "GENUINE_ROW098_RUNTIME_PROOF_ABSENT",
        "INDEPENDENT_VARIATION_AUDIO_REVIEW_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_manifests = [extract_fixture_manifest(root, name) for name in FIXTURE_NAMES]
    adversarial = adversarial_false_open_cases(root)
    false_open_count = sum(1 for case in adversarial if case["false_open"])
    if false_open_count != 0:
        raise DeterministicSoundVariationError(
            f"strict_schema_still_false_open:{false_open_count}"
        )

    first = extract_fixture_manifest(root, "micro_variation_pass")
    second = extract_fixture_manifest(root, "micro_variation_pass")
    determinism_identical = first == second

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-098_deterministic_sound_variation",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "production_authority": False,
        "status": (
            "HOLD_ROW068_ROW071_ROW072_ROW073_ROW079_ROW093_DEPENDENCIES_"
            "DETERMINISTIC_VARIATION_RUNTIME_AND_AUDIO_QA_ABSENT"
        ),
        "required_gates": list(REQUIRED_GATES),
        "planning_schema_boundary": {
            "strict_contract_schema_path": str(SCHEMA_PATH).replace("\\", "/"),
            "planning_schema_remains_non_authority": True,
            "architecture_variation_model_does_not_grant_row098": True,
            "strict_contract_closes_seven_false_open_cases": True,
        },
        "dependency_admissions": admissions,
        "variation_registry": {
            "path": str(REGISTRY_PATH).replace("\\", "/"),
            "registry_revision": registry["registry_revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, REGISTRY_PATH, "registry")),
        },
        "strict_schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(resolve_under(root, SCHEMA_PATH, "schema")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_production",
            "fixture_count": len(fixture_manifests),
            "determinism_identical_bytes": determinism_identical,
            "records": fixture_manifests,
            "determinism_note": (
                "Fixture manifests prove fail-closed micro/structural variation, "
                "canonical-PCM dedup, semantic bounds, original immutability, "
                "license provenance, transform bounds, and combined gate-failure "
                "contracts; they do not accept Row098 production completion or "
                "emit real transformed audio."
            ),
        },
        "adversarial_schema_probe": {
            "validator": "jsonschema.Draft202012Validator",
            "case_count": len(adversarial),
            "false_open_count": false_open_count,
            "cases": adversarial,
        },
        "blocker_codes": sorted(set(blocker_codes)),
        "decision": {
            "status": "blocked",
            "row098_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows071, 072, 073, 079, and 093 (Row068 already accepted); "
                "bind rights-cleared source PCM with onset/usable-bounds and taxonomy "
                "identity into a bounded deterministic transform engine; enforce "
                "semantic similarity bounds, canonical-PCM dedup, and original "
                "immutability; preserve hash-bound transform recipes; validate "
                "synthetic truth and genuine library fixtures; perform independent "
                "variation audio review; then replace this hold packet with "
                "production Row098 evidence."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("production", "fixture"), default="production")
    parser.add_argument("--fixture", default="micro_variation_pass")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise DeterministicSoundVariationError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_manifest(root, args.fixture)
    else:
        payload = build_production_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise DeterministicSoundVariationError(
                "production_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise DeterministicSoundVariationError(
                "production_mode_must_not_claim_row_complete"
            )
        if payload.get("production_authority") is True:
            raise DeterministicSoundVariationError(
                "production_mode_must_not_claim_production_authority"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "row_complete": payload.get("row_complete", False),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
