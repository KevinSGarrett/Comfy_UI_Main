# Current Pursuing Goal

## Active Wave
Wave 61 workflow runtime proof preparation, with Wave 62 package/readiness evidence in place.

## Goal Statement
Advance the first queued authored base-generation lane from local-only readiness to post-auth EC2 static proof, bounded package-fed workflow execution, artifact pullback, and image QA, without bypassing the `Plan/Instructions` operating system or repeating stale housekeeping loops.

## Required Instruction Read Order
Every continuation must use `C:\Comfy_UI_Main` as the project root and must read these project instructions before changing code, evidence, or trackers:

1. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md`
2. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md`
3. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md`
4. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md`
5. `C:\Comfy_UI_Main\Plan\Instructions\NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md`
6. `C:\Comfy_UI_Main\Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
7. `C:\Comfy_UI_Main\Plan\Instructions\Operations\README_OPERATIONS_WAVE60.md`
8. `C:\Comfy_UI_Main\Plan\Instructions\QA\README_QA_WAVE61.md`
9. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\TRACKER_UPDATE_PROTOCOL.md`
10. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\ITEMIZED_LIST_UPDATE_PROTOCOL.md`
11. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_LOG_PROTOCOL.md`

Do not replace this read order with a shorter autonomous goal. The pursuing goal is only a pointer to the active objective; the detailed operating rules live in `Plan/Instructions`.

## How To Use The Instruction Files
Before acting, reconcile the newest acceptable evidence across the instruction files:

- Prefer current passing evidence with the newest timestamp over older failed blockers when the newer evidence directly supersedes it.
- Treat `BLOCKER-W59-GIT-001` as superseded for `C:\Comfy_UI_Main`; this root now has a valid `.git`, canonical `origin`, and pushed `main`.
- Treat `C:\Comfy_UI` only as historical/source context unless a task explicitly says to inspect the old workspace.
- Treat Wave42/Main Flow analysis, registries, release records, and snapshots under `Plan` as source/staging context. The active runtime surface is `C:\Comfy_UI_Main\Workflows\base_generation`, with simplified first-proof API lanes only.
- If top summaries conflict with newer lower sections or evidence files, fix the summary instead of repeating old work.
- Use generated indexes to find files, but do not refresh indexes repeatedly unless files changed in the current turn.
- When evidence commits advance `HEAD`, rerun the Git checkpoint gate immediately before any EC2 `-Execute` path.

## Current Status
`SELECTED_AUTHORED_STATIC_SMOKE_IMAGE_QA_AUTH_GATE_PULLBACK_PROFILE_AWARE_LANE_READINESS_EC2_STATIC_PROOF_GATE_SMOKE_COORDINATOR_CURRENT_HELPER_INDEX_AWS_PROFILE_ITEMS_TRACKER_AUTH_RECHECK_PULLBACK_MANIFEST_AUTH_CONTRACT_READINESS_CONTRACT_COORDINATOR_GATE_PROJECT_READINESS_QA_CONTRACT_RUNTIME_HANDOFF_HANDOFF_READINESS_CONTRACT_EC2_GIT_CHECKPOINT_GATE_POST_CHECKPOINT_GIT_RECHECK_REALVISXL_LANE_STATIC_PASS_LANE_SPECIFIC_READINESS_LANE_AWARE_PROJECT_HANDOFF_AUTHORED_LANE_EVIDENCE_COVERAGE_RUNTIME_LANE_QUEUE_VALIDATED_QUEUE_AWARE_READINESS_VALIDATED_MODEL_REGISTRY_GATE_VALIDATED_ROOT_PREFLIGHT_MODEL_REGISTRY_GATE_PASSED_PENDING_BROWSER_LOGIN`

Both concrete authored base-generation lanes have lane-matched local pre-EC2 evidence and a validated runtime queue. The first runtime lane is `sdxl_low_risk_fallback_lane`; `sdxl_realvisxl_base_lane` is queued second. Model registry coverage is an EC2 preflight gate and currently passes for the active lanes. AWS browser/SSO auth is still the external blocker before EC2 static proof or generation can run.

This goal does not mean the full old `C:\Comfy_UI` workflow system or the full Wave42/Main Flow graph is active runtime yet. Main Flow material must be extracted into a lane/module and pass the current validation, registry, queue, package, auth, Git, readiness, static-proof, pullback, and QA gates before execution.

## Last Verified Facts
The current root preflight passed from `C:\Comfy_UI_Main` with `.git` present, `HEAD == origin/main` at check time, `.env` ignored, required root file structure present, active lane exports static-valid, model registry coverage passing, `ec2_started=false`, and `generation_executed=false`.

The current runtime handoff must be model-registry-gated, queue-aware, Git-checkpoint-gated, and package-aware. The bounded workflow-smoke command must include:

```powershell
-RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json
```

Use `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_RUNTIME_UNBLOCK_HANDOFF_MARKDOWN_ESCAPE_FIX_20260706T101855-0500.md` as the current human-readable runtime handoff. Do not use the older `W61_RUNTIME_UNBLOCK_HANDOFF_MODEL_REGISTRY_GATE_20260706T094500-0500.md` Markdown as the active handoff because it contains PowerShell backtick escape corruption.

## Next Exact Work
If the passing root preflight/index evidence from the active session is still uncommitted, finish that evidence checkpoint first without changing runtime behavior.

After the evidence checkpoint, stop local housekeeping and wait for AWS browser/SSO auth. Once auth is refreshed, run the current handoff sequence in this order:

1. `Test-AwsAuthGate.ps1 -AttemptRemoteLogin` until `ec2_work_allowed=true` and `safe_to_start_ec2=true`.
2. `Test-AwsProfileAuthMatrix.ps1` to verify expected account `029530099913`.
3. `Test-RuntimeLaneQueue.ps1` and require first lane `sdxl_low_risk_fallback_lane`, selected order `1`, failed checks `0`.
4. `Test-WorkflowModelRegistryCoverage.ps1` and require selected lane result `pass`, failed checks `0`.
5. `Invoke-GitHubCheckpoint.ps1` / Git checkpoint recheck and require clean worktree plus `HEAD == origin/main`.
6. `Test-LaneRuntimeReadiness.ps1 -LaneId sdxl_low_risk_fallback_lane`.
7. `Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute`.
8. `Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -RunPackageManifestFile ...RUN_PACKAGE_MANIFEST.json`.
9. Pull back remote artifacts, record the remote manifest, stop EC2, verify final state `stopped`.
10. Run image artifact QA and update evidence, tracker, itemized list, state, and the pursuing goal once.

## Hard Stop And No-Loop Rules
If AWS auth remains expired and the local queue, model registry, root preflight, readiness, and Git gates are already passing or blocked only by auth, do not create more validators, new instruction rewrites, repeated index refreshes, or new evidence files with the same result. Record the auth blocker once, update state once, and stop or wait for user/browser auth.

Housekeeping is allowed only when it fixes a real contradiction, stale current-state pointer, broken validation, missing evidence reference, or requested instruction improvement. It must end with a concrete next runtime action.

## Update Protocol
When this file is autonomously updated, preserve these sections and keep the required instruction read order. Updates should change only the current status, last verified facts, next exact work, and hard blockers. Do not compress this file back into a short goal that omits `Plan/Instructions`.
