# Ultimate Modular Multimodal Workflow QA and Promotion Protocol

Updated: 2026-07-16 America/Chicago

## Decision model

Promotion is a deterministic decision over scoped evidence, not an LLM verdict and not one aggregate realism score. Every artifact is evaluated against the job, pass, character, shot, mask, timing, engine-stack, and benchmark revisions that produced it.

## Gate layers

### Contract and lineage

- schemas validate with no unresolved IDs;
- source artifacts and accepted parents match content hashes;
- scene/shot/take, character revisions/instances, masks, route, attempt, workflow, model, and runtime lineage are complete;
- coordinate/time transforms are invertible and verified;
- no output overwrote an accepted parent.

### Technical integrity

- output exists, decodes, has expected media type, dimensions, color/audio format, duration, timebase, and hash;
- ComfyUI prompt/history or external engine job evidence is bound to the attempt;
- no unresolved node, model, service, OOM, truncation, NaN, mux, clipping, or corruption fault exists;
- resource and cost envelopes were respected or explicitly rejected before promotion.

### Target result

Measure only criteria relevant to the declared pass: composition, identity, pose, anatomy, contact, surface/material, typography, temporal motion, speech, Foley, music, sync, or export. The target must improve against the accepted parent or meet an absolute gate.

### Protected-scope preservation

Measure protected characters, regions, frames, spans, stems, dialogue, wardrobe, props, background, color, lighting, camera, identity, morphology, timing, and continuity. Any unauthorized change fails the pass.

### Whole-artifact regression

Review the complete image, complete relevant video span plus boundaries, complete audio program/stems, or full AV playback. A localized improvement fails if it introduces a new global defect or cumulative drift.

## Required scorecard dimensions

Use separate recorded dimensions, thresholds, and evidence rather than collapsing them into 98 percent realism:

- identity similarity and distinguishing-trait continuity;
- body morphology and proportion continuity;
- camera/framing/composition completeness;
- pose/keypoint/depth/occlusion/contact error;
- mask ownership, IoU where gold exists, boundary leakage, and transform integrity;
- anatomy and regional fidelity;
- skin, hair, fabric, accessory, lighting, shadow, and material coherence;
- protected-region and whole-artifact drift;
- temporal identity, structure, motion, flicker, boundary, and shot continuity;
- speech intelligibility, speaker/voice consistency, pronunciation, prosody, and artifact rate;
- Foley/event alignment, ambience/acoustics, music intent, spatial mix, loudness, and clipping;
- lip-sync/event-sync, PTS/sample/frame alignment, mux integrity, and full-duration playback;
- runtime reliability, repeatability, latency, VRAM/RAM, storage, and cost.

Each dimension declares method, threshold, sample set, confidence/uncertainty where relevant, and whether it is deterministic, model-observed, or independently reviewed.

## Reviewer authority

Deterministic validators decide format, hash, graph, registry, geometry, ownership, transform, timing, resource, and threshold facts. A VLM or audio-language reviewer emits structured observations linked to regions, frames, spans, and artifact IDs. Reviewer disagreement is retained; the policy engine applies declared rules. A reviewer cannot self-promote its own generation.

## Promotion states

- draft: output exists but required gates are incomplete;
- candidate: technical and lineage gates pass, full QA pending;
- accepted_parent: all pass gates pass and the artifact may parent later work;
- promoted_scope: accepted for one declared capability/scene bucket;
- released: all job and release gates pass;
- rejected: evidence proves a failed gate;
- blocked: required authority, service, resource, or evidence is unavailable;
- revoked: previously accepted authority was invalidated with an explicit reason and replacement/rollback pointer.

No state is inferred from a filename, directory, UI badge, or model reputation.

## Benchmark and champion rules

Benchmarks are bucketed by modality, pass intent, target region/span, character count, visibility/occlusion/contact class, resolution/duration, mask authority, hardware/runtime, and quality/cost tier. The registry may name a champion only inside the tested bucket. A new model version, workflow hash, node version, adapter stack, quantization, runtime profile, or material benchmark change creates a new candidate scope.

At minimum, comparison includes multiple seeds/samples and more than one scene/character where the intended scope is not character-specific. Failure rate, outliers, cumulative drift, and resource behavior are reported with quality. One attractive sample cannot promote a stack.

### Initial milestone sample floors

These counts prove milestone reachability only. A production reliability claim must predeclare the maximum serious-failure rate and pass an appropriate one-sided 95 percent confidence bound; sparse buckets abstain.

- router: at least 100 valid and 100 adversarial route fixtures with identical decisions from the same registry snapshot and zero incompatible selections;
- single-character image: at least 30 cases across six or more shot, lighting, visibility, mask, and specialist buckets;
- two-character image/contact: at least 24 cases across three or more character pairs and four separation, occlusion, or contact buckets;
- video: at least 12 clips spanning one/two characters, low/high motion, static/moving camera, and occlusion/contact, including a failed-span repair;
- speech: at least 30 held-out utterances; Foley/event audio: at least 30 held-out events; integrated audio: at least four acoustic buckets;
- AV: at least 12 complete clips with monotonic timestamps, full decode/playback, and frame/sample alignment;
- App Mode: at least 20 scripted operator journeys including reconnect, cancel, resume, blocker, comparison, and rollback;
- planner: at least 100 held-out requests; reviewer: at least 200 adjudicated defect panels; tool gateway: at least 100 adversarial authorization/path/injection cases; autonomy: at least 30 complete shadow jobs before activation.

