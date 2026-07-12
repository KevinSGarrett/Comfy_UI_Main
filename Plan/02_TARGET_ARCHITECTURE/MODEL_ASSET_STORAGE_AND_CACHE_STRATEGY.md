# Model Asset Storage, Cache, and Manifest Strategy

## Core decision

Model binaries are external runtime assets. Git stores references, manifests, hashes, categories, engine compatibility, and hydration instructions only.

## Asset tiers

| Tier | Location | Purpose | Git status |
|---|---|---|---|
| Canonical model store | S3 | Source of truth for large binaries | Not in Git |
| EC2 runtime cache | EC2 EBS/NVMe | GPU runtime proof and final rendering | Not in Git |
| Local optional cache | local disk | Optional dev previews if available | Not in Git |
| Manifest registry | Git | Metadata, references, hashes, roles | In Git |
| Stub files | Git optional small text/json | Validate path intent without model binary | In Git if useful |

## Required model registry fields

```json
{
  "model_id": "W42-FLUX-0044",
  "engine": "flux",
  "asset_type": "lora",
  "category": "body",
  "scene_role": "body_detail",
  "canonical_s3_uri": "s3://bucket/models/wave42/flux/body/example.safetensors",
  "runtime_relative_path": "models/loras/wave42/flux/body/example.safetensors",
  "sha256": "...",
  "size_bytes": 0,
  "status": "installed|path_verified|rejected|disabled",
  "allowed_passes": ["masked_detail", "contact_deformation"],
  "forbidden_passes": ["global_base"],
  "requires_mask": true,
  "qa_required": ["mask_no_bleed", "crop_before_after"]
}
```

## Hydration algorithm

1. Read pass plan.
2. Resolve required checkpoints, VAEs, ControlNets, LoRAs, upscalers, video/audio models.
3. Check local/EC2 cache for exact SHA256.
4. Download missing files from S3.
5. Verify SHA256 and file size.
6. Write `hydration_manifest.json`.
7. Run ComfyUI runtime proof.

## Dehydration algorithm

1. Preserve generated evidence and logs.
2. Keep only pinned hot-cache assets if budget allows.
3. Delete unused model binaries from EC2 cache.
4. Stop EC2.

## Validation without models

Local CI must pass without full model files by validating:

- model IDs exist in registry,
- pass is allowed by engine and model role,
- required model status is not rejected/disabled,
- target path is syntactically valid,
- S3 URI is present for runtime-required models,
- workflow node values match registry references.


---

# Wave 02 Expansion — Civitai Metadata and S3 Hydration

Wave 02 extends this strategy with a mandatory Civitai-aware model registry.

## New rule

Every model asset should have:

```text
file hash
Civitai model/version identity when available
raw Civitai JSON cache
normalized registry row
S3 canonical URI
local cache path
EC2 target path
engine compatibility decision
pass-scope recommendation
QA status
promotion status
```

## Minimum registry width

The AI system must maintain at least 70 columns of metadata per model asset. Wave 02 defines 146 columns to support autonomous model selection, duplicate detection, engine routing, masked pass selection, QA, and EC2/S3 hydration.

## Civitai is source intelligence, not rendering

Civitai API data is used to organize and understand model assets. The ComfyUI local/EC2 runtime remains the execution layer.

## Machine-readable storage and proof contract

The canonical Row007 contract is:

`Plan/10_REGISTRIES/model_asset_storage_cache_contract.json`

Every runtime-required model is evaluated across two separate surfaces:

1. The declaration surface (`model_registry.jsonl` plus `model_runtime_validation_queue.csv`) records identity, lane, path, expected SHA256, and intended validation state.
2. The proof surface records actual presence, observed SHA256, runtime loading, output, QA, and promotion evidence for the exact lane and scope.

## Fail-closed precedence

When declaration and proof surfaces disagree, use the strictest current state for any runtime or promotion decision:

```text
blocked > missing > queued > local_validated > target_runtime_validated
```

A broader lane summary cannot override a queued or missing required-model row. Reconciliation requires a lane-matched evidence pointer and an intentional registry/queue state update; historical evidence is never rewritten to manufacture agreement.

## Required model checks

1. `model_registry_required`: exactly one active registry record must match the lane and required asset role.
2. `sha256_required`: the registry must carry a 64-character SHA256; runtime presence requires an observed matching hash.
3. `non_git_model_path`: the path must remain under an ignored model/cache root, and binary extensions remain prohibited from Git.
4. `required_model_presence`: a required asset must be present and hash-matched before the dependent local or target-runtime execution.

Registration is not installation. Expected hashes are not observed hashes. Local presence is not EC2 presence. A successful proof for one lane, model version, or scope does not promote a queued record for another lane.

## Current controlled exceptions

- The inpaint checkpoint declaration remains `queued` until its registry and validation-queue row are reconciled to the exact bounded proof state.
- Flux.1 Dev remains registered but locally absent, hash-unverified in the local cache, license-acceptance unasserted, and promotion-blocked.
- Existing validated SDXL/RealVisXL/ControlNet states remain bounded to their recorded lane evidence and do not imply universal model or project certification.
