from __future__ import annotations

import argparse
import base64
import binascii
import copy
import csv
import hashlib
import io
import json
import math
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


PACKAGE_ID = "wave64_maskfactory_autonomous_bridge_rows321_348"
UPDATED_AT = "2026-07-17T02:20:00-05:00"
STATUS = "Planned_Autonomous_Implementation_Required"
SCHEMA_VERSION = "2.0.0"
SCHEMA_BASE = "https://schemas.local/comfy-ui-main/wave64/maskfactory-bridge/v2"
COMMON_ID = f"{SCHEMA_BASE}/wave64_maskfactory_bridge_common_v2.schema.json"

ACCESS_MODES = ["mode_a_package_read", "mode_b_live_predict", "mode_b_live_refine"]
AUTHORITY_STATES = ["invalid", "hypothesis", "draft", "qa_passed_noncertified", "certified"]
ISSUER_KINDS = ["maskfactory_autonomous", "human_anchor_optional", "none"]
CLAIM_CLASSES = ["invalid", "machine_candidate", "qa_passed_machine_candidate", "operationally_certified_artifact", "independent_real_accuracy_anchor", "training_gold"]
EXECUTION_STATES = ["compiled", "admitted", "submitted", "accepted", "running", "completed_pending_receipt", "succeeded", "failed", "cancelled", "outcome_unknown", "reconciled_not_found"]
ALLOWED_EXECUTION_TRANSITIONS = [
    ["compiled", "admitted"], ["admitted", "submitted"], ["submitted", "accepted"], ["accepted", "running"],
    ["submitted", "succeeded"], ["submitted", "failed"], ["submitted", "cancelled"], ["submitted", "outcome_unknown"],
    ["accepted", "succeeded"], ["accepted", "failed"], ["accepted", "cancelled"], ["accepted", "outcome_unknown"],
    ["running", "succeeded"], ["running", "failed"], ["running", "cancelled"], ["running", "outcome_unknown"],
    ["outcome_unknown", "running"], ["outcome_unknown", "completed_pending_receipt"], ["outcome_unknown", "failed"], ["outcome_unknown", "reconciled_not_found"],
    ["completed_pending_receipt", "succeeded"], ["reconciled_not_found", "submitted"],
]
COMPLETION_PROFILES = ["core_autonomous_runtime", "independent_real_accuracy", "scale_daz_maturity"]
REQUIRED_ADOPTION_CHECK_IDS = [
    "release_payload_hash", "wire_schema_set", "required_fields", "semantic_invariant_profile", "api_contract",
    "package_format", "ontology", "node_pack", "capability_snapshot", "trust_policy", "invalidation_reason_policy", "journal_checkpoint", "revocation_checkpoint",
]
REQUIRED_BRIDGE_RELEASE_GATE_IDS = ["row218_runtime", *[f"row{number}_runtime" for number in range(321, 348)]]
APP_PAGE_GATE_IDS = {
    "home_readiness": ["row218_runtime", "row321_runtime", "row324_runtime", "row347_runtime"],
    "projects_revisions": ["row321_runtime", "row322_runtime", "row323_runtime", "row324_runtime"],
    "scene_builder_pose_masks": [f"row{number}_runtime" for number in range(325, 333)],
    "runs_dag": ["row333_runtime", "row337_runtime", "row338_runtime", "row341_runtime"],
    "queue_workers": ["row337_runtime", "row338_runtime", "row339_runtime"],
    "recovery": ["row324_runtime", "row337_runtime", "row338_runtime", "row339_runtime", "row340_runtime"],
    "qa": [*[f"row{number}_runtime" for number in range(329, 333)], *[f"row{number}_runtime" for number in range(341, 348)]],
}
PRODUCER_INVALIDATION_REASON_POLICY: dict[str, dict[str, list[str]]] = {
    "release_superseded": {"target_kinds": ["release"], "required_actions": ["refresh_release", "revalidate_adoption"]},
    "release_revoked": {"target_kinds": ["release"], "required_actions": ["rollback_release", "revalidate_adoption"]},
    "producer_signing_key_revoked": {"target_kinds": ["signing_key"], "required_actions": ["rotate_trust_anchor", "revalidate_adoption"]},
    "producer_signing_key_rotated": {"target_kinds": ["signing_key"], "required_actions": ["rotate_trust_anchor", "revalidate_adoption"]},
    "consumer_adoption_key_revoked": {"target_kinds": ["signing_key"], "required_actions": ["rotate_trust_anchor", "revalidate_adoption"]},
    "consumer_adoption_key_rotated": {"target_kinds": ["signing_key"], "required_actions": ["rotate_trust_anchor", "revalidate_adoption"]},
    "trust_policy_changed": {"target_kinds": ["trust_policy", "policy"], "required_actions": ["rotate_trust_anchor", "revalidate_adoption"]},
    "wire_schema_changed": {"target_kinds": ["wire_schema"], "required_actions": ["refresh_contract", "revalidate_adoption"]},
    "semantic_invariant_profile_changed": {"target_kinds": ["semantic_profile"], "required_actions": ["refresh_contract", "revalidate_adoption"]},
    "api_contract_changed": {"target_kinds": ["api_contract"], "required_actions": ["refresh_contract", "revalidate_adoption"]},
    "package_format_changed": {"target_kinds": ["package_format"], "required_actions": ["refresh_contract", "revalidate_adoption"]},
    "ontology_changed": {"target_kinds": ["ontology"], "required_actions": ["refresh_contract", "revalidate_adoption"]},
    "node_pack_changed": {"target_kinds": ["node_pack"], "required_actions": ["reinstall_node_pack", "revalidate_adoption"]},
    "capability_snapshot_changed": {"target_kinds": ["capability_snapshot"], "required_actions": ["refresh_capability_snapshot", "revalidate_adoption"]},
    "capability_policy_changed": {"target_kinds": ["policy", "capability_snapshot"], "required_actions": ["refresh_capability_snapshot", "revalidate_adoption"]},
    "package_invalidated": {"target_kinds": ["package"], "required_actions": ["invalidate_cache", "revalidate_adoption"]},
    "artifact_invalidated": {"target_kinds": ["artifact"], "required_actions": ["tombstone_cached_artifact", "revalidate_adoption"]},
    "artifact_hash_drift": {"target_kinds": ["artifact"], "required_actions": ["quarantine_artifact", "revalidate_adoption"]},
    "certificate_expired": {"target_kinds": ["certificate"], "required_actions": ["block_dependent_pass", "revalidate_adoption"]},
    "certificate_revoked": {"target_kinds": ["certificate"], "required_actions": ["block_dependent_pass", "revalidate_adoption"]},
    "provider_stack_changed": {"target_kinds": ["provider_stack", "execution_fingerprint"], "required_actions": ["reroute_to_eligible_authority", "revalidate_adoption"]},
    "consumer_requirements_changed": {"target_kinds": ["consumer_requirements"], "required_actions": ["refresh_consumer_requirements", "revalidate_adoption"]},
    "signed_journal_stale": {"target_kinds": ["journal_checkpoint"], "required_actions": ["replay_signed_journal", "revalidate_adoption"]},
    "signed_journal_fork_detected": {"target_kinds": ["journal_checkpoint"], "required_actions": ["reject_forked_journal", "revalidate_adoption"]},
    "revocation_checkpoint_stale": {"target_kinds": ["journal_checkpoint"], "required_actions": ["refresh_revocation_checkpoint", "revalidate_adoption"]},
    "validity_expired": {"target_kinds": ["adoption_receipt"], "required_actions": ["expire_adoption", "revalidate_adoption"]},
    "qa_regression": {"target_kinds": ["artifact", "certificate", "provider_stack"], "required_actions": ["quarantine_artifact", "block_dependent_pass"]},
}
PRODUCER_INVALIDATION_REASONS = list(PRODUCER_INVALIDATION_REASON_POLICY)
PRODUCER_INVALIDATION_TARGET_KINDS = sorted({value for policy in PRODUCER_INVALIDATION_REASON_POLICY.values() for value in policy["target_kinds"]})
PRODUCER_INVALIDATION_ACTIONS = sorted({value for policy in PRODUCER_INVALIDATION_REASON_POLICY.values() for value in policy["required_actions"]} | {"revalidate_binding"})
MAIN_INVALIDATION_ACTIONS = ["block_and_revalidate", "invalidate_cache_and_revalidate", "demote_and_repair", "rollback_or_block"]
PRODUCER_INVALIDATION_POLICY_BINDING_STATUS = "frozen_producer_contract_pending_signed_runtime_release_adoption"
SIGNER_ROLES = [
    "maskfactory_release_signer",
    "maskfactory_receipt_signer",
    "maskfactory_invalidation_signer",
    "main_adoption_signer",
    "main_journal_checkpoint_signer",
    "main_bridge_gate_signer",
    "main_bridge_event_signer",
    "main_bridge_release_signer",
    "maskfactory_operational_certificate_signer",
    "main_promotion_policy_signer",
    "main_normalization_signer",
    "main_trusted_clock_signer",
    "main_consumer_requirements_signer",
    "main_mask_request_signer",
    "main_mask_feedback_signer",
]

# These are exact raw-byte bindings to the frozen MaskFactory wire-contract tree.
# They are immutable design-time interoperability evidence, but not a substitute for
# the future signed runtime release/adoption pin that production consumption requires.
def frozen_producer_schema_binding(name: str, sha256: str, properties: list[str], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_id": f"https://maskfactory.local/schemas/{name}.schema.json",
        "schema_version": "1.0.0",
        "schema_sha256": sha256,
        "schema_source": f"MaskFactory:src/maskfactory/schemas/{name}.schema.json",
        "properties": properties,
        "required": required if required is not None else list(properties),
    }


PRODUCER_SCHEMA_BINDINGS: dict[str, dict[str, Any]] = {
    "maskfactory_release_snapshot": frozen_producer_schema_binding(
        "maskfactory_release_snapshot", "3f5e267c79c18c79212e2b69947f204d08335ae652f31cd859dae5c250b89f5b",
        ["schema_version", "record_type", "release_id", "release_status", "published_at", "evidence_context", "fixture_only", "canonicalization", "producer", "signing_trust", "canonicalization_spec", "artifact_security_policy", "journal_checkpoint", "compatibility", "wire_schemas", "semantic_invariant_profile", "completion_profiles", "artifacts", "openapi", "capability_snapshot", "workflow_inventory", "node_inventory", "certificate_index", "evidence_index", "known_limitations", "breaking_changes", "installation", "rollback", "supersedes_release_id", "revoked_release_ids", "release_payload_sha256", "signature"],
    ),
    "maskfactory_capability_snapshot": frozen_producer_schema_binding(
        "maskfactory_capability_snapshot", "68244dc62eae41b1ed6f045d43ac4f26e5c9b3beff2a65b3981dcd3afee9dc58",
        ["schema_version", "record_type", "snapshot_id", "release_id", "generated_at", "evidence_context", "fixture_only", "canonicalization", "bridge_contract", "access_modes", "endpoints", "package_formats", "ontologies", "labels", "artifact_kinds", "coordinate_spaces", "transform_operations", "limits", "authority_policy", "authority_crosswalk", "provider_stacks", "availability", "snapshot_sha256"],
    ),
    "maskfactory_consumer_requirements": frozen_producer_schema_binding(
        "maskfactory_consumer_requirements", "8d16b7d3829d810ad904b9427a3011bdc217d6030750bc978f62f53b41a6d3e8",
        ["schema_version", "record_type", "requirements_id", "consumer", "created_at", "authentication", "trust_binding", "canonicalization", "bridge_contract", "accepted_wire_schemas", "required_semantic_invariant_profile", "trusted_signing_key_sets", "required_access_modes", "required_capabilities", "optional_capabilities", "compatibility", "required_labels", "required_artifact_kinds", "required_coordinate_spaces", "required_transform_operations", "minimum_person_count", "accepted_media_scopes", "authority_requirements", "runtime_requirements", "requirements_sha256", "signature"],
    ),
    "mask_acquisition_request": frozen_producer_schema_binding(
        "mask_acquisition_request", "2160fd336a8ab25c25dd86babe418c7f2cf072a341c7e7bd94c00743e9103f72",
        ["schema_version", "record_type", "request_id", "project_id", "run_id", "correlation_id", "job_id", "pass_id", "attempt_id", "attempt_number", "hypothesis", "idempotency_key", "created_at", "deadline_at", "authentication", "trust_binding", "canonicalization", "access_mode", "media_scope", "source", "subject", "mask_intents", "target_regions", "protected_regions", "protected_owner_roster", "transform_chain", "compatibility", "minimum_authority_state", "accepted_authority", "resource_envelope", "retry_policy", "mode_payload", "request_payload_sha256", "signature"],
    ),
    "mask_acquisition_receipt": frozen_producer_schema_binding(
        "mask_acquisition_receipt", "2a16bf9fe3f9e46e14c02a1cee287f09a821eca20023124d852a4aaf5dc5f18d",
        ["schema_version", "record_type", "receipt_id", "request_id", "request_payload_sha256", "project_id", "run_id", "job_id", "pass_id", "attempt_id", "attempt_number", "hypothesis_id", "idempotency_key", "completed_at", "authentication", "trust_binding", "canonicalization", "result", "access_mode", "media_scope", "execution_observation", "release_binding", "source_binding", "subject_binding", "provider_binding", "artifacts", "transform_validation", "qa", "authority", "truth_tier", "lineage", "use_eligibility", "error", "receipt_payload_sha256", "signature"],
        ["schema_version", "record_type", "receipt_id", "request_id", "request_payload_sha256", "project_id", "run_id", "job_id", "pass_id", "attempt_id", "attempt_number", "hypothesis_id", "idempotency_key", "completed_at", "authentication", "trust_binding", "canonicalization", "result", "access_mode", "media_scope", "release_binding", "execution_observation", "source_binding", "subject_binding", "provider_binding", "artifacts", "transform_validation", "qa", "authority", "truth_tier", "lineage", "use_eligibility", "error", "receipt_payload_sha256", "signature"],
    ),
    "operational_autonomy_certificate": frozen_producer_schema_binding(
        "operational_autonomy_certificate", "9846b5afb7898a0af6f9b8f7169fe1eb5cc71ded1a3c0c37b28ed281d849bee8",
        ["schema_version", "record_type", "certificate_kind", "certificate_id", "canonicalization", "certificate_payload_sha256", "status", "issued_at", "expires_at", "evidence_context", "fixture_only", "issuer_kind", "authority_profile", "authority_state", "truth_tier", "access_mode", "media_scope", "release_binding", "ontology_binding", "pipeline_policy_binding", "execution_binding", "subject_binding", "source_binding", "coordinate_binding", "qualified_route_scope", "certified_output_scope", "lineage", "bound_artifacts", "qa_evidence", "revocation", "signature", "external_manual_anchor_required", "claim_limits"],
    ),
    "mask_bridge_error": frozen_producer_schema_binding(
        "mask_bridge_error", "c65a4fc9e8c4c1df8c63911c653e91e364ae23387758c4c9ed617f86e69e7219",
        ["schema_version", "record_type", "error_id", "request_id", "observed_at", "code", "category", "retryable", "impact_scope", "affected_scope", "remediation", "no_silent_fallback", "message", "details_sha256"],
    ),
    "maskfactory_adoption_receipt": frozen_producer_schema_binding(
        "maskfactory_adoption_receipt", "9edaf568c39b8bcf69e064d260425a411b8ac2addf19ae06b3b5a4269c56d5cc",
        ["schema_version", "record_type", "adoption_id", "decided_at", "adoption_scope", "evidence_context", "fixture_only", "production_use_authorized", "consumer", "release_id", "release_payload_sha256", "capability_snapshot_id", "capability_snapshot_sha256", "consumer_requirements_id", "consumer_requirements_sha256", "qualification_bundle_id", "qualification_bundle_sha256", "trust_binding", "journal_checkpoint", "decision", "required_capabilities_satisfied", "compatibility_checks", "pinned_artifacts", "capability_decisions", "accepted_capabilities", "rejected_capabilities", "valid_until", "use_time_recheck_required", "revalidation_triggers", "adoption_payload_sha256", "signature"],
        ["schema_version", "record_type", "adoption_id", "decided_at", "adoption_scope", "evidence_context", "fixture_only", "production_use_authorized", "consumer", "release_id", "release_payload_sha256", "capability_snapshot_id", "capability_snapshot_sha256", "consumer_requirements_id", "consumer_requirements_sha256", "qualification_bundle_id", "qualification_bundle_sha256", "trust_binding", "journal_checkpoint", "decision", "required_capabilities_satisfied", "compatibility_checks", "capability_decisions", "pinned_artifacts", "accepted_capabilities", "rejected_capabilities", "valid_until", "use_time_recheck_required", "revalidation_triggers", "adoption_payload_sha256", "signature"],
    ),
    "mask_authority_invalidation_event": frozen_producer_schema_binding(
        "mask_authority_invalidation_event", "72b072a1d239057a574ea9ff6dd8536e072d47f13b3b16f2edd6890a0ecb0920",
        ["schema_version", "record_type", "event_id", "stream_id", "sequence", "causation_id", "idempotency_key", "occurred_at", "effective_at", "evidence_context", "fixture_only", "producer", "canonicalization", "trust_binding", "reason", "severity", "target_transitions", "required_actions", "superseding_binding", "rollback_binding", "evidence_sha256", "event_payload_sha256", "signature"],
    ),
    "mask_repair_feedback": frozen_producer_schema_binding(
        "mask_repair_feedback", "602413b3bcd84b4656218c3a9a27dd4157466674b3221989b5862003c837df26",
        ["schema_version", "record_type", "feedback_id", "project_id", "run_id", "job_id", "pass_id", "attempt_id", "created_at", "consumer", "authentication", "trust_binding", "canonicalization", "parent_receipt_binding", "release_binding", "policy_binding", "certificate_binding", "source_binding", "media_scope_sha256", "subject_binding", "provider_binding", "output_artifact_bindings", "protected_artifact_bindings", "transform_binding", "qa_binding", "authority_binding", "defects", "hypothesis", "requested_action", "retry_budget", "progress_guard", "immutable_accepted_parent", "advisory_only", "consumer_may_mutate_gold", "consumer_may_escalate_authority", "feedback_payload_sha256", "signature"],
    ),
    "mask_bridge_event": frozen_producer_schema_binding(
        "mask_bridge_event", "d1d707b460bfcb273c8e6929d1811d04b3eacf346f2c20dc9e46ecef81aa4407",
        ["schema_version", "record_type", "event_id", "sequence", "stream_id", "occurred_at", "evidence_context", "fixture_only", "canonicalization", "trust_binding", "journal_epoch", "event_type", "producer", "correlation_id", "causation_id", "subject", "state_transition", "payload_schema", "payload_sha256", "previous_event_sha256", "event_payload_sha256", "signature"],
    ),
    "mask_bridge_semantic_invariant_profile": frozen_producer_schema_binding(
        "mask_bridge_semantic_invariant_profile", "0cd46afbdf7a2fdc07f4e693bd83e47f14683bb8778e10802f054e5640253bf4",
        ["schema_version", "record_type", "profile_id", "profile_version", "status", "canonicalization", "canonicalization_spec_sha256", "required_validation_layers", "authority_rank", "certificate_kind_crosswalk", "invariants", "conformance_fixture_index", "profile_sha256"],
    ),
}

PARENT_ITEMS = ["ITEM-W64-177", "ITEM-W64-178", "ITEM-W64-179", "ITEM-W64-180"]

WORKSTREAMS = [
    ("MFB-01", "release_snapshot_and_pinning", "Publish, verify, pin, and invalidate immutable MaskFactory integration releases."),
    ("MFB-02", "adapter_dual_mode_contract", "Implement strict request/result ports for package and live-service access without authority inference."),
    ("MFB-03", "authority_certificate_promotion", "Verify the frozen authority crosswalk, operational certificates, promotion gates, and revocation."),
    ("MFB-04", "ownership_transform_derivation_repair", "Preserve multi-character ownership, geometry, derived-mask lineage, protected regions, and bounded repair."),
    ("MFB-05", "resilience_cache_event_recovery", "Provide health, idempotency, circuit breaking, cache invalidation, event replay, and recovery."),
    ("MFB-06", "cross_repository_session_handshake", "Exchange consumer requirements, adoption receipts, compatibility evidence, and non-mutating feedback."),
    ("MFB-07", "assurance_app_vertical_release", "Prove contracts, faults, observability, App projections, integrated execution, and core release."),
]

ROW_SPECS: list[list[tuple[str, str, str, str, list[str]]]] = [
    [
        ("contract", "MaskFactory Immutable Integration Release Snapshot", "Define the v2 producer snapshot binding clean source, exact wire contracts, canonical encoding/domain separation, API, package, ontology, node pack, wheel, capabilities, certificates, revocation index, signed journal bootstrap/checkpoint, and artifacts by hash.", "A canonical trust-anchored snapshot rejects mutable worktree authority, embedded/self-signed key substitution, missing hashes, unmanifested artifacts, archive/path escape, and ambiguous contract identity.", []),
        ("implementation", "Main Exact Release Pin and Integrity Verifier", "Implement isolated import, safe archive extraction, content hashing, out-of-band trusted-key verification, canonical payload/signature verification, clean-source verification, atomic pinning, checkpoint validation, and rollback metadata.", "Only a fully verified named release signed by an allowed active key and bound to the current revocation index/journal head can become the active Main producer pin; prior non-revoked pins remain recoverable.", ["maskfactory_release_snapshot_available"]),
        ("validation", "Schema Source Version Hash and Semantic Drift Gate", "Compare schema source, schema ID, semantic version, content hash, required fields, semantic invariants, executable field mapping, API/OpenAPI, package, ontology, node-pack, wheel, certificate format, canonicalization profile, and journal format.", "Same-name, semver-compatible-but-hash-different, required-field, enum, or invariant drift fails closed with a typed blocker before normalization or execution.", []),
        ("release", "Release Supersession Revocation and Adoption Boundary", "Process supersession, signing-key state, certificate validity, revocation-index freshness, and per-scope invalidation before authorizing a new pin; retain immutable signed adoption and checkpoint evidence.", "A revoked, expired, superseded, forked, or invalidated scope cannot be resurrected by cache, rollback, restart, timestamp manipulation, embedded keys, or journal resealing.", []),
    ],
    [
        ("contract", "Strict v2 Bridge Request Compiler", "Compile project/run/job/pass/attempt/hypothesis, idempotency/nonce, exact still-frame-or-span media scope, source, declared scene roster, one target, protected character/prop/environment regions, separate input ROI hashes, intent, executable transform, compatibility, accepted claim class, resource/deadline, authority, and policy fields from immutable pass records.", "Unknown fields, replayed authorization, target/protected ambiguity, output-as-input collisions, and invented references fail; access mode remains independent from minimum authority and accepted issuers.", []),
        ("implementation", "Mode A Read-Only Package Adapter", "Resolve packages only through the active pin and verify artifact, source, owner, ontology, transform, authority, and certificate bindings.", "Mode A never implies certified and Main performs no producer mutation.", ["adopted_maskfactory_release_with_mode_a_capability"]),
        ("implementation", "Mode B Live Predict and Refine Adapter", "Implement authenticated health, bounded nonce/deadline/idempotency admission, explicit admitted/submitted/accepted/running/succeeded/failed/cancelled/outcome_unknown lifecycle, predict/refine, reconciliation before resubmission, response validation, route/runtime lineage, and typed failure behavior.", "Mode B defaults to draft; a network ambiguity becomes outcome_unknown, never an assumed failure or success, and one result may be stronger only through an active exact serving-route/output operational certificate.", ["compatible_maskfactory_service_or_synthetic_fixture"]),
        ("validation", "Normalized Result and Deterministic Arbitration", "Normalize both modes while retaining exact input ROI versus generated-output identity, source/media scope, package/service, route and eligible alternatives, runtime kind/digest, timing/resources, hypothesis, owner, transform, authority/claim class, certificate, QA, cache, and blocker lineage.", "Normalization records factual execution without granting authority; a newer draft cannot overwrite stronger valid authority, close candidates branch only within budget, and ambiguity abstains.", []),
    ],
    [
        ("contract", "Frozen Authority Issuer Claim-Class and Legacy Migration Crosswalk", "Implement exact authority_state, issuer_kind, and claim_class vocabulary with access-mode-independent intended-use policy; migrate the legacy live QA strictness dial/string promotion gates to pinned structured v2 policy.", "Unknown values fail; operationally_certified_artifact can support only its exact permitted use and never becomes independent accuracy or training gold; legacy/UI/LLM summaries are non-authoritative.", []),
        ("implementation", "Exact Trust-Anchored Operational Certificate Verifier", "Verify out-of-band trusted signer, signature algorithm, release, capability, access mode, exact execution stack/runtime provenance, source media/frame/output, owner, transform, QA, policy, scope, issuer, issuance/expiry at decision time, and current revocation index.", "Neither Mode A nor Mode B receives authority outside the exact active certificate scope, and embedded/self-signed keys or fixture evidence cannot establish production trust.", ["certificate_trust_root_or_synthetic_fixture"]),
        ("validation", "Structured Mask Authority and Downstream Promotion Gate", "Recompute use eligibility from the exact signed pinned Main policy using a complete unique criterion vector, declared comparator/threshold, analyzer and evidence hashes, claim class, signer trust, decision timestamp, certificate temporal evaluation, current revocation index, and genuine runtime evidence.", "Producer use_eligibility, QA success, certificate presence, or LLM/VLM opinion is never sufficient by itself; every exact policy criterion and Main QA must pass without blockers.", []),
        ("release", "Certificate Revocation Demotion and Per-Target Invalidation", "Apply signer revocation, certificate expiry/revocation, regression, per-target scope/hash drift, media-frame drift, and policy/revocation-index change as durable signed invalidations and re-evaluate dependents.", "Only affected target masks/caches/dependents fail closed while unrelated targets and DAG branches continue; tombstoned authority cannot resurrect.", []),
    ],
    [
        ("contract", "Multi-Entity Scene Roster Owner and Provider Index Binding", "Bind the exact target character plus every visible/protected character, prop, and environment instance to the declared scene roster, provider indices where applicable, references, visibility, occlusion, target masks, and protected input regions.", "Duplicate, swapped, absent, cross-character, prop, environment, or ambiguous assignments block the affected pass and cannot be promotion-authoritative.", []),
        ("implementation", "Executable Coordinate Transform and Roundtrip Validator", "Record and execute typed ordered crop, resize, pad, flip, projection, inverse, interpolation, rounding, source/output dimensions, character-perspective side swaps, per-step hashes, canonical chain hash, and tolerance.", "Step continuity, sentinel points, bounds, and masks roundtrip within policy; non-invertible operations, wrong side labels, or image/mask transform divergence fail.", []),
        ("validation", "Target Protected Input and Derived Output Lineage Gate", "Keep input ROI/protected constraint artifacts distinct from generated masks, validate ownership/overlap, and record boolean, morphological, feather, crop, and projection derivations with exact parent hashes and parent authority records.", "Only an exact Mode A package selector may intentionally reference the same immutable package mask; protected-region policy is explicit and each derived output is capped at the weakest parent authority/claim scope.", []),
        ("release", "Disagreement Arbitration and Localized Mask Repair", "Localize provider disagreement, preserve accepted parents, require a new hypothesis, and bound candidate, attempt, time, and compute budgets.", "Repair changes only the failed scope and passes regional plus whole-artifact regression or abstains.", []),
    ],
    [
        ("contract", "Health Capability Route and Runtime Snapshot", "Publish freshness-bound service, authenticated endpoint, model-route, authority ceiling, native/venv or container runtime provenance, resource envelope, and compatibility observations.", "Stale health never authorizes execution, container routes require image digests, native/venv routes require environment/lock hashes, and current Mode B default authority is draft.", []),
        ("implementation", "Lifecycle Idempotency Retry Deadline and Circuit Breaker", "Separate transport retry from quality repair, bind retries to request payload/idempotency/nonce/deadline, persist explicit execution state transitions, and reconcile outcome_unknown before resubmission.", "Confirmed effects are not duplicated, impossible/backward transitions fail, quality retries require a new hypothesis, and breakers are exact-route scoped and deadline bounded.", []),
        ("validation", "Content-Addressed Cache and Per-Scope Invalidation Tombstones", "Key cache by release/contracts/source/media/owner/input regions/intent/transform/route/runtime/model/authority/claim/policy and persist signed per-target invalidation tombstones.", "Stale, revoked, wrong-frame, or wrong-owner entries cannot resurrect after restart; forensic retention and fixture entries cannot satisfy active production routes.", []),
        ("release", "Signed Append-Only Bridge Event Journal Checkpoints and Recovery", "Persist canonical domain-separated admitted, submitted, accepted, running, outcome_unknown, received, validated, authority, cache, invalidation, repair, incident, and promotion-decision events with causation, previous hashes, signed bootstrap/checkpoints, and trusted head pins.", "Replay verifies sequence/hash/signature/checkpoint continuity, rejects fork/deletion/reorder/reseal/substituted-key history, reconstructs projections, and resumes only safe work without repeating confirmed external effects.", []),
    ],
    [
        ("contract", "Main Consumer Requirements and Trust Manifest", "Declare exact wire schema name/version/hash, canonicalization/domain profile, trusted-key registry and allowed key IDs/algorithms, auth/nonce/replay policy, API/package/ontology compatibility, labels, person counts, transforms, media scope, access modes, issuer/certificate/claim scope, runtime provenance, latency/resources, and completion profile.", "Core requirements explicitly set human anchors and scale/DAZ maturity as optional; embedded keys, conversational memory, and producer use_eligibility have no Main authority.", []),
        ("implementation", "Producer Consumer Adoption Receipt", "Record adopted, partially adopted, or rejected status with exact pin, signed trust result, current revocation index, journal checkpoint/head pin, checks, mismatches, capability scope, and revalidation triggers.", "Partial adoption authorizes only enumerated diagnostic/shadow capabilities and never broad production use; every required signature must resolve to an active out-of-band trusted key.", ["maskfactory_release_snapshot_available"]),
        ("validation", "Bidirectional Compatibility Contract and Adversarial CI", "Run producer fixtures and Main positive/negative/adversarial fixtures against the same immutable release and consumer manifest, including canonicalization, signer substitution, nonce replay, path/archive safety, media/ownership/transform drift, certificate time/revocation, journal forks, and mapping completeness.", "Any schema, semantic, trust, ontology, route, authority, lifecycle, or certificate drift fails before runtime activation.", []),
        ("release", "Typed Feedback Repair Request Without Truth Mutation", "Return source/result hashes, localized defect, QA evidence, and requested producer action through an append-only request.", "Main requests no gold mutation or authority change; producer response appears only through its own later event/release.", []),
    ],
    [
        ("contract", "Strict v2 Fixture Semantic Security and Legacy Migration Validator Suite", "Validate every schema/example, canonical/security invariant, executable producer mapping, trust anchor, signature/time/revocation rule, journal/state-machine rule, dependency, ownership/media/transform/lineage rule, authority/claim rule, structured promotion criterion, legacy migration, completion profile, mirror, and preservation hash.", "Positive and adversarial fixtures prove Mode A/Mode B authority independence, exact-certificate live eligibility, fixture/runtime separation, and rejection of embedded-key, producer eligibility, conversational summary, live QA-dial, or string-only promotion authority.", []),
        ("implementation", "Bridge Observability Incident and App Projection", "Implement the explicit read-model map for Home/readiness, Projects/revisions, Scene Builder Pose & Masks, Runs/DAG, Queue/Workers, Recovery, and QA, including the strict readiness-projection v2 contract.", "Every named page consumes only its registered read models and evidence lineage; Browser, App Mode, LLM, and VLM cannot bypass the adapter, mutate producer truth, commit promotion, or infer runtime readiness from fixtures.", []),
        ("validation", "Single and Multi-Character Integrated Bridge Proof", "Run single-person Mode A, two-person plus prop/environment ownership/protection, still/frame/span scope, Mode B draft and exact certified output, outage/outcome_unknown reconciliation, per-target invalidation, signed-journal restart, and downstream edit proofs.", "Every core gate produces trust- and hash-bound genuine runtime evidence; wrong-owner/frame/key/revocation/transform injections fail closed, unrelated branches continue, and an injected child failure preserves its accepted parent.", ["runtime_maskfactory_release_and_main_adapter_available"]),
        ("release", "Core Autonomous MaskFactory Bridge Release", "Issue the core_autonomous_runtime bridge release only after Rows321-347 and the existing Character-to-Image vertical slice pass.", "Row218 and every core bridge gate pass; optional independent accuracy and scale/DAZ maturity are reported separately and do not block core.", ["ITEM-W64-218_runtime_evidence"]),
    ],
]

DOC_PATHS = [
    "Plan/00_PROJECT_CONTROL/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_AND_RELEASE_HANDSHAKE_MASTER_PLAN.md",
    "Plan/01_CURRENT_SYSTEM_REVIEW/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_GAP_AUDIT.md",
    "Plan/02_TARGET_ARCHITECTURE/ADR_WAVE64_MASKFACTORY_IMMUTABLE_RELEASE_AND_DUAL_MODE_ADAPTER.md",
    "Plan/02_TARGET_ARCHITECTURE/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ARCHITECTURE.md",
    "Plan/Instructions/WAVE64_MASKFACTORY_BRIDGE_IMPLEMENTATION_AND_OPERATION_PROTOCOL.md",
    "Plan/Instructions/QA/WAVE64_MASKFACTORY_BRIDGE_QA_AND_PROMOTION_PROTOCOL.md",
    "Plan/Instructions/Hydration_Rehydration/MASKFACTORY_AUTONOMOUS_BRIDGE_MAIN_SESSION_HANDOFF.md",
]

STATIC_SOURCES = [
    ".gitattributes",
    *DOC_PATHS,
    "Plan/07_IMPLEMENTATION/scripts/build_wave64_maskfactory_autonomous_bridge_package.py",
    "Plan/07_IMPLEMENTATION/scripts/validate_wave64_maskfactory_autonomous_bridge_package.py",
    "Plan/Instructions/QA/Scripts/test_wave64_maskfactory_autonomous_bridge_package.py",
    "Plan/00_PROJECT_CONTROL/WAVE64_ULTIMATE_MODULAR_CHARACTER_TO_MULTIMODAL_WORKFLOW_MASTER_PLAN.md",
    "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md",
    "Plan/08_SCHEMAS/mask_factory_contract.schema.json",
    "Plan/Items/README.md",
    "Plan/Items/Waves/Wave64/README.md",
    "Plan/Tracker/README.md",
    "Plan/Tracker/Waves/Wave64/README.md",
    "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md",
    "Plan/Instructions/COMPLETION_DEFINITION_AND_DONE_GATE.md",
    "Plan/Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md",
    "Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md",
    "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md",
    "Plan/Instructions/Hydration_Rehydration/BLOCKERS.md",
    "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
    "Plan/Instructions/Hydration_Rehydration/RECENT_DECISIONS.md",
    "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
    "Plan/Instructions/Hydration_Rehydration/KNOWN_ISSUES.md",
    "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
    "Plan/README.md",
    "Plan/PROJECT_MANIFEST.json",
    "Plan/03_IMAGE_SYSTEM/MASK_FACTORY_SPEC.md",
    "Plan/03_IMAGE_SYSTEM/IMAGE_PIPELINE_BLUEPRINT.md",
    "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md",
    "Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md",
    "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json",
]


def h(character: str) -> str:
    return character * 64


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def strict_json_loads(raw: bytes | str) -> Any:
    """Decode authority-bearing JSON without duplicate, Unicode-collision, or non-finite ambiguity."""
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("authority-bearing JSON is not strict UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise TypeError("strict JSON input must be bytes or text")

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON number is forbidden: {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("non-finite JSON number is forbidden")
        return parsed

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        normalized_keys: dict[str, str] = {}
        for key, value in pairs:
            normalized = unicodedata.normalize("NFC", key)
            if normalized in normalized_keys:
                previous = normalized_keys[normalized]
                kind = "duplicate" if previous == key else "Unicode NFC-colliding"
                raise ValueError(f"{kind} JSON object key is forbidden: {key!r}")
            normalized_keys[normalized] = key
            result[key] = value
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("authority-bearing JSON failed strict decoding") from exc


def _maskfactory_canonical_number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("MaskFactory canonical JSON rejects non-finite numbers")
    if value == 0:
        return "0"
    encoded = repr(value).lower()
    if "e" in encoded:
        mantissa, exponent = encoded.split("e", 1)
        sign = ""
        if exponent.startswith(("+", "-")):
            sign, exponent = exponent[0], exponent[1:]
        exponent = exponent.lstrip("0") or "0"
        if sign == "+":
            sign = ""
        encoded = f"{mantissa}e{sign}{exponent}"
    return encoded


def _maskfactory_canonical_json_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _maskfactory_canonical_number(value)
    if isinstance(value, str):
        return json.dumps(unicodedata.normalize("NFC", value), ensure_ascii=False, allow_nan=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_maskfactory_canonical_json_text(item) for item in value) + "]"
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise TypeError("MaskFactory canonical JSON requires string object keys")
            key = unicodedata.normalize("NFC", raw_key)
            if key in normalized:
                raise ValueError("MaskFactory canonical JSON rejects NFC-colliding keys")
            normalized[key] = item
        return "{" + ",".join(
            _maskfactory_canonical_json_text(key) + ":" + _maskfactory_canonical_json_text(normalized[key])
            for key in sorted(normalized)
        ) + "}"
    raise TypeError(f"unsupported MaskFactory canonical JSON value: {type(value).__name__}")


def maskfactory_canonical_json_bytes(value: Any) -> bytes:
    return _maskfactory_canonical_json_text(value).encode("utf-8")


def maskfactory_document_sha256(document: dict[str, Any], *, excluded: tuple[str, ...]) -> str:
    payload = {key: value for key, value in document.items() if key not in set(excluded)}
    return sha256_bytes(maskfactory_canonical_json_bytes(payload))


def validate_frozen_producer_document(
    document: dict[str, Any], contract_name: str,
    runtime_verification_context: dict[str, Any] | None,
) -> None:
    if runtime_verification_context is None:
        raise ValueError("producer wire validation requires the adopted frozen schema bytes")
    raw_schema = runtime_verification_context.get("producer_wire_schema_bytes", {}).get(contract_name)
    binding = PRODUCER_SCHEMA_BINDINGS[contract_name]
    if not isinstance(raw_schema, bytes) or sha256_bytes(raw_schema) != binding["schema_sha256"]:
        raise ValueError("producer wire schema bytes do not match the exact frozen schema binding")
    schema = strict_json_loads(raw_schema)
    if schema.get("$id") != binding["schema_id"]:
        raise ValueError("producer wire schema identity differs from the exact frozen binding")
    try:
        import jsonschema
        errors = list(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(document))
    except Exception as exc:
        raise ValueError("producer wire schema validation could not be completed") from exc
    if errors:
        pointer = "/" + "/".join(str(value) for value in errors[0].absolute_path)
        raise ValueError(f"producer wire document violates the exact frozen schema at {pointer}")


def validate_outbound_maskfactory_signed_document(
    document: dict[str, Any], contract_name: str, payload_hash_field: str,
    expected_producer_key_role: str, expected_main_signer_role: str,
    signature_trust: dict[str, Any], trusted_keys: dict[str, Any],
    runtime_verification_context: dict[str, Any], *, use_time: str,
) -> None:
    """Validate a compiled Main→MaskFactory wire document before it can leave Main."""
    validate_frozen_producer_document(document, contract_name, runtime_verification_context)
    canonicalization = document.get("canonicalization")
    excluded = [payload_hash_field, "signature"]
    if canonicalization != {"algorithm": "maskfactory-canonical-json-v1", "excluded_top_level_fields": excluded}:
        raise ValueError("outbound producer document canonicalization profile is not exact")
    digest = maskfactory_document_sha256(document, excluded=tuple(excluded))
    signature = document.get("signature")
    trust_binding = document.get("trust_binding")
    if (
        document.get(payload_hash_field) != digest
        or not isinstance(signature, dict)
        or signature.get("algorithm") != "ed25519"
        or signature.get("signed_payload_sha256") != digest
        or signature.get("signed_payload_format") != "sha256_digest_bytes"
        or not isinstance(trust_binding, dict)
        or trust_binding.get("key_role") != expected_producer_key_role
        or signature.get("key_id") != trust_binding.get("signing_key_id")
        or signature.get("key_id") != signature_trust.get("signing_key_id")
    ):
        raise ValueError("outbound producer document hash, signature, or key-role binding differs from the compiled payload")
    try:
        embedded_key = base64.b64decode(signature["public_key_base64"], validate=True)
    except (ValueError, binascii.Error, KeyError, TypeError) as exc:
        raise ValueError("outbound producer document embeds an invalid public key") from exc
    embedded_sha256 = sha256_bytes(embedded_key)
    if (
        trust_binding.get("signing_public_key_sha256") != embedded_sha256
        or signature_trust.get("embedded_public_key_sha256") != embedded_sha256
    ):
        raise ValueError("outbound producer document public key differs from the out-of-band Main trust binding")
    verify_ed25519_runtime_signature(
        digest, signature["value_base64"], "maskfactory.sha256_digest_bytes.v1",
        signature_trust, trusted_keys, runtime_verification_context,
        expected_signer_role=expected_main_signer_role, use_time=use_time,
        signature_message_format="digest_bytes",
    )


def resolve_adopted_capability_snapshot(
    release_binding: dict[str, Any], runtime_verification_context: dict[str, Any] | None,
) -> dict[str, Any]:
    if runtime_verification_context is None or not isinstance(runtime_verification_context.get("adopted_capability_snapshot_ref"), dict):
        raise ValueError("production projection requires the exact capability snapshot bound by the signed adopted release")
    snapshot_ref = runtime_verification_context["adopted_capability_snapshot_ref"]
    raw_bytes = resolve_verified_artifact_bytes(snapshot_ref, runtime_verification_context)
    snapshot = strict_json_loads(raw_bytes)
    if not isinstance(snapshot, dict):
        raise ValueError("adopted capability snapshot is not a JSON object")
    validate_frozen_producer_document(snapshot, "maskfactory_capability_snapshot", runtime_verification_context)
    payload_sha256 = maskfactory_document_sha256(snapshot, excluded=("snapshot_sha256",))
    adopted_release = runtime_verification_context.get("adopted_producer_release_binding")
    if (
        snapshot_ref["record_type"] != snapshot.get("record_type")
        or snapshot_ref["record_id"] != snapshot.get("snapshot_id")
        or snapshot.get("snapshot_sha256") != payload_sha256
        or release_binding.get("capability_snapshot_id") != snapshot.get("snapshot_id")
        or release_binding.get("capability_snapshot_sha256") != payload_sha256
        or not isinstance(adopted_release, dict)
        or adopted_release.get("capability_snapshot_document_sha256") != snapshot_ref["sha256"]
    ):
        raise ValueError("capability snapshot identity/hash is not the exact document bound by the signed adopted release")
    return snapshot


def exact_certificate_scope_projection(raw: dict[str, Any]) -> list[str]:
    qualified = raw["qualified_route_scope"]
    output = raw["certified_output_scope"]
    values = {
        f"qualified_scope:{qualified['scope_sha256']}",
        f"output_scope:{output['scope_sha256']}",
        *{f"label:{value}" for value in output["labels"]},
        *{f"artifact_kind:{value}" for value in output["artifact_kinds"]},
        *{f"owner:{value}" for value in output["owners"]},
        *{f"coordinate_space:{value}" for value in output["coordinate_spaces"]},
        *{f"permitted_use:{value}" for value in output["permitted_uses"]},
    }
    return sorted(values)


PRODUCER_TO_MAIN_COORDINATE_SPACE = {
    "source_pixel": "source_pixels",
    "crop_pixel": "working_pixels",
    "output_pixel": "frame_pixels",
    "normalized_0_1": "normalized_0_1",
}


def _normalized_color_space(value: str) -> str:
    return {"sRGB": "srgb", "linear_sRGB": "linear_srgb"}.get(value, value.lower())


def _ref_hashes(values: list[dict[str, Any]]) -> set[str]:
    return {value["sha256"] for value in values}


def _assert_equal_projection(name: str, expected: Any, observed: Any) -> None:
    if expected != observed:
        raise ValueError(f"raw producer {name} does not equal the deterministic Main normalization projection")


def _normalized_certificate_ref_for_raw(
    certificate_id: str | None,
    raw_certificate_sha256: str | None,
    runtime_verification_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if certificate_id is None or raw_certificate_sha256 is None:
        if certificate_id is not None or raw_certificate_sha256 is not None:
            raise ValueError("raw producer certificate identity is only partially populated")
        return None
    mapping = {} if runtime_verification_context is None else runtime_verification_context.get("raw_to_main_certificate_refs", {})
    normalized_ref = mapping.get(raw_certificate_sha256) if isinstance(mapping, dict) else None
    if (
        not isinstance(normalized_ref, dict)
        or normalized_ref.get("record_type") != "maskfactory_operational_certificate_v2"
        or normalized_ref.get("record_id") != certificate_id
    ):
        raise ValueError("raw producer certificate is not bound to its exact normalized Main certificate")
    return normalized_ref


def validate_raw_release_projection(
    raw: dict[str, Any], release: dict[str, Any], runtime_verification_context: dict[str, Any] | None,
) -> None:
    """Cross-bind every release fact that can affect identity, compatibility, or authority."""
    _assert_equal_projection("release identity", raw["release_id"], release["release_id"])
    _assert_equal_projection("release status", raw["release_status"], release["release_status"])
    _assert_equal_projection("release publication time", raw["published_at"], release["published_at"])
    _assert_equal_projection("release fixture context", raw["fixture_only"], release["fixture_only"])
    expected_context = "fixture_validation" if raw["fixture_only"] else "production_runtime"
    _assert_equal_projection("release evidence context", expected_context, release["release_context"])
    producer = raw["producer"]
    _assert_equal_projection(
        "release producer source",
        {
            "repository_id": producer["repository_id"],
            "commit_sha": producer["git_commit"],
            "source_clean": not producer["dirty"],
        },
        {key: release["producer_source"][key] for key in ("repository_id", "commit_sha", "source_clean")},
    )
    expected_contracts = {
        (value["name"], value["version"], value["schema_id"], value["sha256"])
        for value in raw["wire_schemas"]
    }
    observed_contracts = {
        (value["wire_schema_name"], value["schema_version"], value["schema_id"], value["schema_sha256"])
        for value in release["contract_bindings"]
    }
    _assert_equal_projection("release wire-schema set", expected_contracts, observed_contracts)
    _assert_equal_projection(
        "release completion-profile set",
        {value["profile_id"] for value in raw["completion_profiles"]},
        set(release["completion_profiles"]),
    )
    capability = raw["capability_snapshot"]
    _assert_equal_projection("release capability ref set", {capability["payload_sha256"]}, _ref_hashes(release["capability_refs"]))
    expected_artifact_hashes = {value["sha256"] for value in raw["artifacts"]} | {raw["evidence_index"]["sha256"]}
    _assert_equal_projection("release artifact/evidence ref set", expected_artifact_hashes, _ref_hashes(release["artifact_refs"]))
    expected_certificate_hashes = {raw["certificate_index"]["sha256"], raw["certificate_index"]["revocation_index_sha256"]}
    _assert_equal_projection("release certificate/revocation index ref set", expected_certificate_hashes, _ref_hashes(release["certificate_refs"]))
    release_ids_requiring_resolution = set(raw["revoked_release_ids"])
    if raw["supersedes_release_id"] is not None:
        release_ids_requiring_resolution.add(raw["supersedes_release_id"])
    resolver = {} if runtime_verification_context is None else runtime_verification_context.get("producer_release_revocation_refs", {})
    if not isinstance(resolver, dict) or set(resolver) != release_ids_requiring_resolution:
        raise ValueError("release revocation/supersession IDs are not exactly resolved through the signed producer journal")
    expected_revocation_refs = {immutable_ref_key(value) for value in resolver.values()}
    observed_revocation_refs = {immutable_ref_key(value) for value in release["revocation_refs"]}
    _assert_equal_projection("release resolved revocation ref set", expected_revocation_refs, observed_revocation_refs)
    for value in resolver.values():
        resolve_verified_artifact_bytes(value, runtime_verification_context)
    semantic = raw["semantic_invariant_profile"]
    if semantic["document_sha256"] != "0292d3714a2ddfe74ef59dceee98630b48f9400f50ef2b07dcbbe123d36d3a67":
        raise ValueError("raw producer release does not bind the exact frozen semantic-invariant profile document")
    signing = raw["signing_trust"]
    checkpoint = raw["journal_checkpoint"]
    artifacts_by_kind = {value["kind"]: value for value in raw["artifacts"]}
    compatibility = raw["compatibility"]
    expected_components = {
        ("api_openapi", raw["openapi"]["version"], raw["openapi"]["sha256"]),
        ("compatibility_manifest", compatibility["bridge_contract"], artifacts_by_kind["compatibility_manifest"]["sha256"]),
        ("package_format", compatibility["package_format"], artifacts_by_kind["compatibility_manifest"]["sha256"]),
        ("ontology", compatibility["ontology_version"], artifacts_by_kind["compatibility_manifest"]["sha256"]),
        ("node_pack", compatibility["node_pack_version"], artifacts_by_kind["comfyui_node_pack"]["sha256"]),
        ("workflow_inventory", raw["workflow_inventory"]["inventory_id"], raw["workflow_inventory"]["sha256"]),
        ("node_inventory", raw["node_inventory"]["inventory_id"], raw["node_inventory"]["sha256"]),
        ("install_manifest", "sha256", raw["installation"]["install_manifest_sha256"]),
        ("installer", raw["installation"]["installer_id"], raw["installation"]["installer_sha256"]),
        ("installation_verification", raw["installation"]["verification_workflow_id"], raw["installation"]["verification_workflow_sha256"]),
        ("rollback", raw["rollback"]["rollback_id"], raw["rollback"]["rollback_sha256"]),
        ("rollback_verification", raw["rollback"]["target_release_id"], raw["rollback"]["verification_evidence_sha256"]),
        ("semantic_profile", semantic["record_id"], semantic["profile_sha256"]),
        ("semantic_profile_document", "1.0.0", semantic["document_sha256"]),
        ("capability_snapshot_document", capability["record_id"], capability["document_sha256"]),
        ("signing_key_set", signing["key_set_version"], signing["key_set_sha256"]),
        ("rotation_policy", signing["rotation_policy_id"], signing["rotation_policy_sha256"]),
        ("revocation_policy", signing["revocation_policy_id"], signing["revocation_policy_sha256"]),
        ("journal_head", checkpoint["stream_id"], checkpoint["head_event_sha256"]),
        ("journal_revocation_state", str(checkpoint["last_sequence"]), checkpoint["revocation_state_sha256"]),
        ("journal_validator", str(checkpoint["event_count"]), checkpoint["validator_sha256"]),
    }
    observed_components = {(value["component"], value["version"], value["sha256"]) for value in release["component_bindings"]}
    _assert_equal_projection("release component/trust/journal binding set", expected_components, observed_components)


def _expected_main_media_scope(raw_scope: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    frame_span = raw_scope["frame_span"]
    return {
        "media_kind": {"still_image": "still_image", "video_frame": "video_frame", "frame_span": "frame_span"}[raw_scope["scope_kind"]],
        "source_media_sha256": raw_scope["source_video_sha256"] or source_sha256,
        "frame_index": raw_scope["frame_index"],
        "pts_ticks": raw_scope["pts"],
        "timebase_numerator": raw_scope["timebase_numerator"],
        "timebase_denominator": raw_scope["timebase_denominator"],
        "span_start_frame": None if frame_span is None else frame_span["start_frame"],
        "span_end_frame": None if frame_span is None else frame_span["end_frame"],
        "exact_frame_scope_only": True,
    }


def _observed_main_media_scope(scope: dict[str, Any]) -> dict[str, Any]:
    return {
        key: scope[key]
        for key in (
            "media_kind", "source_media_sha256", "frame_index", "pts_ticks", "timebase_numerator",
            "timebase_denominator", "span_start_frame", "span_end_frame", "exact_frame_scope_only",
        )
    }


def validate_raw_receipt_projection(
    raw: dict[str, Any], result: dict[str, Any], runtime_verification_context: dict[str, Any] | None,
) -> None:
    """Prove that the signed producer receipt and normalized result describe the same run and artifacts."""
    _assert_equal_projection(
        "receipt request identity",
        (raw["request_id"], raw["request_payload_sha256"]),
        (result["request_ref"]["record_id"], result["request_ref"]["sha256"]),
    )
    _assert_equal_projection("receipt access mode", raw["access_mode"], result["access_mode"])
    _assert_equal_projection("receipt result status", {"succeeded": "succeeded", "blocked": "blocked", "failed": "error"}[raw["result"]], result["status"])
    if runtime_verification_context is None:
        raise ValueError("receipt projection requires the signed adopted release binding")
    release_binding = raw["release_binding"]
    adopted_producer_release = runtime_verification_context.get("adopted_producer_release_binding")
    _assert_equal_projection(
        "receipt adopted producer release",
        (
            release_binding["release_id"], release_binding["release_payload_sha256"], release_binding["capability_snapshot_id"], release_binding["capability_snapshot_sha256"],
            release_binding["bridge_contract"], release_binding["wire_schema_name"], release_binding["wire_schema_version"], release_binding["wire_schema_sha256"],
        ),
        None if not isinstance(adopted_producer_release, dict) else (
            adopted_producer_release.get("release_id"), adopted_producer_release.get("release_payload_sha256"),
            adopted_producer_release.get("capability_snapshot_id"), adopted_producer_release.get("capability_snapshot_sha256"),
            adopted_producer_release.get("bridge_contract"), "mask_acquisition_receipt",
            PRODUCER_SCHEMA_BINDINGS["mask_acquisition_receipt"]["schema_version"], PRODUCER_SCHEMA_BINDINGS["mask_acquisition_receipt"]["schema_sha256"],
        ),
    )
    _assert_equal_projection("receipt adopted Main release", runtime_verification_context.get("adopted_main_release_ref"), result["release_snapshot_ref"])
    source = raw["source_binding"]
    _assert_equal_projection(
        "receipt source identity",
        {
            "sha256": source["encoded_sha256"], "width": source["width"], "height": source["height"],
            "color_space": _normalized_color_space(source["color_space"]),
            "coordinate_space": PRODUCER_TO_MAIN_COORDINATE_SPACE[source["coordinate_space"]],
        },
        {key: result["source_artifact"][key] for key in ("sha256", "width", "height", "color_space", "coordinate_space")},
    )
    _assert_equal_projection("receipt media scope", _expected_main_media_scope(raw["media_scope"], source["encoded_sha256"]), _observed_main_media_scope(result["media_scope"]))
    route = raw["execution_observation"]["route_selection"]
    _assert_equal_projection("receipt selected route", route["selected_route_id"], result["route_id"])
    provider = raw["provider_binding"]
    if provider is not None:
        _assert_equal_projection(
            "receipt execution stack",
            (provider["stack_id"], provider["stack_sha256"]),
            (result["execution_stack_ref"]["record_id"], result["execution_stack_ref"]["sha256"]),
        )
        capability_snapshot = resolve_adopted_capability_snapshot(release_binding, runtime_verification_context)
        stack_matches = [
            value for value in capability_snapshot["provider_stacks"]
            if value["stack_id"] == provider["stack_id"] and value["stack_sha256"] == provider["stack_sha256"]
        ]
        if len(stack_matches) != 1:
            raise ValueError("receipt provider stack is not uniquely present in the signed adopted capability snapshot")
        stack = stack_matches[0]
        if raw["access_mode"] not in stack["access_modes"] or route["selected_route_id"] != stack["route_key"]["route_key_id"]:
            raise ValueError("receipt route/access mode is not authorized by the signed adopted capability snapshot")
    subject = raw["subject_binding"]
    expected_owner = (subject["scene_instance_id"], subject["provider_person_index"], subject["assignment_evidence_sha256"])
    observed_owners = {
        (value["character_instance_id"], value["provider_person_index"], value["assignment_evidence_refs"][0]["sha256"])
        for value in result["owner_bindings"]
    }
    _assert_equal_projection("receipt subject/owner identity", {expected_owner}, observed_owners)
    transform = raw["transform_validation"]
    _assert_equal_projection(
        "receipt transform identity and dimensions",
        (
            transform["transform_chain_id"], transform["transform_chain_sha256"],
            PRODUCER_TO_MAIN_COORDINATE_SPACE[transform["source_coordinate_space"]], transform["source_width"], transform["source_height"],
            PRODUCER_TO_MAIN_COORDINATE_SPACE[transform["output_coordinate_space"]], transform["output_width"], transform["output_height"],
            transform["maximum_roundtrip_error_px"],
        ),
        (
            result["transform_chain"]["chain_id"], result["transform_chain"]["chain_sha256"],
            result["transform_chain"]["source"]["coordinate_space"], result["transform_chain"]["source"]["width"], result["transform_chain"]["source"]["height"],
            result["transform_chain"]["output"]["coordinate_space"], result["transform_chain"]["output"]["width"], result["transform_chain"]["output"]["height"],
            result["roundtrip_max_error_pixels"],
        ),
    )
    for value in raw["artifacts"]:
        raw_owner = value["owner"]
        if (
            raw_owner["scene_instance_id"] != subject["scene_instance_id"]
            or raw_owner["canonical_person_id"] != subject["canonical_person_id"]
            or raw_owner["person_index"] != subject["person_index"]
        ):
            raise ValueError("raw producer receipt artifact owner differs from its signed subject binding")
    raw_artifacts = {
        (
            value["artifact_id"], value["encoded_sha256"], value["decoded_mask_sha256"], value["label"],
            value["width"], value["height"], PRODUCER_TO_MAIN_COORDINATE_SPACE[value["coordinate_space"]],
            subject["scene_instance_id"], subject["provider_person_index"], value["transform_chain_sha256"],
        )
        for value in raw["artifacts"]
    }
    main_artifacts = {
        (
            value["mask_ref"]["record_id"], value["mask_ref"]["sha256"], value["mask_sha256"], value["label"],
            value["width"], value["height"], value["coordinate_space"], value["owner"]["character_instance_id"],
            value["owner"]["provider_person_index"], result["transform_chain"]["chain_sha256"],
        )
        for value in result["masks"]
    }
    _assert_equal_projection("receipt artifact set", raw_artifacts, main_artifacts)
    authority = raw["authority"]
    expected_certificate_ref = _normalized_certificate_ref_for_raw(
        authority["certificate_id"], authority["certificate_sha256"], runtime_verification_context,
    )
    _assert_equal_projection(
        "receipt authority",
        (authority["authority_state"], authority["issuer_kind"], expected_certificate_ref),
        (result["authority"]["authority_state"], result["authority"]["issuer_kind"], result["authority"]["certificate_ref"]),
    )
    expected_claim = {
        "invalid": "invalid",
        "machine_candidate": "machine_candidate",
        "qa_passed_machine_candidate": "qa_passed_machine_candidate",
        "operationally_certified_artifact": "operationally_certified_artifact",
        "autonomous_certified_gold": "operationally_certified_artifact",
        "human_anchor_gold": "independent_real_accuracy_anchor",
    }[raw["truth_tier"]]
    _assert_equal_projection("receipt truth tier", expected_claim, result["authority"]["claim_class"])
    _assert_equal_projection("receipt revocation check time", authority["revocation_checked_at"], result["authority"]["revocation_checked_at"])
    if authority["authority_state"] == "certified":
        if authority["certificate_status"] != "active" or not authority["certificate_exact_scope_match"] or not result["authority"]["certificate_scope"]:
            raise ValueError("certified raw receipt lost active exact-scope certificate facts during normalization")
    if raw["qa"]["report_sha256"] not in _ref_hashes(result["qa_record_refs"]):
        raise ValueError("raw producer receipt QA report is absent from the Main result")
    observation = raw["execution_observation"]
    scope = result["execution_observation"]["execution_scope"]
    _assert_equal_projection(
        "receipt execution identity",
        (raw["project_id"], raw["run_id"], raw["job_id"], raw["pass_id"], raw["attempt_id"], raw["attempt_number"], raw["hypothesis_id"]),
        (scope["project_id"], scope["run_id"], scope["job_id"], scope["pass_id"], scope["attempt_id"], result["execution_observation"]["attempt_number"], result["execution_observation"]["hypothesis"]["hypothesis_id"]),
    )
    _assert_equal_projection(
        "receipt execution measurements",
        (observation["queue_ms"], observation["runtime_ms"], observation["resources"]["peak_vram_mb"], observation["resources"]["peak_ram_mb"], observation["resources"]["output_bytes"], observation["deadline_met"]),
        (result["execution_observation"]["queue_ms"], result["execution_observation"]["runtime_ms"], result["execution_observation"]["peak_vram_mb"], result["execution_observation"]["peak_ram_mb"], result["execution_observation"]["output_bytes"], result["execution_observation"]["deadline_met"]),
    )
    lineage = raw["lineage"]
    expected_kind_operation = {
        "original_prediction": ("original", "none"), "package_read": ("original", "none"),
        "refinement": ("derived", "refine"), "derived_union": ("derived", "union"),
        "inpaint_derivative": ("derived", "refine"), "projection": ("derived", "project"),
    }[lineage["operation_kind"]]
    if {(value["lineage_kind"], value["derivation_operation"]) for value in result["masks"]} != {expected_kind_operation}:
        raise ValueError("raw producer receipt lineage operation differs from the Main mask lineage")
    raw_parent_identities = set()
    for value in lineage["parents"]:
        normalized_parent_ref = _normalized_certificate_ref_for_raw(
            value["certificate_id"], value["certificate_sha256"], runtime_verification_context,
        )
        raw_parent_identities.add(
            (
                value["artifact_sha256"], value["authority_state"],
                None if normalized_parent_ref is None else immutable_ref_key(normalized_parent_ref),
            )
        )
    for mask in result["masks"]:
        main_parent_identities = {
            (
                value["parent_mask_ref"]["sha256"], value["parent_authority"]["authority_state"],
                None if value["parent_operational_certificate_ref"] is None else immutable_ref_key(value["parent_operational_certificate_ref"]),
            )
            for value in mask["parents"]
        }
        _assert_equal_projection("receipt lineage parent set", raw_parent_identities, main_parent_identities)
    expected_target_regions = {(value["region_id"], value["artifact_identity_sha256"]) for value in lineage["input_target_regions"]}
    observed_target_regions = {(value["record_id"], value["sha256"]) for value in result["input_region_lineage"]["target_region_refs"]}
    _assert_equal_projection("receipt target-region lineage", expected_target_regions, observed_target_regions)
    expected_protected_regions = {(value["region_id"], value["artifact_identity_sha256"]) for value in lineage["input_protected_regions"]}
    observed_protected_regions = {(value["record_id"], value["sha256"]) for value in result["input_region_lineage"]["protected_region_refs"]}
    _assert_equal_projection("receipt protected-region lineage", expected_protected_regions, observed_protected_regions)
    _assert_equal_projection("receipt lineage transform", transform["transform_chain_sha256"], result["input_region_lineage"]["request_transform_chain_sha256"])
    _assert_equal_projection(
        "receipt lineage output identities",
        set(lineage["output_artifact_identity_sha256s"]),
        {value["artifact_identity_sha256"] for value in raw["artifacts"]},
    )


def validate_raw_certificate_projection(
    raw: dict[str, Any], certificate: dict[str, Any], runtime_verification_context: dict[str, Any] | None,
) -> None:
    expected_context = "fixture_validation" if raw["fixture_only"] else "production_runtime"
    _assert_equal_projection(
        "certificate identity, context, status, and time",
        (raw["certificate_id"], expected_context, {"active": "active", "expired": "expired", "revoked": "revoked", "superseded": "revoked"}[raw["status"]], raw["issued_at"], raw["expires_at"], raw["access_mode"], raw["issuer_kind"]),
        (certificate["maskfactory_operational_certificate_v2_id"], certificate["certification_context"], certificate["status"], certificate["issued_at"], certificate["expires_at"], certificate["access_mode"], certificate["issuer_kind"]),
    )
    if runtime_verification_context is None:
        raise ValueError("certificate projection requires the signed adopted release binding")
    release_binding = raw["release_binding"]
    expected_release = runtime_verification_context.get("adopted_producer_release_binding")
    _assert_equal_projection(
        "certificate adopted producer release",
        (
            release_binding["release_id"], release_binding["release_payload_sha256"], release_binding["capability_snapshot_id"], release_binding["capability_snapshot_sha256"],
            release_binding["bridge_contract"], release_binding["certificate_schema_sha256"], release_binding["signing_key_set_id"],
            release_binding["signing_key_set_version"], release_binding["signing_key_set_sha256"], release_binding["rotation_policy_sha256"], release_binding["revocation_policy_sha256"],
        ),
        None if not isinstance(expected_release, dict) else (
            expected_release.get("release_id"), expected_release.get("release_payload_sha256"),
            expected_release.get("capability_snapshot_id"), expected_release.get("capability_snapshot_sha256"),
            expected_release.get("bridge_contract"), PRODUCER_SCHEMA_BINDINGS["operational_autonomy_certificate"]["schema_sha256"],
            expected_release.get("signing_key_set_id"), expected_release.get("signing_key_set_version"), expected_release.get("signing_key_set_sha256"),
            expected_release.get("rotation_policy_sha256"), expected_release.get("revocation_policy_sha256"),
        ),
    )
    _assert_equal_projection("certificate adopted Main release", runtime_verification_context.get("adopted_main_release_ref"), certificate["release_snapshot_ref"])
    execution = raw["execution_binding"]
    runtime_manifest_bytes = resolve_verified_artifact_bytes(certificate["runtime_provenance"]["runtime_manifest_ref"], runtime_verification_context)
    runtime_manifest = strict_json_loads(runtime_manifest_bytes)
    if not isinstance(runtime_manifest, dict):
        raise ValueError("certificate runtime manifest is not a structured immutable JSON document")
    required_runtime_manifest_fields = {
        "runtime_kind", "runtime_id", "runtime_version", "operating_system", "architecture", "python_version",
        "environment_lock_sha256", "interpreter_build_sha256", "venv_manifest_sha256", "container_sha256",
    }
    if set(runtime_manifest) != required_runtime_manifest_fields:
        raise ValueError("certificate runtime manifest is not the exact closed portability record")
    expected_main_runtime_kind = {
        ("native_venv", "Windows"): "windows_native_venv",
        ("native_venv", "Linux"): "linux_native_venv",
        ("container", runtime_manifest["operating_system"]): "container",
        ("remote_service", runtime_manifest["operating_system"]): "remote_service",
    }.get((execution["runtime_kind"], runtime_manifest["operating_system"]))
    if expected_main_runtime_kind is None:
        raise ValueError("certificate runtime kind/operating-system combination is not supported by the frozen portability mapping")
    _assert_equal_projection(
        "certificate execution stack",
        (
            execution["provider_stack_id"], execution["provider_stack_sha256"], execution["environment_lock_sha256"],
            execution["runtime_kind"], execution["runtime_id"], execution["runtime_version"], execution["interpreter_build_sha256"],
            execution["venv_manifest_sha256"], execution["container_sha256"],
        ),
        (
            certificate["execution_stack_ref"]["record_id"], certificate["execution_stack_ref"]["sha256"],
            runtime_manifest["environment_lock_sha256"], runtime_manifest["runtime_kind"], runtime_manifest["runtime_id"],
            runtime_manifest["runtime_version"], runtime_manifest["interpreter_build_sha256"], runtime_manifest["venv_manifest_sha256"],
            runtime_manifest["container_sha256"],
        ),
    )
    _assert_equal_projection(
        "certificate Main runtime projection",
        (
            expected_main_runtime_kind, runtime_manifest["operating_system"], runtime_manifest["architecture"], runtime_manifest["python_version"],
            runtime_manifest["environment_lock_sha256"], runtime_manifest["container_sha256"],
        ),
        (
            certificate["runtime_provenance"]["runtime_kind"], certificate["runtime_provenance"]["operating_system"],
            certificate["runtime_provenance"]["architecture"], certificate["runtime_provenance"]["python_version"],
            certificate["runtime_provenance"]["environment_lock_sha256"], certificate["runtime_provenance"]["container_image_digest"],
        ),
    )
    capability_snapshot = resolve_adopted_capability_snapshot(release_binding, runtime_verification_context)
    stack_matches = [
        value for value in capability_snapshot["provider_stacks"]
        if value["stack_id"] == execution["provider_stack_id"] and value["stack_sha256"] == execution["provider_stack_sha256"]
    ]
    if len(stack_matches) != 1:
        raise ValueError("certificate provider stack is not uniquely present in the signed adopted capability snapshot")
    stack = stack_matches[0]
    expected_capability = {
        "mode_a_package_read": "mask.package.read",
        "mode_b_live_predict": "mask.live.predict",
        "mode_b_live_refine": "mask.live.refine",
    }[raw["access_mode"]]
    _assert_equal_projection(
        "certificate signed route and capability",
        (stack["route_key"]["route_key_id"], expected_capability),
        (certificate["serving_route_id"], certificate["capability_id"]),
    )
    if expected_capability not in stack["capability_ids"] or raw["access_mode"] not in stack["access_modes"]:
        raise ValueError("certificate access mode/capability is absent from the signed adopted capability snapshot")
    qualified = raw["qualified_route_scope"]
    stack_scope = stack["qualification_scope"]
    _assert_equal_projection(
        "certificate qualified route scope",
        (qualified["scope_sha256"], set(qualified["labels"]), set(qualified["contexts"]), set(qualified["risk_buckets"]), qualified["max_person_count"], set(qualified["artifact_kinds"])),
        (stack_scope["scope_sha256"], set(stack_scope["labels"]), set(stack_scope.get("contexts", qualified["contexts"])), set(qualified["risk_buckets"]), stack_scope["max_person_count"], set(stack_scope["artifact_kinds"])),
    )
    source = raw["source_binding"]
    _assert_equal_projection(
        "certificate source identity",
        (source["encoded_sha256"], source["width"], source["height"], _normalized_color_space(source["color_space"])),
        (certificate["source_artifact"]["sha256"], certificate["source_artifact"]["width"], certificate["source_artifact"]["height"], certificate["source_artifact"]["color_space"]),
    )
    _assert_equal_projection("certificate media scope", _expected_main_media_scope(raw["media_scope"], source["encoded_sha256"]), _observed_main_media_scope(certificate["media_scope"]))
    subject = raw["subject_binding"]
    if (subject["scene_instance_id"], subject["provider_person_index"]) not in {
        (value["character_instance_id"], value["provider_person_index"]) for value in certificate["owner_bindings"]
    }:
        raise ValueError("raw producer certificate subject ownership is not preserved by Main")
    coordinate = raw["coordinate_binding"]
    _assert_equal_projection(
        "certificate coordinate and transform binding",
        (
            coordinate["transform_chain_id"], coordinate["transform_chain_sha256"],
            PRODUCER_TO_MAIN_COORDINATE_SPACE[coordinate["source_coordinate_space"]], coordinate["source_width"], coordinate["source_height"],
            PRODUCER_TO_MAIN_COORDINATE_SPACE[coordinate["output_coordinate_space"]], coordinate["output_width"], coordinate["output_height"],
            coordinate["maximum_roundtrip_error_px"], tuple(coordinate["executed_step_sha256s"]),
        ),
        (
            certificate["transform_chain"]["chain_id"], certificate["transform_chain"]["chain_sha256"],
            certificate["transform_chain"]["source"]["coordinate_space"], certificate["transform_chain"]["source"]["width"], certificate["transform_chain"]["source"]["height"],
            certificate["transform_chain"]["output"]["coordinate_space"], certificate["transform_chain"]["output"]["width"], certificate["transform_chain"]["output"]["height"],
            certificate["transform_chain"]["roundtrip_policy"]["maximum_error_pixels"], tuple(value["step_sha256"] for value in certificate["transform_chain"]["steps"]),
        ),
    )
    expected_outputs = {(value["artifact_id"], value["encoded_sha256"]) for value in raw["bound_artifacts"]}
    observed_outputs = {(value["record_id"], value["sha256"]) for value in certificate["output_refs"]}
    _assert_equal_projection("certificate output artifact set", expected_outputs, observed_outputs)
    if not raw["certified_output_scope"]["exact_scope_only"] or set(raw["certified_output_scope"]["artifact_identity_sha256s"]) != {value["artifact_identity_sha256"] for value in raw["bound_artifacts"]}:
        raise ValueError("raw producer certificate output scope is widened or not bound to its exact artifact identities")
    _assert_equal_projection("certificate exact normalized scope", exact_certificate_scope_projection(raw), sorted(certificate["certificate_scope"]))
    output_scope = raw["certified_output_scope"]
    if set(output_scope["owners"]) != {value["scene_instance_id"] for value in raw["bound_artifacts"]}:
        raise ValueError("raw producer certificate output owner scope differs from bound artifacts")
    if set(output_scope["coordinate_spaces"]) != {value["coordinate_space"] for value in raw["bound_artifacts"]}:
        raise ValueError("raw producer certificate coordinate scope differs from bound artifacts")
    if set(output_scope["artifact_kinds"]) != {value["artifact_kind"] for value in raw["bound_artifacts"]}:
        raise ValueError("raw producer certificate artifact-kind scope differs from bound artifacts")
    if set(output_scope["labels"]) != {value["label"] for value in raw["bound_artifacts"]}:
        raise ValueError("raw producer certificate label scope differs from bound artifacts")
    qa = raw["qa_evidence"]
    if qa["status"] != "pass" or not qa["all_blocking_gates_passed"] or any(value["result"] != "pass" for value in certificate["qa_bindings"]):
        raise ValueError("raw producer certificate QA pass is not preserved by Main")
    expected_qa = {
        ("deterministic_report", qa["deterministic_report_sha256"]),
        ("critic_report", qa["critic_report_sha256"]),
        ("ownership_report", qa["ownership_report_sha256"]),
        ("protected_region_report", qa["protected_region_report_sha256"]),
        *{(f"producer_gate:{value['gate_id']}", value["evidence_sha256"]) for value in qa["gate_results"]},
    }
    observed_qa = {(value["gate_id"], value["qa_record_ref"]["sha256"]) for value in certificate["qa_bindings"]}
    _assert_equal_projection("certificate exact QA evidence set", expected_qa, observed_qa)
    critic = qa["critic_binding"]
    expected_critic_hashes = {
        critic["critic_stack_sha256"], critic["workflow_sha256"], critic["execution_fingerprint_sha256"],
        critic["qualification_scope_sha256"], critic["qualification_certificate_sha256"],
        *{value["sha256"] for value in critic["model_artifacts"]},
    }
    if not expected_critic_hashes.issubset(_ref_hashes(certificate["evidence_manifest_refs"])):
        raise ValueError("raw producer certificate independent critic identity/qualification is absent from Main evidence")
    revocation = raw["revocation"]
    if revocation["is_revoked"] != (certificate["revocation_ref"] is not None):
        raise ValueError("raw producer certificate revocation status differs from Main")
    if revocation["revocation_index_sha256"] not in _ref_hashes(certificate["revocation_manifest_refs"]):
        raise ValueError("raw producer certificate revocation index is absent from Main")


def validate_raw_invalidation_projection(raw: dict[str, Any], event: dict[str, Any]) -> None:
    _assert_equal_projection("invalidation fixture status", raw["fixture_only"], event["fixture_only"])
    expected_evidence_context = "conformance_fixture" if raw["fixture_only"] else "runtime_evidence"
    if raw["evidence_context"] != expected_evidence_context:
        raise ValueError("raw producer invalidation fixture/evidence context is contradictory")
    _assert_equal_projection(
        "invalidation identity, stream, timing, and policy",
        (
            raw["event_id"], raw["stream_id"], raw["sequence"], raw["causation_id"], raw["idempotency_key"],
            raw["occurred_at"], raw["effective_at"], raw["reason"], {"warning": "blocking", "blocking": "blocking"}[raw["severity"]], raw["evidence_sha256"],
        ),
        (
            event["event_id"], event["stream_id"], event["sequence"], event["causation_id"], event["idempotency_key"],
            event["created_at"], event["effective_at"], event["reason"], event["severity"], event["producer_evidence_sha256"],
        ),
    )
    canonical_producer_identity = unicodedata.normalize("NFC", raw["producer"]).casefold()
    if event["producer_identity"] != canonical_producer_identity:
        raise ValueError("raw producer invalidation issuer identity differs from Main")
    raw_transitions = {
        tuple(value[key] for key in (
            "transition_id", "target_kind", "target_id", "target_sha256", "previous_authority_state",
            "new_authority_state", "previous_certificate_status", "new_certificate_status", "reason_code", "scope_sha256",
        ))
        for value in raw["target_transitions"]
    }
    main_transitions = {
        tuple(value[key] for key in (
            "transition_id", "target_kind", "target_id", "target_sha256", "previous_authority_state",
            "new_authority_state", "previous_certificate_status", "new_certificate_status", "reason_code", "scope_sha256",
        ))
        for value in event["target_transitions"]
    }
    _assert_equal_projection("invalidation target-transition set", raw_transitions, main_transitions)
    raw_actions = {
        (value["action_id"], tuple(value["transition_ids"]), value["action"], value["deadline_at"], value["verification_evidence_required"], value["verification_policy_sha256"])
        for value in raw["required_actions"]
    }
    main_actions = {
        (value["action_id"], tuple(value["transition_ids"]), value["action"], value["deadline_at"], value["verification_evidence_required"], value["verification_policy_sha256"])
        for value in event["required_actions"]
    }
    _assert_equal_projection("invalidation required-action set", raw_actions, main_actions)
    for raw_name, main_name in (("superseding_binding", "superseding_binding"), ("rollback_binding", "rollback_binding")):
        _assert_equal_projection(f"invalidation {raw_name}", raw[raw_name], event[main_name])


def csv_bytes(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def bridge_event_sha256(event: dict[str, Any]) -> str:
    excluded = {"event_sha256", "signature", "signature_trust", "journal_pin"}
    payload = {key: value for key, value in event.items() if key not in excluded}
    domain = b"comfy_ui_main.maskfactory_bridge_event.v2\0"
    return sha256_bytes(domain + canonical_json(payload))


def promotion_policy_sha256(policy: dict[str, Any]) -> str:
    return sha256_bytes(promotion_policy_payload_bytes(policy))


def promotion_policy_payload_bytes(policy: dict[str, Any]) -> bytes:
    excluded = {"policy_sha256", "signature", "signature_trust", "policy_artifact_ref"}
    payload = {key: value for key, value in policy.items() if key not in excluded}
    artifact_ref = policy["policy_artifact_ref"]
    payload["policy_artifact_identity"] = {key: artifact_ref[key] for key in ("record_type", "record_id", "revision")}
    domain = b"comfy_ui_main.maskfactory_promotion_gate_policy.v2\0"
    return domain + canonical_json(payload)


def seal_promotion_policy(policy: dict[str, Any]) -> None:
    digest = promotion_policy_sha256(policy)
    policy["policy_sha256"] = digest
    policy["policy_artifact_ref"]["sha256"] = digest


def operational_certificate_payload_bytes(certificate: dict[str, Any]) -> bytes:
    excluded = {"certificate_payload_sha256", "signature", "signature_trust"}
    payload = {key: value for key, value in certificate.items() if key not in excluded}
    return b"comfy_ui_main.maskfactory_operational_certificate.v2\0" + canonical_json(payload)


def operational_certificate_sha256(certificate: dict[str, Any]) -> str:
    return sha256_bytes(operational_certificate_payload_bytes(certificate))


def seal_operational_certificate(certificate: dict[str, Any]) -> None:
    certificate["certificate_payload_sha256"] = operational_certificate_sha256(certificate)


def immutable_operational_certificate_ref(certificate: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": certificate["record_type"],
        "record_id": certificate["maskfactory_operational_certificate_v2_id"],
        "revision": certificate["revision"],
        "sha256": certificate["certificate_payload_sha256"],
    }


def normalized_result_payload_bytes(result: dict[str, Any]) -> bytes:
    excluded = {"normalization_payload_sha256", "normalization_signature", "normalization_signature_trust"}
    payload = {key: value for key, value in result.items() if key not in excluded}
    return b"comfy_ui_main.maskfactory_normalized_result.v2\0" + canonical_json(payload)


def normalized_result_sha256(result: dict[str, Any]) -> str:
    return sha256_bytes(normalized_result_payload_bytes(result))


def seal_normalized_result(result: dict[str, Any]) -> None:
    result["normalization_payload_sha256"] = normalized_result_sha256(result)


def normalized_release_payload_bytes(release: dict[str, Any]) -> bytes:
    excluded = {"normalization_payload_sha256", "normalization_signature", "normalization_signature_trust"}
    payload = {key: value for key, value in release.items() if key not in excluded}
    return b"comfy_ui_main.maskfactory_normalized_release.v2\0" + canonical_json(payload)


def normalized_release_sha256(release: dict[str, Any]) -> str:
    return sha256_bytes(normalized_release_payload_bytes(release))


def seal_normalized_release(release: dict[str, Any]) -> None:
    release["normalization_payload_sha256"] = normalized_release_sha256(release)


def trusted_key_entry_sha256(entry: dict[str, Any]) -> str:
    payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
    return sha256_bytes(b"comfy_ui_main.maskfactory_trusted_key_entry.v2\0" + canonical_json(payload))


def trusted_clock_payload(clock: dict[str, Any]) -> bytes:
    payload = {
        key: clock[key]
        for key in ("source", "observed_at", "clock_sequence", "monotonic_floor_at")
    }
    return canonical_json(payload)


def journal_checkpoint_payload(journal_pin: dict[str, Any]) -> bytes:
    payload = {
        key: journal_pin[key]
        for key in (
            "stream_id", "checkpoint_sequence", "head_event_sha256",
            "previous_checkpoint_sha256", "checkpointed_at", "fresh_until",
        )
    }
    return canonical_json(payload)


def adoption_receipt_sha256(adoption: dict[str, Any]) -> str:
    excluded = {"adoption_receipt_sha256", "adoption_signature", "adoption_signature_trust"}
    payload = {key: value for key, value in adoption.items() if key not in excluded}
    domain = b"comfy_ui_main.maskfactory_adoption_receipt.v2\0"
    return sha256_bytes(domain + canonical_json(payload))


def seal_adoption_receipt(adoption: dict[str, Any]) -> None:
    if "qualification_bundle_ref" in adoption:
        qualification_bytes = canonical_json({"checks": adoption["checks"]})
        qualification_digest = sha256_bytes(qualification_bytes)
        adoption["qualification_bundle_sha256"] = qualification_digest
        adoption["qualification_bundle_ref"]["sha256"] = qualification_digest
    adoption["adoption_receipt_sha256"] = adoption_receipt_sha256(adoption)


def immutable_release_ref(release: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": release["record_type"], "record_id": release["maskfactory_release_snapshot_v2_id"],
        "revision": release["revision"], "sha256": release["normalization_payload_sha256"],
    }


def immutable_adoption_ref(adoption: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": adoption["record_type"], "record_id": adoption["maskfactory_adoption_receipt_v2_id"],
        "revision": adoption["revision"], "sha256": adoption["adoption_receipt_sha256"],
    }


def release_gate_report_sha256(report: dict[str, Any]) -> str:
    excluded = {"gate_report_sha256", "gate_report_signature", "signature_trust"}
    payload = {key: value for key, value in report.items() if key not in excluded}
    gate_ref = copy.deepcopy(payload["gate_report_ref"])
    gate_ref["sha256"] = "0" * 64
    payload["gate_report_ref"] = gate_ref
    domain = b"comfy_ui_main.maskfactory_bridge_release_gate_report.v2\0"
    return sha256_bytes(domain + canonical_json(payload))


def seal_release_gate_report(report: dict[str, Any]) -> None:
    digest = release_gate_report_sha256(report)
    report["gate_report_sha256"] = digest
    report["gate_report_ref"]["sha256"] = digest


def bridge_release_certificate_sha256(release: dict[str, Any]) -> str:
    excluded = {"release_certificate_sha256", "release_signature", "release_signature_trust"}
    payload = {key: value for key, value in release.items() if key not in excluded}
    domain = b"comfy_ui_main.maskfactory_bridge_release_certificate.v2\0"
    return sha256_bytes(domain + canonical_json(payload))


def seal_bridge_release_certificate(release: dict[str, Any]) -> None:
    release["release_certificate_sha256"] = bridge_release_certificate_sha256(release)


def immutable_bridge_release_ref(release: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": release["record_type"], "record_id": release["maskfactory_bridge_release_certificate_v2_id"],
        "revision": release["revision"], "sha256": release["release_certificate_sha256"],
    }


def invalidation_event_sha256(event: dict[str, Any]) -> str:
    excluded = {"invalidation_event_sha256", "normalization_signature", "producer_signature_trust", "signature_trust"}
    payload = {key: value for key, value in event.items() if key not in excluded}
    domain = b"comfy_ui_main.maskfactory_invalidation_event.v2\0"
    return sha256_bytes(domain + canonical_json(payload))


def seal_invalidation_event(event: dict[str, Any]) -> None:
    event["invalidation_event_sha256"] = invalidation_event_sha256(event)


def immutable_ref_key(value: dict[str, str]) -> tuple[str, str, str, str]:
    return tuple(value[key] for key in ("record_type", "record_id", "revision", "sha256"))


def resolve_verified_artifact_bytes(value: dict[str, str], runtime_verification_context: dict[str, Any] | None) -> bytes:
    if runtime_verification_context is None:
        raise ValueError("production authority requires an independent runtime evidence resolver")
    payload = runtime_verification_context.get("artifact_bytes", {}).get(immutable_ref_key(value))
    if not isinstance(payload, bytes) or sha256_bytes(payload) != value["sha256"]:
        raise ValueError("runtime evidence ref is missing or does not hash to the independently resolved artifact bytes")
    return payload


def verify_runtime_evidence_refs(values: list[dict[str, str]], runtime_verification_context: dict[str, Any] | None) -> None:
    if not values:
        raise ValueError("production authority requires non-empty independently resolved runtime evidence")
    for value in values:
        resolve_verified_artifact_bytes(value, runtime_verification_context)


def resolve_trusted_use_time(use_time: str | None, runtime_verification_context: dict[str, Any] | None) -> str:
    if runtime_verification_context is None:
        raise ValueError("production authority requires an independently supplied trusted runtime clock")
    clock = runtime_verification_context.get("trusted_clock")
    if (
        not isinstance(clock, dict)
        or clock.get("source") not in {"main_monotonic_utc_clock", "trusted_time_service"}
        or not isinstance(clock.get("observed_at"), str)
        or not isinstance(clock.get("evidence_ref"), dict)
        or not isinstance(clock.get("clock_sequence"), int)
        or clock["clock_sequence"] < 1
        or not isinstance(clock.get("monotonic_floor_at"), str)
        or not isinstance(clock.get("payload_sha256"), str)
        or clock.get("signature_domain") != "comfy_ui_main.trusted_clock_observation.v1"
        or not isinstance(clock.get("signature"), str)
        or not isinstance(clock.get("signature_trust"), dict)
    ):
        raise ValueError("production authority requires a signed structured trusted runtime clock observation")
    resolved_clock = resolve_verified_artifact_bytes(clock["evidence_ref"], runtime_verification_context)
    clock_payload = trusted_clock_payload(clock)
    if resolved_clock != clock_payload or clock["payload_sha256"] != sha256_bytes(clock_payload):
        raise ValueError("trusted runtime clock evidence does not exactly bind the clock observation")
    if use_time is not None and use_time != clock["observed_at"]:
        raise ValueError("caller-supplied use time does not match the independently supplied trusted runtime clock")
    observed_at = parse_timestamp(clock["observed_at"])
    monotonic_floor_at = parse_timestamp(clock["monotonic_floor_at"])
    context_floor = runtime_verification_context.get("last_accepted_use_time")
    last_sequence = runtime_verification_context.get("last_accepted_clock_sequence")
    if not isinstance(context_floor, str) or not isinstance(last_sequence, int):
        raise ValueError("trusted runtime clock continuity requires persisted last-accepted time and sequence")
    if (
        observed_at < monotonic_floor_at
        or monotonic_floor_at < parse_timestamp(context_floor)
        or observed_at < parse_timestamp(context_floor)
        or clock["clock_sequence"] <= last_sequence
    ):
        raise ValueError("trusted runtime clock observation is backdated, replayed, or non-increasing")
    trusted_keys = runtime_verification_context.get("trusted_keys")
    validate_signature_trust_record(
        clock["signature_trust"], trusted_keys, production_required=True,
        expected_signer_role="main_trusted_clock_signer", use_time=clock["observed_at"],
        runtime_verification_context=runtime_verification_context,
    )
    verify_ed25519_runtime_signature(
        clock["payload_sha256"], clock["signature"], clock["signature_domain"],
        clock["signature_trust"], trusted_keys, runtime_verification_context,
        expected_signer_role="main_trusted_clock_signer", use_time=clock["observed_at"],
    )
    return clock["observed_at"]


def verify_ed25519_runtime_signature(
    payload_sha256: str, signature_base64: str, signature_domain: str, trust: dict[str, Any],
    trusted_keys: dict[str, Any] | None, runtime_verification_context: dict[str, Any] | None,
    *, expected_signer_role: str, use_time: str, signature_message_format: str = "domain_separated_digest",
) -> None:
    if runtime_verification_context is None or trusted_keys is None:
        raise ValueError("production authority requires an independent signature verifier and trusted public-key material")
    entry = trusted_keys.get(trust["signing_key_id"])
    if not isinstance(entry, dict) or entry.get("status") != "active" or not isinstance(entry.get("public_key_base64"), str):
        raise ValueError("production signing key lacks independently supplied active Ed25519 public-key material")
    required_entry_fields = {
        "key_id", "signer_role", "status", "public_key_base64", "public_key_sha256",
        "valid_from", "valid_until", "revocation_checked_at", "revocation_valid_until",
        "revocation_evidence_ref", "entry_sha256",
    }
    if set(entry) != required_entry_fields:
        raise ValueError("trusted signing-key entry is not the exact closed registry record")
    use_at = parse_timestamp(use_time)
    if (
        entry["key_id"] != trust["signing_key_id"]
        or entry["signer_role"] != expected_signer_role
        or trust["signer_role"] != expected_signer_role
        or trusted_key_entry_sha256(entry) != entry["entry_sha256"]
        or not parse_timestamp(entry["valid_from"]) <= use_at < parse_timestamp(entry["valid_until"])
        or not parse_timestamp(entry["revocation_checked_at"]) <= use_at < parse_timestamp(entry["revocation_valid_until"])
    ):
        raise ValueError("trusted signing key role, canonical entry, validity, or revocation status is invalid at use time")
    resolve_verified_artifact_bytes(entry["revocation_evidence_ref"], runtime_verification_context)
    resolve_verified_artifact_bytes(trust["verification_evidence_ref"], runtime_verification_context)
    try:
        public_key_bytes = base64.b64decode(entry["public_key_base64"], validate=True)
        signature_bytes = base64.b64decode(signature_base64, validate=True)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        if signature_message_format == "domain_separated_digest":
            signed_message = signature_domain.encode("utf-8") + b"\0" + bytes.fromhex(payload_sha256)
        elif signature_message_format == "digest_bytes":
            signed_message = bytes.fromhex(payload_sha256)
        else:
            raise ValueError("unknown signature message format")
        public_key.verify(signature_bytes, signed_message)
    except Exception as exc:
        raise ValueError("Ed25519 signature verification failed against the out-of-band trusted key") from exc
    public_key_sha256 = sha256_bytes(public_key_bytes)
    if entry.get("public_key_sha256") != public_key_sha256 or trust["embedded_public_key_sha256"] != public_key_sha256 or trust["trusted_key_entry_sha256"] != entry.get("entry_sha256"):
        raise ValueError("verified Ed25519 key does not match the exact out-of-band trust-registry binding")


def producer_invalidation_policy_document(*, final_release_binding: bool = False) -> dict[str, Any]:
    del final_release_binding
    return {
        "policy_version": "1.0.0",
        "revalidation_triggers": sorted(PRODUCER_INVALIDATION_REASON_POLICY),
        "invalidation_reasons": {
            reason: {
                "target_kinds": sorted(policy["target_kinds"]),
                "required_actions": sorted(policy["required_actions"]),
            }
            for reason, policy in sorted(PRODUCER_INVALIDATION_REASON_POLICY.items())
        },
    }


def producer_invalidation_policy_sha256(policy: dict[str, Any] | None = None) -> str:
    compact = json.dumps(
        policy or producer_invalidation_policy_document(), sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(compact)


def producer_invalidation_policy_bytes(policy: dict[str, Any] | None = None) -> bytes:
    return json.dumps(
        policy or producer_invalidation_policy_document(), sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")


def producer_invalidation_policy_ref(policy: dict[str, Any] | None = None) -> dict[str, str]:
    value = policy or producer_invalidation_policy_document()
    return {
        "record_type": "maskfactory_invalidation_reason_policy",
        "record_id": "maskfactory_invalidation_reason_policy_v1",
        "revision": value["policy_version"],
        "sha256": producer_invalidation_policy_sha256(value),
    }


def main_enforcement_actions_for_reason(reason: str) -> list[str]:
    if reason in {"release_revoked", "signed_journal_fork_detected"}:
        return ["rollback_or_block"]
    if reason in {"package_invalidated", "artifact_invalidated", "artifact_hash_drift"}:
        return ["invalidate_cache_and_revalidate"]
    if reason in {"provider_stack_changed", "qa_regression"}:
        return ["demote_and_repair"]
    return ["block_and_revalidate"]


def build_revalidation_rules() -> list[dict[str, Any]]:
    return [
        {
            "producer_reason_code": reason,
            "allowed_target_kinds": copy.deepcopy(policy["target_kinds"]),
            "required_producer_actions": copy.deepcopy(policy["required_actions"]),
            "main_enforcement_actions": main_enforcement_actions_for_reason(reason),
            "invalidates_active_pin": "revalidate_adoption" in policy["required_actions"],
            "invalidates_dependent_cache": bool(set(policy["required_actions"]) & {"invalidate_cache", "tombstone_cached_artifact", "quarantine_artifact", "block_dependent_pass", "rollback_release"}),
            "requires_signature_reverification": bool(set(policy["target_kinds"]) & {"release", "signing_key", "trust_policy", "policy", "wire_schema", "semantic_profile", "api_contract", "package_format", "ontology", "node_pack", "certificate", "adoption_receipt"}),
            "requires_journal_reconciliation": reason in {"signed_journal_stale", "signed_journal_fork_detected", "revocation_checkpoint_stale"},
            "scope": "exact_affected_scope_then_dependents",
            "producer_semantics_preserved": True,
            "no_silent_fallback": True,
        }
        for reason, policy in PRODUCER_INVALIDATION_REASON_POLICY.items()
    ]


def ref(record_type: str, record_id: str, char: str = "a") -> dict[str, str]:
    return {"record_type": record_type, "record_id": record_id, "revision": "r001", "sha256": h(char)}


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous_release: str | None = None
    number = 321
    for (workstream_id, slug, objective), specs in zip(WORKSTREAMS, ROW_SPECS, strict=True):
        workstream_items: list[str] = []
        for index, (phase, title, action, acceptance, external_gates) in enumerate(specs):
            item_id = f"ITEM-W64-{number:03d}"
            tracker_id = f"TRK-W64-{number:03d}"
            if index == 0:
                dependencies = list(PARENT_ITEMS)
                if previous_release:
                    dependencies.append(previous_release)
            else:
                dependencies = list(workstream_items)
            if number == 348:
                dependencies.append("ITEM-W64-218")
            row = {
                "row_number": number,
                "item_id": item_id,
                "tracker_id": tracker_id,
                "workstream_id": workstream_id,
                "workstream": slug,
                "domain": "maskfactory_autonomous_bridge",
                "phase": phase,
                "title": title,
                "implementation_action": action,
                "acceptance": acceptance,
                "dependencies": dependencies,
                "required_artifacts": ["implementation_hashes", "tests", "qa_record", "pass_or_exact_blocker"],
                "external_gates": external_gates,
                "status": STATUS,
                "runtime_proof_required": True,
                "runtime_completion_claimed": False,
                "completion_profile": "core_autonomous_runtime",
                "optional_profiles_not_blocking": ["independent_real_accuracy", "scale_daz_maturity"],
                "source_citations": [
                    "Plan/00_PROJECT_CONTROL/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_AND_RELEASE_HANDSHAKE_MASTER_PLAN.md",
                    "Plan/02_TARGET_ARCHITECTURE/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ARCHITECTURE.md",
                    "Plan/Instructions/WAVE64_MASKFACTORY_BRIDGE_IMPLEMENTATION_AND_OPERATION_PROTOCOL.md",
                    "Plan/Instructions/QA/WAVE64_MASKFACTORY_BRIDGE_QA_AND_PROMOTION_PROTOCOL.md",
                ],
            }
            rows.append(row)
            workstream_items.append(item_id)
            number += 1
        previous_release = workstream_items[-1]
    return rows


def strict_object(properties: dict[str, Any], required: list[str], **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }
    result.update(extra)
    return result


def base_properties(record_type: str) -> dict[str, Any]:
    return {
        "schema_version": {"const": SCHEMA_VERSION},
        "record_type": {"const": record_type},
        f"{record_type}_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
        "revision": {"$ref": f"{COMMON_ID}#/$defs/id"},
        "created_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
        "fixture_only": {"type": "boolean"},
        "runtime_completion_claimed": {"const": False},
    }


def record_required(record_type: str) -> list[str]:
    return ["schema_version", "record_type", f"{record_type}_id", "revision", "created_at", "fixture_only", "runtime_completion_claimed"]


def record_schema(record_type: str, properties: dict[str, Any], required: list[str], all_of: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    schema = strict_object({**base_properties(record_type), **properties}, [*record_required(record_type), *required])
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{SCHEMA_BASE}/{record_type}.schema.json", "title": record_type})
    if all_of:
        schema["allOf"] = all_of
    return schema


def build_schemas() -> dict[str, dict[str, Any]]:
    immutable_ref = strict_object(
        {"record_type": {"$ref": "#/$defs/id"}, "record_id": {"$ref": "#/$defs/id"}, "revision": {"$ref": "#/$defs/id"}, "sha256": {"$ref": "#/$defs/sha256"}},
        ["record_type", "record_id", "revision", "sha256"],
    )
    contract_binding = strict_object(
        {
            "wire_schema_name": {"$ref": "#/$defs/id"},
            "schema_source": {"type": "string", "minLength": 3},
            "schema_id": {"type": "string", "format": "uri"},
            "schema_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "schema_sha256": {"$ref": "#/$defs/sha256"},
        },
        ["wire_schema_name", "schema_source", "schema_id", "schema_version", "schema_sha256"],
    )
    scope = strict_object(
        {
            "project_id": {"$ref": "#/$defs/id"}, "run_id": {"$ref": "#/$defs/id"}, "job_id": {"$ref": "#/$defs/id"},
            "pass_id": {"$ref": "#/$defs/id"}, "attempt_id": {"$ref": "#/$defs/id"}, "scene_id": {"$ref": "#/$defs/id"},
            "shot_id": {"$ref": "#/$defs/id"}, "take_id": {"$ref": "#/$defs/id"},
        },
        ["project_id", "run_id", "job_id", "pass_id", "attempt_id", "scene_id", "shot_id", "take_id"],
    )
    source_artifact = strict_object(
        {
            "artifact_ref": {"$ref": "#/$defs/immutable_ref"}, "sha256": {"$ref": "#/$defs/sha256"},
            "width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1},
            "color_space": {"enum": ["srgb", "linear_srgb", "display_p3", "acescg"]},
            "coordinate_space": {"enum": ["source_pixels", "normalized_0_1", "working_pixels", "frame_pixels"]},
        },
        ["artifact_ref", "sha256", "width", "height", "color_space", "coordinate_space"],
    )
    media_scope = strict_object(
        {
            "media_kind": {"enum": ["still_image", "video_frame", "frame_span"]},
            "source_media_ref": {"$ref": "#/$defs/immutable_ref"}, "source_media_sha256": {"$ref": "#/$defs/sha256"},
            "frame_index": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
            "pts_ticks": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
            "timebase_numerator": {"oneOf": [{"type": "integer", "minimum": 1}, {"type": "null"}]},
            "timebase_denominator": {"oneOf": [{"type": "integer", "minimum": 1}, {"type": "null"}]},
            "span_start_frame": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
            "span_end_frame": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
            "neighbor_frame_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "uniqueItems": True},
            "temporal_evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "uniqueItems": True},
            "exact_frame_scope_only": {"const": True},
        },
        ["media_kind", "source_media_ref", "source_media_sha256", "frame_index", "pts_ticks", "timebase_numerator", "timebase_denominator", "span_start_frame", "span_end_frame", "neighbor_frame_refs", "temporal_evidence_refs", "exact_frame_scope_only"],
        allOf=[
            {"if": {"properties": {"media_kind": {"const": "still_image"}}, "required": ["media_kind"]}, "then": {"properties": {"frame_index": {"type": "null"}, "pts_ticks": {"type": "null"}, "timebase_numerator": {"type": "null"}, "timebase_denominator": {"type": "null"}, "span_start_frame": {"type": "null"}, "span_end_frame": {"type": "null"}, "neighbor_frame_refs": {"maxItems": 0}, "temporal_evidence_refs": {"maxItems": 0}}}},
            {"if": {"properties": {"media_kind": {"const": "video_frame"}}, "required": ["media_kind"]}, "then": {"properties": {"frame_index": {"type": "integer"}, "pts_ticks": {"type": "integer"}, "timebase_numerator": {"type": "integer"}, "timebase_denominator": {"type": "integer"}, "span_start_frame": {"type": "null"}, "span_end_frame": {"type": "null"}, "temporal_evidence_refs": {"minItems": 1}}}},
            {"if": {"properties": {"media_kind": {"const": "frame_span"}}, "required": ["media_kind"]}, "then": {"properties": {"frame_index": {"type": "null"}, "pts_ticks": {"type": "null"}, "timebase_numerator": {"type": "integer"}, "timebase_denominator": {"type": "integer"}, "span_start_frame": {"type": "integer"}, "span_end_frame": {"type": "integer"}, "temporal_evidence_refs": {"minItems": 1}}}},
        ],
    )
    owner_binding = strict_object(
        {
            "character_instance_id": {"$ref": "#/$defs/id"}, "provider_person_index": {"type": "integer", "minimum": 0},
            "owner_role": {"enum": ["target", "protected", "context"]}, "assignment_evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "minItems": 1},
        },
        ["character_instance_id", "provider_person_index", "owner_role", "assignment_evidence_refs"],
    )
    scene_owner_roster = strict_object(
        {
            "roster_ref": {"$ref": "#/$defs/immutable_ref"},
            "target_character_instance_id": {"$ref": "#/$defs/id"},
            "character_instance_ids": {"type": "array", "items": {"$ref": "#/$defs/id"}, "minItems": 1, "uniqueItems": True},
            "prop_instance_ids": {"type": "array", "items": {"$ref": "#/$defs/id"}, "uniqueItems": True},
            "environment_instance_id": {"$ref": "#/$defs/id"},
        },
        ["roster_ref", "target_character_instance_id", "character_instance_ids", "prop_instance_ids", "environment_instance_id"],
    )
    input_region_binding = strict_object(
        {
            "region_id": {"$ref": "#/$defs/id"},
            "region_ref": {"$ref": "#/$defs/immutable_ref"},
            "region_sha256": {"$ref": "#/$defs/sha256"},
            "source_artifact_sha256": {"$ref": "#/$defs/sha256"},
            "region_role": {"enum": ["target", "protected"]},
            "selector_kind": {"enum": ["roi_constraint", "mode_a_exact_package_artifact"]},
            "owner_entity_type": {"enum": ["character_instance", "prop", "environment"]},
            "owner_entity_id": {"$ref": "#/$defs/id"},
            "relationship_to_target": {"enum": ["self", "other_character", "prop", "environment"]},
            "provider_person_index": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
            "label": {"$ref": "#/$defs/id"},
            "coordinate_space": {"enum": ["source_pixels", "working_pixels", "frame_pixels", "normalized_0_1"]},
            "width": {"type": "integer", "minimum": 1},
            "height": {"type": "integer", "minimum": 1},
            "transform_chain_sha256": {"$ref": "#/$defs/sha256"},
            "transform_step_sequence": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
            "assignment_evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "minItems": 1},
        },
        ["region_id", "region_ref", "region_sha256", "source_artifact_sha256", "region_role", "selector_kind", "owner_entity_type", "owner_entity_id", "relationship_to_target", "provider_person_index", "label", "coordinate_space", "width", "height", "transform_chain_sha256", "transform_step_sequence", "assignment_evidence_refs"],
        allOf=[
            {"if": {"properties": {"owner_entity_type": {"const": "character_instance"}}, "required": ["owner_entity_type"]}, "then": {"properties": {"provider_person_index": {"type": "integer"}, "relationship_to_target": {"enum": ["self", "other_character"]}}}},
            {"if": {"properties": {"owner_entity_type": {"const": "prop"}}, "required": ["owner_entity_type"]}, "then": {"properties": {"provider_person_index": {"type": "null"}, "relationship_to_target": {"const": "prop"}}}},
            {"if": {"properties": {"owner_entity_type": {"const": "environment"}}, "required": ["owner_entity_type"]}, "then": {"properties": {"provider_person_index": {"type": "null"}, "relationship_to_target": {"const": "environment"}}}},
            {"if": {"properties": {"selector_kind": {"const": "mode_a_exact_package_artifact"}}, "required": ["selector_kind"]}, "then": {"properties": {"region_role": {"const": "target"}}}},
        ],
    )
    coordinate_state = strict_object(
        {
            "coordinate_space": {"enum": ["source_pixels", "working_pixels", "frame_pixels", "normalized_0_1"]},
            "width": {"type": "integer", "minimum": 1},
            "height": {"type": "integer", "minimum": 1},
        },
        ["coordinate_space", "width", "height"],
    )
    transform_parameters = {
        "oneOf": [
            strict_object({"parameter_type": {"const": "identity"}}, ["parameter_type"]),
            strict_object(
                {"parameter_type": {"const": "crop"}, "x": {"type": "integer", "minimum": 0}, "y": {"type": "integer", "minimum": 0}, "width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1}},
                ["parameter_type", "x", "y", "width", "height"],
            ),
            strict_object(
                {"parameter_type": {"const": "resize"}, "width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1}, "interpolation": {"enum": ["nearest", "bilinear", "bicubic", "lanczos", "area"]}, "rounding": {"enum": ["floor", "ceil", "half_even", "half_away_from_zero"]}, "antialias": {"type": "boolean"}},
                ["parameter_type", "width", "height", "interpolation", "rounding", "antialias"],
            ),
            strict_object(
                {"parameter_type": {"const": "pad"}, "left": {"type": "integer", "minimum": 0}, "right": {"type": "integer", "minimum": 0}, "top": {"type": "integer", "minimum": 0}, "bottom": {"type": "integer", "minimum": 0}, "mode": {"enum": ["constant", "reflect", "edge"]}, "value": {"type": ["number", "null"], "minimum": 0, "maximum": 1}},
                ["parameter_type", "left", "right", "top", "bottom", "mode", "value"],
            ),
            strict_object(
                {"parameter_type": {"const": "horizontal_flip"}, "axis": {"const": "horizontal"}, "character_side_swap": {"const": True}},
                ["parameter_type", "axis", "character_side_swap"],
            ),
            strict_object(
                {"parameter_type": {"enum": ["project", "inverse_project"]}, "matrix_3x3": {"type": "array", "items": {"type": "number"}, "minItems": 9, "maxItems": 9}, "clip_policy": {"enum": ["clip", "pad", "reject_out_of_bounds"]}, "rounding": {"enum": ["floor", "ceil", "half_even", "half_away_from_zero"]}},
                ["parameter_type", "matrix_3x3", "clip_policy", "rounding"],
            ),
        ]
    }
    transform_operation = strict_object(
        {
            "sequence": {"type": "integer", "minimum": 0},
            "operation": {"enum": ["identity", "crop", "resize", "pad", "horizontal_flip", "project", "inverse_project"]},
            "input": {"$ref": "#/$defs/coordinate_state"},
            "output": {"$ref": "#/$defs/coordinate_state"},
            "parameters": {"$ref": "#/$defs/transform_parameters"},
            "inverse_strategy": {"enum": ["exact_inverse", "reproject_with_context", "none"]},
            "step_sha256": {"$ref": "#/$defs/sha256"},
        },
        ["sequence", "operation", "input", "output", "parameters", "inverse_strategy", "step_sha256"],
    )
    transform_chain = strict_object(
        {
            "chain_id": {"$ref": "#/$defs/id"},
            "chain_sha256": {"$ref": "#/$defs/sha256"},
            "canonical_hash_profile": {"const": "main_sorted_utf8_json_v2_excluding_self_hash"},
            "source": {"$ref": "#/$defs/coordinate_state"},
            "output": {"$ref": "#/$defs/coordinate_state"},
            "steps": {"type": "array", "items": {"$ref": "#/$defs/transform_operation"}, "minItems": 1},
            "roundtrip_policy": strict_object(
                {"required": {"const": True}, "maximum_error_pixels": {"type": "number", "minimum": 0}, "reject_noninvertible": {"const": True}},
                ["required", "maximum_error_pixels", "reject_noninvertible"],
            ),
            "roundtrip_evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "minItems": 1, "uniqueItems": True},
        },
        ["chain_id", "chain_sha256", "canonical_hash_profile", "source", "output", "steps", "roundtrip_policy", "roundtrip_evidence_refs"],
    )
    signing_trust_verification = strict_object(
        {
            "signature_algorithm": {"enum": ["ed25519", "fixture_local_hash_attestation"]},
            "signing_key_id": {"$ref": "#/$defs/id"},
            "signer_role": {"enum": SIGNER_ROLES},
            "embedded_public_key_sha256": {"$ref": "#/$defs/sha256"},
            "trusted_key_registry_ref": {"$ref": "#/$defs/immutable_ref"},
            "trusted_key_entry_sha256": {"$ref": "#/$defs/sha256"},
            "trust_anchor_source": {"const": "main_out_of_band_trusted_key_registry"},
            "embedded_public_key_is_trust_anchor": {"const": False},
            "signature_verified": {"type": "boolean"},
            "trust_anchor_matched": {"type": "boolean"},
            "key_status": {"enum": ["active", "revoked", "not_found", "fixture_untrusted"]},
            "trust_result": {"enum": ["trusted", "rejected", "fixture_only_untrusted"]},
            "verified_at": {"$ref": "#/$defs/timestamp"},
            "verification_evidence_ref": {"$ref": "#/$defs/immutable_ref"},
        },
        ["signature_algorithm", "signing_key_id", "signer_role", "embedded_public_key_sha256", "trusted_key_registry_ref", "trusted_key_entry_sha256", "trust_anchor_source", "embedded_public_key_is_trust_anchor", "signature_verified", "trust_anchor_matched", "key_status", "trust_result", "verified_at", "verification_evidence_ref"],
        allOf=[
            {
                "if": {"properties": {"trust_result": {"const": "trusted"}}, "required": ["trust_result"]},
                "then": {"properties": {"signature_algorithm": {"const": "ed25519"}, "signature_verified": {"const": True}, "trust_anchor_matched": {"const": True}, "key_status": {"const": "active"}}},
            }
        ],
    )
    certificate_temporal_evaluation = strict_object(
        {
            "certificate_ref": {"$ref": "#/$defs/immutable_ref"},
            "decision_at": {"$ref": "#/$defs/timestamp"},
            "certificate_issued_at": {"$ref": "#/$defs/timestamp"},
            "certificate_expires_at": {"$ref": "#/$defs/timestamp"},
            "revocation_index_ref": {"$ref": "#/$defs/immutable_ref"},
            "revocation_index_valid_from": {"$ref": "#/$defs/timestamp"},
            "revocation_index_valid_until": {"$ref": "#/$defs/timestamp"},
            "revocation_checked_at": {"$ref": "#/$defs/timestamp"},
            "issued_not_after_decision": {"type": "boolean"},
            "decision_before_expiry": {"type": "boolean"},
            "revocation_index_current_at_decision": {"type": "boolean"},
            "certificate_not_revoked": {"type": "boolean"},
            "temporal_decision": {"enum": ["valid", "future_issued", "expired", "revoked", "stale_revocation_index"]},
        },
        ["certificate_ref", "decision_at", "certificate_issued_at", "certificate_expires_at", "revocation_index_ref", "revocation_index_valid_from", "revocation_index_valid_until", "revocation_checked_at", "issued_not_after_decision", "decision_before_expiry", "revocation_index_current_at_decision", "certificate_not_revoked", "temporal_decision"],
        allOf=[
            {
                "if": {"properties": {"temporal_decision": {"const": "valid"}}, "required": ["temporal_decision"]},
                "then": {"properties": {"issued_not_after_decision": {"const": True}, "decision_before_expiry": {"const": True}, "revocation_index_current_at_decision": {"const": True}, "certificate_not_revoked": {"const": True}}},
            }
        ],
    )
    runtime_provenance = strict_object(
        {
            "runtime_kind": {"enum": ["windows_native_venv", "linux_native_venv", "container"]},
            "operating_system": {"type": "string", "minLength": 1},
            "architecture": {"type": "string", "minLength": 1},
            "python_version": {"type": "string", "minLength": 1},
            "runtime_manifest_ref": {"$ref": "#/$defs/immutable_ref"},
            "environment_lock_sha256": {"$ref": "#/$defs/sha256"},
            "container_image_digest": {"oneOf": [{"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"}, {"type": "null"}]},
        },
        ["runtime_kind", "operating_system", "architecture", "python_version", "runtime_manifest_ref", "environment_lock_sha256", "container_image_digest"],
        allOf=[
            {"if": {"properties": {"runtime_kind": {"const": "container"}}, "required": ["runtime_kind"]}, "then": {"properties": {"container_image_digest": {"type": "string"}}}},
            {"if": {"properties": {"runtime_kind": {"enum": ["windows_native_venv", "linux_native_venv"]}}, "required": ["runtime_kind"]}, "then": {"properties": {"container_image_digest": {"type": "null"}}}},
        ],
    )
    hypothesis_binding = strict_object(
        {
            "hypothesis_id": {"$ref": "#/$defs/id"},
            "hypothesis_class": {"enum": ["initial", "geometry", "ownership", "boundary", "model_route", "prompt_control", "transform", "transport_replay"]},
            "material_change_sha256": {"oneOf": [{"$ref": "#/$defs/sha256"}, {"type": "null"}]},
            "retry_kind": {"enum": ["initial", "quality_hypothesis", "transport_replay"]},
        },
        ["hypothesis_id", "hypothesis_class", "material_change_sha256", "retry_kind"],
        allOf=[
            {"if": {"properties": {"retry_kind": {"const": "quality_hypothesis"}}, "required": ["retry_kind"]}, "then": {"properties": {"material_change_sha256": {"$ref": "#/$defs/sha256"}}}},
            {"if": {"properties": {"retry_kind": {"const": "transport_replay"}}, "required": ["retry_kind"]}, "then": {"properties": {"hypothesis_class": {"const": "transport_replay"}}}},
        ],
    )
    resource_envelope = strict_object(
        {
            "maximum_runtime_ms": {"type": "integer", "minimum": 1}, "maximum_queue_ms": {"type": "integer", "minimum": 0},
            "maximum_vram_mb": {"type": "integer", "minimum": 0}, "maximum_ram_mb": {"type": "integer", "minimum": 1},
            "maximum_output_bytes": {"type": "integer", "minimum": 1}, "priority": {"enum": ["low", "normal", "high", "critical"]},
            "allow_cpu_fallback": {"type": "boolean"},
        },
        ["maximum_runtime_ms", "maximum_queue_ms", "maximum_vram_mb", "maximum_ram_mb", "maximum_output_bytes", "priority", "allow_cpu_fallback"],
    )
    execution_observation = strict_object(
        {
            "execution_scope": {"$ref": "#/$defs/scope"}, "attempt_number": {"type": "integer", "minimum": 1}, "hypothesis": {"$ref": "#/$defs/hypothesis_binding"},
            "admitted_at": {"$ref": "#/$defs/timestamp"}, "queue_started_at": {"$ref": "#/$defs/timestamp"}, "execution_started_at": {"$ref": "#/$defs/timestamp"}, "completed_at": {"$ref": "#/$defs/timestamp"},
            "queue_ms": {"type": "integer", "minimum": 0}, "runtime_ms": {"type": "integer", "minimum": 0}, "peak_vram_mb": {"type": "integer", "minimum": 0}, "peak_ram_mb": {"type": "integer", "minimum": 0}, "output_bytes": {"type": "integer", "minimum": 0},
            "deadline_met": {"type": "boolean"}, "resource_envelope_met": {"type": "boolean"},
            "selected_route_id": {"$ref": "#/$defs/id"}, "selection_reason_code": {"$ref": "#/$defs/id"},
            "eligible_alternative_route_ids": {"type": "array", "items": {"$ref": "#/$defs/id"}, "uniqueItems": True},
            "route_selection_evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}, "minItems": 1},
            "factual_not_promotion_authority": {"const": True},
        },
        ["execution_scope", "attempt_number", "hypothesis", "admitted_at", "queue_started_at", "execution_started_at", "completed_at", "queue_ms", "runtime_ms", "peak_vram_mb", "peak_ram_mb", "output_bytes", "deadline_met", "resource_envelope_met", "selected_route_id", "selection_reason_code", "eligible_alternative_route_ids", "route_selection_evidence_refs", "factual_not_promotion_authority"],
    )
    journal_pin = strict_object(
        {
            "stream_id": {"$ref": "#/$defs/id"}, "checkpoint_ref": {"$ref": "#/$defs/immutable_ref"}, "checkpoint_sequence": {"type": "integer", "minimum": 0},
            "head_event_sha256": {"oneOf": [{"$ref": "#/$defs/sha256"}, {"type": "null"}]}, "previous_checkpoint_sha256": {"oneOf": [{"$ref": "#/$defs/sha256"}, {"type": "null"}]},
            "checkpointed_at": {"$ref": "#/$defs/timestamp"}, "fresh_until": {"$ref": "#/$defs/timestamp"},
            "checkpoint_payload_sha256": {"$ref": "#/$defs/sha256"}, "checkpoint_signature_domain": {"const": "comfy_ui_main.maskfactory_journal_checkpoint.v2"},
            "checkpoint_signature": {"type": "string", "minLength": 16},
            "checkpoint_signature_trust": {"$ref": "#/$defs/signing_trust_verification"}, "forks_allowed": {"const": False}, "deletion_or_reorder_allowed": {"const": False},
        },
        ["stream_id", "checkpoint_ref", "checkpoint_sequence", "head_event_sha256", "previous_checkpoint_sha256", "checkpointed_at", "fresh_until", "checkpoint_payload_sha256", "checkpoint_signature_domain", "checkpoint_signature", "checkpoint_signature_trust", "forks_allowed", "deletion_or_reorder_allowed"],
    )
    authority = strict_object(
        {
            "authority_state": {"enum": AUTHORITY_STATES}, "issuer_kind": {"enum": ISSUER_KINDS},
            "claim_class": {"enum": CLAIM_CLASSES},
            "certificate_ref": {"oneOf": [{"$ref": "#/$defs/immutable_ref"}, {"type": "null"}]},
            "certificate_scope": {"type": "array", "items": {"$ref": "#/$defs/id"}, "uniqueItems": True},
            "verified_at": {"$ref": "#/$defs/timestamp"}, "revocation_checked_at": {"$ref": "#/$defs/timestamp"},
        },
        ["authority_state", "issuer_kind", "claim_class", "certificate_ref", "certificate_scope", "verified_at", "revocation_checked_at"],
        allOf=[
            {
                "if": {"properties": {"authority_state": {"const": "certified"}}, "required": ["authority_state"]},
                "then": {"properties": {"certificate_ref": {"$ref": "#/$defs/immutable_ref"}, "issuer_kind": {"enum": ["maskfactory_autonomous", "human_anchor_optional"]}}, "required": ["certificate_ref", "issuer_kind"]},
            },
            {"if": {"properties": {"authority_state": {"const": "certified"}, "issuer_kind": {"const": "maskfactory_autonomous"}}, "required": ["authority_state", "issuer_kind"]}, "then": {"properties": {"claim_class": {"const": "operationally_certified_artifact"}}}},
            {"if": {"properties": {"authority_state": {"enum": ["hypothesis", "draft"]}}, "required": ["authority_state"]}, "then": {"properties": {"claim_class": {"const": "machine_candidate"}}}},
            {"if": {"properties": {"authority_state": {"const": "qa_passed_noncertified"}}, "required": ["authority_state"]}, "then": {"properties": {"claim_class": {"const": "qa_passed_machine_candidate"}}}},
        ],
    )
    parent_lineage_record = strict_object(
        {
            "parent_mask_ref": {"$ref": "#/$defs/immutable_ref"},
            "parent_authority": {"$ref": "#/$defs/authority"},
            "parent_operational_certificate_ref": {
                "oneOf": [{"$ref": "#/$defs/immutable_ref"}, {"type": "null"}]
            },
        },
        ["parent_mask_ref", "parent_authority", "parent_operational_certificate_ref"],
    )
    mask_artifact = strict_object(
        {
            "mask_ref": {"$ref": "#/$defs/immutable_ref"}, "mask_sha256": {"$ref": "#/$defs/sha256"}, "label": {"$ref": "#/$defs/id"},
            "mask_type": {"enum": ["binary", "soft", "label_map", "instance"]}, "coordinate_space": {"enum": ["source_pixels", "normalized_0_1", "working_pixels", "frame_pixels"]},
            "width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1}, "owner": {"$ref": "#/$defs/owner_binding"},
            "authority": {"$ref": "#/$defs/authority"},
            "lineage_kind": {"enum": ["original", "derived"]},
            "parents": {"type": "array", "items": {"$ref": "#/$defs/parent_lineage_record"}, "uniqueItems": True},
            "derivation_operation": {"enum": ["none", "union", "intersection", "subtract", "refine", "dilate", "erode", "feather", "crop", "project"]},
        },
        ["mask_ref", "mask_sha256", "label", "mask_type", "coordinate_space", "width", "height", "owner", "authority", "lineage_kind", "parents", "derivation_operation"],
        allOf=[
            {
                "if": {"properties": {"lineage_kind": {"const": "original"}}, "required": ["lineage_kind"]},
                "then": {"properties": {"parents": {"maxItems": 0}, "derivation_operation": {"const": "none"}}},
            },
            {
                "if": {"properties": {"lineage_kind": {"const": "derived"}}, "required": ["lineage_kind"]},
                "then": {
                    "properties": {
                        "parents": {"minItems": 1},
                        "derivation_operation": {"enum": ["union", "intersection", "subtract", "refine", "dilate", "erode", "feather", "crop", "project"]},
                    }
                },
            },
        ],
    )
    blocker = strict_object(
        {
            "code": {"$ref": "#/$defs/id"}, "category": {"enum": ["compatibility", "availability", "integrity", "ownership", "transform", "authority", "quality", "recovery", "policy"]},
            "message": {"type": "string", "minLength": 1}, "retryable": {"type": "boolean"}, "blocks_scope": {"enum": ["dependent_pass", "required_release_path", "whole_run"]},
            "completion_profile": {"enum": COMPLETION_PROFILES}, "core_impact": {"enum": ["blocking", "non_blocking"]},
            "evidence_refs": {"type": "array", "items": {"$ref": "#/$defs/immutable_ref"}},
        },
        ["code", "category", "message", "retryable", "blocks_scope", "completion_profile", "core_impact", "evidence_refs"],
        allOf=[
            {"if": {"properties": {"completion_profile": {"enum": ["independent_real_accuracy", "scale_daz_maturity"]}}, "required": ["completion_profile"]}, "then": {"properties": {"core_impact": {"const": "non_blocking"}}}},
        ],
    )
    common = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": COMMON_ID, "title": "wave64_maskfactory_bridge_common_v2",
        "$defs": {
            "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$"},
            "timestamp": {"type": "string", "format": "date-time"},
            "immutable_ref": immutable_ref, "contract_binding": contract_binding, "scope": scope, "source_artifact": source_artifact, "media_scope": media_scope,
            "owner_binding": owner_binding, "scene_owner_roster": scene_owner_roster, "input_region_binding": input_region_binding,
            "coordinate_state": coordinate_state, "transform_parameters": transform_parameters, "transform_operation": transform_operation, "transform_chain": transform_chain,
            "signing_trust_verification": signing_trust_verification, "certificate_temporal_evaluation": certificate_temporal_evaluation,
            "runtime_provenance": runtime_provenance, "hypothesis_binding": hypothesis_binding, "resource_envelope": resource_envelope,
            "execution_observation": execution_observation, "journal_pin": journal_pin, "authority": authority,
            "parent_lineage_record": parent_lineage_record, "mask_artifact": mask_artifact, "blocker": blocker,
        },
    }

    release_record = "maskfactory_release_snapshot_v2"
    release = record_schema(
        release_record,
        {
            "release_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "snapshot_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "raw_producer_release_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "release_status": {"enum": ["fixture", "published", "superseded", "revoked"]}, "published_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "release_context": {"enum": ["fixture_validation", "production_runtime"]},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "release_signature_domain": {"const": "maskfactory.sha256_digest_bytes.v1"}, "release_signature": {"type": "string", "minLength": 16},
            "normalization_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust"},
            "normalization_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "normalization_signature_domain": {"const": "comfy_ui_main.maskfactory_normalized_release.v2"},
            "normalization_signature": {"type": "string", "minLength": 16},
            "normalization_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "producer_source": strict_object({"repository_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "commit_sha": {"type": "string", "pattern": "^[a-f0-9]{40}$"}, "tag": {"$ref": f"{COMMON_ID}#/$defs/id"}, "source_clean": {"const": True}}, ["repository_id", "commit_sha", "tag", "source_clean"]),
            "contract_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/contract_binding"}, "minItems": 1, "uniqueItems": True},
            "component_bindings": {"type": "array", "items": strict_object({"component": {"$ref": f"{COMMON_ID}#/$defs/id"}, "version": {"type": "string", "minLength": 1}, "sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}}, ["component", "version", "sha256"]), "minItems": 4},
            "capability_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "certificate_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "revocation_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "artifact_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
            "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "completion_profiles": strict_object({name: {"enum": ["not_claimed", "planned", "qualified"]} for name in COMPLETION_PROFILES}, COMPLETION_PROFILES),
            "mutable_worktree_consumption_allowed": {"const": False},
        },
        ["release_id", "snapshot_sha256", "raw_producer_release_ref", "release_status", "published_at", "release_context", "genuine_runtime_evidence_refs", "release_signature_domain", "release_signature", "normalization_hash_profile", "normalization_payload_sha256", "normalization_signature_domain", "normalization_signature", "normalization_signature_trust", "producer_source", "contract_bindings", "component_bindings", "capability_refs", "certificate_refs", "revocation_refs", "artifact_refs", "signature_trust", "completion_profiles", "mutable_worktree_consumption_allowed"],
        [
            {"if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]}, "then": {"properties": {"release_status": {"const": "fixture"}, "release_context": {"const": "fixture_validation"}, "genuine_runtime_evidence_refs": {"maxItems": 0}, "runtime_completion_claimed": {"const": False}}}},
            {"if": {"properties": {"release_context": {"const": "production_runtime"}}, "required": ["release_context"]}, "then": {"properties": {"fixture_only": {"const": False}, "release_status": {"const": "published"}, "genuine_runtime_evidence_refs": {"minItems": 1}, "signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}}},
        ],
    )

    requirements_record = "maskfactory_consumer_requirements_v2"
    consumer = record_schema(
        requirements_record,
        {
            "completion_profile": {"enum": COMPLETION_PROFILES}, "required_contract_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/contract_binding"}, "minItems": 1, "uniqueItems": True},
            "supported_access_modes": {"type": "array", "items": {"enum": ACCESS_MODES}, "minItems": 1, "uniqueItems": True},
            "minimum_authority_state": {"enum": AUTHORITY_STATES}, "allowed_issuer_kinds": {"type": "array", "items": {"enum": ISSUER_KINDS}, "minItems": 1, "uniqueItems": True},
            "allowed_claim_classes": {"type": "array", "items": {"enum": CLAIM_CLASSES}, "minItems": 1, "uniqueItems": True},
            "required_certificate_scope": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
            "required_labels": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True},
            "maximum_person_count": {"type": "integer", "minimum": 1}, "required_transform_operations": {"type": "array", "items": {"enum": ["identity", "crop", "resize", "pad", "horizontal_flip", "project"]}, "minItems": 1, "uniqueItems": True},
            "maximum_latency_ms": {"type": "integer", "minimum": 1}, "human_anchor_required_for_core": {"const": False}, "scale_daz_required_for_core": {"const": False},
            "trusted_signing_key_registry_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "required_signing_key_ids": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True},
            "required_signature_algorithm": {"const": "ed25519"},
            "embedded_public_key_may_establish_trust": {"const": False},
        },
        ["completion_profile", "required_contract_bindings", "supported_access_modes", "minimum_authority_state", "allowed_issuer_kinds", "allowed_claim_classes", "required_certificate_scope", "required_labels", "maximum_person_count", "required_transform_operations", "maximum_latency_ms", "human_anchor_required_for_core", "scale_daz_required_for_core", "trusted_signing_key_registry_ref", "required_signing_key_ids", "required_signature_algorithm", "embedded_public_key_may_establish_trust"],
    )

    adoption_record = "maskfactory_adoption_receipt_v2"
    check_item = strict_object({"check": {"$ref": f"{COMMON_ID}#/$defs/id"}, "status": {"enum": ["pass", "fail", "not_applicable"]}, "expected": {"type": "string"}, "observed": {"type": "string"}, "evidence_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}}, ["check", "status", "expected", "observed", "evidence_ref"])
    use_time_certificate_evaluation = strict_object(
        {
            "certificate_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "status": {"enum": ["active", "expired", "revoked", "superseded"]},
            "issued_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "expires_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "revocation_checked_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "revocation_valid_until": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "status_evidence_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
        },
        ["certificate_ref", "status", "issued_at", "expires_at", "revocation_checked_at", "revocation_valid_until", "status_evidence_ref"],
    )
    producer_journal_checkpoint_binding = strict_object(
        {
            "source_release_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "release_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "stream_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "genesis_event_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "genesis_event_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "first_sequence": {"type": "integer", "minimum": 1}, "last_sequence": {"type": "integer", "minimum": 1},
            "event_count": {"type": "integer", "minimum": 1},
            "head_event_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "head_event_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "revocation_state_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "active_revocation_count": {"type": "integer", "minimum": 0},
            "validator_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "checkpointed_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "fresh_until": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "producer_and_main_journal_domains_are_separate": {"const": True},
        },
        [
            "source_release_ref", "release_payload_sha256", "stream_id", "genesis_event_id", "genesis_event_sha256",
            "first_sequence", "last_sequence", "event_count", "head_event_id", "head_event_sha256", "revocation_state_sha256",
            "active_revocation_count", "validator_sha256", "checkpointed_at", "fresh_until", "producer_and_main_journal_domains_are_separate",
        ],
    )
    revalidation_rule = strict_object(
        {
            "producer_reason_code": {"enum": PRODUCER_INVALIDATION_REASONS},
            "allowed_target_kinds": {"type": "array", "items": {"enum": PRODUCER_INVALIDATION_TARGET_KINDS}, "minItems": 1, "uniqueItems": True},
            "required_producer_actions": {"type": "array", "items": {"enum": PRODUCER_INVALIDATION_ACTIONS}, "minItems": 1, "uniqueItems": True},
            "main_enforcement_actions": {"type": "array", "items": {"enum": MAIN_INVALIDATION_ACTIONS}, "minItems": 1, "uniqueItems": True},
            "invalidates_active_pin": {"type": "boolean"}, "invalidates_dependent_cache": {"type": "boolean"},
            "requires_signature_reverification": {"type": "boolean"}, "requires_journal_reconciliation": {"type": "boolean"},
            "scope": {"const": "exact_affected_scope_then_dependents"}, "producer_semantics_preserved": {"const": True}, "no_silent_fallback": {"const": True},
        },
        ["producer_reason_code", "allowed_target_kinds", "required_producer_actions", "main_enforcement_actions", "invalidates_active_pin", "invalidates_dependent_cache", "requires_signature_reverification", "requires_journal_reconciliation", "scope", "producer_semantics_preserved", "no_silent_fallback"],
    )
    adoption = record_schema(
        adoption_record,
        {
            "consumer_requirements_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "decided_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "valid_until": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "use_time_recheck_required": {"const": True},
            "adoption_context": {"enum": ["fixture_validation", "production_runtime"]},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "decision": {"enum": ["adopted", "partially_adopted", "rejected"]},
            "checks": {"type": "array", "items": check_item, "minItems": len(REQUIRED_ADOPTION_CHECK_IDS), "maxItems": len(REQUIRED_ADOPTION_CHECK_IDS), "allOf": [{"contains": {"properties": {"check": {"const": check_id}}, "required": ["check"]}, "minContains": 1, "maxContains": 1} for check_id in REQUIRED_ADOPTION_CHECK_IDS]},
            "qualification_bundle_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "qualification_bundle_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "mismatch_codes": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
            "authorized_capability_ids": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
            "production_consumption_allowed": {"type": "boolean"}, "active_pin_written": {"type": "boolean"},
            "trusted_signing_key_registry_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "release_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "capability_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "capability_snapshot_status": {"enum": ["current", "superseded", "revoked", "expired"]},
            "capability_observed_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "capability_valid_until": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "capability_revocation_checked_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "capability_revocation_valid_until": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "capability_status_evidence_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "operational_certificate_evaluations": {"type": "array", "items": use_time_certificate_evaluation, "uniqueItems": True},
            "producer_journal_checkpoint_binding": producer_journal_checkpoint_binding,
            "journal_pin": {"$ref": f"{COMMON_ID}#/$defs/journal_pin"},
            "adoption_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_receipt_hash_signature_and_signature_trust"},
            "adoption_receipt_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "adoption_signature_domain": {"const": "comfy_ui_main.maskfactory_adoption_receipt.v2"}, "adoption_signature": {"type": "string", "minLength": 16},
            "adoption_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "all_required_signatures_trusted": {"type": "boolean"},
            "producer_invalidation_policy_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "producer_invalidation_policy_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "revalidation_triggers": {"type": "array", "items": {"enum": PRODUCER_INVALIDATION_REASONS}, "minItems": len(PRODUCER_INVALIDATION_REASONS), "maxItems": len(PRODUCER_INVALIDATION_REASONS), "uniqueItems": True},
            "revalidation_rules": {"type": "array", "items": revalidation_rule, "minItems": len(PRODUCER_INVALIDATION_REASONS), "maxItems": len(PRODUCER_INVALIDATION_REASONS), "allOf": [{"contains": {"properties": {"producer_reason_code": {"const": reason}}, "required": ["producer_reason_code"]}, "minContains": 1, "maxContains": 1} for reason in PRODUCER_INVALIDATION_REASONS]},
        },
        ["consumer_requirements_ref", "release_snapshot_ref", "decided_at", "valid_until", "use_time_recheck_required", "adoption_context", "genuine_runtime_evidence_refs", "decision", "checks", "qualification_bundle_ref", "qualification_bundle_sha256", "mismatch_codes", "authorized_capability_ids", "production_consumption_allowed", "active_pin_written", "trusted_signing_key_registry_ref", "release_signature_trust", "capability_snapshot_ref", "capability_snapshot_status", "capability_observed_at", "capability_valid_until", "capability_revocation_checked_at", "capability_revocation_valid_until", "capability_status_evidence_ref", "operational_certificate_evaluations", "producer_journal_checkpoint_binding", "journal_pin", "adoption_hash_profile", "adoption_receipt_sha256", "adoption_signature_domain", "adoption_signature", "adoption_signature_trust", "all_required_signatures_trusted", "producer_invalidation_policy_ref", "producer_invalidation_policy_sha256", "revalidation_triggers", "revalidation_rules"],
        [
            {"if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]}, "then": {"properties": {"adoption_context": {"const": "fixture_validation"}, "genuine_runtime_evidence_refs": {"maxItems": 0}, "production_consumption_allowed": {"const": False}, "active_pin_written": {"const": False}, "runtime_completion_claimed": {"const": False}}}},
            {
                "if": {"properties": {"production_consumption_allowed": {"const": True}}, "required": ["production_consumption_allowed"]},
                "then": {
                    "properties": {
                        "fixture_only": {"const": False}, "adoption_context": {"const": "production_runtime"},
                        "genuine_runtime_evidence_refs": {"minItems": 1}, "decision": {"const": "adopted"},
                        "mismatch_codes": {"maxItems": 0}, "active_pin_written": {"const": True},
                        "capability_snapshot_status": {"const": "current"},
                        "all_required_signatures_trusted": {"const": True},
                        "release_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}},
                        "adoption_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}},
                        "journal_pin": {"properties": {"checkpoint_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}},
                    }
                },
            },
            {"if": {"properties": {"active_pin_written": {"const": True}}, "required": ["active_pin_written"]}, "then": {"properties": {"production_consumption_allowed": {"const": True}}}},
        ],
    )

    request_record = "maskfactory_bridge_request_v2"
    intent_item = strict_object({"intent_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "label": {"$ref": f"{COMMON_ID}#/$defs/id"}, "purpose": {"enum": ["target_edit", "protect", "identity_isolation", "pose_control", "video_tracking", "qa"]}, "mask_type": {"enum": ["binary", "soft", "label_map", "instance"]}}, ["intent_id", "label", "purpose", "mask_type"])
    request = record_schema(
        request_record,
        {
            "correlation_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "idempotency_key": {"$ref": f"{COMMON_ID}#/$defs/id"}, "scope": {"$ref": f"{COMMON_ID}#/$defs/scope"},
            "attempt_number": {"type": "integer", "minimum": 1}, "hypothesis": {"$ref": f"{COMMON_ID}#/$defs/hypothesis_binding"},
            "access_mode": {"enum": ACCESS_MODES}, "source_artifact": {"$ref": f"{COMMON_ID}#/$defs/source_artifact"}, "media_scope": {"$ref": f"{COMMON_ID}#/$defs/media_scope"},
            "owner_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/owner_binding"}, "minItems": 1},
            "scene_owner_roster": {"$ref": f"{COMMON_ID}#/$defs/scene_owner_roster"},
            "target_region_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/input_region_binding"}, "minItems": 1},
            "protected_region_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/input_region_binding"}},
            "mask_intents": {"type": "array", "items": intent_item, "minItems": 1}, "transform_chain": {"$ref": f"{COMMON_ID}#/$defs/transform_chain"},
            "roundtrip_tolerance_pixels": {"type": "number", "minimum": 0}, "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "expected_contract_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/contract_binding"}, "minItems": 1},
            "minimum_authority_state": {"enum": AUTHORITY_STATES}, "accepted_issuer_kinds": {"type": "array", "items": {"enum": ISSUER_KINDS}, "minItems": 1, "uniqueItems": True},
            "accepted_claim_classes": {"type": "array", "items": {"enum": CLAIM_CLASSES}, "minItems": 1, "uniqueItems": True},
            "required_certificate_scope": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
            "intended_use": {"enum": ["diagnostic", "preview", "repair", "promotion_bound"]}, "deadline_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "retry_class": {"enum": ["none", "transport_only", "bounded_quality_repair"]}, "resource_envelope": {"$ref": f"{COMMON_ID}#/$defs/resource_envelope"}, "production_promotion_requested": {"type": "boolean"},
        },
        ["correlation_id", "idempotency_key", "scope", "attempt_number", "hypothesis", "access_mode", "source_artifact", "media_scope", "owner_bindings", "scene_owner_roster", "target_region_bindings", "protected_region_bindings", "mask_intents", "transform_chain", "roundtrip_tolerance_pixels", "release_snapshot_ref", "expected_contract_bindings", "minimum_authority_state", "accepted_issuer_kinds", "accepted_claim_classes", "required_certificate_scope", "intended_use", "deadline_at", "retry_class", "resource_envelope", "production_promotion_requested"],
    )

    certificate_record = "maskfactory_operational_certificate_v2"
    qa_binding = strict_object({"qa_record_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "gate_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "result": {"const": "pass"}}, ["qa_record_ref", "gate_id", "result"])
    operational_certificate = record_schema(
        certificate_record,
        {
            "certification_context": {"enum": ["fixture_validation", "production_runtime"]},
            "claim_class": {"const": "operationally_certified_artifact"},
            "status": {"enum": ["active", "expired", "revoked"]}, "issuer_kind": {"enum": ["maskfactory_autonomous", "human_anchor_optional"]},
            "issuer_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "signature_algorithm": {"enum": ["ed25519", "ecdsa_p256_sha256", "local_hash_attestation"]},
            "raw_producer_certificate_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "raw_producer_certificate_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "raw_producer_certificate_signature_domain": {"const": "maskfactory.sha256_digest_bytes.v1"},
            "raw_producer_certificate_signature": {"type": "string", "minLength": 16},
            "raw_producer_certificate_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "certificate_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_certificate_hash_signature_and_signature_trust"},
            "certificate_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "signature_domain": {"const": "comfy_ui_main.maskfactory_operational_certificate.v2"},
            "signature": {"type": "string", "minLength": 16}, "issued_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "expires_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "capability_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "serving_route_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "access_mode": {"enum": ACCESS_MODES},
            "execution_stack_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "runtime_provenance": {"$ref": f"{COMMON_ID}#/$defs/runtime_provenance"}, "source_artifact": {"$ref": f"{COMMON_ID}#/$defs/source_artifact"}, "media_scope": {"$ref": f"{COMMON_ID}#/$defs/media_scope"},
            "output_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1}, "owner_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/owner_binding"}, "minItems": 1},
            "transform_chain": {"$ref": f"{COMMON_ID}#/$defs/transform_chain"}, "qa_bindings": {"type": "array", "items": qa_binding, "minItems": 1},
            "promotion_gate_policy_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "evidence_manifest_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "certificate_scope": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True}, "revocation_manifest_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1}, "revocation_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
        },
        ["certification_context", "claim_class", "status", "issuer_kind", "issuer_id", "signature_algorithm", "raw_producer_certificate_ref", "raw_producer_certificate_payload_sha256", "raw_producer_certificate_signature_domain", "raw_producer_certificate_signature", "raw_producer_certificate_signature_trust", "certificate_hash_profile", "certificate_payload_sha256", "signature_domain", "signature", "signature_trust", "issued_at", "expires_at", "release_snapshot_ref", "capability_id", "serving_route_id", "access_mode", "execution_stack_ref", "runtime_provenance", "source_artifact", "media_scope", "output_refs", "owner_bindings", "transform_chain", "qa_bindings", "promotion_gate_policy_ref", "evidence_manifest_refs", "genuine_runtime_evidence_refs", "certificate_scope", "revocation_manifest_refs", "revocation_ref"],
        [
            {
                "if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]},
                "then": {"properties": {"certification_context": {"const": "fixture_validation"}, "genuine_runtime_evidence_refs": {"maxItems": 0}, "runtime_completion_claimed": {"const": False}}},
            },
            {
                "if": {"properties": {"certification_context": {"const": "production_runtime"}}, "required": ["certification_context"]},
                "then": {"properties": {"fixture_only": {"const": False}, "genuine_runtime_evidence_refs": {"minItems": 1}, "runtime_completion_claimed": {"const": False}, "signature_algorithm": {"const": "ed25519"}, "signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}},
            },
        ],
    )

    promotion_record = "maskfactory_promotion_gate_policy_v2"
    promotion_criterion = strict_object(
        {
            "criterion_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "dimension": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "comparator": {"enum": ["gte", "lte", "eq", "boolean_true", "no_blockers"]}, "threshold": {"type": ["number", "integer", "boolean", "string"]},
            "evidence_type": {"$ref": f"{COMMON_ID}#/$defs/id"}, "analyzer_manifest_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "blocking": {"const": True},
        },
        ["criterion_id", "dimension", "comparator", "threshold", "evidence_type", "analyzer_manifest_ref", "blocking"],
    )
    promotion_policy = record_schema(
        promotion_record,
        {
            "policy_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"}, "policy_context": {"enum": ["fixture_validation", "production_runtime"]}, "completion_profile": {"const": "core_autonomous_runtime"},
            "policy_artifact_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "policy_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "policy_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_policy_hash_signature_signature_trust_and_artifact_ref_hash"},
            "signature_domain": {"const": "comfy_ui_main.maskfactory_promotion_gate_policy.v2"},
            "signature": {"type": "string", "minLength": 16},
            "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "criteria": {"type": "array", "items": promotion_criterion, "minItems": 1}, "evidence_manifest_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "revocation_manifest_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
            "live_qa_strictness_control_authoritative": {"const": False}, "runtime_policy_mutable_from_app": {"const": False},
            "optional_independent_accuracy_can_mutate_core_decision": {"const": False}, "legacy_string_gate_authoritative": {"const": False},
        },
        ["policy_version", "policy_context", "completion_profile", "policy_artifact_ref", "policy_sha256", "policy_hash_profile", "signature_domain", "signature", "signature_trust", "criteria", "evidence_manifest_refs", "genuine_runtime_evidence_refs", "revocation_manifest_refs", "live_qa_strictness_control_authoritative", "runtime_policy_mutable_from_app", "optional_independent_accuracy_can_mutate_core_decision", "legacy_string_gate_authoritative"],
        [
            {"if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]}, "then": {"properties": {"policy_context": {"const": "fixture_validation"}, "genuine_runtime_evidence_refs": {"maxItems": 0}}}},
            {"if": {"properties": {"policy_context": {"const": "production_runtime"}}, "required": ["policy_context"]}, "then": {"properties": {"fixture_only": {"const": False}, "genuine_runtime_evidence_refs": {"minItems": 1}, "signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}}},
        ],
    )

    result_record = "maskfactory_bridge_result_v2"
    result = record_schema(
        result_record,
        {
            "request_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "access_mode": {"enum": ACCESS_MODES},
            "raw_producer_receipt_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "raw_producer_receipt_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "raw_producer_receipt_signature_domain": {"const": "maskfactory.mask_acquisition_receipt.v1"},
            "raw_producer_receipt_signature": {"type": "string", "minLength": 16},
            "raw_producer_receipt_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "normalization_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust"},
            "normalization_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "normalization_signature_domain": {"const": "comfy_ui_main.maskfactory_normalized_result.v2"},
            "normalization_signature": {"type": "string", "minLength": 16},
            "normalization_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "status": {"enum": ["succeeded", "blocked", "error"]}, "source_artifact": {"$ref": f"{COMMON_ID}#/$defs/source_artifact"}, "media_scope": {"$ref": f"{COMMON_ID}#/$defs/media_scope"},
            "route_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "execution_stack_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "owner_bindings": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/owner_binding"}, "minItems": 1}, "transform_chain": {"$ref": f"{COMMON_ID}#/$defs/transform_chain"},
            "input_region_lineage": strict_object(
                {
                    "target_region_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
                    "protected_region_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
                    "request_transform_chain_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
                    "input_roi_hashes_are_output_artifact_hashes": {"type": "boolean"},
                    "mode_a_exact_selector_exception_applied": {"type": "boolean"},
                },
                ["target_region_refs", "protected_region_refs", "request_transform_chain_sha256", "input_roi_hashes_are_output_artifact_hashes", "mode_a_exact_selector_exception_applied"],
            ),
            "execution_observation": {"$ref": f"{COMMON_ID}#/$defs/execution_observation"},
            "roundtrip_max_error_pixels": {"type": "number", "minimum": 0}, "authority": {"$ref": f"{COMMON_ID}#/$defs/authority"},
            "authority_aggregation_rule": {"const": "minimum_of_all_mask_authorities"},
            "operational_certificate_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "masks": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/mask_artifact"}}, "qa_record_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}}, "cache_state": {"enum": ["not_cached", "fresh_hit", "fresh_written", "invalidated", "bypassed"]},
        },
        ["request_ref", "release_snapshot_ref", "access_mode", "raw_producer_receipt_ref", "raw_producer_receipt_payload_sha256", "raw_producer_receipt_signature_domain", "raw_producer_receipt_signature", "raw_producer_receipt_signature_trust", "normalization_hash_profile", "normalization_payload_sha256", "normalization_signature_domain", "normalization_signature", "normalization_signature_trust", "status", "source_artifact", "media_scope", "route_id", "execution_stack_ref", "owner_bindings", "transform_chain", "input_region_lineage", "execution_observation", "roundtrip_max_error_pixels", "authority", "authority_aggregation_rule", "operational_certificate_ref", "masks", "qa_record_refs", "blockers", "cache_state"],
        [
            {
                "if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]},
                "then": {"properties": {"authority": {"properties": {"authority_state": {"not": {"const": "certified"}}}}, "operational_certificate_ref": {"type": "null"}}},
            },
            {
                "if": {"properties": {"status": {"const": "succeeded"}}, "required": ["status"]},
                "then": {"properties": {"masks": {"minItems": 1}, "blockers": {"maxItems": 0}, "execution_observation": {"properties": {"deadline_met": {"const": True}, "resource_envelope_met": {"const": True}}}}},
            },
            {
                "if": {"properties": {"status": {"enum": ["blocked", "error"]}}, "required": ["status"]},
                "then": {"properties": {"blockers": {"minItems": 1}, "masks": {"maxItems": 0}, "operational_certificate_ref": {"type": "null"}, "authority": {"properties": {"authority_state": {"enum": ["invalid", "hypothesis", "draft", "qa_passed_noncertified"]}}}}},
            },
            {
                "if": {"properties": {"authority": {"properties": {"authority_state": {"const": "certified"}}, "required": ["authority_state"]}}, "required": ["authority"]},
                "then": {"properties": {"operational_certificate_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}}, "required": ["operational_certificate_ref"]},
            },
        ],
    )

    authority_record = "maskfactory_authority_decision_v2"
    authority_decision = record_schema(
        authority_record,
        {
            "result_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "access_mode": {"enum": ACCESS_MODES}, "observed_authority": {"$ref": f"{COMMON_ID}#/$defs/authority"},
            "required_authority_state": {"enum": AUTHORITY_STATES}, "required_issuer_kinds": {"type": "array", "items": {"enum": ISSUER_KINDS}, "minItems": 1, "uniqueItems": True},
            "required_claim_classes": {"type": "array", "items": {"enum": CLAIM_CLASSES}, "minItems": 1, "uniqueItems": True},
            "required_certificate_scope": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
            "intended_use": {"enum": ["diagnostic", "preview", "repair", "promotion_bound"]}, "decision": {"enum": ["eligible", "diagnostic_only", "blocked"]}, "eligible_for_intended_use": {"type": "boolean"},
            "decision_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "certificate_temporal_evaluation": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/certificate_temporal_evaluation"}, {"type": "null"}]},
            "certificate_signature_trust": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"}, {"type": "null"}]},
            "decision_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "consumer_policy_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "consumer_policy_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "criterion_evaluations": {"type": "array", "items": strict_object({"criterion_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "comparator": {"enum": ["gte", "lte", "eq", "boolean_true", "no_blockers"]}, "threshold": {"type": ["number", "integer", "boolean", "string"]}, "observed": {"type": ["number", "integer", "boolean", "string"]}, "status": {"enum": ["pass", "fail", "blocked"]}, "evidence_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}}, ["criterion_id", "comparator", "threshold", "observed", "status", "evidence_ref"]), "minItems": 1},
            "crosswalk_rule_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}},
        },
        ["result_ref", "access_mode", "observed_authority", "required_authority_state", "required_issuer_kinds", "required_claim_classes", "required_certificate_scope", "intended_use", "decision", "eligible_for_intended_use", "decision_at", "certificate_temporal_evaluation", "certificate_signature_trust", "decision_evidence_refs", "genuine_runtime_evidence_refs", "consumer_policy_ref", "consumer_policy_sha256", "criterion_evaluations", "crosswalk_rule_id", "blockers"],
        [
            {
                "if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]},
                "then": {
                    "properties": {
                        "eligible_for_intended_use": {"const": False}, "decision": {"enum": ["diagnostic_only", "blocked"]},
                        "intended_use": {"not": {"const": "promotion_bound"}},
                        "observed_authority": {"properties": {"authority_state": {"not": {"const": "certified"}}}},
                        "genuine_runtime_evidence_refs": {"maxItems": 0},
                    }
                },
            },
            {
                "if": {"properties": {"eligible_for_intended_use": {"const": True}}, "required": ["eligible_for_intended_use"]},
                "then": {
                    "properties": {
                        "decision": {"const": "eligible"},
                        "criterion_evaluations": {"items": {"properties": {"status": {"const": "pass"}}}},
                        "genuine_runtime_evidence_refs": {"minItems": 1},
                        "blockers": {"maxItems": 0},
                    }
                },
            },
            {"if": {"properties": {"decision": {"const": "eligible"}}, "required": ["decision"]}, "then": {"properties": {"eligible_for_intended_use": {"const": True}}}},
            {"if": {"properties": {"decision": {"enum": ["diagnostic_only", "blocked"]}}, "required": ["decision"]}, "then": {"properties": {"eligible_for_intended_use": {"const": False}}}},
            {
                "if": {"properties": {"eligible_for_intended_use": {"const": True}, "required_authority_state": {"const": "certified"}}, "required": ["eligible_for_intended_use", "required_authority_state"]},
                "then": {"properties": {"certificate_temporal_evaluation": {"$ref": f"{COMMON_ID}#/$defs/certificate_temporal_evaluation", "properties": {"temporal_decision": {"const": "valid"}}}, "certificate_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification", "properties": {"trust_result": {"const": "trusted"}}}}},
            },
        ],
    )

    health_record = "maskfactory_health_capability_snapshot_v2"
    route_capability = strict_object(
        {"route_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "access_mode": {"enum": ACCESS_MODES}, "status": {"enum": ["available", "degraded", "unavailable", "unqualified"]}, "default_authority_state": {"enum": AUTHORITY_STATES}, "maximum_authority_state": {"enum": AUTHORITY_STATES}, "operational_certificate_required_above_default": {"const": True}, "supported_labels": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True}, "execution_stack_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]}},
        ["route_id", "access_mode", "status", "default_authority_state", "maximum_authority_state", "operational_certificate_required_above_default", "supported_labels", "execution_stack_ref"],
    )
    health = record_schema(
        health_record,
        {"release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "service_status": {"enum": ["healthy", "degraded", "offline", "unknown"]}, "observed_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "expires_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "api_contract": {"$ref": f"{COMMON_ID}#/$defs/contract_binding"}, "routes": {"type": "array", "items": route_capability, "minItems": 1}, "current_mode_b_default_authority_state": {"const": "draft"}},
        ["release_snapshot_ref", "service_status", "observed_at", "expires_at", "api_contract", "routes", "current_mode_b_default_authority_state"],
    )

    invalidation_record = "maskfactory_invalidation_event_v2"
    invalidation_transition = strict_object(
        {
            "transition_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "target_kind": {"enum": PRODUCER_INVALIDATION_TARGET_KINDS},
            "target_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "target_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "previous_authority_state": {"enum": AUTHORITY_STATES}, "new_authority_state": {"enum": ["invalid", "hypothesis", "draft", "qa_passed_noncertified"]},
            "previous_certificate_status": {"enum": ["active", "expired", "revoked", "superseded", "none"]},
            "new_certificate_status": {"enum": ["expired", "revoked", "superseded", "none"]},
            "reason_code": {"$ref": f"{COMMON_ID}#/$defs/id"}, "scope_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "main_target_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "unrelated_scope_preserved": {"const": True},
        },
        ["transition_id", "target_kind", "target_id", "target_sha256", "previous_authority_state", "new_authority_state", "previous_certificate_status", "new_certificate_status", "reason_code", "scope_sha256", "main_target_ref", "unrelated_scope_preserved"],
    )
    producer_required_action = strict_object(
        {
            "action_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "transition_ids": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True},
            "action": {"enum": PRODUCER_INVALIDATION_ACTIONS}, "deadline_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "verification_evidence_required": {"const": True}, "verification_policy_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
        },
        ["action_id", "transition_ids", "action", "deadline_at", "verification_evidence_required", "verification_policy_sha256"],
    )
    superseding_binding = strict_object(
        {"release_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "release_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "adoption_required": {"const": True}},
        ["release_id", "release_payload_sha256", "adoption_required"],
    )
    rollback_binding = strict_object(
        {"rollback_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "rollback_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "target_release_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "target_release_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}},
        ["rollback_id", "rollback_sha256", "target_release_id", "target_release_payload_sha256"],
    )
    invalidation = record_schema(
        invalidation_record,
        {
            "stream_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "event_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "sequence": {"type": "integer", "minimum": 1}, "correlation_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "causation_id": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/id"}, {"type": "null"}]}, "idempotency_key": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "occurred_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "reason": {"enum": PRODUCER_INVALIDATION_REASONS},
            "producer_identity": {"$ref": f"{COMMON_ID}#/$defs/id"}, "severity": {"const": "blocking"},
            "producer_evidence_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "producer_signature_domain": {"const": "maskfactory.sha256_digest_bytes.v1"}, "producer_signature": {"type": "string", "minLength": 16},
            "producer_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
            "producer_payload_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "producer_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "producer_payload_preserved_losslessly": {"const": True},
            "producer_invalidation_policy_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "producer_invalidation_policy_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "target_transitions": {"type": "array", "items": invalidation_transition, "minItems": 1},
            "affected_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1, "uniqueItems": True},
            "required_actions": {"type": "array", "items": producer_required_action, "minItems": 1},
            "main_enforcement_actions": {"type": "array", "items": {"enum": MAIN_INVALIDATION_ACTIONS}, "minItems": 1, "uniqueItems": True},
            "effective_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "supersedes_invalidation_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "superseding_binding": {"oneOf": [superseding_binding, {"type": "null"}]}, "rollback_binding": {"oneOf": [rollback_binding, {"type": "null"}]},
            "dependent_pass_only_by_default": {"const": True}, "tombstone_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "invalidation_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_invalidation_hash_normalization_signature_and_trust_records"},
            "invalidation_event_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "normalization_signature_domain": {"const": "comfy_ui_main.maskfactory_invalidation_event.v2"},
            "normalization_signature": {"type": "string", "minLength": 16},
            "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
        },
        ["stream_id", "event_id", "sequence", "correlation_id", "causation_id", "idempotency_key", "occurred_at", "reason", "producer_identity", "severity", "producer_evidence_sha256", "producer_signature_domain", "producer_signature", "producer_signature_trust", "producer_payload_ref", "producer_payload_sha256", "producer_payload_preserved_losslessly", "producer_invalidation_policy_ref", "producer_invalidation_policy_sha256", "target_transitions", "affected_refs", "required_actions", "main_enforcement_actions", "effective_at", "supersedes_invalidation_ref", "superseding_binding", "rollback_binding", "dependent_pass_only_by_default", "tombstone_sha256", "invalidation_hash_profile", "invalidation_event_sha256", "normalization_signature_domain", "normalization_signature", "signature_trust"],
        [
            {"if": {"properties": {"reason": {"const": "release_superseded"}}, "required": ["reason"]}, "then": {"properties": {"superseding_binding": superseding_binding}}},
            {"if": {"properties": {"reason": {"not": {"const": "release_superseded"}}}, "required": ["reason"]}, "then": {"properties": {"superseding_binding": {"type": "null"}}}},
            {"if": {"properties": {"supersedes_invalidation_ref": {"type": "object"}}, "required": ["supersedes_invalidation_ref"]}, "then": {"properties": {"sequence": {"minimum": 2}, "causation_id": {"$ref": f"{COMMON_ID}#/$defs/id"}}}},
        ],
    )

    event_record = "maskfactory_bridge_event_v2"
    reconciliation_outcome = strict_object(
        {
            "outcome": {"enum": ["found_running", "found_completed_pending_receipt", "found_failed", "not_found_safe_to_submit"]},
            "remote_execution_id": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/id"}, {"type": "null"}]},
            "remote_execution_sha256": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/sha256"}, {"type": "null"}]},
            "remote_status": {"enum": ["running", "completed", "failed", "not_found"]},
            "remote_result_sha256": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/sha256"}, {"type": "null"}]},
            "checked_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "not_found_evidence_sha256": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/sha256"}, {"type": "null"}]},
            "reconciliation_evidence_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "resubmission_authorized": {"type": "boolean"},
        },
        ["outcome", "remote_execution_id", "remote_execution_sha256", "remote_status", "remote_result_sha256", "checked_at", "not_found_evidence_sha256", "reconciliation_evidence_ref", "resubmission_authorized"],
    )
    execution_transition = strict_object(
        {
            "from_state": {"enum": EXECUTION_STATES}, "to_state": {"enum": EXECUTION_STATES},
            "transition_reason_code": {"$ref": f"{COMMON_ID}#/$defs/id"}, "request_payload_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
            "reconciliation_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "remote_receipt_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "reconciliation": {"oneOf": [reconciliation_outcome, {"type": "null"}]},
            "resubmission_authorization_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "resubmission_authorization_consumed": {"type": "boolean"},
        },
        ["from_state", "to_state", "transition_reason_code", "request_payload_sha256", "reconciliation_ref", "remote_receipt_ref", "reconciliation", "resubmission_authorization_ref", "resubmission_authorization_consumed"],
    )
    lifecycle_event_types = ["request_admitted", "submission_started", "submission_resubmitted_after_signed_not_found", "submission_accepted", "execution_running", "submission_outcome_unknown", "submission_reconciled_found_running", "submission_reconciled_found_completed_pending_receipt", "submission_reconciled_found_failed", "submission_reconciled_not_found_safe_to_submit", "receipt_committed", "execution_succeeded", "execution_failed", "execution_cancelled"]
    bridge_event = record_schema(
        event_record,
        {
            "stream_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "sequence": {"type": "integer", "minimum": 1}, "correlation_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "causation_id": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/id"}, {"type": "null"}]},
            "event_type": {"enum": [*lifecycle_event_types, "route_selected", "result_received", "validation_passed", "validation_failed", "authority_verified", "cache_written", "invalidation_applied", "repair_requested", "incident_opened", "policy_decided"]},
            "aggregate_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "payload_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "idempotency_key": {"$ref": f"{COMMON_ID}#/$defs/id"}, "previous_event_sha256": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/sha256"}, {"type": "null"}]},
            "lifecycle_transition": {"oneOf": [execution_transition, {"type": "null"}]},
            "event_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_event_hash_signature_trust_and_pin"},
            "signature_domain": {"const": "comfy_ui_main.maskfactory_bridge_event.v2"},
            "event_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "signature": {"type": "string", "minLength": 16},
            "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"}, "journal_pin": {"$ref": f"{COMMON_ID}#/$defs/journal_pin"}, "authoritative_for_maskfactory_truth": {"const": False},
        },
        ["stream_id", "sequence", "correlation_id", "causation_id", "event_type", "aggregate_ref", "payload_ref", "idempotency_key", "previous_event_sha256", "lifecycle_transition", "event_hash_profile", "signature_domain", "event_sha256", "signature", "signature_trust", "journal_pin", "authoritative_for_maskfactory_truth"],
        [
            {"if": {"properties": {"event_type": {"enum": lifecycle_event_types}}, "required": ["event_type"]}, "then": {"properties": {"lifecycle_transition": execution_transition}}},
            {"if": {"properties": {"event_type": {"not": {"enum": lifecycle_event_types}}}, "required": ["event_type"]}, "then": {"properties": {"lifecycle_transition": {"type": "null"}}}},
        ],
    )

    feedback_record = "maskfactory_feedback_repair_request_v2"
    feedback = record_schema(
        feedback_record,
        {"source_result_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "source_artifact": {"$ref": f"{COMMON_ID}#/$defs/source_artifact"}, "affected_mask_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1}, "defect_codes": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True}, "localized_region_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "qa_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1}, "requested_action": {"enum": ["review", "re_predict", "refine", "requalify_route", "issue_invalidation"]}, "hypothesis_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "direct_gold_mutation_requested": {"const": False}, "authority_change_requested": {"const": False}, "response_expected_via_release_or_event": {"const": True}},
        ["source_result_ref", "source_artifact", "affected_mask_refs", "defect_codes", "localized_region_ref", "qa_evidence_refs", "requested_action", "hypothesis_id", "direct_gold_mutation_requested", "authority_change_requested", "response_expected_via_release_or_event"],
    )

    integration_record = "maskfactory_bridge_release_certificate_v2"
    release_check = strict_object(
        {
            "gate_id": {"enum": REQUIRED_BRIDGE_RELEASE_GATE_IDS}, "status": {"enum": ["pass", "fail", "blocked"]}, "derived_pass": {"type": "boolean"},
            "subject_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "gate_report_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "gate_report_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "evaluator_manifest_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "gate_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_gate_hash_signature_and_signature_trust"},
            "signature_domain": {"const": "comfy_ui_main.maskfactory_bridge_release_gate_report.v2"}, "gate_report_signature": {"type": "string", "minLength": 16},
            "evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "minItems": 1, "uniqueItems": True},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "evaluated_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"}, "signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"},
        },
        ["gate_id", "status", "derived_pass", "subject_ref", "gate_report_ref", "gate_report_sha256", "evaluator_manifest_ref", "gate_hash_profile", "signature_domain", "gate_report_signature", "evidence_refs", "genuine_runtime_evidence_refs", "evaluated_at", "signature_trust"],
        allOf=[
            {"if": {"properties": {"status": {"const": "pass"}}, "required": ["status"]}, "then": {"properties": {"derived_pass": {"const": True}}}},
            {"if": {"properties": {"status": {"enum": ["fail", "blocked"]}}, "required": ["status"]}, "then": {"properties": {"derived_pass": {"const": False}}}},
        ],
    )
    release_checks = {
        "type": "array", "items": release_check, "minItems": len(REQUIRED_BRIDGE_RELEASE_GATE_IDS), "maxItems": len(REQUIRED_BRIDGE_RELEASE_GATE_IDS),
        "allOf": [{"contains": {"properties": {"gate_id": {"const": gate_id}}, "required": ["gate_id"]}, "minContains": 1, "maxContains": 1} for gate_id in REQUIRED_BRIDGE_RELEASE_GATE_IDS],
    }
    integration = record_schema(
        integration_record,
        {"runtime_completion_claimed": {"type": "boolean"}, "completion_profile": {"const": "core_autonomous_runtime"}, "release_context": {"enum": ["fixture_validation", "production_runtime"]}, "status": {"enum": ["released", "blocked"]}, "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "adoption_receipt_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "row218_runtime_passed": {"type": "boolean"}, "rows321_347_runtime_passed": {"type": "boolean"}, "trusted_signing_identity_checks_passed": {"type": "boolean"}, "journal_checkpoint_checks_passed": {"type": "boolean"}, "journal_pin": {"$ref": f"{COMMON_ID}#/$defs/journal_pin"}, "checks": release_checks, "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True}, "release_allowed": {"type": "boolean"}, "release_hash_profile": {"const": "main_domain_separated_sorted_utf8_json_v2_excluding_release_certificate_hash_signature_and_signature_trust"}, "release_certificate_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"}, "release_signature_domain": {"const": "comfy_ui_main.maskfactory_bridge_release_certificate.v2"}, "release_signature": {"type": "string", "minLength": 16}, "release_signature_trust": {"$ref": f"{COMMON_ID}#/$defs/signing_trust_verification"}, "independent_real_accuracy_required": {"const": False}, "scale_daz_maturity_required": {"const": False}},
        ["completion_profile", "release_context", "status", "release_snapshot_ref", "adoption_receipt_ref", "row218_runtime_passed", "rows321_347_runtime_passed", "trusted_signing_identity_checks_passed", "journal_checkpoint_checks_passed", "journal_pin", "checks", "genuine_runtime_evidence_refs", "release_allowed", "release_hash_profile", "release_certificate_sha256", "release_signature_domain", "release_signature", "release_signature_trust", "independent_real_accuracy_required", "scale_daz_maturity_required"],
        [
            {"if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]}, "then": {"properties": {"release_context": {"const": "fixture_validation"}, "genuine_runtime_evidence_refs": {"maxItems": 0}, "release_allowed": {"const": False}, "status": {"const": "blocked"}, "runtime_completion_claimed": {"const": False}}}},
            {"if": {"properties": {"release_allowed": {"const": True}}, "required": ["release_allowed"]}, "then": {"properties": {"release_context": {"const": "production_runtime"}, "fixture_only": {"const": False}, "runtime_completion_claimed": {"const": True}, "genuine_runtime_evidence_refs": {"minItems": 1}, "status": {"const": "released"}, "row218_runtime_passed": {"const": True}, "rows321_347_runtime_passed": {"const": True}, "trusted_signing_identity_checks_passed": {"const": True}, "journal_checkpoint_checks_passed": {"const": True}, "release_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}, "journal_pin": {"properties": {"checkpoint_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}}, "checks": {"items": {"properties": {"status": {"const": "pass"}, "derived_pass": {"const": True}, "genuine_runtime_evidence_refs": {"minItems": 1}, "signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}}}}}},
            {"if": {"properties": {"status": {"const": "released"}}, "required": ["status"]}, "then": {"properties": {"release_allowed": {"const": True}}}},
        ],
    )

    readiness_record = "maskfactory_bridge_readiness_projection_v2"
    readiness_profile = strict_object(
        {
            "completion_profile": {"enum": COMPLETION_PROFILES},
            "required_for_core_release": {"type": "boolean"},
            "status": {"enum": ["not_started", "planned", "blocked", "ready"]},
            "evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}},
        },
        ["completion_profile", "required_for_core_release", "status", "evidence_refs", "blockers"],
        allOf=[
            {"if": {"properties": {"completion_profile": {"const": "core_autonomous_runtime"}}, "required": ["completion_profile"]}, "then": {"properties": {"required_for_core_release": {"const": True}}}},
            {"if": {"properties": {"completion_profile": {"enum": ["independent_real_accuracy", "scale_daz_maturity"]}}, "required": ["completion_profile"]}, "then": {"properties": {"required_for_core_release": {"const": False}, "blockers": {"items": {"properties": {"core_impact": {"const": "non_blocking"}}}}}}},
        ],
    )
    readiness_page = strict_object(
        {
            "page_id": {"enum": ["home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"]},
            "status": {"enum": ["not_ready", "degraded", "ready", "not_applicable"]},
            "source_read_model_ids": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "minItems": 1, "uniqueItems": True},
            "evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}},
            "blocker_codes": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/id"}, "uniqueItems": True},
        },
        ["page_id", "status", "source_read_model_ids", "evidence_refs", "blocker_codes"],
    )
    readiness = record_schema(
        readiness_record,
        {
            "runtime_completion_claimed": {"type": "boolean"},
            "projection_as_of": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "project_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "revision_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
            "release_snapshot_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "adoption_receipt_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "bridge_release_certificate_ref": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, {"type": "null"}]},
            "active_pin_status": {"enum": ["missing", "diagnostic_only", "active", "invalidated"]},
            "row218_status": {"enum": ["not_started", "planned", "blocked", "passed"]},
            "rows321_347_status": {"enum": ["not_started", "planned", "blocked", "passed"]},
            "row348_release_status": {"enum": ["not_started", "planned", "blocked", "released"]},
            "signing_trust_status": {"enum": ["missing", "fixture_only_untrusted", "rejected", "trusted"]},
            "journal_integrity_status": {"enum": ["missing", "fixture_only", "forked", "stale", "trusted_current"]},
            "profile_readiness": {"type": "array", "items": readiness_profile, "minItems": 3, "maxItems": 3, "allOf": [{"contains": {"properties": {"completion_profile": {"const": profile}}, "required": ["completion_profile"]}, "minContains": 1, "maxContains": 1} for profile in COMPLETION_PROFILES]},
            "page_readiness": {"type": "array", "items": readiness_page, "minItems": 7, "maxItems": 7, "allOf": [{"contains": {"properties": {"page_id": {"const": page}}, "required": ["page_id"]}, "minContains": 1, "maxContains": 1} for page in ["home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"]]},
            "event_cursor": strict_object({"stream_id": {"$ref": f"{COMMON_ID}#/$defs/id"}, "last_sequence": {"type": "integer", "minimum": 0}, "last_event_sha256": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/sha256"}, {"type": "null"}]}}, ["stream_id", "last_sequence", "last_event_sha256"]),
            "journal_pin": {"oneOf": [{"$ref": f"{COMMON_ID}#/$defs/journal_pin"}, {"type": "null"}]},
            "genuine_runtime_evidence_refs": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "uniqueItems": True},
            "runtime_readiness_claimed": {"type": "boolean"},
            "projection_authority": {"const": "read_only_derived_no_execution_or_promotion_authority"},
            "core_blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}},
            "optional_profile_blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}},
            "blockers": {"type": "array", "items": {"$ref": f"{COMMON_ID}#/$defs/blocker"}},
        },
        ["projection_as_of", "project_ref", "revision_ref", "release_snapshot_ref", "adoption_receipt_ref", "bridge_release_certificate_ref", "active_pin_status", "row218_status", "rows321_347_status", "row348_release_status", "signing_trust_status", "journal_integrity_status", "profile_readiness", "page_readiness", "event_cursor", "journal_pin", "genuine_runtime_evidence_refs", "runtime_readiness_claimed", "projection_authority", "core_blockers", "optional_profile_blockers", "blockers"],
        [
            {
                "if": {"properties": {"fixture_only": {"const": True}}, "required": ["fixture_only"]},
                "then": {"properties": {"runtime_completion_claimed": {"const": False}, "runtime_readiness_claimed": {"const": False}, "genuine_runtime_evidence_refs": {"maxItems": 0}, "row348_release_status": {"not": {"const": "released"}}}},
            },
            {
                "if": {"properties": {"runtime_readiness_claimed": {"const": True}}, "required": ["runtime_readiness_claimed"]},
                "then": {
                    "properties": {
                        "runtime_completion_claimed": {"const": True}, "fixture_only": {"const": False},
                        "release_snapshot_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "adoption_receipt_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"}, "bridge_release_certificate_ref": {"$ref": f"{COMMON_ID}#/$defs/immutable_ref"},
                        "active_pin_status": {"const": "active"}, "genuine_runtime_evidence_refs": {"minItems": 1},
                        "row218_status": {"const": "passed"}, "rows321_347_status": {"const": "passed"}, "row348_release_status": {"const": "released"},
                        "signing_trust_status": {"const": "trusted"}, "journal_integrity_status": {"const": "trusted_current"},
                        "journal_pin": {"$ref": f"{COMMON_ID}#/$defs/journal_pin", "properties": {"checkpoint_signature_trust": {"properties": {"trust_result": {"const": "trusted"}}}}},
                        "profile_readiness": {"contains": {"properties": {"completion_profile": {"const": "core_autonomous_runtime"}, "required_for_core_release": {"const": True}, "status": {"const": "ready"}}, "required": ["completion_profile", "required_for_core_release", "status"]}},
                        "page_readiness": {"items": {"properties": {"status": {"const": "ready"}}}},
                        "core_blockers": {"maxItems": 0},
                    }
                },
            },
            {"if": {"properties": {"runtime_completion_claimed": {"const": True}}, "required": ["runtime_completion_claimed"]}, "then": {"properties": {"runtime_readiness_claimed": {"const": True}}}},
        ],
    )

    mapping_binding = strict_object(
        {
            "contract_name": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "contract_role": {"enum": ["producer_wire_v1", "main_internal_v2"]},
            "schema_source": {"type": "string", "minLength": 3},
            "schema_id": {"type": "string", "format": "uri"},
            "schema_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "schema_sha256": {"$ref": f"{COMMON_ID}#/$defs/sha256"},
        },
        ["contract_name", "contract_role", "schema_source", "schema_id", "schema_version", "schema_sha256"],
    )
    mapping_transform = strict_object(
        {
            "operation": {"enum": ["identity", "const", "rename", "object_projection", "array_projection", "enum_map", "normalize_ref", "normalize_authority", "normalize_lineage", "normalize_blocker", "normalize_event", "normalize_transform_chain", "hash_bind", "context_lookup", "policy_recompute", "preserve_validated_raw_envelope", "drop_after_validation"]},
            "version": {"const": "1.0.0"},
            "enum_conversion": {"type": "object", "additionalProperties": {"type": ["string", "number", "integer", "boolean", "null"]}},
            "parameters": {"type": "object", "additionalProperties": True},
            "unmapped_enum_action": {"const": "reject"},
        },
        ["operation", "version", "enum_conversion", "parameters", "unmapped_enum_action"],
    )
    mapping_authority = strict_object(
        {
            "source_authority": {"enum": ["producer_wire_factual", "main_internal_factual", "main_policy_derived", "none"]},
            "target_authority": {"enum": ["producer_wire_factual", "main_internal_factual", "main_policy_derived", "none"]},
            "may_elevate_authority": {"const": False},
        },
        ["source_authority", "target_authority", "may_elevate_authority"],
    )
    field_rule = strict_object(
        {
            "field_rule_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "direction": {"enum": ["maskfactory_to_main", "main_to_maskfactory"]},
            "source_path": {"oneOf": [{"type": "string", "pattern": r"^\$"}, {"type": "null"}]},
            "target_path": {"oneOf": [{"type": "string", "pattern": r"^\$"}, {"type": "null"}]},
            "source_required": {"type": "boolean"},
            "target_required": {"type": "boolean"},
            "disposition": {"enum": ["map", "drop", "default", "recompute", "reject"]},
            "transform": mapping_transform,
            "authority": mapping_authority,
            "reason": {"type": "string", "minLength": 1},
        },
        ["field_rule_id", "direction", "source_path", "target_path", "source_required", "target_required", "disposition", "transform", "authority", "reason"],
        allOf=[
            {"if": {"properties": {"disposition": {"const": "drop"}}, "required": ["disposition"]}, "then": {"properties": {"source_path": {"type": "string"}, "target_path": {"type": "null"}}}},
            {"if": {"properties": {"disposition": {"enum": ["default", "recompute"]}}, "required": ["disposition"]}, "then": {"properties": {"target_path": {"type": "string"}}}},
            {"if": {"properties": {"disposition": {"const": "map"}}, "required": ["disposition"]}, "then": {"properties": {"source_path": {"type": "string"}, "target_path": {"type": "string"}}}},
        ],
    )
    mapping_entry = strict_object(
        {
            "mapping_rule_id": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "direction": {"enum": ["maskfactory_to_main", "main_to_maskfactory"]},
            "producer_contract_name": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "main_contract_name": {"$ref": f"{COMMON_ID}#/$defs/id"},
            "source_contract_role": {"enum": ["producer_wire_v1", "main_internal_v2"]},
            "target_contract_role": {"enum": ["producer_wire_v1", "main_internal_v2"]},
            "producer_binding": mapping_binding,
            "main_binding": mapping_binding,
            "exact_producer_binding_required": {"const": True},
            "field_rules": {"type": "array", "items": field_rule, "minItems": 1},
            "covered_producer_top_level_paths": {"type": "array", "items": {"type": "string", "pattern": r"^\$\."}, "minItems": 1, "uniqueItems": True},
            "producer_required_paths": {"type": "array", "items": {"type": "string", "pattern": r"^\$\."}, "minItems": 1, "uniqueItems": True},
            "covered_main_top_level_paths": {"type": "array", "items": {"type": "string", "pattern": r"^\$\."}, "minItems": 1, "uniqueItems": True},
            "main_required_paths": {"type": "array", "items": {"type": "string", "pattern": r"^\$\."}, "minItems": 1, "uniqueItems": True},
            "unknown_source_field_action": {"const": "reject"},
            "unknown_target_field_action": {"const": "reject"},
            "unmapped_required_field_action": {"const": "block_dependent_pass"},
            "recursive_subtree_policy": {"const": "validate_against_exact_bound_schema_then_execute_named_transform"},
        },
        ["mapping_rule_id", "direction", "producer_contract_name", "main_contract_name", "source_contract_role", "target_contract_role", "producer_binding", "main_binding", "exact_producer_binding_required", "field_rules", "covered_producer_top_level_paths", "producer_required_paths", "covered_main_top_level_paths", "main_required_paths", "unknown_source_field_action", "unknown_target_field_action", "unmapped_required_field_action", "recursive_subtree_policy"],
    )
    mapping_schema = strict_object(
        {
            "schema_version": {"const": SCHEMA_VERSION},
            "registry_id": {"const": "wave64_maskfactory_producer_wire_to_main_port_mapping_v2"},
            "updated_at": {"$ref": f"{COMMON_ID}#/$defs/timestamp"},
            "mapping_schema_binding": mapping_binding,
            "producer_schema_authority": {"const": "exact_schema_name_version_hash_imported_from_adopted_maskfactory_release"},
            "main_schema_authority": {"const": "internal_normalized_port_and_import_validation_only"},
            "path_language": {"const": "rfc9535_jsonpath"},
            "unknown_or_missing_mapping_action": {"const": "block_dependent_pass"},
            "producer_use_eligibility_policy": strict_object(
                {
                    "source_path": {"const": "$.use_eligibility"},
                    "producer_value_authoritative_for_main_use": {"const": False},
                    "normalization_action": {"const": "drop_after_validation"},
                    "main_recompute_contract_binding": mapping_binding,
                    "main_target_path": {"const": "$.eligible_for_intended_use"},
                    "recompute_rule": {"const": "evaluate_exact_signed_pinned_main_policy_unique_criteria_claim_class_trusted_signer_decision_timestamp_certificate_expiry_current_revocation_index_and_nonfixture_evidence"},
                },
                ["source_path", "producer_value_authoritative_for_main_use", "normalization_action", "main_recompute_contract_binding", "main_target_path", "recompute_rule"],
            ),
            "mappings": {"type": "array", "items": mapping_entry, "minItems": 12},
            "runtime_completion_claimed": {"const": False},
        },
        ["schema_version", "registry_id", "updated_at", "mapping_schema_binding", "producer_schema_authority", "main_schema_authority", "path_language", "unknown_or_missing_mapping_action", "producer_use_eligibility_policy", "mappings", "runtime_completion_claimed"],
        **{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{SCHEMA_BASE}/wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json", "title": "wave64_maskfactory_producer_wire_to_main_port_mapping_v2"},
    )

    schemas = {
        "wave64_maskfactory_bridge_common_v2.schema.json": common,
        "wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json": mapping_schema,
        f"{release_record}.schema.json": release,
        f"{requirements_record}.schema.json": consumer,
        f"{adoption_record}.schema.json": adoption,
        f"{request_record}.schema.json": request,
        f"{certificate_record}.schema.json": operational_certificate,
        f"{promotion_record}.schema.json": promotion_policy,
        f"{result_record}.schema.json": result,
        f"{authority_record}.schema.json": authority_decision,
        f"{health_record}.schema.json": health,
        f"{invalidation_record}.schema.json": invalidation,
        f"{event_record}.schema.json": bridge_event,
        f"{feedback_record}.schema.json": feedback,
        f"{integration_record}.schema.json": integration,
        f"{readiness_record}.schema.json": readiness,
    }
    return schemas


def mapping_transform(operation: str, *, enum_conversion: dict[str, Any] | None = None, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "operation": operation,
        "version": "1.0.0",
        "enum_conversion": enum_conversion or {},
        "parameters": parameters or {},
        "unmapped_enum_action": "reject",
    }


def mapping_authority(source: str, target: str) -> dict[str, Any]:
    return {"source_authority": source, "target_authority": target, "may_elevate_authority": False}


def main_schema_view(schemas: dict[str, dict[str, Any]], spec: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    schema = schemas[spec["main_schema_file"]]
    if spec.get("main_view") == "blocker":
        view = schema["$defs"]["blocker"]
        properties = list(view["properties"])
        required = list(view["required"])
    elif spec.get("main_projection_properties"):
        properties = list(spec["main_projection_properties"])
        required = list(spec.get("main_projection_required", properties))
    else:
        properties = list(schema["properties"])
        required = list(schema["required"])
    return schema, properties, required


def mapping_specs() -> list[dict[str, Any]]:
    access_enum = {mode: mode for mode in ACCESS_MODES}
    authority_enum = {state: state for state in AUTHORITY_STATES}
    issuer_enum = {kind: kind for kind in ISSUER_KINDS}
    coordinate_to_main = {"source_pixel": "source_pixels", "crop_pixel": "working_pixels", "output_pixel": "frame_pixels", "normalized_0_1": "normalized_0_1"}
    coordinate_to_producer = {value: key for key, value in coordinate_to_main.items()}
    operation_to_producer = {"identity": "identity", "crop": "crop", "resize": "resize", "pad": "pad", "horizontal_flip": "horizontal_flip", "project": "inverse_project"}
    operation_to_main = {value: key for key, value in operation_to_producer.items()}
    producer_error_to_main = {
        "SERVICE_UNAVAILABLE": "MFB_SERVICE_OFFLINE", "TIMEOUT": "MFB_TIMEOUT", "RATE_LIMITED": "MFB_RATE_LIMITED",
        "RESOURCE_LIMIT_EXCEEDED": "MFB_RESOURCE_LIMIT_EXCEEDED", "OUT_OF_MEMORY": "MFB_OUT_OF_MEMORY", "CIRCUIT_OPEN": "MFB_CIRCUIT_OPEN",
        "RELEASE_NOT_ADOPTED": "MFB_RELEASE_NOT_ADOPTED", "RELEASE_REVOKED": "MFB_RELEASE_REVOKED", "API_VERSION_MISMATCH": "MFB_API_CONTRACT_DRIFT",
        "WIRE_SCHEMA_MISMATCH": "MFB_SCHEMA_HASH_DRIFT", "CONTRACT_VERSION_MISMATCH": "MFB_SCHEMA_VERSION_DRIFT", "PACKAGE_FORMAT_MISMATCH": "MFB_PACKAGE_FORMAT_DRIFT",
        "ONTOLOGY_MISMATCH": "MFB_ONTOLOGY_DRIFT", "SOURCE_HASH_MISMATCH": "MFB_OUTPUT_HASH_MISMATCH", "SOURCE_DIMENSION_MISMATCH": "MFB_SOURCE_DIMENSION_MISMATCH",
        "PERSON_INDEX_AMBIGUOUS": "MFB_PERSON_INDEX_CONFLICT", "OWNERSHIP_AMBIGUOUS": "MFB_OWNER_AMBIGUOUS", "TRANSFORM_MISMATCH": "MFB_TRANSFORM_MISMATCH",
        "TRANSFORM_ROUNDTRIP_FAILED": "MFB_TRANSFORM_ROUNDTRIP_FAIL", "LABEL_UNSUPPORTED": "MFB_LABEL_UNSUPPORTED", "ARTIFACT_HASH_MISMATCH": "MFB_OUTPUT_HASH_MISMATCH",
        "CERTIFICATE_MISSING": "MFB_CERTIFICATE_MISSING", "CERTIFICATE_EXPIRED": "MFB_CERTIFICATE_EXPIRED", "CERTIFICATE_REVOKED": "MFB_CERTIFICATE_REVOKED",
        "CERTIFICATE_OUT_OF_SCOPE": "MFB_CERTIFICATE_SCOPE_MISMATCH", "AUTHORITY_INSUFFICIENT": "MFB_AUTHORITY_INSUFFICIENT", "PROVIDER_UNAVAILABLE": "MFB_PROVIDER_UNAVAILABLE",
        "NO_ELIGIBLE_ROUTE": "MFB_NO_ELIGIBLE_ROUTE", "QA_GATE_FAILED": "MFB_QA_GATE_FAILED", "PATH_ESCAPE_REJECTED": "MFB_PATH_ESCAPE_REJECTED",
        "STALE_CACHE": "MFB_CACHE_INVALIDATED", "MALFORMED_RESPONSE": "MFB_MALFORMED_RESPONSE", "UNKNOWN_SUBMISSION": "MFB_SUBMISSION_UNKNOWN",
        "INVARIANT_VIOLATION": "MFB_INVARIANT_VIOLATION", "IDEMPOTENCY_CONFLICT": "MFB_IDEMPOTENCY_CONFLICT", "INVALID_REQUEST": "MFB_INVALID_REQUEST",
        "INTERNAL_ERROR": "MFB_INTERNAL_ERROR",
    }
    main_error_to_producer = {
        "MFB_SERVICE_OFFLINE": "SERVICE_UNAVAILABLE", "MFB_TIMEOUT": "TIMEOUT", "MFB_RATE_LIMITED": "RATE_LIMITED",
        "MFB_RESOURCE_LIMIT_EXCEEDED": "RESOURCE_LIMIT_EXCEEDED", "MFB_OUT_OF_MEMORY": "OUT_OF_MEMORY", "MFB_CIRCUIT_OPEN": "CIRCUIT_OPEN",
        "MFB_RELEASE_NOT_ADOPTED": "RELEASE_NOT_ADOPTED", "MFB_RELEASE_REVOKED": "RELEASE_REVOKED", "MFB_API_CONTRACT_DRIFT": "API_VERSION_MISMATCH",
        "MFB_SCHEMA_SOURCE_DRIFT": "WIRE_SCHEMA_MISMATCH", "MFB_SCHEMA_HASH_DRIFT": "WIRE_SCHEMA_MISMATCH", "MFB_SCHEMA_VERSION_DRIFT": "CONTRACT_VERSION_MISMATCH",
        "MFB_PACKAGE_FORMAT_DRIFT": "PACKAGE_FORMAT_MISMATCH", "MFB_ONTOLOGY_DRIFT": "ONTOLOGY_MISMATCH", "MFB_OUTPUT_HASH_MISMATCH": "ARTIFACT_HASH_MISMATCH",
        "MFB_SOURCE_DIMENSION_MISMATCH": "SOURCE_DIMENSION_MISMATCH", "MFB_PERSON_INDEX_CONFLICT": "PERSON_INDEX_AMBIGUOUS", "MFB_OWNER_AMBIGUOUS": "OWNERSHIP_AMBIGUOUS",
        "MFB_TRANSFORM_MISMATCH": "TRANSFORM_MISMATCH", "MFB_TRANSFORM_ROUNDTRIP_FAIL": "TRANSFORM_ROUNDTRIP_FAILED", "MFB_LABEL_UNSUPPORTED": "LABEL_UNSUPPORTED",
        "MFB_CERTIFICATE_MISSING": "CERTIFICATE_MISSING", "MFB_CERTIFICATE_EXPIRED": "CERTIFICATE_EXPIRED", "MFB_CERTIFICATE_REVOKED": "CERTIFICATE_REVOKED",
        "MFB_CERTIFICATE_SCOPE_MISMATCH": "CERTIFICATE_OUT_OF_SCOPE", "MFB_AUTHORITY_INSUFFICIENT": "AUTHORITY_INSUFFICIENT", "MFB_PROVIDER_UNAVAILABLE": "PROVIDER_UNAVAILABLE",
        "MFB_NO_ELIGIBLE_ROUTE": "NO_ELIGIBLE_ROUTE", "MFB_QA_GATE_FAILED": "QA_GATE_FAILED", "MFB_PROTECTED_REGION_LEAK": "QA_GATE_FAILED",
        "MFB_PATH_ESCAPE_REJECTED": "PATH_ESCAPE_REJECTED", "MFB_CACHE_INVALIDATED": "STALE_CACHE", "MFB_MALFORMED_RESPONSE": "MALFORMED_RESPONSE",
        "MFB_SUBMISSION_UNKNOWN": "UNKNOWN_SUBMISSION", "MFB_INVARIANT_VIOLATION": "INVARIANT_VIOLATION", "MFB_IDEMPOTENCY_CONFLICT": "IDEMPOTENCY_CONFLICT",
        "MFB_INVALID_REQUEST": "INVALID_REQUEST", "MFB_INTERNAL_ERROR": "INTERNAL_ERROR", "MFB_PACKAGE_NOT_FOUND": "PROVIDER_UNAVAILABLE",
    }
    return [
        {
            "producer": "maskfactory_release_snapshot", "direction": "maskfactory_to_main", "main": "maskfactory_release_snapshot_v2", "main_schema_file": "maskfactory_release_snapshot_v2.schema.json", "rule": "map_release_snapshot_v1_to_main_validation_v2",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}},
                "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_release_snapshot_v2"}},
                "release_id": {"target": "$.release_id", "operation": "identity"},
                "release_status": {"target": "$.release_status", "operation": "identity", "parameters": {"allowed_release_statuses": ["fixture", "published", "superseded", "revoked"], "non_published_action": "retain_for_invalidation_or_reject_adoption"}},
                "published_at": {"target": "$.published_at", "operation": "identity"},
                "evidence_context": {"target": "$.release_context", "operation": "enum_map", "enum": {"conformance_fixture": "fixture_validation", "runtime_evidence": "production_runtime"}},
                "fixture_only": {"target": "$.fixture_only", "operation": "identity"},
                "canonicalization": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_algorithm": "maskfactory-canonical-json-v1", "required_excluded_top_level_fields": ["release_payload_sha256", "signature"]}},
                "producer": {"target": "$.producer_source", "operation": "object_projection", "parameters": {"field_map": {"repository_id": "repository_id", "git_commit": "commit_sha", "dirty": "source_clean_inverted"}}},
                "compatibility": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "compatibility_components_with_hashes_from_release_artifacts"}},
                "wire_schemas": {"target": "$.contract_bindings", "operation": "array_projection", "parameters": {"projection": "name_version_sha256_to_exact_contract_binding"}},
                "semantic_invariant_profile": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_semantic_profile_and_document_hash_component_bindings", "require_all_validation_layers": True}},
                "completion_profiles": {"target": "$.completion_profiles", "operation": "object_projection", "enum": {name: name for name in COMPLETION_PROFILES}, "parameters": {"projection": "three_exact_profile_ids_to_status_map", "core_required_true": True, "optional_profiles_required_false": True}},
                "artifacts": {"target": "$.artifact_refs", "operation": "array_projection", "parameters": {"projection": "release_artifact_to_immutable_ref"}},
                "openapi": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_openapi_component_binding"}},
                "capability_snapshot": {"target": "$.capability_refs", "operation": "normalize_ref"},
                "workflow_inventory": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_workflow_inventory_hash_binding"}},
                "node_inventory": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_node_inventory_hash_binding"}},
                "certificate_index": {"target": "$.certificate_refs", "operation": "array_projection", "parameters": {"projection": "certificate_index_and_revocation_index_to_exact_immutable_refs"}},
                "evidence_index": {"target": "$.artifact_refs", "operation": "array_projection", "parameters": {"projection": "append_evidence_index_immutable_ref"}},
                "known_limitations": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"preserve_via_release_payload_sha256": True, "project_to_readiness_blockers": True}},
                "breaking_changes": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_breaking_change_migration_hash_component_bindings", "unmapped_breaking_change_action": "reject_adoption"}},
                "installation": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_installer_and_verification_workflow_hash_bindings"}},
                "rollback": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "append_rollback_and_verification_hash_bindings"}},
                "supersedes_release_id": {"target": "$.revocation_refs", "operation": "array_projection", "parameters": {"projection": "nullable_superseded_release_to_invalidation_ref"}},
                "revoked_release_ids": {"target": "$.revocation_refs", "operation": "array_projection", "parameters": {"projection": "release_id_to_invalidation_ref"}},
                "release_payload_sha256": {"target": "$.snapshot_sha256", "operation": "identity"},
                "journal_checkpoint": {"target": "$.component_bindings", "operation": "array_projection", "parameters": {"projection": "producer_journal_head_revocation_state_and_validator_component_bindings", "producer_checkpoint_is_later_copied_exactly_to_adoption_producer_journal_checkpoint_binding": True, "separate_from_main_event_journal": True}},
                "signing_trust": {"target": "$.signature_trust", "operation": "object_projection", "parameters": {"projection": "producer_release_signing_binding_plus_out_of_band_main_trust_verification", "also_derives": ["$.component_bindings.signing_key_set", "$.component_bindings.rotation_policy", "$.component_bindings.revocation_policy"], "caller_supplied_trust_result_forbidden": True}},
                "signature": {"target": "$.release_signature", "operation": "object_projection", "parameters": {"projection": "validated_signature_value_base64", "verify_before_normalization": True, "signature_covers": "canonical_producer_payload"}},
            },
            "main_context_fields": {
                "raw_producer_release_ref": {"source_path": "$", "operation": "preserve_validated_raw_envelope", "parameters": {"projection": "immutable_ref_to_exact_strict_utf8_schema_validated_raw_bytes", "record_id_source": "$.release_id", "sha256_source": "exact_raw_envelope_bytes", "caller_override_forbidden": True}, "reason": "The immutable ref is injected only from the exact validated raw producer envelope; controller context cannot choose its identity or hash.", "source_authority": "producer_wire_factual"},
                "normalization_payload_sha256": {"operation": "hash_bind", "parameters": {"projection": "main_normalized_release_domain_separated_canonical_payload"}},
                "normalization_signature": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signing_result"], "sign_exact_normalization_payload_sha256": True}},
                "normalization_signature_trust": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signer_out_of_band_verification"], "caller_supplied_trust_result_forbidden": True}},
            },
        },
        {
            "producer": "maskfactory_capability_snapshot", "direction": "maskfactory_to_main", "main": "maskfactory_health_capability_snapshot_v2", "main_schema_file": "maskfactory_health_capability_snapshot_v2.schema.json", "rule": "map_capability_snapshot_v1_to_health_projection_v2",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}},
                "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_health_capability_snapshot_v2"}},
                "snapshot_id": {"target": "$.maskfactory_health_capability_snapshot_v2_id", "operation": "rename"},
                "release_id": {"target": "$.release_snapshot_ref", "operation": "normalize_ref"},
                "generated_at": {"target": "$.created_at", "operation": "rename"},
                "bridge_contract": {"target": "$.api_contract", "operation": "hash_bind", "parameters": {"binding_source": "adopted_release_openapi_and_wire_manifest"}},
                "access_modes": {"target": "$.routes", "operation": "array_projection", "enum": access_enum, "parameters": {"projection": "route_access_mode_seed"}},
                "labels": {"target": "$.routes", "operation": "array_projection", "parameters": {"projection": "route_supported_labels"}},
                "provider_stacks": {"target": "$.routes", "operation": "array_projection", "parameters": {"projection": "provider_stack_to_exact_execution_route"}},
                "availability": {"target": "$.service_status", "operation": "enum_map", "enum": {"available": "healthy", "degraded": "degraded", "unavailable": "offline"}, "parameters": {"projection": "worst_required_route_availability"}},
            },
        },
        {
            "producer": "maskfactory_consumer_requirements", "direction": "main_to_maskfactory", "main": "maskfactory_consumer_requirements_v2", "main_schema_file": "maskfactory_consumer_requirements_v2.schema.json", "rule": "map_main_requirements_v2_to_producer_wire_v1",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}},
                "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "maskfactory_consumer_requirements"}},
                "requirements_id": {"source": "$.maskfactory_consumer_requirements_v2_id", "operation": "rename"},
                "consumer": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["controller_version", "git_commit"], "project": "Comfy_UI_Main"}},
                "created_at": {"source": "$.created_at", "operation": "identity"},
                "authentication": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_authenticated_consumer_principal_nonce_record"], "credential_material_included": False, "expiry_and_replay_window_required": True}},
                "trust_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_consumer_requirements_signing_key_binding"], "out_of_band_active_key_required": True}},
                "canonicalization": {"disposition": "default", "operation": "const", "parameters": {"value": {"algorithm": "maskfactory-canonical-json-v1", "excluded_top_level_fields": ["requirements_sha256", "signature"]}}},
                "bridge_contract": {"disposition": "default", "operation": "const", "parameters": {"value": "maskfactory-comfyui-bridge/1.0"}},
                "accepted_wire_schemas": {"source": "$.required_contract_bindings", "operation": "array_projection", "parameters": {"projection": "wire_schema_name_version_sha256"}},
                "trusted_signing_key_sets": {"source": "$.trusted_signing_key_registry_ref", "operation": "array_projection", "parameters": {"projection": "exact_active_allowed_maskfactory_key_sets_from_out_of_band_registry", "required_signing_key_ids_source": "$.required_signing_key_ids", "caller_supplied_keys_forbidden": True}},
                "required_semantic_invariant_profile": {"source": "$.required_contract_bindings", "operation": "array_projection", "parameters": {"projection": "semantic_invariant_profile_exact_binding", "required_profile_id": "maskfactory-comfyui-bridge-semantics", "required_profile_version": "1.0.0", "require_all_validation_layers": True}},
                "required_access_modes": {"source": "$.supported_access_modes", "operation": "enum_map", "enum": access_enum},
                "required_capabilities": {"source": "$.required_certificate_scope", "operation": "array_projection", "parameters": {"additional_sources": ["$.supported_access_modes", "$.required_labels", "$.maximum_person_count"], "projection": "main_required_scopes_to_producer_capability_requirements", "missing_required_capability_action": "reject"}},
                "optional_capabilities": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["pinned_optional_capability_requirements"], "empty_array_allowed": True, "producer_extra_never_implicitly_required": True}},
                "compatibility": {"source": "$.required_contract_bindings", "operation": "object_projection", "parameters": {"projection": "api_package_ontology_node_pack_sets"}},
                "required_labels": {"source": "$.required_labels", "operation": "identity"},
                "required_artifact_kinds": {"disposition": "default", "operation": "context_lookup", "parameters": {"required_context": ["pinned_consumer_artifact_kind_policy"]}},
                "required_coordinate_spaces": {"disposition": "default", "operation": "context_lookup", "parameters": {"required_context": ["pinned_consumer_coordinate_space_policy"]}},
                "required_transform_operations": {"source": "$.required_transform_operations", "operation": "enum_map", "enum": operation_to_producer, "parameters": {"identity_noop_rule": "omit_only_after_exact_roundtrip_validation"}},
                "accepted_media_scopes": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["pinned_consumer_media_scope_policy"], "must_cover_requested_still_frame_and_span_modes_exactly": True}},
                "minimum_person_count": {"disposition": "default", "operation": "const", "parameters": {"value": 1}},
                "authority_requirements": {"source": "$.minimum_authority_state", "operation": "object_projection", "enum": {**authority_enum, **issuer_enum}, "parameters": {"additional_sources": ["$.allowed_issuer_kinds", "$.required_certificate_scope"], "access_mode_determines_authority": False, "allow_consumer_truth_escalation": False}},
                "runtime_requirements": {"source": "$.maximum_latency_ms", "operation": "object_projection", "parameters": {"additional_context": ["retry_and_idempotency_policy"]}},
                "requirements_sha256": {"disposition": "recompute", "operation": "hash_bind", "parameters": {"algorithm": "sha256", "scope": "canonical_producer_payload_without_requirements_sha256_and_signature", "signature_is_appended_only_after_hashing": True}},
                "signature": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_consumer_requirements_signing_result"], "signer_role": "main_consumer_requirements_signer", "producer_key_role": "consumer_requirements", "hash_before_signature": True, "signed_payload_format": "sha256_digest_bytes"}},
            },
        },
        {
            "producer": "mask_bridge_semantic_invariant_profile", "direction": "maskfactory_to_main", "main": "maskfactory_release_snapshot_v2.component_bindings", "main_schema_file": "maskfactory_release_snapshot_v2.schema.json", "main_projection_properties": ["component_bindings"], "rule": "map_frozen_semantic_invariant_profile_to_exact_component_binding",
            "fields": {
                "profile_id": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "semantic_profile_identity"}},
                "profile_version": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "semantic_profile_version"}},
                "status": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"required_status": "frozen"}},
                "canonicalization": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "canonicalization_profile"}},
                "canonicalization_spec_sha256": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "canonicalization_spec_hash"}},
                "required_validation_layers": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "closed_validation_layer_set"}},
                "authority_rank": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "authority_rank_invariant"}},
                "certificate_kind_crosswalk": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "certificate_crosswalk_invariant"}},
                "invariants": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "semantic_invariant_set"}},
                "conformance_fixture_index": {"target": "$.component_bindings", "operation": "object_projection", "parameters": {"projection": "conformance_fixture_index_hash"}},
                "profile_sha256": {"target": "$.component_bindings", "operation": "hash_bind"},
            },
        },
        {
            "producer": "mask_acquisition_request", "direction": "main_to_maskfactory", "main": "maskfactory_bridge_request_v2", "main_schema_file": "maskfactory_bridge_request_v2.schema.json", "rule": "compile_main_request_v2_to_producer_request_v1",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}},
                "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "mask_acquisition_request"}},
                "request_id": {"source": "$.maskfactory_bridge_request_v2_id", "operation": "rename"},
                "project_id": {"source": "$.scope.project_id", "operation": "rename"},
                "run_id": {"source": "$.scope.run_id", "operation": "rename"},
                "correlation_id": {"source": "$.correlation_id", "operation": "identity"},
                "job_id": {"source": "$.scope.job_id", "operation": "rename"},
                "pass_id": {"source": "$.scope.pass_id", "operation": "rename"},
                "attempt_id": {"source": "$.scope.attempt_id", "operation": "rename"},
                "attempt_number": {"source": "$.attempt_number", "operation": "identity"},
                "hypothesis": {"source": "$.hypothesis", "operation": "object_projection", "parameters": {"projection": "exact_hypothesis_id_class_retry_kind_and_material_change_hash"}},
                "idempotency_key": {"source": "$.idempotency_key", "operation": "identity"},
                "created_at": {"source": "$.created_at", "operation": "identity"},
                "deadline_at": {"source": "$.deadline_at", "operation": "identity"},
                "authentication": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_authenticated_request_principal_nonce_record"], "credential_material_included": False, "expiry_and_replay_window_required": True}},
                "trust_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_request_signing_key_binding"], "out_of_band_active_key_required": True}},
                "canonicalization": {"disposition": "default", "operation": "const", "parameters": {"value": {"algorithm": "maskfactory-canonical-json-v1", "excluded_top_level_fields": ["request_payload_sha256", "signature"]}}},
                "access_mode": {"source": "$.access_mode", "operation": "enum_map", "enum": access_enum},
                "media_scope": {"source": "$.media_scope", "operation": "object_projection", "parameters": {"projection": "exact_still_frame_or_span_scope_with_pts_timebase_neighbors_and_hashes"}},
                "source": {"source": "$.source_artifact", "operation": "object_projection", "enum": coordinate_to_producer, "parameters": {"projection": "source_artifact_to_wire_source"}},
                "subject": {"source": "$.owner_bindings", "operation": "object_projection", "parameters": {"additional_sources": ["$.scene_owner_roster"], "projection": "exact_single_target_character_instance_and_provider_person_index", "ambiguous_target_action": "reject"}},
                "mask_intents": {"source": "$.mask_intents", "operation": "array_projection", "parameters": {"projection": "strict_intent_projection"}},
                "target_regions": {"source": "$.target_region_bindings", "operation": "array_projection", "parameters": {"projection": "input_target_roi_hash_owner_coordinate_transform_bindings", "never_substitute_output_artifact_hash": True}},
                "protected_regions": {"source": "$.protected_region_bindings", "operation": "array_projection", "parameters": {"additional_sources": ["$.scene_owner_roster"], "projection": "protected_self_other_character_prop_environment_owner_bindings", "ambiguous_owner_action": "reject", "never_substitute_output_artifact_hash": True}},
                "protected_owner_roster": {"source": "$.scene_owner_roster", "operation": "array_projection", "parameters": {"projection": "exact_protected_owner_identity_and_assignment_evidence_roster", "missing_or_ambiguous_owner_action": "reject"}},
                "transform_chain": {"source": "$.transform_chain", "operation": "normalize_transform_chain", "enum": operation_to_producer, "parameters": {"preserve_typed_parameters_spaces_dimensions_interpolation_rounding_side_swap_inverse_roundtrip_and_chain_hash": True, "non_executable_or_hash_only_action": "reject"}},
                "compatibility": {"source": "$.expected_contract_bindings", "operation": "object_projection", "parameters": {"additional_sources": ["$.release_snapshot_ref"]}},
                "minimum_authority_state": {"source": "$.minimum_authority_state", "operation": "enum_map", "enum": authority_enum},
                "accepted_authority": {"source": "$.accepted_issuer_kinds", "operation": "object_projection", "enum": issuer_enum, "parameters": {"additional_sources": ["$.required_certificate_scope"]}},
                "resource_envelope": {"source": "$.resource_envelope", "operation": "object_projection", "parameters": {"projection": "exact_admitted_deadline_queue_runtime_vram_ram_output_priority_cpu_policy"}},
                "retry_policy": {"source": "$.retry_class", "operation": "object_projection", "parameters": {"same_hypothesis_quality_retry_allowed": False}},
                "mode_payload": {"source": "$.access_mode", "operation": "object_projection", "enum": access_enum, "parameters": {"projection": "strict_access_mode_discriminated_payload", "missing_selector_action": "reject"}},
                "request_payload_sha256": {"disposition": "recompute", "operation": "hash_bind", "parameters": {"algorithm": "sha256", "scope": "canonical_producer_payload_without_request_payload_sha256_and_signature", "signature_is_appended_only_after_hashing": True}},
                "signature": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_request_signing_result"], "signer_role": "main_mask_request_signer", "producer_key_role": "consumer_request", "hash_before_signature": True, "signed_payload_format": "sha256_digest_bytes"}},
            },
        },
        {
            "producer": "mask_acquisition_receipt", "direction": "maskfactory_to_main", "main": "maskfactory_bridge_result_v2", "main_schema_file": "maskfactory_bridge_result_v2.schema.json", "rule": "validate_then_normalize_producer_receipt_v1",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}},
                "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_bridge_result_v2"}},
                "receipt_id": {"target": "$.maskfactory_bridge_result_v2_id", "operation": "rename"},
                "request_id": {"target": "$.request_ref", "operation": "normalize_ref"},
                "request_payload_sha256": {"target": "$.request_ref", "operation": "hash_bind", "parameters": {"projection": "bind_request_id_and_exact_request_payload_sha256"}},
                "project_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "execution_scope_project_id"}},
                "run_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "execution_scope_run_id"}},
                "job_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "execution_scope_job_id"}},
                "pass_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "execution_scope_pass_id"}},
                "attempt_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "execution_scope_attempt_id"}},
                "attempt_number": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "attempt_number"}},
                "hypothesis_id": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "hypothesis_id"}},
                "idempotency_key": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"verify_against_bound_request": True}},
                "completed_at": {"target": "$.created_at", "operation": "rename"},
                "authentication": {"disposition": "drop", "operation": "preserve_validated_raw_envelope", "parameters": {"raw_envelope_target": "$.raw_producer_receipt_ref", "validate_nonce_principal_role_expiry_and_replay_window_before_normalization": True}},
                "trust_binding": {"target": "$.raw_producer_receipt_signature_trust", "operation": "object_projection", "parameters": {"projection": "producer_receipt_key_binding_plus_out_of_band_main_trust_verification", "caller_supplied_trust_result_forbidden": True}},
                "canonicalization": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_algorithm": "maskfactory-canonical-json-v1", "required_excluded_top_level_fields": ["receipt_payload_sha256", "signature"]}},
                "result": {"target": "$.status", "operation": "enum_map", "enum": {"succeeded": "succeeded", "blocked": "blocked", "failed": "error"}},
                "access_mode": {"target": "$.access_mode", "operation": "enum_map", "enum": access_enum},
                "media_scope": {"target": "$.media_scope", "operation": "object_projection", "parameters": {"projection": "exact_still_frame_or_span_scope_without_widening"}},
                "execution_observation": {"target": "$.execution_observation", "operation": "object_projection", "parameters": {"projection": "exact_route_timing_resource_worker_and_outcome_observation", "factual_not_promotion_authority": True}},
                "release_binding": {"target": "$.release_snapshot_ref", "operation": "normalize_ref"},
                "source_binding": {"target": "$.source_artifact", "operation": "object_projection", "enum": coordinate_to_main, "parameters": {"projection": "wire_source_to_source_artifact"}},
                "subject_binding": {"target": "$.owner_bindings", "operation": "array_projection", "parameters": {"projection": "subject_to_owner_binding_with_assignment_evidence"}},
                "provider_binding": {"target": "$.execution_stack_ref", "operation": "normalize_ref", "parameters": {"also_derives": ["$.route_id"]}},
                "artifacts": {"target": "$.masks", "operation": "array_projection", "enum": coordinate_to_main, "parameters": {"projection": "wire_artifact_to_normalized_mask_with_per_mask_authority"}},
                "transform_validation": {"target": "$.transform_chain", "operation": "normalize_transform_chain", "enum": coordinate_to_main, "parameters": {"also_derives": ["$.roundtrip_max_error_pixels"], "preserve_chain_id_hash_spaces_dimensions_executed_step_hashes_and_roundtrip_result": True, "required_true": ["roundtrip_checked", "roundtrip_passed"]}},
                "qa": {"target": "$.qa_record_refs", "operation": "normalize_ref", "parameters": {"also_derives": ["$.blockers"]}},
                "authority": {"target": "$.authority", "operation": "normalize_authority", "enum": {**authority_enum, **issuer_enum}, "parameters": {"producer_authority_remains_factual_not_use_eligibility": True}},
                "truth_tier": {"target": "$.authority.claim_class", "operation": "enum_map", "enum": {"invalid": "invalid", "machine_candidate": "machine_candidate", "qa_passed_machine_candidate": "qa_passed_machine_candidate", "operationally_certified_artifact": "operationally_certified_artifact", "autonomous_certified_gold": "operationally_certified_artifact", "human_anchor_gold": "independent_real_accuracy_anchor"}, "parameters": {"legacy_autonomous_certified_gold_is_never_training_or_accuracy_gold": True, "producer_final_expected_value": "operationally_certified_artifact"}},
                "lineage": {"target": "$.masks", "operation": "normalize_lineage", "enum": {"original_prediction": "original", "package_read": "original", "refinement": "derived", "derived_union": "derived", "inpaint_derivative": "derived", "projection": "derived"}, "parameters": {"derivation_operation_map": {"original_prediction": "none", "package_read": "none", "refinement": "refine", "derived_union": "union", "inpaint_derivative": "refine", "projection": "project"}, "preserve_parent_authority_and_certificate_refs": True, "derived_parent_minimum": 1, "original_parent_maximum": 0}},
                "use_eligibility": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"producer_value_authoritative_for_main_use": False, "recompute_with": "maskfactory_authority_decision_v2"}, "reason": "Producer use_eligibility is validated for wire integrity, explicitly ignored as Main policy authority, and recomputed by Main."},
                "error": {"target": "$.blockers", "operation": "normalize_blocker", "parameters": {"null_means_no_blocker": True}},
                "receipt_payload_sha256": {"target": "$.raw_producer_receipt_payload_sha256", "operation": "identity", "parameters": {"verify_before_normalization": True, "retain_in_evidence_store": True}},
                "signature": {"target": "$.raw_producer_receipt_signature", "operation": "object_projection", "parameters": {"projection": "validated_signature_value_base64", "key_id_must_equal_trust_binding_and_out_of_band_registry": True}},
            },
            "main_context_fields": {
                "raw_producer_receipt_ref": {"source_path": "$", "operation": "preserve_validated_raw_envelope", "parameters": {"projection": "immutable_ref_to_exact_strict_utf8_schema_validated_raw_bytes", "record_id_source": "$.receipt_id", "sha256_source": "exact_raw_envelope_bytes", "caller_override_forbidden": True}, "reason": "The raw receipt ref is derived exclusively from validated bytes and cannot be widened by caller context.", "source_authority": "producer_wire_factual"},
                "normalization_payload_sha256": {"operation": "hash_bind", "parameters": {"projection": "main_normalized_result_domain_separated_canonical_payload"}},
                "normalization_signature": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signing_result"], "sign_exact_normalization_payload_sha256": True}},
                "normalization_signature_trust": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signer_out_of_band_verification"], "caller_supplied_trust_result_forbidden": True}},
            },
        },
        {
            "producer": "operational_autonomy_certificate", "direction": "maskfactory_to_main", "main": "maskfactory_operational_certificate_v2", "main_schema_file": "maskfactory_operational_certificate_v2.schema.json", "rule": "validate_exact_certificate_then_normalize_v2",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}},
                "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_operational_certificate_v2"}},
                "certificate_kind": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_value": "exact_serving_route_output", "broader_certificate_kind_action": "reject"}},
                "certificate_id": {"target": "$.maskfactory_operational_certificate_v2_id", "operation": "rename"},
                "canonicalization": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_algorithm": "maskfactory-canonical-json-v1", "required_excluded_top_level_fields": ["certificate_payload_sha256", "signature"]}},
                "certificate_payload_sha256": {"target": "$.raw_producer_certificate_payload_sha256", "operation": "identity", "parameters": {"also_derives": ["$.evidence_manifest_refs"], "projection": "certificate_payload_hash_evidence_ref", "verify_before_normalization": True}},
                "status": {"target": "$.status", "operation": "enum_map", "enum": {"active": "active", "expired": "expired", "revoked": "revoked", "superseded": "revoked"}},
                "issued_at": {"target": "$.issued_at", "operation": "identity"},
                "expires_at": {"target": "$.expires_at", "operation": "identity"},
                "evidence_context": {"target": "$.certification_context", "operation": "enum_map", "enum": {"conformance_fixture": "fixture_validation", "runtime_evidence": "production_runtime"}},
                "fixture_only": {"target": "$.fixture_only", "operation": "identity"},
                "issuer_kind": {"target": "$.issuer_kind", "operation": "enum_map", "enum": {"maskfactory_autonomous": "maskfactory_autonomous"}},
                "authority_profile": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_profile": "core_autonomous_runtime"}},
                "authority_state": {"target": "$.certificate_scope", "operation": "enum_map", "enum": {"certified": "certified"}, "parameters": {"validate_certified_for_active_output_scope": True}},
                "truth_tier": {"target": "$.claim_class", "operation": "enum_map", "enum": {"operationally_certified_artifact": "operationally_certified_artifact"}, "parameters": {"does_not_imply_independent_real_accuracy_or_training_gold": True, "legacy_value_rejected_after_producer_freeze": True}},
                "access_mode": {"target": "$.access_mode", "operation": "enum_map", "enum": access_enum},
                "media_scope": {"target": "$.media_scope", "operation": "object_projection", "parameters": {"projection": "exact_still_frame_or_span_scope_without_widening"}},
                "release_binding": {"target": "$.release_snapshot_ref", "operation": "normalize_ref"},
                "ontology_binding": {"target": "$.evidence_manifest_refs", "operation": "normalize_ref", "parameters": {"projection": "ontology_version_hash_convention_evidence_ref"}},
                "pipeline_policy_binding": {"target": "$.promotion_gate_policy_ref", "operation": "normalize_ref", "parameters": {"also_derives": ["$.evidence_manifest_refs"], "preserve_pipeline_prompt_controller_randomness_sampler_hashes": True}},
                "execution_binding": {"target": "$.execution_stack_ref", "operation": "normalize_ref", "parameters": {"also_derives": ["$.serving_route_id", "$.capability_id"]}},
                "subject_binding": {"target": "$.owner_bindings", "operation": "array_projection"},
                "source_binding": {"target": "$.source_artifact", "operation": "object_projection", "enum": coordinate_to_main},
                "coordinate_binding": {"target": "$.transform_chain", "operation": "normalize_transform_chain", "enum": operation_to_main},
                "qualified_route_scope": {"target": "$.certificate_scope", "operation": "array_projection", "parameters": {"also_derives": ["$.serving_route_id", "$.capability_id"], "preserve_labels_contexts_risk_person_count_artifact_kinds": True}},
                "certified_output_scope": {"target": "$.certificate_scope", "operation": "array_projection", "parameters": {"also_derives": ["$.output_refs"], "exact_scope_only_required": True, "preserve_artifact_hashes_kinds_permitted_uses": True}},
                "lineage": {"target": "$.evidence_manifest_refs", "operation": "normalize_lineage"},
                "bound_artifacts": {"target": "$.output_refs", "operation": "array_projection"},
                "qa_evidence": {"target": "$.qa_bindings", "operation": "array_projection", "parameters": {"also_derives": ["$.evidence_manifest_refs"]}},
                "revocation": {"target": "$.revocation_ref", "operation": "normalize_ref", "parameters": {"also_derives": ["$.revocation_manifest_refs"]}},
                "signature": {"target": "$.raw_producer_certificate_signature", "operation": "object_projection", "parameters": {"projection": "validated_signature_value_base64", "also_derives": ["$.signature_algorithm", "$.issuer_id", "$.raw_producer_certificate_signature_trust"], "caller_supplied_trust_result_forbidden": True}},
                "external_manual_anchor_required": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_false_for_core_autonomous_runtime": True}},
                "claim_limits": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"maximum_claim": "operational_policy_conformance_for_exact_bound_artifacts", "independent_real_accuracy_claim_required_false": True, "holdout_truth_claim_required_false": True}},
            },
            "main_context_fields": {
                "raw_producer_certificate_ref": {"source_path": "$", "operation": "preserve_validated_raw_envelope", "parameters": {"projection": "immutable_ref_to_exact_strict_utf8_schema_validated_raw_bytes", "record_id_source": "$.certificate_id", "sha256_source": "exact_raw_envelope_bytes", "caller_override_forbidden": True}, "reason": "The raw certificate ref is derived exclusively from validated signed bytes.", "source_authority": "producer_wire_factual"},
                "raw_producer_certificate_signature_trust": {"source_path": "$.signature", "operation": "object_projection", "parameters": {"projection": "producer_certificate_signature_plus_out_of_band_main_trust_verification", "caller_supplied_trust_result_forbidden": True}, "source_authority": "producer_wire_factual"},
                "certificate_payload_sha256": {"operation": "hash_bind", "parameters": {"projection": "main_normalized_certificate_domain_separated_canonical_payload"}},
                "signature": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signing_result"], "sign_exact_certificate_payload_sha256": True}},
                "signature_trust": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signer_out_of_band_verification"], "caller_supplied_trust_result_forbidden": True}},
            },
        },
        {
            "producer": "mask_bridge_error", "direction": "maskfactory_to_main", "main": "wave64_maskfactory_bridge_common_v2.blocker", "main_schema_file": "wave64_maskfactory_bridge_common_v2.schema.json", "main_view": "blocker", "rule": "map_producer_error_v1_to_main_blocker_v2",
            "fields": {
                "code": {"target": "$.code", "operation": "enum_map", "enum": producer_error_to_main},
                "category": {"target": "$.category", "operation": "enum_map", "enum": {"availability": "availability", "compatibility": "compatibility", "identity": "ownership", "geometry": "transform", "authority": "authority", "quality": "quality", "resource": "availability", "security": "integrity", "request": "policy", "internal": "recovery"}},
                "retryable": {"target": "$.retryable", "operation": "identity"},
                "impact_scope": {"target": "$.blocks_scope", "operation": "enum_map", "enum": {"request_only": "dependent_pass", "dependent_pass": "dependent_pass", "run": "whole_run", "release": "required_release_path", "consumer_adoption": "required_release_path"}},
                "affected_scope": {"target": "$.evidence_refs", "operation": "array_projection", "parameters": {"projection": "affected_correlation_pass_release_capability_artifact_dimensions_to_refs"}},
                "remediation": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"retain_via_details_sha256": True, "controller_must_recompute_action_from_policy": True, "producer_remediation_is_advisory": True}},
                "no_silent_fallback": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_value": True}},
                "message": {"target": "$.message", "operation": "identity"},
                "details_sha256": {"target": "$.evidence_refs", "operation": "normalize_ref"},
            },
        },
        {
            "producer": "mask_bridge_error", "direction": "main_to_maskfactory", "main": "wave64_maskfactory_bridge_common_v2.blocker", "main_schema_file": "wave64_maskfactory_bridge_common_v2.schema.json", "main_view": "blocker", "rule": "map_main_blocker_v2_to_producer_error_v1",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}},
                "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "mask_bridge_error"}},
                "error_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["producer_error_id"]}},
                "request_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["producer_request_id_or_null"]}},
                "observed_at": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["observed_at"]}},
                "code": {"source": "$.code", "operation": "enum_map", "enum": main_error_to_producer},
                "category": {"source": "$.category", "operation": "enum_map", "enum": {"availability": "availability", "compatibility": "compatibility", "integrity": "security", "ownership": "identity", "transform": "geometry", "authority": "authority", "quality": "quality", "recovery": "internal", "policy": "request"}},
                "retryable": {"source": "$.retryable", "operation": "identity"},
                "impact_scope": {"source": "$.blocks_scope", "operation": "enum_map", "enum": {"dependent_pass": "dependent_pass", "required_release_path": "release", "whole_run": "run"}},
                "affected_scope": {"source": "$.evidence_refs", "operation": "object_projection", "parameters": {"projection": "typed_evidence_refs_to_correlation_pass_release_capability_artifact_dimensions", "unknown_ref_kind_action": "reject"}},
                "remediation": {"source": "$.retryable", "operation": "object_projection", "parameters": {"additional_sources": ["$.code", "$.blocks_scope", "$.evidence_refs"], "projection": "policy_selected_typed_remediation", "operator_authorization_not_inferred": True}},
                "no_silent_fallback": {"disposition": "default", "operation": "const", "parameters": {"value": True}},
                "message": {"source": "$.message", "operation": "identity"},
                "details_sha256": {"source": "$.evidence_refs", "operation": "hash_bind", "parameters": {"projection": "canonical_evidence_ref_list_sha256"}},
            },
        },
        {
            "producer": "maskfactory_adoption_receipt", "direction": "main_to_maskfactory", "main": "maskfactory_adoption_receipt_v2", "main_schema_file": "maskfactory_adoption_receipt_v2.schema.json", "rule": "map_main_adoption_v2_to_producer_wire_v1",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}}, "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "maskfactory_adoption_receipt"}},
                "adoption_id": {"source": "$.maskfactory_adoption_receipt_v2_id", "operation": "rename"}, "decided_at": {"source": "$.decided_at", "operation": "identity"},
                "consumer": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["controller_version", "git_commit"], "project": "Comfy_UI_Main"}},
                "adoption_scope": {"source": "$.authorized_capability_ids", "operation": "object_projection", "parameters": {"additional_sources": ["$.release_snapshot_ref", "$.consumer_requirements_ref", "$.checks"], "projection": "exact_authorized_capability_release_consumer_and_qualification_scope"}},
                "evidence_context": {"source": "$.adoption_context", "operation": "enum_map", "enum": {"fixture_validation": "conformance_fixture", "production_runtime": "runtime_evidence"}},
                "fixture_only": {"source": "$.fixture_only", "operation": "identity"},
                "production_use_authorized": {"source": "$.production_consumption_allowed", "operation": "identity"},
                "release_id": {"source": "$.release_snapshot_ref", "operation": "normalize_ref"}, "release_payload_sha256": {"source": "$.release_snapshot_ref", "operation": "hash_bind"},
                "capability_snapshot_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["exact_adopted_capability_snapshot_id"], "must_be_bound_by_release_snapshot": True}},
                "capability_snapshot_sha256": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["exact_adopted_capability_snapshot_sha256"], "must_be_bound_by_release_snapshot": True}},
                "consumer_requirements_id": {"source": "$.consumer_requirements_ref", "operation": "normalize_ref"}, "consumer_requirements_sha256": {"source": "$.consumer_requirements_ref", "operation": "hash_bind"},
                "qualification_bundle_id": {"source": "$.qualification_bundle_ref.record_id", "operation": "identity"},
                "qualification_bundle_sha256": {"source": "$.checks", "operation": "hash_bind", "parameters": {"projection": "canonical_qualification_bundle_including_all_check_evidence", "all_required_checks_must_be_present": True}},
                "trust_binding": {"source": "$.adoption_signature_trust", "operation": "object_projection", "parameters": {"additional_sources": ["$.release_signature_trust", "$.trusted_signing_key_registry_ref"], "projection": "exact_consumer_adoption_and_producer_release_key_set_binding", "producer_key_role": "consumer_adoption", "cross_role_substitution_forbidden": True}},
                "journal_checkpoint": {"source": "$.producer_journal_checkpoint_binding", "operation": "object_projection", "parameters": {"projection": "exact_signed_producer_release_journal_checkpoint_binding", "main_journal_pin_is_separate": True}},
                "decision": {"source": "$.decision", "operation": "enum_map", "enum": {"adopted": "adopted", "partially_adopted": "partially_adopted", "rejected": "rejected"}},
                "required_capabilities_satisfied": {"source": "$.production_consumption_allowed", "operation": "object_projection", "parameters": {"additional_sources": ["$.checks", "$.authorized_capability_ids", "$.decision"], "projection": "all_required_capability_checks_pass_and_authorized"}},
                "compatibility_checks": {"source": "$.checks", "operation": "array_projection"}, "pinned_artifacts": {"source": "$.release_snapshot_ref", "operation": "array_projection", "parameters": {"projection": "verified_pinned_artifacts"}},
                "capability_decisions": {"source": "$.checks", "operation": "array_projection", "parameters": {"additional_sources": ["$.authorized_capability_ids", "$.mismatch_codes"], "projection": "one_explicit_decision_per_required_optional_and_producer_extra_capability", "missing_capability_decision_action": "reject"}},
                "accepted_capabilities": {"source": "$.authorized_capability_ids", "operation": "identity"}, "rejected_capabilities": {"source": "$.mismatch_codes", "operation": "array_projection"},
                "valid_until": {"source": "$.valid_until", "operation": "identity"},
                "revalidation_triggers": {"source": "$.revalidation_triggers", "operation": "enum_map", "enum": {name: name for name in PRODUCER_INVALIDATION_REASONS}, "parameters": {"exact_closed_enum_equality_required": True}},
                "use_time_recheck_required": {"source": "$.use_time_recheck_required", "operation": "identity"},
                "adoption_payload_sha256": {"disposition": "recompute", "operation": "hash_bind", "parameters": {"scope": "canonical_producer_payload_without_adoption_payload_sha256_and_signature", "signature_is_appended_only_after_hashing": True}},
                "signature": {"source": "$.adoption_signature", "operation": "object_projection", "parameters": {"additional_sources": ["$.adoption_signature_trust"], "projection": "producer_signature_object_from_verified_main_adoption_signature", "signer_role": "main_adoption_signer", "producer_key_role": "consumer_adoption"}},
            },
        },
        {
            "producer": "mask_authority_invalidation_event", "direction": "maskfactory_to_main", "main": "maskfactory_invalidation_event_v2", "main_schema_file": "maskfactory_invalidation_event_v2.schema.json", "rule": "validate_then_apply_invalidation_v2",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}}, "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_invalidation_event_v2"}},
                "event_id": {"target": "$.event_id", "operation": "identity"},
                "stream_id": {"target": "$.stream_id", "operation": "identity"},
                "sequence": {"target": "$.sequence", "operation": "identity"},
                "causation_id": {"target": "$.causation_id", "operation": "identity"},
                "idempotency_key": {"target": "$.idempotency_key", "operation": "identity"},
                "occurred_at": {"target": "$.created_at", "operation": "rename"},
                "effective_at": {"target": "$.effective_at", "operation": "identity"},
                "evidence_context": {"disposition": "drop", "operation": "preserve_validated_raw_envelope", "parameters": {"raw_envelope_target": "$.producer_payload_ref", "fixture_maps_only_to_main_fixture_only": True}},
                "fixture_only": {"target": "$.fixture_only", "operation": "identity"},
                "producer": {"target": "$.producer_identity", "operation": "object_projection", "parameters": {"projection": "canonical_lowercase_producer_identity"}},
                "canonicalization": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_algorithm": "maskfactory-canonical-json-v1", "required_excluded_top_level_fields": ["event_payload_sha256", "signature"]}},
                "trust_binding": {"target": "$.producer_signature_trust", "operation": "object_projection", "parameters": {"projection": "producer_journal_key_binding_plus_out_of_band_main_trust_verification", "caller_supplied_trust_result_forbidden": True}},
                "reason": {"target": "$.reason", "operation": "identity", "enum": {name: name for name in PRODUCER_INVALIDATION_REASONS}},
                "severity": {"target": "$.severity", "operation": "enum_map", "enum": {"warning": "blocking", "blocking": "blocking"}, "parameters": {"warning_is_conservatively_blocking_until_policy_revalidation": True}},
                "target_transitions": {"target": "$.target_transitions", "operation": "array_projection", "parameters": {"projection": "lossless_exact_transition_fields_plus_deterministic_main_target_refs", "also_derives": ["$.affected_refs"], "context_widening_forbidden": True}},
                "required_actions": {"target": "$.required_actions", "operation": "array_projection", "parameters": {"projection": "lossless_action_transition_deadline_and_verification_policy_set", "context_widening_forbidden": True}},
                "superseding_binding": {"target": "$.superseding_binding", "operation": "object_projection", "parameters": {"null_preserved_exactly": True}},
                "rollback_binding": {"target": "$.rollback_binding", "operation": "object_projection", "parameters": {"null_preserved_exactly": True}},
                "evidence_sha256": {"target": "$.producer_evidence_sha256", "operation": "identity"},
                "event_payload_sha256": {"target": "$.producer_payload_sha256", "operation": "identity", "parameters": {"also_derives": ["$.tombstone_sha256"], "raw_ref_hash_is_exact_envelope_bytes_not_payload_digest": True}},
                "signature": {"target": "$.producer_signature", "operation": "object_projection", "parameters": {"projection": "validated_signature_value_base64", "key_id_must_equal_trust_binding_and_out_of_band_registry": True}},
            },
            "main_context_fields": {
                "correlation_id": {"source_path": "$.event_id", "operation": "object_projection", "parameters": {"projection": "deterministic_stream_and_event_identity_to_correlation_id", "external_context_forbidden": True}, "source_authority": "producer_wire_factual"},
                "producer_payload_ref": {"source_path": "$", "operation": "preserve_validated_raw_envelope", "parameters": {"projection": "immutable_ref_to_exact_strict_utf8_schema_validated_raw_bytes", "record_id_source": "$.event_id", "sha256_source": "exact_raw_envelope_bytes", "caller_override_forbidden": True}, "reason": "The producer tombstone ref is derived exclusively from validated signed bytes.", "source_authority": "producer_wire_factual"},
                "producer_signature_domain": {"operation": "const", "parameters": {"value": "maskfactory.sha256_digest_bytes.v1"}},
                "producer_payload_preserved_losslessly": {"operation": "const", "parameters": {"value": True}},
                "tombstone_sha256": {"source_path": "$.event_payload_sha256", "operation": "identity", "source_authority": "producer_wire_factual"},
                "producer_invalidation_policy_ref": {"operation": "policy_recompute", "parameters": {"projection": "exact_frozen_policy_ref_adopted_from_signed_release", "caller_override_forbidden": True}},
                "producer_invalidation_policy_sha256": {"operation": "policy_recompute", "parameters": {"value": "0dc09f41f46f9f364fb72ee092a9c808887d5bf95d2827d7990329b81cb1a0b3", "caller_override_forbidden": True}},
                "affected_refs": {"source_path": "$.target_transitions", "operation": "array_projection", "parameters": {"projection": "exact_target_identity_to_main_immutable_ref_set", "context_widening_forbidden": True}, "source_authority": "producer_wire_factual"},
                "main_enforcement_actions": {"source_path": "$.reason", "operation": "policy_recompute", "parameters": {"projection": "exact_frozen_reason_policy_to_main_actions", "caller_override_forbidden": True}, "source_authority": "producer_wire_factual"},
                "dependent_pass_only_by_default": {"operation": "const", "parameters": {"value": True}},
                "invalidation_event_sha256": {"operation": "hash_bind", "parameters": {"projection": "main_normalized_invalidation_domain_separated_canonical_payload"}},
                "normalization_signature": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signing_result"], "sign_exact_invalidation_event_sha256": True}},
                "signature_trust": {"operation": "context_lookup", "parameters": {"required_context": ["main_normalization_signer_out_of_band_verification"], "caller_supplied_trust_result_forbidden": True}},
                "supersedes_invalidation_ref": {"operation": "context_lookup", "parameters": {"required_context": ["verified_immediately_prior_invalidation_event_ref_or_null"], "must_derive_from_verified_stream_chain": True, "caller_override_forbidden": True}},
            },
        },
        {
            "producer": "mask_repair_feedback", "direction": "main_to_maskfactory", "main": "maskfactory_feedback_repair_request_v2", "main_schema_file": "maskfactory_feedback_repair_request_v2.schema.json", "rule": "map_advisory_feedback_without_truth_mutation",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}}, "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "mask_repair_feedback"}},
                "feedback_id": {"source": "$.maskfactory_feedback_repair_request_v2_id", "operation": "rename"}, "created_at": {"source": "$.created_at", "operation": "identity"}, "consumer": {"disposition": "default", "operation": "const", "parameters": {"value": "Comfy_UI_Main"}},
                "project_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_execution_scope_project_id"], "must_match_source_result": True}},
                "run_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_execution_scope_run_id"], "must_match_source_result": True}},
                "job_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_execution_scope_job_id"], "must_match_source_result": True}},
                "pass_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_execution_scope_pass_id"], "must_match_source_result": True}},
                "attempt_id": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_execution_scope_attempt_id"], "must_match_source_result": True}},
                "authentication": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_authenticated_feedback_principal_nonce_record"], "credential_material_included": False}},
                "trust_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_feedback_signing_key_binding"], "producer_key_role": "consumer_feedback", "signer_role": "main_mask_feedback_signer"}},
                "canonicalization": {"disposition": "default", "operation": "const", "parameters": {"value": {"algorithm": "maskfactory-canonical-json-v1", "excluded_top_level_fields": ["feedback_payload_sha256", "signature"]}}},
                "parent_receipt_binding": {"source": "$.source_result_ref", "operation": "object_projection", "parameters": {"projection": "exact_receipt_and_request_ids_and_signed_payload_hashes_from_source_result", "source_result_must_resolve": True}},
                "release_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_adopted_release_binding"], "must_match_source_result": True}},
                "policy_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_feedback_policy_binding"], "must_be_signed_and_current": True}},
                "certificate_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_certificate_binding"], "must_match_source_result_authority": True}},
                "source_binding": {"source": "$.source_artifact", "operation": "object_projection", "parameters": {"projection": "exact_encoded_and_decoded_source_hashes_plus_decoder_identity_from_source_result"}},
                "media_scope_sha256": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_media_scope_sha256"], "must_match_source_result": True}},
                "subject_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_subject_binding"], "must_match_source_result_owner": True}},
                "provider_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_provider_binding"], "must_match_source_result_route_and_stack": True}},
                "output_artifact_bindings": {"source": "$.affected_mask_refs", "operation": "array_projection", "parameters": {"projection": "exact_output_artifact_identity_hashes_from_source_result", "every_ref_must_resolve": True}},
                "protected_artifact_bindings": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["immutable_accepted_parent_protected_artifact_bindings"], "must_not_include_mutable_or_unaccepted_output": True}},
                "transform_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_transform_binding"], "must_match_source_result": True}},
                "qa_binding": {"source": "$.qa_evidence_refs", "operation": "object_projection", "parameters": {"additional_sources": ["$.defect_codes", "$.localized_region_ref"], "projection": "exact_qa_report_policy_and_blocking_failure_binding"}},
                "authority_binding": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["source_result_exact_authority_binding"], "feedback_cannot_escalate": True}},
                "defects": {"source": "$.defect_codes", "operation": "array_projection", "parameters": {"additional_sources": ["$.qa_evidence_refs", "$.localized_region_ref"]}},
                "hypothesis": {"source": "$.hypothesis_id", "operation": "object_projection"}, "requested_action": {"source": "$.requested_action", "operation": "enum_map", "enum": {"review": "quarantine_and_abstain", "re_predict": "mode_b_live_predict", "refine": "mode_b_live_refine", "requalify_route": "provider_rebenchmark", "issue_invalidation": "quarantine_and_abstain"}},
                "retry_budget": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["bounded_retry_budget"], "same_hypothesis_retry_allowed": False}},
                "progress_guard": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["bounded_repair_progress_guard"], "abstain_when_exhausted": True, "no_unexplained_seed_loop": True}},
                "immutable_accepted_parent": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["immutable_accepted_parent_binding"], "must_resolve_and_be_accepted": True}},
                "consumer_may_mutate_gold": {"source": "$.direct_gold_mutation_requested", "operation": "identity"}, "consumer_may_escalate_authority": {"source": "$.authority_change_requested", "operation": "identity"},
                "advisory_only": {"disposition": "default", "operation": "const", "parameters": {"value": True}},
                "feedback_payload_sha256": {"disposition": "recompute", "operation": "hash_bind", "parameters": {"scope": "canonical_producer_payload_without_feedback_payload_sha256_and_signature", "signature_is_appended_only_after_hashing": True}},
                "signature": {"disposition": "recompute", "operation": "context_lookup", "parameters": {"required_context": ["main_feedback_signing_result"], "signer_role": "main_mask_feedback_signer", "producer_key_role": "consumer_feedback", "hash_before_signature": True}},
            },
        },
        {
            "producer": "mask_bridge_event", "direction": "maskfactory_to_main", "main": "maskfactory_bridge_event_v2", "main_schema_file": "maskfactory_bridge_event_v2.schema.json", "rule": "map_producer_event_v1_to_main_event_v2",
            "fields": {
                "schema_version": {"target": "$.schema_version", "disposition": "recompute", "operation": "const", "parameters": {"value": SCHEMA_VERSION}}, "record_type": {"target": "$.record_type", "disposition": "recompute", "operation": "const", "parameters": {"value": "maskfactory_bridge_event_v2"}},
                "event_id": {"target": "$.maskfactory_bridge_event_v2_id", "operation": "rename"}, "sequence": {"target": "$.sequence", "operation": "identity"}, "occurred_at": {"target": "$.created_at", "operation": "rename"},
                "canonicalization": {"disposition": "drop", "operation": "drop_after_validation", "parameters": {"required_algorithm": "maskfactory-canonical-json-v1", "required_excluded_top_level_fields": ["event_payload_sha256"]}},
                "event_type": {"target": "$.event_type", "operation": "normalize_event", "parameters": {"unmapped_event_action": "reject"}}, "correlation_id": {"target": "$.correlation_id", "operation": "identity"},
                "subject": {"target": "$.aggregate_ref", "operation": "normalize_ref"}, "payload_schema": {"target": "$.payload_ref", "operation": "normalize_ref", "parameters": {"additional_sources": ["$.payload_sha256"]}},
                "previous_event_sha256": {"target": "$.previous_event_sha256", "operation": "identity"}, "event_payload_sha256": {"target": "$.event_sha256", "operation": "identity"},
            },
        },
        {
            "producer": "mask_bridge_event", "direction": "main_to_maskfactory", "main": "maskfactory_bridge_event_v2", "main_schema_file": "maskfactory_bridge_event_v2.schema.json", "rule": "map_main_event_v2_to_producer_event_v1",
            "fields": {
                "schema_version": {"disposition": "default", "operation": "const", "parameters": {"value": "1.0.0"}}, "record_type": {"disposition": "default", "operation": "const", "parameters": {"value": "mask_bridge_event"}},
                "event_id": {"source": "$.maskfactory_bridge_event_v2_id", "operation": "rename"}, "sequence": {"source": "$.sequence", "operation": "identity"}, "stream_id": {"source": "$.stream_id", "operation": "identity"}, "occurred_at": {"source": "$.created_at", "operation": "rename"},
                "evidence_context": {"source": "$.fixture_only", "operation": "enum_map", "enum": {"true": "conformance_fixture", "false": "runtime_evidence"}, "parameters": {"boolean_enum_keys": True}},
                "fixture_only": {"source": "$.fixture_only", "operation": "identity"},
                "canonicalization": {"disposition": "default", "operation": "const", "parameters": {"value": {"algorithm": "maskfactory-canonical-json-v1", "excluded_top_level_fields": ["event_payload_sha256", "signature"]}}},
                "trust_binding": {"source": "$.signature_trust", "operation": "object_projection", "parameters": {"projection": "main_event_signer_to_consumer_journal_key_binding", "signer_role": "main_bridge_event_signer", "producer_key_role": "consumer_journal"}},
                "journal_epoch": {"source": "$.journal_pin", "operation": "object_projection", "parameters": {"projection": "signed_main_journal_epoch_and_checkpoint_identity", "forks_forbidden": True}},
                "event_type": {"source": "$.event_type", "operation": "normalize_event", "parameters": {"unmapped_event_action": "reject"}}, "producer": {"disposition": "default", "operation": "const", "parameters": {"value": "Comfy_UI_Main"}}, "correlation_id": {"source": "$.correlation_id", "operation": "identity"}, "causation_id": {"source": "$.causation_id", "operation": "identity"},
                "subject": {"source": "$.aggregate_ref", "operation": "object_projection"},
                "state_transition": {"source": "$.lifecycle_transition", "operation": "object_projection", "parameters": {"projection": "exact_execution_state_and_reconciliation_transition"}},
                "payload_schema": {"source": "$.payload_ref", "operation": "object_projection"}, "payload_sha256": {"source": "$.payload_ref.sha256", "operation": "identity"}, "previous_event_sha256": {"source": "$.previous_event_sha256", "operation": "identity"},
                "event_payload_sha256": {"disposition": "recompute", "operation": "hash_bind", "parameters": {"scope": "canonical_producer_payload_without_event_payload_sha256_and_signature", "signature_is_appended_only_after_hashing": True}},
                "signature": {"source": "$.signature", "operation": "object_projection", "parameters": {"additional_sources": ["$.signature_trust"], "projection": "producer_signature_object_from_verified_main_event_signature", "signer_role": "main_bridge_event_signer", "producer_key_role": "consumer_journal"}},
            },
        },
    ]


def build_executable_mapping_registry(schemas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mappings: list[dict[str, Any]] = []
    for spec in mapping_specs():
        producer_name = spec["producer"]
        producer = PRODUCER_SCHEMA_BINDINGS[producer_name]
        producer_required = set(producer.get("required", producer["properties"]))
        unknown_override_fields = set(spec.get("fields", {})) - set(producer["properties"])
        if unknown_override_fields:
            raise ValueError(f"mapping {spec['rule']} contains obsolete/non-schema producer fields: {sorted(unknown_override_fields)}")
        if spec["direction"] == "main_to_maskfactory":
            missing_required_overrides = producer_required - set(spec.get("fields", {}))
            if missing_required_overrides:
                raise ValueError(f"mapping {spec['rule']} leaves required producer fields to uncontrolled fallback: {sorted(missing_required_overrides)}")
        main_schema, main_properties, main_required = main_schema_view(schemas, spec)
        main_contract_name = spec["main"]
        direction = spec["direction"]
        rules: list[dict[str, Any]] = []
        main_covered: set[str] = set()

        def add_rule(*, source_path: str | None, target_path: str | None, disposition: str, operation: str, enum_conversion: dict[str, Any] | None = None, parameters: dict[str, Any] | None = None, reason: str, source_required: bool, target_required: bool, source_authority: str, target_authority: str) -> None:
            index = len(rules) + 1
            rules.append({
                "field_rule_id": f"{spec['rule']}.{index:03d}", "direction": direction,
                "source_path": source_path, "target_path": target_path,
                "source_required": source_required, "target_required": target_required,
                "disposition": disposition,
                "transform": mapping_transform(operation, enum_conversion=enum_conversion, parameters=parameters),
                "authority": mapping_authority(source_authority, target_authority), "reason": reason,
            })

        for property_name in producer["properties"]:
            override = spec.get("fields", {}).get(property_name, {})
            enum_conversion = override.get("enum")
            parameters = override.get("parameters")
            reason = override.get("reason", "Exact-schema validation precedes this explicit field disposition; the immutable producer payload hash remains in evidence.")
            if direction == "maskfactory_to_main":
                target = override.get("target")
                disposition = override.get("disposition", "map" if target else "drop")
                operation = override.get("operation", "rename" if target else "drop_after_validation")
                add_rule(
                    source_path=f"$.{property_name}", target_path=target, disposition=disposition, operation=operation,
                    enum_conversion=enum_conversion, parameters=parameters, reason=reason,
                    source_required=property_name in producer_required, target_required=bool(target), source_authority="producer_wire_factual",
                    target_authority="main_internal_factual" if target else "none",
                )
                if target and target.startswith("$."):
                    main_covered.add(target[2:].split(".", 1)[0])
            else:
                source = override.get("source")
                disposition = override.get("disposition", "map" if source else "recompute")
                operation = override.get("operation", "rename" if source else "context_lookup")
                add_rule(
                    source_path=source, target_path=f"$.{property_name}", disposition=disposition, operation=operation,
                    enum_conversion=enum_conversion, parameters=parameters, reason=reason,
                    source_required=bool(source), target_required=property_name in producer_required,
                    source_authority="main_internal_factual" if source else "none", target_authority="producer_wire_factual",
                )
                if source and source.startswith("$."):
                    main_covered.add(source[2:].split(".", 1)[0])

        for property_name in main_properties:
            if property_name in main_covered:
                continue
            if direction == "maskfactory_to_main":
                context_override = spec.get("main_context_fields", {}).get(property_name, {})
                add_rule(
                    source_path=context_override.get("source_path"), target_path=f"$.{property_name}",
                    disposition=context_override.get("disposition", "recompute"),
                    operation=context_override.get("operation", "context_lookup"),
                    parameters=context_override.get("parameters", {"required_context": [property_name], "missing_context_action": "reject"}),
                    reason=context_override.get("reason", "Required Main normalized field is derived only from validated controller context; missing context blocks normalization."),
                    source_required=False, target_required=property_name in main_required,
                    source_authority=context_override.get("source_authority", "none"), target_authority="main_internal_factual",
                )
            else:
                add_rule(
                    source_path=f"$.{property_name}", target_path=None, disposition="drop", operation="drop_after_validation",
                    parameters={"retained_in_main_record": True},
                    reason="Main-only field is intentionally absent from the producer wire payload and remains in the immutable Main source record.",
                    source_required=property_name in main_required, target_required=False, source_authority="main_internal_factual", target_authority="none",
                )
            main_covered.add(property_name)

        if direction == "maskfactory_to_main":
            add_rule(source_path="$.*", target_path=None, disposition="reject", operation="drop_after_validation", parameters={"match": "unmapped_source_field"}, reason="Any producer field not enumerated above is rejected before the dependent pass.", source_required=False, target_required=False, source_authority="none", target_authority="none")
        else:
            add_rule(source_path=None, target_path="$.*", disposition="reject", operation="drop_after_validation", parameters={"match": "unmapped_target_field"}, reason="Any producer target field not enumerated above is rejected before serialization.", source_required=False, target_required=False, source_authority="none", target_authority="none")

        main_schema_source = f"Plan/08_SCHEMAS/{spec['main_schema_file']}"
        if spec.get("main_view") == "blocker":
            main_schema_source += "#/$defs/blocker"
        mappings.append({
            "mapping_rule_id": spec["rule"], "direction": direction,
            "producer_contract_name": producer_name, "main_contract_name": main_contract_name,
            "source_contract_role": "producer_wire_v1" if direction == "maskfactory_to_main" else "main_internal_v2",
            "target_contract_role": "main_internal_v2" if direction == "maskfactory_to_main" else "producer_wire_v1",
            "producer_binding": {
                "contract_name": producer_name, "contract_role": "producer_wire_v1", "schema_source": producer["schema_source"],
                "schema_id": producer["schema_id"], "schema_version": producer["schema_version"], "schema_sha256": producer["schema_sha256"],
            },
            "main_binding": {
                "contract_name": main_contract_name, "contract_role": "main_internal_v2", "schema_source": main_schema_source,
                "schema_id": main_schema["$id"], "schema_version": SCHEMA_VERSION, "schema_sha256": sha256_bytes(canonical_json(main_schema)),
            },
            "exact_producer_binding_required": True, "field_rules": rules,
            "covered_producer_top_level_paths": [f"$.{name}" for name in producer["properties"]],
            "producer_required_paths": [f"$.{name}" for name in producer["properties"] if name in producer_required],
            "covered_main_top_level_paths": [f"$.{name}" for name in main_properties],
            "main_required_paths": [f"$.{name}" for name in main_required],
            "unknown_source_field_action": "reject", "unknown_target_field_action": "reject",
            "unmapped_required_field_action": "block_dependent_pass",
            "recursive_subtree_policy": "validate_against_exact_bound_schema_then_execute_named_transform",
        })

    mapping_schema = schemas["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json"]
    authority_schema = schemas["maskfactory_authority_decision_v2.schema.json"]
    return {
        "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_producer_wire_to_main_port_mapping_v2", "updated_at": UPDATED_AT,
        "mapping_schema_binding": {"contract_name": "wave64_maskfactory_producer_wire_to_main_port_mapping_v2", "contract_role": "main_internal_v2", "schema_source": "Plan/08_SCHEMAS/wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json", "schema_id": mapping_schema["$id"], "schema_version": SCHEMA_VERSION, "schema_sha256": sha256_bytes(canonical_json(mapping_schema))},
        "producer_schema_authority": "exact_schema_name_version_hash_imported_from_adopted_maskfactory_release",
        "main_schema_authority": "internal_normalized_port_and_import_validation_only", "path_language": "rfc9535_jsonpath",
        "unknown_or_missing_mapping_action": "block_dependent_pass",
        "producer_use_eligibility_policy": {
            "source_path": "$.use_eligibility", "producer_value_authoritative_for_main_use": False,
            "normalization_action": "drop_after_validation",
            "main_recompute_contract_binding": {"contract_name": "maskfactory_authority_decision_v2", "contract_role": "main_internal_v2", "schema_source": "Plan/08_SCHEMAS/maskfactory_authority_decision_v2.schema.json", "schema_id": authority_schema["$id"], "schema_version": SCHEMA_VERSION, "schema_sha256": sha256_bytes(canonical_json(authority_schema))},
            "main_target_path": "$.eligible_for_intended_use", "recompute_rule": "evaluate_exact_signed_pinned_main_policy_unique_criteria_claim_class_trusted_signer_decision_timestamp_certificate_expiry_current_revocation_index_and_nonfixture_evidence",
        },
        "mappings": mappings, "runtime_completion_claimed": False,
    }


def build_registries(schemas: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    schemas = schemas or build_schemas()
    authority_matrix = []
    for mode in ACCESS_MODES:
        for state in AUTHORITY_STATES:
            authority_matrix.append({
                "access_mode": mode,
                "authority_state": state,
                "access_mode_implies_authority": False,
                "promotion_eligible_by_state_alone": False,
                "operational_certificate_required_when_certified": True,
            })
    return {
        "wave64_maskfactory_bridge_authority_crosswalk_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_authority_crosswalk_v2", "updated_at": UPDATED_AT,
            "access_modes": ACCESS_MODES, "authority_states": AUTHORITY_STATES, "issuer_kinds": ISSUER_KINDS, "claim_classes": CLAIM_CLASSES,
            "default_authority_by_access_mode": {"mode_a_package_read": "authority_record_required_no_default", "mode_b_live_predict": "draft", "mode_b_live_refine": "draft"},
            "all_modes_certified_rule": "allowed_only_for_one_exact_output_when_an_active_trust_anchored_operational_certificate_binds_release_capability_access_mode_execution_stack_runtime_source_media_frame_output_owner_transform_qa_policy_scope_issuer_time_and_current_revocation_index",
            "operational_claim_firewall": {"operationally_certified_artifact_can_support_exact_permitted_core_production_use": True, "counts_as_independent_real_accuracy": False, "counts_as_training_gold": False, "legacy_autonomous_certified_gold_alias_allowed": False},
            "mode_a_unconditionally_promotable": False, "mode_b_permanently_nonpromotable": False, "human_anchor_required_for_core": False,
            "matrix": authority_matrix, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_error_taxonomy_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_error_taxonomy_v2", "updated_at": UPDATED_AT,
            "errors": [
                {"code": code, "category": category, "retryable": retryable, "default_scope": "dependent_pass"}
                for code, category, retryable in [
                    ("MFB_RELEASE_NOT_ADOPTED", "compatibility", False), ("MFB_SCHEMA_SOURCE_DRIFT", "compatibility", False),
                    ("MFB_SCHEMA_VERSION_DRIFT", "compatibility", False), ("MFB_SCHEMA_HASH_DRIFT", "compatibility", False),
                    ("MFB_API_CONTRACT_DRIFT", "compatibility", False), ("MFB_ONTOLOGY_DRIFT", "compatibility", False),
                    ("MFB_PACKAGE_NOT_FOUND", "availability", False), ("MFB_SERVICE_OFFLINE", "availability", True),
                    ("MFB_TIMEOUT", "availability", True), ("MFB_SUBMISSION_UNKNOWN", "recovery", False),
                    ("MFB_OUTPUT_HASH_MISMATCH", "integrity", False), ("MFB_OWNER_AMBIGUOUS", "ownership", False),
                    ("MFB_PERSON_INDEX_CONFLICT", "ownership", False), ("MFB_TRANSFORM_ROUNDTRIP_FAIL", "transform", False),
                    ("MFB_CERTIFICATE_MISSING", "authority", False), ("MFB_CERTIFICATE_SCOPE_MISMATCH", "authority", False),
                    ("MFB_CERTIFICATE_NOT_YET_VALID", "authority", False), ("MFB_CERTIFICATE_EXPIRED", "authority", False),
                    ("MFB_CERTIFICATE_REVOKED", "authority", False), ("MFB_CLAIM_CLASS_MISMATCH", "authority", False),
                    ("MFB_UNTRUSTED_SIGNING_KEY", "integrity", False), ("MFB_SIGNER_REVOKED", "integrity", False),
                    ("MFB_JOURNAL_CHECKPOINT_UNTRUSTED", "integrity", False), ("MFB_JOURNAL_FORK", "integrity", False),
                    ("MFB_STALE_REVOCATION_INDEX", "authority", False), ("MFB_MEDIA_SCOPE_MISMATCH", "integrity", False),
                    ("MFB_RUNTIME_PROVENANCE_MISMATCH", "integrity", False), ("MFB_INPUT_OUTPUT_IDENTITY_COLLISION", "integrity", False),
                    ("MFB_CANONICALIZATION_MISMATCH", "security", False), ("MFB_AUTH_FAILED", "security", False),
                    ("MFB_NONCE_REPLAY", "security", False), ("MFB_ARCHIVE_PATH_ESCAPE", "security", False),
                    ("MFB_INVALID_STATE_TRANSITION", "recovery", False),
                    ("MFB_PROTECTED_REGION_LEAK", "quality", False), ("MFB_CACHE_INVALIDATED", "recovery", False),
                ]
            ], "silent_fallback_allowed": False, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_compatibility_policy_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_compatibility_policy_v2", "updated_at": UPDATED_AT,
            "required_exact_checks": ["release_snapshot_sha256", "wire_schema_name", "schema_source", "schema_id", "schema_version", "schema_sha256", "semantic_invariant_profile_hash", "api_openapi_hash", "package_format_hash", "ontology_hash", "node_pack_hash", "certificate_format_hash", "trusted_signing_key_registry_hash", "release_signature_trust", "journal_checkpoint_head_hash"],
            "canonical_payload_security_policy": {
                "exact_profile_name_version_hash_from_adopted_release_required": True,
                "wire_encoding": "utf-8", "duplicate_object_keys": "reject", "nonfinite_numbers": "reject",
                "signature_domain_separation_required": True, "payload_hash_and_signature_exclusions_must_match_bound_profile": True,
                "unknown_or_ambiguous_canonicalization_action": "reject_before_hash_or_signature_verification",
            },
            "request_authentication_and_replay_policy": {
                "authenticated_principal_required_for_production": True, "authorization_bound_to_exact_route_and_capability": True,
                "request_payload_hash_bound_to_idempotency_key": True, "nonce_required_for_production": True,
                "nonce_uniqueness_scope": "trusted_principal_plus_route_plus_release", "nonce_reuse_action": "reject_and_audit",
                "timestamp_window_and_clock_skew_source": "exact_adopted_producer_security_profile", "unknown_outcome_must_reconcile_before_resubmit": True,
            },
            "safe_release_import_policy": {
                "manifest_before_extract_required": True, "extract_to_isolated_staging_required": True,
                "absolute_parent_traversal_drive_unc_and_device_paths": "reject", "symlink_hardlink_reparse_escape": "reject",
                "case_collision_and_duplicate_member_names": "reject", "declared_size_and_expansion_limits_required": True,
                "post_extract_manifest_hash_verification_required": True, "atomic_activation_after_full_verification_only": True,
            },
            "dirty_worktree_consumption_allowed": False, "mutable_latest_allowed": False, "partial_adoption_production_allowed": False,
            "installed_node_pack_implies_compatibility": False, "semantic_version_overrides_hash_mismatch": False, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2", "updated_at": UPDATED_AT,
            "hard_filters_before_ranking": True, "newer_draft_overwrites_stronger_authority": False, "protected_region_default": "protected_wins",
            "quality_retry_requires_new_hypothesis": True, "transport_retry_reuses_idempotency_key": True, "unknown_submission_requires_reconciliation": True,
            "execution_lifecycle": {
                "states": EXECUTION_STATES,
                "allowed_transitions": ALLOWED_EXECUTION_TRANSITIONS,
                "terminal_states": ["succeeded", "failed", "cancelled"], "outcome_unknown_is_terminal": False,
                "reconciliation_outcomes": ["found_running", "found_completed_pending_receipt", "found_failed", "not_found_safe_to_submit"],
                "not_found_safe_to_submit_authorizes_exactly_one_resubmission": True,
                "running_and_completed_pending_receipt_are_not_collapsed_to_terminal_states": True,
                "backward_or_unlisted_transition_action": "reject_and_record_incident", "resubmit_from_outcome_unknown_allowed": False,
                "reconciliation_must_bind_original_request_hash_idempotency_key_structured_remote_outcome_and_signed_evidence": True,
            },
            "circuit_breaker_scope": "exact_route", "cache_is_content_addressed": True, "invalidation_tombstone_before_delete": True,
            "restart_replays_tombstones_before_cache": True, "signed_checkpoint_head_required": True, "journal_fork_deletion_reorder_or_reseal_action": "reject_and_quarantine",
            "unrelated_dag_branches_continue": True, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_completion_profile_registry_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_completion_profile_registry_v2", "updated_at": UPDATED_AT,
            "profiles": [
                {"profile": "core_autonomous_runtime", "required_for_core_release": True, "human_anchor_required": False, "daz_scale_required": False},
                {"profile": "independent_real_accuracy", "required_for_core_release": False, "human_anchor_required": "policy_optional", "daz_scale_required": False},
                {"profile": "scale_daz_maturity", "required_for_core_release": False, "human_anchor_required": False, "daz_scale_required": True},
            ], "optional_profile_absence_blocks_core": False, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_invalidation_policy_binding_v2.json": producer_invalidation_policy_document(),
        "wave64_maskfactory_bridge_contract_catalog_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_contract_catalog_v2", "updated_at": UPDATED_AT,
            "contracts": [
                {
                    "contract_name": name.removesuffix(".schema.json"), "path": f"Plan/08_SCHEMAS/{name}", "schema_id": schema["$id"], "schema_version": SCHEMA_VERSION,
                    "schema_sha256": sha256_bytes(canonical_json(schema)),
                    "owner": "main_controller", "surface": "main_internal_normalized_v2_or_import_validation_view", "direction": "internal_or_as_declared_by_mapping",
                    "producer_wire_authority": False, "producer_schema_must_be_pinned_from_release": True,
                }
                for name, schema in schemas.items()
            ],
            "producer_wire_contracts": [
                {
                    "contract_name": name, "schema_owner": "maskfactory", "surface": "producer_wire_v1", "direction": direction,
                    "schema_binding_source": "adopted_maskfactory_release_snapshot_only", "local_main_schema_is_authoritative": False,
                    "schema_id": PRODUCER_SCHEMA_BINDINGS[name]["schema_id"], "schema_version": PRODUCER_SCHEMA_BINDINGS[name]["schema_version"],
                    "schema_sha256": PRODUCER_SCHEMA_BINDINGS[name]["schema_sha256"], "development_schema_source": PRODUCER_SCHEMA_BINDINGS[name]["schema_source"],
                }
                for name, direction in [
                    ("maskfactory_release_snapshot", "maskfactory_to_main"), ("maskfactory_capability_snapshot", "maskfactory_to_main"),
                    ("maskfactory_consumer_requirements", "main_to_maskfactory"), ("mask_bridge_semantic_invariant_profile", "maskfactory_to_main"),
                    ("mask_acquisition_request", "main_to_maskfactory"), ("mask_acquisition_receipt", "maskfactory_to_main"),
                    ("operational_autonomy_certificate", "maskfactory_to_main"), ("mask_bridge_error", "bidirectional"),
                    ("maskfactory_adoption_receipt", "main_to_maskfactory"), ("mask_authority_invalidation_event", "maskfactory_to_main"),
                    ("mask_repair_feedback", "main_to_maskfactory"), ("mask_bridge_event", "bidirectional"),
                ]
            ],
            "autonomous_intelligence_authority_policy": {
                "llm_vlm_outputs_must_be_schema_bound": True, "retrieval_evidence_refs_must_be_immutable_and_hash_bound": True,
                "conversation_or_compaction_summary_is_durable_project_truth": False, "llm_vlm_observation_is_promotion_authority": False,
                "llm_can_propose_requests_routes_hypotheses_and_repairs": True, "llm_can_self_promote_or_mutate_producer_truth": False,
                "tool_gateway_is_only_execution_surface": True, "deterministic_validator_policy_and_signed_evidence_own_admission_authority_and_promotion": True,
                "memory_write_requires_schema_validation_provenance_and_event_journal_admission": True,
            },
            "model_library_dependency_deferral": {
                "existing_model_intelligence_master_plan": "Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_AND_SELECTION_MASTER_PLAN.md",
                "existing_activation_gate_registry": "Plan/10_REGISTRIES/wave64_model_library_activation_gate_registry.json",
                "existing_operation_protocol": "Plan/Instructions/AUTONOMOUS_MODEL_LIBRARY_INGESTION_QUALIFICATION_SELECTION_AND_LEARNING_PROTOCOL.md",
                "existing_main_session_handoff": "Plan/Instructions/Hydration_Rehydration/AUTONOMOUS_MODEL_INTELLIGENCE_MAIN_SESSION_HANDOFF.md",
                "owned_rows": [223, 260], "declared_discovery_records": 7282,
                "complete_intended_library_downloaded": False, "dry_run_ingestion_activated": False,
                "all_7282_record_dry_run_ingestion_deferred": True, "pilot_qualification_deferred": True,
                "bundle_solver_implementation_and_benchmark_runner_activation_deferred": True,
                "autonomous_router_llm_vlm_and_app_model_activation_deferred": True,
                "activation_requires": ["explicit_user_or_main_task_declaration_complete_model_download", "exact_main_inventory_verification"],
                "sole_activation_authority": "explicit_complete_download_declaration_plus_exact_main_inventory_verification",
                "bridge_cannot_clear_or_bypass_deferral": True,
                "full_library_required_for_bridge_core": False, "no_bridge_or_core_gate_may_require_full_library": True,
                "bridge_may_use_current_installed_qualified_subset": True, "duplicate_model_intelligence_package": False,
                "current_state": "deferred_waiting_for_complete_model_download",
            },
            "producer_planning_provenance": {
                "repository": "KevinSGarrett/MaskingUltimate", "branch": "codex/mask-autonomy-bridge-plan",
                "commit": "938b469", "pull_request": "https://github.com/KevinSGarrett/MaskingUltimate/pull/2",
                "planning_preservation_manifest_sha256": "13fda3eab823e4a544f171c5570ceed99e77cd246ccbc13e686879616682bde2",
                "planning_manifest_entries": 113, "wire_schema_count": 12,
                "immutable_producer_packet_commit": "938b46949e277d92f26d9411fd5710005c506677",
                "integration_head": "e6d6c6bdf00a0702d274455fbf07ded2b3a838b3",
                "current_pr_validation_head": "30008808957f484b0989329843d72e1c22d044da",
                "integration_base_commit": "85d4c19b7974c1b64f48176d91211defbaba35a0",
                "integration_strategy": "non_rewriting_merge_commit",
                "integration_reconciliation_manifest": "Plan/Instructions/11_AUTONOMOUS_CORE_BRIDGE_INTEGRATION_RECONCILIATION_MANIFEST.json",
                "integration_reconciliation_manifest_sha256": "d382e55b6c78deed983a9b56672349f1915fa60a4acd0328f831c2bc84acba77",
                "base_owned_supersession_count": 6, "integration_protocol_update_count": 2,
                "unaccounted_integration_drift_count": 0, "wire_schemas_unchanged_after_integration": True,
                "planning_bindings_finalized": True, "runtime_release_state": "unpublished_unadopted",
                "runtime_release_is_required_before_production_adoption": True,
            },
            "schema_source_version_hash_required_at_runtime": True, "unknown_or_missing_producer_mapping_fails_closed": True, "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json": build_executable_mapping_registry(schemas),
        "wave64_maskfactory_bridge_app_read_model_mapping_v2.json": {
            "schema_version": SCHEMA_VERSION,
            "registry_id": "wave64_maskfactory_bridge_app_read_model_mapping_v2",
            "updated_at": UPDATED_AT,
            "readiness_projection_contract": {
                "name": "maskfactory_bridge_readiness_projection_v2",
                "schema_id": schemas["maskfactory_bridge_readiness_projection_v2.schema.json"]["$id"],
                "schema_version": SCHEMA_VERSION,
                "schema_sha256": sha256_bytes(canonical_json(schemas["maskfactory_bridge_readiness_projection_v2.schema.json"])),
            },
            "pages": [
                {
                    "page_id": "home_readiness", "display_name": "Home / Readiness",
                    "read_models": ["maskfactory_bridge_readiness_projection_v2", "maskfactory_health_capability_snapshot_v2", "maskfactory_bridge_release_certificate_v2"],
                    "field_paths": ["$.release_snapshot_ref", "$.adoption_receipt_ref", "$.bridge_release_certificate_ref", "$.active_pin_status", "$.profile_readiness", "$.row218_status", "$.rows321_347_status", "$.row348_release_status", "$.signing_trust_status", "$.journal_integrity_status", "$.journal_pin", "$.page_readiness", "$.core_blockers", "$.optional_profile_blockers"],
                    "purpose": "Show truthful current readiness, exact blockers, optional-profile separation, and runtime-evidence provenance.",
                },
                {
                    "page_id": "projects_revisions", "display_name": "Projects / Revisions",
                    "read_models": ["maskfactory_release_snapshot_v2", "maskfactory_adoption_receipt_v2", "maskfactory_invalidation_event_v2"],
                    "field_paths": ["$.release_id", "$.snapshot_sha256", "$.producer_source", "$.contract_bindings", "$.signature_trust", "$.decision", "$.checks", "$.trusted_signing_key_registry_ref", "$.journal_pin", "$.revalidation_triggers", "$.affected_refs"],
                    "purpose": "Show exact producer release pins, Main adoption decisions, revision lineage, and invalidation state.",
                },
                {
                    "page_id": "scene_builder_pose_masks", "display_name": "Scene Builder / Pose & Masks",
                    "read_models": ["maskfactory_bridge_request_v2", "maskfactory_bridge_result_v2", "maskfactory_authority_decision_v2"],
                    "field_paths": ["$.scope", "$.media_scope", "$.source_artifact", "$.scene_owner_roster", "$.owner_bindings", "$.target_region_bindings", "$.protected_region_bindings", "$.mask_intents", "$.transform_chain", "$.input_region_lineage", "$.masks", "$.authority", "$.eligible_for_intended_use", "$.blockers"],
                    "purpose": "Show exact target identity, cross-character/prop/environment protected ownership, still/frame/span scope, typed transforms, separate input ROI/output lineage, and policy-scoped eligibility.",
                },
                {
                    "page_id": "runs_dag", "display_name": "Runs / DAG",
                    "read_models": ["maskfactory_bridge_event_v2", "maskfactory_bridge_request_v2", "maskfactory_bridge_result_v2", "maskfactory_authority_decision_v2"],
                    "field_paths": ["$.stream_id", "$.sequence", "$.correlation_id", "$.causation_id", "$.event_type", "$.aggregate_ref", "$.payload_ref", "$.scope", "$.attempt_number", "$.hypothesis", "$.execution_observation", "$.media_scope", "$.status", "$.cache_state", "$.decision", "$.blockers"],
                    "purpose": "Project exact project/run/job/pass/attempt/hypothesis, selected route and alternatives, timing/resources, media scope, validation, authority, cache, and dependent-pass state into the durable DAG.",
                },
                {
                    "page_id": "queue_workers", "display_name": "Queue / Workers",
                    "read_models": ["maskfactory_health_capability_snapshot_v2", "maskfactory_bridge_event_v2", "maskfactory_bridge_request_v2", "maskfactory_bridge_result_v2"],
                    "field_paths": ["$.service_status", "$.routes", "$.observed_at", "$.expires_at", "$.event_type", "$.idempotency_key", "$.correlation_id", "$.resource_envelope", "$.deadline_at", "$.execution_observation.queue_ms", "$.execution_observation.runtime_ms", "$.execution_observation.peak_vram_mb", "$.execution_observation.peak_ram_mb", "$.execution_observation.deadline_met", "$.execution_observation.resource_envelope_met"],
                    "purpose": "Show route freshness, worker eligibility, exact queue/runtime/resource facts, deadline/envelope enforcement, retries, and circuit state without direct service control.",
                },
                {
                    "page_id": "recovery", "display_name": "Recovery",
                    "read_models": ["maskfactory_invalidation_event_v2", "maskfactory_bridge_event_v2", "maskfactory_bridge_result_v2"],
                    "field_paths": ["$.reason", "$.affected_refs", "$.required_action", "$.tombstone_sha256", "$.signature_trust", "$.stream_id", "$.sequence", "$.previous_event_sha256", "$.event_sha256", "$.journal_pin", "$.cache_state", "$.blockers"],
                    "purpose": "Show trusted signed checkpoint/head replay, fork/deletion/reorder/reseal rejection, invalidation tombstones, reconciliation, cache safety, repair, rollback, and resume state.",
                },
                {
                    "page_id": "qa", "display_name": "QA",
                    "read_models": ["maskfactory_bridge_result_v2", "maskfactory_authority_decision_v2", "maskfactory_promotion_gate_policy_v2", "maskfactory_operational_certificate_v2"],
                    "field_paths": ["$.qa_record_refs", "$.authority.authority_state", "$.authority.claim_class", "$.criterion_evaluations", "$.eligible_for_intended_use", "$.decision_at", "$.certificate_temporal_evaluation", "$.certificate_signature_trust", "$.policy_sha256", "$.signature_trust", "$.criteria", "$.genuine_runtime_evidence_refs", "$.certificate_scope", "$.media_scope", "$.blockers"],
                    "purpose": "Show factual QA separately from exact-use authority, accuracy/training claims, signed policy criteria, current certificate/revocation/signer validity, media scope, and genuine runtime evidence.",
                },
            ],
            "all_pages_read_only": True,
            "controller_gateway_is_only_write_authority": True,
            "app_can_mutate_producer_truth": False,
            "app_can_commit_promotion": False,
            "app_or_conversation_summary_can_establish_project_truth": False,
            "llm_vlm_can_bypass_schema_validator_or_signed_policy": False,
            "fixture_can_project_runtime_ready": False,
            "runtime_completion_claimed": False,
        },
        "wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json": {
            "schema_version": SCHEMA_VERSION, "registry_id": "wave64_maskfactory_bridge_legacy_migration_crosswalk_v2", "updated_at": UPDATED_AT,
            "migrations": [
                {
                    "legacy_surface": "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md#qa_strictness_live_control",
                    "legacy_authority": "none_for_core_runtime",
                    "v2_replacement": "maskfactory_promotion_gate_policy_v2",
                    "migration_rule": "display_or_proposal_only_live_value_cannot_mutate_pinned_core_policy",
                    "validator_required": True,
                },
                {
                    "legacy_surface": "Plan/08_SCHEMAS/mask_factory_contract.schema.json#promotion_gates_string_array",
                    "legacy_authority": "diagnostic_only",
                    "v2_replacement": "maskfactory_promotion_gate_policy_v2.criteria",
                    "migration_rule": "each_string_requires_explicit_versioned_criterion_comparator_threshold_evidence_analyzer_manifest_revocation_manifest_and_blocking_flag",
                    "validator_required": True,
                },
                {
                    "legacy_surface": "Plan/Tracker/README.md#wave70_manual_gold_blocker",
                    "legacy_authority": "historical_wording_no_core_authority",
                    "v2_replacement": "maskfactory_operational_certificate_v2_and_maskfactory_authority_decision_v2",
                    "migration_rule": "core_accepts_exact_active_unrevoked_maskfactory_autonomous_authority; human anchors apply only to independent_real_accuracy",
                    "validator_required": True,
                },
                {
                    "legacy_surface": "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md#gold_mask_dependency",
                    "legacy_authority": "term_requires_authority_qualified_interpretation",
                    "v2_replacement": "authority_qualified_exact_mask_not_necessarily_manual",
                    "migration_rule": "core Foley accepts adopted exact-output autonomous authority with matching scope lineage QA and Main policy",
                    "validator_required": True,
                },
                {
                    "legacy_surface": "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json",
                    "legacy_authority": "immutable_historical_evidence_only",
                    "v2_replacement": "profile_scoped_current_authority_evaluation",
                    "migration_rule": "preserve_report_bytes; its manual blocker cannot block core and may apply only to an explicitly selected independent_real_accuracy claim",
                    "historical_evidence_mutable": False,
                    "validator_required": True,
                },
            ],
            "legacy_string_gate_can_authorize_promotion": False,
            "live_qa_dial_can_mutate_core_decision": False,
            "optional_independent_accuracy_can_mutate_core_decision": False,
            "runtime_completion_claimed": False,
        },
    }


def base_example(record_type: str, char: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "record_type": record_type, f"{record_type}_id": f"{record_type}_fixture_001",
        "revision": "r001", "created_at": UPDATED_AT, "fixture_only": True, "runtime_completion_claimed": False,
    }


def contract_binding(name: str, char: str = "1") -> dict[str, str]:
    return {"wire_schema_name": name, "schema_source": f"Plan/08_SCHEMAS/{name}.schema.json", "schema_id": f"{SCHEMA_BASE}/{name}.schema.json", "schema_version": SCHEMA_VERSION, "schema_sha256": h(char)}


def producer_contract_binding(name: str, char: str = "1") -> dict[str, str]:
    del char
    binding = PRODUCER_SCHEMA_BINDINGS[name]
    return {
        "wire_schema_name": name,
        "schema_source": f"maskfactory_release://contracts/{name}.schema.json",
        "schema_id": binding["schema_id"],
        "schema_version": binding["schema_version"],
        "schema_sha256": binding["schema_sha256"],
    }


def fixture_scope() -> dict[str, str]:
    return {"project_id": "project_fixture_001", "run_id": "run_fixture_001", "job_id": "job_fixture_001", "pass_id": "pass_fixture_001", "attempt_id": "attempt_fixture_001", "scene_id": "scene_fixture_001", "shot_id": "shot_fixture_001", "take_id": "take_fixture_001"}


def fixture_source() -> dict[str, Any]:
    return {"artifact_ref": ref("image_artifact", "source_fixture_001", "2"), "sha256": h("2"), "width": 1024, "height": 1024, "color_space": "srgb", "coordinate_space": "source_pixels"}


def fixture_media_scope() -> dict[str, Any]:
    return {"media_kind": "still_image", "source_media_ref": ref("image_artifact", "source_fixture_001", "2"), "source_media_sha256": h("2"), "frame_index": None, "pts_ticks": None, "timebase_numerator": None, "timebase_denominator": None, "span_start_frame": None, "span_end_frame": None, "neighbor_frame_refs": [], "temporal_evidence_refs": [], "exact_frame_scope_only": True}


def fixture_owner(role: str = "target", index: int = 0) -> dict[str, Any]:
    return {"character_instance_id": f"character_instance_fixture_{index:03d}", "provider_person_index": index, "owner_role": role, "assignment_evidence_refs": [ref("owner_assignment", f"owner_fixture_{index:03d}", str((index + 3) % 10))]}


def fixture_transform() -> dict[str, Any]:
    coordinate = {"coordinate_space": "source_pixels", "width": 1024, "height": 1024}
    step = {"sequence": 0, "operation": "identity", "input": dict(coordinate), "output": dict(coordinate), "parameters": {"parameter_type": "identity"}, "inverse_strategy": "exact_inverse"}
    step["step_sha256"] = sha256_bytes(canonical_json(step))
    chain = {
        "chain_id": "transform_chain_fixture_001", "canonical_hash_profile": "main_sorted_utf8_json_v2_excluding_self_hash", "source": dict(coordinate), "output": dict(coordinate),
        "steps": [step],
        "roundtrip_policy": {"required": True, "maximum_error_pixels": 0.5, "reject_noninvertible": True},
        "roundtrip_evidence_refs": [ref("transform_roundtrip_evidence", "transform_roundtrip_fixture_001", "e")],
    }
    chain["chain_sha256"] = sha256_bytes(canonical_json(chain))
    return chain


def fixture_signing_trust(
    *, trusted: bool = False, key_id: str = "maskfactory_fixture_signer",
    signer_role: str = "maskfactory_release_signer",
) -> dict[str, Any]:
    return {
        "signature_algorithm": "ed25519" if trusted else "fixture_local_hash_attestation",
        "signing_key_id": key_id,
        "signer_role": signer_role,
        "embedded_public_key_sha256": h("d"),
        "trusted_key_registry_ref": ref("trusted_signing_key_registry", "main_maskfactory_trust_registry_fixture", "c"),
        "trusted_key_entry_sha256": h("d"),
        "trust_anchor_source": "main_out_of_band_trusted_key_registry",
        "embedded_public_key_is_trust_anchor": False,
        "signature_verified": True,
        "trust_anchor_matched": trusted,
        "key_status": "active" if trusted else "fixture_untrusted",
        "trust_result": "trusted" if trusted else "fixture_only_untrusted",
        "verified_at": UPDATED_AT,
        "verification_evidence_ref": ref("signature_verification_evidence", f"signature_verification_{key_id}", "d"),
    }


def fixture_journal_pin(*, trusted: bool = False) -> dict[str, Any]:
    return {
        "stream_id": "maskfactory_bridge_fixture_stream", "checkpoint_ref": ref("maskfactory_journal_checkpoint", "checkpoint_fixture_001", "9"),
        "checkpoint_sequence": 1, "head_event_sha256": h("9"), "previous_checkpoint_sha256": None,
        "checkpointed_at": UPDATED_AT, "fresh_until": "2026-07-18T02:20:00-05:00",
        "checkpoint_payload_sha256": h("9"), "checkpoint_signature_domain": "comfy_ui_main.maskfactory_journal_checkpoint.v2",
        "checkpoint_signature": "fixture-journal-checkpoint-signature-not-runtime-authority",
        "checkpoint_signature_trust": fixture_signing_trust(trusted=trusted, signer_role="main_journal_checkpoint_signer"), "forks_allowed": False, "deletion_or_reorder_allowed": False,
    }


def fixture_producer_journal_checkpoint_binding(release: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_release_ref": copy.deepcopy(release["raw_producer_release_ref"]),
        "release_payload_sha256": release["snapshot_sha256"],
        "stream_id": "maskfactory-release-journal",
        "genesis_event_id": "mfbevt_000000000000000000000001", "genesis_event_sha256": h("1"),
        "first_sequence": 1, "last_sequence": 1, "event_count": 1,
        "head_event_id": "mfbevt_000000000000000000000001", "head_event_sha256": h("9"),
        "revocation_state_sha256": h("8"), "active_revocation_count": 0, "validator_sha256": h("7"),
        "checkpointed_at": UPDATED_AT, "fresh_until": "2026-07-18T02:20:00-05:00",
        "producer_and_main_journal_domains_are_separate": True,
    }


def fixture_scene_roster() -> dict[str, Any]:
    return {
        "roster_ref": ref("scene_owner_roster", "scene_owner_roster_fixture_001", "b"),
        "target_character_instance_id": "character_instance_fixture_000",
        "character_instance_ids": ["character_instance_fixture_000", "character_instance_fixture_001"],
        "prop_instance_ids": ["prop_instance_fixture_001"], "environment_instance_id": "environment_instance_fixture_001",
    }


def fixture_region(*, role: str = "target", relationship: str = "self", owner_id: str = "character_instance_fixture_000", index: int = 0, sha_char: str = "a") -> dict[str, Any]:
    owner_type = "character_instance" if relationship in {"self", "other_character"} else relationship
    return {
        "region_id": f"{role}_region_fixture_{index:03d}", "region_ref": ref("input_region", f"{role}_region_fixture_{index:03d}", sha_char),
        "region_sha256": h(sha_char), "source_artifact_sha256": h("2"), "region_role": role, "selector_kind": "roi_constraint",
        "owner_entity_type": owner_type, "owner_entity_id": owner_id, "relationship_to_target": relationship,
        "provider_person_index": index if owner_type == "character_instance" else None, "label": "person" if owner_type == "character_instance" else owner_type,
        "coordinate_space": "source_pixels", "width": 1024, "height": 1024, "transform_chain_sha256": fixture_transform()["chain_sha256"], "transform_step_sequence": 0,
        "assignment_evidence_refs": [ref("owner_assignment", f"region_owner_fixture_{index:03d}", sha_char)],
    }


def fixture_resource_envelope() -> dict[str, Any]:
    return {"maximum_runtime_ms": 30000, "maximum_queue_ms": 5000, "maximum_vram_mb": 24576, "maximum_ram_mb": 65536, "maximum_output_bytes": 104857600, "priority": "normal", "allow_cpu_fallback": False}


def fixture_runtime_provenance() -> dict[str, Any]:
    return {"runtime_kind": "windows_native_venv", "operating_system": "Windows", "architecture": "x86_64", "python_version": "3.12", "runtime_manifest_ref": ref("runtime_manifest", "runtime_manifest_fixture_001", "5"), "environment_lock_sha256": h("5"), "container_image_digest": None}


def fixture_execution_observation() -> dict[str, Any]:
    return {
        "execution_scope": fixture_scope(), "attempt_number": 1,
        "hypothesis": {"hypothesis_id": "hypothesis_initial_fixture_001", "hypothesis_class": "initial", "material_change_sha256": None, "retry_kind": "initial"},
        "admitted_at": "2026-07-17T02:20:00-05:00", "queue_started_at": "2026-07-17T02:20:01-05:00", "execution_started_at": "2026-07-17T02:20:02-05:00", "completed_at": "2026-07-17T02:20:04-05:00",
        "queue_ms": 1000, "runtime_ms": 2000, "peak_vram_mb": 1024, "peak_ram_mb": 2048, "output_bytes": 4096,
        "deadline_met": True, "resource_envelope_met": True, "selected_route_id": "live_predict_fixture_route", "selection_reason_code": "eligible_ranked_champion",
        "eligible_alternative_route_ids": ["live_predict_fixture_alternative"], "route_selection_evidence_refs": [ref("route_selection_evidence", "route_selection_fixture_001", "6")],
        "factual_not_promotion_authority": True,
    }


def fixture_authority(state: str = "draft", issuer: str = "maskfactory_autonomous", certified: bool = False) -> dict[str, Any]:
    claim_class = "operationally_certified_artifact" if certified else ("qa_passed_machine_candidate" if state == "qa_passed_noncertified" else "machine_candidate")
    return {"authority_state": state, "issuer_kind": issuer, "claim_class": claim_class, "certificate_ref": ref("maskfactory_operational_certificate_v2", "certificate_fixture_001", "8") if certified else None, "certificate_scope": ["mask_target_edit"] if certified else [], "verified_at": UPDATED_AT, "revocation_checked_at": UPDATED_AT}


def fixture_release_gate_report(gate_id: str, *, passed: bool = False, trusted: bool = False, runtime: bool = False) -> dict[str, Any]:
    row_token = gate_id.removeprefix("row").removesuffix("_runtime")
    report = {
        "gate_id": gate_id, "status": "pass" if passed else "blocked", "derived_pass": passed,
        "subject_ref": ref("wave64_requirement_row", f"item_w64_{row_token}", "a"),
        "gate_report_ref": ref("maskfactory_bridge_gate_report_v2", f"{gate_id}_report", "0"),
        "gate_report_sha256": h("0"), "evaluator_manifest_ref": ref("gate_evaluator_manifest", f"{gate_id}_evaluator", "b"),
        "gate_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_gate_hash_signature_and_signature_trust",
        "signature_domain": "comfy_ui_main.maskfactory_bridge_release_gate_report.v2", "gate_report_signature": "fixture-gate-report-signature-not-runtime-authority",
        "evidence_refs": [ref("gate_evidence", f"{gate_id}_evidence", "c")],
        "genuine_runtime_evidence_refs": [ref("runtime_gate_evidence", f"{gate_id}_runtime_evidence", "d")] if runtime else [],
        "evaluated_at": UPDATED_AT, "signature_trust": fixture_signing_trust(trusted=trusted, key_id="maskfactory_production_signer_001" if trusted else "maskfactory_fixture_signer", signer_role="main_bridge_gate_signer"),
    }
    seal_release_gate_report(report)
    return report


def build_examples() -> dict[str, dict[str, Any]]:
    release = {
        **base_example("maskfactory_release_snapshot_v2", "1"), "release_id": "maskfactory_release_fixture_001", "snapshot_sha256": h("1"), "raw_producer_release_ref": ref("maskfactory_release_snapshot", "producer_release_fixture_001", "a"),
        "release_status": "fixture", "published_at": UPDATED_AT,
        "release_context": "fixture_validation", "genuine_runtime_evidence_refs": [],
        "release_signature_domain": "maskfactory.sha256_digest_bytes.v1", "release_signature": "fixture-release-snapshot-signature-not-runtime-authority",
        "normalization_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust", "normalization_payload_sha256": h("1"),
        "normalization_signature_domain": "comfy_ui_main.maskfactory_normalized_release.v2", "normalization_signature": "fixture-release-normalization-signature-not-runtime-authority", "normalization_signature_trust": fixture_signing_trust(signer_role="main_normalization_signer"),
        "producer_source": {"repository_id": "comfy_ui_main_masking", "commit_sha": "a" * 40, "tag": "maskfactory_v2_fixture_001", "source_clean": True},
        "contract_bindings": [producer_contract_binding("mask_acquisition_request", "1"), producer_contract_binding("mask_acquisition_receipt", "2"), producer_contract_binding("operational_autonomy_certificate", "3")],
        "component_bindings": [{"component": name, "version": "fixture-1", "sha256": h(char)} for name, char in [("api_openapi", "3"), ("package_format", "4"), ("ontology", "5"), ("node_pack", "6")]],
        "capability_refs": [ref("capability_registry", "capability_fixture_001", "3")], "certificate_refs": [], "revocation_refs": [], "artifact_refs": [ref("release_artifact", "artifact_fixture_001", "4")],
        "signature_trust": fixture_signing_trust(),
        "completion_profiles": {"core_autonomous_runtime": "planned", "independent_real_accuracy": "not_claimed", "scale_daz_maturity": "not_claimed"}, "mutable_worktree_consumption_allowed": False,
    }
    seal_normalized_release(release)
    release_ref = immutable_release_ref(release)
    consumer = {
        **base_example("maskfactory_consumer_requirements_v2", "2"), "completion_profile": "core_autonomous_runtime",
        "required_contract_bindings": [producer_contract_binding("mask_acquisition_request", "1"), producer_contract_binding("mask_acquisition_receipt", "2"), producer_contract_binding("operational_autonomy_certificate", "3")],
        "supported_access_modes": ACCESS_MODES, "minimum_authority_state": "draft", "allowed_issuer_kinds": ["maskfactory_autonomous", "human_anchor_optional"], "allowed_claim_classes": ["machine_candidate", "qa_passed_machine_candidate", "operationally_certified_artifact"], "required_certificate_scope": ["mask_target_edit"],
        "required_labels": ["person", "hand", "face", "hair", "clothing"], "maximum_person_count": 4, "required_transform_operations": ["identity", "crop", "resize", "pad", "horizontal_flip", "project"],
        "maximum_latency_ms": 30000, "human_anchor_required_for_core": False, "scale_daz_required_for_core": False,
        "trusted_signing_key_registry_ref": ref("trusted_signing_key_registry", "main_maskfactory_trust_registry_fixture", "c"), "required_signing_key_ids": ["maskfactory_production_signer_001"],
        "required_signature_algorithm": "ed25519", "embedded_public_key_may_establish_trust": False,
    }
    adoption = {
        **base_example("maskfactory_adoption_receipt_v2", "3"), "consumer_requirements_ref": ref("maskfactory_consumer_requirements_v2", "consumer_fixture_001", "2"), "release_snapshot_ref": copy.deepcopy(release_ref),
        "decided_at": UPDATED_AT, "valid_until": "2026-07-18T02:20:00-05:00", "use_time_recheck_required": True,
        "adoption_context": "fixture_validation", "genuine_runtime_evidence_refs": [],
        "decision": "rejected", "checks": [
            {"check": check_id, "status": "fail" if check_id == "wire_schema_set" else "not_applicable", "expected": "exact", "observed": "fixture_not_qualified", "evidence_ref": ref("compatibility_evidence", f"{check_id}_fixture_evidence", "3")}
            for check_id in REQUIRED_ADOPTION_CHECK_IDS
        ],
        "qualification_bundle_ref": ref("maskfactory_adoption_qualification_bundle_v2", "qualification_bundle_fixture_001", "0"), "qualification_bundle_sha256": h("0"),
        "mismatch_codes": ["MFB_SCHEMA_HASH_DRIFT"], "authorized_capability_ids": [], "production_consumption_allowed": False, "active_pin_written": False,
        "trusted_signing_key_registry_ref": ref("trusted_signing_key_registry", "main_maskfactory_trust_registry_fixture", "c"), "release_signature_trust": fixture_signing_trust(signer_role="maskfactory_release_signer"),
        "capability_snapshot_ref": ref("maskfactory_capability_snapshot", "capability_snapshot_fixture_001", "3"), "capability_snapshot_status": "current",
        "capability_observed_at": UPDATED_AT, "capability_valid_until": "2026-07-18T02:20:00-05:00",
        "capability_revocation_checked_at": UPDATED_AT, "capability_revocation_valid_until": "2026-07-18T02:20:00-05:00",
        "capability_status_evidence_ref": ref("capability_status_evidence", "capability_status_fixture_001", "3"), "operational_certificate_evaluations": [],
        "producer_journal_checkpoint_binding": fixture_producer_journal_checkpoint_binding(release),
        "journal_pin": fixture_journal_pin(), "adoption_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_receipt_hash_signature_and_signature_trust",
        "adoption_signature_domain": "comfy_ui_main.maskfactory_adoption_receipt.v2", "adoption_signature": "fixture-adoption-signature-not-runtime-authority", "adoption_signature_trust": fixture_signing_trust(signer_role="main_adoption_signer"), "all_required_signatures_trusted": False,
        "producer_invalidation_policy_ref": producer_invalidation_policy_ref(), "producer_invalidation_policy_sha256": producer_invalidation_policy_sha256(),
        "revalidation_triggers": list(PRODUCER_INVALIDATION_REASONS), "revalidation_rules": build_revalidation_rules(),
    }
    seal_adoption_receipt(adoption)
    adoption_ref = immutable_adoption_ref(adoption)
    request = {
        **base_example("maskfactory_bridge_request_v2", "4"), "correlation_id": "correlation_fixture_001", "idempotency_key": "idempotency_fixture_001", "scope": fixture_scope(),
        "attempt_number": 1, "hypothesis": {"hypothesis_id": "hypothesis_initial_fixture_001", "hypothesis_class": "initial", "material_change_sha256": None, "retry_kind": "initial"},
        "access_mode": "mode_b_live_predict", "source_artifact": fixture_source(), "media_scope": fixture_media_scope(), "owner_bindings": [fixture_owner()], "scene_owner_roster": fixture_scene_roster(),
        "target_region_bindings": [fixture_region()], "protected_region_bindings": [fixture_region(role="protected", relationship="other_character", owner_id="character_instance_fixture_001", index=1, sha_char="b")],
        "mask_intents": [{"intent_id": "intent_person_001", "label": "person", "purpose": "target_edit", "mask_type": "binary"}], "transform_chain": fixture_transform(), "roundtrip_tolerance_pixels": 0.5,
        "release_snapshot_ref": copy.deepcopy(release_ref), "expected_contract_bindings": [producer_contract_binding("mask_acquisition_request", "1"), producer_contract_binding("mask_acquisition_receipt", "2")],
        "minimum_authority_state": "draft", "accepted_issuer_kinds": ["maskfactory_autonomous"], "accepted_claim_classes": ["machine_candidate", "qa_passed_machine_candidate", "operationally_certified_artifact"], "required_certificate_scope": [], "intended_use": "preview", "deadline_at": "2026-07-17T03:20:00-05:00", "retry_class": "transport_only", "resource_envelope": fixture_resource_envelope(), "production_promotion_requested": False,
    }
    certificate = {
        **base_example("maskfactory_operational_certificate_v2", "5"), "maskfactory_operational_certificate_v2_id": "certificate_fixture_001", "certification_context": "fixture_validation", "claim_class": "operationally_certified_artifact", "status": "active", "issuer_kind": "maskfactory_autonomous", "issuer_id": "maskfactory_autonomous_issuer_fixture", "signature_algorithm": "local_hash_attestation", "raw_producer_certificate_ref": ref("operational_autonomy_certificate", "producer_certificate_fixture_001", "a"), "raw_producer_certificate_payload_sha256": h("a"), "raw_producer_certificate_signature_domain": "maskfactory.sha256_digest_bytes.v1", "raw_producer_certificate_signature": "fixture-producer-certificate-signature", "raw_producer_certificate_signature_trust": fixture_signing_trust(signer_role="maskfactory_operational_certificate_signer"), "certificate_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_certificate_hash_signature_and_signature_trust", "certificate_payload_sha256": h("5"), "signature_domain": "comfy_ui_main.maskfactory_operational_certificate.v2", "signature": "fixture-certificate-normalization-signature", "signature_trust": fixture_signing_trust(signer_role="main_normalization_signer"), "issued_at": UPDATED_AT, "expires_at": "2026-07-18T02:20:00-05:00",
        "release_snapshot_ref": copy.deepcopy(release_ref), "capability_id": "live_predict_certified_fixture", "serving_route_id": "live_predict_fixture_route", "access_mode": "mode_b_live_predict", "execution_stack_ref": ref("execution_stack", "stack_fixture_001", "5"), "runtime_provenance": fixture_runtime_provenance(),
        "source_artifact": fixture_source(), "media_scope": fixture_media_scope(), "output_refs": [ref("mask_artifact", "mask_fixture_001", "6")], "owner_bindings": [fixture_owner()], "transform_chain": fixture_transform(),
        "qa_bindings": [{"qa_record_ref": ref("mask_qa_record", "qa_fixture_001", "7"), "gate_id": "mask_core_gate", "result": "pass"}],
        "promotion_gate_policy_ref": ref("maskfactory_promotion_gate_policy_v2", "promotion_policy_fixture_001", "5"), "evidence_manifest_refs": [ref("evidence_manifest", "evidence_manifest_fixture_001", "7")], "genuine_runtime_evidence_refs": [],
        "certificate_scope": ["mask_target_edit"], "revocation_manifest_refs": [ref("revocation_manifest", "revocation_manifest_fixture_001", "8")], "revocation_ref": None,
    }
    promotion_policy = {
        **base_example("maskfactory_promotion_gate_policy_v2", "5"), "maskfactory_promotion_gate_policy_v2_id": "promotion_policy_fixture_001", "policy_version": "2.0.0", "policy_context": "fixture_validation", "completion_profile": "core_autonomous_runtime",
        "policy_artifact_ref": ref("maskfactory_promotion_gate_policy_v2", "promotion_policy_fixture_001", "5"), "policy_sha256": h("5"),
        "policy_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_policy_hash_signature_signature_trust_and_artifact_ref_hash", "signature_domain": "comfy_ui_main.maskfactory_promotion_gate_policy.v2", "signature": "fixture-promotion-policy-signature-not-runtime-authority", "signature_trust": fixture_signing_trust(signer_role="main_promotion_policy_signer"),
        "criteria": [
            {"criterion_id": "transform_roundtrip", "dimension": "roundtrip_error_pixels", "comparator": "lte", "threshold": 0.5, "evidence_type": "deterministic_transform_report", "analyzer_manifest_ref": ref("analyzer_manifest", "transform_analyzer_fixture_001", "5"), "blocking": True},
            {"criterion_id": "protected_region", "dimension": "protected_region_leak", "comparator": "eq", "threshold": 0, "evidence_type": "protected_region_report", "analyzer_manifest_ref": ref("analyzer_manifest", "protected_analyzer_fixture_001", "6"), "blocking": True},
        ],
        "evidence_manifest_refs": [ref("evidence_manifest", "evidence_manifest_fixture_001", "7")], "genuine_runtime_evidence_refs": [], "revocation_manifest_refs": [ref("revocation_manifest", "revocation_manifest_fixture_001", "8")],
        "live_qa_strictness_control_authoritative": False, "runtime_policy_mutable_from_app": False, "optional_independent_accuracy_can_mutate_core_decision": False, "legacy_string_gate_authoritative": False,
    }
    seal_promotion_policy(promotion_policy)
    certificate["promotion_gate_policy_ref"] = copy.deepcopy(promotion_policy["policy_artifact_ref"])
    seal_operational_certificate(certificate)
    mask = {"mask_ref": ref("mask_artifact", "mask_fixture_001", "6"), "mask_sha256": h("6"), "label": "person", "mask_type": "binary", "coordinate_space": "source_pixels", "width": 1024, "height": 1024, "owner": fixture_owner(), "authority": fixture_authority(), "lineage_kind": "original", "parents": [], "derivation_operation": "none"}
    result = {
        **base_example("maskfactory_bridge_result_v2", "6"), "request_ref": ref("maskfactory_bridge_request_v2", "request_fixture_001", "4"), "release_snapshot_ref": copy.deepcopy(release_ref),
        "raw_producer_receipt_ref": ref("mask_acquisition_receipt", "producer_receipt_fixture_001", "a"), "raw_producer_receipt_payload_sha256": h("a"),
        "raw_producer_receipt_signature_domain": "maskfactory.mask_acquisition_receipt.v1", "raw_producer_receipt_signature": "fixture-producer-receipt-signature-not-runtime-authority", "raw_producer_receipt_signature_trust": fixture_signing_trust(signer_role="maskfactory_receipt_signer"),
        "normalization_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust", "normalization_payload_sha256": h("6"),
        "normalization_signature_domain": "comfy_ui_main.maskfactory_normalized_result.v2", "normalization_signature": "fixture-normalization-signature-not-runtime-authority", "normalization_signature_trust": fixture_signing_trust(signer_role="main_normalization_signer"),
        "access_mode": "mode_b_live_predict", "status": "succeeded", "source_artifact": fixture_source(), "media_scope": fixture_media_scope(), "route_id": "live_predict_fixture_route", "execution_stack_ref": ref("execution_stack", "stack_fixture_001", "5"),
        "owner_bindings": [fixture_owner()], "transform_chain": fixture_transform(),
        "input_region_lineage": {"target_region_refs": [ref("input_region", "target_region_fixture_000", "a")], "protected_region_refs": [ref("input_region", "protected_region_fixture_001", "b")], "request_transform_chain_sha256": fixture_transform()["chain_sha256"], "input_roi_hashes_are_output_artifact_hashes": False, "mode_a_exact_selector_exception_applied": False},
        "execution_observation": fixture_execution_observation(), "roundtrip_max_error_pixels": 0.0, "authority": fixture_authority(), "authority_aggregation_rule": "minimum_of_all_mask_authorities", "operational_certificate_ref": None,
        "masks": [mask], "qa_record_refs": [ref("mask_qa_record", "qa_fixture_001", "7")], "blockers": [], "cache_state": "fresh_written",
    }
    seal_normalized_result(result)
    authority = {
        **base_example("maskfactory_authority_decision_v2", "7"), "result_ref": ref("maskfactory_bridge_result_v2", "result_fixture_001", "6"), "access_mode": "mode_b_live_predict", "observed_authority": fixture_authority(),
        "required_authority_state": "draft", "required_issuer_kinds": ["maskfactory_autonomous"], "required_claim_classes": ["machine_candidate"], "required_certificate_scope": [], "intended_use": "preview", "decision": "diagnostic_only", "eligible_for_intended_use": False,
        "decision_at": UPDATED_AT, "certificate_temporal_evaluation": None, "certificate_signature_trust": None,
        "decision_evidence_refs": [ref("authority_decision_evidence", "decision_evidence_fixture_001", "5")], "genuine_runtime_evidence_refs": [],
        "consumer_policy_ref": copy.deepcopy(promotion_policy["policy_artifact_ref"]), "consumer_policy_sha256": promotion_policy["policy_sha256"],
        "criterion_evaluations": [
            {"criterion_id": "transform_roundtrip", "comparator": "lte", "threshold": 0.5, "observed": 0.0, "status": "pass", "evidence_ref": ref("transform_report", "transform_report_fixture_001", "5")},
            {"criterion_id": "protected_region", "comparator": "eq", "threshold": 0, "observed": 0, "status": "pass", "evidence_ref": ref("protected_region_report", "protected_region_report_fixture_001", "6")},
        ],
        "crosswalk_rule_id": "authority_draft_preview_allowed_by_exact_policy", "blockers": [],
    }
    health = {
        **base_example("maskfactory_health_capability_snapshot_v2", "8"), "release_snapshot_ref": copy.deepcopy(release_ref), "service_status": "healthy", "observed_at": UPDATED_AT, "expires_at": "2026-07-17T02:25:00-05:00", "api_contract": producer_contract_binding("maskfactory_capability_snapshot", "8"),
        "routes": [{"route_id": "live_predict_fixture_route", "access_mode": "mode_b_live_predict", "status": "available", "default_authority_state": "draft", "maximum_authority_state": "certified", "operational_certificate_required_above_default": True, "supported_labels": ["person", "hand", "face", "hair", "clothing"], "execution_stack_ref": ref("execution_stack", "stack_fixture_001", "5")}],
        "current_mode_b_default_authority_state": "draft",
    }
    invalidation = {
        **base_example("maskfactory_invalidation_event_v2", "9"), "stream_id": "maskfactory_invalidation_fixture_stream", "event_id": "invalidation_event_fixture_001", "sequence": 1,
        "correlation_id": "invalidation_correlation_fixture_001", "causation_id": None, "idempotency_key": "invalidation_idempotency_fixture_001", "reason": "certificate_revoked",
        "occurred_at": UPDATED_AT, "producer_identity": "maskfactory", "severity": "blocking", "producer_evidence_sha256": h("8"), "producer_signature_domain": "maskfactory.sha256_digest_bytes.v1", "producer_signature": "fixture-producer-invalidation-signature", "producer_signature_trust": fixture_signing_trust(signer_role="maskfactory_invalidation_signer"),
        "producer_payload_ref": ref("mask_authority_invalidation_event", "producer_invalidation_fixture_001", "9"), "producer_payload_sha256": h("9"), "producer_payload_preserved_losslessly": True,
        "producer_invalidation_policy_ref": producer_invalidation_policy_ref(), "producer_invalidation_policy_sha256": producer_invalidation_policy_sha256(),
        "target_transitions": [{
            "transition_id": "transition_fixture_001", "target_kind": "certificate", "target_id": "certificate_fixture_001", "target_sha256": h("8"),
            "previous_authority_state": "certified", "new_authority_state": "invalid", "previous_certificate_status": "active", "new_certificate_status": "revoked",
            "reason_code": "certificate_revoked", "scope_sha256": h("6"), "main_target_ref": ref("maskfactory_operational_certificate_v2", "certificate_fixture_001", "8"), "unrelated_scope_preserved": True,
        }],
        "affected_refs": [ref("maskfactory_operational_certificate_v2", "certificate_fixture_001", "8")],
        "required_actions": [
            {"action_id": "action_block_fixture_001", "transition_ids": ["transition_fixture_001"], "action": "block_dependent_pass", "deadline_at": UPDATED_AT, "verification_evidence_required": True, "verification_policy_sha256": h("7")},
            {"action_id": "action_revalidate_fixture_001", "transition_ids": ["transition_fixture_001"], "action": "revalidate_adoption", "deadline_at": UPDATED_AT, "verification_evidence_required": True, "verification_policy_sha256": h("7")},
        ],
        "main_enforcement_actions": ["block_and_revalidate"], "effective_at": UPDATED_AT, "supersedes_invalidation_ref": None, "superseding_binding": None, "rollback_binding": None,
        "dependent_pass_only_by_default": True, "tombstone_sha256": h("9"), "invalidation_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_invalidation_hash_normalization_signature_and_trust_records", "normalization_signature_domain": "comfy_ui_main.maskfactory_invalidation_event.v2", "normalization_signature": "fixture-invalidation-normalization-signature", "signature_trust": fixture_signing_trust(signer_role="main_normalization_signer"),
    }
    seal_invalidation_event(invalidation)
    bridge_event = {
        **base_example("maskfactory_bridge_event_v2", "9"), "stream_id": "maskfactory_bridge_fixture_stream", "sequence": 1, "correlation_id": "correlation_fixture_001", "causation_id": None, "event_type": "request_admitted",
        "aggregate_ref": ref("maskfactory_bridge_request_v2", "request_fixture_001", "4"), "payload_ref": ref("maskfactory_bridge_request_v2", "request_fixture_001", "4"),
        "idempotency_key": "idempotency_fixture_001", "previous_event_sha256": None,
        "lifecycle_transition": {"from_state": "compiled", "to_state": "admitted", "transition_reason_code": "request_validated_and_admitted", "request_payload_sha256": h("4"), "reconciliation_ref": None, "remote_receipt_ref": None, "reconciliation": None, "resubmission_authorization_ref": None, "resubmission_authorization_consumed": False},
        "event_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_event_hash_signature_trust_and_pin", "signature_domain": "comfy_ui_main.maskfactory_bridge_event.v2",
        "signature": "fixture-event-signature-not-runtime-authority", "signature_trust": fixture_signing_trust(signer_role="main_bridge_event_signer"), "journal_pin": fixture_journal_pin(), "authoritative_for_maskfactory_truth": False,
    }
    bridge_event["event_sha256"] = bridge_event_sha256(bridge_event)
    bridge_event["journal_pin"]["head_event_sha256"] = bridge_event["event_sha256"]
    feedback = {
        **base_example("maskfactory_feedback_repair_request_v2", "a"), "source_result_ref": ref("maskfactory_bridge_result_v2", "result_fixture_001", "6"), "source_artifact": fixture_source(), "affected_mask_refs": [ref("mask_artifact", "mask_fixture_001", "6")], "defect_codes": ["boundary_leak"], "localized_region_ref": ref("region_artifact", "region_fixture_001", "a"), "qa_evidence_refs": [ref("mask_qa_record", "qa_fixture_001", "7")], "requested_action": "refine", "hypothesis_id": "hypothesis_boundary_protected_001", "direct_gold_mutation_requested": False, "authority_change_requested": False, "response_expected_via_release_or_event": True,
    }
    integration = {
        **base_example("maskfactory_bridge_release_certificate_v2", "b"), "completion_profile": "core_autonomous_runtime", "release_context": "fixture_validation", "status": "blocked", "release_snapshot_ref": copy.deepcopy(release_ref), "adoption_receipt_ref": copy.deepcopy(adoption_ref), "row218_runtime_passed": False, "rows321_347_runtime_passed": False, "trusted_signing_identity_checks_passed": False, "journal_checkpoint_checks_passed": False,
        "journal_pin": fixture_journal_pin(), "checks": [fixture_release_gate_report(gate_id) for gate_id in REQUIRED_BRIDGE_RELEASE_GATE_IDS],
        "genuine_runtime_evidence_refs": [], "release_allowed": False, "release_hash_profile": "main_domain_separated_sorted_utf8_json_v2_excluding_release_certificate_hash_signature_and_signature_trust",
        "release_signature_domain": "comfy_ui_main.maskfactory_bridge_release_certificate.v2", "release_signature": "fixture-row348-release-signature-not-runtime-authority", "release_signature_trust": fixture_signing_trust(signer_role="main_bridge_release_signer"),
        "independent_real_accuracy_required": False, "scale_daz_maturity_required": False,
    }
    seal_bridge_release_certificate(integration)
    page_ids = ["home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"]
    readiness = {
        **base_example("maskfactory_bridge_readiness_projection_v2", "c"),
        "projection_as_of": UPDATED_AT,
        "project_ref": ref("project", "comfy_ui_main_fixture", "c"),
        "revision_ref": ref("project_revision", "wave64_bridge_planning_fixture", "c"),
        "release_snapshot_ref": None,
        "adoption_receipt_ref": None,
        "bridge_release_certificate_ref": None,
        "active_pin_status": "missing",
        "row218_status": "planned",
        "rows321_347_status": "planned",
        "row348_release_status": "planned",
        "signing_trust_status": "fixture_only_untrusted",
        "journal_integrity_status": "fixture_only",
        "profile_readiness": [
            {"completion_profile": "core_autonomous_runtime", "required_for_core_release": True, "status": "planned", "evidence_refs": [ref("planning_coverage", "coverage_fixture_001", "b")], "blockers": []},
            {"completion_profile": "independent_real_accuracy", "required_for_core_release": False, "status": "not_started", "evidence_refs": [], "blockers": []},
            {"completion_profile": "scale_daz_maturity", "required_for_core_release": False, "status": "not_started", "evidence_refs": [], "blockers": []},
        ],
        "page_readiness": [{"page_id": page_id, "status": "not_ready", "source_read_model_ids": ["maskfactory_bridge_readiness_projection_v2"], "evidence_refs": [ref("planning_coverage", "coverage_fixture_001", "b")], "blocker_codes": ["MFB_RUNTIME_EVIDENCE_MISSING"]} for page_id in page_ids],
        "event_cursor": {"stream_id": "maskfactory_bridge_fixture_stream", "last_sequence": 1, "last_event_sha256": h("9")},
        "journal_pin": fixture_journal_pin(),
        "genuine_runtime_evidence_refs": [],
        "runtime_readiness_claimed": False,
        "projection_authority": "read_only_derived_no_execution_or_promotion_authority",
        "core_blockers": [{"code": "MFB_RUNTIME_EVIDENCE_MISSING", "category": "policy", "message": "Planning fixtures do not establish runtime readiness.", "retryable": False, "blocks_scope": "required_release_path", "completion_profile": "core_autonomous_runtime", "core_impact": "blocking", "evidence_refs": [ref("planning_coverage", "coverage_fixture_001", "b")]}],
        "optional_profile_blockers": [],
        "blockers": [{"code": "MFB_RUNTIME_EVIDENCE_MISSING", "category": "policy", "message": "Planning fixtures do not establish runtime readiness.", "retryable": False, "blocks_scope": "required_release_path", "completion_profile": "core_autonomous_runtime", "core_impact": "blocking", "evidence_refs": [ref("planning_coverage", "coverage_fixture_001", "b")]}],
    }
    return {
        "maskfactory_release_snapshot_v2.example.json": release,
        "maskfactory_consumer_requirements_v2.example.json": consumer,
        "maskfactory_adoption_receipt_v2.example.json": adoption,
        "maskfactory_bridge_request_v2.example.json": request,
        "maskfactory_operational_certificate_v2.example.json": certificate,
        "maskfactory_promotion_gate_policy_v2.example.json": promotion_policy,
        "maskfactory_bridge_result_v2.example.json": result,
        "maskfactory_authority_decision_v2.example.json": authority,
        "maskfactory_health_capability_snapshot_v2.example.json": health,
        "maskfactory_invalidation_event_v2.example.json": invalidation,
        "maskfactory_bridge_event_v2.example.json": bridge_event,
        "maskfactory_feedback_repair_request_v2.example.json": feedback,
        "maskfactory_bridge_release_certificate_v2.example.json": integration,
        "maskfactory_bridge_readiness_projection_v2.example.json": readiness,
    }


def validate_rows(rows: list[dict[str, Any]]) -> None:
    if [row["row_number"] for row in rows] != list(range(321, 349)):
        raise ValueError("Rows321-348 must be contiguous")
    if len({row["item_id"] for row in rows}) != 28 or len({row["tracker_id"] for row in rows}) != 28:
        raise ValueError("row item/tracker IDs must be unique")
    workstream_counts = {wid: 0 for wid, _, _ in WORKSTREAMS}
    for row in rows:
        workstream_counts[row["workstream_id"]] += 1
        if row["status"] != STATUS or row["runtime_completion_claimed"]:
            raise ValueError(f"false runtime claim in {row['item_id']}")
        if row["completion_profile"] != "core_autonomous_runtime" or row["optional_profiles_not_blocking"] != ["independent_real_accuracy", "scale_daz_maturity"]:
            raise ValueError(f"completion-profile drift in {row['item_id']}")
    if set(workstream_counts.values()) != {4}:
        raise ValueError("every workstream must have exactly four rows")
    item_ids = {row["item_id"] for row in rows}
    dep_map = {row["item_id"]: [dep for dep in row["dependencies"] if dep in item_ids] for row in rows}
    seen: set[str] = set()
    stack = ["ITEM-W64-348"]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(dep_map[current])
    if seen != item_ids:
        raise ValueError(f"Row348 does not transitively reach {sorted(item_ids - seen)}")
    if "ITEM-W64-218" not in rows[-1]["dependencies"]:
        raise ValueError("Row348 must directly depend on Row218")
    reachable_external: set[str] = set(rows[-1]["dependencies"])
    walk = [dep for dep in rows[-1]["dependencies"] if dep in item_ids]
    by_id = {row["item_id"]: row for row in rows}
    while walk:
        current = walk.pop()
        for dep in by_id[current]["dependencies"]:
            if dep not in reachable_external:
                reachable_external.add(dep)
                if dep in item_ids:
                    walk.append(dep)
    if not set(PARENT_ITEMS).issubset(reachable_external):
        raise ValueError("Rows177-180 are not transitive parents")


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_source_artifact(source: dict[str, Any]) -> None:
    if source["artifact_ref"]["sha256"] != source["sha256"]:
        raise ValueError("source artifact immutable reference/hash mismatch")


def validate_media_scope(scope: dict[str, Any]) -> None:
    if scope["source_media_ref"]["sha256"] != scope["source_media_sha256"] or not scope["exact_frame_scope_only"]:
        raise ValueError("media scope source hash mismatch or widened authority")
    if scope["media_kind"] == "frame_span" and scope["span_start_frame"] >= scope["span_end_frame"]:
        raise ValueError("frame-span media scope is empty or reversed")
    if scope["media_kind"] in {"video_frame", "frame_span"} and not scope["temporal_evidence_refs"]:
        raise ValueError("video media scope lacks temporal evidence")


def validate_signature_trust_record(
    trust: dict[str, Any], trusted_keys: dict[str, Any] | None = None, *, production_required: bool = False,
    expected_signer_role: str | None = None, use_time: str | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
) -> None:
    if trust["embedded_public_key_is_trust_anchor"] or trust["trust_anchor_source"] != "main_out_of_band_trusted_key_registry":
        raise ValueError("embedded or producer-supplied key cannot establish signer authenticity")
    if trust.get("signer_role") not in SIGNER_ROLES:
        raise ValueError("signature trust record has an unknown signer role")
    if production_required:
        if trust["signature_algorithm"] != "ed25519" or not trust["signature_verified"] or not trust["trust_anchor_matched"] or trust["key_status"] != "active" or trust["trust_result"] != "trusted":
            raise ValueError("production signature lacks an active out-of-band Main trust anchor")
        if expected_signer_role is None or trust["signer_role"] != expected_signer_role:
            raise ValueError("production signature signer role does not match the authority domain")
        if trusted_keys is not None:
            entry = trusted_keys.get(trust["signing_key_id"])
            if not isinstance(entry, dict):
                raise ValueError("production signature key is absent from the pinned Main trust registry")
            if entry.get("entry_sha256") != trusted_key_entry_sha256(entry) or entry.get("signer_role") != expected_signer_role:
                raise ValueError("trusted key entry hash or signer-role binding is invalid")
            if entry.get("public_key_sha256") != trust["embedded_public_key_sha256"] or trust["trusted_key_entry_sha256"] != entry.get("entry_sha256"):
                raise ValueError("substituted self-signed key is not present in the pinned Main trust registry")
            if use_time is not None:
                use_at = parse_timestamp(use_time)
                if (
                    entry.get("status") != "active"
                    or not parse_timestamp(entry["valid_from"]) <= use_at < parse_timestamp(entry["valid_until"])
                    or not parse_timestamp(entry["revocation_checked_at"]) <= use_at < parse_timestamp(entry["revocation_valid_until"])
                ):
                    raise ValueError("trusted signing key is expired, revoked, future-valid, or stale at use time")
            if runtime_verification_context is not None:
                resolve_verified_artifact_bytes(entry["revocation_evidence_ref"], runtime_verification_context)
                resolve_verified_artifact_bytes(trust["verification_evidence_ref"], runtime_verification_context)


def validate_journal_pin_runtime(
    journal_pin: dict[str, Any], trusted_keys: dict[str, Any] | None, runtime_verification_context: dict[str, Any] | None,
    *, use_time: str,
) -> None:
    use_at = parse_timestamp(use_time)
    if not parse_timestamp(journal_pin["checkpointed_at"]) <= use_at < parse_timestamp(journal_pin["fresh_until"]):
        raise ValueError("journal checkpoint is future-dated or stale at the exact use time")
    checkpoint_bytes = resolve_verified_artifact_bytes(journal_pin["checkpoint_ref"], runtime_verification_context)
    if journal_pin["checkpoint_payload_sha256"] != journal_pin["checkpoint_ref"]["sha256"] or sha256_bytes(checkpoint_bytes) != journal_pin["checkpoint_payload_sha256"]:
        raise ValueError("journal checkpoint payload/ref hash mismatch")
    checkpoint_payload = strict_json_loads(checkpoint_bytes)
    expected_payload = strict_json_loads(journal_checkpoint_payload(journal_pin))
    if checkpoint_payload != expected_payload or set(checkpoint_payload) != {
        "stream_id", "checkpoint_sequence", "head_event_sha256", "previous_checkpoint_sha256",
        "checkpointed_at", "fresh_until",
    }:
        raise ValueError("journal checkpoint bytes do not exactly bind the stream, sequence, chain heads, and freshness window")
    validate_signature_trust_record(
        journal_pin["checkpoint_signature_trust"], trusted_keys, production_required=True,
        expected_signer_role="main_journal_checkpoint_signer", use_time=use_time,
        runtime_verification_context=runtime_verification_context,
    )
    verify_ed25519_runtime_signature(
        journal_pin["checkpoint_payload_sha256"], journal_pin["checkpoint_signature"], journal_pin["checkpoint_signature_domain"],
        journal_pin["checkpoint_signature_trust"], trusted_keys, runtime_verification_context,
        expected_signer_role="main_journal_checkpoint_signer", use_time=use_time,
    )


def validate_release_snapshot_record(
    release: dict[str, Any], trusted_keys: dict[str, Any] | None = None, *, production_required: bool = False,
    runtime_verification_context: dict[str, Any] | None = None, use_time: str | None = None,
) -> None:
    if not release["producer_source"]["source_clean"] or release["mutable_worktree_consumption_allowed"]:
        raise ValueError("release snapshot is not clean immutable producer source")
    if release["normalization_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust" or release["normalization_payload_sha256"] != normalized_release_sha256(release):
        raise ValueError("normalized release canonical seal mismatch")
    if release["fixture_only"]:
        if release["release_context"] != "fixture_validation" or release["genuine_runtime_evidence_refs"] or release["runtime_completion_claimed"]:
            raise ValueError("fixture release snapshot cannot establish production release authority")
    if release["release_context"] == "production_runtime":
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        if release["fixture_only"] or release["release_status"] != "published" or not release["genuine_runtime_evidence_refs"]:
            raise ValueError("production release snapshot requires non-fixture genuine runtime evidence")
        if use_time is None or parse_timestamp(release["published_at"]) > parse_timestamp(use_time):
            raise ValueError("production release is not published and active at the explicit use time")
        raw_release_bytes = resolve_verified_artifact_bytes(release["raw_producer_release_ref"], runtime_verification_context)
        raw_release = strict_json_loads(raw_release_bytes)
        if not isinstance(raw_release, dict):
            raise ValueError("raw producer release is not a JSON object")
        if (
            release["raw_producer_release_ref"]["record_type"] != raw_release.get("record_type")
            or release["raw_producer_release_ref"]["record_id"] != raw_release.get("release_id")
        ):
            raise ValueError("raw producer release immutable-ref identity differs from the signed document")
        validate_frozen_producer_document(raw_release, "maskfactory_release_snapshot", runtime_verification_context)
        recomputed_release_sha256 = maskfactory_document_sha256(raw_release, excluded=("release_payload_sha256", "signature"))
        raw_signature = raw_release.get("signature")
        raw_trust = raw_release.get("signing_trust")
        raw_signature_public_sha256 = None
        if isinstance(raw_signature, dict) and isinstance(raw_signature.get("public_key_base64"), str):
            try:
                raw_signature_public_sha256 = sha256_bytes(base64.b64decode(raw_signature["public_key_base64"], validate=True))
            except (ValueError, binascii.Error):
                raw_signature_public_sha256 = None
        if (
            raw_release.get("release_payload_sha256") != recomputed_release_sha256
            or recomputed_release_sha256 != release["snapshot_sha256"]
            or not isinstance(raw_signature, dict)
            or raw_signature.get("signed_payload_sha256") != recomputed_release_sha256
            or raw_signature.get("signed_payload_format") != "sha256_digest_bytes"
            or raw_signature.get("value_base64") != release["release_signature"]
            or not isinstance(raw_trust, dict)
            or raw_signature.get("key_id") != raw_trust.get("release_signing_key_id")
            or raw_trust.get("release_signing_key_id") != release["signature_trust"]["signing_key_id"]
            or raw_signature_public_sha256 != raw_trust.get("release_signing_public_key_sha256")
            or raw_signature_public_sha256 != release["signature_trust"]["embedded_public_key_sha256"]
        ):
            raise ValueError("normalized release does not bind the exact signed raw producer release")
        validate_raw_release_projection(raw_release, release, runtime_verification_context)
        validate_signature_trust_record(
            release["signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="maskfactory_release_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_runtime_evidence_refs(release["genuine_runtime_evidence_refs"], runtime_verification_context)
        verify_ed25519_runtime_signature(
            release["snapshot_sha256"], release["release_signature"], release["release_signature_domain"],
            release["signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="maskfactory_release_signer", use_time=use_time,
            signature_message_format="digest_bytes",
        )
        if resolve_verified_artifact_bytes(immutable_release_ref(release), runtime_verification_context) != normalized_release_payload_bytes(release):
            raise ValueError("resolved normalized release bytes differ from the sealed Main release")
        validate_signature_trust_record(
            release["normalization_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_normalization_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            release["normalization_payload_sha256"], release["normalization_signature"], release["normalization_signature_domain"],
            release["normalization_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_normalization_signer", use_time=use_time,
        )
    if production_required and release["release_context"] != "production_runtime":
        raise ValueError("fixture release snapshot cannot satisfy production adoption")


def validate_revalidation_policy(
    adoption: dict[str, Any], producer_policy: dict[str, Any] | None = None, *, production_required: bool = False,
    runtime_verification_context: dict[str, Any] | None = None,
) -> None:
    producer_policy = producer_policy or producer_invalidation_policy_document()
    if producer_policy != producer_invalidation_policy_document() or producer_invalidation_policy_sha256(producer_policy) != "0dc09f41f46f9f364fb72ee092a9c808887d5bf95d2827d7990329b81cb1a0b3":
        raise ValueError("producer invalidation reason/target/action policy differs from the exact frozen producer policy")
    expected_policy_sha256 = producer_invalidation_policy_sha256(producer_policy)
    if adoption["producer_invalidation_policy_sha256"] != expected_policy_sha256 or adoption["producer_invalidation_policy_ref"] != producer_invalidation_policy_ref(producer_policy):
        raise ValueError("adoption invalidation policy binding does not match the exact producer policy")
    if production_required:
        if runtime_verification_context is None or runtime_verification_context.get("producer_invalidation_policy_adopted_from_signed_release") is not True:
            raise ValueError("production adoption requires the frozen policy to be pinned by the signed adopted runtime release")
        if resolve_verified_artifact_bytes(adoption["producer_invalidation_policy_ref"], runtime_verification_context) != producer_invalidation_policy_bytes(producer_policy):
            raise ValueError("resolved producer invalidation policy bytes differ from the adopted policy")
    triggers = adoption["revalidation_triggers"]
    rules = adoption["revalidation_rules"]
    if len(triggers) != len(set(triggers)) or set(triggers) != set(PRODUCER_INVALIDATION_REASONS):
        raise ValueError("adoption revalidation trigger coverage is incomplete or duplicated")
    if len(rules) != len(PRODUCER_INVALIDATION_REASONS) or len({rule["producer_reason_code"] for rule in rules}) != len(rules):
        raise ValueError("adoption revalidation rules are incomplete or duplicated")
    expected = {rule["producer_reason_code"]: rule for rule in build_revalidation_rules()}
    observed = {rule["producer_reason_code"]: rule for rule in rules}
    if observed != expected:
        raise ValueError("adoption revalidation trigger/action/scope policy drift")


def validate_adoption_against_signed_producer_checkpoint(
    adoption: dict[str, Any], release: dict[str, Any], runtime_verification_context: dict[str, Any] | None, use_time: str,
) -> None:
    raw_release_bytes = resolve_verified_artifact_bytes(release["raw_producer_release_ref"], runtime_verification_context)
    raw_release = strict_json_loads(raw_release_bytes)
    if not isinstance(raw_release, dict):
        raise ValueError("signed producer release checkpoint source is not a JSON object")
    checkpoint = raw_release["journal_checkpoint"]
    binding = adoption["producer_journal_checkpoint_binding"]
    expected_binding = {
        "source_release_ref": release["raw_producer_release_ref"],
        "release_payload_sha256": raw_release["release_payload_sha256"],
        **checkpoint,
        "producer_and_main_journal_domains_are_separate": True,
    }
    _assert_equal_projection("adoption producer journal checkpoint binding", expected_binding, binding)
    _assert_equal_projection(
        "adoption producer/Main journal domain separation",
        True,
        binding["producer_and_main_journal_domains_are_separate"] and binding["stream_id"] != adoption["journal_pin"]["stream_id"],
    )
    use_at = parse_timestamp(use_time)
    if not parse_timestamp(checkpoint["checkpointed_at"]) <= use_at < parse_timestamp(checkpoint["fresh_until"]):
        raise ValueError("signed producer release journal/revocation checkpoint is stale or future-dated at adoption use time")
    if runtime_verification_context is None or not isinstance(runtime_verification_context.get("producer_revocation_state_ref"), dict):
        raise ValueError("producer revocation-state evidence is absent from the signed release adoption")
    revocation_ref = runtime_verification_context["producer_revocation_state_ref"]
    if revocation_ref["sha256"] != checkpoint["revocation_state_sha256"]:
        raise ValueError("producer revocation-state evidence differs from the signed release checkpoint")
    resolve_verified_artifact_bytes(revocation_ref, runtime_verification_context)
    if runtime_verification_context.get("producer_active_revocation_count") != checkpoint["active_revocation_count"]:
        raise ValueError("producer active revocation count differs from the signed release checkpoint")


def validate_adoption_trust(
    adoption: dict[str, Any], consumer: dict[str, Any], release: dict[str, Any], trusted_keys: dict[str, Any],
    runtime_verification_context: dict[str, Any] | None = None, *, use_time: str | None = None,
) -> None:
    production = adoption["production_consumption_allowed"]
    producer_policy = None if runtime_verification_context is None else runtime_verification_context.get("producer_invalidation_policy")
    validate_revalidation_policy(
        adoption, producer_policy, production_required=production, runtime_verification_context=runtime_verification_context,
    )
    if adoption["trusted_signing_key_registry_ref"] != consumer["trusted_signing_key_registry_ref"]:
        raise ValueError("adoption trust registry does not match consumer requirements")
    if adoption["release_snapshot_ref"] != immutable_release_ref(release):
        raise ValueError("adoption release reference identity or hash does not match the exact normalized release")
    if adoption["release_signature_trust"] != release["signature_trust"]:
        raise ValueError("adoption release signer evidence does not match normalized release")
    if adoption["adoption_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_receipt_hash_signature_and_signature_trust" or adoption["adoption_receipt_sha256"] != adoption_receipt_sha256(adoption):
        raise ValueError("adoption receipt canonical hash mismatch")
    validate_release_snapshot_record(release, trusted_keys, production_required=production, runtime_verification_context=runtime_verification_context, use_time=use_time)
    validate_signature_trust_record(
        adoption["journal_pin"]["checkpoint_signature_trust"], trusted_keys, production_required=production,
        expected_signer_role="main_journal_checkpoint_signer" if production else None,
    )
    validate_signature_trust_record(
        adoption["adoption_signature_trust"], trusted_keys, production_required=production,
        expected_signer_role="main_adoption_signer" if production else None,
    )
    derived_all_trusted = all(
        trust["trust_result"] == "trusted"
        for trust in (
            release["signature_trust"], release["normalization_signature_trust"],
            adoption["adoption_signature_trust"], adoption["journal_pin"]["checkpoint_signature_trust"],
        )
    )
    if adoption["all_required_signatures_trusted"] != derived_all_trusted:
        raise ValueError("adoption signature-trust aggregate is self-declared or inconsistent")
    if production:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        use_at = parse_timestamp(use_time)
        validate_adoption_against_signed_producer_checkpoint(adoption, release, runtime_verification_context, use_time)
        validate_signature_trust_record(
            adoption["adoption_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_adoption_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        decided_at = parse_timestamp(adoption["decided_at"])
        valid_until = parse_timestamp(adoption["valid_until"])
        published_at = parse_timestamp(release["published_at"])
        if not adoption["use_time_recheck_required"] or not published_at <= decided_at <= use_at < valid_until:
            raise ValueError("production adoption is future-decided, expired, or not rechecked at use time")
        capability_observed_at = parse_timestamp(adoption["capability_observed_at"])
        capability_valid_until = parse_timestamp(adoption["capability_valid_until"])
        capability_revocation_checked_at = parse_timestamp(adoption["capability_revocation_checked_at"])
        capability_revocation_valid_until = parse_timestamp(adoption["capability_revocation_valid_until"])
        if adoption["capability_snapshot_status"] != "current" or not capability_observed_at <= use_at < capability_valid_until or not capability_revocation_checked_at <= use_at < capability_revocation_valid_until:
            raise ValueError("capability snapshot is inactive, expired, or has stale revocation status at use time")
        resolve_verified_artifact_bytes(adoption["capability_snapshot_ref"], runtime_verification_context)
        resolve_verified_artifact_bytes(adoption["capability_status_evidence_ref"], runtime_verification_context)
        for evaluation in adoption["operational_certificate_evaluations"]:
            if evaluation["status"] != "active" or not parse_timestamp(evaluation["issued_at"]) <= use_at < parse_timestamp(evaluation["expires_at"]) or not parse_timestamp(evaluation["revocation_checked_at"]) <= use_at < parse_timestamp(evaluation["revocation_valid_until"]):
                raise ValueError("operational certificate is inactive, expired, future-issued, or stale at use time")
            resolve_verified_artifact_bytes(evaluation["certificate_ref"], runtime_verification_context)
            resolve_verified_artifact_bytes(evaluation["status_evidence_ref"], runtime_verification_context)
        if adoption["fixture_only"] or release["fixture_only"] or adoption["adoption_context"] != "production_runtime" or release["release_context"] != "production_runtime":
            raise ValueError("production adoption cannot consume a fixture release or fixture adoption")
        if not adoption["genuine_runtime_evidence_refs"] or not release["genuine_runtime_evidence_refs"]:
            raise ValueError("production adoption requires genuine runtime evidence for both release and adoption")
        if adoption["decision"] != "adopted" or adoption["mismatch_codes"] or not adoption["active_pin_written"] or any(check["status"] != "pass" for check in adoption["checks"]):
            raise ValueError("production adoption requires an exact passing adopted decision and active pin")
        if {check["check"] for check in adoption["checks"]} != set(REQUIRED_ADOPTION_CHECK_IDS) or len(adoption["checks"]) != len(REQUIRED_ADOPTION_CHECK_IDS):
            raise ValueError("production adoption qualification check set is incomplete, duplicated, or invented")
        qualification_bytes = canonical_json({"checks": adoption["checks"]})
        if adoption["qualification_bundle_sha256"] != sha256_bytes(qualification_bytes) or adoption["qualification_bundle_ref"]["sha256"] != adoption["qualification_bundle_sha256"]:
            raise ValueError("production adoption qualification bundle hash mismatch")
        if resolve_verified_artifact_bytes(adoption["qualification_bundle_ref"], runtime_verification_context) != qualification_bytes:
            raise ValueError("production adoption qualification bundle bytes differ from the closed check set")
        for check in adoption["checks"]:
            resolve_verified_artifact_bytes(check["evidence_ref"], runtime_verification_context)
        verify_runtime_evidence_refs(adoption["genuine_runtime_evidence_refs"], runtime_verification_context)
        verify_ed25519_runtime_signature(
            adoption["adoption_receipt_sha256"], adoption["adoption_signature"], adoption["adoption_signature_domain"],
            adoption["adoption_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_adoption_signer", use_time=use_time,
        )
        validate_journal_pin_runtime(adoption["journal_pin"], trusted_keys, runtime_verification_context, use_time=use_time)
        signing_key_id = release["signature_trust"]["signing_key_id"]
        if signing_key_id not in consumer["required_signing_key_ids"] or not adoption["all_required_signatures_trusted"]:
            raise ValueError("production adoption signer is outside the consumer trust policy")
    elif adoption["active_pin_written"]:
        raise ValueError("active producer pin cannot be written by a non-production adoption")


def validate_transform_chain(chain: dict[str, Any], *, maximum_error_pixels: float | None = None) -> None:
    if chain["canonical_hash_profile"] != "main_sorted_utf8_json_v2_excluding_self_hash":
        raise ValueError("transform chain uses an unknown canonical hash profile")
    steps = chain["steps"]
    previous = chain["source"]
    for expected_sequence, step in enumerate(steps):
        if step["sequence"] != expected_sequence or step["input"] != previous:
            raise ValueError("transform chain sequence or coordinate continuity mismatch")
        if step["operation"] != step["parameters"]["parameter_type"]:
            raise ValueError("transform operation does not match its typed parameters")
        if step["operation"] == "horizontal_flip" and not step["parameters"]["character_side_swap"]:
            raise ValueError("horizontal flip must explicitly swap character-perspective side labels")
        if step["inverse_strategy"] == "none" and chain["roundtrip_policy"]["reject_noninvertible"]:
            raise ValueError("noninvertible transform is forbidden by the roundtrip policy")
        step_payload = {key: value for key, value in step.items() if key != "step_sha256"}
        if step["step_sha256"] != sha256_bytes(canonical_json(step_payload)):
            raise ValueError("transform step canonical hash mismatch")
        previous = step["output"]
    if previous != chain["output"]:
        raise ValueError("transform chain output does not match the last executable step")
    if not chain["roundtrip_policy"]["required"] or not chain["roundtrip_policy"]["reject_noninvertible"]:
        raise ValueError("transform chain does not require fail-closed inverse roundtrip validation")
    if maximum_error_pixels is not None and chain["roundtrip_policy"]["maximum_error_pixels"] > maximum_error_pixels:
        raise ValueError("transform chain roundtrip tolerance exceeds the request policy")
    if not chain["roundtrip_evidence_refs"]:
        raise ValueError("transform chain lacks immutable roundtrip evidence")
    chain_payload = {key: value for key, value in chain.items() if key != "chain_sha256"}
    if chain["chain_sha256"] != sha256_bytes(canonical_json(chain_payload)):
        raise ValueError("transform chain canonical hash mismatch")


def validate_request_ownership(request: dict[str, Any]) -> None:
    validate_source_artifact(request["source_artifact"])
    validate_media_scope(request["media_scope"])
    if request["media_scope"]["media_kind"] == "still_image" and request["media_scope"]["source_media_sha256"] != request["source_artifact"]["sha256"]:
        raise ValueError("still-image media scope is not bound to the exact source artifact")
    roster = request["scene_owner_roster"]
    target_bindings = [owner for owner in request["owner_bindings"] if owner["owner_role"] == "target"]
    if len(target_bindings) != 1 or target_bindings[0]["character_instance_id"] != roster["target_character_instance_id"]:
        raise ValueError("request must bind exactly one target subject matching the scene roster")
    if roster["target_character_instance_id"] not in roster["character_instance_ids"]:
        raise ValueError("target subject is absent from the declared scene roster")
    region_ids: set[str] = set()
    for expected_role, regions in (("target", request["target_region_bindings"]), ("protected", request["protected_region_bindings"])):
        for region in regions:
            if region["region_id"] in region_ids:
                raise ValueError("ambiguous duplicate input region identity")
            region_ids.add(region["region_id"])
            if region["region_role"] != expected_role:
                raise ValueError("input region appears in the wrong target/protected collection")
            owner_id = region["owner_entity_id"]
            relationship = region["relationship_to_target"]
            if region["owner_entity_type"] == "character_instance" and owner_id not in roster["character_instance_ids"]:
                raise ValueError("character region owner is absent from the scene roster")
            if region["owner_entity_type"] == "prop" and owner_id not in roster["prop_instance_ids"]:
                raise ValueError("prop region owner is absent from the scene roster")
            if region["owner_entity_type"] == "environment" and owner_id != roster["environment_instance_id"]:
                raise ValueError("environment region owner is absent from the scene roster")
            if relationship == "self" and owner_id != roster["target_character_instance_id"]:
                raise ValueError("self region owner does not match the exact target subject")
            if relationship == "other_character" and owner_id == roster["target_character_instance_id"]:
                raise ValueError("other-character protected owner ambiguously aliases the target")
            if expected_role == "target" and relationship != "self":
                raise ValueError("target regions must be owned by the exact target subject")
            if region["region_ref"]["sha256"] != region["region_sha256"] or region["source_artifact_sha256"] != request["source_artifact"]["sha256"]:
                raise ValueError("input region hash or source-artifact lineage mismatch")
            if region["transform_chain_sha256"] != request["transform_chain"]["chain_sha256"]:
                raise ValueError("input region is bound to a different transform chain")
            sequence = region["transform_step_sequence"]
            if sequence is not None:
                if sequence >= len(request["transform_chain"]["steps"]):
                    raise ValueError("input region transform-step sequence is outside the executable chain")
                coordinate = request["transform_chain"]["steps"][sequence]["input"]
                if (region["coordinate_space"], region["width"], region["height"]) != (coordinate["coordinate_space"], coordinate["width"], coordinate["height"]):
                    raise ValueError("input region coordinate dimensions do not match its transform step")
    validate_transform_chain(request["transform_chain"], maximum_error_pixels=request["roundtrip_tolerance_pixels"])


def validate_request_result_pair(request: dict[str, Any], result: dict[str, Any]) -> None:
    validate_request_ownership(request)
    validate_source_artifact(result["source_artifact"])
    validate_media_scope(result["media_scope"])
    validate_transform_chain(result["transform_chain"], maximum_error_pixels=request["roundtrip_tolerance_pixels"])
    if result["transform_chain"]["chain_sha256"] != request["transform_chain"]["chain_sha256"] or result["input_region_lineage"]["request_transform_chain_sha256"] != request["transform_chain"]["chain_sha256"]:
        raise ValueError("receipt/result transform chain is not exactly bound to the request")
    if result["media_scope"] != request["media_scope"] or not result["media_scope"]["exact_frame_scope_only"]:
        raise ValueError("result changed the exact still/frame/span media scope")
    if result["roundtrip_max_error_pixels"] > request["roundtrip_tolerance_pixels"]:
        raise ValueError("result transform roundtrip exceeds the request tolerance")
    if result["status"] == "succeeded":
        requested_labels = sorted(intent["label"] for intent in request["mask_intents"])
        output_labels = sorted(mask["label"] for mask in result["masks"])
        if output_labels != requested_labels or result["blockers"]:
            raise ValueError("succeeded result does not provide exactly one output for every mask intent")
    elif result["masks"] or result["operational_certificate_ref"] is not None:
        raise ValueError("blocked/error result cannot carry authoritative outputs or a certificate")
    target_refs = {tuple(region["region_ref"][key] for key in ("record_type", "record_id", "revision", "sha256")) for region in request["target_region_bindings"]}
    protected_refs = {tuple(region["region_ref"][key] for key in ("record_type", "record_id", "revision", "sha256")) for region in request["protected_region_bindings"]}
    result_target_refs = {tuple(value[key] for key in ("record_type", "record_id", "revision", "sha256")) for value in result["input_region_lineage"]["target_region_refs"]}
    result_protected_refs = {tuple(value[key] for key in ("record_type", "record_id", "revision", "sha256")) for value in result["input_region_lineage"]["protected_region_refs"]}
    if target_refs != result_target_refs or protected_refs != result_protected_refs:
        raise ValueError("result input ROI lineage does not exactly preserve request target/protected regions")
    input_regions = [*request["target_region_bindings"], *request["protected_region_bindings"]]
    output_hashes = {mask["mask_sha256"] for mask in result["masks"]}
    collisions = [region for region in input_regions if region["region_sha256"] in output_hashes]
    allowed_collisions = request["access_mode"] == "mode_a_package_read" and all(region["selector_kind"] == "mode_a_exact_package_artifact" for region in collisions)
    if collisions and not allowed_collisions:
        raise ValueError("input target/protected ROI hashes cannot be conflated with newly generated output artifacts")
    if result["input_region_lineage"]["input_roi_hashes_are_output_artifact_hashes"] != bool(collisions) or result["input_region_lineage"]["mode_a_exact_selector_exception_applied"] != bool(collisions and allowed_collisions):
        raise ValueError("result input/output identity declaration disagrees with exact artifact hashes")
    observation = result["execution_observation"]
    if observation["execution_scope"] != request["scope"] or observation["attempt_number"] != request["attempt_number"] or observation["hypothesis"] != request["hypothesis"]:
        raise ValueError("execution observation lost project/run/job/pass/attempt/hypothesis identity")
    if observation["selected_route_id"] != result["route_id"]:
        raise ValueError("execution observation selected route does not match result route")
    envelope = request["resource_envelope"]
    measured_within_envelope = observation["queue_ms"] <= envelope["maximum_queue_ms"] and observation["runtime_ms"] <= envelope["maximum_runtime_ms"] and observation["peak_vram_mb"] <= envelope["maximum_vram_mb"] and observation["peak_ram_mb"] <= envelope["maximum_ram_mb"] and observation["output_bytes"] <= envelope["maximum_output_bytes"]
    deadline_met = parse_timestamp(observation["completed_at"]) <= parse_timestamp(request["deadline_at"])
    if observation["resource_envelope_met"] != measured_within_envelope or observation["deadline_met"] != deadline_met or not measured_within_envelope or not deadline_met:
        raise ValueError("execution exceeded the admitted deadline or resource envelope")


def validate_invalidation_event_record(
    event: dict[str, Any], trusted_keys: dict[str, str] | None = None, *, production_required: bool = False,
    producer_policy: dict[str, Any] | None = None, runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> None:
    if event["invalidation_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_invalidation_hash_normalization_signature_and_trust_records":
        raise ValueError("invalidation event canonical hash profile mismatch")
    if event["invalidation_event_sha256"] != invalidation_event_sha256(event):
        raise ValueError("invalidation event canonical hash mismatch")
    if not event["producer_payload_preserved_losslessly"] or event["producer_payload_sha256"] != event["tombstone_sha256"]:
        raise ValueError("producer invalidation payload is not preserved by exact immutable hash")
    if (
        event["producer_payload_ref"]["record_type"] != "mask_authority_invalidation_event"
        or event["producer_payload_ref"]["sha256"] != event["producer_payload_sha256"]
    ):
        raise ValueError("producer invalidation immutable ref differs from the preserved producer payload")
    producer_policy = producer_policy or producer_invalidation_policy_document()
    expected_policy_sha256 = producer_invalidation_policy_sha256(producer_policy)
    if event["producer_invalidation_policy_sha256"] != expected_policy_sha256 or event["producer_invalidation_policy_ref"] != producer_invalidation_policy_ref(producer_policy):
        raise ValueError("invalidation event is not bound to the exact producer reason policy")
    if production_required:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        if runtime_verification_context is None or runtime_verification_context.get("producer_invalidation_policy_adopted_from_signed_release") is not True:
            raise ValueError("production invalidation requires a signed-release-adopted frozen producer policy")
        raw_event_bytes = resolve_verified_artifact_bytes(event["producer_payload_ref"], runtime_verification_context)
        raw_event = strict_json_loads(raw_event_bytes)
        if not isinstance(raw_event, dict):
            raise ValueError("raw producer invalidation is not a JSON object")
        if (
            event["producer_payload_ref"]["record_type"] != raw_event.get("record_type")
            or event["producer_payload_ref"]["record_id"] != raw_event.get("event_id")
        ):
            raise ValueError("raw producer invalidation immutable-ref identity differs from the signed document")
        validate_frozen_producer_document(raw_event, "mask_authority_invalidation_event", runtime_verification_context)
        recomputed_payload_sha256 = maskfactory_document_sha256(raw_event, excluded=("event_payload_sha256", "signature"))
        raw_signature = raw_event.get("signature")
        raw_trust = raw_event.get("trust_binding")
        raw_signature_public_sha256 = None
        if isinstance(raw_signature, dict) and isinstance(raw_signature.get("public_key_base64"), str):
            try:
                raw_signature_public_sha256 = sha256_bytes(base64.b64decode(raw_signature["public_key_base64"], validate=True))
            except (ValueError, binascii.Error):
                raw_signature_public_sha256 = None
        if (
            raw_event.get("event_payload_sha256") != recomputed_payload_sha256
            or recomputed_payload_sha256 != event["producer_payload_sha256"]
            or not isinstance(raw_signature, dict)
            or raw_signature.get("signed_payload_sha256") != recomputed_payload_sha256
            or raw_signature.get("signed_payload_format") != "sha256_digest_bytes"
            or raw_signature.get("value_base64") != event["producer_signature"]
            or not isinstance(raw_trust, dict)
            or raw_trust.get("key_role") != "producer_journal"
            or raw_trust.get("signing_key_id") != event["producer_signature_trust"]["signing_key_id"]
            or raw_signature.get("key_id") != raw_trust.get("signing_key_id")
            or raw_signature_public_sha256 != raw_trust.get("signing_public_key_sha256")
            or raw_signature_public_sha256 != event["producer_signature_trust"]["embedded_public_key_sha256"]
        ):
            raise ValueError("normalized invalidation does not bind the exact signed raw producer event")
        validate_raw_invalidation_projection(raw_event, event)
        validate_signature_trust_record(
            event["producer_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="maskfactory_invalidation_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            event["producer_payload_sha256"], event["producer_signature"], event["producer_signature_domain"],
            event["producer_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="maskfactory_invalidation_signer", use_time=use_time,
            signature_message_format="digest_bytes",
        )
        validate_signature_trust_record(
            event["signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_normalization_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            event["invalidation_event_sha256"], event["normalization_signature"], event["normalization_signature_domain"],
            event["signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_normalization_signer", use_time=use_time,
        )
        if resolve_verified_artifact_bytes(event["producer_invalidation_policy_ref"], runtime_verification_context) != producer_invalidation_policy_bytes(producer_policy):
            raise ValueError("production invalidation payload or reason policy bytes are not independently resolved")
    transitions = event["target_transitions"]
    target_keys = [(transition["target_kind"], transition["target_id"], transition["target_sha256"]) for transition in transitions]
    if len(target_keys) != len(set(target_keys)):
        raise ValueError("invalidation event contains duplicate target transitions")
    if {immutable_ref_key(transition["main_target_ref"]) for transition in transitions} != {immutable_ref_key(value) for value in event["affected_refs"]}:
        raise ValueError("invalidation affected refs do not equal the exact per-target transition set")
    transition_ids = {transition["transition_id"] for transition in transitions}
    if len(transition_ids) != len(transitions):
        raise ValueError("invalidation transition IDs are duplicated")
    covered_transition_ids: set[str] = set()
    action_ids: set[str] = set()
    observed_actions: set[str] = set()
    for action in event["required_actions"]:
        if action["action_id"] in action_ids or not set(action["transition_ids"]).issubset(transition_ids):
            raise ValueError("invalidation required action identity or transition reference is invalid")
        action_ids.add(action["action_id"])
        covered_transition_ids.update(action["transition_ids"])
        observed_actions.add(action["action"])
        if parse_timestamp(action["deadline_at"]) < parse_timestamp(event["effective_at"]):
            raise ValueError("invalidation required action deadline precedes effective time")
    if covered_transition_ids != transition_ids:
        raise ValueError("every invalidated target must have an explicit producer-required action")
    policy = PRODUCER_INVALIDATION_REASON_POLICY[event["reason"]]
    if not set(policy["required_actions"]).issubset(observed_actions):
        raise ValueError("invalidation required actions do not cover the exact producer reason policy")
    if event["main_enforcement_actions"] != main_enforcement_actions_for_reason(event["reason"]):
        raise ValueError("Main enforcement actions are not the exact additive projection for the producer reason")
    ranks = {state: index for index, state in enumerate(AUTHORITY_STATES)}
    for transition in transitions:
        if transition["target_kind"] not in policy["target_kinds"]:
            raise ValueError("per-target invalidation kind is not permitted by the exact producer reason policy")
        if transition["main_target_ref"]["record_id"] != transition["target_id"] or transition["main_target_ref"]["sha256"] != transition["target_sha256"]:
            raise ValueError("Main target projection diverges from the exact producer target identity")
        if not transition["unrelated_scope_preserved"]:
            raise ValueError("invalidation may not mutate unrelated scopes")
        if ranks[transition["new_authority_state"]] >= ranks[transition["previous_authority_state"]]:
            raise ValueError("invalidation must strictly lower authority for every exact target")
        if transition["target_kind"] == "certificate" and transition["previous_certificate_status"] == "active" and transition["new_certificate_status"] == "none":
            raise ValueError("certificate invalidation must retain an explicit terminal certificate state")
    if event["reason"] == "release_superseded" and event["superseding_binding"] is None:
        raise ValueError("release supersession requires the exact producer superseding binding")
    if event["reason"] != "release_superseded" and event["superseding_binding"] is not None:
        raise ValueError("producer superseding binding is only valid for release supersession")
    if event["supersedes_invalidation_ref"] is not None and (event["sequence"] < 2 or event["causation_id"] is None):
        raise ValueError("invalidation supersession lacks sequence and causation identity")
    if not production_required:
        validate_signature_trust_record(event["signature_trust"], trusted_keys)


def validate_invalidation_stream(
    events: list[dict[str, Any]], trusted_keys: dict[str, Any] | None = None, *,
    production_required: bool = False, producer_policy: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None, use_time: str | None = None,
) -> None:
    if not events:
        raise ValueError("invalidation stream cannot be empty")
    stream_id = events[0]["stream_id"]
    seen_event_ids: set[str] = set()
    idempotency_payloads: dict[str, str] = {}
    previous_ref: dict[str, str] | None = None
    for expected_sequence, event in enumerate(events, start=1):
        validate_invalidation_event_record(
            event, trusted_keys, production_required=production_required,
            producer_policy=producer_policy, runtime_verification_context=runtime_verification_context,
            use_time=use_time,
        )
        if event["stream_id"] != stream_id or event["sequence"] != expected_sequence or event["event_id"] in seen_event_ids:
            raise ValueError("invalidation stream identity, sequence, or event uniqueness mismatch")
        prior_payload = idempotency_payloads.setdefault(event["idempotency_key"], event["producer_payload_ref"]["sha256"])
        if prior_payload != event["producer_payload_ref"]["sha256"]:
            raise ValueError("invalidation idempotency key was reused for a different producer payload")
        if event["supersedes_invalidation_ref"] is not None and event["supersedes_invalidation_ref"] != previous_ref:
            raise ValueError("invalidation supersession does not identify the immediately prior immutable event")
        seen_event_ids.add(event["event_id"])
        previous_ref = {
            "record_type": event["record_type"], "record_id": event["maskfactory_invalidation_event_v2_id"],
            "revision": event["revision"], "sha256": event["invalidation_event_sha256"],
        }


def validate_event_journal(
    events: list[dict[str, Any]], journal_pin: dict[str, Any], trusted_keys: dict[str, Any], *,
    production_required: bool = False, runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> None:
    if not events:
        raise ValueError("event journal checkpoint cannot authorize an empty or deleted chain")
    stream_id = events[0]["stream_id"]
    previous_hash = None
    lifecycle_state = "compiled"
    request_payload_sha256 = None
    idempotency_key = None
    safe_resubmission_authorization_ref = None
    exact_transitions = {
        "request_admitted": {("compiled", "admitted")}, "submission_started": {("admitted", "submitted")},
        "submission_resubmitted_after_signed_not_found": {("reconciled_not_found", "submitted")},
        "submission_accepted": {("submitted", "accepted")}, "execution_running": {("accepted", "running")},
        "submission_outcome_unknown": {(state, "outcome_unknown") for state in ["submitted", "accepted", "running"]},
        "submission_reconciled_found_running": {("outcome_unknown", "running")},
        "submission_reconciled_found_completed_pending_receipt": {("outcome_unknown", "completed_pending_receipt")},
        "submission_reconciled_found_failed": {("outcome_unknown", "failed")},
        "submission_reconciled_not_found_safe_to_submit": {("outcome_unknown", "reconciled_not_found")},
        "receipt_committed": {("completed_pending_receipt", "succeeded")},
        "execution_succeeded": {(state, "succeeded") for state in ["submitted", "accepted", "running"]},
        "execution_failed": {(state, "failed") for state in ["submitted", "accepted", "running"]},
        "execution_cancelled": {(state, "cancelled") for state in ["submitted", "accepted", "running"]},
    }
    if production_required:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
    for expected_sequence, event in enumerate(events, start=1):
        if event["stream_id"] != stream_id or event["sequence"] != expected_sequence or event["previous_event_sha256"] != previous_hash:
            raise ValueError("event journal fork, deletion, or reorder detected")
        if event["event_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_event_hash_signature_trust_and_pin" or event["signature_domain"] != "comfy_ui_main.maskfactory_bridge_event.v2":
            raise ValueError("event journal canonical hash or signature domain mismatch")
        if event["event_sha256"] != bridge_event_sha256(event):
            raise ValueError("event journal canonical payload hash mismatch or reseal detected")
        transition = event["lifecycle_transition"]
        if event["event_type"] in exact_transitions:
            if transition is None or (transition["from_state"], transition["to_state"]) not in exact_transitions[event["event_type"]]:
                raise ValueError("event type and execution lifecycle transition disagree")
            if transition["from_state"] != lifecycle_state or [transition["from_state"], transition["to_state"]] not in ALLOWED_EXECUTION_TRANSITIONS:
                raise ValueError("execution lifecycle transition is discontinuous, backward, or unregistered")
            if request_payload_sha256 is None:
                request_payload_sha256 = transition["request_payload_sha256"]
                idempotency_key = event["idempotency_key"]
            elif transition["request_payload_sha256"] != request_payload_sha256 or event["idempotency_key"] != idempotency_key:
                raise ValueError("execution lifecycle changed request payload hash or idempotency identity")
            reconciliation_expectations = {
                "submission_reconciled_found_running": ("found_running", "running", False),
                "submission_reconciled_found_completed_pending_receipt": ("found_completed_pending_receipt", "completed", False),
                "submission_reconciled_found_failed": ("found_failed", "failed", False),
                "submission_reconciled_not_found_safe_to_submit": ("not_found_safe_to_submit", "not_found", True),
            }
            expected_reconciliation = reconciliation_expectations.get(event["event_type"])
            if expected_reconciliation is not None:
                reconciliation = transition["reconciliation"]
                if reconciliation is None or transition["reconciliation_ref"] != reconciliation["reconciliation_evidence_ref"]:
                    raise ValueError("reconciliation outcome lacks the exact structured signed evidence reference")
                expected_outcome, expected_status, may_resubmit = expected_reconciliation
                if reconciliation["outcome"] != expected_outcome or reconciliation["remote_status"] != expected_status or reconciliation["resubmission_authorized"] is not may_resubmit:
                    raise ValueError("reconciliation event does not preserve its exact producer outcome")
                remote_identity_present = reconciliation["remote_execution_id"] is not None and reconciliation["remote_execution_sha256"] is not None
                result_present = reconciliation["remote_result_sha256"] is not None
                not_found_present = reconciliation["not_found_evidence_sha256"] is not None
                if may_resubmit:
                    if remote_identity_present or result_present or not not_found_present or reconciliation["reconciliation_evidence_ref"]["sha256"] != reconciliation["not_found_evidence_sha256"]:
                        raise ValueError("safe resubmission requires exact signed remote not-found evidence and no remote execution")
                    safe_resubmission_authorization_ref = copy.deepcopy(reconciliation["reconciliation_evidence_ref"])
                elif expected_status == "completed":
                    if not remote_identity_present or not result_present or not_found_present:
                        raise ValueError("completed-pending-receipt reconciliation lacks exact remote execution and result identity")
                elif not remote_identity_present or not_found_present:
                    raise ValueError("running/failed reconciliation lacks exact remote execution identity")
                if transition["resubmission_authorization_ref"] is not None or transition["resubmission_authorization_consumed"]:
                    raise ValueError("reconciliation outcome cannot pre-consume its resubmission authorization")
            elif event["event_type"] == "submission_resubmitted_after_signed_not_found":
                if safe_resubmission_authorization_ref is None or transition["resubmission_authorization_ref"] != safe_resubmission_authorization_ref or not transition["resubmission_authorization_consumed"]:
                    raise ValueError("resubmission requires and must consume the exact one-time signed not-found authorization")
                if transition["reconciliation"] is not None or transition["reconciliation_ref"] is not None or transition["remote_receipt_ref"] is not None:
                    raise ValueError("resubmission cannot invent a second reconciliation outcome")
                safe_resubmission_authorization_ref = None
            elif transition["reconciliation"] is not None or transition["reconciliation_ref"] is not None or transition["remote_receipt_ref"] is not None or transition["resubmission_authorization_ref"] is not None or transition["resubmission_authorization_consumed"]:
                raise ValueError("non-reconciliation transition carries ambiguous reconciliation or resubmission evidence")
            lifecycle_state = transition["to_state"]
        elif transition is not None:
            raise ValueError("non-lifecycle event attempted an execution state transition")
        validate_signature_trust_record(
            event["signature_trust"], trusted_keys, production_required=production_required,
            expected_signer_role="main_bridge_event_signer" if production_required else None,
            use_time=use_time, runtime_verification_context=runtime_verification_context,
        )
        if production_required:
            verify_ed25519_runtime_signature(
                event["event_sha256"], event["signature"], event["signature_domain"],
                event["signature_trust"], trusted_keys, runtime_verification_context,
                expected_signer_role="main_bridge_event_signer", use_time=use_time,
            )
        previous_hash = event["event_sha256"]
    if journal_pin["stream_id"] != stream_id or journal_pin["checkpoint_sequence"] != events[-1]["sequence"] or journal_pin["head_event_sha256"] != events[-1]["event_sha256"]:
        raise ValueError("event journal head does not match the pinned signed checkpoint")
    if journal_pin["forks_allowed"] or journal_pin["deletion_or_reorder_allowed"]:
        raise ValueError("event journal pin permits forbidden history mutation")
    if production_required:
        validate_journal_pin_runtime(journal_pin, trusted_keys, runtime_verification_context, use_time=use_time)
    else:
        validate_signature_trust_record(journal_pin["checkpoint_signature_trust"], trusted_keys)


def validate_readiness_projection(
    readiness: dict[str, Any], *, release_snapshot: dict[str, Any] | None = None, adoption: dict[str, Any] | None = None,
    bridge_release: dict[str, Any] | None = None, consumer: dict[str, Any] | None = None, trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None, use_time: str | None = None,
) -> None:
    profiles = readiness["profile_readiness"]
    pages = readiness["page_readiness"]
    if [item["completion_profile"] for item in profiles].count("core_autonomous_runtime") != 1 or any([item["completion_profile"] for item in profiles].count(profile) != 1 for profile in COMPLETION_PROFILES):
        raise ValueError("readiness projection must contain exactly one record for every completion profile")
    expected_pages = ["home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"]
    if any([item["page_id"] for item in pages].count(page) != 1 for page in expected_pages):
        raise ValueError("readiness projection must contain exactly one record for every App page")
    profile_by_id = {item["completion_profile"]: item for item in profiles}
    if not profile_by_id["core_autonomous_runtime"]["required_for_core_release"] or profile_by_id["independent_real_accuracy"]["required_for_core_release"] or profile_by_id["scale_daz_maturity"]["required_for_core_release"]:
        raise ValueError("readiness completion-profile core-impact flags are incorrect")
    if any(blocker["completion_profile"] != "core_autonomous_runtime" or blocker["core_impact"] != "blocking" for blocker in readiness["core_blockers"]):
        raise ValueError("core blocker collection contains an optional or nonblocking profile blocker")
    if any(blocker["completion_profile"] == "core_autonomous_runtime" or blocker["core_impact"] != "non_blocking" for blocker in readiness["optional_profile_blockers"]):
        raise ValueError("optional blocker collection can incorrectly affect core readiness")
    if readiness["blockers"] != [*readiness["core_blockers"], *readiness["optional_profile_blockers"]]:
        raise ValueError("aggregate readiness blockers do not equal core plus optional blockers")
    journal_pin = readiness["journal_pin"]
    if journal_pin is not None and (readiness["event_cursor"]["stream_id"] != journal_pin["stream_id"] or readiness["event_cursor"]["last_sequence"] != journal_pin["checkpoint_sequence"] or readiness["event_cursor"]["last_event_sha256"] != journal_pin["head_event_sha256"]):
        raise ValueError("readiness event cursor does not match the pinned journal checkpoint")
    if readiness["fixture_only"] and (readiness["runtime_readiness_claimed"] or readiness["runtime_completion_claimed"]):
        raise ValueError("fixture readiness projection cannot claim runtime readiness or completion")
    if readiness["runtime_readiness_claimed"] != readiness["runtime_completion_claimed"]:
        raise ValueError("runtime readiness and completion claims must be identical derived release state")
    if readiness["runtime_readiness_claimed"]:
        if release_snapshot is None or adoption is None or bridge_release is None or consumer is None:
            raise ValueError("runtime readiness requires the actual release, adoption, Row348 certificate, and consumer records")
        validate_bridge_release_certificate_record(
            bridge_release, release_snapshot=release_snapshot, adoption=adoption, consumer=consumer, trusted_keys=trusted_keys or {},
            runtime_verification_context=runtime_verification_context, use_time=use_time,
        )
        if readiness["release_snapshot_ref"] != immutable_release_ref(release_snapshot) or readiness["adoption_receipt_ref"] != immutable_adoption_ref(adoption) or readiness["bridge_release_certificate_ref"] != immutable_bridge_release_ref(bridge_release):
            raise ValueError("readiness refs do not match the actual signed release/adoption/Row348 records")
        if bridge_release["release_snapshot_ref"] != readiness["release_snapshot_ref"] or bridge_release["adoption_receipt_ref"] != readiness["adoption_receipt_ref"]:
            raise ValueError("readiness and Row348 certificate disagree on exact release/adoption identity")
        if readiness["journal_pin"] != adoption["journal_pin"] or readiness["journal_pin"] != bridge_release["journal_pin"]:
            raise ValueError("readiness journal pin is not the exact trusted adoption and Row348 checkpoint")
        check_by_gate = {check["gate_id"]: check for check in bridge_release["checks"]}
        bridge_ref = immutable_bridge_release_ref(bridge_release)
        expected_runtime_refs = {
            immutable_ref_key(value)
            for value in [
                *release_snapshot["genuine_runtime_evidence_refs"], *adoption["genuine_runtime_evidence_refs"],
                *bridge_release["genuine_runtime_evidence_refs"],
                *[value for check in bridge_release["checks"] for value in check["genuine_runtime_evidence_refs"]],
            ]
        }
        if {immutable_ref_key(value) for value in readiness["genuine_runtime_evidence_refs"]} != expected_runtime_refs:
            raise ValueError("readiness runtime evidence is not the exact cross-document evidence projection")
        if immutable_ref_key(bridge_ref) not in {immutable_ref_key(value) for value in profile_by_id["core_autonomous_runtime"]["evidence_refs"]}:
            raise ValueError("core readiness profile is not bound to the exact Row348 release certificate")
        for page in pages:
            expected_page_refs = {immutable_ref_key(bridge_ref)} | {
                immutable_ref_key(check_by_gate[gate_id]["gate_report_ref"]) for gate_id in APP_PAGE_GATE_IDS[page["page_id"]]
            }
            if {immutable_ref_key(value) for value in page["evidence_refs"]} != expected_page_refs or page["blocker_codes"]:
                raise ValueError("App page readiness is not derived from its exact Row348 gate-report projection")
        required = (
            readiness["release_snapshot_ref"] is not None and readiness["adoption_receipt_ref"] is not None and readiness["active_pin_status"] == "active"
            and readiness["row218_status"] == "passed" and readiness["rows321_347_status"] == "passed" and readiness["row348_release_status"] == "released"
            and readiness["signing_trust_status"] == "trusted" and readiness["journal_integrity_status"] == "trusted_current" and journal_pin is not None
            and bool(readiness["genuine_runtime_evidence_refs"]) and profile_by_id["core_autonomous_runtime"]["status"] == "ready"
            and all(page["status"] == "ready" for page in pages) and not readiness["core_blockers"] and not readiness["fixture_only"]
            and bridge_release["release_allowed"] and adoption["production_consumption_allowed"] and adoption["active_pin_written"]
        )
        if not required:
            raise ValueError("runtime-ready projection contradicts a required release, pin, profile, page, evidence, trust, journal, row, or blocker state")


def validate_result_certificate_pair(
    result: dict[str, Any], certificate: dict[str, Any] | None,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    *, use_time: str | None = None, production_required: bool = False,
) -> None:
    validate_mask_lineage(result)
    if result["normalization_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_normalization_hash_signature_and_signature_trust" or result["normalization_payload_sha256"] != normalized_result_sha256(result):
        raise ValueError("normalized result canonical seal mismatch")
    if result["raw_producer_receipt_payload_sha256"] == result["normalization_payload_sha256"]:
        raise ValueError("raw producer receipt and normalized Main result may not share an ambiguous payload identity")
    if production_required:
        if result["fixture_only"]:
            raise ValueError("fixture result cannot satisfy production certification")
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        raw_receipt_bytes = resolve_verified_artifact_bytes(result["raw_producer_receipt_ref"], runtime_verification_context)
        raw_receipt = strict_json_loads(raw_receipt_bytes)
        if not isinstance(raw_receipt, dict):
            raise ValueError("raw producer receipt is not a JSON object")
        if (
            result["raw_producer_receipt_ref"]["record_type"] != raw_receipt.get("record_type")
            or result["raw_producer_receipt_ref"]["record_id"] != raw_receipt.get("receipt_id")
        ):
            raise ValueError("raw producer receipt immutable-ref identity differs from the signed document")
        validate_frozen_producer_document(raw_receipt, "mask_acquisition_receipt", runtime_verification_context)
        recomputed_raw_sha256 = maskfactory_document_sha256(raw_receipt, excluded=("receipt_payload_sha256", "signature"))
        raw_signature = raw_receipt.get("signature")
        raw_trust = raw_receipt.get("trust_binding")
        raw_signature_public_sha256 = None
        if isinstance(raw_signature, dict) and isinstance(raw_signature.get("public_key_base64"), str):
            try:
                raw_signature_public_sha256 = sha256_bytes(base64.b64decode(raw_signature["public_key_base64"], validate=True))
            except (ValueError, binascii.Error):
                raw_signature_public_sha256 = None
        if (
            raw_receipt.get("receipt_payload_sha256") != recomputed_raw_sha256
            or recomputed_raw_sha256 != result["raw_producer_receipt_payload_sha256"]
            or not isinstance(raw_signature, dict)
            or raw_signature.get("signed_payload_sha256") != recomputed_raw_sha256
            or raw_signature.get("signed_payload_format") != "sha256_digest_bytes"
            or raw_signature.get("value_base64") != result["raw_producer_receipt_signature"]
            or not isinstance(raw_trust, dict)
            or raw_trust.get("key_role") != "producer_receipt"
            or raw_trust.get("signing_key_id") != result["raw_producer_receipt_signature_trust"]["signing_key_id"]
            or raw_signature.get("key_id") != raw_trust.get("signing_key_id")
            or raw_signature_public_sha256 != raw_trust.get("signing_public_key_sha256")
            or raw_signature_public_sha256 != result["raw_producer_receipt_signature_trust"]["embedded_public_key_sha256"]
        ):
            raise ValueError("normalized result does not bind the exact signed raw producer receipt")
        validate_raw_receipt_projection(raw_receipt, result, runtime_verification_context)
        validate_signature_trust_record(
            result["raw_producer_receipt_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="maskfactory_receipt_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            result["raw_producer_receipt_payload_sha256"], result["raw_producer_receipt_signature"], result["raw_producer_receipt_signature_domain"],
            result["raw_producer_receipt_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="maskfactory_receipt_signer", use_time=use_time,
            signature_message_format="digest_bytes",
        )
        validate_signature_trust_record(
            result["normalization_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_normalization_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            result["normalization_payload_sha256"], result["normalization_signature"], result["normalization_signature_domain"],
            result["normalization_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_normalization_signer", use_time=use_time,
        )
    authority = result["authority"]
    if authority["authority_state"] != "certified":
        return
    if result["fixture_only"]:
        raise ValueError("fixture result cannot satisfy production certification")
    if certificate is None or certificate["status"] != "active":
        raise ValueError("certified result requires an active exact operational certificate")
    if certificate["fixture_only"] or certificate["certification_context"] != "production_runtime":
        raise ValueError("fixture certificate cannot satisfy production certification")
    validate_operational_certificate_record(
        certificate, production_required=production_required, trusted_keys=trusted_keys,
        runtime_verification_context=runtime_verification_context, use_time=use_time,
    )
    validate_source_artifact(certificate["source_artifact"])
    validate_media_scope(certificate["media_scope"])
    if certificate["access_mode"] != result["access_mode"]:
        raise ValueError("operational certificate access mode mismatch")
    if certificate["serving_route_id"] != result["route_id"]:
        raise ValueError("operational certificate serving route mismatch")
    if certificate["release_snapshot_ref"] != result["release_snapshot_ref"]:
        raise ValueError("operational certificate release mismatch")
    if certificate["execution_stack_ref"] != result["execution_stack_ref"]:
        raise ValueError("operational certificate execution stack mismatch")
    if certificate["source_artifact"]["sha256"] != result["source_artifact"]["sha256"]:
        raise ValueError("operational certificate source mismatch")
    if certificate["media_scope"] != result["media_scope"] or not certificate["media_scope"]["exact_frame_scope_only"]:
        raise ValueError("operational certificate media/frame scope mismatch or cross-frame authority")
    output_refs = {(value["record_type"], value["record_id"], value["revision"], value["sha256"]) for value in certificate["output_refs"]}
    for mask in result["masks"]:
        key = tuple(mask["mask_ref"][name] for name in ("record_type", "record_id", "revision", "sha256"))
        if key not in output_refs:
            raise ValueError("operational certificate output mismatch")
    result_owners = {(value["character_instance_id"], value["provider_person_index"]) for value in result["owner_bindings"]}
    certificate_owners = {(value["character_instance_id"], value["provider_person_index"]) for value in certificate["owner_bindings"]}
    if result_owners != certificate_owners:
        raise ValueError("operational certificate owner mismatch")
    if certificate["transform_chain"] != result["transform_chain"]:
        raise ValueError("operational certificate transform mismatch")
    if result["authority"]["certificate_scope"] != certificate["certificate_scope"]:
        raise ValueError("normalized result certificate scope is not the exact signed operational certificate scope")
    for mask in result["masks"]:
        if mask["authority"]["certificate_scope"] != certificate["certificate_scope"]:
            raise ValueError("per-mask authority scope differs from the exact signed operational certificate scope")
        for parent in mask["parents"]:
            if parent["parent_operational_certificate_ref"] == result.get("operational_certificate_ref") and parent["parent_authority"]["certificate_scope"] != certificate["certificate_scope"]:
                raise ValueError("parent authority widened the exact signed operational certificate scope")
    certificate_ref = result.get("operational_certificate_ref")
    authority_ref = authority.get("certificate_ref")
    if certificate_ref != authority_ref or certificate_ref is None:
        raise ValueError("operational certificate reference mismatch")
    if certificate_ref["record_type"] != certificate["record_type"] or certificate_ref["record_id"] != certificate["maskfactory_operational_certificate_v2_id"]:
        raise ValueError("operational certificate identity mismatch")
    if certificate_ref != immutable_operational_certificate_ref(certificate):
        raise ValueError("operational certificate immutable payload hash mismatch")
    if production_required and resolve_verified_artifact_bytes(certificate_ref, runtime_verification_context) != operational_certificate_payload_bytes(certificate):
        raise ValueError("operational certificate resolved bytes differ from the signed certificate payload")
    if not certificate["qa_bindings"] or not certificate["evidence_manifest_refs"] or not certificate["revocation_manifest_refs"]:
        raise ValueError("operational certificate evidence or revocation manifest missing")


def validate_mask_lineage(result: dict[str, Any]) -> None:
    ranks = {state: index for index, state in enumerate(AUTHORITY_STATES)}
    masks = result.get("masks", [])
    mask_ranks: list[int] = []
    for mask in masks:
        lineage_kind = mask["lineage_kind"]
        operation = mask["derivation_operation"]
        parents = mask["parents"]
        if lineage_kind == "original" and (operation != "none" or parents):
            raise ValueError("original mask lineage must use operation none and have no parents")
        if lineage_kind == "derived" and (operation == "none" or not parents):
            raise ValueError("derived mask lineage requires an actual derivation operation and at least one parent")
        child_rank = ranks[mask["authority"]["authority_state"]]
        mask_ranks.append(child_rank)
        for parent in parents:
            parent_authority = parent["parent_authority"]
            parent_rank = ranks[parent_authority["authority_state"]]
            if child_rank > parent_rank:
                raise ValueError("derived child authority exceeds parent authority ceiling")
            if parent["parent_operational_certificate_ref"] != parent_authority["certificate_ref"]:
                raise ValueError("parent operational certificate reference does not match parent authority")
    if masks:
        result_rank = ranks[result["authority"]["authority_state"]]
        if result.get("authority_aggregation_rule") != "minimum_of_all_mask_authorities":
            raise ValueError("normalized result authority aggregation rule is missing or unknown")
        if result_rank != min(mask_ranks):
            raise ValueError("normalized result authority must equal the minimum per-mask authority")


def validate_operational_certificate_record(
    certificate: dict[str, Any], *, production_required: bool = False,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> None:
    validate_source_artifact(certificate["source_artifact"])
    validate_media_scope(certificate["media_scope"])
    context = certificate["certification_context"]
    runtime_refs = certificate["genuine_runtime_evidence_refs"]
    if certificate["certificate_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_certificate_hash_signature_and_signature_trust" or certificate["signature_domain"] != "comfy_ui_main.maskfactory_operational_certificate.v2" or certificate["certificate_payload_sha256"] != operational_certificate_sha256(certificate):
        raise ValueError("operational certificate canonical hash or signature domain mismatch")
    if certificate["fixture_only"]:
        if context != "fixture_validation" or runtime_refs or certificate["runtime_completion_claimed"]:
            raise ValueError("fixture certificate may validate fixtures only and cannot carry runtime authority")
    if context == "production_runtime" and (certificate["fixture_only"] or not runtime_refs or certificate["runtime_completion_claimed"]):
        raise ValueError("production certificate requires non-fixture genuine runtime evidence")
    if context == "production_runtime" and production_required:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        use_at = parse_timestamp(use_time)
        if certificate["status"] != "active" or certificate["revocation_ref"] is not None or not parse_timestamp(certificate["issued_at"]) <= use_at < parse_timestamp(certificate["expires_at"]):
            raise ValueError("operational certificate is inactive, revoked, future-issued, or expired at use time")
        raw_certificate_bytes = resolve_verified_artifact_bytes(certificate["raw_producer_certificate_ref"], runtime_verification_context)
        raw_certificate = strict_json_loads(raw_certificate_bytes)
        if not isinstance(raw_certificate, dict):
            raise ValueError("raw producer operational certificate is not a JSON object")
        if (
            certificate["raw_producer_certificate_ref"]["record_type"] != raw_certificate.get("record_type")
            or certificate["raw_producer_certificate_ref"]["record_id"] != raw_certificate.get("certificate_id")
        ):
            raise ValueError("raw producer certificate immutable-ref identity differs from the signed document")
        validate_frozen_producer_document(raw_certificate, "operational_autonomy_certificate", runtime_verification_context)
        recomputed_raw_sha256 = maskfactory_document_sha256(raw_certificate, excluded=("certificate_payload_sha256", "signature"))
        raw_signature = raw_certificate.get("signature")
        release_binding = raw_certificate.get("release_binding")
        raw_signature_public_sha256 = None
        if isinstance(raw_signature, dict) and isinstance(raw_signature.get("public_key_base64"), str):
            try:
                raw_signature_public_sha256 = sha256_bytes(base64.b64decode(raw_signature["public_key_base64"], validate=True))
            except (ValueError, binascii.Error):
                raw_signature_public_sha256 = None
        if (
            raw_certificate.get("certificate_payload_sha256") != recomputed_raw_sha256
            or recomputed_raw_sha256 != certificate["raw_producer_certificate_payload_sha256"]
            or not isinstance(raw_signature, dict)
            or raw_signature.get("signed_payload_sha256") != recomputed_raw_sha256
            or raw_signature.get("signed_payload_format") != "sha256_digest_bytes"
            or raw_signature.get("value_base64") != certificate["raw_producer_certificate_signature"]
            or not isinstance(release_binding, dict)
            or raw_signature.get("key_id") != certificate["raw_producer_certificate_signature_trust"]["signing_key_id"]
            or raw_signature_public_sha256 != certificate["raw_producer_certificate_signature_trust"]["embedded_public_key_sha256"]
        ):
            raise ValueError("normalized operational certificate does not bind the exact signed raw producer certificate")
        validate_raw_certificate_projection(raw_certificate, certificate, runtime_verification_context)
        validate_signature_trust_record(
            certificate["raw_producer_certificate_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="maskfactory_operational_certificate_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            certificate["raw_producer_certificate_payload_sha256"], certificate["raw_producer_certificate_signature"], certificate["raw_producer_certificate_signature_domain"],
            certificate["raw_producer_certificate_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="maskfactory_operational_certificate_signer", use_time=use_time,
            signature_message_format="digest_bytes",
        )
        validate_signature_trust_record(
            certificate["signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_normalization_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_runtime_evidence_refs(runtime_refs, runtime_verification_context)
        verify_runtime_evidence_refs(certificate["evidence_manifest_refs"], runtime_verification_context)
        verify_runtime_evidence_refs(certificate["revocation_manifest_refs"], runtime_verification_context)
        resolve_verified_artifact_bytes(certificate["runtime_provenance"]["runtime_manifest_ref"], runtime_verification_context)
        for binding in certificate["qa_bindings"]:
            resolve_verified_artifact_bytes(binding["qa_record_ref"], runtime_verification_context)
        verify_ed25519_runtime_signature(
            certificate["certificate_payload_sha256"], certificate["signature"], certificate["signature_domain"],
            certificate["signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_normalization_signer", use_time=use_time,
        )
    if production_required and context != "production_runtime":
        raise ValueError("fixture certificate cannot satisfy production certification")
    validate_transform_chain(certificate["transform_chain"])
    runtime = certificate["runtime_provenance"]
    if runtime["runtime_kind"] == "container" and runtime["container_image_digest"] is None:
        raise ValueError("container runtime certification requires an exact image digest")
    if runtime["runtime_kind"] != "container" and runtime["container_image_digest"] is not None:
        raise ValueError("native/venv runtime certification must not fabricate a container digest")


def validate_bridge_release_certificate_record(
    release: dict[str, Any], *, release_snapshot: dict[str, Any] | None = None, adoption: dict[str, Any] | None = None,
    consumer: dict[str, Any] | None = None, trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None, use_time: str | None = None,
) -> None:
    runtime_refs = release["genuine_runtime_evidence_refs"]
    if release["release_allowed"] and not runtime_refs:
        raise ValueError("Row348 release requires non-fixture genuine runtime evidence")
    checks = release["checks"]
    gate_ids = [check["gate_id"] for check in checks]
    if len(gate_ids) != len(REQUIRED_BRIDGE_RELEASE_GATE_IDS) or len(set(gate_ids)) != len(gate_ids) or set(gate_ids) != set(REQUIRED_BRIDGE_RELEASE_GATE_IDS):
        raise ValueError("Row348 requires exactly one closed gate report for Row218 and every Row321-347 gate")
    for check in checks:
        if check["gate_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_gate_hash_signature_and_signature_trust" or check["signature_domain"] != "comfy_ui_main.maskfactory_bridge_release_gate_report.v2":
            raise ValueError("Row348 gate report hash or signature domain mismatch")
        if check["derived_pass"] != (check["status"] == "pass"):
            raise ValueError("Row348 gate pass boolean is self-declared rather than derived from gate status")
        if check["gate_report_ref"]["sha256"] != check["gate_report_sha256"] or check["gate_report_sha256"] != release_gate_report_sha256(check):
            raise ValueError("Row348 gate report immutable identity or canonical hash mismatch")
        if not check["evidence_refs"] or not check["evaluator_manifest_ref"]:
            raise ValueError("Row348 gate report lacks exact evidence or evaluator identity")
    by_gate = {check["gate_id"]: check for check in checks}
    derived_row218 = by_gate["row218_runtime"]["status"] == "pass"
    derived_rows321_347 = all(by_gate[f"row{number}_runtime"]["status"] == "pass" for number in range(321, 348))
    if release["row218_runtime_passed"] != derived_row218 or release["rows321_347_runtime_passed"] != derived_rows321_347:
        raise ValueError("Row348 aggregate row booleans are not derived from the closed gate-report set")
    journal_trusted = release["journal_pin"]["checkpoint_signature_trust"]["trust_result"] == "trusted" and not release["journal_pin"]["forks_allowed"] and not release["journal_pin"]["deletion_or_reorder_allowed"]
    signing_trusted = journal_trusted and release["release_signature_trust"]["trust_result"] == "trusted" and all(check["signature_trust"]["trust_result"] == "trusted" for check in checks)
    if release["trusted_signing_identity_checks_passed"] != signing_trusted or release["journal_checkpoint_checks_passed"] != journal_trusted:
        raise ValueError("Row348 trust or journal booleans are self-declared rather than derived")
    if release["fixture_only"] and (release["release_allowed"] or release["status"] == "released" or runtime_refs or release["runtime_completion_claimed"]):
        raise ValueError("fixture release record cannot satisfy Row348 or runtime release")
    production_facts = (
        release["release_context"] == "production_runtime" and not release["fixture_only"] and bool(runtime_refs)
        and derived_row218 and derived_rows321_347 and signing_trusted and journal_trusted
        and all(check["genuine_runtime_evidence_refs"] for check in checks)
    )
    expected_release_allowed = bool(production_facts)
    if release["release_allowed"] != expected_release_allowed or release["runtime_completion_claimed"] != expected_release_allowed or release["status"] != ("released" if expected_release_allowed else "blocked"):
        raise ValueError("Row348 release status is not the exact derived result of all required runtime gates")
    if release["release_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_release_certificate_hash_signature_and_signature_trust" or release["release_signature_domain"] != "comfy_ui_main.maskfactory_bridge_release_certificate.v2" or release["release_certificate_sha256"] != bridge_release_certificate_sha256(release):
        raise ValueError("Row348 release certificate canonical hash mismatch")
    if expected_release_allowed:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        use_at = parse_timestamp(use_time)
        if parse_timestamp(release["created_at"]) > use_at or any(parse_timestamp(check["evaluated_at"]) > use_at for check in checks):
            raise ValueError("Row348 or a required gate report is future-issued at use time")
        verify_runtime_evidence_refs(release["genuine_runtime_evidence_refs"], runtime_verification_context)
        validate_signature_trust_record(
            release["release_signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_bridge_release_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            release["release_certificate_sha256"], release["release_signature"], release["release_signature_domain"],
            release["release_signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_bridge_release_signer", use_time=use_time,
        )
        validate_journal_pin_runtime(release["journal_pin"], trusted_keys, runtime_verification_context, use_time=use_time)
        for check in checks:
            validate_signature_trust_record(
                check["signature_trust"], trusted_keys, production_required=True,
                expected_signer_role="main_bridge_gate_signer", use_time=use_time,
                runtime_verification_context=runtime_verification_context,
            )
            resolve_verified_artifact_bytes(check["evaluator_manifest_ref"], runtime_verification_context)
            verify_runtime_evidence_refs(check["evidence_refs"], runtime_verification_context)
            verify_runtime_evidence_refs(check["genuine_runtime_evidence_refs"], runtime_verification_context)
            verify_ed25519_runtime_signature(
                check["gate_report_sha256"], check["gate_report_signature"], check["signature_domain"],
                check["signature_trust"], trusted_keys, runtime_verification_context,
                expected_signer_role="main_bridge_gate_signer", use_time=use_time,
            )
        if release_snapshot is None or adoption is None or consumer is None:
            raise ValueError("Row348 production release requires actual release, adoption, and consumer records")
        validate_adoption_trust(adoption, consumer, release_snapshot, trusted_keys or {}, runtime_verification_context, use_time=use_time)
        if not adoption["operational_certificate_evaluations"]:
            raise ValueError("Row348 end-to-end release requires an active operational runtime certificate at use time")
        if release["release_snapshot_ref"] != immutable_release_ref(release_snapshot) or release["adoption_receipt_ref"] != immutable_adoption_ref(adoption):
            raise ValueError("Row348 release/adoption refs do not match the actual signed records")


def validate_mapping_registry(mapping: dict[str, Any], schemas: dict[str, dict[str, Any]]) -> None:
    expected_names = set(PRODUCER_SCHEMA_BINDINGS)
    mapped_names = {entry["producer_contract_name"] for entry in mapping["mappings"]}
    if mapped_names != expected_names:
        raise ValueError("producer mapping contract coverage is incomplete")
    mapping_schema = schemas["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json"]
    if mapping["mapping_schema_binding"]["schema_sha256"] != sha256_bytes(canonical_json(mapping_schema)):
        raise ValueError("mapping registry is not bound to the generated mapping schema hash")
    for entry in mapping["mappings"]:
        producer = PRODUCER_SCHEMA_BINDINGS[entry["producer_contract_name"]]
        binding = entry["producer_binding"]
        if any(binding[key] != producer[key] for key in ("schema_id", "schema_version", "schema_sha256", "schema_source")):
            raise ValueError(f"producer schema binding drift in {entry['mapping_rule_id']}")
        main_matches = [schema for schema in schemas.values() if schema.get("$id") == entry["main_binding"]["schema_id"]]
        if len(main_matches) != 1 or entry["main_binding"]["schema_sha256"] != sha256_bytes(canonical_json(main_matches[0])):
            raise ValueError(f"Main schema hash binding drift in {entry['mapping_rule_id']}")
        producer_paths = {f"$.{name}" for name in producer["properties"]}
        producer_required_paths = {f"$.{name}" for name in producer.get("required", producer["properties"])}
        if set(entry["covered_producer_top_level_paths"]) != producer_paths or set(entry["producer_required_paths"]) != producer_required_paths:
            raise ValueError(f"producer field coverage drift in {entry['mapping_rule_id']}")
        if not entry["exact_producer_binding_required"] or entry["unknown_source_field_action"] != "reject" or entry["unknown_target_field_action"] != "reject" or entry["unmapped_required_field_action"] != "block_dependent_pass":
            raise ValueError(f"non-fail-closed mapping policy in {entry['mapping_rule_id']}")
        rules = entry["field_rules"]
        if not any(rule["disposition"] == "reject" for rule in rules):
            raise ValueError(f"unknown-field reject rule missing in {entry['mapping_rule_id']}")
        if any(rule["transform"]["unmapped_enum_action"] != "reject" or rule["authority"]["may_elevate_authority"] for rule in rules):
            raise ValueError(f"enum or authority fail-closed rule missing in {entry['mapping_rule_id']}")
        if any(rule["transform"]["operation"] == "enum_map" and not rule["transform"]["enum_conversion"] for rule in rules):
            raise ValueError(f"explicit enum conversion missing in {entry['mapping_rule_id']}")
        if entry["direction"] == "maskfactory_to_main":
            explicit = {rule["source_path"] for rule in rules if rule["source_path"] in producer_paths}
            targeted = {f"$.{rule['target_path'][2:].split('.', 1)[0]}" for rule in rules if isinstance(rule["target_path"], str) and rule["target_path"].startswith("$.")}
            if explicit != producer_paths or targeted != set(entry["main_required_paths"]):
                raise ValueError(f"inbound source/target field coverage incomplete in {entry['mapping_rule_id']}")
        else:
            explicit = {rule["target_path"] for rule in rules if rule["target_path"] in producer_paths}
            sourced = {f"$.{rule['source_path'][2:].split('.', 1)[0]}" for rule in rules if isinstance(rule["source_path"], str) and rule["source_path"].startswith("$.") and rule["source_path"] != "$.*"}
            if explicit != producer_paths or sourced != set(entry["covered_main_top_level_paths"]):
                raise ValueError(f"outbound source/target field coverage incomplete in {entry['mapping_rule_id']}")
    use_policy = mapping["producer_use_eligibility_policy"]
    if use_policy["producer_value_authoritative_for_main_use"] or use_policy["normalization_action"] != "drop_after_validation" or use_policy["main_target_path"] != "$.eligible_for_intended_use":
        raise ValueError("producer use_eligibility is not explicitly ignored and recomputed by Main")
    authority_schema = schemas["maskfactory_authority_decision_v2.schema.json"]
    if use_policy["main_recompute_contract_binding"]["schema_sha256"] != sha256_bytes(canonical_json(authority_schema)):
        raise ValueError("Main use-eligibility recomputation contract hash drift")
    receipt_mapping = next(entry for entry in mapping["mappings"] if entry["producer_contract_name"] == "mask_acquisition_receipt")
    use_rules = [rule for rule in receipt_mapping["field_rules"] if rule["source_path"] == "$.use_eligibility"]
    if len(use_rules) != 1 or use_rules[0]["disposition"] != "drop" or use_rules[0]["target_path"] is not None:
        raise ValueError("receipt use_eligibility field mapping is not an explicit drop")


def validate_producer_schema_bindings_against_files(producer_root: Path) -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    for contract_name, expected in sorted(PRODUCER_SCHEMA_BINDINGS.items()):
        prefix = "MaskFactory:"
        if not expected["schema_source"].startswith(prefix):
            raise ValueError(f"producer schema source is not repository-relative for {contract_name}")
        relative = expected["schema_source"][len(prefix):]
        path = producer_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"producer schema missing for {contract_name}: {path}")
        raw = path.read_bytes()
        schema = strict_json_loads(raw)
        observed_hash = sha256_bytes(raw)
        observed_version = schema.get("properties", {}).get("schema_version", {}).get("const")
        observed_properties = list(schema.get("properties", {}))
        observed_required = list(schema.get("required", []))
        expected_required = list(expected.get("required", expected["properties"]))
        mismatches = []
        if schema.get("$id") != expected["schema_id"]:
            mismatches.append("schema_id")
        if observed_version != expected["schema_version"]:
            mismatches.append("schema_version")
        if observed_hash != expected["schema_sha256"]:
            mismatches.append("schema_sha256")
        if observed_properties != expected["properties"]:
            mismatches.append("top_level_properties")
        if observed_required != expected_required:
            mismatches.append("top_level_required")
        if mismatches:
            raise ValueError(f"producer schema freeze mismatch for {contract_name}: {','.join(mismatches)}")
        checked.append({"contract_name": contract_name, "schema_path": relative, "schema_sha256": observed_hash, "top_level_properties": len(observed_properties), "top_level_required": len(observed_required)})
    return {"status": "PASS", "producer_root": producer_root.as_posix(), "contracts_checked": len(checked), "contracts": checked}


def criterion_passes(comparator: str, threshold: Any, observed: Any, blockers: list[dict[str, Any]]) -> bool:
    if comparator == "gte":
        return isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and isinstance(observed, (int, float)) and not isinstance(observed, bool) and observed >= threshold
    if comparator == "lte":
        return isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and isinstance(observed, (int, float)) and not isinstance(observed, bool) and observed <= threshold
    if comparator == "eq":
        return type(observed) is type(threshold) and observed == threshold
    if comparator == "boolean_true":
        return threshold is True and observed is True
    if comparator == "no_blockers":
        return not blockers and observed in (0, False, "none")
    raise ValueError(f"unknown policy comparator {comparator}")


def validate_promotion_policy_record(
    policy: dict[str, Any], trusted_keys: dict[str, Any] | None = None, *, production_required: bool = False,
    runtime_verification_context: dict[str, Any] | None = None, use_time: str | None = None,
) -> None:
    criterion_ids = [criterion["criterion_id"] for criterion in policy["criteria"]]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("promotion policy contains duplicate criterion IDs")
    if policy["policy_hash_profile"] != "main_domain_separated_sorted_utf8_json_v2_excluding_policy_hash_signature_signature_trust_and_artifact_ref_hash" or policy["signature_domain"] != "comfy_ui_main.maskfactory_promotion_gate_policy.v2":
        raise ValueError("promotion policy canonical hash profile mismatch")
    if policy["policy_artifact_ref"]["sha256"] != policy["policy_sha256"] or policy["policy_sha256"] != promotion_policy_sha256(policy):
        raise ValueError("promotion policy immutable binding hash mismatch")
    if policy["fixture_only"] and (policy["policy_context"] != "fixture_validation" or policy["genuine_runtime_evidence_refs"]):
        raise ValueError("fixture promotion policy cannot carry runtime authority")
    if policy["policy_context"] == "production_runtime":
        if policy["fixture_only"] or policy["policy_context"] != "production_runtime" or not policy["genuine_runtime_evidence_refs"]:
            raise ValueError("eligible production decision requires a non-fixture runtime promotion policy")
    if production_required:
        use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
        if resolve_verified_artifact_bytes(policy["policy_artifact_ref"], runtime_verification_context) != promotion_policy_payload_bytes(policy):
            raise ValueError("resolved promotion policy bytes differ from the signed immutable policy")
        verify_runtime_evidence_refs(policy["genuine_runtime_evidence_refs"], runtime_verification_context)
        verify_runtime_evidence_refs(policy["evidence_manifest_refs"], runtime_verification_context)
        verify_runtime_evidence_refs(policy["revocation_manifest_refs"], runtime_verification_context)
        validate_signature_trust_record(
            policy["signature_trust"], trusted_keys, production_required=True,
            expected_signer_role="main_promotion_policy_signer", use_time=use_time,
            runtime_verification_context=runtime_verification_context,
        )
        verify_ed25519_runtime_signature(
            policy["policy_sha256"], policy["signature"], policy["signature_domain"],
            policy["signature_trust"], trusted_keys, runtime_verification_context,
            expected_signer_role="main_promotion_policy_signer", use_time=use_time,
        )


def validate_authority_decision_record(
    decision: dict[str, Any], certificate: dict[str, Any] | None = None,
    trusted_keys: dict[str, Any] | None = None, policy: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None, *, use_time: str | None = None,
    production_required: bool = False,
) -> None:
    ranks = {state: index for index, state in enumerate(AUTHORITY_STATES)}
    observed = decision["observed_authority"]
    sufficient = ranks[observed["authority_state"]] >= ranks[decision["required_authority_state"]]
    issuer_allowed = observed["issuer_kind"] in decision["required_issuer_kinds"]
    claim_allowed = observed["claim_class"] in decision["required_claim_classes"]
    scope_sufficient = set(decision["required_certificate_scope"]).issubset(observed["certificate_scope"])
    criteria_pass = all(item["status"] == "pass" for item in decision["criterion_evaluations"])
    if decision["eligible_for_intended_use"] != (decision["decision"] == "eligible"):
        raise ValueError("authority decision and eligible flag are not equivalent")
    if decision["fixture_only"] and (decision["eligible_for_intended_use"] or observed["authority_state"] == "certified" or decision["intended_use"] == "promotion_bound"):
        raise ValueError("fixture authority decision cannot authorize certified or promotion-bound use")
    if decision["eligible_for_intended_use"] and (decision["fixture_only"] or not decision["genuine_runtime_evidence_refs"] or policy is None):
        raise ValueError("eligible decision requires trusted non-fixture runtime evidence and an immutable production policy")
    evaluation_ids = [item["criterion_id"] for item in decision["criterion_evaluations"]]
    if len(evaluation_ids) != len(set(evaluation_ids)):
        raise ValueError("authority decision contains duplicate criterion evaluations")
    for evaluation in decision["criterion_evaluations"]:
        recomputed = criterion_passes(evaluation["comparator"], evaluation["threshold"], evaluation["observed"], decision["blockers"])
        if (evaluation["status"] == "pass") != recomputed:
            raise ValueError("authority criterion status was self-declared instead of recomputed")
    if policy is not None:
        validate_promotion_policy_record(
            policy, trusted_keys, production_required=production_required and decision["eligible_for_intended_use"],
            runtime_verification_context=runtime_verification_context, use_time=use_time,
        )
        if decision["consumer_policy_ref"] != policy["policy_artifact_ref"] or decision["consumer_policy_sha256"] != policy["policy_sha256"]:
            raise ValueError("authority decision is not bound to the exact immutable promotion policy")
        policy_by_id = {item["criterion_id"]: item for item in policy["criteria"]}
        evaluation_by_id = {item["criterion_id"]: item for item in decision["criterion_evaluations"]}
        if set(policy_by_id) != set(evaluation_by_id):
            raise ValueError("authority decision omitted or invented policy criteria")
        for criterion_id, criterion in policy_by_id.items():
            evaluation = evaluation_by_id[criterion_id]
            if evaluation["comparator"] != criterion["comparator"] or evaluation["threshold"] != criterion["threshold"]:
                raise ValueError("authority decision changed a signed policy comparator or threshold")
    if decision["eligible_for_intended_use"]:
        if production_required:
            use_time = resolve_trusted_use_time(use_time, runtime_verification_context)
            if parse_timestamp(decision["decision_at"]) > parse_timestamp(use_time):
                raise ValueError("authority decision is future-issued at trusted use time")
            verify_runtime_evidence_refs(decision["decision_evidence_refs"], runtime_verification_context)
            verify_runtime_evidence_refs(decision["genuine_runtime_evidence_refs"], runtime_verification_context)
            for evaluation in decision["criterion_evaluations"]:
                resolve_verified_artifact_bytes(evaluation["evidence_ref"], runtime_verification_context)
        if not sufficient or not issuer_allowed or not claim_allowed or not scope_sufficient or not criteria_pass or decision["blockers"]:
            raise ValueError("intended-use eligibility is inconsistent with policy, authority, issuer, claim class, scope, criteria, or blockers")
        if decision["required_authority_state"] == "certified":
            temporal = decision["certificate_temporal_evaluation"]
            signature_trust = decision["certificate_signature_trust"]
            if certificate is None or temporal is None or signature_trust is None:
                raise ValueError("certified eligibility requires decision-time certificate, temporal, revocation, and signer evidence")
            if policy is None or certificate["promotion_gate_policy_ref"] != policy["policy_artifact_ref"]:
                raise ValueError("operational certificate and authority decision do not bind the same exact promotion policy")
            if temporal["decision_at"] != decision["decision_at"] or temporal["certificate_issued_at"] != certificate["issued_at"] or temporal["certificate_expires_at"] != certificate["expires_at"]:
                raise ValueError("certificate temporal evaluation is not bound to the decision and certificate")
            decision_at = parse_timestamp(decision["decision_at"])
            issued_at = parse_timestamp(certificate["issued_at"])
            expires_at = parse_timestamp(certificate["expires_at"])
            revocation_valid_from = parse_timestamp(temporal["revocation_index_valid_from"])
            revocation_valid_until = parse_timestamp(temporal["revocation_index_valid_until"])
            revocation_checked_at = parse_timestamp(temporal["revocation_checked_at"])
            valid_temporal = issued_at <= decision_at < expires_at
            current_revocation = revocation_valid_from <= revocation_checked_at <= decision_at < revocation_valid_until
            not_revoked = certificate["status"] == "active" and certificate["revocation_ref"] is None and temporal["certificate_not_revoked"]
            if not valid_temporal or not current_revocation or not not_revoked or temporal["temporal_decision"] != "valid" or not temporal["issued_not_after_decision"] or not temporal["decision_before_expiry"] or not temporal["revocation_index_current_at_decision"]:
                raise ValueError("certificate is future-issued, expired, revoked, or evaluated against a stale revocation index")
            if signature_trust != certificate["signature_trust"]:
                raise ValueError("authority decision signer evidence does not match the exact certificate")
            if temporal["certificate_ref"] != immutable_operational_certificate_ref(certificate):
                raise ValueError("authority temporal evaluation does not bind the exact certificate payload")
            if production_required:
                resolve_verified_artifact_bytes(temporal["revocation_index_ref"], runtime_verification_context)
                validate_operational_certificate_record(
                    certificate, production_required=True, trusted_keys=trusted_keys,
                    runtime_verification_context=runtime_verification_context, use_time=use_time,
                )
    if decision["intended_use"] == "promotion_bound" and decision["decision"] == "diagnostic_only":
        raise ValueError("promotion-bound decision cannot be diagnostic_only")


def validate_policy_registries(registries: dict[str, dict[str, Any]]) -> None:
    compatibility = registries["wave64_maskfactory_bridge_compatibility_policy_v2.json"]
    canonical = compatibility["canonical_payload_security_policy"]
    if not canonical["exact_profile_name_version_hash_from_adopted_release_required"] or canonical["wire_encoding"] != "utf-8" or canonical["duplicate_object_keys"] != "reject" or canonical["nonfinite_numbers"] != "reject" or not canonical["signature_domain_separation_required"] or canonical["unknown_or_ambiguous_canonicalization_action"] != "reject_before_hash_or_signature_verification":
        raise ValueError("canonical payload policy is ambiguous or does not fail closed")
    replay = compatibility["request_authentication_and_replay_policy"]
    if not all(replay[key] for key in ["authenticated_principal_required_for_production", "authorization_bound_to_exact_route_and_capability", "request_payload_hash_bound_to_idempotency_key", "nonce_required_for_production", "unknown_outcome_must_reconcile_before_resubmit"]) or replay["nonce_reuse_action"] != "reject_and_audit":
        raise ValueError("request authentication, nonce, or replay policy is not fail closed")
    safe_import = compatibility["safe_release_import_policy"]
    if not all(safe_import[key] for key in ["manifest_before_extract_required", "extract_to_isolated_staging_required", "declared_size_and_expansion_limits_required", "post_extract_manifest_hash_verification_required", "atomic_activation_after_full_verification_only"]):
        raise ValueError("release import policy omits a mandatory safe-extraction control")
    if any(safe_import[key] != "reject" for key in ["absolute_parent_traversal_drive_unc_and_device_paths", "symlink_hardlink_reparse_escape", "case_collision_and_duplicate_member_names"]):
        raise ValueError("release import policy permits a path, link, or member-name escape")

    recovery = registries["wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2.json"]
    lifecycle = recovery["execution_lifecycle"]
    states = lifecycle["states"]
    state_set = set(states)
    transitions = [tuple(transition) for transition in lifecycle["allowed_transitions"]]
    if len(states) != len(state_set) or len(transitions) != len(set(transitions)) or any(len(transition) != 2 or set(transition) - state_set for transition in transitions):
        raise ValueError("execution lifecycle has duplicate, malformed, or unknown transitions")
    terminal = set(lifecycle["terminal_states"])
    if terminal != {"succeeded", "failed", "cancelled"} or lifecycle["outcome_unknown_is_terminal"] or any(source in terminal for source, _ in transitions):
        raise ValueError("execution lifecycle terminal-state semantics are unsafe")
    required_unknown_resolutions = {
        ("outcome_unknown", "running"), ("outcome_unknown", "completed_pending_receipt"),
        ("outcome_unknown", "failed"), ("outcome_unknown", "reconciled_not_found"),
    }
    if not required_unknown_resolutions.issubset(set(transitions)) or ("reconciled_not_found", "submitted") not in transitions or lifecycle["resubmit_from_outcome_unknown_allowed"] or not lifecycle["reconciliation_must_bind_original_request_hash_idempotency_key_structured_remote_outcome_and_signed_evidence"] or not lifecycle["not_found_safe_to_submit_authorizes_exactly_one_resubmission"]:
        raise ValueError("outcome_unknown can bypass exact reconciliation")
    if not recovery["signed_checkpoint_head_required"] or recovery["journal_fork_deletion_reorder_or_reseal_action"] != "reject_and_quarantine":
        raise ValueError("event journal checkpoint/fork policy is not fail closed")

    catalog = registries["wave64_maskfactory_bridge_contract_catalog_v2.json"]
    intelligence = catalog["autonomous_intelligence_authority_policy"]
    if not intelligence["llm_vlm_outputs_must_be_schema_bound"] or not intelligence["retrieval_evidence_refs_must_be_immutable_and_hash_bound"] or intelligence["conversation_or_compaction_summary_is_durable_project_truth"] or intelligence["llm_vlm_observation_is_promotion_authority"] or intelligence["llm_can_self_promote_or_mutate_producer_truth"] or not intelligence["tool_gateway_is_only_execution_surface"] or not intelligence["deterministic_validator_policy_and_signed_evidence_own_admission_authority_and_promotion"] or not intelligence["memory_write_requires_schema_validation_provenance_and_event_journal_admission"]:
        raise ValueError("LLM/VLM/tool/memory authority boundary is unsafe")

    app = registries["wave64_maskfactory_bridge_app_read_model_mapping_v2.json"]
    if app["app_or_conversation_summary_can_establish_project_truth"] or app["llm_vlm_can_bypass_schema_validator_or_signed_policy"]:
        raise ValueError("App or conversational surfaces can bypass durable authority")


def validate_examples(examples: dict[str, dict[str, Any]], registries: dict[str, dict[str, Any]]) -> None:
    validate_policy_registries(registries)
    result = examples["maskfactory_bridge_result_v2.example.json"]
    if result["access_mode"] not in ACCESS_MODES or result["authority"]["authority_state"] != "draft" or "can_satisfy_promotion_gate" in result:
        raise ValueError("current Mode B fixture must be a factual draft result without self-declared policy eligibility")
    validate_mask_lineage(result)
    validate_request_result_pair(examples["maskfactory_bridge_request_v2.example.json"], result)
    certificate = examples["maskfactory_operational_certificate_v2.example.json"]
    required = {"certification_context", "claim_class", "release_snapshot_ref", "capability_id", "serving_route_id", "access_mode", "execution_stack_ref", "runtime_provenance", "media_scope", "output_refs", "owner_bindings", "transform_chain", "qa_bindings", "promotion_gate_policy_ref", "evidence_manifest_refs", "genuine_runtime_evidence_refs", "revocation_manifest_refs", "signature", "signature_trust"}
    if not required.issubset(certificate):
        raise ValueError("operational certificate is missing an exact binding")
    validate_operational_certificate_record(certificate)
    release = examples["maskfactory_release_snapshot_v2.example.json"]
    if not release["producer_source"]["source_clean"] or release["mutable_worktree_consumption_allowed"]:
        raise ValueError("release fixture permits dirty mutable consumption")
    validate_release_snapshot_record(release)
    consumer = examples["maskfactory_consumer_requirements_v2.example.json"]
    if consumer["human_anchor_required_for_core"] or consumer["scale_daz_required_for_core"]:
        raise ValueError("optional profiles became core blockers")
    validate_adoption_trust(examples["maskfactory_adoption_receipt_v2.example.json"], consumer, release, {})
    validate_invalidation_event_record(examples["maskfactory_invalidation_event_v2.example.json"])
    crosswalk = registries["wave64_maskfactory_bridge_authority_crosswalk_v2.json"]
    if crosswalk["access_modes"] != ACCESS_MODES or crosswalk["authority_states"] != AUTHORITY_STATES or crosswalk["issuer_kinds"] != ISSUER_KINDS:
        raise ValueError("wire vocabulary drift")
    if crosswalk["mode_a_unconditionally_promotable"] or crosswalk["mode_b_permanently_nonpromotable"]:
        raise ValueError("access mode was coupled to promotion")
    promotion = examples["maskfactory_promotion_gate_policy_v2.example.json"]
    if promotion["live_qa_strictness_control_authoritative"] or promotion["runtime_policy_mutable_from_app"] or promotion["optional_independent_accuracy_can_mutate_core_decision"] or promotion["legacy_string_gate_authoritative"]:
        raise ValueError("legacy or optional controls can mutate core promotion policy")
    if not all({"criterion_id", "dimension", "comparator", "threshold", "evidence_type", "analyzer_manifest_ref", "blocking"}.issubset(criterion) for criterion in promotion["criteria"]):
        raise ValueError("promotion criterion is not structured")
    validate_promotion_policy_record(promotion)
    legacy = registries["wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json"]
    if legacy["legacy_string_gate_can_authorize_promotion"] or legacy["live_qa_dial_can_mutate_core_decision"] or legacy["optional_independent_accuracy_can_mutate_core_decision"]:
        raise ValueError("legacy migration retains forbidden authority")
    validate_authority_decision_record(examples["maskfactory_authority_decision_v2.example.json"])
    mapping = registries["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    expected_producer_contracts = {entry["contract_name"] for entry in registries["wave64_maskfactory_bridge_contract_catalog_v2.json"]["producer_wire_contracts"]}
    mapped_contracts = {entry["producer_contract_name"] for entry in mapping["mappings"]}
    if mapped_contracts != expected_producer_contracts or mapping["unknown_or_missing_mapping_action"] != "block_dependent_pass":
        raise ValueError("producer wire to Main port mapping is incomplete or non-fail-closed")
    if any(not entry["exact_producer_binding_required"] for entry in mapping["mappings"]):
        raise ValueError("producer mapping does not require an exact adopted release binding")
    validate_mapping_registry(mapping, build_schemas())
    release_certificate = examples["maskfactory_bridge_release_certificate_v2.example.json"]
    validate_bridge_release_certificate_record(release_certificate)
    readiness = examples["maskfactory_bridge_readiness_projection_v2.example.json"]
    expected_pages = {"home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"}
    expected_profiles = set(COMPLETION_PROFILES)
    if {entry["page_id"] for entry in readiness["page_readiness"]} != expected_pages or {entry["completion_profile"] for entry in readiness["profile_readiness"]} != expected_profiles or readiness["runtime_readiness_claimed"] or readiness["genuine_runtime_evidence_refs"]:
        raise ValueError("fixture readiness projection is incomplete or overclaims runtime readiness")
    validate_readiness_projection(readiness)
    validate_event_journal([examples["maskfactory_bridge_event_v2.example.json"]], examples["maskfactory_bridge_event_v2.example.json"]["journal_pin"], {}, production_required=False)
    app = registries["wave64_maskfactory_bridge_app_read_model_mapping_v2.json"]
    if {entry["page_id"] for entry in app["pages"]} != expected_pages or not app["all_pages_read_only"] or app["app_can_mutate_producer_truth"] or app["app_can_commit_promotion"] or app["fixture_can_project_runtime_ready"]:
        raise ValueError("App page/read-model mapping is incomplete or grants forbidden authority")


def desired_outputs(project_root: Path) -> dict[str, bytes]:
    rows = build_rows()
    schemas = build_schemas()
    registries = build_registries(schemas)
    examples = build_examples()
    validate_rows(rows)
    validate_examples(examples, registries)
    outputs: dict[str, bytes] = {}
    for name, schema in schemas.items():
        outputs[f"Plan/08_SCHEMAS/{name}"] = canonical_json(schema)
    for name, registry in registries.items():
        outputs[f"Plan/10_REGISTRIES/{name}"] = canonical_json(registry)
    for name, example in examples.items():
        outputs[f"Plan/08_SCHEMAS/examples/{name}"] = canonical_json(example)

    requirements = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT, "row_range": [321, 348],
        "status": STATUS, "planning_complete": True, "runtime_complete": False, "runtime_completion_claimed": False,
        "parent_rows": [177, 178, 179, 180], "final_external_dependency": 218,
        "required_completion_profile": "core_autonomous_runtime", "optional_profiles_not_blocking": ["independent_real_accuracy", "scale_daz_maturity"],
        "workstreams": [{"id": wid, "slug": slug, "objective": objective} for wid, slug, objective in WORKSTREAMS], "requirements": rows,
    }
    req_bytes = canonical_json(requirements)
    outputs["Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"] = req_bytes
    outputs["Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"] = req_bytes

    fields = ["row_number", "item_id", "tracker_id", "workstream_id", "workstream", "domain", "phase", "title", "implementation_action", "acceptance", "dependencies", "required_artifacts", "external_gates", "status", "runtime_proof_required", "runtime_completion_claimed", "completion_profile", "optional_profiles_not_blocking", "source_citations"]
    flat_rows = [{**row, "dependencies": "|".join(row["dependencies"]), "required_artifacts": "|".join(row["required_artifacts"]), "external_gates": "|".join(row["external_gates"]), "optional_profiles_not_blocking": "|".join(row["optional_profiles_not_blocking"]), "source_citations": "|".join(row["source_citations"])} for row in rows]
    outputs["Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ITEM_ROWS.csv"] = csv_bytes(flat_rows, fields)
    tracker_fields = [*fields, "tracker_state", "next_action", "blocker"]
    tracker_rows = [{**row, "tracker_state": "planned_not_started", "next_action": "main_task_formal_adoption_then_dependency_order_implementation", "blocker": "runtime_implementation_and_evidence_not_yet_complete"} for row in flat_rows]
    outputs["Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_TRACKER_ROWS.csv"] = csv_bytes(tracker_rows, tracker_fields)

    coverage = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT, "status": "planning_contract_coverage_pass",
        "rows": len(rows), "workstreams": len(WORKSTREAMS), "rows_per_workstream": 4, "schemas": len(schemas), "registries": len(registries), "examples": len(examples), "documents": len(DOC_PATHS),
        "rows177_180_are_transitive_parents": True, "row348_transitively_depends_on_rows321_347": True, "row348_directly_depends_on_row218": True,
        "access_mode_independent_from_authority": True, "mode_b_default_authority_state": "draft", "mode_b_exact_certificate_path_supported": True, "mode_a_unconditionally_promotable": False,
        "human_anchor_required_for_core": False, "scale_daz_required_for_core": False, "schema_source_version_hash_drift_checks_present": True,
        "executable_field_complete_producer_main_mapping_present": True, "producer_use_eligibility_recomputed_by_main": True,
        "per_mask_parent_authority_ceiling_validation_present": True, "fixture_can_satisfy_runtime_certification_or_row348": False,
        "out_of_band_signer_trust_and_decision_time_revocation_present": True,
        "input_roi_output_artifact_identity_firewall_present": True, "multi_entity_scene_roster_present": True,
        "typed_executable_transform_chain_present": True, "exact_still_frame_span_scope_present": True,
        "conditional_runtime_provenance_and_execution_observation_present": True,
        "signed_checkpointed_fork_intolerant_journal_present": True, "outcome_unknown_reconciliation_state_present": True,
        "canonical_auth_nonce_replay_and_safe_import_policy_present": True,
        "llm_vlm_tool_memory_non_authority_boundary_present": True, "operational_claim_class_firewall_present": True,
        "fixture_release_and_adoption_firewall_present": True, "closed_row218_and_rows321_347_gate_set_present": True,
        "row348_aggregates_derived_from_hashed_signed_gate_reports": True, "cross_document_readiness_derivation_present": True,
        "lossless_per_target_invalidation_transition_and_supersession_present": True,
        "complete_invalidation_to_adoption_revalidation_trigger_path_present": True,
        "explicit_app_pages": ["home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"],
        "readiness_projection_v2_present": True, "producer_planning_bindings_finalized": True,
        "producer_planning_commit": "938b469", "producer_runtime_release_adoption_pending": True,
        "runtime_completion_claimed": False, "runtime_adapter_implemented": False, "runtime_release_published": False, "integrated_vertical_slice_executed": False,
    }
    coverage_bytes = canonical_json(coverage)
    outputs["Plan/Instructions/QA/Evidence/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"] = coverage_bytes
    outputs["Plan/Tracker/Evidence/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"] = coverage_bytes

    manifest_entries = []
    for path, content in sorted(outputs.items()):
        manifest_entries.append({"path": path, "sha256": sha256_bytes(content), "bytes": len(content), "source": "generated"})
    for path in STATIC_SOURCES:
        full = project_root / path
        if not full.exists():
            raise FileNotFoundError(f"missing static preservation source: {path}")
        content = full.read_bytes()
        manifest_entries.append({"path": path, "sha256": sha256_bytes(content), "bytes": len(content), "source": "static_preserved"})
    manifest = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT,
        "status": "intentional_additive_project_work_preserve_pending_main_task_adoption", "runtime_completion_claimed": False,
        "authoritative_project_root": "C:/Comfy_UI_Main", "isolated_pre_adoption_worktree": "C:/w/main-maskfactory-bridge-plan",
        "entries": sorted(manifest_entries, key=lambda entry: entry["path"]),
    }
    outputs["Plan/Instructions/Hydration_Rehydration/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PRESERVATION_MANIFEST.json"] = canonical_json(manifest)
    return outputs


def write_or_check(project_root: Path, mode: str) -> dict[str, Any]:
    outputs = desired_outputs(project_root)
    mismatches: list[str] = []
    for relative, expected in outputs.items():
        path = project_root / relative
        if mode == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.exists():
            mismatches.append(f"missing:{relative}")
        elif path.read_bytes() != expected:
            mismatches.append(f"changed:{relative}")
    if mismatches:
        raise RuntimeError("; ".join(mismatches))
    return {
        "status": "PASS", "mode": mode, "package_id": PACKAGE_ID, "rows": 28, "workstreams": 7,
        "schemas": len(build_schemas()), "registries": len(build_registries(build_schemas())), "examples": len(build_examples()),
        "generated_files_including_manifest": len(outputs), "runtime_completion_claimed": False,
        "runtime_adapter_implemented": False, "runtime_release_published": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = write_or_check(args.root.resolve(), "write" if args.write else "check")
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
