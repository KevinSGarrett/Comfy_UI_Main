# Wave 02 Model Storage Implementation Manual

## Goal

Use S3 as canonical storage, local disk as optional dev cache, and EC2 as runtime cache. Do not put model binaries in Git.

## Required repo root

```text
C:\Comfy_UI_Main
```

## Required external cache root

```text
C:\Comfy_UI_Model_Cache
```

## Required S3 structure

```text
s3://<bucket>/models/
s3://<bucket>/metadata/civitai/
s3://<bucket>/manifests/model_assets/
s3://<bucket>/renders/
```

## Required repo structure

```text
C:\Comfy_UI_Main\
  workflows\
  workflows_api\
  registries\
  manifests\
  schemas\
  scripts\
  qa\
  docs\
```

## Forbidden repo structure

Do not create these inside Git with real model binaries:

```text
C:\Comfy_UI_Main\models
C:\Comfy_UI_Main\checkpoints
C:\Comfy_UI_Main\loras
C:\Comfy_UI_Main\vae
C:\Comfy_UI_Main\controlnet
C:\Comfy_UI_Main\video_models
```

If such folders exist for ComfyUI convenience, they must be ignored by Git or represented as symlinks/external mounts only.

## S3 upload rule

Before upload:

```text
compute sha256
write metadata registry row
write raw Civitai cache
create S3 target URI
dry-run sync/copy
confirm no Git binary inclusion
```

Then upload:

```powershell
aws s3 cp "<local_model_path>" "s3://<bucket>/models/<engine>/<asset_type>/<category>/<model_id>/<version_id>/<filename>" `
  --profile "<AWS_PROFILE>" `
  --region "<AWS_REGION>" `
  --storage-class STANDARD
```

## EC2 hydration rule

EC2 hydration must use a manifest. Do not run full sync unless explicitly approved.

Example:

```powershell
aws s3 cp "s3://bucket/models/flux/lora/body/123/456/file.safetensors" `
  "/opt/ComfyUI/models/loras/wave42/flux/body/file.safetensors" `
  --dryrun
```

The AI system must remove `--dryrun` only after local validation and explicit EC2 runtime proof authorization.

## Hash validation

For every model:

```text
local hash == registry hash
S3 hash tag or stored hash == registry hash
EC2 hash == registry hash after hydration
```

If any mismatch occurs:

```text
block asset
do not select for workflow
write QA failure manifest
```

## Metadata validation

For every model:

```text
Civitai metadata present OR exception record present
raw JSON cache exists
normalized registry row exists
engine family known
asset type known
recommended pass scope known
QA requirements known
```

## Model promotion

A model can only be promoted when:

```text
hash verified
Civitai metadata resolved or exception approved
S3 canonical URI exists
local/EC2 path mapped
engine compatibility passes
usage role assigned
QA tests defined
not rejected/superseded
```

## Model demotion

A model must be demoted when:

```text
hash mismatch
bad path
wrong engine
bad loader
bad runtime proof
frequent artifacts
identity drift too high
pose drift too high
duplicate of a better version
```
