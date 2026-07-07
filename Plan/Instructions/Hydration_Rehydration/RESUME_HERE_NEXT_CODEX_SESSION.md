# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then read `CURRENT_PURSUING_GOAL.md` and follow its required instruction read order for `Plan/Instructions`. Do not continue from this resume file alone. The current active runtime handoff is the W68 ControlNet Canny target-runtime sequence in `NEXT_ACTION.md`, not the old W61 low-risk handoff. The older `W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.md` Markdown is historical/corrupted.

## Latest W68 Canny v4 generation gate

- Active root remains `C:\Comfy_UI_Main`; do not switch to `C:\Comfy_UI`.
- The old no-`.git` blocker is stale for this root. `.git` exists and `origin/main` currently matches local `HEAD`, but the live worktree is dirty with local Canny QA/package/evidence changes.
- W68 Canny EC2 static proof passed: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W68_EC2_STATIC_PROOF_CANNY_DEPLOY_BUNDLE_BOM_FIX_20260707T034500-0500.json`.
- Fresh readiness after static proof reports `ready_for_generation=true`: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_LANE_RUNTIME_READINESS_CANNY_AFTER_STATIC_PROOF_20260707T012158-0500.json`.
- Canny v4 generation dry-run used the current v4 package and blocked before EC2 start only on `local_git_worktree_dirty`; no generation ran and EC2 was not started: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W68_EC2_WORKFLOW_SMOKE_CANNY_V4_GATE_DRY_RUN_20260707T012214-0500.json`.
- Built a local-only v4 deploy bundle from `runtime_artifacts/run_packages/sdxl_realvisxl_controlnet_canny_lane_clean_control_wardrobe_current_v4/RUN_PACKAGE_MANIFEST.json`: `runtime_artifacts/deploy_bundles/canny_v4_static_deploy_20260707T012255-0500/`.
- V4 bundle tracked evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_CANNY_V4_DEPLOY_BUNDLE_LOCAL_READY_20260707T012255-0500.json`; ZIP SHA256 `76cdfcf6fa3f1e4f80d2d6f67f657fa51512286b398b8496ca9cd074bbbb418f`, size `62877`.
- Do not start EC2 until the clean-head gate is satisfied. If Git checkpointing is allowed, make one minimal checkpoint for the Canny v4 local QA/package/evidence state, publish this v4 bundle or a clean-head successor to S3, rerun exactly one bounded v4 static proof, then run exactly one bounded v4 generation with pullback and strict QA.

## Latest W68 Canny deploy-bundle readiness

- Active root is `C:\Comfy_UI_Main`; the work must continue there, not in `C:\Comfy_UI`.
- Built a local-only Canny deploy bundle from the validated run package while AWS auth remained expired and EC2 stayed unused.
- Tracked evidence:
  - `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_CANNY_DEPLOY_BUNDLE_LOCAL_READY_20260707T020500-0500.json`
  - `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_CANNY_DEPLOY_BUNDLE_S3_PUBLISH_DRY_RUN_20260707T020600-0500.json`
- Bundle facts:
  - `bundle_id`: `canny_static_deploy_20260707T020500-0500`
  - `source_git_head`: `96c01860997344cdd449847aff551f35edea9908`
  - `bundle_zip_sha256`: `b9cd47466f761a86db61d48c02ef11f8b570f93dafe367662b80a7fc587b067c`
  - `bundle_zip_size_bytes`: `60317`
  - `s3_bundle_uri`: `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/canny-static-proof/canny_static_deploy_20260707T020500-0500/canny_static_deploy_20260707T020500-0500.zip`
  - `s3_manifest_uri`: `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/canny-static-proof/canny_static_deploy_20260707T020500-0500/DEPLOY_BUNDLE_MANIFEST.json`
- The actual bundle ZIP/content is ignored under `runtime_artifacts/deploy_bundles/` and must not be committed.
- No AWS contact, GitHub API contact, Civitai contact, ComfyUI contact, EC2 start, or generation occurred.
- Next: after AWS login/SSO refresh for account `029530099913`, rerun auth/profile/readiness. If safe, upload this exact bundle or a fresh clean-head successor with `Publish-DeployBundleToS3.ps1 -Execute`, verify SHA256, schedule emergency stop, and run Canny EC2 static proof with `-DeployBundleS3Uri` and `-DeployBundleSha256`.

## Latest W68 Canny current-queue checkpoint

- Active root is `C:\Comfy_UI_Main`. This directory already has `.git`, `.env`, `comfyui-lora-key.pem`, `Plan`, `Workflows`, `models`, and `ComfyUI`; do not recreate Git metadata and do not switch work to `C:\Comfy_UI`.
- Sensitive local files remain private and uncommitted: `.env`, `comfyui-lora-key.pem`, local model binaries, ignored local `ComfyUI`, and generated private runtime outputs.
- `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json` and `Workflows/base_generation/ACTIVE_LANES.json` now identify `sdxl_realvisxl_controlnet_canny_lane` as the current runtime lane while preserving target-runtime status as queued/pending EC2 proof.
- Canny local pre-EC2 proof evidence is attached to the queue record: local model provisioning, input asset manifest, object_info/model/input readiness, bounded local generation, whole-image visual QA, and operations gate-contract validation.
- New evidence:
  - `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W68_WORKFLOW_EXPORT_SYNC_CANNY_CURRENT_LANE_20260707T012500-0500.json`
  - `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W68_RUNTIME_LANE_QUEUE_CANNY_CURRENT_LOCAL_PROOF_20260707T012500-0500.json`
  - `Plan/Instructions/QA/Evidence/Model_Registry/W68_MODEL_REGISTRY_COVERAGE_CANNY_CURRENT_LOCAL_PROOF_20260707T013000-0500.json`
  - `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_LANE_RUNTIME_READINESS_CANNY_CURRENT_QUEUE_BLOCKED_AUTH_20260707T012500-0500.json`
  - `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_RUNTIME_UNBLOCK_HANDOFF_CANNY_CURRENT_QUEUE_BLOCKED_AUTH_20260707T013000-0500.json`
  - `Plan/Instructions/QA/Evidence/Project_Readiness/W68_PROJECT_READINESS_CANNY_CURRENT_QUEUE_WITH_HANDOFF_20260707T013500-0500.json`
  - `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W68_QA_HELPER_CANNY_CURRENT_QUEUE_CONTRACT_SYNC_20260707T014500-0500.json`
- The image-engine router now reads UTF-8-BOM JSON/JSONL files correctly. `New-RuntimeUnblockHandoff.ps1` now prefers auth/profile evidence selected by lane readiness. `Test-QAHelperStatic.ps1` now accepts the explicit `handoff_ready_runtime_blocked_auth` result in the `pass_local_ready_runtime_blocked` contract.
- Latest QA helper result is `pass_local_only`. No EC2 start and no generation occurred in this checkpoint.
- Current runtime blocker remains AWS auth only: the selected W68 AWS auth gate reports expired session, `safe_to_start_ec2=false`, and Canny lane readiness reports `ready_for_ec2_static_proof=false`.
- Immediate next action: rerun Wave65 source coverage after these new Plan evidence/hydration updates, validate JSON/CSV/PowerShell/Python, run secret/path scans, commit, push, and verify clean `HEAD == origin/main`. After the clean checkpoint, refresh AWS login/SSO for account `029530099913` before any EC2 static proof.

## Latest W68 Canny gate-contract checkpoint

- Active root is still `C:\Comfy_UI_Main`; `.git` exists and the old `BLOCKER-W59-GIT-001` no-`.git` statement is resolved/stale for this root. Do not recreate Git metadata and do not switch work to `C:\Comfy_UI`.
- Sensitive files exist locally and must remain unprinted/uncommitted: `C:\Comfy_UI_Main\.env` and `C:\Comfy_UI_Main\comfyui-lora-key.pem`.
- Hardened `Plan/Instructions/Operations/Scripts/Test-OperationsHelperStatic.ps1` so it directly selects and contract-checks the current W68 ControlNet Canny auth/readiness/static-proof/workflow-smoke gate evidence, not only older W60/W61 records.
- Evidence `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_OPERATIONS_HELPER_W68_CANNY_GATE_CONTRACTS_20260707T011500-0500.json` reports `pass_local_only`, 25 operations scripts parsed, local dry-run smokes passed, evidence contract failures 0, and `controlnet_canny_w68_gate_contract` result `pass`.
- The contract asserts the real current state: AWS session expired, remote login requires external noninteractive browser authorization, no auth URL was recorded, Canny local pre-EC2 readiness is true, EC2 static proof and workflow smoke are blocked before EC2 start, EC2 was not started, generation did not run, and the Canny run package is valid/lane-matched.
- Wave65 was rerun after the new evidence and reports `pass`, `plan_file_count=3002`, `wave65_rows_created=827`, `missing_after_wave65_count=0`.
- Immediate next action: validate, scan, commit, push, verify clean `HEAD == origin/main`; then refresh AWS login/SSO for account `029530099913`, rerun auth/profile/readiness gates, create a fresh emergency stop schedule, and run Canny EC2 static proof only if auth/readiness gates allow it.

## Latest W68 checkpoint preparation

- Active root is `C:\Comfy_UI_Main`; `.git` exists and the old `BLOCKER-W59-GIT-001` no-`.git` statement is resolved/stale for this root. Do not recreate Git metadata and do not switch the project root to `C:\Comfy_UI`.
- Sensitive local files exist and must remain unprinted/uncommitted: `C:\Comfy_UI_Main\.env` and `C:\Comfy_UI_Main\comfyui-lora-key.pem`.
- W68 pre-EC2 gates passed for `sdxl_realvisxl_controlnet_canny_lane`: AWS auth, AWS profile matrix, model registry coverage, runtime lane queue, S3 transfer readiness, and lane runtime readiness. Evidence is under `Plan/Instructions/QA/Evidence/.../W68_*CONTROLNET_CANNY*`.
- `Plan/Instructions/Operations/Scripts/Test-LaneRuntimeReadiness.ps1` was fixed to select current auth/profile/model-registry evidence instead of stale W60/W61-only records. The failed stale-selector readiness record is preserved as evidence; the retest reports `ready_for_ec2_static_proof`.
- Added `Plan/Instructions/Operations/Scripts/Install-EC2InputAssetFromS3.ps1`, a dry-run-by-default helper that installs S3 input assets into `/home/ubuntu/ComfyUI/input` only with `-Execute`; dry-run evidence exists at `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_EC2_INPUT_ASSET_INSTALL_HELPER_DRY_RUN_20260706T222000-0500.json`.
- Uploaded and verified the ControlNet Canny runtime assets in S3 without starting EC2. Model: `s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/controlnet/controlnet-canny-sdxl-1.0-small.safetensors`, SHA256 `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`. Input: `s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/input-assets/controlnet_canny_corrected_white_edges_black_bg.png`, SHA256 `1af02b8bd12a9de394fbcc1becd72912f4604f843cb7e7a2fc80496835b8e9a5`. Evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_S3_CONTROLNET_CANNY_RUNTIME_ASSET_UPLOAD_20260706T222500-0500.json`.
- Latest Wave65 coverage after W68 passes: `plan_file_count=2987`, `wave65_rows_created=812`, `missing_after_wave65_count=0`.
- Local ComfyUI port 8188 is closed. EC2 `i-0560bf8d143f93bb1` is `stopped`, type `g5.xlarge`, IAM profile `ComfyUI-SSM-Profile`, volume `vol-0eb9b2c6d3d2706d6`, and public IP `null`.
- Immediate next action: validate, staged-file scan, commit, push, verify clean `HEAD == origin/main`; then create/verify emergency stop, install model/input on EC2 from S3, commit/push install evidence, run EC2 static proof, rerun readiness, execute one bounded EC2 workflow smoke, pull back artifacts, and complete technical plus whole-image visual QA.

## Latest W68 EC2 asset install

- After checkpoint `51e5fe9`, created emergency stop schedule evidence `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_EC2_EMERGENCY_STOP_CONTROLNET_CANNY_INSTALL_20260706T224000-0500.json`.
- Installed the Canny ControlNet model on EC2 from S3. Evidence `Plan/Instructions/QA/Evidence/Model_Registry/W68_EC2_CONTROLNET_CANNY_MODEL_INSTALL_20260706T224500-0500.json` reports `install_model_hash_verified`, command status `Success`, remote path `/home/ubuntu/ComfyUI/models/controlnet/controlnet-canny-sdxl-1.0-small.safetensors`, SHA256 `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`, final EC2 state `stopped`, and `generation_executed=false`.
- Installed the Canny LoadImage input asset on EC2 from S3. Evidence `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_EC2_CONTROLNET_CANNY_INPUT_ASSET_INSTALL_20260706T225500-0500.json` reports `input_asset_hash_verified`, command status `Success`, remote path `/home/ubuntu/ComfyUI/input/controlnet_canny_corrected_white_edges_black_bg.png`, SHA256 `1af02b8bd12a9de394fbcc1becd72912f4604f843cb7e7a2fc80496835b8e9a5`, final EC2 state `stopped`, and `generation_executed=false`.
- Latest Wave65 coverage after install evidence passes: `plan_file_count=2990`, `wave65_rows_created=815`, `missing_after_wave65_count=0`.
- Immediate next action: validate, staged-file scan, commit, push, verify clean `HEAD == origin/main`, create a fresh emergency stop schedule for static proof, then run `Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_controlnet_canny_lane -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -Execute`.

## Current W68 runtime blocker

- After pushing install checkpoint `d766aaa`, clean Git still matched `origin/main`, but AWS auth expired before static proof. The default auth gate reports `blocked_expired_session`, and the profile matrix reports `blocked_no_valid_profile` with 0 of 15 profiles authenticating to expected account `029530099913`.
- Evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_PROFILE_AUTH_MATRIX_CONTROLNET_CANNY_STATIC_RECHECK_20260706T231000-0500.json` and `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_RECHECK_BLOCKED_20260706T231000-0500.json`.
- This is not a GitHub token, Civitai key, `.env`, `.git`, local model, S3 upload, or EC2 asset-placement blocker. The Canny model/input are already installed and hash-verified on EC2.
- Latest local hardening evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_20260707T001000-0500.json` reports `remote_login_status=external_authorization_required_noninteractive`, `auth_url_recorded=false`, `safe_to_start_ec2=false`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_LANE_RUNTIME_READINESS_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_20260707T001500-0500.json` reports local pre-EC2 readiness true but static proof/generation blocked by auth.
- Immediate next action: refresh AWS login/SSO for expected account `029530099913`, rerun auth/profile/lane-readiness gates, create a fresh emergency stop schedule, then run Canny EC2 static proof from clean pushed head.

