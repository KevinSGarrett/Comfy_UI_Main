# Current Pursuing Goal

## Active Wave
Wave 64 strict AI Items/Tracker end-to-end QA coverage plus Wave 65 exhaustive Plan source coverage closure, building on Wave 63 EC2 cost-control and Wave 61 runtime proof for queued lanes.

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
14. `C:\Comfy_UI_Main\Plan\Instructions\Waves\Wave64\WAVE64_SCOPE.md`
15. `C:\Comfy_UI_Main\Plan\Items\Waves\Wave64\WAVE64_STRICT_AI_COVERAGE_REQUIREMENTS.json`
16. `C:\Comfy_UI_Main\Plan\Tracker\Waves\Wave64\WAVE64_STRICT_AI_COVERAGE_REQUIREMENTS.json`
17. `C:\Comfy_UI_Main\Plan\Instructions\Waves\Wave65\WAVE65_SCOPE.md`
18. `C:\Comfy_UI_Main\Plan\Items\Waves\Wave65\WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json`
19. `C:\Comfy_UI_Main\Plan\Tracker\Waves\Wave65\WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json`

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
- Read Wave 64 Items/Tracker strict AI coverage before marking any project domain complete. Wave 64 rows require source citation file, section, line range, evidence, and strict whole-artifact visual/audio review when media exists.
- Read Wave 65 Plan source coverage closure before deciding the project plan is fully mapped. Wave 65 proves every current file under `C:\Comfy_UI_Main\Plan` has direct Items/Tracker source coverage. If any Plan file is added or renamed, rerun `Plan\Items\Scripts\generate_wave65_plan_source_coverage.py` before marking coverage complete.

## Current Status
The first queued runtime lane, `sdxl_low_risk_fallback_lane`, completed target EC2 static proof, one bounded package-fed workflow smoke generation, SSM pullback, technical image QA, and visual QA with runtime-smoke notes. Do not repeat that lane just to re-prove the same path.

The next queued runtime lane, `sdxl_realvisxl_base_lane`, has also completed RealVisXL model installation, SHA256 verification, EC2 static proof after install, one EC2 workflow smoke generation, generated artifact pullback, pullback hash verification, and technical plus visual image QA. Do not rerun this smoke proof unless the lane, prompt, model, or runtime changed, or the user explicitly asks for a broader multi-sample image-quality certification.

The local-first RealVisXL iteration path is now live too. `C:\Comfy_UI_Main\ComfyUI` is an ignored local checkout with CUDA Torch, the verified RealVisXL checkpoint is in ignored project model storage, local extra model paths are configured, `/object_info` passes, and a bounded 512x512/10-step local RealVisXL smoke generated one PNG with technical plus whole-image visual QA. Local evidence is `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_REALVISXL_SMOKE_EXECUTE_20260706T205501-0500.json` and `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_REALVISXL_SMOKE_IMAGE_QA_VISUAL_20260706T205650-0500.json`. This local proof is for low-cost iteration and does not replace EC2 target-runtime proof.

The next local-first lane is now locally proven: `sdxl_realvisxl_controlnet_canny_lane` / `MOD-17-CONTROLNET-CANNY-LANE`. The lane has been extracted from the Wave11/Main Flow Canny branch into Plan and exported `Workflows`, added as queue order 3, registered with model requirements, packaged as `runtime_artifacts/run_packages/sdxl_realvisxl_controlnet_canny_lane_static_package_v1/RUN_PACKAGE_MANIFEST.json`, statically validated, smoke-dry-run validated, and local object_info checked for ControlNet nodes plus model visibility. The SDXL Canny ControlNet small fp16 model is downloaded locally with SHA256 `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`; the control image input is prepared and hashed; bounded local generation produced one pulled-back PNG that passed technical QA and whole-image visual QA with notes. It remains blocked only from target-runtime certification until EC2 static proof, bounded EC2 generation, pullback, technical QA, and whole-image visual QA pass from a clean pushed head.

