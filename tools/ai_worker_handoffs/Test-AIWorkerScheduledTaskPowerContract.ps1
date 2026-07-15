[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$installerPath = Join-Path $PSScriptRoot "dispatcher\Install-AIWorkerDispatcherTask.ps1"
$monitorPath = Join-Path $PSScriptRoot "dispatcher\Invoke-AIWorkerDeterministicHealthMonitor.ps1"
$installer = Get-Content -Raw -LiteralPath $installerPath
$monitor = Get-Content -Raw -LiteralPath $monitorPath
$checks = [ordered]@{
  installer_allows_battery_start = ($installer -match '-AllowStartIfOnBatteries')
  installer_continues_on_battery = ($installer -match '-DontStopIfGoingOnBatteries')
  monitor_reports_battery_start_contract = ($monitor -match 'allows_battery_start')
  monitor_reports_battery_continuation_contract = ($monitor -match 'continues_on_battery')
  monitor_fails_closed_on_power_drift = ($monitor -match 'Scheduled task is not battery-resilient')
}
$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
[ordered]@{
  status = $(if ($failed.Count) { "FAIL" } else { "PASS" })
  classification = "AI_WORKER_SCHEDULED_TASK_POWER_CONTRACT"
  checks = $checks
  failed = $failed
} | ConvertTo-Json -Depth 5
if ($failed.Count) { exit 1 }
