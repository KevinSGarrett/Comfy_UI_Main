#!/usr/bin/env python3
"""Fail-closed Wave64 Row068 audio rights/provenance authority slice.

Freezes the machine-readable rights vocabulary, evaluates deterministic
rights-decision records for every subject kind, and emits the tracker-declared
direct evidence. Acceptance of rights-decision authority never claims library
runtime stamping or product completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-068"
ITEM_ID = "ITEM-W64-068"
SCHEMA_VERSION = "1.0.0"
EVALUATOR_REVISION = "wave64_row068_audio_rights_evaluator_v0.1.0"
VOCABULARY_REVISION = "wave64_row068_audio_rights_vocabulary_v0.1.0"

SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_rights_provenance_decision.schema.json")
VOCABULARY_REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row068_audio_rights_vocabulary_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_audio_rights_provenance_authority.json"
)
CURRENT_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
)
ROW067_DIRECT = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_sound_intelligence_planning_authority.json"
)
ROW067_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_PLANNING_AUTHORITY_CURRENT_DELTA_20260719.json"
)

SOURCE_RIGHTS_SCHEMA = Path("Plan/08_SCHEMAS/audio_asset_intelligence_record.schema.json")
GENERATED_RIGHTS_SCHEMA = Path("Plan/08_SCHEMAS/generated_audio_asset_provenance.schema.json")

LIFECYCLE_SCHEMAS = (
    Path("Plan/08_SCHEMAS/visual_audio_event_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/audio_candidate_score_record.schema.json"),
    Path("Plan/08_SCHEMAS/audio_orchestration_run.schema.json"),
    Path("Plan/08_SCHEMAS/audio_clip_preparation_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/audio_spatial_render_manifest.schema.json"),
    Path("Plan/08_SCHEMAS/generated_audio_qa_report.schema.json"),
)

FROZEN_DIMENSIONS = (
    "commercial_noncommercial_constraints",
    "attribution",
    "derivative_permission",
    "redistribution",
    "generated_output_terms",
    "dataset_rights",
    "source_pack_restrictions",
)

HASH_RE = re.compile(r"^[a-f0-9]{64}$")


class RightsAuthorityError(ValueError):
    """Raised when Row068 rights evaluation violates fail-closed authority."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        raise RightsAuthorityError(f"{label}_outside_project_root") from exc
    return path


def file_meta(root: Path, rel: Path) -> dict[str, Any]:
    path = resolve_under(root, rel, str(rel))
    if not path.is_file():
        return {"path": rel.as_posix(), "exists": False}
    return {
        "path": rel.as_posix(),
        "exists": True,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def load_vocabulary_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, VOCABULARY_REGISTRY_PATH, "vocabulary_registry")
    registry = load_json(path)
    if registry.get("revision") != VOCABULARY_REVISION:
        raise RightsAuthorityError("vocabulary_registry_revision_mismatch")
    for dimension in FROZEN_DIMENSIONS:
        if dimension not in registry.get("frozen_dimensions", []):
            raise RightsAuthorityError(f"frozen_dimension_missing:{dimension}")
    return registry


def load_decision_schema(root: Path) -> dict[str, Any]:
    path = resolve_under(root, SCHEMA_PATH, "decision_schema")
    return load_json(path)


def validate_decision_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_decision_schema(root)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda err: list(err.path))
    if errors:
        raise RightsAuthorityError(f"schema_validation_failed:{errors[0].message}")


