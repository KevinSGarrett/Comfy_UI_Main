# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then re-open:

```text
Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md
Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
```

## Current session completed

- Rehydrated the Wave 58-62 instruction system.
- Completed Wave 59 live local index validation.
- Resolved missing Git metadata and pushed `main`.
- Completed Wave 60 operations static validation.
- Completed Wave 61 QA helper validation.
- Completed Wave 62 hydration helper and cumulative zip validation.
- Ran secret-safe readiness preflight. GitHub API, AWS account, EC2 identity, EBS volume, and Civitai metadata checks passed. Local ComfyUI runtime is absent.
- Ran bounded EC2 runtime discovery. SSM was online, NVIDIA A10G was visible, ComfyUI was found at `/home/ubuntu/ComfyUI`, no `Comfy_UI_Main` checkout was found, and EC2 was stopped afterward.

## Active blockers

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`: local `C:\Comfy_UI_Main\ComfyUI` runtime and model folders are absent. EC2 route found.
- `BLOCKER-EC2-PROJECT-SYNC-001`: EC2 has `/home/ubuntu/ComfyUI` but no `Comfy_UI_Main` checkout. Use bounded EC2 project sync after committing the discovery checkpoint.

## Current goal

Run bounded EC2 project sync with Git/LFS verification and stopped-state verification.

## Next exact action

Commit/push the EC2 discovery checkpoint, then run EC2 project sync:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 discovery"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, start only `i-0560bf8d143f93bb1`, use SSM to clone or update `/home/ubuntu/Comfy_UI_Main`, verify remote Git/LFS state, stop the instance, and verify final state is `stopped`.

## Evidence created

- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.md`
- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T012748-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.md`

## GitHub state

- `C:\Comfy_UI_Main` is a Git repository on `main`.
- `.env` is ignored and untracked.
- Latest pushed checkpoint before EC2 discovery evidence: `36a32c6c14dfeb8b26b7bae276c71731be7d2818`.

## AWS/EC2 state

- EC2 discovery final state was verified `stopped`.
- ComfyUI path on EC2: `/home/ubuntu/ComfyUI`.
- Project checkout on EC2: not found yet.
- GPU: NVIDIA A10G, driver `595.71.05`, memory `23028 MiB`.

## Must not repeat

- Do not rerun completed local static/package validations unless files change.
- Do not print token values from `.env`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not leave EC2 running after sync.
- Do not run generation or model downloads during project sync.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
