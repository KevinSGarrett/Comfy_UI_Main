# Wave64 Ultimate Modular Character-to-Multimodal Workflow Master Plan

Updated: 2026-07-16 America/Chicago

## Decision and authority

This additive program reserves Wave64 Rows149-220 for the production system that turns versioned characters and scene intent into still images, video, audio, and synchronized AV through modular ComfyUI workflows.

The production architecture is one durable external control plane coordinating many small, versioned, API-compatible workflow modules. It is not one permanent giant ComfyUI graph. ComfyUI is the execution plane. App Mode is an operator surface. The external orchestrator owns job state, pass dependencies, recovery, evidence aggregation, and deterministic policy enforcement. LLM/VLM services may propose plans and observations, but they do not bypass registries, execute arbitrary graphs, or promote artifacts.

Rows001-148, their statuses, and their accepted evidence remain unchanged. This package begins in `Planned_Autonomous_Implementation_Required`. Planning coverage is not implementation, runtime proof, artifact acceptance, engine promotion, or project completion.

## Goals

The completed system must support:

1. reusable Character Packages built independently and revised without invalidating accepted history;
2. solo and multi-character scenes with explicit identity, pose, depth, occlusion, contact, and region ownership;
3. a separate reusable pose/shot planning family consumed by image, mask, video, audio, and QA stages;
4. MaskFactory package masks and live prediction through an explicit cross-repository adapter;
5. a dynamic hyperreal multipass DAG whose passes may use different certified engine/model stacks;
6. targeted repair of the smallest failed region, span, stem, or stage without discarding accepted parents;
7. image, video, speech, Foley, ambience, music, spatial mix, lip-sync, mux, and release families;
8. a self-hosted, role-separated planner/reviewer/RAG stack behind deterministic schemas and a scoped tool gateway;
9. App Mode/operator controls that expose creative intent and evidence without exposing node IDs, raw paths, or credentials;
10. complete provenance, replay, recovery, resource, cost, QA, benchmark, promotion, rollback, and no-false-completion controls.

## Non-negotiable invariants

- `scene_id`, `shot_id`, and `take_id` are first-class lineage fields. Their producers are the Scene/Shot compiler, not downstream guesswork.
- `character_id` identifies the durable character; `character_revision` identifies an immutable Character Package revision; `character_instance_id` identifies one occurrence in one shot. Instance IDs are opaque and unbounded.
- Multi-character count is limited only by certified runtime/resource envelopes, never by alphabetic slots such as A-E.
- Every instance owns its skeleton, depth layer, silhouette, region map, target masks, protected masks, wardrobe state, contacts, and MaskFactory binding.
- MaskFactory Mode A means read-only package consumption. Mode B means live prediction/refinement drafts. Access mode and truth/authority tier are separate fields.
- A MaskFactory live prediction remains a machine draft unless its exact certificate and scope authorize more. ComfyUI never mutates MaskFactory gold.
- Every execution pass binds one exact execution stack: engine family, model revision/hash, workflow revision/hash, adapters/LoRAs/controls, runtime profile, and evidence scope.
- Hard eligibility filtering happens before quality/cost ranking. No incompatible or uncertified stack is ranked.
- Cross-engine transfer uses decoded images, crops, masks, control maps, timelines, audio events, and manifests. Latent transfer is forbidden without an exact compatibility certificate.
- Accepted artifacts are immutable parents. A failed child never rewrites or deletes an accepted parent.
- Repairs require a material hypothesis. Unexplained seed loops and silent parameter drift are forbidden.
- Target-region QA, protected-region QA, and whole-artifact regression QA are all required after localized work.
- An LLM/VLM observation cannot override failed deterministic geometry, ownership, format, lineage, mask, timing, sync, resource, or evidence gates.
- Model presence, workflow presence, planning, a smoke test, one attractive sample, or one scalar score never establishes production authority.
- `content_based_suppression=false` remains explicit. Adult/NSFW subject matter is ordinary content metadata and does not create a separate hiding, suppression, quarantine, or deprioritization path. Existing provenance and quality controls remain content-agnostic.

## Canonical products

### Character Package Revision

A Character Package is the reusable character authority, not a single image or prompt. Each immutable revision contains:

