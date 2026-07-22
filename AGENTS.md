# Comfy_UI_Main Codex Execution Gate

`C:\Comfy_UI_Main` is the authoritative project root. Before assigning substantive analysis, implementation, semantic review, or Git/GitHub synthesis to a dispatched worker, create a signed task intent with:

`tools/ai_worker_handoffs/dispatcher/New-AIWorkerDevelopmentPipeline.ps1`

The pipeline routes immediately by default. Use `-DeferRouting` only for a documented diagnostic that must be admitted but intentionally queued later. Do not call the Cursor or Claude wrappers directly for production work; unledgered direct calls fail closed as `AI_WORKER_DIRECT_WRAPPER_BYPASS_BLOCKED`. `-AllowDirectDiagnostic` is limited to explicit capability or wrapper diagnostics and does not count as production delegation.

For the active RunPod Autonomous Campaign Execution and Evidence Compaction pursuing goal, Cursor is not an authorized worker route. Do not create or retry Cursor work for this package. Route bulk architecture, semantic synthesis, contradiction review, test strategy, and bounded acceptance review to signed Claude Sonnet 5 workers. Codex performs exact implementation and retains final Git/GitHub/AWS/Jira/RunPod/coordinator/mask/visual-QA/project-state and acceptance authority. During a separately user-started top-level interactive Cursor shift outside this pursuing goal, that interactive session retains only the bounded authority described below; this does not authorize dispatched Cursor workers for this package.

After a worker packet completes, review it and record `ADOPTED`, `PARTIALLY_ADOPTED`, or `REJECTED` with `Set-AIWorkerDispatchAdoption.ps1`. Do not begin worker-eligible reasoning directly in Codex merely because the intake queue is empty.

## Interactive Cursor/Codex Shift Authority

The user may alternate development shifts between Codex Desktop and a user-started top-level interactive Cursor session. Whichever platform the user intentionally opens for the current shift is the active integration authority. It may analyze, implement, validate, update Plan/Items/Tracker/registries/instructions/evidence, accept work, and perform bounded Git/GitHub mutations through already-configured authentication.

This authority applies only to the interactive top-level session. Signed Cursor/Claude workers, wrappers, scheduled tasks, and nested agents remain bounded workers and may not commit, push, mutate GitHub, or claim final acceptance.

At shift start, reconstruct branch, HEAD, upstream, worktree ownership, active requests, retained worktrees, blockers, and the next actionable tracker item. At shift end, leave a repository-backed handoff with the last pushed commit, validators, dirty ownership boundaries, active requests, blockers, and next action. Do not run overlapping Cursor and Codex integration shifts on the same paths.

Pre-existing dirty or untracked paths are preserved and outside the active session's commit unless explicitly assigned, newly changed by that session from a clean baseline, owned by a signed retained diff, or tied to the current work item by repository evidence. A large dirty worktree does not block exact-path work. Never use `git add -A` or `git add .`; stage only reviewed paths with `git add -- <exact paths>`, inspect the staged diff, and commit a bounded increment. Never read or expose `.env` values or tokens; use configured Git/GitHub authentication through normal commands.

The signed pipeline is mandatory for dispatched worker work. It is not a requirement for the active top-level interactive Cursor session to dispatch its own direct analysis or implementation back to itself.

Interactive Cursor shifts must not false-stop: continue autonomously until end-to-end project/tracker complete per `.cursor/rules/continuous-autonomous-until-project-complete.mdc` (switch lanes on blockers; never treat one row as shift-complete).

## Shared RunPod GPU Capacity Authority

Cross-project GPU admission for the current 48 GB RunPod is governed by
`C:\Users\kevin\.codex\shared_runpod_coordinator\README.md`. Before a GPU-affecting
action, request and validate a capacity lease. CPU-only work never needs a lease.
MaskFactory process presence, `runs/gpu.lock`, `/workspace/tmp/gpu.lock`, and
ComfyUI queue idleness are not by themselves cross-project exclusion authority.
They remain internal workflow/critical-section evidence. Qualified shared work
may run concurrently when the coordinator's 40 GB peak budget, 8 GB reserve,
fresh telemetry, and intensity rules pass. Never kill or steal another owner's
process or internal lock.
