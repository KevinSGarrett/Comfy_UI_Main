# Wave 07 Request-to-Structured-Scene-Plan Pipeline

## Pipeline overview

The Scene Director converts a request into a plan through deterministic stages.

```text
1. request intake
2. normalization
3. intent classification
4. ambiguity resolution
5. scene graph construction
6. camera/framing construction
7. environment/material construction
8. action/contact/body/motion construction
9. mask goal construction
10. model-selection construction
11. engine-route construction
12. pass-plan construction
13. QA goal construction
14. promotion/evidence requirements
15. validation
```

## Stage 1 — Request intake

Input is the raw request plus any available controls from App Mode or a CLI/API job.

Required fields:

- request ID
- raw user request
- target output, if known
- reference assets, if any
- engine preferences, if any
- constraints
- negative constraints
- project context

## Stage 2 — Normalization

The Director rewrites the request into implementation-friendly form.

Example:

```text
Raw:
"make it look more realistic and keep the whole body in frame"

Normalized:
"Generate or refine an image with hyperreal material detail, full-body framing, visible head and feet, realistic anatomy, and no global background change."
```

The normalized request should remove ambiguity without adding unsupported details.

## Stage 3 — Intent classification

Classify the request into one or more intent IDs from:

- image_single_hyperreal_character
- image_multi_character_interaction
- body_shape_or_anatomy_correction
- soft_body_contact_deformation
- environment_camera_framing
- gif_or_video_scene
- audio_or_av_sync
- model_selection_or_registry_update

One primary intent is required. Secondary intents are allowed.

## Stage 4 — Ambiguity resolution

The Director should not stall on every missing detail. It should make best-effort defaults and record assumptions.

Ask a follow-up only when:

- a required reference file is missing
- requested output format is impossible to infer
- a blocking contradiction exists

Otherwise:

- choose defaults
- record them in `assumptions[]`
- continue with a usable plan

## Stage 5 — Scene graph

The scene graph defines:

- characters
- environment
- props
- actions
- relationships
- depth order
- occlusion
- material context
- negative constraints

The scene graph is the anchor for camera, masks, pass plan, and QA.

## Stage 6 — Camera/framing

Camera plan must define:

- shot type
- full-body/half-body/close-up requirement
- subject count visible
- crop rules
- lens look
- camera height
- camera distance
- camera angle
- zoom/focal length hint
- depth of field
- safe margins
- occlusion warnings

QA must be derived from this plan.

## Stage 7 — Environment/material

The Director must define enough environment context to avoid floating subjects, wrong scale, and mismatched lighting.

Required environment concepts:

- location type
- surface/floor/wall context
- lighting source
- material list
- scale constraints
- background protection rules

## Stage 8 — Action/contact/body/motion

For interactions or physical detail, the Director must produce explicit graph data instead of relying on prompt text alone.

Examples:

- source entity
- source region
- target entity
- target region
- pressure/intensity
- contact zone
- occlusion/shadow requirement
- deformation target
- motion phase
- expected rebound/settle behavior for video/GIF

## Stage 9 — Mask goals

The Director creates planned masks before detail passes.

Mask categories:

- macro
- major
- minor
- micro
- nano
- contact
- protect

Every regional pass must have a mask or a reason why no mask is needed.

## Stage 10 — Model selection

The Director uses:

- Civitai metadata registry
- model storage manifest
- engine registry
- asset compatibility registry
- rejected/superseded status
- QA history

The Director proposes model candidates. The router/validator confirms them.

## Stage 11 — Engine route

The Director proposes primary/fallback engines. The router enforces validity.

Common routes:

- Flux2 Dev for planned high-prompt-following base generation after runtime proof.
- SDXL/RealVisXL for existing LoRA/detail ecosystem.
- Flux1 for current Flux family fallback.
- Z-Image for proxy/experimental image lane.
- Pony/Pony-SDXL for specialty compatibility only.
- Wan/Hunyuan/LTX/LTX2 for video lanes.
- Audio/foley/TTS/room systems for audio lanes.

## Stage 12 — Pass plan

Each pass must include:

- pass ID
- pass type
- engine ID
- workflow module ID
- model IDs
- mask IDs
- inputs
- outputs
- QA goals
- promotion gate
- runtime proof requirement

## Stage 13 — QA goals

QA is not an afterthought. It is compiled with the plan.

Every plan must include:

- basic file QA
- scene intent QA
- camera/framing QA
- anatomy QA
- engine compatibility QA
- mask QA when regional passes exist
- contact QA when interactions exist
- temporal QA when video/GIF exists
- audio/AV sync QA when audio exists
- promotion QA

## Stage 14 — Evidence requirements

The Director declares the evidence required before promotion.

Examples:

- scene plan JSON
- pass plan JSON
- engine route JSON
- model-selection manifest
- mask overlay images
- before/after crops
- output SHA256
- runtime logs
- ComfyUI history ID
- object_info snapshot
- EC2 stop confirmation when EC2 is used

## Stage 15 — Validation

The plan is validated before execution.

Static validation checks:

- required fields exist
- JSON parses
- engine IDs exist
- model IDs exist or are explicitly marked pending
- no rejected model selected
- no wrong-engine LoRA mix
- pass plan order is valid
- QA goals exist
- promotion blockers are declared