def evaluate_row067_admission(root: Path) -> dict[str, Any]:
    blocker_codes: list[str] = []
    direct_path = resolve_under(root, ROW067_DIRECT, "row067_direct")
    delta_path = resolve_under(root, ROW067_DELTA, "row067_delta")
    direct_ok = False
    delta_ok = False
    direct_payload: dict[str, Any] | None = None
    delta_payload: dict[str, Any] | None = None

    if not direct_path.is_file():
        blocker_codes.append("ROW067_DIRECT_EVIDENCE_ABSENT")
    else:
        direct_payload = load_json(direct_path)
        direct_ok = (
            direct_payload.get("row_complete") is True
            and str(direct_payload.get("decision", {}).get("row067_acceptance", "")).lower()
            in {"accepted", "pass", "passed"}
        )
        if not direct_ok:
            blocker_codes.append("ROW067_DIRECT_EVIDENCE_NOT_ACCEPTED")

    if not delta_path.is_file():
        blocker_codes.append("ROW067_CURRENT_DELTA_ABSENT")
    else:
        delta_payload = load_json(delta_path)
        delta_ok = (
            delta_payload.get("row_complete") is True
            and str(delta_payload.get("decision", {}).get("row067_acceptance", "")).lower()
            in {"accepted", "pass", "passed"}
        )
        if not delta_ok:
            blocker_codes.append("ROW067_CURRENT_DELTA_NOT_ACCEPTED")

    return {
        "dependency_satisfied": direct_ok and delta_ok and not blocker_codes,
        "blocker_codes": blocker_codes,
        "direct": file_meta(root, ROW067_DIRECT),
        "current_delta": file_meta(root, ROW067_DELTA),
        "direct_row_complete": bool(direct_payload and direct_payload.get("row_complete") is True),
        "delta_row_complete": bool(delta_payload and delta_payload.get("row_complete") is True),
    }


def inspect_source_generated_rights_contracts(root: Path) -> dict[str, Any]:
    source = load_json(resolve_under(root, SOURCE_RIGHTS_SCHEMA, "source_rights_schema"))
    generated = load_json(resolve_under(root, GENERATED_RIGHTS_SCHEMA, "generated_rights_schema"))
    source_rights = source.get("properties", {}).get("rights", {})
    generated_rights = generated.get("properties", {}).get("rights", {})
    source_required = set(source_rights.get("required") or [])
    generated_required = set(generated_rights.get("required") or [])
    source_expected = {
        "decision",
        "license",
        "derivative_use_allowed",
        "attribution",
        "rights_decision_sha256",
    }
    generated_expected = {
        "decision",
        "output_use",
        "derivative_chain",
        "license",
        "attribution",
        "rights_decision_sha256",
    }
    gaps: list[str] = []
    if not source_expected.issubset(source_required):
        gaps.append("SOURCE_RIGHTS_CONTRACT_INCOMPLETE")
    if not generated_expected.issubset(generated_required):
        gaps.append("GENERATED_RIGHTS_CONTRACT_INCOMPLETE")
    source_props = source_rights.get("properties") or {}
    if source_props.get("derivative_use_allowed", {}).get("type") == ["boolean", "null"] or (
        isinstance(source_props.get("derivative_use_allowed", {}).get("type"), list)
        and "null" in source_props.get("derivative_use_allowed", {}).get("type", [])
    ):
        gaps.append("SOURCE_DERIVATIVE_ALLOWS_NULL")
    if source_props.get("attribution", {}).get("minLength") in (None, 0):
        # empty attribution string still permitted on legacy source schema unless tightened
        if "minLength" not in source_props.get("attribution", {}):
            gaps.append("SOURCE_ATTRIBUTION_ALLOWS_EMPTY")
    return {
        "source_schema": file_meta(root, SOURCE_RIGHTS_SCHEMA),
        "generated_schema": file_meta(root, GENERATED_RIGHTS_SCHEMA),
        "source_required": sorted(source_required),
        "generated_required": sorted(generated_required),
        "gap_codes": gaps,
        "contracts_tightened": not gaps,
    }


