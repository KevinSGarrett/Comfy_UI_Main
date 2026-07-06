# Wave 02 Delivery Report

## Wave

`02 — Model storage, S3/EC2/local cache`

## Goal

Keep models out of Git; use S3 as canonical storage and hydrate only needed assets.

## Added in this cumulative pack

Wave 02 adds the missing foundation for model asset operations:

- `.env.example` for local/GitHub/AWS/S3/EC2/Civitai/ComfyUI/QA configuration.
- `.ec2.example` for optional EC2-specific environment overlay.
- A Civitai API metadata system for model discovery, model/version lookup, image/sample metadata, tags, creators, file hashes, and raw JSON caching.
- A 146-column model registry column catalog, exceeding the requested 60–70+ columns.
- Model storage path conventions for S3, local cache, EC2 cache, metadata cache, hydration manifests, and evidence manifests.
- Strict QA gates for metadata completeness, hash proof, S3 canonical storage, Git safety, engine compatibility, and EC2 hydration.

## Important Wave 02 decision

Civitai API is metadata/source-intelligence input. It is not the rendering engine.

Rendering remains:

```text
ComfyUI local/EC2 runtime
→ pass planner
→ engine-specific workflow module
→ output QA
```

Civitai is used to enrich and organize models:

```text
local model file or Civitai URL/hash/model ID
→ Civitai API fetch
→ raw JSON cache
→ normalized registry
→ engine compatibility registry
→ S3/local/EC2 hydration manifest
→ QA/promotion
```

## Current source alignment

The current main flow already contains a disabled Wave42 LoRA library and says its disabled/disconnected LoRA nodes represent deployed paths, while the executable production chain remains separate and only compatible same-engine stacks should be promoted. Wave 02 turns that warning into model-asset policy and registry requirements.
