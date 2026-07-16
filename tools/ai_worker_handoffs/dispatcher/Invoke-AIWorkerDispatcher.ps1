[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = 'C:\Users\kevin\.codex\ai_worker_dispatcher',
  [ValidateSet('Cursor','Claude','All')][string]$Lane = 'All',
  [switch]$Once,
  [ValidateRange(1,100)][int]$MaxRequests = 1,
  [ValidateRange(1,240)][int]$StaleDispatchLockMinutes = 30,
  [ValidateRange(1,60)][int]$HardTimeoutGraceSeconds = 30,
  [string]$CursorWrapperPath = 'C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1',
  [string]$ClaudeWrapperPath = 'C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1'
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking

function Assert-UnderRoot {
  param([string]$Path,[string]$Root)
  $full = [IO.Path]::GetFullPath($Path)
  $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\')
  if (-not $full.StartsWith($rootFull + '\',[StringComparison]::OrdinalIgnoreCase)) { throw "Path escaped dispatcher root: $full" }
  return $full
}

function Move-SignedRecord {
  param([string]$Source,[string]$Destination)
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  Move-Item -LiteralPath $Source -Destination $Destination -Force
  foreach ($suffix in @('.sig','.sha256')) {
    if (Test-Path -LiteralPath ($Source + $suffix)) { Move-Item -LiteralPath ($Source + $suffix) -Destination ($Destination + $suffix) -Force }
  }
}

function Copy-HandoffArtifacts {
  param([string]$WorktreePath,[string]$Destination)
  $sourceRoot = Join-Path $WorktreePath 'runtime_artifacts\agent_handoffs'
  if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { return @() }
  $records = @(Get-ChildItem -LiteralPath $sourceRoot -Filter handoff_record.json -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc)
  if ($records.Count -eq 0) { return @() }
  $artifactDestination = Join-Path $Destination 'worker_handoff'
  Copy-Item -LiteralPath $records[-1].Directory.FullName -Destination $artifactDestination -Recurse -Force
  return @(Get-ChildItem -LiteralPath $artifactDestination -File -Recurse | ForEach-Object { $_.FullName })
}

function Get-RequestControl {
  param([string]$Root,[string]$RequestId)
  $path = Join-Path $Root "controls\$RequestId.json"
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
  $control = Read-AIWorkerSignedJson -Path $path -DispatcherRoot $Root
  if ([string]$control.artifact_type -ne 'ai_worker_dispatch_control' -or [string]$control.request_id -ne $RequestId) { throw 'Invalid dispatch control contract.' }
  return $control
}

function Assert-DispatchRequest {
  param($Request,[string]$RequestId,[string]$ExpectedLane)
  if ([string]$Request.artifact_type -ne 'ai_worker_dispatch_request' -or [string]$Request.status -ne 'QUEUED' -or [string]$Request.request_id -ne $RequestId) { throw 'Invalid dispatch request contract.' }
  if ([string]$Request.worker_lane -ne $ExpectedLane) { throw 'Request was placed in the wrong lane queue.' }
  if ([string]$Request.operation -notin @('read_only','implementation')) { throw 'Invalid dispatch operation.' }
  if ($ExpectedLane -eq 'Claude' -and [string]$Request.operation -ne 'read_only') { throw 'Claude dispatch must remain read-only.' }
  if ([DateTimeOffset]$Request.expires_at -le [DateTimeOffset]::Now) { throw 'AI_WORKER_REQUEST_EXPIRED' }
  $projectRoot = [IO.Path]::GetFullPath([string]$Request.project_root).TrimEnd('\')
  $worktrees = @(& git.exe -C $projectRoot worktree list --porcelain 2>$null | Where-Object { $_ -like 'worktree *' } | ForEach-Object { [IO.Path]::GetFullPath($_.Substring(9)).TrimEnd('\') })
  if ($LASTEXITCODE -ne 0 -or $worktrees.Count -lt 1 -or -not $projectRoot.Equals($worktrees[0],[StringComparison]::OrdinalIgnoreCase)) { throw 'Dispatch project_root must be the registered primary worktree.' }
  foreach ($path in @($Request.allowed_paths)) { if (Test-AIWorkerProtectedPath ([string]$path)) { throw "Protected worker path: $path" } }
  if ([string]$Request.operation -eq 'implementation' -and (@($Request.allowed_paths).Count -lt 1 -or @($Request.validator_commands).Count -lt 1)) { throw 'Implementation request requires exact write paths and host validators.' }
  if ([string]$Request.operation -eq 'read_only' -and (@($Request.allowed_paths).Count -gt 0 -or @($Request.validator_commands).Count -gt 0)) { throw 'Read-only request may not declare writes or validators.' }
}

function Test-Dependencies {
  param($Request,[string]$Root)
  $context = @()
  foreach ($dependencyId in @($Request.depends_on_request_ids)) {
    $completedRecord = Join-Path $Root "completed\$dependencyId\dispatch_record.json"
    $failedRecord = Join-Path $Root "dead_letter\$dependencyId\dispatch_record.json"
    if (Test-Path -LiteralPath $failedRecord) { return [ordered]@{ready=$false;terminal=$true;issue="Dependency failed: $dependencyId";context=@()} }
    if (-not (Test-Path -LiteralPath $completedRecord)) { return [ordered]@{ready=$false;terminal=$false;issue="Dependency pending: $dependencyId";context=@()} }
    $record = Read-AIWorkerSignedJson -Path $completedRecord -DispatcherRoot $Root
    if ([string]$record.status -ne 'PASS') { return [ordered]@{ready=$false;terminal=$true;issue="Dependency is not pass-like: $dependencyId";context=@()} }
    $packetPath = Join-Path $Root "completed\$dependencyId\codex_review_packet.json"
    if (Test-Path -LiteralPath $packetPath) {
      $packet = Read-AIWorkerSignedJson -Path $packetPath -DispatcherRoot $Root
      $context += [ordered]@{request_id=$dependencyId;worker_summary=[string]$packet.worker_summary;worker_classification=[string]$packet.worker_classification;recommendation=[string]$packet.recommended_codex_follow_up;changed_paths=@($packet.changed_paths);validator_status=[string]$packet.validator_status;diff_sha256=[string]$packet.diff_sha256;diff_excerpt=[string]$packet.diff_excerpt}
    }
  }
  return [ordered]@{ready=$true;terminal=$false;issue='';context=$context}
}

function Test-StaleScope {
  param($Request)
  $projectRoot = [IO.Path]::GetFullPath([string]$Request.project_root).TrimEnd('\')
  $head = (& git.exe -C $projectRoot rev-parse HEAD).Trim()
  if ($head -eq [string]$Request.base_commit) { return $false }
  & git.exe -C $projectRoot diff --quiet ([string]$Request.base_commit) $head -- @($Request.candidate_paths)
  return ($LASTEXITCODE -ne 0)
}

function Get-ChangedPaths {
  param([string]$WorktreePath)
  $tracked = @(& git.exe -C $WorktreePath diff --name-only HEAD -- | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  $untracked = @(& git.exe -C $WorktreePath ls-files --others --exclude-standard | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  return @($tracked + $untracked | ForEach-Object { ($_ -replace '\\','/').Trim() } | Where-Object { $_ -notmatch '^runtime_artifacts/agent_handoffs/' } | Sort-Object -Unique)
}

function Test-PathAllowed {
  param([string]$Path,[string[]]$AllowedPaths)
  foreach ($allowed in $AllowedPaths) {
    $normalized = (Normalize-AIWorkerRelativePath $allowed).TrimEnd('/')
    if ($Path.Equals($normalized,[StringComparison]::OrdinalIgnoreCase) -or $Path.StartsWith($normalized + '/',[StringComparison]::OrdinalIgnoreCase)) { return $true }
  }
  return $false
}

function Invoke-WorkerWrapperProcess {
  param([string]$WrapperPath,[hashtable]$Parameters,[string]$RequestId,[int]$Attempt,[int]$ContractTimeoutSeconds,[string]$Root)
  $logRoot=Join-Path $Root "logs\$RequestId\attempt_$Attempt";New-Item -ItemType Directory -Force -Path $logRoot|Out-Null
  $parametersPath=Join-Path $logRoot 'wrapper_parameters.json';$outputPath=Join-Path $logRoot 'wrapper_output.json';$stdoutPath=Join-Path $logRoot 'host_stdout.txt';$stderrPath=Join-Path $logRoot 'host_stderr.txt'
  $safe=[ordered]@{};foreach($key in $Parameters.Keys){$safe[$key]=$Parameters[$key]}
  [IO.File]::WriteAllText($parametersPath,($safe|ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
  $hostScript=Join-Path $PSScriptRoot 'Invoke-AIWorkerWrapperHost.ps1';$powerShell=(Get-Command powershell.exe -ErrorAction Stop).Source
  $arguments="-NoLogo -NoProfile -NonInteractive -File `"$hostScript`" -WrapperPath `"$WrapperPath`" -ParametersPath `"$parametersPath`" -OutputPath `"$outputPath`""
  $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$powerShell;$psi.Arguments=$arguments;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
  $process=New-Object Diagnostics.Process;$process.StartInfo=$psi;$watch=[Diagnostics.Stopwatch]::StartNew();[void]$process.Start();$stdoutTask=$process.StandardOutput.ReadToEndAsync();$stderrTask=$process.StandardError.ReadToEndAsync()
  $hardTimeoutSeconds=$ContractTimeoutSeconds+$HardTimeoutGraceSeconds;$timedOut=-not$process.WaitForExit($hardTimeoutSeconds*1000)
  if($timedOut){try{&taskkill.exe /PID $process.Id /T /F|Out-Null}catch{};try{[void]$process.WaitForExit(10000)}catch{}}else{$process.WaitForExit()};$watch.Stop()
  $stdout=$stdoutTask.Result;$stderr=$stderrTask.Result;[IO.File]::WriteAllText($stdoutPath,$stdout,(New-Object Text.UTF8Encoding($false)));[IO.File]::WriteAllText($stderrPath,$stderr,(New-Object Text.UTF8Encoding($false)))
  $result=[ordered]@{timed_out=$timedOut;contract_timeout_seconds=$ContractTimeoutSeconds;hard_timeout_seconds=$hardTimeoutSeconds;elapsed_seconds=[math]::Round($watch.Elapsed.TotalSeconds,3);exit_code=$(if($timedOut){-1}else{$process.ExitCode});output_path=$outputPath;stdout_path=$stdoutPath;stderr_path=$stderrPath}
  if($timedOut){throw "AI_WORKER_WRAPPER_HARD_TIMEOUT: process tree terminated after $hardTimeoutSeconds seconds (contract $ContractTimeoutSeconds seconds)."}
  if($process.ExitCode-ne0){$excerpt=if($stderr.Length-gt1000){$stderr.Substring(0,1000)}else{$stderr};throw "AI_WORKER_WRAPPER_PROCESS_FAILED exit=$($process.ExitCode): $excerpt"}
  if(-not(Test-Path $outputPath -PathType Leaf)){throw 'AI_WORKER_WRAPPER_OUTPUT_MISSING'}
  $result.output=Get-Content -LiteralPath $outputPath -Raw
  return [pscustomobject]$result
}

function Set-IdempotencyState {
  param($Request,[string]$Root,[string]$State,[string]$RecordPath='')
  if ([string]::IsNullOrWhiteSpace([string]$Request.idempotency_key)) { return }
  $path = Join-Path $Root "idempotency\$($Request.idempotency_key).json"
  $value = [ordered]@{artifact_type='ai_worker_idempotency_index';request_id=[string]$Request.request_id;request_path=$RecordPath;idempotency_key=[string]$Request.idempotency_key;state=$State;updated_at=(Get-Date).ToString('o')}
  Write-AIWorkerSignedJson -Path $path -Value $value -DispatcherRoot $Root | Out-Null
}

function Write-Outcome {
  param($Request,[string]$Root,[string]$State,[string]$Classification,[string[]]$Issues,[string[]]$Warnings,[string]$RunningPath,[datetime]$StartedAt,[string]$WorktreePath,[bool]$RetainWorktree,[object[]]$Artifacts,[object]$Additional)
  $destinationRoot = Join-Path $Root "$State\$($Request.request_id)"
  New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null
  $record = [ordered]@{
    schema_version=2;artifact_type='ai_worker_dispatch_record';request_id=[string]$Request.request_id;intent_id=[string]$Request.intent_id
    started_at=$StartedAt.ToString('o');finalized_at=(Get-Date).ToString('o');duration_ms=[long]((Get-Date)-$StartedAt).TotalMilliseconds
    status=$(if($State -eq 'completed'){'PASS'}else{'FAIL'});classification=$Classification;worker_lane=[string]$Request.worker_lane
    operation=[string]$Request.operation;risk_class=[string]$Request.risk_class;quality_profile=[string]$Request.quality_profile
    attempt=[int]$Request.attempt;max_attempts=[int]$Request.max_attempts;project_root=[string]$Request.project_root;base_commit=[string]$Request.base_commit
    isolated_worktree_path=$WorktreePath;worktree_retained_for_codex_review=$RetainWorktree;worker_artifact_paths=@($Artifacts)
    issues=@($Issues);warnings=@($Warnings);adoption_status=$(if($State -eq 'completed'){'PENDING_CODEX_REVIEW'}else{'NOT_APPLICABLE'})
  }
  if ($Additional) { foreach ($property in $Additional.PSObject.Properties) { $record[$property.Name] = $property.Value } }
  $recordPath = Join-Path $destinationRoot 'dispatch_record.json'
  Write-AIWorkerSignedJson -Path $recordPath -Value $record -DispatcherRoot $Root | Out-Null
  if (Test-Path -LiteralPath $RunningPath) { Move-SignedRecord -Source $RunningPath -Destination (Join-Path $destinationRoot 'request.json') }
  Set-IdempotencyState -Request $Request -Root $Root -State $(if($State -eq 'completed'){'COMPLETED_AWAITING_CODEX'}else{'DEAD_LETTER'}) -RecordPath $recordPath
  return $recordPath
}

function Requeue-Request {
  param($Request,[string]$Root,[string]$RunningPath,[string]$Issue)
  $Request.attempt = [int]$Request.attempt + 1
  $Request.status = 'QUEUED'
  $Request | Add-Member -NotePropertyName last_attempt_issue -NotePropertyValue $Issue -Force
  $Request | Add-Member -NotePropertyName not_before -NotePropertyValue ([DateTimeOffset]::Now.AddMinutes([math]::Min(15,[int]$Request.attempt * 2)).ToString('o')) -Force
  $queuePath = Join-Path $Root "queue\$($Request.worker_lane)\$($Request.request_id).json"
  if (Test-Path -LiteralPath $RunningPath) { Remove-Item -LiteralPath $RunningPath -Force }
  foreach ($suffix in @('.sig','.sha256')) { Remove-Item -LiteralPath ($RunningPath+$suffix) -Force -ErrorAction SilentlyContinue }
  Write-AIWorkerSignedJson -Path $queuePath -Value $Request -DispatcherRoot $Root | Out-Null
  Write-Utf8NoBom -Path ($queuePath+'.sha256') -Text ((Get-FileHash -LiteralPath $queuePath -Algorithm SHA256).Hash.ToLowerInvariant())
  Set-IdempotencyState -Request $Request -Root $Root -State 'QUEUED' -RecordPath $queuePath
}

function Invoke-Lane {
  param([string]$SelectedLane,[string]$Root)
  $lockPath = Join-Path $Root ("locks\{0}.lock" -f $SelectedLane.ToLowerInvariant())
  if (-not (Enter-AIWorkerFileLock -Path $lockPath -StaleMinutes $StaleDispatchLockMinutes)) { return [ordered]@{lane=$SelectedLane;status='IDLE';classification='AI_WORKER_LANE_ALREADY_RUNNING';processed=0;results=@()} }
  $results = @()
  try {
    $queueRoot = Join-Path $Root "queue\$SelectedLane"
    $files = @(Get-ChildItem -LiteralPath $queueRoot -Filter *.json -File -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -First ($MaxRequests * 4))
    foreach ($file in $files) {
      if ($results.Count -ge $MaxRequests) { break }
      $requestId = $file.BaseName
      $request = $null
      $startedAt = Get-Date
      try { $request = Read-AIWorkerSignedJson -Path $file.FullName -DispatcherRoot $Root } catch {
        $quarantineRoot = Join-Path $Root "dead_letter\$requestId"; New-Item -ItemType Directory -Force -Path $quarantineRoot | Out-Null
        Move-SignedRecord -Source $file.FullName -Destination (Join-Path $quarantineRoot 'request.json')
        $record = [ordered]@{schema_version=2;artifact_type='ai_worker_dispatch_record';request_id=$requestId;started_at=$startedAt.ToString('o');finalized_at=(Get-Date).ToString('o');status='FAIL';classification='AI_WORKER_DISPATCH_REQUEST_INTEGRITY_FAILED';issues=@($_.Exception.Message);warnings=@();adoption_status='NOT_APPLICABLE'}
        $recordPath=Join-Path $quarantineRoot 'dispatch_record.json';Write-AIWorkerSignedJson -Path $recordPath -Value $record -DispatcherRoot $Root|Out-Null
        $results += [ordered]@{request_id=$requestId;status='FAIL';classification=$record.classification;dispatch_record_path=$recordPath};continue
      }
      if ($request.PSObject.Properties.Name -contains 'not_before' -and [DateTimeOffset]$request.not_before -gt [DateTimeOffset]::Now) { continue }
      $dependency = Test-Dependencies -Request $request -Root $Root
      if (-not $dependency.ready -and -not $dependency.terminal) { continue }
      $runningPath = Join-Path $Root "running\$SelectedLane\$requestId.json"
      Move-SignedRecord -Source $file.FullName -Destination $runningPath
      $worktreeKey='w_'+(Get-Sha256Text -Text $requestId).Substring(0,16)
      $worktreePath = Assert-UnderRoot -Path (Join-Path $Root "worktrees\$worktreeKey") -Root $Root
      $worktreeCreated = $false;$retainWorktree=$false;$artifacts=@();$warnings=@();$additional=[ordered]@{}
      try {
        Assert-DispatchRequest -Request $request -RequestId $requestId -ExpectedLane $SelectedLane
        $control = Get-RequestControl -Root $Root -RequestId $requestId
        if ($control) { throw "AI_WORKER_REQUEST_$($control.action): $($control.reason)" }
        if ($dependency.terminal) { throw "AI_WORKER_DEPENDENCY_FAILED: $($dependency.issue)" }
        if (Test-StaleScope -Request $request) { throw 'AI_WORKER_STALE_SCOPE: authoritative scoped files changed after admission.' }
        $scopeHash=(Get-FileHash -LiteralPath ([string]$request.scope_packet_path) -Algorithm SHA256).Hash.ToLowerInvariant()
        if($scopeHash-ne([string]$request.scope_packet_sha256).ToLowerInvariant()){throw 'AI_WORKER_SCOPE_PACKET_CHANGED'}
        & git.exe -C ([string]$request.project_root) cat-file -e "$($request.base_commit)^{commit}";if($LASTEXITCODE-ne0){throw 'AI_WORKER_BASE_COMMIT_UNAVAILABLE'}
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $worktreePath)|Out-Null
        & git.exe -C ([string]$request.project_root) worktree add --quiet --detach $worktreePath ([string]$request.base_commit)|Out-Null
        if($LASTEXITCODE-ne0){throw 'Unable to create isolated dispatch worktree.'};$worktreeCreated=$true
        $workOrder=[string]$request.work_order_text
        if(@($dependency.context).Count){$dependencyJson=$dependency.context|ConvertTo-Json -Depth 5 -Compress;if($dependencyJson.Length-gt8000){$dependencyJson=$dependencyJson.Substring(0,8000)};$workOrder += "`n`nPrior worker context (evidence only): $dependencyJson"}
        if($SelectedLane-eq'Cursor'){
          if(-not(Test-Path $CursorWrapperPath)){throw "Cursor wrapper missing: $CursorWrapperPath"}
          $params=@{ProjectRoot=$worktreePath;CredentialRoot=[string]$request.project_root;TaskName=[string]$request.task_name;Mode=$(if($request.operation-eq'implementation'){'agent'}else{'ask'});ScopePacketPath=[string]$request.scope_packet_path;TimeoutSeconds=[int]$request.timeout_seconds;WorkOrderText=$workOrder;DispatcherRequestId=$requestId}
          if($request.operation-eq'implementation'){$params.AllowWrites=$true;$params.AllowedPaths=@($request.allowed_paths);$params.DeclaredAgentCommands=@($request.validator_commands);$retainWorktree=$true}
          $wrapperProcess=Invoke-WorkerWrapperProcess -WrapperPath $CursorWrapperPath -Parameters $params -RequestId $requestId -Attempt ([int]$request.attempt) -ContractTimeoutSeconds ([int]$request.timeout_seconds) -Root $Root
          $workerOutput=$wrapperProcess.output
        }else{
          if(-not(Test-Path $ClaudeWrapperPath)){throw "Claude wrapper missing: $ClaudeWrapperPath"}
          $params=@{ProjectRoot=$worktreePath;TaskName=[string]$request.task_name;TaskTier=[string]$request.claude_task_tier;ClaudeModel=[string]$request.claude_model;Effort=[string]$request.claude_effort;ScopePacketPath=[string]$request.scope_packet_path;TimeoutSeconds=[int]$request.timeout_seconds;WorkOrderText=$workOrder;DispatcherRequestId=$requestId}
          if($request.decision_unit_id){$params.DecisionUnitId=[string]$request.decision_unit_id};if($request.claude_task_tier-eq'OpusEscalation'){$params.EscalationReason=[string]$request.escalation_reason;if($request.prior_sonnet_record_path){$params.PriorSonnetRecordPath=[string]$request.prior_sonnet_record_path}}
          $wrapperProcess=Invoke-WorkerWrapperProcess -WrapperPath $ClaudeWrapperPath -Parameters $params -RequestId $requestId -Attempt ([int]$request.attempt) -ContractTimeoutSeconds ([int]$request.timeout_seconds) -Root $Root
          $workerOutput=$wrapperProcess.output
        }
        $workerRecord=($workerOutput|Out-String).Trim()|ConvertFrom-Json -ErrorAction Stop
        $additional.worker_status=[string]$workerRecord.status;$additional.worker_classification=[string]$workerRecord.classification;$additional.wrapper_contract_timeout_seconds=$wrapperProcess.contract_timeout_seconds;$additional.wrapper_hard_timeout_seconds=$wrapperProcess.hard_timeout_seconds;$additional.wrapper_elapsed_seconds=$wrapperProcess.elapsed_seconds
        if([string]$workerRecord.status-ne'PASS'){throw "Worker wrapper did not complete usefully: $($workerRecord.classification)"}
        $changed=Get-ChangedPaths -WorktreePath $worktreePath;$outside=@($changed|Where-Object{-not(Test-PathAllowed -Path $_ -AllowedPaths @($request.allowed_paths))})
        if($request.operation-eq'read_only'-and$changed.Count){throw "Read-only worker changed files: $($changed-join', ')"}
        if($outside.Count){throw "Worker changed paths outside the allowed scope: $($outside-join', ')"}
        $validation=$null
        if($request.operation-eq'implementation'){
          $validationPath=Join-Path (Join-Path $Root "completed\$requestId") 'host_validation.json';New-Item -ItemType Directory -Force -Path(Split-Path -Parent $validationPath)|Out-Null
          $validation=&(Join-Path $PSScriptRoot 'Invoke-AIWorkerCommandBroker.ps1') -WorktreePath $worktreePath -Commands @($request.validator_commands) -TimeoutSeconds ([math]::Min([int]$request.timeout_seconds,600)) -OutputPath $validationPath|ConvertFrom-Json
          if($validation.status-ne'PASS'){throw 'Host validator failed.'}
          $changed=Get-ChangedPaths -WorktreePath $worktreePath;$outside=@($changed|Where-Object{-not(Test-PathAllowed -Path $_ -AllowedPaths @($request.allowed_paths))})
          if($outside.Count){throw "Host validator changed paths outside the allowed scope: $($outside-join', ')"}
        }
        $artifacts=@(Copy-HandoffArtifacts -WorktreePath $worktreePath -Destination (Join-Path $Root "completed\$requestId"))
        $diffStat=(&git.exe -C $worktreePath diff --stat HEAD --|Out-String).Trim();$diffText=(&git.exe -C $worktreePath diff --binary HEAD --|Out-String)
        $diffExcerpt=if($diffText.Length-gt20000){$diffText.Substring(0,20000)+"`n[TRUNCATED; use diff_sha256 for identity]"}else{$diffText}
        $review=[ordered]@{schema_version=1;artifact_type='ai_worker_codex_review_packet';request_id=$requestId;intent_id=[string]$request.intent_id;quality_profile=[string]$request.quality_profile;risk_class=[string]$request.risk_class;acceptance_contract=$request.acceptance_contract;worker_status=[string]$workerRecord.status;worker_classification=[string]$workerRecord.classification;worker_summary=[string]$workerRecord.summary;recommended_codex_follow_up=[string]$workerRecord.recommended_codex_follow_up;changed_paths=$changed;outside_allowed_paths=$outside;diff_stat=$diffStat;diff_sha256=Get-Sha256Text -Text $diffText;diff_excerpt=$diffExcerpt;validator_status=$(if($validation){$validation.status}else{'NOT_APPLICABLE'});validator_result_path=$(if($validation){$validationPath}else{''});dependency_context=@($dependency.context);codex_review_required=$true}
        $reviewPath=Join-Path $Root "completed\$requestId\codex_review_packet.json";Write-AIWorkerSignedJson -Path $reviewPath -Value $review -DispatcherRoot $Root|Out-Null
        $additional.changed_paths=$changed;$additional.outside_allowed_paths=$outside;$additional.review_packet_path=$reviewPath;$additional.host_validation_status=$review.validator_status
        $recordPath=Write-Outcome -Request $request -Root $Root -State completed -Classification 'AI_WORKER_DISPATCH_COMPLETED_AWAITING_CODEX' -Issues @() -Warnings $warnings -RunningPath $runningPath -StartedAt $startedAt -WorktreePath $worktreePath -RetainWorktree ($worktreeCreated-and$retainWorktree) -Artifacts $artifacts -Additional ([pscustomobject]$additional)
        if($worktreeCreated-and-not$retainWorktree){&git.exe -C ([string]$request.project_root) worktree remove --force $worktreePath|Out-Null}
        $results+=[ordered]@{request_id=$requestId;status='PASS';classification='AI_WORKER_DISPATCH_COMPLETED_AWAITING_CODEX';dispatch_record_path=$recordPath;review_packet_path=$reviewPath}
      }catch{
        $issue=$_.Exception.Message;$permanent=($issue-match'AI_WORKER_(REQUEST_EXPIRED|REQUEST_CANCELED|REQUEST_SUPERSEDED|DEPENDENCY_FAILED|STALE_SCOPE|SCOPE_PACKET_CHANGED|BASE_COMMIT_UNAVAILABLE)|Invalid dispatch|Protected worker|wrong lane')
        if($worktreeCreated-and(Test-Path $worktreePath)){&git.exe -C ([string]$request.project_root) worktree remove --force $worktreePath|Out-Null}
        if(-not$permanent-and[int]$request.attempt-lt[int]$request.max_attempts){
          $attemptRoot=Join-Path $Root "attempts\$requestId\attempt_$($request.attempt)";New-Item -ItemType Directory -Force -Path $attemptRoot|Out-Null
          $attemptRecord=[ordered]@{artifact_type='ai_worker_dispatch_attempt';request_id=$requestId;attempt=[int]$request.attempt;status='RETRY_QUEUED';issue=$issue;finalized_at=(Get-Date).ToString('o')};Write-AIWorkerSignedJson -Path(Join-Path $attemptRoot 'attempt_record.json') -Value $attemptRecord -DispatcherRoot $Root|Out-Null
          Requeue-Request -Request $request -Root $Root -RunningPath $runningPath -Issue $issue
          $results+=[ordered]@{request_id=$requestId;status='RETRY_QUEUED';classification='AI_WORKER_TRANSIENT_FAILURE_RETRY_QUEUED';issue=$issue}
        }else{
          $recordPath=Write-Outcome -Request $request -Root $Root -State dead_letter -Classification $(if($permanent){'AI_WORKER_DISPATCH_TERMINAL_REJECTION'}else{'AI_WORKER_RETRY_BUDGET_EXHAUSTED'}) -Issues @($issue) -Warnings $warnings -RunningPath $runningPath -StartedAt $startedAt -WorktreePath $worktreePath -RetainWorktree $false -Artifacts $artifacts -Additional ([pscustomobject]$additional)
          $results+=[ordered]@{request_id=$requestId;status='FAIL';classification=$(if($permanent){'AI_WORKER_DISPATCH_TERMINAL_REJECTION'}else{'AI_WORKER_RETRY_BUDGET_EXHAUSTED'});dispatch_record_path=$recordPath}
        }
      }
    }
  } finally { Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue }
  return [ordered]@{lane=$SelectedLane;status=$(if(@($results|Where-Object{$_.status-eq'FAIL'}).Count){'FAIL'}else{'PASS'});classification=$(if($results.Count){'AI_WORKER_LANE_PROCESSED'}else{'AI_WORKER_LANE_IDLE'});processed=$results.Count;results=$results}
}

$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
foreach($name in @('queue\Cursor','queue\Claude','running\Cursor','running\Claude','completed','dead_letter','attempts','worktrees','logs','locks','controls','idempotency')){New-Item -ItemType Directory -Force -Path(Join-Path $root $name)|Out-Null}
if(-not(Test-Path(Get-AIWorkerKeyPath -DispatcherRoot $root))){throw 'Dispatcher signing key is not initialized.'}
$lanes=if($Lane-eq'All'){@('Cursor','Claude')}else{@($Lane)}
$laneResults=@();$processedTotal=0
foreach($selectedLane in $lanes){$laneResult=[pscustomobject](Invoke-Lane -SelectedLane $selectedLane -Root $root);$laneResults+=$laneResult;$processedTotal+=[int]$laneResult.processed}
[ordered]@{status=$(if(@($laneResults|Where-Object{$_.status-eq'FAIL'}).Count){'FAIL'}else{'PASS'});classification='AI_WORKER_DISPATCHER_CYCLE_COMPLETED';lanes=$laneResults;processed=$processedTotal}|ConvertTo-Json -Depth 12
