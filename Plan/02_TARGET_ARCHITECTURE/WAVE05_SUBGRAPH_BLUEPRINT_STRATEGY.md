# Wave 05 — Subgraph Blueprint Strategy

## Purpose

Subgraphs should make complex reusable node groups manageable. They should not hide unresolved runtime assumptions.

## Best subgraph candidates for this project

### High-confidence early candidates

1. Upscale/export wrapper
2. Evidence manifest preparation
3. Reference image preparation
4. Basic image bridge wrapper
5. Local inpaint wrapper
6. Control-map preprocessing wrapper
7. Mask combine/grow/blur/feather wrapper

### Later candidates

1. Multi-character region/mask planner
2. Contact-zone mask planner
3. Temporal frame QA extractor
4. Audio scene manifest builder
5. AV sync manifest builder

## What should not become a subgraph yet

- The entire current Main Flow
- The disabled LoRA library
- Experimental adult/model catalogs
- Any module with missing object_info proof
- Any module whose model references are not registry-resolved
- Any branch represented only by notes

## Required subgraph metadata

Every subgraph blueprint must include:

- subgraph_id
- human-readable name
- AI-readable purpose
- owner wave
- required inputs
- required outputs
- required node classes
- model/asset dependencies
- patchable inputs
- QA outputs
- promotion rules
- rollback rules

## Subgraph versioning

Subgraphs must be versioned.

Example:

```text
subgraphs/mask_factory/mask_factory_v001.json
subgraphs/mask_factory/mask_factory_v002.json
```

Never overwrite a proven subgraph without preserving the previous version.

## Subgraph promotion lifecycle

```text
draft → static_validated → object_info_validated → local_runtime_validated → ec2_runtime_validated → production_candidate → production_approved
```

## AI project manager instructions

When modifying a subgraph:

1. Copy the last proven version.
2. Increment the version.
3. Apply changes.
4. Run static validation.
5. Run object_info validation.
6. Run local runtime proof if possible.
7. Run EC2 proof only when needed.
8. Compare output evidence against previous version.
9. Promote only if the new version improves or preserves QA.