The W68 target-runtime preparation for the Canny lane is now locally complete and ready for checkpoint. Fresh AWS auth/account, profile matrix, model registry, runtime lane queue, S3 transfer readiness, and lane readiness evidence were generated for `sdxl_realvisxl_controlnet_canny_lane`. `Test-LaneRuntimeReadiness.ps1` was fixed so it selects current auth/profile/model-registry evidence instead of stale W60/W61-only files. `Install-EC2InputAssetFromS3.ps1` was added as a dry-run-by-default helper, and both the Canny ControlNet model and Canny input image were uploaded to S3 model-cache paths with SHA/size metadata verified by `head-object`. Latest Wave65 coverage after W68 reports `pass`, `plan_file_count=2987`, `wave65_rows_created=812`, and `missing_after_wave65_count=0`.

The W68 EC2 asset install step has also passed. An emergency stop schedule was created before the live window. The Canny ControlNet model was installed on EC2 at `/home/ubuntu/ComfyUI/models/controlnet/controlnet-canny-sdxl-1.0-small.safetensors` and SHA256-verified as `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`. The Canny input image was installed at `/home/ubuntu/ComfyUI/input/controlnet_canny_corrected_white_edges_black_bg.png` and SHA256-verified as `1af02b8bd12a9de394fbcc1becd72912f4604f843cb7e7a2fc80496835b8e9a5`. Both helpers verified EC2 final state `stopped`; no generation ran. Latest Wave65 after install evidence reports `pass`, `plan_file_count=2990`, `wave65_rows_created=815`, and `missing_after_wave65_count=0`.

The current live runtime blocker is AWS auth expiry before static proof. After install checkpoint `d766aaa`, clean Git still matched `origin/main`, but `aws sts get-caller-identity` returned expired session and the profile matrix found zero valid expected-account profiles. This blocks EC2 static proof and generation until AWS login/SSO is refreshed. It is not caused by the GitHub token, Civitai key, `.env`, `.git`, local model provisioning, S3 asset upload, or EC2 asset placement.

Latest local gate-contract hardening is complete. `Test-OperationsHelperStatic.ps1` now directly contract-checks the current W68 Canny auth/readiness/static-proof/workflow-smoke blocked-auth evidence. Evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_OPERATIONS_HELPER_W68_CANNY_GATE_CONTRACTS_20260707T011500-0500.json` reports `pass_local_only` with the new `controlnet_canny_w68_gate_contract` passing, EC2 not started, and generation not executed. Latest Wave65 after this evidence reports `pass`, `plan_file_count=3002`, `wave65_rows_created=827`, and `missing_after_wave65_count=0`.

Wave 63 cost controls are active:

- Local dev preflight: `tools\Test-LocalComfyUIDevPreflight.ps1`.
- Local dev startup: `tools\Start-LocalComfyUIDev.ps1`.
- Deploy bundle builder: `tools\New-EC2DeployBundle.ps1`.
- Deploy bundle S3 publisher: `Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1`.
- S3 runtime transfer readiness gate: `Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1`.
- EC2 model S3 installer: `Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1`.
- EC2 emergency stop scheduler: `Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1`.
- EC2 instance-side watchdog: `Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1`.
- GitHub Actions preflight/package workflow: `.github\workflows\preflight-package.yml`.
- EC2 helpers now support `-SkipGitLfsPull`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, and `-MaxEc2RuntimeMinutes`.
- Safe-to-commit AWS least-privilege policy templates are under `configs\aws`.
- EC2 should be used only for target-runtime facts, not for package/build/index housekeeping.

Wave 64 strict AI Items/Tracker coverage is active:

- Items: `Plan\Items\wave64_end_to_end_strict_ai_itemized_list.csv`.
- Tracker: `Plan\Tracker\wave64_end_to_end_strict_ai_tracker.csv`.
- Validation report: `Plan\Items\Reports\wave64_end_to_end_strict_ai_coverage_report.json`.
- Every localized visual/audio task must also pass whole-artifact review. A target region cannot pass if unrelated hands, face, body, lighting, background, contact, audio timing, voice, foley, ambience, mix, sync, or artifact defects exist elsewhere in the generated output.

Wave 65 exhaustive Plan source coverage closure is active:

- Items: `Plan\Items\wave65_plan_source_coverage_closure_itemized_list.csv`.
- Tracker: `Plan\Tracker\wave65_plan_source_coverage_closure_tracker.csv`.
- Validation report: `Plan\Items\Reports\wave65_plan_source_coverage_report.json`.
- Current result: `pass`, with every current file under `C:\Comfy_UI_Main\Plan` covered by baseline Items/Tracker rows or Wave65 closure rows.
- Wave65 rows are AI-only source execution controls. They do not mark implementation complete; each row still requires source reading, requirement extraction, implementation or blocker, tests, strict QA, whole-artifact media review when applicable, and evidence.

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
Plan/Instructions/QA/Evidence/Project_Readiness/W63_PROJECT_READINESS_REALVISXL_QA_COMPLETE_INDEX_REFRESH_20260706T141911-0500.json
Plan/Instructions/QA/Evidence/Runtime_Readiness/W63_RUNTIME_UNBLOCK_HANDOFF_REALVISXL_QA_COMPLETE_FINAL_20260706T140828-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_OPERATIONS_HELPER_S3_TRANSFER_READINESS_FINAL_20260706T142956-0500.json
Plan/Instructions/QA/Evidence/Operations_Static_Validation/W63_S3_RUNTIME_TRANSFER_READINESS_20260706T142504-0500.json
Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_S3_TRANSFER_READINESS_FINAL_20260706T143145-0500.json
```