## Current session completed

- Provisioned and locally runtime-proved `sdxl_realvisxl_controlnet_canny_lane` after the earlier static extraction checkpoint. Downloaded `controlnet-canny-sdxl-1.0-small.safetensors` from Hugging Face into ignored `models\controlnet`, recorded SHA256 `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`, and updated the model registry/runtime validation queue.
- Updated `config\comfyui_extra_model_paths.yaml` so local ComfyUI can see project `controlnet` models, then proved `/object_info` sees both `realvisxlV50_v50Bakedvae.safetensors` and `controlnet-canny-sdxl-1.0-small.safetensors` at `Plan/Instructions/QA/Evidence/Runtime_Readiness/W67_LOCAL_OBJECT_INFO_CONTROLNET_CANNY_MODEL_INPUT_20260706T215000-0500.json`.
- Generated `controlnet_canny_corrected_white_edges_black_bg.png` from the previous local RealVisXL smoke image, placed it in `ComfyUI\input`, and stored a tracked evidence copy plus manifest under `Plan\Instructions\Operations\Prepared_Input_Assets\controlnet_canny_input_20260707T000000-0500\`.
- Ran bounded local generation through `tools\Invoke-LocalComfyUIRunPackageSmoke.ps1` using `runtime_artifacts\run_packages\sdxl_realvisxl_controlnet_canny_lane_static_package_v1\RUN_PACKAGE_MANIFEST.json`. Runtime evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W67_LOCAL_CONTROLNET_CANNY_RUN_PACKAGE_EXECUTE_20260706T215500-0500.json` reports `pass_local_run_package_generation_smoke`, one output image, helper-started ComfyUI stopped, and port closed.
- Generated image: `Plan/Instructions/Operations/Pulled_Back_Artifacts/controlnet_canny_local_bounded_smoke_v1_20260706T215500-0500/images/codex_sdxl_realvisxl_controlnet_canny_smoke_00001_.png`, SHA256 `3d862c177370c2ebc8b9b6e11f5bec6071b504dff02abe7a28b722c6b72d3644`. Technical QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W67_LOCAL_CONTROLNET_CANNY_IMAGE_QA_TECHNICAL_20260706T215800-0500.json`; whole-image visual QA passed with local-smoke notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W67_LOCAL_CONTROLNET_CANNY_IMAGE_QA_VISUAL_20260706T220000-0500.json`.
- Remaining Canny lane boundary: local iteration is unblocked, but EC2 target-runtime proof is still pending. Before any EC2 `-Execute`, checkpoint/push, verify clean Git head, rerun fresh AWS auth/cost gates, and then run lane-specific EC2 static proof, bounded generation, pullback, technical QA, and whole-image visual QA.