- identity core and accepted reference hashes;
- face, body morphology, proportions, distinguishing traits, view coverage, and visibility rules;
- surface profile for skin distribution, pores, marks, hair, makeup, materials, and continuity;
- wardrobe/accessory states, material metadata, ownership, and permitted variation;
- voice cards, pronunciation, language, continuity lines, and audio authority bindings;
- per-engine adapters and conditioning bindings; an adapter is never assumed portable to another engine;
- benchmark panels, failure examples, QA goals, model/workflow hashes, rights/use metadata, and status;
- revision lineage, migration rules, revocation, and rollback pointers.

Characters are built and calibrated independently. Multi-character composition consumes already accepted Character Package revisions; it does not attempt to establish multiple identities inside one shared calibration pass.

### Scene Package

The Scene Package contains world, environment, participants, wardrobe state, props, lighting, action, dialogue, audio expectations, continuity state, and requested outputs. It may contain several shots but never substitutes for a shot-specific spatial plan.

### Shot/Pose Package

The Shot/Pose Package is a separate reusable product containing:

- `scene_id`, `shot_id`, `take_id`, duration, timebase, frame range, and safe margins;
- camera, lens, framing, perspective, depth of field, lighting intent, and output dimensions;
- per-instance skeletons/keypoints, silhouettes, bboxes, depth order, visibility, occlusion, and protected regions;
- person/person, hand/object, body/support, wardrobe, prop, and environment contacts;
- keyframes, motion constraints, expected audio/vocal events, dialogue ownership, and active speaker state;
- source coordinate spaces, transforms, confidence, authority, and QA goals.

A flattened pose image may be one control artifact but is not the authoritative multi-character pose representation.

### MaskFactory Binding

The binding crosswalk maps:

`character_id + character_revision + character_instance_id + scene_id + shot_id + take_id`

to:

`MaskFactory image_id + person_index + package revision + ontology version + mask identifiers`.

It also binds image hash, dimensions, crop/resize/pad transforms, coordinate system, source provider, truth tier, certificate, and validity interval. Ownership or transform ambiguity blocks dependent passes.

### Pass DAG

The pass graph contains explicit dependencies rather than a static list. Every pass declares:

- pass intent and modality;
- required input artifact hashes and accepted parent IDs;
- target character instances, target regions/time spans/stems, and protected regions;
- exact selected execution stack and route decision;
- workflow patch values and allowlisted inputs;
- resource request, cache policy, retry budget, timeout, and cost budget;
- deterministic QA, model-review observations, whole-artifact review, and promotion gate;
- failure taxonomy, repair hypothesis requirements, fallback policy, and rollback point.

### Artifact Manifest

Every output records source package revisions, route decision, workflow/API graph hash, model and adapter hashes, prompts/configuration, seed, controls, masks, transforms, runtime identity, ComfyUI prompt/history binding, output hashes, dimensions/timing, resource telemetry, QA results, and state transition.

## Control plane

The control plane contains:

1. request/intent compiler;
2. Character, Scene, Shot/Pose, Mask, and continuity package resolver;
3. deterministic compatibility validator;
4. pass-DAG compiler;
5. per-pass Engine/Model Capability Router;
6. resource scheduler and cache manager;
7. ComfyUI HTTP/WebSocket and optional official-CLI adapter;
8. MaskFactory adapter;
9. image/video/audio/AV tool adapters;
10. deterministic QA runners;
11. independent planner and VLM reviewer services;
12. promotion/rollback policy engine;
13. append-only event store and query projections;
14. App Mode/operator API and audit UI.

For the single-node prototype, SQLite in WAL mode is the event and projection store. Every event binds run, pass, attempt, correlation, causation, and idempotency IDs plus schema/workflow/model/artifact hashes. PostgreSQL becomes the target when multiple executors or concurrent writers are introduced. Framework checkpoints may assist execution but do not replace the domain event log.

The minimum event vocabulary is: `run_created`, `plan_proposed`, `plan_validated`, `plan_rejected`, `pass_ready`, `pass_submitted`, `comfy_prompt_accepted`, `pass_progressed`, `pass_failed`, `artifact_registered`, `qa_observed`, `qa_decided`, `repair_planned`, `promotion_decided`, `pass_completed`, `run_blocked`, `run_completed`, and `run_cancelled`.

## Per-pass engine/model specialization

The router does not select one engine for an entire job. Each pass independently selects the best eligible execution stack for the exact capability and evidence scope.

### Stage 1: hard eligibility

The deterministic router rejects a candidate unless all required facts pass:

