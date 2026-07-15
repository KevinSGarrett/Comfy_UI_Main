[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string]$ProjectRoot='C:\Comfy_UI_Main',
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [switch]$Apply
)

$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\');$powershell=(Get-Command powershell.exe -ErrorAction Stop).Source
$definitions=@(
  [ordered]@{name='ComfyUIMain AI Worker Admission Router';script='Invoke-AIWorkerAdmissionRouter.ps1';args='';minutes=1;limit=10;description='Routes signed task intents before substantive Codex reasoning.'},
  [ordered]@{name='ComfyUIMain AI Worker Cursor Lane';script='Invoke-AIWorkerDispatcher.ps1';args='-Lane Cursor -Once -MaxRequests 1';minutes=1;limit=120;description='Runs the independent Cursor subscription lane in isolated worktrees.'},
  [ordered]@{name='ComfyUIMain AI Worker Claude Lane';script='Invoke-AIWorkerDispatcher.ps1';args='-Lane Claude -Once -MaxRequests 1';minutes=1;limit=120;description='Runs the independent Claude subscription lane in isolated worktrees.'},
  [ordered]@{name='ComfyUIMain AI Worker Health Monitor';script='Invoke-AIWorkerDeterministicHealthMonitor.ps1';args="-ProjectRoot `"$ProjectRoot`"";minutes=240;limit=10;description='Checks queue, tasks, package drift, and qualification without launching a model.'},
  [ordered]@{name='ComfyUIMain EC2 Read Only Safety Monitor';script='Invoke-EC2ReadOnlySafetyMonitor.ps1';args="-ProjectRoot `"$ProjectRoot`"";minutes=15;limit=10;description='Reads approved EC2/runtime disposition and raises an exception file; never mutates AWS.'},
  [ordered]@{name='ComfyUIMain AI Worker Worktree Lifecycle';script='Invoke-AIWorkerWorktreeLifecycle.ps1';args='-Apply';minutes=60;limit=10;description='Removes reviewed or expired isolated worker worktrees.'}
)
$results=@()
foreach($definition in $definitions){
  $scriptPath=Join-Path $root $definition.script;if(-not(Test-Path $scriptPath -PathType Leaf)){throw "Installed dispatcher script missing: $scriptPath"}
  $arguments="-NoLogo -NoProfile -NonInteractive -File `"$scriptPath`" -DispatcherRoot `"$root`" $($definition.args)".Trim()
  if($Apply-and$PSCmdlet.ShouldProcess($definition.name,'Register production worker task')){$action=New-ScheduledTaskAction -Execute $powershell -Argument $arguments;$trigger=New-ScheduledTaskTrigger -Once -At(Get-Date).AddMinutes(1) -RepetitionInterval(New-TimeSpan -Minutes $definition.minutes) -RepetitionDuration(New-TimeSpan -Days 3650);$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit(New-TimeSpan -Minutes $definition.limit) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;Register-ScheduledTask -TaskName $definition.name -Action $action -Trigger $trigger -Settings $settings -Description $definition.description -Force|Out-Null}
  $task=Get-ScheduledTask -TaskName $definition.name -ErrorAction SilentlyContinue;$results+=[ordered]@{name=$definition.name;script=$scriptPath;arguments=$arguments;interval_minutes=$definition.minutes;present=($null-ne$task);state=$(if($task){[string]$task.State}else{'NOT_INSTALLED'})}
}
if($Apply){Unregister-ScheduledTask -TaskName 'ComfyUIMain AI Worker Dispatcher' -Confirm:$false -ErrorAction SilentlyContinue}
[ordered]@{status='PASS';classification=$(if($Apply){'AI_WORKER_PRODUCTION_TASKS_INSTALLED'}else{'AI_WORKER_PRODUCTION_TASKS_DRY_RUN'});applied=[bool]$Apply;tasks=$results}|ConvertTo-Json -Depth 8
