[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = 'C:\Users\kevin\.codex\ai_worker_dispatcher',
  [Parameter(Mandatory=$true)][string]$RequestId,
  [Parameter(Mandatory=$true)][ValidateSet('ADOPTED','PARTIALLY_ADOPTED','REJECTED')][string]$AdoptionStatus,
  [Parameter(Mandatory=$true)][string]$ReviewNote,
  [string[]]$AdoptedPaths = @(),
  [ValidateRange(0,100)][int]$AdoptionPercent = 0,
  [ValidateSet('PASS','PASS_WITH_FINDINGS','REJECTED')][string]$AcceptanceDecision = 'PASS',
  [string[]]$ResidualDefects = @(),
  [switch]$CleanupWorktree
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root = [IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
$id = Get-AIWorkerSafeId $RequestId
$recordPath = Join-Path $root "completed\$id\dispatch_record.json"
if (-not (Test-Path -LiteralPath $recordPath -PathType Leaf)) { throw "Completed dispatch record missing: $recordPath" }
$record = Read-AIWorkerSignedJson -Path $recordPath -DispatcherRoot $root
if ([string]$record.artifact_type -ne 'ai_worker_dispatch_record' -or [string]$record.status -ne 'PASS') { throw 'Only successful completed dispatches may receive adoption review.' }
if ($AdoptionPercent -eq 0) { $AdoptionPercent = switch ($AdoptionStatus) { 'ADOPTED' { 100 } 'PARTIALLY_ADOPTED' { 50 } default { 0 } } }
if ($AdoptionStatus -eq 'ADOPTED' -and $AdoptionPercent -lt 100) { throw 'ADOPTED requires AdoptionPercent 100.' }
if ($AdoptionStatus -eq 'REJECTED' -and $AdoptionPercent -ne 0) { throw 'REJECTED requires AdoptionPercent 0.' }
$record | Add-Member adoption_status $AdoptionStatus -Force
$record | Add-Member adoption_percent $AdoptionPercent -Force
$record | Add-Member adoption_reviewed_at ((Get-Date).ToString('o')) -Force
$record | Add-Member adoption_review_note $ReviewNote -Force
$record | Add-Member adopted_paths @($AdoptedPaths | Sort-Object -Unique) -Force
$record | Add-Member acceptance_decision $AcceptanceDecision -Force
$record | Add-Member residual_defects @($ResidualDefects) -Force
Write-AIWorkerSignedJson -Path $recordPath -Value $record -DispatcherRoot $root | Out-Null

$requestPath = Join-Path $root "completed\$id\request.json"
if (Test-Path -LiteralPath $requestPath) {
  $request = Read-AIWorkerSignedJson -Path $requestPath -DispatcherRoot $root
  if ($request.idempotency_key) {
    $indexPath = Join-Path $root "idempotency\$($request.idempotency_key).json"
    $index = [ordered]@{artifact_type='ai_worker_idempotency_index';request_id=$id;request_path=$recordPath;idempotency_key=[string]$request.idempotency_key;state=$AdoptionStatus;updated_at=(Get-Date).ToString('o')}
    Write-AIWorkerSignedJson -Path $indexPath -Value $index -DispatcherRoot $root | Out-Null
  }
}
if ($CleanupWorktree) { &(Join-Path $PSScriptRoot 'Invoke-AIWorkerWorktreeLifecycle.ps1') -DispatcherRoot $root -Apply | Out-Null }
$record | ConvertTo-Json -Depth 15
