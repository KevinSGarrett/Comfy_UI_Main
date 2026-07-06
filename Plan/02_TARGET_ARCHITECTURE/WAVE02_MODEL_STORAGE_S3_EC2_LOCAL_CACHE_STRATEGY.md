# Wave 02 Model Storage, S3, EC2, and Local Cache Strategy

## Core decision

Model binaries must not be stored in Git.

Git stores:

- workflow JSON
- workflow API templates
- schemas
- registries
- metadata
- model manifests
- hydration instructions
- QA evidence references
- source summaries
- scripts

Git does not store:

- `.safetensors`
- `.ckpt`
- `.pt`
- `.pth`
- `.bin`
- `.gguf`
- `.onnx`
- rendered video/audio/image outputs
- zipped EC2 bundles
- real `.env` files

## Canonical model storage

S3 is the canonical binary store.

```text
s3://<S3_MODEL_BUCKET>/models/<engine>/<asset_type>/<category>/<civitai_model_id>/<version_id>/<filename>
```

Example:

```text
s3://comfy-main-models/models/flux/lora/skin_texture/123456/789012/model.safetensors
s3://comfy-main-models/models/sdxl/checkpoint/realism/123456/789012/model.safetensors
```

## Metadata storage

Raw Civitai metadata is stored separately from model binaries.

```text
s3://<S3_MODEL_BUCKET>/metadata/civitai/<model_id>/<version_id>/model.json
s3://<S3_MODEL_BUCKET>/metadata/civitai/<model_id>/<version_id>/version.json
s3://<S3_MODEL_BUCKET>/metadata/civitai/<model_id>/<version_id>/images.json
s3://<S3_MODEL_BUCKET>/metadata/civitai/<model_id>/<version_id>/normalized_registry_row.json
```

Local raw cache:

```text
C:\Comfy_UI_Model_Cache\metadata\civitai_raw\<model_id>\<version_id>\
```

Repo normalized registry:

```text
C:\Comfy_UI_Main\registries\civitai_model_registry.csv
C:\Comfy_UI_Main\registries\model_asset_registry.json
C:\Comfy_UI_Main\registries\engine_compatibility_registry.json
```

## Local cache

Local cache is optional and must be treated as a cache only.

```text
C:\Comfy_UI_Model_Cache\checkpoints
C:\Comfy_UI_Model_Cache\loras
C:\Comfy_UI_Model_Cache\vae
C:\Comfy_UI_Model_Cache\controlnet
C:\Comfy_UI_Model_Cache\ipadapter
C:\Comfy_UI_Model_Cache\video_models
C:\Comfy_UI_Model_Cache\audio_models
```

The repo may include small stub JSON files that describe expected assets, but not model binaries.

## EC2 cache

EC2 model cache is a runtime mirror.

```text
/opt/ComfyUI/models/checkpoints
/opt/ComfyUI/models/loras
/opt/ComfyUI/models/vae
/opt/ComfyUI/models/controlnet
/opt/ComfyUI/models/ipadapter
/opt/ComfyUI/models/video_models
/opt/ComfyUI/models/audio_models
```

EC2 cache is not canonical. EC2 can be destroyed/recreated if S3 metadata and model manifests are correct.

## Hydration strategy

The AI system must never blindly sync hundreds of GB.

Required strategy:

```text
pass_plan
→ required engines
→ required checkpoints
→ required LoRAs
→ required ControlNets / VAEs / IPAdapter models
→ hydration manifest
→ local dry-run
→ S3 dry-run
→ EC2 dry-run
→ explicit runtime proof
```

## Hydration manifest fields

Each hydration manifest entry must include:

```json
{
  "asset_id_internal": "W42-FLUX-0044",
  "engine_family": "flux",
  "asset_type": "lora",
  "source_s3_uri": "s3://bucket/models/flux/lora/body/123/456/file.safetensors",
  "target_ec2_path": "/opt/ComfyUI/models/loras/wave42/flux/body/file.safetensors",
  "target_local_path": "C:\\Comfy_UI_Model_Cache\\loras\\wave42\\flux\\body\\file.safetensors",
  "sha256": "required",
  "required_for_passes": ["masked_detail_pass"],
  "required_for_workflows": ["image_skin_detail_flux_api.json"],
  "hydrate_local": false,
  "hydrate_ec2": true
}
```

## No full-library activation

The current main flow includes library/reference LoRA nodes that are disabled by default. Wave 02 enforces that model selection must happen through compatible stack/profile routing, never by enabling every library node.

## Completion gate

Wave 02 is not complete until the AI system can produce:

1. a model registry row with at least 70 populated/intentionally-null fields;
2. a raw Civitai JSON cache entry;
3. a hash record;
4. a local path record;
5. an S3 URI record;
6. an EC2 target path record;
7. an engine compatibility decision;
8. a QA status;
9. a promotion status.
