# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then re-open the standard hydration files in this folder.

## Current session completed

- Completed Wave 59-62 local static/package validation and cumulative zip validation.
- Initialized and pushed GitHub `main`.
- Passed GitHub API, AWS/EC2 identity, EBS volume, and Civitai metadata readiness checks.
- Found EC2 ComfyUI at `/home/ubuntu/ComfyUI` with NVIDIA A10G.
- Synced project repo to `/home/ubuntu/Comfy_UI_Main`.
- Inventoried EC2 ComfyUI runtime and model folders at HEAD `aaca121739e55c42b49d5b2cbb2be3c593d0c9ab`.
- Stopped EC2 and verified final state `stopped`.

## Current goal

Select the lowest-risk workflow lane and record prerequisite matching.

## Next exact action

Commit/push the EC2 runtime inventory checkpoint, then match workflow prerequisites:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 inventory"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, inspect `Plan\07_IMPLEMENTATION\workflow_templates\base_generation\*\runtime_requirements.example.json` and match the safest candidate against EC2 inventory evidence. Do not run generation until prerequisite matching is recorded.

## Evidence created

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Inventory/W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.md`

## Must not repeat

- Do not print token values from `.env`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not leave EC2 running.
- Do not run generation until prerequisite matching is recorded.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