- pass intent and modality supported;
- input/output and mask/control/edit methods supported;
- exact engine-family compatibility for checkpoint, VAE, text encoder, LoRA, ControlNet, IP-Adapter, reference adapter, scheduler, and custom nodes;
- model/workflow/node/API-format/runtime hashes present and current;
- required character adapter exists for each targeted instance;
- target region is inside the model card's certified region scope;
- multi-character ownership and protected regions are unambiguous;
- resolution/duration/frame-count/hardware/precision/offload envelope is certified;
- runtime service is available and resource/cost limits fit;
- license/use and source metadata are resolved for the intended personal project use;
- benchmark and promotion evidence are current for this capability bucket.

Failure is recorded with exact eligibility reasons and missing proof. An ineligible candidate is never given a ranking score.

### Stage 2: evidence ranking

Eligible stacks are ranked only using matching benchmark buckets:

- capability-specific perceptual quality;
- identity and morphology preservation;
- pose, anatomy, contact, material, temporal, speech, Foley, or sync accuracy as appropriate;
- target-region improvement;
- protected-region and whole-artifact drift;
- mask boundary leakage and transform integrity;
- failure/OOM/crash/determinism rates;
- latency, peak VRAM/RAM, load/unload cost, storage, and monetary cost;
- cache affinity and batching/concurrency opportunity.

The champion is scoped, for example: `single visible left-hand repair / SDXL stack / 1024 crop / local 8 GiB / mask authority A`. It is never described as universally best.

### Base/first pass

The base pass selects the current global-composition champion for the scene class, character count, reference/control requirements, framing, output resolution, hardware, and cost tier. FLUX is a candidate, not a permanent hardcoded answer. If an engine cannot satisfy required multi-reference identity, pose, or count constraints, the planner may split composition, identity, and pose into separate passes rather than force one engine to do all jobs.

### Specialist pass

A specialist model that exists only in one engine is allowed through its certified stack. The pass must bind one or more target instance IDs, trusted target mask, protected masks, crop/transform, bounded denoise/strength, composite method, and three-layer QA. A failed specialist child leaves its accepted parent unchanged.

### Cross-engine bridge

The bridge exports a decoded artifact plus color space, bit depth, dimensions, crop/pad/resize transforms, alpha/masks, source/target engine IDs, source hashes, and recomposition contract. Latents, LoRAs, text encoders, VAEs, ControlNets, and adapter weights do not cross engine families unless an exact certificate proves compatibility.

## Image multipass order

The default order is dynamic but respects dependencies:

1. composition/environment/camera base;
2. per-character identity binding;
3. pose, camera, depth, count, and ownership enforcement;
4. trusted mask acquisition and transform validation;
5. silhouette/body morphology/anatomy correction;
6. contact, pressure, support, and soft-body correction;
7. skin, hair, makeup, fabric, accessories, and material surface passes;
8. face, eyes, teeth, hands, feet, nails, and other hard-detail passes;
9. lighting/shadow/reflection/coherence refinement;
10. upscale/export;
11. per-target, per-character, protected-region, and whole-frame certification.

A later failure returns to the earliest causal parent. For example, a hand-detail failure may trigger only a new hand hypothesis, while a persistent fused hand/object defect routes back to pose/contact/mask ownership rather than layering more texture passes.

## Multi-character execution

Every person has a unique scene instance with its own Character Package revision, reference set, skeleton, depth, silhouette, regional masks, and protected regions. Per-character passes may run independently when masks do not overlap. Shared contact passes require reciprocal contact declarations and ownership for all participants. Any ambiguous shared region blocks autonomous localized editing.

## MaskFactory integration

MaskFactory remains the source of mask truth and certification. Main integrates through a `MaskFactoryAdapter`:

- Mode A reads approved package assets through the installed node pack or package API. It is read-only and may support production only when the package status, hashes, ontology, transforms, and certificate satisfy the requesting pass.
- Mode B calls `/predict` or `/refine`. Outputs remain machine drafts and may support experimentation/repair proposals; their promotion authority is determined separately by exact certificates.
- Service unavailability, unknown taxonomy, wrong person index, image-hash mismatch, stale package revision, or transform mismatch blocks the dependent pass without preventing unrelated work.
- Main never writes into gold packages and never relabels a live draft as gold.

Current integration evidence at plan creation: the MaskFactory ComfyUI node pack and its three reference workflows are installed, the configured API is `127.0.0.1:8765`, and the live service is not currently reachable. MaskFactory development remains active and completion-gated.

## Video, audio, and AV

