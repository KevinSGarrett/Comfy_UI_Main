<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# LOCAL_DIRECTORY_CATALOGUE

## 1. Purpose

This catalogue explains the expected local directory layout for `C:\Comfy_UI_Main\` and how Codex Desktop should treat each directory during autonomous work.

The catalogue separates:

- source-of-truth planning files
- continuously updated state files
- generated reports
- QA evidence
- runtime artifacts
- GitHub-syncable files
- non-committable secrets
- AWS/GPU output pullbacks

## 2. Required top-level project layout

```text
C:\Comfy_UI_Main\
  .env
  .git\
  Plan\
  ComfyUI-related project folders
  model / workflow / output folders as defined by the project
```

The exact runtime folders may expand over time. Codex must discover them by scanning the local filesystem, but it must keep `Plan` structured and stable.

## 3. Required Plan layout

```text
C:\Comfy_UI_Main\Plan\
  Blueprint_Source\
  Items\
  Tracker\
  Instructions\
```

| Directory | Role | Update policy | Source-of-truth status |
|---|---|---|---|
| `Plan` | Main project plan root. | Stable, expanded only when needed. | Source-of-truth root for planning. |
| `Plan\Blueprint_Source` | Imported/reference blueprint content. | Read-only unless an explicit blueprint update wave says otherwise. | Authoritative reference, not active tracker state. |
| `Plan\Items` | Itemized work list and coverage records. | Updated whenever scope, decomposition, or item state changes. | Source-of-truth for backlog/scope. |
| `Plan\Tracker` | Execution tracker, completion status, QA state, blockers, evidence. | Updated continuously during autonomous execution. | Source-of-truth for progress/completion. |
| `Plan\Instructions` | Codex operating procedures and session manuals. | Updated by instruction waves and protocol revisions. | Source-of-truth for autonomous behavior. |

## 4. Required Instructions layout

```text
C:\Comfy_UI_Main\Plan\Instructions\
  Indexes\
  Hydration_Rehydration\
  Manifests\
  Reports\
  Source_Context\
  Templates\
  Waves\
```

| Directory | Role | Codex behavior |
|---|---|---|
| `Instructions\Indexes` | File/resource location awareness. | Read at session start; regenerate if stale. |
| `Instructions\Hydration_Rehydration` | Current session memory and resume files. | Read at session start; update before session end and after major decisions. |
| `Instructions\Manifests` | Machine-readable package manifests. | Regenerate each wave/package. |
| `Instructions\Reports` | Delivery and validation reports. | Add per wave; do not overwrite prior reports unless explicitly correcting. |
| `Instructions\Source_Context` | Summaries of source uploads and extracted packages. | Update when new source packages are added. |
| `Instructions\Templates` | Standard templates for done certification, current goal, state, etc. | Read-only unless template upgrade is required. |
| `Instructions\Waves` | Per-wave supplements and wave-specific reports. | Add a new wave folder each wave. |

## 5. Files Codex should update continuously

Codex should update these whenever their information changes:

```text
Plan\Tracker\*
Plan\Items\*
Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
Plan\Instructions\Hydration_Rehydration\RECENT_DECISIONS.md
Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
Plan\Instructions\Hydration_Rehydration\PROOF_OF_MOVEMENT_LOG.csv
```

Codex must update these after meaningful work, not only at the end.

## 6. Files Codex should treat as read-only references

Codex should normally treat these as read-only unless a user explicitly requests a correction or upgrade:

```text
Plan\Blueprint_Source\*
Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md
Plan\Instructions\AI_PROJECT_MANAGER_DYNAMIC_OPERATING_MODEL.md
Plan\Instructions\NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md
Plan\Instructions\PURSUING_GOAL_TEXT_UPDATE_PROTOCOL.md
Plan\Instructions\AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL.md
Plan\Instructions\COMPLETION_DEFINITION_AND_DONE_GATE.md
Plan\Instructions\DAILY_SESSION_REHYDRATION_PROTOCOL.md
Plan\Instructions\Templates\*
```

These files define behavior. They should not be casually modified during implementation work.

## 7. Files Codex should regenerate each wave

Codex should regenerate or append these for each cumulative wave:

```text
Plan\Instructions\Manifests\wave##_package_manifest.json
Plan\Instructions\Reports\WAVE##_DELIVERY_REPORT.md
Plan\Instructions\Reports\WAVE##_VALIDATION_REPORT.json
Plan\Instructions\Reports\WAVE##_FILE_INDEX.md
Plan\Instructions\Waves\Wave##\*
Plan\Instructions\Indexes\Generated\*
```

When cumulative packs are created, Codex must run zip integrity validation and ensure all prior wave material remains present.

## 8. Hydration/rehydration state files

These files are active state, not static documentation:

```text
Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
Plan\Instructions\Hydration_Rehydration\RECENT_DECISIONS.md
Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
Plan\Instructions\Hydration_Rehydration\PROOF_OF_MOVEMENT_LOG.csv
```

Codex must never assume hydration state is permanent design truth. Hydration files describe the current working state.

## 9. Generated outputs and QA evidence

Runtime-generated images, videos, audio, logs, and QA evidence must be kept separate from planning files. The exact output directories may be project-specific, but the planning references must record:

- artifact path
- generation date/time
- workflow used
- model/checkpoint/LoRA used
- prompt and negative prompt
- seed and settings when available
- reviewer model/tool if applicable
- QA score
- pass/fail state
- defect notes
- retest status
- tracker item linked

No runtime artifact should be declared accepted without a matching QA evidence entry.

## 10. Local directory scan behavior

When Codex needs a live file index, it must run or replicate the logic in:

```text
C:\Comfy_UI_Main\Plan\Instructions\Scripts\Generate-Project-Indexes.ps1
```

The live scan must include at least:

```text
C:\Comfy_UI_Main\Plan
C:\Comfy_UI_Main\Plan\Items
C:\Comfy_UI_Main\Plan\Tracker
C:\Comfy_UI_Main\Plan\Instructions
```

The scan must exclude secrets and should not include `.env` contents.
