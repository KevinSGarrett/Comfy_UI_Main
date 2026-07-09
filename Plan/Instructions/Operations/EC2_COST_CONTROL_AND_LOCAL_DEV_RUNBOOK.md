# EC2 Cost Control And Local Dev Runbook

## Purpose

This runbook is the active cost-control policy for `C:\Comfy_UI_Main`. It separates cheap/local validation from paid EC2 runtime proof so autonomous sessions can keep moving without repeatedly starting the GPU instance for work that can be done locally or in GitHub Actions.

## Current Cost Facts

- A stopped EC2 instance does not accrue instance usage charges, but attached EBS storage still costs money while it exists.
- Public IPv4 and Elastic IP resources can create cost even when the instance is not doing useful GPU work.
- GitHub Actions, SSM, and CodeDeploy cannot directly update files on the disk of a stopped EC2 instance in the simple path used by this project. SSM and normal `git pull` work only after the instance is running.
- Therefore the best default is: prepare and validate everything before EC2 starts, then run one bounded EC2 proof window.

Primary references:
- AWS EC2 stop/start behavior: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/how-ec2-instance-stop-start-works.html
- AWS Elastic IP pricing note: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html
- AWS Spot interruption behavior: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-interruptions.html
- AWS Spot best practices: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html
- AWS hibernation prerequisites: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/hibernating-prerequisites.html
- GitHub Actions artifacts: https://docs.github.com/en/actions/tutorials/store-and-share-data
- GitHub Actions artifact retention: https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization

## Decision

Use a three-lane runtime strategy:

1. Local dev lane: use the local NVIDIA GPU for workflow/prompt iteration, low-resolution smoke previews, request construction, and node compatibility checks when local ComfyUI is available.
2. GitHub Actions preflight/package lane: validate and package while EC2 is off. The workflow in `.github/workflows/preflight-package.yml` checks model registry coverage, builds the verified run package, and uploads a short-retention deploy bundle artifact.
3. EC2 target proof lane: use the A10G instance only for target-runtime object-info, model path/hash, generation, artifact pullback, and QA.

Local or CI success never replaces EC2 final proof. It only reduces the number and length of EC2 starts.

## S3 Bundle And Model Cache Decision

Use S3 as the preferred non-Git transfer path for deploy bundles, runtime artifacts, and large model binaries.

- GitHub Actions uploads deploy bundles to S3 only when repository variables are configured: `AWS_ROLE_TO_ASSUME`, `AWS_REGION`, and `COMFY_DEPLOY_BUNDLE_S3_URI`.
- EC2 helpers now accept `-DeployBundleS3Uri` and `-DeployBundleSha256`. When supplied, the remote SSM payload downloads the prepared zip from S3, verifies SHA256, extracts it safely, and skips remote `git pull`/Git LFS.
- The RealVisXL checkpoint must be provisioned through S3/model cache or another approved non-Git path. Do not add model binaries to Git or Git LFS.
- EC2 S3 permissions must be least-privilege: read deploy bundles and model-cache objects, write only runtime-artifact pullback objects, and list only approved prefixes.

Safe-to-commit AWS policy templates live in:

```text
configs/aws/
```

They contain placeholders only and do not grant permissions until applied in AWS.

## Active Tools

Local dev preflight:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_low_risk_fallback_lane -OutFile C:\Comfy_UI_Main\runtime_artifacts\run_manifests\LOCAL_COMFY_DEV_PREFLIGHT_<timestamp>.json
```

Run package creation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_low_risk_fallback_lane -PromptProfileFile PromptProfiles\base_generation\hyperreal_editorial_portrait.json -RunId sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1
```

Deploy bundle creation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_low_risk_fallback_lane -RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json
```

GitHub Actions workflow:

```text
.github/workflows/preflight-package.yml
```

The workflow intentionally checks out without Git LFS payloads and uploads the deploy bundle for 7 days.

Optional local S3 publish for a prepared bundle:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W63_DEPLOY_BUNDLE_S3_PUBLISH_<timestamp>.json
```

The command is dry-run by default. Add `-Execute` only after AWS auth and bucket/prefix permissions are verified.

