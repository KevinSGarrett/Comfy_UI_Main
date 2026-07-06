# Civitai API Model Metadata System

## Purpose

All models in the hyperrealism system must be treated as structured assets, not random files.

The AI project manager must use Civitai metadata to understand:

- what the model is;
- which engine/base model it belongs to;
- whether it is a checkpoint, LoRA, ControlNet, VAE, embedding, motion module, or other asset;
- what version it is;
- what file hashes identify it;
- what tags and trigger words belong to it;
- what sample images and metadata suggest about usage;
- what pass type it should be used in;
- what masks/control maps/QA are required;
- whether it is installed locally, mirrored to EC2, or canonical in S3.

## Required Civitai API endpoints

The system must support these Civitai API data sources:

```text
GET /api/v1/models
GET /api/v1/models/:modelId
GET /api/v1/model-versions/:modelVersionId
GET /api/v1/model-versions/by-hash/:hash
GET /api/v1/images
GET /api/v1/tags
GET /api/v1/creators
```

The AI system must store raw responses before normalization.

## Required ingestion paths

The system must support four ways to identify a model:

### 1. Local file hash path

```text
.safetensors file
→ compute SHA256
→ Civitai version by hash
→ model/version metadata
→ normalized registry row
```

### 2. Civitai model URL path

```text
https://civitai.com/models/<modelId>/...
→ parse modelId
→ fetch model
→ fetch versions
→ locate matching version/file
→ normalized registry row
```

### 3. Civitai model version ID path

```text
modelVersionId
→ fetch model version
→ fetch parent model
→ normalized registry row
```

### 4. Existing tracker/manifest path

```text
existing Wave42 manifest row
→ read engine/category/path/hash/profile
→ fetch missing Civitai data by hash or model/version ID
→ normalized registry row
```

## Raw cache requirement

Raw API responses must be preserved exactly so that future waves can re-normalize data without calling the API again.

Required raw cache files:

```text
civitai_raw/<model_id>/<version_id>/model.json
civitai_raw/<model_id>/<version_id>/version.json
civitai_raw/<model_id>/<version_id>/images.json
civitai_raw/<model_id>/<version_id>/creator.json
civitai_raw/<model_id>/<version_id>/tags.json
civitai_raw/<model_id>/<version_id>/fetch_manifest.json
```

## Normalized registry requirement

The normalized registry must be wide. The target is at least 70 columns. This Wave 02 pack defines 146 columns.

The registry exists because a model file alone is not enough. The system needs enough metadata to make autonomous decisions about:

- engine compatibility;
- pass routing;
- mask scope;
- LoRA stack selection;
- duplicate/superseded models;
- QA risk;
- S3 hydration;
- EC2 runtime proof;
- model promotion or rejection.

## Data preservation rule

The AI system must never discard raw Civitai data because a field is not currently used.

Store:

- raw JSON;
- normalized CSV/JSON;
- fetch timestamp;
- fetch status;
- fetch error if present;
- hash of raw JSON;
- transformation version.

## Pagination and reliability rule

The system must prefer cursor pagination where available, use small batches, retry with exponential backoff, and log duplicate records. Do not assume one successful call means the API is complete or stable.

## Authentication rule

The system must support an API token from `.env`:

```text
CIVITAI_API_KEY=
CIVITAI_AUTH_MODE=bearer_header
```

The real key must never be stored in Git.

## Model organization rule

Civitai metadata must feed all model organization decisions:

```text
Civitai model type
+ base model
+ file format
+ tags
+ trigger words
+ sample image metadata
+ existing Wave42 categories
+ QA results
→ normalized engine/category/pass/mask/profile assignment
```

## Required model classification outputs

Every model asset must receive:

```text
engine_family
asset_type
category_primary
scene_role_primary
recommended_pass_scope
recommended_mask_scope
allowed_pass_types
incompatible_pass_types
required_qa_tests
promotion_status
```

## Important boundary

Civitai metadata helps the system organize and select models. It does not prove that a model works in ComfyUI.

Runtime proof still requires:

```text
ComfyUI object_info check
model loader check
workflow API execution
GPU/EC2 proof if local machine cannot run it
output evidence manifest
QA crop/mask/control proof when applicable
```
