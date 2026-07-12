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

## Machine-readable deployment contract

The canonical architecture contract is:

`Plan/10_REGISTRIES/repo_ec2_s3_development_contract.json`

The contract evaluates static and live state separately for four controls:

1. `ci_preflight`: workflow structure, no-LFS checkout, package steps, artifact retention, and configuration-gated S3 upload are static facts; current CI alignment and any live workflow run are separate facts.
2. `s3_bundle_manifest`: local deploy-bundle content and manifest integrity may pass before upload; `ready_local_only` is never equivalent to live S3 publication.
3. `sha256_verification`: every bundle, model, input, output, log, manifest, and pullback claim is scoped to the exact hash chain reviewed.
4. `ec2_window_bound`: local TTL/watchdog dry runs prove command planning only; live enforcement requires current authentication, executed schedule/watchdog evidence, the bounded runtime record, pullback, and stopped-state verification.

## Split-state decisions

Each control records both `static_status` and `live_status`. Static readiness may remain reusable while a dependent live gate is blocked. A static pass must not erase a live blocker, and a historical lane-scoped runtime pass must not certify the current queue, all lanes, or the full project.

Allowed static claims:

- repository and workflow contract readiness;
- local deploy-bundle content readiness;
- local S3 naming/policy/readiness validation;
- exact historical lane-scoped hash integrity when its source evidence remains unchanged;
- non-executing EC2 window/stop-control planning.

Forbidden without current live proof:

- current CI package alignment or successful CI execution;
- current S3 upload/publication certification;
- current EC2 TTL/watchdog enforcement;
- current target-runtime execution for a changed scope;
- full-lane, release, or full-project runtime certification.
