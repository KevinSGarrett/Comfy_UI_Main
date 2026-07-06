# Session Start Rehydration Checklist

## Goal

This checklist tells Codex Desktop exactly what to read and verify at the beginning of every autonomous work session.

## Step 1 — Confirm project root

Expected project root:

```text
C:\Comfy_UI_Main\
```

If running elsewhere, Codex must identify the mounted or copied equivalent and record the actual path in the session state.

## Step 2 — Read the latest resume file first

Open:

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md
```

Extract:

- current goal
- last completed action
- next action
- active tracker IDs
- pending validation
- known blockers
- relevant files to open next

## Step 3 — Read active state files

Open and summarize:

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\RECENT_DECISIONS.md
```

## Step 4 — Read project command manuals

Read in this order:

1. `Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
2. `Plan\Instructions\AI_PROJECT_MANAGER_DYNAMIC_OPERATING_MODEL.md`
3. `Plan\Instructions\NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md`
4. `Plan\Instructions\COMPLETION_DEFINITION_AND_DONE_GATE.md`
5. `Plan\Instructions\Indexes\MASTER_PROJECT_LOCATION_INDEX.md`
6. `Plan\Instructions\Operations\README_OPERATIONS_WAVE60.md`
7. `Plan\Instructions\QA\README_QA_WAVE61.md`
8. `Plan\Instructions\Hydration_Rehydration\TRACKER_UPDATE_PROTOCOL.md`
9. `Plan\Instructions\Hydration_Rehydration\ITEMIZED_LIST_UPDATE_PROTOCOL.md`

## Step 5 — Inspect Items and Tracker

Open the latest tracker and itemized-list files under:

```text
C:\Comfy_UI_Main\Plan\Tracker
C:\Comfy_UI_Main\Plan\Items
```

Codex must determine:

- highest-value incomplete item
- items marked complete but missing QA evidence
- items blocked by missing files, failed tests, AWS, GitHub, Civitai, or model dependencies
- items that should be retried because fixes were made
- items that can be progressed without GPU runtime

## Step 6 — Verify external resource awareness

Before using external systems, read:

```text
Plan\Instructions\Indexes\GITHUB_REPOSITORY_OPERATING_INDEX.md
Plan\Instructions\Indexes\AWS_RESOURCE_INDEX.md
Plan\Instructions\Indexes\EC2_GPU_SERVER_OPERATING_INDEX.md
Plan\Instructions\Operations\GITHUB_MINIMAL_PERSONAL_PROJECT_PROTOCOL.md
Plan\Instructions\Operations\AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md
Plan\Instructions\Operations\CIVITAI_API_OPERATING_PROTOCOL.md
```

Known resource summary:

```text
Main Local Project:
C:\Comfy_UI_Main\

Blueprint / Instruction Manual / Technical Project Plan:
C:\Comfy_UI_Main\Plan

Items:
C:\Comfy_UI_Main\Plan\Items

Tracker:
C:\Comfy_UI_Main\Plan\Tracker

Session Instructions:
C:\Comfy_UI_Main\Plan\Instructions

GitHub:
https://github.com/KevinSGarrett/Comfy_UI_Main

GitHub token location:
C:\Comfy_UI_Main\.env

AWS Account:
029530099913

EC2 Instance:
i-0560bf8d143f93bb1

EC2 Name:
ComfyUI-LoRA-GPU-Server

EC2 Type:
g5.xlarge

IAM Profile:
ComfyUI-SSM-Profile

Expected idle state:
stopped

Public IP when stopped:
none

Attached EBS Volume:
vol-0eb9b2c6d3d2706d6

Volume Size:
1024 GB

```

## Step 7 — Decide the next highest-value task

Use this priority order:

1. S0/S1 failed validations or blockers that prevent broad progress
2. incomplete item with highest downstream dependency value
3. item missing QA evidence even though implementation appears complete
4. item that can be completed locally without EC2 or model downloads
5. item requiring GitHub sync
6. item requiring EC2/GPU validation
7. item requiring Civitai lookup/download
8. documentation/index/tracker cleanup that prevents future confusion

## Step 8 — Start work only after declaring the session objective

Before modifying files, Codex must write or update:

```text
CURRENT_PURSUING_GOAL.md
CURRENT_SESSION_STATE.md
NEXT_ACTION.md
```

## Step 9 — Do not ask the user to repeat known information

If the information exists in Plan, Items, Tracker, Instructions, GitHub index, AWS index, operation protocols, or hydration files, Codex must use it.

## Step 10 — If confused

If state is unclear:

1. stop modifying project files
2. read the tracker and resume files again
3. check the latest validation report
4. classify the issue as missing_context, conflicting_state, missing_file, failed_test, or blocker
5. record the issue
6. continue with the safest high-value task that does not require the missing information