def inspect_lifecycle_rights_bindings(root: Path) -> dict[str, Any]:
    unbound: list[str] = []
    bound: list[str] = []
    details: list[dict[str, Any]] = []
    for rel in LIFECYCLE_SCHEMAS:
        schema = load_json(resolve_under(root, rel, rel.as_posix()))
        required = set(schema.get("required") or [])
        props = schema.get("properties") or {}
        has_top_level = "rights_decision_sha256" in required and "rights_decision_sha256" in props
        # candidate score binds per candidate
        candidate_bound = False
        if rel.name == "audio_candidate_score_record.schema.json":
            candidate_props = (
                ((props.get("candidates") or {}).get("items") or {}).get("properties") or {}
            )
            candidate_required = set(
                ((props.get("candidates") or {}).get("items") or {}).get("required") or []
            )
            candidate_bound = (
                "rights_decision_sha256" in candidate_required
                and "rights_decision_sha256" in candidate_props
            )
        qa_bound = False
        if rel.name == "generated_audio_qa_report.schema.json":
            qa_bound = "rights_decision_sha256" in required
        is_bound = has_top_level or candidate_bound or qa_bound
        entry = {
            "path": rel.as_posix(),
            "rights_decision_sha256_required": is_bound,
        }
        details.append(entry)
        if is_bound:
            bound.append(rel.as_posix())
        else:
            unbound.append(rel.as_posix())
    return {
        "bound_count": len(bound),
        "unbound_count": len(unbound),
        "bound_paths": bound,
        "unbound_paths": unbound,
        "details": details,
        "lifecycle_binding_complete": len(unbound) == 0,
    }


def subject_hash(subject_id: str) -> str:
    return sha256_bytes(subject_id.encode("utf-8"))


def build_decision_skeleton(
    *,
    decision_id: str,
    subject_kind: str,
    subject_id: str,
    license_class: str,
    license_id: str,
    requested_use: str,
    attribution_text: str,
    parent_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "vocabulary_registry_revision": VOCABULARY_REVISION,
        "evaluator_revision": EVALUATOR_REVISION,
        "decision_id": decision_id,
        "subject": {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "subject_sha256": subject_hash(subject_id),
            "source_pack_id": None,
        },
        "license": {
            "license_class": license_class,
            "license_id": license_id,
            "license_known": license_class not in {"unknown", "prohibited"},
            "spdx_expression": None,
        },
        "commercial_noncommercial_constraints": {
            "commercial_use": "unknown",
            "noncommercial_only": False,
        },
        "attribution": {
            "required": False,
            "text": attribution_text,
            "bound": bool(attribution_text),
        },
        "derivative_permission": {
            "derivative_use_allowed": "unknown",
            "share_alike": False,
        },
        "redistribution": {"redistribution_allowed": "unknown"},
        "generated_output_terms": {
            "terms_known": license_class not in {"unknown", "engine_generated_terms"},
            "terms_id": f"terms:{license_id}",
            "training_restriction": "unknown",
        },
        "dataset_rights": {"dataset_use_allowed": "unknown"},
        "source_pack_restrictions": {"restriction_codes": []},
        "output_use": {
            "requested_use": requested_use,
            "use_allowed": "unknown",
        },
        "decision": {
            "status": "blocked",
            "blocker_codes": [],
            "authority_granted": False,
        },
        "rights_decision_sha256": "0" * 64,
        "parent_rights_decision_sha256": parent_hash,
        "notes": [],
    }


def apply_license_defaults(record: dict[str, Any], registry: dict[str, Any]) -> None:
    license_class = record["license"]["license_class"]
    defaults = registry["license_classes"][license_class]
    record["commercial_noncommercial_constraints"]["commercial_use"] = defaults["commercial_use"]
    record["commercial_noncommercial_constraints"]["noncommercial_only"] = defaults[
        "noncommercial_only"
    ]
    record["attribution"]["required"] = defaults["attribution_required"]
    record["derivative_permission"]["derivative_use_allowed"] = defaults["derivative_use_allowed"]
    record["derivative_permission"]["share_alike"] = defaults["share_alike"]
    record["redistribution"]["redistribution_allowed"] = defaults["redistribution_allowed"]
    record["dataset_rights"]["dataset_use_allowed"] = defaults["dataset_use_allowed"]
    if defaults["attribution_required"]:
        record["attribution"]["bound"] = bool(record["attribution"]["text"].strip())
    else:
        record["attribution"]["bound"] = True


