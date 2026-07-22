# Autonomous Video-to-Audio and Generated Sound QA Protocol

## Scope

This protocol governs Wave64 Rows067-112 and complements existing Rows025-033 protocols. It applies to retrieved sounds, transformed derivatives, layered composites, procedural sounds, neural generations, mixes, and muxes.

## Required authority layers

1. `source_and_rights_authority`
2. `visual_event_authority`
3. `audio_semantic_authority`
4. `timing_and_onset_authority`
5. `render_and_spatial_authority`
6. `technical_qa_authority`
7. `playback_review_authority` when required
8. `production_release_authority`
9. `generated_asset_promotion_authority` for reusable generated sounds

No authority layer may manufacture evidence belonging to another layer.

## Mandatory automated gates

- exact input/output hashes and canonical PCM hashes;
- model, revision, weight hash, configuration, environment, and seed;
- rights and attribution decision;
- source/target/event/material confidence;
- event coverage and false-event rejection;
- onset/contact offset and endpoint drift;
- duration, sample rate, channels, loudness, true peak, clipping, silence, and defects;
- semantic event/material/action fit;
- generated-output unexpected-class rejection;
- room, pan, distance, occlusion, and continuity consistency;
- duplicate and near-duplicate detection;
- full-duration mix/global review;
- immutable evidence and no-clobber publication.

## Timing thresholds

Thresholds must be registered per event family and frame rate. A frame-exact contact event should target an error no greater than half a source frame, with stricter sample-domain thresholds where calibrated. Windowed rustle, ambience, and movement events use explicit onset/end windows. The evaluator records both frame and sample errors.

## Semantic ensemble rule

Filename/path tags, audio embeddings, acoustic features, audio tags/captions, event-script expectations, and applicable reference comparisons are independent signals. No single signal may grant final semantic PASS. Disagreement produces lower confidence, fallback, or abstention.

## Generated candidate decision

A generated candidate must be rejected for any of the following:

- unknown output-use rights;
- missing engine/model/config provenance;
- decode failure or corrupted samples;
- wrong or extra event family;
- unexpected speech or music when excluded;
- missing/late/early primary transient;
- truncated attack or natural decay;
- material/action mismatch beyond threshold;
- severe noise, clipping, hum, dropout, or pre-reverb conflict;
- canonical or near duplicate without a justified role;
- source leakage or memorization concern identified by the configured checks;
- failed full-scene mix or AV-sync review.

## Generated-asset promotion and revocation

Passing candidate QA is necessary but not sufficient for reusable-library
admission. Promotion additionally requires accepted source-library selector,
generated-candidate provenance, and generated-sound QA dependencies; exact
output-use rights and license/attribution fields; canonical tags; exact and
near-duplicate decisions; a content-addressed no-clobber publication receipt;
and preserved `generated` origin. Synthetic fixtures never gain selector
visibility or promotion authority.

Every promoted version binds the canonical PCM hash in its object path and
retains the original generation, rights, provenance, QA, and dedup evidence.
Revocation creates a new immutable decision receipt, removes selector
eligibility, and preserves both the asset and prior evidence. Rewriting or
deleting prior evidence is forbidden.

## End-to-end orchestration and recovery

The audio run coordinator executes a content-addressed mandatory-stage DAG.
Every stage key binds the request, immutable predecessor outputs, and exact
implementation revision. A passed output is immutable: replay with the same
output is idempotent and replay with a different output fails closed. No stage
may run before every predecessor is pass-like.

Transition events are append-only and hash chained. Resume validates the run
receipt and event chain, preserves passed branches, and readies only stages
whose predecessors passed. Per-stage retries, global retries, and cost are
independently bounded. Publication requires every mandatory stage and all
dependency authorities; synthetic runs never publish.

## Row106 composite audio/AV matrix

The composite matrix consumes independently produced component receipts; it
does not replace their evaluators. Every receipt must bind the same run ID,
video SHA-256, and audio SHA-256. Event coverage, false-event rate,
contact/transient offset, endpoint drift, semantic/material match, room
consistency, and global review are separately gated. Decode, full-duration
review, clipping/true peak, loudness, dialogue masking, and repetition are
additional hard checks.

All gates must pass. A high score from one metric cannot override another
failure. Synthetic and adversarial fixtures calibrate the implementation but
never grant release authority. Production acceptance additionally requires
accepted Rows090, 091, 097, 103, and 105, rights-bound genuine media, and a
combined full-duration frame/contact/audio playback review.

Evidence is emitted at
`Plan/Instructions/QA/Evidence/Wave64/TRK-W64-106_audio_av_qa_matrix.json`.
The current delta remains a HOLD until those production authorities exist.

## Row107 modular ComfyUI/API boundary

Audio execution is split into exactly six bounded modules: analysis request,
event manifest, selector result, generated candidate, mix render, and QA
evaluation. Modules use unique namespaces and versioned record types. No module
may contain credentials or own reasoning, dependency selection, retry policy,
evidence acceptance, publication, promotion, or release decisions.