S3 runtime transfer readiness:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Operations_Static_Validation\W63_S3_RUNTIME_TRANSFER_READINESS_<timestamp>.json
```

The current readiness evidence is `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_S3_RUNTIME_TRANSFER_READINESS_20260706T142504-0500.json`. It is local-only, validates the safe-to-commit policy templates, prints no secret values, and currently reports `blocked_missing_s3_runtime_config` until deploy-bundle S3 URI, model-cache bucket/prefix, artifact-output prefix, GitHub OIDC role, and scheduler stop role are configured.

## EC2 Defaults

For future EC2 proof or smoke commands:

- Use `-SkipGitLfsPull` by default unless the selected lane explicitly requires Git LFS payloads from the repository.
- Prefer `-DeployBundleS3Uri <s3://...zip> -DeployBundleSha256 <sha256>` when a GitHub Actions or local deploy bundle has been uploaded to S3.
- Set a bounded runtime with `-MaxEc2RuntimeMinutes`.
- Before a live EC2 window, create a one-time emergency stop schedule when the scheduler role exists, and start an instance-side watchdog after SSM is online.
- Batch all target-runtime work for a lane into one window: static proof, smoke generation, remote manifest, pullback, stop, final-state verification.
- Stop the instance in a `finally` path and verify final state `stopped`.
- If a command exceeds the local SSM timeout, cancel the command, stop EC2, and write incomplete evidence rather than waiting indefinitely.

Example static proof:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

Preferred static proof when a verified S3 deploy bundle exists:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

Example workflow smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 45 -RunPackageManifestFile <run-package-manifest> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W63_EC2_WORKFLOW_SMOKE_REALVISXL_<timestamp>.json
```

Preferred workflow smoke when a verified S3 deploy bundle exists:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 45 -RunPackageManifestFile <run-package-manifest> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W63_EC2_WORKFLOW_SMOKE_REALVISXL_<timestamp>.json
```

Emergency stop schedule dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -StopAfterMinutes 60 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_EMERGENCY_STOP_SCHEDULE_<timestamp>.json
```

Instance-side watchdog dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1 -StopAfterMinutes 60 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_INSTANCE_WATCHDOG_<timestamp>.json
```

Both commands are dry-run by default. Add `-Execute` only when AWS auth, IAM permissions, and the intended EC2 runtime window are ready.

Runtime-window marker plan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2RuntimeWindowMarkerPlan.ps1 -LaneId sdxl_realvisxl_base_lane -Command "<approved live EC2 command>" -DeployBundleS3Uri s3://<bucket>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -EmergencyStopEvidencePath <emergency-stop-evidence.json> -WatchdogEvidencePath <watchdog-evidence.json> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_EC2_RUNTIME_WINDOW_MARKER_PLAN_<timestamp>.json
```

This helper is local-only. It writes a marker template for the future live window, but it does not write `runtime_artifacts/ec2_runtime_windows/ACTIVE_EC2_RUNTIME_WINDOW.json`; write the active marker only when the approved EC2 window is actually starting, then remove it or mark it `ENDED` after final stopped-state verification.

## Model Provisioning Cost Rules

Model binaries are not Git project artifacts. Do not commit checkpoints, do not add them to Git LFS as the default provisioning path, and do not spend EC2 time on repeated proof attempts when evidence already says a model is missing.

For missing EC2 models:

1. Read the model registry and runtime requirements first.
2. Check for an existing approved local file or cache/S3 copy.
3. If a local/cache copy exists, sync it through an approved non-Git path and verify SHA256 on EC2.
4. If no local/cache copy exists, prepare the Civitai/Hugging Face source metadata while EC2 is stopped, then use one bounded EC2 model-download/provisioning window.
5. Stop EC2 after provisioning and verify final state `stopped`.
6. Rerun EC2 static proof only after the expected file exists.

RealVisXL model provisioning status:

```text
expected_ec2_path: /home/ubuntu/ComfyUI/models/checkpoints/realvisxlV50_v50Bakedvae.safetensors
source: Civitai model 139562, version 789646, RealVisXL V5.0 (BakedVAE)
expected_sha256: 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
resolved_by: Plan/Instructions/QA/Evidence/Model_Registry/W63_EC2_REALVISXL_MODEL_INSTALL_20260706T125425-0500.json
verified_by: Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json
```

Preferred RealVisXL model install once the model is present in S3:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri s3://<bucket>/<model-cache-prefix>/realvisxlV50_v50Bakedvae.safetensors -ExpectedSha256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80 -MaxEc2RuntimeMinutes 20 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W63_EC2_REALVISXL_MODEL_INSTALL_<timestamp>.json
```

