[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$CodexHome = "C:\Users\kevin\.codex",
  [ValidateRange(5, 1440)][int]$GraceMinutes = 15,
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$now = [DateTimeOffset]::Now
$lanes = @(
  [ordered]@{ name = "cursor"; root = Join-Path $ProjectRoot "runtime_artifacts\agent_handoffs\cursor"; lock = Join-Path $CodexHome "cursor_handoff\cursor_agent.lock"; classification = "CURSOR_HANDOFF_INTERRUPTED" },
  [ordered]@{ name = "claude_subscription"; root = Join-Path $ProjectRoot "runtime_artifacts\agent_handoffs\claude_subscription"; lock = Join-Path $CodexHome "claude_subscription_handoff\claude_subscription.lock"; classification = "CLAUDE_SUBSCRIPTION_HANDOFF_INTERRUPTED" }
)

$results = @()
foreach ($lane in $lanes) {
  $activeLock = $false
  if (Test-Path -LiteralPath $lane.lock -PathType Leaf) {
    try {
      $lock = Get-Content -Raw -LiteralPath $lane.lock | ConvertFrom-Json
      $activeLock = $null -ne (Get-Process -Id ([int]$lock.pid) -ErrorAction SilentlyContinue)
    } catch {
      $activeLock = $true
    }
  }
  if (!(Test-Path -LiteralPath $lane.root -PathType Container)) { continue }
  foreach ($file in Get-ChildItem -LiteralPath $lane.root -Recurse -Filter "handoff_record.json" -File) {
    try { $record = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json } catch { continue }
    if ([string]$record.status -ne "IN_PROGRESS") { continue }
    $started = try { [DateTimeOffset]::Parse([string]$record.started_at) } catch { [DateTimeOffset]$file.LastWriteTime }
    $ageMinutes = $now.Subtract($started).TotalMinutes
    if ($ageMinutes -lt $GraceMinutes) { continue }
    $eligible = -not $activeLock
    if ($Apply -and $eligible) {
      $record.status = "FAIL"
      $record.classification = $lane.classification
      $record.finalized_at = $now.ToString("o")
      $issues = @($record.issues)
      $issues += "Stale IN_PROGRESS record finalized by lock-aware repair after $([Math]::Round($ageMinutes, 1)) minutes with no active worker lock."
      $record.issues = $issues
      [IO.File]::WriteAllText($file.FullName, ($record | ConvertTo-Json -Depth 15), (New-Object Text.UTF8Encoding($false)))
    }
    $results += [ordered]@{ lane = $lane.name; path = $file.FullName; age_minutes = [Math]::Round($ageMinutes, 1); active_lock = $activeLock; eligible = $eligible; repaired = ([bool]$Apply -and $eligible); classification = $lane.classification }
  }
}

[ordered]@{
  status = "PASS"
  classification = $(if ($Apply) { "STALE_AI_WORKER_RECORD_REPAIR_APPLIED" } else { "STALE_AI_WORKER_RECORD_REPAIR_DRY_RUN" })
  applied = [bool]$Apply
  grace_minutes = $GraceMinutes
  stale_record_count = $results.Count
  repairable_record_count = @($results | Where-Object { $_.eligible }).Count
  repaired_record_count = @($results | Where-Object { $_.repaired }).Count
  records = $results
} | ConvertTo-Json -Depth 8
