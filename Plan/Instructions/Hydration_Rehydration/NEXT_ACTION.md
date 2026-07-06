# Next Action

Current local validation is refreshed through the scan-safe project readiness snapshot, current Git blocker recheck, QA helper project-readiness contract validation, runtime unblock handoff validation, runtime handoff readiness contract validation, EC2 Git checkpoint gate validation, post-checkpoint Git recheck at `535c3320f443b05e1ab6dc236004fc36e0bfa611`, and generated index refresh. The next runtime-unblocking action remains AWS CLI remote browser/SSO login in an interactive/browser-capable shell.

Latest EC2 coordinator hardening also requires a clean pushed Git checkpoint before any EC2 `-Execute` run. `Invoke-EC2LaneStaticProof.ps1` and `Invoke-EC2WorkflowSmokeRun.ps1` now block locally unless `HEAD` equals `origin/main` and the worktree is clean, and their remote payloads verify the EC2 checkout reaches the expected pushed commit after `git pull --ff-only origin main`. The latest post-checkpoint Git recheck confirms the current local precondition passes at `535c3320f443b05e1ab6dc236004fc36e0bfa611`.

After AWS login, rerun the secret-safe auth gate:

```powershell
aws login --remote
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json
```

Expected account: `029530099913`.

Current profile-matrix evidence shows zero of 15 configured AWS CLI profiles authenticate to expected account `029530099913`, so GitHub and Civitai token presence in `.env` does not unblock EC2. After browser/SSO login, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsProfileAuthMatrix.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_PROFILE_AUTH_MATRIX_<timestamp>.json
```

The selected-lane readiness helper now records profile-matrix diagnostics too, but it still requires the auth gate to report `safe_to_start_ec2=true` before EC2 static proof.

Latest auth gate contract evidence records `result=blocked_expired_session`, `failure_category=expired_session`, `account_match=false`, and `remote_login_status=not_attempted`; operations validation confirms those top-level fields are present.

Latest lane readiness contract evidence records `result=local_pre_ec2_ready_runtime_blocked_auth`, `failure_category=expired_session`, `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, and `ready_for_generation=false`; operations validation confirms those top-level readiness fields and nested auth-gate summary fields are present.

Latest EC2 coordinator gate contract evidence records static-proof and workflow-smoke blocked `-Execute` results as `blocked_before_ec2_start`, `failure_category=expired_session`, and `ec2_started=false`; no EC2 start or generation occurred.

Latest operations validation now contract-checks those coordinator records directly: 5 evidence-contract checks, 0 failures.

Latest project readiness snapshot now also imports `runtime_unblock_handoff` and records `handoff_ready_runtime_blocked_auth`, `next_required_action=complete_aws_browser_sso_login`, `local_only=true`, `aws_contacted=false`, `github_api_contacted=false`, `civitai_contacted=false`, `ec2_started=false`, `generation_executed=false`, `command_step_count=8`, and `markdown_written=true`.

Latest QA helper validation contract-checks those runtime handoff fields with 0 project-readiness contract failures. This confirms the `.env` GitHub/Civitai keys are not the blocker for EC2; AWS browser/SSO auth is still the runtime gate.

Latest runtime handoff command sequence now includes `git_checkpoint_recheck`; it must pass before EC2 static proof or workflow smoke execution.

Do not start EC2 unless the auth gate reports:

```text
ec2_work_allowed: true
safe_to_start_ec2: true
```

After AWS auth is refreshed and verified, rerun the EC2 static proof for `sdxl_low_risk_fallback_lane`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Only proceed to EC2 static proof when the readiness record reports:

```text
local_pre_ec2_ready: true
ready_for_ec2_static_proof: true
```

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

`Invoke-EC2LaneStaticProof.ps1` now also self-gates before AWS identity checks or EC2 start. If the auth/readiness gates are false, it must write a blocked-execute record with `ec2_started=false`.

- update `/home/ubuntu/Comfy_UI_Main` to `origin/main`
- query ComfyUI `/object_info` and confirm `CheckpointLoaderSimple`, `EmptyLatentImage`, `CLIPTextEncode`, `KSampler`, `VAEDecode`, and `SaveImage`
- resolve `/home/ubuntu/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`
- record file size and sha256
- stop EC2 and verify `stopped`

Only after that proof exists, run the bounded EC2 workflow smoke-run coordinator and perform image QA.

Preferred smoke-run coordinator command after proof exists:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

The coordinator must:

- start only `i-0560bf8d143f93bb1`
- update `/home/ubuntu/Comfy_UI_Main`
- run ComfyUI remotely through SSM
- post the selected-lane smoke request
- create `REMOTE_ARTIFACT_MANIFEST.json`
- pull back through S3 when configured
- stop EC2 and verify `stopped`

After the generated image and runtime logs are pulled back locally, create the local pullback record:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json
```

Current local validation proves this helper excludes `REMOTE_ARTIFACT_MANIFEST.json` from artifact counts and hashes, so a manifest listing one generated image verifies as one local generated image.

Then route the pulled-back image to image QA:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```
