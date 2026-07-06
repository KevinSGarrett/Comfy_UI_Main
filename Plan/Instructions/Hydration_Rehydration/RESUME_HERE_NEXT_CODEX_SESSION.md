# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then re-open the standard hydration files in this folder.

## Current session completed

- Completed Wave 59-62 local static/package validation and cumulative zip validation.
- Initialized and pushed GitHub `main`.
- Passed GitHub API, AWS/EC2 identity, EBS volume, and Civitai metadata readiness checks before AWS login expiry.
- Found EC2 ComfyUI at `/home/ubuntu/ComfyUI` with NVIDIA A10G.
- Synced project repo to `/home/ubuntu/Comfy_UI_Main`.
- Inventoried EC2 ComfyUI runtime and model folders at HEAD `aaca121739e55c42b49d5b2cbb2be3c593d0c9ab`.
- Stopped EC2 and verified final state `stopped`.
- Selected `sdxl_low_risk_fallback_lane` as the first bounded workflow execution candidate.
- Authored the selected lane workflow files under `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_low_risk_fallback_lane/`.
- Recorded lane-selection evidence and pending-runtime certification.
- Added local workflow static validation and EC2 static-proof helper scripts.
- Passed local static validation for the selected SDXL lane and recorded dry-run evidence for the EC2 proof helper.

## Current goal

Refresh AWS auth, complete EC2 static proof for the selected lane, then run bounded workflow execution and generated image QA.

## Next exact action

Refresh AWS CLI default login:

```powershell
aws login --remote
aws sts get-caller-identity --query Account --output text
```

The account must be `029530099913` before EC2 work resumes.

Then rerun the EC2 static lane proof for `sdxl_low_risk_fallback_lane`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

That helper should:

1. Start only `i-0560bf8d143f93bb1`.
2. Update `/home/ubuntu/Comfy_UI_Main` to `origin/main` and pull LFS.
3. Query ComfyUI `/object_info` for required node availability.
4. Resolve and hash `/home/ubuntu/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`.
5. Stop EC2 and verify `stopped`.
6. Record evidence before running generation.

Do not run generation until object-info, path, and hash proof are recorded.

## Evidence created

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Inventory/W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.md`
- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T022710-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_20260706T024845-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.md`

## Must not repeat

- Do not print token values from `.env`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not leave EC2 running.
- Do not run generation until prerequisite matching object-info, path, and hash proof is recorded.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
