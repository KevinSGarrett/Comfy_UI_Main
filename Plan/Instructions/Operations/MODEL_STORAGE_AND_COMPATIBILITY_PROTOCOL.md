# Model Storage and Compatibility Protocol

Wave: 60  
Purpose: Define how Codex Desktop should organize model storage and prevent incompatible Flux, SDXL, Pony, SD1.5, ControlNet, LoRA, video, and audio assets from being used in the wrong workflow lane.

Project constants:
- Main local project: C:\Comfy_UI_Main\
- Plan directory: C:\Comfy_UI_Main\Plan
- Items directory: C:\Comfy_UI_Main\Plan\Items
- Tracker directory: C:\Comfy_UI_Main\Plan\Tracker
- Instructions directory: C:\Comfy_UI_Main\Plan\Instructions
- Operations directory: C:\Comfy_UI_Main\Plan\Instructions\Operations
- GitHub repo: https://github.com/KevinSGarrett/Comfy_UI_Main
- GitHub token location: C:\Comfy_UI_Main\.env
- AWS account: 029530099913
- EC2 instance ID: i-0560bf8d143f93bb1
- EC2 name tag: ComfyUI-LoRA-GPU-Server
- EC2 type: g5.xlarge
- IAM profile: ComfyUI-SSM-Profile
- Expected normal idle state: stopped
- Public IP when stopped: none
- Attached EBS volume: vol-0eb9b2c6d3d2706d6
- EBS volume size: 1024 GB

## 1. Storage principle

The project may contain thousands of models and multiple generation engines. Codex must use registry-driven organization rather than memory or guesswork.

A model is not usable until its registry entry says where it belongs and what it is compatible with.

## 2. Storage tiers

| Tier | Purpose |
|---|---|
| Local project model folders | Active models used by local ComfyUI |
| EC2/EBS model folders | Active GPU runtime model cache |
| S3/archive storage | Large cold storage or transfer staging |
| Registry metadata | Source-of-truth for what each model is and why it exists |
| Rejected/candidate folders | Prevent rediscovery loops and accidental use |

## 3. Suggested local storage pattern

```text
C:\Comfy_UI_Main\ComfyUI\models\
  checkpoints\
  loras\
  controlnet\
  vae\
  upscale_models\
  embeddings\
  clip\
  unet\
  diffusion_models\
  text_encoders\
```

If the real ComfyUI folder layout differs, Codex must update indexes before moving files.

## 4. Compatibility lanes

Codex must assign one or more lanes:

```text
flux_base_generation
flux_refine
sdxl_base_generation
sdxl_refine
pony_specialty
sd15_legacy
controlnet_pose
controlnet_depth
controlnet_normal
video_generation
video_refine
audio_generation
audio_review
upscale_restore
qa_only
candidate_unverified
rejected
```

## 5. Engine compatibility matrix

| Asset | Flux lane | SDXL lane | Pony lane | SD1.5 lane |
|---|---:|---:|---:|---:|
| Flux checkpoint | yes | no | no | no |
| Flux LoRA | yes, if matching Flux family | no | no | no |
| SDXL checkpoint | no | yes | maybe if Pony-compatible context says no | no |
| SDXL LoRA | no | yes | maybe | no |
| Pony checkpoint | no | maybe with Pony-specific prompting | yes | no |
| Pony LoRA | no | maybe only in Pony-compatible SDXL setups | yes | no |
| SD1.5 checkpoint | no | no | no | yes |
| SD1.5 LoRA | no | no | no | yes |
| ControlNet | only if built for matching family | only if SDXL ControlNet | only if Pony-compatible SDXL ControlNet | only if SD1.5 ControlNet |

Unknown compatibility must be treated as blocked until runtime validation.

## 6. Cross-engine use

Codex may design multi-engine pipelines, but it must not directly load incompatible model files into the wrong engine.

Allowed pattern:

```text
Flux base image → exported image → SDXL/Pony low-denoise refine pass → QA comparison
```

Blocked pattern:

```text
Load Pony LoRA directly into Flux model stack
```

Allowed bridging requires:

- image handoff, not latent/model-file mixing unless specifically supported
- low denoise on refine passes
- before/after QA
- identity/anatomy drift check
- artifact comparison
- fallback to original if refine corrupts output

## 7. Model naming convention

Suggested normalized filename prefix pattern for registry labels:

```text
<base>__<type>__<short_model_name>__<version>__<hash8>
```

Examples:

```text
sdxl__lora__skin_microdetail__v1__abc12345.safetensors
flux_dev__lora__cinematic_realism__v2__def45678.safetensors
pony_sdxl__checkpoint__realistic_pony_mix__v5__9876abcd.safetensors
```

Do not rename physical files if ComfyUI or model managers depend on exact file names unless registry and workflow references are updated.

## 8. Registry location over physical location

Physical folders alone are insufficient. A model in `loras\` may still be incompatible with the current engine. Codex must consult registry fields:

```text
base_model
workflow_lane
compatible_engines
runtime_validation_status
qa_status
```

## 9. EC2/EBS model cache

The EC2 attached EBS volume is 1024 GB and should be treated as the GPU runtime cache. Codex must maintain a remote model cache index once live EC2 discovery is performed.

Remote registry fields:

```text
ec2_path
ec2_present
ec2_sha256
ec2_last_verified
ec2_load_test_status
```

## 10. Archive behavior

When a model is not active but may be useful:

```text
registry status: archived_candidate
physical location: archive/S3/local cold path
runtime status: not_active
```

Do not delete model files unless the tracker and registry explicitly mark them safe to remove.

## 11. Done gate

A storage/compatibility task is complete only when:

```text
[ ] model physical path known
[ ] registry entry exists
[ ] base family normalized
[ ] compatibility lane assigned
[ ] duplicate status known
[ ] runtime validation status known or queued
[ ] workflow references updated
[ ] tracker updated
```

Reference sources checked for Wave 60 protocol drafting on 2026-07-06:
- AWS CLI EC2 describe-instances command reference
- AWS CLI EC2 start-instances / stop-instances command references
- AWS CLI EC2 waiter references for instance-running, instance-status-ok, and instance-stopped
- AWS Systems Manager send-command and Run Command references
- AWS Systems Manager start-session reference
- GitHub personal access token and REST API authentication documentation
- Civitai REST API reference migration notice and historical endpoint reference
