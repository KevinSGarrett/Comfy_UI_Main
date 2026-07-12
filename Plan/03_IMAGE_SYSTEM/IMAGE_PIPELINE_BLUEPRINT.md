# Image Pipeline Blueprint

## Preferred production path

```text
Scene request
→ character bible + references
→ pose/camera/depth/control maps
→ base image generation
→ base QA
→ full-image realism refine
→ refine QA
→ mask factory
→ body-shape correction if required
→ skin/fabric/detail passes if required
→ face/hands/detail passes
→ contact/deformation passes if required
→ upscale/final detail
→ final crop QA
→ promotion manifest
```

## Base pass

Responsible for:
- number of characters
- identity seed
- body silhouette
- pose
- camera angle
- lighting
- composition
- environment

Not responsible for:
- cellulite
- pores
- finger indentation
- contact pressure
- individual skin blemishes
- final hand detail

## Detail pass

Responsible for:
- surface details
- local blemishes
- textile texture
- hair details
- skin details
- local body-part changes

## Shape pass

Responsible for:
- waist/stomach/hips proportions
- body silhouette
- large body morph corrections

## Contact pass

Responsible for:
- hand/body interaction
- pressure
- deformation
- indentation
- occlusion
- contact shadow

## Final pass

Responsible for:
- resolution
- final polish
- artifacts
- crop QA
- metadata and release

## Machine-readable stage contract

The current image-pipeline implementation and proof state is recorded in:

`Plan/10_REGISTRIES/image_pipeline_stage_contract.json`

The contract separates four gates:

1. `workflow_template_valid`: compiler, validator, current workflow template paths, and stage ordering are valid for local dry-run planning.
2. `prompt_request_valid`: an image request compiles with concrete evidence bindings and validates without errors or warnings.
3. `image_artifact_manifest`: every required pass must bind its input, workflow, model, output, QA, and scope evidence; a local or superseded manifest is partial only.
4. `promotion_gate`: promotion requires current same-scope runtime, QA, artifact, and certification evidence and cannot be inferred from compilation or local outputs.

## Current implementation boundary

- Base, control, inpaint/detail, and upscale workflow modules exist, but their runtime and QA scopes differ by lane.
- Mask, body-shape, hand/contact, and deformation passes remain blocked wherever trusted manual gold-mask or geometry authority is required.
- Flux remains blocked on license acceptance, installation, hash verification, and runtime proof.
- The existing evidence-bound orchestrator plan is local and dry-run-first; it proves planning and evidence linkage, not a completed production render chain.
- The current promotion manifest is superseded and local-only, has no run manifest or promoted outputs, and correctly blocks final promotion.

## Promotion invariant

No stage may inherit proof from another lane, seed, input, workflow version, model version, or runtime. A complete image pipeline claim requires a single materially scoped base-to-final chain with every required pass evidenced, strict whole-image visual QA, and a passing promotion decision.
