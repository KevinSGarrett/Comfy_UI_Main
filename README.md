# Comfy_UI_Main

This is the main local project root for the autonomous ComfyUI hyperrealism system.

## Working Directories

```text
C:\Comfy_UI_Main\
  Plan\                 Source-of-truth project plan, tracker, instructions, QA evidence
  Workflows\            Exported ComfyUI workflow files ready for runtime use
  models\               Local model placement guide; model binaries are git-ignored
  runtime_artifacts\    Pullbacks, run outputs, and review material; large outputs stay out of git
  configs\              Local runtime/config handoff files that are safe to commit
  .github\              CI preflight/package workflow definitions
  tools\                Root local validation, packaging, and deploy-bundle helpers
```

## Active Workflows

The first runtime lane is:

```text
Workflows\base_generation\sdxl_low_risk_fallback_lane\workflow.api.json
```

The second queued lane is:

```text
Workflows\base_generation\sdxl_realvisxl_base_lane\workflow.api.json
```

The authoritative planning copies remain under:

```text
Plan\07_IMPLEMENTATION\workflow_templates\base_generation
```

## Runtime Scope Boundary

`Plan\` contains Wave42/Main Flow analysis, registries, release records, and source snapshots. That material is source/staging context.

The active runtime surface today is the simplified first-proof lane set under `Workflows\base_generation`, not the full old `C:\Comfy_UI` workflow system and not the full Wave42/Main Flow graph. Main Flow material must be extracted into a concrete lane or module, statically validated, registered, queued, packaged, and passed through the current auth/queue/model-registry/Git/readiness/runtime QA gates before it becomes executable project runtime.

## Runtime Gate And Cost Control

GitHub and Civitai keys are loaded from `.env`, but they do not prove AWS access. Before any new EC2 work, AWS auth must be refreshed/verified for account `029530099913`, the worktree must be clean and pushed, the selected lane must pass runtime lane queue, model registry coverage (`result=pass_local_only`, selected lane `pass`, failed checks `0`), package, and lane-readiness gates.

Cost-control default: validate locally or in GitHub Actions while EC2 is stopped, then use EC2 only for target-runtime object-info, model path/hash/load, generation, pullback, and QA. See:

```text
Plan\Instructions\Operations\EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md
```

Preferred low-cost runtime path:

1. Build the run package and deploy bundle locally or in GitHub Actions.
2. Upload the deploy bundle to S3 before EC2 starts.
3. Provision large checkpoints through S3/model cache, not Git or Git LFS.
4. Run EC2 helpers with `-SkipGitLfsPull`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, and `-MaxEc2RuntimeMinutes`.
5. Use an EventBridge Scheduler emergency stop and/or instance-side watchdog for live EC2 windows.

The first low-risk lane has runtime smoke proof and pulled-back image QA evidence. Do not repeat that lane just to re-prove the same path; move to the next queued lane or a concrete user-approved improvement.

Current next-lane status: `sdxl_realvisxl_base_lane` now has RealVisXL model install evidence, EC2 static proof with the expected checkpoint SHA256, one completed EC2 workflow smoke generation, local pullback hash verification, and technical plus visual image QA. Do not rerun that smoke proof unless the lane, prompt, model, or runtime changed. The remaining cost-control improvement is S3 permissions for future deploy/model/artifact transfers, not a blocker for the completed RealVisXL proof.

Do not commit `.env`, model binaries, private keys, or generated media outputs.

## Root Tools

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Sync-WorkflowExports.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-RootProjectPreflight.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -LaneId sdxl_low_risk_fallback_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Start-LocalComfyUIDev.ps1 -ProjectRoot C:\Comfy_UI_Main -LocalComfyRoot <path-to-local-ComfyUI> -LowVram
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -LaneId sdxl_low_risk_fallback_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -LaneId sdxl_low_risk_fallback_lane -PromptProfileFile PromptProfiles\base_generation\hyperreal_editorial_portrait.json -RunId sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -LaneId sdxl_low_risk_fallback_lane -RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri s3://<bucket>/<model-cache-prefix>/realvisxlV50_v50Bakedvae.safetensors -ExpectedSha256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -StopAfterMinutes 60
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1 -StopAfterMinutes 60
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_low_risk_fallback_lane -RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json
```