The command is dry-run by default. Add `-Execute` only after the S3 object exists, AWS auth passes, and the EC2 role has `s3:GetObject` for the model-cache prefix. A successful live record must report `result=install_model_hash_verified`, `final_state=stopped`, and `generation_executed=false`.

Current RealVisXL runtime status:

```text
model install: complete and SHA256 verified
EC2 static proof: complete after install
workflow smoke generation: complete
pullback: complete with local hash verification
image QA: technical pass and visual pass_with_notes_for_runtime_smoke
workflow smoke evidence: Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json
pullback evidence: Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json
image QA evidence: Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json
terminal handoff: Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json
current blocker: none for this single RealVisXL runtime smoke proof
S3 status: smoke run recorded s3_bucket_not_configured / remote s3_sync not attempted; SSM SSH-tunnel pullback succeeded as fallback
```

Next cost-saving action is to apply the EC2 runtime S3 policy template before future smoke/pullback windows, use `-S3Bucket`/`-S3Prefix` where supported, and avoid SSM chunk or SSH-tunnel pullback except as a fallback. Do not rerun the completed RealVisXL smoke only to test S3.

## Local ComfyUI Activation

Use local ComfyUI for iteration when a real local checkout exists. It is good for prompt/request construction, low-resolution previews, node compatibility checks, and workflow edits. It does not replace EC2 final proof.

Preflight:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -LocalComfyRoot <path-to-local-ComfyUI>
```

Start local dev server dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Start-LocalComfyUIDev.ps1 -ProjectRoot C:\Comfy_UI_Main -LocalComfyRoot <path-to-local-ComfyUI> -LowVram -OutFile C:\Comfy_UI_Main\runtime_artifacts\run_manifests\LOCAL_COMFY_DEV_START_<timestamp>.json
```

Add `-Execute` only after `main.py` is found. Default local settings use `127.0.0.1`, port `8188`, and low-VRAM arguments for the local RTX 5060 Laptop GPU class.

Run a verified local run package smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Invoke-LocalComfyUIRunPackageSmoke.ps1 -ProjectRoot C:\Comfy_UI_Main -RunPackageManifestFile <run-package-manifest> -LaneId <lane-id> -LocalComfyRoot C:\Comfy_UI_Main\ComfyUI -ExtraModelPathsConfig C:\Comfy_UI_Main\config\comfyui_extra_model_paths.yaml -LowVram -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_LOCAL_COMFYUI_RUN_PACKAGE_SMOKE_<timestamp>.json
```

The command is dry-run by default. Add `-Execute` only for a deliberately bounded local preview. A successful execute record must copy generated images into `Plan\Instructions\Operations\Pulled_Back_Artifacts\`, stop the local process it started, and be followed by technical plus whole-image visual QA for every generated artifact. Current helper validation evidence: dry run `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_RUN_PACKAGE_HELPER_DRY_RUN_20260706T210826-0500.json`; execute `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_RUN_PACKAGE_HELPER_EXECUTE_20260706T210854-0500.json`; visual QA `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_RUN_PACKAGE_HELPER_IMAGE_QA_VISUAL_20260706T211000-0500.json`.

## No-Loop Rule

If local preflight, model registry coverage, queue, Git, package, and instruction indexes are already current, do not create more local evidence solely to appear busy. Choose one of these:

1. Run local ComfyUI development work that changes the lane, prompt, package, or QA outcome.
2. Build or inspect the GitHub Actions deploy bundle.
3. Run one bounded EC2 target proof window when auth and Git gates pass.
4. Stop and report the exact external blocker.

## Deferred Options

Spot instances can be evaluated later for retryable experimental generations only. Do not use Spot for final proof until scripts checkpoint cleanly and tolerate interruption.

Hibernation is not the first optimization path. AWS requires hibernation to be enabled at instance launch, so it belongs to a future new-instance/AMI design, not the current instance.
