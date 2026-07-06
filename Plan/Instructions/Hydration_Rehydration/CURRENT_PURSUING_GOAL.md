# Current Pursuing Goal

## Active Wave
Wave 63 EC2 cost-control and local/CI preflight packaging, continuing Wave 61 runtime proof for queued lanes.

## Goal Statement
Advance `C:\Comfy_UI_Main` toward end-to-end autonomous ComfyUI completion by using `Plan/Instructions` as the operating system, avoiding repeated housekeeping, minimizing paid EC2 time, and moving from the completed first-lane runtime proof to the next concrete queued runtime work.

## Required Instruction Read Order
Every continuation must use `C:\Comfy_UI_Main` as the project root and must read these project instructions before changing code, evidence, trackers, runtime helpers, or goals:

1. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md`
2. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md`
3. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md`
4. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md`
5. `C:\Comfy_UI_Main\Plan\Instructions\NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md`
6. `C:\Comfy_UI_Main\Plan\Instructions\Operations\EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md`
7. `C:\Comfy_UI_Main\Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
8. `C:\Comfy_UI_Main\Plan\Instructions\Operations\README_OPERATIONS_WAVE60.md`
9. `C:\Comfy_UI_Main\Plan\Instructions\QA\README_QA_WAVE61.md`
10. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\TRACKER_UPDATE_PROTOCOL.md`
11. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\ITEMIZED_LIST_UPDATE_PROTOCOL.md`
12. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_LOG_PROTOCOL.md`
13. `C:\Comfy_UI_Main\Plan\Instructions\Waves\Wave63\WAVE63_SCOPE.md`

Do not replace this read order with a short autonomous goal. The pursuing goal is only the active objective pointer; detailed operating rules live in `Plan/Instructions`.

## How To Use The Instruction Files
Before acting, reconcile the newest acceptable evidence across the instruction files:

- Prefer current passing evidence with the newest timestamp over older failed blockers when the newer evidence directly supersedes it.
- Treat `BLOCKER-W59-GIT-001` as superseded for `C:\Comfy_UI_Main`; this root has a valid `.git`, canonical `origin`, and pushed `main`.
- Treat `C:\Comfy_UI` as historical/source context and a possible local development ComfyUI environment, not the active Plan-bearing project root.
- Treat Wave42/Main Flow analysis, registries, release records, and snapshots under `Plan` as source/staging context. The active runtime surface is `C:\Comfy_UI_Main\Workflows\base_generation`, with concrete API lanes only.
- If top summaries conflict with newer lower sections or evidence files, fix the summary instead of repeating old work.
- Use generated indexes to find files, but do not refresh indexes repeatedly unless files changed in the current turn.
- When evidence commits advance `HEAD`, rerun the Git checkpoint gate immediately before any EC2 `-Execute` path.
- Read `EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md` before any AWS/EC2 decision. If local or CI validation can advance the work while EC2 is stopped, do that first.

## Current Status
The first queued runtime lane, `sdxl_low_risk_fallback_lane`, completed target EC2 static proof, one bounded package-fed workflow smoke generation, SSM pullback, technical image QA, and visual QA with runtime-smoke notes. Do not repeat that lane just to re-prove the same path.

The next queued runtime lane, `sdxl_realvisxl_base_lane`, has also completed RealVisXL model installation, SHA256 verification, EC2 static proof after install, one EC2 workflow smoke generation, generated artifact pullback, pullback hash verification, and technical plus visual image QA. Do not rerun this smoke proof unless the lane, prompt, model, or runtime changed, or the user explicitly asks for a broader multi-sample image-quality certification.

Wave 63 cost controls are active:

- Local dev preflight: `tools\Test-LocalComfyUIDevPreflight.ps1`.
- Local dev startup: `tools\Start-LocalComfyUIDev.ps1`.
- Deploy bundle builder: `tools\New-EC2DeployBundle.ps1`.
- Deploy bundle S3 publisher: `Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1`.
- EC2 model S3 installer: `Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1`.
- EC2 emergency stop scheduler: `Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1`.
- EC2 instance-side watchdog: `Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1`.
- GitHub Actions preflight/package workflow: `.github\workflows\preflight-package.yml`.
- EC2 helpers now support `-SkipGitLfsPull`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, and `-MaxEc2RuntimeMinutes`.
- Safe-to-commit AWS least-privilege policy templates are under `configs\aws`.
- EC2 should be used only for target-runtime facts, not for package/build/index housekeeping.

