[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [Parameter(Mandatory=$true)][datetimeoffset]$WindowStartedAt,
  [datetimeoffset]$WindowEndedAt=[datetimeoffset]::Now,
  [string]$OutputPath=''
)
$ErrorActionPreference='Stop';Import-Module(Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1')-Force -DisableNameChecking
if(-not(Test-Path $CsvPath -PathType Leaf)){throw "Cursor usage CSV missing: $CsvPath"};$rows=@(Import-Csv $CsvPath|Where-Object{$date=[datetimeoffset]$_.Date;$date-ge$WindowStartedAt-and$date-le$WindowEndedAt})
$models=@();foreach($group in @($rows|Group-Object Model)){$models+=[ordered]@{model=$group.Name;events=$group.Count;total_tokens=[long](($group.Group|Measure-Object -Property 'Total Tokens' -Sum).Sum);input_without_cache_write=[long](($group.Group|Measure-Object -Property 'Input (w/o Cache Write)' -Sum).Sum);cache_read=[long](($group.Group|Measure-Object -Property 'Cache Read' -Sum).Sum);output_tokens=[long](($group.Group|Measure-Object -Property 'Output Tokens' -Sum).Sum);automation_event_count=@($group.Group|Where-Object{$_.'Automation ID'}).Count}}
$record=[ordered]@{schema_version=1;artifact_type='cursor_subscription_usage_measurement';status='OBSERVATIONAL';created_at=(Get-Date).ToString('o');window_started_at=$WindowStartedAt.ToString('o');window_ended_at=$WindowEndedAt.ToString('o');source_csv_sha256=(Get-AIWorkerFileSha256Shared -Path $CsvPath);event_count=$rows.Count;total_tokens=[long](($rows|Measure-Object -Property 'Total Tokens' -Sum).Sum);automation_event_count=@($rows|Where-Object{$_.'Automation ID'}).Count;models=$models;qualification_note='Cursor utilization is diagnostic and cannot prove Codex Desktop reduction without matched Codex usage windows.'}
if(-not$OutputPath){$stamp=(Get-Date -Format 'yyyyMMddTHHmmssfffzzz')-replace':','';$OutputPath=Join-Path([IO.Path]::GetFullPath($DispatcherRoot))"measurements\cursor_usage_$stamp.json"};Write-AIWorkerSignedJson -Path $OutputPath -Value $record -DispatcherRoot $DispatcherRoot|Out-Null;$record|ConvertTo-Json -Depth 8
