[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [ValidateRange(1,168)][int]$LookbackHours = 168,
  [ValidateRange(1,1000)][int]$EligibleWorkCount = 0,
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
$cutoff = [DateTimeOffset]::Now.AddHours(-$LookbackHours)
$records = @()
$recordPaths = @()
foreach ($state in @('completed','failed')) {
  $recordPaths += @(Get-ChildItem -LiteralPath (Join-Path $root $state) -Filter dispatch_record.json -File -Recurse -ErrorAction SilentlyContinue)
}
foreach ($path in $recordPaths) {
  try {
    $record = Get-Content -LiteralPath $path.FullName -Raw | ConvertFrom-Json
    if ([string]$record.artifact_type -eq 'ai_worker_dispatch_record' -and [DateTimeOffset]$record.finalized_at -ge $cutoff) { $records += $record }
  } catch { }
}
$substantive = @($records | Where-Object { [string]$_.worker_classification -notmatch 'HEALTH_PROBE|PROBE' })
$useful = @($substantive | Where-Object { [string]$_.status -eq 'PASS' })
$reviewed = @($useful | Where-Object { [string]$_.adoption_status -in @('ADOPTED','PARTIALLY_ADOPTED','REJECTED') })
$adopted = @($reviewed | Where-Object { [string]$_.adoption_status -in @('ADOPTED','PARTIALLY_ADOPTED') })
$scopeCompliant = @($useful | Where-Object {
  $handoff = @($_.worker_artifact_paths | Where-Object { [string]$_ -match 'handoff_record\.json$' } | Select-Object -First 1)
  if ($handoff.Count -ne 1 -or -not (Test-Path -LiteralPath $handoff[0])) { return $false }
  try {
    $h = Get-Content -LiteralPath $handoff[0] -Raw | ConvertFrom-Json
    $readOnlyCompliant = ($_.operation -eq 'read_only' -and $h.scope_files_unchanged -ne $false -and @($h.scope_mutation_paths).Count -eq 0)
    $implementationCompliant = ($_.operation -eq 'implementation' -and @($h.outside_allowed_paths).Count -eq 0)
    return (($readOnlyCompliant -or $implementationCompliant) -and @($h.issues).Count -eq 0)
  } catch { return $false }
})
$routingDenominator = if ($EligibleWorkCount -gt 0) { $EligibleWorkCount } else { $substantive.Count }
$routingRate = if ($routingDenominator -gt 0) { 100.0 * $substantive.Count / $routingDenominator } else { 0.0 }
$usefulRate = if ($substantive.Count -gt 0) { 100.0 * $useful.Count / $substantive.Count } else { 0.0 }
$adoptionRate = if ($useful.Count -gt 0) { 100.0 * $adopted.Count / $useful.Count } else { 0.0 }
$scopeRate = if ($useful.Count -gt 0) { 100.0 * $scopeCompliant.Count / $useful.Count } else { 0.0 }

$measurements = @()
foreach ($path in @(Get-ChildItem -LiteralPath (Join-Path $root 'measurements') -Filter *.json -File -ErrorAction SilentlyContinue)) {
  try {
    $m = Get-Content -LiteralPath $path.FullName -Raw | ConvertFrom-Json
    if ([string]$m.artifact_type -eq 'codex_usage_window_measurement' -and [DateTimeOffset]$m.ended_at -ge $cutoff) { $measurements += $m }
  } catch { }
}
$fiveHourPasses = @($measurements | Where-Object { $_.window_type -eq 'five_hour' -and $_.target_met -eq $true }).Count
$longWindowPasses = @($measurements | Where-Object { $_.window_type -eq 'twenty_four_hour_weekly_rate' -and $_.target_met -eq $true }).Count
$checks = [ordered]@{
  substantive_handoffs = [ordered]@{actual=$substantive.Count;required=25;pass=($substantive.Count -ge 25)}
  useful_completion_percent = [ordered]@{actual=[math]::Round($usefulRate,2);required=85;pass=($usefulRate -ge 85)}
  adopted_output_percent = [ordered]@{actual=[math]::Round($adoptionRate,2);required=80;pass=($adoptionRate -ge 80)}
  scope_compliance_percent = [ordered]@{actual=[math]::Round($scopeRate,2);required=95;pass=($scopeRate -ge 95)}
  eligible_worker_routing_percent = [ordered]@{actual=[math]::Round($routingRate,2);required=90;pass=($routingRate -ge 90 -and $EligibleWorkCount -gt 0)}
  five_hour_reduction_periods = [ordered]@{actual=$fiveHourPasses;required=2;pass=($fiveHourPasses -ge 2)}
  daily_or_weekly_rate_periods = [ordered]@{actual=$longWindowPasses;required=2;pass=($longWindowPasses -ge 2)}
}
$allPass = @($checks.Values | Where-Object { -not $_.pass }).Count -eq 0
$result = [ordered]@{
  schema_version = 1
  artifact_type = 'ai_worker_qualification_measurement'
  status = $(if ($allPass) { 'QUALIFIED' } else { 'NOT_YET_QUALIFIED' })
  confidence = $(if ($allPass) { 'HIGH' } else { 'LOW_TO_MEDIUM_UNTIL_MEASURED' })
  finalized_at = (Get-Date).ToString('o')
  lookback_hours = $LookbackHours
  eligible_work_count = $EligibleWorkCount
  checks = $checks
  direct_measurement_required = $true
  note = 'Proxy token counts and subscription utilization do not prove Codex reduction; measured five-hour and 24-hour/weekly-rate windows are mandatory.'
}
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
  [System.IO.File]::WriteAllText($OutputPath, ($result | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
}
$result | ConvertTo-Json -Depth 8