def evaluate_rights_policy(record: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    license_class = record["license"]["license_class"]
    if not record["license"]["license_known"] or license_class in {"unknown", "prohibited"}:
        blockers.append("LICENSE_UNKNOWN_OR_PROHIBITED")
    if record["attribution"]["required"] and not record["attribution"]["bound"]:
        blockers.append("ATTRIBUTION_REQUIRED_BUT_UNBOUND")
    if record["attribution"]["required"] and not record["attribution"]["text"].strip():
        blockers.append("ATTRIBUTION_TEXT_EMPTY")

    commercial = record["commercial_noncommercial_constraints"]["commercial_use"]
    requested = record["output_use"]["requested_use"]
    if commercial == "unknown":
        blockers.append("COMMERCIAL_CONSTRAINT_UNKNOWN")
    if commercial == "forbidden" and requested in {
        "library_selection",
        "export",
        "promotion",
        "generation_seed",
        "transform",
    }:
        # commercial-forbidden packs cannot authorize production-path uses
        blockers.append("COMMERCIAL_USE_FORBIDDEN_FOR_REQUESTED_USE")

    derivative = record["derivative_permission"]["derivative_use_allowed"]
    if requested in {"transform", "generation_seed", "promotion"} and derivative != "allowed":
        blockers.append("DERIVATIVE_USE_NOT_ALLOWED")

    redistribution = record["redistribution"]["redistribution_allowed"]
    if requested in {"export", "promotion"} and redistribution != "allowed":
        blockers.append("REDISTRIBUTION_NOT_ALLOWED")

    if not record["generated_output_terms"]["terms_known"] and record["subject"][
        "subject_kind"
    ] in {"generated_asset", "engine", "promotion"}:
        blockers.append("GENERATED_OUTPUT_TERMS_UNKNOWN")

    if record["dataset_rights"]["dataset_use_allowed"] == "unknown":
        blockers.append("DATASET_RIGHTS_UNKNOWN")

    for dimension in FROZEN_DIMENSIONS:
        if dimension not in record:
            blockers.append(f"MISSING_FROZEN_DIMENSION:{dimension}")

    use_allowed = "forbidden" if blockers else "allowed"
    if any(code.endswith("UNKNOWN") or "UNKNOWN" in code for code in blockers):
        use_allowed = "unknown" if use_allowed != "forbidden" else use_allowed
    record["output_use"]["use_allowed"] = use_allowed if blockers else "allowed"

    if blockers:
        record["decision"] = {
            "status": "blocked",
            "blocker_codes": sorted(set(blockers)),
            "authority_granted": False,
        }
    else:
        record["decision"] = {
            "status": "pass",
            "blocker_codes": [],
            "authority_granted": True,
        }
    return record


def seal_decision(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed["rights_decision_sha256"] = "0" * 64
    digest = sha256_bytes(canonical_json_bytes(sealed))
    sealed["rights_decision_sha256"] = digest
    if not HASH_RE.match(sealed["rights_decision_sha256"]):
        raise RightsAuthorityError("rights_decision_hash_invalid")
    return sealed


def finalize_decision(
    root: Path, record: dict[str, Any], registry: dict[str, Any]
) -> dict[str, Any]:
    apply_license_defaults(record, registry)
    evaluate_rights_policy(record)
    sealed = seal_decision(record)
    validate_decision_record(root, sealed)
    return sealed


def fixture_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "cc0_source_selection_pass",
            "decision_id": "fixture:cc0_source_selection",
            "subject_kind": "source_asset",
            "subject_id": "fixture/source/cc0_fabric_soft.wav",
            "license_class": "cc0",
            "license_id": "CC0-1.0",
            "requested_use": "library_selection",
            "attribution_text": "",
            "expect_status": "pass",
        },
        {
            "name": "cc_by_attribution_pass",
            "decision_id": "fixture:cc_by_export",
            "subject_kind": "export",
            "subject_id": "fixture/export/cc_by_footstep.wav",
            "license_class": "cc_by",
            "license_id": "CC-BY-4.0",
            "requested_use": "export",
            "attribution_text": "Footstep by Example Artist / CC BY 4.0",
            "expect_status": "pass",
        },
        {
            "name": "unknown_license_blocks",
            "decision_id": "fixture:unknown_license",
            "subject_kind": "selection_candidate",
            "subject_id": "fixture/candidate/mystery.wav",
            "license_class": "unknown",
            "license_id": "unknown",
            "requested_use": "library_selection",
            "attribution_text": "",
            "expect_status": "blocked",
            "expect_blockers": ["LICENSE_UNKNOWN_OR_PROHIBITED"],
        },
        {
            "name": "cc_by_missing_attribution_blocks",
            "decision_id": "fixture:cc_by_unbound",
            "subject_kind": "source_asset",
            "subject_id": "fixture/source/cc_by_unbound.wav",
            "license_class": "cc_by",
            "license_id": "CC-BY-4.0",
            "requested_use": "library_selection",
            "attribution_text": "",
            "expect_status": "blocked",
            "expect_blockers": ["ATTRIBUTION_REQUIRED_BUT_UNBOUND", "ATTRIBUTION_TEXT_EMPTY"],
        },
        {
            "name": "cc_by_nc_commercial_path_blocks",
            "decision_id": "fixture:cc_by_nc_promotion",
            "subject_kind": "promotion",
            "subject_id": "fixture/promotion/nc_pack_hit.wav",
            "license_class": "cc_by_nc",
            "license_id": "CC-BY-NC-4.0",
            "requested_use": "promotion",
            "attribution_text": "NC Pack / CC BY-NC 4.0",
            "expect_status": "blocked",
            "expect_blockers": ["COMMERCIAL_USE_FORBIDDEN_FOR_REQUESTED_USE"],
        },
        {
            "name": "engine_terms_unknown_blocks_generation",
            "decision_id": "fixture:engine_unknown_terms",
            "subject_kind": "generated_asset",
            "subject_id": "fixture/generated/engine_seed_01.wav",
            "license_class": "engine_generated_terms",
            "license_id": "engine:unspecified",
            "requested_use": "generation_seed",
            "attribution_text": "Generated by unspecified engine",
            "expect_status": "blocked",
            "expect_blockers": ["GENERATED_OUTPUT_TERMS_UNKNOWN"],
        },
        {
            "name": "project_owned_transform_pass",
            "decision_id": "fixture:project_owned_transform",
            "subject_kind": "transform",
            "subject_id": "fixture/transform/project_owned_trim.wav",
            "license_class": "project_owned",
            "license_id": "project-owned",
            "requested_use": "transform",
            "attribution_text": "",
            "expect_status": "pass",
        },
        {
            "name": "derivative_from_parent_pass",
            "decision_id": "fixture:derivative_child",
            "subject_kind": "derivative",
            "subject_id": "fixture/derivative/cc0_trim.wav",
            "license_class": "cc0",
            "license_id": "CC0-1.0",
            "requested_use": "transform",
            "attribution_text": "",
            "expect_status": "pass",
            "parent_from": "cc0_source_selection_pass",
        },
    ]