The expected RealVisXL file is now present on EC2 and verified with SHA256 `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`. Model binaries must not be committed to Git. S3 runtime transfer readiness was later initialized with real bucket/IAM values and now passes locally; do not return to the stale missing-config blocker.

Model registry coverage is now queue-driven: `Test-WorkflowModelRegistryCoverage.ps1` reads `runtime_lane_queue.json`, so adding a third or later lane requires matching `runtime_requirements.json`, `model_registry.jsonl`, and `model_runtime_validation_queue.csv` coverage before EC2 readiness can pass. Current dynamic evidence is `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_DYNAMIC_QUEUE_COVERAGE_20260706T143810-0500.json`.

Model registry coverage also supports explicit required model types for future non-SDXL lanes. Evidence `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_GENERIC_MODEL_TYPES_20260706T144324-0500.json` proves the current lanes still pass while the helper now validates `required_models[].model_type` when present and falls back to `Checkpoint` only for checkpoint roles.

Static workflow validation now also supports generic required-model reference checks. Evidence `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_low_risk_fallback_lane_20260706T144819-0500.json`, `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_realvisxl_base_lane_20260706T144819-0500.json`, and `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_STATIC_GENERIC_MODEL_REFERENCES_20260706T144827-0500.json` prove the current two queued lanes pass with `model_reference_checks`; future non-checkpoint required models must provide `node_id`/`input` or `node_class`/`input` mappings.

Model registry state now matches completed runtime evidence for both active lanes. `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_FINAL_20260706T145923-0500.json` proves `model_registry.jsonl`, `model_runtime_validation_queue.csv`, and runtime requirements use completed smoke-proof statuses with existing evidence paths; `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_20260706T145931-0500.json` confirms the broader QA helper still passes locally.

Wave64 strict AI-operational coverage is present and validated. `Plan/Items/Reports/wave64_end_to_end_strict_ai_coverage_report.json` and `Plan/Tracker/Reports/wave64_end_to_end_strict_ai_coverage_report.json` report `pass` with 66 item rows, 66 tracker rows, and 28 required domains covered; this is coverage/control evidence, not completion evidence.