- Selected and extracted the next local-first lane/module: `MOD-17-CONTROLNET-CANNY-LANE` as `sdxl_realvisxl_controlnet_canny_lane`. Selection evidence is `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W66_NEXT_LANE_MODULE_SELECTION_CONTROLNET_CANNY_20260706T212030-0500.json`.
- Added concrete Plan lane files under `Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_realvisxl_controlnet_canny_lane\` and exported runtime-facing copies under `Workflows\base_generation\sdxl_realvisxl_controlnet_canny_lane\`.
- Updated `Workflows\base_generation\ACTIVE_LANES.json` and `Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json` so the Canny lane is queue order 3 with status `queued`, not runtime-proven.
- Added queued model registry and runtime-validation rows for the Canny lane: RealVisXL checkpoint reuse for this lane and missing `models\controlnet\controlnet-canny-sdxl-1.0-small.safetensors`.
- Created local run package `runtime_artifacts\run_packages\sdxl_realvisxl_controlnet_canny_lane_static_package_v1\RUN_PACKAGE_MANIFEST.json`; result `pass_local_only`, 10 workflow nodes, 18 patched inputs, no EC2 start, no ComfyUI contact, no generation.
- Static validation passed at `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_WORKFLOW_STATIC_VALIDATION_SDXL_REALVISXL_CONTROLNET_CANNY_20260706T212030-0500.json`; dry-run `/prompt` construction passed at `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_WORKFLOW_SMOKE_DRY_RUN_SDXL_REALVISXL_CONTROLNET_CANNY_20260706T212030-0500.json`.
- Local ComfyUI `/object_info` check passed for `ControlNetLoader`, `LoadImage`, `ControlNetApplyAdvanced`, and the base SDXL nodes at `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_OBJECT_INFO_CONTROLNET_CANNY_NODES_20260706T212030-0500.json`; local process was stopped.
- Model registry coverage now passes for 3 lanes / 4 model rows at `Plan/Instructions/QA/Evidence/Model_Registry/W66_MODEL_REGISTRY_CONTROLNET_CANNY_QUEUE_20260706T212030-0500.json`; authored-lane coverage passes for 3 lanes at `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W66_AUTHORED_LANE_EVIDENCE_COVERAGE_CONTROLNET_CANNY_20260706T212030-0500.json`; runtime lane queue retest passes at `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W66_RUNTIME_LANE_QUEUE_CONTROLNET_CANNY_RETEST_20260706T212030-0500.json`.
- Active blocker for this lane: `models\controlnet\controlnet-canny-sdxl-1.0-small.safetensors` is not present, and `controlnet_canny_corrected_white_edges_black_bg.png` has not yet been proven in the active ComfyUI input directory. Do not claim runtime proof, generated artifact QA, or promotion until model metadata/SHA256, input placement, generation, pullback/hash evidence, technical image QA, and whole-image visual QA are complete.

- Completed local ComfyUI CUDA/model/object-info readiness. New helper `tools\Initialize-LocalComfyUIPythonEnv.ps1` created ignored venv `C:\Comfy_UI_Main\ComfyUI\.venv` and installed CUDA Torch/ComfyUI requirements. Evidence `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_PYTHON_ENV_EXECUTE_20260706T203510-0500.json` reports `torch 2.11.0+cu128`, CUDA `12.8`, and RTX 5060 available.
- Downloaded RealVisXL version `789646` from Civitai to ignored local path `C:\Comfy_UI_Main\models\checkpoints\realvisxlV50_v50Bakedvae.safetensors`; evidence `Plan/Instructions/QA/Evidence/Model_Registry/W66_LOCAL_REALVISXL_MODEL_DOWNLOAD_20260706T204500-0500.json` reports exact expected bytes and SHA256 match. Do not commit this binary.
- Hardened local preflight `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_DEV_PREFLIGHT_FULL_READY_20260706T204500-0500.json` now reports `pass_local_gpu_generation_candidate`: CUDA Torch true, required RealVisXL model present, selected-lane static validation pass, and failed check count `0`.
- Local object-info smoke `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_OBJECT_INFO_SMOKE_20260706T204800-0500.json` reports 791 local ComfyUI nodes and all required RealVisXL workflow nodes present. The local ComfyUI process was stopped. EC2 remains required for target-runtime proof.
- Completed a bounded local RealVisXL generation smoke. Added `config\comfyui_extra_model_paths.yaml`, added profile `PromptProfiles\base_generation\realvisxl_local_bounded_smoke.json`, built package `runtime_artifacts\run_packages\realvisxl_local_bounded_smoke_v1\RUN_PACKAGE_MANIFEST.json`, started local ComfyUI with CUDA/low-VRAM settings and the extra model paths config, posted the package prompt request, generated one 512x512 PNG, and stopped the local process.
- Local smoke runtime evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_REALVISXL_SMOKE_EXECUTE_20260706T205501-0500.json` reports `pass_local_generation_smoke`, prompt id `f2a001ac-3ce7-4639-ae52-85d8a67cc75e`, one output image, local process stopped, and port closed. Pullback evidence is `Plan/Instructions/Operations/Pulled_Back_Artifacts/local_comfyui_realvisxl_smoke_20260706T205501-0500/LOCAL_ARTIFACT_MANIFEST.json`.
- Local generated image is `Plan/Instructions/Operations/Pulled_Back_Artifacts/local_comfyui_realvisxl_smoke_20260706T205501-0500/images/codex_realvisxl_local_bounded_smoke_00001_.png`, SHA256 `a3b1527fcd3223fbb55cfc51434ff9b7495318ec79cfcb2f1ca48b0184881ec8`.
- Local smoke technical QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_REALVISXL_SMOKE_IMAGE_QA_TECHNICAL_20260706T205600-0500.json`; whole-image visual QA passed with local-smoke notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_REALVISXL_SMOKE_IMAGE_QA_VISUAL_20260706T205650-0500.json`. This is local iteration proof only, not EC2 target-runtime proof or final portfolio certification.
- Wave65 was rerun after local smoke generation and QA evidence and now reports `plan_file_count=2939`, `wave65_rows_created=764`, and `missing_after_wave65_count=0`.
- Added reusable local run-package helper `tools\Invoke-LocalComfyUIRunPackageSmoke.ps1`. Dry-run evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_RUN_PACKAGE_HELPER_DRY_RUN_20260706T210826-0500.json` validates package lane/hash/local root without ComfyUI contact. Execute evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_RUN_PACKAGE_HELPER_EXECUTE_20260706T210854-0500.json` proves the helper starts local ComfyUI, posts the bounded RealVisXL package, copies one PNG into project evidence, and stops the local process.
- Helper-produced image is `Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_local_bounded_smoke_v1_20260706T210854-0500/images/codex_realvisxl_local_bounded_smoke_00002_.png`, SHA256 `a3b1527fcd3223fbb55cfc51434ff9b7495318ec79cfcb2f1ca48b0184881ec8`. Technical QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_RUN_PACKAGE_HELPER_IMAGE_QA_TECHNICAL_20260706T210930-0500.json`; visual QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_RUN_PACKAGE_HELPER_IMAGE_QA_VISUAL_20260706T211000-0500.json`.
- Wave65 was rerun after helper evidence and now reports `plan_file_count=2946`, `wave65_rows_created=771`, and `missing_after_wave65_count=0`.
- Advanced the local-first runtime path after matrix certification. Added `tools\Initialize-LocalComfyUICheckout.ps1`, added `.gitignore` rules so `ComfyUI/` and portable ComfyUI folders remain external/uncommitted, and created a local ComfyUI checkout at `C:\Comfy_UI_Main\ComfyUI` from `https://github.com/comfyanonymous/ComfyUI.git`, head `7747c342d4143f35e7c8031dddf3ee4455f10a2e`.
- Local ComfyUI bootstrap evidence: dry run `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_CHECKOUT_BOOTSTRAP_DRY_RUN_20260706T202204-0500.json`; execute `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_CHECKOUT_BOOTSTRAP_EXECUTE_20260706T202500-0500.json`.
- Local CLI smoke evidence `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_CLI_SMOKE_AFTER_BOOTSTRAP_20260706T202600-0500.json` records `python C:\Comfy_UI_Main\ComfyUI\main.py --help` exit `0` and Torch import with `2.12.1+cpu`, CUDA false.
- Hardened local preflight evidence `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_DEV_PREFLIGHT_AFTER_BOOTSTRAP_HARDENED_20260706T202700-0500.json` reports local RTX 5060 Laptop GPU present, ComfyUI `main.py` found, selected RealVisXL lane static validation pass, but local GPU generation pending CUDA-enabled Torch and local RealVisXL checkpoint placement. Do not commit `C:\Comfy_UI_Main\ComfyUI` or model binaries.
- Completed RealVisXL matrix sample 3 from `runtime_artifacts/run_packages/realvisxl_multisample_certification_v1_realvisxl_environment_lowlight_v1/RUN_PACKAGE_MANIFEST.json` using fresh clean-head S3 bundle `rvxl_mx_s3d_20260706T194502-0500`, SHA256 `b5ff8b371d80773654d0646d2c842ffd0a8fcee8722687b5a0e0fe76e696ebda`.
- Sample 3 static proof passed at `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3D_20260706T194602-0500.json`; runtime evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE3_20260706T195751-0500.json` reports `workflow_smoke_generation_complete`, prompt id `1683210b-6159-41a6-9ea7-c171e7e84880`, S3 sync success, pullback record creation, and EC2 final state `stopped`.
- Sample 3 generated image is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T195752-0500/images/9_codex_realvisxl_cert_environment_lowlight_00001_.png`; pullback `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T195752-0500/PULLBACK_RECORD.json` reports `pullback_hashes_verified` and completed QA evidence.
- Sample 3 technical QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_IMAGE_QA_TECHNICAL_20260706T200751-0500.json`; visual QA passed with notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_IMAGE_QA_VISUAL_20260706T200845-0500.json`; pullback artifact QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE3_PULLBACK_ARTIFACT_QA_20260706T200855-0500.json`.
- Final RealVisXL matrix certification is `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json`; it certifies the bounded three-sample RealVisXL matrix with notes. This does not mark the whole project complete.
- Recovered from the stale S3 bundle block by building/publishing fresh RealVisXL matrix bundle `rvxl_mx_s3b_20260706T184054-0500` from clean pushed head `59d34ea1d1e057f628b160c4629fb1e5736bb4cf`, verifying uploaded/downloaded SHA256 `e1044e447abb548db5e834ba26c8376ba0a80ad463fadd5b969346edf30a3605`, and recording evidence at `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_MATRIX_DEPLOY_BUNDLE_PUBLISH_VERIFY_RETRY_20260706T190620-0500.json`.
- Retried S3-backed EC2 static proof successfully with the fresh bundle. Evidence `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3_RETRY_20260706T184233-0500.json` records required node availability, RealVisXL checkpoint path/hash proof, matching source head, generation false, and EC2 final state `stopped`.
- Executed RealVisXL matrix sample 1 from `runtime_artifacts/run_packages/realvisxl_multisample_certification_v1_realvisxl_closeup_skin_eye_v1/RUN_PACKAGE_MANIFEST.json`. Runtime evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE1_20260706T185314-0500.json` reports `workflow_smoke_generation_complete`, prompt id `3c0be6fd-274c-4a2d-bcc1-644be90fe22d`, one generated PNG, S3 sync success, pullback record creation, and EC2 final state `stopped`.
- Sample 1 generated image is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T185315-0500/images/9_codex_realvisxl_cert_closeup_skin_eye_00001_.png`; pullback record `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T185315-0500/PULLBACK_RECORD.json` reports `pullback_hashes_verified`.
- Sample 1 technical image QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE1_IMAGE_QA_TECHNICAL_20260706T190410-0500.json`; visual QA passed with notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE1_IMAGE_QA_VISUAL_20260706T190640-0500.json`; pullback artifact QA passed with nonblocking log notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE1_PULLBACK_ARTIFACT_QA_20260706T190700-0500.json`.
- Wave65 was rerun after sample 1 evidence and now reports `plan_file_count=2883`, `wave65_rows_created=708`, and `missing_after_wave65_count=0`.
- Hardened `Plan/Items/Scripts/generate_wave65_plan_source_coverage.py` so binary/media artifacts and control-heavy logs use safe citation summaries. This prevents generated CSVs from embedding raw PNG bytes or terminal control sequences after artifact pullback.
- Built/published fresh bundle `rvxl_mx_s3c_20260706T191636-0500` from clean head `d262a2ad3b81f7bc2be2949ab5197b98c79e604f`, verified SHA256 `74d1a8f9d18f78487c34c5dd96be5571fc6f82172ef4bcc0907032774bcd2aa9`, and passed fresh static proof at `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3C_20260706T191804-0500.json`.
- Executed RealVisXL matrix sample 2 from `runtime_artifacts/run_packages/realvisxl_multisample_certification_v1_realvisxl_three_quarter_hands_fabric_v1/RUN_PACKAGE_MANIFEST.json`. Runtime evidence `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_SAMPLE2_20260706T192734-0500.json` reports `workflow_smoke_generation_complete`, one generated hands/fabric PNG, successful S3 sync, pullback record creation, and EC2 final state `stopped`.
- Sample 2 generated image is `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T192734-0500/images/9_codex_realvisxl_cert_hands_fabric_00001_.png`; technical QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE2_IMAGE_QA_TECHNICAL_20260706T193743-0500.json`; visual QA passed with minor hand-contact notes at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE2_IMAGE_QA_VISUAL_20260706T193800-0500.json`; pullback artifact QA passed at `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_SAMPLE2_PULLBACK_ARTIFACT_QA_20260706T193810-0500.json`.
- Wave65 was rerun after sample 2 evidence and now reports `plan_file_count=2901`, `wave65_rows_created=726`, and `missing_after_wave65_count=0`.
- Initialized S3/IAM runtime infrastructure from `C:\Comfy_UI_Main`: added `Plan/Instructions/Operations/Scripts/Initialize-S3RuntimeInfrastructure.ps1`, created/configured bucket `comfy-ui-main-runtime-029530099913-us-east-1`, attached `ComfyUIRuntimeS3Access` to `ComfyUI-SSM-Role`, created `ComfyUIGitHubDeployBundleRole`, created `ComfyUIEmergencyStopSchedulerRole`, updated only non-secret local `.env` values, and kept EC2 `stopped` with no generation.
- Current S3 evidence: dry run `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_DRY_RUN_20260706T175619-0500.json`; execute `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json`; readiness `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json`; operations helper `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_S3_RUNTIME_INFRA_20260706T175902-0500.json`. Readiness now reports `ready_local_only`; the old missing-S3-config blocker is historical.
- Published and SHA-verified the RealVisXL matrix deploy bundle in S3. Uploaded bundle: `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/rvxl_mx_s3_20260706T181144-0500/rvxl_mx_s3_20260706T181144-0500.zip`; SHA256: `d3d81bbe2b6cb678304ab06ddf9cb707da31721cb01ca9c26df729414396cc84`. Evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_MATRIX_DEPLOY_BUNDLE_UPLOAD_VERIFY_20260706T181252-0500.json`.
- Prepared the S3-backed matrix quality EC2 window with fresh auth, queue, model registry, and RealVisXL readiness evidence, and created a verified EventBridge Scheduler emergency stop. Also fixed `New-EC2EmergencyStopSchedule.ps1` after detecting Windows CLI quoting and long schedule-name issues. Evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LANE_RUNTIME_READINESS_REALVISXL_MATRIX_QUALITY_20260706T182127-0500.json` and `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_EC2_EMERGENCY_STOP_MATRIX_STATIC_DIRECT_20260706T182233-0500.json`.
- Ran a bounded S3-backed RealVisXL matrix static-proof attempt. EC2 started and stopped safely, but the remote helper rejected the uploaded bundle because its source head `27111d0c606336e5c67c529228e11703974b02e7` did not match current `origin/main` `ce4487f5cfbd72448e5bec1d3191d076ec4d97af`. Evidence: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W66_EC2_STATIC_PROOF_REALVISXL_MATRIX_S3_20260706T182817-0500.json`.
- Wave65 was rerun after S3 matrix publish, pre-EC2 gate evidence, and stale-bundle static-proof evidence and now reports `plan_file_count=2866`, `wave65_rows_created=691`, and `missing_after_wave65_count=0`.
- Implemented Wave64 image-engine router proof for `TRK-W64-009` / `ITEM-W64-009` in `C:\Comfy_UI_Main`. New resolver: `Plan/07_IMPLEMENTATION/scripts/resolve_wave64_image_engine_route.py`; QA wrapper: `Plan/Instructions/QA/Scripts/Test-ImageEngineRouter.ps1`; example requests: `Plan/09_EXAMPLES/wave64_image_engine_route_realvisxl_request.example.json` and `Plan/09_EXAMPLES/wave64_image_engine_route_incompatible_lora_request.example.json`.
- Post-ledger router evidence `Plan/Instructions/QA/Evidence/Engine_Router/W64_IMAGE_ENGINE_ROUTER_VALIDATION_POST_LEDGER_20260706T151800-0500.json` reports `pass_local_only`: compatible RealVisXL SDXL routing selects `sdxl_realvisxl_base_lane`; incompatible Flux LoRA on SDXL blocks with no silent fallback. Latest decision evidence: `Plan/Instructions/QA/Evidence/Engine_Router/W64_IMAGE_ENGINE_ROUTER_REALVISXL_DECISION_20260706T152201-0500.json` and `Plan/Instructions/QA/Evidence/Engine_Router/W64_IMAGE_ENGINE_ROUTER_INCOMPATIBLE_LORA_DECISION_20260706T152201-0500.json`.
- Integrated the router proof into the QA helper. Post-ledger QA evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W64_QA_HELPER_IMAGE_ENGINE_ROUTER_POST_LEDGER_20260706T151800-0500.json` reports `pass_local_only` with local smoke failures `0`. Wave64 supplements, `PROJECT_ROOT_MANIFEST.json`, `QA_EVIDENCE_INDEX.md`, `PROOF_OF_MOVEMENT_LOG.csv`, `CURRENT_SESSION_STATE.md`, `NEXT_ACTION.md`, and `RECENT_DECISIONS.md` were updated for the router gate.
- Post-login runtime proof completed for the first queued lane `sdxl_low_risk_fallback_lane`: AWS auth passed for account `029530099913`; EC2 static proof passed; bounded workflow smoke generated one hyperreal editorial portrait from run package `runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/RUN_PACKAGE_MANIFEST.json`; EC2 final state was verified `stopped`; artifacts were pulled back through SSM chunk transfer after S3 role permissions and SSH port 22 blocked faster routes; pullback hashes verified; technical image QA passed; visual QA passed with notes for runtime-smoke purposes. Current evidence includes `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_POST_LOGIN_RETEST_20260706T104311-0500.json`, `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_POST_STATIC_PROOF_RETEST_20260706T110424-0500.json`, `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/PULLBACK_RECORD.json`, and `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_VISUAL_20260706T122027-0500.json`.
- Completed Wave 59-62 local static/package validation and cumulative zip validation.
- Initialized and pushed GitHub `main`.
- Passed GitHub API, AWS/EC2 identity, EBS volume, and Civitai metadata readiness checks before AWS login expiry.
- Found EC2 ComfyUI at `/home/ubuntu/ComfyUI` with NVIDIA A10G.
- Synced project repo to `/home/ubuntu/Comfy_UI_Main`.
- Inventoried EC2 ComfyUI runtime and model folders at HEAD `aaca121739e55c42b49d5b2cbb2be3c593d0c9ab`.
- Stopped EC2 and verified final state `stopped`.
- Selected `sdxl_low_risk_fallback_lane` as the first bounded workflow execution candidate.
- Authored the selected lane workflow files under `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_low_risk_fallback_lane/`.
- Recorded lane-selection evidence and pending-runtime certification.
- Added local workflow static validation and EC2 static-proof helper scripts.
- Passed local static validation for the selected SDXL lane and recorded dry-run evidence for the EC2 proof helper.
- Added a bounded ComfyUI smoke helper and generated the patched `/prompt` request body for the selected SDXL lane without starting EC2 or running generation.
- Added an image artifact QA helper and generated a pending-artifact QA record/checklist for the future selected-lane smoke output.
- Added a secret-safe AWS auth gate helper and recorded redacted evidence that AWS remote browser authorization is still required before EC2 work can resume.
- Added an EC2 pullback record helper and generated pending-runtime dry-run evidence for post-generation artifact count/hash/QA routing.
- Added a selected-lane runtime readiness gate and recorded that local pre-EC2 readiness is true, while EC2 start and generation remain blocked by AWS auth/object-info/hash proof.
- Added a bounded EC2 workflow smoke-run coordinator and generated dry-run evidence plus a patched request body showing it refuses EC2 start/generation while auth/static proof gates are missing.
- Reran selected-lane readiness with the coordinator included in helper parser validation; local pre-EC2 readiness remains true and runtime remains blocked by auth/static proof.
- Tightened the EC2 static-proof helper so blocked `-Execute` calls write evidence before AWS identity checks or EC2 start.
- Generated gated static-proof dry-run evidence and blocked-execute evidence with `ec2_started=false`.
- Updated readiness and smoke-run coordinator static-proof discovery so dry-run and blocked-execute records are not treated as real object-info/path/hash proof.
- Added current operations helper static validation and recorded local-only evidence covering all 14 operations scripts, operation schema/template JSON, and the latest runtime gate evidence.
- Rechecked the stale `BLOCKER-W59-GIT-001` report and confirmed `C:\Comfy_UI_Main` already has `.git`, canonical `origin`, ignored/untracked `.env`, required GitHub/Civitai secret variable names, and local `main` matching `origin/main`.
- Refreshed the stale `BLOCKER-W59-GIT-001` recheck evidence at current HEAD `642aa73e3e456e7f7d2661eddf9e00e1e2493d44`; `ls-remote` passed, a no-prompt push dry-run reported `Everything up-to-date`, and `.env` remains ignored/untracked.
- Sanitized `Test-OperationsHelperStatic.ps1` evidence output so validation temp paths are redacted, then regenerated current operations helper validation evidence with all local checks passing.
- Hardened `Invoke-GitHubCheckpoint.ps1` with staged content secret scanning and added a non-mutating checkpoint dry-run to current operations helper validation; latest operations helper validation passes with 7 local smoke checks.
- Added current QA helper static validation and recorded local-only evidence covering all 5 QA scripts, QA schemas/templates, markdown templates, image QA dry-run/technical sample checks, and selected-lane workflow static validation smoke.
- Added current hydration helper static validation and recorded local-only evidence covering all 3 hydration scripts, hydration templates, session-state generation, and the actual cumulative Wave 58-62 zip validation.
- Regenerated current generated local indexes and recorded evidence that the newest operations, QA, and hydration helper/evidence files are discoverable in generated indexes.
- Added `Test-AwsProfileAuthMatrix.ps1`, reran AWS auth diagnostics, and recorded that the active default profile is expired and zero of 15 configured AWS CLI profiles currently authenticate to expected account `029530099913`.
- Reran current operations helper validation with the profile matrix helper included; 15 scripts parsed, 5 JSON schema/template files parsed, and 7 local-only smoke checks passed.
- Regenerated current generated local indexes after adding the profile matrix helper/evidence and recorded row-count/discovery/secret-scan evidence.
- Updated selected-lane readiness to include AWS profile matrix diagnostics while keeping EC2 start gated by `Test-AwsAuthGate.ps1`.
- Reran selected-lane readiness: `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, `ready_for_generation=false`, auth failure category `expired_session`, profile count 15, expected-account matches 0.
- Reran current operations helper validation after the readiness update; 15 scripts parsed, 5 JSON schema/template files parsed, and 7 local-only smoke checks passed.
- Regenerated current generated local indexes after profile-aware readiness evidence and recorded row-count/discovery/secret-scan evidence.
- Added `Test-ItemsTrackerPackageStatic.ps1` and recorded current Items/Tracker package validation evidence: tracker rows 54695, item rows 54647, 5059/5059 source keys covered in both packages, zero missing source keys, zero bad human flags, zero bad citations, zero bad line rows.
- Reran current QA helper validation with the Items/Tracker package validation smoke included; 6 scripts parsed, 4 JSON schema/template files parsed, 4 markdown templates checked, and 6 local-only smoke checks passed.
- Regenerated current generated local indexes after Items/Tracker validation evidence and recorded row-count/discovery/secret-scan evidence: plan 2481, instructions 255, items 45, tracker 26.
- Reran current AWS auth/profile gates after the latest checkpoint: default auth remains `expired_session`, all 15 configured profiles were checked, zero profiles authenticate to expected account `029530099913`, and EC2/generation gates remain false.
- Reran selected-lane readiness against the fresh auth/profile evidence: `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, and `ready_for_generation=false`.
- Regenerated current generated local indexes after auth/profile/readiness recheck evidence and recorded row-count/discovery/secret-scan evidence: plan 2488, instructions 262, items 45, tracker 26.
- Hardened EC2 pullback manifest verification so `REMOTE_ARTIFACT_MANIFEST.json` is not counted as a pulled artifact, then reran current operations helper validation with 15 scripts, 5 JSON files, 8 local smoke checks, and zero local smoke failures.
- Hardened AWS auth gate evidence so `Test-AwsAuthGate.ps1` emits top-level `result`, `failure_category`, `account_match`, and `remote_login_status`; reran auth/profile/readiness gates without EC2 start; and passed operations helper validation with the auth evidence contract check.
- Regenerated current generated local indexes after auth-contract hardening and recorded row-count/discovery/secret-scan evidence: plan 2498, instructions 272, items 45, tracker 26.
- Hardened selected-lane readiness evidence so `Test-LaneRuntimeReadiness.ps1` emits top-level `result` and `failure_category`, carries auth summary fields, and passes operations validation with readiness evidence contract checks.
- Hardened EC2 static-proof and workflow-smoke coordinator evidence so blocked dry-run/execute records emit top-level gate summaries and prove `ec2_started=false` and `generation_executed=false` while AWS auth is blocked.
- Added EC2 coordinator evidence contract checks to the operations helper validator; latest operations helper validation has 4 evidence checks, 5 evidence-contract checks, and 0 failures.
- Added `Test-ProjectReadinessSnapshot.ps1`, wired it into current QA helper validation, retained the first failed snapshot as retest evidence, and passed the final local project readiness snapshot with `result=pass_local_ready_runtime_blocked_auth`, `local_ready=true`, `ec2_start_allowed=false`, and `generation_allowed=false`.
- Reran current QA helper validation with the project-readiness snapshot smoke included; 7 QA scripts parsed, 4 JSON schemas/templates parsed, 4 markdown templates checked, and 7 local-only smoke checks passed.
- Regenerated current generated local indexes after project-readiness snapshot evidence and recorded row-count/discovery/secret-scan evidence: plan 2531, instructions 305, items 45, tracker 26; final post-cert regeneration row counts are plan 2533, instructions 307, items 45, tracker 26.
- Removed literal token/private-temp scan patterns and token-like scan labels from `Test-ProjectReadinessSnapshot.ps1`, reran direct snapshot validation and QA helper validation, and passed the current scan-safe snapshot with 177 scanned files and 0 secret/private-path hits.
- Hardened `Test-QAHelperStatic.ps1` so project-readiness snapshot smoke must satisfy explicit contract checks, reran QA helper validation with 0 contract failures, and produced a current project readiness snapshot that still reports local-ready/runtime-blocked-auth while AWS auth is expired.
- Regenerated generated indexes after QA helper contract hardening and certified row-count parity plus discovery for the new QA validation, readiness snapshot, contract certification, and index refresh evidence.
- Added `New-RuntimeUnblockHandoff.ps1`, generated local-only JSON/Markdown handoff evidence with exact post-auth command sequence and EC2 safety gates, wired it into operations helper validation, and refreshed project readiness. Current handoff result is `handoff_ready_runtime_blocked_auth`; it records `aws_contacted=false`, `ec2_started=false`, and `generation_executed=false`.
- Regenerated generated indexes after runtime unblock handoff evidence/certification and certified row-count parity plus discovery for the new helper, handoff evidence, operations validation, readiness snapshot, and index evidence.
- Hardened project readiness and QA helper validation so `runtime_unblock_handoff` is now a required readiness input and QA contract-checks `local_only=true`, no AWS/GitHub API/Civitai contact, `ec2_started=false`, `generation_executed=false`, eight command steps, and Markdown output written.
- Reran direct project readiness and QA helper validation; the latest snapshot reports `pass_local_ready_runtime_blocked_auth`, the handoff summary reports `handoff_ready_runtime_blocked_auth`, and the QA helper reports `project_readiness_contract_failures=0`.
- Regenerated generated indexes after runtime handoff readiness contract hardening and certified row-count parity plus discovery for the updated QA scripts, readiness snapshot, QA validation evidence, contract certification, index evidence, and index certification.
- Added a local Git checkpoint gate to the EC2 static-proof and workflow-smoke coordinators. Future `-Execute` runs now require a clean worktree and local `HEAD == origin/main` before EC2 can start, and remote payloads verify the EC2 checkout reaches the expected pushed commit after `git pull --ff-only origin main`.
- Refreshed the runtime unblock handoff with a `git_checkpoint_recheck` command and safety invariant, then reran operations validation, runtime handoff evidence, QA helper validation, and project readiness.
- Verified the pushed EC2 Git checkpoint gate implementation with local `main` equal to `origin/main`, clean worktree, `git push --dry-run origin main` reporting `Everything up-to-date`, and `.env` remaining ignored/untracked; later evidence commits may advance the live checkpoint and must be rechecked before EC2.
- Added post-checkpoint Git recheck evidence/certification and refreshed generated index evidence so the current Git state is discoverable in project-owned QA evidence.
- Authored `sdxl_realvisxl_base_lane` as the second concrete local SDXL lane, generated static validation and smoke dry-run evidence, and updated the QA helper so it validates all authored base-generation lanes.
- Current RealVisXL lane status: local static validation passed, `/prompt` request dry-run built, `execution_allowed=false`, `generation_executed=false`, runtime proof pending AWS auth/EC2 object-info/checkpoint hash/output/QA.
- Hardened lane-runtime readiness after the second authored lane: `Test-LaneRuntimeReadiness.ps1` now selects static validation and smoke dry-run/request evidence by `LaneId`, and the EC2 static-proof/workflow-smoke coordinators default to lane-matched readiness/static-proof records.
- Current lane-specific readiness status: both `sdxl_low_risk_fallback_lane` and `sdxl_realvisxl_base_lane` report `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, and `ready_for_generation=false` while AWS auth remains expired.
- QA helper validation now includes lane-runtime readiness smokes for all authored base-generation lanes; latest result is `pass_local_only`, authored lane count 2, local smoke failures 0, and project-readiness contract failures 0.
- RealVisXL EC2 static-proof and workflow-smoke coordinator dry-runs remained blocked before EC2 start, confirmed readiness lane match for `sdxl_realvisxl_base_lane`, and kept `generation_executed=false`.
- Hardened project readiness and runtime unblock handoff after adding multiple authored lanes. `Test-ProjectReadinessSnapshot.ps1` now selects lane readiness, runtime handoff, and blocked coordinator evidence by `LaneId`; `New-RuntimeUnblockHandoff.ps1` now accepts `-LaneId` and writes explicit lane-specific command steps.
- Current low-risk project readiness retest reports `pass_local_ready_runtime_blocked_auth` and proves both `runtime_gates.lane_readiness.lane_match=true` and `runtime_gates.runtime_unblock_handoff.lane_match=true` for `sdxl_low_risk_fallback_lane`.
- Current lane-aware runtime handoff reports `handoff_ready_runtime_blocked_auth`, carries `sdxl_low_risk_fallback_lane`, and includes 9 command steps with explicit `-LaneId sdxl_low_risk_fallback_lane` on readiness/static-proof/workflow-smoke commands.
- QA helper validation now contract-checks the project-readiness lane match fields; latest result is `pass_local_only` with `project_readiness_contract_failures=0`.
- Added authored-lane evidence coverage validation. `Test-AuthoredLaneEvidenceCoverage.ps1` now verifies every concrete authored base-generation lane has lane-matched workflow static validation, workflow smoke dry-run/request body evidence, and lane runtime readiness evidence.
- Current authored-lane coverage passes for both `sdxl_low_risk_fallback_lane` and `sdxl_realvisxl_base_lane`: authored lane count 2, failed lane count 0, no AWS/GitHub API/Civitai/ComfyUI contact, no EC2 start, and no generation.
- QA helper validation now includes the authored-lane evidence coverage smoke: 8 QA scripts parsed, 11 local smokes passed, local smoke failures 0, authored lane count 2, project-readiness contract failures 0.
- Operations helper validation was rerun after the QA helper update and remains `pass_local_only`.
- Generated indexes were refreshed after authored-lane evidence coverage hardening: plan rows 2608, instructions rows 378, items rows 45, tracker rows 26, discovery missing 0, credential/private-path scan hits 0.
- Added runtime lane queue validation. `runtime_lane_queue.json` fixes `sdxl_low_risk_fallback_lane` as first EC2 proof/generation lane and queues `sdxl_realvisxl_base_lane` second for later RealVisXL checkpoint path/hash/load/output QA.
- Current runtime lane queue validation passes: `result=pass_local_only`, queued lane count 2, failed check count 0, first runtime lane `sdxl_low_risk_fallback_lane`, no AWS/GitHub API/Civitai/ComfyUI contact, no EC2 start, and no generation.
- QA helper validation now includes the runtime lane queue smoke: 9 QA scripts parsed, 12 local smokes passed, local smoke failures 0, authored lane count 2, project-readiness contract failures 0.
- Operations helper validation was rerun after runtime lane queue validation and remains `pass_local_only`.
- Generated indexes were refreshed after runtime lane queue validation: plan rows 2617, instructions rows 386, items rows 45, tracker rows 26, discovery missing 0, credential/private-path scan hits 0. A first ad hoc index probe failure caused by top-level JSON array wrapping was preserved and corrected on retest.
- Hardened project readiness and runtime unblock handoff so runtime lane queue evidence is a required local readiness/handoff input.
- Current queue-aware project readiness reports `pass_local_ready_runtime_blocked_auth`, selected queue order 1, `queue_allows_selected_lane_ec2_static_proof=true`, `ec2_start_allowed=false`, and `generation_allowed=false` while AWS auth remains expired.
- Current queue-aware runtime handoff reports `handoff_ready_runtime_blocked_auth`, selected queue order 1, command step count 10, includes `runtime_lane_queue_recheck`, and records `aws_contacted=false`, `ec2_started=false`, and `generation_executed=false`.
- QA helper validation now contract-checks the runtime lane queue gate in project readiness and passes with 9 QA scripts, 12 local smokes, 0 smoke failures, and 0 project-readiness contract failures.
- Operations helper validation now checks the runtime queue safety invariant in the runtime handoff smoke and remains `pass_local_only`.
- Added visible main-directory scaffold under `C:\Comfy_UI_Main`: `README.md`, `PROJECT_ROOT_MANIFEST.json`, `Workflows\base_generation\ACTIVE_LANES.json`, exported low-risk and RealVisXL workflow files under `Workflows\base_generation\`, and safe `models`, `configs`, and `runtime_artifacts` subfolders.
- Validated both exported top-level workflow lanes directly with `Test-ComfyWorkflowStatic.ps1`; both pass and all exported workflow/support files hash-match the validated Plan templates.
- Added root-level workflow tooling: `tools\Sync-WorkflowExports.ps1`, `tools\Test-RootProjectPreflight.ps1`, and `tools\New-WorkflowRunPackage.ps1`.
- Generated the first local run package for `sdxl_low_risk_fallback_lane` at `runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_20260706T081301-0500`. It contains `prompt_request.json`, copied lane files, static validation, smoke dry-run, and `RUN_PACKAGE_MANIFEST.json`; result is `pass_local_only`, `execution_allowed=false`, `ec2_started=false`, and `generation_executed=false`.
- Added prompt profile support to `tools\New-WorkflowRunPackage.ps1`, added `PromptProfiles\base_generation\hyperreal_editorial_portrait.json`, and generated `runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1`. The package applies `hyperreal_editorial_portrait_v1`, builds a concrete hyperreal portrait `prompt_request.json`, records `pass_local_only`, and keeps `ec2_started=false` plus `generation_executed=false`.
- Pushed runtime package commit `92ce3111145c9d4f16e7db9f5bbd648de4a7d138` to `origin/main`, verified local/remote refs matched, and saved post-push root preflight evidence at `runtime_artifacts\run_manifests\ROOT_LOCAL_PREFLIGHT_20260706T090734-0500.json` with failed check count `0`.
- Added `-RunPackageManifestFile` support to `Invoke-EC2WorkflowSmokeRun.ps1` and pushed commit `f99294bf5c85af65030e07c3016dbfc93d6ddcb8` to `origin/main`, so the first post-auth bounded workflow smoke can consume the verified hyperreal run package request.
- Generated package-fed EC2 workflow smoke dry-run evidence at `Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_HYPERREAL_PACKAGE_20260706T091711-0500.json`; it records local Git gate `pass`, `request_source=run_package`, `run_package.valid=true`, profile `hyperreal_editorial_portrait_v1`, `failure_category=expired_session`, `ec2_started=false`, and `generation_executed=false`.
- Added `-RunPackageManifestFile` support to `New-RuntimeUnblockHandoff.ps1` and pushed commit `f841b95822d64c31b9396ac0b7995646bd8fcb96`, so the generated post-auth handoff now includes the verified hyperreal package on the bounded workflow-smoke command.
- Generated package-aware runtime handoff evidence at `Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_RUNTIME_UNBLOCK_HANDOFF_HYPERREAL_PACKAGE_20260706T092429-0500.json` plus Markdown at `Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_RUNTIME_UNBLOCK_HANDOFF_HYPERREAL_PACKAGE_20260706T092429-0500.md`; it records `gate_summary.run_package.valid=true`, profile `hyperreal_editorial_portrait_v1`, prompt hash match `true`, command step count `10`, and `ec2_started=false` / `generation_executed=false`.
- Hardened selected-lane readiness, project readiness, runtime unblock handoff, QA helper validation, and operations helper validation so model registry coverage is now a required EC2 preflight gate.
- Generated model-registry-gated readiness evidence at `Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_MODEL_REGISTRY_GATE_20260706T094500-0500.json`; it records `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, `failure_category=expired_session`, and `model_registry_coverage.coverage_allows_selected_lane_ec2_static_proof=true`.
- Generated model-registry-gated project readiness at `Plan\Instructions\QA\Evidence\Project_Readiness\W61_PROJECT_READINESS_SNAPSHOT_MODEL_REGISTRY_GATE_20260706T094500-0500.json`; it records `pass_local_ready_runtime_blocked_auth`, `local_ready=true`, `ec2_start_allowed=false`, and `generation_allowed=false`.
- Generated current runtime handoff at `Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.json` plus Markdown at `Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.md`; it records command step count `11`, includes `model_registry_coverage_recheck`, keeps the hyperreal package argument, and still blocks on AWS auth with `ec2_started=false` / `generation_executed=false`.
- Pushed root preflight model-registry gate commit `2a1449601bc2d022fa5034fd2b5940f3ef3a474e` to `origin/main`.
- Reran root preflight from `C:\Comfy_UI_Main`; evidence `runtime_artifacts\run_manifests\ROOT_LOCAL_PREFLIGHT_MODEL_REGISTRY_GATE_20260706T101500-0500.json` reports `pass_local_only`, failed check count `0`, `.git` present, `HEAD == origin/main`, `.env` ignored, required root file structure present, active exported lanes static-valid, and model registry coverage passing for both active lanes.
- Refreshed generated indexes after the root preflight and operations validation evidence; latest parity is plan `2656`, instructions `421`, items `45`, tracker `26`, with index validation evidence `Plan\Instructions\QA\Evidence\Index_Validation\W59_LIVE_INDEX_REFRESH_ROOT_PREFLIGHT_MODEL_REGISTRY_GATE_20260706T101500-0500.json`.
- Hardened runtime unblock handoff Markdown generation and operations helper validation for generated handoff Markdown content; evidence `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W60_OPERATIONS_HELPER_CURRENT_VALIDATION_ROOT_PREFLIGHT_HANDOFF_MARKDOWN_20260706T101500-0500.json` reports `pass_local_only`, 16 scripts parsed, 10 local smokes, 0 smoke failures, and 0 evidence-contract failures.
- Reran current-head root preflight after pushed evidence commit `8bd059bdec2b2c8bd95a158930d2a26fa9d77b0a`; evidence `runtime_artifacts\run_manifests\ROOT_LOCAL_PREFLIGHT_CURRENT_HEAD_20260706T103000-0500.json` reports `pass_local_only`, failed check count `0`, `.git` present, `HEAD == origin/main`, `.env` ignored, active exported lanes static-valid, and model registry coverage passing.
- Confirmed again that `BLOCKER-W59-GIT-001` is stale/resolved. The remaining execution blocker is AWS browser/SSO auth expiry, not `.git`, GitHub token presence, or Civitai key presence.
- Clarified the runtime scope boundary: Wave42/Main Flow analysis and snapshots under `Plan` are source/staging context. The current executable surface is `Workflows\base_generation` simplified first-proof API lanes, not the full old `C:\Comfy_UI` workflow system or full Wave42/Main Flow graph.

