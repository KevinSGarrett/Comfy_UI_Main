# Blockers

No packaging blockers known.

## Current local validation blockers

None for Wave 59 live local directory/index validation. `ISSUE-W59-INDEX-001` was fixed and retested.

## Active blockers

None currently active for local Wave 58-62 static and packaging validation.

## Active runtime blockers

- `BLOCKER-AWS-AUTH-EXPIRED-W68-STATIC-PROOF-001`
  - status: active after successful W68 EC2 Canny model/input installation; not a GitHub token, Civitai key, `.env`, or Git repository blocker.
  - blocker type: aws_cli_login_expired
  - failed condition: before the `sdxl_realvisxl_controlnet_canny_lane` EC2 static-proof window, `aws sts get-caller-identity` returned an expired-session error and the profile matrix found 0 of 15 profiles authenticating to expected account `029530099913`.
  - latest proof of progress before block: the Canny ControlNet model and Canny input image were installed on EC2 from S3 and SHA256-verified; both helpers verified EC2 final state `stopped`; no generation ran.
  - impact: EC2 static proof and bounded workflow smoke must not start until fresh AWS auth/account gates pass again.
  - current state: Git is clean/pushed at the install checkpoint, but AWS auth must be refreshed before EC2 static proof.
  - route: complete `aws login`/SSO for expected account `029530099913`, rerun `Test-AwsAuthGate.ps1`, rerun `Test-AwsProfileAuthMatrix.ps1`, rerun lane readiness, create a fresh emergency stop schedule, then run `Invoke-EC2LaneStaticProof.ps1` for `sdxl_realvisxl_controlnet_canny_lane` from a clean pushed head.
  - evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_PROFILE_AUTH_MATRIX_CONTROLNET_CANNY_STATIC_RECHECK_20260706T231000-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_RECHECK_BLOCKED_20260706T231000-0500.json`; `Plan/Instructions/QA/Evidence/Model_Registry/W68_EC2_CONTROLNET_CANNY_MODEL_INSTALL_20260706T224500-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_EC2_CONTROLNET_CANNY_INPUT_ASSET_INSTALL_20260706T225500-0500.json`

- `BLOCKER-RUNTIME-CONTROLNET-CANNY-EC2-PROOF-001`
  - status: active for queued lane `sdxl_realvisxl_controlnet_canny_lane` after local runtime proof.
  - blocker type: target_runtime_proof_pending
  - failed condition: EC2 static proof, bounded EC2 generation, pullback, technical QA, and whole-image visual QA have not yet run for the ControlNet Canny lane from a clean pushed head.
  - impact: Local iteration is unblocked, but the lane is not target-runtime certified and cannot count toward final project completion.
  - current proof: local model provisioning, input asset preparation, local `/object_info` model visibility, local bounded generation, pullback, technical QA, and whole-image visual QA all pass with notes.
  - evidence: `Plan/Instructions/QA/Evidence/Model_Registry/W67_CONTROLNET_CANNY_MODEL_LOCAL_PROVISIONING_20260706T214500-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W67_LOCAL_OBJECT_INFO_CONTROLNET_CANNY_MODEL_INPUT_20260706T215000-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Runtime/W67_LOCAL_CONTROLNET_CANNY_RUN_PACKAGE_EXECUTE_20260706T215500-0500.json`; `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W67_LOCAL_CONTROLNET_CANNY_IMAGE_QA_VISUAL_20260706T220000-0500.json`
  - route: after checkpoint/push and fresh AWS auth/Git/cost-control gates, run the lane-specific EC2 static proof, bounded generation, pullback, technical image QA, and whole-image visual QA.

- `BLOCKER-RUNTIME-CONTROLNET-CANNY-MODEL-001`
  - status: resolved 2026-07-06T22:00:00-05:00; not a Git, GitHub token, Civitai key, or `.env` blocker.
  - blocker type: required_controlnet_model_and_input_asset_missing
  - failed condition: `models/controlnet/controlnet-canny-sdxl-1.0-small.safetensors` is not present and `controlnet_canny_corrected_white_edges_black_bg.png` has not yet been proven in the active ComfyUI input directory.
  - resolution: downloaded the fp16 small SDXL Canny ControlNet safetensors from Hugging Face into ignored `models/controlnet`, SHA256-recorded it as `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`, generated and placed `controlnet_canny_corrected_white_edges_black_bg.png` in the active ComfyUI input directory, proved both through local `/object_info`, ran bounded local generation, pulled the image into project evidence, and completed technical plus whole-image visual QA.
  - evidence: `Plan/Instructions/QA/Evidence/Model_Registry/W67_CONTROLNET_CANNY_MODEL_LOCAL_PROVISIONING_20260706T214500-0500.json`; `Plan/Instructions/Operations/Prepared_Input_Assets/controlnet_canny_input_20260707T000000-0500/CONTROL_IMAGE_INPUT_ASSET_MANIFEST.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W67_LOCAL_OBJECT_INFO_CONTROLNET_CANNY_MODEL_INPUT_20260706T215000-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Runtime/W67_LOCAL_CONTROLNET_CANNY_RUN_PACKAGE_EXECUTE_20260706T215500-0500.json`; `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W67_LOCAL_CONTROLNET_CANNY_IMAGE_QA_VISUAL_20260706T220000-0500.json`

- `BLOCKER-W68-CANNY-AWS-AUTH-EXPIRED-STATIC-PROOF-001`
  - status: active runtime blocker as of 2026-07-07T01:45:00-05:00; local project work and GitHub checkpointing can continue.
  - blocker type: aws_cli_sso_session_expired_before_ec2_static_proof
  - failed condition: current W68 auth gate for `sdxl_realvisxl_controlnet_canny_lane` reports expired AWS session and `safe_to_start_ec2=false`; lane readiness reports `local_pre_ec2_ready=true` but `ready_for_ec2_static_proof=false` and `ready_for_generation=false`.
  - not the cause: GitHub token, Civitai key, `.env`, `.git`, local model provisioning, S3 asset upload, EC2 asset placement, or the private PEM file.
  - safe current work: validate, scan, commit, push, update trackers/hydration, and continue local-only QA/tooling improvements. Do not start EC2 until AWS auth/profile/readiness gates pass for expected account `029530099913`.
  - evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_AUTH_GATE_CONTROLNET_CANNY_STATIC_REMOTE_LOGIN_CLASSIFIED_20260707T001000-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_AWS_PROFILE_AUTH_MATRIX_CONTROLNET_CANNY_STATIC_RECHECK_20260706T231000-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_LANE_RUNTIME_READINESS_CANNY_CURRENT_QUEUE_BLOCKED_AUTH_20260707T012500-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W68_RUNTIME_UNBLOCK_HANDOFF_CANNY_CURRENT_QUEUE_BLOCKED_AUTH_20260707T013000-0500.json`; `Plan/Instructions/QA/Evidence/Project_Readiness/W68_PROJECT_READINESS_CANNY_CURRENT_QUEUE_WITH_HANDOFF_20260707T013500-0500.json`

