# Technical Project Plan Sequence Audit Protocol

## Purpose

This protocol defines the strict six-hour audit standard for verifying that Codex is building from the technical project plan in the correct development sequence.

The audit must not merely check whether the current top hydration text looks correct. It must determine whether the recent work window included sequence drift, ledger drift, stale manifests, skipped active rows, deferred-wave activation, or runtime-evidence labels being mistaken for project sequence.

## Required Review Scope

Every six-hour milestone auditor run must perform a manifest-driven technical-plan review of:

- `C:\Comfy_UI_Main\Plan\PROJECT_MANIFEST.json`
- `C:\Comfy_UI_Main\Plan\README.md`
- `C:\Comfy_UI_Main\Plan\Instructions\WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md`
- `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration`
- `C:\Comfy_UI_Main\Plan\Items\README.md`
- `C:\Comfy_UI_Main\Plan\Items\Manifests\items_package_manifest.json`
- active and deferred Items CSVs needed to validate current and recently referenced rows
- `C:\Comfy_UI_Main\Plan\Tracker\README.md`
- `C:\Comfy_UI_Main\Plan\Tracker\Manifests\tracker_package_manifest.json`
- active and deferred Tracker CSVs needed to validate current and recently referenced rows
- relevant `C:\Comfy_UI_Main\Plan\Instructions\Waves\Wave*\*_SCOPE.md` files
- recent proof, QA, and evidence indexes for the audit window

The review must parse structured files as structured data where possible. For very large Markdown, CSV, or JSON files, the auditor may use bounded structural reads, counts, hashes, targeted row extraction, headings, manifest fields, and direct row lookups. It must record any bounded or degraded read in `probe_statuses`.

## Exhaustive Sequence Understanding

The auditor must build and record an explicit understanding of:

- current operational layers
- active implementation waves
- deferred planning waves
- runtime evidence namespaces
- current top hydration task
- all recently referenced Tracker and Items rows
- whether each referenced row exists
- whether Items and Tracker agree for each referenced row
- whether package manifests match current CSV row counts
- whether any work in the audit window started from the highest wave number, latest evidence label, or deferred rows instead of active project state

## Required Boolean Fields

Every six-hour audit JSON must include:

- `current_state_aligned`
- `recent_sequence_drift_detected`
- `drift_corrected`
- `residual_ledger_or_manifest_gap`
- `actionable_manifest_maintenance_needed`
- `target_thread_update_needed`

## Classification Rules

If current state is aligned and no recent sequence drift or ledger gap exists, use `MILESTONE_SEQUENCE_PASS`.

If any wrong-sequence work occurred inside the audit window, classify as `MILESTONE_SEQUENCE_DRIFT`, even if later hydration corrected it.

If wrong-sequence work occurred but is already corrected and the remaining issue is stale Items/Tracker/hydration/manifest metadata, classify as `MILESTONE_SEQUENCE_LEDGER_GAP`.

If manifests disagree with actual active Items/Tracker CSV row counts, treat that as actionable manifest maintenance. The auditor may update only the stale manifest fields proven by parsed CSV counts. It must not run broad Wave65/index refreshes as a substitute for this narrow correction.

If top hydration points to a row that is missing, deferred, superseded, or contradicted by Items/Tracker, classify as `MILESTONE_SEQUENCE_DRIFT` and correct `NEXT_ACTION.md` and `CURRENT_PURSUING_GOAL.md` when the correction lock is available.

## Main Session Update Rule

When `recent_sequence_drift_detected` is true, `residual_ledger_or_manifest_gap` is true, or the audit updates Items/Tracker/manifest metadata, the auditor must send or prepare a concise target-thread update for the main Codex session. The message must state:

- classification
- whether current state is aligned
- what drift or ledger gap was found
- what was corrected
- the exact next active row or task

## Mutation Limits

Allowed narrow corrections:

- prepend small source-cited steering blocks to hydration files
- update stale manifest fields proven by current CSV row counts
- update Items/Tracker row status only when source evidence directly proves the exact status change
- write project evidence only for actionable findings

Forbidden routine actions:

- broad Wave65 or index refreshes
- rewriting whole Items/Tracker packages
- activating Wave71+ without activation-gate proof
- treating `W68_*` or other runtime evidence labels as active project sequence
- Git commit, push, stage, reset, checkout, or destructive cleanup
