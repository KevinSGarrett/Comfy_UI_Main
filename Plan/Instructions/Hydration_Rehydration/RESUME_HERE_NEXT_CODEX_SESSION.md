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

- Completed Wave 59-62 local static/package validation and cumulative zip validation.
- Initialized and pushed GitHub `main`.
- Passed GitHub API, AWS/EC2 identity, EBS volume, and Civitai metadata readiness checks.
- Found EC2 ComfyUI at `/home/ubuntu/ComfyUI` with NVIDIA A10G.
- Synced project repo to `/home/ubuntu/Comfy_UI_Main`.
- Verified remote HEAD `edc659b41ad9f6a18c0d295427cbd6a5903ff8a3`, Git LFS pull, clean status, `.env` absent, zip present.
- Stopped EC2 and verified final state `stopped`.

## Active blockers

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`: local `C:\Comfy_UI_Main\ComfyUI` runtime and model folders are absent. EC2 route is active.

## Current goal

Run bounded EC2 ComfyUI/model/workflow inventory with stopped-state verification.

## Next exact action

Commit/push the EC2 project sync checkpoint, then run EC2 runtime inventory:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 project sync"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, start only `i-0560bf8d143f93bb1`, use SSM to inventory `/home/ubuntu/ComfyUI` model folders and `/home/ubuntu/Comfy_UI_Main` workflow/runtime files, stop the instance, and verify final state is `stopped`.

## Evidence created

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T015022-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Project_Sync/W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.md`

## Must not repeat

- Do not print token values from `.env`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not leave EC2 running after inventory.
- Do not run generation or model downloads during inventory.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