- `BLOCKER-AWS-AUTH-EXPIRED-001`
  - status: historical/conditional recheck gate after the post-login low-risk proof, RealVisXL runtime proof, and S3/IAM runtime infrastructure initialization; not a current local/S3 blocker.
  - blocker type: aws_cli_login_expired
  - failed condition: `aws sts get-caller-identity` returned `ExpiredToken` and `aws ec2 describe-instances` returned `RequestExpired` for the default login credential.
  - latest retest: 2026-07-06T17:57:16-05:00 S3/IAM runtime infrastructure setup verified AWS account `029530099913` and completed S3/IAM changes without EC2 start. Before any future EC2 `-Execute`, rerun the auth/account/Git/cost-control gates because credentials can expire between sessions.
  - AWS/EC2 involved: yes
  - impact: No current local/S3 setup impact. Future EC2 static proof, workflow execution, and generated artifact QA must still prove fresh auth before start.
  - current state: EC2 was verified `stopped` after the failed static-probe attempt.
  - route: before any future EC2 `-Execute`, rerun `Test-AwsAuthGate.ps1`, verify account `029530099913`, ensure local `HEAD` equals `origin/main` with a clean worktree, and then continue the next selected lane/module path. For RealVisXL, checkpoint install, static proof, smoke generation, pullback, and image QA have completed; the next S3 action is bundle publish/sha verification, not auth-blocker recovery.
  - evidence: `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_20260706T031007-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_RECHECK_20260706T041956-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_20260706T042212-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_RECHECK_20260706T044605-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_RECHECK_20260706T044606-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_AUTH_RECHECK_20260706T044638-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_CONTRACT_20260706T050233-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_CONTRACT_20260706T050233-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_CONTRACT_20260706T050233-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_READINESS_CONTRACT_20260706T051212-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_READINESS_CONTRACT_20260706T051212-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_CONTRACT_RETEST_20260706T051212-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_COORDINATOR_CONTRACT_20260706T052346-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_COORDINATOR_CONTRACT_20260706T052346-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_COORDINATOR_CONTRACT_20260706T052346-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_COORDINATOR_CONTRACT_20260706T052346-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_RUN_BLOCKED_EXECUTE_COORDINATOR_CONTRACT_20260706T052346-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_AUTHORED_LANE_EVIDENCE_COVERAGE_20260706T071911-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_RUNTIME_LANE_QUEUE_VALIDATION_20260706T073455-0500.json`

