# Next Action

## Current next action - 2026-07-06T18:02:36-05:00

Finish the current stale-bundle static-proof failure checkpoint from `C:\Comfy_UI_Main`, then rebuild and publish a fresh RealVisXL matrix deploy bundle from the current clean pushed `HEAD`. The previous uploaded bundle was SHA-valid but built from source head `27111d0`, so the EC2 helper correctly rejected it against current `origin/main` `ce4487f`; do not retry static proof or run generation until a new S3 bundle sidecar records the current pushed head.

Latest run-package hardening: `tools\New-WorkflowRunPackage.ps1` now supports `-RouteRequestFile` and records the Wave64 router decision in each gated package manifest. Use it for future image run packages so package creation cannot bypass model-family and lane compatibility. Current package evidence is `runtime_artifacts/run_packages/sdxl_realvisxl_router_gated_package_v1/RUN_PACKAGE_MANIFEST.json`; dedicated validation is `Plan/Instructions/QA/Evidence/Run_Package/W66_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153601-0500.json`; QA helper evidence is `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153612-0500.json`. Result: `pass_local_only`, no EC2 start, no generation.

Latest local implementation: the Wave 64 image-engine router proof for `TRK-W64-009` / `ITEM-W64-009` is implemented and validated. Use `Plan/07_IMPLEMENTATION/scripts/resolve_wave64_image_engine_route.py` and `Plan/Instructions/QA/Scripts/Test-ImageEngineRouter.ps1` before promoting new image routes. Current post-ledger evidence is `Plan/Instructions/QA/Evidence/Engine_Router/W64_IMAGE_ENGINE_ROUTER_VALIDATION_POST_LEDGER_20260706T151800-0500.json`, with QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W64_QA_HELPER_IMAGE_ENGINE_ROUTER_POST_LEDGER_20260706T151800-0500.json`. Compatible RealVisXL SDXL routing passes; incompatible Flux LoRA on SDXL blocks with no external contact, EC2 start, or generation.

Current strict AI coverage files:

```text
Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv
Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv
Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv
Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv
Plan/Items/Reports/wave64_end_to_end_strict_ai_coverage_report.json
Plan/Tracker/Reports/wave64_end_to_end_strict_ai_coverage_report.json
```

Wave 64 hard media rule: localized visual/audio work cannot pass by looking only at the target region. Every generated image, video, GIF, or audio artifact must pass whole-artifact review; unrelated visible or audible defects block promotion.

Current exhaustive Plan source coverage files:

```text
Plan/Items/wave65_plan_source_coverage_closure_itemized_list.csv
Plan/Items/Waves/Wave65/WAVE65_PLAN_SOURCE_COVERAGE_ITEM_ROWS.csv
Plan/Tracker/wave65_plan_source_coverage_closure_tracker.csv
Plan/Tracker/Waves/Wave65/WAVE65_PLAN_SOURCE_COVERAGE_TRACKER_ROWS.csv
Plan/Items/Reports/wave65_plan_source_coverage_report.json
Plan/Tracker/Reports/wave65_plan_source_coverage_report.json
Plan/Items/Scripts/generate_wave65_plan_source_coverage.py
```

Wave 65 current result is `pass`: 2,866 current source files under `Plan` are covered, 691 closure Items rows and 691 closure Tracker rows were generated, and `missing_after_wave65_count=0`. Transient `__pycache__` and `.pyc` files are excluded from the coverage universe. Rerun `python Plan\Items\Scripts\generate_wave65_plan_source_coverage.py` after any Plan file addition or rename.

Latest multi-sample preparation: `tools\New-WorkflowRunPackageMatrix.ps1` created a router-gated RealVisXL certification matrix from `PromptProfiles/base_generation/realvisxl_multisample_certification.matrix.json`. Persistent manifest: `runtime_artifacts/run_package_matrices/realvisxl_multisample_certification_v1/RUN_PACKAGE_MATRIX_MANIFEST.json`; dedicated evidence: `Plan/Instructions/QA/Evidence/Run_Package/W66_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155031-0500.json`; QA helper evidence: `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155048-0500.json`. Result: `pass_local_only`, three unique RealVisXL sample packages, no EC2 start, no generation.

Latest deploy-bundle preparation: `tools\New-EC2DeployBundleMatrix.ps1` packaged that RealVisXL matrix, source JSON, prompt profiles, project context, and all three sample packages into one local-only deploy ZIP. Dedicated evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_EC2_DEPLOY_BUNDLE_MATRIX_S3_DRY_RUN_REDACTED_20260706T171921-0500.json`; QA helper evidence: `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_MATRIX_S3_DRY_RUN_REDACTED_20260706T171934-0500.json`; operations helper evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_MATRIX_BUNDLE_MANIFEST_20260706T171309-0500.json`. Result: `pass_local_only`, 55 bundled files, latest ZIP SHA256 `e29256311196349987e505bf38a8f2006b72cb7300fa5d545ce2270a01fc9d8e`, S3 dry-run manifest sidecar `DEPLOY_BUNDLE_MATRIX_MANIFEST.json`, no AWS contact, no EC2 start, no generation. EC2 bundle extraction now accepts both `DEPLOY_BUNDLE_MANIFEST.json` and `DEPLOY_BUNDLE_MATRIX_MANIFEST.json`.

Latest matrix quality-run planning: `Plan/Instructions/Operations/Scripts/New-EC2WorkflowMatrixQualityRunPlan.ps1` validates the RealVisXL three-sample matrix and emits bounded per-sample `Invoke-EC2WorkflowSmokeRun.ps1` commands. Dedicated evidence: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_20260706T173124-0500.json`; QA helper evidence: `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json`; operations helper evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json`. Result: `pass_local_only`; all three sample commands include `-RunPackageManifestFile`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, `-SkipGitLfsPull`, and `-MaxEc2RuntimeMinutes`; every sample has planned pullback and whole-image QA commands; no AWS contact, no EC2 start, no generation.

Latest S3 runtime infrastructure: `Plan/Instructions/Operations/Scripts/Initialize-S3RuntimeInfrastructure.ps1` initialized bucket `comfy-ui-main-runtime-029530099913-us-east-1`, EC2 runtime S3 access, GitHub OIDC deploy role, scheduler stop role, and local non-secret `.env` config while EC2 stayed stopped and no generation ran. Dry-run evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_DRY_RUN_20260706T175619-0500.json`; execute evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json`; readiness evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json`; operations helper evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_S3_RUNTIME_INFRA_20260706T175902-0500.json`. Result: `s3_runtime_infrastructure_ready`; readiness now `ready_local_only`; missing config is empty.

Latest S3 matrix publish: RealVisXL matrix bundle `rvxl_mx_s3_20260706T181144-0500` was uploaded to `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/rvxl_mx_s3_20260706T181144-0500/rvxl_mx_s3_20260706T181144-0500.zip` and download-verified with SHA256 `d3d81bbe2b6cb678304ab06ddf9cb707da31721cb01ca9c26df729414396cc84`. Evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_MATRIX_DEPLOY_BUNDLE_PUBLISH_EXECUTE_20260706T181217-0500.json` and `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_MATRIX_DEPLOY_BUNDLE_UPLOAD_VERIFY_20260706T181252-0500.json`. S3-backed quality plan: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_S3_PUBLISHED_20260706T181317-0500.json`; result `pass_local_only`, three samples, real S3 URI/SHA args, no EC2 start, no generation.

Latest pre-EC2 gates: auth `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_AWS_AUTH_GATE_MATRIX_QUALITY_20260706T182114-0500.json`, queue `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W66_RUNTIME_LANE_QUEUE_MATRIX_QUALITY_20260706T182114-0500.json`, model registry `Plan/Instructions/QA/Evidence/Model_Registry/W66_MODEL_REGISTRY_MATRIX_QUALITY_20260706T182114-0500.json`, and RealVisXL readiness `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LANE_RUNTIME_READINESS_REALVISXL_MATRIX_QUALITY_20260706T182127-0500.json` all pass for the S3-backed matrix quality window. Verified emergency stop schedule: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_EC2_EMERGENCY_STOP_MATRIX_STATIC_DIRECT_20260706T182233-0500.json`. Emergency-stop helper fix validation: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_EC2_EMERGENCY_STOP_HELPER_DRY_RUN_FIXED_20260706T182320-0500.json`.

Do not repeat the first-lane smoke path. `sdxl_low_risk_fallback_lane` already has EC2 static proof, bounded workflow smoke generation, SSM pullback, technical image QA, and visual QA with runtime-smoke notes.

The earlier RealVisXL pullback/QA blocker is resolved:

```text
RESOLVED-RUNTIME-REALVISXL-PULLBACK-QA-001
RealVisXL EC2 workflow smoke generation completed, generated artifacts were pulled back through the SSM SSH tunnel using comfyui-lora-key.pem, pullback hashes were verified, and technical plus visual image QA were recorded.
```

Current evidence:

```text
Plan/Instructions/QA/Evidence/Model_Registry/W63_EC2_REALVISXL_MODEL_INSTALL_20260706T125425-0500.json
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_LANE_RUNTIME_READINESS_REALVISXL_AFTER_STATIC_PROOF_20260706T132103-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_IMAGE_QA_TECHNICAL_REALVISXL_20260706T140027-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json
Plan/Instructions/QA/Evidence/Project_Readiness/W63_PROJECT_READINESS_REALVISXL_QA_COMPLETE_INDEX_REFRESH_20260706T141911-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_OPERATIONS_HELPER_S3_TRANSFER_READINESS_FINAL_20260706T142956-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_S3_RUNTIME_TRANSFER_READINESS_20260706T142504-0500.json
Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_GENERIC_MODEL_TYPES_20260706T144324-0500.json
Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_GENERIC_MODEL_TYPES_20260706T144332-0500.json
```

Next runtime work after the checkpoint:

1. Verify Wave 64 and Wave 65 coverage stay passing after any Items/Tracker/Plan change.
2. Verify AWS auth and Git clean/head only before an EC2 `-Execute` path.
3. Use the S3-backed matrix quality-run plan only after fresh auth/Git/readiness/static-proof/cost-control gates pass.
4. Do not rerun RealVisXL static proof or workflow smoke unless the lane, prompt, model, or EC2 runtime changed.
5. For image-quality certification, run the generated matrix quality-run plan only after auth/Git/readiness/cost-control gates pass, pull back every generated sample, and perform whole-image visual QA for all three samples rather than treating the single smoke output as final portfolio proof.
6. For audio/video expansion, require full-duration/whole-frame review in addition to target feature checks.
7. For runtime expansion, define the next lane/module and add it to the queue with local validation before any EC2 execution.

The model registry coverage gate is now dynamic and queue-driven. Before adding a third or later lane, update `runtime_lane_queue.json`, the lane `runtime_requirements.json`, `Plan/Registries/Models/model_registry.jsonl`, and `Plan/Registries/Models/model_runtime_validation_queue.csv`; then rerun `Test-WorkflowModelRegistryCoverage.ps1`. Current evidence `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_DYNAMIC_QUEUE_COVERAGE_20260706T143810-0500.json` proves the two currently queued lanes pass the dynamic gate.

The same gate now supports explicit non-checkpoint model types. Future Flux/Z-Image/Pony or other non-SDXL lanes should put `model_type` on each `required_models[]` entry and mirror that type in the model registry and runtime validation queue. Current evidence `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_GENERIC_MODEL_TYPES_20260706T144324-0500.json` proves the current two lanes pass after this generic model-type hardening.

Wave 63 cost-control defaults are active: use local/CI validation first, upload deploy bundles and model binaries to S3 before EC2 starts, use `-SkipGitLfsPull` unless the lane explicitly requires repository LFS payloads, set `-MaxEc2RuntimeMinutes`, prefer `-DeployBundleS3Uri` and `-DeployBundleSha256`, and do not run housekeeping on the EC2 clock.

Current cost-control helper inventory:

```text
tools/Start-LocalComfyUIDev.ps1
Plan/Instructions/Operations/Scripts/Publish-DeployBundleToS3.ps1
Plan/Instructions/Operations/Scripts/Install-EC2ModelFromS3.ps1
Plan/Instructions/Operations/Scripts/New-EC2EmergencyStopSchedule.ps1
Plan/Instructions/Operations/Scripts/Start-EC2InstanceStopWatchdog.ps1
configs/aws/
```

Validation evidence:

```text
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_OPERATIONS_HELPER_S3_TRANSFER_READINESS_FINAL_20260706T142956-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_S3_RUNTIME_TRANSFER_READINESS_20260706T142504-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json
```

Operations validation now includes the S3 runtime infrastructure dry-run smoke. S3 runtime transfer readiness is local-only and currently reports `ready_local_only`; the earlier `blocked_missing_s3_runtime_config` result is historical. The generated handoff smoke now requires S3 deploy-bundle, S3 model-install, emergency-stop instructions, and the no-rerun completed-smoke invariant. Do not rerun this validation unless the helper scripts, policy templates, S3/IAM config, or publish target changes.

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

Next exact action after committing this evidence: finish the Wave 63 cost-control checkpoint, run a final Git clean/head check, then choose the next lane/module or broader RealVisXL quality-certification objective intentionally. RealVisXL static proof, workflow smoke, pullback, and image QA already completed; do not rerun them unless the lane, prompt, model, runtime, or QA objective changed.

## Current cost-control update - 2026-07-06T12:45:00-05:00

The project now has an active EC2 cost-control path:

```text
Plan/Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md
tools/Test-LocalComfyUIDevPreflight.ps1
tools/New-EC2DeployBundle.ps1
.github/workflows/preflight-package.yml
Plan/Instructions/Waves/Wave63/WAVE63_SCOPE.md
```

Before any new EC2 `-Execute`, use local/CI validation while EC2 is stopped. Default EC2 helpers to `-SkipGitLfsPull`, prefer S3 bundles when available, and set `-MaxEc2RuntimeMinutes`. Do not rerun the completed low-risk lane or completed RealVisXL smoke just to re-prove them.

Current RealVisXL runtime status:

```text
Plan/Instructions/QA/Evidence/Model_Registry/W63_EC2_REALVISXL_MODEL_INSTALL_20260706T125425-0500.json
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_LANE_RUNTIME_READINESS_REALVISXL_AFTER_STATIC_PROOF_20260706T132103-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_IMAGE_QA_TECHNICAL_REALVISXL_20260706T140027-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json
```

RealVisXL model install, SHA256 verification, EC2 static proof, workflow smoke generation, pullback hash verification, and image QA are complete. The next action is checkpoint/advance or future S3 permission configuration, not another housekeeping pass, not model provisioning, not artifact recovery, and not a repeat generation.

Expected model:

```text
filename: realvisxlV50_v50Bakedvae.safetensors
source: Civitai model 139562, version 789646, RealVisXL V5.0 (BakedVAE)
expected_sha256: 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
```

Do not commit model binaries and do not use Git LFS as the model-provisioning path. For future model additions, prefer S3/model-cache and SHA256 verification. For the current RealVisXL smoke proof, pullback and image QA are complete; move to checkpoint/advance or S3 permission hardening for future runs.

Recommended local preparation for the next queued lane:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -AllowNonFirstLane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -RunPackageManifestFile <realvisxl-run-package-manifest>
```

