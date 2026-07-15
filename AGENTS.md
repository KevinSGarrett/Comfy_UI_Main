# Comfy_UI_Main Codex Execution Gate

`C:\Comfy_UI_Main` is the authoritative project root. Before substantive analysis, implementation, semantic review, or Git/GitHub synthesis, create a signed task intent with:

`tools/ai_worker_handoffs/dispatcher/New-AIWorkerDevelopmentPipeline.ps1`

The pipeline routes immediately by default. Use `-DeferRouting` only for a documented diagnostic that must be admitted but intentionally queued later. Do not call the Cursor or Claude wrappers directly for production work; unledgered direct calls fail closed as `AI_WORKER_DIRECT_WRAPPER_BYPASS_BLOCKED`. `-AllowDirectDiagnostic` is limited to explicit capability or wrapper diagnostics and does not count as production delegation.

Route mechanical extraction and bounded drafting to Cursor. Route semantic synthesis, architecture, contradiction review, and test strategy to Claude Sonnet 5. Codex retains final Git/GitHub/AWS/Jira/mask/visual-QA/project-state and acceptance authority.

After a worker packet completes, review it and record `ADOPTED`, `PARTIALLY_ADOPTED`, or `REJECTED` with `Set-AIWorkerDispatchAdoption.ps1`. Do not begin worker-eligible reasoning directly in Codex merely because the intake queue is empty.