- `BLOCKER-EC2-PROJECT-SYNC-001`
  - status: resolved 2026-07-06T01:59:07-05:00
  - blocker type: ec2_project_checkout_missing
  - failed condition: bounded EC2 discovery found `/home/ubuntu/ComfyUI` but no `Comfy_UI_Main` project checkout in searched paths.
  - AWS/EC2 involved: yes
  - impact: EC2 cannot pull/use the latest project workflows, registries, tracker state, or QA protocols until the project checkout is cloned or updated.
  - resolution: cloned `https://github.com/KevinSGarrett/Comfy_UI_Main.git` to `/home/ubuntu/Comfy_UI_Main`, pulled Git LFS, verified matching HEAD, confirmed `.env` absent, stopped EC2, and verified final state `stopped`.
  - evidence: `Plan/Instructions/QA/Evidence/EC2_Project_Sync/W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.json`

## Resolved blockers

- `BLOCKER-W59-GIT-001` - resolved/stale for active root 2026-07-07T01:20:00-05:00
  - blocker type: stale_wrong_root_git_detection
  - resolution: `C:\Comfy_UI_Main` is the active project root and contains `.git`, `.env`, `comfyui-lora-key.pem`, `Plan`, `Workflows`, `models`, `ComfyUI`, and the expected project file structure. Git status/head checks confirm the active repo root is `C:/Comfy_UI_Main`; do not recreate Git metadata and do not switch back to historical `C:\Comfy_UI`.
  - current blocker after resolution: AWS CLI/SSO auth is expired before W68 Canny EC2 static proof; this is separate from GitHub token, Civitai key, `.env`, `.git`, local model, S3 upload, or EC2 asset placement.
  - evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W68_OPERATIONS_HELPER_W68_CANNY_GATE_CONTRACTS_20260707T011500-0500.json`

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001` - resolved 2026-07-06T20:58:00-05:00
  - blocker type: local_runtime_missing / local_generation_unproven
  - resolution: bootstrapped ignored local ComfyUI checkout, created CUDA Torch venv, downloaded and SHA-verified local RealVisXL checkpoint, configured local extra model paths, passed local `/object_info`, generated one bounded RealVisXL PNG locally, copied it into project pullback evidence, ran technical image QA, and completed whole-image visual QA.
  - evidence: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_REALVISXL_SMOKE_EXECUTE_20260706T205501-0500.json`; `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_REALVISXL_SMOKE_IMAGE_QA_VISUAL_20260706T205650-0500.json`

- `BLOCKER-RUNTIME-S3-CONFIG-001` - resolved 2026-07-06T17:58:08-05:00
  - blocker type: missing_s3_runtime_bucket_and_iam_config
  - resolution: initialized bucket `comfy-ui-main-runtime-029530099913-us-east-1`, attached EC2 runtime S3 access, created the GitHub OIDC deploy role and scheduler stop role, updated only non-secret local `.env` values, and reran readiness with `result=ready_local_only`.
  - evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_INFRA_EXECUTE_20260706T175716-0500.json`; `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_S3_RUNTIME_TRANSFER_READY_20260706T175808-0500.json`

