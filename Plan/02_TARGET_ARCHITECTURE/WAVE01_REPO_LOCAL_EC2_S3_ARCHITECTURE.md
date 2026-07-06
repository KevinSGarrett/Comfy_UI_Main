# Wave 01 Architecture — GitHub, Local Repo, EC2 Mirror, S3 Model Store

## Core decision

The correct architecture is:

```text
GitHub repo
  = source control for code, docs, schemas, workflows, manifests, tests, and scripts

Local repo C:\Comfy_UI_Main
  = day-to-day development, validation, planning, static QA, workflow compilation

Local model cache
  = optional model files for local testing only, outside Git

S3
  = canonical model/object store for large model assets

EC2
  = GPU runtime proof and final render environment, kept off by default
```

## Why models must not be in Git

Model files are often hundreds of MB to multiple GB. GitHub blocks files above 100 MiB, and even Git LFS is not a good fit for hundreds of GB of constantly changing model libraries.

Therefore:

```text
DO NOT commit model binaries.
DO NOT commit ComfyUI outputs.
DO NOT commit generated video/audio renders.
DO NOT commit large downloaded custom-node caches.
DO commit model manifests.
DO commit sha256 references.
DO commit S3 URIs.
DO commit local/EC2 path mapping templates.
```

## Recommended root

```text
C:\Comfy_UI_Main
```

## Recommended remote

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

## Repository role

The repo is the AI project manager's command center. It should contain:

```text
docs/
  strategy, wave plans, operating manuals, QA reports

workflows/
  ui/
  api/
  subgraphs/
  modules/
  app_mode/

orchestration/
  planner/
  runner/
  qa/
  repair/
  registries/

schemas/
  JSON schemas for scene plans, pass plans, masks, model assets, QA manifests

configs/
  local.example.json
  ec2.example.json
  s3.example.json

scripts/
  powershell/
  python/
  bash/

manifests/
  source_inventory/
  model_assets/
  workflow_validation/
  qa/
  ec2_runtime_proof/

evidence/
  local/
  ec2/
  visual_qa/
  runtime_logs/

tests/
  unit/
  integration/
  golden_scenes/
  no_gpu_static/

external_assets/
  README.md
  model_mount_manifest.example.json

.github/workflows/
  static-validation.yml
```

## Local-first development rule

The AI system must do as much as possible locally before EC2 is started:

```text
Local allowed:
- parse workflow JSON
- validate schemas
- check repo structure
- check no model binaries are committed
- inspect manifests
- compile pass plans
- compile workflow API JSON
- test orchestration logic with mocks
- generate dry-run EC2 commands
- generate dry-run S3 hydration plans

EC2 required:
- actual GPU image/video generation
- model load proof
- custom node import proof on EC2
- VRAM/performance proof
- real ComfyUI /prompt execution using large models
- final render proof
```

## S3 model strategy

The model registry should be the source of truth for where each model lives.

Example:

```json
{
  "asset_id": "flux_base_dev_fp8",
  "engine": "flux",
  "role": "checkpoint",
  "s3_uri": "s3://YOUR_BUCKET/models/flux/checkpoints/flux1-dev-fp8.safetensors",
  "local_cache_path": "D:/ComfyUI_Models/flux/checkpoints/flux1-dev-fp8.safetensors",
  "ec2_path": "/opt/comfyui/models/checkpoints/flux1-dev-fp8.safetensors",
  "sha256": "known_sha256_here",
  "status": "planned"
}
```

## EC2 mirror strategy

EC2 should mirror only what is required for proof:

```text
1. Local pass planner selects exact workflow module.
2. Engine router selects exact required model assets.
3. Hydration manifest lists exact S3 URIs.
4. Dry-run S3 command is created.
5. EC2 start request is blocked until confirmation token exists.
6. EC2 starts only for runtime proof.
7. Required assets hydrate from S3 to EC2.
8. ComfyUI runtime proof runs.
9. Outputs/logs/manifests sync back.
10. EC2 stops.
```

## Failure handling

If any local static QA fails, EC2 must not start.

If EC2 proof fails, the AI system must:

```text
- stop EC2 if safe
- save logs
- save failed workflow JSON
- save model hydration manifest
- save ComfyUI history output if available
- create a remediation task
```