## Current goal

Continue Wave 63 cost-controlled work without repeating the completed low-risk lane or the completed RealVisXL smoke proof. RealVisXL model install, static proof, workflow smoke, pullback hash verification, technical image QA, and visual image QA are done; keep EC2 only for new target-runtime facts that cannot be advanced locally or in CI.

## Next exact action

First finish the current Wave66 reusable-local-helper checkpoint: rerun Wave65 after these new Plan evidence files, validate JSON/CSV/PowerShell parsing, run `git diff --check`, run a staged forbidden-path and secret scan, commit the helper script, helper evidence, helper artifact QA, and required tracker/hydration/Wave65 refresh files, push, and verify `HEAD == origin/main`.

After that, continue local-first from a clean pushed state. Preferred next work is either a small bounded local ComfyUI prompt/workflow iteration with technical plus whole-image QA, or defining the next lane/module from Main Flow/Wave42 source context with local validation, registry coverage, queue updates, run package creation, and deploy-bundle creation while EC2 stays stopped.

Read `Plan/Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md` before any EC2 decision. If the current Wave 63/Wave64 changes are uncommitted, first create one clean checkpoint and verify `HEAD == origin/main`.

Do not rerun `sdxl_low_risk_fallback_lane` just to re-prove the same path. It already has EC2 static proof, generated smoke output, pullback, and image QA evidence.