Wave65 exhaustive source coverage closure is present and validated. `Plan/Items/Reports/wave65_plan_source_coverage_report.json` and `Plan/Tracker/Reports/wave65_plan_source_coverage_report.json` report `pass`, every current `Plan` file is covered, and `missing_after_wave65_count=0`; current count is 2,851 Plan files covered by 676 Wave65 closure rows. This is source coverage/control evidence, not implementation completion evidence.

Wave64 image-engine routing is now enforced at run-package creation when `-RouteRequestFile` is supplied. `tools\New-WorkflowRunPackage.ps1` writes `router_decision.json`, records `route_gate` in `RUN_PACKAGE_MANIFEST.json`, and blocks lane mismatches. Evidence `Plan/Instructions/QA/Evidence/Run_Package/W66_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153601-0500.json` and QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153612-0500.json` both report `pass_local_only`; the compatible RealVisXL package passed and the intentional low-risk/RealVisXL mismatch was blocked without EC2 start or generation.

RealVisXL multi-sample image-quality certification is now locally prepared but not visually certified. `tools\New-WorkflowRunPackageMatrix.ps1` builds three router-gated packages from `PromptProfiles\base_generation\realvisxl_multisample_certification.matrix.json`; persistent matrix manifest is `runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json`; evidence `Plan/Instructions/QA/Evidence/Run_Package/W66_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155031-0500.json` and QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155048-0500.json` report `pass_local_only`. Completion still requires EC2 execution, pullback, hash verification, and whole-image visual QA for all three generated samples.

The RealVisXL multi-sample matrix also has a local-only deploy-bundle and S3 dry-run path. `tools\New-EC2DeployBundleMatrix.ps1` packages the matrix manifest, source matrix, prompt profiles, project context, and all three sample run packages into one ZIP; `Publish-DeployBundleToS3.ps1` now preserves `DEPLOY_BUNDLE_MATRIX_MANIFEST.json` as the S3 sidecar; EC2 static-proof and workflow-smoke helpers accept either single-package or matrix bundle manifests after extraction. Evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_EC2_DEPLOY_BUNDLE_MATRIX_S3_DRY_RUN_REDACTED_20260706T171921-0500.json`, QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_MATRIX_S3_DRY_RUN_REDACTED_20260706T171934-0500.json`, and operations helper evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_MATRIX_BUNDLE_MANIFEST_20260706T171309-0500.json` report `pass_local_only`. The bundle is preparation for future S3/EC2 quality execution, not final visual certification.

The RealVisXL multi-sample matrix now has a local-only bounded EC2 quality-run plan. `Plan\Instructions\Operations\Scripts\New-EC2WorkflowMatrixQualityRunPlan.ps1` validates the three matrix package manifests and emits one planned `Invoke-EC2WorkflowSmokeRun.ps1` command per sample with `-RunPackageManifestFile`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, `-SkipGitLfsPull`, and `-MaxEc2RuntimeMinutes`; it also emits per-sample pullback and whole-image QA commands. Evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_20260706T173124-0500.json`, QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json`, and operations helper evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json` report `pass_local_only`. This is still preparation: final certification requires real S3 publish, bounded EC2 generation, artifact pullback, hash verification, and whole-image QA for every sample.

