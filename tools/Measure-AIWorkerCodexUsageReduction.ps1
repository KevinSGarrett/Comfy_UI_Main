<#
.SYNOPSIS
Measures post-delegation Codex weekly quota burn-rate reduction.

.DESCRIPTION
Normalizes used/remaining percentages into consumed quota, calculates the
pre-delegation burn rate from the weekly period start to the baseline bookmark,
and compares it with the post-delegation burn rate through a current snapshot.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Mandatory = $true)]
  [string]$BaselinePath,

  [Parameter(Mandatory = $true)]
  [string]$CurrentSnapshotPath,

  [Parameter(Mandatory = $true)]
  [ValidateSet("UsedPercent", "RemainingPercent")]
  [string]$BaselineMetricSemantics,

  [ValidateRange(1, 168)]
  [double]$MinimumObservationHours = 6,

  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-ConsumedPercent {
  param(
    [Parameter(Mandatory = $true)][double]$DisplayedPercent,
    [Parameter(Mandatory = $true)][string]$Semantics
  )
  if ($DisplayedPercent -lt 0 -or $DisplayedPercent -gt 100) {
    throw "Usage percentage must be between 0 and 100."
  }
  if ($Semantics -eq "UsedPercent") { return $DisplayedPercent }
  if ($Semantics -eq "RemainingPercent") { return 100.0 - $DisplayedPercent }
  throw "Unsupported metric semantics: $Semantics"
}

foreach ($path in @($BaselinePath, $CurrentSnapshotPath)) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required snapshot missing: $path" }
}

$baseline = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
$current = Get-Content -LiteralPath $CurrentSnapshotPath -Raw | ConvertFrom-Json

$baselineReset = [string]$baseline.weekly_reset_at
$currentReset = [string]$current.weekly_reset_at
if ($baselineReset -ne $currentReset) {
  throw "Snapshots cross a weekly reset and cannot be compared. Baseline=$baselineReset current=$currentReset"
}

$baselineAt = [DateTimeOffset]::Parse([string]$baseline.created_at)
$currentAt = [DateTimeOffset]::Parse([string]$current.observed_at)
if ($currentAt -le $baselineAt) { throw "Current snapshot must be later than the baseline." }

$resetOffset = $baselineAt.Offset
$resetAt = [DateTimeOffset]::new(
  [int]$baselineReset.Substring(0, 4),
  [int]$baselineReset.Substring(5, 2),
  [int]$baselineReset.Substring(8, 2),
  0, 0, 0,
  $resetOffset
)
$periodStart = $resetAt.AddDays(-7)
if ($baselineAt -le $periodStart) { throw "Baseline timestamp must occur after the weekly period start." }

$baselineDisplayed = [double]$baseline.usage_percent
$baselineConsumed = Get-ConsumedPercent -DisplayedPercent $baselineDisplayed -Semantics $BaselineMetricSemantics
$currentSemantics = [string]$current.metric_semantics
$currentDisplayed = [double]$current.displayed_usage_percent
$currentConsumed = Get-ConsumedPercent -DisplayedPercent $currentDisplayed -Semantics $currentSemantics

$preHours = ($baselineAt - $periodStart).TotalHours
$postHours = ($currentAt - $baselineAt).TotalHours
$postConsumedDelta = $currentConsumed - $baselineConsumed
if ($postConsumedDelta -lt 0) {
  throw "Normalized consumed usage decreased within the same weekly period. Verify UsedPercent versus RemainingPercent semantics."
}

$preRate = $baselineConsumed / $preHours
$postRate = $postConsumedDelta / $postHours
$reduction = if ($preRate -eq 0) { 0.0 } else { (1.0 - ($postRate / $preRate)) * 100.0 }
$reductionRounded = [math]::Round($reduction, 2)
$observationSufficient = $postHours -ge $MinimumObservationHours
$confidence = if (-not $observationSufficient) {
  "LOW_INSUFFICIENT_OBSERVATION"
} elseif ($postHours -ge 24 -and $postConsumedDelta -ge 1) {
  "HIGH"
} else {
  "MEDIUM"
}

$result = [ordered]@{
  schema_version = 1
  artifact_type = "ai_worker_codex_usage_reduction_measurement"
  status = $(if ($observationSufficient) { "measured" } else { "insufficient_observation" })
  finalized_at = [DateTimeOffset]::Now.ToString("o")
  baseline_path = [System.IO.Path]::GetFullPath($BaselinePath)
  current_snapshot_path = [System.IO.Path]::GetFullPath($CurrentSnapshotPath)
  weekly_period_start = $periodStart.ToString("o")
  weekly_reset_at = $baselineReset
  baseline_observed_at = $baselineAt.ToString("o")
  current_observed_at = $currentAt.ToString("o")
  baseline_metric_semantics = $BaselineMetricSemantics
  current_metric_semantics = $currentSemantics
  baseline_consumed_percent = [math]::Round($baselineConsumed, 2)
  current_consumed_percent = [math]::Round($currentConsumed, 2)
  pre_delegation_elapsed_hours = [math]::Round($preHours, 2)
  post_delegation_elapsed_hours = [math]::Round($postHours, 2)
  pre_delegation_burn_rate_percent_per_hour = [math]::Round($preRate, 4)
  post_delegation_burn_rate_percent_per_hour = [math]::Round($postRate, 4)
  measured_usage_reduction_percent = $reductionRounded
  target_reduction_percent = 50
  target_met = ($observationSufficient -and $reduction -ge 50)
  confidence = $confidence
  formula = "100 * (1 - post_delegation_burn_rate / pre_delegation_burn_rate)"
}

if (![string]::IsNullOrWhiteSpace($OutputPath)) {
  $outputParent = Split-Path -Parent $OutputPath
  if (![string]::IsNullOrWhiteSpace($outputParent)) { New-Item -ItemType Directory -Path $outputParent -Force | Out-Null }
  $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
}

$result | ConvertTo-Json -Depth 6
