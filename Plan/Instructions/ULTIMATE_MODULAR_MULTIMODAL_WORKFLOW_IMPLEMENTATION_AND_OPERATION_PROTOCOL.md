# Ultimate Modular Multimodal Workflow Implementation and Operation Protocol

Updated: 2026-07-16 America/Chicago

## Purpose

This protocol governs Wave64 Rows149-220. It converts the character-to-image/video/audio/AV architecture into an executable, resumable, evidence-backed program while preserving accepted work in Rows001-148 and the active FLUX.2 and MaskFactory tasks.

## Authority order

1. current explicit user objective;
2. project intake, security, no-loop, and truth-authority rules;
3. this protocol and the Wave64 master plan;
4. canonical schemas and registries;
5. accepted runtime evidence and scoped benchmark certificates;
6. planner or reviewer proposals.

An LLM proposal never outranks a failed deterministic contract, compatibility, ownership, geometry, timing, resource, or promotion gate.

## Required package flow

Every autonomous job follows this package chain:

request -> character revisions -> scene package -> shot/pose package -> MaskFactory bindings -> pass DAG -> per-pass route decisions -> attempts -> artifact manifests -> QA decisions -> promotion or repair events.

No downstream component may infer a missing durable identifier from filenames, prompt text, node IDs, or visual similarity. Scene, shot, take, character revision, character instance, mask, pass, route, attempt, and artifact IDs must be explicit.

## Planning procedure

For each requested output, the planner must:

1. resolve immutable Character Package revisions and requested wardrobe/voice states;
2. compile scene, shot, camera, pose, depth, occlusion, contact, event, and continuity intent;
3. assign an opaque character_instance_id to every occurrence;
4. acquire or request masks with explicit person ownership and coordinate transforms;
5. construct a dependency DAG at the smallest independently verifiable pass granularity;
6. declare target and protected scope, required capabilities, acceptance goals, budgets, and fallback policy per pass;
7. submit every route request to the deterministic capability router;
8. reject the plan if any required identifier, authority, transform, dependency, execution stack, or evidence scope is unresolved.

The planner may propose alternatives. It cannot invent registry records, silently alter protected scope, or convert a draft mask/model/workflow into production authority.

## Route and execution procedure

For each ready pass:

1. hard-filter execution stacks by exact modality, capability, engine-family compatibility, input/output contract, target scope, character adapters, mask authority, workflow API compatibility, model/node/runtime hashes, resource envelope, and benchmark currency;
2. rank only eligible stacks within the matching capability bucket;
3. persist the full candidate set, rejection reasons, scoring inputs, selected stack, selection reason, and fallback order;
4. materialize an allowlisted API-format workflow from the selected workflow revision;
5. bind all inputs by content hash and all mutable controls by explicit value;
6. connect ComfyUI WebSocket telemetry before POST /prompt, correlate by prompt_id, and reconcile /history after completion or reconnect;
7. register every output, log, history record, resource observation, and failure as append-only events;
8. run target, protected, ownership/identity, and whole-artifact gates before advancing.

No silent engine/model/workflow substitution is permitted. If the selected stack becomes unavailable, create a new route decision and attempt with an explicit reason.

## First-pass and specialist-pass rules

The first image pass uses the certified global-composition champion for the exact scene bucket. FLUX is a candidate family, not a fixed policy. Identity, pose, contact, typography, anatomy, skin, hair, clothing, accessories, or other specialist needs may route to different certified engines on later passes.

A specialist pass must bind:

- one accepted parent artifact;
- one or more target character_instance_id values;
- target region, frame span, audio span, or stem;
- trusted target mask or equivalent time-domain selector;
- protected regions/instances/spans;
- decoded bridge and crop/resize/pad transforms when crossing engines;
- exact denoise/strength and composite policy;
- bounded attempt and cost budget;
- target-improvement, preservation, seam/coherence, identity/ownership, and whole-artifact gates.

Specialist failure leaves the accepted parent unchanged. A successful local score does not permit promotion if whole-artifact regression fails.

## Repair procedure

Every retry must state a material hypothesis tied to a classified failure. Valid changes include correcting mask ownership/transforms, returning to an earlier causal parent, selecting a differently certified stack, changing control evidence, changing crop/context, or changing a bounded parameter justified by the failure.

Seed-only iteration is forbidden as a repair policy. It is allowed only in an explicitly declared stochastic-robustness benchmark. Repeated failure with no new hypothesis terminates the pass with an exact blocker and preserves all accepted ancestors.

## Multi-character rules

- Character calibration and package publication happen independently.
- Every shot instance has separate identity, skeleton, depth, visibility, silhouette, masks, protected regions, wardrobe, and contacts.
- Independent localized passes may run concurrently only when write masks and protected scopes cannot conflict.
- Shared contact edits require reciprocal declarations and deterministic ownership for every participant and object.
- An ambiguous overlap, person index, mask transform, or identity binding blocks only dependent passes.

## MaskFactory rules

- Mode A is read-only consumption of package masks. Production use depends on package truth tier and certificate, not the access-mode name.
- Mode B is live prediction/refinement. Its output is a machine draft unless an exact certificate grants stronger scoped authority.
- The adapter validates package revision, image hash, dimensions, ontology, person index, source coordinates, transforms, mask type, provider, truth tier, certificate, and validity.
- Main never edits MaskFactory gold packages or relabels drafts as gold.
- MaskFactory unavailability blocks only passes that require it; unrelated DAG branches may continue.

## Video, audio, and AV rules

Video passes consume accepted keyframes and the same Shot/Pose Package used by image work. Repair is span-local unless the cause is an upstream keyframe, pose, camera, ownership, or identity failure.

Audio passes consume dialogue ownership, voice bindings, visual/contact event timelines, acoustics, and duration. Speech, nonverbal vocalization, Foley, ambience, music, enhancement, spatial mix, and master are replaceable stems with separate provenance and QA.

AV assembly accepts only promoted video and audio inputs. It validates timebase, PTS, sample/frame alignment, lip-sync/event sync, clipping/loudness, mux integrity, duration, and full-playback quality. Joint AV engines remain independently gated.

## Runtime and resource rules

- Plan loading, execution, review, and promotion are separate authority roles even if initially deployed on one machine.
- The local 8 GiB development GPU is not scheduled for a heavy generation engine and production planner/VLM at the same time.
- The scheduler accounts for model residency, load/unload cost, peak VRAM/RAM, disk/cache needs, timeout, concurrency, and monetary budget.
- OOM or service failure is classified as runtime failure, never visual-quality failure.
- Cancellation and restart are idempotent; history is reconciled before resubmission.

## Completion rule

Planning documents, schemas, registry entries, installed files, workflow validation, smoke tests, or attractive samples do not complete a runtime row. Each row requires its declared implementation, tests, runtime proof where applicable, direct QA, artifact hashes, evidence, and explicit pass or exact blocker. No package-level completion may be inferred from a subset of rows.

## Main-task preservation

All files named in the Wave64 main-session handoff are additive reserved work for Rows149-220. The main task must preserve them as intentional untracked/dirty artifacts until reviewed and integrated. It must not rewrite Rows001-148 or active FLUX.2/MaskFactory evidence to claim this program complete.
