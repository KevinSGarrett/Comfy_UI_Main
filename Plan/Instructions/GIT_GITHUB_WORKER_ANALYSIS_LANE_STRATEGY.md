# Git/GitHub Worker Analysis Lane Strategy

Updated: 2026-07-10

This strategy defines how Codex Desktop, Cursor CLI, and Claude Code subscription should split Git and GitHub work without giving worker lanes mutation authority.

## Objective

Reduce Codex Desktop usage spent on Git and GitHub investigation by routing read-only diagnosis, evidence extraction, and draft preparation to worker lanes while keeping Codex as the only authority for repository and GitHub mutations.

This lane exists because Git/GitHub work often consumes long Codex turns without directly advancing ComfyUI runtime/orchestration progress. The target behavior is:

1. Workers gather compact Git/GitHub evidence.
2. Workers propose exact safe next commands or draft text.
3. Codex reviews the evidence.
4. Codex alone performs any mutation.
5. Codex immediately returns to concrete ComfyUI progress when Git/GitHub is not blocking.

## Gate Name

Use this mandatory gate when Git/GitHub work exceeds a tiny check:

```text
GIT_GITHUB_WORKER_ANALYSIS_REQUIRED
```

This is a worker-analysis gate, not a worker-authority gate.

## Relationship To The Other Gates

- `CODEX_ONLY_AUTHORITY`: final repository, branch, GitHub, PR, issue, label, release, and checkpoint decisions.
- `CURSOR_FIRST_REQUIRED`: mechanical local file, diff, status, log, CI, and comment extraction.
- `CLAUDE_HEAVY_REVIEW_REQUIRED`: high-effort risk synthesis and checkpoint strategy.
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`: read-only Git/GitHub investigation and draft preparation above threshold.
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`: small local check that stays below all routing thresholds.

`GIT_GITHUB_WORKER_ANALYSIS_REQUIRED` should usually route first to Cursor for extraction, then to Claude only when the extracted evidence needs high-effort synthesis.

## Trigger Thresholds

Codex must use this lane before spending a long turn on Git/GitHub analysis when any of these are true:

- More than 5 changed files are present and their ownership or checkpoint grouping is not already deterministic.
- More than one Git/GitHub failure source is involved.
- The branch, origin, upstream, or PR state is unclear.
- GitHub Actions or CI logs require more than a tiny bounded read.
- PR review comments, issue comments, or requested changes require inventory.
- The checkpoint boundary is unclear.
- The dirty worktree contains generated evidence, runtime artifacts, hydration files, tracker files, or policy files mixed together.
- Large-file, Git LFS, artifact, or binary inclusion risk is present.
- A commit, push, PR, merge, rebase, checkout, reset, or restore is being considered and Codex would need more than 3 minutes of active analysis before deciding.

## Known-Scope Deterministic Fast Path

Do not create a worker handoff only to restate a checkpoint boundary that is already exact. Codex may use `KNOWN_SCOPE_GIT_FAST_PATH` when the current implementation unit declared its include list, every changed path belongs to that unit, no unrelated dirty files exist, branch/upstream state is known, and repository scripts perform the mechanical safety checks.

This fast path covers deterministic status, scoped diff-stat, diff-check, blocked-path, staged-secret, and local/origin verification around Codex-owned mutation. It does not cover uncertain grouping, pre-existing dirty state, Git LFS or binary risk, branch divergence, CI failures, PR review, or GitHub diagnosis. Those remain worker-analysis tasks.

When analysis is required, create a bounded input packet with:

```text
C:\Comfy_UI_Main\tools\New-AIWorkerScopePacket.ps1
```

Supply exact candidate paths or captured read-only evidence. Do not ask Cursor or Claude to perform broad repository discovery when deterministic Git evidence is already available.

## Cursor Responsibilities

Cursor is the first worker for mechanical Git/GitHub analysis:

- summarize `git status --short`;
- summarize `git diff --stat`;
- summarize `git diff --name-only`;
- group changed files by purpose and likely checkpoint;
- identify unrelated or user-owned dirty files that should not be included;
- inspect read-only CI or `gh run view` output when provided or safe to fetch;
- inventory PR comments, issue comments, labels, and requested changes when accessible through read-only local tools;
- identify whether Git/GitHub state is blocking the selected ComfyUI work;
- draft commit-message, PR-body, release-note, or checkpoint-summary candidates.

