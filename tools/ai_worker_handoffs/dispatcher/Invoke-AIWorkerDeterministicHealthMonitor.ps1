[CmdletBinding()]
param(
  [string]$ProjectRoot='C:\Comfy_UI_Main',
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [ValidateRange(5,1440)][int]$QueueAgeAlertMinutes=30
)

$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\');$project=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
foreach($dir in @('monitoring','alerts')){New-Item -ItemType Directory -Force -Path(Join-Path $root $dir)|Out-Null}
$issues=@();$warnings=@();$queue=@()
foreach($lane in @('Cursor','Claude')){
  foreach($file in @(Get-ChildItem -LiteralPath(Join-Path $root "queue\$lane") -Filter *.json -File -ErrorAction SilentlyContinue)){
    $age=[math]::Round(((Get-Date)-$file.LastWriteTime).TotalMinutes,2);$queue+=[ordered]@{lane=$lane;request=$file.BaseName;age_minutes=$age}
    if($age-ge$QueueAgeAlertMinutes){$issues+="Stale $lane queue request $($file.BaseName): $age minutes"}
  }
}
$tasks=@()
foreach($name in @('ComfyUIMain AI Worker Admission Router','ComfyUIMain AI Worker Cursor Lane','ComfyUIMain AI Worker Claude Lane','ComfyUIMain AI Worker Worktree Lifecycle')){
  $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;$info=if($task){Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue}else{$null}
  $tasks+=[ordered]@{name=$name;present=($null-ne$task);state=$(if($task){[string]$task.State}else{'MISSING'});last_result=$(if($info){[int]$info.LastTaskResult}else{$null});allows_battery_start=$(if($task){-not[bool]$task.Settings.DisallowStartIfOnBatteries}else{$false});continues_on_battery=$(if($task){-not[bool]$task.Settings.StopIfGoingOnBatteries}else{$false})}
  if(-not$task){$issues+="Scheduled task missing: $name"}elseif($info.LastTaskResult-ne0-and$info.LastRunTime.Year-gt2000){$issues+="Scheduled task failed: $name result=$($info.LastTaskResult)"}elseif($task.Settings.DisallowStartIfOnBatteries-or$task.Settings.StopIfGoingOnBatteries){$issues+="Scheduled task is not battery-resilient: $name"}
}
$packageDrift=$null
try{$packageDrift=&(Join-Path $PSScriptRoot 'Test-AIWorkerHandoffPackageDrift.ps1') -ManifestPath (Join-Path $PSScriptRoot 'canonical_package_manifest.json') -CodexHome (Split-Path -Parent $root)|ConvertFrom-Json;if($packageDrift.status-ne'PASS'){$issues+='Canonical/live worker package drift detected.'}}catch{$issues+="Package drift check failed: $($_.Exception.Message)"}
$qualification=$null
try{$qualification=&(Join-Path $PSScriptRoot 'Measure-AIWorkerQualification.ps1') -DispatcherRoot $root -LookbackHours 168|ConvertFrom-Json}catch{$warnings+="Qualification snapshot failed: $($_.Exception.Message)"}
$record=[ordered]@{schema_version=1;artifact_type='ai_worker_deterministic_health_monitor';status=$(if($issues.Count){'ACTION_REQUIRED'}else{'PASS'});classification=$(if($issues.Count){'AI_WORKER_HEALTH_EXCEPTION_REQUIRES_CODEX'}else{'AI_WORKER_HEALTHY_NO_CODEX_WAKE'});finalized_at=(Get-Date).ToString('o');queue=$queue;scheduled_tasks=$tasks;package_drift_status=$(if($packageDrift){$packageDrift.status}else{'UNKNOWN'});qualification_status=$(if($qualification){$qualification.status}else{'UNKNOWN'});issues=$issues;warnings=$warnings;worker_launched=$false;codex_wake_requested=($issues.Count-gt0)}
$stamp=Get-Date -Format 'yyyyMMddTHHmmssfffzzz';$stamp=$stamp-replace':','';$path=Join-Path $root "monitoring\health_$stamp.json";Write-AIWorkerSignedJson -Path $path -Value $record -DispatcherRoot $root|Out-Null;Write-AIWorkerSignedJson -Path(Join-Path $root 'monitoring\health_latest.json') -Value $record -DispatcherRoot $root|Out-Null
$alertPath=Join-Path $root 'alerts\AI_WORKER_HEALTH_ACTION_REQUIRED.json'
if($issues.Count){Write-AIWorkerSignedJson -Path $alertPath -Value $record -DispatcherRoot $root|Out-Null}else{Remove-Item $alertPath,($alertPath+'.sig') -Force -ErrorAction SilentlyContinue}
$record|ConvertTo-Json -Depth 12
