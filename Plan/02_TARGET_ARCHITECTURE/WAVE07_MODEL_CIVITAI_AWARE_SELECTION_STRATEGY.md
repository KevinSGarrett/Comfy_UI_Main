# Wave 07 Civitai-Aware Model Selection Strategy

## Purpose

The Scene Director must be aware of the model library, but it must not simply search filenames or randomly pick LoRAs.

Wave02 created the Civitai metadata strategy and 70+ column normalized registry. Wave07 uses that metadata to select candidate models for a scene plan.

## Required metadata inputs

The Director should use, when available:

- Civitai model ID
- Civitai version ID
- creator
- model name
- version name
- base model
- model type
- tags
- trigger words
- file name
- file hashes
- file size
- download/source URL metadata
- sample image metadata
- local path
- S3 path
- EC2 path
- engine family
- asset type
- allowed passes
- forbidden passes
- status
- verification tier
- QA requirements
- prior success/failure evidence

## Selection workflow

1. Convert request into model needs.
2. Map model needs to scene roles.
3. Query local registry first.
4. If metadata is missing, queue a Civitai metadata refresh.
5. Exclude rejected/superseded/disabled assets unless controlled comparison is requested.
6. Exclude wrong-engine models.
7. Exclude models that require a mask when no mask exists.
8. Prefer models with runtime proof and prior QA success.
9. Keep selected LoRA stacks small.
10. Send selected candidates to the router for hard validation.

## Model need examples

| Scene need | Model role | Required registry fields |
|---|---|---|
| hyperreal base | checkpoint or base realism LoRA | engine, base model, status, hash, allowed pass |
| body shape | regional LoRA/detail model | region, engine, mask requirement, allowed pass |
| skin detail | microdetail LoRA/inpaint model | region, texture type, mask scope |
| hair/face | identity/detail model | region, reference compatibility |
| pose/camera | pose/control model | control type, engine family |
| video motion | video model | temporal support, input format |
| audio/foley | audio model/tool | event type, timing support |

## Civitai refresh trigger

The Director should request a metadata refresh when:

- a model has no Civitai model/version ID
- base model is unknown
- trigger words are missing
- tags are missing
- hash is missing
- status is unknown
- the same hash appears under multiple names
- the filename suggests a category that conflicts with registry category
- the model was recently added to S3/local cache

## Output requirements

The Director model-selection plan must include:

- selected candidate models
- backup candidates
- blocked models and reason
- metadata freshness status
- required Civitai refresh jobs
- engine compatibility status
- QA proof requirements
