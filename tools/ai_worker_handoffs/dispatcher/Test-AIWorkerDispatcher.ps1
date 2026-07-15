[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
$tempRoot=Join-Path $env:TEMP ('ai-worker-production-test-'+[guid]::NewGuid().ToString('N'))
$repo=Join-Path $tempRoot 'repo';$dispatcherRoot=Join-Path $tempRoot 'dispatcher';$fakeCursor=Join-Path $tempRoot 'fake-cursor.ps1';$fakeClaude=Join-Path $tempRoot 'fake-claude.ps1';$slowCursor=Join-Path $tempRoot 'slow-cursor.ps1';$checks=[ordered]@{}
try{
  New-Item -ItemType Directory -Force -Path(Join-Path $repo 'tools')|Out-Null
  New-Item -ItemType Directory -Force -Path(Join-Path $repo 'Plan\10_REGISTRIES')|Out-Null
  Copy-Item -LiteralPath(Join-Path $PSScriptRoot '..\..\New-AIWorkerScopePacket.ps1') -Destination(Join-Path $repo 'tools\New-AIWorkerScopePacket.ps1')
  Copy-Item -LiteralPath(Join-Path $PSScriptRoot '..\..\..\Plan\10_REGISTRIES\ai_worker_development_quality_profiles.json') -Destination(Join-Path $repo 'Plan\10_REGISTRIES\ai_worker_development_quality_profiles.json')
  Set-Content(Join-Path $repo 'sample.txt') 'stable scope' -Encoding ASCII
  &git.exe -C $repo init|Out-Null;&git.exe -C $repo config user.email 'dispatcher-test@example.invalid';&git.exe -C $repo config user.name 'Dispatcher Test';&git.exe -C $repo add .;&git.exe -C $repo commit -m fixture|Out-Null
  &(Join-Path $PSScriptRoot 'Initialize-AIWorkerDispatcherSecurity.ps1') -DispatcherRoot $dispatcherRoot -Apply|Out-Null
  @'
param($ProjectRoot,$CredentialRoot,$TaskName,$Mode,$ScopePacketPath,$TimeoutSeconds,$WorkOrderText,[switch]$AllowWrites,[string[]]$AllowedPaths,[string[]]$DeclaredAgentCommands)
$run=Join-Path $ProjectRoot 'runtime_artifacts\agent_handoffs\cursor\fake';New-Item -ItemType Directory -Force -Path $run|Out-Null
if($AllowWrites){Set-Content -LiteralPath(Join-Path $ProjectRoot $AllowedPaths[0]) -Value 'worker draft' -Encoding ASCII}
$record=[ordered]@{status='PASS';classification='CURSOR_HANDOFF_COMPLETED';summary='Bounded Cursor result.';recommended_codex_follow_up='Review compact diff.';scope_files_unchanged=(-not$AllowWrites);scope_mutation_paths=$(if($AllowWrites){@($AllowedPaths[0])}else{@()});outside_allowed_paths=@();issues=@()}
$record|ConvertTo-Json -Depth 5|Set-Content(Join-Path $run 'handoff_record.json') -Encoding UTF8;$record|ConvertTo-Json -Depth 5
'@|Set-Content $fakeCursor -Encoding UTF8
  @'
param($ProjectRoot,$TaskName,$TaskTier,$ClaudeModel,$Effort,$ScopePacketPath,$TimeoutSeconds,$WorkOrderText,$DecisionUnitId,$EscalationReason,$PriorSonnetRecordPath)
$run=Join-Path $ProjectRoot 'runtime_artifacts\agent_handoffs\claude_subscription\fake';New-Item -ItemType Directory -Force -Path $run|Out-Null
$record=[ordered]@{status='PASS';classification='CLAUDE_SONNET_HANDOFF_COMPLETED';summary='Bounded Sonnet result.';recommended_codex_follow_up='Use architecture contract.';scope_files_unchanged=$true;scope_mutation_paths=@();issues=@()}
$record|ConvertTo-Json -Depth 5|Set-Content(Join-Path $run 'handoff_record.json') -Encoding UTF8;$record|ConvertTo-Json -Depth 5
'@|Set-Content $fakeClaude -Encoding UTF8
  @'
param($ProjectRoot,$CredentialRoot,$TaskName,$Mode,$ScopePacketPath,$TimeoutSeconds,$WorkOrderText,[switch]$AllowWrites,[string[]]$AllowedPaths,[string[]]$DeclaredAgentCommands)
Start-Sleep -Seconds 5
[ordered]@{status='PASS';classification='SHOULD_HAVE_TIMED_OUT'}|ConvertTo-Json
'@|Set-Content $slowCursor -Encoding UTF8
  Import-Module(Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1')-Force -DisableNameChecking
  $new=Join-Path $PSScriptRoot 'New-AIWorkerDispatchRequest.ps1';$dispatch=Join-Path $PSScriptRoot 'Invoke-AIWorkerDispatcher.ps1';$control=Join-Path $PSScriptRoot 'Set-AIWorkerDispatchControl.ps1';$adopt=Join-Path $PSScriptRoot 'Set-AIWorkerDispatchAdoption.ps1';$broker=Join-Path $PSScriptRoot 'Invoke-AIWorkerCommandBroker.ps1'

  $cursor=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName cursor_read -WorkerLane Cursor -Operation read_only -WorkOrderText 'Inspect exact scope.' -CandidatePaths sample.txt|ConvertFrom-Json
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.cursor_lane_pass=($run.processed-eq1-and(Test-Path(Join-Path $dispatcherRoot "completed\$($cursor.request_id)\dispatch_record.json")))
  if(-not$checks.cursor_lane_pass){throw "Cursor read fixture failed: $($run|ConvertTo-Json -Depth 12 -Compress)"}

  $claude=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName sonnet_read -WorkerLane Claude -Operation read_only -WorkOrderText 'Synthesize exact scope.' -CandidatePaths sample.txt|ConvertFrom-Json
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Claude -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.claude_lane_pass=($run.processed-eq1-and(Test-Path(Join-Path $dispatcherRoot "completed\$($claude.request_id)\dispatch_record.json")))
  if(-not$checks.claude_lane_pass){throw "Claude read fixture failed: $($run|ConvertTo-Json -Depth 12 -Compress)"}

  $implementation=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName cursor_implementation -WorkerLane Cursor -Operation implementation -WorkOrderText 'Edit exact scope; host runs validators.' -CandidatePaths sample.txt -AllowedPaths sample.txt -DeclaredCommands 'Write-Output validator-pass' -QualityProfile fast_low_risk -RiskClass low|ConvertFrom-Json
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  if(-not$run.lanes[0].results[0].dispatch_record_path){throw "Implementation dispatch did not complete: $($run|ConvertTo-Json -Depth 12 -Compress)"}
  $record=Get-Content $run.lanes[0].results[0].dispatch_record_path -Raw|ConvertFrom-Json;$reviewPath=[string]$run.lanes[0].results[0].review_packet_path
  $checks.implementation_review_packet=($record.status-eq'PASS'-and$record.host_validation_status-eq'PASS'-and(Test-Path $reviewPath)-and$record.worktree_retained_for_codex_review)
  $adoption=&$adopt -DispatcherRoot $dispatcherRoot -RequestId $implementation.request_id -AdoptionStatus ADOPTED -AdoptionPercent 100 -ReviewNote 'Accepted fixture.' -AdoptedPaths sample.txt -CleanupWorktree|ConvertFrom-Json
  $checks.signed_adoption_and_cleanup=($adoption.adoption_status-eq'ADOPTED'-and-not(Test-Path $record.isolated_worktree_path))

  $tampered=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName tamper_read -WorkerLane Cursor -Operation read_only -WorkOrderText Inspect -CandidatePaths sample.txt|ConvertFrom-Json
  Add-Content $tampered.request_path ' ' -Encoding ASCII
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.hmac_tamper_dead_letter=($run.lanes[0].results[0].classification-eq'AI_WORKER_DISPATCH_REQUEST_INTEGRITY_FAILED')

  $cancel=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName cancel_read -WorkerLane Cursor -Operation read_only -WorkOrderText Inspect -CandidatePaths sample.txt|ConvertFrom-Json
  &$control -DispatcherRoot $dispatcherRoot -RequestId $cancel.request_id -Action CANCELED -Reason 'Fixture cancellation.'|Out-Null
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.cancel_terminal=($run.lanes[0].results[0].classification-eq'AI_WORKER_DISPATCH_TERMINAL_REJECTION')

  $dependency=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName dependency_sonnet -WorkerLane Claude -Operation read_only -WorkOrderText Design -CandidatePaths sample.txt|ConvertFrom-Json
  $dependent=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName dependent_cursor -WorkerLane Cursor -Operation read_only -WorkOrderText Consume -CandidatePaths sample.txt -DependsOnRequestIds $dependency.request_id|ConvertFrom-Json
  $before=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  &$dispatch -DispatcherRoot $dispatcherRoot -Lane Claude -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|Out-Null
  $after=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.dependency_order=($before.processed-eq0-and(Test-Path(Join-Path $dispatcherRoot "completed\$($dependent.request_id)\dispatch_record.json")))

  $dedupe1=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName dedupe_read -WorkerLane Cursor -Operation read_only -WorkOrderText Same -CandidatePaths sample.txt|ConvertFrom-Json
  $dedupe2=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName dedupe_read -WorkerLane Cursor -Operation read_only -WorkOrderText Same -CandidatePaths sample.txt|ConvertFrom-Json
  $checks.idempotency_deduplicates=($dedupe2.status-eq'DEDUPLICATED'-and$dedupe2.request_id-eq$dedupe1.request_id)
  &$control -DispatcherRoot $dispatcherRoot -RequestId $dedupe1.request_id -Action CANCELED -Reason cleanup|Out-Null;&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|Out-Null

  $stale=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName stale_read -WorkerLane Cursor -Operation read_only -WorkOrderText Inspect -CandidatePaths sample.txt|ConvertFrom-Json
  Set-Content(Join-Path $repo 'sample.txt') 'new authoritative scope' -Encoding ASCII;&git.exe -C $repo add sample.txt;&git.exe -C $repo commit -m scope-change|Out-Null
  $run=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $fakeCursor -ClaudeWrapperPath $fakeClaude|ConvertFrom-Json
  $checks.stale_scope_rejected=($run.lanes[0].results[0].classification-eq'AI_WORKER_DISPATCH_TERMINAL_REJECTION')

  $brokerRejected=$false;try{&$broker -WorktreePath $repo -Commands 'git status'|Out-Null}catch{$brokerRejected=$true}
  $brokerPass=&$broker -WorktreePath $repo -Commands 'Write-Output safe-validator'|ConvertFrom-Json
  $checks.command_broker_boundary=($brokerRejected-and$brokerPass.status-eq'PASS')

  $timeout=&$new -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName hard_timeout -WorkerLane Cursor -Operation read_only -WorkOrderText 'Timeout fixture.' -CandidatePaths sample.txt -MaxAttempts 1|ConvertFrom-Json
  $timeoutRequest=Read-AIWorkerSignedJson -Path $timeout.request_path -DispatcherRoot $dispatcherRoot;$timeoutRequest.timeout_seconds=1;Write-AIWorkerSignedJson -Path $timeout.request_path -Value $timeoutRequest -DispatcherRoot $dispatcherRoot|Out-Null;Write-Utf8NoBom -Path($timeout.request_path+'.sha256') -Text((Get-FileHash $timeout.request_path -Algorithm SHA256).Hash.ToLowerInvariant())
  $watch=[Diagnostics.Stopwatch]::StartNew();$timeoutRun=&$dispatch -DispatcherRoot $dispatcherRoot -Lane Cursor -Once -CursorWrapperPath $slowCursor -ClaudeWrapperPath $fakeClaude -HardTimeoutGraceSeconds 1|ConvertFrom-Json;$watch.Stop()
  $checks.wrapper_hard_timeout=($watch.Elapsed.TotalSeconds-lt10-and$timeoutRun.lanes[0].results[0].classification-eq'AI_WORKER_RETRY_BUDGET_EXHAUSTED')

  $pipeline=&(Join-Path $PSScriptRoot 'New-AIWorkerDevelopmentPipeline.ps1') -ProjectRoot $repo -DispatcherRoot $dispatcherRoot -TaskName assured_change -WorkType implementation -Objective 'Implement with architecture and residual-risk review.' -CandidatePaths sample.txt -AllowedPaths sample.txt -ValidatorCommands @('Write-Output validator-one','Write-Output validator-two','Write-Output validator-three') -QualityProfile high_assurance -RiskClass high -RouteNow|ConvertFrom-Json
  $checks.high_assurance_dependency_graph=($pipeline.routing.results[0].request_ids.Count-eq3-and@(Get-ChildItem(Join-Path $dispatcherRoot 'queue\Claude') -Filter *.json).Count-eq2-and@(Get-ChildItem(Join-Path $dispatcherRoot 'queue\Cursor') -Filter *.json).Count-eq1)

  $failed=@($checks.GetEnumerator()|Where-Object{-not$_.Value}|ForEach-Object{$_.Key})
  [ordered]@{status=$(if($failed.Count){'FAIL'}else{'PASS'});classification='AI_WORKER_PRODUCTIONIZATION_REGRESSION';checks=$checks;failed=$failed;pipeline_diagnostic=$(if($failed-contains'high_assurance_dependency_graph'){$pipeline}else{$null})}|ConvertTo-Json -Depth 12
  if($failed.Count){exit 1}
}finally{
  if(Test-Path $repo){$repoFull=[IO.Path]::GetFullPath($repo).TrimEnd('\');&git.exe -C $repo worktree list --porcelain 2>$null|Where-Object{$_-like'worktree *'}|ForEach-Object{$path=[IO.Path]::GetFullPath($_.Substring(9)).TrimEnd('\');if(-not$path.Equals($repoFull,[StringComparison]::OrdinalIgnoreCase)-and(Test-Path $path)){&git.exe -C $repo worktree remove --force $path 2>$null|Out-Null}}}
  Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