Contract-only modules are inactive. Activation requires the exact workflow
path, accepted producer dependencies, static graph/schema validation against
the target runtime's `/object_info`, and an isolated runtime smoke under a
coordinator lease. One oversized graph cannot substitute for these six module
boundaries, and a workflow queue/history result remains evidence rather than
external-controller authority.

## Row108 runtime, cache, batch, and cost controls

Feature and embedding cache keys bind exact source, model, configuration,
implementation, and decoder hashes. A change to any field invalidates reuse.
Resume preserves hash-matched passed items and never reruns them merely to
refresh evidence; a changed retained input identity fails closed.

Every batch is bounded by item count, estimated peak VRAM, storage reserve,
retry count, and USD budget before admission. Transfer manifests bind source
hash, byte count, unique destination, and verification state. Live work is
limited to the registered sole RunPod pod and requires an exact sanitized
exclusive coordinator lease. Completion additionally requires actual cost,
TTL/watchdog, and final lease-release evidence. Synthetic receipts never grant
runtime authority.

## Row110 observability and deterministic replay

Every audio run uses an append-only, strictly sequenced hash chain. Events
retain stage timing, exact model hashes, cache observations, candidate ranking
and rejection reasons, transform lineage, mix decisions, QA evidence, retries,
authority evidence, final artifact hashes, and explicit external blockers.

Replay recomputes the projection from immutable events. Payload, parent,
sequence, event, ledger, or recorded-projection mismatch fails closed. A
released mix or promoted generated asset must replay with every required event,
exact final-artifact and authority hashes, and no unresolved blocker. Synthetic
replay validates the mechanism but cannot grant release authority.

## Row111 existing-component compatibility

Every reused component has one unique capability owner and an exact source
path, byte count, and SHA-256. Its disposition is `reuse_direct`, `adapt_once`,
`evidence_only_hold`, or `replace_with_reason`. Adaptation requires a named
versioned contract and cannot exceed the source component's authority ceiling.

Known limitations and completed-proof guards are mandatory. File existence,
historical runtime, or structural tests do not create production authority.
Wave31 structural compilers and the historical MMAudio packet remain
evidence-only until their modern ownership, model, runtime, and QA gates pass.
Hash drift invalidates the inventory and must be reviewed before reuse.

## Benchmark requirements

Benchmarks must include:

- heel and toe phases on wood, tile, carpet, concrete, and ambiguous surfaces;
- bare foot, soft shoe, sneaker, boot, and hard heel;
- hand/body contacts with visible, clothed, occluded, and multi-actor ownership cases;
- fabric, prop, furniture, door, water, and ambience events;
- single and repeated events;
- dry and reverberant sources;
- fixed and moving cameras;
- cuts, slow motion, variable frame rate, and offscreen events;
- intentionally silent visual motion;
- adversarial filename and semantic mismatches;
- generated candidates containing extra events, wrong materials, or timing drift.

Train, calibration, and final test partitions remain separate. Generated outputs cannot become reference truth merely by passing their own model-based evaluator.

## Completion rule

Rows067-112 remain planned or blocked until their exact implementation, tests, runtime evidence, and QA pass. Row112 cannot pass while any prerequisite row is incomplete or while required playback/production authority is absent.

## Row112 certification-matrix gate

Row112 must inspect all 45 dependency rows, Rows067-111, from exactly one
unambiguous current delta per tracker. A dependency is accepted only when
`row_complete` is the boolean `true`, its status is pass-like, and its evidence
hash matches the inspected file. Missing, invalid, held, or competing current
deltas are exact blockers.

When a row intentionally retains multiple files whose names contain
`CURRENT_DELTA`, a canonical record may be selected only by the Row112 current-
delta authority registry. The registry must bind the exact complete candidate
set and every SHA-256, designate one contract-level canonical record, retain all
others as supplemental evidence, and confer no acceptance upgrade. Membership
or hash drift restores the ambiguity blocker.

Certification additionally requires independently hash-bound evidence and
artifact hashes for genuine runtime, rights, provenance, full-duration review,
AV sync, global QA, multimodal release, and replay reconstruction. These gates
must cover at least three unique genuine-video hashes. A rollup record cannot
substitute for an individual gate, and any synthetic dependency, gate, or video
fixture is calibration-only and cannot grant production authority.

## Row101 video-conditioned Foley gate

Bind the exact video, canonical event script, generated candidate, engine
family and revision, model, qualification record, and runtime record by SHA-256.
Each trusted deterministic one-shot anchor must have exactly one explicit
decision (`retain`, `supplement`, or `blend_explicit`) and exactly one alignment
measurement. `overwrite` and implicit replacement are forbidden.

Production eligibility requires Rows083, 091, 092, 097, and 099 to be accepted,
the engine to be registered and independently qualified, genuine runtime proof,
onset error no greater than 50 ms, and coverage of at least 0.8 for every
anchor. Historical or synthetic execution may establish candidate evidence but
cannot establish current production authority.
