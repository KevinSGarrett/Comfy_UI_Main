# Wave 07 — LLM Scene Director Architecture

## Purpose

The LLM Scene Director is the planning layer between a human request and the ComfyUI execution system.

A user may describe a desired image, video, GIF, audio scene, character, body-shape correction, camera angle, environment, motion, soft-body/contact detail, or model-selection task in plain language. The Scene Director converts that request into structured data that the rest of the system can validate, route, compile, execute, and QA.

The Scene Director does not directly generate media. It creates the execution plan.

## Why this layer is required

Without a Scene Director, large ComfyUI systems tend to become unstable because the user request goes straight into a giant graph, model stack, or prompt. That causes several problems:

- wrong engine selected
- wrong LoRA family mixed into a checkpoint
- too many LoRAs enabled at once
- notes mistaken for executable lanes
- staged nodes treated as production-ready
- camera/framing goals lost
- mask/detail passes applied globally
- output promoted without proof
- video/audio lanes mixed into image lanes
- Civitai model metadata ignored
- no repeatable QA target

Wave07 prevents that by making the request become a structured contract first.

## Core inputs

The Scene Director reads:

1. Raw user request.
2. User constraints.
3. Negative constraints.
4. Reference assets, if provided.
5. Civitai/model registry metadata.
6. Engine registry/router rules.
7. Workflow module catalog.
8. Main Flow deconstruction summary.
9. QA catalogs.
10. Prior pass/promotion/evidence state.

## Core outputs

The Scene Director writes:

1. `scene_director_plan.json`
2. `scene_graph.json`
3. `camera_plan.json`
4. `mask_plan.json`
5. `model_selection_plan.json`
6. `engine_route.json`
7. `pass_plan.json`
8. `qa_goal_plan.json`
9. `promotion_requirements.json`
10. `evidence_requirements.json`

## Director boundary

The Scene Director may:

- normalize a request
- classify intent
- resolve non-blocking ambiguity
- pick planned engines from the registry
- select model candidates from registries
- propose pass order
- propose masks
- define QA goals
- define failure/retry rules

The Scene Director may not:

- run ComfyUI
- modify workflow JSON directly
- start EC2
- hydrate model binaries
- promote an output
- invent a model path
- enable all LoRA library nodes
- treat a note node as runtime proof
- direct-mix incompatible engines

## System flow

```text
User request
  -> Scene Director
  -> structured scene plan
  -> validation harness
  -> workflow module compiler
  -> engine router
  -> ComfyUI API runner
  -> output/evidence collector
  -> QA and promotion gate
```

## Plan-first principle

Every generated media job must have a plan before execution. The plan is the source of truth for what the system intended to do. QA then compares the actual output against that plan.

If the plan says full-body framing, QA checks full-body framing.
If the plan says two characters, QA checks character count and separation.
If the plan says regional skin detail, QA checks mask overlays and no-bleed.
If the plan says Flux2-to-SDXL bridge, QA checks that transfer happened by image file, not by direct latent/model mixing.

## Integration with App Mode

App Mode should expose simplified controls such as:

- target output type
- scene preset
- engine preference
- camera/framing
- subject count
- reference inputs
- body/detail controls
- mask/detail intensity
- quality vs cost profile

App Mode submits those controls to the Scene Director, not directly to the giant graph.

## Integration with Civitai metadata

The Scene Director must use the Civitai-enriched model registry from Wave02 when it needs a checkpoint, LoRA, ControlNet, VAE, upscaler, video model, audio model, or specialty asset.

The Scene Director should not choose a model based only on a filename. It should consider:

- model type
- version/base model
- engine family
- tags
- trigger words
- creator/source
- Civitai model/version ID
- file hashes
- local/S3/EC2 path status
- selected/rejected/superseded status
- allowed passes
- forbidden passes
- QA status
- prior promotion evidence

## Integration with Wave06 Engine Router

The Scene Director chooses the planned engine route. The Wave06 router enforces whether it is valid.

Example:

```text
Scene Director says:
  base pass -> Flux2 Dev
  detail pass -> SDXL inpaint

Wave06 router enforces:
  Flux2 and SDXL cannot share LoRAs or latent/model objects.
  The bridge must be approved image output -> image load -> low-denoise/refine.
```

## QA-first design

Every pass must have QA goals before runtime. The generated output is not judged only by subjective quality. It is judged against the plan.

Required QA classes:

- file/decode QA
- scene-intent QA
- camera/framing QA
- character-count QA
- anatomy QA
- identity/reference QA
- mask no-bleed QA
- contact/deformation QA
- engine compatibility QA
- temporal QA for video/GIF
- audio/AV sync QA
- promotion QA
