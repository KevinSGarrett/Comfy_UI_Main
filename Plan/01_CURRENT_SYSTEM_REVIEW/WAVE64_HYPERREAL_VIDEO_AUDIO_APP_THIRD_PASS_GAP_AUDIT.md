# Wave64 Hyperreal Video, Audio/AV, and App Third-Pass Gap Audit

Updated: 2026-07-16 America/Chicago

## Verdict

The project contains broad, valuable domain coverage, but coverage count is not
the same as implementation depth. Many original canonical video, audio, and App
documents are short outlines. The strongest runtime evidence remains bounded to
individual lanes such as keyframe/video tests, deterministic audio/mux work,
MMAudio proof, speech controls, and review packets. A unified hyperreal media
runtime and operator application do not yet exist.

## Reconciled evidence and legacy-authority findings

### Video

- The legacy Wave27 video registry/router can describe WAN as proven while the
  newer canonical capability registry correctly leaves an exact production
  bundle unresolved. Production routing must use the newer exact-bundle and
  bucket-scoped certificate authority; broad legacy engine status is diagnostic
  evidence only.
- The currently evidenced WAN lane is a bounded start-image TI2V lane. It does
  not prove multi-anchor keyframes, pose/depth/contact conditioning, temporal
  masks, per-character adapters, generative failed-span repair, moving-camera
  continuity, or multi-character ownership.
- Several Wave28, Wave29, and Wave33 files named as schemas are descriptive
  planning records rather than strict JSON Schema contracts. Their shallow
  validators and caller-supplied aggregate scores cannot authorize production
  execution or promotion.
- Existing temporal scoring can hide missing dimensions or worst-span failures.
  Observation, deterministic gate decision, immutable accepted-parent change,
  and promotion are therefore separated in this package.
- The existing OpenCV short-span lane is useful for bounded deterministic
  defects, but is not evidence of identity-, physics-, contact-, or
  boundary-certified generative video repair.

### Audio and AV

- Genuine MMAudio execution, 48 kHz stereo mixing, and bounded mux correction
  are valuable runtime evidence. They do not yet prove event ownership,
  perceptual acceptance, spatial/room authority, speech continuity, or a full
  promoted AV master.
- Speech-engine candidates and speech controls exist, but candidate creation is
  not voice qualification. Identity, pronunciation, prosody, nonverbal vocal
  behavior, forced alignment, viseme production, room rendering, and downstream
  mix/mux certification remain separate gates.
- Audio provenance needs three orthogonal axes: origin class, realization
  action, and derivation state. A single source label cannot distinguish a
  recorded library asset, a processed derivative, a neural reconstruction, and
  a hybrid layer with enough precision for routing or audit.
- Legacy delivery fixtures must not make 16 kHz mono or one container profile a
  universal production authority. Delivery profiles are explicit and the
  current high-fidelity planning baseline is 48 kHz with profile-specific
  channel, codec, loudness, true-peak, and sync requirements.
- Existing library indexing proves discoverability, not acoustic suitability.
  Assets require content, material, force, perspective, noise, room, license,
  quality, and bucket-specific qualification before automatic selection.

### Operator application

- The earlier App Mode work is a useful control inventory, not a built
  application. It contains incompatible envelope shapes, contradictory control
  definitions, and controls that imply direct rendering or promotion authority.
- ComfyUI App Mode remains a bounded single-workflow input/output surface. The
  durable multi-workflow product is the controller console; optional App Mode
  launchers may only create unpromoted candidates under short-lived authority.
- UI disclosure modes and authorization roles are independent. A browser action
  is always a typed request followed by controller authorization, a durable
  receipt, and projection reconciliation; it never mutates ComfyUI production
  state or promotes an artifact directly.

## Legacy surfaces requiring fail-closed quarantine or migration

1. Broad engine labels and mutable readiness flags that are not bound to an
   immutable model, workflow, runtime, control, hardware, and certificate tuple.
2. Caller-supplied video/audio QA numbers, incomplete averages, and scripts that
   can emit `promote` without analyzer lineage and independent gate authority.
3. Descriptive pseudo-schemas without Draft 2020-12 validation and semantic
   cross-field checks.
4. Legacy App controls such as direct final-render or promotion toggles, raw
   workflow/node/path controls, and browser-to-ComfyUI production mutations.
5. Media-clock assumptions derived from container averages instead of decoded
   PTS/sample evidence and explicit rounding policy.
6. Audio source taxonomies that collapse origin, realization, and derivation.

The generated deprecation registries and legacy App-control crosswalk mark these
surfaces non-authoritative. Implementation must fence or replace them before a
production controller entrypoint is enabled.

## P0 gaps closed at the planning-contract level

1. One canonical frame/PTS/sample clock and typed span contract.
2. Exact per-pass video bundle selection, uncertainty, branching, and abstention.
3. Per-frame identity, ownership, pose, mask, depth, exposure, color, flow, and
   defect manifests.
4. Surface-anchored temporal texture and physical motion scorecards.
5. Immutable-parent localized span repair with handles and boundary QA.
6. Per-event audio source routing across recorded, library, procedural, neural,
   speech, and hybrid methods.
7. Dry voice identity/performance authority separated from room and mix effects.
8. Force/material/contact-aware foley and evidence-bound acoustic/spatial claims.
9. Nondestructive stem/mix/master lineage and event-class AV tolerances.
10. Controller console vs App Mode vs frontend-extension authority decision.
11. Typed application commands, queries, projections, timeline edits,
    comparisons, repair reviews, permissions, incidents, and releases.
12. Objective, critic, human, accessibility, fault, and performance test matrix.

## Remaining implementation gaps

- No production durable controller or event/projection store.
- No released controller API or operator frontend.
- No certified video model bundle or full video benchmark corpus under this plan.
- No complete frame-manifest/track/flow pipeline for every runtime engine.
- No operational multi-character physical/contact video certification.
- No unified audio event compiler and source router across all audio sources.
- No production object/stem acoustic renderer proven against geometry evidence.
- No end-to-end voice-to-viseme-to-room-to-mix-to-mux release proof.
- No calibrated full critic ensemble with held-out false-accept measurements.
- No end-to-end restart, lease-loss, unknown-submission, disk-full, or projection
  lag test through the future operator application.

## Anti-patterns explicitly rejected

- one giant ComfyUI workflow or App Mode application;
- one global engine choice for every video or audio pass;
- treating a planned engine card as eligible;
- treating high spatial detail as temporally stable detail;
- full-clip seed loops for localized failures;
- generating every sound when a qualified source/library/procedural layer is
  more faithful;
- adding room effects before dry voice acceptance;
- using container average frame rate as clock authority;
- allowing a UI, LLM, or critic to promote its own output;
- showing a green aggregate score while a blocking realism dimension fails.

## Readiness statement

Architecture and contract depth are materially strengthened. Runtime and
release readiness remain false until implementation artifacts and empirical
evidence satisfy Rows261-320 and all external gates.