The next queued runtime lane, `sdxl_realvisxl_base_lane`, has completed its single runtime smoke proof. Evidence:

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

Expected model:

```text
/home/ubuntu/ComfyUI/models/checkpoints/realvisxlV50_v50Bakedvae.safetensors
Civitai model 139562, version 789646, RealVisXL V5.0 (BakedVAE)
SHA256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80
```

The next runtime-unblocking action is not RealVisXL artifact recovery, not S3/IAM configuration planning, and not S3 bundle publishing. Do not commit the model binary and do not use Git LFS as a model-provisioning path. Do not rerun RealVisXL generation unless the lane, prompt, model, runtime, or QA objective changed. The next work should be fresh pre-EC2 gates followed by the S3-backed three-sample RealVisXL quality run, a new lane/module, or a user-approved broader multi-sample certification path.

The model registry coverage gate now derives active lanes from `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json` instead of a hardcoded two-lane list. Evidence `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_DYNAMIC_QUEUE_COVERAGE_20260706T143810-0500.json` and QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_DYNAMIC_MODEL_REGISTRY_COVERAGE_20260706T143818-0500.json` passed locally. Any future queued lane must have runtime requirements, model registry record(s), and model runtime validation queue rows before readiness can pass.

The registry gate now supports explicit required-model types for non-checkpoint assets. Evidence `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_GENERIC_MODEL_TYPES_20260706T144324-0500.json` and QA helper evidence `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_GENERIC_MODEL_TYPES_20260706T144332-0500.json` passed locally. Future Flux/Z-Image/Pony lanes should declare each asset type in `required_models[].model_type` and keep the registry/queue rows aligned.

Cost-control local/CI preparation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Start-LocalComfyUIDev.ps1 -ProjectRoot C:\Comfy_UI_Main -LocalComfyRoot <path-to-local-ComfyUI> -LowVram
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -AllowNonFirstLane
```

When a RealVisXL run package manifest exists, build the deploy bundle while EC2 is off:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -RunPackageManifestFile <realvisxl-run-package-manifest>
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>
```

For future model installs, make sure S3 permissions are in place using the placeholder templates under `configs/aws`, then upload checkpoints to an approved S3 model-cache prefix. The current RealVisXL checkpoint install is already complete, so this command is not the next action:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri s3://<bucket>/<model-cache-prefix>/realvisxlV50_v50Bakedvae.safetensors -ExpectedSha256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80 -MaxEc2RuntimeMinutes 20 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W63_EC2_REALVISXL_MODEL_INSTALL_<timestamp>.json
```

Before any future live EC2 window, create the cloud-side safety stop when the scheduler role exists:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -StopAfterMinutes 60 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_EMERGENCY_STOP_SCHEDULE_<timestamp>.json
```

Before any future EC2 `-Execute`, rerun AWS auth, queue, model registry, Git, and lane readiness gates. The account must be `029530099913`, `safe_to_start_ec2` must be `true`, the worktree must be clean, and local `HEAD` must equal `origin/main`.

Do not rerun RealVisXL static proof after the checkpoint is verified unless lane files, checkpoint, runtime, or prompt changed. If a future proof is required, prefer S3 deploy bundles:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

Do not rerun RealVisXL workflow smoke unless a user-approved runtime change or broader QA objective requires a new generation. Current smoke result is `workflow_smoke_generation_complete`; pullback hash verification and image QA are complete. If a future smoke is required for a changed lane/prompt/model/runtime, prefer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 45 -StaticProofFile <realvisxl-static-proof> -RunPackageManifestFile <realvisxl-run-package-manifest> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W63_EC2_WORKFLOW_SMOKE_REALVISXL_<timestamp>.json
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 45 -StaticProofFile <realvisxl-static-proof> -RunPackageManifestFile <realvisxl-run-package-manifest> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W63_EC2_WORKFLOW_SMOKE_REALVISXL_<timestamp>.json
```

