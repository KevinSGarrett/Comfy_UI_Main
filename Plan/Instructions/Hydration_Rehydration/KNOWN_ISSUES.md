# Known Issues

## Packaging known issues

None known.

## Runtime validation still required

The final pack defines instructions and protocols. It does not prove live runtime execution has succeeded. Runtime validations must be performed by Codex Desktop inside `C:\Comfy_UI_Main\`.

## Fixed issues this session

- `ISSUE-W59-INDEX-001`: Wave 59 live index generator failed under Windows PowerShell because `[System.IO.Path]::GetRelativePath` was unavailable. Fixed by adding `Get-RelativePathCompat`; retest passed. Evidence: `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json`.
- `ISSUE-W59-GIT-001`: `C:\Comfy_UI_Main` was not a Git repository. Resolved by initializing Git metadata, adding canonical origin, enabling LFS, committing, pushing `main`, and verifying remote HEAD. Evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json`.
- `ISSUE-W62-ZIP-001`: No cumulative zip file existed under `C:\Comfy_UI_Main`. Resolved by building `Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip` from tracked project files and passing the official cumulative pack validator. Evidence: `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json`.

## Active known issues

- `ISSUE-RUNTIME-COMFYUI-LOCAL-001`: Local `C:\Comfy_UI_Main\ComfyUI` runtime and expected model folders are absent, so local workflow execution and local model validation cannot run from this checkout. AWS/EC2 identity is verified and the instance is stopped; next action is bounded EC2 runtime discovery with stop verification. Evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`.
- `ISSUE-EC2-PROJECT-SYNC-001` (resolved 2026-07-06T01:59:07-05:00): EC2 discovery found ComfyUI at `/home/ubuntu/ComfyUI` and a working NVIDIA A10G GPU, but no `Comfy_UI_Main` project checkout was found in searched paths. Resolved by cloning the project to `/home/ubuntu/Comfy_UI_Main`, pulling Git LFS, verifying matching HEAD, and stopping EC2. Evidence: `Plan/Instructions/QA/Evidence/EC2_Project_Sync/W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.json`.
- `ISSUE-AWS-AUTH-EXPIRED-001`: The AWS CLI default login credential expired during workflow lane static proof. EC2 was stopped and verified stopped, but object-info, model path, model hash, execution output, and generated artifact QA are pending until AWS login is refreshed. Evidence: `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json`.
