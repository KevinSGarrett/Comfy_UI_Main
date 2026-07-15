[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [Parameter(Mandatory=$true)][string]$RequestId,
  [Parameter(Mandatory=$true)][ValidateSet("ADOPTED","PARTIALLY_ADOPTED","REJECTED")][string]$AdoptionStatus,
  [Parameter(Mandatory=$true)][string]$ReviewNote,
  [string[]]$AdoptedPaths = @()
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
$recordPath = Join-Path $root "completed\$RequestId\dispatch_record.json"
if (-not (Test-Path -LiteralPath $recordPath -PathType Leaf)) { throw "Completed dispatch record missing: $recordPath" }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
if ([string]$record.artifact_type -ne 'ai_worker_dispatch_record' -or [string]$record.status -ne 'PASS') { throw 'Only successful completed dispatches may receive adoption review.' }
$record | Add-Member -NotePropertyName adoption_status -NotePropertyValue $AdoptionStatus -Force
$record | Add-Member -NotePropertyName adoption_reviewed_at -NotePropertyValue ((Get-Date).ToString('o')) -Force
$record | Add-Member -NotePropertyName adoption_review_note -NotePropertyValue $ReviewNote -Force
$record | Add-Member -NotePropertyName adopted_paths -NotePropertyValue @($AdoptedPaths | Sort-Object -Unique) -Force
[System.IO.File]::WriteAllText($recordPath, ($record | ConvertTo-Json -Depth 12), (New-Object System.Text.UTF8Encoding($false)))
$record | ConvertTo-Json -Depth 12