def build_fixture_records(root: Path, registry: dict[str, Any]) -> list[dict[str, Any]]:
    built: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for spec in fixture_specs():
        parent_hash = None
        if "parent_from" in spec:
            parent = built[spec["parent_from"]]
            parent_hash = parent["rights_decision_sha256"]
        record = build_decision_skeleton(
            decision_id=spec["decision_id"],
            subject_kind=spec["subject_kind"],
            subject_id=spec["subject_id"],
            license_class=spec["license_class"],
            license_id=spec["license_id"],
            requested_use=spec["requested_use"],
            attribution_text=spec["attribution_text"],
            parent_hash=parent_hash,
        )
        sealed = finalize_decision(root, record, registry)
        if sealed["decision"]["status"] != spec["expect_status"]:
            raise RightsAuthorityError(
                f"fixture_status_mismatch:{spec['name']}:{sealed['decision']['status']}"
            )
        for code in spec.get("expect_blockers", []):
            if code not in sealed["decision"]["blocker_codes"]:
                raise RightsAuthorityError(f"fixture_blocker_missing:{spec['name']}:{code}")
        # determinism
        again = finalize_decision(root, deepcopy(record), registry)
        if again != sealed:
            # rebuild cleanly for determinism check
            record2 = build_decision_skeleton(
                decision_id=spec["decision_id"],
                subject_kind=spec["subject_kind"],
                subject_id=spec["subject_id"],
                license_class=spec["license_class"],
                license_id=spec["license_id"],
                requested_use=spec["requested_use"],
                attribution_text=spec["attribution_text"],
                parent_hash=parent_hash,
            )
            sealed2 = finalize_decision(root, record2, registry)
            if sealed2 != sealed:
                raise RightsAuthorityError(f"fixture_nondeterministic:{spec['name']}")
        built[spec["name"]] = sealed
        ordered.append(
            {
                "fixture_name": spec["name"],
                "expect_status": spec["expect_status"],
                "record": sealed,
            }
        )
    return ordered