## Last Verified Facts
The current root is `C:\Comfy_UI_Main`. `.env` is ignored, GitHub/Civitai variable names are present without printing values, and model binaries/private keys/generated media must not be committed.

Current proof evidence for the first lane includes:

```text
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_POST_LOGIN_RETEST_20260706T104311-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_POST_STATIC_PROOF_RETEST_20260706T110424-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_TECHNICAL_20260706T121958-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_VISUAL_20260706T122027-0500.json
```

S3 pullback was blocked by missing EC2 role permissions and SSH/SCP timed out, so SSM chunk pullback is the known working fallback. EC2 final state was verified `stopped`.

Current RealVisXL evidence:

```text
Plan/Instructions/QA/Evidence/Model_Registry/W63_EC2_REALVISXL_MODEL_INSTALL_20260706T125425-0500.json
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_LANE_RUNTIME_READINESS_REALVISXL_AFTER_STATIC_PROOF_20260706T132103-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_IMAGE_QA_TECHNICAL_REALVISXL_20260706T140027-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json
Plan/Instructions/QA/Evidence/Project_Readiness/W63_PROJECT_READINESS_REALVISXL_QA_COMPLETE_20260706T140806-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_COST_CONTROL_TERMINAL_STATE_VALIDATION_20260706T140909-0500.json
Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_TERMINAL_STATE_VALIDATION_20260706T141104-0500.json
```

The expected RealVisXL file is now present on EC2 and verified with SHA256 `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`. Model binaries must not be committed to Git.

## Next Exact Work
First, if the runtime proof, cost-control, tracker, or instruction updates are uncommitted, finish one clean Git checkpoint and verify local `HEAD == origin/main`.

Second, choose the next work intentionally. The default next work is one of:

1. Configure/apply S3 runtime permissions using `configs\aws\ec2-runtime-s3-policy.template.json`, `configs\aws\github-actions-oidc-deploy-bundle-policy.template.json`, and the scheduler templates so future deploy/model/artifact transfer is faster and cheaper.
2. Define the next lane/module from the Main Flow/Wave42 source context and run local validation, registry coverage, queue updates, run package creation, and deploy-bundle creation while EC2 is stopped.
3. If image-quality certification is the explicit next target, run a broader multi-sample RealVisXL QA plan rather than treating the single smoke image as final portfolio proof.

Third, keep using the cost-control lane before any future generation attempt:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Start-LocalComfyUIDev.ps1 -ProjectRoot C:\Comfy_UI_Main -LocalComfyRoot <path-to-local-ComfyUI> -LowVram
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -AllowNonFirstLane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -RunPackageManifestFile <realvisxl-run-package-manifest>
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -StopAfterMinutes 60
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1 -StopAfterMinutes 60
```

Do not rerun RealVisXL static proof, workflow smoke, pullback, or image QA for the completed proof unless the lane, prompt, model, runtime, or QA objective changed. The next runtime evidence should belong to a new lane/module or a user-approved broader quality pass.

## Hard Stop And No-Loop Rules
If AWS auth is expired, Git is not clean/pushed, or the selected lane is not ready, do not start EC2. Record the blocker once and switch only to a concrete local/CI task that changes runtime capability.

Allowed local/CI tasks while EC2 is stopped:

- Improve a lane, prompt profile, model registry record, run package, deploy bundle, or QA rule.
- Run local ComfyUI dev checks/previews without claiming EC2 equivalence.
- Run GitHub Actions preflight/package and inspect the artifact.
- Fix a real stale/conflicting instruction that would misroute the autonomous session.

Disallowed loop work:

- Repeating first-lane proof without a changed lane/package/prompt/QA objective.
- Rebuilding indexes or handoffs repeatedly with the same result.
- Running Git LFS pulls on the EC2 clock unless a lane explicitly needs them.
- Starting EC2 to upload/sync project files when a deploy bundle can be prepared and uploaded to S3 first.
- Starting EC2 for prompt/workflow iteration that local ComfyUI can handle.
- Updating this pursuing goal in a way that omits the required `Plan/Instructions` read order.

## Update Protocol
When this file is autonomously updated, preserve these sections and keep the required instruction read order. Updates should change only current status, last verified facts, next exact work, and hard blockers. Do not compress this file back into a short goal that omits `Plan/Instructions`.
