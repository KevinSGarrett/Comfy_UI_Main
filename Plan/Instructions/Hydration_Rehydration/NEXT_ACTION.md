# Next Action

## Current next action - 2026-07-06T12:49:30-05:00

Finish and push the current checkpoint from `C:\Comfy_UI_Main`, then continue the second queued lane `sdxl_realvisxl_base_lane`.

Do not repeat the first-lane smoke path. `sdxl_low_risk_fallback_lane` already has EC2 static proof, bounded workflow smoke generation, SSM pullback, technical image QA, and visual QA with runtime-smoke notes.

The active RealVisXL blocker is now specific:

```text
BLOCKER-RUNTIME-REALVISXL-CHECKPOINT-EC2-001
Required EC2 file missing:
/home/ubuntu/ComfyUI/models/checkpoints/realvisxlV50_v50Bakedvae.safetensors

Expected source:
Civitai model 139562, version 789646, RealVisXL V5.0 (BakedVAE)

Expected SHA256:
6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
```

Current evidence:

```text
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_REALVISXL_20260706T123028-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_REALVISXL_MISSING_MODEL_CLASSIFICATION_20260706T124103-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_REALVISXL_MISSING_MODEL_CLASSIFICATION_20260706T124103-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_EC2_DEPLOY_BUNDLE_VALIDATION_20260706T124907-0500.json
```

Next runtime work after the checkpoint:

1. Verify AWS auth and Git clean/head.
2. Start EC2 only for a bounded model install/verification window.
3. Download or sync `realvisxlV50_v50Bakedvae.safetensors` into `/home/ubuntu/ComfyUI/models/checkpoints/`.
4. Verify SHA256 equals `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`.
5. Stop EC2 and verify final state `stopped`.
6. Rerun RealVisXL EC2 static proof with `-SkipGitLfsPull -MaxEc2RuntimeMinutes 25`.
7. Only if static proof passes, build/use the RealVisXL run package, run bounded workflow smoke, pull back artifacts, and perform image QA.

Wave 63 cost-control defaults are active: use local/CI validation first, use `-SkipGitLfsPull` unless the lane explicitly requires repository LFS payloads, set `-MaxEc2RuntimeMinutes`, and do not run housekeeping on the EC2 clock.

## Current runtime proof update - 2026-07-06T12:20:27-05:00

The first queued lane `sdxl_low_risk_fallback_lane` has now completed live EC2 static proof and one bounded workflow smoke generation from the hyperreal editorial portrait run package. Commit/push the evidence from this session before any further EC2 work.

Key current evidence:

```text
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_POST_LOGIN_RETEST_20260706T104311-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_AFTER_STATIC_PROOF_20260706T105156-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_POST_STATIC_PROOF_RETEST_20260706T110424-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_SSM_CHUNK_PULLBACK_aws_gpu_workflow_smoke_20260706T110424-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_TECHNICAL_20260706T121958-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_VISUAL_20260706T122027-0500.json
```

Generation result:

```text
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/images/9_codex_hyperreal_editorial_portrait_00002_.png
```

Runtime smoke result is `workflow_smoke_generation_complete`; pullback result is `pullback_hashes_verified`; visual QA result is `pass_with_notes_for_runtime_smoke`. EC2 final state is `stopped`.

Important caveats: S3 pullback is blocked by missing EC2 role permissions (`s3:ListBucket` and `s3:PutObject`); SSH/SCP timed out on port 22 even though `C:\Comfy_UI_Main\comfyui-lora-key.pem` exists and is ignored by Git. The artifact was pulled back through SSM chunk transfer and verified locally. Do not claim final image-quality certification from this single smoke image; it is a runtime-lane proof with visual QA notes.

Next exact action after committing this evidence: finish the Wave 63 cost-control checkpoint, run a final Git clean/head check, then prepare `sdxl_realvisxl_base_lane` locally/through CI before any EC2 start. Begin RealVisXL EC2 static proof only after another clean pushed checkpoint, auth gate pass, lane readiness pass, and deploy/package preparation.