- `BLOCKER-RUNTIME-REALVISXL-PULLBACK-QA-001` - resolved 2026-07-06T14:01:00-05:00
  - blocker type: generated_artifact_pullback_and_qa_pending
  - resolution: RealVisXL workflow smoke generation completed on EC2, generated artifacts were pulled back locally through the SSM SSH tunnel using `comfyui-lora-key.pem`, hashes were verified with `PULLBACK_RECORD.json`, and technical plus visual image QA were recorded.
  - evidence: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json`; `Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json`; `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_IMAGE_QA_TECHNICAL_REALVISXL_20260706T140027-0500.json`; `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json`

- `BLOCKER-RUNTIME-REALVISXL-CHECKPOINT-EC2-001` - resolved 2026-07-06T13:20:40-05:00
  - blocker type: ec2_required_model_missing
  - resolution: RealVisXL checkpoint `realvisxlV50_v50Bakedvae.safetensors` was installed on EC2, SHA256 was verified as `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`, EC2 static proof passed after install, and workflow smoke generation later completed.
  - evidence: `Plan/Instructions/QA/Evidence/Model_Registry/W63_EC2_REALVISXL_MODEL_INSTALL_20260706T125425-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json`

- `BLOCKER-W59-GIT-001` - resolved 2026-07-06T01:06:03-05:00
  - affected tracker IDs: `TRK-W59-004`, `TRK-W60-001`, `TRK-W60-009`
  - resolution: initialized Git metadata in `C:\Comfy_UI_Main`, configured canonical origin, enabled Git LFS for oversized CSVs, created initial commit, pushed `main`, and verified remote HEAD matches local HEAD.
  - evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json`
  - latest recheck: 2026-07-06T10:30:00-05:00 confirmed `C:\Comfy_UI_Main` is the canonical repo, `.git` exists, `origin` is configured as `https://github.com/KevinSGarrett/Comfy_UI_Main.git`, `.env` is ignored and untracked, `GITHUB_TOKEN` and `CIVITAI_API_KEY` variable names are present without values printed, and root preflight passed with local `HEAD` matching `origin/main` at `8bd059bdec2b2c8bd95a158930d2a26fa9d77b0a`. Do not recreate Git metadata or switch to `C:\Comfy_UI`.
  - latest recheck evidence: `runtime_artifacts/run_manifests/ROOT_LOCAL_PREFLIGHT_CURRENT_HEAD_20260706T103000-0500.json`

- `BLOCKER-W62-ZIP-001` - resolved 2026-07-06T01:15:48-05:00
  - affected tracker ID: `TRK-W62-009`
  - blocker type: local_cumulative_zip_missing
  - failed condition: no `.zip` file was found under `C:\Comfy_UI_Main`, so `Test-CumulativeWavePack.ps1` could not be run against a real cumulative pack.
  - resolution: created `C:\Comfy_UI_Main\Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip`, validated private-path exclusion, ran `Test-CumulativeWavePack.ps1`, and recorded done certification.
  - evidence: `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json`

## Runtime blockers to detect later

- Missing or invalid `.env`
- GitHub token missing or invalid
- AWS CLI not configured
- AWS account mismatch
- EC2 instance not found
- EC2 not using expected IAM profile
- Civitai API access unavailable
- Required model files missing
- ComfyUI runtime path mismatch