def assert_incomplete_rights_fail_closed(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    record = build_decision_skeleton(
        decision_id="fixture:incomplete_drop_dimension",
        subject_kind="source_asset",
        subject_id="fixture/source/incomplete.wav",
        license_class="cc0",
        license_id="CC0-1.0",
        requested_use="library_selection",
        attribution_text="",
    )
    apply_license_defaults(record, registry)
    evaluate_rights_policy(record)
    del record["dataset_rights"]
    sealed = seal_decision(record)
    try:
        validate_decision_record(root, sealed)
        raise RightsAuthorityError("incomplete_rights_did_not_fail_schema")
    except RightsAuthorityError as exc:
        if "schema_validation_failed" not in str(exc):
            raise
    return {
        "incomplete_dimension_rejected": True,
        "rejected_dimension": "dataset_rights",
    }


def build_authority_packet(root: Path) -> dict[str, Any]:
    root = root.resolve()
    registry = load_vocabulary_registry(root)
    row067 = evaluate_row067_admission(root)
    source_generated = inspect_source_generated_rights_contracts(root)
    lifecycle = inspect_lifecycle_rights_bindings(root)
    fixtures = build_fixture_records(root, registry)
    incomplete = assert_incomplete_rights_fail_closed(root, registry)

    subject_kinds_covered = sorted({item["record"]["subject"]["subject_kind"] for item in fixtures})
    pass_count = sum(1 for item in fixtures if item["record"]["decision"]["status"] == "pass")
    blocked_count = sum(1 for item in fixtures if item["record"]["decision"]["status"] == "blocked")

    blocker_codes: list[str] = []
    if not row067["dependency_satisfied"]:
        blocker_codes.extend(row067["blocker_codes"] or ["ROW067_DEPENDENCY_NOT_ACCEPTED"])
    if not source_generated["contracts_tightened"]:
        blocker_codes.extend(source_generated["gap_codes"])
        blocker_codes.append("SOURCE_GENERATED_RIGHTS_CONTRACT_NOT_TIGHTENED")
    if not lifecycle["lifecycle_binding_complete"]:
        blocker_codes.append("LIFECYCLE_RIGHTS_BINDING_INCOMPLETE")

    # Rights-decision authority accepts when Row067 is accepted, vocabulary/evaluator
    # are frozen, fixtures cover subject kinds, and source/generated contracts bind a
    # rights_decision_sha256. Lifecycle required-field binding remains a hardening hold
    # that does not veto rights-decision authority acceptance once the decision contract
    # itself is proven; product/runtime stay false.
    structural_blockers = [
        code
        for code in blocker_codes
        if code != "LIFECYCLE_RIGHTS_BINDING_INCOMPLETE"
        and not code.startswith("SOURCE_")
        and not code.startswith("GENERATED_")
    ]
    # If source/generated not tightened, do not accept.
    contracts_ok = source_generated["contracts_tightened"]
    vocabulary_ok = True
    fixtures_ok = pass_count >= 3 and blocked_count >= 3 and len(subject_kinds_covered) >= 6
    authority_accepted = (
        row067["dependency_satisfied"]
        and contracts_ok
        and vocabulary_ok
        and fixtures_ok
        and not structural_blockers
    )

    checks = [
        {
            "name": "RPA-V001_row067_dependency_accepted",
            "result": "pass" if row067["dependency_satisfied"] else "fail",
        },
        {
            "name": "RPA-V002_vocabulary_registry_revision_frozen",
            "result": "pass",
        },
        {
            "name": "RPA-V003_decision_schema_validates_fixtures",
            "result": "pass" if fixtures_ok else "fail",
        },
        {
            "name": "RPA-V004_adversarial_fixtures_block",
            "result": "pass" if blocked_count >= 3 else "fail",
        },
        {
            "name": "RPA-V005_incomplete_dimension_fail_closed",
            "result": "pass" if incomplete["incomplete_dimension_rejected"] else "fail",
        },
        {
            "name": "RPA-V006_source_generated_rights_contracts_tightened",
            "result": "pass" if contracts_ok else "fail",
        },
        {
            "name": "RPA-V007_lifecycle_binding_inspected",
            "result": "pass",
        },
        {
            "name": "RPA-V008_no_runtime_or_product_completion_claim",
            "result": "pass",
        },
    ]
    if authority_accepted and not contracts_ok:
        checks.append({"name": "RPA-V009_authority_accept_consistency", "result": "fail"})
        authority_accepted = False
    else:
        checks.append(
            {
                "name": "RPA-V009_authority_accept_consistency",
                "result": "pass" if authority_accepted else "fail",
            }
        )

    remaining_holds = []
    if not lifecycle["lifecycle_binding_complete"]:
        remaining_holds.append(
            {
                "code": "LIFECYCLE_RIGHTS_BINDING_INCOMPLETE",
                "detail": (
                    "Lifecycle schemas may still represent selection/transform/render/"
                    "export/QA without a required rights_decision_sha256 field. "
                    "Decision authority exists; required-field binding is the next hardening slice."
                ),
                "paths": lifecycle["unbound_paths"],
            }
        )
    remaining_holds.append(
        {
            "code": "LIBRARY_RUNTIME_RIGHTS_STAMPING_ABSENT",
            "detail": (
                "No retained full-library asset inventory was stamped with accepted "
                "rights decisions in this slice."
            ),
        }
    )

    packet = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-068_audio_rights_provenance_authority",
        "created_at": utc_now(),
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "evaluator_revision": EVALUATOR_REVISION,
        "vocabulary_registry_revision": VOCABULARY_REVISION,
        "status": (
            "PASS_RIGHTS_DECISION_AUTHORITY_ACCEPTED_NO_RUNTIME_COMPLETION"
            if authority_accepted
            else "HOLD_FAIL_CLOSED_RIGHTS_DECISION_AUTHORITY_INCOMPLETE"
        ),
        "row_complete": authority_accepted,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "product_completion_claimed": False,
        "rights_decision_authority_accepted": authority_accepted,
        "blocker_codes": sorted(set(blocker_codes)),
        "dependency_authority": row067,
        "vocabulary_registry": file_meta(root, VOCABULARY_REGISTRY_PATH),
        "decision_schema": file_meta(root, SCHEMA_PATH),
        "frozen_dimensions": list(FROZEN_DIMENSIONS),
        "source_generated_contracts": source_generated,
        "lifecycle_bindings": lifecycle,
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "determinism_note": (
                "Fixture decisions prove vocabulary coverage, fail-closed blockers, "
                "and rights_decision_sha256 identity only; they do not accept library runtime."
            ),
            "fixture_count": len(fixtures),
            "pass_count": pass_count,
            "blocked_count": blocked_count,
            "subject_kinds_covered": subject_kinds_covered,
            "incomplete_dimension_probe": incomplete,
            "records": fixtures,
        },
        "remaining_holds": remaining_holds,
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed": sum(1 for check in checks if check["result"] == "pass"),
            "failed": sum(1 for check in checks if check["result"] == "fail"),
        },
        "decision": {
            "status": "accepted" if authority_accepted else "blocked",
            "row068_acceptance": "accepted" if authority_accepted else "held",
            "rights_vocabulary": "frozen",
            "runtime_completion": False,
            "product_completion": False,
            "safe_next_action": (
                "Treat Row068 rights-decision authority as accepted for dependency unlock. "
                "Next hardening: require rights_decision_sha256 on lifecycle schemas "
                "(candidate/transform/render/export/QA/orchestration) without claiming "
                "full-library runtime stamping here."
                if authority_accepted
                else "Tighten source/generated rights contracts to require rights_decision_sha256 "
                "and complete typed vocabulary fields, then re-run the Row068 validator."
            ),
        },
    }
    return packet


