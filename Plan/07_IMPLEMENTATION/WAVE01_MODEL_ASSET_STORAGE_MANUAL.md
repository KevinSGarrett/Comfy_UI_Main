# Wave 01 Model Asset Storage Manual

## Decision

Model binaries stay outside Git.

## Model storage tiers

### Tier 1 — S3 canonical store

Purpose:

```text
canonical long-term model storage
exact source for EC2 hydration
exact source for local hydration if needed
```

### Tier 2 — Local cache

Purpose:

```text
local testing
local path/reference validation
optional local ComfyUI runtime
```

Recommended local cache outside Git:

```text
D:\ComfyUI_Models
```

or:

```text
C:\ComfyUI_Models
```

Do not store model binaries under:

```text
C:\Comfy_UI_Main
```

### Tier 3 — EC2 runtime cache

Purpose:

```text
GPU proof
runtime generation
final rendering
```

Recommended EC2 structure:

```text
/opt/comfyui/models/checkpoints
/opt/comfyui/models/loras
/opt/comfyui/models/vae
/opt/comfyui/models/clip
/opt/comfyui/models/controlnet
/opt/comfyui/models/upscale_models
/opt/comfyui/models/ipadapter
```

## Asset manifest

Every model must have a manifest entry.

Required manifest file:

```text
manifests/model_assets/model_asset_registry.json
```

Required fields:

```text
asset_id
engine
role
category
s3_uri
local_cache_path
ec2_path
sha256
size_bytes
status
allowed_workflow_modules
blocked_workflow_modules
runtime_verification_status
```

## Hydration rule

The AI system may only hydrate models by manifest.

Bad:

```text
sync the whole bucket
download all Flux models
download all SDXL models
```

Good:

```text
hydrate only the exact assets for pass_plan_id = waveXX_sceneYY_attemptZZ
```

## S3 command rule

Use dry-run first:

```powershell
aws s3 sync s3://bucket/models D:\ComfyUI_Models --exclude "*" --include "flux/checkpoints/flux1-dev-fp8.safetensors" --dryrun
```

Then only remove `--dryrun` after approval.

## Runtime proof

A model is not runtime-verified until:

```text
1. The file exists on the target machine.
2. Its sha256 matches the manifest.
3. ComfyUI can load it.
4. A minimal workflow using it runs.
5. A runtime proof manifest records success.
```
