[CmdletBinding()]
param(
  [string]$ProjectRoot='C:\Comfy_UI_Main',
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [string]$InstanceId='i-0560bf8d143f93bb1',
  [string]$Region='us-east-1'
)

$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\');foreach($dir in @('monitoring','alerts')){New-Item -ItemType Directory -Force -Path(Join-Path $root $dir)|Out-Null}
$issues=@();$disposition=$null
try{$disposition=&(Join-Path ([IO.Path]::GetFullPath($ProjectRoot)) 'Plan\Instructions\Operations\Scripts\Get-EC2RuntimeReadinessDisposition.ps1') -ProjectRoot $ProjectRoot -InstanceId $InstanceId -Region $Region -IncludeAwsState|ConvertFrom-Json}catch{$issues+="EC2 read-only disposition failed: $($_.Exception.Message)"}
$actionable=@('RUNNING_MARKER_UNKNOWN_REVIEW_NEEDED','BLOCKED_INVALID_GPU_WORK_ORDER','BLOCKED_STALE_GPU_WORK_ORDER','BLOCKED_FAILED_GPU_WORK_ORDER')
if($disposition-and$disposition.classification-in$actionable){$issues+="EC2 disposition requires review: $($disposition.classification)"}
$record=[ordered]@{schema_version=1;artifact_type='ec2_read_only_safety_monitor';status=$(if($issues.Count){'ACTION_REQUIRED'}else{'PASS'});classification=$(if($issues.Count){'EC2_SAFETY_EXCEPTION_REQUIRES_CODEX'}else{'EC2_SAFETY_NO_CODEX_WAKE'});finalized_at=(Get-Date).ToString('o');instance_id=$InstanceId;region=$Region;disposition=$disposition;issues=$issues;aws_mutation_performed=$false;ec2_start_or_stop_performed=$false;codex_wake_requested=($issues.Count-gt0)}
$stamp=(Get-Date -Format 'yyyyMMddTHHmmssfffzzz')-replace':','';Write-AIWorkerSignedJson -Path(Join-Path $root "monitoring\ec2_$stamp.json") -Value $record -DispatcherRoot $root|Out-Null;Write-AIWorkerSignedJson -Path(Join-Path $root 'monitoring\ec2_latest.json') -Value $record -DispatcherRoot $root|Out-Null
$alertPath=Join-Path $root 'alerts\EC2_SAFETY_ACTION_REQUIRED.json';if($issues.Count){Write-AIWorkerSignedJson -Path $alertPath -Value $record -DispatcherRoot $root|Out-Null}else{Remove-Item $alertPath,($alertPath+'.sig') -Force -ErrorAction SilentlyContinue}
$record|ConvertTo-Json -Depth 12
