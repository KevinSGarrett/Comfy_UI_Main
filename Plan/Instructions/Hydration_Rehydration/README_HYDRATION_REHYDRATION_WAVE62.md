# README — Wave 62 Hydration / Rehydration System

Wave 62 is the final session-continuity, tracker-maintenance, and cumulative-pack certification layer for the autonomous Codex Desktop build system.

## Primary purpose

A new Codex Desktop window must be able to open `C:\Comfy_UI_Main\`, read the project state, and immediately understand:

- what was completed
- what failed
- what needs retesting
- what the current goal is
- what the next action is
- what files matter
- what AWS / GitHub / Civitai resources exist
- what QA evidence exists
- how to update trackers and itemized lists
- how to build the next cumulative pack without losing prior wave content

## Known locations

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

## Required first files to read

1. `Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md`
2. `Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md`
3. `Plan\Instructions\Hydration_Rehydration\CURRENT_STATUS_AND_NEXT_ACTION_TEMPLATE.md`
4. `Plan\Instructions\Hydration_Rehydration\AUTONOMOUS_SESSION_STATE_TEMPLATE.md`
5. `Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
6. `Plan\Instructions\Indexes\MASTER_PROJECT_LOCATION_INDEX.md`
7. `Plan\Instructions\Operations\README_OPERATIONS_WAVE60.md`
8. `Plan\Instructions\QA\README_QA_WAVE61.md`
9. Latest tracker and itemized-list files under `Plan\Tracker` and `Plan\Items`

## Required final files to write before ending a session

- `CURRENT_SESSION_STATE.md`
- `CURRENT_PURSUING_GOAL.md`
- `NEXT_ACTION.md`
- `RECENT_DECISIONS.md`
- `KNOWN_ISSUES.md`
- `BLOCKERS.md`
- `QA_EVIDENCE_INDEX.md`
- `PROOF_OF_MOVEMENT_LOG.csv`
- any tracker / itemized-list rows affected by the session
- any QA evidence records created during the session
- `RESUME_HERE_NEXT_CODEX_SESSION.md`

## Golden rule

Do not allow the next autonomous session to guess. If future Codex needs context, record that context before ending the current session.
