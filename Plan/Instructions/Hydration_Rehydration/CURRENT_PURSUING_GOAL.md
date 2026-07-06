# Current Pursuing Goal

## Active Wave
Wave 60/61 EC2 runtime discovery.

## Goal Statement
Run a bounded EC2 runtime discovery pass because local `C:\Comfy_UI_Main\ComfyUI` is absent and workflow/model runtime validation requires a real ComfyUI-capable environment.

## Why This Goal Is Active
Secret-safe readiness preflight passed for GitHub API, AWS identity, EC2 identity, EBS volume, and Civitai metadata. The EC2 instance is verified and stopped. Local ComfyUI runtime execution is blocked by missing local runtime/model folders, so the next valid runtime path is EC2 discovery with a stop plan.

## Current Scope
- Create an EC2 run record before starting.
- Start only `i-0560bf8d143f93bb1`.
- Wait for running and status-ok.
- Verify SSM availability.
- Run minimal remote discovery commands only.
- Identify remote project and ComfyUI paths.
- Capture command output as evidence.
- Stop EC2 and verify stopped state.
- Update blockers, trackers, and hydration.

## Out of Scope
- Long-running generation.
- Model downloads.
- Generated media QA.
- Leaving EC2 running.
- SSH unless SSM fails and a later recovery path explicitly permits it.

## Source Inputs
- `Plan/Instructions/Operations/AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md`
- `Plan/Instructions/Operations/LOCAL_TO_EC2_SYNC_PROTOCOL.md`
- `Plan/Instructions/Operations/EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`

## Required Evidence
- AWS account and EC2 identity already verified before start.
- Run record with start time, starting state, commands, stop attempt, and final state.
- SSM readiness result.
- Remote path discovery output.
- Final stopped-state verification.
- Updated tracker/hydration state.

## Validation Plan
- Commit and push the readiness preflight checkpoint first.
- Start EC2 only after the checkpoint is clean on `origin/main`.
- Use SSM Run Command for remote discovery.
- Stop the instance even if discovery fails.
- Record any SSM or path mismatch as a runtime blocker.

## Current Status
SELECTED

## Last Action
Completed secret-safe readiness preflight and opened `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`.

## Next Action
Commit/push the readiness preflight evidence, then perform bounded EC2 runtime discovery with stop verification.

## Stop Condition
Stop this task when the EC2 discovery run has evidence and the instance is verified stopped, or when AWS/SSM blocks discovery and the stopped state is verified.

## Fallback / Reroute
If SSM is unavailable, stop the instance, record the blocker, and do not use SSH without an explicit recovery decision in the tracker.
