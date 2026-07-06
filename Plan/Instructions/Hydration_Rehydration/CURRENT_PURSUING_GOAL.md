# Current Pursuing Goal

## Active Wave
Wave 60/61 EC2 runtime inventory.

## Goal Statement
Inventory the synced EC2 project checkout, remote ComfyUI runtime, model folders, and workflow prerequisites before attempting any ComfyUI workflow execution.

## Why This Goal Is Active
EC2 project sync passed. `/home/ubuntu/Comfy_UI_Main` now matches pushed local HEAD with Git LFS pulled and `.env` absent. ComfyUI exists at `/home/ubuntu/ComfyUI`, but model folders, workflow entry points, and runnable prerequisites still need direct evidence before execution.

## Current Scope
- Commit and push the EC2 project sync evidence locally first.
- Start only `i-0560bf8d143f93bb1`.
- Use SSM Run Command only.
- Inventory `/home/ubuntu/ComfyUI` model folders and workflow-related paths.
- Inventory `/home/ubuntu/Comfy_UI_Main` workflow templates and runtime requirement files.
- Capture model counts and missing prerequisite risks.
- Stop EC2 and verify stopped state.
- Record evidence and update trackers/hydration.

## Out of Scope
- Running generation.
- Downloading models.
- Editing remote files except read-only inventory commands.
- Leaving EC2 running.

## Current Status
SELECTED

## Last Action
Completed bounded EC2 project sync and verified final EC2 state `stopped`.

## Next Action
Commit/push EC2 project sync evidence, then run bounded EC2 ComfyUI/model/workflow inventory with stop verification.