Video consumes accepted image/keyframe artifacts, Character Packages, and Shot/Pose Packages. It emits frame/timeline manifests and temporal QA. Only failed spans are repaired unless the failure is causal at the keyframe, pose, identity, or camera level.

Audio consumes voice bindings, dialogue, visual event timelines, contact/force events, environment/acoustics, and duration contracts. Dialogue, nonverbal vocalization, Foley, ambience, music, enhancement, spatial mix, and master remain replaceable stems.

AV assembly consumes accepted video and accepted audio stems. It aligns samples/frames/PTS, mixes, loudness-checks, muxes, and performs full-duration review. A joint AV engine is a candidate lane, not permission to skip independent video, audio, speech, Foley, sync, and identity gates.

## Self-hosted LLM/VLM topology

Roles are separated:

- planner: proposes structured plan and repair hypotheses;
- deterministic validator: resolves every registry ID and state transition;
- tool gateway: owns allowlisted credentials and execution;
- VLM reviewer: emits observations tied to artifact/region/frame IDs;
- retrieval service: resolves Plan, registry, evidence, and model documentation;
- policy engine: makes promotion/rollback decisions from deterministic gates and authorized review evidence.

The local RTX 5060 Laptop GPU has about 8 GiB VRAM and 31.3 GiB system RAM. It is the development/fallback node and must not host a production planner/VLM concurrently with heavy ComfyUI generation. Production candidates are evaluated per role on appropriate larger GPU tiers. Transport compatibility, structured output, or nominal context length is not selection evidence; exact model/runtime/template/parser/quantization/context combinations must pass the project benchmark.

## App Mode/operator surface

One canonical control schema powers:

- Character Library and revision comparison;
- Scene and Shot/Pose authoring;
- participant/instance/wardrobe/voice binding;
- engine policy (`auto`, preferred, forced-for-diagnostic) with eligibility explanation;
- quality/cost/runtime budget;
- pass DAG and targeted repair controls;
- MaskFactory package/live-draft status;
- queue, events, resource state, and cancellation;
- QA observations, comparisons, approvals, blockers, and results;
- provenance/export/replay.

App Mode never becomes the autonomous brain. It hides node IDs, raw paths, credentials, and mutable engine internals from normal operation.

## Implementation order and acceptance

1. Freeze canonical v1 schemas, IDs, state machine, and registries.
2. Parameterize Character 1 experiments into the first Character Package publisher without rerunning accepted work.
3. Implement Shot/Pose Package and single-/two-character ownership fixtures.
4. Implement Engine/Model Capability Graph, route decisions, and bridge/specialist contracts.
5. Implement MaskFactory Mode A adapter; keep Mode B draft-only until service/certificates pass.
6. Replace the static pass-list compiler and seed-default retry with a resumable event-driven DAG and hypothesis repair engine.
7. Deliver one complete single-character image proof.
8. Deliver one complete two-character image/contact proof.
9. Connect approved keyframes to video, then pass a failed-span repair proof.
10. Connect visual events to speech/Foley/ambience/music and accepted stems to AV assembly.
11. Build the canonical App Mode/operator surface.
12. Benchmark and activate role-separated self-hosted planner/reviewer services.
13. Complete multi-sample, multi-scene, multi-character, temporal, audio, recovery, security, performance, and release certification.

Each phase requires contracts, implementation hashes, tests, real runtime output when applicable, direct QA, evidence, and an explicit status. Later phases cannot convert an upstream blocker into implied completion.

## References and external dependency

- Existing local architecture: `Plan/02_TARGET_ARCHITECTURE/MODULAR_CHARACTER_TO_MULTIMODAL_MEDIA_ORCHESTRATION_ARCHITECTURE.md`
- Existing App Mode design: `Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md`
- Existing workflow decision: `Plan/02_TARGET_ARCHITECTURE/WORKFLOW_MODULE_DECISION.md`
- Existing image/video/audio blueprints: `Plan/03_IMAGE_SYSTEM`, `Plan/04_VIDEO_GIF_SYSTEM`, `Plan/05_AUDIO_SYSTEM`
- Existing scorecard: `Plan/06_QA_TESTING/WAVE64_MULTIMODAL_SCORECARD_GATE_SPEC.md`
- External MaskFactory contract: `C:\Comfy_UI_Main_Masking\Plan\13_COMFYUI_INTEGRATION.md`
- MaskFactory source task: `019f4cfc-60c3-7500-8626-261dcf70db5d`
- Main implementation task: `019f422f-88b1-7382-872b-21de2089e983`