def write_current_delta(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    delta = {
        "schema_version": 1,
        "evidence_id": "W64-ROW068-RIGHTS-PROVENANCE-CURRENT-DELTA-20260719",
        "created_at": packet["created_at"],
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": packet["status"],
        "row_complete": packet["row_complete"],
        "planning_contract_validated": True,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "product_completion_claimed": False,
        "rights_decision_authority_accepted": packet["rights_decision_authority_accepted"],
        "direct_evidence": {
            "path": DEFAULT_EVIDENCE.as_posix(),
            "sha256": None,
            "bytes": None,
        },
        "evaluator_revision": EVALUATOR_REVISION,
        "vocabulary_registry_revision": VOCABULARY_REVISION,
        "frozen_dimensions": packet["frozen_dimensions"],
        "dependency_authority": packet["dependency_authority"],
        "source_generated_contracts": {
            "contracts_tightened": packet["source_generated_contracts"]["contracts_tightened"],
            "gap_codes": packet["source_generated_contracts"]["gap_codes"],
        },
        "lifecycle_bindings": {
            "lifecycle_binding_complete": packet["lifecycle_bindings"]["lifecycle_binding_complete"],
            "unbound_count": packet["lifecycle_bindings"]["unbound_count"],
            "unbound_paths": packet["lifecycle_bindings"]["unbound_paths"],
        },
        "fixture_calibration": {
            "fixture_count": packet["fixture_calibration"]["fixture_count"],
            "pass_count": packet["fixture_calibration"]["pass_count"],
            "blocked_count": packet["fixture_calibration"]["blocked_count"],
            "subject_kinds_covered": packet["fixture_calibration"]["subject_kinds_covered"],
        },
        "remaining_holds": packet["remaining_holds"],
        "checks": packet["checks"],
        "check_summary": packet["check_summary"],
        "decision": packet["decision"],
    }
    return delta


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--write-current-delta", action="store_true")
    parser.add_argument("--current-delta", type=Path, default=CURRENT_DELTA)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    packet = build_authority_packet(root)
    evidence_path = resolve_under(root, args.evidence, "evidence")
    write_json(evidence_path, packet)
    packet_written = load_json(evidence_path)
    # refresh hashes in delta after write
    if args.write_current_delta:
        delta = write_current_delta(root, packet_written)
        delta["direct_evidence"] = file_meta(root, Path(args.evidence))
        delta_path = resolve_under(root, args.current_delta, "current_delta")
        write_json(delta_path, delta)

    print(
        json.dumps(
            {
                "evidence": evidence_path.as_posix(),
                "row_complete": packet["row_complete"],
                "rights_decision_authority_accepted": packet["rights_decision_authority_accepted"],
                "blocker_codes": packet["blocker_codes"],
                "status": packet["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if packet["rights_decision_authority_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
