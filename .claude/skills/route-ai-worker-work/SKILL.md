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
   - `CLAUDE_SONNET_PRIMARY_REQUIRED`
   - `CLAUDE_OPUS_ESCALATION_REQUIRED`
   - `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
   - `DETERMINISTIC_FAST_PATH`
4. If a worker is needed and paths are known, create a packet with `tools/New-AIWorkerScopePacket.ps1`. Keep normal scope at 12 files or fewer and 524,288 aggregate bytes, then pass it through `-ScopePacketPath`. Prefer compact authority excerpts over full hydration ledgers.
5. Execute only the assigned worker responsibility. Do not rediscover unrelated trees.
6. Return completed compact evidence. Codex reviews, patches, validates, and performs any mutation.

## Lane Choice

Use Cursor first for inventories, path/hash extraction, parser or validator triage, repeated evidence reads, and first-pass helper drafts.

Use plain `gpt-5.3-codex` for Cursor. Do not use fast Cursor variants.

Use exact `claude-sonnet-5` as the primary lane for difficult synthesis, contradiction review, architecture/routing critique, test strategy, and checkpoint/branch/CI/PR risk synthesis. Sonnet should perform the first substantive semantic pass when reasoning is the hard part.

Use exact `claude-opus-4-8` only when the centralized escalation contract passes: unresolved or low-confidence Sonnet, a high-severity issue after one remediation, at least three subsystems or two authority domains, material evidence conflict, or more than about 15 minutes of otherwise necessary Codex reasoning. Require one decision-unit ID, one reason, a hash-bound packet, prior Sonnet evidence unless the direct exception is approved, and the two-per-day pilot ceiling.

Review budget: Cursor extraction if needed, one Sonnet pass, Codex remediation/final authority, and at most one Sonnet confirmation. Use one Opus adjudication instead of a third Sonnet review when the remaining issue qualifies.

Use Git/GitHub worker analysis when changed-file ownership, checkpoint grouping, branch state, CI logs, PR comments, Git LFS risk, or upstream state is uncertain. Keep all mutation in Codex.

For Git LFS work, require the Cursor wrapper `-RequireGitLfs` preflight. Missing capability is `CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS`; use the validated Windows evidence bridge only as a bounded contingency. Claude synthesizes extracted LFS evidence and does not replace Cursor's mechanical extraction.

Use `KNOWN_SCOPE_GIT_FAST_PATH` only when the current implementation has an exact include list, all changed files belong to it, no unrelated dirty state exists, branch/upstream is known, and deterministic safety scripts cover the checkpoint.

## Failure Handling

- Retry incomplete output once with a narrower packet.
- Do not escalate incomplete promise-style output directly to Opus.
- Let the Cursor wrapper apply process-local PowerShell execution-policy bypass internally.
- Require `-AllowBroadDiscovery -BroadDiscoveryReason` for any whole-tree exception; otherwise the wrapper must reject it.
- Keep normal Cursor timeouts at 600 seconds or less.
- Do not repeatedly poll or narrate worker progress.
- After one failed narrow retry, return the failure record and a compact fallback recommendation.

## Output

Include these labels near the beginning:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `confidence:`
- `recommended Codex follow-up:`

Opus results also include `escalation outcome:`.

For Git/GitHub analysis, also include `git_github_scope:`, `commands_run_read_only:`, `changed_files_grouped:`, `risks:`, `recommended_codex_commands:`, and `mutation_boundary: Codex-only`.

Read [routing-contract.md](references/routing-contract.md) when exact thresholds, wrappers, or measurement tools are needed.
