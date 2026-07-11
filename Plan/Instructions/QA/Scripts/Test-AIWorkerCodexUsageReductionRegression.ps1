<#
.SYNOPSIS
Runs disposable regression cases for Codex usage burn-rate measurement.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
$measureScript = Join-Path $ProjectRoot "tools\Measure-AIWorkerCodexUsageReduction.ps1"
$netProxyScript = Join-Path $ProjectRoot "tools\Measure-AIWorkerNetUsageReductionProxy.ps1"
if (!(Test-Path -LiteralPath $measureScript -PathType Leaf)) { throw "Measurement script missing: $measureScript" }
if (!(Test-Path -LiteralPath $netProxyScript -PathType Leaf)) { throw "Net proxy script missing: $netProxyScript" }

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ai_worker_usage_regression_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
  $baselinePath = Join-Path $tempRoot "baseline.json"
  $usedPath = Join-Path $tempRoot "used.json"
  $remainingPath = Join-Path $tempRoot "remaining.json"
  $confirmationPath = Join-Path $tempRoot "confirmation.json"

  @{
    created_at = "2026-07-09T12:00:00-05:00"
    usage_percent = 48
    weekly_reset_at = "2026-07-15"
  } | ConvertTo-Json | Set-Content -LiteralPath $baselinePath -Encoding UTF8

  @{
    observed_at = "2026-07-10T12:00:00-05:00"
    displayed_usage_percent = 60
    metric_semantics = "UsedPercent"
    weekly_reset_at = "2026-07-15"
  } | ConvertTo-Json | Set-Content -LiteralPath $usedPath -Encoding UTF8

  @{
    observed_at = "2026-07-10T12:00:00-05:00"
    displayed_usage_percent = 40
    metric_semantics = "RemainingPercent"
    weekly_reset_at = "2026-07-15"
  } | ConvertTo-Json | Set-Content -LiteralPath $remainingPath -Encoding UTF8

  @{
    observed_at = "2026-07-11T12:00:00-05:00"
    displayed_usage_percent = 72
    metric_semantics = "UsedPercent"
    weekly_reset_at = "2026-07-15"
  } | ConvertTo-Json | Set-Content -LiteralPath $confirmationPath -Encoding UTF8

  $used = & $measureScript -BaselinePath $baselinePath -CurrentSnapshotPath $usedPath -BaselineMetricSemantics UsedPercent | ConvertFrom-Json
  $remaining = & $measureScript -BaselinePath $baselinePath -CurrentSnapshotPath $remainingPath -BaselineMetricSemantics UsedPercent | ConvertFrom-Json
  $confirmed = & $measureScript -BaselinePath $baselinePath -CurrentSnapshotPath $usedPath -ConfirmationSnapshotPath $confirmationPath -BaselineMetricSemantics UsedPercent | ConvertFrom-Json
  $strongProxy = & $netProxyScript -WorkerEligibleCounterfactualMinutes 200 -CodexFinalAuthorityMinutes 50 -CodexReviewAndValidationMinutes 12 -CodexFallbackRecoveryMinutes 2 -CodexWorkerOrchestrationMinutes 4 -IncrementalScheduledCodexMinutes 2 -UsefulHandoffs 23 -FailedHandoffs 2 -ScopePacketCompliancePercent 95 | ConvertFrom-Json
  $weakProxy = & $netProxyScript -WorkerEligibleCounterfactualMinutes 100 -CodexFinalAuthorityMinutes 100 -CodexReviewAndValidationMinutes 20 -CodexFallbackRecoveryMinutes 15 -CodexWorkerOrchestrationMinutes 10 -IncrementalScheduledCodexMinutes 10 -UsefulHandoffs 15 -FailedHandoffs 10 -ScopePacketCompliancePercent 20 -MalformedPathOrWriteScopeViolations 1 | ConvertFrom-Json

  $checks = @(
    [pscustomobject]@{ name = "used_semantics_measured"; passed = ($used.status -eq "measured") },
    [pscustomobject]@{ name = "remaining_semantics_normalized"; passed = ([double]$remaining.post_delegation_measurements[0].consumed_percent -eq 60) },
    [pscustomobject]@{ name = "semantic_paths_match"; passed = ([double]$used.measured_usage_reduction_percent -eq [double]$remaining.measured_usage_reduction_percent) },
    [pscustomobject]@{ name = "formula_is_deterministic"; passed = ($used.formula -eq "100 * (1 - post_delegation_burn_rate / pre_delegation_burn_rate)") },
    [pscustomobject]@{ name = "single_measurement_capped_medium"; passed = ($used.confidence -eq "MEDIUM_SINGLE_OR_UNCONFIRMED_MEASUREMENT" -and -not $used.high_confidence_ready) },
    [pscustomobject]@{ name = "two_target_measurements_required_for_high"; passed = ($confirmed.confidence -eq "HIGH_TWO_MEASURED_PERIODS" -and $confirmed.high_confidence_ready) },
    [pscustomobject]@{ name = "strong_proxy_capped_medium"; passed = ($strongProxy.confidence -eq "MEDIUM_PROXY_CAP_REQUIRES_DIRECT_MEASUREMENT") },
    [pscustomobject]@{ name = "weak_proxy_stays_low"; passed = ($weakProxy.confidence -eq "LOW_PROXY_THRESHOLDS_NOT_MET") }
  )
  $failed = @($checks | Where-Object { -not $_.passed })
  $result = [ordered]@{
    status = $(if ($failed.Count -eq 0) { "PASS" } else { "FAIL" })
    check_count = $checks.Count
    failed_count = $failed.Count
    checks = $checks
  }
  $result | ConvertTo-Json -Depth 6
  if ($failed.Count -gt 0) { exit 1 }
} finally {
  if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
