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

## EC2 Defaults

For future EC2 proof or smoke commands:

- Use `-SkipGitLfsPull` by default unless the selected lane explicitly requires Git LFS payloads from the repository.
- Set a bounded runtime with `-MaxEc2RuntimeMinutes`.
- Batch all target-runtime work for a lane into one window: static proof, smoke generation, remote manifest, pullback, stop, final-state verification.
- Stop the instance in a `finally` path and verify final state `stopped`.
- If a command exceeds the local SSM timeout, cancel the command, stop EC2, and write incomplete evidence rather than waiting indefinitely.

Example static proof:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

Example workflow smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 45 -RunPackageManifestFile <run-package-manifest> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W63_EC2_WORKFLOW_SMOKE_REALVISXL_<timestamp>.json
```

## Model Provisioning Cost Rules

Model binaries are not Git project artifacts. Do not commit checkpoints, do not add them to Git LFS as the default provisioning path, and do not spend EC2 time on repeated proof attempts when evidence already says a model is missing.

For missing EC2 models:

1. Read the model registry and runtime requirements first.
2. Check for an existing approved local file or cache/S3 copy.
3. If a local/cache copy exists, sync it through an approved non-Git path and verify SHA256 on EC2.
4. If no local/cache copy exists, prepare the Civitai/Hugging Face source metadata while EC2 is stopped, then use one bounded EC2 model-download/provisioning window.
5. Stop EC2 after provisioning and verify final state `stopped`.
6. Rerun EC2 static proof only after the expected file exists.

Current RealVisXL blocker:

```text
expected_ec2_path: /home/ubuntu/ComfyUI/models/checkpoints/realvisxlV50_v50Bakedvae.safetensors
source: Civitai model 139562, version 789646, RealVisXL V5.0 (BakedVAE)
expected_sha256: 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
evidence: Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_REALVISXL_20260706T123028-0500.json
```

## No-Loop Rule

If local preflight, model registry coverage, queue, Git, package, and instruction indexes are already current, do not create more local evidence solely to appear busy. Choose one of these:

1. Run local ComfyUI development work that changes the lane, prompt, package, or QA outcome.
2. Build or inspect the GitHub Actions deploy bundle.
3. Run one bounded EC2 target proof window when auth and Git gates pass.
4. Stop and report the exact external blocker.

## Deferred Options

Spot instances can be evaluated later for retryable experimental generations only. Do not use Spot for final proof until scripts checkpoint cleanly and tolerate interruption.

Hibernation is not the first optimization path. AWS requires hibernation to be enabled at instance launch, so it belongs to a future new-instance/AMI design, not the current instance.
