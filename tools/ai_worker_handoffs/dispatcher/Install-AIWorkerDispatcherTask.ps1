[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [string]$TaskName = "ComfyUIMain AI Worker Dispatcher",
  [ValidateRange(1,30)][int]$IntervalMinutes = 2,
  [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path ([System.IO.Path]::GetFullPath($DispatcherRoot)) 'Invoke-AIWorkerDispatcher.ps1'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "Installed dispatcher missing: $scriptPath" }
$powerShellPath = (Get-Command powershell.exe -ErrorAction Stop).Source
$arguments = "-NoLogo -NoProfile -NonInteractive -File `"$scriptPath`" -Once"
$result = [ordered]@{
  status = 'PASS'
  classification = $(if($Apply){'AI_WORKER_DISPATCHER_TASK_INSTALLED'}else{'AI_WORKER_DISPATCHER_TASK_DRY_RUN'})
  task_name = $TaskName
  executable = $powerShellPath
  arguments = $arguments
  interval_minutes = $IntervalMinutes
  applied = [bool]$Apply
}
if ($Apply) {
  $action = New-ScheduledTaskAction -Execute $powerShellPath -Argument $arguments
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Consumes bounded Cursor/Claude subscription work orders without waking Codex Desktop.' -Force | Out-Null
  $installed = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $result.task_state = [string]$installed.State
}
$result | ConvertTo-Json -Depth 5