## Current cost-control update - 2026-07-06T12:45:00-05:00

The project now has an active EC2 cost-control path:

```text
Plan/Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md
tools/Test-LocalComfyUIDevPreflight.ps1
tools/New-EC2DeployBundle.ps1
.github/workflows/preflight-package.yml
Plan/Instructions/Waves/Wave63/WAVE63_SCOPE.md
```

Before any new EC2 `-Execute`, use local/CI validation while EC2 is stopped. Default EC2 helpers to `-SkipGitLfsPull` and set `-MaxEc2RuntimeMinutes`. Do not rerun the completed low-risk lane just to re-prove it.

Recommended local preparation for the next queued lane:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -AllowNonFirstLane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -RunPackageManifestFile <realvisxl-run-package-manifest>
```

Recommended bounded EC2 static proof after auth/Git/readiness gates pass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

## Current local work completed

As of 2026-07-06T10:30:00-05:00, Codex reran `tools/Test-RootProjectPreflight.ps1` from `C:\Comfy_UI_Main` after the latest pushed evidence commit. Current evidence `runtime_artifacts/run_manifests/ROOT_LOCAL_PREFLIGHT_CURRENT_HEAD_20260706T103000-0500.json` reports `pass_local_only`, failed check count `0`, `.git` present, `HEAD == origin/main` at `8bd059bdec2b2c8bd95a158930d2a26fa9d77b0a`, `.env` ignored with GitHub/Civitai variable names present, root file structure present, active exported lanes static-valid, and model registry coverage passing for both active lanes. The stale `BLOCKER-W59-GIT-001` no-`.git` report is not active.

Queue-aware readiness is now superseded by the model-registry-gated runtime handoff. `Test-ProjectReadinessSnapshot.ps1` must import runtime lane queue, model registry coverage, and the current runtime unblock handoff; `New-RuntimeUnblockHandoff.ps1` must include `runtime_lane_queue_recheck`, `model_registry_coverage_recheck`, and `git_checkpoint_recheck` before any EC2 `-Execute` step. This work did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.

Current local validation is refreshed through scan-safe project readiness, current Git blocker recheck, QA helper project-readiness contract validation, runtime unblock handoff validation, runtime handoff readiness contract validation, EC2 Git checkpoint gate validation, post-checkpoint Git recheck evidence, lane-aware project handoff validation, authored-lane local pre-EC2 evidence coverage, runtime lane queue validation, model registry coverage validation, model-registry-gated project readiness/handoff retests, generated index refreshes, top-level workflow export/static validation, root preflight, and local run packages for the first queued lane. The next runtime-unblocking action remains AWS CLI remote browser/SSO login in an interactive/browser-capable shell.

`sdxl_realvisxl_base_lane` is now authored and local-static validated as a second SDXL lane. Keep `sdxl_low_risk_fallback_lane` as the first EC2 proof/generation lane; queue `sdxl_realvisxl_base_lane` for later RealVisXL checkpoint path/hash/load/output QA after the low-risk lane proves the runtime path.

Runtime scope boundary: Wave42/Main Flow analysis, registries, release records, and source snapshots exist under `Plan` as source/staging context. The current executable surface is only `C:\Comfy_UI_Main\Workflows\base_generation`, with simplified first-proof API lanes exported from validated Plan templates. Do not treat the full old `C:\Comfy_UI` workflow system or the full Wave42/Main Flow graph as active runtime until a specific lane/module is extracted and passes the current validation, registry, queue, package, auth, Git, readiness, static-proof, pullback, and QA gates.

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

Latest project readiness snapshot now imports `runtime_unblock_handoff`, `runtime_lane_queue`, and model registry coverage. It records `handoff_ready_runtime_blocked_auth`, `next_required_action=complete_aws_browser_sso_login`, `local_only=true`, `aws_contacted=false`, `github_api_contacted=false`, `civitai_contacted=false`, `ec2_started=false`, `generation_executed=false`, `command_step_count=11`, `markdown_written=true`, selected queue order 1, `queue_allows_selected_lane_ec2_static_proof=true`, and model registry coverage allowing selected-lane EC2 static proof.

Latest QA helper validation parses 10 QA scripts, runs 13 local smokes, includes authored-lane coverage, runtime lane queue, and model registry coverage smokes, and contract-checks runtime handoff, runtime queue, and model registry fields with 0 project-readiness contract failures. This confirms the `.env` GitHub/Civitai keys are not the blocker for EC2; AWS browser/SSO auth is still the runtime gate.

Latest runtime handoff command sequence now includes `runtime_lane_queue_recheck`, `model_registry_coverage_recheck`, and `git_checkpoint_recheck`; all three must pass before EC2 static proof or workflow smoke execution.

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

Current model-registry-gated runtime unblock handoff:

```text
Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.json
```

It records `gate_summary.run_package.valid=true`, profile `hyperreal_editorial_portrait_v1`, prompt hash match `true`, `gate_summary.model_registry_coverage.coverage_allows_selected_lane_ec2_static_proof=true`, command step count `11`, and a bounded workflow-smoke command containing `-RunPackageManifestFile`. Use its Markdown pair `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.md` as the current post-auth command handoff. The older `W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.md` file is historical and contains PowerShell backtick escape corruption; do not use it as the human handoff.

Current root preflight evidence:

```text
runtime_artifacts/run_manifests/ROOT_LOCAL_PREFLIGHT_CURRENT_HEAD_20260706T103000-0500.json
```

It proves `C:\Comfy_UI_Main` is the Git repository root, local `main` matched `origin/main` during the check, `.env` was ignored, required root directories exist, active lane exports validate, and model registry coverage is a required/passing EC2 preflight gate. Later evidence commits may advance `HEAD`, so rerun this preflight or the Git checkpoint recheck before any EC2 `-Execute` path.

Do not start EC2 unless the auth gate reports:

```text
ec2_work_allowed: true
safe_to_start_ec2: true
```

After AWS auth is refreshed and verified, rerun the current local preflight gates before EC2 static proof:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W61_RUNTIME_LANE_QUEUE_VALIDATION_<timestamp>.json
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json
git -C C:\Comfy_UI_Main status --short --branch
git -C C:\Comfy_UI_Main rev-parse HEAD
git -C C:\Comfy_UI_Main rev-parse origin/main
```

