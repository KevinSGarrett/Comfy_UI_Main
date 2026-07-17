# Pass-Level Engine and Model Routing QA Protocol

Updated: 2026-07-16 America/Chicago

## Purpose

This protocol proves that every first, intermediate, specialist, repair, video, audio, and AV pass uses a legal and evidence-backed engine/model stack.

## Required route evidence

Every route decision records:

- route request and schema version;
- pass, modality, intent, targets, protected scope, inputs, masks/controls, outputs, quality/resource/cost budgets, and required evidence scope;
- every candidate stack considered;
- hard-eligibility result and machine-readable rejection reasons per candidate;
- benchmark bucket and metric evidence for every eligible candidate;
- ranking weights/policy revision, selected stack, fallback order, and selection explanation;
- exact engine family, model revision/hash, workflow/API hash, VAE, text encoder, scheduler/sampler, adapters/LoRAs/ControlNets/reference controls, custom-node lock, runtime/precision/offload profile, and certificate IDs;
- expiry/revalidation conditions and whether operator override was requested.

## Hard rejection tests

Reject before ranking when any of these are unresolved or false:

1. modality/pass capability;
2. engine-family compatibility of every model-side component;
3. input/output media and edit/control method;
4. target character adapter and region/span coverage;
5. mask truth tier, ownership, coordinate transform, and certificate;
6. multi-character count/ownership/contact scope;
7. resolution, duration, frame count, precision, VRAM/RAM, disk, runtime, node, and API-format envelope;
8. exact model/workflow/runtime hashes and current benchmark scope;
9. service availability and allowed cost/license/use metadata;
10. a legal bridge from every accepted parent to the candidate stack.

An ineligible candidate receives no quality score. Missing data is ineligible, not zero-score eligible.

## Ranking tests

Ranking must be deterministic for identical inputs and registry snapshots. Metrics must match the requested bucket. Verify quality, target improvement, identity/morphology/pose/contact preservation, protected/whole-artifact drift, failure/OOM rate, latency, memory, model-load cost, cache affinity, and monetary cost. Persist both normalized components and raw evidence references.

## Substitution and override tests

- Removing or disabling the selected stack must produce a new route decision, not silent fallback.
- An operator preference may influence ranking only among eligible stacks.
- A forced diagnostic route is clearly marked non-promotable unless it independently satisfies normal evidence.
- A planner-provided engine/model name that is not an exact registry ID is rejected.
- A model marketed for a body part or capability is not eligible until the exact stack has a scoped card and benchmark certificate.

## Cross-engine tests

Cross-family tests verify decoded media hash, color space/sample format, bit depth, dimensions/duration, alpha/channel semantics, crop/resize/pad or time transforms, target/protected masks, source/target stack IDs, and recomposition contract. Reprojected masks and artifacts must align with the original coordinate system. Latent transfer fails unless an exact producer-consumer compatibility certificate covers both stacks and every latent-affecting component.

## Specialist-pass tests

Use fixtures for face, hand/body-part, hair, skin, fabric/accessory, contact, video span, speech span, Foley event, and AV sync repair. Each fixture proves:

- only declared targets are writable;
- protected masks/spans remain stable;
- multiple characters cannot exchange identity or ownership;
- boundary/context and recomposition are coherent;
- target improvement passes;
- whole-artifact regression passes;
- failure preserves the accepted parent and produces a causal repair hypothesis.

## Property and failure-injection tests

Test unbounded opaque instance IDs, candidate-order independence, deterministic tie-breaking, acyclic DAGs, idempotent resubmission, stale certificate/model/workflow/node hashes, wrong person index, transform mismatch, service loss, WebSocket disconnect/history recovery, OOM, corrupted artifact, partial AV output, concurrent non-overlapping passes, and conflicting write masks.

## Acceptance

The routing layer passes only when schema validation, unit/property tests, golden fixtures, failure injection, exact-stack replay, resource observations, and at least one real runtime proof for each promoted capability bucket are present. Rows and registry entries remain planned/candidate when only static validation exists.