S3 runtime transfer readiness is now backed by both a local-only config planner and real initialized AWS infrastructure. `Plan\Instructions\Operations\Scripts\Initialize-S3RuntimeInfrastructure.ps1` created/configured bucket `comfy-ui-main-runtime-029530099913-us-east-1`, attached `ComfyUIRuntimeS3Access`, created `ComfyUIGitHubDeployBundleRole` and `ComfyUIEmergencyStopSchedulerRole`, updated only non-secret local `.env` values, and kept EC2 stopped with no generation. Evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json` reports `s3_runtime_infrastructure_ready`; readiness evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json` reports `ready_local_only`; operations helper evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_S3_RUNTIME_INFRA_20260706T175902-0500.json` reports `pass_local_only`. After sample 1 evidence, Wave65 now covers 2,883 Plan files with 708 closure rows and zero missing.

RealVisXL matrix sample 1 is now generated, pulled back, hash-verified, and QA-reviewed. Fresh bundle `rvxl_mx_s3b_20260706T184054-0500` was download-verified from S3 with SHA256 `e1044e447abb548db5e834ba26c8376ba0a80ad463fadd5b969346edf30a3605`; fresh static proof passed in `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3_RETRY_20260706T184233-0500.json`; sample 1 runtime evidence is `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE1_20260706T185314-0500.json`; pullback evidence is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T185315-0500/PULLBACK_RECORD.json`; technical QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE1_IMAGE_QA_TECHNICAL_20260706T190410-0500.json`; visual QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE1_IMAGE_QA_VISUAL_20260706T190640-0500.json`. Samples 2 and 3 remain pending, so the matrix is not fully certified.

RealVisXL matrix sample 2 is now generated, pulled back, hash-verified, and QA-reviewed. Fresh bundle `rvxl_mx_s3c_20260706T191636-0500` was download-verified from S3 with SHA256 `74d1a8f9d18f78487c34c5dd96be5571fc6f82172ef4bcc0907032774bcd2aa9`; fresh static proof passed in `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3C_20260706T191804-0500.json`; sample 2 runtime evidence is `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE2_20260706T192734-0500.json`; pullback evidence is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T192734-0500/PULLBACK_RECORD.json`; technical QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE2_IMAGE_QA_TECHNICAL_20260706T193743-0500.json`; visual QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE2_IMAGE_QA_VISUAL_20260706T193800-0500.json`. Sample 3 remains pending, so the matrix is still not fully certified.

RealVisXL matrix sample 3 is now generated, pulled back, hash-verified, and QA-reviewed. Fresh bundle `rvxl_mx_s3d_20260706T194502-0500` was download-verified from S3 with SHA256 `b5ff8b371d80773654d0646d2c842ffd0a8fcee8722687b5a0e0fe76e696ebda`; fresh static proof passed in `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3D_20260706T194602-0500.json`; sample 3 runtime evidence is `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE3_20260706T195751-0500.json`; pullback evidence is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T195752-0500/PULLBACK_RECORD.json`; technical QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_IMAGE_QA_TECHNICAL_20260706T200751-0500.json`; visual QA is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_IMAGE_QA_VISUAL_20260706T200845-0500.json`. Final matrix certification is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json`; the bounded three-sample RealVisXL matrix is certified with notes.

## Next Exact Work
First, refresh AWS login/SSO for expected account `029530099913`, then rerun `Test-AwsAuthGate.ps1`, `Test-AwsProfileAuthMatrix.ps1`, and `Test-LaneRuntimeReadiness.ps1` for `sdxl_realvisxl_controlnet_canny_lane`. Do not start EC2 unless the auth gate reports `safe_to_start_ec2=true`.

Second, create/verify a fresh emergency stop schedule for the static-proof window, then run `Invoke-EC2LaneStaticProof.ps1` for `sdxl_realvisxl_controlnet_canny_lane` from a clean pushed head. Rerun lane readiness after static proof.

Third, run one bounded EC2 workflow smoke from `runtime_artifacts\run_packages\sdxl_realvisxl_controlnet_canny_lane_static_package_v1\RUN_PACKAGE_MANIFEST.json` only if static proof and readiness pass. Pull back artifacts, run technical image QA and whole-image visual QA, update tracker/evidence/hydration files, and certify only the lane result that actually passed.

Fourth, if broader image-quality certification becomes the explicit target instead, create a new multi-sample QA plan rather than rerunning already certified RealVisXL matrix samples.

Keep using the cost-control lane before any future generation attempt:

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
