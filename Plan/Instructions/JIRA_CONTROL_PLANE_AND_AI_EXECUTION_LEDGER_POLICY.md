# Jira Control Plane and AI Execution Ledger Policy

Decision timestamp: 2026-07-09T00:54:24-05:00

This project must treat the CU Jira board as a control-plane plus curated active-board view, not as the full autonomous execution ledger.

Latest proof-reuse update: 2026-07-09T01:23:58-05:00

Imported Jira rows, Jira issue status, Jira issue count, Jira cleanup drift, or Jira backlog text must not recreate, reopen, or re-run work that the local execution ledger already proves complete or pass-with-notes. Completed local/AWS proof in `Plan\Instructions\QA\Evidence`, `Plan\Tracker\Evidence`, `Workflows`, and `runtime_artifacts` remains authoritative for execution state.

## Jira Scope

Jira project CU may contain:

- The project-level Feature/Initiative for ComfyUI delivery.
- The 18 imported domain Epics that summarize the major work areas.
- A small, intentionally selected set of current user-facing milestones or active coordination tickets when a human-readable board view is needed.
- The curated active Jira board issues generated from `C:\Comfy_UI_Main\Jira\19_CURATED_ACTIVE_BOARD`, labeled `aij-curated-active`, when they are deduped against local evidence and linked to existing Epics.

Jira project CU must not contain:

- The mechanically expanded Wave8 execution pack as individual Jira issues.
- Bulk-imported 14,270 Stories, 71,350 Tasks, and 142,700 Sub-tasks.
- Automatic one-row-per-item or one-row-per-tracker mirrors from `Plan\Items`, `Plan\Tracker`, generated evidence, QA rows, or runtime artifacts.
- Scheduled automation output that creates Jira issues without an explicit bounded scope and human approval.
- Imported Jira Stories, Tasks, or Sub-tasks that cause Codex or cron jobs to redo already-proven ComfyUI runtime, AWS, lane-smoke, QA, mask, or evidence work.

Current curated active board baseline:

- `C:\Comfy_UI_Main\Jira\19_CURATED_ACTIVE_BOARD\curated_active_jira_issues.csv`
- `C:\Comfy_UI_Main\Jira\19_CURATED_ACTIVE_BOARD\curated_active_jira_apply_result.json`
- `C:\Comfy_UI_Main\Jira\19_CURATED_ACTIVE_BOARD\curated_active_jira_live_verify.json`

This curated board is intentionally not a replay of the Wave8 full import pack. It contains only current active/not-completed coordination rows selected after evidence reconciliation: open Wave64 rows that still need exact direct evidence, explicit Wave64 blockers, and compressed Wave70 gate blockers. Completed/local-ready Wave64 rows, Wave65 planned backlog rows, and deferred Waves71-87 rows are intentionally excluded.

## Local Ledger Scope

The authoritative autonomous execution ledger remains local:

- `C:\Comfy_UI_Main\Plan\Items`
- `C:\Comfy_UI_Main\Plan\Tracker`
- `C:\Comfy_UI_Main\Plan\Instructions`
- `C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence`
- `C:\Comfy_UI_Main\Plan\Tracker\Evidence`
- `C:\Comfy_UI_Main\runtime_artifacts`

Atomic AI work rows, child work items, proof records, package manifests, QA evidence, and runtime blockers belong in the local ledger unless a narrow Jira coordination ticket is explicitly selected.

## Proof Reuse Boundary

Jira may summarize current state, but it is not execution authority. Before acting on any Jira issue, imported Jira row, Jira cleanup finding, Jira automation output, or Jira-derived task text, Codex and scheduled jobs must check the local proof ledger first.

If local evidence already proves the same workflow/request/input/model route, the correct action is to reuse or cite the existing proof, not to recreate the work.

Current explicit baseline example:

- `sdxl_realvisxl_controlnet_canny_lane` has W68 AWS/EC2 target-runtime smoke proof with generation, S3 sync, pullback/hash verification, technical QA, and visual QA.
- The same lane also has 2026-07-09 local package smoke proof with generated image plus diagnostic control map.
- Imported Jira items must not send the project back to baseline Canny local smoke, Canny AWS smoke, Canny deploy-bundle recreation, or equivalent already-proven setup work unless the workflow/request/input/model route changed, evidence is missing/corrupt, or the user intentionally selects final certification or changed-variant target proof.

The general runtime proof reuse rule is defined in:

```text
C:\Comfy_UI_Main\Plan\Instructions\QA\RUNTIME_PROOF_REUSE_AND_NO_RERUN_PROTOCOL.md
```

## Importer Boundary

The Jira importer session is `019f452c-76e8-7312-9fe0-2ade82f19651`.

That session must not continue importing the full 228,339-row pack into Jira. Its correct cleanup role is:

- Stop any active `jira_api_importer.py import-issues` process.
- Preserve the imported Feature/Initiative, 18 Epics, and curated active issues labeled `aij-curated-active`.
- Delete imported Story, Task, and Sub-task rows from Jira CU using the resumable cleanup script:

```text
C:\Comfy_UI_Main\Jira\16_WAVE8_IMPORT_READY_JIRA_PACK\cleanup_jira_control_plane.py
```

Cleanup state and audit files live under:

```text
C:\Comfy_UI_Main\Jira\16_WAVE8_IMPORT_READY_JIRA_PACK\_jira_api_import_state
```

The old full import supervisor is not an active execution route. `jira_full_import_supervisor.py` must abort unless a future user explicitly authorizes a bounded import policy change. `jira_api_importer.py import-issues` must remain blocked by default unless `--allow-bulk-import` is passed for an explicitly approved bounded import.

## Automation Boundary

Scheduled ComfyUI agents targeting session `019f422f-88b1-7382-872b-21de2089e983` must read this policy before any Jira-related action.

They may inspect Jira cleanup state and report drift, but they must not:

- Rebuild the Jira board from the full local Items/Tracker ledger.
- Create new Jira Stories, Tasks, or Sub-tasks from every local row.
- Delete or overwrite the curated active Jira issues labeled `aij-curated-active` unless a fresh local evidence reconciliation proves the corresponding item is complete, obsolete, or superseded.
- Treat Jira issue count as project completion proof.
- Treat Jira issue status or imported Jira backlog rows as authority to recreate already-completed local/AWS proof.
- Re-run baseline Canny local/AWS proof, Wave64/Wave65 hygiene, route alignment, or completed package smoke because a Jira issue says a source section is still open.
- Interrupt current ComfyUI runtime/orchestration work to do Jira bookkeeping unless the user explicitly selects Jira as the active task.

## Working Rule

Use Jira for executive/project visibility. Use the local Plan/Items/Tracker/evidence system for 24/7 autonomous execution detail.

When Jira and local proof disagree, preserve Jira as a visibility/control-plane signal and let local source-cited evidence decide execution state. If Jira needs correction, record cleanup or synchronization evidence; do not redo the underlying ComfyUI work merely to satisfy Jira.