Do not rerun bounded EC2 static proof after the model is already verified unless the lane files, checkpoint, runtime, or prompt changed:

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

Latest RealVisXL runtime handoff now imports `runtime_unblock_handoff`, `runtime_lane_queue`, model registry coverage, workflow smoke, pullback, image QA, S3 deploy-bundle guidance, S3 model-install guidance, and emergency-stop guidance. It records `result=handoff_runtime_smoke_qa_complete`, `command_step_count=16`, `markdown_written=true`, `ec2_started=false`, and `generation_executed=false`; use `Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json`.

Latest QA helper validation parses 10 QA scripts, runs 13 local smokes, includes authored-lane coverage, runtime lane queue, and model registry coverage smokes, and contract-checks runtime handoff, runtime queue, and model registry fields with 0 project-readiness contract failures. This confirms the `.env` GitHub/Civitai keys are not the blocker for EC2; AWS browser/SSO auth is still the runtime gate.

Latest runtime handoff command sequence now includes `runtime_lane_queue_recheck`, `model_registry_coverage_recheck`, `git_checkpoint_recheck`, `deploy_bundle_s3_publish`, `realvisxl_model_s3_install`, and `emergency_stop_schedule`. For the current RealVisXL smoke proof, model install/static proof/workflow smoke/pullback/image QA are already complete, so the next action is checkpoint/advance or future S3 permission hardening.

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
Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_FINAL_20260706T145923-0500.json
```

It proves both active SDXL lanes have checkpoint registry records, completed runtime-smoke queue rows, verified runtime-requirement hash/path status, and existing evidence paths for EC2 static proof, workflow smoke, pullback, and image QA. RealVisXL V5.0 metadata was fetched through the Civitai helper after fixing URL encoding, and the cached metadata confirms model id `139562`, version id `789646`, file `realvisxlV50_v50Bakedvae.safetensors`, and source SHA256 `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`. This does not download model binaries or create a new EC2 proof; it aligns local registry state with already-recorded proof evidence.

Model registry coverage is now an EC2 preflight gate. Immediately before any EC2 static proof attempt, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json
```

Expected result: `pass_local_only`, selected lane `sdxl_low_risk_fallback_lane` result `pass`, failed check count `0`, no AWS/GitHub API/Civitai/ComfyUI contact, `ec2_started=false`, and `generation_executed=false`.

Current static workflow validation also records generic required-model references:

```text
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_low_risk_fallback_lane_20260706T144819-0500.json
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_realvisxl_base_lane_20260706T144819-0500.json
Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_STATIC_GENERIC_MODEL_REFERENCES_20260706T144827-0500.json
```

When adding future non-SDXL lanes, set `required_models[].node_id` plus `input`, or `required_models[].node_class` plus `input`, so `Test-ComfyWorkflowStatic.ps1` can prove the workflow node actually references the required UNet, CLIP, VAE, LoRA, or other model asset. Checkpoint requirements can still use the `CheckpointLoaderSimple.ckpt_name` fallback.

Then route the pulled-back image to image QA:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```
