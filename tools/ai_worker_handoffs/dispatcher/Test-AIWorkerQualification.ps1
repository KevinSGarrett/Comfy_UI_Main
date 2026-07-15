[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Join-Path $env:TEMP ("ai-worker-qualification-test-" + [guid]::NewGuid().ToString('N'))
try {
  $handoffPath = Join-Path $root 'fixture_handoff_record.json'
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  [ordered]@{status='PASS';scope_files_unchanged=$true;scope_mutation_paths=@();outside_allowed_paths=@();issues=@()} | ConvertTo-Json | Set-Content -LiteralPath $handoffPath -Encoding UTF8
  for ($i=1; $i -le 25; $i++) {
    $dir = Join-Path $root ("completed\request-{0:D2}" -f $i)
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $record = [ordered]@{
      artifact_type='ai_worker_dispatch_record';status='PASS';classification='AI_WORKER_DISPATCH_COMPLETED_AWAITING_CODEX'
      finalized_at=(Get-Date).AddMinutes(-$i).ToString('o');worker_classification='CURSOR_HANDOFF_COMPLETED'
      adoption_status='ADOPTED';operation='read_only';worker_artifact_paths=@($handoffPath)
    }
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dir 'dispatch_record.json') -Encoding UTF8
  }
  $measurementTool = Join-Path $PSScriptRoot 'New-CodexUsageWindowMeasurement.ps1'
  $now = [DateTimeOffset]::Now
  & $measurementTool -DispatcherRoot $root -WindowType five_hour -StartedAt $now.AddHours(-5) -EndedAt $now -PreDelegationBurnPercentPerHour 10 -CodexConsumedPercent 20 | Out-Null
  & $measurementTool -DispatcherRoot $root -WindowType five_hour -StartedAt $now.AddHours(-11) -EndedAt $now.AddHours(-6) -PreDelegationBurnPercentPerHour 10 -CodexConsumedPercent 20 | Out-Null
  & $measurementTool -DispatcherRoot $root -WindowType twenty_four_hour_weekly_rate -StartedAt $now.AddHours(-24) -EndedAt $now -PreDelegationBurnPercentPerHour 2 -CodexConsumedPercent 20 | Out-Null
  & $measurementTool -DispatcherRoot $root -WindowType twenty_four_hour_weekly_rate -StartedAt $now.AddHours(-49) -EndedAt $now.AddHours(-25) -PreDelegationBurnPercentPerHour 2 -CodexConsumedPercent 20 | Out-Null
  $qualification = & (Join-Path $PSScriptRoot 'Measure-AIWorkerQualification.ps1') -DispatcherRoot $root -EligibleWorkCount 25 | ConvertFrom-Json
  $checks = [ordered]@{
    qualification_reaches_high_only_with_all_metrics = ($qualification.status -eq 'QUALIFIED' -and $qualification.confidence -eq 'HIGH')
    substantive_threshold = ($qualification.checks.substantive_handoffs.actual -eq 25 -and $qualification.checks.substantive_handoffs.pass)
    useful_threshold = ($qualification.checks.useful_completion_percent.actual -eq 100 -and $qualification.checks.useful_completion_percent.pass)
    adoption_threshold = ($qualification.checks.adopted_output_percent.actual -eq 100 -and $qualification.checks.adopted_output_percent.pass)
    scope_threshold = ($qualification.checks.scope_compliance_percent.actual -eq 100 -and $qualification.checks.scope_compliance_percent.pass)
    routing_threshold = ($qualification.checks.eligible_worker_routing_percent.actual -eq 100 -and $qualification.checks.eligible_worker_routing_percent.pass)
    direct_period_thresholds = ($qualification.checks.five_hour_reduction_periods.actual -eq 2 -and $qualification.checks.daily_or_weekly_rate_periods.actual -eq 2)
  }
  for ($i=1; $i -le 5; $i++) {
    $dir = Join-Path $root ("failed\failure-{0:D2}" -f $i)
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    [ordered]@{artifact_type='ai_worker_dispatch_record';status='FAIL';finalized_at=(Get-Date).ToString('o');worker_classification='CURSOR_HANDOFF_PROCESS_FAILED';adoption_status='NOT_APPLICABLE';operation='read_only';worker_artifact_paths=@()} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'dispatch_record.json') -Encoding UTF8
  }
  $degraded = & (Join-Path $PSScriptRoot 'Measure-AIWorkerQualification.ps1') -DispatcherRoot $root -EligibleWorkCount 30 | ConvertFrom-Json
  $checks.failed_dispatches_reduce_completion_rate = (-not $degraded.checks.useful_completion_percent.pass -and $degraded.checks.useful_completion_percent.actual -lt 85)
  [ordered]@{status=$(if(@($checks.Values|Where-Object{-not $_}).Count -eq 0){'PASS'}else{'FAIL'});checks=$checks} | ConvertTo-Json -Depth 6
} finally {
  if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
}
