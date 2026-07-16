[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$installerPath = Join-Path $PSScriptRoot "dispatcher\Install-AIWorkerDispatcherTask.ps1"
$monitorPath = Join-Path $PSScriptRoot "dispatcher\Invoke-AIWorkerDeterministicHealthMonitor.ps1"
$hiddenHostPath = Join-Path $PSScriptRoot "dispatcher\Invoke-HiddenPowerShell.vbs"
$installer = Get-Content -Raw -LiteralPath $installerPath
$monitor = Get-Content -Raw -LiteralPath $monitorPath
$hiddenHost = Get-Content -Raw -LiteralPath $hiddenHostPath
$wscript = (Get-Command wscript.exe -ErrorAction Stop).Source
$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$canaryArguments = '//B //NoLogo "' + $hiddenHostPath + '" "' + $powershell + '" "-NoLogo" "-NoProfile" "-NonInteractive" "-WindowStyle" "Hidden" "-Command" "exit 23"'
$canary = Start-Process -FilePath $wscript -ArgumentList $canaryArguments -Wait -PassThru
$checks = [ordered]@{
  installer_allows_battery_start = ($installer -match '-AllowStartIfOnBatteries')
  installer_continues_on_battery = ($installer -match '-DontStopIfGoingOnBatteries')
  installer_uses_gui_script_host = ($installer -match 'wscript\.exe')
  installer_uses_batch_script_host_mode = ($installer -match '//B //NoLogo')
  installer_routes_through_hidden_host = ($installer -match 'Invoke-HiddenPowerShell\.vbs')
  hidden_host_requests_zero_window_style = ($hiddenHost -match 'shell\.Run\(command, 0, True\)')
  hidden_host_propagates_exit_code = ($hiddenHost -match 'exitCode = shell\.Run' -and $hiddenHost -match 'WScript\.Quit exitCode')
  hidden_host_live_exit_code_canary = ($canary.ExitCode -eq 23)
  monitor_reports_battery_start_contract = ($monitor -match 'allows_battery_start')
  monitor_reports_battery_continuation_contract = ($monitor -match 'continues_on_battery')
  monitor_reports_hidden_window_contract = ($monitor -match 'window_hidden')
  monitor_requires_gui_script_host = ($monitor -match "GetFileName\(\[string\]\`$_.Execute\)-ieq'wscript\.exe'")
  monitor_requires_hidden_host = ($monitor -match 'Invoke-HiddenPowerShell\\\.vbs')
  monitor_fails_closed_on_power_drift = ($monitor -match 'Scheduled task is not battery-resilient')
  monitor_fails_closed_on_visible_console = ($monitor -match 'Scheduled task can open a visible console window')
}
$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
[ordered]@{
  status = $(if ($failed.Count) { "FAIL" } else { "PASS" })
  classification = "AI_WORKER_SCHEDULED_TASK_POWER_CONTRACT"
  checks = $checks
  failed = $failed
} | ConvertTo-Json -Depth 5
if ($failed.Count) { exit 1 }
