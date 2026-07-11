<#
.SYNOPSIS
Records one user-observed Codex Desktop weekly usage snapshot.

.DESCRIPTION
Writes a compact local JSON record without reading application internals or
credentials. The caller must supply the percentage exactly as displayed and
declare whether the UI reports used or remaining quota.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Mandatory = $true)]
  [ValidateRange(0, 100)]
  [int]$UsagePercent,

  [Parameter(Mandatory = $true)]
  [ValidateSet("UsedPercent", "RemainingPercent")]
  [string]$MetricSemantics,

  [Parameter(Mandatory = $true)]
  [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
  [string]$WeeklyResetAt,

  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$BaselinePath = "",
  [string]$ObservedAt = "",
  [string]$Source = "user_observed_codex_desktop_ui",
  [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($BaselinePath)) {
  $BaselinePath = Join-Path $projectRootFull "runtime_artifacts\agent_handoffs\ai_worker_rollout\CODEX_DESKTOP_USAGE_BOOKMARK_20260709T150020-0500.json"
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
  $OutputDirectory = Join-Path $projectRootFull "runtime_artifacts\agent_handoffs\ai_worker_rollout"
}

if (!(Test-Path -LiteralPath $BaselinePath -PathType Leaf)) {
  throw "Usage baseline not found: $BaselinePath"
}

$baseline = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
if ([string]$baseline.weekly_reset_at -ne $WeeklyResetAt) {
  throw "Weekly reset does not match the baseline. Baseline=$($baseline.weekly_reset_at) supplied=$WeeklyResetAt"
}

$observed = if ([string]::IsNullOrWhiteSpace($ObservedAt)) {
  [DateTimeOffset]::Now
} else {
  [DateTimeOffset]::Parse($ObservedAt)
}
$consumedPercent = if ($MetricSemantics -eq "UsedPercent") { $UsagePercent } else { 100 - $UsagePercent }
$stamp = $observed.ToString("yyyyMMdd'T'HHmmsszzz") -replace ':', ''

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$outputPath = Join-Path $OutputDirectory "CODEX_DESKTOP_USAGE_SNAPSHOT_$stamp.json"

$record = [ordered]@{
  schema_version = 2
  artifact_type = "codex_desktop_usage_snapshot"
  status = "finalized"
  observed_at = $observed.ToString("o")
  timezone = "America/Chicago"
  project = "Comfy_UI_Main"
  usage_metric = "weekly_codex_desktop_usage_percent"
  displayed_usage_percent = $UsagePercent
  metric_semantics = $MetricSemantics
  normalized_consumed_percent = $consumedPercent
  weekly_reset_at = $WeeklyResetAt
  source = $Source
  baseline_path = [System.IO.Path]::GetFullPath($BaselinePath)
  target_reduction_percent = 50
  note = "The displayed percentage and semantics were supplied explicitly; no UI value was inferred."
}

$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outputPath -Encoding UTF8
$record.output_path = $outputPath
$record | ConvertTo-Json -Depth 6
