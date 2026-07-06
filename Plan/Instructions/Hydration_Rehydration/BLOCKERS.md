# Blockers

No packaging blockers known.

## Current local validation blockers

None for Wave 59 live local directory/index validation. `ISSUE-W59-INDEX-001` was fixed and retested.

## Active blockers

None currently active for local Wave 58-62 static and packaging validation.

## Active runtime blockers

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`
  - blocker type: local_runtime_missing
  - failed condition: `C:\Comfy_UI_Main\ComfyUI` and expected local model folders do not exist.
  - local filesystem involved: yes
  - impact: local ComfyUI workflow execution and local model load validation cannot run from this checkout.
  - route: EC2 runtime discovery found `/home/ubuntu/ComfyUI` and a working NVIDIA A10G GPU path.
  - evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`

- `BLOCKER-AWS-AUTH-EXPIRED-001`
  - blocker type: aws_cli_login_expired
  - failed condition: `aws sts get-caller-identity` returned `ExpiredToken` and `aws ec2 describe-instances` returned `RequestExpired` for the default login credential.
  - latest retest: `Test-AwsAuthGate.ps1` classified the active default profile as `expired_session`; `Test-AwsProfileAuthMatrix.ps1` checked 15 configured AWS CLI profiles and found zero profiles currently authenticated to expected account `029530099913`.
  - AWS/EC2 involved: yes
  - impact: EC2 static lane proof, model hash capture, object-info proof, workflow execution, and generated artifact QA cannot continue until AWS login is refreshed.
  - current state: EC2 was verified `stopped` after the failed static-probe attempt.
  - route: complete `aws login --remote` or `aws sso login --profile <matching-profile>` in a browser-capable interactive shell, rerun `Test-AwsAuthGate.ps1`, verify account `029530099913`, then rerun EC2 static lane proof for `sdxl_low_risk_fallback_lane`.
  - evidence: `Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_20260706T031007-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_RECHECK_20260706T041956-0500.json`; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_20260706T042212-0500.json`

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
  - latest recheck: 2026-07-06T03:59:00-05:00 confirmed `.git` exists, `origin` is configured, `.env` is ignored and untracked, `GITHUB_TOKEN` and `CIVITAI_API_KEY` variable names are present without values printed, and local `main` matches `origin/main`.
  - latest recheck evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_CURRENT_RECHECK_20260706T035900-0500.json`

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