Cursor must not stage, commit, push, reset, checkout, restore, clean, merge, rebase, create PRs, edit PRs, merge PRs, rerun workflows, cancel workflows, mutate issues, mutate labels, mutate releases, mutate projects, submit reviews, or add reactions.

For GitHub PR, issue, comment, label, reaction, review, release, and metadata reads, prefer the connected GitHub app/connector when available. Use local `gh` only for gaps the connector does not cover well, especially current-branch PR discovery, GitHub Actions logs, and local checkout correlation.

## Claude Responsibilities

Claude subscription is the high-effort Git/GitHub synthesis lane:

- decide whether a checkpoint boundary is coherent after Cursor extraction;
- review risk before a proposed commit or push;
- compare local evidence, Git status, GitHub Actions, and project policy for contradictions;
- recommend whether Git/GitHub state is actually blocking ComfyUI progress;
- critique branch, PR, or checkpoint strategy when Codex would otherwise spend a long reasoning turn.

Claude must not run or recommend unsafe mutation as an action for itself. It may draft exact commands for Codex to review, but Codex is the only executor.

## Codex Responsibilities

Codex keeps final authority for:

- `git add`;
- `git commit`;
- `git push`;
- `git reset`;
- `git checkout`;
- `git restore`;
- `git clean`;
- merge and rebase operations;
- branch creation/deletion/switching;
- PR creation, update, merge, close, or reopen;
- issue/label/milestone/project mutation;
- GitHub Actions rerun/cancel/dispatch;
- deciding whether the current repository state is authoritative enough for runtime/deploy gates.

Codex may run tiny read-only Git checks directly when the work is under threshold. Once the work crosses threshold, Codex must use the worker-analysis lane or record why delegation is unavailable.

## Allowed Read-Only Commands For Worker Evidence

Workers may use read-only commands when the work order permits them:

```text
git status --short
git status --branch --short
git diff --stat
git diff --name-only
git diff --check
git log --oneline -n <bounded>
git branch --show-current
git remote -v
gh auth status
gh run list --limit <bounded>
gh run view <run-id> --log
gh pr view <number-or-url>
gh pr checks <number-or-url>
gh issue view <number-or-url>
```

Workers must not print tokens, credential values, `.env` values, or secret-bearing remotes. If `git remote -v` includes an embedded credential or token-like value, workers must redact it or report only the host/repo shape.

## Output Contract

Every Git/GitHub worker-analysis handoff must return compact labeled output:

- `status:`
- `git_github_scope:`
- `commands_run_read_only:`
- `files_or_items_inspected:`
- `changed_files_grouped:`
- `findings:`
- `risks:`
- `recommended_codex_follow_up:`
- `recommended_codex_commands:`
- `mutation_boundary: Codex-only`
- `blockers:`
- `confidence:`

Promise-style output is not evidence. If a worker returns incomplete output, Codex must retry once with a narrower work order before absorbing the analysis directly.

## Routing Examples

Use Cursor first:

- "Summarize this dirty worktree and group files into checkpoint candidates."
- "Read the failing CI log and extract the failing command, file, and likely fix area."
- "List actionable PR comments and group them by file."

Use Claude after Cursor or directly for heavy synthesis:

- "Given this grouped dirty worktree and project policy, is checkpoint A safe?"
- "Does the branch/PR state block selected-inpaint runtime work?"
- "Which commit strategy minimizes risk and avoids mixing unrelated user changes?"

Keep Codex-only:

- "Stage and commit these exact files."
- "Push this branch."
- "Create or merge a PR."
- "Reset, checkout, restore, clean, merge, or rebase."

## Monitor Requirements

The combined AI worker monitor should score:

- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_analysis_successful_handoffs`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
- `git_github_codex_mutation_authority_preserved`
- `estimated_git_github_codex_minutes_avoided`

Any worker mutation attempt is a policy violation even if the command fails.

## Success Criteria

This lane is working when:

- Codex spends less active time reading diffs, CI logs, PR comments, and branch state.
- Workers return compact Git/GitHub evidence and draft commands.
- Codex only reviews and executes final safe mutations.
- Git/GitHub work stops becoming a loop that delays concrete ComfyUI runtime/orchestration progress.