## Test pyramid

- Static/property: validate every schema, reference, ID, hash, compatibility decision, legal state transition, DAG edge/cycle, coordinate/time transform, and policy rule. Generate at least 10,000 DAG/route/transform cases before release.
- Unit: critical router, promotion, lineage, event, scheduler, and rollback modules target at least 95 percent branch coverage and 85 percent mutation score; every failure code has a direct test.
- Contract: cover every producer/consumer pair, ComfyUI adapter, MaskFactory Mode A/B, media adapter, App API, and supported schema migration; stale/newer unsupported revisions must refuse safely.
- Integration: use real SQLite/content-addressed storage, fake then live ComfyUI, Mode A packages, WebSocket/history reconnect, admission control, cache corruption, cancellation, timeout, OOM, service loss, and duplicate delivery.
- End-to-end: execute the phase matrices, forced failures, accepted-parent immutability, promotion refusal, rollback, and clean-start recovery.
- Perceptual/benchmark: freeze inputs, use multiple seeds where stochastic, report outliers/failure rates, perform blinded comparisons where useful, and always review the whole artifact.

## Local 8 GiB resource admission

The observed development GPU has 8,151 MiB VRAM. A local stack becomes eligible only after at least ten measured cold/warm trials and:

measured maximum VRAM + 1,024 MiB is less than or equal to 8,151 MiB.

The initial local admission ceiling is therefore 7,127 MiB. Keep system RAM below 80 percent unless a separate measured profile certifies more. Permit one GPU-heavy lease at a time. A GPU planner/VLM cannot share the local GPU with heavy ComfyUI or MaskFactory generation. A stack without this certificate routes to a larger certified envelope or blocks.

OOM immediately suspends that runtime envelope. One new route may choose a materially different certified offload, quantized, lower-resolution, or larger-GPU stack. An unchanged OOM retry is forbidden. Cache keys include exact packages, parents, transforms, stack/workflow/runtime/configuration hashes, seed when relevant, and replay policy. Accepted parents, benchmark fixtures, and release evidence are pinned and cannot be evicted as the only copy.

## Recovery and rollback matrix

Inject recovery at: before submission, after POST /prompt, during execution, after output creation, after artifact registration, during QA, immediately before promotion, and immediately after the promotion event commits.

- Unknown submission: reconcile queue/history by idempotency and prompt correlation before any resubmission.
- Output exists but event is missing: hash and register the existing output; do not regenerate.
- QA incomplete: resume QA without rerunning generation.
- Child failure: quarantine/reject the child and retain every accepted parent unchanged.
- Revoked mask/model/workflow/node/runtime certificate: block new use and dependent cache reuse while preserving historical evidence.
- Service loss: block only dependent branches.
- OOM: classify as runtime failure, unload safely, and issue a new certified route decision.
- Corrupt cache: reject the hash mismatch and rehydrate from canonical storage.
- Rollback: append a rollback event and restore the prior registry pointer; never rewrite event history.

Chaos acceptance requires zero duplicate promotions, zero accepted-parent mutations, zero lost terminal events, and projections identical to a clean replay.

## Atomic no-false-promotion transaction

Promotion atomically verifies:

1. complete schemas, references, and immutable lineage;
2. accepted parent hashes;
3. exact registry snapshot and a hard-eligible route decision;
4. exact model, component, workflow, node, runtime, and environment hashes;
5. required artifacts exist and decode;
6. deterministic target, protected-scope, identity/ownership, seam/sync, technical, and whole-artifact gates pass;
7. required review evidence is authorized and linked to exact regions/frames/spans;
8. the capability-bucket benchmark certificate is current;
9. no required blocker, revocation, or resource violation remains;
10. the policy decision and rollback pointer are signed and committed with the promotion event.

Negative fixtures for stale masks, wrong person index, transform mismatch, missing history, wrong model hash, attractive local result with failed whole-artifact QA, reviewer pass against a deterministic failure, OOM, and unapproved fallback must all reject promotion.

## Repair gate

A failed attempt records taxonomy, evidence, earliest plausible causal pass, and next material hypothesis. The next attempt must differ in a way capable of addressing that cause. Repeating equivalent attempts or incrementing seeds without a declared robustness experiment is a no-loop failure.

## Release evidence bundle

The release bundle contains validated package manifests, event-log digest, route decisions, exact stack cards, workflow/API hashes, input/output hashes, ComfyUI history or external job proof, deterministic metrics, structured reviewer observations, comparisons, full-artifact reviews, resource/cost telemetry, unresolved limitations, rollback pointers, and a signed promotion decision.

Planning coverage for Rows149-220 is accepted only as planning coverage. Runtime and release status remain planned until row-specific evidence satisfies this protocol.
