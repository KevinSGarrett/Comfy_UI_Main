# Current Pursuing Goal

## Active Wave
Wave 60/61 EC2 project sync.

## Goal Statement
Clone or update the `Comfy_UI_Main` project checkout on the verified EC2 ComfyUI machine so runtime workflow validation can use the same project state as local `origin/main`.

## Why This Goal Is Active
Bounded EC2 runtime discovery passed: SSM is available, the NVIDIA A10G GPU is visible, ComfyUI exists at `/home/ubuntu/ComfyUI`, and EC2 was stopped afterward. No `Comfy_UI_Main` project checkout was found remotely, so workflow execution cannot proceed until the project is synced.

## Current Scope
- Commit and push the EC2 discovery evidence locally first.
- Start only `i-0560bf8d143f93bb1`.
- Use SSM Run Command only.
- Create or update a stable project checkout path, preferably `/home/ubuntu/Comfy_UI_Main`.
- Pull or clone `https://github.com/KevinSGarrett/Comfy_UI_Main`.
- Verify remote Git branch, HEAD, LFS availability, and `.env` absence.
- Stop EC2 and verify stopped state.
- Record run evidence and update trackers/hydration.

## Out of Scope
- Running ComfyUI workflows.
- Downloading models.
- Generated media QA.
- Leaving EC2 running.
- Writing secrets to EC2 project files.

## Source Inputs
- `Plan/Instructions/Operations/LOCAL_TO_EC2_SYNC_PROTOCOL.md`
- `Plan/Instructions/Operations/AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json`
- Current local Git `main` after the EC2 discovery evidence checkpoint.

## Required Evidence
- Local discovery checkpoint pushed before EC2 sync.
- EC2 start and stop verification.
- SSM command output for clone/pull and Git status.
- Remote project path.
- Remote HEAD matching expected pushed local commit.
- LFS availability or blocker.
- Tracker/hydration updates.

## Validation Plan
- Commit and push the EC2 discovery evidence.
- Start EC2 for bounded sync only.
- Use SSM to clone or update `/home/ubuntu/Comfy_UI_Main`.
- Run `git status`, `git rev-parse HEAD`, and LFS checks remotely.
- Stop EC2 and verify stopped state.

## Current Status
SELECTED

## Last Action
Completed bounded EC2 runtime discovery and verified final EC2 state `stopped`.

## Next Action
Commit/push EC2 discovery evidence, then run bounded EC2 project sync with stop verification.

## Stop Condition
Stop this task when EC2 has a verified project checkout matching pushed `origin/main` and the instance is verified stopped, or when sync is blocked and the instance is verified stopped.

## Fallback / Reroute
If remote Git auth or LFS blocks sync, stop EC2, record the blocker, and prepare a safe credential or artifact-transfer recovery path without printing secrets.
