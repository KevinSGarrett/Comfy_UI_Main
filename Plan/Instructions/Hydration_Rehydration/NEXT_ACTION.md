# Next Action

## Current local work completed

As of 2026-07-06T07:52:41-05:00, Codex completed queue-aware project readiness and runtime handoff hardening. `Test-ProjectReadinessSnapshot.ps1` imports runtime lane queue evidence and only allows EC2 static-proof readiness when the selected lane is first in `runtime_lane_queue.json`. `New-RuntimeUnblockHandoff.ps1` records the queue gate, includes a `runtime_lane_queue_recheck` command, and carries the `do_not_start_ec2_unless_runtime_lane_queue_allows` safety invariant. `Test-QAHelperStatic.ps1` contract-checks the queue gate. This work did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.

Current local validation is refreshed through the scan-safe project readiness snapshot, current Git blocker recheck, QA helper project-readiness contract validation, runtime unblock handoff validation, runtime handoff readiness contract validation, EC2 Git checkpoint gate validation, post-checkpoint Git recheck evidence, lane-aware project handoff validation, authored-lane local pre-EC2 evidence coverage, runtime lane queue validation, queue-aware project readiness/handoff retests, generated index refresh for the queue-aware slice, top-level workflow export/static validation, root local preflight, and a local run package for the first queued lane. The next runtime-unblocking action remains AWS CLI remote browser/SSO login in an interactive/browser-capable shell.

`sdxl_realvisxl_base_lane` is now authored and local-static validated as a second SDXL lane. Keep `sdxl_low_risk_fallback_lane` as the first EC2 proof/generation lane; queue `sdxl_realvisxl_base_lane` for later RealVisXL checkpoint path/hash/load/output QA after the low-risk lane proves the runtime path.

Lane-runtime readiness is now lane-specific. `Test-LaneRuntimeReadiness.ps1`, `Invoke-EC2LaneStaticProof.ps1`, and `Invoke-EC2WorkflowSmokeRun.ps1` must use readiness/static-proof evidence matching the requested `LaneId`; do not reuse low-risk SDXL readiness or proof files for RealVisXL.

Project readiness and runtime unblock handoff are now lane-aware too. The current first-runtime handoff is for `sdxl_low_risk_fallback_lane`; keep `-LaneId sdxl_low_risk_fallback_lane` on the first post-auth readiness, EC2 static-proof, and workflow-smoke commands.

Authored-lane evidence coverage is now part of QA helper validation. `Test-AuthoredLaneEvidenceCoverage.ps1` currently passes for both authored base-generation lanes with static validation, smoke dry-run/request, and lane readiness evidence matched by `LaneId`; it does not prove EC2 object-info/path/hash, generation, pullback, or visual QA.

Latest EC2 coordinator hardening also requires a clean pushed Git checkpoint before any EC2 `-Execute` run. `Invoke-EC2LaneStaticProof.ps1` and `Invoke-EC2WorkflowSmokeRun.ps1` now block locally unless `HEAD` equals `origin/main` and the worktree is clean, and their remote payloads verify the EC2 checkout reaches the expected pushed commit after `git pull --ff-only origin main`. Evidence commits can advance `HEAD`, so run the `git_checkpoint_recheck` handoff command immediately before EC2 work.

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

Latest project readiness snapshot now imports both `runtime_unblock_handoff` and `runtime_lane_queue`. It records `handoff_ready_runtime_blocked_auth`, `next_required_action=complete_aws_browser_sso_login`, `local_only=true`, `aws_contacted=false`, `github_api_contacted=false`, `civitai_contacted=false`, `ec2_started=false`, `generation_executed=false`, `command_step_count=10`, `markdown_written=true`, selected queue order 1, and `queue_allows_selected_lane_ec2_static_proof=true`.

Latest QA helper validation parses 9 QA scripts, runs 12 local smokes, includes the authored-lane coverage and runtime lane queue smokes, and contract-checks runtime handoff plus runtime queue fields with 0 project-readiness contract failures. This confirms the `.env` GitHub/Civitai keys are not the blocker for EC2; AWS browser/SSO auth is still the runtime gate.

Latest runtime handoff command sequence now includes both `runtime_lane_queue_recheck` and `git_checkpoint_recheck`; both must pass before EC2 static proof or workflow smoke execution.

Current local run package for the first queued lane:

```text
runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_20260706T081301-0500/RUN_PACKAGE_MANIFEST.json
```

It contains the patched `prompt_request.json` for later bounded `/prompt` execution, but it is local-only and records `execution_allowed=false`, `ec2_started=false`, and `generation_executed=false`.

Current hyperreal prompt-profile package for the first queued lane:

```text
runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/RUN_PACKAGE_MANIFEST.json
```

It contains the profile-modified `prompt_request.json` for `hyperreal_editorial_portrait_v1`; result is `pass_local_only`, `prompt_profile.applied=true`, `workflow_static.qa_status=pass`, `smoke_dry_run.error_count=0`, `ec2_started=false`, and `generation_executed=false`. Post-push root preflight evidence is saved at `runtime_artifacts/run_manifests/ROOT_LOCAL_PREFLIGHT_20260706T090734-0500.json` with failed check count `0`.

Current package-fed EC2 workflow smoke dry-run:

```text
Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_HYPERREAL_PACKAGE_20260706T091711-0500.json
```

It proves `Invoke-EC2WorkflowSmokeRun.ps1 -RunPackageManifestFile` can consume the hyperreal package, validate the package hash/profile/lane match, copy the package `prompt_request.json`, and keep `ec2_started=false` plus `generation_executed=false` while AWS auth is expired. The paired request body is `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_HYPERREAL_PACKAGE_20260706T091711-0500.json`.

Do not start EC2 unless the auth gate reports:

```text
ec2_work_allowed: true
safe_to_start_ec2: true
```

After AWS auth is refreshed and verified, rerun the EC2 static proof for `sdxl_low_risk_fallback_lane`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -LaneId sdxl_low_risk_fallback_lane -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Only proceed to EC2 static proof when the readiness record reports:

```text
local_pre_ec2_ready: true
ready_for_ec2_static_proof: true
```

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
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
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
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
