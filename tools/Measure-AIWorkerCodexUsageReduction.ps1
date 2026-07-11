<#
.SYNOPSIS
Measures post-delegation Codex weekly quota burn-rate reduction.

.DESCRIPTION
Normalizes used/remaining percentages into consumed quota and compares the
pre-delegation burn rate with one or two post-delegation observations. HIGH
confidence requires two post-baseline observations that both meet the target;
a single observation is capped at MEDIUM regardless of its result.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Mandatory = $true)]
  [string]$BaselinePath,

  [Parameter(Mandatory = $true)]
  [string]$CurrentSnapshotPath,

  [string]$ConfirmationSnapshotPath = "",

  [ValidateSet("", "UsedPercent", "RemainingPercent")]
  [string]$BaselineMetricSemantics = "",

  [ValidateRange(1, 168)]
  [double]$MinimumObservationHours = 6,

  [ValidateRange(1, 72)]
  [double]$MinimumConfirmationGapHours = 6,

  [ValidateRange(6, 168)]
  [double]$MinimumHighConfidenceObservationHours = 24,

  [ValidateRange(1, 99)]
  [double]$TargetReductionPercent = 50,

  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-ConsumedPercent {
  param(
    [Parameter(Mandatory = $true)][double]$DisplayedPercent,
    [Parameter(Mandatory = $true)][string]$Semantics
  )
  if ($DisplayedPercent -lt 0 -or $DisplayedPercent -gt 100) { throw "Usage percentage must be between 0 and 100." }
  if ($Semantics -eq "UsedPercent") { return $DisplayedPercent }
  if ($Semantics -eq "RemainingPercent") { return 100.0 - $DisplayedPercent }
  throw "Unsupported metric semantics: $Semantics"
}

function Read-UsageSnapshot {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required snapshot missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
}

$baseline = Read-UsageSnapshot -Path $BaselinePath
$current = Read-UsageSnapshot -Path $CurrentSnapshotPath
$confirmation = if ([string]::IsNullOrWhiteSpace($ConfirmationSnapshotPath)) { $null } else { Read-UsageSnapshot -Path $ConfirmationSnapshotPath }
if ([string]::IsNullOrWhiteSpace($BaselineMetricSemantics)) {
  $BaselineMetricSemantics = [string]$baseline.metric_semantics
}
if ($BaselineMetricSemantics -notin @("UsedPercent", "RemainingPercent")) {
  throw "Baseline metric semantics are missing. Record UsedPercent or RemainingPercent in the baseline or pass -BaselineMetricSemantics."
}

$baselineReset = [string]$baseline.weekly_reset_at
$baselineAt = [DateTimeOffset]::Parse([string]$baseline.created_at)
$resetAt = [DateTimeOffset]::new(
  [int]$baselineReset.Substring(0, 4),
  [int]$baselineReset.Substring(5, 2),
  [int]$baselineReset.Substring(8, 2),
  0, 0, 0,
  $baselineAt.Offset
)
$periodStart = $resetAt.AddDays(-7)
if ($baselineAt -le $periodStart) { throw "Baseline timestamp must occur after the weekly period start." }

$baselineDisplayed = [double]$baseline.usage_percent
$baselineConsumed = Get-ConsumedPercent -DisplayedPercent $baselineDisplayed -Semantics $BaselineMetricSemantics
$preHours = ($baselineAt - $periodStart).TotalHours
$preRate = $baselineConsumed / $preHours

function Measure-Snapshot {
  param(
    [Parameter(Mandatory = $true)]$Snapshot,
    [Parameter(Mandatory = $true)][string]$SnapshotPath
  )
  if ([string]$Snapshot.weekly_reset_at -ne $baselineReset) {
    throw "Snapshots cross a weekly reset and cannot be compared. Baseline=$baselineReset current=$($Snapshot.weekly_reset_at)"
  }
  $observedAt = [DateTimeOffset]::Parse([string]$Snapshot.observed_at)
  if ($observedAt -le $baselineAt) { throw "Post-delegation snapshot must be later than the baseline: $SnapshotPath" }
  $semantics = [string]$Snapshot.metric_semantics
  $displayed = [double]$Snapshot.displayed_usage_percent
  $consumed = Get-ConsumedPercent -DisplayedPercent $displayed -Semantics $semantics
  $postHours = ($observedAt - $baselineAt).TotalHours
  $delta = $consumed - $baselineConsumed
  if ($delta -lt 0) { throw "Normalized consumed usage decreased within the same weekly period. Verify UsedPercent versus RemainingPercent semantics." }
  $postRate = $delta / $postHours
  $reduction = if ($preRate -eq 0) { 0.0 } else { (1.0 - ($postRate / $preRate)) * 100.0 }
  return [ordered]@{
    snapshot_path = [System.IO.Path]::GetFullPath($SnapshotPath)
    observed_at = $observedAt.ToString("o")
    metric_semantics = $semantics
    displayed_percent = $displayed
    consumed_percent = [math]::Round($consumed, 2)
    post_delegation_elapsed_hours = [math]::Round($postHours, 2)
    consumed_delta_percent = [math]::Round($delta, 2)
    post_delegation_burn_rate_percent_per_hour = [math]::Round($postRate, 4)
    measured_usage_reduction_percent = [math]::Round($reduction, 2)
    target_met = ($postHours -ge $MinimumObservationHours -and $reduction -ge $TargetReductionPercent)
  }
}

