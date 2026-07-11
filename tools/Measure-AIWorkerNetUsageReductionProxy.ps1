<#
.SYNOPSIS
Calculates a conservative net proxy for total Codex Desktop usage reduction.

.DESCRIPTION
Unlike worker-only avoided-minute estimates, this proxy includes final-authority
work and subtracts Codex review, fallback, orchestration, direct eligible work,
and incremental scheduled-automation overhead. Proxy confidence is capped at
MEDIUM until direct quota snapshots satisfy the measured confidence gate.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Mandatory = $true)][ValidateRange(0, 100000)][double]$WorkerEligibleCounterfactualMinutes,
  [Parameter(Mandatory = $true)][ValidateRange(0, 100000)][double]$CodexFinalAuthorityMinutes,
  [ValidateRange(0, 100000)][double]$CodexReviewAndValidationMinutes = 0,
  [ValidateRange(0, 100000)][double]$CodexFallbackRecoveryMinutes = 0,
  [ValidateRange(0, 100000)][double]$CodexWorkerOrchestrationMinutes = 0,
  [ValidateRange(0, 100000)][double]$DirectCodexWorkerEligibleMinutes = 0,
  [ValidateRange(0, 100000)][double]$IncrementalScheduledCodexMinutes = 0,
  [ValidateRange(0, 100000)][int]$UsefulHandoffs = 0,
  [ValidateRange(0, 100000)][int]$FailedHandoffs = 0,
  [ValidateRange(0, 100)][double]$ScopePacketCompliancePercent = 0,
  [ValidateRange(0, 100000)][int]$DirectCodexViolations = 0,
  [ValidateRange(0, 100000)][int]$MalformedPathOrWriteScopeViolations = 0,
  [ValidateRange(0, 100000)][int]$StaleOrInterruptedRecords = 0,
  [ValidateRange(1, 99)][double]$TargetReductionPercent = 50,
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$totalCounterfactual = $WorkerEligibleCounterfactualMinutes + $CodexFinalAuthorityMinutes
$codexDelegationOverhead = (
  $CodexReviewAndValidationMinutes +
  $CodexFallbackRecoveryMinutes +
  $CodexWorkerOrchestrationMinutes +
  $DirectCodexWorkerEligibleMinutes +
  $IncrementalScheduledCodexMinutes
)
$actualCodexMinutes = $CodexFinalAuthorityMinutes + $codexDelegationOverhead
$netAvoided = [math]::Max(0, $totalCounterfactual - $actualCodexMinutes)
$netReduction = if ($totalCounterfactual -eq 0) { 0.0 } else { 100.0 * $netAvoided / $totalCounterfactual }
$handoffTotal = $UsefulHandoffs + $FailedHandoffs
$handoffSuccessRate = if ($handoffTotal -eq 0) { 0.0 } else { 100.0 * $UsefulHandoffs / $handoffTotal }
$proxyOperationallyStrong = (
  $netReduction -ge $TargetReductionPercent -and
  $handoffTotal -ge 25 -and
  $handoffSuccessRate -ge 85 -and
  $ScopePacketCompliancePercent -ge 90 -and
  $DirectCodexViolations -eq 0 -and
  $MalformedPathOrWriteScopeViolations -eq 0 -and
  $StaleOrInterruptedRecords -eq 0
)

$result = [ordered]@{
  schema_version = 1
  artifact_type = "ai_worker_net_usage_reduction_proxy"
  status = "proxy_only"
  finalized_at = [DateTimeOffset]::Now.ToString("o")
  total_codex_counterfactual_minutes = [math]::Round($totalCounterfactual, 2)
  worker_eligible_counterfactual_minutes = [math]::Round($WorkerEligibleCounterfactualMinutes, 2)
  codex_final_authority_minutes = [math]::Round($CodexFinalAuthorityMinutes, 2)
  codex_review_and_validation_minutes = [math]::Round($CodexReviewAndValidationMinutes, 2)
  codex_fallback_recovery_minutes = [math]::Round($CodexFallbackRecoveryMinutes, 2)
  codex_worker_orchestration_minutes = [math]::Round($CodexWorkerOrchestrationMinutes, 2)
  direct_codex_worker_eligible_minutes = [math]::Round($DirectCodexWorkerEligibleMinutes, 2)
  incremental_scheduled_codex_minutes = [math]::Round($IncrementalScheduledCodexMinutes, 2)
  actual_codex_minutes = [math]::Round($actualCodexMinutes, 2)
  net_codex_minutes_avoided = [math]::Round($netAvoided, 2)
  net_estimated_usage_reduction_percent = [math]::Round($netReduction, 2)
  target_reduction_percent = $TargetReductionPercent
  target_met_by_proxy = ($netReduction -ge $TargetReductionPercent)
  useful_handoffs = $UsefulHandoffs
  failed_handoffs = $FailedHandoffs
  handoff_success_rate_percent = [math]::Round($handoffSuccessRate, 2)
  scope_packet_compliance_percent = $ScopePacketCompliancePercent
  direct_codex_violations = $DirectCodexViolations
  malformed_path_or_write_scope_violations = $MalformedPathOrWriteScopeViolations
  stale_or_interrupted_records = $StaleOrInterruptedRecords
  operational_thresholds_met = $proxyOperationallyStrong
  confidence = $(if ($proxyOperationallyStrong) { "MEDIUM_PROXY_CAP_REQUIRES_DIRECT_MEASUREMENT" } else { "LOW_PROXY_THRESHOLDS_NOT_MET" })
  formula = "(worker-eligible counterfactual + final-authority - final-authority - all Codex delegation overhead) / total counterfactual"
}

if (![string]::IsNullOrWhiteSpace($OutputPath)) {
  $parent = Split-Path -Parent $OutputPath
  if (![string]::IsNullOrWhiteSpace($parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
  $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
}

$result | ConvertTo-Json -Depth 6
