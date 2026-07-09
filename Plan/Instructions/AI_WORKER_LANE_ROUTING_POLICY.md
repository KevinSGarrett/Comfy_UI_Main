# AI Worker Lane Routing Policy

Updated: 2026-07-09

This policy defines how Codex Desktop, Cursor CLI, and Claude Code subscription work together for Comfy_UI_Main.

## Objective

Reduce Codex Desktop usage by moving bounded worker tasks to Cursor and high-effort synthesis tasks to Claude Code subscription while keeping Codex as final project authority.

## Lane 1: Codex Desktop Final Authority

Codex owns:

- final project decisions and user-facing summaries;
- visual QA and final image/video judgment;
- Git checkpoint, commit, push, reset, checkout, and branch decisions;
- AWS, EC2, S3, live runtime, and ComfyUI generation decisions;
- mask promotion, Wave70 hard gates, Wave71+ activation, and Jira mutation;
- Items/Tracker status mutation.

Codex should not spend long active turns doing broad mechanical scans when Cursor or Claude can produce compact evidence.

## Lane 2: Cursor First Worker

Cursor is the default first worker for:

- broad local inventories;
- evidence extraction from many files;
- parser and validator triage;
- helper or script first drafts in narrow scopes;
- bookmark-resume diagnosis;
- repetitive file/path/hash summaries.

Use:

```text
C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1
```

Default read-only mode is `ask`. Use `plan` only after `ask` is insufficient. Incomplete promise-style output is not evidence.

## Lane 3: Claude Code Subscription

Claude subscription is the high-effort Sonnet lane for:

- difficult strategy synthesis;
- contradiction review across plans and policies;
- architecture or routing critique;
- second-pass review after Cursor extraction;
- heavy reasoning tasks that would otherwise consume a long Codex Desktop turn.

Use:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

The wrapper must verify:

- `loggedIn: true`
- `authMethod: claude.ai`
- `apiProvider: firstParty`
- no `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or `ANTHROPIC_BASE_URL` environment fallback

Default model is `sonnet`. Use `--Effort medium` for routine synthesis, `--Effort high` for difficult review, and `--Effort xhigh` or `--Effort max` only for unusually heavy work.

## Routing Order

1. If the task involves final authority, live runtime, masks, Git, Jira, S3, EC2, or visual QA, keep it in Codex.
2. If the task is mechanical local reading, inventory, triage, or drafting, send it to Cursor first.
3. If the task is hard synthesis or strategy review, use Claude subscription after Cursor extraction or as the primary heavy-review lane.
4. Codex reviews compact worker evidence and decides the final action.

## Output Contract

Worker handoffs must return:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `recommended Codex follow-up:`

Codex should retry narrower or classify the lane as unavailable when the output is incomplete.

## Forbidden Delegation

Do not delegate these final decisions to Cursor or Claude:

- live EC2 start/stop;
- S3 upload;
- ComfyUI generation;
- Git mutation;
- Jira mutation;
- mask promotion or Wave70 hard gates;
- Wave71+ activation;
- final visual QA approval;
- Items/Tracker status mutation.
