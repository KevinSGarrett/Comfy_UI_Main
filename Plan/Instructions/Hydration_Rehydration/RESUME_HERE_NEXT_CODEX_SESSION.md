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
- Added a bounded ComfyUI smoke helper and generated the patched `/prompt` request body for the selected SDXL lane without starting EC2 or running generation.
- Added an image artifact QA helper and generated a pending-artifact QA record/checklist for the future selected-lane smoke output.
- Added a secret-safe AWS auth gate helper and recorded redacted evidence that AWS remote browser authorization is still required before EC2 work can resume.
- Added an EC2 pullback record helper and generated pending-runtime dry-run evidence for post-generation artifact count/hash/QA routing.
- Added a selected-lane runtime readiness gate and recorded that local pre-EC2 readiness is true, while EC2 start and generation remain blocked by AWS auth/object-info/hash proof.
- Added a bounded EC2 workflow smoke-run coordinator and generated dry-run evidence plus a patched request body showing it refuses EC2 start/generation while auth/static proof gates are missing.
- Reran selected-lane readiness with the coordinator included in helper parser validation; local pre-EC2 readiness remains true and runtime remains blocked by auth/static proof.
- Tightened the EC2 static-proof helper so blocked `-Execute` calls write evidence before AWS identity checks or EC2 start.
- Generated gated static-proof dry-run evidence and blocked-execute evidence with `ec2_started=false`.
- Updated readiness and smoke-run coordinator static-proof discovery so dry-run and blocked-execute records are not treated as real object-info/path/hash proof.
- Added current operations helper static validation and recorded local-only evidence covering all 14 operations scripts, operation schema/template JSON, and the latest runtime gate evidence.
- Rechecked the stale `BLOCKER-W59-GIT-001` report and confirmed `C:\Comfy_UI_Main` already has `.git`, canonical `origin`, ignored/untracked `.env`, required GitHub/Civitai secret variable names, and local `main` matching `origin/main`.
- Sanitized `Test-OperationsHelperStatic.ps1` evidence output so validation temp paths are redacted, then regenerated current operations helper validation evidence with all local checks passing.
- Hardened `Invoke-GitHubCheckpoint.ps1` with staged content secret scanning and added a non-mutating checkpoint dry-run to current operations helper validation; latest operations helper validation passes with 7 local smoke checks.
- Added current QA helper static validation and recorded local-only evidence covering all 5 QA scripts, QA schemas/templates, markdown templates, image QA dry-run/technical sample checks, and selected-lane workflow static validation smoke.
- Added current hydration helper static validation and recorded local-only evidence covering all 3 hydration scripts, hydration templates, session-state generation, and the actual cumulative Wave 58-62 zip validation.
- Regenerated current generated local indexes and recorded evidence that the newest operations, QA, and hydration helper/evidence files are discoverable in generated indexes.

## Current goal

Refresh AWS auth, complete EC2 static proof for the selected lane, then run bounded workflow execution and generated image QA.

## Next exact action

Complete AWS CLI remote browser login in an interactive/browser-capable shell, then rerun the auth gate:

```powershell
aws login --remote
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json
```

The account must be `029530099913`, `ec2_work_allowed` must be `true`, and `safe_to_start_ec2` must be `true` before EC2 work resumes.

Then rerun the selected-lane readiness gate:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Only proceed if `ready_for_ec2_static_proof=true`.

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

The helper now self-gates before AWS identity checks or EC2 start. If auth/readiness gates are false, it writes a blocked-execute record and leaves `ec2_started=false`.

Do not run generation until object-info, path, and hash proof are recorded.

After object-info/path/hash proof exists, run the preferred bounded coordinator:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

Then pull back generated image artifacts and apply `Plan/Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md`.

Create a local pullback record after artifact pullback:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json
```

Image QA helper command after pullback record exists:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```

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
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_DRY_RUN_20260706T025536-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_REQUEST_20260706T025536-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_COMFY_WORKFLOW_SMOKE_HELPER_DRY_RUN_20260706T025536-0500.md`
- `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_DRY_RUN_20260706T030037-0500.json`
- `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_CHECKLIST_DRY_RUN_20260706T030037-0500.md`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_IMAGE_ARTIFACT_QA_HELPER_DRY_RUN_20260706T030037-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_20260706T031007-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_AWS_AUTH_GATE_HELPER_20260706T031007-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_EC2_PULLBACK_RECORD_DRY_RUN_20260706T031758-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_EC2_PULLBACK_RECORD_HELPER_DRY_RUN_20260706T031758-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T032345-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_RUNTIME_READINESS_LOCAL_GATE_20260706T032345-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_20260706T033928-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_20260706T033928-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T033522-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_EC2_WORKFLOW_SMOKE_RUN_HELPER_DRY_RUN_20260706T033928-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_GATED_20260706T034448-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_20260706T034448-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T034515-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_20260706T034516-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_20260706T034516-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_EC2_STATIC_PROOF_GATE_REFRESH_20260706T034516-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T035148-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T035148-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_CURRENT_RECHECK_20260706T035900-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_W60_GIT_CURRENT_RECHECK_20260706T035900-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T040205-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_SANITIZED_20260706T040205-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W60_GITHUB_CHECKPOINT_SECRET_SCAN_HARDENING_20260706T040505-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_GITHUB_CHECKPOINT_SECRET_SCAN_HARDENING_20260706T040505-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T040505-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_SECRET_SCAN_20260706T040505-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T040932-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_CURRENT_VALIDATION_20260706T040932-0500.md`
- `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_CURRENT_VALIDATION_20260706T041240-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_HYDRATION_HELPER_CURRENT_VALIDATION_20260706T041240-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_CURRENT_20260706T041526-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_CURRENT_20260706T041526-0500.md`

## Must not repeat

- Do not print token values from `.env`.
- Do not recreate Git metadata in `C:\Comfy_UI_Main`; `.git` already exists and `origin/main` currently matches local `main`. Use `C:\Comfy_UI_Main` as the canonical project root even if the Codex workspace root is `C:\Comfy_UI`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not start EC2 until `Test-AwsAuthGate.ps1` verifies account `029530099913` and reports `safe_to_start_ec2=true`.
- Do not run EC2 static proof until `Test-LaneRuntimeReadiness.ps1` reports `ready_for_ec2_static_proof=true`.
- Treat static-proof dry-run and blocked-execute records as safety evidence only, not as object-info/path/hash proof.
- Do not leave EC2 running.
- Do not treat a generated output as QA-ready until pullback file count/hash evidence is recorded.
- Do not run generation until prerequisite matching object-info, path, and hash proof is recorded.
- Prefer `Invoke-EC2WorkflowSmokeRun.ps1 -Execute` for the first bounded smoke generation after static proof because it owns the run lifecycle and stop verification.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