Required results: first runtime lane `sdxl_low_risk_fallback_lane`, selected lane order `1`, model registry selected lane result `pass`, failed check count `0`, clean worktree, and local `HEAD == origin/main`.

Then rerun the lane readiness gate for `sdxl_low_risk_fallback_lane`:

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
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

For the first hyperreal portrait execution, keep this package manifest in the command:

```powershell
-RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json
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

Current active model registry coverage:

```text
Plan/Registries/Models/model_registry.jsonl
Plan/Registries/Models/model_runtime_validation_queue.csv
Plan/Instructions/QA/Evidence/Model_Registry/W61_MODEL_REGISTRY_COVERAGE_20260706T093415-0500.json
```

It proves both active SDXL lanes have checkpoint registry records and queued runtime-validation rows. RealVisXL V5.0 metadata was fetched through the Civitai helper after fixing URL encoding, and the cached metadata confirms model id `139562`, version id `789646`, file `realvisxlV50_v50Bakedvae.safetensors`, and source SHA256 `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`. This does not download model binaries or replace EC2 path/hash/load proof.

Model registry coverage is now an EC2 preflight gate. Immediately before any EC2 static proof attempt, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json
```

Expected result: `pass_local_only`, selected lane `sdxl_low_risk_fallback_lane` result `pass`, failed check count `0`, no AWS/GitHub API/Civitai/ComfyUI contact, `ec2_started=false`, and `generation_executed=false`.

Then route the pulled-back image to image QA:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```
