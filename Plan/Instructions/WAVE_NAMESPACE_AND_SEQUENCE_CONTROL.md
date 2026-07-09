# Wave Namespace And Sequence Control

## Purpose

This file prevents Codex sessions from confusing different wave namespaces and accidentally starting work from the wrong point in the project.

The technical project plan is the singular folder:

```text
C:\Comfy_UI_Main\Plan
```

There is no canonical `C:\Comfy_UI_Main\Plans` folder in the current workspace.

## Wave Namespaces

The project has multiple overlapping wave namespaces. They are not one simple linear build queue.

1. Blueprint and architecture waves
   - Examples: `PROJECT_MANIFEST.json` with `wave_current: 25`, `Plan\README.md` with Wave35-Wave37 organization content, and imported blueprint source files.
   - These describe cumulative architecture and historical/source plans.
   - They are not automatically the current executable task pointer.

2. Instruction and operating-system waves
   - Examples: Wave58-Wave60 instruction, hydration, AWS/EC2, and governance packages.
   - These define how Codex operates.
   - They can be current rules even when they are not current implementation work.

3. Strict AI and source-coverage tracker waves
   - Wave64 is the current strict AI operational coverage layer.
   - Wave65 is the current exhaustive Plan source coverage layer.
   - These are controls and coverage obligations, not proof that every cited evidence label is next implementation work.

4. Runtime evidence/checkpoint labels
   - Examples: `W66_*`, `W68_*`, and similar QA/runtime evidence file names.
   - These are evidence labels for specific runtime lanes, checks, and checkpoints.
   - They must not be treated as the start of the technical build sequence or as an active wave by name alone.

5. Current Mask Factory wave
   - Wave70 is the current Ultimate Mask Factory tracker/items layer.
   - Wave70 remains active while non-blocked, not-complete Wave70 rows exist or while Wave70 authority/gate evidence is unresolved.

6. Deferred physics/deformation waves
   - Waves71-87 are deferred future physics/deformation/simulation layers.
   - They are not next-action implementation work until source-cited activation-gate evidence explicitly proves activation.

## Task Selection Rule

At session start, Codex must choose work from current operational state, not from the highest wave number or from runtime evidence labels.

Selection order:

1. Current explicit user request.
2. Top of `Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md`.
3. Top of `CURRENT_PURSUING_GOAL.md`, `CURRENT_SESSION_STATE.md`, and `RESUME_HERE_NEXT_CODEX_SESSION.md`.
4. Active non-deferred Tracker and Items rows.
5. Current Plan manifests and README files.
6. Historical reports, imported blueprint source, and runtime evidence labels.

If these sources conflict, Codex must write a small steering correction and continue with the highest-priority active, non-deferred, evidence-backed task.

## Six-Hour Audit Enforcement

The six-hour milestone progress auditor must also follow:

```text
C:\Comfy_UI_Main\Plan\Instructions\TECHNICAL_PROJECT_PLAN_SEQUENCE_AUDIT_PROTOCOL.md
```

Audit classification must account for the full audit window, not only the final top hydration state. If wrong-sequence work occurred during the window, the audit must report it as sequence drift or sequence ledger gap even if a later correction restored the current next action.

Stale Items/Tracker package manifests are actionable ledger gaps when their row counts disagree with parsed current CSV row counts. The auditor may make narrow manifest metadata corrections from parsed counts without running broad Wave65/index refreshes.

## Current Sequence Guard

As of 2026-07-08T15:51:59-05:00:

- Do not treat `W68_*` files as the project starting point.
- Do not advance into Wave71+ physics/deformation implementation unless activation-gate evidence proves activation.
- Continue current non-deferred operational work, especially unresolved Wave70 rows and Wave64/Wave65 control obligations.
- Wave70 numbered rows stop at `0178`, but Wave70 is not exhausted while non-blocked, not-complete Wave70 rows or unresolved authority/gate rows remain.

## Manual Gold Mask Dependency Rule

Manual gold-standard mask creation follows:

```text
C:\Comfy_UI_Main\Plan\Instructions\QA\GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md
```

Wave70 rows that require trusted manual gold masks must fail closed with `Blocked_Gold_Mask_Dependency_Missing` until the exact masks pass intake, QA, geometry, and promotion evidence. This does not freeze unrelated Wave70 control, organization, manifest, automation, workflow-structure, evidence, validation-scaffold, or non-mask work.

Candidate, rejected, source-test, or guarded in-progress mask folders must not be consumed as gold-standard evidence, must not trigger mask promotion, and must not activate Wave71+.
