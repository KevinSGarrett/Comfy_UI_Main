# Wave64 Foley Force Alignment Gate Spec

## Purpose

Wave64 evaluates whether visual contact evidence, Wave22 force events, and Wave30 foley events remain exactly aligned under strict, hash-bound evidence.

## Trust Boundary

- Canonical root is derived from evaluator `__file__`.
- Optional `--root` must equal canonical root exactly.
- Every input path must resolve under canonical root and be hash-bound.
- Bound artifacts include request, visual contact manifest, Wave22 force manifest, Wave30 manifest, optional Wave31 manifest, optional runtime proof, optional A/V review proof, optional production bundle, visual take artifact, contact evidence artifact, and every evaluated WAV.
- Output must not collide with any bound input path.
- Output write is atomic.

## Authority Registry

The evaluator loads only:

- `Plan/10_REGISTRIES/wave64_foley_force_alignment_authority_registry.json`

It defines:

- visual intensity taxonomy,
- force profile constraints (loudness hints, normalized RMS ranges, clipping),
- material pair to foley-family rules,
- body-contact material taxonomy,
- allowed foley layers,
- sync tolerances,
- `approved_alignment_bundles`.

`approved_alignment_bundles` is intentionally empty in this implementation.

## Required Inputs

The request must bind:

- visual contact manifest,
- Wave22 force-event manifest,
- strict Wave30 audio-event manifest,
- optional Wave31 force manifest,
- optional runtime proof,
- optional A/V alignment review proof,
- optional production alignment bundle,
- finite threshold values.

### Visual Contact Manifest

Exact top-level keys:

- `run_id`, `scene_id`, `shot_id`, `take_id`, `is_synthetic`,
- `frame_rate`, `frame_time_origin_seconds`,
- `visual_take_artifact`, `contact_evidence_artifact`,
- `contact_authority`,
- `contact_edges`.

Each contact edge must bind identity, ownership, materials, visual force intensity, frame range, audio expectation, and min/max expected force-event counts.

`visual_take_artifact` and `contact_evidence_artifact` must declare `media_type`, match an allowlisted extension, and pass format recognition checks (`image/png` signature for visual take, parseable UTF-8 JSON for contact evidence).

`contact_authority` must declare:

- `authority_scope` (`body`, `contact`, `body_contact`, or `non_body_contact`),
- `gold_mask_dependency_status` (`cleared`, `missing`, `not_applicable`),
- `evidence_authority_class`,
- `production_trust_claim`.

Body, contact, and body-contact scopes cannot use `not_applicable`. A `cleared` body/contact dependency requires `gold_mask_validated`; a `missing` dependency cannot claim that class. `non_body_contact` must use `not_applicable` and cannot claim gold-mask validation.

The registry body-contact material taxonomy is authoritative for scope classification. A `non_body_contact` declaration is invalid when any bound edge contains a body-contact material.

### Wave22 Force Manifest

Exact top-level keys:

- `schema_name`, `manifest_version`,
- `run_id`, `scene_id`, `shot_id`, `take_id`, `is_synthetic`,
- `frame_rate`,
- `force_events`.

Each event must include:

- `event_id`, `contact_edge_id`,
- `source_material`, `target_material`,
- `expected_foley_family`,
- `audio_force_class`, `loudness_hint`,
- `confidence`,
- `start_frame`, `end_frame`.

### Runtime Proof and A/V Review Proof

Runtime proof requires strict metadata and exact input hash bindings, ordered force->audio->wav bindings, and booleans:

- `runtime_executed=true`
- `decode_succeeded=true`

A/V review proof requires strict metadata and one exact result per expected force event with literal booleans:

- `visual_contact_present`
- `ownership_match`
- `material_family_match`
- `force_loudness_match`
- `timing_aligned`
- `foley_present`
- `false_event_absent`

## Semantic Gates

Statuses are `PASS`, `FAIL`, `BLOCKED`.

- `event_binding_check`
- `frame_to_audio_alignment`
- `foley_presence`
- `false_event_reject`
- `av_event_alignment_review`
- `production_runtime_proof`
- `production_alignment_authority`
- `overall_pass`

No `PASS` gate may contain blockers.

### Additional Row028 Strictness

- Request `is_synthetic` must match visual manifest, Wave22 manifest, Wave30 manifest, and each matched Wave30 event synthetic state.
- Wave30 `audio_event_count` must exactly equal `audio_events` length.
- Wave30 `required_lanes` must contain every lane used by matched force-mapped events.
- Every force-to-audio mapping must satisfy:
  - `event_type == layer`,
  - both equal force `expected_foley_family`,
  - both are permitted by the selected force profile and registry allowlisted foley layers,
  - `subject_binding` identity maps to the referenced contact edge source/target entity or owner identifiers.
- Unknown material pairs fail closed. Known material-pair expected family must match force and mapped Wave30 event.
- Wave30 `av_sync_binding.frame_rate` and each mapped `expected_video_frame_range.frame_rate` must match visual and Wave22 frame rates.
- Request drift thresholds are caller-tightenable only; registry sync tolerances are mandatory ceilings.

## Gate Outcomes

- Missing runtime proof, A/V review proof, bundle, or allowlisted authority -> `BLOCKED`.
- Present semantic defects -> `FAIL`.
- Malformed JSON, invalid schema, hash mismatch, root escape, non-finite values, malformed WAV -> invalid input (`exit 1`).
- Structurally valid but failing or blocked packet -> `exit 2`.
- `exit 0` only for a genuine future fully passed allowlisted non-synthetic production bundle.

## Gold Mask Dependency

Gold-mask handling is evaluated from `visual_contact_manifest.contact_authority` rather than owner-ID substring inference.

For this gate, `gold_mask` means an authority-qualified exact mask, not
necessarily a human/manual annotation. For `core_autonomous_runtime`, a mask
qualifies when it comes from an adopted MaskFactory release or exact output and
has an active, unrevoked, scope/source/output/owner/transform/lineage-matching
`maskfactory_autonomous` certificate plus the required deterministic QA and Main
policy decision. A `human_anchor_optional` mask may satisfy a separately
selected `independent_real_accuracy` profile, but its absence cannot block the
core Foley path.

- If `authority_scope` includes body/contact and `gold_mask_dependency_status` is `missing`, both `av_event_alignment_review` and `production_alignment_authority` are `BLOCKED` with `Blocked_Gold_Mask_Authority_Missing`.
- `production_trust_claim` is self-reported and never sufficient for production authority. An exact allowlisted, non-revoked bundle remains mandatory.
- `production_alignment_authority` cannot pass when any event binding, frame alignment, presence, false-event, A/V review, or runtime prerequisite is failed or blocked.
