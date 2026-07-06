<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# EC2_GPU_SERVER_OPERATING_INDEX

## 1. Purpose

This file tells Codex Desktop how to identify and safely handle the EC2 GPU server used for ComfyUI runtime validation.

This file is an index and verification guide. Wave 60 will expand this into a full operational start/stop and sync protocol.

## 2. Canonical GPU server

```text
Instance ID:
i-0560bf8d143f93bb1

Name tag:
ComfyUI-LoRA-GPU-Server

AWS account:
029530099913

Instance type:
g5.xlarge

IAM profile:
ComfyUI-SSM-Profile

Expected normal idle state:
stopped

Public IP when stopped:
none

Attached EBS volume:
vol-0eb9b2c6d3d2706d6

Volume size:
1024 GB
```

## 3. What this server is for

Codex may use the GPU server for:

- ComfyUI workflow runtime validation
- Flux / SDXL / Pony engine testing
- checkpoint loading tests
- LoRA loading tests
- ControlNet / pose / depth / auxiliary model checks
- visual generation sample tests
- video generation sample tests
- audio-related runtime tests if configured
- VRAM and performance validation
- missing model/path detection
- registry-to-runtime compatibility checks
- artifact generation for QA evidence

Codex must not use the GPU server as a general-purpose development machine unless the task requires GPU/runtime validation.

## 4. Start criteria

Codex may start the instance only when all of these are true:

1. Local-only validation is insufficient.
2. A concrete GPU validation task exists.
3. AWS account and instance identity are verified.
4. The tracker item requires runtime evidence.
5. The expected artifact/log pullback path is known.
6. Codex has a stop plan.

## 5. Stop criteria

Codex must stop the instance after:

- validation completes
- validation fails and no further useful GPU work is possible
- required evidence has been pulled back
- a blocker prevents progress
- Codex is ending the session
- no GPU task is currently active

The expected idle state is:

```text
stopped
```

## 6. EC2 verification commands

Equivalent checks:

```powershell
aws sts get-caller-identity

aws ec2 describe-instances `
  --instance-ids i-0560bf8d143f93bb1

aws ec2 describe-volumes `
  --volume-ids vol-0eb9b2c6d3d2706d6
```

Codex must record the state observed before and after GPU use.

## 7. Artifact pullback requirements

After GPU use, Codex must pull back or preserve references to:

- generated images
- generated videos
- generated audio
- ComfyUI logs
- workflow JSON used
- model registry snapshot
- prompt/negative prompt metadata
- sampler/settings metadata
- seed metadata
- terminal output/logs
- error tracebacks
- QA scorecards
- pass/fail results
- screenshots when useful

No runtime test can be marked complete without evidence.

## 8. Path awareness rule

The EC2 server may not have the same path layout as local Windows. Codex must maintain a local-to-EC2 path mapping once the remote environment is inspected.

Until a later wave defines the exact mapping, Codex must not assume that:

```text
C:\Comfy_UI_Main\
```

exists on EC2. It must inspect and record remote paths before running remote commands.

## 9. EC2 issue classification

| Issue | Severity | Required Codex action |
|---|---:|---|
| Wrong instance | Critical | Stop immediately. |
| Wrong account | Critical | Stop immediately. |
| Instance fails to start | High | Record blocker. |
| SSM unavailable | High | Record blocker or use approved fallback later. |
| GPU unavailable | High | Record failure, do not claim runtime pass. |
| VRAM OOM | Medium/High | Record settings, reduce test scope, retry only with reason. |
| Missing model | Medium | Update model registry/task state, do not fake validation. |
| Broken path | Medium | Repair mapping and retest. |
| Failed output pullback | High | Do not mark test complete. |

## 10. EC2 status in Wave 59

Wave 59 defines the GPU server identity and verification model. It does not claim the instance was contacted, started, tested, or stopped.
