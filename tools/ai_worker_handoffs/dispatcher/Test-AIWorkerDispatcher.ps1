[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$tempRoot = Join-Path $env:TEMP ("ai-worker-dispatcher-test-" + [guid]::NewGuid().ToString('N'))
$repo = Join-Path $tempRoot 'repo'
$dispatcherRoot = Join-Path $tempRoot 'dispatcher'
$fakeCursor = Join-Path $tempRoot 'fake-cursor.ps1'
$fakeClaude = Join-Path $tempRoot 'fake-claude.ps1'
$checks = [ordered]@{}

try {
  New-Item -ItemType Directory -Force -Path (Join-Path $repo 'tools') | Out-Null
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\..\New-AIWorkerScopePacket.ps1') -Destination (Join-Path $repo 'tools\New-AIWorkerScopePacket.ps1')
  Set-Content -LiteralPath (Join-Path $repo 'sample.txt') -Value 'stable scope' -Encoding ASCII
  & git.exe -C $repo init | Out-Null
  & git.exe -C $repo config user.email 'dispatcher-test@example.invalid'
  & git.exe -C $repo config user.name 'Dispatcher Test'
  & git.exe -C $repo add tools/New-AIWorkerScopePacket.ps1 sample.txt
  & git.exe -C $repo commit -m 'fixture' | Out-Null

  @'
param($ProjectRoot,$CredentialRoot,$TaskName,$Mode,$ScopePacketPath,$TimeoutSeconds,$WorkOrderText,[switch]$AllowWrites,[string[]]$AllowedPaths,[string[]]$DeclaredAgentCommands)
$run = Join-Path $ProjectRoot 'runtime_artifacts\agent_handoffs\cursor\fake'
New-Item -ItemType Directory -Force -Path $run | Out-Null
if ($AllowWrites) { Set-Content -LiteralPath (Join-Path $ProjectRoot $AllowedPaths[0]) -Value 'worker draft' -Encoding ASCII }
$record = [ordered]@{status='PASS';classification='CURSOR_HANDOFF_COMPLETED';scope_files_unchanged=(-not $AllowWrites);scope_mutation_paths=$(if($AllowWrites){@($AllowedPaths[0])}else{@()});outside_allowed_paths=@();issues=@()}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'handoff_record.json') -Encoding UTF8
$record | ConvertTo-Json -Depth 5
'@ | Set-Content -LiteralPath $fakeCursor -Encoding UTF8
  @'
param($ProjectRoot,$TaskName,$TaskTier,$ClaudeModel,$Effort,$ScopePacketPath,$TimeoutSeconds,$WorkOrderText,$DecisionUnitId,$EscalationReason,$PriorSonnetRecordPath)
$run = Join-Path $ProjectRoot 'runtime_artifacts\agent_handoffs\claude_subscription\fake'
New-Item -ItemType Directory -Force -Path $run | Out-Null
$record = [ordered]@{status='PASS';classification='CLAUDE_SONNET_HANDOFF_COMPLETED';scope_files_unchanged=$true;scope_mutation_paths=@();issues=@()}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'handoff_record.json') -Encoding UTF8
$record | ConvertTo-Json -Depth 5
'@ | Set-Content -LiteralPath $fakeClaude -Encoding UTF8

  $newRequest = Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1'
  $dispatcher = Join-Path $PSScriptRoot 'Invoke-AIWorkerDispatcher.ps1'
  $adoption = Join-Path $PSScriptRoot 'Set-AIWorkerDispatchAdoption.ps1'

  $cursorRequest = & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName cursor_read_only_fixture -WorkerLane Cursor -Operation read_only -WorkOrderText 'Inspect the exact file.' -CandidatePaths sample.txt | ConvertFrom-Json
  $cursorRun = & $dispatcher -DispatcherRoot $dispatcherRoot -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude | ConvertFrom-Json
  $cursorRecord = Get-Content -LiteralPath $cursorRun.results[0].dispatch_record_path -Raw | ConvertFrom-Json
  $checks.cursor_read_only_dispatched = ($cursorRun.processed -eq 1 -and $cursorRecord.status -eq 'PASS' -and -not $cursorRecord.worktree_retained_for_codex_review)

  $claudeRequest = & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName claude_read_only_fixture -WorkerLane Claude -Operation read_only -WorkOrderText 'Synthesize the exact file.' -CandidatePaths sample.txt | ConvertFrom-Json
  $claudeRun = & $dispatcher -DispatcherRoot $dispatcherRoot -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude | ConvertFrom-Json
  $claudeRecord = Get-Content -LiteralPath $claudeRun.results[0].dispatch_record_path -Raw | ConvertFrom-Json
  $checks.claude_read_only_dispatched = ($claudeRun.processed -eq 1 -and $claudeRecord.status -eq 'PASS')

  $tamperedRequest = & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName tampered_fixture -WorkerLane Cursor -Operation read_only -WorkOrderText 'Inspect.' -CandidatePaths sample.txt | ConvertFrom-Json
  Add-Content -LiteralPath $tamperedRequest.request_path -Value ' ' -Encoding ASCII
  $tamperedRun = & $dispatcher -DispatcherRoot $dispatcherRoot -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude | ConvertFrom-Json
  $checks.tampered_request_quarantined = ($tamperedRun.status -eq 'FAIL' -and $tamperedRun.results[0].classification -eq 'AI_WORKER_DISPATCH_REQUEST_INTEGRITY_FAILED')

  $implementationRequest = & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName cursor_implementation_fixture -WorkerLane Cursor -Operation implementation -WorkOrderText 'Draft the exact change and run the declared validator.' -CandidatePaths sample.txt -AllowedPaths sample.txt -DeclaredCommands 'Write-Output validator-pass' | ConvertFrom-Json
  $implementationRun = & $dispatcher -DispatcherRoot $dispatcherRoot -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude | ConvertFrom-Json
  $implementationRecordPath = [string]$implementationRun.results[0].dispatch_record_path
  $implementationRecord = Get-Content -LiteralPath $implementationRecordPath -Raw | ConvertFrom-Json
  $checks.implementation_worktree_retained = ($implementationRecord.status -eq 'PASS' -and $implementationRecord.worktree_retained_for_codex_review -and (Test-Path -LiteralPath (Join-Path $implementationRecord.isolated_worktree_path 'sample.txt')))
  if ($implementationRecord.status -ne 'PASS') { throw "Implementation fixture failed: $($implementationRecord.issues -join '; ')" }
  $adopted = & $adoption -DispatcherRoot $dispatcherRoot -RequestId $implementationRequest.request_id -AdoptionStatus ADOPTED -ReviewNote 'Fixture adopted.' -AdoptedPaths sample.txt | ConvertFrom-Json
  $checks.adoption_recorded = ($adopted.adoption_status -eq 'ADOPTED')

  $protectedRejected = $false
  try {
    & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName protected_fixture -WorkerLane Cursor -Operation implementation -WorkOrderText 'Forbidden.' -CandidatePaths sample.txt -AllowedPaths Plan/Tracker/state.json -DeclaredCommands 'Write-Output test' | Out-Null
  } catch { $protectedRejected = $_.Exception.Message -match 'authority boundary' }
  $checks.protected_path_rejected = $protectedRejected

  $commandRejected = $false
  try {
    & $newRequest -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName command_fixture -WorkerLane Cursor -Operation implementation -WorkOrderText 'Forbidden.' -CandidatePaths sample.txt -AllowedPaths sample.txt -DeclaredCommands 'git commit -am test' | Out-Null
  } catch { $commandRejected = $_.Exception.Message -match 'authority boundary' }
  $checks.authority_command_rejected = $commandRejected

  if ($implementationRecord.worktree_retained_for_codex_review) {
    & git.exe -C $repo worktree remove --force ([string]$implementationRecord.isolated_worktree_path) | Out-Null
  }
} finally {
  if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}

[ordered]@{
  status = $(if (@($checks.Values | Where-Object { -not $_ }).Count -eq 0) { 'PASS' } else { 'FAIL' })
  checks = $checks
} | ConvertTo-Json -Depth 6
