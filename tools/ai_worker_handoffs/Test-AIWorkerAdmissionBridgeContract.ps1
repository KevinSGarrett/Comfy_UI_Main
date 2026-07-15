[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$packageRoot = $PSScriptRoot
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $packageRoot "..\..")).Path
$cursorWrapper = Join-Path $packageRoot "cursor\Invoke-CursorAgentHandoff.ps1"
$claudeWrapper = Join-Path $packageRoot "claude\Invoke-ClaudeSubscriptionHandoff.ps1"
$dispatcher = Join-Path $packageRoot "dispatcher\Invoke-AIWorkerDispatcher.ps1"
$pipeline = Join-Path $packageRoot "dispatcher\New-AIWorkerDevelopmentPipeline.ps1"
$agents = Join-Path $repoRoot "AGENTS.md"

$checks = [ordered]@{}
$agentsText = Get-Content -Raw -LiteralPath $agents
$checks.codex_agents_gate_present = $agentsText -match "New-AIWorkerDevelopmentPipeline\.ps1" -and $agentsText -match "AI_WORKER_DIRECT_WRAPPER_BYPASS_BLOCKED"

$cursorBlocked = & $cursorWrapper -TaskName "direct_cursor_bypass_fixture" -WorkOrderText "This must not launch Cursor." | ConvertFrom-Json
$checks.cursor_direct_production_bypass_blocked = $cursorBlocked.status -eq "BLOCKED" -and $cursorBlocked.classification -eq "AI_WORKER_DIRECT_WRAPPER_BYPASS_BLOCKED"

$claudeBlocked = & $claudeWrapper -TaskName "direct_claude_bypass_fixture" -WorkOrderText "This must not launch Claude." | ConvertFrom-Json
$checks.claude_direct_production_bypass_blocked = $claudeBlocked.status -eq "BLOCKED" -and $claudeBlocked.classification -eq "AI_WORKER_DIRECT_WRAPPER_BYPASS_BLOCKED"

$dispatcherText = Get-Content -Raw -LiteralPath $dispatcher
$checks.dispatcher_passes_request_identity = @($dispatcherText -split 'DispatcherRequestId=\$requestId').Count -eq 3

$pipelineText = Get-Content -Raw -LiteralPath $pipeline
$checks.pipeline_routes_by_default = $pipelineText -match '\$routeImmediately=-not\$DeferRouting'
$checks.explicit_deferred_route_supported = $pipelineText -match "AI_WORKER_DEVELOPMENT_PIPELINE_ADMITTED_DEFERRED"

$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
[ordered]@{
  status = $(if ($failed.Count) { "FAIL" } else { "PASS" })
  classification = "AI_WORKER_ADMISSION_BRIDGE_CONTRACT"
  checks = $checks
  failed = $failed
} | ConvertTo-Json -Depth 6
if ($failed.Count) { exit 1 }
