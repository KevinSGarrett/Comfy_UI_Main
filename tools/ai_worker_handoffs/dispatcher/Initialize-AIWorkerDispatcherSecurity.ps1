[CmdletBinding(SupportsShouldProcess=$true)]
param([string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',[switch]$Apply)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot)
$keyPath=Get-AIWorkerKeyPath -DispatcherRoot $root
if ($Apply) {
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  Initialize-AIWorkerSigningKey -DispatcherRoot $root | Out-Null
  $identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
  & icacls.exe $root '/inheritance:r' '/grant:r' "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Unable to apply dispatcher ACL.' }
}
[ordered]@{status='PASS';classification=$(if($Apply){'AI_WORKER_DISPATCHER_SECURITY_INITIALIZED'}else{'AI_WORKER_DISPATCHER_SECURITY_DRY_RUN'});dispatcher_root=$root;key_path=$keyPath;key_exists=(Test-Path $keyPath);dpapi_scope='CurrentUser';acl_principals=@([Security.Principal.WindowsIdentity]::GetCurrent().Name,'SYSTEM');applied=[bool]$Apply}|ConvertTo-Json -Depth 5
