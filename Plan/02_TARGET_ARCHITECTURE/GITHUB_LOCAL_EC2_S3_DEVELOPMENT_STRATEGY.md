# GitHub, Local Repo, EC2 Mirror, and S3 Model Strategy

## Decision

Use GitHub and `C:\Comfy_UI_Main` for code, workflow templates, schemas, docs, manifests, scripts, tests, and lightweight config. Do **not** store checkpoint, LoRA, VAE, ControlNet, upscaler, video, or audio model binaries in Git.

Canonical repo:

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
Local path:
C:\Comfy_UI_Main
```

## Why model files cannot live in Git

GitHub blocks files larger than 100 MiB and recommends Git LFS for large files, but the project has hundreds of GB/TB of model files, so even Git LFS should be avoided for the main model library. The canonical model library must live in S3/EC2/local cache manifests rather than Git.

## Repository contents

```text
C:\Comfy_UI_Main
├─ workflows_api/
├─ workflows_ui/
├─ subgraphs/
├─ app_mode/
├─ orchestrator/
├─ schemas/
├─ registries/
├─ manifests/
├─ scripts/
├─ qa/
├─ tests/
├─ docs/
├─ examples/
└─ .gitignore
```

## Git-excluded contents

```text
models/
outputs/
input/private_references/
secrets/
*.safetensors
*.ckpt
*.pt
*.pth
*.onnx
*.gguf
*.mp4
*.mov
*.wav
*.flac
*.png large generated outputs
```

## Model asset layers

```text
S3 canonical model store
  ↓ hydrate selected assets only
EC2 GPU runtime cache
  ↓ optional local cache / stubs
Local development manifest validation
```

## Local development rules

Local work must validate structure without needing all model binaries:

1. Validate JSON, schemas, paths, registry shape, prompts, pass plans, and workflow graph reachability locally.
2. Validate model references against `model_registry.json`, not by loading all model files.
3. Use stubs for missing local model files.
4. Run CPU-safe tests locally.
5. Turn EC2 on only for GPU runtime proof, model-loader proof, image/video/audio output proof, or final QA evidence.

## EC2 development rules

EC2 must be treated as an on-demand render/proof worker:

1. Start EC2 only when a wave requires GPU runtime proof.
2. Sync repo code/config to EC2.
3. Hydrate only required model files from S3 using the model manifest.
4. Run ComfyUI tests through API.
5. Pull back outputs, logs, manifests, QA evidence, and runtime reports.
6. Stop EC2 automatically.

## S3 sync policy

Use include/exclude rules so only required files are synced for the current wave. The model registry must specify which model files are required for each runtime proof.

## Required scripts

- `scripts/local/validate_repo.ps1`
- `scripts/local/validate_workflows.py`
- `scripts/models/hydrate_models_from_manifest.py`
- `scripts/models/dehydrate_model_cache.py`
- `scripts/ec2/start_gpu_worker.ps1`
- `scripts/ec2/sync_repo_to_ec2.ps1`
- `scripts/ec2/run_runtime_proof.ps1`
- `scripts/ec2/pull_evidence_and_stop.ps1`

## Promotion rule

No wave can be marked runtime-complete until the EC2 proof report includes:

- exact commit SHA,
- exact workflow/template IDs,
- exact model manifest IDs,
- output artifact SHA256,
- QA manifest,
- pass/fail decision,
- EC2 stopped confirmation.
