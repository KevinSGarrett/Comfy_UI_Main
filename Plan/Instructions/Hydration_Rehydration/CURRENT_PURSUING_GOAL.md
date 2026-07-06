# Current Pursuing Goal

## Active Wave
Wave 61 workflow lane selection.

## Goal Statement
Select the lowest-risk ComfyUI workflow lane from the runtime requirement templates and verify model/node prerequisites before attempting a bounded first execution.

## Why This Goal Is Active
EC2 runtime inventory passed. The remote ComfyUI runtime, GPU, model folders, custom nodes, synced project checkout, and seven runtime requirement templates are present. The next safe step is matching a workflow lane to available assets before running generation.

## Current Status
SELECTED_AUTHORED_STATIC_SMOKE_IMAGE_QA_AUTH_GATE_PULLBACK_PROFILE_AWARE_LANE_READINESS_EC2_STATIC_PROOF_GATE_SMOKE_COORDINATOR_CURRENT_HELPER_INDEX_AWS_PROFILE_ITEMS_TRACKER_AUTH_RECHECK_PULLBACK_MANIFEST_AUTH_CONTRACT_READINESS_CONTRACT_COORDINATOR_GATE_PROJECT_READINESS_QA_CONTRACT_RUNTIME_HANDOFF_HANDOFF_READINESS_CONTRACT_EC2_GIT_CHECKPOINT_GATE_POST_CHECKPOINT_GIT_RECHECK_REALVISXL_LANE_STATIC_PASS_LANE_SPECIFIC_READINESS_LANE_AWARE_PROJECT_HANDOFF_AUTHORED_LANE_EVIDENCE_COVERAGE_PENDING_BROWSER_LOGIN

## Last Action
Added authored-lane evidence coverage validation and wired it into the QA helper. The current coverage record proves both authored base-generation lanes have lane-matched static validation, smoke dry-run/request, and lane runtime readiness evidence; QA helper validation now parses 8 QA scripts, runs 11 local smokes, and reports 0 local smoke failures.

## Next Action
After AWS browser/SSO login is refreshed and the worktree is clean/pushed, rerun `Test-AwsAuthGate.ps1`, `Test-LaneRuntimeReadiness.ps1`, EC2 static proof, bounded smoke generation, artifact pullback, and image QA.
