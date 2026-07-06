# Blockers

No packaging blockers known.

## Current local validation blockers

None for Wave 59 live local directory/index validation. `ISSUE-W59-INDEX-001` was fixed and retested.

## Active blockers

None currently active for local Wave 58-62 static and packaging validation.

## Active runtime blockers

- `BLOCKER-RUNTIME-REALVISXL-CHECKPOINT-EC2-001`
  - blocker type: ec2_required_model_missing
  - failed condition: RealVisXL second-lane EC2 static proof found `/home/ubuntu/ComfyUI/models/checkpoints/realvisxlV50_v50Bakedvae.safetensors` missing.
  - AWS/EC2 involved: yes
  - impact: `sdxl_realvisxl_base_lane` cannot run generation, pullback, or image QA until the checkpoint exists on EC2 and its SHA256 is verified.
  - expected file: `realvisxlV50_v50Bakedvae.safetensors`
  - expected source/version: Civitai model `139562`, version `789646`, `RealVisXL V5.0 (BakedVAE)`
  - expected source SHA256: `6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80`
  - current state: EC2 `/object_info` proof passed, required nodes were present, command status was `Success`, and final EC2 state was verified `stopped`; model proof reported `exists=false`.
  - route: install or sync the checkpoint into the EC2 ComfyUI checkpoints directory, verify SHA256, rerun `Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute`, then rerun lane readiness before any workflow smoke generation.
  - evidence: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_REALVISXL_20260706T123028-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_REALVISXL_MISSING_MODEL_CLASSIFICATION_20260706T124103-0500.json`

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`
  - blocker type: local_runtime_missing
  - failed condition: `C:\Comfy_UI_Main\ComfyUI` and expected local model folders do not exist.
  - local filesystem involved: yes
  - impact: local ComfyUI workflow execution and local model load validation cannot run from this checkout.
  - route: EC2 runtime discovery found `/home/ubuntu/ComfyUI` and a working NVIDIA A10G GPU path.
  - evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`

- `BLOCKER-AWS-AUTH-EXPIRED-001`
  - status: historical/conditional recheck gate after the post-login low-risk proof and RealVisXL static proof attempt; not the current RealVisXL blocker.
  - blocker type: aws_cli_login_expired
  - failed condition: `aws sts get-caller-identity` returned `ExpiredToken` and `aws ec2 describe-instances` returned `RequestExpired` for the default login credential.
  - latest retest: 2026-07-06T09:45:00-05:00 model-registry-gated readiness records `result=local_pre_ec2_ready_runtime_blocked_auth`, `local_pre_ec2_ready=true`, `ready_for_ec2_static_proof=false`, and `model_registry_coverage.coverage_allows_selected_lane_ec2_static_proof=true`; project readiness records `result=pass_local_ready_runtime_blocked_auth`, `local_ready=true`, `ec2_start_allowed=false`, and `generation_allowed=false`; runtime handoff records command step count `11` with `model_registry_coverage_recheck`; QA and operations helper validations both report `pass_local_only` with zero local smoke failures. AWS auth still blocks EC2 start.
  - AWS/EC2 involved: yes
  - impact: EC2 static lane proof, model hash capture, object-info proof, workflow execution, and generated artifact QA cannot continue until AWS login is refreshed.
  - current state: EC2 was verified `stopped` after the failed static-probe attempt.
  - route: before any future EC2 `-Execute`, rerun `Test-AwsAuthGate.ps1`, verify account `029530099913`, ensure local `HEAD` equals `origin/main` with a clean worktree, and then continue the current lane-specific blocker path. For RealVisXL, resolve the missing checkpoint on EC2 and verify SHA256 before workflow smoke generation.
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
