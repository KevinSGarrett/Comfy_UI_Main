#!/usr/bin/env python3
"""Fail-closed Wave64 Row079 fine-grained Foley taxonomy enrichment slice.

Library enrichment refuses authority without accepted Row074 segment identity,
Row076 acoustic room/perspective evidence, and Row078 source-attributed tag
ensemble. Fixture mode may emit deterministic schema-validated taxonomy records
with explicit unknowns that block incompatible exact-match use, without
promoting library completion or mutating source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/fine_grained_foley_taxonomy_record.schema.json")
TAXONOMY_REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row079_fine_grained_foley_taxonomy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_fine_grained_foley_taxonomy.json"
)
ROW074_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"
)
ROW076_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
)
ROW078_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-078_AUDIO_TAG_CAPTION_ENSEMBLE_CURRENT_DELTA_20260719.json"
)
ENRICHER_REVISION = "wave64_row079_fine_grained_foley_enricher_v0.1.0"
TAXONOMY_REVISION = "wave64_row079_fine_grained_foley_taxonomy_v0.1.0"
TRACKER_ID = "TRK-W64-079"
ITEM_ID = "ITEM-W64-079"
SCHEMA_VERSION = "1.0.0"

REQUIRED_DIMENSIONS = (
    "event_family",
    "contact_pair",
    "body_region",
    "footwear",
    "gait_phase",
    "surface_material",
    "object_material",
    "force",
    "attack",
    "motion",
    "room",
    "source_perspective",
)

UNKNOWN_SENTINEL = "unknown"
NOT_APPLICABLE_SENTINEL = "n_a"


class FoleyTaxonomyError(ValueError):
    """Raised when Row079 taxonomy enrichment violates fail-closed authority."""


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


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise FoleyTaxonomyError(f"{label}_outside_project_root") from exc
    return path


def load_taxonomy_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, TAXONOMY_REGISTRY_PATH, "taxonomy_registry")
    payload = load_json(path)
    if payload.get("revision") != TAXONOMY_REVISION:
        raise FoleyTaxonomyError("taxonomy_registry_revision_mismatch")
    dims = payload.get("required_dimensions")
    if not isinstance(dims, list) or tuple(dims) != REQUIRED_DIMENSIONS:
        raise FoleyTaxonomyError("taxonomy_registry_required_dimensions_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    acceptance_key: str,
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
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        decision = {}
    acceptance = str(decision.get(acceptance_key, "")).lower()
    dependency_satisfied = row_complete and acceptance in {"accepted", "pass", "passed"}
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


def evaluate_row074_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW074_DELTA,
        tracker_id="TRK-W64-074",
        acceptance_key="row074_acceptance",
        blocker_code="ROW074_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW074_DELTA_ABSENT",
    )


def evaluate_row076_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW076_DELTA,
        tracker_id="TRK-W64-076",
        acceptance_key="row076_acceptance",
        blocker_code="ROW076_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW076_DELTA_ABSENT",
    )


def evaluate_row078_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW078_DELTA,
        tracker_id="TRK-W64-078",
        acceptance_key="row078_acceptance",
        blocker_code="ROW078_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW078_DELTA_ABSENT",
    )


def _classification_for_value(value: str) -> str:
    if value == UNKNOWN_SENTINEL:
        return "unknown"
    if value == NOT_APPLICABLE_SENTINEL:
        return "not_applicable"
    return "known"


def _dimension_evidence(value: str, evidence_source: str) -> dict[str, Any]:
    classification = _classification_for_value(value)
    confidence = 0.92 if classification == "known" else (0.8 if classification == "not_applicable" else 0.55)
    return {
        "value": value,
        "classification": classification,
        "confidence": confidence,
        "evidence_source": evidence_source,
        "enricher_identity": ENRICHER_REVISION,
    }


def evaluate_semantic_rules(taxonomy: dict[str, str], registry: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    rules = registry.get("semantic_rules") or {}
    footwear_rule = rules.get("footwear_requires_foot_contact") or {}
    if taxonomy.get("footwear") in set(footwear_rule.get("when_footwear_in") or []):
        if taxonomy.get("contact_pair") not in set(footwear_rule.get("contact_pair_must_be_in") or []):
            blockers.append("SEMANTIC_FOOTWEAR_CONTACT_PAIR_MISMATCH")
        if taxonomy.get("body_region") not in set(footwear_rule.get("body_region_must_be_in") or []):
            blockers.append("SEMANTIC_FOOTWEAR_BODY_REGION_MISMATCH")
    gait_rule = rules.get("gait_phase_requires_footstep_family") or {}
    if taxonomy.get("gait_phase") in set(gait_rule.get("when_gait_phase_in") or []):
        if taxonomy.get("event_family") not in set(gait_rule.get("event_family_must_be_in") or []):
            blockers.append("SEMANTIC_GAIT_PHASE_EVENT_FAMILY_MISMATCH")
    return blockers


def evaluate_compatibility(
    taxonomy: dict[str, str],
    registry: dict[str, Any],
) -> dict[str, Any]:
    dimensions = registry["dimensions"]
    unknown_dimensions: list[str] = []
    invalid_dimensions: list[str] = []
    for dim in REQUIRED_DIMENSIONS:
        value = taxonomy.get(dim)
        if not isinstance(value, str) or not value.strip():
            invalid_dimensions.append(dim)
            continue
        allowed = set((dimensions.get(dim) or {}).get("allowed_values") or [])
        if value not in allowed:
            invalid_dimensions.append(dim)
        elif value == UNKNOWN_SENTINEL:
            unknown_dimensions.append(dim)
    semantic_blocker_codes = evaluate_semantic_rules(taxonomy, registry)
    all_present = set(taxonomy.keys()) >= set(REQUIRED_DIMENSIONS) and len(taxonomy) == len(REQUIRED_DIMENSIONS)
    exact_match_compatible = (
        all_present
        and not unknown_dimensions
        and not invalid_dimensions
        and not semantic_blocker_codes
    )
    return {
        "exact_match_compatible": exact_match_compatible,
        "unknown_dimensions": unknown_dimensions,
        "invalid_dimensions": invalid_dimensions,
        "semantic_blocker_codes": semantic_blocker_codes,
        "all_required_dimensions_present": all_present and not invalid_dimensions,
    }


def build_enrichment_record(
    root: Path,
    *,
    asset_id: str,
    source_sha256: str,
    segment_id: str,
    canonical_pcm_sha256: str,
    taxonomy: dict[str, str],
    evidence_source: str,
    library_authority: bool = False,
    blocker_codes: list[str] | None = None,
) -> dict[str, Any]:
    registry = load_taxonomy_registry(root)
    if set(taxonomy.keys()) != set(REQUIRED_DIMENSIONS):
        raise FoleyTaxonomyError("required_dimensions_missing_or_extra")
    for dim in REQUIRED_DIMENSIONS:
        value = taxonomy[dim]
        if not isinstance(value, str) or not value.strip():
            raise FoleyTaxonomyError(f"empty_dimension:{dim}")
        if value != value.strip() or " " in value:
            raise FoleyTaxonomyError(f"whitespace_or_alias_collision:{dim}")

    compatibility = evaluate_compatibility(taxonomy, registry)
    blockers = list(blocker_codes or [])
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    if compatibility["unknown_dimensions"]:
        blockers.append("UNKNOWN_DIMENSION_BLOCKS_EXACT_MATCH")
    if compatibility["invalid_dimensions"]:
        blockers.append("INVALID_TAXONOMY_VALUE")
    for code in compatibility["semantic_blocker_codes"]:
        if code not in blockers:
            blockers.append(code)
    if not compatibility["exact_match_compatible"]:
        blockers.append("EXACT_MATCH_USE_BLOCKED")

    promotion_eligible = bool(
        library_authority
        and compatibility["exact_match_compatible"]
        and not blockers
    )
    exact_match_use_allowed = bool(compatibility["exact_match_compatible"] and library_authority)
    status = "pass" if promotion_eligible and exact_match_use_allowed else "blocked"

    dimension_evidence = {
        dim: _dimension_evidence(taxonomy[dim], evidence_source) for dim in REQUIRED_DIMENSIONS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "enricher_revision": ENRICHER_REVISION,
        "taxonomy_revision": TAXONOMY_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "segment_id": segment_id,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "taxonomy": {dim: taxonomy[dim] for dim in REQUIRED_DIMENSIONS},
        "dimension_evidence": dimension_evidence,
        "compatibility": compatibility,
        "decision": {
            "status": status,
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "promotion_eligible": promotion_eligible,
            "exact_match_use_allowed": exact_match_use_allowed,
            "source_bytes_unchanged": True,
        },
    }


def validate_enrichment_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise FoleyTaxonomyError(f"schema_validation_failed:{location}:{first.message}")
    registry = load_taxonomy_registry(root)
    compatibility = evaluate_compatibility(record["taxonomy"], registry)
    if compatibility != record["compatibility"]:
        raise FoleyTaxonomyError("compatibility_projection_mismatch")


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row079_fixture:{label}".encode("utf-8"))


FIXTURE_TAXONOMIES: dict[str, dict[str, str]] = {
    "heel_on_hardwood": {
        "event_family": "footstep",
        "contact_pair": "heel_to_surface",
        "body_region": "foot",
        "footwear": "heel",
        "gait_phase": "heel_strike",
        "surface_material": "hardwood",
        "object_material": "none",
        "force": "medium",
        "attack": "transient",
        "motion": "strike",
        "room": "dry_close",
        "source_perspective": "close_mic",
    },
    "hand_to_body_contact": {
        "event_family": "body_contact",
        "contact_pair": "hand_to_body",
        "body_region": "hand",
        "footwear": "none",
        "gait_phase": "n_a",
        "surface_material": "skin",
        "object_material": "none",
        "force": "light",
        "attack": "soft_onset",
        "motion": "press",
        "room": "small_room",
        "source_perspective": "near_field",
    },
    "unknown_force_blocks_exact_match": {
        "event_family": "impact",
        "contact_pair": "object_to_object",
        "body_region": "none",
        "footwear": "none",
        "gait_phase": "n_a",
        "surface_material": "metal",
        "object_material": "metal",
        "force": "unknown",
        "attack": "transient",
        "motion": "strike",
        "room": "medium_room",
        "source_perspective": "mid_field",
    },
    "unknown_room_blocks_exact_match": {
        "event_family": "friction",
        "contact_pair": "cloth_to_cloth",
        "body_region": "torso",
        "footwear": "none",
        "gait_phase": "n_a",
        "surface_material": "fabric",
        "object_material": "fabric",
        "force": "soft",
        "attack": "sustained",
        "motion": "rub",
        "room": "unknown",
        "source_perspective": "near_field",
    },
    "footwear_contact_mismatch": {
        "event_family": "body_contact",
        "contact_pair": "hand_to_body",
        "body_region": "hand",
        "footwear": "heel",
        "gait_phase": "n_a",
        "surface_material": "skin",
        "object_material": "none",
        "force": "light",
        "attack": "soft_onset",
        "motion": "press",
        "room": "dry_close",
        "source_perspective": "close_mic",
    },
}


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    if fixture_name not in FIXTURE_TAXONOMIES:
        raise FoleyTaxonomyError(f"unknown_fixture:{fixture_name}")
    taxonomy = dict(FIXTURE_TAXONOMIES[fixture_name])
    source_sha = _stable_hash(f"source:{fixture_name}")
    pcm_sha = _stable_hash(f"pcm:{fixture_name}")
    record = build_enrichment_record(
        root,
        asset_id=f"fixture:{fixture_name}",
        source_sha256=source_sha,
        segment_id=f"fixture_segment:{fixture_name}",
        canonical_pcm_sha256=pcm_sha,
        taxonomy=taxonomy,
        evidence_source=f"synthetic_fixture:{fixture_name}",
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    validate_enrichment_record(root, record)
    return record


def assert_promotion_fail_closed(root: Path, record: dict[str, Any]) -> list[str]:
    """Return blocker codes that must prevent promotion / exact-match use."""
    validate_enrichment_record(root, record)
    blockers: list[str] = []
    if record["decision"]["library_authority"] is not True:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    if not record["compatibility"]["exact_match_compatible"]:
        blockers.append("EXACT_MATCH_USE_BLOCKED")
    if record["compatibility"]["unknown_dimensions"]:
        blockers.append("UNKNOWN_DIMENSION_BLOCKS_EXACT_MATCH")
    if record["compatibility"]["invalid_dimensions"]:
        blockers.append("INVALID_TAXONOMY_VALUE")
    blockers.extend(record["compatibility"]["semantic_blocker_codes"])
    if record["decision"]["promotion_eligible"] and blockers:
        raise FoleyTaxonomyError("promotion_eligible_despite_blockers")
    if record["decision"]["exact_match_use_allowed"] and (
        not record["compatibility"]["exact_match_compatible"]
        or not record["decision"]["library_authority"]
    ):
        raise FoleyTaxonomyError("exact_match_allowed_despite_incompatibility")
    return sorted(set(blockers))


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row074 = evaluate_row074_admission(root)
    row076 = evaluate_row076_admission(root)
    row078 = evaluate_row078_admission(root)
    blocker_codes: list[str] = []
    for admission in (row074, row076, row078):
        blocker_codes.extend(admission["blocker_codes"])
    if not (
        row074["dependency_satisfied"]
        and row076["dependency_satisfied"]
        and row078["dependency_satisfied"]
    ):
        if "ROW074_ROW076_ROW078_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW074_ROW076_ROW078_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_FULL_LIBRARY_ENRICHMENT_RUNTIME_ABSENT",
        "PROMOTED_FOLEY_SUBSET_RECONCILIATION_ABSENT",
        "CALIBRATED_HELD_OUT_FOLEY_LABEL_SETS_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_names = list(FIXTURE_TAXONOMIES.keys())
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    registry = load_taxonomy_registry(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-079_fine_grained_foley_taxonomy",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "enricher_revision": ENRICHER_REVISION,
        "taxonomy_revision": TAXONOMY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW074_ROW076_ROW078_DEPENDENCIES_AND_FULL_LIBRARY_TAXONOMY_RUNTIME_ABSENT",
        "required_dimensions": list(REQUIRED_DIMENSIONS),
        "row074_admission": row074,
        "row076_admission": row076,
        "row078_admission": row078,
        "taxonomy_registry": {
            "path": str(TAXONOMY_REGISTRY_PATH).replace("\\", "/"),
            "revision": registry["revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, TAXONOMY_REGISTRY_PATH, "taxonomy_registry")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove required-dimension coverage, explicit-unknown "
                "exact-match blocking, semantic inconsistency guards, and promotion "
                "fail-closed behavior; they do not accept Row079 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row079_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row074 segment/virtual-clip identity, Row076 acoustic "
                "room/perspective evidence, and Row078 source-attributed ensemble "
                "tags; reconcile every retained Foley asset to this frozen taxonomy "
                "revision with explicit unknowns that block incompatible exact-match "
                "use; then replace this hold packet with full-library enrichment and "
                "promoted-subset reconciliation evidence."
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
    parser.add_argument("--fixture", default="heel_on_hardwood")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise FoleyTaxonomyError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise FoleyTaxonomyError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
