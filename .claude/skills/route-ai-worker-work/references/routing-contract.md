# Routing Contract

## Canonical Sources

- Routing: `C:\Comfy_UI_Main\Plan\Instructions\AI_WORKER_LANE_ROUTING_POLICY.md`
- Git/GitHub: `C:\Comfy_UI_Main\Plan\Instructions\GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md`
- Automation: `C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md`
- Cursor policy: `C:\Users\kevin\.codex\cursor_handoff\CURSOR_DELEGATION_POLICY.md`
- Claude policy: `C:\Users\kevin\.codex\claude_subscription_handoff\CLAUDE_SUBSCRIPTION_DELEGATION_POLICY.md`

## Wrappers

- Cursor: `C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1`
- Claude: `C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1`

## Deterministic Tools

- Scope packet: `C:\Comfy_UI_Main\tools\New-AIWorkerScopePacket.ps1`
- Usage snapshot: `C:\Comfy_UI_Main\tools\New-CodexDesktopUsageSnapshot.ps1`
- Usage reduction: `C:\Comfy_UI_Main\tools\Measure-AIWorkerCodexUsageReduction.ps1`

## Hard Triggers

- More than 10 files or one major tree: Cursor extraction.
- More than 3 minutes difficult reasoning: Claude heavy review.
- More than 5 unclassified changed files or uncertain ownership: Git/GitHub worker analysis.
- Incomplete worker output: one narrower retry.
- Exact current-task Git scope with deterministic safety checks: `KNOWN_SCOPE_GIT_FAST_PATH`.

## Authority

Codex alone owns Git/GitHub mutation, AWS/EC2/S3, Jira, masks, Wave gates, final visual QA, Items/Tracker mutation, and final acceptance.
