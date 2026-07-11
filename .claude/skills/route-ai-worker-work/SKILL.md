---
name: route-ai-worker-work
description: Classify and route Comfy_UI_Main work across Codex final authority, Cursor mechanical extraction, Claude subscription heavy reasoning, and read-only Git/GitHub analysis. Use before broad scans, multi-file diagnosis, task selection, strategy synthesis, helper drafting, checkpoint analysis, CI/PR review, or any task expected to consume more than three minutes of Codex reasoning.
---

# Route AI Worker Work

Apply the smallest safe lane before starting broad work. Keep output bounded and preserve Codex final authority.

## Workflow

1. Read `C:\Comfy_UI_Main\CLAUDE.md`.
2. Read only the current authority needed to identify candidate files: top hydration block, active work order, queue row, or manifest link.
3. Select exactly one gate:
   - `CODEX_ONLY_AUTHORITY`
   - `CURSOR_FIRST_REQUIRED`
   - `CLAUDE_HEAVY_REVIEW_REQUIRED`
   - `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
   - `NO_WORKER_NEEDED_UNDER_THRESHOLD`
4. If a worker is needed and paths are known, create a packet with `tools/New-AIWorkerScopePacket.ps1`. Keep the normal scope at 12 files or fewer.
5. Execute only the assigned worker responsibility. Do not rediscover unrelated trees.
6. Return completed compact evidence. Codex reviews, patches, validates, and performs any mutation.

## Lane Choice

Use Cursor first for inventories, path/hash extraction, parser or validator triage, repeated evidence reads, and first-pass helper drafts.

Use Claude as the primary lane for difficult synthesis, contradiction review, architecture/routing critique, and checkpoint/branch/CI/PR risk synthesis. Claude is not merely a second reviewer.

Use Git/GitHub worker analysis when changed-file ownership, checkpoint grouping, branch state, CI logs, PR comments, Git LFS risk, or upstream state is uncertain. Keep all mutation in Codex.

Use `KNOWN_SCOPE_GIT_FAST_PATH` only when the current implementation has an exact include list, all changed files belong to it, no unrelated dirty state exists, branch/upstream is known, and deterministic safety scripts cover the checkpoint.

## Failure Handling

- Retry incomplete output once with a narrower packet.
- Use process-local PowerShell execution-policy bypass only when wrapper loading is blocked.
- Do not repeatedly poll or narrate worker progress.
- After one failed narrow retry, return the failure record and a compact fallback recommendation.

## Output

Include these labels near the beginning:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `recommended Codex follow-up:`

For Git/GitHub analysis, also include `git_github_scope:`, `commands_run_read_only:`, `changed_files_grouped:`, `risks:`, `recommended_codex_commands:`, and `mutation_boundary: Codex-only`.

Read [routing-contract.md](references/routing-contract.md) when exact thresholds, wrappers, or measurement tools are needed.