If AWS auth is expired or Git is not clean/pushed, stop and report that blocker. Do not create more housekeeping evidence unless it fixes a real stale/conflicting instruction.

## Evidence created

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Inventory/W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.md`
- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T022710-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_20260706T024845-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_DRY_RUN_20260706T025536-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_REQUEST_20260706T025536-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_COMFY_WORKFLOW_SMOKE_HELPER_DRY_RUN_20260706T025536-0500.md`
- `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_DRY_RUN_20260706T030037-0500.json`
- `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_CHECKLIST_DRY_RUN_20260706T030037-0500.md`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_IMAGE_ARTIFACT_QA_HELPER_DRY_RUN_20260706T030037-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_20260706T031007-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_AWS_AUTH_GATE_HELPER_20260706T031007-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_EC2_PULLBACK_RECORD_DRY_RUN_20260706T031758-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_EC2_PULLBACK_RECORD_HELPER_DRY_RUN_20260706T031758-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T032345-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_RUNTIME_READINESS_LOCAL_GATE_20260706T032345-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_20260706T033928-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_20260706T033928-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T033522-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_EC2_WORKFLOW_SMOKE_RUN_HELPER_DRY_RUN_20260706T033928-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_GATED_20260706T034448-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_20260706T034448-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_20260706T034515-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_20260706T034516-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_20260706T034516-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_EC2_STATIC_PROOF_GATE_REFRESH_20260706T034516-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T035148-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T035148-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_CURRENT_RECHECK_20260706T055911-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_W60_GIT_CURRENT_RECHECK_20260706T055911-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T040205-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_SANITIZED_20260706T040205-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W60_GITHUB_CHECKPOINT_SECRET_SCAN_HARDENING_20260706T040505-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_GITHUB_CHECKPOINT_SECRET_SCAN_HARDENING_20260706T040505-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T040505-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_SECRET_SCAN_20260706T040505-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T040932-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_CURRENT_VALIDATION_20260706T040932-0500.md`
- `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_CURRENT_VALIDATION_20260706T041240-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_HYDRATION_HELPER_CURRENT_VALIDATION_20260706T041240-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_CURRENT_20260706T041526-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_CURRENT_20260706T041526-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_RECHECK_20260706T041956-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_20260706T042212-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_AWS_PROFILE_AUTH_MATRIX_20260706T042212-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T042257-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_PROFILE_MATRIX_20260706T042257-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_AUTH_MATRIX_20260706T042440-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_AUTH_MATRIX_20260706T042440-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_PROFILE_MATRIX_20260706T042932-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_RUNTIME_READINESS_PROFILE_MATRIX_20260706T042932-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T042938-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_HELPER_CURRENT_VALIDATION_READINESS_PROFILE_20260706T042938-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_PROFILE_READINESS_20260706T043130-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_PROFILE_READINESS_20260706T043130-0500.md`
- `Plan/Instructions/QA/Evidence/Items_Tracker_Validation/W59_W60_ITEMS_TRACKER_CURRENT_VALIDATION_20260706T043530-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_W60_ITEMS_TRACKER_CURRENT_VALIDATION_20260706T043530-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T043539-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_CURRENT_VALIDATION_ITEMS_TRACKER_20260706T043539-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_ITEMS_TRACKER_20260706T044021-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_ITEMS_TRACKER_20260706T044021-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_RECHECK_20260706T044605-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_RECHECK_20260706T044606-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_AWS_AUTH_PROFILE_RECHECK_20260706T044606-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_AUTH_RECHECK_20260706T044638-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_RUNTIME_READINESS_AUTH_RECHECK_20260706T044638-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_AUTH_RECHECK_20260706T044911-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_AUTH_RECHECK_20260706T044911-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_PULLBACK_20260706T045401-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_PULLBACK_MANIFEST_VERIFICATION_20260706T045558-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_CONTRACT_20260706T050233-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_CONTRACT_20260706T050233-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_CONTRACT_20260706T050233-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_AUTH_CONTRACT_20260706T050233-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_AUTH_CONTRACT_RETEST_20260706T050327-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_AWS_AUTH_GATE_CONTRACT_HARDENING_20260706T050352-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_AUTH_CONTRACT_20260706T050612-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_AUTH_CONTRACT_20260706T050612-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_READINESS_CONTRACT_20260706T051212-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_READINESS_CONTRACT_20260706T051212-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_CONTRACT_RETEST_20260706T051212-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_READINESS_CONTRACT_20260706T051212-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_READINESS_CONTRACT_HARDENING_20260706T051348-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_READINESS_CONTRACT_20260706T051624-0500.json`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_READINESS_CONTRACT_RETEST_20260706T051738-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_READINESS_CONTRACT_20260706T051743-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_BLOCKED_EXECUTE_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_COORDINATOR_CONTRACT_20260706T052346-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_EC2_COORDINATOR_GATE_CONTRACT_HARDENING_20260706T052427-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_COORDINATOR_CONTRACT_20260706T052709-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_COORDINATOR_CONTRACT_20260706T052714-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_COORDINATOR_CONTRACT_VALIDATOR_20260706T053043-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_COORDINATOR_CONTRACT_VALIDATOR_20260706T053100-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_COORDINATOR_VALIDATOR_20260706T053239-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_COORDINATOR_VALIDATOR_20260706T053244-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T054119-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T054134-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T054139-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T054153-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_PROJECT_READINESS_SNAPSHOT_20260706T054201-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_PROJECT_READINESS_20260706T054446-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_PROJECT_READINESS_20260706T054450-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T054909-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T054918-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T054932-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T055410-0500.json`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_PROJECT_READINESS_SCAN_SAFE_20260706T055133-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_PROJECT_READINESS_SCAN_SAFE_20260706T055137-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T060420-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T060449-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_PROJECT_READINESS_CONTRACT_20260706T060500-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_QA_CONTRACT_20260706T060710-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_QA_CONTRACT_20260706T060710-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_20260706T061207-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_20260706T061207-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T061212-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T061237-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_RUNTIME_UNBLOCK_HANDOFF_20260706T061207-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_RUNTIME_HANDOFF_20260706T061430-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_RUNTIME_HANDOFF_20260706T061430-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T061933-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T061938-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_RUNTIME_HANDOFF_READINESS_CONTRACT_20260706T062043-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_RUNTIME_HANDOFF_CONTRACT_20260706T062043-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_RUNTIME_HANDOFF_CONTRACT_20260706T062043-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_20260706T063044-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_20260706T063108-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_20260706T063108-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_20260706T063119-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_20260706T063135-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_GIT_CHECKPOINT_GATE_20260706T063145-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_EC2_GIT_GATE_20260706T063145-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_EC2_GIT_GATE_20260706T063145-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_CURRENT_RECHECK_20260706T063842-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_W60_GIT_CURRENT_RECHECK_20260706T063842-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_GIT_POST_CHECKPOINT_20260706T063929-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_GIT_POST_CHECKPOINT_20260706T063929-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_STATIC_VALIDATION_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_SMOKE_DRY_RUN_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_SMOKE_REQUEST_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_REALVISXL_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_SDXL_REALVISXL_BASE_LANE_STATIC_20260706T064900-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_REALVISXL_LANE_20260706T065000-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_REALVISXL_LANE_20260706T065000-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_LANE_SPECIFIC_LOW_RISK_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_LANE_SPECIFIC_REALVISXL_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_REALVISXL_LANE_SPECIFIC_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_REALVISXL_LANE_SPECIFIC_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_REALVISXL_LANE_SPECIFIC_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_LANE_READINESS_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_LANE_READINESS_20260706T065821-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_LANE_READINESS_HARDENING_20260706T065821-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_LANE_READINESS_HARDENING_20260706T070140-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_LANE_READINESS_HARDENING_20260706T070140-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_LANE_AWARE_20260706T071230-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_LANE_AWARE_20260706T071230-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_LANE_AWARE_20260706T071230-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_LANE_AWARE_RETEST_20260706T071230-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_LANE_AWARE_PROJECT_READINESS_20260706T071230-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_LANE_AWARE_HANDOFF_20260706T071230-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_PROJECT_READINESS_LANE_AWARE_HANDOFF_20260706T071230-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_LANE_AWARE_HANDOFF_20260706T071530-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_LANE_AWARE_HANDOFF_20260706T071530-0500.md`
- `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_AUTHORED_LANE_EVIDENCE_COVERAGE_20260706T071911-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_AUTHORED_LANE_EVIDENCE_COVERAGE_20260706T071919-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_AUTHORED_LANE_EVIDENCE_COVERAGE_20260706T071943-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_AUTHORED_LANE_EVIDENCE_COVERAGE_20260706T071911-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_AUTHORED_LANE_COVERAGE_20260706T072520-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_AUTHORED_LANE_COVERAGE_20260706T072520-0500.md`
- `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json`
- `Plan/Instructions/QA/Scripts/Test-RuntimeLaneQueue.ps1`
- `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_RUNTIME_LANE_QUEUE_VALIDATION_20260706T073455-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_RUNTIME_LANE_QUEUE_20260706T073502-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_RUNTIME_LANE_QUEUE_20260706T073523-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_RUNTIME_LANE_QUEUE_VALIDATION_20260706T073455-0500.md`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_RUNTIME_LANE_QUEUE_FIRST_VALIDATION_FAILURE_20260706T073928-0500.json`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_RUNTIME_LANE_QUEUE_20260706T073928-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_REFRESH_RUNTIME_LANE_QUEUE_20260706T073928-0500.md`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_QUEUE_AWARE_SELECTOR_FINAL_20260706T075211-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_QUEUE_AWARE_SELECTOR_RETEST_20260706T075211-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_QUEUE_AWARE_SELECTOR_RETEST_20260706T075211-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_QUEUE_AWARE_READINESS_RETEST_20260706T075228-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_QUEUE_AWARE_HANDOFF_RETEST_20260706T075228-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QUEUE_AWARE_READINESS_HANDOFF_20260706T075211-0500.md`
- `README.md`
- `PROJECT_ROOT_MANIFEST.json`
- `Workflows/base_generation/ACTIVE_LANES.json`
- `Workflows/base_generation/sdxl_low_risk_fallback_lane/workflow.api.json`
- `Workflows/base_generation/sdxl_realvisxl_base_lane/workflow.api.json`
- `tools/New-WorkflowRunPackage.ps1`
- `runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_20260706T081301-0500/RUN_PACKAGE_MANIFEST.json`
- `runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_20260706T081301-0500/prompt_request.json`
- `PromptProfiles/base_generation/hyperreal_editorial_portrait.json`
- `runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/RUN_PACKAGE_MANIFEST.json`
- `runtime_artifacts/run_packages/sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1/prompt_request.json`
- `runtime_artifacts/run_manifests/ROOT_LOCAL_PREFLIGHT_20260706T090734-0500.json`
- `Plan/Instructions/Operations/Scripts/Invoke-EC2WorkflowSmokeRun.ps1`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_HYPERREAL_PACKAGE_20260706T091711-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_HYPERREAL_PACKAGE_20260706T091711-0500.json`
- `Plan/Instructions/Operations/Scripts/New-RuntimeUnblockHandoff.ps1`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_HYPERREAL_PACKAGE_20260706T092429-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_HYPERREAL_PACKAGE_20260706T092429-0500.md`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_PACKAGE_HANDOFF_20260706T092429-0500.json`
- `Plan/Registries/Models/model_registry.jsonl`
- `Plan/Registries/Models/model_runtime_validation_queue.csv`
- `Plan/Registries/Models/model_registry_index.md`
- `Plan/Registries/Models/metadata/civitai/realvisxl_query_20260706T093109-0500.json`
- `Plan/Instructions/Operations/Scripts/Invoke-CivitaiModelLookup.ps1`
- `Plan/Instructions/QA/Scripts/Test-WorkflowModelRegistryCoverage.ps1`
- `Plan/Instructions/QA/Evidence/Model_Registry/W61_MODEL_REGISTRY_COVERAGE_20260706T093415-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_MODEL_REGISTRY_COVERAGE_20260706T093415-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_CIVITAI_MODEL_REGISTRY_20260706T093415-0500.json`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_MODEL_REGISTRY_COVERAGE_20260706T093806-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_MODEL_REGISTRY_GATE_20260706T094500-0500.json`
- `Plan/Instructions/QA/Evidence/Project_Readiness/W61_PROJECT_READINESS_SNAPSHOT_MODEL_REGISTRY_GATE_20260706T094500-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.json`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_MODEL_REGISTRY_GATE_20260706T094500-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_MODEL_REGISTRY_GATE_20260706T094500-0500.json`
- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REFRESH_MODEL_REGISTRY_GATE_20260706T094730-0500.json`
- `Plan/Instructions/QA/Scripts/Test-ComfyWorkflowStatic.ps1`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_low_risk_fallback_lane_20260706T144819-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_realvisxl_base_lane_20260706T144819-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_STATIC_GENERIC_MODEL_REFERENCES_20260706T144827-0500.json`
- `Plan/Registries/Models/model_registry.jsonl`
- `Plan/Registries/Models/model_runtime_validation_queue.csv`
- `Plan/Registries/Models/model_registry_index.md`
- `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_FINAL_20260706T145923-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_20260706T145931-0500.json`
- `Plan/Instructions/Waves/Wave64/WAVE64_SCOPE.md`
- `Plan/Items/Reports/wave64_end_to_end_strict_ai_coverage_report.json`
- `Plan/Tracker/Reports/wave64_end_to_end_strict_ai_coverage_report.json`

## Latest Static Generic Model Reference Update

- `Test-ComfyWorkflowStatic.ps1` now records `model_reference_checks` and validates `runtime.required_models` with explicit `node_id`/`input` or `node_class`/`input` mappings.
- Checkpoint requirements still fall back to matching `CheckpointLoaderSimple.ckpt_name`, so both current queued SDXL lanes continue to pass.
- Low-risk evidence: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_low_risk_fallback_lane_20260706T144819-0500.json`.
- RealVisXL evidence: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_STATIC_GENERIC_MODEL_REFERENCES_sdxl_realvisxl_base_lane_20260706T144819-0500.json`.
- QA helper evidence: `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_STATIC_GENERIC_MODEL_REFERENCES_20260706T144827-0500.json`; result `pass_local_only`, parse failures `0`, smoke failures `0`, project readiness contract failures `0`.
- This was local-only. It did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.

## Latest Model Registry Runtime-Proof Alignment

- `model_registry.jsonl`, `model_runtime_validation_queue.csv`, `model_registry_index.md`, and active-lane `runtime_requirements.json` files now match the existing smoke-proof evidence instead of saying both active models are still queued or not tested.
- `Test-WorkflowModelRegistryCoverage.ps1` is state-aware: pending lanes still require queued registry state, while lanes marked `runtime_smoke_proven` require completed registry status, completed queue status, verified hash/path requirement state, and existing evidence paths.
- First failed alignment evidence is preserved at `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_20260706T145843-0500.json`; it was retested after fixing the lane-status lookup.
- Final passing coverage evidence is `Plan/Instructions/QA/Evidence/Model_Registry/W63_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_FINAL_20260706T145923-0500.json`; result `pass_local_only`, failed check count `0`, both active lanes `pass`, no external contacts, no EC2 start, no generation.
- QA helper evidence is `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W63_QA_HELPER_MODEL_REGISTRY_RUNTIME_PROOF_ALIGNMENT_20260706T145931-0500.json`; result `pass_local_only`.

## Latest Wave64 Strict AI Coverage

- Wave64 strict AI-operational Items and Tracker coverage is present under `Plan/Instructions/Waves/Wave64`, `Plan/Items/Waves/Wave64`, and `Plan/Tracker/Waves/Wave64`.
- Validation command: `python C:\Comfy_UI_Main\Plan\Items\Scripts\generate_wave64_end_to_end_ai_coverage.py`.
- Reports: `Plan/Items/Reports/wave64_end_to_end_strict_ai_coverage_report.json` and `Plan/Tracker/Reports/wave64_end_to_end_strict_ai_coverage_report.json`.
- Result: `pass`, `row_count_items=66`, `row_count_tracker=66`, `required_domain_count=28`, and no missing required domains.
- Wave64 is integrated into Items/Tracker validation and project readiness evidence. Current records: `Plan/Instructions/QA/Evidence/Items_Tracker_Validation/W64_ITEMS_TRACKER_STRICT_AI_COVERAGE_20260706T150215-0500.json`, `Plan/Instructions/QA/Evidence/Project_Readiness/W64_PROJECT_READINESS_STRICT_AI_ITEMS_TRACKER_FINAL_20260706T150215-0500.json`, and `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W64_QA_HELPER_STRICT_AI_ITEMS_TRACKER_20260706T150215-0500.json`.
- Wave64 is a strict coverage/control layer for future work; it does not certify full project completion.

## Latest Workflow Run Package Router Gate

- `tools\New-WorkflowRunPackage.ps1` now accepts `-RouteRequestFile` and uses `Plan\07_IMPLEMENTATION\scripts\resolve_wave64_image_engine_route.py` to gate package creation.
- A routed package writes `router_decision.json` and a manifest `route_gate` block; if the router-selected lane does not match `-LaneId`, package creation throws before a package can be promoted.
- Current generated package: `runtime_artifacts\run_packages\sdxl_realvisxl_router_gated_package_v1\RUN_PACKAGE_MANIFEST.json`; result `pass_local_only`, selected lane `sdxl_realvisxl_base_lane`, selected model `realvisxlV50_v50Bakedvae.safetensors`, `ec2_started=false`, `generation_executed=false`.
- Dedicated evidence: `Plan\Instructions\QA\Evidence\Run_Package\W66_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153601-0500.json`; compatible RealVisXL packaging passed and intentional low-risk/RealVisXL route mismatch blocked.
- QA helper evidence: `Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_20260706T153612-0500.json`; result `pass_local_only`, and the new `workflow_run_package_router_gate_smoke` is part of the local QA helper.
- This was local-only and did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.

## Latest RealVisXL Multi-Sample Package Matrix

- Added three RealVisXL certification prompt profiles:
  - `PromptProfiles\base_generation\realvisxl_multisample_certification\realvisxl_closeup_skin_eye.json`
  - `PromptProfiles\base_generation\realvisxl_multisample_certification\realvisxl_three_quarter_hands_fabric.json`
  - `PromptProfiles\base_generation\realvisxl_multisample_certification\realvisxl_environment_lowlight.json`
- Matrix file: `PromptProfiles\base_generation\realvisxl_multisample_certification.matrix.json`.
- Builder: `tools\New-WorkflowRunPackageMatrix.ps1`.
- Persistent matrix manifest: `runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json`; result `pass_local_only`, sample count `3`, route lane `sdxl_realvisxl_base_lane`, unique seeds, unique output prefixes, no EC2 start, no generation.
- Persistent sample package manifests:
  - `runtime_artifacts\run_packages\realvisxl_multisample_certification_v1_realvisxl_closeup_skin_eye_v1\RUN_PACKAGE_MANIFEST.json`
  - `runtime_artifacts\run_packages\realvisxl_multisample_certification_v1_realvisxl_three_quarter_hands_fabric_v1\RUN_PACKAGE_MANIFEST.json`
  - `runtime_artifacts\run_packages\realvisxl_multisample_certification_v1_realvisxl_environment_lowlight_v1\RUN_PACKAGE_MANIFEST.json`
- Dedicated evidence: `Plan\Instructions\QA\Evidence\Run_Package\W66_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155031-0500.json`; result `pass_local_only`.
- QA helper evidence: `Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W66_QA_HELPER_WORKFLOW_RUN_PACKAGE_MATRIX_20260706T155048-0500.json`; result `pass_local_only`, local smoke failures `0`.
- Wave65 source coverage was rerun again after the matrix S3 dry-run addition. Current result: `pass`, `plan_file_count=2840`, `wave65_rows_created=665`, `missing_after_wave65_count=0`.
- This is preparation for broader image-quality certification, not final certification. Next quality step requires bounded EC2 generation from the matrix packages, artifact pullback, hash verification, and whole-image visual QA for all three samples.

## Latest RealVisXL Matrix Deploy Bundle

- Builder: `tools\New-EC2DeployBundleMatrix.ps1`.
- QA script: `Plan\Instructions\QA\Scripts\Test-EC2DeployBundleMatrix.ps1`.
- QA helper integration: `Plan\Instructions\QA\Scripts\Test-QAHelperStatic.ps1` now includes `ec2_deploy_bundle_matrix_smoke`.
- Latest dedicated evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_DEPLOY_BUNDLE_MATRIX_S3_DRY_RUN_REDACTED_20260706T171921-0500.json`; result `pass_local_only`, matrix id `realvisxl_multisample_certification_v1`, sample count `3`, bundle file count `55`, ZIP SHA256 `e29256311196349987e505bf38a8f2006b72cb7300fa5d545ce2270a01fc9d8e`, and S3 dry-run sidecar `DEPLOY_BUNDLE_MATRIX_MANIFEST.json`.
- QA helper evidence: `Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W66_QA_HELPER_MATRIX_S3_DRY_RUN_REDACTED_20260706T171934-0500.json`; result `pass_local_only`, 14 QA scripts parsed, 17 local smokes, 0 smoke failures.
- Operations helper evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_OPERATIONS_HELPER_MATRIX_BUNDLE_MANIFEST_20260706T171309-0500.json`; result `pass_local_only`, 21 operations scripts parsed, 15 local smokes, 0 evidence-contract failures.
- `Publish-DeployBundleToS3.ps1` preserves the supplied manifest filename, so matrix bundles publish `DEPLOY_BUNDLE_MATRIX_MANIFEST.json` instead of being renamed to the single-package sidecar.
- `Invoke-EC2LaneStaticProof.ps1` and `Invoke-EC2WorkflowSmokeRun.ps1` now read either `DEPLOY_BUNDLE_MANIFEST.json` or `DEPLOY_BUNDLE_MATRIX_MANIFEST.json` after S3 bundle extraction and record matrix metadata when present.
- This was local-only. It did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.
- Next RealVisXL quality step: use the already uploaded and SHA-verified S3 matrix bundle for bounded EC2 generation only after auth/Git/cost-control gates pass, pull back every generated artifact, verify hashes, and perform whole-image visual QA for every sample.

## Latest RealVisXL Matrix Quality-Run Plan

- Planner: `Plan\Instructions\Operations\Scripts\New-EC2WorkflowMatrixQualityRunPlan.ps1`.
- QA script: `Plan\Instructions\QA\Scripts\Test-EC2WorkflowMatrixQualityRunPlan.ps1`.
- QA helper integration: `Plan\Instructions\QA\Scripts\Test-QAHelperStatic.ps1` now includes `ec2_workflow_matrix_quality_run_plan_smoke`.
- Dedicated evidence: `Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_20260706T173124-0500.json`; result `pass_local_only`, matrix id `realvisxl_multisample_certification_v1`, sample count `3`, planned sample count `3`.
- QA helper evidence: `Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W66_QA_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json`; result `pass_local_only`, 15 QA scripts parsed, 18 local smokes, 0 smoke failures.
- Operations helper evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_OPERATIONS_HELPER_MATRIX_QUALITY_RUN_PLAN_20260706T173138-0500.json`; result `pass_local_only`, 22 operations scripts parsed, 0 parse failures.
- The plan emits one bounded `Invoke-EC2WorkflowSmokeRun.ps1` command per sample and requires `-RunPackageManifestFile`, `-DeployBundleS3Uri`, `-DeployBundleSha256`, `-SkipGitLfsPull`, and `-MaxEc2RuntimeMinutes`.
- The plan also emits per-sample `New-EC2PullbackRecord.ps1` and `New-ImageArtifactQARecord.ps1` commands so every generated sample has pullback hash verification plus whole-image QA before certification.
- Wave65 source coverage was rerun after this addition. Current result: `pass`, `plan_file_count=2845`, `wave65_rows_created=670`, `missing_after_wave65_count=0`.
- This was local-only. It did not contact AWS, GitHub APIs, Civitai, ComfyUI, start EC2, or run generation.
- Next RealVisXL quality step: run only the generated S3-backed per-sample plan after AWS auth, Git cleanliness, static proof, readiness, and cost-control gates pass. Pull back and whole-image QA every sample before any quality certification.

