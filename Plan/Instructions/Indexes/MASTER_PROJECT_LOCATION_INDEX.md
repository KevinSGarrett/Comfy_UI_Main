<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# MASTER_PROJECT_LOCATION_INDEX

## 1. Purpose

This file is the canonical location map for Codex Desktop when operating the `Comfy_UI_Main` autonomous hyperrealism project.

Codex must read this index during every session start before choosing work. This index tells Codex where the project lives locally, where the authoritative planning files live, where tracking state is stored, where GitHub is located, and what AWS resources belong to the GPU validation environment.

This index does **not** replace the Itemized List, Tracker, or Instruction Manual. It is the directory and resource awareness layer that helps Codex locate those files correctly.

## 2. Canonical local paths

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

Index system:
C:\Comfy_UI_Main\Plan\Instructions\Indexes

Hydration / Rehydration state:
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration

Wave folders:
C:\Comfy_UI_Main\Plan\Instructions\Waves
```

## 3. Canonical GitHub resource

```text
GitHub Repository:
https://github.com/KevinSGarrett/Comfy_UI_Main

Expected local Git root:
C:\Comfy_UI_Main\

GitHub token expected location:
C:\Comfy_UI_Main\.env
```

Codex must never print, commit, summarize, copy, index, or expose any token value. The `.env` file may be used only as a local secret source and must remain excluded from Git.

## 4. Canonical AWS resources

```text
AWS Account:
029530099913

EC2 Instance:
i-0560bf8d143f93bb1

EC2 Name tag:
ComfyUI-LoRA-GPU-Server

EC2 Instance type:
g5.xlarge

IAM Profile:
ComfyUI-SSM-Profile

Expected normal idle state:
stopped

Public IP when stopped:
none

Attached EBS Volume:
vol-0eb9b2c6d3d2706d6

Volume size:
1024 GB
```

Codex must verify AWS account, instance identity, instance type, IAM profile, state, EBS volume attachment, and volume size before using the GPU server.

## 5. Source-of-truth hierarchy

Codex must resolve conflicts using this priority order:

| Priority | Source | Path / Resource | Purpose |
|---:|---|---|---|
| 1 | Current user instruction | Current Codex session request | Highest-priority active wave instruction. |
| 2 | Autonomous master manual | `C:\Comfy_UI_Main\Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md` | Codex behavior and autonomous operating rules. |
| 3 | Completion gate | `C:\Comfy_UI_Main\Plan\Instructions\COMPLETION_DEFINITION_AND_DONE_GATE.md` | Determines whether work can be marked complete. |
| 4 | Active tracker | `C:\Comfy_UI_Main\Plan\Tracker` | Execution state, status, blockers, QA, evidence. |
| 5 | Itemized list | `C:\Comfy_UI_Main\Plan\Items` | Task backlog and implementation scope. |
| 6 | Blueprint / technical plan | `C:\Comfy_UI_Main\Plan` | Authoritative design and architecture reference. |
| 7 | Hydration state | `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration` | Current session state and resume information. |
| 8 | GitHub repo | `https://github.com/KevinSGarrett/Comfy_UI_Main` | Remote backup and synchronization point. |
| 9 | AWS runtime | Account `029530099913`, EC2 `i-0560bf8d143f93bb1` | GPU validation and runtime testing environment. |

## 6. Required session-start location checks

At the beginning of every autonomous session, Codex must:

1. Confirm `C:\Comfy_UI_Main\` exists.
2. Confirm `C:\Comfy_UI_Main\Plan\` exists.
3. Confirm `Plan\Items`, `Plan\Tracker`, and `Plan\Instructions` exist.
4. Read the master manual.
5. Read the current pursuing goal.
6. Read current session state.
7. Read blockers and known issues.
8. Read tracker state.
9. Read itemized list state.
10. Read this location index.
11. Check Git status without exposing secrets.
12. Verify AWS state only when AWS/GPU use is needed.
13. Regenerate local file indexes if files changed materially.

## 7. Required session-end location updates

Before ending a session, Codex must update:

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\PROOF_OF_MOVEMENT_LOG.csv
```

Codex must also update the active Tracker and Itemized List when any item changes status, scope, blocker state, QA state, or done status.

## 8. Local/GitHub/AWS separation rules

| Area | What belongs here | What must not be confused with it |
|---|---|---|
| Local project | Active working files, generated artifacts, scripts, ComfyUI workflows, plan files. | GitHub remote state. |
| GitHub repo | Versioned project backup and synchronization. | Runtime EC2 state or secrets. |
| AWS EC2 | GPU validation, ComfyUI execution, model runtime checks. | Source-of-truth planning state. |
| Tracker | Execution status and proof. | The itemized backlog. |
| Items | Work scope and planned tasks. | Completion proof. |
| Instructions | Operating rules and protocols. | Runtime-generated images/videos/audio. |
| Hydration | Session continuity state. | Permanent architecture source. |

## 9. Codex confusion recovery rule

If Codex is unsure where something belongs, it must:

1. Stop modifying files.
2. Read this index.
3. Read the local directory catalogue.
4. Read the relevant file index.
5. Inspect the actual local path.
6. Use tracker evidence before deciding completion state.
7. Record the confusion and resolution in hydration state.
8. Continue only after establishing the correct path and next action.

## 10. Wave 59 status

Wave 59 creates the location/catalogue system. It does not claim that AWS was contacted, GitHub was contacted, EC2 was started, or Civitai was used. It defines the verification path Codex must follow during later execution waves.
