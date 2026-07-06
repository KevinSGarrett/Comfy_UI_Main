# Wave 02 Civitai API Implementation Manual

## Purpose

This manual tells the AI implementation system how to use Civitai API metadata to organize every model in the hyperrealism system.

## Required flow

```text
scan local model folders
→ compute file hashes
→ resolve Civitai model version by hash when possible
→ fetch model/version metadata
→ fetch sample images and generation metadata when available
→ fetch creator/tags when useful
→ cache raw JSON
→ normalize 70+ registry fields
→ write CSV/JSON registry
→ validate registry
→ create S3 hydration manifest
→ block promotion until QA passes
```

## Step 1 — Load environment

Use:

```text
07_IMPLEMENTATION/templates/repo/.env.example
```

The real `.env` must be local only and must never be committed.

Required variables:

```text
CIVITAI_API_KEY
CIVITAI_API_BASE_URL
LOCAL_MODEL_CACHE_ROOT
CIVITAI_CACHE_RAW_JSON_ROOT
CIVITAI_NORMALIZED_REGISTRY_PATH
S3_MODEL_BUCKET
S3_MODEL_PREFIX
AWS_PROFILE
AWS_REGION
```

## Step 2 — Scan local files

Supported extensions:

```text
.safetensors
.ckpt
.pt
.pth
.bin
.gguf
.onnx
```

For each file:

```text
compute sha256
record size
record extension
record original path
record inferred ComfyUI target folder
```

## Step 3 — Resolve Civitai identity

Preferred lookup:

```text
GET /api/v1/model-versions/by-hash/:hash
```

Fallbacks:

```text
parse Civitai URL if available
parse model ID/version ID from existing tracker/manifest
use known download URL
use filename/folder only as low-confidence fallback
```

## Step 4 — Fetch complete metadata

For each resolved model/version, fetch:

```text
model detail
model version detail
images/samples
creator when available
tags when available
```

## Step 5 — Cache raw JSON

Write raw JSON exactly as returned.

```text
civitai_raw/<model_id>/<version_id>/model.json
civitai_raw/<model_id>/<version_id>/version.json
civitai_raw/<model_id>/<version_id>/images.json
civitai_raw/<model_id>/<version_id>/fetch_manifest.json
```

## Step 6 — Normalize into wide registry

The normalized registry must include at least 70 columns. The Wave 02 registry target is 146 columns.

The AI system must not shrink this registry to a simple 10–15 field list. That would lose the information needed for autonomous routing, QA, model dedupe, and model promotion.

## Step 7 — Assign engine compatibility

Use evidence:

```text
base model
model type
file type
tags
existing manifest category
workflow loader requirements
```

Assign:

```text
engine_family
asset_type
comfyui_loader_class
comfyui_target_folder
allowed_pass_types
incompatible_pass_types
```

## Step 8 — Assign usage role

Assign:

```text
category_primary
scene_role_primary
recommended_pass_scope
recommended_mask_scope
recommended_mask_size_class
recommended_weight_min/max
recommended_denoise_min/max
required_qa_tests
```

## Step 9 — Build S3 canonical path

Use:

```text
s3://<bucket>/models/<engine>/<asset_type>/<category>/<model_id>/<version_id>/<filename>
```

## Step 10 — Validate

The validator must fail if:

- model binary is inside Git;
- hash is missing;
- Civitai metadata is missing and no exception exists;
- engine family is unknown;
- S3 URI is missing;
- duplicate hash exists without dedupe group;
- rejected/superseded asset is selected for production;
- model is selected for incompatible pass type;
- EC2 hydration manifest references nonexistent S3 assets;
- real API keys appear in committed files.

## Required outputs

```text
registries/civitai_model_registry.csv
registries/model_asset_registry.json
registries/engine_compatibility_registry.json
manifests/model_hydration_manifest.json
manifests/civitai_fetch_manifest.json
qa/evidence/model_asset_validation/*.json
```