## Latest S3 Runtime Infrastructure

- The prior S3 runtime transfer readiness block is superseded. Real bucket/base URI and IAM role values were initialized, and readiness now reports `ready_local_only`.
- Initializer: `Plan\Instructions\Operations\Scripts\Initialize-S3RuntimeInfrastructure.ps1`.
- Readiness checker: `Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1`.
- Operations helper integration: `Plan\Instructions\Operations\Scripts\Test-OperationsHelperStatic.ps1` now includes `s3_runtime_infrastructure_dry_run`.
- Dry-run evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_INFRA_DRY_RUN_20260706T175619-0500.json`; result `dry_run_ready`.
- Execute evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json`; result `s3_runtime_infrastructure_ready`.
- Readiness evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json`; result `ready_local_only`, `missing_config=[]`.
- Operations helper evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_OPERATIONS_HELPER_S3_RUNTIME_INFRA_20260706T175902-0500.json`; result `pass_local_only`.
- Bucket `comfy-ui-main-runtime-029530099913-us-east-1` was created/configured with public access block, SSE-S3 encryption, and versioning. Inline IAM policies verified: `ComfyUIRuntimeS3Access`, `ComfyUIDeployBundleS3Upload`, and `ComfyUIEmergencyStopOnly`.
- Non-secret `.env` values were updated locally and remain ignored; do not commit or print `.env`. The private key `C:\Comfy_UI_Main\comfyui-lora-key.pem` remains ignored/private and must not be committed.
- EC2 was not started and no generation ran. EC2 final state was verified `stopped`.
- Wave65 source coverage was rerun after this addition. Current result: `pass`, `plan_file_count=2855`, `wave65_rows_created=680`, `missing_after_wave65_count=0`.
- This infrastructure setup was followed by a successful S3 matrix bundle publish and SHA verification.

