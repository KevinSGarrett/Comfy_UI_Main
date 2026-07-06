# Wave 03 — Runtime Inventory and Validation Harness

## Wave focus

**Runtime inventory and validation harness**  
Validate workflow JSON, node availability, model references, registries, and manifests locally.

## Goal

Create the validation layer that future waves must use before any workflow module, model registry, masking lane, pass planner, video lane, or audio lane can be considered safe to promote.

Wave 03 does **not** render final images or prove creative quality. It creates the local-first validation system that proves the project is structurally correct before expensive EC2 runtime testing.

## Why this wave matters

The current main ComfyUI flow is a useful runtime-bound image canvas, but it still contains a large mix of executable lanes, staged lanes, notes, disabled/catalog LoRA nodes, manifest metadata, and promotion boundaries. The workflow itself states that reference identity, pose/depth/edge/mask control, and regional inpaint are still partly staged, and that additional reference-slot routing and pose/depth/OpenPose control maps remain notes until direct runtime proof exists.

Wave 03 turns those boundaries into machine-checkable validation gates.

## Required outcome

At the end of Wave 03, the AI project manager must be able to run local validation and answer:

1. Does the workflow JSON parse?
2. Are all node IDs and link IDs internally valid?
3. Are all link source and target slots valid?
4. Are declared link types consistent with node input/output types?
5. Which nodes are upstream of enabled outputs?
6. Which nodes are catalog-only, staged, disabled, or not upstream of an enabled output?
7. Which node types are required by the workflow?
8. Which model/checkpoint/LoRA/VAE/upscale/control assets are referenced?
9. Which model references are local, S3-backed, registry-backed, or missing?
10. Which registries/manifests parse as valid JSON?
11. Does the local ComfyUI runtime expose the required node types through `/object_info`?
12. Is EC2 actually required for the next validation step, or can the check still be done locally?

## Hard boundary

Wave 03 must keep EC2 **off by default**.

EC2 may only be used when:

- local static validation passes,
- local ComfyUI node visibility cannot prove the required runtime,
- the required GPU model loading proof cannot be completed locally,
- or a later wave explicitly requests EC2 runtime proof.

## Definition of done

Wave 03 is complete only when the cumulative pack contains:

- static workflow graph validator,
- model-reference extractor,
- local/registry model-reference validator,
- JSON registry parser,
- ComfyUI `/object_info` collector,
- object-info-to-workflow validator,
- local validation runner,
- Windows PowerShell validation wrapper,
- runtime inventory reports for the attached main flow,
- schema definitions for validation reports,
- strict QA gate documentation,
- release validation manifest.

## Promotion rule

A workflow or module may not be promoted to production-valid simply because it exists in the canvas.

Promotion requires:

```text
static graph PASS
+ required node types visible in /object_info
+ model references resolved or explicitly marked hydrate-required
+ registry/manifests parse
+ required outputs generated in a runtime proof
+ downstream creative QA in later waves
```

Wave 03 proves the first layers. Later waves prove creative accuracy, image quality, video continuity, audio sync, and full hyper-realism behavior.