$measurements = @(
  Measure-Snapshot -Snapshot $current -SnapshotPath $CurrentSnapshotPath
)
if ($null -ne $confirmation) {
  $measurements += Measure-Snapshot -Snapshot $confirmation -SnapshotPath $ConfirmationSnapshotPath
}
$measurements = @($measurements | Sort-Object { [DateTimeOffset]::Parse($_.observed_at) })
$final = $measurements[-1]
$observationSufficient = [double]$final.post_delegation_elapsed_hours -ge $MinimumObservationHours
$confirmationGapHours = if ($measurements.Count -ge 2) {
  ([DateTimeOffset]::Parse($measurements[-1].observed_at) - [DateTimeOffset]::Parse($measurements[-2].observed_at)).TotalHours
} else { 0.0 }
$twoTargetMet = ($measurements.Count -ge 2 -and @($measurements | Where-Object { -not $_.target_met }).Count -eq 0)
$highConfidenceReady = (
  $twoTargetMet -and
  [double]$final.post_delegation_elapsed_hours -ge $MinimumHighConfidenceObservationHours -and
  $confirmationGapHours -ge $MinimumConfirmationGapHours -and
  [double]$final.consumed_delta_percent -ge 1
)
$confidence = if (-not $observationSufficient) {
  "LOW_INSUFFICIENT_OBSERVATION"
} elseif ($highConfidenceReady) {
  "HIGH_TWO_MEASURED_PERIODS"
} else {
  "MEDIUM_SINGLE_OR_UNCONFIRMED_MEASUREMENT"
}

$result = [ordered]@{
  schema_version = 2
  artifact_type = "ai_worker_codex_usage_reduction_measurement"
  status = $(if ($observationSufficient) { "measured" } else { "insufficient_observation" })
  finalized_at = [DateTimeOffset]::Now.ToString("o")
  baseline_path = [System.IO.Path]::GetFullPath($BaselinePath)
  weekly_period_start = $periodStart.ToString("o")
  weekly_reset_at = $baselineReset
  baseline_observed_at = $baselineAt.ToString("o")
  baseline_metric_semantics = $BaselineMetricSemantics
  baseline_consumed_percent = [math]::Round($baselineConsumed, 2)
  pre_delegation_elapsed_hours = [math]::Round($preHours, 2)
  pre_delegation_burn_rate_percent_per_hour = [math]::Round($preRate, 4)
  post_delegation_measurements = $measurements
  measured_usage_reduction_percent = $final.measured_usage_reduction_percent
  target_reduction_percent = $TargetReductionPercent
  target_met = ($observationSufficient -and [bool]$final.target_met)
  consecutive_target_met_measurements = $(if ($twoTargetMet) { 2 } elseif ($final.target_met) { 1 } else { 0 })
  confirmation_gap_hours = [math]::Round($confirmationGapHours, 2)
  high_confidence_ready = $highConfidenceReady
  confidence = $confidence
  formula = "100 * (1 - post_delegation_burn_rate / pre_delegation_burn_rate)"
  high_confidence_requirements = @(
    "two post-baseline measurements both meet target",
    "final observation is at least $MinimumHighConfidenceObservationHours hours after baseline",
    "measurements are at least $MinimumConfirmationGapHours hours apart",
    "final consumed delta is at least 1 percentage point"
  )
}

if (![string]::IsNullOrWhiteSpace($OutputPath)) {
  $outputParent = Split-Path -Parent $OutputPath
  if (![string]::IsNullOrWhiteSpace($outputParent)) { New-Item -ItemType Directory -Path $outputParent -Force | Out-Null }
  $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
}

$result | ConvertTo-Json -Depth 8
