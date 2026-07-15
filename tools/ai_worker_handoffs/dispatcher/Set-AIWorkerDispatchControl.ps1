[CmdletBinding()]
param([string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',[Parameter(Mandatory=$true)][string]$RequestId,[Parameter(Mandatory=$true)][ValidateSet('CANCELED','SUPERSEDED')][string]$Action,[Parameter(Mandatory=$true)][string]$Reason,[string]$SupersededByRequestId='')
$ErrorActionPreference='Stop';Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$id=Get-AIWorkerSafeId $RequestId;if($Action-eq'SUPERSEDED'-and[string]::IsNullOrWhiteSpace($SupersededByRequestId)){throw 'SupersededByRequestId is required.'}
$record=[ordered]@{schema_version=1;artifact_type='ai_worker_dispatch_control';request_id=$id;action=$Action;reason=$Reason;superseded_by_request_id=$SupersededByRequestId;created_at=(Get-Date).ToString('o');authority='Codex Desktop or deterministic admission controller'}
$path=Join-Path ([IO.Path]::GetFullPath($DispatcherRoot)) "controls\$id.json";Write-AIWorkerSignedJson -Path $path -Value $record -DispatcherRoot $DispatcherRoot|Out-Null;$record.control_path=$path;$record|ConvertTo-Json -Depth 5
