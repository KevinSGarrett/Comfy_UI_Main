# Wave 02 Model Asset QA Gates

## Purpose

Wave 02 QA protects the entire system from broken model references, missing metadata, Git mistakes, wrong-engine loading, EC2 cost waste, and bad model promotion.

## Gate 01 — Secret safety

Fail if committed files contain likely real secrets:

```text
GITHUB_TOKEN=
CIVITAI_API_KEY=
AWS_SECRET_ACCESS_KEY=
AWS_ACCESS_KEY_ID=
```

Allowed only in `.env.example` as blank placeholders.

## Gate 02 — No model binaries in Git

Fail if Git-tracked tree contains:

```text
*.safetensors
*.ckpt
*.pt
*.pth
*.bin
*.gguf
*.onnx
```

Exception: no exception for real model binaries.

## Gate 03 — Civitai metadata completeness

Every model registry row must include at minimum:

```text
asset_id_internal
hash_sha256
engine_family
asset_type
base_model_normalized
civitai_model_id or unresolved_civitai_origin
civitai_model_version_id or unresolved_civitai_origin
local_cache_path or s3_uri
s3_uri
comfyui_target_folder
recommended_pass_scope
required_qa_tests
promotion_status
```

## Gate 04 — 70+ column requirement

The normalized Civitai model registry must contain at least 70 columns.

This Wave 02 pack defines 146 columns. The AI system must not reduce this to a minimal schema.

## Gate 05 — Hash integrity

Fail if:

```text
hash_sha256 is missing
local file hash does not match registry
S3 hash/tag does not match registry
EC2 hash does not match registry after hydration
```

## Gate 06 — Engine compatibility

Fail if:

```text
Flux LoRA is selected for SDXL path
SDXL LoRA is selected for Flux path
Pony LoRA is selected for non-Pony path without explicit specialty image-bridge pass
VAE is treated as LoRA
ControlNet is treated as checkpoint
video model is selected for image base pass
audio model is selected for visual pass
```

## Gate 07 — S3 canonical storage

Fail production promotion if:

```text
s3_uri missing
s3_key not under approved prefix
S3 asset not present when runtime proof requires it
storage-class/tag/hash metadata missing when required
```

## Gate 08 — EC2 cost guard

Fail EC2 runtime proof if:

```text
local registry validation failed
hydration manifest missing
S3 dry-run not performed
EC2_START_ALLOWED=false
EC2 instance is not tagged/identified
stop-after-run not configured
```

## Gate 09 — Duplicate/superseded model handling

Fail if duplicate hashes exist without:

```text
dedupe_group_id
duplicate_of_asset_id
preferred_version_flag
duplicate_reason
```

Fail if `rejected_or_superseded` assets are selected for production.

## Gate 10 — QA evidence

Every model validation run must produce:

```text
qa/evidence/model_asset_validation/<timestamp>.json
qa/evidence/model_asset_validation/<timestamp>.csv
```

## Wave 02 completion criteria

Wave 02 passes only when:

```text
.env.example exists
.ec2.example exists
Civitai docs exist
70+ column registry spec exists
S3/local/EC2 storage docs exist
validation script exists
metadata ingest script exists
validation report says PASS
```
