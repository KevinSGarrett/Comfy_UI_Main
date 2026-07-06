# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then re-open the standard hydration files in this folder.

## Current session completed

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

## Current goal

Refresh AWS auth, complete EC2 static proof for the selected lane, then run bounded workflow execution and generated image QA.

## Next exact action

Complete AWS CLI remote browser/SSO login in an interactive/browser-capable shell, then rerun the auth gate:

```powershell
aws login --remote
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json
```

The account must be `029530099913`, `ec2_work_allowed` must be `true`, and `safe_to_start_ec2` must be `true` before EC2 work resumes.

Current profile-matrix evidence confirms no configured AWS profile is presently usable for the expected account, so use `aws login --remote` or `aws sso login --profile <matching-profile>` before rerunning the gates.
Latest selected-lane readiness evidence now includes both the auth gate and profile matrix diagnostics, but it still requires the auth gate to pass before EC2 static proof.

Latest project readiness and QA helper evidence now also prove the runtime handoff is local-only and did not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2. `GITHUB_TOKEN` and `CIVITAI_API_KEY` in `.env` are present and protected, but they do not unblock EC2; AWS browser/SSO auth is the gate. Before EC2 `-Execute`, local Git must also be clean and synced to `origin/main`, using the live `git_checkpoint_recheck` command from the runtime handoff.

Then rerun the selected-lane readiness gate:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Only proceed if `ready_for_ec2_static_proof=true`.

Then rerun the EC2 static lane proof for `sdxl_low_risk_fallback_lane`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

That helper should:

1. Start only `i-0560bf8d143f93bb1`.
2. Update `/home/ubuntu/Comfy_UI_Main` to `origin/main` and pull LFS.
3. Query ComfyUI `/object_info` for required node availability.
4. Resolve and hash `/home/ubuntu/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`.
5. Stop EC2 and verify `stopped`.
6. Record evidence before running generation.

The helper now self-gates before AWS identity checks or EC2 start. If auth/readiness gates are false, it writes a blocked-execute record and leaves `ec2_started=false`.

Do not run generation until object-info, path, and hash proof are recorded.

After object-info/path/hash proof exists, run the preferred bounded coordinator:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

Then pull back generated image artifacts and apply `Plan/Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md`.

Create a local pullback record after artifact pullback:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json
```

Image QA helper command after pullback record exists:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```

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

## Must not repeat

- Do not print token values from `.env`.
- Do not recreate Git metadata in `C:\Comfy_UI_Main`; `.git` already exists and `origin/main` currently matches local `main`. Use `C:\Comfy_UI_Main` as the canonical project root even if the Codex workspace root is `C:\Comfy_UI`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not start EC2 until `Test-AwsAuthGate.ps1` verifies account `029530099913` and reports `safe_to_start_ec2=true`.
- Use the top-level auth gate fields (`result`, `failure_category`, `account_match`, `remote_login_status`) when summarizing the current AWS auth blocker.
- Use the top-level lane readiness fields (`result`, `failure_category`, `local_pre_ec2_ready`, `ready_for_ec2_static_proof`, `ready_for_generation`) when summarizing selected-lane runtime status.
- Use the top-level EC2 coordinator fields (`result`, `failure_category`, `execute_gates_pass`, `ec2_started`, `generation_executed`) when summarizing static-proof or workflow-smoke gate status.
- Operations helper validation now has dedicated EC2 coordinator evidence contract checks; do not rely on plain JSON parse alone when assessing blocked coordinator evidence.
- Do not repeat the failed index-validation probe that wrapped generated JSON index arrays and counted them as one object; the corrected retest evidence uses direct JSON row counts.
- Do not repeat the first project-readiness snapshot validation mistake that accepted `pass` but not `pass_local_only` for Items/Tracker validation; `Test-ProjectReadinessSnapshot.ps1` now accepts both local-valid result names.
- Do not store literal GitHub token prefixes, token-like scan labels, or user-specific temp paths in helper scan-pattern definitions; `Test-ProjectReadinessSnapshot.ps1` builds those patterns dynamically and uses neutral labels to avoid staged-scan false positives.
- Treat the project-readiness snapshot as a local status aggregator only; it proves `local_ready=true` and blocked runtime gates, but it does not prove EC2 object-info/path/hash, generation, artifact pullback, or media QA.
- Do not treat project-readiness snapshot smoke as sufficient merely because JSON was created; `Test-QAHelperStatic.ps1` now contract-checks recognized result, `local_ready=true`, scan cleanliness, runtime gate consistency, and blocked coordinator safety.
- Use `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_20260706T061207-0500.md` as the concise post-auth command handoff. It is local-only and does not replace the actual auth gate/readiness/static proof evidence.
- Do not run EC2 static proof until `Test-LaneRuntimeReadiness.ps1` reports `ready_for_ec2_static_proof=true`.
- Treat static-proof dry-run and blocked-execute records as safety evidence only, not as object-info/path/hash proof.
- Do not leave EC2 running.
- Do not treat a generated output as QA-ready until pullback file count/hash evidence is recorded.
- Do not treat `REMOTE_ARTIFACT_MANIFEST.json` as a pulled artifact when comparing local pullback counts/hashes against a remote artifact manifest.
- Do not run generation until prerequisite matching object-info, path, and hash proof is recorded.
- Prefer `Invoke-EC2WorkflowSmokeRun.ps1 -Execute` for the first bounded smoke generation after static proof because it owns the run lifecycle and stop verification.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
- Do not treat GitHub or Civitai token presence in `.env` as AWS auth proof; latest STS/profile-matrix evidence shows AWS auth itself is expired.
