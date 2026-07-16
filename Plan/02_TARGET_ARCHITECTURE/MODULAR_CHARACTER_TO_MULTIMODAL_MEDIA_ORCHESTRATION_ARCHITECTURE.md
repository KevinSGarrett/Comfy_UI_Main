# Modular Character-To-Multimodal Media Orchestration Architecture

Updated: 2026-07-16 America/Chicago

## Decision

Production uses separate, versioned ComfyUI API workflows coordinated by one external autonomous orchestrator. The project must not collapse character construction, still-image generation, image repair, video generation, audio generation, and AV assembly into one giant ComfyUI graph.

The large Main Flow remains an operator/reference and compatibility surface. It is not the production execution graph unless every modular contract is synchronized into it and the combined graph independently passes runtime QA.

## Persistent Products

The system passes immutable, hash-bound products between workflows:

1. `Character Package`
   - character ID and revision;
   - approved face, body, hair, wardrobe, material, and voice references;
   - locked and variable traits;
   - reference hashes, rights/license metadata, and authority state;
   - engine-specific conditioning bindings without treating one engine's adapter as portable to another.
2. `Scene Package`
   - environment, participants, wardrobe state, props, camera, lighting, action, dialogue, and continuity state.
3. `Shot Plan`
   - shot ID, duration, framing, pose, motion, keyframes, contacts, expected audio events, and acceptance gates.
4. `Pass Plan`
   - ordered workflow invocations, inputs, engine routes, patch values, dependencies, budgets, QA gates, and retry limits.
5. `Artifact Manifest`
   - source package revisions, workflow and model hashes, prompt/configuration, seed, output hash, dimensions or timing, runtime logs, and QA decision.

A character is not a single image. It is a versioned Character Package that can be consumed repeatedly by image, video, audio, and AV workflows.

## Workflow Families

### Character Package Workflows

Character intake and construction workflows organize references, validate identity coverage, generate optional candidates through an image lane, compare candidates to authority references, and publish a new Character Package revision only after acceptance.

These workflows do not directly become the video or audio workflow. They create the stable inputs those workflows consume.

### Image Workflows

Image production normally executes a pass graph such as:

1. composition/base generation;
2. identity and reference conditioning;
3. pose, depth, camera, and control guidance;
4. mask or region preparation when trusted authority exists;
5. regional anatomy, contact, wardrobe, or surface repair;
6. low-denoise refinement through explicit image bridges;
7. upscale/export;
8. whole-image and targeted QA.

Each engine family has its own workflow and model objects. FLUX.1, FLUX.2, SDXL, video, and audio objects are never directly mixed. Cross-engine refinement transfers a decoded image plus a manifest through an explicit bridge.

### Video Workflows

Video workflows consume an approved character-aware image or keyframe set, Character Package revision, Scene Package, and Shot Plan. They produce frame/timeline manifests, motion output, and temporal QA. Failed spans are repaired through bounded frame/span workflows; the accepted source is not regenerated merely because a downstream span failed.

### Audio Workflows

Audio workflows consume the Character Package voice binding, dialogue plan, visual action/event timeline, environment/acoustic state, and duration contract. Dialogue, Foley, ambience, music/reaction, and spatial-mix workflows remain separate so one failed stem can be replaced without regenerating the image or video.

### AV Assembly Workflows

AV assembly consumes an approved video artifact and approved audio stems. It performs synchronization, mixing, loudness/conformance, muxing, technical QA, full-duration review, and release packaging. It does not generate character identity or silently repair rejected upstream media.

## Multiple Passes

Multiple passes are nodes in an external pass graph, not duplicated branches inside one permanent ComfyUI canvas.

Every pass records:

- `pass_id`, `attempt_id`, and parent artifact hashes;
- exact workflow, model, adapter, prompt/configuration, seed, and input hashes;
- target regions or time spans;
- protected regions or continuity constraints;
- machine and perceptual QA results;
- decision: accept, targeted repair, fallback, block, or promote.

An accepted output becomes the immutable input to the next pass. A failed regional or temporal pass reruns only the smallest affected workflow when a materially different correction exists. The orchestrator never loops seeds or parameters without a declared new hypothesis and retry budget.

## Autonomous Execution Loop

The external controller performs this state machine:

1. Compile the user request into Character, Scene, Shot, and Pass packages.
2. Resolve exact model and workflow dependencies from registries; reuse exact hashes before acquisition.
3. Select the smallest eligible workflow lane and validate compatibility.
4. Patch a versioned ComfyUI API workflow with package IDs and runtime values.
5. Run static validation, then local runtime or an explicitly gated EC2 runtime.
6. Collect ComfyUI history, outputs, logs, and hashes into an Artifact Manifest.
7. Run deterministic QA and Codex-owned visual/audio review where required.
8. Accept and advance, run one targeted repair/fallback, or record an exact blocker.
9. Assemble downstream video, audio, and AV packages only from accepted upstream artifacts.
10. Update Items/Tracker minimally after the implementation or runtime result exists.

Routine execution is autonomous. Human action is limited to irreducible authority such as subjective listening, rights/access approval, or explicitly user-owned creative acceptance. Missing human authority blocks only dependent promotion; it does not stop unrelated implementation.

## Example Character-To-AV Run

```text
Character Package C01 r3
  -> Scene Package S014
  -> image/base/flux2-dev r1
  -> image/identity-reference r2
  -> image/regional-repair r4
  -> approved keyframe K014
  -> video/primary-shot r2
  -> video/span-repair r1
  -> approved video V014

Character Package C01 r3 voice binding
  + V014 event timeline
  -> audio/dialogue r2
  -> audio/foley r1
  -> audio/ambience r1
  -> audio/spatial-mix r3

V014 + approved audio stems
  -> av/sync-mix-mux r2
  -> multimodal QA
  -> release candidate
```

The exact number of passes is selected from the request and QA results. Unneeded workflows are skipped.

## FLUX.2 Placement

FLUX.2 is a separate image-engine family and the next bounded image modernization delivery. The first delivery must:

1. Resolve exact official FLUX.2 Dev and Klein variants, licenses/access terms, versions, filenames, sources, sizes, and SHA-256 values.
2. Reuse exact local, legacy, or S3 bytes when hashes match; otherwise acquire and register the diffusion model, matching text encoder, and FLUX.2 VAE.
3. Build dedicated text-to-image and reference/edit API workflows plus runtime requirements and smoke requests.
4. Wire FLUX.2 into the engine router with fail-closed fallback to proven image lanes.
5. Run local or EC2 object-info, loader, text-to-image, and reference/edit smoke proofs.
6. Perform direct visual A/B QA against FLUX.1 and RealVisXL using scope-matched prompts and references.
7. Modernize only compatible downstream workflows through decoded-image bridges.

FLUX.1 checkpoints, LoRAs, ControlNets, text encoders, and VAEs are not FLUX.2 assets. They remain in FLUX.1 workflows unless an exact asset has explicit FLUX.2 compatibility proof. Prompt intent, reference images, masks/control images where supported, manifests, QA tooling, and decoded outputs may be reused through declared contracts.

Until these gates pass, FLUX.2 remains unproven: no workflow-complete, runtime-proven, artifact-present, QA-passed, or production-certified claim is allowed.
