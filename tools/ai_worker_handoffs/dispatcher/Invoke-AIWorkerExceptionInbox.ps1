[CmdletBinding()]
param([string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher')
$ErrorActionPreference='Stop';Import-Module(Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1')-Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\');$alerts=@()
foreach($path in @(Get-ChildItem -LiteralPath(Join-Path $root 'alerts') -Filter *.json -File -ErrorAction SilentlyContinue)){$alerts+=Read-AIWorkerSignedJson -Path $path.FullName -DispatcherRoot $root}
[ordered]@{status=$(if($alerts.Count){'ACTION_REQUIRED'}else{'PASS'});classification=$(if($alerts.Count){'LOCAL_MONITOR_EXCEPTIONS_REQUIRE_CODEX'}else{'LOCAL_MONITORS_CLEAR_NO_CODEX_WORK'});alert_count=$alerts.Count;alerts=$alerts}|ConvertTo-Json -Depth 15
