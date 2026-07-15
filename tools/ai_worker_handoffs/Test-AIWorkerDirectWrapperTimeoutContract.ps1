[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$cursorPath = Join-Path $PSScriptRoot "cursor\Invoke-CursorAgentHandoff.ps1"
$claudePath = Join-Path $PSScriptRoot "claude\Invoke-ClaudeSubscriptionHandoff.ps1"
$cursor = Get-Content -Raw -LiteralPath $cursorPath
$claude = Get-Content -Raw -LiteralPath $claudePath

$checks = [ordered]@{
  cursor_bounded_process_tree_stop = ($cursor -match 'function Stop-WorkerProcessTreeBounded' -and $cursor -match 'Stop-WorkerProcessTreeBounded -Process \$proc')
  claude_bounded_process_tree_stop = ($claude -match 'function Stop-WorkerProcessTreeBounded' -and $claude -match 'Stop-WorkerProcessTreeBounded -Process \$proc')
  no_unbounded_taskkill_invocation = ($cursor -notmatch '&\s+taskkill\.exe' -and $claude -notmatch '&\s+taskkill\.exe')
  claude_timeout_scope_only_finalization = ($claude -match '\$workerTimedOut = \$true' -and $claude -match 'Skipped the unbounded whole-worktree fingerprint after timeout')
  claude_normal_failure_keeps_drift_attribution = ($claude -match '\$null -ne \$worktreeBefore -and -not \$workerTimedOut')
}
$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
[ordered]@{
  status = $(if ($failed.Count) { "FAIL" } else { "PASS" })
  classification = "AI_WORKER_DIRECT_WRAPPER_TIMEOUT_CONTRACT"
  checks = $checks
  failed = $failed
} | ConvertTo-Json -Depth 5
if ($failed.Count) { exit 1 }