## Latest S3 Matrix Deploy Bundle Publish

- Built ignored local bundle `runtime_artifacts\deploy_bundles\rvxl_mx_s3_20260706T181144-0500\DEPLOY_BUNDLE_MATRIX_MANIFEST.json`; result `pass_local_only`, file count `55`, source Git clean, EC2 not started, generation not run.
- Publish dry-run evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_MATRIX_DEPLOY_BUNDLE_PUBLISH_DRY_RUN_20260706T181159-0500.json`; result `dry_run_ready_to_upload`.
- Publish execute evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_MATRIX_DEPLOY_BUNDLE_PUBLISH_EXECUTE_20260706T181217-0500.json`; result `deploy_bundle_uploaded_to_s3`.
- Upload verification evidence: `Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_S3_MATRIX_DEPLOY_BUNDLE_UPLOAD_VERIFY_20260706T181252-0500.json`; result `s3_upload_sha256_verified`.
- Uploaded bundle URI: `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/rvxl_mx_s3_20260706T181144-0500/rvxl_mx_s3_20260706T181144-0500.zip`.
- Uploaded manifest URI: `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/rvxl_mx_s3_20260706T181144-0500/DEPLOY_BUNDLE_MATRIX_MANIFEST.json`.
- Uploaded/download-verified SHA256: `d3d81bbe2b6cb678304ab06ddf9cb707da31721cb01ca9c26df729414396cc84`.
- S3-backed quality-run plan evidence: `Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_S3_PUBLISHED_20260706T181317-0500.json`; result `pass_local_only`, three planned samples, real `-DeployBundleS3Uri`, real `-DeployBundleSha256`, and `failure_count=0`.
- Wave65 source coverage was rerun after this addition. Current result: `pass`, `plan_file_count=2859`, `wave65_rows_created=684`, `missing_after_wave65_count=0`.
- Next exact action: checkpoint the completed local RealVisXL smoke and QA evidence, then choose the next local-first lane/module or bounded local prompt iteration from a clean pushed state. Fresh AWS auth/Git/readiness/static/cost gates are still required before any future EC2 `-Execute`.

## Latest Local ControlNet Canny QA Loop - 2026-07-07T01:25:00-05:00

- Manual-supervisor local work requirement has been satisfied for `sdxl_realvisxl_controlnet_canny_lane`: local ComfyUI generated a quality matrix, QA identified control-strength/control-image defects, the workflow/request was improved, and the improved package passed local QA across three seeds.
- Current promoted local settings: cleaned control image `controlnet_canny_cleaned_eye_safe_v1.png`, ControlNet `strength=0.45`, `end_percent=0.65`, positive wardrobe terms `tailored dark blazer over textured shirt, clothed shoulders`, and negative wardrobe/control-artifact terms including `bare shoulders`, `strapless top`, `nude`, and `unclothed torso`.
- Final local evidence to use before any future target-runtime gate:
  - `Plan/Instructions/Operations/Prepared_Input_Assets/controlnet_canny_cleaned_eye_safe_v1_20260707T005200-0500/CONTROL_IMAGE_INPUT_ASSET_MANIFEST.json`
  - `Plan/Instructions/QA/Evidence/Workflow_Runtime/W68_LOCAL_CANNY_WARDROBE_PACKAGE_V3_TECHNICAL_20260707T011200-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W68_LOCAL_CANNY_WARDROBE_PACKAGE_V3_VISUAL_QA_20260707T011200-0500.json`
  - `Plan/Instructions/QA/Evidence/Workflow_Runtime/W68_LOCAL_CANNY_WARDROBE_V3_MULTISEED_TECHNICAL_20260707T011900-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W68_LOCAL_CANNY_WARDROBE_V3_MULTISEED_VISUAL_QA_20260707T011900-0500.json`
- `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json` now records the cleaned-control/wardrobe multiseed evidence as the current local pre-EC2 proof. Canny remains pending target-runtime proof; do not certify it until clean checkpoint, bounded EC2 static proof, bounded EC2 generation, pullback, technical QA, and strict whole-image visual QA pass.
- Minimal changed-input local checks passed after this alignment: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W68_LOCAL_CANNY_CLEAN_CONTROL_WARDROBE_STATIC_RECHECK_20260707T013000-0500.json` and `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W68_RUNTIME_LANE_QUEUE_CANNY_CLEAN_CONTROL_LOCAL_QA_RETEST_20260707T013500-0500.json`.
- Preserve `status=queued` for the Canny lane in `runtime_lane_queue.json`; the runtime queue validator expects that exact status while richer local-QA details belong in `role`, `local_pre_ec2_status`, and evidence fields.
- Current Canny package for future target-runtime proof/generation is `runtime_artifacts/run_packages/sdxl_realvisxl_controlnet_canny_lane_clean_control_wardrobe_current_v4/RUN_PACKAGE_MANIFEST.json`. Tracked evidence `Plan/Instructions/QA/Evidence/Run_Package/W68_CANNY_CLEAN_CONTROL_WARDROBE_CURRENT_PACKAGE_V4_20260707T013600-0500.json` reports `pass_local_only`, static workflow pass, dry-run prompt request construction with 18 patched inputs, and prompt SHA256 `0764b5a7a0f51adedaeef99ed4f6685317b6d533b94abe915addb76ac041f3b1`. This package does not certify target runtime; v4 still needs EC2 static proof, bounded EC2 generation, pullback, technical QA, and strict whole-image visual QA.
- Runtime queue validation passed after adding the v4 package evidence: `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W68_RUNTIME_LANE_QUEUE_CANNY_V4_PACKAGE_LOCAL_RETEST_20260707T014000-0500.json`.
- Route-gated package promotion is correctly blocked for Canny v4 until target-runtime proof exists. Router decision `Plan/Instructions/QA/Evidence/Engine_Router/W68_CANNY_V4_ROUTE_DECISION_20260707T014500-0500.json` selected already target-proven `sdxl_realvisxl_base_lane`; package block evidence `Plan/Instructions/QA/Evidence/Run_Package/W68_CANNY_V4_ROUTE_GATED_PACKAGE_BLOCK_20260707T014500-0500.json` records the expected mismatch. Do not treat this as a defect in v4 packaging; it is the router enforcing the missing EC2 static/generation/QA gates.

## Must not repeat

- Do not print token values from `.env`.
- Do not recreate Git metadata in `C:\Comfy_UI_Main`; `.git` already exists and `origin/main` currently matches local `main`. Use `C:\Comfy_UI_Main` as the canonical project root even if the Codex workspace root is `C:\Comfy_UI`.
- Do not treat the empty/broken `.git` directory under `C:\Comfy_UI` as the project repository. Use `git -C C:\Comfy_UI_Main ...` or set the shell working directory to `C:\Comfy_UI_Main` for Git operations.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not start EC2 until `Test-AwsAuthGate.ps1` verifies account `029530099913` and reports `safe_to_start_ec2=true`.
- Use the top-level auth gate fields (`result`, `failure_category`, `account_match`, `remote_login_status`) when summarizing the current AWS auth blocker.
- Use the top-level lane readiness fields (`result`, `failure_category`, `local_pre_ec2_ready`, `ready_for_ec2_static_proof`, `ready_for_generation`) when summarizing selected-lane runtime status.
- Readiness, EC2 static-proof, and EC2 workflow-smoke evidence must match the requested `LaneId`; do not use low-risk SDXL readiness/proof files for the RealVisXL lane.
- Project readiness snapshots and runtime unblock handoffs must also match the requested `LaneId`; do not let a latest RealVisXL readiness record become the low-risk handoff.
- Project readiness snapshots and runtime unblock handoffs must use latest acceptable passing evidence, not the newest preserved failed retest artifact.
- Do not omit the runtime lane queue gate from readiness or handoff evidence; selected lane order must be 1 before EC2 static proof can be allowed.
- Do not omit the model registry coverage gate from readiness or handoff evidence; `Test-WorkflowModelRegistryCoverage.ps1` must report `pass_local_only`, selected lane result `pass`, and failed check count `0` before EC2 static proof can be allowed.
- Do not regress active smoke-proven model registry records back to `queued`, `not_tested`, or `needs_runtime_validation`; completed active lanes must retain evidence-backed runtime-smoke status until a changed lane/model/prompt requires retest.
- Do not add future non-checkpoint `required_models` without a static reference mapping; include `node_id`/`input` or `node_class`/`input` so `Test-ComfyWorkflowStatic.ps1` can prove the workflow references the required asset.
- Do not skip `Test-AuthoredLaneEvidenceCoverage.ps1` when checking multi-lane local readiness; it is now the local pre-EC2 evidence coverage gate for authored base-generation lanes.
- Do not promote `sdxl_realvisxl_base_lane` to first EC2 proof/generation lane. `runtime_lane_queue.json` and `Test-RuntimeLaneQueue.ps1` currently validate `sdxl_low_risk_fallback_lane` first and RealVisXL second.
- Use the top-level EC2 coordinator fields (`result`, `failure_category`, `execute_gates_pass`, `ec2_started`, `generation_executed`) when summarizing static-proof or workflow-smoke gate status.
- Operations helper validation now has dedicated EC2 coordinator evidence contract checks; do not rely on plain JSON parse alone when assessing blocked coordinator evidence.
- Do not repeat the failed index-validation probe that wrapped generated JSON index arrays and counted them as one object; the corrected retest evidence uses direct JSON row counts.
- Do not repeat the first project-readiness snapshot validation mistake that accepted `pass` but not `pass_local_only` for Items/Tracker validation; `Test-ProjectReadinessSnapshot.ps1` now accepts both local-valid result names.
- Do not store literal GitHub token prefixes, token-like scan labels, or user-specific temp paths in helper scan-pattern definitions; `Test-ProjectReadinessSnapshot.ps1` builds those patterns dynamically and uses neutral labels to avoid staged-scan false positives.
- Treat the project-readiness snapshot as a local status aggregator only; it proves `local_ready=true` and blocked runtime gates, but it does not prove EC2 object-info/path/hash, generation, artifact pullback, or media QA.
- Do not treat project-readiness snapshot smoke as sufficient merely because JSON was created; `Test-QAHelperStatic.ps1` now contract-checks recognized result, `local_ready=true`, scan cleanliness, runtime gate consistency, and blocked coordinator safety.
- Use `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.md` as the current post-auth command handoff. It is local-only and does not replace the actual auth gate/readiness/static proof evidence. The older `W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.md` Markdown is historical/corrupted and must not be used as the active human handoff.
- Do not run EC2 static proof until `Test-LaneRuntimeReadiness.ps1` reports `ready_for_ec2_static_proof=true`.
- Treat static-proof dry-run and blocked-execute records as safety evidence only, not as object-info/path/hash proof.
- Do not leave EC2 running.
- Do not treat a generated output as QA-ready until pullback file count/hash evidence is recorded.
- Do not treat `REMOTE_ARTIFACT_MANIFEST.json` as a pulled artifact when comparing local pullback counts/hashes against a remote artifact manifest.
- Do not run generation until prerequisite matching object-info, path, and hash proof is recorded.
- Prefer `Invoke-EC2WorkflowSmokeRun.ps1 -Execute` for the first bounded smoke generation after static proof because it owns the run lifecycle and stop verification.
- For the first hyperreal portrait smoke generation, pass `-RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json` to `Invoke-EC2WorkflowSmokeRun.ps1` so the coordinator uses the verified package request.
- Older handoffs may omit either the package manifest argument or the model registry coverage recheck. Prefer the model-registry-gated handoff unless a newer passing handoff supersedes it.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
- Do not treat GitHub or Civitai token presence in `.env` as AWS auth proof; latest STS/profile-matrix evidence shows AWS auth itself is expired.
- Do not rerun the pre-fix Civitai helper path that uses `System.Web.HttpUtility`; `Invoke-CivitaiModelLookup.ps1` now uses `System.Net.WebUtility` and has successfully cached RealVisXL V5.0 metadata without printing the key.
- Do not treat `Plan/Registries/Models/model_registry.jsonl` as runtime proof. It is local registry/queue coverage only; EC2 must still prove checkpoint path, hash, model load, generation output, pullback, and image QA.
- Do not treat Wave42/Main Flow source snapshots or old `C:\Comfy_UI` workflow files as active runtime just because they exist. Promote only extracted, validated, registered, queued, packaged lanes/modules through the current gate stack.
